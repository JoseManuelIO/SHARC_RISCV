# S8 Permanent Mainline Hardening

- date: `2026-03-27`
- status: `PASS`

## Goal

Turn the recovered `CVA6` baseline into the permanent default behavior of the repo:

- one single SDK root
- no implicit `/tmp` fallback
- no implicit payload fallback outside `cva6-sdk`
- early failure if `install64/` is overwritten with an unvalidated triplet

## Mainline Changes

### 1. Single default SDK root

Updated:

- `/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
- `/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- `/home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/cva6_image_builder.sh`

Default SDK root is now:

- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk`

No active mainline script still prefers `/tmp/cva6-sdk-clean-20260324-r1-2`.

### 2. Validated boot triplet guard

`run_cva6_figure5_tcp.sh` and `cva6_runtime_launcher.py` now reject the run by default unless:

- `spike_fw_payload.elf = 6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`
- `vmlinux = fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
- `Image = fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`

Override only for deliberate experiments:

- `CVA6_ALLOW_UNVERIFIED_TRIPLET=1`

### 3. Non-destructive builder default

`cva6_image_builder.sh` no longer rebuilds `install64/` by default.

Default behavior:

- rebuild runtime binary
- refresh target runtime/config in `buildroot/output/target`
- leave the validated boot triplet untouched

Explicit opt-in for boot-triplet rebuild:

- `CVA6_REBUILD_BOOT_TRIPLET=1`

### 4. Cache sweep default aligned

Updated:

- `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh`

The sweep now defaults to the same persistent SDK root in `CVA6_LINUX/cva6-sdk`.

## Validation

Syntax / import checks:

- `bash -n SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
- `bash -n SHARCBRIDGE_CVA6/cva6_image_builder.sh`
- `python3 -m py_compile SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- `bash -n artifacts_cva6/cache_sweep/scripts/run_spike_cache_sweep.sh`

Full mainline revalidation:

```bash
CVA6_PORT=5122 \
CVA6_SKIP_BUILD=1 \
CVA6_RUNTIME_MODE=spike_persistent \
CVA6_SDK_DIR=/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk \
bash /home/jminiesta/Repositorios/SHARC_RISCV/SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh
```

Output:

- `/tmp/sharc_cva6_figure5/2026-03-27--11-09-27-cva6_figure5/latest/experiment_list_data_incremental.json`
- `/tmp/sharc_cva6_figure5/2026-03-27--11-09-27-cva6_figure5/latest/plots.png`

Experiment checks:

- `cva6-real-delays`: `unique_k=64`, `max_k=63`, `t_last=12.8`
- `baseline-no-delay-onestep`: `unique_k=64`, `max_k=63`, `t_last=12.8`

## Result

The repo now defaults to the stable consolidated SDK root and actively blocks the exact drift that had previously broken the flow after reboot or rebuild.
