# Scenario Catalog (T5.1)

- Generated: `2026-02-23T10:05:25.762738`

- Total config files: `16`

## `default.json`
- Experiments: `1`
- Labels: `['Default Settings']`
- n_time_steps: `['-']`
- Delay providers: `['-']`

## `example_configs.json`
- Experiments: `1`
- Labels: `['<no-label>']`
- n_time_steps: `['-']`
- Delay providers: `['-']`

## `fake_delays.json`
- Experiments: `2`
- Labels: `['Parallel', 'Serial']`
- n_time_steps: `[40, 40]`
- Delay providers: `['onestep', 'execution-driven scarab']`

## `gvsoc_figure5.json`
- Experiments: `2`
- Labels: `['GVSoC - Real Delays', 'Baseline - No Delay (Onestep)']`
- n_time_steps: `[40, 40]`
- Delay providers: `['gvsoc', 'onestep']`

## `gvsoc_test.json`
- Experiments: `1`
- Labels: `['GVSoC Serial']`
- n_time_steps: `[20]`
- Delay providers: `['gvsoc']`

## `gvsoc_timing_analysis.json`
- Experiments: `4`
- Labels: `['GVSoC Serial - Real Delays', 'GVSoC Serial - Horizon 10', 'GVSoC Serial - Horizon 15', 'Baseline - Onestep Delays']`
- n_time_steps: `[40, 40, 40, 40]`
- Delay providers: `['gvsoc', 'gvsoc', 'gvsoc', 'onestep']`

## `parallel.json`
- Experiments: `3`
- Labels: `['Parallel - Fake Delays', 'Parallel - Scarab Delays - Short Computations', 'Parallel Scarab - Long Computations']`
- n_time_steps: `[8, 8, 32]`
- Delay providers: `['onestep', 'onestep', 'onestep']`

## `parallel_vs_serial.json`
- Experiments: `4`
- Labels: `['Parallel Fake', 'Serial Fake', 'Parallel Scarab', 'Serial Scarab']`
- n_time_steps: `[64, 64, 64, 64]`
- Delay providers: `['onestep', 'execution-driven scarab', 'onestep', 'execution-driven scarab']`

## `prediction_horizon.json`
- Experiments: `4`
- Labels: `['2', '5', '10', '15']`
- n_time_steps: `['-', '-', '-', '-']`
- Delay providers: `['-', '-', '-', '-']`

## `serial.json`
- Experiments: `2`
- Labels: `['Serial Without Scarab', 'Serial With Scarab']`
- n_time_steps: `[32, 32]`
- Delay providers: `['execution-driven scarab', 'execution-driven scarab']`

## `simulation_modes_tests.json`
- Experiments: `5`
- Labels: `['No external dynamics', 'External non-scarab dynamics', 'Update immediately when computation done', 'Serial Scarab', 'Parallel Scarab']`
- n_time_steps: `['-', '-', '-', 1, 8]`
- Delay providers: `['-', '-', '-', '-', '-']`

## `smoke_test.json`
- Experiments: `4`
- Labels: `['Parallel Fake', 'Serial Fake', 'Parallel Scarab', 'Serial Scarab']`
- n_time_steps: `[16, 8, 2, 2]`
- Delay providers: `['onestep', 'execution-driven scarab', 'onestep', 'execution-driven scarab']`

## `test_consistency_SLOW.json`
- Experiments: `8`
- Labels: `['Serial Without Scarab 1', 'Serial Without Scarab 2', 'Serial With Scarab 1', 'Serial With Scarab 2', 'Parallel Without Scarab 1', 'Parallel Without Scarab 2', 'Parallel With Scarab 1', 'Parallel With Scarab 2']`
- n_time_steps: `[4, 4, 4, 4, 4, 4, 4, 4]`
- Delay providers: `['execution-driven scarab', 'execution-driven scarab', 'execution-driven scarab', 'execution-driven scarab', 'onestep', 'onestep', 'onestep', 'onestep']`

## `test_consistency_serial_vs_parallel.json`
- Experiments: `2`
- Labels: `['Serial', 'Parallel']`
- n_time_steps: `[32, 32]`
- Delay providers: `['execution-driven scarab', 'onestep']`

## `test_serial_consistency_with_fake_delays.json`
- Experiments: `4`
- Labels: `['Serial Without Scarab 1', 'Serial Without Scarab 2', 'Serial Without Scarab 3', 'Serial Without Scarab 4']`
- n_time_steps: `[4, 4, 4, 4]`
- Delay providers: `['execution-driven scarab', 'execution-driven scarab', 'execution-driven scarab', 'execution-driven scarab']`

## `test_serial_vs_parallel_with_fake_delays.json`
- Experiments: `2`
- Labels: `['Serial', 'Parallel']`
- n_time_steps: `[4, 4]`
- Delay providers: `['execution-driven scarab', 'onestep']`
