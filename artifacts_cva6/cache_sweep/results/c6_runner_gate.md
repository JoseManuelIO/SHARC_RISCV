# C6 Runner Gate

Fecha: 2026-03-25

- estado: `PASS`

## Runner validado

- archivo:
  - [run_spike_cache_sweep.sh](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh)

## Endurecimiento aplicado

- matriz por defecto:
  - [cache_sweep_matrix_smoke.json](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/configs/cache_sweep_matrix_smoke.json)
- puerto por caso:
  - `CACHE_SWEEP_BASE_PORT=5040`
  - `baseline -> 5040`
  - `cache_1mb -> 5041`
- `skip build` por defecto:
  - `CVA6_SKIP_BUILD=1`
- `SDK` bueno por defecto:
  - `/tmp/cva6-sdk-clean-20260324-r1-2`
- modo por defecto:
  - `spike_persistent`
- timeouts de shell listos para `cachesim`

## Gate ejecutado

Se lanzó el runner smoke con:

- `baseline`
- `cache_1mb`

Resultado:

- `baseline`: `PASS`
  - log:
    - [baseline.log](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/baseline.log)
  - out dir:
    - `/tmp/sharc_cva6_figure5/2026-03-25--12-45-18-cva6_figure5`
- `cache_1mb`: `PASS`
  - log:
    - [cache_1mb.log](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/cache_1mb.log)
  - out dir:
    - `/tmp/sharc_cva6_figure5/2026-03-25--12-47-37-cva6_figure5`

## Evidencia final

- manifest agregado:
  - [cache_sweep_manifest.json](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/cache_sweep_manifest.json)
- outputs del caso `cache_1mb`:
  - [/tmp/sharc_cva6_figure5/2026-03-25--12-47-37-cva6_figure5/latest/experiment_list_data_incremental.json](/tmp/sharc_cva6_figure5/2026-03-25--12-47-37-cva6_figure5/latest/experiment_list_data_incremental.json)
  - [/tmp/sharc_cva6_figure5/2026-03-25--12-47-37-cva6_figure5/latest/plots.png](/tmp/sharc_cva6_figure5/2026-03-25--12-47-37-cva6_figure5/latest/plots.png)

## Integridad del baseline protegido

- hashes después del gate:
  - `spike_fw_payload.elf = 75f8d46a5e9ab5c840498543406196a36647a1e236285df7dbdb227cce328a19`
  - `vmlinux = e6ff4e686f6d0647073061302d1b73fda6c4b7f9ec9b7115fb260f05c650723a`
  - `Image = 7675861a576490a78da06c39b50ca73fc99e19b800546cb68595f2d88eb877b3`
  - `rootfs.cpio = fb19e9cc6ef1e1c55ebce3a170bf2ed4d2fb411e5672cc8e89bdf69640a1f205`
  - `spike = 99eb8993c4854acddc4161d9961661f77a442e40f0ef32837080cf45f0177c86`
- comparación con el manifest protegido:
  - sin cambios

## Conclusión

- `C6` queda en `PASS`
- el runner ya ejecuta varios casos sin rebuilds, con puertos separados y manifest claro
- el siguiente paso correcto es `C7`: parsear estadísticas específicas del `cachesim` de `Spike`
