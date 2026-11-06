/* Own Linux AArch64 boot-region read candidate, source/build only.
 * Main-p3 reference file profile; updater marker is rejected. No upload,
 * constructor, auth, partition write, reset, cleanup deletion or retry API.
 * Kernel open/read may select eMMC access and panic: see stage214 evidence.
 */
typedef unsigned long long u64;
typedef unsigned int u32;
typedef unsigned char u8;
_Static_assert(sizeof(long)==8 && sizeof(u64)==8,"64-bit ABI");
#ifdef FX3_BOOT_HOST_FIXTURE
extern long fx3_boot_test_syscall(long,long,long,long,long);
#define sc fx3_boot_test_syscall
#else
#if !defined(__aarch64__)
#error "Linux AArch64 target required"
#endif
static long sc(long nr,long a,long b,long c,long d) {
    register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x8 __asm__("x8")=nr;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x8):"memory","cc");return x0;
}
#endif
enum { BLOCK=65536,UNIT=131072,MAX_TOTAL=255*UNIT,WINDOW=128,
       RD=0xa0000,DIR=0xb0000,NEW=0xa00c1,AT_FDCWD=-100 };
enum { OK=0,REPLAY=10,NOT_ROOT,RAM_INVALID,REQUEST_INVALID,PROFILE_INVALID,
       PARTITIONS_INVALID,SOURCE_INVALID,SIZE_INVALID,OUTPUT_INVALID,
       CLOCK_INVALID,READ_INVALID,WRITE_INVALID,CLOSE_UNKNOWN,DEADLINE };
struct kstat {
    u64 dev,ino;u32 mode,nlink,uid,gid;u64 rdev,pad1;
    long size;int blksize,pad2;long blocks,atime;u64 atime_ns;
    long mtime;u64 mtime_ns;long ctime;u64 ctime_ns;u32 pad3,pad4;
};
_Static_assert(sizeof(struct kstat)==128 && __builtin_offsetof(struct kstat,size)==48,"arm64 stat ABI");
static int used;
static u8 data[BLOCK+64],proc[8192],hashbuf[4096];
static const u8 req_magic[16]="FX3BOOTREQv1",chunk_magic[16]="FX3BOOTCHUNKv1",man_magic[16]="FX3BOOTMANv1";
static const char profile_hex[]="057dc79d9fe94348e2eb4cc7135db1824c8f97c65046dffe307b3b8568ce72c6";
static const char file_hashes[3][65]={
    "14d17ea8065e3bc751a699dc644f00d247225640175d2957fb2a44bea39e5e4d",
    "521589c8eac8b851f1cab29f95f449c7bbaf31639a01331d3bf0ca8866b488b8",
    "cca1d9acd87a718c7742d168ea0de402b01a7c04cd40433ff2ca4071150dbc23"};
static const u32 file_sizes[3]={341024,14592,6344};
static void zero(u8 *p,u32 n){for(u32 i=0;i<n;++i)p[i]=0;}
static void copy(u8 *p,const u8 *q,u32 n){for(u32 i=0;i<n;++i)p[i]=q[i];}
static int equal(const u8 *p,const u8 *q,u32 n){u8 v=0;for(u32 i=0;i<n;++i)v|=p[i]^q[i];return !v;}
static u32 get32(const u8 *p){return p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static u64 get64(const u8 *p){return get32(p)|(u64)get32(p+4)<<32;}
static void put32(u8 *p,u32 v){for(u32 i=0;i<4;++i)p[i]=(u8)(v>>(8*i));}
static void put64(u8 *p,u64 v){put32(p,(u32)v);put32(p+4,(u32)(v>>32));}
static u32 crc(u32 c,const u8 *p,u32 n){for(u32 i=0;i<n;++i){c^=p[i];for(u32 b=0;b<8;++b)c=(c>>1)^(0xedb88320u&(0u-(c&1)));}return c;}
static int hex_matches(const u8 *p,const char *s){const char *h="0123456789abcdef";for(u32 i=0;i<32;++i)if(h[p[i]>>4]!=s[i*2]||h[p[i]&15]!=s[i*2+1])return 0;return 1;}
/* Own SHA-256 implementation; verified independently with hashlib in fixtures. */
struct sha {u32 state[8];u64 bytes;u32 count;u8 buf[64];};
static const u32 K[64]={
 0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
 0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
 0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
 0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
 0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
 0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
 0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
 0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
static u32 rr(u32 x,u32 n){return (x>>n)|(x<<(32-n));}
static void sha_block(struct sha *s,const u8 *p){
    u32 w[64];for(u32 i=0;i<16;++i)w[i]=(u32)p[4*i]<<24|(u32)p[4*i+1]<<16|(u32)p[4*i+2]<<8|p[4*i+3];
    for(u32 i=16;i<64;++i){u32 a=w[i-15],b=w[i-2];w[i]=w[i-16]+(rr(a,7)^rr(a,18)^(a>>3))+w[i-7]+(rr(b,17)^rr(b,19)^(b>>10));}
    u32 a=s->state[0],b=s->state[1],c=s->state[2],d=s->state[3],e=s->state[4],f=s->state[5],g=s->state[6],h=s->state[7];
    for(u32 i=0;i<64;++i){u32 t=h+(rr(e,6)^rr(e,11)^rr(e,25))+((e&f)^(~e&g))+K[i]+w[i];u32 v=(rr(a,2)^rr(a,13)^rr(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+v;}
    s->state[0]+=a;s->state[1]+=b;s->state[2]+=c;s->state[3]+=d;s->state[4]+=e;s->state[5]+=f;s->state[6]+=g;s->state[7]+=h;
}
static void sha_init(struct sha *s){
    const u32 v[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
    for(u32 i=0;i<8;++i)s->state[i]=v[i];s->bytes=0;s->count=0;
}
static void sha_update(struct sha *s,const u8 *p,u32 n){s->bytes+=n;for(u32 i=0;i<n;++i){s->buf[s->count++]=p[i];if(s->count==64){sha_block(s,s->buf);s->count=0;}}}
static void sha_final(struct sha *s,u8 out[32]){
    u64 bits=s->bytes*8;s->buf[s->count++]=0x80;
    if(s->count>56){while(s->count<64)s->buf[s->count++]=0;sha_block(s,s->buf);s->count=0;}
    while(s->count<56)s->buf[s->count++]=0;
    for(u32 i=0;i<8;++i)s->buf[56+i]=(u8)(bits>>(56-8*i));sha_block(s,s->buf);
    for(u32 i=0;i<8;++i)for(u32 j=0;j<4;++j)out[4*i+j]=(u8)(s->state[i]>>(24-8*j));
}
static void hash(const u8 *p,u32 n,u8 out[32]){struct sha s;sha_init(&s);sha_update(&s,p,n);sha_final(&s,out);}
static u32 major_(u64 d){return (u32)(((d>>8)&0xfff)|((d>>32)&0xfffff000));}
static u32 minor_(u64 d){return (u32)((d&255)|((d>>12)&0xffffff00));}
static int stat_(long fd,struct kstat *s){return sc(80,fd,(long)s,0,0)==0;}
static int stable(const struct kstat *a,const struct kstat *b){return a->dev==b->dev&&a->ino==b->ino&&a->mode==b->mode&&a->nlink==b->nlink&&a->uid==b->uid&&a->rdev==b->rdev&&a->size==b->size&&a->mtime==b->mtime&&a->mtime_ns==b->mtime_ns&&a->ctime==b->ctime&&a->ctime_ns==b->ctime_ns;}
static int ram(long fd,u64 need){u64 x[32];for(u32 i=0;i<32;++i)x[i]=0;if(sc(44,fd,(long)x,0,0)||x[0]!=0x01021994||(x[10]&1)||(x[4]>>63))return 0;u64 unit=x[9]?x[9]:x[1];return unit&&unit<=1048576&&x[4]>=(need+unit-1)/unit;}
static int tick(u64 *now){long ts[2]={0,0};if(sc(113,1,(long)ts,0,0)||ts[0]<0||ts[1]<0||ts[1]>=1000000000||(u64)ts[0]>18000000000ULL)return 0;u64 n=(u64)ts[0]*1000000000ULL+(u64)ts[1];if(!n||n<*now)return 0;*now=n;return 1;}
static int whitespace(u8 c){return c==' '||c=='\t'||c=='\r';}
static void skip(const u8 **p,const u8 *end){while(*p<end&&whitespace(**p))++*p;}
static int decimal(const u8 **p,const u8 *end,u64 *out){const u8 *a=*p;u64 v=0;while(*p<end&&**p>='0'&&**p<='9'){u32 n=**p-'0';if(v>(0xffffffffULL-n)/10)return 0;v=v*10+n;++*p;}*out=v;return *p>a;}
static int token(const u8 *p,const u8 *end,const char *s){while(*s&&p<end)if(*p++!=(u8)*s++)return 0;return !*s&&p==end;}
static int geometry(u64 size){return size>=UNIT&&size<=MAX_TOTAL&&size%UNIT==0;}
static int partitions(long n,u64 *total){
    u32 seen=0;u64 sizes[2]={0,0};const u8 *p=proc,*end=proc+n;
    while(p<end){const u8 *line=p;while(p<end&&*p!='\n')++p;if(p==end)return 0;const u8 *stop=p++;u64 ma=0,mi=0,kib=0;skip(&line,stop);
        if(!decimal(&line,stop,&ma))continue;
        if(line==stop||!whitespace(*line))return 0;skip(&line,stop);
        if(!decimal(&line,stop,&mi)||line==stop||!whitespace(*line))return 0;skip(&line,stop);
        if(!decimal(&line,stop,&kib)||line==stop||!whitespace(*line))return 0;skip(&line,stop);
        const u8 *name=line;while(line<stop&&!whitespace(*line))++line;
        int role=token(name,line,"nflashaB0")?1:token(name,line,"nflashaB1")?2:0;if(!role)continue;skip(&line,stop);
        if(line!=stop||(seen&(u32)role)||ma!=252||mi!=(u64)(125+role)||!geometry(kib*1024))return 0;
        seen|=(u32)role;sizes[role-1]=kib*1024;
    }
    *total=sizes[0];return seen==3&&sizes[0]==sizes[1];
}
static const char *profile_path(u32 i){return i==0?"/kmod/emmc.ko":i==1?"/kmod/crypt-emmc.ko":"/kmod/devno.ko";}
static int file_profile(void){
    long marker=sc(56,AT_FDCWD,(long)"/root/IAMUPDATER",RD,0);
    if(marker>=0){return sc(57,marker,0,0,0)?CLOSE_UNKNOWN:PROFILE_INVALID;}
    if(marker!=-2)return PROFILE_INVALID;
    for(u32 i=0;i<3;++i){
        long fd=sc(56,AT_FDCWD,(long)profile_path(i),RD,0);if(fd<0)return PROFILE_INVALID;
        struct kstat a,b;int result=PROFILE_INVALID;u8 out[32],extra=0;struct sha s;sha_init(&s);
        if(!stat_(fd,&a)||(a.mode&0170000)!=0100000||a.uid||a.nlink!=1||a.size!=file_sizes[i])goto close_profile;
        u32 left=file_sizes[i];while(left){u32 want=left>sizeof(hashbuf)?sizeof(hashbuf):left;long n=sc(63,fd,(long)hashbuf,want,0);if(n!=(long)want)goto close_profile;sha_update(&s,hashbuf,want);left-=want;}
        sha_final(&s,out);
        if(sc(63,fd,(long)&extra,1,0)||!stat_(fd,&b)||!stable(&a,&b)||!hex_matches(out,file_hashes[i]))goto close_profile;
        result=OK;
close_profile:
        if(sc(57,fd,0,0,0))return CLOSE_UNKNOWN;if(result)return result;
    }
    return OK;
}
static int save(long dir,const char *name,const u8 *h,u32 hn,const u8 *p,u32 pn){long fd=sc(56,dir,(long)name,NEW,0600);if(fd<0)return WRITE_INVALID;int r=OK;if(sc(64,fd,(long)h,hn,0)!=(long)hn||(pn&&sc(64,fd,(long)p,pn,0)!=(long)pn)||sc(82,fd,0,0,0))r=WRITE_INVALID;if(sc(57,fd,0,0,0))r=CLOSE_UNKNOWN;return r;}

static int fx3_inner_boot_read_window(void){
    if(__atomic_exchange_n(&used,1,__ATOMIC_ACQ_REL))return REPLAY;
    if(sc(175,0,0,0,0)!=0)return NOT_ROOT;
    long root=-1,request=-1,table=-1,source=-1,output=-1;int result=RAM_INVALID;
    u8 req[128],req_sha[32];struct kstat a,b,ss,ss2,ds;u64 total=0,sectors=0,now=0,deadline=0;
    root=sc(56,AT_FDCWD,(long)"/tmp_wbshd",DIR,0);if(root<0||!ram(root,2097152))goto done;
    result=REQUEST_INVALID;request=sc(56,root,(long)"fx3-boot-request-v1.bin",RD,0);
    if(request<0||!ram(request,0)||!stat_(request,&a)||(a.mode&0170000)!=0100000||(a.mode&07777)!=0600||a.uid||a.nlink!=1||a.size!=128||sc(63,request,(long)req,128,0)!=128||!stat_(request,&b)||!stable(&a,&b))goto done;
    if(sc(57,request,0,0,0)){request=-1;result=CLOSE_UNKNOWN;goto done;}request=-1;
    u8 present=0;for(u32 i=16;i<32;++i)present|=req[i];
    u32 target=get32(req+36),window=get32(req+40);u64 expected=get64(req+48);
    if(!equal(req,req_magic,16)||!present||get32(req+32)!=1||target>1||window>3||get32(req+44)!=BLOCK||!hex_matches(req+56,profile_hex)||get32(req+88)!=3||get32(req+92)!=252||get32(req+96)!=126+target||get32(req+100)!=1||get32(req+124)!=(crc(0xffffffffu,req,124)^0xffffffffu))goto done;
    for(u32 i=104;i<124;++i)if(req[i])goto done;
    if((!expected&&window)|| (expected&&!geometry(expected)))goto done;
    hash(req,128,req_sha);
    result=file_profile();if(result)goto done;
    result=PARTITIONS_INVALID;table=sc(56,AT_FDCWD,(long)"/proc/partitions",RD,0);if(table<0)goto done;
    long n=sc(63,table,(long)proc,sizeof(proc),0);u8 extra=0;
    if(n<=0||n>=(long)sizeof(proc)||sc(63,table,(long)&extra,1,0)!=0||!partitions(n,&total)||(expected&&expected!=total))goto done;
    if(sc(57,table,0,0,0)){table=-1;result=CLOSE_UNKNOWN;goto done;}table=-1;
    u32 chunks=(u32)(total/BLOCK),first=window*WINDOW;if(first>=chunks){result=REQUEST_INVALID;goto done;}
    u32 count=chunks-first;if(count>WINDOW)count=WINDOW;
    result=RAM_INVALID;if(!ram(root,(u64)count*(BLOCK+256)+2097152))goto done;
    result=SOURCE_INVALID;source=sc(56,AT_FDCWD,(long)(target?"/dev/nflashaB1":"/dev/nflashaB0"),RD,0);
    if(source<0||!stat_(source,&ss)||(ss.mode&0170000)!=0060000||ss.uid||ss.nlink!=1||major_(ss.rdev)!=252||minor_(ss.rdev)!=126+target)goto done;
    result=SIZE_INVALID;if(sc(29,source,0x1260,(long)&sectors,0)||sectors!=total/512)goto done;
    result=CLOCK_INVALID;if(!tick(&now))goto done;deadline=now+60000000000ULL;
    char name[80];const char *prefix="fx3-boot-";u32 at=0;while(prefix[at]){name[at]=prefix[at];++at;}const char *hex="0123456789abcdef";
    for(u32 i=16;i<32;++i){name[at++]=hex[req[i]>>4];name[at++]=hex[req[i]&15];}
    name[at++]='-';name[at++]='b';name[at++]=(char)('0'+target);name[at++]='-';name[at++]='w';name[at++]=(char)('0'+window);name[at++]='-';name[at++]='v';name[at++]='1';name[at]=0;
    result=OUTPUT_INVALID;if(sc(34,root,(long)name,0700,0))goto done;
    output=sc(56,root,(long)name,DIR,0);if(output<0||!ram(output,0)||!stat_(output,&ds)||(ds.mode&0170000)!=0040000||(ds.mode&07777)!=0700||ds.uid)goto done;
    result=save(output,"request.bin",req,128,0,0);if(result)goto done;
    u32 full_crc=0xffffffffu;
    for(u32 local=0;local<count;++local){
        result=CLOCK_INVALID;if(!tick(&now))goto done;result=DEADLINE;if(now>=deadline)goto done;u64 call_deadline=now+5000000000ULL;
        result=SOURCE_INVALID;if(!stat_(source,&ss2)||!stable(&ss,&ss2))goto done;
        for(u32 i=0;i<32;++i){data[i]=0xc7;data[BLOCK+32+i]=0xc7;}
        u32 index=first+local;u64 offset=(u64)index*BLOCK;
        long actual=sc(67,source,(long)(data+32),BLOCK,(long)offset);
        result=CLOCK_INVALID;if(!tick(&now))goto done;result=DEADLINE;if(now>=deadline||now>=call_deadline)goto done;
        result=READ_INVALID;if(actual!=BLOCK)goto done;for(u32 i=0;i<32;++i)if(data[i]!=0xc7||data[BLOCK+32+i]!=0xc7)goto done;
        result=SOURCE_INVALID;if(!stat_(source,&ss2)||!stable(&ss,&ss2))goto done;
        u8 header[256];zero(header,sizeof(header));copy(header,chunk_magic,16);put32(header+16,1);put32(header+20,target);put32(header+24,window);put32(header+28,index);
        put64(header+32,total);put64(header+40,offset);put32(header+48,BLOCK);put32(header+52,BLOCK);put32(header+56,crc(0xffffffffu,data+32,BLOCK)^0xffffffffu);
        put32(header+60,252);put32(header+64,126+target);put32(header+68,3);copy(header+72,req+16,16);copy(header+88,(const u8 *)(target?"nflashaB1":"nflashaB0"),9);copy(header+104,req+56,32);copy(header+136,req_sha,32);
        char file[]="chunk-000.bin";file[6]=(char)('0'+local/100);file[7]=(char)('0'+local/10%10);file[8]=(char)('0'+local%10);
        result=save(output,file,header,256,data+32,BLOCK);if(result)goto done;full_crc=crc(full_crc,data+32,BLOCK);
    }
    result=SIZE_INVALID;sectors=0;if(sc(29,source,0x1260,(long)&sectors,0)||sectors!=total/512)goto done;
    result=SOURCE_INVALID;if(!stat_(source,&ss2)||!stable(&ss,&ss2))goto done;result=CLOCK_INVALID;if(!tick(&now))goto done;result=DEADLINE;if(now>=deadline)goto done;
    if(sc(57,source,0,0,0)){source=-1;result=CLOSE_UNKNOWN;goto done;}source=-1;
    u8 manifest[256];zero(manifest,sizeof(manifest));copy(manifest,man_magic,16);put32(manifest+16,1);put32(manifest+20,target);put32(manifest+24,window);put32(manifest+28,first);put32(manifest+32,count);put32(manifest+36,BLOCK);
    put64(manifest+40,total);put64(manifest+48,(u64)first*BLOCK);put32(manifest+56,full_crc^0xffffffffu);put32(manifest+60,252);put32(manifest+64,126+target);put32(manifest+68,255);
    copy(manifest+72,req+16,16);copy(manifest+88,(const u8 *)(target?"nflashaB1":"nflashaB0"),9);copy(manifest+104,req+56,32);copy(manifest+136,req_sha,32);
    put32(manifest+168,get32(req+124));put32(manifest+172,(chunks+WINDOW-1)/WINDOW);put32(manifest+176,1);put32(manifest+180,3);
    result=save(output,"manifest.bin",manifest,256,0,0);if(result)goto done;result=sc(82,output,0,0,0)?WRITE_INVALID:OK;
done:
    if(source>=0&&sc(57,source,0,0,0))result=CLOSE_UNKNOWN;
    if(table>=0&&sc(57,table,0,0,0))result=CLOSE_UNKNOWN;
    if(request>=0&&sc(57,request,0,0,0))result=CLOSE_UNKNOWN;
    if(output>=0&&sc(57,output,0,0,0))result=CLOSE_UNKNOWN;
    if(root>=0&&sc(57,root,0,0,0))result=CLOSE_UNKNOWN;
    return result;
}
#ifdef FX3_BOOT_HOST_FIXTURE
__attribute__((visibility("default"))) void fx3_boot_fixture_reset(void){used=0;}
__attribute__((visibility("default"))) void fx3_boot_fixture_hash(const u8 *p,u32 n,u8 out[32]){hash(p,n,out);}
#endif
