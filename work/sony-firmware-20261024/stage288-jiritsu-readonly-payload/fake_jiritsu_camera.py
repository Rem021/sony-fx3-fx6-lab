"""Offline fake of the Jiritsu command surface used by the Stage 288 read-only test.

This is a host-side state machine, not camera code. It validates the request
sequence and response parsing; it does not prove the camera's behaviour.

Corrected per the DeepSeek review and FX3 libJiritsu.so:
  - SET_FILE_PATH payload = 00 + path + 00
  - SET_FILE2 / GET_FILE2 payload = 00 ff 00 (+ file bytes for SET)
  - SET_FILE2 refuses the libJit write when /tmp/jbusy EXISTS (0x10000011)
  - the inline dlopen happens inside SET_FILE2; MODE/START are not needed
"""
import struct

PFUNC = 0x0040
CATEGORY = 0x1001
CMD_MODE = 1
CMD_START = 4
CMD_SET_FILE_PATH = 15
CMD_SET_FILE2 = 16
CMD_GET_FILE2 = 17

STATUS_OK = 0
STATUS_BUSY = 0x10000011
STATUS_BAD_FRAME = 0x10000201
STATUS_GET_ABSENT = 0x11
LIBJIT_PATH = "/tmp/jiritsu/libJit.so"
SECTOR0_PATH = "/tmp/jiritsu/sector0.bin"


class FakeJiritsuCamera:
    def __init__(self, sector0: bytes):
        assert len(sector0) == 512
        self.sector0 = sector0
        self.jmodes = {}
        self.jbusy = False
        self.selected_path = None
        self.files = {}

    @staticmethod
    def _response(seq: int, status: int, payload: bytes = b"") -> bytes:
        body = struct.pack("<I", status) + payload
        header = struct.pack("<IHHBBBB", len(body), PFUNC, seq, 3, 0, 0, 1)
        return header + body

    def handle(self, wire: bytes) -> bytes:
        assert len(wire) >= 16
        size, pfunc, seq, version, flag, reserved, res = struct.unpack_from("<IHHBBBB", wire, 0)
        assert (pfunc, version, flag, reserved, res) == (PFUNC, 2, 0, 0, 0)
        assert size == len(wire) - 12, (size, len(wire))
        body = wire[12:]
        category, command = struct.unpack_from("<HH", body, 0)
        assert category == CATEGORY
        inner = body[4:]

        if command == CMD_MODE:
            if len(inner) != 2 or inner[0] != 1:
                return self._response(seq, STATUS_BAD_FRAME)
            # cmd_mode case 4 writes " TE" (the %sE suffix) and returns command status 4.
            self.jmodes["/tmp/jmode"] = " TE" if (inner[1] & 0xF) == 4 else f"M{inner[1]:02x}"
            return self._response(seq, 4)

        if command == CMD_START:
            if inner != b"\x01":
                return self._response(seq, STATUS_BAD_FRAME)
            self.jbusy = True
            return self._response(seq, STATUS_OK)

        if command == CMD_SET_FILE_PATH:
            if len(inner) < 3 or inner[0] != 0x00 or inner[-1] != 0x00:
                return self._response(seq, STATUS_BAD_FRAME)
            path = inner[1:-1].decode("ascii", "strict")
            if not path.startswith("/tmp/jiritsu/"):
                return self._response(seq, STATUS_BAD_FRAME)
            self.selected_path = path
            return self._response(seq, STATUS_OK)

        if command == CMD_SET_FILE2:
            if len(inner) < 4 or inner[0] != 0x00 or inner[1] != 0xFF or inner[2] not in (0, 1):
                return self._response(seq, STATUS_BAD_FRAME)
            if self.jbusy:
                return self._response(seq, STATUS_BUSY)
            data = inner[3:]
            self.files[self.selected_path] = data
            # The inline dlopen happens only when the selected path is exactly libJit.so.
            if self.selected_path == LIBJIT_PATH:
                # Simulate the constructor: read /dev/nflasha 512B into sector0.bin.
                self.files[SECTOR0_PATH] = self.sector0
            return self._response(seq, STATUS_OK)

        if command == CMD_GET_FILE2:
            if inner != b"\x00\xff\x00":
                return self._response(seq, STATUS_BAD_FRAME)
            if self.selected_path not in self.files:
                return self._response(seq, STATUS_GET_ABSENT)
            return self._response(seq, STATUS_OK, self.files[self.selected_path])

        return self._response(seq, STATUS_BAD_FRAME)
