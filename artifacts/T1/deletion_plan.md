# Deletion Plan (T1.3)

## Decision
- Remove `_obsolete_root/` and `riscv_bridge/`.

## Why
- They are legacy bridge trees superseded by `SHARCBRIDGE/`.
- No active references found in current active code scan (`dependency_matrix.md` PASS).

## Impact Check
- Expected impact on official flow: none.
- Official flow paths remain under:
  - `SHARCBRIDGE/`
  - `sharc_original/`
  - `PULP/`

## Test Gate for Deletion
- Re-run reference scan for obsolete paths after deletion.
- Run smoke/integration baseline command after deletion.

## Approval Context
- User explicitly approved removal if paths are obsolete.
