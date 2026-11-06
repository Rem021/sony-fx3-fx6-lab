/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <crypto/hash.h>
#include <crypto/algapi.h>
#include "crypto_shash_req.h"
#include "crypto_api_internal.h"
#include "sdebug.h"

int crypto_shash_request(struct crypto_info *ci)
{
	uint8_t *src_buf, *dst_buf;
	struct crypto_shash *tfm = crypto_alloc_shash(
		crypto_handle_get_algo_name(ci->base_param.hash_algo), 0, 0);
	struct shash_desc *desc;
	uint32_t keylen;
	uint32_t nbytes;
	int i, data_num = ci->common_param.data_num;
	int shash_ret;
#ifdef CRYPTO_CONFIG_DEBUG_PRINT_TIME
	uint64_t start_ns = ktime_get_ns(), end_ns;
	uint64_t debug_nbytes = 0;
#endif /* CRYPTO_CONFIG_DEBUG_PRINT_TIME */

	if (IS_ERR(tfm)) {
		s_print(S_DEBUG_ERROR, "Failed to allocate tfm. %ld\n",
			PTR_ERR(tfm));
		return PTR_ERR(tfm);
	}

	desc = kzalloc(sizeof(*desc) + crypto_shash_descsize(tfm), GFP_KERNEL);
	if (IS_ERR(desc)) {
		s_print(S_DEBUG_ERROR, "Failed to allocate shash desc\n");
		return -ENOMEM;
	}
	desc->tfm = tfm;

	keylen = crypto_handle_get_hmac_keylen(ci->auth_param.hash_algo);
	shash_ret = crypto_shash_setkey(tfm, (u8 *)&ci->auth_param.auth_key[0],
					keylen);
	if (shash_ret != 0) {
		s_print(S_DEBUG_ERROR, "crypto_shash_setkey failed\n");
		goto crypto_shash_request_end;
	}

	for (i = 0; i < data_num; i++) {
		nbytes = ci->auth_param.auth_size[i];
#ifdef CRYPTO_CONFIG_DEBUG_PRINT_TIME
		debug_nbytes += nbytes;
#endif /* CRYPTO_CONFIG_DEBUG_PRINT_TIME */
		src_buf = crypto_phys_to_virt(ci->common_param.src_phys_addr +
					      CRYPTO_MULTI_DATA_MODE_ADD_OFFSET(i) +
					      ci->auth_param.auth_offset[i]);
		dst_buf = crypto_phys_to_virt(ci->common_param.dst_phys_addr +
					      CRYPTO_MULTI_DATA_MODE_ADD_OFFSET(i) +
					      ci->auth_param.hash_offset[i]);
		if ((src_buf == NULL) || (dst_buf == NULL)) {
			s_print(S_DEBUG_ERROR, "Failed crypto_phys_to_virt\n");
			shash_ret = -ENOMEM;
			break;
		}

		shash_ret = crypto_shash_digest(desc, src_buf, nbytes, dst_buf);
		if (shash_ret != 0) {
			break;
		}

	}
crypto_shash_request_end:
	crypto_free_shash(tfm);
	kfree_sensitive(desc);
#ifdef CRYPTO_CONFIG_DEBUG_PRINT_TIME
	end_ns = ktime_get_ns();
	s_print(S_DEBUG_ERROR, "size  %12llu byte.\n", debug_nbytes);
	s_print(S_DEBUG_ERROR, "time  %12llu usec.\n", (end_ns - start_ns)/1000);
	s_print(S_DEBUG_ERROR, "      %12llu  bps.\n", debug_nbytes * 8000000000ULL / (end_ns - start_ns));
#endif /* CRYPTO_CONFIG_DEBUG_PRINT_TIME */
	return shash_ret;
}
