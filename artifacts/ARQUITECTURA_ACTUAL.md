# Arquitectura Actual (Oficial)

Fecha: 2026-03-05

## Objetivo
Ruta oficial para SHARC + GVSoC con:
- TCP
- perfil double (`rv32imfdcxpulpv2` + `ilp32d`)
- dinamicas y formulacion QP en host
- solve QP en RISC-V (GVSoC)

## Componentes
1. Host/SHARC (CPU)
- Calcula dinamicas de planta.
- Ejecuta lazo por iteracion (`k,t,x,w`).
- Formula QP desde `x,w,u_prev`.

2. Wrapper SHARC
- Lee/escribe pipes de SHARC.
- Envia request TCP al servidor.
- Recibe `u,cost,iterations,cycles,status,t_delay`.

3. Servidor TCP
- Endpoint oficial de control.
- Valida protocolo.
- Construye payload QP host-side y delega solve.

4. GVSoC core
- Gestiona sesion persistente del solver.
- Ejecuta el solve en firmware RISC-V.
- Devuelve solucion y metricas.

5. Firmware RISC-V
- `qp_riscv_runtime.elf`.
- Resuelve QP en worker persistente.

## Flujo por iteracion
1. SHARC entrega `k,t,x,w` al wrapper.
2. Wrapper envia `qp_solve` por TCP.
3. Servidor formula `P,q,A,l,u` en host.
4. GVSoC resuelve QP en RISC-V.
5. Respuesta vuelve al wrapper.
6. Wrapper devuelve `u` a SHARC.

## Codigo clave
- `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py`
- `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`
- `SHARCBRIDGE/scripts/mpc_host_api.py`
- `SHARCBRIDGE/scripts/mpc_legacy_host_solver.py`
- `SHARCBRIDGE/scripts/gvsoc_core.py`
- `SHARCBRIDGE/mpc/qp_riscv_runtime.c`

## Referencia extendida
- `architecture_3/03/26/README.md`
- `architecture_3/03/26/USO_ENTORNO_Y_FLUJO_COMPLETO.md`
