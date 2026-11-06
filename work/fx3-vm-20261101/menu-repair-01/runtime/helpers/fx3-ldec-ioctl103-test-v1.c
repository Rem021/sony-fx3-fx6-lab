/* Original ioctl1 round-trip against independent corpus fixtures, guest only.
 * All writes target the separate1MiB AP103 FDT reservation before AP startup. */
typedef unsigned long U;typedef unsigned int W;typedef unsigned char B;
extern int open(const char*,int,...),close(int),ioctl(int,U,...),dprintf(int,const char*,...),munmap(void*,U),memcmp(const void*,const void*,U);
extern long read(int,void*,U),lseek(int,long,int);extern void*mmap(void*,U,int,int,int,long),*malloc(U),*memset(void*,int,U);extern void free(void*);extern int*__errno_location(void);
struct req {U source;W n,p32,output,records,channel;B bypass[2],reserved[2];};
_Static_assert(sizeof(struct req)==32,"original32B ioctl");
static long load(const char*p,B**out){int f=open(p,0);if(f<0)return -1;long n=lseek(f,0,2);if(n<=0||n>1048576||lseek(f,0,0)){close(f);return -2;}B*b=malloc(n);if(!b){close(f);return -3;}U at=0;while(at<(U)n){long z=read(f,b+at,n-at);if(z<=0){free(b);close(f);return -4;}at+=z;}close(f);*out=b;return n;}
static U hash(const B*p,U n){U h=0xcbf29ce484222325UL;for(U i=0;i<n;i++){h^=p[i];h*=0x100000001b3UL;}return h;}
static int guard(B*p){for(U j=0;j<1048576;j++)if(p[j]!=0xa5)return 0;return 1;}
int main(void){const char*names[]={"nine-patch-01-1355","panel-02-1228","icon-00-0"};const char*srcs[]={"/simulation/ldec103/nine-patch-01-1355.ldec","/simulation/ldec103/panel-02-1228.ldec","/simulation/ldec103/icon-00-0.ldec"};const char*refs[]={"/simulation/ldec103/nine-patch-01-1355.raw","/simulation/ldec103/panel-02-1228.raw","/simulation/ldec103/icon-00-0.raw"};
 int m=open("/dev/mem",2),f=open("/dev/ldec",2);if(m<0||f<0)return 1;B*target=mmap(0,1048576,3,1,m,0x41d300000UL);close(m);if(target==(void*)-1)return 2;
 for(int i=0;i<3;i++){B*src=0,*ref=0;long n=load(srcs[i],&src),out=load(refs[i],&ref);if(n<=0||out<=0)return 3;struct req r={(U)src,n,0x1d300000,out,(out+4095)/4096,8,{0,1},{0,0}};memset(target,0xa5,1048576);int rc=ioctl(f,1,&r);if(rc||memcmp(target,ref,out))return 4;for(U j=out;j<1048576;j++)if(target[j]!=0xa5)return 5;dprintf(1,"FX3_LDEC103_GUEST_EXACT sample=%s compressed=%ld output=%ld result=0 byte_equal=1 output_fnv=%#lx guard_equal=1\n",names[i],n,out,hash(target,out));
  struct req good=r;memset(target,0xa5,1048576);
#define BAD(mutation) do{r=good;mutation;int z=ioctl(f,1,&r);if(z!=-1||!guard(target))return 6;dprintf(1,"FX3_LDEC103_GUEST_REJECT case=%s errno=%d output_unchanged=1\n",#mutation,*__errno_location());}while(0)
  BAD(r.n=0);BAD(r.output++);BAD(r.records++);BAD(r.channel=16);BAD(r.p32=0x1d3ffff0);BAD(r.p32=0x10923fff);BAD(r.source=(1UL<<39)-1);BAD(r.n--);
  r=good;int z=ioctl(f,2,&r);if(z!=-1||!guard(target))return 7;free(src);free(ref);
 }
 close(f);munmap(target,1048576);dprintf(1,"FX3_LDEC103_GUEST_IOCTL_SELFTEST_PASS three_samples=1 exact32B=1 invalid_lengths_OOB_rejected=1 no_partial_output=1 test_reservation_only=1\n");return 0;
}
