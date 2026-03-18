#!/usr/bin/env python3
"""Binary framing for QP payloads (host -> RISC-V solver)."""

from __future__ import annotations

import struct
import zlib

MAGIC = b"QPBF"
VERSION = 1

# Header:
# magic[4], version[u8], flags[u8], reserved[u16], request_id[u32],
# n[u32], m[u32], p_nnz[u32], a_nnz[u32], payload_len[u32]
HEADER_STRUCT = struct.Struct("<4sBBHIIIIII")
TRAILER_STRUCT = struct.Struct("<I")

FLAG_FULL_QP = 0x01

REQUIRED_KEYS = [
    "n",
    "m",
    "P_colptr",
    "P_rowind",
    "P_data",
    "q",
    "A_colptr",
    "A_rowind",
    "A_data",
    "l",
    "u",
]


def _is_int_list(values) -> bool:
    return isinstance(values, list) and all(isinstance(v, int) for v in values)


def _is_num_list(values) -> bool:
    return isinstance(values, list) and all(isinstance(v, (int, float)) for v in values)


def _validate_csc(name: str, rows: int, cols: int, colptr: list[int], rowind: list[int], data: list[float]) -> tuple[bool, str]:
    if not _is_int_list(colptr):
        return False, f"{name}_colptr must be list[int]"
    if not _is_int_list(rowind):
        return False, f"{name}_rowind must be list[int]"
    if not _is_num_list(data):
        return False, f"{name}_data must be list[number]"

    if len(colptr) != cols + 1:
        return False, f"{name}_colptr must have len cols+1"
    if colptr[0] != 0:
        return False, f"{name}_colptr[0] must be 0"

    prev = 0
    for i, v in enumerate(colptr):
        if v < 0:
            return False, f"{name}_colptr[{i}] must be >= 0"
        if v < prev:
            return False, f"{name}_colptr must be nondecreasing"
        prev = v

    nnz = colptr[-1]
    if len(rowind) != nnz:
        return False, f"{name}_rowind length must match nnz"
    if len(data) != nnz:
        return False, f"{name}_data length must match nnz"

    for i, r in enumerate(rowind):
        if r < 0 or r >= rows:
            return False, f"{name}_rowind[{i}] out of bounds"

    return True, ""


def validate_qp_payload(payload: dict) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "payload must be object"

    for key in REQUIRED_KEYS:
        if key not in payload:
            return False, f"missing payload field: {key}"

    n = payload["n"]
    m = payload["m"]
    if not isinstance(n, int) or n <= 0:
        return False, "n must be positive int"
    if not isinstance(m, int) or m <= 0:
        return False, "m must be positive int"

    ok, err = _validate_csc(
        "P",
        rows=n,
        cols=n,
        colptr=payload["P_colptr"],
        rowind=payload["P_rowind"],
        data=payload["P_data"],
    )
    if not ok:
        return False, err

    ok, err = _validate_csc(
        "A",
        rows=m,
        cols=n,
        colptr=payload["A_colptr"],
        rowind=payload["A_rowind"],
        data=payload["A_data"],
    )
    if not ok:
        return False, err

    q = payload["q"]
    l = payload["l"]
    u = payload["u"]

    if not _is_num_list(q) or len(q) != n:
        return False, "q must be numeric list of length n"
    if not _is_num_list(l) or len(l) != m:
        return False, "l must be numeric list of length m"
    if not _is_num_list(u) or len(u) != m:
        return False, "u must be numeric list of length m"

    for i, (lo, hi) in enumerate(zip(l, u)):
        if float(lo) > float(hi):
            return False, f"l[{i}] must be <= u[{i}]"

    return True, ""


def _pack_u32_array(values: list[int]) -> bytes:
    return struct.pack("<" + ("I" * len(values)), *[int(v) for v in values])


def _pack_f32_array(values: list[float]) -> bytes:
    return struct.pack("<" + ("f" * len(values)), *[float(v) for v in values])


def _unpack_u32_array(blob: bytes, count: int) -> tuple[list[int], int]:
    nbytes = 4 * count
    if len(blob) < nbytes:
        raise ValueError("payload truncated while reading uint32 array")
    vals = list(struct.unpack("<" + ("I" * count), blob[:nbytes]))
    return vals, nbytes


def _unpack_f32_array(blob: bytes, count: int) -> tuple[list[float], int]:
    nbytes = 4 * count
    if len(blob) < nbytes:
        raise ValueError("payload truncated while reading float32 array")
    vals = list(struct.unpack("<" + ("f" * count), blob[:nbytes]))
    return vals, nbytes


def _encode_body(payload: dict) -> bytes:
    n = int(payload["n"])
    m = int(payload["m"])

    return (
        _pack_u32_array(payload["P_colptr"])
        + _pack_u32_array(payload["P_rowind"])
        + _pack_f32_array(payload["P_data"])
        + _pack_f32_array(payload["q"])
        + _pack_u32_array(payload["A_colptr"])
        + _pack_u32_array(payload["A_rowind"])
        + _pack_f32_array(payload["A_data"])
        + _pack_f32_array(payload["l"])
        + _pack_f32_array(payload["u"])
    )


def _decode_body(n: int, m: int, p_nnz: int, a_nnz: int, body: bytes) -> dict:
    pos = 0

    P_colptr, used = _unpack_u32_array(body[pos:], n + 1)
    pos += used
    P_rowind, used = _unpack_u32_array(body[pos:], p_nnz)
    pos += used
    P_data, used = _unpack_f32_array(body[pos:], p_nnz)
    pos += used
    q, used = _unpack_f32_array(body[pos:], n)
    pos += used

    A_colptr, used = _unpack_u32_array(body[pos:], n + 1)
    pos += used
    A_rowind, used = _unpack_u32_array(body[pos:], a_nnz)
    pos += used
    A_data, used = _unpack_f32_array(body[pos:], a_nnz)
    pos += used

    l, used = _unpack_f32_array(body[pos:], m)
    pos += used
    u, used = _unpack_f32_array(body[pos:], m)
    pos += used

    if pos != len(body):
        raise ValueError("payload has trailing bytes")

    payload = {
        "n": n,
        "m": m,
        "P_colptr": P_colptr,
        "P_rowind": P_rowind,
        "P_data": P_data,
        "q": q,
        "A_colptr": A_colptr,
        "A_rowind": A_rowind,
        "A_data": A_data,
        "l": l,
        "u": u,
    }

    ok, err = validate_qp_payload(payload)
    if not ok:
        raise ValueError(f"decoded payload invalid: {err}")

    return payload


def encode_qp_message(payload: dict, request_id: int = 0, flags: int = FLAG_FULL_QP) -> bytes:
    ok, err = validate_qp_payload(payload)
    if not ok:
        raise ValueError(err)

    n = int(payload["n"])
    m = int(payload["m"])
    p_nnz = int(payload["P_colptr"][-1])
    a_nnz = int(payload["A_colptr"][-1])

    body = _encode_body(payload)
    header = HEADER_STRUCT.pack(
        MAGIC,
        VERSION,
        int(flags),
        0,
        int(request_id),
        n,
        m,
        p_nnz,
        a_nnz,
        len(body),
    )
    crc = zlib.crc32(header + body) & 0xFFFFFFFF
    return header + body + TRAILER_STRUCT.pack(crc)


def decode_qp_message(blob: bytes) -> dict:
    if len(blob) < HEADER_STRUCT.size + TRAILER_STRUCT.size:
        raise ValueError("message too short")

    (
        magic,
        version,
        flags,
        _reserved,
        request_id,
        n,
        m,
        p_nnz,
        a_nnz,
        payload_len,
    ) = HEADER_STRUCT.unpack_from(blob, 0)

    if magic != MAGIC:
        raise ValueError("bad magic")
    if version != VERSION:
        raise ValueError(f"unsupported version: {version}")

    payload_start = HEADER_STRUCT.size
    payload_end = payload_start + payload_len
    if payload_end + TRAILER_STRUCT.size != len(blob):
        raise ValueError("payload length mismatch")

    stored_crc = TRAILER_STRUCT.unpack_from(blob, payload_end)[0]
    calc_crc = zlib.crc32(blob[:payload_end]) & 0xFFFFFFFF
    if stored_crc != calc_crc:
        raise ValueError("checksum mismatch")

    payload = _decode_body(
        n=int(n),
        m=int(m),
        p_nnz=int(p_nnz),
        a_nnz=int(a_nnz),
        body=blob[payload_start:payload_end],
    )

    return {
        "protocol_version": int(version),
        "flags": int(flags),
        "request_id": int(request_id),
        "payload": payload,
    }
