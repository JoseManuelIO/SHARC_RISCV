# T0 Arquitectura y Reutilizacion

## Estado

`PASS`

## Que se reutiliza del caso PULP

### Wrapper

Referencia:

- `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py`

Se reutiliza:

- idea de wrapper externo compatible con SHARC
- lectura de pipes/ficheros de simulacion
- contrato de entrada/salida con SHARC
- traduccion a backend externo

Se reemplaza:

- dependencia especifica de `GVSoC`

### Servidor TCP

Referencia:

- `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`
- `SHARCBRIDGE/scripts/tcp_protocol.py`

Se reutiliza:

- framing NDJSON
- validacion de requests
- modelo `request -> handler -> response`
- comandos de `health/shutdown/compute`

Se reemplaza:

- handler de ejecucion del backend

### Script E2E

Referencia:

- `SHARCBRIDGE/scripts/run_gvsoc_config.sh`
- `SHARCBRIDGE/scripts/run_gvsoc_figure5_tcp.sh`

Se reutiliza:

- arranque ordenado del servidor
- comprobacion del backend
- inyeccion del wrapper en el entorno de SHARC
- script unico de orquestacion E2E

Se reemplaza:

- builder/runtime de `PULP/GVSoC`

## Que no se reutiliza

- toolchain `pulp-sdk`
- target `pulp-open`
- runtime bare-metal
- build del ELF RISC-V de PULP

## Que entra nuevo

- runtime `CVA6 Linux`
- builder de imagen/rootfs `CVA6`
- launcher para ejecutar el controlador dentro de `CVA6`

## Contrato cerrado

### SHARC -> wrapper

- `k`
- `t`
- `x`
- `w`

### wrapper -> TCP backend

- `type`
- `request_id`
- `k`
- `t`
- `x`
- `w`
- `u_prev`

### backend -> wrapper

- `status`
- `request_id`
- `k`
- `u`
- `iterations`
- `cost`
- `metadata`

## Decision tecnica de T0

La arquitectura del nuevo flujo sera:

`SHARC -> wrapper compatible -> TCP server -> launcher CVA6 -> MPC original`

No se abre ninguna integracion directa entre SHARC y el runtime CVA6 sin pasar por wrapper y TCP.
