from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-gpe-resource-v2.inc').read_text();s=s.replace('unsigned uhdl,active;','unsigned uhdl,active,native_open;').replace('static U resource_epoch,allocation_events;','static U resource_epoch,allocation_events,resource_class_vptr;');s=s.replace('r.epoch=++resource_epoch;r.active=1;resources[slot]=r;','r.epoch=++resource_epoch;r.active=1;r.native_open=!strcmp(origin,"native_open_return_v1");resources[slot]=r;');s=s.replace('if(install_resource_hooks(m->base))','resource_class_vptr=m->base+0x253a48;\n if(install_resource_hooks(m->base))');(H/'fx3-gpe-resource-v3-target.inc').write_text(s)
s=(H/'fx3-gpe-observe-v16r2-mallocparent.c').read_text().replace('fx3-gpe-resource-v2.inc','fx3-gpe-resource-v3-target.inc');s=s.replace('U source_bytes=0,source_page=0;','U source_bytes=0,source_page=0,destination_map_bytes=0;');start=s.index('  reason=GPE_UNSUPPORTED;\n  if(!within(plan.dst');end=s.index('  life_leave();life_held=0;fills_done++;',start)
s=s[:start]+r'''
  int destination_screen=within(plan.dst,plan.dst_step,plan.line,plan.rows),same_parent=0;
  life_enter();life_held=1;U event_before=__atomic_load_n(&allocation_events,__ATOMIC_RELAXED);
  struct screen_identity si={0},after_si={0};struct resource_record sr={0},dr={0};unsigned count_before=0,count_after=0;
  if(!screen_live(&si)){reason=GPE_STALE;goto done;}
  if(!destination_screen){
   if(!obj_bound||!resource_lookup(plan.dst,plan.dst_step,plan.line,plan.rows,&dr)||!dr.native_open||dr.type!=0x403||!resource_class_vptr||dr.vptr!=resource_class_vptr){reason=GPE_STALE;goto done;}
  }
  int source_screen=op==1&&within(plan.src,plan.src_step,plan.src_line,plan.src_rows);
  if(op==1&&!source_screen){
   if(!obj_bound||!resource_lookup(plan.src,plan.src_step,plan.src_line,plan.src_rows,&sr)){reason=GPE_STALE;goto done;}
   (void)pread(process_mem,&count_before,4,(long)sr.object+0x24);
   same_parent=!destination_screen&&sr.object==dr.object&&sr.epoch==dr.epoch;
  }
  if(op==1&&!(destination_screen&&source_screen)&&!same_parent){
   U page=plan.src&~4095UL,tail=plan.src+(U)(plan.src_rows-1)*plan.src_step+plan.src_line;
   U requested=tail-page;if(requested>~0UL-4095){reason=GPE_BOUNDS;goto done;}
   source_bytes=(requested+4095)&~4095UL;source_page=page;
   source_area=mmap(0,source_bytes,1,1,physical,page);if(source_area==(void*)-1){reason=GPE_STALE;goto done;}
  }
  U destination_base=destination_screen?EXT_BASE:dr.phys,destination_size=destination_screen?EXT_BYTES:dr.bytes;
  U destination_page=destination_base&~4095UL,leading=destination_base-destination_page;
  if(destination_size>~0UL-leading-4095UL){reason=GPE_BOUNDS;goto done;}
  destination_map_bytes=(leading+destination_size+4095)&~4095UL;
  area=mmap(0,destination_map_bytes,3,1,physical,destination_page);if(area==(void*)-1){reason=GPE_STALE;goto done;}
  if(!screen_live(&after_si)||si.serial!=after_si.serial){reason=GPE_STALE;goto done;}
  if(!destination_screen){struct resource_record current={0};if(!object_fields((void*)dr.object,&current)||!resource_same(&dr,&current)){reason=GPE_STALE;goto done;}}
  struct gpe_context ctx;struct gpe_ref dst_ref=destination_screen?(struct gpe_ref){0x81,si.serial}:(struct gpe_ref){dr.object,dr.epoch},src_ref=dst_ref;
  gpe_init(&ctx,(struct gpe_hooks){0});reason=gpe_register(&ctx,dst_ref,destination_base,(unsigned char*)area+leading,destination_size);if(reason)goto done;
  if(op==1&&!(destination_screen&&source_screen)&&!same_parent){
   src_ref=source_screen?(struct gpe_ref){0x81,si.serial}:(struct gpe_ref){sr.object,sr.epoch};
   U envelope=(U)(plan.src_rows-1)*plan.src_step+plan.src_line;
   reason=gpe_register(&ctx,src_ref,plan.src,(unsigned char*)source_area+plan.src-source_page,envelope);if(reason)goto done;
  }
  reason=gpe_begin_batch(&ctx,1);if(reason)goto done;
  unsigned char execution[144];__builtin_memcpy(execution,raw,len);execution[ao]=1;__builtin_memset(execution+fo,0,16);
  reason=gpe_submit(&ctx,op,seq,0,execution,len,dst_ref,src_ref);if(reason)goto done;
  __atomic_thread_fence(__ATOMIC_SEQ_CST);
  if(sr.object)(void)pread(process_mem,&count_after,4,(long)sr.object+0x24);
  U event_after=__atomic_load_n(&allocation_events,__ATOMIC_RELAXED);
  dprintf(2,"FX3_GPE_SCOPE seq=%u screen_anchor_extent_id=0x81 screen_anchor_type=0x545 screen_serial=%#lx source_object=%#lx source_uhdl=%#x source_epoch=%lu source_type=%#lx source_phys=%#lx source_bytes=%#lx interval_lease=1 subblock_lifetime_unproven=1 queued_ABA_uncovered=1 compaction_uncovered=1 compaction_or_subblock_change_during_draw=%u native_count_before=%u native_count_after=%u approx_fmt2=%u original_fmt2_semantics_unproven=%u approx_stretch=%s\n",seq,si.serial,sr.object,sr.uhdl,sr.epoch,sr.type,sr.phys,sr.bytes,event_before!=event_after||count_before!=count_after,count_before,count_after,plan.approx_fmt2,plan.approx_fmt2,plan.approx_stretch?"nearest_v1":"none");
  if(!destination_screen){
   dprintf(2,"FX3_GPE_NATIVE_TARGET seq=%u destination_origin=native_open_type403_v1 object=%#lx identity=%#lx vptr=%#lx type=%#lx uhdl=%#x epoch=%lu phys=%#lx bytes=%#lx original_state10=1 original_fields_rechecked=1 per_row_parent_bounds=1 lifecycle_guard=1 source_alias_same_parent=%u screen_or_doublebuffer_role_unproven=1 bitmap_subblock_compaction_queuedABA_uncovered=1\n",seq,dr.object,dr.identity,dr.vptr,dr.type,dr.uhdl,dr.epoch,dr.phys,dr.bytes,same_parent);
   struct resource_record current={0};if(!object_fields((void*)dr.object,&current)||!resource_same(&dr,&current)){reason=GPE_STALE;goto done;}
  }
  if(!screen_live(&after_si)||si.serial!=after_si.serial){reason=GPE_STALE;goto done;}
  if(munmap(area,destination_map_bytes)){area=(void*)-1;reason=GPE_DELIVERY;goto done;}area=(void*)-1;
  if(source_area!=(void*)-1){if(munmap(source_area,source_bytes)){source_area=(void*)-1;reason=GPE_DELIVERY;goto done;}source_area=(void*)-1;}
'''+s[end:];s=s.replace('munmap(area,EXT_BYTES)','munmap(area,destination_map_bytes)').replace('adapter=v16r2','adapter=v17_native_target');(H/'fx3-gpe-observe-v17-native-target.c').write_text(s);print('v17 target adapter and registry v3 generated')
