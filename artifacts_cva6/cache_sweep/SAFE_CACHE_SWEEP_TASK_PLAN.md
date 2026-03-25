# Plan Seguro Por Tareas Para El Barrido De Cachés Con Spike

Fecha: 2026-03-25

## Objetivo

Construir un barrido de cachés para la Figure 5 usando `Spike`, manteniendo el
flujo principal estable y evitando volver a romper el `payload` bueno.

## Baseline Protegido

El baseline que no se debe romper es el ya validado:

- comando principal: `./run_cva6_figure5_tcp.sh`
- `SDK` bueno: `/tmp/cva6-sdk-clean-20260324-r1-2`
- `payload` bueno: `/tmp/cva6-sdk-clean-20260324-r1-2/install64/spike_fw_payload.elf`
- validación actual:
  - `artifacts_cva6/figure5_recovery/results/s5_simple_flow_validation.md`

## Reglas De Seguridad

1. No ejecutar el barrido con `CVA6_SKIP_BUILD=0`.
2. No reconstruir `payload`, `Image` ni `vmlinux` durante esta línea de trabajo.
3. No tocar `CVA6_LINUX/cva6-sdk` ni el `SDK` limpio salvo evidencia fuerte y
   tarea explícita.
4. Usar siempre puerto nuevo en las pruebas de barrido.
5. Toda prueba, runner, parser, matriz y log vive en `artifacts_cva6/cache_sweep/`.
6. No pasar a la siguiente tarea mientras la anterior no tenga `PASS`.
7. Antes y después de cada tarea que toque la ruta principal, verificar que el
   hash del `payload` bueno no ha cambiado.

## Artefactos De Seguridad Obligatorios

Se mantendrá un manifest de referencia con:

- `spike_fw_payload.elf`
- `vmlinux` si aplica
- `Image` si aplica
- `rootfs.cpio` si aplica
- `SDK dir` usado
- `Spike bin` usado

## Tareas

### C0 - Congelar El Baseline Y El Manifest Del Payload

Objetivo:

- fijar una huella del baseline antes de tocar integración de caché

Trabajo:

- registrar:
  - comando baseline actual
  - `SDK dir`
  - `Spike bin`
  - `payload`
  - hashes de los binarios protegidos
- enlazar la validación actual de Figure 5

Test / Gate:

- existe un manifest reproducible del baseline protegido
- el baseline sigue en `PASS`

Salida:

- `results/c0_safe_baseline_manifest.md`
- `results/c0_safe_baseline_manifest.json`

### C1 - Auditar El Estado Real De La Integración De Caché

Objetivo:

- resolver la discrepancia entre el plan antiguo y el código actual

Trabajo:

- comprobar si la ruta principal actual sigue soportando:
  - `SPIKE_CACHE_ARGS`
  - propagación al comando de `Spike`
  - trazabilidad en metadata/logs
- documentar si la integración antigua sigue viva o se perdió

Test / Gate:

- queda cerrada la verdad actual del código
- no se toca todavía el baseline

Salida:

- `results/c1_cache_integration_audit.md`

### C2 - Diseñar La Reintegración Mínima Y Segura

Objetivo:

- definir la modificación mínima necesaria en `SHARCBRIDGE_CVA6`

Trabajo:

- limitar la interfaz a una sola variable:
  - `SPIKE_CACHE_ARGS`
- decidir exactamente dónde se inyecta:
  - launcher
  - y, solo si hace falta, script principal
- definir qué metadatos mínimos se deben exponer:
  - `spike_cache_args`
  - identificación del caso

Test / Gate:

- existe un diseño que no requiere rebuild del `payload`
- el cambio previsto en `SHARCBRIDGE_CVA6` es mínimo y acotado

Salida:

- `results/c2_safe_integration_design.md`

### C3 - Implementar La Inyección De Caché Sin Tocar El Payload

Objetivo:

- permitir pasar flags de caché a `Spike` sin tocar el guest ni reconstruir imágenes

Trabajo:

- implementar solo la propagación de:
  - `--ic`
  - `--dc`
  - `--l2`
  - `--log-cache-miss`
- asegurar compatibilidad total cuando `SPIKE_CACHE_ARGS` está vacío

Test / Gate:

- baseline sin caché sigue funcionando
- el hash del `payload` protegido no cambia antes/después
- una ejecución controlada muestra que los args llegan al launcher

Salida:

- `results/c3_injection_runtime_gate.md`

### C4 - Prueba Controlada De Dos Casos

Objetivo:

- demostrar que la integración funciona en runtime antes del sweep

Trabajo:

- ejecutar solo dos casos:
  - `baseline`
  - `cache_smoke_small`
- usar puertos nuevos y salidas separadas
- comprobar que cada caso deja evidencia distinta de `spike_cache_args`

Test / Gate:

- ambos casos completan Figure 5 o al menos el gate runtime acordado
- el baseline sigue sano
- el `payload` sigue intacto

Salida:

- `results/c4_two_case_runtime_validation.md`

### C5 - Congelar La Matriz De Barrido

Objetivo:

- definir un sweep útil y acotado, ya sobre una integración probada

Trabajo:

- revisar o refinar:
  - `cache_sweep_matrix.json`
- mantener solo configuraciones defendibles:
  - baseline
  - pequeña
  - media
  - grande
  - con/sin L2
- descartar explosión combinatoria innecesaria

Test / Gate:

- la matriz queda cerrada y razonable
- cada caso tiene nombre, args y propósito claro

Salida:

- `configs/cache_sweep_matrix.json`
- `results/c5_final_cache_matrix.md`

### C6 - Runner Experimental Seguro

Objetivo:

- automatizar el sweep sin ensuciar el flujo principal

Trabajo:

- usar o rehacer el runner experimental en:
  - `artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh`
- asegurar:
  - puerto por caso
  - directorio de salida por caso
  - logs por caso
  - manifest agregado
  - cero rebuilds

Test / Gate:

- el runner ejecuta al menos dos casos distintos sin tocar el baseline
- el manifest final identifica claramente qué caso usó qué args

Salida:

- `results/c6_runner_gate.md`
- `results/cache_sweep_manifest.json`

### C7 - Parser De Estadísticas De Caché

Objetivo:

- extraer métricas útiles del `cachesim` de `Spike`

Trabajo:

- localizar y parsear:
  - `Read/Write Accesses`
  - `Read/Write Misses`
  - `Miss Rate`
  - `Writebacks`
  - `Bytes Read/Written`
- convertirlas a formato estructurado

Test / Gate:

- el parser funciona sobre al menos dos runs reales
- los números quedan trazables al log fuente

Salida:

- `scripts/parse_spike_cache_stats.py`
- `results/c7_cache_parser_validation.md`

### C8 - Sweep Completo Y Reporte

Objetivo:

- completar el barrido ya sobre una base segura

Trabajo:

- lanzar la matriz final
- agregar:
  - métricas de caché
  - métricas hardware
  - métricas solver
- producir tabla y figura comparativa

Test / Gate:

- todos los casos terminan o quedan documentados con fallo clasificado
- existe un reporte final comparable por caso
- el baseline protegido sigue intacto

Salida:

- `results/c8_cache_sweep_report.md`
- `results/c8_cache_sweep_table.csv`
- `results/c8_cache_sweep_plot.png`

### C9 - Revalidación Del Flujo Principal

Objetivo:

- cerrar la línea de trabajo demostrando que el flujo simple principal no se degradó

Trabajo:

- relanzar:
  - `./run_cva6_figure5_tcp.sh`
- comparar hashes del manifest protegido contra `C0`

Test / Gate:

- la Figure 5 principal sigue en `PASS`
- el `payload` protegido no cambió

Salida:

- `results/c9_post_sweep_mainline_gate.md`

## Orden De Ejecución Obligatorio

1. `C0`
2. `C1`
3. `C2`
4. `C3`
5. `C4`
6. `C5`
7. `C6`
8. `C7`
9. `C8`
10. `C9`

## Regla De Parada

Si una tarea falla:

- no se avanza a la siguiente
- se guarda evidencia en `artifacts`
- se compara contra el manifest de `C0`
- si el `payload` cambió, se restaura el baseline antes de seguir

## Principio Rector

La prioridad no es “hacer el sweep cuanto antes”.  
La prioridad es:

- mantener vivo el baseline bueno
- introducir la caché solo como parámetro de ejecución
- no volver a mezclar investigación de caché con drift de `payload` o `SDK`
