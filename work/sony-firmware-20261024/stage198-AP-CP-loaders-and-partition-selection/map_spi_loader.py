"""Decode loader_spi bytes at a tentative VA; output locators, not reachability."""
from pathlib import Path
from hashlib import sha256
import json, struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
from capstone.arm64 import ARM64_OP_IMM, ARM64_OP_REG, ARM64_OP_MEM
H = Path(__file__).resolve().parent
p = H/'originals/loader_spi.bin'
d = p.read_bytes()
assert sha256(d).hexdigest() == '314d372d0d2b9883c3b9dc04b40389edb3100e6d5ef529633cc427c3d0cab72e'
VA = 0xfe049000
c = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN); c.detail = True
instructions = {}
for off in range(0,len(d)-3,4):
    ins = list(c.disasm(d[off:off+4], VA+off, count=1))
    if ins:
        instructions[VA+off] = ins[0]
def canon(reg):
    n = c.reg_name(reg)
    return 'x'+n[1:] if n.startswith('w') else n
known = {}; refs = []; branches = []
for ins in instructions.values():
    old = known.copy(); ops=ins.operands; values={}
    if ins.mnemonic in ('bl','b') and ops and ops[0].type==ARM64_OP_IMM:
        branches.append({'site_offset':hex(ins.address-VA),'kind':ins.mnemonic,'target_offset':hex(ops[0].imm-VA)})
    if ins.mnemonic in ('adr','adrp'):
        values[canon(ops[0].reg)] = ops[1].imm
    elif ins.mnemonic in ('add','sub') and len(ops)==3 and ops[1].type==ARM64_OP_REG and ops[2].type==ARM64_OP_IMM and canon(ops[1].reg) in old:
        v=old[canon(ops[1].reg)]+(1 if ins.mnemonic=='add' else -1)*(ops[2].imm<<ops[2].shift.value)
        values[canon(ops[0].reg)]=v
        if VA<=v<VA+len(d):
            raw=d[v-VA:v-VA+160].split(b'\0')[0]
            if len(raw)>=4 and all(a in (10,13,9) or 32<=a<127 for a in raw):
                refs.append({'site_offset':hex(ins.address-VA),'VA_if_base_correct':hex(ins.address),'literal_offset':hex(v-VA),'string':raw.decode('ascii'),'candidate_only':True})
    elif ins.mnemonic=='mov' and len(ops)==2:
        if ops[1].type==ARM64_OP_IMM:
            values[canon(ops[0].reg)]=ops[1].imm
        elif ops[1].type==ARM64_OP_REG and canon(ops[1].reg) in old:
            values[canon(ops[0].reg)]=old[canon(ops[1].reg)]
    elif ins.mnemonic=='movk' and len(ops)==2 and canon(ops[0].reg) in old:
        sh=ops[1].shift.value; values[canon(ops[0].reg)]=(old[canon(ops[0].reg)]&~(65535<<sh))|(ops[1].imm<<sh)
    for r in ins.regs_access()[1]: known.pop(canon(r),None)
    known.update(values)
    if ins.mnemonic=='bl':
        for k in range(19):known.pop('x'+str(k),None)
    elif ins.mnemonic in ('b','br','ret'): known.clear()
with (H/'spi-loader-all-locators.txt').open('x') as f:
    f.write('# Every aligned word, including data. Tentative base only. Not complete reachable-code disassembly.\n')
    for i in instructions.values():f.write(f'{i.address:#x} [file+{i.address-VA:#x}] {i.bytes.hex()} {i.mnemonic:8} {i.op_str}\n')
with (H/'spi-loader-locators.json').open('x') as f:
    json.dump({'source_sha256':sha256(d).hexdigest(),'tentative_base':hex(VA),
        'scope':'all aligned words may include data; literal-reference candidates only, no runtime/reachability proof',
        'base_clues':{'literal_file0x618':hex(struct.unpack_from('<Q',d,0x618)[0]),'literal_file0x620':hex(struct.unpack_from('<Q',d,0x620)[0])},
        'references':refs,'direct_branch_candidates':branches,'Sony_or_guest_code_executed':False},f,indent=2);f.write('\n')
print(json.dumps({'reference_candidates':len(refs),'branch_locator_count':len(branches)}))
