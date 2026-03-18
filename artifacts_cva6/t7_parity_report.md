# T7 Parity Report

- status: `PASS`
- source parity: `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/plan_tests_librerias/results/parity_report_fixed_interval.json`
- overall: `PASS`
- behavioral: `PASS`
- formulation: `PASS`
- validated snapshots: `5`
- solver config:
  - `adaptive_rho = true`
  - `adaptive_rho_interval = 25`
  - `profiling = true`
- max diffs:
  - `u0 = 2.996408e-09`
  - `u1 = 1.284403e-07`
  - `cost = 3.72529e-09`
  - `iterations = 0.0`
- transport smoke:
  - `u = [0.000154724130672, 63.3166773436]`
  - `iterations = 75`
  - `cost = -6049688.622352711`
- SHARC E2E audit:
  - `status histogram = {'1': 34, '-2': 2, '2': 4}`
  - `iter max = 5000`
  - `flagged count = 6`
  - `late replay = PASS`
  - `plot = /home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/t6_sharc_short_plots.png`

## Lectura tecnica

- La paridad standalone host vs CVA6 esta cerrada.
- El transporte y el E2E con SHARC funcionan.
- Los casos tardios con `solver_status = -2/2` y `iterations = 5000` son reproducibles fuera de SHARC; por tanto son comportamiento del solver en esos estados, no un bug de integracion.
