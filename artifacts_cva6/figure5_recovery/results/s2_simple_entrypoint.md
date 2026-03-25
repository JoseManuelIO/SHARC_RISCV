# S2 Simple Entrypoint

- fecha: `2026-03-25`
- estado: `PASS`

## Comando normal

```bash
./run_cva6_figure5_tcp.sh
```

## Defaults simplificados

- `CVA6_RUNTIME_MODE=spike_persistent`
- `CVA6_SKIP_BUILD=1` cuando el `SDK` bueno existe
- `CVA6_PORT=5001`
- overrides opcionales por entorno cuando se quiera aislar una prueba

## Comando recomendado para aislamiento manual

```bash
CVA6_PORT=5019 ./run_cva6_figure5_tcp.sh
```

## Gate

- ya existe una forma corta y estable de lanzar Figure 5
