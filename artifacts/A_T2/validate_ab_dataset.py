#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


REQUIRED_KEYS = {"i", "k", "t", "x", "w", "u_prev", "u_ref", "u_candidate", "source_run"}


def is_num(x):
    return isinstance(x, (int, float)) and math.isfinite(float(x))


def validate_record(rec, idx):
    missing = REQUIRED_KEYS - set(rec.keys())
    if missing:
        raise ValueError(f"record {idx}: missing keys {sorted(missing)}")
    if not isinstance(rec["x"], list) or len(rec["x"]) != 3:
        raise ValueError(f"record {idx}: x must have len=3")
    if not isinstance(rec["w"], list) or len(rec["w"]) != 2:
        raise ValueError(f"record {idx}: w must have len=2")
    for key in ("u_prev", "u_ref", "u_candidate"):
        if not isinstance(rec[key], list) or len(rec[key]) != 2:
            raise ValueError(f"record {idx}: {key} must have len=2")
    nums = [rec["t"], *rec["x"], *rec["w"], *rec["u_prev"], *rec["u_ref"], *rec["u_candidate"]]
    if not all(is_num(v) for v in nums):
        raise ValueError(f"record {idx}: non-numeric/NaN/Inf value found")
    if rec["t"] < 0:
        raise ValueError(f"record {idx}: negative time")
    if rec["x"][2] < 0:
        raise ValueError(f"record {idx}: negative velocity")


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("artifacts/A_T2/ab_dataset.jsonl")
    lines = [ln for ln in path.read_text().splitlines() if ln.strip()]
    if len(lines) < 10:
        raise SystemExit("FAIL: dataset too short")

    prev_t = None
    for idx, ln in enumerate(lines):
        rec = json.loads(ln)
        validate_record(rec, idx)
        if prev_t is not None and rec["t"] < prev_t:
            raise SystemExit(f"FAIL: non-monotonic time at record {idx}")
        prev_t = rec["t"]

    print(f"PASS: dataset schema/range checks OK ({len(lines)} records).")


if __name__ == "__main__":
    main()
