import importlib.util
import json
from pathlib import Path


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _write_sim(path: Path, u_vals, x_vals):
    n = len(u_vals)
    data = {
        "k": list(range(n)),
        "t": [0.1 * i for i in range(n)],
        "u": u_vals,
        "x": x_vals,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


def test_t8_gate_passes_for_small_deltas(tmp_path):
    gate = _load_module("SHARCBRIDGE/scripts/t8_fidelity_gate.py", "t8_gate_mod_pass")

    ab_run = tmp_path / "ab_run"
    fg_run = tmp_path / "fg_run"

    ref_u = [[0.0, 100.0], [0.0, 120.0], [0.0, 140.0]]
    cand_u = [[0.2, 100.5], [0.1, 120.4], [0.0, 140.3]]
    ref_x = [[0.0, 50.0, 10.0], [1.0, 49.5, 10.1], [2.0, 49.0, 10.2]]
    cand_x = [[0.01, 50.01, 10.0], [1.02, 49.52, 10.09], [2.01, 48.99, 10.19]]

    _write_sim(
        ab_run / "a-original-onestep" / "simulation_data_incremental.json",
        ref_u,
        ref_x,
    )
    _write_sim(
        ab_run / "b-gvsoc-onestep" / "simulation_data_incremental.json",
        cand_u,
        cand_x,
    )
    _write_sim(
        fg_run / "baseline-no-delay-onestep" / "simulation_data_incremental.json",
        ref_u,
        ref_x,
    )
    _write_sim(
        fg_run / "gvsoc-real-delays" / "simulation_data_incremental.json",
        cand_u,
        cand_x,
    )

    thresholds = {
        "ab_onestep_compare": {
            "signals": {
                "u_accel": {"mae": 1.0, "rmse": 1.0},
                "u_brake": {"mae": 1.0, "rmse": 1.0},
                "x_p": {"mae": 0.1, "rmse": 0.1},
                "x_h": {"mae": 0.1, "rmse": 0.1},
                "x_v": {"mae": 0.1, "rmse": 0.1},
            }
        },
        "gvsoc_figure5": {
            "signals": {
                "u_accel": {"mae": 1.0, "rmse": 1.0},
                "u_brake": {"mae": 1.0, "rmse": 1.0},
                "x_p": {"mae": 0.1, "rmse": 0.1},
                "x_h": {"mae": 0.1, "rmse": 0.1},
                "x_v": {"mae": 0.1, "rmse": 0.1},
            }
        },
    }

    report = gate.run_gate(ab_run, fg_run, thresholds)
    assert report["pass"]
    assert report["ab_onestep_compare"]["pass"]
    assert report["gvsoc_figure5"]["pass"]


def test_t8_gate_fails_for_large_deltas(tmp_path):
    gate = _load_module("SHARCBRIDGE/scripts/t8_fidelity_gate.py", "t8_gate_mod_fail")

    ab_run = tmp_path / "ab_run"
    fg_run = tmp_path / "fg_run"

    ref_u = [[0.0, 100.0], [0.0, 120.0], [0.0, 140.0]]
    bad_u = [[10.0, 500.0], [10.0, 520.0], [10.0, 540.0]]
    ref_x = [[0.0, 50.0, 10.0], [1.0, 49.5, 10.1], [2.0, 49.0, 10.2]]
    bad_x = [[2.0, 55.0, 12.0], [3.0, 54.5, 12.1], [4.0, 54.0, 12.2]]

    _write_sim(
        ab_run / "a-original-onestep" / "simulation_data_incremental.json",
        ref_u,
        ref_x,
    )
    _write_sim(
        ab_run / "b-gvsoc-onestep" / "simulation_data_incremental.json",
        bad_u,
        bad_x,
    )
    _write_sim(
        fg_run / "baseline-no-delay-onestep" / "simulation_data_incremental.json",
        ref_u,
        ref_x,
    )
    _write_sim(
        fg_run / "gvsoc-real-delays" / "simulation_data_incremental.json",
        bad_u,
        bad_x,
    )

    thresholds = {
        "ab_onestep_compare": {
            "signals": {
                "u_accel": {"mae": 0.5},
                "u_brake": {"mae": 0.5},
            }
        },
        "gvsoc_figure5": {
            "signals": {
                "u_accel": {"mae": 0.5},
                "u_brake": {"mae": 0.5},
            }
        },
    }

    report = gate.run_gate(ab_run, fg_run, thresholds)
    assert not report["pass"]
    assert report["ab_onestep_compare"]["violations"]
    assert report["gvsoc_figure5"]["violations"]

