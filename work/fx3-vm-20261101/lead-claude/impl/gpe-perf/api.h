#include "fx3-gpe-backend-v9.h"
void v8_gpe_init(struct gpe_context*,struct gpe_hooks);
int v8_gpe_register(struct gpe_context*,struct gpe_ref,uint64_t,void*,size_t);
int v8_gpe_unregister(struct gpe_context*,struct gpe_ref);
int v8_gpe_acquire(struct gpe_context*,struct gpe_ref,struct gpe_lease*);
int v8_gpe_release(struct gpe_context*,struct gpe_lease*);
int v8_gpe_begin_batch(struct gpe_context*,uint64_t);
int v8_gpe_plan_fill(const void*,size_t,struct gpe_plan*);
int v8_gpe_plan_blit(const void*,size_t,struct gpe_plan*);
int v8_gpe_submit(struct gpe_context*,uint32_t,uint32_t,uint32_t,const void*,size_t,struct gpe_ref,struct gpe_ref);
int v8_gpe_deliver_one(struct gpe_context*);
uint32_t ref_blend(uint32_t,uint32_t,unsigned,unsigned),opt_blend(uint32_t,uint32_t,unsigned,unsigned);
uint32_t ref_a8(unsigned,const uint8_t*,uint32_t,unsigned),opt_a8(unsigned,const uint8_t*,uint32_t,unsigned);
unsigned opt_r255(unsigned);
