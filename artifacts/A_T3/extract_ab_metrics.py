#!/usr/bin/env python3
import json
import math
import sys
from statistics import mean


def rmse(vals):
    return math.sqrt(mean([v * v for v in vals]))


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "artifacts/A_T2/ab_dataset.jsonl"
    rows = [json.loads(ln) for ln in open(path) if ln.strip()]
    du0 = [r["u_candidate"][0] - r["u_ref"][0] for r in rows]
    du1 = [r["u_candidate"][1] - r["u_ref"][1] for r in rows]
    out = {
        "samples": len(rows),
        "rmse_u_accel": rmse(du0),
        "rmse_u_brake": rmse(du1),
        "mae_u_accel": mean([abs(v) for v in du0]),
        "mae_u_brake": mean([abs(v) for v in du1]),
    }
    print(json.dumps(out))


if __name__ == "__main__":
    main()
