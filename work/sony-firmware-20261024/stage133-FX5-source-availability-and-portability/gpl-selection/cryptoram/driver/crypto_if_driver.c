/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <linux/module.h>
#include <linux/mod_devicetable.h>
#include <linux/platform_device.h>
#include <linux/of_address.h>

#include <crypto/algapi.h>
#include <linux/crypto.h>

#include "crypto_cdev.h"
#include "crypto_ioctl.h"
#include "crypto_handle.h"
#include "sdebug.h"

#include "crypto_ram_core.h"
#include "crypto_ram_algs.h"
#include "crypto_ram_skcipher.h"
#include "crypto_ram_shash.h"
#include "crypto_ram_aead.h"

enum log_level_e log_level = S_DEBUG_ERROR;

#define CRYPTO_RAM_DESC_NUM (256U)

/**
 * crypto_ram_verify_config() - Validates the input parameters
 */
static int crypto_ram_verify_config(struct device *dev,
				    struct crypto_ram_config *cfg)
{
	int err = 0;

	dev_notice(dev, "Module parameters:\n");

	if (strlen(cfg->name) > 15) {
		dev_err(dev, "dev-name must be 15 characters or less\n");
		err = -EINVAL;

	} else {
		dev_notice(dev, "dev-name = %s\n", cfg->name);
	}

	dev_notice(dev, "hw-ver = %08x", cfg->hw_ver);
	dev_notice(dev, "enc-raw-{tx, rx}-desc-num = {%d, %d}\n",
		   cfg->enc_raw_tx_desc_num, cfg->enc_raw_rx_desc_num);
	dev_notice(dev, "dec-raw-{tx, rx}-desc-num = {%d, %d}\n",
		   cfg->dec_raw_tx_desc_num, cfg->dec_raw_rx_desc_num);

	if (cfg->enc_raw_tx_desc_num == 0 || cfg->enc_raw_rx_desc_num == 0 ||
	    cfg->dec_raw_tx_desc_num == 0 || cfg->dec_raw_rx_desc_num == 0) {
		dev_err(dev, "Zeroed desc-num found\n");
		err = -EINVAL;
	}

	if (cfg->enc_raw_tx_desc_num > NETSEC_DESC_ENTRY_NUM_MAX ||
	    cfg->enc_raw_rx_desc_num > NETSEC_DESC_ENTRY_NUM_MAX ||
	    cfg->dec_raw_tx_desc_num > NETSEC_DESC_ENTRY_NUM_MAX ||
	    cfg->dec_raw_rx_desc_num > NETSEC_DESC_ENTRY_NUM_MAX) {
		dev_err(dev, "Too-large desc-num found\n");
		err = -EINVAL;
	}

	if (cfg->enc_raw_tx_desc_num < CRYPTO_RAM_SCAT_NUM_MAX ||
	    cfg->enc_raw_rx_desc_num < CRYPTO_RAM_SCAT_NUM_MAX ||
	    cfg->dec_raw_tx_desc_num < CRYPTO_RAM_SCAT_NUM_MAX ||
	    cfg->dec_raw_rx_desc_num < CRYPTO_RAM_SCAT_NUM_MAX) {
		dev_err(dev, "Too-small RAW desc-num found\n");
		err = -EINVAL;
	}

	dev_notice(dev, "said-num = %d", cfg->said_num);

	if (cfg->said_num == 0) {
		dev_err(dev, "said-num zeroed\n");
		err = -EINVAL;
	}

	if (cfg->said_num > NETSEC_SADB_ENTRY_NUM_MAX) {
		dev_err(dev, "Too many SAIDs\n");
		err = -EINVAL;
	}

	return err;
}

static int crypto_ram_set_config(struct device *dev,
				 struct crypto_ram_config *cfg)
{
	const u32 *p;
	struct device_node *node = dev->of_node;

	cfg->name = "crypto_ram";

	p = of_get_property(node, "hw-ver", NULL);

	if (p) {
		cfg->hw_ver = be32_to_cpu(*p);
	} else {
		dev_err(dev, "hw-ver undefined\n");
		return -EINVAL;
	}

	cfg->enc_raw_tx_desc_num = CRYPTO_RAM_DESC_NUM;
	cfg->enc_raw_rx_desc_num = CRYPTO_RAM_DESC_NUM;
	cfg->dec_raw_tx_desc_num = CRYPTO_RAM_DESC_NUM;
	cfg->dec_raw_rx_desc_num = CRYPTO_RAM_DESC_NUM;

	p = of_get_property(node, "raw-said-num", NULL);
	cfg->said_num = p ? be32_to_cpu(*p) : 32;

	return crypto_ram_verify_config(dev, cfg);
}

/** Create & initialize crypto_ram core device object */
static struct crypto_ram_device *
crypto_ram_core_create(struct platform_device *pdev)
{
	int err, irq;
	struct crypto_ram_config cfg;
	struct resource *res;
	struct crypto_ram_device *core;
	void *err_ptr;
	struct device *dev = &pdev->dev;

	err = crypto_ram_set_config(dev, &cfg);
	if (err)
		return ERR_PTR(err);

	core = devm_kzalloc(&pdev->dev, sizeof(*core), GFP_KERNEL);
	if (!core)
		return ERR_PTR(-ENOMEM);

	core->name = cfg.name;
	core->dev = &pdev->dev;
	core->said_num = cfg.said_num;

	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	if (!res) {
		dev_err(dev, "Missing base resource\n");
		err_ptr = ERR_PTR(-EINVAL);
		goto exit;
	}

	cfg.base =
		devm_ioremap(&pdev->dev, res->start, res->end - res->start + 1);
	if (!cfg.base) {
		dev_err(dev, "ioremap() failed\n");
		err_ptr = ERR_PTR(-EINVAL);
		goto exit;
	}

	irq = platform_get_irq(pdev, 0);
	if (irq < 0) {
		dev_err(dev, "Missing IRQ resource\n");
		err_ptr = ERR_PTR(-ENODEV);
		goto exit;
	}

	err = devm_request_irq(&pdev->dev, irq, crypto_ram_irq_handler, 0,
			       "crypto_ram", core);
	if (err) {
		err_ptr = ERR_PTR(err);
		goto exit;
	}

	err = crypto_ram_init(core, &cfg);
	if (err) {
		err_ptr = ERR_PTR(err);
		goto exit;
	}

	core->cdev_handle = cdev_handle_create(&pdev->dev);
	if (IS_ERR(core->cdev_handle)) {
		err_ptr = ERR_PTR(-ENOMEM);
		goto exit;
	}

	err = cdev_register(core->cdev_handle, &crypto_fops);
	if (err != 0) {
		err_ptr = ERR_PTR(err);
		goto exit;
	}

	return core;

exit:
	devm_kfree(&pdev->dev, core);
	return err_ptr;
}

static void crypto_ram_core_destroy(struct crypto_ram_device *core)
{
	cdev_unregister(core->cdev_handle);
	crypto_ram_uninit(core);
	memset(&core, 0, sizeof(core));
}

static int crypto_ram_register_algs(struct crypto_ram_device *core)
{
	int err;

	err = crypto_ram_register_aeads(core);
	if (err)
		return err;

	err = crypto_ram_register_skciphers(core);
	if (err)
		goto skcipher_reg_err;

	err = crypto_ram_register_shashes(core);
	if (err)
		goto shash_reg_err;

	return 0;
shash_reg_err:
	crypto_ram_unregister_skciphers(core);

skcipher_reg_err:
	crypto_ram_unregister_aeads(core);

	return err;
}

static void crypto_ram_unregister_algs(struct crypto_ram_device *core)
{
	crypto_ram_unregister_aeads(core);
	crypto_ram_unregister_skciphers(core);
	crypto_ram_unregister_shashes(core);
}

static int crypto_if_probe(struct platform_device *pdev)
{
	int err;
	struct crypto_ram_device *core;

	pdev->dev.coherent_dma_mask = DMA_BIT_MASK(35);
	pdev->dev.dma_mask = &pdev->dev.coherent_dma_mask;

	core = crypto_ram_core_create(pdev);
	if (IS_ERR(core))
		return PTR_ERR(core);

	platform_set_drvdata(pdev, core);

	err = crypto_ram_register_algs(core);
	if (err) {
		crypto_ram_core_destroy(core);
		return err;
	}

	crypto_handle_mutex_init();
	if (crypto_handle_workqueue_init() != 0) {
		return -ENOMEM;
	}
	crypto_handle_completion_init();

	return 0;
}

static int crypto_if_remove(struct platform_device *pdev)
{
	struct crypto_ram_device *core = platform_get_drvdata(pdev);

	crypto_handle_workqueue_destroy();
	crypto_handle_mutex_destroy();

	crypto_ram_unregister_algs(core);
	crypto_ram_core_destroy(core);
	return 0;
}

static const struct of_device_id crypto_if_ids[] = {
	{ .compatible = "cxd,crypto_ram" },
	{}
};

static struct platform_driver crypto_if_driver = {
	.probe = crypto_if_probe,
	.remove = crypto_if_remove,
	.driver =
		{
			.name = "crypto_if",
			.of_match_table = crypto_if_ids,
		},
};

static int __init crypto_if_driver_module_init(void)
{
	return platform_driver_register(&crypto_if_driver);
}
module_init(crypto_if_driver_module_init);

static void __exit crypto_if_driver_module_exit(void)
{
	platform_driver_unregister(&crypto_if_driver);
}
module_exit(crypto_if_driver_module_exit);

MODULE_DESCRIPTION("Crypto-RAM driver");
MODULE_AUTHOR("Sony Corporation, Socionext Inc.");
MODULE_LICENSE("GPL");
MODULE_VERSION("1.0");
