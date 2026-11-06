/* FX3 fixed-target Linux AArch64 read-worker CANDIDATE.
 * Explicit entry only: no constructor, preload, loader, USB or source writes.
 * Freestanding relocatable object, NOT an executable/deployable camera module.
 * The host fixture replaces only the syscall boundary; no camera is used.
 */
typedef unsigned long uword;
typedef unsigned long long u64;
typedef unsigned int u32;
typedef unsigned char u8;
_Static_assert(sizeof(long)==8 && sizeof(u64)==8 && sizeof(u32)==4,"64-bit ABI required");
#ifdef FX3_P1_HOST_FIXTURE
extern long fx3_p1_test_syscall(long,long,long,long,long);
#define sc fx3_p1_test_syscall
#else
#if !defined(__aarch64__)
#error "production source is Linux AArch64 only"
#endif
static long sc(long nr,long a,long b,long c,long d) {
    register long x0 __asm__("x0")=a;
    register long x1 __asm__("x1")=b;
    register long x2 __asm__("x2")=c;
    register long x3 __asm__("x3")=d;
    register long x8 __asm__("x8")=nr;
    __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x8):"memory","cc");
    return x0;
}
#endif

enum { BLOCK=65536, TOTAL=25100288, CHUNKS=383, WINDOW=128,
       RD=0xa0000, DIR=0xb0000, NEW=0xa00c1, AT_FDCWD=-100 };
enum { OK=0, REPLAY=10, NOT_ROOT, RAM_INVALID, REQUEST_INVALID, PARTITIONS_INVALID,
       SOURCE_INVALID, SIZE_INVALID, OUTPUT_INVALID, CLOCK_INVALID, READ_INVALID,
       WRITE_INVALID, CLOSE_UNKNOWN, DEADLINE };
/* Linux arm64 asm-generic stat ABI; no host libc struct is used. */
struct kstat {
    u64 dev,ino; u32 mode,nlink,uid,gid; u64 rdev,pad1;
    long size; int blksize,pad2; long blocks,atime; u64 atime_ns;
    long mtime; u64 mtime_ns; long ctime; u64 ctime_ns; u32 pad3,pad4;
};
_Static_assert(sizeof(struct kstat)==128,"arm64 stat layout");
_Static_assert(__builtin_offsetof(struct kstat,size)==48,"stat size offset");
static int used;
static u8 data[BLOCK+64], proc[8192];
static const u8 req_magic[16]="FX3P1REQv1", chunk_magic[16]="FX3P1CHUNKv1", man_magic[16]="FX3P1MANv1";
static const u8 source_name[16]="cnflasha1";

static void zero(u8 *p,u32 n) {for(u32 i=0;i<n;++i)p[i]=0;}
static void copy(u8 *p,const u8 *q,u32 n) {for(u32 i=0;i<n;++i)p[i]=q[i];}
static int equal(const u8 *p,const u8 *q,u32 n) {u8 v=0;for(u32 i=0;i<n;++i)v|=p[i]^q[i];return !v;}
static u32 get32(const u8 *p) {return p[0]|(u32)p[1]<<8|(u32)p[2]<<16|(u32)p[3]<<24;}
static void put32(u8 *p,u32 n) {for(u32 i=0;i<4;++i)p[i]=(u8)(n>>(8*i));}
static void put64(u8 *p,u64 n) {put32(p,(u32)n);put32(p+4,(u32)(n>>32));}
static u32 crc(u32 c,const u8 *p,u32 n) {
    for(u32 i=0;i<n;++i){c^=p[i];for(u32 b=0;b<8;++b)c=(c>>1)^(0xedb88320u&(0u-(c&1u)));}
    return c;
}
static u32 major_(u64 d) {return (u32)(((d>>8)&0xfff)|((d>>32)&0xfffff000));}
static u32 minor_(u64 d) {return (u32)((d&0xff)|((d>>12)&0xffffff00));}
static int stat_(long fd,struct kstat *s) {return sc(80,fd,(long)s,0,0)==0;}
static int ram(long fd,u64 need) {
    u64 fields[32];for(u32 i=0;i<32;++i)fields[i]=0;
    if(sc(44,fd,(long)fields,0,0) || fields[0]!=0x01021994 || (fields[10]&1) || (fields[4]>>63))return 0;
    u64 unit=fields[9]?fields[9]:fields[1];
    return unit && unit<=1048576 && fields[4]>=(need+unit-1)/unit;
}
static int stable(const struct kstat *a,const struct kstat *b) {
    return a->dev==b->dev && a->ino==b->ino && a->mode==b->mode && a->nlink==b->nlink &&
           a->uid==b->uid && a->rdev==b->rdev && a->size==b->size && a->mtime==b->mtime &&
           a->mtime_ns==b->mtime_ns && a->ctime==b->ctime && a->ctime_ns==b->ctime_ns;
}
static int tick(u64 *now) {
    long ts[2]={0,0};
    if(sc(113,1,(long)ts,0,0) || ts[0]<0 || ts[1]<0 || ts[1]>=1000000000 ||
       (u64)ts[0]>18000000000ULL)return 0;
    u64 n=(u64)ts[0]*1000000000ULL+(u64)ts[1];
    if(!n || n<*now)return 0;
    *now=n;return 1;
}
static int whitespace(u8 c) {return c==' ' || c=='\t' || c=='\r';}
static void skip(const u8 **p,const u8 *end) {while(*p<end && whitespace(**p))++*p;}
static int decimal(const u8 **p,const u8 *end,u64 *out) {
    const u8 *start=*p;u64 v=0;
    while(*p<end && **p>='0' && **p<='9') {
        u32 n=(u32)(**p-'0');if(v>(0xffffffffULL-n)/10)return 0;v=v*10+n;++*p;
    }
    *out=v;return *p>start;
}
static int token(const u8 *p,const u8 *end,const char *s) {
    while(*s && p<end)if(*p++!=(u8)*s++)return 0;
    return !*s && p==end;
}
static int partitions(long n,u32 selected[4]) {
    u32 seen=0;const u8 *p=proc,*end=proc+n;
    while(p<end) {
        const u8 *line=p;while(p<end && *p!='\n')++p;if(p==end)return 0;
        const u8 *stop=p++;u64 ma=0,mi=0,kib=0;skip(&line,stop);
        if(!decimal(&line,stop,&ma))continue;
        if(line==stop || !whitespace(*line))return 0;skip(&line,stop);
        if(!decimal(&line,stop,&mi) || line==stop || !whitespace(*line))return 0;skip(&line,stop);
        if(!decimal(&line,stop,&kib) || line==stop || !whitespace(*line))return 0;skip(&line,stop);
        const u8 *name=line;while(line<stop && !whitespace(*line))++line;
        int which=token(name,line,"pnflasha1")?1:token(name,line,"cnflasha1")?2:0;
        if(!which)continue;skip(&line,stop);
        if(line!=stop || (seen&(u32)which) || !ma || kib!=TOTAL/1024)return 0;
        seen|=(u32)which;
        if(which==2){selected[0]=(u32)ma;selected[1]=(u32)mi;}
        else {selected[2]=(u32)ma;selected[3]=(u32)mi;}
    }
    return seen==3 && (selected[0]!=selected[2] || selected[1]!=selected[3]);
}
static int save(long directory,const char *name,const u8 *header,u32 hn,const u8 *body,u32 bn) {
    long fd=sc(56,directory,(long)name,NEW,0600);if(fd<0)return WRITE_INVALID;
    int result=OK;
    if(sc(64,fd,(long)header,hn,0)!=(long)hn || (bn && sc(64,fd,(long)body,bn,0)!=(long)bn) || sc(82,fd,0,0,0))result=WRITE_INVALID;
    if(sc(57,fd,0,0,0))result=CLOSE_UNKNOWN;
    return result;
}

__attribute__((visibility("default"))) int fx3_p1_read_window(void) {
    if(__atomic_exchange_n(&used,1,__ATOMIC_ACQ_REL))return REPLAY;
    if(sc(175,0,0,0,0)!=0)return NOT_ROOT;
    long root=-1,request=-1,table=-1,source=-1,output=-1;int result=RAM_INVALID;
    u8 req[64];struct kstat rs,rs2,ss,ss2,ds;u32 selected[4]={0,0,0,0};u64 now=0,deadline=0,sectors=0;
    root=sc(56,AT_FDCWD,(long)"/tmp_wbshd",DIR,0);
    if(root<0 || !ram(root,2*1024*1024))goto done;
    result=REQUEST_INVALID;
    request=sc(56,root,(long)"fx3-p1-request-v1.bin",RD,0);
    if(request<0 || !ram(request,0) || !stat_(request,&rs) || (rs.mode&0170000)!=0100000 ||
       (rs.mode&07777)!=0600 || rs.uid || rs.nlink!=1 || rs.size!=64 ||
       sc(63,request,(long)req,64,0)!=64 || !stat_(request,&rs2) || !stable(&rs,&rs2))goto done;
    if(sc(57,request,0,0,0)){request=-1;result=CLOSE_UNKNOWN;goto done;}request=-1;
    u8 present=0;for(u32 i=16;i<32;++i)present|=req[i];
    u32 window=get32(req+36),first=window*WINDOW,count=window==2?127:128;
    if(!equal(req,req_magic,16) || !present || get32(req+32)!=1 || window>2 ||
       get32(req+40)!=first || get32(req+44)!=count || get32(req+48)!=BLOCK ||
       get32(req+52)!=(crc(0xffffffffu,req,52)^0xffffffffu) || get32(req+56) || get32(req+60))goto done;
    result=RAM_INVALID;if(!ram(root,(u64)count*(BLOCK+128)+2097152))goto done;
    result=PARTITIONS_INVALID;table=sc(56,AT_FDCWD,(long)"/proc/partitions",RD,0);
    if(table<0)goto done;
    long n=sc(63,table,(long)proc,sizeof(proc),0);u8 extra=0;
    if(n<=0 || n>=(long)sizeof(proc) || sc(63,table,(long)&extra,1,0)!=0 || !partitions(n,selected))goto done;
    if(sc(57,table,0,0,0)){table=-1;result=CLOSE_UNKNOWN;goto done;}table=-1;
    result=SOURCE_INVALID;source=sc(56,AT_FDCWD,(long)"/dev/cnflasha1",RD,0);
    if(source<0 || !stat_(source,&ss) || (ss.mode&0170000)!=0060000 || ss.uid || ss.nlink!=1 ||
       major_(ss.rdev)!=selected[0] || minor_(ss.rdev)!=selected[1])goto done;
    result=SIZE_INVALID;if(sc(29,source,0x1260,(long)&sectors,0) || sectors!=TOTAL/512)goto done;
    result=CLOCK_INVALID;if(!tick(&now))goto done;deadline=now+60000000000ULL;
    char name[64];const char *prefix="fx3-p1-";u32 at=0;
    while(prefix[at]){name[at]=prefix[at];++at;}
    const char *hex="0123456789abcdef";
    for(u32 i=16;i<32;++i){name[at++]=hex[req[i]>>4];name[at++]=hex[req[i]&15];}
    name[at++]='-';name[at++]='w';name[at++]=(char)('0'+window);name[at++]='-';name[at++]='v';name[at++]='1';name[at]=0;
    result=OUTPUT_INVALID;
    if(sc(34,root,(long)name,0700,0))goto done;
    output=sc(56,root,(long)name,DIR,0);
    if(output<0 || !ram(output,0) || !stat_(output,&ds) || (ds.mode&0170000)!=0040000 ||
       (ds.mode&07777)!=0700 || ds.uid)goto done;
    result=save(output,"request.bin",req,64,0,0);if(result)goto done;
    u32 full_crc=0xffffffffu;
    for(u32 local=0;local<count;++local) {
        result=CLOCK_INVALID;if(!tick(&now))goto done;
        result=DEADLINE;if(now>=deadline)goto done;u64 call_deadline=now+5000000000ULL;
        result=SOURCE_INVALID;if(!stat_(source,&ss2) || !stable(&ss,&ss2))goto done;
        for(u32 i=0;i<32;++i){data[i]=0xc7;data[BLOCK+32+i]=0xc7;}
        u32 index=first+local;u64 offset=(u64)index*BLOCK;
        long actual=sc(67,source,(long)(data+32),BLOCK,(long)offset);
        result=CLOCK_INVALID;if(!tick(&now))goto done;
        result=DEADLINE;if(now>=deadline || now>=call_deadline)goto done;
        result=READ_INVALID;if(actual!=BLOCK)goto done;
        for(u32 i=0;i<32;++i)if(data[i]!=0xc7 || data[BLOCK+32+i]!=0xc7)goto done;
        result=SOURCE_INVALID;if(!stat_(source,&ss2) || !stable(&ss,&ss2))goto done;
        u8 header[128];zero(header,sizeof(header));copy(header,chunk_magic,16);
        put32(header+16,1);put32(header+20,window);put32(header+24,index);
        put64(header+32,TOTAL);put64(header+40,offset);put32(header+48,BLOCK);put32(header+52,BLOCK);
        put32(header+56,crc(0xffffffffu,data+32,BLOCK)^0xffffffffu);
        put32(header+60,selected[0]);put32(header+64,selected[1]);copy(header+72,req+16,16);copy(header+88,source_name,16);
        char file[]="chunk-000.bin";file[6]=(char)('0'+local/100);file[7]=(char)('0'+local/10%10);file[8]=(char)('0'+local%10);
        result=save(output,file,header,128,data+32,BLOCK);if(result)goto done;
        full_crc=crc(full_crc,data+32,BLOCK);
    }
    result=SIZE_INVALID;sectors=0;
    if(sc(29,source,0x1260,(long)&sectors,0) || sectors!=TOTAL/512)goto done;
    result=SOURCE_INVALID;if(!stat_(source,&ss2) || !stable(&ss,&ss2))goto done;
    result=CLOCK_INVALID;if(!tick(&now))goto done;
    result=DEADLINE;if(now>=deadline)goto done;
    if(sc(57,source,0,0,0)){source=-1;result=CLOSE_UNKNOWN;goto done;}source=-1;
    u8 manifest[128];zero(manifest,sizeof(manifest));copy(manifest,man_magic,16);
    put32(manifest+16,1);put32(manifest+20,window);put32(manifest+24,first);put32(manifest+28,count);
    put64(manifest+32,TOTAL);put64(manifest+40,(u64)first*BLOCK);put32(manifest+48,BLOCK);
    put32(manifest+52,full_crc^0xffffffffu);put32(manifest+56,selected[0]);put32(manifest+60,selected[1]);
    copy(manifest+64,req+16,16);copy(manifest+80,source_name,16);put32(manifest+100,63);put32(manifest+104,get32(req+52));
    result=save(output,"manifest.bin",manifest,128,0,0);if(result)goto done;
    result=sc(82,output,0,0,0)?WRITE_INVALID:OK;
done:
    /* Never retry close. A blocking syscall stays inside this invocation;
     * no watcher/constructor/cleanup thread creates a competing operation. */
    if(source>=0 && sc(57,source,0,0,0))result=CLOSE_UNKNOWN;
    if(table>=0 && sc(57,table,0,0,0))result=CLOSE_UNKNOWN;
    if(request>=0 && sc(57,request,0,0,0))result=CLOSE_UNKNOWN;
    if(output>=0 && sc(57,output,0,0,0))result=CLOSE_UNKNOWN;
    if(root>=0 && sc(57,root,0,0,0))result=CLOSE_UNKNOWN;
    return result;
}
#ifdef FX3_P1_HOST_FIXTURE
__attribute__((visibility("default"))) void fx3_p1_fixture_reset(void) {used=0;}
#endif
