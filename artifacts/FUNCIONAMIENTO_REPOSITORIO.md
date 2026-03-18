# Funcionamiento del Repositorio (Ruta Oficial)

Fecha: 2026-03-05

## Preparacion
```bash
cd /home/jminiesta/Repositorios/SHARC_RISCV
source venv/bin/activate
```

## Comandos principales
1. Run corto:
```bash
SHARC_DOUBLE_NATIVE=1 bash SHARCBRIDGE/scripts/run_gvsoc_config.sh gvsoc_test.json
```

2. Figura 5 + hardware:
```bash
SHARC_DOUBLE_NATIVE=1 bash SHARCBRIDGE/scripts/run_gvsoc_figure5_tcp.sh
```

3. Verificacion final (pipeline + repeatability + gates):
```bash
bash SHARCBRIDGE/scripts/verify_final_official.sh
```

## Outputs esperados
- Runs cortos: `/tmp/sharc_runs/<timestamp>-gvsoc_test/...`
- Figure 5: `/tmp/sharc_figure5_tcp/<timestamp>/...`
- Plot principal: `<run>/latest/plots.png`
- Hardware: `<run>/latest/hw_metrics.{json,csv,md,png}`

## Gates oficiales
- `SHARCBRIDGE/scripts/t3_formulation_parity_gate.py`
- `SHARCBRIDGE/scripts/t8_fidelity_gate.py`
- `SHARCBRIDGE/scripts/check_official_repeatability.sh`
- `SHARCBRIDGE/scripts/verify_final_official.sh`

## Configuracion oficial
- `transport = TCP`
- `double = ON`
- `GVSOC_QP_SOLVE = 1`
- `backend persistente = proxy`
- `fallback oficial = OFF`
