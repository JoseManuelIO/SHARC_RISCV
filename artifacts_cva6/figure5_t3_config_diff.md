# CVA6 Figure 5 Config Diff

Reference:

- `sharc_original/examples/acc_example/simulation_configs/gvsoc_figure5.json`

Derived config:

- `SHARCBRIDGE_CVA6/cva6_figure5.json`

## Intentional differences

1. Label of experiment 1 is renamed from `GVSoC - Real Delays` to `CVA6 - Real Delays`.
2. The backend is `CVA6/Spike`, but the config keeps:
   - `use_gvsoc_controller = true`
   - `in-the-loop_delay_provider = "gvsoc"`

This is intentional. SHARC already routes external execution through the wrapper
selected by `use_gvsoc_controller`, and the current delay provider contract is
based on `gvsoc_cycles_<k>.txt`. Reusing that contract avoids modifying
`sharc_original`.

## Parameters kept identical

- `n_time_steps = 64`
- `only_update_control_at_sample_times = false`
- `prediction_horizon = 5`
- `control_horizon = 5`
- `output_cost_weight = 10000.0`
- `input_cost_weight = 0.01`
- `delta_input_cost_weight = 1.0`
- `enable_mpc_warm_start = false`
- `use_state_after_delay_prediction = false`

## Acceptance criterion

The config is valid if it differs only in backend identity and not in the
functional definition of the Figure 5 scenario.
