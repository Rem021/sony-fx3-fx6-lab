from pathlib import Path
from io import BytesIO
import json,hashlib
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
R=Path(__file__).resolve().parent;p=R.parent/'original-uipc/original-modules/upm.ko';b=p.read_bytes();assert hashlib.sha256(b).hexdigest()=='ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e';e=ELFFile(BytesIO(b));symtab=e.get_section_by_name('.symtab');sym=next(s for s in symtab.iter_symbols() if s.name=='k_upm_init_boot_factor');sec=e.get_section(sym['st_shndx']);refs={}
for rs in e.iter_sections():
 if rs['sh_type']=='SHT_RELA' and rs['sh_info']==sym['st_shndx']:
  st=e.get_section(rs['sh_link'])
  for rel in rs.iter_relocations():refs[rel['r_offset']]=st.get_symbol(rel['r_info_sym']).name
cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);ins=[]
for i in cs.disasm(sec.data()[sym['st_value']:sym['st_value']+sym['st_size']],sym['st_value']):ins.append({'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'relocation_symbol':refs.get(i.address)})
result={'source_sha256':hashlib.sha256(b).hexdigest(),'function':sym.name,'instructions':ins,'endpoint':'0x80924127','actual_AP25_requests_missing_receiver':'original sends return-1 errno1020; raw errno on successful requests not treated as failures','actual_UPM_trial':'AP24 k_upm_snd_rec_inh_msg+0x60 SCU VAfffffffff1388f54 faults before UPM init can complete','SCU_reference':'Sony GPL platform.h CXD900XX_SCU=f1388000; no register-side-effect model yet','scope':'Source binding and actual missing receiver, not emulated UPM or automatic success replies'}
(R/'upm-native-reply-proof.json').write_text(json.dumps(result,indent=2)+'\n');print([(i['va'],i['relocation_symbol']) for i in ins if i['relocation_symbol']])

callback=[]
for i in cs.disasm(sec.data()[0x3278:0x3334],0x3278):callback.append({'va':hex(i.address),'bytes':i.bytes.hex(),'instruction':i.mnemonic+' '+i.op_str,'relocation_symbol':refs.get(i.address)})
result['original_callback']={'entry':'0x3278','bound_by_registration_pointer_relocation':'text41c8 -> text3278','instructions':callback,'recognized_tag':'request & fffffffd == 00920111','native_payload_copy':'40bytes from original UPM boot-factor state to caller; only first16bytes captured in live run'}
result['native_return_observation']={'run':'runs/ap28upm-c0ac4524','target':'0x80924127','post_first16':'11019200020000000100000001000000','meaning':'identifier00920111/mode2/boot_type1/eecap1; first16 bytes only, no claim to full40byte readback','CP_peer_reply_added':False}
result['SCU_reference']='Restricted AP-only register bank inferred from original consumer; original UPM loaded0, actual register writef54/101 observed; no automatic CP ACK'
result['scope']='Native original UPM callback data under explicit virtual SCU profile; not physical power or full CP boot acceptance'
(R/'upm-native-reply-proof.json').write_text(json.dumps(result,indent=2)+'\n')
