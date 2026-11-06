/*
 * driver/misc/cxd/dma/module.c
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

#include <linux/udif/module.h>

#include "internal.h"

static unsigned int cxdma_ch_map;
module_param_named(map, cxdma_ch_map, uint, S_IRUSR);

#define N_CHAN 8
static unsigned char cxdma_prio[4][N_CHAN];
module_param_array_named(prio0, cxdma_prio[0], byte, NULL, S_IRUSR);
module_param_array_named(prio1, cxdma_prio[1], byte, NULL, S_IRUSR);
module_param_array_named(prio2, cxdma_prio[2], byte, NULL, S_IRUSR);
module_param_array_named(prio3, cxdma_prio[3], byte, NULL, S_IRUSR);

static unsigned char cxdma_src_osr[4][N_CHAN];
module_param_array_named(osrS0, cxdma_src_osr[0], byte, NULL, S_IRUSR);
module_param_array_named(osrS1, cxdma_src_osr[1], byte, NULL, S_IRUSR);
module_param_array_named(osrS2, cxdma_src_osr[2], byte, NULL, S_IRUSR);
module_param_array_named(osrS3, cxdma_src_osr[3], byte, NULL, S_IRUSR);

static unsigned char cxdma_dst_osr[4][N_CHAN];
module_param_array_named(osrD0, cxdma_dst_osr[0], byte, NULL, S_IRUSR);
module_param_array_named(osrD1, cxdma_dst_osr[1], byte, NULL, S_IRUSR);
module_param_array_named(osrD2, cxdma_dst_osr[2], byte, NULL, S_IRUSR);
module_param_array_named(osrD3, cxdma_dst_osr[3], byte, NULL, S_IRUSR);

static chan_t dma_chan_ctrl[N_DMA_CH];

chan_t *cxdma_get_chan(uint ch)
{
	if (ch >= N_DMA_CH)
		return NULL;
	return &dma_chan_ctrl[ch];
}

static UDIF_INIT UDIF_ERR cxdma_init(UDIF_VP data)
{
	cxdma_cdev_init();
#ifdef CONFIG_PROC_FS
	cxdma_proc_init();
#endif
	return UDIF_ERR_OK;
}

static UDIF_EXIT UDIF_ERR cxdma_exit(UDIF_VP data)
{
	cxdma_cdev_exit();
#ifdef CONFIG_PROC_FS
	cxdma_proc_exit();
#endif
	return UDIF_ERR_OK;
}

static void dma_stat_init(struct dma_stat *stat)
{
	memset(stat, 0, sizeof *stat);
}

static UDIF_ERR cxdma_probe(const UDIF_DEVICE *dev, UDIF_CH ch, UDIF_VP data)
{
	int i;
	chan_t *chan;
	struct hw_cxdma_conf cfg;

	for (i = 0, chan = dma_chan_ctrl; i < N_DMA_CH; i++, chan++) {
		/* initialize dma_chan_ctrl */
		chan->ch = i;
		udif_spin_lock_init(&chan->lock);
		chan->flag = 0U;
		udif_list_head_init(&chan->pending_list);
		chan->cur = NULL;
		dma_stat_init(&chan->stat);

		cfg.priority   = cxdma_prio[i / N_CHAN][i % N_CHAN];
		cfg.src_outstanding = cxdma_src_osr[i / N_CHAN][i % N_CHAN];
		cfg.dst_outstanding = cxdma_dst_osr[i / N_CHAN][i % N_CHAN];
		cfg.qos         = 0;
		hw_cxdma_config(chan, &cfg);

		/* use dma_mem_transfer_async ? */
		if (!(cxdma_ch_map & BIT(i)))
			continue;

		if (hw_cxdma_open(chan) < 0) {
			continue;
		}
		dma_flag_set_enable(chan);
	}
	return UDIF_ERR_OK;
}

static UDIF_ERR cxdma_remove(const UDIF_DEVICE *dev, UDIF_CH ch, UDIF_VP data)
{
	int i;
	chan_t *chan;
	unsigned long flags;

	for (i = 0, chan = dma_chan_ctrl; i < N_DMA_CH; i++, chan++) {
		LOCK(chan);
		if (dma_enabled(chan)) {
			hw_cxdma_close(chan);
			dma_flag_clr_enable(chan);
		}
		UNLOCK(chan);
	}
	return UDIF_ERR_OK;
}

#ifdef CONFIG_PM
static UDIF_ERR cxdma_suspend(const UDIF_DEVICE *dev, UDIF_CH ch, UDIF_VP data)
{
	int i;
	chan_t *chan;
	unsigned long flags;

	for (i = 0, chan = dma_chan_ctrl; i < N_DMA_CH; i++, chan++) {
		LOCK(chan);
		if (dma_enabled(chan)) {
			dma_flag_set_suspend(chan);
			udif_list_head_init(&chan->pending_list);
			chan->cur = NULL;
			hw_cxdma_stop(chan);
		}
		UNLOCK(chan);
	}
	return UDIF_ERR_OK;
}

static UDIF_ERR cxdma_resume(const UDIF_DEVICE *dev, UDIF_CH ch, UDIF_VP data)
{
	int i;
	chan_t *chan;
	unsigned long flags;

	for (i = 0, chan = dma_chan_ctrl; i < N_DMA_CH; i++, chan++) {
		LOCK(chan);
		if (dma_enabled(chan)) {
			dma_flag_clr_suspend(chan);
		}
		UNLOCK(chan);
	}
	return UDIF_ERR_OK;
}
#endif /* CONFIG_PM */

static UDIF_DRIVER_OPS cxdma_ops = {
	.init		= cxdma_init,
	.exit		= cxdma_exit,
	.probe		= cxdma_probe,
	.remove		= cxdma_remove,
#ifdef CONFIG_PM
	.suspend	= cxdma_suspend,
	.resume		= cxdma_resume,
#endif
};

UDIF_IDS(cxdma_ids) = {};
UDIF_DEPS(cxdma_deps) = {};
UDIF_DECLARE_DRIVER(udif_cxdma, DRV_NAME, DRV_VER, &cxdma_ops, cxdma_ids, cxdma_deps, NULL);

static int __init __udif_init_cxdma(void)
{
	UDIF_DRIVER *drv = &udif_cxdma;
	return udif_driver_register(&drv, 1);
}
late_initcall(__udif_init_cxdma);
