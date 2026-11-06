"""Static ABI/lifecycle audit of saved official bytes. Never executes Sony code."""
from pathlib import Path
from hashlib import sha256
import io,json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;R=H.parents[2];B=H.parent
saved=json.loads((H/'selected-functions.json').read_text());P=(R/Path(saved['source'])).resolve();raw=P.read_bytes()
assert sha256(raw).hexdigest()==saved['source_sha256']=='bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9'
e=ELFFile(io.BytesIO(raw));syms=e.get_section_by_name('.dynsym');byname={s.name:s for s in syms.iter_symbols()};md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
def read(va,n):
 for s in e.iter_segments():
  if s['p_type']=='PT_LOAD' and s['p_vaddr']<=va and va+n<=s['p_vaddr']+s['p_filesz']:
   off=s['p_offset']+va-s['p_vaddr'];return raw[off:off+n]
 raise ValueError((va,n))
def word(pc):return struct.unpack('<I',read(pc,4))[0]
def cs(va):
 data=read(va,256);assert b'\0' in data;return data.split(b'\0')[0].decode()
def branch(pc):
 w=word(pc);assert w&0x7c000000==0x14000000;imm=w&0x3ffffff
 if imm&(1<<25):imm-=1<<26
 return pc+imm*4
def addr(pc,add,reg):
 w=word(pc);assert w&0x9f00001f==0x90000000|reg;imm=(((w>>5)&0x7ffff)<<2)|((w>>29)&3)
 if imm&(1<<20):imm-=1<<21
 w=word(add);assert w&0xffc003ff==0x91000000|(reg<<5)|reg
 return (pc&~4095)+(imm<<12)+((w>>10)&4095)
base=e.get_section_by_name('.plt')['sh_addr'];plt={base+32+i*16:syms.get_symbol(x['r_info_sym']).name for i,x in enumerate(e.get_section_by_name('.rela.plt').iter_relocations())}
for row in saved['functions']:
 s=byname[row['name']];assert s['st_value']==row['VA'] and s['st_size']==row['bytes']
 data=read(row['VA'],row['bytes']);assert data.hex()==row['raw'] and sha256(data).hexdigest()==row['sha256']
 ins=list(md.disasm(data,row['VA']));assert len(ins)*4==len(data) and [dict(pc=i.address,asm=i.mnemonic+' '+i.op_str,PLT=plt.get(int(i.op_str[1:],16)) if i.mnemonic in ('b','bl') and i.op_str.startswith('#') else None) for i in ins]==row['instructions']
checks=[]
for pc,name in [(0xb570,'osal_valloc_msg_wait'),(0xb5a8,'osal_snd_msg'),(0xb65c,'osal_create_waitable_thread'),(0xb730,'osal_wait_thread_exit'),(0xb788,'dlsym'),(0xb7c0,'dlclose'),(0xb7dc,'ramdisk_umount'),(0xb950,'sys_mount'),(0xb9a4,'_ZN10IM_JIRITSU10CImJiritsu7releaseEv'),(0xbab0,'ramdisk_mount'),(0xbadc,'sys_file_copy'),(0xbb04,'dlopen'),(0xbb4c,'dlsym'),(0xbbb4,'dlsym'),(0xbcc4,'fopen'),(0xbe1c,'dlsym'),(0xbe70,'open'),(0xbea8,'unlink'),(0xc0c8,'_ZN10IM_JIRITSU10CImJiritsu3reqEjNS0_11IMJ_REQUESTEPKcS3_S3_j'),(0xc150,'_ZN10IM_JIRITSU10CImJiritsu3reqEjNS0_11IMJ_REQUESTEPKcS3_S3_j'),(0xc1b0,'_ZN10IM_JIRITSU10CImJiritsu3reqEjNS0_11IMJ_REQUESTEPKcS3_S3_j'),(0xc228,'usleep')]:
 assert plt[branch(pc)]==name;checks.append(dict(pc=hex(pc),bytes=read(pc,4).hex(),target=hex(branch(pc)),symbol=name))
symbols=[]
for a,z,reg,name in [(0xbb40,0xbb48,1,'CreateScriptI'),(0xbba8,0xbbb0,1,'LoadScriptI'),(0xbdf4,0xbdfc,1,'RunScriptI'),(0xb780,0xb784,1,'DestroyScriptI')]:
 va=addr(a,z,reg);assert cs(va)==name;symbols.append(dict(adrp=hex(a),add=hex(z),string_VA=hex(va),symbol=name))
assert word(0xbb84)==0xd63f0380 and word(0xbc70)==0xd63f0340 and word(0xbea0)==0xd63f0360 and word(0xb7b4)==0xd63f0280
asm={i['pc']:i['asm'] for row in saved['functions'] for i in row['instructions']}
required={0xb55c:'mov w3, #1',0xb560:'mov w2, #0x20',0xb594:'str w24, [x0]',0xb598:'stp x23, x22, [x0, #8]',0xb5a0:'str x21, [x0, #0x18]',0xbb88:'str x0, [x19, #0x20]',0xbc68:'ldr x0, [x19, #0x20]',0xbc6c:'ldr x1, [x20, #0x10]',0xbc74:'tst w0, #0xff',0xbc88:'ldr x0, [x0, #0x38]',0xbdd8:'mov x2, #0x18f8',0xbe94:'ldr x2, [x20, #0x18]',0xbe98:'mov x1, x26',0xbe9c:'ldr x0, [x19, #0x20]',0xbea4:'mov x0, x21',0xb7b8:'ldr x0, [x19, #0x18]',0xb734:'str xzr, [x19, #0x10]',0xc1a0:'mov w2, #3',0xc1b8:'mov w21, #0x86a0',0xc1bc:'mov w20, #0x1f',0xc1c0:'movk w21, #1, lsl #16',0xc1c8:'cmp w0, #0xa',0xc1d0:'subs w20, w20, #1',0xc1f4:'mov w0, #0x1e',0xc1f8:'str w0, [x19, #8]',0xc040:'str w0, [x19, #8]',0xc058:'ret',0xc0e0:'cmp w0, #0xe',0xc14c:'mov w2, #2'}
for pc,text in required.items():assert asm[pc].strip()==text.strip(),(hex(pc),asm[pc],text)
stop=next(row for row in saved['functions'] if '4stop' in row['name']);assert not any(i['PLT'] in ['osal_wait_thread_exit','dlclose','kill','pthread_cancel'] for i in stop['instructions'])
paths={name:cs(va) for name,va in [('mount_parent',0x30e17),('source_partition',0x30e29),('RAM_target',0x32335),('RAM_options',0x30c8a),('RAM_library',0x31ffe),('script_log',0x3121a),('RAM_filesystem',0x31315)]}
assert paths==dict(mount_parent='/tmp/jiritsu',source_partition='/dev/nflasha6',RAM_target='/tmp/jiritsu/ramdsk_libJit',RAM_options='size=5M',RAM_library='/tmp/jiritsu/ramdsk_libJit/libJit.so',script_log='/tmp/jiritsu/jit.log',RAM_filesystem='tmpfs')
previous=json.loads((B/'stage189-TERM_MODE-consumer/fixed-loader-prefix-results.json').read_text());assert previous['source_sha256']==sha256(raw).hexdigest() and previous['cases'][0]['pending_mount_is_readonly'] is False
report=dict(schema='fx3-stage229-Jiritsu-plugin-lifecycle-static-v1',source=dict(path=str(P.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()),whole_functions_rebound=len(saved['functions']),manual_PLT_checks=checks,independent_ADRP_ADD_symbol_checks=symbols,ABI_instruction_checks=[dict(pc=hex(pc),raw=read(pc,4).hex(),expected_asm=text) for pc,text in required.items()],paths=paths,
 plugin_contract=dict(CreateScriptI='factory return pointer stored in CImJiritsu+0x20; no deliberate semantic argument prepared immediately before call',LoadScriptI='object in x0, queued script pathname pointer in x1; success determined from low8bits',RunScriptI='object x0, zeroed and partially initialized 0x18f8-byte stack context x1, queued parameter pointer x2; return overwritten without checking',DestroyScriptI='object x0; return overwritten, then dlclose',object_error_text_pointer_offset=56,full_object_or_Run_context_layout_recovered=False,bootstrap227_exports_match=False),
 queue_contract=dict(message_bytes=32,operation_offset=0,borrowed_pointer_offsets=[8,16,24],deep_copy_of_queued_strings_in_sender=False,enqueue_success_is_execution_completion=False),
 lifecycle=dict(run_enqueues_load_then_when_state14_enqueues_run=True,run_return_is_script_or_descendant_completion=False,stop_enqueues_operation=3,stop_expected_observed_state=10,stop_counter=31,maximum_requested_sleeps_before_timeout=30,sleep_argument_microseconds=100000,nominal_requested_sleep_seconds=3,observed_real_timeout_seconds=None,stop_timeout_or_enqueue_failure_writes_state=30,stop_has_thread_join_or_kill_or_dlclose=False,state10_store='0xc040',thread_return='0xc058',state10_is_actual_thread_exit_proof=False,exit_calls_wait_thread_exit=True,exit_checks_wait_return_before_clearing_handle=False,original_RunScriptI_executes_synchronously_on_Jiritsu_thread=True,blocked_Run_prevents_same_thread_consuming_stop_until_return=True),
 mount_and_loader=dict(normal_source_parent_flash_mount_precedes_child_tmpfs_copy=True,child_tmpfs_size_MiB=5,existing_plugin_release_called_before_new_copy=True,copy_to_RAM_is_zero_persistent_side_effect_proof=False,actual_mount_or_file_state_observed=False),
 conclusion='Actual factory/script lifecycle differs from bootstrap227. Sender queues borrowed pointers, run only submits work, stop polling/state10 and exit handle-clearing are not independent completion proof. A synchronous blocked plugin can delay the same thread consuming stop. No loader guard relaxed, no plugin generated or uploaded.',
 limitations=['Static ordinary instruction paths only; no actual plugin, OSAL runtime, scheduling or camera execution.','Missing full plugin object/Run context and caller data lifetimes; names alone are insufficient for an adapter.','Other service entrypoints remain outside this bounded route; no universal nonexistence claim.','No independent AP rescue, same-body complete backup, modified update acceptance or MAIN HEVC proof.'],Sony_or_Linux_code_executed=False,new_camera_operations=0,first_flash_released=False)
(H/'plugin-lifecycle-audit.json').open('x').write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='REAL_SCRIPT_ABI_AND_STOP_COMPLETION_GAPS_PINNED',whole_functions=len(saved['functions']),manual_PLT_checks=len(checks),ABI_instruction_checks=len(required),symbol_address_checks=len(symbols),camera_operations=0)))
