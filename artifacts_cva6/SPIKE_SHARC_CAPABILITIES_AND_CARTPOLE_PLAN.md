# Spike + SHARC: Capacidades Actuales y Plan para CartPole

## Objetivo

Este documento resume:

1. qué se puede sacar hoy del flujo `SHARC -> wrapper -> TCP -> Spike/CVA6`,
2. qué límites tiene `Spike` como referencia temporal,
3. cómo empezar de forma ordenada la implementación del ejemplo `cartpole` sobre la infraestructura actual.

El foco es práctico: dejar claro qué ya está probado, qué es reutilizable y cuál es el refactor mínimo para desbloquear un segundo caso de uso además de `ACC`.

## Resumen Ejecutivo

Hoy el flujo `SHARC + CVA6 + Spike` ya permite:

- ejecutar el controlador original de SHARC en `CVA6 Linux` dentro de `Spike`,
- mantener a SHARC sin cambios internos usando el patrón `wrapper -> TCP -> backend`,
- recoger métricas reales del runtime exportadas por el controlador en RISC-V,
- correr campañas comparativas de caché con `Spike cachesim`,
- publicar bundles y figuras tipo `Figure 5`,
- extraer eventos de `cache miss` con `--log-cache-miss`.

La limitación clave es que `Spike` no es un simulador microarquitectónico ciclo a ciclo. Por tanto:

- sí sirve para validación funcional,
- sí sirve para comparación relativa y campañas de sensibilidad,
- no debe venderse aún como referencia temporal fiel del hardware.

Además, el stack actual de `SHARCBRIDGE_CVA6` está todavía acoplado al caso `ACC`, aunque el stack original de SHARC ya contiene un ejemplo `cartpole` reutilizable.

## Arquitectura Actual

La arquitectura base ya cerrada es:

`SHARC -> wrapper compatible -> TCP server -> launcher CVA6 -> runtime MPC en Spike/CVA6`

Referencias:

- `SHARCBRIDGE_CVA6/README.md`
- `SHARCBRIDGE_CVA6/ARCHITECTURE.md`
- `artifacts_cva6/t0_architecture_reuse.md`

Las responsabilidades actuales están separadas así:

- `cva6_controller_wrapper.py`: habla con SHARC, lee pipes/ficheros y traduce a TCP.
- `cva6_tcp_server.py`: valida requests, ejecuta snapshots y devuelve JSON.
- `cva6_runtime_launcher.py`: arranca `Spike`, prepara el guest, ejecuta el runtime y recoge salida.
- `cva6_image_builder.sh`: compila el runtime RISC-V y actualiza el target filesystem de `cva6-sdk`.
- `run_cva6_figure5_tcp.sh`: orquesta el flujo end-to-end.

## Qué Ya Está Demostrado con Spike + SHARC

### 1. Integración funcional end-to-end

El flujo `SHARC + CVA6` ya está oficializado como funcional:

- wrapper compatible con SHARC,
- transporte TCP estable,
- backend `Spike/CVA6`,
- ejecución del stack original `libmpc + Eigen + OSQP`.

Referencias:

- `artifacts_cva6/t8_final_decision.md`
- `artifacts_cva6/t7_parity_report.md`

### 2. Paridad host vs CVA6

Ya existe evidencia de paridad de comportamiento entre host y CVA6 para snapshots validados del caso `ACC`:

- diferencias máximas muy pequeñas en `u`,
- `iterations` alineado,
- `cost` alineado,
- mismos casos límite reproducibles fuera de SHARC.

Esto es importante porque demuestra que el backend RISC-V no está rompiendo la formulación.

Referencia:

- `artifacts_cva6/t7_parity_report.md`

### 3. Ejecución persistente en Spike

El launcher actual soporta al menos dos modos:

- `spike`
- `spike_persistent`

El modo persistente evita reboot completo en cada snapshot y es la base de las campañas actuales.

Referencia principal:

- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`

### 4. Métricas del runtime que ya se pueden extraer

Hoy el runtime actual exporta directamente desde RISC-V:

- `cycles`
- `instret`
- `cpi`
- `ipc`
- `iterations`
- `cost`
- `constraint_error`
- `dual_residual`
- `solver_status`
- `is_feasible`
- `t_delay`

Origen técnico:

- `cva6_acc_runtime.cpp` mide `rdcycle` y `rdinstret`.
- `cva6_controller_wrapper.py` reemite estas métricas hacia SHARC.
- `collect_spike_hw_metrics.py` agrega estas métricas a nivel de run.

Referencias:

- `SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp`
- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`
- `artifacts_cva6/cva6_research/archived_from_sharcbridge_cva6/collect_spike_hw_metrics.py`
- `artifacts_cva6/spike_hw_metrics_validation.md`

### 5. Sweep de cachés con Spike cachesim

Ya existe una infraestructura reproducible para barrer configuraciones de caché de Spike usando:

- `--ic=<sets>:<ways>:<block>`
- `--dc=<sets>:<ways>:<block>`
- `--l2=<sets>:<ways>:<block>`

La inyección de la configuración se hace mediante:

- variable de entorno `SPIKE_CACHE_ARGS`,
- leída por `cva6_runtime_launcher.py`,
- establecida caso a caso por `run_spike_cache_sweep.sh`.

Casos ya definidos:

- `baseline` sin `cachesim`,
- `cache_1mb`,
- `cache_262kb`,
- `cache_32kb`.

Referencias:

- `artifacts_cva6/cache_sweep/configs/cache_sweep_matrix.json`
- `artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh`
- `artifacts_cva6/cache_sweep/results/c5_final_cache_matrix.md`
- `artifacts_cva6/cache_sweep/results/c8_full_sweep_report.md`

### 6. Comparación relativa de rendimiento entre configuraciones de caché

La campaña de cachés muestra hoy:

- `delay_mean_ms` sensible a la configuración de caché,
- `cycles_mean` e `instret_mean` casi planos,
- `feasible_ratio` estable.

Interpretación práctica:

- útil para comparación relativa,
- útil para construir campañas de sensibilidad,
- insuficiente por sí sola como modelo temporal microarquitectónico fiel.

Referencias:

- `artifacts_cva6/cache_sweep/results/spike_cache_sweep_report_full.md`
- `artifacts_cva6/cache_sweep/results/c8_full_sweep_report.md`

### 7. Extracción de cache misses

El binario local de Spike soporta `--log-cache-miss`.

Ya existe parser para extraer:

- `I$ read miss`
- `D$ read miss`
- `D$ write miss`
- opcionalmente `L2$ ... miss` si aparecen en el log

Métricas derivadas:

- `miss_count`
- `unique_addr_count`
- `block_bytes`
- `estimated_linefill_bytes`

Referencias:

- `artifacts_cva6/cache_sweep/scripts/parse_spike_cache_miss_log.py`
- `artifacts_cva6/cache_sweep/results/c7_cache_miss_probe.md`
- `artifacts_cva6/cache_sweep/results/c7_cache_parser_gate.md`

### 8. Publicación de bundles y figuras

El flujo actual ya puede generar y publicar:

- bundle `experiment_list_data_incremental.json`,
- tablas agregadas JSON/CSV/MD,
- figura comparativa tipo `Figure 5`,
- paquete `latest/` para consumo más sencillo.

Referencias:

- `artifacts_cva6/cache_sweep/scripts/build_spike_cache_sweep_report.py`
- `artifacts_cva6/cache_sweep/scripts/publish_cache_latest.py`
- `artifacts_cva6/cache_sweep/results/cl5_latest_publish.md`

## Qué No Se Puede Afirmar Aún con Spike

Aunque el flujo ya es muy útil, hay límites importantes:

### 1. No tenemos una referencia temporal microarquitectónica fiel

Con `Spike` actual no podemos afirmar que:

- los `cycles` reflejen penalties reales de memoria/caché,
- la latencia temporal observada sea equivalente a hardware real,
- el efecto de caché sea una predicción cuantitativa fiel de CVA6 físico o RTL.

Lo que sí tenemos es:

- una ejecución funcional correcta,
- contadores arquitectónicos básicos,
- sensibilidad del flujo host-side a `cachesim`,
- métricas observables comparables entre configuraciones.

### 2. El efecto principal hoy aparece en `t_delay`, no en `cycles`

Esto ya se vio en la campaña de cachés:

- `delay_mean_ms` cambia claramente,
- `cycles_mean` e `instret_mean` no acompañan con el mismo contraste.

Eso sugiere que hoy `Spike cachesim` nos da una señal útil, pero todavía no una referencia temporal cerrada.

### 3. El stack SHARCBRIDGE_CVA6 está especializado a ACC

Las capas actuales asumen implícitamente:

- `x` de longitud 3,
- `w` de longitud 2,
- `u_prev` de longitud 2,
- runtime basado en `ACC_Controller`,
- builder compilado con `TNX=3`, `TNU=2`, `TNDU=2`, `TNY=1`.

Esto basta para `ACC`, pero bloquea `cartpole`.

Referencias:

- `SHARCBRIDGE_CVA6/cva6_tcp_server.py`
- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`
- `SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp`
- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`

## Qué Aporta el Ejemplo CartPole Ya Existente

El ejemplo `cartpole` ya existe en SHARC original:

- `sharc_original/examples/cartpole/base_config.json`
- `sharc_original/examples/cartpole/controller_delegator.py`
- `sharc_original/resources/dynamics/dynamics.py`
- `sharc_original/resources/controllers/src/NLMPCController.cpp`

Características importantes del caso:

- `state_dimension = 4`
- `input_dimension = 1`
- `exogenous_input_dimension = 1`
- `output_dimension = 0`
- `controller_type = "NLMPCController"`

Esto es muy valioso porque significa que:

- no hace falta inventar `cartpole` desde cero,
- ya existe dinámica,
- ya existe controlador,
- ya existe configuración base,
- el propio stack original sabe construir ese controlador con macros parametrizadas.

## Gap Técnico entre ACC y CartPole

Para pasar de `ACC` a `cartpole` hay cuatro gaps reales:

### 1. Contrato de dimensiones en transporte

Hoy el servidor TCP valida longitudes fijas:

- `x` de 3
- `w` de 2
- `u_prev` de 2

Para `cartpole` deberían ser:

- `x` de 4
- `w` de 1
- `u_prev` de 1

### 2. Runtime acoplado a ACC

El runtime actual:

- incluye `ACC_Controller.h`,
- construye un `ACCReplayController`,
- fija el tipo de control a dos salidas.

Para `cartpole` hay que pasar a un runtime genérico o a un runtime específico de `cartpole`.

### 3. Builder acoplado a ACC

El builder actual compila con:

- `-DTNX=3`
- `-DTNU=2`
- `-DTNDU=2`
- `-DTNY=1`
- `ACC_Controller.cpp`
- `base_config.json` de `acc_example`

Para `cartpole` eso debe volverse parametrizable.

### 4. Wrapper orientado a control bidimensional

El wrapper actual normaliza `u` esperando exactamente dos componentes.

Eso hay que hacerlo dependiente de la configuración o del response.

## Recomendación de Implementación para Empezar CartPole

La recomendación es no intentar portar `cartpole` “de golpe” al flujo completo. Lo más seguro es hacerlo por hitos.

### Fase 0. Congelar el baseline ACC

Antes de tocar nada:

- mantener `ACC` como camino oficial,
- no romper `run_cva6_figure5_tcp.sh`,
- hacer que los cambios nuevos sean opt-in.

Objetivo:

- preservar la evidencia ya cerrada para el equipo.

### Fase 1. Introducir una vía genérica de dimensiones

Primer refactor mínimo:

- permitir que `cva6_tcp_server.py` valide dimensiones configurables,
- permitir que `cva6_controller_wrapper.py` no asuma `u` de longitud 2,
- transportar `x`, `w` y `u_prev` sin hardcode de tamaño.

Cómo hacerlo:

- añadir variables de entorno o un JSON de contrato:
  - `CVA6_STATE_DIM`
  - `CVA6_INPUT_DIM`
  - `CVA6_EXOGENOUS_DIM`
- usar esas dimensiones para validar request/response.

Resultado esperado:

- el transporte deja de ser “ACC-only”.

### Fase 2. Separar runtime genérico de runtime ACC

En vez de seguir con `cva6_acc_runtime.cpp` monolítico, crear una abstracción sencilla:

- `cva6_runtime_main.cpp` o `cva6_generic_runtime.cpp`
- carga `config.json`
- lee `controller_type`
- instancia el controlador adecuado usando el registro ya existente (`Controller::createController`)

Ventaja:

- el stack original ya tiene infraestructura para registrar controladores.
- esto evitaría duplicar runtimes por cada ejemplo.

Si eso resulta demasiado grande para una primera iteración, alternativa segura:

- crear un `cva6_cartpole_runtime.cpp` específico,
- sin tocar todavía el runtime ACC.

### Fase 3. Parametrizar el builder

`cva6_image_builder.sh` debería aceptar un “perfil de ejemplo”, por ejemplo:

- `CVA6_EXAMPLE=acc`
- `CVA6_EXAMPLE=cartpole`

Y a partir de ahí seleccionar:

- fuente del controlador,
- dimensiones `TNX/TNU/TNDU/TNY`,
- horizontes,
- config base a copiar al target,
- nombre del binario resultante.

Para `cartpole`, los primeros valores deberían salir de:

- `sharc_original/examples/cartpole/base_config.json`

### Fase 4. Hacer un smoke test standalone de cartpole en CVA6

Antes de meter a SHARC:

1. compilar el runtime/cartpole para RISC-V,
2. copiar binario y config al guest,
3. lanzar un snapshot manual,
4. verificar salida JSON correcta.

Éxito mínimo:

- el runtime abre config,
- ejecuta el controlador,
- devuelve `u`, `iterations`, `cost`, `solver_status`,
- no hay errores de dimensiones.

### Fase 5. Añadir un smoke test TCP de cartpole

Una vez el runtime standalone funcione:

- reutilizar el `TCP server`,
- enviar un `run_snapshot` con dimensiones de cartpole,
- validar respuesta completa.

Esto cierra:

- transporte,
- launcher,
- runtime,
- guest staging,
- JSON de retorno.

### Fase 6. Integrar cartpole con SHARC

Solo después del smoke standalone + TCP:

- crear configuración de wrapper/runner para `cartpole`,
- apuntar al ejemplo original de SHARC,
- correr un caso corto,
- validar que SHARC consume bien `u` de dimensión 1.

## Propuesta de Orden de Trabajo

Orden recomendado:

1. generalizar transporte y wrapper a dimensiones variables,
2. hacer runtime específico o genérico para `cartpole`,
3. parametrizar builder,
4. smoke standalone en Spike,
5. smoke TCP,
6. integración con SHARC,
7. métricas y cachés sobre cartpole.

Este orden minimiza riesgo y evita depurar demasiadas capas a la vez.

## Qué Haría Yo Primero en Código

Si el objetivo es empezar ya, el primer lote de cambios debería ser:

### Lote A. Desacoplar tamaños fijos en Python

Archivos:

- `SHARCBRIDGE_CVA6/cva6_tcp_server.py`
- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`

Cambio:

- sustituir validaciones rígidas por dimensiones configurables.

### Lote B. Crear runtime mínimo de cartpole

Archivo nuevo sugerido:

- `SHARCBRIDGE_CVA6/cva6_cartpole_runtime.cpp`

Cambio:

- usar `NLMPCController`,
- dimensiones `4/1/1/0`,
- leer snapshot `x[4]`, `w[1]`, `u_prev[1]`,
- devolver `u[1]` más metadata.

### Lote C. Añadir modo de build de cartpole

Archivo:

- `SHARCBRIDGE_CVA6/cva6_image_builder.sh`

Cambio:

- añadir selección por ejemplo,
- compilar binario correcto,
- copiar `base_config.json` correcto al target.

Con solo esos tres lotes ya podríamos aspirar a un primer smoke test real de `cartpole` sobre Spike.

## Qué Se Podrá Sacar de Spike con CartPole una Vez Porteado

Si `cartpole` entra al flujo actual, se podrá reutilizar inmediatamente:

- ejecución funcional en `CVA6 Linux`,
- `cycles`,
- `instret`,
- `cpi`,
- `ipc`,
- `iterations`,
- `cost`,
- `constraint_error`,
- `dual_residual`,
- `solver_status`,
- `t_delay`,
- campañas de caché por `SPIKE_CACHE_ARGS`,
- extracción de `cache miss`,
- bundles y tablas agregadas por run.

Eso permitiría comparar dos ejemplos sobre la misma infraestructura:

- `ACC`
- `cartpole`

Y responder si el patrón observado con cachés es:

- específico de `ACC`,
- o reproducible también en un controlador distinto.

## Riesgos y Cómo Reducirlos

### Riesgo 1. Intentar generalizar todo a la vez

Mitigación:

- mantener `ACC` como camino oficial,
- introducir `cartpole` detrás de una opción explícita.

### Riesgo 2. Acoplar el runtime genérico demasiado pronto

Mitigación:

- empezar con `cva6_cartpole_runtime.cpp` separado,
- unificar después si sale estable.

### Riesgo 3. Depurar SHARC antes del smoke standalone

Mitigación:

- primero runtime local,
- luego TCP,
- luego SHARC.

### Riesgo 4. Mezclar validación funcional con validación temporal

Mitigación:

- cerrar primero correctitud funcional,
- después métricas,
- después campañas de caché.

## Recomendación Final

La infraestructura actual ya justifica presentar al equipo de SHARC que:

- el flujo Spike/CVA6 está maduro para campañas reproducibles,
- ya existe evidencia funcional y de paridad para `ACC`,
- las campañas de caché son válidas como comparación relativa,
- el siguiente paso de mayor valor técnico es portar un segundo ejemplo, y `cartpole` es el candidato natural.

La mejor estrategia para empezar `cartpole` no es rehacer todo, sino:

1. quitar hardcodes de dimensiones en Python,
2. compilar un runtime/cartpole mínimo en RISC-V,
3. pasar un smoke test de snapshot,
4. recién entonces conectarlo a SHARC.

Eso nos daría una segunda demostración fuerte de reutilización real del puente `SHARC -> Spike/CVA6`.
