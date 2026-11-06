/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_IOCTL_CMD_H
#define CRYPTO_IOCTL_CMD_H

#ifndef __KERNEL__
#include <sys/ioctl.h>
#endif /* __KERNEL__ */

#include "crypto_param.h"
#include "crypto_type.h"

#define CRYPTO_IOCTL_MAGIC    'C'
#define CRYPTO_IO(num, len)   _IO(CRYPTO_IOCTL_MAGIC, num, len)
#define CRYPTO_IOR(num, len)  _IOR(CRYPTO_IOCTL_MAGIC, num, len)
#define CRYPTO_IOW(num, len)  _IOW(CRYPTO_IOCTL_MAGIC, num, len)
#define CRYPTO_IOWR(num, len) _IOWR(CRYPTO_IOCTL_MAGIC, num, len)

struct crypto_ioctl_init_param {
	struct cryptoRam_initParam *init;
	int id;
	E_CRYPTO_ERROR ret;
};

struct crypto_ioctl_exit_param {
	int id;
	E_CRYPTO_ERROR ret;
};

struct crypto_ioctl_crypto_param {
	struct cryptoRam_cryptoParam *crypto;
	int id;
	E_CRYPTO_ERROR ret;
};

struct crypto_ioctl_enc_param {
	struct cryptoRam_encParam *enc;
	int id;
	E_CRYPTO_ERROR ret;
};

struct crypto_ioctl_dec_param {
	struct cryptoRam_decParam *dec;
	int id;
	E_CRYPTO_ERROR ret;
};

struct crypto_ioctl_auth_param {
	struct cryptoRam_authParam *auth;
	int id;
	E_CRYPTO_ERROR ret;
};

struct crypto_ioctl_exe_param {
	UINT32 timeout;
	int id;
	E_CRYPTO_ERROR ret;
};

struct crypto_ioctl_cancel_param {
	int id;
	E_CRYPTO_ERROR ret;
};

struct crypto_ioctl_release_param {
	E_CRYPTO_ERROR ret;
};

struct crypto_ioctl_wait_param {
	int id;
	E_CRYPTO_ERROR ret;
};

#define CRYPTO_IOCTL_INIT CRYPTO_IOWR(0U, struct crypto_ioctl_init_param)
#define CRYPTO_IOCTL_EXIT CRYPTO_IOWR(1U, struct crypto_ioctl_exit_param)
#define CRYPTO_IOCTL_SET_CRYPTO_PARAM \
	CRYPTO_IOWR(2U, struct crypto_ioctl_crypto_param)
#define CRYPTO_IOCTL_SET_ENC_PARAM \
	CRYPTO_IOWR(3U, struct crypto_ioctl_enc_param)
#define CRYPTO_IOCTL_SET_DEC_PARAM \
	CRYPTO_IOWR(4U, struct crypto_ioctl_dec_param)
#define CRYPTO_IOCTL_SET_AUTH_PARAM \
	CRYPTO_IOWR(5U, struct crypto_ioctl_auth_param)
#define CRYPTO_IOCTL_EXECUTE CRYPTO_IOWR(6U, struct crypto_ioctl_exe_param)
#define CRYPTO_IOCTL_CANCEL  CRYPTO_IOWR(7U, struct crypto_ioctl_cancel_param)
#define CRYPTO_IOCTL_RELEASE_DRV \
	CRYPTO_IOWR(8U, struct crypto_ioctl_release_param)
#define CRYPTO_IOCTL_WAIT_COMPLETION \
	CRYPTO_IOWR(9U, struct crypto_ioctl_wait_param)

#endif /* CRYPTO_IOCTL_CMD_H */
