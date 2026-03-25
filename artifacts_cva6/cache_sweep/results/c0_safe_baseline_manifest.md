# C0 Safe Baseline Manifest

- fecha: `2026-03-25`
- estado: `PASS`

## Baseline protegido

- comando: `./run_cva6_figure5_tcp.sh`
- validación base:
  - [s5_simple_flow_validation.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/s5_simple_flow_validation.md)
- run de referencia:
  - [/tmp/sharc_cva6_figure5/2026-03-25--10-32-09-cva6_figure5/latest/experiment_list_data_incremental.json](/tmp/sharc_cva6_figure5/2026-03-25--10-32-09-cva6_figure5/latest/experiment_list_data_incremental.json)
  - [/tmp/sharc_cva6_figure5/2026-03-25--10-32-09-cva6_figure5/latest/plots.png](/tmp/sharc_cva6_figure5/2026-03-25--10-32-09-cva6_figure5/latest/plots.png)

## Rutas protegidas

- `SDK dir`: `/tmp/cva6-sdk-clean-20260324-r1-2`
- `Spike bin`: `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/bin/spike`

## Hashes congelados

- `spike_fw_payload.elf`: `75f8d46a5e9ab5c840498543406196a36647a1e236285df7dbdb227cce328a19`
- `vmlinux`: `e6ff4e686f6d0647073061302d1b73fda6c4b7f9ec9b7115fb260f05c650723a`
- `Image`: `7675861a576490a78da06c39b50ca73fc99e19b800546cb68595f2d88eb877b3`
- `rootfs.cpio`: `fb19e9cc6ef1e1c55ebce3a170bf2ed4d2fb411e5672cc8e89bdf69640a1f205`
- `spike`: `99eb8993c4854acddc4161d9961661f77a442e40f0ef32837080cf45f0177c86`

## Gate

- existe baseline único y validado antes de tocar integración de caché
- existe manifest reproducible para detectar cualquier deriva del payload protegido
