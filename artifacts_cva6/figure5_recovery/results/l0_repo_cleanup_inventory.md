# L0 Repo Cleanup Inventory

- fecha: `2026-03-24`
- estado: `PASS`

## Cambios necesarios para Figure 5

- [cva6_runtime_launcher.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_runtime_launcher.py)
- [cva6_tcp_server.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_tcp_server.py)
- [run_cva6_figure5_tcp.sh](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh)
- [figure5_recovery](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery)

## Evidencia y artifacts de la recuperacion

- [README.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/README.md)
- [PLAN.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/PLAN.md)
- [COMPARISON_PLAN.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/COMPARISON_PLAN.md)
- [REINSTALL_PLAN.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/REINSTALL_PLAN.md)
- [CLEANUP_PLAN.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/CLEANUP_PLAN.md)
- `results/` y `scripts/` de `figure5_recovery`

## Cambios ajenos o no necesarios para cerrar Figure 5

- [PLAN_FIGURE5_SPIKE_HW_TABLE.md](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/PLAN_FIGURE5_SPIKE_HW_TABLE.md)
- [collect_spike_hw_metrics.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/collect_spike_hw_metrics.py)
- [PLAN_SPIKE_CACHE_SWEEP_FIGURE5.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/PLAN_SPIKE_CACHE_SWEEP_FIGURE5.md)
- [PLAN_SPIKE_FIGURE5_EXECUTION_TASKS.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/PLAN_SPIKE_FIGURE5_EXECUTION_TASKS.md)
- [cache_sweep](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep)
- [tmp](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/tmp)

## Subrepos o submodules sucios que no se deben mezclar con esta limpieza

- `CVA6_LINUX/cva6`
- `CVA6_LINUX/cva6-sdk`
- `CVA6_LINUX/deps/osqp`
- `PULP/dory`
- `PULP/gvsoc`
- `PULP/pulp-riscv-gnu-toolchain`
- `PULP/pulp-sdk`
- `sharc_original`

## Gate

- existe una clasificacion cerrada entre superficie minima del flujo, evidencia de recuperacion y suciedad ajena
- no hace falta tocar los subrepos sucios para dejar Figure 5 funcional
