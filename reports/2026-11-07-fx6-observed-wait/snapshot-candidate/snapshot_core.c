#include "snapshot_core.h"
#include <errno.h>
#include <inttypes.h>
#include <stddef.h>
#include <sys/uio.h>

int fx6_frame_valid(uint64_t fp,uint64_t sp,const struct fx6_stack *s,uint64_t page) {
 return page>=16 && !(page&(page-1)) && !(fp&15) && fp>=sp && fp>=s->low &&
        s->high>=16 && fp<=s->high-16 && (fp&(page-1))<=page-16;
}

static int wait_stop(struct fx6_ops *o,struct fx6_active *a,uint64_t budget,int cleanup) {
 uint64_t until=o->now()+budget;
 for (;;) {
  int status=0,error=0,r=o->wait(a->tid,&status,&error);
  if (r==a->tid) {
   if ((status&0xff)==0x7f) {
    a->stopped=1;
    /* Preserve an actual signal-delivery-stop; EVENT_STOP injects no signal.
       Group-stop state is preserved by Linux ptrace_unlink on DETACH. */
    a->signal=(status>>16)==0 ? (status>>8)&0xff : 0;
    fprintf(o->out,"FX6_WAIT_SNAPSHOT_STOP tid=%d status=0x%x detach_signal=%d\n",a->tid,status,a->signal);
    return 1;
   }
   fprintf(o->out,"FX6_WAIT_SNAPSHOT_GONE tid=%d status=0x%x\n",a->tid,status);
   a->seized=0;return 0;
  }
  if (r<0 && error!=EINTR) {
   fprintf(o->out,"FX6_WAIT_SNAPSHOT_WAIT_FAIL tid=%d errno=%d\n",a->tid,error);return 0;
  }
  if ((!cleanup && o->cancel()) || o->now()>=until) {
   fprintf(o->out,"FX6_WAIT_SNAPSHOT_WAIT_TIMEOUT tid=%d cleanup=%d\n",a->tid,cleanup);return 0;
  }
  o->pause();
 }
}

int fx6_cleanup_thread(struct fx6_ops *o,struct fx6_active *a) {
 if (!a->seized)return 0;
 int error=0;
 if (!a->stopped) {
  long r=o->trace(FX6_INTERRUPT,a->tid,0,0,&error);
  fprintf(o->out,"FX6_WAIT_SNAPSHOT_CLEANUP_INTERRUPT tid=%d rc=%ld errno=%d\n",a->tid,r,error);
  (void)wait_stop(o,a,250,1);
 }
 if (!a->seized)return 0;
 long r=o->trace(FX6_DETACH,a->tid,0,(uintptr_t)a->signal,&error);
 fprintf(o->out,"FX6_WAIT_SNAPSHOT_DETACH tid=%d rc=%ld errno=%d stopped=%d signal=%d\n",a->tid,r,error,a->stopped,a->signal);
 if (r==0) { a->seized=0;a->stopped=0;return 0; }
 /* Caller must exit after this failure. No EXITKILL is set: Linux tracer exit
    unlinks any remaining tracee instead of leaving a live attachment. */
 return -1;
}

static int peek_word(struct fx6_ops *o,int tid,uint64_t address,uint64_t *value) {
 int error=0;long r=o->trace(FX6_PEEKDATA,tid,(uintptr_t)address,0,&error);
 if (error) { fprintf(o->out,"FX6_WAIT_SNAPSHOT_PEEK_FAIL tid=%d address=0x%" PRIx64 " errno=%d\n",tid,address,error);return 0; }
 *value=(uint64_t)(unsigned long)r;return 1;
}

static int walk_frames(struct fx6_ops *o,int tid,const struct fx6_regs *r) {
 struct fx6_stack s={0};uint64_t fp=r->x[29],seen[20];unsigned count=0;
 if (!o->stack(tid,r->sp,&s)) {
  fprintf(o->out,"FX6_WAIT_SNAPSHOT_FP_END tid=%d reason=no_current_stack_map\n",tid);return 1;
 }
 fprintf(o->out,"FX6_WAIT_SNAPSHOT_STACK tid=%d sp=0x%" PRIx64 " low=0x%" PRIx64 " high=0x%" PRIx64 "\n",tid,r->sp,s.low,s.high);
 for (unsigned i=0;i<20 && !o->cancel();i++) {
  if (!fx6_frame_valid(fp,r->sp,&s,o->page_size)) {
   fprintf(o->out,"FX6_WAIT_SNAPSHOT_FP_END tid=%d reason=alignment_range_or_page fp=0x%" PRIx64 "\n",tid,fp);return 1;
  }
  for (unsigned j=0;j<count;j++)if (seen[j]==fp) {
   fprintf(o->out,"FX6_WAIT_SNAPSHOT_FP_END tid=%d reason=cycle\n",tid);return 1;
  }
  seen[count++]=fp;uint64_t next=0,lr=0;
  /* Two errno-checked, aligned word reads, both within this SP-containing
     anonymous/stack map and a single page. Never reads Sony heap objects. */
  if (!peek_word(o,tid,fp,&next) || !peek_word(o,tid,fp+8,&lr))return 1;
  fprintf(o->out,"FX6_WAIT_SNAPSHOT_FRAME tid=%d index=%u fp=0x%" PRIx64 " next_fp=0x%" PRIx64 " saved_lr=0x%" PRIx64 "\n",tid,i,fp,next,lr);
  if (!next || next<=fp) {
   fprintf(o->out,"FX6_WAIT_SNAPSHOT_FP_END tid=%d reason=chain_end_or_nonincreasing\n",tid);return next?1:0;
  }
  fp=next;
 }
 fprintf(o->out,"FX6_WAIT_SNAPSHOT_FP_END tid=%d reason=%s\n",tid,o->cancel()?"cancelled":"limit20");
 return o->cancel()?1:0;
}

int fx6_capture_thread(struct fx6_ops *o,struct fx6_active *a,int tid) {
 *a=(struct fx6_active){.tid=tid};int error=0,result=1;
 if (!o->belongs(tid)) { fprintf(o->out,"FX6_WAIT_SNAPSHOT_IDENTITY_FAIL tid=%d phase=before_seize\n",tid);return 1; }
 long rc=o->trace(FX6_SEIZE,tid,0,0,&error);
 fprintf(o->out,"FX6_WAIT_SNAPSHOT_SEIZE tid=%d rc=%ld errno=%d\n",tid,rc,error);
 if (rc<0)return 1;
 a->seized=1;
 if (!o->belongs(tid)) { fprintf(o->out,"FX6_WAIT_SNAPSHOT_IDENTITY_FAIL tid=%d phase=after_seize\n",tid);goto done; }
 rc=o->trace(FX6_INTERRUPT,tid,0,0,&error);
 fprintf(o->out,"FX6_WAIT_SNAPSHOT_INTERRUPT tid=%d rc=%ld errno=%d\n",tid,rc,error);
 if (rc<0 || !wait_stop(o,a,200,0))goto done;
 if (o->cancel())goto done;
 struct fx6_regs r={0};struct iovec iov={.iov_base=&r,.iov_len=sizeof r};
 rc=o->trace(FX6_GETREGSET,tid,FX6_NT_PRSTATUS,(uintptr_t)&iov,&error);
 if (rc<0 || iov.iov_len!=sizeof r) {
  fprintf(o->out,"FX6_WAIT_SNAPSHOT_REG_FAIL tid=%d rc=%ld errno=%d bytes=%zu expected=%zu\n",tid,rc,error,iov.iov_len,sizeof r);goto done;
 }
 fprintf(o->out,"FX6_WAIT_SNAPSHOT_REG tid=%d pc=0x%" PRIx64 " lr=0x%" PRIx64 " fp=0x%" PRIx64 " sp=0x%" PRIx64 " pstate=0x%" PRIx64,tid,r.pc,r.x[30],r.x[29],r.sp,r.pstate);
 for (unsigned i=0;i<=8;i++)fprintf(o->out," x%u=0x%" PRIx64,i,r.x[i]);
 fputc('\n',o->out);result=walk_frames(o,tid,&r);
done:
 if (fx6_cleanup_thread(o,a)<0)return -1;
 return result;
}
