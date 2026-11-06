/* SPDX-License-Identifier:     GPL-2.0 */
/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */
/** @file
 * LDEC Driver internal header
*/

#ifndef __LDEC_DRV_H__
#define __LDEC_DRV_H__


#ifdef __cplusplus
extern "C" {
#endif

/* VERSION DEFINITION */
#define LDEC_VERSION 		"1.1"				/**< Version Number */

/* Base address of LDEC SLAVE space */
#define LDEC_MAX_SIZE		(4096)				/**< Max size */
#define LDEC_MAX_RECORDS	(0x1FFFU)			/**< maximum compressed record number(8191) */
#define LDEC_MAX_RECORD_SIZE	(4096)			/**< maximum record size(4KB) */
#define LDEC_ADDR_CHECK		(0x1FU)				/*for alignment check */
#define LDEC_COOKIE		(0x29AB87F4)			/*cookie used in DMAC transfer */
#define LDEC_CPU_TRANS_SIZE	(4U)                /*CPU transfer size(4Byte/) */

#ifdef CONFIG_ARCH_CXD90XXX_FPGA	//FPGA or not(ES), defined by kernel configure
#define LDEC_USE_FPGA
#endif

	
#ifndef LDEC_USE_FPGA
#define LDEC_BUSCLEAN_CHK_TIME  1				/* period for bus request status check (ES) */
#else
#define LDEC_BUSCLEAN_CHK_TIME  30				/* period for bus request status check (FPGA)  */
#endif

#define LDEC_BUSCLEAN_CHK_NUM   2				/* number of bus request status check */
  
/**
 * @brief ldec transfer setting structure
*/


typedef struct {
	struct page **pages;	/**< array of page start address */
	uint32_t nr_pages;	/**< number of pages */
	uint64_t addr;	/**< source transfer address */
	uint32_t len;	/**< data size */
	uint32_t vmalloc_flg;	/** 1: vmalloc allocation, 0:pre-allocated */
}ldec_trans_t;

/**
 * @brief dmac transfer setting structure
*/
typedef struct {
	uint64_t dst;						/**< distination address */
	uint64_t src;						/**< source address */
	uint32_t size;						/**< data size */
	uint32_t trans_size;					/**< transfered data size */
}trans_t;

/* utility function*/
#define ldec_howmany(_x, _y)	(uint32_t)(((uint64_t)((uint32_t)(_x)) + (((uint32_t)(_y)) - 1u)) / ((uint32_t)(_y)))            /**< x: block number (y: block length) */


static inline void ldec_mutex_init(struct mutex *mutex){
		mutex_init(mutex);
}

#define ldec_mutex_lock(mutex)	{	\
	mutex_lock ( mutex );		\
}
#define ldec_mutex_unlock(mutex)	{	\
	mutex_unlock ( mutex );		\
}

static inline void ldec_spin_lock_init(spinlock_t *spinlock){
	spin_lock_init( spinlock );
}

#define ldec_spin_lock_irqsave(spinlock,flags)	{	\
	spin_lock_irqsave ( spinlock,flags );		\
}

#define ldec_spin_unlock_irqrestore(spinlock,flags)	{	\
	spin_unlock_irqrestore ( spinlock,flags );		\
}

#ifdef LDEC_LOCK_TIMES
#define ldec_get_ldec_state(result,s_time,e_time)       \
        do {                                                                    \
	  unsigned long flags = 0;					\
                ldec_spin_lock_irqsave( &ldec_state_lock, flags ); /* lock start */     \
                ktime_get_real_ts64(&s_time);/* measurement start */                     \
                result = ldec_state;                                            \
                ktime_get_real_ts64(&e_time);/* measurement end */                     \
                ldec_spin_unlock_irqrestore( &ldec_state_lock, flags );/* lock end */ \
} while (0)
#define ldec_set_ldec_state(state,s_time,e_time)       \
        do {                                                                    \
	  unsigned long flags = 0;					\
                ldec_spin_lock_irqsave( &ldec_state_lock, flags ); /* lock start */     \
                ktime_get_real_ts64(&s_time);/* measurement start */                     \
                ldec_state = state; \
                ktime_get_real_ts64(&e_time);/*measurement end */                     \
                ldec_spin_unlock_irqrestore( &ldec_state_lock, flags );/* lock end */ \
} while (0)

#else /* LDEC_LOCK_TIMES */
#define ldec_get_ldec_state(result)     \
        do { \
                unsigned long flags = 0; \
                ldec_spin_lock_irqsave( &ldec_state_lock, flags ); /* lock start */ \
                result = ldec_state; \
                ldec_spin_unlock_irqrestore( &ldec_state_lock, flags );/* lock end */ \
} while (0)

#define ldec_set_ldec_state(state)     \
        do { \
                unsigned long flags = 0; \
                ldec_spin_lock_irqsave( &ldec_state_lock, flags ); /* lock start */ \
                ldec_state = state; \
                ldec_spin_unlock_irqrestore( &ldec_state_lock, flags );/* lock end */ \
} while (0)


#endif /* LDEC_LOCK_TIMES */

#ifdef __cplusplus 
}
#endif
#endif /* #ifndef __LDEC_DRV_H__ */
/*---------------------------------------------------------------------------
  END
---------------------------------------------------------------------------*/
