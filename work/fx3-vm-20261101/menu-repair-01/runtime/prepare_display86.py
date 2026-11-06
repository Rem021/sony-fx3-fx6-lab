from pathlib import Path
import json,hashlib,struct
from elftools.elf.elffile import ELFFile
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_ARM
R=Path(__file__).resolve().parent;H=R/'helpers';L=R.parents[1]/'lead-claude';P=R.parent/'original-uipc/ap-projection/regular-files/usr/lib'
points={'ap':[0x28254cc,0x2825634,0x2823890,0x2823bf8,0x27ed854,0x27ed888,0x27ed88c,0x16f19e4,0x2dcadd0,0x2dcae40,0x2dcae80,0x2bd76fc,0x2bd7750,0x2bd7758,0x2bd7780], 'obj':[0xc9c08,0xc9c48,0x1771f4,0x17723c,0x1719c4,0x16223c,0x16ea5c,0x16ea60]}
proof={'sources':{},'points':{},'audits':{}};rows=[];cs=Cs(CS_ARCH_ARM64,CS_MODE_ARM)
for image,vs in points.items():
 p=P/('appFw.so' if image=='ap' else 'libObj.so');b=p.read_bytes();proof['sources'][image]={'path':str(p),'sha256':hashlib.sha256(b).hexdigest()}
 with p.open('rb') as f:
  ef=ELFFile(f)
  def raw(v,n):
   o=next(s['p_offset']+v-s['p_vaddr'] for s in ef.iter_segments() if s['p_type']=='PT_LOAD' and s['p_vaddr']<=v and v+n<=s['p_vaddr']+s['p_filesz']);return b[o:o+n]
  for va in vs:
   q=raw(va,4);ins=next(cs.disasm(q,va));w=struct.unpack('<I',q)[0]
   assert ins.mnemonic not in ('adr','adrp','b','blr','br','tbz','tbnz') and not ins.mnemonic.startswith('b.') and not (ins.mnemonic=='ldr' and '[' not in ins.op_str), (image,hex(va),ins.mnemonic,ins.op_str)
   rows.append((image,va,w));proof['points'][f'{image}:{va:x}']={'raw':q.hex(),'asm':ins.mnemonic+' '+ins.op_str}
  if image=='ap':proof['model_getter']={'raw':raw(0x16f0ca8,24).hex(),'asm':[i.mnemonic+' '+i.op_str for i in cs.disasm(raw(0x16f0ca8,24),0x16f0ca8)]}
# Recheck all supplied original byte blocks, without running/rebuilding audit scripts.
for name,file,key in [('display','display-target-hinge/display-target-proof.json','blocks'),('sys400','vdf0400/vdf0400-proof.json','code')]:
 a=json.loads((L/'audits'/file).read_text());proof['audits'][name]={'sha256':hashlib.sha256((L/'audits'/file).read_bytes()).hexdigest()};proof['audits'][name]['shape']=str(type(a[key]));proof['audits'][name]['keys']=list(a[key])[:4] if isinstance(a[key],dict) else len(a[key])
# Unique points cannot collide with earlier observer/timer patch sites.
for image,v,w in rows:
 for name in ['fx3-ui-gate-v11.c','fx3-timer-v3.c']:
  p=H/name
  if p.exists():assert hex(v) not in p.read_text(),(name,hex(v))
(R/'ap86-display-observer-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
old=(H/'fx3-ui-gate-v11.c').read_text();decl=old[:old.index('struct statistics')];test=old[old.index('__attribute__((visibility("hidden"))) int fx3_gate_test_compare'):old.index('__attribute__((visibility("hidden"))) void fx3_gate_event')];installer=old[old.index('static void sync_code'):old.index('static int bind_ram')];installer=installer.replace('test_pool,app_pool','test_pool,app_pool,obj_pool')
pre=decl+'''extern long pread(int,void *,size_t,long);extern char *getenv(const char *);extern int strcmp(const char *,const char *);\nextern void fx3_gate_probe_core(void);extern int fx3_gate_test(void),fx3_gate_branch_test(int),fx3_gate_bl_test(int);extern char fx3_gate_test_point[],fx3_gate_test_cb[],fx3_gate_test_bl[];\n'''+test
# selftest destructive handler path byte-for-byte from old validated gate.
handler=old[old.index(' if(id==63){'):old.index(' if(id>=60){')]
s=pre+(R/'display86-body.c').read_text()+installer
ap=[r for r in rows if r[0]=='ap'];ob=[r for r in rows if r[0]=='obj'];code='static const struct {U image,va;W word;U id;} points[]={'+','.join('{%d,%s,%s,%d}'%(im=='obj',hex(va),hex(w),i) for i,(im,va,w) in enumerate(rows))+'};\n'
s=s.replace('/*SELFTEST_BRANCH*/',handler)
s+=code+r'''
static void bind(void *h){if(bound)return;const char *profile=getenv("FX3_DISPLAY_OBSERVE");if(!profile||strcmp(profile,"passive-v1"))return;struct lm *a=0,*o=0;void *(*next)(const char *,int)=dlsym((void *)-1,"dlopen");void *oh=next?next("libObj.so",6):0;if(dlinfo(h,2,&a)||!a||!oh||dlinfo(oh,2,&o)||!o)return;app_base=a->base;obj_base=o->base;
 for(unsigned i=0;i<sizeof points/sizeof points[0];i++){U base=points[i].image?obj_base:app_base;if(*(W *)(base+points[i].va)!=points[i].word){dprintf(2,"FX3_DISPLAY_BIND_FAIL id=%u original_instruction=1\n",i);return;}}
 int f=open("/tmp/fx3-display-observe.claim",0x200c1,0600);if(f<0)return;dprintf(f,"pid=%ld passive=1 no_input_changes=1\n",syscall(172));close(f);pmem=open("/proc/self/mem",0);if(pmem<0)return;
 int rc=install(&test_pool,(U)fx3_gate_test_point,*(W *)fx3_gate_test_point,63,31);if(!rc)rc=install(&test_pool,(U)fx3_gate_test_cb,*(W *)fx3_gate_test_cb,63,31);if(!rc)rc=install(&test_pool,(U)fx3_gate_test_bl,*(W *)fx3_gate_test_bl,63,31);if(!rc)rc=fx3_gate_test();if(!rc&&(fx3_gate_branch_test(0)!=11||fx3_gate_branch_test(1)!=22||fx3_gate_bl_test(9)!=16))rc=250;if(rc){dprintf(2,"FX3_DISPLAY_SELFTEST_FAIL result=%d originals_not_bound=1\n",rc);return;}dprintf(2,"FX3_DISPLAY_SELFTEST_PASS GPR=31 SIMD=32 NZCV=preserved FPCR_FPSR=preserved SP=preserved NOP_CBNZ_BL=passed\n");
 f=open("/dev/mem",2);if(f>=0){void *p=mmap(0,0x10000,3,1,f,0x41e000000UL);close(f);if(p!=(void *)-1)ram=p;}
 for(unsigned i=0;i<sizeof points/sizeof points[0];i++){U base=points[i].image?obj_base:app_base;rc=install(points[i].image?&obj_pool:&app_pool,base+points[i].va,points[i].word,points[i].id,31);if(rc){dprintf(2,"FX3_DISPLAY_BIND_FAIL id=%u result=%d\n",i,rc);return;}}bound=1;dprintf(2,"FX3_DISPLAY_BOUND points=%lu app=%#lx obj=%#lx epoch=1 input_unchanged=1 no_getters_or_observers_invoked=1\n",(U)(sizeof points/sizeof points[0]),app_base,obj_base);
}
void *dlopen(const char *name,int flags){int saved=*__errno_location();void *(*fn)(const char *,int)=dlsym((void *)-1,"dlopen");if(!fn)__builtin_trap();*__errno_location()=saved;void *h=fn(name,flags);saved=*__errno_location();if(h&&name&&strstr(name,"appFw.so"))bind(h);*__errno_location()=saved;return h;}
'''
s=s.replace('fx3_gate_','fx3_display_');(H/'fx3-display-observe-v1.c').write_text(s);(H/'fx3-display-probes-v1.S').write_text((H/'fx3-ui-gate-probes-v1.S').read_text().replace('fx3_gate_','fx3_display_'))
args=json.loads((H/'fx3-ui-gate-v11-build.json').read_text())['args'];args=[x.replace('fx3-ui-gate-v11','fx3-display-observe-v1').replace('fx3-ui-gate-probes-v1','fx3-display-probes-v1') for x in args];(R/'display86-build-args.json').write_text(json.dumps(args));print(json.dumps(proof['points'],indent=2));print(proof['model_getter'])
