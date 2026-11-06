/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_PARAM_H
#define CRYPTO_PARAM_H

#include "crypto_type.h"

#define CRYPTO_DATA_NUM_MAX 255

typedef enum {
	E_CRYPTO_OPERATIONMODE_SINGLEDATA = 0x1,
	E_CRYPTO_OPERATIONMODE_ENC = 0x2,
	E_CRYPTO_OPERATIONMODE_AUTH = 0x4,
	E_CRYPTO_OPERATIONMODE_DEC = 0x8,
} E_CRYPTO_OPERATIONMODE;

typedef enum {
	E_CRYPTO_MODE_ECB = 0x1,
	E_CRYPTO_MODE_CBC = 0x2,
	E_CRYPTO_MODE_CTR = 0x3,
	E_CRYPTO_MODE_CCM = 0x4,
	E_CRYPTO_MODE_GCM = 0x5,
	E_CRYPTO_MODE_CHACHA20 = 0x6,
} E_CRYPTO_MODE;

typedef enum {
	E_HASH_ALGO_MD5 = 0x1,
	E_HASH_ALGO_SHA_256 = 0x2,
	E_HASH_ALGO_SHA_384 = 0x3,
	E_HASH_ALGO_SHA_512 = 0x4,
	E_HASH_ALGO_SHA3_256 = 0x5,
	E_HASH_ALGO_SHA3_384 = 0x6,
	E_HASH_ALGO_SHA3_512 = 0x7,
} E_HASH_ALGO;

typedef enum {
	E_CRYPTO_AESKEYLEN_128 = 0x1,
	E_CRYPTO_AESKEYLEN_256 = 0x2,
} E_CRYPTO_AESKEYLEN;

typedef enum {
	E_CRYPTO_ERROR_OK = 0,
	E_CRYPTO_ERROR_OPMODE,
	E_CRYPTO_ERROR_MODE,
	E_CRYPTO_ERROR_AESKEYLEN,
	E_CRYPTO_ERROR_ID,
	E_CRYPTO_ERROR_DATANUM,
	E_CRYPTO_ERROR_SRCADDR,
	E_CRYPTO_ERROR_DSTADDR,
	E_CRYPTO_ERROR_BUSY,
	E_CRYPTO_ERROR_ENCSIZE,
	E_CRYPTO_ERROR_ENCOFFSET,
	E_CRYPTO_ERROR_DECSIZE,
	E_CRYPTO_ERROR_DECOFFSET,
	E_CRYPTO_ERROR_AUTHSIZE,
	E_CRYPTO_ERROR_AUTHOFFSET,
	E_CRYPTO_ERROR_HASHOFFSET,
	E_CRYPTO_ERROR_TIMEOUT,
	E_CRYPTO_ERROR_CANCEL,
	E_CRYPTO_ERROR_UNKNOWN,
} E_CRYPTO_ERROR;

struct cryptoRam_initParam {
	E_CRYPTO_OPERATIONMODE operation_mode;
	E_CRYPTO_MODE crypto_mode;
	E_CRYPTO_AESKEYLEN aes_key_len;
};

struct cryptoRam_cryptoParam {
	UINT32 data_num;
	UINT32 src_addr_lower;
	UINT32 src_addr_upper;
	UINT32 dst_addr_lower;
	UINT32 dst_addr_upper;
};

struct cryptoRam_encParam {
	UINT32 encrypt_size[CRYPTO_DATA_NUM_MAX];
	UINT32 encrypt_offset[CRYPTO_DATA_NUM_MAX];
	UINT8 encrypt_key[32];
	UINT8 encrypt_iv[CRYPTO_DATA_NUM_MAX][16];
	UINT8 encrypt_icv[CRYPTO_DATA_NUM_MAX];
};

struct cryptoRam_decParam {
	UINT32 decrypt_size[CRYPTO_DATA_NUM_MAX];
	UINT32 decrypt_offset[CRYPTO_DATA_NUM_MAX];
	UINT8 decrypt_key[32];
	UINT8 decrypt_iv[CRYPTO_DATA_NUM_MAX][16];
	UINT8 decrypt_icv[CRYPTO_DATA_NUM_MAX];
};

struct cryptoRam_authParam {
	UINT32 auth_size[CRYPTO_DATA_NUM_MAX];
	UINT32 auth_offset[CRYPTO_DATA_NUM_MAX];
	UINT8 auth_key[64];
	E_HASH_ALGO hash_algo;
	UINT32 hash_offset[CRYPTO_DATA_NUM_MAX];
};

struct cryptoRam_exeParam {
	UINT32 timeout;
	void (*callback)(int id, E_CRYPTO_ERROR err);
};

#endif /* CRYPTO_PARAM_H */
