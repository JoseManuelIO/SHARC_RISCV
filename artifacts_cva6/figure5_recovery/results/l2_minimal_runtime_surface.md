# L2 Minimal Runtime Surface

- fecha: `2026-03-24`
- estado: `PASS`

## Ficheros del flujo que realmente necesitan cambios para Figure 5

- [cva6_runtime_launcher.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_runtime_launcher.py)
  - fija el arranque de `spike_persistent`
  - acepta assets ya presentes en guest
  - publica identidad de backend en `health`
- [cva6_tcp_server.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_tcp_server.py)
  - mantiene el contrato TCP y los timeouts de ejecucion
- [run_cva6_figure5_tcp.sh](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh)
  - arranca el backend
  - resuelve `Spike` para el SDK limpio
  - evita reuse erroneo de un server viejo

## Ficheros del flujo que siguen siendo necesarios pero no requieren limpieza nueva

- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`
- `SHARCBRIDGE_CVA6/cva6_figure5.json`
- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`

## Decision

- la superficie minima modificable sigue siendo de tres ficheros
- no hace falta mover mas logica a `SHARCBRIDGE_CVA6`
- el resto de sondas y scripts auxiliares se quedan en `artifacts_cva6/figure5_recovery/scripts`

## Gate

- lista cerrada de codigo minimo necesaria para sostener el flujo recuperado
