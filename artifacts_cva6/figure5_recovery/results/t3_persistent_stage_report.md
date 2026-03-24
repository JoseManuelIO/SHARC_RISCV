# T3 Persistent Backend Recovery

- status: `IN_PROGRESS`
- target_mode: `spike_persistent`
- date: `2026-03-24`

## What Now Works

- `cva6_runtime_launcher.py` no longer injects the snapshot at `Run /init` or `rpcbind`.
- The launcher now waits for late boot progress and reaches a real shell prompt in the March guest:
  - `Starting sshd: OK`
  - `NFS preparation skipped, OK`
  - `# `
- A direct diagnostic command confirmed the guest can execute shell commands after boot.

## Conclusive Guest Findings

- `/usr/bin/sharc_cva6_acc_runtime`: `MISSING`
- `/usr/share/sharcbridge_cva6/base_config.json`: `MISSING`
- `/lib/ld-linux-riscv64-lp64d.so.1`: `EXISTS`

This means the current March bootable guest is usable as a shell environment, but it does not embed the SHARC runtime payload or its base config. The loader is present, so the blocker is not the dynamic linker anymore.

## Tests Run

1. `t2_boot_observer.py`
   - Result: boot reaches late init markers and shell path.
2. Direct persistent shell presence probe
   - Result: `PASS`
   - Evidence: prompt reached and commands executed.
3. Direct asset presence probe in guest
   - Result: `FAIL`
   - Runtime/config missing, loader present.
4. Persistent launcher smoke after late-boot fixes
   - Result: no longer times out at boot; failure moved to guest asset availability / stage path.

## Side-Load Attempts

1. Plain runtime execution from guest path
   - Result: `FAIL`
   - Error: `/usr/bin/sharc_cva6_acc_runtime: not found`
2. Compressed runtime side-load (`gzip`)
   - Result: `FAIL`
   - Guest error: `gzip: not found`
3. Runtime/config stage via console
   - Result: partially improved, but still not stable enough to close T3 in this session.

## Current Conclusion

The recovery is now narrowed to a single functional gap:

- either restore a bootable guest image that already contains:
  - `/usr/bin/sharc_cva6_acc_runtime`
  - `/usr/share/sharcbridge_cva6/base_config.json`
- or finish a robust minimal side-load path for those two assets in `spike_persistent`.

The boot/shell path is no longer the main blocker.
