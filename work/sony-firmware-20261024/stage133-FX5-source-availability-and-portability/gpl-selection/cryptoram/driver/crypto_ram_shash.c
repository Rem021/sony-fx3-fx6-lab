/**
 * Copyright 2022 Sony Corporation
 * Copyright (c) 2021-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <crypto/hash.h>
#include <crypto/md5.h>
#include <crypto/sha2.h>
#include <crypto/sha3.h>
#include <linux/crypto.h>

#include "crypto_ram_algs.h"
#include "crypto_ram_shash.h"

#define CRYPTO_RAM_SHA3_INTERMEDIATE_LEN 200

struct crypto_ram_shash_req {
	struct shash_desc *desc;
	const u8 *data;
	unsigned int len;
	u8 *out;
};

struct crypto_ram_shash_dev {
	struct crypto_ram_device *core;
	struct shash_alg *alg;
	int algnum;

	struct list_head list;
	bool is_init;
};

struct crypto_ram_shash_state {
	u32 count;
	u8 buf[CRYPTO_RAM_SHA3_INTERMEDIATE_LEN];
};

/**
 * crypto_ram_shash_partial - stores plaintext data temporarily for suspend/resume
 * @cnt: number of bytes stored
 * @ch: currently active chan[nel
 * @buf: stored data. Channel will be switched when a single routine has to
 *	   store two different data
 */
struct crypto_ram_shash_partial {
	u32 cnt;
	u8 ch;
	u8 buf[2][SHA3_256_BLOCK_SIZE];
};

struct crypto_ram_shash_ctx {
	struct crypto_ram_device *core;
	u8 auth_alg;
	u8 id;

	struct crypto_ram_shash_state state;
	struct crypto_ram_shash_partial partial;
	u32 intermediate_size;
};

static int crypto_ram_shash_cra_init(struct crypto_tfm *tfm);
static int crypto_ram_shash_cra_init_sha384(struct crypto_tfm *tfm);
static int crypto_ram_shash_cra_init_sha3(struct crypto_tfm *tfm);

static void crypto_ram_shash_cra_exit(struct crypto_tfm *tfm);
static int crypto_ram_shash_init(struct shash_desc *desc);
static int crypto_ram_shash_update(struct shash_desc *desc, const u8 *data,
				   unsigned int len);
static int crypto_ram_shash_final(struct shash_desc *desc, u8 *out);
static int crypto_ram_shash_digest(struct shash_desc *desc, const u8 *data,
				   unsigned int len, u8 *out);
static int crypto_ram_shash_export(struct shash_desc *desc, void *out);
static int crypto_ram_shash_import(struct shash_desc *desc, const void *in);

struct shash_alg crypto_ram_shash_algs_base[] = {
	{
		.init = crypto_ram_shash_init,
		.update = crypto_ram_shash_update,
		.final = crypto_ram_shash_final,
		.digest = crypto_ram_shash_digest,
		.export = crypto_ram_shash_export,
		.import = crypto_ram_shash_import,
		.digestsize = MD5_DIGEST_SIZE,
		.descsize = sizeof(struct crypto_ram_shash_state),
		.statesize = sizeof(struct crypto_ram_shash_state),
		.base = {
			.cra_name = "md5",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SHASH,
			.cra_blocksize = MD5_BLOCK_WORDS * MD5_HASH_WORDS,
			.cra_ctxsize = sizeof(struct crypto_ram_shash_ctx),
			.cra_module = THIS_MODULE,
			.cra_init = crypto_ram_shash_cra_init,
			.cra_exit = crypto_ram_shash_cra_exit,
		},
	},
	{
		.init = crypto_ram_shash_init,
		.update = crypto_ram_shash_update,
		.final = crypto_ram_shash_final,
		.digest = crypto_ram_shash_digest,
		.export = crypto_ram_shash_export,
		.import = crypto_ram_shash_import,
		.digestsize = SHA256_DIGEST_SIZE,
		.descsize = sizeof(struct crypto_ram_shash_state),
		.statesize = sizeof(struct crypto_ram_shash_state),
		.base = {
			.cra_name = "sha256",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SHASH,
			.cra_blocksize = SHA256_BLOCK_SIZE,
			.cra_ctxsize = sizeof(struct crypto_ram_shash_ctx),
			.cra_module = THIS_MODULE,
			.cra_init = crypto_ram_shash_cra_init,
			.cra_exit = crypto_ram_shash_cra_exit,
		},
	},
	{
		.init = crypto_ram_shash_init,
		.update = crypto_ram_shash_update,
		.final = crypto_ram_shash_final,
		.digest = crypto_ram_shash_digest,
		.export = crypto_ram_shash_export,
		.import = crypto_ram_shash_import,
		.digestsize = SHA384_DIGEST_SIZE,
		.descsize = sizeof(struct crypto_ram_shash_state),
		.statesize = sizeof(struct crypto_ram_shash_state),
		.base = {
			.cra_name = "sha384",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SHASH,
			.cra_blocksize = SHA384_BLOCK_SIZE,
			.cra_ctxsize = sizeof(struct crypto_ram_shash_ctx),
			.cra_module = THIS_MODULE,
			.cra_init = crypto_ram_shash_cra_init_sha384,
			.cra_exit = crypto_ram_shash_cra_exit,
		},
	},
	{
		.init = crypto_ram_shash_init,
		.update = crypto_ram_shash_update,
		.final = crypto_ram_shash_final,
		.digest = crypto_ram_shash_digest,
		.export = crypto_ram_shash_export,
		.import = crypto_ram_shash_import,
		.digestsize = SHA512_DIGEST_SIZE,
		.descsize = sizeof(struct crypto_ram_shash_state),
		.statesize = sizeof(struct crypto_ram_shash_state),
		.base = {
			.cra_name = "sha512",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SHASH,
			.cra_blocksize = SHA512_BLOCK_SIZE,
			.cra_ctxsize = sizeof(struct crypto_ram_shash_ctx),
			.cra_module = THIS_MODULE,
			.cra_init = crypto_ram_shash_cra_init,
			.cra_exit = crypto_ram_shash_cra_exit,
		},
	},
	{
		.init = crypto_ram_shash_init,
		.update = crypto_ram_shash_update,
		.final = crypto_ram_shash_final,
		.digest = crypto_ram_shash_digest,
		.export = crypto_ram_shash_export,
		.import = crypto_ram_shash_import,
		.digestsize = SHA3_256_DIGEST_SIZE,
		.descsize = sizeof(struct crypto_ram_shash_state),
		.statesize = sizeof(struct crypto_ram_shash_state),
		.base = {
			.cra_name = "sha3-256",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SHASH,
			.cra_blocksize = SHA3_256_BLOCK_SIZE,
			.cra_ctxsize = sizeof(struct crypto_ram_shash_ctx),
			.cra_module = THIS_MODULE,
			.cra_init = crypto_ram_shash_cra_init_sha3,
			.cra_exit = crypto_ram_shash_cra_exit,
		},
	},
	{
		.init = crypto_ram_shash_init,
		.update = crypto_ram_shash_update,
		.final = crypto_ram_shash_final,
		.digest = crypto_ram_shash_digest,
		.export = crypto_ram_shash_export,
		.import = crypto_ram_shash_import,
		.digestsize = SHA3_384_DIGEST_SIZE,
		.descsize = sizeof(struct crypto_ram_shash_state),
		.statesize = sizeof(struct crypto_ram_shash_state),
		.base = {
			.cra_name = "sha3-384",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SHASH,
			.cra_blocksize = SHA3_384_BLOCK_SIZE,
			.cra_ctxsize = sizeof(struct crypto_ram_shash_ctx),
			.cra_module = THIS_MODULE,
			.cra_init = crypto_ram_shash_cra_init_sha3,
			.cra_exit = crypto_ram_shash_cra_exit,
		},
	},
	{
		.init = crypto_ram_shash_init,
		.update = crypto_ram_shash_update,
		.final = crypto_ram_shash_final,
		.digest = crypto_ram_shash_digest,
		.export = crypto_ram_shash_export,
		.import = crypto_ram_shash_import,
		.digestsize = SHA3_512_DIGEST_SIZE,
		.descsize = sizeof(struct crypto_ram_shash_state),
		.statesize = sizeof(struct crypto_ram_shash_state),
		.base = {
			.cra_name = "sha3-512",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_SHASH,
			.cra_blocksize = SHA3_512_BLOCK_SIZE,
			.cra_ctxsize = sizeof(struct crypto_ram_shash_ctx),
			.cra_module = THIS_MODULE,
			.cra_init = crypto_ram_shash_cra_init_sha3,
			.cra_exit = crypto_ram_shash_cra_exit,
		},
	},
};

static int crypto_ram_shash_generate_algs(struct crypto_ram_shash_dev *dev)
{
	int i;
	int ret = 0;

	memcpy(dev->alg, crypto_ram_shash_algs_base,
	       sizeof(crypto_ram_shash_algs_base));

	for (i = 0; i < dev->algnum; i++) {
		ret = crypto_ram_core_set_driver_name(dev->core,
						      &dev->alg[i].base);
		if (ret != 0) {
			break;
		}
	}

	return ret;
}

static struct crypto_ram_shash_dev *
crypto_ram_shash_create(struct crypto_ram_device *core)
{
	struct crypto_ram_shash_dev *dev;
	struct shash_alg *alg;
	int algnum;
	int ret;

	dev = devm_kzalloc(core->dev, sizeof(struct crypto_ram_shash_dev),
			   GFP_KERNEL);
	if (IS_ERR(dev))
		return dev;

	algnum = ARRAY_SIZE(crypto_ram_shash_algs_base);

	alg = devm_kzalloc(core->dev, algnum * sizeof(struct shash_alg),
			   GFP_KERNEL);
	if (IS_ERR(alg)) {
		return ERR_PTR(-ENOMEM);
	}

	dev->core = core;
	dev->algnum = algnum;
	dev->alg = alg;

	ret = crypto_ram_shash_generate_algs(dev);
	if (ret != 0) {
		return ERR_PTR(ret);
	}

	return dev;
}

static void crypto_ram_shash_destroy(struct crypto_ram_shash_dev *dev)
{
	/* Nothing to be done for now */
}

static bool crypto_ram_shash_has_alg(struct crypto_ram_shash_dev *dev,
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

static struct crypto_ram_shash_dev crypto_ram_shash;

static int crypto_ram_shash_find_device(struct crypto_ram_device **core,
					const char *driver_name)
{
	struct crypto_ram_shash_dev *dev;

	list_for_each_entry (dev, &crypto_ram_shash.list, list) {
		if (crypto_ram_shash_has_alg(dev, driver_name))
			*core = dev->core;
		return 0;
	}

	NETSEC_MSG_ERR("Device not found for: %s", driver_name);
	return -EINVAL;
}

int crypto_ram_register_shashes(struct crypto_ram_device *core)
{
	struct crypto_ram_shash_dev *dev;
	int err = 0;

	if (core->said_num == 0)
		return 0;

	dev = crypto_ram_shash_create(core);
	if (IS_ERR(dev)) {
		err = PTR_ERR(dev);
		goto exit;
	}

	INIT_LIST_HEAD(&dev->list);

	if (!crypto_ram_shash.is_init) {
		INIT_LIST_HEAD(&crypto_ram_shash.list);
		crypto_ram_shash.is_init = true;
	}

	list_add_tail(&dev->list, &crypto_ram_shash.list);

	err = crypto_register_shashes(dev->alg, dev->algnum);
	if (err)
		goto exit;

	dev_info(core->dev, "Registered shash\n");
	return 0;

exit:
	dev_err(core->dev, "Failed to register shash: %d\n", err);
	return err;
}

void crypto_ram_unregister_shashes(struct crypto_ram_device *core)
{
	struct crypto_ram_shash_dev *dev = NULL;

	if (core->said_num == 0)
		return;

	list_for_each_entry (dev, &crypto_ram_shash.list, list) {
		if (dev->core == core)
			break;
	}

	if (!dev) {
		dev_err(core->dev, "Device not found for %s\n", core->name);
		return;
	}

	crypto_unregister_shashes(dev->alg, dev->algnum);
	list_del(&dev->list);
	crypto_ram_shash_destroy(dev);
}

int crypto_ram_shash_complete(struct crypto_ram_calcinfo *info)
{
	complete(&info->wait.completion);

	return 0;
}

struct shash_sadata {
	const char *name;
	u8 alg;
};

static const struct shash_sadata auth_table[] = {
	{ "md5", NETSEC_AUTH_ALG_MD5 },
	{ "sha256", NETSEC_AUTH_ALG_SHA256 },
	{ "sha384", NETSEC_AUTH_ALG_SHA384 },
	{ "sha512", NETSEC_AUTH_ALG_SHA512 },
	{ "sha3-256", NETSEC_AUTH_ALG_SHA3_256 },
	{ "sha3-384", NETSEC_AUTH_ALG_SHA3_384 },
	{ "sha3-512", NETSEC_AUTH_ALG_SHA3_512 },
};

static int crypto_ram_shash_set_alg(struct crypto_ram_shash_ctx *ctx,
				    char *cra_name)
{
	int i;

	for (i = 0; i < ARRAY_SIZE(auth_table); i++) {
		if (strcmp(cra_name, auth_table[i].name) == 0) {
			ctx->auth_alg = auth_table[i].alg;
			return 0;
		}
	}

	NETSEC_MSG_ERR("alg not found: %s", cra_name);
	return -EINVAL;
}

static int crypto_ram_shash_configure_entry(struct crypto_ram_shash_ctx *ctx)
{
	int err = 0;
	netsec_sa_data_t sa = { 0 };

	sa.auth_alg = ctx->auth_alg;
	sa.process_type = NETSEC_RAW_PROCESS_AUTH;
	sa.bulk_mode = NETSEC_BULK_MODE_RAW;

	err = crypto_ram_core_configure_entry(ctx->core, ctx->id, &sa);

	memzero_explicit(&sa, sizeof(sa));
	return err;
}

static int crypto_ram_shash_cra_init(struct crypto_tfm *tfm)
{
	struct crypto_ram_shash_ctx *ctx = crypto_tfm_ctx(tfm);
	struct crypto_alg *alg = tfm->__crt_alg;
	int err;
	struct crypto_shash *shash = __crypto_shash_cast(tfm);

	memset(ctx, 0, sizeof(*ctx));

	err = crypto_ram_shash_find_device(&ctx->core,
					   tfm->__crt_alg->cra_driver_name);
	if (err)
		return err;

	err = crypto_ram_core_acquire_entry(ctx->core, &ctx->id);
	if (err)
		return err;

	err = crypto_ram_shash_set_alg(ctx, alg->cra_name);
	if (err)
		return err;

	err = crypto_ram_shash_configure_entry(ctx);
	if (err)
		return err;

	ctx->intermediate_size = crypto_shash_digestsize(shash);

	return 0;
}

static int crypto_ram_shash_cra_init_sha384(struct crypto_tfm *tfm)
{
	int ret = crypto_ram_shash_cra_init(tfm);
	struct crypto_ram_shash_ctx *ctx = crypto_tfm_ctx(tfm);

	ctx->intermediate_size = SHA512_DIGEST_SIZE;

	return ret;
}

static int crypto_ram_shash_cra_init_sha3(struct crypto_tfm *tfm)
{
	int ret = crypto_ram_shash_cra_init(tfm);
	struct crypto_ram_shash_ctx *ctx = crypto_tfm_ctx(tfm);

	ctx->intermediate_size = CRYPTO_RAM_SHA3_INTERMEDIATE_LEN;

	return ret;
}

static void crypto_ram_shash_cra_exit(struct crypto_tfm *tfm)
{
	struct crypto_ram_shash_ctx *ctx = crypto_tfm_ctx(tfm);

	crypto_ram_core_release_entry(ctx->core, &ctx->id);
}

/** Start shash chipher operation in RAW mode */
static int crypto_ram_shash_do_raw(struct crypto_ram_shash_req *req,
				   const u8 tx_ring_no, const u8 rx_ring_no)
{
	struct crypto_shash *shash = req->desc->tfm;
	struct crypto_ram_shash_ctx *ctx =
		crypto_tfm_ctx(crypto_shash_tfm(shash));
	netsec_handle_t *handle = ctx->core->handle;
	u32 tx_num = 0, rx_num = 0;
	netsec_enc_tx_pkt_ctrl_t cfg = { 0 };
	netsec_frag_info_t tx[1]; /* data:1 */
	netsec_frag_info_t rx[1];
	struct crypto_ram_calcinfo *info = NULL;
	int err = 0;
	int netsec_err;
	int i;

	info = crypto_ram_calcinfo_create(req, CRYPTO_RAM_ALG_TYPE_SHASH,
					  crypto_shash_digestsize(shash));

	if (!info) {
		NETSEC_MSG_ERR("Memory allocation failure");
		return -ENOMEM;
	}
	crypto_init_wait(&info->wait);

	err = crypto_ram_set_tx_frag_info(ctx->core->dev, &tx[tx_num++],
					  (u8 *)req->data, req->len);
	if (unlikely(err != 0)) {
		NETSEC_MSG_ERR("DMA mapping failure");
		tx_num--;
		goto exit_dma_tx;
	}

	err = crypto_ram_set_rx_frag_info(ctx->core->dev, &rx[rx_num++],
					  info->data.buf,
					  crypto_shash_digestsize(shash));
	if (unlikely(err != 0)) {
		NETSEC_MSG_ERR("DMA mapping failure");
		rx_num--;
		goto exit_dma;
	}

	netsec_enc_clean_tx_desc_ring(handle, tx_ring_no);

	cfg.said = ctx->id;
	cfg.direct_iv_flag = false;
	cfg.enc_flag = true;
	cfg.valid_null_flag = true;
	cfg.hash_suspend_flag = false;
	cfg.hash_resume_flag = false;

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

	} else {
		/* shash_async not available */
		wait_for_completion(&info->wait.completion);
		memcpy(req->out, rx[0].addr, rx[0].len);
		err = 0;
		goto exit_dma_tx; /* unset_rx has been run in tasklet */
	}

exit_dma:
	for (i = 0; i < rx_num; i++) {
		crypto_ram_unset_rx_frag_info(ctx->core->dev, &rx[i]);
	}
exit_dma_tx:
	for (i = 0; i < tx_num; i++) {
		crypto_ram_unset_tx_frag_info(ctx->core->dev, &tx[i]);
	}
	crypto_ram_calcinfo_destroy(info);

	return err;
}

static int crypto_ram_shash_digest(struct shash_desc *desc, const u8 *data,
				   unsigned int len, u8 *out)
{
	struct crypto_ram_shash_req req = {
		.desc = desc,
		.data = data,
		.len = len,
		.out = out,
	};
	return crypto_ram_shash_do_raw(&req, NETSEC_DESC_RING_NO_ENC_RAW_TX,
				       NETSEC_DESC_RING_NO_ENC_RAW_RX);
}

static inline void
crypto_ram_shash_partial_clear(struct crypto_ram_shash_partial *partial)
{
	partial->ch = 0;
	partial->cnt = 0;
	memset(partial->buf, 0, sizeof(partial->buf));
}

/**
 * crypto_ram_shash_partial_write() - saves the given data to partial data structure
 * @partial: strucure to save data to
 * @buf: data to save
 * @cnt: number of bytes to save
 * @ch_changed: whether to swap the buffer to save to
 */
static void
crypto_ram_shash_partial_write(struct crypto_ram_shash_partial *partial,
			       u8 *buf, u32 cnt, bool ch_changed)
{
	if (ch_changed) {
		u8 prev_ch = partial->ch;
		partial->ch ^= 0x1;

		memcpy(partial->buf[partial->ch], partial->buf[prev_ch],
		       partial->cnt);
	}

	if (partial->cnt + cnt <= sizeof(partial->buf)) {
		memcpy(&partial->buf[partial->ch][partial->cnt], buf, cnt);
		partial->cnt += cnt;

	} else {
		NETSEC_MSG_ERR("cnt too large: %u", cnt);
	}
}

/**
 * crypto_ram_shash_partial_read() - decrements the byte position of the saved data
 *
 * @partial: structure which retains the saved data
 * @cnt: number of bytes to decrement
 *
 * Return: head address of current buffer in use
 */
static inline void *
crypto_ram_shash_partial_read(struct crypto_ram_shash_partial *partial, u32 cnt)
{
	partial->cnt -= cnt;
	return &partial->buf[partial->ch][0];
}

/**
 * crypto_ram_shash_intermediate() - starts shash chipher operation in RAW mode
 *								  for suspended data
 */
static int crypto_ram_shash_intermediate(struct crypto_ram_shash_req *req,
					 const u8 tx_ring_no,
					 const u8 rx_ring_no)
{
	struct crypto_shash *shash = req->desc->tfm;
	struct crypto_ram_shash_ctx *ctx =
		crypto_tfm_ctx(crypto_shash_tfm(shash));
	netsec_handle_t *handle = ctx->core->handle;
	netsec_enc_tx_pkt_ctrl_t cfg = { 0 };
	netsec_frag_info_t tx[4]; /* state:2, partial:1, data:1 */
	netsec_frag_info_t rx[1];
	struct crypto_ram_calcinfo *info = NULL;
	u32 tx_num = 0, rx_num = 0;
	long nbytes;
	int err = 0, residue;
	int netsec_err;
	uint32_t tmp_partial_len;
	u32 blocksize = crypto_shash_blocksize(shash);
	int i;

	if (req->len + ctx->partial.cnt < blocksize) {
		crypto_ram_shash_partial_write(&ctx->partial, (u8 *)req->data,
					       req->len, false);
		return 0;
	}

	info = crypto_ram_calcinfo_create(req, CRYPTO_RAM_ALG_TYPE_SHASH, 0);
	if (!info) {
		NETSEC_MSG_ERR("Memory allocation failure");
		return -ENOMEM;
	}
	crypto_init_wait(&info->wait);

	/* Transfer intermediate data if not the first update */
	if (ctx->state.count > 0) {
		cfg.hash_resume_flag = true;
		cfg.interim_len =
			sizeof(ctx->state.count) + ctx->intermediate_size;

		err = crypto_ram_set_tx_frag_info(ctx->core->dev, &tx[tx_num++],
						  &ctx->state.count,
						  sizeof(ctx->state.count));
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma_tx;
		}
		err = crypto_ram_set_tx_frag_info(ctx->core->dev, &tx[tx_num++],
						  ctx->state.buf,
						  ctx->intermediate_size);
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma_tx;
		}

	} else {
		cfg.hash_resume_flag = false;
		cfg.interim_len = 0;
	}

	/* Handle newly incoming data + stashed data (w/ alignment) */
	nbytes = req->len + ctx->partial.cnt;
	residue = nbytes % blocksize;
	nbytes -= residue;

	/* Transfer stashed data if any */
	if (ctx->partial.cnt > 0) {
		nbytes -= ctx->partial.cnt;
		tmp_partial_len = ctx->partial.cnt;
		err = crypto_ram_set_tx_frag_info(
			ctx->core->dev, &tx[tx_num++],
			crypto_ram_shash_partial_read(&ctx->partial,
						      tmp_partial_len),
			tmp_partial_len);
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma_tx;
		}
	}

	if ((nbytes != 0) || (tx_num == 0)) {
		err = crypto_ram_set_tx_frag_info(ctx->core->dev, &tx[tx_num++],
						  (u8 *)req->data, nbytes);
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma_tx;
		}
	}

	/* Stash remaining data */
	if (residue > 0) {
		crypto_ram_shash_partial_write(
			&ctx->partial, (u8 *)req->data + (req->len - residue),
			residue, true);
	}

	err = crypto_ram_set_rx_frag_info(
		ctx->core->dev, &rx[rx_num++], &ctx->state,
		sizeof(ctx->state.count) + ctx->intermediate_size);
	if (unlikely(err != 0)) {
		NETSEC_MSG_ERR("DMA mapping failure");
		rx_num--;
		goto exit_dma;
	}

	netsec_enc_clean_tx_desc_ring(handle, tx_ring_no);

	cfg.said = ctx->id;
	cfg.direct_iv_flag = false;
	cfg.enc_flag = true;
	cfg.valid_null_flag = true;
	cfg.hash_suspend_flag = true; /* make HW return intermediate results */

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

	} else {
		/* shash_async not available */
		wait_for_completion(&info->wait.completion);
		err = 0;
		goto exit_dma_tx; /* unset_rx has been run in tasklet */
	}

exit_dma:
	for (i = 0; i < rx_num; i++) {
		crypto_ram_unset_rx_frag_info(ctx->core->dev, &rx[i]);
	}
exit_dma_tx:
	for (i = 0; i < tx_num; i++) {
		crypto_ram_unset_tx_frag_info(ctx->core->dev, &tx[i]);
	}
	crypto_ram_calcinfo_destroy(info);

	return err;
}

static int crypto_ram_shash_last(struct crypto_ram_shash_req *req,
				 const u8 tx_ring_no, const u8 rx_ring_no)
{
	struct crypto_shash *shash = req->desc->tfm;
	struct crypto_ram_shash_ctx *ctx =
		crypto_tfm_ctx(crypto_shash_tfm(shash));
	netsec_handle_t *handle = ctx->core->handle;
	netsec_enc_tx_pkt_ctrl_t cfg = { 0 };
	netsec_frag_info_t tx[3]; /* state:2, partial:1 */
	netsec_frag_info_t rx[1];
	struct crypto_ram_calcinfo *info = NULL;
	u32 tx_num = 0, rx_num = 0;
	int err = 0;
	netsec_err_t netsec_err;
	uint32_t tmp_partial_len;
	int i;

	info = crypto_ram_calcinfo_create(req, CRYPTO_RAM_ALG_TYPE_SHASH,
					  crypto_shash_digestsize(shash));
	if (!info) {
		NETSEC_MSG_ERR("Memory allocation failure");
		return -ENOMEM;
	}
	crypto_init_wait(&info->wait);

	if (ctx->state.count > 0) {
		cfg.hash_resume_flag = true;
		cfg.interim_len =
			sizeof(ctx->state.count) + ctx->intermediate_size;

		err = crypto_ram_set_tx_frag_info(ctx->core->dev, &tx[tx_num++],
						  &ctx->state.count,
						  sizeof(ctx->state.count));
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma_tx;
		}
		err = crypto_ram_set_tx_frag_info(ctx->core->dev, &tx[tx_num++],
						  ctx->state.buf,
						  ctx->intermediate_size);
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma_tx;
		}

	} else {
		cfg.hash_resume_flag = false;
		cfg.interim_len = 0;
	}

	if (ctx->partial.cnt > 0) {
		tmp_partial_len = ctx->partial.cnt;
		err = crypto_ram_set_tx_frag_info(
			ctx->core->dev, &tx[tx_num++],
			crypto_ram_shash_partial_read(&ctx->partial,
						      tmp_partial_len),
			tmp_partial_len);
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma_tx;
		}
	}

	err = crypto_ram_set_rx_frag_info(ctx->core->dev, &rx[rx_num++],
					  info->data.buf,
					  crypto_shash_digestsize(shash));
	if (unlikely(err != 0)) {
		NETSEC_MSG_ERR("DMA mapping failure");
		rx_num--;
		goto exit_dma;
	}

	netsec_enc_clean_tx_desc_ring(handle, tx_ring_no);

	cfg.said = ctx->id;
	cfg.direct_iv_flag = false;
	cfg.enc_flag = true;
	cfg.valid_null_flag = true;
	cfg.hash_suspend_flag = false;

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

	} else {
		/* shash_async not available */
		wait_for_completion(&info->wait.completion);
		memcpy(req->out, rx[0].addr, rx[0].len);
		err = 0;
		goto exit_dma_tx; /* unset_rx has been run in tasklet */
	}

exit_dma:
	for (i = 0; i < rx_num; i++) {
		crypto_ram_unset_rx_frag_info(ctx->core->dev, &rx[i]);
	}
exit_dma_tx:
	for (i = 0; i < tx_num; i++) {
		crypto_ram_unset_tx_frag_info(ctx->core->dev, &tx[i]);
	}
	crypto_ram_calcinfo_destroy(info);

	return err;
}

static int crypto_ram_shash_init(struct shash_desc *desc)
{
	struct crypto_shash *shash = desc->tfm;
	struct crypto_ram_shash_ctx *ctx =
		crypto_tfm_ctx(crypto_shash_tfm(shash));
	struct crypto_ram_shash_state *state = shash_desc_ctx(desc);

	memset(state, 0x00, sizeof(struct crypto_ram_shash_state));
	crypto_ram_shash_partial_clear(&ctx->partial);
	return 0;
}

static int crypto_ram_shash_update(struct shash_desc *desc, const u8 *data,
				   unsigned int len)
{
	struct crypto_shash *shash = desc->tfm;
	struct crypto_ram_shash_ctx *ctx =
		crypto_tfm_ctx(crypto_shash_tfm(shash));
	struct crypto_ram_shash_req req = {
		.desc = desc,
		.data = data,
		.len = len,
		.out = NULL,
	};
	struct crypto_ram_shash_state *state = shash_desc_ctx(desc);
	int ret;

	memcpy(&ctx->state, state, sizeof(struct crypto_ram_shash_state));
	ret = crypto_ram_shash_intermediate(&req,
					    NETSEC_DESC_RING_NO_ENC_RAW_TX,
					    NETSEC_DESC_RING_NO_ENC_RAW_RX);
	memcpy(state, &ctx->state, sizeof(struct crypto_ram_shash_state));
	return ret;
}

static int crypto_ram_shash_final(struct shash_desc *desc, u8 *out)
{
	struct crypto_ram_shash_state *state = shash_desc_ctx(desc);
	struct crypto_shash *shash = desc->tfm;
	struct crypto_ram_shash_ctx *ctx =
		crypto_tfm_ctx(crypto_shash_tfm(shash));
	struct crypto_ram_shash_req req = {
		.desc = desc,
		.data = NULL,
		.len = 0,
		.out = out,
	};
	int ret;

	memcpy(&ctx->state, state, sizeof(struct crypto_ram_shash_state));
	if (ctx->state.count > 0 || ctx->partial.cnt > 0) {
		ret = crypto_ram_shash_last(&req,
					    NETSEC_DESC_RING_NO_ENC_RAW_TX,
					    NETSEC_DESC_RING_NO_ENC_RAW_RX);

	} else {
		ret = crypto_ram_shash_digest(desc, req.data, req.len, out);
	}

	return ret;
}

static int crypto_ram_shash_export(struct shash_desc *desc, void *out)
{
	struct crypto_ram_shash_state *state = shash_desc_ctx(desc);
	struct crypto_shash *shash = desc->tfm;

	memcpy(out, state, crypto_shash_statesize(shash));
	return 0;
}

static int crypto_ram_shash_import(struct shash_desc *desc, const void *in)
{
	struct crypto_ram_shash_state *state = shash_desc_ctx(desc);
	struct crypto_shash *shash = desc->tfm;

	memcpy(state, in, crypto_shash_statesize(shash));
	return 0;
}
