#!/usr/bin/env python3
"""Read-only member-by-member verification of the fixed-length CPIO replacement."""
import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/hybrid-ap-candidate/guest-three-entry.cpio')
OUT = ROOT / 'guest-hybrid-fx6kernel.cpio'
TARGET = b'simulation/fx3-cp-backup-reset-v1.ko'
FIXED = 453184500


def sha(b):
    return hashlib.sha256(b).hexdigest()


def parse(path):
    rows = []
    with Path(path).open('rb') as f:
        while True:
            start = f.tell()
            header = f.read(110)
            if len(header) != 110:
                raise ValueError('short header at ' + str(start))
            if header[:6] != b'070701':
                raise ValueError('not newc')
            namesize = int(header[94:102], 16)
            filesize = int(header[54:62], 16)
            name = f.read(namesize)
            name_pad = f.read((4 - (110 + namesize) % 4) % 4)
            payload = f.read(filesize)
            payload_pad = f.read((4 - filesize % 4) % 4)
            rows.append({'start': start, 'header': header, 'name_raw': name,
                         'name': name.rstrip(b'\0').decode('utf-8', 'replace'),
                         'name_pad': name_pad, 'payload': payload,
                         'payload_pad': payload_pad, 'filesize': filesize})
            if name.rstrip(b'\0') == b'TRAILER!!!':
                break
        end = f.tell()
        trailing = f.read()
    return rows, end, trailing


def main():
    src, src_end, src_tail = parse(SRC)
    out, out_end, out_tail = parse(OUT)
    src_names = [r['name'] for r in src]
    out_names = [r['name'] for r in out]
    assert src_names == out_names, 'member order/name changed'
    target_rows = []
    for a, b in zip(src, out):
        if a['name'] == TARGET.decode():
            target_rows.append((a, b))
            assert b['payload'] == (ROOT / 'fx6-cp-backup-sync100-agnostic-g0.ko').read_bytes()
            assert b['filesize'] == len(b['payload'])
            assert b['header'][54:62] == f'{len(b["payload"]):08x}'.encode()
            assert b['header'][:54] == a['header'][:54] and b['header'][62:] == a['header'][62:]
            continue
        assert a['name_raw'] == b['name_raw'], (a['name'], 'name raw')
        assert a['name_pad'] == b['name_pad'], (a['name'], 'name pad')
        assert a['payload'] == b['payload'], (a['name'], 'payload')
        assert a['payload_pad'] == b['payload_pad'], (a['name'], 'payload pad')
        assert a['header'] == b['header'], (a['name'], 'header')
    assert len(target_rows) == 1
    a, b = target_rows[0]
    assert OUT.stat().st_size == FIXED
    assert len(out_tail) == FIXED - out_end and set(out_tail) == {0}
    result = {
        'schema': 'fx6-hybrid-fx6kernel-cpio-verify-v1',
        'source': str(SRC), 'source_bytes': SRC.stat().st_size,
        'source_sha256': hashlib.sha256(SRC.read_bytes()).hexdigest(),
        'output': str(OUT), 'output_bytes': OUT.stat().st_size,
        'output_sha256': hashlib.sha256(OUT.read_bytes()).hexdigest(),
        'member_count': len(src), 'target_member': a['name'],
        'target_old_bytes': a['filesize'], 'target_new_bytes': b['filesize'],
        'target_old_sha256': sha(a['payload']), 'target_new_sha256': sha(b['payload']),
        'all_other_members_byte_identical': True,
        'target_header_only_size_changed': True,
        'trailer_present': out_names[-1] == 'TRAILER!!!',
        'trailing_bytes_after_trailer': len(out_tail),
        'trailing_all_zero': set(out_tail) == {0},
        'fixed_length_preserved': OUT.stat().st_size == FIXED,
        'verdict': 'pass_offline_member_replacement'}
    (ROOT / 'HYBRID-CPIO-VERIFY.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
