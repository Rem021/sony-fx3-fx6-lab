from pathlib import Path
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import struct,json,hashlib
R=Path(__file__).resolve().parent;m=json.loads((R.parent/'original-uipc/ap-projection/full-v4/projection-manifest-full-v4.json').read_text());row=next(x for x in m['members'] if x['guest_path']=='/usr/lib/appFw.so');b=Path(row['local_file']).read_bytes();assert hashlib.sha256(b).hexdigest()==row['sha256'];e=ELFFile(open(row['local_file'],'rb'));cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);out=[]
for seg in e.iter_segments():
 if seg['p_type']!='PT_LOAD' or not seg['p_flags']&1:continue
 off=seg['p_offset'];data=b[off:off+seg['p_filesz']]
 for i in range(0,len(data)-4,4):
  w=struct.unpack_from('<I',data,i)[0]
  if w&0xffe00000!=0x52800000 or (w>>5)&65535!=0x15e:continue
  rd=w&31
  if not any(struct.unpack_from('<I',data,j)[0]==0x72a00000|(0x9004<<5)|rd for j in range(i+4,min(i+80,len(data)-3),4)):continue
  a=seg['p_vaddr']+i;start=max(0,i-0x60);n=min(len(data)-start,0xf0);out.append({'target_mov':hex(a),'instructions':[{'va':hex(x.address),'bytes':x.bytes.hex(),'instruction':x.mnemonic+' '+x.op_str} for x in cs.disasm(data[start:start+n],seg['p_vaddr']+start)]})
(R/'capid-fx3-candidate-proof.json').write_text(json.dumps({'source_sha256':row['sha256'],'candidates':out},indent=2)+'\n');print([x['target_mov'] for x in out])
for x in out:print('\n'.join(i['va']+' '+i['instruction'] for i in x['instructions']))
