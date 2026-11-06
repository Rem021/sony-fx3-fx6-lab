/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <linux/mutex.h>
#include <linux/bits.h>
#include <linux/timer.h>
#include <linux/jiffies.h>
#include <linux/workqueue.h>
#include <linux/completion.h>
#include <linux/crypto.h>
#include <crypto/md5.h>
#include <crypto/sha2.h>
#include <crypto/sha3.h>
#ifdef CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT
#include <linux/delay.h>
#endif /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
#include "crypto_handle.h"
#include "crypto_config.h"
#include "crypto_skcipher_req.h"
#include "crypto_shash_req.h"
#include "crypto_aead_req.h"

#include "sdebug.h"

/* Notice) Not SA entry in Crypto-RAM */
#define CRYPTO_EXEC_ID_MAX (CRYPTO_CONFIG_ID_NUM)

/* Crypto-RAM M_AWADDR, M_ARADDR width[34:0] */
#define CRYPTO_RAM_AXI_ADDRESS_OVER (BIT_ULL(35))

#define CRYPTO_RAM_DATA_SIZE_MAX (0xffff0000)

static const struct {
	char *algo_name;
} crypto_table[E_CRYPTO_ALGO_MAX] = {
	[E_CRYPTO_ALGO_AES_ECB] = {
		.algo_name = "ecb(aes)",
	},
	[E_CRYPTO_ALGO_AES_CBC] = {
		.algo_name = "cbc(aes)",
	},
	[E_CRYPTO_ALGO_AES_CTR] = {
		.algo_name = "ctr(aes)",
	},
	[E_CRYPTO_ALGO_AES_CCM] = {
		.algo_name = "ccm(aes)",
	},
	[E_CRYPTO_ALGO_AES_GCM] = {
		.algo_name = "gcm(aes)",
	},
	[E_CRYPTO_ALGO_CHACHA_POLY] = {
		.algo_name = "rfc7539(chacha20,poly1305)",
	},
	[E_CRYPTO_ALGO_HMAC_MD5] = {
		.algo_name = "hmac(md5)",
	},
	[E_CRYPTO_ALGO_HMAC_SHA2_256] = {
		.algo_name = "hmac(sha256)",
	},
	[E_CRYPTO_ALGO_HMAC_SHA2_384] = {
		.algo_name = "hmac(sha384)",
	},
	[E_CRYPTO_ALGO_HMAC_SHA2_512] = {
		.algo_name = "hmac(sha512)",
	},
	[E_CRYPTO_ALGO_HMAC_SHA3_256] = {
		.algo_name = "hmac(sha3-256)",
	},
	[E_CRYPTO_ALGO_HMAC_SHA3_384] = {
		.algo_name = "hmac(sha3-384)",
	},
	[E_CRYPTO_ALGO_HMAC_SHA3_512] = {
		.algo_name = "hmac(sha3-512)",
	},
};

struct id_info {
	struct crypto_info ci;
	struct timer_list tl;
#ifdef CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT
	struct delayed_work ws;
#else /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	struct work_struct ws;
#endif /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	struct completion cmpl;
	int result;
	struct mutex info_sem;
};

struct crypto_id_handle {
	struct id_info info[CRYPTO_EXEC_ID_MAX];
	struct mutex id_sem;
};

static struct crypto_id_handle id_handle = { 0 };
static struct workqueue_struct *crypto_wq;

static inline bool op_mode_is_single(E_CRYPTO_OPERATIONMODE op_mode)
{
	return ((op_mode & E_CRYPTO_OPERATIONMODE_SINGLEDATA) != 0);
}

static inline bool op_mode_is_enc(E_CRYPTO_OPERATIONMODE op_mode)
{
	return ((op_mode & E_CRYPTO_OPERATIONMODE_ENC) != 0);
}

static inline bool op_mode_is_dec(E_CRYPTO_OPERATIONMODE op_mode)
{
	return ((op_mode & E_CRYPTO_OPERATIONMODE_DEC) != 0);
}

static inline bool op_mode_is_auth(E_CRYPTO_OPERATIONMODE op_mode)
{
	return ((op_mode & E_CRYPTO_OPERATIONMODE_AUTH) != 0);
}

static inline bool op_mode_is_cipher(E_CRYPTO_OPERATIONMODE op_mode)
{
	bool enc_flag = op_mode_is_enc(op_mode);
	bool dec_flag = op_mode_is_dec(op_mode);

	return (enc_flag || dec_flag);
}

static inline bool op_mode_is_encauth(E_CRYPTO_OPERATIONMODE op_mode)
{
	bool enc_flag = op_mode_is_enc(op_mode);
	bool auth_flag = op_mode_is_auth(op_mode);

	return (enc_flag && auth_flag);
}

static void crypto_handle_do_work(struct work_struct *work);

char *crypto_handle_get_algo_name(E_CRYPTO_ALGO algo)
{
	return crypto_table[algo].algo_name;
}

uint32_t crypto_handle_get_cipher_keylen(E_CRYPTO_AESKEYLEN cipher_keylen)
{
	uint32_t keylen = 0;

	switch (cipher_keylen) {
	case E_CRYPTO_AESKEYLEN_128:
		keylen = 16;
		break;
	case E_CRYPTO_AESKEYLEN_256:
		keylen = 32;
		break;
	default:
		break;
	}
	return keylen;
}

uint32_t crypto_handle_get_hmac_keylen(E_HASH_ALGO hash_algo)
{
	uint32_t keylen = 0;

	switch (hash_algo) {
	case E_HASH_ALGO_MD5:
		keylen = 16;
		break;
	case E_HASH_ALGO_SHA_256: /* fall-through */
	case E_HASH_ALGO_SHA3_256:
		keylen = 32;
		break;
	case E_HASH_ALGO_SHA_384: /* fall-through */
	case E_HASH_ALGO_SHA3_384:
		keylen = 48;
		break;
	case E_HASH_ALGO_SHA_512: /* fall-through */
	case E_HASH_ALGO_SHA3_512:
		keylen = 64;
		break;
	default:
		break;
	}
	return keylen;
}

uint32_t crypto_handle_get_cipher_blocklen(E_CRYPTO_MODE crypto_mode)
{
	uint32_t blocklen;

	switch (crypto_mode) {
	case E_CRYPTO_MODE_ECB: /* fall-through */
	case E_CRYPTO_MODE_CBC:
		blocklen = 16;
		break;
	default:
		blocklen = 1;
		break;
	}
	return blocklen;
}

static bool crypto_handle_try_set_todo_flag(uint32_t id)
{
	bool ret = false;

	mutex_lock(&id_handle.info[id].info_sem);
	if (!id_handle.info[id].ci.todo_flag &&
	    !id_handle.info[id].ci.run_hw_proc_flag) {
		id_handle.info[id].ci.todo_flag = true;
		ret = true;
	}
	mutex_unlock(&id_handle.info[id].info_sem);
	return ret;
}

static inline bool crypto_handle_get_todo_run_flag(uint32_t id)
{
	return (id_handle.info[id].ci.todo_flag ||
		id_handle.info[id].ci.run_hw_proc_flag);
}

static inline bool crypto_handle_is_id_valid(uint32_t id)
{
	return (id < CRYPTO_EXEC_ID_MAX) ? id_handle.info[id].ci.used_flag :
					   false;
}

static bool crypto_handle_is_executable(uint32_t id)
{
	E_CRYPTO_OPERATIONMODE operation_mode =
		id_handle.info[id].ci.init_param.operation_mode;
	bool enc_flag = op_mode_is_enc(operation_mode);
	bool dec_flag = op_mode_is_dec(operation_mode);
	bool auth_flag = op_mode_is_auth(operation_mode);

	if (!id_handle.info[id].ci.used_flag ||
	    !id_handle.info[id].ci.common_param_set_flag) {
		return false;
	}
	if ((enc_flag || dec_flag)) {
		if (!id_handle.info[id].ci.cipher_param_set_flag) {
			return false;
		}
	}
	if (auth_flag) {
		if (!id_handle.info[id].ci.auth_param_set_flag) {
			return false;
		}
	}
	return true;
}

void crypto_handle_mutex_init(void)
{
	int i;
	mutex_init(&id_handle.id_sem);
	for (i = 0; i < CRYPTO_EXEC_ID_MAX; i++) {
		mutex_init(&id_handle.info[i].info_sem);
	}
}

void crypto_handle_mutex_destroy(void)
{
	int i;
	mutex_destroy(&id_handle.id_sem);
	for (i = 0; i < CRYPTO_EXEC_ID_MAX; i++) {
		mutex_destroy(&id_handle.info[i].info_sem);
	}
}

int crypto_handle_workqueue_init(void)
{
	int i;

	crypto_wq = create_workqueue("crypto_workqueue");
	if (unlikely(!crypto_wq)) {
		s_print(S_DEBUG_ERROR, "create_workqueue failed.\n");
		return -1;
	}

	for (i = 0; i < ARRAY_SIZE(id_handle.info); i++) {
#ifdef CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT
		INIT_DELAYED_WORK(&id_handle.info[i].ws, crypto_handle_do_work);
#else /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
		INIT_WORK(&id_handle.info[i].ws, crypto_handle_do_work);
#endif /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	}

	return 0;
}

void crypto_handle_completion_init(void)
{
	int i;

	for (i = 0; i < ARRAY_SIZE(id_handle.info); i++) {
		init_completion(&id_handle.info[i].cmpl);
		s_print(S_DEBUG_DEBUG, "init_completion: %p.\n",
			&id_handle.info[i].cmpl);
	}
}

void crypto_handle_workqueue_destroy(void)
{
	flush_workqueue(crypto_wq);
	destroy_workqueue(crypto_wq);
}

static int crypto_handle_acquire_id(uint32_t *id,
				    struct cryptoRam_initParam *init_param)
{
	uint32_t i;
	int ret = -1;

	mutex_lock(&id_handle.id_sem);

	for (i = 0; i < CRYPTO_EXEC_ID_MAX; i++) {
		if (!id_handle.info[i].ci.used_flag) {
			*id = i;
			memcpy(&id_handle.info[i].ci.init_param, init_param,
			       sizeof(struct cryptoRam_initParam));
			id_handle.info[i].ci.used_flag = true;
			ret = 0;
			break;
		}
	}

	mutex_unlock(&id_handle.id_sem);

	return ret;
}

static int crypto_handle_release_id(uint32_t id)
{
	int ret = -1;

	mutex_lock(&id_handle.id_sem);

	if (id_handle.info[id].ci.used_flag) {
		memset(&id_handle.info[id].ci, 0x00,
		       sizeof(struct crypto_info));
		ret = 0;
	}

	mutex_unlock(&id_handle.id_sem);

	return ret;
}

static bool crypto_mode_is_valid(E_CRYPTO_MODE crypto_mode)
{
	bool ret;
	switch (crypto_mode) {
	case E_CRYPTO_MODE_ECB: /* fall-through */
	case E_CRYPTO_MODE_CBC: /* fall-through */
	case E_CRYPTO_MODE_CTR: /* fall-through */
	case E_CRYPTO_MODE_CCM: /* fall-through */
	case E_CRYPTO_MODE_GCM: /* fall-through */
	case E_CRYPTO_MODE_CHACHA20:
		ret = true;
		break;
	default:
		ret = false;
		break;
	}
	return ret;
}

static bool crypto_mode_is_skcipher(E_CRYPTO_MODE crypto_mode)
{
	bool ret;
	switch (crypto_mode) {
	case E_CRYPTO_MODE_ECB: /* fall-through */
	case E_CRYPTO_MODE_CBC: /* fall-through */
	case E_CRYPTO_MODE_CTR:
		ret = true;
		break;
	default:
		ret = false;
		break;
	}
	return ret;
}

static bool crypto_mode_is_aead(E_CRYPTO_MODE crypto_mode)
{
	bool ret;
	switch (crypto_mode) {
	case E_CRYPTO_MODE_CCM: /* fall-through */
	case E_CRYPTO_MODE_GCM: /* fall-through */
	case E_CRYPTO_MODE_CHACHA20:
		ret = true;
		break;
	default:
		ret = false;
		break;
	}
	return ret;
}

static bool aes_key_len_is_valid(E_CRYPTO_AESKEYLEN aes_key_len)
{
	bool ret;
	switch (aes_key_len) {
	case E_CRYPTO_AESKEYLEN_128: /* fall-through */
	case E_CRYPTO_AESKEYLEN_256:
		ret = true;
		break;
	default:
		ret = false;
		break;
	}
	return ret;
}

static bool chacha_key_len_is_valid(E_CRYPTO_MODE crypto_mode,
				    E_CRYPTO_AESKEYLEN aes_key_len)
{
	bool ret = true;
	if ((crypto_mode == E_CRYPTO_MODE_CHACHA20) &&
	    (aes_key_len != E_CRYPTO_AESKEYLEN_256)) {
		ret = false;
	}
	return ret;
}

static bool aes_gcm_icv_is_valid(uint8_t icvlen)
{
	bool ret;

	switch (icvlen) {
	case 4: /* fall-through */
	case 8: /* fall-through */
	case 12: /* fall-through */
	case 13: /* fall-through */
	case 14: /* fall-through */
	case 15: /* fall-through */
	case 16:
		ret = true;
		break;
	default:
		ret = false;
		break;
	}
	return ret;
}

static bool aes_ccm_icv_is_valid(uint8_t icvlen)
{
	bool ret;

	switch (icvlen) {
	case 4: /* fall-through */
	case 6: /* fall-through */
	case 8: /* fall-through */
	case 10: /* fall-through */
	case 12: /* fall-through */
	case 14: /* fall-through */
	case 16:
		ret = true;
		break;
	default:
		ret = false;
		break;
	}
	return ret;
}

static bool chacha_icv_is_valid(uint8_t icvlen)
{
	bool ret;

	switch (icvlen) {
	case 16:
		ret = true;
		break;
	default:
		ret = false;
		break;
	}
	return ret;
}

static bool aead_icv_is_valid(E_CRYPTO_MODE crypto_mode, uint8_t icvlen)
{
	bool ret;
	switch (crypto_mode) {
	case E_CRYPTO_MODE_CCM:
		ret = aes_ccm_icv_is_valid(icvlen);
		break;
	case E_CRYPTO_MODE_GCM:
		ret = aes_gcm_icv_is_valid(icvlen);
		break;
	case E_CRYPTO_MODE_CHACHA20:
		ret = chacha_icv_is_valid(icvlen);
		break;
	default:
		ret = false;
		break;
	}
	return ret;
}

static bool hash_algo_is_valid(E_HASH_ALGO hash_algo)
{
	bool ret;
	switch (hash_algo) {
	case E_HASH_ALGO_MD5: /* fall-through */
	case E_HASH_ALGO_SHA_256: /* fall-through */
	case E_HASH_ALGO_SHA_384: /* fall-through */
	case E_HASH_ALGO_SHA_512: /* fall-through */
	case E_HASH_ALGO_SHA3_256: /* fall-through */
	case E_HASH_ALGO_SHA3_384: /* fall-through */
	case E_HASH_ALGO_SHA3_512:
		ret = true;
		break;
	default:
		ret = false;
		break;
	}
	return ret;
}

static inline uint32_t get_digest_size(E_HASH_ALGO hash_algo)
{
	uint32_t digest_size = 0;
	switch (hash_algo) {
	case E_HASH_ALGO_MD5:
		digest_size = MD5_DIGEST_SIZE;
		break;
	case E_HASH_ALGO_SHA_256:
		digest_size = SHA256_DIGEST_SIZE;
		break;
	case E_HASH_ALGO_SHA_384:
		digest_size = SHA384_DIGEST_SIZE;
		break;
	case E_HASH_ALGO_SHA_512:
		digest_size = SHA512_DIGEST_SIZE;
		break;
	case E_HASH_ALGO_SHA3_256:
		digest_size = SHA3_256_DIGEST_SIZE;
		break;
	case E_HASH_ALGO_SHA3_384:
		digest_size = SHA3_384_DIGEST_SIZE;
		break;
	case E_HASH_ALGO_SHA3_512:
		digest_size = SHA3_512_DIGEST_SIZE;
		break;
	default:
		break;
	}
	return digest_size;
}

static E_CRYPTO_ERROR
crypto_check_init_param(struct cryptoRam_initParam *init_param)
{
	E_CRYPTO_OPERATIONMODE operation_mode = init_param->operation_mode;
	bool single_data_flag = op_mode_is_single(operation_mode);
	bool enc_flag = op_mode_is_enc(operation_mode);
	bool dec_flag = op_mode_is_dec(operation_mode);
	bool auth_flag = op_mode_is_auth(operation_mode);
	E_CRYPTO_MODE crypto_mode = init_param->crypto_mode;
	E_CRYPTO_AESKEYLEN aes_key_len = init_param->aes_key_len;

	/* No operation_mode */
	if (!enc_flag && !dec_flag && !auth_flag) {
		s_print(S_DEBUG_ERROR, "%s No valid operation mode set.(%x)\n",
			__func__, operation_mode);
		return E_CRYPTO_ERROR_OPMODE;
	}

	/* Unknown operation_mode */
	if (((operation_mode &
	      ~(E_CRYPTO_OPERATIONMODE_SINGLEDATA | E_CRYPTO_OPERATIONMODE_ENC |
		E_CRYPTO_OPERATIONMODE_AUTH | E_CRYPTO_OPERATIONMODE_DEC)) !=
	     0)) {
		s_print(S_DEBUG_ERROR, "%s operation_mode(%x) is invalid.\n",
			__func__, operation_mode);
		return E_CRYPTO_ERROR_OPMODE;
	}

	/* Unauthorized operation_mode */
	if (enc_flag && dec_flag) {
		s_print(S_DEBUG_ERROR,
			"%s Both ENC and DEC can not be set "
			"in operation mode(%x) together.\n",
			__func__, operation_mode);
		return E_CRYPTO_ERROR_OPMODE;
	}
	if (single_data_flag && auth_flag) {
		s_print(S_DEBUG_ERROR,
			"%s Both SINGLEDATA and AUTH can not be set "
			"in operation mode(%x) together.\n",
			__func__, operation_mode);
		return E_CRYPTO_ERROR_OPMODE;
	}

	if (dec_flag && auth_flag) {
		s_print(S_DEBUG_ERROR,
			"%s Both DEC and AUTH can not be set "
			"in operation mode(%x) together.\n",
			__func__, operation_mode);
		return E_CRYPTO_ERROR_OPMODE;
	}

	if (enc_flag || dec_flag) {
		if (!crypto_mode_is_valid(crypto_mode)) {
			s_print(S_DEBUG_ERROR,
				"%s crypto_mode(%u) is invalid.\n", __func__,
				crypto_mode);
			return E_CRYPTO_ERROR_MODE;
		}
		if (!aes_key_len_is_valid(aes_key_len)) {
			s_print(S_DEBUG_ERROR,
				"%s aes_key_len(%u) is invalid.\n", __func__,
				aes_key_len);
			return E_CRYPTO_ERROR_AESKEYLEN;
		}
		if (!chacha_key_len_is_valid(crypto_mode, aes_key_len)) {
			s_print(S_DEBUG_ERROR,
				"%s chacha20 key_len(%u) is invalid.\n",
				__func__, aes_key_len);
			return E_CRYPTO_ERROR_AESKEYLEN;
		}
		if (crypto_mode_is_aead(crypto_mode)) {
			if (single_data_flag) {
				s_print(S_DEBUG_ERROR,
					"%s Operation mode(%x) is SINGLEDATA, "
					"but crypto_mode(%u) is AEAD.\n",
					__func__, operation_mode, crypto_mode);
				return E_CRYPTO_ERROR_UNKNOWN;
			}
			if (auth_flag) {
				s_print(S_DEBUG_ERROR,
					"%s Operation mode(%x) is AUTH, "
					"but crypto_mode(%u) is AEAD.\n",
					__func__, operation_mode, crypto_mode);
				return E_CRYPTO_ERROR_UNKNOWN;
			}
		}
	}

	return E_CRYPTO_ERROR_OK;
}

static E_CRYPTO_ERROR
crypto_check_enc_param(struct crypto_info *info,
		       struct cryptoRam_encParam *enc_param)
{
	int i;
	struct cryptoRam_initParam *init_param = &info->init_param;
	struct crypto_common_param *common_param = &info->common_param;
	bool aead_flag = crypto_mode_is_aead(init_param->crypto_mode);

	for (i = 0; i < common_param->data_num; i++) {
		if (enc_param->encrypt_size[i] >= CRYPTO_RAM_DATA_SIZE_MAX) {
			s_print(S_DEBUG_ERROR,
				"%s encrypt_size[%d]:0x%08x is invalid.\n",
				__func__, i, enc_param->encrypt_size[i]);
			return E_CRYPTO_ERROR_ENCSIZE;
		}
		if ((crypto_mode_is_skcipher(init_param->crypto_mode)) &&
		    (enc_param->encrypt_size[i] == 0)) {
			s_print(S_DEBUG_ERROR, "%s encrypt_size[%d] is zero.\n",
				__func__, i);
			return E_CRYPTO_ERROR_ENCSIZE;
		}
		if ((enc_param->encrypt_size[i] %
		     crypto_handle_get_cipher_blocklen(
			     init_param->crypto_mode)) != 0) {
			s_print(S_DEBUG_ERROR,
				"%s encrypt_size[%d]:0x%08x is not an integer "
				"multiple of block length.\n",
				__func__, i, enc_param->encrypt_size[i]);
			return E_CRYPTO_ERROR_ENCSIZE;
		}
		if (aead_flag &&
		    !aead_icv_is_valid(init_param->crypto_mode,
				       enc_param->encrypt_icv[i])) {
			s_print(S_DEBUG_ERROR,
				"%s encrypt_icv[%d]:0x%08x invalid.\n",
				__func__, i, enc_param->encrypt_icv[i]);
			return E_CRYPTO_ERROR_UNKNOWN;
		}
	}

	return E_CRYPTO_ERROR_OK;
}

static E_CRYPTO_ERROR
crypto_check_dec_param(struct crypto_info *info,
		       struct cryptoRam_decParam *dec_param)
{
	int i;
	struct cryptoRam_initParam *init_param = &info->init_param;
	struct crypto_common_param *common_param = &info->common_param;
	bool aead_flag = crypto_mode_is_aead(init_param->crypto_mode);

	for (i = 0; i < common_param->data_num; i++) {
		if (dec_param->decrypt_size[i] >= CRYPTO_RAM_DATA_SIZE_MAX) {
			s_print(S_DEBUG_ERROR,
				"%s decrypt_size[%d]:0x%08x is invalid.\n",
				__func__, i, dec_param->decrypt_size[i]);
			return E_CRYPTO_ERROR_DECSIZE;
		}
		if ((crypto_mode_is_skcipher(init_param->crypto_mode)) &&
		    (dec_param->decrypt_size[i] == 0)) {
			s_print(S_DEBUG_ERROR, "%s decrypt_size[%d] is zero.\n",
				__func__, i);
			return E_CRYPTO_ERROR_DECSIZE;
		}
		if ((dec_param->decrypt_size[i] %
		     crypto_handle_get_cipher_blocklen(
			     init_param->crypto_mode)) != 0) {
			s_print(S_DEBUG_ERROR,
				"%s decrypt_size[%d]:0x%08x is not an integer "
				"multiple of block length.\n",
				__func__, i, dec_param->decrypt_size[i]);
			return E_CRYPTO_ERROR_DECSIZE;
		}
		if (aead_flag) {
			if (!aead_icv_is_valid(init_param->crypto_mode,
					       dec_param->decrypt_icv[i])) {
				s_print(S_DEBUG_ERROR,
					"%s decrypt_icv[%d]:0x%08x invalid.\n",
					__func__, i, dec_param->decrypt_icv[i]);
				return E_CRYPTO_ERROR_UNKNOWN;
			}
			if (dec_param->decrypt_size[i] <
			    dec_param->decrypt_icv[i]) {
				s_print(S_DEBUG_ERROR,
					"%s decrypt_size[%d]:0x%08x is smaller "
					"than decrypt_icv[%d]:0x%08x.\n",
					__func__, i, dec_param->decrypt_size[i],
					i, dec_param->decrypt_icv[i]);
				return E_CRYPTO_ERROR_DECSIZE;
			}
		}
	}

	return E_CRYPTO_ERROR_OK;
}

static E_CRYPTO_ERROR
crypto_check_auth_param(struct crypto_info *info,
			struct cryptoRam_authParam *auth_param)
{
	int i;
	struct crypto_common_param *common_param = &info->common_param;

	if (!hash_algo_is_valid(auth_param->hash_algo)) {
		s_print(S_DEBUG_ERROR, "%s hash_algo(%u) is invalid.\n",
			__func__, auth_param->hash_algo);
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	for (i = 0; i < common_param->data_num; i++) {
		if (auth_param->auth_size[i] >= CRYPTO_RAM_DATA_SIZE_MAX) {
			s_print(S_DEBUG_ERROR,
				"%s auth_size[%d]:0x%08x is invalid.\n",
				__func__, i, auth_param->auth_size[i]);
			return E_CRYPTO_ERROR_AUTHSIZE;
		}
	}

	return E_CRYPTO_ERROR_OK;
}

static bool encoffset_is_valid(struct crypto_info *info, uint8_t idx,
			       bool enc_flag, bool aead_flag, bool multi_data_mode_flag)
{
	struct crypto_common_param *common_param = &info->common_param;
	struct crypto_cipher_param *cipher_param = &info->cipher_param;
	uint64_t size_offset;

	if (enc_flag) {
		size_offset = cipher_param->size[idx] + cipher_param->offset[idx];
		if ((common_param->src_phys_addr + size_offset) >=
		    CRYPTO_RAM_AXI_ADDRESS_OVER) {
			s_print(S_DEBUG_ERROR,
				"%s src offset error detected. index[%d] "
				"src_addr:0x%016llx size:0x%08x offset:0x%08x\n",
				__func__, idx, common_param->src_phys_addr,
				cipher_param->size[idx],
				cipher_param->offset[idx]);
			return false;
		}
		if (!aead_flag) {
			if ((common_param->dst_phys_addr + size_offset) >=
			    CRYPTO_RAM_AXI_ADDRESS_OVER) {
				s_print(S_DEBUG_ERROR,
					"%s dst offset error detected. index[%d] "
					"dst_addr:0x%016llx size:0x%08x offset:0x%08x\n",
					__func__, idx,
					common_param->dst_phys_addr,
					cipher_param->size[idx],
					cipher_param->offset[idx]);
				return false;
			}
			if (multi_data_mode_flag &&
			    (size_offset > CRYPTO_MULTI_DATA_MODE_REGION_SIZE)) {
				s_print(S_DEBUG_ERROR,
					"%s offset error detected in Multi Data mode. index[%d] "
					"size:0x%08x offset:0x%08x\n",
					__func__, idx,
					cipher_param->size[idx],
					cipher_param->offset[idx]);
				return false;
			}
		} else {
			if ((common_param->dst_phys_addr + size_offset +
			     cipher_param->icvlen[idx]) >=
			    CRYPTO_RAM_AXI_ADDRESS_OVER) {
				s_print(S_DEBUG_ERROR,
					"%s dst offset error detected. index[%d] "
					"dst_addr:0x%016llx size:0x%08x offset:0x%08x icvlen:%08x\n",
					__func__, idx,
					common_param->dst_phys_addr,
					cipher_param->size[idx],
					cipher_param->offset[idx],
					cipher_param->icvlen[idx]);
				return false;
			}
			if (multi_data_mode_flag &&
			    (size_offset + cipher_param->icvlen[idx] >
				 CRYPTO_MULTI_DATA_MODE_REGION_SIZE)) {
				s_print(S_DEBUG_ERROR,
					"%s offset error detected in Multi Data mode. index[%d] "
					"size:0x%08x offset:0x%08x icvlen:%08x\n",
					__func__, idx,
					cipher_param->size[idx],
					cipher_param->offset[idx],
					cipher_param->icvlen[idx]);
				return false;
			}
		}
	}
	return true;
}

static bool decoffset_is_valid(struct crypto_info *info, uint8_t idx,
			       bool dec_flag, bool aead_flag, bool multi_data_mode_flag)
{
	struct crypto_common_param *common_param = &info->common_param;
	struct crypto_cipher_param *cipher_param = &info->cipher_param;
	uint64_t size_offset;

	if (dec_flag) {
		size_offset = cipher_param->size[idx] + cipher_param->offset[idx];
		if ((common_param->src_phys_addr + size_offset) >=
		    CRYPTO_RAM_AXI_ADDRESS_OVER) {
			s_print(S_DEBUG_ERROR,
				"%s src offset error detected. index[%d] "
				"src_addr:0x%016llx size:0x%08x offset:0x%08x\n",
				__func__, idx, common_param->src_phys_addr,
				cipher_param->size[idx],
				cipher_param->offset[idx]);
			return false;
		}
		if (!aead_flag) {
			if ((common_param->dst_phys_addr + size_offset) >=
			    CRYPTO_RAM_AXI_ADDRESS_OVER) {
				s_print(S_DEBUG_ERROR,
					"%s dst offset error detected. index[%d] "
					"dst_addr:0x%016llx size:0x%08x offset:0x%08x\n",
					__func__, idx,
					common_param->dst_phys_addr,
					cipher_param->size[idx],
					cipher_param->offset[idx]);
				return false;
			}
		} else {
			if ((common_param->dst_phys_addr + size_offset -
			     cipher_param->icvlen[idx]) >=
			    CRYPTO_RAM_AXI_ADDRESS_OVER) {
				s_print(S_DEBUG_ERROR,
					"%s dst offset error detected. index[%d] "
					"dst_addr:0x%016llx size:0x%08x offset:0x%08x icvlen:%08x\n",
					__func__, idx,
					common_param->dst_phys_addr,
					cipher_param->size[idx],
					cipher_param->offset[idx],
					cipher_param->icvlen[idx]);
				return false;
			}
		}
		if (multi_data_mode_flag) {
			if (size_offset > CRYPTO_MULTI_DATA_MODE_REGION_SIZE) {
				s_print(S_DEBUG_ERROR,
					"%s offset error detected in Multi Data mode. index[%d] "
					"size:0x%08x offset:0x%08x\n",
					__func__, idx,
					cipher_param->size[idx],
					cipher_param->offset[idx]);
				return false;
			}
		}
	}
	return true;
}

static bool authoffset_is_valid(struct crypto_info *info, uint8_t idx,
				bool auth_flag)
{
	struct crypto_common_param *common_param = &info->common_param;
	struct cryptoRam_authParam *auth_param = &info->auth_param;
	uint64_t size_offset;

	if (auth_flag) {
		size_offset = auth_param->auth_size[idx] + auth_param->auth_offset[idx];
		if ((common_param->src_phys_addr + size_offset) >=
		    CRYPTO_RAM_AXI_ADDRESS_OVER) {
			s_print(S_DEBUG_ERROR,
				"%s src offset error detected. index[%d] "
				"src_addr:0x%016llx auth_size:0x%08x auth_offset:0x%08x\n",
				__func__, idx, common_param->src_phys_addr,
				auth_param->auth_size[idx],
				auth_param->auth_offset[idx]);
			return false;
		}
		/* AUTH is always Multi Data mode */
		if (size_offset > CRYPTO_MULTI_DATA_MODE_REGION_SIZE) {
			s_print(S_DEBUG_ERROR,
				"%s offset error detected in Multi Data mode. index[%d] "
				"auth_size:0x%08x auth_offset:0x%08x\n",
				__func__, idx,
				auth_param->auth_size[idx],
				auth_param->auth_offset[idx]);
			return false;
		}
	}
	return true;
}

static bool hashoffset_is_valid(struct crypto_info *info, uint8_t idx,
				bool auth_flag)
{
	struct crypto_common_param *common_param = &info->common_param;
	struct cryptoRam_authParam *auth_param = &info->auth_param;
	uint32_t digest_size = get_digest_size(auth_param->hash_algo);
	uint64_t size_offset;

	if (auth_flag) {
		size_offset = digest_size + auth_param->hash_offset[idx];
		if ((common_param->dst_phys_addr + size_offset) >=
		    CRYPTO_RAM_AXI_ADDRESS_OVER) {
			s_print(S_DEBUG_ERROR,
				"%s dst offset error detected. index[%d] "
				"dst_addr:0x%016llx digest_size:0x%08x hash_offset:0x%08x\n",
				__func__, idx, common_param->src_phys_addr,
				digest_size, auth_param->hash_offset[idx]);
			return false;
		}
		/* AUTH is always Multi Data mode */
		if (size_offset > CRYPTO_MULTI_DATA_MODE_REGION_SIZE) {
			s_print(S_DEBUG_ERROR,
				"%s offset error detected. index[%d] "
				"digest_size:0x%08x hash_offset:0x%08x\n",
				__func__, idx, digest_size, auth_param->hash_offset[idx]);
			return false;
		}
	}
	return true;
}

static E_CRYPTO_ERROR crypto_check_exe_param(struct crypto_info *info)
{
	struct cryptoRam_initParam *init_param = &info->init_param;
	struct crypto_common_param *common_param = &info->common_param;
	bool enc_flag = op_mode_is_enc(init_param->operation_mode);
	bool dec_flag = op_mode_is_dec(init_param->operation_mode);
	bool auth_flag = op_mode_is_auth(init_param->operation_mode);
	bool aead_flag = crypto_mode_is_aead(init_param->crypto_mode);
	bool multi_data_mode_flag = !op_mode_is_single(init_param->operation_mode);
	int i;

	for (i = 0; i < common_param->data_num; i++) {
		if (!encoffset_is_valid(info, i, enc_flag, aead_flag,
					multi_data_mode_flag)) {
			return E_CRYPTO_ERROR_ENCOFFSET;
		}
		if (!decoffset_is_valid(info, i, dec_flag, aead_flag,
					multi_data_mode_flag)) {
			return E_CRYPTO_ERROR_DECOFFSET;
		}
		if (!authoffset_is_valid(info, i, auth_flag)) {
			return E_CRYPTO_ERROR_AUTHOFFSET;
		}
		if (!hashoffset_is_valid(info, i, auth_flag)) {
			return E_CRYPTO_ERROR_HASHOFFSET;
		}
	}
	return E_CRYPTO_ERROR_OK;
}

static inline E_CRYPTO_ALGO
crypto_handle_convert_cipher_algo(E_CRYPTO_MODE crypto_mode)
{
	E_CRYPTO_ALGO algo;

	switch (crypto_mode) {
	case E_CRYPTO_MODE_ECB:
		algo = E_CRYPTO_ALGO_AES_ECB;
		break;
	case E_CRYPTO_MODE_CBC:
		algo = E_CRYPTO_ALGO_AES_CBC;
		break;
	case E_CRYPTO_MODE_CTR:
		algo = E_CRYPTO_ALGO_AES_CTR;
		break;
	case E_CRYPTO_MODE_CCM:
		algo = E_CRYPTO_ALGO_AES_CCM;
		break;
	case E_CRYPTO_MODE_GCM:
		algo = E_CRYPTO_ALGO_AES_GCM;
		break;
	case E_CRYPTO_MODE_CHACHA20:
		algo = E_CRYPTO_ALGO_CHACHA_POLY;
		break;
	default:
		algo = E_CRYPTO_ALGO_MAX;
		break;
	}
	return algo;
}

static inline E_CRYPTO_ALGO
crypto_handle_convert_hash_algo(E_HASH_ALGO hash_mode)
{
	E_CRYPTO_ALGO algo;

	switch (hash_mode) {
	case E_HASH_ALGO_MD5:
		algo = E_CRYPTO_ALGO_HMAC_MD5;
		break;
	case E_HASH_ALGO_SHA_256:
		algo = E_CRYPTO_ALGO_HMAC_SHA2_256;
		break;
	case E_HASH_ALGO_SHA_384:
		algo = E_CRYPTO_ALGO_HMAC_SHA2_384;
		break;
	case E_HASH_ALGO_SHA_512:
		algo = E_CRYPTO_ALGO_HMAC_SHA2_512;
		break;
	case E_HASH_ALGO_SHA3_256:
		algo = E_CRYPTO_ALGO_HMAC_SHA3_256;
		break;
	case E_HASH_ALGO_SHA3_384:
		algo = E_CRYPTO_ALGO_HMAC_SHA3_384;
		break;
	case E_HASH_ALGO_SHA3_512:
		algo = E_CRYPTO_ALGO_HMAC_SHA3_512;
		break;
	default:
		algo = E_CRYPTO_ALGO_MAX;
		break;
	}
	return algo;
}

E_CRYPTO_ERROR crypto_handle_init(uint32_t *id,
				  struct cryptoRam_initParam *init_param)
{
	E_CRYPTO_ERROR ret;

	ret = crypto_check_init_param(init_param);
	if (ret != E_CRYPTO_ERROR_OK) {
		return ret;
	}

	if (crypto_handle_acquire_id(id, init_param) == 0) {
		/* Will not be E_CRYPTO_ALGO_MAX */
		id_handle.info[*id].ci.base_param.cipher_algo =
			crypto_handle_convert_cipher_algo(
				init_param->crypto_mode);

		ret = E_CRYPTO_ERROR_OK;

	} else {
		s_print(S_DEBUG_ERROR,
			"%s 32 IDs, the upper limit, have already been issued\n",
			__func__);
		ret = E_CRYPTO_ERROR_ID;
	}

	return ret;
}

E_CRYPTO_ERROR crypto_handle_exit(uint32_t id)
{
	E_CRYPTO_ERROR ret;

	if (!crypto_handle_is_id_valid(id)) {
		s_print(S_DEBUG_ERROR, "%s id(%u) is invalid.\n", __func__, id);
		return E_CRYPTO_ERROR_ID;
	}

	if (crypto_handle_get_todo_run_flag(id)) {
		s_print(S_DEBUG_ERROR,
			"%s HW processing is scheduled or running."
			"id(%u)\n",
			__func__, id);
		return E_CRYPTO_ERROR_BUSY;
	}

	if (crypto_handle_release_id(id) == 0) {
		ret = E_CRYPTO_ERROR_OK;
	} else {
		s_print(S_DEBUG_ERROR,
			"%s A non-issued ID(%u) was specified.\n", __func__,
			id);
		ret = E_CRYPTO_ERROR_ID;
	}

	return ret;
}

E_CRYPTO_ERROR
crypto_handle_set_crypto_param(uint32_t id,
			       struct cryptoRam_cryptoParam *crypto_param)
{
	E_CRYPTO_OPERATIONMODE operation_mode;
	bool single_data_flag;
	uint64_t src_phys_addr, dst_phys_addr;

	if (!crypto_handle_is_id_valid(id)) {
		s_print(S_DEBUG_ERROR, "%s id(%u) is invalid.\n", __func__, id);
		return E_CRYPTO_ERROR_ID;
	}

	if (crypto_handle_get_todo_run_flag(id)) {
		s_print(S_DEBUG_ERROR,
			"%s HW processing is scheduled or running."
			"id(%u)\n",
			__func__, id);
		return E_CRYPTO_ERROR_BUSY;
	}

	operation_mode = id_handle.info[id].ci.init_param.operation_mode;
	single_data_flag = op_mode_is_single(operation_mode);

	src_phys_addr = crypto_param->src_addr_lower |
			((uint64_t)crypto_param->src_addr_upper << 32);

	dst_phys_addr = crypto_param->dst_addr_lower |
			((uint64_t)crypto_param->dst_addr_upper << 32);

	if (single_data_flag) {
		if (crypto_param->data_num != 1) {
			s_print(S_DEBUG_ERROR,
				"%s Invalid data_num(%u) in single mode.\n",
				__func__, crypto_param->data_num);
			return E_CRYPTO_ERROR_DATANUM;
		}
		if (src_phys_addr >= CRYPTO_RAM_AXI_ADDRESS_OVER) {
			s_print(S_DEBUG_ERROR, "%s Invalid src_addr(%016llx).\n",
				__func__, src_phys_addr);
			return E_CRYPTO_ERROR_SRCADDR;
		}

		if (dst_phys_addr >= CRYPTO_RAM_AXI_ADDRESS_OVER) {
			s_print(S_DEBUG_ERROR, "%s Invalid dst_addr(%016llx).\n",
				__func__, dst_phys_addr);
			return E_CRYPTO_ERROR_DSTADDR;
		}

	} else {
		if ((crypto_param->data_num == 0) ||
		    (crypto_param->data_num > CRYPTO_DATA_NUM_MAX)) {
			s_print(S_DEBUG_ERROR, "%s Invalid data_num(%u).\n",
				__func__, crypto_param->data_num);
			return E_CRYPTO_ERROR_DATANUM;
		}
		if (src_phys_addr >=
		    (CRYPTO_RAM_AXI_ADDRESS_OVER -
		    (CRYPTO_MULTI_DATA_MODE_REGION_SIZE * crypto_param->data_num))) {
			s_print(S_DEBUG_ERROR,
					"%s Invalid src_addr(%016llx) and data_num(%u).\n",
					__func__, src_phys_addr, crypto_param->data_num);
			return E_CRYPTO_ERROR_SRCADDR;
		}
		if (dst_phys_addr >=
		    (CRYPTO_RAM_AXI_ADDRESS_OVER -
		    (CRYPTO_MULTI_DATA_MODE_REGION_SIZE * crypto_param->data_num))) {
			s_print(S_DEBUG_ERROR,
					"%s Invalid dst_addr(%016llx) and data_num(%u).\n",
					__func__, dst_phys_addr, crypto_param->data_num);
			return E_CRYPTO_ERROR_DSTADDR;
		}

	}

	/* If dst address is not set or in encauth mode, it will be src address */
	if (dst_phys_addr == 0 || op_mode_is_encauth(operation_mode)) {
		dst_phys_addr = src_phys_addr;
	}

	id_handle.info[id].ci.common_param.data_num = crypto_param->data_num;
	id_handle.info[id].ci.common_param.src_phys_addr = src_phys_addr;
	id_handle.info[id].ci.common_param.dst_phys_addr = dst_phys_addr;
	id_handle.info[id].ci.common_param_set_flag = true;

	return E_CRYPTO_ERROR_OK;
}

E_CRYPTO_ERROR crypto_handle_set_enc_param(uint32_t id,
					   struct cryptoRam_encParam *enc_param)
{
	E_CRYPTO_ERROR ret;
	E_CRYPTO_OPERATIONMODE operation_mode;
	bool enc_flag;

	if (!crypto_handle_is_id_valid(id)) {
		s_print(S_DEBUG_ERROR, "%s id(%u) is invalid.\n", __func__, id);
		return E_CRYPTO_ERROR_ID;
	}

	if (crypto_handle_get_todo_run_flag(id)) {
		s_print(S_DEBUG_ERROR,
			"%s HW processing is scheduled or running."
			"id(%u)\n",
			__func__, id);
		return E_CRYPTO_ERROR_BUSY;
	}

	operation_mode = id_handle.info[id].ci.init_param.operation_mode;
	enc_flag = op_mode_is_enc(operation_mode);
	if (!enc_flag) {
		s_print(S_DEBUG_ERROR,
			"%s Does not correspond to set operation mode"
			"(0x%x).\n",
			__func__, operation_mode);
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	ret = crypto_check_enc_param(&id_handle.info[id].ci, enc_param);
	if (ret != E_CRYPTO_ERROR_OK) {
		return ret;
	}

	memcpy(&id_handle.info[id].ci.cipher_param, enc_param,
	       sizeof(struct cryptoRam_encParam));
	id_handle.info[id].ci.cipher_param_set_flag = true;
	id_handle.info[id].ci.base_param.enc_flag = true;

	return E_CRYPTO_ERROR_OK;
}

E_CRYPTO_ERROR crypto_handle_set_dec_param(uint32_t id,
					   struct cryptoRam_decParam *dec_param)
{
	E_CRYPTO_ERROR ret;
	E_CRYPTO_OPERATIONMODE operation_mode;
	bool dec_flag;

	if (!crypto_handle_is_id_valid(id)) {
		s_print(S_DEBUG_ERROR, "%s id(%u) is invalid.\n", __func__, id);
		return E_CRYPTO_ERROR_ID;
	}

	if (crypto_handle_get_todo_run_flag(id)) {
		s_print(S_DEBUG_ERROR,
			"%s HW processing is scheduled or running."
			"id(%u)\n",
			__func__, id);
		return E_CRYPTO_ERROR_BUSY;
	}

	operation_mode = id_handle.info[id].ci.init_param.operation_mode;
	dec_flag = op_mode_is_dec(operation_mode);
	if (!dec_flag) {
		s_print(S_DEBUG_ERROR,
			"%s Does not correspond to set operation mode"
			"(0x%x).\n",
			__func__, operation_mode);
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	ret = crypto_check_dec_param(&id_handle.info[id].ci, dec_param);
	if (ret != E_CRYPTO_ERROR_OK) {
		return ret;
	}

	memcpy(&id_handle.info[id].ci.cipher_param, dec_param,
	       sizeof(struct cryptoRam_decParam));
	id_handle.info[id].ci.cipher_param_set_flag = true;
	id_handle.info[id].ci.base_param.enc_flag = false;

	return E_CRYPTO_ERROR_OK;
}

E_CRYPTO_ERROR
crypto_handle_set_auth_param(uint32_t id,
			     struct cryptoRam_authParam *auth_param)
{
	E_CRYPTO_ERROR ret;
	E_CRYPTO_OPERATIONMODE operation_mode;
	bool auth_flag;

	if (!crypto_handle_is_id_valid(id)) {
		s_print(S_DEBUG_ERROR, "%s id(%u) is invalid.\n", __func__, id);
		return E_CRYPTO_ERROR_ID;
	}

	if (crypto_handle_get_todo_run_flag(id)) {
		s_print(S_DEBUG_ERROR,
			"%s HW processing is scheduled or running."
			"id(%u)\n",
			__func__, id);
		return E_CRYPTO_ERROR_BUSY;
	}

	operation_mode = id_handle.info[id].ci.init_param.operation_mode;
	auth_flag = op_mode_is_auth(operation_mode);
	if (!auth_flag) {
		s_print(S_DEBUG_ERROR,
			"%s Does not correspond to set operation mode"
			"(0x%x).\n",
			__func__, operation_mode);
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	ret = crypto_check_auth_param(&id_handle.info[id].ci, auth_param);
	if (ret != E_CRYPTO_ERROR_OK) {
		return ret;
	}

	memcpy(&id_handle.info[id].ci.auth_param, auth_param,
	       sizeof(struct cryptoRam_authParam));
	id_handle.info[id].ci.base_param.hash_algo =
		crypto_handle_convert_hash_algo(auth_param->hash_algo);
	id_handle.info[id].ci.auth_param_set_flag = true;

	return E_CRYPTO_ERROR_OK;
}

/* timer callback routine */
static void crypto_handle_timer_expired(struct timer_list *t)
{
	struct id_info *info = container_of(t, struct id_info, tl);

	/* Cancel if possible */
	if (!info->ci.run_hw_proc_flag) {
		s_print(S_DEBUG_WARNING, "timer expired\n");

		info->result = E_CRYPTO_ERROR_TIMEOUT;
		complete(&info->cmpl);
		s_print(S_DEBUG_DEBUG, "complete: %p.\n", &info->cmpl);
	}
}

E_CRYPTO_ERROR crypto_handle_execute(uint32_t id, UINT32 timeout)
{
	E_CRYPTO_ERROR ret = E_CRYPTO_ERROR_OK;
	bool timer_enable_flag = (timeout != 0);
	struct timer_list *tl;

	if (!crypto_handle_is_id_valid(id)) {
		s_print(S_DEBUG_ERROR, "%s id(%u) is invalid.\n", __func__, id);
		return E_CRYPTO_ERROR_ID;
	}

	if (!crypto_handle_is_executable(id)) {
		s_print(S_DEBUG_ERROR,
			"%s Missing configuration for this id(%u).\n", __func__,
			id);
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	if (timeout > CRYPTO_CONFIG_TIMEOUT_MS) {
		s_print(S_DEBUG_ERROR, "%s timeout(%u) is over %u.\n", __func__,
			timeout, CRYPTO_CONFIG_TIMEOUT_MS);
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	ret = crypto_check_exe_param(&id_handle.info[id].ci);
	if (ret != E_CRYPTO_ERROR_OK) {
		return ret;
	}

	if (!crypto_handle_try_set_todo_flag(id)) {
		s_print(S_DEBUG_ERROR,
			"%s HW processing is scheduled or running."
			"id(%u)\n",
			__func__, id);
		return E_CRYPTO_ERROR_BUSY;
	}

	if (timer_enable_flag) {
		tl = &id_handle.info[id].tl;
		timer_setup(tl, crypto_handle_timer_expired, 0);
		mod_timer(tl, jiffies + msecs_to_jiffies(timeout));
	}

#ifdef CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT
	msleep(5); /* for timeout */
	queue_delayed_work(crypto_wq, &id_handle.info[id].ws,
	        msecs_to_jiffies(CRYPTO_CONFIG_DEBUG_DELAYED_WQ_MS)); /* for cancel */
#else /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	/* execute processing */
	queue_work(crypto_wq, &id_handle.info[id].ws);
#endif /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */

	if (timer_enable_flag) {
		del_timer_sync(tl);
	}
	return ret;
}

E_CRYPTO_ERROR crypto_handle_wait_completion(uint32_t id)
{
	E_CRYPTO_ERROR ret;

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, id);
	wait_for_completion(&id_handle.info[id].cmpl);
	s_print(S_DEBUG_DEBUG, "%s wakeup:%p\n", __func__,
		&id_handle.info[id].cmpl);
	ret = id_handle.info[id].result;
	if (ret == E_CRYPTO_ERROR_TIMEOUT) {
#ifdef CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT
		cancel_delayed_work_sync(&id_handle.info[id].ws);
#else /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
		/* If the work's callback appears to be running, */
		/* cancel_work_sync will block until it has completed. */
		cancel_work_sync(&id_handle.info[id].ws);
#endif /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	}

	mutex_lock(&id_handle.info[id].info_sem);
	id_handle.info[id].ci.todo_flag = false;
	id_handle.info[id].ci.run_hw_proc_flag = false;
	mutex_unlock(&id_handle.info[id].info_sem);

	return ret;
}

E_CRYPTO_ERROR crypto_handle_cancel(uint32_t id)
{
	E_CRYPTO_ERROR ret = E_CRYPTO_ERROR_OK;

	if (!crypto_handle_is_id_valid(id)) {
		s_print(S_DEBUG_ERROR, "%s id(%u) is invalid.\n", __func__, id);
		return E_CRYPTO_ERROR_ID;
	}

	if (id_handle.info[id].ci.run_hw_proc_flag) {
		s_print(S_DEBUG_ERROR,
			"%s HW processing is running."
			"id(%u)\n",
			__func__, id);
		return E_CRYPTO_ERROR_BUSY;
	}

	if (!id_handle.info[id].ci.todo_flag) {
		s_print(S_DEBUG_ERROR,
			"%s HW processing is not scheduled."
			"id(%u)\n",
			__func__, id);
		return E_CRYPTO_ERROR_UNKNOWN;
	}

#ifdef CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT
	cancel_delayed_work_sync(&id_handle.info[id].ws);
#else /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	/* If the work's callback appears to be running, */
	/* cancel_work_sync will block until it has completed. */
	cancel_work_sync(&id_handle.info[id].ws);
#endif /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	mutex_lock(&id_handle.info[id].info_sem);
	id_handle.info[id].result = E_CRYPTO_ERROR_CANCEL;
	mutex_unlock(&id_handle.info[id].info_sem);

	complete(&id_handle.info[id].cmpl);
	s_print(S_DEBUG_DEBUG, "complete: %p.\n", &id_handle.info[id].cmpl);

	return ret;
}

E_CRYPTO_ERROR crypto_handle_release(void)
{
	E_CRYPTO_ERROR ret = E_CRYPTO_ERROR_OK;
	uint32_t i;

	for (i = 0; i < CRYPTO_EXEC_ID_MAX; i++) {
		if (crypto_handle_get_todo_run_flag(i)) {
			s_print(S_DEBUG_ERROR,
				"%s HW processing is scheduled or running."
				"id(%u)\n",
				__func__, i);
			return E_CRYPTO_ERROR_BUSY;
		}
	}

	return ret;
}

static int crypto_handle_capi_request(struct crypto_info *ci)
{
	int ret = 0;

	/* encryption or decryption */
	if (op_mode_is_cipher(ci->init_param.operation_mode)) {
		/* skcipher */
		if (crypto_mode_is_skcipher(ci->init_param.crypto_mode)) {
			ret = crypto_skcipher_request(ci);
		/* aead */
		} else {
			ret = crypto_aead_request(ci);
			return ret;
		}
	}

	/* authentication */
	if (ret == 0 && op_mode_is_auth(ci->init_param.operation_mode)) {
		/* shash */
		ret = crypto_shash_request(ci);
	}

	return ret;
}

static void crypto_handle_do_work(struct work_struct *work)
{
#ifdef CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT
	struct id_info *info = container_of(work, struct id_info, ws.work);
#else /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	struct id_info *info = container_of(work, struct id_info, ws);
#endif /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	int ret;

	s_print(S_DEBUG_DEBUG, "work queue start\n");

	mutex_lock(&info->info_sem);
	info->ci.run_hw_proc_flag = true;
	info->ci.todo_flag = false;
	mutex_unlock(&info->info_sem);

	/* run crypto */
#ifdef CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT
	msleep(500); /* for cancel error */
#endif /* CRYPTO_CONFIG_DEBUG_CANCEL_TIMEOUT */
	ret = crypto_handle_capi_request(&info->ci);
	mutex_lock(&info->info_sem);
	if (ret == 0) {
		info->result = E_CRYPTO_ERROR_OK;
	} else {
		info->result = E_CRYPTO_ERROR_UNKNOWN;
	}
	mutex_unlock(&info->info_sem);

	complete(&info->cmpl);
	s_print(S_DEBUG_DEBUG, "complete: %p.\n", &info->cmpl);
}
