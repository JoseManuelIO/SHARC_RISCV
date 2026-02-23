# Resumen Técnico Actual (T9 v5 + arquitectura completa)

- Fecha: 2026-02-23
- Objetivo activo: acercar el MPC adaptado al comportamiento del MPC original de SHARC, manteniendo ejecución del cálculo MPC en GVSoC/PULP.
- Estado: `EN CURSO` (paridad en modo tolerancia, no equivalencia exacta todavía).

## 1) Qué se ejecuta hoy

- Escenario de paridad principal: `sharc_original/examples/acc_example/simulation_configs/ab_onestep_compare.json`
- Runner: `SHARCBRIDGE/scripts/run_gvsoc_config.sh`
- Transporte oficial wrapper->host: HTTP (`gvsoc_flask_server.py`), con fallback TCP (`gvsoc_tcp_server.py`).
- Controlador original (A): binario C++ `main_controller_5_5` desde `sharc_original/resources/controllers/src/ACC_Controller.cpp` (LMPC/OSQP).
- Controlador adaptado (B): `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py` + cómputo GVSoC en `SHARCBRIDGE/mpc/mpc_acc_controller.c`.

## 2) Arquitectura completa (host, Docker, SHARC, PULP/GVSoC)

### 2.1 Host (máquina local)

- Lanza Flask server de MPC: `SHARCBRIDGE/scripts/gvsoc_flask_server.py`.
- Lanza SHARC dentro de Docker: `sharc-gvsoc:latest`.
- Monta en el contenedor:
  - Wrapper Python parcheado.
  - Config JSON de simulación.
  - Carpeta de salida (`/tmp/sharc_runs/...`).

### 2.2 Docker (`sharc-gvsoc:latest`)

- Ejecuta `sharc --config_filename ...`.
- SHARC corre planta + orquestación temporal.
- En experimento A usa controlador original C++ (`main_controller_5_5`).
- En experimento B usa wrapper Python (`gvsoc_controller_wrapper_v2.py`).

### 2.3 Wrapper (dentro de Docker)

- Implementa el protocolo de pipes de SHARC:
  - Lee por iteración: `k,t,x,w`.
  - Escribe: `u` y `metadata`.
  - Lee `t_delay_py_to_c++` para evitar bloqueo.
- Persistencia de trazas de dinámica:
  - `wrapper_dynamics_trace.ndjson` (una línea JSON por iteración con `k,t,x,w,u_prev`).
- Comunicación con host:
  - HTTP `/mpc/compute` (oficial) o TCP fallback.
- Frecuencia efectiva para delay:
  - `GVSOC_CHIP_CYCLE_NS`.
  - Escala `cycles` antes de escribir `gvsoc_cycles_k.txt` para emular frecuencia sin tocar SHARC interno del contenedor.

### 2.4 Host server MPC (Flask/TCP)

- Endpoint HTTP `POST /mpc/compute` en `SHARCBRIDGE/scripts/gvsoc_flask_server.py`.
- Reutiliza `run_gvsoc_mpc(...)` de `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`.
- `run_gvsoc_mpc(...)`:
  - Parchea ELF con estado/entrada actual (`k,t,x,w,u_prev`) en `.shared_data`.
  - Ejecuta GVSoC (`gvsoc`) sobre `mpc_acc_controller.elf`.
  - Parsea stdout: `U=`, `COST=`, `ITER=`, `CYCLES=`, `STATUS=`.

### 2.5 PULP/GVSoC (cómputo MPC)

- Binario ejecutado: `SHARCBRIDGE/mpc/build/mpc_acc_controller.elf`.
- Código MPC: `SHARCBRIDGE/mpc/mpc_acc_controller.c`.
- Solver actual: QP ligero (2 variables) vía `SHARCBRIDGE/mpc/qp_solver.c`.
- Salidas hacia wrapper: `u`, `cost`, `iterations`, `cycles`, `status`.

## 3) Flujo completo de datos (end-to-end)

1. Host ejecuta `run_gvsoc_config.sh`.
2. Arranca/reusa Flask y arranca contenedor SHARC.
3. SHARC inicia experimento y crea pipes + `status`.
4. Wrapper abre pipes en orden seguro y entra al loop.
5. En cada iteración, wrapper lee `k,t,x,w` desde SHARC.
6. Wrapper guarda traza en `wrapper_dynamics_trace.ndjson`.
7. Wrapper envía request MPC al host (`k,t,x,w,u_prev`).
8. Flask delega en `run_gvsoc_mpc`.
9. `run_gvsoc_mpc` parchea ELF con entradas actuales y ejecuta GVSoC.
10. GVSoC ejecuta MPC en PULP y devuelve `u,cost,iter,cycles,status`.
11. Wrapper aplica escalado de ciclos para delay (si hay barrido de frecuencia).
12. Wrapper escribe `u`, `metadata` y `gvsoc_cycles_k.txt`.
13. SHARC lee `gvsoc_cycles_k.txt` con `GVSoCDelayProvider`, convierte a `t_delay`, actualiza planta.
14. SHARC vuelca resultados a `simulation_data_incremental.json`.
15. `run_gvsoc_config.sh` valida trazas, construye `experiment_list_data_incremental.json` y genera `plots.png` con `generate_example_figures.py`.

## 4) De dónde salen los datos de las gráficas

- Fuente base por experimento:
  - `.../simulation_data_incremental.json`
- Campos usados para plots:
  - `t`: eje temporal
  - `x`: estados (posición, headway, velocidad)
  - `u`: control (aceleración, frenado)
  - `w`: entradas exógenas (incluye velocidad frontal)
  - `pending_computation` / `pending_computations`: delays y metadata por cálculo
- Archivo intermedio para plotter:
  - `.../latest/experiment_list_data_incremental.json`
- Imagen final:
  - `.../latest/plots.png`

## 5) Comparativa con SHARC original (lo relevante)

### 5.1 Igualdades

- Misma planta y orquestación temporal SHARC.
- Mismo protocolo de intercambio por pipes.
- Misma estructura de salida (`x,u,t,w,pending_computation`).
- A/B corre en mismo framework y mismo escenario.

### 5.2 Diferencias

- Original:
  - Control C++ con LMPC/OSQP (`ACC_Controller.cpp`, `libmpc`).
- Adaptado actual:
  - Control C bare-metal en GVSoC (`mpc_acc_controller.c`), QP ligero + guards físicos.
- Implicación:
  - No es todavía bit-a-bit ni solver-a-solver equivalente al original.
  - Sí hay convergencia por comportamiento en modo tolerancia.

## 6) Ajuste de frenado más reciente (v5)

### 6.1 Cambio aplicado

- Archivo: `SHARCBRIDGE/mpc/mpc_acc_controller.c`
- En `solve_mpc(...)`:
  - Se mantiene suavizado por canal (`wdu_acc=1.0`, `wdu_br=0.30`).
  - Se añade `closing-speed guard` para evitar infrarrenado en `2-5s`.
  - Se mantiene cap de liberación en zona segura para evitar sobrerrenado tardío.

### 6.2 Run de validación

- Run: `/tmp/sharc_runs/2026-02-23--13-22-05-ab_onestep_compare`
- Plot automático: `/tmp/sharc_runs/2026-02-23--13-22-05-ab_onestep_compare/latest/plots.png`
- Copia plot relevante: `artifacts/T8/plots/ab_onestep_compare_2026-02-23--13-22-05_plots.png`
- Plot foco freno: `artifacts/T8/plots/ab_onestep_compare_2026-02-23--13-22-05_brake_focus.png`

### 6.3 Métricas v4 -> v5 (freno)

- Comparativa: `artifacts/T8/runs/ab_onestep_brake_tuning_compare_v4_to_v5_2026-02-23--13-22-05.md`
- Resultado clave:
  - `2-5s`: MAE `619.220 -> 218.356` (mejora `64.74%`)
  - `5-6.5s`: MAE `1209.499 -> 560.700` (mejora `53.64%`)
  - `6.5-8s`: MAE `221.534 -> 300.806` (empeora, pero sigue muy por debajo de estado pre-v4)
  - Global: MAE freno `520.603 -> 255.384` y RMSE freno `798.192 -> 412.705`

## 7) Evidencias y tests

- Tests: `pytest -q SHARCBRIDGE/tests` -> `12 passed`.
- Trazas dinámicas por iteración (`k,t,x,w`) validadas automáticamente en runner.
- Artefactos principales:
  - `artifacts/T8/runs/ab_onestep_brake_segmented_2026-02-23--13-22-05.json`
  - `artifacts/T8/runs/ab_onestep_brake_segmented_2026-02-23--13-22-05.md`
  - `artifacts/T8/runs/ab_onestep_brake_tuning_compare_v4_to_v5_2026-02-23--13-22-05.md`
  - `artifacts/T8/plots/ab_onestep_compare_2026-02-23--13-22-05_brake_focus.png`

## 8) Estado de fidelidad MPC vs original

- Estado actual: mejorado de forma relevante en frenado global y tramo medio.
- Gap abierto: afinar tramo tardío (`6.5-8s`) sin degradar mejora global.
- Conclusión: arquitectura end-to-end está estable y trazable; queda iterar pesos/guards para cerrar más la paridad estricta con SHARC original.
