import io
import importlib.util
import json
from pathlib import Path


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def test_pipe_controller_read_vector_parses_csv():
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod',
    )
    pc = wrapper.PipeController()
    reader = io.StringIO('[1.0, 2.5, -3]\n')
    assert pc.read_vector(reader, 'x') == [1.0, 2.5, -3.0]


def test_pipe_controller_end_of_pipe_raises_eoferror():
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod2',
    )
    pc = wrapper.PipeController()
    reader = io.StringIO('END OF PIPE\n')
    try:
        pc.read_int(reader, 'k')
        raised = False
    except EOFError:
        raised = True
    assert raised


def test_pipe_controller_write_vector_format():
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod3',
    )
    pc = wrapper.PipeController()
    writer = io.StringIO()
    pc.write_vector(writer, [1.0, 2.345678, -0.5], 'u')
    out = writer.getvalue().strip()
    assert out.startswith('[') and out.endswith(']')
    values = [float(x.strip()) for x in out[1:-1].split(',')]
    assert values == [1.0, 2.345678, -0.5]


def test_pipe_controller_write_vector_precision_is_high():
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod4',
    )
    pc = wrapper.PipeController()
    writer = io.StringIO()
    ref = [0.1234567890123, -9876.543210987, 1e-9]
    pc.write_vector(writer, ref, 'u')
    out = writer.getvalue().strip()
    values = [float(x.strip()) for x in out[1:-1].split(',')]
    max_err = max(abs(a - b) for a, b in zip(ref, values))
    # Transport formatting should keep sub-1e-8 absolute error on representative values.
    assert max_err < 1e-8


def test_append_dynamics_trace_writes_jsonl(tmp_path):
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod_trace',
    )
    trace = tmp_path / 'trace.ndjson'
    wrapper.append_dynamics_trace(
        str(trace),
        {"iteration": 3, "k": 3, "t": 0.3, "x": [1.0, 2.0], "w": [3.0], "u_prev": [0.0, 100.0]},
    )
    lines = trace.read_text().strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["k"] == 3
    assert record["x"] == [1.0, 2.0]
    assert record["w"] == [3.0]


def test_scale_cycles_for_delay_matches_cycle_ratio():
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod_scale',
    )
    assert wrapper.scale_cycles_for_delay(1000, cycle_ns=2.5, base_cycle_ns=1.25) == 2000
    assert wrapper.scale_cycles_for_delay(1000, cycle_ns=0.625, base_cycle_ns=1.25) == 500


def test_run_gvsoc_mpc_parses_stdout(monkeypatch):
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'srv_mod')

    monkeypatch.setattr(srv, 'patch_elf_with_params', lambda *args, **kwargs: '/tmp/fake.elf')

    class FakeResult:
        returncode = 0
        stdout = 'MPC_START\nU=12.5,34.0\nCOST=1.23e+04\nITER=42\nCYCLES=123456\nSTATUS=OPTIMAL\nMPC_DONE\n'
        stderr = ''

    monkeypatch.setattr(srv.subprocess, 'run', lambda *args, **kwargs: FakeResult())

    res = srv.run_gvsoc_mpc(0, 0.0, [0.0, 60.0, 15.0], [11.0, 1.0], [0.0, 100.0])
    assert res['u'] == [12.5, 34.0]
    assert res['iterations'] == 42
    assert res['cycles'] == 123456
    assert res['status'] == 'OPTIMAL'


def test_run_gvsoc_mpc_marks_no_start(monkeypatch):
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'srv_mod2')

    monkeypatch.setattr(srv, 'patch_elf_with_params', lambda *args, **kwargs: '/tmp/fake.elf')

    class FakeResult:
        returncode = 0
        stdout = 'U=0.0,0.0\nCOST=0\nITER=1\nCYCLES=10\nSTATUS=OPTIMAL\n'
        stderr = ''

    monkeypatch.setattr(srv.subprocess, 'run', lambda *args, **kwargs: FakeResult())

    res = srv.run_gvsoc_mpc(1, 0.2, [0.0, 60.0, 15.0], [11.0, 1.0], [0.0, 100.0])
    assert res['status'] == 'NO_START'


def test_run_gvsoc_mpc_parses_scientific_and_signed_numbers(monkeypatch):
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'srv_mod3')

    monkeypatch.setattr(srv, 'patch_elf_with_params', lambda *args, **kwargs: '/tmp/fake.elf')

    class FakeResult:
        returncode = 0
        stdout = (
            'MPC_START\n'
            'U=-1.25e+01,3.40E+01\n'
            'COST=-1.23e+04\n'
            'ITER=42\n'
            'CYCLES=123456\n'
            'STATUS=OPTIMAL\n'
            'MPC_DONE\n'
        )
        stderr = ''

    monkeypatch.setattr(srv.subprocess, 'run', lambda *args, **kwargs: FakeResult())

    res = srv.run_gvsoc_mpc(2, 0.4, [0.0, 60.0, 15.0], [11.0, 1.0], [0.0, 100.0])
    assert res['u'] == [-12.5, 34.0]
    assert res['cost'] == -12300.0
    assert res['iterations'] == 42
    assert res['cycles'] == 123456
    assert res['status'] == 'OPTIMAL'
