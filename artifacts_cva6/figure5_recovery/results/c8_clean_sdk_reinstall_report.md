# C8 Clean SDK Reinstall Report

## Status

`FAIL`

## Goal

Test whether a clean reinstall of the local `cva6-sdk` build environment can
recover a working guest more reliably than the incremental rebuild attempted in
C7.

## What was executed

Wrapper:

- `artifacts_cva6/figure5_recovery/scripts/c8_clean_sdk_reinstall.sh`

Operations performed:

1. backup of the earlier reference payload triplet
2. `make -C CVA6_LINUX/cva6-sdk clean`
3. `make -C CVA6_LINUX/cva6-sdk gcc`
4. `bash SHARCBRIDGE_CVA6/cva6_image_builder.sh`

Post-install validation:

- `C7_SPIKE_BOOT_TIMEOUT_S=240 C7_SPIKE_COMMAND_TIMEOUT_S=60 python3 artifacts_cva6/figure5_recovery/scripts/c7_guest_presence_probe.py`

## Reinstall result

The clean reinstall completed at build level:

- `make clean`: PASS
- `make gcc`: PASS
- `cva6_image_builder.sh`: PASS

Artifacts changed again:

- `CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio`
  - before: `c62462a7d4809d4327878aedc3fa7a9fd1f6129701678f9cbc7fb0af61ce1f15`
  - after: `b2909bd8113fa045ab3a9db0a99372d68172190c691424ef496b96299580c15d`
- `CVA6_LINUX/cva6-sdk/install64/vmlinux`
  - before: `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
  - after: `e9f262af38f00b7c4d45c7e31e4800a36abdc30b88eea7746ea6d644d7079dc6`
- `CVA6_LINUX/cva6-sdk/install64/Image`
  - before: `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`
  - after: `d1ae584f0bf19037e9ac4022f335b336676280108da7759d859a786ec0a64840`
- `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
  - before: `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`
  - after: `1e821d5b874c8e6c84445ec951363f47681167f73be7627e6372576c974ad611`

Additional side effect:

- `make clean` removed repo-root `install64/vmlinux`, so the wrapper backup was
  necessary to preserve a known reference payload triplet.

## Live-guest validation result

The post-reinstall guest probe failed again:

- classification: `probe_failed`
- error: `Timeout waiting for markers ['Starting sshd: OK', 'NFS preparation skipped, OK', '# ']`

The probe log only reached OpenSBI, with no Linux boot output after the
reinstalled payload:

- `artifacts_cva6/figure5_recovery/logs/c7_guest_presence_probe.log`

This is worse than the earlier pre-reinstall state, where the restored March
payload at least reached Linux init and userspace startup.

## Safety restoration performed

After the failed reinstall validation, the earlier bootable reference payload
triplet was restored from:

- `artifacts_cva6/figure5_recovery/results/c8_backup_before_reinstall/`

Restored to:

- `install64/vmlinux`
- `install64/Image`
- `install64/spike_fw_payload.elf`
- `CVA6_LINUX/cva6-sdk/install64/vmlinux`
- `CVA6_LINUX/cva6-sdk/install64/Image`
- `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`

Restored hashes:

- `vmlinux`: `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
- `Image`: `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`
- `spike_fw_payload.elf`: `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`

## Conclusion

This task rules out a second recovery path:

- incremental official rebuild: not sufficient
- clean local `cva6-sdk` reinstall: also not sufficient

The problem is therefore no longer best explained as generic local build drift.
The evidence now supports a narrower conclusion:

- a specific historical guest/kernel/payload state worked
- current source-level rebuilds from today do not reproduce that state

## Strong next action

The next repair step should not be another rebuild variant. It should be one of:

1. recover the exact historical SDK/kernel guest state that produced the March
   payload triplet, or
2. diff the historical working payload/rootfs assembly inputs against today and
   restore that exact combination

## Test / Gate

- clean reinstall completed with official commands: PASS
- reinstalled payload reaches late userspace prompt: FAIL
- reference payload triplet restored after failure: PASS

## Exit criterion

This task is complete because it converted "maybe a clean reinstall fixes it"
into another evidence-backed negative result, while preserving the earlier
reference payload triplet for continued recovery work.
