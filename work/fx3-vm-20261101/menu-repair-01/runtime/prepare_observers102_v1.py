from pathlib import Path
import importlib.util,json,struct,hashlib,subprocess
R=Path(__file__).resolve().parent;H=R/'helpers';A=R.parents[1]/'lead-claude/audits/backup-save-trigger/audit_save_trigger.py'
sp=importlib.util.spec_from_file_location('saveaudit102',A);a=importlib.util.module_from_spec(sp);sp.loader.exec_module(a)
ap=a.Image('ap');backup=a.Module();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
points=[(110,0x2b22c80,'idle_f24_load'),(111,0x2b22c88,'idle_dirty_test'),(112,0x2b22cbc,'product_gate_actual_return'),(113,0x2b22cc0,'idle_original_sync_call'),(114,0x2b22d9c,'dirty_assignment'),(115,0x2a69974,'language_callback'),(116,0x2ab90a4,'language_enqueue'),(117,0x2b23754,'language_daemon_consume'),(118,0x2ec0794,'language_native_write_return'),(119,0x2b22b80,'idle_cond_wait'),(120,0x2b22b84,'idle_cond_wait_return'),(121,0x2b22cc8,'daemon_work_dispatch')]
rows=[]
for ident,pc,label in points:
 row=ap.dis(pc,4)[0];word=int.from_bytes(bytes.fromhex(row['raw']),'little');assert not word&0x7c000000==0x14000000 or word&0xfc000000==0x94000000,(label,row)
 rows.append(dict(row,id=ident,label=label,word=word))
s=(H/'fx3-preset-context-v5-sync100.c').read_text()
needle=' if(id>=80&&id<=102)date98_point(id,c->pc-app_base,r);'
extra=''' if(id>=110&&id<=121){W f24=~0U,index=~0U,work=~0U;peek(app_base+0x8e29f24,&f24,4);peek(app_base+0x47ce0a8,&index,4);if(id==114||id==121)peek(r[29]+0xa0,&work,4);dprintf(2,"FX3_SAVE102_AP_POINT id=%lu relative=%#lx tid=%ld x0=%#lx x1=%#lx w19=%u w20=%u f24_word=%u product_index=%u work_type=%u native_unchanged=1 only_read_observation=1\\n",id,c->pc-app_base,syscall(178),r[0],r[1],(W)r[19],(W)r[20],f24,index,work);}
'''
assert needle in s;s=s.replace(needle,extra+needle)
for typ,name in [('U','addresses'),('W','words'),('U','ids')]:
 old=f'{typ} {name}[36]={{';start=s.index(old)+len(old);end=s.index('}',start)
 addition=','.join('app_base+'+hex(row['va'] if isinstance(row['va'],int) else int(row['va'],16)) if name=='addresses' else hex(row['word']) if name=='words' else str(row['id']) for row in rows)
 s=s[:end]+','+addition+s[end:];s=s.replace(old,f'{typ} {name}[48]={{',1)
s=s.replace('i<36','i<48').replace('points=36','points=48 AP102_idle_language_readonly_points=12')
(H/'fx3-preset-context-v6-save102.c').write_text(s)
s=(H/'fx3-backup-return-v4-sync100.c').read_text().replace('int watched=(service==', 'int watched=(service==0x2cfU&&(key==0x02cf0000U||key==0x02cf03feU))||(service==',1)
s+='''\nint Backup_sync_subsystem(W sid){int saved=*__errno_location();int(*fn)(W)=dlsym((void*)-1,"Backup_sync_subsystem");if(!fn)__builtin_trap();U caller=(U)__builtin_return_address(0);dprintf(2,"FX3_SAVE102_SUBSYSTEM_ENTER sid=%#x tid=%ld caller=%#lx args_unchanged=1 native_call_follows=1\\n",sid,syscall(178),caller);*__errno_location()=saved;int rc=fn(sid);int after=*__errno_location();dprintf(2,"FX3_SAVE102_SUBSYSTEM_RETURN sid=%#x tid=%ld result=%d errno=%d original_call_completed=1 file_success_separate=1\\n",sid,syscall(178),rc,after);*__errno_location()=after;return rc;}\n'''
(H/'fx3-backup-return-v5-save102.c').write_text(s)
kpoints=[(0x2ea0,'Backup_sync_subsystem_entry'),(0x2ca0,'sync_subsystem_mp_entry'),(0x3f0,'local_merge_entry'),(0x42c,'malloc_actual_return'),(0x438,'cache_type_actual_return'),(0x448,'physical_to_VA_actual_return'),(0x464,'old_file_load_actual_return'),(0x614,'local_file_save_actual_return'),(0x5fc,'local_merge_return'),(0x8fd8,'DMM_malloc_entry'),(0x90b4,'DMM_send_original_request'),(0x90b8,'DMM_send_actual_return'),(0x90e0,'DMM_receive_original_args'),(0x90e4,'DMM_receive_actual_return'),(0x9034,'DMM_malloc_return'),(0x91d0,'DMM_malloc_alt_return'),(0x6a88,'backupfile_save_file_entry')]
sym=backup.sym['backupfile_save_file'];rr=backup.dis(sym['st_value'],sym['st_size']);kpoints.extend((int(x['va'],16),'backupfile_save_file_return') for x in rr if x['asm']=='ret')
krows=[]
for pc,label in kpoints:
 row=backup.dis(pc,4)[0];assert len(bytes.fromhex(row['raw']))==4
 krows.append(dict(row,offset=pc,label=label,relocated_call='relocation' in row))
proof={'authority':['msg_451e29d2c9b9','msg_7eb2cdbf663a','msg_2c7707dd92c8'],'inputs':[{'path':str(x.path),'sha256':sha(x.path)} for x in (ap,backup)],'AP_points':rows,'kernel_points':krows,'kernel_observation':'QEMU TCG Z1 CPU breakpoints, no guest text patch; exact original instructions stepped and breakpoints removed before cleanup','runtime_module_base':'must read actual /sys/module/backup/sections/.text; not fixed VA','not_added':['device replies','flush','setters','DMM allocation','parameter writes']}
(R/'ap102-observer-original-proof-v1.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n')
for old,new in [('fx3-preset-context-v5-sync100','fx3-preset-context-v6-save102'),('fx3-backup-return-v4-sync100','fx3-backup-return-v5-save102')]:
 build=json.loads((H/(old+'-build.json')).read_text());args=[x.replace(old,new) for x in build['args']];p=subprocess.run(args,capture_output=True,text=True);(H/(new+'-build.log')).write_text(p.stdout+p.stderr);assert p.returncode==0,(new,p.stderr);(H/(new+'-build.json')).write_text(json.dumps({'args':args,'exit':p.returncode,'source_sha256':sha(H/(new+'.c')),'output_sha256':sha(H/(new+'.so')),'authority':proof['authority'],'new_observation_only':True},indent=2)+'\n')
print('AP102 original guards:',len(rows),'AP points;',len(krows),'kernel observation points; two passive user libraries built')
