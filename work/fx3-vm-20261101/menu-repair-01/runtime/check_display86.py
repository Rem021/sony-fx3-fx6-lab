from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-display-observe-v1.c').read_text();body=s[s.index('static U app_base'):s.index('static void sync_code')];a=body.index(' if(id==63){');b=body.index(' if(id>=23){');body=body[:a]+body[b:];body=body.replace('__asm__ volatile("dmb sy":::"memory");','')
pre=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
typedef unsigned long U;typedef unsigned W;struct ctx{U pc,continuation,id,objreg;};static int e=42;static unsigned reads;struct cell{U address,value;}cells[128];static unsigned cells_count;
static void put(U a,U v){cells[cells_count++]=(struct cell){a,v};}
static long test_pread(int fd,void *out,U n,long at){assert(fd==3&&n<=24);reads++;memset(out,0,n);for(unsigned j=0;j<n;j++){int found=0;for(unsigned i=0;i<cells_count;i++)if((U)at+j>=cells[i].address&&(U)at+j<cells[i].address+8){((unsigned char *)out)[j]=((unsigned char *)&cells[i].value)[(U)at+j-cells[i].address];found=1;break;}if(!found)return -1;}return n;}
static long test_syscall(long n,...){assert(n==172||n==178);return n==172?221:346;}static int *test_errno(void){return &e;}
#define pread test_pread
#define syscall test_syscall
#define __errno_location test_errno
'''
post=r'''
static void event(unsigned id,U r[31]){struct ctx c={0,0,id,31};U before[31];memcpy(before,r,sizeof before);fx3_display_event(&c,r);assert(!memcmp(before,r,sizeof before)&&e==42);}
int main(void){pmem=3;app_base=0x10000000;obj_base=0x20000000;U r[31]={0};put(app_base+0x835ea28,0);put(app_base+0x835ea3c,0);put(app_base+0x835ea50,0);put(app_base+0x835ea64,0);put(app_base+0x835ea78,0);put(app_base+0x822c9f4,7);put(app_base+0x822c71c,2);put(app_base+0x47ce0a8,8);put(app_base+0x834375c,1);event(0,r);assert(state[5]==7&&state[6]==2&&state[7]==8&&state[8]==1);
 r[21]=7;r[22]=1;r[20]=1;event(4,r);assert(display_category==7&&state[17]==1&&state[18]==1);event(5,r);event(6,r);
 put(0x30000000+0x8ac,0);put(0x30000000+0x7c8,0x300007d0);put(obj_base+0x2cf100,0x33300000);r[0]=0x30000000;event(17,r);assert(!state[12]&&state[15]==0x33300000);
 r[0]=0x34000000;event(21,r);r[0]=0;event(22,r);r[0]=1;event(22,r);assert(dirty_zero==1&&dirty_nonzero==1&&state[28]==0x34000000);
 r[0]=0x35000000;r[1]=0x71c4;r[2]=0x36000000;put(r[2],0);put(r[2]+8,0x7fffffff);put(r[2]+16,0);event(15,r);r[0]=0x7fffffff;event(16,r);assert(cache_key==0);
 r[0]=0x37000000;put(r[0]+0x1bc,0);put(r[0]+0x158,0x37100000);put(r[0]+0x160,0x37100018);put(0x37100000,0x38000000);put(0x37100008,2);put(0x37100010,3);put(0x38000000,4);event(8,r);r[0]=0;event(9,r);event(10,r);r[19]=0x39000000;r[20]=0x37000000;put(r[19]+0x10,r[19]+0x10);put(r[19]+0x20,0);put(r[19]+0x88,r[20]);event(11,r);event(12,r);event(13,r);event(14,r);assert(state[25]==1&&state[26]==1&&state[27]==1&&!sys_task&&!sys_stage);
 puts("DISPLAY_OBSERVER_PASS actual_event_logic/read_only_originals/no_getters_or_virtual_calls/args_errno_preserved/category_direction_separate/cache_sentinel/empty_root/actual_dirty_return/SYS400_completion_next_bounded");}
'''
p=H/'check-display-observer-v1.c';p.write_text(pre+body+post);args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];q=subprocess.run(args,text=True,capture_output=True);assert not q.returncode,q.stderr;q=subprocess.run([str(p.with_suffix(''))],text=True,capture_output=True);(H/'display-observer-host-check.json').write_text(json.dumps({'args':args,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr[-6000:],'helper_sha256':hashlib.sha256(s.encode()).hexdigest(),'scope':'Actual normal event logic host-mocked; A64 trampoline full-register preservation requires guest selftest'},indent=2)+'\n');assert not q.returncode,q.stderr;print(q.stdout)
