# T8 OSQP Fixed Interval

## Estado

`PASS`

## Hipotesis validada

La divergencia de iteraciones entre host y CVA6 no venia de la formulacion del QP ni de `libmpc`, sino del comportamiento adaptativo de `OSQP` cuando `adaptive_rho_interval` se decide en funcion del tiempo de setup con `PROFILING=ON`.

## Evidencia

- Comparacion baseline con `OSQP` original:
  - `CVA6_LINUX/plan_tests_librerias/results/parity_report.md`
  - `iteration_match = False`
- Comparacion de formulacion QP:
  - `CVA6_LINUX/plan_tests_librerias/results/t8_qp_formulation_compare.txt`
  - `T8_QP_FORMULATION_PASS`
- Experimento con `adaptive_rho_interval = 25`:
  - `CVA6_LINUX/plan_tests_librerias/results/t8_osqp_fixed_interval_compare.txt`
  - `T8_OSQP_FIXED_INTERVAL_PASS`

## Resultado

- Host y CVA6 vuelven a coincidir en:
  - `iterations`
  - `u`
  - `cost`
- Error maximo observado:
  - `u0`: `2.996408e-09`
  - `u1`: `1.284403e-07`
  - `cost`: `3.725290e-09`
  - `iterations`: `0`

## Conclusiones

1. La causa raiz esta en la adaptacion temporal de `rho`.
2. Una configuracion determinista de `adaptive_rho_interval` elimina la divergencia.
3. El siguiente paso tecnico correcto es aplicar este ajuste al flujo CVA6 real, sin depender del experimento aislado.
