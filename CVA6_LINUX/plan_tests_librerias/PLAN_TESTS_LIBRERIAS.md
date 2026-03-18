# Plan de Validacion de Librerias MPC en CVA6

## Objetivo

Validar, de forma aislada y reproducible, si las librerias necesarias para ejecutar el MPC original de SHARC pueden compilarse y ejecutarse en `CVA6 + Linux + Spike`, antes de integrarlas con SHARC.

## Alcance

- No se toca el flujo actual de `PULP`.
- No se integra todavia con SHARC.
- No se empieza ninguna implementacion del MPC completo hasta cerrar la validacion de toolchain y librerias.
- Todo lo nuevo de esta linea de trabajo debe vivir dentro de:

```text
CVA6_LINUX/plan_tests_librerias/
```

## Regla de paso

No se pasa a la siguiente tarea si la anterior no queda en uno de estos estados:

- `PASS`
- `FAIL` con causa exacta, reproducible y documentada

No vale avanzar con errores sin aislar.

## Estructura prevista dentro de `plan_tests_librerias`

```text
plan_tests_librerias/
├── PLAN_TESTS_LIBRERIAS.md
├── docs/
├── probes/
├── snapshots/
├── host_ref/
├── cva6_app/
├── scripts/
└── results/
```

## Tarea 0. Gate de entorno y toolchain

### Objetivo

Confirmar que el entorno minimo de `CVA6 + Linux + Spike` esta listo antes de probar ninguna libreria.

### Salidas esperadas

- Toolchain Linux de `cva6-sdk` funcional.
- Spike funcional.
- Toolchain `riscv64-unknown-elf` instalada si se quiere usar `riscv-tests` como smoke test adicional.

### Test obligatorio

1. La toolchain Linux responde:

```bash
riscv64-linux-gcc --version
```

2. Spike arranca y apaga:

```bash
install64/bin/spike install64/spike_fw_payload.elf
```

3. Smoke test Linux propio ejecutado dentro de Spike.

### Criterio de paso

- `PASS` si compila y ejecuta un binario Linux RISC-V propio.
- `FAIL` si falla toolchain, runner o empaquetado.

---

## Tarea 1. Inventario exacto de dependencias del MPC original

### Objetivo

Congelar que librerias, headers, flags y puntos de entrada usa realmente el MPC actual que queremos reproducir.

### Trabajo

1. Identificar librerias exactas del controlador.
2. Identificar versiones o commits si aplica.
3. Identificar el punto minimo del controlador que hay que replicar.
4. Identificar dependencias transitivas relevantes.

### Artefactos previstos

- `docs/mpc_dependency_inventory.md`
- `docs/mpc_entrypoints.md`

### Test obligatorio

El inventario debe dejar cerrados, como minimo:

- librerias usadas
- modo de compilacion
- precision numerica
- binario o funcion minima a reproducir
- dependencias C/C++ necesarias

### Criterio de paso

- `PASS` si el inventario permite construir probes aislados sin ambiguedad.

---

## Tarea 2. Probe de compatibilidad de Eigen

### Objetivo

Comprobar si `Eigen` compila, enlaza y ejecuta correctamente en `CVA6 Linux`.

### Trabajo

1. Crear un probe minimo de matrices en `double`.
2. Probar:
   - multiplicacion
   - resolucion lineal simple
   - factorizacion sencilla
3. Compilar para host y para `riscv64 Linux`.
4. Ejecutar el binario en Spike.

### Artefactos previstos

- `probes/eigen_probe.cpp`
- `scripts/build_eigen_probe.sh`
- `scripts/run_eigen_probe_spike.sh`
- `results/eigen_probe_host.txt`
- `results/eigen_probe_cva6.txt`

### Test obligatorio

1. Compila en host.
2. Compila en `riscv64 Linux`.
3. Ejecuta dentro de Spike.
4. Los valores numericos coinciden con host dentro de tolerancia fijada.

### Criterio de paso

- `PASS` si `Eigen` funciona en build y runtime.
- `FAIL` si se aisla un problema de compilacion, linking o runtime.

---

## Tarea 3. Probe de compatibilidad de OSQP

### Objetivo

Comprobar si `OSQP` puede compilarse y resolver un QP pequeno en `CVA6 Linux`.

### Trabajo

1. Integrar `OSQP` minimo en esta carpeta.
2. Crear un QP de tamano pequeno con solucion conocida.
3. Compilar y ejecutar en host.
4. Compilar y ejecutar en Spike.

### Artefactos previstos

- `probes/osqp_probe.c`
- `scripts/build_osqp_probe.sh`
- `scripts/run_osqp_probe_spike.sh`
- `results/osqp_probe_host.json`
- `results/osqp_probe_cva6.json`

### Test obligatorio

1. El solver devuelve estado valido.
2. La solucion coincide con host dentro de tolerancia.
3. Se registran iteraciones, residual y estado del solver.

### Criterio de paso

- `PASS` si `OSQP` queda validado en `CVA6 Linux`.
- `FAIL` si se documenta con precision la incompatibilidad.

---

## Tarea 4. Probe de compatibilidad de libmpc o libreria de formulacion

### Objetivo

Comprobar si la libreria que formula el MPC original entra en este entorno.

### Trabajo

1. Integrar la libreria exacta que use el controlador del SHARC actual.
2. Crear un probe que construya el controlador y formule un caso minimo.
3. Ejecutarlo en host y en Spike.

### Artefactos previstos

- `probes/libmpc_probe.cpp`
- `scripts/build_libmpc_probe.sh`
- `scripts/run_libmpc_probe_spike.sh`
- `results/libmpc_probe_host.json`
- `results/libmpc_probe_cva6.json`

### Test obligatorio

1. La libreria compila y enlaza.
2. El probe se ejecuta.
3. Devuelve dimensiones y estructuras de formulacion validas.

### Criterio de paso

- `PASS` si la libreria de formulacion funciona.
- `FAIL` si el problema queda aislado a symbols, headers, ABI o runtime.

---

## Tarea 5. Congelacion de snapshots reales del MPC

### Objetivo

Usar entradas reales del controlador sin depender todavia de la integracion con SHARC en tiempo real.

### Trabajo

1. Capturar snapshots reales del flujo actual:
   - `x`
   - `w`
   - `u_prev`
   - parametros necesarios
2. Guardarlos en formato estable y simple.
3. Crear lector comun para host y CVA6.

### Artefactos previstos

- `snapshots/snapshot_001.json`
- `snapshots/snapshot_002.json`
- `snapshots/snapshot_003.json`
- `scripts/validate_snapshots.py`

### Test obligatorio

1. Los snapshots cargan correctamente.
2. Con un snapshot se puede invocar el controlador standalone completo.

### Criterio de paso

- `PASS` si los snapshots son suficientes para un replay del MPC.

---

## Tarea 6. Runner standalone del MPC en host

### Objetivo

Construir una referencia congelada del MPC completo fuera de SHARC usando snapshots reales.

### Trabajo

1. Crear un ejecutable standalone en host.
2. Cargar snapshots.
3. Ejecutar el MPC completo.
4. Guardar:
   - formulacion
   - solucion del solver
   - control final

### Artefactos previstos

- `host_ref/mpc_snapshot_host.cpp`
- `scripts/build_host_ref.sh`
- `results/host_snapshot_001.json`

### Test obligatorio

1. El runner produce resultados deterministas.
2. La salida queda guardada en JSON comparable.

### Criterio de paso

- `PASS` si existe una referencia host congelada y reproducible.

---

## Tarea 7. Runner standalone del MPC en CVA6

### Objetivo

Ejecutar el MPC completo en `CVA6 Linux` con los mismos snapshots usados en host.

### Trabajo

1. Crear un ejecutable `riscv64 Linux` del MPC standalone.
2. Copiarlo al rootfs/overlay.
3. Ejecutarlo automaticamente dentro de Spike.
4. Exportar resultados.

### Artefactos previstos

- `cva6_app/mpc_snapshot_cva6.cpp`
- `scripts/build_cva6_app.sh`
- `scripts/package_rootfs_app.sh`
- `scripts/run_spike_noninteractive.sh`
- `results/cva6_snapshot_001.json`

### Test obligatorio

1. El binario arranca sin interaccion manual.
2. Procesa snapshots reales.
3. Devuelve resultados comparables con host.

### Criterio de paso

- `PASS` si el MPC standalone corre completo en `CVA6 Linux`.

---

## Tarea 8. Gate de paridad host vs CVA6

### Objetivo

Comparar si el MPC ejecutado en `CVA6 Linux` reproduce el comportamiento del host.

### Trabajo

1. Comparar formulacion:
   - `P`
   - `q`
   - `A`
   - `l`
   - `u`
2. Comparar solucion:
   - estado del solver
   - iteraciones
   - residual
   - vector solucion
3. Comparar control final:
   - `u_accel`
   - `u_brake`

### Artefactos previstos

- `scripts/compare_results.py`
- `results/parity_report.json`
- `results/parity_report.md`

### Test obligatorio

1. Error de formulacion dentro de tolerancia.
2. Error de salida de control dentro de tolerancia.
3. Informe con `PASS` o `FAIL` y causa exacta.

### Criterio de paso

- Solo si esta tarea pasa se abre la integracion con SHARC.

---

## Tarea 9. Decision de integracion con SHARC

### Objetivo

Decidir con evidencia si ya tiene sentido conectar este nuevo camino con SHARC.

### Trabajo

1. Revisar resultados de compatibilidad de librerias.
2. Revisar runner standalone.
3. Revisar paridad host vs CVA6.
4. Abrir plan especifico de integracion con SHARC solo si los gates anteriores pasan.

### Test obligatorio

Checklist cerrada:

- `Eigen` validado
- `OSQP` validado
- libreria de formulacion validada
- MPC standalone validado
- paridad host vs CVA6 validada

### Criterio de paso

- Si cualquier punto falla, no se integra con SHARC todavia.

---

## Prioridad real de ejecucion

Orden obligatorio:

1. Tarea 0
2. Tarea 1
3. Tarea 2
4. Tarea 3
5. Tarea 4
6. Tarea 5
7. Tarea 6
8. Tarea 7
9. Tarea 8
10. Tarea 9

## Nota de control

Mientras no termine la instalacion de la toolchain que estas montando ahora, este plan no entra en fase de ejecucion. De momento queda como hoja de ruta y estructura de validacion.
