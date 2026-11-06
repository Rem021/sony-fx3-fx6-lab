"""Own offline byte codec for an upstream-derived, unverified FX3 candidate.

No USB, backend, file access, authentication, retries, writes, or native modules.
Only single-frame candidate setpath/read requests can be encoded. This does not
prove that an FX3 accepts these bytes or that a read request is device-bounded.
"""

from dataclasses import dataclass
import struct

TARGET_ROUTE_VERIFIED = False
LIVE_TRANSPORT_SUPPORTED = False
MAX_DATA_BYTES = 65536  # Local analysis policy, not a camera protocol limit.
MAX_PATH_BYTES = 510
HEADER_BYTES = 12
_HEADER = struct.Struct("<IHHBBBB")
_COMMAND = struct.Struct("<HH")
_STATUS = struct.Struct("<I")
_PFUNC = 0x40
_FAMILY = 0x1001
_SETPATH = 15
_READ = 17
_MISSING_CANDIDATE = 0x10000006


class CodecError(ValueError):
    """Unsupported or malformed offline input; no I/O was attempted."""


class RemoteStatusError(CodecError):
    def __init__(self, status):
        self.status = status
        super().__init__("Upstream-derived nonzero Jiritsu status: %#x" % status)


class MissingCandidate(RemoteStatusError):
    """Upstream missing-file status candidate, not FX3-verified semantics."""


@dataclass(frozen=True)
class Reply:
    sequence: int
    # Command comes from the caller's context; it is not echoed by this layout.
    expected_command: int
    data: bytes


def _sequence(value):
    if type(value) is not int or not 1 <= value <= 0xFFFF:
        raise CodecError("Sequence must be an integer in 1..65535; no wrap")
    return value


def _request(sequence, command, arguments):
    if command not in (_SETPATH, _READ):
        raise CodecError("Only candidate setpath/read is supported")
    payload = _COMMAND.pack(_FAMILY, command) + arguments
    return _HEADER.pack(len(payload), _PFUNC, _sequence(sequence), 0, 0, 0, 0) + payload


def encode_setpath(path, *, sequence):
    """Encode a canonical temporary path; traversal is intentionally excluded."""
    if type(path) is not str:
        raise CodecError("Path must be an ASCII string")
    try:
        raw = path.encode("ascii")
    except UnicodeEncodeError as exc:
        raise CodecError("Path must be ASCII") from exc
    if (not path.startswith("/tmp/jiritsu/") or len(raw) > MAX_PATH_BYTES
            or any(byte < 32 or byte > 126 for byte in raw)
            or any(part in ("", ".", "..") for part in path.split("/")[1:])):
        raise CodecError("Path is outside the conservative offline candidate policy")
    return _request(sequence, _SETPATH, b"\0" + raw + b"\0")


def encode_read(*, sequence):
    """Encode upstream read arguments. There is NO on-wire length limit here."""
    return _request(sequence, _READ, b"\0\xff\0")


def parse_reply(frame, *, expected_sequence, expected_command, max_data_bytes=MAX_DATA_BYTES):
    """Validate one already-assembled frame, never a USB stream or fragments.

    Refuse nonzero flags/status, continuation-size frames, mismatched lengths,
    trailing bytes, and data larger than local policy. No device I/O occurs.
    """
    _sequence(expected_sequence)
    if type(expected_command) is not int or expected_command not in (_SETPATH, _READ):
        raise CodecError("Unknown expected command; only setpath/read context allowed")
    if type(max_data_bytes) is not int or not 0 <= max_data_bytes <= MAX_DATA_BYTES:
        raise CodecError("Invalid local response bound")
    if type(frame) is not bytes:
        raise CodecError("Input must be immutable bytes")
    if len(frame) < HEADER_BYTES:
        raise CodecError("Truncated outer header")
    if len(frame) > HEADER_BYTES + 4 + max_data_bytes:
        raise CodecError("Response exceeds local frame bound")
    size, pfunc, sequence, version, micon, offset, response = _HEADER.unpack_from(frame)
    if not 4 <= size <= 4 + max_data_bytes:
        raise CodecError("Declared payload size outside local bound")
    if len(frame) != HEADER_BYTES + size:
        raise CodecError("Declared size mismatch: truncated or trailing data")
    if pfunc != _PFUNC or sequence != expected_sequence:
        raise CodecError("Wrong pFunc or sequence")
    if (version, micon, offset, response) != (0, 0, 0, 0):
        raise CodecError("Unsupported outer flags or nonzero adjust response")
    status = _STATUS.unpack_from(frame, HEADER_BYTES)[0]
    data = frame[HEADER_BYTES + 4:]
    if status:
        if data:
            raise CodecError("Nonzero status with unexpected body")
        if status == _MISSING_CANDIDATE and expected_command == _READ:
            raise MissingCandidate(status)
        raise RemoteStatusError(status)
    if expected_command == _SETPATH and data:
        raise CodecError("Unexpected data in setpath acknowledgement")
    return Reply(sequence, expected_command, data)
