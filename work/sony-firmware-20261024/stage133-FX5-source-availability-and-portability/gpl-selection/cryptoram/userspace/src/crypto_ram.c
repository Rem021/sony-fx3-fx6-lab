/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#include <string.h>
#include <pthread.h>
#include <sys/param.h>
#ifdef CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS
#include <unistd.h>
#endif /* CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS */
#include "crypto_ram.h"
#include "do_ioctl.h"
#include "crypto_ioctl_cmd.h"
#include "sdebug.h"

#define CRYPTO_PARAM_ARRAY_SIZE(array) (sizeof(array) / sizeof(array[0]))

enum log_level_e log_level = S_DEBUG_ERROR;

struct thread_data {
	struct crypto_ioctl_wait_param ioctl_param;
	void (*callback)(int id, E_CRYPTO_ERROR err);
};

static inline void crypto_hexdump(UINT8 *buf, UINT32 len)
{
	int i;
	UINT32 row = 16;
	UINT32 remain = len;

	if (S_DEBUG_DEBUG > log_level) {
		return;
	}

	while (remain != 0) {
		for (i = 0; i < MIN(remain, row); i++) {
			s_print(S_DEBUG_DEBUG, "%02x ", *buf++);
		}
		s_print(S_DEBUG_DEBUG, "\n");
		if (remain > row) {
			remain -= row;
		} else {
			remain = 0;
		}
	}
}

E_CRYPTO_ERROR cryptoRam_init(struct cryptoRam_initParam *initParam, int *id)
{
	struct crypto_ioctl_init_param ioctl_param = { 0 };

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	if ((initParam == NULL) || (id == NULL)) {
		s_print(S_DEBUG_ERROR, "initParam or id is NULL.\n");
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	/* Outputs input parameters */
	s_print(S_DEBUG_DEBUG, "operation_mode:0x%x\n",
		initParam->operation_mode);
	s_print(S_DEBUG_DEBUG, "crypto_mode:0x%x\n", initParam->crypto_mode);
	s_print(S_DEBUG_DEBUG, "aes_key_len:0x%x\n", initParam->aes_key_len);

	ioctl_param.init = initParam;
	if (do_ioctl(CRYPTO_IOCTL_INIT, &ioctl_param) != 0) {
		return E_CRYPTO_ERROR_UNKNOWN;
	}
	s_print(S_DEBUG_DEBUG, "id:%d\n", ioctl_param.id);
	*id = ioctl_param.id;

	if (ioctl_param.ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param.ret);
	} else {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
	}
	return ioctl_param.ret;
}

E_CRYPTO_ERROR cryptoRam_exit(int id)
{
	struct crypto_ioctl_exit_param ioctl_param = { 0 };

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	/* Outputs input parameters */
	s_print(S_DEBUG_DEBUG, "id:%d\n", id);

	ioctl_param.id = id;
	if (do_ioctl(CRYPTO_IOCTL_EXIT, &ioctl_param) != 0) {
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	if (ioctl_param.ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param.ret);
	} else {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
	}
	return ioctl_param.ret;
}

E_CRYPTO_ERROR
cryptoRam_setCryptoParam(int id, struct cryptoRam_cryptoParam *cryptoParam)
{
	struct crypto_ioctl_crypto_param ioctl_param = { 0 };

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	if (cryptoParam == NULL) {
		s_print(S_DEBUG_ERROR, "cryptoParam is NULL.\n");
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	/* Outputs input parameters */
	s_print(S_DEBUG_DEBUG, "id:%d\n", id);
	s_print(S_DEBUG_DEBUG, "data_num:%d\n", cryptoParam->data_num);
	s_print(S_DEBUG_DEBUG, "src_addr_lower:0x%08x\n",
		cryptoParam->src_addr_lower);
	s_print(S_DEBUG_DEBUG, "src_addr_upper:0x%08x\n",
		cryptoParam->src_addr_upper);
	s_print(S_DEBUG_DEBUG, "dst_addr_lower:0x%08x\n",
		cryptoParam->dst_addr_lower);
	s_print(S_DEBUG_DEBUG, "dst_addr_upper:0x%08x\n",
		cryptoParam->dst_addr_upper);

	ioctl_param.id = id;
	ioctl_param.crypto = cryptoParam;
	if (do_ioctl(CRYPTO_IOCTL_SET_CRYPTO_PARAM, &ioctl_param) != 0) {
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	if (ioctl_param.ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param.ret);
	} else {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
	}
	return ioctl_param.ret;
}

E_CRYPTO_ERROR cryptoRam_setEncParam(int id,
				     struct cryptoRam_encParam *encParam)
{
	struct crypto_ioctl_enc_param ioctl_param = { 0 };
	int i;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	if (encParam == NULL) {
		s_print(S_DEBUG_ERROR, "encParam is NULL.\n");
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	/* Outputs input parameters */
	s_print(S_DEBUG_DEBUG, "id:%d\n", id);
	for (i = 0; i < CRYPTO_PARAM_ARRAY_SIZE(encParam->encrypt_size); i++) {
		s_print(S_DEBUG_DEBUG, "encrypt_size[%d]:0x%08x\n", i,
			encParam->encrypt_size[i]);
	}
	for (i = 0; i < CRYPTO_PARAM_ARRAY_SIZE(encParam->encrypt_offset);
	     i++) {
		s_print(S_DEBUG_DEBUG, "encrypt_offset[%d]:0x%08x\n", i,
			encParam->encrypt_offset[i]);
	}
	s_print(S_DEBUG_DEBUG, "encrypt_key:0x");
	crypto_hexdump(encParam->encrypt_key, sizeof(encParam->encrypt_key));
	for (i = 0; i < CRYPTO_PARAM_ARRAY_SIZE(encParam->encrypt_iv); i++) {
		s_print(S_DEBUG_DEBUG, "encrypt_iv[%d]:0x", i);
		crypto_hexdump(encParam->encrypt_iv[i],
			       sizeof(encParam->encrypt_iv[0]));
	}
	for (i = 0; i < sizeof(encParam->encrypt_icv); i++) {
		s_print(S_DEBUG_DEBUG, "encrypt_icv[%d]:0x%02x\n", i,
			encParam->encrypt_icv[i]);
	}

	ioctl_param.id = id;
	ioctl_param.enc = encParam;
	if (do_ioctl(CRYPTO_IOCTL_SET_ENC_PARAM, &ioctl_param) != 0) {
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	if (ioctl_param.ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param.ret);
	} else {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
	}
	return ioctl_param.ret;
}

E_CRYPTO_ERROR cryptoRam_setDecParam(int id,
				     struct cryptoRam_decParam *decParam)
{
	struct crypto_ioctl_dec_param ioctl_param = { 0 };
	int i;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	if (decParam == NULL) {
		s_print(S_DEBUG_ERROR, "decParam is NULL.\n");
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	/* Outputs input parameters */
	s_print(S_DEBUG_DEBUG, "id:%d\n", id);
	for (i = 0; i < CRYPTO_PARAM_ARRAY_SIZE(decParam->decrypt_size); i++) {
		s_print(S_DEBUG_DEBUG, "decrypt_size[%d]:0x%08x\n", i,
			decParam->decrypt_size[i]);
	}
	for (i = 0; i < CRYPTO_PARAM_ARRAY_SIZE(decParam->decrypt_offset);
	     i++) {
		s_print(S_DEBUG_DEBUG, "decrypt_offset[%d]:0x%08x\n", i,
			decParam->decrypt_offset[i]);
	}
	s_print(S_DEBUG_DEBUG, "decrypt_key:0x");
	crypto_hexdump(decParam->decrypt_key, sizeof(decParam->decrypt_key));
	for (i = 0; i < CRYPTO_PARAM_ARRAY_SIZE(decParam->decrypt_iv); i++) {
		s_print(S_DEBUG_DEBUG, "decrypt_iv[%d]:0x", i);
		crypto_hexdump(decParam->decrypt_iv[i],
			       sizeof(decParam->decrypt_iv[0]));
	}
	for (i = 0; i < sizeof(decParam->decrypt_icv); i++) {
		s_print(S_DEBUG_DEBUG, "decrypt_icv[%d]:0x%02x\n", i,
			decParam->decrypt_icv[i]);
	}

	ioctl_param.id = id;
	ioctl_param.dec = decParam;
	if (do_ioctl(CRYPTO_IOCTL_SET_DEC_PARAM, &ioctl_param) != 0) {
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	if (ioctl_param.ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param.ret);
	} else {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
	}
	return ioctl_param.ret;
}

E_CRYPTO_ERROR cryptoRam_setAuthParam(int id,
				      struct cryptoRam_authParam *authParam)
{
	struct crypto_ioctl_auth_param ioctl_param = { 0 };
	int i;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	if (authParam == NULL) {
		s_print(S_DEBUG_ERROR, "authParam is NULL.\n");
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	/* Outputs input parameters */
	s_print(S_DEBUG_DEBUG, "id:%d\n", id);
	for (i = 0; i < CRYPTO_PARAM_ARRAY_SIZE(authParam->auth_size); i++) {
		s_print(S_DEBUG_DEBUG, "auth_size[%d]:0x%08x\n", i,
			authParam->auth_size[i]);
	}
	for (i = 0; i < CRYPTO_PARAM_ARRAY_SIZE(authParam->auth_offset); i++) {
		s_print(S_DEBUG_DEBUG, "auth_offset[%d]:0x%08x\n", i,
			authParam->auth_offset[i]);
	}
	s_print(S_DEBUG_DEBUG, "auth_key:0x");
	crypto_hexdump(authParam->auth_key, sizeof(authParam->auth_key));
	s_print(S_DEBUG_DEBUG, "hash_algo:%d\n", authParam->hash_algo);
	for (i = 0; i < CRYPTO_PARAM_ARRAY_SIZE(authParam->hash_offset); i++) {
		s_print(S_DEBUG_DEBUG, "hash_offset[%d]:0x%08x\n", i,
			authParam->hash_offset[i]);
	}

	ioctl_param.id = id;
	ioctl_param.auth = authParam;
	if (do_ioctl(CRYPTO_IOCTL_SET_AUTH_PARAM, &ioctl_param) != 0) {
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	if (ioctl_param.ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param.ret);
	} else {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
	}
	return ioctl_param.ret;
}

static void *thread_ioctl_wait_completion(void *arg)
{
	struct thread_data *th_priv = (struct thread_data *)arg;
	struct crypto_ioctl_wait_param *ioctl_param = &th_priv->ioctl_param;

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

#if !defined(CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS)
	if (pthread_detach(pthread_self()) != 0) {
		/* The thread ID is valid, and the thread is not already detached; */
		/* therefore, no error will occur. */
		s_print(S_DEBUG_ERROR, "pthread_detach failed. Ignored.\n");
	}
#endif /* !CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS */

	if (do_ioctl(CRYPTO_IOCTL_WAIT_COMPLETION, ioctl_param) != 0) {
		ioctl_param->ret = E_CRYPTO_ERROR_UNKNOWN;
	}
	if (ioctl_param->ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param->ret);
	} else {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
	}
	th_priv->callback(ioctl_param->id, ioctl_param->ret);
	free(th_priv);

	return (void *)NULL;
}

E_CRYPTO_ERROR cryptoRam_execute(int id, struct cryptoRam_exeParam *exeParam)
{
	struct crypto_ioctl_exe_param ioctl_param = { 0 };
	struct thread_data *th_priv = NULL;
	pthread_t pth;
#ifdef CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS
	pid_t   pid;
#endif /* CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS */

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	if ((exeParam == NULL) || (exeParam->callback == NULL)) {
		s_print(S_DEBUG_ERROR, "exeParam or callback is NULL.\n");
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	/* Outputs input parameters */
	s_print(S_DEBUG_DEBUG, "id:%d\n", id);
	s_print(S_DEBUG_DEBUG, "timeout:%u\n", exeParam->timeout);

	ioctl_param.timeout = exeParam->timeout;
	ioctl_param.id = id;
	if (do_ioctl(CRYPTO_IOCTL_EXECUTE, &ioctl_param) != 0) {
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	if (ioctl_param.ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param.ret);
		return ioctl_param.ret;
	}

#ifdef CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS
	pid = fork();
	if (pid == -1) {
		s_print(S_DEBUG_ERROR, "%s fork failed.\n", __func__);
		return E_CRYPTO_ERROR_UNKNOWN;
	}
	if (pid != 0) {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
		return E_CRYPTO_ERROR_OK;
	}
#endif /* CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS */

	/* create thread */
	th_priv = malloc(sizeof(struct thread_data));
	if (th_priv == NULL) {
		s_print(S_DEBUG_ERROR, "malloc failed.\n");
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	th_priv->callback = exeParam->callback;
	th_priv->ioctl_param.id = id;
	if (pthread_create(&pth, NULL, thread_ioctl_wait_completion,
			   (void *)th_priv) != 0) {
		s_print(S_DEBUG_ERROR, "pthread_create failed.\n");
		free(th_priv);
		return E_CRYPTO_ERROR_UNKNOWN;
	}

#ifdef CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS
	pthread_join(pth, NULL);
#else /* CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS */
	s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
#endif /* CRYPTO_CONFIG_SEPARATE_WAIT_PROCESS */
	return E_CRYPTO_ERROR_OK;
}

E_CRYPTO_ERROR cryptoRam_cancel(int id)
{
	struct crypto_ioctl_cancel_param ioctl_param = { 0 };

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	/* Outputs input parameters */
	s_print(S_DEBUG_DEBUG, "id:%d\n", id);

	ioctl_param.id = id;
	if (do_ioctl(CRYPTO_IOCTL_CANCEL, &ioctl_param) != 0) {
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	if (ioctl_param.ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param.ret);
	} else {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
	}
	return ioctl_param.ret;
}

E_CRYPTO_ERROR cryptoRam_releaseDrv(void)
{
	struct crypto_ioctl_release_param ioctl_param = { 0 };

	s_print(S_DEBUG_DEBUG, "%s\n", __func__);

	if (do_ioctl(CRYPTO_IOCTL_RELEASE_DRV, &ioctl_param) != 0) {
		return E_CRYPTO_ERROR_UNKNOWN;
	}

	if (ioctl_param.ret != E_CRYPTO_ERROR_OK) {
		s_print(S_DEBUG_ERROR, "%s failed. ret:%d\n", __func__,
			ioctl_param.ret);
	} else {
		s_print(S_DEBUG_DEBUG, "%s success.\n", __func__);
	}
	return ioctl_param.ret;
}
