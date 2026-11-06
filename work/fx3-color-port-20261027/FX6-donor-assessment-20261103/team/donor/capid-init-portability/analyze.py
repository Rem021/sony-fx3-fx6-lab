import sys
sys.dont_write_bytecode=True
from pathlib import Path
import struct,hashlib,json,subprocess,re
HERE=Path(__file__).resolve().parent;MAC=HERE.parents[5];DONOR=HERE.parent
P={'fx6_ap':DONOR/'nflasha15-files/lib/appFw.so','fx3_ap':MAC/'work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so','helper':MAC/'work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-capid-v49-touch100.so','fx3_mpr':MAC/'work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so','fx6_mpr':DONOR/'nflasha15-files/lib/libmpr.so'}
PINS={'fx6_ap':'a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067','fx3_ap':'545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f','helper':'cd51ea7b3347ccb8bd8d0cdd72b096936f0a226c142575f41a24cc018948156e','fx3_mpr':'9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c'}
sha=lambda b:hashlib.sha256(b).hexdigest()
class ELF:
 def __init__(self,p):
  self.b=p.read_bytes();b=self.b;assert b[:6]==b'\x7fELF\x02\x01';self.loads=[]
  off=struct.unpack_from('<Q',b,32)[0];size,num=struct.unpack_from('<HH',b,54)
  for i in range(num):
   v=struct.unpack_from('<II6Q',b,off+i*size)
   if v[0]==1:self.loads.append(v)
  off=struct.unpack_from('<Q',b,40)[0];size,num,idx=struct.unpack_from('<HHH',b,58)
  self.sections=[struct.unpack_from('<II4QII2Q',b,off+i*size) for i in range(num)]
  names=self.sections[idx];ns=b[names[4]:names[4]+names[5]];self.named={ns[v[0]:].split(b'\0')[0].decode():v for v in self.sections}
 def mapping(self,va,n=4):
  for v in self.loads:
   if v[3]<=va and va+n<=v[3]+v[5]:return {'va':hex(va),'fileoff':hex(v[2]+va-v[3]),'load_va':hex(v[3]),'load_offset':hex(v[2]),'bytes_le':self.b[v[2]+va-v[3]:v[2]+va-v[3]+n].hex()}
  raise ValueError(hex(va))
 def calls(self,targets):
  out=[]
  for s in self.sections:
   if not s[2]&4:continue
   for i,(w,) in enumerate(struct.iter_unpack('<I',self.b[s[4]:s[4]+s[5]//4*4])):
    if w&0x7c000000==0x14000000:
     imm=w&0x3ffffff;imm-=1<<26 if imm&(1<<25) else 0;va=s[3]+i*4;t=va+imm*4
     if t in targets:out.append({**self.mapping(va),'target':hex(t),'kind':'BL' if w>>31 else 'B'})
  return out
 def rels(self,targets):
  out=[]
  for s in self.sections:
   if s[1]!=4:continue
   for off in range(s[4],s[4]+s[5],24):
    va,info,add=struct.unpack_from('<QQq',self.b,off)
    if add in targets:out.append({'relocation_fileoff':hex(off),'target_va':hex(va),'type':info&0xffffffff,'addend':hex(add),'raw':self.b[off:off+24].hex()})
  return out
E={k:ELF(p) for k,p in P.items()};hashes={k:sha(e.b) for k,e in E.items()}
for k,v in PINS.items():assert hashes[k]==v
ranges={
 'fx6_ap':[(0x212f470,0x212f7cc,'mpr-param-producer'),(0x20f158c,0x20f1624,'audio-leaf'),(0x20dddec,0x20dde2c,'mpr-wrapper'),(0x20d00bc,0x20d00fc,'audio-wrapper'),(0x1cd826c,0x1cd86b4,'cold-boot-run'),(0x1cd80dc,0x1cd8108,'cold-boot-hdmi'),(0x1cd8074,0x1cd8088,'cold-vptr'),(0x2ec5ec8,0x2ec5f18,'cold-vtable-data')],
 'fx3_ap':[(0x2e58b00,0x2e58f6c,'mpr-param-producer')],
 'fx3_mpr':[(0xb6844,0xb68e0,'init-gate'),(0xb6fe0,0xb7048,'init-capid-call'),(0x13250c,0x132610,'capid-init'),(0x13133c,0x1315a0,'capid-send'),(0x12fa40,0x12fb28,'capid-map'),(0x12fb28,0x12fd30,'capid-sync')],
 'fx6_mpr':[(0x12b3dc,0x12b478,'init-gate'),(0x12bca0,0x12bd00,'init-no-capid-call'),(0x1c9ca8,0x1c9dac,'capid-init'),(0x1c8b34,0x1c8d90,'capid-send'),(0x1c74e4,0x1c75cc,'capid-map'),(0x1c75cc,0x1c77d0,'capid-sync')],
 'helper':[(0x24550,0x245dc,'capid-control')]}
excerpts={}
for k,rs in ranges.items():
 for start,end,label in rs:
  name=f'{k}-{label}.txt';s=subprocess.check_output(['xcrun','llvm-objdump','-d',f'--start-address={start}',f'--stop-address={end}',str(P[k])],text=True);(HERE/name).write_text(s)
  excerpts[name]={'start':E[k].mapping(start),'end_exclusive':hex(end),'sha256':sha(s.encode())}
targets={'fx6_ap':[0x212f470,0x20f158c,0xb174c0,0x20dddec,0x20d00bc,0x1cd826c,0x1cd80dc],'fx3_ap':[0x1591a40],'fx3_mpr':[0x13250c,0x7d440],'fx6_mpr':[0x1c9ca8]}
xrefs={k:{'direct_branches':E[k].calls(t),'rela_addends':E[k].rels(t)} for k,t in targets.items()}
# Verify immutable CPIO actually carries FX3 libmpr; never extract or edit members.
cpio=DONOR/'hybrid-ap-candidate/guest-three-entry.cpio';cb=cpio.read_bytes();i=0;member=None
while cb[i:i+6] in (b'070701',b'070702'):
 h=cb[i:i+110];v=[int(h[j:j+8],16) for j in range(6,110,8)];n=cb[i+110:i+110+v[11]-1].decode();start=(i+110+v[11]+3)&~3;end=start+v[6]
 if n.lstrip('./')=='usr/lib/libmpr.so':member={'name':n,'fileoff':hex(start),'size':v[6],'sha256':sha(cb[start:end])}
 if n=='TRAILER!!!':break
 i=(end+3)&~3
assert member and member['sha256']==hashes['fx3_mpr']
logs={}
for name,p in [('fx3',MAC/'work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap85r4osdring-5dcb8371/serial.log'),('fx6_first',DONOR/'hybrid-ap-candidate/runs/fx6ap-bb7588e5/serial.log'),('fx6_latest',DONOR/'first-ap-readonly-observer/runs/ap-ro-f58ad0fb/serial.log')]:
 b=p.read_bytes();rows=[];offset=0
 for lineno,line in enumerate(b.splitlines(keepends=True),1):
  if any(x in line for x in [b'/usr/lib/libmpr.so',b'IWrapperMprNull',b'FX3_CAPID_BIND',b'FX3_CAPID_COMMIT',b'infra_wrapper_bb_procam_chaplin_base.cpp:1075',b'raw=0d202d030a0001800000']):rows.append({'line':lineno,'fileoff':offset,'text':line.decode('utf-8','replace').strip()})
  offset+=len(line)
 logs[name]={'path':str(p),'sha256':sha(b),'markers':rows}
# Pure integer/layout fixture; no ELF execution and no fake initialization success.
param=bytearray(0x290);struct.pack_into('<Q',param,0x1d0,0x213bde0);struct.pack_into('<I',param,0x268,2)
fixture={'fx6_correct_count':struct.unpack_from('<I',param,0x268)[0],'fx3_misread_unrelocated_callback_low32':struct.unpack_from('<I',param,0x1d0)[0],'fx3_gate_rejects_unrelocated_example':struct.unpack_from('<I',param,0x1d0)[0]>4,'warning':'runtime bias/dispatch/actual init return unobserved; demonstrates layout only'}
receipt={'status':'STATIC_PRODUCER_AND_ABI_DIFFERENCE_FOUND_RUNTIME_UNPROVEN','paths':{k:str(v) for k,v in P.items()},'hashes':hashes,'cpio_sha256':sha(cb),'cpio_mpr':member,'excerpts':excerpts,'xrefs':xrefs,'logs':logs,'fixture':fixture,'vtable_data':E['fx6_ap'].mapping(0x2ec5ec8,0x50),'key_producer_words':{hex(v):E['fx6_ap'].mapping(v) for v in [0x212f478,0x212f488,0x212f698,0x212f69c,0x212f6a0,0x212f750,0x212f7b8,0x1cd8580,0x1cd86a4]},'unknowns':['same-run PLT/GOT resolution and mpr Init call occurrence','runtime bias and count misread value','virtual startup path ordering before audio','full callback semantic conversion map']}
assert all(sha(P[k].read_bytes())==v for k,v in hashes.items())
(HERE/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps({'hashes':hashes,'member':member,'xrefs':xrefs,'fixture':fixture},indent=2))
