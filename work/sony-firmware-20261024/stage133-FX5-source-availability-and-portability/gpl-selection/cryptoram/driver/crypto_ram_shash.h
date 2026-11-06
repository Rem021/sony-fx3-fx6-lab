/**
 * Copyright 2022 Sony Corporation
 * Copyright (c) 2021-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_RAM_SHASH_H
#define CRYPTO_RAM_SHASH_H

#include "crypto_ram_core.h"

int crypto_ram_register_shashes(struct crypto_ram_device *core);
void crypto_ram_unregister_shashes(struct crypto_ram_device *core);
int crypto_ram_shash_complete(struct crypto_ram_calcinfo *info);

#endif /* CRYPTO_RAM_SHASH_H */
