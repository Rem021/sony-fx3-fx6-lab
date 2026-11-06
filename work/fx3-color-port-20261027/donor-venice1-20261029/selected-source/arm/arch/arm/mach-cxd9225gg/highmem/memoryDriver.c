/*
 * Copyright 2012 Sony Corporation
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License, version 2, as
 * published by the Free Software Foundation.
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
 * GNU General Public License for more details.
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 */

#include <linux/module.h>
#include <linux/mm.h>
#include <linux/fs.h>
#include <linux/cdev.h>
#include <linux/device.h>
#include <asm/uaccess.h>
#include <asm/setup.h>
#include <linux/io.h>
#include "memoryDriverDef.h"
#include "memoryDriver.h"

#include <mach/cxd9225gg_types.h>

#ifdef CONFIG_SNSC_HSS
#include <linux/snsc_hss.h>
#endif /* #ifdef CONFIG_SNSC_HSS */

/* defines */
#define DEVICE_NAME  "memoryDriver"

static unsigned char memdrv_pool_area[0xC87000] __attribute__((aligned(4096)));

static __init void parse_mem(char **p, unsigned long *addr, unsigned long *size)
{
	*size = memparse(*p, p);

	if (**p == '@' || **p == '$' || **p == '#') {
		*addr = memparse(*p + 1, p);
	}
}

static unsigned long virt_addr_base = 0;
static unsigned long phys_addr_base = 0;
static unsigned long memory_size = 0;

typedef struct _memory_data {
	unsigned long phys_addr_base;
	unsigned long virt_addr_base;
	unsigned long memory_size;
} memory_data_t;

static memory_data_t memory_data[] = {
    { -1UL, 0, 0 },
    { -1UL, 0, 0 },
    { -1UL, 0, 0 },
    { -1UL, 0, 0 },
    { (unsigned long)__pa(memdrv_pool_area), (unsigned long)memdrv_pool_area, sizeof(memdrv_pool_area) },
};

static memory_data_t static_memory_data = { -1UL, 0, 0 };

static __init void parse_remap(char **p)
{
    parse_mem(p, &phys_addr_base, &memory_size);
}

static __init void parse_stream(char **p)
{
    parse_mem(p, &memory_data[0].phys_addr_base,  &memory_data[0].memory_size);
}

static __init void parse_mcarea(char **p)
{
    parse_mem(p, &static_memory_data.phys_addr_base,  &static_memory_data.memory_size);
}

__early_param("remap=", parse_remap);
__early_param("stream=", parse_stream);
__early_param("mc_area=", parse_mcarea);

static const int memory_data_size = sizeof(memory_data) / sizeof(memory_data[0]);

static int major_number = CXD9225GG_MAJOR_ID_HI_MEM;

#ifdef CONFIG_SNSC_HSS
struct hss_memory_d_info {
    struct hss_node *node;
};
struct hss_memory_d_info    *p_hss_memory_d_info;
#endif  /* #ifdef CONFIG_SNSC_HSS */

static int memoryDrv_open(struct inode *inode, struct file *file);
static int memoryDrv_release(struct inode *inode, struct file *file);
static int memoryDrv_ioctl(struct inode *inode, struct file *file,
        unsigned int cmd, unsigned long args);
static int memoryDrv_mmap(struct file *file, struct vm_area_struct *vma);

/* file operations */
static struct file_operations memdrv_fops = {
        .owner = THIS_MODULE,
        .mmap = memoryDrv_mmap,
        .ioctl = memoryDrv_ioctl,
        .open = memoryDrv_open,
        .release = memoryDrv_release,
};

unsigned long cxd9225gg_hi_address_virt(void)
{
        return virt_addr_base;
}
EXPORT_SYMBOL(cxd9225gg_hi_address_virt);

unsigned long cxd9225gg_hi_address_phys(void)
{
        return phys_addr_base;
}
EXPORT_SYMBOL(cxd9225gg_hi_address_phys);

unsigned long cxd9225gg_hi_address_size(void)
{
        return memory_size;
}
EXPORT_SYMBOL(cxd9225gg_hi_address_size);

unsigned long kernel_virt_to_phys(unsigned long virt_addr)
{
        /* virtual address range check */
		if(virt_addr >= virt_addr_base &&
                virt_addr - virt_addr_base < memory_size)
                return (virt_addr - virt_addr_base + phys_addr_base);

		if(virt_addr >= static_memory_data.virt_addr_base &&
                virt_addr - static_memory_data.virt_addr_base < static_memory_data.memory_size)
                return (virt_addr - static_memory_data.virt_addr_base + static_memory_data.phys_addr_base);

        return __pa(virt_addr);
}
EXPORT_SYMBOL(kernel_virt_to_phys);

unsigned long kernel_phys_to_virt(unsigned long phys_addr)
{
        /* virtual address range check */
        if(phys_addr >= phys_addr_base &&
                phys_addr - phys_addr_base < memory_size)
                return (phys_addr - phys_addr_base + virt_addr_base);

        if(phys_addr >= static_memory_data.phys_addr_base &&
                phys_addr - static_memory_data.phys_addr_base < static_memory_data.memory_size)
                return (phys_addr - static_memory_data.phys_addr_base + static_memory_data.virt_addr_base);

        return (unsigned long)__va(phys_addr);
}
EXPORT_SYMBOL(kernel_phys_to_virt);

/**
 * memoryDrv_mmap - map reserved memory to user space
 * @file: pointer to struct file
 * @vma: pointer to struct vm_area_struct
 *
 * return 0 if succeeded, none zero if failed.
 */
static int memoryDrv_mmap(struct file *file, struct vm_area_struct *vma)
{
        unsigned long offset = vma->vm_pgoff << PAGE_SHIFT;
		unsigned long size = vma->vm_end - vma->vm_start;

		int i;
		int found = 0;

		for(i = 0; i < memory_data_size; i++) {
				if(offset >= memory_data[i].phys_addr_base &&
					offset < memory_data[i].phys_addr_base + memory_data[i].memory_size) {
					found = 1;
					break;
				}
		}
		if(offset >= static_memory_data.phys_addr_base &&
					offset < static_memory_data.phys_addr_base + static_memory_data.memory_size) {
			found = 1;
		}

        if(!found){
                printk(DEVICE_NAME" mmap addr or size is wrong!!!\n");
                return -ENXIO;
        }

	vma->vm_page_prot = pgprot_noncached(vma->vm_page_prot); 
 
        vma->vm_flags |= VM_LOCKED;
        /* map physical memory to user space */
        if(remap_pfn_range(vma, vma->vm_start, offset >> PAGE_SHIFT, size, vma->vm_page_prot)){
                printk(DEVICE_NAME"remap_pfn_range failed\n");
                return -ENXIO;
        }
#ifdef CONFIG_SNSC_ENABLE_MMAP_HACK_FOR_DIRECT_IO_TEST
        vma->vm_flags &= ~(VM_IO | VM_PFNMAP);
#endif
        return 0;
}

static int memoryDrv_open(struct inode *inode, struct file *file)
{
        return 0;
}

static int memoryDrv_release(struct inode *inode, struct file *file)
{
        return 0;
}

static int memoryDrv_ioctl(struct inode *inode, struct file *file,
        unsigned int cmd, unsigned long args)
{
        int result = 0;
        void __user *argp = (void __user*)args;
		unsigned long data = 0;		
		
	    switch(cmd & MEMORY_IOCTL_MASK){
        case MEMORY_IOCTL_PHYS_ADDR:
        		if(cmd -  MEMORY_IOCTL_PHYS_ADDR<memory_data_size){
					data = memory_data[cmd -  MEMORY_IOCTL_PHYS_ADDR].phys_addr_base;
	            }else{
					data = static_memory_data.phys_addr_base;
				}
                if(copy_to_user(argp, &data, sizeof(data)))
                        result = -1;
                break;
        case MEMORY_IOCTL_MEMORY_SIZE:
        		if(cmd - MEMORY_IOCTL_MEMORY_SIZE<memory_data_size){
					data = memory_data[cmd -  MEMORY_IOCTL_MEMORY_SIZE].memory_size;
				}else{
					data = static_memory_data.memory_size;
				}
                if(copy_to_user(argp, &data, sizeof(data)))
                        result = -1;
                break;
        default:
                printk(DEVICE_NAME"  ioctl cmd is wrong.");
                result = -1;
        }

        return result;
}

#ifdef CONFIG_SNSC_HSS
static int memory_d_hss_node_suspend(struct hss_node *node)
{
    /* TENTATIVE : no procedure */
    return 0;
}

static int memory_d_hss_node_resume(struct hss_node *node)
{
    /* TENTATIVE : no procedure */
    return 0;
}

static struct hss_node_ops hss_memory_d_node_ops = {
    .suspend = memory_d_hss_node_suspend,
    .resume = memory_d_hss_node_resume,
};

static int memory_d_hss_node_init(void)
{
    struct hss_node *node;
    int error = 0;

    /* alloc for emif_dl info */
    p_hss_memory_d_info = kzalloc(sizeof(*p_hss_memory_d_info), GFP_KERNEL);
    if (!p_hss_memory_d_info) {
        return -ENOMEM;
    }

    /*
     * alloc the HSS node
     */
    node = hss_alloc_node(MEMORY_D_HSS_NODE_NAME);
    if (!node) {
        kfree(p_hss_memory_d_info);
        return -ENOMEM;
    }

    /*
     * save struct to HSS
     */
    hss_set_private(node, p_hss_memory_d_info);
    p_hss_memory_d_info->node = node;

    /*
     * Register the node.  If you want to get the callbacks to be called
     * before the specified node's one, specify the third parameter with
     * the name of the parent node. NULL means for no parent needed.
     */

    /* register HSS Platform for suspend/resume */
    error = hss_register_node(node, &hss_memory_d_node_ops, MEMORY_D_HSS_NODE_PARENT);

    if (error) {
        hss_free_node(node);
        kfree(p_hss_memory_d_info);
    }

    return error;
}

static void memory_d_hss_node_exit(void)
{
	hss_unregister_node(p_hss_memory_d_info->node);
	hss_free_node(p_hss_memory_d_info->node);
	kfree(p_hss_memory_d_info);
}
#endif /* #ifdef CONFIG_SNSC_HSS */

// make the func name readable and traceable.
static int __init memdrv_init(void)
{
        int result;
        int err;

#ifdef CONFIG_SNSC_HSS
    /* register driver to hss */
    result = memory_d_hss_node_init();
    if(result != 0) {
        return result;
    }
#endif /* #ifdef CONFIG_SNSC_HSS */

        printk("memdrv remap:  0x%08lx @ 0x%08lx\n", memory_size, phys_addr_base);
        printk("memdrv stream: 0x%08lx @ 0x%08lx\n", memory_data[0].memory_size, memory_data[0].phys_addr_base);
        printk("memdrv mcarea: 0x%08lx @ 0x%08lx\n", static_memory_data.memory_size, static_memory_data.phys_addr_base);

        /* register a char device driver */
		if(major_number > 0){
                result = register_chrdev(major_number, DEVICE_NAME, &memdrv_fops);
                if(result){
                        printk(DEVICE_NAME "can't register major number\n");
                        return result;
                }
        }else{
                major_number = register_chrdev(0, DEVICE_NAME, &memdrv_fops);
                if(major_number < 0){
                        printk(DEVICE_NAME "can't get major number\n");
                        return major_number;
                }
        }

        /* map physical memory to kernel space */
        virt_addr_base = (unsigned long)ioremap(phys_addr_base, memory_size);
        if(!virt_addr_base){
                printk(DEVICE_NAME "ioremap error, 0x%lx,0x%lx\n", phys_addr_base, memory_size);
                err = -ENODEV;
                goto error;
        }
        
        /* map static physical memory to kernel space */
        static_memory_data.virt_addr_base = (unsigned long)ioremap(static_memory_data.phys_addr_base, static_memory_data.memory_size);
        if(!static_memory_data.virt_addr_base){
                printk(DEVICE_NAME "ioremap error, 0x%lx,0x%lx\n", static_memory_data.phys_addr_base, static_memory_data.memory_size);
                err = -ENODEV;
                goto error;
        }

		memory_data[0].virt_addr_base = virt_addr_base;
        SetPageReserved(virt_to_page(memory_data[4].virt_addr_base));
        return 0;
error:
        unregister_chrdev(major_number, DEVICE_NAME);
        return err;
}

// make the func name readable and traceable.
static void __exit memdrv_fini(void)
{
        if(virt_addr_base){
                ClearPageReserved(virt_to_page(virt_addr_base));
                iounmap((void *)virt_addr_base);
                virt_addr_base = 0;
        }
        if(static_memory_data.virt_addr_base){
                ClearPageReserved(virt_to_page(static_memory_data.virt_addr_base));
                iounmap((void *)static_memory_data.virt_addr_base);
                static_memory_data.virt_addr_base = 0;
		}

		ClearPageReserved(virt_to_page(memory_data[4].virt_addr_base));
        unregister_chrdev(major_number, DEVICE_NAME);

#ifdef CONFIG_SNSC_HSS
    /* unregister driver from hss */
    memory_d_hss_node_exit();
#endif /* #ifdef CONFIG_SNSC_HSS */
}


MODULE_LICENSE("GPL");

module_init(memdrv_init);
module_exit(memdrv_fini);
