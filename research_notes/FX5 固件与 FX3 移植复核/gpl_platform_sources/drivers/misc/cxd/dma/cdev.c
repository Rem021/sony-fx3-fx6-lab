/*
 * driver/misc/cxd/dma/cdev.c
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

#include <linux/udif/cdev.h>
#include <linux/completion.h>
#include <linux/udif/uaccess.h>
#include <mach/udif/devno.h>

#include "internal.h"

struct cb_info {
	struct completion done;
	UDIF_INT err;
};

static void cxdma_ioctl_cb(int err, void *cookies)
{
	struct cb_info *cbinfo = (struct cb_info *)cookies;

	cbinfo->err = err;
	complete(&cbinfo->done);
}

static UDIF_ERR cxdma_ioctl(UDIF_FILE *file, UDIF_IOCTL *ioctl)
{
	struct dma_request param;
	req_t req;
	struct cb_info cb = {
		.err = 0,
		.done = COMPLETION_INITIALIZER_ONSTACK(cb.done),
	};
	UDIF_ERR ret;

	if (!file || !ioctl) {
		return UDIF_ERR_PAR;
	}
	if (DMA_MEM_TRANSFER != ioctl->cmd) {
		return UDIF_ERR_PAR;
	}
	if (!ioctl->arg) {
		return UDIF_ERR_PAR;
	}
	if (udif_copy_from_user(&param, (UDIF_USR_RO)ioctl->arg, sizeof param) != 0) {
		return UDIF_ERR_FAULT;
	}

	req.ch   = param.ch;
	req.size = param.size;
	req.src  = param.src;
	req.dst  = param.dst;
	req.pconf.data = 0;
	req.callback = cxdma_ioctl_cb;
	req.cookies = &cb;

	ret = dma_mem_transfer_async(&req);
	if (ret) {
		return UDIF_ERR_PAR;
	}
	ret = wait_for_completion_timeout(&cb.done, DMA_IOCTL_TIMEOUT * HZ);
	if (!ret) {
		return UDIF_ERR_TIMEOUT;
	}
	if (cb.err) {
		return UDIF_ERR_IO;
	}
	return UDIF_ERR_OK;
}

static UDIF_ERR cxdma_open(UDIF_FILE *file)
{
	return UDIF_ERR_OK;
}

static UDIF_ERR cxdma_close(UDIF_FILE *file)
{
	return UDIF_ERR_OK;
}

static UDIF_CDEV_OPS cxdma_fops = {
	.open  = cxdma_open,
	.close = cxdma_close,
	.ioctl = cxdma_ioctl,
};

static UDIF_DECLARE_CDEV(cxdma_cdev, udif_device_node(UDIF_NODE_DMA), &cxdma_fops, NULL);

void UDIF_INIT cxdma_cdev_init(void)
{
	UDIF_ERR ret;

	ret = udif_cdev_register(&cxdma_cdev);
	if (UDIF_ERR_OK != ret) {
		cxdma_perr("udif_cdev_register:ret=%d\n", ret);
	}
}

void UDIF_EXIT cxdma_cdev_exit(void)
{
	udif_cdev_unregister(&cxdma_cdev);
}
