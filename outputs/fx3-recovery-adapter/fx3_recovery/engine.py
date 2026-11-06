"""Real local-image adaptation and exact inverse reconstruction. No live backend."""
from hashlib import sha256, md5
import re
import struct
import zlib
from .fat import FatP1, MAX_P1
from .files import require, read_file, encode, new_directory, local_path
from .profiles import PROFILE, LIBRARIES, REFERENCE_IMAGES, patched_library
from .squash import SquashFS, inflate_bounded

INITRD = '/boot/initrd.img'
KERNEL = '/boot/vmlinux.bin'
CHECKSUM = '/p1chksum'
MAX_JSON = 2*1024*1024


def sha(raw):return sha256(raw).hexdigest()


def checksum_pair(fat, initrd=None):
    text = fat.contents(CHECKSUM)
    require(re.fullmatch(rb'[0-9a-f]{32}  \./boot/vmlinux\.bin\n[0-9a-f]{32}  \./boot/initrd\.img\n', text) is not None,
            'unsupported P1 checksum format')
    rows = text.splitlines()
    require(rows[0][:32] == md5(fat.contents(KERNEL)).hexdigest().encode(), 'kernel MD5 differs')
    require(rows[1][:32] == md5(fat.contents(INITRD)).hexdigest().encode(), 'initrd MD5 differs')
    if initrd is None:return text
    return rows[0]+b'\n'+md5(initrd).hexdigest().encode()+b'  ./boot/initrd.img\n'


def inspect_image(raw):
    fat = FatP1(raw)
    checksum_pair(fat)
    initrd = fat.contents(INITRD)
    fs = SquashFS(initrd)
    rows = list(fs.walk())
    names = [r['path'] for r in rows]
    require(len(names) == len(set(names)), 'duplicate SquashFS path')
    selected, compatible = [], True
    for name, spec in LIBRARIES.items():
        entry = next((r for r in rows if r['path'] == name), None)
        require(entry and entry['type'] == 'file', 'updater component absent or not regular: '+name)
        data = fs.contents(entry)
        match = len(data) == spec['bytes'] and sha(data) == spec['sha256']
        compatible &= match
        selected.append({'path': name, 'bytes': len(data), 'sha256': sha(data), 'reference_profile_match': match})
    digest = sha(raw)
    return {
        'schema': 'fx3-p1-inspection-v1', 'model_profile': 'ILME-FX3', 'intended_body_firmware': '7.02',
        'image_bytes': len(raw), 'sha256': digest,
        'recognized_reference': REFERENCE_IMAGES.get(digest),
        'image_origin_and_current_body_identity_verified': False,
        'component_profile': PROFILE, 'component_profile_match': bool(compatible),
        'FAT_geometry': {'sector_bytes': fat.sector, 'cluster_sectors': fat.cluster_sectors, 'clusters': fat.clusters},
        'boot_members': [{'path': p, 'bytes': len(fat.contents(p)), 'sha256': sha(fat.contents(p))} for p in (INITRD, KERNEL, CHECKSUM)],
        'libraries': selected,
        'flashable': False, 'hardware_validated': False, 'contains_HEVC_feature_patch': False,
    }


def block_groups(raw):
    fat = FatP1(raw);checksum_pair(fat)
    fs = SquashFS(fat.contents(INITRD))
    rows = {r['path']: r for r in fs.walk()}
    groups = {}
    for name, spec in LIBRARIES.items():
        entry = rows.get(name)
        require(entry is not None and entry['type'] == 'file', 'missing reference component')
        original = fs.contents(entry)
        modified = patched_library(original, spec)
        require(entry['size'] < fs.header['block_size'] and entry['fragment'] != 0xffffffff,
                'component is not in a supported single SquashFS fragment')
        index = entry['fragment'];table_at = fs.header['fragment_table_start']+(index*16//8192)*8
        pointer = struct.unpack('<Q', fs.read(table_at, 8))[0]
        start, encoded, unused = struct.unpack('<QII', fs.stream(pointer, index*16%8192, 16))
        packed_size = encoded & 0xffffff
        require(not encoded & (1 << 24) and 0 < packed_size <= 131072, 'unsupported fragment encoding')
        packed = fs.read(start, packed_size)
        plain = fs.block(start, encoded)
        require(len(plain) <= 131072, 'fragment plaintext limit')
        off = entry['fragment_offset']
        require(plain[off:off+len(original)] == original, 'library fragment mapping differs')
        key = (start, packed_size)
        group = groups.setdefault(key, {'start': start, 'packed': packed, 'plain': plain, 'target': bytearray(plain), 'libraries': []})
        require(group['plain'] == plain and not any(max(off, p['offset']) < min(off+len(original), p['offset']+p['bytes']) for p in group['libraries']),
                'overlapping library fragment mappings')
        group['target'][off:off+len(original)] = modified
        group['libraries'].append({'path': name, 'offset': off, 'bytes': len(original), 'before_sha256': sha(original), 'after_sha256': sha(modified)})
    return fat, fs, list(groups.values())


def pack_same_size(plain, wanted):
    """Exact stream, no padding/truncation. Fail if bounded search cannot preserve span."""
    def one(split):
        c = zlib.compressobj(9)
        return c.compress(plain[:split])+c.flush(zlib.Z_SYNC_FLUSH)+c.compress(plain[split:])+c.flush(zlib.Z_FINISH)
    direct = zlib.compress(plain, 9)
    if len(direct) == wanted:return direct, 1
    for attempts, at in enumerate(range(0, len(plain)+1, 128), 2):
        value = one(at)
        if len(value) == wanted:
            require(inflate_bounded(value, 131072) == plain, 'new compressed stream differs')
            return value, attempts
    raise ValueError('cannot reproduce compressed fragment size; no output candidate created')


def merge_spans(spans):
    result = []
    for at, count in sorted(spans):
        require(at >= 0 and count > 0, 'bad span')
        if result and at <= result[-1][0]+result[-1][1]:
            begin, size = result[-1];result[-1] = (begin, max(begin+size, at+count)-begin)
        else:result.append((at, count))
    return result


def outside_equal(before, after, spans):
    if len(before) != len(after):return False
    cursor = 0
    for at, count in merge_spans(spans):
        if before[cursor:at] != after[cursor:at]:return False
        cursor = at+count
    return before[cursor:] == after[cursor:]


def verify_derivative(before, after):
    fat, fs, groups = block_groups(before)
    require(len(before) == len(after), 'candidate image size changed')
    candidate = FatP1(after);checksum_pair(candidate)
    initrd = candidate.contents(INITRD)
    spans, records = [], []
    for group in groups:
        begin, n = group['start'], len(group['packed'])
        packed = initrd[begin:begin+n]
        require(inflate_bounded(packed, 131072) == bytes(group['target']), 'candidate fragment has extra/missing plaintext changes')
        spans.extend(fat.mapping(INITRD, begin, n))
        records.append({'initrd_offset': begin, 'bytes': n, 'before_sha256': sha(group['packed']),
                        'after_sha256': sha(packed), 'libraries': group['libraries']})
    spans.extend(fat.mapping(CHECKSUM))
    require(outside_equal(before, after, spans), 'unexpected bytes outside reviewed fragment/checksum spans')
    require(candidate.contents(CHECKSUM) == checksum_pair(fat, initrd), 'candidate checksum changed outside initrd MD5')
    # Independent read of the new filesystem must recover precisely the intended libraries.
    parsed = SquashFS(initrd);entries = {r['path']: r for r in parsed.walk()}
    for group in groups:
        for record in group['libraries']:
            require(sha(parsed.contents(entries[record['path']])) == record['after_sha256'], 'new filesystem library readback differs')
    return {'groups': records, 'spans': [{'offset': a, 'bytes': n, 'before_sha256': sha(before[a:a+n]), 'after_sha256': sha(after[a:a+n])}
                                        for a, n in merge_spans(spans)]}


def build_image(raw):
    fat, fs, groups = block_groups(raw)
    output = bytearray(raw)
    compression = []
    for group in groups:
        packed, attempts = pack_same_size(bytes(group['target']), len(group['packed']))
        fat.replace(output, INITRD, group['start'], packed)
        compression.append({'initrd_offset': group['start'], 'attempts': attempts, 'packed_bytes_preserved': len(packed)})
    new_initrd = FatP1(bytes(output)).contents(INITRD)
    fat.replace(output, CHECKSUM, 0, checksum_pair(fat, new_initrd))
    result = bytes(output)
    verification = verify_derivative(raw, result)
    return result, {'compression': compression, **verification}


def binding(scope, source, body_tag):
    if scope == 'reference':
        require(sha(source) in REFERENCE_IMAGES and body_tag is None, 'reference scope requires a pinned historical FX3 image, without body tag')
        return {'scope': scope, 'reference': REFERENCE_IMAGES[sha(source)], 'camera_verified': False}
    require(scope == 'unverified-snapshot' and len(source) == MAX_P1 and
            isinstance(body_tag, str) and re.fullmatch('[0-9a-f]{64}', body_tag), 'full local snapshot and opaque64hex body tag required')
    return {'scope': scope, 'operator_body_tag': body_tag, 'camera_verified': False}


def create_bundle(source_path, destination, scope='reference', body_tag=None):
    raw = read_file(source_path, MAX_P1)
    origin = binding(scope, raw, body_tag)
    inspection = inspect_image(raw)
    require(inspection['component_profile_match'], 'FX3 component profile mismatch; A7CII offsets are not accepted')
    result, evidence = build_image(raw)
    manifest = {'schema': 'fx3-offline-recovery-bundle-v1', 'tool_version': '0.1.0', 'model': 'ILME-FX3',
                'intended_body_firmware': '7.02', 'profile': PROFILE, 'binding': origin, 'image_bytes': len(raw),
                'source_sha256': sha(raw), 'candidate_sha256': sha(result), 'inspection': inspection,
                'transformation': evidence, 'flashable': False, 'hardware_validated': False,
                'current_body_p1_identity_verified': False, 'contains_HEVC_feature_patch': False,
                'complete_DAT_builder_or_camera_transport': False}
    new_directory(destination, {'source.p1': raw, 'candidate.p1': result, 'manifest.json': encode(manifest)})
    return {'status': 'OFFLINE_CANDIDATE_VERIFIED', 'source_sha256': sha(raw), 'candidate_sha256': sha(result),
            'scope': scope, 'flashable': False, 'HEVC_unlocked': False}


def load_bundle(directory):
    directory = local_path(directory)
    import json
    def unique(pairs):
        value = {}
        for key, item in pairs:
            require(key not in value, 'duplicate JSON key')
            value[key] = item
        return value
    manifest = json.loads(read_file(directory/'manifest.json', MAX_JSON), object_pairs_hook=unique)
    require(type(manifest) is dict and manifest.get('schema') == 'fx3-offline-recovery-bundle-v1' and
            manifest.get('model') == 'ILME-FX3' and manifest.get('profile') == PROFILE and
            manifest.get('intended_body_firmware') == '7.02' and manifest.get('flashable') is False and
            manifest.get('tool_version') == '0.1.0' and manifest.get('hardware_validated') is False and
            manifest.get('contains_HEVC_feature_patch') is False and manifest.get('current_body_p1_identity_verified') is False and
            manifest.get('complete_DAT_builder_or_camera_transport') is False,
            'bundle scope/schema differs')
    source = read_file(directory/'source.p1', MAX_P1)
    candidate = read_file(directory/'candidate.p1', MAX_P1)
    require(len(source) == manifest['image_bytes'] and sha(source) == manifest['source_sha256'] and
            sha(candidate) == manifest['candidate_sha256'], 'bundle image hash differs')
    b = manifest['binding']
    require(binding(b['scope'], source, b.get('operator_body_tag')) == b, 'bundle binding differs')
    require(inspect_image(source) == manifest['inspection'] and verify_derivative(source, candidate) ==
            {k: v for k, v in manifest['transformation'].items() if k != 'compression'},
            'bundle reconstruction/verification differs')
    return manifest, source, candidate


def diagnose(directory, current_path):
    manifest, source, candidate = load_bundle(directory)
    current = read_file(current_path, MAX_P1)
    if current == source:state = 'ORIGINAL'
    elif current == candidate:state = 'CANDIDATE'
    elif len(current) != len(source):state = 'UNKNOWN_SIZE'
    else:
        spans = [(r['offset'], r['bytes']) for r in manifest['transformation']['spans']]
        known = all(current[a:a+n] in (source[a:a+n], candidate[a:a+n]) for a, n in spans)
        state = 'MIXED_KNOWN_SPANS' if known and outside_equal(source, current, spans) else 'UNKNOWN_BYTES'
    return {'state': state, 'current_sha256': sha(current), 'automatic_device_repair_allowed': False,
            'offline_rollback_allowed': state in ('ORIGINAL', 'CANDIDATE')}


def rollback(directory, current_path, destination):
    manifest, source, candidate = load_bundle(directory)
    current = read_file(current_path, MAX_P1)
    require(current in (source, candidate), 'unknown or mixed image: rollback denied; preserve for manual review')
    receipt = {'schema': 'fx3-offline-rollback-v1', 'input_state': 'ORIGINAL' if current == source else 'CANDIDATE',
               'restored_sha256': sha(source), 'source_sha256': manifest['source_sha256'],
               'byte_identical_to_backup': True, 'camera_restore_proven': False, 'flashable': False}
    new_directory(destination, {'restored.p1': source, 'receipt.json': encode(receipt)})
    return receipt
