# T9 Iteration v3 Validation

- Generated: `2026-02-23T12:15:20.666253`
- Scope: equation-based lightweight QP controller (no LMPC/OSQP heavy stack).

## Objective Check vs baseline
- Baseline: `artifacts/T8/ab_report_v1.md`
- Current: `artifacts/T8/ab_report_v2.md`
- RMSE accel improvement: `7.53%`
- RMSE brake improvement: `75.03%`
- MAE accel improvement: `6.10%`
- MAE brake improvement: `79.65%`
- Status parity: `76/80`

## T9.3 Gate
- PASS criterion: objective improvement vs baseline A/B.
- Result: `PASS`.
