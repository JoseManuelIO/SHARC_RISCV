#!/bin/bash
# Script para borrar archivos opcionales creados durante desarrollo

cd ~/Repositorios/SHARC_RISCV

echo "Borrando archivos opcionales..."

# Logs y temporales
rm -fv SHARCBRIDGE/mpc/hyperflash.bin
rm -fv SHARCBRIDGE/mpc/tx_uart.log
rm -fv SHARCBRIDGE/mpc/trace_file.txt
rm -fv SHARCBRIDGE/mpc/power_report.csv

# Build artifacts (regenerables)
rm -fv SHARCBRIDGE/mpc/build/*.o
rm -fv SHARCBRIDGE/mpc/build/mpc_acc_controller.map

# Documentación histórica
rm -fv SHARCBRIDGE/IMPLEMENTATION_STATUS.md
rm -fv SHARCBRIDGE/TEST_RESULTS.md
rm -fv SHARCBRIDGE/TEST_RESULTS_FINAL.md
rm -fv SHARCBRIDGE/INDEX.md
rm -fv SHARCBRIDGE/mpc/README.md

# Scripts duplicados en raíz
rm -fv GVSOC_QUICKSTART.md
rm -fv test_gvsoc_integration.sh
rm -fv test_mpc_gvsoc.sh
rm -fv SHARCBRIDGE_SETUP.sh

echo ""
echo "✓ Limpieza completada"
echo "Archivos críticos conservados:"
echo "  - SHARCBRIDGE/scripts/*.py"
echo "  - SHARCBRIDGE/docker/*"
echo "  - SHARCBRIDGE/mpc/*.{c,h,S,ld,Makefile}"
echo "  - SHARCBRIDGE/mpc/build/mpc_acc_controller.elf"
echo "  - SHARCBRIDGE/README.md + QUICKSTART.md"
