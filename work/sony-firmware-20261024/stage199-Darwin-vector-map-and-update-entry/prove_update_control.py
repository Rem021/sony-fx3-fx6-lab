"""Check a conditional MCU update path from original bytes, never execute it."""
from pathlib import Path
from hashlib import sha256
import json, struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB, CS_MODE_MCLASS
H=Path(__file__).resolve().parent;B=H.parent
SRC=B/'stage198-AP-CP-loaders-and-partition-selection/originals/darwin_core.bin'
SHA='ac3fe4cb9d7122b196d33ca3514d0eb4e2d3abbed882926d4e08d5b26b76afe0'
d=SRC.read_bytes();assert sha256(d).hexdigest()==SHA
BASE=0x4200
def u16(a):return struct.unpack_from('<H',d,a-BASE)[0]
def u32(a):return struct.unpack_from('<I',d,a-BASE)[0]
def signed(v,b):return v-(1<<b) if v&(1<<(b-1)) else v
def bl(a):
    x,y=u16(a),u16(a+2);assert x&0xf800==0xf000 and y&0xd000==0xd000
    s=(x>>10)&1;i1=1^(((y>>13)&1)^s);i2=1^(((y>>11)&1)^s)
    disp=(s<<24)|(i1<<23)|(i2<<22)|((x&1023)<<12)|((y&2047)<<1)
    return a+4+signed(disp,25)
def ldr16(a):
    w=u16(a);assert w&0xf800==0x4800
    pool=((a+4)&~3)+(w&255)*4
    return {'site':hex(a),'pool':hex(pool),'register':(w>>8)&7,'value':hex(u32(pool))}
def put(n,v):
    p=H/n
    if p.exists():assert json.loads(p.read_text())==v
    else:
        with p.open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
c=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);c.detail=True
selected=[]
ranges=[('state-dispatch-loop',0x4b06,0x4b32),('Init-main',0x84ae,0x8572),
        ('Init-next',0x8572,0x858c),('Seton-main',0x86c8,0x883e),('Seton-next',0x883e,0x8858),
        ('Seton-exit',0x8858,0x88dc),('Upd-main',0x99d0,0x9a26),('vector-transfer-leaf',0x45dc,0x45f6)]
byname={}
for name,a,z in ranges:
    raw=d[a-BASE:z-BASE];ins=list(c.disasm(raw,a));assert sum(i.size for i in ins)==len(raw),name
    byname[name]=ins
    text='# Original FX3 core bytes under source map0x4200. No execution.\n'+''.join(
        f'{i.address:#x} [file+{i.address-BASE:#x}] {i.bytes.hex()} {i.mnemonic:9} {i.op_str}\n' for i in ins)
    p=H/(name+'.txt')
    if p.exists():assert p.read_text()==text
    else:
        with p.open('x') as f:f.write(text)
    selected.append({'name':name,'start':hex(a),'end_exclusive':hex(z),'bytes':len(raw),'sha256':sha256(raw).hexdigest(),'instruction_count':len(ins)})

# Fixed state descriptor and dispatcher source evidence, not all-state reachability.
state_pool=ldr16(0x4b06);table_pool=ldr16(0x4b08)
assert state_pool['value']=='0x200026d4' and table_pool['value']=='0x38b60'
table=0x38b60
rows=[]
names=['Init','Seton','On','Exiton','Off','Upd']
for state in range(6):
    values=struct.unpack_from('<4I',d,table+state*16-BASE)
    rows.append({'state':state,'analyst_label_from_source_logs':names[state],
                 'record':hex(table+state*16),'functions_Thumb':[hex(x) for x in values]})
assert rows[1]['functions_Thumb']==['0x8619','0x86c9','0x883f','0x8859']
assert rows[5]['functions_Thumb']==['0x99cd','0x99d1','0x0','0x0']
assert d[0x4b18-BASE:0x4b30-BASE].hex()=='286807eb00142068804760688047a16888472860e0688047'

# Narrow, explicit predicate: if the receive returns with these two halfwords,
# the selected local branches assign saved r4=2. No claim of external reachability.
fixed16={0x8790:0x8820,0x8792:0xb118,0x879c:0x8860,0x879e:0x2804,
         0x87a0:0xd101,0x87a2:0x2402,0x87a4:0xe00a,0x8816:0x4620,0x8818:0xbdf8}
for a,w in fixed16.items():assert u16(a)==w,(hex(a),hex(u16(a)))
assert 0x8792+4+(((u16(0x8792)>>9)&1)<<6)+(((u16(0x8792)>>3)&31)<<1)==0x879c
assert 0x87a4+4+signed(u16(0x87a4)&2047,11)*2==0x87bc
# ARM ABI r4 is preserved by ordinary callees. Observe all explicit register writes.
setters=[]
for i in byname['Seton-main']:
    if 'r4' in [i.reg_name(r) for r in i.regs_access()[1]]:
        setters.append({'site':hex(i.address),'instruction':i.mnemonic+' '+i.op_str})
assert {x['site'] for x in setters}=={'0x86d0','0x8798','0x87a2','0x87b2','0x8818'}
assert all(i.mnemonic!='svc' for i in byname['Seton-main'])
nextpool=ldr16(0x8850);assert nextpool['value']=='0x3a5a4'
seton_next_words=[u32(0x3a5a4+i*4) for i in range(3)]
assert seton_next_words==[2,3,5]
assert d[0x8852-BASE:0x8858-BASE].hex()=='50f8240010bd'

# Init normally returns0; do not promote nearby shared table word5 to an Init route.
assert d[0x856e-BASE:0x8572-BASE].hex()=='002010bd'
assert len([i for i in byname['Init-main'] if i.mnemonic=='pop' and 'pc' in i.op_str])==1
assert not any(i.mnemonic in ('bx','blx','tbb','tbh') for i in byname['Init-main'])
for i in byname['Init-main']:
    if i.mnemonic.startswith('b') and i.mnemonic!='bl':
        assert 0x84ae<=i.operands[-1].imm<0x8572
    if i.mnemonic in ('cbz','cbnz'):
        assert 0x84ae<=i.operands[-1].imm<0x8572
initpool=ldr16(0x8584);assert initpool['value']=='0x3a5a0' and u32(0x3a5a0)==1

# Upd-main writes request4/zero in its own retained MCU state, then enters
# the vector table at address0. These addresses are not an AP partition selector.
request_pool=ldr16(0x99d4);assert request_pool['value']=='0x20000700'
for a,w in {0x9a16:0x2004,0x9a18:0x71a8,0x9a1a:0x2000,0x9a1c:0x71e8,0x45dc:0x6801}.items():
    assert u16(a)==w,(hex(a),hex(u16(a)))
assert bl(0x9a1e)==0x45dc
assert d[0x45de-BASE:0x45e6-BASE].hex()=='81f3088881f30988'
assert d[0x45f2-BASE:0x45f6-BASE].hex()=='d0f804f0'
assert all(i.mnemonic not in ('bl','blx') for i in byname['vector-transfer-leaf'])
adr=u16(0x99dc);assert adr&0xf800==0xa000
label=((0x99dc+4)&~3)+(adr&255)*4
assert label==0x9a30 and d[label-BASE:label-BASE+10]==b'Upd main\n\0'

# Aligned Thumb BL locators for the transfer leaf; data/second halves still possible.
calls=[]
for off in range(0,len(d)-3,2):
    a=BASE+off;x,y=u16(a),u16(a+2)
    if x&0xf800==0xf000 and y&0xd000==0xd000 and bl(a)==0x45dc:calls.append(hex(a))
assert calls==['0x9a1e']
put('update-control-proof.json',{
 'source_sha256':SHA,'source_layout_base':hex(BASE),'selected_ranges':selected,
 'state_pointer_pool':state_pool,'descriptor_pointer_pool':table_pool,'state_descriptors':rows,
 'Seton_conditional_route':{'input':'after ordinary receive return, halfword0=0 and halfword1=4',
    'local_saved_result':2,'next_function':'0x883e','next_table_pool':nextpool,
    'reachable_return_values_under_local_ABI_model':[0,1,2],'next_table_for_these_values':seton_next_words,
    'selected_next_state':5,'explicit_r4_writers':setters,
    'assumptions':['subcalls return normally and preserve r4 under ARM ABI','dispatcher/exit callbacks do not asynchronously overwrite selected state before next iteration'],
    'producer_not_traced_by_this_consumer_slice':True,'producer_trace_extension':'InitCom-link-proof.json',
    'externally_triggerable':False},
 'Init_normal_route':{'return_value':0,'next_table_pool':initpool,'selected_next_state':1,
    'ordinary_call_return_model_only':True},
 'Upd_transfer':{'function':'0x99d0','label_source':'0x9a30','request_pool':request_pool,
    'writes':[{'address':'0x20000706','width_bits':8,'value':4},{'address':'0x20000707','width_bits':8,'value':0}],
    'raw_BL_target':'0x45dc','vector_argument':0,'MSP_PSP_from_address':'0x0','PC_from_address':'0x4',
    'outside_current_core_source_mapping':True,'bootloader_original_bytes_obtained':False,
    'AP_p1_p3_or_USB_fastboot_mapping_proven':False,'independent_corrupt_core_restore_proven':False},
 'transfer_BL_locator_candidates':calls,'locator_scope':'all2B aligned data may include non-code; not exhaustive indirect-call proof',
 'original_or_guest_execution':False,'root_or_device_operations':0,'source_unchanged':sha256(SRC.read_bytes()).hexdigest()==SHA})
print(json.dumps({'conditional_Seton_next_state':5,'Upd_vector_argument':0,'request_byte_address':'0x20000706',
    'request_byte_value':4,'selected_original_ranges':len(selected),'no_device_or_guest_execution':True}))
