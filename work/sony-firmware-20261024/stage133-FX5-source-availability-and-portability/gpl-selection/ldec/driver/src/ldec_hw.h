/* SPDX-License-Identifier:     GPL-2.0 */
/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */
/** @file
 * LDEC Driver LDEC control header file
*/

#ifndef __LDEC_HW_H__
#define __LDEC_HW_H__

#include "ldec_debug.h"

#ifdef __cplusplus
extern "C" {
#endif

/********************************************************/
/* LZ77DEC definition(Decomp function specification)                  */
/********************************************************/
#define LZDECOMP_SRAM_ACCESS_ENABLE         (0x110U)           /*SRAM ENABLE*/
#define LZDECOMP_INTEN_ENABLE_RESET         (0x7FU)            /*interrupt enable setting*/
#define LZDECOMP_EXCEPT_TIMEOUT             (0x7BU)            /*except timeout*/
#define LZDECOMP_RESET                      (1U)               /*software reset*/
#define LZDECOMP_RESET_RELEASE              (0U)               /*start Decomp macro*/
#define LZDECOMP_EXTRA                      (0U)               /*Decompression mode*/
#define LZDECOMP_TIMEOUT_MASK               (0x04U)            /*only tiomeout*/
#define LDEC_BUS_RELEASE                    (0x01U)
#define LDEC_REQUEST                        (0x02U)
#define LZDECOMP_INTCLR_ALLCLR		    (0x7FU)            /*clear all causes of interrupts*/
#define LZDECOMP_INTMSK_ALLMSK		    (0x7FU)            /*mask all interrupts*/
#define LZDECOMP_INTMSK_ALLUNMSK		    (0x00U)            /*unmask all interrupts*/
#define LZDECOMP_INTEN_ALLDISABLE	    (0x0U)		/*disable all interrupts*/

#define LZDECOMP_SRAMLIM_INIT	    (0x00FC00FBU)		/*initial value for SRAM buffer control register*/
#define LZDECOMP_CMDQUELIM_INIT	    (0x00000808U)		/*initial value for CMD QUE control register*/

  
#define LDEC_TIMER_MAX                      (60000000U)       /* timeout period(60 seconds) */
#define DMAC_TIMER_MAX                      (60000000U)       /* DMAC transfer tiomeout period(60 seconds)*/
#define LDEC_TIMEOUT_TIME                   (0xFFFFFU)          /* timeout period(0xFFFFF) */
//max value(0xFFFFF) means 1.352s according to the register specification

#define LDEC_LOWER_ADDR_MASK                (0xFFFFFFFFU)     /*for Lower address mask*/
#define LDEC_CHECK_ALIGN                    (0x1FU)           /*for 32byte alignment check*/


#define LZ77DEC_SUCCESS                     (0x00000001)       /**< SUCCESS */
#define LZ77DEC_BUSERR                      (0x00000040)       /**< BUSERROR */
#define LZ77DEC_INIT                        (0U)
#define LZ77DEC_TIMEOUT                     (0x00000004)       /**< TIMEOUT */

/* ldec_mutex definition */
#define LDEC_LOCK                           (1U)               /*LDEC_LOCK   */
#define LDEC_UNLOCK                         (0U)               /*LDEC_UNLOCK */
#define LDECHW_ENABLE                       (1U)               /*LDECHW generic definition Enable */
#define LDECHW_DISABLE                      (0U)               /*LDECHW generic definition Disable */
#define LDECHW_FLG_ON                       (1U)               /*LDECHW generic definition ON */
#define LDECHW_FLG_OFF                      (0U)               /*LDECHW generic definition OFF */
#define LDECHW_OK                           (0U)               /*LDECHW generic definition OK */
#define LDECHW_NG                           (1U)               /*LDECHW generic definition NG */
#define LDEC_TIMER_US                       (1000000U)         /*timer setting value*/
/*
 * error log output definition(Always valid)
 */
#define ldec_sys_err_printk(fmt, ...)   ldec_print( LDEC_DEBUG_ERROR, "[LDEC] %s() line %d: " fmt, __FUNCTION__, __LINE__, ##__VA_ARGS__)

/*
	* error log output definition(valid in DEBUG)
 */
#ifdef LDEC_DRV_API_ERR_ON
#define ldec_api_err_printk(fmt, ...)   ldec_print( LDEC_DEBUG_ERROR, "%s() line %d: " fmt, __FUNCTION__, __LINE__, ##__VA_ARGS__)
#else
#define ldec_api_err_printk(fmt, ...)   /**< no processing */
#endif /* #ifdef LDEC_DRV_API_ERR_ON */

/*
	* debug log output definition(valid in DEBUG)
 */
#ifdef LDEC_DRV_FUNC_LOG_ON
/* if log output is enabled */
#define fsrt_printk(b)                  ldec_print(LDEC_DEBUG_INFO, "CALL %s %s(%d)\n",(b),__FUNCTION__,__LINE__)                /**<  */
#define fend_printk(b,r)                ldec_print(LDEC_DEBUG_INFO, "CALL %s %s(%d) ret:%d \n",(b),__FUNCTION__,__LINE__,(r))    /**<  */
#define ldec_printk(format, args...)    ldec_print(LDEC_DEBUG_INFO, "LDEC_DEBUG: " format, ##args)
/* to here*/
#else
/* for release */
#define fsrt_printk(b)                  /**< no processing */
#define fend_printk(b,r)                /**< no processing */
#define ldec_printk(format, args...)    /**< no processing */
/* to here */
#endif

#define ldec_assert_NULL(b)                                                     \
	if ((b) == NULL){                                                           \
		ldec_print(LDEC_DEBUG_ERROR, " %s(%d) %p *** ASSERT \n",__FILE__,__LINE__,(b)); \
	}   /**< */


#ifdef __cplusplus                                  /* __cplusplus macro */
}                                                   /* to here linkage setting C languge */
#endif /* #ifdef __cplusplus */
#endif /* #ifndef __LDEC_HW_LDEC_H__ */

/*---------------------------------------------------------------------------
  END
---------------------------------------------------------------------------*/
