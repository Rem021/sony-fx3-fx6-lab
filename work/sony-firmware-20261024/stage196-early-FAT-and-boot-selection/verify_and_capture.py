"""Independent A64 branch encoding check and source-bound selected slices.

Reads original bytes, never executes Sony or guest instructions. No device IO.
"""
from pathlib import Path
from hashlib import sha256
import json,struct
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
HERE=Path(__file__).resolve().parent;BASE=HERE.parent;VA=0xfe049000
SRC=BASE/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin'
data=SRC.read_bytes();h=sha256(data).hexdigest();assert h=='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942'
def word(address):return struct.unpack_from('<I',data,address-VA)[0]
def sign(value,bits):return value-(1<<bits) if value&(1<<(bits-1)) else value
edges={};start=0xfe057fa0;end=0xfe058178
for pc in range(start,end,4):
    w=word(pc)
    if w&0xfffffc1f==0xd65f0000:succ=[]
    elif w&0x7c000000==0x14000000:
        succ=[pc+4] if w&0x80000000 else [pc+sign(w&0x3ffffff,26)*4]
    elif w&0xff000010==0x54000000 or w&0x7e000000==0x34000000:
        succ=[pc+sign((w>>5)&0x7ffff,19)*4,pc+4]
    elif w&0x7e000000==0x36000000:succ=[pc+sign((w>>5)&0x3fff,14)*4,pc+4]
    else:succ=[pc+4]
    edges[hex(pc)]=[hex(x) for x in succ]
reference=json.loads((HERE/'fat-open-cfg.json').read_text())['edges'];assert edges==reference
movn=word(0xfe05816c)
assert movn&0xff80001f==0x12800000
signed_return=sign((~(((movn>>5)&65535)<<(16*((movn>>21)&3))))&0xffffffff,32)
assert signed_return==-408 and word(0xfe058174)==0xd65f03c0

# Decode the actual GPIO leaf's constant construction and one-bit UBFM,
# independently of the Capstone mnemonic aliases used in selected text.
a=word(0xfe0542d0);b=word(0xfe0542d4)
assert a&0xff80001f==0x52800008 and b&0xff80001f==0x72800008
mmio=((a>>5)&65535)|(((b>>5)&65535)<<(16*((b>>21)&3)))
assert mmio==0xf102e008
extract=word(0xfe0542f4)
assert extract&0xffc00000==0x53000000 and (extract&31)==19 and ((extract>>5)&31)==8
assert ((extract>>16)&63)==((extract>>10)&63)==1
caller=word(0xfe0532e8);assert 0xfe0532e8+sign(caller&0x3ffffff,26)*4==0xfe0542cc
c=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
ranges=[('gpio-update-mira',0xfe0542cc,0xfe05431c),('sample-to-shared-word',0xfe0532b4,0xfe05331c),
 ('mode-check-and-cache',0xfe053c78,0xfe053d20),('sequence-executor',0xfe05b67c,0xfe05b870),
 ('spi-choice',0xfe054ae4,0xfe054c48),('spi-choice-call-gate',0xfe05b268,0xfe05b2d0),
 ('startup-main',0xfe059f34,0xfe05a08c),('spi-init-sequence-step',0xfe0533f4,0xfe053444),
 ('first-spi-input',0xfe05c03c,0xfe05c22c),('spi-mode-predicate-prefix',0xfe054c88,0xfe054d5c)]
entries=[]
for name,a,z in ranges:
    raw=data[a-VA:z-VA];lines=list(c.disasm(raw,a));assert len(lines)*4==len(raw)
    with (HERE/(name+'.txt')).open('x') as f:
        f.write('# Analyst label; exact original configured VA, not runtime PC. No execution.\n')
        for i in lines:f.write(f'{i.address:#x} [file+{i.address-VA:#x}] {i.bytes.hex()} {i.mnemonic:8} {i.op_str}\n')
    entries.append({'label':name,'start':hex(a),'end_exclusive':hex(z),'bytes':len(raw),'sha256':sha256(raw).hexdigest(),'instruction_count':len(lines),'prefix_only':name.endswith('prefix')})
table=[]
for off in range(0x18870,0x18a50,32):
    address,flags=struct.unpack_from('<QQ',data,off);name=data[off+16:off+32].split(b'\0')[0].decode('ascii')
    table.append({'offset':hex(off),'target':hex(address),'flags':hex(flags),'name':name})
assert table[1]['target']=='0xfe0532b4' and table[1]['flags']=='0x0'
assert table[4]['target']=='0xfe05331c' and table[4]['flags']=='0x1'
strings={}
for address in (0xfe05f654,0xfe05edab):
    strings[hex(address)]=data[address-VA:].split(b'\0')[0].decode('ascii')
proof={'source':str(SRC),'sha256':h,'scope':'host static and raw-encoding verification; no original/guest/device execution',
       'independent_branch_graph_matches':True,'normal_return_signed32_from_raw_MOVN':signed_return,
       'FAT_open_proof_limit':'all ordinary returns; does not force callees to return or rule out runtime code replacement/other processors',
       'GPIO_leaf':{'configured_entry':'0xfe0542cc','MMIO_configuration_base':hex(mmio),'writes_before_sample':['0xf102e008','0xf102e024'],
           'sample_address':'0xf102e010','sample_bit':1,'normal_result':'(sample_word >> 1) & 1',
           'shared_word_store':'0xfe053308','shared_word_address':'0xfe170028','root_board_pin_or_user_button_mapping_proven':False},
       'sequence_table':table,'literal_strings':strings,'selected_original_ranges':entries,
       'whole_boot_or_recovery_entry_proven':False,'source_unchanged_after':sha256(SRC.read_bytes()).hexdigest()==h}
with (HERE/'selected-source-evidence.json').open('x') as f:json.dump(proof,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({'raw_CFG_matches':True,'normal_return':signed_return,'sample_address':'0xf102e010','sample_bit':1,'shared_word':'0xfe170028','selected_ranges':len(entries),'literal_strings':strings}))
