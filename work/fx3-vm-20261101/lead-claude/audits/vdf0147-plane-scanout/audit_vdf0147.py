#!/usr/bin/env python3
"""Rebuild static firmware/log evidence only. No QEMU, QMP or guest writes."""
import hashlib,json,struct,re,plistlib,subprocess
from pathlib import Path
from capstone import *
from elftools.elf.elffile import ELFFile
R=Path(__file__).resolve().parent
ROOT=next(p for p in R.parents if (p/'work/sony-firmware-20261024').is_dir())
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID'].upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
RT=ROOT/'work/fx3-vm-20261101/menu-repair-01/runtime'
AP=RT.parent/'original-uipc/ap-projection/regular-files/usr/lib/appFw.so'
CP=ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin'
sha=lambda b:hashlib.sha256(b).hexdigest()
assert sha(AP.read_bytes())=='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
assert sha(CP.read_bytes())=='c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba'
proof={'scope':'Offline static evidence; no runtime writes; no physical scanout claim','sources':{},'blocks':{},'captures':{},'records':[]}
def source(p):
 b=p.read_bytes();proof['sources'][str(p.relative_to(ROOT))]={'sha256':sha(b),'bytes':len(b)};return b
libs={}
for name,p in [('appFw',AP),('cpapp',CP),('libObj',AP.parent/'libObj.so'),('libgpe',AP.parent/'libgpe.so')]:
 b=source(p);segs=[]
 if name!='cpapp':
  with p.open('rb') as f:
   e=ELFFile(f);segs=[dict(s.header) for s in e.iter_segments() if s['p_type']=='PT_LOAD']
   if name=='libObj':
    rel=e.get_section_by_name('.rela.plt');syms=e.get_section(rel['sh_link']);pv=e.get_section_by_name('.plt')['sh_addr']
    proof['libObj_plt']={hex(pv+32+16*n):syms.get_symbol(r['r_info_sym']).name for n,r in enumerate(rel.iter_relocations()) if pv+32+16*n in [0x55fd0,0x563d0,0x55750]}
 libs[name]=(b,segs)
def read(name,va,n):
 b,segs=libs[name]
 if name=='cpapp':o=va-0x108000
 else:
  s=next(s for s in segs if s['p_vaddr']<=va<s['p_vaddr']+s['p_filesz']);o=s['p_offset']+va-s['p_vaddr']
 return b[o:o+n]
def block(name,va,n):
 c=Cs(CS_ARCH_ARM,CS_MODE_THUMB) if name=='cpapp' else Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 rows=[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in c.disasm(read(name,va,n),va)]
 assert sum(len(bytes.fromhex(r['bytes'])) for r in rows)==n,(name,hex(va),n)
 proof['blocks'].setdefault(name,{})[hex(va)]=rows
for va,n in [(0x2deb060,0x3b0),(0x2dcffd4,0x40),(0x2bb94f4,0x9c),(0x2df8a30,0x11c)]:block('appFw',va,n)
old=json.loads(source(RT/'fx3-vdf-plane-proof.json'))
for va,rows in old['blocks'].items():block('cpapp',int(va,16),sum(len(bytes.fromhex(r['bytes'])) for r in rows))
for va,n in [(0x5f56b8,0xe8),(0x5fb350,0x68)]:block('cpapp',va,n)
for va,n in [(0xf1d90,0x8c),(0xf1e1c,0x8c),(0xf16b0,0x120),(0xf33d0,0x34),(0xf2fa0,0x10c),(0xf2428,0x148),(0xf233c,0x44),(0xf2638,0x1a0),(0xf27d8,0x10c),(0xf335c,0x24),(0xf3924,8),(0xf3934,8),(0xf1fbc,0x8c),(0x16ea10,0xd4),(0x101d84,0xa0),(0x102b98,0x70)]:block('libObj',va,n)
for va,n in [(0xc30c,0x13c),(0xc60c,0x90),(0xb1f4,0x40),(0xb354,0x78)]:block('libgpe',va,n)
# Hard code anchors: independent native bytes; not generated labels.
assert 'mov w0, #0x147' in [x['instruction'] for x in proof['blocks']['appFw']['0x2deb060']]
assert read('cpapp',0x5f1378,4)==bytes.fromhex('4ff22400') # movw r0, f024
assert read('libObj',0xf33ec,8)==bytes.fromhex('600646a9610206a9') # swap pointers
for run in ['ap66lut-ed5764ad','ap70lcd-f61554d9']:
 p=RT/'runs'/run/'serial.log';data=source(p);lines=data.decode(errors='replace').splitlines();hits=[]
 for j,line in enumerate(lines):
  if 'FX3_PROVIDER_REQUEST' in line and 'bytes=776' in line:
   raw=bytes.fromhex(re.search(r'raw=([0-9a-f]+)',line)[1]);assert len(raw)==776
   assert raw[:8]==bytes.fromhex('0d20470108030180');hits.append({'line':j+1,'hex':raw.hex(),'sha256':sha(raw),'context':lines[max(0,j-13):j+8]})
 assert hits;proof['captures'][run]=hits
 proof.setdefault('bounded_runtime_observations',{})[run]=[{'line':j+1,'text':line} for j,line in enumerate(lines) if any(t in line for t in ['FX3_GPE_UNIFORM_DONE','FX3_GPE_UNIFORM_FLUSH','FX3_VDF_PLANE_COMMIT','FX3_OSD_ONOFF_ACCEPT'])]
raw=bytes.fromhex(proof['captures']['ap70lcd-f61554d9'][0]['hex'])
assert all(bytes.fromhex(h['hex'])==raw for hits in proof['captures'].values() for h in hits)
fixture=source(RT/'ap52-plane-observe/0147-native-request.bin');assert fixture==raw
for i in range(24):
 q=raw[8+i*32:40+i*32];mask,mode,res,layout=struct.unpack('<4B',q[:4]);rect=struct.unpack('<8H',q[4:20])
 proof['records'].append({'index':i,'request_offset':8+32*i,'raw':q.hex(),'selector_mask':mask,'mode':mode,'reserved2':res,'layout_id':layout,'rect_A_xywh':list(rect[:4]),'rect_B_xywh':list(rect[4:]),'option20':q[20],'option21':q[21],'fields22_23':q[22:24].hex(),'option24':q[24],'fields25_27':q[25:28].hex(),'word28':struct.unpack('<I',q[28:])[0], 'pixel_address':None,'stride':None,'pixel_format':None,'alpha_or_z':None,'bank':None})
# RTTI/vtable links, matching ARM Thumb bit explicitly.
for name,vt in [('N3VDF29VdfInputCmdSetYuvLayoutOptionE',0xb7e5d4),('N3VDF20VdfInputSetOsdLayoutE',0xb7e474),('N3VDF20VdfInputCmdUpdateYuvE',0xb7e634)]:
 b=libs['cpapp'][0];nv=b.index(name.encode()+b'\0')+0x108000
 proof.setdefault('classes',{})[name]={'name_va':hex(nv),'vtable':hex(vt),'slots':{hex(k):hex(struct.unpack('<I',read('cpapp',vt+k,4))[0]) for k in [0xc,0x10,0x14]}}
assert proof['classes']['N3VDF29VdfInputCmdSetYuvLayoutOptionE']['slots']['0x10']=='0x1dc171'
for p in [RT/'helpers/fx3-vdf-plane.c',RT/'helpers/fx3-capid-v25.c',RT/'helpers/vdf-plane-host-check.json']:source(p)
proof['conclusions']={'0147':'24 YUV layout option records, not pixel planes','banks':'768B config at object+4/+304; selector+604; f024 pointer refers to retained config','OSD_swap':'libObj f33d0 swaps pointers at +60/+68 unless +70 flag set','publish_candidate':'libObj f2fa0 -> f2428 -> local msg1/40B to8288076c -> f2638 -> msg36B to8280084d; final pin/CP consumption unclosed','format0':'code packs c0,c1,c2,c3 in bits12,8,4,0 of LE16; RGBA semantics unproven','frame_dump':'explicit caller-supplied address, stride, component map, alpha policy and z required'}
proof['unproven']=['selector1/2/4 exact LCD/EVF/HDMI enum names','rectangle A/B exact source/destination domain beyond validation and layout construction','0147 fields20/21/24/28 full enum semantics','OSD pin8280084d to physical CP scanout binding, active frame and flip timing','545 extent to current scanout handle mapping and second buffer address','RGBA channel names, straight/premultiplied alpha, hardware rounding, LCD/YUV/OSD multi-plane z order']
(R/'vdf0147-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
print('PASS: rebuilt vdf0147-proof.json; 24 records; equal AP52/AP66/AP70 raw; original-code anchors')
