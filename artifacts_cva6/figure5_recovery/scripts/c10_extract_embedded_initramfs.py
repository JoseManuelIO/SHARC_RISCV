#!/usr/bin/env python3
from __future__ import annotations

import gzip
import json
import shutil
import subprocess
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
RECOVERY_DIR = SCRIPT_DIR.parent
ARTIFACTS_DIR = RECOVERY_DIR.parent
REPO_DIR = ARTIFACTS_DIR.parent
RESULTS_DIR = RECOVERY_DIR / "results"
LOGS_DIR = RECOVERY_DIR / "logs"
OUT_DIR = RESULTS_DIR / "c10_embedded_initramfs"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
OUT_DIR.mkdir(parents=True, exist_ok=True)

VMLINUX = REPO_DIR / "install64" / "vmlinux"
CURRENT_ROOTFS = REPO_DIR / "CVA6_LINUX" / "cva6-sdk" / "buildroot" / "output" / "images" / "rootfs.cpio"

# From symbol/section inspection of the restored good vmlinux.
INITRAMFS_START_OFF = 0x4AD628
INITRAMFS_SIZE_OFF = 0xAC39C0
SIZE_FIELD_BYTES = 8

GZ_PATH = OUT_DIR / "good_embedded_initramfs.cpio.gz"
CPIO_PATH = OUT_DIR / "good_embedded_initramfs.cpio"
LISTING_PATH = OUT_DIR / "good_embedded_initramfs_listing.txt"
CURRENT_LISTING_PATH = OUT_DIR / "current_rootfs_listing.txt"
DIFF_PATH = OUT_DIR / "listing.diff"
REPORT_JSON = OUT_DIR / "report.json"
REPORT_MD = OUT_DIR / "report.md"


def run(cmd: list[str], stdin_path: Path | None = None) -> str:
    if stdin_path is None:
        proc = subprocess.run(cmd, check=True, text=True, capture_output=True)
    else:
        with stdin_path.open("rb") as fh:
            proc = subprocess.run(cmd, check=True, text=True, stdin=fh, capture_output=True)
    return proc.stdout


def main() -> int:
    data = VMLINUX.read_bytes()
    initramfs_size = int.from_bytes(
        data[INITRAMFS_SIZE_OFF : INITRAMFS_SIZE_OFF + SIZE_FIELD_BYTES], byteorder="little"
    )
    gz_blob = data[INITRAMFS_START_OFF : INITRAMFS_START_OFF + initramfs_size]
    GZ_PATH.write_bytes(gz_blob)
    CPIO_PATH.write_bytes(gzip.decompress(gz_blob))

    good_listing = run(["cpio", "-it"], stdin_path=CPIO_PATH)
    LISTING_PATH.write_text(good_listing, encoding="utf-8")

    current_listing = run(["cpio", "-it"], stdin_path=CURRENT_ROOTFS)
    CURRENT_LISTING_PATH.write_text(current_listing, encoding="utf-8")

    diff_proc = subprocess.run(
        ["diff", "-u", str(LISTING_PATH), str(CURRENT_LISTING_PATH)],
        text=True,
        capture_output=True,
        check=False,
    )
    DIFF_PATH.write_text(diff_proc.stdout, encoding="utf-8")

    extracted_hash = run(["sha256sum", str(CPIO_PATH)]).strip().split()[0]
    current_hash = run(["sha256sum", str(CURRENT_ROOTFS)]).strip().split()[0]

    good_has_runtime = "usr/bin/sharc_cva6_acc_runtime\n" in good_listing
    good_has_config = "usr/share/sharcbridge_cva6/base_config.json\n" in good_listing
    good_has_loader = "lib/ld-linux-riscv64-lp64d.so.1\n" in good_listing
    current_has_runtime = "usr/bin/sharc_cva6_acc_runtime\n" in current_listing
    current_has_config = "usr/share/sharcbridge_cva6/base_config.json\n" in current_listing
    current_has_loader = "lib/ld-linux-riscv64-lp64d.so.1\n" in current_listing

    report = {
        "vmlinux": str(VMLINUX),
        "embedded_initramfs_gz_offset": INITRAMFS_START_OFF,
        "embedded_initramfs_size": initramfs_size,
        "extracted_good_cpio": str(CPIO_PATH),
        "extracted_good_cpio_sha256": extracted_hash,
        "current_rootfs": str(CURRENT_ROOTFS),
        "current_rootfs_sha256": current_hash,
        "good_has_runtime": good_has_runtime,
        "good_has_config": good_has_config,
        "good_has_loader": good_has_loader,
        "current_has_runtime": current_has_runtime,
        "current_has_config": current_has_config,
        "current_has_loader": current_has_loader,
        "listing_diff_path": str(DIFF_PATH),
    }
    REPORT_JSON.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    REPORT_MD.write_text(
        "\n".join(
            [
                "# C10 Embedded Initramfs Extraction",
                "",
                "- status: `PASS`",
                f"- good_vmlinux: `{VMLINUX}`",
                f"- embedded_initramfs_gz_offset: `{hex(INITRAMFS_START_OFF)}`",
                f"- embedded_initramfs_size: `{initramfs_size}`",
                f"- extracted_good_cpio: `{CPIO_PATH}`",
                f"- extracted_good_cpio_sha256: `{extracted_hash}`",
                f"- current_rootfs: `{CURRENT_ROOTFS}`",
                f"- current_rootfs_sha256: `{current_hash}`",
                f"- good_has_runtime: `{good_has_runtime}`",
                f"- good_has_config: `{good_has_config}`",
                f"- good_has_loader: `{good_has_loader}`",
                f"- current_has_runtime: `{current_has_runtime}`",
                f"- current_has_config: `{current_has_config}`",
                f"- current_has_loader: `{current_has_loader}`",
                f"- listing_diff_path: `{DIFF_PATH}`",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
