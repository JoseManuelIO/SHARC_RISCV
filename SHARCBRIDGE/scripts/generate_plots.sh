#!/bin/bash
# Genera plots del último experimento ejecutado

EXPERIMENTS_DIR="/tmp/sharc_experiments"

# Encontrar experimento más reciente
LATEST=$(ls -t "$EXPERIMENTS_DIR" | grep -v latest | head -1)

if [ -z "$LATEST" ]; then
    echo "ERROR: No hay experimentos en $EXPERIMENTS_DIR"
    exit 1
fi

echo "Generando plots para: $LATEST"

# Ir al directorio del experimento
cd "$EXPERIMENTS_DIR/$LATEST"

# Convertir datos al formato esperado por el script de plots
python3 << 'EOF'
import json
import os

# Leer datos de la simulación
with open('gvsoc-serial/simulation_data_incremental.json') as f:
    sim_data = json.load(f)

with open('gvsoc-serial/config.json') as f:
    config = json.load(f)

# Crear formato esperado
experiment_list_data = {
    "GVSoC Serial": {
        "label": "GVSoC Serial",
        "experiment directory": os.getcwd(),
        "experiment data": {
            "k": sim_data["k"],
            "i": sim_data["i"],
            "t": sim_data["t"],
            "x": sim_data["x"],
            "u": sim_data["u"],
            "w": sim_data["w"],
            "pending_computations": sim_data.get("pending_computation", []),
            "batches": None,
            "config": config
        },
        "experiment config": config
    }
}

# Guardar
with open('experiment_list_data_incremental.json', 'w') as f:
    json.dump(experiment_list_data, f, indent=2)

print("✓ Datos formateados")
EOF

# Generar imagen
docker run --rm \
  -v "$EXPERIMENTS_DIR:/home/dcuser/examples/acc_example/experiments" \
  -w /home/dcuser/examples/acc_example \
  sharc-gvsoc:latest \
  bash -c "ln -sf experiments/$LATEST latest && python3 generate_example_figures.py"

echo ""
echo "✓ Plots generados: $EXPERIMENTS_DIR/$LATEST/plots.png"
echo ""

# Abrir imagen
xdg-open "$EXPERIMENTS_DIR/$LATEST/plots.png"
