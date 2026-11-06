#define gpe_init v8_gpe_init
#define gpe_register v8_gpe_register
#define gpe_unregister v8_gpe_unregister
#define gpe_acquire v8_gpe_acquire
#define gpe_release v8_gpe_release
#define gpe_begin_batch v8_gpe_begin_batch
#define gpe_plan_fill v8_gpe_plan_fill
#define gpe_plan_blit v8_gpe_plan_blit
#define gpe_submit v8_gpe_submit
#define gpe_deliver_one v8_gpe_deliver_one
#include "fx3-gpe-backend-v8.c"
uint32_t ref_blend(uint32_t s,uint32_t d,unsigned b,unsigned k){return straight_over_v1(s,d,b,k);}
uint32_t ref_a8(unsigned m,const uint8_t *t,uint32_t d,unsigned k){return a8_color_over_candidate(m,t,d,k);}
