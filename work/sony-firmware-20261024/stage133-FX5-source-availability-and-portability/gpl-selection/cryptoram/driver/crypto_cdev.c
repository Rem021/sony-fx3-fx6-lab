/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#include <linux/device.h>
#include "crypto_config.h"
#include "crypto_cdev.h"
#include "sdebug.h"

#define DEV_NAME CRYPTO_CONFIG_DEV_NAME

struct cdev_handle *cdev_handle_create(struct device *dev)
{
	struct cdev_handle *handle;

	handle = devm_kzalloc(dev, sizeof(struct cdev_handle), GFP_KERNEL);
	if (!handle) {
		s_print(S_DEBUG_ERROR, "Failed to allocate cdev_handle\n");
		return ERR_PTR(-ENOMEM);
	}

	return handle;
}

int cdev_register(struct cdev_handle *handle, struct file_operations *fops)
{
	int ret;
	int minor = 0;
	dev_t next;

	ret = alloc_chrdev_region(&handle->devt, MINOR_BASE, MINOR_NUM,
				  DEV_NAME);
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "alloc_chrdev_region failed\n");
		goto alloc_chrdev_region_err;
	}

	cdev_init(&handle->cdev, fops);
	handle->cdev.owner = fops->owner;

	ret = cdev_add(&handle->cdev, handle->devt, MINOR_NUM);
	if (ret != 0) {
		s_print(S_DEBUG_ERROR, "cdev_add failed\n");
		goto cdev_add_err;
	}

	/* /sys/class/DEV_NAME */
	handle->class = class_create(handle->cdev.owner, DEV_NAME);
	if (IS_ERR(handle->class)) {
		s_print(S_DEBUG_ERROR, "class_create failed\n");
		ret = PTR_ERR(handle->class);
		goto class_create_err;
	}

	for (minor = MINOR_BASE; minor < MINOR_BASE + MINOR_NUM; minor++) {
		next = MKDEV(MAJOR(handle->devt), minor);
		device_create(handle->class, NULL, next, NULL, DEV_NAME "%d",
			      minor);
	}

	return 0;

class_create_err:
	cdev_del(&handle->cdev);

cdev_add_err:
	unregister_chrdev_region(handle->devt, MINOR_NUM);

alloc_chrdev_region_err:

	return ret;
}

void cdev_unregister(struct cdev_handle *handle)
{
	int minor = 0;
	dev_t next;

	for (minor = MINOR_BASE; minor < MINOR_BASE + MINOR_NUM; minor++) {
		next = MKDEV(MAJOR(handle->devt), minor);
		device_destroy(handle->class, next);
	}

	class_destroy(handle->class);
	cdev_del(&handle->cdev);
	unregister_chrdev_region(handle->devt, MINOR_NUM);
}
