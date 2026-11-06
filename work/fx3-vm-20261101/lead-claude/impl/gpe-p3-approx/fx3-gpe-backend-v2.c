#include "fx3-gpe-backend-v2.h"
#include <limits.h>
#include <stdatomic.h>
#include <string.h>
_Static_assert(sizeof(struct gpe_callback_info)==24,"CallbackInfo ABI");
_Static_assert(sizeof(struct gpe_callback_param)==16,"callback parameter ABI");
static uint32_t u32(const uint8_t *p) { return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24; }
static uint64_t u64(const uint8_t *p) { return u32(p)|(uint64_t)u32(p+4)<<32; }
static int64_t coord(const uint8_t *p) { uint32_t n=u32(p); return n<=INT32_MAX?(int64_t)n:(int64_t)n-INT64_C(4294967296); }
static void put32(uint8_t *p,uint32_t n) { for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i)); }
static int eq(struct gpe_ref a,struct gpe_ref b) { return a.handle==b.handle&&a.generation==b.generation; }
static int slot(struct gpe_context *c,struct gpe_ref r) { for(int i=0;i<GPE_EXTENTS;i++)if(eq(c->extents[i].ref,r)&&c->extents[i].active)return i;return -1; }
void gpe_init(struct gpe_context *c,struct gpe_hooks h) { memset(c,0,sizeof(*c));c->current=-1;c->hooks=h; }
int gpe_register(struct gpe_context *c,struct gpe_ref r,uint64_t base,void *cpu,size_t bytes) {
 if(c->delivering)return GPE_BUSY;
 if(!r.handle||!r.generation||!cpu||!bytes||bytes>UINT64_MAX-base||bytes>UINTPTR_MAX-(uintptr_t)cpu)return GPE_INVALID;
 int free_slot=-1;
 for(int i=0;i<GPE_EXTENTS;i++) {
  struct gpe_extent *e=&c->extents[i];
  if(e->ref.handle==r.handle) { if(e->active)return GPE_BUSY;if(r.generation<=e->ref.generation)return GPE_STALE;free_slot=i; }
  if(e->active) {
   if(base<e->physical_base+e->bytes&&e->physical_base<base+bytes)return GPE_OVERLAP;
   if((uintptr_t)cpu<(uintptr_t)e->cpu+e->bytes&&(uintptr_t)e->cpu<(uintptr_t)cpu+bytes)return GPE_OVERLAP;
  }
 }
 if(free_slot<0)for(int i=0;i<GPE_EXTENTS;i++)if(!c->extents[i].ref.handle){free_slot=i;break;}
 if(free_slot<0)return GPE_CAPACITY;
 c->extents[free_slot]=(struct gpe_extent){.ref=r,.physical_base=base,.cpu=cpu,.bytes=bytes,.active=1};return 0;
}
int gpe_unregister(struct gpe_context *c,struct gpe_ref r) {
 if(c->delivering)return GPE_BUSY;int i=slot(c,r);if(i<0)return GPE_STALE;
 struct gpe_extent *e=&c->extents[i];e->retiring=1;if(e->leases)return GPE_BUSY;e->active=0;return 0;
}
int gpe_acquire(struct gpe_context *c,struct gpe_ref r,struct gpe_lease *l) {
 if(c->delivering)return GPE_BUSY;if(!l||l->held)return GPE_INVALID;int i=slot(c,r);if(i<0)return GPE_STALE;
 struct gpe_extent *e=&c->extents[i];if(e->retiring)return GPE_STALE;if(e->leases==UINT32_MAX)return GPE_CAPACITY;
 e->leases++;*l=(struct gpe_lease){.ref=r,.slot=(unsigned)i,.held=1};return 0;
}
static int release_held(struct gpe_context *c,struct gpe_lease *l) {
 if(!l||!l->held||l->slot>=GPE_EXTENTS)return GPE_INVALID;
 struct gpe_extent *e=&c->extents[l->slot];if(!eq(l->ref,e->ref)||!e->leases)return GPE_STALE;
 e->leases--;l->held=0;if(!e->leases&&e->retiring)e->active=0;return 0;
}
int gpe_release(struct gpe_context *c,struct gpe_lease *l) {
 if(c->delivering)return GPE_BUSY;return release_held(c,l);
}
int gpe_begin_batch(struct gpe_context *c,uint64_t id) {
 if(c->delivering||c->count)return GPE_BUSY;if(c->batch_count==GPE_BATCHES)return GPE_CAPACITY;
 for(unsigned i=0;i<c->batch_count;i++)if(c->batches[i].id==id)return GPE_INVALID;
 c->current=(int)c->batch_count++;c->batches[c->current]=(struct gpe_batch){.id=id};return 0;
}
/* Coordinates are signed; arithmetic checked before byte-address conversion.
 * Row width must fit stride, and the last row's complete span is checked. */
static int address(uint64_t base,int64_t x,int64_t y,uint32_t stride,uint32_t w,uint32_t h,unsigned bpp,uint64_t *out,uint64_t *step) {
 if(x<0||y<0||!w||!h||h>GPE_MAX_ROWS||w>INT32_MAX||h>INT32_MAX||!stride||(uint64_t)x+w>stride)return GPE_BOUNDS;
 uint64_t row=(uint64_t)y, col=(uint64_t)x;
 if(row>UINT64_MAX/stride)return GPE_BOUNDS;
 uint64_t pix=row*stride;if(col>UINT64_MAX-pix)return GPE_BOUNDS;pix+=col;
 if(pix>UINT64_MAX/bpp)return GPE_BOUNDS;uint64_t off=pix*bpp;
 if(off>UINT64_MAX-base)return GPE_BOUNDS;*out=base+off;*step=(uint64_t)stride*bpp;
 uint64_t tail=(uint64_t)(h-1)*(*step),line=(uint64_t)w*bpp;
 if(tail>UINT64_MAX-*out||line>UINT64_MAX-(*out+tail))return GPE_BOUNDS;return 0;
}
int gpe_plan_fill(const void *raw,size_t n,struct gpe_plan *p) {
 if(!raw||!p||n!=56)return GPE_INVALID;const uint8_t *q=raw;
 /* selector0/K255 is exact replacement. Only selectors1/2 gain the
  * explicitly authorized approximate model; selector0/K<255 stays closed. */
 if(u32(q+28)>1||q[36]>2||(!q[36]&&q[37]!=255))return GPE_UNSUPPORTED;
 memset(p,0,sizeof(*p));p->bpp=u32(q+28)?4:2;p->rows=u32(q+20);p->line=(uint64_t)u32(q+16)*p->bpp;
 if(p->bpp==2)p->pixel=(q[32]>>4)<<12|(q[33]>>4)<<8|(q[34]>>4)<<4|(q[35]>>4);
 else p->pixel=(uint32_t)q[32]<<24|(uint32_t)q[33]<<16|(uint32_t)q[34]<<8|q[35];
 p->approx_blend=q[36]!=0;p->constant_alpha=q[37];
 return address(u64(q),coord(q+8),coord(q+12),u32(q+24),u32(q+16),p->rows,p->bpp,&p->dst,&p->dst_step);
}
int gpe_plan_blit(const void *raw,size_t n,struct gpe_plan *p) {
 if(!raw||!p||n!=144)return GPE_INVALID;const uint8_t *q=raw;
 if(u32(q+52)>1||u32(q+52)!=u32(q+92)||u32(q+104)||q[112]>1||q[113])return GPE_UNSUPPORTED;
 for(unsigned i=115;i<=118;i++)if(q[i])return GPE_UNSUPPORTED;
 if(q[119]>1||q[120]>1)return GPE_UNSUPPORTED;
 if(u32(q+16)!=u32(q+72)||u32(q+20)!=u32(q+76))return GPE_UNSUPPORTED;
 /* Scale slots are unused by b234. Accept only absent(0) or identity(1). */
 for(unsigned i=96;i<=100;i+=4)if(u32(q+i)&&u32(q+i)!=0x3f800000)return GPE_UNSUPPORTED;
 int64_t dx=coord(q+8)+coord(q+40)-coord(q+80),dy=coord(q+12)+coord(q+44)-coord(q+84);
 int64_t sx=coord(q+64),sy=coord(q+68);uint32_t w=u32(q+72),h=u32(q+76);
 int64_t cx=coord(q+24),cy=coord(q+28);uint32_t cw=u32(q+32),ch=u32(q+36);
 if(!w||!h||w>INT32_MAX||h>GPE_MAX_ROWS||!cw||!ch||cw>INT32_MAX||ch>INT32_MAX||cx<0||cy<0||sx<0||sy<0||dx<0||dy<0)return GPE_BOUNDS;
 /* Conservative clip gate: b234 does not program clip registers. Do not
  * invent partial clipping semantics; require the whole rectangle inside. */
 if(dx<cx||dy<cy||dx+w>cx+cw||dy+h>cy+ch)return GPE_BOUNDS;
 memset(p,0,sizeof(*p));p->blit=1;p->bpp=u32(q+52)?4:2;p->rows=h;p->line=(uint64_t)w*p->bpp;
 p->approx_blend=q[112]!=0||q[114]!=255;p->constant_alpha=q[114];
 p->flip_h=q[119];p->flip_v=q[120];
 int r=address(u64(q),dx,dy,u32(q+48),w,h,p->bpp,&p->dst,&p->dst_step);if(r)return r;
 return address(u64(q+56),sx,sy,u32(q+88),w,h,p->bpp,&p->src,&p->src_step);
}
static int spans(struct gpe_extent *e,uint64_t base,uint64_t step,uint64_t line,uint32_t rows) {
 for(uint32_t y=0;y<rows;y++) { uint64_t a=base+(uint64_t)y*step;
  if(a<e->physical_base||a-e->physical_base>e->bytes||line>e->bytes-(a-e->physical_base))return GPE_BOUNDS;
 }return 0;
}
static void unpin(struct gpe_context *c,struct gpe_lease *l) { if(l->held)(void)release_held(c,l); }
static uint32_t load_pixel(const uint8_t *p,unsigned bpp) {
 uint32_t v=0;for(unsigned b=0;b<bpp;b++)v|=(uint32_t)p[b]<<(8*b);return v;
}
/* Visual approximation only, not Sony factor decoding. For fmt0 the audited
 * input packing happens first; each nibble is then expanded by *17. Every
 * /255 stage rounds to nearest, and the final /17 rounds to nearest too. */
static uint32_t straight_over_v1(uint32_t src,uint32_t dst,unsigned bpp,unsigned k) {
 unsigned bits=bpp==2?4:8,mask=bpp==2?15:255,expand=bpp==2?17:1;
 unsigned as=(src&mask)*expand,ad=(dst&mask)*expand;
 unsigned a=(as*k+127)/255,inv=255-a;
 unsigned ao=a+(ad*inv+127)/255;
 uint32_t out=bpp==2?(ao+8)/17:ao;
 for(unsigned c=1;c<4;c++) {
  unsigned cs=((src>>(bits*c))&mask)*expand,cd=((dst>>(bits*c))&mask)*expand;
  unsigned co=(cs*a+cd*inv+127)/255;
  out|=(uint32_t)(bpp==2?(co+8)/17:co)<<(bits*c);
 }
 return out;
}
static int raster(struct gpe_context *c,struct gpe_plan *p,struct gpe_ref d,struct gpe_ref s,struct gpe_event *ev) {
 int r=gpe_acquire(c,d,&ev->dst);if(r)return r;
 struct gpe_extent *de=&c->extents[ev->dst.slot],*se=NULL;
 if(p->blit) { r=gpe_acquire(c,s,&ev->src);if(r)goto done;se=&c->extents[ev->src.slot]; }
 r=spans(de,p->dst,p->dst_step,p->line,p->rows);if(r)goto done;
 if(se) { r=spans(se,p->src,p->src_step,p->line,p->rows);if(r)goto done;
  uint64_t dend=p->dst+(p->rows-1)*p->dst_step+p->line,send=p->src+(p->rows-1)*p->src_step+p->line;
  if(p->src<dend&&p->dst<send){r=GPE_OVERLAP;goto done;}
 }
 for(uint32_t y=0;y<p->rows;y++) {
  uint8_t *dst=de->cpu+(size_t)(p->dst+(uint64_t)y*p->dst_step-de->physical_base);
  uint32_t sy=p->flip_v?p->rows-1-y:y;
  const uint8_t *src=se?se->cpu+(size_t)(p->src+(uint64_t)sy*p->src_step-se->physical_base):NULL;
  if(src&&!p->approx_blend&&!p->flip_h)memcpy(dst,src,(size_t)p->line);
  else for(uint64_t x=0;x<p->line;x+=p->bpp) {
   uint64_t sx=p->flip_h?p->line-p->bpp-x:x;
   uint32_t pixel=src?load_pixel(src+sx,p->bpp):p->pixel;
   if(p->approx_blend)pixel=straight_over_v1(pixel,load_pixel(dst+x,p->bpp),p->bpp,p->constant_alpha);
   for(unsigned b=0;b<p->bpp;b++)dst[x+b]=(uint8_t)(pixel>>(8*b));
  }
 }
 atomic_thread_fence(memory_order_release);
 done: if(r){unpin(c,&ev->src);unpin(c,&ev->dst);}return r;
}
static void failure(struct gpe_batch *b,uint32_t seq,int r) { b->failures++;if(!b->first_error){b->first_error=r;b->first_sequence=seq;} }
int gpe_submit(struct gpe_context *c,uint32_t op,uint32_t seq,uint32_t source,const void *raw,size_t n,struct gpe_ref d,struct gpe_ref s) {
 if(c->delivering)return GPE_BUSY;if(c->current<0)return GPE_INVALID;
 struct gpe_batch *b=&c->batches[c->current];b->commands++;
 const uint8_t *q=raw;size_t expected=op==0?56:op==1?144:op==4?24:0;
 int r=0;unsigned async=1;uint64_t fn=0,arg=0;
 if(!expected)r=GPE_UNSUPPORTED;else if(!q||n!=expected)r=GPE_INVALID;
 else {size_t a=op==0?38:op==1?121:0,f=op==0?40:op==1?128:8;async=q[a];fn=u64(q+f);arg=u64(q+f+8);if(!async&&!source)r=GPE_INVALID;}
 if(c->count==GPE_EVENTS){failure(b,seq,GPE_CAPACITY);return GPE_CAPACITY;}
 struct gpe_event ev={.info={seq,async?0:source,fn,arg}};
 if(!r) {struct gpe_plan p;if(op==0)r=gpe_plan_fill(q,n,&p);else if(op==1)r=gpe_plan_blit(q,n,&p);else r=b->first_error;
  if(!r&&op!=4)r=raster(c,&p,d,s,&ev);
 }
 if(r){failure(b,seq,r);ev.info.function=0;}
 ev.status=r;
 if(ev.info.function||ev.info.completion_source) {c->events[(c->head+c->count)%GPE_EVENTS]=ev;c->count++;}
 else {unpin(c,&ev.src);unpin(c,&ev.dst);}
 return r;
}
int gpe_deliver_one(struct gpe_context *c) {
 if(c->delivering)return GPE_BUSY;if(!c->count)return GPE_EMPTY;
 struct gpe_event ev=c->events[c->head];c->head=(c->head+1)%GPE_EVENTS;c->count--;c->delivering=1;
 atomic_thread_fence(memory_order_acquire);int r=0;
 if(ev.info.function) {uint8_t p[16]={0};put32(p,ev.info.sequence);for(unsigned i=0;i<8;i++)p[8+i]=(uint8_t)(ev.info.argument>>(8*i));
  if(!c->hooks.callback||c->hooks.callback(c->hooks.user,ev.info.function,p)){r=GPE_DELIVERY;ev.status=GPE_DELIVERY;}
 }
 if(ev.info.completion_source) {uint8_t p[4];put32(p,(uint32_t)ev.status);
  if(!c->hooks.status||c->hooks.status(c->hooks.user,ev.info.completion_source,p))r=GPE_DELIVERY;
 }
 unpin(c,&ev.src);unpin(c,&ev.dst);c->delivering=0;
 if(r)c->batches[c->current].delivery_failures++;return r;
}
