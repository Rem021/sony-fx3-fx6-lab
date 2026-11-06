/*
 * driver/misc/cxd/dma/dma_core.c
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
#include <linux/types.h>
#include <linux/errno.h>
#include <linux/tmonitor.h>

#include "internal.h"

static inline void dma_trans_tmon_write(const char *fmt, void *p)
{
	char buf[16];
	snprintf(buf, sizeof(buf), fmt, (unsigned long)p & 0x000000FFFFFFFFFF);
	tmonitor_write(buf);
}

/*-----------------  Kernel API ----------------------*/
static inline void req_enqueue(chan_t *chan, req_t *req)
{
	udif_list_add_tail(&req->drv.list, &chan->pending_list);
	chan->stat.pending_cnt++;
}

static inline req_t *req_dequeue(chan_t *chan)
{
	req_t *next;

	if (udif_list_empty(&chan->pending_list))
		return NULL;
	next = udif_list_entry_next(&chan->pending_list, req_t, drv.list);
	udif_list_del(&next->drv.list);
	chan->stat.pending_cnt--;
	return next;
}

static void cxdma_start(chan_t *chan)
{
	req_t *req;
	int ret;

	if (dma_busy(chan))
		return;
	if (dma_suspended(chan))
		return;

	do {
		req = req_dequeue(chan);
		if (!req)
			return;

		chan->cur = req;
		ret = hw_cxdma_start(chan);
		if (ret < 0) {
			chan->stat.err_cnt++;
		}
	} while (ret < 0);
}

void cxdma_cb(chan_t *chan, int err)
{
	req_t *cur;
	int suspend;
	unsigned long flags;

	if (err) {
		uint64_t intstat = 0;

		hw_cxdma_errstat(chan, &intstat);
		hw_cxdma_stop(chan);
		chan_log(chan->ch, "abort:%lx", intstat);
		hw_cxdma_dump(chan);
	}

	LOCK(chan);
	chan->stat.done_cnt++;
	if (err)
		chan->stat.abort_cnt++;
	cur = chan->cur;
	suspend = dma_suspended(chan);
	UNLOCK(chan);

	if (unlikely(suspend))
		return;
	if (cur) {
		dma_trans_tmon_write("DMAc:%lx", cur);
		if (cur->callback) {
			(*cur->callback)(err, cur->cookies);
		} else {
			chan_perr(chan->ch, "cb=NULL");
			BUG();
		}
	}

	LOCK(chan);
	chan->cur = NULL;
	cxdma_start(chan);
	UNLOCK(chan);
}

static int dma_trans_common(req_t *req)
{
	chan_t *chan = cxdma_get_chan(req->ch);
	int ret = 0;
	unsigned long flags;

	if (!chan || !dma_enabled(chan))
		return -EINVAL;

	req->drv.pid = task_pid_nr(current);

	LOCK(chan);
	if (dma_enabled(chan) && !dma_suspended(chan)) {
		req_enqueue(chan, req);
		cxdma_start(chan);
		ret = 0;
	} else {
		ret = -EINVAL;
	}
	UNLOCK(chan);
	return ret;
}

static inline int cxdma_check_args(req_t *req)
{
	if (!req)
		return -1;
	if (req->ch >= N_DMA_CH)
		return -1;
	if (!req->callback)
		return -1;
	if (hw_cxdma_check_args(req) < 0)
		return -1;
	return 0;
}

int dma_mem_transfer_async(req_t *req)
{
	dma_trans_tmon_write("DMAm:%lx", req);
	if (cxdma_check_args(req) < 0) {
		return -EINVAL;
	}
	req->pconf.data = 0;
	return dma_trans_common(req);
}
EXPORT_SYMBOL(dma_mem_transfer_async);

static inline int cxdma_check_peri(struct peri_config pconf)
{
	if (DMA_TRANS_TYPE_MEM2PERI != pconf.direction
	    && DMA_TRANS_TYPE_PERI2MEM != pconf.direction)
		return -1;
	return 0;
}

int dma_peri_transfer_async(req_t *req)
{
	dma_trans_tmon_write("DMAp:%lx", req);
	if (cxdma_check_args(req) < 0) {
		return -EINVAL;
	}
	if (cxdma_check_peri(req->pconf) < 0) {
		return -EINVAL;
	}
	return dma_trans_common(req);
}
EXPORT_SYMBOL(dma_peri_transfer_async);

int dma_reset_channel(uint32_t ch)
{
	chan_t *chan = cxdma_get_chan(ch);
	int ret = -EINVAL;
	unsigned long flags;

	if (!chan || !dma_enabled(chan))
		return -EINVAL;
	chan_log(ch, "dma_reset_channel");
	LOCK(chan);
	if (dma_enabled(chan) && !dma_suspended(chan)) {
		udif_list_head_init(&chan->pending_list);
		chan->cur = NULL;
		hw_cxdma_stop(chan);
		ret = 0;
	}
	UNLOCK(chan);
	return ret;
}
EXPORT_SYMBOL(dma_reset_channel);
