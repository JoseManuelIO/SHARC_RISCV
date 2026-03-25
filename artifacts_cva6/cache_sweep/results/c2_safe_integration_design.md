# C2 Safe Integration Design

- fecha: `2026-03-25`
- estado: `PASS`

## Diseño elegido

La reintegración mínima y segura se hará con una sola interfaz:

- variable de entorno `SPIKE_CACHE_ARGS`

## Punto de inyección

- reintroducir la inyección en [cva6_runtime_launcher.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_runtime_launcher.py)
- no tocar el `payload`
- no tocar `rootfs`, `vmlinux` ni `Image`
- no exigir ningún formato nuevo a la arquitectura principal

## Alcance exacto permitido

- aceptar args como:
  - `--ic=...`
  - `--dc=...`
  - `--l2=...`
  - `--log-cache-miss`
- añadir trazabilidad mínima en metadata/health:
  - `spike_cache_args`

## Restricciones

- con `SPIKE_CACHE_ARGS` vacío el comportamiento debe ser idéntico al baseline
- el runner experimental seguirá en `artifacts_cva6/cache_sweep/scripts/`
- no se harán rebuilds ni cambios de `SDK`

## Gate esperado para pasar a C3

- el diseño ya está lo bastante acotado como para implementar la inyección sin tocar artefactos protegidos
