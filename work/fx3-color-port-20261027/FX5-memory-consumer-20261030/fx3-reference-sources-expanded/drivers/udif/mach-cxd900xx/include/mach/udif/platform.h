/*
 * mach-cxd900xx/include/mach/udif/platform.h
 *
 *
 * Copyright 2015 Sony Corporation
 * Copyright 2018 Sony Imaging Products & Solutions Inc
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
#ifndef __MACH_UDIF_PLATFORM_H__
#define __MACH_UDIF_PLATFORM_H__

/* DEVICE ID */
typedef enum {
	UDIF_ID_HWTIMER = 0,
	UDIF_ID_GPIO,
	UDIF_ID_LDEC,
	UDIF_ID_MMC,
	UDIF_ID_EMMC0,
	UDIF_ID_SIRCS,
	UDIF_ID_MS,
	UDIF_ID_SIO,
	UDIF_ID_DMA330,
	UDIF_ID_SATA,
	UDIF_ID_CMMC,
	UDIF_ID_FUSB_OTG,
	UDIF_ID_WDT,
	UDIF_ID_PCIE,
	UDIF_ID_DDR,
	UDIF_ID_NUM
} UDIF_ID;

#if defined(CONFIG_ARCH_CXD900XX_QEMU) || defined(CONFIG_ARCH_CXD900XX_FVP)
#define UDIF_NR_HWTIMER	0
#elif defined(CONFIG_ARCH_CXD900XX_FPGA_V1_5)
#define UDIF_NR_HWTIMER	2
#else
#define UDIF_NR_HWTIMER	4
#endif
enum {
	UDIF_WDT_REG = 0,
	UDIF_WDT_MISC,
	UDIF_NR_WDT
};
#define UDIF_NR_GPIO	19U
# define UDIF_CH_MASK_GPIO 0x00063dff /* CH 0..8,10..13,17..18 */
#define UDIF_NR_LDEC	1U
#define UDIF_NR_MMC	3
#define UDIF_NR_MS	1
#define UDIF_NR_SIO	3
#define UDIF_NR_EMMC0	1
#define UDIF_NR_DMA330_CTRL 2
#define UDIF_NR_DMA330_CH   8
#define UDIF_NR_DMA330  (UDIF_NR_DMA330_CTRL * (UDIF_NR_DMA330_CH + 1))
#define UDIF_NR_SATA	0
enum {
	UDIF_CMMC_CH_REG = 0,
	UDIF_CMMC_CH_INBUF,
	UDIF_NR_CMMC
};
#define UDIF_NR_FUSB	1
#define UDIF_NR_PCIE	5
#define UDIF_NR_DDR	4

#ifdef __KERNEL__
#include <linux/udif/device.h>

extern UDIF_DEVICE udif_devices[UDIF_ID_NUM];

#define udif_get_device(id)	((id) < UDIF_ID_NUM ? &udif_devices[(id)]: NULL)
#define udif_dev_id(dev)	((dev) ? (UDIF_ID)((dev) - udif_devices): -1)

#define	UDIF_ID(id, msk) \
	{ .dev = &udif_devices[(id)], .ch_mask = msk }
#endif /* __KERNEL__ */

#endif /* __MACH_UDIF_PLATFORM_H__ */
