#!/usr/bin/env python3
"""Exercise the actual readback parser's wrap, pairing, and torn-record gates."""
import struct
from parse_v25_diag import CAPACITY, HEADER, MAGIC, RECORDS, STRIDE, parse


def fixture(total, rows):
    data = bytearray(RECORDS + CAPACITY * STRIDE)
    struct.pack_into("<5Q", data, HEADER, MAGIC, 1, total, CAPACITY, STRIDE)
    for serial, event, tid, ns, link in rows:
        struct.pack_into("<12Q", data, RECORDS + (serial - 1) % CAPACITY * STRIDE,
                         serial, ns, tid, event, 5739, 5532, 0x2886049,
                         0x6005, 0, 1, 0x402, link)
    return data


def main():
    data = fixture(4, [(1, 5, 900, 10, 0), (2, 6, 900, 20, 1),
                       (3, 7, 900, 30, 0), (4, 8, 900, 40, 3)])
    result = parse(data)
    assert [p["duration_guest_ns"] for p in result["pairs"]] == [10, 10]
    assert all(p["valid_within_tail"] for p in result["pairs"])
    assert result["unpaired_enters_in_tail"] == []
    # A commit can occur while a native wait is outstanding. The pair's
    # entry snapshot stays attached to the return instead of using the new
    # global committed sequence as the old return-only log did.
    data = fixture(3, [(1, 5, 900, 10, 0), (2, 4, 900, 20, 0),
                       (3, 6, 900, 30, 1)])
    struct.pack_into("<Q", data, RECORDS + 0 * STRIDE + 4 * 8, 5738)
    struct.pack_into("<Q", data, RECORDS + 1 * STRIDE + 4 * 8, 5739)
    struct.pack_into("<Q", data, RECORDS + 2 * STRIDE + 4 * 8, 5738)
    result = parse(data)
    assert [r["committed_seq"] for r in result["rows"]] == [5738, 5739, 5738]
    assert result["pairs"][0]["duration_guest_ns"] == 20
    data = fixture(258, [(3, 5, 900, 100, 0), (257, 6, 900, 150, 3),
                         (258, 7, 900, 200, 0)])
    result = parse(data)
    assert result["tail_first_serial"] == 3
    assert result["invalid_or_torn_serials"][0] == 4
    assert result["pairs"][0]["duration_guest_ns"] == 50
    assert result["unpaired_enters_in_tail"] == [258]
    data[RECORDS + (257 % CAPACITY) * STRIDE] = 0
    result = parse(data)
    assert 258 in result["invalid_or_torn_serials"]
    try:
        parse(bytes(data[:HEADER + 8]))
    except ValueError:
        pass
    else:
        raise AssertionError("truncated readback accepted")
    print("v25 parser: pair, interleaved commit, wrap, open wait, torn slot, truncated header PASS")


if __name__ == "__main__":
    main()
