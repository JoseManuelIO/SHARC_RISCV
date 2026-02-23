# A/B Report v1 (T8.2 + T8.3)

- Generated: `2026-02-23T10:37:11.546189`
- Source run: `/tmp/sharc_runs/2026-02-23--10-36-11-ab_onestep_compare`
- Reference: `/tmp/sharc_runs/2026-02-23--10-36-11-ab_onestep_compare/2026-02-23--01-36-11--ab-onestep-compare/a-original-onestep/simulation_data_incremental.json`
- Candidate: `/tmp/sharc_runs/2026-02-23--10-36-11-ab_onestep_compare/2026-02-23--01-36-11--ab-onestep-compare/b-gvsoc-onestep/simulation_data_incremental.json`
- Samples compared: `80`

## Control Error Metrics
- RMSE accel: `169.991895`
- RMSE brake: `4837.242181`
- MAE accel: `97.061856`
- MAE brake: `4412.209021`
- Max |Δaccel|: `519.196223`
- Max |Δbrake|: `6507.000000`

## Initial Tolerance Gate
- Threshold RMSE accel <= `600.0`
- Threshold RMSE brake <= `600.0`
- Threshold MaxAbs (both channels) <= `3000.0`
- Gate result: `FAIL`

## Metadata Spot Check
- Metadata points compared: `80`
- Matching status labels: `0/80`
