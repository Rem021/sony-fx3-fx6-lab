from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'helpers'
def put(n,s):p=H/n;assert not p.exists(),p;p.write_text(s)
s=(H/'fx3-gpe-backend-v6.h').read_text().replace('BACKEND_V6_H','BACKEND_V7_H').replace('unsigned blit, approx_blend, constant_alpha, flip_h, flip_v;','unsigned blit, approx_blend, constant_alpha, flip_h, flip_v, empty_clip_noop;')
put('fx3-gpe-backend-v7.h',s)
s=(H/'fx3-gpe-backend-v6.c').read_text().replace('fx3-gpe-backend-v6.h','fx3-gpe-backend-v7.h')
a=' if(r<=l||b<=t||r-l>INT32_MAX||b-t>GPE_MAX_ROWS)return GPE_BOUNDS;'
s=s.replace(a,''' /* AP101 original cf2c->c878 and cf2c->bbcc both submit for an empty
  * intersection. Only this already-approved selector1 flag/format subset
  * gains no-op. Full source and destination geometry still validate below. */
 if(r<=l||b<=t){
  memset(p,0,sizeof(*p));p->blit=1;p->bpp=2;p->src_bpp=sf==2?1:2;p->empty_clip_noop=1;
  p->rows=dh;p->write_width=dw;p->line=(uint64_t)dw*2;
  p->src_rows=sh;p->source_width=sw;p->src_line=(uint64_t)sw*p->src_bpp;
  p->target_width=dw;p->target_height=dh;p->approx_blend=1;p->constant_alpha=q[114];p->approx_fmt2=sf==2;p->approx_stretch=dw!=sw||dh!=sh;
  memcpy(p->color,q+108,4);
  int z=address(u64(q),dx,dy,u32(q+48),dw,dh,2,&p->dst,&p->dst_step);if(z)return z;
  return address(u64(q+56),sx,sy,u32(q+88),sw,sh,p->src_bpp,&p->src,&p->src_step);
 }
 if(r-l>INT32_MAX||b-t>GPE_MAX_ROWS)return GPE_BOUNDS;''')
a=' /* All validation and both leases precede the first pixel write. */';assert a in s;s=s.replace(a,a+'''\n /* No source/destination pixel load or store before this point. Leases and
    exact full-rectangle bounds/overlap remain required even for no-op. */
 if(p->empty_clip_noop){atomic_thread_fence(memory_order_release);goto done;}''')
put('fx3-gpe-backend-v7.c',s)
s=(H/'fx3-gpe-observe-v20-const-alpha97.c').read_text().replace('fx3-gpe-backend-v6.h','fx3-gpe-backend-v7.h')
a='static void marker(unsigned op,unsigned seq,const unsigned char *p,int readable,int result,int reason){';assert a in s;s=s.replace(a,a+'\n struct gpe_plan checked_plan;unsigned empty=readable&&op==1&&!result&&!gpe_plan_blit(p,144,&checked_plan)&&checked_plan.empty_clip_noop;')
s=s.replace('rotation=%u src_fmt=%u\\n",','rotation=%u src_fmt=%u empty_clip_noop=%u\\n",')
a='readable&&op==1?load32(p+92):0);';assert a in s;s=s.replace(a,'readable&&op==1?load32(p+92):0,empty);')
a='  stage="backend_submit";reason=gpe_submit(&ctx,op,seq,0,execution,len,dst_ref,src_ref);if(reason)goto done;';assert a in s;s=s.replace(a,a+'''\n  if(plan.empty_clip_noop)dprintf(2,"FX3_GPE_EMPTY_CLIP_NOOP seq=%u empty_clip_noop=1 source_and_destination_full_bounds=1 resource_lifetime_validated=1 no_pixel_read=1 no_pixel_write=1 callback_and_status_normal=1 original_descriptor_submitted_for_empty_clip=1 hardware_execution=0\\n",seq);''')
put('fx3-gpe-observe-v21-emptyclip101.c',s)
print('v7 planner/backend and v21 adapter created')
