/**
 * Copyright 2022 Sony Corporation
 * Copyright (c) 2018-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include "crypto_ram_core.h"
#include "crypto_ram_algs.h"

/* Sets RAW SAID to use & updates the usage */
int crypto_ram_core_acquire_entry(struct crypto_ram_device *core, u8 *id)
{
	if (core->sa_raw_use >= core->said_num) {
		NETSEC_MSG_ERR("SADB full: %d", core->sa_raw_use);
		return -ENOMEM;
	}

	mutex_lock(&core->said_sem);
	*id = core->sa_raw_next;
	core->sa_raw_use++;

	if (++core->sa_raw_next == core->said_num)
		core->sa_raw_next = 0;
	mutex_unlock(&core->said_sem);

	return 0;
}

void crypto_ram_core_release_entry(struct crypto_ram_device *core, u8 *id)
{
	netsec_clr_sa_data(core->handle, *id);

	mutex_lock(&core->said_sem);
	*id = 0;
	if (core->sa_raw_use > 0)
		core->sa_raw_use--;
	mutex_unlock(&core->said_sem);
}

int crypto_ram_get_pair_alg(const struct crypto_ram_key_alg_pair pair[],
			    int len, u32 keybit, u8 *alg)
{
	int i;

	/* Those that have no restriction in key length are
	marked by the first member being .keybit = 0.
	This case, just give its .alg */
	if (pair[0].keybit == 0) {
		*alg = pair[0].alg;
		return 0;
	}

	for (i = 0; i < len; i++) {
		if (pair[i].keybit == keybit) {
			*alg = pair[i].alg;
			return 0;
		}
	}

	return -EINVAL;
}

int crypto_ram_core_configure_entry(struct crypto_ram_device *core, u8 id,
				    netsec_sa_data_t *sa)
{
	int netsec_err = netsec_set_sa_data(core->handle, id, sa);
	if (netsec_err != NETSEC_ERR_OK) {
		NETSEC_MSG_ERR("SADB setting failure: %d", netsec_err);
		return -ENODEV;
	}

	return 0;
}

int crypto_ram_core_set_driver_name(struct crypto_ram_device *core,
				    struct crypto_alg *alg)
{
	int pos;

	if ((strlen(alg->cra_name) + strlen(core->name) + 1) >
	    sizeof(alg->cra_driver_name)) {
		NETSEC_MSG_ERR(
			"Number of characters not allowed in cra_driver_name.%lu",
			(strlen(alg->cra_name) + strlen(core->name) + 1));
		return -EINVAL;
	}

	memset(alg->cra_driver_name, 0, sizeof(alg->cra_driver_name));
	memcpy(alg->cra_driver_name, alg->cra_name, strlen(alg->cra_name));

	pos = strlen(alg->cra_name);
	alg->cra_driver_name[pos++] = '-';

	memcpy(&alg->cra_driver_name[pos], core->name, strlen(core->name));

	NETSEC_MSG_DEBUG("cra_driver_name = %s", alg->cra_driver_name);
	return 0;
}
