/*
 *  arch/arm/mach-emxx/phyadr/phyadr_drv.c
 *  PHYADR0 interface
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

#include "phyadr.h"

#ifdef CONFIG_SNSC_HSS
#include <linux/snsc_hss.h>
#endif  /* #ifdef CONFIG_SNSC_HSS */

static int phyadr_major = 0;
static dev_t t_dev;
static struct cdev phyadr_cdev;

#ifdef CONFIG_SNSC_HSS
struct hss_node* phyadr_hss_node;
#endif  /* #ifdef CONFIG_SNSC_HSS */

/** copy from user
 * @brief  ｛copy_from_userシステムファンクションリライト｝copy_from_userシステムファンクションをリライトする。
 * @param[OUT] なし
 * @param[IN] <<dst>> 目的アドレス
 * @param[IN] <<src>> 元アドレス
 * @param[IN] <<size>> データサイズ
 * @return なし
 * @pre なし
 * @post なし
 * @attention なし
 */

static int phyadr_copy_from_user(char* dst, const char* src, unsigned int size)
{
    int ret = 0;

    ret = copy_from_user(dst, src, size);
    if (ret < 0) {
        return -EFAULT;
    }
    return 0;
}

/** copy to user
 * @brief  ｛copy_to_userシステムファンクションリライト｝copy_to_userシステムファンクションをリライトする。
 * @param[OUT] <<dst>> 目的アドレス
 * @param[IN] <<src>> 元アドレス
 * @param[IN] <<size>> データサイズ
 * @return なし
 * @pre なし
 * @post なし
 * @attention なし
 */
static int phyadr_copy_to_user(char* dst, char* src, unsigned int size)
{
    int ret = 0;

    ret = copy_to_user(dst, src, size);
    if (ret < 0) {
        return -EFAULT;
    }

    return 0;
}

/**
 * @brief write unsigned long val to hardware port
 * @param[OUT] <<spPhyadr_cmd_info->buf>> データバッファエリアのヘッダーポインタを返す
 * @param[IN]  <<spPhyadr_cmd_info->address>> レジスタ先頭アドレス
 * @param[IN]  <<spPhyadr_cmd_info->value>> 書き込み値
 * @param[IN]  <<spPhyadr_cmd_info->mask>> 変更したBitの指定ビット(0?不変,1?変更)
 * @param[IN]  <<spPhyadr_cmd_info->length>> 書き/読みデータ長 no use
 * @return ｛phyadrデバイ状態｝phyadrデバイの状態を戻す
 * @pre なし
 * @post なし
 * @attention なし
 */
static int PhyAdrWrite(PHYADR_CMD_INFO* spPhyadr_cmd_info)
{
    int ret = 0;
    unsigned long val = 0;
    void __iomem* base_addr = NULL;
    base_addr = ioremap_nocache(spPhyadr_cmd_info->address, sizeof(long));
    if(NULL == base_addr) {
        printk("Error occurred at ioremap_nocache.");
        ret = -EFAULT;
        return ret;
    }
    val = ioread32(base_addr);
    val &= ~spPhyadr_cmd_info->mask;
    val |= (spPhyadr_cmd_info->value & spPhyadr_cmd_info->mask);
    iowrite32(val, base_addr);
    val = ioread32(base_addr);
    if(phyadr_copy_to_user((char*)spPhyadr_cmd_info->buf, (char*)&val, sizeof(long))) {
        printk(KERN_INFO "%s():%d copy error\n", __func__, __LINE__);
        ret = -EFAULT;
    }
    iounmap(base_addr);
    return ret;
}

/**
 * @brief read unsigned long val from hardware port
 * @param[OUT] <<spPhyadr_cmd_info->buf>> データバッファエリアのヘッダーポインタを返す
 * @param[IN]  <<spPhyadr_cmd_info->address>> レジスタ先頭アドレス
 * @param[IN]  <<spPhyadr_cmd_info->value>> 書き込み値 no use
 * @param[IN]  <<spPhyadr_cmd_info->mask>> 変更したBitの指定ビット(0?不変,1?変更) no use
 * @param[IN]  <<spPhyadr_cmd_info->length>> 書き/読みデータ長 no use
 * @return ｛phyadrデバイ状態｝phyadrデバイの状態を戻す
 * @pre なし
 * @post なし
 * @attention なし
 */
static int PhyAdrRead(PHYADR_CMD_INFO* spPhyadr_cmd_info)
{
    int ret = 0;
    unsigned long val = 0;
    void __iomem* base_addr = NULL;
    base_addr = ioremap_nocache(spPhyadr_cmd_info->address, sizeof(long));
    if(NULL == base_addr) {
        printk("Error occurred at ioremap_nocache.");
        ret = -EFAULT;
        return ret;
    }
    val = ioread32(base_addr);
    if(phyadr_copy_to_user((char*)spPhyadr_cmd_info->buf, (char*)&val, sizeof(long))) {
        printk(KERN_INFO "%s():%d copy error\n", __func__, __LINE__);
        ret = -EFAULT;
    }
    iounmap(base_addr);
    return ret;
}

/** copy to user
 * @brief read unsigned long val from hardware port
 * @param[OUT] <<spPhyadr_cmd_info->buf>> データバッファエリアのヘッダーポインタを返す
 * @param[IN]  <<spPhyadr_cmd_info->address>> レジスタ先頭アドレス
 * @param[IN]  <<spPhyadr_cmd_info->value>> 書き込み値 no use
 * @param[IN]  <<spPhyadr_cmd_info->mask>> 変更したBitの指定ビット(0?不変,1?変更) no use
 * @param[IN]  <<spPhyadr_cmd_info->length>> 書き/読みデータ長
 * @return ｛phyadrデバイ状態｝phyadrデバイの状態を戻す
 * @pre なし
 * @post なし
 * @attention なし
 */
static int PhyAdrDump(PHYADR_CMD_INFO* spPhyadr_cmd_info)
{
    int i = 0;
    int ret = 0;
    unsigned long val = 0;
    void __iomem* base_addr = NULL;
    base_addr = ioremap_nocache(spPhyadr_cmd_info->address, spPhyadr_cmd_info->length);
    if(NULL == base_addr) {
        printk("Error occurred at ioremap_nocache.\n");
        ret = -EFAULT;
        return ret;
    }
    for(i = 0; i < spPhyadr_cmd_info->length; i += sizeof(long)) {
        val = ioread32(base_addr + i);
        if(phyadr_copy_to_user((char*)(spPhyadr_cmd_info->buf + i), (char*)&val, sizeof(long))) {
            printk(KERN_INFO "%s():%d copy error\n", __func__, __LINE__);
            ret = -EFAULT;
            break;
        }
    }
    iounmap(base_addr);
    return ret;
}

/**
 * @brief malloc memory
 * @param[OUT] <<spPhyadr_cmd_info->buf>> データバッファエリアのヘッダーポインタを返す
 * @param[IN]  <<spPhyadr_cmd_info->address>> レジスタ先頭アドレス no use
 * @param[IN]  <<spPhyadr_cmd_info->value>> 書き込み値 no use
 * @param[IN]  <<spPhyadr_cmd_info->mask>> 変更したBitの指定ビット(0?不変,1?変更) no use
 * @param[IN]  <<spPhyadr_cmd_info->length>> 書き/読みデータ長
 * @return ｛phyadrデバイ状態｝phyadrデバイの状態を戻す
 * @pre なし
 * @post なし
 * @attention なし
 */
static int PhyAdrMalloc(PHYADR_CMD_INFO* spPhyadr_cmd_info)
{
    int ret = 0;
    unsigned long val = 0;
    void* kmallocmem = NULL;
    kmallocmem = kmalloc(spPhyadr_cmd_info->length, GFP_USER | __GFP_DMA);
    if(NULL == kmallocmem) {
        printk("Error occurred at kmalloc %u length memory.\n", (unsigned int)spPhyadr_cmd_info->length);
        ret = -EFAULT;
        return ret;
    }
    val = virt_to_phys(kmallocmem);
    if(phyadr_copy_to_user((char*)spPhyadr_cmd_info->buf, (char*)&val, sizeof(long))) {
        printk(KERN_INFO "%s():%d copy error\n", __func__, __LINE__);
        ret = -EFAULT;
    }
    return ret;
}

/**
 * @brief free memory
 * @param[OUT] <<spPhyadr_cmd_info->buf>> データバッファエリアのヘッダーポインタを返す
 * @param[IN]  <<spPhyadr_cmd_info->address>> レジスタ先頭アドレス
 * @param[IN]  <<spPhyadr_cmd_info->value>> 書き込み値 no use
 * @param[IN]  <<spPhyadr_cmd_info->mask>> 変更したBitの指定ビット(0?不変,1?変更) no use
 * @param[IN]  <<spPhyadr_cmd_info->length>> 書き/読みデータ長 no use
 * @return ｛phyadrデバイ状態｝phyadrデバイの状態を戻す
 * @pre なし
 * @post なし
 * @attention なし
 */
static int PhyAdrFree(PHYADR_CMD_INFO* spPhyadr_cmd_info)
{
    int ret = 0;
    void* kmallocmem = NULL;
    kmallocmem = phys_to_virt(spPhyadr_cmd_info->address);
    if(NULL == kmallocmem) {
        printk("Error occurred at kfree addr:0x%08x.", (unsigned int)spPhyadr_cmd_info->address);
        ret = -EFAULT;
        return ret;
    }
    kfree(kmallocmem);
    return ret;
}
/**
 * @brief suspend phyadr driver with hss-framework
 * @param[OUT] none
 * @param[IN] hss_node
 * @return    0
 * @pre       none
 * @post      none
 * @attention none
 */
static int phyadr_suspend(struct hss_node* hss_node)
{
    return 0;
}
/**
 * @brief resume phyadr driver with hss-framework
 * @param[OUT] none
 * @param[IN] hss_node
 * @return    0
 * @pre       none
 * @post      none
 * @attention none
 */
static int phyadr_resume(struct hss_node* hss_node)
{
    return 0;
}
/** ioctl
 * @brief  {phyadr1デバイスioctl操作｝phyadr1デバイスのioctl操作を行う。
 * @param[OUT] <<arg>> ユーザー定義する命令パラメーター
 * @param[IN] <<dev>> デバイス番号
 * @param[IN] <<inode>> 標準のlinuxデバイスドライバーパラメーター
 * @param[IN] <<file>> 標準のlinuxデバイスドライバーパラメーター
 * @param[IN] <<cmd>> ユーザー定義する命令
 * @param[IN] <<arg>> ユーザー定義する命令パラメーター
 * @return ｛phyadrデバイ状態｝phyadrデバイの状態を戻す
 * @pre なし
 * @post なし
 * @attention なし
 */
int phyadr_ioctl(struct inode* inode, struct file* filp,
                 unsigned int cmd, unsigned long arg)
{
    int ret = 0;
    PHYADR_CMD_INFO tempCMDInfo = {0};
    if (phyadr_copy_from_user((char*)&tempCMDInfo, (char*)arg, sizeof(PHYADR_CMD_INFO))) {
        printk(KERN_INFO "%s():%d copy error\n", __func__, __LINE__);
        ret = -EFAULT;
        return ret;
    }
    switch (cmd) {
    case PHYADR_IOCWRITE:
        ret = PhyAdrWrite(&tempCMDInfo);
        break;
    case PHYADR_IOCREAD:
        ret = PhyAdrRead(&tempCMDInfo);
        break;
    case PHYADR_IOCDUMP:
        ret = PhyAdrDump(&tempCMDInfo);
        break;
    case PHYADR_IOCMALLOC:
        ret = PhyAdrMalloc(&tempCMDInfo);
        break;
    case PHYADR_IOCFREE:
        ret = PhyAdrFree(&tempCMDInfo);
        break;
    default:
        /* error */
        ret = -EINVAL;
        break;
    }
    return ret;
}

/* file operations info (PHYADR0) */
static const struct file_operations phyadr_fops = {
    .ioctl = phyadr_ioctl,
    .owner = THIS_MODULE,
};

#ifdef CONFIG_SNSC_HSS
static struct hss_node_ops hss_phyadr_node_ops = {
    .suspend = phyadr_suspend,
    .resume = phyadr_resume,
};
#endif  /* #ifdef CONFIG_SNSC_HSS */

/** initialize
 * @brief  {ドライバー初期化}ドライバーを初期化する。
 * @param[OUT] なし
 * @param[IN] なし
 * @return {ドライバー初期化した状態}　ドライバーの初期化した状態を戻す
 * @pre 初めてドライバーを初期化しました
 * @post なし
 * @attention なし
 */
static int __init phyadr_init(void)
{
    int result = 0;
    int minor_num_start = 0;
    int dev_count = 1;

#ifdef CONFIG_SNSC_HSS
    int error = 0;

    /*
     * alloc the HSS node
     */
    phyadr_hss_node = hss_alloc_node(PHYADR_HSS_NODE_NAME);
    if (!phyadr_hss_node) {
      printk(KERN_INFO "%s(): alloc_node(phyadr) failed\n", __func__);
      return -ENOMEM;
    }

    /*
     * Register the node.  If you want to get the callbacks to be called
     * before the specified node's one, specify the third parameter with
     * the name of the parent node. NULL means for no parent needed.
     */
    error = hss_register_node(phyadr_hss_node, &hss_phyadr_node_ops, PHYADR_HSS_NODE_PARENT);
    if (error) {
      printk(KERN_INFO "%s: register_node(phyadr) failed\n", __func__);
      hss_free_node(phyadr_hss_node);
      return error;
    }
#endif  /* #ifdef CONFIG_SNSC_HSS */

    if (phyadr_major) {
        t_dev  = MKDEV(phyadr_major, minor_num_start);
        result = register_chrdev_region(t_dev, dev_count, PHYADR_NAME);
    } else {
        result = alloc_chrdev_region(&t_dev, minor_num_start,
                                     dev_count, PHYADR_NAME);
        phyadr_major  = MAJOR(t_dev);
    }
    if (result < 0) {
        printk(KERN_ERR "phyadr: can't get major number.\n");
        goto fail_get_major;
    }

    cdev_init(&phyadr_cdev, &phyadr_fops);
    phyadr_cdev.owner = THIS_MODULE;

    result = cdev_add(&phyadr_cdev, t_dev, dev_count);
    if (result) {
        goto fail_cdev_add;
    }

    printk(KERN_INFO "phyadr: registered device phyadr [phyadr]\n");

    goto success;

fail_cdev_add:
    unregister_chrdev_region(t_dev, dev_count);
fail_get_major:
success:

    return result;
}

/** exit
 * @brief  ｛ドライバーアンロード｝ドライバーをアンロードする。
 * @param[OUT] なし
 * @param[IN] なし
 * @return なし
 * @pre phyadr もうドライバーを初期化しました
 * @post なし
 * @attention なし
 */
static void __exit phyadr_exit(void)
{
#ifdef CONFIG_SNSC_HSS
    hss_unregister_node(phyadr_hss_node);
    hss_free_node(phyadr_hss_node);
#endif  /* #ifdef CONFIG_SNSC_HSS */
    cdev_del(&phyadr_cdev);
    unregister_chrdev_region(t_dev, 1);
}

module_init(phyadr_init);
module_exit(phyadr_exit);
MODULE_LICENSE("GPL");
