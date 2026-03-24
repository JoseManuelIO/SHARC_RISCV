# R0 Reinstall Backup Report

- status: `PASS`
- repo_head: `20d185a`
- sdk_head: `77fc4a9`
- backup_dir: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r0_reinstall_backup`
- manifest: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r0_reinstall_backup_manifest.txt`

## Backup Captured

- `install64/vmlinux` -> hash `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
- `install64/Image` -> hash `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`
- `install64/spike_fw_payload.elf` -> hash `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`
- `CVA6_LINUX/cva6-sdk/install64/vmlinux` -> same hash as repo-root backup
- `CVA6_LINUX/cva6-sdk/install64/Image` -> same hash as repo-root backup
- `CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf` -> same hash as repo-root backup

## Notes

- The active `cva6-sdk` tree is dirty, which reinforces the choice to avoid any
  in-place reinstall on the main repo copy.
- The backup manifest also records timestamps, current SDK status, and current
  submodule revisions for rollback.
