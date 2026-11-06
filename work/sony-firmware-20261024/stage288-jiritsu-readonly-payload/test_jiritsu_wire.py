"""Host-only tests for the Jiritsu read-only wire codec. No camera, USB, QEMU, or network."""
from hashlib import sha256
from pathlib import Path
import struct

from jiritsu_wire import (
    AdjustRequestEnvelope,
    PFUNC_ADJUST_CONTROL,
    CATEGORY_JIRITSU,
    CMD_JIRITSU_MODE,
    CMD_JIRITSU_START,
    CMD_SET_FILE_PATH,
    CMD_SET_FILE2,
    CMD_GET_FILE2,
    REQ_VERSION_ADJUST,
    RESP_VERSION_STOCK,
    RESP_RES_OK,
    mode_request,
    start_request,
    set_file_path_request,
    set_file2_request,
    get_file2_request,
    parse_adjust_response_header,
    parse_adjust_response_body,
    parse_sector0,
)

HERE = Path(__file__).resolve().parent
SO = HERE / "payload" / "libJit_test.so"
SO_SHA256 = "05000a0ecceaa5004385b71fbeb2b15859bda7418e227a3d90238da31bc4cd7a"


def expect_error(fn, label: str) -> str:
    try:
        fn()
    except ValueError as exc:
        return f"{label}: {exc}"
    raise AssertionError(f"expected ValueError for {label}")


def make_sector0() -> bytes:
    buf = bytearray(512)
    buf[0:4] = b"8246"
    buf[4:8] = b"2.00"
    struct.pack_into("<I", buf, 8, 30)
    # FX3 p1 is real; the rest are synthetic but structurally valid.
    struct.pack_into("<IIII", buf, 0x20, 0x80, 0xBF80, 4, 1)
    for index in range(1, 30):
        struct.pack_into("<IIII", buf, 0x20 + index * 16, 0x1000 * (index + 1), 0x100, 4, 1)
    return bytes(buf)


def main() -> None:
    assert SO.exists(), f"missing payload: {SO}"
    so_bytes = SO.read_bytes()
    assert sha256(so_bytes).hexdigest() == SO_SHA256, "payload SHA256 mismatch"
    assert len(so_bytes) == 8345, f"unexpected payload size: {len(so_bytes)}"

    # 1. MODE request: header + 4B selector + 01 04
    wire_mode = mode_request(seq=1).to_wire_bytes()
    assert len(wire_mode) == 18, len(wire_mode)
    size, pfunc, seq, version, flag, reserved, res = struct.unpack_from("<IHHBBBB", wire_mode, 0)
    cat, cmd = struct.unpack_from("<HH", wire_mode, 12)
    assert (size, pfunc, seq, version, flag, reserved, res) == (6, PFUNC_ADJUST_CONTROL, 1, REQ_VERSION_ADJUST, 0, 0, 0)
    assert (cat, cmd) == (CATEGORY_JIRITSU, CMD_JIRITSU_MODE)
    assert wire_mode[16:18] == b"\x01\x04", "MODE payload is not 01 04"

    # 2. START request: header + selector + 01
    wire_start = start_request(seq=2).to_wire_bytes()
    assert len(wire_start) == 17
    assert struct.unpack_from("<I", wire_start, 0)[0] == 5
    assert struct.unpack_from("<H", wire_start, 14)[0] == CMD_JIRITSU_START
    assert wire_start[16:17] == b"\x01"

    # 3. SET_FILE_PATH: /tmp/jiritsu/libJit.so + NUL
    path = "/tmp/jiritsu/libJit.so"
    wire_path = set_file_path_request(seq=3, path=path).to_wire_bytes()
    assert struct.unpack_from("<H", wire_path, 14)[0] == CMD_SET_FILE_PATH
    assert wire_path[16:] == b"\x00" + path.encode() + b"\x00"
    assert len(wire_path) == 12 + 4 + 1 + len(path) + 1

    # 4. SET_FILE2 op 0: 00 + 8,345-byte payload
    wire_set = set_file2_request(seq=4, file_bytes=so_bytes).to_wire_bytes()
    assert struct.unpack_from("<H", wire_set, 14)[0] == CMD_SET_FILE2
    assert wire_set[16:19] == b"\x00\xff\x00"
    assert wire_set[19:] == so_bytes
    assert struct.unpack_from("<I", wire_set, 0)[0] == 4 + 3 + len(so_bytes)
    assert len(wire_set) <= 0x100000

    # 5. GET_FILE2 op 0: one byte
    wire_get = get_file2_request(seq=5).to_wire_bytes()
    assert struct.unpack_from("<H", wire_get, 14)[0] == CMD_GET_FILE2
    assert wire_get[16:19] == b"\x00\xff\x00"
    assert len(wire_get) == 19

    # 6. Response: 4B status + 512B sector0
    sector0 = make_sector0()
    resp_body = struct.pack("<I", 0) + sector0
    resp_header = struct.pack("<IHHBBBB", len(resp_body), PFUNC_ADJUST_CONTROL, 5, RESP_VERSION_STOCK, 0, 0, RESP_RES_OK)
    size2 = parse_adjust_response_header(resp_header, expected_seq=5, max_payload_bytes=4 + 512)
    parsed = parse_adjust_response_body(resp_body, expected_size=size2)
    assert parsed["native_status"] == 0
    assert parsed["payload_bytes"] == 512
    table = parse_sector0(parsed["payload"])
    assert table["n_partitions"] == 30
    assert table["partitions"][0] == dict(index=1, start=0x80, size=0xBF80, type=4, flag=1)

    # 7. Counterexamples: must fail closed.
    rejections = [
        expect_error(lambda: mode_request(seq=0).to_wire_bytes(), "seq_zero"),
        expect_error(lambda: mode_request(seq=1, subcommand=2), "bad_subcommand"),
        expect_error(lambda: AdjustRequestEnvelope(seq=1, command=0x9999, inner_payload=b"x").to_wire_bytes(), "bad_command"),
        expect_error(lambda: set_file_path_request(seq=1, path="/tmp/other"), "path_outside_jiritsu"),
        expect_error(lambda: set_file_path_request(seq=1, path="/tmp/jiritsu/" + "a" * 520), "path_too_long"),
        expect_error(lambda: set_file2_request(seq=1, file_bytes=b""), "empty_file"),
        expect_error(lambda: set_file2_request(seq=1, file_bytes=b"x", selector=2), "selector_2_rejected"),
        expect_error(lambda: get_file2_request(seq=1, selector=2), "get_selector_2_rejected"),
        expect_error(lambda: parse_adjust_response_header(
            struct.pack("<IHHBBBB", 4, PFUNC_ADJUST_CONTROL, 1, 2, 0, 0, RESP_RES_OK), expected_seq=1), "bad_version"),
        expect_error(lambda: parse_adjust_response_header(
            struct.pack("<IHHBBBB", 4, PFUNC_ADJUST_CONTROL, 2, RESP_VERSION_STOCK, 0, 0, RESP_RES_OK), expected_seq=1), "seq_mismatch"),
        expect_error(lambda: parse_adjust_response_body(struct.pack("<I", 1), expected_size=4), "nonzero_status"),
        expect_error(lambda: parse_sector0(b"\x00" * 512), "bad_magic"),
        expect_error(lambda: parse_sector0(b"82462.00" + b"\x00" * 504), "bad_partition_count"),
    ]

    print(f"PASS payload sha256/size: {SO_SHA256[:16]}... / {len(so_bytes)} B")
    print(f"PASS MODE wire: {len(wire_mode)} B, payload {wire_mode[16:].hex()}")
    print(f"PASS START wire: {len(wire_start)} B, payload {wire_start[16:].hex()}")
    print(f"PASS SET_FILE_PATH: {path} + NUL")
    print(f"PASS SET_FILE2: op=0x00, {len(so_bytes)} B, wire {len(wire_set)} B")
    print(f"PASS GET_FILE2: op=0x00, wire {len(wire_get)} B")
    print(f"PASS sector0 parse: 30 partitions, p1 start=0x80 size=0xBF80")
    print(f"PASS rejections: {len(rejections)} cases")
    for line in rejections:
        print(f"  - {line}")


if __name__ == "__main__":
    main()
