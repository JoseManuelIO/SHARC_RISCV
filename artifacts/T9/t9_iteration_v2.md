# T9 Iteration v2 Validation

- Generated: `2026-02-23T11:04:35.246006`
- Scope: tuned GVSoC MPC cost + metadata alignment + precision transport cleanup.

## Objective Check vs baseline
- Baseline: `artifacts/T8/ab_report_v1.md`
- Current: `artifacts/T8/ab_report_v2.md`
- RMSE brake improvement: `74.72%`
- MAE brake improvement: `80.02%`
- Max |Δbrake| improvement: `63.04%`
- RMSE accel improvement: `0.07%`
- Status parity: `76/80`

## T9.3 Gate
- PASS criterion: objective improvement vs baseline A/B.
- Result: `PASS`.
