"""Host-only wire codec for the Jiritsu read-only payload experiment.

Never performs USB/IOKit/root operations or executes camera code.
The command numbers and payload layout are static inferences from the
FX3 7.02 libJiritsu.so disassembly; the first device session validates them.
"""
from dataclasses import dataclass
import struct

PFUNC_ADJUST_CONTROL = 0x0040
CATEGORY_JIRITSU = 0x1001

CMD_JIRITSU_MODE = 0x0001
CMD_JIRITSU_START = 0x0004
CMD_SET_FILE_PATH = 0x000F
CMD_SET_FILE2 = 0x0010
CMD_GET_FILE2 = 0x0011

SUPPORTED_COMMANDS = (
    CMD_JIRITSU_MODE,
    CMD_JIRITSU_START,
    CMD_SET_FILE_PATH,
    CMD_SET_FILE2,
    CMD_GET_FILE2,
)

REQ_VERSION_ADJUST = 2
RESP_VERSION_STOCK = 3
RESP_RES_OK = 1

OP_FILESYSTEM_MOUNT = 0x00
OP_RAM_CACHE_SLOT = 0xFF

MAX_BODY_BYTES = 0x100000  # SenserThread 1 MiB request-body limit
MAX_PATH_BYTES = 0x1FF     # adj_cmd_set_file_path limit
MAX_FILE_BYTES = 0x500000  # 5 MiB, same bound used by SET_FILE2 op 0xFF


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


@dataclass(frozen=True)
class AdjustRequestEnvelope:
    seq: int
    command: int
    inner_payload: bytes

    def to_wire_bytes(self) -> bytes:
        _need(isinstance(self.seq, int) and 0 < self.seq <= 0xFFFF, "invalid sequence number")
        _need(self.command in SUPPORTED_COMMANDS, f"unsupported command: {self.command:#x}")
        _need(isinstance(self.inner_payload, bytes) and len(self.inner_payload) >= 1, "empty inner payload")
        body_size = 4 + len(self.inner_payload)
        _need(body_size <= MAX_BODY_BYTES, "request body exceeds SenserThread 1 MiB limit")
        header = struct.pack(
            "<IHHBBBB",
            body_size,
            PFUNC_ADJUST_CONTROL,
            self.seq,
            REQ_VERSION_ADJUST,
            0,
            0,
            0,
        )
        selector = struct.pack("<HH", CATEGORY_JIRITSU, self.command)
        return header + selector + self.inner_payload


def mode_request(seq: int, subcommand: int = 1, mode: int = 4) -> AdjustRequestEnvelope:
    """JIRITSU_MODE (command 1).

    subcommand=1 selects the 'set' branch. mode low nibble 4 selects the
    base string " T" (space + T) in cmd_mode; bit7 is clear so no suffix.
    """
    _need(subcommand in (0, 1), "mode subcommand must be 0 or 1")
    _need(0 <= mode <= 0xFF, "mode byte out of range")
    return AdjustRequestEnvelope(seq=seq, command=CMD_JIRITSU_MODE, inner_payload=bytes([subcommand, mode]))


def start_request(seq: int) -> AdjustRequestEnvelope:
    """JIRITSU_START (command 4). cmd_start requires [cmd+0x28] == 1."""
    return AdjustRequestEnvelope(seq=seq, command=CMD_JIRITSU_START, inner_payload=b"\x01")


def set_file_path_request(seq: int, path: str) -> AdjustRequestEnvelope:
    """SET_FILE_PATH (command 15).

    Binary layout from adj_cmd_set_file_path (0x89b4): byte +0x28 must be 0,
    the path is copied from data+1 with size-1 bytes (NUL included). Therefore
    the inner payload is 00 + path + 00.
    """
    _need(isinstance(path, str) and path.startswith("/tmp/jiritsu/"), "path must be under /tmp/jiritsu/")
    raw_path = path.encode("ascii")
    _need(len(raw_path) <= MAX_PATH_BYTES, "path exceeds 0x1FF bytes")
    return AdjustRequestEnvelope(seq=seq, command=CMD_SET_FILE_PATH, inner_payload=b"\x00" + raw_path + b"\x00")


def set_file2_request(
    seq: int,
    file_bytes: bytes,
    selector: int = 0xFF,
    mode: int = 0x00,
) -> AdjustRequestEnvelope:
    """SET_FILE2 (command 16, filesystem op 0).

    adj_cmd_set_file2 (0x9528): inner bytes are [op=0x00][selector][mode][data...].
    Selector 0x02 is rejected at 0x95a4; 0xFF selects the path set by
    SET_FILE_PATH. The file starts at data+3 (0x96b0/0x9890). jbusy must be
    ABSENT: 0x977c branches to 0x9944 (status 0x10000011) when it exists.
    """
    _need(selector == 0xFF, "selector 0x02 is rejected; use 0xFF for the selected path")
    _need(mode in (0, 1), "mode byte must be 0 or 1")
    _need(isinstance(file_bytes, bytes) and 1 <= len(file_bytes) <= MAX_FILE_BYTES, "file size out of bounds")
    return AdjustRequestEnvelope(
        seq=seq,
        command=CMD_SET_FILE2,
        inner_payload=b"\x00" + bytes([selector, mode]) + file_bytes,
    )


def get_file2_request(seq: int, selector: int = 0xFF, mode: int = 0x00) -> AdjustRequestEnvelope:
    """GET_FILE2 (command 17, filesystem op 0).

    adj_cmd_get_file2 (0x9e74): [op=0x00][selector][mode]; selector is masked
    with ~2 at 0x9efc, so selector 0/2 is rejected; 0xFF selects the current path.
    """
    _need(selector == 0xFF, "selector 0x02 is rejected; use 0xFF for the selected path")
    _need(mode in (0, 1), "mode byte must be 0 or 1")
    return AdjustRequestEnvelope(seq=seq, command=CMD_GET_FILE2, inner_payload=b"\x00\xff\x00")


def parse_adjust_response_header(header: bytes, expected_seq: int, max_payload_bytes: int = MAX_BODY_BYTES) -> int:
    """Validate the 12-byte stock SenserPacket response header and return body size."""
    _need(isinstance(header, bytes) and len(header) == 12, "response header must be 12 bytes")
    _need(isinstance(expected_seq, int) and 0 < expected_seq <= 0xFFFF, "invalid expected_seq")
    size, pfunc, seq, version, flag, reserved, res = struct.unpack("<IHHBBBB", header)
    _need(pfunc == PFUNC_ADJUST_CONTROL, f"unexpected response pFunc: {pfunc:#x}")
    _need(seq == expected_seq, f"sequence mismatch: got {seq}, expected {expected_seq}")
    _need(version == RESP_VERSION_STOCK, f"unexpected response version: {version}")
    _need(flag == 0 and reserved == 0, "non-zero response flag/reserved byte")
    _need(res == RESP_RES_OK, f"non-ok Senser response res byte: {res}")
    _need(4 <= size <= max_payload_bytes, f"response body size {size} outside [4, {max_payload_bytes}]")
    return size


def parse_adjust_response_body(body: bytes, expected_size: int) -> dict:
    """Validate 4-byte little-endian status + optional payload; status must be 0."""
    _need(isinstance(body, bytes) and len(body) == expected_size and expected_size >= 4, "response body length mismatch")
    status = struct.unpack_from("<I", body, 0)[0]
    _need(status == 0, f"non-zero business status: {status:#x}")
    payload = body[4:]
    return dict(
        native_status=status,
        payload=payload,
        payload_bytes=len(payload),
    )


def parse_sector0(payload: bytes) -> dict:
    """Validate a 512-byte Sony partition table read back from /dev/nflasha."""
    _need(len(payload) == 512, f"sector0 must be 512 bytes, got {len(payload)}")
    _need(payload[0:4] == b"8246", "sector0 magic is not 8246")
    _need(payload[4:8] == b"2.00", "sector0 version is not 2.00")
    n_partitions = struct.unpack_from("<I", payload, 8)[0]
    _need(1 <= n_partitions <= 30, f"unexpected partition count: {n_partitions}")
    partitions = []
    for index in range(n_partitions):
        off = 0x20 + index * 16
        start, size, ptype, flag = struct.unpack_from("<IIII", payload, off)
        partitions.append(dict(index=index + 1, start=start, size=size, type=ptype, flag=flag))
    return dict(n_partitions=n_partitions, partitions=partitions)
