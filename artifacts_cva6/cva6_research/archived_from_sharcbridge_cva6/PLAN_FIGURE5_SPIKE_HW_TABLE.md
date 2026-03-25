# Plan Figure 5 + Spike Hardware Table

## Objetivo

Extender el flujo actual de `Figure 5` en `CVA6/Spike` para que, además de generar la figura, exporte una tabla con todas las métricas hardware y de ejecución **realmente disponibles** en el backend actual.

La tabla debe dejar claro:

- qué métricas vienen de `Spike/CVA6`
- qué métricas vienen del runtime/solver MPC
- qué métricas **no** están disponibles en `Spike` y no deben simularse ni inventarse

## Alcance

Se reutiliza el flujo actual:

- `SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp`
- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`
- `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`

No se toca `sharc_original`.

Los tests, muestras y evidencias irán en `artifacts_cva6/`.

## Métricas disponibles hoy

### Métricas arquitectónicas del backend actual

Estas ya salen del runtime en `RISC-V`:

- `cycles`
- `instret`
- `cpi`
- `ipc`

Origen:

- `SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp`

### Métricas del solver/controlador

Estas ya salen de `libmpc/OSQP` y del metadata del controlador:

- `iterations`
- `cost`
- `solver_status`
- `solver_status_msg`
- `is_feasible`
- `constraint_error`
- `dual_residual`
- `status`

Origen:

- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- metadata del runtime MPC

### Métricas de integración/tiempo host

Estas no son métricas hardware puras, pero son útiles para contexto:

- `t_delay`
- `scaled_cycles_for_delay`
- `chip_cycle_time_ns_effective`
- `backend_mode`

Origen:

- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`

## Métricas no disponibles en Spike hoy

Estas métricas no deben figurar como si fueran reales mientras el backend siga siendo `Spike`:

- `imiss`
- `ld_stall`
- `jmp_stall`
- `stall_total`
- `branch`
- `taken_branch`
- misses/latencias de caché
- occupancy del pipeline
- stalls microarquitectónicos realistas

Estas columnas solo podrían aparecer como:

- `N/A`
- o no aparecer

## Resultado esperado

Al terminar `run_cva6_figure5_tcp.sh`, el run debe generar además de `plots.png`:

- `latest/hw_metrics_spike.json`
- `latest/hw_metrics_spike.csv`
- `latest/hw_metrics_spike.md`
- opcionalmente `latest/hw_metrics_spike.png`

La tabla debe resumir por experimento de Figure 5, por ejemplo:

- `baseline-no-delay-onestep`
- `cva6-real-delays`

## Tareas

### T0. Congelar el contrato de métricas

Objetivo:

- fijar exactamente qué columnas se van a exportar
- separar métricas disponibles y no disponibles

Trabajo:

- definir el schema del fichero final
- documentar columnas obligatorias y opcionales
- marcar explícitamente las columnas `N/A` si se mantienen por compatibilidad

Salida:

- `artifacts_cva6/t0_hw_schema.md`

Criterio de paso:

- existe una lista cerrada de columnas
- no hay ambigüedad sobre si una métrica viene de `Spike`, del solver o del host

### T1. Reutilizar/adaptar el colector de métricas existente

Objetivo:

- aprovechar la lógica ya existente en `SHARCBRIDGE/scripts/collect_run_hw_metrics.py`

Trabajo:

- decidir si se reutiliza tal cual o si se crea un colector específico para CVA6
- si se adapta, el colector debe:
  - leer `simulation_data_incremental.json`
  - exportar solo métricas válidas para `Spike`
  - no prometer métricas GVSoC que aquí no existen

Implementación esperada:

- preferible: nuevo script principal en `SHARCBRIDGE_CVA6/collect_spike_hw_metrics.py`
- alternativa: reutilizar el script de `SHARCBRIDGE/` con un modo `--backend spike`

Salida:

- script funcional de recolección
- `artifacts_cva6/t1_collector_smoke.*`

Criterio de paso:

- el colector genera `json/csv/md` a partir de un run real ya existente

### T2. Definir la tabla final

Objetivo:

- dejar una tabla útil y estable para Figure 5

Columnas mínimas recomendadas:

- `mode`
- `label`
- `n_samples`
- `cycles_mean`
- `cycles_p95`
- `cycles_max`
- `instret_mean`
- `instret_p95`
- `instret_max`
- `cpi_mean`
- `ipc_mean`
- `iterations_mean`
- `iterations_p95`
- `iterations_max`
- `cost_mean`
- `delay_mean_ms`
- `delay_p95_ms`
- `delay_max_ms`
- `solver_status_counts`
- `feasible_ratio`
- `constraint_error_mean`
- `dual_residual_mean`
- `source`

Columnas opcionales:

- `scaled_cycles_mean`
- `backend_mode`
- `chip_cycle_time_ns_effective`

Criterio de paso:

- la tabla refleja solo métricas reales del flujo actual

### T3. Integrar el colector en Figure 5

Objetivo:

- que `run_cva6_figure5_tcp.sh` exporte la tabla automáticamente al final del run

Trabajo:

- enganchar el colector tras la generación del experimento
- escribir salidas en `latest/`
- dejar trazas claras por consola con rutas de salida

Archivos tocados esperados:

- `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
- script colector elegido

Salida:

- `latest/hw_metrics_spike.json`
- `latest/hw_metrics_spike.csv`
- `latest/hw_metrics_spike.md`
- opcional `latest/hw_metrics_spike.png`

Criterio de paso:

- un run completo de Figure 5 deja los artefactos hardware sin intervención manual

### T4. Validación de contenido

Objetivo:

- comprobar que la tabla no mezcla métricas incompatibles ni deja valores absurdos

Trabajo:

- validar que `cycles`, `instret`, `cpi`, `ipc` tienen sentido
- validar que las medias y percentiles usan `pending_computation.metadata`
- validar que `solver_status_counts` cuadra con el número de snapshots
- validar que no aparecen métricas GVSoC inventadas

Salida:

- `artifacts_cva6/t4_hw_table_validation.md`

Criterio de paso:

- la tabla es consistente con el run real

### T5. Decisión final de presentación

Objetivo:

- decidir qué se deja como salida oficial de Figure 5 en Spike

Opciones:

1. solo `hw_metrics_spike.md/csv/json`
2. además `hw_metrics_spike.png`
3. una tabla compacta y otra extendida

Recomendación:

- dejar `md + csv + json`
- y `png` solo si aporta lectura rápida real

Salida:

- `artifacts_cva6/t5_final_presentation.md`

Criterio de paso:

- queda fijado el formato oficial del resumen hardware para Figure 5

## Decisión técnica importante

La tabla debe representar **lo que Spike ofrece de verdad**, no lo que ofrecería un simulador microarquitectónico.

Por tanto:

- sí: `cycles`, `instret`, `cpi`, `ipc`, solver metrics y delays efectivos
- no: misses de caché, stalls y contadores de branch si no se obtienen realmente en este backend

## Siguiente implementación recomendada

Orden:

1. `T0`
2. `T1`
3. `T3`
4. `T4`
5. `T5`

La prioridad real es que `run_cva6_figure5_tcp.sh` deje una tabla útil al final del run sin romper el flujo ya validado.
