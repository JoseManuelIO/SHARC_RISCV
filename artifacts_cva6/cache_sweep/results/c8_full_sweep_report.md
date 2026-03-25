# C8 Full Sweep Report

- Date: 2026-03-25
- Status: PASS
- Manifest: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/cache_sweep_manifest.json`
- Aggregated report:
  - `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/spike_cache_sweep_report_full.json`
  - `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/spike_cache_sweep_report_full.csv`
  - `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/results/spike_cache_sweep_report_full.md`

## Sweep Result

- All 4 cache cases completed successfully with the protected payload kept intact:
  - `Baseline (no cachesim)`
  - `1 MB`
  - `262 KB`
  - `32 KB`
- The final aggregated report contains 8 rows:
  - 4 cache cases
  - 2 experiment modes per case (`baseline-no-delay-onestep`, `cva6-real-delays`)
- `feasible_ratio = 1.000` in all aggregated rows.

## Key Observation

- `cycles_mean` and `instret_mean` stay nearly flat across all cache configurations.
- `delay_mean_ms` increases materially when Spike cachesim is enabled:
  - baseline `baseline-no-delay-onestep`: `575.200 ms`
  - `1 MB` `baseline-no-delay-onestep`: `4498.080 ms`
  - `262 KB` `baseline-no-delay-onestep`: `4882.194 ms`
  - `32 KB` `baseline-no-delay-onestep`: `5261.417 ms`
  - baseline `cva6-real-delays`: `1352.267 ms`
  - `1 MB` `cva6-real-delays`: `8554.065 ms`
  - `262 KB` `cva6-real-delays`: `9621.276 ms`
  - `32 KB` `cva6-real-delays`: `10368.604 ms`

## Interpretation

- For this local Spike build, cachesim is clearly affecting host-observed execution delay.
- The same runs do not show a correspondingly strong variation in the reported architectural counters (`cycles_mean`, `instret_mean`).
- This reinforces the earlier conclusion: the current cachesim path is useful for comparative runtime/memory-behavior studies, but it should not yet be interpreted as a faithful microarchitectural timing model.

## Payload Protection Gate

- The protected artifacts still match the baseline hashes captured in `C0`:
  - `spike_fw_payload.elf`: `75f8d46a5e9ab5c840498543406196a36647a1e236285df7dbdb227cce328a19`
  - `vmlinux`: `e6ff4e686f6d0647073061302d1b73fda6c4b7f9ec9b7115fb260f05c650723a`
  - `Image`: `7675861a576490a78da06c39b50ca73fc99e19b800546cb68595f2d88eb877b3`
  - `rootfs.cpio`: `fb19e9cc6ef1e1c55ebce3a170bf2ed4d2fb411e5672cc8e89bdf69640a1f205`
  - repo `spike`: `99eb8993c4854acddc4161d9961661f77a442e40f0ef32837080cf45f0177c86`

## Notes

- The per-run hardware summaries were generated with:
  - `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cva6_research/archived_from_sharcbridge_cva6/collect_spike_hw_metrics.py`
- The local environment still lacks `matplotlib`, so the aggregated builder produced JSON/CSV/MD but skipped the PNG plot.
