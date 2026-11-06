import struct
from parse_v25_diag_r3 import CAPACITY, HEADER, MAGIC, RECORDS, STRIDE, parse


def fixture(total, entries, dropped=0):
    data = bytearray(RECORDS + CAPACITY * STRIDE)
    struct.pack_into('<6Q', data, HEADER, MAGIC, 2, total, CAPACITY, STRIDE, dropped)
    for serial, event, link, ns in entries:
        struct.pack_into('<12Q', data, RECORDS + (serial - 1) % CAPACITY * STRIDE,
                         serial, ns, 900, event, 5738, 5532, 0x2886049,
                         0x6005, 0, 1, 0x402, link)
    return data


def main():
    data = fixture(2, [(1, 5, 0, 100), (2, 6, 1, 120)])
    assert parse(data, quiesced=True)['pairs'][0]['duration_guest_ns'] == 20
    for field, value, fault in ((2, 901, 'identity_tid'), (4, 5739, 'identity_committed_seq'),
                                (5, 5533, 'identity_source_seq'), (6, 0x99, 'identity_id'),
                                (7, 0x1005, 'identity_op'), (9, 2, 'identity_epoch'),
                                (10, 0x403, 'identity_token'), (1, 90, 'nonmonotonic_guest_time'),
                                (11, 2, 'link_not_before_return')):
        broken = bytearray(data)
        struct.pack_into('<Q', broken, RECORDS + STRIDE + field * 8, value)
        assert fault in parse(broken, quiesced=True)['pairs'][0]['faults'], field
    data = fixture(3, [(1, 5, 0, 100), (2, 6, 1, 120), (3, 6, 1, 130)])
    assert 'duplicate_return_link' in parse(data, quiesced=True)['pairs'][1]['faults']
    data = fixture(1, [(1, 5, 0, 100)])
    assert parse(data, quiesced=True)['unpaired_enters_in_tail'][0]['classification'] == 'unpaired_at_quiesced_snapshot'
    assert parse(data)['unpaired_enters_in_tail'][0]['classification'] == 'unknown_possible_lost_return'
    data = fixture(1, [(1, 5, 0, 100)], dropped=1)
    assert parse(data, quiesced=True)['unpaired_enters_in_tail'][0]['classification'] == 'unknown_possible_lost_return'
    data = fixture(257, [(257, 6, 1, 120)])
    assert 'enter_outside_tail' in parse(data, quiesced=True)['pairs'][0]['faults']
    data = fixture(2, [(1, 5, 0, 100), (2, 6, 1, 120)])
    struct.pack_into('<Q', data, RECORDS, 0)
    assert parse(data, quiesced=True)['invalid_or_torn_slots'][0]['reason'] == 'missing_or_torn'
    try:
        parse(data[:HEADER+8])
    except ValueError:
        pass
    else:
        raise AssertionError('truncation accepted')
    print('v25-r3 parser identity/time/link/duplicate/loss/wrap/torn/truncated PASS')


if __name__ == '__main__':
    main()
