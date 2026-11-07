#include "snapshot_core.h"
#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <string.h>
#include <sys/uio.h>

static int mode,seizes,interrupts,detaches,reads,registers,signal_out,cancelled,identities;
static uint64_t clock_ms;
static long fake_trace(int request,int tid,uintptr_t address,uintptr_t data,int *error) {
 assert(tid==224);*error=0;
 if (request==FX6_SEIZE) { seizes++;if(mode==1){*error=EPERM;return -1;}return 0; }
 if (request==FX6_INTERRUPT) { interrupts++;return 0; }
 if (request==FX6_DETACH) { detaches++;signal_out=(int)data;if(mode==7){*error=ESRCH;return -1;}return 0; }
 if (request==FX6_GETREGSET) {
  registers++;assert(address==1);struct iovec *i=(struct iovec*)data;
  if(mode==3){*error=EIO;return -1;}
  struct fx6_regs *r=i->iov_base;memset(r,0,sizeof *r);r->sp=0x1000;r->pc=0x8000;r->x[29]=0x1100;r->x[30]=0x9000;
  if(mode==11)r->x[29]=0x1ff8;
  if(mode==4)i->iov_len=8;
  return 0;
 }
 assert(request==FX6_PEEKDATA);reads++;
 assert(address>=0x1000 && address<0x2000);
 if(mode==5){*error=EIO;return -1;}
 if(mode==10)return (address&15)?-1:(long)(address+16);
 if(address==0x1100)return mode==8?0x1100:0;
 assert(address==0x1108);return -1; /* legitimate all-ones word, errno==0 */
}
static int fake_wait(int tid,int *status,int *error) {
 *error=0;if(mode==2)return 0;
 if(mode==13){*error=ECHILD;return -1;}
 *status=mode==6 ? (10<<8)|0x7f : (128<<16)|(5<<8)|0x7f;
 return tid;
}
static uint64_t fake_now(void) { return clock_ms; }
static void fake_pause(void) { clock_ms++; }
static int fake_cancel(void) { return cancelled; }
static int fake_belongs(int tid) { assert(tid==224);identities++;return mode==15?0:(mode==16?identities==1:1); }
static int fake_stack(int tid,uint64_t sp,struct fx6_stack *s) {
 assert(tid==224 && sp==0x1000);s->low=0x1000;s->high=0x2000;return mode==12?0:1;
}
static struct fx6_ops setup(int test_mode) {
 mode=test_mode;seizes=interrupts=detaches=reads=registers=signal_out=cancelled=identities=0;clock_ms=0;
 FILE *out=tmpfile();assert(out);
 return (struct fx6_ops){fake_trace,fake_wait,fake_now,fake_pause,fake_cancel,fake_belongs,fake_stack,out,4096};
}
int main(void) {
 struct fx6_stack s={0x1000,0x3000};
 assert(fx6_frame_valid(0x1100,0x1000,&s,4096));
 assert(!fx6_frame_valid(0x1108,0x1000,&s,4096));
 assert(!fx6_frame_valid(0xff0,0x1000,&s,4096));
 assert(!fx6_frame_valid(0x3000,0x1000,&s,4096));
 assert(!fx6_frame_valid(UINT64_MAX-15,0,&s,4096));
 assert(!fx6_frame_valid(0x1100,0x1000,&s,3));
 for(int t=0;t<=16;t++) {
  struct fx6_ops o=setup(t);struct fx6_active a={0};int result=fx6_capture_thread(&o,&a,224);
  assert(seizes==(t==15?0:1));
  if(t==15) { assert(result==1 && !detaches);fclose(o.out);continue; }
  if(t==1) { assert(detaches==0 && registers==0 && result==1); }
  else {
   assert(detaches==1);
   if(t==2)assert(registers==0 && clock_ms==450 && result==1);
   if(t==3 || t==4)assert(reads==0 && result==1);
   if(t==5)assert(reads==1 && result==1);
   if(t==6)assert(signal_out==10);
   if(t==7)assert(result==-1 && a.seized);
   if(t==0)assert(reads==2 && result==0);
   if(t==8)assert(reads==2 && result==1);
   if(t==10)assert(reads==40 && result==0);
   if(t==11 || t==12)assert(reads==0 && result==1);
   if(t==13 || t==16)assert(registers==0 && result==1);
  }
  fclose(o.out);
 }
 struct fx6_ops o=setup(0);struct fx6_active a={0};cancelled=1;
 assert(fx6_capture_thread(&o,&a,224)==1 && detaches==1 && !a.seized);fclose(o.out);
 puts("snapshot core: 18 state scenarios and frame boundary checks passed");return 0;
}
