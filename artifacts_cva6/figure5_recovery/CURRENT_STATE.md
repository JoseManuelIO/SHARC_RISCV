# Estado Actual

Fecha: 2026-03-24

## Baseline conocido bueno

- El commit actual del repo principal es `20d185a` y su mensaje es `generacion figura 5 completa con CVA6`.
- Hay evidencia de exito previa en:
  - `artifacts_cva6/figure5_t9_run_summary.md`
  - `artifacts_cva6/spike_hw_metrics_validation.md`
- La evidencia `PASS` apunta a runs validos del `2026-03-18`.

## Bloqueos observados hoy

- El flujo vuelve a fallar en `[3/6] Running SHARC Figure 5 config`.
- Evidencias:
  - `artifacts_cva6/cache_sweep/results/t1_flow_check_2026-03-23.md`
  - `artifacts_cva6/cache_sweep/results/task3_launcher_gate.md`
  - `artifacts_cva6/cache_sweep/results/task4_figure5_e2e_gate.md`

## Hallazgo mas importante

La evidencia mas fuerte no apunta a un problema del controlador MPC sino del guest/payload.

En `/tmp/sharcbridge_cva6_runtime/persistent_session.log` aparece:

- el guest llega a `Run /init as init process`,
- se obtiene prompt `#`,
- `test -x /usr/bin/sharc_cva6_acc_runtime` devuelve `__SHARCBRIDGE_RUNTIME_MISSING__`,
- la llamada al runtime falla con `-bin/sh: /usr/bin/sharc_cva6_acc_runtime: not found`.

Eso obliga a distinguir entre dos causas:

- el runtime no esta realmente empaquetado en el guest,
- o el binario esta pero su loader/librerias no estan presentes y BusyBox responde como `not found`.

## Drift del entorno detectado

- `CVA6_LINUX/cva6-sdk` no esta limpio:
  - `configs/buildroot64_defconfig` modificado
  - `rootfs/usr/bin/hello_riscv` sin trackear
- `CVA6_LINUX/cva6` tampoco esta limpio.
- Los artefactos generados del SDK se reconstruyeron el `2026-03-23`:
  - `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
  - `CVA6_LINUX/cva6-sdk/install64/vmlinux`
  - `CVA6_LINUX/cva6-sdk/buildroot/output/target/usr/bin/sharc_cva6_acc_runtime`
- El `vmlinux` actual del SDK no coincide con el `install64/vmlinux` que quedo como evidencia del `2026-03-17`.

## Conclusiones operativas

1. El orden correcto no es tocar antes el wrapper ni SHARC.
2. Primero hay que recuperar un guest conocido bueno con runtime visible dentro de Linux.
3. Solo despues se valida `launcher -> tcp server -> wrapper -> figure5`.
4. Si no se consigue reproducir ese estado con limpieza controlada, se justifica reinstalacion completa del SDK/buildroot.

