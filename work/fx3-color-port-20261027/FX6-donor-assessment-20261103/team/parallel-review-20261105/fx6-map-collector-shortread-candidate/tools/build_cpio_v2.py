#!/usr/bin/env python3
"""Build/validate the new CPIO from the frozen 3a08 archive.

Only the existing init diagnostic call site (init.patched) and the new helper
member may differ.  All other member headers and content, and the 25,746,348
byte zero tail, are preserved byte-for-byte.
"""
import hashlib, json, sys
from pathlib import Path

ALIGN = 4

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()

def parse(path):
    b = Path(path).read_bytes()
    out = []
    pos = 0
    while True:
        if b[pos:pos+6] != b'070701':
            raise SystemExit('not newc at %d' % pos)
        hdr = b[pos:pos+110]
        vals = [int(hdr[6+i*8:14+i*8], 16) for i in range(13)]
        namesize, filesize = vals[11], vals[6]
        name = b[pos+110:pos+110+namesize]
        start = (pos+110+namesize+ALIGN-1) & ~(ALIGN-1)
        end = start+filesize
        data = b[start:end]
        pos = (end+ALIGN-1) & ~(ALIGN-1)
        out.append({'header': hdr, 'fields': vals, 'name': name.rstrip(b'\0'),
                    'raw_name': name, 'data': data, 'offset': pos})
        if name.rstrip(b'\0') == b'TRAILER!!!':
            break
    return out, b[pos:]

def hdr(fields, name):
    vals = list(fields)
    vals[11] = len(name)+1
    return b'070701' + b''.join(b'%08x' % x for x in vals[:13]) + name + b'\0'

def pad(b):
    return b + b'\0' * ((-len(b)) % ALIGN)

def build(entries, tail):
    out = b''
    for e in entries:
        out += pad(hdr(e['fields'], e['name'])) + pad(e['data'])
    return out + tail

def member_map(entries):
    return {e['name']: e for e in entries if e['name'] != b'TRAILER!!!'}

def main():
    here = Path(__file__).resolve().parent.parent
    orig_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/guest-hybrid-fx6kernel-capid-grmreal46.cpio')
    old_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-map-observer-integration-candidate/work/fx6-map-observer-grmreal46.cpio')
    init_path = here / 'work/init.patched'
    helper_path = here / 'work/fx3-map-snapshot-v2-aarch64'
    out_path = here / 'work/fx6-map-collector-shortread-grmreal46.cpio'
    diff_path = here / 'receipts/cpio-diff-v2.json'
    orig, tail = parse(orig_path)
    old, old_tail = parse(old_path)
    old_by = member_map(old)
    new_helper = helper_path.read_bytes()
    init_data = init_path.read_bytes()
    old_helper = old_by.get(b'simulation/fx3-map-snapshot')
    if old_helper is None:
        raise SystemExit('old candidate helper member missing')
    new = []
    for e in orig:
        if e['name'] == b'TRAILER!!!':
            continue
        q = {'header': e['header'], 'fields': list(e['fields']),
             'name': e['name'], 'data': e['data']}
        if e['name'] == b'init':
            q['data'] = init_data
            q['fields'][6] = len(init_data)
            q['header'] = hdr(q['fields'], q['name'])
        new.append(q)
    # insert new helper before trailer, using the reviewed old-candidate metadata
    h = {'header': None, 'fields': list(old_helper['fields']),
         'name': b'simulation/fx3-map-snapshot', 'data': new_helper}
    h['fields'][6] = len(new_helper)
    h['fields'][0] = max(e['fields'][0] for e in orig if e['name'] != b'TRAILER!!!') + 1
    h['header'] = hdr(h['fields'], h['name'])
    new.append(h)
    trailer = [e for e in orig if e['name'] == b'TRAILER!!!'][0]
    new.append({'header': trailer['header'], 'fields': list(trailer['fields']),
                'name': trailer['name'], 'data': trailer['data']})
    outb = build(new, tail)
    out_path.write_bytes(outb)
    reparsed, re_tail = parse(out_path)
    by = member_map(reparsed)
    # full diff vs original
    mismatches = []
    unchanged = 0
    for e in orig:
        if e['name'] == b'TRAILER!!!':
            continue
        q = by.get(e['name'])
        if q is None:
            mismatches.append({'name': e['name'].decode(), 'why': 'missing'})
        elif e['name'] == b'init':
            if q['data'] != init_data:
                mismatches.append({'name': 'init', 'why': 'init data not patched'})
        elif e['data'] != q['data'] or e['header'] != q['header']:
            mismatches.append({'name': e['name'].decode(), 'why': 'unexpected change'})
        else:
            unchanged += 1
    helper = by.get(b'simulation/fx3-map-snapshot')
    if helper is None or helper['data'] != new_helper:
        mismatches.append({'name': 'simulation/fx3-map-snapshot', 'why': 'helper missing/wrong'})
    if len(reparsed) != len(new) or re_tail != tail:
        mismatches.append({'why': 'reparse structure/tail mismatch'})
    # minimal diff vs old candidate
    old_changes = []
    for name, e in old_by.items():
        q = by.get(name)
        if q is None:
            old_changes.append({'name': name.decode(), 'why': 'missing'})
        elif e['data'] != q['data'] or e['header'] != q['header']:
            old_changes.append({'name': name.decode(), 'why': 'changed'})
    report = {
        'schema': 'fx6-map-collector-cpio-diff-v2',
        'original': str(orig_path), 'original_sha256': sha(orig_path),
        'old_candidate': str(old_path), 'old_candidate_sha256': sha(old_path),
        'new': str(out_path), 'new_sha256': sha(out_path), 'new_bytes': len(outb),
        'tail_padding_bytes': len(tail), 'reparsed_tail_bytes': len(re_tail),
        'original_count': len(member_map(orig)),
        'old_candidate_count': len(member_map(old)),
        'new_count': len(member_map(reparsed)),
        'unchanged_members': unchanged,
        'only_expected_changes': not mismatches,
        'mismatches': mismatches,
        'old_candidate_to_new_changes': old_changes,
        'only_helper_changed_from_old_candidate': old_changes == [{'name': 'simulation/fx3-map-snapshot', 'why': 'changed'}],
        'actual_reparse_ok': not mismatches and re_tail == tail and len(reparsed) == len(new),
        'init': {'bytes': len(init_data), 'sha256': hashlib.sha256(init_data).hexdigest(),
                 'original_bytes': len(member_map(orig)[b'init']['data']),
                 'new_header_matches_old_candidate': by[b'init']['header'] == old_by[b'init']['header']},
        'helper': {'bytes': len(new_helper), 'sha256': hashlib.sha256(new_helper).hexdigest(),
                   'old_candidate_bytes': len(old_helper['data']),
                   'metadata_preserved_from_old_candidate': helper['header'] == hdr(old_helper['fields'], old_helper['name']) if False else None},
        'note': 'newc archive rebuilt from frozen 3a08; only init data and new helper differ; zero tail preserved',
    }
    diff_path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('new', 'new_sha256', 'new_bytes', 'new_count',
        'unchanged_members', 'only_expected_changes', 'actual_reparse_ok',
        'old_candidate_to_new_changes', 'only_helper_changed_from_old_candidate',
        'tail_padding_bytes', 'init', 'helper')}, indent=2))
    return 0 if report['only_expected_changes'] and report['actual_reparse_ok'] and report['only_helper_changed_from_old_candidate'] else 1

if __name__ == '__main__':
    sys.exit(main())
