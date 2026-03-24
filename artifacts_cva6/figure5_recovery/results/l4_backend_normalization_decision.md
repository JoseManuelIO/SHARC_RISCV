# L4 Backend Normalization Decision

- fecha: `2026-03-24`
- estado: `PASS`

## Opciones consideradas

1. recompilar `isa-sim` tambien dentro del SDK limpio
2. resolver `CVA6_SPIKE_BIN` automaticamente cuando el SDK limpio no tenga `install64/bin/spike`

## Decision tomada

- se aplica la opcion 2

## Motivo

- es el cambio minimo en el flujo principal
- evita recordar una variable manual que ya causaba deriva operativa
- no obliga a rehacer otra fase pesada del SDK limpio

## Implementacion

- [run_cva6_figure5_tcp.sh](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh)
  - si `CVA6_SPIKE_BIN` viene dado, lo respeta
  - si no, intenta `CVA6_SDK_DIR/install64/bin/spike`
  - si ese SDK limpio no trae `Spike`, cae al `Spike` del SDK del repo

## Validacion

- run completo correcto sin pasar `CVA6_SPIKE_BIN` a mano:
  - [/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/experiment_list_data_incremental.json](/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/experiment_list_data_incremental.json)
  - [/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/plots.png](/tmp/sharc_cva6_figure5/2026-03-24--16-52-29-cva6_figure5/latest/plots.png)

## Gate

- Figure 5 arranca con una receta estable y sin depender de pasar `CVA6_SPIKE_BIN` manualmente
