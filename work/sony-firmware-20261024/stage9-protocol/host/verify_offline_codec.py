"""Own synthetic fixtures; import ONLY the adjacent own offline codec."""

import ast
from pathlib import Path
import struct
import unittest

from offline_codec import (CodecError, MissingCandidate, RemoteStatusError,
                           MAX_DATA_BYTES, encode_read, encode_setpath, parse_reply)

READ_REQUEST = bytes.fromhex("0700000040000200000000000110110000ff00")
PATH_REQUEST = bytes.fromhex(
    "18000000400001000000000001100f0000"
    "2f746d702f6a6972697473752f662e62696e00")
READ_REPLY = bytes.fromhex("07000000400002000000000000000000414243")
PATH_REPLY = bytes.fromhex("04000000400001000000000000000000")


def reply(*, size=None, pfunc=0x40, sequence=2, flags=(0, 0, 0, 0), status=0, data=b""):
    body = struct.pack("<I", status) + data
    return struct.pack("<IHHBBBB", len(body) if size is None else size,
                       pfunc, sequence, *flags) + body


class OfflineFixtures(unittest.TestCase):
    def parse_read(self, data, **kwargs):
        return parse_reply(data, expected_sequence=2, expected_command=17, **kwargs)

    def test_independent_golden_requests(self):
        self.assertEqual(encode_read(sequence=2), READ_REQUEST)
        self.assertEqual(encode_setpath("/tmp/jiritsu/f.bin", sequence=1), PATH_REQUEST)

    def test_independent_golden_replies(self):
        self.assertEqual(self.parse_read(READ_REPLY).data, b"ABC")
        self.assertEqual(parse_reply(PATH_REPLY, expected_sequence=1, expected_command=15).data, b"")

    def test_every_truncated_prefix(self):
        for length in range(len(READ_REPLY)):
            with self.subTest(length=length), self.assertRaises(CodecError):
                self.parse_read(READ_REPLY[:length])

    def test_trailing_bytes(self):
        with self.assertRaises(CodecError):
            self.parse_read(READ_REPLY + b"extra")

    def test_declared_length_too_small_or_large(self):
        for size in (0, 1, 2, 3, 6, 8, 0xFFFFFFFF):
            with self.subTest(size=size), self.assertRaises(CodecError):
                self.parse_read(reply(size=size, data=b"ABC"))

    def test_mismatched_sequence_or_function(self):
        for frame in (reply(sequence=1), reply(pfunc=0x20), reply(pfunc=0xFF01)):
            with self.assertRaises(CodecError):
                self.parse_read(frame)

    def test_unsupported_outer_flags_and_response(self):
        for index in range(4):
            flags = [0, 0, 0, 0]
            flags[index] = 1
            with self.subTest(index=index), self.assertRaises(CodecError):
                self.parse_read(reply(flags=flags))

    def test_missing_candidate_is_not_success(self):
        with self.assertRaises(MissingCandidate) as caught:
            self.parse_read(reply(status=0x10000006))
        self.assertEqual(caught.exception.status, 0x10000006)

    def test_unknown_remote_status_is_not_success(self):
        with self.assertRaises(RemoteStatusError):
            self.parse_read(reply(status=0xDEADBEEF))

    def test_nonzero_status_with_payload_is_rejected(self):
        with self.assertRaises(CodecError):
            self.parse_read(reply(status=0x10000006, data=b"hidden"))

    def test_setpath_extra_data_rejected(self):
        with self.assertRaises(CodecError):
            parse_reply(reply(data=b"extra"), expected_sequence=2, expected_command=15)

    def test_empty_read_is_valid(self):
        self.assertEqual(self.parse_read(reply()).data, b"")

    def test_exact_local_boundary_and_one_over(self):
        self.assertEqual(len(self.parse_read(reply(data=b"x" * MAX_DATA_BYTES)).data), MAX_DATA_BYTES)
        with self.assertRaises(CodecError):
            self.parse_read(reply(data=b"x" * (MAX_DATA_BYTES + 1)))

    def test_smaller_custom_bound(self):
        self.assertEqual(self.parse_read(READ_REPLY, max_data_bytes=3).data, b"ABC")
        with self.assertRaises(CodecError):
            self.parse_read(READ_REPLY, max_data_bytes=2)

    def test_invalid_bounds_and_types(self):
        for limit in (-1, MAX_DATA_BYTES + 1, True, None):
            with self.subTest(limit=limit), self.assertRaises(CodecError):
                self.parse_read(READ_REPLY, max_data_bytes=limit)
        for data in (None, bytearray(READ_REPLY), "bytes"):
            with self.subTest(kind=type(data).__name__), self.assertRaises(CodecError):
                self.parse_read(data)

    def test_no_write_command_context(self):
        for command in (16, 18, 1, 0x400F, 0x4011, True):
            with self.subTest(command=command), self.assertRaises(CodecError):
                parse_reply(READ_REPLY, expected_sequence=2, expected_command=command)

    def test_sequence_validation_no_wrap(self):
        for sequence in (0, -1, 65536, True, "1"):
            with self.subTest(sequence=sequence), self.assertRaises(CodecError):
                encode_read(sequence=sequence)

    def test_path_policy_excludes_traversal_and_controls(self):
        for path in ("/usr/lib/appFw.so", "/tmp/jiritsu/../a", "/tmp/jiritsu/../../a",
                     "/tmp/jiritsu//a", "/tmp/jiritsu/./a", "/tmp/jiritsu/",
                     "/tmp/jiritsu/a\0b", "/tmp/jiritsu/a\nb", "/tmp/jiritsu/中文",
                     "/tmp/jiritsu/" + "a" * 511, None):
            with self.subTest(path=path), self.assertRaises(CodecError):
                encode_setpath(path, sequence=1)

    def test_codec_imports_are_stdlib_bytes_only(self):
        tree = ast.parse(Path(__file__).with_name("offline_codec.py").read_text())
        imports = {node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)}
        imports |= {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
        self.assertEqual(imports, {"dataclasses", "struct"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
