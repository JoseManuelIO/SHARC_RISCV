# Plan Maestro SHARC-CVA6

## Objetivo final

Integrar SHARC con un backend `CVA6 Linux` para ejecutar el controlador MPC usando las mismas librerias del stack original de SHARC, sin modificar SHARC y reutilizando la mayor parte posible de la arquitectura ya validada en `SHARCBRIDGE`.

## Restricciones duras

1. `sharc_original` no se modifica.
2. SHARC solo entrega las dinamicas y recibe el control.
3. El wrapper sigue siendo el punto de acoplamiento con SHARC.
4. El transporte oficial es `TCP`.
5. El MPC en CVA6 debe usar:
   - `libmpc`
   - `Eigen`
   - `OSQP`
6. La evidencia de tareas y tests debe quedar en `artifacts_cva6/`.
7. Los archivos del flujo principal deben quedar en `SHARCBRIDGE_CVA6/`.

## Reutilizacion del caso PULP

### Se reutiliza

- Patron `SHARC -> wrapper -> TCP server -> backend`
- Contrato de entrada/salida del wrapper
- Scripts E2E
- Generacion de imagen/rootfs
- Gates de validacion
- Extraccion de metadata
- Filosofia de backend persistente

### Se sustituye

- Runtime `PULP/GVSoC`
- Toolchain y target bare-metal
- Backend de ejecucion del solver/control

### Se conserva como referencia directa

- `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py`
- `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`
- `SHARCBRIDGE/scripts/run_gvsoc_config.sh`
- `SHARCBRIDGE/scripts/run_gvsoc_figure5_tcp.sh`
- `SHARCBRIDGE/scripts/tcp_protocol.py`

## Arquitectura objetivo

1. SHARC genera `k, t, x, w, u_prev`.
2. El wrapper CVA6 lee esos datos sin cambiar SHARC.
3. El wrapper envia una peticion TCP al backend CVA6.
4. El backend CVA6 prepara la entrada para el runtime Linux.
5. El runtime CVA6 ejecuta el controlador MPC original:
   - formula el problema con `libmpc`
   - usa `Eigen`
   - resuelve con `OSQP`
6. El backend recoge:
   - `u`
   - `status`
   - `iterations`
   - `cost`
   - metadata util
7. El wrapper devuelve el control a SHARC.

## Estructura objetivo del flujo principal

Los nombres pueden ajustarse en implementacion, pero la separacion debe ser esta:

- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`
- `SHARCBRIDGE_CVA6/cva6_tcp_server.py`
- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`
- `SHARCBRIDGE_CVA6/run_cva6_config.sh`
- `SHARCBRIDGE_CVA6/run_cva6_e2e.sh`
- `SHARCBRIDGE_CVA6/ARCHITECTURE.md`

## Tareas del plan

### Tarea 0. Congelar la arquitectura base a reutilizar

#### Objetivo

Fijar exactamente que partes del flujo PULP se reutilizan y cuales cambian en el backend CVA6.

#### Trabajo

1. Inventariar wrapper, TCP server, scripts E2E y protocolo actual.
2. Fijar el contrato minimo:
   - entrada desde SHARC
   - peticion TCP
   - respuesta del backend
3. Documentar la arquitectura objetivo.

#### Salidas principales

- `SHARCBRIDGE_CVA6/ARCHITECTURE.md`
- `artifacts_cva6/t0_architecture_reuse.md`

#### Test obligatorio

1. El contrato wrapper/backend queda escrito.
2. Se identifica por fichero que se reutiliza y que se reemplaza.

#### Criterio de paso

- `PASS` si la arquitectura queda cerrada sin ambiguedad.

---

### Tarea 1. Crear el wrapper CVA6 sin tocar SHARC

#### Objetivo

Construir un wrapper nuevo, derivado del caso PULP, que mantenga la interfaz esperada por SHARC.

#### Trabajo

1. Duplicar la logica util del wrapper actual.
2. Eliminar dependencias especificas de GVSoC.
3. Mantener:
   - lectura de `k, t, x, w`
   - control del proceso
   - salida compatible con SHARC
4. Conectar el wrapper a un cliente TCP CVA6.

#### Salidas principales

- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`

#### Test obligatorio

1. El wrapper acepta entradas con el mismo formato que SHARC.
2. El wrapper puede serializar una peticion TCP valida.
3. El wrapper puede devolver una respuesta simulada al formato que espera SHARC.

#### Evidencia

- `artifacts_cva6/t1_wrapper_contract.json`
- `artifacts_cva6/t1_wrapper_smoke.md`

#### Criterio de paso

- `PASS` si SHARC podria cambiar de wrapper sin cambiar su codigo.

---

### Tarea 2. Crear el backend TCP para CVA6

#### Objetivo

Reusar la arquitectura del servidor TCP anterior, pero sustituyendo el backend PULP por el runtime CVA6.

#### Trabajo

1. Derivar el servidor desde `gvsoc_tcp_server.py`.
2. Mantener el framing/protocolo TCP.
3. Crear comandos minimos:
   - `health`
   - `run_snapshot`
   - `shutdown`
4. Conectar el servidor con el launcher CVA6.

#### Salidas principales

- `SHARCBRIDGE_CVA6/cva6_tcp_server.py`
- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`

#### Test obligatorio

1. El servidor arranca.
2. Responde a `health`.
3. Ejecuta un snapshot fijo y devuelve JSON valido.

#### Evidencia

- `artifacts_cva6/t2_tcp_health.log`
- `artifacts_cva6/t2_tcp_roundtrip.json`

#### Criterio de paso

- `PASS` si el backend TCP ya puede resolver snapshots fuera de SHARC.

---

### Tarea 3. Integrar el runtime CVA6 Linux con el MPC original

#### Objetivo

Ejecutar el controlador MPC usando el stack original de SHARC en el entorno CVA6 Linux.

#### Trabajo

1. Empaquetar en la imagen CVA6:
   - binario del controlador
   - config base
   - runtime launcher
2. Reusar el conocimiento ya validado:
   - `libmpc`
   - `Eigen`
   - `OSQP`
3. Mantener la configuracion determinista de `OSQP` validada:
   - `adaptive_rho = true`
   - `adaptive_rho_interval = 25`
   - `profiling = on`

#### Salidas principales

- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`
- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`

#### Test obligatorio

1. El runtime arranca dentro de CVA6.
2. Ejecuta snapshots reales.
3. Devuelve control y metadata validos.

#### Evidencia

- `artifacts_cva6/t3_runtime_smoke.log`
- `artifacts_cva6/t3_snapshot_outputs.json`

#### Criterio de paso

- `PASS` si el backend CVA6 resuelve el MPC original fuera de SHARC.

---

### Tarea 4. Generacion automatica de imagen y rootfs

#### Objetivo

Reproducir la filosofia del flujo PULP: que el entorno ejecutable se genere por script y no manualmente.

#### Trabajo

1. Crear builder de imagen/rootfs para CVA6.
2. Copiar binarios y configs automaticamente.
3. Dejar un script reproducible para rehacer el payload.

#### Salidas principales

- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`

#### Test obligatorio

1. La imagen se genera desde cero.
2. El binario objetivo queda dentro del rootfs.
3. Se puede relanzar el entorno sin pasos manuales.

#### Evidencia

- `artifacts_cva6/t4_image_build.log`
- `artifacts_cva6/t4_rootfs_manifest.txt`

#### Criterio de paso

- `PASS` si la imagen es reproducible y automatizada.

---

### Tarea 5. E2E corto sin tocar SHARC

#### Objetivo

Validar el flujo completo wrapper -> TCP -> CVA6 -> respuesta, todavia sin integrarlo dentro del lazo real de SHARC.

#### Trabajo

1. Preparar un runner corto con snapshots o inputs congelados.
2. Ejecutar el flujo completo como servicio.
3. Registrar control y metadata.

#### Salidas principales

- `SHARCBRIDGE_CVA6/run_cva6_config.sh`

#### Test obligatorio

1. El wrapper se conecta al backend TCP.
2. El backend ejecuta el MPC en CVA6.
3. La respuesta vuelve completa.

#### Evidencia

- `artifacts_cva6/t5_e2e_short.log`
- `artifacts_cva6/t5_e2e_short.json`

#### Criterio de paso

- `PASS` si el E2E corto funciona sin modificar SHARC.

---

### Tarea 6. Integracion real con SHARC

#### Objetivo

Sustituir el backend experimental por el camino real controlado desde SHARC, manteniendo SHARC intacto.

#### Trabajo

1. Montar el wrapper CVA6 en el punto donde SHARC espera el wrapper.
2. Arrancar servidor TCP y runtime CVA6 desde script E2E.
3. Ejecutar un run corto real con SHARC.

#### Salidas principales

- `SHARCBRIDGE_CVA6/run_cva6_e2e.sh`

#### Test obligatorio

1. SHARC arranca sin cambios internos.
2. SHARC envia dinamicas al wrapper.
3. El wrapper devuelve controles validos desde CVA6.

#### Evidencia

- `artifacts_cva6/t6_sharc_short.log`
- `artifacts_cva6/t6_sharc_short_plots.png`

#### Criterio de paso

- `PASS` si SHARC corre usando el nuevo backend CVA6.

---

### Tarea 7. Gate de paridad funcional

#### Objetivo

Comprobar que el nuevo camino CVA6 reproduce el comportamiento esperado del controlador.

#### Trabajo

1. Comparar salida de control entre host y CVA6.
2. Comparar metadata relevante.
3. Confirmar que la configuracion determinista de `OSQP` se mantiene.

#### Test obligatorio

1. Paridad funcional de `u`.
2. Paridad de iteraciones.
3. Paridad de coste dentro de tolerancia.

#### Evidencia

- `artifacts_cva6/t7_parity_report.json`
- `artifacts_cva6/t7_parity_report.md`

#### Criterio de paso

- `PASS` si el comportamiento del controlador queda alineado con la referencia.

---

### Tarea 8. Decision de oficializacion del flujo

#### Objetivo

Decidir si el camino `SHARC + CVA6` ya puede pasar a ser flujo principal del nuevo backend.

#### Trabajo

1. Revisar resultados de T0-T7.
2. Confirmar reproducibilidad.
3. Emitir decision tecnica.

#### Test obligatorio

1. Existe un script E2E unico.
2. Existe una imagen reproducible.
3. Existe paridad funcional cerrada.

#### Evidencia

- `artifacts_cva6/t8_final_decision.md`

#### Criterio de paso

- `PASS` si el flujo esta listo para iterar ya sobre integracion real y resultados.

## Recomendacion de implementacion

El orden recomendado es este:

1. `T0`
2. `T1`
3. `T2`
4. `T3`
5. `T4`
6. `T5`
7. `T6`
8. `T7`
9. `T8`

No se debe abrir la integracion real con SHARC antes de cerrar `T5`.

## Nota tecnica critica

La experiencia previa en `CVA6_LINUX/plan_tests_librerias/` ya ha demostrado dos cosas que deben respetarse en este nuevo plan:

1. El stack `libmpc + Eigen + OSQP` es viable en `CVA6 Linux`.
2. Para cerrar la paridad entre host y `CVA6`, `OSQP` debe evitar un `adaptive_rho_interval` dependiente del tiempo de setup.

Por tanto, el nuevo flujo debe incorporar desde el principio una configuracion determinista de `OSQP`.
