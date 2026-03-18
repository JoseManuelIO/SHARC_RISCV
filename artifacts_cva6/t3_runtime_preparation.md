# T3 Runtime Preparation

## Estado

`IN_PROGRESS`

## Piezas principales ya creadas

- `SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp`
- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`

## Objetivo de estas piezas

1. Compilar el controlador ACC original con:
   - `libmpc`
   - `Eigen`
   - `OSQP`
2. Construir la imagen CVA6 con una configuracion determinista de `OSQP`.
3. Dejar el binario instalado dentro del rootfs para que el launcher posterior pueda ejecutarlo.

## Nota tecnica

La build incorpora desde el principio:

- `adaptive_rho = true`
- `adaptive_rho_interval = 25`
- `profiling = on`

porque esa fue la configuracion que cerro la paridad host/CVA6 en la validacion previa.
