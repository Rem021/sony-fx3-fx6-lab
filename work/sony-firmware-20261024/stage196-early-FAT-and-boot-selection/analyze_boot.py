"""Original NOR host-only static slices. Linear matches are candidates only."""
from pathlib import Path
from hashlib import sha256
import json,struct,plistlib,subprocess
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from capstone.arm64 import ARM64_OP_IMM,ARM64_OP_REG,ARM64_OP_MEM
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
SOURCE=BASE/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin'
EXPECTED='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
VA=0xfe049000
v=plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))
assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
data=SOURCE.read_bytes();assert sha256(data).hexdigest()==EXPECTED
cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);cs.detail=True
instructions=[];byaddr={}
for off in range(0,len(data)-3,4):
    decoded=list(cs.disasm(data[off:off+4],VA+off,count=1))
    if decoded:instructions.append(decoded[0]);byaddr[VA+off]=decoded[0]
def canonical(reg):
    name=cs.reg_name(reg)
    return 'x'+name[1:] if name.startswith('w') else name
targets={'FAT_ready':0xfe06216a,'FAT_current_partition':0xfe0620f8,'update_memory_word':0xfe170028}
known={};references=[];calls=[]
for ins in instructions:
    ops=ins.operands;old=known.copy();result={}
    if ins.mnemonic in ('bl','b') and ops and ops[0].type==ARM64_OP_IMM:
        calls.append({'site':hex(ins.address),'kind':ins.mnemonic,'target':hex(ops[0].imm)})
    for op in ops:
        if op.type==ARM64_OP_MEM and canonical(op.mem.base) in old and not op.mem.index:
            address=old[canonical(op.mem.base)]+op.mem.disp
            for name,target in targets.items():
                if target-8<=address<=target+8:
                    references.append({'site':hex(ins.address),'target_name':name,'effective_address':hex(address),
                        'instruction':ins.mnemonic+' '+ins.op_str,'source_register_value':hex(old[canonical(ops[0].reg)]) if ops and ops[0].type==ARM64_OP_REG and canonical(ops[0].reg) in old else None,
                        'candidate_only':True})
    if ins.mnemonic in ('adr','adrp') and len(ops)==2 and ops[1].type==ARM64_OP_IMM:result[canonical(ops[0].reg)]=ops[1].imm
    elif ins.mnemonic in ('add','sub') and len(ops)>=3 and ops[1].type==ARM64_OP_REG and ops[2].type==ARM64_OP_IMM and canonical(ops[1].reg) in old:
        n=ops[2].imm<<ops[2].shift.value
        result[canonical(ops[0].reg)]=old[canonical(ops[1].reg)]+(n if ins.mnemonic=='add' else -n)
    elif ins.mnemonic=='mov' and len(ops)==2 and ops[0].type==ARM64_OP_REG:
        if ops[1].type==ARM64_OP_IMM:result[canonical(ops[0].reg)]=ops[1].imm
        elif ops[1].type==ARM64_OP_REG and canonical(ops[1].reg) in old:result[canonical(ops[0].reg)]=old[canonical(ops[1].reg)]
    elif ins.mnemonic=='ldr' and len(ops)==2 and ops[1].type==ARM64_OP_IMM:
        offset=ops[1].imm-VA;size=4 if cs.reg_name(ops[0].reg).startswith('w') else 8
        if 0<=offset<=len(data)-size:result[canonical(ops[0].reg)]=int.from_bytes(data[offset:offset+size],'little')
    for register in ins.regs_access()[1]:known.pop(canonical(register),None)
    known.update(result)
    if ins.mnemonic=='bl':
        for i in range(19):known.pop('x'+str(i),None)
    elif ins.mnemonic in ('ret','br','b'):known.clear()
out={'source':str(SOURCE),'sha256':EXPECTED,'configured_base':hex(VA),'targets':{k:hex(v) for k,v in targets.items()},
     'scope':'static local register candidates; all4B offsets include data; no reachability/physical/guest execution claim','references':references,'calls':calls}
with (HERE/'reference-candidates.json').open('x') as f:json.dump(out,f,indent=2);f.write('\n')
with (HERE/'candidate-windows.txt').open('x') as f:
 for ref in references:
    address=int(ref['site'],16);f.write('\n'+json.dumps(ref)+'\n')
    for at in range(address-24,address+28,4):
        ins=byaddr.get(at)
        if ins:f.write(f'{at:#x} [file+{at-VA:#x}] {ins.bytes.hex()} {ins.mnemonic:8} {ins.op_str}\n')
def section(label,a,z):
 raw=data[a-VA:z-VA];assert len(raw)==z-a
 with (HERE/(label+'.txt')).open('x') as f:
    for ins in cs.disasm(raw,a):f.write(f'{ins.address:#x} [file+{ins.address-VA:#x}] {ins.bytes.hex()} {ins.mnemonic:8} {ins.op_str}\n')
 return {'label':label,'start':hex(a),'end':hex(z),'file_offset':hex(a-VA),'bytes':len(raw),'sha256':sha256(raw).hexdigest()}
selected=[section('init-information-sectors',0xfe052970,0xfe0529a8),section('presequence-storage-init',0xfe058adc,0xfe058b7c)]
with (HERE/'initial-slices.json').open('x') as f:json.dump(selected,f,indent=2);f.write('\n')
assert sha256(SOURCE.read_bytes()).hexdigest()==EXPECTED
print(json.dumps({'candidate_references':len(references),'references':references,'source_unchanged':True}))
