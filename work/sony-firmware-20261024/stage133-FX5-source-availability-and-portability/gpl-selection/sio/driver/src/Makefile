# SPDX-License-Identifier: GPL-2.0
# Copyright 2023 Sony Corporation, SOCIONEXT INC.
# Makefile for sio device drivers.
#

ARCH?=arm64

CROSS_COMPILE=aarch64-linux-gnu-

obj-m += sio.o
sio-objs := sio_lin.o

all:
	make -C $(KDIR) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) M=$(PWD) modules

install:

clean:
	@rm -rf *.o *.ko .*.cmd *.mod.c *.order *.symvers .tmp_versions *~ *.mod *.mod.gcno *.gcno
