/* SPDX-License-Identifier:     GPL-2.0 */
/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */
/** @file
 * register structure
*/

#ifndef __LDEC_REG_H__
#define __LDEC_REG_H__

#ifdef __cplusplus
extern "C" {
#endif

/***********************************/
/* Register address definition     */
/***********************************/

/* ==================================================================== */
/* LZDECOMP Register */
/**
 * @brief LDEC Register DECMODE register structure
*/
typedef struct {
    uint32_t       DATA;          /**< DATA */
} LZDECOMP_UN_DECMODE ;

/**
 * @brief LDEC Register START register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_START ;

/**
 * @brief LDEC Register TIMEOUT register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_TIMEOUT ;

/**
 * @brief LDEC Register RECORDS register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_RECORDS ;

/**
 * @brief LDEC Register DESTADDR register structure
*/
typedef struct {
    uint32_t        DATAL;          /**< DATA */
    uint32_t        DATAH;
} LZDECOMP_UN_DESTADDR ;

/**
 * @brief LDEC Register CURRADDR register structure
*/
typedef struct {
    uint32_t        DATAL;          /**< DATA */
    uint32_t        DATAH;
} LZDECOMP_UN_CURRADDR ;

/**
 * @brief LDEC Register BUSCLEAN register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_BUSCLEAN ;

/**
 * @brief LDEC Register INTEN register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_INTEN ;

/**
 * @brief LDEC Register INTMASK register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_INTMSK ;

/**
 * @brief LDEC Register INTCLEAR register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_INTCLR ;

/**
 * @brief LDEC Register INT register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_INT ;

/**
 * @brief LDEC Register INTRAW register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_INTRAW ;

/**
 * @brief LDEC Register SRAM buffer control register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_SRAMLIM ;

/**
 * @brief LDEC Register CMDQUE control register structure
*/
typedef struct {
    uint32_t        DATA;          /**< DATA */
} LZDECOMP_UN_CMDQUELIM ;


/* ==================================================================== */
/* IO definition */
#define __I     volatile const              /**< read only   */
#define __O     volatile                    /**< write only  */
#define __IO    volatile                    /**< read / write */

/* ==================================================================== */

/*==============================================================================================*/
/* definition name : LZDECOMP Register                                                                   */
/* function:                                                                                     */
/* remarks:                                                                                     */
/* history:                                                                                     */
/*==============================================================================================*/
/**
 * @brief LDEC Register group structure
*/
typedef struct {
    __IO LZDECOMP_UN_DECMODE                            LZDECOMP_DECMODE        ; /**< 0x00000000 */
    __IO LZDECOMP_UN_START                              LZDECOMP_START          ; /**< 0x00000004 */
    __IO LZDECOMP_UN_TIMEOUT                            LZDECOMP_TIMEOUT        ; /**< 0x00000008 */
    __IO LZDECOMP_UN_RECORDS                            LZDECOMP_RECORDS        ; /**< 0x0000000C */
    __IO LZDECOMP_UN_DESTADDR                           LZDECOMP_DESTADDR       ; /**< 0x00000010 */
    __IO LZDECOMP_UN_CURRADDR                           LZDECOMP_CURRADDR       ; /**< 0x00000018 */
    uint32_t                                            __res0[1]               ; /**< 0x00000020 */
    __IO LZDECOMP_UN_BUSCLEAN                           LZDECOMP_BUSCLEAN       ; /**< 0x00000024 */
    __IO LZDECOMP_UN_INTEN                              LZDECOMP_INTEN          ; /**< 0x00000028 */
    __IO LZDECOMP_UN_INTMSK                             LZDECOMP_INTMSK         ; /**< 0x0000002C */
    __IO LZDECOMP_UN_INTCLR                             LZDECOMP_INTCLR         ; /**< 0x00000030 */
    __IO LZDECOMP_UN_INT                                LZDECOMP_INT            ; /**< 0x00000034 */
    __IO LZDECOMP_UN_INTRAW                             LZDECOMP_INTRAW         ; /**< 0x00000038 */
    uint32_t                                            __res1[1]               ; /**< 0x0000003C */
    __IO LZDECOMP_UN_SRAMLIM                            LZDECOMP_SRAMLIM        ; /**< 0x00000040 */
    __IO LZDECOMP_UN_CMDQUELIM                          LZDECOMP_SMDQUELIM      ; /**< 0x00000044 */
} LZDECOMP_T;


#ifdef __cplusplus
}
#endif
#endif /* #ifndef __LDEC_REG_H__ */

/*---------------------------------------------------------------------------
  END
---------------------------------------------------------------------------*/
