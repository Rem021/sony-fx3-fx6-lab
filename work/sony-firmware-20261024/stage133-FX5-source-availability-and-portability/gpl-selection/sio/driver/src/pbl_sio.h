/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */
// for kernel
#ifndef __SIO_LIN_H__
#define __SIO_LIN_H__

#define PBL_SIO_CH0		0x00
#define PBL_SIO_CM_CH0	0x40

#define DEBUG_SIO  0
#define DEBUG_TEST_SIO  0

typedef enum {
	PBL_SIO_BRATE_2048	= 2048,
	PBL_SIO_BRATE_4096	= 4096,
	PBL_SIO_BRATE_8192	= 8192,
	PBL_SIO_BRATE_16384	= 16384,
	PBL_SIO_BRATE_32K	= 32000,
	PBL_SIO_BRATE_64K	= 64000,
	PBL_SIO_BRATE_128K	= 128000,
	PBL_SIO_BRATE_256K	= 256000,
	PBL_SIO_BRATE_512K	= 512000,
	PBL_SIO_BRATE_780K	= 780000,
	PBL_SIO_BRATE_800K	= 800000,
	PBL_SIO_BRATE_975K	= 975000,
	PBL_SIO_BRATE_1000K	= 1000000,
	PBL_SIO_BRATE_1250K	= 1250000,
	PBL_SIO_BRATE_1264K	= 1263158,
	PBL_SIO_BRATE_1500K	= 1500000,
	PBL_SIO_BRATE_1750K	= 1750000,
	PBL_SIO_BRATE_2000K	= 2000000,
	PBL_SIO_BRATE_2250K	= 2250000,
	PBL_SIO_BRATE_2500K	= 2500000,
	PBL_SIO_BRATE_2750K	= 2750000,
	PBL_SIO_BRATE_3000K	= 3000000,
	PBL_SIO_BRATE_3250K	= 3250000,
	PBL_SIO_BRATE_3300K	= 3300000,
	PBL_SIO_BRATE_3500K	= 3500000,
	PBL_SIO_BRATE_3750K	= 3750000,
	PBL_SIO_BRATE_4000K	= 4000000,
	PBL_SIO_BRATE_5500K	= 5500000,
	PBL_SIO_BRATE_6500K	= 6500000,
	PBL_SIO_BRATE_8000K	= 8000000,
	PBL_SIO_BRATE_8250K	= 8250000,
	PBL_SIO_BRATE_9750K	= 9750000,
	PBL_SIO_BRATE_12M	= 12000000,
} PBL_SIO_BRATE;

typedef enum {
	PBL_SIO_LMS_LSB = 0,
	PBL_SIO_LMS_MSB = 1,
} PBL_SIO_LMS;

typedef enum {
	PBL_SIO_IMOD_EN = 0,
	PBL_SIO_IMOD_DIS = 1,
} PBL_SIO_IMOD;

typedef enum {
	PBL_SIO_ICK_X16 = 0,
	PBL_SIO_ICK_X32 = 1,
	PBL_SIO_ICK_X64 = 2,
	PBL_SIO_ICK_X128 = 3,
} PBL_SIO_ICK;

typedef enum {
	PBL_SIO_RTMOD_NORMAL = 0,
	PBL_SIO_RTMOD_AUTO = 1,
} PBL_SIO_RTMOD;

typedef enum {
	PBL_SIO_BUF_TX = 0,
	PBL_SIO_BUF_RX = 1,
} PBL_SIO_BUF;

typedef enum {
	PBL_OK = 0,
	PBL_DUPLICATE_OPEN_ERR = -1,
	PBL_NOT_OPEN_ERR = -2,
	PBL_HW_BUSY_ERR = -3,
	PBL_BRATE_ERR = -4,
	PBL_NOT_SET = -5,
	PBL_TRANSFER_FAILED = -6,
	PBL_HW_WAIT_TMOUT = -7,
	PBL_AIF_ADR_ERR = -8,
	PBL_DATA_ERR = -9,
	PBL_HW_ADR_ERR = -10,
	PBL_HW_TMR_ERR = -11,
	PBL_STOP_COUNT_PARAM_ERR = -12,
	PBL_OTHER_ERR = -13,
	PBL_SIO_STS_OE = -14,
	PBL_SIO_STS_EXEC = -15,
	PBL_SIO_STS_END = -16,
} PBL_ER;

typedef enum {
	PBL_SIO_MOD_RX = 1,
	PBL_SIO_MOD_TX = 2,
	PBL_SIO_MOD_TXRX = 3,
} PBL_SIO_MOD;

typedef enum {
	PBL_SIO_CSOMOD_OFF = 0,
	PBL_SIO_CSOMOD_ON = 1,
} PBL_SIO_CSOMOD;

typedef enum {
	PBL_SIO_CSEL_INTNL = 0,
	PBL_SIO_CSEL_EXTNL = 1,
} PBL_SIO_CSEL;

typedef enum {
	PBL_SIO_CSEN_INTNL = 0,
	PBL_SIO_CSEN_EXTNL = 1,
} PBL_SIO_CSEN;

typedef enum {
	PBL_SIO_INT_TRAN_END = 0,
	PBL_SIO_INT_OE_ERR = 1,
	PBL_SIO_INT_CS_CANCEL_ERR = 2,
} PBL_FACT;

typedef enum {
	PBL_SIO_CSSEL_CS0 = 0,
	PBL_SIO_CSSEL_CS1,
	PBL_SIO_CSSEL_CS2,
} PBL_SIO_CSSEL;

typedef struct {
	PBL_SIO_BRATE brate;
	PBL_SIO_LMS lms;
	PBL_SIO_CSEL csel;
	PBL_SIO_CSEN csen;
	PBL_SIO_IMOD imod;
	PBL_SIO_ICK ick;
	PBL_SIO_RTMOD rtmod;
	PBL_SIO_CSOMOD csomod;
	PBL_SIO_CSSEL cssel;
	uint16_t siockst;
	uint16_t sioick;
	uint16_t sioidly;
	uint16_t siocsint;
	bool siocksten;
	bool sioicken;
	bool sioidlyen;
	bool siopol;
} PBL_SIO_INFO;

typedef struct {
	PBL_SIO_MOD mode;
	uint16_t num;
	uint16_t cscnt;
} PBL_SIO_START_INFO;

struct sio_xfer {
	void *tx;
	void *rx;
	int count;
};


typedef void (*PBL_FUNC)(PBL_FACT arg);

PBL_ER pbl_sio_open(const uint32_t ch);
PBL_ER pbl_sio_close(const uint32_t ch);
PBL_ER pbl_sio_set_func(const uint32_t ch, const PBL_SIO_INFO *info, PBL_FUNC fp);
int32_t pbl_sio_write_buffer(const uint32_t ch, const char *wbuf, const size_t len);
int32_t pbl_sio_read_buffer(const uint32_t ch, const char *rbuf, const size_t len);
PBL_ER pbl_sio_start(const uint32_t ch, const PBL_SIO_START_INFO *start_info);
PBL_ER pbl_sio_get_status(const uint32_t ch);
PBL_ER pbl_sio_chk_buffer(const uint32_t ch, const uint32_t buf_type);
PBL_ER pbl_sio_clr_buffer(const uint32_t ch);
#endif /* __SIO_LIN_H__ */
