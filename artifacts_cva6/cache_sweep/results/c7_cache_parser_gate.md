# C7 Cache Parser Gate

Fecha: 2026-03-25

- estado: `PASS`

## Hallazgo principal

- el `Spike` local soporta `--log-cache-miss`
- en la práctica observada, este build no emite un resumen final tipo:
  - `Read Accesses`
  - `Write Accesses`
  - `Miss Rate`
  - `Writebacks`
  - `Bytes Read/Written`
- lo que sí emite de forma fiable son eventos crudos de miss como:
  - `I$ read miss 0x...`
  - `D$ read miss 0x...`
  - `D$ write miss 0x...`

## Parser implementado

- script:
  - [parse_spike_cache_miss_log.py](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/scripts/parse_spike_cache_miss_log.py)

## Gate ejecutado

- entrada real:
  - `/tmp/sharcbridge_cva6_runtime/r6-runtime-probe.log`
- args asociados:
  - `--ic=4:4:64 --dc=4:4:64 --l2=128:4:64 --log-cache-miss`
- salidas:
  - [c7_cache_miss_probe.json](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/c7_cache_miss_probe.json)
  - [c7_cache_miss_probe.csv](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/c7_cache_miss_probe.csv)
  - [c7_cache_miss_probe.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/c7_cache_miss_probe.md)

## Resultado validado

- filas útiles:
  - `I$ read`
  - `D$ read`
  - `D$ write`
- resumen del probe:
  - `total_miss_events = 222598`
  - `I$ read miss_count = 68164`
  - `D$ read miss_count = 8551`
  - `D$ write miss_count = 145883`

## Métricas disponibles

- `miss_count`
- `unique_addr_count`
- `block_bytes`
- `estimated_linefill_bytes`

## Métricas no disponibles de forma nativa en este build observado

- `Read Accesses`
- `Write Accesses`
- `Miss Rate`
- `Writebacks`
- `Bytes Read/Written` exactos del simulador

## Interpretación

- para esta línea de trabajo, el comportamiento de caché se puede comparar de forma robusta con:
  - misses por tipo de caché
  - misses por tipo de operación
  - proxy de tráfico por línea (`estimated_linefill_bytes`)
- si en una fase posterior aparece un build de `Spike` que sí imprima resúmenes agregados, este parser se puede extender, pero no hace falta para avanzar ahora

## Conclusión

- `C7` queda en `PASS`
- el siguiente paso correcto es `C8`: ejecutar el sweep con la matriz aprobada y combinar:
  - métricas runtime por run
  - métricas de miss cuando se use `--log-cache-miss`
