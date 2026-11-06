/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPT_EMMC_INIT_H
#define CRYPT_EMMC_INIT_H

#include <uapi/linux/rtnetlink.h>
#include "crypt_emmc_init_config.h"

typedef enum {
	E_CYPR_ERR_OK = 0,
	E_CYPR_ERR_KEYL,
	E_CYPR_ERR_PARAM,
	E_CYPR_ERR_ENC_OR_DEC, /* Reserved for future use */
	E_CYPR_ERR_INIT,
	E_CYPR_ERR_DEV_BUSY,
	E_CYPR_ERR_UNIT_SIZE_OVERSIZE,
	E_CYPR_ERR_UNIT_SIZE_UNDERSIZE,
	E_CYPR_ERR_UNIT_SIZE_NOT_16_MULTIPLE_BYTES,
	E_CYPR_ERR_PROC_LEN_OVERSIZE,
	E_CYPR_ERR_PROC_LEN_UNDERSIZE,
	E_CYPR_ERR_PROC_LEN_NOT_MULTIPLE_UNIT_SIZE,
	E_CYPR_ERR_PROC_LEN_SMALL_THAN_UNIT_SIZE,
	E_CYPR_ERR_INVALID,
	E_CYPR_ERR_NUMOF,
} E_CYPR_ERR;

typedef enum {
	E_CYPR_KEYL_128 = 0,
	E_CYPR_KEYL_256,
	E_CYPR_KEYL_NUMOF,
} E_CYPR_KEYL;

typedef struct {
	E_CYPR_KEYL e_keyType;
	uint32_t ui32_Key1_0;
	uint32_t ui32_Key1_1;
	uint32_t ui32_Key1_2;
	uint32_t ui32_Key1_3;
	uint32_t ui32_Key1_4;
	uint32_t ui32_Key1_5;
	uint32_t ui32_Key1_6;
	uint32_t ui32_Key1_7;
	uint32_t ui32_Key2_0;
	uint32_t ui32_Key2_1;
	uint32_t ui32_Key2_2;
	uint32_t ui32_Key2_3;
	uint32_t ui32_Key2_4;
	uint32_t ui32_Key2_5;
	uint32_t ui32_Key2_6;
	uint32_t ui32_Key2_7;
} ST_CYPR_KEY;

E_CYPR_ERR cryptEmmcInit_init(void);
#ifdef CRYPT_EMMC_INIT_CONFIG_DEBUG
E_CYPR_ERR cryptEmmcInit_setKey(ST_CYPR_KEY *pst_key);
#endif /* CRYPT_EMMC_INIT_CONFIG_DEBUG */

#endif /* CRYPT_EMMC_INIT_H */
