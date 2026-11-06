/*
 * dma32.h
 *
 * 32bit DMA address converter
 *
 * Copyright 2022 Sony Corporation
 *
 */
#ifndef __MACH_CXD90XXX_INCLUDE_MACH_DMA32_H
#define __MACH_CXD90XXX_INCLUDE_MACH_DMA32_H

/* DMAC address map */
#define DMA32_P64_DDR_BASE	0x200000000UL
#define DMA32_P64_DDR_END	0x300000000UL
#define DMA32_P64(x)		(0x200000000UL|(x))

#define PHYS32_ERR		(~0U)
#define PHYS64_ERR		(0UL)

static inline uint32_t __arch_p64_to_p32(uint64_t p64)
{
	if (DMA32_P64_DDR_BASE <= p64 && p64 < DMA32_P64_DDR_END)
		return (uint32_t)p64;
	return PHYS32_ERR;
}

static inline uint64_t __arch_p32_to_p64(uint32_t p32)
{
	return DMA32_P64(p32);
}

#endif /* __MACH_CXD90XXX_INCLUDE_MACH_DMA32_H */
