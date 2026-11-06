/*
 * noncache.h
 *
 * Physical address / Virtual address converter
 *
 * Copyright 2022 Sony Corporation
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

#ifndef __MACH_CXD90XXX_INCLUDE_MACH_NONCACHE_H
#define __MACH_CXD90XXX_INCLUDE_MACH_NONCACHE_H
/*
 * NAME
 * 	PHYS_TO_NONCACHE, PHYS_TO_CACHE, PHYS_TO_VA
 *		- Convert physical address to kernel address
 *
 * SYNOPSIS
 *	#include <mach/noncache.h>
 *	uintptr_t PHYS_TO_NONCACHE(phys_addr_t);
 *	uintptr_t PHYS_TO_CACHE(phys_addr_t);
 *	uintptr_t PHYS_TO_VA(phys_addr_t);
 * INPUT
 *	Physical address of DDR, eSRAM.
 * RETURN VALUE
 *	PHYS_TO_NONCACHE: Noncacheable kernel address
 *	PHYS_TO_CACHE:    Cacheable kernel address
 *	PHYS_TO_VA:       Kernel address
 *
 *	If input is out of range, PA2NC_ERR shall be returned.
 *
 * note
 *   Prefix PA2NC_ means Physical Address TO NonCacheable address.
 */
/*
 * NAME
 * 	VA_TO_PHYS - Convert virtual address to physical address
 *
 * SYNOPSIS
 *	#include <mach/noncache.h>
 *	phys_addr_t VA_TO_PHYS(uintptr_t);
 * INPUT
 *	Kernel address of DDR, eSRAM.
 * RETURN VALUE
 *	Physical address
 *
 *	If input is out of range, PA2NC_ERR shall be returned.
 *
 */
/*
 * NAME
 * 	VA_TO_NONCACHE, VA_TO_CACHE
 *		- Convert virtual address to virtual address
 *
 * SYNOPSIS
 *	#include <mach/noncache.h>
 *	uintptr_t VA_TO_NONCACHE(uintptr_t);
 *	uintptr_t VA_TO_CACHE(uintptr_t);
 * INPUT
 *	Kernel address of DDR, eSRAM.
 * RETURN VALUE
 *	VA_TO_NONCACHE: Noncacheable kernel address
 *	VA_TO_CACHE:    Cacheable kernel address
 *
 *	If input is out of range, PA2NC_ERR shall be returned.
 *
 */
/*
 * NAME
 * 	PHYS_TO_MEMTYPE, VA_TO_MEMTYPE
 *		- get memory type of address
 *
 * SYNOPSIS
 *	#include <mach/noncache.h>
 *	int PHYS_TO_MEMTYPE(phys_addr_t);
 *	int VA_TO_MEMTYPE(uintptr_t);
 * INPUT
 *	PHYS_TO_MEMTYPE: Physical address of DDR, eSRAM.
 *	VA_TO_MEMTYPE:   Kernel address of DDR, eSRAM.
 * RETURN VALUE
 *	PA2NC_DDRA	when DDR_A
 *	PA2NC_DDRB	when DDR_B
 *	PA2NC_ESRAM	when eSRAM
 *	PA2NC_ERR	when illegal input
 *
 */
/*
 * NAME
 * 	PHYS_TO_CACHETYPE, VA_TO_CACHETYPE
 *		- return cacheable or uncacheable
 *
 * SYNOPSIS
 *	#include <mach/noncache.h>
 *	int PHYS_TO_CACHETYPE(phys_addr_t);
 *	int VA_TO_CACHETYPE(uintptr_t);
 * INPUT
 *	PHYS_TO_CACHETYPE: Physical address of DDR, eSRAM.
 *	VA_TO_CACHETYPE:   Kernel address of DDR, eSRAM.
 * RETURN VALUE
 *	PA2NC_CA	when cacheable
 *	PA2NC_UC	when uncacheable
 *	PA2NC_ERR	when illegal input
 *
 */

#define PHYS_TO_NONCACHE(x)	arch_phys_to_noncache(x)
#define PHYS_TO_CACHE(x)	arch_phys_to_cache(x)
#define PHYS_TO_VA(x)		arch_phys_to_va(x)
#define VA_TO_PHYS(x)		arch_va_to_phys(x)
#define VA_TO_NONCACHE(x)	arch_va_to_noncache(x)
#define VA_TO_CACHE(x)		arch_va_to_cache(x)
#define PHYS_TO_MEMTYPE(x)	arch_phys_to_memtype(x)
#define VA_TO_MEMTYPE(x)	arch_va_to_memtype(x)
#define PHYS_TO_CACHETYPE(x)	arch_phys_to_cachetype(x)
#define VA_TO_CACHETYPE(x)	arch_va_to_cachetype(x)
#define PHYS_TO_CACHETYPE2(x,y)	arch_phys_to_cachetype2((x),(y))
#define PHYS32_TO_PHYS64(x)	arch_p32_to_p64(x)
#define PHYS64_TO_PHYS32(x)	arch_p64_to_p32(x)
#define PCI32_TO_PHYS64(x)	arch_pci32_to_p64(x)
#define PHYS64_TO_PCI32(x)	arch_p64_to_pci32(x)

#define PA2NC_ERR	(0)
#define PA2NC_ERR2	(~0U)
#define PA2NC_DDRA	(0x1)
#define PA2NC_DDRB	(0x2)
#define PA2NC_ESRAM	(0x3)
#define PA2NC_ESRAMB	(0x4)
#define PA2NC_ESRAMC	(0x5)
#define PA2NC_CA	(0x11)
#define PA2NC_UC	(0x12)
#define PA2NC_MIX	(0x13)

#ifdef __KERNEL__
# include <linux/types.h>
#else
typedef unsigned long phys_addr_t;
typedef unsigned long size_t;
#endif

#ifdef __cplusplus
extern "C" {
#endif

	extern uintptr_t   arch_phys_to_noncache(phys_addr_t pa);
	extern uintptr_t   arch_phys_to_cache(phys_addr_t pa);
	extern uintptr_t   arch_phys_to_va(phys_addr_t pa);
	extern phys_addr_t arch_va_to_phys(uintptr_t va);
	extern uintptr_t   arch_va_to_noncache(uintptr_t va);
	extern uintptr_t   arch_va_to_cache(uintptr_t va);
	extern int         arch_phys_to_memtype(phys_addr_t pa);
	extern int         arch_va_to_memtype(uintptr_t va);
	extern int         arch_phys_to_cachetype(phys_addr_t pa);
	extern int         arch_va_to_cachetype(uintptr_t va);
	extern int         arch_phys_to_cachetype2(phys_addr_t pa, size_t size);
	extern phys_addr_t arch_p32_to_p64(uint32_t p32);
	extern uint32_t    arch_p64_to_p32(phys_addr_t p64);
	extern phys_addr_t arch_pci32_to_p64(uint32_t p32);
	extern uint32_t    arch_p64_to_pci32(phys_addr_t p64);

#ifdef __cplusplus
}
#endif

#endif /* __MACH_CXD90XXX_INCLUDE_MACH_NONCACHE_H */
