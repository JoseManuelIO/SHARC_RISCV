import io
import importlib.util
import json
import os


def _load_module(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def _sample_qp_payload():
    return {
        "n": 2,
        "m": 2,
        "P_colptr": [0, 1, 2],
        "P_rowind": [0, 1],
        "P_data": [1.0, 1.0],
        "q": [0.0, 0.0],
        "A_colptr": [0, 1, 2],
        "A_rowind": [0, 1],
        "A_data": [1.0, 1.0],
        "l": [0.0, 0.0],
        "u": [1.0, 1.0],
    }


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


def test_wrapper_official_config_accepts_tcp_qp_mode(monkeypatch):
    monkeypatch.setenv("SHARC_OFFICIAL_RISCV_MODE", "1")
    monkeypatch.setenv("GVSOC_TRANSPORT", "tcp")
    monkeypatch.setenv("GVSOC_QP_SOLVE", "1")
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod_official_ok',
    )
    wrapper.validate_official_runtime_config()


def test_wrapper_official_config_requires_qp_solve(monkeypatch):
    monkeypatch.setenv("SHARC_OFFICIAL_RISCV_MODE", "1")
    monkeypatch.setenv("GVSOC_TRANSPORT", "tcp")
    monkeypatch.setenv("GVSOC_QP_SOLVE", "0")
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod_official_requires_qp',
    )
    try:
        wrapper.validate_official_runtime_config()
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "requires GVSOC_QP_SOLVE=1" in str(exc)
    assert raised


def test_wrapper_official_config_requires_tcp_transport(monkeypatch):
    monkeypatch.setenv("SHARC_OFFICIAL_RISCV_MODE", "1")
    monkeypatch.setenv("GVSOC_TRANSPORT", "http")
    monkeypatch.setenv("GVSOC_QP_SOLVE", "1")
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod_official_requires_tcp',
    )
    try:
        wrapper.validate_official_runtime_config()
        raised = False
    except RuntimeError as exc:
        raised = True
        assert "requires GVSOC_TRANSPORT=tcp" in str(exc)
    assert raised


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


def test_build_acc_qp_payload_has_valid_structure():
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod_qp',
    )
    qp = _load_module('SHARCBRIDGE/scripts/qp_payload.py', 'qp_payload_mod_wrapper')

    payload = wrapper.build_acc_qp_payload(
        [0.0, 60.0, 15.0],
        [11.0, 1.0],
        [0.0, 100.0],
    )
    ok, err = qp.validate_qp_payload(payload)
    assert ok, err
    assert payload["n"] == 2
    assert payload["m"] == 2


def test_apply_legacy_post_qp_guards_enforces_safety_floor():
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod_guards_1',
    )
    x = [52.30453001520002, 51.385377261978675, 14.131333152280108]
    w = [9.371071084369659, 1.0]
    u_qp = [10.0, 200.0]

    u = wrapper.apply_legacy_post_qp_guards(x, w, u_qp)
    assert u[0] == 0.0
    assert u[1] > u_qp[1]
    assert u[1] <= wrapper.F_BRAKE_MAX


def test_apply_legacy_post_qp_guards_applies_brake_cap_when_safe():
    wrapper = _load_module(
        'SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py',
        'wrapper_mod_guards_2',
    )
    x = [0.0, 20.0, 5.0]
    w = [10.0, 1.0]
    u_qp = [0.0, 2400.0]

    u = wrapper.apply_legacy_post_qp_guards(x, w, u_qp)
    assert u[0] == 0.0
    assert u[1] < u_qp[1]
    assert u[1] >= wrapper.MPC_BRAKE_CAP_MIN


def test_run_gvsoc_mpc_parses_stdout(monkeypatch):
    core = _load_module('SHARCBRIDGE/scripts/gvsoc_core.py', 'core_mod')

    monkeypatch.setattr(core, 'patch_elf_with_params', lambda *args, **kwargs: '/tmp/fake.elf')

    class FakeResult:
        returncode = 0
        stdout = 'MPC_START\nU=12.5,34.0\nCOST=1.23e+04\nITER=42\nCYCLES=123456\nSTATUS=OPTIMAL\nMPC_DONE\n'
        stderr = ''

    monkeypatch.setattr(core.subprocess, 'run', lambda *args, **kwargs: FakeResult())

    res = core.run_gvsoc_mpc(0, 0.0, [0.0, 60.0, 15.0], [11.0, 1.0], [0.0, 100.0])
    assert res['u'] == [12.5, 34.0]
    assert res['iterations'] == 42
    assert res['cycles'] == 123456
    assert res['status'] == 'OPTIMAL'


def test_run_gvsoc_mpc_marks_no_start(monkeypatch):
    core = _load_module('SHARCBRIDGE/scripts/gvsoc_core.py', 'core_mod2')

    monkeypatch.setattr(core, 'patch_elf_with_params', lambda *args, **kwargs: '/tmp/fake.elf')

    class FakeResult:
        returncode = 0
        stdout = 'U=0.0,0.0\nCOST=0\nITER=1\nCYCLES=10\nSTATUS=OPTIMAL\n'
        stderr = ''

    monkeypatch.setattr(core.subprocess, 'run', lambda *args, **kwargs: FakeResult())

    res = core.run_gvsoc_mpc(1, 0.2, [0.0, 60.0, 15.0], [11.0, 1.0], [0.0, 100.0])
    assert res['status'] == 'NO_START'


def test_run_gvsoc_mpc_parses_scientific_and_signed_numbers(monkeypatch):
    core = _load_module('SHARCBRIDGE/scripts/gvsoc_core.py', 'core_mod3')

    monkeypatch.setattr(core, 'patch_elf_with_params', lambda *args, **kwargs: '/tmp/fake.elf')

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

    monkeypatch.setattr(core.subprocess, 'run', lambda *args, **kwargs: FakeResult())

    res = core.run_gvsoc_mpc(2, 0.4, [0.0, 60.0, 15.0], [11.0, 1.0], [0.0, 100.0])
    assert res['u'] == [-12.5, 34.0]
    assert res['cost'] == -12300.0
    assert res['iterations'] == 42
    assert res['cycles'] == 123456
    assert res['status'] == 'OPTIMAL'


def test_tcp_server_delegates_to_core_functions():
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_mod')
    assert srv.run_gvsoc_mpc.__module__ == 'gvsoc_core'
    assert srv.validate_environment.__module__ == 'gvsoc_core'


def test_flask_server_delegates_to_core_functions():
    flask_srv = _load_module('SHARCBRIDGE/scripts/gvsoc_flask_server.py', 'flask_srv_mod')
    assert flask_srv.run_gvsoc_mpc.__module__ == 'gvsoc_core'
    assert flask_srv.validate_environment.__module__ == 'gvsoc_core'


def test_tcp_handle_client_roundtrip_compute(monkeypatch):
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_roundtrip_mod')

    class FakeConn:
        def __init__(self, payloads):
            self._payloads = list(payloads)
            self.sent = []
            self.closed = False

        def recv(self, _size):
            if self._payloads:
                return self._payloads.pop(0)
            return b''

        def sendall(self, data):
            self.sent.append(data)

        def close(self):
            self.closed = True

    expected = {
        'k': 7,
        'u': [1.0, 2.0],
        'cost': 3.0,
        'status': 'OPTIMAL',
        'iterations': 4,
        'cycles': 5,
        't_delay': 0.01,
    }
    monkeypatch.setattr(srv, 'run_gvsoc_mpc', lambda *args, **kwargs: expected)

    req = b'{"type":"compute_mpc","k":7,"t":0.2,"x":[0,1,2],"w":[3,4]}\n'
    conn = FakeConn([req, b''])
    srv.handle_client(conn, ('127.0.0.1', 9999))

    assert conn.closed
    assert len(conn.sent) == 1
    response = json.loads(conn.sent[0].decode('utf-8').strip())
    assert response == expected


def test_flask_compute_endpoint_returns_core_payload(monkeypatch):
    flask_srv = _load_module('SHARCBRIDGE/scripts/gvsoc_flask_server.py', 'flask_srv_endpoint_mod')

    expected = {
        'k': 2,
        'u': [10.0, 20.0],
        'cost': 5.5,
        'status': 'OPTIMAL',
        'iterations': 6,
        'cycles': 7,
        't_delay': 0.02,
    }
    monkeypatch.setattr(flask_srv, 'run_gvsoc_mpc', lambda *args, **kwargs: expected)

    client = flask_srv.app.test_client()
    resp = client.post(
        '/mpc/compute',
        json={'k': 2, 't': 0.4, 'x': [1.0, 2.0, 3.0], 'w': [4.0, 5.0], 'u_prev': [0.0, 100.0]},
    )

    assert resp.status_code == 200
    assert resp.get_json() == expected


def test_gvsoc_core_reads_runtime_target_config_from_env(monkeypatch):
    monkeypatch.setenv('PULP_SDK_CONFIG', 'pulp-open-rnnext.sh')
    monkeypatch.setenv('GVSOC_TARGET', 'siracusa')
    monkeypatch.setenv('GVSOC_PLATFORM', 'rtl')
    monkeypatch.setenv('GVSOC_RUN_TIMEOUT_S', '17')

    core = _load_module('SHARCBRIDGE/scripts/gvsoc_core.py', 'core_env_cfg_mod')

    assert core.PULP_SDK_CONFIG == 'pulp-open-rnnext.sh'
    assert core.GVSOC_TARGET == 'siracusa'
    assert core.GVSOC_PLATFORM == 'rtl'
    assert core.GVSOC_RUN_TIMEOUT_S == 17
    assert str(core.PULP_SDK_SOURCEME).endswith(
        '/PULP/pulp-sdk/configs/pulp-open-rnnext.sh'
    )


def test_run_gvsoc_mpc_uses_target_platform_and_timeout_from_env(monkeypatch):
    monkeypatch.setenv('PULP_SDK_CONFIG', 'siracusa.sh')
    monkeypatch.setenv('GVSOC_TARGET', 'siracusa')
    monkeypatch.setenv('GVSOC_PLATFORM', 'rtl')
    monkeypatch.setenv('GVSOC_RUN_TIMEOUT_S', '33')

    core = _load_module('SHARCBRIDGE/scripts/gvsoc_core.py', 'core_env_cmd_mod')
    monkeypatch.setattr(core, 'patch_elf_with_params', lambda *args, **kwargs: '/tmp/fake.elf')

    seen = {}

    class FakeResult:
        returncode = 0
        stdout = 'MPC_START\nU=1.0,2.0\nCOST=3\nITER=4\nCYCLES=5\nSTATUS=OPTIMAL\nMPC_DONE\n'
        stderr = ''

    def fake_run(*args, **kwargs):
        if args and isinstance(args[0], list) and len(args[0]) >= 3 and args[0][0] == 'bash' and args[0][1] == '-c':
            seen['cmd'] = args[0][2]
        return FakeResult()

    monkeypatch.setattr(core.subprocess, 'run', fake_run)

    res = core.run_gvsoc_mpc(0, 0.0, [0.0, 60.0, 15.0], [11.0, 1.0], [0.0, 100.0])

    cmd = seen.get('cmd', '')
    assert f"source {os.path.expanduser('~/Repositorios/SHARC_RISCV/PULP/pulp-sdk/configs/siracusa.sh')}" in cmd
    assert '--target=siracusa' in cmd
    assert '--platform=rtl' in cmd
    assert 'timeout 33 ' in cmd
    assert res['status'] == 'OPTIMAL'


def test_run_gvsoc_qp_parses_stdout(monkeypatch):
    core = _load_module('SHARCBRIDGE/scripts/gvsoc_core.py', 'core_qp_mod')
    payload = _sample_qp_payload()

    monkeypatch.setattr(core, 'patch_qp_elf_with_payload', lambda *args, **kwargs: '/tmp/fake_qp.elf')

    class FakeResult:
        returncode = 0
        stdout = (
            'QP_START\n'
            'N=2\n'
            'M=2\n'
            'X=1.25,-2.5e-01\n'
            'COST=3.40E+01\n'
            'ITER=12\n'
            'PRIMAL_RES=1.0e-05\n'
            'DUAL_RES=2.0e-05\n'
            'CYCLES=9876\n'
            'STATUS=OPTIMAL\n'
            'QP_DONE\n'
        )
        stderr = ''

    monkeypatch.setattr(core.subprocess, 'run', lambda *args, **kwargs: FakeResult())

    out = core.run_gvsoc_qp(payload, settings={"max_iter": 50})
    assert out["status"] == "OPTIMAL"
    assert out["x"] == [1.25, -0.25]
    assert out["cost"] == 34.0
    assert out["iterations"] == 12
    assert out["converged"] == 1
    assert out["cycles"] == 9876
    assert out["n"] == 2
    assert out["m"] == 2


def test_qp_persistent_wait_done_advances_with_run_steps(monkeypatch):
    core = _load_module('SHARCBRIDGE/scripts/gvsoc_core.py', 'core_qp_persistent_wait_mod')
    session = core.QPPersistentSession(worker_id=0)

    class _Proc:
        def poll(self):
            return None

    session._process = _Proc()
    steps = {"count": 0}
    states = iter(
        [
            {"done_flag": 0},
            {"done_flag": 0},
            {"done_flag": 1, "status": "OPTIMAL", "x": [0.1, 0.2], "cost": 1.0, "iterations": 3, "converged": 1, "cycles": 10, "primal_residual": 0.0, "dual_residual": 0.0, "n": 2, "m": 2},
        ]
    )

    def fake_run_step():
        steps["count"] += 1

    def fake_read_state(**_kwargs):
        return next(states)

    monkeypatch.setattr(session, "_run_step", fake_run_step)
    monkeypatch.setattr(session, "_read_state", fake_read_state)

    state = session._wait_done(fallback_n=2, fallback_m=2, timeout_s=0.1)
    assert state["done_flag"] == 1
    assert state["status"] == "OPTIMAL"
    assert steps["count"] == 3


def test_qp_persistent_run_step_uses_async_window_and_stop(monkeypatch):
    monkeypatch.setenv("GVSOC_QP_PERSISTENT_STEP_TIMEOUT_S", "0.5")
    monkeypatch.setenv("GVSOC_QP_PERSISTENT_RUN_WINDOW_S", "0.002")
    core = _load_module('SHARCBRIDGE/scripts/gvsoc_core.py', 'core_qp_persistent_step_mod')
    session = core.QPPersistentSession(worker_id=0)

    class _Proxy:
        def run(self):
            return None

        def stop(self):
            return None

    session._proxy = _Proxy()
    calls = []
    sleeps = []

    def fake_proxy_call(fn, *args, op_name: str, timeout_s=None):
        calls.append((fn.__name__, args, op_name, timeout_s))
        return None

    monkeypatch.setattr(session, "_proxy_call", fake_proxy_call)
    monkeypatch.setattr(core.time, "sleep", lambda v: sleeps.append(v))
    session._run_step()

    assert len(calls) == 2
    assert calls[0][2] == "run_async"
    assert calls[0][1] == ()
    assert calls[1][2] == "stop_after_run"
    assert calls[1][1] == ()
    assert float(calls[0][3]) == 0.5
    assert float(calls[1][3]) == 0.5
    assert sleeps == [0.002]


def test_qp_solve_handler_uses_riscv_backend_even_in_official_mode(monkeypatch):
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_qp_handler_mod')

    monkeypatch.setattr(srv, "OFFICIAL_RISCV_MODE", True)

    seen = {}

    def fake_build_payload(x, u_prev, w, backend="c_abi", allow_fallback=False):
        seen["build_x"] = x
        seen["build_u_prev"] = u_prev
        seen["build_w"] = w
        seen["build_backend"] = backend
        seen["build_allow_fallback"] = allow_fallback
        return _sample_qp_payload(), "c_abi"

    def fake_run_gvsoc_qp(got_payload, settings=None):
        seen["payload"] = got_payload
        seen["settings"] = settings
        return {
            "status": "OPTIMAL",
            "x": [0.1, 0.2],
            "cost": 1.23,
            "iterations": 7,
            "converged": 1,
            "primal_residual": 1e-4,
            "dual_residual": 2e-4,
            "n": 2,
            "m": 2,
        }

    monkeypatch.setattr(srv, "build_acc_qp_payload_host", fake_build_payload)
    monkeypatch.setattr(srv, "run_gvsoc_qp", fake_run_gvsoc_qp)

    out = srv._handle_qp_solve_request(
        {
            "type": "qp_solve",
            "x": [0.0, 60.0, 15.0],
            "w": [11.0, 1.0],
            "u_prev": [0.0, 100.0],
            "settings": {"max_iter": 80, "tol": 1e-5},
        }
    )

    assert seen["build_x"] == [0.0, 60.0, 15.0]
    assert seen["build_w"] == [11.0, 1.0]
    assert seen["build_u_prev"] == [0.0, 100.0]
    assert seen["build_backend"] == "c_abi"
    assert seen["build_allow_fallback"] is False
    assert seen["payload"] == _sample_qp_payload()
    assert seen["settings"] == {"max_iter": 80, "tol": 1e-5}
    assert out["status"] == "OPTIMAL"
    assert out["x"] == [0.1, 0.2]
    assert out["iterations"] == 7
    assert out["n"] == 2
    assert out["m"] == 2


def test_tcp_handle_client_roundtrip_qp_solve(monkeypatch):
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_qp_roundtrip_mod')
    payload = _sample_qp_payload()

    class FakeConn:
        def __init__(self, payloads):
            self._payloads = list(payloads)
            self.sent = []
            self.closed = False

        def recv(self, _size):
            if self._payloads:
                return self._payloads.pop(0)
            return b''

        def sendall(self, data):
            self.sent.append(data)

        def close(self):
            self.closed = True

    monkeypatch.setattr(
        srv,
        "run_gvsoc_qp",
        lambda *args, **kwargs: {
            "status": "OPTIMAL",
            "x": [0.0, 0.5],
            "cost": 2.0,
            "iterations": 9,
            "converged": 1,
            "primal_residual": 0.0,
            "dual_residual": 0.0,
            "n": 2,
            "m": 2,
        },
    )

    req = {
        "type": "qp_solve",
        "request_id": "qp-1",
        "qp_payload": payload,
        "settings": {"max_iter": 100},
    }
    conn = FakeConn([(json.dumps(req) + "\n").encode("utf-8"), b""])
    srv.handle_client(conn, ("127.0.0.1", 8888))

    assert conn.closed
    assert len(conn.sent) == 1
    response = json.loads(conn.sent[0].decode("utf-8").strip())
    assert response["request_id"] == "qp-1"
    assert response["status"] == "OPTIMAL"
    assert response["x"] == [0.0, 0.5]
    assert response["iterations"] == 9


def test_tcp_protocol_qp_solve_accepts_host_vectors():
    proto = _load_module('SHARCBRIDGE/scripts/tcp_protocol.py', 'tcp_protocol_qp_vectors_mod')
    request = {
        "type": "qp_solve",
        "x": [0.0, 60.0, 15.0],
        "w": [11.0, 1.0],
        "u_prev": [0.0, 100.0],
        "settings": {"max_iter": 60, "tol": 1e-3},
    }
    result = proto.validate_request(request)
    assert result.ok, result.error


def test_tcp_protocol_qp_solve_rejects_invalid_u_prev():
    proto = _load_module('SHARCBRIDGE/scripts/tcp_protocol.py', 'tcp_protocol_qp_invalid_uprev_mod')
    request = {
        "type": "qp_solve",
        "x": [0.0, 60.0, 15.0],
        "w": [11.0, 1.0],
        "u_prev": [0.0],
    }
    result = proto.validate_request(request)
    assert not result.ok
    assert "u_prev must be [2 numbers]" in result.error


def test_decode_qp_request_payload_builds_from_host_vectors(monkeypatch):
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_decode_host_qp_mod')
    payload = _sample_qp_payload()
    seen = {}

    def fake_build_payload(x, u_prev, w, backend="c_abi", allow_fallback=False):
        seen["x"] = x
        seen["u_prev"] = u_prev
        seen["w"] = w
        seen["backend"] = backend
        seen["allow_fallback"] = allow_fallback
        return payload, "c_abi"

    monkeypatch.setattr(srv, "build_acc_qp_payload_host", fake_build_payload)

    request = {
        "type": "qp_solve",
        "x": [1.0, 2.0, 3.0],
        "w": [4.0, 1.0],
        "u_prev": [5.0, 6.0],
    }
    out_payload, err = srv._decode_qp_request_payload(request)
    assert err == ""
    assert out_payload == payload
    assert request.get("_qp_payload_backend") == "c_abi"
    assert seen["x"] == [1.0, 2.0, 3.0]
    assert seen["w"] == [4.0, 1.0]
    assert seen["u_prev"] == [5.0, 6.0]
    assert seen["backend"] == "c_abi"
    assert seen["allow_fallback"] is False


def test_decode_qp_request_payload_rejects_qp_payload_in_official_mode(monkeypatch):
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_official_payload_reject_mod')
    monkeypatch.setattr(srv, "OFFICIAL_RISCV_MODE", True)
    payload = _sample_qp_payload()

    out_payload, err = srv._decode_qp_request_payload({"type": "qp_solve", "qp_payload": payload})
    assert out_payload is None
    assert "qp_payload is not allowed in SHARC_OFFICIAL_RISCV_MODE" in err


def test_decode_qp_request_payload_rejects_qp_blob_in_official_mode(monkeypatch):
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_official_blob_reject_mod')
    monkeypatch.setattr(srv, "OFFICIAL_RISCV_MODE", True)

    out_payload, err = srv._decode_qp_request_payload({"type": "qp_solve", "qp_blob_hex": "00aa"})
    assert out_payload is None
    assert "qp_blob_hex is not allowed in SHARC_OFFICIAL_RISCV_MODE" in err


def test_qp_dispatch_uses_persistent_pool():
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_qp_pool_mod')
    payload = _sample_qp_payload()

    srv.configure_qp_runtime_pool(
        1,
        compute_fn_factory=lambda _wid: (
            lambda got_payload, settings=None: {
                "status": "OPTIMAL",
                "x": [0.2, 0.3],
                "cost": 9.9,
                "iterations": int((settings or {}).get("max_iter", 0)),
                "converged": 1,
                "primal_residual": 0.0,
                "dual_residual": 0.0,
                "n": got_payload["n"],
                "m": got_payload["m"],
            }
        ),
    )

    out = srv._compute_qp_dispatch(payload, settings={"max_iter": 77})
    assert out["status"] == "OPTIMAL"
    assert out["x"] == [0.2, 0.3]
    assert out["iterations"] == 77
    assert out["n"] == 2
    assert out["m"] == 2


def test_set_exec_mode_persistent_exposes_qp_runtime():
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_exec_mode_qp_runtime_mod')
    state = srv.set_exec_mode("persistent", persistent_workers=1)
    assert state["exec_mode"] == "persistent"
    assert state["runtime"] is not None
    assert state["qp_runtime"] is not None
    assert state["runtime"]["num_workers"] == 1
    assert state["qp_runtime"]["num_workers"] == 1
    assert state["metrics"]["qp_worker_spawn_count"] == 1


def test_qp_compute_factory_uses_proxy_backend(monkeypatch):
    monkeypatch.setenv("GVSOC_QP_PERSISTENT_BACKEND", "proxy")
    monkeypatch.setenv("GVSOC_QP_PERSISTENT_EXPERIMENTAL", "1")
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_qp_proxy_factory_mod')

    marker = {"called": False}

    def fake_builder(worker_id):
        marker["called"] = True
        marker["worker_id"] = worker_id
        return lambda payload, settings=None: {"status": "OPTIMAL", "x": [0.0, 0.0], "cost": 0.0, "iterations": 0, "converged": 1, "cycles": 0, "t_delay": 0.0, "primal_residual": 0.0, "dual_residual": 0.0, "n": 2, "m": 2}

    monkeypatch.setattr(srv, "build_qp_persistent_compute_fn", fake_builder)
    factory = srv._qp_compute_factory()
    _ = factory(3)
    assert marker["called"] is True
    assert marker["worker_id"] == 3


def test_qp_compute_factory_proxy_defaults_to_legacy(monkeypatch):
    monkeypatch.setenv("GVSOC_QP_PERSISTENT_BACKEND", "proxy")
    monkeypatch.delenv("GVSOC_QP_PERSISTENT_EXPERIMENTAL", raising=False)
    srv = _load_module('SHARCBRIDGE/scripts/gvsoc_tcp_server.py', 'tcp_srv_qp_proxy_default_legacy_mod')
    factory = srv._qp_compute_factory()
    fn = factory(0)
    assert fn == srv.run_gvsoc_qp


def test_generic_persistent_runtime_pool_close_calls_compute_close():
    rt = _load_module('SHARCBRIDGE/scripts/gvsoc_persistent_runtime.py', 'persistent_runtime_close_mod')
    state = {"closed": 0}

    def make_compute(_wid):
        def _compute(payload, settings=None):
            return {"status": "OPTIMAL"}
        def _close():
            state["closed"] += 1
        setattr(_compute, "_close", _close)
        return _compute

    pool = rt.GenericPersistentRuntimePool(num_workers=2, compute_fn_factory=make_compute)
    pool.close()
    assert state["closed"] == 2
