"""Source-only SPI inspection. Decode saved bytes; never execute them."""
from pathlib import Path
from hashlib import sha256
import json, struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
SRC = BASE / 'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin'
EXPECTED = '4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
VA = 0xfe049000
d = SRC.read_bytes()
assert sha256(d).hexdigest() == EXPECTED
c = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)
c.detail = True

def put(name, value):
    with (HERE / name).open('x') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

def string_at(addr):
    off = addr - VA
    if not 0 <= off < len(d):
        return None
    s = d[off:off+180].split(b'\0', 1)[0]
    if len(s) < 4 or any(v not in (9, 10, 13) and not 32 <= v < 127 for v in s):
        return None
    return s.decode('ascii')

def normal_edges(ins):
    if ins.mnemonic == 'ret':
        return []
    if ins.mnemonic == 'b':
        return [ins.operands[-1].imm]
    if ins.mnemonic.startswith('b.') or ins.mnemonic in ('cbz', 'cbnz', 'tbz', 'tbnz'):
        return [ins.operands[-1].imm, ins.address+4]
    assert ins.mnemonic not in ('br', 'blr'), f'indirect branch {ins.address:#x}'
    return [ins.address+4]

ranges = [
    ('spi-state-consumer', 0xfe054c88, 0xfe055724),
    ('first-spi-input', 0xfe05c03c, 0xfe05c22c),
    ('initial-handshake', 0xfe05c22c, 0xfe05c2d4),
    ('bootdata-import', 0xfe059198, 0xfe059218),
    ('common-first-spi', 0xfe05331c, 0xfe0533f4),
    ('mode-get-and-set', 0xfe053ab4, 0xfe053c78),
]
evidence = []
for label, start, end in ranges:
    raw = d[start-VA:end-VA]
    instructions = list(c.disasm(raw, start))
    assert len(instructions)*4 == len(raw)
    known = {}
    strings = []
    lines = []
    edges = {}
    for ins in instructions:
        ops = ins.operands
        comment = ''
        if ins.mnemonic == 'adrp':
            known[ins.reg_name(ops[0].reg)] = ops[1].imm
        elif ins.mnemonic == 'add' and len(ops) == 3 and ops[1].type == ARM64_OP_REG and ops[2].type == ARM64_OP_IMM:
            sr = ins.reg_name(ops[1].reg)
            dr = ins.reg_name(ops[0].reg)
            if sr in known:
                addr = known[sr] + (ops[2].imm << ops[2].shift.value)
                known[dr] = addr
                value = string_at(addr)
                if value:
                    comment = ' ; source string candidate ' + repr(value)
                    strings.append({'site': hex(ins.address), 'address': hex(addr), 'value': value})
        else:
            for reg in ins.regs_access()[1]:
                known.pop(ins.reg_name(reg), None)
        if ins.mnemonic == 'bl':
            for k in range(19):
                known.pop('x'+str(k), None)
        elif ins.mnemonic in ('b', 'ret') or ins.mnemonic.startswith('b.'):
            known.clear()
        edges[hex(ins.address)] = [hex(a) for a in normal_edges(ins)]
        lines.append(f'{ins.address:#x} [file+{ins.address-VA:#x}] {ins.bytes.hex()} {ins.mnemonic:8} {ins.op_str}{comment}')
    with (HERE/(label+'.txt')).open('x') as f:
        f.write('# Exact original configured VA; ordinary-call-return CFG; not runtime PC. No execution.\n'+'\n'.join(lines)+'\n')
    if label == 'spi-state-consumer':
        allowed = set(range(start, end, 4))
        reachable = set()
        stack = [start]
        while stack:
            at = stack.pop()
            if at in reachable:
                continue
            assert at in allowed, f'outside selected function {at:#x}'
            reachable.add(at)
            stack.extend(int(x, 16) for x in edges[hex(at)])
        put('spi-state-cfg.json', {'scope': 'both conditional successors; ordinary BL returns; no callees executed or guaranteed to return',
             'start': hex(start), 'end_exclusive': hex(end), 'edges': edges,
             'reachable_instructions': len(reachable), 'instructions': len(instructions),
             'normal_returns': [hex(i.address) for i in instructions if i.mnemonic == 'ret'],
             'calls': [{'site': hex(i.address), 'target': hex(i.operands[0].imm)} for i in instructions if i.mnemonic == 'bl']})
    evidence.append({'label': label, 'start': hex(start), 'end_exclusive': hex(end),
                     'sha256': sha256(raw).hexdigest(), 'bytes': len(raw),
                     'instructions': len(instructions), 'string_candidates': strings})
put('source-slices.json', {'source': str(SRC), 'sha256': EXPECTED,
    'configured_VA': hex(VA), 'original_or_guest_execution': False,
    'source_unchanged': sha256(SRC.read_bytes()).hexdigest() == EXPECTED, 'ranges': evidence})
print(json.dumps({'slices': len(evidence), 'state_consumer_instructions': evidence[0]['instructions'],
                  'original_or_guest_execution': False, 'device_operations': 0}))
