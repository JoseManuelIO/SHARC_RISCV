# Estado T4-T6

- T4: `PASS`
  - builder reproducible: `SHARCBRIDGE_CVA6/cva6_image_builder.sh`
  - log: `artifacts_cva6/t4_image_build.log`
  - manifest: `artifacts_cva6/t4_rootfs_manifest.txt`
- T5: `PASS`
  - runner corto: `SHARCBRIDGE_CVA6/run_cva6_config.sh`
  - JSON: `artifacts_cva6/t5_e2e_short.json`
  - log: `artifacts_cva6/t5_e2e_short.log`
- T6: `PASS`
  - run real con SHARC: `SHARCBRIDGE_CVA6/run_cva6_e2e.sh`
  - log: `artifacts_cva6/t6_sharc_short.log`
  - plot: `artifacts_cva6/t6_sharc_short_plots.png`
  - experiment_result: `artifacts_cva6/t6_experiment_result.json`
  - simulation_data_incremental: `artifacts_cva6/t6_simulation_data_incremental.json`
