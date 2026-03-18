import importlib.util
from pathlib import Path


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_t3_compare_payloads_zero_diff():
    gate = _load_module("SHARCBRIDGE/scripts/t3_formulation_parity_gate.py", "t3_gate_mod_1")
    payload = {
        "n": 2,
        "m": 2,
        "P_colptr": [0, 1, 3],
        "P_rowind": [0, 0, 1],
        "P_data": [1.0, 0.1, 1.2],
        "q": [0.0, -1.0],
        "A_colptr": [0, 1, 2],
        "A_rowind": [0, 1],
        "A_data": [1.0, 1.0],
        "l": [0.0, 0.0],
        "u": [2.0, 3.0],
    }
    cmp_out = gate.compare_payloads(payload, dict(payload))
    assert cmp_out["int_equal"]
    assert cmp_out["max_abs_overall"] == 0.0


def test_t3_static_contract_current_files_pass():
    gate = _load_module("SHARCBRIDGE/scripts/t3_formulation_parity_gate.py", "t3_gate_mod_2")
    ok, issues = gate.check_official_static_contract(
        Path("SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py"),
        Path("SHARCBRIDGE/scripts/gvsoc_tcp_server.py"),
    )
    assert ok, issues

