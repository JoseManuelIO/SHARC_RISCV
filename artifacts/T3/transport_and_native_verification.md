# Transport and Native Verification (T3)

- Generated: `2026-02-23T10:03:22.750810`

## T3.1 HTTP Official
- Matches found: `1`
- `43:GVSOC_TRANSPORT = os.environ.get('GVSOC_TRANSPORT', 'http')`

## T3.2 TCP Fallback Available
- Matches found: `4`
- `SHARCBRIDGE/scripts/gvsoc_tcp_server.py:29:SERVER_PORT = 5000`
- `SHARCBRIDGE/scripts/gvsoc_tcp_server.py:388:def run_server():`
- `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py:48:class GVSoCTCPClient:`
- `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py:108:class GVSoCHTTPClient:`

## T3.3 Native Execution Evidence
- `/tmp/sharc_figure5/2026-02-23--10-02-14`

## Verdict
- PASS