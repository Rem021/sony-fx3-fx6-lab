#!/usr/bin/env python3
"""Bounded Sony LDEC block decoder, pure Python 3 standard library.

The caller supplies the exact output size (including bitmap row padding).
No guest/hardware operations. See lz77_format.md for evidence and limits.
"""
from dataclasses import dataclass, field
import argparse
from pathlib import Path
import struct
import zlib

LENGTHS = tuple(range(3, 17)) + (32, 64)
MAX_BYTES = 16 * 1024 * 1024


class DecodeError(ValueError):
    def __init__(self, code, offset, produced):
        self.code, self.offset, self.produced = code, offset, produced
        super().__init__(f"{code}: input+0x{offset:x}, output+0x{produced:x}")


@dataclass
class DecodeInfo:
    input_bytes: int = 0
    output_bytes: int = 0
    literals: int = 0
    matches: int = 0
    max_distance: int = 0
    block_sizes: list = field(default_factory=list)
    block_types: list = field(default_factory=list)
    raw_reserved: list = field(default_factory=list)
    terminator_codes: list = field(default_factory=list)


def decode_details(source, output_size):
    """Return (bytes, DecodeInfo), rejecting incomplete, excess or invalid data.

    History resets at each block. A distance of zero ends an f0 block;
    unused bits of its flag byte are ignored. No bytes after the last block
    are silently discarded. 0f raw block byte 1 is reserved/ignored.
    """
    if not isinstance(source, (bytes, bytearray, memoryview)):
        raise TypeError("source must be bytes-like")
    if not isinstance(output_size, int) or not 0 < output_size <= MAX_BYTES:
        raise DecodeError("size_limit", 0, 0)
    source = bytes(source)  # private immutable snapshot; no TOCTOU
    if not 0 < len(source) <= MAX_BYTES:
        raise DecodeError("size_limit", 0, 0)
    out = bytearray()
    info = DecodeInfo()
    pos = 0

    def fail(code):
        raise DecodeError(code, pos, len(out))

    while pos < len(source):
        block_start = len(out)
        kind = source[pos]
        pos += 1
        if kind == 0x0f:
            if len(source) - pos < 3:
                fail("truncated_raw_header")
            reserved = source[pos]
            count = int.from_bytes(source[pos + 1:pos + 3], "little")
            pos += 3
            if count > len(source) - pos:
                fail("truncated_raw_data")
            if count > output_size - len(out):
                fail("output_overflow")
            out.extend(source[pos:pos + count])
            pos += count
            info.raw_reserved.append(reserved)
        elif kind == 0xf0:
            ended = False
            while not ended:
                if pos == len(source):
                    fail("missing_terminator")
                flags = source[pos]
                pos += 1
                for bit in range(8):
                    if flags & (1 << bit):
                        if len(source) - pos < 2:
                            fail("truncated_match")
                        first, second = source[pos], source[pos + 1]
                        pos += 2
                        distance = ((first & 15) << 8) | second
                        if distance == 0:
                            info.terminator_codes.append(first >> 4)
                            ended = True
                            break
                        count = LENGTHS[first >> 4]
                        if distance > len(out) - block_start:
                            fail("invalid_distance")
                        if count > output_size - len(out):
                            fail("output_overflow")
                        # Forward copy intentionally permits overlap (RLE).
                        pattern = out[-distance:]
                        out.extend((pattern * ((count + distance - 1) // distance))[:count])
                        info.matches += 1
                        info.max_distance = max(info.max_distance, distance)
                    else:
                        if pos == len(source):
                            fail("truncated_literal")
                        if len(out) == output_size:
                            fail("output_overflow")
                        out.append(source[pos])
                        pos += 1
                        info.literals += 1
        else:
            fail("unknown_block_type")
        info.block_sizes.append(len(out) - block_start)
        info.block_types.append(kind)
    if len(out) != output_size:
        fail("output_size_mismatch")
    info.input_bytes, info.output_bytes = pos, len(out)
    return bytes(out), info


def decode_ldec(source, output_size):
    """Decode with exact input consumption and exact output length."""
    return decode_details(source, output_size)[0]


def rgba4444(raw, width, height):
    """Crop align16-pixel row padding; LE R12 G8 B4 A0 -> RGBA8."""
    stride = (width + 15) & ~15
    if width <= 0 or height <= 0 or len(raw) != stride * height * 2:
        raise ValueError("invalid dimensions/raw length")
    rgba = bytearray(width * height * 4)
    at = 0
    for y in range(height):
        for x in range(width):
            p = 2 * (y * stride + x)
            value = raw[p] | raw[p + 1] << 8
            rgba[at:at + 4] = bytes(((value >> 12) * 17, ((value >> 8) & 15) * 17,
                                     ((value >> 4) & 15) * 17, (value & 15) * 17))
            at += 4
    return bytes(rgba)


def write_png(path, width, height, rgba):
    """Write RGBA8 PNG using only the standard library."""
    if len(rgba) != width * height * 4:
        raise ValueError("incorrect RGBA byte count")
    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))
    scan = b"".join(b"\0" + rgba[y * width * 4:(y + 1) * width * 4] for y in range(height))
    Path(path).write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
                           + chunk(b"IDAT", zlib.compress(scan, 9)) + chunk(b"IEND", b""))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path)
    p.add_argument("output", type=Path)
    p.add_argument("--size", type=int, required=True)
    p.add_argument("--width", type=int)
    p.add_argument("--height", type=int)
    args = p.parse_args()
    raw, info = decode_details(args.input.read_bytes(), args.size)
    if args.width is not None or args.height is not None:
        if args.width is None or args.height is None:
            p.error("PNG requires both --width and --height")
        write_png(args.output, args.width, args.height, rgba4444(raw, args.width, args.height))
    else:
        args.output.write_bytes(raw)
    print(f"decoded {info.input_bytes} -> {info.output_bytes} bytes, {len(info.block_sizes)} blocks")


if __name__ == "__main__":
    main()
