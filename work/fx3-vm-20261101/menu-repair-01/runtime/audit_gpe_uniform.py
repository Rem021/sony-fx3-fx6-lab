from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import *
import json,hashlib
R=Path(__file__).resolve().parent;A=R.parent/'original-uipc/ap-projection/regular-files/usr/lib';out={}
for name,blocks in {'libgpe.so':[(0xb1f4,0x40),(0xc3fc,0x34),(0xc458,0x10),(0xc60c,0x68),(0xc69c,0x58),(0xaf08,0x28),(0xa158,0x84),(0xd6b0,0xc4)],'libObj.so':[(0x101d84,0xa8),(0x102394,0xa0)]}.items():
 p=A/name;b=p.read_bytes();e=ELFFile(p.open('rb'));sec=e.get_section_by_name('.text');cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM);out[name]={'sha256':hashlib.sha256(b).hexdigest(),'blocks':{hex(a):[{'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str} for i in cs.disasm(sec.data()[a-sec['sh_addr']:a-sec['sh_addr']+n],a)] for a,n in blocks}}
out['facts']=['c60c offset=y*stride+x; b1f4 format0 =>multiply2, format1 =>multiply4','c3fc color8bit channels quantized to RGBA4444; uniformchannels avoid unverified channel ordering for32bit','c458 blend0/alpha255 overwrite branch c50c; c69c flag38 withnullcallback skips SetCallback; no callback supported','a158 original callback info issequence32/reserved0/argument64; d6b0 SendDrawComp alloc/copy/send and freeonfailure','GetDmmMemInfo argument isnot proven tobe allocatedhandle; function constructs object, not purequery. AP56rc2; no subsequent use.','Softwaremodel uses exactliveextent545/43feb5000/140000 and originalFIFO pending draw lifetime; doesnot claim independent allocatorpin']
(R/'gpe-uniform-original-proof.json').write_text(json.dumps(out,indent=2)+'\n');print('original proof saved')
