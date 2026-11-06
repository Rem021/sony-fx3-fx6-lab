/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include "crypt_emmc_init.h"
#include "crypt_emmc_init_tee_cmd.h"
#include "crypt_emmc_init_internal.h"
#include "crypt_emmc_init_external.h"
#include "crypt_emmc_init_print.h"

#define CRYPT_EMMC_UNIT_SIZE_MAX   0x1ffffff0
#define CRYPT_EMMC_UNIT_SIZE_BLOCK 0x10
#define CRYPT_EMMC_UNIT_SIZE_MIN   CRYPT_EMMC_UNIT_SIZE_BLOCK

E_CYPR_ERR cryptEmmcInit_init(void)
{
	struct crypt_emmc_init_teedev *teedev;
	struct crypt_emmc_init_cmd_init cmd_init = { 0 };
	int ret;

	crypt_emmc_pr_trace("%s", __func__);

	if (!is_eary_init()) {
		cmd_init.unit_size = get_unit_size();
		if (cmd_init.unit_size > CRYPT_EMMC_UNIT_SIZE_MAX) {
			crypt_emmc_pr_err("Unit size(%08x) exceeded limit",
					  cmd_init.unit_size);
			return E_CYPR_ERR_UNIT_SIZE_OVERSIZE;
		}

		if (cmd_init.unit_size < CRYPT_EMMC_UNIT_SIZE_MIN) {
			crypt_emmc_pr_err(
				"Unit size(%08x) is less than lower limit",
				cmd_init.unit_size);
			return E_CYPR_ERR_UNIT_SIZE_UNDERSIZE;
		}

		if ((cmd_init.unit_size % CRYPT_EMMC_UNIT_SIZE_BLOCK) != 0) {
			crypt_emmc_pr_err(
				"Unit size(%08x) is not an integral multiple of %d",
				cmd_init.unit_size, CRYPT_EMMC_UNIT_SIZE_BLOCK);
			return E_CYPR_ERR_UNIT_SIZE_NOT_16_MULTIPLE_BYTES;
		}

		if (crypt_emmc_init_hw_init() != 0) {
			crypt_emmc_pr_err("HW Initialization Failed");
			return E_CYPR_ERR_INIT;
		}

		/* Request initialize to OP-TEE */
		teedev = crypt_emmc_init_get_teedev();

		ret = crypt_emmc_init_tee_cmd_init(teedev, &cmd_init);
		if (ret != 0) {
			crypt_emmc_pr_err("OP-TEE pseudo-TA failed");
			return E_CYPR_ERR_INIT;
		}

		eMMC_CRYPT_KEY_SET();
	}

	return E_CYPR_ERR_OK;
}

E_CYPR_ERR cryptEmmcInit_setKey(ST_CYPR_KEY *pst_key)
{
	struct crypt_emmc_init_teedev *teedev = crypt_emmc_init_get_teedev();
	struct crypt_emmc_init_cmd_setkey cmd_setkey = { 0 };
	uint32_t keylen;
	int ret;

	crypt_emmc_pr_trace("%s", __func__);

	if (pst_key == NULL) {
		return E_CYPR_ERR_PARAM;
	}

	switch (pst_key->e_keyType) {
	case E_CYPR_KEYL_128:
		keylen = 16;
		break;
	case E_CYPR_KEYL_256:
		keylen = 32;
		break;
	default:
		return E_CYPR_ERR_KEYL;
	}

	/* Request setkey to OP-TEE */
	cmd_setkey.keylen = keylen;
	cmd_setkey.key1 = &pst_key->ui32_Key1_0;
	cmd_setkey.key2 = &pst_key->ui32_Key2_0;
	ret = crypt_emmc_init_tee_cmd_setkey(teedev, &cmd_setkey);
	if (ret != 0) {
		crypt_emmc_pr_err("OP-TEE pseudo-TA failed");
		return E_CYPR_ERR_INVALID;
	}

	return E_CYPR_ERR_OK;
}
#ifdef CRYPT_EMMC_INIT_CONFIG_DEBUG
EXPORT_SYMBOL(cryptEmmcInit_setKey);
#endif /* CRYPT_EMMC_INIT_CONFIG_DEBUG */
