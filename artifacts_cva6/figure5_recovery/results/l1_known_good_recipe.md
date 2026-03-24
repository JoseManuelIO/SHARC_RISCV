# L1 Known Good Recipe

- fecha: `2026-03-24`
- estado: `PASS`

## Receta minima reproducible

```bash
CVA6_PORT=5017 \
CVA6_SKIP_BUILD=1 \
CVA6_RUNTIME_MODE=spike_persistent \
CVA6_SDK_DIR=/tmp/cva6-sdk-clean-20260324-r1-2 \
bash /home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh
```

## Lo que queda fijado

- `CVA6_RUNTIME_MODE=spike_persistent`
- `CVA6_SDK_DIR=/tmp/cva6-sdk-clean-20260324-r1-2`
- `CVA6_SPIKE_PAYLOAD=/tmp/cva6-sdk-clean-20260324-r1-2/install64/spike_fw_payload.elf`
- `CVA6_SPIKE_BIN` ya no hace falta pasarlo a mano para esta receta
- usar puerto nuevo cuando se quiera aislar una validacion

## Run bueno validado

- [r8_figure5_clean_run_report.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r8_figure5_clean_run_report.md)
- rerun limpio con recipe simplificada:
  - out dir: `/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5`
  - bundle: [/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/experiment_list_data_incremental.json](/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/experiment_list_data_incremental.json)
  - plot: [/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/plots.png](/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/plots.png)

## Gate

- existe una receta corta y reproducible
- la receta ya no depende de recordar `CVA6_SPIKE_BIN` manualmente
