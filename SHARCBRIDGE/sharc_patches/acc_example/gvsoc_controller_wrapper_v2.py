#!/usr/bin/env python3
"""
GVSoC Controller Wrapper for SHARC (TCP Version) - FIXED
Implements the exact pipe protocol of main_controller.cpp to avoid deadlocks

This wrapper acts as the "controller executable" for SHARC, implementing
the same pipe interface as main_controller.cpp, but executes the actual
MPC computation in GVSoC via a TCP server running on the host.

Critical fixes:
- Opens pipes in the correct order (matches main_controller.cpp)
- Reads t_delay_py_to_c++ to avoid blocking SHARC
- Maintains open file descriptors (no open/close per iteration)
- Writes "END OF PIPE\n" before closing output pipes
"""

import os
import sys
import socket
import json
import time
import math
import ctypes

# Get simulation directory from command line argument
if len(sys.argv) > 1:
    SIMULATION_DIR = os.path.abspath(sys.argv[1])
else:
    SIMULATION_DIR = os.getcwd()

# Pipe paths (same as main_controller.cpp)
U_OUT = os.path.join(SIMULATION_DIR, 'u_c++_to_py')
METADATA_OUT = os.path.join(SIMULATION_DIR, 'metadata_c++_to_py')
STATUS_IN = os.path.join(SIMULATION_DIR, 'status_py_to_c++')
K_IN = os.path.join(SIMULATION_DIR, 'k_py_to_c++')
T_IN = os.path.join(SIMULATION_DIR, 't_py_to_c++')
X_IN = os.path.join(SIMULATION_DIR, 'x_py_to_c++')
W_IN = os.path.join(SIMULATION_DIR, 'w_py_to_c++')
T_DELAY_IN = os.path.join(SIMULATION_DIR, 't_delay_py_to_c++')
TRACE_FILE = os.path.join(SIMULATION_DIR, 'wrapper_dynamics_trace.ndjson')


# Transport settings
# GVSOC_TRANSPORT=tcp  → raw TCP (official/default path)
# GVSOC_TRANSPORT=http → Flask HTTP (legacy/optional path)
GVSOC_TRANSPORT = os.environ.get('GVSOC_TRANSPORT', 'tcp')
GVSOC_EXEC_MODE = os.environ.get('GVSOC_EXEC_MODE', 'legacy').strip().lower()
try:
    GVSOC_PERSISTENT_WORKERS = int(os.environ.get('GVSOC_PERSISTENT_WORKERS', '1'))
except ValueError:
    GVSOC_PERSISTENT_WORKERS = 1
GVSOC_HOST = os.environ.get('GVSOC_HOST', '127.0.0.1')
GVSOC_PORT = int(os.environ.get('GVSOC_PORT', '5000'))
try:
    GVSOC_SOCKET_TIMEOUT_S = float(os.environ.get('GVSOC_SOCKET_TIMEOUT_S', '60'))
except ValueError:
    GVSOC_SOCKET_TIMEOUT_S = 60.0
GVSOC_BASE_CYCLE_NS = 1.25
try:
    GVSOC_CYCLE_NS = float(os.environ.get('GVSOC_CHIP_CYCLE_NS', str(GVSOC_BASE_CYCLE_NS)))
except ValueError:
    GVSOC_CYCLE_NS = GVSOC_BASE_CYCLE_NS
GVSOC_QP_SOLVE = os.environ.get('GVSOC_QP_SOLVE', '0').strip().lower() in {'1', 'true', 'yes', 'on'}
OFFICIAL_RISCV_MODE = os.environ.get('SHARC_OFFICIAL_RISCV_MODE', '0').strip().lower() in {
    '1', 'true', 'yes', 'on'
}


# Lightweight ACC QP formulation constants (aligned with legacy host solver path).
MASS = 2044.0
BETA = 339.1329
GAMMA = 0.77
D_MIN = 6.0
V_DES = 15.0
F_ACCEL_MAX = 4880.0
F_BRAKE_MAX = 6507.0
SAMPLE_TIME = 0.2
MPC_W_DU_BRAKE = 1.0
MPC_W_HEADWAY = 80.0
V_MAX = 20.0
A_BRAKE_EGO = 3.2
A_BRAKE_FRONT = 5.0912
PREDICTION_HORIZON = 5
MPC_MARGIN_TRIGGER = -1.0
MPC_SAFETY_CLOSE_GAIN = 185.0
MPC_SAFETY_MARGIN_GAIN = 28.0
MPC_BRAKE_CAP_MARGIN_POS = 4.0
MPC_BRAKE_CAP_BASE = 900.0
MPC_BRAKE_CAP_SPEED_GAIN = 230.0
MPC_BRAKE_CAP_MARGIN_SLOPE = 18.0
MPC_BRAKE_CAP_MIN = 150.0
MPC_BRAKE_CAP_MAX = 2400.0
MPC_TRANSITION_GUARD_ENABLE = False
MPC_TRANSITION_H_MIN = 40.0
MPC_TRANSITION_H_MAX = 47.0
MPC_TRANSITION_VDIFF_MIN = 1.2
MPC_TRANSITION_BRAKE_K = 260.0
MPC_TRANSITION_BRAKE_B = 250.0


def _compute_friction(v):
    return _f32(BETA + _f32(GAMMA * _f32(v) * _f32(v)))


def _f32(v):
    """Match C float arithmetic used by legacy host solver."""
    return float(ctypes.c_float(float(v)).value)


def _predict_state(x, u, w, dt):
    v = float(x[2])
    a = (float(u[0]) - float(u[1]) - _compute_friction(v)) / MASS
    v_next = max(0.0, min(v + a * dt, V_MAX))
    return [
        float(x[0]) + v_next * dt,
        max(0.0, float(x[1]) + (float(w[0]) - v_next) * dt),
        v_next,
    ]


def _predict_terminal_margin(x0, u, w0):
    x = [float(x0[0]), float(x0[1]), float(x0[2])]
    vf_end = float(w0[0])
    for k in range(PREDICTION_HORIZON):
        vf_end = max(0.0, float(w0[0]) - float(k) * SAMPLE_TIME * A_BRAKE_FRONT)
        x = _predict_state(x, u, [vf_end, 1.0], SAMPLE_TIME)

    lhs = x[1] - x[2] * (V_MAX / (2.0 * A_BRAKE_EGO))
    rhs = D_MIN - (vf_end * vf_end) / (2.0 * A_BRAKE_FRONT)
    closing_end = x[2] - vf_end
    return lhs - rhs, closing_end


def apply_legacy_post_qp_guards(x, w, u):
    """Mirror legacy MPC guard-rail logic after QP solve."""
    u_out = [float(u[0]), float(u[1])]
    v = float(x[2])
    h = float(x[1])
    margin, closing_end = _predict_terminal_margin(x, u_out, w)

    if margin < MPC_MARGIN_TRIGGER and closing_end > 0.0:
        safety_floor = MPC_SAFETY_CLOSE_GAIN * closing_end + MPC_SAFETY_MARGIN_GAIN * (-margin)
        safety_floor = max(0.0, min(F_BRAKE_MAX, safety_floor))
        u_out[1] = max(u_out[1], safety_floor)
        u_out[0] = 0.0

    if (
        MPC_TRANSITION_GUARD_ENABLE
        and h > MPC_TRANSITION_H_MIN
        and h < MPC_TRANSITION_H_MAX
        and v > (float(w[0]) + MPC_TRANSITION_VDIFF_MIN)
    ):
        v_diff = v - float(w[0])
        transition_floor = MPC_TRANSITION_BRAKE_K * v_diff + MPC_TRANSITION_BRAKE_B
        transition_floor = max(0.0, min(F_BRAKE_MAX, transition_floor))
        u_out[1] = max(u_out[1], transition_floor)
        u_out[0] = 0.0

    if margin > MPC_BRAKE_CAP_MARGIN_POS and closing_end <= 0.0:
        brake_cap = (
            MPC_BRAKE_CAP_BASE
            + MPC_BRAKE_CAP_SPEED_GAIN * max(0.0, v - 8.0)
            - MPC_BRAKE_CAP_MARGIN_SLOPE * (margin - MPC_BRAKE_CAP_MARGIN_POS)
        )
        brake_cap = max(MPC_BRAKE_CAP_MIN, min(MPC_BRAKE_CAP_MAX, brake_cap))
        u_out[1] = min(u_out[1], brake_cap)

    # Enforce actuator bounds at the end.
    u_out[0] = max(0.0, min(F_ACCEL_MAX, u_out[0]))
    u_out[1] = max(0.0, min(F_BRAKE_MAX, u_out[1]))
    return u_out


def build_acc_qp_payload(x, w, u_prev):
    """Build reduced ACC QP payload in T2 CSC format."""
    v = _f32(x[2])
    h = _f32(x[1])
    w0 = _f32(w[0])
    up0 = _f32(u_prev[0])
    up1 = _f32(u_prev[1])
    wy = _f32(10000.0)
    wu = _f32(0.01)
    wdu_acc = _f32(1.0)
    wdu_br = _f32(MPC_W_DU_BRAKE)
    wh = _f32(MPC_W_HEADWAY)

    a = _f32(SAMPLE_TIME / MASS)
    c_v = _f32(v - _f32(a * _compute_friction(v)))
    gv0, gv1 = _f32(a), _f32(-a)
    ev = _f32(c_v - V_DES)

    c_h = _f32(h + _f32(SAMPLE_TIME * _f32(w0 - c_v)))
    gh0, gh1 = _f32(-_f32(SAMPLE_TIME * a)), _f32(_f32(SAMPLE_TIME * a))
    eh = _f32(c_h - D_MIN)

    p00 = _f32(0.0)
    p01 = _f32(0.0)
    p11 = _f32(0.0)
    q0 = _f32(0.0)
    q1 = _f32(0.0)

    p00 = _f32(p00 + _f32(_f32(2.0) * wy * gv0 * gv0))
    p01 = _f32(p01 + _f32(_f32(2.0) * wy * gv0 * gv1))
    p11 = _f32(p11 + _f32(_f32(2.0) * wy * gv1 * gv1))
    q0 = _f32(q0 + _f32(_f32(2.0) * wy * ev * gv0))
    q1 = _f32(q1 + _f32(_f32(2.0) * wy * ev * gv1))

    p00 = _f32(p00 + _f32(_f32(2.0) * wh * gh0 * gh0))
    p01 = _f32(p01 + _f32(_f32(2.0) * wh * gh0 * gh1))
    p11 = _f32(p11 + _f32(_f32(2.0) * wh * gh1 * gh1))
    q0 = _f32(q0 + _f32(_f32(2.0) * wh * eh * gh0))
    q1 = _f32(q1 + _f32(_f32(2.0) * wh * eh * gh1))

    p00 = _f32(p00 + _f32(_f32(2.0) * _f32(wu + wdu_acc)))
    p11 = _f32(p11 + _f32(_f32(2.0) * _f32(wu + wdu_br)))
    q0 = _f32(q0 + _f32(-_f32(2.0) * wdu_acc * up0))
    q1 = _f32(q1 + _f32(-_f32(2.0) * wdu_br * up1))

    # P in upper-triangular CSC for 2x2.
    # column 0: row 0 -> p00
    # column 1: row 0 -> p01, row 1 -> p11
    return {
        "n": 2,
        "m": 2,
        "P_colptr": [0, 1, 3],
        "P_rowind": [0, 0, 1],
        "P_data": [float(p00), float(p01), float(p11)],
        "q": [float(q0), float(q1)],
        # A = I
        "A_colptr": [0, 1, 2],
        "A_rowind": [0, 1],
        "A_data": [1.0, 1.0],
        "l": [0.0, 0.0],
        "u": [F_ACCEL_MAX, F_BRAKE_MAX],
    }


class GVSoCTCPClient:
    """TCP client for communicating with GVSoC server."""
    
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.sock = None
    
    def connect(self):
        """Establish TCP connection."""
        print(f"[Wrapper] Connecting to GVSoC server at {self.host}:{self.port}", file=sys.stderr)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.settimeout(GVSOC_SOCKET_TIMEOUT_S)
        
        for attempt in range(5):
            try:
                self.sock.connect((self.host, self.port))
                print(f"[Wrapper] Connected successfully", file=sys.stderr)
                return
            except Exception as e:
                print(f"[Wrapper] Connection attempt {attempt+1}/5 failed: {e}", file=sys.stderr)
                if attempt < 4:
                    time.sleep(2)
                else:
                    raise
    
    def send_request(self, request_dict):
        """Send JSON request and receive response."""
        request_json = json.dumps(request_dict) + '\n'
        self.sock.sendall(request_json.encode('utf-8'))
        
        # Read response (newline-delimited JSON)
        buffer = b""
        while b'\n' not in buffer:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("Connection closed by server")
            buffer += chunk
        
        response_line = buffer.split(b'\n')[0]
        response = json.loads(response_line.decode('utf-8'))
        return response
    
    def close(self, send_shutdown=False):
        """Close connection. Set send_shutdown=True to request server shutdown."""
        if self.sock:
            if send_shutdown:
                try:
                    shutdown_json = json.dumps({"type": "shutdown"}) + '\n'
                    self.sock.sendall(shutdown_json.encode('utf-8'))
                    time.sleep(0.1)
                except:
                    pass
            try:
                self.sock.close()
            except:
                pass
            print(f"[Wrapper] Connection closed", file=sys.stderr)


class GVSoCHTTPClient:
    """HTTP client for the Flask server (gvsoc_flask_server.py).

    Same public interface as GVSoCTCPClient so main() needs no changes
    beyond the transport factory.
    Uses only urllib.request (stdlib) — no extra pip packages inside Docker.
    """

    def __init__(self, host, port):
        self.base_url = f'http://{host}:{port}'

    def connect(self):
        """Verify Flask server is alive (GET /health)."""
        import urllib.request as _req
        import urllib.error as _err
        url = f'{self.base_url}/health'
        print(f'[Wrapper] Checking Flask server at {url}', file=sys.stderr)
        for attempt in range(5):
            try:
                with _req.urlopen(url, timeout=5) as resp:
                    if resp.status == 200:
                        print('[Wrapper] Flask server is ready', file=sys.stderr)
                        return
            except _err.URLError as exc:
                print(f'[Wrapper] Health check attempt {attempt+1}/5 failed: {exc}', file=sys.stderr)
                if attempt < 4:
                    time.sleep(2)
                else:
                    raise ConnectionError(f'Flask server not reachable at {url}') from exc

    def send_request(self, request_dict):
        """POST to /mpc/compute, return response dict."""
        import urllib.request as _req
        import urllib.error as _err
        url = f'{self.base_url}/mpc/compute'
        body = json.dumps(request_dict).encode('utf-8')
        req = _req.Request(url, data=body,
                           headers={'Content-Type': 'application/json'},
                           method='POST')
        try:
            with _req.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except _err.HTTPError as exc:
            raise RuntimeError(f'Flask server returned {exc.code}: {exc.read()}') from exc

    def close(self, send_shutdown=False):
        """Optionally ask the Flask server to shut down."""
        if send_shutdown:
            import urllib.request as _req
            try:
                url = f'{self.base_url}/shutdown'
                req = _req.Request(url, data=b'', method='POST')
                with _req.urlopen(req, timeout=5):
                    pass
            except Exception:
                pass  # Server may already be down
        print('[Wrapper] HTTP client closed', file=sys.stderr)


class PipeController:
    """Manages pipe I/O following main_controller.cpp protocol."""
    
    def __init__(self):
        self.u_writer = None
        self.metadata_writer = None
        self.k_reader = None
        self.t_reader = None
        self.x_reader = None
        self.w_reader = None
        self.t_delay_reader = None
    
    def open_pipes(self):
        """
        Open pipes in the exact order as main_controller.cpp:
        1. Writers (u, metadata) - FIRST
        2. Status file - regular file, not pipe
        3. Readers (k, t, x, w, t_delay) - SECOND
        
        This order is critical for avoiding deadlock with SHARC's PipesControllerInterface.
        """
        print("[Wrapper] Opening pipes...", file=sys.stderr)
        
        # Step 1: Open WRITERS first (unblocks SHARC's reader opens)
        print("[Wrapper]   Opening u_c++_to_py (write)", file=sys.stderr)
        self.u_writer = open(U_OUT, 'w', buffering=1)  # Line buffered
        
        print("[Wrapper]   Opening metadata_c++_to_py (write)", file=sys.stderr)
        self.metadata_writer = open(METADATA_OUT, 'w', buffering=1)
        
        # Step 2: Status is a regular file, not a pipe
        # (SHARC writes to it before opening pipes, we just read it when needed)
        
        # Step 3: Open READERS (unblocks SHARC's writer opens)
        print("[Wrapper]   Opening k_py_to_c++ (read)", file=sys.stderr)
        self.k_reader = open(K_IN, 'r')
        
        print("[Wrapper]   Opening t_py_to_c++ (read)", file=sys.stderr)
        self.t_reader = open(T_IN, 'r')
        
        print("[Wrapper]   Opening x_py_to_c++ (read)", file=sys.stderr)
        self.x_reader = open(X_IN, 'r')
        
        print("[Wrapper]   Opening w_py_to_c++ (read)", file=sys.stderr)
        self.w_reader = open(W_IN, 'r')
        
        # Step 4: CRITICAL - open t_delay pipe
        # SHARC opens this for WRITING in PipesControllerInterface.open()
        # If we don't open it for reading, SHARC's open() will block forever
        print("[Wrapper]   Opening t_delay_py_to_c++ (read) - CRITICAL", file=sys.stderr)
        self.t_delay_reader = open(T_DELAY_IN, 'r')
        print("[Wrapper] All pipes opened successfully", file=sys.stderr)
    
    def _read_line(self, reader, name):
        """Read a single line, treat EOF or 'END OF PIPE' as EOF condition."""
        line = reader.readline()
        if line == '':
            raise EOFError(f"EOF on {name}")
        line = line.strip()
        if line == "END OF PIPE":
            raise EOFError(f"END OF PIPE on {name}")
        return line
    
    def read_int(self, reader, name):
        """Read integer from pipe."""
        line = self._read_line(reader, name)
        try:
            return int(line)
        except ValueError:
            raise ValueError(f"Invalid int from {name}: {line}")
    
    def read_float(self, reader, name):
        """Read float from pipe."""
        line = self._read_line(reader, name)
        try:
            return float(line)
        except ValueError:
            raise ValueError(f"Invalid float from {name}: {line}")
    
    def read_vector(self, reader, name):
        """Read vector from pipe (CSV format)."""
        line = self._read_line(reader, name)
        # Remove brackets and split by comma
        line = line.replace('[', '').replace(']', '').strip()
        if line == '':
            return []
        values = []
        for x in line.split(','):
            xs = x.strip()
            if xs != '':
                try:
                    values.append(float(xs))
                except ValueError:
                    raise ValueError(f"Invalid float in vector from {name}: {xs}")
        return values
    
    def read_status(self):
        """Read simulator status from regular file."""
        if not os.path.exists(STATUS_IN):
            return "RUNNING"
        try:
            with open(STATUS_IN, 'r') as f:
                return f.read().strip()
        except:
            return "RUNNING"
    
    def write_vector(self, writer, vec, name):
        """Write vector in SHARC format: [val1, val2, ...]\n"""
        # Keep higher precision to minimize avoidable quantization in pipe transport.
        vec_str = '[' + ', '.join(f"{v:.12g}" for v in vec) + ']'
        writer.write(vec_str + '\n')
        writer.flush()
    
    def write_json(self, writer, data, name):
        """Write JSON metadata in single line."""
        json_str = json.dumps(data)
        writer.write(json_str + '\n')
        writer.flush()
    
    def close_pipes(self):
        """Close all pipes, writing END OF PIPE marker for outputs."""
        print("[Wrapper] Closing pipes...", file=sys.stderr)
        
        # Write "END OF PIPE" to outputs before closing (matches main_controller.cpp)
        if self.u_writer:
            try:
                self.u_writer.write("END OF PIPE\n")
                self.u_writer.flush()
            except (BrokenPipeError, OSError):
                pass
            try:
                self.u_writer.close()
            except:
                pass
        
        if self.metadata_writer:
            try:
                self.metadata_writer.write("END OF PIPE\n")
                self.metadata_writer.flush()
            except (BrokenPipeError, OSError):
                pass
            try:
                self.metadata_writer.close()
            except:
                pass
        
        # Close readers
        if self.k_reader:
            self.k_reader.close()
        if self.t_reader:
            self.t_reader.close()
        if self.x_reader:
            self.x_reader.close()
        if self.w_reader:
            self.w_reader.close()
        if self.t_delay_reader:
            self.t_delay_reader.close()
        
        print("[Wrapper] Pipes closed", file=sys.stderr)


def append_dynamics_trace(path, record):
    """Append one JSON line with per-iteration dynamics received from SHARC."""
    with open(path, 'a', encoding='utf-8') as fh:
        fh.write(json.dumps(record) + '\n')


def scale_cycles_for_delay(raw_cycles, cycle_ns=GVSOC_CYCLE_NS, base_cycle_ns=GVSOC_BASE_CYCLE_NS):
    """Scale raw GVSoC cycles so SHARC's fixed 1.25ns conversion can emulate cycle_ns."""
    raw_cycles = int(raw_cycles)
    scale = cycle_ns / base_cycle_ns
    return max(0, int(round(raw_cycles * scale)))


def validate_official_runtime_config():
    """Enforce strict config guards for the official RISC-V pipeline."""
    if OFFICIAL_RISCV_MODE and GVSOC_TRANSPORT != 'tcp':
        raise RuntimeError("SHARC_OFFICIAL_RISCV_MODE requires GVSOC_TRANSPORT=tcp")
    if OFFICIAL_RISCV_MODE and not GVSOC_QP_SOLVE:
        raise RuntimeError("SHARC_OFFICIAL_RISCV_MODE requires GVSOC_QP_SOLVE=1")


def main():
    """Main controller loop."""
    print(f"[Wrapper] Starting GVSoC Controller Wrapper", file=sys.stderr)
    print(f"[Wrapper] Working directory: {SIMULATION_DIR}", file=sys.stderr)

    validate_official_runtime_config()
    
    tcp_client = None
    pipe_controller = PipeController()

    try:
        # Connect to GVSoC server — transport chosen by GVSOC_TRANSPORT env var
        if GVSOC_TRANSPORT == 'http':
            print(f'[Wrapper] Transport: HTTP (Flask) → {GVSOC_HOST}:{GVSOC_PORT}', file=sys.stderr)
            tcp_client = GVSoCHTTPClient(GVSOC_HOST, GVSOC_PORT)
        else:
            print(f'[Wrapper] Transport: TCP → {GVSOC_HOST}:{GVSOC_PORT}', file=sys.stderr)
            tcp_client = GVSoCTCPClient(GVSOC_HOST, GVSOC_PORT)
        tcp_client.connect()

        request_type = "compute_mpc"
        if GVSOC_TRANSPORT != 'http' and GVSOC_EXEC_MODE == 'persistent':
            init_req = {
                "type": "init",
                "exec_mode": "persistent",
                "persistent_workers": max(1, GVSOC_PERSISTENT_WORKERS),
            }
            init_resp = tcp_client.send_request(init_req)
            print(f"[Wrapper] Persistent INIT response: {init_resp}", file=sys.stderr)
            request_type = "step"
        qp_solve_enabled = GVSOC_TRANSPORT != 'http' and GVSOC_QP_SOLVE
        if qp_solve_enabled:
            print("[Wrapper] QP offload mode enabled: using qp_solve protocol", file=sys.stderr)
        
        # Open pipes (CRITICAL: correct order to avoid deadlock)
        pipe_controller.open_pipes()
        # Reset trace so each simulation directory keeps only current run records.
        with open(TRACE_FILE, 'w', encoding='utf-8'):
            pass
        
        # Track previous control (starts at default: no accel, 100N brake)
        u_prev = [0.0, 100.0]
        
        # Main control loop
        iteration = 0
        while True:
            # Step 1-4: Read inputs from SHARC
            k = pipe_controller.read_int(pipe_controller.k_reader, "k")
            t = pipe_controller.read_float(pipe_controller.t_reader, "t")
            x = pipe_controller.read_vector(pipe_controller.x_reader, "x")
            w = pipe_controller.read_vector(pipe_controller.w_reader, "w")
            
            print(f"[Wrapper] Iteration {k}: t={t:.3f}, x={x}, w={w}", file=sys.stderr)
            
            # Step 5: Check status
            status = pipe_controller.read_status()
            if status == "FINISHED":
                print(f"[Wrapper] Status = FINISHED, exiting", file=sys.stderr)
                break

            # Persist the exact dynamics received from SHARC at this iteration.
            append_dynamics_trace(TRACE_FILE, {
                "iteration": iteration,
                "k": k,
                "t": t,
                "x": x,
                "w": w,
                "u_prev": u_prev
            })
            
            # Step 6-7: Compute control via TCP
            if qp_solve_enabled:
                request = {
                    "type": "qp_solve",
                    "k": k,
                    # In official path, host builds the QP payload from x/w/u_prev.
                    "x": x,
                    "w": w,
                    "u_prev": u_prev,
                    "settings": {
                        # Match legacy C path settings for fidelity.
                        "max_iter": 60,
                        "tol": 1e-3,
                        "rho": 0.05,
                    },
                }
            else:
                request = {
                    "type": request_type,
                    "k": k,
                    "t": t,
                    "x": x,
                    "w": w,
                    "u_prev": u_prev
                }
            
            response = tcp_client.send_request(request)

            if response.get('status') == 'ERROR':
                raise RuntimeError(f"Server error: {response}")

            if qp_solve_enabled:
                x_sol = response.get('x', u_prev)
                if isinstance(x_sol, list) and len(x_sol) >= 2:
                    u = apply_legacy_post_qp_guards(x, w, [float(x_sol[0]), float(x_sol[1])])
                else:
                    u = [0.0, 100.0]
            else:
                u = response.get('u', [0.0, 100.0])
            
            # Update u_prev for next iteration
            u_prev = u
            raw_status = response.get('status', 'UNKNOWN')
            iters = int(response.get('iterations', 0))
            # Match SHARC original naming where successful solves are reported as SUCCESS.
            status_norm = 'SUCCESS' if raw_status == 'OPTIMAL' else raw_status

            if qp_solve_enabled:
                raw_cycles = int(response.get('cycles', max(0, 800 * max(1, iters))))
            else:
                raw_cycles = int(response.get('cycles', 0))
            scaled_cycles = scale_cycles_for_delay(raw_cycles)
            instret = int(response.get('instret', 0))
            ld_stall = int(response.get('ld_stall', 0))
            jmp_stall = int(response.get('jmp_stall', 0))
            imiss = int(response.get('imiss', 0))
            stall_total = int(response.get('stall_total', ld_stall + jmp_stall + imiss))
            branch = int(response.get('branch', 0))
            taken_branch = int(response.get('taken_branch', 0))
            cpi = float(response.get('cpi', (float(raw_cycles) / float(instret)) if instret > 0 else 0.0))
            ipc = float(response.get('ipc', (float(instret) / float(raw_cycles)) if raw_cycles > 0 else 0.0))

            metadata = {
                'cost': response.get('cost', 0.0),
                'iterations': iters,
                'cycles': raw_cycles,
                'scaled_cycles_for_delay': scaled_cycles,
                'chip_cycle_time_ns_effective': GVSOC_CYCLE_NS,
                'status': status_norm,
                't_delay': response.get('t_delay', 0.001),
                'is_feasible': True,
                'solver_status': status_norm,
                'constraint_error': 0.0,  # Grid search has no explicit constraints
                'dual_residual': response.get('dual_residual', 0.0),
                'primal_residual': response.get('primal_residual', 0.0),
                'instret': instret,
                'ld_stall': ld_stall,
                'jmp_stall': jmp_stall,
                'stall_total': stall_total,
                'imiss': imiss,
                'branch': branch,
                'taken_branch': taken_branch,
                'cpi': cpi,
                'ipc': ipc,
            }
            
            # Write cycles to file for GVSoCDelayProvider to read
            # Escribir con la ruta completa para que SHARC lo encuentre
            cycles_file = f'gvsoc_cycles_{k}.txt'
            with open(cycles_file, 'w') as f:
                f.write(str(scaled_cycles))
            print(
                f"[Wrapper] Wrote cycles to {cycles_file} "
                f"(raw={raw_cycles}, scaled={scaled_cycles}, cycle_ns={GVSOC_CYCLE_NS})",
                file=sys.stderr,
            )
            # Step 8-9: Write outputs to SHARC
            pipe_controller.write_vector(pipe_controller.u_writer, u, "u")
            pipe_controller.write_json(pipe_controller.metadata_writer, metadata, "metadata")
            
            # Step 10: CRITICAL - Read t_delay (and discard)
            # SHARC writes to t_delay_py_to_c++ after reading u and metadata
            # If we don't read it, SHARC will block on write
            t_delay = pipe_controller.read_float(pipe_controller.t_delay_reader, "t_delay")
            # We don't use this value, but must read it to unblock SHARC
            
            iteration += 1
        
        print(f"[Wrapper] Completed {iteration} iterations", file=sys.stderr)
    
    except KeyboardInterrupt:
        print(f"\n[Wrapper] Interrupted by user", file=sys.stderr)
    except EOFError as eof:
        print(f"[Wrapper] EOF reached: {eof}", file=sys.stderr)
        # Normal end-of-simulation; exit cleanly without requesting server shutdown
    except Exception as e:
        print(f"[Wrapper] ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Cleanup
        pipe_controller.close_pipes()
        if tcp_client:
            # Do NOT request server shutdown on normal exit
            tcp_client.close(send_shutdown=False)
    
    print(f"[Wrapper] Exiting successfully", file=sys.stderr)
    sys.exit(0)


if __name__ == "__main__":
    main()
