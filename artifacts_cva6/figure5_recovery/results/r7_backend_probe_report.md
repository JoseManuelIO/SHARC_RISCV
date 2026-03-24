# R7 Backend Probe Report

- clean_sdk_dir: `/tmp/cva6-sdk-clean-20260324-r1-2`
- spike_probe: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r6_guest_runtime_probe.md`
- spike_persistent_probe: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r7_spike_persistent_probe.md`

## Result

- `spike`: `PASS`
- `spike_persistent`: `PASS`

## Meaning

- the clean SDK reinstall is now good enough to boot Linux, expose the SHARC
  runtime in the guest, and execute a real snapshot successfully in both
  oneshot `spike` mode and `spike_persistent` mode
- the clean reinstall has therefore recovered the backend path up to the
  pre-Figure-5 gate

## Evidence

- oneshot success:
  - classification: `runtime_present_and_executable`
  - solver status: `1`
  - backend mode: `spike`
  - delay: about `221.8 s`
- persistent success:
  - classification: `runtime_present_and_executable`
  - solver status: `1`
  - backend mode: `spike_persistent`
  - delay: about `193.5 s`

## Minimal Fix Applied

- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py` now validates staging hashes only
  when `STAGE_*_SHA=` lines are actually emitted
- this preserves hash checking for fresh staging while accepting the valid case
  where the runtime and config are already embedded in the guest

## Next Step

- run the Figure 5 wrapper flow against the clean SDK payload with
  `CVA6_SKIP_BUILD=1` and `CVA6_RUNTIME_MODE=spike_persistent`
