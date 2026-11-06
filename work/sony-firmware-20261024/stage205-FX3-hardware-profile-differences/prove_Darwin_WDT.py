"""Source-bound current FX3 MCU counter and reload references, without execution."""
from pathlib import Path
from hashlib import sha256
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_LITTLE_ENDIAN
import json, struct, re
H = Path(__file__).resolve().parent
B = H.parent
R = H.parents[2]
src = B / 'stage198-AP-CP-loaders-and-partition-selection/originals/darwin_core.bin'
d = src.read_bytes()
expected = 'ac3fe4cb9d7122b196d33ca3514d0eb4e2d3abbed882926d4e08d5b26b76afe0'
assert sha256(d).hexdigest() == expected
base = 0x4200
u16 = lambda a: struct.unpack_from('<H', d, a - base)[0]
u32 = lambda a: struct.unpack_from('<I', d, a - base)[0]
def literal(a):
    w = u16(a)
    assert w & 0xf800 == 0x4800
    pool = ((a + 4) & ~3) + (w & 255) * 4
    return pool, u32(pool)
def bl(a):
    x, y = u16(a), u16(a + 2)
    assert x & 0xf800 == 0xf000 and y & 0xd000 == 0xd000
    s = (x >> 10) & 1
    imm = (s << 24) | ((1 ^ (((y >> 13) & 1) ^ s)) << 23) | ((1 ^ (((y >> 11) & 1) ^ s)) << 22) | ((x & 1023) << 12) | ((y & 2047) << 1)
    if s:
        imm -= 1 << 25
    return a + 4 + imm
refs = [0x64ee, 0x6502, 0x651a, 0x654c]
for a in refs:
    assert literal(a) == (0x65b4, 0x200026fc)
assert u16(0x64ea) == 0x22ff and u16(0x64ec) == 0x2104
assert u16(0x651c) == 0x20ff
# Direct byte counter consumer: skip0xFF, decrement one, return1 on zero.
assert u16(0x6552) == 0x29ff and u16(0x6556) == 0x1e49
assert u16(0x6560) == 0x2001
reloads = []
for slot, load_base, byte_load, call in [(0, 0x8d34, 0x8de8, 0x8dee), (1, 0x8f90, 0x8f92, 0x8f98), (2, 0x9042, 0x907a, 0x9080)]:
    pool, value = literal(load_base)
    assert value == 0x20000000 and bl(call) == 0x64f4
    first, second = u16(byte_load), u16(byte_load + 2)
    assert first & 0xfff0 == 0xf890 and second >> 12 == 1
    assert first & 15 == (u16(load_base) >> 8) & 7
    assert second & 4095 == 0x3c + slot
    assert u16(call - 2) == 0x2000 + slot
    reloads.append(dict(slot=slot, base_load=hex(load_base), base_pool=hex(pool),
        byte_load=hex(byte_load), source_address=hex(value + 0x3c + slot), setter_call=hex(call)))
header = H / 'reference/payloads/fastboot/include/darwin.h'
text = header.read_text()
assert re.search(r'#define\s+VWDT_TABLE\s+0x200026FCu', text)
assert re.search(r'#define\s+VWDT_RELOAD\s+0x2000003Cu', text)
md = Cs(CS_ARCH_ARM, CS_MODE_THUMB | CS_MODE_LITTLE_ENDIAN)
cuts = []
for a, z, label, data_only in [(0x64ea, 0x652a, 'WDT-init-set-disable', False),
    (0x652a, 0x6574, 'WDT-counter-consumer', False), (0x65b4, 0x65b8, 'WDT-address-pool', True),
    (0x8d32, 0x8d3c, 'WDT-reload0-base', False), (0x8de8, 0x8df2, 'WDT-reload0-call', False),
    (0x8f90, 0x8f9c, 'WDT-reload1-call', False), (0x9042, 0x9044, 'WDT-reload2-base', False),
    (0x907a, 0x9084, 'WDT-reload2-call', False), (0x8f70, 0x8f74, 'WDT-base-pool0', True),
    (0x9374, 0x9378, 'WDT-base-pool12', True)]:
    part = d[a - base:z - base]
    out = H / 'pins' / (label + '.txt')
    out.parent.mkdir(exist_ok=True)
    lines = [hex(a) + ' DATA ' + part.hex()] if data_only else [f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}' for i in md.disasm(part, a)]
    out.open('x').write('\n'.join(lines) + '\n')
    cuts.append(dict(start=hex(a), end_exclusive=hex(z), bytes=len(part), sha256=sha256(part).hexdigest(),
        data_not_code=data_only, output=str(out.relative_to(R))))
result = dict(status='FX3_CURRENT_MCU_COUNTER_AND_THREE_RELOAD_SOURCES_MATCH_REFERENCE_ADDRESSES',
    source=str(src.relative_to(R)), source_sha256=expected, source_layout_base=hex(base),
    counter_table='0x200026fc', counter_pool='0x65b4', counter_literal_references=[hex(a) for a in refs],
    initializer_declared_bytes=4, disabled_sentinel=255, decrement_consumer='0x652a',
    zero_case='returns1; physical shutdown/reset caller and timing not established in this proof',
    reload_source_examples=reloads, reference_header_sha256=sha256(header.read_bytes()).hexdigest(),
    selected_ranges=cuts, actual_live_counter_state_read=False,
    SIO_channel_pins_command16_or_keepalive_compatibility_proven=False,
    limits=['static same addresses are not the same whole MCU firmware or protocol compatibility',
            'reload examples bind3 call sites only; not an exhaustive classification of all setters',
            'slots0/2 use callee-saved base registers across intervening calls; their source association assumes normal ARM procedure-call preservation, not symbolic execution of all callees',
            'no time unit, timeout, RAM write, feed/disable operation or failure recovery has been measured'],
    original_or_guest_execution=False, root_or_device_operations=0)
(H / 'Darwin-WDT-source-proof.json').open('x').write(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(counter_table='0x200026fc', reload_examples=len(reloads), source_ranges=len(cuts),
    live_state_read=False, actual_device_operations=0)))
