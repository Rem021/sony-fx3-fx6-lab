
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "fx3-osd-core-v3.h"
static struct ho_model hm;static unsigned observer_ready=1;static long owner=123;static unsigned publications;
static int enabled(void){return 1;}static void own_lock(void){}static void own_unlock(void){}static long syscall(long n){assert(n==172);return 123;}static void publish_status(void){publications++;}
int fx3_osd_timeout_pair(unsigned expected,unsigned long expected_prior_sequence){if(!enabled())return -1;own_lock();int ok=observer_ready&&owner==syscall(172)&&!hm.failed&&hm.stage==1&&hm.pending==expected&&hm.seq==expected_prior_sequence;if(ok){hm.failed=1;publish_status();}own_unlock();return ok?0:-1;}

int main(void){hm.stage=1;hm.pending=0x1005;hm.seq=1358;assert(fx3_osd_timeout_pair(0x1005,1357)<0&&!hm.failed&&!publications);assert(fx3_osd_timeout_pair(0x1003,1358)<0&&!hm.failed);hm.stage=2;assert(fx3_osd_timeout_pair(0x1005,1358)<0&&!hm.failed);hm.stage=1;assert(!fx3_osd_timeout_pair(0x1005,1358)&&hm.failed&&publications==1);unsigned char ack[8];assert(ho_prepare_ack(&hm,ack)<0&&fx3_osd_timeout_pair(0x1005,1358)<0);puts("PAIR_TIMEOUT_GATE_PASS exact_pending_and_prior_seq/stale_timer_cannot_poison_new_batch/no_original_semaphore_or_ACK");}
