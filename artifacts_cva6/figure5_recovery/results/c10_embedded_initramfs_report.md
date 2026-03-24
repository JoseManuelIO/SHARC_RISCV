# C10 Embedded Initramfs Report

## Status

`PASS`

## Goal

Extract the initramfs embedded inside the historical bootable reference kernel
and compare it directly against the currently regenerated `rootfs.cpio`.

## Method

Extraction script:

- `artifacts_cva6/figure5_recovery/scripts/c10_extract_embedded_initramfs.py`

Extraction source:

- `install64/vmlinux`

Recovered from symbol/section analysis:

- embedded gzip blob offset: `0x4ad628`
- size field offset: `0xac39c0`
- embedded initramfs size: `6382484`

## Extraction result

Recovered historical embedded initramfs:

- `artifacts_cva6/figure5_recovery/results/c10_embedded_initramfs/good_embedded_initramfs.cpio`
- sha256: `2a689e1053129e1d5c9e14160d309d3b335d79c1d98f334e5b8d7762eee8f081`

Current regenerated rootfs used for comparison:

- `CVA6_LINUX/cva6-sdk/buildroot/output/images/rootfs.cpio`
- sha256: `c0eb9ac6bcc5ea7c8b054361bcbb885c7e8b77cf73fa5c2dd3fbd99b5a26746b`

## Critical finding

The historical embedded initramfs from the bootable reference kernel contains:

- `lib/ld-linux-riscv64-lp64d.so.1`

But it does **not** contain:

- `usr/bin/sharc_cva6_acc_runtime`
- `usr/share/sharcbridge_cva6/base_config.json`

The current regenerated rootfs does contain all three:

- `lib/ld-linux-riscv64-lp64d.so.1`
- `usr/bin/sharc_cva6_acc_runtime`
- `usr/share/sharcbridge_cva6/base_config.json`

## Consequence

This invalidates a key earlier assumption:

- the bootable historical reference guest was **already** missing runtime/config

So the mere fact that the live guest lacks:

- `/usr/bin/sharc_cva6_acc_runtime`
- `/usr/share/sharcbridge_cva6/base_config.json`

cannot by itself explain the Figure 5 regression.

## Listing delta

The current regenerated rootfs has extra content absent from the historical
embedded initramfs, including:

- `usr/bin/sharc_cva6_acc_runtime`
- multiple `plan_*` binaries
- `usr/lib/libstdc++.so*`
- `usr/share/sharcbridge_cva6/base_config.json`
- `usr/share/plan_tests_librerias/...`

The historical embedded initramfs instead looks much leaner and only shows:

- `usr/bin/plan_hello_smoke`

as the only `plan_*` binary in that area.

## Interpretation

There are now only two plausible explanations:

1. the historical successful Figure 5 flow used a payload different from the
   current restored bootable reference kernel, or
2. the historical successful flow injected/staged the runtime by a path that is
   not reflected in committed `20d185a` launcher code

The second option is weakened by comparison with commit `20d185a`:

- `cva6_runtime_launcher.py` in `20d185a` does **not** implement runtime staging
- it directly calls `/usr/bin/sharc_cva6_acc_runtime /usr/share/sharcbridge_cva6/base_config.json`

Therefore the strongest current inference is:

- the restored bootable reference triplet (`#6 SMP Tue Mar 17 11:54:00 CET 2026`)
  is **not** the exact payload triplet that backed the successful Figure 5 runs
  from March 18

## New diagnosis

The real recovery target is no longer:

- "make the restored bootable reference guest contain runtime/config"

It is:

- identify or reconstruct the actual March 18 Figure 5 payload triplet that
  matched the committed `20d185a` launcher contract

## Test / Gate

- embedded initramfs extracted from historical kernel: PASS
- historical embedded listing produced: PASS
- direct listing comparison vs current rootfs produced: PASS
- earlier "runtime missing in guest" hypothesis re-evaluated with stronger evidence: PASS

## Exit criterion

This task is complete because it changes the recovery search space in a
meaningful and evidence-backed way: the restored bootable reference kernel is
not sufficient evidence of the actual successful Figure 5 guest state.
