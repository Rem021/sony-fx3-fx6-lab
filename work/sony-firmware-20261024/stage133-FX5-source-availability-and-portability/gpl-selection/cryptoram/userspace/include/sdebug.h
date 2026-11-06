/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef __SDEBUG_H__
#define __SDEBUG_H__

#ifdef __KERNEL__
#include <linux/printk.h>
#endif /* __KERNEL__ */

enum log_level_e {
	S_DEBUG_ERROR = 1,
	S_DEBUG_WARNING,
	S_DEBUG_INFO,
	S_DEBUG_DEBUG,
};

extern enum log_level_e log_level;

#ifdef __KERNEL__
#define s_print(level, ...)                                \
	do {                                               \
		if (level <= log_level) {                  \
			switch (level) {                   \
			case S_DEBUG_ERROR:                \
				pr_err("[E]" __VA_ARGS__); \
				break;                     \
			case S_DEBUG_WARNING:              \
				pr_err("[W]" __VA_ARGS__); \
				break;                     \
			case S_DEBUG_INFO:                 \
				pr_err("[I]" __VA_ARGS__); \
				break;                     \
			case S_DEBUG_DEBUG:                \
				pr_err("[D]" __VA_ARGS__); \
				break;                     \
			default:                           \
				pr_err(__VA_ARGS__);       \
				break;                     \
			}                                  \
		}                                          \
	} while (0)

#else
#define s_print(level, ...)                  \
	do {                                 \
		if (level <= log_level) {    \
			printf(__VA_ARGS__); \
		}                            \
	} while (0)
#endif /* __KERNEL__ */

#endif /* __SDEBUG_H__ */
