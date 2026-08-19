"""
conceptgrade/calibration.py -- post-hoc affine recalibration for verifier
scores, applied AFTER the pipeline's own scoring (verifier_weight=1.0,
see pipeline.py's docstring and REPRODUCIBILITY.md "Finding 4").

Design rule, validated empirically and REVISED after a properly controlled
re-test caught a real confound in the first version of this module (see
compute_controlled_calibration_transfer.py and
compute_crossdataset_calibration_transfer.py):

  - Calibration is NOT portable across DATASETS/DOMAINS on the same
    backbone: transferring a fitted calibration between Mohler,
    DigiKlausur, and Kaggle ASAG hurt in 5 of 6 directions tested,
    sometimes badly (up to 38% worse MAE). This part of the original
    finding held up.

  - Calibration is NOT freely portable across BACKBONE MODELS either --
    an earlier version of this module claimed it was, based on a test
    that gave the "prior" backbone an unfair sample-size advantage (fit
    on 298 examples vs. a 10-50 example local fit). A properly controlled
    re-test (matched sample sizes both directions, shrinkage-strength
    sweep, confidence intervals) found the transfer is ASYMMETRIC:
    DeepSeek's calibration transfers well when applied to GPT's scores,
    but GPT's calibration transferred to DeepSeek's scores is actively
    worse than just fitting locally, at every tested sample size. A
    direct backbone-specific-vs-pooled comparison confirmed the same
    asymmetry: a calibration pooled across GPT+DeepSeek data slightly
    helped GPT (0.379->0.367 MAE) but measurably hurt DeepSeek
    (0.447->0.464 MAE), both differences outside their 95% CIs.

Practical consequence: fit and store ONE calibration PER (dataset/domain,
backbone) PAIR. Do not pool across backbones, and do not apply one
backbone's calibration to another's scores without first validating that
specific direction -- "transfers well" is not a property of calibration
in general, it was a property of one specific (DeepSeek -> GPT) direction
that happened to work in the one comparison run so far. A calibration
artifact records which backbone it was fit on (`fit_backbone`); applying
it to a different backbone's raw scores is refused by default (see
`Calibration.check_compatible`) rather than silently producing a
plausible-looking but unvalidated number.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict, field
from pathlib import Path

import numpy as np


class IncompatibleCalibrationError(Exception):
    """Raised when a Calibration is applied to a context (domain and/or
    backbone) it wasn't validated for. Callers that want a best-effort
    number anyway must opt in explicitly via check_compatible(..., strict=False)
    -- the default is to fail loudly rather than silently apply an
    unvalidated affine transform (see module docstring: this is exactly
    the mistake the pooled-calibration test caught)."""


@dataclass
class Calibration:
    """An affine y_calibrated = clip(a*y_raw + b, 0, 5), plus the
    compatibility metadata needed to judge whether it's safe to reuse.

    `domain` and `fit_backbone` are BOTH required and BOTH checked by
    check_compatible() -- see module docstring for why backbone match
    can no longer be treated as optional the way an earlier version of
    this module assumed.
    """
    a: float
    b: float
    domain: str              # dataset/subject this was fit on, e.g.
                              # "mohler_data_structures". NOT validated safe
                              # to reuse across domains -- see module docstring.
    fit_backbone: str        # the single LLM (OpenRouter model id) whose raw
                              # scores this was fit against, e.g.
                              # "openai/gpt-5.6-terra". NOT validated safe to
                              # apply to a different backbone's scores -- the
                              # transfer that was tested turned out asymmetric,
                              # not a general property. See module docstring.
    n_fit: int                # sample size the fit used
    rubric_id: str = ""       # optional finer-grained provenance -- score
                               # scale / rubric version, if it can differ
                               # within a domain. Empty string = unspecified,
                               # not "any rubric is fine".
    verifier_prompt_version: str = ""  # optional -- verifier prompt/system
                                         # prompt version this was fit under.
                                         # A verifier prompt change can shift
                                         # the raw-score distribution and
                                         # silently invalidate a calibration
                                         # fit under the old prompt.
    fit_date: str = ""

    def check_compatible(self, domain: str, backbone: str, verifier_prompt_version: str = "",
                          strict: bool = True) -> bool:
        """Raises IncompatibleCalibrationError (strict=True, the default) or
        returns False (strict=False) when domain, backbone, or verifier
        prompt version don't match what this calibration was validated
        for. Never silently says yes to a mismatch -- see module
        docstring for why that's the wrong default here specifically.

        verifier_prompt_version is checked only when BOTH sides specify a
        non-empty value -- an empty string on either side means "unknown",
        not "any version is fine", so it's skipped rather than treated as
        a match. This exists because a verifier prompt change (e.g. the
        skepticism instruction added in Finding 5) can shift the raw-score
        distribution enough to invalidate an existing calibration fit
        under the old prompt -- exactly what happened the first time this
        module shipped a calibration artifact."""
        problems = []
        if domain != self.domain:
            problems.append(f"domain mismatch: calibration fit for {self.domain!r}, requested {domain!r}")
        if backbone != self.fit_backbone:
            problems.append(f"backbone mismatch: calibration fit on {self.fit_backbone!r}, requested {backbone!r}")
        if verifier_prompt_version and self.verifier_prompt_version and verifier_prompt_version != self.verifier_prompt_version:
            problems.append(f"verifier_prompt_version mismatch: calibration fit under "
                             f"{self.verifier_prompt_version!r}, current prompt is {verifier_prompt_version!r}")
        if problems:
            if strict:
                raise IncompatibleCalibrationError("; ".join(problems))
            return False
        return True

    def apply(self, raw_score: float | np.ndarray) -> float | np.ndarray:
        calibrated = self.a * np.asarray(raw_score) + self.b
        clipped = np.clip(calibrated, 0.0, 5.0)
        return float(clipped) if np.isscalar(raw_score) or np.ndim(raw_score) == 0 else clipped

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Calibration":
        return cls(**d)


def fit(human_scores: np.ndarray, raw_scores: np.ndarray, domain: str,
        fit_backbone: str, rubric_id: str = "", verifier_prompt_version: str = "",
        fit_date: str = "") -> Calibration:
    """Least-squares affine fit: human_scores ~= a*raw_scores + b.

    `domain` should identify the dataset/subject/rubric this calibration
    is valid for. `fit_backbone` must name the single LLM these raw_scores
    came from -- fit one Calibration per (domain, backbone) pair, do not
    pool multiple backbones' scores into one fit (see module docstring:
    pooling was tested and found to help one backbone while hurting
    another, an asymmetric trade-off with no safe single default)."""
    human_scores = np.asarray(human_scores, dtype=float)
    raw_scores = np.asarray(raw_scores, dtype=float)
    if len(human_scores) != len(raw_scores):
        raise ValueError(f"length mismatch: {len(human_scores)} human scores vs {len(raw_scores)} raw scores")
    if len(human_scores) < 10:
        raise ValueError(
            f"only {len(human_scores)} samples -- fitting a calibration on fewer than "
            f"10 is unreliable (see compute_controlled_calibration_transfer.py's n=10 "
            f"result, which already shows high variance at this size)"
        )
    A = np.column_stack([raw_scores, np.ones_like(raw_scores)])
    a, b = np.linalg.lstsq(A, human_scores, rcond=None)[0]
    return Calibration(a=float(a), b=float(b), domain=domain, fit_backbone=fit_backbone,
                        n_fit=len(human_scores), rubric_id=rubric_id,
                        verifier_prompt_version=verifier_prompt_version, fit_date=fit_date)


def save(calibration: Calibration, path: Path | str) -> None:
    Path(path).write_text(json.dumps(calibration.to_dict(), indent=2))


def load(path: Path | str) -> Calibration:
    return Calibration.from_dict(json.loads(Path(path).read_text()))
