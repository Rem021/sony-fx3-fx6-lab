"""Verify fixed handoff from saved loader_spi, with raw instruction fields."""
from pathlib import Path
from hashlib import sha256
import json, re, struct
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
H = Path(__file__).resolve().parent
BASE = H.parent
SRC = H/'originals/loader_spi.bin'
EXPECTED = '314d372d0d2b9883c3b9dc04b40389edb3100e6d5ef529633cc427c3d0cab72e'
d = SRC.read_bytes(); assert sha256(d).hexdigest() == EXPECTED
VA = 0xfe049000  # tentative source-layout base, not a measured runtime PC

def word(a):return struct.unpack_from('<I',d,a)[0]
def signed(v,b):return v-(1<<b) if v&(1<<(b-1)) else v
def target(a, opcode):
    w=word(a); assert w&0xfc000000==opcode
    return a+signed(w&0x3ffffff,26)*4
assert target(0x5abc,0x94000000)==0x41bc
assert target(0x41bc,0x14000000)==0x3ca8

def mov_imm(a, rd, is64, keep=False):
    w=word(a)
    expected=(0xf2800000 if keep else 0xd2800000) if is64 else (0x72800000 if keep else 0x52800000)
    assert w&0xff80001f==expected|rd, (hex(a),hex(w))
    return ((w>>5)&65535)<<(16*((w>>21)&3))
entry=mov_imm(0x5aac,0,False)|mov_imm(0x5ab0,0,False,True)
assert entry==0x00108000
scr=mov_imm(0x3cb8,5,True);spsr=mov_imm(0x3ccc,5,True)
assert scr==0x30 and spsr==0x13
fixed={0x3cbc:0xd51e1105,0x3cd0:0xd51e4005,0x3cd4:0xd51e4020,0x3cd8:0xd69f03e0,
       0x5ab4:0xaa1403e1,0x5ab8:0xd503209f}
for a,v in fixed.items():assert word(a)==v,(hex(a),hex(word(a)))

# No intervening path writes x0 between fixed assignment and ELR_EL3.
# Decode the complete target leaf, including both CBZ successors.
c=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);c.detail=True
leaf=list(c.disasm(d[0x3ca8:0x3cdc], VA+0x3ca8))
assert len(leaf)==13 and leaf[-1].mnemonic=='eret'
assert all('x0' not in [i.reg_name(r) for r in i.regs_access()[1]] for i in leaf)
assert all(i.mnemonic not in ('bl','blr','br','ret') for i in leaf)
assert leaf[0].mnemonic=='cbz' and leaf[0].operands[-1].imm==VA+0x3cb8

config=BASE/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/pformat_config.txt'
assert sha256(config.read_bytes()).hexdigest()=='21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece'
rows=re.findall(r'file_param\s*\{([^}]+)\}',config.read_text())
cp=[r for r in rows if '"cpapp-b.bin"' in r]; assert len(cp)==1
cp_load=int(re.search(r'load\s*=\s*(0x[0-9a-fA-F]+)',cp[0]).group(1),16)
assert cp_load==entry
hist=(H/'originals/historical2.05-loadaddr.txt').read_text().strip()
hist_addrs=[int(v,16) for v in hist.split(',')]
assert hist_addrs[0]==0x400080000 and hist_addrs[0]!=entry

ranges=[('spi-handoff-caller',0x5a28,0x5ac8),('spi-handoff-tail-stub',0x41bc,0x41c0),
        ('spi-handoff-eret-leaf',0x3ca8,0x3cdc),('spi-startup-base-clues',0x0,0x100)]
selected=[]
for label,a,z in ranges:
    raw=d[a:z];ins=list(c.disasm(raw,VA+a));assert len(ins)*4==len(raw)
    with (H/(label+'.txt')).open('x') as f:
        f.write('# File offsets authoritative; display VA tentative, no firmware execution.\n')
        for i in ins:f.write(f'{i.address:#x} [file+{i.address-VA:#x}] {i.bytes.hex()} {i.mnemonic:8} {i.op_str}\n')
    selected.append({'label':label,'start_offset':hex(a),'end_offset_exclusive':hex(z),
        'bytes':len(raw),'sha256':sha256(raw).hexdigest(),'instructions':len(ins)})

# Sequence rows are source data: absolute pointers internally agree with the
# tentative base. They are not evidence that every step runs on the body.
table=[]
for off in range(0x9748,0x98e8,32):
    addr,flags=struct.unpack_from('<QQ',d,off)
    name=d[off+16:off+32].split(b'\0')[0].decode('ascii').strip()
    table.append({'file_offset':hex(off),'absolute_target':hex(addr),'flags':hex(flags),'name':name,
                  'target_offset_if_base_correct':hex(addr-VA)})
assert table[0]['name']=='CM:ldr_common_' and table[-1]['absolute_target']=='0x0'
result={
 'source_sha256':EXPECTED,'source_bytes':len(d),'tentative_base':hex(VA),
 'base_not_runtime_verified':True,'offset_bound_proof_does_not_require_measured_base':True,
 'raw_BL_target_offset':'0x41bc','raw_tail_B_target_offset':'0x3ca8',
 'fixed_handoff_target':hex(entry),'ELR_EL3_source_register':'x0',
 'x0_no_write_in_target_leaf':True,'SCR_EL3':hex(scr),'SCR_EL3_RW_bit':(scr>>10)&1,
 'SPSR_EL3':hex(spsr),'SPSR_mode_bits':bin(spsr&31),
 'interpretation':'AArch32 Supervisor-mode handoff candidate; matches current cpapp-b config, not a proven AP p1/p3 selector',
 'cpapp_b_config_path':str(config),'cpapp_b_config_load':hex(cp_load),
 'historical2_05_AP_kernel_address':hex(hist_addrs[0]),'historical_not_current_body':True,
 'selected_original_ranges':selected,'on_sequence_table':table,
 'callee_normal_return_assumptions':['preceding log/sequence/cache subcalls return normally to observed fixed handoff prefix'],
 'device_boot_trace_or_controller_identity_verified':False,'p1_p3_selection_proven':False,
 'original_or_guest_execution':False,'device_or_administrator_operations':0,
 'source_unchanged':sha256(SRC.read_bytes()).hexdigest()==EXPECTED}
with (H/'fixed-handoff-proof.json').open('x') as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'fixed_target':hex(entry),'matches_cpapp_b_config':True,'selected_ranges':len(selected),
 'SPSR':hex(spsr),'no_device_or_guest_execution':True}))
