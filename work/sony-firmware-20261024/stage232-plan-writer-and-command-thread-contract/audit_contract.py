"""Reproduce static writer and receive-thread facts; never run Sony code."""
from pathlib import Path
from hashlib import sha256
import io,json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
class Image:
 def __init__(self,path,pin):
  self.path=path;self.raw=path.read_bytes();assert sha256(self.raw).hexdigest()==pin
  self.e=ELFFile(io.BytesIO(self.raw));self.dyn=self.e.get_section_by_name('.dynsym');self.syms={s.name:s for s in self.dyn.iter_symbols()};self.md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
  base=self.e.get_section_by_name('.plt')['sh_addr'];self.plt={base+32+i*16:self.dyn.get_symbol(x['r_info_sym']).name for i,x in enumerate(self.e.get_section_by_name('.rela.plt').iter_relocations())};self.rows=[];self.checks=[]
 def read(self,a,n):
  s=next(x for x in self.e.iter_segments() if x['p_type']=='PT_LOAD' and x['p_vaddr']<=a and a+n<=x['p_vaddr']+x['p_filesz']);at=s['p_offset']+a-s['p_vaddr'];return self.raw[at:at+n]
 def function(self,name):
  s=self.syms[name];return self.slice(s['st_value'],s['st_size'],name,'dynamic symbol full function')
 def slice(self,a,n,label,boundary='explicit static slice, not asserted whole function'):
  raw=self.read(a,n);ins=list(self.md.disasm(raw,a));assert len(ins)*4==n
  row=dict(label=label,VA=hex(a),bytes=n,boundary=boundary,sha256=sha256(raw).hexdigest(),original_hex=raw.hex(),instructions=[])
  for i in ins:
   target=None
   if i.mnemonic in ('bl','b') and i.op_str.startswith('#'):
    w=int.from_bytes(i.bytes,'little');assert w&0x7c000000==0x14000000;delta=w&0x3ffffff;delta=delta-(1<<26) if delta&(1<<25) else delta;target=i.address+4*delta;assert target==int(i.op_str[1:],16)
   row['instructions'].append(dict(pc=hex(i.address),raw=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str,target=hex(target) if target is not None else None,PLT=self.plt.get(target)))
  self.rows.append(row);return row
 def asm(self,pc,wanted):
  ins=list(self.md.disasm(self.read(pc,4),pc));assert len(ins)==1 and ins[0].mnemonic+' '+ins[0].op_str==wanted,(hex(pc),ins,wanted)
  self.checks.append(dict(pc=hex(pc),raw=self.read(pc,4).hex(),asm=wanted))
 def call(self,pc,name):
  ins=list(self.md.disasm(self.read(pc,4),pc));assert len(ins)==1 and ins[0].mnemonic=='bl' and self.plt[int(ins[0].op_str[1:],16)]==name
  self.checks.append(dict(pc=hex(pc),raw=self.read(pc,4).hex(),symbol=name,target=ins[0].op_str))
 def string(self,pc,wanted):assert self.read(pc,len(wanted)+1)==wanted.encode()+b'\0'
 def result(self):return dict(path=str(self.path.relative_to(R)),bytes=len(self.raw),sha256=sha256(self.raw).hexdigest(),functions_and_slices=self.rows,manual_checks=self.checks)
j=Image(B/'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/originals/lib/libJiritsu.so','bdef58b24a3b67b4d14d4f0214b89aae0fcad19f114b4188c328f9d2c092f1d9')
for name in ['adj_cmd_set_file','adj_cmd_set_file2','_ZN11CFileAccess4openEPKci','get_access_filename','adj_cmd_set_file_path','jiritsu_init','cmd_high_capacity_send_file']:j.function(name)
j.slice(0xb278,0x25c,'registered Jiritsu callback','prior184 original .eh_frame whole function')
for pc,wanted in [(0x8e38,'mov w2, #0x1ed'),(0x8e3c,'mov w1, #0x241'),(0x981c,'mov w2, #0x241'),(0xec74,'mov w1, w20'),(0xec78,'mov x0, x22'),(0xecfc,'str wzr, [x23]'),(0xecf4,'mov w1, w20'),(0xecf8,'mov x0, x22'),(0x95d4,'mov w0, #-1'),(0x95e0,'strb w0, [x21, #0x29]'),(0x95f0,'ldrb w0, [x21, #0x29]'),(0x95f8,'mov x1, x22'),(0x93d8,'b #0x93b8'),(0x9408,'b #0x93a0'),(0x6dac,'mov w0, #0x480'),(0x6db4,'movk w0, #0x16f, lsl #16'),(0x6da4,'adrp x2, #0xb000'),(0x6da8,'add x2, x2, #0x278')]:j.asm(pc,wanted)
for pc,name in [(0x8e40,'open'),(0x9820,'_ZN11CFileAccess4openEPKci'),(0xec6c,'__errno_location'),(0xec80,'open'),(0xece8,'snprintf'),(0xecec,'__errno_location'),(0xed00,'open'),(0x95bc,'sys_mount'),(0x9600,'get_access_filename'),(0x6dbc,'osal_reg_sync_msg_queue_cb'),(0xb37c,'cmd_high_capacity_send_file'),(0xacc4,'adj_cmd_set_file2')]:j.call(pc,name)
# Both ordinary-file branches reach open after a call that may clobber x2;
# no explicit x2/w2 assignment repairs the required creation-mode argument.
mode_gaps=[]
for a,z in [(0xec6c,0xec80),(0xecec,0xed00)]:
 rows=list(j.md.disasm(j.read(a,z-a),a));assert rows[0].mnemonic=='bl'
 assert all(not (i.op_str.startswith(('x2,','w2,'))) for i in rows[1:])
 mode_gaps.append(dict(after_call=hex(a),open=hex(z),explicit_mode_assignment=False,actual_register_value_or_created_mode_known=False))
for pc,s in [(0x31203,'/tmp/jiritsu/libJit.so'),(0x31375,'/mnt'),(0x11d7e,'%s/%s'),(0x11dd7,'%s'),(0x327e6,'%s%s')]:j.string(pc,s)
u=Image(B/'stage182-boot-selector-and-recovery-admission/evidence/boot-request/originals/lib/libosal_uipc.so','09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3')
for name in ['osal_reg_sync_msg_queue_cb','u_osal_reg_sync_msg_queue_cb','reg_sync_msg_queue_cb']:u.function(name)
for a,n,label in [(0x2b88,0x338,'pool slot selection and pthread creation'),(0x2ec0,0x80,'registration counter and conditional pool expansion'),(0x3260,0x130,'shared fd receive loop and returned callback invocation'),(0x3390,0x58,'pthread entry naming and receive-loop entry')]:u.slice(a,n,label)
for pc,wanted in [(0x5bb4,'tbz w4, #0xf, #0x5c80'),(0x5c90,'b #0x2560'),(0x2efc,'cmp w19, w0'),(0x2f00,'b.lt #0x2f10'),(0x2f18,'b #0x2b88'),(0x2cb8,'adrp x2, #0x3000'),(0x2cc0,'add x2, x2, #0x390'),(0x33e0,'bl #0x3260'),(0x32cc,'ldr w0, [x21]'),(0x32e8,'ldp x2, x1, [x29, #0x60]'),(0x32f0,'blr x2'),(0x3314,'cbz w0, #0x32e8')]:u.asm(pc,wanted)
for pc,name in [(0x3db0,'ioctl'),(0x2cd0,'pthread_create'),(0x32d8,'ioctl'),(0x3308,'ioctl')]:u.call(pc,name)
queue=0x016f0480;assert not queue&0x8000
# Bind the unnamed callback to the earlier original FDE, not to a guessed end.
prior=B/'stage184-community-recovery-and-standalone-service/evidence/standalone-commands/selected-original-functions.json';f=next(x for x in json.loads(prior.read_text()) if x['file']=='libJiritsu.so' and x['va']=='0xb278');assert f['bytes']==0x25c and f['boundary']=='original .eh_frame FDE' and sha256(j.read(0xb278,0x25c)).hexdigest()==f['sha256']
out=dict(schema='fx3-stage232-plan-writer-and-callback-thread-static-v1',images=[j.result(),u.result()],mode_gaps=mode_gaps,writer=dict(old_explicit_create_mode='0755 before umask/default ACL',old_flags='0x241 WRONLY|CREAT|TRUNC without EXCL/NOFOLLOW',new_wrapper_ordinary_file_mode_argument_not_established=True,root0600_RAM_plan_creation_proven=False,existing_0600_file_mode_preservation_requires_actual_safe_precreation=True,exact_target_umask_ACL_mount_permissions_unobserved=True),path=dict(normal_base='/tmp/jiritsu for operation0, /mnt for operation1',operation1_forces_selector_ff=True,absolute_outside_base_is_prefixed_not_passed_as_root_path=True,plain_RAM_plan_path_not_proven_direct_target=True,path_escape_is_currently_validated_safe_provisioning=False,ordinary_flash_mount_side_effect_not_removed=True),thread=dict(queue=hex(queue),bit15_clear_uses_uipc_registration_ioctl=True,conditional_pool_creation_uses_same_receive_function=True,receive_loop_invokes_ioctl_returned_callback=True,one_queue_does_not_prove_same_TID=True,current_actual_driver_pool_limit_or_assignment_unobserved=True,kernel_callback_to_worker_assignment_not_yet_audited=True,current231_different_live_creator_thread_correctly_rejected=True,loosening_thread_guard_accepted=False),next_adapter=dict(proposed_preparer_embeds_expected_worker_SHA_nonce_and_association_fields=True,proposed_preparer_creates_full_EXCL_NOFOLLOW_root0600_RAM_plan_using_its_own_target_CLOCK_MONOTONIC=True,empty_precreation_plus_normal_host_RAM_write_is_not_a_complete_route=True,requires_independent_own_code_design_build_model_and_scope_review=True,plan_START_to_OBSERVE_transition_and_host_receipt_readback_still_required=True,preparer_implemented=False,preparer_deployable=False,thread_assignment_or_thread_independent_exact_exit_identity_design_still_required=True,no_generic_shell=True),source_only=True,original_Sony_glibc_Linux_or_public_camera_code_executed=False,new_device_USB_cache_admin_auth_upload_firmware_or_WBI_operations=0,first_flash_released=False)
name='contract-audit.json' if not (H/'contract-audit.json').exists() else 'contract-audit-final.json'
(H/name).open('x').write(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='WRITER_AND_QUEUE_ASSUMPTIONS_NOT_SATISFIED',images=2,full_functions=10,original_FDE_function=1,explicit_slices=4,manual_checks=len(j.checks)+len(u.checks),mode_gaps=len(mode_gaps),real_device_operations=0)))
