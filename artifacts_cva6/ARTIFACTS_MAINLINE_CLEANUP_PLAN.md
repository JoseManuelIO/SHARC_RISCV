# artifacts_cva6 Mainline Cleanup Plan

## Objetivo

Reducir `artifacts_cva6/` a una superficie minima y mantenible, dejando solo:

- documentacion que siga siendo util para el flujo principal actual,
- evidencia minima de validacion,
- el subarbol operativo de `cache_sweep/`,
- y, solo si aporta valor real, una guia corta de recuperacion de Figure 5.

La limpieza debe eliminar:

- `.md` rotos o desfasados,
- planes historicos ya cerrados,
- resultados voluminosos de investigacion,
- scripts auxiliares no usados,
- y artefactos que no participan en el flujo principal validado.

## Restriccion explicita

No tocar `Documentacion/presentacion_ricardo/`.

Eso implica:

- no reescribir ni borrar enlaces desde esa carpeta,
- no usar su estado actual como requisito para editarla,
- y tratar sus referencias a `artifacts_cva6/` como una dependencia externa que debe preservarse o, si no se puede preservar, señalarse antes de borrar.

## Hallazgos actuales

### Superficie actual

- `artifacts_cva6/cache_sweep/`: ya reducido y validado; hoy es la unica rama operativa dentro de `artifacts_cva6/`.
- `artifacts_cva6/figure5_recovery/`: concentra la mayor parte del ruido historico.
- `artifacts_cva6/cva6_research/`: material archivado.
- raiz de `artifacts_cva6/`: mezcla de reportes de tareas antiguas, planes y scripts de probes.

### Tamano

- `artifacts_cva6/cache_sweep/`: ~1 MB
- `artifacts_cva6/cva6_research/`: ~56 KB
- `artifacts_cva6/figure5_recovery/`: ~320 MB

Dentro de `figure5_recovery/`:

- `results/`: ~275 MB
- `logs/`: ~28 MB
- `build/`: ~19 MB

Los mayores candidatos a borrado estan en:

- `artifacts_cva6/figure5_recovery/results/c9_forensic_triplet/` (~113 MB)
- `artifacts_cva6/figure5_recovery/results/r0_reinstall_backup/` (~95 MB)
- `artifacts_cva6/figure5_recovery/results/c8_backup_before_reinstall/` (~48 MB)
- `artifacts_cva6/figure5_recovery/results/c10_embedded_initramfs/` (~20 MB)

### Markdown roto o inconsistente

Se han detectado al menos:

- `10` enlaces rotos dentro de `artifacts_cva6/**/*.md`
- `5` enlaces rotos en `Documentacion/presentacion_ricardo/*.md` que apuntan a resultados de `cache_sweep` ya eliminados

Los rotos internos se concentran sobre todo en:

- `artifacts_cva6/figure5_recovery/results/l1_known_good_recipe.md`
- `artifacts_cva6/figure5_recovery/results/l4_backend_normalization_decision.md`
- `artifacts_cva6/figure5_recovery/results/l6_cleanup_validation_report.md`
- `artifacts_cva6/figure5_recovery/results/s5_simple_flow_validation.md`
- `artifacts_cva6/figure5_recovery/results/l0_repo_cleanup_inventory.md`

La causa principal es que apuntan a:

- rutas efimeras en `/tmp/sharc_cva6_figure5/...`
- archivos ya inexistentes en el repo
- resultados antiguos de `cache_sweep` que ya no forman parte del estado limpio

### Dependencias externas a tener en cuenta

`Documentacion/presentacion_ricardo/` no se toca, pero hoy enlaza directamente a:

- `t0_architecture_reuse.md`
- `t1_wrapper_smoke.md`
- `t2_tcp_roundtrip.md`
- `t3_runtime_smoke.md`
- `t4_t6_status.md`
- `t7_parity_report.md`
- `t8_final_decision.md`
- `figure5_t0_reference.md`
- `figure5_t9_run_summary.md`
- `spike_hw_metrics_validation.md`
- `SPIKE_SHARC_CAPABILITIES_AND_CARTPOLE_PLAN.md`

## Superficie protegida propuesta

### Mantener

- `artifacts_cva6/README.md`
- `artifacts_cva6/cache_sweep/README.md`
- `artifacts_cva6/cache_sweep/configs/`
- `artifacts_cva6/cache_sweep/scripts/`
- `artifacts_cva6/cache_sweep/latest/`
- `artifacts_cva6/cache_sweep/results/`

### Mantener solo si queremos una memoria minima del flujo principal

- `artifacts_cva6/figure5_recovery/README.md`
- un unico documento final tipo `artifacts_cva6/MAINLINE_STATUS.md`
- opcionalmente una sola guia operativa corta extraida de `figure5_recovery/results/l7_operational_guide.md`

### Candidatos fuertes a borrar

- todos los `PLAN_*.md` y planes cerrados en la raiz de `artifacts_cva6/`
- los reportes de tareas antiguas `t0_*`, `t1_*`, `t2_*`, `t3_*`, `t4_*`, `t6_*`, `t7_*`, `t8_*`
- `figure5_t*.md`, `final_plan_status.md`, `spike_hw_metrics_validation.md`
- scripts de probes de la raiz:
  - `t1_wrapper_smoke.py`
  - `t2_tcp_smoke.py`
  - `t3_runtime_smoke.py`
  - `analyze_late_solver_status.py`
  - `build_t7_t8_reports.py`
- `artifacts_cva6/cva6_research/archived_from_sharcbridge_cva6/`
- casi todo `artifacts_cva6/figure5_recovery/{build,logs,results,scripts}/`
- `artifacts_cva6/tmp/`

## Estrategia de ejecucion

### Fase 1. Congelar el destino final de la documentacion

Crear o consolidar solo 2-4 documentos supervivientes:

- `artifacts_cva6/README.md`
- `artifacts_cva6/MAINLINE_STATUS.md`
- `artifacts_cva6/cache_sweep/README.md`
- opcional: `artifacts_cva6/FIGURE5_OPERATIONAL_GUIDE.md`

Objetivo:

- que las presentaciones y el material maestro apunten a estos supervivientes, no a docenas de reportes intermedios.

### Fase 2. Proteger referencias externas antes de borrar

Como `Documentacion/presentacion_ricardo/` no se puede tocar:

- no se borran de entrada los `.md` de `artifacts_cva6/` que esa carpeta siga enlazando
- primero se clasifica cada uno como `preservar`, `consolidar` o `pendiente de permiso`
- cualquier borrado que rompa esas referencias queda pospuesto hasta nueva instruccion

### Fase 3. Eliminar markdown roto dentro de `artifacts_cva6`

Borrar o reescribir los `.md` con enlaces muertos.

Regla:

- si el `.md` aporta una decision final o una receta operativa, se consolida
- si solo captura una fase intermedia, se elimina
- si esta enlazado desde `Documentacion/presentacion_ricardo/`, se preserva por ahora aunque sea historico

Prioridad:

1. `figure5_recovery/results/*.md` con enlaces a `/tmp`
2. planes historicos en la raiz
3. reportes de tareas antiguas ya absorbidos por documentacion superior

### Fase 4. Poda de archivos no necesarios para el flujo principal

Eliminar:

- `artifacts_cva6/tmp/`
- scripts de probes antiguos en la raiz
- `artifacts_cva6/cva6_research/archived_from_sharcbridge_cva6/`
- `artifacts_cva6/figure5_recovery/scripts/` salvo que queramos preservar una sola utilidad concreta

### Fase 5. Poda pesada de `figure5_recovery/`

Mantener solo una memoria minima.

Borrar por defecto:

- `figure5_recovery/build/`
- `figure5_recovery/logs/`
- backups y diffs pesados dentro de `figure5_recovery/results/`
- reportes repetidos de smoke/probe/reinstall/forensic

Mantener, si se consideran utiles:

- `figure5_recovery/README.md`
- `figure5_recovery/results/l7_operational_guide.md`
- `figure5_recovery/results/r8_figure5_clean_run_report.md`

### Fase 6. Validacion final

Despues de la limpieza:

1. ejecutar `bash SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
2. ejecutar `bash artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh`
3. volver a comprobar enlaces locales de `artifacts_cva6/**/*.md`
4. comprobar aparte que la limpieza no haya roto rutas enlazadas desde `Documentacion/presentacion_ricardo/`, sin editar esa carpeta

## Criterio de borrado

Un archivo dentro de `artifacts_cva6/` se puede borrar si cumple al menos una de estas:

- no participa en la ejecucion actual del flujo principal
- no es necesario para repetir la validacion principal
- su contenido ya esta resumido en otro documento superviviente
- apunta a rutas que ya no existen
- es evidencia historica duplicada o demasiado granular

## Resultado esperado

Al final, `artifacts_cva6/` deberia quedar aproximadamente asi:

- `README.md`
- `MAINLINE_STATUS.md`
- `cache_sweep/`
- opcional: una guia corta de Figure 5

Y deberian desaparecer:

- la mayoria de `.md` de tareas antiguas
- casi todo `figure5_recovery/`
- `cva6_research/archived_from_sharcbridge_cva6/`
- probes y scripts ya no usados
- cualquier enlace roto dentro de `artifacts_cva6/`

Nota:

- mientras `Documentacion/presentacion_ricardo/` siga enlazando archivos antiguos de `artifacts_cva6/`, esos archivos no se deben borrar sin una decision explicita posterior.
