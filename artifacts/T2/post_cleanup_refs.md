# Post-Cleanup References (T2.1)

- Generated: `2026-02-23T10:01:46.186668`
- Excluded path: `sharc_original/examples/acc_example/_obsolete/*`
- Total mentions: `21`
- Blocking mentions: `0`

## Mentions
- [expected] `.gitignore:68:_obsolete_root/`
- [expected] `.gitignore:69:riscv_bridge/`
- [expected] `PLAN_MAESTRO_SHARC_GVSOC.md:47:- Acción: inventariar `SHARCBRIDGE`, `riscv_bridge`, `_obsolete_root`, scripts y configs.`
- [expected] `PLAN_MAESTRO_SHARC_GVSOC.md:59:- Acción: preparar lista final de candidatos obsoletos (incluye `riscv_bridge/` y `_obsolete_root/` si aplican).`
- [expected] `PLAN_MAESTRO_SHARC_GVSOC.md:215:- Acción: evaluar y portar/reutilizar máximo código original (incluye `riscv_bridge` útil).`
- [expected] `artifacts/T1/deletion_plan.md:4:- Remove `_obsolete_root/` and `riscv_bridge/`.`
- [expected] `artifacts/T2/post_cleanup_refs.md:8:- [expected] `PLAN_MAESTRO_SHARC_GVSOC.md:47:- Acción: inventariar `SHARCBRIDGE`, `riscv_bridge`, `_obsolete_root`, scripts y configs.``
- [expected] `artifacts/T2/post_cleanup_refs.md:9:- [expected] `PLAN_MAESTRO_SHARC_GVSOC.md:59:- Acción: preparar lista final de candidatos obsoletos (incluye `riscv_bridge/` y `_obsolete_root/` si aplican).``
- [expected] `artifacts/T2/post_cleanup_refs.md:10:- [expected] `PLAN_MAESTRO_SHARC_GVSOC.md:215:- Acción: evaluar y portar/reutilizar máximo código original (incluye `riscv_bridge` útil).``
- [expected] `artifacts/T2/post_cleanup_refs.md:11:- [expected] `.gitignore:68:_obsolete_root/``
- [expected] `artifacts/T2/post_cleanup_refs.md:12:- [expected] `.gitignore:69:riscv_bridge/``
- [expected] `artifacts/T2/post_cleanup_refs.md:13:- [expected] `artifacts/T1/deletion_plan.md:4:- Remove `_obsolete_root/` and `riscv_bridge/`.``
- [expected] `artifacts/T2/post_cleanup_refs.md:14:- [blocking] `SHARCBRIDGE/mpc/run_gvsoc.sh:17:APP_DIR="$HOME/Repositorios/SHARC_RISCV/riscv_bridge/applications/mpc_acc"``
- [expected] `artifacts/T2/post_cleanup_refs.md:15:- [blocking] `sharc_original/examples/acc_example/_obsolete/test_wrapper_integration.sh:13:    echo "   Ejecuta primero: cd ~/Repositorios/SHARC_RISCV/riscv_bridge/scripts && python3 gvsoc_tcp_server.py &"``
- [expected] `artifacts/T2/post_cleanup_refs.md:16:- [blocking] `sharc_original/examples/acc_example/_obsolete/gvsoc_controller_wrapper.py:245:        print(f"Start the server with: riscv_bridge/scripts/gvsoc_tcp_server.py", file=sys.stderr)``
- [expected] `artifacts/T2/post_cleanup_refs.md:17:- [blocking] `sharc_original/examples/acc_example/_obsolete/GVSOC_INTEGRATION.md:7:riscv_bridge/applications/mpc_acc/mpc_acc_controller.c``
- [expected] `artifacts/T2/post_cleanup_refs.md:18:- [blocking] `sharc_original/examples/acc_example/_obsolete/GVSOC_INTEGRATION.md:76:   cd riscv_bridge``
- [expected] `artifacts/T2/post_cleanup_refs.md:19:- [blocking] `sharc_original/examples/acc_example/_obsolete/GVSOC_INTEGRATION.md:78:   # Produce: riscv_bridge/applications/mpc_acc/mpc_acc.elf``
- [expected] `artifacts/T2/post_cleanup_refs.md:20:- [blocking] `sharc_original/examples/acc_example/_obsolete/GVSOC_INTEGRATION.md:118:MPC_ELF = os.path.expanduser("~/Repositorios/SHARC_RISCV/riscv_bridge/applications/mpc_acc/mpc_acc.elf")``
- [expected] `artifacts/T2/post_cleanup_refs.md:21:- [blocking] `sharc_original/examples/acc_example/_obsolete/GVSOC_INTEGRATION.md:163:gvsoc --target pulp-open --binary riscv_bridge/applications/mpc_acc/mpc_acc.elf run``
- [expected] `artifacts/T2/post_cleanup_refs.md:22:- [blocking] `sharc_original/examples/acc_example/_obsolete/GVSOC_INTEGRATION.md:202:riscv_bridge/applications/mpc_acc/``

## Verdict
- PASS: no blocking references to removed paths.