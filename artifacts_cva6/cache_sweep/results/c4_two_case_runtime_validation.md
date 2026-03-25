# C4 Two-Case Runtime Validation

Fecha: 2026-03-25

- estado: `PASS`

## Casos ejecutados

1. `baseline`

- label: `c4-baseline-cleanmachine`
- modo: `spike_persistent`
- `spike_cache_args`: vacío
- evidencia:
  - [c4-baseline-cleanmachine.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/c4-baseline-cleanmachine.md)
- resultado:
  - `PASS`

2. `cache_1mb`

- label: `c4-cache-smoke-1mb-cleanmachine`
- modo: `spike_persistent`
- `spike_cache_args`:
  - `--ic=128:4:64 --dc=128:4:64 --l2=4096:4:64`
- evidencia:
  - [c4-cache-smoke-1mb-cleanmachine.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/c4-cache-smoke-1mb-cleanmachine.md)
- resultado:
  - `PASS`

## Hallazgos

- con la máquina limpia de procesos `spike` huérfanos, el caso `1 MB` deja de atascarse
- el guest con `cachesim` sí llega a:
  - `Starting sshd: OK`
  - `NFS preparation skipped, OK`
  - prompt `#`
- fue necesario hacer configurable la ventana de `shell ready` en el launcher:
  - `CVA6_SPIKE_SHELL_READY_ATTEMPTS`
  - `CVA6_SPIKE_SHELL_PROMPT_TIMEOUT_S`
  - `CVA6_SPIKE_SHELL_MARKER_TIMEOUT_S`
- esto no cambia el baseline cuando no se usan esas variables

## Métricas comparativas

- baseline:
  - `t_delay = 55.47926734999055`
  - `cycles = 3156171`
  - `spike_cache_args = ""`
- 1 MB:
  - `t_delay = 237.16601731203264`
  - `cycles = 3156171`
  - `spike_cache_args = "--ic=128:4:64 --dc=128:4:64 --l2=4096:4:64"`

## Interpretación

- el gate runtime ya está demostrado para dos casos distintos
- la diferencia más visible de momento está en el tiempo host del backend, no en los contadores reportados por el runtime
- para el barrido final habrá que recoger también estadísticas específicas del `cachesim` de `Spike`

## Integridad del baseline protegido

- hashes revalidados tras `C4`:
  - `spike_fw_payload.elf = 75f8d46a5e9ab5c840498543406196a36647a1e236285df7dbdb227cce328a19`
  - `vmlinux = e6ff4e686f6d0647073061302d1b73fda6c4b7f9ec9b7115fb260f05c650723a`
  - `Image = 7675861a576490a78da06c39b50ca73fc99e19b800546cb68595f2d88eb877b3`
  - `rootfs.cpio = fb19e9cc6ef1e1c55ebce3a170bf2ed4d2fb411e5672cc8e89bdf69640a1f205`
  - `spike = 99eb8993c4854acddc4161d9961661f77a442e40f0ef32837080cf45f0177c86`
- comparación con el manifest protegido:
  - sin cambios

## Conclusión

- `C4` queda en `PASS`
- el siguiente paso correcto es cerrar una matriz conservadora para el sweep y construir el runner sobre una máquina limpia y con puertos dedicados por caso
