# Cache Sweep

Esta carpeta contiene solo el flujo operativo actual para generar la variante de cache de Figure 5 sobre la misma base CVA6/SHARC del flujo principal.

## Resumen por carpeta

### `configs/`

- `cache_sweep_matrix.json`: matriz completa de casos que define baseline, `1 MB`, `262 KB` y `32 KB`.
- `cache_sweep_matrix_smoke.json`: matriz reducida para comprobaciones rápidas.

### `scripts/`

- `run_spike_cache_sweep.sh`: runner principal del barrido de caché. Lanza Figure 5 caso a caso con `SPIKE_CACHE_ARGS`, recoge los `OUT_DIR` y publica el resultado final.
- `publish_cache_latest.py`: construye el bundle público y la figura final en `latest/`.

### `latest/`

- Contiene la salida publicada más reciente del barrido de caché.
- `experiment_list_data_incremental.json`: bundle listo para consumo externo.
- `plot_cache.png`: figura principal de comparación de cachés.
- `cache_latest_report.json`: trazabilidad mínima de la publicación.

### `results/`

- Guarda la evidencia de la última ejecución operativa del barrido.
- `cache_sweep_manifest.json`: manifiesto con casos, puertos, logs y `OUT_DIR` de cada corrida.
- `*.log`: logs por caso y del paso de publicación.

## Flujo principal

1. Ejecutar `bash artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh`.
2. El runner reutiliza `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh` para cada punto de caché.
3. Al terminar, `publish_cache_latest.py` actualiza `latest/`.

## Criterio de limpieza aplicado

- Se eliminaron planes antiguos, backups del SDK, variantes experimentales, replay cerrado, logs manuales y scripts fuera del camino crítico.
- La carpeta queda centrada en el flujo que hoy se ejecuta y en la salida que hoy se consume.
