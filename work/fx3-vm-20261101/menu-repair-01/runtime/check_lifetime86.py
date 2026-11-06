from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';s=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "fx3-osd-life-core-v1.h"
static struct lp_model m;
int main(void){assert(lp_role(0x8280074d,12,0xf1db8)==0x1002);assert(lp_role(0x8280084d,36,0xf1e44)==0x1003);assert(lp_role(0x8280084e,8,0xf1d2c)==0x1005);assert(!lp_role(0x8280084e,8,0xf1d2d));assert(!lp_role(0x8280084d,8,0xf1d2c));assert(lp_return(&m,0,1,12,0x1002,-1)<0&&!m.live);assert(lp_return(&m,0x1000,0x8280074d,12,0x1002,0)==0&&m.live==1);assert(lp_sent(&m,0x1000,0x8280074d,0x1002)==0&&m.sends==1);assert(lp_freed(&m,0x1000,1,0)<0&&m.live==1);assert(lp_freed(&m,0x1000,0x8280074d,-1)<0&&m.live==1);assert(lp_return(&m,0x1000,0x8280074d,12,0x1002,0)==0&&m.reuses==1&&m.live==1);assert(lp_freed(&m,0x1000,0x8280074d,0)==0&&!m.live&&m.frees==1);assert(!lp_control(&m,0x1005,10));assert(lp_control(&m,0x1005,20)<0&&m.pair_started==10);assert(!lp_expired(&m,2000000009UL)&&lp_expired(&m,2000000010UL));assert(lp_descriptor(&m,0x1003)<0&&m.pending==0x1005);assert(!lp_descriptor(&m,0x1005)&&!m.pending);assert(!lp_control(&m,0x1003,11)&&m.sequence==2);m.failed=1;assert(!lp_expired(&m,9999999999UL)&&lp_descriptor(&m,0x1003)<0);puts("LIFETIME_CORE_PASS native_constructor_exact/alloc_failure/no_userfree_vs_native_reuse_distinct/wrong_free_unchanged/paired_types/deadline_no_duplicate_reset/failed_no_ack");}
''';p=H/'check-osd-life-core-v1.c';p.write_text(s);a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];q=subprocess.run(a,text=True,capture_output=True);assert not q.returncode,q.stderr;q=subprocess.run([str(p.with_suffix(''))],text=True,capture_output=True);(H/'osd-lifetime-core-host-check.json').write_text(json.dumps({'args':a,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr},indent=2)+'\n');assert not q.returncode,q.stderr;print(q.stdout)
# Test the actual exported timeout gate without native side effects.
src=(H/'fx3-osd-headless-v4.c').read_text();gate=src[src.index('int fx3_osd_timeout_pair('):];pre=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "fx3-osd-core-v3.h"
static struct ho_model hm;static unsigned observer_ready=1;static long owner=123;static unsigned publications;
static int enabled(void){return 1;}static void own_lock(void){}static void own_unlock(void){}static long syscall(long n){assert(n==172);return 123;}static void publish_status(void){publications++;}
''';post=r'''
int main(void){hm.stage=1;hm.pending=0x1005;hm.seq=1358;assert(fx3_osd_timeout_pair(0x1005,1357)<0&&!hm.failed&&!publications);assert(fx3_osd_timeout_pair(0x1003,1358)<0&&!hm.failed);hm.stage=2;assert(fx3_osd_timeout_pair(0x1005,1358)<0&&!hm.failed);hm.stage=1;assert(!fx3_osd_timeout_pair(0x1005,1358)&&hm.failed&&publications==1);unsigned char ack[8];assert(ho_prepare_ack(&hm,ack)<0&&fx3_osd_timeout_pair(0x1005,1358)<0);puts("PAIR_TIMEOUT_GATE_PASS exact_pending_and_prior_seq/stale_timer_cannot_poison_new_batch/no_original_semaphore_or_ACK");}
''';p=H/'check-osd-timeout-gate-v4.c';p.write_text(pre+gate+post);a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];q=subprocess.run(a,text=True,capture_output=True);assert not q.returncode,q.stderr;q=subprocess.run([str(p.with_suffix(''))],text=True,capture_output=True);(H/'osd-timeout-gate-host-check.json').write_text(json.dumps({'args':a,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr,'helper_sha256':hashlib.sha256(src.encode()).hexdigest()},indent=2)+'\n');assert not q.returncode,q.stderr;print(q.stdout)
