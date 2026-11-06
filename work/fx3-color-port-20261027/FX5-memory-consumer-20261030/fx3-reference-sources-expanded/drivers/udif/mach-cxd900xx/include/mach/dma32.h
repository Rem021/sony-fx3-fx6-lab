/*
 * dma32.h
 *
 * 32bit DMA address converter
 *
 * Copyright 2019 Sony Imaging Products & Solutions Inc
 *
 */
#ifndef __MACH_CXD900XX_INCLUDE_MACH_DMA32_H
#define __MACH_CXD900XX_INCLUDE_MACH_DMA32_H

/* DMAC address map */
#define DMA32_DDR_BASE		0x000000000U
#define DMA32_DDR_END		0x0FE000000U
#define DMA32_ESRAM_BASE	0x0FE000000U
#define DMA32_ESRAM_END		0x0FF000000U

#define DMA32_P64(x)		(0x400000000UL|(x))
#define DMA32_P64_DDR_BASE	DMA32_P64(DMA32_DDR_BASE)
#define DMA32_P64_DDR_END	DMA32_P64(DMA32_DDR_END)
#define DMA32_P64_ESRAM_BASE	DMA32_ESRAM_BASE
#define DMA32_P64_ESRAM_END	DMA32_ESRAM_END

#define PHYS32_ERR		(~0U)
#define PHYS64_ERR		(0UL)

static inline uint32_t __arch_p64_to_p32(uint64_t p64)
{
	if (DMA32_P64_DDR_BASE <= p64 && p64 < DMA32_P64_DDR_END)
		return (uint32_t)p64;
	else if (DMA32_P64_ESRAM_BASE <= p64 && p64 < DMA32_P64_ESRAM_END)
		return (uint32_t)p64;
	return PHYS32_ERR;
}

static inline uint64_t __arch_p32_to_p64(uint32_t p32)
{
	if (DMA32_DDR_BASE <= p32 && p32 < DMA32_DDR_END)
		return DMA32_P64(p32);
	else if (DMA32_ESRAM_BASE <= p32 && p32 < DMA32_ESRAM_END)
		return (uint64_t)p32;
	return PHYS64_ERR;
}

#endif /* __MACH_CXD900XX_INCLUDE_MACH_DMA32_H */
