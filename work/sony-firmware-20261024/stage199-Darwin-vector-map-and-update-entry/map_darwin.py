"""FX3 saved MCU image: source-bound vector map and ADR locators, no execution."""
from pathlib import Path
from hashlib import sha256
import json, struct, re
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
from capstone.arm import ARM_OP_IMM, ARM_OP_REG, ARM_REG_PC
H=Path(__file__).resolve().parent;B=H.parent
SRC=B/'stage198-AP-CP-loaders-and-partition-selection/originals/darwin_core.bin'
SHA='ac3fe4cb9d7122b196d33ca3514d0eb4e2d3abbed882926d4e08d5b26b76afe0'
d=SRC.read_bytes();assert sha256(d).hexdigest()==SHA
BASE=0x4200
c=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);c.detail=True
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
def u16(a):return struct.unpack_from('<H',d,a-BASE)[0]
def u32(a):return struct.unpack_from('<I',d,a-BASE)[0]
def signed(v,b):return v-(1<<b) if v&(1<<(b-1)) else v
def thumb_bl(a):
    h1,h2=u16(a),u16(a+2)
    assert h1&0xf800==0xf000 and h2&0xd000==0xd000
    s=(h1>>10)&1;j1=(h2>>13)&1;j2=(h2>>11)&1
    disp=(s<<24)|((1^(j1^s))<<23)|((1^(j2^s))<<22)|((h1&0x3ff)<<12)|((h2&0x7ff)<<1)
    return a+4+signed(disp,25)
vectors=list(struct.unpack_from('<16I',d))
assert vectors[0]==0x200026d0 and vectors[1]==0x45f9 and vectors[2]==0x4601
assert thumb_bl(0x45f8)==0x4674
assert u16(0x45fc)==0x481c and u16(0x45fe)==0x4700
pool=((0x45fc+4)&~3)+((u16(0x45fc)&255)*4)
assert pool==0x4670 and u32(pool)==0x43fd
# Source evidence for exception-vector entries under the new map.
assert d[0x4600-BASE:0x4614-BASE].hex()=='1ef0040f0cbfeff30880eff3098002f014fffee7'
assert vectors[3]==0x4615 and u16(0x461c)==0xe7fe

selected=[]
for name,a,z in [('reset-and-fault-entries',0x45f8,0x463c),('reset-runtime-target',0x43fc,0x4430),
                 ('early-init-prefix',0x4674,0x46cc),('common-IRQ-entry-prefix',0x6eaa,0x6ee0)]:
    raw=d[a-BASE:z-BASE];ins=list(c.disasm(raw,a));assert sum(i.size for i in ins)==len(raw)
    text='# Source-layout map0x4200; no runtime PC, physical trace or execution claim.\n'+''.join(
        f'{i.address:#x} [file+{i.address-BASE:#x}] {i.bytes.hex()} {i.mnemonic:9} {i.op_str}\n' for i in ins)
    p=H/(name+'.txt')
    if p.exists():assert p.read_text()==text
    else:
        with p.open('x') as f:f.write(text)
    selected.append({'name':name,'start':hex(a),'end_exclusive':hex(z),'bytes':len(raw),'sha256':sha256(raw).hexdigest()})

# Every 2-byte alignment, including possible data and second halves. These
# are locators only; a selected source slice is required before use as code.
refs=[]
for off in range(0,len(d)-3,2):
    q=list(c.disasm(d[off:off+4],BASE+off,count=1))
    if not q:continue
    i=q[0]
    if i.mnemonic.startswith('adr') and len(i.operands)==2 and i.operands[1].type==ARM_OP_IMM:
        target=((i.address+4)&~3)+i.operands[1].imm
        t=target-BASE
        if not 0<=t<len(d):continue
        raw=d[t:t+180].split(b'\0')[0]
        if len(raw)>=3 and all(v in (9,10,13) or 32<=v<127 for v in raw):
            refs.append({'site':hex(i.address),'file_offset':hex(off),'bytes':i.bytes.hex(),
                'instruction':i.mnemonic+' '+i.op_str,'target':hex(target),'target_file_offset':hex(t),
                'value':raw.decode('ascii'),'candidate_only':True})
put('ADR-reference-candidates.json',{'source_sha256':SHA,'base':hex(BASE),'scope':'all2B alignments, may include data or second halves; not reachability or exhaustive alias proof','candidates':refs})
put('vector-source-proof.json',{'source_path':str(SRC),'source_sha256':SHA,'source_bytes':len(d),
    'source_layout_base':hex(BASE),'base_source':'A6000 public finding used as hypothesis; verified here against distinct FX3 bytes and raw Thumb branch/pool fields',
    'first16_vector_words':[hex(v) for v in vectors],'reset_entry':'0x45f9','reset_file_offset':'0x3f8',
    'raw_BL_target':'0x4674','reset_LDR_pool':'0x4670','runtime_branch_pointer':'0x43fd',
    'fault_vector_source_matches':True,'selected_ranges':selected,
    'scope':'self-consistent source-layout mapping; not physical MCU identity, verified boot trace, independent bootloader or recovery reachability',
    'original_or_guest_execution':False,'root_or_device_operations':0,
    'source_unchanged':sha256(SRC.read_bytes()).hexdigest()==SHA})
print(json.dumps({'source_map':'0x4200','reset_BL_raw':'0x4674','runtime_target':'0x43fd','ADR_candidates':len(refs),
    'selected_update_refs':[{k:r[k] for k in ('site','target','value')} for r in refs if re.search(r'BOOT:|update|reset req',r['value'],re.I)]}))
