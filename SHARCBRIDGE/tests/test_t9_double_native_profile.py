import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_t9_double_native_gvsoc_core_defaults(monkeypatch):
    monkeypatch.setenv("SHARC_DOUBLE_NATIVE", "1")
    monkeypatch.delenv("PULP_SDK_CONFIG", raising=False)
    monkeypatch.delenv("GVSOC_TARGET", raising=False)
    core = _load_module("SHARCBRIDGE/scripts/gvsoc_core.py", "t9_core_double_mod")
    assert core.DOUBLE_NATIVE is True
    assert core.PULP_SDK_CONFIG == "pulp-open-double.sh"
    assert core.GVSOC_TARGET == "pulp-open"


def test_t9_toolchain_prefix_override(monkeypatch):
    monkeypatch.setenv("RISCV_TOOLCHAIN_PREFIX", "/tmp/custom-riscv")
    core = _load_module("SHARCBRIDGE/scripts/gvsoc_core.py", "t9_core_toolchain_override")
    assert str(core.TOOLCHAIN_DIR) == "/tmp/custom-riscv/bin"
    assert str(core.GCC) == "/tmp/custom-riscv/bin/riscv32-unknown-elf-gcc"


def test_t9_double_native_configs_present():
    core_cfg = Path("PULP/pulp-sdk/tools/gap-configs/configs/ips/riscv/ri5ky_v2_fpu_ilp32d.json")
    chip_cfg = Path("PULP/pulp-sdk/tools/gap-configs/configs/chips/pulp/pulp_double.json")
    target_cfg = Path("PULP/pulp-sdk/tools/gapy/targets/pulp_double.json")
    sdk_cfg = Path("PULP/pulp-sdk/configs/pulp-open-double.sh")
    build_script = Path("SHARCBRIDGE/scripts/build_mpc_profile.sh")

    for path in (core_cfg, chip_cfg, target_cfg, sdk_cfg, build_script):
        assert path.exists(), f"missing {path}"

    core_data = json.loads(core_cfg.read_text(encoding="utf-8"))
    assert "imfdc" in core_data["march"].lower()
    assert any("ilp32d" in arg for arg in core_data.get("compiler_args", []))

    chip_data = json.loads(chip_cfg.read_text(encoding="utf-8"))
    assert chip_data["soc"]["fc"]["core"] == "ri5ky_v2_fpu_ilp32d"
    assert chip_data["cluster"]["core"] == "ri5ky_v2_fpu_ilp32d"
    assert Path("SHARCBRIDGE/scripts/run_gvsoc_config_double.sh").exists()


def test_t9_double_native_toolchain_probe_true(monkeypatch, tmp_path):
    core = _load_module("SHARCBRIDGE/scripts/gvsoc_core.py", "t9_core_probe_true")
    fake_gcc = tmp_path / "riscv32-unknown-elf-gcc"
    fake_gcc.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_gcc.chmod(0o755)
    monkeypatch.setattr(core, "GCC", fake_gcc)
    monkeypatch.setattr(
        core.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=".;x/ilp32d;@mabi=ilp32d\n"),
    )
    assert core.toolchain_supports_ilp32d() is True


def test_t9_double_native_toolchain_probe_false(monkeypatch, tmp_path):
    core = _load_module("SHARCBRIDGE/scripts/gvsoc_core.py", "t9_core_probe_false")
    fake_gcc = tmp_path / "riscv32-unknown-elf-gcc"
    fake_gcc.write_text("#!/bin/sh\n", encoding="utf-8")
    fake_gcc.chmod(0o755)
    monkeypatch.setattr(core, "GCC", fake_gcc)
    monkeypatch.setattr(
        core.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout=".;x/ilp32;@mabi=ilp32\n"),
    )
    assert core.toolchain_supports_ilp32d() is False


def test_t9_gvsoc_core_nonzero_exit_returns_error(monkeypatch):
    core = _load_module("SHARCBRIDGE/scripts/gvsoc_core.py", "t9_core_nonzero_exit")
    monkeypatch.setattr(core, "patch_elf_with_params", lambda *args, **kwargs: "/tmp/fake.elf")
    monkeypatch.setattr(core, "_bump_spawn_count", lambda: 1)
    monkeypatch.setattr(core, "get_runtime_metrics_snapshot", lambda: {"gvsoc_spawn_count": 1, "elf_patch_count": 1})
    monkeypatch.setattr(
        core.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="Input error: Invalid target"),
    )

    out = core.run_gvsoc_mpc(0, 0.0, [0.0, 60.0, 15.0], [11.0, 1.0], [0.0, 100.0])
    assert out["status"] == "ERROR"
    assert "Invalid target" in out.get("error", "")
