# G8 Figure5 K0 Restored Triplet

- date: `2026-03-27`
- status: `PASS`

## Goal

Validate the exact first `Figure 5` snapshot outside SHARC using the restored bootable triplet now resident in:

- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/`

## Snapshot

- `request_id=figure5-k0-probe-restored-triplet`
- `k=0`
- `t=0.0`
- `x=[0.0, 60.0, 15.0]`
- `w=[11.0, 1.0]`
- `u_prev=[0.0, 0.0]`
- mode: `spike_persistent`

## Result

The exact `Figure 5` first request completes successfully:

```json
{
  "elapsed_s": 102.28524446487427,
  "ok": true,
  "response": {
    "constraint_error": 0.0003830891449930012,
    "cost": -6749320.930988319,
    "cpi": 1.0,
    "cycles": 2635946,
    "dual_residual": 6.606817436181925e-05,
    "instret": 2635946,
    "ipc": 1.0,
    "is_feasible": true,
    "iterations": 50,
    "k": 0,
    "request_id": "figure5-k0-probe-restored-triplet",
    "solver_status": "1",
    "status": "SUCCESS",
    "t_delay": 102.28505124200001,
    "u": [2.4154000086434118, -0.0003830891449930012]
  }
}
```

## Interpretation

This is the strongest confirmation so far that the restored `#6` triplet fixes the remaining boot/runtime path for the exact first `Figure 5` request.

That means:

- the failure seen earlier in full `Figure 5` was not caused by `k=0`, `x`, `w`, or `u_prev`
- the failure was tied to the unstable rebuilt triplet, not to the controller inputs

## Gate

`PASS`.

The next correct validation is the full `Figure 5` flow with the restored triplet left in place inside `CVA6_LINUX/cva6-sdk/install64/`.
