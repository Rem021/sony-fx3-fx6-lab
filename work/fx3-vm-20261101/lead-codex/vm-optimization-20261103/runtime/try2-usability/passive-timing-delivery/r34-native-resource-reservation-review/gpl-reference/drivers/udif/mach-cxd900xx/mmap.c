/*
 * drivers/udif/mach-cxd900xx/mmap.c
 *
 * Copyright 2018 Sony Corporation
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
#include <linux/fs.h>
#include <linux/mm.h>
#include <linux/sched.h>
#include <mach/noncache.h>

static int cxd900x0_mmap_debug = 0;
module_param_named(debug, cxd900x0_mmap_debug, int, S_IRUSR|S_IWUSR);

static char *req_str(int req_is_uc)
{
	return (req_is_uc) ? "uc" : "ca";
}

static char *mem_str(int mem_type)
{
	switch (mem_type) {
	case PA2NC_CA:
		return "ca";
	case PA2NC_UC:
		return "uc";
	case PA2NC_MIX:
		return "mix";
	default:
		break;
	}
	return "???";
}

static void show_info(phys_addr_t phys, unsigned long size,
		      int req_is_uc, int mem_type)
{
	phys_addr_t pe = phys + size - 1;

	printk(KERN_ERR "ERROR:%s(%d):mmap[0x%llx-0x%llx] cache type mismatch:req=%s, mem=%s\n",
	       current->comm, current->pid,
	       (unsigned long long)phys, (unsigned long long)pe,
	       req_str(req_is_uc), mem_str(mem_type));
}

int phys_mem_access_prot_allowed(struct file *file, unsigned long pfn,
				 unsigned long size, pgprot_t *vma_prot)
{
	phys_addr_t phys;
	int req_is_uc, mem_type;

	if (!cxd900x0_mmap_debug)
		return 1;

	/* get request type */
	req_is_uc = file->f_flags & O_SYNC;

	/* get memory type */
	phys = __pfn_to_phys(pfn);
	mem_type = PHYS_TO_CACHETYPE2(phys, size);

	/* verify */
	switch (mem_type) {
	case PA2NC_CA:
		if (!req_is_uc) /* match */
			return 1;
		break;
	case PA2NC_UC:
		if (req_is_uc) /* match */
			return 1;
		break;
	case PA2NC_MIX:
		break;
	default: /* not memory (check is not required) */
		return 1;
	}

	/* error */
	switch (cxd900x0_mmap_debug) {
	case 1: /* warning only */
		show_info(phys, size, req_is_uc, mem_type);
		return 1;
	case 2: /* warning and error */
		show_info(phys, size, req_is_uc, mem_type);
		break;
	default: /* exception */
		show_info(phys, size, req_is_uc, mem_type);
		BUG();
		break;
	}
	return 0;
}
