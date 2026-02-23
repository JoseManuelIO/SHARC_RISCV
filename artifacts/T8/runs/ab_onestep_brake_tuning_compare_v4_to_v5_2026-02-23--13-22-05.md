# Comparativa tuning frenado: v4 vs v5

- v4: `artifacts/T8/runs/ab_onestep_brake_segmented_2026-02-23--13-10-55.json`
- v5: `artifacts/T8/runs/ab_onestep_brake_segmented_2026-02-23--13-22-05.json`

| Segmento | MAE v4 | MAE v5 | Mejora MAE | RMSE v4 | RMSE v5 | Mejora RMSE |
|---|---:|---:|---:|---:|---:|---:|
| early_0_2s | 20.877 | 20.881 | -0.02% | 25.364 | 25.368 | -0.02% |
| mid_2_5s | 619.220 | 218.356 | 64.74% | 906.911 | 434.116 | 52.13% |
| transition_5_6_5s | 1209.499 | 560.700 | 53.64% | 1255.866 | 625.834 | 50.17% |
| late_6_5_8s | 221.534 | 300.806 | -35.78% | 264.172 | 336.001 | -27.19% |
| all | 520.603 | 255.384 | 50.94% | 798.192 | 412.705 | 48.29% |

## Global

- RMSE brake: `798.192 -> 412.705` (`48.29%` mejora)
- MAE brake: `520.603 -> 255.384` (`50.94%` mejora)
- RMSE accel: `157.180 -> 158.198` (tradeoff menor)
