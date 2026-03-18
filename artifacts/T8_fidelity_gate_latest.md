# T8 Fidelity Gate Report

- pass: `True`

## ab_onestep_compare
- pass: `True`
- run_dir: `/tmp/sharc_runs/2026-03-04--16-15-22-ab_onestep_compare`
- ref: `/tmp/sharc_runs/2026-03-04--16-15-22-ab_onestep_compare/2026-03-04--07-15-24--ab-onestep-compare/a-original-onestep/simulation_data_incremental.json`
- cand: `/tmp/sharc_runs/2026-03-04--16-15-22-ab_onestep_compare/2026-03-04--07-15-24--ab-onestep-compare/b-gvsoc-onestep/simulation_data_incremental.json`
- samples: `80`

| signal | MAE | RMSE | P95(abs) | Max(abs) |
|---|---:|---:|---:|---:|
| u_accel | 87.088267 | 150.540455 | 380.753837 | 464.238288 |
| u_brake | 218.231974 | 347.943129 | 877.432642 | 940.259160 |
| x_p | 0.158024 | 0.215211 | 0.414910 | 0.423830 |
| x_h | 0.158024 | 0.215211 | 0.414910 | 0.423830 |
| x_v | 0.110343 | 0.139671 | 0.279377 | 0.289677 |

## gvsoc_figure5
- pass: `True`
- run_dir: `/tmp/sharc_figure5_tcp/2026-03-10--11-02-28`
- ref: `/tmp/sharc_figure5_tcp/2026-03-10--11-02-28/2026-03-10--03-02-30--gvsoc-figure5/baseline-no-delay-onestep/simulation_data_incremental.json`
- cand: `/tmp/sharc_figure5_tcp/2026-03-10--11-02-28/2026-03-10--03-02-30--gvsoc-figure5/gvsoc-real-delays/simulation_data_incremental.json`
- samples: `160`

| signal | MAE | RMSE | P95(abs) | Max(abs) |
|---|---:|---:|---:|---:|
| u_accel | 0.683264 | 1.059384 | 2.181938 | 2.340778 |
| u_brake | 0.371647 | 0.577346 | 1.200550 | 1.368408 |
| x_p | 1.460539 | 1.965949 | 2.946717 | 2.993787 |
| x_h | 0.336374 | 0.452502 | 0.937909 | 1.030096 |
| x_v | 0.063383 | 0.077857 | 0.142011 | 0.150339 |

