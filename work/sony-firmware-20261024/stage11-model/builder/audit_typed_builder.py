"""Own, read-only AArch64 static parser; only output under this task directory."""
from pathlib import Path
import io, json, hashlib, re, struct, subprocess, plistlib
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
INPUT=ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so'
EXPECTED='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
class Image:
 def __init__(self):
  self.blob=INPUT.read_bytes();assert hashlib.sha256(self.blob).hexdigest()==EXPECTED
  self.elf=ELFFile(io.BytesIO(self.blob)); self.segments=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
  self.md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);self.md.detail=True
 def read(self,a,n):
  for s in self.segments:
   if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']:
    o=s['p_offset']+a-s['p_vaddr'];return self.blob[o:o+n]
  raise ValueError(hex(a))
 def dump(self,a,z):return [{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in self.md.disasm(self.read(a,z-a),a)]
 def write(self,name,record): (OUT/name).write_text(json.dumps(record,indent=2))
 def leaf(self,a):
  ins=list(self.md.disasm(self.read(a,0x20),a));val=None
  for i in ins:
   if i.mnemonic=='adrp' and i.op_str.startswith('x0, #'): val=int(i.op_str.split('#')[1],16)
   elif i.mnemonic=='add' and i.op_str.startswith('x0, x0, #'):
    amt=int(i.op_str.split('#')[1].split(',')[0],16);val+=amt*(4096 if 'lsl #12' in i.op_str else 1)
   elif i.mnemonic=='ret':return val
   else:return None
 def strings(self,needle):
  out=[]
  for s in self.segments:
   d=s.data()
   for match in re.finditer(rb'[^\x00\x01-\x1f\x7f-\xff]{4,}',d):
    if needle.lower() in match.group().lower():out.append({'va':hex(s['p_vaddr']+match.start()),'text':match.group().decode('ascii')})
  return out

def main():
 assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 im=Image(); main=im.dump(0x2beae8c,0x2beea04)
 im.write('builder-static.json',{'sha256':EXPECTED,'builder':main})
 (OUT/'builder-disassembly.txt').write_text('\n'.join(f"{i['va']} {i['bytes']} {i['asm']}" for i in main)+'\n')
 targets=sorted({int(i['asm'].split('#')[1],16) for i in main if i['asm'].startswith('bl #')})
 leafs=[{'accessor':hex(a),'global':hex(im.leaf(a)),'raw':im.dump(a,a+20)} for a in targets if im.leaf(a) is not None]
 im.write('model-leaf-accessors.json',{'sha256':EXPECTED,'accessors':leafs})
 im.write('model-strings.json',im.strings(b'movie')+im.strings(b'frame_rate'))
 print('builder instructions',len(main),'direct calls',len(targets),'leafs',len(leafs))
 print('non-leaf calls',[hex(a) for a in targets if im.leaf(a) is None])
 print('leafs',[(x['accessor'],x['global']) for x in leafs])
if __name__=='__main__': main()
