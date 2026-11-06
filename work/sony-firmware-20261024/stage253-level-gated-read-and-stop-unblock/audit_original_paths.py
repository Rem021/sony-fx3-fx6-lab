"""Inspect original files only; never import/execute Sony or access USB."""
from pathlib import Path
from hashlib import sha256
import importlib.util,io,json,struct,sys
from elftools.elf.elffile import ELFFile
from elftools.dwarf.callframe import FDE
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM

H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
spec=importlib.util.spec_from_file_location('normal253',B/'stage149-normal-cooperator-and-NIN-checkpoint/normal_cooperator.py')
normal=importlib.util.module_from_spec(spec);spec.loader.exec_module(normal)
obj,core=normal.images()
spec=importlib.util.spec_from_file_location('reader253',B/'stage134-backup-reader-scope-and-service-extension/audit_readers.py')
reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
common=reader.Image('libInfraUsbCmn.so','6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396')
reader.LIB=H/'originals';plugin=reader.Image('libpro00.so','771749c2397c48e9a3444a7562a8f8e2773abf59a262276c2b225cc415ac9403')
names=['_ZN19WorkerThreadManager10onCompleteEi','_Z10ParseCheckPK12SenserPacket','_Z5ParsePK12SenserPacket',
 '_Z15ProductInfoFuncPK12SenserPacket','_Z15GetPluginModulePKcth','_Z19CreatePluginCommandPvtm','Read_Hasp','Reset_Hasp',
 '_ZNK8DeviceIo4readEPvm','_Z15SenserIfReceivePhm']
functions=[dict(image='libsencore.so',**core.function(n))for n in names]
functions += [dict(image='libInfraUsbCmn.so',**common.function('_ZN13CUsbGadgetSen7receiveEPhij')),
 dict(image='libpro00.so',**plugin.function('command001F'))]
frames={f['initial_location']:f['address_range']for f in obj.elf.get_dwarf_info().EH_CFI_entries()if isinstance(f,FDE)}
for at in [0xea128,0xea3e0,0xea750,0xec458,0xec4bc]:
 raw=obj.read(at,frames[at]);functions.append(dict(image='libObj.so',VA=hex(at),bytes=len(raw),sha256=sha256(raw).hexdigest(),boundary='original EH FDE',instructions=obj.instructions(at,len(raw))))
ci={int(i['pc'],16):i for f in functions if f['image']=='libsencore.so'for i in f['instructions']}
pi={int(i['pc'],16):i for f in functions if f['image']=='libpro00.so'for i in f['instructions']}
oi={int(i['pc'],16):i for f in functions if f['image']=='libObj.so'for i in f['instructions']}
mi={int(i['pc'],16):i for f in functions if f['image']=='libInfraUsbCmn.so'for i in f['instructions']}
checks=0
def expect(rows,items):
 global checks
 for at,text in items.items():assert rows[at]['asm']==text,(hex(at),rows[at]);checks+=1
expect(pi,{0x9a4:'ldr x1, [x0, #8]',0x9a8:'cbz x1, #0xa5c',0x9c0:'ldrb w0, [x0]',0x9c4:'cbnz w0, #0xa1c',
 0x9c8:'mov x0, #0x58',0x9d0:'mov x1, #0x58',0x9e4:'bl #0x830',0x9f0:'mov w0, #1',0xa1c:'cmp w0, #0x80',0xa24:'bl #0x800'})
assert pi[0x9e4]['PLT_symbol']=='Read_Hasp' and pi[0xa24]['PLT_symbol']=='Reset_Hasp'
expect(ci,{0xc10c:'cmp w1, #2',0xc11c:'cmp w1, #3',0xc124:'cmp w1, #1',0xc178:'str xzr, [x3]',
 0xea9c:'ldrh w3, [x0, #4]',0xeaa4:'cmp w3, w2',0xeb58:'lsr w2, w2, #8',
 0x1426c:'mov w2, #0x1000',0x14284:'movk w2, #0x10, lsl #16',0x1429c:'mov x2, #0x58',0x142b0:'cmp w20, #0x58'})
expect(oi,{0xea128:'cmp w0, #1',0xea12c:'b.ne #0xea1d8',0xea1d8:'ret ',0xea820:'bl #0x55f20',
 0xea854:'bl #0xec458',0xea860:'bl #0xec4bc',0xea8dc:'mov x0, x19',0xea8e0:'bl #0xea3e0',
 0xea414:'bl #0xec458',0xea420:'bl #0xec4bc',0xec478:'bl #0x57a90',0xec4dc:'bl #0x57910',0xec4e0:'cbz w0, #0xec504'})
assert oi[0xec478]['PLT_symbol']=='pthread_cancel' and oi[0xec4dc]['PLT_symbol']=='pthread_join'
expect(mi,{0x18ee4:'mov x1, #0xe801',0x18ef0:'movk x1, #0x8010, lsl #16',0x18efc:'ldr w0, [x29, #0x18]',
 0x18f04:'add w1, w0, #0x16',0x18f1c:'ldrsb w0, [x0, w1, uxtw]'})
mapping=struct.unpack('<19b',common.read(0x1d448,19));assert mapping[-4+22]==-15
rel={r['r_offset']:r for r in core.elf.get_section_by_name('.rela.dyn').iter_relocations()}
tables={}
for label in ['A','B','C']:
 s=core.symbols['pFunc_level_'+label];data=core.read(s['st_value'],s['st_size']);items=[]
 for at in range(0,len(data),16):
  pfunc=struct.unpack_from('<H',data,at)[0]
  if not pfunc:break
  r=rel[s['st_value']+at+8];sym=core.dynsym.get_symbol(r['r_info_sym']);items.append(dict(pFunc=pfunc,handler=sym.name,target=hex(sym['st_value']+r['r_addend'])))
 tables[label]=dict(VA=hex(s['st_value']),sha256=sha256(data).hexdigest(),items=items)
assert all(any(x['pFunc']==0x10 for x in tables[t]['items'])for t in ['A','B'])
assert not any(x['pFunc']==0x10 for x in tables['C']['items'])
assert core.string(0x171ac)=='libpro%02X.so' and core.string(0x16fa9)=='command%04X'
flags=0x101000;assert flags&3==0 and not flags&(0x40|0x200)
report=dict(status='ORIGINAL_LEVEL_AB_READ_BRANCH_AND_NORMAL_SUPERVISOR_PATH_PINNED',
 functions=functions,instruction_checks=checks,pfunc_tables=tables,
 fixed_read_candidate=dict(pFunc=0x10,category=0,command=0x1f,argument_hex='00',expected_payload_bytes=88,
 plugin='libpro00.so',plugin_entry='command001F',read_flag_value=0,reset_flag_value=0x80,
 Reset_Hasp_call_is_excluded=True,read_open_flags=hex(flags),read_path='/setting/.hasp',
 stock_table_requirement='A or B; level2 or3. Not proof of level3, actual firmware hash or thread exit.',
 read_branch_file_operations_only=True,whole_session_zero_write_claim=False,
 limitation='Authentication history, dynamic loading/constructors and error logging are separate effects; no live command is released.'),
 normal_exit=dict(event_callback='libObj+0xea128',non_event1_returns=True,
 supervisor='libObj+0xea750',supervisor_wait='0xea820 sem_wait',NIN_cancel='0xea854',NIN_join='0xea860',
 later_worker_stop='0xea8e0 ->0xea3e0',normal_cancel_wrapper='0xec458',normal_join_wrapper='0xec4bc',
 direct_inactive_callback_is_not_the_supervisor_trigger=True,
 conditional_minimal_probe_counterexample='If only this normal cooperator is registered and no other canceller acts, challenge-only omits completion/resource handoff, non-event1 callback returns, and no supervisor cancellation is established. This is not an observed device hang or exhaustive proof no other canceller exists.',
 join_success_or_other_cancellers_not_measured=True),
 receive_return_mapping=dict(VA='0x1d448',raw_hex=common.read(0x1d448,19).hex(),kernel_count_minus4_maps_to=-15,
 target_in_252_Serialize='generic negative cancellation/yield loop; not the -6/-4 special mutex-release branch'),
 original_instructions_executed=False,live_camera_or_host_privilege_operations=0)
with(H/'level-gate-and-normal-exit.json').open('x')as f:json.dump(report,f,ensure_ascii=False,indent=2);f.write('\n')

# Exact saved702 module: callback registration, wake/condition bits and cleanup.
mp=B/'stage138-USB-stop-dispatch-and-Mac-ownership/original-components/kmod/usbg_sen.ko';raw=mp.read_bytes()
assert sha256(raw).hexdigest()=='1a7294dd9d3babde3f1e8cc2ac4aa12f54356f61995993bbc18ace095ed0cbf2'
e=ELFFile(io.BytesIO(raw));sy=e.get_section_by_name('.symtab');text=e.get_section_by_name('.text').data()
rels={r['r_offset']:r for r in e.get_section_by_name('.rela.text').iter_relocations()};md=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
parts=[]
for label,lo,hi in [('cleanup',0xe8,0x164),('core_stop',0x168,0x260),('receive_complete',0x308,0x39c),
 ('receive_post_wait',0x10dc,0x10f4),('receive_wait',0x1338,0x138c),('registration',0x15a0,0x15d8)]:
 rows=[]
 for i in md.disasm(text[lo:hi],lo):
  r=rels.get(i.address);rows.append(dict(offset=i.address,word=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str,relocation_symbol=sy.get_symbol(r['r_info_sym']).name if r else None))
 parts.append(dict(label=label,start=hex(lo),bytes=hi-lo,sha256=sha256(text[lo:hi]).hexdigest(),instructions=rows,range_type='explicit code range; anonymous function boundaries not exported STT_FUNC sizes'))
ix={i['offset']:i for p in parts for i in p['instructions']}
expect(ix,{0x150:'bl #0x150',0x154:'ldr x1, [x20]',0x1cc:'mov w0, #2',0x1e4:'bl #0x1e4',
 0x1f8:'bl #0x1f8',0x208:'bl #0xe8',0x370:'mov w0, #1',0x374:'bl #0x374',
 0x10f0:'tbnz w0, #2, #0x17e0',0x1370:'mov w0, #1',0x1374:'bl #0x1374',0x1378:'cbz w0, #0x1350'})
assert ix[0x150]['relocation_symbol']=='usb_ep_dequeue' and ix[0x374]['relocation_symbol']=='set_bit'
r=rels[0x1a30];assert r['r_addend']==0x168 and sy.get_symbol(r['r_info_sym'])['st_shndx']==2

sys.path.insert(0,str(B/'stage146-original-kernel-symbol-and-vendor-route'))
from kernel_symbols import KernelSymbols,K,KERNEL_SHA256
k=KernelSymbols();symbols={x['address']:x['name']for x in k.rows};kernel=[]
for name in ['usb_ep_dequeue','gcore_dequeue','gcw_dequeue','dwc3_gadget_ep_dequeue','dwc3_stop_active_transfer.constprop.16','dwc3_gadget_giveback','usb_gadget_giveback_request']:
 lo,hi=k.span(name);rows=[]
 for i in md.disasm(k.raw[lo:hi],K+lo):
  dest=int(i.op_str[1:],16)if i.mnemonic in ('bl','b')and i.op_str.startswith('#0x')else None
  rows.append(dict(offset=i.address-K,word=i.bytes.hex(),asm=i.mnemonic+' '+i.op_str,target=symbols.get(dest)))
 kernel.append(dict(name=name,start=hex(lo),bytes=hi-lo,sha256=sha256(k.raw[lo:hi]).hexdigest(),instructions=rows,boundary='next original kernel symbol; not ELF function size'))
ki={i['offset']:i for p in kernel for i in p['instructions']}
expect(ki,{0x2e0c0c:'ldr x2, [x2, #0x28]',0x2e0f90:'ldr x2, [x1, #0x30]',0x2d974c:'mov w25, #0',
 0x2d9750:'b #0xffffff8008359678',0x2d9688:'mov w0, w25'})
assert ki[0x2d9674]['target']=='dwc3_gadget_giveback' and ki[0x2d8574]['target']=='usb_gadget_giveback_request'
out=dict(status='EXACT702_STOP_RECEIVE_WAKE_AND_DEQUEUE_BOUNDARIES_PINNED',module_sha256=sha256(raw).hexdigest(),module_ranges=parts,
 kernel_sha256=KERNEL_SHA256,kernel_ranges=kernel,
 findings=[
  'core_stop sets interrupt bit2 and wakes; receive waits on completion bit1. A wake notification alone does not satisfy that condition.',
  'cleanup calls usb_ep_dequeue conditionally on USING, and its return code is not checked before continuing.',
  'The receive-completion callback sets bit1 and wakes. On this completed/interrupted path, common receive maps kernel count-4 to internal-15, reaching Serialize cancellation handling.',
  'The saved DWC3 dequeue contains direct giveback branches and a local success-return branch0x2d974c without a direct giveback call on that branch. Runtime request state, indirect binding and interrupt progress are unmeasured; this is not a claim the device hangs or violates an API contract.',
  'These internal notifications are not a host-readable record proving NIN cancel/join success. Normal initial-MSC supervision and standalone service WorkerThreadManager are distinct paths.'
 ],
 Linux49_reference_must_not_be_replaced_with_modern_dequeue_semantics=True,
 live_callback_or_complete_thread_exit_proven=False,original_instructions_executed=False,new_live_operations=0)
with(H/'stop-unblock-audit.json').open('x')as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status='TWO_ORIGINAL_STATIC_AUDITS_COMPLETE',whole_ELF_functions=len(functions),module_code_ranges=len(parts),kernel_symbol_ranges=len(kernel),instruction_checks=checks,read_payload_bytes=88,live_operations=0)))
