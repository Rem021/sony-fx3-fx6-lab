// SPDX-License-Identifier:     GPL-2.0
/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */
#include <linux/miscdevice.h>
#include <linux/device.h>
#include <linux/fs.h>
#include <linux/module.h>
#include <linux/platform_device.h>
#include <linux/seq_file.h>
#include <linux/slab.h>
#include <linux/of.h>
#include <linux/delay.h>
#include <linux/wait.h>
#include <linux/list.h>
#include <linux/irq.h>
#include <linux/interrupt.h>
#include <linux/clk.h>
#include <linux/reset.h>
#include <linux/spinlock.h>

#include "sio.h"
#define DEBUG_PRINT 1
#include "sdebug.h"

/* CLOE, ICLSIO Work Around
 *  SIOCS and OE are not cleared, even though CLOE and ICLSIO set
 */
#define D_WA_SIOCS_REG_CLEAR

#if DEBUG_TEST_SIO
void SIO_time_mesure_reset(void);
static void SIO_time_mesure_start(void);
static void SIO_time_mesure_stop(void);
void SIO_time_mesure_print(void);
#endif

#define D_DRIVERNAME "sio-driver"
#define D_DEVICENAME "cxd,sio"
#define D_CH_FREE	0
#define D_CH_PBL	1
#define D_CH_FOPS	2

#define D_XMIT_MODE_EC_IS	0x1000
#define D_XMIT_MODE_EC_ES	0x1001
#define D_XMIT_MODE_NR		0x1002
#define D_XMIT_MODE_FS		0x1003
#define D_XMIT_MODE_CS		0x1004

#define D_BUFSZ_MAX	0x100
#define D_REG_RANGE 0x54
#define D_REG16_MIN	0
#define D_REG16_MAX	0xffff
#define D_CH_ERR	NULL
#define D_CH_0		0
#define D_CH_1		1
#define D_CH_MAX	2

/* --- register --- */
#define D_REG_SIOCS		0x0
#define D_REG_SIOM		0x4
#define D_REG_SIOSA		0x8
#define D_REG_SION		0xc
#define D_REG_SIOEN		0x10
#define D_REG_SIOBGC0		0x14
#define D_REG_SIOBGC1		0x18
#define D_REG_SIOCKST0	0x1c
#define D_REG_SIOCKST1	0x20
#define D_REG_SIOCKSTEN	0x24
#define D_REG_SIOICK0		0x28
#define D_REG_SIOICK1		0x2c
#define D_REG_SIOICKEN	0x30
#define D_REG_SIOIDLY0	0x34
#define D_REG_SIOIDLY1	0x38
#define D_REG_SIOIDLYEN	0x3c
#define D_REG_SIOCSCNT	0x40
#define D_REG_SIOCSINT0	0x44
#define D_REG_SIOCSINT1	0x48
#define D_REG_SIOPOL		0x4c
#define D_REG_CSSEL		0x50
#define D_REG_DATABUF		0x100
/* SIOCS */
#define D_STATE_OE		BIT(25)
#define D_STATE_ST		BIT(29)
#define D_CSEL(x)		((x & 1) << 24)
#define D_OE(x)			((x & 1) << 25)
#define D_LMS(x)		((x & 1) << 26)
#define D_SOEN(x)		((x & 1) << 27)
#define D_SCKOE(x)		((x & 1) << 28)
#define D_SIOST(x)		((x & 1) << 29)
#define D_CLOE(x)		((x & 1) << 30)
#define D_ICLSIO(x)		((x & 1) << 31)
/* SIOM */
#define D_CSOMOD(x)		((x & 1) << 24)
#define D_RTMOD(x)		((x & 1) << 25)
#define D_ICK(x)		((x & 3) << 26)
#define D_TRM(x)		((x & 3) << 28)
#define D_IMOD(x)		((x & 1) << 30)
#define D_CSEN(x)		((x & 1) << 31)
/* SIOSA */
#define D_SIOSA(x)		((x & 0xff) << 24)
/* SION */
#define D_SION(x)		((x & 0xff) << 24)
/* SIOEN */
#define D_SIOEN(x)		((x & 1) << 24)
/* SIOBGC */
#define D_SIOBGC0(x)	((x & 0x00ff) << 24)
#define D_SIOBGC1(x)	((x & 0xff00) << 16)
/* SIOCKST */
#define D_CKST0(x)	((x & 0x00ff) << 24)
#define D_CKST1(x)	((x & 0xff00) << 16)
/* SIOCKSTEN */
#define D_CKSTEN(x)		((x & 1) << 24)
/* SIOICK */
#define D_ICK0(x)	((x & 0x00ff) << 24)
#define D_ICK1(x)	((x & 0xff00) << 16)
/* SIOICKEN */
#define D_ICKEN(x)		((x & 1) << 24)
/* SIOIDLY */
#define D_DLY0(x)	((x & 0x00ff) << 24)
#define D_DLY1(x)	((x & 0xff00) << 16)
/* SIOIDLYEN */
#define D_IDLYEN(x)		((x & 1) << 24)
/* SIOCSCNT */
#define D_CNT(x)	((x & 0xff) << 24)
/* SIOCSINT */
#define D_INT0(x)	((x & 0x00ff) << 24)
#define D_INT1(x)	((x & 0xff00) << 16)
/* SIOPOL */
#define D_SCKINV(x)		((x & 1) << 24)
/* CSSEL */
#define D_CSOSEL(x)		((x & 3) << 30)
/* --- register END --- */

#define D_BGC_MIN 1
#define D_DEVICENAME_LENGTH 16

#define D_IOCTL_CKST_VAL 0
#define D_IOCTL_CKSTEN_VAL 0
#define D_IOCTL_IDLYEN_VAL 1
#define D_IOCTL_IDLY_VAL 0x20
#define D_IOCTL_CSINT_VAL 0
#define D_IOCTL_RTMOD_VAL PBL_SIO_RTMOD_NORMAL

#ifdef D_WA_SIOCS_REG_CLEAR
#define D_APB_1CLK_NS 11 // APB 96MHz about 10.4ns
#endif
/* use this time in case of forced transfer cancellation, waiting time to reach byte boundary in transfer */
#define D_TRANS_CANCEL_US 1000

struct cxd_sio_driver {
	struct device *dev;
	struct miscdevice miscdev;
	struct reset_control *rst;
	struct clk *pclk;
	struct clk *ps;
	struct completion compl;
	struct mutex paramlock;
	struct mutex buflock;
	PBL_SIO_INFO info;
	PBL_SIO_START_INFO start_info;
	PBL_FACT irqfact;
	PBL_FUNC int_func;
	void __iomem *base;
	uint32_t pm_regs[D_REG_RANGE >> 2];
	uint32_t xmitmode;
	char devname[D_DEVICENAME_LENGTH];
	char is_used;
	char align_buf[D_BUFSZ_MAX];
	resource_size_t irq_no;
};

static struct cxd_sio_driver g_priv[D_CH_MAX];

/**
 * sio_get_private() - Get private data from device id.
 * @dev_id: device id.
 *
 * Convert from device id to device private data.
 *
 * Return: Pointer to device private data.
 */
static struct cxd_sio_driver *sio_get_private(uint32_t dev_id)
{
	if (dev_id == PBL_SIO_CH0)
		return &g_priv[D_CH_0];
	else if (dev_id == PBL_SIO_CM_CH0)
		return &g_priv[D_CH_1];

	return D_CH_ERR;
}



/**
 * sio_check_xmit_mode() - Get SIO transfer mode
 * @info: Pointer to PBL_SIO_INFO
 *
 * Get a transfer mode using info structure.
 * Transfer mode:
 *  External clock and Internal start
 *  External clock and External start
 *  Normal (Internal clock and Internal start)
 *  Fast (Internal clock and Internal start)
 *  Using CS (Internal clock and Internal start)
 *
 * Return: Transfer mode or error
 */
static int32_t sio_check_xmit_mode(const PBL_SIO_INFO *info)
{
	int32_t ret;

	ret = PBL_OK;

	if (info->csel == PBL_SIO_CSEL_EXTNL) {
		if (info->csomod == PBL_SIO_CSOMOD_ON){
			s_print(S_DEBUG_ERROR, "EXTCLK & CS CNTROL ON");
			ret = PBL_DATA_ERR;
		}
		else if (info->imod == PBL_SIO_IMOD_EN){
			s_print(S_DEBUG_ERROR, "EXTCLK & IMOD EN");
			ret = PBL_DATA_ERR;
		}
		else if (info->csen == PBL_SIO_CSEN_INTNL)
			ret = D_XMIT_MODE_EC_IS;/* external clock and start */
		else
			ret = D_XMIT_MODE_EC_ES;/* external clock, external start */
	} else if (info->csel == PBL_SIO_CSEL_INTNL) {
		if (info->csen == PBL_SIO_CSEN_EXTNL){
			s_print(S_DEBUG_ERROR, "INTCLK & CS TRIG");
			ret = PBL_DATA_ERR;
		}
		else if (info->csomod == PBL_SIO_CSOMOD_ON) {
			ret = D_XMIT_MODE_CS;/* CS mode */
		} else if (info->csomod == PBL_SIO_CSOMOD_OFF) {
			if (info->imod == PBL_SIO_IMOD_EN)
				ret = D_XMIT_MODE_NR;/* internal clock, internal start, normal */
			else if (info->imod == PBL_SIO_IMOD_DIS)
				ret = D_XMIT_MODE_FS;/* internal clock, internal start, Fast */
			else{
				s_print(S_DEBUG_ERROR, "IMOD error");
				ret = PBL_DATA_ERR;
			}
		} else {
			s_print(S_DEBUG_ERROR, "CSMOD error");
			ret = PBL_DATA_ERR;
		}
	} else {
		s_print(S_DEBUG_ERROR, "INTCLK/EXTCLK error");
		ret = PBL_DATA_ERR;
	}

	if (ret == PBL_DATA_ERR) {
		s_print(S_DEBUG_ERROR, "%s:%d\n", __func__, __LINE__);
		s_print(S_DEBUG_ERROR, "csel\t%d\n", info->csel);
		s_print(S_DEBUG_ERROR, "csen\t%d\n", info->csen);
		s_print(S_DEBUG_ERROR, "imod\t%d\n", info->imod);
		s_print(S_DEBUG_ERROR, "csomod\t%d\n", info->csomod);
	}
	return ret;
}


static int32_t sio_check_info_brate(const PBL_SIO_INFO *info)
{
	int32_t ret;
	int32_t val;

	ret = PBL_OK;

	val = info->brate;


	switch (val) {
	case PBL_SIO_BRATE_32K:
	case PBL_SIO_BRATE_64K:
	case PBL_SIO_BRATE_800K:
	case PBL_SIO_BRATE_1000K:
	case PBL_SIO_BRATE_1500K:
	case PBL_SIO_BRATE_2000K:
	case PBL_SIO_BRATE_3000K:
	case PBL_SIO_BRATE_4000K:
	case PBL_SIO_BRATE_8000K:
	case PBL_SIO_BRATE_12M:
	/* --- not support --- */
	case PBL_SIO_BRATE_2048:
	case PBL_SIO_BRATE_4096:
	case PBL_SIO_BRATE_8192:
	case PBL_SIO_BRATE_16384:
	case PBL_SIO_BRATE_128K:
	case PBL_SIO_BRATE_256K:
	case PBL_SIO_BRATE_512K:
	case PBL_SIO_BRATE_780K:
	case PBL_SIO_BRATE_975K:
	case PBL_SIO_BRATE_1250K:
	case PBL_SIO_BRATE_1264K:
	case PBL_SIO_BRATE_1750K:
	case PBL_SIO_BRATE_2250K:
	case PBL_SIO_BRATE_2500K:
	case PBL_SIO_BRATE_2750K:
	case PBL_SIO_BRATE_3250K:
	case PBL_SIO_BRATE_3300K:
	case PBL_SIO_BRATE_3500K:
	case PBL_SIO_BRATE_3750K:
	case PBL_SIO_BRATE_5500K:
	case PBL_SIO_BRATE_6500K:
	case PBL_SIO_BRATE_8250K:
	case PBL_SIO_BRATE_9750K:
		break;
	default:
		s_print(S_DEBUG_ERROR, "brate \t%d\n", (int)info->brate);
		ret = PBL_DATA_ERR;
		break;
	}


	return ret;
}


static int32_t sio_check_info_lms(const PBL_SIO_INFO *info)
{
	int32_t ret;
	int32_t val;

	ret = PBL_OK;
	val = info->lms;
	if ((val != PBL_SIO_LMS_LSB) && (val != PBL_SIO_LMS_MSB)) {
		s_print(S_DEBUG_ERROR, "lms \t%d\n", (int)info->lms);
		ret = PBL_DATA_ERR;
	}
	return ret;
}	


static int32_t sio_check_info_csel(const PBL_SIO_INFO *info)
{
	int32_t ret;
	int32_t val;

	ret = PBL_OK;

	val = info->csel;
	if ((val != PBL_SIO_CSEL_INTNL) && (val != PBL_SIO_CSEL_EXTNL)) {
		s_print(S_DEBUG_ERROR, "csel \t%d\n", (int)info->csel);
		ret = PBL_DATA_ERR;
	}
	return ret;	
}

static int32_t sio_check_info_imod(const PBL_SIO_INFO *info)
{
	int32_t ret;
	int32_t val;

	ret = PBL_OK;

	val = info->imod;
	if ((val != PBL_SIO_IMOD_EN) && (val != PBL_SIO_IMOD_DIS)) {
		s_print(S_DEBUG_ERROR, "imod \t%d\n", (int)info->imod);
		ret = PBL_DATA_ERR;
	}
	return ret;	
}

static int32_t sio_check_info_ick(const PBL_SIO_INFO *info)
{
	int32_t ret;
	int32_t val;

	ret = PBL_OK;

	val = info->ick;
	if ((val != PBL_SIO_ICK_X16) &&
		(val != PBL_SIO_ICK_X32) &&
		(val != PBL_SIO_ICK_X64) &&
		(val != PBL_SIO_ICK_X128)) {
		s_print(S_DEBUG_ERROR, "ick \t%d\n", (int)info->ick);
		ret = PBL_DATA_ERR;
	}
	return ret;	
}

static int32_t sio_check_info_csomod(const PBL_SIO_INFO *info)
{
	int32_t ret;
	int32_t val;

	ret = PBL_OK;

	val = info->csomod;
	if ((val != PBL_SIO_CSOMOD_OFF) && (val != PBL_SIO_CSOMOD_ON)) {
		s_print(S_DEBUG_ERROR, "csomod \t%d\n", (int)info->csomod);
		ret = PBL_DATA_ERR;
	}
	return ret;	
}



static int32_t sio_check_info_cssel(const PBL_SIO_INFO *info)
{
	int32_t ret;
	int32_t val;

	ret = PBL_OK;

	val = info->cssel;
	if ((val != PBL_SIO_CSSEL_CS0) &&
		(val != PBL_SIO_CSSEL_CS1) &&
		(val != PBL_SIO_CSSEL_CS2)) {
		s_print(S_DEBUG_ERROR, "cssel \t%d\n", (int)info->cssel);
		ret = PBL_DATA_ERR;
	}
	return ret;	
}



/**
 * sio_check_info() - Check PBL_SIO_INFO
 * @info: Pointer to PBL_SIO_INFO
 *
 * Check if the parameter of PBL_SIO_INFO are in range.
 *
 * Return: Success(PBL_OK) or Error
 */

static int32_t sio_check_info(const PBL_SIO_INFO *info)
{
	int32_t val;
	int32_t ret;

	ret = PBL_OK;


	val = info->brate;
	switch (val) {
	case PBL_SIO_BRATE_32K:
	case PBL_SIO_BRATE_64K:
	case PBL_SIO_BRATE_800K:
	case PBL_SIO_BRATE_1000K:
	case PBL_SIO_BRATE_1500K:
	case PBL_SIO_BRATE_2000K:
	case PBL_SIO_BRATE_3000K:
	case PBL_SIO_BRATE_4000K:
	case PBL_SIO_BRATE_8000K:
	case PBL_SIO_BRATE_12M:
	/* --- not support --- */
	case PBL_SIO_BRATE_2048:
	case PBL_SIO_BRATE_4096:
	case PBL_SIO_BRATE_8192:
	case PBL_SIO_BRATE_16384:
	case PBL_SIO_BRATE_128K:
	case PBL_SIO_BRATE_256K:
	case PBL_SIO_BRATE_512K:
	case PBL_SIO_BRATE_780K:
	case PBL_SIO_BRATE_975K:
	case PBL_SIO_BRATE_1250K:
	case PBL_SIO_BRATE_1264K:
	case PBL_SIO_BRATE_1750K:
	case PBL_SIO_BRATE_2250K:
	case PBL_SIO_BRATE_2500K:
	case PBL_SIO_BRATE_2750K:
	case PBL_SIO_BRATE_3250K:
	case PBL_SIO_BRATE_3300K:
	case PBL_SIO_BRATE_3500K:
	case PBL_SIO_BRATE_3750K:
	case PBL_SIO_BRATE_5500K:
	case PBL_SIO_BRATE_6500K:
	case PBL_SIO_BRATE_8250K:
	case PBL_SIO_BRATE_9750K:
		break;
	default:
		s_print(S_DEBUG_ERROR, "brate \t%d\n", (int)info->brate);
		ret = PBL_DATA_ERR;
		break;
	}


	val = info->lms;
	if ((val != PBL_SIO_LMS_LSB) && (val != PBL_SIO_LMS_MSB)) {
		s_print(S_DEBUG_ERROR, "lms \t%d\n", (int)info->lms);
		ret = PBL_DATA_ERR;
	}

	val = info->csel;
	if ((val != PBL_SIO_CSEL_INTNL) && (val != PBL_SIO_CSEL_EXTNL)) {
		s_print(S_DEBUG_ERROR, "csel \t%d\n", (int)info->csel);		
		ret = PBL_DATA_ERR;
	}

	val = info->csen;
	if ((val != PBL_SIO_CSEN_INTNL) && (val != PBL_SIO_CSEN_EXTNL)) {
		s_print(S_DEBUG_ERROR, "csen \t%d\n", (int)info->csen);
		ret = PBL_DATA_ERR;
	}

	val = info->imod;
	if ((val != PBL_SIO_IMOD_EN) && (val != PBL_SIO_IMOD_DIS)) {
		s_print(S_DEBUG_ERROR, "imod \t%d\n", (int)info->imod);
		ret = PBL_DATA_ERR;
	}

	val = info->ick;
	if ((val != PBL_SIO_ICK_X16) &&
		(val != PBL_SIO_ICK_X32) &&
		(val != PBL_SIO_ICK_X64) &&
		(val != PBL_SIO_ICK_X128)) {
		s_print(S_DEBUG_ERROR, "ick \t%d\n", (int)info->ick);
		ret = PBL_DATA_ERR;
	}

	val = info->rtmod;
	if ((val != PBL_SIO_RTMOD_NORMAL) && (val != PBL_SIO_RTMOD_AUTO)) {
		s_print(S_DEBUG_ERROR, "rtmod \t%d\n", (int)info->rtmod);
		ret = PBL_DATA_ERR;
	}

	val = info->csomod;
	if ((val != PBL_SIO_CSOMOD_OFF) && (val != PBL_SIO_CSOMOD_ON)) {
		s_print(S_DEBUG_ERROR, "csomod \t%d\n", (int)info->csomod);
		ret = PBL_DATA_ERR;
	}

	val = info->cssel;
	if ((val != PBL_SIO_CSSEL_CS0) &&
		(val != PBL_SIO_CSSEL_CS1) &&
		(val != PBL_SIO_CSSEL_CS2)) {
		s_print(S_DEBUG_ERROR, "cssel \t%d\n", (int)info->cssel);
		ret = PBL_DATA_ERR;
	}

	val = info->siockst;
	if ((val < D_REG16_MIN) || (D_REG16_MAX < val)) {
		s_print(S_DEBUG_ERROR, "siockst \t%d\n", (int)info->siockst);
		ret = PBL_DATA_ERR;
	}

	val = info->sioick;
	if ((val < D_REG16_MIN) || (D_REG16_MAX < val)) {
		s_print(S_DEBUG_ERROR, "sioick \t%d\n", (int)info->sioick);
		ret = PBL_DATA_ERR;
	}


	val = info->sioidly;
	if ((val < D_REG16_MIN) || (D_REG16_MAX < val)) {
		s_print(S_DEBUG_ERROR, "sioidly \t%d\n", (int)info->sioidly);
		ret = PBL_DATA_ERR;
	}

	val = info->siocsint;
	if ((val < D_REG16_MIN) || (D_REG16_MAX < val)) {
		s_print(S_DEBUG_ERROR, "siocsint \t%d\n", (int)info->siocsint);
		ret = PBL_DATA_ERR;
	}

	return ret;
}


/**
 * sio_is_start() - Check if SIO is working
 * @p: Pointer to sio base address
 *
 * Return: Start(1) or Stop(0)
 */
static bool sio_is_start(void __iomem *p)
{
	uint32_t val;

	val = readl_relaxed(p + D_REG_SIOCS);
	return !!(val & D_STATE_ST);
}

/**
 * sio_is_overrun() - Check if SIO is overrun
 * @p: Pointer to sio base address
 *
 * Return: overrun(1) or NOT overrun(0)
 */
static bool sio_is_overrun(void __iomem *p)
{
	uint32_t val;

	val = readl_relaxed(p + D_REG_SIOCS);
	return !!(val & D_STATE_OE);
}

/**
 * sio_is_xmit_size_over() - Check if the transfer size is in range.
 * @info: Pointer to sio base address
 *
 * Return: over (true) or NOT over(false)
 */
static bool sio_is_xmit_size_over(uint32_t len, uint32_t cscnt)
{
	uint32_t val;

	/* cscnt(SIOCSCNT)=0 means number of transfer once  */
	val = (cscnt + 1) * len;
	if ((val > D_BUFSZ_MAX) || (val == 0))
		return true;
	else
		return false;
}


/**
 * sio_xmit_start() - Start transfer
 * @priv: Pointer to driver private data
 * @start_info: Pointer to PBL_SIO_START_INFO
 *
 * Start transfer using PBL_SIO_INFO settings.
 * This function writes a value to registers
 * according to the settings of BPL_SIO_INFO and PBL_SIO_START_INFO.
 *
 * Return: success(PBL_OK) or fail
 */
static PBL_ER sio_xmit_start(struct cxd_sio_driver *priv, const PBL_SIO_START_INFO *start_info)
{
	const PBL_SIO_START_INFO *sinfo = start_info;
	int32_t mode;
	uint32_t val;
	uint32_t siocs;
	uint32_t ps_freq;
	uint32_t brate;
	
	mutex_lock(&priv->paramlock);
	priv->start_info = *sinfo;/* update */
	mutex_unlock(&priv->paramlock);

	mode = sio_check_xmit_mode(&priv->info);
	if (mode == D_XMIT_MODE_EC_IS) {
		priv->info.siocksten = 0;
		siocs = 0;
		priv->info.csomod = 0;
	} else if (mode == D_XMIT_MODE_EC_ES) {
		priv->info.siocksten = 0;
		siocs = 0;
		priv->info.csomod = 0;
	} else if (mode == D_XMIT_MODE_NR) {
		siocs = D_SCKOE(1);
	} else if (mode == D_XMIT_MODE_FS) {
		siocs = D_SCKOE(1);
	} else if (mode == D_XMIT_MODE_CS) {
		siocs = D_SCKOE(1);
	} else {
		s_print(S_DEBUG_ERROR, "mode error(%d)",mode);
		priv->xmitmode = PBL_DATA_ERR;
		return PBL_DATA_ERR;
	}
	priv->xmitmode = mode;

	if ((sinfo->mode != PBL_SIO_MOD_RX) &&
		(sinfo->mode != PBL_SIO_MOD_TX) &&
		(sinfo->mode != PBL_SIO_MOD_TXRX)) {
		s_print(S_DEBUG_ERROR, "Not support transfer mode %d\n", sinfo->mode);
		return PBL_DATA_ERR;
	}

	if ((mode == D_XMIT_MODE_CS) &&
		(sinfo->mode != PBL_SIO_MOD_TXRX) &&
		(sinfo->cscnt != 0) &&
		(priv->info.rtmod == PBL_SIO_RTMOD_AUTO)) {
		s_print(S_DEBUG_ERROR, "Not support auto txrx mode by cscnt!=0  %d\n", sinfo->cscnt);
		return PBL_DATA_ERR;
	}

	/* register set */
	ps_freq = (uint32_t)clk_get_rate(priv->ps);
	brate = (uint32_t)priv->info.brate;

	val = ps_freq / (2*brate) - 1;
	if (ps_freq % (2*brate) != 0) val +=1; 	/* rounding up to the decimal point */
	
	if (val < D_BGC_MIN){
	   val = D_BGC_MIN;	/* Rounded up to D_BGC_MIN or higher for HW */
	}

	writel_relaxed(D_SIOBGC1(val), priv->base + D_REG_SIOBGC1);
	writel_relaxed(D_SIOBGC0(val), priv->base + D_REG_SIOBGC0);
	s_print(S_DEBUG_DEBUG,"[SIO]brate %d, %d->%d[bps], %d[Hz]\n", val, priv->info.brate, ps_freq/(2*(val+1)), ps_freq );

	val = 0;
	val |= D_CSEN(priv->info.csen);
	val |= D_IMOD(priv->info.imod);
	val |= D_TRM(sinfo->mode);
	val |= D_ICK(priv->info.ick);
	val |= D_RTMOD(priv->info.rtmod);
	val |= D_CSOMOD(priv->info.csomod);
	writel_relaxed(val, priv->base + D_REG_SIOM);


#if DEBUG_SIO
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_CSEN 0x%x\n", D_CSEN(priv->info.csen));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_IMOD 0x%x\n", D_IMOD(priv->info.imod));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_TRM 0x%x\n", D_TRM(sinfo->mode));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_ICK 0x%x\n", D_ICK(priv->info.ick));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_RTMOD 0x%x\n", D_RTMOD(priv->info.rtmod));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_CSOMOD 0x%x\n", D_CSOMOD(priv->info.csomod));
#endif

	writel_relaxed(D_CKST1(priv->info.siockst), priv->base + D_REG_SIOCKST1);
	writel_relaxed(D_CKST0(priv->info.siockst), priv->base + D_REG_SIOCKST0);
	writel_relaxed(D_CKSTEN((priv->info.siocksten==0)?0:1), priv->base + D_REG_SIOCKSTEN); 
	writel_relaxed(D_ICK1(priv->info.sioick), priv->base + D_REG_SIOICK1);
	writel_relaxed(D_ICK0(priv->info.sioick), priv->base + D_REG_SIOICK0);
	writel_relaxed(D_ICKEN((priv->info.sioicken==0)?0:1), priv->base + D_REG_SIOICKEN);
	writel_relaxed(D_DLY1(priv->info.sioidly), priv->base + D_REG_SIOIDLY1); 
	writel_relaxed(D_DLY0(priv->info.sioidly), priv->base + D_REG_SIOIDLY0); 
	writel_relaxed(D_IDLYEN((priv->info.sioidly==0)?0:1), priv->base + D_REG_SIOIDLYEN);
	writel_relaxed(D_INT1(priv->info.siocsint), priv->base + D_REG_SIOCSINT1);
	writel_relaxed(D_INT0(priv->info.siocsint), priv->base + D_REG_SIOCSINT0);

#if DEBUG_SIO
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOCKST1 0x%x\n", D_CKST1(priv->info.siockst));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOCKST0 0x%x\n", D_CKST0(priv->info.siockst));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOCKSTEN 0x%x\n", D_CKSTEN(priv->info.siocksten));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOICK1 0x%x\n", D_ICK1(priv->info.sioick));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOICK0 0x%x\n", D_ICK0(priv->info.sioick));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOICKEN 0x%x\n", D_ICKEN(priv->info.sioicken));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOIDLY1 0x%x\n", D_DLY1(priv->info.sioidly));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOIDLY0 0x%x\n", D_DLY0(priv->info.sioidly));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOIDLYEN 0x%x\n", D_IDLYEN((priv->info.sioidly==0)?0:1));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOCSINT1 0x%x\n", D_INT1(priv->info.siocsint));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOCSINT0 0x%x\n", D_INT0(priv->info.siocsint));
#endif

	val = D_SCKINV(priv->info.siopol);
	writel_relaxed(val, priv->base + D_REG_SIOPOL);


	val = D_CSOSEL(priv->info.cssel);
	writel_relaxed(val, priv->base + D_REG_CSSEL);


	val = sinfo->cscnt;
	writel_relaxed(D_CNT(val), priv->base + D_REG_SIOCSCNT);


	val = (sinfo->num) - 1;/* SION=0 means transfer size 1 */
	writel_relaxed(D_SION(val), priv->base + D_REG_SION);

	writel_relaxed(0, priv->base + D_REG_SIOSA);


	priv->irqfact = PBL_SIO_INT_TRAN_END;

	siocs |= D_CLOE(1);
#ifdef D_WA_SIOCS_REG_CLEAR
	writel_relaxed(siocs, priv->base + D_REG_SIOCS);

	/* CLOE issue : Software Work around */
	ndelay(D_APB_1CLK_NS);
	siocs &= ~(D_CLOE(1));
#endif	
	siocs |= D_CSEL(priv->info.csel);
	siocs |= D_LMS(priv->info.lms);
	siocs |= D_SIOST(1);
	siocs |= D_SOEN(1); 
	writel_relaxed(siocs, priv->base + D_REG_SIOCS);


#if DEBUG_SIO
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOCKST1 0x%08x\n", D_SCKINV(priv->info.siopol));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOCKST0 0x%08x\n", D_CSOSEL(priv->info.cssel));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOCKSTEN 0x%08x\n", D_CNT(sinfo->cscnt));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOICK1 0x%08x\n", D_SION(((uint32_t)(sinfo->num) - 1)));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOICK0 0x%08x\n", D_CSEL(priv->info.csel));
	s_print(S_DEBUG_DEBUG,"[SIO] D_REG_SIOICKEN 0x%08x\n",D_LMS(priv->info.lms));
#endif

	return PBL_OK;
}

/**
 * sio_sub_open() - common function of "open"
 * @priv: Pointer to driver private data
 * @mode: Open mode (PBL or FOPS)
 *
 * Return: success(PBL_OK) or fail
 */
static PBL_ER sio_sub_open(struct cxd_sio_driver *priv, uint32_t mode)
{
	uint32_t ret;

	mutex_lock(&priv->paramlock);

	if (priv->is_used != D_CH_FREE) {
		mutex_unlock(&priv->paramlock);
		return PBL_DUPLICATE_OPEN_ERR;
	}else{
		ret = reset_control_assert(priv->rst);
		if (ret)
			goto err_reset;
		ret = reset_control_deassert(priv->rst);
		if (ret)
			goto err_reset;
		ret = clk_prepare_enable(priv->pclk);
		if (ret)
			goto err_pclk;
		ret = clk_prepare_enable(priv->ps);
		if (ret)
			goto err_ps;
		priv->is_used = mode;
		init_completion(&priv->compl);
		priv->int_func = NULL;
		ret = PBL_OK;
	}

	enable_irq(priv->irq_no);

	writel_relaxed(D_SIOEN(1), priv->base + D_REG_SIOEN);

	mutex_unlock(&priv->paramlock);

	return ret;

err_ps:
	s_print(S_DEBUG_ERROR, "%s:%d fail to enable ps\n", __func__, __LINE__);
	clk_disable_unprepare(priv->pclk);
err_pclk:
	s_print(S_DEBUG_ERROR, "%s:%d fail to enable pclk\n", __func__, __LINE__);
	reset_control_assert(priv->rst);
err_reset:
	s_print(S_DEBUG_ERROR, "%s:%d fail to reset deassert\n", __func__, __LINE__);
 
	mutex_unlock(&priv->paramlock);
	return PBL_OTHER_ERR;
}

/**
 * sio_sub_close() - common function of "close"
 * @priv: Pointer to driver private data
 * @mode: Close mode (D_CH_PBL or D_CH_FOPS)
 *
 * Return: success(PBL_OK) or fail
 */
static PBL_ER sio_sub_close(struct cxd_sio_driver *priv, uint32_t mode)
{
	uint32_t val,ret=PBL_OK;

	mutex_lock(&priv->paramlock);
	
	if (priv->is_used != mode){
		mutex_unlock(&priv->paramlock);
		return PBL_DUPLICATE_OPEN_ERR;
	}

	val = readl_relaxed(priv->base + D_REG_SIOCS);
	if(val & D_SIOST(1)){
		writel_relaxed(val & ~(D_SIOST(1)), (priv->base + D_REG_SIOCS));
		fsleep(D_TRANS_CANCEL_US);
	}

	disable_irq(priv->irq_no);

	writel_relaxed(D_SIOEN(0), priv->base + D_REG_SIOEN);
	clk_disable_unprepare(priv->pclk);
	clk_disable_unprepare(priv->ps);
	if(reset_control_assert(priv->rst))
		ret = PBL_OTHER_ERR;
	priv->is_used = D_CH_FREE;
	priv->int_func = NULL;

	mutex_unlock(&priv->paramlock);	

	return ret;
}

PBL_ER pbl_sio_open(const uint32_t ch)
{
	struct cxd_sio_driver *priv;

	s_print(S_DEBUG_DEBUG,"[SIO]pbl_sio_open\n");

	priv = sio_get_private(ch);
	if (priv == D_CH_ERR)
		return PBL_DATA_ERR;

	return sio_sub_open(priv, D_CH_PBL);
}
EXPORT_SYMBOL(pbl_sio_open);

PBL_ER pbl_sio_close(const uint32_t ch)
{
	struct cxd_sio_driver *priv;

	s_print(S_DEBUG_DEBUG,"[SIO]pbl_sio_close\n");

	priv = sio_get_private(ch);
	if (priv == D_CH_ERR)
		return PBL_DATA_ERR;
	
	return sio_sub_close(priv, D_CH_PBL);
}
EXPORT_SYMBOL(pbl_sio_close);

PBL_ER pbl_sio_set_func(const uint32_t ch, const PBL_SIO_INFO *info, PBL_FUNC arg)
{

	struct cxd_sio_driver *priv;

	priv = sio_get_private(ch);
	if (priv == D_CH_ERR)
		return PBL_DATA_ERR;

	if (priv->is_used != D_CH_PBL)
		return PBL_NOT_OPEN_ERR;

	if (sio_is_start(priv->base))
		return PBL_HW_BUSY_ERR;

	if (info == NULL)
		return PBL_DATA_ERR;

	if (sio_check_info(info) != PBL_OK)
		return PBL_DATA_ERR;


	mutex_lock(&priv->paramlock);
	priv->info = *info;
	priv->int_func = arg;
	mutex_unlock(&priv->paramlock);
	return PBL_OK;
}
EXPORT_SYMBOL(pbl_sio_set_func);

/**
 * sio_sub_hwbuf_access() - Transfer buffer access
 * @priv: Pointer to driver private data
 * @app_buf: Upperlayer buffer such as application
 * @len: Transfer size
 * @f: Read or Write flag
 *
 * Write or Read to/from SIO hardware buffer.
 * SIO hardware buffer is restricted to access 32bit.
 * Upperlayer does not know limitation, so the function covers it.
 *
 */
static void sio_sub_hwbuf_access(struct cxd_sio_driver *priv, const char *app_buf, const size_t len, int32_t f)
{
	uint32_t i;
	int32_t ibuf[D_BUFSZ_MAX >> 2];

	memset(ibuf, 0, D_BUFSZ_MAX);
	/* sio buffer must access by word size */
	if (f == PBL_SIO_MOD_TX) {
		memcpy(ibuf, app_buf, len);
		for (i = 0; i < D_BUFSZ_MAX; i += 4)
			writel_relaxed(*(ibuf + (i >> 2)), priv->base + D_REG_DATABUF + i);
	} else {
		for (i = 0; i < D_BUFSZ_MAX; i += 4)
			*(ibuf + (i >> 2)) = readl_relaxed(priv->base + D_REG_DATABUF + i);
		memcpy((char *)app_buf, (char *)ibuf, len);
	}
}

/**
 * sio_sub_rw() - Wrapper sio_sub_hwbuf_access
 * @priv: Pointer to driver private data
 * @app_buf: Upperlayer buffer such as application
 * @len: Transfer size
 * @f: Read or Write flag
 *
 * Error check for pbl_* function
 *
 */
static uint32_t sio_sub_rw(struct cxd_sio_driver *priv,
	const char *buf, const size_t len, int32_t f)
{
	if (priv->is_used != D_CH_PBL)
		return PBL_NOT_OPEN_ERR;

	if (sio_is_start(priv->base))
		return PBL_HW_BUSY_ERR;

	if ((buf == NULL) || (len > D_BUFSZ_MAX) || (len == 0))
		return PBL_DATA_ERR;

	if (mutex_is_locked(&priv->buflock))
		return PBL_OTHER_ERR;

	mutex_lock(&priv->buflock);
	sio_sub_hwbuf_access(priv, buf, len, f);
	mutex_unlock(&priv->buflock);
	return len;
}

int32_t pbl_sio_write_buffer(const uint32_t ch, const char *wbuf, const size_t len)
{
	struct cxd_sio_driver *priv;

	priv = sio_get_private(ch);
	if (priv == D_CH_ERR)
		return PBL_DATA_ERR;

	return sio_sub_rw(priv, wbuf, len, PBL_SIO_MOD_TX);
}
EXPORT_SYMBOL(pbl_sio_write_buffer);

int32_t pbl_sio_read_buffer(const uint32_t ch, const char *rbuf, const size_t len)
{
	struct cxd_sio_driver *priv;

	priv = sio_get_private(ch);
	if (priv == D_CH_ERR)
		return PBL_DATA_ERR;

	return sio_sub_rw(priv, rbuf, len, PBL_SIO_MOD_RX);
}
EXPORT_SYMBOL(pbl_sio_read_buffer);

PBL_ER pbl_sio_start(const uint32_t ch, const PBL_SIO_START_INFO *start_info)
{
	struct cxd_sio_driver *priv;

	if (!start_info){
		s_print(S_DEBUG_ERROR, "start_info NULL");
		return PBL_DATA_ERR;
	}

	priv = sio_get_private(ch);
	if (priv == D_CH_ERR){
		s_print(S_DEBUG_ERROR, "sio_get_private error(ch error)");
		return PBL_DATA_ERR;
	}

	if (priv->is_used != D_CH_PBL){
		s_print(S_DEBUG_ERROR, "is_used != D_CH_PBL");
		return PBL_NOT_OPEN_ERR;
	}

	if (sio_is_start(priv->base)){
		s_print(S_DEBUG_ERROR, "PBL_HW_BUSY_ERR");
		return PBL_HW_BUSY_ERR;
	}

	if (mutex_is_locked(&priv->buflock)){
		s_print(S_DEBUG_ERROR, "mutex locked");
		return PBL_OTHER_ERR;
	}

	if (sio_is_xmit_size_over(start_info->num, start_info->cscnt)){
		s_print(S_DEBUG_ERROR, "size over");
		return PBL_DATA_ERR;
	}

	return sio_xmit_start(priv, start_info);
}
EXPORT_SYMBOL(pbl_sio_start);

PBL_ER pbl_sio_get_status(const uint32_t ch)
{
	struct cxd_sio_driver *priv;

	priv = sio_get_private(ch);
	if (priv == D_CH_ERR)
		return PBL_DATA_ERR;

	if (priv->is_used != D_CH_PBL)
		return PBL_DATA_ERR;

	if (sio_is_start(priv->base))
		return PBL_SIO_STS_EXEC;

	if (sio_is_overrun(priv->base) ||
		(priv->irqfact == PBL_SIO_INT_OE_ERR))
		return PBL_SIO_STS_OE;

	if (priv->irqfact == PBL_SIO_INT_CS_CANCEL_ERR)
		return PBL_SIO_STS_END;

	return PBL_OK;
}
EXPORT_SYMBOL(pbl_sio_get_status);

PBL_ER pbl_sio_chk_buffer(const uint32_t ch, const uint32_t buf_type)
{
	uint32_t sion, siosa, rtmod, siocs;
	struct cxd_sio_driver *priv;

	priv = sio_get_private(ch);
	if (priv == D_CH_ERR)
		return PBL_DATA_ERR;

	if (priv->is_used != D_CH_PBL)
		return PBL_NOT_OPEN_ERR;

	siosa = readl_relaxed(priv->base + D_REG_SIOSA);
	sion = readl_relaxed(priv->base + D_REG_SION);
	rtmod = (readl_relaxed(priv->base + D_REG_SIOM) & D_RTMOD(1));
	siocs = readl_relaxed(priv->base + D_REG_SIOCS);

	if (siocs & D_SIOST(1))
		return PBL_OTHER_ERR;

	if ((priv->xmitmode == D_XMIT_MODE_CS) ||
		(priv->xmitmode == D_XMIT_MODE_NR && rtmod != 0))
		siosa += 1;

	if (buf_type == PBL_SIO_BUF_RX) {
		if (siosa == 0)
			return PBL_OTHER_ERR;
	} else 
		if (buf_type != PBL_SIO_BUF_TX)
			return PBL_DATA_ERR;

	return PBL_OK;
}
EXPORT_SYMBOL(pbl_sio_chk_buffer);

PBL_ER pbl_sio_clr_buffer(const uint32_t ch)
{
	int i;
	struct cxd_sio_driver *priv;

	priv = sio_get_private(ch);
	if (priv == D_CH_ERR)
		return PBL_DATA_ERR;

	if (priv->is_used != D_CH_PBL)
		return PBL_NOT_OPEN_ERR;

	if (sio_is_start(priv->base))
		return PBL_OTHER_ERR;

	if (mutex_is_locked(&priv->buflock))
		return PBL_OTHER_ERR;

	writel_relaxed(0, priv->base + D_REG_SIOSA);

	mutex_lock(&priv->buflock);
	for (i = 0; i < D_BUFSZ_MAX; i += 4)
		writel_relaxed(0, priv->base + D_REG_DATABUF + i);
	mutex_unlock(&priv->buflock);

	return PBL_OK;
}
EXPORT_SYMBOL(pbl_sio_clr_buffer);

static int open(struct inode *inode, struct file *fp)
{
	struct miscdevice *mdev = fp->private_data;
	struct cxd_sio_driver *priv = container_of(mdev, struct cxd_sio_driver, miscdev);
	uint32_t ret;

	ret = sio_sub_open(priv, D_CH_FOPS);
	if ( ret == PBL_OK)
		return 0;
	else if(ret == PBL_DUPLICATE_OPEN_ERR)
		return -EACCES;
	else
		return -EIO;
}

static int close(struct inode *inode, struct file *fp)
{
	struct miscdevice *mdev = fp->private_data;
	struct cxd_sio_driver *priv = container_of(mdev, struct cxd_sio_driver, miscdev);
	uint32_t ret;

	ret = sio_sub_close(priv, D_CH_FOPS);
	if (ret != PBL_OK){
		if(ret == PBL_OTHER_ERR)
			return -EIO;
		else
			return -EBADF;
	}else
		return 0;
}

static ssize_t read(struct file *fp, char __user *user, size_t count, loff_t *l)
{
	struct miscdevice *mdev = fp->private_data;
	struct cxd_sio_driver *priv = container_of(mdev, struct cxd_sio_driver, miscdev);
	PBL_SIO_START_INFO start_info;
	char buf[D_BUFSZ_MAX];

	if (priv->is_used != D_CH_FOPS)
		return -EBADF;

	if (sio_is_start(priv->base))
		return -EBUSY;

	start_info.mode = PBL_SIO_MOD_RX;
	start_info.num = count;
	start_info.cscnt = 0;

	if (sio_is_xmit_size_over(start_info.num, start_info.cscnt))
		return -EINVAL;

	if (sio_xmit_start(priv, &start_info) != PBL_OK)
		return -EIO;

	wait_for_completion(&priv->compl);

	sio_sub_hwbuf_access(priv, &buf[0], start_info.num, PBL_SIO_MOD_RX);
	if (copy_to_user(user, (void *)buf, start_info.num) != 0) {
		s_print(S_DEBUG_ERROR, "fault: count %d", start_info.num);
		return -EFAULT;
	}

	return start_info.num;
}

static ssize_t write(struct file *fp, const char __user *user, size_t count, loff_t *l)
{
	
	struct miscdevice *mdev = fp->private_data;
	struct cxd_sio_driver *priv = container_of(mdev, struct cxd_sio_driver, miscdev);
	PBL_SIO_START_INFO start_info;
	char buf[D_BUFSZ_MAX];


	if (priv->is_used != D_CH_FOPS)
		return -EBADF;

	if (sio_is_start(priv->base))
		return -EBUSY;

	start_info.mode = PBL_SIO_MOD_TX;
	start_info.num = count;
	start_info.cscnt = 0;
	if (sio_is_xmit_size_over(start_info.num, start_info.cscnt))
		return -EINVAL;

	if (copy_from_user((void *)buf, user, start_info.num) != 0) {
		s_print(S_DEBUG_ERROR, "fault: count %d", start_info.num);
		return -EFAULT;
	}

	sio_sub_hwbuf_access(priv, &buf[0], start_info.num, PBL_SIO_MOD_TX);

	if (sio_xmit_start(priv, &start_info) != PBL_OK)
		return -EIO;


	wait_for_completion(&priv->compl);
	return start_info.num;

}

static long unlocked_ioctl(struct file *fp, unsigned int cmd, unsigned long arg)
{
	struct miscdevice *mdev = fp->private_data;
	struct cxd_sio_driver *priv = container_of(mdev, struct cxd_sio_driver, miscdev);
	PBL_SIO_INFO *info = &priv->info;
	PBL_SIO_START_INFO start_info;
	struct sio_xfer *xfer;
	char buf[D_BUFSZ_MAX];
	int32_t ret;
	int32_t ret2;

	ret = PBL_OK;
	ret2 = PBL_OK;

	if (priv->is_used != D_CH_FOPS)
		return -EBADF;

	switch (cmd) {
	case SIO_MASTER_TRANSFER:
		xfer = (struct sio_xfer *)arg;

		start_info.mode = PBL_SIO_MOD_TXRX;
		start_info.num = xfer->count;
		start_info.cscnt = 0;
		if (sio_is_xmit_size_over(start_info.num, start_info.cscnt)) {
			s_print(S_DEBUG_ERROR, "transfer size is %d", start_info.num);
			return -EINVAL;
		}

		if (xfer->tx == NULL) {
			s_print(S_DEBUG_ERROR, "tx buffer is NULL");
			return -EINVAL;
		}
		if (xfer->rx == NULL) {
			s_print(S_DEBUG_ERROR, "rx buffer is NULL");
			return -EINVAL;
		}

		if (copy_from_user((void *)buf, xfer->tx, start_info.num) != 0) {
			s_print(S_DEBUG_ERROR, "write fault");
			return -EFAULT;
		}
		sio_sub_hwbuf_access(priv, &buf[0], start_info.num, PBL_SIO_MOD_TX);
		s_print(S_DEBUG_DEBUG,"[SIO]SIO_MASTER_TRANSFER PBL_SIO_MOD_TX\n");

		if (sio_xmit_start(priv, &start_info) != PBL_OK)
			return -EIO;

		wait_for_completion(&priv->compl);
		sio_sub_hwbuf_access(priv, &buf[0], start_info.num, PBL_SIO_MOD_RX);
		s_print(S_DEBUG_DEBUG,"[SIO]SIO_MASTER_TRANSFER PBL_SIO_MOD_RX\n");
		if (copy_to_user(xfer->rx, (void *)buf, start_info.num) != 0) {
			s_print(S_DEBUG_ERROR, "read fault");
			return -EFAULT;
		}
		return 0;
	case SIO_BAUD:
		info->brate = arg;
		ret = sio_check_info_brate(info);
		break;
	case SIO_CTL_DISABLE_ICLK:
		priv->info.sioick = arg;
		if(arg){	
			priv->info.sioicken = 1;
		}else{
			priv->info.sioicken = 0;
		}
		break;
	case SIO_CTL_ICK128:
		priv->info.ick = PBL_SIO_ICK_X128;
		priv->info.imod = PBL_SIO_IMOD_EN;
		ret = sio_check_info_ick(info);
		ret2 = sio_check_info_imod(info);				
		break;
	case SIO_CTL_ICK64:
		priv->info.ick = PBL_SIO_ICK_X64;
		priv->info.imod = PBL_SIO_IMOD_EN;
		ret = sio_check_info_ick(info);
		ret2 = sio_check_info_imod(info);
		break;
	case SIO_CTL_ICK32:
		priv->info.ick = PBL_SIO_ICK_X32;
		priv->info.imod = PBL_SIO_IMOD_EN;
		ret = sio_check_info_ick(info);
		ret2 = sio_check_info_imod(info);
		break;
	case SIO_CTL_ICK16:
		priv->info.ick = PBL_SIO_ICK_X16;
		priv->info.imod = PBL_SIO_IMOD_EN;
		ret = sio_check_info_ick(info);
		ret2 = sio_check_info_imod(info);
		break;
	case SIO_CTL_ICK_DIS:
		priv->info.imod = PBL_SIO_IMOD_DIS;
		ret = sio_check_info_imod(info);
		break;
	case SIO_CTL_ENABLE_SCK:
		priv->info.csel = PBL_SIO_CSEL_INTNL;
		ret = sio_check_info_csel(info);
		break;
	case SIO_CTL_EXT_CLK:
		priv->info.csel = PBL_SIO_CSEL_EXTNL;
		priv->info.imod = PBL_SIO_IMOD_DIS;
		priv->info.siocksten = 0;
		priv->info.sioick = 0;
		ret = sio_check_info_csel(info);
		break;
	case SIO_CTL_MSB_FIRST:
		priv->info.lms = PBL_SIO_LMS_MSB;
		ret = sio_check_info_lms(info);
		break;
	case SIO_CTL_LSB_FIRST:
		priv->info.lms = PBL_SIO_LMS_LSB;
		ret = sio_check_info_lms(info);
		break;
	case SIO_CTL_ENABLE_SCS:
		if (arg != 0){
			priv->info.csomod = PBL_SIO_CSOMOD_ON;
			ret = sio_check_info_csomod(info);
		}else{
			priv->info.csomod = PBL_SIO_CSOMOD_OFF;
			ret = sio_check_info_csomod(info);
		}
		break;
	case SIO_CTL_CSSEL0:
		priv->info.cssel = PBL_SIO_CSSEL_CS0;
		ret = sio_check_info_cssel(info);
		break;
	case SIO_CTL_CSSEL1:
		priv->info.cssel = PBL_SIO_CSSEL_CS1;
		ret = sio_check_info_cssel(info);
		break;
	case SIO_CTL_CSSEL2:
		priv->info.cssel = PBL_SIO_CSSEL_CS2;
		ret = sio_check_info_cssel(info);
		break;
	case SIO_CTL_INV_SCK:
		if (arg != 0){
			priv->info.siopol = true;
		}else{
			priv->info.siopol = false;
		}
		break;
	case SIO_CTL_CSEN:
		priv->info.csen = arg;
		break;

#if DEBUG_TEST_SIO
	case SIO_CTL_GET_DISABLE_ICLK:
		return priv->info.sioick;
	case SIO_CTL_GET_ICK:
		return priv->info.ick;
	case SIO_CTL_GET_CSEL:
		return priv->info.csel;
	case SIO_CTL_GET_LMS:
		return priv->info.lms;
	case SIO_CTL_GET_CSOMOD:
		return priv->info.csomod;
	case SIO_CTL_GET_CSSEL:
		return priv->info.cssel;
	case SIO_CTL_GET_SIOPOL:
		return priv->info.siopol;
	case SIO_CTL_GET_BRATE:
		return priv->info.brate;
#endif
	default:
		return -EINVAL;
	}


	priv->info.siockst = D_IOCTL_CKST_VAL;
	priv->info.siocksten = D_IOCTL_CKSTEN_VAL;
	priv->info.sioidlyen = D_IOCTL_IDLYEN_VAL;
	priv->info.sioidly = D_IOCTL_IDLY_VAL;
	priv->info.siocsint = D_IOCTL_CSINT_VAL;
	priv->info.rtmod = D_IOCTL_RTMOD_VAL;


	if((ret != PBL_OK) || (ret2 != PBL_OK)){
		s_print(S_DEBUG_DEBUG,"[SIO]unlocked_ioctl sio_check_info NG\n");
		return -EINVAL;
	}
	else{
		s_print(S_DEBUG_DEBUG,"[SIO]unlocked_ioctl sio_check_info OK\n");
		return 0;
	}
}

static const struct file_operations fops = {
	.llseek = seq_lseek,
	.open = open,
	.owner = THIS_MODULE,
	.release = close,
	.unlocked_ioctl = unlocked_ioctl,
	.write = write,
	.read = read,
};

/**
 * sio_interrupt() - Interrupt of SIO
 * @irq: interrupt number
 * @data: Pointer to driver private data
 *
 * return irq complete or Start thread
 *
 */
static irqreturn_t sio_interrupt(int irq, void *data)
{
	struct cxd_sio_driver *priv = data;
	uint32_t val;

#if DEBUG_TEST_SIO
	SIO_time_mesure_start();
#endif
	val = readl_relaxed(priv->base + D_REG_SIOCS);
	if ((val & D_STATE_OE) != 0)
		priv->irqfact = PBL_SIO_INT_OE_ERR;
	else if ((val & D_STATE_ST) != 0)
		priv->irqfact = PBL_SIO_INT_CS_CANCEL_ERR;
	else
		priv->irqfact = PBL_SIO_INT_TRAN_END;

	val |= D_ICLSIO(1);
	val &= ~(D_SIOST(1));
	writel_relaxed(val, priv->base + D_REG_SIOCS);
#ifdef D_WA_SIOCS_REG_CLEAR
	/* CLOE issue : Software Work around */
	val &= ~(D_ICLSIO(1));
	ndelay(D_APB_1CLK_NS);
	writel_relaxed(val, priv->base + D_REG_SIOCS);
#endif
	complete(&priv->compl);

#if DEBUG_TEST_SIO
	SIO_time_mesure_stop();
#endif

	if (priv->int_func != NULL){
		return IRQ_WAKE_THREAD;
	}
	else {
		return IRQ_HANDLED;
	}
}
/**
 * sio_thread() - interrupt thread
 * @irq: interrupt number
 * @data: Pointer to driver private data
 *
 * The thread is started with IRQ_WAKE_THREAD.
 *
 * return irq complete
 *
 */
static irqreturn_t sio_thread(int irq, void *data)
{
	struct cxd_sio_driver *priv = data;

	priv->int_func(priv->irqfact);
	return IRQ_HANDLED;
}

static int sio_probe(struct platform_device *pdev)
{
	struct device *dev = &pdev->dev;
	struct cxd_sio_driver *priv = NULL;
	uint32_t dev_id;
	struct resource *res = NULL;
	int ret;

	s_print(S_DEBUG_DEBUG,"[SIO]probe start\n");
	ret = -EINVAL;
	if (of_property_read_u32(dev->of_node, "dev-id", &dev_id))
		goto probe_err;

	if ((dev_id != PBL_SIO_CH0) && (dev_id != PBL_SIO_CM_CH0))
		goto probe_err;

	priv = sio_get_private(dev_id);
	priv->is_used = D_CH_FREE;
	priv->irqfact = PBL_SIO_INT_TRAN_END;
	priv->dev = dev;
	mutex_init(&priv->paramlock);
	mutex_init(&priv->buflock);

	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	priv->base = devm_ioremap_resource(dev, res);
	if (!priv->base)
		goto probe_err;

	res = platform_get_resource(pdev, IORESOURCE_IRQ, 0);
	if (res) {
		irq_set_status_flags(res->start, IRQ_NOAUTOEN);
		if (devm_request_threaded_irq(dev, res->start, &sio_interrupt,
				&sio_thread, IRQF_TRIGGER_RISING, "sio_irq", priv))
			goto probe_err;
	}
	else goto probe_err;

	priv->irq_no = res->start;

	priv->pclk = devm_clk_get(dev, "sio_pclk");
	if (IS_ERR(priv->pclk)) {
		s_print(S_DEBUG_INFO, "%s:%d fail to get pclk\n", __func__, __LINE__);
		return PTR_ERR(priv->pclk);
	}
	priv->ps = devm_clk_get(dev, "sio_ps");
	if (IS_ERR(priv->ps)) {
		s_print(S_DEBUG_INFO, "%s:%d fail to get ps clock\n", __func__, __LINE__);
		return PTR_ERR(priv->ps);
	}
	priv->rst = devm_reset_control_get_exclusive(dev, NULL);
	if (IS_ERR(priv->rst)) {
		s_print(S_DEBUG_INFO, "%s:%d fail to get reset\n", __func__, __LINE__);
		return PTR_ERR(priv->rst);
	}

	s_print(S_DEBUG_DEBUG,"[SIO]ps clock %lu[Hz]",clk_get_rate(priv->ps));
	s_print(S_DEBUG_DEBUG,"[SIO]probe end\n");

	snprintf(priv->devname, sizeof(priv->devname), "sio%d", dev_id);
	priv->miscdev.name = priv->devname;
	priv->miscdev.minor = MISC_DYNAMIC_MINOR,
	priv->miscdev.fops = &fops,
	platform_set_drvdata(pdev, priv);
	init_completion(&priv->compl); // for sio_interrupt before open
	return misc_register(&priv->miscdev);

probe_err:
	s_print(S_DEBUG_ERROR, "%s:%d\n", __func__, __LINE__);
	s_print(S_DEBUG_ERROR, "dev-id\t%d\n", dev_id);
	s_print(S_DEBUG_ERROR, "pclk\t%d\n", dev_id);
	if (priv)
		s_print(S_DEBUG_ERROR, "reg addr\t%p\n", priv->base);
	if (res)
		s_print(S_DEBUG_ERROR, "irq no.\t%lld\n", res->start);
	return ret;
}

static int sio_remove(struct platform_device *pdev)
{
	struct cxd_sio_driver *priv = platform_get_drvdata(pdev);
	uint32_t val;
	int ret = 0;

	if(priv->is_used != D_CH_FREE){
		if (sio_is_start(priv->base)) {
			/* force stop */
			val = readl_relaxed(priv->base + D_REG_SIOCS);
			writel_relaxed(val & ~(D_SIOST(1)), (priv->base + D_REG_SIOCS));
			fsleep(D_TRANS_CANCEL_US);
			ret = -EBUSY;
		}
		writel_relaxed(D_SIOEN(0), priv->base + D_REG_SIOEN);
		clk_disable_unprepare(priv->pclk);
		clk_disable_unprepare(priv->ps);
		reset_control_assert(priv->rst);
	}
	misc_deregister(&priv->miscdev);

	return ret;
}

static int sio_suspend(struct platform_device *pdev, pm_message_t state)
{
	struct cxd_sio_driver *priv = platform_get_drvdata(pdev);
	int32_t i;
	
	if(priv->is_used != D_CH_FREE){
		if (sio_is_start(priv->base)){
			return -EBUSY;
		}
		for (i = 0; i < D_REG_RANGE; i += 4)
			priv->pm_regs[i >> 2] = readl_relaxed(priv->base + i);
		sio_sub_hwbuf_access(priv, &priv->align_buf[0], D_BUFSZ_MAX, PBL_SIO_MOD_RX);
		clk_disable_unprepare(priv->pclk);
		clk_disable_unprepare(priv->ps);
		reset_control_assert(priv->rst);
	}
	return 0;
}

static int sio_resume(struct platform_device *pdev)
{
	struct cxd_sio_driver *priv = platform_get_drvdata(pdev);
	int32_t i;
	int ret;

	if(priv->is_used != D_CH_FREE){
		reset_control_deassert(priv->rst);
		ret = clk_prepare_enable(priv->pclk);
		if (ret)
			return ret;
		ret = clk_prepare_enable(priv->ps);
		if (ret)
			return ret;

		for (i = 0; i < D_REG_RANGE; i += 4)
			writel_relaxed(priv->pm_regs[i >> 2], priv->base + i);
		sio_sub_hwbuf_access(priv, &priv->align_buf[0], D_BUFSZ_MAX, PBL_SIO_MOD_TX);
	}
	return 0;
}

static const struct of_device_id dev_match[] = {
	{ .compatible = D_DEVICENAME},
	{ /* end of list */ },
};
static struct platform_driver driver_info = {
	.driver = {
		.name = D_DRIVERNAME,
		.of_match_table = of_match_ptr(dev_match),
	},
	.probe = sio_probe,
	.remove = sio_remove,
	.suspend = sio_suspend,
	.resume = sio_resume,
};

static int __init sio_init(void)
{
	return platform_driver_register(&driver_info);
}

static void __exit sio_exit(void)
{
	platform_driver_unregister(&driver_info);
}

#if DEBUG_TEST_SIO
PBL_SIO_INFO *sio_get_info(uint32_t dev_id)
{
	struct cxd_sio_driver *priv;

	priv = sio_get_private(dev_id);
	if (priv == D_CH_ERR)
		return NULL;

	return &priv->info;
}
EXPORT_SYMBOL(sio_get_info);


void *sio_get_baseaddress(uint32_t dev_id)
{
	//void __iomem *base;
	struct cxd_sio_driver *priv;

	priv = sio_get_private(dev_id);
	if (priv == D_CH_ERR)
		return NULL;

	return priv->base;
}
EXPORT_SYMBOL(sio_get_baseaddress);



/* -------------------------------- 
   Time measurement module
---------------------------------*/

static volatile u64 SIO_t1[2],SIO_t2[2];
static volatile u64 SIO_max[2];

void SIO_time_mesure_reset(void)
{
	SIO_max[0]=0;
	SIO_max[1]=0;
}
EXPORT_SYMBOL(SIO_time_mesure_reset);

static void SIO_time_mesure_start(void)
{
	SIO_t1[smp_processor_id()]=ktime_get_ns();
}

static void SIO_time_mesure_stop(void)
{
	u64 delta = 0;
	u32 p;
	p=smp_processor_id();
	SIO_t2[p]=ktime_get_ns();
	if ( SIO_t1[p]!=0 )
		delta = SIO_t2[p]-SIO_t1[p];

	if (delta > SIO_max[p])
		SIO_max[p]=delta;
}

void SIO_time_mesure_print(void)
{
//	u32 p;
	if (SIO_max[0]){
		printk("maximum time@cpu%u=%u[ns]",0,(unsigned int)SIO_max[0]);
	}else{
		printk("maximum time@cpu%u=--[ns]",0);
	}

	if (SIO_max[1]){
		printk("maximum time@cpu%u=%u[ns]",1,(unsigned int)SIO_max[1]);
	}else{
		printk("maximum time@cpu%u=--[ns]",1);
	}
}
EXPORT_SYMBOL(SIO_time_mesure_print);

#endif

module_init(sio_init)
module_exit(sio_exit)
MODULE_LICENSE("GPL");
