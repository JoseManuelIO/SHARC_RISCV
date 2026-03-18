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

## Evidencia y tests

Todo lo relacionado con tareas, pruebas, snapshots, logs, validaciones y reportes debe ir en:

- `artifacts_cva6/`
