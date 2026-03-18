# Arquitectura SHARC-CVA6

## Objetivo

Conectar SHARC con un backend `CVA6 Linux` sin modificar SHARC y reutilizando el patron ya validado en `SHARCBRIDGE`.

## Regla principal

SHARC no conoce ni `CVA6`, ni `Spike`, ni la toolchain.  
SHARC solo interactua con un **wrapper** con la misma interfaz que ya esperaba en el flujo anterior.

## Flujo end-to-end

1. SHARC genera por iteracion:
   - `k`
   - `t`
   - `x`
   - `w`
   - estado del proceso
2. El wrapper CVA6 lee esas entradas desde el directorio de simulacion.
3. El wrapper serializa una peticion TCP.
4. El servidor TCP CVA6 recibe la peticion.
5. El servidor invoca el launcher/runtime CVA6.
6. El runtime CVA6 ejecuta el controlador MPC original usando:
   - `libmpc`
   - `Eigen`
   - `OSQP`
7. El runtime devuelve:
   - `u`
   - `status`
   - `iterations`
   - `cost`
   - metadata adicional
8. El servidor responde al wrapper.
9. El wrapper escribe la salida en el formato esperado por SHARC.
10. SHARC continua su lazo sin cambios internos.

## Capas

### 1. SHARC

No se modifica.

Responsabilidades:

- generar dinamicas
- pedir control
- consumir `u` y metadata

### 2. Wrapper CVA6

Responsabilidades:

- hablar el protocolo local de SHARC
- traducir a peticion TCP
- traducir la respuesta TCP al formato SHARC

No debe contener logica pesada del MPC.

### 3. Servidor TCP CVA6

Responsabilidades:

- mantener el contrato de transporte
- validar peticiones
- invocar el backend CVA6
- devolver respuesta estructurada

### 4. Launcher/runtime CVA6

Responsabilidades:

- preparar input para el entorno Linux del target
- lanzar la imagen/payload
- recoger salida del controlador
- devolver JSON al servidor

### 5. Controlador MPC en CVA6

Responsabilidades:

- usar el stack original del MPC de SHARC
- formular con `libmpc`
- usar `Eigen`
- resolver con `OSQP`

## Contrato minimo de entrada

El wrapper debe recibir desde SHARC:

- `k`
- `t`
- `x[3]`
- `w[2]`
- opcionalmente `u_prev`

## Contrato minimo TCP

Peticion esperada del wrapper al backend:

```json
{
  "type": "run_snapshot",
  "request_id": "str|int",
  "k": 0,
  "t": 0.0,
  "x": [0.0, 60.0, 15.0],
  "w": [11.0, 1.0],
  "u_prev": [0.0, 0.0]
}
```

Respuesta minima del backend:

```json
{
  "status": "SUCCESS",
  "request_id": "str|int",
  "k": 0,
  "u": [2.4, 0.0],
  "iterations": 50,
  "cost": -6749320.93,
  "metadata": {}
}
```

## Archivos principales previstos

- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`
- `SHARCBRIDGE_CVA6/cva6_tcp_server.py`
- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`
- `SHARCBRIDGE_CVA6/run_cva6_config.sh`
- `SHARCBRIDGE_CVA6/run_cva6_e2e.sh`

## Decisiones cerradas

1. No se toca `sharc_original`.
2. Se reutiliza el patron `wrapper -> TCP -> backend`.
3. El backend objetivo es `CVA6 Linux`.
4. El MPC debe usar las librerias del stack original.
5. La configuracion de `OSQP` debe ser determinista para evitar divergencias de iteraciones entre host y CVA6.
