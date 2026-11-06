#include "fx3-gpe-backend-v9.c"
uint32_t opt_blend(uint32_t s,uint32_t d,unsigned b,unsigned k){return b==2?blend16((uint16_t)s,(uint16_t)d,k):blend32(s,d,k);}
uint32_t opt_a8(unsigned m,const uint8_t *t,uint32_t d,unsigned k){return a8_over16(m,t,(uint16_t)d,k);}
unsigned opt_r255(unsigned n){return r255(n);}
