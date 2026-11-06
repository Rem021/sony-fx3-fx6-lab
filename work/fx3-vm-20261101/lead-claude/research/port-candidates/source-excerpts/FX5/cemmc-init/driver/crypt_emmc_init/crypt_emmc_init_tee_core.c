/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <linux/slab.h> /* kmalloc */
#include <linux/err.h>

#include "crypt_emmc_init_tee_core.h"
#include "crypt_emmc_init_print.h"

/** Obtain configuration of Crypto_RAM driver in OP-TEE */
static int crypt_emmc_init_tee_ctx_match(struct tee_ioctl_version_data *ver,
					 const void *data)
{
	crypt_emmc_pr_trace("%s", __func__);

	return ver->impl_id == TEE_IMPL_ID_OPTEE ? 1 : 0;
}

/** Connect to the corresponding PTA in OP-TEE OS */
static int
crypt_emmc_init_tee_establish_session(struct crypt_emmc_init_teedev *teedev)
{
	struct device *dev = teedev->dev;
	struct tee_client_device *client_device = to_tee_client_device(dev);
	int ret = 0, err = -ENODEV;
	struct tee_ioctl_open_session_arg sess_arg;

	crypt_emmc_pr_trace("%s", __func__);

	memset(&sess_arg, 0, sizeof(sess_arg));

	teedev->ctx = tee_client_open_context(
		NULL, crypt_emmc_init_tee_ctx_match, NULL, NULL);
	if (IS_ERR(teedev->ctx)) {
		crypt_emmc_pr_err("tee_client_open_context failed\n");
		return -ENODEV;
	}

	export_uuid(sess_arg.uuid, &client_device->id.uuid);
	sess_arg.clnt_login = TEE_IOCTL_LOGIN_PUBLIC;
	sess_arg.num_params = 0;

	ret = tee_client_open_session(teedev->ctx, &sess_arg, NULL);
	if (ret < 0 || sess_arg.ret != 0) {
		crypt_emmc_pr_err("tee_client_open_session failed, err: %x\n",
				  sess_arg.ret);
		err = -EINVAL;
		goto out_ctx;
	}

	teedev->session_id = sess_arg.session;

	return 0;

out_ctx:
	tee_client_close_context(teedev->ctx);

	return err;
}

static void
crypt_emmc_init_tee_destroy_session(struct crypt_emmc_init_teedev *teedev)
{
	crypt_emmc_pr_trace("%s", __func__);

	if (!IS_ERR(teedev->ctx)) {
		tee_client_close_session(teedev->ctx, teedev->session_id);
		tee_client_close_context(teedev->ctx);
	}
}

void crypt_emmc_init_tee_clear_shm(struct tee_shm *shm, size_t len)
{
	u8 *buf = tee_shm_get_va(shm, 0);

	crypt_emmc_pr_trace("%s", __func__);

	memzero_explicit(buf, len);
}

struct crypt_emmc_init_teedev *crypt_emmc_init_tee_init(struct device *dev)
{
	int err;
	struct crypt_emmc_init_teedev *teedev;

	crypt_emmc_pr_trace("%s", __func__);

	teedev = devm_kzalloc(dev, sizeof(struct crypt_emmc_init_teedev),
			      GFP_KERNEL);
	if (!teedev) {
		crypt_emmc_pr_err(
			"Failed to allocate crypt_emmc_init_teedev\n");
		return ERR_PTR(-ENOMEM);
	}
	teedev->dev = dev;

	err = crypt_emmc_init_tee_establish_session(teedev);
	if (err) {
		crypt_emmc_pr_err("Failed to establish session\n");
		goto out;
	}
	teedev->shm_in =
		tee_shm_alloc_kernel_buf(teedev->ctx, CRYPT_EMMC_SHM_LEN);
	if (IS_ERR(teedev->shm_in)) {
		crypt_emmc_pr_err("tee_shm_alloc_kernel_buf failed\n");
		err = PTR_ERR(teedev->shm_in);
		crypt_emmc_init_tee_destroy_session(teedev);
		goto out;
	}

	return teedev;

out:
	return ERR_PTR(err);
}

void crypt_emmc_init_tee_exit(struct crypt_emmc_init_teedev *teedev)
{
	crypt_emmc_pr_trace("%s", __func__);

	tee_shm_free(teedev->shm_in);
	crypt_emmc_init_tee_destroy_session(teedev);
}
