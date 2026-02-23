#!/usr/bin/env python3
"""
GVSoC Flask HTTP Server - Thread-safe MPC computation service

Advantages over raw TCP server (gvsoc_tcp_server.py):
- Handles N concurrent clients simultaneously (one thread per request)
- No serial bottleneck: parallel SHARC batches can call /mpc/compute at the same time
- Easy to debug with curl or a browser
- TCP server (gvsoc_tcp_server.py) remains untouched for backward compatibility

Usage:
  python3 gvsoc_flask_server.py [--port PORT]
  
  Select via wrapper env var:
    GVSOC_TRANSPORT=http  -> wrapper uses this Flask server
    GVSOC_TRANSPORT=tcp   -> wrapper uses TCP server (default)
"""

import sys
import os
import argparse
from pathlib import Path

# Re-use all GVSoC logic from TCP server (no code duplication)
_scripts_dir = Path(__file__).parent
sys.path.insert(0, str(_scripts_dir))
from gvsoc_tcp_server import (
    run_gvsoc_mpc,
    validate_environment,
    SERVER_HOST,
    SERVER_PORT,
)

from flask import Flask, request, jsonify

app = Flask(__name__)


# ============================================================================
# Endpoints
# ============================================================================

@app.route('/health', methods=['GET'])
def health():
    """Health check. Used by run_flask_integration.sh to wait until ready."""
    return jsonify({'status': 'ok', 'server': 'gvsoc-flask'}), 200


@app.route('/mpc/compute', methods=['POST'])
def compute_mpc():
    """
    Execute one MPC step in GVSoC.

    Request JSON:
      {
        "k":      int,
        "t":      float,
        "x":      [float, float, float],
        "w":      [float, float],
        "u_prev": [float, float]   // optional
      }

    Response JSON (same shape as TCP server):
      {
        "k": int, "u": [float, float], "cost": float,
        "status": str, "iterations": int, "cycles": int, "t_delay": float
      }

    Flask runs this handler in a dedicated thread per request (threaded=True),
    so multiple SHARC batches can call /mpc/compute concurrently without blocking
    each other.
    """
    data = request.get_json(silent=True)
    if data is None:
        return jsonify({'error': 'Request body must be JSON'}), 400

    # Validate required fields
    for field in ('k', 't', 'x', 'w'):
        if field not in data:
            return jsonify({'error': f'Missing required field: {field}'}), 400

    try:
        k      = int(data['k'])
        t      = float(data['t'])
        x      = [float(v) for v in data['x']]
        w      = [float(v) for v in data['w']]
        u_prev = [float(v) for v in data['u_prev']] if 'u_prev' in data else None
    except (TypeError, ValueError) as exc:
        return jsonify({'error': f'Invalid field value: {exc}'}), 400

    try:
        result = run_gvsoc_mpc(k, t, x, w, u_prev)
    except Exception as exc:
        print(f'[Flask] ERROR in run_gvsoc_mpc: {exc}', file=sys.stderr)
        return jsonify({'error': str(exc)}), 500

    return jsonify(result), 200


@app.route('/shutdown', methods=['POST'])
def shutdown():
    """
    Graceful shutdown endpoint.
    Called by run_flask_integration.sh after the experiment finishes.
    """
    func = request.environ.get('werkzeug.server.shutdown')
    if func is not None:
        func()
        return jsonify({'status': 'shutting down'}), 200
    # Werkzeug >= 2.1 removed shutdown hook; fall back to OS signal
    import signal, os
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({'status': 'shutting down via SIGINT'}), 200


# ============================================================================
# Entry point
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description='GVSoC Flask MPC server')
    parser.add_argument('--port', type=int, default=SERVER_PORT,
                        help=f'Port to listen on (default: {SERVER_PORT})')
    parser.add_argument('--host', default=SERVER_HOST,
                        help=f'Host to bind to (default: {SERVER_HOST})')
    parser.add_argument('--skip-validation', action='store_true',
                        help='Skip environment validation (useful for tests)')
    args = parser.parse_args()

    if not args.skip_validation:
        print('Validating environment...', file=sys.stderr)
        if not validate_environment():
            print('\nFix the errors above and try again.', file=sys.stderr)
            sys.exit(1)
        print('✓ All checks passed\n', file=sys.stderr)

    print('=' * 70, file=sys.stderr)
    print('GVSoC Flask Server - SHARCBRIDGE', file=sys.stderr)
    print('=' * 70, file=sys.stderr)
    print(f'Listening on:  http://{args.host}:{args.port}', file=sys.stderr)
    print(f'Health check:  GET  http://localhost:{args.port}/health', file=sys.stderr)
    print(f'MPC endpoint:  POST http://localhost:{args.port}/mpc/compute', file=sys.stderr)
    print(f'Shutdown:      POST http://localhost:{args.port}/shutdown', file=sys.stderr)
    print('=' * 70, file=sys.stderr)
    print('\nthreaded=True → concurrent requests are handled in parallel\n', file=sys.stderr)

    app.run(
        host=args.host,
        port=args.port,
        debug=False,
        threaded=True,     # CRITICAL: one thread per request → N batches in parallel
        use_reloader=False,
    )


if __name__ == '__main__':
    main()
