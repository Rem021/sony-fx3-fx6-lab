"""Bind the actual user-ioctl registration route, separately from kernel API."""
from pathlib import Path
from io import BytesIO
from hashlib import sha256
import json
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
H=Path(__file__).resolve().parent; md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.skipdata=True;rows=[]
for name,section,a,z,label in [
 ('/lib/libosal_uipc.so',None,0x6b78,0x6dac,'user-register-API'),
 ('/lib/libosal_uipc.so',None,0x3cd8,0x3d68,'user-register-ioctl'),
 ('/kmod/osal_uipc.ko','.text',0xe90,0xfc4,'kernel-register-from-user')]:
    raw=(H/'originals/7.02-main'/name.lstrip('/')).read_bytes();e=ELFFile(BytesIO(raw));note={};rel={}
    if section:
        sec=e.get_section_by_name(section);part=sec.data()[a:z];rs=e.get_section_by_name('.rela'+section);st=e.get_section(rs['sh_link'])
        rel={r['r_offset']:dict(symbol=st.get_symbol(r['r_info_sym']).name,addend=r['r_addend'],type=r['r_info_type']) for r in rs.iter_relocations()}
    else:
        s=next(s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and z<=s['p_vaddr']+s['p_filesz']);off=s['p_offset']+a-s['p_vaddr'];part=raw[off:off+z-a]
        rs=e.get_section_by_name('.rela.plt');st=e.get_section(rs['sh_link']);plt=e.get_section_by_name('.plt');note={plt['sh_addr']+32+16*n:st.get_symbol(r['r_info_sym']).name for n,r in enumerate(rs.iter_relocations())}
    lines=[]
    for i in md.disasm(part,a):
        target=int(i.op_str[1:],16) if i.mnemonic in ['bl','b'] and i.op_str.startswith('#') else -1
        extra=' ; '+note[target] if target in note else ''
        if i.address in rel:extra+=' ; relocation '+str(rel[i.address])
        lines.append(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}{extra}')
    assert len(lines)*4==len(part)
    out=H/(label+'.txt');out.write_text('\n'.join(lines)+'\n')
    rows.append(dict(source=name,source_sha256=sha256(raw).hexdigest(),address_kind='section_offset' if section else 'ELF_VA',section=section,start=hex(a),end_exclusive=hex(z),bytes=len(part),sha256=sha256(part).hexdigest(),disassembly=out.name))
with (H/'user-registration-proof.json').open('x') as f:
    json.dump(dict(selected_original_ranges=rows,route=[
      'libObj registers0x004b0376; bit15 is0, so user API takes branch6ba4->6ce0->u_osal_reg_msg_queue_cb',
      'user helper builds async registration payload and ioctl low32 request0x80000008',
      'kernel registration-from-user stores userspace callback/opaque context in node, selects async reg_msg_queue_cb with uxth(w19) at0xfa8',
      'sender0x804b0376 has bit31 set but bits30..28 zero, so kernel send takes local low16 queue0x0376; no remote public hook at this branch',
      'kernel pending proxy and libosal userspace callback dispatch precede business function; registration must actually succeed and service remain alive'
    ],kernel_direct_reg_API_slice_is_context_not_actual_user_registration_entry=True,actual_runtime_registration_observed=False,original_or_guest_execution=False,root_or_device_operations=0),f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(actual_user_registration_ranges=len(rows),guest_or_device_execution=False)))
