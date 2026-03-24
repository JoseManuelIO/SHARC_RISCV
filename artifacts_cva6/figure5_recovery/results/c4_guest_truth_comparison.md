# C4 Guest Truth Comparison

## Status

`PASS`

## Goal

Compare what the good baseline guest demonstrably executed against what the
current guest actually exposes at runtime.

## Good baseline evidence

The March-good run metadata explicitly points to persistent runtime logs:

- `backend_mode: "spike_persistent"`
- `launcher: "cva6_runtime_launcher"`
- `log_path: "/tmp/sharcbridge_cva6_runtime/persistent_0.log"`

Evidence locations:

- `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/latest/experiment_list_data_incremental.json`
- `/tmp/sharc_cva6_figure5/2026-03-18--13-35-10-cva6_figure5/2026-03-18--05-35-12--cva6-figure5/cva6-real-delays/experiment_result.json`

The surviving persistent logs currently present at the referenced paths show the
guest successfully invoked:

- `/usr/bin/sharc_cva6_acc_runtime /usr/share/sharcbridge_cva6/base_config.json /tmp/sharcbridge_cva6/snapshot_0.json`
- `/usr/bin/sharc_cva6_acc_runtime /usr/share/sharcbridge_cva6/base_config.json /tmp/sharcbridge_cva6/snapshot_63.json`

And they produced successful runtime JSON:

- `"status": "SUCCESS"`
- `cycles`, `instret`, `ipc`, `cpi` populated

Important note:

- The files `/tmp/sharcbridge_cva6_runtime/persistent_0.log` and
  `/tmp/sharcbridge_cva6_runtime/persistent_63.log` have mtimes from
  `2026-03-20`, not `2026-03-18`.
- Because the March-good artifacts explicitly reference those exact paths, these
  logs are valid corroborating evidence of the good guest/runtime path, even if
  they are not immutable March-18 snapshots.

## Current guest evidence

From `artifacts_cva6/figure5_recovery/results/t3_persistent_stage_report.md`
and `/tmp/sharcbridge_cva6_runtime/persistent_session.log`:

- `/usr/bin/sharc_cva6_acc_runtime`: `MISSING`
- `/usr/share/sharcbridge_cva6/base_config.json`: `MISSING`
- `/lib/ld-linux-riscv64-lp64d.so.1`: `EXISTS`
- Running the baseline command now yields:
  - `-/bin/sh: /usr/bin/sharc_cva6_acc_runtime: not found`

## Direct comparison

Good guest path:

- command path exists
- config path exists
- runtime executes
- runtime emits JSON metadata with `status: "SUCCESS"`

Current guest path:

- command path missing
- config path missing
- loader exists
- same command fails before runtime starts

## Conclusion

This comparison closes the main uncertainty:

- the good baseline did not succeed through an alternative path
- it really did execute `/usr/bin/sharc_cva6_acc_runtime` with
  `/usr/share/sharcbridge_cva6/base_config.json`
- the current failure is therefore a real guest-content regression

## Test / Gate

- Good run metadata references persistent logs: PASS
- Surviving `persistent_0.log` and `persistent_63.log` show successful runtime execution: PASS
- Current guest presence probe shows runtime/config missing and loader present: PASS
- Current invocation fails with `not found`: PASS

## Exit criterion

The regression is now confirmed at the live guest-content level, not merely in
build assumptions or host-side export logic.
