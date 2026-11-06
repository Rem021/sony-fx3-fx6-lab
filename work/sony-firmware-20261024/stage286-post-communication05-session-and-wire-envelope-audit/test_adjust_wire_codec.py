"""Offline unit tests for adjust_wire_codec.py."""
from pathlib import Path
from hashlib import sha256
import json, struct
from adjust_wire_codec import (
    AdjustRequestEnvelope,
    build_ram_slot_set_request,
    build_ram_slot_get_request,
    parse_adjust_response_header,
    parse_adjust_response_body,
    PFUNC_ADJUST_CONTROL,
    CATEGORY_JIRITSU,
    CMD_SET_FILE2,
    CMD_GET_FILE2,
    REQ_VERSION_ADJUST,
    RESP_VERSION_STOCK,
    RESP_RES_OK,
    OP_RAM_CACHE_SLOT,
)

H = Path(__file__).resolve().parent


def expect_error(fn, label: str) -> str:
    try:
        fn()
    except ValueError as exc:
        return f'{label}: {exc}'
    raise AssertionError(f'Expected ValueError for {label}')


def main() -> None:
    # 1. Valid RAM slot SET_FILE2 request
    sample = b'FX3_STAGE286_RAM_SLOT_TEST_PAYLOAD'
    req_set = build_ram_slot_set_request(seq=1, slot=0, mode=0, data=sample)
    wire_set = req_set.to_wire_bytes()
    assert len(wire_set) == 12 + 4 + 3 + len(sample)
    sz, pfunc, seq, ver, flag, rsv, res = struct.unpack_from('<IHHBBBB', wire_set, 0)
    cat, cmd = struct.unpack_from('<HH', wire_set, 12)
    assert (sz, pfunc, seq, ver, flag, rsv, res) == (4 + 3 + len(sample), PFUNC_ADJUST_CONTROL, 1, REQ_VERSION_ADJUST, 0, 0, 0)
    assert (cat, cmd) == (CATEGORY_JIRITSU, CMD_SET_FILE2)
    assert wire_set[16:19] == bytes([OP_RAM_CACHE_SLOT, 0, 0])

    # 2. Valid RAM slot GET_FILE2 request
    req_get = build_ram_slot_get_request(seq=2, slot=0, mode=0)
    wire_get = req_get.to_wire_bytes()
    assert len(wire_get) == 12 + 4 + 3 == 19
    sz2, pfunc2, seq2, ver2, flag2, rsv2, res2 = struct.unpack_from('<IHHBBBB', wire_get, 0)
    cat2, cmd2 = struct.unpack_from('<HH', wire_get, 12)
    assert (sz2, pfunc2, seq2, ver2, flag2, rsv2, res2) == (7, PFUNC_ADJUST_CONTROL, 2, REQ_VERSION_ADJUST, 0, 0, 0)
    assert (cat2, cmd2) == (CATEGORY_JIRITSU, CMD_GET_FILE2)
    assert wire_get[16:19] == bytes([OP_RAM_CACHE_SLOT, 0, 0])

    # 3. Valid SET_FILE2 4-byte response (header + 4B status=0)
    resp_hdr_set = struct.pack('<IHHBBBB', 4, PFUNC_ADJUST_CONTROL, 1, RESP_VERSION_STOCK, 0, 0, RESP_RES_OK)
    parsed_sz_set = parse_adjust_response_header(resp_hdr_set, expected_seq=1, max_payload_bytes=4)
    assert parsed_sz_set == 4
    parsed_body_set = parse_adjust_response_body(struct.pack('<I', 0), expected_size=4)
    assert parsed_body_set['native_status'] == 0 and parsed_body_set['payload_bytes'] == 0

    # 4. Valid GET_FILE2 response (header + 4B status=0 + sample)
    resp_hdr_get = struct.pack('<IHHBBBB', 4 + len(sample), PFUNC_ADJUST_CONTROL, 2, RESP_VERSION_STOCK, 0, 0, RESP_RES_OK)
    parsed_sz_get = parse_adjust_response_header(resp_hdr_get, expected_seq=2, max_payload_bytes=260)
    assert parsed_sz_get == 4 + len(sample)
    parsed_body_get = parse_adjust_response_body(struct.pack('<I', 0) + sample, expected_size=parsed_sz_get)
    assert parsed_body_get['native_status'] == 0
    assert parsed_body_get['payload_bytes'] == len(sample)
    assert parsed_body_get['payload_sha256_hex'] == sha256(sample).hexdigest()

    # 5. Counterexample rejections
    rejections = [
        expect_error(lambda: build_ram_slot_set_request(seq=0, slot=0, mode=0, data=b'x').to_wire_bytes(), 'seq_zero'),
        expect_error(lambda: build_ram_slot_set_request(seq=1, slot=256, mode=0, data=b'x'), 'slot_overflow'),
        expect_error(lambda: build_ram_slot_set_request(seq=1, slot=0, mode=0x12, data=b'x'), 'mode_above_0x11'),
        expect_error(lambda: build_ram_slot_set_request(seq=1, slot=0, mode=0, data=b''), 'empty_data'),
        expect_error(lambda: AdjustRequestEnvelope(seq=1, command=0x9999, inner_payload=b'x').to_wire_bytes(), 'bad_command'),
        expect_error(
            lambda: parse_adjust_response_header(
                struct.pack('<IHHBBBB', 4, PFUNC_ADJUST_CONTROL, 1, 0, 0, 0, RESP_RES_OK), expected_seq=1
            ),
            'wrong_response_version_0',
        ),
        expect_error(
            lambda: parse_adjust_response_header(
                struct.pack('<IHHBBBB', 4, PFUNC_ADJUST_CONTROL, 9, RESP_VERSION_STOCK, 0, 0, RESP_RES_OK), expected_seq=1
            ),
            'wrong_response_seq',
        ),
        expect_error(
            lambda: parse_adjust_response_header(
                struct.pack('<IHHBBBB', 4, 0x0010, 1, RESP_VERSION_STOCK, 0, 0, RESP_RES_OK), expected_seq=1
            ),
            'wrong_response_pfunc',
        ),
        expect_error(
            lambda: parse_adjust_response_header(
                struct.pack('<IHHBBBB', 4, PFUNC_ADJUST_CONTROL, 1, RESP_VERSION_STOCK, 0, 0, 0x82), expected_seq=1
            ),
            'error_res_0x82',
        ),
        expect_error(
            lambda: parse_adjust_response_header(
                struct.pack('<IHHBBBB', 512, PFUNC_ADJUST_CONTROL, 1, RESP_VERSION_STOCK, 0, 0, RESP_RES_OK),
                expected_seq=1,
                max_payload_bytes=260,
            ),
            'oversized_response_payload',
        ),
        expect_error(
            lambda: parse_adjust_response_body(struct.pack('<I', 0x10000201), expected_size=4),
            'nonzero_native_status_0x10000201',
        ),
        expect_error(
            lambda: parse_adjust_response_body(b'\x00\x00\x00', expected_size=4),
            'short_response_body',
        ),
    ]

    receipt = dict(
        status='ADJUST_WIRE_CODEC_TESTS_PASSED',
        valid_cases=4,
        rejected_counterexamples=len(rejections),
        rejection_details=rejections,
        usb_or_camera_operations=0,
    )
    (H / 'codec-test-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    main()
