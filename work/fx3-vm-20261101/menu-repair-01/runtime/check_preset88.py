from pathlib import Path
import subprocess,json
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-preset-context-v1.c').read_text()
def fn(start):
 a=s.index(start);b=s.index('{',a);lev=1;i=b+1
 while lev:
  if s[i]=='{':lev+=1
  elif s[i]=='}':lev-=1
  i+=1
 return s[a:i]
e=fn('__attribute__((visibility("hidden"))) void fx3_display_event');a=e.index(' if(id==63)');b=e.index(' if(id==24)');e=e[:a]+e[b:]
body=r'''
#include <assert.h>
#include <string.h>
#include <stdarg.h>
typedef unsigned long U;typedef unsigned int W;struct ctx{U pc,continuation,id,objreg;};static int pmem=1,err;static U epoch;static __thread U preset_task,preset_tid,preset_epoch,preset_values[4];static __thread unsigned preset_valid;static W data[4]={11,22,33,44};static U tid=352;static int readable=1;
static int*__errno_location(void){return &err;}static long syscall(long n,...){assert(n==178);return tid;}static long pread(int fd,void*p,U n,long off){assert(fd==1&&off==0x1001bc&&n==16);if(!readable)return -1;memcpy(p,data,16);return 16;}static int dprintf(int fd,const char*f,...){assert(fd==2);(void)f;return 0;}
'''+fn('static int peek(')+'\n'+fn('int fx3_timecode_preset_context(')+'\n'+e+r'''
int main(void){U out[7],regs[31]={0x100000};struct ctx c={0,0,24,31};assert(!fx3_timecode_preset_context(out,7));fx3_display_event(&c,regs);assert(preset_valid&&preset_epoch==1&&fx3_timecode_preset_context(out,7)==7&&out[0]==0x100000&&out[1]==352&&out[2]==1&&out[3]==11&&out[6]==44);assert(!fx3_timecode_preset_context(out,6));for(unsigned i=0;i<4;i++){data[i]++;assert(!fx3_timecode_preset_context(out,7));data[i]--;}tid++;assert(!fx3_timecode_preset_context(out,7));tid--;c.id=37;fx3_display_event(&c,regs);assert(!preset_valid&&!fx3_timecode_preset_context(out,7));c.id=24;readable=0;fx3_display_event(&c,regs);assert(!preset_valid&&!fx3_timecode_preset_context(out,7));readable=1;fx3_display_event(&c,regs);assert(fx3_timecode_preset_context(out,7)==7&&out[2]==3);return 0;}
''';p=H/'check-preset88.c';p.write_text(body);a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];q=subprocess.run(a,capture_output=True,text=True);assert not q.returncode,q.stderr;q=subprocess.run([str(p.with_suffix(''))],capture_output=True,text=True);(H/'preset88-host-check.json').write_text(json.dumps({'args':a,'exit':q.returncode,'stderr':q.stderr,'scope':'Actualcontextentry/RET/getterextracted;task4words/currentthread/epoch/recheck/readfailure/retire. Registerselftest originalASMwillruninguest'},indent=2)+'\n');assert not q.returncode,q.stderr;print('PRESET_CONTEXT88_PASS')
