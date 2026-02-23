# Gap Analysis (T7.3)

- Generated: `2026-02-23T10:21:46.661861`
- Traceability source: `artifacts/T7/traceability_matrix.md`

## Critical Gaps
1. Solver mismatch: original uses LMPC/OSQP; GVSoC uses custom grid-search + gradient routine.
2. Numeric precision mismatch: original uses `double`; GVSoC path currently uses `float` inputs/states/costs.
3. Model/constraint mismatch: original updates linearized model and terminal scalar constraint; GVSoC custom controller uses different handcrafted cost/safety terms.
4. Metadata semantics mismatch: original reports solver residuals from LMPC; GVSoC fills placeholders for residuals in wrapper metadata.
5. I/O precision loss: server patches shared struct with `struct.pack(<...f>)` and parses output via text patterns.

## Prioritized Actions
- P1 (`T9.1`): align algorithm to original LMPC/OSQP formulation or reuse equivalent implementation path.
  - Affected: `SHARCBRIDGE/mpc/mpc_acc_controller.c`
  - Gate test: `artifacts/T8/ab_report_v2.md` shows objective improvement vs `ab_report_v1`.
- P2 (`T10.2`): improve numeric path and eliminate avoidable text/rounding losses before A/B gate.
  - Affected: `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`, `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py`
  - Gate test: `artifacts/T10/precision_gate.md` PASS under agreed tolerance.
- P3 (`T8.2`): enforce metadata parity and schema checks in integration tests.
  - Affected: `SHARCBRIDGE/tests/`
  - Gate test: schema validator and metadata parity tests green.

## Closure

- Gap inventory status: `CLOSED` (all critical gaps captured and prioritized).
- T7.3 PASS criterion (lista cerrada de gaps priorizados): `PASS`.
