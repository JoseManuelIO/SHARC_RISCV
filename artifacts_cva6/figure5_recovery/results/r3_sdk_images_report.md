# R3 SDK Images Report

- status: `PASS`
- clean_sdk_dir: `/tmp/cva6-sdk-clean-20260324-r1-2`
- log: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/logs/r3_sdk_images_build.log`
- manifest: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r3_sdk_images_manifest.txt`

## Gate Result

- `buildroot/output/images/rootfs.cpio`: present
- `install64/vmlinux`: present
- `install64/Image`: present
- `install64/spike_fw_payload.elf`: present

## Artifact Hashes

- `rootfs.cpio`: `0ff9c13660bec3438b027dee9da742d8c786ab202e684bee2c5b64cf4979fe8a`
- `vmlinux`: `f0775845a2eecda37030a8f65a587aba18cff9770aa69eaedd4b9801e06670c5`
- `Image`: `7e833eec4e4fe9de3af6c47506843095de408ce905b7e8047c15dedfa0fc7c67`
- `spike_fw_payload.elf`: `caf25a2d0152aa927ee6640dd7102957241187781cbe60eb6357244b1bc0093f`

## Interpretation

- the isolated SDK can rebuild the base Linux image chain end to end
- the clean reinstall path remains viable after enabling C++ in the toolchain
- the next gate is no longer the SDK itself, but SHARC integration on top of
  this rebuilt base image
