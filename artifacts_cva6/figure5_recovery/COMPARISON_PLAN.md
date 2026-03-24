# Plan De Comparacion Con La Version Buena

Fecha: 2026-03-24

## Objetivo

Construir una comparacion reproducible entre la version buena de marzo y el estado actual roto para identificar el delta minimo que explique por que `Figure 5` ya no funciona con `CVA6/Spike`.

La idea no es parchear a ciegas, sino aislar exactamente:

- que artefacto bueno existia,
- que artefacto actual se esta arrancando de verdad,
- que diferencia concreta rompe el flujo.

## Restriccion Principal

Durante este plan no se modifica el flujo principal salvo lo estrictamente necesario para:

- medir,
- comparar,
- y validar un candidato de restauracion.

Toda evidencia nueva debe vivir en `artifacts_cva6/figure5_recovery/`.

## Baselines A Comparar

Referencia buena principal:

- `artifacts_cva6/figure5_t9_run_summary.md`
- `artifacts_cva6/spike_hw_metrics_validation.md`
- `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/`
- `/tmp/sharc_cva6_figure5/2026-03-18--13-35-10-cva6_figure5/`

Referencia rota actual:

- `artifacts_cva6/figure5_recovery/CURRENT_STATE.md`
- `artifacts_cva6/figure5_recovery/results/t0_artifact_inventory.txt`
- `artifacts_cva6/figure5_recovery/results/t2_guest_manifest.txt`
- `artifacts_cva6/figure5_recovery/results/t3_persistent_stage_report.md`

## Criterio De Exito Del Plan

El plan termina bien si deja cerradas estas tres preguntas:

1. Que payload/kernel/rootfs arrancaba en la version buena.
2. Que payload/kernel/rootfs esta arrancando hoy realmente.
3. Cual es el delta minimo que hay que restaurar para volver al guest bueno.

## Tarea C0 - Congelar Las Fuentes De Comparacion

Objetivo:

- fijar las rutas y archivos que se usaran como baseline bueno y baseline roto.

Trabajo:

- inventariar artefactos buenos de marzo todavia presentes en `/tmp` y en `artifacts_cva6`,
- inventariar artefactos actuales en:
  - `install64/`
  - `CVA6_LINUX/cva6-sdk/install64/`
  - `CVA6_LINUX/cva6-sdk/buildroot/output/images/`
- fijar hashes, tamanos y fechas.

Test:

- generar un manifiesto unico con:
  - ruta
  - `sha256`
  - `size`
  - `mtime`

PASS:

- existe una tabla de comparacion completa de las fuentes buenas y actuales.

Salida esperada:

- `results/c0_comparison_sources.md`
- `results/c0_comparison_sources.tsv`

## Tarea C1 - Comparar El Estado Git Y El Drift Del Repo

Objetivo:

- separar cambios de codigo fuente de cambios de artefactos generados.

Trabajo:

- comparar el estado actual con el commit previo relevante:
  - `7c61d44`
  - `20d185a`
- focalizar en:
  - `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
  - `SHARCBRIDGE_CVA6/cva6_image_builder.sh`
  - `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
  - `CVA6_LINUX/cva6-sdk/rootfs/`
  - `CVA6_LINUX/cva6-sdk/configs/`

Test:

- generar un diff resumido solo de rutas relevantes al flujo.

PASS:

- queda claro si el problema viene de:
  - codigo del launcher,
  - pipeline de build del payload,
  - overlay/rootfs,
  - o artefactos generados fuera de git.

Salida esperada:

- `results/c1_git_delta.md`
- `results/c1_relevant_paths.txt`

## Tarea C2 - Comparar La Cadena De Build Buena Contra La Actual

Objetivo:

- reconstruir que pipeline exacto genero el guest bueno.

Trabajo:

- leer y resumir:
  - `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/image_build.log`
  - logs equivalentes actuales si existen,
- extraer:
  - que `vmlinux` se uso,
  - que `Image` se uso,
  - que `spike_fw_payload.elf` se uso,
  - que paso copio o empaqueto runtime/config dentro del guest.

Test:

- producir una tabla "build buena vs build actual".

PASS:

- se identifica al menos una divergencia material en la cadena de build.

Salida esperada:

- `results/c2_build_chain_compare.md`
- `results/c2_build_chain_compare.tsv`

## Tarea C3 - Comparar Artefactos Binarios Reales

Objetivo:

- validar si el payload que arranca hoy corresponde o no al guest esperado.

Trabajo:

- comparar checksums y metadatos de:
  - `install64/Image`
  - `install64/vmlinux`
  - `install64/spike_fw_payload.elf`
  - `CVA6_LINUX/cva6-sdk/install64/Image`
  - `CVA6_LINUX/cva6-sdk/install64/vmlinux`
  - `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
  - `CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio`
- confirmar si el payload bootable de marzo coincide o no con el payload actual.

Test:

- tabla de `sha256` y `file(1)` de cada binario.

PASS:

- queda demostrado si el guest roto arranca:
  - el payload bueno,
  - el payload actual,
  - o una mezcla inconsistente de ambos.

Salida esperada:

- `results/c3_binary_compare.md`
- `results/c3_binary_compare.tsv`

## Tarea C4 - Comparar El Rootfs Empaquetado Contra El Guest Visible

Objetivo:

- demostrar la diferencia entre lo que `rootfs.cpio` contiene y lo que Linux ve realmente al arrancar.

Trabajo:

- usar como referencia:
  - `artifacts_cva6/t4_rootfs_manifest.txt`
  - `artifacts_cva6/figure5_recovery/results/t2_guest_manifest.txt`
- generar un probe de guest vivo que liste:
  - `/usr/bin/sharc_cva6_acc_runtime`
  - `/usr/share/sharcbridge_cva6/base_config.json`
  - `/lib/ld-linux-riscv64-lp64d.so.1`
- comparar rootfs empaquetado vs guest real.

Test:

- emitir una matriz:
  - `present_in_rootfs`
  - `present_in_live_guest`
  - `usable_in_live_guest`

PASS:

- queda localizada la capa exacta donde se pierde el runtime:
  - overlay no aplicado,
  - kernel con initramfs viejo,
  - payload equivocado,
  - o guest diferente al esperado.

Salida esperada:

- `results/c4_rootfs_vs_live_guest.md`
- `results/c4_rootfs_vs_live_guest.tsv`

## Tarea C5 - Comparar Logs Buenos Contra Logs Actuales

Objetivo:

- detectar el ultimo punto comun y la primera divergencia observable en tiempo de arranque y runtime.

Trabajo:

- comparar:
  - `tcp_server.log` bueno de marzo
  - `sharc_figure5.log` bueno de marzo
  - `persistent_session.log` actual
  - logs de `t2_boot_observer` y `t1_guest_runtime_probe`
- marcar:
  - ultimo marcador comun,
  - primer error comun,
  - primer error nuevo.

Test:

- linea temporal anotada "good vs current".

PASS:

- se puede decir en una frase donde se rompe el flujo actual.

Salida esperada:

- `results/c5_log_timeline_compare.md`

## Tarea C6 - Derivar La Hipotesis Ganadora Y El Cambio Minimo

Objetivo:

- convertir toda la comparacion en una hipotesis unica y verificable.

Trabajo:

- resumir los hallazgos de C0-C5,
- decidir una sola hipotesis primaria, por ejemplo:
  - payload de marzo con initramfs viejo,
  - build actual con rootfs correcto pero kernel no bootable,
  - mezcla de `vmlinux` bueno con `rootfs` incorrecto,
  - drift del SDK/buildroot fuera de git,
- definir el cambio minimo que se debe probar primero.

Test:

- documento de decision con:
  - hipotesis primaria
  - evidencia a favor
  - evidencia en contra
  - experimento minimo para validarla

PASS:

- queda una unica restauracion candidata priorizada, no una lista abierta de ideas.

Salida esperada:

- `results/c6_comparison_decision.md`

## Tarea C7 - Gate Antes De Tocar El Flujo Productivo

Objetivo:

- impedir cambios innecesarios en `SHARCBRIDGE_CVA6/` antes de tener evidencia suficiente.

Trabajo:

- no modificar el flujo principal hasta que C6 este en `PASS`,
- si hace falta tocar algo antes, justificarlo como:
  - instrumentacion minima
  - o prueba necesaria para validar la hipotesis.

Test:

- lista de cambios permitidos y su razon.

PASS:

- todo cambio fuera de `artifacts_cva6` queda justificado y minimizado.

Salida esperada:

- `results/c7_change_guard.md`

## Orden Recomendado

1. C0
2. C1
3. C2
4. C3
5. C4
6. C5
7. C6
8. C7

## Resultado Esperado

Al terminar este plan deberiamos saber si la solucion definitiva es una de estas:

- restaurar exactamente el payload/kernel/rootfs del baseline bueno,
- reconstruir el guest actual reproduciendo fielmente la cadena de build buena,
- o dejar un ajuste minimo y permanente en el flujo para que el guest correcto sea el que realmente arranque.

Hasta no cerrar esa comparacion, cualquier arreglo del launcher o side-load debe considerarse temporal.
