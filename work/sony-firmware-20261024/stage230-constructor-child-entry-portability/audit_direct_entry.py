"""Static distinction between direct dlopen and scripted Jiritsu loading."""
from pathlib import Path
from hashlib import sha256
import ast,io,json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/originals/lib/libJiritsu.so';raw=P.read_bytes();assert sha256(raw).hexdigest()=='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
e=ELFFile(io.BytesIO(raw));dyn=e.get_section_by_name('.dynsym');symbols={s.name:s for s in dyn.iter_symbols()};md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def read(va,n):
 for s in e.iter_segments():
  if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']:
   at=s['p_offset']+va-s['p_vaddr'];return raw[at:at+n]
 raise ValueError((va,n))
def word(pc):return struct.unpack('<I',read(pc,4))[0]
def branch(pc):
 w=word(pc);assert w&0x7c000000==0x14000000;imm=w&0x3ffffff
 if imm&(1<<25):imm-=1<<26
 return pc+imm*4
base=e.get_section_by_name('.plt')['sh_addr'];plt={base+32+i*16:dyn.get_symbol(r['r_info_sym']).name for i,r in enumerate(e.get_section_by_name('.rela.plt').iter_relocations())}
functions=[];insns={}
for name in ['adj_cmd_set_file','adj_cmd_set_file2','_ZN10IM_JIRITSU10CImJiritsu10jit_threadEPv']:
 s=symbols[name];data=read(s['st_value'],s['st_size']);ins=list(md.disasm(data,s['st_value']));assert len(ins)*4==len(data)
 rows=[]
 for i in ins:
  target=branch(i.address) if i.mnemonic in ('b','bl') else None
  if target is not None:assert target==int(i.op_str[1:],16)
  row=dict(pc=i.address,raw=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str,target=target,PLT=plt.get(target));rows.append(row);insns[i.address]=row
 functions.append(dict(name=name,VA=s['st_value'],bytes=len(data),sha256=sha256(data).hexdigest(),original_hex=data.hex(),instructions=rows))
checks=[]
for pc,name in [(0x8e40,'open'),(0x8e9c,'write'),(0x8ea8,'fsync'),(0x8eb0,'close'),(0x8ef0,'strcmp'),(0x8f1c,'dlopen'),(0x8f60,'dlclose'),(0x95bc,'sys_mount'),(0x9600,'get_access_filename'),(0x9820,'_ZN11CFileAccess4openEPKci'),(0x9898,'_ZN11CFileAccess5writeEPKvm'),(0x98a4,'_ZN11CFileAccess5fsyncEv'),(0x98ac,'_ZN11CFileAccess5closeEv'),(0x98e0,'strcmp'),(0x9908,'dlopen'),(0x9928,'dlclose')]:
 assert plt[branch(pc)]==name,(hex(pc),plt[branch(pc)],name);checks.append(dict(pc=hex(pc),target=hex(branch(pc)),symbol=name,raw=read(pc,4).hex()))
for f in functions[:2]:assert all(i['PLT']!='dlsym' for i in f['instructions'])
assert insns[0x8f18]['asm']=='mov w1, #1' and insns[0x9904]['asm']=='mov w1, #1'
assert insns[0x8f20]['asm']=='cbnz x0, #0x8f60' and insns[0x990c]['asm']=='cbnz x0, #0x9928'
assert insns[0x8e3c]['asm']=='mov w1, #0x241' and insns[0x981c]['asm']=='mov w2, #0x241'
literal=read(0x31203,64).split(b'\0')[0].decode();assert literal=='/tmp/jiritsu/libJit.so'
assert insns[0x9558]['asm']=='mov x26, x1' and insns[0x9574]['asm']=='ldrb w0, [x21, #0x28]'
assert insns[0x958c]['asm']=='b.eq #0x9608' and insns[0x962c]['asm']=='cmp w20, #0x500, lsl #12'
assert insns[0x9628]['asm']=='ldrb w25, [x21, #0x2a]' and insns[0x9630]['asm']=='ccmp w25, #0x11, #0, ls'
assert insns[0x95a8]['asm']=='b.eq #0x9590' and insns[0x9590]['asm']=='mov w19, #0'
for name in ['source-capture.json','payload-source-capture.json']:
 for row in json.loads((H/name).read_text()):
  assert row['returncode']==0;p=H/row['output'];assert sha256(p.read_bytes()).hexdigest()==row['sha256'] and p.stat().st_size==row['bytes']
cpath=H/'reference/chocotan--report--2026-10-18-libjit-exec--scripts--payload--libjit_exec.c';c=cpath.read_text();ctor=c[c.index('void _init(void) {'):]
assert 'sc(SYS_UNLINKAT, AT_FDCWD, (i64)SELF_PATH' in ctor and 'sc(SYS_CLONE, SIGCHLD, 0, 0, 0, 0, 0)' in ctor and 'run_child(output_fd)' in ctor
assert '#define SIGCHLD      17' in c and '#define SYS_CLONE    220' in c and '#define SYS_EXECVE   221' in c
assert 'sc(SYS_EXECVE, (i64)SHELL_PATH' in c and 'SYS_WAIT' not in c and 'wait4(' not in c and 'waitpid(' not in c
req=H/'reference/chocotan--report--2026-10-18-libjit-exec--scripts--libjit_requests.py';tree=ast.parse(req.read_text());caps={n.targets[0].id:n.value.value for n in tree.body if isinstance(n,ast.Assign) and len(n.targets)==1 and isinstance(n.targets[0],ast.Name) and isinstance(n.value,ast.Constant) and n.targets[0].id in ['MAX_UPLOAD','MAX_PAYLOAD']};assert caps=={'MAX_UPLOAD':0x500000,'MAX_PAYLOAD':0x40000}
glibc=H/'reference/glibc-2.25-dl-init.c';g=glibc.read_text();assert 'DL_CALL_DT_INIT' in g and '((init_t) addrs[j]) (argc, argv, env);' in g
assert g.index('DL_CALL_DT_INIT')<g.index('((init_t) addrs[j]) (argc, argv, env);')
ref=B/'stage133-FX5-source-availability-and-portability/fx3-gpl-reference/linux-kernel/arch/arm64/configs/cxd90057_set_defconfig';config=ref.read_text();assert 'CONFIG_ARM64_PAGE_SHIFT=12' in config and 'CONFIG_ARM64_4K_PAGES=y' in config
old=B/'stage227-zero-arg-bootstrap-and-keeper-handoff';source=(old/'bootstrap.c').read_text();assert 'static void fx3_module_init(void){initialized=0x465833424f4f5431ULL;}' in source
module=old/'runs-final/built/parent-module.so';assert module.stat().st_size==262936 and sha256(module.read_bytes()).hexdigest()=='96939f5ac7cfb64da3866c710cf511e13515f806415a9ab37beab80c1d3940eb'
report=dict(schema='fx3-stage230-direct-constructor-entry-portability-v1',source=dict(path=str(P.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()),functions=functions,manual_call_checks=checks,direct_load=dict(path=literal,flags=1,old_set_file_dlopen='0x8f1c',old_set_file_dlclose='0x8f60',set_file2_dlopen='0x9908',set_file2_dlclose='0x9928',neither_full_setter_has_direct_dlsym=True,full_script_interface_needed_for_constructor_code=False,full_script_interface_needed_for_separate_jit_thread_route=True,constructor_long_work_blocks_request=True,constructor_must_not_exit_calling_service=True,actual_FX3_service_upload_or_loader_execution_verified=False),
 distinction=dict(stage229_lifecycle_audit_remains_correct_for_script_thread=True,stage229_full_interface_is_not_universal_loading_prerequisite=True,existing227_constructor_only_memory_mark=True,current227_step_status_exports_called_by_direct_setter=False,current227_requires_major_constructor_activation_completion_and_context_adaptation=True,prior_candidate_now_flashable=False),
 public_source=dict(chocotan_commit='2f66a0cd9732dd7900582e0213b5adb7761c4d1e',FireHydrant_commit='f4e328425386bb1578cc5651f44dea0fa9685cf5',constructor_raw_clone_flags=17,no_CLONE_VM=True,child_execs_dynamic_shell=True,parent_never_waits=True,shell_echo_nonce_status_is_kernel_exit_or_descendant_completion=False,public_self_unlink_and_named_cleanup_before_full_checks_not_adopted=True,public_source_compiled_imported_or_executed=False),
 transfer_limits=dict(A7CII_tool_declares_MAX_UPLOAD=caps['MAX_UPLOAD'],A7CII_tool_declares_MAX_PAYLOAD=caps['MAX_PAYLOAD'],A6700_document_declares_single_upload=65536,FX3_5MiB_compare_is_action_ff_cache_branch_not_proven_general_file_write_cap=True,FX3_full_transfer_alloc_and_length_bounds_verified=False,module227_bytes=module.stat().st_size,module227_exceeds_A7CII_tool_payload_cap=True,copying_foreign_host_limit_or_offsets_is_validated=False),
 kernel_page_reference=dict(path=str(ref.relative_to(R)),sha256=sha256(ref.read_bytes()).hexdigest(),page_shift=12,reference_only_not_current_body_kernel_measurement=True),
 next_architecture='Use explicitly bounded constructor activation and return promptly from direct dlopen/dlclose. Child must survive parent unmap without CLONE_VM, perform only fixed authorized work, and provide private completion plus independent exit observation. Do not adopt generic shell, unverified self-delete, public echo as exit proof or weaken owner/image/request guards. A zero-signal no-exec observer is only a future hypothesis; exec resets SIGCHLD and existing reaper problem remains.',
 source_only=True,original_Sony_glibc_Linux_or_upstream_program_executed=False,new_camera_admin_or_USB_operations=0,first_flash_released=False)
(H/'direct-entry-audit.json').open('x').write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='DIRECT_SETTER_CONSTRUCTOR_ROUTE_DISTINGUISHED_FROM_SCRIPT_INTERFACE',complete_functions=3,manual_calls=len(checks),real_FX3_execution=False)))
