/*
 * mach-cxd900xx/include/mach/udif/devno.h
 *
 *
 * Copyright 2015 Sony Corporation
 * Copyright 2018 Sony Imaging Products & Solutions Inc
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
#ifndef __MACH_UDIF_DEVNO_H__
#define __MACH_UDIF_DEVNO_H__

#include <linux/udif/devnode.h>

typedef enum {
	UDIF_NODE_GPIO = 0,
	UDIF_NODE_USB_EVENT,
	UDIF_NODE_USB_GCORE,
	UDIF_NODE_USB_OCORE,
	UDIF_NODE_USB_CORE,
	UDIF_NODE_USB_SCSI,
	UDIF_NODE_USB_MASS,
	UDIF_NODE_USB_SICD_CORE,
	UDIF_NODE_USB_SICD_DATA,
	UDIF_NODE_USB_SICD_EVENT,
	UDIF_NODE_USB_SEN,
	UDIF_NODE_USB_TER,
	UDIF_NODE_USB_CUR,
	UDIF_NODE_USB_EXTCMD,
	UDIF_NODE_USB_GADGET_BUSPOWER,
	UDIF_NODE_PCIDMA,
	UDIF_NODE_USB_IAP,
	UDIF_NODE_NUM,
} UDIF_NODE_ID;

/* GPIO device */
#define DEVNAME_GPIO		"gpio"

#if defined UDIF_DEVNODE_HAS_INSTANCE || !defined __KERNEL__
UDIF_DEVNODE __udif_devnodes[] = {
	[UDIF_NODE_GPIO] = {
		.name		= DEVNAME_GPIO,
		.type		= UDIF_TYPE_CDEV,
		.major		= 240,
		.first_minor	= 0,
		.nr_minor	= 1,
	},
	[UDIF_NODE_PCIDMA]    = {"pcidma",		UDIF_TYPE_CDEV, 240, 1, 1 },
	[UDIF_NODE_USB_EVENT] = { "usb/event",		UDIF_TYPE_CDEV, 242, 0, 1 },
	[UDIF_NODE_USB_GCORE] = { "usb/gadgetcore",	UDIF_TYPE_CDEV, 242, 1, 1 },
	[UDIF_NODE_USB_OCORE] = { "usb/otgcore",	UDIF_TYPE_CDEV, 242, 2, 1 },
	[UDIF_NODE_USB_CORE] =  { "usb/usbcore",	UDIF_TYPE_CDEV, 242, 3, 1 },
	[UDIF_NODE_USB_SCSI] =  { "usb/scsi",		UDIF_TYPE_CDEV, 242, 4, 1 },
	[UDIF_NODE_USB_MASS] =  { "usb/massstorage", UDIF_TYPE_CDEV, 248, 0, 1 },
	[UDIF_NODE_USB_SICD_CORE] =  { "usb/sicd_core", UDIF_TYPE_CDEV, 248, 1, 1 },
	[UDIF_NODE_USB_SICD_DATA] =  { "usb/sicd_data", UDIF_TYPE_CDEV, 248, 2, 1 },
	[UDIF_NODE_USB_SICD_EVENT] = { "usb/sicd_event",    UDIF_TYPE_CDEV, 248, 3, 1 },
	[UDIF_NODE_USB_SEN] =   { "usb/sen",        UDIF_TYPE_CDEV, 248, 4, 1 },
	[UDIF_NODE_USB_TER] =   { "usb/ter",        UDIF_TYPE_CDEV, 248, 5, 1 },
	[UDIF_NODE_USB_CUR] =   { "usb/cur",        UDIF_TYPE_CDEV, 248, 8, 1 },
	[UDIF_NODE_USB_EXTCMD]= { "usb/usb_extcmd", UDIF_TYPE_CDEV, 248, 7, 1 },
	[UDIF_NODE_USB_GADGET_BUSPOWER] = { "usb/usbg_bspwr", UDIF_TYPE_CDEV, 248, 14, 1 },
	[UDIF_NODE_USB_IAP]       = { "usb/iap", UDIF_TYPE_CDEV, 248, 15, 1 },
};

#ifdef __KERNEL__
 #include <linux/module.h>
 EXPORT_SYMBOL(__udif_devnodes);
#endif

#else /* UDIF_DEVNODE_HAS_INSTANCE || !_KERNEL__ */
 extern UDIF_DEVNODE __udif_devnodes[UDIF_NODE_NUM];
#endif /* UDIF_DEVNODE_HAS_INSTANCE || !_KERNEL__ */

#define udif_device_node(id) (((id) < UDIF_NODE_NUM) ? &__udif_devnodes[id] : NULL)

#endif /* __MACH_UDIF_DEVNO_H__ */
