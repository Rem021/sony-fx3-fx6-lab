"""Own bytes-only candidate parser. No transport, request encoder, or device I/O.

feed() boundaries are synthetic byte fragments, NOT USB packet boundaries.
finish() closes a supplied offline capture, NOT a USB transfer or file.
The remaining-size continuation rule comes from fixed PMCA host source.
All target and USB completion claims remain false.
"""

from dataclasses import dataclass
import struct

TARGET_VERIFIED = False
USB_TERMINATION_VERIFIED = False
SEGMENT_BYTES = 0x100000
MAX_DATA_BYTES = 2 * SEGMENT_BYTES
MAX_CAPTURE_BYTES = 4 * SEGMENT_BYTES
MAX_MANIFEST_DATA_BYTES = 80 * SEGMENT_BYTES
FX3_APPFW_EXPECTED_BYTES = 79015712
MAX_EMPTY_FRAGMENTS = 16
_HEADER = struct.Struct("<IHHBBBB")
_STATUS = struct.Struct("<I")
_VERSIONS = {"upstream-zero-fixture": 0, "fx3-static-version3-candidate": 3}


class ParseError(ValueError):
    pass


class IncompleteCapture(ParseError):
    pass


class RemoteStatusError(ParseError):
    def __init__(self, status):
        self.status = status
        super().__init__("Nonzero upstream-derived status: %#x" % status)


@dataclass(frozen=True)
class Expectation:
    sequence: int
    command: int
    max_data_bytes: int = 65536
    expected_data_bytes: int | None = None

    def __post_init__(self):
        if type(self.sequence) is not int or not 1 <= self.sequence <= 65535:
            raise ParseError("Expected sequence outside 1..65535; no wrap")
        if type(self.command) is not int or self.command not in (15, 17):
            raise ParseError("Only setpath/read response contexts are allowed")
        if type(self.max_data_bytes) is not int or not 0 <= self.max_data_bytes <= MAX_MANIFEST_DATA_BYTES:
            raise ParseError("Data bound outside local policy")
        if self.expected_data_bytes is not None:
            if (type(self.expected_data_bytes) is not int
                    or not 0 <= self.expected_data_bytes <= self.max_data_bytes):
                raise ParseError("Exact manifest length outside the declared data bound")
            if self.command == 15 and self.expected_data_bytes != 0:
                raise ParseError("Setpath manifest cannot declare data")
        elif self.max_data_bytes > MAX_DATA_BYTES:
            raise ParseError("Large data bounds require an exact manifest length")


@dataclass(frozen=True)
class Reply:
    sequence: int
    expected_command: int  # Context, NOT an echoed wire field.
    data: bytes


@dataclass(frozen=True)
class OfflineCapture:
    replies: tuple
    profile: str
    logical_capture_complete: bool = True
    target_verified: bool = False
    usb_termination_verified: bool = False


class ResponseAssembler:
    """Fail-closed, bounded offline reassembly for an explicit response plan.

    No reply is released until finish() validates the entire supplied capture.
    Unknown USB/ZLP/short-packet semantics are deliberately not synthesized.
    """

    def __init__(self, expectations, *, profile):
        if type(profile) is not str or profile not in _VERSIONS:
            raise ParseError("Explicit supported synthetic/static profile required")
        if type(expectations) not in (tuple, list) or not 1 <= len(expectations) <= 8:
            raise ParseError("An explicit bounded response plan is required")
        if any(type(item) is not Expectation for item in expectations):
            raise ParseError("Response plan requires exact Expectation objects")
        if any(b.sequence != a.sequence + 1 for a, b in zip(expectations, expectations[1:])):
            raise ParseError("Expected logical sequences must increase by one without wrapping")
        self._plan = tuple(expectations)
        self._profile = profile
        self._version = _VERSIONS[profile]
        self._capture_limit = MAX_CAPTURE_BYTES
        if any(item.max_data_bytes > MAX_DATA_BYTES for item in expectations):
            if len(expectations) != 1 or expectations[0].command != 17:
                raise ParseError("Large manifest mode permits exactly one read response")
        if len(expectations) == 1 and expectations[0].expected_data_bytes is not None:
            payload_bytes = 4 + expectations[0].expected_data_bytes
            segments = (payload_bytes + SEGMENT_BYTES - 1) // SEGMENT_BYTES
            self._capture_limit = payload_bytes + segments * _HEADER.size
        self._buffer = bytearray()
        self._payload = bytearray()
        self._results = []
        self._index = 0
        self._remaining = None
        self._declared = None
        self._body_left = 0
        self._segment_size = 0
        self._status_checked = False
        self._received = 0
        self._empty = 0
        self._failed = False
        self._finished = False

    def _fail(self, error):
        self._failed = True
        self._buffer.clear()
        self._payload.clear()
        self._results.clear()
        raise error

    def _usable(self):
        if self._failed:
            raise ParseError("Capture is unusable after a previous error")
        if self._finished:
            raise ParseError("Capture was already finalized")

    def feed(self, fragment):
        self._usable()
        if type(fragment) is not bytes:
            self._fail(ParseError("Only immutable bytes fragments are accepted"))
        if not fragment:
            self._empty += 1
            if self._empty > MAX_EMPTY_FRAGMENTS:
                self._fail(ParseError("Empty-fragment budget exhausted; no implied EOF"))
            return
        if len(fragment) > self._capture_limit - self._received:
            self._fail(ParseError("Cumulative capture limit exceeded"))
        self._received += len(fragment)
        self._buffer.extend(fragment)
        while self._buffer:
            if self._index == len(self._plan):
                self._fail(ParseError("Unexpected trailing bytes or an unplanned response"))
            expected = self._plan[self._index]
            if not self._body_left:
                if len(self._buffer) < _HEADER.size:
                    return
                size, pfunc, seq, version, micon, offset, response = _HEADER.unpack_from(self._buffer)
                if (pfunc, seq) != (0x40, expected.sequence):
                    self._fail(ParseError("Wrong response pFunc/sequence"))
                if (version, micon, offset, response) != (self._version, 0, 0, 0):
                    self._fail(ParseError("Unsupported response profile or nonzero outer status"))
                if self._remaining is None:
                    if not 4 <= size <= 4 + expected.max_data_bytes:
                        self._fail(ParseError("Declared logical payload exceeds local bound or lacks status"))
                    if expected.expected_data_bytes is not None and size != 4 + expected.expected_data_bytes:
                        self._fail(ParseError("Declared payload does not match the exact manifest length"))
                    if expected.command == 15 and size != 4:
                        self._fail(ParseError("Unexpected setpath acknowledgement data"))
                    self._remaining = self._declared = size
                elif size != self._remaining:
                    self._fail(ParseError("Continuation must declare exact remaining payload size"))
                del self._buffer[:_HEADER.size]
                self._segment_size = min(size, SEGMENT_BYTES)
                self._body_left = self._segment_size
            take = min(len(self._buffer), self._body_left)
            self._payload.extend(self._buffer[:take])
            del self._buffer[:take]
            self._body_left -= take
            if not self._status_checked and len(self._payload) >= 4:
                status = _STATUS.unpack_from(self._payload)[0]
                self._status_checked = True
                if status:
                    self._fail(RemoteStatusError(status))
            if self._body_left:
                return
            self._remaining -= self._segment_size
            if self._remaining:
                continue
            if not self._status_checked or len(self._payload) != self._declared:
                self._fail(ParseError("Internal logical-length/status mismatch"))
            self._results.append(Reply(expected.sequence, expected.command, bytes(self._payload[4:])))
            self._payload.clear()
            self._index += 1
            self._remaining = self._declared = None
            self._status_checked = False

    def abort(self, reason):
        """Record a caller-supplied failed capture; never retry or release data."""
        self._usable()
        if type(reason) is not str or len(reason) > 256:
            self._fail(ParseError("Invalid offline failure description"))
        self._fail(ParseError("Offline capture aborted: " + reason))

    def finish(self):
        """Close the offline fixture; success does not assert USB termination."""
        self._usable()
        if self._buffer or self._remaining is not None or self._index != len(self._plan):
            self._fail(IncompleteCapture("Capture ended before the response plan was complete"))
        self._finished = True
        return OfflineCapture(tuple(self._results), self._profile)
