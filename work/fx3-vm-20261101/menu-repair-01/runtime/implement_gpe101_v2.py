from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'helpers'
def put(n,s):p=H/n;assert not p.exists(),p;p.write_text(s)
s=(H/'fx3-gpe-backend-v7.h').read_text().replace('BACKEND_V7_H','BACKEND_V8_H').replace('flip_v, empty_clip_noop;','flip_v, empty_clip_noop, approx_tile, dst_nominal_outside;\n uint64_t raw_dst_base;')
put('fx3-gpe-backend-v8.h',s)
s=(H/'fx3-gpe-backend-v7.c').read_text().replace('fx3-gpe-backend-v7.h','fx3-gpe-backend-v8.h')
s=s.replace('q[115]!=1||q[116]||q[118]','q[115]!=1||q[116]>1||q[118]')
a=' if(!dw||!dh||!sw||!sh||dw>INT32_MAX||sw>INT32_MAX||dh>GPE_MAX_ROWS||sh>GPE_MAX_ROWS)return GPE_BOUNDS;';assert s.count(a)==1
s=s.replace(a,a+'''\n /* P74=1 source-repeat subset: exact observed unity scale, power-of-two
    source crop, fmt0, selector1/K255/P73=1, all other flags unchanged. */
 unsigned tile=q[116]==1;
 if(tile&&(sf!=0||q[114]!=255||q[117]||u32(q+96)!=0x3f800000U||u32(q+100)!=0x3f800000U||(sw&(sw-1))||(sh&(sh-1))))return GPE_UNSUPPORTED;''')
a='''  p->rows=dh;p->write_width=dw;p->line=(uint64_t)dw*2;''';assert a in s;s=s.replace(a,'''  /* Nominal destination may lie wholly outside the clip/screen. Validate
     the real clip span and original base against the same live owner; no
     nominal-destination pixel address will ever be read or written. */
  p->rows=ch;p->write_width=cw;p->line=(uint64_t)cw*2;
  p->raw_dst_base=u64(q);p->dst_nominal_outside=1;p->approx_tile=tile;''')
s=s.replace('p->approx_stretch=dw!=sw||dh!=sh;','p->approx_stretch=tile?0:(dw!=sw||dh!=sh);')
s=s.replace('int z=address(u64(q),dx,dy,u32(q+48),dw,dh,2,&p->dst,&p->dst_step);if(z)return z;\n  return address(u64(q+56),sx,sy','int z=address(u64(q),cx,cy,u32(q+48),cw,ch,2,&p->dst,&p->dst_step);if(z)return z;\n  return address(u64(q+56),sx,sy')
a=' p->target_width=dw;p->target_height=dh;p->offset_x=(uint32_t)(l-dx);p->offset_y=(uint32_t)(t-dy);';assert a in s;s=s.replace(a,a+'\n p->raw_dst_base=u64(q);p->approx_tile=tile;p->dst_nominal_outside=dx<cx||dy<cy||dx+dw>cx+cw||dy+dh>cy+ch;')
a=' r=spans(de,p->dst,p->dst_step,p->line,p->rows);if(r)goto done;';assert a in s;s=s.replace(a,''' if(p->empty_clip_noop&&(p->raw_dst_base<de->physical_base||p->raw_dst_base-de->physical_base>de->bytes||p->bpp>de->bytes-(p->raw_dst_base-de->physical_base))){r=GPE_BOUNDS;goto done;}
'''+a)
a='''  if(se&&sy>=p->src_rows)sy=p->src_rows-1;''';assert a in s;s=s.replace(a,'''  if(se&&p->approx_tile)sy=(y+p->offset_y)&(p->src_rows-1);
'''+a)
a='''   if(se&&sx>=p->source_width)sx=p->source_width-1;''';assert a in s;s=s.replace(a,'''   if(se&&p->approx_tile)sx=(uint32_t)(x/p->bpp+p->offset_x)&(p->source_width-1);
'''+a)
put('fx3-gpe-backend-v8.c',s)
s=(H/'fx3-gpe-observe-v21-emptyclip101.c').read_text().replace('fx3-gpe-backend-v7.h','fx3-gpe-backend-v8.h')
a=' struct gpe_plan checked_plan;unsigned empty=readable&&op==1&&!result&&!gpe_plan_blit(p,144,&checked_plan)&&checked_plan.empty_clip_noop;';assert a in s;s=s.replace(a,''' struct gpe_plan checked_plan;unsigned valid_plan=readable&&op==1&&!result&&!gpe_plan_blit(p,144,&checked_plan);unsigned empty=valid_plan&&checked_plan.empty_clip_noop,outside=valid_plan&&checked_plan.dst_nominal_outside;const char*tile=valid_plan&&checked_plan.approx_tile?"repeat_mask_v1":"none";''')
s=s.replace('src_fmt=%u empty_clip_noop=%u\\n",','src_fmt=%u empty_clip_noop=%u dst_nominal_outside=%u approx_tile=%s\\n",').replace('load32(p+92):0,empty);','load32(p+92):0,empty,outside,tile);')
s=s.replace('source_and_destination_full_bounds=1 resource_lifetime_validated=1','source_full_crop_bounds=1 destination_clip_bounds=1 original_destination_base_same_owner=1 dst_nominal_outside=1 resource_lifetime_validated=1')
a='  if(plan.empty_clip_noop)dprintf';i=s.index(a);end=s.index('\n',i);s=s[:end]+'''\n  if(plan.approx_tile)dprintf(2,"FX3_GPE_TILE_APPLIED seq=%u approx_tile=repeat_mask_v1 source_width=%u source_height=%u source_origin_folded_into_physical=1 clip_offset_x=%u clip_offset_y=%u masks=%u,%u pixel_math=straight_over_v1 K=255 hardware_pixel_oracle=0\\n",seq,plan.source_width,plan.src_rows,plan.offset_x,plan.offset_y,plan.source_width-1,plan.src_rows-1);'''+s[end:]
put('fx3-gpe-observe-v22-tile101.c',s)
# Host regression sources are independent new files.
for old,new in [('check-gpe101-alpha-regression-v1.c','check-gpe101-v8-alpha-regression-v1.c'),('check-gpe101-native73-regression-v1.c','check-gpe101-v8-native73-regression-v1.c'),('check-emptyclip101-v1.c','check-emptyclip101-v2.c')]:
 s=(H/old).read_text().replace('fx3-gpe-backend-v7.c','fx3-gpe-backend-v8.c')
 if old=='check-emptyclip101-v1.c':
  s=s.replace('case 0:put32(p+48,500);','case 0:put32(p+48,500);') # clip ends637, so still invalid
  # Existing overlap check remains for nonempty operations. An empty clip
  # does not touch nominal src/dst overlap, but the validated clip owner
  # footprint still preserves the backend's existing overlap guard.
 put(new,s)
print('v8/v22 sources prepared; no frozen sources changed')
