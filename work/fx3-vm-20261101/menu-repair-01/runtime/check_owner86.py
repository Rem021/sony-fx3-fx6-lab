from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';src=(H/'fx3-osd-headless-v5.c').read_text()
pre=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <unistd.h>
typedef unsigned long U;
#include "fx3-osd-core-v3.h"
#include "fx3-osd-owner-core-v1.h"
static struct ho_model hm;static struct qo_model ownership;static void *owned_descriptor;static unsigned owned_queue;
static unsigned char configs[256*96+96];static U config_version;
static unsigned char body[4096];static unsigned qsrc,nbytes;static int receive_result,free_result;static unsigned frees,receives;
static unsigned sz(void *p){assert(p==body);return nbytes;}static unsigned source(void *p){assert(p==body);return qsrc;}
static int freem(unsigned q,void *p){assert(q==HO_CONTROL||q==HO_PIXELS||q==HO_META);assert(p==body);int i=qo_index(q);assert(!ownership.leases[i].pointer);frees++;return free_result;}
static int receive(unsigned q,void **p,long t){assert(t==10);assert(q==HO_CONTROL||q==HO_PIXELS||q==HO_META);receives++;*p=body;return receive_result;}
static int (*hreceive)(unsigned,void **,long)=receive;static int (*hfree)(unsigned,void *)=freem;static unsigned (*hsize)(void *)=sz,(*hsource)(void *)=source;
static void own_lock(void){}static void own_unlock(void){}static void publish_status(void){}static int fail(const char *p,int r){(void)p;(void)r;hm.failed=1;return -1;}
'''
actual=src[src.index('static void owner_raw('):src.index('static void *worker(void *unused)')]
post=r'''
static void reset(unsigned op,unsigned n,unsigned src){memset(&hm,0,sizeof hm);memset(&ownership,0,sizeof ownership);memset(body,0,sizeof body);body[0]=op;body[1]=op>>8;nbytes=n;qsrc=src;frees=receives=0;free_result=receive_result=0;owned_descriptor=0;owned_queue=0;}
static void accepted(unsigned dst){U stamp=qo_register(&ownership,dst,qsrc,body,nbytes,(U)body,hm.seq+1);assert(stamp);assert(qo_match(&ownership,dst,qsrc,body,nbytes,(U)body,hm.seq+1)==1);assert(!qo_confirm(&ownership,dst,(U)body,stamp,0));}
int main(void){
 reset(0x1000,80,0x9088076b);assert(!owner_receive_step()&&ownership.GUI==1&&frees==1&&hm.stage==0);
 reset(0x1001,96,0x9088076b);body[8]=255;body[28]=16;assert(!owner_receive_step()&&ownership.GUI==1&&frees==1);
 reset(0x1001,96,0x9088076b);body[28]=17;assert(!owner_receive_step()&&ownership.unknown==1&&frees==1&&!hm.stage);
 reset(0x1004,16,0x9088076b);assert(!owner_receive_step()&&ownership.GUI==1&&frees==1);
 reset(0x9999,4096,12);assert(!owner_receive_step()&&ownership.unknown==1&&frees==1&&!hm.stage);
 reset(0x1002,12,HO_AP);body[8]=3;body[9]=16;assert(!owner_receive_step()&&ownership.stale==1&&frees==1&&!hm.stage);
 reset(0x1002,12,HO_AP);body[8]=3;body[9]=16;accepted(HO_CONTROL);assert(!owner_receive_step()&&frees==1&&hm.stage==1&&hm.pending==0x1003);
 memset(body,0,sizeof body);body[0]=3;body[1]=16;nbytes=36;body[12]=1;body[20]=1;body[22]=1;accepted(HO_PIXELS);assert(!owner_receive_step()&&frees==1&&hm.stage==2&&owned_descriptor==body&&owned_queue==HO_PIXELS);assert(!owner_release(owned_queue,owned_descriptor,"after-capture"));assert(frees==2&&ownership.freed[1]==1);
 reset(0x1002,12,HO_AP);body[8]=5;body[9]=16;accepted(HO_CONTROL);free_result=-4;assert(owner_receive_step()<0&&hm.failed&&ownership.errors==1);
 reset(0,4097,0);assert(owner_receive_step()<0&&frees==1&&hm.failed);/* no oversize read */
 reset(0,8,0);receive_result=-1021;assert(!owner_receive_step()&&frees==1&&!hm.failed);
 /* Failed send / wrong sequence / bytes cannot become accepted. */
 reset(0x1002,12,HO_AP);body[8]=5;body[9]=16;U stamp=qo_register(&ownership,HO_CONTROL,qsrc,body,nbytes,(U)body,1);assert(!qo_confirm(&ownership,HO_CONTROL,(U)body,stamp,-1));assert(qo_match(&ownership,HO_CONTROL,qsrc,body,nbytes,(U)body,1)<0);qo_retire(&ownership,HO_CONTROL,(U)body);accepted(HO_CONTROL);assert(qo_match(&ownership,HO_CONTROL,qsrc,body,nbytes,(U)body,2)<0);body[2]=1;assert(qo_match(&ownership,HO_CONTROL,qsrc,body,nbytes,(U)body,1)<0);
 puts("OWNER_RECEIVER_PASS actual_native_receive/free_order/GUI_frozen/unknown_fullraw_no_reply/stale_no_ACK/current_exact_lease/retire_before_free/no_oversize_read/failure_poison");}
'''
p=H/'check-osd-owner-v5.c';p.write_text(pre+actual+post);args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];c=subprocess.run(args,text=True,capture_output=True);assert not c.returncode,c.stderr;c=subprocess.run([str(p.with_suffix(''))],text=True,capture_output=True)
# Static exact placement check of all worker failure cleanup paths, preserved native capture implementation.
worker=src[src.index('static void *worker(void *unused)'):src.index('static void observe(')]
assert worker.index('descriptor-after-copy-release')<worker.index('ho_commit(')<worker.index('halloc(HO_AP')
assert 'capture-failure-no-ACK' in worker and 'metadata-failure-no-ACK' in worker
old=(H/'fx3-osd-headless-v4.c').read_text();a='static int capture(';b='static void ring_commit(';assert src[src.index(a):src.index(b)]==old[old.index(a):old.index(b)]
(H/'osd-owner-v5-host-check.json').write_text(json.dumps({'args':args,'exit':c.returncode,'stdout':c.stdout[-2000:],'stderr':c.stderr[-2000:],'helper_sha256':hashlib.sha256(src.encode()).hexdigest(),'capture_unchanged':True,'worker_original_free_precedes_commit_and_ACK':True},indent=2)+'\n');assert not c.returncode,c.stderr;print(c.stdout[-1000:])
