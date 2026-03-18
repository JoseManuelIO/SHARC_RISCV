# T3 Formulation Parity Gate

- pass: `True`
- tol: `1e-12`
- samples: `256`

## Parity
- pass: `True`
- max_abs_overall: `0.0`

| field | max_abs_diff |
|---|---:|
| P_data | 0.000000000000e+00 |
| q | 0.000000000000e+00 |
| A_data | 0.000000000000e+00 |
| l | 0.000000000000e+00 |
| u | 0.000000000000e+00 |

## Log Evidence
- pass: `True`
- count: `20`
- pattern: `qp_solve payload backend=c_abi fields=P,q,A,l,u`

## Wrapper Diagnostic (non-blocking)
- max_abs_overall_vs_c_abi: `3.814697265625e-06`

## Official Static Contract
- pass: `True`
