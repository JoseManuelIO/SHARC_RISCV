# Estado del Plan Maestro

- Fecha: 2026-02-23
- Plan: `PLAN_MAESTRO_SHARC_GVSOC.md`
- Criterio de avance: no abrir `T(n+1)` sin tests PASS de `T(n)`.

## Estado por tarea

- `T0` Baseline y reproducibilidad: `COMPLETADA`
  - Evidencia: `artifacts/T0/baseline_snapshot.md`, `artifacts/T0/repro_diff_report.md`
  - Test: baseline ejecuta y comparación reproducible en PASS.

- `T1` Inventario/dependencias: `COMPLETADA`
  - Evidencia: `artifacts/T1/inventory.json`, `artifacts/T1/dependency_matrix.md`, `artifacts/T1/deletion_plan.md`
  - Test: clasificación completa y sin referencias sin resolver.

- `T2` Limpieza efectiva: `COMPLETADA`
  - Evidencia: `artifacts/T2/post_cleanup_refs.md`, `artifacts/T2/smoke_after_cleanup.md`
  - Test: smoke post-limpieza PASS sin deadlock/timeout.

- `T3` Arquitectura ejecución (HTTP oficial + TCP fallback + nativo): `COMPLETADA`
  - Evidencia: `artifacts/T3/transport_and_native_verification.md`
  - Test: checks de transporte y ejecución nativa en PASS.

- `T4` Framework de tests: `COMPLETADA`
  - Evidencia: `SHARCBRIDGE/tests/test_wrapper_and_server.py`, `SHARCBRIDGE/tests/test_gvsoc_delay_provider.py`, `artifacts/T4/stability_runs.md`
  - Test: `pytest -q SHARCBRIDGE/tests` => 12 PASS; estabilidad 3/3 PASS.

- `T5` Réplica de escenarios: `COMPLETADA (subset GVSoC ejecutado)`
  - Evidencia: `artifacts/T5/scenario_catalog.md`, `artifacts/T5/tier0_results/summary.md`, `artifacts/T5/full_matrix_report.md`
  - Test: escenarios objetivo del subset ejecutado con salida válida.

- `T6` Comparativa de tiempos: `EN CURSO`
  - Evidencia actual: `artifacts/T6/timing_comparison.md`, `artifacts/T6/original_scarab_timing.csv`, `artifacts/T6/gvsoc_timing.csv`
  - Test pendiente: comparación estricta escenario-equivalente (apples-to-apples) con deltas cerrados.

- `T7` Especificación formal MPC original: `COMPLETADA`
  - Evidencia: `artifacts/T7/mpc_original_spec.md`, `artifacts/T7/io_contract.json`, `artifacts/T7/traceability_matrix.md`, `artifacts/T7/io_contract_validation.md`, `artifacts/T7/gap_analysis.md`
  - Test T7.1: trazabilidad completa con 0 ítems sin mapear => PASS.
  - Test T7.2: validación de contrato I/O sobre trazas reales => PASS.
  - Test T7.3: inventario de gaps críticos cerrado y priorizado => PASS.

- `T8` Paridad A/B MPC: `COMPLETADA (modo tolerancia)`
  - Evidencia: `sharc_original/examples/acc_example/simulation_configs/ab_onestep_compare.json`, `artifacts/T8/canonical_dataset.json`, `artifacts/T8/ab_report_v2.md`, `artifacts/T8/t8_tests.md`
  - Evidencia adicional (plots por simulación + validación dinámica): `artifacts/T8/plots/ab_onestep_compare_2026-02-23--12-22-45.png`, `artifacts/T8/plots/gvsoc_figure5_2026-02-23--12-28-48.png`, `artifacts/T8/runs/gvsoc_figure5_2026-02-23--12-28-48_metrics.json`
  - Test T8.1: dataset canónico generado => PASS.
  - Test T8.2: arnés A/B ejecutado y métricas generadas => PASS.
  - Test T8.3: gate provisional de tolerancia => PASS (gate strict queda pendiente para endurecimiento).
- `T9` Portado a MPC original LMPC/OSQP en GVSoC: `EN CURSO`
  - Iteración v1/v2/v3: parches validados en `artifacts/T9/t9_iteration_v1.md`, `artifacts/T9/t9_iteration_v2.md` y `artifacts/T9/t9_iteration_v3.md` (mejora objetiva vs `ab_report_v1`).
  - Iteración v4/v5 (tuning de frenado + arquitectura completa): `artifacts/T9/t9_iteration_v4_brake_tuning.md` y `artifacts/T8/runs/ab_onestep_brake_tuning_compare_v4_to_v5_2026-02-23--13-22-05.md` (mejora fuerte en `2-5s`, tradeoff moderado en `6.5-8s`, mejora global clara de RMSE/MAE de freno).
  - Factibilidad LMPC/OSQP en entorno actual: `artifacts/T9/osqp_lmpc_gvsoc_feasibility.md` => no viable sin port de dependencias/toolchain.
- `T10` Alineación numérica 64b/32b: `PENDIENTE`
  - Diagnóstico preliminar ya generado: `artifacts/T10/precision_diagnosis.md` (mismatch caracterizado).
  - Avance T10.2 (canal de transporte): `artifacts/T10/precision_transport_validation.md` => PASS.
- `T11` Barrido de frecuencia: `EN CURSO`
  - Evidencia inicial: `SHARCBRIDGE/scripts/run_frequency_sweep.sh`, `artifacts/T11/freq_sweep_2026-02-23--12-45-19/summary.csv`, `artifacts/T11/freq_sweep_2026-02-23--12-45-19/summary_enriched.csv`, `artifacts/T11/freq_sweep_2026-02-23--12-45-19/report.md`
  - Test: barrido corto (600/800 MHz) PASS, con plot por punto y traza dinámica validada.
- `T12` Validación E2E y cierre: `PENDIENTE`

## Siguientes pasos inmediatos

1. Ampliar `T11`: ejecutar barrido completo (p. ej. 400/600/800/1000 MHz) y seleccionar frecuencia objetivo.
2. Cerrar `T6`: repetir mediciones y homologar escenarios para reporte temporal comparable.
3. Continuar `T9`: siguiente iteración para acercar canal de aceleración y aproximar solver original.
