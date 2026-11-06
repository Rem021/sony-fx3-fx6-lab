/*
 * Cache maintenance
 *
 * Copyright (C) 2001 Deep Blue Solutions Ltd.
 * Copyright (C) 2012 ARM Ltd.
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License version 2 as
 * published by the Free Software Foundation.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <linux/errno.h>
#include <linux/linkage.h>
#include <linux/init.h>
#include <asm/assembler.h>
#include <asm/cpufeature.h>
#include <asm/alternative.h>

/*
 *	flush_icache_range(start,end)
 *
 *	Ensure that the I and D caches are coherent within specified region.
 *	This is typically used when code has been written to a memory region,
 *	and will be executed.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
ENTRY(flush_icache_range)
	/* FALLTHROUGH */

/*
 *	__flush_cache_user_range(start,end)
 *
 *	Ensure that the I and D caches are coherent within specified region.
 *	This is typically used when code has been written to a memory region,
 *	and will be executed.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
ENTRY(__flush_cache_user_range)
	dcache_line_size x2, x3
	sub	x3, x2, #1
	bic	x4, x0, x3
1:
user_alt 9f, "dc cvau, x4",  "dc civac, x4",  ARM64_WORKAROUND_CLEAN_CACHE
	add	x4, x4, x2
	cmp	x4, x1
	b.lo	1b
	dsb	ish

	icache_line_size x2, x3
	sub	x3, x2, #1
	bic	x4, x0, x3
1:
USER(9f, ic	ivau, x4	)		// invalidate I line PoU
	add	x4, x4, x2
	cmp	x4, x1
	b.lo	1b
	dsb	ish
	isb
	mov	x0, #0
	ret
9:
	mov	x0, #-EFAULT
	ret
ENDPROC(flush_icache_range)
ENDPROC(__flush_cache_user_range)

/*
 *	__flush_dcache_area(kaddr, size)
 *
 *	Ensure that any D-cache lines for the interval [kaddr, kaddr+size)
 *	are cleaned and invalidated to the PoC.
 *
 *	- kaddr   - kernel address
 *	- size    - size in question
 */
ENTRY(__flush_dcache_area)
	dcache_by_line_op civac, sy, x0, x1, x2, x3
	ret
ENDPIPROC(__flush_dcache_area)

/*
 *	__clean_dcache_area_pou(kaddr, size)
 *
 * 	Ensure that any D-cache lines for the interval [kaddr, kaddr+size)
 * 	are cleaned to the PoU.
 *
 *	- kaddr   - kernel address
 *	- size    - size in question
 */
ENTRY(__clean_dcache_area_pou)
	dcache_by_line_op cvau, ish, x0, x1, x2, x3
	ret
ENDPROC(__clean_dcache_area_pou)

/*
 *	__dma_inv_area(start, size)
 *	- start   - virtual start address of region
 *	- size    - size in question
 */
__dma_inv_area:
	add	x1, x1, x0
	/* FALLTHROUGH */

/*
 *	__inval_cache_range(start, end)
 *	- start   - start address of region
 *	- end     - end address of region
 */
ENTRY(__inval_cache_range)
	dcache_line_size x2, x3
	sub	x3, x2, #1
	tst	x1, x3				// end cache line aligned?
	bic	x1, x1, x3
	b.eq	1f
	dc	civac, x1			// clean & invalidate D / U line
1:	tst	x0, x3				// start cache line aligned?
	bic	x0, x0, x3
	b.eq	2f
	dc	civac, x0			// clean & invalidate D / U line
	b	3f
2:	dc	ivac, x0			// invalidate D / U line
3:	add	x0, x0, x2
	cmp	x0, x1
	b.lo	2b
	dsb	sy
	ret
ENDPIPROC(__inval_cache_range)
ENDPROC(__dma_inv_area)

/*
 *	__clean_dcache_area_poc(kaddr, size)
 *
 * 	Ensure that any D-cache lines for the interval [kaddr, kaddr+size)
 * 	are cleaned to the PoC.
 *
 *	- kaddr   - kernel address
 *	- size    - size in question
 */
ENTRY(__clean_dcache_area_poc)
	/* FALLTHROUGH */

/*
 *	__dma_clean_area(start, size)
 *	- start   - virtual start address of region
 *	- size    - size in question
 */
__dma_clean_area:
	dcache_by_line_op cvac, sy, x0, x1, x2, x3
	ret
ENDPIPROC(__clean_dcache_area_poc)
ENDPROC(__dma_clean_area)

/*
 *	__dma_flush_area(start, size)
 *
 *	clean & invalidate D / U line
 *
 *	- start   - virtual start address of region
 *	- size    - size in question
 */
ENTRY(__dma_flush_area)
	dcache_by_line_op civac, sy, x0, x1, x2, x3
	ret
ENDPIPROC(__dma_flush_area)

/*
 *	__dma_map_area(start, size, dir)
 *	- start	- kernel virtual start address
 *	- size	- size of region
 *	- dir	- DMA direction
 */
ENTRY(__dma_map_area)
	cmp	w2, #DMA_FROM_DEVICE
	b.eq	__dma_inv_area
	b	__dma_clean_area
ENDPIPROC(__dma_map_area)

/*
 *	__dma_unmap_area(start, size, dir)
 *	- start	- kernel virtual start address
 *	- size	- size of region
 *	- dir	- DMA direction
 */
ENTRY(__dma_unmap_area)
	cmp	w2, #DMA_TO_DEVICE
	b.ne	__dma_inv_area
	ret
ENDPIPROC(__dma_unmap_area)

/*
 *     v8_flush_dcache_louis()
 *
 *     Flush the D-cache up to the Level of Unification Inner Shareable
 */
ENTRY(v8_flush_dcache_louis)
	dmb	ish			// ensure ordering with previous memory accesses
	mrs	x0, clidr_el1		// read clidr, x0 = clidr
#ifdef CONFIG_SMP
	mov	x3, x0, lsr #20		// move LoUIS into bit[3..1]
#else
	mov	x3, x0, lsr #26		// move LoUU into bit[3..1]
#endif
	ands	x3, x3, #7 << 1 	// bit[3..0]=LoU*2
	bne	start_flush_levels	// if LoU != 0, start flushing
	ret
ENDPIPROC(v8_flush_dcache_louis)

/*
 *	v8_flush_dcache_all
 *
 */
ENTRY(v8_flush_dcache_all)
	dmb	osh			// ensure ordering with previous memory accesses
	mrs	x0, clidr_el1		// read clidr, x0 = clidr
	mov	x3, x0, lsr #23		// move LoC into bit[3..1]
	ands	x3, x3, #7 << 1		// bit[3..0]=LoC*2
	beq	finished		// if LoC is 0, then no need to clean
start_flush_levels:
	// x0 = clidr_el1
	// x3 = end of cache level*2
	// x10 = cache level*2
	mov	x10, #0			// start clean at cache level 0
flush_levels:
	add	x2, x10, x10, lsr #1	// work out 3x current cache level
	lsr	x1, x0, x2		// extract cache type bits from clidr
	and	x1, x1, #7		// mask of the bits for current cache only
	cmp	x1, #2			// see what cache we have at this level
	blt	skip			// skip if no cache, or just i-cache
#ifdef CONFIG_PREEMPT
	mrs	x9, daif		// local_irq_save
	disable_irq			// make cssr&csidr read atomic
#endif
	msr	csselr_el1, x10		// select current cache level in cssr
	isb				// isb to sych the new cssr&csidr
	mrs	x1, ccsidr_el1		// read the new csidr(32bit)
#ifdef CONFIG_PREEMPT
	msr	daif, x9		// local_irq_restore
#endif
	and	w2, w1, #7		// extract the length of the cache lines
	add	w2, w2, #4		// add 4 (line length offset)
	mov	w4, #0x3ff		// Way:10bit
	and	w4, w4, w1, lsr #3	// find maximum number on the way size
	clz	w5, w4			// find bit position of way size increment
	mov	w7, #0x7fff		// NumSets:15bit
	and	w7, w7, w1, lsr #13	// extract max number of the index size
loop1:
	mov	w9, w7			// create working copy of max index
loop2:
	mov	x11, xzr
	lsl	w11, w4, w5		// factor way into w11
	orr	w11, w11, w10		// factor cache number into w11
	lsl	w12, w9, w2		// index number
	orr	w11, w11, w12		// factor index number into w11
	dc	cisw, x11		// clean & invalidate by set/way
	subs	w9, w9, #1		// decrement the index
	bge	loop2
	subs	w4, w4, #1		// decrement the way
	bge	loop1
skip:
	add	x10, x10, #2		// increment cache number
	cmp	x3, x10
	bgt	flush_levels
finished:
	msr	csselr_el1, xzr		// swith back to cache level 0
	dsb	st
	isb
	ret
ENDPIPROC(v8_flush_dcache_all)

/*
 *	v8_inv_dcache_all
 *
 */
ENTRY(v8_inv_dcache_all)
	dmb	osh			// ensure ordering with previous memory accesses
	mrs	x0, clidr_el1		// read clidr, x0 = clidr
	mov	x3, x0, lsr #23		// move LoC into bit[3..1]
	ands	x3, x3, #7 << 1		// bit[3..0]=LoC*2
	beq	inv_finished		// if LoC is 0, then no need to inv
	// x0 = clidr_el1
	// x3 = end of cache level*2
	// x10 = cache level*2
	mov	x10, #0			// start clean at cache level 0
inv_levels:
	add	x2, x10, x10, lsr #1	// work out 3x current cache level
	lsr	x1, x0, x2		// extract cache type bits from clidr
	and	x1, x1, #7		// mask of the bits for current cache only
	cmp	x1, #2			// see what cache we have at this level
	blt	inv_skip		// skip if no cache, or just i-cache
#ifdef CONFIG_PREEMPT
	mrs	x9, daif		// local_irq_save
	disable_irq			// make cssr&csidr read atomic
#endif
	msr	csselr_el1, x10		// select current cache level in cssr
	isb				// isb to sych the new cssr&csidr
	mrs	x1, ccsidr_el1		// read the new csidr(32bit)
#ifdef CONFIG_PREEMPT
	msr	daif, x9		// local_irq_restore
#endif
	and	w2, w1, #7		// extract the length of the cache lines
	add	w2, w2, #4		// add 4 (line length offset)
	mov	w4, #0x3ff		// Way:10bit
	and	w4, w4, w1, lsr #3	// find maximum number on the way size
	clz	w5, w4			// find bit position of way size increment
	mov	w7, #0x7fff		// NumSets:15bit
	and	w7, w7, w1, lsr #13	// extract max number of the index size
inv_loop1:
	mov	w9, w7			// create working copy of max index
inv_loop2:
	mov	x11, xzr
	lsl	w11, w4, w5		// factor way into w11
	orr	w11, w11, w10		// factor cache number into w11
	lsl	w12, w9, w2		// index number
	orr	w11, w11, w12		// factor index number into w11
	dc	isw, x11		// invalidate by set/way
	subs	w9, w9, #1		// decrement the index
	bge	inv_loop2
	subs	w4, w4, #1		// decrement the way
	bge	inv_loop1
inv_skip:
	add	x10, x10, #2		// increment cache number
	cmp	x3, x10
	bgt	inv_levels
inv_finished:
	msr	csselr_el1, xzr		// swith back to cache level 0
	dsb	st
	isb
	ret
ENDPIPROC(v8_inv_dcache_all)
