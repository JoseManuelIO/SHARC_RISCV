# S1 Default Paths Report

- fecha: `2026-03-25`
- estado: `PASS`

## Cambios aplicados

- [run_cva6_figure5_tcp.sh](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh)
  - resuelve por defecto `CVA6_SDK_DIR=/tmp/cva6-sdk-clean-20260324-r1-2` si existe
  - deriva `CVA6_SPIKE_PAYLOAD` de ese `SDK`
  - exporta `CVA6_SDK_DIR` para que el server y el launcher vean el mismo default
- [cva6_runtime_launcher.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_runtime_launcher.py)
  - usa por defecto el `SDK` bueno si existe
  - hace fallback del binario `Spike` al `cva6-sdk` del repo si el `SDK` limpio no lo trae
- [cva6_image_builder.sh](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_image_builder.sh)
  - reconstruye sobre el `SDK` bueno por defecto si se forza build

## Evidencia

El comando simple ya imprime por defecto:

- `CVA6 sdk dir=/tmp/cva6-sdk-clean-20260324-r1-2`
- `CVA6 spike payload=/tmp/cva6-sdk-clean-20260324-r1-2/install64/spike_fw_payload.elf`
- `CVA6 spike bin=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/bin/spike`

## Gate

- la ruta principal ya no cae por defecto en el `payload` malo del repo
