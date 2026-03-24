# R8 Figure 5 Clean Run Report

- status: `PASS`
- out_dir: `/tmp/sharc_cva6_figure5/2026-03-24--16-33-22-cva6_figure5`
- latest_bundle: `/tmp/sharc_cva6_figure5/2026-03-24--16-33-22-cva6_figure5/latest/experiment_list_data_incremental.json`
- plot: `/tmp/sharc_cva6_figure5/2026-03-24--16-33-22-cva6_figure5/latest/plots.png`
- wrapper_log: `/tmp/sharc_cva6_figure5/2026-03-24--16-33-22-cva6_figure5/sharc_figure5.log`
- tcp_server_log: `/tmp/sharc_cva6_figure5/2026-03-24--16-33-22-cva6_figure5/tcp_server.log`

## Gate Result

- two `simulation_data_incremental.json` outputs were generated
- the latest experiment bundle was assembled
- plot generation completed

## Clean Backend Settings Used

- `CVA6_SKIP_BUILD=1`
- `CVA6_RUNTIME_MODE=spike_persistent`
- `CVA6_SDK_DIR=/tmp/cva6-sdk-clean-20260324-r1-2`
- `CVA6_SPIKE_BIN=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/bin/spike`
- `CVA6_SPIKE_PAYLOAD=/tmp/cva6-sdk-clean-20260324-r1-2/install64/spike_fw_payload.elf`
- `CVA6_PORT=5016`

## Minimal Fixes Required

- clean SDK reinstall through `R4`
- persistent launcher fix in `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py` so
  already-present guest assets do not require fresh `STAGE_*_SHA` lines
- explicit `CVA6_SPIKE_BIN` when using the clean SDK, because the isolated SDK
  rebuild did not include `install64/bin/spike`

## Interpretation

- the flow is recovered with the clean SDK payload and the minimal launcher fix
- the remaining cleanup, if desired later, is ergonomic:
  - either build `isa-sim` into the clean SDK
  - or make the figure-5 launcher path pass `CVA6_SPIKE_BIN` explicitly when
    `CVA6_SDK_DIR` points to an SDK without local Spike
