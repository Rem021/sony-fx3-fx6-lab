/* SPDX-License-Identifier: GPL-2.0 WITH Linux-syscall-note */
/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */
// for userspace
#ifndef __SIO_H__
#define __SIO_H__

#include "pbl_sio.h"

#define SIO_MASTER_TRANSFER		_IOWR('g', 0, int)
#define SIO_BAUD				_IOW('g', 1, int)
#define SIO_CTL_DISABLE_ICLK	_IOW('g', 2, int)
#define SIO_CTL_ICK128			_IOW('g', 3, int)
#define SIO_CTL_ICK64			_IOW('g', 4, int)
#define SIO_CTL_ICK32			_IOW('g', 5, int)
#define SIO_CTL_ICK16			_IOW('g', 6, int)
#define SIO_CTL_ENABLE_SCK		_IOW('g', 7, int)
#define SIO_CTL_EXT_CLK			_IOW('g', 8, int)
#define SIO_CTL_MSB_FIRST		_IOW('g', 9, int)
#define SIO_CTL_LSB_FIRST		_IOW('g', 10, int)
#define SIO_CTL_ENABLE_SCS		_IOW('g', 11, int)
#define SIO_CTL_CSSEL0			_IOW('g', 12, int)
#define SIO_CTL_CSSEL1			_IOW('g', 13, int)
#define SIO_CTL_CSSEL2			_IOW('g', 14, int)
#define SIO_CTL_INV_SCK			_IOW('g', 15, int)
#define SIO_CTL_ICK_DIS			_IOW('g', 16, int)
#define SIO_CTL_CSEN		    _IOW('g', 17, int)

#if DEBUG_TEST_SIO
 #define SIO_CTL_GET_DISABLE_ICLK	_IOW('g', 18, int)
 #define SIO_CTL_GET_ICK		_IOW('g', 19, int)
 #define SIO_CTL_GET_CSEL		_IOW('g', 20, int)
 #define SIO_CTL_GET_LMS		_IOW('g', 21, int)
 #define SIO_CTL_GET_CSOMOD		_IOW('g', 22, int)
 #define SIO_CTL_GET_CSSEL		_IOW('g', 23, int)
 #define SIO_CTL_GET_SIOPOL		_IOW('g', 24, int)
 #define SIO_CTL_GET_BRATE		_IOW('g', 25, int)
#endif

#endif /* __SIO_H__ */
