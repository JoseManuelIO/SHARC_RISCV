# C7 Controlled Guest Rebuild Report

## Status

`FAIL`

## Goal

Run the official guest assembly path in a controlled way, then validate whether
the rebuilt payload restores a live guest containing the SHARC runtime and base
config.

## What was executed

Controlled rebuild wrapper:

- `artifacts_cva6/figure5_recovery/scripts/c7_controlled_guest_rebuild.sh`

Official guest builder used by the wrapper:

- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`

Validation probe used after rebuild:

- `artifacts_cva6/figure5_recovery/scripts/c7_guest_presence_probe.py`

## Rebuild result

The rebuild completed successfully at build level:

- `CVA6 image build PASS`
- runtime copied to `buildroot/output/target/usr/bin/sharc_cva6_acc_runtime`
- config copied to `buildroot/output/target/usr/share/sharcbridge_cva6/base_config.json`
- `linux-rebuild-with-initramfs` completed
- `install64/vmlinux`, `install64/Image`, and `install64/spike_fw_payload.elf` were regenerated

Evidence:

- `artifacts_cva6/figure5_recovery/logs/c7_controlled_guest_rebuild.log`
- `artifacts_cva6/figure5_recovery/results/c7_manifest_diff.txt`

## Artifact delta

The controlled rebuild changed all boot-critical exported artifacts:

- `rootfs.cpio`
  - before: `f31c19b61a80db3c8fd383b7159ea15313386798cec78337f6a514ca908340fa`
  - after: `c62462a7d4809d4327878aedc3fa7a9fd1f6129701678f9cbc7fb0af61ce1f15`
- `vmlinux`
  - before: `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
  - after: `38f51efa1002983305ac18fdaa46f670286c1be71c5c79aa6147db1bc0b284c2`
- `Image`
  - before: `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`
  - after: `7efd3f8ed3b9f2f136475c8d1511e110ab0b747e4a4a9be1944517dd4ba52b52`
- `spike_fw_payload.elf`
  - before: `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`
  - after: `62caf30e6a81f9f0b547a015fa4e606ba9d0199660aa5e6192c2ee620300d303`

At the packaged-rootfs level, runtime/config/loader remained present before and
after:

- `lib/ld-linux-riscv64-lp64d.so.1`
- `usr/bin/sharc_cva6_acc_runtime`
- `usr/share/sharcbridge_cva6/base_config.json`

## Live-guest validation result

The rebuilt payload failed the live-guest probe:

- classification: `probe_failed`
- error: `Timeout waiting for markers ['Starting sshd: OK', 'NFS preparation skipped, OK', '# ']`

Observed behavior:

- the rebuilt payload initially stalled at OpenSBI in the first probe run
- after restoring the previous bootable payload triplet from repo-root `install64/`,
  Linux boot messages returned again and reached:
  - `Run /init as init process`
  - `Starting syslogd: OK`
  - `Starting klogd: OK`
  - `Starting rpcbind: OK`
- but the new strict probe still did not reach the late prompt markers before timeout

This means:

- the official rebuild path is currently not a safe recovery path by itself
- rebuilding from current SDK sources made the boot path worse than the previous state

## Safety restoration performed

To avoid leaving the workspace in the worse post-rebuild boot state, the SDK
exported payload triplet was restored from the known earlier repo-root
references:

- `install64/vmlinux -> CVA6_LINUX/cva6-sdk/install64/vmlinux`
- `install64/Image -> CVA6_LINUX/cva6-sdk/install64/Image`
- `install64/spike_fw_payload.elf -> CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`

Restored hashes:

- `vmlinux`: `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
- `Image`: `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`
- `spike_fw_payload.elf`: `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`

## Conclusion

The controlled rebuild disproves the hypothesis that a plain official rebuild is
enough to recover the good Figure 5 guest state.

The comparison now points to a stronger next action:

- perform a clean reinstall/reset of the `cva6-sdk` build environment
- preserve the previously bootable payload triplet as reference
- validate guest presence immediately after reinstall, before attempting Figure 5

## Test / Gate

- Official builder executed end-to-end: PASS
- Rootfs still contains runtime/config/loader after rebuild: PASS
- Rebuilt payload reaches stable late guest prompt: FAIL
- Previous bootable payload triplet restored after failed rebuild: PASS

## Exit criterion

This task is complete because it converted "maybe rebuild fixes it" into a
clear negative result, with evidence and a safe rollback to the earlier bootable
payload triplet.
