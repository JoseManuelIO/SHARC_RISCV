# T2 SDK Restore Report

Fecha: 2026-03-24

## Resultado actual

Estado: `IN_PROGRESS`

## Evidencia cerrada

1. El guest empaquetado en `rootfs.cpio` si contiene:
   - `usr/bin/sharc_cva6_acc_runtime`
   - `usr/share/sharcbridge_cva6/base_config.json`
   - `lib/ld-linux-riscv64-lp64d.so.1`
2. El manifest extraido queda en:
   - `artifacts_cva6/figure5_recovery/results/t2_guest_manifest.txt`
3. Por tanto, el problema actual no parece ser "binario ausente en rootfs.cpio".

## Experimento realizado

1. Se comparo el baseline conocido bueno de `install64/` del `2026-03-17` con los artefactos actuales de `CVA6_LINUX/cva6-sdk/install64/` del `2026-03-23`.
2. Se copio el `Image` y el `vmlinux` conocidos buenos al `install64/` del SDK.
3. Se reconstruyo `spike_fw_payload.elf` desde dentro de `CVA6_LINUX/cva6-sdk` con:
   - `CCACHE_DIR=/tmp/buildroot-ccache make spike_payload`

## Efecto del experimento

Antes del experimento:

- el boot fresco del payload actual se quedaba en `OpenSBI` y no llegaba a `Run /init as init process`.

Despues del experimento:

- el boot vuelve a Linux,
- aparece `Run /init as init process`,
- aparecen `Starting syslogd: OK`, `Starting klogd: OK`, `Running sysctl: OK`, `Starting rpcbind: OK`,
- pero el backend sigue sin completar el snapshot.

## Hallazgo sobre el launcher

Con el payload que vuelve a Linux, el problema visible pasa a ser de sincronizacion de arranque:

- el launcher inyectaba el snapshot demasiado pronto,
- se corrigio `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py` para no disparar con `Run /init as init process`,
- aun asi el `oneshot` sigue sin llegar al `END_MARKER`.

## Lectura tecnica actual

La recuperacion del `vmlinux` conocido bueno mejora el arranque, asi que la regresion no estaba solo en SHARC ni en el wrapper.

El bloqueo restante esta entre:

- el payload/estado del SDK que ahora arranca pero no llega a shell estable,
- y la sincronizacion del launcher con el momento exacto en que el guest ya acepta el comando del runtime.

## Siguiente paso recomendado

1. Ejecutar el mismo experimento sobre un SDK limpio en `/tmp` o copia limpia local, sin drift de `cva6-sdk`.
2. Volver a probar `spike_persistent`, que es el modo oficial validado en marzo.
3. Si el SDK limpio llega a prompt, consolidar ese `Image/vmlinux` como baseline operativo y seguir con T3/T4/T5.

