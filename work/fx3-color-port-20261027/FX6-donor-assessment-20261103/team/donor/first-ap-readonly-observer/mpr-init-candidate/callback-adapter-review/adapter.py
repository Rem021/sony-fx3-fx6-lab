"""拒绝式 host 字节合同。绝不调用原 ELF、guest 回调或设备。"""
from __future__ import annotations

import hashlib
import importlib.util
import struct
from dataclasses import dataclass
from pathlib import Path


DONOR = Path(__file__).resolve().parents[3]
PROVEN = {
    "poweron": (DONOR / "capid-init-portability/poweron-contract/offline.py",
                "538a2f45bb452032f21ee2a3a6ae9f56f8fcdcfcf5912f750d671d1cd3382782"),
    "timer_record": (DONOR / "capid-init-portability/init-callback-entry-contract/record_subset.py",
                     "cb6c4efe99adfe51ac805da67053e9100af606a6fe3f132e249b66de939c03ea"),
}


class ContractRejected(ValueError):
    pass


def _load_proven(name: str):
    path, expected = PROVEN[name]
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ContractRejected(f"{name} source SHA drift")
    spec = importlib.util.spec_from_file_location("pinned_" + name, path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@dataclass(frozen=True)
class MovieCore:
    kind: str
    fx3_event: int
    fx6_event: int
    common_u32_at_4: int
    common_u32_at_8: int
    common_u32_at_c: int
    userdata_qword_0: int
    userdata_qword_1: int
    userdata_fx6_offset: int
    fx3_payload_len: int = 0x20


MOVIE = {
    "movie_write_finished": (0x1009, 0x1009, 0x778, 0x788, 0x780),
    "movie_auto_divided": (0x1030, 0x1037, 0x770, 0x780, 0x778),
}


def inspect_movie_core(kind: str, raw: bytes) -> MovieCore:
    """仅析出两种 FX3 Notify 已证 32B 记录；不产生 FX6 原生回调入参。"""
    if kind not in MOVIE:
        raise ContractRejected("unknown movie event kind")
    if type(raw) is not bytes or len(raw) != 0x20:
        raise ContractRejected("FX3 SetIssueEvent requires immutable exact 32B snapshot")
    fx3_event, fx6_event, dst, _size, _highest = MOVIE[kind]
    event, a, b, c, user0, user1 = struct.unpack("<IIIIQQ", raw)
    if event != fx3_event:
        raise ContractRejected("event does not match pinned FX3 Notify producer")
    if kind == "movie_auto_divided" and c != 0:
        raise ContractRejected("FX3 AutoDivided Notify zeroes +0xc")
    return MovieCore(kind, fx3_event, fx6_event, a, b, c, user0, user1, dst)


def translate_host_subsets(kind: str, raw: bytes) -> bytes:
    """仅复用既有原字闭合的 host 字节子集；不检验运行态来源或等待者。"""
    if kind in MOVIE:
        inspect_movie_core(kind, raw)
        raise ContractRejected(
            "32B producer lacks FX6 extended flag/path data; cannot construct native callback payload"
        )
    if kind == "poweron":
        try:
            return _load_proven("poweron").translate(raw)
        except ValueError as e:
            raise ContractRejected(str(e)) from e
    if kind == "timer_record":
        try:
            return _load_proven("timer_record").convert_record_timer(raw)
        except ValueError as e:
            raise ContractRejected(str(e)) from e
    raise ContractRejected("callback kind has no proven byte contract")
