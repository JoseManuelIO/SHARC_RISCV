#!/usr/bin/env python3
"""Binary framing for kernel_op transport payloads."""

from __future__ import annotations

import struct
import sys
import zlib
from pathlib import Path

_scripts_dir = Path(__file__).parent
sys.path.insert(0, str(_scripts_dir))
from kernel_ops import validate_kernel_payload


MAGIC = b"KRNL"
VERSION = 1
HEADER_STRUCT = struct.Struct("<4sBBHII")
TRAILER_STRUCT = struct.Struct("<I")

OP_CODES = {
    "matvec_dense": 1,
    "matvec_sparse": 2,
    "dot": 3,
    "axpy": 4,
    "box_project": 5,
}
OP_NAMES = {v: k for k, v in OP_CODES.items()}


def _pack_f32_array(values: list[float]) -> bytes:
    return struct.pack("<" + ("f" * len(values)), *[float(v) for v in values])


def _unpack_f32_array(blob: bytes, count: int) -> tuple[list[float], int]:
    nbytes = 4 * count
    if len(blob) < nbytes:
        raise ValueError("payload truncated while reading float array")
    vals = list(struct.unpack("<" + ("f" * count), blob[:nbytes]))
    return vals, nbytes


def _pack_u32_array(values: list[int]) -> bytes:
    return struct.pack("<" + ("I" * len(values)), *[int(v) for v in values])


def _unpack_u32_array(blob: bytes, count: int) -> tuple[list[int], int]:
    nbytes = 4 * count
    if len(blob) < nbytes:
        raise ValueError("payload truncated while reading uint32 array")
    vals = list(struct.unpack("<" + ("I" * count), blob[:nbytes]))
    return vals, nbytes


def _encode_payload(op: str, payload: dict) -> bytes:
    if op == "dot":
        x = payload["x"]
        y = payload["y"]
        return struct.pack("<I", len(x)) + _pack_f32_array(x) + _pack_f32_array(y)
    if op == "axpy":
        alpha = float(payload["alpha"])
        x = payload["x"]
        y = payload["y"]
        return struct.pack("<If", len(x), alpha) + _pack_f32_array(x) + _pack_f32_array(y)
    if op == "box_project":
        x, lo, hi = payload["x"], payload["lo"], payload["hi"]
        return struct.pack("<I", len(x)) + _pack_f32_array(x) + _pack_f32_array(lo) + _pack_f32_array(hi)
    if op == "matvec_dense":
        rows, cols = payload["rows"], payload["cols"]
        A, x = payload["A"], payload["x"]
        return struct.pack("<II", rows, cols) + _pack_f32_array(A) + _pack_f32_array(x)
    if op == "matvec_sparse":
        rows, cols = payload["rows"], payload["cols"]
        indptr, indices, data, x = payload["indptr"], payload["indices"], payload["data"], payload["x"]
        nnz = len(indices)
        return (
            struct.pack("<III", rows, cols, nnz)
            + _pack_u32_array(indptr)
            + _pack_u32_array(indices)
            + _pack_f32_array(data)
            + _pack_f32_array(x)
        )
    raise ValueError(f"unsupported op: {op}")


def _decode_payload(op: str, blob: bytes) -> dict:
    pos = 0

    def _read(fmt: str):
        nonlocal pos
        st = struct.Struct(fmt)
        if pos + st.size > len(blob):
            raise ValueError("payload truncated")
        out = st.unpack_from(blob, pos)
        pos += st.size
        return out

    if op == "dot":
        (n,) = _read("<I")
        x, used = _unpack_f32_array(blob[pos:], n)
        pos += used
        y, used = _unpack_f32_array(blob[pos:], n)
        pos += used
        return {"x": x, "y": y}

    if op == "axpy":
        n, alpha = _read("<If")
        x, used = _unpack_f32_array(blob[pos:], n)
        pos += used
        y, used = _unpack_f32_array(blob[pos:], n)
        pos += used
        return {"alpha": alpha, "x": x, "y": y}

    if op == "box_project":
        (n,) = _read("<I")
        x, used = _unpack_f32_array(blob[pos:], n)
        pos += used
        lo, used = _unpack_f32_array(blob[pos:], n)
        pos += used
        hi, used = _unpack_f32_array(blob[pos:], n)
        pos += used
        return {"x": x, "lo": lo, "hi": hi}

    if op == "matvec_dense":
        rows, cols = _read("<II")
        a_count = rows * cols
        A, used = _unpack_f32_array(blob[pos:], a_count)
        pos += used
        x, used = _unpack_f32_array(blob[pos:], cols)
        pos += used
        return {"rows": rows, "cols": cols, "A": A, "x": x}

    if op == "matvec_sparse":
        rows, cols, nnz = _read("<III")
        indptr, used = _unpack_u32_array(blob[pos:], rows + 1)
        pos += used
        indices, used = _unpack_u32_array(blob[pos:], nnz)
        pos += used
        data, used = _unpack_f32_array(blob[pos:], nnz)
        pos += used
        x, used = _unpack_f32_array(blob[pos:], cols)
        pos += used
        return {"rows": rows, "cols": cols, "indptr": indptr, "indices": indices, "data": data, "x": x}

    raise ValueError(f"unsupported op: {op}")


def encode_kernel_message(op: str, payload: dict, request_id: int = 0, flags: int = 0) -> bytes:
    if op not in OP_CODES:
        raise ValueError(f"unsupported op: {op}")
    ok, err = validate_kernel_payload(op, payload)
    if not ok:
        raise ValueError(err)
    body = _encode_payload(op, payload)
    header = HEADER_STRUCT.pack(MAGIC, VERSION, OP_CODES[op], flags, int(request_id), len(body))
    crc = zlib.crc32(header + body) & 0xFFFFFFFF
    return header + body + TRAILER_STRUCT.pack(crc)


def decode_kernel_message(blob: bytes) -> dict:
    if len(blob) < HEADER_STRUCT.size + TRAILER_STRUCT.size:
        raise ValueError("message too short")
    magic, version, op_code, flags, request_id, payload_len = HEADER_STRUCT.unpack_from(blob, 0)
    if magic != MAGIC:
        raise ValueError("bad magic")
    if version != VERSION:
        raise ValueError(f"unsupported version: {version}")
    if op_code not in OP_NAMES:
        raise ValueError(f"unsupported op code: {op_code}")

    payload_start = HEADER_STRUCT.size
    payload_end = payload_start + payload_len
    if payload_end + TRAILER_STRUCT.size != len(blob):
        raise ValueError("payload length mismatch")

    stored_crc = TRAILER_STRUCT.unpack_from(blob, payload_end)[0]
    calc_crc = zlib.crc32(blob[:payload_end]) & 0xFFFFFFFF
    if stored_crc != calc_crc:
        raise ValueError("checksum mismatch")

    op = OP_NAMES[op_code]
    payload = _decode_payload(op, blob[payload_start:payload_end])
    ok, err = validate_kernel_payload(op, payload)
    if not ok:
        raise ValueError(f"decoded payload invalid: {err}")

    return {
        "protocol_version": version,
        "op": op,
        "flags": flags,
        "request_id": request_id,
        "payload": payload,
    }
