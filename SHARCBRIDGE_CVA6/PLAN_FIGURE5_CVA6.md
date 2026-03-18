# Plan Figure 5 SHARC-CVA6

## Objetivo

Generar los resultados de la Figura 5 usando `RISC-V` sobre `Spike` en `CVA6 SDK`, manteniendo el controlador MPC original de `sharc_original` dentro del target `RISC-V` y sin modificar `sharc_original`.

El controlador que debe ejecutarse dentro de `RISC-V` es el controlador MPC completo, no solo el solve QP. La formulacion y la resolucion deben usar el mismo stack que el camino original:

- `sharc_original/libmpc`
- `Eigen`
- `OSQP`

## Restricciones duras

1. `sharc_original` no se toca.
2. El flujo anterior de `PULP/SHARCBRIDGE` no se toca.
3. SHARC solo entrega dinamicas y recibe el control.
4. El punto de acoplamiento con SHARC sigue siendo el wrapper externo.
5. El transporte oficial sigue siendo `TCP`.
6. Todo test, log, replay, reporte y evidencia va en `artifacts_cva6/`.
7. En `SHARCBRIDGE_CVA6/` solo viven archivos del flujo principal.
8. La configuracion de la Figura 5 debe replicar el escenario de `sharc_original/examples/acc_example/simulation_configs/gvsoc_figure5.json`.
9. El horizonte y los pesos MPC deben ser los mismos que en la referencia original.
10. La precision numerica debe priorizar fidelidad frente a velocidad.

## Referencia funcional que se debe igualar

La referencia inmediata es `sharc_original/examples/acc_example/simulation_configs/gvsoc_figure5.json`.

Parametros que deben mantenerse:

- `n_time_steps = 40`
- `prediction_horizon = 5`
- `control_horizon = 5`
- `output_cost_weight = 10000.0`
- `input_cost_weight = 0.01`
- `delta_input_cost_weight = 1.0`
- `enable_mpc_warm_start = false`
- `use_state_after_delay_prediction = false`
- `only_update_control_at_sample_times = false`

Experimentos que debe reproducir el flujo nuevo:

1. `CVA6 - Real Delays`
2. `Baseline - No Delay (Onestep)`

## Requisitos de fidelidad MPC

1. El binario que corre en `CVA6` debe instanciar el mismo controlador ACC que usa `sharc_original`.
2. El horizonte de prediccion y el horizonte de control no pueden degradarse para "hacer que funcione".
3. La build debe priorizar `double` cuando sea necesario para igualar el comportamiento del stack original.
4. `OSQP` debe mantenerse en configuracion determinista validada:
   - `adaptive_rho = true`
   - `adaptive_rho_interval = 25`
   - `profiling = on`
5. La salida funcional a igualar no es solo `u`, tambien:
   - `solver_status`
   - `iterations`
   - `cost`
   - factibilidad
   - consistencia de delays

## Arquitectura objetivo

1. SHARC genera `k, t, x, w`.
2. El wrapper de `SHARCBRIDGE_CVA6` lee esos datos sin cambiar SHARC.
3. El wrapper mantiene `u_prev` y envia una peticion `TCP`.
4. El backend `CVA6` ejecuta el controlador MPC completo dentro de `Spike`.
5. El runtime devuelve:
   - `u`
   - `solver_status`
   - `iterations`
   - `cost`
   - `constraint_error`
   - `dual_residual`
   - metricas de tiempo/ciclos necesarias para delay
6. El wrapper escribe el control de vuelta a SHARC.
7. Para el experimento de delay real, el wrapper debe dejar la evidencia en el mismo contrato que ya entiende SHARC para el provider `gvsoc`, de forma que no haya que tocar `sharc_original`.

## Flujo principal esperado

Los archivos del flujo principal deben quedar, como minimo, en estos nombres o equivalentes directos:

- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`
- `SHARCBRIDGE_CVA6/cva6_tcp_server.py`
- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- `SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp`
- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`
- `SHARCBRIDGE_CVA6/cva6_figure5.json`
- `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`

Todo lo demas:

- gates
- scripts de comparacion
- snapshots
- logs
- reportes
- capturas
- resultados agregados

debe quedar en `artifacts_cva6/`.

## Tareas

### Tarea 0. Congelar la referencia exacta de Figure 5

#### Objetivo

Cerrar por escrito que configuracion exacta de Figura 5 se debe reproducir y con que tolerancias.

#### Trabajo

1. Congelar la referencia de `gvsoc_figure5.json`.
2. Congelar el stack MPC exacto:
   - `ACC_Controller`
   - `libmpc`
   - `Eigen`
   - `OSQP`
3. Congelar el criterio de fidelidad:
   - paridad funcional de control
   - paridad de formulacion
   - compatibilidad de delay
4. Fijar la configuracion numerica objetivo para `OSQP`.

#### Archivos principales

- ninguno nuevo obligatorio en flujo

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t0_reference.md`

#### Criterio de paso

- `PASS` si la Figura 5 de referencia queda cerrada sin ambiguedad.

---

### Tarea 1. Adaptar el runtime CVA6 para calcular el controlador MPC completo

#### Objetivo

Pasar de snapshots sueltos a un runtime que ejecute el controlador ACC/MPC original dentro de `RISC-V`.

#### Trabajo

1. Reusar `cva6_acc_runtime.cpp` como base.
2. Asegurar que dentro de `CVA6` se instancia el mismo `ACC_Controller` que usa SHARC.
3. Asegurar que el runtime acepta:
   - `k`
   - `t`
   - `x`
   - `w`
   - `u_prev`
4. Devolver salida completa del controlador y metadata del solver.

#### Archivos principales

- `SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp`
- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t1_runtime_smoke.log`
- `artifacts_cva6/figure5_t1_runtime_output.json`

#### Criterio de paso

- `PASS` si el runtime ejecuta el MPC completo dentro de `CVA6` fuera de SHARC.

---

### Tarea 2. Cerrar la compatibilidad de delay real sin tocar SHARC

#### Objetivo

Conseguir que SHARC pueda usar delays reales de `CVA6/Spike` sin modificar `sharc_original`.

#### Trabajo

1. Identificar el contrato exacto que ya usa `GVSoCDelayProvider`.
2. Hacer que el wrapper CVA6 emita el mismo contrato de archivos esperado por SHARC.
3. Si el tiempo de ciclo efectivo de `CVA6` no coincide con el supuesto de SHARC, aplicar el mismo esquema de escalado que ya se usaba en el flujo GVSoC.
4. Mantener tambien el modo baseline `onestep`.

#### Archivos principales

- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t2_delay_contract.md`
- `artifacts_cva6/figure5_t2_delay_roundtrip.json`

#### Criterio de paso

- `PASS` si SHARC puede consumir delay real de `CVA6` usando su provider actual.

---

### Tarea 3. Crear la configuracion Figure 5 especifica de CVA6

#### Objetivo

Disponer de una configuracion de Figura 5 propia del flujo `CVA6`, pero funcionalmente equivalente a la referencia.

#### Trabajo

1. Derivar una config desde `gvsoc_figure5.json`.
2. Mantener los mismos parametros MPC.
3. Mantener dos experimentos:
   - real delays
   - onestep baseline
4. Ajustar solo lo necesario para usar el wrapper/backend `CVA6`.

#### Archivos principales

- `SHARCBRIDGE_CVA6/cva6_figure5.json`

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t3_config_diff.md`

#### Criterio de paso

- `PASS` si la config nueva difiere solo en el backend, no en el contenido funcional del experimento.

---

### Tarea 4. Rehacer el builder de imagen para Figure 5

#### Objetivo

Tener una build reproducible del payload `CVA6` preparada para los runs largos de Figura 5.

#### Trabajo

1. Asegurar que la imagen incluye el runtime MPC completo.
2. Asegurar que se empaquetan:
   - binario
   - config base
   - dependencias necesarias
3. Verificar build en modo de precision objetivo.

#### Archivos principales

- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t4_image_build.log`
- `artifacts_cva6/figure5_t4_rootfs_manifest.txt`

#### Criterio de paso

- `PASS` si el payload de Figura 5 se puede regenerar por script sin pasos manuales.

---

### Tarea 5. Crear el script principal de Figure 5

#### Objetivo

Tener el equivalente CVA6 del flujo `run_gvsoc_figure5_tcp.sh`.

#### Trabajo

1. Reusar la estructura del script anterior:
   - build
   - arranque del servidor TCP
   - arranque de SHARC
   - recogida de resultados
2. Usar la config `cva6_figure5.json`.
3. Montar el wrapper CVA6 sobre la ruta esperada por SHARC.
4. Dejar salida reproducible en un directorio temporal equivalente al flujo anterior.

#### Archivos principales

- `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t5_run_smoke.log`

#### Criterio de paso

- `PASS` si el script hace un run corto de Figura 5 sin intervencion manual.

---

### Tarea 6. Validar el baseline onestep con el backend CVA6

#### Objetivo

Separar el problema de integracion general del problema de delay real.

#### Trabajo

1. Ejecutar el experimento baseline `onestep`.
2. Verificar que el controlador en `CVA6` reproduce el comportamiento esperado.
3. Comparar con host para snapshots representativos.

#### Archivos principales

- ninguno nuevo obligatorio en flujo

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t6_onestep_run.log`
- `artifacts_cva6/figure5_t6_onestep_report.md`

#### Criterio de paso

- `PASS` si el baseline `onestep` queda funcionalmente alineado con la referencia.

---

### Tarea 7. Validar el experimento de real delays con Spike

#### Objetivo

Comprobar que el delay real que entra en la planta procede de la ejecucion real del controlador en `Spike/CVA6`.

#### Trabajo

1. Ejecutar el experimento de real delays.
2. Verificar que por iteracion se generan los archivos de delay esperados.
3. Verificar que el solver corre dentro de `CVA6` y no cae en atajos del host.
4. Auditar:
   - `solver_status`
   - `iterations`
   - delays consumidos

#### Archivos principales

- ninguno nuevo obligatorio en flujo

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t7_real_delay_run.log`
- `artifacts_cva6/figure5_t7_delay_audit.json`
- `artifacts_cva6/figure5_t7_delay_audit.md`

#### Criterio de paso

- `PASS` si la planta consume delay real del backend `CVA6`.

---

### Tarea 8. Gate de fidelidad host vs CVA6 para Figure 5

#### Objetivo

Demostrar que el stack en `CVA6` reproduce la referencia con suficiente fidelidad.

#### Trabajo

1. Comparar snapshots host vs `CVA6`.
2. Comparar:
   - formulacion
   - control
   - solver status
   - iteraciones
   - coste
3. Documentar diferencias permitidas y diferencias no permitidas.

#### Archivos principales

- ninguno nuevo obligatorio en flujo

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t8_parity_report.json`
- `artifacts_cva6/figure5_t8_parity_report.md`

#### Criterio de paso

- `PASS` si el comportamiento de `CVA6` es funcionalmente equivalente a la referencia.

---

### Tarea 9. Generar los resultados completos de Figura 5

#### Objetivo

Producir el run completo con las dos ramas del experimento y dejar resultados listos para inspeccion.

#### Trabajo

1. Ejecutar el script principal completo.
2. Recoger:
   - `simulation_data_incremental.json`
   - plots
   - logs
   - trazas del wrapper
3. Organizar la salida con una estructura similar al flujo anterior.

#### Archivos principales

- `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t9_run_summary.md`
- `artifacts_cva6/figure5_t9_output_paths.txt`

#### Criterio de paso

- `PASS` si la Figura 5 de `CVA6` se genera end-to-end.

---

### Tarea 10. Cierre y criterio de oficializacion

#### Objetivo

Decidir si el flujo `CVA6` ya puede considerarse el backend oficial para esta Figura 5.

#### Trabajo

1. Revisar:
   - fidelidad MPC
   - consistencia de delays
   - reproducibilidad del script principal
2. Documentar limitaciones residuales.
3. Fijar si el flujo queda:
   - `PASS`
   - `HOLD`
   - `FAIL`

#### Archivos principales

- ninguno nuevo obligatorio en flujo

#### Evidencia en artifacts

- `artifacts_cva6/figure5_t10_final_decision.md`

#### Criterio de paso

- `PASS` solo si la Figura 5 puede generarse de forma reproducible con el backend `CVA6`.

## Orden recomendado de resolucion

1. `T0`
2. `T1`
3. `T2`
4. `T3`
5. `T4`
6. `T5`
7. `T6`
8. `T7`
9. `T8`
10. `T9`
11. `T10`

## Criterio general del plan

No se pasa de tarea si la tarea anterior no queda en uno de estos dos estados:

- `PASS`
- `FAIL` con causa exacta y reproducible

No vale cerrar una tarea con "parece que funciona".

## Script principal objetivo

Cuando el plan quede resuelto, el script principal del flujo debe ser:

- `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`

Ese script debe ser el equivalente directo del flujo `Figure 5` anterior, pero con:

- `CVA6`
- `Spike`
- `RISC-V`
- controlador MPC original ejecutado dentro del target
