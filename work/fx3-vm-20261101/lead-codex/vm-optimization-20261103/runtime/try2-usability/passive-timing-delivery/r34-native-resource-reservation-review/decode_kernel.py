#!/usr/bin/env python3
"""Offline disassembly only. Run with existing verification venv, Python -B."""

import plistlib, subprocess
assert plistlib.loads(subprocess.check_output(['/usr/sbin/diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
from pathlib import Path
import json,hashlib,io
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
from elftools.elf.elffile import ELFFile
HERE=Path(__file__).resolve().parent;ROOT=next(p for p in HERE.parents if p.name=='Mac')
p=ROOT/'work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin';data=p.read_bytes();assert hashlib.sha256(data).hexdigest()=='da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c'
cat=json.loads((ROOT/'work/sony-firmware-20261024/stage146-original-kernel-symbol-and-vendor-route/work/kernel-symbol-catalog.json').read_text());byaddr={x['address']:x['name'] for x in cat};cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM);result={}
for i,x in enumerate(cat):
 if x['name'] not in ['parse_memrsv','arch_memrsv_add','is_ext_reserved_area','mmap_mem','phys_mem_access_prot','phys_mem_access_prot_allowed','valid_mmap_phys_addr_range','rmem_arm_add']:continue
 end=next(y['address'] for y in cat[i+1:] if y['address']>x['address']);size=end-x['address'];raw=data[x['file_offset']:x['file_offset']+size];lines=[]
 for ins in cs.disasm(raw,x['address']):
  target=''
  if ins.mnemonic in ['bl','b'] and ins.op_str.startswith('#'):
   a=int(ins.op_str[1:],16);target=byaddr.get(a,'')
  lines.append(dict(address=hex(ins.address),file_offset=hex(ins.address-x['address']+x['file_offset']),bytes=ins.bytes.hex(),instruction=ins.mnemonic+' '+ins.op_str,call_target=target))
 result[x['name']]=dict(symbol=x,bytes=size,instructions=lines)
(HERE/'KERNEL-EXACT.json').write_text(json.dumps(result,indent=2)+'\n')
(HERE/'KERNEL-EXACT.txt').write_text('\n\n'.join(name+'\n'+'\n'.join(i['address']+' '+i['bytes']+' '+i['instruction']+(' <'+i['call_target']+'>' if i['call_target'] else '') for i in v['instructions']) for name,v in result.items())+'\n')
with (HERE/'libObj.so').open('rb') as f:
 elf=ELFFile(f);fdes=[]
 for e in elf.get_dwarf_info().EH_CFI_entries():
  if hasattr(e,'header') and 'initial_location' in e.header and e.header['initial_location'] in [0x1031b0,0x1032f4,0xf96f4]:fdes.append(dict(start=hex(e.header['initial_location']),bytes=e.header['address_range'],end_exclusive=hex(e.header['initial_location']+e.header['address_range'])))
(HERE/'LIBOBJ-FUNCTION-BOUNDARIES.json').write_text(json.dumps(fdes,indent=2)+'\n');print(json.dumps(fdes));print('exact kernel functions',len(result))
