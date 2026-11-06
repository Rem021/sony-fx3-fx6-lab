/**
 * Copyright 2022 Sony Corporation
 * Copyright (c) 2018-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include "crypto_ram_aead.h"
#include "crypto_ram_algs.h"

#include <crypto/aead.h>
#include <crypto/aes.h>
#include <crypto/gcm.h>
#include <crypto/chacha.h>
#include <crypto/poly1305.h>
#include <crypto/algapi.h>
#include <linux/crypto.h>

#define AESCCM_Q_BIT_FIELD (0x7)
#define AESCCM_N_BIT_MAX   (15U)

struct crypto_ram_aead_dev {
	struct crypto_ram_device *core;
	struct aead_alg *alg;
	int algnum;
	struct list_head list;
	bool is_init;
};

struct crypto_ram_aead_ctx {
	struct crypto_ram_device *core;
	u8 enc_alg;
	u8 auth_alg;
	u8 id;

	bool needs_deckey;
	u8 dummy_rcv_buf[1];
};

static int crypto_ram_aead_cra_init_raw(struct crypto_aead *aead);
static void crypto_ram_aead_cra_exit_raw(struct crypto_aead *aead);
static int crypto_ram_aead_setauthsize_raw_aesgcm(struct crypto_aead *aead,
						  unsigned int authsize);
static int crypto_ram_aead_setauthsize_raw_aesccm(struct crypto_aead *aead,
						  unsigned int authsize);
static int crypto_ram_aead_setauthsize_raw_chachapoly(struct crypto_aead *aead,
						      unsigned int authsize);
static int crypto_ram_aead_setkey_raw(struct crypto_aead *aead, const u8 *key,
				      unsigned int keylen);
static int crypto_ram_aead_encrypt_raw(struct aead_request *req);
static int crypto_ram_aead_decrypt_raw(struct aead_request *req);
static int crypto_ram_aead_encrypt_raw_aesccm(struct aead_request *req);
static int crypto_ram_aead_decrypt_raw_aesccm(struct aead_request *req);

static struct aead_alg crypto_ram_aead_algs_raw_base[] = {
	{
		.base = {
			.cra_name = "gcm(aes)",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_AEAD | CRYPTO_ALG_ASYNC,
			.cra_blocksize = 1,
			.cra_ctxsize = sizeof(struct crypto_ram_aead_ctx),
			.cra_module = THIS_MODULE,
		},
		.setkey = crypto_ram_aead_setkey_raw,
		.setauthsize = crypto_ram_aead_setauthsize_raw_aesgcm,
		.encrypt = crypto_ram_aead_encrypt_raw,
		.decrypt = crypto_ram_aead_decrypt_raw,
		.ivsize = GCM_AES_IV_SIZE,
		.maxauthsize = AES_BLOCK_SIZE,
		.init = crypto_ram_aead_cra_init_raw,
		.exit = crypto_ram_aead_cra_exit_raw,
	},
	{
		.base = {
			.cra_name = "ccm(aes)",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_AEAD | CRYPTO_ALG_ASYNC,
			.cra_blocksize = 1,
			.cra_ctxsize = sizeof(struct crypto_ram_aead_ctx),
			.cra_module = THIS_MODULE,
		},
		.setkey = crypto_ram_aead_setkey_raw,
		.setauthsize = crypto_ram_aead_setauthsize_raw_aesccm,
		.encrypt = crypto_ram_aead_encrypt_raw_aesccm,
		.decrypt = crypto_ram_aead_decrypt_raw_aesccm,
		.ivsize = AES_BLOCK_SIZE,
		.maxauthsize = AES_BLOCK_SIZE,
		.init = crypto_ram_aead_cra_init_raw,
		.exit = crypto_ram_aead_cra_exit_raw,
	},
	{
		.base = {
			.cra_name = "rfc7539(chacha20,poly1305)",
			.cra_driver_name = "",
			.cra_priority = CRYPTO_RAM_ALG_PRIORITY,
			.cra_flags = CRYPTO_ALG_TYPE_AEAD | CRYPTO_ALG_ASYNC,
			.cra_blocksize = 1,
			.cra_ctxsize = sizeof(struct crypto_ram_aead_ctx),
			.cra_module = THIS_MODULE,
		},
		.setkey = crypto_ram_aead_setkey_raw,
		.setauthsize = crypto_ram_aead_setauthsize_raw_chachapoly,
		.encrypt = crypto_ram_aead_encrypt_raw,
		.decrypt = crypto_ram_aead_decrypt_raw,
		.ivsize = CHACHAPOLY_IV_SIZE,
		.maxauthsize = POLY1305_DIGEST_SIZE,
		.init = crypto_ram_aead_cra_init_raw,
		.exit = crypto_ram_aead_cra_exit_raw,
	},
};

static int crypto_ram_aead_create_raw_algs(struct crypto_ram_aead_dev *dev)
{
	int i;
	int ret = 0;

	dev->alg = devm_kzalloc(dev->core->dev,
				sizeof(crypto_ram_aead_algs_raw_base),
				GFP_KERNEL);
	if (!dev->alg)
		return -ENOMEM;

	memcpy(dev->alg, crypto_ram_aead_algs_raw_base,
	       sizeof(crypto_ram_aead_algs_raw_base));

	dev->algnum = ARRAY_SIZE(crypto_ram_aead_algs_raw_base);

	for (i = 0; i < dev->algnum; i++) {
		ret = crypto_ram_core_set_driver_name(dev->core,
						      &dev->alg[i].base);
		if (ret != 0) {
			break;
		}
	}

	return ret;
}

static int crypto_ram_register_raw_algs(struct crypto_ram_aead_dev *dev)
{
	int err;

	if (dev->core->said_num == 0)
		return 0;

	err = crypto_ram_aead_create_raw_algs(dev);
	if (err)
		goto exit;

	err = crypto_register_aeads(dev->alg, dev->algnum);
	if (err)
		goto exit;

	dev_info(dev->core->dev, "Registered aead\n");
	return 0;

exit:
	dev_err(dev->core->dev, "Failed to register aead\n");
	return err;
}

static void crypto_ram_unregister_raw_algs(struct crypto_ram_aead_dev *dev)
{
	if (dev->core->said_num == 0)
		return;

	crypto_unregister_aeads(dev->alg, dev->algnum);
}

static struct crypto_ram_aead_dev *
crypto_ram_aead_create(struct crypto_ram_device *core)
{
	struct crypto_ram_aead_dev *dev;

	dev = devm_kzalloc(core->dev, sizeof(struct crypto_ram_aead_dev),
			   GFP_KERNEL);
	if (!dev)
		return dev;

	dev->core = core;
	return dev;
}

static void crypto_ram_aead_destroy(struct crypto_ram_aead_dev *dev)
{
	/* Nothing to be done for now */
}

static bool crypto_ram_aead_has_alg(struct crypto_ram_aead_dev *dev,
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

static struct crypto_ram_aead_dev crypto_ram_aead;

static int crypto_ram_aead_find_device(struct crypto_ram_device **core,
				       const char *driver_name)
{
	struct crypto_ram_aead_dev *dev;

	list_for_each_entry (dev, &crypto_ram_aead.list, list) {
		if (crypto_ram_aead_has_alg(dev, driver_name))
			*core = dev->core;
		return 0;
	}

	NETSEC_MSG_ERR("Device not found for: %s", driver_name);
	return -EINVAL;
}

int crypto_ram_register_aeads(struct crypto_ram_device *core)
{
	struct crypto_ram_aead_dev *dev;
	int err;

	dev = crypto_ram_aead_create(core);
	if (IS_ERR(dev))
		return PTR_ERR(dev);

	INIT_LIST_HEAD(&dev->list);

	if (!crypto_ram_aead.is_init) {
		INIT_LIST_HEAD(&crypto_ram_aead.list);
		crypto_ram_aead.is_init = true;
	}

	list_add_tail(&dev->list, &crypto_ram_aead.list);

	err = crypto_ram_register_raw_algs(dev);
	if (err)
		return err;

	return 0;
}

void crypto_ram_unregister_aeads(struct crypto_ram_device *core)
{
	struct crypto_ram_aead_dev *dev = NULL;

	list_for_each_entry (dev, &crypto_ram_aead.list, list) {
		if (dev->core == core)
			break;
	}

	if (!dev) {
		dev_err(core->dev, "aead device not found for %s\n",
			core->name);
		return;
	}

	list_del(&dev->list);

	crypto_ram_unregister_raw_algs(dev);
	crypto_ram_aead_destroy(dev);
}

struct crypto_async_request *
crypto_ram_aead_complete(struct crypto_ram_calcinfo *info)
{
	int i;
	struct crypto_aead *aead = crypto_aead_reqtfm(info->req_aead);
	struct crypto_ram_aead_ctx *ctx = crypto_aead_ctx(aead);

	for (i = 0; i < info->tx_num; i++) {
		crypto_ram_unset_tx_frag_info(ctx->core->dev, &info->tx[i]);
	}
	kfree(info->tx);
	return &info->req_aead->base;
}

static int crypto_ram_aead_cra_init_raw(struct crypto_aead *aead)
{
	int err = 0;
	struct crypto_tfm *tfm = crypto_aead_tfm(aead);
	struct crypto_ram_aead_ctx *ctx = crypto_tfm_ctx(tfm);

	memset(ctx, 0, sizeof(*ctx));

	err = crypto_ram_aead_find_device(&ctx->core,
					  tfm->__crt_alg->cra_driver_name);
	if (err)
		return err;

	return crypto_ram_core_acquire_entry(ctx->core, &ctx->id);
}

static void crypto_ram_aead_cra_exit_raw(struct crypto_aead *aead)
{
	struct crypto_tfm *tfm = crypto_aead_tfm(aead);
	struct crypto_ram_aead_ctx *ctx = crypto_tfm_ctx(tfm);

	crypto_ram_core_release_entry(ctx->core, &ctx->id);
}

static int crypto_ram_aead_setauthsize_raw_aesgcm(struct crypto_aead *aead,
						  unsigned int authsize)
{
	return crypto_gcm_check_authsize(authsize);
}

static int crypto_ram_aead_setauthsize_raw_aesccm(struct crypto_aead *aead,
						  unsigned int authsize)
{
	switch (authsize) {
	case 4: /* fall-through */
	case 6: /* fall-through */
	case 8: /* fall-through */
	case 10: /* fall-through */
	case 12: /* fall-through */
	case 14: /* fall-through */
	case 16:
		break;
	default:
		return -EINVAL;
	}

	return 0;
}

static int crypto_ram_aead_setauthsize_raw_chachapoly(struct crypto_aead *aead,
						      unsigned int authsize)
{
	return (authsize == POLY1305_DIGEST_SIZE) ? 0 : -EINVAL;
}

struct aead_sadata {
	const char *name;
	const struct crypto_ram_key_alg_pair *enc_pair;
	const u8 enclen;
	const struct crypto_ram_key_alg_pair *auth_pair;
	const u8 authlen;
	const bool needs_deckey;
};

#define AEAD_SADATA_ITEM(name, enc_pair, auth_pair, needs_deckey) \
	{                                                         \
		name, enc_pair, ARRAY_SIZE(enc_pair), auth_pair,  \
			ARRAY_SIZE(auth_pair), needs_deckey       \
	}

static const struct aead_sadata sa_table[] = {
	AEAD_SADATA_ITEM("gcm(aes)", encpair_aes_gcm, authpair_aes_gcm, false),
	AEAD_SADATA_ITEM("ccm(aes)", encpair_aes_ccm, authpair_aes_ccm, false),
	AEAD_SADATA_ITEM("rfc7539(chacha20,poly1305)", encpair_chachapoly,
			 authpair_chachapoly, false),
};

/* Configure algorithms to run */
static int crypto_ram_aead_set_alg(struct crypto_ram_aead_ctx *ctx,
				   char *cra_name, u32 enc_key_bit,
				   u32 auth_key_bit)
{
	int i;
	u8 enc_alg, auth_alg;

	for (i = 0; i < ARRAY_SIZE(sa_table); i++) {
		if (strcmp(cra_name, sa_table[i].name) == 0) {
			if (crypto_ram_get_pair_alg(sa_table[i].enc_pair,
						    sa_table[i].enclen,
						    enc_key_bit, &enc_alg)) {
				NETSEC_MSG_INFO(
					"Failed to set enc_alg for %s: keybit = %d",
					cra_name, enc_key_bit);
				return -EINVAL;
			}

			if (crypto_ram_get_pair_alg(sa_table[i].auth_pair,
						    sa_table[i].authlen,
						    auth_key_bit, &auth_alg)) {
				NETSEC_MSG_INFO(
					"Failed to set auth_alg for %s: keybit = %d",
					cra_name, auth_key_bit);
				return -EINVAL;
			}

			ctx->enc_alg = enc_alg;
			ctx->auth_alg = auth_alg;
			ctx->needs_deckey = sa_table[i].needs_deckey;

			return 0;
		}
	}

	NETSEC_MSG_ERR("alg not found: %s", cra_name);
	return -EINVAL;
}

static int crypto_ram_aead_configure_entry_raw(struct crypto_ram_aead_ctx *ctx,
					       const u8 *key, u32 keylen)
{
	int err = 0;
	netsec_sa_data_t sa = { 0 };

	sa.bulk_mode = NETSEC_BULK_MODE_RAW;
	sa.encrypt_alg = ctx->enc_alg;
	sa.auth_alg = ctx->auth_alg;
	sa.process_type = NETSEC_RAW_PROCESS_AEAD;
	memcpy(sa.encrypt_key, key, keylen);

	err = crypto_ram_core_configure_entry(ctx->core, ctx->id, &sa);
	if (err)
		return err;

	memzero_explicit(&sa, sizeof(sa));
	return err;
}

static int crypto_ram_aead_setkey_raw(struct crypto_aead *aead, const u8 *key,
				      unsigned int keylen)
{
	struct crypto_tfm *tfm = crypto_aead_tfm(aead);
	struct crypto_ram_aead_ctx *ctx = crypto_tfm_ctx(tfm);
	struct crypto_alg *alg = tfm->__crt_alg;
	int err;

	err = crypto_ram_aead_set_alg(ctx, alg->cra_name, keylen * 8,
				      keylen * 8);
	if (err)
		return err;

	err = crypto_ram_aead_configure_entry_raw(ctx, key, keylen);
	if (err)
		return err;

	return 0;
}

/** Runs RAW mode cipher operation */
static int crypto_ram_aead_do_raw(struct aead_request *req, const bool is_enc,
				  const u8 tx_ring_no, const u8 rx_ring_no)
{
	struct crypto_aead *aead = crypto_aead_reqtfm(req);
	struct crypto_ram_aead_ctx *ctx = crypto_aead_ctx(aead);
	netsec_handle_t *handle = ctx->core->handle;
	u32 src_nents = sg_nents(req->src);
	u32 dst_nents = sg_nents(req->dst);
	u32 src_nents_tot;
	u32 assoclen = req->assoclen;
	u32 tx_num = 0, rx_num = 0;
	netsec_enc_tx_pkt_ctrl_t cfg = { 0 };
	netsec_frag_info_t *tx = NULL, *rx = NULL;
	struct crypto_ram_calcinfo *info = NULL;
	struct scatterlist *src, *dst;
	int err = 0, i;
	netsec_err_t netsec_err;
	long nbytes;

	/* +1 to store IV */
	src_nents_tot = 1 + src_nents;

	if (src_nents_tot > CRYPTO_RAM_SCAT_NUM_MAX ||
	    dst_nents > CRYPTO_RAM_SCAT_NUM_MAX) {
		NETSEC_MSG_ERR("Too many scatterlists");
		return -ENOMEM;
	}

	tx = kzalloc(sizeof(netsec_frag_info_t) * src_nents_tot, GFP_KERNEL);
	rx = kzalloc(sizeof(netsec_frag_info_t) * dst_nents, GFP_KERNEL);
	info = crypto_ram_calcinfo_create(req, CRYPTO_RAM_ALG_TYPE_AEAD,
					  crypto_aead_ivsize(aead));

	if (!tx || !rx || !info) {
		NETSEC_MSG_ERR("Memory allocation failure");
		err = -ENOMEM;
		goto exit_mem;
	}

	/* Copy IV to DMA-able area */
	memcpy(info->data.buf, req->iv, crypto_aead_ivsize(aead));

	/* Register IV first */
	err = crypto_ram_set_tx_frag_info(ctx->core->dev, &tx[tx_num++],
					  info->data.buf, info->data.nbytes);
	if (unlikely(err != 0)) {
		NETSEC_MSG_ERR("DMA mapping failure");
		tx_num--;
		goto exit_dma;
	}

	/* Count the number of bytes to be registered for Tx */
	nbytes = req->cryptlen + req->assoclen;

	/* Register remaining data */
	for_each_sg (req->src, src, src_nents, i) {
		if (nbytes <= 0)
			break;

		/*
		 * Total crypt length can sometimes be larger than each buffer's
		 * size, hence we take their min() here
		 */
		err = crypto_ram_set_tx_frag_info(
			ctx->core->dev, &tx[tx_num++], sg_virt(src),
			min((u32)nbytes, src->length));
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma;
		}

		nbytes -= min((u32)nbytes, src->length);
	}
	crypto_ram_set_tx_info(info, tx_num, tx);

	/* Count the number of bytes to be registered for Rx */
	nbytes = is_enc ? req->cryptlen + crypto_aead_authsize(aead) :
			  req->cryptlen - crypto_aead_authsize(aead);

	/* Register remaining data */
	for_each_sg (req->dst, dst, dst_nents, i) {
		/*
		 * When Tx data contains AAD, Rx scatterlist expects the driver
		 * to store encrypted data with an offset by `assoclen` bytes,
		 * so we need to
		 * - discard first Rx sg elements smaller than `assoclen` bytes, and
		 * - set an offset to the first packet
		 */
		if (nbytes > 0) {
			if (dst->length <= assoclen) {
				assoclen -= dst->length;
				continue;
			}
			/* size of an sg element can be too large,
			 * so we need min() here
			 */
			err = crypto_ram_set_rx_frag_info(
				ctx->core->dev, &rx[rx_num],
				sg_virt(dst) + assoclen,
				min(dst->length - assoclen, (u32)nbytes));
			assoclen = 0;
			nbytes -= rx[rx_num++].len;

		} else {
			/* Set dummy_buf for zero data length in decryption */
			err = crypto_ram_set_rx_frag_info(
				ctx->core->dev, &rx[rx_num++],
				ctx->dummy_rcv_buf,
				ARRAY_SIZE(ctx->dummy_rcv_buf));
		}
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			rx_num--;
			goto exit_dma;
		}

		if (nbytes <= 0) {
			break;
		}
	}

	netsec_enc_clean_tx_desc_ring(handle, tx_ring_no);

	cfg.said = ctx->id;
	cfg.direct_iv_flag = false;
	cfg.enc_flag = is_enc;
	cfg.stream_flag = false;
	cfg.raw_aead_flag = true;
	cfg.valid_null_flag = true;
	cfg.aad_len = req->assoclen;
	cfg.icv_len = crypto_aead_authsize(aead);

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

static int crypto_ram_aead_encrypt_raw(struct aead_request *req)
{
	return crypto_ram_aead_do_raw(req, true, NETSEC_DESC_RING_NO_ENC_RAW_TX,
				      NETSEC_DESC_RING_NO_ENC_RAW_RX);
}

static int crypto_ram_aead_decrypt_raw(struct aead_request *req)
{
	return crypto_ram_aead_do_raw(req, false,
				      NETSEC_DESC_RING_NO_DEC_RAW_TX,
				      NETSEC_DESC_RING_NO_DEC_RAW_RX);
}

static inline bool crypto_ram_ccm_valid_iv(uint8_t iv_0)
{
	/* 2 <= L <= 8, so 1 <= L' <= 7. */
	if ((iv_0 < 1) || (iv_0 > 7)) {
		return false;
	}

	return true;
}

static inline uint8_t crypto_ram_ccm_decode_q(uint8_t iv_0)
{
	return ((iv_0 & AESCCM_Q_BIT_FIELD) +
		1); /* q: 2 to 8(max), min 1 is error */
}

static inline uint32_t crypto_ram_get_nonce_len(uint8_t iv_0)
{
	return (AESCCM_N_BIT_MAX - crypto_ram_ccm_decode_q(iv_0));
}

static uint64_t crypto_ram_ccm_get_max_len(uint8_t nonce_len)
{
	uint64_t max_len = 0xffffffffULL;
	if ((nonce_len == 12) || (nonce_len == 13)) {
		max_len = (0x1ULL << ((AESCCM_N_BIT_MAX - nonce_len) * 8)) - 1;
	}
	return max_len;
}

static int crypto_ram_aead_do_raw_aesccm(struct aead_request *req,
					 const bool is_enc, const u8 tx_ring_no,
					 const u8 rx_ring_no)
{
	struct crypto_aead *aead = crypto_aead_reqtfm(req);
	struct crypto_ram_aead_ctx *ctx = crypto_aead_ctx(aead);
	netsec_handle_t *handle = ctx->core->handle;
	u32 src_nents = sg_nents(req->src);
	u32 dst_nents = sg_nents(req->dst);
	u32 src_nents_tot;
	u32 assoclen = req->assoclen;
	u32 tx_num = 0, rx_num = 0;
	netsec_enc_tx_pkt_ctrl_t cfg = { 0 };
	netsec_frag_info_t *tx = NULL, *rx = NULL;
	struct crypto_ram_calcinfo *info = NULL;
	struct scatterlist *src, *dst;
	int err = 0, i;
	netsec_err_t netsec_err;
	long nbytes;
	uint8_t nonce_len = crypto_ram_get_nonce_len(*req->iv);
	uint64_t src_len;

	if (!crypto_ram_ccm_valid_iv(*req->iv)) {
		return -EINVAL;
	}

	src_len = is_enc ? req->cryptlen :
			   req->cryptlen - crypto_aead_authsize(aead);
	if (src_len > crypto_ram_ccm_get_max_len(nonce_len)) {
		return -EINVAL;
	}

	/* +1 to store IV */
	src_nents_tot = 1 + src_nents;

	if (src_nents_tot > CRYPTO_RAM_SCAT_NUM_MAX ||
	    dst_nents > CRYPTO_RAM_SCAT_NUM_MAX) {
		NETSEC_MSG_ERR("Too many scatterlists");
		return -ENOMEM;
	}

	tx = kzalloc(sizeof(netsec_frag_info_t) * src_nents_tot, GFP_KERNEL);
	rx = kzalloc(sizeof(netsec_frag_info_t) * dst_nents, GFP_KERNEL);
	info = crypto_ram_calcinfo_create(req, CRYPTO_RAM_ALG_TYPE_AEAD,
					  nonce_len);

	if (!tx || !rx || !info) {
		NETSEC_MSG_ERR("Memory allocation failure");
		err = -ENOMEM;
		goto exit_mem;
	}

	/* Copy IV to DMA-able area */
	memcpy(info->data.buf, req->iv + 1, nonce_len);

	/* Register IV first */
	err = crypto_ram_set_tx_frag_info(ctx->core->dev, &tx[tx_num++],
					  info->data.buf, info->data.nbytes);
	if (unlikely(err != 0)) {
		NETSEC_MSG_ERR("DMA mapping failure");
		tx_num--;
		goto exit_dma;
	}

	/* Count the number of bytes to be registered for Tx */
	nbytes = req->cryptlen + req->assoclen;

	/* Register remaining data */
	for_each_sg (req->src, src, src_nents, i) {
		if (nbytes <= 0)
			break;

		/*
		 * Total crypt length can sometimes be larger than each buffer's
		 * size, hence we take their min() here
		 */
		err = crypto_ram_set_tx_frag_info(
			ctx->core->dev, &tx[tx_num++], sg_virt(src),
			min((u32)nbytes, src->length));
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			tx_num--;
			goto exit_dma;
		}

		nbytes -= min((u32)nbytes, src->length);
	}
	crypto_ram_set_tx_info(info, tx_num, tx);

	/* Count the number of bytes to be registered for Rx */
	nbytes = is_enc ? req->cryptlen + crypto_aead_authsize(aead) :
			  req->cryptlen - crypto_aead_authsize(aead);

	/* Register remaining data */
	for_each_sg (req->dst, dst, dst_nents, i) {
		/*
		 * When Tx data contains AAD, Rx scatterlist expects the driver
		 * to store encrypted data with an offset by `assoclen` bytes,
		 * so we need to
		 * - discard first Rx sg elements smaller than `assoclen` bytes, and
		 * - set an offset to the first packet
		 */
		if (nbytes > 0) {
			if (dst->length <= assoclen) {
				assoclen -= dst->length;
				continue;
			}
			/* size of an sg element can be too large,
			 * so we need min() here
			 */
			err = crypto_ram_set_rx_frag_info(
				ctx->core->dev, &rx[rx_num],
				sg_virt(dst) + assoclen,
				min(dst->length - assoclen, (u32)nbytes));
			assoclen = 0;
			nbytes -= rx[rx_num++].len;

		} else {
			/* Set dummy_buf for zero data length in decryption */
			err = crypto_ram_set_rx_frag_info(
				ctx->core->dev, &rx[rx_num++],
				ctx->dummy_rcv_buf,
				ARRAY_SIZE(ctx->dummy_rcv_buf));
		}
		if (unlikely(err != 0)) {
			NETSEC_MSG_ERR("DMA mapping failure");
			rx_num--;
			goto exit_dma;
		}

		if (nbytes <= 0) {
			break;
		}
	}

	netsec_enc_clean_tx_desc_ring(handle, tx_ring_no);

	cfg.said = ctx->id;
	cfg.direct_iv_flag = false;
	cfg.enc_flag = is_enc;
	cfg.stream_flag = false;
	cfg.raw_aead_flag = true;
	cfg.valid_null_flag = true;
	cfg.aad_len = req->assoclen;
	cfg.icv_len = crypto_aead_authsize(aead);
	cfg.nonce_len = nonce_len;

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

static int crypto_ram_aead_encrypt_raw_aesccm(struct aead_request *req)
{
	return crypto_ram_aead_do_raw_aesccm(req, true,
					     NETSEC_DESC_RING_NO_ENC_RAW_TX,
					     NETSEC_DESC_RING_NO_ENC_RAW_RX);
}

static int crypto_ram_aead_decrypt_raw_aesccm(struct aead_request *req)
{
	return crypto_ram_aead_do_raw_aesccm(req, false,
					     NETSEC_DESC_RING_NO_DEC_RAW_TX,
					     NETSEC_DESC_RING_NO_DEC_RAW_RX);
}
