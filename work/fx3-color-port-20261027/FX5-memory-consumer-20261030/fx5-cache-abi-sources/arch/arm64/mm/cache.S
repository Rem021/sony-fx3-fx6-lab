/* SPDX-License-Identifier: GPL-2.0-only */
/*
 * Cache maintenance
 *
 * Copyright (C) 2001 Deep Blue Solutions Ltd.
 * Copyright (C) 2012 ARM Ltd.
 */

#include <linux/errno.h>
#include <linux/linkage.h>
#include <linux/init.h>
#include <asm/assembler.h>
#include <asm/cpufeature.h>
#include <asm/alternative.h>
#include <asm/asm-uaccess.h>

/*
 *	caches_clean_inval_pou_macro(start,end) [fixup]
 *
 *	Ensure that the I and D caches are coherent within specified region.
 *	This is typically used when code has been written to a memory region,
 *	and will be executed.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 *	- fixup   - optional label to branch to on user fault
 */
.macro	caches_clean_inval_pou_macro, fixup
alternative_if ARM64_HAS_CACHE_IDC
	dsb     ishst
	b       .Ldc_skip_\@
alternative_else_nop_endif
	mov     x2, x0
	mov     x3, x1
	dcache_by_line_op cvau, ish, x2, x3, x4, x5, \fixup
.Ldc_skip_\@:
alternative_if ARM64_HAS_CACHE_DIC
	isb
	b	.Lic_skip_\@
alternative_else_nop_endif
	invalidate_icache_by_line x0, x1, x2, x3, \fixup
.Lic_skip_\@:
.endm

/*
 *	caches_clean_inval_pou(start,end)
 *
 *	Ensure that the I and D caches are coherent within specified region.
 *	This is typically used when code has been written to a memory region,
 *	and will be executed.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
SYM_FUNC_START(caches_clean_inval_pou)
	caches_clean_inval_pou_macro
	ret
SYM_FUNC_END(caches_clean_inval_pou)

/*
 *	caches_clean_inval_user_pou(start,end)
 *
 *	Ensure that the I and D caches are coherent within specified region.
 *	This is typically used when code has been written to a memory region,
 *	and will be executed.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
SYM_FUNC_START(caches_clean_inval_user_pou)
	uaccess_ttbr0_enable x2, x3, x4

	caches_clean_inval_pou_macro 2f
	mov	x0, xzr
1:
	uaccess_ttbr0_disable x1, x2
	ret
2:
	mov	x0, #-EFAULT
	b	1b
SYM_FUNC_END(caches_clean_inval_user_pou)

/*
 *	icache_inval_pou(start,end)
 *
 *	Ensure that the I cache is invalid within specified region.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
SYM_FUNC_START(icache_inval_pou)
alternative_if ARM64_HAS_CACHE_DIC
	isb
	ret
alternative_else_nop_endif

	invalidate_icache_by_line x0, x1, x2, x3
	ret
SYM_FUNC_END(icache_inval_pou)

/*
 *	dcache_clean_inval_poc(start, end)
 *
 *	Ensure that any D-cache lines for the interval [start, end)
 *	are cleaned and invalidated to the PoC.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
SYM_FUNC_START_PI(dcache_clean_inval_poc)
	dcache_by_line_op civac, sy, x0, x1, x2, x3
	ret
SYM_FUNC_END_PI(dcache_clean_inval_poc)

/*
 *	dcache_clean_pou(start, end)
 *
 * 	Ensure that any D-cache lines for the interval [start, end)
 * 	are cleaned to the PoU.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
SYM_FUNC_START(dcache_clean_pou)
alternative_if ARM64_HAS_CACHE_IDC
	dsb	ishst
	ret
alternative_else_nop_endif
	dcache_by_line_op cvau, ish, x0, x1, x2, x3
	ret
SYM_FUNC_END(dcache_clean_pou)

/*
 *	dcache_inval_poc(start, end)
 *
 * 	Ensure that any D-cache lines for the interval [start, end)
 * 	are invalidated. Any partial lines at the ends of the interval are
 *	also cleaned to PoC to prevent data loss.
 *
 *	- start   - kernel start address of region
 *	- end     - kernel end address of region
 */
SYM_FUNC_START_LOCAL(__dma_inv_area)
SYM_FUNC_START_PI(dcache_inval_poc)
	/* FALLTHROUGH */

/*
 *	__dma_inv_area(start, end)
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
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
SYM_FUNC_END_PI(dcache_inval_poc)
SYM_FUNC_END(__dma_inv_area)

/*
 *	dcache_clean_poc(start, end)
 *
 * 	Ensure that any D-cache lines for the interval [start, end)
 * 	are cleaned to the PoC.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
SYM_FUNC_START_LOCAL(__dma_clean_area)
SYM_FUNC_START_PI(dcache_clean_poc)
	/* FALLTHROUGH */

/*
 *	__dma_clean_area(start, end)
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
	dcache_by_line_op cvac, sy, x0, x1, x2, x3
	ret
SYM_FUNC_END_PI(dcache_clean_poc)
SYM_FUNC_END(__dma_clean_area)

/*
 *	dcache_clean_pop(start, end)
 *
 * 	Ensure that any D-cache lines for the interval [start, end)
 * 	are cleaned to the PoP.
 *
 *	- start   - virtual start address of region
 *	- end     - virtual end address of region
 */
SYM_FUNC_START_PI(dcache_clean_pop)
	alternative_if_not ARM64_HAS_DCPOP
	b	dcache_clean_poc
	alternative_else_nop_endif
	dcache_by_line_op cvap, sy, x0, x1, x2, x3
	ret
SYM_FUNC_END_PI(dcache_clean_pop)

/*
 *	__dma_flush_area(start, size)
 *
 *	clean & invalidate D / U line
 *
 *	- start   - virtual start address of region
 *	- size    - size in question
 */
SYM_FUNC_START_PI(__dma_flush_area)
	add	x1, x0, x1
	dcache_by_line_op civac, sy, x0, x1, x2, x3
	ret
SYM_FUNC_END_PI(__dma_flush_area)

/*
 *	__dma_map_area(start, size, dir)
 *	- start	- kernel virtual start address
 *	- size	- size of region
 *	- dir	- DMA direction
 */
SYM_FUNC_START_PI(__dma_map_area)
	add	x1, x0, x1
	b	__dma_clean_area
SYM_FUNC_END_PI(__dma_map_area)

/*
 *	__dma_unmap_area(start, size, dir)
 *	- start	- kernel virtual start address
 *	- size	- size of region
 *	- dir	- DMA direction
 */
SYM_FUNC_START_PI(__dma_unmap_area)
	add	x1, x0, x1
	cmp	w2, #DMA_TO_DEVICE
	b.ne	__dma_inv_area
	ret
SYM_FUNC_END_PI(__dma_unmap_area)

/*
 *     v8_flush_dcache_louis()
 *
 *     Flush the D-cache up to the Level of Unification Inner Shareable
 */
SYM_FUNC_START_PI(v8_flush_dcache_louis)
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
SYM_FUNC_END_PI(v8_flush_dcache_louis)

/*
 *	v8_flush_dcache_all
 *
 */
SYM_FUNC_START_PI(v8_flush_dcache_all)
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
	save_and_disable_irq x9		// make cssr&csidr read atomic
#endif
	msr	csselr_el1, x10		// select current cache level in cssr
	isb				// isb to sych the new cssr&csidr
	mrs	x1, ccsidr_el1		// read the new csidr(32bit)
#ifdef CONFIG_PREEMPT
	restore_irq x9			// local_irq_restore
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
SYM_FUNC_END_PI(v8_flush_dcache_all)

/*
 *	v8_inv_dcache_all
 *
 */
SYM_FUNC_START_PI(v8_inv_dcache_all)
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
	save_and_disable_irq x9		// make cssr&csidr read atomic
#endif
	msr	csselr_el1, x10		// select current cache level in cssr
	isb				// isb to sych the new cssr&csidr
	mrs	x1, ccsidr_el1		// read the new csidr(32bit)
#ifdef CONFIG_PREEMPT
	restore_irq x9			// local_irq_restore
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
SYM_FUNC_END_PI(v8_inv_dcache_all)
