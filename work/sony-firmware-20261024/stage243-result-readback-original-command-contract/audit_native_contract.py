"""Re-read saved official ELF and audit instructions/tables; no emulation."""
from pathlib import Path
from hashlib import sha256
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
import ast,io,json,struct
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
record=json.loads((H/'original-functions.json').read_text());source=R/record['source'];raw=source.read_bytes()
assert sha256(raw).hexdigest()==record['sha256']=='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
elf=ELFFile(io.BytesIO(raw));sy=elf.get_section_by_name('.dynsym');symbols={s.name:s for s in sy.iter_symbols()};md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
base=elf.get_section_by_name('.plt')['sh_addr'];plt={base+32+16*i:sy.get_symbol(x['r_info_sym']).name for i,x in enumerate(elf.get_section_by_name('.rela.plt').iter_relocations())}
def read(va,n):
 s=next(s for s in elf.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']);at=s['p_offset']+va-s['p_vaddr'];return raw[at:at+n]
functions=record['functions']+[json.loads((H/'original-path-selector.json').read_text())]+json.loads((H/'original-dispatch-functions.json').read_text())
for f in functions:
 s=symbols[f['name']];assert (s['st_value'],s['st_size'])==(f['VA'],f['bytes'])
 data=read(f['VA'],f['bytes']);assert sha256(data).hexdigest()==f['sha256'] and len(f['instructions'])*4==len(data)
 for i,row in enumerate(f['instructions']):assert row['pc']==f['VA']+i*4 and bytes.fromhex(row['word'])==data[i*4:i*4+4]
checks=[]
def check(pc,*,asm=None,call=None):
 data=read(pc,4);i=next(md.disasm(data,pc));text=i.mnemonic+' '+i.op_str
 if asm is not None:assert text==asm,(hex(pc),text,asm)
 if call is not None:
  assert i.mnemonic=='bl';target=int(i.op_str[1:],16);assert plt[target]==call,(hex(pc),plt.get(target),call)
 checks.append(dict(pc=pc,word=data.hex(),asm=text,PLT=call))
for pc,text in [
 (0x89d4,'cmp w0, #0x1ff'),(0x89d8,'b.ls #0x89f8'),(0x8a20,'cbnz w0, #0x89f0'),
 (0x8a48,'str x0, [x19, #0x7c8]'),(0x8a78,'cmp w0, #0x5c'),(0x8a80,'strb w5, [x3, x1]'),
 (0x8a8c,'cmp w2, #0x2c'),(0x935c,'ldr x21, [x0, #0x7c8]'),(0x9380,'cbz w0, #0x93b8'),
 (0x9ed8,'ldrb w1, [x19, #0x28]'),(0x9ee0,'b.eq #0x9f30'),(0x9ee8,'cmp w1, #0xff'),
 (0x9f4c,'ldrb w0, [x19, #0x2a]'),(0x9f58,'ldrb w0, [x19, #0x29]'),
 (0xa030,'cmp w0, #0x300'),(0xa034,'b.ne #0xa0e4'),(0xa124,'ldr x23, [x29, #0x12c8]'),
 (0xa174,'mov w2, #0'),(0xa200,'cmp w23, w24'),(0xa228,'b.eq #0xa240'),
 (0x9fdc,'str w0, [x20]'),(0x9fec,'str xzr, [x19, #0x7c8]'),(0xa000,'mov w0, #0'),
 (0x990c,'cbnz x0, #0x9928'),(0x992c,'b #0x96dc'),(0x96dc,'mov w20, #0'),
 (0x96f8,'str w20, [x21, #0x1c]'),(0x9700,'mov w0, w19'),
 (0xeb80,'cbnz w0, #0xecd4'),(0xecf4,'mov w1, w20'),(0xfb0c,'cbnz w0, #0xfc7c'),
 (0xb144,'sub w0, w0, #8'),(0xb148,'cmp w0, #9'),(0xb15c,'adr x1, #0xb168'),
 (0xac2c,'sub w0, w0, #6'),(0xac30,'cmp w0, #0xa'),(0xac44,'adr x1, #0xac50')]:check(pc,asm=text)
for pc,name in [(0x9378,'strncmp'),(0x93c8,'snprintf'),(0x9f18,'sys_mount'),(0x9f64,'get_access_filename'),
 (0xa0ec,'_ZN11CFileAccess4statEPKcP13tag_FILE_INFO'),(0xa14c,'_ZN6DmmMgr9dmm_allocEj'),
 (0xa178,'_ZN11CFileAccess4openEPKci'),(0xa1d8,'_ZN11CFileAccess4readEPvm'),
 (0xa1f4,'_ZN11CFileAccess5fsyncEv'),(0xa1fc,'_ZN11CFileAccess5closeEv'),(0x9fe8,'free'),
 (0x9ff4,'_ZN11CFileAccess5closeEv'),(0x9908,'dlopen'),(0x9928,'dlclose'),
 (0x96fc,'_ZN11CFileAccess5closeEv'),(0xed00,'open'),(0xacb4,'adj_cmd_set_file_path'),
 (0xacc4,'adj_cmd_set_file2'),(0xb20c,'adj_cmd_get_file2')]:check(pc,call=name)
strings=[]
for va,value in [(0x30e17,b'/tmp/jiritsu'),(0x30e29,b'/dev/nflasha6'),(0x31375,b'/mnt'),
 (0x11dd7,b'%s'),(0x11d7e,b'%s/%s'),(0x327e6,b'%s%s')]:
 assert read(va,len(value)+1)==value+b'\0';strings.append(dict(VA=va,value=value.decode(),bytes=read(va,len(value)+1).hex()))
tables=[]
for va,count,first,target_base in [(0x11b14,11,6,0xac50),(0x11b20,10,8,0xb168)]:
 data=read(va,count);rows=[dict(command=first+i,signed_index=v if v<128 else v-256,target=target_base+4*(v if v<128 else v-256)) for i,v in enumerate(data)]
 tables.append(dict(VA=va,bytes=data.hex(),sha256=sha256(data).hexdigest(),rows=rows))
send={r['command']:r['target'] for r in tables[0]['rows']};get={r['command']:r['target'] for r in tables[1]['rows']}
assert send[15]==0xacac and send[16]==0xacbc and get[17]==0xb1f8
from result_protocol import SELECTED_RESULT,RAM_RESULT
mask=(0x1000<<32)|0x2400;rejected=[v for v in range(45) if mask>>v&1];assert rejected==[10,13,44]
assert len(SELECTED_RESULT.encode())+2<=513 and SELECTED_RESULT.startswith('/tmp/jiritsu/')
assert all(v not in rejected for v in SELECTED_RESULT.encode()) and '\\' not in SELECTED_RESULT
reference=B/'stage230-constructor-child-entry-portability/reference/chocotan--report--2026-10-18-libjit-exec--scripts--libjit_requests.py'
tree=ast.parse(reference.read_text());literals={n.targets[0].id:n.value.value for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant)}
assert {n:literals[n] for n in ['CATEGORY','CMD_SELECT','CMD_READ']}==dict(CATEGORY=0x1001,CMD_SELECT=15,CMD_READ=17)
report=dict(status='STATIC_RESULT_READ_ROUTE_WITH_MOUNT_SHARED_PATH_AND_UNCHECKED_RETURNS_NOT_RELEASED',
 original_source=record['source'],original_source_sha256=record['sha256'],complete_functions=len(functions),
 instruction_checks=len(checks),checks=checks,literal_checks=strings,jump_tables=tables,
 own_fixed_candidate_path=SELECTED_RESULT,proposed_resolved_RAM_target=RAM_RESULT,
 dot_components_accepted_by_checked_character_filter_but_actual_mount_namespace_resolution_unverified=True,
 operation0_selectorFF_mode0_distinct_from_operationFF_cache=True,
 operation0_calls_mount_helper_before_file_access=True,operation1_media_mount_not_selected_by_candidate=True,
 specific_selector3_pending_log_flush_not_selected_but_other_logging_and_auth_side_effects_not_excluded=True,
 file_size_is_whole_file_DMM_allocation_not_host_limited_device_allocation=True,
 normal_mode0_native_body_is_4byte_status_plus_file_bytes=True,
 getter_fsync_close_and_setter_dlclose_returns_not_checked_by_native_business_status=True,
 setter_zero_status_does_not_describe_our_constructor_state=True,
 selected_path_cell=0x467c8,path_selection_and_read_are_separate_and_GET_frees_shared_cell=True,
 native_category_registration_DMM_session_actual_auth_selected_path_exclusivity_and_wire_reply_unverified=True,
 public_inner_envelope_reference=dict(path=str(reference.relative_to(R)),sha256=sha256(reference.read_bytes()).hexdigest(),
 url='https://github.com/chocotan/a7c2-re/blob/2f66a0cd9732dd7900582e0213b5adb7761c4d1e/report/2026-10-18-libjit-exec/scripts/libjit_requests.py',AST_only_not_imported=True),
 original_Sony_or_downloaded_code_executed=False,new_device_USB_cache_admin_auth_upload_or_firmware_operations=0,
 first_flash_released=False)
(H/'native-result-contract.json').open('x').write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status=report['status'],functions=len(functions),instruction_checks=len(checks),table_entries=21)))
