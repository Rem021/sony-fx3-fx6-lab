/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPT_EMMC_INIT_TEE_CORE_H
#define CRYPT_EMMC_INIT_TEE_CORE_H

#include <linux/kernel.h>
#include <linux/tee_drv.h>

#define CRYPT_EMMC_SHM_LEN 128

/**
 * struct crypt_emmc_init_teedev - Private data
 * @dev:	OP-TEE based crypt_emmc_init device
 * @ctx:	OP-TEE context handler
 * @session_id:	PTA session identifier
 * @shm:	Shared Memory
 */
struct crypt_emmc_init_teedev {
	struct device *dev;
	struct tee_context *ctx;
	u32 session_id;

	struct tee_shm *shm_in;
};

struct crypt_emmc_init_teedev *crypt_emmc_init_tee_init(struct device *dev);
void crypt_emmc_init_tee_exit(struct crypt_emmc_init_teedev *teedev);
void crypt_emmc_init_tee_clear_shm(struct tee_shm *shm, size_t len);

#endif /* CRYPT_EMMC_INIT_TEE_CORE_H */
