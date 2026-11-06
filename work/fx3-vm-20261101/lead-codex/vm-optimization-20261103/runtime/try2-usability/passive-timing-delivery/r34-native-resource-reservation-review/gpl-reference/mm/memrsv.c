/*
 * mm/memrsv.c
 *
 *
 * Copyright 2019 Sony Imaging Products & Solutions Inc.
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
 *
 */
#include <linux/init.h>
#include <linux/errno.h>
#include <linux/memblock.h>
#include <linux/printk.h>
#include <linux/memrsv.h>

#define MAX_RESERVE_AREAS CONFIG_SNSC_MAX_RESERVE_AREA

struct reserved_mem {
	unsigned long start;
	unsigned long size;
};
static struct reserved_mem reserved_mem[MAX_RESERVE_AREAS];
static unsigned int reserve_mem_nr_map;

static int memrsv_add(unsigned long start, unsigned long size)
{
	if (MAX_RESERVE_AREAS == reserve_mem_nr_map) {
		printk(KERN_ERR "too many reserved areas(max %d)!\n", MAX_RESERVE_AREAS);
		return -1;
	}
	printk("memrsv: 0x%lx@0x%lx\n", size, start);
	reserved_mem[reserve_mem_nr_map].start = start;
	reserved_mem[reserve_mem_nr_map].size = size;
	reserve_mem_nr_map++;
	return 0;
}

/*
  return if the page@phys is in the reserved area list
  @phys: physical address of the page
*/
int is_ext_reserved_area(unsigned long phys)
{
	int i;
	for(i=0; i<reserve_mem_nr_map; i++){
		if(phys >= reserved_mem[i].start
		   && phys < (reserved_mem[i].start + reserved_mem[i].size))
			return 1;
	}

	return 0;
}

int __weak __init arch_memrsv_add(unsigned long start, unsigned long size, char *p)
{
	return 0;
}

static __init int parse_memrsv(char *p)
{
	int start_flag;
	unsigned long size, start;
	char *endp;

	start_flag = 0;
	size = start = 0;
	size = memparse(p, &endp);
	if ('@' == *endp) {
		start = memparse(endp + 1, &endp);
		start_flag = 1;
	}
	p = endp;

	if (size && start_flag) {
		if (memblock_reserve(start, size) < 0)
			return -EINVAL;
		if (memrsv_add(start, size) < 0)
			return -EINVAL;
		if (arch_memrsv_add(start, size, p) < 0)
			return -EINVAL;
	}
	return 0;
}
early_param("memrsv", parse_memrsv);
