# Punto de Entrada del MPC

## Objetivo

Fijar cual es el camino minimo del controlador que hay que reproducir fuera de SHARC para hacer replay standalone en `CVA6`.

## Punto de entrada funcional

El punto de entrada del controlador ACC es:

- `ACC_Controller::calculateControl(int k, double t, const xVec &x, const wVec &w)`

Referencia:

- `sharc_original/resources/controllers/src/ACC_Controller.cpp`

## Flujo observado

### 1. Carga y preparacion en `setup(...)`

En `ACC_Controller::setup(...)` se hace:

1. Carga de parametros del sistema desde JSON
2. Carga de pesos MPC
3. Construccion del modelo linealizado
4. Carga de restricciones
5. Carga de referencias
6. Configuracion del solver a traves de `lmpc.setOptimizerParameters(...)`

## 2. Camino de calculo en `calculateControl(...)`

Secuencia observada:

1. recibe:
   - `k`
   - `t`
   - `x`
   - `w`
2. actualiza matrices de estado segun velocidad actual
3. actualiza restriccion terminal segun velocidad del vehiculo delantero
4. construye una serie de prediccion `w_series`
5. llama a:

```cpp
lmpc.setExogenousInputs(w_series);
lmpc_step_result = lmpc.optimize(state, control);
control = lmpc_step_result.cmd;
```

6. guarda metadatos del solver
7. extrae secuencia optima con:

```cpp
mpc::OptSequence optimal_sequence = lmpc.getOptimalSequence();
```

## 3. Resultado minimo que interesa reproducir

Para la fase standalone en `CVA6`, el resultado minimo util es:

- control final `control`
- estado del solver
- numero de iteraciones
- coste
- residual primal
- residual dual

## 4. Entrada minima para el replay standalone

Para un snapshot standalone hacen falta, como minimo:

- estado `x`
- perturbacion/exogena `w`
- parametros del controlador
- horizonte de prediccion
- horizonte de control

Opcional para depuracion:

- export de la formulacion QP
- secuencia optima completa

## 5. Hook util ya existente

En `ACC_Controller::setup(...)` ya existe un mecanismo de export de QP usando:

- variable de entorno `SHARC_QP_EXPORT_PATH`

Ese hook exporta:

- `P`
- `q`
- `A`
- `l`
- `u`

Esto es util para:

- congelar snapshots de formulacion
- comparar host vs `CVA6`
- depurar si la desviacion aparece en formulacion o en el solver

## 6. Decision para el replay standalone

El ejecutable standalone de referencia debe envolver este camino:

1. construir `ACC_Controller`
2. cargar JSON de configuracion
3. cargar snapshot `x/w`
4. llamar a `calculateControl(...)`
5. exportar:
   - control
   - metadatos del solver
   - opcionalmente formulacion QP

## 7. Implicacion para las siguientes tareas

Los probes deben converger hacia un runner con esta forma:

- `host_ref/mpc_snapshot_host.cpp`
- `cva6_app/mpc_snapshot_cva6.cpp`

Ambos deben ejecutar exactamente el mismo camino logico con distintas toolchains:

- host nativo
- `riscv64 Linux` para `CVA6`
