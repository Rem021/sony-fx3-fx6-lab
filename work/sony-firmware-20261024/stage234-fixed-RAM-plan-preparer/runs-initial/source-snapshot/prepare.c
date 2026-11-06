/* Own fixed RAM-plan preparation component, no worker/source/USB backend.
 * Embedded associations and normalized-image checks are NOT authorization
 * or live-body attestation. This build is an offline synthetic candidate. */
#include "core_support.inc"
#include "parent_ipc.inc"
extern const u8 __fx3_elf_base[] __attribute__((visibility("hidden")));
static int state,reason;
static const char im_sha[]="5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91";
static const char worker_sha[]="c711f6ab13666c45249cc255d2ab09ec283496214d8941d11b9f1569124c47ec";
static int error(int code){state=2;reason=code;return 0;}
static int nonzero(const u8 *p,u32 n){u8 v=0;for(u32 i=0;i<n;++i)v|=p[i];return v!=0;}
static int regular(const struct kstat *s,u32 mode){return (s->mode&0170000)==0100000&&!s->uid&&s->nlink==1&&(s->mode&07777)==mode;}
static void finish_crc(u8 *p){put32(p+252,crc(0xffffffffu,p,252)^0xffffffffu);}
static int config_valid(void){
 const u8 *p=__fx3_elf_base+4096;static const u8 magic[16]="FX3PREPCONFIGv1";
 if(!equal(p,magic,16)||get32(p+16)!=1||get32(p+20)!=1||get32(p+24)!=1||get32(p+28)!=1||!nonzero(p+32,16)||!nonzero(p+48,32)||!nonzero(p+80,32)||!hex_matches(p+112,worker_sha)||get64(p+152)!=131864||get32(p+160)!=1)return 0;
 if(!get64(p+144)||get64(p+144)>900000000000ULL||get32(p+252)!=(crc(0xffffffffu,p,252)^0xffffffffu))return 0;
 for(u32 i=164;i<252;++i)if(p[i])return 0;return nonzero(__fx3_elf_base+4352,32);
}
static int parent_identity(void){
 long pid=sc(172,0,0,0,0),tid=sc(178,0,0,0,0);if(pid<=1||pid>2147483647L||tid<=1||tid>2147483647L||sc(174,0,0,0,0)||sc(175,0,0,0,0))return 0;
 long fd=sc(56,AT_FDCWD,(long)"/proc/self/exe",0x80000,0);if(fd<0)return 0;struct kstat a,z;struct sha s;u8 buf[4096],out[32],extra=0;int ok=0;
 if(!stat_(fd,&a)||(a.mode&0170000)!=0100000||a.uid||a.nlink!=1||a.size!=40920)goto end;
 sha_init(&s);for(u32 left=40920;left;){u32 n=left>4096?4096:left;if(sc(63,fd,(long)buf,n,0)!=(long)n)goto end;sha_update(&s,buf,n);left-=n;}
 sha_final(&s,out);if(sc(63,fd,(long)&extra,1,0)||!hex_matches(out,im_sha)||!stat_(fd,&z)||!stable(&a,&z))goto end;ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int image_profile(u8 full_sha[32]){
 const u8 *base=__fx3_elf_base;long fd=sc(56,AT_FDCWD,(long)"/tmp/jiritsu/libJit.so",RD,0);if(fd<0)return 0;
 struct kstat a,z;struct sha full,norm;u8 buf[4096],out[32],extra=0;int ok=0;
 if(!stat_(fd,&a)||(a.mode&0170000)!=0100000||a.uid||a.nlink!=1||a.size<32768||a.size>262144)goto end;
 if(get32(base)!=0x464c457f||get64(base+32)!=64||base[54]!=56||base[55]||base[56]!=8||base[57])goto end;
 sha_init(&full);sha_init(&norm);
 for(u32 at=0;at<(u32)a.size;){u32 n=(u32)a.size-at;if(n>4096)n=4096;if(sc(63,fd,(long)buf,n,0)!=(long)n)goto end;sha_update(&full,buf,n);
  for(u32 i=0;i<3;++i){const u8 *p=base+64+56*i;u64 off=get64(p+8),va=get64(p+16),size=get64(p+32);u32 flags=get32(p+4);
   if(get32(p)!=1||flags!=(i==1?5u:4u)||off!=(u64)i*32768||va!=off||!size||size>32768)goto end;
   for(u32 j=0;j<n;++j)if((u64)at+j>=off&&(u64)at+j<off+size&&buf[j]!=base[va+(u64)at+j-off])goto end;
  }
  for(u32 j=0;j<n;++j)if(at+j>=4352&&at+j<4384)buf[j]=0;
  sha_update(&norm,buf,n);at+=n;
 }
 sha_final(&full,full_sha);sha_final(&norm,out);if(!equal(out,base+4352,32)||sc(63,fd,(long)&extra,1,0)||!stat_(fd,&z)||!stable(&a,&z))goto end;ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int store(long directory,const char *name,const u8 data[256],struct kstat *saved){
 long fd=sc(56,directory,(long)name,(NEW&~3)|2,0600);if(fd<0)return 0;struct kstat a,z;u8 got[256],extra=0;int ok=0;
 if(!ram(fd,0)||!stat_(fd,&a)||!regular(&a,0600)||a.size)goto end;
 if(sc(64,fd,(long)data,256,0)!=256||sc(82,fd,0,0,0)||!stat_(fd,&a)||!regular(&a,0600)||a.size!=256)goto end;
 if(sc(62,fd,0,0,0)!=0||sc(63,fd,(long)got,256,0)!=256||sc(63,fd,(long)&extra,1,0)||!equal(got,data,256)||!stat_(fd,&z)||!stable(&a,&z))goto end;if(saved)copy((u8 *)saved,(u8 *)&z,sizeof(z));ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
static int verify_plan(long root,const u8 plan[256],const struct kstat *saved){
 long fd=sc(56,root,(long)"fx3-entry-plan-v1.bin",RD,0);if(fd<0)return 0;struct kstat a,z;u8 got[256],extra=0;int ok=0;
 if(!ram(fd,0)||!stat_(fd,&a)||!regular(&a,0600)||a.size!=256||a.dev!=saved->dev||a.ino!=saved->ino)goto end;
 if(sc(63,fd,(long)got,256,0)!=256||sc(63,fd,(long)&extra,1,0)||!equal(got,plan,256)||!stat_(fd,&z)||!stable(&a,&z))goto end;ok=1;
end:if(sc(57,fd,0,0,0))ok=0;return ok;
}
__attribute__((constructor)) static void fx3_module_init(void){
 state=4;reason=0;long root=-1,claim=-1;struct kstat s,pending;u8 own_sha[32],plan[256],report[256];u64 begun=0,now=0;
 if(!parent_identity()||!config_valid()||!image_profile(own_sha))return;
 root=sc(56,AT_FDCWD,(long)"/tmp_wbshd",DIR,0);
 if(root<0||!ram(root,65536)||!stat_(root,&s)||(s.mode&0170000)!=0040000||s.uid||((s.mode&022)&&!(s.mode&01000))){error(10);goto end;}
 if(sc(34,root,(long)"fx3-plan-preparation-v1",0700,0)){error(11);goto end;}
 claim=sc(56,root,(long)"fx3-plan-preparation-v1",DIR,0);
 if(claim<0||!ram(claim,0)||!stat_(claim,&s)||(s.mode&0170000)!=0040000||s.uid||(s.mode&07777)!=0700){error(12);goto end;}
 if(!tick(&begun)){error(13);goto end;}
 const u8 *cfg=__fx3_elf_base+4096;u64 ttl=get64(cfg+144);if(begun>~0ULL-ttl){error(13);goto end;}
 zero(plan,256);copy(plan,(const u8 *)"FX3ENTRYPLANv1",14);put32(plan+16,1);put32(plan+20,1);put32(plan+24,1);copy(plan+32,cfg+32,112);put64(plan+144,begun);put64(plan+152,begun+ttl);put32(plan+160,1);finish_crc(plan);
 if(!store(claim,"plan.pending",plan,&pending)){error(14);goto end;}
 /* STAGED receipt is written BEFORE publish. It is never a release/cleanup,
  * camera identity, execution approval, worker completion or USB receipt. */
 zero(report,256);copy(report,(const u8 *)"FX3PREPSTAGED1",14);put32(report+16,1);put32(report+20,1);put32(report+24,(u32)sc(172,0,0,0,0));put32(report+28,(u32)sc(178,0,0,0,0));copy(report+32,cfg+32,16);copy(report+48,own_sha,32);hash(plan,256,report+80);copy(report+112,cfg+112,32);put64(report+144,begun);put64(report+152,begun+ttl);hash(cfg,256,report+160);put32(report+192,1);put64(report+200,pending.dev);put64(report+208,pending.ino);finish_crc(report);
 if(!store(claim,"prepare.staged",report,0)){error(15);goto end;}
 now=begun;if(!tick(&now)||now>=begun+ttl){error(16);goto end;}
 /* renameat2 RENAME_NOREPLACE, never plain rename or overwrite fallback. */
 if(ipc_sc(276,claim,(long)"plan.pending",root,(long)"fx3-entry-plan-v1.bin",1,0)){error(17);goto end;}
 if(!verify_plan(root,plan,&pending)){error(18);goto end;}state=1;
end:
 if(claim>=0&&sc(57,claim,0,0,0))error(19);
 if(root>=0&&sc(57,root,0,0,0))error(20);
 /* Keep claims, partial staging and any published plan on error. No unlink,
  * chmod, retry, child launch, device access or replacement is permitted. */
}
__attribute__((visibility("default"))) int fx3_prepare_state(void){return state;}
__attribute__((visibility("default"))) int fx3_prepare_reason(void){return reason;}
