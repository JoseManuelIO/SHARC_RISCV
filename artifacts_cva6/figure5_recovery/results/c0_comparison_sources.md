# C0 Comparison Sources Snapshot

## Status

`PASS`

## Goal

Freeze the exact "good" and "current" evidence sources that will be used for the
Figure 5 recovery comparison.

## Good baseline sources

- Summary with successful Figure 5 run:
  - `artifacts_cva6/figure5_t9_run_summary.md`
  - status: `PASS`
  - script: `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
  - backend: `spike_persistent`
  - main run dir: `/tmp/sharc_cva6_figure5/2026-03-18--10-38-18-cva6_figure5`
- Validation with successful hardware metrics integration:
  - `artifacts_cva6/spike_hw_metrics_validation.md`
  - status: `PASS`
  - validated run dir: `/tmp/sharc_cva6_figure5/2026-03-18--13-35-10-cva6_figure5`
- Build evidence from a good March run:
  - `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/image_build.log`
  - `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/tcp_server.log`
- Additional good run outputs present:
  - `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/latest/hw_metrics_spike_test.json`
  - `/tmp/sharc_cva6_figure5/2026-03-18--13-35-10-cva6_figure5/latest/hw_metrics_spike.json`
  - `/tmp/sharc_cva6_figure5/2026-03-18--13-35-10-cva6_figure5/latest/plots.png`

## Current recovery sources

- State summary:
  - `artifacts_cva6/figure5_recovery/CURRENT_STATE.md`
- Artifact inventory:
  - `artifacts_cva6/figure5_recovery/results/t0_artifact_inventory.txt`
- Live-guest evidence:
  - `artifacts_cva6/figure5_recovery/results/t3_persistent_stage_report.md`
  - `artifacts_cva6/figure5_recovery/results/t2_guest_manifest.txt`

## Good build-chain evidence extracted

From `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/image_build.log`:

- The build log records:
  - `>>>   Copying overlay ../rootfs`
  - `Generating filesystem image rootfs.cpio`
  - `CVA6 image build PASS`
- Buildroot target rootfs was assembled under:
  - `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/buildroot/output/target`
- Kernel image export used:
  - `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/vmlinux`
  - `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/Image`
- OpenSBI payload export used:
  - `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
- Runtime/config intended for guest packaging:
  - `target_binary=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/bin/sharc_cva6_acc_runtime`
  - `target_config=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/share/sharcbridge_cva6/base_config.json`

## Nested repo heads already captured

From `artifacts_cva6/figure5_recovery/results/t0_nested_repos_status.txt`:

- `repo_head=20d185a`
- `cva6_sdk_head=77fc4a9`
- `cva6_head=4c02b24fe`

## Current binary snapshot

- `install64/Image`
  - sha256: `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`
  - size: `19592192`
  - mtime: `2026-03-17 11:54:03 +0100`
- `install64/vmlinux`
  - sha256: `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
  - size: `15636784`
  - mtime: `2026-03-17 11:54:03 +0100`
- `install64/spike_fw_payload.elf`
  - sha256: `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`
  - size: `20555528`
  - mtime: `2026-03-17 11:54:03 +0100`
- `CVA6_LINUX/cva6-sdk/install64/Image`
  - sha256: `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`
  - size: `19592192`
  - mtime: `2026-03-24 10:36:33 +0100`
- `CVA6_LINUX/cva6-sdk/install64/vmlinux`
  - sha256: `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
  - size: `15636784`
  - mtime: `2026-03-24 10:36:26 +0100`
- `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
  - sha256: `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`
  - size: `20555528`
  - mtime: `2026-03-24 10:36:34 +0100`
- `CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio`
  - sha256: `f31c19b61a80db3c8fd383b7159ea15313386798cec78337f6a514ca908340fa`
  - size: `16755200`
  - mtime: `2026-03-24 10:33:29 +0100`

## Comparison notes

- The currently exported repo-root `install64/*` and `CVA6_LINUX/cva6-sdk/install64/*`
  match byte-for-byte for `Image`, `vmlinux`, and `spike_fw_payload.elf`.
- The live guest evidence still says:
  - runtime missing
  - base config missing
  - dynamic loader present
- This keeps the primary hypothesis unchanged: the booted guest content does not
  match the packaged rootfs content we expect.

## Test / Gate

- `find /tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5 -maxdepth 2 -type f | sort`: PASS
- `find /tmp/sharc_cva6_figure5/2026-03-18--13-35-10-cva6_figure5 -maxdepth 2 -type f | sort`: PASS
- `sha256sum` and `stat` captured for current kernel/payload/rootfs artifacts: PASS

## Exit criterion

The comparison has a stable set of good/current sources and a reproducible
snapshot of the current exported binaries.
