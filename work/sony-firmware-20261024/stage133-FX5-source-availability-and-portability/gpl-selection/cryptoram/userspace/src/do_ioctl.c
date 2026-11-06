/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <stdio.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <unistd.h>
#include "crypto_config.h"
#include "do_ioctl.h"
#include "sdebug.h"

#define CRYPTO_DEV_FILE CRYPTO_CONFIG_DEV_NAME "0"
#define DEV_FILE	"/dev/" CRYPTO_DEV_FILE

int do_ioctl(unsigned int cmd, void *data_p)
{
	int fd;
	int ret = 0;

	fd = open(DEV_FILE, O_RDWR);
	if (fd < 0) {
		s_print(S_DEBUG_ERROR, "do_ioctl open failed\n");
		return 1;
	}

	if (ioctl(fd, cmd, data_p) < 0) {
		s_print(S_DEBUG_ERROR, "do_ioctl ioctl failed\n");
		ret = 1;
	}

	if (close(fd) < 0) {
		s_print(S_DEBUG_ERROR, "do_ioctl close failed\n");
		ret = 1;
	}

	return ret;
}
