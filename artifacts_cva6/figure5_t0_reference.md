# Figure 5 Reference Freeze

## Scope

This document freezes the functional reference for the `SHARC + CVA6` Figure 5 flow.

Reference source:

- `sharc_original/examples/acc_example/simulation_configs/gvsoc_figure5.json`

## Experiments to reproduce

1. `CVA6 - Real Delays`
2. `Baseline - No Delay (Onestep)`

The new flow keeps the same two-branch experiment structure as the GVSoC Figure 5 flow.

## MPC parameters that must remain unchanged

- `n_time_steps = 64`
- `prediction_horizon = 5`
- `control_horizon = 5`
- `output_cost_weight = 10000.0`
- `input_cost_weight = 0.01`
- `delta_input_cost_weight = 1.0`
- `enable_mpc_warm_start = false`
- `use_state_after_delay_prediction = false`
- `only_update_control_at_sample_times = false`

## MPC stack that must run inside RISC-V

- `sharc_original/resources/controllers/src/ACC_Controller.cpp`
- `sharc_original/libmpc`
- `CVA6_LINUX/deps/eigen`
- `CVA6_LINUX/deps/osqp`

## Numerical policy

Priority is fidelity over speed.

Required solver policy:

- `adaptive_rho = true`
- `adaptive_rho_interval = 25`
- `profiling = on`

## SHARC compatibility rule

`sharc_original` must not be modified.

Therefore, the real-delay path must remain compatible with SHARC's current
`GVSoCDelayProvider` contract:

- experiment uses `in-the-loop_delay_provider = "gvsoc"`
- wrapper/backend must emit `gvsoc_cycles_<k>.txt`

The file naming remains legacy for compatibility, even though the backend is
`CVA6/Spike` and not `GVSoC`.

## Output equivalence targets

The new flow must be checked against the host/original controller for:

- control action `u`
- `solver_status`
- `iterations`
- `cost`
- feasibility
- delay consistency

## Pass condition for the Figure 5 flow

The flow passes when:

1. both Figure 5 experiments run end-to-end
2. the controller is executed inside `RISC-V/CVA6`
3. SHARC consumes baseline and real-delay branches without code changes
4. the functional behaviour remains aligned with the reference stack
