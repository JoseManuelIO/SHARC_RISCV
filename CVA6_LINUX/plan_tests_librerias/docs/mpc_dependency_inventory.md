# Inventario de Dependencias MPC

## Objetivo

Fijar el stack real que usa el MPC del arbol `sharc_original` para saber que hay que reproducir en `CVA6 + Linux + Spike`.

## Hallazgos

### 1. Libreria de formulacion MPC

El controlador lineal usa la libreria `libmpc` con la clase `LMPC`.

Evidencia:

- `sharc_original/resources/controllers/include/ACC_Controller.h`
- `sharc_original/resources/controllers/src/ACC_Controller.cpp`
- `sharc_original/resources/controllers/src/LMPCController.cpp`
- `sharc_original/libmpc/include/mpc/LMPC.hpp`

Uso directo observado:

- `ACC_Controller` declara:
  - `LMPC<Tnx, Tnu, Tndu, Tny, prediction_horizon, control_horizon> lmpc;`
- `ACC_Controller::calculateControl(...)` llama:
  - `lmpc.optimize(state, control);`

### 2. Eigen

`Eigen` se usa como base de tipos y algebra lineal.

Evidencia:

- `sharc_original/resources/controllers/include/controller.h`
- `sharc_original/resources/controllers/include/ACC_Controller.h`
- `sharc_original/resources/controllers/src/main_controller.cpp`
- `sharc_original/libmpc/CMakeLists.txt`

Tipos observados:

- `Eigen::Matrix<double, ...>`
- `Eigen::VectorXd`
- `Eigen::MatrixXd`

Observacion:

- `libmpc` declara `find_package(Eigen3 REQUIRED)` en:
  - `sharc_original/libmpc/CMakeLists.txt`

### 3. OSQP

`OSQP` es el solver QP del camino LMPC.

Evidencia:

- `sharc_original/libmpc/CMakeLists.txt`
- `sharc_original/examples/acc_example/CMakeLists.txt`
- `sharc_original/resources/controllers/src/ACC_Controller.cpp`
- `sharc_original/resources/controllers/src/LMPCController.cpp`

Uso observado:

- se cargan parametros del solver desde `osqp_options`
- `libmpc` hace `find_package(osqp REQUIRED)`

Parametros observados:

- `eps_rel`
- `eps_abs`
- `eps_prim_inf`
- `eps_dual_inf`
- `time_limit`
- `maximum_iteration`
- `verbose`
- `enable_warm_start`
- `polish`

### 4. NLopt

`NLopt` aparece como dependencia de `libmpc`, pero asociada al camino no lineal.

Evidencia:

- `sharc_original/libmpc/CMakeLists.txt`

Interpretacion:

- para el objetivo actual de ACC lineal, el riesgo principal es `LMPC + Eigen + OSQP`
- `NLopt` queda inventariada, pero no es la primera dependencia critica del camino ACC lineal

### 5. JSON y utilidades auxiliares

El controlador usa `nlohmann::json` y utilidades del propio repositorio para cargar parametros.

Evidencia:

- `sharc_original/resources/controllers/src/ACC_Controller.cpp`
- `sharc_original/resources/include/nlohmann/json.hpp`
- `sharc_original/resources/include/sharc/utils.hpp`

## Stack minimo a reproducir

Para el camino ACC lineal, el stack minimo real es:

1. `Eigen`
2. `OSQP`
3. `libmpc` con `LMPC`
4. `nlohmann::json`
5. codigo del controlador ACC (`ACC_Controller`)

## Dependencias no prioritarias para esta fase

No se consideran bloqueantes para la fase inicial de probes:

- `DynamoRIO`
- `ScarAB`
- `Snappy`
- `lz4`
- `zlib`

Motivo:

- aparecen en el `CMakeLists.txt` del ejemplo de `acc_example`
- pero no forman parte del nucleo matematico del MPC que queremos ejecutar en `CVA6`

## Decision para la siguiente tarea

Orden de validacion de librerias:

1. `Eigen`
2. `OSQP`
3. `libmpc/LMPC`

Ese orden minimiza tiempo de depuracion porque:

- `Eigen` es header-only y define si el entorno C++/double esta sano
- `OSQP` valida solver y linking C/C++
- `libmpc` valida la capa superior de formulacion sobre las dos anteriores
