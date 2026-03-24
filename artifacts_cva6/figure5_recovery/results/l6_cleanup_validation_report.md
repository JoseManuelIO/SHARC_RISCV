# L6 Cleanup Validation Report

- fecha: `2026-03-24`
- estado: `PASS`

## Gates cubiertas

- `spike` oneshot smoke: `PASS`
  - [l6-cleanup-spike.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/l6-cleanup-spike.md)
- `spike_persistent` smoke: `PASS`
  - [r7_spike_persistent_probe.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r7_spike_persistent_probe.md)
- Figure 5 full run: `PASS`
  - [r8_figure5_clean_run_report.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r8_figure5_clean_run_report.md)
  - rerun simplificado:
    - [/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/experiment_list_data_incremental.json](/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/experiment_list_data_incremental.json)
    - [/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/plots.png](/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/plots.png)

## Resultado

- la limpieza no rompe el flujo funcional recuperado
- el run script ya resuelve `Spike` para el SDK limpio
- el backend ya no depende de reuse ambiguo por puerto

## Nota

- el smoke persistente previo sigue siendo valido para `L6` porque los cambios de esta fase no tocaron la ejecucion del snapshot, solo `health` y la logica bash de reuse/seleccion de `Spike`
