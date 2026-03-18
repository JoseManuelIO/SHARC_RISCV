# T6 Late Snapshot Replay Report

- status: `PASS`
- status codes:
  - `-2 = OSQP_MAX_ITER_REACHED`
  - `2 = OSQP_SOLVED_INACCURATE`
- max |u| diff CVA6 integrated replay: `4.958110366715118e-09`

## Compared snapshots

- `late_17`
  - statuses: `host=-2`, `cva6=-2`, `integrated=-2`
  - iterations: `host=5000`, `cva6=5000`, `integrated=5000`
  - match: `PASS`

- `late_18`
  - statuses: `host=2`, `cva6=2`, `integrated=2`
  - iterations: `host=5000`, `cva6=5000`, `integrated=5000`
  - match: `PASS`

- `late_19`
  - statuses: `host=2`, `cva6=2`, `integrated=2`
  - iterations: `host=5000`, `cva6=5000`, `integrated=5000`
  - match: `PASS`
