from pathlib import Path
import json,subprocess,os,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';old=H/'fx3-gpe-observe-v14-guard-v1.c';new=H/'fx3-gpe-observe-v15-earlybind.c';s=old.read_text();s=s.replace('static void bind(void *h) {\n if(__atomic_test_and_set(&binding_lock,__ATOMIC_ACQUIRE))return;\n bind_impl(h);\n __atomic_clear(&binding_lock,__ATOMIC_RELEASE);\n}', '''static int bind(void *h) {
 if(__atomic_test_and_set(&binding_lock,__ATOMIC_ACQUIRE))return -2;
 bind_impl(h);int result=__atomic_load_n(&armed,__ATOMIC_ACQUIRE)?0:-1;
 __atomic_clear(&binding_lock,__ATOMIC_RELEASE);return result;
}''');assert 'static int bind(void *h)' in s
needle='#ifdef FX3_GPE_HOST_TEST\n#define dlopen host_interposer_dlopen';assert needle in s
addition=r'''
/* GpeInit ddcc creates exact gpe0_info/1_info before lazy dlopen binding
 * can finish on another thread. Do not let these original worker entries
 * run until the existing software setup/GOT binding is completely armed. */
static int (*native_create_thread)(const void *);
#ifdef FX3_GPE_HOST_TEST
static int (*host_early_bind_override)(void *);
#endif
static int match_gpe_thread(const void *info,U base){
 if(!base||((U)info!=base+0x297c0&&(U)info!=base+0x297e8))return -1;
 const U *w=info;int g=(U)info==base+0x297c0?0:1;
 if(w[0]!=base+(g?0x1574e:0x15759)||w[1]!=4||w[2]!=base+(g?0xdce4:0xdcb0)||w[3]||w[4]!=0x288)return -1;
 return g;
}
int osal_create_thread(const void *info){
 int saved=*__errno_location();int(*fn)(const void *)=__atomic_load_n(&native_create_thread,__ATOMIC_ACQUIRE);
 if(!fn){fn=dlsym((void *)-1,"osal_create_thread");if(!fn)_exit(126);__atomic_store_n(&native_create_thread,fn,__ATOMIC_RELEASE);}
 struct app_dl_info location={0};int g=-1;
 if(info&&dladdr(info,&location))g=match_gpe_thread(info,(U)location.base);
 if(g>=0){
  void *(*open_next)(const char *,int)=__atomic_load_n(&loader,__ATOMIC_ACQUIRE);
  if(!open_next){open_next=dlsym((void *)-1,"dlopen");if(open_next)__atomic_store_n(&loader,open_next,__ATOMIC_RELEASE);}
  void*h=open_next?open_next("libgpe.so",5):0;struct lm*map=0;
  if(!h||dlinfo(h,2,&map)||!map||map->base!=(U)location.base){dprintf(2,"FX3_GPE_EARLY_BIND_REJECT gpe=%d reason=original_NOLOAD_identity native_thread_not_created=1\n",g);_exit(126);}
  unsigned yielded=0;int rc;
  for(;;){
#ifdef FX3_GPE_HOST_TEST
   rc=host_early_bind_override?host_early_bind_override(h):bind(h);
#else
   rc=bind(h);
#endif
   if(rc!=-2)break;yielded++;syscall(124);
  }
  if(rc||!__atomic_load_n(&armed,__ATOMIC_ACQUIRE)){dprintf(2,"FX3_GPE_EARLY_BIND_REJECT gpe=%d reason=existing_bind_failed native_thread_not_created=1 result=%d\n",g,rc);_exit(126);}
  dprintf(2,"FX3_GPE_EARLY_THREAD_GATE gpe=%d info_relative=%#lx entry_relative=%#lx armed=1 wait_yields=%u original_thread_create_follows=1 original_args_unchanged=1 no_register_model=1\n",g,(U)info-(U)location.base,((const U*)info)[2]-(U)location.base,yielded);
 }
 *__errno_location()=saved;int result=fn(info);int after=*__errno_location();
 if(g>=0)dprintf(2,"FX3_GPE_EARLY_THREAD_RETURN gpe=%d result=%d errno=%d native_return=1\n",g,result,after);
 *__errno_location()=after;return result;
}
'''
s=s.replace(needle,addition+needle).replace('adapter=v14 approx_model','adapter=v15 early_thread_bind=1 approx_model');new.write_text(s)
b=json.loads((H/'fx3-gpe-observe-v14-guard-v1-build.json').read_text());args=[str(a).replace('fx3-gpe-observe-v14-guard-v1','fx3-gpe-observe-v15-earlybind') for a in b['args']];q=subprocess.run(args,env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache')),text=True,capture_output=True);assert not q.returncode,q.stderr;(H/'fx3-gpe-observe-v15-earlybind-build.json').write_text(json.dumps({'args':args,'exit':0,'previous_source_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(new.with_suffix('.so').read_bytes()).hexdigest(),'scope':'Only exactoriginal gpe0_info297c0/entrydcb0 or gpe1_info297e8/entrydce4 creation gateduntil existing setup/GOT binding armed. Originalosal_create_thread args/result/errno forwarded; raster/nativeFIFO/completion identicalv14guard; noMMIOmodel.'},indent=2)+'\n');print('GPEv15 BUILT')
