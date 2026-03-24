# C5 Good vs Current Log Delta

## Status

`PASS`

## Goal

Contrast the good baseline logs and current failing logs to isolate the smallest
behavioral delta that explains why Figure 5 no longer runs.

## Good baseline sequence

From the good March artifacts:

1. `image_build.log` reports:
   - `Copying overlay ../rootfs`
   - `Generating filesystem image rootfs.cpio`
   - `CVA6 image build PASS`
2. Run metadata reports:
   - `backend_mode: "spike_persistent"`
   - `launcher: "cva6_runtime_launcher"`
   - `log_path: "/tmp/sharcbridge_cva6_runtime/persistent_0.log"`
3. The referenced persistent logs show:
   - `__SHARCBRIDGE_BEGIN_0__`
   - `/usr/bin/sharc_cva6_acc_runtime /usr/share/sharcbridge_cva6/base_config.json ...`
   - `status: 0 (opt code: 1)`
   - `"status": "SUCCESS"`

Result:

- the guest booted
- the runtime binary was present
- the config path was present
- the runtime produced controller output and metrics

## Current failing sequence

From `/tmp/sharcbridge_cva6_runtime/persistent_session.log`:

1. Guest boots far enough to reach:
   - `Starting sshd: OK`
   - `NFS preparation skipped, OK`
   - shell prompt `#`
2. Presence probe reports:
   - `MISSING:/usr/bin/sharc_cva6_acc_runtime`
   - `MISSING:/usr/share/sharcbridge_cva6/base_config.json`
   - `EXISTS:/lib/ld-linux-riscv64-lp64d.so.1`
3. The same runtime invocation then fails with:
   - `-/bin/sh: /usr/bin/sharc_cva6_acc_runtime: not found`

Result:

- the guest boot path is healthy enough
- the failure occurs before controller runtime execution
- the breakage is at the guest asset layer

## Smallest explanatory delta

The smallest delta that explains the regression is:

- good run: guest image included runtime + config
- current run: booted guest lacks runtime + config

What is not the primary blocker anymore:

- `spike_persistent` orchestration itself
- shell/prompt reachability
- dynamic linker presence

## Recovery implication

The definitive fix should target the guest assembly state:

1. recover the exact guest image composition that produced the good persistent logs, or
2. rebuild/reinstall `cva6-sdk` until the booted guest again contains:
   - `/usr/bin/sharc_cva6_acc_runtime`
   - `/usr/share/sharcbridge_cva6/base_config.json`

Only after that should we reconsider any main-flow code changes.

## Test / Gate

- Good baseline log chain reconstructed from stored artifacts: PASS
- Current failure chain reconstructed from live session log: PASS
- Minimal explanatory delta isolated to guest asset availability: PASS

## Exit criterion

The comparison now supports a concrete, minimal remediation target instead of
further exploratory edits in the main Figure 5 flow.
