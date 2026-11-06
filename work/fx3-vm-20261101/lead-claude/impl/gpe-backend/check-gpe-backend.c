#include "fx3-gpe-backend.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
#define BASE UINT64_C(0x43feb5000)
static const struct gpe_ref D={545,1},S={546,1},Z={0,0};
static unsigned assertions,tests;
#define CHECK(x) do {assertions++; if(!(x)){fprintf(stderr,"FAIL line %d: %s\n",__LINE__,#x);return 1;}}while(0)
static void p32(uint8_t *p,uint32_t v) {for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(i*8));}
static void p64(uint8_t *p,uint64_t v) {p32(p,(uint32_t)v);p32(p+4,(uint32_t)(v>>32));}
static uint32_t r32(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void fill(uint8_t *q,unsigned fmt) {
 memset(q,0,56);p64(q,BASE);p32(q+8,1);p32(q+12,1);p32(q+16,3);p32(q+20,2);p32(q+24,6);p32(q+28,fmt);
 q[32]=0x12;q[33]=0x3a;q[34]=0xb7;q[35]=0xe4;q[37]=255;q[38]=1;
}
static void blit(uint8_t *q,unsigned fmt) {
 memset(q,0,144);p64(q,BASE);p32(q+8,1);p32(q+12,1);p32(q+16,3);p32(q+20,2);
 p32(q+32,6);p32(q+36,6);p32(q+48,6);p32(q+52,fmt);p64(q+56,BASE+0x1000);
 p32(q+64,2);p32(q+68,1);p32(q+72,3);p32(q+76,2);p32(q+88,7);p32(q+92,fmt);q[114]=255;q[121]=1;
}
static int setup(struct gpe_context *c,uint8_t *dst,size_t n,uint8_t *src,size_t m,struct gpe_hooks h) {
 gpe_init(c,h);if(gpe_register(c,D,BASE,dst,n))return 1;
 if(src&&gpe_register(c,S,BASE+0x1000,src,m))return 1;return gpe_begin_batch(c,1);
}
static int pixels(void) {
 for(unsigned fmt=0;fmt<2;fmt++) {
  uint8_t dst[192],expected[192],q[56];struct gpe_context c;unsigned bpp=fmt?4:2;
  memset(dst,0xa5,sizeof(dst));memcpy(expected,dst,sizeof(dst));fill(q,fmt);CHECK(!setup(&c,dst,sizeof(dst),NULL,0,(struct gpe_hooks){0}));
  const uint8_t f0[]={0xbe,0x13},f1[]={0xe4,0xb7,0x3a,0x12};
  for(unsigned y=1;y<3;y++)for(unsigned x=1;x<4;x++)memcpy(expected+(y*6+x)*bpp,fmt?f1:f0,bpp);
  CHECK(!gpe_submit(&c,0,1,0,q,56,D,Z));CHECK(!memcmp(dst,expected,sizeof(dst)));CHECK(c.extents[0].leases==0);
  /* Independent single-channel cases exercise channel order, not uniform black. */
  for(unsigned channel=0;channel<4;channel++) {
   memset(q+32,0,4);q[32+channel]=0xf0;CHECK(!gpe_submit(&c,0,2+channel,0,q,56,D,Z));
   unsigned value=fmt?0xf0u<<(24-8*channel):0xfu<<(12-4*channel);
   for(unsigned b=0;b<bpp;b++)CHECK(dst[7*bpp+b]==(uint8_t)(value>>(8*b)));
  }
 }
 tests++;return 0;
}
static int rejects(void) {
 struct gpe_context c;uint8_t dst[192],before[192],q[144];memset(dst,0xa5,sizeof(dst));memcpy(before,dst,sizeof(dst));
 CHECK(!setup(&c,dst,36,NULL,0,(struct gpe_hooks){0}));fill(q,1);
 /* First row fits, last crosses: reject before writing the first pixel. */
 CHECK(gpe_submit(&c,0,1,0,q,56,D,Z)==GPE_BOUNDS);CHECK(!memcmp(dst,before,sizeof(dst)));
 CHECK(!gpe_unregister(&c,D));CHECK(gpe_submit(&c,0,2,0,q,56,D,Z)==GPE_STALE);CHECK(!memcmp(dst,before,sizeof(dst)));
 CHECK(gpe_register(&c,D,BASE,dst,sizeof(dst))==GPE_STALE);
 struct gpe_ref d2={545,2};CHECK(!gpe_register(&c,d2,BASE,dst,sizeof(dst)));CHECK(gpe_submit(&c,0,3,0,q,56,D,Z)==GPE_STALE);
 struct gpe_lease lease={0};CHECK(!gpe_acquire(&c,d2,&lease));CHECK(gpe_unregister(&c,d2)==GPE_BUSY);
 CHECK(gpe_submit(&c,0,4,0,q,56,d2,Z)==GPE_STALE);CHECK(!gpe_release(&c,&lease));CHECK(gpe_release(&c,&lease)==GPE_INVALID);
 CHECK(!memcmp(dst,before,sizeof(dst)));
 CHECK(!setup(&c,dst,sizeof(dst),NULL,0,(struct gpe_hooks){0}));
 for(unsigned fmt=2;fmt<8;fmt++){fill(q,fmt);CHECK(gpe_submit(&c,0,10+fmt,0,q,56,D,Z)==GPE_UNSUPPORTED);}
 fill(q,0);q[36]=1;CHECK(gpe_submit(&c,0,20,0,q,56,D,Z)==GPE_UNSUPPORTED);
 fill(q,0);q[37]=254;CHECK(gpe_submit(&c,0,21,0,q,56,D,Z)==GPE_UNSUPPORTED);
 fill(q,0);p32(q+8,0xffffffff);CHECK(gpe_submit(&c,0,22,0,q,56,D,Z)==GPE_BOUNDS);
 fill(q,0);p64(q,UINT64_MAX-2);CHECK(gpe_submit(&c,0,23,0,q,56,D,Z)==GPE_BOUNDS);
 fill(q,0);p32(q+16,0);CHECK(gpe_submit(&c,0,24,0,q,56,D,Z)==GPE_BOUNDS);
 CHECK(gpe_submit(&c,2,25,0,q,144,D,Z)==GPE_UNSUPPORTED);CHECK(gpe_submit(&c,3,26,0,q,144,D,Z)==GPE_UNSUPPORTED);
 CHECK(gpe_submit(&c,0,27,0,q,55,D,Z)==GPE_INVALID);CHECK(!memcmp(dst,before,sizeof(dst)));
 /* Contiguous extents cannot combine into one surface. */
 CHECK(!setup(&c,dst,36,NULL,0,(struct gpe_hooks){0}));CHECK(!gpe_register(&c,S,BASE+36,dst+36,156));fill(q,1);
 CHECK(gpe_submit(&c,0,28,0,q,56,D,Z)==GPE_BOUNDS);CHECK(!memcmp(dst,before,sizeof(dst)));
 CHECK(gpe_register(&c,(struct gpe_ref){9,1},BASE+10,dst+100,10)==GPE_OVERLAP);
 CHECK(gpe_register(&c,(struct gpe_ref){9,1},BASE+1000,dst+10,10)==GPE_OVERLAP);
 tests++;return 0;
}
static int copies(void) {
 for(unsigned fmt=0;fmt<2;fmt++) {
  struct gpe_context c;uint8_t dst[192],expected[192],src[192],q[144];unsigned bpp=fmt?4:2;
  for(unsigned i=0;i<sizeof(src);i++)src[i]=(uint8_t)(i*37+19);
  memset(dst,0xa5,sizeof(dst));memcpy(expected,dst,sizeof(dst));CHECK(!setup(&c,dst,sizeof(dst),src,sizeof(src),(struct gpe_hooks){0}));blit(q,fmt);
  /* Exercise both additive offsets and subtractive coordinate corrections. */
  p32(q+8,2);p32(q+40,2);p32(q+80,3);p32(q+12,3);p32(q+44,1);p32(q+84,3);
  for(unsigned y=0;y<2;y++)memcpy(expected+((y+1)*6+1)*bpp,src+((y+1)*7+2)*bpp,3*bpp);
  CHECK(!gpe_submit(&c,1,1,0,q,144,D,S));CHECK(!memcmp(dst,expected,sizeof(dst)));
  p64(q+56,BASE);CHECK(gpe_submit(&c,1,2,0,q,144,D,D)==GPE_OVERLAP);CHECK(!memcmp(dst,expected,sizeof(dst)));
  blit(q,fmt);p32(q+32,2);CHECK(gpe_submit(&c,1,3,0,q,144,D,S)==GPE_BOUNDS);CHECK(!memcmp(dst,expected,sizeof(dst)));
  blit(q,fmt);p32(q+24,2);CHECK(gpe_submit(&c,1,4,0,q,144,D,S)==GPE_BOUNDS);
  for(unsigned flag=115;flag<=120;flag++){blit(q,fmt);q[flag]=1;CHECK(gpe_submit(&c,1,flag,0,q,144,D,S)==GPE_UNSUPPORTED);}
  blit(q,fmt);p32(q+92,1-fmt);CHECK(gpe_submit(&c,1,5,0,q,144,D,S)==GPE_UNSUPPORTED);
  blit(q,fmt);p32(q+104,1);CHECK(gpe_submit(&c,1,6,0,q,144,D,S)==GPE_UNSUPPORTED);
  blit(q,fmt);p32(q+16,4);CHECK(gpe_submit(&c,1,7,0,q,144,D,S)==GPE_UNSUPPORTED);
  blit(q,fmt);p32(q+96,0x40000000);CHECK(gpe_submit(&c,1,8,0,q,144,D,S)==GPE_UNSUPPORTED);
  blit(q,fmt);p32(q+76,30);p32(q+20,30);p32(q+36,40);CHECK(gpe_submit(&c,1,9,0,q,144,D,S)==GPE_BOUNDS);
  CHECK(!memcmp(dst,expected,sizeof(dst)));CHECK(c.extents[0].leases==0&&c.extents[1].leases==0);
 }
 tests++;return 0;
}
struct log {unsigned n;uint32_t kind[512],value[512];unsigned fail;uint8_t *pixels;struct gpe_context *context;};
static int cb(void *user,uint64_t fn,const uint8_t p[16]) {
 struct log *l=user;assert(fn==0x123456789ULL);assert(r32(p+4)==0);assert(r32(p+8)==0x76543210);assert(r32(p+12)==0xfedcba98);
 if(l->context){assert(gpe_deliver_one(l->context)==GPE_BUSY);assert(gpe_begin_batch(l->context,777)==GPE_BUSY);struct gpe_lease lease={0};assert(gpe_release(l->context,&lease)==GPE_BUSY);}
 if(l->pixels)assert(l->pixels[14]==0xbe);l->kind[l->n]=1;l->value[l->n++]=r32(p);return l->fail;
}
static int status(void *user,uint32_t dst,const uint8_t p[4]) {
 struct log *l=user;assert(dst==0x8899);l->kind[l->n]=2;l->value[l->n++]=r32(p);return l->fail;
}
static int completions(void) {
 struct gpe_context c;uint8_t dst[192],q[56],flush[24]={0};struct log l={.pixels=dst,.context=&c};struct gpe_hooks h={&l,cb,status};
 memset(dst,0,sizeof(dst));CHECK(!setup(&c,dst,sizeof(dst),NULL,0,h));fill(q,0);q[38]=0;p64(q+40,0x123456789ULL);p64(q+48,UINT64_C(0xfedcba9876543210));
 CHECK(!gpe_submit(&c,0,10,0x8899,q,56,D,Z));CHECK(l.n==0);CHECK(c.count==1);CHECK(c.events[c.head].info.sequence==10);
 CHECK(c.extents[0].leases==1);CHECK(gpe_unregister(&c,D)==GPE_BUSY);CHECK(gpe_begin_batch(&c,2)==GPE_BUSY);
 CHECK(!gpe_deliver_one(&c));CHECK(l.n==2&&l.kind[0]==1&&l.value[0]==10&&l.kind[1]==2&&l.value[1]==0);
 CHECK(!c.extents[0].active);CHECK(gpe_deliver_one(&c)==GPE_EMPTY);CHECK(l.n==2);
 CHECK(!gpe_register(&c,(struct gpe_ref){545,2},BASE,dst,sizeof(dst)));
 struct gpe_ref d2={545,2};fill(q,0);q[38]=0;CHECK(!gpe_submit(&c,0,11,0x8899,q,56,d2,Z));
 fill(q,0);p64(q+40,0x123456789ULL);p64(q+48,UINT64_C(0xfedcba9876543210));CHECK(!gpe_submit(&c,0,12,0,q,56,d2,Z));
 CHECK(!gpe_submit(&c,4,13,0x8899,flush,24,Z,Z));
 CHECK(!gpe_deliver_one(&c));CHECK(!gpe_deliver_one(&c));CHECK(!gpe_deliver_one(&c));
 CHECK(l.n==5&&l.kind[2]==2&&l.kind[3]==1&&l.value[3]==12&&l.kind[4]==2);CHECK(gpe_deliver_one(&c)==GPE_EMPTY);
 fill(q,7);q[38]=0;CHECK(gpe_submit(&c,0,14,0x8899,q,56,d2,Z)==GPE_UNSUPPORTED);
 CHECK(gpe_submit(&c,4,15,0x8899,flush,24,Z,Z)==GPE_UNSUPPORTED);
 CHECK(!gpe_deliver_one(&c));CHECK(!gpe_deliver_one(&c));CHECK(l.value[5]==GPE_UNSUPPORTED&&l.value[6]==GPE_UNSUPPORTED);
 CHECK(c.batches[0].first_sequence==14&&c.batches[0].failures==2);
 CHECK(!gpe_begin_batch(&c,2));CHECK(!gpe_submit(&c,4,16,0x8899,flush,24,Z,Z));CHECK(!gpe_deliver_one(&c));CHECK(l.value[7]==0);
 l.fail=1;CHECK(!gpe_submit(&c,4,17,0x8899,flush,24,Z,Z));CHECK(gpe_deliver_one(&c)==GPE_DELIVERY);CHECK(c.batches[1].delivery_failures==1);CHECK(gpe_deliver_one(&c)==GPE_EMPTY);
 /* Callback dispatch failure cannot send a false sync success, nor retry. */
 fill(q,0);q[38]=0;p64(q+40,0x123456789ULL);p64(q+48,UINT64_C(0xfedcba9876543210));
 CHECK(!gpe_submit(&c,0,18,0x8899,q,56,d2,Z));CHECK(gpe_deliver_one(&c)==GPE_DELIVERY);
 CHECK(l.kind[l.n-2]==1&&l.kind[l.n-1]==2&&l.value[l.n-1]==GPE_DELIVERY);CHECK(gpe_deliver_one(&c)==GPE_EMPTY);
 tests++;return 0;
}
static int capacity(void) {
 struct gpe_context c;uint8_t dst[192],q[56],before[192];struct log l={0};CHECK(!setup(&c,dst,sizeof(dst),NULL,0,(struct gpe_hooks){&l,cb,status}));
 memset(dst,0xa5,sizeof(dst));fill(q,0);q[38]=0;
 for(unsigned i=0;i<GPE_EVENTS;i++)CHECK(!gpe_submit(&c,0,i,0x8899,q,56,D,Z));
 memcpy(before,dst,sizeof(dst));q[32]=255;CHECK(gpe_submit(&c,0,999,0x8899,q,56,D,Z)==GPE_CAPACITY);CHECK(!memcmp(before,dst,sizeof(dst)));
 CHECK(c.extents[0].leases==GPE_EVENTS);for(unsigned i=0;i<GPE_EVENTS;i++)CHECK(!gpe_deliver_one(&c));CHECK(c.extents[0].leases==0&&l.n==GPE_EVENTS);
 tests++;return 0;
}
int main(void) {
 if(pixels()||rejects()||copies()||completions()||capacity())return 1;
 printf("{\"result\":\"passed\",\"test_groups\":%u,\"assertions\":%u,\"sanitizers\":[\"address\",\"undefined\"]}\n",tests,assertions);return 0;
}
