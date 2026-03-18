from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "SHARCBRIDGE" / "scripts" / "run_gvsoc_figure5_tcp.sh"


def test_t9_tcp_1_script_contract_exists_and_is_executable():
    assert SCRIPT_PATH.exists(), f"Missing script: {SCRIPT_PATH}"
    assert SCRIPT_PATH.stat().st_mode & 0o111, "Script should be executable"


def test_t9_tcp_1_script_contract_transport_selection():
    text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "gvsoc_tcp_server.py" in text
    assert "gvsoc_flask_server.py" not in text
    assert "GVSOC_TRANSPORT=tcp" in text
    assert "probe_tcp_server" in text
    assert 'SHARC_DOUBLE_NATIVE="${SHARC_DOUBLE_NATIVE:-1}"' in text
    assert "build_qp_runtime_profile.sh" in text
    assert "build_mpc_profile.sh" in text
    assert 'GVSOC_QP_SOLVE="${GVSOC_QP_SOLVE:-}"' in text
    assert "SHARC_OFFICIAL_RISCV_MODE=1 requires GVSOC_QP_SOLVE=1" in text
    assert "curl -sf" not in text, "TCP script should not depend on HTTP health checks"


def test_t9_tcp_1_script_contract_shell_syntax_ok():
    import subprocess

    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
