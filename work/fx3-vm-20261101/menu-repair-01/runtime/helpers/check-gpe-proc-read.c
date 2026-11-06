#include <assert.h>
#include <stdio.h>
#include <string.h>
static char fixture[16000];static unsigned long cursor,total;
static int fake_open(const char *p,int f){(void)f;assert(!strcmp(p,"/proc/udm/dmm_extents"));cursor=0;return 9;}
static int fake_close(int fd){assert(fd==9);return 0;}
static long fake_read(int fd,void *p,unsigned long n){assert(fd==9);if(n>4096)n=4096;if(n>total-cursor)n=total-cursor;memcpy(p,fixture+cursor,n);cursor+=n;return n;}
#define open fake_open
#define close fake_close
#define read fake_read
static int extent_live(void){
 char data[65536];int fd=open("/proc/udm/dmm_extents",0);if(fd<0)return 0;long n=0,part;while(n<sizeof(data)-1&&(part=read(fd,data+n,sizeof(data)-1-n))>0)n+=part;close(fd);if(n<=0||n>=sizeof(data)-1)return 0;data[n]=0;
 char *line=data;while(line&&*line){unsigned int a,b,c,d,e,f,g,h;unsigned long start,parent,offset,bytes;
 if(sscanf(line,"%x %x %x %x %x %x %x %x %lx (%lx+%lx) %lx",&a,&b,&c,&d,&e,&f,&g,&h,&start,&parent,&offset,&bytes)==12&&d==0x545&&c==1&&g==3&&start==0x43feb5000UL&&bytes==0x140000UL)return 1;
 while(*line&&*line!='\n')line++;if(*line)line++;else break;}return 0;
}
int main(void){memset(fixture,'\n',sizeof fixture);const char *row="0081 0003 00000001 00000545 00000000 00000000 00000003 0000008c 43feb5000 (430400000+0fab5000) 00140000\n";memcpy(fixture+9000,row,strlen(row));total=9000+strlen(row);assert(extent_live());total=4096;assert(!extent_live());total=9000+strlen(row);fixture[9000+21]='9';assert(!extent_live());puts("PROC_SHORT_READ_PASS validextent_after9000B; missing_and_foreign_type_rejected");}
