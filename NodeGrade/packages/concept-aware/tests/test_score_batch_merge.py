"""Split-mode merge must require matching C_LLM / C5_fix ID sets."""

from __future__ import annotations

import json
import os
import tempfile

import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import score_batch_results as sbr  # noqa: E402


def test_split_merge_rejects_mismatched_ids():
    with tempfile.TemporaryDirectory() as d:
        sbr.BATCH_DIR = d
        with open(os.path.join(d, "kaggle_asag_cllm_batch_01_response.json"), "w") as f:
            json.dump({"scores": {"1": 2.0, "2": 3.0}}, f)
        with open(os.path.join(d, "kaggle_asag_c5fix_batch_01_response.json"), "w") as f:
            json.dump({"scores": {"1": 2.5}}, f)
        try:
            sbr.load_responses("kaggle_asag")
        except ValueError as e:
            assert "Incomplete split-mode merge" in str(e)
        else:
            raise AssertionError("expected ValueError")


if __name__ == "__main__":
    test_split_merge_rejects_mismatched_ids()
    print("score_batch merge test: OK")
