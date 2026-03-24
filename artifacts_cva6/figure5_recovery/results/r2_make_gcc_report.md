# R2 Make GCC Report

- status: `PASS`
- clean_sdk_dir: `/tmp/cva6-sdk-clean-20260324-r1-2`
- log: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/logs/r2_make_gcc.log`
- cxx_rebuild_log: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/logs/r2c_gxx_rebuild.log`

## First Failure Found

- stage: `host-m4`
- cause: `ccache` tried to write under `/home/jminiesta/.buildroot-ccache`
- exact symptom:
  - `ccache: error: Failed to create temporary file for /home/jminiesta/.buildroot-ccache/tmp/conftest.stdout: Read-only file system`

## Corrective Action Applied

- moved aside the seeded generated directories inherited from the active SDK:
  - `buildroot/output.pre_r2_seed_*`
  - `install64.pre_r2_seed_*`
- moved aside the partial output from the first `R2` failure:
  - `buildroot/output.pre_r2_ccache_fail_*`
  - `install64.pre_r2_ccache_fail_*`
- relaunched `make gcc` with:
  - `CCACHE_DIR=/tmp/buildroot-ccache`

## Second Issue Found

- stage: `C++ cross compiler availability`
- cause: the clean SDK toolchain was rebuilt without C++
- exact symptom:
  - `/tmp/cva6-sdk-clean-20260324-r1-2/buildroot/.config` had
    `# BR2_TOOLCHAIN_BUILDROOT_CXX is not set`
  - `riscv64-linux-g++` and `riscv64-buildroot-linux-gnu-g++` were absent

## Second Corrective Action Applied

- enabled `BR2_TOOLCHAIN_BUILDROOT_CXX=y` in the isolated SDK copy
- refreshed the clean Buildroot config with `olddefconfig`
- forced a real C++ rebuild with:
  - `make -C /tmp/cva6-sdk-clean-20260324-r1-2/buildroot host-gcc-final-dirclean`
  - `CCACHE_DIR=/tmp/buildroot-ccache make -C /tmp/cva6-sdk-clean-20260324-r1-2/buildroot host-gcc-final -j$(nproc)`
- verified from `config.log` that the rebuilt toolchain used:
  - `--enable-languages=c,c++`

## Current State

- the clean SDK now provides:
  - `/tmp/cva6-sdk-clean-20260324-r1-2/buildroot/output/host/bin/riscv64-buildroot-linux-gnu-gcc`
  - `/tmp/cva6-sdk-clean-20260324-r1-2/buildroot/output/host/bin/riscv64-buildroot-linux-gnu-g++`
  - `/tmp/cva6-sdk-clean-20260324-r1-2/buildroot/output/host/bin/riscv64-linux-gcc`
  - `/tmp/cva6-sdk-clean-20260324-r1-2/buildroot/output/host/bin/riscv64-linux-g++`
- the wrapper layout matches the active SDK pattern:
  - both compiler names are symlinks to `toolchain-wrapper`
- `host-gcc-final` finished cleanly after the C++ rebuild

## Next Gate

- `R3`: build `vmlinux`, `Image`, `rootfs.cpio`, and `spike_fw_payload.elf`
  from the isolated SDK

## Interpretation

- the reinstall path remains valid
- the first `R2` failure was environmental
- the second `R2` issue was configuration drift in the clean toolchain seed,
  and it is now corrected
- the isolated SDK is ready for the image rebuild phases
