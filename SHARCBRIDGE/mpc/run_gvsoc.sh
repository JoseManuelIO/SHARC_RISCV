#!/bin/bash

# Script para ejecutar MPC controller en GVSOC
# Configura el entorno necesario y ejecuta el simulador

set -e

# Configurar toolchain
export PULP_RISCV_GCC_TOOLCHAIN=/opt/riscv

# Configurar PULP SDK
PULP_SDK_HOME="$HOME/Repositorios/SHARC_RISCV/PULP/pulp-sdk"
cd "$PULP_SDK_HOME"
source configs/pulp-open.sh

# Volver al directorio de la aplicación
APP_DIR="$HOME/Repositorios/SHARC_RISCV/SHARCBRIDGE/mpc"
cd "$APP_DIR"

# Ejecutar en GVSOC
echo "=========================================="
echo "Ejecutando MPC Controller en GVSOC"
echo "=========================================="
echo "Binary: build/mpc_acc_controller.elf"
echo ""

GVSOC_BIN="$HOME/Repositorios/SHARC_RISCV/PULP/gvsoc/install/bin/gvsoc"
$GVSOC_BIN --target=pulp-open --binary=build/mpc_acc_controller.elf run
