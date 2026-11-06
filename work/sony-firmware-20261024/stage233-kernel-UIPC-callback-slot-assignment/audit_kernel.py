"""Static ET_REL section/relocation audit. No kernel code is executed."""
from pathlib import Path
from hashlib import sha256
import io,json,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
H=Path(__file__).resolve().parent;B=H.parent;R=H.parents[2]
P=B/'stage182-boot-selector-and-recovery-admission/evidence/boot-request/originals/kmod/osal_uipc.ko'
raw=P.read_bytes();assert sha256(raw).hexdigest()=='6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38'
e=ELFFile(io.BytesIO(raw));assert e['e_type']=='ET_REL' and e['e_machine']=='EM_AARCH64';symbols=e.get_section_by_name('.symtab');text=e.get_section_by_name('.text').data();rel={}
for section in e.iter_sections():
 if section['sh_type']!='SHT_RELA':continue
 target=e.get_section(section['sh_info']).name
 for r in section.iter_relocations():
  s=symbols.get_symbol(r['r_info_sym']);idx=s['st_shndx'];row=dict(owner_section=target,offset=hex(r['r_offset']),type=r['r_info_type'],symbol=s.name,symbol_value=hex(s['st_value']),symbol_section=e.get_section(idx).name if isinstance(idx,int) else idx,addend=r['r_addend']);assert (target,r['r_offset']) not in rel;rel[target,r['r_offset']]=row
md=Cs(CS_ARCH_ARM64,CS_MODE_ARM);ranges=[];checks=[]
def take(a,z,label):
 data=text[a:z];ins=list(md.disasm(data,a));assert len(ins)*4==len(data)
 rows=[]
 for i in ins:
  row=dict(pc=hex(i.address),raw=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str,relocation=rel.get(('.text',i.address)))
  if i.mnemonic in ('b','bl') and i.op_str.startswith('#') and not row['relocation']:
   word=int.from_bytes(i.bytes,'little');assert word&0x7c000000==0x14000000;delta=word&0x3ffffff;delta=delta-(1<<26) if delta&(1<<25) else delta;assert i.address+delta*4==int(i.op_str[1:],16)
  rows.append(row)
 ranges.append(dict(section='.text',VA=hex(a),end=hex(z),bytes=z-a,label=label,boundary='explicit source slice only',sha256=sha256(data).hexdigest(),original_hex=data.hex(),instructions=rows))
def asm(pc,wanted):
 ins=list(md.disasm(text[pc:pc+4],pc));assert len(ins)==1 and ins[0].mnemonic+' '+ins[0].op_str==wanted,(hex(pc),wanted);checks.append(dict(pc=hex(pc),raw=text[pc:pc+4].hex(),asm=wanted))
def relocated(pc,symbol):
 r=rel['.text',pc];assert r['type']==283 and r['symbol']==symbol;checks.append(dict(pc=hex(pc),raw=text[pc:pc+4].hex(),relocation=r))
for a,z,label in [(0x4d8,0x5b8,'ioctl command normalization, process owner and dispatch table'),(0xe90,0xfc8,'callback registration stores the same handle context before queue registration'),(0x890,0xb30,'receive callback slot binding and shared FIFO removal'),(0x1538,0x15f0,'callback FIFO append and all-slot wake scan'),(0x15f0,0x1788,'synchronous/non-synchronous callback handoff into enqueue')]:take(a,z,label)
for pc,wanted in [(0x538,'and w19, w19, #0x7fffffff'),(0x53c,'cmp w19, #0x10'),(0x55c,'ldr x1, [x20, #0x28]'),(0x564,'b.ne #0x590'),(0x574,'add x3, x3, #0x28'),(0x57c,'ldr x3, [x3, w19, sxtw #3]'),(0x580,'blr x3'),(0x930,'ldr w20, [x29, #0x68]'),(0x934,'cmp w20, #3'),(0x938,'b.hi #0x8e8'),(0x940,'add x0, x19, x20, lsl #5'),(0x944,'ldr x0, [x0, #0x70]'),(0xb00,'mrs x1, sp_el0'),(0xb04,'cmp x0, x1'),(0xb08,'b.eq #0x94c'),(0xaf0,'mrs x2, sp_el0'),(0xaf4,'str x2, [x1, #0x70]'),(0x9c0,'ldr x1, [x19, #0x38]'),(0x9c8,'ldr x2, [x1, #8]'),(0x9d0,'str x2, [x19, #0x38]'),(0x9e8,'str w2, [x1, #0x1c]'),(0x9f4,'stp x4, x2, [x29, #0x50]'),(0xa10,'str x1, [x4, #0x78]'),(0xa88,'str w0, [x24, #0x88]'),(0x1554,'ldr x20, [x1, #0x30]'),(0x1568,'ldr x2, [x20, #0x38]'),(0x157c,'ldr x0, [x2, #8]'),(0x1588,'str xzr, [x21, #8]'),(0x1590,'str x21, [x2]'),(0x158c,'add x19, x20, #0x88'),(0x1594,'add x22, x20, #0x108'),(0x159c,'ldr w0, [x19]'),(0x15a4,'ldur x1, [x19, #-0x18]'),(0x15a8,'str wzr, [x19]'),(0x15b8,'add x19, x19, #0x20'),(0x15bc,'cmp x19, x22'),(0x15c0,'b.ne #0x159c'),(0x1684,'bl #0x1538'),(0x1710,'bl #0x1538')]:asm(pc,wanted)
for pc,symbol in [(0x530,'__arch_copy_from_user'),(0x928,'__arch_copy_from_user'),(0x954,'_raw_spin_lock_irqsave'),(0xaa8,'schedule'),(0xacc,'__arch_copy_to_user'),(0x15b4,'wake_up_process'),(0x1560,'_raw_spin_lock_irqsave'),(0x15cc,'_raw_spin_unlock_irqrestore')]:relocated(pc,symbol)
for pc,wanted in [(0xee0,'mov x20, x2'),(0xf0c,'str x3, [x0, #0x10]'),(0xf20,'strh w19, [x0, #0x1a]'),(0xf28,'str x20, [x0, #0x30]'),(0xf84,'ldr w0, [x29, #0x48]')]:asm(pc,wanted)
for pc,symbol in [(0xee8,'__arch_copy_from_user'),(0xf94,'reg_sync_msg_queue_cb')]:relocated(pc,symbol)
literal=rel['.text',0x5b8];assert literal['type']==257 and literal['symbol_section']=='.rodata' and literal['addend']==0x318
table=[]
for index in range(17):
 r=rel['.rodata',0x318+0x28+8*index];assert r['type']==257 and r['symbol_section']=='.text';table.append(dict(index=index,entry=r))
assert table[13]['entry']['addend']==0x890 and table[8]['entry']['addend']==0xe90
selected=[rel['.text',a] for a in [0x5b8,0xb40,0xb48,0xfc8]];assert selected[1]['symbol_section']==selected[3]['symbol_section']=='.text' and selected[1]['addend']==selected[3]['addend']==0x15f0
markers=[dict(name=s.name,VA=hex(s['st_value'])) for s in symbols.iter_symbols() if s['st_shndx']==2 and s.name in ('$x','$d') and s['st_value']<=0x1798]
report=dict(schema='fx3-stage233-kernel-callback-slot-static-v1',source=dict(path=str(P.relative_to(R)),bytes=len(raw),sha256=sha256(raw).hexdigest()),slices=ranges,manual_instruction_checks=checks,dispatch_table=table,selected_literal_relocations=selected,mapping_symbols=markers,userspace_contract='stage232 libosal_uipc shared fd ioctl8000000d + 32B reply containing callback/arg/message/index',ioctl_command='0x8000000d',normalized_index=13,selected_handler_section='.text',selected_handler_offset='0x890',registration=dict(normalized_index=8,handler_offset='0xe90',CB_context30_stores_same_handle_context=True,CB_function10_is_handoff15f0=True,queue_number_stored_separately_at_CB1a=True),worker_slots=dict(count=4,stride=32,task_pointer_base='context+0x70',pending_CB_base='context+0x78',sleep_flag_base='context+0x88',index_bound='0..3',slot_sticks_to_a_task_not_a_queue=True),queue_algorithm=dict(append='tail of context+0x38 singly-linked pending callback list',receive='remove head of same context+0x38 under spin lock',wake='scan all four sleep slots and wake each populated task',receive_checks_queue_to_thread_affinity_in_this_slice=False),limits=['Static fixed module bytes, not the currently loaded module or runtime state.','User receiver count comes from unmeasured target configuration; four supported slots do not mean four active threads.','No full scheduler/kernel/IPC/driver execution; synthetic interleavings are conditional possibilities.','Other routes outside the pinned branch are not exhaustively excluded.'],implication='If multiple receivers share this handle, different slots can remove successive callbacks; same service queue is insufficient to establish231same-live-creator-thread eligibility.',original_Sony_Linux_or_kernel_module_executed=False,new_device_operations=0,first_flash_released=False)
name='kernel-assignment-audit.json' if not (H/'kernel-assignment-audit.json').exists() else 'kernel-assignment-audit-final.json'
(H/name).open('x').write(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(status='SHARED_CALLBACK_FIFO_FOUR_TASK_SLOTS_PINNED',slices=len(ranges),manual_checks=len(checks),dispatch_entries=len(table),supported_slots=4,current_active_slots_verified=False,camera_operations=0)))
