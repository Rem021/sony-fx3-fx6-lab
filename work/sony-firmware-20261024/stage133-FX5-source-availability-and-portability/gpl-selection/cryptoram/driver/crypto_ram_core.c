/**
 * Copyright 2022 Sony Corporation
 * Copyright (c) 2018-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include "crypto_ram_core.h"
#include "crypto_ram_algs.h"
#include "netsec_api.h"
#include "crypto_ram_skcipher.h"
#include "crypto_ram_shash.h"
#include "crypto_ram_aead.h"

#include <linux/platform_device.h>

#include <linux/version.h>
#include <linux/kernel.h>

static const netsec_desc_ring_no_t desc_ring_no[] = {
	NETSEC_DESC_RING_NO_ENC_RAW_TX, NETSEC_DESC_RING_NO_DEC_RAW_TX,
	NETSEC_DESC_RING_NO_ENC_RAW_RX, NETSEC_DESC_RING_NO_DEC_RAW_RX
};

static const netsec_desc_ring_no_t tx_desc_ring_no[] = {
	NETSEC_DESC_RING_NO_ENC_RAW_TX, NETSEC_DESC_RING_NO_DEC_RAW_TX
};

static const u32 enc_top_tx_irq_factor[] = { NETSEC_TOP_IRQ_REG_ENC_RAW_TX,
					     NETSEC_TOP_IRQ_REG_DEC_RAW_TX };

static const netsec_desc_ring_no_t rx_desc_ring_no[] = {
	NETSEC_DESC_RING_NO_ENC_RAW_RX, NETSEC_DESC_RING_NO_DEC_RAW_RX
};

static const u32 enc_top_rx_irq_factor[] = { NETSEC_TOP_IRQ_REG_ENC_RAW_RX,
					     NETSEC_TOP_IRQ_REG_DEC_RAW_RX };

#define CRYPTO_RAM_ALL_TX_IRQ \
	(NETSEC_TOP_IRQ_REG_ENC_RAW_TX | NETSEC_TOP_IRQ_REG_DEC_RAW_TX)

#define CRYPTO_RAM_ALL_RX_IRQ \
	(NETSEC_TOP_IRQ_REG_ENC_RAW_RX | NETSEC_TOP_IRQ_REG_DEC_RAW_RX)

#define CRYPTO_RAM_AXI_ERR_STATUS (0x3U << 6)

static void crypto_ram_tasklet(unsigned long data);
static int __crypto_ram_tasklet(netsec_handle_t handle,
				netsec_desc_ring_no_t ring_no,
				struct crypto_ram_device *core);

/**
 * Completes the given cipher operation
 *
 * @info: current operation status
 * @err: error flag of the cipher operation performed
 */
static int crypto_ram_rx_complete(struct crypto_ram_calcinfo *info, u8 status)
{
	struct crypto_async_request *base;
	int err = 0;

	switch (info->type) {
	case CRYPTO_RAM_ALG_TYPE_AEAD:
		base = crypto_ram_aead_complete(info);
		break;

	case CRYPTO_RAM_ALG_TYPE_SKCIPHER:
		base = crypto_ram_skcipher_complete(info);
		break;

	case CRYPTO_RAM_ALG_TYPE_SHASH:
		return crypto_ram_shash_complete(info);

	default:
		NETSEC_MSG_ERR("Invalid type: 0x%X", info->type);
		err = -EINVAL;
		goto exit;
	}

	base->complete(base, status == 0 ? 0 : -EBADMSG);

exit:
	crypto_ram_calcinfo_destroy(info);
	return err;
}

/**
 * crypto_ram_tasklet() - receives chipher data from NETSEC_ENC
 */
static void crypto_ram_tasklet(unsigned long data)
{
	struct crypto_ram_device *core = (struct crypto_ram_device *)data;
	u32 status, tx_irq_status;
	int err = 0;
	int i = 0;

	do {
		status = netsec_get_top_irq_status(core->handle, NETSEC_FALSE,
						   core->use_inta);
		if ((status & CRYPTO_RAM_ALL_TX_IRQ) != 0) {
			for (i = 0; i < ARRAY_SIZE(enc_top_tx_irq_factor);
			     i++) {
				tx_irq_status =
					netsec_enc_get_desc_ring_irq_status(
						core->handle,
						tx_desc_ring_no[i], false);
				if ((tx_irq_status &
				     CRYPTO_RAM_AXI_ERR_STATUS) != 0) {
					NETSEC_MSG_ERR(
						"tx_ring_no=%d transfer failed. irq_status:0x%08x",
						(int)tx_desc_ring_no[i],
						tx_irq_status);
					netsec_enc_clear_desc_ring_irq_status(
						core->handle,
						tx_desc_ring_no[i],
						tx_irq_status);
				}
			}
		}

		for (i = 0; i < ARRAY_SIZE(enc_top_rx_irq_factor); i++) {
			if ((status & enc_top_rx_irq_factor[i]) != 0) {
				err = __crypto_ram_tasklet(
					core->handle, rx_desc_ring_no[i], core);

				if (err != 0) {
					NETSEC_MSG_ERR(
						"rx_ring_no=%d failed with error code %d",
						(int)rx_desc_ring_no[i], err);
					break;
				}
			}
		}
	} while ((status & CRYPTO_RAM_ALL_RX_IRQ) != 0);
}

static int __crypto_ram_tasklet(netsec_handle_t handle,
				netsec_desc_ring_no_t ring_no,
				struct crypto_ram_device *core)
{
	u16 scat_num;
	u32 totlen;
	struct crypto_ram_calcinfo *info;
	int i, netsec_err, err;
	u8 status;

	netsec_frag_info_t *rx =
		kmalloc(sizeof(netsec_frag_info_t) * CRYPTO_RAM_SCAT_NUM_MAX,
			GFP_ATOMIC);

	if (!rx) {
		err = -ENOMEM;
		goto exit;
	}

	while (netsec_enc_get_rx_num(handle, ring_no) != 0) {
		scat_num = CRYPTO_RAM_SCAT_NUM_MAX;
		netsec_err = netsec_enc_get_rx_pkt_data(handle, ring_no,
							&status, rx, &totlen,
							NULL, (void **)&info,
							&scat_num);
		if (netsec_err != NETSEC_ERR_OK) {
			err = -EINVAL;
			goto exit;
		}

		for (i = 0; i < scat_num; i++) {
			crypto_ram_unset_rx_frag_info(core->dev, &rx[i]);
		}


		err = crypto_ram_rx_complete(info, status);

		if (err)
			goto exit;
	}

exit:
	kfree(rx);
	netsec_enable_top_irq(handle, CRYPTO_RAM_ALL_RX_IRQ, core->use_inta);
	return err;
}

/**
 * crypto_ram_irq_handler() - Prepares for receiving cipher data
 */
irqreturn_t crypto_ram_irq_handler(int irq, void *dev_id)
{
	struct crypto_ram_device *core = (struct crypto_ram_device *)dev_id;
	netsec_handle_t handle = core->handle;
	u32 irq_rx = CRYPTO_RAM_ALL_RX_IRQ;

	u32 status =
		netsec_get_top_irq_status(handle, NETSEC_TRUE, core->use_inta);

	if (status == 0)
		return IRQ_NONE;

	if ((status & irq_rx) != 0) {
		netsec_disable_top_irq(handle, status, core->use_inta);
		tasklet_schedule(&core->tasklet);
	}

	return IRQ_HANDLED;
}

static int crypto_ram_init_descriptors(netsec_handle_t handle,
				       u16 rx_packet_count, u16 rx_timeout_us)
{
	int i, j, err;

	const netsec_desc_ring_no_t ring_tx[] = {
		NETSEC_DESC_RING_NO_ENC_RAW_TX, NETSEC_DESC_RING_NO_DEC_RAW_TX
	};

	const netsec_desc_ring_no_t ring_rx[] = {
		NETSEC_DESC_RING_NO_ENC_RAW_RX, NETSEC_DESC_RING_NO_DEC_RAW_RX
	};

	for (i = 0; i < ARRAY_SIZE(ring_rx); i++) {
		err = netsec_enc_clean_rx_desc_ring(handle, ring_rx[i]);

		if (err != NETSEC_ERR_OK) {
			NETSEC_MSG_ERR("netsec_clean_desc_ring(%d) failed: %d",
				       ring_rx[i], (int)err);
			return -EINVAL;
		}

		err = netsec_enc_set_rx_irq_param(handle, ring_rx[i],
						  rx_packet_count, NETSEC_FALSE,
						  rx_timeout_us);

		if (err != NETSEC_ERR_OK) {
			NETSEC_MSG_ERR(
				"netsec_enc_set_rx_irq_param(%d) failed: %d",
				ring_rx[i], (int)err);
			return -EINVAL;
		}
	}

	for (i = 0; i < ARRAY_SIZE(ring_tx); i++) {
		err = netsec_enc_clean_tx_desc_ring(handle, ring_tx[i]);

		if (err != NETSEC_ERR_OK) {
			NETSEC_MSG_ERR("netsec_clean_desc_ring(%d) failed: %d",
				       ring_tx[i], (int)err);
			return -EINVAL;
		}
	}

	for (i = 0; i < NETSEC_DESC_RING_NO_MAX; i++) {
		err = netsec_enc_start_desc_ring(handle, desc_ring_no[i]);

		if (err != NETSEC_ERR_OK) {
			NETSEC_MSG_ERR(
				"netsec_enc_start_desc_ring(%d) failed: %d",
				desc_ring_no[i], (int)err);

			for (j = i; j >= 0; j--) {
				netsec_enc_stop_desc_ring(handle,
							  desc_ring_no[j]);
			}

			return -EINVAL;
		}
	}

	return 0;
}

static void crypto_ram_parse_device_param(netsec_param_t *param,
					  struct crypto_ram_config *cfg)
{
	param->netsec_ver = cfg->hw_ver;

	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_ENC_RAW_TX].valid_flag =
		NETSEC_TRUE;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_ENC_RAW_TX].entry_num =
		cfg->enc_raw_tx_desc_num;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_ENC_RAW_TX]
		.little_endian_flag = NETSEC_TRUE;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_ENC_RAW_RX].valid_flag =
		NETSEC_TRUE;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_ENC_RAW_RX].entry_num =
		cfg->enc_raw_rx_desc_num;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_ENC_RAW_RX]
		.little_endian_flag = NETSEC_TRUE;

	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_DEC_RAW_TX].valid_flag =
		NETSEC_TRUE;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_DEC_RAW_TX].entry_num =
		cfg->dec_raw_tx_desc_num;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_DEC_RAW_TX]
		.little_endian_flag = NETSEC_TRUE;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_DEC_RAW_RX].valid_flag =
		NETSEC_TRUE;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_DEC_RAW_RX].entry_num =
		cfg->dec_raw_rx_desc_num;
	param->enc_desc_ring_param[NETSEC_DESC_RING_NO_DEC_RAW_RX]
		.little_endian_flag = NETSEC_TRUE;

	param->use_netsec_func = NETSEC_FUNC_BIT_ENC;
}

static int to_driver_error(int netsec_err)
{
	int err;

	switch (netsec_err) {
	case NETSEC_ERR_OK:
		err = 0;
		break;

	case NETSEC_ERR_ALLOC:
		err = -ENOMEM;
		break;

	case NETSEC_ERR_NOTAVAIL:
		err = -ENODEV;
		break;

	case NETSEC_ERR_BUSY:
		err = -EBUSY;
		break;

	default:
		err = -EINVAL;
	}

	return err;
}

#define RX_PACKET_COUNT 3
#define RX_TIMEOUT_US	160

int crypto_ram_init(struct crypto_ram_device *core,
		    struct crypto_ram_config *cfg)
{
	int err;
	netsec_param_t param = { 0 };

	crypto_ram_parse_device_param(&param, cfg);

	err = to_driver_error(netsec_init(cfg->base, core->dev, &param,
					  (void *)&core->handle));
	if (err) {
		dev_err(core->dev, "Failed to initialize NETSEC: %d\n", err);
		return err;
	}

	err = crypto_ram_init_descriptors(core->handle, RX_PACKET_COUNT,
					  RX_TIMEOUT_US);
	if (err)
		goto exit_core;

	mutex_init(&core->said_sem);
	tasklet_init(&core->tasklet, crypto_ram_tasklet, (unsigned long)core);
	netsec_enable_top_irq(core->handle, CRYPTO_RAM_ALL_RX_IRQ,
			      core->use_inta);

	return 0;

exit_core:
	netsec_terminate(core->handle);

	return err;
}

void crypto_ram_uninit(struct crypto_ram_device *core)
{
	int i;

	netsec_disable_top_irq(core->handle, CRYPTO_RAM_ALL_RX_IRQ,
			       core->use_inta);
	for (i = 0; i < ARRAY_SIZE(enc_top_tx_irq_factor); i++) {
		netsec_enc_clear_desc_ring_irq_status(
			core->handle, tx_desc_ring_no[i],
			(NETSEC_CH_IRQ_REG_NOT_OWNER | NETSEC_CH_IRQ_REG_EMPTY |
			 NETSEC_CH_IRQ_REG_ERR));
	}

	for (i = 0; i < ARRAY_SIZE(desc_ring_no); i++) {
		netsec_enc_stop_desc_ring(core->handle, desc_ring_no[i]);
	}
	mutex_destroy(&core->said_sem);
	netsec_terminate(core->handle);
}
