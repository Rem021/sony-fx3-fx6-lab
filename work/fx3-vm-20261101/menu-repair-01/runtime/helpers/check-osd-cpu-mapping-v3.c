
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
typedef unsigned long U;
#include "fx3-osd-core-v3.h"
static char fixture[262144];static unsigned position,closed;
static int test_open(const char *p,int flags){assert(!strcmp(p,"/proc/self/maps")&&flags==0);position=0;return 9;}
static long test_read(int fd,void *out,unsigned long n){assert(fd==9);unsigned left=strlen(fixture)-position;if(n>left)n=left;memcpy(out,fixture+position,n);position+=n;return n;}
static int test_close(int fd){assert(fd==9);closed++;return 0;}
#define open test_open
#define read test_read
#define close test_close
static int mapped_cpu(const void *bits,struct ho_frame *f){char buffer[4096],line[1024];unsigned used=0,over=0;int fd=open("/proc/self/maps",0);if(fd<0)return 0;long n;while((n=read(fd,buffer,sizeof buffer))>0){for(long j=0;j<n;j++){char c=buffer[j];if(c!='\n'){if(used<sizeof line-1)line[used++]=c;else over=1;continue;}line[used]=0;U begin=0,end=0,offset=0;char perm[5]={0},path[128]={0};if(!over&&sscanf(line,"%lx-%lx %4s %lx %*s %*s %127s",&begin,&end,perm,&offset,path)==5&&ho_cpu_mapping((U)bits,f->span,f->physical,begin,end,offset,perm,!strcmp(path,"/dev/mem"))){f->bits=(U)bits;f->map_begin=begin;f->map_end=end;f->map_offset=offset;close(fd);return 1;}used=over=0;}}close(fd);return 0;}

int main(void){struct ho_frame f={.span=0x96000,.physical=0x43feb5100UL};const void *bits=(void *)0x7efe036100UL;unsigned n=0;for(unsigned j=0;j<2100;j++)n+=sprintf(fixture+n,"00400000-00409000 r-xp 00000000 00:02 261 /usr/bin/im.elf\n");memset(fixture+n,'a',2000);n+=2000;fixture[n++]='\n';strcpy(fixture+n,"7efe036000-7efe0cd000 rw-s 43feb5000 00:06 3073 /dev/mem\n");assert(mapped_cpu(bits,&f)&&f.bits==(U)bits&&f.map_begin==0x7efe036000UL&&f.map_offset==0x43feb5000UL&&closed==1);unsigned hits=0;const char *negative[]={"7efe036000-7efe0cd000 rw-p 43feb5000 00:06 3073 /dev/mem\n","7efe036000-7efe0cd000 -w-s 43feb5000 00:06 3073 /dev/mem\n","7efe036000-7efe0cd000 rw-s 43feb5001 00:06 3073 /dev/mem\n","7efe036000-7efe037000 rw-s 43feb5000 00:06 3073 /dev/mem\n","7efe036000-7efe0cd000 rw-s 43feb5000 00:06 3073 /tmp/file\n"};for(unsigned j=0;j<5;j++){strcpy(fixture,negative[j]);assert(!mapped_cpu(bits,&f));hits++;}printf("CPU_MAPPING_PASS real_parser/large_maps_stream/chunk_and_overlong_lines/exact_shared_devmem_VA_physical_span/negative%u\n",hits);}
