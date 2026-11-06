/**
 * Copyright 2022 Sony Corporation
 * Copyright (c) 2021-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <crypto/algapi.h>
#include <linux/crypto.h>
#include <crypto/internal/skcipher.h>
#include <crypto/skcipher.h>
#include <crypto/aes.h>
#include <crypto/ctr.h>

#include "crypto_ram_algs.h"
#include "crypto_ram_skcipher.h"

struct crypto_ram_sk_dev {
	struct crypto_ram_device *core;
	struct skcipher_alg *alg;
	int algnum;

	struct list_head list;
	bool is_init;
};

struct crypto_ram_skcipher_ctx {
	struct crypto_ram_device *core;
	u8 alg;
	u8 id;

	bool needs_deckey;
	bool is_ctr;
};

static int crypto_ram_skcipher_setkey(struct crypto_skcipher *skcipher,
				      const u8 *key, unsigned int keylen);
static int crypto_ram_skcipher_encrypt(struct skcipher_request *req);
static int crypto_ram_skcipher_decrypt(struct skcipher_request *req);
static int crypto_ram_skcipher_init(struct crypto_skcipher *tfm);
static int crypto_ram_skcipher_init_ctr(struct crypto_skcipher *tfm);
static void crypto_ram_skcipher_exit(struct crypto_skcipher *tfm);

static struct skcipher_alg crypto_ram_skcipher_algs_base[] = {
	{
		.setkey = crypto_ram_skcipher_setkey,
		.encrypt = crypto_ram_skcipher_encrypt,
		.decrypt = crypto_ram_skcipher_decrypt,
		.init = crypto_ram_skcipher_init,
		.exit = crypto_ram_skcipher_exit,
		.min_keysize = AES_KEYSIZE_128,
		.max_keysize = AES_KEYSIZE_256,
		.ivsize = 0,
		.chunksize = AES_BLOCK_SIZE,
		.walksize = AES_BLOCK_SIZE,
		.base = {
			.cra_name = "ecb(aes)",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SKCIPHER | CRYPTO_ALG_ASYNC,
			.cra_blocksize = AES_BLOCK_SIZE,
			.cra_ctxsize = sizeof(struct crypto_ram_skcipher_ctx),
			.cra_module = THIS_MODULE,
		},
	},
	{
		.setkey = crypto_ram_skcipher_setkey,
		.encrypt = crypto_ram_skcipher_encrypt,
		.decrypt = crypto_ram_skcipher_decrypt,
		.init = crypto_ram_skcipher_init,
		.exit = crypto_ram_skcipher_exit,
		.min_keysize = AES_KEYSIZE_128,
		.max_keysize = AES_KEYSIZE_256,
		.ivsize = AES_BLOCK_SIZE,
		.chunksize = AES_BLOCK_SIZE,
		.walksize = AES_BLOCK_SIZE,
		.base = {
			.cra_name = "cbc(aes)",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SKCIPHER | CRYPTO_ALG_ASYNC,
			.cra_blocksize = AES_BLOCK_SIZE,
			.cra_ctxsize = sizeof(struct crypto_ram_skcipher_ctx),
			.cra_module = THIS_MODULE,
		},
	},
	{
		.setkey = crypto_ram_skcipher_setkey,
		.encrypt = crypto_ram_skcipher_encrypt,
		.decrypt = crypto_ram_skcipher_decrypt,
		.init = crypto_ram_skcipher_init_ctr,
		.exit = crypto_ram_skcipher_exit,
		.min_keysize = AES_KEYSIZE_128,
		.max_keysize = AES_KEYSIZE_256,
		.ivsize = AES_BLOCK_SIZE,
		.chunksize = AES_BLOCK_SIZE,
		.walksize = AES_BLOCK_SIZE,
		.base = {
			.cra_name = "ctr(aes)",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SKCIPHER | CRYPTO_ALG_ASYNC,
			.cra_blocksize = 1,
			.cra_ctxsize = sizeof(struct crypto_ram_skcipher_ctx),
			.cra_module = THIS_MODULE,
		},
	},
};

static int crypto_ram_sk_generate_algs(struct crypto_ram_sk_dev *dev)
{
	int i;
	int ret = 0;

	memcpy(dev->alg, crypto_ram_skcipher_algs_base,
	       sizeof(crypto_ram_skcipher_algs_base));

	for (i = 0; i < dev->algnum; i++) {
		ret = crypto_ram_core_set_driver_name(dev->core,
						      &dev->alg[i].base);
		if (ret != 0) {
			break;
		}
	}

	return ret;
}

static struct crypto_ram_sk_dev *
crypto_ram_sk_create(struct crypto_ram_device *core)
{
	struct crypto_ram_sk_dev *dev;
	struct skcipher_alg *alg;
	int algnum;
	int ret;

	dev = devm_kzalloc(core->dev, sizeof(struct crypto_ram_sk_dev),
			   GFP_KERNEL);
	if (IS_ERR(dev))
		return dev;

	algnum = ARRAY_SIZE(crypto_ram_skcipher_algs_base);

	alg = devm_kzalloc(core->dev, algnum * sizeof(struct skcipher_alg),
			   GFP_KERNEL);
	if (IS_ERR(alg)) {
		return ERR_PTR(-ENOMEM);
	}

	dev->core = core;
	dev->algnum = algnum;
	dev->alg = alg;

	ret = crypto_ram_sk_generate_algs(dev);
	if (ret != 0) {
		return ERR_PTR(ret);
	}

	return dev;
}

static void crypto_ram_sk_destroy(struct crypto_ram_sk_dev *dev)
{
	/* Nothing to be done for now */
}

static bool crypto_ram_sk_has_alg(struct crypto_ram_sk_dev *dev,
				  const char *driver_name)
{
	int i;

	for (i = 0; i < dev->algnum; i++) {
		if (strcmp(dev->alg[i].base.cra_driver_name, driver_name) ==
		    0) {
			return true;
		}
	}

	return false;
}

static struct crypto_ram_sk_dev crypto_ram_sk;

static int crypto_ram_skcipher_find_device(struct crypto_ram_device **core,
					   const char *driver_name)
{
	struct crypto_ram_sk_dev *dev;

	list_for_each_entry (dev, &crypto_ram_sk.list, list) {
		if (crypto_ram_sk_has_alg(dev, driver_name))
			*core = dev->core;
		return 0;
	}

	NETSEC_MSG_ERR("Device not found for: %s", driver_name);
	return -EINVAL;
}

int crypto_ram_register_skciphers(struct crypto_ram_device *core)
{
	struct crypto_ram_sk_dev *dev;
	int err = 0;

	if (core->said_num == 0)
		return 0;

	dev = crypto_ram_sk_create(core);
	if (IS_ERR(dev)) {
		err = PTR_ERR(dev);
		goto exit;
	}

	INIT_LIST_HEAD(&dev->list);

	if (!crypto_ram_sk.is_init) {
		INIT_LIST_HEAD(&crypto_ram_sk.list);
		crypto_ram_sk.is_init = true;
	}

	list_add_tail(&dev->list, &crypto_ram_sk.list);

	err = crypto_register_skciphers(dev->alg, dev->algnum);
	if (err)
		goto exit;

	dev_info(dev->core->dev, "Registered skcipher\n");
	return 0;

exit:
	dev_err(core->dev, "Failed to register skcipher: %d\n", err);
	return err;
}

void crypto_ram_unregister_skciphers(struct crypto_ram_device *core)
{
	struct crypto_ram_sk_dev *dev = NULL;

	if (core->said_num == 0)
		return;

	list_for_each_entry (dev, &crypto_ram_sk.list, list) {
		if (dev->core == core)
			break;
	}

	if (!dev) {
		dev_err(core->dev, "skcipher device not found for %s\n",
			core->name);
		return;
	}

	crypto_unregister_skciphers(dev->alg, dev->algnum);
	list_del(&dev->list);
	crypto_ram_sk_destroy(dev);
}

static inline void crypto_ram_ctr_manual_inc(u8 *ctr, unsigned int block_size,
					     unsigned int num)
{
	int i;

	for (i = 0; i < DIV_ROUND_UP(num, block_size); i++) {
		crypto_inc(ctr, block_size);
	}
}

struct crypto_async_request *
crypto_ram_skcipher_complete(struct crypto_ram_calcinfo *info)
{
	int i;
	struct crypto_skcipher *skcipher =
		crypto_skcipher_reqtfm(info->req_skcipher);
	struct crypto_ram_skcipher_ctx *ctx = crypto_skcipher_ctx(skcipher);
	u32 cryptlen = info->req_skcipher->cryptlen;

	for (i = 0; i < info->tx_num; i++) {
		crypto_ram_unset_tx_frag_info(ctx->core->dev, &info->tx[i]);
	}

	if (info->data.nbytes > 0) {
		if (ctx->is_ctr && (cryptlen % crypto_skcipher_chunksize(skcipher) != 0))
				crypto_ram_ctr_manual_inc(
				    info->data.buf,
				    crypto_skcipher_chunksize(skcipher), cryptlen);

		memcpy(info->req_skcipher->iv, info->data.buf,
		       info->data.nbytes);
	}

	kfree(info->tx);
	return &info->req_skcipher->base;
}

/** crypto_ram_skcipher_do_raw() - starts skcipher operation in RAW mode */
static int crypto_ram_skcipher_do_raw(struct skcipher_request *req,
				      const bool is_enc, const u8 tx_ring_no,
				      const u8 rx_ring_no)
{
	struct crypto_skcipher *skcipher = crypto_skcipher_reqtfm(req);
	struct crypto_ram_skcipher_ctx *ctx = crypto_skcipher_ctx(skcipher);
	netsec_handle_t *handle = ctx->core->handle;
	u32 src_nents = sg_nents(req->src);
	u32 dst_nents = sg_nents(req->dst);
	u32 src_nents_tot, dst_nents_tot;
	u32 cryptlen = req->cryptlen;
	u32 tx_num = 0, rx_num = 0;
	netsec_enc_tx_pkt_ctrl_t cfg = { 0 };
	netsec_frag_info_t *tx = NULL, *rx = NULL;
	struct crypto_ram_calcinfo *info = NULL;
	struct scatterlist *src, *dst;
	u32 sum_in;
	long nbytes;
	int err = 0, i, netsec_err;

	/* +1 to store IV */
	src_nents_tot = src_nents + 1;
	dst_nents_tot = dst_nents + 1;

	if (cryptlen % crypto_skcipher_blocksize(skcipher) != 0) {
		return -EINVAL;
	}

	/* Immediately exit to avoid zero input */
	if (cryptlen == 0) {
		req->base.complete(&req->base, 0);
		return 0;
	}

	if (src_nents_tot > CRYPTO_RAM_SCAT_NUM_MAX ||
	    dst_nents_tot > CRYPTO_RAM_SCAT_NUM_MAX) {
		NETSEC_MSG_ERR("Too many scatterlists");
		return -ENOMEM;
	}

	tx = kzalloc(sizeof(netsec_frag_info_t) * src_nents_tot, GFP_KERNEL);
	rx = kzalloc(sizeof(netsec_frag_info_t) * dst_nents_tot, GFP_KERNEL);
	info = crypto_ram_calcinfo_create(req, CRYPTO_RAM_ALG_TYPE_SKCIPHER,
					  crypto_skcipher_ivsize(skcipher));

	if (!tx || !rx || !info) {
		NETSEC_MSG_ERR("Memory allocation failure");
		err = -ENOMEM;
		goto exit_mem;
	}

	if (crypto_skcipher_ivsize(skcipher) > 0) {
		/* Copy IV to DMA-able area */
		memcpy(info->data.buf, req->iv,
		       crypto_skcipher_ivsize(skcipher));
		err = crypto_ram_set_tx_frag_info(
			ctx->core->dev, &tx[tx_num++], info->data.buf,
			crypto_skcipher_ivsize(skcipher));
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma;
		}
	}

	sum_in = 0;

	for_each_sg (req->src, src, src_nents, i) {
		sum_in += src->length;

		if (sum_in > cryptlen) {
			err = crypto_ram_set_tx_frag_info(
				ctx->core->dev, &tx[tx_num++], sg_virt(src),
				src->length - (sum_in - cryptlen));
			if (unlikely(err != 0)) {
				NETSEC_MSG_ERR("DMA mapping failure");
				tx_num--;
				goto exit_dma;
			}
			break;

		} else if (sum_in == cryptlen) {
			err = crypto_ram_set_tx_frag_info(ctx->core->dev,
							  &tx[tx_num++],
							  sg_virt(src),
							  src->length);
			if (unlikely(err != 0)) {
				NETSEC_MSG_ERR("DMA mapping failure");
				tx_num--;
				goto exit_dma;
			}
			break;

		} else {
			err = crypto_ram_set_tx_frag_info(ctx->core->dev,
							  &tx[tx_num++],
							  sg_virt(src),
							  src->length);
			if (unlikely(err != 0)) {
				NETSEC_MSG_ERR("DMA mapping failure");
				tx_num--;
				goto exit_dma;
			}
		}
	}
	crypto_ram_set_tx_info(info, tx_num, tx);

	nbytes = cryptlen;

	for_each_sg (req->dst, dst, dst_nents, i) {
		/*
		 * Size of an sg element can be too large,
		 * so we need min() here
		 */
		err = crypto_ram_set_rx_frag_info(
			ctx->core->dev, &rx[rx_num++], sg_virt(dst),
			min((u32)nbytes, dst->length));
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			rx_num--;
			goto exit_dma;
		}

		nbytes -= min((u32)nbytes, dst->length);

		if (nbytes <= 0)
			break;
	}

	if ((crypto_skcipher_ivsize(skcipher) > 0) &&
	    (cryptlen % crypto_skcipher_chunksize(skcipher) == 0)) {
		err = crypto_ram_set_rx_frag_info(
			ctx->core->dev, &rx[rx_num++], info->data.buf,
			crypto_skcipher_ivsize(skcipher));
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			rx_num--;
			goto exit_dma;
		}
		cfg.iv_scatter_flag = true;
	} else {
		cfg.iv_scatter_flag = false;
	}

	netsec_enc_clean_tx_desc_ring(handle, tx_ring_no);

	cfg.enc_flag = is_enc;
	cfg.direct_iv_flag = NETSEC_FALSE;
	cfg.said = ctx->id;
	netsec_err = netsec_enc_set_tx_pkt_data(handle, tx_ring_no, &cfg,
						tx_num, tx, info, rx_num, rx);

	if (unlikely(netsec_err == NETSEC_ERR_BUSY)) {
		NETSEC_MSG_ERR("Device too busy - possible system overload");
		err = -EBUSY;
		goto exit_dma;

	} else if (unlikely(netsec_err != NETSEC_ERR_OK)) {
		NETSEC_MSG_ERR("Failed to set Tx packet data: %d", netsec_err);
		err = -ENODEV;
		goto exit_dma;
	}

	kfree(rx);

	return -EINPROGRESS;

exit_dma:
	for (i = 0; i < tx_num; i++) {
		crypto_ram_unset_tx_frag_info(ctx->core->dev, &tx[i]);
	}

	for (i = 0; i < rx_num; i++) {
		crypto_ram_unset_rx_frag_info(ctx->core->dev, &rx[i]);
	}

exit_mem:
	crypto_ram_calcinfo_destroy(info);
	kfree(rx);
	kfree(tx);

	return err;
}

struct skcipher_sadata {
	const char *name;
	const struct crypto_ram_key_alg_pair *enc_pair;
	const u8 enclen;
	const bool needs_deckey;
};

#define SKCIPHER_SADATA_ITEM(name, enc_pair, needs_deckey)         \
	{                                                          \
		name, enc_pair, ARRAY_SIZE(enc_pair), needs_deckey \
	}

static const struct skcipher_sadata sa_table[] = {
	SKCIPHER_SADATA_ITEM("ecb(aes)", encpair_aes_ecb, true),
	SKCIPHER_SADATA_ITEM("cbc(aes)", encpair_aes_cbc, true),
	SKCIPHER_SADATA_ITEM("ctr(aes)", encpair_aes_ctr, false),
};

static int crypto_ram_skcipher_set_alg(struct crypto_ram_skcipher_ctx *ctx,
				       char *cra_name, u32 key_bit)
{
	int i;
	u8 alg;

	for (i = 0; i < ARRAY_SIZE(sa_table); i++) {
		if (strcmp(cra_name, sa_table[i].name) == 0) {
			if (crypto_ram_get_pair_alg(sa_table[i].enc_pair,
						    sa_table[i].enclen, key_bit,
						    &alg)) {
				NETSEC_MSG_INFO(
					"Failed to set alg for %s: keybit = %d",
					cra_name, key_bit);
				return -EINVAL;
			}

			ctx->alg = alg;
			ctx->needs_deckey = sa_table[i].needs_deckey;

			return 0;
		}
	}

	NETSEC_MSG_ERR("alg not found: %s", cra_name);
	return -EINVAL;
}

static int
crypto_ram_skcipher_configure_entry(struct crypto_ram_skcipher_ctx *ctx,
				    const u8 *key, u32 keylen)
{
	int err = 0;
	netsec_sa_data_t sa = { 0 };

	sa.bulk_mode = NETSEC_BULK_MODE_RAW;
	sa.encrypt_alg = ctx->alg;
	sa.aes_ctr_len_128_ext_flag = true;
	memcpy(sa.encrypt_key, key, keylen);

	if (ctx->needs_deckey) {
		memcpy(sa.auth_key, key, keylen);
		netsec_aes_gen_dec_key(ctx->core->handle, sa.auth_key,
				       keylen * 8);
	}
	err = crypto_ram_core_configure_entry(ctx->core, ctx->id, &sa);

	memzero_explicit(&sa, sizeof(sa));
	return err;
}

/** crypto_ram_skcipher_setkey() - configures SADB
 *
 * Since the key length is dependent on the algorithm,
 * both the key length and the algorithm are configured
 * at the same time in this function
 */
static int crypto_ram_skcipher_setkey(struct crypto_skcipher *skcipher,
				      const u8 *key, unsigned int keylen)
{
	struct crypto_tfm *tfm = crypto_skcipher_tfm(skcipher);
	struct crypto_ram_skcipher_ctx *ctx = crypto_tfm_ctx(tfm);
	struct crypto_alg *alg = tfm->__crt_alg;
	int err;

	if (keylen > NETSEC_ENCRYPT_KEY_LEN_MAX) {
		return -EINVAL;
	}

	err = crypto_ram_skcipher_set_alg(ctx, alg->cra_name, keylen * 8);
	if (err)
		return err;

	err = crypto_ram_skcipher_configure_entry(ctx, key, keylen);
	if (err)
		return err;

	return 0;
}

static int crypto_ram_skcipher_encrypt(struct skcipher_request *req)
{
	return crypto_ram_skcipher_do_raw(req, true,
					  NETSEC_DESC_RING_NO_ENC_RAW_TX,
					  NETSEC_DESC_RING_NO_ENC_RAW_RX);
}

static int crypto_ram_skcipher_decrypt(struct skcipher_request *req)
{
	return crypto_ram_skcipher_do_raw(req, false,
					  NETSEC_DESC_RING_NO_DEC_RAW_TX,
					  NETSEC_DESC_RING_NO_DEC_RAW_RX);
}

/**
 * crypto_ram_skcipher_init() - initializes the context specifier
 */
static int crypto_ram_skcipher_init(struct crypto_skcipher *tfm)
{
	int err = 0;
	struct crypto_ram_skcipher_ctx *ctx = crypto_skcipher_ctx(tfm);

	memset(ctx, 0x00, sizeof(*ctx));

	err = crypto_ram_skcipher_find_device(
		&ctx->core, tfm->base.__crt_alg->cra_driver_name);
	if (err)
		return err;

	err = crypto_ram_core_acquire_entry(ctx->core, &ctx->id);

	ctx->is_ctr = false;

	return err;
}

static int crypto_ram_skcipher_init_ctr(struct crypto_skcipher *tfm)
{
	int err = crypto_ram_skcipher_init(tfm);
	struct crypto_ram_skcipher_ctx *ctx = crypto_skcipher_ctx(tfm);

	ctx->is_ctr = true;
	return err;
}

static void crypto_ram_skcipher_exit(struct crypto_skcipher *tfm)
{
	struct crypto_ram_skcipher_ctx *ctx = crypto_skcipher_ctx(tfm);

	crypto_ram_core_release_entry(ctx->core, &ctx->id);
}
