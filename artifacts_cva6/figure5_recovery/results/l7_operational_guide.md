# L7 Operational Guide

- fecha: `2026-03-24`
- estado: `PASS`

## Como arrancar Figure 5 en limpio

```bash
CVA6_PORT=5017 \
CVA6_SKIP_BUILD=1 \
CVA6_RUNTIME_MODE=spike_persistent \
CVA6_SDK_DIR=/tmp/cva6-sdk-clean-20260324-r1-2 \
bash /home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh
```

## Que outputs mirar

- `latest/experiment_list_data_incremental.json`
- `latest/plots.png`
- `tcp_server.log`
- `sharc_figure5.log`

## Cuando usar puerto nuevo

- al cambiar de `SDK`
- al cambiar de `payload`
- al comparar ramas o estados distintos
- cuando se quiera aislar una validacion

## Que se puede borrar sin riesgo

- runs viejos en `/tmp/sharc_cva6_figure5/*`
- logs temporales en `/tmp/sharcbridge_cva6_runtime/*`
- backups binarios de forense ya archivados fuera del commit funcional

## Que conviene conservar

- [l1_known_good_recipe.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/l1_known_good_recipe.md)
- [l6_cleanup_validation_report.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/l6_cleanup_validation_report.md)
- [r8_figure5_clean_run_report.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r8_figure5_clean_run_report.md)
