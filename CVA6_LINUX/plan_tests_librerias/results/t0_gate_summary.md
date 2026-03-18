# Tarea 0 Gate

## Verificaciones

- baremetal toolchain: PASS
- linux toolchain: PASS
- spike: PASS
- smoke app Linux en Spike: PASS

## Evidencia

- app: `CVA6_LINUX/plan_tests_librerias/cva6_app/hello_linux_smoke.c`
- binario: `CVA6_LINUX/plan_tests_librerias/results/hello_linux_smoke`
- payload: `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
- log: `CVA6_LINUX/plan_tests_librerias/results/t0_spike_smoke.log`

## Resultado

La Tarea 0 queda validada. El entorno `CVA6 + Linux + Spike` compila y ejecuta un binario propio RISC-V Linux de forma no interactiva.
