#ifndef FX3_CONTROLLED_PORT_TRANSITION_H
#define FX3_CONTROLLED_PORT_TRANSITION_H
#include "stream.h"
/* Sampled topology association assumes physical custody/no device substitution.
 * It is not a serial number or cryptographic device authentication. */
int fx3_witness_init(fx3_port_witness *,const fx3_identity *,const uint8_t [16]);
int fx3_witness_arm(fx3_port_witness *,uint32_t,uint64_t,uint64_t);
int fx3_witness_sample(fx3_port_witness *,uint32_t,int,const fx3_identity *,uint64_t);
int fx3_witness_matches(const fx3_port_witness *,const fx3_identity *,uint32_t);
#endif
