# T8 Final Decision

- status: `PASS`
- officialize flow: `YES`

## Base tecnica

- T4 reproducible image build: `PASS` (`/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/t4_image_build.log`)
- T5 short E2E: `PASS` (`/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/t5_e2e_short.json`)
- T6 SHARC real run: `PASS` como integracion; auditoria bruta en `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/t6_solver_status_audit.json` y replay explicativo en `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/t6_late_snapshot_replay_report.json`
- T7 parity gate: `PASS` (`/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/t7_parity_report.json`)

## Decision

- El flujo `SHARC + CVA6` ya es funcional de extremo a extremo.
- La paridad host vs CVA6 esta cerrada para el stack original `libmpc + Eigen + OSQP`.
- Los estados `-2/2` observados al final del run SHARC no son un fallo de integracion: coinciden con el replay host y CVA6 de esos mismos snapshots.
- La condicion tecnica para mantener esta lectura es conservar la configuracion determinista de OSQP (`adaptive_rho_interval = 25`, `profiling = on`).
