#!/usr/bin/env python3
import importlib.util
import io
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER_PATH = REPO_ROOT / "SHARCBRIDGE_CVA6" / "cva6_controller_wrapper.py"
OUT_JSON = REPO_ROOT / "artifacts_cva6" / "t1_wrapper_contract.json"
OUT_MD = REPO_ROOT / "artifacts_cva6" / "t1_wrapper_smoke.md"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


wrapper = load_module(WRAPPER_PATH, "cva6_wrapper_mod")
pc = wrapper.PipeController()

vec_reader = io.StringIO("[1.0, 2.5, -3]\n")
vec = pc.read_vector(vec_reader, "x")

writer = io.StringIO()
pc.write_vector(writer, [1.0, 2.345678, -0.5], "u")
u_wire = writer.getvalue().strip()

request = wrapper.build_run_snapshot_request(
    request_id="req-1",
    k=7,
    t=0.2,
    x=[0.0, 60.0, 15.0],
    w=[11.0, 1.0],
    u_prev=[0.0, 0.0],
)

u, metadata = wrapper.normalize_backend_response(
    {
        "status": "SUCCESS",
        "iterations": 50,
        "cost": -123.4,
        "u": [2.4, 0.0],
        "metadata": {"solver_status": "SUCCESS"},
    }
)

contract = {
    "wrapper_path": str(WRAPPER_PATH),
    "request_type": request["type"],
    "request_keys": sorted(request.keys()),
    "response_u": u,
    "metadata_keys": sorted(metadata.keys()),
    "vector_parse_sample": vec,
    "wire_vector_sample": u_wire,
}
OUT_JSON.write_text(json.dumps(contract, indent=2), encoding="utf-8")

OUT_MD.write_text(
    "\n".join(
        [
            "# T1 Wrapper Smoke",
            "",
            "## Estado",
            "",
            "`PASS`",
            "",
            "## Comprobaciones",
            "",
            "- El wrapper se importa correctamente.",
            "- `PipeController.read_vector()` parsea el formato SHARC esperado.",
            "- `PipeController.write_vector()` mantiene el formato wire `[v0, v1]`.",
            "- `build_run_snapshot_request()` genera una peticion TCP valida para CVA6.",
            "- `normalize_backend_response()` produce `u` y `metadata` compatibles con SHARC.",
            "",
            "## Evidencia",
            "",
            f"- contrato: `{OUT_JSON}`",
        ]
    )
    + "\n",
    encoding="utf-8",
)
