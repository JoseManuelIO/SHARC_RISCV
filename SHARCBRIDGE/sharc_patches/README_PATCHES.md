# SHARC Patches

Estos archivos son modificaciones del repositorio SHARC original necesarias para la integración con GVSoC.

## Archivos Modificados

### `acc_example/gvsoc_controller_wrapper_v2.py`

**Ubicación original**: `sharc_original/examples/acc_example/gvsoc_controller_wrapper_v2.py`

**Modificaciones**:
- Añadido método `_read_line()` para manejo robusto de EOF
- Detección de string "END OF PIPE" como señal de finalización
- Manejo de `EOFError` y `BrokenPipeError` para cierre limpio
- Comunicación TCP con servidor GVSoC (host-based)
- Apertura de FIFOs en orden correcto para evitar deadlock

### `acc_example/simulation_configs/gvsoc_test.json`

**Ubicación original**: `sharc_original/examples/acc_example/simulation_configs/gvsoc_test.json`

**Contenido**: 
- Configuración de test con 20 time steps
- `use_gvsoc_controller: true` para activar wrapper
- `parallel_scarab_simulation: false` (ejecución serial)
- `in-the-loop_delay_provider: "onestep"` (simplicidad)

## Uso

### Durante Build de Docker

El Dockerfile copia estos archivos a la imagen:

```dockerfile
COPY SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py \
     /root/sharc/examples/acc_example/
COPY SHARCBRIDGE/sharc_patches/acc_example/simulation_configs/gvsoc_test.json \
     /root/sharc/examples/acc_example/simulation_configs/
```

### Para Desarrollo Local

Si quieres probar cambios sin rebuild del Docker:

```bash
# Copiar manualmente a sharc_original
cp SHARCBRIDGE/sharc_patches/acc_example/*.py \
   sharc_original/examples/acc_example/

cp SHARCBRIDGE/sharc_patches/acc_example/simulation_configs/*.json \
   sharc_original/examples/acc_example/simulation_configs/
```

## Aplicar Patches al SHARC Original

Si clonas el repo desde GitHub:

```bash
# 1. Clonar submódulo SHARC
git submodule update --init sharc_original

# 2. Copiar patches
cp -r SHARCBRIDGE/sharc_patches/acc_example/* \
      sharc_original/examples/acc_example/
```

O simplemente construye el Docker, que lo hace automáticamente.
