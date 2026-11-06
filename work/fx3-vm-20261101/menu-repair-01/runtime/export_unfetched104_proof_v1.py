from pathlib import Path
import json,hashlib,re
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
R=Path(__file__).resolve().parent;r=R/'runs/ap104light4save1200-2e5d177c';out=R/'ap104-unfetched-source-timeline-v1.json';assert not out.exists();s=(r/'serial.log').read_bytes();lines=s.decode(errors='replace').splitlines();wanted=[]
for no,line in enumerate(lines,1):
 if ('FX3_GPE104_DYNAMIC_'in line and re.search(r'event=(485|486)\b',line))or('FX3_GPE104_COMPLETE_'in line and 'seq=1207 'in line)or('FX3_LIGHT104_'in line and re.search(r'event=(2584|2585|2586)\b',line))or'unfetched dynamic queue'in line or('FX3_GPE104_CMD_RETURN'in line and 'seq=1207 'in line):wanted.append({'line':no,'text':line})
p=R.parent/'original-uipc/ap-projection/regular-files/usr/lib/libgpe.so';# exact source lives one level above menu-repair runtime
p=R.parent/'original-uipc/ap-projection/regular-files/usr/lib/libgpe.so'
assert p.is_file();assert hashlib.sha256(p.read_bytes()).hexdigest()=='363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464';blocks=[]
with p.open('rb')as f:
 e=ELFFile(f);pl=e.get_section_by_name('.plt');rel=e.get_section_by_name('.rela.plt');sy=e.get_section(rel['sh_link']);names={pl['sh_addr']+32+i*16:sy.get_symbol(x['r_info_sym']).name for i,x in enumerate(rel.iter_relocations())}
 for address,n in [(0xd89c,0x18),(0xd774,0x40),(0xa3d4,0x5c),(0x9c3c,0x18)]:
  for seg in e.iter_segments():
   if seg['p_type']=='PT_LOAD'and seg['p_vaddr']<=address<address+n<=seg['p_vaddr']+seg['p_filesz']:f.seek(seg['p_offset']+address-seg['p_vaddr']);b=f.read(n);break
  rows=[]
  for i in Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN).disasm(b,address):
   dst=int(i.op_str[1:],16)if i.mnemonic=='bl'and i.op_str.startswith('#')else 0;rows.append({'VA':hex(i.address),'bytes':i.bytes.hex(),'mnemonic':i.mnemonic,'operands':i.op_str,'PLT_symbol':names.get(dst)})
  blocks.append({'VA':hex(address),'bytes':b.hex(),'instructions':rows})
v={'run':str(r),'serial_SHA256':hashlib.sha256(s).hexdigest(),'input_original_ELF':str(p),'ELF_SHA256':hashlib.sha256(p.read_bytes()).hexdigest(),'libgpe_runtime_base':'0x7f7c16b000','QID':'0x808261c0','primary_flush_seq':1207,'native_clock':'CLOCK_MONOTONIC from existing user wrappers; kernel printk clock not mixed','claim_return_ns':350103662992,'release_enter_ns':355213540000,'release_return_ns':355389662000,'first_zero_completion_attempt_ns':400101364000,'first_zero_completion_return_ns':400115166000,'claim_to_release_return_ns':5285999008,'release_return_to_first_zero_attempt_ns':44711702000,'primary_alloc_result':-1018,'primary_alloc_errno':1018,'secondary_native_Main_PLT':{'caller_relative':'0x9c50','status':5,'alloc_result':-1018,'SendDrawComp_bool':0,'errno':1018},'native_SyncCallback_PLT_path_logged_count':0,'source_conclusion':'ReceiveDrawComp setsw3=1; helper retains timeout0x1388 at d798 and calls osal_rcv_msg_tmo at d7a8; CMF releases dynamic queue at a41c after success or failure. Observed5.286s to release and latefirst completion support receive-budget expiry, not duplicate-zero as this first fault cause.','boundary':'Direct ReceiveDrawComp entry/return not interposed. No kernel owner-read in light mode; release APIsucceeded and original code proves its clear operation. Absence of another zero log is limited to recovered rows, not global negative proof.','raw_timeline':wanted,'source_blocks':blocks,'lifecycle':json.loads((r/'receipt.json').read_text())['restore103']};out.write_text(json.dumps(v,indent=2)+'\n');print(out)
