#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "fx3-gpe-backend-v7.c"
#include "emptyclip101-fixture-v1.h"
static unsigned callbacks,statuses,order;static int status_expected;static struct gpe_context*active;
static int cb(void*u,uint64_t fn,const uint8_t p[16]){(void)u;assert(fn==0x1234&&u32(p)==712&&!u32(p+4)&&u64(p+8)==0x5678);assert(order++==0);assert(active->extents[0].leases==1&&active->extents[1].leases==1);callbacks++;return 0;}
static int status(void*u,uint32_t Q,const uint8_t p[4]){(void)u;assert(Q==0x22&&(int)u32(p)==status_expected);assert(order++==(status_expected?0:1));statuses++;return 0;}
static void fillword(uint8_t*p,size_t n,unsigned word){for(size_t i=0;i<n;i+=2){p[i]=word;p[i+1]=word>>8;}}
static void reset_hooks(void){callbacks=statuses=order=0;status_expected=0;}
int main(void){size_t dn=0x140000,sn=0x340000;uint8_t*d=malloc(dn),*s=malloc(sn),*expected=malloc(dn);assert(d&&s&&expected);struct gpe_ref dr={1,1},sr={2,1};
 for(unsigned i=0;i<sizeof ec101/sizeof ec101[0];i++){
  uint8_t p[144];memcpy(p,ec101[i].raw,144);p[121]=0;put32(p+128,0x1234);put32(p+136,0x5678);
  struct gpe_plan plan;assert(!gpe_plan_blit(p,144,&plan));assert(plan.empty_clip_noop==ec101[i].empty);fillword(d,dn,0x24c8);fillword(expected,dn,0x24c8);fillword(s,sn,0xf19f);
  if(!ec101[i].empty){int64_t dx=coord(p+8)+coord(p+40)-coord(p+80),dy=coord(p+12)+coord(p+44)-coord(p+84);int64_t x1=dx>coord(p+24)?dx:coord(p+24),y1=dy>coord(p+28)?dy:coord(p+28);int64_t x2=dx+u32(p+16)<coord(p+24)+u32(p+32)?dx+u32(p+16):coord(p+24)+u32(p+32),y2=dy+u32(p+20)<coord(p+28)+u32(p+36)?dy+u32(p+20):coord(p+28)+u32(p+36);for(int64_t y=y1;y<y2;y++)for(int64_t x=x1;x<x2;x++){size_t o=u64(p)-0x43feb5000UL+(y*u32(p+48)+x)*2;assert(o+2<=dn);expected[o]=0x9f;expected[o+1]=0xf1;}}
  struct gpe_context c;active=&c;reset_hooks();gpe_init(&c,(struct gpe_hooks){0,cb,status});assert(!gpe_register(&c,dr,0x43feb5000UL,d,dn)&&!gpe_register(&c,sr,0x410924000UL,s,sn)&&!gpe_begin_batch(&c,1));assert(!gpe_submit(&c,1,712,0x22,p,144,dr,sr));assert(!memcmp(d,expected,dn));for(size_t z=0;z<sn;z++)assert(s[z]==(z%2?0xf1:0x9f));assert(c.extents[0].leases==1&&c.extents[1].leases==1&&c.count==1);assert(gpe_unregister(&c,dr)==GPE_BUSY&&gpe_unregister(&c,sr)==GPE_BUSY);assert(!gpe_deliver_one(&c)&&callbacks==1&&statuses==1&&order==2&&!c.extents[0].active&&!c.extents[1].active&&!c.extents[0].leases&&!c.extents[1].leases);uint8_t flush[24]={1};assert(!gpe_submit(&c,4,713,0,flush,24,dr,sr)&&!c.batches[0].failures);
 }
 /* Inaccessible pixel pages prove an accepted empty clip performs no loads/stores. */
 void*nd=mmap(0,0x200000,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0),*ns=mmap(0,0x400000,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);assert(nd!=MAP_FAILED&&ns!=MAP_FAILED);uint8_t q[144];memcpy(q,ec101[0].raw,144);q[121]=1;memset(q+128,0,16);struct gpe_context c;gpe_init(&c,(struct gpe_hooks){0});assert(!gpe_register(&c,dr,0x43feb5000UL,nd,dn)&&!gpe_register(&c,sr,0x410924000UL,ns,sn)&&!gpe_begin_batch(&c,1));assert(!gpe_submit(&c,1,712,0,q,144,dr,sr));assert(!c.extents[0].leases&&!c.extents[1].leases);
 /* Fully validated resources remain mandatory, including own bounds and overlap. */
 for(unsigned which=0;which<3;which++){gpe_init(&c,(struct gpe_hooks){0});assert(!gpe_register(&c,dr,0x43feb5000UL,d,which==0?16:dn)&&!gpe_register(&c,sr,0x410924000UL,s,which==1?16:sn)&&!gpe_begin_batch(&c,1));struct gpe_ref use=which==2?(struct gpe_ref){2,2}:sr;int want=which==2?GPE_STALE:GPE_BOUNDS;assert(gpe_submit(&c,1,712,0,q,144,dr,use)==want);uint8_t flush[24]={1};assert(gpe_submit(&c,4,713,0,flush,24,dr,sr)==want);assert(!c.extents[0].leases&&!c.extents[1].leases);}
 for(unsigned which=0;which<8;which++){uint8_t p[144];memcpy(p,q,144);int want=GPE_BOUNDS;switch(which){case 0:put32(p+48,500);break;case 1:put32(p+88,5);break;case 2:put32(p+8,0xffffffff);break;case 3:put32(p+32,0);break;case 4:p[116]=1;want=GPE_UNSUPPORTED;break;case 5:put32(p+92,9);want=GPE_UNSUPPORTED;break;case 6:p[112]=2;want=GPE_UNSUPPORTED;break;case 7:put32(p+36,0);break;}struct gpe_plan plan;assert(gpe_plan_blit(p,144,&plan)==want);}
 uint8_t overlap[144];memcpy(overlap,q,144);for(unsigned z=0;z<8;z++)overlap[56+z]=overlap[z];put32(overlap+64,501);put32(overlap+68,432);put32(overlap+72,6);put32(overlap+76,42);put32(overlap+88,640);gpe_init(&c,(struct gpe_hooks){0});assert(!gpe_register(&c,dr,0x43feb5000UL,d,dn)&&!gpe_begin_batch(&c,1));assert(gpe_submit(&c,1,712,0,overlap,144,dr,dr)==GPE_OVERLAP&&!c.extents[0].leases);
 assert(gpe_plan_blit(q,143,&(struct gpe_plan){0})==GPE_INVALID);munmap(nd,0x200000);munmap(ns,0x400000);free(d);free(s);free(expected);puts("AP101_EMPTY_CLIP_PASS native_seq712/9_empty_nonempty_edge_vectors/zero_pixel_access_PROT_NONE/full_buffer_guards/source_target_bounds/format_flags_stride_negative_length_reject/stale_resource_and_overlap_reject/callback_before_status_once/leases_held_until_native_delivery/retirement_once/Flush_success_and_prior_failure_sticky");}
