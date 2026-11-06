#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>
#include <assert.h>
typedef unsigned long U;typedef unsigned W;
#define __errno_location date97_errno
static int *date97_errno(void){return &errno;}
static char out[65536];static unsigned used,reads,sizes,calls;static U app_base;static unsigned char request[32],model[16];static W n=32;
static int mocklog(int fd,const char *fmt,...){(void)fd;va_list a;va_start(a,fmt);int k=vsnprintf(out+used,sizeof out-used,fmt,a);va_end(a);assert(k>=0&&(unsigned)k<sizeof out-used);used+=k;errno=88;return k;}
#define dprintf mocklog
static long mocktid(long n,...){assert(n==178);errno=89;return 42;}
#define syscall mocktid
static int peek(U p,void *q,U l){reads++;errno=90;if(p>=(U)request&&p+l<=(U)request+sizeof request){memcpy(q,(void*)p,l);return 1;}if(p>=app_base+0x8227358&&p+l<=app_base+0x8227360){memcpy(q,model+4+(p-app_base-0x8227358),l);return 1;}if(p==app_base+0x8365c90&&l==2){memcpy(q,model,2);return 1;}return 0;}
#include "fx3-date-observe97r2.h"
static W sizefn(void *p){assert(p==request);sizes++;errno=91;return n;}
static int native(W dst,void *p){calls++;assert(errno==19);assert(dst==0x80900141||dst==7);if(p){assert(p==request);for(unsigned i=0;i<32;i++)assert(request[i]==i);request[2]=0xfe;}errno=5;return -1021;}
static void reset(void){for(unsigned i=0;i<32;i++)request[i]=i;reads=sizes=calls=used=0;out[0]=0;errno=19;}
int main(void){reset();assert(date97_sync(native,sizefn,0x80900141,request)==-1021);assert(errno==5&&calls==1&&sizes==1&&reads==2&&request[2]==0xfe);assert(strstr(out,"phase=before")&&strstr(out,"phase=after")&&strstr(out,"result=-1021 errno=5")&&strstr(out,"000102030405")&&strstr(out,"0001fe030405"));
 reset();assert(date97_sync(native,sizefn,7,request)==-1021);assert(errno==5&&calls==1&&sizes==0&&reads==0&&used==0);
 reset();assert(date97_sync(native,sizefn,0x80900141,0)==-1021);assert(errno==5&&calls==1&&sizes==0&&reads==0&&used==0);
 reset();n=4097;assert(date97_sync(native,sizefn,0x80900141,request)==-1021);assert(errno==5&&calls==1&&reads==0&&strstr(out,"captured=0"));n=32;
 reset();date97_events=64;assert(date97_sync(native,sizefn,0x80900141,request)==-1021);assert(errno==5&&calls==1&&reads==0);
 reset();U regs[31]={0};model[0]=1;model[1]=0;W dc=2,dn=0;memcpy(model+4,&dc,4);memcpy(model+8,&dn,4);regs[0]=(U)request;regs[19]=(U)request;int saved=errno;date97_point(80,0x2d7e6f4,regs);errno=saved;assert(errno==19&&strstr(out,"force_current=1 force_next=0")&&strstr(out,"date_current=2")&&strstr(out,"date_next=0"));for(unsigned i=0;i<32;i++)assert(request[i]==i);assert(model[0]==1&&model[1]==0);puts("DATE97R2_PASS native_args_result_errno_original_body_lifetime_preserved/before_after_exact_hex/unwatched_null_no_reads/bounds_eventcap/no_model_or_request_writes");}
