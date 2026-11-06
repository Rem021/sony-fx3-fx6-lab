"""Locate record-walking functions in the captured ET_REL file only."""
from pathlib import Path
from io import BytesIO
from hashlib import sha256
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import json
H=Path(__file__).resolve().parent;R=H.parents[2];P=H/'originals/kmod/backup.ko';raw=P.read_bytes();e=ELFFile(BytesIO(raw));ss=e.get_section_by_name('.symtab');syms={s.name:s for s in ss.iter_symbols() if s.name};txt=e.get_section_by_name('.text');idx=next(i for i,s in enumerate(e.iter_sections()) if s.name=='.text');d=txt.data();rels={}
for s in e.iter_sections():
 if s['sh_type']!='SHT_RELA' or s['sh_info']!=idx:continue
 sy=e.get_section(s['sh_link'])
 for r in s.iter_relocations():
  z=sy.get_symbol(r['r_info_sym']);sec=z['st_shndx'];name=z.name or (e.get_section(sec).name if isinstance(sec,int) else str(sec))
  rels.setdefault(r['r_offset'],[]).append(dict(type=r['r_info_type'],symbol=name,value=z['st_value'],section=sec,addend=r['r_addend']))
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);ranges=[]
for name in ['Data_getAdrs','Data_getSize','Data_SearchId','Data_GetHeader','backupfile_init','backup_sync_msg']:
 s=syms[name];ranges.append((s['st_value'],s['st_value']+s['st_size'],name))
ranges.append((0x6618,0x66a8,'load_selected_whole_file'))
lines=[];cuts=[]
for a,z,name in ranges:
 lines.append('\n'+name)
 for i in md.disasm(d[a:z],a):lines.append(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}'+(' ; '+json.dumps(rels[i.address]) if i.address in rels else ''))
 cuts.append(dict(label=name,section='.text',offset=a,bytes=z-a,sha256=sha256(d[a:z]).hexdigest()))
lines.append('\nLITERAL RELOCATIONS')
for a in sorted(rels):
 if any(lo<=a<hi for lo,hi in [(0x4dd8,0x4de8),(0x4f58,0x4f60),(0x53a0,0x53a8),(0x5988,0x5a60),(0x6618,0x66a8),(0x7fc8,0x7ff0),(0x7980,0x79f0)]):lines.append(hex(a)+' '+json.dumps(rels[a]))
(H/'record-walk-locator.txt').open('x').write('\n'.join(lines)+'\n')
(H/'extra-cuts.json').open('x').write(json.dumps(dict(source=str(P.relative_to(R)),source_sha256=sha256(raw).hexdigest(),ranges=cuts,unapplied_relocations=True,Sony_code_or_guest_execution=False,root_or_device_operations=0),indent=2)+'\n')
print('\n'.join(lines))
