"""Read-only audit of the pinned A7C II patch against two local program files.

This never patches a file, opens a camera, imports USB code, or permits install.
The supplied spec must be the public JSON at the pinned URL below. Obtain it
separately, then provide --spec. Reports are new files beside this script only.
"""
import argparse
import hashlib
import json
from pathlib import Path
import stat

SPEC_URL = 'https://raw.githubusercontent.com/QAQLeonard/a7c2-fl23-research/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/assets/patches.json'
SPEC_SHA256 = '92931b700112c5b906dc255f79be9943df1d0f7d28ea9b366e6f74f00cb16a9d'
SOURCE_MODEL, SOURCE_VERSION = 'ILCE-7CM2', '2.01'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def regular(path):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError('Only regular, non-symlink local input files are allowed')


def audit(spec_path, paths, model, version):
    regular(spec_path)
    if digest(spec_path) != SPEC_SHA256:
        raise ValueError('Patch description differs from the pinned public source')
    specs = json.loads(spec_path.read_text())
    if len(specs) != 2:
        raise ValueError('Unexpected patch description format')
    blocks = []
    reasons = []
    if model != SOURCE_MODEL:
        reasons.append('target_model_mismatch')
    if version != SOURCE_VERSION:
        reasons.append('target_firmware_mismatch')
    for index, (spec, path) in enumerate(zip(specs, paths, strict=True)):
        regular(path)
        before = path.stat()
        actual_hash = digest(path)
        rows = []
        ends = []
        with path.open('rb') as stream:
            for window in spec['writes']:
                offset = int(window['file_offset'], 16)
                old, new = bytes.fromhex(window['before_hex']), bytes.fromhex(window['after_hex'])
                if not old or len(old) != len(new) or offset < 0:
                    raise ValueError('Malformed public patch window')
                ends.append((offset, offset + len(old)))
                in_bounds = offset + len(old) <= before.st_size
                stream.seek(offset)
                current = stream.read(len(old)) if in_bounds else b''
                rows.append({'offset': hex(offset), 'bytes': len(old),
                             'in_bounds': in_bounds, 'expected_before_matches': current == old,
                             'purpose': window.get('purpose')})
        ends.sort()
        if any(a[1] > b[0] for a, b in zip(ends, ends[1:])):
            raise ValueError('Public patch contains overlapping windows')
        after = path.stat()
        if (before.st_ino, before.st_size, before.st_mtime_ns) != (after.st_ino, after.st_size, after.st_mtime_ns):
            raise ValueError('Input changed while being audited')
        base_matches = actual_hash == spec['source_sha256']
        if not base_matches:
            reasons.append(f'program_{index}_whole_file_hash_mismatch')
        if not all(r['in_bounds'] and r['expected_before_matches'] for r in rows):
            reasons.append(f'program_{index}_window_preconditions_mismatch')
        blocks.append({'path': str(path.resolve()), 'size': before.st_size,
                       'actual_sha256': actual_hash, 'required_sha256': spec['source_sha256'],
                       'whole_file_hash_matches': base_matches, 'windows': rows})
    return {'scope': 'offline portability audit; not an installer or patch generator',
            'source_model': SOURCE_MODEL, 'source_firmware': SOURCE_VERSION,
            'source_spec_url': SPEC_URL, 'source_spec_sha256': SPEC_SHA256,
            'target_model_declared': model, 'target_firmware_declared': version,
            'decision': 'reject_port_as_is' if reasons else 'offline_base_checks_only',
            'blocked_reasons': reasons, 'camera_write_allowed': False, 'programs': blocks}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--ap', type=Path, required=True)
    parser.add_argument('--cp', type=Path, required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--firmware', required=True)
    parser.add_argument('--report-name', default='fx3-vs-a7c2-compatibility.json')
    args = parser.parse_args()
    if Path(args.report_name).name != args.report_name or not args.report_name.endswith('.json'):
        parser.error('Report name must be one JSON filename')
    result = audit(args.spec, [args.ap, args.cp], args.model, args.firmware)
    output = Path(__file__).resolve().parent / args.report_name
    with output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(result['decision'], str(output))


if __name__ == '__main__':
    main()
