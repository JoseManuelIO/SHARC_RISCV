# C1 Cache Integration Audit

- fecha: `2026-03-25`
- estado: `PASS`

## Objetivo auditado

Comprobar si la integración antigua de caché sigue viva en la ruta principal
actual.

## Hallazgo principal

La integración antigua descrita en:

- [t3_integration_design.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/t3_integration_design.md)
- [t4_injection_validation.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/t4_injection_validation.md)

ya no coincide con el código actual de:

- [cva6_runtime_launcher.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_runtime_launcher.py)

## Evidencia

- el runner experimental todavía pasa `SPIKE_CACHE_ARGS`
  - [run_spike_cache_sweep.sh](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh)
- pero el launcher principal actual:
  - no define `SPIKE_CACHE_ARGS`
  - no expone `_build_spike_host_command()`
  - sigue lanzando `Spike` con la forma fija `[str(SPIKE_BIN), str(SPIKE_PAYLOAD)]`

## Conclusión

- la ruta experimental no está conectada de forma efectiva a la ruta principal actual
- antes de cualquier sweep real hay que reintroducir la inyección mínima de caché
- esto confirma que el siguiente paso correcto es `C2`, no lanzar un barrido directo

## Gate

- queda cerrada la verdad actual del código
- no se ha tocado aún el baseline protegido
