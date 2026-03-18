from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "SHARCBRIDGE" / "scripts" / "verify_final_official.sh"


def test_t10_script_exists_and_executable():
    assert SCRIPT_PATH.exists(), f"Missing script: {SCRIPT_PATH}"
    assert SCRIPT_PATH.stat().st_mode & 0o111, "Script should be executable"


def test_t10_script_contract_contains_all_gates():
    text = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "verify_official_pipeline.sh" in text
    assert "check_official_repeatability.sh" in text
    assert "t3_formulation_parity_gate.py" in text
    assert "t8_fidelity_gate.py" in text
    assert "T3_formulation_parity_gate_latest.json" in text
    assert "T8_fidelity_thresholds_v1.json" in text


def test_t10_script_shell_syntax_ok():
    import subprocess

    result = subprocess.run(
        ["bash", "-n", str(SCRIPT_PATH)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
