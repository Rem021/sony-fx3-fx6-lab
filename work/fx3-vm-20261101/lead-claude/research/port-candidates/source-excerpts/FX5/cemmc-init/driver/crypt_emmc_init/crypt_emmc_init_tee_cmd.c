/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <uapi/linux/rtnetlink.h>
#include <linux/tee_drv.h>

#include "crypt_emmc_init_tee_cmd.h"
#include "crypt_emmc_init_print.h"

#define TEE_NUM_PARAMS 4

int crypt_emmc_init_tee_cmd_init(struct crypt_emmc_init_teedev *teedev,
				 struct crypt_emmc_init_cmd_init *cmd_init)
{
	struct tee_ioctl_invoke_arg inv_arg = { 0 };
	struct tee_param param[TEE_NUM_PARAMS] = { 0 };
	int invoke_err = 0, ret = 0;

	crypt_emmc_pr_trace("%s", __func__);

	memset(&inv_arg, 0, sizeof(inv_arg));
	memset(param, 0, sizeof(param));

	inv_arg.func = CRYPT_EMMC_PTA_CMD_INIT;
	inv_arg.session = teedev->session_id;
	inv_arg.num_params = TEE_NUM_PARAMS;

	param[0] = (struct tee_param){
		.attr = TEE_IOCTL_PARAM_ATTR_TYPE_VALUE_INPUT,
		.u.value.a = cmd_init->unit_size,
	};

	invoke_err = tee_client_invoke_func(teedev->ctx, &inv_arg, param);
	if (invoke_err < 0 || inv_arg.ret != 0) {
		crypt_emmc_pr_err("invoke err func:%d ret:%x\n", inv_arg.func,
				  inv_arg.ret);
		ret = -EINVAL;
		goto crypt_emmc_tee_cmd_init_exit;
	}
	crypt_emmc_pr_debug("%s success\n", __func__);

crypt_emmc_tee_cmd_init_exit:
	return ret;
}

int crypt_emmc_init_tee_cmd_setkey(struct crypt_emmc_init_teedev *teedev,
				   struct crypt_emmc_init_cmd_setkey *cmd_setkey)
{
	struct tee_ioctl_invoke_arg inv_arg = { 0 };
	struct tee_param param[TEE_NUM_PARAMS] = { 0 };
	int invoke_err = 0, ret = 0;

	crypt_emmc_pr_trace("%s", __func__);

	inv_arg.func = CRYPT_EMMC_PTA_CMD_SETKEY;
	inv_arg.session = teedev->session_id;
	inv_arg.num_params = TEE_NUM_PARAMS;

	param[0] = (struct tee_param){
		.attr = TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT,
		.u.memref.shm = teedev->shm_in,
		.u.memref.size = cmd_setkey->keylen,
		.u.memref.shm_offs = 0,
	};

	param[1] = (struct tee_param){
		.attr = TEE_IOCTL_PARAM_ATTR_TYPE_MEMREF_INPUT,
		.u.memref.shm = teedev->shm_in,
		.u.memref.size = cmd_setkey->keylen,
		.u.memref.shm_offs = param[0].u.memref.size,
	};

	/* setkey to shared memory */
	memcpy(tee_shm_get_va(teedev->shm_in, 0), cmd_setkey->key1,
	       cmd_setkey->keylen);
	memcpy(tee_shm_get_va(teedev->shm_in, cmd_setkey->keylen),
	       cmd_setkey->key2, cmd_setkey->keylen);
#ifdef CRYPT_EMMC_INIT_CONFIG_DEBUG
	print_hex_dump(KERN_ERR, "key1:", DUMP_PREFIX_NONE, cmd_setkey->keylen,
		       1, cmd_setkey->key1, cmd_setkey->keylen, false);
	print_hex_dump(KERN_ERR, "key2:", DUMP_PREFIX_NONE, cmd_setkey->keylen,
		       1, cmd_setkey->key2, cmd_setkey->keylen, false);
#endif /* CRYPT_EMMC_INIT_CONFIG_DEBUG */

	invoke_err = tee_client_invoke_func(teedev->ctx, &inv_arg, param);
	if (invoke_err < 0 || inv_arg.ret != 0) {
		crypt_emmc_pr_err("invoke err func:%d ret:%x\n", inv_arg.func,
				  inv_arg.ret);
		ret = -EINVAL;
		goto crypt_emmc_tee_cmd_setkey_exit;
	}
	crypt_emmc_pr_debug("%s success\n", __func__);

crypt_emmc_tee_cmd_setkey_exit:
	crypt_emmc_init_tee_clear_shm(
		teedev->shm_in,
		cmd_setkey->keylen << 1); /* clear key1, key2 region */
	memzero_explicit(cmd_setkey->key1, cmd_setkey->keylen);
	memzero_explicit(cmd_setkey->key2, cmd_setkey->keylen);

#ifdef CRYPT_EMMC_INIT_CONFIG_DEBUG
	print_hex_dump(KERN_ERR, "key1(zero clear):", DUMP_PREFIX_NONE,
		       cmd_setkey->keylen, 1, cmd_setkey->key1,
		       cmd_setkey->keylen, false);
	print_hex_dump(KERN_ERR, "key2(zero clear):", DUMP_PREFIX_NONE,
		       cmd_setkey->keylen, 1, cmd_setkey->key2,
		       cmd_setkey->keylen, false);
#endif /* CRYPT_EMMC_INIT_CONFIG_DEBUG */

	return ret;
}
