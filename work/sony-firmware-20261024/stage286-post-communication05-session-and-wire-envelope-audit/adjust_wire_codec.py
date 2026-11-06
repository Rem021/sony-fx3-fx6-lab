"""Offline pure-CPU wire-envelope codec and validator for AdjustControlFunc (pFunc=0x0040, category=0x1001).

Never performs USB/IOKit/root operations or executes camera code.
"""
from dataclasses import dataclass
import struct

PFUNC_ADJUST_CONTROL = 0x0040
CATEGORY_JIRITSU = 0x1001

CMD_SET_FILE_PATH = 0x000F
CMD_SET_FILE2 = 0x0010
CMD_GET_FILE2 = 0x0011

REQ_VERSION_ADJUST = 2
RESP_VERSION_STOCK = 3
RESP_RES_OK = 1

OP_FILESYSTEM_MOUNT = 0x00
OP_MEDIA_MOUNT = 0x01
OP_RAM_CACHE_SLOT = 0xFF

MAX_INLINE_ADJUST_PAYLOAD = 0x124  # 292 bytes in TransactionStart (0xfc74)
MAX_SET_FILE_PATH_BYTES = 0x1FF    # 511 bytes in adj_cmd_set_file_path (0x89d4)
MAX_RAM_SLOT_PAYLOAD = 0x500000    # 5 MiB in adj_cmd_set_file2 op 0xFF (0x962c)


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


@dataclass(frozen=True)
class AdjustRequestEnvelope:
    seq: int
    command: int
    inner_payload: bytes

    def to_wire_bytes(self) -> bytes:
        _need(isinstance(self.seq, int) and 0 < self.seq <= 0xFFFF, 'invalid sequence number')
        _need(self.command in (CMD_SET_FILE_PATH, CMD_SET_FILE2, CMD_GET_FILE2), 'unsupported AdjustControl command')
        _need(isinstance(self.inner_payload, bytes) and len(self.inner_payload) >= 1, 'empty inner payload')
        body_size = 4 + len(self.inner_payload)
        _need(body_size <= 0x100000, 'request body exceeds SenserThread 1 MiB limit (0xb8a0)')
        header = struct.pack(
            '<IHHBBBB',
            body_size,
            PFUNC_ADJUST_CONTROL,
            self.seq,
            REQ_VERSION_ADJUST,
            0,
            0,
            0,
        )
        selector = struct.pack('<HH', CATEGORY_JIRITSU, self.command)
        return header + selector + self.inner_payload


def build_ram_slot_set_request(seq: int, slot: int, mode: int, data: bytes) -> AdjustRequestEnvelope:
    """Build an in-memory slot (operation=0xFF) SET_FILE2 request envelope (no sys_mount, no filesystem I/O)."""
    _need(isinstance(slot, int) and 0 <= slot <= 0xFF, 'slot out of range')
    _need(isinstance(mode, int) and 0 <= mode <= 0x11, 'mode out of range for operation 0xFF (0x9630)')
    _need(isinstance(data, bytes) and 1 <= len(data) <= MAX_RAM_SLOT_PAYLOAD, 'data length out of bounds')
    inner = bytes([OP_RAM_CACHE_SLOT, slot, mode]) + data
    return AdjustRequestEnvelope(seq=seq, command=CMD_SET_FILE2, inner_payload=inner)


def build_ram_slot_get_request(seq: int, slot: int, mode: int = 0) -> AdjustRequestEnvelope:
    """Build an in-memory slot (operation=0xFF) GET_FILE2 request envelope (no sys_mount, no filesystem I/O)."""
    _need(isinstance(slot, int) and 0 <= slot <= 0xFF, 'slot out of range')
    _need(isinstance(mode, int) and 0 <= mode <= 0x11, 'mode out of range')
    inner = bytes([OP_RAM_CACHE_SLOT, slot, mode])
    return AdjustRequestEnvelope(seq=seq, command=CMD_GET_FILE2, inner_payload=inner)


def parse_adjust_response_header(header: bytes, expected_seq: int, max_payload_bytes: int = 1024) -> int:
    """Validate 12-byte stock SenserPacket response header (version=3 at offset 8, res=1 at offset 11)."""
    _need(isinstance(header, bytes) and len(header) == 12, 'response header must be 12 bytes')
    _need(isinstance(expected_seq, int) and 0 < expected_seq <= 0xFFFF, 'invalid expected_seq')
    _need(isinstance(max_payload_bytes, int) and 4 <= max_payload_bytes <= 0x100000, 'invalid max_payload_bytes')
    size, pfunc, seq, version, flag, reserved, res = struct.unpack('<IHHBBBB', header)
    _need(pfunc == PFUNC_ADJUST_CONTROL, f'unexpected response pFunc: {hex(pfunc)}')
    _need(seq == expected_seq, f'sequence mismatch: got {seq}, expected {expected_seq}')
    _need(version == RESP_VERSION_STOCK, f'unexpected response version: {version} (stock SendResponse writes 3)')
    _need(flag == 0 and reserved == 0, 'non-zero response flag/reserved byte')
    _need(res == RESP_RES_OK, f'non-ok Senser response res byte: {res}')
    _need(4 <= size <= max_payload_bytes, f'response payload size {size} outside bounded [4, {max_payload_bytes}]')
    return size


def parse_adjust_response_body(body: bytes, expected_size: int) -> dict:
    """Validate AdjustControl response body (4-byte little-endian status word followed by optional data)."""
    _need(isinstance(body, bytes) and len(body) == expected_size and expected_size >= 4, 'response body length mismatch')
    native_status = struct.unpack_from('<I', body, 0)[0]
    _need(native_status == 0, f'non-zero native business status: {hex(native_status)}')
    payload = body[4:]
    return dict(
        native_status=native_status,
        payload_bytes=len(payload),
        payload_sha256_hex=__import__('hashlib').sha256(payload).hexdigest(),
    )
