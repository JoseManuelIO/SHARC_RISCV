# MPC Original Spec (T7.1)

- Generated: `2026-02-23T10:21:46.661762`
- Scope: `ACC_Controller.cpp/.h` + `controller.h` + `base_config.json`

## Numeric Model
- Vector types in original controller are `double`-precision Eigen matrices (`xVec/uVec/wVec/yVec`).
- LMPC backend uses `double` types (`mpc::mat`, `mpc::cvec`).

## Plant/Model Parameters (from base config)
- `mass` = `2044`
- `v_des` = `15`
- `d_min` = `6.0`
- `v_max` = `20`
- `F_accel_max` = `4880`
- `F_brake_max` = `6507`
- `max_brake_acceleration` = `3.2`
- `max_brake_acceleration_front` = `5.0912`
- `beta` = `339.1329`
- `gamma` = `0.77`

## Optimization Setup
- Controller class: `ACC_Controller` using `LMPC<Tnx,Tnu,Tndu,Tny,prediction_horizon,control_horizon>`.
- Prediction horizon: `5`
- Control horizon: `5`
- Objective weights: output=`10000.0`, input=`0.01`, delta_input=`1.0`
- Optimizer options set via OSQP parameters (`eps_rel`, `eps_abs`, `eps_prim_inf`, `eps_dual_inf`, `maximum_iteration`, warm start flag).

## Dynamics Linearization and Disturbances
- Continuous A/B are updated per step using current velocity `v0` (online linearization).
- Disturbance model includes front-vehicle estimate series `w_series` and friction offset via `k = beta - gamma*v0^2` in controller model.
- Discretization uses `mpc::discretization(...)` utility.

## Constraints
- Input bounds: `0 <= F_accel <= F_accel_max`, `0 <= F_brake <= F_brake_max`.
- State bounds: `p >= 0`, `h >= d_min`, `0 <= v <= v_max`.
- Output bounds: `0 <= v <= v_max`.
- Terminal scalar safety constraint uses braking model and worst-case front velocity at prediction horizon.

## Outputs/Metadata
- Uses LMPC optimize step result fields: iterations, solver status/message, feasibility, cost, primal/dual residual, status enum string.

## Traceability References
- `sharc_original/resources/controllers/include/controller.h` (double vector typedefs).
- `sharc_original/resources/controllers/include/ACC_Controller.h` (LMPC and parameters).
- `sharc_original/resources/controllers/src/ACC_Controller.cpp` (setup, constraints, objective, terminal constraint).
- `sharc_original/examples/acc_example/base_config.json` (numerical values).