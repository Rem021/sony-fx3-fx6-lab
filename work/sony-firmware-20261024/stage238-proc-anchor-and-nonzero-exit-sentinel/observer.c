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
__attribute__((visibility("default"))) int fx3_proc_anchor_observer(long anchor,u32 pid,u32 parent,u64 start){
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
