/**
 * Copyright (c) 2018-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <linux/dma-mapping.h>

#include "pfdep.h"
#include "netsec_config.h"

pfdep_debug_level_t pfdep_debug_level = PFDEP_DEBUG_LEVEL_FATAL;

pfdep_err_t pfdep_dma_malloc(pfdep_dev_handle_t dev_handle, pfdep_uint32 len,
			     void **addr_p, pfdep_phys_addr_t *phys_addr_p)
{
	(void)dev_handle; /* Suppress compiler warning */

	*addr_p = dma_alloc_coherent(dev_handle, (size_t)len, phys_addr_p,
				     GFP_KERNEL);

	if (!*addr_p)
		return PFDEP_ERR_ALLOC;

	return PFDEP_ERR_OK;
}

void pfdep_dma_free(pfdep_dev_handle_t dev_handle, pfdep_uint32 len, void *addr,
		    pfdep_phys_addr_t phys_addr)
{
	(void)dev_handle; /* Suppress compiler warning */

	dma_free_coherent(dev_handle, (size_t)len, addr, phys_addr);
}

