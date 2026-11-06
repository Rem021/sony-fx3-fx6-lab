/**
 * Copyright 2022 Sony Corporation
 * Copyright (c) 2018-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_RAM_PRINT_H
#define CRYPTO_RAM_PRINT_H

#include "pfdep.h"

#define NETSEC_MSG_ERR(x, y...) \
	pfdep_print(PFDEP_DEBUG_LEVEL_FATAL, "[E] %s: " x "\n", __func__, ##y)

#define NETSEC_MSG_INFO(x, y...) \
	pfdep_print(PFDEP_DEBUG_LEVEL_NOTICE, "[I] %s: " x "\n", __func__, ##y)

#define NETSEC_MSG_DEBUG(x, y...) \
	pfdep_print(PFDEP_DEBUG_LEVEL_DEBUG, "[D] %s: " x "\n", __func__, ##y)

#define CRYPTO_RAM_HEXDUMP(buf, len)                                       \
	print_hex_dump(KERN_CONT, "", DUMP_PREFIX_OFFSET, 16, 1, buf, len, \
		       false)

#endif /* CRYPTO_RAM_PRINT_H */
