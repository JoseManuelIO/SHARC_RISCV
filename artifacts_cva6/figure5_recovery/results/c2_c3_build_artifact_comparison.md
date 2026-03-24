# C2 C3 Build and Artifact Comparison

## Status

`PASS`

## Goal

Compare the intended build outputs with the current live-guest behavior, and
check whether the exported kernel and payload artifacts are internally
consistent.

## Build-chain facts from the good March build

From `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/image_build.log`:

- The rootfs was built through:
  - `CVA6_LINUX/cva6-sdk/buildroot/output/target`
- The kernel export step was:
  - `objcopy ... CVA6_LINUX/cva6-sdk/install64/vmlinux CVA6_LINUX/cva6-sdk/install64/Image`
- The OpenSBI payload build used:
  - `FW_PAYLOAD_PATH=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/Image`
- The final payload export was:
  - `cp opensbi/build/platform/generic/firmware/fw_payload.elf /home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
- The SHARC guest assets intended for packaging were:
  - `target_binary=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/bin/sharc_cva6_acc_runtime`
  - `target_config=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/share/sharcbridge_cva6/base_config.json`

## Current packaged rootfs facts

Current `rootfs.cpio` contains all three expected files:

- `lib/ld-linux-riscv64-lp64d.so.1`
- `usr/bin/sharc_cva6_acc_runtime`
- `usr/share/sharcbridge_cva6/base_config.json`

Command used:

```bash
cpio -it < CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio
```

## Current live-guest facts

From `artifacts_cva6/figure5_recovery/results/t3_persistent_stage_report.md`:

- `/usr/bin/sharc_cva6_acc_runtime`: `MISSING`
- `/usr/share/sharcbridge_cva6/base_config.json`: `MISSING`
- `/lib/ld-linux-riscv64-lp64d.so.1`: `EXISTS`

## Exported artifact consistency

The following artifact pairs currently match byte-for-byte:

- `install64/Image` == `CVA6_LINUX/cva6-sdk/install64/Image`
- `install64/vmlinux` == `CVA6_LINUX/cva6-sdk/install64/vmlinux`
- `install64/spike_fw_payload.elf` == `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`

This means there is no current mismatch between the repo-root exported payload
triplet and the `cva6-sdk/install64` exported payload triplet.

## Interpretation

The comparison currently points to a content-selection problem, not a simple
export-copy problem:

- the packaged rootfs says runtime/config should exist
- the booted guest says runtime/config do not exist
- the loader exists in both views
- the exported kernel/payload triplet is internally consistent

The most likely explanations are:

1. the booted payload is not using the same guest content as the current
   packaged rootfs, or
2. the good March boot path relied on a different guest assembly state that is
   no longer reproduced today.

## Recovery consequence

The next comparison step should focus on recovering or identifying the exact
guest assembly state used by the good March runs, instead of continuing to tweak
copy/export mechanics in the main flow.

## Test / Gate

- `image_build.log` contains the build and export chain: PASS
- `rootfs.cpio` lists runtime/config/loader: PASS
- live guest probe still reports runtime/config missing and loader present: PASS
- exported payload triplet matches across both install roots: PASS

## Exit criterion

We have isolated the discrepancy to "packaged rootfs vs booted guest content",
which is now the primary target for the next comparison tasks.
