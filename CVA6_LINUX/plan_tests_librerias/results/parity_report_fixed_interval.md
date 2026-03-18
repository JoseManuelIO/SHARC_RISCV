# Tarea 8. Gate de paridad host vs CVA6

## Estado

- overall: `PASS`
- behavioral: `PASS`
- formulation: `PASS`
- status_match: `True`
- control_match: `True`
- iteration_match: `True`

## Configuracion valida

- `adaptive_rho = true`
- `adaptive_rho_interval = 25`
- `profiling = on`

## Maximos observados

- max |u0| diff: `2.996408e-09`
- max |u1| diff: `1.284403e-07`
- max |cost| diff: `3.725290e-09`
- max |iterations| diff: `0.000000e+00`

## Lectura tecnica

- La formulacion QP coincide entre host y CVA6.
- El solver converge con la misma trayectoria iterativa cuando `adaptive_rho_interval` se fija a un valor constante.
- La divergencia original quedo explicada por la dependencia de `adaptive_rho_interval` con `setup_time` bajo `PROFILING=ON`.
- Con esta configuracion, la paridad requerida por T8 queda cerrada.
