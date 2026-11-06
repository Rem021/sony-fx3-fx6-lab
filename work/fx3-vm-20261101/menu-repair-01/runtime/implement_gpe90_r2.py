from pathlib import Path
R=Path(__file__).resolve().parent;H=R/'helpers'
s=(H/'fx3-gpe-resource-v1.inc').read_text().replace('U object,identity,type,logical,phys,bytes,epoch;','U object,identity,type,logical,phys,bytes,epoch,vptr;')
s=s.replace('r->object=(U)o;r->identity=', 'r->object=(U)o;r->vptr=load64(b);r->identity=')
s=s.replace('return a->object==b->object&&a->identity==b->identity','return a->object==b->object&&a->vptr==b->vptr&&a->identity==b->identity')
s=s.replace('static void resource_add(void *o){','static void resource_add(void *o,const char *origin){')
s=s.replace('scope=allocation_interval subblock_lifetime_unproven=1 queued_ABA_uncovered=1\\n",o,r.identity,r.type,r.uhdl,r.logical,r.phys,r.bytes,r.epoch);','scope=allocation_interval subblock_lifetime_unproven=1 queued_ABA_uncovered=1 vptr=%#lx registration_origin=%s\\n",o,r.identity,r.type,r.uhdl,r.logical,r.phys,r.bytes,r.epoch,r.vptr,origin);')
s=s.replace('resource_add(o);','resource_add(o,"native_open_return_v1");')
a=s.index('static int observe_resource_malloc(')
s=s[:a]+'''/* Approved supplement: successful original allocation exposes a live parent.
 * Exact resource log tuple is a cross-check only: same native class/vptr,
 * complete live fields, valid allocation span and nonoverlap are mandatory. */
static void malloc_parent_register(void *o,const struct resource_record*r,U ptr,U bytes){
 for(unsigned i=0;i<RESOURCE_LIMIT;i++)if(resources[i].active&&resources[i].object==(U)o)return;
 unsigned known_class=0,tuple=0,overlap=0;
 for(unsigned i=0;i<RESOURCE_LIMIT;i++)if(resources[i].active){
  struct resource_record*e=&resources[i];
  if(e->vptr&&r->vptr==e->vptr)known_class=1;
  if(r->phys<e->phys+e->bytes&&e->phys<r->phys+r->bytes)overlap=1;
  if(r->logical<e->logical+e->bytes&&e->logical<r->logical+r->bytes)overlap=1;
 }
 tuple=(r->phys==0x410524000UL&&r->bytes==0x400000UL)||(r->phys==0x410924000UL&&r->bytes==0x340000UL)||(r->phys==0x410c64000UL&&r->bytes==0x200000UL);
 int span=ptr>=r->logical&&ptr-r->logical<r->bytes&&bytes<=r->bytes-(ptr-r->logical);
 if(!known_class||!tuple||overlap||!span){dprintf(2,"FX3_GPE_RESOURCE_PARENT_REJECT object=%p vptr=%#lx same_original_class=%u exact_log_tuple=%u overlap=%u returned_span_valid=%u phys=%#lx bytes=%#lx\\n",o,r->vptr,known_class,tuple,overlap,span,r->phys,r->bytes);return;}
 resource_add(o,"malloc_parent_v1");
}
''' + s[a:]
s=s.replace('phys=r.phys+ptr-r.logical;','{phys=r.phys+ptr-r.logical;malloc_parent_register(o,&r,ptr,bytes);}')
s=s.replace('scope=allocation_interval compaction_uncovered=1 queued_ABA_uncovered=1\\n','scope=allocation_interval compaction_uncovered=1 queued_ABA_uncovered=1 malloc_parent_supplement=1\\n')
(H/'fx3-gpe-resource-v2.inc').write_text(s)
s=(H/'fx3-gpe-observe-v16-resources.c').read_text().replace('"fx3-gpe-resource-v1.inc"','"fx3-gpe-resource-v2.inc"').replace('adapter=v16 early_thread_bind=1','adapter=v16r2 early_thread_bind=1')
(H/'fx3-gpe-observe-v16r2-mallocparent.c').write_text(s)
s=(R/'build_gpe90.py').read_text().replace('fx3-gpe-observe-v16-resources','fx3-gpe-observe-v16r2-mallocparent').replace('fx3-gpe-resource-v1.inc','fx3-gpe-resource-v2.inc')
(R/'build_gpe90_r2.py').write_text(s)
print('v16r2 new source, v16 and resourcev1 frozen unchanged')
