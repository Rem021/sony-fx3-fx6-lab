from pathlib import Path
import importlib.util,json,hashlib,subprocess
R=Path(__file__).resolve().parent;H=R/'helpers';A=R.parents[1]/'lead-claude/audits/backup-save-trigger/audit_save_trigger.py';audit=R.parents[1]/'lead-claude/audits/gpe-completion-unfetched/unfetched-proof.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(audit)=='3a4f2a1a02ec8f86ba704cf82cba47a5c37e0767e05345731632f046e922aa55'
sp=importlib.util.spec_from_file_location('readonly104',A);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);k=m.Module('osal_uipc');g=m.Image('libgpe.so');assert sha(k.path)=='6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38';assert sha(g.path)=='363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464'
kp=[(0x5b4c,'dynamic_owner_claim',3,0),(0x59b0,'dynamic_owner_release',23,None),(0x5c80,'dynamic_owner_pending_release',23,None),(0x3480,'completion_alloc_owner_read',21,None),(0x34a4,'first_unfetched_return',21,None)]
kr=[]
for pc,label,qreg,tokenreg in kp:
 row=k.dis(pc,4)[0];kr.append(dict(row,offset=pc,label=label,module='uipc',queue_register=qreg,token_register=tokenreg,relocated_call=False))
up=[(0xa110,'original_Main_SyncCallback_enter'),(0xa154,'original_Main_SyncCallback_return'),(0xd888,'original_SendDrawComp_enter'),(0xd714,'original_shared_Send_return')];ur=[]
for pc,label in up:
 row=g.dis(pc,4)[0];ur.append(dict(row,offset=pc,label=label,module='gpe',relocated_call=False))
task=k.dis(k.sym['print_task_info']['st_value'],k.sym['print_task_info']['st_size']);assert any(x['raw']=='038843b9'and'x0, #0x388' in x['asm']for x in task);assert any(x['raw']=='42e01491'and'#0x538'in x['asm']for x in task)
proof={'authority':'msg_b94a0dacc3e4','audit':{'path':str(audit),'sha256':sha(audit)},'inputs':[{'path':str(v.path),'sha256':sha(v.path)}for v in [k,g]],'uipc_points':kr,'user_gpe_points':ur,'current_task':{'register':'SP_EL0','pid_offset':0x388,'comm_offset':0x538,'comm_bytes':16,'original_print_task_info':task},'queue_layout':{'flags_offset':0,'count_offset':2,'owner_offset':48,'bytes':64},'scope':'QEMU TCG CPU breakpoint table only; before/after exact original owner store, no writes to original memory or registers; user wrappers preserve calls/results/errno'}
(R/'ap104-observer-original-proof-v1.json').write_text(json.dumps(proof,indent=2)+'\n')
old='fx3-gpe-observe-v24-serial102';new='fx3-gpe-observe-v25-complete104';dest=H/(new+'.c');assert not dest.exists();s=(H/(old+'.c')).read_text();s=s.replace('#include "fx3-gpe-command-wait102-v1.h"','#include "fx3-gpe-command-wait102-v1.h"\n#include "fx3-complete104-observe-v1.h"',1)
a='if(cb){struct gpe_callback_param cp={seq,0,arg};((void (*)(const void *))cb)(&cp);}'
b='if(cb){struct gpe_callback_param cp={seq,0,arg};gpe104_callback((void (*)(const void *))cb,&cp,seq,op,raw[ao],src,arg);}'
assert s.count(a)==1;s=s.replace(a,b)
a='if(!raw[ao]&&src){unsigned int status=0;if(!draw_complete(src,&status,4)){reason=GPE_DELIVERY;goto done;}}'
b='if(!raw[ao]&&src){unsigned int status=0;if(!gpe104_complete(draw_complete,src,&status,4,seq,op,raw[ao])){reason=GPE_DELIVERY;goto done;}}'
assert s.count(a)==1;s=s.replace(a,b)
a='if(gpe102_take(&command_lock,seq,op)){marker(op,seq,raw,readable,5,GPE_BUSY);return 5;}'
b='if(gpe102_take(&command_lock,seq,op)){marker(op,seq,raw,readable,5,GPE_BUSY);gpe104_command_return(seq,op,src,5);return 5;}'
assert s.count(a)==1;s=s.replace(a,b)
a=' /* Nonzero is returned to original Main, which alone sends failure status. */\n return result;';assert s.count(a)==1;s=s.replace(a,' gpe104_command_return(seq,op,src,result);\n'+a)
a=' draw_complete=dlsym(h,"_ZN5mpgpe7message12SendDrawCompEjPKvm");';assert s.count(a)==1;s=s.replace(a,a+'\n {int saved104=*__errno_location();dprintf(2,"FX3_GPE104_LIB_BIND base=%#lx MainSyncCallback=%#lx SendDrawComp=%#lx passive_only=1\\n",base,base+0xa110,base+0xd888);*__errno_location()=saved104;}')
s+='''\nstatic int gpe104_peek(U p,void*out,U n){return process_mem>=0&&p>=4096&&p<0x8000000000UL&&n<=0x8000000000UL-p&&pread(process_mem,out,n,(long)p)==(long)n;}\nint osal_dynamic_id(unsigned flags,unsigned module,void*argument){int saved=*__errno_location();int(*fn)(unsigned,unsigned,void*)=dlsym((void*)-1,"osal_dynamic_id");if(!fn)__builtin_trap();*__errno_location()=saved;if(flags==0x2a||flags==0x4a)return gpe104_dynamic(fn,gpe104_peek,flags,module,argument,(U)__builtin_return_address(0));return fn(flags,module,argument);}\n'''
dest.write_text(s);build=json.loads((H/(old+'-build.json')).read_text());args=[x.replace(old,new)for x in build['args']];q=subprocess.run(args,capture_output=True,text=True);(H/(new+'-build.log')).write_text(q.stdout+q.stderr);assert q.returncode==0,q.stderr
(H/(new+'-build.json')).write_text(json.dumps({'args':args,'exit':q.returncode,'authority':'msg_b94a0dacc3e4','source_sha256':sha(dest),'output_sha256':sha(H/(new+'.so')),'passive_header_SHA256':sha(H/'fx3-complete104-observe-v1.h'),'baseline_source_SHA256':sha(H/(old+'.c')),'pixel_backend_unchanged_SHA256':sha(H/'fx3-gpe-backend-v8.c'),'all_existing_completion_order_conditions_results_unchanged':True,'new_observation_only':True},indent=2)+'\n');print('AP104_NATIVE_GUARDS_AND_PASSIVE_LIBRARY_BUILT')
