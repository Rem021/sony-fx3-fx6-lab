/* AP89 bounded guest RAM input. Never opens the original seed for writing. */
typedef unsigned char B;typedef unsigned int W;typedef unsigned long U;
extern int open(const char*,int,...),close(int),printf(const char*,...);extern long read(int,void*,U),lseek(int,long,int);extern void*malloc(U);extern void free(void*);extern void*memcpy(void*,const void*,U);extern int memcmp(const void*,const void*,U);extern void*memset(void*,int,U);extern void*mmap(void*,U,int,int,int,long);extern int munmap(void*,U);
#define REPLAY_BYTES 0x221000UL
#define REPLAY_PHYS 0x404000000UL
static const char expected[]="191924ef39d996171ae06ab4ca85e249b655b16db6b68fd1e2ddea45efc60bdc";
static W ror(W x,unsigned n){return x>>n|x<<(32-n);}static W be(const B*p){return(W)p[0]<<24|(W)p[1]<<16|(W)p[2]<<8|p[3];}
static void block(W*h,const B*p){static const W k[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};W w[64];for(unsigned i=0;i<16;i++)w[i]=be(p+4*i);for(unsigned i=16;i<64;i++){W a=w[i-15],b=w[i-2];w[i]=w[i-16]+(ror(a,7)^ror(a,18)^(a>>3))+w[i-7]+(ror(b,17)^ror(b,19)^(b>>10));}W a=h[0],b=h[1],c=h[2],d=h[3],e=h[4],f=h[5],g=h[6],z=h[7];for(unsigned i=0;i<64;i++){W t=z+(ror(e,6)^ror(e,11)^ror(e,25))+((e&f)^(~e&g))+k[i]+w[i],u=(ror(a,2)^ror(a,13)^ror(a,22))+((a&b)^(a&c)^(b&c));z=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+u;}h[0]+=a;h[1]+=b;h[2]+=c;h[3]+=d;h[4]+=e;h[5]+=f;h[6]+=g;h[7]+=z;}
static void digest(const B*p,U n,char out[65]){W h[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};U original=n;while(n>=64){block(h,p);p+=64;n-=64;}B tail[128]={0};for(U i=0;i<n;i++)tail[i]=p[i];tail[n]=128;U size=n<56?64:128,bits=original*8;for(unsigned i=0;i<8;i++)tail[size-1-i]=(B)(bits>>(i*8));block(h,tail);if(size==128)block(h,tail+64);const char*hex="0123456789abcdef";for(unsigned i=0;i<32;i++){B x=(B)(h[i/4]>>(24-8*(i%4)));out[2*i]=hex[x>>4];out[2*i+1]=hex[x&15];}out[64]=0;}
static W le(const B*p){return(W)p[0]|(W)p[1]<<8|(W)p[2]<<16|(W)p[3]<<24;}
static int header(const B*p,W np,W start,W size){return le(p)==0x04000000&&le(p+4)==0xaaaaaaaa&&le(p+12)==0x00344b42&&le(p+16)==819&&le(p+20)==np&&le(p+24)==start&&le(p+28)==size;}
static int replay(void){int result=1,fd=-1,physical=-1,written=0;B*source=0,*previous=0,*target=(void*)-1;char hash[65];
 fd=open("/simulation/ap89-backup-ram.bin",0);if(fd<0||lseek(fd,0,2)!=(long)REPLAY_BYTES||lseek(fd,0,0))goto done;
 source=malloc(REPLAY_BYTES);previous=malloc(REPLAY_BYTES);if(!source||!previous)goto done;
 for(U got=0;got<REPLAY_BYTES;){long z=read(fd,source+got,REPLAY_BYTES-got);if(z<=0)goto done;got+=(U)z;}close(fd);fd=-1;digest(source,REPLAY_BYTES,hash);if(memcmp(hash,expected,65))goto done;
 printf("FX3_AP89_BACKUP_REPLAY_SOURCE sha256=%s bytes=%lu original_saved_RAM=1\n",hash,REPLAY_BYTES);physical=open("/dev/mem",2);if(physical<0)goto done;
 target=mmap(0,REPLAY_BYTES,3,1,physical,REPLAY_PHYS);if(target==(void*)-1)goto done;
 if(!header(target,35668,219200,638700)||!header(target+0xd2000,31197,192384,1177196))goto done;
 memcpy(previous,target,REPLAY_BYTES);memcpy(target,source,REPLAY_BYTES);written=1;
#ifndef REPLAY_HOST_TEST
 __asm__ volatile("dmb sy":::"memory");
#endif
 munmap(target,REPLAY_BYTES);target=mmap(0,REPLAY_BYTES,1,1,physical,REPLAY_PHYS);if(target!=(void*)-1){digest(target,REPLAY_BYTES,hash);if(!memcmp(hash,expected,65)){printf("FX3_AP89_BACKUP_REPLAY_READBACK sha256=%s remapped_read_only=1 physical=%#lx bytes=%lu\n",hash,REPLAY_PHYS,REPLAY_BYTES);printf("FX3_AP89_BACKUP_REPLAY_VERIFIED raw_live_RAM=1 AP_not_started=1 original_seed_and_checksums_unchanged=1 no_disk_persistence_claim=1\n");result=0;}}
 done:if(result&&written){if(target!=(void*)-1){munmap(target,REPLAY_BYTES);target=(void*)-1;}target=mmap(0,REPLAY_BYTES,3,1,physical,REPLAY_PHYS);if(target!=(void*)-1){memcpy(target,previous,REPLAY_BYTES);printf("FX3_AP89_BACKUP_REPLAY_ROLLBACK verified=%d\n",!memcmp(target,previous,REPLAY_BYTES));}else printf("FX3_AP89_BACKUP_REPLAY_ROLLBACK verified=0 remap_failed=1\n");}
 if(target!=(void*)-1)munmap(target,REPLAY_BYTES);if(fd>=0)close(fd);if(physical>=0)close(physical);if(source)free(source);if(previous)free(previous);if(result)printf("FX3_AP89_REPLAY_FAILED no_AP_launch=1 result=%d\n",result);return result;}
#ifndef REPLAY_HOST_TEST
extern int __libc_start_main(int(*)(int,char**),int,char**,void(*)(void),void(*)(void),void(*)(void),void*);
__asm__(".global _start\n.type _start,%function\n_start:\nmov x0,sp\nbl entry\nbrk #0\n");
static int run(int argc,char**argv){(void)argv;return argc==1?replay():2;}
__attribute__((noreturn)) void entry(U*stack){__libc_start_main(run,(int)stack[0],(char**)(stack+1),0,0,0,stack);__builtin_trap();}
#endif
