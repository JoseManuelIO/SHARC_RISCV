# SHARCBRIDGE_CVA6

Esta carpeta contiene solo el flujo principal del nuevo camino `SHARC -> CVA6`.

## Principios

- No se toca `sharc_original`.
- Se reutiliza al maximo la arquitectura que ya funciono con `SHARCBRIDGE`.
- El transporte oficial sigue siendo `TCP`.
- El wrapper sigue siendo el punto de contacto con SHARC.
- El controlador MPC debe usar las librerias del stack original de SHARC:
  - `libmpc`
  - `Eigen`
  - `OSQP`
- La ejecucion objetivo del MPC es `CVA6 Linux`.

## Contenido esperado de esta carpeta

Solo deben vivir aqui los archivos del flujo principal:

- wrapper del controlador para CVA6
- servidor TCP del backend CVA6
- launcher/runtime del proceso CVA6
- builder de imagen/rootfs para CVA6
- script E2E principal
- documentacion de arquitectura e integracion

## Ejecucion Principal

El comando principal para Figure 5 debe ser simple:

```bash
./run_cva6_figure5_tcp.sh
```

Defaults operativos esperados:

- `CVA6_RUNTIME_MODE=spike_persistent`
- `CVA6_SDK_DIR=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk`
- `CVA6_SKIP_BUILD=1` cuando `cva6-sdk` ya contiene payload, runtime y config
- `Spike` resuelto automaticamente
- el flujo rechaza por defecto un `install64/` no validado

## Guardas de robustez

- La unica raiz operativa por defecto es `CVA6_LINUX/cva6-sdk`.
- El triplete de arranque validado vive en:
  - `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
  - `CVA6_LINUX/cva6-sdk/install64/vmlinux`
  - `CVA6_LINUX/cva6-sdk/install64/Image`
- `run_cva6_figure5_tcp.sh` y el launcher rechazan por defecto un triplete distinto.
- Si se quiere probar deliberadamente otro triplete:
  - `CVA6_ALLOW_UNVERIFIED_TRIPLET=1`
- `cva6_image_builder.sh` ya no reconstruye `install64/` por defecto.
- Si se quiere reconstruir de forma deliberada el triplete de boot:
  - `CVA6_REBUILD_BOOT_TRIPLET=1 bash ./cva6_image_builder.sh`

Outputs esperados:

- `latest/experiment_list_data_incremental.json`
- `latest/plots.png`

Si se quiere aislar una prueba manual, conviene cambiar el puerto:

- `CVA6_PORT=5019 ./run_cva6_figure5_tcp.sh`

## Evidencia y tests

Todo lo relacionado con tareas, pruebas, snapshots, logs, validaciones y reportes debe ir en:

- `artifacts_cva6/`
