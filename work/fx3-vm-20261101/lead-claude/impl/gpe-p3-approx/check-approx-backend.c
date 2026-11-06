#include "fx3-gpe-backend-v2.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "expected-vectors.h"
#define BASE UINT64_C(0x43feb5100)
static const struct gpe_ref D={545,1},S={546,1},Z={0};
static unsigned checks;
#define CHECK(x) do{checks++;if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1;}}while(0)
static void put(uint8_t *p,uint64_t v,unsigned n){for(unsigned i=0;i<n;i++)p[i]=(uint8_t)(v>>(i*8));}
static uint32_t get(const uint8_t *p,unsigned n){uint32_t v=0;for(unsigned i=0;i<n;i++)v|=(uint32_t)p[i]<<(i*8);return v;}
static void mkfill(uint8_t *q,unsigned fmt,unsigned as,unsigned k,unsigned sel){
 memset(q,0,56);put(q,BASE,8);put(q+16,2,4);put(q+20,2,4);put(q+24,4,4);put(q+28,fmt,4);
 q[32]=253;q[33]=91;q[34]=17;q[35]=as;q[36]=sel;q[37]=k;q[38]=1;
}
static void mkblit(uint8_t *q,unsigned fmt,unsigned k,unsigned sel){
 memset(q,0,144);put(q,BASE,8);put(q+56,BASE+0x1000,8);
 put(q+16,2,4);put(q+20,2,4);put(q+32,2,4);put(q+36,2,4);put(q+48,4,4);put(q+52,fmt,4);
 put(q+72,2,4);put(q+76,2,4);put(q+88,5,4);put(q+92,fmt,4);q[112]=sel;q[114]=k;q[121]=1;
}
static int init(struct gpe_context *c,uint8_t *d,size_t dn,uint8_t *s,size_t sn){
 gpe_init(c,(struct gpe_hooks){0});int r=gpe_register(c,D,BASE,d,dn);if(r)return r;
 if(s){r=gpe_register(c,S,BASE+0x1000,s,sn);if(r)return r;}
 return gpe_begin_batch(c,1);
}
int main(void){
 struct gpe_context c;uint8_t d[128],s[128],expected[128],q[144];
 unsigned nv=sizeof(vectors)/sizeof(*vectors);
 for(unsigned i=0;i<nv;i++){
  const struct vector *v=&vectors[i];unsigned bpp=v->fmt?4:2;
  for(unsigned sel=1;sel<=2;sel++){
   memset(d,0xa5,sizeof(d));for(unsigned y=0;y<2;y++)for(unsigned x=0;x<2;x++)put(d+(y*4+x)*bpp,v->dst,bpp);
   memcpy(expected,d,sizeof(d));for(unsigned y=0;y<2;y++)for(unsigned x=0;x<2;x++)put(expected+(y*4+x)*bpp,v->out,bpp);
   CHECK(!init(&c,d,sizeof(d),NULL,0));mkfill(q,v->fmt,v->as,v->k,sel);
   CHECK(!gpe_submit(&c,0,i,0,q,56,D,Z));CHECK(!memcmp(d,expected,sizeof(d)));CHECK(!c.extents[0].leases);
  }
  for(unsigned sel=0;sel<=1;sel++)for(unsigned flip=0;flip<4;flip++){
   memset(d,0xa5,sizeof(d));memset(s,0xb6,sizeof(s));
   /* Transparent source with nonzero RGB at one edge: must preserve dst. */
   for(unsigned y=0;y<2;y++)for(unsigned x=0;x<2;x++){
    put(d+(y*4+x)*bpp,v->dst,bpp);put(s+(y*5+x)*bpp,(x==0&&y==0)?(v->src&~(bpp==2?15U:255U)):v->src,bpp);
   }
   memcpy(expected,d,sizeof(d));
   for(unsigned y=0;y<2;y++)for(unsigned x=0;x<2;x++){
    unsigned sx=(flip&1)?1-x:x,sy=(flip&2)?1-y:y;
    unsigned copying=sel==0&&v->k==255;
    uint32_t out=copying?get(s+(sy*5+sx)*bpp,bpp):(sx==0&&sy==0)?v->dst:v->out;
    put(expected+(y*4+x)*bpp,out,bpp);
   }
   CHECK(!init(&c,d,sizeof(d),s,sizeof(s)));mkblit(q,v->fmt,v->k,sel);q[119]=flip&1;q[120]=(flip>>1)&1;
   q[108]=13;q[109]=57;q[110]=91;q[111]=3; /* unused color must not tint */
   CHECK(!gpe_submit(&c,1,i,0,q,144,D,S));CHECK(!memcmp(d,expected,sizeof(d)));CHECK(!c.extents[0].leases&&!c.extents[1].leases);
  }
 }
 /* Each unadmitted byte value is rejected before any write, including flags
  * 0x10 whose low nibble is zero. H/V admit exactly 0/1, never aliases. */
 unsigned rejects=0;
 for(unsigned fmt=0;fmt<2;fmt++)for(unsigned field=112;field<=120;field++)for(unsigned value=0;value<256;value++){
  if(field==114)continue;
  if((field==112||field>=119)?value<=1:value==0)continue;
  memset(d,0xa5,sizeof(d));memset(s,0xb6,sizeof(s));memcpy(expected,d,sizeof(d));CHECK(!init(&c,d,sizeof(d),s,sizeof(s)));
  mkblit(q,fmt,127,1);q[field]=value;CHECK(gpe_submit(&c,1,1,0,q,144,D,S)==GPE_UNSUPPORTED);CHECK(!memcmp(d,expected,sizeof(d)));rejects++;
 }
 for(unsigned t=0;t<20;t++){
  memset(d,0xa5,sizeof(d));memset(s,0xb6,sizeof(s));memcpy(expected,d,sizeof(d));CHECK(!init(&c,d,sizeof(d),s,sizeof(s)));mkblit(q,1,127,1);
  int want=GPE_UNSUPPORTED;
  if(t<3){put(q+52,t+2,4);put(q+92,t+2,4);}
  if(t==3)put(q+92,0,4);
  if(t==4)put(q+104,1,4);
  if(t==5)put(q+16,3,4);
  if(t==6)put(q+96,0x40000000,4);
  if(t==7)put(q+100,0x40000000,4);
  if(t==8){put(q+32,1,4);want=GPE_BOUNDS;}
  if(t==9){put(q+56,BASE,8);want=GPE_OVERLAP;}
  if(t==10){put(q+56,BASE+0x1000+sizeof(s)-24,8);want=GPE_BOUNDS;}
  if(t==11){put(q,BASE+sizeof(d)-20,8);want=GPE_BOUNDS;}
  if(t==12){put(q+64,0xffffffff,4);want=GPE_BOUNDS;}
  if(t==13){put(q+72,0,4);put(q+16,0,4);want=GPE_BOUNDS;}
  if(t==14){put(q+8,0xffffffff,4);want=GPE_BOUNDS;}
  if(t==15){put(q,UINT64_MAX-1,8);want=GPE_BOUNDS;}
  if(t>=16){mkfill(q,t==16?2:0,127,127,t==17?3:t==18?255:t==19?0:1);CHECK(gpe_submit(&c,0,1,0,q,56,D,Z)==GPE_UNSUPPORTED);}
  else CHECK(gpe_submit(&c,1,1,0,q,144,D,t==9?D:S)==want);
  CHECK(!memcmp(d,expected,sizeof(d)));rejects++;
 }
 /* Source crop coordinates, destination correction and flips all operate on
  * the requested rectangle, never padding or the rest of the surface. */
 for(unsigned fmt=0;fmt<2;fmt++)for(unsigned flip=0;flip<4;flip++){
  unsigned bpp=fmt?4:2;memset(d,0xa5,sizeof(d));memset(s,0xb6,sizeof(s));
  for(unsigned y=0;y<2;y++)for(unsigned x=0;x<2;x++)put(s+((y+1)*5+x+1)*bpp,fmt?0x123456ffU+(y*2+x)*0x10000U:0x135fU+(y*2+x)*0x100U,bpp);
  memcpy(expected,d,sizeof(d));for(unsigned y=0;y<2;y++)for(unsigned x=0;x<2;x++){
   unsigned sx=(flip&1)?1-x:x,sy=(flip&2)?1-y:y;memcpy(expected+((y+1)*4+x+1)*bpp,s+((sy+1)*5+sx+1)*bpp,bpp);
  }
  CHECK(!init(&c,d,sizeof(d),s,sizeof(s)));mkblit(q,fmt,255,1);put(q+64,1,4);put(q+68,1,4);
  put(q+8,2,4);put(q+40,1,4);put(q+80,2,4);put(q+12,1,4);put(q+32,4,4);put(q+36,4,4);q[119]=flip&1;q[120]=(flip>>1)&1;
  CHECK(!gpe_submit(&c,1,1,0,q,144,D,S));CHECK(!memcmp(d,expected,sizeof(d)));
 }
 printf("PASS backend-v2 vectors=%u fill_cases=%u blit_cases=%u rejected_zero_write=%u checks=%u ASan/UBSan enabled\n",nv,nv*2,nv*8,rejects,checks);return 0;
}
