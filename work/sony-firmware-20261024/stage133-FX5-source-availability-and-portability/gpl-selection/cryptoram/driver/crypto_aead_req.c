/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <crypto/aead.h>
#include "crypto_aead_req.h"
#include "crypto_api_internal.h"
#include "sdebug.h"

int crypto_aead_request(struct crypto_info *ci)
{
	uint8_t *src_buf, *dst_buf;
	struct crypto_data_type src_data[2], dst_data[2];
	uint8_t nents;
	struct crypto_aead *tfm = crypto_alloc_aead(
		crypto_handle_get_algo_name(ci->base_param.cipher_algo), 0, 0);
	struct aead_request *req;
	struct crypto_wait wait;
	uint32_t keylen;
	uint32_t cryptlen;
	uint32_t aadlen = 0;
	uint32_t icvlen;
	int i, data_num = ci->common_param.data_num;
	int aead_ret;
#ifdef CRYPTO_CONFIG_DEBUG_PRINT_TIME
	uint64_t start_ns = ktime_get_ns(), end_ns;
	uint64_t debug_cryptlen = 0;
#endif /* CRYPTO_CONFIG_DEBUG_PRINT_TIME */

	if (IS_ERR(tfm)) {
		s_print(S_DEBUG_ERROR, "Failed to allocate tfm. %ld\n",
			PTR_ERR(tfm));
		return PTR_ERR(tfm);
	}
	req = aead_request_alloc(tfm, GFP_KERNEL);
	if (IS_ERR(req)) {
		s_print(S_DEBUG_ERROR, "Failed to allocate aead req\n");
		return -ENOMEM;
	}

	keylen = crypto_handle_get_cipher_keylen(ci->init_param.aes_key_len);
	aead_ret =
		crypto_aead_setkey(tfm, (u8 *)&ci->cipher_param.key[0], keylen);
	if (aead_ret != 0) {
		s_print(S_DEBUG_ERROR, "crypto_aead_setkey failed\n");
		goto crypto_aead_request_end;
	}

	for (i = 0; i < data_num; i++) {
		nents = 0;
		icvlen = ci->cipher_param.icvlen[i];
		aead_ret = crypto_aead_setauthsize(tfm, icvlen);
		if (aead_ret != 0) {
			s_print(S_DEBUG_ERROR,
				"crypto_aead_setauthsize failed\n");
			break;
		}

		cryptlen = ci->cipher_param.size[i];
#ifdef CRYPTO_CONFIG_DEBUG_PRINT_TIME
		debug_cryptlen += cryptlen;
#endif /* CRYPTO_CONFIG_DEBUG_PRINT_TIME */
		src_buf = crypto_phys_to_virt(ci->common_param.src_phys_addr +
					      CRYPTO_MULTI_DATA_MODE_ADD_OFFSET(i) +
					      ci->cipher_param.offset[i]);
		dst_buf = crypto_phys_to_virt(ci->common_param.dst_phys_addr +
					      CRYPTO_MULTI_DATA_MODE_ADD_OFFSET(i) +
					      ci->cipher_param.offset[i]);
		if ((src_buf == NULL) || (dst_buf == NULL)) {
			s_print(S_DEBUG_ERROR, "Failed crypto_phys_to_virt\n");
			aead_ret = -ENOMEM;
			break;
		}
		crypto_set_data(&src_data[nents], src_buf, cryptlen);
		if (ci->base_param.enc_flag) {
			crypto_set_data(&dst_data[nents], dst_buf, cryptlen + icvlen);
		} else {
			crypto_set_data(&dst_data[nents], dst_buf, cryptlen - icvlen);
		}
		nents++;

		crypto_set_sg_multi(ci->base_param.src, src_data, nents);
		crypto_set_sg_multi(ci->base_param.dst, dst_data, nents);

		/*
		 * Crypto-API memory structure for cipher operation has the following structure:
		 *
		 * - AEAD encryption input:  assoc data || plaintext
		 * - AEAD encryption output: assoc data || ciphertext || auth tag
		 * - AEAD decryption input:  assoc data || ciphertext || auth tag
		 * - AEAD decryption output: assoc data || plaintext
		 */
		crypto_init_wait(&wait);
		aead_request_set_ad(req, aadlen);
		aead_request_set_crypt(req, ci->base_param.src,
				       ci->base_param.dst, cryptlen,
				       ci->cipher_param.iv[i]);
		aead_request_set_callback(req, 0, crypto_req_done, &wait);
		if (ci->base_param.enc_flag) {
			aead_ret = crypto_aead_encrypt(req);
		} else {
			aead_ret = crypto_aead_decrypt(req);
		}
		aead_ret = crypto_wait_req(aead_ret, &wait);
		if (aead_ret != 0) {
			break;
		}

	}
crypto_aead_request_end:
	crypto_free_aead(tfm);
	aead_request_free(req);
#ifdef CRYPTO_CONFIG_DEBUG_PRINT_TIME
	end_ns = ktime_get_ns();
	s_print(S_DEBUG_ERROR, "size  %12llu byte.\n", debug_cryptlen);
	s_print(S_DEBUG_ERROR, "time  %12llu usec.\n", (end_ns - start_ns)/1000);
	s_print(S_DEBUG_ERROR, "      %12llu  bps.\n", debug_cryptlen * 8000000000ULL / (end_ns - start_ns));
#endif /* CRYPTO_CONFIG_DEBUG_PRINT_TIME */
	return aead_ret;
}
