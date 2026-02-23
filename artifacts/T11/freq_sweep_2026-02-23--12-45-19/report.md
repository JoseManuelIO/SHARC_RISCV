# Barrido de frecuencia (validación corta)

- Fecha: 2026-02-23
- Config: `gvsoc_figure5.json`
- Objetivo: validar barrido y generación automática de plots por simulación.

| Freq (MHz) | Cycle ns | Avg delay (s) | RMSE u_accel | RMSE u_brake | RMSE x_pos | RMSE x_vel | Plot |
|---:|---:|---:|---:|---:|---:|---:|---|
| 600 | 1.666666667 | 0.004859483 | 1.066850 | 2.518730 | 1.925930 | 0.467424 | `plots/600MHz.png` |
| 800 | 1.250000000 | 0.003565060 | 1.156977 | 2.008713 | 1.938614 | 0.471241 | `plots/800MHz.png` |

- Mejor latencia media en este barrido: **800 MHz** (avg_delay=0.003565060 s).
- Nota: este barrido es corto (2 puntos); ampliar rango para decisión final.
