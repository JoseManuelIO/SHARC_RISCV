# Tarea 8. Gate de paridad host vs CVA6

## Estado

- overall: `FAIL`
- behavioral: `PASS`
- formulation: `PASS`
- status_match: `True`
- control_match: `True`
- iteration_match: `False`

## Maximos observados

- max |u0| diff: `4.547990e-03`
- max |u1| diff: `1.369592e-02`
- max |cost| diff: `1.373562e-01`
- max |iterations| diff: `2.500000e+01`

## Lectura tecnica

- La formulacion QP coincide entre host y CVA6 dentro de tolerancias numericas de redondeo.
- El ACC original corre tanto en host como en CVA6 Linux.
- El estado del solver y la factibilidad coinciden en todos los snapshots comparados.
- Las salidas de control son muy proximas y pasan una tolerancia funcional razonable.
- El numero de iteraciones no coincide en varios snapshots; por tanto, la paridad completa de solver no esta cerrada.
- El problema queda localizado en el camino iterativo/numerico del solver, no en la construccion del QP.
