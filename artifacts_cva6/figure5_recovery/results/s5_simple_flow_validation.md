# S5 Simple Flow Validation

- fecha: `2026-03-25`
- estado: `PASS`

## Comando validado

```bash
./run_cva6_figure5_tcp.sh
```

## Run final

- out dir: `/tmp/sharc_cva6_figure5/2026-03-25--10-32-09-cva6_figure5`
- bundle:
  - [/tmp/sharc_cva6_figure5/2026-03-25--10-32-09-cva6_figure5/latest/experiment_list_data_incremental.json](/tmp/sharc_cva6_figure5/2026-03-25--10-32-09-cva6_figure5/latest/experiment_list_data_incremental.json)
- plot:
  - [/tmp/sharc_cva6_figure5/2026-03-25--10-32-09-cva6_figure5/latest/plots.png](/tmp/sharc_cva6_figure5/2026-03-25--10-32-09-cva6_figure5/latest/plots.png)

## Resultado

- el comando simple usa por defecto el `SDK` bueno
- no recompila el `payload` malo del repo
- genera los 2 `simulation_data_incremental.json`
- genera `latest/experiment_list_data_incremental.json`
- genera `latest/plots.png`

## Gate

- la limpieza no solo simplifica el flujo: deja probado el final end-to-end hasta Figure 5
