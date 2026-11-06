"""Audit this own capsule's rebasing and bind completed tests/builds to sources.

This is not a Linux loader, an original firmware executor or device admission.
"""
from pathlib import Path
from hashlib import sha256
import ast, collections, difflib, json, struct
import bridge_build as D

H = Path(__file__).resolve().parent
def load(p): return json.loads(p.read_text())
def digest(p): return sha256(p.read_bytes()).hexdigest()
def put(name, value):
    with (H / name).open('x') as f:
        f.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

raw = (H / 'build-first/bridge.elf').read_bytes()
b = load(H / 'build-first/build.json')
r = load(H / 'reproducible-build/build.json')
t = load(H / 'runs-bridge-verified/receipt.json')
assert b['sha256'] == r['sha256'] == t['binary_sha256'] == sha256(raw).hexdigest()
assert raw == (H / 'reproducible-build/bridge.elf').read_bytes()
assert len(raw) == 262144 and t['tests'] == 8 and len(t['cases']) == 27
assert t['errors'] == t['failures'] == 0
assert b['source_pins'] == r['source_pins']
for folder in ['build-first', 'reproducible-build']:
    for name, pin in b['source_pins'].items():
        assert digest(H / name) == digest(H / folder / name) == pin
    for name in ['parent', 'collector', 'bridge']:
        assert (H / folder / (name + '.o.stderr.txt')).read_bytes() == b''
for name, pin in t['source_hashes'].items(): assert digest(H / name) == pin
snap = H / 'runs-bridge-verified/source-snapshot'
snap.mkdir(mode=0o700)
for name, pin in t['source_hashes'].items():
    with (snap / name).open('xb') as f: f.write((H / name).read_bytes())
    assert digest(snap / name) == pin

inverse = {v: k for k, v in D.RELOCATIONS.items()}
deltas = [0, 0x1fc00000, 0x2fc00000, 0x4fc10000, 0x5fc00000]
rows = []
for relocation in b['relocations']:
    kind = inverse[relocation['kind']]
    assert struct.unpack_from('<I', raw, relocation['file_offset'])[0] == relocation['after']
    for delta in deltas:
        assert delta % D.PAGE == 0
        value = D.relocate(relocation['before'], kind,
                           relocation['place'] + delta, relocation['target'] + delta)
        assert value == relocation['after']
    rows.append(dict(file_offset=relocation['file_offset'], kind=relocation['kind'],
                     source_object=relocation['object'], stable_at_all_deltas=True))
assert len(rows) == 128
segments = D.read_executable(raw)
assert [s['flags'] for s in segments] == [4, 5, 4, 6]
assert raw[3 * D.PAGE:] == bytes(D.PAGE)
assert all(not (s['flags'] & 1 and s['flags'] & 2) for s in segments)
for p in H.glob('*.py'): ast.parse(p.read_text(), filename=str(p))

seed = H / 'seed-source'
seed_record = load(seed / 'source-assembly.json')
for name, pin in seed_record['outputs'].items(): assert digest(seed / name) == pin
replay = load(H / 'assembly-replay-receipt.json')
assert replay['status'] == 'PASS' and replay['generator_sha256'] == digest(H / 'assemble_source.py')
for name, pin in replay['files'].items():
    assert digest(H / name) == digest(H / 'assembly-replay' / name) == pin
changes = {}
for name in ['parent.c', 'collector.c', 'assemble_source.py']:
    text = ''.join(difflib.unified_diff((seed / name).read_text().splitlines(True),
                 (H / name).read_text().splitlines(True), fromfile='seed/' + name,
                 tofile='current/' + name))
    changes[name] = dict(seed_sha256=digest(seed / name), current_sha256=digest(H / name),
                         difference=text)
put('source-revisions.json', dict(
    status='CURRENT_ASSEMBLY_REPLAY_MATCHES', changes=changes,
    original_source_assembly_json_is_seed_not_current_output_record=True,
    clock_unit_conversion_seed_bug_corrected_before_first_build=True,
    current_assembly_receipt='assembly-replay-receipt.json'))
put('relocation-audit.json', dict(
    status='PASS_FOR_THIS_FIXED_OWN_CAPSULE', binary_sha256=sha256(raw).hexdigest(),
    relocation_count=len(rows), arithmetic_checks=len(rows)*len(deltas),
    deltas=deltas, kinds=dict(collections.Counter(x['kind'] for x in rows)), rows=rows,
    segments=segments, tested_source_hashes=t['source_hashes'],
    executable_bytes_unchanged_by_uniform_PAGE_aligned_rebase=True,
    arbitrary_images_or_unaligned_bases_supported=False,
    zero_normalized_BSS_hash_is_not_authorization=True,
    original_Linux_loader_or_CPU_cache_coherence_executed_or_verified=False,
    actual_camera_memory_layout_or_stack_lifetime_verified=False,
    first_flash_released=False))
put('reproducible-build-summary.json', dict(
    status='PASS', binary_sha256=sha256(raw).hexdigest(), bytes=len(raw),
    source_pins=b['source_pins'], tested_source_hashes=t['source_hashes'],
    builds=['build-first/build.json', 'reproducible-build/build.json'],
    deployable=False))
print(json.dumps(dict(status='PASS', tests=t['tests'], cases=len(t['cases']),
                      relocations=len(rows), arithmetic_checks=len(rows)*len(deltas))))
