# SHARC + GVSoC Validation Notes

## Objective
Keep a single official execution path for ACC validation:
1. dynamics on SHARC side (CPU),
2. MPC computation on PULP/GVSoC (RISC-V),
3. TCP transport between wrapper and host server,
4. double profile toolchain (`ilp32d`) for higher numeric fidelity.

## Official entrypoints
- Generic config run:
  - `SHARCBRIDGE/scripts/run_gvsoc_config.sh`
- Figure 5 run:
  - `SHARCBRIDGE/scripts/run_gvsoc_figure5_tcp.sh`

## Core components
- Wrapper:
  - `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py`
- TCP server:
  - `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`
- Shared GVSoC core:
  - `SHARCBRIDGE/scripts/gvsoc_core.py`
- MPC firmware:
  - `SHARCBRIDGE/mpc/mpc_acc_controller.c`
  - `SHARCBRIDGE/mpc/qp_solver.c`

## End-to-end flow
1. Run script starts TCP server (`gvsoc_tcp_server.py`) and SHARC container.
2. SHARC computes plant dynamics and sends `k,t,x,w` over pipes.
3. Wrapper reads pipe data and sends TCP request to host server.
4. Server calls `run_gvsoc_mpc(...)` from `gvsoc_core.py`.
5. `gvsoc_core.py` patches ELF shared inputs and executes GVSoC.
6. Firmware computes control and prints `U`, `COST`, `ITER`, `CYCLES`, `STATUS`.
7. Server returns parsed result to wrapper.
8. Wrapper writes control + metadata back to SHARC and emits cycle file for delay path.

## Commands
Figure 5 (official):
```bash
cd /home/jminiesta/Repositorios/SHARC_RISCV
source venv/bin/activate
bash SHARCBRIDGE/scripts/run_gvsoc_figure5_tcp.sh
```

Single config (official):
```bash
cd /home/jminiesta/Repositorios/SHARC_RISCV
source venv/bin/activate
bash SHARCBRIDGE/scripts/run_gvsoc_config.sh gvsoc_test.json
```

## Outputs
- SHARC outputs and plots:
  - `/tmp/sharc_runs/<timestamp>-<config>/...`
  - `/tmp/sharc_figure5_tcp/<timestamp>/...`
- Figure 5 hardware metrics:
  - `<run>/latest/hw_metrics.json`
  - `<run>/latest/hw_metrics.csv`
  - `<run>/latest/hw_metrics.md`
  - `<run>/latest/hw_metrics.png`

## Current status on parity
Integration and execution path are validated (TCP + GVSoC + double).  
Strict algorithmic parity with original SHARC MPC still requires additional migration work in formulation/solver parity.
