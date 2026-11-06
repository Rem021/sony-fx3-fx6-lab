# SPDX-License-Identifier:     GPL-2.0
# Copyright 2022 Sony Corporation, SOCIONEXT INC.

ARCH?=arm64

obj-m += ldec.o
ldec-objs := ldec_drv.o

CROSS_COMPILE=aarch64-linux-gnu-
PWD ?= $(shell pwd)

#=================================================

# default : time out function is enable
ifneq ($(timeout),disable)
FLGS += KCFLAGS+=-DLDEC_TIMEOUT_FLAG
endif

# default : debug print is enable. level=1
ifneq ($(debug_print),disable)
FLGS += KCFLAGS+=-DDEBUG_PRINT

# set print level
# 1:LDEC_DEBUG_ERROR/TIME 2: Up to LDEC_DEBUG_WARNING 3: Up to LDEC_DEBUG_DEBUG 4: Up to LDEC_DEBUG＿INFO

ifeq ($(print_level),1)
FLGS += KCFLAGS+=-DLDEC_PRINT_LEVEL=1
endif

ifeq ($(print_level),2)
FLGS += KCFLAGS+=-DLDEC_PRINT_LEVEL=2
endif

ifeq ($(print_level),3)
FLGS += KCFLAGS+=-DLDEC_PRINT_LEVEL=3
endif

ifeq ($(print_level),4)
FLGS += KCFLAGS+=-DLDEC_PRINT_LEVEL=4
endif

ifndef print_level
FLGS += KCFLAGS+=-DLDEC_PRINT_LEVEL=1
endif

endif	#end ($(debug_print),disable)

# default : Transfer method is dma
ifeq ($(transfer),cpu)
FLGS += KCFLAGS+=-DLDEC_TRANS_CPU
endif

#=================================================
# for test

ifeq ($(sleep_test),enable)
FLGS += KCFLAGS+=-DSLEEP70SEC4TEST
endif

#=================================================
# for performance measurement
#=================================================

ifeq ($(ioctl_times),enable)
FLGS += KCFLAGS+=-DLDEC_IOCTL_TIMES
endif
ifeq ($(irq_times),enable)
FLGS += KCFLAGS+=-DLDEC_IRQ_TIMES
endif
ifeq ($(irq_times_detail),enable)
FLGS += KCFLAGS+=-DLDEC_IRQ_TIMES_DETAIL
endif
ifeq ($(lock_times),enable)
FLGS += KCFLAGS+=-DLDEC_LOCK_TIMES
endif

all:
	make -C $(KDIR) $(FLGS) ARCH=$(ARCH) CROSS_COMPILE=$(CROSS_COMPILE) M=$(PWD) modules

install:

clean:
	@rm -rf *.o *.ko .*.cmd *.mod.c *.order *.symvers .tmp_versions *~ *.mod *.mod.gcno *.gcno
