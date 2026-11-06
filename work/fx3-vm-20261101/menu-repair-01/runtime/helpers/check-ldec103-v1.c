#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include "fx3-ldec-soft103-v1.c"
B __this_module[768];
struct node103 udif_devnodes[6]={[5]={"ldec",0,251,205,1}};
static B target[1024*1024],source[1024*1024];static struct request103 wire;
static int copy_fail,alloc_fail,registered_test;
int printk(const char*f,...){(void)f;return 0;}
void *vmalloc(U n){return alloc_fail?0:malloc(n);}void vfree(void*p){free(p);}
U __arch_copy_from_user(void*d,const void*s,U n){if(copy_fail)return n;if((U)s==0x10000&&n==32){memcpy(d,&wire,n);return 0;}if((U)s==0x20000&&n<=sizeof(source)){memcpy(d,source,n);return 0;}return n;}
U arch_p32_to_p64(W p){return 0x400000000UL+p;}
void*arch_phys_to_va(U p){return p==0x41d300000UL?target:0;}
U arch_va_to_phys(U p){return p>=(U)target&&p<(U)target+sizeof(target)?0x41d300000UL+p-(U)target:0;}
int udif_cdev_register(void*p){assert(p==cdev103&&cdev103[16]==(U)__this_module);registered_test=1;return 0;}
int udif_cdev_unregister(void*p){assert(p==cdev103);registered_test=0;return 0;}
static U load(const char*p,B*b,U cap){FILE*f=fopen(p,"rb");assert(f);U n=fread(b,1,cap,f);assert(feof(f));fclose(f);return n;}
int main(int argc,char**argv){assert(argc==7);assert(init_module()==0&&registered_test);void*token=(void*)&magic103;struct file103 f={251*1048576U+205,&token};struct ioctl103 c={1,0x10000,0};assert(open103(&f)==0);
 for(int i=1;i<7;i+=2){U n=load(argv[i],source,sizeof(source));B*ref=malloc(sizeof(target));U m=load(argv[i+1],ref,sizeof(target));wire=(struct request103){0x20000,(W)n,0x1d300000,(W)m,(W)((m+4095)/4096),8,0,1,{0,0}};memset(target,0xa5,sizeof(target));assert(ioctl103(&f,&c)==0);assert(!memcmp(target,ref,m));for(U j=m;j<sizeof(target);j++)assert(target[j]==0xa5);printf("AP103_HOST_IOCTL_EXACT %s bytes=%lu fnv=%#lx\n",argv[i],m,hash103(target,m));free(ref);}
 memset(target,0xa5,sizeof(target));struct request103 good=wire;
#define BAD(mut,expected) do{wire=good;mut;assert(ioctl103(&f,&c)==(expected));for(U j=0;j<sizeof(target);j++)assert(target[j]==0xa5);}while(0)
 BAD(wire.source_bytes=0,-22);BAD(wire.destination_bytes=0x1000001,-22);BAD(wire.records++,-22);BAD(wire.channel=16,-22);BAD(wire.reserved[1]=1,-22);BAD(wire.destination=0x1d3ffff0,-22);BAD(wire.destination=0x10923fff,-22);BAD(wire.destination=0xffffffff,-22);BAD(wire.source=(1UL<<39)-1,-5);BAD(wire.source_bytes--,-5);BAD(source[0]=0,-5);source[0]=0xf0;
 wire=good;copy_fail=1;assert(ioctl103(&f,&c)==-5);copy_fail=0;alloc_fail=1;assert(ioctl103(&f,&c)==-5);alloc_fail=0;c.command=2;assert(ioctl103(&f,&c)==-22);c.command=1;token=0;assert(open103(&f)==-22&&ioctl103(&f,&c)==-22);token=(void*)&magic103;
 for(U j=0;j<sizeof(target);j++)assert(target[j]==0xa5);assert(close103(&f)==0);cleanup_module();assert(!registered_test);puts("AP103_HOST_ABI_BOUNDS_COPY_FAILURE_NO_PARTIAL_OUTPUT_ASAN_UBSAN_PASS");}
