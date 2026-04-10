# Spike HW Metrics Validation

## Scope

Validation of `SHARCBRIDGE_CVA6/collect_spike_hw_metrics.py` and its integration into `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`.

## Static checks

- `python3 -m py_compile SHARCBRIDGE_CVA6/collect_spike_hw_metrics.py`: PASS
- `bash -n SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`: PASS

## Collector smoke test on existing run

Input run:

- `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5`

Generated outputs:

- `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/latest/hw_metrics_spike_test.json`
- `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/latest/hw_metrics_spike_test.csv`
- `/tmp/sharc_cva6_figure5/2026-03-18--13-00-16-cva6_figure5/latest/hw_metrics_spike_test.md`

Result:

- PASS

## End-to-end Figure 5 validation

Command executed:

```bash
source venv/bin/activate
CVA6_SKIP_BUILD=1 CVA6_PORT=5012 CVA6_RUNTIME_MODE=spike_persistent bash SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh
```

Output run:

- `/tmp/sharc_cva6_figure5/2026-03-18--13-35-10-cva6_figure5`

Generated outputs in `latest/`:

- `plots.png`
- `experiment_list_data_incremental.json`
- `hw_metrics_spike.json`
- `hw_metrics_spike.csv`
- `hw_metrics_spike.md`
- `hw_metrics_spike.png`

Result:

- PASS

## Notes

- The exported hardware table only contains metrics that are real in the current `Spike` backend.
- Unsupported microarchitectural metrics are explicitly called out in `hw_metrics_spike.md`.
- In the current end-to-end run, `matplotlib` was available and `hw_metrics_spike.png` was generated successfully.
