/*
 * mach-cxd900xx/include/mach/irqs.h
 *
 * IRQ definitions
 *
 * Copyright 2018 Sony Corporation
 *
 * This code is based on include/asm-arm/arch-realview/irqs.h.
 */
/*
 *  linux/include/asm-arm/arch-realview/irqs.h
 *
 *  Copyright (C) 2003 ARM Limited
 *  Copyright (C) 2000 Deep Blue Solutions Ltd.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
 */

#ifndef __MACH_CXD900X0_IRQS_H
#define __MACH_CXD900X0_IRQS_H

/* SGI: 0-15
   PPI: 16-31
   SPI: 32-287 */
#define NR_GIC_SPI			256

#define IRQ_GIC_START			32

#define IRQ_REC_V			69
#define IRQ_REC_V_HS			70

#if defined(CONFIG_ARCH_CXD900XX_FPGA_V1_5)
#define IRQ_SDEMMC_BASE			139
#define IRQ_SDEMMC(x)			(IRQ_SDEMMC_BASE + (x)*2)
#define IRQ_EMMC0			IRQ_SDEMMC(0)
#define IRQ_EMMC1			IRQ_SDEMMC(1)
#define IRQ_SDIF(x)			IRQ_SDEMMC(2 + (x))

#define IRQ_DMA330_0_BASE		156
#define IRQ_DMA330_0(x)			(IRQ_DMA330_0_BASE + (x))
#define IRQ_DMA330_0_ABORT		IRQ_DMA330_0(32)
#define IRQ_DMA330_1_BASE		189
#define IRQ_DMA330_1(x)			(IRQ_DMA330_1_BASE + (x))
#define IRQ_DMA330_1_ABORT		IRQ_DMA330_1(32)

#define IRQ_GPIO_BASE			238
#define IRQ_GPIO(x)			(IRQ_GPIO_BASE + (x))
#define NR_GPIO_IRQ			24

#define IRQ_TIMER_BASE			267
#define IRQ_TIMER(x)			(IRQ_TIMER_BASE + (x))

#define IRQ_UART_BASE			285
#define IRQ_UART(x)			(IRQ_UART_BASE + (x))

#else

#define IRQ_DMA330_0_BASE		112
#define IRQ_DMA330_0(x)			(IRQ_DMA330_0_BASE + (x))
#define IRQ_DMA330_0_ABORT		IRQ_DMA330_0(32)
#define IRQ_DMA330_1_BASE		145
#define IRQ_DMA330_1(x)			(IRQ_DMA330_1_BASE + (x))
#define IRQ_DMA330_1_ABORT		IRQ_DMA330_1(32)

#define IRQ_GPIO_BASE			88
#define IRQ_GPIO(x)			(IRQ_GPIO_BASE + (x))
#define NR_GPIO_IRQ			24
#define IRQ_GPIO25			218
#define IRQ_GPIO24			219

#define IRQ_PMU_BASE			272
#define IRQ_PMU(x)			(IRQ_PMU_BASE + (x))
#define IRQ_PMU_CPU0			IRQ_PMU(0)
#define IRQ_PMU_CPU1			IRQ_PMU(1)
#define IRQ_PMU_CPU2			IRQ_PMU(2)
#define IRQ_PMU_CPU3			IRQ_PMU(3)

#define IRQ_UART_BASE			250
#define IRQ_UART(x)			(IRQ_UART_BASE + (x))

#define IRQ_WDOG_INT			230
#define IRQ_WDOG			231
#define IRQ_TIMER_BASE			232
#define IRQ_TIMER(x)			(IRQ_TIMER_BASE + (x))

#define IRQ_LDEC			224

#define IRQ_SIO_BASE			261
#define IRQ_SIO(x)			(IRQ_SIO_BASE + (x))

#define IRQ_MS0_BASE			220
#define IRQ_MS0				(IRQ_MS0_BASE + 0)

#define IRQ_SDEMMC_BASE			208
#define IRQ_SDEMMC(x)			(IRQ_SDEMMC_BASE + (x)*2)
#define IRQ_EMMC0			IRQ_SDEMMC(0)
#define IRQ_EMMC1			IRQ_SDEMMC(1)
#define IRQ_SDIF(x)			IRQ_SDEMMC(2 + (x))

#endif

#ifndef __ASSEMBLY__
extern void raise_irq(unsigned int cpu, unsigned int irq);
extern int gpiopin_to_irq(unsigned int port, unsigned int bit);
#endif /* !__ASSEMBLY__ */
#endif /* __MACH_CXD900X0_IRQS_H */
