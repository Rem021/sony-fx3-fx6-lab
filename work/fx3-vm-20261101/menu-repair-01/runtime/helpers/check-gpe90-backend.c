#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fx3-gpe-backend-v3.c"
#include "gpe90-fixture.h"
#define SCREEN_BASE UINT64_C(0x43feb5000)
#define SCREEN_BYTES 0x140000
static uint8_t *d,*s,*copy;
static struct gpe_ref dr={0x81,3},sr={0x1234,45};
static int submit_test(const uint8_t*p,size_t srcbytes,struct gpe_ref source){
 struct gpe_context c;gpe_init(&c,(struct gpe_hooks){0});assert(!gpe_register(&c,dr,SCREEN_BASE,d,SCREEN_BYTES));assert(!gpe_register(&c,sr,u64(p+56),s,srcbytes));assert(!gpe_begin_batch(&c,1));return gpe_submit(&c,1,0,0,p,144,dr,source);
}
int main(void){
 d=malloc(SCREEN_BYTES+128);copy=malloc(SCREEN_BYTES);s=malloc(0x400000+128);assert(d&&s&&copy);
 for(unsigned i=0;i<16;i++){const unsigned*v=vectors90[i];uint8_t color[4]={v[1],v[2],v[3],v[4]};assert(a8_color_over_candidate(v[0],color,v[5],v[6])==v[7]);}
 for(unsigned j=0;j<73;j++){
  const uint8_t*p=params90[j];struct gpe_plan plan;assert(!gpe_plan_blit(p,144,&plan));assert(plan.approx_blend);assert(plan.approx_fmt2==(u32(p+92)==2));assert(plan.approx_stretch==(u32(p+16)!=u32(p+72)||u32(p+20)!=u32(p+76)));
  memset(d,0xa5,SCREEN_BYTES+128);for(unsigned i=0;i<SCREEN_BYTES;i+=2){d[i]=15;d[i+1]=0;}
  unsigned stride=u32(p+88),fmt=u32(p+92);for(unsigned i=0;i<0x200000;i++)if(fmt==2)s[i]=(i*17+(i/stride)*3)&255;else{uint16_t v=((i/8%16)<<12)|((i/stride%16)<<8)|((i%16)<<4)|(i%16);memcpy(s+2*i,&v,2);}
  assert(!submit_test(p,0x400000,sr));uint64_t f=UINT64_C(14695981039346656037);for(unsigned i=0;i<SCREEN_BYTES;i++)f=(f^d[i])*UINT64_C(1099511628211);printf("REF90 index=%u fnv=%#llx\n",j,(unsigned long long)f);
  for(unsigned i=SCREEN_BYTES;i<SCREEN_BYTES+128;i++)assert(d[i]==0xa5);
  /* Tight exact source envelope succeeds; one-byte-short last row rejects
   * before any write, including different bpp and crop/stride padding. */
  size_t envelope=plan.src-u64(p+56)+(plan.src_rows-1)*plan.src_step+plan.src_line;memcpy(copy,d,SCREEN_BYTES);
  assert(submit_test(p,envelope-1,sr)==GPE_BOUNDS);assert(!memcmp(copy,d,SCREEN_BYTES));
  assert(submit_test(p,envelope,(struct gpe_ref){sr.handle,sr.generation-1})==GPE_STALE);assert(!memcmp(copy,d,SCREEN_BYTES));
  uint8_t q[144];memcpy(q,p,144);q[116]=1;assert(submit_test(q,0x400000,sr)==GPE_UNSUPPORTED);assert(!memcmp(copy,d,SCREEN_BYTES));
  if(fmt==2){q[116]=0;q[111]=128;assert(submit_test(q,0x400000,sr)==GPE_UNSUPPORTED);assert(!memcmp(copy,d,SCREEN_BYTES));}
 }
 /* Leases retire before reuse; native count is not a lease. */
 struct gpe_context c;gpe_init(&c,(struct gpe_hooks){0});assert(!gpe_register(&c,sr,0x1000,s,4096));struct gpe_lease l={0};assert(!gpe_acquire(&c,sr,&l));assert(gpe_unregister(&c,sr)==GPE_BUSY);struct gpe_lease other={0};assert(gpe_acquire(&c,sr,&other)==GPE_STALE);assert(!gpe_release(&c,&l));assert(!gpe_register(&c,(struct gpe_ref){sr.handle,sr.generation+1},0x1000,s,4096));assert(gpe_acquire(&c,sr,&other)==GPE_STALE);
 free(d);free(copy);free(s);puts("GPE90_BACKEND_PASS vectors16 actualparams73 syntheticpixels/clip/stride/differentbpp/nearest/zero-write-bounds/stale-epoch/flags/lifetime");return 0;
}
