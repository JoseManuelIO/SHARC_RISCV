# Timing Comparison (T6.3)

- Generated: `2026-02-23T10:37`

## Reference (Original SHARC + Scarab)
- `smoke_test.json`: container_real=`113.091`s, host_real=`None`s

## GVSoC (Current path)
- `gvsoc_test.json`: host_real=`6.31`s
- `gvsoc_figure5.json`: host_real=`23.659`s

## Controlled A/B Runtime (same config, fake delays)
- Config: `sharc_original/examples/acc_example/simulation_configs/ab_onestep_compare.json`
- `A-Original-Onestep`: `12.23`s
- `B-GVSoC-Onestep`: `10.50`s

## Environment Limitation
- Running original with real Scarab execution in this environment fails with:
  - `setarch: failed to set personality to x86_64: Operation not permitted`
- Because of this, the strict apples-to-apples Scarab-real comparison is still pending.

## Notes
- Initial baseline exists, and a controlled A/B runtime with mock delays is now available.
- T6 remains `EN CURSO` until we can run equivalent Scarab-real and GVSoC scenarios with the same configuration basis.
