/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPT_EMMC_INIT_INTERNAL_H
#define CRYPT_EMMC_INIT_INTERNAL_H

#include "crypt_emmc_init_tee_core.h"

bool is_eary_init(void);
bool is_key_256bit(void);
uint32_t get_unit_size(void);
int crypt_emmc_init_hw_init(void);
struct crypt_emmc_init_teedev *crypt_emmc_init_get_teedev(void);

#endif /* CRYPT_EMMC_INIT_INTERNAL_H */
