/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <linux/fs.h>
#include <linux/slab.h>
#include "crypto_ioctl.h"
#include "crypto_ioctl_cmd.h"
#include "crypto_handle.h"

#include "sdebug.h"

#define memcpy_from_user(to, arg, bytes) \
	copy_from_user(to, (void __user *)arg, bytes)

#define memcpy_to_user(arg, from, bytes) \
	copy_to_user((void __user *)arg, from, bytes)

static int crypto_fops_open(struct inode *inode, struct file *filp)
{
	return 0;
}

static int crypto_fops_close(struct inode *inode, struct file *filp)
{
	return 0;
}

static long crypto_fops_ioctl_init(unsigned long arg)
{
	struct crypto_ioctl_init_param ioctl_param;
	struct cryptoRam_initParam *init_param = NULL;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ret = memcpy_from_user(&ioctl_param, arg, sizeof(ioctl_param));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_init_end;
	}
	init_param = kzalloc(sizeof(struct cryptoRam_initParam), GFP_KERNEL);
	ret = memcpy_from_user(init_param, ioctl_param.init,
			       sizeof(struct cryptoRam_initParam));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_init_end;
	}

	s_print(S_DEBUG_DEBUG, "%s operation_mode:%d\n", __func__,
		init_param->operation_mode);
	s_print(S_DEBUG_DEBUG, "%s crypto_mode:%d\n", __func__,
		init_param->crypto_mode);
	s_print(S_DEBUG_DEBUG, "%s aes_key_len:%d\n", __func__,
		init_param->aes_key_len);

	ioctl_param.ret = crypto_handle_init(&ioctl_param.id, init_param);

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, ioctl_param.id);

	ret = memcpy_to_user(arg, &ioctl_param, sizeof(ioctl_param));

crypto_fops_ioctl_init_end:
	if (init_param != NULL) {
		kfree(init_param);
		init_param = NULL;
	}

	return ret;
}

static long crypto_fops_ioctl_exit(unsigned long arg)
{
	struct crypto_ioctl_exit_param ioctl_param;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ret = memcpy_from_user(&ioctl_param, arg, sizeof(ioctl_param));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_exit_end;
	}

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, ioctl_param.id);

	ioctl_param.ret = crypto_handle_exit(ioctl_param.id);

	ret = memcpy_to_user(arg, &ioctl_param, sizeof(ioctl_param));

crypto_fops_ioctl_exit_end:

	return ret;
}

static long crypto_fops_ioctl_set_crypto_param(unsigned long arg)
{
	struct crypto_ioctl_crypto_param ioctl_param;
	struct cryptoRam_cryptoParam *crypto_param = NULL;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ret = memcpy_from_user(&ioctl_param, arg, sizeof(ioctl_param));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_set_crypto_param_end;
	}
	crypto_param =
		kzalloc(sizeof(struct cryptoRam_cryptoParam), GFP_KERNEL);
	ret = memcpy_from_user(crypto_param, ioctl_param.crypto,
			       sizeof(struct cryptoRam_cryptoParam));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_set_crypto_param_end;
	}

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, ioctl_param.id);

	ioctl_param.ret =
		crypto_handle_set_crypto_param(ioctl_param.id, crypto_param);

	ret = memcpy_to_user(arg, &ioctl_param, sizeof(ioctl_param));

crypto_fops_ioctl_set_crypto_param_end:
	if (crypto_param != NULL) {
		kfree(crypto_param);
		crypto_param = NULL;
	}

	return ret;
}

static long crypto_fops_ioctl_set_enc_param(unsigned long arg)
{
	struct crypto_ioctl_enc_param ioctl_param;
	struct cryptoRam_encParam *enc_param = NULL;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ret = memcpy_from_user(&ioctl_param, arg, sizeof(ioctl_param));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_set_enc_param_end;
	}
	enc_param = kzalloc(sizeof(struct cryptoRam_encParam), GFP_KERNEL);
	ret = memcpy_from_user(enc_param, ioctl_param.enc,
			       sizeof(struct cryptoRam_encParam));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_set_enc_param_end;
	}

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, ioctl_param.id);

	ioctl_param.ret =
		crypto_handle_set_enc_param(ioctl_param.id, enc_param);

	ret = memcpy_to_user(arg, &ioctl_param, sizeof(ioctl_param));

crypto_fops_ioctl_set_enc_param_end:
	if (enc_param != NULL) {
		kfree(enc_param);
		enc_param = NULL;
	}

	return ret;
}

static long crypto_fops_ioctl_set_dec_param(unsigned long arg)
{
	struct crypto_ioctl_dec_param ioctl_param;
	struct cryptoRam_decParam *dec_param = NULL;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ret = memcpy_from_user(&ioctl_param, arg, sizeof(ioctl_param));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_set_dec_param_end;
	}
	dec_param = kzalloc(sizeof(struct cryptoRam_decParam), GFP_KERNEL);
	ret = memcpy_from_user(dec_param, ioctl_param.dec,
			       sizeof(struct cryptoRam_decParam));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_set_dec_param_end;
	}

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, ioctl_param.id);

	ioctl_param.ret =
		crypto_handle_set_dec_param(ioctl_param.id, dec_param);

	ret = memcpy_to_user(arg, &ioctl_param, sizeof(ioctl_param));

crypto_fops_ioctl_set_dec_param_end:
	if (dec_param != NULL) {
		kfree(dec_param);
		dec_param = NULL;
	}

	return ret;
}

static long crypto_fops_ioctl_set_auth_param(unsigned long arg)
{
	struct crypto_ioctl_auth_param ioctl_param;
	struct cryptoRam_authParam *auth_param = NULL;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ret = memcpy_from_user(&ioctl_param, arg, sizeof(ioctl_param));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_set_auth_param_end;
	}
	auth_param = kzalloc(sizeof(struct cryptoRam_authParam), GFP_KERNEL);
	ret = memcpy_from_user(auth_param, ioctl_param.auth,
			       sizeof(struct cryptoRam_authParam));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_set_auth_param_end;
	}

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, ioctl_param.id);

	ioctl_param.ret =
		crypto_handle_set_auth_param(ioctl_param.id, auth_param);

	ret = memcpy_to_user(arg, &ioctl_param, sizeof(ioctl_param));

crypto_fops_ioctl_set_auth_param_end:
	if (auth_param != NULL) {
		kfree(auth_param);
		auth_param = NULL;
	}

	return ret;
}

static long crypto_fops_ioctl_execute(unsigned long arg)
{
	struct crypto_ioctl_exe_param ioctl_param;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ret = memcpy_from_user(&ioctl_param, arg, sizeof(ioctl_param));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_execute_end;
	}

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, ioctl_param.id);
	s_print(S_DEBUG_DEBUG, "%s timeout:%d\n", __func__,
		ioctl_param.timeout);
	ioctl_param.ret =
		crypto_handle_execute(ioctl_param.id, ioctl_param.timeout);

	ret = memcpy_to_user(arg, &ioctl_param, sizeof(ioctl_param));

crypto_fops_ioctl_execute_end:

	return ret;
}

static long crypto_fops_ioctl_wait_completion(unsigned long arg)
{
	struct crypto_ioctl_wait_param ioctl_param;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ret = memcpy_from_user(&ioctl_param, (void *)arg, sizeof(ioctl_param));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_wait_completion_end;
	}

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, ioctl_param.id);
	ioctl_param.ret = crypto_handle_wait_completion(ioctl_param.id);

	ret = memcpy_to_user((void *)arg, &ioctl_param, sizeof(ioctl_param));

crypto_fops_ioctl_wait_completion_end:

	return ret;
}

static long crypto_fops_ioctl_cancel(unsigned long arg)
{
	struct crypto_ioctl_cancel_param ioctl_param;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ret = memcpy_from_user(&ioctl_param, (void *)arg, sizeof(ioctl_param));
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "%s memcpy_from_user failed\n",
			__func__);
		goto crypto_fops_ioctl_cancel_end;
	}

	s_print(S_DEBUG_DEBUG, "%s id:%d\n", __func__, ioctl_param.id);
	ioctl_param.ret = crypto_handle_cancel(ioctl_param.id);

	ret = memcpy_to_user((void *)arg, &ioctl_param, sizeof(ioctl_param));

crypto_fops_ioctl_cancel_end:

	return ret;
}

static long crypto_fops_ioctl_release(unsigned long arg)
{
	struct crypto_ioctl_release_param ioctl_param;
	long ret;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	ioctl_param.ret = crypto_handle_release();

	ret = memcpy_to_user((void *)arg, &ioctl_param, sizeof(ioctl_param));

	return ret;
}

static long crypto_fops_ioctl(struct file *filp, unsigned int cmd,
			      unsigned long arg)
{
	long ret = 0;
	s_print(S_DEBUG_DEBUG, "%s %08x\n", __func__, cmd);

	switch (cmd) {
	case CRYPTO_IOCTL_INIT:
		ret = crypto_fops_ioctl_init(arg);
		break;
	case CRYPTO_IOCTL_EXIT:
		ret = crypto_fops_ioctl_exit(arg);
		break;
	case CRYPTO_IOCTL_SET_CRYPTO_PARAM:
		ret = crypto_fops_ioctl_set_crypto_param(arg);
		break;
	case CRYPTO_IOCTL_SET_ENC_PARAM:
		ret = crypto_fops_ioctl_set_enc_param(arg);
		break;
	case CRYPTO_IOCTL_SET_DEC_PARAM:
		ret = crypto_fops_ioctl_set_dec_param(arg);
		break;
	case CRYPTO_IOCTL_SET_AUTH_PARAM:
		ret = crypto_fops_ioctl_set_auth_param(arg);
		break;
	case CRYPTO_IOCTL_EXECUTE:
		ret = crypto_fops_ioctl_execute(arg);
		break;
	case CRYPTO_IOCTL_WAIT_COMPLETION:
		ret = crypto_fops_ioctl_wait_completion(arg);
		break;
	case CRYPTO_IOCTL_CANCEL:
		ret = crypto_fops_ioctl_cancel(arg);
		break;
	case CRYPTO_IOCTL_RELEASE_DRV:
		ret = crypto_fops_ioctl_release(arg);
		break;
	default:
		s_print(S_DEBUG_ERROR, "%s Invalid ioctl cmd:%08x\n", __func__,
			cmd);
		ret = -ENOSYS;
		break;
	}

	return ret;
}

struct file_operations crypto_fops = {
	.owner = THIS_MODULE,
	.open = crypto_fops_open,
	.release = crypto_fops_close,
	.unlocked_ioctl = crypto_fops_ioctl,
};
