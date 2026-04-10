# Mainline Status

## Estado actual

- estado global: `PASS`
- fecha de consolidacion: `2026-04-07`
- flujo principal preservado:
  - `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
  - `artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh`

## Que queda en `artifacts_cva6`

- `cache_sweep/`: flujo operativo actual del barrido de caches y su ultima publicacion valida
- este documento: resumen ejecutivo del estado mainline
- un conjunto reducido de `.md` historicos que se conservan porque siguen enlazados desde `Documentacion/presentacion_ricardo/`

## Figure 5 principal

Validacion reciente:

- script: `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
- fecha: `2026-04-07`
- resultado: `PASS`

Artefactos confirmados en la ultima corrida validada:

- `latest/plots.png`
- `latest/experiment_list_data_incremental.json`

## Cache sweep

Validacion reciente:

- script: `artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh`
- fecha: `2026-04-07`
- resultado: `PASS`

Casos ejecutados:

- `baseline`
- `cache_1mb`
- `cache_262kb`
- `cache_32kb`

Salidas vigentes:

- [cache_latest_report.json](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/latest/cache_latest_report.json)
- [experiment_list_data_incremental.json](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/latest/experiment_list_data_incremental.json)
- [plot_cache.png](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/latest/plot_cache.png)
- [cache_sweep_manifest.json](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/cache_sweep_manifest.json)

## Decisiones tecnicas que siguen vigentes

- arquitectura base:
  - `SHARC -> wrapper compatible -> TCP server -> launcher CVA6 -> runtime MPC`
- modo de ejecucion operativo para Figure 5:
  - `spike_persistent`
- `cache_sweep/` queda como el unico subarbol experimental conservado dentro de `artifacts_cva6`

## Politica de limpieza aplicada

- se eliminaron ramas historicas pesadas como `figure5_recovery/`, `cva6_research/` y `tmp/`
- se retiraron probes, planes y reportes intermedios que no participan en el flujo actual
- no se toco `Documentacion/presentacion_ricardo/`
- no se borraron los `.md` de `artifacts_cva6` que esa carpeta sigue enlazando

## Documentos recomendados

- [README.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/README.md)
- [cache_sweep/README.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/README.md)
- [SPIKE_SHARC_CAPABILITIES_AND_CARTPOLE_PLAN.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/SPIKE_SHARC_CAPABILITIES_AND_CARTPOLE_PLAN.md)
