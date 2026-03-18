# Architecture 3/03/26

## Objetivo
Documentar la arquitectura oficial actual para ejecutar SHARC + GVSoC con:
- transporte TCP
- perfil numérico double (`ilp32d`)
- dinámicas y formulación MPC en host (SHARC/CPU)
- solve QP en RISC-V (GVSoC)

## Arquitectura (qué corre en cada parte)

### 1) Host / SHARC (CPU)
Responsabilidad:
- Simulación y dinámicas de planta.
- Lazo de control por iteración (`k, t, x, w`).
- Formulación QP en host a partir de `x, w, u_prev` para ruta oficial.

Código relevante:
- `sharc_original/resources/sharc/plant_runner.py`
- `sharc_original/resources/sharc/controller_interface.py`
- `sharc_original/resources/dynamics/dynamics.py`
- `SHARCBRIDGE/scripts/mpc_host_api.py`
- `SHARCBRIDGE/scripts/qp_payload.py`

### 2) Wrapper SHARC <-> servidor
Responsabilidad:
- Leer/escribir pipes de SHARC.
- Enviar request TCP al servidor con estado de iteración.
- Recibir `u, cost, iterations, cycles, status, t_delay`.
- Aplicar guardas de modo oficial (`tcp` + `qp_solve=1`).

Código relevante:
- `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py`

### 3) Servidor TCP
Responsabilidad:
- Endpoint TCP oficial.
- Validar protocolo y enrutar peticiones.
- Construir payload QP host-side (ruta oficial) y delegar solve a GVSoC.

Código relevante:
- `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`
- `SHARCBRIDGE/scripts/tcp_protocol.py`

### 4) Núcleo GVSoC
Responsabilidad:
- Gestionar sesión persistente del solver QP en RISC-V.
- Parchar/leer memoria compartida del runtime.
- Devolver solución QP y métricas (`status, iters, cost, cycles`).

Código relevante:
- `SHARCBRIDGE/scripts/gvsoc_core.py`
- `SHARCBRIDGE/scripts/gvsoc_qp_target_control.py`

### 5) Firmware QP en RISC-V (GVSoC)
Responsabilidad:
- Resolver el QP recibido desde host.
- Ejecutar en modo persistent worker (sin spawn por iteración).

Código relevante:
- `SHARCBRIDGE/mpc/qp_riscv_runtime.c`
- `SHARCBRIDGE/scripts/build_qp_runtime_profile.sh`

### 6) Toolchain / perfil numérico
Perfil oficial:
- `MARCH=rv32imfdcxpulpv2`
- `MABI=ilp32d`

Código relevante:
- `SHARCBRIDGE/scripts/build_qp_runtime_profile.sh`
- `SHARCBRIDGE/scripts/build_mpc_profile.sh` (solo fallback legacy)

## Flujo E2E (paso a paso)
1. `run_gvsoc_config.sh` o `run_gvsoc_figure5_tcp.sh` arrancan server TCP y SHARC.
2. SHARC calcula dinámicas y pasa `k,t,x,w` al wrapper.
3. Wrapper envía request TCP.
4. Servidor formula QP en host (`c_abi`) y lo envía al runtime QP RISC-V.
5. GVSoC resuelve QP en worker persistente y devuelve solución+estadísticas.
6. Wrapper devuelve `u` y metadata a SHARC.
7. SHARC aplica delay y continúa la simulación.
8. Se guardan datos, plots y métricas hardware.

## Comandos oficiales

### A) Preparación
```bash
cd /home/jminiesta/Repositorios/SHARC_RISCV
source venv/bin/activate
```

### B) Run corto de validación
```bash
SHARC_DOUBLE_NATIVE=1 bash SHARCBRIDGE/scripts/run_gvsoc_config.sh gvsoc_test.json
```

### C) Figura 5 TCP + métricas hardware
```bash
SHARC_DOUBLE_NATIVE=1 bash SHARCBRIDGE/scripts/run_gvsoc_figure5_tcp.sh
```

### D) Tests oficiales
```bash
bash SHARCBRIDGE/scripts/run_official_pytest_suite.sh
```

### E) Verificación pipeline oficial
```bash
bash SHARCBRIDGE/scripts/verify_official_pipeline.sh
```

### F) Gate de repetibilidad
```bash
bash SHARCBRIDGE/scripts/check_official_repeatability.sh
```

### G) Gate de fidelidad (2 escenarios obligatorios)
```bash
python3 SHARCBRIDGE/scripts/t8_fidelity_gate.py \
  --thresholds artifacts/T8_fidelity_thresholds_v1.json
```

### H) Gate de formulación T3
```bash
python3 SHARCBRIDGE/scripts/t3_formulation_parity_gate.py \
  --tol 1e-12
```

### I) Verificación final en un comando
```bash
bash SHARCBRIDGE/scripts/verify_final_official.sh
```

## Salidas esperadas

Run corto (`gvsoc_test.json`):
- `/tmp/sharc_runs/<timestamp>-gvsoc_test/.../simulation_data_incremental.json`
- `/tmp/sharc_runs/<timestamp>-gvsoc_test/latest/plots.png`

Figura 5 TCP:
- `/tmp/sharc_figure5_tcp/<timestamp>/.../simulation_data_incremental.json`
- `/tmp/sharc_figure5_tcp/<timestamp>/latest/plots.png`
- `/tmp/sharc_figure5_tcp/<timestamp>/latest/hw_metrics.json`
- `/tmp/sharc_figure5_tcp/<timestamp>/latest/hw_metrics.csv`
- `/tmp/sharc_figure5_tcp/<timestamp>/latest/hw_metrics.md`
- `/tmp/sharc_figure5_tcp/<timestamp>/latest/hw_metrics.png`

Gates de fidelidad:
- `artifacts/T8_fidelity_gate_latest.json`
- `artifacts/T8_fidelity_gate_latest.md`

Gate de formulación T3:
- `artifacts/T3_formulation_parity_gate_latest.json`
- `artifacts/T3_formulation_parity_gate_latest.md`

## Notas
- Camino oficial: TCP + double + QP solve en RISC-V.
- HTTP/Flask se mantienen como fallback no oficial.
- En modo oficial, si no hay solver QP en RISC-V, debe fallar explícitamente.
