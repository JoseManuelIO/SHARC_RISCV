# Brake divergence (A original vs B adaptado) - patched v5

- Run: `/tmp/sharc_runs/2026-02-23--13-22-05-ab_onestep_compare/2026-02-23--04-22-06--ab-onestep-compare`
- Signal: `u[1]` (frenado), delta = `B - A`

| Segmento | Samples | MAE | RMSE | Max | mean signed |
|---|---:|---:|---:|---:|---:|
| early_0_2s | 19 | 20.881 | 25.368 | 47.122 | 20.881 |
| mid_2_5s | 30 | 218.356 | 434.116 | 1327.688 | -161.682 |
| transition_5_6_5s | 16 | 560.700 | 625.834 | 965.018 | -174.048 |
| late_6_5_8s | 15 | 300.806 | 336.001 | 515.781 | 300.806 |
| all | 80 | 255.384 | 412.705 | 1327.688 | -34.080 |

## Global

- RMSE accel: 158.198
- RMSE brake: 412.705
- MAE accel: 93.285
- MAE brake: 255.384
