/* Passive native PLT observation; exact calls/arguments/results/errno retained. */
typedef unsigned long U;
extern void *dlsym(void*,const char*);extern int dprintf(int,const char*,...),*__errno_location(void);extern long syscall(long,...),pread(int,void*,U,long);extern int open(const char*,int,...);extern char*strstr(const char*,const char*);extern void*memcpy(void*,const void*,U);
struct light_ts{long s,n;};extern int clock_gettime(int,struct light_ts*);
struct light_di{const char*file;void*base;const char*symbol;void*address;};extern int dladdr(const void*,struct light_di*);
static int memfd=-1;static U events,gpe_base;
static int(*complete_fn)(unsigned,const void*,U);
static int(*alloc_fn)(unsigned,void**,unsigned,unsigned);
static int(*snd_fn)(unsigned,void*);
static U stamp(void){struct light_ts t={0};clock_gettime(1,&t);return(U)t.s*1000000000UL+t.n;}
static U thread_pointer(void){
#ifdef LIGHT104_HOST
 return 0x104104;
#else
 U p;__asm__ volatile("mrs %0,tpidr_el0":"=r"(p));return p;
#endif
}
static int peek(U p,void*out,U n){
#ifdef LIGHT104_HOST
 if(!p)return 0;memcpy(out,(void*)p,n);return 1;
#else
 return memfd>=0&&p>=4096&&p<0x8000000000UL&&n<=0x8000000000UL-p&&pread(memfd,out,n,(long)p)==(long)n;
#endif
}
#ifndef LIGHT104_HOST
__attribute__((constructor))static void ready(void){int saved=*__errno_location();memfd=open("/proc/self/mem",0x80000);alloc_fn=dlsym((void*)-1,"osal_valloc_msg_wait");snd_fn=dlsym((void*)-1,"osal_snd_msg");dprintf(2,"FX3_LIGHT104_READY tid=%ld tpidr=%#lx mem_O_RDONLY=1 mem_available=%u alloc_bound_before_threads=%u snd_bound_before_threads=%u no_runtime_dladdr=1 no_GDB_breakpoints=1 passive_only=1\n",syscall(178),thread_pointer(),memfd>=0,alloc_fn!=0,snd_fn!=0);*__errno_location()=saved;}
#endif
static const char* path(void*caller,U*rel,int*in_gpe){U base=__atomic_load_n(&gpe_base,__ATOMIC_ACQUIRE);*in_gpe=base&&(U)caller>=base&&(U)caller<base+0x20000;*rel=*in_gpe?(U)caller-base:0;if(*in_gpe&&*rel==0xa12c)return"original_SyncCallback_SendDrawComp_PLT";if(*in_gpe&&*rel==0x9c50)return"original_Main_failure_SendDrawComp_PLT";return"native_PLT_caller_unclassified_use_passive_lib_base_offline";}

int light_SendDrawComp(unsigned,const void*,U)
#ifndef LIGHT104_HOST
 __asm__("_ZN5mpgpe7message12SendDrawCompEjPKvm")
#endif
;
int light_SendDrawComp(unsigned q,const void*p,U n){
 int saved=*__errno_location();int(*f)(unsigned,const void*,U)=__atomic_load_n(&complete_fn,__ATOMIC_ACQUIRE);if(!f){f=dlsym((void*)-1,"_ZN5mpgpe7message12SendDrawCompEjPKvm");if(!f)__builtin_trap();__atomic_store_n(&complete_fn,f,__ATOMIC_RELEASE);__atomic_store_n(&gpe_base,(U)f-0xd888,__ATOMIC_RELEASE);}void*caller=__builtin_return_address(0);U rel=0;int in_gpe=0;const char*kind=path(caller,&rel,&in_gpe);unsigned status=0;int available=n==4&&peek((U)p,&status,4);U id=__atomic_add_fetch(&events,1,__ATOMIC_RELAXED);long tid=syscall(178);U tp=thread_pointer();
 dprintf(2,"FX3_LIGHT104_SENDCOMP_ENTER tid=%ld tpidr=%#lx event=%lu ns=%lu QID=%#x bytes=%lu status=%#x status_available=%u caller=%p caller_relative=%#lx caller_is_libgpe=%u call_path=%s adapter_seq_unavailable_here=1 unchanged=1\n",tid,tp,id,stamp(),q,n,status,available,caller,rel,in_gpe,kind);
 *__errno_location()=saved;int result=f(q,p,n);int after=*__errno_location();dprintf(2,"FX3_LIGHT104_SENDCOMP_RETURN tid=%ld tpidr=%#lx event=%lu ns=%lu QID=%#x result=%d errno=%d unchanged=1\n",tid,tp,id,stamp(),q,result,after);*__errno_location()=after;return result;
}
int osal_valloc_msg_wait(unsigned q,void**out,unsigned n,unsigned wait){
 int saved=*__errno_location();int(*f)(unsigned,void**,unsigned,unsigned)=__atomic_load_n(&alloc_fn,__ATOMIC_ACQUIRE);if(!f){f=dlsym((void*)-1,"osal_valloc_msg_wait");if(!f)__builtin_trap();__atomic_store_n(&alloc_fn,f,__ATOMIC_RELEASE);}void*caller=__builtin_return_address(0);U rel=0;int in_gpe=0;path(caller,&rel,&in_gpe);int observe=((q>>16)&255)==0x82;U id=observe?__atomic_add_fetch(&events,1,__ATOMIC_RELAXED):0;long tid=observe?syscall(178):0;U tp=observe?thread_pointer():0;
 if(observe)dprintf(2,"FX3_LIGHT104_ALLOC_ENTER tid=%ld tpidr=%#lx event=%lu ns=%lu QID=%#x bytes=%u wait=%u out=%p caller=%p caller_relative=%#lx caller_is_libgpe=%u unchanged=1\n",tid,tp,id,stamp(),q,n,wait,out,caller,rel,in_gpe);
 *__errno_location()=saved;int result=f(q,out,n,wait);int after=*__errno_location();void*message=0;int available=observe&&result==0&&peek((U)out,&message,8);
 if(observe)dprintf(2,"FX3_LIGHT104_ALLOC_RETURN tid=%ld tpidr=%#lx event=%lu ns=%lu QID=%#x result=%d errno=%d message=%p message_available=%u unchanged=1\n",tid,tp,id,stamp(),q,result,after,message,available);*__errno_location()=after;return result;
}
int osal_snd_msg(unsigned q,void*message){
 int saved=*__errno_location();int(*f)(unsigned,void*)=__atomic_load_n(&snd_fn,__ATOMIC_ACQUIRE);if(!f){f=dlsym((void*)-1,"osal_snd_msg");if(!f)__builtin_trap();__atomic_store_n(&snd_fn,f,__ATOMIC_RELEASE);}void*caller=__builtin_return_address(0);U rel=0;int in_gpe=0;path(caller,&rel,&in_gpe);int observe=((q>>16)&255)==0x82;U id=observe?__atomic_add_fetch(&events,1,__ATOMIC_RELAXED):0;long tid=observe?syscall(178):0;U tp=observe?thread_pointer():0;unsigned first4=0;int available=observe&&peek((U)message,&first4,4);
 if(observe)dprintf(2,"FX3_LIGHT104_SND_ENTER tid=%ld tpidr=%#lx event=%lu ns=%lu QID=%#x message=%p body_first4=%#x body_available=%u read_before_ownership_transfer=1 caller=%p caller_relative=%#lx caller_is_libgpe=%u unchanged=1\n",tid,tp,id,stamp(),q,message,first4,available,caller,rel,in_gpe);
 *__errno_location()=saved;int result=f(q,message);int after=*__errno_location();if(observe)dprintf(2,"FX3_LIGHT104_SND_RETURN tid=%ld tpidr=%#lx event=%lu ns=%lu QID=%#x result=%d errno=%d message_not_read_after_transfer=1 unchanged=1\n",tid,tp,id,stamp(),q,result,after);*__errno_location()=after;return result;
}
