# SHARC + GVSoC Validation Notes

## Objective
Validate that the current `acc_example` flow:
1. runs end-to-end without failures,
2. keeps plant dynamics on SHARC (CPU side),
3. runs MPC on PULP/GVSoC,
4. and checks whether GVSoC MPC is equivalent to original SHARC MPC.

## Reference Figure-5 Source (Original SHARC)
Original script provided by user:
- `sharc_original/repeatability_evaluation/run_acc_example_to_generate_figure_5.sh`

That script calls:
- `sharc_original/repeatability_evaluation/run_example_in_container.sh`
- with config: `sharc_original/examples/acc_example/simulation_configs/parallel_vs_serial.json`

Important: original Figure 5 compares **Parallel Scarab vs Serial Scarab** (both on original SHARC controller), not GVSoC.

## Current GVSoC Execution Architecture (Validated)
### Entry script
- `SHARCBRIDGE/scripts/run_gvsoc_figure5.sh`

### Wrapper and transport
- `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py`
- `SHARCBRIDGE/scripts/gvsoc_flask_server.py`
- `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`

### SHARC integration points
- `sharc_original/resources/sharc/plant_runner.py`
- `sharc_original/resources/sharc/controller_interface.py`
- `sharc_original/resources/sharc/__init__.py`
- `sharc_original/resources/sharc/scarabizor.py`

### Dynamics model (CPU side)
- `sharc_original/resources/dynamics/dynamics.py` (`ACCDynamics`)

### GVSoC MPC binary source
- `SHARCBRIDGE/mpc/mpc_acc_controller.c`

## Information Flow (End-to-End)
1. `run_gvsoc_figure5.sh` starts Flask server and runs SHARC container.
2. SHARC plant loop (`plant_runner.py`) computes dynamics in Python (`ACCDynamics`).
3. SHARC controller interface writes `k,t,x,w` through pipes.
4. GVSoC wrapper reads pipes and calls Flask `/mpc/compute`.
5. Flask server calls `run_gvsoc_mpc(...)` in `gvsoc_tcp_server.py`.
6. `run_gvsoc_mpc(...)` patches ELF inputs, executes GVSoC, parses `U=...`, `CYCLES=...`, etc.
7. Wrapper writes `u` + metadata to SHARC and writes `gvsoc_cycles_k.txt`.
8. `GVSoCDelayProvider` reads `gvsoc_cycles_k.txt` and converts cycles to `t_delay`.
9. SHARC applies delay logic and evolves plant state for next step.

## Commands Used During Validation
Main Figure-5 run:
```bash
cd /home/jminiesta/Repositorios/SHARC_RISCV
source venv/bin/activate
bash SHARCBRIDGE/scripts/run_gvsoc_figure5.sh
```

Reference original Figure-5 script (for baseline SHARC behavior):
```bash
cd /home/jminiesta/Repositorios/SHARC_RISCV/sharc_original/repeatability_evaluation
./run_acc_example_to_generate_figure_5.sh
```

## Tests Executed and Results
### 1) Reproducibility (current GVSoC Figure-5 flow)
Two runs:
- `/tmp/sharc_figure5/2026-02-20--13-42-39`
- `/tmp/sharc_figure5/2026-02-20--13-43-22`

Result:
- `len(t/x/u)` identical in both runs for both experiments.
- `max|dt|=0`, `max|dx|=0`, `max|du|=0` (exact match).

### 2) Architecture verification from logs
From:
- `/tmp/sharc_figure5/2026-02-20--13-43-22/2026-02-20--04-43-23--gvsoc-figure5/gvsoc-real-delays/controller.log`
- `/tmp/sharc_figure5/2026-02-20--13-43-22/2026-02-20--04-43-23--gvsoc-figure5/gvsoc-real-delays/dynamics.log`

Observed:
- Wrapper iterations show per-step `(k,t,x,w)` and cycle-file writes.
- Dynamics log shows plant time-step loop (`Starting time step #...`) on SHARC side.
- Confirms dynamics and plant integration are on SHARC CPU side, while MPC call goes out through wrapper/server/GVSoC path.

### 3) Delay-path verification
From simulation data:
- GVSoC experiment (`gvsoc` delay provider): delay from cycles, approx `0.00096s` to `0.00143s`.
- Baseline experiment (`onestep` delay provider): fixed `0.1999998s`.

This confirms delay source switching is active and functioning.

## MPC Equivalence Check (Critical Finding)
Current GVSoC MPC implementation is **not algorithmically equivalent** to original SHARC MPC.

Evidence in source:
- Original SHARC MPC: `sharc_original/resources/controllers/src/ACC_Controller.cpp`
  - LMPC/OSQP-based optimization, linearized model updates, constraints and terminal constraint.
- GVSoC MPC: `SHARCBRIDGE/mpc/mpc_acc_controller.c`
  - custom grid-search + projected-gradient approach, different cost structure and solver flow.

Conclusion:
- Current setup validates execution and integration, but **does not yet guarantee same MPC calculations** as original SHARC.

## Current Blocker for Direct A/B in Same Container
Trying to run original SHARC controller in the `sharc-gvsoc` image through the serial Scarab path fails with:
- `setarch: failed to set personality ... Operation not permitted`

This is an environment/privilege issue in the Scarab execution path, not a plant or wrapper math error.

## What Must Change for True MPC Parity
To claim strict equivalence with original SHARC MPC, one of these is needed:
1. Port/run the same original LMPC/OSQP controller logic on PULP/GVSoC.
2. Or run original SHARC controller and GVSoC controller in a controlled A/B harness with identical `(k,t,x,w,u_prev)` and compare `u_k` step-by-step with tolerance.

