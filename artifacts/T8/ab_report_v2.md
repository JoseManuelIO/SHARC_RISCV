# A/B Report v2 (Post-Patch)

- Generated: `2026-02-23T12:15:20.665973`
- Source run: `/tmp/sharc_runs/2026-02-23--12-13-57-ab_onestep_compare`
- Reference: `/tmp/sharc_runs/2026-02-23--12-13-57-ab_onestep_compare/2026-02-23--03-13-57--ab-onestep-compare/a-original-onestep/simulation_data_incremental.json`
- Candidate: `/tmp/sharc_runs/2026-02-23--12-13-57-ab_onestep_compare/2026-02-23--03-13-57--ab-onestep-compare/b-gvsoc-onestep/simulation_data_incremental.json`
- Samples compared: `80`

## Control Error Metrics
- RMSE accel: `157.186719`
- RMSE brake: `1207.892369`
- MAE accel: `91.143506`
- MAE brake: `898.078492`
- Max |Δaccel|: `476.210877`
- Max |Δbrake|: `2288.634928`

## Improvement vs v1
- RMSE brake improvement: `75.03%`
- MAE brake improvement: `79.65%`
- Max |Δbrake| improvement: `64.83%`
- RMSE accel improvement: `7.53%`

## Metadata Status Parity
- Matching status labels: `76/80`

## Gate Evaluation
- Strict gate (v1): `FAIL`
- Provisional tolerance gate (stage tolerance): `PASS`

## Conclusion
- T8 can be closed in tolerance mode, with strict gate still pending for later hardening.
