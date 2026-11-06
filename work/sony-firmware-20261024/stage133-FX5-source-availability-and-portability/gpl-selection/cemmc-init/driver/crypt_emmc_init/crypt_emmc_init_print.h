/**
 * Copyright 2022 Sony Corporation, Socionext Inc.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef CRYPT_EMMC_INIT_PRINT_H
#define CRYPT_EMMC_INIT_PRINT_H

#include <linux/printk.h>
#include "crypt_emmc_init_config.h"

#ifdef CRYPT_EMMC_INIT_CONFIG_LOG_LV
#define CRYPT_EMMC_INIT_LOG_LV CRYPT_EMMC_INIT_CONFIG_LOG_LV
#else
#define CRYPT_EMMC_INIT_LOG_LV CRYPT_EMMC_INIT_LOG_LEVEL_NONE
#endif /* CRYPT_EMMC_INIT_CONFIG_LOG_LV */

#define CRYPT_EMMC_INIT_LOG_LEVEL_NONE	  (0)
#define CRYPT_EMMC_INIT_LOG_LEVEL_ERROR	  (1)
#define CRYPT_EMMC_INIT_LOG_LEVEL_WARNING (2)
#define CRYPT_EMMC_INIT_LOG_LEVEL_INFO	  (3)
#define CRYPT_EMMC_INIT_LOG_LEVEL_DEBUG	  (4)
#define CRYPT_EMMC_INIT_LOG_LEVEL_TRACE	  (5)

#if CRYPT_EMMC_INIT_LOG_LV >= CRYPT_EMMC_INIT_LOG_LEVEL_ERROR
#define crypt_emmc_pr_err(...) pr_err("[E]" __VA_ARGS__)
#else
#define crypt_emmc_pr_err(...)
#endif

#if CRYPT_EMMC_INIT_LOG_LV >= CRYPT_EMMC_INIT_LOG_LEVEL_WARNING
#define crypt_emmc_pr_warn(...) pr_err("[W]" __VA_ARGS__)
#else
#define crypt_emmc_pr_warn(...)
#endif

#if CRYPT_EMMC_INIT_LOG_LV >= CRYPT_EMMC_INIT_LOG_LEVEL_INFO
#define crypt_emmc_pr_info(...) pr_err("[I]" __VA_ARGS__)
#else
#define crypt_emmc_pr_info(...)
#endif

#if CRYPT_EMMC_INIT_LOG_LV >= CRYPT_EMMC_INIT_LOG_LEVEL_DEBUG
#define crypt_emmc_pr_debug(...) pr_err("[D]" __VA_ARGS__)
#else
#define crypt_emmc_pr_debug(...)
#endif

#if CRYPT_EMMC_INIT_LOG_LV >= CRYPT_EMMC_INIT_LOG_LEVEL_TRACE
#define crypt_emmc_pr_trace(...) pr_err("[T]" __VA_ARGS__)
#else
#define crypt_emmc_pr_trace(...)
#endif

#endif /* CRYPT_EMMC_INIT_PRINT_H */
