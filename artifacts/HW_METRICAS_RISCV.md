# Metricas de Hardware (RISC-V / GVSoC)

Fecha: 2026-03-10

## Objetivo
Definir exactamente las metricas de hardware que se recogen en el flujo oficial TCP y como interpretarlas.

## Donde se miden
1. Firmware RISC-V: `SHARCBRIDGE/mpc/qp_riscv_runtime.c`
- Activa contadores de rendimiento PULP para el tramo de solve QP.
- Lee contadores al terminar cada iteracion.

2. Bridge GVSoC: `SHARCBRIDGE/scripts/gvsoc_core.py`
- Parsea los valores devueltos por el runtime.
- Calcula `cpi` e `ipc`.

3. Wrapper SHARC: `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py`
- Guarda metricas por iteracion en `pending_computation.metadata`.

4. Agregador final: `SHARCBRIDGE/scripts/collect_run_hw_metrics.py`
- Genera resumen por experimento: `mean`, `p95`, `max`.

## Tabla de metricas por iteracion
| Campo | Tipo | Fuente | Significado |
|---|---|---|---|
| `cycles` | int | `rdcycle` / GVSoC | Ciclos totales consumidos por el solve QP. |
| `instret` | int | contador `PCER_INSTR` | Instrucciones retiradas (commit). |
| `ld_stall` | int | contador `PCER_LD_STALL` | Ciclos perdidos por stalls de carga. |
| `jmp_stall` | int | contador `PCER_JMP_STALL` | Ciclos perdidos por stalls de salto/control. |
| `imiss` | int | contador `PCER_IMISS` | Misses de instruccion (o eventos de i-fetch miss del modelo). |
| `stall_total` | int | runtime | Suma usada en el flujo actual: `ld_stall + jmp_stall + imiss`. |
| `branch` | int | contador `PCER_BRANCH` | Numero de branches ejecutados. |
| `taken_branch` | int | contador `PCER_TAKEN_BRANCH` | Numero de branches tomados. |
| `iterations` | int | solver ADMM | Iteraciones del solver QP hasta converger o alcanzar maximo. |
| `t_delay` | float (s) | wrapper | Delay de control reportado a SHARC para esa muestra. |
| `status` | int | solver QP | Estado del solver (optimo, max iter, error factor, etc.). |

## Metricas derivadas
| Campo | Formula | Interpretacion |
|---|---|---|
| `cpi` | `cycles / instret` (si `instret > 0`) | Coste medio en ciclos por instruccion retirada. Menor suele ser mejor. |
| `ipc` | `instret / cycles` (si `cycles > 0`) | Instrucciones retiradas por ciclo. Mayor suele ser mejor. |

## Salidas de resumen (Figure 5 TCP)
Al ejecutar:

```bash
SHARC_DOUBLE_NATIVE=1 bash SHARCBRIDGE/scripts/run_gvsoc_figure5_tcp.sh
```

se generan en `<run>/latest/`:
- `hw_metrics.csv`
- `hw_metrics.json`
- `hw_metrics.md`
- `hw_metrics.png`

Cada metrica numerica aparece agregada por experimento con sufijos:
- `_mean`
- `_p95`
- `_max`

## Nota de alcance
Estas metricas caracterizan el tramo de calculo del solver QP en RISC-V dentro de GVSoC (no todo el tiempo de pared del experimento completo en host).
