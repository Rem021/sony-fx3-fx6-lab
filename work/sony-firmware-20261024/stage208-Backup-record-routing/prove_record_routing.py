"""Prove static Backup command/record routing using original section bytes/relocations.

No ELF loading, relocations, Sony instructions, devices or guest runtime executed.
"""
from pathlib import Path
from io import BytesIO
from hashlib import sha256
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
import json,struct
H=Path(__file__).resolve().parent;R=H.parents[2];B=H.parent
cap=json.loads((H/'source-capture.json').read_text());rows={r['image_path']:r for r in cap['files']}
def original(path):
 row=rows[path];raw=(R/row['output']).read_bytes();assert len(raw)==row['bytes'] and sha256(raw).hexdigest()==row['sha256'];return raw,ELFFile(BytesIO(raw))
raw,e=original('/kmod/backup.ko');txt=e.get_section_by_name('.text').data();ro=e.get_section_by_name('.rodata').data();secidx=next(i for i,s in enumerate(e.iter_sections()) if s.name=='.text')
rel={}
for s in e.iter_sections():
 if s['sh_type']=='SHT_RELA' and s['sh_info']==secidx:
  sy=e.get_section(s['sh_link'])
  for r in s.iter_relocations():
   q=sy.get_symbol(r['r_info_sym']);sn=q['st_shndx'];name=q.name or (e.get_section(sn).name if isinstance(sn,int) else str(sn))
   rel[r['r_offset']]=dict(type=r['r_info_type'],symbol=name,value=q['st_value'],section=sn,addend=r['r_addend'])
w=lambda a:int.from_bytes(txt[a:a+4],'little')
def call(a,name):assert w(a)==0x94000000 and rel[a]['type']==283 and rel[a]['symbol']==name
# Registration and callback, followed by command4's halfword switch entry.
assert w(0x7920)==0xd28029a3 and w(0x7924)==0xf2a007c3
call(0x7934,'osal_reg_sync_msg_queue_cb');assert rel[0x79d0]['symbol']=='.text' and rel[0x79d0]['addend']==0x74e8
call(0x74f0,'backup_osal_call_func')
assert w(0x7ac4)==0x11000680 and w(0x7ac8)==0x7100e01f
assert rel[0x7fc8]['symbol']=='.rodata' and rel[0x7fc8]['addend']==0xa8
entry=struct.unpack_from('<h',ro,0xa8+(4+1)*2)[0];assert 0x7b1c+entry*4==0x7f58
call(0x7f60,'Backup_read_4Byte');assert w(0x7f64)==0xb9000660
# Ordinary read uses local Data helpers, all referencing the same .bss+0x28.
for a,name in [(0x1f54,'Data_SearchId'),(0x1f60,'Data_GetSize'),(0x1f94,'Data_GetDataPt')]:call(a,name)
assert w(0x1f68)==0x7100101f and w(0x1f98)==0xb9400014
for a in [0x4dd8,0x4f58,0x53a0,0x57e8]:assert rel[a]['symbol']=='.bss' and rel[a]['addend']==0x28
assert w(0x4d6c)==0xf90000c0 and w(0x4dbc)==0xa90084c2
assert w(0x4dac)==0x91040002 and w(0x4db8)==0x9ba30821
# File init's base pointer is not shifted to record1 before Data_init.
for a,name in [(0x6570,'backupfile_load_file'),(0x6590,'arch_p32_to_p64'),(0x6594,'arch_phys_to_cache'),(0x65b4,'Data_init')]:call(a,name)
assert w(0x658c)==0xb9400280 and w(0x6598)==0xaa0003f3 and w(0x65b0)==0xaa1303e0
assert w(0x65a8)==0x710006bf and w(0x65e8)==0xaa1303e2
call(0x65f4,'backupfile_load_file')
# CP transfer explicitly selects index1; actual source functions walk to the
# next4KiB-aligned record using header dataOffset+dataSize, not a fixed offset.
for a,name in [(0x7040,'Data_GetHeader'),(0x7048,'Data_getAdrs'),(0x7064,'Data_GetHeader'),(0x706c,'Data_getSize')]:call(a,name)
assert w(0x7044)==w(0x7068)==0x52800021
assert w(0x59a0)==w(0x5a00)==0x29430400 and w(0x59a4)==0x8b010000
assert w(0x59a8)==w(0x5a08)==0x913ffc00 and w(0x59ac)==w(0x5a0c)==0x9274cc00
assert w(0x59b0)==w(0x5a10)==0x8b0000a5
assert w(0x598c)==0x34000281 and w(0x59dc)==0xaa0503e0
call(0x59b8,'Data_GetFormatRevision');call(0x5a18,'Data_GetFormatRevision');call(0x70bc,'pcidma_transfer_async')
# This actual small callee does not overwrite x5, which holds the selected base.
md=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);md.detail=True
for i in md.disasm(txt[0x4c80:0x4d3c],0x4c80):
 reads,writes=i.regs_access();assert not any(i.reg_name(r) in ['x5','w5'] for r in writes)
# Userspace wrapper supplies command4 and one argument (not length4).
lraw,le=original('/lib/libbackup.so')
def lr(a,n):
 s=next(s for s in le.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=a and a+n<=s['p_vaddr']+s['p_filesz']);at=s['p_offset']+a-s['p_vaddr'];return lraw[at:at+n]
lw=lambda a:int.from_bytes(lr(a,4),'little')
assert lw(0x1e1c)==0x528029a1 and lw(0x1e30)==0x72a007c1 and lw(0x1e2c)==0x52800082 and lw(0x1e20)==0x52800023
assert lw(0x1a58)==0x2a0203f7 and lw(0x1ab0)==0x29007e77
pl=le.get_section_by_name('.plt')['sh_addr'];rs=le.get_section_by_name('.rela.plt');ss=le.get_section(rs['sh_link']);imports={pl+32+16*n:ss.get_symbol(x['r_info_sym']).name for n,x in enumerate(rs.iter_relocations())}
assert imports[0x1530]=='backup_sync_msg' and imports[0x15d0]=='osal_snd_sync_msg'
# Evaluate only the source-derived record-offset formula against11real
# default files; no firmware instructions are run.
previous=json.loads((B/'stage207-Backup-template-and-GPIO-config/template-field-results.json').read_text());checks=[]
for t in previous['templates']:
 d=(R/t['source_path']).read_bytes();assert sha256(d).hexdigest()==t['source_sha256'];start,size=struct.unpack_from('<II',d,24);next_record=(start+size+0xfff)&~0xfff
 assert next_record==t['records'][1]['offset']==0xd2000 and d[next_record+12:next_record+16]==b'BK4\0'
 assert [[r['value_u32'] for r in rec['selected_properties']] for rec in t['records']]==[[0,4,2],[5,4,30]]
 checks.append(dict(template=t['name'],local_record_offset=0,CP_record_offset=next_record))
# Keep exact code and data ranges separate. Existing locators may display
# literal words as UDF; those are not claimed to be executed instructions.
ranges=[];outdir=H/'pins';outdir.mkdir()
def pin(section,a,z,label,kind='code',source_raw=raw,source_e=e,path='/kmod/backup.ko'):
 s=source_e.get_section_by_name(section);part=s.data()[a:z] if source_e['e_type']=='ET_REL' else lr(a,z-a)
 assert len(part)==z-a
 lines=[part.hex()] if kind=='data' else [f'{i.address:08x} {i.bytes.hex()} {i.mnemonic:8} {i.op_str}' for i in md.disasm(part,a)]
 p=outdir/(label+'.txt');p.open('x').write('\n'.join(lines)+'\n')
 ranges.append(dict(source=rows[path]['output'],source_sha256=sha256(source_raw).hexdigest(),section=section,offset=a,bytes=z-a,kind=kind,sha256=sha256(part).hexdigest(),output=str(p.relative_to(R))))
for a,z,label,kind in [(0x74e8,0x74fc,'sync-receiver','code'),(0x4dd8,0x4de8,'local-init-literals','data'),(0x4f58,0x4f60,'local-search-literal','data'),(0x53a0,0x53a8,'local-value-literal','data'),(0x57e8,0x57f0,'local-header-literal','data'),(0x79d0,0x79f0,'registered-callback-literals','data'),(0x4c80,0x4d3c,'format-revision-callee','code'),(0x4d40,0x4d58,'format-name-literals','data')]:pin('.text',a,z,label,kind)
pin('.rodata',0xa8,0xa8+114,'dispatch-switch-table','data')
pin('.text',0x1a10,0x1b6c,'userspace-sync-builder','code',lraw,le,'/lib/libbackup.so')
pin('.text',0x1e14,0x1e4c,'userspace-ordinary-read4','code',lraw,le,'/lib/libbackup.so')
result=dict(status='OFFICIAL_MAIN_LOCAL_RECORD0_AND_CP_RECORD1_STATIC_ROUTES_BOUND',
 source_module_sha256=sha256(raw).hexdigest(),source_library_sha256=sha256(lraw).hexdigest(),queue='0x003e014d',operation_selector=4,argument_count=1,
 operation_selector_is_not_length=True,receiver_callback_offset='0x74e8',dispatch_table=dict(section='.rodata',offset='0xa8',index=5,signed_halfword=entry,destination='0x7f58',call='Backup_read_4Byte@.text+0x7f60'),
 local_record=dict(Data_init_stores_unshifted_record_base=True,shared_state_relocation='.bss+0x28',Data_init='0x4d60',Data_SearchId='0x4ef8',Data_GetDataPt='0x5350'),
 CP_record=dict(caller='backupfile_get_cp_data',index=1,formula='align_up(header.dataOffset + header.dataSize,4096)',transport='pcidma_transfer_async'),
 template_layout_checks=checks,classic_public_AP_defaults=dict(SIO=0,GPIO_portid=4,GPIO_bitnum=2),classic_public_CP_defaults=dict(SIO=5,GPIO_portid=4,GPIO_bitnum=30),
 extra_source_ranges=ranges,relocations_are_static_evidence_only=True,actual_body_Backup_read=False,current_body_driver_provider_attested=False,
 actual_AP_current_settings_or_recovery_execution_proven=False,Sony_code_or_guest_execution=False,root_or_device_operations=0,
 limits=['AP/CP default record roles now source-bound, but runtime Backup bytes were not acquired','Main7.02 package provider is not an installed same-body p1 fingerprint','Static defaults do not prove board pin state, UART/SIO transport, clock, MCU state, independent AP entry or restore'])
(H/'record-routing-proof.json').open('x').write(json.dumps(result,indent=2)+'\n')
(H/'FX3-default-profile-candidate.json').open('x').write(json.dumps(dict(model='classic ILME-FX3',firmware_package='7.02',profile_scope='public AP defaults only',SIO_channel=0,GPIO_portid=4,GPIO_bitnum=2,GPIO_open_mode=2,
 source='record-routing-proof.json',runtime_verified=False,executable_payload=False,device_operation_authorized=False,independent_restore_proven=False),indent=2)+'\n')
print(json.dumps(dict(local_default_record=0,CP_default_record=1,AP_default_SIO_port_bit=[0,4,2],template_layouts=len(checks),new_pinned_ranges=len(ranges),operation4_is_not_length=True,device_operations=0)))
