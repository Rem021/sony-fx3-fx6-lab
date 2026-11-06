// SPDX-License-Identifier:     GPL-2.0
/* Copyright 2022 Sony Corporation, SOCIONEXT INC. */

#include <linux/miscdevice.h>
#include <linux/device.h>
#include <linux/module.h>
#include <linux/uaccess.h>
#include <linux/printk.h>
#include <linux/io.h>
#include <linux/mm.h>
#include <linux/slab.h>
#include <linux/mutex.h>
#include <linux/completion.h>
#include <linux/interrupt.h>
#include <linux/platform_device.h>
#include <linux/of.h>
#include <asm/memory.h>
#include <linux/delay.h>
#include <linux/string.h>
#include <linux/clk.h>
#include <linux/reset.h>
#include <linux/dma-mapping.h>
#include <linux/spinlock.h>

/* internal include */
#include "ldec_driver.h"
#include "ldec_drv.h"
#include "ldec_hw.h"
#include "ldec_reg.h"

/* DMAC */
#include <linux/dmac_lld.h>

/* system call declaration */
static long ldec_ioctl(struct file *file, unsigned int cmd, unsigned long arg);
/* device register functions */
static int __init ldec_init(void);
static void __exit ldec_exit(void);
static int ldec_probe(struct platform_device *pdev);
static int ldec_remove(struct platform_device *pdev);
static int ldec_suspend(struct platform_device *pdev, pm_message_t state);
static int ldec_resume(struct platform_device *pdev);

/* internal functions */
static int ldec_get_user_pages(ldec_trans_t *trans, void *p, uint32_t len);
static int ldec_trans_set( ldec_trans_t *trans, uint32_t ch , uint32_t srcflush );
#ifdef LDEC_TRANS_CPU			//CPU transfer mode
static void ldec_cpu_trans( trans_t *trans ); 
#else	/* LDEC_TRANS_CPU */	//DMA transfer mode
static int ldec_ll_dma_trans( ldec_trans_t *ldec_trans, uint32_t ch , uint32_t srcflush );
#endif	/* LDEC_TRANS_CPU */
static int ldec_clk_rst( uint32_t sw );

static void ldec_sw_reset( void );
static int ldec_system_reset( void );
static int ldec_check_busreq( void );
static void ldec_error_processing( void );

/* ldec functions */
static void ldechw_resource_init( void );
static void ldechw_lock( uint32_t type );
static int ldechw_set( uint32_t records , uint64_t dst_phys );
static int ldechw_wait( void );
static irqreturn_t ldechw_process(int, void *);

static int ldec_aclk_enable(void);
static void ldec_aclk_disable(void);

#define D_DRIVERNAME "ldec-driver"
#define D_DEVICENAME "cxd,ldec"


#ifdef LDEC_TRANS_CPU
	static void __iomem *iomem_ldec_slave;
#endif	/* LDEC_TRANS_CPU */

#define BUFFER_SIZE (4096)	//size of intermediate buffer must be 4096B (not implemented for other than 4096B)
#define INITIAL_LL_SIZE (4096)	//initial kmalloc size for LinkedList area must be 4096B (not implemented for other than 4096B)
#define LLI_SIZE (sizeof(LLD_DMAC_LINKLIST)) 	//size of LinkedListItem (sizeof(LLD_DMAC_LINKLIST)) must be 64B
#define INITIAL_PAGE_ARRAY_SIZE	(4096)	//size of kmalloc area to store start addresses of all pages

//#define LDEC_DMAC_CH_CONFIG	//LDEC deadlock work around: if use lld_dmac_set_config(), this definition is enabled.

/**
 * @brief ldec Driver Base address
 * 
 * store base address of LDEC register in probe function call
 */
static void __iomem *lld_ldec_base_addr;

/**
 * @brief ldec Driver Base address
 * 
 * store SRAM physical address of LDEC in probe function call
 */
static uint64_t lz77_slave;

/**
 * @brief ldec Driver Base address
 * 
 * store pointer of clock structure for aclk in probe function call
 */
static struct clk *aclk;

/**
 * @brief ldec Driver Base address
 * 
 * store pointer of clock structure for pclk in probe function call
 */
static struct clk *pclk;

/**
 * @brief ldec Driver Base address
 * 
 * store pointer of reset_control structure for LDEC reset in probe function call
 */
static struct reset_control *rst;

/**
 * @brief ldec Driver Base address
 * 
 * store slave physical address of LDEC in probe function call
 */
static uint64_t lz77_slave;

/**
 * @brief Storage of information for sysfs
 * 
 * store information returned from sysfs
 */
static ldec_decompress_t proc_info = {0};


/**
 * @brief Mutual exclusion for LDEC function
 * 
 * mutual exclusion for LDEC function
 */
static struct mutex	ldec_api_lock;			/* for LZ77DEC exclusion control */

/**
 * @brief Spinlock for ldec status
 *
 * Spinlock for ldec status
 */
static spinlock_t ldec_state_lock;

/**
 * @brief Mutual exclusion for sysfs information access
 * 
 * Mutual exclusion for sysfs information access
 */
static struct mutex	ldec_proc_lock;

/**
 * @brief ldec interrupt enable/disable information
 * 
* keep ldec interrupt status (enabled or disabled)
 */
static volatile uint32_t ldechw_enable_set = LDECHW_DISABLE;

/**
 * @brief resource for wait_event information
 * 
 * used for wait to start processing triggered by an enabled interrupt
 */
static struct completion event_wait;

/**
 * @brief wait_event 
 * 
 * used for interrupt waiting
 */
static volatile uint32_t lld_ldec_int_cond = 0;

/**
 * @brief status of LDEC controller
 * 
 * store status of LDEC controller
 */
static volatile int ldec_state = 0;	/* interrupt result */  

/**
 * @brief address of allocated memory area
 * 
 * address of allocated memory area
 */
static void * ldec_initial_page_array_vadr = NULL;   /* start virtual address of initial area(4kB by kmalloc()) to store page addresses which is passed to get_user_pages() */  

/* to register MISC device */
static struct miscdevice miscdev;

/* pointer to device structure */
static struct device *dev_ldec;

#ifndef LDEC_TRANS_CPU	//DMA transfer mode
/**
 * @brief address of allocated memory area
 * 
 * address of allocated memory area
 */
static uint8_t * ldec_buffer_vadr = NULL;   /* virtual start address(pointer) of middle buffer(4kB) allocated by kmalloc() */  
static uint8_t * ldec_buffer_padr = NULL;   /* physical start address(pointer) of middle buffer(4kB)  */  
static uint8_t * ldec_initial_ll_vadr = NULL;   /* virtual start address(pointer) of initial allocated area(4kB) by kmalloc() for LinkedList */  

#ifndef LDEC_TRANS_CPU
	dma_addr_t dma_handle_interbuffer;	//DMA handle of middle buffer
#endif

/**
 * @brief wait_event information resource
 *
 * used for waiting of DMAC transfer completion
 */
static struct completion dmac_wait;

/**
 * @brief result of DMAC interrupt processing
 * 
 * store result of DMAC interrupt processing
 */
static uint32_t int_result_dmac = LDECHW_OK;   /* result of DMAC interrupt */  

/**
 * @brief DMAC interrupt status
 * 
 * value of DMAC interrupt status
 */
static uint64_t int_status_dmac = 0;   /* interrupt status */  

/**
 * @brief callback function for DMA transfer(register to DMAC driver)
 *
 */
static void int_func(const LLD_CH lld_ch, const LLD_FACT fact, void * const cookies_ptr)
{
	LLD_ER ret = LLD_OK;
	
	if(fact == LLD_DMAC_TRAN_END){
		/* process for tranfer success */
		int_result_dmac = LDECHW_OK;
	} else {
		/* process for transfer failure */
		int_result_dmac = LDECHW_NG;
		ret = lld_dmac_get_int_status(lld_ch,&int_status_dmac);
		if ( ret != LLD_OK ){
			ldec_print(LDEC_DEBUG_ERROR,"lld_dmac_get_int_status error! ret=%d \n",ret);
		}
		ldec_print(LDEC_DEBUG_DEBUG,"dma failed :: fact=%d , ret = %d\n",fact,ret );
	}
	complete( &dmac_wait );
}
#endif /*LDEC_TRANS_CPU*/

#ifdef DEBUG_PRINT
#ifndef LDEC_TRANS_CPU //DMA transfer mode
/*----------------------------------------------------------------------*/
/**
 * @brief function to print DMAC LinkedList for debug
 * 
 * print top of PRINT_ITEM_NUM items and the last one item in LinkedList
 * 
 *remark: maximum number of items in LinkedList is 4096
 * @return non
*/
/*----------------------------------------------------------------------*/

#define	PRINT_ITEM_NUM (9)	//total number of LLI for print
static void ldec_printk_linked_list(void *list_start_adr)
{
	int32_t i,item_num;
	LLD_DMAC_LINKLIST *list_va;
	
	for(i=0,list_va=(LLD_DMAC_LINKLIST *)list_start_adr;i<4096;i++){
		if(list_va->ul_ctl.f1_lli_last ==1){
			break;
		}
		list_va = (LLD_DMAC_LINKLIST *)phys_to_virt(list_va->s_lli.lli_adr<<6);
	}
	if(i==4096){
		ldec_print(LDEC_DEBUG_DEBUG,"CAUTION!! ldec_printk_linked_list(): list item number > 4096\n");
	}
	
	item_num = i+1;
	ldec_print(LDEC_DEBUG_DEBUG,"----------------------\n");
	ldec_print(LDEC_DEBUG_DEBUG,"    NUM of LL item = %d\n",item_num);
	ldec_print(LDEC_DEBUG_DEBUG,"----------------------\n");

	for(i=0,list_va=(LLD_DMAC_LINKLIST *)list_start_adr;i<item_num;i++){
		if((i<PRINT_ITEM_NUM) || (i>item_num-PRINT_ITEM_NUM)){
			if(i == item_num -1)
				ldec_print(LDEC_DEBUG_DEBUG,"----LAST item NO.=%d----\n",i);
			else
				ldec_print(LDEC_DEBUG_DEBUG,"----Item NO.=%d----\n",i);
			ldec_print(LDEC_DEBUG_DEBUG,"	Item VA=0x%llx\n",(uint64_t)list_va);
			ldec_print(LDEC_DEBUG_DEBUG,"	sadr(phys)=0x%llx\n",list_va->sadr);
			ldec_print(LDEC_DEBUG_DEBUG,"	dadr(phys)=0x%llx\n",list_va->dadr);
			switch(list_va->ul_ctl.f3_swidth){
				case	 LLD_DMAC_WIDTH32:
					ldec_print(LDEC_DEBUG_DEBUG,"	swidth = 32bit\n");
					break;
				case	 LLD_DMAC_WIDTH128:
					ldec_print(LDEC_DEBUG_DEBUG,"	swidth = 128bit\n");
					break;
				default:
					ldec_print(LDEC_DEBUG_DEBUG,"	swidth = ERROR\n");
			}
			switch(list_va->ul_ctl.f3_dwidth){
				case	 LLD_DMAC_WIDTH32:
					ldec_print(LDEC_DEBUG_DEBUG,"	dwidth = 32bit\n");
					break;
				case	 LLD_DMAC_WIDTH128:
					ldec_print(LDEC_DEBUG_DEBUG,"	dwidth = 128bit\n");
					break;
				default:
					ldec_print(LDEC_DEBUG_DEBUG,"	dwidth = ERROR\n");
			}
			ldec_print(LDEC_DEBUG_DEBUG,"	tsz=%d\n",list_va->tsz);
			ldec_print(LDEC_DEBUG_DEBUG,"	next_lli(phys>>6)=0x%llx\n",(uint64_t)(list_va->s_lli.lli_adr));
			ldec_print(LDEC_DEBUG_DEBUG,"	next_lli(VA)=0x%llx\n",(uint64_t)phys_to_virt(list_va->s_lli.lli_adr<<6));
			ldec_print(LDEC_DEBUG_DEBUG,"	ul_ctl.f1_lli_last=%d\n",list_va->ul_ctl.f1_lli_last);
		}
		list_va = (LLD_DMAC_LINKLIST *)phys_to_virt(list_va->s_lli.lli_adr<<6);
	}

}

#endif //DMA transfer mode
#endif //DEBUG_PRINT


/*----------------------------------------------------------------------*/
/**
 * @brief function for DMA channel config setting by calling lld_dmac_set_config()
 * 
 * by calling lld_dmac_set_config(), set a configuration to an assigned DMA channel
 * config values are defined by software workaround for the DeadLock issue
 * this function is compiled if LDEC_DMAC_CH_CONFIG macro is defined
 * @return 0:fail 1:success
*/
/*----------------------------------------------------------------------*/

#ifndef LDEC_TRANS_CPU	//DMA transfer mode
#ifdef LDEC_DMAC_CH_CONFIG	//Enable software work-around for Decomp DeadLock issue 
static int32_t ldec_set_dmac_ch_config(LLD_CH ch)
{

	LLD_DMAC_CH_CONF	lld_ch_conf;
	LLD_ER	ret;
	
	lld_ch_conf.prio = 3;	
	lld_ch_conf.aw_qos = 0;	// QoS setting has no effect according to Hardware spec.
	lld_ch_conf.ar_qos = 0;
	lld_ch_conf.src_outstand = 3;	//3 means buffer number = 4
	lld_ch_conf.dst_outstand = 0;	//0 means buffer number = 1
	ldec_print(LDEC_DEBUG_DEBUG, "call lld_dmac_set_config()\n");
	ret = lld_dmac_set_config(ch, &lld_ch_conf);
	if(ret != LLD_OK){
		ldec_print(LDEC_DEBUG_ERROR,"lld_dmac_set_config() error = 0x%x\n",ret);
		return 0;	//error
	}
	else{
		return 1;	//success
	}
}	
#endif //LDEC_DMAC_CH_CONFIG
#endif //LDEC_TRANS_CPU
/*----------------------------------------------------------------------*/
/**
 * @brief get ldec base address
 * 
 * return virtual base address of ldec registers
 *
 * @return base address(virtual address)
*/
/*----------------------------------------------------------------------*/

static void __iomem *lld_get_base_addr_ldec( void )
{
	return lld_ldec_base_addr;
}

/*----------------------------------------------------------------------*/
/**
 * @brief ldechw_set
 * 
 * LDEC setting at start of decompression process
 * 
 * @param[in]  records          
 * @param[in]  dst_phys         
 * 
 * @return none
*/
/*----------------------------------------------------------------------*/
static int ldechw_set( uint32_t records , uint64_t dst_phys )
{
	LZDECOMP_T *ldec;
	int state;
	int ret;
#ifdef LDEC_LOCK_TIMES
	struct timespec64 s_lock_time,e_lock_time;
#endif

	ldec = (LZDECOMP_T *)lld_get_base_addr_ldec();
	ldec_assert_NULL( ldec );

	writel_relaxed( LZDECOMP_INTCLR_ALLCLR, &ldec->LZDECOMP_INTCLR.DATA );		/* clear cause of interrupts */
	
	state = readl_relaxed( &ldec->LZDECOMP_INT.DATA );							/* get cause of interrupts */

	ldec_print(LDEC_DEBUG_INFO, "int_reg_val = 0x%08x\n",state);

	/* ldec setting before decompression */
	ldec_aclk_disable();

	writel_relaxed( LZDECOMP_SRAM_ACCESS_ENABLE, &ldec->LZDECOMP_DECMODE.DATA);	/* set SRAM Access Enable */
	ret = ldec_aclk_enable();
	if (ret  != 0 ) {
		ldec_print(LDEC_DEBUG_ERROR, " failed :: ret = %d\n" , ret);
		return ret;
	}
	writel_relaxed( LZDECOMP_SRAMLIM_INIT, &ldec->LZDECOMP_SRAMLIM.DATA);		/* set SRAM buffer control register(fixed vlue) */

	writel_relaxed( LZDECOMP_CMDQUELIM_INIT, &ldec->LZDECOMP_SMDQUELIM.DATA);	/* set CMD QUE control register(fixed vlue) */

#ifdef LDEC_TIMEOUT_FLAG	/* timeout function enabled */
#ifdef LDEC_TRANS_CPU		/*timeout is disabled for CPU transfer mode*/
	writel_relaxed( LZDECOMP_EXCEPT_TIMEOUT, &ldec->LZDECOMP_INTEN.DATA );	/* enable interrupts except timeout */
	writel_relaxed( LZDECOMP_TIMEOUT_MASK, &ldec->LZDECOMP_INTMSK.DATA );
#else	/* LDEC_TRANS_CPU *//* enable timeout for DMA transfer */
	writel_relaxed( LZDECOMP_INTEN_ENABLE_RESET, &ldec->LZDECOMP_INTEN.DATA );	/* enable all interrupts */
	writel_relaxed(LZDECOMP_INTMSK_ALLUNMSK, &ldec->LZDECOMP_INTMSK.DATA );
#endif	/* LDEC_TRANS_CPU */

#else	/* LDEC_TIMEOUT_FLAG *//* timeout function disabled */

	writel_relaxed( LZDECOMP_EXCEPT_TIMEOUT, &ldec->LZDECOMP_INTEN.DATA );
	writel_relaxed( LZDECOMP_TIMEOUT_MASK, &ldec->LZDECOMP_INTMSK.DATA );
	/* enable interrupts except timeout */

#endif	/* LDEC_TIMEOUT_FLAG */

	writel_relaxed( dst_phys&LDEC_LOWER_ADDR_MASK , &ldec->LZDECOMP_DESTADDR.DATAL );	/* set decompressed destination address (lower) */
	writel_relaxed( dst_phys>>32, &ldec->LZDECOMP_DESTADDR.DATAH);						/* set decompressed destination address (upper) */
	writel_relaxed( records, &ldec->LZDECOMP_RECORDS.DATA );							/* set records number */
	writel_relaxed( LDEC_TIMEOUT_TIME,&ldec->LZDECOMP_TIMEOUT.DATA);					/* set timeout period */
	writel_relaxed( LZDECOMP_RESET, &ldec->LZDECOMP_START.DATA );						/* set DECOMP reset */

	/* initializeation for wait */
	init_completion( &event_wait );
	lld_ldec_int_cond = 0;

#ifdef LDEC_LOCK_TIMES	//measure spinlock time
	ldec_set_ldec_state(-EBUSY,s_lock_time,e_lock_time);	/* modify interrupt result to BUSY(on the way of decompression) */
	LDEC_LOCK_TIMES_CHECK(e_lock_time,s_lock_time);
#else
	ldec_set_ldec_state(-EBUSY);							/* modify interrupt result to BUSY*/
#endif

	/* clear cause of interrupts just before reset cancellation */
	writel_relaxed( LZDECOMP_INTCLR_ALLCLR, &ldec->LZDECOMP_INTCLR.DATA );	/* clear all cause of interrupts */

	/* release reset */
	writel_relaxed( LZDECOMP_RESET_RELEASE, &ldec->LZDECOMP_START.DATA );
	
	/* software workaround : wait more than (APBCLKx2+ACLKx16) from LDEC LDEC reset cancellation(start decompression) to starting data transfer */
	readl_relaxed( &ldec->LZDECOMP_DECMODE.DATA );	/* dummy read mode register twice */
	readl_relaxed( &ldec->LZDECOMP_DECMODE.DATA );	
	return ret;
}

/*----------------------------------------------------------------------*/
/**
 * @brief ldechw_wait
 * 
 * LDEC wait process after completion of DMAC transfer
 * 
 * @return	error code
 * @retval	0         success
 * @retval	other than 0	error
*/
/*----------------------------------------------------------------------*/
static int ldechw_wait( void )
{
	int result;
	LZDECOMP_T *ldec;
	uint64_t timer_count;
	uint64_t timer_ret;
#ifdef LDEC_LOCK_TIMES
	struct timespec64 s_lock_time,e_lock_time;
#endif	/* LDEC_LOCK_TIMES */

	ldec = (LZDECOMP_T *)lld_get_base_addr_ldec();

	ldec_print(LDEC_DEBUG_INFO, "ldechw_wait wait start \n");

	/* wait event without interrupt */
	timer_count =  ((uint64_t)LDEC_TIMER_MAX * HZ)/LDEC_TIMER_US;
	ldec_print(LDEC_DEBUG_INFO,"timer_count(jiffies) = %lld , lld_ldec_int_cond = %d : request specification system timeout = 60s\n",timer_count,lld_ldec_int_cond);

	/*  event setting:wait completion if decompression has not completed */
	timer_ret = wait_for_completion_timeout( &event_wait, timer_count );
	
	if( timer_ret == 0 )	{
		ldec_print(LDEC_DEBUG_ERROR, "wait_for_completion_timeout = %lld , %lld jiffies timeout\n", timer_ret,timer_count);
		result = -EIO;	/*set EIO because of timeout of wait_for_completion_timeout() */

	} else {

		ldec_print(LDEC_DEBUG_INFO, "wait_for_completion_timeout timer_ret = %lld\n", timer_ret);
#ifdef LDEC_LOCK_TIMES
		ldec_get_ldec_state(result,s_lock_time,e_lock_time);
		LDEC_LOCK_TIMES_CHECK(e_lock_time,s_lock_time);
#else
		ldec_get_ldec_state(result);
#endif		
		/* modify return value to EIO because system reset is needed at bus error and APU return value has no choice of BUSY */
		if( result == -EBUSY ){
			result = -EIO;
		}

	}
	
	ldec_print(LDEC_DEBUG_INFO, "intraw_reg_value = 0x%x\n",readl_relaxed( &ldec->LZDECOMP_INTRAW.DATA ));
	ldec_print(LDEC_DEBUG_INFO, "int_reg_value = 0x%x\n",readl_relaxed( &ldec->LZDECOMP_INT.DATA ));
	ldec_print(LDEC_DEBUG_INFO, "inten_reg_value = 0x%x\n",readl_relaxed( &ldec->LZDECOMP_INTEN.DATA ));
	ldec_print(LDEC_DEBUG_INFO, "intmsk_reg_value = 0x%x\n",readl_relaxed( &ldec->LZDECOMP_INTMSK.DATA ));
	ldec_print(LDEC_DEBUG_INFO, "ldechw_wait() : result = %d\n",result);
	ldec_print(LDEC_DEBUG_INFO, "ldec_trans_set() cur_addr_l = %x, cur_addr_h = %x, return = %d\n", readl_relaxed( &ldec->LZDECOMP_CURRADDR.DATAL ),readl_relaxed( &ldec->LZDECOMP_CURRADDR.DATAH ) ,result);

	return result;
}

/*----------------------------------------------------------------------*/
/**
 * @brief ldechw_system_reset
 * 
 * ldec system reset
 * 
 * @return error code
 * @retval 0        success
 * @retval -EIO		no responce
 * @retval -EINVAL	invalid parameter
*/

/*----------------------------------------------------------------------*/
static int ldec_system_reset( void )
{
	int ret = 0;
	int ret2 = 0;

	ldec_print(LDEC_DEBUG_DEBUG, "call start \n" );
	ldec_check_busreq();
	ldec_print(LDEC_DEBUG_DEBUG, "end check busreq \n" );
	/* if bus request is active, system reset will be done */
	/* if ldec_check_busreq() occurs an error, ldec_check_busreq() will output error log */

	ret = ldec_clk_rst(LDECHW_DISABLE);		/* assert LDEC system reset */

	if( ret != 0 ){
		ldec_print(LDEC_DEBUG_ERROR, "ldec_clk_rst(DISABLE) err=%d\n",ret);
	}
	ret2 = ldec_clk_rst(LDECHW_ENABLE);	/* deassert LDEC system reset */
	if( ret2 != 0 ){
		ldec_print(LDEC_DEBUG_ERROR, "ldec_clk_rst(ENABLE) err=%d\n",ret2);
		if ( ret == 0 ){
			ret = ret2;
		}
	}

	return ret;
}

/*----------------------------------------------------------------------*/
/**
 * @brief ldec_error_processing
 * 
 * processing depends on cause of interrupts
 * 
 * @return 	void
 *
*/
/*----------------------------------------------------------------------*/
void ldec_error_processing( void )
{
	
	int32_t status = 0;
	int32_t result;

#ifdef LDEC_LOCK_TIMES
	struct timespec64 s_lock_time,e_lock_time;
	ldec_get_ldec_state(result,s_lock_time,e_lock_time);
	LDEC_LOCK_TIMES_CHECK(e_lock_time,s_lock_time);
#else
	ldec_get_ldec_state(result);
#endif
	status = ldec_check_busreq();	/* check bus request status */

	/* branch depends on interupt and check bus request status */
	if(( result == -EBUSY ) || ( status != 0 )){ 
		/* no LDEC interrupt and bus request status is active, then do  system reset */
		msleep(LDEC_BUSCLEAN_CHK_TIME);	/* waiit for more than 1ms after completion of transfer */
		ldec_system_reset();					/* do sysytem reset */
	}else if(( result != 0) && ( status == 0 )){
		/* error occurs and bus request status is inactive, then do software reset */
		msleep(LDEC_BUSCLEAN_CHK_TIME);	/* wait for more than 1ms after transfer */
		ldec_sw_reset( );						/* soft reset LDEC*/
	}

	return;

}

/*----------------------------------------------------------------------*/
/**
 * @brief ldechw_process
 * 
 * ldec interrupt process
 * 
 * @param[in]  intr             
 * 
 * @return result
 * @retval IRQ_HANDLED  success
*/
/*----------------------------------------------------------------------*/
static irqreturn_t ldechw_process(int irq, void *data)
{
	uint32_t int_state;			/* interrupt status */  
	LZDECOMP_T *ldec;

#ifdef LDEC_IRQ_TIMES	/* measure consumed time of interrupt handler */
	struct timespec64 s_time,e_time,ts;
	unsigned long irq_flags;
#endif /* LDEC_IRQ_TIMES */

#ifdef LDEC_IRQ_TIMES_DETAIL		
	struct timespec64 chk1_time,chk2_time,chk3_time,chk4_time,chk5_time;
#endif /* LDEC_IRQ_TIMES_DETAIL */
#ifdef LDEC_LOCK_TIMES
	struct timespec64 s_lock_time,e_lock_time;
#endif

#ifdef LDEC_IRQ_TIMES	
	local_irq_save(irq_flags);
	ktime_get_real_ts64(&s_time);
#endif /* LDEC_IRQ_TIMES */
	
#ifdef LDEC_IRQ_TIMES_DETAIL		
	ktime_get_real_ts64(&chk1_time);
#endif /* LDEC_IRQ_TIMES_DETAIL */


	ldec = (LZDECOMP_T *)lld_get_base_addr_ldec();

#ifdef LDEC_IRQ_TIMES_DETAIL
	ktime_get_real_ts64(&chk2_time);
#endif /* LDEC_IRQ_TIMES_DETAIL */
	
	int_state = readl_relaxed( &ldec->LZDECOMP_INT.DATA );		/* get cause of interrupt */

#ifdef LDEC_IRQ_TIMES_DETAIL
	ktime_get_real_ts64(&chk3_time);
#endif /* LDEC_IRQ_TIMES_DETAIL */

	ldec_print(LDEC_DEBUG_DEBUG, "int_state = 0x%x\n",int_state);

#ifdef LDEC_IRQ_TIMES_DETAIL
	ktime_get_real_ts64(&chk4_time);
#endif /* LDEC_IRQ_TIMES_DETAIL */

	/* cause of interrupt */
	switch( int_state )
	{
		case LZ77DEC_SUCCESS:	/* LDEC normal completion */
			ldec_print(LDEC_DEBUG_INFO, "INT: success\n");
#ifdef LDEC_LOCK_TIMES
			ldec_set_ldec_state(0,s_lock_time,e_lock_time);	/* modify interrupt result to SUCCESS */
#else
			ldec_set_ldec_state(0);							/* modify interrupt result to SUCCESS */
#endif
			break;
		default:				/* LDEC abnormal completion*/
			ldec_print(LDEC_DEBUG_ERROR, "INT: error. intraw = 0x%08x\n", readl_relaxed( &ldec->LZDECOMP_INTRAW.DATA ));

			if( int_state & LZ77DEC_BUSERR ){		/* bus error occured */
				/* if bus error occured, system reset is needed, set -EBUSY to do same processing as timeout */
#ifdef LDEC_LOCK_TIMES
				ldec_set_ldec_state(-EBUSY,s_lock_time,e_lock_time);	/* modify interrupt result to BUSY(on the way of decompression) */
#else
				ldec_set_ldec_state(-EBUSY);							/* modify interrupt result to BUSY */
#endif
			}else{		/* error occured except bus error */
#ifdef LDEC_LOCK_TIMES
				ldec_set_ldec_state(-EIO,s_lock_time,e_lock_time);	/* modify interrupt result to IO error  */
#else
				ldec_set_ldec_state(-EIO);							/* modify interrupt result to IO error */
#endif
			}
			break;
	}
	LDEC_LOCK_TIMES_CHECK(e_lock_time,s_lock_time);

	/* inerrupt control */
	writel_relaxed( LZDECOMP_INTCLR_ALLCLR, &ldec->LZDECOMP_INTCLR.DATA );		/* clear cause of interrupts */
	writel_relaxed( LZDECOMP_INTMSK_ALLMSK, &ldec->LZDECOMP_INTMSK.DATA );		/* mask interrupts */
	writel_relaxed( LZDECOMP_INTEN_ALLDISABLE,&ldec->LZDECOMP_INTEN.DATA );		/* disable interrupts */

	
#ifdef LDEC_IRQ_TIMES_DETAIL
	ktime_get_real_ts64(&chk5_time);
#endif

	/* event */
	lld_ldec_int_cond = 1;		/* LDEC decompression process completed */
	complete( &event_wait );	/* wake up event waiting process */

#ifdef LDEC_IRQ_TIMES	/* measure consumed time of interrupt handler */
	ktime_get_real_ts64(&e_time);
	ts = timespec64_sub(e_time,s_time);
	local_irq_restore(irq_flags);
	ldec_print(LDEC_DEBUG_TIME,"start time %llu.%09lu [s]\n" ,s_time.tv_sec,s_time.tv_nsec );
	ldec_print(LDEC_DEBUG_TIME, "end time %llu.%09lu [s]\n",e_time.tv_sec,e_time.tv_nsec );
	if((ts.tv_nsec > 100000) || (ts.tv_sec > 0)){
		ldec_print(LDEC_DEBUG_TIME,"Over 100usec :: interrupt handler execution time  %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );
	}else{
		ldec_print(LDEC_DEBUG_TIME,"Under 100usec :: interrupt handler execution time  %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );
	}
#endif /* LDEC_IRQ_TIMES */

#ifdef LDEC_IRQ_TIMES_DETAIL	
#if 0	/* laptime */
	/* elapsed time */
	ts = timespec64_sub(chk1_time,s_time);
	ldec_print(LDEC_DEBUG_TIME,"execution time start-chk1 %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );

	ts = timespec64_sub(chk2_time,s_time);
	ldec_print(LDEC_DEBUG_TIME,"execution time start-chk2 %llu.%09lu [s]\n", ts.tv_sec,ts.tv_nsec );

	ts = timespec64_sub(chk3_time,s_time);
	ldec_print(LDEC_DEBUG_TIME,"execution time start-chk3 %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );

	ts = timespec64_sub(chk4_time,s_time);
	ldec_print(LDEC_DEBUG_TIME,"execution time start-chk4 %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );

	ts = timespec64_sub(chk5_time,s_time);
	ldec_print(LDEC_DEBUG_TIME,"execution time start-chk5 %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );
#endif
	/* lap time */
	ts = timespec64_sub(chk1_time,s_time);
	ldec_print(LDEC_DEBUG_DEBUG,"execution time start-chk1 %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );

	ts = timespec64_sub(chk2_time,chk1_time);
	ldec_print(LDEC_DEBUG_DEBUG,"execution time chk1-chk2 %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );

	ts = timespec64_sub(chk3_time,chk2_time);
	ldec_print(LDEC_DEBUG_DEBUG,"execution time chk2-chk3 %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );

	ts = timespec64_sub(chk4_time,chk3_time);
	ldec_print(LDEC_DEBUG_DEBUG,"execution time chk3-chk4 %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );

	ts = timespec64_sub(chk5_time,chk4_time);
	ldec_print(LDEC_DEBUG_DEBUG,"execution time chk4-chk5 %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );

	ts = timespec64_sub(e_time,chk5_time);
	ldec_print(LDEC_DEBUG_DEBUG,"execution time chk5-e_time %llu.%09lu [s]\n",ts.tv_sec,ts.tv_nsec );

#endif	  /* LDEC_IRQ_TIMES_DETAIL */

	return IRQ_HANDLED;
}


/*----------------------------------------------------------------------*/
/**
 * @brief ldechw_resource_init
 * 
 * initialize ldec resoures
 * 
 * @return none
*/
/*----------------------------------------------------------------------*/
static void ldechw_resource_init( void )
{
	/* initialize mutexlock */
	ldec_mutex_init( &ldec_api_lock);			/* initialize MUTEX structure */
	ldec_mutex_init( &ldec_proc_lock);
	/* initialize spinlock */
	ldec_spin_lock_init( &ldec_state_lock);
#ifndef LDEC_TRANS_CPU
	int_result_dmac = LDECHW_OK;
#endif
	return ;
}

/*----------------------------------------------------------------------*/
/**
 * @brief ldechw_lock
 * 
 * lock or unlock mutex of ldec
 * 
 * @param[in]  type		LDEC_LOCK or LDEC_UNLOCK
 * 
 * @return  none
*/
/*----------------------------------------------------------------------*/
static void ldechw_lock( uint32_t type )
{
	if( type == LDEC_LOCK )	{
		ldec_mutex_lock( &ldec_api_lock );		/* set LZ77DEC exclusive setting */
	} else {
		ldec_mutex_unlock( &ldec_api_lock );	/* cancel LZ77DEC exclusive setting */
	}
	return ;
}


/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_get_user_pages
 *
 * get user_page address array by pin_user_pages()
 *
 * @param [in]  trans           pointer to ldec transfer structure(each member value is set in this function)
 * @param [in]  p               transfer start address (user space address)
 * @param [in]  len             transfer size
 *
 * @return	error code
 * @retval	0	success
 * @retval	-EIO -EFAULT -ENOMEM
 */
/*----------------------------------------------------------------------------*/
static int ldec_get_user_pages(ldec_trans_t *trans, void *p, uint32_t len)
{
	uint64_t addr = (uint64_t)p;
	uint64_t nr_pages;
	uint64_t offset;
	uint64_t alloc_size;

	trans->addr = addr;
	trans->len = len;

	offset = addr & ~PAGE_MASK;
	nr_pages = (offset + len + PAGE_SIZE - 1) >> PAGE_SHIFT; /* calculate total page number*/
	
	alloc_size = nr_pages * sizeof(struct pages *);
	
	if(alloc_size > INITIAL_PAGE_ARRAY_SIZE){	//if array size exceeds pre-allocated (kmalloc)4kB memory area in probe()
		trans->vmalloc_flg=1;
		trans->pages = vmalloc(alloc_size );	/* re-allocates array area by vmalloc() to store each physical address of user_page vmalloc */
		if(!trans->pages){
			ldec_print(LDEC_DEBUG_ERROR," Cannot vmalloc trans->pages, nr_pages = %lld \n",nr_pages);
			return -ENOMEM;
		}
		ldec_print(LDEC_DEBUG_DEBUG,"use vmalloc area for page information\n");
	}
	else{	//use pre-allocated kmalloc 4KB area in probe()
		trans->vmalloc_flg=0;
		trans->pages = ldec_initial_page_array_vadr;
		ldec_print(LDEC_DEBUG_DEBUG,"use kmalloc area for page information\n");
	}

	trans->nr_pages = 0;
	down_read(&current->mm->mmap_lock);
	trans->nr_pages = pin_user_pages(addr, nr_pages, 0, trans->pages, NULL);

	up_read(&current->mm->mmap_lock);

	if (trans->nr_pages != nr_pages) {
		ldec_print(LDEC_DEBUG_ERROR,"failed pin_user_pages(), addr = 0x%08x, len=%d, nr_pages = %lld, trans->nr_pages=%d\n",
		(uint32_t)addr, len, nr_pages, trans->nr_pages);
		return -EFAULT;
	}
	return 0;
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_put_user_pages
 *
 * free user_page information by unpin_user_pages()
 *
 * @param [in]  trans           pointer to ldec transfer structure
 *
 * @return none
 */
/*----------------------------------------------------------------------------*/
static void ldec_put_user_pages(ldec_trans_t *trans)
{
/*
	void unpin_user_pages(struct page **pages, unsigned long npages);
*/
	unpin_user_pages(trans->pages,trans->nr_pages);

	trans->nr_pages = 0;

	if ((trans->pages) && (trans->vmalloc_flg)) {	//if the area alloced by vmalloc, vfree it
			vfree( trans->pages );
		trans->pages = NULL;
	}
}

#ifndef LDEC_TRANS_CPU	//DMA transfer mode
/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_trans_set
 *
 * preparation for DMA transfer for ldec
 *
 * @param [in]  ldec_trans      pointer to ldec transfer structure
 * @param [in]  ch              DMA channel number
 * @param [in]  srcflush        cache flush source area (0) or not(not 0)
 *
 * @return 	error code
 * @retval 	0	success
 * @retval -EIO	IO error
 */
/*----------------------------------------------------------------------------*/
static int ldec_trans_set( ldec_trans_t *ldec_trans, uint32_t ch , uint32_t srcflush )
{
	int status = 0;

	LLD_ER ret = LLD_OK;
	LLD_DMAC_CH_INFO lld_info;
	uint32_t cookies;

	/*preparation for DMAC to transfer*/
	init_completion( &dmac_wait );
	ret = lld_dmac_open( ch );
	if(ret != LLD_OK)	{
	  /* DMAC Open error */
		ldec_print(LDEC_DEBUG_ERROR,"lld_dmac_open error = %x\n",ret);
		status = -EINVAL;
		return status;
	}

	lld_info.flowctl = LLD_DMAC_MM_DMAC;
	lld_info.srcid = 0;
	lld_info.dstid = 0;
	cookies = LDEC_COOKIE;
	
	/* Registering DMAC callback function */
	ret = lld_dmac_set_func( ch, &lld_info, int_func, &cookies, LLD_FUNC_NOTHREAD );
	if(ret != LLD_OK)	{
		ldec_print(LDEC_DEBUG_ERROR,"lld_dmac_set_func error = %x\n",ret);
		status = -EIO;
		lld_dmac_close( ch );
		return status;
	}
	//DMAC transfer (all at once transfer by LinkedList)
	status = ldec_ll_dma_trans( ldec_trans, ch , srcflush );
	//both of DMA success and fail, execute DMAC stop and close
	ret=lld_dmac_stop(ch);
	if(ret != LLD_OK){
		ldec_print(LDEC_DEBUG_ERROR, "lld_dmac_stop() error. ret=%d\n", ret);
	}
	ret=lld_dmac_close(ch);
	if(ret != LLD_OK){
		ldec_print(LDEC_DEBUG_ERROR, "lld_dmac_close() error. ret=%d\n", ret);
	}
	return status;	//regardless of DMA transfer success or fail, upper function manages post-process for LDEC
}

#else // CPU transfer mode
/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_trans_set
 *
 * prerapration for CPU transfer for ldec
 *
 * @param [in]  ldec_trans      pointer ldec transfer structure
 * @param [in]  ch              DMA channel number
 * @param [in]  srcflush        cache flush source area (0) or not(not 0)
 *
 * @return 	error code
 * @retval 	0	success
 * @retval -EIO	IO error
 */
/*----------------------------------------------------------------------------*/
static int ldec_trans_set( ldec_trans_t *ldec_trans, uint32_t ch , uint32_t srcflush )
{
	int status = 0;

	uint32_t	n = ldec_trans->nr_pages;
	uint32_t	i;
	uint32_t len = ldec_trans->len;
	uint32_t offset = ldec_trans->addr & ~PAGE_MASK;
	trans_t trans;
#ifdef LDEC_LOCK_TIMES
	struct timespec64 s_lock_time,e_lock_time;
#endif
	/*initialize transfer structure */
	trans.trans_size = 0;

	trans.size = PAGE_SIZE - offset;

	/* transfer size is enough */
	if (trans.size > len)
	{
		trans.size = len;
	}

	trans.dst = (uint64_t)iomem_ldec_slave;

	// the first page data transfer ( the page may have address offset
	trans.src = (uint64_t)page_to_virt(ldec_trans->pages[0]) + offset;
	ldec_print(LDEC_DEBUG_INFO, "ldec_cpu_trans() start\n");
	ldec_print(LDEC_DEBUG_INFO, "trans.src = 0x%llx, trans.dst = 0x%llx,  trans.size=%d, trans.trans_size=%d\n",trans.src,trans.dst,trans.size,trans.trans_size);
	ldec_cpu_trans( &trans );
	/* confirm LDEC completion then if LDEC stopped, finish transfer */
	if (lld_ldec_int_cond ==1){				/* confirm LDEC stopped */
#ifdef LDEC_LOCK_TIMES
		ldec_get_ldec_state(status,s_lock_time,e_lock_time);
		LDEC_LOCK_TIMES_CHECK(e_lock_time,s_lock_time);
#else
		ldec_get_ldec_state(status);
#endif
		return status;
	}

	len -= trans.size;

	trans.dst += trans.size;
	/* loop number of pages */
	for (i=1;i<n;i++)
	{
		/* get next page address */
		trans.src = (uint64_t)page_to_virt(ldec_trans->pages[i]) ;
		trans.size = len > PAGE_SIZE ? PAGE_SIZE : len;
		len -= trans.size;
		ldec_cpu_trans( &trans ); 

		/* if LDEC decompression completed, CPU transfer is finished */
		if (lld_ldec_int_cond ==1){
#ifdef LDEC_LOCK_TIMES
			ldec_get_ldec_state(status,s_lock_time,e_lock_time);
			LDEC_LOCK_TIMES_CHECK(e_lock_time,s_lock_time);
#else
			ldec_get_ldec_state(status);
#endif
			return status;
		}
	}
	return status;
}
#endif	//CPU transfer mode


#ifdef LDEC_TRANS_CPU //CPU transfer mode
/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_cpu_trans
 *
 * ldec setting to start CPU transfer
 *
 * @param [in]  trans	pointer to transfer structure
 *
 */
/*----------------------------------------------------------------------------*/
static void ldec_cpu_trans( trans_t *trans ){
	uint32_t *src_p;
	uint32_t *dst_p;
	uint32_t i;
	uint32_t j;
	uint32_t n;

	src_p = (uint32_t *) trans->src;
	dst_p = (uint32_t *) iomem_ldec_slave;
	n = (trans->size + LDEC_CPU_TRANS_SIZE -1) / LDEC_CPU_TRANS_SIZE;  /* write unit is 4 bytes so round up, boundary of source address is 16 bytes */

	ldec_print(LDEC_DEBUG_INFO, "ldec_cpu_trans() start , src_p=0x%llx, size=%d , trans_size=%d, loop n=%d \n",  (uint64_t)src_p, trans->size, trans->trans_size,n);

	for( i = 0; i  < n ; i++ ){
		j = trans->trans_size/LDEC_CPU_TRANS_SIZE;	/* calculate destination address */
		dst_p[j] = src_p[i];
		/*if 4KB has been transferred, destination address returns to start address*/
		if((trans->trans_size + LDEC_CPU_TRANS_SIZE) >= LDEC_MAX_SIZE)	{
			trans->trans_size = 0;	/* destination address is reset */
			
		} else {
			trans->trans_size += LDEC_CPU_TRANS_SIZE;	/* renew destination address */
		}
	}
	ldec_print(LDEC_DEBUG_INFO, "ldec_cpu_trans end trans\n");
}
#else //DMA transfer
/*----------------------------------------------------------------------------*/
/**
 * @brief convert_virt_to_phys
 *
 * conversion from virtual address to physical address (includes virtual address allocated by vmalloc)
 *
 * @param [in]  vmalloc_flg     if virtual address is allocated by vmalloc, this flag is 1 other 0
 * @param [in]  virt_adr        virtual address
 *
 * @return unit64_t 	physical address
 */
/*----------------------------------------------------------------------------*/
static uint64_t ldec_convert_virt_to_phys(uint32_t vmalloc_flg, uint64_t virt_adr)
{
	if(vmalloc_flg){
		return  (uint64_t)PFN_PHYS(vmalloc_to_pfn((void *)virt_adr)) | ((uint64_t)virt_adr & ~PAGE_MASK);
	}
	else{
		return (uint64_t)virt_to_phys((void*)virt_adr);
	}
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_ll_dma_trans
 *
 * ldec DMA transfer process using LinkedList
 *
 * @param [in]  *ldec_trans	pointer to transfer structure (array of page structure, total page number)
 * @param [in]	ch	DMA channel number
 * @param [in]	srcflush	LDEC driver do cache flush(0) source data area or not(1)
 *
 * @return	error code
 * @retval	0	success
 * @retval	-EIO	IOerror
 * @retval	-ENOMEM	not enough memory
 */
/*----------------------------------------------------------------------------*/
static int ldec_ll_dma_trans( ldec_trans_t *ldec_trans, uint32_t ch , uint32_t srcflush )
{
	uint32_t list_item_size;
	uint8_t * list_start_adr;
	uint8_t * ldec_vmalloc_ll_vadr = NULL;	  /* virtual address of LinkedList area in case that the area allocated by vmalloc */  
	uint32_t vmalloc_flg = 0;	//set 1 if LinkedList area is allocated by vmalloc
	uint32_t vmalloc_ll_size =0; //allocated size by vmalloc
	uint8_t * buffer_padr;

	uint32_t i,temp_uint32;
	uint32_t dmac_wa=0;
	uint32_t trans_remained;
	uint32_t list_item_num;
	uint64_t first_page_offset,temp_uint64,second_half_page_size;
	LLD_DMAC_LINKLIST	ll_item;
	LLD_DMAC_LINKLIST	ll_item_m2m;
	uint64_t next_lli_adr;
	uint64_t current_lli_adr;
	LLD_DMAC_IND_INFO lld_ind_info;
	LLD_ER ret = LLD_OK;
	uint64_t timer_ret,timer_count;
	int status = 0;
	dma_addr_t dma_handle;

	//middle buffer physical address
	buffer_padr = ldec_buffer_padr;

/*
	item size of LinkedList round upped to multiple of 64bytes 
	now actual sizeof(LLD_DMAC_LINKLIST)==64, this round-up is not needed
	list_item_size = ((sizeof(LLD_DMAC_LINKLIST)+63)/64) * 64;
	ldec_print(LDEC_DEBUG_DEBUG,"list_item_size =%d\n",list_item_size);
*/

	list_item_size = LLI_SIZE;

	//data position in the first page
	first_page_offset = ldec_trans->addr & ~PAGE_MASK;
	ldec_print(LDEC_DEBUG_DEBUG,"first_page_offset = 0x%llx\n",first_page_offset);

	//do  cache flush each page of source data 
	if(!srcflush){
		ldec_print(LDEC_DEBUG_DEBUG,"exec_srcflush\n");
		ldec_print(LDEC_DEBUG_DEBUG,"next dma_map/unmap_single()\n");
		//flush the first page
		temp_uint64 = PAGE_SIZE - first_page_offset;
		if(temp_uint64 > ldec_trans->len){
			temp_uint64 = ldec_trans->len;
		}
		dma_handle = dma_map_single(dev_ldec, page_to_virt(ldec_trans->pages[0]),PAGE_SIZE, DMA_TO_DEVICE);
		if (dma_mapping_error(dev_ldec, dma_handle)) {
			ldec_print(LDEC_DEBUG_ERROR,"error:dma_map_single() for first page!\n");
			return -EIO;
		}
		dma_unmap_single(dev_ldec, dma_handle, (size_t)BUFFER_SIZE, DMA_TO_DEVICE);

		if(ldec_trans->nr_pages > 1){ //more than 2 pages
			//cache flush from the second page to tha page previous the last page(in case of only 2page, this process will be skipped)
			for(i=1;i<ldec_trans->nr_pages-1;i++){
				dma_handle = dma_map_single(dev_ldec, page_to_virt(ldec_trans->pages[i]),PAGE_SIZE, DMA_TO_DEVICE);
				if (dma_mapping_error(dev_ldec, dma_handle)) {
					ldec_print(LDEC_DEBUG_ERROR,"error:dma_map_single() for page[i]!\n");
					return -EIO;
				}
				dma_unmap_single(dev_ldec, dma_handle, (size_t)BUFFER_SIZE, DMA_TO_DEVICE);
			}
			//cache flush the last page
			temp_uint64 = (first_page_offset + ldec_trans->len) & ~PAGE_MASK;
			if (temp_uint64==0){
				temp_uint64=PAGE_SIZE;
			}
			dma_handle = dma_map_single(dev_ldec, page_to_virt(ldec_trans->pages[ldec_trans->nr_pages-1]),temp_uint64, DMA_TO_DEVICE);
				if (dma_mapping_error(dev_ldec, dma_handle)) {
				ldec_print(LDEC_DEBUG_ERROR,"error:dma_map_single() for page[last]!\n");
				return -EIO;
			}
			dma_unmap_single(dev_ldec, dma_handle, temp_uint64, DMA_TO_DEVICE);

			ldec_print(LDEC_DEBUG_DEBUG,"nr_pages has more than one page\n");
		}else{
			ldec_print(LDEC_DEBUG_DEBUG,"nr_pages has one page\n");
		}
	}

	//calculate number of list_item(total number of items in LinkedList == DMA times)
	if(!(first_page_offset & 0x0f)){	//in case of 16N alignment, page number = DMA times
		list_item_num =	ldec_trans->nr_pages;
		ldec_print(LDEC_DEBUG_DEBUG,"first_page_offset is 16byte aligned = 0x%llx\n",first_page_offset);
	}
	else{	// data present NOT from top of the first page
			//1 dma time from the last page, total DMA times are 3*(total pages - 1)
			//2 dma times from the last page, total DMA times are 3*(total pages - 1)+2
		list_item_num =	3 * (ldec_trans->nr_pages - 1);
			//if 2 times DMA is needed from the last page
		if ((ldec_trans->len & ~PAGE_MASK) <= (PAGE_SIZE - first_page_offset)) {
			list_item_num +=2;
		}
		ldec_print(LDEC_DEBUG_DEBUG,"first_page_offset isn't 16byte aligned = 0x%llx\n",first_page_offset);

	}
	ldec_print(LDEC_DEBUG_DEBUG,"nr_page=%d, list_item_num=%d \n",ldec_trans->nr_pages,list_item_num);

	//4KB size(for 64 LinkedList items) initial LinkedList area was allocated in probe(). if over 4KB needed, re-allocated by vmalloc
	if(list_item_num > INITIAL_LL_SIZE / LLI_SIZE){
		vmalloc_ll_size = list_item_num * LLI_SIZE;
		ldec_vmalloc_ll_vadr = vmalloc(vmalloc_ll_size);
		if(ldec_vmalloc_ll_vadr == NULL){
			ldec_print(LDEC_DEBUG_ERROR,"ERROR vmaloc() for LL area\n");
			return -ENOMEM;
		}
		list_start_adr = ldec_vmalloc_ll_vadr;
		vmalloc_flg=1;	//set a flag that means LinkedList area is allocated by vmalloc
		ldec_print(LDEC_DEBUG_DEBUG,"use vmalloc area for LinkedList\n");
	}
	else{
		list_start_adr = ldec_initial_ll_vadr;	//use pre-allocated 4KB by kmalloc in probe()
		ldec_print(LDEC_DEBUG_DEBUG,"use kmalloc area for LinkedList\n");
	}

	//template of a list item:Page-->middle buffer(memory to memory transfer)
	memset(&ll_item_m2m,0,sizeof(ll_item_m2m));	//zero clear
//	ll_item_m2m.sadr = 0;	//depends on each item
//	ll_item_m2m.dadr = 0;	//depends on each item
//	ll_item_m2m.tsz  = 0;	//depends on each item
//	ll_item_m2m.s_lli.lms = 0; // 0 fixed
//	ll_item_m2m.s_lli.lli_adr = 0; //depends on each item. Next physical address which shifted right 6 bits
	ll_item_m2m.ul_ctl.f1_smch = LLD_DMAC_AXI_MASTER1;	//fixed value
	ll_item_m2m.ul_ctl.f1_dmch = LLD_DMAC_AXI_MASTER1;	//fixed value
	ll_item_m2m.ul_ctl.f1_si = LLD_DMAC_ADR_INC;	//page memory side, INC fixed
	ll_item_m2m.ul_ctl.f1_di = LLD_DMAC_ADR_INC;	//middle memory side, INC fixed
	ll_item_m2m.ul_ctl.f3_swidth = LLD_DMAC_WIDTH32;	//bus width to read from page, 32 in transfer from front side of page page, 128 from rear side
	ll_item_m2m.ul_ctl.f3_dwidth = LLD_DMAC_WIDTH128;	//bus width to write to middle  buffer is 16Bytes
	ll_item_m2m.ul_ctl.f4_sbsize = LLD_DMAC_BSIZE32;	//same as destination side
	ll_item_m2m.ul_ctl.f4_dbsize = LLD_DMAC_BSIZE32;	//by considering bus usage rate, set 32
	ll_item_m2m.ul_ctl.f4_arcache = 0x2;	//fixed value
	ll_item_m2m.ul_ctl.f4_awcache = 0x2;	//fixed value
// ARCACHE[3:0] AWCACHE[3:0] Memory type
// 0000 0000 Device Non-bufferable
// 0001 0001 Device Bufferable
// 0010 0010 Normal Non-cacheable Non-bufferable
// 0011 0011 Normal Non-cacheable Bufferable
// 1010 0110 Write-through No-allocate
// 1110 (0110) 0110 Write-through Read-allocate
// 1010 1110 (1010) Write-through Write-allocate
// 1110 1110 Write-through Read and Write-allocate
// 1011 0111 Write-back No-allocate
// 1111 (0111) 0111 Write-back Read-allocate
// 1011 1111 (1011) Write-back Write-allocate
// 1111 1111 Write-back Read and Write-allocate

//	ll_item_m2m.ul_ctl.f1_lastwren = 0;	//0 fixed
	ll_item_m2m.ul_ctl.f3_arprot = 0x2;	//fixed value
	ll_item_m2m.ul_ctl.f3_awprot = 0x2;	//fixed value
// AXI AxPROT
//  [0] 0:unprivileged access 1:privileged access
//  [1] 0:secure access 1:non-secure access
//  [2] 0:data access  1:instruction access

//	ll_item_m2m.ul_ctl.f1_arlenen = 0;	//0 fixed
//	ll_item_m2m.ul_ctl.f8_arlen = 0;	//0 fixed
//	ll_item_m2m.ul_ctl.f1_awlenen = 0;	//0 fixed
//	ll_item_m2m.ul_ctl.f8_awlen = 0;	//0 fixed
//	ll_item_m2m.ul_ctl.f1_srcstaten = 0;	//0 fixed
//	ll_item_m2m.ul_ctl.f1_dststaten = 0;	//0 fixed
//	ll_item_m2m.ul_ctl.f1_IOCBLKTFR = 0;	//0 fixed
//	ll_item_m2m.ul_ctl.f1_lli_last = 0;	//0 fixed except the last LLI(last LLI = 1)
	ll_item_m2m.ul_ctl.f1_lli_valid = 1;	//fixed value
//	ll_item_m2m.sstat = 0;		//for getting information
//	ll_item_m2m.dstat = 0;		//for getting information
//	ll_item_m2m.lstat = 0;		//for getting information

	
	//template of a list item:middle buffer-->LDEC
	memset(&ll_item,0,sizeof(ll_item));	//zero clear
	ll_item.sadr = (uint64_t)buffer_padr;	//fixed value in all items
	ll_item.dadr = lz77_slave;	//fixed value in all items
	ll_item.tsz  = PAGE_SIZE/16 - 1;	//transfer times except the last DMA transfer to DEC
//	ll_item.s_lli.lms = 0; //0 fixed
//	ll_item.s_lli.lli_adr = 0; //depends on each item. Next physical address which shifted right 6 bits
	ll_item.ul_ctl.f1_smch = LLD_DMAC_AXI_MASTER1;	//fixed value
	ll_item.ul_ctl.f1_dmch = LLD_DMAC_AXI_MASTER1;	//fixed value
	ll_item.ul_ctl.f1_si = LLD_DMAC_ADR_INC;	//middle buffer side: INC fixed
	ll_item.ul_ctl.f1_di = LLD_DMAC_ADR_FIX;	//LDEC side: FIX fixed becase of 16 bytes alligned source data
	ll_item.ul_ctl.f3_swidth = LLD_DMAC_WIDTH128;	//same as destination side
	ll_item.ul_ctl.f3_dwidth = LLD_DMAC_WIDTH128;	//128 fixed value because of 4kB aligned (16B aligned). the last of the last DMA transfer may include invalid data, but it will be ignored by LDEC)
	ll_item.ul_ctl.f4_sbsize = LLD_DMAC_BSIZE32;	//same as destination
	ll_item.ul_ctl.f4_dbsize = LLD_DMAC_BSIZE32;	//LDEC side maximum value 32
	ll_item.ul_ctl.f4_arcache = 0x02;	//fixed value
	ll_item.ul_ctl.f4_awcache = 0x00;	//fixed value
//	ll_item.ul_ctl.f1_lastwren = 0;	//0 fixed
	ll_item.ul_ctl.f3_arprot = 0x2;	//fixed value
	ll_item.ul_ctl.f3_awprot = 0x2;	//fixed value
//	ll_item.ul_ctl.f1_arlenen = 0;	//0 fixed
//	ll_item.ul_ctl.f8_arlen = 0;	//0 fixed
	ll_item.ul_ctl.f1_awlenen = 1;	//software work around for DeadLock issue :beat number limitation
	ll_item.ul_ctl.f8_awlen = 1;	//software work around for DeadLock issue :number of beat=2
//	ll_item.ul_ctl.f1_srcstaten = 0;	//0 fixed
//	ll_item.ul_ctl.f1_dststaten = 0;	//0 fixed
//	ll_item.ul_ctl.f1_IOCBLKTFR = 0;	//0 fixed
//	ll_item.ul_ctl.f1_lli_last = 0;	//0 fixed except the last LLI(last LLI = 1)
	ll_item.ul_ctl.f1_lli_valid = 1;	//fixed value
//	ll_item.sstat = 0;		//for getting information
//	ll_item.dstat = 0;		//for getting information
//	ll_item.lstat = 0;		//for getting information

	trans_remained = ldec_trans->len;
	current_lli_adr= (uint64_t)list_start_adr;
	next_lli_adr = 	current_lli_adr + list_item_size;

	//making LinkedList
	second_half_page_size = PAGE_SIZE - first_page_offset;	//size of rear side of page
	if (first_page_offset & 0x0f){	//in case of non 16 bytes aligned but 4byte aligned. the first page has data offset.
									//DMA transfer from rear side of page after the offset and front side of next page before the offset to the middle buffer
									//and then DMA transfer from the middle buffer to LDEC
		if(second_half_page_size < 16){
			dmac_wa=1;	//work around flag for DMAC issue which occurs in case of 
						//unaligned DMA transfer from rear side of page page and DMA transfer size is less than 16bytes
						//work around : width will be changed to 32bit avoid unaligned transfer
		}
		for(i=0;i<ldec_trans->nr_pages-1;i++){	//after combine rear side of i page and front side of i+1 page in the middle buffer, then DMA transfer from the middle buffer to LDEC
			//make LLI of rear side of page page(M2M)
			ll_item_m2m.sadr = (uint64_t)page_to_phys(ldec_trans->pages[i]) + first_page_offset; 	//set for each item
			ll_item_m2m.dadr = (uint64_t)buffer_padr;	//set for each item : start address of the middle buffer
//			ll_item_m2m.ul_ctl.f3_swidth = LLD_DMAC_WIDTH128;	//from rear side of page:128 (from front side of page:32)
			//transfer is unaligned from the rear side of page, if transfer time is once, work around is needed to avoid unaligned transfer
//			ll_item_m2m.tsz  = (second_half_page_size+15)/16 - 1;	
			if(dmac_wa){
				ll_item_m2m.ul_ctl.f3_swidth = LLD_DMAC_WIDTH32;
				ll_item_m2m.tsz  = (second_half_page_size+3)/4 - 1;	//round-up
			}
			else{
				ll_item_m2m.ul_ctl.f3_swidth = LLD_DMAC_WIDTH128;
				ll_item_m2m.tsz  = (second_half_page_size+15)/16 - 1;	//round-up
			}
			ll_item_m2m.s_lli.lli_adr = ldec_convert_virt_to_phys(vmalloc_flg, next_lli_adr)  >>6; //depends on each item. Next physical address which shifted right 6 bits
			memcpy((void *)current_lli_adr,&ll_item_m2m,sizeof(LLD_DMAC_LINKLIST));

			//prepare to  make next LLI(m2m)
			current_lli_adr= next_lli_adr;
			next_lli_adr += (uint64_t)list_item_size;

			//make LLI for the next page(M2M)
			ll_item_m2m.sadr = (uint64_t)page_to_phys(ldec_trans->pages[i+1]) ;		//data is present from top of page
			ll_item_m2m.dadr = (uint64_t)buffer_padr + second_half_page_size ;	
			ll_item_m2m.ul_ctl.f3_swidth = LLD_DMAC_WIDTH32;	//from front side of page:32 (from rear side of page:128)
			if(trans_remained <= 4096){	//in case of remained transfer size less than 4096, this DMA fransfer(M2M) is the last one
				ll_item_m2m.tsz  = (trans_remained - second_half_page_size + 3)/4 - 1;	//round-up because of the last M2M transfer
			}
			else{	//in case of remained transfer size more than 4096
				ll_item_m2m.tsz  = first_page_offset/4 - 1;	//m2m:round-up is not needed because of multiple of 4
			}
			ll_item_m2m.s_lli.lli_adr = ldec_convert_virt_to_phys(vmalloc_flg, next_lli_adr) >>6; //depends on each item. Next physical address which shifted right 6 bits
			memcpy((void *)current_lli_adr,&ll_item_m2m,sizeof(LLD_DMAC_LINKLIST));
			
			//prepare make next LLI(m2ldec)
			current_lli_adr= next_lli_adr;
			next_lli_adr += (uint64_t)list_item_size;
	
			//make LLI for DMA from middle buffer to LDEC
			if(trans_remained <= 4096){	//in case of remained transfer size less than or equal 4096bytes
				ll_item.tsz = (trans_remained+15)/16 - 1;	//m2ldec:16byte in one transfer, round-up to multiple of 16 because of the last DMA
				ll_item.ul_ctl.f1_lli_last = 1;		//in case of only one page, both of m2m and m2ldec are only 1 dma transfer, LLI of m2ldec set the last LLI
				memcpy((void *)current_lli_adr,&ll_item,sizeof(LLD_DMAC_LINKLIST));
				ldec_print(LDEC_DEBUG_DEBUG,"one time DMA transfers from the last page\n");

				goto	_LL_GENERATED;
			}
			else{
				ll_item.tsz  = 4096/16 - 1;	//m2ldec
				ll_item.s_lli.lli_adr = ldec_convert_virt_to_phys(vmalloc_flg, next_lli_adr) >>6; //depends on each item. Next physical address which shifted right 6 bits
				memcpy((void *)current_lli_adr,&ll_item,sizeof(LLD_DMAC_LINKLIST));
			}
				
			//prepare to make next LLI(m2m)
			current_lli_adr = next_lli_adr;
			next_lli_adr += (uint64_t)list_item_size;
			trans_remained -=4096;
		}	//for loop above here

		//pass through here in case of DMA twice from the last page
		ldec_print(LDEC_DEBUG_DEBUG,"two times DMA transfers from the last page\n");
		//make LLI for rear side of the last page(M2M)
		ll_item_m2m.sadr = (uint64_t)page_to_phys(ldec_trans->pages[ldec_trans->nr_pages -1]) + first_page_offset; 
		ll_item_m2m.dadr = (uint64_t)buffer_padr;
		ll_item_m2m.ul_ctl.f3_swidth = LLD_DMAC_WIDTH32;	//in this case, source address is 4 byte aligned , and last data is also non 16byte aligned, so that width=32
		ll_item_m2m.tsz  = (trans_remained + 3)/4 - 1 ;	//round-up
		ll_item_m2m.s_lli.lli_adr = ldec_convert_virt_to_phys(vmalloc_flg, next_lli_adr) >>6; //depends on each item. Next physical address which shifted right 6 bits
		memcpy((void *)current_lli_adr,&ll_item_m2m,sizeof(LLD_DMAC_LINKLIST));

		//prepare to make next LLI(m2ldec)
		current_lli_adr= next_lli_adr;
		next_lli_adr += (uint64_t)list_item_size;

		//make LLI from middle buffer to LDEC
		ll_item.tsz  = (trans_remained+15)/16 - 1;	//m2ldec:one transaction is 16 bytes. Because of the last DMA, so round-up to multiple of 16
		ll_item.ul_ctl.f1_lli_last = 1;		//in case of 1page only, both of m2m and m2ldec transfer is once. LLI of m2ldec set last flag
		memcpy((void *)current_lli_adr,&ll_item,sizeof(LLD_DMAC_LINKLIST));
		goto	_LL_GENERATED;
		
	}	//in case of non 16 byte offset, above here
	else{	//in case of 16 byte align, transfer directly from each page to LDEC with 128bit width with address fixed mode for LDEC side (DMA times = number of total page)
		
		current_lli_adr=(uint64_t)list_start_adr;
		next_lli_adr=(uint64_t)list_start_adr+list_item_size;
		//DMA from the first page
		ll_item.sadr  = (uint64_t)page_to_phys(ldec_trans->pages[0]) + first_page_offset;
		if(ldec_trans->nr_pages ==1){	//in case of only one page
			ll_item.ul_ctl.f1_lli_last = 1;	
			ll_item.tsz  = (ldec_trans->len +15)/16  -1;	//round-up becuse of the last DMA
			memcpy((void *)current_lli_adr,&ll_item,sizeof(ll_item));
			goto _LL_GENERATED;
		}	
		else{	//DMA drom the first page in case of more than 1 page
			ll_item.tsz  = second_half_page_size/16  - 1;	//no round-up bacase of 16 byte align
			ll_item.s_lli.lli_adr = ldec_convert_virt_to_phys(vmalloc_flg, next_lli_adr) >> 6; //depends on each item. Next physical address which shifted right 6 bits
			memcpy((void *)current_lli_adr,&ll_item,sizeof(ll_item));
			//prepare next LLI
			trans_remained = ldec_trans->len - second_half_page_size; 	//remained transfer data size
			current_lli_adr = next_lli_adr;
			next_lli_adr += (uint64_t)list_item_size;
			ll_item.tsz  = PAGE_SIZE/16  - 1;
		}
		//DMA except the last page
		for(i=1;i<ldec_trans->nr_pages-1;i++){	//in case of only 2 pages, this is skipped
			ll_item.sadr  = (uint64_t)page_to_phys(ldec_trans->pages[i]); 
			ll_item.s_lli.lli_adr = ldec_convert_virt_to_phys(vmalloc_flg, next_lli_adr) >> 6; //depends on each item. Next physical address which shifted right 6 bits
			memcpy((void *)current_lli_adr,&ll_item,sizeof(ll_item));
			//prepare nest LLI
			trans_remained -= PAGE_SIZE; 	//remained transfer data size
			current_lli_adr = next_lli_adr;
			next_lli_adr += (uint64_t)list_item_size;
		}
		//DMA from the last page
		ll_item.sadr  = (uint64_t)page_to_phys(ldec_trans->pages[ldec_trans->nr_pages-1]); 
		ll_item.tsz  = (trans_remained+15)/16  -1;	//round-up becuse of the last DMA
		ll_item.ul_ctl.f1_lli_last = 1;	//this is the last LLI
		memcpy((void *)current_lli_adr,&ll_item,sizeof(ll_item));
	}

_LL_GENERATED:
#ifdef DEBUG_PRINT 
	//printk a part of LinkedList
	ldec_printk_linked_list(list_start_adr);
#endif
	//before DMA start, cache flush LinkedList area
	if(vmalloc_flg){	//LL area allocated by vmalloc(allocated pages are not consecutive memory)
		temp_uint32 = (vmalloc_ll_size+PAGE_SIZE-1)/PAGE_SIZE;	//total page number allocated by vmalloc
		for(i=0;i<temp_uint32;i++){	//cache flush each page
			dma_handle = dma_map_single(dev_ldec, page_address(pfn_to_page(vmalloc_to_pfn(list_start_adr+(PAGE_SIZE*i)))), PAGE_SIZE, DMA_TO_DEVICE);
			if (dma_mapping_error(dev_ldec, dma_handle)) {
				ldec_print(LDEC_DEBUG_ERROR,"error:dma_map_single() for LinkedList allocated by vmalloc()page=%d\n",i);
				status = -EIO;
				goto _EOUT_LL;
			}
			dma_unmap_single(dev_ldec, dma_handle, (size_t)PAGE_SIZE, DMA_TO_DEVICE);		
		}
	}
	else{	//LL area allocated by kmalloc
		dma_handle = dma_map_single(dev_ldec, list_start_adr, list_item_num * LLI_SIZE, DMA_TO_DEVICE);
		if (dma_mapping_error(dev_ldec, dma_handle)) {
			ldec_print(LDEC_DEBUG_ERROR,"error:dma_map_single() for LinkedList allocated by kmalloc()\n");
			status = -EIO;
			goto _EOUT_LL;
		}
		dma_unmap_single(dev_ldec, dma_handle, (size_t)BUFFER_SIZE, DMA_TO_DEVICE);
	}

	ldec_print(LDEC_DEBUG_DEBUG,"LinkedList area cache flushed\n");

#ifdef LDEC_DMAC_CH_CONFIG	//software workaround for DeadLock issue. a part of lld_dmac_set_config()
	if(ldec_set_dmac_ch_config(ch)==0){
		ldec_print(LDEC_DEBUG_DEBUG,"lld_dmac_set_config() error\n");
		status = -EIO;
		goto _EOUT_LL;
	}
#endif	//software workaround above here

	//from here start DMA using LinkedList

	memset(&lld_ind_info,0,sizeof(lld_ind_info));
	lld_ind_info.lms = LLD_DMAC_AXI_MASTER1;
	lld_ind_info.lli_adr = ldec_convert_virt_to_phys(vmalloc_flg, (uint64_t)list_start_adr) >> 6;
	ldec_print(LDEC_DEBUG_DEBUG,"next:Linked List DMA start:LinkedList start phys adr=0x%llx, virt adr=0x%llx\n",ldec_convert_virt_to_phys(vmalloc_flg, (uint64_t)list_start_adr),(uint64_t)list_start_adr);
	ret = lld_dmac_sc_start(ch , lld_ind_info);	//start DMA with LL
	if( ret != LLD_OK ){
		ldec_print(LDEC_DEBUG_DEBUG,"lld_dmac_sc_start() error = %x\n",ret);
		status = -EIO;
		goto _EOUT_LL;
	}
	ldec_print(LDEC_DEBUG_DEBUG,"lld_dmac_sc_start() called...waiting event of DMAC inerrupt\n");
	timer_count =  ((uint64_t)LDEC_TIMER_MAX * HZ)/LDEC_TIMER_US;
	timer_ret = wait_for_completion_timeout( &dmac_wait , timer_count);	//waiting DMAC interrupt
	if(( timer_ret == 0 ) || ( int_result_dmac != LDECHW_OK )){
		ldec_print(LDEC_DEBUG_ERROR,"wait_for_completion_timeout() error = %lld\n",timer_ret);
		status = -EIO;
#ifdef DEBUG_PRINT 
		if( timer_ret == 0){
			ldec_print(LDEC_DEBUG_DEBUG,"LL_DMAC timeout = %d\n",int_result_dmac);
		}
		else{
			ldec_print(LDEC_DEBUG_DEBUG,"__DMAC dmac error = %d\n",int_result_dmac);
		}
#endif
	}
	ldec_print(LDEC_DEBUG_DEBUG,"int_status_dmac=%lld\n",int_status_dmac);

_EOUT_LL:
	if(ldec_vmalloc_ll_vadr != NULL){
		vfree(ldec_vmalloc_ll_vadr);
	}
	return status;	//upper function do stop()/close of DMAC
}

#endif

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_ioctl
 *
 * ioctl process
 *
 * @param [in]  file            pointer to control structure
 * @param [in]  ioctl           pointer ioctl information 
 *
 * @return	error code
 * @retval	0	success
 * @retval	-EINVAL	invalid parameter
 * @retval	-EIO	IO error
 * @retval	-EFAULT	address conversion error
 * called at device node ioctl, do command process
 *
 * check parameters, if invalid, return -1 and errno is set EINVAL
 * 
 * convert from virt and srclen to physcal address.
 * after exclusive processing for LDEC resource, start decompression. after decompression, release the exclusion.
 * decompressed data is stored from dst_phys address.
 * dst_phys must be 32Byte aligned.
 * if not aligned address, return -1 and errno is set EINVAL.
 * records must not exceed 8191(0x1FFF).
 * if records is set more than 8191,return -1 and errno is set EINVAL.
 * 
 * dstlen must be equal or less than (4KB x records)
 * if exceed 4KB x records, return -1and errno is set EINVAL
 * 
 * in DMA transfer mode, transfer src data to LDEC by using DMAC channel indicated ch
 * in CPU transfer mode, CPU read src data and the write data to LDEC
 * 
 * if timeout is enabled, LDEC timeout register is set 0x1FF and timeout interrupt is enabled
 * Regardless using LDEC timeout function or not, 60sec software timeout is always enabled
 * When  timeout or error occured, return -1 and errno is set EIO.
 * 
 * if xsrcflush is 0, before DMA transfer of compressed data to LDEC,
 * cache flush virt area. the area size is srclen.
 * 
 * if dstflush is 0, both of before and after decompression, cache invalidate dst_phys area. the area size is dstlen.
 * 
 * if error occurs at address conversion of virt or dst_phys, return -1 and errno is set EFAULT.
 * 
 * if fail at memory allocation, return -1 and errno is set ENOMEM.
 * 
 */
/*----------------------------------------------------------------------------*/

//#define IS_DST_LINUX_MEMORY	/* parameter check if dst area is in Linux memory area or not
static long ldec_ioctl(struct file *file, unsigned int cmd, unsigned long arg)
{
	int status = 0;
	ldec_trans_t trans;
	uint8_t *lz77_virt;
	ldec_decompress_t param={0};
	ldec_decompress_t *param_ptr;
	dma_addr_t dma_handle;
#ifdef IS_DST_LINUX_MEMORY
	struct device_node *np;
	uint32_t reg_val[4];
	uint64_t mem_st_adr;
	uint64_t mem_size;
#endif
#ifdef LDEC_LOCK_TIMES
	struct timespec64 s_lock_time,e_lock_time;
#endif
#ifdef LDEC_IOCTL_TIMES
	struct timespec64 s_time,e_time,ts;
	ktime_get_real_ts64(&s_time);
	
#endif /* LDEC_IOCTL_TIMES */

	/* parameter check */
	if( (void __user *)arg == NULL ) {		/* NULL check */
		ldec_print(LDEC_DEBUG_ERROR,"ret=%x  :: ictl:arg is NULL \n",-EINVAL);
		return -EINVAL;	/* invalid parameter */
	}

	/* ioctl CMD check */
	if( cmd != LDEC_DECOMPRESS )	{
		ldec_print(LDEC_DEBUG_ERROR,"ret=%x ::  illegal cmd(%d) \n",-EINVAL,cmd);
		return -EINVAL;
	}

	param_ptr = (ldec_decompress_t *)arg;
	param.virt = param_ptr->virt;
	param.dst_phys = param_ptr->dst_phys;
	param.srclen = param_ptr->srclen;
	param.dstlen = param_ptr->dstlen;
	param.records = param_ptr->records;
	param.ch = param_ptr->ch;
	param.xsrcflush = param_ptr->xsrcflush;
	param.xdstflush = param_ptr->xdstflush;

	ldec_print(LDEC_DEBUG_DEBUG, "ioctl : cmd       = %d\n", cmd);
	ldec_print(LDEC_DEBUG_DEBUG, "ioctl : virt      = 0x%llx\n", (uint64_t)param.virt);
	ldec_print(LDEC_DEBUG_DEBUG, "ioctl : dst_phys  = 0x%llx\n", param.dst_phys);
	ldec_print(LDEC_DEBUG_DEBUG, "ioctl : srclen    = %d/0x%x\n", param.srclen, param.srclen);
	ldec_print(LDEC_DEBUG_DEBUG, "ioctl : dstlen    = %d/0x%x\n", param.dstlen, param.dstlen);
	ldec_print(LDEC_DEBUG_DEBUG, "ioctl : records   = %d/0x%x\n", param.records, param.records);
	ldec_print(LDEC_DEBUG_DEBUG, "ioctl : ch        = %d\n", param.ch);
	ldec_print(LDEC_DEBUG_DEBUG, "ioctl : xsrcflush = %d\n", param.xsrcflush);
	ldec_print(LDEC_DEBUG_DEBUG, "ioctl : xdstflush = %d\n", param.xdstflush);

	/* parameter check:dst_phys alignment */
	if((param.dst_phys & LDEC_CHECK_ALIGN)  != 0)	{
		ldec_print(LDEC_DEBUG_ERROR,"dst_phys: ret=%x  :: dst_phys = 0x%llx\n",-EINVAL,param.dst_phys);
		return -EINVAL;
	}
	/* parameter check:records */
	if(( param.records > LDEC_MAX_RECORDS ) || ( param.records <= 0 ))	{
		ldec_print(LDEC_DEBUG_ERROR,"records is too big or set 0 :ret=%x  :: records = %d\n",-EINVAL,param.records);
		return -EINVAL;
	}
	/* parameter check:dstlen */
	if(( param.dstlen > param.records * LDEC_MAX_RECORD_SIZE ) || ( param.dstlen <= 0 ))	{
		ldec_print(LDEC_DEBUG_ERROR,"dstlen is too big or set 0 : ret=%x :: dstlen    = %d \n",-EINVAL,param.dstlen);
		return -EINVAL;
	}
#ifndef LDEC_TRANS_CPU	//DMA transfer mode
	/* parameter check:ch */
	if( param.ch > LLD_CH_MAX )	{
		ldec_print(LDEC_DEBUG_ERROR,"DMA ch is too large: ret=%x :: ch = %d\n",-EINVAL,param.ch);
		return -EINVAL;
	}
#endif
	/*  parameter check:virt alignment */
	if( (uint64_t)param.virt & 0x3)	{/*must be 4byte aligned*/
		ldec_print(LDEC_DEBUG_ERROR,"virt address must be aligned 4byte: ret=%x  :: virt = 0x%llx\n",-EINVAL,(uint64_t)param.virt);
		return -EINVAL;
	}
	/* parameter check:srclen */
	if( !(param.srclen > 0)){
		ldec_print(LDEC_DEBUG_ERROR,"srclen must be larger than 0: ret=%x  :: srclen    = %d \n",-EINVAL,param.srclen);
		return -EINVAL;
	}
	
	/* in case of xdstflush==0(cache invalidate), dst area must be included in Linux memory area  */
	/* to avoid freeze at cache invalidate(dma_map_single()) */
	/* "memory@200000000"  must meet DeviceTree description */
#ifdef IS_DST_LINUX_MEMORY
	if(param.xdstflush == 0){
		np = of_find_node_by_path("/memory@200000000");	
		of_property_read_u32_array(np, "reg", reg_val,4);
		mem_st_adr = (uint64_t)reg_val[0]<<32 | reg_val[1];
		mem_size = (uint64_t)reg_val[2]<<32 | reg_val[3];
		ldec_print(LDEC_DEBUG_DEBUG,"Linux memory start address = 0x%016llx, size = 0x%016llx\n",mem_st_adr, mem_size);
		if((param.dst_phys < mem_st_adr) || ((param.dst_phys + param.dstlen) > (mem_st_adr + mem_size))){
			ldec_print(LDEC_DEBUG_ERROR,"dst phys area must be in Linux memory area to invalidate cache.\n");
			return -EINVAL;
		}
	}
#endif
	
	/* start LDEC resource lock */
	ldechw_lock( LDEC_LOCK );
#ifdef LDEC_LOCK_TIMES
	ldec_set_ldec_state(0,s_lock_time,e_lock_time);	/* Initialize the state to SUCCESS */
	LDEC_LOCK_TIMES_CHECK(e_lock_time,s_lock_time);
#else
	ldec_set_ldec_state(0);							/* Initialize the state to SUCCESS  */
#endif

	//before decompression, cache invalidate
	if( param.xdstflush == 0 ){
		ldec_print(LDEC_DEBUG_DEBUG,"exec_dstflush before decompress\n");
		//convert to virtual address from dst_phys
		lz77_virt = (uint8_t *)phys_to_virt( param.dst_phys );
		dma_handle = dma_map_single(dev_ldec, lz77_virt, (size_t)param.dstlen, DMA_FROM_DEVICE);
		if (dma_mapping_error(dev_ldec, dma_handle)) {
			ldec_print(LDEC_DEBUG_ERROR,"error:dma_map_single() for lz77_virt(before DMA)\n");
			ldechw_lock( LDEC_UNLOCK );
			return -EIO;
		}
	}else{
		ldec_print(LDEC_DEBUG_INFO, "do not exec CACHE_INVALIDATE\n");
	}

	/* start exclusion ldec_read_proc and proc_info output */
	ldec_mutex_lock( &ldec_proc_lock );
	/* get sysfs info */
	memcpy( (void*)&proc_info, (void*)&param, sizeof(param));
	ldec_mutex_unlock( &ldec_proc_lock );
	/* end exclusion ldec_read_proc and proc_info output */

	/*get page info*/
	status = ldec_get_user_pages(&trans, param.virt, param.srclen);
	if( status != 0)
	{
		ldec_print(LDEC_DEBUG_ERROR,"ERROR ldec_get_user_pages()  ret=%x\n",status);
		goto _EOUT;
	}


	ldec_print(LDEC_DEBUG_INFO, " next call of ldechw_set()\n");

	/* LDEC start */
	status = ldechw_set( param.records , param.dst_phys );
	if( status != 0)
	{
		ldec_print(LDEC_DEBUG_ERROR,"ERROR ldechw_set()  ret=%x\n",status);
		goto _EOUT;
	}

	ldec_print(LDEC_DEBUG_INFO, "next call of ldec_trans_set()\n");

	/* data transfer */
	status = ldec_trans_set( &trans, param.ch, param.xsrcflush );
	if( status != 0)	{
		ldec_print(LDEC_DEBUG_INFO, "data transfer failed \n");
		goto _EOUT;
	}

	ldec_print(LDEC_DEBUG_INFO, "next call of ldechw_wait()\n");

	/* wait for LDEC completion */
	status = ldechw_wait();
	if( status != 0 )	{
		ldec_print(LDEC_DEBUG_ERROR, "next call of error \n");
		goto _EOUT;
	}

	/* cache invalidate dst area after decompression */
	if( param.xdstflush == 0 )	{
		ldec_print(LDEC_DEBUG_DEBUG,"exec_dstflush after decompress\n");
		dma_sync_single_for_device(dev_ldec, dma_handle, (size_t)param.dstlen,DMA_FROM_DEVICE);
	}else{
		ldec_print(LDEC_DEBUG_INFO, "do not exec CACHE_INVALIDATE\n");
	}

_EOUT:
	if( param.xdstflush == 0 )	{
		dma_unmap_single(dev_ldec, dma_handle, (size_t)param.dstlen, DMA_FROM_DEVICE);
	}
	ldec_put_user_pages(&trans);

	/* avoid missing LDEC stop */
	if ( status != 0){
		ldec_error_processing( );
	}
	
#ifdef SLEEP70SEC4TEST
	ldec_print(LDEC_DEBUG_DEBUG, " [LDEC_TESTCODE] sleep 70sec \n" );
	msleep(70000);  /* for test1.3.15 sleep 70sec before UNLOCK*/
#endif
	
	/* LDEClock end */
	ldechw_lock( LDEC_UNLOCK );

#ifdef LDEC_IOCTL_TIMES
	/* measure decompression time */
	ktime_get_real_ts64(&e_time);
	ts = timespec64_sub(e_time,s_time);
//	ldec_print(LDEC_DEBUG_TIME, "ret=%d  end time %llu.%09lu [s]\n",status,e_time.tv_sec,e_time.tv_nsec );
	ldec_print(LDEC_DEBUG_TIME,"ldec_ioctl() ret=%d  execution time:%llu.%09lu [s]\n",status,ts.tv_sec,ts.tv_nsec );
#endif

	ldec_print(LDEC_DEBUG_DEBUG, "ldec_ioctl() return val = %d \n", status );

	return status;
}

/**
 * @brief file operation structure
 * 
 * 
 */
 
static const struct file_operations fops = {
	.open = NULL,
	.owner = THIS_MODULE,
	.release = NULL,
	.unlocked_ioctl = ldec_ioctl,
};


/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_show
 *
 * sysfs reading process
 *
 * @param [in]  dev            
 *
 * @return	read data size
 * @retval	len	 total read size
 */
/*----------------------------------------------------------------------------*/

ssize_t ldec_show(struct device *dev,struct device_attribute *attr, char *buf)
{

	LZDECOMP_T *ldec;
	size_t len = 0;
	int status = 0;
#ifdef LDEC_LOCK_TIMES
	struct timespec64 s_lock_time,e_lock_time;
#endif
	
	ldec = (LZDECOMP_T *)lld_get_base_addr_ldec();
	ldec_assert_NULL( ldec );	

	len +=sysfs_emit_at(buf,len,
#ifdef LDEC_USE_FPGA
			"target : fpga \n");
#else
			"target : es \n");
#endif

	len +=sysfs_emit_at(buf,len,
#ifdef LDEC_TRANS_CPU
			"trans_mode : cpu \n");
#else
			"trans_mode : dma \n");
#endif			

	len +=sysfs_emit_at(buf,len,
#ifdef LDEC_TIMEOUT_FLAG
#ifndef LDEC_TRANS_CPU
			"timeout : enable \n");
#else	/* LDEC_TRANS_CPU */
			"timeout : disable \n");
#endif	/* LDEC_TRANS_CPU */
#else	/* LDEC_TIMEOUT_FLAG */
			"timeout : disable \n");
#endif	/* LDEC_TIMEOUT_FLAG */

	len +=sysfs_emit_at(buf,len,
#ifdef DEBUG_PRINT
		"log output :: level=%x \n",LDEC_PRINT_LEVEL);
#else
		"log output :: disable\n");
#endif

#ifdef SLEEP70SEC4TEST
	len += sysfs_emit_at(buf,len,
		"for test binary : 70sec sleep \n");
#endif

#ifdef LDEC_IOCTL_TIMES
	len += sysfs_emit_at(buf,len,
		"for test binary : ioctl time measurement \n");
#endif
#ifdef LDEC_IRQ_TIMES
	len += sysfs_emit_at(buf,len,
		"for test binary : irq time measurement \n");
#endif
#ifdef LDEC_IRQ_TIMES_DETAIL
	len += sysfs_emit_at(buf,len,
		"for test binary : irq detail time measurement \n");
#endif
#ifdef LDEC_LOCK_TIMES
	len += sysfs_emit_at(buf,len,
		"for test binary : lock time measurement \n");
#endif

#ifdef LDEC_LOCK_TIMES
	ldec_get_ldec_state(status,s_lock_time,e_lock_time);
	LDEC_LOCK_TIMES_CHECK(e_lock_time,s_lock_time);
#else
	ldec_get_ldec_state(status);
#endif
	len += sysfs_emit_at(buf,len,
		"state      : 0x%x\n", status );
	/* start exclusion with sysfs change */

	ldec_mutex_lock( &ldec_proc_lock );

	len += sysfs_emit_at(buf,len,
		"virt       : 0x%llx\n", (uint64_t)proc_info.virt);
	len += sysfs_emit_at(buf,len,
		"srclen     : 0x%x\n", proc_info.srclen);
	len += sysfs_emit_at(buf,len,
		"dst_phys   : 0x%llx\n", proc_info.dst_phys);
	len += sysfs_emit_at(buf,len,
		"dstlen     : 0x%x\n", proc_info.dstlen);
	len += sysfs_emit_at(buf,len,
		"records    : 0x%x\n", proc_info.records);
	len += sysfs_emit_at(buf,len,
		"ch         : 0x%x\n", proc_info.ch);
	len += sysfs_emit_at(buf,len,
		"xsrcflush  : 0x%x\n", proc_info.xsrcflush);
	len += sysfs_emit_at(buf,len,
		"xdstflush  : 0x%x\n", proc_info.xdstflush);
		
	ldec_mutex_unlock( &ldec_proc_lock );
	/* end exculusion with sysfs change */

	len += sysfs_emit_at(buf,len,
		"ldec_base_addr  : 0x%llx\n", (uint64_t)lld_ldec_base_addr);
	len += sysfs_emit_at(buf,len,
		"LDEC Controller Register Values \n");	
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_DECMODE.DATA  :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_DECMODE.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_START.DATA    :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_START.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_TIMEOUT.DATA  :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_TIMEOUT.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_RECORDS.DATA  :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_RECORDS.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_DESTADDR.DATAL :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_DESTADDR.DATAL ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_DESTADDR.DATAH :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_DESTADDR.DATAH ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_CURRADDR.DATAL :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_CURRADDR.DATAL ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_CURRADDR.DATAH :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_CURRADDR.DATAH ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_BUSCLEAN.DATA :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_BUSCLEAN.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_INTEN.DATA    :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_INTEN.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_INTMSK.DATA   :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_INTMSK.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_INTCLR.DATA   :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_INTCLR.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_INT.DATA      :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_INT.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_INTRAW.DATA   :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_INTRAW.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_SRAMLIM.DATA   :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_SRAMLIM.DATA ));
	len += sysfs_emit_at(buf,len,
		"LZDECOMP_SMDQUELIM.DATA :0x%08x\n",readl_relaxed( &ldec->LZDECOMP_SMDQUELIM.DATA ));
	return len;
}
	
static DEVICE_ATTR_RO(ldec);	



static struct attribute *ldec_attrs[] = {
	&dev_attr_ldec.attr,
	NULL,   /* need to NULL terminate the list of attributes */
};

static struct attribute_group ldec_group = {
       .attrs = ldec_attrs,
};



/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_probe
 *
 * driver probe function
 *
 * @param [in]  pdev             device info
 *
 * @return	error code
 * @retval	0	success
 * @retval	-EINAL        invalid parameter
 * @retval	-ENOMEM       memory allocation error
 * @retval	-EIO          IO error
 */
/*----------------------------------------------------------------------------*/
static int ldec_probe(struct platform_device *pdev)

{
	struct resource *res = NULL;
	int ret =0;

	if( pdev == NULL ){			
		ldec_print(LDEC_DEBUG_ERROR,"ret=%d :: null pointer error \n",-EINVAL);
		return -EINVAL;	
	}

	dev_ldec = &pdev->dev;

	ret = sysfs_create_group(&(dev_ldec->kobj), &ldec_group);
	if (ret != 0) {
		ldec_print(LDEC_DEBUG_ERROR, "Can not create sysfs nodes.\n");
		return -EIO;
	}

	res = platform_get_resource(pdev, IORESOURCE_MEM, 0);
	if (IS_ERR(res)) {
		ldec_print(LDEC_DEBUG_ERROR, "Fail to  platform_get_resource(0)\n");
		return PTR_ERR(res);
	}
	lld_ldec_base_addr = devm_ioremap_resource(dev_ldec, res);
	ldec_print(LDEC_DEBUG_INFO,"lld_ldec_base_addr = 0x%p\n",lld_ldec_base_addr);
	ldec_print(LDEC_DEBUG_INFO,"lld_ldec_base_addr(phys) = 0x%016llx, end address =0x%016llx\n",res->start,res->end);
	if(!lld_ldec_base_addr){
		ldec_print(LDEC_DEBUG_ERROR,"lld_ldec_base_addr ERROR!\n");	
 		return -EIO;
	}
	
	res = platform_get_resource(pdev, IORESOURCE_MEM, 1);
	if (IS_ERR(res)) {
		ldec_print(LDEC_DEBUG_ERROR, "Fail to  platform_get_resource(1)\n");
		return PTR_ERR(res);
	}
	lz77_slave = res->start;
#ifdef LDEC_TRANS_CPU
	iomem_ldec_slave  = devm_ioremap_resource(dev_ldec, res);
	ldec_print(LDEC_DEBUG_INFO,"iomem_ldec_slave(virt) = 0x%016llx\n",(uint64_t)iomem_ldec_slave);
	ldec_print(LDEC_DEBUG_INFO,"iomem_ldec_slave(phys) = 0x%016llx ens address = 0x%016llx\n",res->start,res->end);
	if (iomem_ldec_slave == NULL) {
		ldec_print(LDEC_DEBUG_INFO, "ioremap failed.\n");
		ldec_print(LDEC_DEBUG_ERROR,"ret=%d\n",-EINVAL);
		return -EINVAL;
	}
	ldec_print(LDEC_DEBUG_INFO, "iomem_ldec_slave = 0x%llx\n", (uint64_t)iomem_ldec_slave);
#endif

	pclk = devm_clk_get(dev_ldec, "ldec_pclk");
	if (IS_ERR(pclk)) {
		ldec_print(LDEC_DEBUG_ERROR, "Fail to get pclk devm_clk_get()\n");
		return PTR_ERR(pclk);
	}

	aclk = devm_clk_get(dev_ldec, "ldec_aclk");
	if (IS_ERR(aclk)) {
		ldec_print(LDEC_DEBUG_ERROR, "Fail to get aclk devm_clk_get()\n");
		return PTR_ERR(aclk);
	}
	
	rst = devm_reset_control_get_exclusive(dev_ldec, NULL);
	if (IS_ERR(rst)) {
		ldec_print(LDEC_DEBUG_ERROR, "Fail to get LDEC reset:devm_reset_control_get_exclusive()\n");
		return PTR_ERR(rst);
	}

	/* allocate array area(4kB) for start address of pages */
	ldec_initial_page_array_vadr = devm_kmalloc(dev_ldec,INITIAL_PAGE_ARRAY_SIZE,GFP_KERNEL);
	if (ldec_initial_page_array_vadr == NULL){
		ldec_print(LDEC_DEBUG_ERROR,"4kB initial_page_array devm_kmalloc error!\n");
		return -ENOMEM;
	}

	if(dma_set_mask_and_coherent(dev_ldec, DMA_BIT_MASK(64)) != 0){	//initialize mask setting
		ldec_print(LDEC_DEBUG_ERROR,"dma_set_mask_and_coherent()\n");
		return -EIO;
	}

#ifndef LDEC_TRANS_CPU //DMA transfer mode
	if(sizeof(LLD_DMAC_LINKLIST) != 64){	//not support other than 64B of LinkedListItem size
		ldec_print(LDEC_DEBUG_ERROR,"ERROR! size of LinkedListItem != 64B current value=%ld\n",sizeof(LLD_DMAC_LINKLIST));
		return -EIO;
		
	}
	/* allocate middle buffer(4kB) */
	ldec_buffer_vadr = devm_kmalloc(dev_ldec,BUFFER_SIZE,GFP_KERNEL);
	if (ldec_buffer_vadr == NULL){
		ldec_print(LDEC_DEBUG_ERROR,"4kB buffer devm_kmalloc error!\n");
		return -ENOMEM;
	}
	ldec_buffer_padr = (uint8_t *)virt_to_phys((void*)ldec_buffer_vadr);
	
	//after kmalloc, write back may occur, so that do cache invalidate

	dma_handle_interbuffer = dma_map_single(dev_ldec, ldec_buffer_vadr, (size_t)BUFFER_SIZE, DMA_BIDIRECTIONAL);
	if (dma_mapping_error(dev_ldec, dma_handle_interbuffer)) {
		ldec_print(LDEC_DEBUG_ERROR,"dma_map_single() at probe() error!\n");
		return -EIO;
	}

	/* allocate initial area for LinkedList */
	ldec_initial_ll_vadr = devm_kmalloc(dev_ldec,INITIAL_LL_SIZE,GFP_KERNEL);
	if (ldec_initial_ll_vadr == NULL){
		ldec_print(LDEC_DEBUG_ERROR,"4kB initial LinkedList devm_kmalloc error!\n");
		return -ENOMEM;
	}
#endif //DMA transfer mode

	/* register ldec interrupt */
	res = platform_get_resource(pdev, IORESOURCE_IRQ, 0);
	if (res) {
		if (devm_request_threaded_irq(dev_ldec, res->start, &ldechw_process, NULL, IRQF_TRIGGER_NONE, "ldec_irq", 0)){
			ldec_print(LDEC_DEBUG_ERROR,"devm_request_threaded_irq() error!\n");
			return -EIO;
		}
	}
	else{
		ldec_print(LDEC_DEBUG_ERROR,"platform_get_resource() error!\n");
		return -EIO;
	}
	
	miscdev.name = "ldec";
	miscdev.minor = MISC_DYNAMIC_MINOR;
	miscdev.fops = &fops;
	
	ret = misc_register(&miscdev);
	if (ret){
		ldec_print(LDEC_DEBUG_ERROR,"ERROR!! misc_register()\n");
		return ret;
	}	
	ret = ldec_clk_rst(LDECHW_ENABLE);	/* release reset and supply clocks to LDEC */

	ldec_print(LDEC_DEBUG_INFO, "ldec_probe() finished..\n");
	ldec_print(LDEC_DEBUG_DEBUG,"ldec_probe() ret=%d\n",ret);
	return ret;
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_remove
 *
 * release interrupt registration etc.
 *
 * @param [in]  pdev             device info
 *
 * @return	error code
 * @retval	0	success
 * @retval	-EINVAL	invalid parameter
 * @retval	-EIO	IO error
 */
/*----------------------------------------------------------------------------*/

static int ldec_remove(struct platform_device *pdev)
{
	int ret = 0;
	struct device *dev;
	struct resource *res;
	
	/* parameter check*/
	if( pdev == NULL ){
		ldec_print(LDEC_DEBUG_ERROR,"ret=%d ::pdev  null pointer error \n",-EINVAL);
		return -EINVAL;
	}

	res = platform_get_resource(pdev, IORESOURCE_IRQ, 0);
	if (!res) {
		ldec_print(LDEC_DEBUG_ERROR,"platform_get_resource() error!\n");
		return -EIO;
	}
	disable_irq(res->start);
	
	misc_deregister(&miscdev);
	
	dev = &pdev->dev;
	sysfs_remove_group(&(dev->kobj), &ldec_group);
#ifndef LDEC_TRANS_CPU
	dma_unmap_single(dev_ldec, dma_handle_interbuffer, (size_t)BUFFER_SIZE, DMA_BIDIRECTIONAL);
#endif
	/* stop clocks and reset assert */
	ret = ldec_clk_rst(LDECHW_DISABLE);
	ldec_print(LDEC_DEBUG_DEBUG,"ldec_remove() ret=%d\n",ret);
	return ret;
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_suspend
 *
 * device suspend process
 *
 * @param [in]  pdev            device info
 * @param [in]  state           
 *
 * @return	 error code
 * @retval	0	success
 * @retval	-EIO	device error
 */
/*----------------------------------------------------------------------------*/
static int ldec_suspend(struct platform_device *pdev, pm_message_t state)
{
	int ret = 0;

	ldec_print(LDEC_DEBUG_DEBUG,"pdev = 0x%p \n", pdev);
	
	ldec_print(LDEC_DEBUG_INFO,"get mutex.\n" );
	
	ldechw_lock( LDEC_LOCK );	/* LDEC lock */
	
	/* assert reset and stop clocks */
	ret = ldec_clk_rst(LDECHW_DISABLE);
	
	ldechw_lock( LDEC_UNLOCK );

	ldec_print(LDEC_DEBUG_DEBUG,"ldec_suspend() ret=%d\n",ret);
	
	return ret;
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_resume
 *
 * resume ldec
 *
 * @param [in]  pdev             device info
 *
 * @return	 error code
 * @retval	0	success
 * @retval	-EIO	device error
 */
/*----------------------------------------------------------------------------*/
static int ldec_resume(struct platform_device *pdev)
{
	int ret = 0;
	ldec_print(LDEC_DEBUG_DEBUG,"pdev = 0x%p \n", pdev);
	ret = ldec_clk_rst(LDECHW_ENABLE);
	ldec_print(LDEC_DEBUG_DEBUG,"ret=%d\n",ret);
	return ret;
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_check_busreq
 *
 * check RE(bus request status) bit in BUSCLEAN register
 *
 * @return	error code
 * @retval	0	normal	bus request status=0
 * @retval	-EIO	device error 	bus request status=1
 **/
/*----------------------------------------------------------------------------*/
static int ldec_check_busreq(void)
{
	LZDECOMP_T *ldec;
	uint32_t state;
	uint32_t i;
	
	ldec = (LZDECOMP_T *)lld_get_base_addr_ldec();

	ldec_assert_NULL( ldec );

	for (i=0; i < LDEC_BUSCLEAN_CHK_NUM; i++){
		state = readl_relaxed( &ldec->LZDECOMP_BUSCLEAN.DATA );
		if( state == 0 ){
			return 0;
		}else{
			ldec_print(LDEC_DEBUG_DEBUG, "Bus_Request val=%x , msloop = %d \n", readl_relaxed( &ldec->LZDECOMP_BUSCLEAN.DATA ),LDEC_BUSCLEAN_CHK_TIME);
			msleep(LDEC_BUSCLEAN_CHK_TIME);
		}
	}
	ldec_print(LDEC_DEBUG_ERROR, "FATAL ERROR!. Couldn't clear Bus_Request reg_val=%x\n", readl_relaxed( &ldec->LZDECOMP_BUSCLEAN.DATA ));
	return -EIO;
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_sw_reset
 *
 * software reset
 *
 *
 * @return	error code
 * @retval	0	success
 * @retval -EIO	device error
 **/
/*----------------------------------------------------------------------------*/
static void ldec_sw_reset(void)
{

	LZDECOMP_T *ldec;

	ldec_print(LDEC_DEBUG_DEBUG, "exec \n");
	ldec = (LZDECOMP_T *)lld_get_base_addr_ldec();
	ldec_assert_NULL( ldec );
	writel_relaxed( LZDECOMP_RESET, &ldec->LZDECOMP_START.DATA );	/* software reset */

	return;
}



/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_clk_rst
 *
 * clock and system reset control
 *
 * @param [in]  sw 	LDECHW_ENABLE:start decompression, LDECHW_DISABLE:stop decompression(software reset)
 *
 * @return	error code
 * @retval	0	success
 * @retval	-EIO	device error
 * @retval	-EINVAL	invalid parameter
 */
/*----------------------------------------------------------------------------*/
static int ldec_clk_rst(uint32_t sw)
{
	int ret = 0;
	int fret;

	ldec_print(LDEC_DEBUG_INFO,"sw = %d\n", sw);
	
	switch (sw) {
		case LDECHW_ENABLE: 
			/*
			 * release system reset
			 * release LDEC software reset
			 */
			fret = reset_control_deassert(rst);
			if(fret){
				ret = -EIO;
				ldec_print(LDEC_DEBUG_ERROR, "failed reset_control_deassert) :: fret = %d, return = %d \n" , fret, ret);
				break;
			}
		
			/*
			 * supply pclk and aclk
			 */
			fret = clk_prepare_enable(pclk);
			if(fret){
				ret = -EIO;
				ldec_print(LDEC_DEBUG_ERROR, " failed clk_prepare_enable(pclk) :: fret = %d, return = %d \n" , fret, ret);
				break;
			}
	
			fret = clk_prepare_enable(aclk);
			if(fret){
				ret = -EIO;
				ldec_print(LDEC_DEBUG_ERROR, "failed clk_prepare_enable(aclk) :: fret = %d, return = %d \n" , fret, ret);
				break;
			}
	
			break;
		case LDECHW_DISABLE:
			/* stop clocks */
			clk_disable_unprepare(aclk);
			clk_disable_unprepare(pclk);

			/* assert system reset */
			fret = reset_control_assert(rst);
			if(fret){
				ret = -EIO;
				ldec_print(LDEC_DEBUG_ERROR, "failed reset_control_assert(rst) :: fret = %d, return = %d \n" , fret, ret);
				break;
			}

			break;

		default:
			ret = -EINVAL;   
			ldec_print(LDEC_DEBUG_ERROR, "parameter error(sw=%d)! return = %d \n" ,sw, ret);
			break;
	}
	ldec_print(LDEC_DEBUG_INFO,"ret = %d\n", ret);
	return ret;
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_aclk_enable
 *
 * supply aclk to LDEC
 *
 * @return	error code
 * @retval	0	success
 * @retval	-EIO	device error
 */
/*----------------------------------------------------------------------------*/
static int ldec_aclk_enable(void)
{
	int ret = 0;
	int fret;

	fret = clk_prepare_enable(aclk);
	if(fret){
		ret = -EIO;
		ldec_print(LDEC_DEBUG_ERROR, "failed clk_prepare_enable(aclk) :: fret = %d, return = %d \n" , fret, ret);
	}
	return ret;
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_aclk_disable
 *
 * stop aclk to LDEC
 *
 * @return void
 */
/*----------------------------------------------------------------------------*/

static void ldec_aclk_disable(void)
{
	clk_disable_unprepare(aclk);
}


static const struct of_device_id dev_match[] = {
	{ .compatible = D_DEVICENAME},
	{ /* end of list */ },
};
static struct platform_driver driver_info = {
	.driver = {
		.name = D_DRIVERNAME,
		.of_match_table = of_match_ptr(dev_match),
	},
	.probe = ldec_probe,
	.remove = ldec_remove,
	.suspend = ldec_suspend,
	.resume = ldec_resume,
};


/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_init
 *
 * LDEC driver initial process
 *
 *
 * @return	error code
 * @retval	0	success
 * @retval	other than 0	error
 */
/*----------------------------------------------------------------------------*/
static int __init ldec_init(void)
{
	int ret = 0;

	
	/* device registration */
	if(( ret = platform_driver_register(&driver_info)) != 0){
		ldec_print(LDEC_DEBUG_ERROR,"platform_driver_register() ret=%d\n", ret);
		return ret;
	}

	/* initialize exclusion resource */
	ldechw_resource_init();

	
#ifdef LDEC_USE_FPGA
	ldec_print(LDEC_DEBUG_DEBUG,"ldec.ko : target = fpga \n");
#else
	ldec_print(LDEC_DEBUG_DEBUG,"ldec.ko : target = es \n");
#endif

#ifdef LDEC_TRANS_CPU
	ldec_print(LDEC_DEBUG_DEBUG,"ldec.ko : transfer mode = cpu \n");
#else
	ldec_print(LDEC_DEBUG_DEBUG,"ldec.ko : transfer mode = dma \n");
#endif

#ifdef LDEC_TIMEOUT_FLAG
#ifndef LDEC_TRANS_CPU
	ldec_print(LDEC_DEBUG_DEBUG,"ldec.ko : time-out = enable \n");
#else	/* LDEC_TRANS_CPU */
	ldec_print(LDEC_DEBUG_DEBUG,"ldec.ko : time-out = disable \n");
#endif	/* LDEC_TRANS_CPU */
#else	/* LDEC_TIMEOUT_FLAG */
	ldec_print(LDEC_DEBUG_DEBUG,"ldec.ko : time-out = disable \n");
#endif	/* LDEC_TIMEOUT_FLAG */

#ifdef SLEEP70SEC4TEST
	ldec_print(LDEC_DEBUG_DEBUG,"ldec.ko : for test 70sec sleep \n");
#endif

#ifdef LDEC_IOCTL_TIMES
	ldec_print(LDEC_DEBUG_DEBUG,"for test : ioctl time measurement \n");
#endif
#ifdef LDEC_IRQ_TIMES
	ldec_print(LDEC_DEBUG_DEBUG,"for test : irq time measurement \n");
#endif
#ifdef LDEC_IRQ_TIMES_DETAIL
	ldec_print(LDEC_DEBUG_DEBUG,"for test : irq detail time measurement \n");
#endif
#ifdef LDEC_LOCK_TIMES
	ldec_print(LDEC_DEBUG_DEBUG,"for test : lock time measurement \n");
#endif

	ldec_print(LDEC_DEBUG_DEBUG,"ldec.ko : debug version :: print level=%x \n",LDEC_PRINT_LEVEL);
	ldec_print(LDEC_DEBUG_DEBUG,"ldec_init() ret=%d\n",ret);
	return ret;
}

/*----------------------------------------------------------------------------*/
/**
 * @brief ldec_exit
 *
 * driver exit process
 *
 */
/*----------------------------------------------------------------------------*/
static void __exit ldec_exit(void)
{
	platform_driver_unregister(&driver_info);
	ldec_print(LDEC_DEBUG_DEBUG,"ldec_exit() ret=%d\n",0);
}

module_init(ldec_init)
module_exit(ldec_exit)
MODULE_LICENSE("GPL");

/*---------------------------------------------------------------------------
  END
---------------------------------------------------------------------------*/
