# Plan De Recuperacion

Fecha: 2026-03-24

## Objetivo

Recuperar el flujo de `Figure 5` de SHARC con backend `CVA6/Spike` partiendo de que ya funciono antes, priorizando restauracion de estado conocido bueno frente a rediseño.

## Restricciones

- `sharc_original/` no se toca.
- `SHARCBRIDGE/` no recibe pruebas, logs ni scripts auxiliares nuevos.
- `SHARCBRIDGE_CVA6/` solo puede cambiar en:
  - `cva6_image_builder.sh`
  - `cva6_runtime_launcher.py`
  - `cva6_tcp_server.py`
  - `run_cva6_figure5_tcp.sh`
  - `cva6_controller_wrapper.py`
- Todo lo demas va en `artifacts_cva6/figure5_recovery/`.

## Estrategia

1. Congelar el baseline que si funciono.
2. Recuperar el guest/payload hasta que el runtime exista dentro de Linux.
3. Validar backend por capas.
4. Ejecutar `Figure 5` completa.
5. Limpiar el diff final para que en `SHARCBRIDGE_CVA6/` quede solo lo imprescindible.

## Tarea 0 - Congelar baseline y drift actual

Objetivo:

- fijar el baseline conocido bueno,
- fijar el estado actual roto,
- evitar diagnosticos cambiantes durante la recuperacion.

Trabajo:

- registrar commit del repo principal y commits/estado de `CVA6_LINUX/cva6-sdk` y `CVA6_LINUX/cva6`,
- registrar artefactos buenos ya existentes del `2026-03-18`,
- registrar artefactos actuales regenerados del `2026-03-23`,
- guardar tamanos, fechas y rutas de `vmlinux`, `spike_fw_payload.elf` y runtime.

Test:

- `bash artifacts_cva6/figure5_recovery/scripts/t0_baseline_audit.sh`

PASS:

- existe un inventario reproducible del baseline bueno y del drift actual.

Artefactos:

- `results/t0_baseline_audit.md`
- `results/t0_nested_repos_status.txt`
- `results/t0_artifact_inventory.txt`

## Tarea 1 - Probar el guest real y aislar la causa de runtime missing

Objetivo:

- demostrar dentro del guest si el runtime falta de verdad o si falla por loader/librerias.

Trabajo:

- arrancar `spike_persistent` fuera del flujo completo,
- ejecutar dentro del guest:
  - `test -x /usr/bin/sharc_cva6_acc_runtime`
  - `ls -l /usr/bin/sharc_cva6_acc_runtime`
  - `ls -l /usr/share/sharcbridge_cva6/base_config.json`
  - chequeo de interpreter o librerias si el binario aparece pero no arranca,
- guardar transcripcion completa del guest.

Test:

- `python3 artifacts_cva6/figure5_recovery/scripts/t1_guest_runtime_probe.py`

PASS:

- el guest llega a shell y queda clasificada una sola causa:
  - `runtime_absent`,
  - `runtime_present_but_loader_missing`,
  - `runtime_present_and_executable`.

Artefactos:

- `logs/t1_guest_runtime_probe.log`
- `results/t1_guest_runtime_probe.json`
- `results/t1_guest_runtime_probe.md`

## Tarea 2 - Restaurar o reinstalar el SDK/buildroot hasta obtener guest bueno

Objetivo:

- volver a un payload/rootfs que contenga el runtime usable dentro del guest.

Trabajo:

- comparar el estado actual de `cva6-sdk` con el baseline,
- limpiar drift no esencial del SDK,
- reconstruir payload con procedimiento controlado,
- si eso no devuelve un guest sano, reinstalar en limpio:
  - `CVA6_LINUX/cva6-sdk`
  - dependencias necesarias del SDK
  - buildroot/toolchain afectado
- reaplicar solo los cambios minimos realmente necesarios para este flujo.

Test:

- `bash artifacts_cva6/figure5_recovery/scripts/t2_sdk_restore_gate.sh`

PASS:

- tres arranques consecutivos del guest muestran:
  - runtime visible,
  - base config visible,
  - sin `not found` al invocar el runtime.

Artefactos:

- `logs/t2_sdk_restore_gate.log`
- `results/t2_sdk_restore_report.md`
- `results/t2_guest_manifest.txt`

## Tarea 3 - Validar backend CVA6 por snapshots antes de SHARC

Objetivo:

- confirmar que `launcher + tcp server + runtime` responden establemente sin meter aun `Figure 5`.

Trabajo:

- reusar primero tests existentes:
  - `artifacts_cva6/t2_tcp_smoke.py`
  - `artifacts_cva6/t3_runtime_smoke.py`
- si no bastan, crear probe dedicado en esta carpeta,
- validar `health`,
- validar `run_snapshot`,
- validar `spike_persistent` como modo principal,
- dejar `spike` oneshot solo como diagnostico secundario.

Test:

- `python3 artifacts_cva6/figure5_recovery/scripts/t3_backend_smoke.py --mode spike_persistent --snapshots 5`

PASS:

- cinco snapshots consecutivos responden `SUCCESS`,
- no hay `BACKEND_TIMEOUT`,
- no hay `END OF PIPE`,
- no se cae el servidor TCP.

Artefactos:

- `logs/t3_backend_smoke.log`
- `results/t3_backend_smoke.json`
- `results/t3_backend_smoke.md`

## Tarea 4 - Validar contrato wrapper-delay con SHARC en escenario corto

Objetivo:

- asegurar que el backend ya recuperado vuelve a hablar el contrato que SHARC espera.

Trabajo:

- ejecutar escenario corto controlado,
- revisar `cva6_wrapper_trace.ndjson`,
- revisar generacion de `gvsoc_cycles_<k>.txt`,
- revisar que el wrapper no rompa el pipe al primer fallo,
- validar ambos caminos:
  - `baseline-no-delay-onestep`
  - `cva6-real-delays`

Test:

- `bash artifacts_cva6/figure5_recovery/scripts/t4_wrapper_contract_gate.sh`

PASS:

- el escenario corto genera al menos:
  - `simulation_data_incremental.json`
  - `cva6_wrapper_trace.ndjson`
  - `gvsoc_cycles_0.txt`
- SHARC consume los delays sin tocar `sharc_original`.

Artefactos:

- `logs/t4_wrapper_contract_gate.log`
- `results/t4_wrapper_contract_gate.md`

## Tarea 5 - Recuperar Figure 5 oficial end-to-end

Objetivo:

- volver a obtener la figura y los dos experimentos completos con el flujo productivo.

Trabajo:

- ejecutar `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`,
- usar `spike_persistent` como modo oficial mientras siga siendo el camino validado,
- no avanzar hasta recuperar las salidas finales equivalentes a las del `2026-03-18`.

Test:

- `CVA6_SKIP_BUILD=1 CVA6_RUNTIME_MODE=spike_persistent bash SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`

PASS:

- existen:
  - `latest/plots.png`
  - `latest/experiment_list_data_incremental.json`
  - `baseline-no-delay-onestep/simulation_data_incremental.json`
  - `cva6-real-delays/simulation_data_incremental.json`

Artefactos:

- `logs/t5_figure5_e2e.log`
- `results/t5_figure5_e2e.md`
- `results/t5_output_paths.txt`

## Tarea 6 - Cerrar el diff minimo y documentar el estado final

Objetivo:

- que el repo quede limpio y mantenible,
- que `SHARCBRIDGE_CVA6/` solo conserve lo imprescindible.

Trabajo:

- mover todo experimento auxiliar a esta carpeta,
- revisar que no queden probes o scripts temporales dentro de `SHARCBRIDGE` o `SHARCBRIDGE_CVA6`,
- documentar exactamente que archivos del flujo principal tuvieron que quedar modificados y por que.

Test:

- `bash artifacts_cva6/figure5_recovery/scripts/t6_repo_hygiene_gate.sh`

PASS:

- los cambios permanentes quedan limitados al flujo productivo,
- los artefactos de trabajo quedan solo en `artifacts_cva6/figure5_recovery/`.

Artefactos:

- `results/t6_repo_hygiene.md`
- `results/t6_final_change_set.txt`

## Regla De Escalado

Si Tarea 2 no alcanza `PASS` tras:

- una limpieza controlada,
- y una reconstruccion completa del payload,

se pasa a reinstalacion completa del SDK/buildroot en vez de seguir parcheando.

## Orden obligatorio

1. Tarea 0
2. Tarea 1
3. Tarea 2
4. Tarea 3
5. Tarea 4
6. Tarea 5
7. Tarea 6

No se avanza a la siguiente tarea sin cerrar el test de la actual.

