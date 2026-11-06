#!/usr/bin/env python3
"""Pinned, read-only FX6 dirty-bit data-edge receipt with FX3 identity gate."""
import hashlib
import json
import struct
from pathlib import Path

WORK=Path(__file__).resolve().parents[7]
FX6=WORK/'fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so'
FX3=WORK/'fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so'
EXPECTED={FX6:'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067',
          FX3:'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'}

def elf(path):
 b=path.read_bytes();digest=hashlib.sha256(b).hexdigest()
 if digest!=EXPECTED[path]:raise ValueError(f'original digest mismatch: {path}: {digest}')
 if b[:6]!=b'\x7fELF\x02\x01' or struct.unpack_from('<H',b,18)[0]!=183:raise ValueError('ELF64 AArch64 required')
 po=struct.unpack_from('<Q',b,32)[0]; es,n=struct.unpack_from('<HH',b,54);loads=[]
 for i in range(n):
  typ,_,fo,va,_,fs,_,_=struct.unpack_from('<IIQQQQQQ',b,po+i*es)
  if typ==1:loads.append({'va':va,'file_offset':fo,'filesz':fs})
 def raw(va,n):
  for m in loads:
   if m['va']<=va and va+n<=m['va']+m['filesz']:
    fo=m['file_offset']+va-m['va'];return fo,b[fo:fo+n]
  raise ValueError(f'not file backed: {va:#x}')
 return b,digest,loads,raw

b6,h6,m6,r6=elf(FX6);b3,h3,m3,r3=elf(FX3)
words={
 0x1134728:0xb9403fa0,0x113472c:0x52800021,0x1134730:0x97ff04d6,
 0x10f5a98:0x2a0003f3,0x10f5a9c:0x52800800,0x10f5aac:0x1ac00e60,
 0x10f5ab4:0x4b001a61,0x10f5ab8:0x9ac12042,
 0x10f5ac0:0x912c2021,0x10f5ac4:0xf8607823,0x10f5ac8:0xaa020063,0x10f5acc:0xf8207823,
 0x10f5ad4:0x91042021,0x10f5ad8:0xf8607823,0x10f5adc:0xaa020062,0x10f5ae0:0xf8207822,
 0x10f58e0:0xb949c841,0x10f58ec:0xf8617805,0x10f58f0:0xf8617861,0x10f58f4:0xea0100bf,
 0x10f5918:0x912c2042,0x10f5928:0xb949c823,0x10f5930:0xf8637804,0x10f5934:0xf8637846,
 0x10f5938:0x8a2400c4,0x10f593c:0xf8237844,
 0xde360c:0xf9400001,0xde3610:0xf9401021,0xde3614:0xd63f0020,
 0xde3618:0x940c48ab,0xdfa618:0xb9400280,0xdfa61c:0x7100081f,
 0xdfa628:0x97ffa3e7,0xdfa63c:0x940bec9d,
 0x10f5838:0x52800801,0x10f584c:0xf8615841,0x10f5850:0x9ac02420,
 0x102ea2c:0x94031b8c,0x102ea60:0x710e42bf,
}
checks=[]
for va,want in words.items():
 fo,data=r6(va,4);w=struct.unpack('<I',data)[0]
 if w!=want:raise ValueError(f'word mismatch {va:#x}: {w:#x}')
 checks.append({'va':hex(va),'file_offset':hex(fo),'raw_le':data.hex(),'word':hex(w)})

def bl_target(va):
 fo,data=r6(va,4);w=struct.unpack('<I',data)[0]
 if w>>26!=0b100101:raise ValueError(f'not BL {va:#x}')
 imm=w&0x3ffffff
 if imm&0x2000000:imm-=0x4000000
 return {'va':hex(va),'file_offset':hex(fo),'raw_le':data.hex(),'target':hex(va+imm*4)}
calls=[bl_target(v) for v in (0x1134730,0xde3618,0xdfa628,0xdfa63c,0x102ea2c)]
if [x['target'] for x in calls]!=['0x10f5a88','0x10f58c4','0xde35c4','0x10f58b0','0x10f585c']:
 raise ValueError('call chain changed')
model_id=0x3662;q,r=divmod(model_id,64);mask=1<<r
if (q,r,mask)!=(217,34,0x400000000):raise ValueError('bit math changed')
receipt={'level':'file-static; no firmware execution or device inference',
 'sources':{'fx6':{'path':str(FX6),'sha256':h6},'fx3':{'path':str(FX3),'sha256':h3}},
 'fx6_load_segments':[{'va':hex(x['va']),'file_offset':hex(x['file_offset']),'filesz':hex(x['filesz'])} for x in m6],
 'fx3_load_segments':[{'va':hex(x['va']),'file_offset':hex(x['file_offset']),'filesz':hex(x['filesz'])} for x in m3],
 'id':hex(model_id),'word_index':q,'bit_index':r,'mask':hex(mask),
 'bitmap_a_base_va':'0x4da5b08','bitmap_a_word_va':hex(0x4da5b08+q*8),
 'bitmap_b_base_va':'0x4da5108','bitmap_b_word_va':hex(0x4da5108+q*8),
 'consumer_list':'runtime object: [x0+0xeac] count, [x0+0x9c8+4*i] word index',
 'id_0x3662_in_consumer_list':'unknown','ipc_field_length_consumer':'unknown',
 'checks':checks,'calls':calls}
print(json.dumps(receipt,indent=2))
