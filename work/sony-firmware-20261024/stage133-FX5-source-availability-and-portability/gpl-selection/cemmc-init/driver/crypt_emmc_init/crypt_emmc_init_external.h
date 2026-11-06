/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPT_EMMC_INIT_EXTERNAL_H
#define CRYPT_EMMC_INIT_EXTERNAL_H

#include <linux/panic.h>
#include <linux/tee_drv.h>

/* KEYSET UUID : 99B6DCB3-C8EF-43A5-8DB2-9776D0DDDEEF */
#define KEYSET_TA_UUID				{{ 0x99, 0xB6, 0xDC, 0xB3, 0xC8, 0xEF, 0x43, 0xA5,	\
										0x8D, 0xB2, 0x97, 0x76, 0xD0, 0xDD, 0xDE, 0xEF }}
#define TA_CMD_SETKEY_EMMC			(1)

static int cemmc_keyset_tee_match(struct tee_ioctl_version_data *ver, const void *data) {
	return ( ver->impl_id == TEE_IMPL_ID_OPTEE );
}

static inline void eMMC_CRYPT_KEY_SET(void)
{
	const uuid_t ta_uuid = KEYSET_TA_UUID;
	int ret = 0;
	struct tee_ioctl_open_session_arg sess_arg;
	struct tee_ioctl_invoke_arg invk_arg;
	struct tee_context *ctx = tee_client_open_context(NULL, cemmc_keyset_tee_match, NULL, NULL);
	if(IS_ERR(ctx)) { panic("Error at [tee_client_open_context]\n"); }

	memset(&sess_arg, 0, sizeof(sess_arg));
	export_uuid(sess_arg.uuid, &ta_uuid);
	sess_arg.clnt_login = TEE_IOCTL_LOGIN_PUBLIC;
	sess_arg.num_params = 0;

	ret = tee_client_open_session(ctx, &sess_arg, NULL);
	if (ret < 0 || sess_arg.ret != 0) { panic("Error at [tee_client_open_session]\n"); }

	memset(&invk_arg, 0, sizeof(invk_arg));
	invk_arg.session = sess_arg.session;
	invk_arg.func = TA_CMD_SETKEY_EMMC;

	ret = tee_client_invoke_func(ctx, &invk_arg, NULL);
	if (ret < 0 || sess_arg.ret != 0) { panic("Error at [tee_client_invoke_func]\n"); }

	tee_client_close_session(ctx, sess_arg.session);
	tee_client_close_context(ctx);
}

#endif /* CRYPT_EMMC_INIT_EXTERNAL_H */
