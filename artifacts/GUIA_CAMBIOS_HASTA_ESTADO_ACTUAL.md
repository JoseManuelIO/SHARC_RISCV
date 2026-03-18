# Guia Unica de Cambios hasta el Estado Actual

Fecha: 2026-03-05

## Objetivo alcanzado
Dejar una ruta oficial estable en la que:
- SHARC mantiene dinamicas en host.
- El solve QP del controlador se ejecuta en RISC-V (GVSoC).
- El transporte oficial es TCP.

## Cambios principales realizados
1. Transporte
- Se migro de HTTP como camino principal a TCP oficial.
- HTTP/Flask queda como fallback no oficial.

2. Ejecucion GVSoC
- Se paso a runtime persistente para evitar relanzar ELF en cada iteracion.
- Se anadieron guardas para impedir fallback silencioso en modo oficial.

3. Solver en RISC-V
- Se habilito ruta `qp_solve` host->GVSoC.
- Formulacion QP sigue en host (c_abi) y solve en firmware RISC-V.

4. Perfil numerico
- Se fijo perfil double en el camino oficial (`rv32imfdcxpulpv2` + `ilp32d`).

5. Validacion y calidad
- Se consolidaron gates T3 (paridad formulacion), T8 (fidelidad), T9 (repeatability hardware), T10 (verificacion final).
- Se unifico verificacion en `verify_final_official.sh`.

## Estado actual
- Pipeline oficial ejecutable de extremo a extremo.
- Plots y metricas hardware generables en cada corrida.
- Base lista para siguientes pasos de migracion y comparativa final.

## Comandos de comprobacion
```bash
bash SHARCBRIDGE/scripts/verify_final_official.sh
```
