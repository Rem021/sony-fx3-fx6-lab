/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <linux/platform_device.h>
#include <linux/of_device.h>
#include <linux/sh_clk.h>
#include <linux/reset.h>
#include <linux/suspend.h>
#include "crypt_emmc_init_internal.h"
#include "crypt_emmc_init.h"
#include "crypt_emmc_init_print.h"
#include "crypt_emmc_init_config.h"

#define CRYPTO_XTS_COMPATIBLE_NAME	"cxd,crypt_emmc_init"
#define CRYPTO_XTS_ACLK_NAME	"xts_aclk"
#define CRYPTO_XTS_S_PCLK_NAME	"xts_s_pclk"
#define CRYPTO_XTS_NS_PCLK_NAME "xts_ns_pclk"
#define CRYPTO_XTS_RST_NAME     "xts_rstx"

struct crypt_emmc_init_driver_info {
	struct clk *aclk;
	struct clk *s_pclk;
	struct clk *ns_pclk;
	struct reset_control *rst;
	struct crypt_emmc_init_teedev *teedev;
} driver_info = { 0 };

static bool early_init = false;
module_param(early_init, bool, 0644);

static bool key_256bit = false;
module_param(key_256bit, bool, 0644);

static uint32_t unit_size = 0;
module_param(unit_size, uint, 0);

bool is_eary_init(void)
{
	crypt_emmc_pr_trace("%s", __func__);

	return early_init;
}

bool is_key_256bit(void)
{
	crypt_emmc_pr_trace("%s", __func__);

	return key_256bit;
}

uint32_t get_unit_size(void)
{
	crypt_emmc_pr_trace("%s", __func__);

	return unit_size;
}

int crypt_emmc_init_hw_init(void)
{
	int ret = -1;

	crypt_emmc_pr_trace("%s", __func__);

#ifndef CONFIG_ARCH_CXD90XXX_FPGA
	/* reset control */
	if (reset_control_assert(driver_info.rst)) {
		crypt_emmc_pr_err("Failed to assert reset\n");
		goto crypt_emmc_init_hw_init_end;
	}

	if (reset_control_deassert(driver_info.rst)) {
		crypt_emmc_pr_err("Failed to deassert reset\n");
		goto crypt_emmc_init_hw_init_end;
	}
	crypt_emmc_pr_debug("%s reset_control done\n", __func__);
#endif /* CONFIG_ARCH_CXD90XXX_FPGA */

	ret = 0;

#ifndef CONFIG_ARCH_CXD90XXX_FPGA
crypt_emmc_init_hw_init_end:
#endif /* CONFIG_ARCH_CXD90XXX_FPGA */
	return ret;
}

struct crypt_emmc_init_teedev *crypt_emmc_init_get_teedev(void)
{
	crypt_emmc_pr_trace("%s", __func__);

	return driver_info.teedev;
}

int crypt_emmc_init_probe(struct device *dev)
{
	int ret = 0;
#ifndef CONFIG_ARCH_CXD90XXX_FPGA
	struct device_node *node =
	    of_find_compatible_node(NULL, NULL, CRYPTO_XTS_COMPATIBLE_NAME);
#endif /* CONFIG_ARCH_CXD90XXX_FPGA */

	crypt_emmc_pr_trace("%s", __func__);

#ifndef CONFIG_ARCH_CXD90XXX_FPGA
	dev->of_node = node;
	driver_info.aclk = devm_clk_get_optional_enabled(dev, CRYPTO_XTS_ACLK_NAME);
	if (IS_ERR_OR_NULL(driver_info.aclk)) {
		crypt_emmc_pr_err("devm_clk_get_optional_enabled failed for aclk\n");
		return PTR_ERR(driver_info.aclk);
	}
	driver_info.s_pclk = devm_clk_get_optional_enabled(dev, CRYPTO_XTS_S_PCLK_NAME);
	if (IS_ERR_OR_NULL(driver_info.s_pclk)) {
		crypt_emmc_pr_err("devm_clk_get_optional_enabled failed for s_pclk\n");
		return PTR_ERR(driver_info.s_pclk);
	}
	driver_info.ns_pclk = devm_clk_get_optional_enabled(dev, CRYPTO_XTS_NS_PCLK_NAME);
	if (IS_ERR_OR_NULL(driver_info.ns_pclk)) {
		crypt_emmc_pr_err("devm_clk_get_optional_enabled failed for ns_pclk\n");
		return PTR_ERR(driver_info.ns_pclk);
	}

	driver_info.rst = devm_reset_control_get_optional_exclusive(dev, CRYPTO_XTS_RST_NAME);
	if (IS_ERR_OR_NULL(driver_info.rst)) {
		crypt_emmc_pr_err(
			"devm_reset_control_get_optional_exclusive failed "
			"for reset\n");
		return PTR_ERR(driver_info.rst);
	}
#endif /* CONFIG_ARCH_CXD90XXX_FPGA */

	driver_info.teedev = crypt_emmc_init_tee_init(dev);
	if (IS_ERR(driver_info.teedev)) {
		crypt_emmc_pr_err("crypt_emmc_init_tee_init failed\n");
		return PTR_ERR(driver_info.teedev);
	}

	if (cryptEmmcInit_init() != E_CYPR_ERR_OK) {
		crypt_emmc_pr_err("cryptEmmcInit_init failed\n");
		ret = -EIO;
	}

	return ret;
}

int crypt_emmc_init_remove(struct device *dev)
{
	crypt_emmc_pr_trace("%s", __func__);

	crypt_emmc_init_tee_exit(driver_info.teedev);
	return 0;
}

int crypt_emmc_init_suspend(struct device *dev)
{
	crypt_emmc_pr_trace("%s", __func__);

	return 0;
}

int crypt_emmc_init_resume(struct device *dev)
{
	int ret = 0;

	crypt_emmc_pr_trace("%s", __func__);

	if( pm_is_mem_alive() == 1 ) {
		/* Hot resume */
		if (cryptEmmcInit_init() != E_CYPR_ERR_OK) {
			crypt_emmc_pr_err("cryptEmmcInit_init failed\n");
			ret = -EIO;
		}
	}
	else {
		/* SSB */
		if( crypt_emmc_init_remove(dev) != 0 ) {
			crypt_emmc_pr_err("crypt_emmc_init_remove in resume failed\n");
			ret = -EIO;
		}
		
		driver_info.teedev = crypt_emmc_init_tee_init(dev);
		if (IS_ERR(driver_info.teedev)) {
			crypt_emmc_pr_err("crypt_emmc_init_tee_init failed\n");
			return PTR_ERR(driver_info.teedev);
		}

		if (cryptEmmcInit_init() != E_CYPR_ERR_OK) {
			crypt_emmc_pr_err("cryptEmmcInit_init failed\n");
			ret = -EIO;
		}
	}

	return ret;
}

static const struct tee_client_device_id crypt_emmc_init_tee_client_id_table[] = {
	{ UUID_INIT(0x7e592a35, 0x4637, 0x054a, 0x62, 0xb1, 0x74, 0x6e, 0xc0,
		    0x79, 0xea, 0x63) },
	{ /* sentinel */ },
};
MODULE_DEVICE_TABLE(tee, crypt_emmc_init_tee_client_id_table);

static struct dev_pm_ops crypt_emmc_init_pm_ops = {
	.suspend = crypt_emmc_init_suspend,
	.resume_early = crypt_emmc_init_resume,
};

static struct tee_client_driver crypt_emmc_init_tee_client = {
	.id_table   = crypt_emmc_init_tee_client_id_table,
	.driver = {
		.name = "crypt_emmc_init",
		.bus = &tee_bus_type,
		.probe = crypt_emmc_init_probe,
		.remove = crypt_emmc_init_remove,
		.pm = &crypt_emmc_init_pm_ops,
	},
};

static int __init crypt_emmc_init_module_init(void)
{
	crypt_emmc_pr_trace("%s", __func__);

	return driver_register(&crypt_emmc_init_tee_client.driver);
}
module_init(crypt_emmc_init_module_init);

static void __exit crypt_emmc_init_module_exit(void)
{
	crypt_emmc_pr_trace("%s", __func__);

	driver_unregister(&crypt_emmc_init_tee_client.driver);
}
module_exit(crypt_emmc_init_module_exit);

MODULE_DESCRIPTION("Crypt-eMMC Initialize driver");
MODULE_AUTHOR("Sony Corporation, Socionext Inc.");
MODULE_LICENSE("GPL");
MODULE_VERSION("1.0");
