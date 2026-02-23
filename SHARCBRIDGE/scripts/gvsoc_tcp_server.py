#!/usr/bin/env python3
"""
GVSoC TCP Server - Bridge between SHARC and GVSoC

This server listens for TCP connections from SHARC (running in Docker)
and executes MPC computations in GVSoC for each request.

Protocol:
  Request:  {"type": "compute_mpc", "k": int, "t": float, "x": [3 floats], "w": [2 floats]}
  Response: {"k": int, "u": [2 floats], "cost": float, "status": str, "iterations": int, "cycles": int}
  
  Special: {"type": "shutdown"} to stop the server
"""

import socket
import json
import subprocess
import os
import sys
import signal
import tempfile
from pathlib import Path

# ============================================================================
# Configuration
# ============================================================================

SERVER_HOST = "0.0.0.0"  # Bind to all interfaces (Docker can reach)
SERVER_PORT = 5000

# Paths (adjust if needed)
SHARCBRIDGE_DIR = Path.home() / "Repositorios" / "SHARC_RISCV" / "SHARCBRIDGE"
MPC_DIR = SHARCBRIDGE_DIR / "mpc"
MPC_ELF = MPC_DIR / "build" / "mpc_acc_controller.elf"

# Python virtual environment
VENV_ACTIVATE = Path.home() / "Repositorios" / "SHARC_RISCV" / "venv" / "bin" / "activate"

# PULP GVSoC paths
PULP_DIR = Path.home() / "Repositorios" / "SHARC_RISCV" / "PULP"
PULP_SDK_SOURCEME = PULP_DIR / "pulp-sdk" / "configs" / "pulp-open.sh"
GVSOC_INSTALL_DIR = PULP_DIR / "gvsoc" / "install"
GVSOC_BINARY = GVSOC_INSTALL_DIR / "bin" / "gvsoc"

# Toolchain for ELF patching
TOOLCHAIN_DIR = Path("/opt/riscv/bin")
OBJCOPY = TOOLCHAIN_DIR / "riscv32-unknown-elf-objcopy"
NM = TOOLCHAIN_DIR / "riscv32-unknown-elf-nm"

# Temp files
PATCHED_ELF = "/tmp/mpc_acc_patched.elf"

# ============================================================================
# Validation
# ============================================================================

def validate_environment():
    """Check that all required files exist."""
    errors = []
    
    if not MPC_ELF.exists():
        errors.append(f"MPC ELF not found: {MPC_ELF}")
        errors.append(f"  Build with: cd {MPC_DIR} && make")
    
    if not PULP_SDK_SOURCEME.exists():
        errors.append(f"PULP SDK config not found: {PULP_SDK_SOURCEME}")
    
    if not GVSOC_BINARY.exists():
        errors.append(f"GVSoC binary not found: {GVSOC_BINARY}")
        errors.append("  Build GVSoC first: cd PULP/gvsoc && make all install")
    
    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return False
    
    return True

# ============================================================================
# ELF Patching - Inject runtime parameters into shared memory
# ============================================================================

# Shared data layout offsets (must match SharedData struct in mpc_acc_controller.c)
# float input_x[3]      -> offset 0x00 (12 bytes)
# float input_w[2]      -> offset 0x0C (8 bytes)
# int input_k           -> offset 0x14 (4 bytes)
# float input_t         -> offset 0x18 (4 bytes)
# float input_u_prev[2] -> offset 0x1C (8 bytes)

import struct
import shutil

# Cache the symbol address (extracted once)
_shared_addr = None

def get_shared_addr():
    """Get the address of the 'shared' symbol from the ELF."""
    global _shared_addr
    if _shared_addr is not None:
        return _shared_addr
    
    try:
        result = subprocess.run(
            [str(NM), str(MPC_ELF)],
            capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            if ' D shared' in line or ' d shared' in line:
                _shared_addr = int(line.split()[0], 16)
                print(f"[Server] Shared data at 0x{_shared_addr:08x}", file=sys.stderr)
                return _shared_addr
    except Exception as e:
        print(f"[Server] WARNING: Could not read symbol table: {e}", file=sys.stderr)
    
    # Fallback: known address from linker script
    _shared_addr = 0x1c010000
    print(f"[Server] Using default shared address: 0x{_shared_addr:08x}", file=sys.stderr)
    return _shared_addr

def patch_elf_with_params(k: int, t: float, x: list, w: list, u_prev: list = None) -> str:
    """
    Create a patched copy of the ELF with runtime parameters injected
    into the .shared_data section.
    
    Returns path to patched ELF.
    """
    import re
    
    if u_prev is None:
        u_prev = [0.0, 100.0]  # Default: no accel, 100N brake
    
    print(f"[Server] DEBUG: Patching ELF with k={k}, t={t}, x={x}, w={w}, u_prev={u_prev}", file=sys.stderr)
    print(f"[Server] DEBUG: Source ELF: {MPC_ELF}", file=sys.stderr)
    print(f"[Server] DEBUG: Target ELF: {PATCHED_ELF}", file=sys.stderr)
    
    # Copy original ELF
    shutil.copy2(str(MPC_ELF), PATCHED_ELF)
    
    # Build the raw bytes for the SharedData struct (inputs only)
    # float input_x[3] + float input_w[2] + int input_k + float input_t + float input_u_prev[2]
    data = struct.pack('<3f', x[0], x[1], x[2])   # input_x (12 bytes)
    data += struct.pack('<2f', w[0], w[1])         # input_w (8 bytes)
    data += struct.pack('<i', k)                    # input_k (4 bytes)
    data += struct.pack('<f', t)                    # input_t (4 bytes)
    data += struct.pack('<2f', u_prev[0], u_prev[1])  # input_u_prev (8 bytes)
    # Total: 36 bytes
    
    # Write raw data to a temp file
    raw_file = "/tmp/gvsoc_shared_data.bin"
    with open(raw_file, 'wb') as f:
        f.write(data)
    
    # Use objcopy to update the .shared_data section
    print(f"[Server] DEBUG: Running objcopy with data file {raw_file}", file=sys.stderr)
    try:
        result = subprocess.run(
            [str(OBJCOPY),
             "--update-section", f".shared_data={raw_file}",
             PATCHED_ELF],
            capture_output=True, text=True, timeout=5
        )
        print(f"[Server] DEBUG: objcopy returncode={result.returncode}", file=sys.stderr)
        if result.returncode != 0:
            print(f"[Server] WARNING: objcopy failed: {result.stderr}", file=sys.stderr)
            # Fall back to unpatched ELF
            return str(MPC_ELF)
        else:
            print(f"[Server] DEBUG: objcopy successful, using {PATCHED_ELF}", file=sys.stderr)
    except Exception as e:
        print(f"[Server] WARNING: objcopy error: {e}", file=sys.stderr)
        return str(MPC_ELF)
    
    return PATCHED_ELF

# ============================================================================
# GVSoC Execution
# ============================================================================

def run_gvsoc_mpc(k: int, t: float, x: list, w: list, u_prev: list = None) -> dict:
    """
    Execute one MPC computation in GVSoC.
    
    1. Patches the ELF with the runtime state parameters (x, w, k, t, u_prev)
    2. Launches GVSoC with a timeout (the WFI instruction doesn't terminate cleanly)
    3. Parses stdout for MPC results (U=, COST=, ITER=, STATUS=, etc.)
    
    Args:
        k: time step index
        t: time in seconds
        x: state vector [position, headway, velocity]
        w: exogenous input [v_front, constant]
        u_prev: previous control [F_accel, F_brake]
        
    Returns:
        dict with keys: k, u, cost, status, iterations, cycles, t_delay
    """
    import re
    
    if u_prev is None:
        u_prev = [0.0, 100.0]
    
    # Patch ELF with runtime parameters
    elf_path = patch_elf_with_params(k, t, x, w, u_prev)
    print(f"[Server] DEBUG: Using ELF: {elf_path}", file=sys.stderr)
    
    # Build GVSoC command using absolute path to gvsoc binary
    # Activate venv first for Python dependencies (gapylib)
    # Then source pulp-open.sh for PULP_SDK_HOME and related vars
    cmd = f"""
    source {VENV_ACTIVATE} && \\
    source {PULP_SDK_SOURCEME} && \\
    timeout 10 {GVSOC_BINARY} \\
        --target=pulp-open \\
        --platform=gvsoc \\
        --binary={elf_path} \\
        run
    """
    
    print(f"\n[Server] Step {k}: x={x}, w={w}", file=sys.stderr)
    
    # Measure real execution time
    import time
    t_start = time.perf_counter()
    
    try:
        result = subprocess.run(
            ["bash", "-c", cmd],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            cwd=str(MPC_DIR)
        )
        
        t_end = time.perf_counter()
        t_delay = t_end - t_start
        
        output = result.stdout
        stderr = result.stderr
        
        if stderr:
            print(f"[GVSOC stderr] {stderr[:200]}", file=sys.stderr)
        
    except subprocess.TimeoutExpired:
        t_end = time.perf_counter()
        t_delay = t_end - t_start
        print(f"[Server] ERROR: GVSoC timeout at step {k}", file=sys.stderr)
        return {
            'k': k, 'u': [0.0, 100.0], 'cost': 0.0,
            'status': 'TIMEOUT', 'iterations': 0, 'cycles': 0, 't_delay': t_delay
        }
    except Exception as e:
        t_end = time.perf_counter()
        t_delay = t_end - t_start
        print(f"[Server] ERROR running GVSoC: {e}", file=sys.stderr)
        return {
            'k': k, 'u': [0.0, 100.0], 'cost': 0.0,
            'status': 'ERROR', 'iterations': 0, 'cycles': 0, 't_delay': t_delay
        }
    
    # Parse stdout for MPC results
    u = [0.0, 0.0]
    cost = 0.0
    iters = 0
    cycles = 0
    status = "UNKNOWN"
    
    num = r'[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?'
    u_match = re.search(rf'U=({num}),({num})', output)
    if u_match:
        u = [float(u_match.group(1)), float(u_match.group(2))]
    
    cost_match = re.search(rf'COST=({num})', output)
    if cost_match:
        cost = float(cost_match.group(1))
    
    iter_match = re.search(r'ITER=(\d+)', output)
    if iter_match:
        iters = int(iter_match.group(1))
    
    cycles_match = re.search(r'CYCLES=(\d+)', output)
    if cycles_match:
        cycles = int(cycles_match.group(1))
    
    status_match = re.search(r'STATUS=(\w+)', output)
    if status_match:
        status = status_match.group(1)
    
    has_start = 'MPC_START' in output
    has_done = 'MPC_DONE' in output
    
    if not has_start:
        print(f"[Server] WARNING: No MPC_START in output", file=sys.stderr)
        status = "NO_START"
    
    print(f"[Server] Step {k}: u={u}, cost={cost:.2e}, status={status}, t_delay={t_delay:.6f}s", file=sys.stderr)
    
    return {
        'k': k,
        'u': u,
        'cost': cost,
        'status': status,
        'iterations': iters,
        'cycles': cycles,
        't_delay': t_delay
    }

# ============================================================================
# TCP Server
# ============================================================================

def handle_client(conn, addr):
    """Handle a single client connection."""
    print(f"\n[Server] Client connected: {addr}", file=sys.stderr)
    
    # Maintain u_prev between iterations (starts at default [0, 100])
    u_prev = [0.0, 100.0]
    
    try:
        buffer = b""
        step = 0
        
        while True:
            # Receive data
            chunk = conn.recv(4096)
            if not chunk:
                print(f"[Server] Client {addr} disconnected", file=sys.stderr)
                break
            
            buffer += chunk
            
            # Process complete JSON messages (newline-delimited)
            while b'\n' in buffer:
                line, buffer = buffer.split(b'\n', 1)
                
                if not line.strip():
                    continue
                
                try:
                    request = json.loads(line.decode('utf-8'))
                except json.JSONDecodeError as e:
                    print(f"[Server] JSON decode error: {e}", file=sys.stderr)
                    continue
                
                # Handle shutdown request
                if request.get('type') == 'shutdown':
                    print(f"[Server] Shutdown requested by {addr}", file=sys.stderr)
                    response = {'status': 'SHUTDOWN'}
                    conn.sendall((json.dumps(response) + '\n').encode('utf-8'))
                    return 'shutdown'
                
                # Handle MPC computation request
                if request.get('type') == 'compute_mpc':
                    k = request.get('k', 0)
                    t = request.get('t', 0.0)
                    x = request.get('x', [0.0, 60.0, 15.0])
                    w = request.get('w', [11.0, 1.0])
                    
                    # Get u_prev from request, or fall back to internal tracking
                    request_u_prev = request.get('u_prev', None)
                    if request_u_prev is not None:
                        u_prev = request_u_prev
                        print(f"[Server] Using u_prev from request: {u_prev}", file=sys.stderr)
                    else:
                        print(f"[Server] Using tracked u_prev: {u_prev}", file=sys.stderr)
                    
                    # Execute MPC in GVSoC with u_prev
                    result = run_gvsoc_mpc(k, t, x, w, u_prev)
                    
                    # Update u_prev for next iteration (backward compatibility)
                    u_prev = result.get('u', u_prev)
                    
                    # Send response
                    response_str = json.dumps(result) + '\n'
                    conn.sendall(response_str.encode('utf-8'))
                    
                    step += 1
                else:
                    print(f"[Server] Unknown request type: {request.get('type')}", file=sys.stderr)
        
    except Exception as e:
        print(f"[Server] Error handling client {addr}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    
    finally:
        conn.close()

def run_server():
    """Main server loop."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server_socket.bind((SERVER_HOST, SERVER_PORT))
        server_socket.listen(5)
        
        print("=" * 70)
        print("GVSoC TCP Server - SHARCBRIDGE")
        print("=" * 70)
        print(f"MPC ELF:        {MPC_ELF}")
        print(f"GVSoC binary:   {GVSOC_BINARY}")
        print(f"PULP SDK:       {PULP_SDK_SOURCEME}")
        print(f"\nListening on:   {SERVER_HOST}:{SERVER_PORT}")
        print("=" * 70)
        print("\nWaiting for connections...\n")
        
        while True:
            conn, addr = server_socket.accept()
            
            # Handle client in the same thread (sequential)
            # For multiple simultaneous clients, use threading
            result = handle_client(conn, addr)
            
            if result == 'shutdown':
                print("\n[Server] Shutting down gracefully")
                break
    
    except KeyboardInterrupt:
        print("\n\n[Server] Interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"\n[Server] Fatal error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        server_socket.close()
        print("[Server] Socket closed")

# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Entry point."""
    print("Validating environment...", file=sys.stderr)
    
    if not validate_environment():
        print("\nFix the errors above and try again.", file=sys.stderr)
        sys.exit(1)
    
    print("✓ All checks passed\n", file=sys.stderr)
    
    # Run server
    run_server()

if __name__ == "__main__":
    main()
