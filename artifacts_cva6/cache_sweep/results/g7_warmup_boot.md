# G7 Warmup Boot

- date: `2026-03-27`
- status: `PASS_AFTER_RESTORING_BOOTABLE_TRIPLET`

## Probe

Command class used:

- `artifacts_cva6/figure5_recovery/scripts/r6_guest_runtime_probe.py`

Environment:

- `CVA6_RUNTIME_MODE=spike_persistent`
- `CVA6_SDK_DIR=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk`

Outputs:

- rebuilt-triplet failure: `artifacts_cva6/figure5_recovery/results/g7_warmup_boot_probe.json`
- restored-triplet pass: `artifacts_cva6/figure5_recovery/results/g7_warmup_boot_probe_restored_triplet.json`

## Result

### 1. Rebuilt triplet (`#37`) fails

The first warmup probe, executed after rebuilding `cva6-sdk/install64/`, fails before runtime execution:

```text
Timeout waiting for markers ['# ', 'Starting sshd: OK', 'NFS preparation skipped, OK', 'Starting rpcbind: OK', 'Running sysctl: OK', 'Run /init as init process']
```

Observed behavior in `/tmp/sharcbridge_cva6_runtime/persistent_session.log`:

- repeated `OpenSBI v0.9`
- no stable progression to shell

This proves the rebuilt boot triplet was not stable enough for `spike_persistent`.

### 2. Restored triplet (`#6`) passes

After restoring the known-good triplet into:

- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/vmlinux`
- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/Image`

the warmup probe passes with:

- `classification: runtime_present_and_executable`
- `status: PASS`
- `response.status: SUCCESS`

The restored triplet hashes match the preserved known-good copies in `/home/jminiesta/Repositorios/SHARC_RISCV/install64`:

- `spike_fw_payload.elf`: `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`
- `vmlinux`: `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
- `Image`: `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`

## Interpretation

`G0-G6` already proved that the single-root SDK is coherent at build time:

- target contains runtime/config/libs
- `rootfs.cpio` contains runtime/config/libs
- kernel build tree embeds that `rootfs.cpio`

`G7` now isolates the remaining difference:

- the rebuilt `#37` boot triplet is unstable
- the restored `#6` boot triplet is stable enough to reach shell and execute the runtime

So the current blocker is not guest contents anymore. It is reproducibility of the boot triplet rebuild.

## Gate

`PASS` for warmup when `CVA6_LINUX/cva6-sdk/install64/` contains the restored bootable triplet.

`G8`, `G9`, and `G10` can proceed from this restored-triplet baseline.
