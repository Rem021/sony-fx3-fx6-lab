"""FX3 original-file static provenance and narrowly scoped main setter audit."""
from pathlib import Path
import io,json,hashlib,struct,subprocess,plistlib
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
INPUT=ROOT/'work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so'
EXPECTED='545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f'
class Image:
 def __init__(self):
  self.blob=INPUT.read_bytes();assert hashlib.sha256(self.blob).hexdigest()==EXPECTED
  self.elf=ELFFile(io.BytesIO(self.blob));assert self.elf['e_machine']=='EM_AARCH64'
  self.segments=[s for s in self.elf.iter_segments() if s['p_type']=='PT_LOAD']
  self.md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 def read(self,a,n):
  for s in self.segments:
   if s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']:
    o=s['p_offset']+a-s['p_vaddr'];return self.blob[o:o+n]
  raise ValueError(hex(a))
 def dump(self,a,z):
  return [{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in self.md.disasm(self.read(a,z-a),a)]
 def calls(self,targets):
  result=[]
  for s in self.segments:
   if not s['p_flags']&1:continue
   data=s.data();va=s['p_vaddr']
   for k in range(0,len(data)-3,4):
    w=struct.unpack_from('<I',data,k)[0]
    if w>>26 not in (0b100101,0b000101):continue
    off=w&0x3ffffff;off=off-(1<<26) if off&(1<<25) else off
    target=va+k+off*4
    if target in targets:
     a=va+k;result.append({'call_va':hex(a),'target_va':hex(target),'context':self.dump(a-0x60,a+0x20)})
  return result

def run():
 v=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
 assert v['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
 im=Image()
 out={'input':str(INPUT),'sha256':EXPECTED,'execution':'static only; no firmware/USB/native execution','setter':im.dump(0x2e6e5d8,0x2e6f9c4),'wrapper':im.dump(0x2ddae94,0x2ddaed4),'callers':im.calls({0x2ddae94,0x2e6e5d8}), 'producer_first_caller':im.dump(0x2b60000,0x2b60550),'format_entry':im.dump(0x2e6ea18,0x2e6ea68)}
 (OUT/'actual-main-setter-static.json').write_text(json.dumps(out,indent=2))
 print('setter_bytes',len(im.read(0x2e6e5d8,0x2e6f9c4-0x2e6e5d8)),'caller_count',len(out['callers']))
 for i in out['producer_first_caller']:
  if any(x in i['asm'] for x in ['bl ','str ','stp ','#0x490','#0x4a0','#0x4a4','#0x4a8','#0x4ac']):print(i['va'],i['asm'])
if __name__=='__main__':run()
