# Plan De Limpieza Simple Para La Ejecucion Principal

Fecha: 2026-03-25

## Objetivo

Dejar la ejecucion principal de `CVA6 Figure 5` lo mas simple posible para
pruebas:

- que el comando normal funcione sin recordar recetas largas
- que por defecto use el `SDK` y `payload` buenos ya validados
- que `SHARCBRIDGE_CVA6` se quede solo con el codigo realmente necesario para
  la ruta principal
- que todo lo accesorio de investigacion viva en `artifacts`

## Criterio De Exito

- `./run_cva6_figure5_tcp.sh` funciona con defaults sensatos
- el flujo apunta por defecto al `SDK` bueno en `/tmp/cva6-sdk-clean-20260324-r1-2`
- el `payload` bueno se usa por defecto sin tener que pasar variables manuales
- los ficheros no necesarios para la ejecucion principal salen de
  `SHARCBRIDGE_CVA6`
- la validacion final llega hasta `latest/plots.png`

## Suposicion Operativa

Se toma como `baseline` bueno el `SDK` limpio ya validado:

- `/tmp/cva6-sdk-clean-20260324-r1-2`

Si ese path deja de existir en el futuro, habra que recrearlo o redefinir el
default antes de seguir usando el modo simplificado.

## S0 - Congelar El Baseline Bueno

Objetivo:

- dejar por escrito que el `baseline` actual es el del `SDK` limpio

Trabajo:

- enlazar:
  - `results/l1_known_good_recipe.md`
  - `results/l6_cleanup_validation_report.md`
  - `results/l7_operational_guide.md`
- registrar el path del `SDK` bueno y del `payload` bueno

Test / Gate:

- existe una referencia unica al baseline actual

Salida:

- `results/s0_simple_baseline.md`

## S1 - Ajustar Defaults Del Flujo Principal

Objetivo:

- que la ejecucion principal use por defecto el `SDK` bueno y no el `cva6-sdk`
  activo del repo

Trabajo:

- revisar y ajustar los defaults en:
  - `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
  - `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- hacer que:
  - `CVA6_SDK_DIR` apunte por defecto al `SDK` limpio bueno si existe
  - `CVA6_SPIKE_PAYLOAD` derive por defecto de ese `SDK`
  - `Spike` se resuelva automaticamente sin receta adicional
- evitar que el flujo principal reconstruya el `payload` malo por defecto

Test / Gate:

- `./run_cva6_figure5_tcp.sh` muestra por defecto el path bueno de `SDK` y
  `payload`

Salida:

- `results/s1_default_paths_report.md`

## S2 - Simplificar El Comando Principal

Objetivo:

- que la forma normal de probar sea corta y estable

Trabajo:

- decidir el default mas simple para:
  - `CVA6_SKIP_BUILD`
  - `CVA6_RUNTIME_MODE`
  - `CVA6_PORT`
- mantener override por variables de entorno cuando haga falta
- documentar claramente el comando normal y el comando de override

Test / Gate:

- existe un comando corto para Figure 5 que no requiere recordar parches

Salida:

- `results/s2_simple_entrypoint.md`

## S3 - Reducir SHARCBRIDGE_CVA6 A La Ruta Principal

Objetivo:

- sacar de `SHARCBRIDGE_CVA6` lo que no ayude a ejecutar o validar el flujo
  principal

Trabajo:

- mantener en `SHARCBRIDGE_CVA6` solo lo necesario para:
  - lanzar Figure 5
  - lanzar el backend
  - construir el runtime si alguna vez se necesita
- mover a `artifacts` los elementos accesorios de investigacion, por ejemplo:
  - `PLAN_FIGURE5_SPIKE_HW_TABLE.md`
  - `collect_spike_hw_metrics.py`
- revisar si otros planes o notas deben moverse tambien

Test / Gate:

- `SHARCBRIDGE_CVA6` queda mas enfocada en la ejecucion principal

Salida:

- `results/s3_sharcbridge_surface_report.md`

## S4 - Actualizar La Documentacion Principal

Objetivo:

- que la ruta buena quede explicada donde el usuario la va a buscar

Trabajo:

- actualizar el README relevante de `SHARCBRIDGE_CVA6`
- dejar:
  - comando normal
  - defaults importantes
  - outputs esperados
  - nota corta sobre cuando cambiar puerto

Test / Gate:

- una persona puede lanzar Figure 5 leyendo solo la documentacion principal

Salida:

- `results/s4_docs_alignment_report.md`

## S5 - Validacion Completa Del Flujo

Objetivo:

- demostrar que la limpieza no ha roto nada y que la nueva ruta simple funciona

Trabajo:

- ejecutar el comando principal ya simplificado
- comprobar:
  - backend correcto
  - dos `simulation_data_incremental.json`
  - `latest/experiment_list_data_incremental.json`
  - `latest/plots.png`

Test / Gate:

- Figure 5 completa termina en `PASS`

Salida:

- `results/s5_simple_flow_validation.md`

## Orden De Ejecucion

1. `S0` baseline
2. `S1` defaults
3. `S2` comando simple
4. `S3` mover accesorios a artifacts
5. `S4` docs
6. `S5` validacion final

## Nota Practica

El principio rector de esta limpieza es simple:

- tocar lo minimo del flujo principal
- usar por defecto lo que ya sabemos que funciona
- mover el resto a `artifacts`
- validar al final con la Figure 5 completa, no solo con smokes parciales
