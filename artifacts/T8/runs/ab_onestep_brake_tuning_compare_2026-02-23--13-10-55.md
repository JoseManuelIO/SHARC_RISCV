# Comparativa de tuning de frenado (antes vs parche)

- Antes: `ab_onestep_brake_segmented_2026-02-23--12-22-45.json`
- Después: `ab_onestep_brake_segmented_2026-02-23--13-10-55.json`

| Segmento | MAE antes | MAE después | Mejora MAE | RMSE antes | RMSE después | Mejora RMSE |
|---|---:|---:|---:|---:|---:|---:|
| early_0_2s | 29.763 | 20.877 | 29.85% | 35.970 | 25.364 | 29.49% |
| mid_2_5s | 614.256 | 619.220 | -0.81% | 876.113 | 906.911 | -3.52% |
| transition_5_6_5s | 1413.076 | 1209.499 | 14.41% | 1419.705 | 1255.866 | 11.54% |
| late_6_5_8s | 2005.376 | 221.534 | 88.95% | 2014.953 | 264.172 | 86.89% |
| all | 896.038 | 520.603 | 41.90% | 1205.204 | 798.192 | 33.77% |

- Resultado clave: en `late_6_5_8s` la MAE de frenado baja de `2005.376` a `221.534` (mejora `88.95%`).
