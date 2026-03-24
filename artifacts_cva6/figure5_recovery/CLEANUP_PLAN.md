# Plan De Limpieza Del Repo Para Figure 5

Fecha: 2026-03-24

## Objetivo

Dejar el repo en un estado limpio, entendible y funcional para regenerar la
Figure 5 de CVA6 sin depender de estados ambiguos, servidores viejos o
artefactos mezclados.

## Criterio De Exito

- existe una ruta documentada para generar Figure 5
- el backend `spike_persistent` funciona con el payload limpio validado
- el repo no mezcla trabajo de Figure 5 con otras lineas de trabajo ajenas
- los artefactos grandes o efimeros quedan fuera del control normal del repo

## Principios

- no tocar subrepos ni submodules ajenos a Figure 5 salvo que sean bloqueantes
- no borrar a ciegas nada no versionado sin antes clasificarlo
- separar:
  - codigo necesario
  - documentacion/evidencia
  - artefactos efimeros
- mantener siempre una ruta de rollback

## L0 - Inventario De Suciedad

Objetivo:

- saber exactamente que ensucia el repo y que pertenece a Figure 5

Trabajo:

- sacar `git status --short`
- agrupar cambios en:
  - necesarios para Figure 5
  - evidencias/artifacts
  - cambios ajenos
  - submodules sucios
  - directorios temporales grandes

Test / Gate:

- existe una tabla o md con clasificacion completa del estado actual

Salida:

- `results/l0_repo_cleanup_inventory.md`

## L1 - Congelar La Configuracion Buena

Objetivo:

- fijar la combinacion exacta que hoy funciona

Trabajo:

- registrar:
  - `CVA6_SDK_DIR`
  - `CVA6_SPIKE_BIN`
  - `CVA6_SPIKE_PAYLOAD`
  - `CVA6_RUNTIME_MODE`
  - puerto valido del backend
- apuntar al run bueno de Figure 5

Test / Gate:

- existe una receta minima reproducible de ejecucion

Salida:

- `results/l1_known_good_recipe.md`

## L2 - Separar Codigo Minimo Necesario

Objetivo:

- aislar el minimo codigo del repo que realmente hace falta para el flujo

Trabajo:

- revisar y marcar como necesarios solo:
  - `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
  - `SHARCBRIDGE_CVA6/cva6_tcp_server.py`
  - `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
- decidir si hace falta un helper pequeño para pasar `CVA6_SPIKE_BIN` cuando el
  SDK limpio no tenga `install64/bin/spike`

Test / Gate:

- lista cerrada de ficheros funcionales minimos

Salida:

- `results/l2_minimal_runtime_surface.md`

## L3 - Mover Evidencia A Artifacts Y Excluir Lo Efimero

Objetivo:

- que el repo no se llene de logs, backups y builds pesados

Trabajo:

- mantener en `artifacts_cva6/figure5_recovery/`:
  - planes
  - scripts de diagnostico
  - reports `.md`
  - manifests `.txt/.json`
- dejar fuera del camino normal:
  - builds locales
  - logs largos
  - backups binarios
  - payload dumps
  - outputs en `/tmp`

Test / Gate:

- listado claro de que si va al repo y que no

Salida:

- `results/l3_artifact_policy.md`

## L4 - Normalizar El Backend Limpio

Objetivo:

- evitar depender de recordar variables manuales al ejecutar Figure 5

Trabajo:

- elegir una de estas dos opciones:
  1. compilar `isa-sim` tambien en el SDK limpio
  2. hacer que el flujo detecte y use `CVA6_SPIKE_BIN` explicito cuando
     `CVA6_SDK_DIR` apunte a un SDK sin Spike local

Test / Gate:

- Figure 5 arranca con una receta estable y sin ambiguedad del binario Spike

Salida:

- `results/l4_backend_normalization_decision.md`

## L5 - Limpiar Reutilizacion Peligrosa Del TCP Server

Objetivo:

- impedir que se reutilice un server viejo con otro payload o SDK

Trabajo:

- ampliar el health/reuse contract para comprobar, si compensa:
  - runtime mode
  - payload path
  - sdk dir
  - spike bin path
- o documentar que para cambios de SDK se use puerto nuevo o reinicio forzado

Test / Gate:

- no hay reuse erroneo del backend entre payloads distintos

Salida:

- `results/l5_tcp_server_reuse_policy.md`

## L6 - Validacion Funcional Completa

Objetivo:

- confirmar que el repo limpio sigue generando Figure 5

Trabajo:

- pasar estas gates:
  - `spike` oneshot smoke
  - `spike_persistent` smoke
  - Figure 5 full run

Test / Gate:

- se generan:
  - 2 `simulation_data_incremental.json`
  - `latest/experiment_list_data_incremental.json`
  - `latest/plots.png`

Salida:

- `results/l6_cleanup_validation_report.md`

## L7 - Cierre Operativo

Objetivo:

- dejar una forma de trabajo simple para no volver a este estado

Trabajo:

- documentar:
  - como arrancar el backend limpio
  - como lanzar Figure 5
  - que outputs mirar
  - cuando usar puerto nuevo
  - que artefactos borrar sin riesgo

Test / Gate:

- existe una guia corta de operacion y mantenimiento

Salida:

- `README.md` o `results/l7_operational_guide.md`

## Orden Recomendado

1. `L0` inventario
2. `L1` receta buena
3. `L2` superficie minima
4. `L3` politica de artifacts
5. `L4` normalizacion de Spike
6. `L5` reuse policy del server
7. `L6` validacion final
8. `L7` guia operativa

## Nota Practica

Hoy ya sabemos que el repo puede generar Figure 5 con:

- SDK limpio en `/tmp/cva6-sdk-clean-20260324-r1-2`
- `spike_persistent` validado
- launcher persistente corregido
- `CVA6_SPIKE_BIN` explicito hacia el Spike ya construido del SDK activo

Asi que la limpieza ya no parte de una situacion rota: parte de una situacion
funcional que hay que simplificar y fijar.
