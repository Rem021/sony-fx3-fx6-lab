"""Pin current 7.02 queue registration and its filesystem effects, statically."""
from pathlib import Path
from hashlib import sha256
from io import BytesIO
import importlib.util, json, os, struct
from elftools.elf.elffile import ELFFile
from capstone import Cs, CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN
H=Path(__file__).resolve().parent; B=H.parent
reader=B/'stage2/extraction/read_filesystems.py'
assert sha256(reader.read_bytes()).hexdigest()=='eecbe9b099f9fbc8f8e06759c5e8a2ce9910e0f365ae9891fe0887353edc31ad'
spec=importlib.util.spec_from_file_location('fx3_saved_ext2_reader',reader); m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
image=B/'stage2/extraction/nflasha15.img';fs=m.Ext2(image)
assert sha256(fs.b).hexdigest()=='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5'
inv=list(fs.walk()); capture=[]; data={}
selected=['/lib/libObj.so','/lib/libosal_uipc.so','/kmod/osal_uipc.ko','/bin/up.sh','/bin/ud_send_lsi.elf']
selected += [r['path'] for r in inv if r['path'].endswith('/us_remove_modes.sh') and r['type']==0o100000]
assert len(selected)==6
for name in selected:
    row=[r for r in inv if r['path']==name and r['type']==0o100000];assert len(row)==1
    raw=fs.data(row[0]['inode']); data[name]=raw
    p=H/'originals/7.02-main'/name.lstrip('/');p.parent.mkdir(parents=True,exist_ok=True)
    with os.fdopen(os.open(p,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as f:f.write(raw)
    capture.append(dict(path_in_fs=name,path=str(p),bytes=len(raw),sha256=sha256(raw).hexdigest()))
fs.b.close();fs.f.close()
assert sha256(data['/lib/libObj.so']).hexdigest()=='c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae'
def put(n,v):
    with (H/n).open('x') as f:json.dump(v,f,ensure_ascii=False,indent=2);f.write('\n')
put('current-main-capture.json',dict(source_image=str(image),source_image_sha256='df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5',captures=capture,
    current_body_p1_read=False,original_or_guest_execution=False,root_or_device_operations=0))
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.skipdata=True
selected_ranges=[]
def pin(name,a,z,label,section=None):
    raw=data[name];e=ELFFile(BytesIO(raw));note={};rm={}
    if section:
        sec=e.get_section_by_name(section);part=sec.data()[a:z];kind='section_offset'
        rs=e.get_section_by_name('.rela'+section)
        if rs:
            st=e.get_section(rs['sh_link']);rm={r['r_offset']:{'symbol':st.get_symbol(r['r_info_sym']).name,'addend':r['r_addend'],'type':r['r_info_type']} for r in rs.iter_relocations()}
    else:
        seg=[s for s in e.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and z<=s['p_vaddr']+s['p_filesz']];assert len(seg)==1
        off=seg[0]['p_offset']+a-seg[0]['p_vaddr'];part=raw[off:off+z-a];kind='ELF_VA'
        rs=e.get_section_by_name('.rela.plt');plt=e.get_section_by_name('.plt')
        if rs and plt:
            st=e.get_section(rs['sh_link']);note={plt['sh_addr']+32+16*n:st.get_symbol(r['r_info_sym']).name for n,r in enumerate(rs.iter_relocations())}
    assert len(part)==z-a
    ins=list(md.disasm(part,a));assert sum(i.size for i in ins)==len(part)
    lines=[]
    for i in ins:
        extra=''
        if i.mnemonic in ['b','bl'] and i.op_str.startswith('#'):
            target=int(i.op_str[1:],16)
            if target in note:extra=' ; '+note[target]
        if i.address in rm:extra+=' ; relocation '+str(rm[i.address])
        lines.append(f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}{extra}')
    out=H/(label+'.txt');out.write_text('\n'.join(lines)+'\n')
    selected_ranges.append(dict(source=name,source_sha256=sha256(raw).hexdigest(),address_kind=kind,section=section,start=hex(a),end_exclusive=hex(z),bytes=len(part),sha256=sha256(part).hexdigest(),disassembly=out.name))
    return part
pin('/lib/libObj.so',0xee0b0,0xee1a4,'current-registration')
pin('/lib/libObj.so',0xed990,0xedae0,'current-business-callback')
pin('/lib/libObj.so',0xed8cc,0xed940,'current-remove-wrapper')
pin('/lib/libObj.so',0xed940,0xed990,'current-create-flag')
pin('/lib/libObj.so',0xee1a4,0xee238,'current-unregister')
pin('/lib/libosal_uipc.so',0x32cc,0x3340,'current-user-dispatch')
pin('/kmod/osal_uipc.ko',0x4ae0,0x4c7c,'current-kernel-registration','.text')
pin('/kmod/osal_uipc.ko',0x3bf8,0x3e00,'current-kernel-send','.text')
e=ELFFile(BytesIO(data['/bin/ud_send_lsi.elf']));text=e.get_section_by_name('.text')
# Select full helper text as a bounded locator and pin the established send/reply range separately.
pin('/bin/ud_send_lsi.elf',0x400a38,0x400adc,'current-helper-reply')
raw=data['/lib/libObj.so'];e=ELFFile(BytesIO(raw))
def va(a,n):
    for s in e.iter_segments():
        if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']:
            off=s['p_offset']+a-s['p_vaddr'];return raw[off:off+n]
    raise ValueError('unbacked VA')
strings={hex(a):va(a,160).split(b'\0')[0].decode() for a in [0x1dd733,0x1dd797,0x1dd7ae,0x1dd7c5,0x1dd81e]}
st=e.get_section_by_name('.dynsym');rs=e.get_section_by_name('.rela.plt');plt=e.get_section_by_name('.plt')
names={plt['sh_addr']+32+16*n:st.get_symbol(r['r_info_sym']).name for n,r in enumerate(rs.iter_relocations())}
assert names[0x57c50]=='osal_reg_msg_queue_cb' and names[0x55c10]=='open'
assert va(0xee16c,4)==bytes.fromhex('c36e80d2') and va(0xee174,4)==bytes.fromhex('6309a0f2')
assert va(0xee17c,4)==bytes.fromhex('42402691') and va(0xee188,4)==bytes.fromhex('b2a6fd97')
assert va(0xed944,4)==bytes.fromhex('82248052') and va(0xed948,4)==bytes.fromhex('41088052')
init=[s for s in st.iter_symbols() if s.name=='udtr_senser_init'];assert len(init)==1 and init[0]['st_value']==0xee0b0
text=e.get_section_by_name('.text');direct_refs=[]
for off in range(0,len(text.data())-3,4):
    w=struct.unpack_from('<I',text.data(),off)[0]
    if w&0x7c000000!=0x14000000:continue
    d=w&0x3ffffff;d=d-(1<<26) if d&(1<<25) else d
    a=text['sh_addr']+off;dest=a+4*d
    if dest in [0xee0b0,0xed990]:direct_refs.append(dict(at=hex(a),target=hex(dest)))
put('queue-endpoint-proof.json',dict(
    source='official7.02 main AP image, not measured runtime',selected_original_ranges=selected_ranges,strings=strings,
    registration=dict(export='udtr_senser_init',entry='0xee0b0',call='0xee188',api=names[0x57c50],id='0x004b0376',callback='0xed990',context='0x004b0376',handle_address='0x2ce198',
        conditions=['nonzero service-registration result saved at a GOT-referenced global','Backup_read(0x004b0000) returns positive','first setting byte is1 or2'],actual_runtime_registration_observed=False),
    queue_identity=dict(sender_id='0x804b0376',registration_id='0x004b0376',low16='0x0376',kernel_send_takes_low16=True,kernel_registration_takes_low16=True,hardware_execution_observed=False),
    callback_effects=dict(first_remove_command=strings['0x1dd733'],flag_open_flags='0x42',flag_open_mode='0x124',
        accepted_normal_paths={'0':[],'2':['mode'],'3':['mode','mode3'],'4':['mode','mode1'],'6':['mode','mode6']},
        other_command_path='after successful remove wrapper: prints command error, frees incoming message; does not allocate reply',
        reply='allocates4B reply, no payload store in this callback before send to original source id',
        direct_restart_or_AP_partition_load_call_in_selected_callback=False),
    helper_reply_limit='selected source accepts receive result0 or -1022 without checking a reply command/body; not proof of completed boot or accepted mode',
    direct_text_refs=direct_refs,limitations=['selected ordinary call paths only; dynamic registration timing, stm_system behavior, filesystem writes and cold boot not executed',
        'callback uses libObj/im runtime, not independently established when im or main AP is unavailable','historical p1 providers are separate reference versions, not current installed p1'],
    original_or_guest_execution=False,root_or_device_operations=0))
print(json.dumps(dict(registration_api=names[0x57c50],callback='0xed990',original_slices=len(selected_ranges),strings=strings,direct_refs=direct_refs),ensure_ascii=False))
