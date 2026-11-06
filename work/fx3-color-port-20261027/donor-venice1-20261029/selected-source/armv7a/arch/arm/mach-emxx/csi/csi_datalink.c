/*
 *  arch/arm/mach-emxx/csi/csi_datalink.c
 *  CSI_DATALINK interface
 *
 *  Copyright 2011 Sony Corporation
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
 */

#include <linux/module.h>
#include <linux/init.h>
#include <linux/poll.h>
#include <linux/delay.h>
#include <linux/dma-mapping.h>
#include <linux/interrupt.h>
#include <linux/cdev.h>
#include <linux/vmalloc.h>
#include <linux/io.h>
#include <linux/gpio.h>
#include <linux/spinlock.h>

#include <linux/time.h>

#include <asm/mach/irq.h>
#include <stdbool.h>
#include <mach/spi.h>
#include "csi_datalink.h"

#ifdef CONFIG_SNSC_HSS
#include <linux/snsc_hss.h>
#endif /* #ifdef CONFIG_SNSC_HSS */

#define CSI_DL_PACKET_LENGTH 384
#define CSI_DL_HIGH_V 1
#define CSI_DL_LOW_V  0
#define CSI_DL_PEN GPIO_P10
#define CSI_DL_RDY GPIO_P3
#define IS_SPI1_CONTROL_TX_FULL (inl(0xe0011008) & 0x00000080)
#define CLR_GPIO_010_INTERRUPT outl(0x04000400,0xe0050058)
#define ENABLE_GPIO_010_003_PINS(n) (n) = inl(0xe0140200);  \
    (n) |= 0x00000408; \
    outl((n),0xe0140200);   \
    (n) = inl(0xe0140338);  \
    (n) |= 0x00000005; \
    outl((n),0xe0140338);   \
    (n) = inl(0xe0140350);  \
    (n) |= 0x00001000; \
    outl((n),0xe0140350)
#define SET_GPIO_010_INTERRUPT_ASYNCHRONOUS(n)  (n) = inl(0xe0050044); \
    (n) &= 0xfffff0ff;\
    (n) |= 0x00000900;\
    outl((n),0xe0050044)
#define SET_SPI1_CS0_PULLDOWN(n) (n) = inl(0xe0140334); \
    (n) &= 0xffff0fff;\
    (n) |= 0x00007000;\
    outl((n),0xe0140334)

unsigned long csi_dl_dma_dummy_send_p;
unsigned long csi_dl_dma_send_p;
static unsigned long csi_dl_dma_receive_p;
static void (* pdma_irq_callback_func)(unsigned long* pdmareceive);
static void (* ppen_irq_callback_func)(unsigned long* pdmasend);

#define USE_DMA_ALLOC_COHERENT      1

#define CSI_READY_TRUE   1
#define CSI_READY_FALSE  0
#define CSI_FIRSTPKT_TRUE  1
#define CSI_FIRSTPKT_FALSE 0

#define TIME_DELAY ((10)*(HZ))    /* 10s delay */

unsigned int csi_lowlevel_count = 1;
static void csi_timeout_function(unsigned long data);
static volatile unsigned int csi_drv_rdy_flag = CSI_READY_FALSE;
static volatile unsigned int csi_firstpkt_flag = CSI_FIRSTPKT_TRUE;
static struct timer_list csi_handshake_timer = {0};

#ifdef CONFIG_SNSC_HSS
static int csi_dl_hss_node_suspend(struct hss_node *node);
static int csi_dl_hss_node_resume(struct hss_node *node);
static int csi_dl_hss_platform_drv(void);

static struct hss_csi_dl_info {
    struct hss_node *node;
};
struct hss_csi_dl_info *p_hss_csi_dl_info;
#endif /* #ifdef CONFIG_SNSC_HSS */

/*
** @brief configuration of spi_dev
*/
static SPI_CONFIG device1_config = {
    .dev    = SPI_DEV_SP1,
    .cs_sel = SPI_CS_SEL_CS0,
    .m_s    = SPI_M_S_SLAVE,
    .dma    = SPI_DMA_ON,
    .pol    = SPI_CSW_8CLK | SPI_CK_DLY_OFF | SPI_CK_POL_POS | SPI_CS_POL_NEG,
    .tiecs  = SPI_TIECS_NORMAL,
    .nbw    = SPI_NB_16BIT,
    .nbr    = SPI_NB_16BIT,
    .sclk   = SPI_SCLK_12MHZ,
};

/**
 * @brief set kernel flag
 * @param[OUT] None
 * @param[IN] None
 * @return None
 * @pre None
 * @post None
 * @attention None
 */
void csi_drv_rdyflag_init(void)
{
    static unsigned long spin_lock_rdyflag = 0;
    static spinlock_t csi_drv_rdy_lock = SPIN_LOCK_UNLOCKED;

    spin_lock_irqsave(&csi_drv_rdy_lock, spin_lock_rdyflag);
    if (!csi_drv_rdy_flag) {
        csi_drv_rdy_flag = CSI_READY_TRUE;
        if (CSI_DL_LOW_V == gpio_get_value(CSI_DL_PEN)) {
            if (csi_firstpkt_flag) {
                csi_firstpkt_flag = CSI_FIRSTPKT_FALSE;
            }

            CLR_GPIO_010_INTERRUPT;/* clear interrupt */

            spin_unlock_irqrestore(&csi_drv_rdy_lock, spin_lock_rdyflag);
            csi_lowlevel_callback();
            return;
        }
    }
    spin_unlock_irqrestore(&csi_drv_rdy_lock, spin_lock_rdyflag);

    return;
}

/**
 * @brief timeout warning
 * @param[OUT] None
 * @param[IN] data
 * @return None
 * @pre None
 * @post None
 * @attention None
 */
static void csi_timeout_function(unsigned long data)
{
    csi_handshake_timer.function = NULL;
    printk("[--CSI_DRV--] Csi_handshake is timeout !!\n");
    return;
}

/**
 * @brief set call back func pointer
 * @param[OUT] None
 * @param[IN] call back func pointer
 * @return status of the csi_dl_init
 * @pre this module has been installed
 * @post None
 * @attention pFunc pointer can not be NULL
 */
int csi_dl_init(void* pfuncdmacallback, void* pfuncpencallback, unsigned long dma_dummy_send_p, unsigned long dma_receive_p)
{
    int ret = 0;

    pdma_irq_callback_func = pfuncdmacallback;
    ppen_irq_callback_func = pfuncpencallback;

    csi_dl_dma_dummy_send_p = dma_dummy_send_p;
    csi_dl_dma_receive_p = dma_receive_p;
    csi_dl_dma_send_p = dma_dummy_send_p;

    return ret;
}
EXPORT_SYMBOL(csi_dl_init);

/**
 * @brief set DMA pointers and trans one packet
 * @param[OUT] None
 * @param[IN] DMA_send_p DMA transfer send head pointer
 * @param[IN] DMA_receive_p DMA transfer receive head pointer
 * @return status of this process
 * @pre
 * @post None
 * @attention slave want transfer packet as sponsor whatever master status now
 */
int csi_dl_send_packet(unsigned long dma_send_p, unsigned int number)
{
    static unsigned long csi_send_flag = 0UL;
    static spinlock_t csi_lock = SPIN_LOCK_UNLOCKED;
    int ret = 0;
    spin_lock_irqsave(&csi_lock, csi_send_flag);
    if (csi_firstpkt_flag) {
        csi_firstpkt_flag = CSI_FIRSTPKT_FALSE;

        /* init timer */
        init_timer(&csi_handshake_timer);
        csi_handshake_timer.expires = jiffies + TIME_DELAY; /* 10s delay */
        csi_handshake_timer.data = 0;
        csi_handshake_timer.function = csi_timeout_function;
        add_timer(&csi_handshake_timer);  /* start timer */

    }
    spin_unlock_irqrestore(&csi_lock, csi_send_flag);

    if (0 == number) {
        while (CSI_DL_LOW_V == gpio_get_value(CSI_DL_PEN)) {
            udelay(1);
            ret++;
            if (ret > 60) {
                break;
            }
        }
    }

    spin_lock_irqsave(&csi_lock, csi_send_flag);

    if (CSI_DL_LOW_V == gpio_get_value(CSI_DL_RDY)) {
        spin_unlock_irqrestore(&csi_lock, csi_send_flag);
        /* delete unuse log */
        /*printk("\n ##### DMA RDY IS LOW #####  \n");*/
        return -1;
    }

    csi_dl_dma_send_p = dma_send_p;
    ret = spi1_csi_fdx_rw(&device1_config, csi_dl_dma_send_p, csi_dl_dma_receive_p, CSI_DL_PACKET_LENGTH);
    if (ret < 0) {
        printk(KERN_INFO "%s(): spi1_csi_FDX_RW error %d\n", __func__, ret);
        ret = -1;
    }
    gpio_set_value(CSI_DL_RDY, CSI_DL_LOW_V);

    spin_unlock_irqrestore(&csi_lock, csi_send_flag);

    return ret;
}
EXPORT_SYMBOL(csi_dl_send_packet);

/**
 * @brief  callback function
 * @param[IN]  None
 * @param[OUT]  None
 * @return None
 * @pre None
 * @post None
 * @attention None
 */
void csi_lowlevel_callback(void)
{
    int ret;
    ppen_irq_callback_func(&csi_dl_dma_send_p);
    ret = spi1_csi_fdx_rw(&device1_config, csi_dl_dma_send_p, csi_dl_dma_receive_p, CSI_DL_PACKET_LENGTH);
    if (ret < 0) {
        printk(KERN_INFO "%s():%d spi1_csi_FDX_RW error %d\n", __func__, __LINE__, ret);
        ret = -1;
    }
    gpio_set_value(CSI_DL_RDY, CSI_DL_LOW_V);

    return;
}

/**
 * @brief  handle PEN irq interrupt
 * @param[IN]  <<irq>> Num of interrupt
 * @param[IN]  <<id>>  interrupt info
 * @return status of this process
 * @pre None
 * @post None
 * @attention None
 */
static irqreturn_t csi_dl_pen_irq_handler(int irq, void* id)
{
    int ret;
    csi_lowlevel_count++;

    if (csi_firstpkt_flag) {
        csi_firstpkt_flag = CSI_FIRSTPKT_FALSE;
    }

    if (csi_handshake_timer.function) {
        del_timer(&csi_handshake_timer);
        csi_handshake_timer.function = NULL;
    }
    if (!csi_drv_rdy_flag) {
        printk(KERN_WARNING "csi driver is not ready !!!\n");
        return IRQ_HANDLED;
    }

    CLR_GPIO_010_INTERRUPT;/* clear interrupt */

    if (CSI_DL_HIGH_V != gpio_get_value(CSI_DL_PEN)) {
        if (0 != csi_dl_dma_receive_p) {
            if (gpio_get_value (CSI_DL_RDY) == CSI_DL_LOW_V) {
                return IRQ_HANDLED;
            }

            ppen_irq_callback_func(&csi_dl_dma_send_p);
            ret = spi1_csi_fdx_rw(&device1_config, csi_dl_dma_send_p, csi_dl_dma_receive_p, CSI_DL_PACKET_LENGTH);
            if (ret < 0) {
                printk(KERN_INFO "%s():%d spi1_csi_FDX_RW error %d\n", __func__, __LINE__, ret);
                ret = -1;
            }
            gpio_set_value(CSI_DL_RDY, CSI_DL_LOW_V);
        }
    }
    return IRQ_HANDLED;
}

/**
 * @brief initiate conditions of gpio install handler of gpio interrupt
 * @param[OUT] None
 * @param[IN] None
 * @return status of this process
 * @pre
 * @post None
 * @attention None
 */
static int csi_dl_gpio_init(void)
{
    int irq  = 0;
    int ret = 0;
    unsigned int val = 0;
    ENABLE_GPIO_010_003_PINS(val);
    irq = gpio_to_irq(CSI_DL_PEN);
    set_irq_type(irq, IRQ_TYPE_EDGE_FALLING); /* interrupt detection mode setup IRQ_TYPE_EDGE_FALLING */
    SET_GPIO_010_INTERRUPT_ASYNCHRONOUS(val);

    enable_irq(irq);
    gpio_direction_input(CSI_DL_PEN);/* input */
    ret = request_irq(INT_GPIO_BASE + CSI_DL_PEN, csi_dl_pen_irq_handler, IRQF_DISABLED, "CSIDLGPIO", NULL);
    if (ret) {
        printk(KERN_INFO"%s():%d irq request failed \n", __func__, __LINE__);
    }

    gpio_set_value(CSI_DL_RDY, CSI_DL_HIGH_V);/* RDYHigh */
    gpio_direction_output(CSI_DL_RDY, 1); /* output */

    return ret;
}

/**
 * @brief enable PEN interrupt
 * @param[OUT] None
 * @param[IN] None
 * @return normal
 * @pre
 * @post None
 * @attention None
 */
void csi_dl_enable_pen(void)
{
    unsigned long val = 0UL;
    val = inl(0xe0050014);
    val |= 0x00000400;
    outl(val, 0xe0050014);
    return;
}
EXPORT_SYMBOL(csi_dl_enable_pen);

/**
 * @brief disable PEN interrupt
 * @param[OUT] None
 * @param[IN] None
 * @return normal
 * @pre
 * @post None
 * @attention None
 */
void csi_dl_disable_pen(void)
{
    unsigned long val = 0UL;
    val = inl(0xe0050014);
    val &= ~0x00000400;
    outl(val, 0xe0050014);
    return;
}
EXPORT_SYMBOL(csi_dl_disable_pen);

/**
 * @brief  clear conditions of gpio free interrupt handler
 * @param[OUT] None
 * @param[IN] None
 * @return normal
 * @pre
 * @post None
 * @attention None
 */
static int csi_dl_gpio_exit(void)
{
    int irq  = 0;
    irq = gpio_to_irq(CSI_DL_PEN);
    disable_irq(irq);
    free_irq(INT_GPIO_BASE + CSI_DL_PEN, NULL);
    return 0;
}

/**
 * @brief  handle spi1 DMA IRQ as call back func
 * @param[OUT] None
 * @param[IN] <<err>> DMA error
 * @return normal
 * @pre
 * @post None
 * @attention None
 */
static void csi_dl_response_dma_irq(int err)
{
    csi_dl_dma_send_p = csi_dl_dma_dummy_send_p;
#ifndef USE_DMA_ALLOC_COHERENT
    dma_sync_single_for_device(NULL, csi_dl_dma_receive_p, CSI_DL_PACKET_LENGTH, DMA_FROM_DEVICE);
#endif
    if (pdma_irq_callback_func) {
        pdma_irq_callback_func(&csi_dl_dma_receive_p);
    }
}

#ifdef CONFIG_SNSC_HSS
static struct hss_node_ops hss_csi_dl_node_ops = {
    .suspend = csi_dl_hss_node_suspend,
    .resume = csi_dl_hss_node_resume,
};

static int csi_dl_hss_node_suspend(struct hss_node *node)
{
    csi_dl_gpio_exit();
    return 0;
}

static int csi_dl_hss_node_resume(struct hss_node *node)
{
    int result = 0;
    unsigned long val = 0UL;

    SET_SPI1_CS0_PULLDOWN(val);
    result = csi_dl_gpio_init();
    return result;
}

static int csi_dl_hss_platform_drv(void)
{
    struct hss_node *node;
    int err = 0;

    /* alloc for csi info */
    p_hss_csi_dl_info = kzalloc(sizeof(*p_hss_csi_dl_info), GFP_KERNEL);
    if (p_hss_csi_dl_info == NULL) {
        err = -ENOMEM;
        return err;
    }

    /*
     * alloc the HSS node
     */
    node = hss_alloc_node(CSI_DL_E_HSS_NODE_NAME);
    if (node == NULL) {
        kfree(p_hss_csi_dl_info);
        err = -ENOMEM;
        return err;
    }

    /*
     * save struct to HSS
     */
    hss_set_private(node, p_hss_csi_dl_info);
    p_hss_csi_dl_info->node = node;

    /*
     * Register the node.  If you want to get the callbacks to be called
     * before the specified node's one, specify the third parameter with
     * the name of the parent node. NULL means for no parent needed.
     */

    /* register HSS Platform for suspend/resume */
    err = hss_register_node(node, &hss_csi_dl_node_ops, CSI_DL_E_HSS_NODE_NAME_PARENT);

    if (err != 0) {
        kfree(p_hss_csi_dl_info);
        return err;
    }

    return err;
}
#endif /* #ifdef CONFIG_SNSC_HSS */

/** initialize
 * @brief  datalink driver install
 * @param[OUT] None
 * @param[IN] None
 * @return status of install
 * @pre spi1 module has been complied into kernel
 * @post None
 * @attention None
 */
static int __init csi_dl_drv_init(void)
{
    int result = 0;
    unsigned long val = 0UL;

#ifdef CONFIG_SNSC_HSS
    /* register hss platform driver function */
    result = csi_dl_hss_platform_drv();
    if(result != 0) {
        return result;
    }
#endif /* #ifdef CONFIG_SNSC_HSS */

    SET_SPI1_CS0_PULLDOWN(val);
    spi_init_csicallbackfunc(csi_dl_response_dma_irq);
    result = csi_dl_gpio_init();
    return result;
}

/** exit
 * @brief  datalink driver uninstall
 * @param[OUT] None
 * @param[IN] None
 * @return None
 * @pre spi1 working in FDX way as part of kernel
 * @post None
 * @attention None
 */
static void __exit csi_dl_exit(void)
{
    csi_dl_gpio_exit();
#ifdef CONFIG_SNSC_HSS
    hss_unregister_node(p_hss_csi_dl_info->node);
    hss_free_node(p_hss_csi_dl_info->node);
    kfree(p_hss_csi_dl_info);
#endif /* #ifdef CONFIG_SNSC_HSS */
}

module_init(csi_dl_drv_init);
module_exit(csi_dl_exit);
MODULE_LICENSE("GPL");

