"""Own synthetic stream fixtures; imports only our adjacent bytes parser."""

import ast
import hashlib
from pathlib import Path
import random
import struct
import unittest

from offline_reassembly import (Expectation, ResponseAssembler, ParseError,
    IncompleteCapture, RemoteStatusError, SEGMENT_BYTES, MAX_DATA_BYTES,
    MAX_CAPTURE_BYTES, MAX_EMPTY_FRAGMENTS, MAX_MANIFEST_DATA_BYTES,
    FX3_APPFW_EXPECTED_BYTES)

GOLDEN_READ_V0 = bytes.fromhex("07000000400002000000000000000000414243")
GOLDEN_READ_V3 = bytes.fromhex("07000000400002000300000000000000414243")
GOLDEN_ACK_V3 = bytes.fromhex("04000000400001000300000000000000")


def header(size, *, sequence=2, version=3, pfunc=0x40, flags=(0, 0, 0)):
    return struct.pack("<IHHBBBB", size, pfunc, sequence, version, *flags)


def logical(data=b"ABC", *, sequence=2, version=3, status=0):
    payload = struct.pack("<I", status) + data
    out = bytearray()
    while payload:
        out.extend(header(len(payload), sequence=sequence, version=version))
        out.extend(payload[:SEGMENT_BYTES])
        payload = payload[SEGMENT_BYTES:]
    return bytes(out)


class ReassemblyFixtures(unittest.TestCase):
    def parser(self, *, max_data=65536, profile="fx3-static-version3-candidate"):
        return ResponseAssembler((Expectation(2, 17, max_data),), profile=profile)

    def assert_latched(self, parser):
        with self.assertRaises(ParseError):
            parser.feed(b"")
        with self.assertRaises(ParseError):
            parser.finish()

    def test_fixed_golden_profiles_and_false_acceptance_claims(self):
        for profile, raw in (("upstream-zero-fixture", GOLDEN_READ_V0),
                             ("fx3-static-version3-candidate", GOLDEN_READ_V3)):
            parser = self.parser(profile=profile)
            parser.feed(raw)
            result = parser.finish()
            self.assertEqual(result.replies[0].data, b"ABC")
            self.assertTrue(result.logical_capture_complete)
            self.assertFalse(result.target_verified)
            self.assertFalse(result.usb_termination_verified)

    def test_each_two_way_fragment_boundary(self):
        for cut in range(len(GOLDEN_READ_V3) + 1):
            with self.subTest(cut=cut):
                parser = self.parser()
                parser.feed(GOLDEN_READ_V3[:cut])
                parser.feed(GOLDEN_READ_V3[cut:])
                self.assertEqual(parser.finish().replies[0].data, b"ABC")

    def test_one_byte_fragments_including_split_status(self):
        parser = self.parser()
        for byte in GOLDEN_READ_V3:
            parser.feed(bytes((byte,)))
        self.assertEqual(parser.finish().replies[0].data, b"ABC")

    def test_deterministic_random_fragmentation(self):
        data = bytes(range(256)) * 17
        raw = logical(data)
        for seed in range(20):
            parser = self.parser()
            rng = random.Random(seed)
            offset = 0
            while offset < len(raw):
                count = rng.randint(1, 127)
                parser.feed(raw[offset:offset + count])
                offset += count
            self.assertEqual(parser.finish().replies[0].data, data)

    def test_concatenated_planned_responses_and_lookahead(self):
        parser = ResponseAssembler([Expectation(1, 15), Expectation(2, 17)],
                                   profile="fx3-static-version3-candidate")
        self.assertIsNone(parser.feed(GOLDEN_ACK_V3 + GOLDEN_READ_V3[:7]))
        self.assertIsNone(parser.feed(GOLDEN_READ_V3[7:]))
        self.assertEqual([item.data for item in parser.finish().replies], [b"", b"ABC"])

    def test_no_reply_release_before_capture_close(self):
        parser = self.parser()
        self.assertIsNone(parser.feed(GOLDEN_READ_V3))
        with self.assertRaises(ParseError):
            parser.feed(b"unexpected")
        self.assert_latched(parser)

    def test_every_incomplete_prefix_never_finishes(self):
        for cut in range(len(GOLDEN_READ_V3)):
            with self.subTest(cut=cut):
                parser = self.parser()
                parser.feed(GOLDEN_READ_V3[:cut])
                with self.assertRaises(IncompleteCapture):
                    parser.finish()
                self.assert_latched(parser)

    def test_empty_fragment_is_not_eof_or_missing_end(self):
        parser = self.parser()
        parser.feed(GOLDEN_READ_V3[:15])
        parser.feed(b"")
        with self.assertRaises(IncompleteCapture):
            parser.finish()

    def test_empty_fragment_budget_is_finite(self):
        parser = self.parser()
        for _ in range(MAX_EMPTY_FRAGMENTS):
            parser.feed(b"")
        with self.assertRaises(ParseError):
            parser.feed(b"")
        self.assert_latched(parser)

    def test_oversized_and_too_short_headers_rejected_before_body(self):
        for size in (0, 1, 2, 3, 65541, 0xFFFFFFFF):
            with self.subTest(size=size):
                parser = self.parser()
                with self.assertRaises(ParseError):
                    parser.feed(header(size))
                self.assert_latched(parser)

    def test_overrun_and_unplanned_concatenation(self):
        for trailing in (b"x", GOLDEN_READ_V3, b"\0" * 12):
            parser = self.parser()
            with self.assertRaises(ParseError):
                parser.feed(GOLDEN_READ_V3 + trailing)
            self.assert_latched(parser)

    def test_sequence_replay_and_skipped_response(self):
        parser = ResponseAssembler([Expectation(1, 15), Expectation(2, 17)],
                                   profile="fx3-static-version3-candidate")
        with self.assertRaises(ParseError):
            parser.feed(GOLDEN_ACK_V3 + logical(sequence=1))
        self.assert_latched(parser)

    def test_wrong_function_flags_or_profile(self):
        headers = [header(4, pfunc=0x20), header(4, sequence=3), header(4, version=0)]
        headers += [header(4, flags=flags) for flags in [(1, 0, 0), (0, 1, 0), (0, 0, 1)]]
        for raw in headers:
            parser = self.parser()
            with self.assertRaises(ParseError):
                parser.feed(raw)
            self.assert_latched(parser)

    def test_nonzero_status_and_phase_order_never_succeed(self):
        for status in (1, 0x10000006, 0xDEADBEEF):
            parser = self.parser()
            with self.assertRaises(RemoteStatusError) as caught:
                parser.feed(logical(b"", status=status))
            self.assertEqual(caught.exception.status, status)
            self.assert_latched(parser)
        parser = self.parser()
        with self.assertRaises(RemoteStatusError):
            parser.feed(header(7) + b"ABC\0\0\0\0")  # data before status

    def test_incomplete_status_is_not_zero_status(self):
        parser = self.parser()
        parser.feed(header(4) + b"\0\0\0")
        with self.assertRaises(IncompleteCapture):
            parser.finish()

    def test_setpath_ack_data_rejected(self):
        parser = ResponseAssembler([Expectation(1, 15)], profile="fx3-static-version3-candidate")
        with self.assertRaises(ParseError):
            parser.feed(header(5, sequence=1))

    def test_single_segment_exact_boundary(self):
        data = b"x" * (SEGMENT_BYTES - 4)
        parser = self.parser(max_data=len(data))
        raw = logical(data)
        self.assertEqual(len(raw), SEGMENT_BYTES + 12)
        parser.feed(raw)
        self.assertEqual(parser.finish().replies[0].data, data)

    def test_remaining_size_continuation_and_status_only_once(self):
        data = b"x" * (SEGMENT_BYTES - 4) + b"\x06\0\0\x10ABCD"
        parser = self.parser(max_data=len(data))
        raw = logical(data)
        self.assertEqual(raw[SEGMENT_BYTES + 12:SEGMENT_BYTES + 24], header(8))
        for offset in range(0, len(raw), 0x8000):
            parser.feed(raw[offset:offset + 0x8000])
        self.assertEqual(parser.finish().replies[0].data, data)

    def test_missing_continuation_header_or_payload(self):
        data = b"x" * SEGMENT_BYTES
        raw = logical(data)
        for cut in (SEGMENT_BYTES + 12, len(raw) - 1):
            parser = self.parser(max_data=len(data))
            parser.feed(raw[:cut])
            with self.assertRaises(IncompleteCapture):
                parser.finish()

    def test_wrong_remaining_size_continuation(self):
        data = b"x" * SEGMENT_BYTES
        raw = logical(data)
        boundary = SEGMENT_BYTES + 12
        parser = self.parser(max_data=len(data))
        with self.assertRaises(ParseError):
            parser.feed(raw[:boundary] + header(3) + raw[boundary + 12:])
        self.assert_latched(parser)

    def test_default_bound_rejects_large_continuation_header(self):
        parser = self.parser()
        with self.assertRaises(ParseError):
            parser.feed(header(SEGMENT_BYTES + 4))

    def test_cumulative_capture_limit(self):
        parser = self.parser()
        with self.assertRaises(ParseError):
            parser.feed(b"x" * (MAX_CAPTURE_BYTES + 1))
        self.assert_latched(parser)

    def test_explicit_failed_capture_cannot_release_prefix(self):
        for reason in ("timeout with partial data", "overflow", "disconnected", "unknown end"):
            parser = self.parser()
            parser.feed(GOLDEN_READ_V3)
            with self.assertRaises(ParseError):
                parser.abort(reason)
            self.assert_latched(parser)

    def test_input_plan_types_limits_and_write_contexts(self):
        for args in [(0, 17), (65536, 17), (True, 17), (1, 16), (1, 18), (1, 0x4011)]:
            with self.assertRaises(ParseError):
                Expectation(*args)
        for bound in (-1, True, MAX_DATA_BYTES + 1):
            with self.assertRaises(ParseError):
                Expectation(1, 17, bound)
        for plan in ([], [Expectation(1, 17), Expectation(3, 17)], [Expectation(1, 17)] * 9):
            with self.assertRaises(ParseError):
                ResponseAssembler(plan, profile="fx3-static-version3-candidate")
        parser = self.parser()
        with self.assertRaises(ParseError):
            parser.feed(bytearray(GOLDEN_READ_V3))

    def test_finalization_cannot_be_reopened(self):
        parser = self.parser()
        parser.feed(GOLDEN_READ_V3)
        parser.finish()
        with self.assertRaises(ParseError):
            parser.feed(b"")
        with self.assertRaises(ParseError):
            parser.finish()

    def test_empty_read_and_zero_data_budget(self):
        parser = self.parser(max_data=0)
        parser.feed(logical(b""))
        self.assertEqual(parser.finish().replies[0].data, b"")

    def test_exact_manifest_rejects_wrong_total_at_header(self):
        for declared in (4 + FX3_APPFW_EXPECTED_BYTES - 1, 4 + FX3_APPFW_EXPECTED_BYTES + 1):
            parser = ResponseAssembler([Expectation(2, 17, FX3_APPFW_EXPECTED_BYTES,
                                                     FX3_APPFW_EXPECTED_BYTES)],
                                       profile="fx3-static-version3-candidate")
            with self.assertRaises(ParseError):
                parser.feed(header(declared))
            self.assert_latched(parser)

    def test_large_bound_requires_exact_manifest_and_single_read(self):
        with self.assertRaises(ParseError):
            Expectation(2, 17, FX3_APPFW_EXPECTED_BYTES)
        with self.assertRaises(ParseError):
            Expectation(2, 17, MAX_MANIFEST_DATA_BYTES + 1, MAX_MANIFEST_DATA_BYTES + 1)
        with self.assertRaises(ParseError):
            Expectation(2, 17, 100, 101)
        with self.assertRaises(ParseError):
            ResponseAssembler([Expectation(1, 15), Expectation(2, 17, FX3_APPFW_EXPECTED_BYTES,
                                                           FX3_APPFW_EXPECTED_BYTES)],
                              profile="fx3-static-version3-candidate")

    def test_79015712_byte_generated_manifest_readback(self):
        size = FX3_APPFW_EXPECTED_BYTES
        parser = ResponseAssembler([Expectation(2, 17, size, size)],
                                   profile="fx3-static-version3-candidate")
        # Generate at most 32 KiB at a time. No target file, network, or backend.
        pattern = bytes(range(256)) * 130
        expected_hash = hashlib.sha256()
        remaining = size + 4
        data_offset = 0
        first = True
        segment_count = 0
        wire_bytes = 0
        while remaining:
            parser.feed(header(remaining))
            segment_count += 1
            wire_bytes += 12
            body = min(remaining, SEGMENT_BYTES)
            if first:
                parser.feed(b"\0" * 4)
                body -= 4
                wire_bytes += 4
                first = False
            while body:
                count = min(body, 0x8000)
                start = data_offset % 256
                chunk = pattern[start:start + count]
                parser.feed(chunk)
                expected_hash.update(chunk)
                data_offset += count
                wire_bytes += count
                body -= count
            remaining -= min(remaining, SEGMENT_BYTES)
        capture = parser.finish()
        result = capture.replies[0].data
        actual_hash = hashlib.sha256(result).hexdigest()
        self.assertEqual(len(result), 79015712)
        self.assertEqual(actual_hash, expected_hash.hexdigest())
        self.assertEqual(data_offset, size)
        self.assertEqual(segment_count, 76)
        self.assertEqual(wire_bytes, size + 4 + 76 * 12)
        self.assertFalse(capture.target_verified)
        self.assertFalse(capture.usb_termination_verified)
        print("MANIFEST_FIXTURE bytes=%d segments=%d wire_bytes=%d sha256=%s" %
              (len(result), segment_count, wire_bytes, actual_hash))

    def test_exact_manifest_rejects_bytes_after_completed_payload(self):
        parser = ResponseAssembler([Expectation(2, 17, 3, 3)],
                                   profile="fx3-static-version3-candidate")
        parser.feed(GOLDEN_READ_V3)
        with self.assertRaises(ParseError):
            parser.feed(b"x")
        self.assert_latched(parser)

    def test_own_parser_has_only_bytes_related_stdlib_imports(self):
        tree = ast.parse(Path(__file__).with_name("offline_reassembly.py").read_text())
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertEqual(imports, {"dataclasses", "struct"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
