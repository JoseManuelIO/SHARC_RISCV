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
- `CVA6_SDK_DIR=/tmp/cva6-sdk-clean-20260324-r1-2` si existe
- `CVA6_SKIP_BUILD=1` cuando se usa ese SDK bueno
- `Spike` resuelto automaticamente

Outputs esperados:

- `latest/experiment_list_data_incremental.json`
- `latest/plots.png`

Si se quiere aislar una prueba manual, conviene cambiar el puerto:

- `CVA6_PORT=5019 ./run_cva6_figure5_tcp.sh`

## Evidencia y tests

Todo lo relacionado con tareas, pruebas, snapshots, logs, validaciones y reportes debe ir en:

- `artifacts_cva6/`
