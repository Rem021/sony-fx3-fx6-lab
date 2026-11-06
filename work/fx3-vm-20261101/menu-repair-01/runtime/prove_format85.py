from pathlib import Path
import json,hashlib,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
R=Path(__file__).resolve().parent;P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib/libObj.so';b=P.read_bytes();assert hashlib.sha256(b).hexdigest()=='c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae';out={'original_sha256':hashlib.sha256(b).hexdigest(),'blocks':{},'tables':{},'conclusion':'Bitmap enum domain differs from GPE format; map1/7->GPE0 2B,2/8->GPE1 4B. Other native formats remain rejected. No byte capacity/extent gate relaxed.'}
with P.open('rb') as f:
 ef=ELFFile(f)
 def raw(v,n):
  o=next(s['p_offset']+v-s['p_vaddr'] for s in ef.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v and v+n<=s['p_vaddr']+s['p_filesz']);return b[o:o+n]
 cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
 for v,n in [(0xef074,0x74),(0xf09f0,0x4c),(0xf0e94,0x6c),(0x101890,0x80),(0x101b14,0x80)]:
  q=raw(v,n);out['blocks'][hex(v)]={'bytes':q.hex(),'instructions':[{'va':hex(i.address),'bytes':i.bytes.hex(),'asm':i.mnemonic+' '+i.op_str} for i in cs.disasm(q,v)]}
 for v,n in [(0x1de628,20),(0x1e220c,8),(0x1e2214,8),(0x1e221c,8)]:out['tables'][hex(v)]=raw(v,n).hex()
 bp=struct.unpack('<10H',raw(0x1de628,20));assert bp[1]==bp[7]==2 and bp[2]==bp[8]==4;out['native_bitmap_Bpp_table']=list(bp);out['fill_branch_targets']={str(k+1):hex(0x1018b8+struct.unpack('b',bytes([x]))[0]*4) for k,x in enumerate(raw(0x1e220c,8))};out['software_supported_mapping']={'1':0,'7':0,'2':1,'8':1};(R/'ap85-format-domain-proof.json').write_text(json.dumps(out,indent=2)+'\n');print('FORMAT_DOMAIN_PROOF',out['fill_branch_targets'],bp)
