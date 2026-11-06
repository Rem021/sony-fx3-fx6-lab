/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPTO_CDEV_H
#define CRYPTO_CDEV_H

#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/device/class.h>

#define MINOR_BASE 0
#define MINOR_NUM  1

struct cdev_handle {
	dev_t devt;
	struct cdev cdev;
	struct class *class;
};

struct cdev_handle *cdev_handle_create(struct device *dev);
int cdev_register(struct cdev_handle *handle, struct file_operations *fops);
void cdev_unregister(struct cdev_handle *handle);

#endif /* CRYPTO_CDEV_H */
