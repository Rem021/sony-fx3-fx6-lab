#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fx3-gpe-backend-v6.c"
#include "gpe97-alpha-fixture.h"
static uint64_t hash97(const uint8_t*p,size_t n){uint64_t h=UINT64_C(14695981039346656037);for(size_t i=0;i<n;i++)h=(h^p[i])*UINT64_C(1099511628211);return h;}
static void initial97(uint8_t*p,size_t n){for(size_t i=0;i<n;i+=2){p[i]=0x5f;p[i+1]=0x13;}}
static unsigned pattern97(size_t i){return(i*37+11)&255;}
int main(void){
 for(unsigned i=0;i<sizeof pv97/sizeof pv97[0];i++)assert(straight_over_v1(pv97[i][0],pv97[i][1],pv97[i][3],pv97[i][2])==pv97[i][4]);
 for(unsigned i=0;i<sizeof av97/sizeof av97[0];i++){uint8_t c[4]={av97[i][1],av97[i][2],av97[i][3],av97[i][4]};assert(a8_color_over_candidate(av97[i][0],c,av97[i][5],av97[i][6])==av97[i][7]);}
 uint8_t*d=malloc(614400+64),*s=malloc(0x200000+64);assert(d&&s);for(size_t i=0;i<0x200000;i++)s[i]=pattern97(i);memset(s+0x200000,0x5a,64);
 const uint8_t*params[2]={native97_0,native97_1};
 for(unsigned j=0;j<2;j++)for(unsigned ki=0;ki<5;ki++){
  uint8_t q[144];memcpy(q,params[j],144);q[114]=near97_K[ki];struct gpe_plan p;assert(!gpe_plan_blit(q,144,&p)&&p.approx_blend&&p.constant_alpha==near97_K[ki]&&p.approx_fmt2==(j==0));
  initial97(d,614400);memset(d+614400,0xa5,64);struct gpe_context ctx;gpe_init(&ctx,(struct gpe_hooks){0});struct gpe_ref dr={1,1},sr={2,1};assert(!gpe_register(&ctx,dr,u64(q),d,614400));assert(!gpe_register(&ctx,sr,u64(q+56),s,0x200000));assert(!gpe_begin_batch(&ctx,1));q[121]=1;memset(q+128,0,16);assert(!gpe_submit(&ctx,1,998+j,0,q,144,dr,sr));assert(hash97(d,614400)==native97_matrix[j][ki]);for(unsigned i=0;i<64;i++)assert(d[614400+i]==0xa5&&s[0x200000+i]==0x5a);for(size_t i=0;i<0x200000;i++)assert(s[i]==pattern97(i));
  /* New K admission removes the batch's predecessor failure; Flush needs no policy bypass. */
  uint8_t flush[24]={1};assert(!gpe_submit(&ctx,4,1050,0,flush,24,dr,sr));
  memcpy(q,params[j],144);q[116]=1;initial97(d,614400);assert(gpe_submit(&ctx,1,1060,0,q,144,dr,sr)==GPE_UNSUPPORTED);assert(hash97(d,614400)==hash97((uint8_t[2]){0x5f,0x13},2)||d[0]==0x5f);for(size_t i=0;i<614400;i++)assert(d[i]==(i%2?0x13:0x5f));assert(gpe_submit(&ctx,4,1061,0,flush,24,dr,sr)==GPE_UNSUPPORTED);
 }
 for(unsigned ki=0;ki<5;ki++){
  uint8_t q[144];memcpy(q,near97,144);q[114]=near97_K[ki];uint8_t dst[12],src[4];initial97(dst,12);for(unsigned i=0;i<4;i++)src[i]=pattern97(i);struct gpe_context c;struct gpe_ref dr={1,1},sr={2,1};gpe_init(&c,(struct gpe_hooks){0});assert(!gpe_register(&c,dr,0x1000,dst,12)&&!gpe_register(&c,sr,0x100000,src,4)&&!gpe_begin_batch(&c,1));assert(!gpe_submit(&c,1,1,0,q,144,dr,sr));assert(hash97(dst,12)==near97_fnv[ki]);
  uint8_t fill[56]={0};put32(fill,0x2000);put32(fill+16,3);put32(fill+20,2);put32(fill+24,5);fill[32]=0xa5;fill[33]=0x5f;fill[34]=0xe7;fill[35]=0x83;fill[37]=near97_K[ki];fill[38]=1;uint16_t pix[12];for(unsigned i=0;i<12;i++)pix[i]=0x24c8;gpe_init(&c,(struct gpe_hooks){0});assert(!gpe_register(&c,dr,0x2000,pix,sizeof pix)&&!gpe_begin_batch(&c,1));struct gpe_plan p;assert(!gpe_plan_fill(fill,56,&p)&&p.approx_blend==(near97_K[ki]!=255));assert(!gpe_submit(&c,0,1,0,fill,56,dr,dr));for(unsigned y=0;y<2;y++)for(unsigned x=0;x<5;x++)assert(pix[y*5+x]==(x<3?fill97_ref[ki]:0x24c8));assert(pix[10]==0x24c8&&pix[11]==0x24c8);
 }
 free(d);free(s);puts("AP97R2_ALPHA_PASS Fraction40_fmt0_fmt1_math/35_A8_math/native_seq998_999_all5K_pixelFNV/source_padding_neighbors_unchanged/nearest5K/fill_selector0_5K/retained_unknown_guard_zero_write/Flush_failure_propagates_only_prior_failure");return 0;
}
