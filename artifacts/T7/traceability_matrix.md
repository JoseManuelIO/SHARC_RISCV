# MPC Traceability Matrix (T7.1)

- Generated: `2026-02-23`
- Goal: map every core element of the original MPC (`ACC_Controller.cpp`) to the current GVSoC implementation status.

## Matrix

| Element | Original Reference | GVSoC Reference | Status |
|---|---|---|---|
| Numeric scalar/vector precision | `sharc_original/resources/controllers/include/controller.h:24` | `SHARCBRIDGE/mpc/mpc_acc_controller.c:124` | `MISMATCH` (double -> float32) |
| MPC backend solver | `sharc_original/resources/controllers/src/ACC_Controller.cpp:119` | `SHARCBRIDGE/mpc/mpc_acc_controller.c:286` | `MISMATCH` (LMPC/OSQP vs grid+gradient) |
| Online linearization with current `v` | `sharc_original/resources/controllers/src/ACC_Controller.cpp:104` | `SHARCBRIDGE/mpc/mpc_acc_controller.c:188` | `PARTIAL` (state propagation present, not LMPC linearized model update) |
| Disturbance horizon `w_series` | `sharc_original/resources/controllers/src/ACC_Controller.cpp:111` | `SHARCBRIDGE/mpc/mpc_acc_controller.c:257` | `MISMATCH` (single-step `w`, no horizon disturbance matrix) |
| Discretization utility (`mpc::discretization`) | `sharc_original/resources/controllers/src/ACC_Controller.cpp:220` | `SHARCBRIDGE/mpc/mpc_acc_controller.c:196` | `MISMATCH` (Euler predictor, no explicit Ad/Bd/Bd_dist) |
| Objective weights (`Q,R,dR`) | `sharc_original/resources/controllers/src/ACC_Controller.cpp:258` | `SHARCBRIDGE/mpc/mpc_acc_controller.c:210` | `MISMATCH` (custom priority cost) |
| State/input/output bounds in optimizer | `sharc_original/resources/controllers/src/ACC_Controller.cpp:302` | `SHARCBRIDGE/mpc/mpc_acc_controller.c:362` | `PARTIAL` (input projection/clamps, no explicit LMPC constraints) |
| Terminal scalar safety constraint | `sharc_original/resources/controllers/src/ACC_Controller.cpp:315` | `SHARCBRIDGE/mpc/mpc_acc_controller.c:383` | `MISMATCH` (heuristic safety override only) |
| Warm-start OSQP and solver options | `sharc_original/resources/controllers/src/ACC_Controller.cpp:227` | `SHARCBRIDGE/mpc/mpc_acc_controller.c:169` | `MISMATCH` (no OSQP settings) |
| Solver metadata semantics | `sharc_original/resources/controllers/src/ACC_Controller.cpp:123` | `SHARCBRIDGE/scripts/gvsoc_tcp_server.py:270` | `MISMATCH` (text parse + placeholder semantics) |
| Transport serialization precision | N/A (in-process C++ doubles) | `SHARCBRIDGE/scripts/gvsoc_tcp_server.py:141` | `MISMATCH` (`struct.pack('<...f')`) |
| HTTP official / TCP fallback | N/A (project integration choice) | `SHARCBRIDGE/scripts/gvsoc_flask_server.py:1`, `SHARCBRIDGE/scripts/gvsoc_tcp_server.py:1` | `MATCH` |

## Coverage Gate

- Core elements listed: `12`
- Unmapped items: `0`
- T7.1 PASS criterion (`0 ítems sin mapear`): `PASS`

## Notes

- `PASS` in this gate means full *traceability coverage*, not behavioral parity.
- Behavioral parity is gated later by `T8` (A/B), `T9` (portado LMPC/OSQP), and `T10` (alineación numérica).
