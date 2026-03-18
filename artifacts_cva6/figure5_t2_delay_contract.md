# CVA6 Figure 5 Delay Contract

## Goal

Make SHARC consume real delays from the `CVA6/Spike` backend without modifying
`sharc_original`.

## Compatibility rule

SHARC's current real-delay branch uses `GVSoCDelayProvider`, which waits for:

- `gvsoc_cycles_<k>.txt`

The `CVA6` backend now reuses that exact file contract on purpose.

## Implemented path

1. `SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp`
   - measures `cycles` and `instret` around `controller.calculateControl(...)`
   - exports them inside runtime metadata

2. `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
   - propagates `cycles`, `instret`, `cpi`, `ipc` to the TCP response

3. `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`
   - receives raw `cycles`
   - scales them to SHARC's legacy 1.25ns delay contract
   - writes `gvsoc_cycles_<k>.txt` inside the simulation directory

4. `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
   - can pass `CVA6_CHIP_CYCLE_NS`
   - mirrors it to `GVSOC_CHIP_CYCLE_NS` so SHARC's provider reads the same effective cycle time

## Effective variables

- `CVA6_CHIP_CYCLE_NS`
- `GVSOC_CHIP_CYCLE_NS`

If only one is set, the Figure 5 run script mirrors it to the other for
consistency.

## Result

The `CVA6` backend is now compatible with the existing `gvsoc` delay provider
contract used by SHARC.
