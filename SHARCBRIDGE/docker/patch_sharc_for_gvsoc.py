#!/usr/bin/env python3
"""
Patch SHARC to execute GVSoC wrapper natively (without SCARAB).
SCARAB cannot handle network syscalls needed for TCP communication.
"""
import sys

def main():
    filepath = '/home/dcuser/resources/sharc/__init__.py'
    
    with open(filepath, 'r') as f:
        lines = f.readlines()
    
    # Find the run_controller method in SerialSimulationExecutor (around line 1141)
    target_line = None
    for i, line in enumerate(lines):
        if i > 1130 and 'def run_controller(self):' in line:
            # Check if next lines match our expected context
            if i+2 < len(lines) and 'cmd = " ".join([self.controller_executable])' in lines[i+1]:
                target_line = i
                break
    
    if target_line is None:
        print("ERROR: Could not find target location in SHARC __init__.py", file=sys.stderr)
        sys.exit(1)
    
    # Insert our patch after line with 'print("Starting scarab_runner: "...'
    insert_pos = target_line + 3  # After the print statement
    
    patch_code = '''    
    # GVSOC integration: execute wrapper natively (no SCARAB)
    # SCARAB cannot handle network syscalls (socket, connect, send)
    use_gvsoc = self.sim_config.get("use_gvsoc_controller", False)
    if use_gvsoc:
      print("[GVSOC] Using NATIVE execution (no SCARAB)")
      # Replace controller executable with GVSoC wrapper
      wrapper_path = '/home/dcuser/examples/acc_example/gvsoc_controller_wrapper_v2.py'
      print(f"[GVSOC] Using wrapper: {wrapper_path}")
      import subprocess
      proc = subprocess.Popen(
        [wrapper_path],
        cwd=self.sim_dir,
        stdout=self.controller_log,
        stderr=subprocess.STDOUT
      )
      result = proc.wait()
      print(f"[GVSOC] Wrapper finished with exit code {result}")
      if result != 0:
        raise Exception(f"GVSoC wrapper failed with code {result}")
      return
    
'''
    
    # Insert the patch
    lines.insert(insert_pos, patch_code)
    
    # Write back
    with open(filepath, 'w') as f:
        f.writelines(lines)
    
    print(f"✓ Successfully patched {filepath} at line {insert_pos}")
    print("  Added native execution path for use_gvsoc_controller=true")

if __name__ == '__main__':
    main()
