
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "fx3-osd-life-core-v1.h"
static struct lp_model m;
int main(void){assert(lp_role(0x8280074d,12,0xf1db8)==0x1002);assert(lp_role(0x8280084d,36,0xf1e44)==0x1003);assert(lp_role(0x8280084e,8,0xf1d2c)==0x1005);assert(!lp_role(0x8280084e,8,0xf1d2d));assert(!lp_role(0x8280084d,8,0xf1d2c));assert(lp_return(&m,0,1,12,0x1002,-1)<0&&!m.live);assert(lp_return(&m,0x1000,0x8280074d,12,0x1002,0)==0&&m.live==1);assert(lp_sent(&m,0x1000,0x8280074d,0x1002)==0&&m.sends==1);assert(lp_freed(&m,0x1000,1,0)<0&&m.live==1);assert(lp_freed(&m,0x1000,0x8280074d,-1)<0&&m.live==1);assert(lp_return(&m,0x1000,0x8280074d,12,0x1002,0)==0&&m.reuses==1&&m.live==1);assert(lp_freed(&m,0x1000,0x8280074d,0)==0&&!m.live&&m.frees==1);assert(!lp_control(&m,0x1005,10));assert(lp_control(&m,0x1005,20)<0&&m.pair_started==10);assert(!lp_expired(&m,2000000009UL)&&lp_expired(&m,2000000010UL));assert(lp_descriptor(&m,0x1003)<0&&m.pending==0x1005);assert(!lp_descriptor(&m,0x1005)&&!m.pending);assert(!lp_control(&m,0x1003,11)&&m.sequence==2);m.failed=1;assert(!lp_expired(&m,9999999999UL)&&lp_descriptor(&m,0x1003)<0);puts("LIFETIME_CORE_PASS native_constructor_exact/alloc_failure/no_userfree_vs_native_reuse_distinct/wrong_free_unchanged/paired_types/deadline_no_duplicate_reset/failed_no_ack");}
