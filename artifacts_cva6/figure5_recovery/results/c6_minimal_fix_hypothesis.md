# C6 Minimal Fix Hypothesis

## Status

`PASS`

## Winning hypothesis

The primary regression is not in MPC logic, TCP orchestration, or late boot.
The primary regression is that the guest image currently being booted does not
contain the SHARC runtime payload expected by the good Figure 5 flow.

More precisely:

- the packaged `rootfs.cpio` currently contains:
  - `usr/bin/sharc_cva6_acc_runtime`
  - `usr/share/sharcbridge_cva6/base_config.json`
  - `lib/ld-linux-riscv64-lp64d.so.1`
- the booted guest currently exposes only:
  - `lib/ld-linux-riscv64-lp64d.so.1`
- the good baseline evidence shows the guest really did execute:
  - `/usr/bin/sharc_cva6_acc_runtime /usr/share/sharcbridge_cva6/base_config.json ...`

Therefore the fix target is:

- recover the guest assembly state used by the good persistent runs

not:

- further tuning the main Figure 5 flow blindly

## Minimal repair strategy

1. Keep the current comparison evidence as source of truth.
2. Do not modify the main flow except to validate the recovered guest content.
3. Restore the guest by reproducing the good packaging path first:
   - verify overlay/rootfs inputs
   - verify `buildroot/output/target/usr/bin/sharc_cva6_acc_runtime`
   - verify `buildroot/output/target/usr/share/sharcbridge_cva6/base_config.json`
   - rebuild `rootfs.cpio`
   - rebuild/export `vmlinux`, `Image`, `spike_fw_payload.elf`
4. Before rerunning full Figure 5, run a single guest presence test:
   - guest must report both runtime and config as present
5. Only then rerun `spike_persistent` smoke and finally Figure 5.

## Minimal test ladder

- Gate 1:
  - `cpio -it < rootfs.cpio` contains runtime/config/loader
- Gate 2:
  - live guest presence probe reports runtime/config/loader all present
- Gate 3:
  - one persistent smoke run executes `sharc_cva6_acc_runtime` successfully
- Gate 4:
  - full `run_cva6_figure5_tcp.sh` in `spike_persistent` regenerates Figure 5 outputs

## What should be avoided

- continuing with fragile side-load as the main solution
- broad edits to `SHARCBRIDGE_CVA6` before guest content is restored
- assuming `rootfs.cpio` presence alone proves the booted guest is correct

## Recommended next task

Execute a controlled guest rebuild/reinstall comparison task in artifacts:

- capture the exact rootfs overlay inputs
- rebuild guest artifacts in isolation
- rerun only the guest presence probe

If that still boots a guest without runtime/config, the next step is a clean
`cva6-sdk` reinstall rather than more launcher patching.
