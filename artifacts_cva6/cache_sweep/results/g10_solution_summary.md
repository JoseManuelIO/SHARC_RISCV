# G10 Solution Summary

- date: `2026-03-27`
- status: `SOLUTION_FOUND`

## Problem

`Figure 5` and the cache campaign became fragile after reboot because the flow no longer used one coherent SDK identity.

The volatile SDK in `/tmp` disappeared, and the runtime path fell back to a mixed setup:

- host assets from `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk`
- boot payload from `/home/jminiesta/Repositorios/SHARC_RISCV/install64`

Later, rebuilding `cva6-sdk/install64/` produced a new `#37` triplet that was coherent on disk but unstable at boot time.

## Root Cause

The real blocker was the boot triplet, not the guest contents.

Evidence:

- rebuilt triplet in `cva6-sdk/install64/` failed warmup boot
- restored bootable `#6` triplet passed warmup
- exact `Figure 5` `k=0` snapshot passed with the restored triplet
- full `Figure 5` passed end-to-end with the restored triplet in place

## Practical Fix

Use a single SDK root:

- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk`

and ensure that root contains the preserved bootable triplet:

- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/spike_fw_payload.elf`
- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/vmlinux`
- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/install64/Image`

with hashes:

- `spike_fw_payload.elf`: `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`
- `vmlinux`: `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
- `Image`: `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`

Runtime/config/libs remain inside:

- `/home/jminiesta/Repositorios/SHARC_RISCV/CVA6_LINUX/cva6-sdk/buildroot/output/target/`

## What This Solves

- warmup probe: `PASS`
- exact `Figure 5` `k=0`: `PASS`
- full `Figure 5`: `PASS`

Reference run:

- `/tmp/sharc_cva6_figure5/2026-03-27--10-57-30-cva6_figure5/latest/plots.png`

## What Not To Do

Do not treat the newly rebuilt `#37` triplet as the mainline boot image.

At the current repo state it is not reproducibly stable enough for `spike_persistent`.

## Next Safe Step

Resume the cache experiments from this restored-triplet baseline, without rebuilding `install64/` again unless a new bootable triplet is explicitly validated first.
