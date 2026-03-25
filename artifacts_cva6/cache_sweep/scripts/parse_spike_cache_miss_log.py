#!/usr/bin/env python3
"""Parse Spike --log-cache-miss output into structured cache miss counts."""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


MISS_RE = re.compile(r"^(?P<cache>I\$|D\$|L2\$)\s+(?P<op>read|write)\s+miss\s+(?P<addr>0x[0-9a-fA-F]+)$")
CACHE_ARG_RE = re.compile(r"--(?P<name>ic|dc|l2)=(?P<sets>\d+):(?P<ways>\d+):(?P<block>\d+)")


def _parse_cache_args(cache_args: str) -> dict[str, dict[str, int]]:
    parsed: dict[str, dict[str, int]] = {}
    for match in CACHE_ARG_RE.finditer(cache_args or ""):
        parsed[match.group("name")] = {
            "sets": int(match.group("sets")),
            "ways": int(match.group("ways")),
            "block_bytes": int(match.group("block")),
        }
    return parsed


def _parse_log(log_path: Path) -> tuple[list[dict], dict]:
    events: list[dict] = []
    counts: dict[str, int] = {}
    unique_addrs: dict[str, set[int]] = {}

    with log_path.open("r", encoding="utf-8", errors="ignore") as fh:
        for raw_line in fh:
            line = raw_line.strip()
            match = MISS_RE.match(line)
            if not match:
                continue
            cache = match.group("cache")
            op = match.group("op")
            addr_text = match.group("addr")
            addr = int(addr_text, 16)
            key = f"{cache}:{op}"
            counts[key] = counts.get(key, 0) + 1
            unique_addrs.setdefault(key, set()).add(addr)
            events.append(
                {
                    "cache": cache,
                    "op": op,
                    "addr": addr_text,
                    "addr_int": addr,
                }
            )

    summary_rows: list[dict] = []
    for key in sorted(counts):
        cache, op = key.split(":", 1)
        summary_rows.append(
            {
                "cache": cache,
                "op": op,
                "miss_count": counts[key],
                "unique_addr_count": len(unique_addrs.get(key, set())),
            }
        )

    summary = {
        "total_miss_events": sum(counts.values()),
        "rows": summary_rows,
    }
    return events, summary


def _write_csv(path: Path, rows: list[dict]) -> None:
    fieldnames = ["cache", "op", "miss_count", "unique_addr_count", "block_bytes", "estimated_linefill_bytes"]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _write_md(path: Path, payload: dict) -> None:
    lines = [
        "# Spike Cache Miss Log Summary",
        "",
        f"- log: `{payload['log_path']}`",
        f"- spike_cache_args: `{payload['spike_cache_args']}`",
        f"- total_miss_events: `{payload['total_miss_events']}`",
        "",
        "| cache | op | miss_count | unique_addr_count | block_bytes | estimated_linefill_bytes |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in payload["rows"]:
        lines.append(
            f"| {row['cache']} | {row['op']} | {row['miss_count']} | {row['unique_addr_count']} | "
            f"{row['block_bytes']} | {row['estimated_linefill_bytes']} |"
        )

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- This parser uses actual `Spike --log-cache-miss` event lines such as `I$ read miss ...`.",
            "- This local Spike build does not emit aggregate `Read Accesses` / `Miss Rate` summaries in the observed logs.",
            "- `estimated_linefill_bytes` is a simple `miss_count * block_bytes` estimate and should be treated as a cache-line traffic proxy.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, required=True, help="Spike log produced with --log-cache-miss")
    parser.add_argument("--spike-cache-args", default="", help="Original SPIKE_CACHE_ARGS string")
    parser.add_argument("--out-prefix", type=Path, required=True, help="Output prefix without extension")
    args = parser.parse_args()

    events, summary = _parse_log(args.log.resolve())
    cache_cfg = _parse_cache_args(args.spike_cache_args)

    rows: list[dict] = []
    for row in summary["rows"]:
        block_bytes = 0
        if row["cache"] == "I$":
            block_bytes = cache_cfg.get("ic", {}).get("block_bytes", 0)
        elif row["cache"] == "D$":
            block_bytes = cache_cfg.get("dc", {}).get("block_bytes", 0)
        elif row["cache"] == "L2$":
            block_bytes = cache_cfg.get("l2", {}).get("block_bytes", 0)
        out_row = dict(row)
        out_row["block_bytes"] = block_bytes
        out_row["estimated_linefill_bytes"] = row["miss_count"] * block_bytes if block_bytes else 0
        rows.append(out_row)

    payload = {
        "log_path": str(args.log.resolve()),
        "spike_cache_args": args.spike_cache_args,
        "cache_config": cache_cfg,
        "total_miss_events": summary["total_miss_events"],
        "rows": rows,
        "sample_event_count": len(events),
    }

    out_prefix = args.out_prefix.resolve()
    out_prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = out_prefix.with_suffix(".json")
    csv_path = out_prefix.with_suffix(".csv")
    md_path = out_prefix.with_suffix(".md")

    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    _write_csv(csv_path, rows)
    _write_md(md_path, payload)

    print(f"JSON: {json_path}")
    print(f"CSV:  {csv_path}")
    print(f"MD:   {md_path}")
    print(f"Rows: {len(rows)}")
    print(f"Misses: {payload['total_miss_events']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
