#!/usr/bin/env python3
import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--indices", default="")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with input_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    x_list = data["x"]
    w_list = data["w"]
    t_list = data["t"]
    k_list = data["k"]
    pc_list = data["pending_computation"]

    if args.indices:
        indices = [int(x.strip()) for x in args.indices.split(",") if x.strip()]
    else:
        indices = list(range(min(args.count, len(k_list))))

    manifest = []
    prev_u = [0.0, 0.0]
    for out_idx, i in enumerate(indices, start=1):
        pc = pc_list[i]
        current_u = pc["u"]
        snap = {
            "snapshot_id": f"snapshot_{out_idx:03d}",
            "source_file": str(input_path),
            "source_index": i,
            "k": k_list[i],
            "t": t_list[i],
            "x": x_list[i],
            "w": w_list[i],
            "u_prev": prev_u,
            "u_current": current_u,
            "delay": pc["delay"],
            "metadata": pc.get("metadata", {}),
        }
        snap_path = output_dir / f"snapshot_{out_idx:03d}.json"
        with snap_path.open("w", encoding="utf-8") as f:
            json.dump(snap, f, indent=2)
        manifest.append({"snapshot": snap["snapshot_id"], "path": str(snap_path), "k": snap["k"], "t": snap["t"]})
        prev_u = current_u

    manifest_path = output_dir / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    print(f"SNAPSHOT_COUNT={len(manifest)}")
    print(f"MANIFEST={manifest_path}")


if __name__ == "__main__":
    main()
