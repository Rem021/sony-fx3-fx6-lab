import ctypes
import random
import unittest
from decode_ldec import decode_ldec, DecodeError, LENGTHS


def packed_block(tokens):
    """Independent synthetic encoder; tokens are literal int or (length_code,dist)."""
    tokens = list(tokens) + [(0, 0)]
    out = bytearray([0xf0])
    for at in range(0, len(tokens), 8):
        group = tokens[at:at + 8]
        flags = sum((1 << i) for i, token in enumerate(group) if isinstance(token, tuple))
        out.append(flags)
        for token in group:
            if isinstance(token, tuple):
                code, distance = token
                out.extend((code << 4 | distance >> 8, distance & 255))
            else:
                out.append(token)
    return bytes(out)


class DecoderTests(unittest.TestCase):
    cdecode = None

    def both(self, source, expected):
        self.assertEqual(decode_ldec(source, len(expected)), expected)
        if self.cdecode:
            status, data = self.cdecode(source, len(expected))
            self.assertEqual(status, 0)
            self.assertEqual(data, expected)

    def reject(self, source, length):
        with self.assertRaises(DecodeError): decode_ldec(source, length)
        if self.cdecode:
            status, data = self.cdecode(source, length)
            self.assertNotEqual(status, 0)
            self.assertEqual(data, b"\xa5" * length, "C failure must not modify destination")

    def test_all_lengths_overlap(self):
        for code, count in enumerate(LENGTHS):
            self.both(packed_block([65, (code, 1)]), b"A" * (1 + count))

    def test_flag_order_and_groups(self):
        self.both(packed_block(list(b"abcdefghij") + [(5, 10)]), b"abcdefghijabcdefgh")

    def test_short_pattern_overlap(self):
        self.both(packed_block([65,66,(15,2)]), b"AB" * 33)

    def test_fixed_fx3_small_stream(self):
        # Actual image_02_43 index1840. Public length table predicts 128 B.
        # This tests the real stream without depending on originals at test time.
        self.both(bytes.fromhex("f07c0f0df002e002d002b0020000"), b"\x0f\x0d" * 64)

    def test_raw_and_multiblock(self):
        raw = b"\x0f\xa7\x03\0XYZ"
        self.both(raw + packed_block([65,(14,1)]), b"XYZ" + b"A" * 33)

    def test_reset_history(self):
        self.reject(packed_block([65,66]) + packed_block([(0,1)]), 5)

    def test_boundaries(self):
        good = packed_block([65,66,(15,2)])
        for end in range(len(good)): self.reject(good[:end], 66)
        self.reject(good, 65)
        self.reject(good, 67)
        self.reject(good + b"\0", 66)
        self.reject(b"\x0f\0\x03\0ab", 3)
        self.reject(packed_block([(1,1)]), 4)
        self.reject(b"\x21", 1)

    def test_zero_distance_terminator(self):
        for code in range(16):
            self.both(bytes([0xf0, 2, 65, code << 4, 0]), b"A")

    def test_max_distance(self):
        # 4095 byte distance; the 4KiB hardware record size is not a parser cap.
        seed = bytes(i % 251 for i in range(4095))
        self.both(packed_block(list(seed) + [(15,4095)]), seed + seed[:64])

    def test_random_synthetic(self):
        rng = random.Random(0x1dec)
        for _ in range(200):
            expected = bytearray()
            tokens = []
            for _ in range(rng.randrange(1,80)):
                if expected and rng.random() < .65:
                    code = rng.randrange(16)
                    dist = rng.randrange(1, min(len(expected),4095) + 1)
                    tokens.append((code,dist))
                    for _ in range(LENGTHS[code]): expected.append(expected[-dist])
                else:
                    value = rng.randrange(256)
                    tokens.append(value); expected.append(value)
            self.both(packed_block(tokens), bytes(expected))


if __name__ == "__main__": unittest.main()
