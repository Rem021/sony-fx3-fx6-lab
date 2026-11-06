/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_HANDLE_H
#define CRYPTO_HANDLE_H

#include <linux/uaccess.h>
#include <linux/scatterlist.h>
#include "crypto_param.h"
#include "crypto_type.h"

#define SGSIZE 3
#define CRYPTO_MULTI_DATA_MODE_REGION_SIZE   (2048)
#define CRYPTO_MULTI_DATA_MODE_ADD_OFFSET(i) (CRYPTO_MULTI_DATA_MODE_REGION_SIZE * i)

typedef enum {
	E_CRYPTO_ALGO_AES_ECB = 0,
	E_CRYPTO_ALGO_AES_CBC,
	E_CRYPTO_ALGO_AES_CTR,
	E_CRYPTO_ALGO_AES_CCM,
	E_CRYPTO_ALGO_AES_GCM,
	E_CRYPTO_ALGO_CHACHA_POLY,
	E_CRYPTO_ALGO_HMAC_MD5,
	E_CRYPTO_ALGO_HMAC_SHA2_256,
	E_CRYPTO_ALGO_HMAC_SHA2_384,
	E_CRYPTO_ALGO_HMAC_SHA2_512,
	E_CRYPTO_ALGO_HMAC_SHA3_256,
	E_CRYPTO_ALGO_HMAC_SHA3_384,
	E_CRYPTO_ALGO_HMAC_SHA3_512,
	E_CRYPTO_ALGO_MAX,
} E_CRYPTO_ALGO;

struct crypto_base_param {
	uint32_t keylen;
	E_CRYPTO_ALGO cipher_algo;
	E_CRYPTO_ALGO hash_algo;
	bool enc_flag; /* used with skcipher or aead */
	struct scatterlist src[SGSIZE];
	struct scatterlist dst[SGSIZE];
};

struct crypto_common_param {
	int data_num;
	uint64_t src_phys_addr;
	uint64_t dst_phys_addr;
};

/* Note: Must have the same coniguration as enc_param and dec_param */
struct crypto_cipher_param {
	uint32_t size[CRYPTO_DATA_NUM_MAX];
	uint32_t offset[CRYPTO_DATA_NUM_MAX];
	uint8_t key[32];
	uint8_t iv[CRYPTO_DATA_NUM_MAX][16];
	uint8_t icvlen[CRYPTO_DATA_NUM_MAX];
};

struct crypto_info {
	bool used_flag;
	struct crypto_base_param base_param;
	struct cryptoRam_initParam init_param;
	bool common_param_set_flag;
	struct crypto_common_param common_param;
	bool cipher_param_set_flag;
	struct crypto_cipher_param cipher_param;
	bool auth_param_set_flag;
	struct cryptoRam_authParam auth_param;
	bool todo_flag; /* for cancel or timeout */
	bool run_hw_proc_flag; /* request to crypto framework */
};

void crypto_handle_mutex_init(void);
void crypto_handle_mutex_destroy(void);
int crypto_handle_workqueue_init(void);
void crypto_handle_workqueue_destroy(void);
void crypto_handle_completion_init(void);

E_CRYPTO_ERROR crypto_handle_init(uint32_t *id,
				  struct cryptoRam_initParam *init_param);
E_CRYPTO_ERROR crypto_handle_exit(uint32_t id);
E_CRYPTO_ERROR
crypto_handle_set_crypto_param(uint32_t id,
			       struct cryptoRam_cryptoParam *crypto_param);
E_CRYPTO_ERROR
crypto_handle_set_enc_param(uint32_t id, struct cryptoRam_encParam *enc_param);
E_CRYPTO_ERROR
crypto_handle_set_dec_param(uint32_t id, struct cryptoRam_decParam *dec_param);
E_CRYPTO_ERROR
crypto_handle_set_auth_param(uint32_t id,
			     struct cryptoRam_authParam *auth_param);
E_CRYPTO_ERROR crypto_handle_execute(uint32_t id, UINT32 timeout);
E_CRYPTO_ERROR crypto_handle_wait_completion(uint32_t id);
E_CRYPTO_ERROR crypto_handle_cancel(uint32_t id);
E_CRYPTO_ERROR crypto_handle_release(void);

char *crypto_handle_get_algo_name(E_CRYPTO_ALGO algo);
uint32_t crypto_handle_get_cipher_keylen(E_CRYPTO_AESKEYLEN cipher_keylen);
uint32_t crypto_handle_get_hmac_keylen(E_HASH_ALGO hash_algo);

#endif /* CRYPTO_HANDLE_H */
