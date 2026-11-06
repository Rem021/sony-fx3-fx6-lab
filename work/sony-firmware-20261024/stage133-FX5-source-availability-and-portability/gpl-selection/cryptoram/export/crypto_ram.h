/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_RAM_H
#define CRYPTO_RAM_H

#include "crypto_param.h"

E_CRYPTO_ERROR cryptoRam_init(struct cryptoRam_initParam *initParam, int *id);

E_CRYPTO_ERROR cryptoRam_exit(int id);

E_CRYPTO_ERROR
cryptoRam_setCryptoParam(int id, struct cryptoRam_cryptoParam *cryptoParam);

E_CRYPTO_ERROR cryptoRam_setEncParam(int id,
				     struct cryptoRam_encParam *encParam);

E_CRYPTO_ERROR cryptoRam_setDecParam(int id,
				     struct cryptoRam_decParam *decParam);

E_CRYPTO_ERROR cryptoRam_setAuthParam(int id,
				      struct cryptoRam_authParam *authParam);

E_CRYPTO_ERROR cryptoRam_execute(int id, struct cryptoRam_exeParam *exeParam);

E_CRYPTO_ERROR cryptoRam_cancel(int id);

E_CRYPTO_ERROR cryptoRam_releaseDrv(void);

#endif /* CRYPTO_RAM_H */
