/**
 * Copyright (c) 2018-2022 Socionext Inc.
 * All rights reserved.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as published
 * by the Free Software Foundation.
 */

#ifndef PFDEP_H
#define PFDEP_H

#include <linux/kernel.h>
#include <linux/device.h>
#include <linux/spinlock.h>
#include <linux/slab.h>
#include <linux/string.h>
#include <linux/interrupt.h>
#include <linux/dma-mapping.h>
#include <linux/delay.h>

typedef char pfdep_int8;
typedef unsigned char pfdep_uint8;
typedef short pfdep_int16;
typedef unsigned short pfdep_uint16;
typedef int pfdep_int32;
typedef unsigned int pfdep_uint32;
typedef long long pfdep_int64;
typedef unsigned long long pfdep_uint64;
typedef int pfdep_bool;
typedef char pfdep_char;

#define PFDEP_TRUE ((pfdep_bool)1)
#define PFDEP_FALSE ((pfdep_bool)0)

typedef enum pfdep_err_e {
	PFDEP_ERR_OK = 0,
	PFDEP_ERR_PARAM,
	PFDEP_ERR_ALLOC,
	PFDEP_ERR_INTERRUPT
} pfdep_err_t;

typedef struct device *pfdep_dev_handle_t;
typedef void *pfdep_pkt_handle_t;
typedef dma_addr_t pfdep_phys_addr_t;
typedef void (*pfdep_timer_func_t)(void *);
typedef struct timer_list *pfdep_timer_handle_t;
typedef void *pfdep_gpio_handle_t;


#if __SIZEOF_POINTER__ == 4
typedef unsigned int pfdep_cpu_addr_t;
#elif __SIZEOF_POINTER__ == 8
typedef unsigned long long pfdep_cpu_addr_t;
#else /*  __SIZEOF_POINTER__ == unknown */
#error "Unsupported __SIZEOF_POINTER__"
#endif /* __SIZEOF_POINTER__ == 4 */

typedef spinlock_t pfdep_hard_lock_t;
typedef spinlock_t pfdep_soft_lock_t;

typedef unsigned long pfdep_hard_lock_ctx_t;

typedef int pfdep_soft_lock_ctx_t;

typedef unsigned int pfdep_debug_level_t;

#define PFDEP_DEBUG_LEVEL_FATAL ((pfdep_debug_level_t)1)
#define PFDEP_DEBUG_LEVEL_WARNING ((pfdep_debug_level_t)2)
#define PFDEP_DEBUG_LEVEL_NOTICE ((pfdep_debug_level_t)3)
#define PFDEP_DEBUG_LEVEL_DEBUG ((pfdep_debug_level_t)4)
#define PFDEP_DEBUG_LEVEL_DEBUG_DETAILED ((pfdep_debug_level_t)5)
#define PFDEP_DEBUG_LEVEL_DEBUG_MORE_DETAILED ((pfdep_debug_level_t)6)


extern pfdep_debug_level_t pfdep_debug_level;

static __inline pfdep_uint32 pfdep_iomem_read(void *addr)
{
	return readl_relaxed(addr);
}

static __inline void pfdep_iomem_write(void *addr, pfdep_uint32 val)
{
	writel_relaxed(val, addr);
}

#define pfdep_read_mem_barrier() rmb()
#define pfdep_write_mem_barrier() wmb()
#define pfdep_mem_barrier() mb()

static __inline void *pfdep_malloc(pfdep_uint32 len)
{
	return kmalloc((size_t)len, GFP_NOWAIT);
}

static __inline void pfdep_free(void *addr)
{
	kfree(addr);
}

pfdep_err_t pfdep_dma_malloc(pfdep_dev_handle_t dev_handle, pfdep_uint32 len,
			     void **addr_p, pfdep_phys_addr_t *phys_addr_p);

void pfdep_dma_free(pfdep_dev_handle_t dev_handle, pfdep_uint32 len, void *addr,
		    pfdep_phys_addr_t phys_addr);

pfdep_err_t pfdep_alloc_pkt_buf(pfdep_dev_handle_t dev_handle, pfdep_uint16 len,
				void **addr_p, pfdep_phys_addr_t *phys_addr_p,
				pfdep_pkt_handle_t *pkt_handle_p);

void pfdep_free_pkt_buf(pfdep_dev_handle_t dev_handle, pfdep_uint16 len,
			void *addr, pfdep_phys_addr_t phys_addr,
			pfdep_bool last_flag, pfdep_pkt_handle_t pkt_handle);

static __inline pfdep_err_t pfdep_init_hard_lock(pfdep_hard_lock_t *hard_lock_p)
{
	spin_lock_init(hard_lock_p);

	return PFDEP_ERR_OK;
}

static __inline void pfdep_uninit_hard_lock(pfdep_hard_lock_t *hard_lock_p)
{
	return;
}

static __inline pfdep_err_t
pfdep_acquire_hard_lock(pfdep_hard_lock_t *hard_lock_p,
			pfdep_hard_lock_ctx_t *ctx_p)
{
	spin_lock_irqsave(hard_lock_p, *ctx_p);

	return PFDEP_ERR_OK;
}

static __inline void pfdep_release_hard_lock(pfdep_hard_lock_t *hard_lock_p,
					     pfdep_hard_lock_ctx_t *ctx_p)
{
	spin_unlock_irqrestore(hard_lock_p, *ctx_p);
}

static __inline pfdep_err_t pfdep_init_soft_lock(pfdep_soft_lock_t *soft_lock_p)
{
	spin_lock_init(soft_lock_p);

	return PFDEP_ERR_OK;
}

static __inline void pfdep_uninit_soft_lock(pfdep_soft_lock_t *soft_lock_p)
{
	return;
}

static __inline pfdep_err_t
pfdep_acquire_soft_lock(pfdep_soft_lock_t *soft_lock_p,
			pfdep_soft_lock_ctx_t *ctx_p)
{
	if (in_softirq()) {
		*ctx_p = 1; /* Mark that bh is already disabled. */
		spin_lock(soft_lock_p);
	} else {
		*ctx_p = 0;
		spin_lock_bh(soft_lock_p);
	}

	return PFDEP_ERR_OK;
}

static __inline void pfdep_release_soft_lock(pfdep_soft_lock_t *soft_lock_p,
					     pfdep_soft_lock_ctx_t *ctx_p)
{
	if (*ctx_p == 1) {
		spin_unlock(soft_lock_p);
	} else { /* *ctx_p == 0 */
		spin_unlock_bh(soft_lock_p);
	}
}

#define pfdep_l2h_32(val_le) le32_to_cpu(val_le)
#define pfdep_h2l_32(val) cpu_to_le32(val)
#define pfdep_l2h_16(val_le) le16_to_cpu(val_le)
#define pfdep_h2l_16(val) cpu_to_le16(val)
#define pfdep_b2h_32(val_be) be32_to_cpu(val_be)
#define pfdep_h2b_32(val) cpu_to_be32(val)
#define pfdep_b2h_16(val_be) be16_to_cpu(val_be)
#define pfdep_h2b_16(val) cpu_to_be16(val)

static __inline void pfdep_memcpy(void *dst_p, const void *src_p,
				  pfdep_uint32 len)
{
	memcpy(dst_p, src_p, (size_t)len);
}

static __inline void pfdep_memset(void *dst_p, pfdep_uint8 c, pfdep_uint32 len)
{
	memset(dst_p, c, (size_t)len);
}

static __inline pfdep_err_t pfdep_msleep(pfdep_uint32 wait_ms)
{
	msleep((unsigned int)wait_ms);

	return PFDEP_ERR_OK;
}

pfdep_err_t pfdep_register_timer(pfdep_timer_func_t func, const void *data,
				 pfdep_uint32 timer_ms,
				 pfdep_timer_handle_t *timer_handle_p);

pfdep_err_t pfdep_unregister_timer(pfdep_timer_handle_t timer_handle);

#define pfdep_print(level, ...)                                                \
	do {                                                                   \
		if (level <= pfdep_debug_level) {                              \
			switch (level) {                                       \
			case PFDEP_DEBUG_LEVEL_FATAL:                          \
				pr_err(__VA_ARGS__);                           \
				break;                                         \
			case PFDEP_DEBUG_LEVEL_WARNING:                        \
				pr_warn(__VA_ARGS__);                          \
				break;                                         \
			case PFDEP_DEBUG_LEVEL_NOTICE:                         \
				pr_notice(__VA_ARGS__);                        \
				break;                                         \
			case PFDEP_DEBUG_LEVEL_DEBUG:                          \
				pr_info(__VA_ARGS__);                          \
				break;                                         \
			default:                                               \
				pr_debug(__VA_ARGS__);                         \
			}                                                      \
		}                                                              \
	} while (0)

static __inline pfdep_debug_level_t pfdep_get_debug_level(void)
{
	return pfdep_debug_level;
}

static __inline void pfdep_set_debug_level(pfdep_debug_level_t level)
{
	pfdep_debug_level = level;
}

#ifdef CONFIG_ARCH_CXD90XXX_FPGA
#define pfdep_assert(cond) BUG_ON(!(cond))
#else /* CONFIG_ARCH_CXD90XXX_FPGA */
#define pfdep_assert(cond) WARN_ON_ONCE(!(cond))
#endif /* CONFIG_ARCH_CXD90XXX_FPGA */


#endif /* PFDEP_H */
