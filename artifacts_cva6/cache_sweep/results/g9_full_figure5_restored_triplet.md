# G9 Full Figure5 Restored Triplet

- date: `2026-03-27`
- status: `PASS`

## Goal

Validate the full `Figure 5` flow end-to-end using a single SDK root:

- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk`

with the restored bootable triplet resident inside:

- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/`

## Command

```bash
CVA6_PORT=5120 \
CVA6_SKIP_BUILD=1 \
CVA6_RUNTIME_MODE=spike_persistent \
CVA6_SDK_DIR=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk \
bash /home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh
```

## Run

- output directory: `/tmp/sharc_cva6_figure5/2026-03-27--10-57-30-cva6_figure5`
- final bundle: `/tmp/sharc_cva6_figure5/2026-03-27--10-57-30-cva6_figure5/latest/experiment_list_data_incremental.json`
- final plot: `/tmp/sharc_cva6_figure5/2026-03-27--10-57-30-cva6_figure5/latest/plots.png`

## Validation

Produced experiment outputs:

- `/tmp/sharc_cva6_figure5/2026-03-27--10-57-30-cva6_figure5/2026-03-27--02-57-32--cva6-figure5/cva6-real-delays/simulation_data_incremental.json`
- `/tmp/sharc_cva6_figure5/2026-03-27--10-57-30-cva6_figure5/2026-03-27--02-57-32--cva6-figure5/baseline-no-delay-onestep/simulation_data_incremental.json`

Both experiments complete with:

- `unique_k = 64`
- `max_k = 63`
- `t_last = 12.8`

The persistent backend crossed the previous failure point cleanly:

- `request_id=0` completed
- later requests advanced at least through `request_id=48` during live inspection
- the run reached `[4/6] Checking outputs`, `[5/6] Building latest experiment bundle`, and `[6/6] Generating plots`

## Interpretation

This confirms the practical durable fix:

- keep the bootable `#6` triplet inside `CVA6_LINUX/cva6-sdk/install64/`
- keep runtime/config/libs inside `CVA6_LINUX/cva6-sdk/buildroot/output/target/`
- run the flow from that single SDK root

The failed rebuilt `#37` triplet was the blocker. The restored triplet removes the boot instability that had been stopping `request_id=0`.

## Gate

`PASS`.
