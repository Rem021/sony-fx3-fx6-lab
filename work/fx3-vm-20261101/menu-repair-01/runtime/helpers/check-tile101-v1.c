#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include "fx3-gpe-backend-v8.c"
#include "tile101-fixture-v1.h"
static uint64_t hash(const unsigned char*p,size_t n){uint64_t h=14695981039346656037UL;for(size_t i=0;i<n;i++)h=(h^p[i])*1099511628211UL;return h;}
static uint16_t word(unsigned x,unsigned y){return (uint16_t)((((x+7*y)&15)<<12)|(((3*x+y)&15)<<8)|(((x^y)&15)<<4)|15);}
static void init(uint8_t*d,uint8_t*s,size_t dn,size_t sn){for(size_t z=0;z<dn;z+=2){d[z]=0xc8;d[z+1]=0x24;}for(size_t z=0;z<sn/2;z++){uint16_t v=word(z%64,z/64);s[2*z]=v;s[2*z+1]=v>>8;}}
static unsigned callbacks,statuses,order;static int cb(void*u,uint64_t fn,const uint8_t p[16]){(void)u;assert(fn==0x1234&&u32(p)==712&&!u32(p+4)&&u64(p+8)==0x5678&&order++==0);callbacks++;return 0;}
static int status(void*u,uint32_t q,const uint8_t p[4]){(void)u;assert(q==0x22&&!u32(p)&&order++==1);statuses++;return 0;}
static void reference(const uint8_t*p,uint8_t*expected,const uint8_t*s,size_t dn,size_t sn){
 int64_t dx=coord(p+8)+coord(p+40)-coord(p+80),dy=coord(p+12)+coord(p+44)-coord(p+84),cx=coord(p+24),cy=coord(p+28);int64_t l=dx>cx?dx:cx,t=dy>cy?dy:cy,r=dx+u32(p+16)<cx+u32(p+32)?dx+u32(p+16):cx+u32(p+32),b=dy+u32(p+20)<cy+u32(p+36)?dy+u32(p+20):cy+u32(p+36);
 for(int64_t y=t;y<b;y++)for(int64_t x=l;x<r;x++){uint64_t tx=(x-dx)&(u32(p+72)-1),ty=(y-dy)&(u32(p+76)-1);size_t a=((u32(p+68)+ty)*u32(p+88)+u32(p+64)+tx)*2,at=(y*u32(p+48)+x)*2;assert(a+2<=sn&&at+2<=dn);expected[at]=s[a];expected[at+1]=s[a+1];}
}
int main(void){size_t dn=0x140000,sn=0x400000;uint8_t*d=malloc(dn),*s=malloc(sn),*e=malloc(dn);assert(d&&s&&e);struct gpe_ref dr={1,1},sr={2,1};
 for(unsigned v=0;v<7;v++){
  uint8_t q[144];memcpy(q,tile101_native,144);
  if(v==1){put32(q+8,10);put32(q+12,10);put32(q+16,80);put32(q+20,10);put32(q+24,27);put32(q+28,13);put32(q+32,31);put32(q+36,5);}
  if(v==2){put32(q+16,32);put32(q+20,2);}
  if(v==3){put32(q+64,17);put32(q+68,1);}
  if(v==4){put32(q+8,10);put32(q+12,10);put32(q+16,80);put32(q+20,6);put32(q+24,15);put32(q+28,12);put32(q+32,20);put32(q+36,3);put32(q+40,7);put32(q+44,3);put32(q+80,2);put32(q+84,1);}
  if(v==5){put32(q+72,1);put32(q+76,1);}
  if(v==6){put32(q+72,16);put32(q+76,4);put32(q+20,7);put32(q+36,7);}
  struct gpe_plan plan;assert(!gpe_plan_blit(q,144,&plan)&&plan.approx_tile&&!plan.approx_stretch&&!plan.empty_clip_noop);init(d,s,dn,sn);memcpy(e,d,dn);uint64_t before=hash(s,sn);reference(q,e,s,dn,sn);q[121]=0;put32(q+128,0x1234);put32(q+136,0x5678);struct gpe_context c;gpe_init(&c,(struct gpe_hooks){0,cb,status});callbacks=statuses=order=0;assert(!gpe_register(&c,dr,u64(q),d,dn)&&!gpe_register(&c,sr,u64(q+56),s,sn)&&!gpe_begin_batch(&c,1));assert(!gpe_submit(&c,1,712,0x22,q,144,dr,sr));assert(!memcmp(d,e,dn)&&before==hash(s,sn));assert(c.extents[0].leases==1&&c.extents[1].leases==1);assert(!gpe_deliver_one(&c)&&callbacks==1&&statuses==1&&order==2&&!c.extents[0].leases&&!c.extents[1].leases);uint8_t flush[24]={1};assert(!gpe_submit(&c,4,713,0,flush,24,dr,sr));
 }
 /* Original fully offscreen nominal rectangles: clip itself is valid and
    both source and destination pixels are inaccessible. */
 void*nd=mmap(0,0x200000,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0),*ns=mmap(0,0x400000,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);assert(nd!=MAP_FAILED&&ns!=MAP_FAILED);
 for(unsigned i=0;i<sizeof off101/sizeof off101[0];i++){
  uint8_t q[144];memcpy(q,off101[i],144);q[121]=1;memset(q+128,0,16);struct gpe_plan plan;assert(!gpe_plan_blit(q,144,&plan)&&plan.empty_clip_noop&&plan.dst_nominal_outside);struct gpe_context c;gpe_init(&c,(struct gpe_hooks){0});assert(!gpe_register(&c,dr,u64(q),nd,dn)&&!gpe_register(&c,sr,u64(q+56),ns,sn)&&!gpe_begin_batch(&c,1));assert(!gpe_submit(&c,1,713,0,q,144,dr,sr));assert(!c.extents[0].leases&&!c.extents[1].leases);
  /* Source capacity/clip capacity and physical destination base still gate. */
  for(unsigned bad=0;bad<3;bad++){gpe_init(&c,(struct gpe_hooks){0});assert(!gpe_register(&c,dr,u64(q)+(bad==2?1:0),nd,bad==0?16:dn)&&!gpe_register(&c,sr,u64(q+56),ns,bad==1?1:sn)&&!gpe_begin_batch(&c,1));assert(gpe_submit(&c,1,713,0,q,144,dr,sr)==GPE_BOUNDS);}
  put32(q+32,641);assert(gpe_plan_blit(q,144,&plan)==GPE_BOUNDS);
 }
 for(unsigned bad=0;bad<11;bad++){uint8_t q[144];memcpy(q,tile101_native,144);int want=GPE_UNSUPPORTED;switch(bad){case 0:put32(q+72,31);break;case 1:put32(q+76,3);break;case 2:q[114]=254;break;case 3:put32(q+96,0);break;case 4:put32(q+100,0x40000000);break;case 5:q[116]=2;break;case 6:q[118]=1;break;case 7:put32(q+92,2);q[117]=14;break;case 8:put32(q+104,1);break;case 9:put32(q+88,47);want=GPE_BOUNDS;break;case 10:put32(q+64,0xffffffff);want=GPE_BOUNDS;break;}struct gpe_plan plan;assert(gpe_plan_blit(q,144,&plan)==want);}
 munmap(nd,0x200000);munmap(ns,0x400000);free(d);free(s);free(e);puts("AP101_TILE_PASS nativeP74seq712/repeat32x2/clip_offsets/partial_dst/7_fullbuffer_independent_mask_reference/source_origin_fold/nonzero_adjust/1x1/16x4/PROT_NONE_native_seq713_718_720_723_725/clip_extent_original_base_owner_sourcebounds_reject/nonpow2_scale_K_flags_formats_rotation_reject/native_callback_status_lease_Flush");}
