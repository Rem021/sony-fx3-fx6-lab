/* SPDX-License-Identifier: GPL-2.0 WITH Linux-syscall-note */
/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */

enum {
	S_DEBUG_ERROR = 1,
	S_DEBUG_WARNING,
	S_DEBUG_DEBUG,
	S_DEBUG_INFO,
};

#define DEBUG_LEVEL S_DEBUG_ERROR

#ifndef DEBUG_PRINT
#define s_print(level, format, ...) do {} while (0)
#else
#include <linux/kernel.h>
#define s_print(level, format, ...) \
	if( level <= DEBUG_LEVEL ) \
		printk("[%s:%d:%d]" format, __func__, __LINE__, level, ##__VA_ARGS__)
#endif

