/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPT_EMMC_INIT_TEE_CMD_H
#define CRYPT_EMMC_INIT_TEE_CMD_H

#include "crypt_emmc_init_tee_core.h"

/* Command ID */
#define CRYPT_EMMC_PTA_CMD_INIT	  0x00000001U
#define CRYPT_EMMC_PTA_CMD_SETKEY 0x00000002U

struct crypt_emmc_init_cmd_init {
	u32 unit_size;
};

struct crypt_emmc_init_cmd_setkey {
	unsigned int keylen;
	uint32_t *key1;
	uint32_t *key2;
};

int crypt_emmc_init_tee_cmd_init(struct crypt_emmc_init_teedev *teedev,
				 struct crypt_emmc_init_cmd_init *cmd_init);
int crypt_emmc_init_tee_cmd_setkey(
	struct crypt_emmc_init_teedev *teedev,
	struct crypt_emmc_init_cmd_setkey *cmd_setkey);

#endif /* CRYPT_EMMC_INIT_TEE_CMD_H */
