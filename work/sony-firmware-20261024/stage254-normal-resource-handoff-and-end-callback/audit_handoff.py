"""Bind normal resource/acquire/end routes from original ELF bytes, no execution."""
from pathlib import Path
from hashlib import sha256
from elftools.dwarf.callframe import FDE
import importlib.util,json,struct

H=Path(__file__).resolve().parent;B=H.parent;R=B.parents[1]
spec=importlib.util.spec_from_file_location('normal254',B/'stage149-normal-cooperator-and-NIN-checkpoint/normal_cooperator.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);obj,core=m.images()
entries=[0xea58c,0xea660,0xea6b0,0xea924,0xea9b4,0xea750,0xea1dc,0xea488,0xea3e0,0xea71c,0xeac50,0xec458,0xec4bc]
frames={x['initial_location']:x['address_range']for x in obj.elf.get_dwarf_info().EH_CFI_entries()if isinstance(x,FDE)}
functions=[]
for at in entries:
 raw=obj.read(at,frames[at]);functions.append(dict(image='libObj.so',VA=hex(at),bytes=len(raw),sha256=sha256(raw).hexdigest(),boundary='original EH FDE',instructions=obj.instructions(at,len(raw))))
core_names=['_Z19SenserIfRegSenEndCBPv','_ZN3Usb12handle_inputER20InitiationDispatcher','_ZN19WorkerThreadManager4joinEv','_ZN19WorkerThreadManager6cancelEv','_ZN3Usb4stopEPFv13__USBIF_EVENTP17usbif_event_paramiE']
functions += [dict(image='libsencore.so',**core.function(n))for n in core_names]
oi={int(i['pc'],16):i for f in functions if f['image']=='libObj.so'for i in f['instructions']}
ci={int(i['pc'],16):i for f in functions if f['image']=='libsencore.so'for i in f['instructions']}
checks=[]
def expect(rows,pairs):
 for at,asm in pairs.items():
  assert rows[at]['asm']==asm,(hex(at),rows[at]);checks.append(dict(pc=hex(at),word=rows[at]['bytes'],asm=asm))
expect(oi,{
 0xea5b4:'mov w4, #0x3d',0xea5b8:'mov w1, #0x2a',0xea5bc:'ldr x3, [x3, #0x6e0]',
 0xea67c:'bl #0x563f0',0xea6d0:'mov w1, #2',0xea6e8:'bl #0xea660',
 0xea9d8:'bl #0xea924',0xea944:'ldrb w1, [x21, #0xd9]',0xea948:'cbnz w1, #0xea998',
 0xea978:'ldr x2, [x2, #0xf40]',0xea97c:'bl #0x55a50',0xea980:'mov w0, #1',0xea988:'strb w0, [x21, #0xd9]',
 0xea9a4:'add x0, x0, #0xe0',0xea9ac:'b #0x56e40',
 0xea780:'bl #0x57d60',0xea788:'mov w2, #0',0xea790:'bl #0x55f60',0xea7d8:'add x0, x21, #0xb8',0xea7e0:'bl #0x55f60',
 0xea818:'bl #0x56e40',0xea81c:'mov x0, x22',0xea820:'bl #0x55f20',0xea824:'ldr x0, [x20, #0xf58]',
 0xea850:'add x0, x24, #0x48',0xea854:'bl #0xec458',0xea858:'mov x0, x27',0xea860:'bl #0xec4bc',
 0xea864:'ldrb w0, [x19, #0x50]',0xea884:'bl #0xea488',0xea8cc:'mov w0, #4',
 0xea8d4:'add x0, x21, #0xb8',0xea8d8:'bl #0x55f20',0xea8dc:'mov x0, x19',0xea8e0:'bl #0xea3e0',
 0xea900:'bl #0xea71c',0xea908:'str xzr, [x0, #0x100]',0xea918:'mov w0, #1',0xea91c:'str w0, [x24]',0xea920:'b #0xea81c',
 0xea414:'bl #0xec458',0xea420:'bl #0xec4bc',0xea424:'mov x0, x19',
 0xea728:'bl #0x55370',0xeac54:'ldr x0, [x0, #0xc38]',0xeac58:'ldr x0, [x0]',
 0xeac5c:'cbz x0, #0xeac74',0xeac60:'ldr w0, [x0, #0x14]',0xeac64:'cbnz w0, #0xeac74',
 0xeac6c:'add x0, x0, #0xb8',0xeac70:'b #0x56e40',0xeac74:'ret ',
 0xec478:'bl #0x57a90',0xec4dc:'bl #0x57910',0xec4e0:'cbz w0, #0xec504',0xec508:'str x0, [x19]',
})
expect(ci,{0xd2b0:'ldr x1, [x1, #0xf00]',0xd2b4:'str x0, [x1]',0xcd78:'bl #0xa6a0',
 0xcd7c:'ldr x0, [x19, #0x18]',0xcd84:'blr x0',0xcd8c:'ldr x0, [x0, #0xf00]',0xcd90:'ldr x0, [x0]',0xcd98:'blr x0'})
orels={r['r_offset']:r for r in obj.elf.get_section_by_name('.rela.dyn').iter_relocations()};bindings=[]
for at,addend in [(0x2616e0,0xea9b4),(0x262f40,0xea750),(0x262110,0xeac50),(0x261758,0xea1dc),(0x262c38,0x2ce0b0)]:
 r=orels[at];assert r['r_info_type']==1027 and r['r_info_sym']==0 and r['r_addend']==addend
 bindings.append(dict(image='libObj.so',offset=hex(at),type='RELATIVE',target=hex(addend)))
crels={r['r_offset']:r for r in core.elf.get_section_by_name('.rela.dyn').iter_relocations()};r=crels[0x6af00];symbol=core.dynsym.get_symbol(r['r_info_sym']);assert symbol.name=='fp_senEndNotify' and symbol['st_value']+r['r_addend']==0x6bab0
bindings.append(dict(image='libsencore.so',offset='0x6af00',symbol=symbol.name,target='0x6bab0'))
jump=core.read(0x16ae0,7);targets=[0xcc9c+4*x for x in struct.unpack('<7b',jump)];assert targets[3]==0xcd70
assert oi[0xea820]['PLT_symbol']=='sem_wait' and oi[0xea8d8]['PLT_symbol']=='sem_wait'
assert oi[0xeac70]['PLT_symbol']=='sem_post' and oi[0xea728]['PLT_symbol']=='_ZN3MWF8RsrcAcsr7ReleaseEv'
# This exact callback contains only context checks and sem_post: no host wire reply.
end_cb=next(f for f in functions if f['image']=='libObj.so'and f['VA']=='0xeac50')
assert [i['PLT_symbol']for i in end_cb['instructions']if i['PLT_symbol']]==['sem_post']
edges=[
 ('normal onComplete','resource Acquire','obj0xea6e8 ->0xea660 ->MWF Acquire'),
 ('resource registration','resource callback','resource42 /obj relocation2616e0 ->ea9b4'),
 ('resource callback','supervisor start or acquire semaphore post','ea9b4 ->ea924; createea750 once, otherwise sem_post2ce0e0'),
 ('supervisor acquire wait','NIN cancellation and join attempt','ea820 ->ea854/ec458 ->ea860/ec4bc'),
 ('supervisor','service worker create','ea884 ->ea488;261758 ->ea1dc'),
 ('supervisor registration','core end-callback global','obj262110->eac50;coreRegSenEndCB stores fp_senEndNotify'),
 ('core internal event3','worker joins then end notification','jump16ae0[3]->cd70;joincd78;notifycd98'),
 ('normal end callback','service-end semaphore post','eac50,ctx!=NULL and mode0 ->sem_post2ce0b8'),
 ('supervisor end wait','service worker cancellation/join attempt','ea8d8 ->ea8e0 ->ea3e0'),
 ('normal supervisor','resource Release then normal wait loop','ea900 ->ea71c;state1;ea920 ->ea81c'),
]
out=dict(status='NORMAL_RESOURCE_AND_END_CALLBACK_CHAIN_STATICALLY_BOUND_NOT_CAMERA_COMPLETION',
 original_object_sha256=sha256(obj.raw).hexdigest(),original_core_sha256=sha256(core.raw).hexdigest(),
 functions=functions,instruction_checks=len(checks),checked_words=checks,relocation_bindings=bindings,
 internal_event3_dispatch=dict(table_VA='0x16ae0',raw_hex=jump.hex(),target=hex(targets[3])),
 path_edges=[dict(source=a,target=b,evidence=c)for a,b,c in edges],
 semaphores=dict(resource='objBSS0x2ce0e0',service_end='objBSS0x2ce0b8'),
 thread_scopes=dict(NIN_handle='normal cooperator+0x48',service_worker_handle='normal cooperator+0x58',
  supervisor='0xea750, normally loops back to resource semaphore until separate shutdown state5'),
 verified_limits=[
  'Resource callback is conditional on actual MWF key/pending completion;152 preserved failures are reused, not rerun.',
  'pthread_create result is not checked before started flag1; a flag or a semaphore post is not a thread-liveness receipt.',
  'NIN/service-worker cancel and join wrappers return status, but the shown supervisor callers do not consume it.',
  'sem_wait returns at ea820 and ea8d8 are not checked; reaching the next basic block does not by itself prove a matching post.',
  'Core event3 calls end notification after join attempts, not after a separately checked aggregate success result.',
  'fp_senEndNotify is one global function pointer; the callback carries no per-trial nonce, USB reply or per-thread completion status.',
  'Normal return reuses the long-lived supervisor. Its continued existence is not itself a session-exit failure; specific session thread completion is still unverified.'
 ],
 nominal_full_path_exists_in_saved_files=True,actual_runtime_registration_and_OS_delivery_unmeasured=True,
 camera_threads_completion_proven=False,host_readable_thread_success_receipt_found_in_this_path=False,
 new_original_guest_or_native_code_execution=False,new_camera_cache_admin_operations=0)
with(H/'handoff-and-end-audit.json').open('x')as f:json.dump(out,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps(dict(status=out['status'],whole_original_functions=len(functions),instruction_checks=len(checks),relocation_bindings=len(bindings),bound_edges=len(edges),live_operations=0)))
