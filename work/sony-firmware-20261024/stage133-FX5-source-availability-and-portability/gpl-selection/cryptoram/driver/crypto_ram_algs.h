/**
 * Copyright 2022 Sony Corporation
 * Copyright (c) 2018-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_RAM_ALGS_H
#define CRYPTO_RAM_ALGS_H

#include <crypto/aes.h>
#include <crypto/ctr.h>
#include <crypto/algapi.h>
#include <crypto/des.h>
#include <crypto/md5.h>
#include <crypto/sha1.h>
#include <crypto/sha2.h>
#include <linux/crypto.h>

#include "crypto_ram_core.h"

#define CRYPTO_RAM_ALG_PRIORITY 10000

struct crypto_alg *crypto_find_alg(const char *alg_name,
				   const struct crypto_type *frontend, u32 type,
				   u32 mask);

/* Utilities */

int crypto_ram_core_acquire_entry(struct crypto_ram_device *core, u8 *id);
void crypto_ram_core_release_entry(struct crypto_ram_device *core, u8 *id);

struct crypto_ram_key_alg_pair {
	u32 keybit;
	u8 alg;
};

static const struct crypto_ram_key_alg_pair encpair_aes_ecb[] = {
	{ 128, NETSEC_ENCRYPT_ALG_AESECB128 },
	{ 192, NETSEC_ENCRYPT_ALG_AESECB192 },
	{ 256, NETSEC_ENCRYPT_ALG_AESECB256 },
};

static const struct crypto_ram_key_alg_pair encpair_aes_cbc[] = {
	{ 128, NETSEC_ENCRYPT_ALG_AESCBC128 },
	{ 192, NETSEC_ENCRYPT_ALG_AESCBC192 },
	{ 256, NETSEC_ENCRYPT_ALG_AESCBC256 },
};

static const struct crypto_ram_key_alg_pair encpair_aes_ctr[] = {
	{ 128, NETSEC_ENCRYPT_ALG_AESCTR128 },
	{ 192, NETSEC_ENCRYPT_ALG_AESCTR192 },
	{ 256, NETSEC_ENCRYPT_ALG_AESCTR256 },
};

static const struct crypto_ram_key_alg_pair encpair_aes_gcm[] = {
	{ 128, NETSEC_ENCRYPT_ALG_AESGCM128 },
	{ 192, NETSEC_ENCRYPT_ALG_AESGCM192 },
	{ 256, NETSEC_ENCRYPT_ALG_AESGCM256 },
};

static const struct crypto_ram_key_alg_pair encpair_aes_ccm[] = {
	{ 128, NETSEC_ENCRYPT_ALG_AESCCM128 },
	{ 192, NETSEC_ENCRYPT_ALG_AESCCM192 },
	{ 256, NETSEC_ENCRYPT_ALG_AESCCM256 },
};

static const struct crypto_ram_key_alg_pair encpair_chachapoly[] = {
	{ 256, NETSEC_ENCRYPT_ALG_CHACHA20_POLY1305 },
};

static const struct crypto_ram_key_alg_pair authpair_aes_gcm[] = {
	{ 0, NETSEC_AUTH_ALG_AESGCM },
};

static const struct crypto_ram_key_alg_pair authpair_aes_ccm[] = {
	{ 0, NETSEC_AUTH_ALG_AESCCM },
};

static const struct crypto_ram_key_alg_pair authpair_chachapoly[] = {
	{ 0, NETSEC_AUTH_ALG_CHACHA20_POLY1305 },
};

int crypto_ram_get_pair_alg(const struct crypto_ram_key_alg_pair pair[],
			    int len, u32 keybit, u8 *alg);

int crypto_ram_core_configure_entry(struct crypto_ram_device *core, u8 id,
				    netsec_sa_data_t *sa);

int crypto_ram_core_set_driver_name(struct crypto_ram_device *core,
				    struct crypto_alg *alg);

#endif /* CRYPTO_RAM_ALGS_H */
