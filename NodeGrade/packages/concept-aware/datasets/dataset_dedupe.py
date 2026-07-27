"""
Dataset deduplication helpers.

Framework Fix #19 (2026-06-15) — Kaggle ASAG ships with 105 byte-identical
duplicate (question, reference_answer, student_answer) tuples (22% of 473
records). Each duplicate pair has matching human_score, so naive paired
statistical tests treat them as independent observations and overestimate
significance. These helpers produce a deduplicated view of the source data
(in-memory, side-car JSON, or both) so downstream analysis can run on the
unique sample set without mutating the original file.

Usage:
    from datasets.dataset_dedupe import load_dedup_dataset
    unique_records, dropped_count = load_dedup_dataset("kaggle_asag")
    # 'dropped_count' is the redundant-record count for telemetry.

Also exposes ``aligned_indices`` so a parallel cached eval_results file can
be sliced down to the same unique set:

    unique_eval = [cached_eval[i] for i in aligned_indices]
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"

# Dataset identifier → source JSON filename
_DATASETS = {
    "mohler":       "mohler_dataset.json",       # may not exist; mohler_loader is canonical
    "kaggle_asag":  "kaggle_asag_dataset.json",
    "digiklausur":  "digiklausur_dataset.json",
}


def _dedupe_key(rec: dict) -> tuple[str, str, str]:
    """Canonical dedupe key: (question, reference_answer, student_answer)
    with whitespace collapsed. Treats trailing-space-only and identical-text
    records as equivalent."""
    return (
        rec.get("question", "").strip(),
        rec.get("reference_answer", "").strip(),
        rec.get("student_answer", "").strip(),
    )


def dedupe_records(records: Iterable[dict]) -> tuple[list[dict], list[int], int]:
    """Drop later occurrences of the same (q, ref, student) tuple.

    Returns
    -------
    unique_records : list[dict]
        First occurrence of each unique tuple, in original order.
    aligned_indices : list[int]
        Positional indices in the ORIGINAL record list that survived dedupe.
        Use to slice a parallel cached eval_results list.
    dropped_count : int
        Number of redundant records (extras beyond the first instance).
    """
    seen: set[tuple] = set()
    unique: list[dict] = []
    indices: list[int] = []
    total = 0
    for i, r in enumerate(records):
        total = i + 1
        k = _dedupe_key(r)
        if k in seen:
            continue
        seen.add(k)
        unique.append(r)
        indices.append(i)
    dropped_count = total - len(unique)
    return unique, indices, dropped_count


def load_dedup_dataset(dataset: str) -> tuple[list[dict], list[int], int]:
    """Load the named dataset and return its dedupd view.

    Raises FileNotFoundError if the source JSON is missing. For 'mohler'
    use datasets.mohler_loader.load_mohler_sample() instead — its 120
    samples are already unique by construction.
    """
    if dataset not in _DATASETS:
        raise ValueError(f"unknown dataset {dataset!r}; known: {list(_DATASETS)}")
    src = _DATA_DIR / _DATASETS[dataset]
    if not src.exists():
        raise FileNotFoundError(
            f"{src} not found — for mohler use datasets.mohler_loader"
        )
    with src.open() as f:
        records = json.load(f)
    return dedupe_records(records)


def write_sidecar(dataset: str, out_path: Path | None = None) -> Path:
    """Persist the dedupd view as `<dataset>_dataset_dedup.json` next to
    the source. Returns the path written. Idempotent: rewrites if invoked
    again with the same arguments."""
    unique, indices, dropped = load_dedup_dataset(dataset)
    if out_path is None:
        out_path = _DATA_DIR / f"{dataset}_dataset_dedup.json"
    payload = {
        "_meta": {
            "source": _DATASETS[dataset],
            "original_count": len(unique) + dropped,
            "unique_count": len(unique),
            "dropped_count": dropped,
            "dedupe_key": "(question, reference_answer, student_answer) post-strip",
            "aligned_indices": indices,
        },
        "records": unique,
    }
    out_path.write_text(json.dumps(payload, indent=2))
    return out_path


def slice_eval_to_unique(
    eval_results: list[dict],
    aligned_indices: list[int],
) -> list[dict]:
    """Slice a parallel cached eval_results list to the dedupd index set."""
    return [eval_results[i] for i in aligned_indices if i < len(eval_results)]
