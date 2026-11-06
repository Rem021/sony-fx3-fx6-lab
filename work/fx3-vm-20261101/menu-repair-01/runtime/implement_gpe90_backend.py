from pathlib import Path
import json
R=Path(__file__).resolve().parent;H=R/'helpers';L=R.parents[1]/'lead-claude/impl/gpe-p3-approx'
h=(L/'fx3-gpe-backend-v2.h').read_text().replace('BACKEND_V2','BACKEND_V3')
h=h.replace('unsigned blit, approx_blend, constant_alpha, flip_h, flip_v;', '''unsigned blit, approx_blend, constant_alpha, flip_h, flip_v;
 uint64_t src_line; uint32_t src_rows, src_bpp, source_width, target_width, target_height;
 uint32_t offset_x, offset_y, write_width; unsigned approx_fmt2, approx_stretch;
 uint8_t color[4];''')
(H/'fx3-gpe-backend-v3.h').write_text(h)
s=(L/'fx3-gpe-backend-v2.c').read_text().replace('"fx3-gpe-backend-v2.h"','"fx3-gpe-backend-v3.h"')
s=s.replace('int gpe_plan_blit(const void *raw,size_t n,struct gpe_plan *p) {','static int legacy_plan_blit(const void *raw,size_t n,struct gpe_plan *p) {',1)
pos=s.index('static int spans(')
s=s[:pos]+'''/* AP90 explicitly approximate, narrowly selected generic/nearest subset.
 * Source crop and destination clipped write spans are independent (fmt2=1B).
 * Read-only source allocation identity is supplied by the adapter, not addresses. */
int gpe_plan_blit(const void *raw,size_t n,struct gpe_plan *p) {
 if(!raw||!p||n!=144)return GPE_INVALID;
 const uint8_t *q=raw;
 if(!q[115]) {
  int r=legacy_plan_blit(raw,n,p);if(r)return r;
  p->src_bpp=p->bpp;p->src_line=p->line;p->src_rows=p->rows;
  p->source_width=p->target_width=p->write_width=(uint32_t)(p->line/p->bpp);p->target_height=p->rows;
  return 0;
 }
 uint32_t sf=u32(q+92),df=u32(q+52),dw=u32(q+16),dh=u32(q+20),sw=u32(q+72),sh=u32(q+76);
 if(df!=0||(sf!=0&&sf!=2)||u32(q+104)||q[112]!=1||q[113]||q[114]!=255||q[115]!=1||q[116]||q[118]||q[119]||q[120])return GPE_UNSUPPORTED;
 if((sf==0&&q[117])||(sf==2&&(q[117]!=14||q[111]!=255||dw!=sw||dh!=sh)))return GPE_UNSUPPORTED;
 if(!dw||!dh||!sw||!sh||dw>INT32_MAX||sw>INT32_MAX||dh>GPE_MAX_ROWS||sh>GPE_MAX_ROWS)return GPE_BOUNDS;
 int64_t dx=coord(q+8)+coord(q+40)-coord(q+80),dy=coord(q+12)+coord(q+44)-coord(q+84),sx=coord(q+64),sy=coord(q+68);
 int64_t cx=coord(q+24),cy=coord(q+28);uint32_t cw=u32(q+32),ch=u32(q+36);
 if(dx<0||dy<0||sx<0||sy<0||cx<0||cy<0||!cw||!ch||cw>INT32_MAX||ch>INT32_MAX)return GPE_BOUNDS;
 int64_t l=dx>cx?dx:cx,t=dy>cy?dy:cy,r=dx+dw<cx+cw?dx+dw:cx+cw,b=dy+dh<cy+ch?dy+dh:cy+ch;
 if(r<=l||b<=t||r-l>INT32_MAX||b-t>GPE_MAX_ROWS)return GPE_BOUNDS;
 memset(p,0,sizeof(*p));p->blit=1;p->bpp=2;p->src_bpp=sf==2?1:2;
 p->rows=(uint32_t)(b-t);p->write_width=(uint32_t)(r-l);p->line=(uint64_t)p->write_width*2;
 p->src_rows=sh;p->source_width=sw;p->src_line=(uint64_t)sw*p->src_bpp;
 p->target_width=dw;p->target_height=dh;p->offset_x=(uint32_t)(l-dx);p->offset_y=(uint32_t)(t-dy);
 p->approx_blend=1;p->constant_alpha=q[114];p->approx_fmt2=sf==2;p->approx_stretch=dw!=sw||dh!=sh;
 memcpy(p->color,q+108,4);
 int z=address(u64(q),l,t,u32(q+48),p->write_width,p->rows,2,&p->dst,&p->dst_step);if(z)return z;
 return address(u64(q+56),sx,sy,u32(q+88),sw,sh,p->src_bpp,&p->src,&p->src_step);
}
''' + s[pos:]
a=s.index('static int raster(');b=s.index('static void failure(',a)
s=s[:a]+'''/* Host vectors also exercise T3!=255 as math-only. The planner above
 * never admits that extension; actual AP90 text alpha already resides in K. */
static uint32_t a8_color_over_candidate(unsigned m,const uint8_t color[4],uint32_t dst,unsigned k){
 unsigned a=(((m*color[3]+127)/255)*k+127)/255,inv=255-a;
 unsigned ad=(dst&15)*17,ao=a+(ad*inv+127)/255;
 uint32_t out=(ao+8)/17;
 for(unsigned c=0;c<3;c++){
  unsigned dc=((dst>>(12-4*c))&15)*17,co=(color[c]*a+dc*inv+127)/255;
  out|=(uint32_t)((co+8)/17)<<(12-4*c);
 }
 return out;
}
static int raster(struct gpe_context *c,struct gpe_plan *p,struct gpe_ref d,struct gpe_ref s,struct gpe_event *ev) {
 int r=gpe_acquire(c,d,&ev->dst);if(r)return r;
 struct gpe_extent *de=&c->extents[ev->dst.slot],*se=NULL;
 if(p->blit) {r=gpe_acquire(c,s,&ev->src);if(r)goto done;se=&c->extents[ev->src.slot];}
 r=spans(de,p->dst,p->dst_step,p->line,p->rows);if(r)goto done;
 if(se){
  r=spans(se,p->src,p->src_step,p->src_line,p->src_rows);if(r)goto done;
  uint64_t dend=p->dst+(p->rows-1)*p->dst_step+p->line,send=p->src+(p->src_rows-1)*p->src_step+p->src_line;
  if(p->src<dend&&p->dst<send){r=GPE_OVERLAP;goto done;}
 }
 /* All validation and both leases precede the first pixel write. */
 for(uint32_t y=0;y<p->rows;y++){
  uint8_t *dst=de->cpu+(size_t)(p->dst+(uint64_t)y*p->dst_step-de->physical_base);
  uint32_t sy=se?(uint32_t)(((uint64_t)y+p->offset_y)*p->src_rows/p->target_height):0;
  if(p->flip_v)sy=p->src_rows-1-sy;
  const uint8_t *src=se?se->cpu+(size_t)(p->src+(uint64_t)sy*p->src_step-se->physical_base):NULL;
  for(uint64_t x=0;x<p->line;x+=p->bpp){
   uint32_t sx=se?(uint32_t)((x/p->bpp+p->offset_x)*p->source_width/p->target_width):0;
   if(p->flip_h)sx=p->source_width-1-sx;
   uint32_t pixel=src?load_pixel(src+(uint64_t)sx*p->src_bpp,p->src_bpp):p->pixel;
   if(p->approx_fmt2)pixel=a8_color_over_candidate(pixel,p->color,load_pixel(dst+x,p->bpp),p->constant_alpha);
   else if(p->approx_blend)pixel=straight_over_v1(pixel,load_pixel(dst+x,p->bpp),p->bpp,p->constant_alpha);
   for(unsigned b=0;b<p->bpp;b++)dst[x+b]=(uint8_t)(pixel>>(8*b));
  }
 }
 atomic_thread_fence(memory_order_release);
 done:if(r){unpin(c,&ev->src);unpin(c,&ev->dst);}return r;
}
''' + s[b:]
(H/'fx3-gpe-backend-v3.c').write_text(s)
print('backend-v3 source written, existing v2 unchanged')
