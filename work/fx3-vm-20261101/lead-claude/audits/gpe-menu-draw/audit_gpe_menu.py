#!/usr/bin/env python3
"""Read-only FX3 AP static audit. Only output is adjacent proof JSON."""
from pathlib import Path
from io import BytesIO
import json, hashlib, subprocess, struct, plistlib
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
volume=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
assert volume.get('VolumeUUID','').upper()=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B', 'Target volume identity mismatch'
R=Path(__file__).resolve().parent
P=next(p for p in R.parents if (p/'menu-repair-01').is_dir())
A=P/'menu-repair-01/original-uipc/ap-projection/regular-files'
cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN)
def audit(name, select):
 p=A/'usr/lib'/name;b=p.read_bytes();e=ELFFile(BytesIO(b));ds=e.get_section_by_name('.dynsym');plt=e.get_section_by_name('.plt');rel=e.get_section_by_name('.rela.plt')
 mp={plt['sh_addr']+32+i*16:ds.get_symbol(x['r_info_sym']).name for i,x in enumerate(rel.iter_relocations())} if rel else {}
 syms=list(ds.iter_symbols());names=[s.name for s in syms];dem=subprocess.check_output(['c++filt'],input='\n'.join(names),text=True).splitlines()
 out={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'exports':[],'functions':{}}
 for s,d in zip(syms,dem):
  if s['st_shndx']=='SHN_UNDEF' or s['st_info']['type']!='STT_FUNC':continue
  a=s['st_value'];n=s['st_size'];out['exports'].append({'symbol':s.name,'demangled':d,'va':hex(a),'size':n})
  if not n or not select(s.name,d,a):continue
  seg=next(t for t in e.iter_segments() if t['p_type']=='PT_LOAD' and t['p_vaddr']<=a and a+n<=t['p_vaddr']+t['p_filesz']);off=seg['p_offset']+a-seg['p_vaddr']
  out['functions'][hex(a)]={'symbol':s.name,'demangled':d,'instructions':[{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str,**({'callee':mp.get(int(i.op_str[1:],16),'internal')} if i.mnemonic in ['b','bl'] and i.op_str.startswith('#') else {})} for i in cs.disasm(b[off:off+n],a)]}
 return out
out={'scope':'Static original AArch64 little-endian library audit; no runtime or device execution','libraries':{}}
out['libraries']['libgpe.so']=audit('libgpe.so',lambda s,d,a:True)
out['libraries']['libObj.so']=audit('libObj.so',lambda s,d,a:any(t in d for t in ['GRM_gperm','GetDmmMemInfo','TextRM_loadFont','registerFontFaceFile']) or 0x101e2c<=a<=0x102800)
# Private routines have no dynsym; explicit audited ranges, not guessed symbols.
for lib,blocks in {'libgpe.so':[(0xa398,0x98),(0xadac,0x450),(0xb1f4,0xd38),(0xbbcc,0x588),(0xd6b0,0x164)],'libObj.so':[(0x100b40,0xc6c),(0x10120c,0x5a0),(0x102344,0x4bc),(0x102b98,0x70),(0x102ee0,0xf0),(0x103550,0xfc)]}.items():
 b=(A/'usr/lib'/lib).read_bytes();e=ELFFile(BytesIO(b));t=e.get_section_by_name('.text')
 for a,n in blocks:
  off=t['sh_offset']+a-t['sh_addr']
  out['libraries'][lib]['functions'][hex(a)]={'symbol':None,'demangled':'private range','instructions':[{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(b[off:off+n],a)]}
 e=ELFFile(BytesIO(b))
 out['libraries'][lib]['rodata_tables']={}
 if lib=='libgpe.so':
  for a,n in [(0x14e70,6),(0x151f8,4),(0x15200,4),(0x15208,3),(0x15210,4)]:
   seg=next(t for t in e.iter_segments() if t['p_type']=='PT_LOAD' and t['p_vaddr']<=a<a+n<=t['p_vaddr']+t['p_filesz']);off=seg['p_offset']+a-seg['p_vaddr']
   out['libraries'][lib]['rodata_tables'][hex(a)]=b[off:off+n].hex()
resources=[]
for p in sorted(list((A/'usr/share/app').iterdir())+list((A/'tmp/images').glob('*.ltt'))):
 if p.suffix not in ['.ttf','.ltt','.uxb'] and not p.name.startswith('image_') and p.name not in ['fontlist.dat','string_english.uxc']:continue
 b=p.read_bytes();item={'path':'/'+str(p.relative_to(A)),'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'header64':b[:64].hex()}
 if b[:4]==b'\x00\x01\x00\x00':
  n=struct.unpack_from('>H',b,4)[0];item['format']='sfnt TrueType';item['tables']=[b[12+16*i:16+16*i].decode('ascii','replace') for i in range(n)]
 elif p.name=='fontlist.dat':item['text']=b.decode('utf-8',errors='replace')
 elif b.startswith(b'LTT\n'):item['format']='Monotype LTT font-linking container, version lines 7/2; embedded glyph codec unconfirmed'
 else:item['format']='UX container '+repr(b[:4])+'; internal image/string codec unconfirmed'
 resources.append(item)
out['resources']=resources
# Byte-level anchors reject a different build or a mistaken VA translation.
anchors={'libgpe.so':{0xa5b0:'20008052',0xa7fc:'80008052',0xc760:'85004039'},'libObj.so':{0x102bc0:'210003cb'}}
for lib,checks in anchors.items():
 b=(A/'usr/lib'/lib).read_bytes();e=ELFFile(BytesIO(b))
 for va,want in checks.items():
  seg=next(t for t in e.iter_segments() if t['p_type']=='PT_LOAD' and t['p_vaddr']<=va<va+4<=t['p_vaddr']+t['p_filesz']);off=seg['p_offset']+va-seg['p_vaddr']
  assert b[off:off+4].hex()==want,(lib,hex(va),b[off:off+4].hex(),want)
out['validation']={'anchors':{k:{hex(a):v for a,v in x.items()} for k,x in anchors.items()},'result':'passed'}
out['validation']['volume_uuid']=volume['VolumeUUID']
out['operations']=[{'opcode':k,'name':n,'parameter_bytes':sz,'message_bytes':sz+16,'constructor_va':hex(a)} for k,n,sz,a in [(0,'FillRect',56,0xa430),(1,'BitBlit',144,0xa514),(2,'StretchRotateBlit',144,0xa5f0),(3,'DrawVariousFrames',240,0xa6cc),(4,'Flush',24,0xa768)]]
out['unconfirmed']=['Actual menu-session BitBlit/CLUT request histogram is not captured; static reachability is not runtime use.','Text glyph rasterizer to GPE bitmap binding is not closed; no text opcode exists in audited Gperm dispatcher.','Format2/3/4 channel meaning and exact alpha rounding/premultiplication are not proven.','af98 emits fixed conversion coefficients, not proof of an indexed palette/CLUT.','DMM lookup/pinning must use live extents; GetDmmMemInfo is a stateful creation/map path.','nativeSendDrawComp name is not a defined dynsym in libgpe/libObj/appFw; audited completion API is mpgpe::message::SendDrawComp.','UX container image codec and LTT embedded font representation remain unconfirmed.']
out['model_evidence']={str(p.relative_to(P)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [P/'menu-repair-01/runtime/helpers/fx3-gpe-observe-v12.c',P/'menu-repair-01/runtime/helpers/fx3-gpe-uniform-v2.c',P/'menu-repair-01/runtime/gpe-uniform-native-readback.json']}
out['reference']='https://www.capstone-engine.org/lang_python (AArch64 disassembly API only; firmware semantics from local original)'
(R/'gpe-menu-draw-proof.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('PASS: regenerated',R/'gpe-menu-draw-proof.json')
if __name__=='__main__':
 import sys
 if '--show' in sys.argv:
  for lib,l in out['libraries'].items():
   for va,f in l['functions'].items():
    if lib=='libgpe.so' and int(va,16)>=0xde70:continue
    print(lib,va,f['demangled']);print('\n'.join(i['va']+' '+i['asm']+' '+i.get('callee','') for i in f['instructions']))
