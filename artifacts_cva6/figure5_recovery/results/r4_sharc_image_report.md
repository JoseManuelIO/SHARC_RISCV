# R4 SHARC Image Report

- status: `PASS`
- clean_sdk_dir: `/tmp/cva6-sdk-clean-20260324-r1-2`
- log: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/logs/r4_sharc_image_build.log`

## Gate Result

- `buildroot/output/target/usr/bin/sharc_cva6_acc_runtime`: present
- `buildroot/output/target/usr/share/sharcbridge_cva6/base_config.json`: present
- `install64/spike_fw_payload.elf`: regenerated

## Artifact Hashes

- `sharc_cva6_acc_runtime`: `7feec3f980d6c0c2502ef343242648971e3b10151ef76781b888c1f3fc4b86fa`
- `base_config.json`: `0b2f599ab2626d8fc8104b3c35640591c6db0bb4bd83afd4049084e686b413c9`
- `vmlinux`: `e6ff4e686f6d0647073061302d1b73fda6c4b7f9ec9b7115fb260f05c650723a`
- `spike_fw_payload.elf`: `75f8d46a5e9ab5c840498543406196a36647a1e236285df7dbdb227cce328a19`

## Interpretation

- the clean SDK now embeds the SHARC runtime and config into the rebuilt guest
- the next gate is booting this rebuilt guest and confirming it reaches a real
  shell before attempting snapshot execution
