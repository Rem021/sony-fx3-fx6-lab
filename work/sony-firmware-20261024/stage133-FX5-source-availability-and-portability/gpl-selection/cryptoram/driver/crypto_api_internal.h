/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_API_INTERNAL_H
#define CRYPTO_API_INTERNAL_H

#include <linux/scatterlist.h>

#include <mach/noncache.h>
#define crypto_phys_to_virt (void *)PHYS_TO_VA

struct crypto_data_type {
	uint8_t *buf;
	uint32_t len;
};

static inline void crypto_set_data(struct crypto_data_type *crypto_data,
				   uint8_t *buf, uint32_t len)
{
	crypto_data->buf = buf;
	crypto_data->len = len;
}

static inline void crypto_set_sg_single(struct scatterlist *sg, uint8_t *buf,
					size_t size)
{
	sg_init_table(sg, 1);
	sg_set_buf(sg, buf, size);
	sg_mark_end(sg);
}

static inline void crypto_set_sg_multi(struct scatterlist *sg,
				       struct crypto_data_type *crypto_data,
				       int nents)
{
	int i;
	sg_init_table(sg, nents);
	for (i = 0; i < nents; i++) {
		sg_set_buf(&sg[i], crypto_data[i].buf, crypto_data[i].len);
	}
	sg_mark_end(&sg[nents - 1]);
}

#endif /* CRYPTO_API_INTERNAL_H */
