# Plan De Reinstalacion Por Partes

Fecha: 2026-03-24

## Objetivo

Reinstalar `CVA6_LINUX/cva6-sdk` de la forma mas segura posible, sin romper el
estado actual del repo y validando cada fase antes de avanzar al flujo de
`Figure 5`.

## Principios De Seguridad

- No borrar ni sobrescribir `CVA6_LINUX/cva6-sdk` al inicio.
- No usar `make clean` dentro del SDK activo del repo principal.
- No seguir la punta actual de GitHub; fijar el SDK a un commit exacto.
- Validar el SDK reinstalado en una ruta aislada antes de hacer cutover.
- Mantener siempre una copia recuperable del triplete actual:
  - `install64/vmlinux`
  - `install64/Image`
  - `install64/spike_fw_payload.elf`

## Referencia Fija

- SDK actual local: `77fc4a9`
- evidencia del riesgo de reinstalacion in-place:
  - `artifacts_cva6/figure5_recovery/results/c8_clean_sdk_reinstall_report.md`

## Ruta Recomendada

- SDK limpio temporal en `/tmp/cva6-sdk-clean`
- Validacion apuntando `CVA6_SDK_DIR=/tmp/cva6-sdk-clean`
- Solo si pasa todo, sustituir el SDK del repo o copiar sus artefactos buenos

## R0 - Congelar Estado Y Rollback

Objetivo:

- poder volver atras en cualquier momento

Trabajo:

- copiar a backup:
  - `install64/vmlinux`
  - `install64/Image`
  - `install64/spike_fw_payload.elf`
  - `CVA6_LINUX/cva6-sdk/install64/vmlinux`
  - `CVA6_LINUX/cva6-sdk/install64/Image`
  - `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
- guardar manifest de hashes y timestamps
- guardar commit del repo principal y del SDK

Test / Gate:

- el backup existe y los hashes del backup coinciden con el estado original

Artefactos:

- `results/r0_reinstall_backup_manifest.txt`
- `results/r0_reinstall_backup_report.md`

## R1 - Preparar SDK Limpio Aislado

Objetivo:

- tener un `cva6-sdk` limpio sin tocar el SDK activo

Trabajo:

- crear `/tmp/cva6-sdk-clean`
- poblarlo desde fuente limpia
- fijarlo al commit `77fc4a9`
- inicializar submodulos de esa copia limpia

Nota:

- si se usa GitHub, clonar recursivo y hacer checkout exacto a `77fc4a9`
- no usar `main`, `master` ni `latest`

Test / Gate:

- `git rev-parse --short HEAD` en `/tmp/cva6-sdk-clean` devuelve `77fc4a9`
- los submodulos requeridos existen

Artefactos:

- `results/r1_clean_sdk_source_report.md`

## R2 - Verificar Prerrequisitos Del SDK Limpio

Objetivo:

- asegurar que la copia limpia puede compilar antes de gastar tiempo en la
  imagen completa

Trabajo:

- comprobar toolchain host, buildroot y spike
- compilar el paso base mas barato primero

Test / Gate:

- `make -C /tmp/cva6-sdk-clean gcc`: PASS

Artefactos:

- `logs/r2_make_gcc.log`
- `results/r2_make_gcc_report.md`

## R3 - Construir Imagen Linux Del SDK Limpio

Objetivo:

- obtener artefactos base del SDK limpio

Trabajo:

- construir `vmlinux`
- construir `Image`
- construir `spike_fw_payload.elf`
- registrar hashes de:
  - `buildroot/output/images/rootfs.cpio`
  - `install64/vmlinux`
  - `install64/Image`
  - `install64/spike_fw_payload.elf`

Test / Gate:

- los cuatro artefactos existen y tienen hash registrado

Artefactos:

- `logs/r3_sdk_images_build.log`
- `results/r3_sdk_images_manifest.txt`
- `results/r3_sdk_images_report.md`

## R4 - Integrar Runtime SHARC En El SDK Limpio

Objetivo:

- comprobar que el overlay y la imagen para SHARC se pueden regenerar en el SDK
  limpio

Trabajo:

- ejecutar la logica de `SHARCBRIDGE_CVA6/cva6_image_builder.sh` contra
  `/tmp/cva6-sdk-clean`
- comprobar que se generan:
  - `buildroot/output/target/usr/bin/sharc_cva6_acc_runtime`
  - `buildroot/output/target/usr/share/sharcbridge_cva6/base_config.json`
  - nuevo `spike_fw_payload.elf`

Test / Gate:

- runtime y config existen en el target del SDK limpio
- el payload se vuelve a generar sin error

Artefactos:

- `logs/r4_sharc_image_build.log`
- `results/r4_sharc_image_report.md`

## R5 - Validar Boot Del Guest Limpio

Objetivo:

- no pasar a SHARC si el guest limpio ni siquiera arranca bien

Trabajo:

- arrancar Spike con el payload del SDK limpio
- verificar llegada a Linux y shell

Test / Gate:

- el guest alcanza al menos:
  - `Run /init as init process`
  - `Starting sshd: OK`
  - `#`

Artefactos:

- `logs/r5_guest_boot_probe.log`
- `results/r5_guest_boot_probe.md`

## R6 - Validar Guest Real Con Runtime

Objetivo:

- confirmar que el guest limpio ve y puede ejecutar el runtime

Trabajo:

- dentro del guest comprobar:
  - `/usr/bin/sharc_cva6_acc_runtime`
  - `/usr/share/sharcbridge_cva6/base_config.json`
  - ejecucion de un snapshot simple

Test / Gate:

- clasificacion `runtime_present_and_executable`

Artefactos:

- `logs/r6_guest_runtime_probe.log`
- `results/r6_guest_runtime_probe.json`
- `results/r6_guest_runtime_probe.md`

## R7 - Validar Backend Antes De Figure 5

Objetivo:

- probar el launcher y el backend con el SDK limpio sin tocar aun el flujo
  principal del repo

Trabajo:

- ejecutar snapshot smoke apuntando `CVA6_SDK_DIR=/tmp/cva6-sdk-clean`
- probar:
  - `spike`
  - `spike_persistent`

Test / Gate:

- un snapshot devuelve `SUCCESS`
- `spike_persistent` no se cae al primer request

Artefactos:

- `logs/r7_backend_smoke.log`
- `results/r7_backend_smoke.md`

## R8 - Figure 5 Smoke Con SDK Limpio

Objetivo:

- validar el flujo real antes del cutover

Trabajo:

- ejecutar `run_cva6_figure5_tcp.sh` usando temporalmente el SDK limpio
- no reemplazar aun el SDK del repo

Test / Gate:

- el run genera al menos:
  - `latest/plots.png`
  - `latest/experiment_list_data_incremental.json`

Artefactos:

- `logs/r8_figure5_smoke.log`
- `results/r8_figure5_smoke.md`

## R9 - Cutover Controlado

Objetivo:

- solo promover el SDK limpio si ya paso todas las gates anteriores

Trabajo:

- sustituir `CVA6_LINUX/cva6-sdk` o copiar solo los artefactos necesarios
- volver a ejecutar una prueba corta en el repo principal

Test / Gate:

- el repo principal sigue pasando el smoke final despues del cambio

Artefactos:

- `results/r9_cutover_report.md`

## R10 - Rollback

Objetivo:

- poder deshacer el cutover en minutos si el SDK limpio falla al integrarse

Trabajo:

- restaurar el backup de `R0`
- dejar hashes finales documentados

Test / Gate:

- los hashes restaurados coinciden con `R0`

Artefactos:

- `results/r10_rollback_report.md`

## Criterio De Decision

- Si `R5` falla: parar y no tocar el repo principal.
- Si `R6` falla: el SDK limpio no sirve para SHARC y no se hace cutover.
- Si `R7` pasa pero `R8` falla: depurar wrapper o flujo, no reinstalar otra vez.
- Si `R8` pasa: el SDK limpio ya es candidato real a reemplazo.

## Recomendacion Practica

- Empezar por `R0` y `R1`.
- No borrar nada antes.
- No repetir `make clean` sobre `CVA6_LINUX/cva6-sdk` del repo principal.
