# Brake divergence (A original vs B adaptado) - patched

- Run: `/tmp/sharc_runs/2026-02-23--13-10-55-ab_onestep_compare/2026-02-23--04-10-56--ab-onestep-compare`
- Signal: `u[1]` (frenado), delta = `B - A`

| Segmento | Samples | MAE | RMSE | Max | mean signed |
|---|---:|---:|---:|---:|---:|
| early_0_2s | 19 | 20.877 | 25.364 | 47.116 | 20.877 |
| mid_2_5s | 30 | 619.220 | 906.911 | 1585.182 | -562.547 |
| transition_5_6_5s | 16 | 1209.499 | 1255.866 | 1594.847 | 1014.614 |
| late_6_5_8s | 15 | 221.534 | 264.172 | 435.408 | 216.813 |
| all | 80 | 520.603 | 798.192 | 1594.847 | 37.579 |

## Global

- RMSE accel: 157.180
- RMSE brake: 798.192
- MAE accel: 90.637
- MAE brake: 520.603
