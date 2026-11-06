"""Independent raw A64 branch/selected-field audit, not firmware execution."""
from pathlib import Path
from hashlib import sha256
import json, struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
HERE = Path(__file__).resolve().parent
BASE = HERE.parent
VA = 0xfe049000
SRC = BASE/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin'
d = SRC.read_bytes()
EXPECTED = '4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
assert sha256(d).hexdigest() == EXPECTED

def put(n, v):
    with (HERE/n).open('x') as f:
        json.dump(v, f, ensure_ascii=False, indent=2)
        f.write('\n')

def word(a):
    return struct.unpack_from('<I', d, a-VA)[0]

def sign(x, bits):
    return x-(1 << bits) if x & (1 << (bits-1)) else x

def branch(a):
    w = word(a)
    if w & 0xfffffc1f == 0xd65f0000:
        return []
    if w & 0x7c000000 == 0x14000000:
        return [a+4] if w & 0x80000000 else [a+sign(w & 0x3ffffff, 26)*4]
    if w & 0xff000010 == 0x54000000 or w & 0x7e000000 == 0x34000000:
        return [a+sign((w >> 5) & 0x7ffff, 19)*4, a+4]
    if w & 0x7e000000 == 0x36000000:
        return [a+sign((w >> 5) & 0x3fff, 14)*4, a+4]
    assert w & 0xfffffc1f not in (0xd61f0000, 0xd63f0000), hex(a)
    return [a+4]

cfg = json.loads((HERE/'spi-state-cfg.json').read_text())
edges = {hex(a): [hex(x) for x in branch(a)] for a in range(0xfe054c88, 0xfe055724, 4)}
assert cfg['edges'] == edges
assert cfg['instructions'] == cfg['reachable_instructions'] == 679
assert cfg['normal_returns'] == ['0xfe0556d4']

def bl_target(a, expected):
    w = word(a)
    assert w & 0xfc000000 == 0x94000000
    actual = a+sign(w & 0x3ffffff, 26)*4
    assert actual == expected, hex(a)
    return {'site': hex(a), 'target': hex(actual), 'word': hex(w)}

calls = [bl_target(a, b) for a,b in [
    (0xfe05c158, 0xfe05c424), (0xfe05c194, 0xfe04b45c),
    (0xfe05c1a4, 0xfe04b45c), (0xfe05334c, 0xfe05c03c),
    (0xfe053380, 0xfe04b45c), (0xfe053388, 0xfe059198),
    (0xfe059208, 0xfe053eb0), (0xfe051fe0, 0xfe053ab4),
    (0xfe05b224, 0xfe054c88), (0xfe054ca4, 0xfe053c78)]]

# Assert original raw bytes for fields rather than trusting mnemonic prose.
# ADD X0,SP,#0x10; output prefix memcpy length0x38; imported+0x30;
# setter/getter same global address; COMMON copy to context+0x1b4.
fixed_words = {
    0xfe05c148: 0x910043e0,
    0xfe05c198: 0x910043e1,
    0xfe05c19c: 0x321d0be2,
    0xfe059204: 0xb9403000,
    0xfe053eb0: 0xd0000068,
    0xfe053eb4: 0xb905d500,
    0xfe053ab4: 0xd0000068,
    0xfe053ab8: 0xb945d500,
    0xfe051fe4: 0xb901b660,
    0xfe05c06c: 0x321c03e8,
    0xfe05c0b8: 0x7100045f,
    0xfe05c144: 0x321a07e8,
    0xfe05c448: 0xb900003f,
}
for a,w in fixed_words.items():
    assert word(a) == w, (hex(a), hex(word(a)), hex(w))
set_off = ((word(0xfe053eb4) >> 10) & 0xfff)*4
get_off = ((word(0xfe053ab8) >> 10) & 0xfff)*4
assert set_off == get_off == 0x5d4
input_off = ((word(0xfe059204) >> 10) & 0xfff)*4
context_off = ((word(0xfe051fe4) >> 10) & 0xfff)*4
assert input_off == 0x30 and context_off == 0x1b4

c = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
selected = []
extra = [('mode-setter', 0xfe053eb0, 0xfe053ebc),
         ('context-mode-copy', 0xfe051fd8, 0xfe051ffc),
         ('SPI-peripheral-receive', 0xfe05c424, 0xfe05c55c),
         ('power-sequence-caller', 0xfe05b0e0, 0xfe05b268)]
for label,a,z in extra:
    raw = d[a-VA:z-VA]
    ins = list(c.disasm(raw, a))
    assert len(ins)*4 == len(raw)
    text = '# Original configured VA only. No execution.\n' + ''.join(
        f'{i.address:#x} [file+{i.address-VA:#x}] {i.bytes.hex()} {i.mnemonic:8} {i.op_str}\n' for i in ins)
    target = HERE/(label+'.txt')
    if target.exists():
        assert target.read_text() == text
    else:
        with target.open('x') as f:
            f.write(text)
    selected.append({'label': label, 'start': hex(a), 'end_exclusive': hex(z),
        'sha256': sha256(raw).hexdigest(), 'bytes': len(raw), 'instructions': len(ins)})

# Decode actual COMMON table records. Flag0x8000 remains conditional,
# so context-mode-copy is not promoted to unconditional boot reachability.
table = []
for off in range(0x18870, 0x18a50, 32):
    a, flags = struct.unpack_from('<QQ', d, off)
    name = d[off+16:off+32].split(b'\0')[0].decode('ascii').strip()
    table.append({'VA': hex(VA+off), 'target': hex(a), 'flags': hex(flags), 'name': name})
assert table[4]['target'] == '0xfe05331c' and table[4]['flags'] == '0x1'
assert table[12]['target'] == '0xfe051fd8' and table[12]['flags'] == '0x8000'

# Scan every aligned word, including possible data; results are locator
# candidates only. Absence does not prove no indirect caller or alias.
targets = {0xfe054c88, 0xfe053eb0, 0xfe05c03c, 0xfe051fd8}
refs = []
for off in range(0, len(d)-3, 4):
    w = struct.unpack_from('<I', d, off)[0]
    if w & 0xfc000000 == 0x94000000:
        target = VA+off+sign(w & 0x3ffffff, 26)*4
        if target in targets:
            refs.append({'site': hex(VA+off), 'target': hex(target), 'candidate_only': True})
put('raw-source-verification.json', {
    'sha256': EXPECTED, 'SPI_state_CFG_raw_encoding_matches': True,
    'instructions': 679, 'reachable_in_local_overapproximation': 679,
    'normal_returns': ['0xfe0556d4'],
    'initial_underbounded_window': {'end_exclusive': '0xfe0556d8',
        'rejected': True, 'reason': 'direct conditional successor reaches post-RET tail block',
        'corrected_end_exclusive': '0xfe055724', 'artifact_preserved': 'spi-state-initial-window.txt'},
    'exact_BL_targets': calls,
    'raw_words_checked': {hex(a): hex(w) for a,w in fixed_words.items()},
    'mode_dataflow': {'received_payload_offset': hex(input_off),
        'destination_global': hex(0xfe061000+set_off),
        'readback_global': hex(0xfe061000+get_off),
        'context_offset_if_Copy_BM_BF_row_executes': hex(context_off),
        'wire_command': 1, 'caller_length_counter_initial_value': 192,
        'receiver_clears_length_counter_on_entry': True,
        'initial_value_is_not_a_proven_receive_bound': True,
        'prefix_copy_bytes': 56, 'remote_controller_identity_established': False,
        'actual_received_length_validation_proven': False,
        'p1_or_p3_selection_proven': False},
    'COMMON_table': table, 'additional_source_ranges': selected,
    'aligned_BL_locator_candidates': refs,
    'locator_scan_scope': 'all aligned words include possible data; no exhaustive indirect/alias/reachability claim',
    'original_or_guest_execution': False, 'root_or_device_operations': 0,
    'source_unchanged': sha256(SRC.read_bytes()).hexdigest() == EXPECTED})
print(json.dumps({'independent_raw_CFG': 'PASS', 'checked_BL_targets': len(calls),
    'checked_raw_fields': len(fixed_words), 'mode_global': '0xfe0615d4',
    'original_or_guest_execution': False}))
