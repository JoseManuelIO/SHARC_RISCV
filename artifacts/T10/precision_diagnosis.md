# Precision Diagnosis 64b vs 32b (T10.1)

- Generated: `2026-02-23T10:24:24.652144`
- Scope: original MPC numeric types vs SHARCBRIDGE transport path.

## Evidence
- Original typedefs use `double` in `sharc_original/resources/controllers/include/controller.h`: `True`
- Original controller parameter declarations with `double` in `sharc_original/resources/controllers/include/ACC_Controller.h`: `19` occurrences
- GVSoC TCP patch path packs `float32` with `struct.pack(<...f)` in `SHARCBRIDGE/scripts/gvsoc_tcp_server.py`: `True`
- Flask ingress casts JSON numeric inputs to Python `float` in `SHARCBRIDGE/scripts/gvsoc_flask_server.py`: `True`
- Wrapper uses `read_float(...)` in `SHARCBRIDGE/sharc_patches/acc_example/gvsoc_controller_wrapper_v2.py`: `True`

## Result
- Mismatch detected (double vs float32 transport): `True`
- Interpretation: Original MPC is double-precision while bridge transport currently serializes as float32.

## Test Gate
- PASS criteria for T10.1: mismatch is explicitly characterized with concrete code evidence.
- Status: `PASS`
