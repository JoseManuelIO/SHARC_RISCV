# R1 Clean SDK Source Report

- status: `PASS`
- clean_sdk_dir: `/tmp/cva6-sdk-clean-20260324-r1-2`
- target_commit: `77fc4a9`
- state_file: `/home/jminiesta/Repositorios/SHARC_RISCV/artifacts_cva6/figure5_recovery/results/r1_clean_sdk_state.txt`

## What Was Done

- Copied the active `CVA6_LINUX/cva6-sdk` into an isolated `/tmp` workspace.
- Restored the copied SDK worktree to commit `77fc4a9`.
- Reinitialized the copied SDK submodules inside the isolated workspace.
- Repaired missing tracked directories in the isolated copy and rechecked status.

## Gate Result

- `git rev-parse --short HEAD`: `PASS` -> `77fc4a9`
- `git status --short --ignore-submodules=all`: `PASS` -> clean output
- `git submodule status`: `PASS`

## Submodules Seen In The Clean Copy

- `buildroot`: `aa433d1c5cfbd72b64ff3f92f2ffa2e02ea7089b`
- `opensbi`: `be245acfffa297b5ed4e0c7bb473a6bd55231bf8`
- `riscv-isa-sim`: `cc38be9991f3abd0831d141ebff8b4fd7a4990ea`
- `riscv-tests`: `fbd7e037ec947c6e9dddc9b78c1cd6bc0fce9993`
- `u-boot`: `f6220650cabb75933abf932c8cbed40363e44f0a`
- `vitetris`: `a922c8b8d082ba0af056d2650950e3be0f5a7b90`

## Conclusion

- The reinstall workflow can now proceed against the isolated SDK copy without
  touching the active SDK in the main repository.
