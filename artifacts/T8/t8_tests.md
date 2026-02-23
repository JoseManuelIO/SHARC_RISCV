# T8 Test Gates

- Generated: `2026-02-23T12:15:20.666315`

## T8.1 Dataset canónico
- Test: existe `artifacts/T8/canonical_dataset.json` y contiene puntos válidos
- Resultado: `PASS` (n_points=20)

## T8.2 Arnés A/B offline
- Test: existe reporte `artifacts/T8/ab_report_v2.md` con métricas comparativas y delta vs baseline
- Resultado: `PASS`

## T8.3 Umbral de tolerancia inicial
- Test: evaluación automática PASS/FAIL en dos perfiles (`strict`, `provisional`)
- Resultado strict: `FAIL`
- Resultado provisional (modo tolerancia acordado): `PASS`

## Cierre T8
- Estado de tarea: `PASS (modo tolerancia)`
- Nota: el perfil strict se mantiene abierto para endurecimiento posterior.
