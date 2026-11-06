/*
 * drivers/udif/mach-cxd90xxx/adrs_conv.c
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

#include <linux/module.h>
#include <linux/init.h>
#include <linux/printk.h>
#include <mach/platform.h>
#include <mach/noncache.h>
#include <mach/dma32.h>

#define BUG_SIMPLE	do { *(int *)0 = 0; for (;;); } while (0)

static int cxd90xxx_adrs_debug;
module_param_named(debug, cxd90xxx_adrs_debug, int, S_IRUSR|S_IWUSR);
static bool cxd90xxx_adrs_ignore_null;
module_param_named(null, cxd90xxx_adrs_ignore_null, bool, S_IRUSR|S_IWUSR);

/* physical address */
#define DDR0_END	(DDR0_BASE + DDR0_SIZE)
#define DDR1_END	(DDR1_BASE + DDR1_SIZE)
#define ESRAM0_BASE	CXD90XXX_ESRAM0_BASE
#define ESRAM0_SIZE	CXD90XXX_ESRAM0_SIZE
#define ESRAM0_END	(ESRAM0_BASE + ESRAM0_SIZE)
#define ESRAM1_BASE	CXD90XXX_ESRAM1_BASE
#define ESRAM1_SIZE	CXD90XXX_ESRAM1_SIZE
#define ESRAM1_END	(ESRAM1_BASE + ESRAM1_SIZE)
#define CSRAM_BASE	CXD90XXX_CSRAM_BASE
#define CSRAM_SIZE	CXD90XXX_CSRAM_SIZE
#define CSRAM_END	(CSRAM_BASE + CSRAM_SIZE)

#define VA_DDR0		PAGE_OFFSET
#define VA_DDR0_END	(VA_DDR0 + DDR0_SIZE)
#define VA_DDR1		(PAGE_OFFSET + SZ_16G)
#define VA_DDR1_END	(VA_DDR1 + DDR1_SIZE)
#define VA_ESRAM0	(CXD90XXX_IO_VA + 0xFE000000UL)
#define VA_ESRAM0_END	(VA_ESRAM0 + ESRAM0_SIZE)
#define VA_ESRAM1	(CXD90XXX_IO_VA + 0xE0000000UL)
#define VA_ESRAM1_END	(VA_ESRAM1 + ESRAM1_SIZE)
#define VA_CSRAM	(CXD90XXX_IO_VA + 0xC0000000UL)
#define VA_CSRAM_END	(VA_CSRAM + CSRAM_SIZE)

#define pass_through(x)	unlikely(!(x)  &&  cxd90xxx_adrs_ignore_null)

static inline void show_info(void)
{
	switch (cxd90xxx_adrs_debug) {
	case 1:
		dump_stack();
		break;
	case 2:
		dump_stack();
		BUG_SIMPLE;
		break;
	default:
		break;
	}
}

/* Physical Address Reg. */
#define PAR_F		0x0000000000000001UL
#define PAR_ATTR_SHIFT	56
#define PAR_PA		0x0000fffffffff000UL

static inline u64 __v2p(uintptr_t va)
{
	unsigned long flags;
	u64 par;

	local_irq_save(flags);
	asm volatile("at s1e1r, %0" ::"r" (va));
	isb();
	par = read_sysreg(par_el1);
	local_irq_restore(flags);
	return par;
}

static inline int v2p(uintptr_t va, u64 *pa)
{
	u64 par;
	u8 attr;

	par = __v2p(va);
	if (unlikely(par & PAR_F)) {
		return -1;
	}
	attr = par >> PAR_ATTR_SHIFT;
	par = (par & PAR_PA)|(va & ~PAGE_MASK);
	/* DDR, CSRAM, ESRAM0/1 ? */
	if (likely((DDR0_BASE <= par  &&  par < DDR0_END)
		   || (CSRAM_BASE <= par  &&  par < CSRAM_END)
		   || (ESRAM0_BASE <= par  &&  par < ESRAM0_END)
		   || (DDR1_BASE <= par && par < DDR1_END)
		   || (ESRAM1_BASE <= par  &&  par < ESRAM1_END))) {
		*pa = par;
		return (int)attr;
	}
	return -1;
}

static inline uintptr_t __p2v(phys_addr_t pa)
{
	if (likely(DDR0_BASE <= pa  &&  pa < DDR0_END)) {
		return (uintptr_t)(VA_DDR0 + (pa - DDR0_BASE));
	} else if (CSRAM_BASE <= pa  &&  pa < CSRAM_END) {
		return (uintptr_t)(VA_CSRAM + (pa - CSRAM_BASE));
	} else if (ESRAM0_BASE <= pa  &&  pa < ESRAM0_END) {
		return (uintptr_t)(VA_ESRAM0 + (pa - ESRAM0_BASE));
	} else if (DDR1_BASE <= pa  &&  pa < DDR1_END) {
		return (uintptr_t)(VA_DDR1 + (pa - DDR1_BASE));
	} else if (ESRAM1_BASE <= pa  &&  pa < ESRAM1_END) {
		return (uintptr_t)(VA_ESRAM1 + (pa - ESRAM1_BASE));
	}
	return PA2NC_ERR;
}

static inline int p2v(phys_addr_t pa, uintptr_t *va)
{
	uintptr_t vtmp;
	u64 ptmp;
	int attr;

	vtmp= __p2v(pa);
	if (unlikely(PA2NC_ERR == vtmp))
		return -1;
	attr = v2p(vtmp, &ptmp);
	if (unlikely(attr < 0 || ptmp != pa))
		return -1;
	*va = vtmp;
	return attr;
}

/* Attr */
#define ATTR_SHIFT	4
#define ATTR_DEVICE	0x0
#define ATTR_NC		0x4

static inline bool is_cache(u8 attr)
{
	switch (attr >> ATTR_SHIFT) {
	case ATTR_DEVICE:
	case ATTR_NC:
		return false;
	default:
		break;
	}
	return true;
}

/*---------------- API ----------------*/
phys_addr_t arch_va_to_phys(uintptr_t va)
{
	u64 pa;

	if (pass_through(va))
		return va;
	if (unlikely(v2p(va, &pa) < 0)) {
		printk(KERN_ERR "ERROR:%s:va=0x%lx\n", __func__, va);
		show_info();
		return PA2NC_ERR;
	}
	return (phys_addr_t)pa;
}

uintptr_t arch_va_to_noncache(uintptr_t va)
{
	u64 pa;
	int attr;

	if (pass_through(va))
		return va;
	attr = v2p(va, &pa);
	if (unlikely(attr < 0 || is_cache(attr))) {
		printk(KERN_ERR "ERROR:%s:va=0x%lx\n", __func__, va);
		show_info();
		return PA2NC_ERR;
	}
	return va;
}

uintptr_t arch_va_to_cache(uintptr_t va)
{
	u64 pa;
	int attr;

	if (pass_through(va))
		return va;
	attr = v2p(va, &pa);
	if (unlikely(attr < 0 || !is_cache(attr))) {
		printk(KERN_ERR "ERROR:%s:va=0x%lx\n", __func__, va);
		show_info();
		return PA2NC_ERR;
	}
	return va;
}


uintptr_t arch_phys_to_va(phys_addr_t pa)
{
	uintptr_t va;

	if (pass_through(pa))
		return pa;
	va = __p2v(pa);
	if (unlikely(PA2NC_ERR == va)) {
		printk(KERN_ERR "ERROR:%s:pa=0x%llx\n", __func__, pa);
		show_info();
		return PA2NC_ERR;
	}
	return va;
}

uintptr_t arch_phys_to_noncache(phys_addr_t pa)
{
	uintptr_t va;
	int attr;

	if (pass_through(pa))
		return pa;
	attr = p2v(pa, &va);
	if (unlikely(attr < 0 || is_cache(attr))) {
		printk(KERN_ERR "ERROR:%s:pa=0x%llx\n", __func__, pa);
		show_info();
		return PA2NC_ERR;
	}
	return va;
}

uintptr_t arch_phys_to_cache(phys_addr_t pa)
{
	uintptr_t va;
	int attr;

	if (pass_through(pa))
		return pa;
	attr = p2v(pa, &va);
	if (unlikely(attr < 0 || !is_cache(attr))) {
		printk(KERN_ERR "ERROR:%s:pa=0x%llx\n", __func__, pa);
		show_info();
		return PA2NC_ERR;
	}
	return va;
}

int arch_phys_to_memtype(phys_addr_t pa)
{
	if (likely(DDR0_BASE <= pa  &&  pa < DDR0_END)) {
		return PA2NC_DDRA;
	} else if (ESRAM0_BASE <= pa  &&  pa < ESRAM0_END) {
		return PA2NC_ESRAM;
	} else if (DDR1_BASE <= pa  &&  pa < DDR1_END) {
		return PA2NC_DDRB;
	} else if (ESRAM1_BASE <= pa  &&  pa < ESRAM1_END) {
		return PA2NC_ESRAMB;
	} else if (CSRAM_BASE <= pa  &&  pa < CSRAM_END) {
		return PA2NC_ESRAMC;
	}
	return PA2NC_ERR;
}

int arch_va_to_memtype(uintptr_t va)
{
	u64 pa;
	int attr;

	attr = v2p(va, &pa);
	if (unlikely(attr < 0))
		return PA2NC_ERR;
	return arch_phys_to_memtype(pa);
}

int arch_phys_to_cachetype(phys_addr_t pa)
{
	uintptr_t va;
	int attr;

	attr = p2v(pa, &va);
	if (unlikely(attr < 0)) {
		return PA2NC_ERR;
	}
	return is_cache(attr) ? PA2NC_CA : PA2NC_UC;
}

int arch_va_to_cachetype(uintptr_t va)
{
	u64 pa;
	int attr;

	attr = v2p(va, &pa);
	if (unlikely(attr < 0)) {
		return PA2NC_ERR;
	}
	return is_cache(attr) ? PA2NC_CA : PA2NC_UC;
}

int arch_phys_to_cachetype2(phys_addr_t pa, size_t size)
{
	phys_addr_t pe = pa + size - 1;
	int ret1, ret2;

	ret1 = arch_phys_to_cachetype(pa);
	ret2 = arch_phys_to_cachetype(pe);
	if (unlikely(PA2NC_ERR == ret1 || PA2NC_ERR == ret2))
		return PA2NC_ERR;
	if (unlikely(ret1 != ret2))
		return PA2NC_MIX;
	return ret1;
}

uint32_t arch_p64_to_p32(phys_addr_t p64)
{
	uint32_t p32;

	p32 = __arch_p64_to_p32(p64);
	if (unlikely(PHYS32_ERR == p32)) {
		printk(KERN_ERR "ERROR:%s:p64=0x%llx\n", __func__, p64);
		show_info();
	}
	return p32;
}

phys_addr_t arch_p32_to_p64(uint32_t p32)
{
	uint64_t p64;

	p64 = __arch_p32_to_p64(p32);
	if (unlikely(PHYS64_ERR == p64)) {
		printk(KERN_ERR "ERROR:%s:p32=0x%x\n", __func__, p32);
		show_info();
	}
	return (phys_addr_t)p64;
}

/* PCI32 address map */
#define PCI32_P64_DDR_BASE	0x200000000UL
#define PCI32_P64_DDR_END	0x300000000UL
#define PCI32_P64(x)		(PCI32_P64_DDR_BASE|(x))

uint32_t arch_p64_to_pci32(phys_addr_t p64)
{
	if (PCI32_P64_DDR_BASE <= p64 && p64 < PCI32_P64_DDR_END)
		return (uint32_t)p64;
	printk(KERN_ERR "ERROR:%s:p64=0x%llx\n", __func__, p64);
	show_info();
	return PHYS32_ERR;
}

phys_addr_t arch_pci32_to_p64(uint32_t pci32)
{
	return (phys_addr_t)PCI32_P64(pci32);
}


EXPORT_SYMBOL(arch_va_to_phys);
EXPORT_SYMBOL(arch_va_to_noncache);
EXPORT_SYMBOL(arch_va_to_cache);
EXPORT_SYMBOL(arch_phys_to_va);
EXPORT_SYMBOL(arch_phys_to_noncache);
EXPORT_SYMBOL(arch_phys_to_cache);
EXPORT_SYMBOL(arch_phys_to_memtype);
EXPORT_SYMBOL(arch_va_to_memtype);
EXPORT_SYMBOL(arch_phys_to_cachetype);
EXPORT_SYMBOL(arch_va_to_cachetype);
EXPORT_SYMBOL(arch_phys_to_cachetype2);
EXPORT_SYMBOL(arch_p64_to_p32);
EXPORT_SYMBOL(arch_p32_to_p64);
EXPORT_SYMBOL(arch_p64_to_pci32);
EXPORT_SYMBOL(arch_pci32_to_p64);
