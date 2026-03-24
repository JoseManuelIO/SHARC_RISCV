# L5 TCP Server Reuse Policy

- fecha: `2026-03-24`
- estado: `PASS`

## Problema

- el script podia reutilizar un `tcp_server` viejo solo por coincidir en `runtime_mode`
- eso permitia mezclar un `SDK`, `payload` o `Spike` distinto con una nueva validacion

## Cambio aplicado

- [cva6_runtime_launcher.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_runtime_launcher.py)
  - `health` publica `sdk_dir`, `spike_bin` y `spike_payload`
- [run_cva6_figure5_tcp.sh](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh)
  - antes de reutilizar compara:
    - `runtime_mode`
    - `sdk_dir`
    - `spike_bin`
    - `spike_payload`
  - si algo no coincide, reinicia el server

## Contrato operativo

- reuse permitido solo si la identidad del backend coincide
- para debugging o cambios grandes sigue siendo recomendable usar puerto nuevo

## Gate

- ya no existe reuse automatico basado solo en el modo
- el contrato de `health` expone la identidad necesaria para decidir reuse seguro
