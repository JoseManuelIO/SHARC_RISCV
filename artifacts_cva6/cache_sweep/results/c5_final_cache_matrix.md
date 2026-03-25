# C5 Final Cache Matrix

Fecha: 2026-03-25

- estado: `PASS`

## Matriz principal

- archivo:
  - [cache_sweep_matrix.json](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/configs/cache_sweep_matrix.json)

## Casos aprobados para fase 1

1. `baseline`

- `spike_cache_args=""`
- propósito:
  - referencia sin `cachesim`

2. `cache_1mb`

- `--ic=128:4:64 --dc=128:4:64 --l2=4096:4:64`
- propósito:
  - punto conservador ya validado en runtime

3. `cache_262kb`

- `--ic=32:4:64 --dc=32:4:64 --l2=1024:4:64`
- propósito:
  - punto medio alineado con SHARC original

4. `cache_32kb`

- `--ic=4:4:64 --dc=4:4:64 --l2=128:4:64`
- propósito:
  - punto pequeño alineado con SHARC original

## Política de seguridad de la matriz

- no se incluye `--log-cache-miss` en la matriz principal de runtime
- `--log-cache-miss` se reserva para una fase posterior de extracción/parsing, cuando el runner ya esté estabilizado
- no se introduce explosión combinatoria de asociatividad o block size en esta fase

## Smoke matrix

- archivo:
  - [cache_sweep_matrix_smoke.json](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/configs/cache_sweep_matrix_smoke.json)
- queda reducida a:
  - `baseline`
  - `cache_1mb`

## Justificación

- `C4` ya validó `baseline` y `cache_1mb` en runtime real
- la smoke matrix debe reutilizar el punto más conservador ya demostrado
- la matriz principal mantiene los tres tamaños representativos sin añadir complejidad innecesaria

## Conclusión

- `C5` queda en `PASS`
- la siguiente tarea correcta es construir el runner seguro sobre esta matriz
