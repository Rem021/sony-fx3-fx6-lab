/**
 * Copyright 2022 Sony Corporation
 * Copyright (c) 2018-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_RAM_H
#define CRYPTO_RAM_H

#include <linux/version.h>
#include <linux/crypto.h>
#include <crypto/aead.h>
#include <crypto/internal/aead.h>
#include <crypto/hash.h>
#include <crypto/internal/hash.h>
#include <crypto/internal/skcipher.h>

#include "netsec_api.h"
#include "crypto_ram_print.h"

#define CRYPTO_RAM_ALG_TYPE_SKCIPHER BIT(0)
#define CRYPTO_RAM_ALG_TYPE_SHASH    BIT(1)
#define CRYPTO_RAM_ALG_TYPE_AEAD     BIT(2)

#define CRYPTO_RAM_SCAT_NUM_MAX 16

struct crypto_ram_config {
	const char *name;
	void *base;

	u32 hw_ver;

	u16 enc_raw_tx_desc_num;
	u16 enc_raw_rx_desc_num;
	u16 dec_raw_tx_desc_num;
	u16 dec_raw_rx_desc_num;

	u16 said_num;
	bool use_inta;
};

struct crypto_ram_device {
	const char *name;
	struct device *dev;
	struct clk *clk;
	struct reset_control *rst;

	netsec_handle_t handle;
	bool use_inta;
	struct tasklet_struct tasklet;
	u16 said_num;
	u8 sa_raw_use;
	u8 sa_raw_next;
	struct mutex said_sem;
	struct cdev_handle *cdev_handle;
};

/* Stores information of each calculation */
struct crypto_ram_calcinfo {
	union {
		void *req;
		struct aead_request *req_aead;
		struct skcipher_request *req_skcipher;
	};
	u32 type;
	struct crypto_wait wait;
	struct {
		u8 *buf;
		u32 nbytes;
	} data;
	u32 tx_num;
	netsec_frag_info_t *tx;
};

static inline struct crypto_ram_calcinfo *
crypto_ram_calcinfo_create(void *req, u32 type, u32 nbytes)
{
	struct crypto_ram_calcinfo *info =
		kzalloc(sizeof(struct crypto_ram_calcinfo), GFP_KERNEL);

	if (unlikely(!info))
		return NULL;

	info->req = req;
	info->type = type;
	info->data.nbytes = nbytes;
	if (nbytes > 0) {
		info->data.buf = kzalloc(nbytes, GFP_KERNEL);

		if (unlikely(!info->data.buf)) {
			kfree(info);
			return NULL;
		}
	} else {
		info->data.buf = NULL;
	}

	return info;
}

static inline void crypto_ram_set_tx_info(struct crypto_ram_calcinfo *info,
					  u32 tx_num, netsec_frag_info_t *tx)
{
	info->tx_num = tx_num;
	info->tx = tx;
}

static inline void crypto_ram_calcinfo_destroy(struct crypto_ram_calcinfo *info)
{
	if (unlikely(!info))
		return;

	if (info->data.nbytes > 0)
		kfree(info->data.buf);

	kfree(info);
}

/* 0: no error / -ENOMEM: DMA_MAPPING_ERROR  */
static inline int crypto_ram_set_frag_info(struct device *dev,
					   netsec_frag_info_t *frag, void *addr,
					   uint32_t len,
					   enum dma_data_direction dir)
{
	frag->addr = addr;
	frag->len = len;
	if (len != 0) {
		frag->phys_addr =
			dma_map_single(dev, frag->addr, frag->len, dir);
		return dma_mapping_error(dev, frag->phys_addr);
	}
	return 0;
}

#define crypto_ram_set_tx_frag_info(dev, frag, addr, len) \
	crypto_ram_set_frag_info(dev, frag, addr, len, DMA_TO_DEVICE)

#define crypto_ram_set_rx_frag_info(dev, frag, addr, len) \
	crypto_ram_set_frag_info(dev, frag, addr, len, DMA_FROM_DEVICE)

static inline void crypto_ram_unset_frag_info(struct device *dev,
					      netsec_frag_info_t *frag,
					      enum dma_data_direction dir)
{
	if (frag->len != 0) {
		dma_unmap_single(dev, frag->phys_addr, frag->len, dir);
		frag->addr = NULL;
		frag->len = 0;
	}
}

#define crypto_ram_unset_tx_frag_info(dev, frag) \
	crypto_ram_unset_frag_info(dev, frag, DMA_TO_DEVICE)

#define crypto_ram_unset_rx_frag_info(dev, frag) \
	crypto_ram_unset_frag_info(dev, frag, DMA_FROM_DEVICE)

int crypto_ram_init(struct crypto_ram_device *core,
		    struct crypto_ram_config *cfg);

void crypto_ram_uninit(struct crypto_ram_device *crypto_ram_dev);

irqreturn_t crypto_ram_irq_handler(int irq, void *dev_id);

#endif /* CRYPTO_RAM_H */
