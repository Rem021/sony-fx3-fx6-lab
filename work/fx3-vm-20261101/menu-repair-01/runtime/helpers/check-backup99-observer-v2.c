#include <stdio.h>
#include <string.h>
#include <stdarg.h>
#include <errno.h>
#include <assert.h>
static int*test_errno(void){return &errno;}
#define __errno_location test_errno
static unsigned char bytes99[2]={1,1};static unsigned writes,reads;static int read_fail,write_result=1;static char logs99[8192];static unsigned used;
static int actual_write(unsigned service,unsigned key,const void*p){assert(errno==19);assert((service==0x2cf&&key==0x02cf0014)||(service==0x107&&key==0x01070140)||key==7);writes++;if(write_result==1&&key!=7)bytes99[key==0x01070140]=*(const unsigned char*)p;errno=5;return write_result;}
static int actual_read(unsigned key,void*p,int n){assert(n==1&&(key==0x02cf0014||key==0x01070140));reads++;errno=88;if(read_fail)return -1021;*(unsigned char*)p=bytes99[key==0x01070140];return 1;}
static void*lookup(void*h,const char*n){assert(h==(void*)-1);errno=89;if(!strcmp(n,"Backup_write"))return actual_write;if(!strcmp(n,"Backup_nread"))return actual_read;assert(0);return 0;}
#define dlsym lookup
static int log99(int fd,const char*fmt,...){(void)fd;va_list a;va_start(a,fmt);int n=vsnprintf(logs99+used,sizeof logs99-used,fmt,a);va_end(a);assert(n>0&&(unsigned)n<sizeof logs99-used);used+=n;errno=90;return n;}
#define dprintf log99
static long tid99(long n,...){assert(n==178);errno=91;return 9;}
#define syscall tid99
#include "fx3-backup-return-v3-date99-nread.c"
int main(void){unsigned char v=0;errno=19;assert(Backup_write(0x2cf,0x02cf0014,&v)==1&&errno==5&&v==0&&!reads);errno=19;assert(Backup_write(0x107,0x01070140,&v)==1&&errno==5&&reads==2&&writes==2&&v==0);assert(strstr(logs99,"native_return=1")&&strstr(logs99,"AP_return=1 AP_value=0")&&strstr(logs99,"mirror_return=1 mirror_value=0"));write_result=-1021;errno=19;assert(Backup_write(0x107,0x01070140,&v)==-1021&&errno==5&&reads==2);write_result=1;read_fail=1;errno=19;assert(Backup_write(0x107,0x01070140,&v)==1&&errno==5&&reads==4&&strstr(logs99,"AP_return=-1021 AP_value=255"));errno=19;assert(Backup_write(9,7,&v)==1&&errno==5&&reads==4&&writes==5);puts("BACKUP99_OBSERVER_V2_USER_ABI_PASS original_args_bytes_return_errno/only_two_real_keys/native_write_return1_preserved/independent_readback_after_mirror/no_extra_write/native_read_failure_not_success");}
