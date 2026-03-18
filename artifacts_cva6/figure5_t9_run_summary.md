# Figure 5 CVA6 Run Summary

## Status

`PASS`

## Main run

- script: `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
- backend mode: `spike_persistent`
- run dir: `/tmp/sharc_cva6_figure5/2026-03-18--10-38-18-cva6_figure5`

## Output checks

- `latest/plots.png`: present
- `latest/experiment_list_data_incremental.json`: present
- `cva6-real-delays/simulation_data_incremental.json`: present
- `baseline-no-delay-onestep/simulation_data_incremental.json`: present

## Experiment coverage

- `cva6-real-delays`
  - `len_k = 256`
  - `pending = 256`
  - `last_k = 63`

- `baseline-no-delay-onestep`
  - `len_k = 256`
  - `pending = 256`
  - `last_k = 63`

## Key implementation result

The critical blocker for Figure 5 was not MPC correctness but backend execution
mode. A one-shot `Spike + Linux` boot per snapshot made the run impractical.

The working solution is:

- `CVA6RuntimeLauncher(mode="spike_persistent")`

This reuses one booted `Spike` session and sends multiple snapshots through the
same guest session.

## Time-axis alignment

The config now uses:

- `n_time_steps = 64`

with SHARC sample time:

- `sample_time = 0.2`

so the generated time axis matches the original SHARC figure duration:

- `64 * 0.2 = 12.8 s`

## Delay compatibility

The run generated `gvsoc_cycles_<k>.txt` in the `cva6-real-delays` experiment,
so SHARC consumed real delays through its existing `GVSoCDelayProvider`
contract without modifying `sharc_original`.
