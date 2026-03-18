from pathlib import Path
import subprocess


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "SHARCBRIDGE" / "scripts" / "run_gvsoc_config.sh"


def test_t14_config_tcp_1_script_exists_and_is_executable():
    assert SCRIPT_PATH.exists(), f"Missing script: {SCRIPT_PATH}"
    assert SCRIPT_PATH.stat().st_mode & 0o111, "Script should be executable"


def test_t14_config_tcp_2_script_uses_tcp_official_path():
    text = SCRIPT_PATH.read_text(encoding="utf-8")

    assert "gvsoc_tcp_server.py" in text
    assert "gvsoc_flask_server.py" not in text
    assert "GVSOC_TRANSPORT=tcp" in text
    assert "probe_tcp_server" in text
    assert 'SHARC_DOUBLE_NATIVE="${SHARC_DOUBLE_NATIVE:-1}"' in text


def test_t14_config_tcp_3_script_shell_syntax_ok():
    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
