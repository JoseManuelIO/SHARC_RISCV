#!/bin/bash
# Integration test: SHARC + GVSoC via TCP
set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== SHARC + GVSoC Integration Test ===${NC}"

# 1. Verificar que el servidor TCP esté corriendo
echo -e "${YELLOW}[1/5] Checking if TCP server is running on port 5000...${NC}"
if ! nc -z 127.0.0.1 5000 2>/dev/null; then
    echo -e "${RED}ERROR: TCP server not running on port 5000${NC}"
    echo "Start it in another terminal with:"
    echo "  cd ~/Repositorios/SHARC_RISCV/SHARCBRIDGE/scripts"
    echo "  source ../../venv/bin/activate"
    echo "  python3 gvsoc_tcp_server.py"
    exit 1
fi
echo -e "${GREEN}✓ TCP server is running${NC}"

# 2. Limpiar experimentos anteriores
echo -e "${YELLOW}[2/5] Cleaning previous experiments...${NC}"
rm -rf /tmp/sharc_experiments/*
mkdir -p /tmp/sharc_experiments
echo -e "${GREEN}✓ Clean workspace ready${NC}"

# 3. Arrancar SHARC en background
echo -e "${YELLOW}[3/5] Starting SHARC (creating FIFOs)...${NC}"
docker run --rm -d --name sharc_test --network=host \
  -e GVSOC_HOST=127.0.0.1 -e GVSOC_PORT=5000 \
  -v /tmp/sharc_experiments:/home/dcuser/examples/acc_example/experiments \
  -w /home/dcuser/examples/acc_example \
  sharc-gvsoc:latest \
  sharc --config_filename gvsoc_test.json

# 4. Esperar a que SHARC cree los FIFOs
echo -e "${YELLOW}[4/5] Waiting for FIFOs to be created...${NC}"
for i in {1..30}; do
    sleep 1
    EXPDIR=$(ls -t /tmp/sharc_experiments 2>/dev/null | head -1)
    if [ -n "$EXPDIR" ]; then
        SIMDIR=$(ls -t /tmp/sharc_experiments/"$EXPDIR" 2>/dev/null | head -1)
        if [ -n "$SIMDIR" ]; then
            FIFO_PATH="/tmp/sharc_experiments/$EXPDIR/$SIMDIR/k_py_to_c++"
            if [ -p "$FIFO_PATH" ]; then
                echo -e "${GREEN}✓ FIFOs found in: $EXPDIR/$SIMDIR${NC}"
                echo -e "${GREEN}  Listing pipes:${NC}"
                ls -lh /tmp/sharc_experiments/"$EXPDIR"/"$SIMDIR"/ | grep "^p"
                break
            fi
        fi
    fi
    echo -n "."
done

if [ ! -p "$FIFO_PATH" ]; then
    echo -e "${RED}ERROR: FIFOs not created after 30 seconds${NC}"
    docker logs sharc_test
    docker stop sharc_test
    exit 1
fi

# 5. Arrancar wrapper
echo -e "${YELLOW}[5/5] Starting wrapper...${NC}"
echo -e "${GREEN}Experiment dir: $EXPDIR${NC}"
echo -e "${GREEN}Simulation dir: $SIMDIR${NC}"

docker run --rm --network=host \
  -v /tmp/sharc_experiments:/home/dcuser/examples/acc_example/experiments \
  -e GVSOC_HOST=127.0.0.1 -e GVSOC_PORT=5000 \
  sharc-gvsoc:latest \
  python3 /home/dcuser/examples/acc_example/gvsoc_controller_wrapper_v2.py \
  /home/dcuser/examples/acc_example/experiments/"$EXPDIR"/"$SIMDIR"

WRAPPER_EXIT=$?

# 6. Cleanup
echo -e "${YELLOW}Stopping SHARC container...${NC}"
docker stop sharc_test 2>/dev/null || true

if [ $WRAPPER_EXIT -eq 0 ]; then
    echo -e "${GREEN}=== Integration test PASSED ===${NC}"
    
    # 7. Generate plots
    echo -e "${YELLOW}Generating plots...${NC}"
    $(dirname $0)/generate_plots.sh
    
    echo -e "${GREEN}✓ Plot saved to: /tmp/sharc_experiments/$EXPDIR/$SIMDIR/../plots.png${NC}"
else
    echo -e "${RED}=== Integration test FAILED (exit code: $WRAPPER_EXIT) ===${NC}"
    exit 1
fi
