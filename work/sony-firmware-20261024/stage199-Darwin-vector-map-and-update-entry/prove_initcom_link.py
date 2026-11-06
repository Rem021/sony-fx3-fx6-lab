"""Conditional InitCom argument/dataflow linkage in original MCU bytes only."""
from pathlib import Path
from hashlib import sha256
import json,struct
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB,CS_MODE_MCLASS
H=Path(__file__).resolve().parent;B=H.parent;BASE=0x4200
SRC=B/'stage198-AP-CP-loaders-and-partition-selection/originals/darwin_core.bin'
SHA='ac3fe4cb9d7122b196d33ca3514d0eb4e2d3abbed882926d4e08d5b26b76afe0'
d=SRC.read_bytes();assert sha256(d).hexdigest()==SHA
def u16(a):return struct.unpack_from('<H',d,a-BASE)[0]
def sign(v,b):return v-(1<<b) if v&(1<<(b-1)) else v
def bl(a):
    x,y=u16(a),u16(a+2);assert x&0xf800==0xf000 and y&0xd000==0xd000
    s=(x>>10)&1;v=(s<<24)|((1^(((y>>13)&1)^s))<<23)|((1^(((y>>11)&1)^s))<<22)|((x&1023)<<12)|((y&2047)<<1)
    return a+4+sign(v,25)
def cond16(a,w,target):
    assert u16(a)==w and w&0xf000==0xd000
    assert a+4+sign(w&255,8)*2==target
fixed={0x4f00:0x0004,0x4fc0:0x7030,0x4fcc:0x7830,0x4fce:0x2804,
       0x51c8:0x4620,0x18006:0xac01,0x18008:0x2500,0x18012:0x8820,
       0x18014:0x280a,0x18040:0x4668,0x18046:0x2800,0x1804a:0x8025,
       0x18050:0x8060,0x18052:0x2000,0x18054:0x9901,0x454c:0xdf0b,0x4550:0xdf0c}
for a,w in fixed.items():assert u16(a)==w,(hex(a),hex(u16(a)))
cond16(0x4f76,0xd01f,0x4fb8)
cond16(0x4fd0,0xd06a,0x50a8)
cond16(0x18016,0xd013,0x18040)
assert u16(0x50a8)==0xe085 and 0x50a8+4+sign(0x85,11)*2==0x51b6
assert d[0x4fb8-BASE:0x4fbc-BASE].hex()=='9df81500'
assert d[0x1804c-BASE:0x18050-BASE].hex()=='9df80000'
calls=[(0x4efc,0x52a4),(0x4f20,0xbda4),(0x1800e,0x4550),(0x18042,0x4e5c),(0x18056,0x454c)]
for a,t in calls:assert bl(a)==t,(hex(a),hex(bl(a)))

c=Cs(CS_ARCH_ARM,CS_MODE_THUMB|CS_MODE_MCLASS);c.detail=True
ranges=[('InitCom-entry-prefix',0x4e5c,0x4e98),('InitCom-receive-and-command',0x4ef0,0x4fd8),
        ('InitCom-update-return-hop',0x50a8,0x50aa),('InitCom-return',0x51b6,0x51d0),
        ('InitCom-event-producer',0x18004,0x1805e),('SVC-event-entries',0x454c,0x4554),
        ('internal-SIO-prefix',0x52a4,0x52d8)]
selected=[]
for name,a,z in ranges:
    raw=d[a-BASE:z-BASE];ins=list(c.disasm(raw,a));assert sum(i.size for i in ins)==len(raw),name
    with (H/(name+'.txt')).open('x') as f:
        f.write('# Original FX3 bytes, source map0x4200, conditional linkage only; no execution.\n')
        for i in ins:f.write(f'{i.address:#x} [file+{i.address-BASE:#x}] {i.bytes.hex()} {i.mnemonic:9} {i.op_str}\n')
    selected.append({'name':name,'start':hex(a),'end_exclusive':hex(z),'bytes':len(raw),'sha256':sha256(raw).hexdigest(),'instruction_count':len(ins)})
    if name=='InitCom-event-producer':
        writers=[hex(i.address) for i in ins if 'r5' in [i.reg_name(r) for r in i.regs_access()[1]]]
        assert writers==['0x18008','0x1805c']

# Only the selected Cmd11 arm: preceding Rx returned0, CRC matches, callees
# preserve r4 and return. Do not include another command's status/branch.
path_ranges=[(0x4f1c,0x4f2c),(0x4f4a,0x4f78),(0x4fb8,0x4fd2),(0x51b6,0x51ca)]
for a,z in path_ranges:
    for i in c.disasm(d[a-BASE:z-BASE],a):
        assert 'r4' not in [i.reg_name(r) for r in i.regs_access()[1]],hex(i.address)

result={
 'source_sha256':SHA,'source_layout_base':hex(BASE),'selected_ranges':selected,
 'extends_local_consumer_evidence':'update-control-proof.json',
 'conditional_InitCom_arm':{'function':'0x4e5c','callee_output_pointer_register':'r6',
    'preconditions':['internal TxRx52a4 returns0','CRC comparison takes equal arm','ordinary ABI return and r4 preservation'],
    'received_frame_command_offset':'sp+0x14','command':17,'received_subvalue_offset':'sp+0x15','subvalue':4,
    'output_byte':4,'normal_return_for_selected_arm':0,
    'other_commands_or_all_error_paths_proven':False},
 'conditional_local_producer':{'function':'0x18004','input_SVC_number':12,'input_selector_argument':3,
    'input_halfword0_required':10,'InitCom_output_pointer':'sp',
    'after_return0_and_output4':{'output_halfwords':[0,4],'packed_word':'0x00040000','SVC_number':11,'selector_argument':0},
    'SVC_queue_implementation_or_delivery_verified':False},
 'local_producer_for_Seton_halfwords_identified_conditionally':True,
 'source_bound_raw_fields':{hex(a):hex(w) for a,w in fixed.items()},
 'raw_BL_targets':[{'site':hex(a),'target':hex(t)} for a,t in calls],
 'unclosed':['external/other-controller sender of internal Cmd11/sub4','transport52a4 physical controller and complete status behavior',
             'SVC delivery and whole-path runtime reachability','MCU bootloader original at0/4 and corrupt-core independent entry',
             'AP p1/p3 selector, actual USB rescue and reverse write'],
 'original_or_guest_execution':False,'root_or_device_operations':0,
 'source_unchanged':sha256(SRC.read_bytes()).hexdigest()==SHA}
with (H/'InitCom-link-proof.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'conditional_Cmd11_sub4_output':4,'conditional_event_word':'0x00040000',
    'selected_ranges':len(selected),'delivery_or_external_entry_verified':False,'no_device_or_guest_execution':True}))
