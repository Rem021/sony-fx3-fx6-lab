"""原 FX6 0x290 Init 快照到固定 FX3 0x1f8 的 host 结构投影与拒绝门。

不执行 ELF、不安装 guest thunk、不返回运行成功。所有非空回调保留原值供审计；
即使映射后得到 0x1f8 bytes，也不能当作可调用的 FX3 入参。
"""
from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

DONOR = Path(__file__).resolve().parents[3]
CALLBACK_INDEX = DONOR / "capid-init-portability/callback-fields.json"
CALLBACK_INDEX_SHA = "aef19dda30c2120538ad4ed66b536b25f01eb94c8326239658b0f5953ff660a5"


class Rejected(ValueError):
    pass


SUPPORT = {
    "_ZN3mpr25gp_evtPowerOnFinishedFuncE": "requires_1026_to_102d_thunk_and_live_waiter",
    "_ZN3mpr19gp_evtRecPbTimeFuncE": "requires_1022_to_1029_record_only_thunk;playback_unknown",
    "_ZN3mpr28gp_evtMovieWriteFinishedFuncE": "reject_32B_to_0x788_extended_payload",
    "_ZN3mpr29gp_evtMovieRecAutoDividedFuncE": "reject_32B_to_0x780_extended_payload",
}


@dataclass(frozen=True)
class Projection:
    original_sha256: str
    count: int
    slots: tuple[int, int, int, int]
    msidconv_values: tuple[int, int, int, int]
    status_active: tuple[bool, bool, bool, bool]
    movie_values: tuple[int, ...]
    scalar_fields: dict
    callback_rows: tuple[dict, ...]
    fx6_extra_nonnull: tuple[dict, ...]
    rejected: tuple[str, ...]
    preview_0x1f8: bytes | None


def _index():
    blob = CALLBACK_INDEX.read_bytes()
    if hashlib.sha256(blob).hexdigest() != CALLBACK_INDEX_SHA:
        raise Rejected("callback field index SHA drift")
    rows = json.loads(blob)["symbol_mapping"]
    common = [r for r in rows if r["fx3_offset"] is not None]
    if len(common) != 57 or {int(r["fx3_offset"], 16) for r in common} != set(range(8, 0x1d0, 8)):
        raise Rejected("FX3 57 callback loads are not a complete unique 0x8..0x1c8 range")
    if any(r["fx6_offset"] is None for r in common):
        raise Rejected("FX6 matching symbol missing")
    return rows, common


def project(raw: bytes, *, writer_mode: str | None = None,
            mode_source: str | None = None) -> Projection:
    """保留原字节做结构预览；模式只能为有来源的 Xavcs，不能给自然快照猜模式。"""
    if type(raw) is not bytes or len(raw) != 0x290:
        raise Rejected("exact immutable 0x290 original snapshot required")
    rows, common = _index()
    count = struct.unpack_from("<I", raw, 0x268)[0]
    slots = struct.unpack_from("<4I", raw, 0x26c)
    skip_id, method = struct.unpack_from("<II", raw, 0x27c)
    node = raw[0x284:0x28a]
    source_u16 = struct.unpack_from("<H", raw, 0x28a)[0]
    tail = struct.unpack_from("<I", raw, 0x28c)[0]
    reasons = []
    if not 1 <= count <= 4:
        reasons.append(f"count_outside_verified_1_to_4:{count}")
    if count <= 4 and any(v == 0xffff for v in slots[:count]):
        reasons.append("active_slot_is_ffff_sentinel")
    if count <= 4 and len(set(slots[:count])) != count:
        reasons.append("duplicate_active_slot_id")
    # Both original InitStatus functions read all four slots, regardless of count.
    status = tuple(x != 0xffff for x in slots)
    msid = tuple(slots[i] if i < count else 0xffff for i in range(4)) if count <= 4 else (0xffff,) * 4
    preview = bytearray(0x1f8)
    preview[:8] = raw[:8]  # diagnostic-only prefix, not a vptr
    cb = []
    for r in sorted(common, key=lambda r: int(r["fx3_offset"], 16)):
        dst, src = int(r["fx3_offset"], 16), int(r["fx6_offset"], 16)
        value = struct.unpack_from("<Q", raw, src)[0]
        preview[dst:dst + 8] = raw[src:src + 8]
        policy = SUPPORT.get(r["symbol"], "no_verified_callback_payload_or_lifecycle")
        cb.append({"symbol": r["symbol"], "fx3_offset": dst, "fx6_offset": src,
                   "source_pointer": f"0x{value:x}", "policy": policy,
                   "source_null": value == 0})
        if value:
            reasons.append(f"callback_requires_guest_binding:{r['symbol']}:{policy}")
        # Source-null is recorded as an original value. We do not zero any non-null slot.
    extras = []
    for r in rows:
        if r["fx3_offset"] is not None:
            continue
        src = int(r["fx6_offset"], 16)
        value = struct.unpack_from("<Q", raw, src)[0]
        if value:
            extras.append({"symbol": r["symbol"], "fx6_offset": src,
                           "source_pointer": f"0x{value:x}"})
    if extras:
        reasons.append(f"fx6_nonnull_callbacks_without_fx3_slot:{len(extras)}")
    struct.pack_into("<I4I", preview, 0x1d0, count, *slots)
    preview[0x1e4:0x1f2] = raw[0x27c:0x28a]
    preview[0x1f4:0x1f8] = raw[0x28c:0x290]
    if writer_mode is None:
        reasons.append("writer_mode_unobserved;u16_1440_to_780_not_authorized")
        preview_bytes = None
    elif writer_mode == "fx6_xavcs" and mode_source in ("symbolic_fixture", "verified_movie_mode_observation"):
        struct.pack_into("<H", preview, 0x1f2, 780)
        # This output remains host preview; no true guest thunk addresses are present.
        if mode_source == "symbolic_fixture":
            reasons.append("writer_mode_is_fixture_not_natural")
        preview_bytes = bytes(preview)
    else:
        reasons.append(f"writer_mode_not_portable:{writer_mode}:{mode_source}")
        preview_bytes = None
    if count <= 4 and slots[count:] and any(x == 0 for x in slots[count:]):
        reasons.append("tail_zero_slots_active_in_both_status_consumers;FX3_hardware_ID_semantics_unknown")
    reasons.append("FX3_Init_side_effects_OSAL_Backup_CAPID_DMA_not_executed_or_verified")
    return Projection(hashlib.sha256(raw).hexdigest(), count, slots, msid, status,
                      slots[:count] if count <= 4 else (),
                      {"skip_id": skip_id, "method": method, "node_hex": node.hex(),
                       "source_u16": source_u16, "tail": tail}, tuple(cb), tuple(extras),
                      tuple(dict.fromkeys(reasons)), preview_bytes)


def convert_for_guest(raw: bytes, *, writer_mode: str | None = None,
                      mode_source: str | None = None) -> bytes:
    """目前拒绝真实调用；绝不把结构预览、原 AP 指针或空指针当 thunk。"""
    p = project(raw, writer_mode=writer_mode, mode_source=mode_source)
    raise Rejected(";".join(p.rejected))
