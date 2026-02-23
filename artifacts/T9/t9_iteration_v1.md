# T9 Iteration v1 Validation

- Generated: `2026-02-23T10:59:27.127576`
- Scope: minimal patch on GVSoC MPC + metadata status normalization.

## Objective Check
- Comparison baseline: `artifacts/T8/ab_report_v1.md`
- Comparison current: `artifacts/T8/ab_report_v2.md`
- RMSE brake improved by `75.14%`.
- Max |Δbrake| improved by `64.39%`.
- RMSE accel improved by `1.34%`.
- Status match now `76/80`.

## T9.3 Gate
- PASS criterion: objective improvement vs `ab_report_v1`.
- Result: `PASS` (control error decreased materially in brake and modestly in accel).
