# SHARCBRIDGE - Integración SHARC + GVSoC

**Fecha de creación**: 13 de febrero de 2026  
**Estado**: En implementación (85% completado)  
**Objetivo**: Ejecutar controlador MPC en RISC-V (via GVSoC) desde SHARC en Docker

---

## 📋 Índice

1. [Visión General](#visión-general)
2. [Arquitectura](#arquitectura)
3. [Componentes](#componentes)
4. [Instalación](#instalación)
5. [Uso](#uso)
6. [Verificación](#verificación)
7. [Problemas Conocidos](#problemas-conocidos)
8. [Bitácora de Desarrollo](#bitácora-de-desarrollo)

---

## Visión General

SHARCBRIDGE conecta SHARC (Simulation framework for Hardware-Accelerated Robot Controllers) con GVSoC (GAP Virtual SOC) para ejecutar controladores MPC (Model Predictive Control) en simuladores RISC-V.

### Flujo de Datos

```
┌──────────────────┐
│  SHARC (Docker)  │  
│  - Simula planta │
│  - Genera estado │
└────────┬─────────┘
         │ Pipes (FIFOs)
         ↓
┌────────────────────────┐
│  Wrapper Python        │  (Dentro del contenedor)
│  - Lee pipes           │
│  - Construye JSON      │
└────────┬───────────────┘
         │ TCP (172.17.0.1:5000)
         ↓
┌────────────────────────┐
│  TCP Server (Host)     │
│  - Parchea ELF         │
│  - Lanza GVSoC         │
└────────┬───────────────┘
         │
         ↓
┌────────────────────────┐
│  GVSoC + RISC-V        │
│  - Ejecuta MPC         │
│  - Cuenta ciclos       │
└────────┬───────────────┘
         │
         ↓ JSON response
┌────────────────────────┐
│  Resultados            │
│  u, cost, cycles       │
└────────────────────────┘
```

### ¿Por qué este diseño?

1. **SHARC en Docker**: Aislamiento de dependencias (PIN tool, SCARAB, LLVM)
2. **TCP Bridge**: SCARAB no soporta syscalls de red → wrapper Python nativo
3. **GVSoC en Host**: Acceso directo a herramientas RISC-V y PULP SDK
4. **Parche SHARC**: Intercepta ejecución para lanzar wrapper nativamente (bypass SCARAB)

---

## Arquitectura

### Estructura de Archivos

```
SHARCBRIDGE/
├── README.md                    # Este archivo
├── scripts/
│   └── gvsoc_tcp_server.py      # Servidor TCP (host)
├── mpc/
│   ├── Makefile                 # Build del controlador RISC-V
│   ├── mpc_acc_controller.c     # Controlador MPC en C
│   ├── qp_solver.c/h            # Solver QP custom
│   ├── start.S                  # Startup assembly
│   ├── riscv.ld                 # Linker script
│   └── build/                   # Binarios generados
└── docker/
    ├── Dockerfile.gvsoc         # Imagen Docker
    └── patch_sharc_for_gvsoc.py # Parche para SHARC

sharc_original/examples/acc_example/
├── gvsoc_controller_wrapper_v2.py  # Wrapper pipes↔TCP
├── controller_delegator.py         # Selector de ejecutable
├── base_config_gvsoc.json          # Config base
└── gvsoc_config.json               # Config experimento
```

---

## Componentes

### 1. TCP Server (`scripts/gvsoc_tcp_server.py`)

**Función**: Servidor TCP que ejecuta GVSoC y devuelve resultados MPC.

**Funciones principales**:
- `validate_environment()`: Verifica paths (ELF, GVSoC, PULP SDK)
- `patch_elf_with_params()`: Inyecta parámetros runtime en ELF usando objcopy
- `run_gvsoc_mpc()`: Ejecuta GVSoC con timeout, parsea stdout
- `handle_client()`: Maneja conexión TCP, procesa requests JSON

**Protocolo**:
```json
Request:  {"type": "compute_mpc", "k": 0, "t": 0.0, "x": [0, 60, 15], "w": [11, 1]}
Response: {"k": 0, "u": [0.0, 198.017], "cost": 1234.5, "status": "OPTIMAL", 
           "iterations": 120, "cycles": 114326238, "t_delay": 1.914}
```

**Paths importantes**:
```python
MPC_ELF = ~/Repositorios/SHARC_RISCV/riscv_bridge/applications/mpc_acc/build/mpc_acc_controller.elf
GVSOC_BINARY = ~/Repositorios/SHARC_RISCV/PULP/gvsoc/install/bin/gvsoc
PULP_SDK_SOURCEME = ~/Repositorios/SHARC_RISCV/PULP/pulp-sdk/configs/pulp-open.sh
```

**Inicio**:
```bash
cd SHARCBRIDGE/scripts
python3 gvsoc_tcp_server.py
```

---

### 2. Wrapper Python (`gvsoc_controller_wrapper_v2.py`)

**Función**: Puente entre pipes de SHARC y TCP server.

**Ubicación**: `sharc_original/examples/acc_example/gvsoc_controller_wrapper_v2.py`

**Protocolo de pipes** (LEE desde SHARC):
- `k_py_to_c++`: índice temporal (int)
- `t_py_to_c++`: tiempo (float)
- `x_py_to_c++`: estado [pos, headway, vel] (CSV)
- `w_py_to_c++`: exógena [v_lead, 1.0] (CSV)

**Protocolo de pipes** (ESCRIBE a SHARC):
- `u_c++_to_py`: control [F_accel, F_brake] (CSV)
- `metadata_c++_to_py`: JSON con cost, cycles, status, etc.

**Protocolo TCP**: Construye JSON request, envía por socket a `GVSOC_HOST:GVSOC_PORT`

**Orden crítico de apertura de pipes** (evita deadlock):
1. WRITERS primero: `u_c++_to_py`, `metadata_c++_to_py`
2. READERS después: `k_py_to_c++`, `t_py_to_c++`, `x_py_to_c++`, `w_py_to_c++`, `t_delay_py_to_c++`

**Variables de entorno**:
```bash
GVSOC_HOST=172.17.0.1  # Docker bridge gateway
GVSOC_PORT=5000
```

---

### 3. Controller Delegator (`controller_delegator.py`)

**Función**: Decide qué ejecutable usar como controlador SHARC.

**Ubicación**: `sharc_original/examples/acc_example/controller_delegator.py`

**Lógica**:
```python
if use_gvsoc_controller == True:
    return "gvsoc_controller_wrapper_v2.py"  # Wrapper Python
else:
    # Compila y devuelve binario C++ nativo
    cmake(...)
    cmake_build(...)
    return "main_controller_{N}_{M}"
```

**Configuración**: Lee `use_gvsoc_controller` de `build_config` (JSON)

---

### 4. Parche SHARC (`docker/patch_sharc_for_gvsoc.py`)

**Función**: Modifica SHARC para ejecutar wrapper Python nativamente.

**Target**: `/home/dcuser/resources/sharc/__init__.py` línea ~1143

**Qué hace**:
1. Busca método `SerialSimulationExecutor.run_controller()`
2. Inserta código que detecta `use_gvsoc_controller=true`
3. Si es `.py`, lanza con `subprocess.Popen` (NO usa SCARAB)
4. Si no, comportamiento normal (ejecuta con SCARAB)

**Por qué es necesario**:
- SCARAB es un simulador de CPU que NO soporta syscalls de red reales
- El wrapper necesita sockets TCP → debe ejecutarse como proceso nativo
- Sin el parche, SCARAB bloquearía en `socket()`, `connect()`, `send()`

**Aplicación**: Se ejecuta durante `docker build`

---

### 5. Dockerfile (`docker/Dockerfile.gvsoc`)

**Base**: `sharc:latest` (imagen con SHARC preinstalado)

**Pasos**:
1. Copia `patch_sharc_for_gvsoc.py` al contenedor
2. Aplica el parche con `python3 /tmp/patch_sharc_for_gvsoc.py`
3. Hace ejecutable el wrapper v2
4. Configura variables de entorno `GVSOC_HOST`, `GVSOC_PORT`

**Build**:
```bash
cd SHARCBRIDGE/docker
docker build -f Dockerfile.gvsoc -t sharc-gvsoc:latest ../..
```

---

### 6. Controlador MPC RISC-V (`mpc/mpc_acc_controller.c`)

**Función**: Implementación del MPC en C para RISC-V.

**Ubicación**: `SHARCBRIDGE/mpc/mpc_acc_controller.c`

**Solver**: Projected Gradient Descent custom (sin dependencias externas)
- 200 iteraciones máximo
- Grid search inicial + refinamiento
- Constraints: F_accel ≥ 0, F_brake ≥ 0

**Inputs** (via `.shared_data` section):
```c
struct SharedData {
    float input_x[3];      // [pos, headway, vel]
    float input_w[2];      // [v_lead, 1.0]
    int input_k;           // timestep
    float input_t;         // tiempo (s)
    float input_u_prev[2]; // [F_accel_prev, F_brake_prev]
    // ... outputs ...
};
```

**Outputs** (escritos en misma struct):
```c
float output_u[2];     // [F_accel, F_brake]
float output_cost;     // Valor función de coste
int output_iter;       // Iteraciones ejecutadas
int output_status;     // 0=OPTIMAL, 1=MAX_ITER, -1=ERROR
```

**Ciclos**: GVSoC cuenta automáticamente con CSR `mcycle`

**Build**:
```bash
cd SHARCBRIDGE/mpc
make clean && make
# Genera: build/mpc_acc_controller.elf (~8KB)
```

---

## Instalación

### Prerequisitos

1. **Docker** instalado con `sharc:latest`
2. **PULP SDK** compilado en `~/Repositorios/SHARC_RISCV/PULP/pulp-sdk/`
3. **GVSoC** compilado en `~/Repositorios/SHARC_RISCV/PULP/gvsoc/install/`
4. **Toolchain RISC-V** en `/opt/riscv/bin/`
5. **Python 3** con venv activado

### Paso 1: Compilar MPC Controller

```bash
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/mpc
make clean
make

# Verificar output
ls -lh build/mpc_acc_controller.elf
# Debe ser ~8KB
```

### Paso 2: Build Docker Image

```bash
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/docker

# Asegurarse de que sharc:latest existe
docker images sharc:latest

# Build
docker build -f Dockerfile.gvsoc -t sharc-gvsoc:latest ../..

# Verificar
docker images sharc-gvsoc:latest
```

### Paso 3: Verificar Paths en TCP Server

Editar `SHARCBRIDGE/scripts/gvsoc_tcp_server.py` si es necesario:

```python
# Líneas 30-45 - ajustar si tus paths difieren
RISCV_BRIDGE_DIR = Path.home() / "Repositorios" / "SHARC_RISCV" / "riscv_bridge"
MPC_APP_DIR = RISCV_BRIDGE_DIR / "applications" / "mpc_acc"
MPC_ELF = MPC_APP_DIR / "build" / "mpc_acc_controller.elf"
```

---

## Uso

### Escenario 1: Test Unitario MPC (sin SHARC)

```bash
# Terminal 1: Iniciar TCP server
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/scripts
python3 gvsoc_tcp_server.py

# Terminal 2: Enviar request de prueba
echo '{"type":"compute_mpc","k":0,"t":0.0,"x":[0,60,15],"w":[11,1]}' | nc localhost 5000
```

**Output esperado**:
```json
{"k":0,"u":[0.0,198.017],"cost":1234.56,"status":"OPTIMAL","iterations":120,"cycles":114326238,"t_delay":1.914}
```

---

### Escenario 2: Closed-Loop SHARC + GVSoC

```bash
# Terminal 1: TCP server en host
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/scripts
python3 gvsoc_tcp_server.py

# Terminal 2: SHARC en Docker
docker run -it --rm --name sharc_test sharc-gvsoc:latest

# Dentro del contenedor:
cd /home/dcuser/examples/acc_example

# Ejecutar experimento (6 timesteps)
python3 -c "
import sharc
experiments = sharc.run('.', 'gvsoc_config.json', fail_fast=True)
print(f'Completed {len(experiments)} experiments')
"
```

**Configs importantes** (`gvsoc_config.json`):
```json
{
  "use_gvsoc_controller": true,
  "n_time_steps": 6,
  "system_parameters": {
    "controller_type": "GVSoC_Controller"
  }
}
```

---

## Verificación

### Checklist de Validación

| Check | Comando | Resultado Esperado |
|-------|---------|-------------------|
| MPC ELF existe | `ls -lh SHARCBRIDGE/mpc/build/mpc_acc_controller.elf` | ~8KB |
| Docker image | `docker images sharc-gvsoc:latest` | Imagen presente |
| TCP server arranca | `python3 scripts/gvsoc_tcp_server.py` | "Listening on 0.0.0.0:5000" |
| Port disponible | `netstat -tlnp \| grep 5000` | LISTEN |
| GVSoC funciona | Request test | JSON response |
| Wrapper ejecutable | `ls -l sharc_original/.../gvsoc_controller_wrapper_v2.py` | -rwxr-xr-x |

### Test Rápido

```bash
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/scripts

# Test validación
python3 -c "
from gvsoc_tcp_server import validate_environment
assert validate_environment(), 'Environment validation failed'
print('✓ Environment OK')
"
```

---

## Problemas Conocidos

### Issue #1: Pipe/Delay Integration (BLOQUEANTE)

**Síntoma**: `AssertionError: Expected value to be a float or int. Instead it was <class 'NoneType'>`

**Ubicación**: `sharc/controller_interface.py` línea 265 en `_write_t_delay()`

**Causa**: SHARC intenta escribir `t_delay` pero el valor es `None` cuando usa `computation-delay-model`

**Workaround actual**: Usar `delay_provider: "none"` (no ideal)

**Solución propuesta**:
1. Modificar wrapper para incluir `t_delay` en metadata JSON
2. Verificar que SHARC lea `t_delay` desde metadata correctamente
3. Ajustar `computation_delay_model` en `base_config_gvsoc.json`

**Estado**: ⚠️ En investigación

---

### Issue #2: Fragilidad del Parche

**Síntoma**: Parche podría fallar si SHARC upstream cambia

**Causa**: `patch_sharc_for_gvsoc.py` busca línea específica (~1141)

**Mitigación**:
- Verificar hash o versión de SHARC antes de aplicar
- Añadir check de idempotencia (no aplicar dos veces)
- Hacer backup del archivo original

**Propuesta futura**: Contribuir "external controller mode" a SHARC upstream

---

## Bitácora de Desarrollo

### 13 de febrero de 2026 - Reorganización y Cleanup

**Creado**:
- ✅ Carpeta `SHARCBRIDGE/` con estructura limpia
- ✅ Este README.md consolidando toda la documentación
- ✅ Subdirectorios: `scripts/`, `mpc/`, `docker/`

**Movido** (pendiente ejecución manual):
- TCP server → `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`
- MPC sources → `SHARCBRIDGE/mpc/`
- Docker files → `SHARCBRIDGE/docker/`

**Eliminado** (pendiente):
- Archivos obsoletos en raíz del repo
- Scripts pre-TCP en `riscv_bridge/scripts/`
- Tests antiguos en `sharc_original/examples/acc_example/`
- Artefactos de build (logs, bins temporales)

**Pendiente**:
- [ ] Resolver issue pipe/delay
- [ ] Test closed-loop 30 timesteps
- [ ] Actualizar paths en scripts tras reorganización
- [ ] Añadir idempotencia a parche
- [ ] Documentar métricas de performance

---

### 11-12 de febrero de 2026 - Implementación TCP

**Completado**:
- ✅ TCP server funcional (port 5000)
- ✅ Wrapper v2 con protocolo pipes correcto
- ✅ Parche SHARC para ejecución nativa
- ✅ Docker image con parche aplicado
- ✅ MPC computation validada (u=[0.0, 198.017], cycles=114M)
- ✅ Network connectivity Docker→Host verificada

**Logs de validación**:
```
[Server] Step 0: u=[0.0, 198.01712], cost=1.23e+03, status=OPTIMAL, t_delay=1.914000s
[Wrapper] Result: u=[0.0, 198.01712], status=OPTIMAL
[GVSOC] Using NATIVE execution (no SCARAB) for gvsoc_controller_wrapper_v2.py
```

---

### Enero-Febrero 2026 - Fase Exploratoria

**Experimentos**:
- ❌ Enfoque 1: Sockets directos desde C++ (SCARAB bloqueaba)
- ❌ Enfoque 2: OSQP solver (demasiado pesado, 20MB)
- ✅ Enfoque 3: QP solver custom (8KB, funcional)
- ✅ Enfoque 4: TCP bridge + parche SHARC (solución actual)

**Lecciones aprendidas**:
1. SCARAB no soporta network syscalls → necesario bypass
2. Orden de apertura de pipes es crítico para evitar deadlock
3. GVSoC `WFI` instruction no termina limpio → timeout necesario
4. Parche en tiempo de build Docker es reproducible

---

## Recursos Adicionales

### Enlaces

- **SHARC**: https://github.com/pwintz/sharc
- **GVSoC**: https://github.com/gvsoc/gvsoc
- **PULP Platform**: https://pulp-platform.org/

### Contacto

Para preguntas sobre esta integración, consultar con el equipo de desarrollo.

### Licencia

Este código integra componentes de SHARC (licencia original) y GVSoC (Apache 2.0).

---

**Última actualización**: 13 de febrero de 2026  
**Versión**: 1.0.0  
**Estado**: En desarrollo activo
