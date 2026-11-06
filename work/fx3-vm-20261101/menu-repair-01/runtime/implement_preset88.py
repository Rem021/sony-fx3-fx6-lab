from pathlib import Path
import json,subprocess,os,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';old=(H/'fx3-display-observe-v4.c').read_text()
def function(start):
 a=old.index(start);br=old.index('{',a);level=1;i=br+1
 while level:
  if old[i]=='{':level+=1
  elif old[i]=='}':level-=1
  i+=1
 return old[a:i]
header=old[:old.index('static U app_base')]
header=header.replace('extern long pread(int,void *,size_t,long);','extern long pread(int,void *,size_t,long);')
event=old[old.index('__attribute__((visibility("hidden"))) void fx3_display_event'):old.index(' if(id>=40)')]
# Prefix retains the entire original register-clobber selftest (id63).
event+='''
 if(id==24){preset_valid=0;preset_task=r[0];preset_tid=syscall(178);preset_epoch=__atomic_add_fetch(&epoch,1,__ATOMIC_RELAXED);W values[4];if(peek(preset_task+0x1bc,values,16)){for(unsigned j=0;j<4;j++)preset_values[j]=values[j];preset_valid=1;}dprintf(2,"FX3_PRESET_CONTEXT_CAPTURE epoch=%lu tid=%lu task=%#lx readable=%u words=%#lx,%#lx,%#lx,%#lx original_entry=2dca610\\n",preset_epoch,preset_tid,preset_task,preset_valid,preset_values[0],preset_values[1],preset_values[2],preset_values[3]);}
 if(id==37){preset_valid=0;dprintf(2,"FX3_PRESET_CONTEXT_RETIRED epoch=%lu tid=%lu original_RET=2dca6e0\\n",preset_epoch,preset_tid);}
 *__errno_location()=saved;
}
'''
setup='''static U app_base;static int bound,pmem=-1;static U epoch;static __thread U preset_task,preset_tid,preset_epoch,preset_values[4];static __thread unsigned preset_valid;
'''+function('static int peek(')+'\n'+function('int fx3_timecode_preset_context(')+'\n'+event+'\n'+function('static void sync_code(')+'''
struct pool{unsigned char*p;U used;};static struct pool test_pool,app_pool;
'''+function('static W branch(')+'\n'+function('static W literal(')+'\n'+function('static int allocate_pool(')+'\n'+function('static int install(')+'\n'
binder='''static void bind(void*h){if(bound)return;const char*profile=getenv("FX3_DISPLAY_OBSERVE");if(!profile||strcmp(profile,"passive-v1"))return;struct lm*a=0;if(dlinfo(h,2,&a)||!a)return;app_base=a->base;pmem=open("/proc/self/mem",0);if(pmem<0)return;
 U addresses[2]={app_base+0x2dca610,app_base+0x2dca6e0};W words[2]={0xa9bb7bfd,0xd65f03c0};for(unsigned i=0;i<2;i++){W current;if(!peek(addresses[i],&current,4)||current!=words[i]){dprintf(2,"FX3_PRESET_CONTEXT_BIND_REJECT point=%u reason=original_word\\n",i);return;}}
 int rc=install(&test_pool,(U)fx3_display_test_point,*(W*)fx3_display_test_point,63,31);if(!rc)rc=install(&test_pool,(U)fx3_display_test_cb,*(W*)fx3_display_test_cb,63,31);if(!rc)rc=install(&test_pool,(U)fx3_display_test_bl,*(W*)fx3_display_test_bl,63,31);if(!rc)rc=fx3_display_test();if(!rc&&(fx3_display_branch_test(0)!=11||fx3_display_branch_test(1)!=22||fx3_display_bl_test(9)!=16))rc=250;if(rc){dprintf(2,"FX3_PRESET_CONTEXT_BIND_REJECT reason=selftest result=%d\\n",rc);return;}
 dprintf(2,"FX3_PRESET_CONTEXT_SELFTEST_PASS GPR=31 SIMD=32 NZCV=preserved SP=preserved originalASM=1\\n");rc=install(&app_pool,addresses[0],words[0],24,31);if(!rc)rc=install(&app_pool,addresses[1],words[1],37,31);if(rc){dprintf(2,"FX3_PRESET_CONTEXT_BIND_REJECT reason=install result=%d\\n",rc);return;}bound=1;dprintf(2,"FX3_PRESET_CONTEXT_BOUND points=2 original0404entry_and_RET=1 no_libObj_pool=1 no_display_observation=1 same_task_fourwords_tid_epoch_recheck=1\\n");}
'''
source=header+setup+binder+function('void *dlopen(')+'\n';p=H/'fx3-preset-context-v1.c';p.write_text(source)
b=json.loads((H/'fx3-display-observe-v4-build.json').read_text());args=[str(a).replace('fx3-display-observe-v4','fx3-preset-context-v1') for a in b['args']];q=subprocess.run(args,env=dict(os.environ,ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache')),text=True,capture_output=True);assert not q.returncode,q.stderr;(H/'fx3-preset-context-v1-build.json').write_text(json.dumps({'args':args,'exit':0,'sha256':hashlib.sha256(p.with_suffix('.so').read_bytes()).hexdigest(),'source_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'scope':'RemoveddisplayDSO; retainonlymandatory0404context originalentry+RET2points. ExactsamefullGPR/SIMDASM, testsandapp64MiBpool; noObjpool/noWidget/panel/queue/displaygetters. Getter rechecks currenttask fourwords+tid+epoch/lifetime.'},indent=2)+'\n');print('PRESET_CONTEXT_ONLY_BUILT')
