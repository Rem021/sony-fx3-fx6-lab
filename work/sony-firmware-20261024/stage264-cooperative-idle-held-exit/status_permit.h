#ifndef FX3_STATUS_PERMIT_H
#define FX3_STATUS_PERMIT_H
#include <stdint.h>
#include <stddef.h>
int fx3_status_permit(const uint8_t nonce[16]);
int fx3_status_permit_bytes(const uint8_t *,size_t,const uint8_t nonce[16]);
#ifdef FX3_PERMIT_TEST
int fx3_status_permit_test_file(const char *,uint32_t,const uint8_t nonce[16]);
#endif
#endif
