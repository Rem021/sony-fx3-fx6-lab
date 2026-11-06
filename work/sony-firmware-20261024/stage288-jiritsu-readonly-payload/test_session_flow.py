"""Offline end-to-end test of the corrected Stage 288 Jiritsu sequence.

Minimal direct path (no MODE/START):
  SET_FILE_PATH(libJit) -> SET_FILE2(00 ff 00 + SO) -> dlopen constructor
  -> SET_FILE_PATH(sector0) -> GET_FILE2(00 ff 00)

Uses a fake camera state machine; no USB, IOKit, QEMU, or camera.
"""
from hashlib import sha256
import struct

from jiritsu_wire import (
    AdjustRequestEnvelope,
    set_file_path_request,
    set_file2_request,
    get_file2_request,
    parse_adjust_response_header,
    parse_adjust_response_body,
    parse_sector0,
    CMD_SET_FILE2,
    CMD_GET_FILE2,
)
from fake_jiritsu_camera import (
    FakeJiritsuCamera,
    STATUS_BUSY,
    STATUS_BAD_FRAME,
    STATUS_GET_ABSENT,
    LIBJIT_PATH,
    SECTOR0_PATH,
)
from test_jiritsu_wire import make_sector0, SO, SO_SHA256


def response(wire: bytes, seq: int):
    size = parse_adjust_response_header(wire[:12], expected_seq=seq, max_payload_bytes=4 + 512)
    body = wire[12:]
    assert len(body) == size
    status = struct.unpack_from("<I", body, 0)[0]
    return status, body[4:]


def main() -> None:
    so_bytes = SO.read_bytes()
    assert sha256(so_bytes).hexdigest() == SO_SHA256
    sector0 = make_sector0()
    cam = FakeJiritsuCamera(sector0)

    # Happy path: no MODE/START; jbusy must be absent.
    seq = 1
    status, _ = response(cam.handle(set_file_path_request(seq, LIBJIT_PATH).to_wire_bytes()), seq)
    assert status == 0, hex(status)
    assert cam.jbusy is False
    assert cam.jmodes == {}

    seq += 1
    status, _ = response(cam.handle(set_file2_request(seq, so_bytes).to_wire_bytes()), seq)
    assert status == 0, hex(status)
    assert cam.files[LIBJIT_PATH] == so_bytes
    assert cam.files[SECTOR0_PATH] == sector0

    seq += 1
    status, _ = response(cam.handle(set_file_path_request(seq, SECTOR0_PATH).to_wire_bytes()), seq)
    assert status == 0, hex(status)

    seq += 1
    status, payload = response(cam.handle(get_file2_request(seq).to_wire_bytes()), seq)
    assert status == 0, hex(status)
    assert len(payload) == 512
    table = parse_sector0(payload)
    assert table["n_partitions"] == 30
    assert table["partitions"][0]["start"] == 0x80
    assert table["partitions"][0]["size"] == 0xBF80

    # Negative 1: jbusy exists -> SET_FILE2 must refuse with 0x10000011.
    cam2 = FakeJiritsuCamera(sector0)
    cam2.jbusy = True
    cam2.handle(set_file_path_request(1, LIBJIT_PATH).to_wire_bytes())
    status, _ = response(cam2.handle(set_file2_request(2, so_bytes).to_wire_bytes()), 2)
    assert status == STATUS_BUSY, hex(status)
    assert LIBJIT_PATH not in cam2.files

    # Negative 2: selector 2 is rejected by the frame handler.
    cam3 = FakeJiritsuCamera(sector0)
    cam3.handle(set_file_path_request(1, LIBJIT_PATH).to_wire_bytes())
    bad = AdjustRequestEnvelope(seq=2, command=CMD_SET_FILE2, inner_payload=b"\x00\x02\x00" + b"x").to_wire_bytes()
    status, _ = response(cam3.handle(bad), 2)
    assert status == STATUS_BAD_FRAME, hex(status)

    # Negative 3: wrong selected path writes but does not dlopen -> no sector0.
    cam4 = FakeJiritsuCamera(sector0)
    cam4.handle(set_file_path_request(1, "/tmp/jiritsu/not_libJit.so").to_wire_bytes())
    status, _ = response(cam4.handle(set_file2_request(2, so_bytes).to_wire_bytes()), 2)
    assert status == 0, hex(status)
    assert SECTOR0_PATH not in cam4.files

    # Negative 4: GET_FILE2 before any file exists -> 0x11, no payload.
    cam5 = FakeJiritsuCamera(sector0)
    cam5.selected_path = SECTOR0_PATH
    status, payload = response(cam5.handle(get_file2_request(1).to_wire_bytes()), 1)
    assert status == STATUS_GET_ABSENT, hex(status)
    assert payload == b""

    print("PASS minimal path: SET_FILE_PATH(libJit) -> SET_FILE2 -> SET_FILE_PATH(sector0) -> GET_FILE2")
    print("PASS no MODE/START: jbusy stays False, jmode untouched")
    print("PASS sector0: magic 8246/2.00, 30 partitions, p1 start=0x80 size=0xBF80")
    print("PASS negative: jbusy exists -> 0x10000011, no write")
    print("PASS negative: selector 2 -> 0x10000201")
    print("PASS negative: wrong path -> no dlopen/sector0")
    print("PASS negative: GET_FILE2 absent -> 0x11, no payload")


if __name__ == "__main__":
    main()
