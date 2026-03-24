# C11 Robust Staging Report

- date: `2026-03-24`
- scope: `last staging-hardening attempt in SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- smoke script: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/scripts/c11_robust_staging_smoke.py`
- result json: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/c11_robust_staging_smoke.json`
- persistent log: `/tmp/sharcbridge_cva6_runtime/persistent_session.log`

## What changed

- Added a real shell-readiness handshake before staging.
- Replaced the earlier console staging with heredoc-based base64 transfer.
- Added host-side hash and size checks for the staged runtime and config.

## Test

- command: `python3 artifacts_cva6/figure5_recovery/scripts/c11_robust_staging_smoke.py`
- gate: persistent mode must reach a stable interactive shell, complete guest staging, and return one `SUCCESS` snapshot.

## Result

- status: `FAIL`
- launcher error: `Could not establish an interactive guest shell before staging`

## Evidence

- The guest still reaches late boot markers:
  - `Starting sshd: OK`
  - `NFS preparation skipped, OK`
  - `#`
- As soon as the heredoc staging starts, the console stream becomes corrupted with long `AAAA...` fragments.
- The persistent session log shows a reboot back to `OpenSBI v0.9` immediately after staging begins.
- A later retry of the shell-ready markers interleaves with boot output and never reaches a stable prompt:
  - `echo __SHARCBRIDGE_SHELL_READY_0__`
  - `echo __SHARCBRIDGE_SHELL_READY_1__`

## Conclusion

- This robust-staging attempt is not reproducible on the current bootable CVA6 guest.
- The blocker is no longer "missing runtime/config transfer logic" but the instability of the guest console/control path itself under large command injection.
- Continuing to harden console staging is likely lower-value than reinstalling or rebuilding CVA6 from a clean baseline, then validating the guest before Figure 5.

## Recommended next step

- Prefer a clean `cva6-sdk` reinstall/rebuild path as the next recovery action.
- Keep the launcher changes only if we want to preserve the investigation branch; do not depend on this staging path as the production fix.
