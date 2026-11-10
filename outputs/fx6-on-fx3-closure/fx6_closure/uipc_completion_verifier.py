"""P5 & P6 UIPC Completion Protocol Codec and Unicorn AArch64 `send_and_wait_cmp_i` Verifier.

Covers:
1. Exact byte-level UIPC BB request matching and 12-byte completion synthesis on target queue
   `0x92840747`:
   - P5 (`0x032d -> 0x132d`, Audio / HDMI pre-init sync):
     10B request `0d202d030a0001800000` -> 12B completion `0d202d130c00018000005800`
     (`raw_status = 0x00580000`, mapped to `0` by `appFw.so` `0x20edd1c`).
   - P6 (`0x0400 -> 0x1400`, `0x0402 -> 0x1402`, `0x0404 -> 0x1404`, `0x0152 -> 0x1152`,
     Timecode / UB / VDF Peaking sync):
     Exact header/length/payload validation -> 12B completion with `raw_status = 0x00000000`.
2. Unicorn AArch64 instruction-level verification of FX6 `appFw.so`:
   - Direct execution of `send_and_wait_cmp_i` (`0x20ef604`..`0x20ef7ec`) and real caller wrappers
     (`0x20f158c`, `0x20f4450`, `0x20f43b0`, `0x20f41f4`, `0x20efe3c`) + status mapper `0x20edd1c`
     intercepting PLT stubs (`osal_valloc_msg_wait`, `osal_set_msg_src`, `osal_snd_msg`,
     `osal_rcv_msg_tmo`, `osal_free_msg`, `osal_subsystem_id`, `osal_dynamic_id`,
     `osal_stat_msgq`, `memcpy`).
   - Proves 100% clean completion across all 5 opcodes with zero visits to `0x20ef7b4`
     (line `1075 = 0x433` assertion) and zero leaked OSAL buffers.
   - Proves deterministic fault capture when `osal_snd_msg` returns non-zero (jumping to
     `0x20ef7b4` / line `1075` assertion) or when completion status is abnormal (strict pre-commit
     rejection to line `1075` assertion, or raw status propagation to `0x20ede04` non-zero error
     mapping `0x6f` / `0x80`).
"""

from __future__ import annotations

import struct
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_LOCAL_UNICORN_SITE = Path(
    "/Volumes/KAFU2T/AI/Orca/Worktrees/Phayen/dugong/work/firmware-reverse-2026-10-22/"
    "tools/venv/lib/python3.14/site-packages"
)
try:
    import unicorn as U
    from unicorn import arm64_const as A
except ImportError:
    if _LOCAL_UNICORN_SITE.is_dir() and str(_LOCAL_UNICORN_SITE) not in sys.path:
        sys.path.append(str(_LOCAL_UNICORN_SITE))
    import unicorn as U
    from unicorn import arm64_const as A


UIPC_BB_TARGET_QUEUE = 0x92840747
UIPC_BB_HEADER_MAGIC = 0x200D
UIPC_BB_HEADER_FLAGS = 0x8001
UIPC_BB_COMPLETION_MASK = 0x1000
UIPC_BB_COMPLETION_BYTES = 12

P5_AUDIO_HDMI_CMD = 0x032D
P5_AUDIO_HDMI_CMP = 0x132D
P5_AUDIO_HDMI_STATUS_OK = 0x00580000
P5_CANONICAL_REQ_HEX = "0d202d030a0001800000"
P5_CANONICAL_CMP_HEX = "0d202d130c00018000005800"

P6_TC_MODE_CMD = 0x0400
P6_TC_UB_MODE_CMD = 0x0402
P6_TC_UB_VAL_CMD = 0x0404
P6_VDF_PEAKING_CMD = 0x0152

# `appFw.so` VMA constants
SEND_AND_WAIT_CMP_ENTRY_VMA = 0x20EF604
SEND_AND_WAIT_CMP_TAIL_VMA = 0x20EF6F4
SEND_AND_WAIT_CMP_LOOP_BACK_VMA = 0x20EF7EC
SEND_AND_WAIT_CMP_ASSERT_1075_VMA = 0x20EF7B4  # mov w1, #0x433 (1075)
STATUS_MAPPER_ENTRY_VMA = 0x20EDD1C
STATUS_MAPPER_ERROR_BRANCH_VMA = 0x20EDE04
ASSERT_HANDLER_VMA = 0x2167784
LOG_HELPER_VMA = 0x21BB120

# Caller wrapper VMAs in `appFw.so`
CALLER_VMA_BY_OPCODE: Dict[int, int] = {
    P5_AUDIO_HDMI_CMD: 0x20F158C,
    P6_TC_MODE_CMD: 0x20F4450,
    P6_TC_UB_MODE_CMD: 0x20F43B0,
    P6_TC_UB_VAL_CMD: 0x20F41F4,
    P6_VDF_PEAKING_CMD: 0x20EFE3C,
}

# PLT stub VMAs in `appFw.so`
PLT_MEMCPY = 0xB17880
PLT_OSAL_SET_MSG_SRC = 0xB17C70
PLT_OSAL_STAT_MSGQ = 0xB183C0
PLT_OSAL_SUBSYSTEM_ID = 0xB18D60
PLT_OSAL_VALLOC_MSG_WAIT = 0xB197E0
PLT_OSAL_DYNAMIC_ID = 0xB19900
PLT_OSAL_FREE_MSG = 0xB19D40
PLT_OSAL_RCV_MSG_TMO = 0xB19EC0
PLT_OSAL_SND_MSG = 0xB1A120

ALL_INTERCEPTED_PLTS: Tuple[int, ...] = (
    PLT_MEMCPY,
    PLT_OSAL_SET_MSG_SRC,
    PLT_OSAL_STAT_MSGQ,
    PLT_OSAL_SUBSYSTEM_ID,
    PLT_OSAL_VALLOC_MSG_WAIT,
    PLT_OSAL_DYNAMIC_ID,
    PLT_OSAL_FREE_MSG,
    PLT_OSAL_RCV_MSG_TMO,
    PLT_OSAL_SND_MSG,
)


class UipcProtocolError(ValueError):
    """Raised when a UIPC BB request or completion packet violates byte-level schema."""


@dataclass(frozen=True)
class UipcOpcodeRule:
    patch_group: str
    request_opcode: int
    completion_opcode: int
    request_size: int
    default_raw_status: int
    canonical_request_hex: str
    canonical_completion_hex: str
    description: str


UIPC_P5_P6_RULES: Dict[int, UipcOpcodeRule] = {
    P5_AUDIO_HDMI_CMD: UipcOpcodeRule(
        patch_group="P5",
        request_opcode=0x032D,
        completion_opcode=0x132D,
        request_size=10,
        default_raw_status=P5_AUDIO_HDMI_STATUS_OK,
        canonical_request_hex=P5_CANONICAL_REQ_HEX,
        canonical_completion_hex=P5_CANONICAL_CMP_HEX,
        description="Audio / HDMI pre-init synchronization",
    ),
    P6_TC_MODE_CMD: UipcOpcodeRule(
        patch_group="P6",
        request_opcode=0x0400,
        completion_opcode=0x1400,
        request_size=10,
        default_raw_status=0x00000000,
        canonical_request_hex="0d2000040a0001800000",
        canonical_completion_hex="0d2000140c00018000000000",
        description="Timecode run-mode synchronization",
    ),
    P6_TC_UB_MODE_CMD: UipcOpcodeRule(
        patch_group="P6",
        request_opcode=0x0402,
        completion_opcode=0x1402,
        request_size=10,
        default_raw_status=0x00000000,
        canonical_request_hex="0d2002040a0001800000",
        canonical_completion_hex="0d2002140c00018000000000",
        description="Timecode / User-Bit mode synchronization",
    ),
    P6_TC_UB_VAL_CMD: UipcOpcodeRule(
        patch_group="P6",
        request_opcode=0x0404,
        completion_opcode=0x1404,
        request_size=12,
        default_raw_status=0x00000000,
        canonical_request_hex="0d2004040c00018000000000",
        canonical_completion_hex="0d2004140c00018000000000",
        description="Timecode / User-Bit 4-byte value synchronization",
    ),
    P6_VDF_PEAKING_CMD: UipcOpcodeRule(
        patch_group="P6",
        request_opcode=0x0152,
        completion_opcode=0x1152,
        request_size=14,
        default_raw_status=0x00000000,
        canonical_request_hex="0d2052010e000180030020000000",
        canonical_completion_hex="0d2052110c00018000000000",
        description="VDF peaking configuration synchronization",
    ),
}


@dataclass(frozen=True)
class DecodedUipcRequest:
    destination_queue: int
    magic: int
    opcode: int
    length: int
    flags: int
    payload: bytes
    patch_group: str


@dataclass(frozen=True)
class DecodedUipcCompletion:
    magic: int
    completion_opcode: int
    length: int
    flags: int
    raw_status: int


@dataclass(frozen=True)
class UipcUnicornCaseResult:
    patch_group: str
    request_opcode: int
    completion_opcode: int
    request_hex: str
    completion_hex: str
    completed_normally: bool
    hit_assert_1075_vma: bool
    assert_hit: bool
    assert_line: int
    status_error_branch_hit: bool
    mapped_ap_status: Optional[int]
    osal_alloc_count: int
    osal_free_count: int
    dynamic_queue_allocated: bool
    dynamic_queue_released: bool
    sp_preserved: bool


@dataclass(frozen=True)
class UipcP5P6AuditSummary:
    positive_direct_cases: Tuple[UipcUnicornCaseResult, ...]
    positive_wrapper_cases: Tuple[UipcUnicornCaseResult, ...]
    snd_error_case: UipcUnicornCaseResult
    strict_bad_status_case: UipcUnicornCaseResult
    raw_bad_status_wrapper_case: UipcUnicornCaseResult
    all_positive_passed: bool
    all_negative_captured: bool


def parse_and_match_uipc_request(destination_queue: int, request_bytes: bytes) -> DecodedUipcRequest:
    """Strictly parse and validate a P5/P6 UIPC BB request packet on queue `0x92840747`."""
    if destination_queue != UIPC_BB_TARGET_QUEUE:
        raise UipcProtocolError(
            f"Unsupported UIPC destination queue 0x{destination_queue:08x} (expected 0x{UIPC_BB_TARGET_QUEUE:08x})"
        )
    if len(request_bytes) < 8:
        raise UipcProtocolError(f"UIPC request too short ({len(request_bytes)} bytes < 8)")

    magic, opcode, declared_len, flags = struct.unpack_from("<HHHH", request_bytes, 0)
    if magic != UIPC_BB_HEADER_MAGIC:
        raise UipcProtocolError(f"Invalid UIPC header magic 0x{magic:04x} (expected 0x{UIPC_BB_HEADER_MAGIC:04x})")
    if flags != UIPC_BB_HEADER_FLAGS:
        raise UipcProtocolError(f"Invalid UIPC header flags 0x{flags:04x} (expected 0x{UIPC_BB_HEADER_FLAGS:04x})")
    if declared_len != len(request_bytes):
        raise UipcProtocolError(
            f"UIPC length mismatch: header declares {declared_len}B, buffer has {len(request_bytes)}B"
        )

    rule = UIPC_P5_P6_RULES.get(opcode)
    if rule is None:
        raise UipcProtocolError(f"Unsupported UIPC BB opcode 0x{opcode:04x}")
    if len(request_bytes) != rule.request_size:
        raise UipcProtocolError(
            f"Opcode 0x{opcode:04x} requires {rule.request_size}B request, got {len(request_bytes)}B"
        )

    payload = request_bytes[8:]
    if opcode == P5_AUDIO_HDMI_CMD:
        if payload[0] not in (0, 1) or payload[1] != 0:
            raise UipcProtocolError(f"Invalid P5 0x032d payload bytes: {payload.hex()}")
    elif opcode == P6_TC_MODE_CMD:
        if payload[0] not in (0, 1, 2) or payload[1] != 0:
            raise UipcProtocolError(f"Invalid P6 0x0400 payload bytes: {payload.hex()}")
    elif opcode == P6_TC_UB_MODE_CMD:
        if payload[0] not in (0, 1) or payload[1] != 0:
            raise UipcProtocolError(f"Invalid P6 0x0402 payload bytes: {payload.hex()}")
    elif opcode == P6_VDF_PEAKING_CMD:
        if payload[0] != 0x03 or payload[1] not in (0, 1) or payload[2] != 0x20 or payload[5] != 0x00:
            raise UipcProtocolError(f"Invalid P6 0x0152 payload bytes: {payload.hex()}")

    return DecodedUipcRequest(
        destination_queue=destination_queue,
        magic=magic,
        opcode=opcode,
        length=declared_len,
        flags=flags,
        payload=payload,
        patch_group=rule.patch_group,
    )


def decode_uipc_completion_packet(
    completion_bytes: bytes,
    expected_request_opcode: Optional[int] = None,
    require_ok_status: bool = True,
) -> DecodedUipcCompletion:
    """Decode and validate a 12-byte UIPC BB completion packet."""
    if len(completion_bytes) != UIPC_BB_COMPLETION_BYTES:
        raise UipcProtocolError(
            f"Completion packet must be {UIPC_BB_COMPLETION_BYTES}B, got {len(completion_bytes)}B"
        )
    magic, cmp_opcode, length, flags, raw_status = struct.unpack("<HHHHI", completion_bytes)
    if magic != UIPC_BB_HEADER_MAGIC or length != UIPC_BB_COMPLETION_BYTES or flags != UIPC_BB_HEADER_FLAGS:
        raise UipcProtocolError(f"Malformed 12B completion header: {completion_bytes.hex()}")
    if (cmp_opcode & UIPC_BB_COMPLETION_MASK) == 0:
        raise UipcProtocolError(f"Completion opcode 0x{cmp_opcode:04x} missing 0x1000 completion bit")

    if expected_request_opcode is not None:
        expected_cmp = expected_request_opcode | UIPC_BB_COMPLETION_MASK
        if cmp_opcode != expected_cmp:
            raise UipcProtocolError(
                f"Completion opcode mismatch: got 0x{cmp_opcode:04x}, expected 0x{expected_cmp:04x}"
            )
    if require_ok_status and raw_status not in (0x00000000, P5_AUDIO_HDMI_STATUS_OK):
        raise UipcProtocolError(f"Abnormal UIPC completion raw_status 0x{raw_status:08x}")

    return DecodedUipcCompletion(
        magic=magic,
        completion_opcode=cmp_opcode,
        length=length,
        flags=flags,
        raw_status=raw_status,
    )


def synthesize_uipc_completion(
    destination_queue: int,
    request_bytes: bytes,
    status_override: Optional[int] = None,
    strict_status_check: bool = True,
) -> bytes:
    """Match a P5/P6 UIPC request and synthesize its exact 12-byte completion packet."""
    decoded = parse_and_match_uipc_request(destination_queue, request_bytes)
    rule = UIPC_P5_P6_RULES[decoded.opcode]
    raw_status = rule.default_raw_status if status_override is None else (status_override & 0xFFFFFFFF)
    pkt = struct.pack(
        "<HHHHI",
        UIPC_BB_HEADER_MAGIC,
        rule.completion_opcode,
        UIPC_BB_COMPLETION_BYTES,
        UIPC_BB_HEADER_FLAGS,
        raw_status,
    )
    decode_uipc_completion_packet(
        pkt,
        expected_request_opcode=decoded.opcode,
        require_ok_status=strict_status_check,
    )
    return pkt


def _setup_appfw_uipc_unicorn(
    appfw_image: bytes,
    force_snd_rc: Optional[int] = None,
    status_override: Optional[int] = None,
    strict_status_check: bool = True,
) -> Tuple[U.Uc, Dict[str, object]]:
    """Map `appFw.so` `send_and_wait_cmp_i`, caller wrappers, status mapper, and PLT hooks."""
    mu = U.Uc(U.UC_ARCH_ARM64, U.UC_MODE_ARM)

    # Map .text slice covering 0x20edd1c .. 0x20f4fff
    text_base = 0x20ED000
    text_size = 0x8000
    mu.mem_map(text_base, text_size, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(text_base, appfw_image[text_base : text_base + text_size])

    # Map .rodata slice covering format/file strings referenced by adrp (0x259c000 .. 0x2604000)
    ro_base = 0x259C000
    ro_size = 0x68000
    mu.mem_map(ro_base, ro_size, U.UC_PROT_READ)
    mu.mem_write(ro_base, appfw_image[ro_base : ro_base + ro_size])

    # Map assertion entry (0x2167784) & internal log helper (0x21bb120)
    mu.mem_map(0x2167000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(0x2167000, appfw_image[0x2167000:0x2168000])

    mu.mem_map(0x21BB000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(LOG_HELPER_VMA, struct.pack("<II", 0x52800000, 0xD65F03C0))

    # Map PLT stub page (0xb17000 .. 0xb1b000) with `ret` at each intercepted PLT slot
    plt_base = 0xB17000
    plt_size = 0x4000
    mu.mem_map(plt_base, plt_size, U.UC_PROT_READ | U.UC_PROT_EXEC)
    for plt_addr in ALL_INTERCEPTED_PLTS:
        mu.mem_write(plt_addr, struct.pack("<I", 0xD65F03C0))

    # Stack, caller I/O scratch, OSAL message pool, and return sentinel
    mu.mem_map(0x70000000, 0x10000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(0x71000000, 0x4000, U.UC_PROT_READ | U.UC_PROT_WRITE)
    mu.mem_map(0x72000000, 0x1000, U.UC_PROT_READ | U.UC_PROT_EXEC)
    mu.mem_write(0x72000000, struct.pack("<I", 0xD503201F))

    mu.reg_write(A.UC_ARM64_REG_CPACR_EL1, 3 << 20)

    pool_cursor = [0x71001000]
    allocated_msgs: Dict[int, Dict[str, int]] = {}
    reply_queues: Dict[int, List[int]] = {}
    dyn_qid = 0x81CF6196

    state: Dict[str, object] = {
        "hit_1075_vma": False,
        "assert_hit": False,
        "assert_line": 0,
        "status_error_branch_hit": False,
        "alloc_count": 0,
        "free_count": 0,
        "dyn_alloc": False,
        "dyn_free": False,
        "last_sent_hex": "",
        "last_cmp_hex": "",
    }

    def _alloc_pool(size: int, owner_qid: int) -> int:
        addr = pool_cursor[0]
        pool_cursor[0] += (max(size, 16) + 0x3F) & ~0x3F
        allocated_msgs[addr] = {"size": size, "src": 0, "owner": owner_qid, "freed": 0}
        state["alloc_count"] = int(state["alloc_count"]) + 1
        return addr

    def _code_hook(uc: U.Uc, address: int, _size: int, _ud: object) -> None:
        if address == SEND_AND_WAIT_CMP_ASSERT_1075_VMA:
            state["hit_1075_vma"] = True
        elif address == STATUS_MAPPER_ERROR_BRANCH_VMA:
            state["status_error_branch_hit"] = True
        elif address == ASSERT_HANDLER_VMA:
            state["assert_hit"] = True
            state["assert_line"] = uc.reg_read(A.UC_ARM64_REG_W1)
            uc.emu_stop()
        elif address == PLT_OSAL_SUBSYSTEM_ID:
            uc.reg_write(A.UC_ARM64_REG_X0, 0x81CF)
        elif address == PLT_OSAL_DYNAMIC_ID:
            op = uc.reg_read(A.UC_ARM64_REG_W0)
            out_ptr = uc.reg_read(A.UC_ARM64_REG_X2)
            if (op & 0xF8) == 0x28:
                uc.mem_write(out_ptr, struct.pack("<I", dyn_qid))
                reply_queues.setdefault(dyn_qid, [])
                state["dyn_alloc"] = True
            elif (op & 0xF8) == 0x48:
                state["dyn_free"] = True
            uc.reg_write(A.UC_ARM64_REG_X0, 0)
        elif address == PLT_OSAL_STAT_MSGQ:
            stat_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
            q = uc.reg_read(A.UC_ARM64_REG_W0)
            pending = len(reply_queues.get(q, []))
            uc.mem_write(stat_ptr, struct.pack("<I", pending))
            uc.reg_write(A.UC_ARM64_REG_X0, 0)
        elif address == PLT_OSAL_VALLOC_MSG_WAIT:
            dst_q = uc.reg_read(A.UC_ARM64_REG_W0)
            out_msg_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
            sz = uc.reg_read(A.UC_ARM64_REG_W2)
            buf_addr = _alloc_pool(sz, dst_q)
            uc.mem_write(out_msg_ptr, struct.pack("<Q", buf_addr))
            uc.reg_write(A.UC_ARM64_REG_X0, 0)
        elif address == PLT_MEMCPY:
            dst = uc.reg_read(A.UC_ARM64_REG_X0)
            src = uc.reg_read(A.UC_ARM64_REG_X1)
            n = uc.reg_read(A.UC_ARM64_REG_X2)
            if n > 0:
                uc.mem_write(dst, bytes(uc.mem_read(src, n)))
            uc.reg_write(A.UC_ARM64_REG_X0, dst)
        elif address == PLT_OSAL_SET_MSG_SRC:
            msg_ptr = uc.reg_read(A.UC_ARM64_REG_X0)
            src_q = uc.reg_read(A.UC_ARM64_REG_W1)
            if msg_ptr in allocated_msgs:
                allocated_msgs[msg_ptr]["src"] = src_q
            uc.reg_write(A.UC_ARM64_REG_X0, 0)
        elif address == PLT_OSAL_SND_MSG:
            dst_q = uc.reg_read(A.UC_ARM64_REG_W0)
            msg_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
            meta = allocated_msgs.get(msg_ptr)
            if meta is None or meta["freed"]:
                uc.reg_write(A.UC_ARM64_REG_X0, 0xFFFFFFEA)  # -22
                return
            req_raw = bytes(uc.mem_read(msg_ptr, meta["size"]))
            state["last_sent_hex"] = req_raw.hex()
            src_q = meta["src"]

            if force_snd_rc is not None:
                uc.reg_write(A.UC_ARM64_REG_X0, force_snd_rc & 0xFFFFFFFF)
                return

            try:
                cmp_bytes = synthesize_uipc_completion(
                    dst_q,
                    req_raw,
                    status_override=status_override,
                    strict_status_check=strict_status_check,
                )
            except UipcProtocolError:
                uc.reg_write(A.UC_ARM64_REG_X0, 0xFFFFFFF9)  # -7
                return

            # Consume request buffer on destination side and enqueue 12B completion to src_q
            meta["freed"] = 1
            state["free_count"] = int(state["free_count"]) + 1

            reply_addr = _alloc_pool(len(cmp_bytes), src_q)
            uc.mem_write(reply_addr, cmp_bytes)
            allocated_msgs[reply_addr]["src"] = dst_q
            reply_queues.setdefault(src_q, []).append(reply_addr)
            state["last_cmp_hex"] = cmp_bytes.hex()
            uc.reg_write(A.UC_ARM64_REG_X0, 0)
        elif address == PLT_OSAL_RCV_MSG_TMO:
            q = uc.reg_read(A.UC_ARM64_REG_W0)
            out_rx_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
            q_list = reply_queues.get(q, [])
            if not q_list:
                uc.reg_write(A.UC_ARM64_REG_X0, 0xFFFFFF92)  # timeout
                return
            rx_addr = q_list.pop(0)
            uc.mem_write(out_rx_ptr, struct.pack("<Q", rx_addr))
            uc.reg_write(A.UC_ARM64_REG_X0, 0)
        elif address == PLT_OSAL_FREE_MSG:
            msg_ptr = uc.reg_read(A.UC_ARM64_REG_X1)
            meta = allocated_msgs.get(msg_ptr)
            if meta is None or meta["freed"]:
                uc.reg_write(A.UC_ARM64_REG_X0, 0xFFFFFFEA)
                return
            meta["freed"] = 1
            state["free_count"] = int(state["free_count"]) + 1
            uc.reg_write(A.UC_ARM64_REG_X0, 0)

    mu.hook_add(U.UC_HOOK_CODE, _code_hook)
    return mu, state


def run_send_and_wait_cmp_unicorn_case(
    appfw_image: bytes,
    request_bytes: bytes,
    destination_queue: int = UIPC_BB_TARGET_QUEUE,
    force_snd_rc: Optional[int] = None,
    status_override: Optional[int] = None,
    strict_status_check: bool = True,
) -> UipcUnicornCaseResult:
    """Execute `send_and_wait_cmp_i` (`0x20ef604`..`0x20ef7ec`) directly in Unicorn AArch64."""
    mu, state = _setup_appfw_uipc_unicorn(
        appfw_image=appfw_image,
        force_snd_rc=force_snd_rc,
        status_override=status_override,
        strict_status_check=strict_status_check,
    )

    init_sp = 0x7000E000
    req_buf = 0x71000000
    resp_buf = 0x71000100
    ret_sentinel = 0x72000000

    mu.mem_write(req_buf, request_bytes)
    mu.mem_write(resp_buf, b"\xaa" * 32)

    mu.reg_write(A.UC_ARM64_REG_SP, init_sp)
    mu.reg_write(A.UC_ARM64_REG_LR, ret_sentinel)
    mu.reg_write(A.UC_ARM64_REG_X0, destination_queue)
    mu.reg_write(A.UC_ARM64_REG_X1, req_buf)
    mu.reg_write(A.UC_ARM64_REG_X2, len(request_bytes))
    mu.reg_write(A.UC_ARM64_REG_X3, resp_buf)
    mu.reg_write(A.UC_ARM64_REG_X4, UIPC_BB_COMPLETION_BYTES)

    mu.emu_start(SEND_AND_WAIT_CMP_ENTRY_VMA, ret_sentinel, count=2000)

    _, req_opcode, _, _ = struct.unpack_from("<HHHH", request_bytes, 0)
    rule = UIPC_P5_P6_RULES.get(req_opcode)
    patch_group = rule.patch_group if rule else "UNKNOWN"
    expected_cmp_op = req_opcode | UIPC_BB_COMPLETION_MASK

    assert_hit = bool(state["assert_hit"])
    resp_hex = "" if assert_hit else bytes(mu.mem_read(resp_buf, UIPC_BB_COMPLETION_BYTES)).hex()
    sp_ok = not assert_hit and (mu.reg_read(A.UC_ARM64_REG_SP) == init_sp)

    return UipcUnicornCaseResult(
        patch_group=patch_group,
        request_opcode=req_opcode,
        completion_opcode=expected_cmp_op,
        request_hex=request_bytes.hex(),
        completion_hex=resp_hex,
        completed_normally=(not assert_hit and sp_ok),
        hit_assert_1075_vma=bool(state["hit_1075_vma"]),
        assert_hit=assert_hit,
        assert_line=int(state["assert_line"]),
        status_error_branch_hit=bool(state["status_error_branch_hit"]),
        mapped_ap_status=None,
        osal_alloc_count=int(state["alloc_count"]),
        osal_free_count=int(state["free_count"]),
        dynamic_queue_allocated=bool(state["dyn_alloc"]),
        dynamic_queue_released=bool(state["dyn_free"]),
        sp_preserved=sp_ok,
    )


def run_caller_wrapper_unicorn_case(
    appfw_image: bytes,
    opcode: int,
    force_snd_rc: Optional[int] = None,
    status_override: Optional[int] = None,
    strict_status_check: bool = True,
) -> UipcUnicornCaseResult:
    """Execute the real `appFw.so` caller wrapper + `send_and_wait_cmp_i` + `0x20edd1c` mapper."""
    caller_vma = CALLER_VMA_BY_OPCODE[opcode]
    rule = UIPC_P5_P6_RULES[opcode]
    mu, state = _setup_appfw_uipc_unicorn(
        appfw_image=appfw_image,
        force_snd_rc=force_snd_rc,
        status_override=status_override,
        strict_status_check=strict_status_check,
    )

    init_sp = 0x7000E000
    arg_struct = 0x71000200
    out_status_ptr = 0x71000280
    ret_sentinel = 0x72000000

    # Zero-initialized caller input struct produces canonical valid request for all 5 wrappers
    # (for 0x0152 @ 0x20efe3c, [x0+8] == 4 selects the clean zero-flag path matching canonical_request_hex)
    mu.mem_write(arg_struct, b"\x00" * 32)
    if opcode == P6_VDF_PEAKING_CMD:
        mu.mem_write(arg_struct + 8, struct.pack("<I", 4))
    mu.mem_write(out_status_ptr, struct.pack("<I", 0xDEADBEEF))

    mu.reg_write(A.UC_ARM64_REG_SP, init_sp)
    mu.reg_write(A.UC_ARM64_REG_LR, ret_sentinel)
    mu.reg_write(A.UC_ARM64_REG_X0, arg_struct)
    mu.reg_write(A.UC_ARM64_REG_X1, out_status_ptr)

    mu.emu_start(caller_vma, ret_sentinel, count=3000)

    assert_hit = bool(state["assert_hit"])
    mapped_status = (
        None
        if assert_hit
        else struct.unpack("<I", bytes(mu.mem_read(out_status_ptr, 4)))[0]
    )
    sp_ok = not assert_hit and (mu.reg_read(A.UC_ARM64_REG_SP) == init_sp)

    return UipcUnicornCaseResult(
        patch_group=rule.patch_group,
        request_opcode=opcode,
        completion_opcode=rule.completion_opcode,
        request_hex=str(state["last_sent_hex"]),
        completion_hex=str(state["last_cmp_hex"]),
        completed_normally=(not assert_hit and sp_ok),
        hit_assert_1075_vma=bool(state["hit_1075_vma"]),
        assert_hit=assert_hit,
        assert_line=int(state["assert_line"]),
        status_error_branch_hit=bool(state["status_error_branch_hit"]),
        mapped_ap_status=mapped_status,
        osal_alloc_count=int(state["alloc_count"]),
        osal_free_count=int(state["free_count"]),
        dynamic_queue_allocated=bool(state["dyn_alloc"]),
        dynamic_queue_released=bool(state["dyn_free"]),
        sp_preserved=sp_ok,
    )


def run_p5_p6_uipc_unicorn_audit(appfw_image: bytes) -> UipcP5P6AuditSummary:
    """Run full positive (5 opcodes x direct + wrapper) and negative fault-capture Unicorn suite."""
    ordered_opcodes = (
        P5_AUDIO_HDMI_CMD,
        P6_TC_MODE_CMD,
        P6_TC_UB_MODE_CMD,
        P6_TC_UB_VAL_CMD,
        P6_VDF_PEAKING_CMD,
    )

    direct_results: List[UipcUnicornCaseResult] = []
    wrapper_results: List[UipcUnicornCaseResult] = []

    for op in ordered_opcodes:
        rule = UIPC_P5_P6_RULES[op]
        req_bytes = bytes.fromhex(rule.canonical_request_hex)
        d_res = run_send_and_wait_cmp_unicorn_case(appfw_image, req_bytes)
        w_res = run_caller_wrapper_unicorn_case(appfw_image, op)
        direct_results.append(d_res)
        wrapper_results.append(w_res)

    # Negative 1: osal_snd_msg returns non-zero (-19 / unrouted queue) -> jumps to 0x20ef7b4 (line 1075)
    snd_err = run_send_and_wait_cmp_unicorn_case(
        appfw_image,
        bytes.fromhex(P5_CANONICAL_REQ_HEX),
        force_snd_rc=-19,
    )

    # Negative 2: strict completion validator blocks abnormal completion status (0xffffffff) before send commit -> 0x20ef7b4 (line 1075)
    strict_bad_status = run_send_and_wait_cmp_unicorn_case(
        appfw_image,
        bytes.fromhex(P5_CANONICAL_REQ_HEX),
        status_override=0xFFFFFFFF,
        strict_status_check=True,
    )

    # Negative 3: raw abnormal completion status (0xffffffff) delivered to caller wrapper -> hits 0x20ede04 error branch & maps to 0x6f
    raw_bad_status_wrapper = run_caller_wrapper_unicorn_case(
        appfw_image,
        P5_AUDIO_HDMI_CMD,
        status_override=0xFFFFFFFF,
        strict_status_check=False,
    )

    pos_ok = all(
        r.completed_normally
        and not r.hit_assert_1075_vma
        and not r.assert_hit
        and r.completion_hex == UIPC_P5_P6_RULES[r.request_opcode].canonical_completion_hex
        and r.osal_alloc_count == r.osal_free_count == 2
        and r.dynamic_queue_allocated
        and r.dynamic_queue_released
        and r.sp_preserved
        for r in direct_results
    ) and all(
        r.completed_normally
        and not r.hit_assert_1075_vma
        and not r.assert_hit
        and not r.status_error_branch_hit
        and r.mapped_ap_status == 0
        and r.request_hex == UIPC_P5_P6_RULES[r.request_opcode].canonical_request_hex
        and r.completion_hex == UIPC_P5_P6_RULES[r.request_opcode].canonical_completion_hex
        for r in wrapper_results
    )

    neg_ok = (
        snd_err.hit_assert_1075_vma
        and snd_err.assert_hit
        and snd_err.assert_line == 1075
        and strict_bad_status.hit_assert_1075_vma
        and strict_bad_status.assert_hit
        and strict_bad_status.assert_line == 1075
        and raw_bad_status_wrapper.completed_normally
        and raw_bad_status_wrapper.status_error_branch_hit
        and raw_bad_status_wrapper.mapped_ap_status == 0x6F
    )

    return UipcP5P6AuditSummary(
        positive_direct_cases=tuple(direct_results),
        positive_wrapper_cases=tuple(wrapper_results),
        snd_error_case=snd_err,
        strict_bad_status_case=strict_bad_status,
        raw_bad_status_wrapper_case=raw_bad_status_wrapper,
        all_positive_passed=pos_ok,
        all_negative_captured=neg_ok,
    )
