"""Disassemble pinned ordinary files; relocations are annotations, never applied/executed."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import json,re
H=Path(__file__).resolve().parent;R=H.parents[2];P=H/'originals/kmod/backup.ko';d=P.read_bytes();e=ELFFile(BytesIO(d));ss=e.get_section_by_name('.symtab')
symbols={s.name:s for s in ss.iter_symbols() if s.name};relocs={}
for s in e.iter_sections():
    if s['sh_type']!='SHT_RELA':continue
    sy=e.get_section(s['sh_link']);target=s['sh_info']
    for rel in s.iter_relocations():
        sym=sy.get_symbol(rel['r_info_sym']);section=sym['st_shndx'];name=sym.name or (e.get_section(section).name if isinstance(section,int) else str(section))
        relocs.setdefault((target,rel['r_offset']),[]).append(dict(type=rel['r_info_type'],symbol=name,symbol_value=sym['st_value'],symbol_section=section,addend=rel['r_addend']))
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);cuts=[];selected=['Backup_read_4Byte','Backup_read','Backup_nread','Data_init','Data_GetDataPt','Data_GetBackupDataInfo','backupfile_load_file','backupfile_load','backupfile_get_file_datasize','backupfile_get_cp_data','backup_osal_call_func','backup_osal_init']
for name in selected:
    s=symbols[name];section=e.get_section(s['st_shndx']);a=s['st_value'];z=a+s['st_size'];part=section.data()[a:z];assert len(part)==s['st_size'];lines=[]
    for i in md.disasm(part,a):
        notes=relocs.get((s['st_shndx'],i.address),[])
        lines.append(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}'+(' ; '+json.dumps(notes) if notes else ''))
    out=H/'disassembly'/(name+'.txt');out.parent.mkdir(exist_ok=True);out.open('x').write('\n'.join(lines)+'\n')
    cuts.append(dict(symbol=name,section=section.name,section_index=s['st_shndx'],offset=a,bytes=s['st_size'],sha256=sha256(part).hexdigest(),output=str(out.relative_to(R))))
(H/'function-cuts.json').open('x').write(json.dumps(dict(source=str(P.relative_to(R)),source_sha256=sha256(d).hexdigest(),ranges=cuts,relocations_are_unapplied_annotations=True,Sony_code_or_guest_execution=False,root_or_device_operations=0),indent=2)+'\n')
print('objects',[(s.name,hex(s['st_value']),s['st_size'],s['st_shndx']) for s in ss.iter_symbols() if s['st_info']['type']=='STT_OBJECT' and s['st_size']>=8 and s['st_shndx']!='SHN_UNDEF'][:90])
for sec in e.iter_sections():
 if sec.name.startswith('.rodata'):
  print('string section',sec.name)
  for m in re.finditer(rb'[\x20-\x7e]{5,}',sec.data()):
   text=m.group().decode()
   if any(v in text.lower() for v in ['backup','load','cp','read','data','file','ap']):print(hex(m.start()),text)
