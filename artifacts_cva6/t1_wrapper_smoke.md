# T1 Wrapper Smoke

## Estado

`PASS`

## Comprobaciones

- El wrapper se importa correctamente.
- `PipeController.read_vector()` parsea el formato SHARC esperado.
- `PipeController.write_vector()` mantiene el formato wire `[v0, v1]`.
- `build_run_snapshot_request()` genera una peticion TCP valida para CVA6.
- `normalize_backend_response()` produce `u` y `metadata` compatibles con SHARC.

## Evidencia

- contrato: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/t1_wrapper_contract.json`
