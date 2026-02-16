# SHARC + GVSoC Integration

Este repositorio integra el framework **SHARC** (Simulation framework for Hardware-Accelerated Robot Controllers) con **GVSoC** (GAP Virtual SOC), un simulador cycle-accurate de arquitectura RISC-V de la plataforma PULP.

## 🎯 ¿Qué hace este proyecto?

Permite simular controladores MPC (Model Predictive Control) escritos en C y compilados para RISC-V, ejecutándolos en un simulador cycle-accurate (GVSoC) mientras SHARC simula la planta dinámica. El sistema mide automáticamente los **ciclos de CPU reales** que tarda el controlador, permitiendo análisis de rendimiento realistas.

### Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    SHARC (Docker Container)                      │
│  ┌──────────────┐         ┌─────────────────────┐               │
│  │  Plant       │         │  Python Wrapper     │               │
│  │  Dynamics    │◄───────►│  (Named Pipes       │               │
│  │  (ACC)       │  FIFOs  │   ↔ TCP Bridge)     │               │
│  └──────────────┘         └──────────┬──────────┘               │
└────────────────────────────────────────┼────────────────────────┘
                                         │ TCP (port 5000)
                                         │
                          ┌──────────────▼──────────────┐
                          │  GVSoC TCP Server (Host)    │
                          │  • Patches ELF with state   │
                          │  • Executes GVSoC           │
                          │  • Reads cycle counter      │
                          │  • Returns control + cycles │
                          └─────────────────────────────┘
```

## 📁 Estructura del Repositorio

### `SHARCBRIDGE/` - **Código principal de la integración** (creado en este proyecto)
Componentes desarrollados para integrar SHARC con GVSoC:

```
SHARCBRIDGE/
├── scripts/
│   ├── gvsoc_tcp_server.py           # Servidor TCP que ejecuta GVSoC (host)
│   ├── run_integration_test.sh       # Test end-to-end automatizado
│   └── generate_plots.sh             # Genera gráficos de resultados
├── mpc/
│   ├── mpc_acc_controller.c          # Controlador MPC en C para RISC-V
│   ├── qp_solver.c / qp_solver.h     # Solver QP custom
│   ├── start.S                       # Assembly startup code
│   ├── riscv.ld                      # Linker script RISC-V
│   └── build/mpc_acc_controller.elf  # Binary compilado (~8KB)
├── docker/
│   ├── Dockerfile.gvsoc              # Imagen Docker con SHARC + wrapper
│   └── patch_sharc_for_gvsoc.py      # Patch para ejecutar wrapper Python
└── configs/
    └── acc_example/
        └── simulation_configs/
            └── gvsoc_test.json       # Config: 20 steps, use_gvsoc_controller=true
```

**Total: 29 archivos**, todos necesarios para la integración.

### `PULP/` - **Plataforma PULP** (repositorios externos)
Herramientas del ecosistema PULP Platform necesarias:

- **`pulp-sdk/`**: SDK de PULP con toolchain RISC-V y runtime
- **`gvsoc/`**: Simulador GVSoC (cycle-accurate, ISS)
- **`pulp-riscv-gnu-toolchain/`**: Compilador de RISC-V (gcc, binutils)
- **`dory/`**: Generador de código para DNNs (NO usado en este proyecto)

**Nota**: Estos son repositorios Git independientes. Ver sección de instalación.

### `sharc_original/` - **Framework SHARC** (repositorio externo)
Framework base de simulación:

- **`examples/acc_example/`**: Ejemplo de Adaptive Cruise Control
- **`libmpc/`**: Biblioteca MPC original (C++)
- **`docs/`**: Documentación del framework

**Archivos modificados**: Los archivos modificados de SHARC están en **`SHARCBRIDGE/sharc_patches/`**:
- `acc_example/gvsoc_controller_wrapper_v2.py` - Wrapper con TCP + EOF handling
- `acc_example/simulation_configs/gvsoc_test.json` - Configuración de 20 steps

Ver [SHARCBRIDGE/sharc_patches/README_PATCHES.md](SHARCBRIDGE/sharc_patches/README_PATCHES.md) para detalles.

### `venv/` - **Python Virtual Environment**
Entorno virtual de Python con dependencias:
- numpy, scipy, matplotlib
- Paquetes del PULP SDK (gapy, gvsoc)

**Este directorio NO se sube a Git** (.gitignore lo excluye).

## 🚀 Instalación

### 1. Requisitos Previos

```bash
# Sistema operativo
Ubuntu 20.04+ / Debian 11+

# Herramientas base
sudo apt update
sudo apt install -y git build-essential cmake ninja-build \
                    python3 python3-pip python3-venv \
                    docker.io libsystemc-dev

# Añadir usuario a grupo docker
sudo usermod -aG docker $USER
newgrp docker  # O reinicia sesión
```

### 2. Clonar Repositorio

**Opción A: Con submódulos Git** (recomendado)
```bash
git clone --recursive https://github.com/TU_USUARIO/SHARC_RISCV.git
cd SHARC_RISCV
```

**Opción B: Si ya clonaste sin --recursive**
```bash
git clone https://github.com/TU_USUARIO/SHARC_RISCV.git
cd SHARC_RISCV
git submodule update --init --recursive
```

### 3. Compilar PULP SDK

```bash
cd PULP/pulp-sdk
source configs/pulp-open.sh
make build
```

**Tiempo estimado**: 15-30 minutos (compilación de toolchain)

### 4. Compilar GVSoC

```bash
cd ../gvsoc
./commands install --gap9-platform=gvsoc  # O --platform=pulp según tu target
```

### 5. Configurar Python Virtual Environment

```bash
cd ~/Repositorios/SHARC_RISCV
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias de SHARC
pip install numpy scipy matplotlib

# Instalar gapy (Python API de GVSoC)
cd PULP/gvsoc
pip install -e .
```

### 6. Construir Docker Image de SHARC

```bash
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE
docker build -f docker/Dockerfile.gvsoc -t sharc-gvsoc:latest .
```

### 7. Compilar Controlador MPC RISC-V

```bash
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/mpc
source ../../PULP/pulp-sdk/configs/pulp-open.sh
make
```

**Resultado**: `build/mpc_acc_controller.elf` (~8KB)

## ▶️ Uso

### Test de Integración Completo

Este script ejecuta el test end-to-end: SHARC + Wrapper + GVSoC + Plots

```bash
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/scripts
source ../../venv/bin/activate
./run_integration_test.sh
```

**¿Qué hace?**
1. Comprueba que el servidor TCP de GVSoC esté corriendo
2. Lanza SHARC en Docker (20 iteraciones)
3. Espera a que SHARC cree los FIFOs
4. Ejecuta el wrapper Python (puente FIFO ↔ TCP)
5. Genera gráficos automáticamente al finalizar

**Resultado esperado**:
```
[Wrapper] Iteration 0: t=0.000, x=[30.0, 0.0, 5.0], w=[0.0, -1.0]
[Wrapper] Result: u=[0.0, 1234.56], status=OPTIMAL, cycles=755234
...
[Wrapper] Iteration 19: t=3.800, x=[29.85, 0.02, 4.98], w=[0.0, -1.2]
[Wrapper] EOF reached: END OF PIPE on k
=== Integration test PASSED ===
```

**Plots generados**: `/tmp/sharc_experiments/<timestamp>/plots.png`
- Velocidad ego vs. front vehicle
- Headway (distancia relativa)
- Delays (latencia del controlador)
- Control forces (aceleración aplicada)

### Ejecutar Solo el Servidor GVSoC

Si quieres ejecutar simulaciones manualmente:

```bash
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/scripts
source ../../venv/bin/activate
python3 gvsoc_tcp_server.py
```

**Puerto**: 5000 (TCP)  
**Protocolo**: JSON `{"x": [...], "w": [...], "t": ...}` → `{"u": [...], "cycles": ..., "status": "..."}`

### Generar Solo los Plots

Si ya ejecutaste la simulación y quieres regenerar plots:

```bash
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/scripts
./generate_plots.sh
```

## 🔍 ¿Cómo Funciona?

### Named Pipes (FIFOs)

SHARC usa **FIFOs** para comunicación entre planta (dynamics) y controlador:

```
/tmp/sharc_experiments/<timestamp>/gvsoc-serial/
├── fifo_k     # Planta → Controlador: iteration k
├── fifo_t     # Planta → Controlador: tiempo t
├── fifo_x     # Planta → Controlador: estado [x1, x2, x3]
├── fifo_w     # Planta → Controlador: exogenous inputs [w1, w2, ...]
├── fifo_u     # Controlador → Planta: control [u1, u2]
├── fifo_metadata  # Controlador → Planta: {"latency": cycles, "status": "OPTIMAL"}
└── fifo_t_delay   # Planta → Controlador: delay adicional (NO usado)
```

**Orden de apertura crítico** (evita deadlock):
1. **Escritura primero**: `fifo_u`, `fifo_metadata` (abiertos para escritura)
2. **Lectura después**: `fifo_k`, `fifo_t`, `fifo_x`, `fifo_w`, `fifo_t_delay` (abiertos para lectura)

**Final de simulación**: SHARC escribe `"END OF PIPE"` en cada FIFO para señalizar EOF.

### Dinámica del ACC (Adaptive Cruise Control)

El sistema simula un vehículo ego siguiendo a un vehículo delantero:

**Estados** (3):
- `x[0]`: Velocidad relativa `v_ego - v_front` [m/s]
- `x[1]`: Headway `h_ego - h_front` [m] (distancia relativa)
- `x[2]`: Error integral de velocidad

**Controles** (2):
- `u[0]`: Fuerza longitudinal [N]
- `u[1]`: (no usado en ACC, siempre 0)

**Exogenous inputs** (2):
- `w[0]`: Aceleración del vehículo delantero [m/s²]
- `w[1]`: Velocidad deseada [m/s]

**Ecuaciones de estado**:
```
x[0]' = (u[0] - m*w[0]) / m  # Dinámica de velocidad relativa
x[1]' = x[0]                  # Integración de velocidad → posición
x[2]' = x[0] - w[1]          # Error integral
```

**Constantes**:
- `m = 1000` kg (masa del vehículo)
- `T_s = 0.2` s (tiempo de muestreo)
- `N = 5` (horizonte de predicción MPC)

## 📊 Resultados Esperados

### Ciclos de CPU por iteración MPC

- **Promedio**: ~755,000 cycles
- **Frecuencia simulada**: 50 MHz (GVSoC GAP9)
- **Latencia real**: ~15 ms

### Precisión del Controlador

- **Distancia mínima mantenida**: `d_min = 5.0` m (configurado en constraints)
- **Error de seguimiento**: < 0.5 m (headway tracking)
- **Convergencia**: 3-5 iteraciones (QP solver)

## 🐛 Troubleshooting

### Error: "Address already in use" (puerto 5000)

```bash
# Encuentra el proceso usando el puerto
lsof -i :5000
# O con netstat
netstat -tulpn | grep 5000

# Mata el proceso
kill -9 <PID>
```

### Error: "Cannot connect to TCP server"

Verifica que el servidor esté corriendo:

```bash
# En terminal separado
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/scripts
source ../../venv/bin/activate
python3 gvsoc_tcp_server.py
```

### Error: "ELF file not found"

Recompila el controlador MPC:

```bash
cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/mpc
source ../../PULP/pulp-sdk/configs/pulp-open.sh
make clean && make
```

### Error: Docker "permission denied"

```bash
sudo usermod -aG docker $USER
newgrp docker
```

### SHARC se queda esperando en FIFO

El wrapper debe ejecutarse **después** de que SHARC cree los FIFOs. El script `run_integration_test.sh` ya maneja esto automáticamente con un loop de detección.

## 📚 Referencias

- **SHARC**: [https://github.com/sharc-project/sharc](Original repository)
- **PULP Platform**: [https://github.com/pulp-platform](GVSoC, SDK)
- **GVSoC Docs**: [https://pulp-platform.github.io/gvsoc/](Official documentation)
- **RISC-V Spec**: [https://riscv.org/technical/specifications/](ISA manual)

## 📝 Licencia

Este proyecto combina múltiples componentes con diferentes licencias:
- **SHARC**: MIT License
- **PULP Platform**: Apache 2.0
- **SHARCBRIDGE** (este trabajo): MIT License

Ver archivos LICENSE en cada subdirectorio.

## 👥 Autores

- **Integración SHARC + GVSoC**: [Tu nombre]
- **SHARC Framework**: Original authors
- **PULP Platform**: ETH Zurich, University of Bologna

## 🎓 Citación

Si usas este código en investigación académica, por favor cita:

```bibtex
@misc{sharc_gvsoc_2026,
  author = {Tu Nombre},
  title = {SHARC + GVSoC Integration: Cycle-Accurate MPC Simulation},
  year = {2026},
  publisher = {GitHub},
  url = {https://github.com/TU_USUARIO/SHARC_RISCV}
}
```
