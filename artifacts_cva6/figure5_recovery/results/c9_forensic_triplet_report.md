# C9 Forensic Triplet Report

## Status

`PASS`

## Goal

Compare the historical bootable reference triplet against a freshly regenerated
triplet from the current sources, and separate byte-level facts from assumptions.

## Method

Controlled comparison wrapper:

- `artifacts_cva6/figure5_recovery/scripts/c9_forensic_triplet_compare.sh`

What it did:

1. copied the current bootable reference triplet from `install64/`
2. captured metadata for that reference triplet
3. rebuilt a fresh current triplet with `cva6_image_builder.sh`
4. copied the regenerated triplet into artifacts
5. captured `sha256`, `stat`, `file`, `readelf` metadata for both triplets
6. restored the bootable reference triplet back into:
   - `install64/`
   - `CVA6_LINUX/cva6-sdk/install64/`

## Byte-level comparison: bootable reference vs regenerated current

Reference triplet:

- `vmlinux`: `fd770e7f592532a4fa8bafc469df9c740f5ec4ab375747243f414940cac14d8a`
- `Image`: `fd27ffa1d3554252e9dfa5d2de3c9eb3f05979c74c5e905f2d8935ae46b26e4a`
- `spike_fw_payload.elf`: `6510db2d5b159f662f0ef4905357390e84033a5e2206fa2c1d02aa535e6584ea`

Regenerated current triplet:

- `vmlinux`: `29421cea4aa8c452d3d4a8a693c668190ff89b0b299c83020f20a345e3473369`
- `Image`: `b49562c6482400c1b5db2c7a29b093680343ede73a2497129397cf0895c2b5f4`
- `spike_fw_payload.elf`: `f1e403d9d2c3095bebe85c49e17218ec79e77457c61e0ffa3cf57bf86d7776ee`

Result:

- all three files differ byte-for-byte

## Structural differences

### `vmlinux`

The strongest direct difference is in `vmlinux`:

- size changed:
  - good: `15636784`
  - regenerated: `16791856`
- `BuildID` changed:
  - good: `94a8643a0f61ae72a30682b6c680ab6281db8d0e`
  - regenerated: `9821dc5f76f646ae908f8bff42f33c6ed41f51a8`
- embedded kernel version string changed:
  - good: `Linux version 5.10.7 ... #6 SMP Tue Mar 17 11:54:00 CET 2026`
  - regenerated: `Linux version 5.10.7 ... #34 SMP Tue Mar 24 12:40:38 CET 2026`

This proves the regenerated payload is not just a repackaging of the same
kernel. It is a different kernel build artifact.

### `Image`

- same file type and same size (`19592192`)
- different hash

Interpretation:

- `Image` is being rebuilt from a different `vmlinux`, so it changes even though
  its outer file shape stays the same

### `spike_fw_payload.elf`

- same file type and same size (`20555528`)
- different hash
- embedded kernel version string also changed from `#6 SMP Tue Mar 17...` to
  `#34 SMP Tue Mar 24...`

Interpretation:

- the OpenSBI payload is also not the historical one; it is packaging the newer
  regenerated kernel

## Rootfs comparison limits

There is no recoverable physical copy of the original historical-good
`rootfs.cpio` in the workspace or `/tmp`.

What we do have:

- historical rootfs hash evidence from earlier manifests:
  - `f31c19b61a80db3c8fd383b7159ea15313386798cec78337f6a514ca908340fa`
  - `c62462a7d4809d4327878aedc3fa7a9fd1f6129701678f9cbc7fb0af61ce1f15`
  - `b2909bd8113fa045ab3a9db0a99372d68172190c691424ef496b96299580c15d`
- freshly regenerated rootfs copied during `C9`:
  - `c0eb9ac6bcc5ea7c8b054361bcbb885c7e8b77cf73fa5c2dd3fbd99b5a26746b`

And the regenerated rootfs still contains:

- `lib/ld-linux-riscv64-lp64d.so.1`
- `usr/bin/sharc_cva6_acc_runtime`
- `usr/share/sharcbridge_cva6/base_config.json`

So the rootfs-side symptom remains the same:

- packaged rootfs contains runtime/config
- the historical bootable guest path did too
- but fresh current rebuilds still fail to reproduce the historical bootable triplet

## Additional search result

Searches did not find any other physical historical copies of the Figure 5
triplet under `/tmp` or `artifacts_cva6`, except:

- the restored reference triplet in `install64/`
- the backup copy in `artifacts_cva6/figure5_recovery/results/c8_backup_before_reinstall/`

No historical-good `rootfs.cpio` copy was found, only hash evidence in previous
manifests.

## Final interpretation

This comparison gives the missing definitive answer:

- the working March payload triplet is not reproducible from the current local
  source/build state
- the most meaningful divergence is not just `rootfs.cpio`; it is the kernel and
  therefore the final `Image` and `spike_fw_payload.elf`
- the real comparison target to recover now is the historical kernel build state
  associated with:
  - `vmlinux` hash `fd770e7f...`
  - `Image` hash `fd27ffa1...`
  - `spike_fw_payload.elf` hash `6510db2d...`

## Practical next step

The next productive recovery action is:

1. identify where that historical `#6 SMP Tue Mar 17 11:54:00 CET 2026` kernel
   came from, or
2. recover the exact build inputs/config that generated that kernel

Not:

- another rebuild from today's sources

## Safety check

After `C9`, the bootable reference triplet was restored successfully and now
matches again in both places:

- `install64/`
- `CVA6_LINUX/cva6-sdk/install64/`

with hashes:

- `fd770e7f...`
- `fd27ffa1...`
- `6510db2d...`
