/* Own object-anchored exit observer candidate. No numeric-PID lookup/wait,
 * device/source IO, signal, reset or process spawning. The input proc FD must
 * first be authenticated as the fixed child's OWN proc directory by an outer
 * handshake which is NOT implemented here. No complete job/USB certificate. */
typedef unsigned char u8;typedef unsigned int u32;typedef unsigned long u64;
static volatile u32 observer_state;
static const char stat_name[]="stat";
enum {HELD=2,DENIED=4,DETACHED_AFTER_SENTINEL=11,SENTINEL_STATUS=42<<8};
struct kstat {u64 dev,ino;u32 mode,nlink,uid,gid;u64 rdev,pad1;long size;int blksize,pad2;long blocks,atime;u64 atime_ns;long mtime;u64 mtime_ns;long ctime;u64 ctime_ns;u32 pad3,pad4;};
_Static_assert(sizeof(struct kstat)==128,"Linux64 stat ABI");
static long sc(long n,long a,long b,long c,long d,long e,long f){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static int close1(long *fd){long n=*fd;*fd=-1;return n<0||sc(57,n,0,0,0,0,0)==0;}
static int meta(long fd,u32 type,struct kstat *out){
 long fs[15]={0};if(sc(80,fd,(long)out,0,0,0,0)||sc(44,fd,(long)fs,0,0,0,0))return 0;
 return (u64)fs[0]==0x9fa0&&(out->mode&0170000)==type&&!out->uid&&out->ino;
}
static int anchored(long fd,const struct kstat *expected){struct kstat now;return meta(fd,0040000,&now)&&now.dev==expected->dev&&now.ino==expected->ino;}
static int number(const u8 *p,u32 n,u32 *at,int signed_ok,u64 *out,int *negative){
 u32 i=*at;u64 value=0;*negative=0;if(signed_ok&&i<n&&p[i]=='-'){*negative=1;i++;}
 u32 start=i;while(i<n&&p[i]>='0'&&p[i]<='9'){u64 digit=p[i]-'0';if(value>(~0ULL-digit)/10)return 0;value=value*10+digit;i++;}
 if(i==start)return 0;*at=i;*out=value;return 1;
}
static int record(const u8 *p,u32 n,u32 pid,u32 parent,u64 start,char *state,u32 *status){
 u32 at=0;u64 v=0;int neg=0;if(!n||p[n-1]!='\n'||!number(p,n,&at,0,&v,&neg)||v!=pid||at+2>=n||p[at++]!=' '||p[at++]!='(')return 0;
 /* comm may contain spaces, newlines and ')' characters. Only the final
  * close-paren+space can precede the numeric tail in this kernel format. */
 u32 end=0;for(u32 i=at;i+3<n;i++){if(!p[i])return 0;if(p[i]==')'&&p[i+1]==' ')end=i;}
 if(!end||end+4>=n||p[end+3]!=' ')return 0;*state=(char)p[end+2];at=end+4;
 for(u32 field=4;field<=52;field++){
  if(!number(p,n,&at,1,&v,&neg))return 0;
  if(field==4&&(neg||v!=parent))return 0;
  if(field==20&&(neg||v!=1))return 0;
  if(field==22&&(neg||v!=start))return 0;
  if(field==52){if(neg||v>0xffffffffULL||at!=n-1)return 0;*status=(u32)v;}
  else if(at>=n||p[at++]!=' ')return 0;
 }
 return 1;
}
static int read_stat(long anchor,u8 *buf,u32 *size){
 long fd=sc(56,anchor,(long)stat_name,0xa0000,0,0,0);if(fd<0)return fd==-2||fd==-3?-1:0;
 struct kstat before,after;int ok=meta(fd,0100000,&before);u32 used=0;
 if(ok)for(u32 round=0;round<129;round++){
  long n=sc(63,fd,(long)(buf+used),4096-used,0,0,0);
  if(n<0){ok=(n==-2||n==-3)?-1:0;break;}
  if(n>(long)(4096-used)){ok=0;break;}if(!n){*size=used;break;}used+=(u32)n;
  if(used==4096||round==128){ok=0;break;}
 }
 if(ok==1&&(!meta(fd,0100000,&after)||after.dev!=before.dev||after.ino!=before.ino))ok=0;
 if(!close1(&fd))ok=0;return ok;
}
static int observe_anchor(long anchor,u32 pid,u32 parent,u64 start){
 observer_state=DENIED;struct kstat identity;u8 data[4096];int result=HELD,saw=0;
 if(anchor<3||pid<=1||parent<=1||!start||sc(174,0,0,0,0,0,0)||sc(175,0,0,0,0,0,0)||!meta(anchor,0040000,&identity))return DENIED;
 observer_state=HELD;
 for(u32 attempt=0;attempt<100;attempt++){
  if(!anchored(anchor,&identity))break;u32 n=0,status=0;char state=0;int r=read_stat(anchor,data,&n);
  if(r<0){if(saw&&anchored(anchor,&identity))result=DETACHED_AFTER_SENTINEL;break;}
  if(!r||!record(data,n,pid,parent,start,&state,&status)||!anchored(anchor,&identity))break;
  if(state=='Z'){
   /* Saved native code can filter exit_code to ZERO on ptrace denial.
    * Only this fixed NONZERO raw normal-exit status is success evidence. */
   if(status!=SENTINEL_STATUS)break;saw=1;
  }else if(saw||(state!='S'&&state!='R'&&state!='D'))break;
  long pause[2]={0,10000000};if(sc(101,(long)pause,0,0,0,0,0))break;
 }
 if(!close1(&anchor))result=HELD;observer_state=(u32)result;return result;
}

/* Own native receiver/ACK component. Real creation, endpoint exclusivity and
 * prepared-plan binding are NOT supplied by this fixture entry. */
static volatile u32 receiver_state;
struct iov {void *base;u64 size;};
struct msg {void *name;u32 namelen,pad;struct iov *iov;u64 iovlen;void *control;u64 controllen;u32 flags,pad2;};
_Static_assert(sizeof(struct msg)==56,"Linux native msghdr ABI");
static void zero(void *v,u32 n){u8 *p=v;for(u32 i=0;i<n;i++)p[i]=0;}
static u32 g32(const u8 *p){u32 v=0;for(u32 i=0;i<4;i++)v|=(u32)p[i]<<(8*i);return v;}
static u64 g64(const u8 *p){u64 v=0;for(u32 i=0;i<8;i++)v|=(u64)p[i]<<(8*i);return v;}
static void p32(u8 *p,u32 v){for(u32 i=0;i<4;i++)p[i]=(u8)(v>>(8*i));}
static int equal(const u8 *a,const u8 *b,u32 n){u8 v=0;for(u32 i=0;i<n;i++)v|=a[i]^b[i];return !v;}
static u32 crc(const u8 *p,u32 n){u32 c=~0u;for(u32 i=0;i<n;i++){c^=p[i];for(u32 j=0;j<8;j++)c=(c>>1)^((0u-(c&1))&0xedb88320u);}return ~c;}
static void expected(u8 *p,u32 type,u32 child){
 zero(p,256);const u8 magic[16]="FX3ISOCOLLECT1";for(u32 i=0;i<16;i++)p[i]=magic[i];p32(p+16,1);p32(p+20,type);p32(p+24,child);
 /* Same synthetic association as238. It is NOT a real request or approval. */
 for(u32 i=32;i<80;i++)p[i]=(u8)(i^0xa6);p32(p+252,crc(p,252));
}
static int channel_profile(long fd,u32 self){
 struct kstat s;if(sc(80,fd,(long)&s,0,0,0,0)||(s.mode&0170000)!=0140000||s.uid||sc(25,fd,1,0,0,0,0)!=1)return 0;
 u32 size=4,type=0,pass=0,peer[3]={0};u8 address[16]={0};u32 len=sizeof(address);
 if(sc(209,fd,1,3,(long)&type,(long)&size,0)||size!=4||type!=2)return 0;
 size=4;if(sc(209,fd,1,16,(long)&pass,(long)&size,0)||size!=4||pass!=1)return 0;
 size=12;if(sc(209,fd,1,17,(long)peer,(long)&size,0)||size!=12||peer[0]!=self||peer[1]||peer[2])return 0;
 return !sc(204,fd,(long)address,(long)&len,0,0,0)&&len==2&&address[0]==1&&!address[1];
}
static int now(u64 *out){long t[2]={0};if(sc(113,1,(long)t,0,0,0,0)||t[0]<0||t[1]<0||t[1]>=1000000000L)return 0;*out=(u64)t[0]*1000000000ULL+(u64)t[1];return 1;}
static int live_window(u64 begun,u64 deadline){u64 t=0;return now(&t)&&t>=begun&&t<deadline;}
static int start_tick(const u8 *p,u32 n,u64 *out){
 u32 end=0;for(u32 i=0;i+3<n;i++)if(p[i]==')'&&p[i+1]==' ')end=i;
 if(!end)return 0;u32 at=end+4;u64 v=0;int neg=0;
 for(u32 field=4;field<=22;field++){if(!number(p,n,&at,1,&v,&neg))return 0;if(field==22){if(neg||!v)return 0;*out=v;return 1;}if(at>=n||p[at++]!=' ')return 0;}return 0;
}
static int receive_one(long fd,u32 child,const u8 wanted[256],long *owned){
 u8 payload[256];u64 aligned_control[512];zero(payload,sizeof(payload));zero(aligned_control,sizeof(aligned_control));struct iov v={payload,256};struct msg m;zero(&m,sizeof(m));m.iov=&v;m.iovlen=1;m.control=aligned_control;m.controllen=sizeof(aligned_control);
 long n=sc(212,fd,(long)&m,0x40000040,0,0,0);if(n==-11)return 2;
 u8 *control=(u8 *)aligned_control;long rights[253];u32 count=0,creds=0;int bad=n!=256||(m.flags&0x28),unknown=n<0;
 u64 limit=m.controllen;if(limit>sizeof(aligned_control)){bad=unknown=1;limit=sizeof(aligned_control);}
 for(u64 at=0;at<limit;){
  if(limit-at<16){bad=unknown=1;break;}u64 length=g64(control+at);u32 level=g32(control+at+8),type=g32(control+at+12);
  if(length<16||length>limit-at){bad=unknown=1;break;}
  if(level==1&&type==2&&length==28){if(++creds!=1||g32(control+at+16)!=child||g32(control+at+20)||g32(control+at+24))bad=1;}
  else if(level==1&&type==1&&length>=20&&(length-16)%4==0){
   for(u64 j=16;j<length;j+=4){u32 raw=g32(control+at+j);int duplicate=0;if(raw>2147483647u||raw==(u32)fd){bad=unknown=1;continue;}
    for(u32 k=0;k<count;k++)if(rights[k]==(long)raw)duplicate=1;
    if(duplicate){bad=1;continue;}if(count==253){bad=unknown=1;continue;}rights[count++]=(long)raw;
   }
  }else bad=1;
  u64 step=(length+7)&~7ULL;if(step>limit-at){if(length!=limit-at)bad=unknown=1;break;}at+=step;
 }
 if(creds!=1||count!=1||!equal(payload,wanted,256))bad=1;
 if(!bad){*owned=rights[0];return 1;}
 for(u32 i=0;i<count;i++){long x=rights[i];if(!close1(&x))unknown=1;}
 /* Unsupported malformed kernel control data can hide installed rights.
  * Do not guess FD numbers or certify cleanup for that condition. */
 if(unknown)receiver_state=6;
 return 0;
}
__attribute__((visibility("default"))) int fx3_parent_receiver(long channel,u32 child){
 receiver_state=DENIED;long self=sc(172,0,0,0,0,0,0),anchor=-1;u8 hello[256],data[4096];u64 begun=0,start=0;int result=HELD;
 if(channel<3||child<=1||self<=1||sc(174,0,0,0,0,0,0)||sc(175,0,0,0,0,0,0)||!channel_profile(channel,(u32)self)||!now(&begun)||begun>~0ULL-2000000000ULL)return DENIED;
 receiver_state=HELD;u64 deadline=begun+2000000000ULL;expected(hello,3,child);int got=0;
 for(u32 i=0;i<100;i++){
  if(!live_window(begun,deadline))break;int r=receive_one(channel,child,hello,&anchor);if(r==1){got=1;break;}if(r!=2)break;
  long pause[2]={0,10000000};if(sc(101,(long)pause,0,0,0,0,0))break;
 }
 if(!got)goto end;
 struct kstat identity;u32 size=0,status=0;char state=0;
 if(sc(25,anchor,1,0,0,0,0)!=1||!meta(anchor,0040000,&identity)||read_stat(anchor,data,&size)!=1||!start_tick(data,size,&start)||!record(data,size,child,(u32)self,start,&state,&status)||(state!='S'&&state!='R')||!anchored(anchor,&identity))goto end;
 /* ACK is sent once, after validated HELLO/anchor, before worker creation. */
 expected(hello,4,child);struct iov v={hello,256};struct msg m;zero(&m,sizeof(m));m.iov=&v;m.iovlen=1;
 if(!live_window(begun,deadline)||sc(211,channel,(long)&m,0x4040,0,0,0)!=256||!live_window(begun,deadline))goto end;
 if(!close1(&channel))goto end;
 {long moved=anchor;anchor=-1;result=observe_anchor(moved,child,(u32)self,start);}
 if(!live_window(begun,deadline))result=HELD;
end:
 if(!close1(&anchor))result=HELD;if(!close1(&channel))result=HELD;
 if(receiver_state!=6)receiver_state=(u32)result;return result;
}
