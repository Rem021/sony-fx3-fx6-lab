from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'helpers';p=H/'fx3-completion104-light-v2.c';assert not p.exists();s=(H/'fx3-completion104-light-v1.c').read_text()
s=s.replace('static int memfd=-1;static U events;', '''static int memfd=-1;static U events,gpe_base;
static int(*complete_fn)(unsigned,const void*,U);
static int(*alloc_fn)(unsigned,void**,unsigned,unsigned);
static int(*snd_fn)(unsigned,void*);''')
old='memfd=open("/proc/self/mem",0x80000);dprintf(2,"FX3_LIGHT104_READY tid=%ld tpidr=%#lx mem_O_RDONLY=1 mem_available=%u no_GDB_breakpoints=1 passive_only=1\\n",syscall(178),thread_pointer(),memfd>=0);'
new='''memfd=open("/proc/self/mem",0x80000);alloc_fn=dlsym((void*)-1,"osal_valloc_msg_wait");snd_fn=dlsym((void*)-1,"osal_snd_msg");complete_fn=dlsym((void*)-1,"_ZN5mpgpe7message12SendDrawCompEjPKvm");if(complete_fn)gpe_base=(U)complete_fn-0xd888;dprintf(2,"FX3_LIGHT104_READY tid=%ld tpidr=%#lx mem_O_RDONLY=1 mem_available=%u alloc_bound_before_threads=%u snd_bound_before_threads=%u no_runtime_dladdr=1 no_GDB_breakpoints=1 passive_only=1\\n",syscall(178),thread_pointer(),memfd>=0,alloc_fn!=0,snd_fn!=0);'''
assert old in s;s=s.replace(old,new)
start=s.index('static const char* path(');end=s.index('\nint light_SendDrawComp',start)
s=s[:start]+'''static const char* path(void*caller,U*rel,int*in_gpe){U base=__atomic_load_n(&gpe_base,__ATOMIC_ACQUIRE);*in_gpe=base&&(U)caller>=base&&(U)caller<base+0x20000;*rel=*in_gpe?(U)caller-base:0;if(*in_gpe&&*rel==0xa12c)return"original_SyncCallback_SendDrawComp_PLT";if(*in_gpe&&*rel==0x9c50)return"original_Main_failure_SendDrawComp_PLT";return"native_PLT_caller_unclassified_use_passive_lib_base_offline";}
'''+s[end:]
s=s.replace('static int(*fn)(unsigned,const void*,U);int(*f)(unsigned,const void*,U)=__atomic_load_n(&fn,__ATOMIC_ACQUIRE);','int(*f)(unsigned,const void*,U)=__atomic_load_n(&complete_fn,__ATOMIC_ACQUIRE);')
s=s.replace('__atomic_store_n(&fn,f,__ATOMIC_RELEASE);}void*caller=', '__atomic_store_n(&complete_fn,f,__ATOMIC_RELEASE);__atomic_store_n(&gpe_base,(U)f-0xd888,__ATOMIC_RELEASE);}void*caller=',1)
s=s.replace('static int(*fn)(unsigned,void**,unsigned,unsigned);int(*f)(unsigned,void**,unsigned,unsigned)=__atomic_load_n(&fn,__ATOMIC_ACQUIRE);','int(*f)(unsigned,void**,unsigned,unsigned)=__atomic_load_n(&alloc_fn,__ATOMIC_ACQUIRE);')
s=s.replace('__atomic_store_n(&fn,f,__ATOMIC_RELEASE);}void*caller=', '__atomic_store_n(&alloc_fn,f,__ATOMIC_RELEASE);}void*caller=',1)
s=s.replace('static int(*fn)(unsigned,void*);int(*f)(unsigned,void*)=__atomic_load_n(&fn,__ATOMIC_ACQUIRE);','int(*f)(unsigned,void*)=__atomic_load_n(&snd_fn,__ATOMIC_ACQUIRE);')
s=s.replace('__atomic_store_n(&fn,f,__ATOMIC_RELEASE);}void*caller=', '__atomic_store_n(&snd_fn,f,__ATOMIC_RELEASE);}void*caller=',1)
s=s.replace('int observe=in_gpe||((q>>16)&255)==0x82;', 'int observe=((q>>16)&255)==0x82;')
s=s.replace('int available=result==0&&peek((U)out,&message,8);','int available=observe&&result==0&&peek((U)out,&message,8);')
assert '__atomic_load_n(&fn'not in s and '__atomic_store_n(&fn'not in s;p.write_text(s)
p=H/'check-completion104-light-v2.c';assert not p.exists();s=(H/'check-completion104-light-v1.c').read_text().replace('fx3-completion104-light-v1.c','fx3-completion104-light-v2.c');s=s.replace('relative=0xa12c;assert(!strcmp(path','relative=0xa12c;gpe_base=0x123456-relative;assert(!strcmp(path').replace('relative=0x9c50;assert(!strcmp(path','relative=0x9c50;gpe_base=0x123456-relative;assert(!strcmp(path');p.write_text(s)
p=R/'build_completion104_light_v2.py';assert not p.exists();s=(R/'build_completion104_light_v1.py').read_text().replace('light-v1','light-v2');s=s.replace('Passive original native SendDrawComp PLT,','Resolve native libosal at process construction; no runtime dladdr, module82-only logs. Passive original native SendDrawComp PLT,');p.write_text(s)
print('LIGHT104_V2_CONSTRUCTOR_BINDING_NO_RUNTIME_DLADDR_CREATED')
