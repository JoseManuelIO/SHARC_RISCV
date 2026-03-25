# Spike Cache Miss Log Summary

- log: `/tmp/sharcbridge_cva6_runtime/r6-runtime-probe.log`
- spike_cache_args: `--ic=4:4:64 --dc=4:4:64 --l2=128:4:64 --log-cache-miss`
- total_miss_events: `222598`

| cache | op | miss_count | unique_addr_count | block_bytes | estimated_linefill_bytes |
|---|---|---:|---:|---:|---:|
| D$ | read | 8551 | 1994 | 64 | 547264 |
| D$ | write | 145883 | 143927 | 64 | 9336512 |
| I$ | read | 68164 | 1752 | 64 | 4362496 |

## Notes

- This parser uses actual `Spike --log-cache-miss` event lines such as `I$ read miss ...`.
- This local Spike build does not emit aggregate `Read Accesses` / `Miss Rate` summaries in the observed logs.
- `estimated_linefill_bytes` is a simple `miss_count * block_bytes` estimate and should be treated as a cache-line traffic proxy.
