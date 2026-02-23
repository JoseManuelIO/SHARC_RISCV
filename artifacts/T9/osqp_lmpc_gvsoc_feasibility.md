# OSQP/LMPC Feasibility on GVSoC (Current Environment)

- Generated: 2026-02-23
- Goal: verify whether we can realistically run original LMPC/OSQP stack directly on current GVSoC flow.

## Evidence Collected

1. `libmpc` explicitly requires external dependencies:
- `sharc_original/libmpc/CMakeLists.txt` requires `Eigen3`, `osqp`, `NLopt`.
- It is configured as C++20 interface.

2. Toolchain and dependency probes failed for target side:
- `riscv32-unknown-elf-g++ -std=c++20 ...` fails (`unrecognized option`).
- `riscv32-unknown-elf-gcc` probe with `#include <osqp.h>` fails (`No such file or directory`).
- `Eigen/Core` headers are not present in system include paths.

3. Current GVSoC MPC build path is lightweight C bare-metal:
- `SHARCBRIDGE/mpc/Makefile` builds `start.S + mpc_acc_controller.c + qp_solver.c` only.
- No C++ runtime / Eigen / OSQP linkage is currently wired in that target flow.

## Conclusion

- In this environment and target flow, LMPC/OSQP is **not currently feasible** without a substantial toolchain/dependency port.
- This matches the prior constraint you noted (data architecture incompatibility + integration weight).
- Recommended path: keep a lightweight solver on GVSoC and enforce fidelity by matching original equations/constraints.

## Decision for Next Steps

- Proceed with equation-faithful lightweight MPC on GVSoC (no heavy LMPC/OSQP libs for now).
- Revisit LMPC/OSQP only if a dedicated cross-compile dependency stack is prepared and validated.
