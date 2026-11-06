/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <crypto/skcipher.h>
#include "crypto_skcipher_req.h"
#include "crypto_api_internal.h"
#include "sdebug.h"

int crypto_skcipher_request(struct crypto_info *ci)
{
	uint8_t *src_buf, *dst_buf;
	struct crypto_skcipher *tfm = crypto_alloc_skcipher(
		crypto_handle_get_algo_name(ci->base_param.cipher_algo), 0, 0);
	struct skcipher_request *req;
	struct crypto_wait wait;
	uint32_t keylen;
	unsigned int cryptlen;
	int i, data_num = ci->common_param.data_num;
	int skcipher_ret;
	uint8_t tmpiv[16];
#ifdef CRYPTO_CONFIG_DEBUG_PRINT_TIME
	uint64_t start_ns = ktime_get_ns(), end_ns;
	uint64_t debug_cryptlen = 0;
#endif /* CRYPTO_CONFIG_DEBUG_PRINT_TIME */

	if (IS_ERR(tfm)) {
		s_print(S_DEBUG_ERROR, "Failed to allocate tfm. %ld\n",
			PTR_ERR(tfm));
		return PTR_ERR(tfm);
	}
	req = skcipher_request_alloc(tfm, GFP_KERNEL);
	if (IS_ERR(req)) {
		s_print(S_DEBUG_ERROR, "Failed to allocate skcipher req\n");
		return -ENOMEM;
	}

	keylen = crypto_handle_get_cipher_keylen(ci->init_param.aes_key_len);
	skcipher_ret = crypto_skcipher_setkey(
		tfm, (u8 *)&ci->cipher_param.key[0], keylen);
	if (skcipher_ret != 0) {
		s_print(S_DEBUG_ERROR, "crypto_skcipher_setkey failed\n");
		goto crypto_skcipher_request_end;
	}

	for (i = 0; i < data_num; i++) {
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
			skcipher_ret = -ENOMEM;
			break;
		}

		crypto_set_sg_single(ci->base_param.src, src_buf, cryptlen);
		crypto_set_sg_single(ci->base_param.dst, dst_buf, cryptlen);

		crypto_init_wait(&wait);
		memcpy(tmpiv, ci->cipher_param.iv[i], sizeof(tmpiv));
		skcipher_request_set_crypt(req, ci->base_param.src,
					   ci->base_param.dst, cryptlen,
					   tmpiv);
		skcipher_request_set_callback(req, 0, crypto_req_done, &wait);
		if (ci->base_param.enc_flag) {
			skcipher_ret = crypto_skcipher_encrypt(req);
		} else {
			skcipher_ret = crypto_skcipher_decrypt(req);
		}
		skcipher_ret = crypto_wait_req(skcipher_ret, &wait);
		if (skcipher_ret != 0) {
			break;
		}

	}
crypto_skcipher_request_end:
	crypto_free_skcipher(tfm);
	skcipher_request_free(req);
#ifdef CRYPTO_CONFIG_DEBUG_PRINT_TIME
	end_ns = ktime_get_ns();
	s_print(S_DEBUG_ERROR, "size  %12llu byte.\n", debug_cryptlen);
	s_print(S_DEBUG_ERROR, "time  %12llu usec.\n", (end_ns - start_ns)/1000);
	s_print(S_DEBUG_ERROR, "      %12llu  bps.\n", debug_cryptlen * 8000000000ULL / (end_ns - start_ns));
#endif /* CRYPTO_CONFIG_DEBUG_PRINT_TIME */
	return skcipher_ret;
}
