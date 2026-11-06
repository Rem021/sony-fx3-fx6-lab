/*
 * mach-cxd900xx/include/mach/platform.h
 *
 * CXD90057 address map
 *
 * Copyright 2018,2019 Sony Imaging Products & Solutions Inc
 *
 *  This program is free software; you can redistribute  it and/or modify it
 *  under  the terms of  the GNU General  Public License as published by the
 *  Free Software Foundation;  version 2 of the  License.
 *
 *  THIS  SOFTWARE  IS PROVIDED   ``AS  IS'' AND   ANY  EXPRESS OR IMPLIED
 *  WARRANTIES,   INCLUDING, BUT NOT  LIMITED  TO, THE IMPLIED WARRANTIES OF
 *  MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.  IN
 *  NO  EVENT  SHALL   THE AUTHOR  BE    LIABLE FOR ANY   DIRECT, INDIRECT,
 *  INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
 *  NOT LIMITED   TO, PROCUREMENT OF  SUBSTITUTE GOODS  OR SERVICES; LOSS OF
 *  USE, DATA,  OR PROFITS; OR  BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
 *  ANY THEORY OF LIABILITY, WHETHER IN  CONTRACT, STRICT LIABILITY, OR TORT
 *  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF
 *  THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 *  You should have received a copy of the  GNU General Public License along
 *  with this program; if not, write  to the Free Software Foundation, Inc.,
 *  51 Franklin Street, Suite 500, Boston, MA 02110-1335, USA.
 *
 */
#ifndef __MACH_CXD900XX_PLATFORM_H
#define __MACH_CXD900XX_PLATFORM_H

#include <asm/memory.h>

#define IO_ADDRESS(x)	(CXD900XX_IO_VA|(x))
#ifdef __ASSEMBLY__
#define IO_ADDRESSP(x)	IO_ADDRESS(x)
#else
#define IO_ADDRESSP(x)	(volatile void __iomem __force *)IO_ADDRESS(x)
#endif

#if defined(CONFIG_ARCH_CXD900XX_QEMU)
#define DDR0_BASE               UL(0x040000000)
#define DDR0_SIZE               UL(0x080000000) /* 2GB */
#elif defined(CONFIG_ARCH_CXD900XX_FPGA)
# if defined(CONFIG_ARCH_CXD900XX_FPGA_SL)
#define DDR0_BASE		UL(0x400000000)
#define DDR0_SIZE		UL(0x080000000) /* 2GB */
# else
#define DDR0_BASE		UL(0x000000000)
#define DDR0_SIZE		UL(0x0C0000000) /* 3GB */
# endif
#else
#define DDR0_BASE		UL(0x400000000)
#define DDR0_SIZE		UL(0x200000000) /* 8GB */
#endif

/*---------------- I/O ----------------*/
#define CXD900XX_IO_BASE	UL(0xf0000000)
#define CXD900XX_IO_SIZE	0x10000000
#define CXD900XX_IO_VA		UL(0xfffffffff0000000)

#define CXD900XX_UART(x)	(UL(0xf1000000) + 0x1000*(x))

#define CXD900XX_TIMER_BASE(x)	(UL(0xf1042000) + 0x1000*(x))
#define VA_TIMER(x)		IO_ADDRESSP(CXD900XX_TIMER_BASE(x))
#define VA_WDT			VA_TIMER(16)

#define CXD900XX_GPIO(x)	(UL(0xf101d000) + 0x1000*(x))
#define PA_GPIO(ch,reg)		(CXD900XX_GPIO(ch) + GPIO_##reg)
#define VA_GPIO(ch)		IO_ADDRESSP(CXD900XX_GPIO(ch))
#define GPIO_INT		17
#define GPIO_SYS		18

#define CXD900XX_DDRC(x)	(UL(0xf105a000) + 0x1000*(x))
#define CXD900XX_DDRPHY(x)	(UL(0xf105e000) + 0x1000*(x))
#define VA_DDRC(x)		IO_ADDRESSP(CXD900XX_DDRC(x))
#define VA_DDRPHY(x)		IO_ADDRESSP(CXD900XX_DDRPHY(x))

#define CXD900XX_PCIEPHY0	UL(0xf11c0000)
#define CXD900XX_PCIEPHY1	UL(0xf1140000)
#define CXD900XX_PCIEPHY2	UL(0xf1180000)
#define CXD900XX_PCIEPHY3	UL(0xf1200000)
#define CXD900XX_PCIEPHY4	UL(0xf1100000)

#define CXD900XX_SCU		UL(0xf1388000)
#define CXD900XX_CLKEN(ch)	(CXD900XX_SCU + ((ch)<<4))
#define CXD900XX_PLL(ch)	(CXD900XX_SCU+0x100 + ((ch)<<2))
#define VA_PLL(ch)		IO_ADDRESSP(CXD900XX_PLL(ch))
#define CXD900XX_CLKSEL(ch)	(CXD900XX_SCU+0x200 + ((ch)<<4))
#define CXD900XX_RESET(ch)	(CXD900XX_SCU+0x300 + ((ch)<<4))
#define CXD900XX_OCTRL(ch,reg)	(CXD900XX_SCU + OCTRL_##reg + 0x10*(ch))
#define CXD900XX_WDT_MISC	(CXD900XX_SCU+0x3a0)
#define VA_WDT_MISC		IO_ADDRESSP(CXD900XX_WDT_MISC)

#define VA_GIC_DIST		IO_ADDRESSP(0xf13a1000)

/*---------------- eSRAM ----------------*/
#define CXD900XX_ESRAM_BASE	UL(0xfe000000)
#define CXD900XX_ESRAM_SIZE	SZ_16M

#endif /* __MACH_CXD900XX_PLATFORM_H */
