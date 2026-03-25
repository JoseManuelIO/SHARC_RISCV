# C3 Injection Runtime Gate

Fecha: 2026-03-25

- estado: `PASS`

## Cambio aplicado

- se reintrodujo `SPIKE_CACHE_ARGS` en [cva6_runtime_launcher.py](/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_runtime_launcher.py)
- la construcción del comando host de `Spike` ya no está fija a `spike payload`, sino a:
  - `spike`
  - `SPIKE_CACHE_ARGS` parseado con `shlex.split(...)`
  - `payload`
- `health` y `runtime metadata` exponen `spike_cache_args`

## Test / Gate Ejecutados

1. Sintaxis del launcher

- comando:
  - `python3 -m py_compile SHARCBRIDGE_CVA6/cva6_runtime_launcher.py SHARCBRIDGE_CVA6/cva6_tcp_server.py`
- resultado:
  - `PASS`

2. Compatibilidad backward-compatible sin caché

- `health` sin `SPIKE_CACHE_ARGS` devuelve:
  - `runtime_mode=spike_persistent`
  - `sdk_dir=/tmp/cva6-sdk-clean-20260324-r1-2`
  - `spike_cache_args=""`
- evidencia runtime:
  - [c3-baseline-regression.md](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/c3-baseline-regression.md)
- resultado:
  - `PASS`

3. Propagación real de args al backend

- se levantó un backend temporal en `127.0.0.1:5023`
- `health` devolvió:
  - `spike_cache_args="--ic=4:4:64 --dc=4:4:64 --l2=128:4:64"`
- resultado:
  - `PASS`

4. Integridad del baseline protegido

- hashes revalidados después del cambio:
  - `spike_fw_payload.elf = 75f8d46a5e9ab5c840498543406196a36647a1e236285df7dbdb227cce328a19`
  - `vmlinux = e6ff4e686f6d0647073061302d1b73fda6c4b7f9ec9b7115fb260f05c650723a`
  - `Image = 7675861a576490a78da06c39b50ca73fc99e19b800546cb68595f2d88eb877b3`
  - `rootfs.cpio = fb19e9cc6ef1e1c55ebce3a170bf2ed4d2fb411e5672cc8e89bdf69640a1f205`
  - `spike = 99eb8993c4854acddc4161d9961661f77a442e40f0ef32837080cf45f0177c86`
- comparación con [c0_safe_baseline_manifest.json](/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/c0_safe_baseline_manifest.json):
  - sin cambios
- resultado:
  - `PASS`

## Hallazgo importante para C4

- los probes con `cachesim` ya no fallan por pérdida de integración ni por corrupción del `payload`
- el límite observado ahora es de runtime/boot:
  - con configuraciones de caché activas, el arranque del guest puede ralentizarse mucho
  - el caso con `--log-cache-miss` además inunda la salida y no sirve como primer gate runtime
- por tanto:
  - `C3` queda cerrado como gate de integración
  - `C4` debe ajustar el gate runtime con timeouts y selección de caso conservadora antes del sweep completo

## Conclusión

- `SPIKE_CACHE_ARGS` vuelve a estar integrado de forma mínima
- el baseline principal sigue intacto
- no se ha tocado ni regenerado el `payload`
- el siguiente trabajo ya no es de integración, sino de validación runtime segura
