#!/usr/bin/env python3
import json
from pathlib import Path


ROOT = Path("/tmp/sharc_runs")
OUT = Path("artifacts/A_T2/ab_dataset.jsonl")
META = Path("artifacts/A_T2/ab_dataset_meta.json")


def find_latest_pair():
    runs = sorted(ROOT.glob("*-ab_onestep_compare"))
    for run in reversed(runs):
        base = next(run.glob("**/a-original-onestep/simulation_data_incremental.json"), None)
        cand = next(run.glob("**/b-gvsoc-onestep/simulation_data_incremental.json"), None)
        if base and cand:
            return run, base, cand
    raise FileNotFoundError("No A/B run pair found under /tmp/sharc_runs")


def load(p):
    with p.open() as f:
        return json.load(f)


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    run_dir, a_path, b_path = find_latest_pair()
    a = load(a_path)
    b = load(b_path)

    n = min(len(a["t"]), len(a["x"]), len(a["w"]), len(a["u"]), len(b["u"]))
    if n < 2:
        raise RuntimeError("Not enough samples to build dataset")

    with OUT.open("w") as f:
        for i in range(n):
            u_prev = a["u"][i - 1] if i > 0 else a["u"][0]
            rec = {
                "i": i,
                "k": a["k"][i],
                "t": a["t"][i],
                "x": a["x"][i],
                "w": a["w"][i],
                "u_prev": u_prev,
                "u_ref": a["u"][i],
                "u_candidate": b["u"][i],
                "source_run": str(run_dir),
            }
            f.write(json.dumps(rec) + "\n")

    meta = {
        "source_run": str(run_dir),
        "source_ref": str(a_path),
        "source_candidate": str(b_path),
        "n_records": n,
    }
    META.write_text(json.dumps(meta, indent=2) + "\n")
    print(f"PASS: wrote {n} records to {OUT}")


if __name__ == "__main__":
    main()
