/*
 *  arch/arm/mach-emxx/switch/switch-vup.c
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

//------------------ インクルード、ローカルマクロ/型定義 --------------------
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h> 
#include <fcntl.h> 
#include <stdbool.h>
#include <assert.h>
#include <unistd.h>
#include <time.h>
#include <sys/time.h>

#include "../include/mach/switch-vup.h"


#define SWITCH_RETRIES		0x0701
#define SWITCH_TIMEOUT		0x0702
#define SWITCH_SLAVE		0x0703
#define SWITCH_SLAVE_FORCE	0x0706
#define SWITCH_TENBIT		0x0704
#define SWITCH_FUNCS		0x0705
#define SWITCH_RDWR			0x0707
#define SWITCH_PEC			0x0708
#define SWITCH_SMBUS		0x0720
#define SWITCH_READ			0x0709
#define SWITCH_WRITE		0x0710
#define SWITCH_SET_POS		0x0711


#define SWITCH_VUP_SEED_BLOCK_SIZE    (0x400)  /* 営業所マイコンの１ブロックサイズ(1KB) */

/* 営業所マイコンバージョンアップ制御レジスタ */
#define SWITCH_VUP_ADDR_VUPCTRL   	  (0x1D)  /* バージョンアップ制御レジスタ内部アドレス */
#define SWITCH_VUP_VUPCTRL_START  	  (0x01)  /* バージョンアップ開始ビット */
#define SWITCH_VUP_VUPCTRL_BSTART 	  (0x02)  /* ブート領域バージョンアップ開始ビット */
#define SWITCH_VUP_VUPCTRL_END    	  (0x04)  /* バージョンアップ終了ビット */
#define SWITCH_VUP_VUPCTRL_SIZE_SHIFT (0x03)  /* 4bit目からサイズが開始するので3bit左シフト */

/* 営業所マイコンバージョンアップステータスレジスタ */
#define SWITCH_VUP_ADDR_VUPSTAT  (0x1E) /* バージョンアップステータスレジスタ内部アドレス */
#define SWITCH_VUP_VUPSTAT_IDLE  (0x00) /* 非バージョンアップ状態 */
#define SWITCH_VUP_VUPSTAT_START (0x01) /* バージョンアップ開始処理中 */
#define SWITCH_VUP_VUPSTAT_WAIT  (0x02) /* バージョンアップ待機中 */
#define SWITCH_VUP_VUPSTAT_WRITE (0x03) /* バージョンアップ処理中 */
#define SWITCH_VUP_VUPSTAT_END   (0x04) /* バージョンアップ終了処理中 */
#define SWITCH_VUP_VUPSTAT_ERR   (0x80) /* エラービット */

/* 営業所マイコンバージョンアップデータレジスタ */
#define SWITCH_VUP_ADDR_VUPDATA  (0x1F) /* バージョンアップデータレジスタ内部アドレス開始アドレス */
#define SWITCH_VUP_VUPDATA_SIZE  (0x20) /* バージョンアップデータレジスタサイズ */

/* 営業所マイコンバージョンアップデータサイズレジスタ */
#define SWITCH_VUP_ADDR_VUPSIZE  (0x3F) /* バージョンアップデータサイズレジスタ内部アドレス */

/* 営業所マイコン待ち時間 */
#define SWITCH_VUP_WAIT_MINTIME_VUPSTART	(50)  /* 書き込み1ブロックあたり50msec待つ */
#define SWITCH_VUP_WAIT_MAXTIME_VUPSTART	(370) /* 書き込み1ブロックあたり370msec待つ */
#define SWITCH_VUP_VUPSTART_POLL_TIME		(100) /* 書き込み開始ステータスポーリング周期 */

#define SWITCH_VUP_WAIT_MINTIME_VUPWRITE	(30)  /* 1書き込みあたり最低30msec待つ */
#define SWITCH_VUP_WAIT_MAXTIME_VUPWRITE	(130) /* 1書き込みあたり最大130msec待つ */
#define SWITCH_VUP_VUPWRITE_POLL_TIME		(10)  /* 書き込みステータスポーリング周期 */

#define SWITCH_VUP_WAIT_MINTIME_VUPEND		(110) /* 書き込み終了処理最低待ち時間 */
#define SWITCH_VUP_WAIT_MAXTIME_VUPEND		(550) /* 書き込み終了処理最大待ち時間 */
#define SWITCH_VUP_VUPEND_POLL_TIME			(40)  /* 書き込み終了ステータスポーリング周期 */

#define SWITCH_VUP_WAIT_NO_TIMEOUT		(1)
#define SWITCH_VUP_WAIT_NO_POLLTIME		(1)

/* 営業所マイコンスレーブアドレス */
#define SWITCH_ADD_S1 (0x09)
#define SWITCH_ADD_S2 (0x0A)
#define SWITCH_ADD_S3 (0x0B)
#define SWITCH_ADD_VF (0x10)

/* sys_ioctl書き込み/読み込み */
#define SWITCH_SYS_IOCTL_WRITE (0x00)
#define SWITCH_SYS_IOCTL_READ  (0x10)

/* 配列添字 */
#define SWITCH_SUBSCRIPT_SUBADD	(0)
#define SWITCH_SUBSCRIPT_RDATA	(0)
#define SWITCH_SUBSCRIPT_WDATA	(1)

/* コールバック関数判定 */
#define SWITCH_OK		0
#define SWITCH_NG		-1

#define SWITCH_RETRY	(5)

#define SWITCH_READ_MAX	64

/*phyadr*/
#define PHYADR_IOCWRITE    _IO('k', 0)
#define PHYADR_IOCREAD     _IO('k', 1)
#define PHYADR_IOCDUMP     _IO('k', 2)
#define PHYADR_IOCMALLOC   _IO('k', 3)
#define PHYADR_IOCFREE     _IO('k', 4)

struct stPhyadr_drv_cmd{
	unsigned long address;
	unsigned long value;
	unsigned long mask;
	unsigned long length;
	unsigned char * buf;
};
#define PHYADR_CMD_INFO struct stPhyadr_drv_cmd
PHYADR_CMD_INFO phyadr_info;


//--------------------- ローカル関数のプロトタイプ宣言 ----------------------

int vup_status_check(unsigned long timeOut, unsigned long pollTime, unsigned char nowStatus, unsigned char expStatus);
int vup_readbuff(void);
int vup_writebuff(unsigned char *buf, int size);

//------------------------ ローカル変数の宣言・定義 -------------------------

unsigned char  read_buf[SWITCH_READ_MAX];
unsigned char  set_reg[2];
int  switch_fd    = 0;
unsigned long  address = 0;

//--------------------------- ローカル関数の定義 ----------------------------

/*!
  関数の詳細:バージョンアップ書き込み開始処理
*/
void if_switch_ver_up(unsigned char *data, unsigned short size, switch_vup_type type , void (*callback) (int status))
{
    unsigned char  blockNum;
    unsigned long  writeDone;
    unsigned long  switchWriteSize = 0;
    unsigned char  vup_buf[SWITCH_VUP_VUPDATA_SIZE+2];
    unsigned char  vup_ctrl  = 0;
    int  ret       = SWITCH_OK;

    //phyadr
    int phy_fd = 0;
    unsigned char *phyadr_buf;

    phyadr_info.address = 0xe0110624;
    phyadr_info.value   = 0x002f002f;
    phyadr_info.mask    = 0x00ff00ff;
    phyadr_info.buf     = phyadr_buf;

    phy_fd = open("/dev/phyadr", O_RDWR);
    ioctl(phy_fd, PHYADR_IOCWRITE, &phyadr_info);

    memset(vup_buf,  0x00, sizeof(vup_buf));
    memset(set_reg,  0x00, sizeof(set_reg));
    memset(read_buf, 0x00, sizeof(read_buf));

    /* open */
    switch_fd = open("/dev/i2c", O_RDWR, 0);
	
    if (switch_fd < SWITCH_OK)
    {
	printf("open-error\n\n");
    }

    printf("\n\n*** VUP START ***\n\n");

    /* 管理テーブル更新 */
    switch(type)
    {
    case VUP_TYPE_S1:
    case VUP_TYPE_S1_BOOT:
    	address = SWITCH_ADD_S1;
    	break;
    case VUP_TYPE_S2:
    case VUP_TYPE_S2_BOOT:
    	address = SWITCH_ADD_S2;
        break;
    case VUP_TYPE_S3:
    case VUP_TYPE_S3_BOOT:
    	address = SWITCH_ADD_S3;
        break;
    case VUP_TYPE_VF:
    case VUP_TYPE_VF_BOOT:
        address = SWITCH_ADD_VF;
        break;
    default:
    	printf("address_type-error\n");
    	ret = SWITCH_NG;
    	goto SWITCH_CALLBACK;
    }

    //スレーブアドレス、R/Wを設定
    ret = ioctl(switch_fd, SWITCH_SLAVE_FORCE, address);
    ret = ioctl(switch_fd, SWITCH_TENBIT, SWITCH_SYS_IOCTL_WRITE);
	
    /* 営業所マイコン消去ブロック数算出 */
    blockNum = size / SWITCH_VUP_SEED_BLOCK_SIZE;
    if(0x00 != size % SWITCH_VUP_SEED_BLOCK_SIZE)
    {
        blockNum++;
    }

    vup_ctrl = blockNum << SWITCH_VUP_VUPCTRL_SIZE_SHIFT;
    if(type >= VUP_TYPE_S1_BOOT) /* ブート領域 */
    {
        vup_ctrl |= SWITCH_VUP_VUPCTRL_BSTART;
    }
    else                    /* 通常領域 */
    {
        vup_ctrl |= SWITCH_VUP_VUPCTRL_START;
    }
	
    //サブアドレスとデータを格納
    set_reg[SWITCH_SUBSCRIPT_SUBADD] = SWITCH_VUP_ADDR_VUPCTRL;
    set_reg[SWITCH_SUBSCRIPT_WDATA] = vup_ctrl;

    /* 制御レジスタへのバージョンアップ開始書き込み */
    ret = vup_writebuff(set_reg, 2);

    if(ret < SWITCH_OK)
    {
    	printf("write_start-error1\n");
    	ret = SWITCH_NG;
    	goto SWITCH_CALLBACK;
    }
	
    /* 営業所マイコンが準備に必要な最大時間を待つ */
    usleep((SWITCH_VUP_WAIT_MAXTIME_VUPSTART * 1000) * blockNum );
	
    /* ステータスレジスタポーリング(ポーリングしない)  */
    ret = vup_status_check(SWITCH_VUP_WAIT_NO_TIMEOUT, SWITCH_VUP_WAIT_NO_POLLTIME, SWITCH_VUP_VUPSTAT_START, SWITCH_VUP_VUPSTAT_WAIT);
    if(ret < SWITCH_OK)
    {
	printf("vup_status_check-error1\n");
	ret = SWITCH_NG;
	goto SWITCH_CALLBACK;
    }


    for(writeDone = 0; writeDone < size; writeDone += switchWriteSize)
    {
        /* 書き込みサイズ算出 */
        switchWriteSize = (SWITCH_VUP_VUPDATA_SIZE < size - writeDone)
            ? SWITCH_VUP_VUPDATA_SIZE : size - writeDone;
    	
    	/* サブアドレス */
    	vup_buf[SWITCH_SUBSCRIPT_SUBADD] = SWITCH_VUP_ADDR_VUPDATA;
    	
        /* 書き込みバッファにコピー（writeで一気に書くため。） */
        memcpy(&vup_buf[SWITCH_SUBSCRIPT_WDATA], data + writeDone, switchWriteSize);
    	
        /* バッファのお尻にサイズを代入 */
        vup_buf[SWITCH_VUP_VUPDATA_SIZE+1] = switchWriteSize;

    	/* ダウンロードデータレジスタへのバージョンアップ開始書き込み */
        ret = vup_writebuff(vup_buf, (SWITCH_VUP_VUPDATA_SIZE+2));
    	
        if(ret < SWITCH_OK)
        {
            printf("write_data-error2\n");
	    ret = SWITCH_NG;
	    goto SWITCH_CALLBACK;
        }

    	/* 営業所マイコンが準備に必要な最大時間を待つ */
		usleep(SWITCH_VUP_WAIT_MINTIME_VUPWRITE * 1000);
    	
    	/* ステータスレジスタポーリング */
    	ret = vup_status_check((SWITCH_VUP_WAIT_MAXTIME_VUPWRITE - SWITCH_VUP_WAIT_MINTIME_VUPWRITE),
    							SWITCH_VUP_VUPWRITE_POLL_TIME,
    							SWITCH_VUP_VUPSTAT_WRITE,
    							SWITCH_VUP_VUPSTAT_WAIT);
		
    	if(ret < SWITCH_OK)
		{
	    	printf("vup_status_check-error2\n");
	    	ret = SWITCH_NG;
	    	goto SWITCH_CALLBACK;
		}
    }

    /* 制御レジスタへのバージョンアップ終了書き込み */
    set_reg[SWITCH_SUBSCRIPT_SUBADD] = SWITCH_VUP_ADDR_VUPCTRL;
    set_reg[SWITCH_SUBSCRIPT_WDATA] = SWITCH_VUP_VUPCTRL_END;
    ret = vup_writebuff(set_reg, 2);
	
    if(ret < SWITCH_OK)
    {
	printf("write_end-error3\n");
	ret = SWITCH_NG;
	goto SWITCH_CALLBACK;
    }
	
    /* 営業所マイコンが準備に必要な最大時間を待つ */
    usleep(SWITCH_VUP_WAIT_MAXTIME_VUPEND * 1000);

    ret = vup_status_check(SWITCH_VUP_WAIT_NO_TIMEOUT, SWITCH_VUP_WAIT_NO_POLLTIME, SWITCH_VUP_VUPSTAT_END, SWITCH_VUP_VUPSTAT_IDLE);

    close(switch_fd);

    if(ret >= SWITCH_OK)
    {
	printf("\n\n*** VUP END ***\n\n");
    }
    else
    {
	printf("\n\n*** VUP ERROR END ***\n\n");
	ret = SWITCH_NG;
    }

    //コールバック処理
    SWITCH_CALLBACK:
    callback(ret);
}


/*!
  関数の詳細:バージョンアップ読み込み処理
*/
int vup_status_check(unsigned long timeOut, unsigned long pollTime, unsigned char nowStatus, unsigned char expStatus)
{
    int i;
    int ret = SWITCH_OK;
    unsigned long  maxWait = 0;
	
	
    if(0 == pollTime)           /* for QAC */
    {
        return SWITCH_NG;
    }

	maxWait = timeOut / pollTime;
	
	for(i = 0; i < maxWait; i++)
	{
		//読み込み処理
		ret =  vup_readbuff();
		usleep(SWITCH_VUP_WAIT_MINTIME_VUPWRITE * 1000);

		if(ret < SWITCH_OK)
		{
			printf("read-error\n");
			return SWITCH_NG;
		}
		
		if(read_buf[SWITCH_SUBSCRIPT_RDATA] != nowStatus)
		{
			break;
		}
		/* 営業所マイコンが準備に必要な最大時間を待つ */
		usleep((pollTime * 1000)*2);
	}
	
	if(i >= maxWait)
	{
		return SWITCH_NG;
	}
	else if(expStatus != read_buf[SWITCH_SUBSCRIPT_RDATA])
	{
		return SWITCH_NG;
	}
	else
	{
		return SWITCH_OK;
	}
}

/*!
  関数の詳細: 読み込み処理
*/
int vup_readbuff(void)
{
	int i;
	int ret = SWITCH_OK;
	for( i = 0; i < SWITCH_RETRY; i++ )
	{
	
		//読み込みを行う際、書き込みを行う
		set_reg[SWITCH_SUBSCRIPT_SUBADD] = SWITCH_VUP_ADDR_VUPSTAT;
		ret = write(switch_fd, set_reg, 1);

		usleep(1000);

		//読み込みを行う
		read_buf[SWITCH_SUBSCRIPT_SUBADD] = SWITCH_VUP_ADDR_VUPSTAT;
		ret = read(switch_fd, read_buf, 1);
	
		if( ret >= SWITCH_OK )
		{
			break;	
		}
	}
	if( ret >= SWITCH_OK )
	{
		//処理無し
	} 
	else
	{
		printf("\n*** Read Retry Over ***\n");
	}
	return ret;
}

/*!
  関数の詳細: 書き込み処理
*/
int vup_writebuff(unsigned char *buf, int size)
{
	int i;
	int ret = SWITCH_NG;

	for( i = 0; i < SWITCH_RETRY; i++ )
	{
		//書き込みを行う
		ret = write(switch_fd, buf, size);

		if( ret >= SWITCH_OK )
		{
			break;
		}
	}

	if( ret >= SWITCH_OK )
	{
		//処理無し
	}
	else
	{
		printf("\n*** Write Retry Over ***\n");
	}
	return ret;
}
