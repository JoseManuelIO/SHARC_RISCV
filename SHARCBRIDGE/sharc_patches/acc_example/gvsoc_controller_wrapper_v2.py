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


# TCP settings
GVSOC_HOST = os.environ.get('GVSOC_HOST', '172.17.0.1')
GVSOC_PORT = int(os.environ.get('GVSOC_PORT', '5000'))


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
        self.sock.settimeout(10)
        
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
        vec_str = '[' + ', '.join(f"{v:.6f}" for v in vec) + ']'
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


def main():
    """Main controller loop."""
    print(f"[Wrapper] Starting GVSoC Controller Wrapper", file=sys.stderr)
    print(f"[Wrapper] Working directory: {SIMULATION_DIR}", file=sys.stderr)
    
    tcp_client = None
    pipe_controller = PipeController()
    
    try:
        # Connect to GVSoC TCP server
        tcp_client = GVSoCTCPClient(GVSOC_HOST, GVSOC_PORT)
        tcp_client.connect()
        
        # Open pipes (CRITICAL: correct order to avoid deadlock)
        pipe_controller.open_pipes()
        
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
            
            # Step 6-7: Compute control via TCP
            request = {
                "type": "compute_mpc",
                "k": k,
                "t": t,
                "x": x,
                "w": w
            }
            
            response = tcp_client.send_request(request)
            
            u = response.get('u', [0.0, 100.0])
            metadata = {
                'cost': response.get('cost', 0.0),
                'iterations': response.get('iterations', 0),
                'cycles': response.get('cycles', 0),
                'status': response.get('status', 'UNKNOWN'),
                't_delay': response.get('t_delay', 0.001),
                'is_feasible': True,
                'solver_status': response.get('status', 'UNKNOWN')
            }
            
            print(f"[Wrapper] Result: u={u}, status={metadata['status']}", file=sys.stderr)
            
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
