# Brake divergence (A original vs B adaptado)

- Run: `/tmp/sharc_runs/2026-02-23--12-22-45-ab_onestep_compare`
- Signal: `u[1]` (frenado), delta = `B - A`

| Segmento | Samples | MAE | RMSE | Max | mean signed |
|---|---:|---:|---:|---:|---:|
| early_0_2s | 19 | 29.763 | 35.970 | 66.076 | 29.763 |
| mid_2_5s | 30 | 614.256 | 876.113 | 1531.655 | -525.669 |
| transition_5_6_5s | 16 | 1413.076 | 1419.705 | 1649.026 | 862.019 |
| late_6_5_8s | 15 | 2005.376 | 2014.953 | 2285.904 | 2005.376 |
| all | 80 | 896.038 | 1205.204 | 2285.904 | 358.355 |

## Top 5 picos |delta_brake|

- t=8.000s: A=900.016, B=3185.920, delta=2285.904
- t=7.800s: A=900.016, B=3185.920, delta=2285.904
- t=7.800s: A=1013.372, B=3221.670, delta=2208.298
- t=7.600s: A=1013.372, B=3221.670, delta=2208.298
- t=7.600s: A=1131.317, B=3257.600, delta=2126.283
