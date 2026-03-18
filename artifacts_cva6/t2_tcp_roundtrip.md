# T2 TCP Roundtrip

## Estado

`PASS`

## Objetivo

Validar el patron:

`wrapper -> TCP server -> runtime launcher -> response`

sin depender todavia de la ejecucion real del MPC en CVA6.

## Resultado

- El servidor arranca en localhost.
- Responde correctamente a `health`.
- Responde correctamente a `run_snapshot`.
- El launcher entrega un `u` y metadata con contrato valido.

## Evidencia

- `artifacts_cva6/t2_tcp_health.log`
- `artifacts_cva6/t2_tcp_roundtrip.json`
