/* SPDX-License-Identifier:     GPL-2.0 */
/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */
/** @file
 * LDEC Driver API header
*/

#ifndef __LDEC_DRIVER_H__
#define __LDEC_DRIVER_H__


#ifdef __cplusplus
extern "C" {
#endif

/* definition of start decompress command */
#define LDEC_DECOMPRESS     (1U)  /**< DDR to DDR LZ77 decompression (ioctl command) */

/* structure */
/**
 * @brief ldec_decompress structure
 * 
 * LZ77 decompress request
*/
typedef struct ldec_decompress{
	void*        virt;          /**< virtual address for compressed data */
	uint64_t     dst_phys;      /**< physical address for decompressed data */
	uint32_t     srclen;        /**< size of compressed data */
	uint32_t     dstlen;        /**< size of decompressed data */
	uint32_t     records;       /**< record number of compressed data */
	uint8_t       ch;            /**< DMAC channel number used for LDEC */
	uint8_t      xsrcflush;     /**< cache flush for compressed data is needed or not */
	uint8_t      xdstflush;     /**< cache invalidate for decompressed data is needed or not */
	uint8_t    __reserve[1];    /**< reserved */
}ldec_decompress_t;

#ifdef __cplusplus 
}
#endif
#endif /* #ifndef __LDEC_DRIVER_H__ */
/*---------------------------------------------------------------------------
  END
---------------------------------------------------------------------------*/
