# Tarea 9. Decision de integracion con SHARC

## Estado

`PASS`

## Decision

- integrar con SHARC: `SI`

## Base tecnica

- overall parity: `PASS`
- formulation parity: `PASS`
- iteration parity: `True`
- solver config: `adaptive_rho_interval=25`

## Conclusion

- El camino CVA6 Linux ya es suficientemente fiel para abrir la integracion con SHARC.
- La condicion tecnica es mantener la configuracion determinista de OSQP validada en T8.
- El siguiente trabajo ya no es de compatibilidad de librerias, sino de integracion de arquitectura.
