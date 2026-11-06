#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
static long stub_pread(int,void*,unsigned long,long);
static int stub_open(const char*,int,...);
static long stub_read(int,void*,unsigned long);
static int stub_close(int);
static void *stub_mmap(void*,unsigned long,int,int,int,long);
static int stub_munmap(void*,unsigned long);
static int stub_printf(int,const char*,...);
#define pread stub_pread
#define open stub_open
#define read stub_read
#define close stub_close
#define mmap stub_mmap
#define munmap stub_munmap
#define dprintf stub_printf
#define __errno_location stub_errno
static int *stub_errno(void){static int e;return &e;}
int dlinfo(void *h,int r,void *p){(void)h;(void)r;(void)p;return -1;}
#define FX3_GPE_HOST_TEST 1
#include "fx3-gpe-observe-v14-guard-v1.c"
static unsigned char memory[EXT_BYTES],before[EXT_BYTES];
static unsigned maps,unmaps,cmd_lines,summary_lines,statuses,callbacks,order,laststatus;
static int live=1,badread=0,mapfail=0,sendfail=0;
static struct gpe_callback_param lastcb;
static void callback(const void *p){memcpy(&lastcb,p,16);assert(order==0);order=1;callbacks++;assert(memory[0x100]==0x44);}
static int complete(unsigned src,const void *p,size_t n){assert(src==0x123);assert(n==4);memcpy(&laststatus,p,4);assert(laststatus==0||laststatus==5);assert(order<=1);order=2;statuses++;return !sendfail;}
static int stub_printf(int fd,const char *fmt,...){(void)fd;va_list ap;va_start(ap,fmt);char buf[2048];int n=vsnprintf(buf,sizeof(buf),fmt,ap);va_end(ap);assert(n>0&&n<(int)sizeof(buf));
 if(strstr(buf,"FX3_GPE_CMD op=")){cmd_lines++;const char *fields[]={" op="," seq="," async="," fmt="," w="," h="," dst_phys="," src_phys="," flags="," result="};for(unsigned i=0;i<10;i++)assert(strstr(buf,fields[i]));}
 if(strstr(buf,"FX3_GPE_CMD_SUMMARY"))summary_lines++;
 fputs(buf,stdout);return n;}
static long stub_pread(int fd,void *p,unsigned long n,long a){(void)fd;if(badread)return -1;memcpy(p,(void*)a,n);return n;}
static int stub_open(const char *p,int f,...){(void)f;if(!strcmp(p,"/proc/udm/dmm_extents"))return 81;if(!strcmp(p,"/proc/self/maps"))return 82;return 80;}
static long stub_read(int fd,void *p,unsigned long n){static int last,used;if(last!=fd){last=fd;used=0;}if(used){used=0;return 0;}used=1;char buf[1024];if(fd==81)snprintf(buf,sizeof(buf),"0 0 1 %x 0 0 3 0 43feb5000 (43feb5000+0) 140000\n",live?0x545:0x546);else snprintf(buf,sizeof(buf),"%lx-%lx r-xp 0 0:0 0\n",(unsigned long)callback&~4095UL,((unsigned long)callback&~4095UL)+4096);size_t z=strlen(buf);assert(z<n);memcpy(p,buf,z);return z;}
static int stub_close(int fd){(void)fd;return 0;}
static void *stub_mmap(void *p,unsigned long n,int a,int b,int fd,long off){(void)p;(void)a;(void)b;(void)fd;assert(n==EXT_BYTES&&off==EXT_BASE);maps++;return mapfail?(void*)-1:memory;}
static int stub_munmap(void *p,unsigned long n){assert(p==memory&&n==EXT_BYTES);unmaps++;return 0;}
static void p32(unsigned char *p,unsigned v){memcpy(p,&v,4);}
static void p64(unsigned char *p,U v){memcpy(p,&v,8);}
static void mkfill(unsigned char *p,unsigned fmt){memset(p,0,56);p64(p,PAYLOAD_BASE);p32(p+16,3);p32(p+20,2);p32(p+24,5);p32(p+28,fmt);p[32]=0x11;p[33]=0x22;p[34]=0x33;p[35]=0x44;p[37]=255;p[38]=1;}
static void reset(void){raster_failed=0;fills_done=0;order=0;live=1;badread=mapfail=sendfail=0;memset(memory,0xa5,sizeof(memory));}
int main(void){physical=80;process_mem=80;draw_complete=complete;unsigned char p[144],f[24]={0};
 for(unsigned fmt=0;fmt<2;fmt++){reset();mkfill(p,fmt);assert(fill(0,0,10,0,p)==0);unsigned bpp=fmt?4:2;for(unsigned y=0;y<2;y++)for(unsigned x=0;x<3;x++){unsigned char *q=memory+0x100+(y*5+x)*bpp;if(fmt)assert(!memcmp(q,"\x44\x33\x22\x11",4));else assert(!memcmp(q,"\x34\x12",2));}assert(memory[0xff]==0xa5&&memory[0x100+3*bpp]==0xa5);assert(flush(0,0,11,0x123,f)==0);}
 reset();mkfill(p,1);p[38]=0;p64(p+40,(U)callback);p64(p+48,0xabc);assert(fill(0,0,12,0x123,p)==0);assert(order==2&&lastcb.sequence==12&&!lastcb.zero&&lastcb.argument==0xabc);
 order=0;p[38]=1;unsigned old=statuses;assert(fill(0,0,13,0x123,p)==0&&statuses==old&&order==1);
 memset(f,0,24);f[0]=1;p64(f+8,(U)callback);p64(f+16,0xdef);order=0;assert(flush(0,0,14,0x123,f)==0&&order==1&&lastcb.argument==0xdef);
 for(unsigned fmt=0;fmt<2;fmt++){reset();for(unsigned i=0;i<64;i++)memory[0x100+i]=(unsigned char)i;
 memset(p,0,144);p64(p,PAYLOAD_BASE+0x400);p64(p+56,PAYLOAD_BASE);p32(p+16,3);p32(p+20,2);p32(p+32,3);p32(p+36,2);p32(p+48,5);p32(p+52,fmt);p32(p+72,3);p32(p+76,2);p32(p+88,5);p32(p+92,fmt);p[114]=255;p[121]=1;memcpy(before,memory,sizeof(memory));assert(blit(0,0,15,0,p)==0);unsigned bpp=fmt?4:2;for(unsigned y=0;y<2;y++){memcpy(before+0x500+y*5*bpp,before+0x100+y*5*bpp,3*bpp);}assert(!memcmp(memory,before,sizeof(memory)));}
 for(unsigned t=0;t<8;t++){reset();mkfill(p,1);if(t==0)p64(p,EXT_BASE+EXT_BYTES);if(t==1)p64(p,EXT_BASE);if(t==2)p64(p,EXT_BASE+EXT_BYTES-16);if(t==3)live=0;if(t==4)p32(p+28,2);if(t==5)badread=1;if(t==6)p64(p+40,3);if(t==7)mapfail=1;memcpy(before,memory,sizeof(memory));old=statuses;assert(fill(0,0,20+t,0x123,p)==5);assert(statuses==old);assert(!memcmp(before,memory,sizeof(memory)));}

 /* Native Main stub: adapter returns failure, Main sends the sole 4B5. */
 reset();mkfill(p,1);p64(p,1);p[38]=0;old=statuses;int rc=fill(0,0,29,0x123,p);assert(rc==5&&statuses==old);assert(complete(0x123,&rc,4)&&statuses==old+1&&laststatus==5);
 /* Source outside 545, overlap and unsupported flags: reject before writes. */
 for(unsigned t=0;t<3;t++){reset();memset(p,0,144);p64(p,PAYLOAD_BASE+0x400);p64(p+56,t==0?1:t==1?PAYLOAD_BASE+0x400:PAYLOAD_BASE);p32(p+16,2);p32(p+20,2);p32(p+32,2);p32(p+36,2);p32(p+48,4);p32(p+52,1);p32(p+72,2);p32(p+76,2);p32(p+88,4);p32(p+92,1);p[114]=255;p[121]=1;if(t==2)p[115]=1;memcpy(before,memory,sizeof(memory));assert(blit(0,0,40+t,0,p)==5&&!memcmp(memory,before,sizeof(memory)));}
 reset();memset(f,0,24);assert(flush(0,0,30,0x123,f)==5);mkfill(p,1);assert(fill(0,0,31,0,p)==0);p64(p,1);assert(fill(0,0,32,0,p)==5);assert(flush(0,0,33,0x123,f)==5);
 reset();mkfill(p,1);sendfail=1;p[38]=0;assert(fill(0,0,34,0x123,p)==5&&raster_failed);sendfail=0;
 reset();seen=0;memset(stats,0,sizeof(stats));cmd_lines=summary_lines=0;mkfill(p,1);for(unsigned i=0;i<1100;i++)assert(fill(0,0,i,0,p)==0);assert(cmd_lines==200&&summary_lines==3&&stats[0].total==1100&&stats[0].ok==1100);assert(maps>=unmaps);
 puts("PASS adapter: pixels, extent rejection zero writes, completion ordering, sticky flush, marker fields and throttling; ASan/UBSan enabled");return 0;}
