#!/usr/bin/env python3
"""Read-only pinned FX6 registry / FX3 Base ISO contrast."""
import hashlib
import json
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parents[7]
FX6 = ROOT/'fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so'
FX3 = ROOT/'fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so'
SHA = {FX6:'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
       FX3:'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'}

def read_elf(path):
    b=path.read_bytes(); h=hashlib.sha256(b).hexdigest()
    if h!=SHA[path]: raise ValueError(f'SHA mismatch: {path}: {h}')
    if b[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',b,18)[0]!=183:
        raise ValueError('not ELF64 little-endian AArch64')
    phoff=struct.unpack_from('<Q',b,32)[0]; ents,n=struct.unpack_from('<HH',b,54)
    loads=[]
    for i in range(n):
        typ,_,off,va,_,filesz,_,_=struct.unpack_from('<IIQQQQQQ',b,phoff+i*ents)
        if typ==1: loads.append((va,off,filesz))
    def raw(va,size):
        for start,off,length in loads:
            if start<=va and va+size<=start+length:
                fileoff=off+va-start
                return fileoff,b[fileoff:fileoff+size]
        raise ValueError(f'not file backed: {va:#x}')
    return b,h,raw

def word(raw,va,expected):
    off,data=raw(va,4); actual=struct.unpack('<I',data)[0]
    if actual!=expected: raise ValueError(f'{va:#x}: {actual:#x} != {expected:#x}')
    return {'va':hex(va),'file_offset':hex(off),'raw_le':data.hex(),'word':hex(actual)}

def bl(raw,va,target):
    off,data=raw(va,4); w=struct.unpack('<I',data)[0]
    if w>>26!=0b100101: raise ValueError(f'not BL: {va:#x}')
    imm=w&0x3ffffff
    if imm&0x2000000: imm-=0x4000000
    actual=va+imm*4
    if actual!=target: raise ValueError(f'BL mismatch: {va:#x} -> {actual:#x}')
    return {'va':hex(va),'file_offset':hex(off),'raw_le':data.hex(),'target':hex(actual)}

b6,h6,r6=read_elf(FX6); b3,h3,r3=read_elf(FX3)
init_off,init_raw=r6(0x29113a8,8)
if int.from_bytes(init_raw,'little')!=0xb74ffc: raise ValueError('init_array constructor pointer changed')
checks=[word(r6,0xb75000,0xb000ce41),word(r6,0xb75010,0xa9017bfd),
        word(r6,0xb75030,0xf942975a),word(r6,0xb750a0,0x9105c022),
        word(r6,0x1ad2664,0xb94002a4),word(r6,0x1ad2768,0x910062b5),
        word(r6,0x1134690,0xf000eda0),word(r6,0x1134698,0xf9429400),
        word(r6,0x11346a0,0xb40002c0),word(r6,0x11346cc,0xb9400660),
        word(r6,0x15370dc,0xf9400802),word(r6,0x15370e4,0xd61f0040),
        word(r3,0x1824124,0x5286cc40),word(r3,0x19f8728,0x5286cc40),
        word(r3,0x19f8730,0x72a00020)]
calls=[bl(r6,0xb75068,0x1ad25bc),bl(r6,0x113469c,0x10f67c0),
       bl(r6,0x11346ac,0x1537090),bl(r6,0x11346d4,0x15370c8),
       bl(r6,0x11346fc,0x1537058),bl(r6,0x1134730,0x10f5a88)]
start,end=0x253e9c0,0x253ebe8
off,table=r6(start,end-start)
if len(table)%24: raise ValueError('map table not 24-byte entries')
records=[]
for i in range(len(table)//24):
    fields=struct.unpack_from('<6I',table,i*24)
    records.append({'va':hex(start+i*24),'file_offset':hex(off+i*24),'u32':[hex(v) for v in fields]})
keys=[int(x['u32'][0],16) for x in records]
if 0x3662 in keys: raise ValueError('0x3662 found in initial registry')
assert len(records)==23 and len(set(keys))==23

# Exact VA xrefs to this registry pointer via ADRP page + LDR +0x528, within eight instructions.
xrefs=[]
for va in range(0xb1a1f0,0x2900000,4):
    w=struct.unpack_from('<I',b6,va)[0]
    if w&0x9f000000!=0x90000000: continue
    imm=((w>>29)&3)|(((w>>5)&0x7ffff)<<2)
    if imm&(1<<20): imm-=1<<21
    if (va&~0xfff)+(imm<<12)!=0x2eeb000: continue
    reg=w&31
    for step in range(4,33,4):
        q=struct.unpack_from('<I',b6,va+step)[0]
        if q&0xffc00000==0xf9400000 and (q>>5)&31==reg and ((q>>10)&0xfff)*8==0x528:
            xrefs.append({'adrp_va':hex(va),'adrp_file_offset':hex(r6(va,4)[0]),
                          'load_va':hex(va+step),'load_file_offset':hex(r6(va+step,4)[0])})
            break

labels=[b'BASE_ISO_LOW_800\0',b'BASE_ISO_HIGH_2500\0',b'BASE_ISO_HIGH_12800\0']
fx3_labels={s[:-1].decode():hex(b3.find(s)) if b3.find(s)>=0 else None for s in labels}
if any(v is None for v in fx3_labels.values()): raise ValueError('FX3 Base ISO labels absent')
fx3_extern_count=b3.count(b'extern_BKID_APP_EXTERN_BASE_ISO')
receipt={'level':'original FX6 and FX3 file static only','sources':{'fx6':{'path':str(FX6),'sha256':h6},'fx3':{'path':str(FX3),'sha256':h3}},
 'fx6_initial_registry':{'init_array_slot_va':'0x29113a8','init_array_slot_file_offset':hex(init_off),'init_array_raw_le':init_raw.hex(),'constructor_va':'0xb74ffc','hash_constructor_va':'0x1ad25bc','table_va':hex(start),'table_end_va':hex(end),'table_file_offset':hex(off),'stride':24,'records':records,'key_0x3662_present':False},
 'registry_pointer_xrefs':xrefs,'fx3':{'labels_file_offsets':fx3_labels,'extern_callback_name_count':fx3_extern_count,'id_0x3662_occurrences':[{'va':'0x1824124','meaning':'plain ID registration'},{'va':'0x19f8728','meaning':'ID later extended by MOVK #1 at 0x19f8730'}]},
 'checks':checks,'calls':calls,
 'bounded_conclusion':'initial FX6 registry does not contain 0x3662; runtime insert/mutation not excluded, so conditional hit path and successor ID remain unknown',
 'ipc_length_field_consumer':'unknown'}
print(json.dumps(receipt,ensure_ascii=False,indent=2))
