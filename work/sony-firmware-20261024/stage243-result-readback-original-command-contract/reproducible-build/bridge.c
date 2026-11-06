/* Own NOOP bridge capsule: runtime plan -> anonymous copy -> private child.
 * Not Sony's constructor, a live transport, authorization or a backup reader. */
#include "bridge_job.h"
typedef unsigned char u8;typedef unsigned int u32;typedef unsigned long u64;
extern const u8 __capsule_base[] __attribute__((visibility("hidden")));
static volatile u32 bridge_state,entered;
static long sc(long n,long a,long b,long c,long d,long e,long f){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static int equal(const u8 *a,const u8 *b,u32 n){u8 v=0;for(u32 i=0;i<n;i++)v|=a[i]^b[i];return !v;}
#include "sha_impl.inc"
static int nonzero(const u8 *p,u32 n){u8 v=0;for(u32 i=0;i<n;i++)v|=p[i];return v!=0;}
static int close1(long *fd){long v=*fd;*fd=-1;return v<0||sc(57,v,0,0,0,0,0)==0;}
static int tick(u64 *out){long t[2]={0};if(sc(113,1,(long)t,0,0,0,0)||t[0]<0||t[1]<0||t[1]>=1000000000L)return 0;*out=(u64)t[0]*1000000000ULL+(u64)t[1];return 1;}
enum {PAGE=65536,IMAGE=262144};
static int image_shape(const u8 *base){
 if(bj_g32(base)!=0x464c457fu||base[4]!=2||base[5]!=1||bj_g32(base+16)!=0x00b70003u||bj_g32(base+20)!=1||bj_g64(base+32)!=64||base[54]!=56||base[55]||base[56]!=6||base[57])return 0;
 for(u32 i=0;i<4;i++){const u8 *p=base+64+56*i;u32 flags=i==1?5u:i==3?6u:4u;if(bj_g32(p)!=1||bj_g32(p+4)!=flags||bj_g64(p+8)!=(u64)i*PAGE||bj_g64(p+16)!=(u64)i*PAGE||bj_g64(p+40)!=PAGE||bj_g64(p+32)!=PAGE)return 0;}
 const u8 *p=base+64+56*4;
 if(bj_g32(p)!=2||bj_g32(p+4)!=6||bj_g64(p+8)!=3*PAGE||bj_g64(p+16)!=3*PAGE||bj_g64(p+32)!=112||bj_g64(p+40)!=112)return 0;
 p=base+64+56*5;return bj_g32(p)==0x6474e551u&&bj_g32(p+4)==6;
}
static int image_hash(const u8 *base,u8 out[32]){
 if(!image_shape(base))return 0;struct sha s;sha_init(&s);sha_update(&s,base,3*PAGE);u8 z[64]={0};for(u32 i=0;i<PAGE/64;i++)sha_update(&s,z,64);sha_final(&s,out);return 1;
 /* The fourth file page is zero padding/BSS, not an authorization field.
  * Mutable runtime globals are excluded by representing that page as zero. */
}
__attribute__((visibility("hidden"))) int fx3_bridge_image_id(u8 out[32]){return image_hash(__capsule_base,out);}
static int validate(struct bridge_job *j,const u8 input[256]){
 bj_copy(j->plan,input,256);const u8 magic[16]="FX3ENTRYPLANv2";u8 *p=j->plan;
 if(!equal(p,magic,16)||bj_g32(p+16)!=2||bj_g32(p+20)!=1||bj_g32(p+24)!=1||bj_g32(p+28)||bj_g32(p+160)!=1||bj_g32(p+252)!=bj_crc(p,252)||!nonzero(p+32,16)||!nonzero(p+48,32)||!nonzero(p+80,32)||!nonzero(p+164,32)||bj_g64(p+196)!=262144)return 0;
 for(u32 i=204;i<252;i++){if(p[i])return 0;}
 j->issued=bj_g64(p+144);j->expires=bj_g64(p+152);u64 t=0;
 if(j->expires<=j->issued||j->expires-j->issued>900000000000ULL||!tick(&t)||t<j->issued||t>=j->expires||!image_hash(__capsule_base,j->image_sha)||!equal(j->image_sha,p+112,32))return 0;
 hash(p,256,j->plan_sha);return 1;
}
static void die(long code){sc(93,code,0,0,0,0,0);for(;;){}}
static long copied_spawn(const struct bridge_job *j,long channel){
 /* Low byte17 only: independent VM/files/sighand/thread group, normal
  * SIGCHLD reaping for this outer child. The inner worker remains clone0. */
 long child=sc(220,17,0,0,0,0,0);
 if(!child){int r=fx3_isolated_collector_core(channel,j);die(r==10?42:r);}return child;
}
static long copied_entry(long *raw_out,const u8 wanted[32]){
 const u8 *source=__capsule_base;long raw=sc(222,0,5*PAGE,3,0x22,-1,0);if(raw<0)return 0;*raw_out=raw;
 u64 aligned=((u64)raw+PAGE-1)&~(u64)(PAGE-1);if(aligned<(u64)raw||aligned+IMAGE>(u64)raw+5*PAGE)return 0;
 if(aligned<(u64)source+IMAGE&&(u64)source<aligned+IMAGE)return 0;
 u8 *base=(u8 *)aligned;bj_copy(base,source,IMAGE);u8 b[32];if(!image_hash(base,b)||!equal(wanted,b,32))return 0;
 if(sc(226,raw,5*PAGE,0,0,0,0))return 0;
 for(u32 i=0;i<4;i++){long prot=i==1?5:i==3?3:1;if(sc(226,(long)(base+i*PAGE),PAGE,prot,0,0,0))return 0;}
 u64 offset=(u64)(long)&copied_spawn-(u64)source;if(offset<PAGE||offset>=2*PAGE)return 0;return (long)(base+offset);
}
__attribute__((visibility("hidden"))) int fx3_bridge_start(const u8 *plan,u64 bytes){
 bridge_state=4;if(entered||!plan||bytes!=256)return 4;entered=1;
 struct bridge_job job;int result=2,mask_set=0,handoff[2]={0,0};long mapping=-1,left=-1,right=-1;int pair[2]={-1,-1};u64 block=~((1ULL<<8)|(1ULL<<18));
 job.parent_pid=(u64)sc(172,0,0,0,0,0,0);job.parent_tid=(u64)sc(178,0,0,0,0,0,0);job.old_mask=0;
 if(job.parent_pid<=1||job.parent_pid>2147483647UL||job.parent_tid<=1||job.parent_tid>2147483647UL||sc(174,0,0,0,0,0,0)||sc(175,0,0,0,0,0,0)||!validate(&job,plan))return 4;
 bridge_state=2;long entry=copied_entry(&mapping,job.image_sha);if(!entry)goto end;
 {u64 t=0;if(!tick(&t)||t<job.issued||t>=job.expires)goto end;}
 if(sc(135,2,(long)&block,(long)&job.old_mask,8,0,0))goto end;mask_set=1;
 if(sc(199,1,0x80002,0,(long)pair,0,0))goto end;left=pair[0];right=pair[1];u32 pass=1;
 if(sc(208,left,1,16,(long)&pass,4,0)||sc(208,right,1,16,(long)&pass,4,0))goto end;
 {u64 t=0;if(!tick(&t)||t<job.issued||t>=job.expires)goto end;}
 long child=((long (*)(const struct bridge_job *,long))entry)(&job,right);
 if(!close1(&right))goto end;
 if(child<=1||child>2147483647L)goto end;
 result=fx3_parent_receiver(left,(u32)child,&job,handoff);if(handoff[1])left=-1;
end:
 {int r=close1(&right),l=close1(&left);if(!r||!l)result=2;}
 if(mapping>=0&&sc(215,mapping,5*PAGE,0,0,0,0))result=2;
 if(mask_set&&handoff[0]==0){if(sc(135,2,(long)&job.old_mask,0,8,0,0))result=2;}else if(handoff[0]<0)result=2;
 bridge_state=(u32)result;return result;
}
