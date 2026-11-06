/* AP104 passive delivery observation. No queue lookup/fetch, no response added. */
static U gpe104_serial;
static U gpe104_thread_pointer(void){
#ifdef FX3_GPE104_HOST_TEST
 return 0x104104;
#else
 U p;__asm__ volatile("mrs %0,tpidr_el0":"=r"(p));return p;
#endif
}
static void gpe104_callback(void(*fn)(const void*),const void*p,unsigned seq,unsigned op,unsigned async,unsigned source,U opaque){
 int saved=*__errno_location();U id=__atomic_add_fetch(&gpe104_serial,1,__ATOMIC_RELAXED),tp=gpe104_thread_pointer(),ns=gpe102_now();long tid=syscall(178);
 dprintf(2,"FX3_GPE104_CB_ENTER tid=%ld tpidr=%#lx event=%lu ns=%lu seq=%u op=%u async=%u completion_source=%#x callback=%#lx opaque=%#lx parameter=%p call_path=adapter_inline_user_callback unchanged=1\n",tid,tp,id,ns,seq,op,async,source,(U)fn,opaque,p);
 *__errno_location()=saved;fn(p);int after=*__errno_location();
 dprintf(2,"FX3_GPE104_CB_RETURN tid=%ld tpidr=%#lx event=%lu ns=%lu seq=%u errno=%d original_callback_returned=1 unchanged=1\n",tid,tp,id,gpe102_now(),seq,after);*__errno_location()=after;
}
static int gpe104_complete(int(*fn)(unsigned,const void*,size_t),unsigned target,const void*p,size_t n,unsigned seq,unsigned op,unsigned async){
 int saved=*__errno_location();U id=__atomic_add_fetch(&gpe104_serial,1,__ATOMIC_RELAXED),tp=gpe104_thread_pointer(),ns=gpe102_now();long tid=syscall(178);unsigned status=~0U;if(n==4)__builtin_memcpy(&status,p,4);
 dprintf(2,"FX3_GPE104_COMPLETE_ENTER tid=%ld tpidr=%#lx event=%lu ns=%lu seq=%u op=%u async=%u completion_source=%#x status=%#x bytes=%lu call_path=adapter_explicit_SendDrawComp real_function=%#lx unchanged=1\n",tid,tp,id,ns,seq,op,async,target,status,(U)n,(U)fn);
 *__errno_location()=saved;int result=fn(target,p,n);int after=*__errno_location();
 dprintf(2,"FX3_GPE104_COMPLETE_RETURN tid=%ld tpidr=%#lx event=%lu ns=%lu seq=%u completion_source=%#x result=%d errno=%d real_function_returned=1 unchanged=1\n",tid,tp,id,gpe102_now(),seq,target,result,after);*__errno_location()=after;return result;
}
static int gpe104_dynamic(int(*fn)(unsigned,unsigned,void*),int(*peek)(U,void*,U),unsigned flags,unsigned module,void*arg,U caller){
 int saved=*__errno_location();U id=__atomic_add_fetch(&gpe104_serial,1,__ATOMIC_RELAXED),tp=gpe104_thread_pointer(),ns=gpe102_now();long tid=syscall(178);
 dprintf(2,"FX3_GPE104_DYNAMIC_ENTER tid=%ld tpidr=%#lx event=%lu ns=%lu flags=%#x module=%#x argument=%#lx caller=%#lx native_call_follows=1\n",tid,tp,id,ns,flags,module,(U)arg,caller);
 *__errno_location()=saved;int result=fn(flags,module,arg);int after=*__errno_location();unsigned q=0;int available=0;
 if(flags==0x4a){q=(unsigned)(U)arg;available=1;}else if(flags==0x2a&&result==0)available=peek((U)arg,&q,4);
 dprintf(2,"FX3_GPE104_DYNAMIC_RETURN tid=%ld tpidr=%#lx event=%lu ns=%lu flags=%#x module=%#x QID=%#x QID_available=%u result=%d errno=%d caller=%#lx owner_from_separate_kernel_probe=1 no_stat_msgq=1 no_extra_dynamic_id=1\n",tid,tp,id,gpe102_now(),flags,module,q,!!available,result,after,caller);
 *__errno_location()=after;return result;
}
static void gpe104_command_return(unsigned seq,unsigned op,unsigned source,int result){
 int saved=*__errno_location();long tid=syscall(178);U tp=gpe104_thread_pointer();
 dprintf(2,"FX3_GPE104_CMD_RETURN tid=%ld tpidr=%#lx ns=%lu seq=%u op=%u completion_source=%#x result=%d errno=%d call_path=adapter_return_to_original_Main unchanged=1\n",tid,tp,gpe102_now(),seq,op,source,result,saved);*__errno_location()=saved;
}
