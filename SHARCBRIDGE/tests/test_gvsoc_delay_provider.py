from pathlib import Path


def test_gvsoc_delay_provider_class_exists_in_sharc_source():
    src = Path('sharc_original/resources/sharc/__init__.py').read_text()
    assert 'class GVSoCDelayProvider' in src


def test_gvsoc_delay_formula_present_in_source():
    src = Path('sharc_original/resources/sharc/__init__.py').read_text()
    # Guard that conversion remains cycles -> seconds via chip_cycle_time_s
    assert 't_delay = cycles * self.chip_cycle_time_s' in src


def test_gvsoc_delay_provider_supports_env_override_for_cycle_time():
    src = Path('sharc_original/resources/sharc/__init__.py').read_text()
    assert 'GVSOC_CHIP_CYCLE_NS' in src
