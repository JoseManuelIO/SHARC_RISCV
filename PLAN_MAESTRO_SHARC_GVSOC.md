# Plan Maestro SHARC + GVSoC

## 1) Objetivo final (criterio de éxito)
- Dinámica de la planta ejecutándose en **SHARC (CPU)**.
- MPC ejecutándose en **GVSoC** con comportamiento equivalente al **MPC original** (`ACC_Controller.cpp` + LMPC/OSQP).
- Métricas arquitecturales (ciclos/tiempo) trazables y reproducibles.
- Flujo oficial nativo en tu máquina con **HTTP** como transporte principal y **TCP** como fallback.

## 2) Reglas de ejecución
- Regla de compuerta: **no se puede iniciar la tarea T(n+1) si no están en PASS todos los tests de T(n)**.
- Limpieza primero, fidelidad MPC después.
- Cambios en `sharc_original/` solo por parche y mínimos.
- Para paridad numérica se acepta tolerancia, pero el objetivo funcional es replicar el MPC original.

## 3) Estructura de validación
- Cada subtarea incluye:
  - Acción
  - Test propio
  - Criterio PASS
  - Artefacto de evidencia

---

## T0. Congelación de baseline y entorno
### T0.1 Snapshot del estado actual
- Acción: guardar estado git, entorno y versiones de toolchain.
- Test propio: `git status --short` + script de versions (`gcc`, `gvsoc`, python).
- PASS: snapshot generado sin errores.
- Evidencia: `artifacts/T0/baseline_snapshot.md`.

### T0.2 Baseline funcional actual
- Acción: ejecutar flujo actual de integración (nativo) y guardar outputs.
- Test propio: run baseline (`run_gvsoc_figure5.sh` o equivalente actual).
- PASS: genera `simulation_data_incremental.json` y logs sin crash.
- Evidencia: `artifacts/T0/baseline_run_*`.

### T0.3 Baseline reproducible
- Acción: repetir baseline 2 veces con misma config.
- Test propio: diff de series `t/x/u` entre corridas.
- PASS: diferencias dentro de tolerancia acordada de baseline.
- Evidencia: `artifacts/T0/repro_diff_report.md`.

---

## T1. Inventario y clasificación de código (limpieza)
### T1.1 Inventario de archivos funcionales
- Acción: inventariar `SHARCBRIDGE`, `riscv_bridge`, `_obsolete_root`, scripts y configs.
- Test propio: script de inventario genera CSV/JSON con clasificación.
- PASS: 100% de archivos clasificados (`activo/dudoso/obsoleto/externo`).
- Evidencia: `artifacts/T1/inventory.json`.

### T1.2 Matriz de dependencias cruzadas
- Acción: detectar referencias entre rutas (imports, paths, scripts, docs).
- Test propio: búsqueda estática (`rg`) + reporte de dependencias.
- PASS: no hay referencias “sin resolver”.
- Evidencia: `artifacts/T1/dependency_matrix.md`.

### T1.3 Lista de eliminación aprobada
- Acción: preparar lista final de candidatos obsoletos (incluye `riscv_bridge/` y `_obsolete_root/` si aplican).
- Test propio: revisión automática de impacto (qué rompería).
- PASS: impacto neto = 0 sobre flujo oficial actual.
- Evidencia: `artifacts/T1/deletion_plan.md`.

---

## T2. Limpieza efectiva del repositorio
### T2.1 Cuarentena/eliminación de obsoletos
- Acción: mover o eliminar rutas obsoletas aprobadas.
- Test propio: escaneo post-limpieza de referencias rotas.
- PASS: 0 referencias a rutas eliminadas.
- Evidencia: `artifacts/T2/post_cleanup_refs.md`.

### T2.2 Ajuste de documentación y comandos
- Acción: actualizar README/guías para una sola ruta oficial.
- Test propio: ejecutar literalmente comandos documentados en entorno limpio.
- PASS: comandos de docs funcionan de punta a punta.
- Evidencia: `artifacts/T2/docs_verification.md`.

### T2.3 Smoke de no regresión tras limpieza
- Acción: correr flujo corto (3-5 steps).
- Test propio: smoke test corto con HTTP.
- PASS: sin deadlocks FIFO, sin timeouts, salida válida.
- Evidencia: `artifacts/T2/smoke_after_cleanup/`.

---

## T3. Consolidación de arquitectura de ejecución
### T3.1 HTTP como oficial
- Acción: fijar HTTP como default en wrapper/scripts.
- Test propio: health + compute por HTTP + integración corta.
- PASS: toda ejecución oficial usa HTTP sin flags extra.
- Evidencia: `artifacts/T3/http_official.md`.

### T3.2 TCP como fallback operativo
- Acción: mantener ruta TCP degradada pero funcional.
- Test propio: prueba de roundtrip TCP independiente.
- PASS: request/response TCP correcta.
- Evidencia: `artifacts/T3/tcp_fallback_test.md`.

### T3.3 Ejecución nativa prioritaria
- Acción: asegurar flujo nativo host-first.
- Test propio: run completo sin Docker.
- PASS: pipeline principal ejecuta y produce artefactos.
- Evidencia: `artifacts/T3/native_run.md`.

---

## T4. Framework de tests automatizados
### T4.1 Crear tests unitarios mínimos en `SHARCBRIDGE/tests`
- Acción: tests de parser salida MPC, delay provider, wrapper I/O básico.
- Test propio: `pytest SHARCBRIDGE/tests -q`.
- PASS: suite unitaria en verde.
- Evidencia: `artifacts/T4/pytest_unit.log`.

### T4.2 Tests de integración de transporte
- Acción: test integración wrapper <-> server HTTP y TCP fallback.
- Test propio: integración con servidor mock + real.
- PASS: ambos modos pasan en CI local.
- Evidencia: `artifacts/T4/transport_integration.log`.

### T4.3 Gate de estabilidad
- Acción: ejecutar suite 3 veces seguidas.
- Test propio: repetición automatizada.
- PASS: 3/3 ejecuciones verdes.
- Evidencia: `artifacts/T4/stability_runs.md`.

---

## T5. Réplica de escenarios de `sharc_original`
### T5.1 Catálogo de escenarios
- Acción: extraer todos los escenarios de `examples/acc_example/simulation_configs`.
- Test propio: script que enumera configs y labels.
- PASS: catálogo completo generado.
- Evidencia: `artifacts/T5/scenario_catalog.md`.

### T5.2 Runner unificado por escenario
- Acción: crear runner para ejecutar escenarios en modo GVSoC.
- Test propio: run de lote Tier-0 (`smoke_test`, `serial`, `parallel`).
- PASS: todos terminan con salida válida.
- Evidencia: `artifacts/T5/tier0_results/`.

### T5.3 Réplica completa
- Acción: ejecutar también `parallel_vs_serial`, `gvsoc_figure5`, `gvsoc_timing_analysis`, consistencias.
- Test propio: validación estructural de outputs por escenario.
- PASS: 100% de escenarios objetivo con `json` válido.
- Evidencia: `artifacts/T5/full_matrix_report.md`.

---

## T6. Comparativa de tiempos vs SHARC+Scarab original
### T6.1 Medición de referencia original
- Acción: medir runtime con scripts de `repeatability_evaluation` (incluye figure 5 original).
- Test propio: ejecución controlada y captura de tiempos.
- PASS: tabla de tiempos base generada.
- Evidencia: `artifacts/T6/original_scarab_timing.csv`.

### T6.2 Medición GVSoC actual
- Acción: medir mismos escenarios en ruta GVSoC.
- Test propio: benchmark runner equivalente.
- PASS: tabla GVSoC generada en mismo formato.
- Evidencia: `artifacts/T6/gvsoc_timing.csv`.

### T6.3 Informe comparativo
- Acción: comparar tiempos, throughput y estabilidad.
- Test propio: script de comparación produce reporte.
- PASS: reporte con deltas por escenario.
- Evidencia: `artifacts/T6/timing_comparison.md`.

---

## T7. Especificación formal del MPC original (obligatoria)
### T7.1 Extracción matemática del original
- Acción: documentar exactamente modelo, coste, restricciones, terminal constraint, solver params.
- Test propio: checklist 1:1 contra `ACC_Controller.cpp/h` y `libmpc`.
- PASS: 0 ítems “sin mapear”.
- Evidencia: `artifacts/T7/mpc_original_spec.md`.

### T7.2 Contrato de I/O y metadata
- Acción: definir contrato exacto de entradas/salidas/metadatos por paso.
- Test propio: validador de schema para requests/responses/metadata.
- PASS: schema validado con casos reales.
- Evidencia: `artifacts/T7/io_contract.json`.

### T7.3 Gap analysis contra MPC GVSoC actual
- Acción: listar divergencias exactas (solver, dinámica, costo, precisión, salida).
- Test propio: diff técnico automatizado + revisión manual.
- PASS: lista cerrada de gaps priorizados.
- Evidencia: `artifacts/T7/gap_analysis.md`.

---

## T8. Paridad MPC A/B (step-by-step)
### T8.1 Dataset canónico de estados
- Acción: capturar conjunto `(k,t,x,w,u_prev)` de escenarios representativos.
- Test propio: validador de dataset (shape/rangos/reproducibilidad).
- PASS: dataset estable y reutilizable.
- Evidencia: `artifacts/T8/ab_dataset.jsonl`.

### T8.2 Arnés A/B offline
- Acción: ejecutar mismo dataset por MPC original y MPC GVSoC, comparar `u/cost/status`.
- Test propio: script de comparación con métricas agregadas.
- PASS: métricas calculadas sin fallos de parsing.
- Evidencia: `artifacts/T8/ab_report_v1.md`.

### T8.3 Umbrales de tolerancia inicial
- Acción: fijar umbral inicial de aceptación por componente de control.
- Test propio: gate numérico automático sobre dataset.
- PASS: umbral formalizado y ejecutable (PASS/FAIL).
- Evidencia: `artifacts/T8/tolerance_gate.yaml`.

---

## T9. Portado a MPC original en GVSoC
### T9.1 Ruta preferida: reutilizar lógica original LMPC/OSQP
- Acción: evaluar y portar/reutilizar máximo código original (incluye `riscv_bridge` útil).
- Test propio: compile+run en GVSoC de controlador alineado al original.
- PASS: ejecuta y devuelve `u/status/cost` válidos.
- Evidencia: `artifacts/T9/build_run_original_like.md`.

### T9.2 Parches mínimos en `sharc_original`
- Acción: encapsular cambios en parches pequeños y trazables.
- Test propio: aplicar/quitar parches reproduciblemente.
- PASS: patchset limpio y reversible.
- Evidencia: `artifacts/T9/patchset_manifest.md`.

### T9.3 Re-ejecutar A/B
- Acción: correr de nuevo T8 con el MPC portado.
- Test propio: gate numérico de paridad.
- PASS: mejora objetiva frente a `ab_report_v1`.
- Evidencia: `artifacts/T9/ab_report_v2.md`.

---

## T10. Alineación numérica (64b vs 32b)
### T10.1 Diagnóstico de precisión
- Acción: medir error inducido por `double->float` y por parseo textual.
- Test propio: test sintético de cuantización y redondeo.
- PASS: error caracterizado por señal/escenario.
- Evidencia: `artifacts/T10/precision_diagnostic.md`.

### T10.2 Canal de datos de alta fidelidad
- Acción: evitar pérdidas evitables en I/O (salida/parseo y serialización interna).
- Test propio: prueba de ida/vuelta numérica con tolerancia estricta.
- PASS: error de canal por debajo del umbral fijado.
- Evidencia: `artifacts/T10/io_precision_test.md`.

### T10.3 Gate final de paridad numérica
- Acción: ejecutar dataset A/B completo con nueva ruta numérica.
- Test propio: validación de tolerancias finales.
- PASS: cumple tolerancias definidas para aceptar “equivalente al original”.
- Evidencia: `artifacts/T10/ab_final_gate.md`.

---

## T11. Barrido de frecuencia/cycle-time en GVSoC
### T11.1 Diseño del sweep
- Acción: definir rejilla de frecuencias/cycle-time y escenarios a medir.
- Test propio: dry-run del sweep en 2 puntos.
- PASS: sweep arranca y guarda resultados estructurados.
- Evidencia: `artifacts/T11/sweep_plan.yaml`.

### T11.2 Ejecución del sweep completo
- Acción: ejecutar barrido completo en escenarios clave.
- Test propio: validación de integridad de resultados (sin huecos).
- PASS: 100% de puntos de sweep completados.
- Evidencia: `artifacts/T11/sweep_results.csv`.

### T11.3 Selección de configuración objetivo
- Acción: elegir configuración frecuencia/cycle-time según fidelidad+coste.
- Test propio: criterio multicriterio aplicado automáticamente.
- PASS: configuración objetivo justificada y reproducible.
- Evidencia: `artifacts/T11/selected_operating_point.md`.

---

## T12. Validación extremo a extremo y cierre
### T12.1 Flujo completo final
- Acción: ejecutar pipeline final: SHARC dinámica + MPC original-like en GVSoC + métricas.
- Test propio: run e2e en escenarios críticos.
- PASS: sin errores, con artefactos completos.
- Evidencia: `artifacts/T12/e2e_final/`.

### T12.2 Reporte final técnico
- Acción: consolidar resultados de limpieza, paridad MPC, tiempos y sweep.
- Test propio: checklist de completitud documental.
- PASS: reporte trazable y verificable por terceros.
- Evidencia: `artifacts/T12/final_report.md`.

### T12.3 Gate de aceptación del repositorio
- Acción: ejecutar todos los gates anteriores en secuencia.
- Test propio: script maestro de gates.
- PASS: 100% PASS.
- Evidencia: `artifacts/T12/gate_summary.md`.

---

## 4) Escenarios objetivo a replicar (mínimo)
- `smoke_test.json`
- `serial.json`
- `parallel.json`
- `parallel_vs_serial.json`
- `gvsoc_figure5.json`
- `gvsoc_timing_analysis.json`
- `test_consistency_serial_vs_parallel.json`
- `test_serial_vs_parallel_with_fake_delays.json`
- `test_serial_consistency_with_fake_delays.json`
- `test_consistency_SLOW.json`

## 5) Definición de “MPC original” para este plan
Se considera cumplido cuando:
- Se reproduce el **mismo planteamiento de optimización** del original (modelo/coste/restricciones/terminal/solver).
- La comparación A/B step-by-step contra el controlador original cumple tolerancias aprobadas.
- Las divergencias residuales quedan explicadas por precisión numérica y/o diferencias arquitecturales medidas.

