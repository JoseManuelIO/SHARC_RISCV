# C1 Git Drift Report

## Status

`PASS`

## Goal

Identify the tracked repo changes between the original CVA6 enablement baseline
and the later Figure 5 completion commit, and separate them from local generated
state.

## Commit range

- baseline candidate: `7c61d44` (`cambios para cva6`)
- later good-flow commit: `20d185a` (`generacion figura 5 completa con CVA6`)

## Commands used

```bash
git log --oneline --decorate -n 12 -- SHARCBRIDGE_CVA6/cva6_runtime_launcher.py CVA6_LINUX/cva6-sdk buildroot
git diff --name-status 7c61d44 20d185a -- SHARCBRIDGE_CVA6 CVA6_LINUX/cva6-sdk
git diff --stat 7c61d44 20d185a -- SHARCBRIDGE_CVA6 CVA6_LINUX/cva6-sdk
git status --short
```

## Tracked changes in the commit range

Changed files:

- `A SHARCBRIDGE_CVA6/PLAN_FIGURE5_CVA6.md`
- `M SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp`
- `M SHARCBRIDGE_CVA6/cva6_controller_wrapper.py`
- `M SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- `M SHARCBRIDGE_CVA6/cva6_tcp_server.py`
- `A SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`

Diffstat:

- `SHARCBRIDGE_CVA6/PLAN_FIGURE5_CVA6.md | 478 ++++++++++++++++++++++++++++`
- `SHARCBRIDGE_CVA6/cva6_acc_runtime.cpp | 37 +++`
- `SHARCBRIDGE_CVA6/cva6_controller_wrapper.py | 28 ++`
- `SHARCBRIDGE_CVA6/cva6_runtime_launcher.py | 183 ++++++++++-`
- `SHARCBRIDGE_CVA6/cva6_tcp_server.py | 97 +++---`
- `SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh | 224 +++++++++++++`

## Important negative result

Within this commit range, `git diff` did not report tracked changes under:

- `CVA6_LINUX/cva6-sdk`

This matters because the current failure symptom is guest-content-related
(runtime/config missing inside the booted guest). That symptom is therefore more
consistent with local/generated SDK state drift than with a tracked repo change
inside `cva6-sdk`.

## Current worktree drift

The worktree is dirty today. Relevant entries include:

- `M SHARCBRIDGE_CVA6/cva6_runtime_launcher.py`
- `M SHARCBRIDGE_CVA6/cva6_tcp_server.py`
- `M SHARCBRIDGE_CVA6/run_cva6_figure5_tcp.sh`
- `m CVA6_LINUX/cva6-sdk`
- `m CVA6_LINUX/cva6`
- `m PULP/gvsoc`
- `?? artifacts_cva6/figure5_recovery/`

This means the definitive comparison should treat:

- tracked commit history
- local dirty state
- generated build outputs

as three separate sources of drift.

## Interpretation

- The key tracked evolution from `7c61d44` to `20d185a` is concentrated in
  `SHARCBRIDGE_CVA6`, especially:
  - persistent runtime launcher behavior
  - tcp server orchestration
  - dedicated Figure 5 execution script
- The absence of tracked `cva6-sdk` changes in the same commit span strengthens
  the current hypothesis that the failure is in the build/output layer or in the
  selected payload/rootfs combination, not in a committed SDK code delta.

## Test / Gate

- Commit range resolved cleanly: PASS
- File-level drift list generated: PASS
- Current dirty worktree captured for context: PASS

## Exit criterion

We now have a bounded tracked-diff set to compare against the good March runs,
without yet modifying the main Figure 5 flow.
