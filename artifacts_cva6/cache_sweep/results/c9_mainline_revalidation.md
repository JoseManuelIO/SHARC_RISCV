# C9 Mainline Revalidation

- Date: 2026-03-25
- Status: PASS
- Command: `bash /home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
- Mode: default simple entrypoint, without `SPIKE_CACHE_ARGS`

## Result

- The mainline Figure 5 command completed successfully after the cache sweep work.
- Output directory:
  - `/tmp/sharc_cva6_figure5/2026-03-25--13-58-54-cva6_figure5`
- Final outputs present:
  - `/tmp/sharc_cva6_figure5/2026-03-25--13-58-54-cva6_figure5/latest/experiment_list_data_incremental.json`
  - `/tmp/sharc_cva6_figure5/2026-03-25--13-58-54-cva6_figure5/latest/plots.png`
- Both Figure 5 experiment branches completed with `status_py_to_c++ = FINISHED`:
  - `baseline-no-delay-onestep`
  - `cva6-real-delays`

## Gate Check

- The command used the protected default route:
  - SDK dir: `/tmp/cva6-sdk-clean-20260324-r1-2`
  - Spike bin: `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/bin/spike`
  - Spike payload: `/tmp/cva6-sdk-clean-20260324-r1-2/install64/spike_fw_payload.elf`
- No rebuild was triggered.
- The cache sweep work did not break the main Figure 5 flow.

## Conclusion

- `C9` passes.
- The repository now supports:
  - the simple main Figure 5 command
  - the isolated cache sweep flow under `artifacts_cva6/cache_sweep/`
- Both coexist without modifying the protected payload.
