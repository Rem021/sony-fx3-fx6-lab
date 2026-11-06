/* Own private-process collector core. NOOP worker only; no target entry,
 * device source, firmware write or outer-host completion backend.
 * Return10 certifies only observed inner worker normal0 under the declared
 * private child-domain contract; it never certifies collector exit/reaping. */
typedef unsigned char u8;typedef unsigned int u32;typedef unsigned long u64;
static const u8 magic[16]="FX3ISOCOLLECT1";
static volatile u32 lifecycle_state;
static long sc(long n,long a,long b,long c,long d,long e,long f){
 register long x0 __asm__("x0")=a,x1 __asm__("x1")=b,x2 __asm__("x2")=c,x3 __asm__("x3")=d,x4 __asm__("x4")=e,x5 __asm__("x5")=f,x8 __asm__("x8")=n;
 __asm__ volatile("svc #0":"+r"(x0):"r"(x1),"r"(x2),"r"(x3),"r"(x4),"r"(x5),"r"(x8):"memory","cc");return x0;
}
static void zero(void *v,u32 n){u8 *p=v;for(u32 i=0;i<n;i++)p[i]=0;}
static int eq(const u8 *a,const u8 *b,u32 n){u8 v=0;for(u32 i=0;i<n;i++)v|=a[i]^b[i];return !v;}
static void p32(u8 *p,u32 v){for(u32 i=0;i<4;i++)p[i]=(u8)(v>>(8*i));}
static u32 g32(const u8 *p){u32 v=0;for(u32 i=0;i<4;i++)v|=(u32)p[i]<<(8*i);return v;}
static u64 g64(const u8 *p){u64 v=0;for(u32 i=0;i<8;i++)v|=(u64)p[i]<<(8*i);return v;}
static u32 crc(const u8 *p,u32 n){u32 c=~0u;for(u32 i=0;i<n;i++){c^=p[i];for(u32 j=0;j<8;j++)c=(c>>1)^((0u-(c&1))&0xedb88320u);}return ~c;}
static int tick(u64 *out){long t[2]={0,0};if(sc(113,1,(long)t,0,0,0,0)||t[0]<0||t[1]<0||t[1]>=1000000000L)return 0;*out=(u64)t[0]*1000000000ULL+(u64)t[1];return 1;}
static void sleep10(void){long t[2]={0,10000000};(void)sc(101,(long)t,0,0,0,0,0);}
static int close1(long *fd){if(*fd<0)return 1;long x=*fd;*fd=-1;return sc(57,x,0,0,0,0,0)==0;}
static void die(long code){sc(93,code,0,0,0,0,0);for(;;){}}
static int value(const u8 *s,u32 n,const char *key,u32 want){
 u32 size=0;while(key[size])size++;
 for(u32 i=0;i+size<n;i++){
  if((i==0||s[i-1]=='\n')&&eq(s+i,(const u8 *)key,size)){
  u32 j=i+size,v=0,digits=0;while(j<n&&(s[j]==' '||s[j]=='\t'))j++;
  while(j<n&&s[j]>='0'&&s[j]<='9'){if(v>214748364u)return 0;v=v*10+(s[j++]-'0');digits++;}
  return digits&&j<n&&s[j]=='\n'&&v==want;
  }
 }
 return 0;
}
static int status_guard(long self,long parent){
 long fd=sc(56,-100,(long)"/proc/self/status",0x80000,0,0,0);if(fd<0)return 0;
 u8 s[4096];u32 have=0;int ok=0;
 for(u32 i=0;i<65;i++){long n=sc(63,fd,(long)(s+have),sizeof(s)-have,0,0,0);if(n<0||n>(long)(sizeof(s)-have))break;if(!n){ok=value(s,have,"Pid:",(u32)self)&&value(s,have,"Tgid:",(u32)self)&&value(s,have,"PPid:",(u32)parent)&&value(s,have,"Threads:",1)&&value(s,have,"TracerPid:",0);break;}have+=(u32)n;if(have==sizeof(s))break;}
 if(!close1(&fd))ok=0;return ok;
}
static int close_inherited(long keep){
 long fd=sc(56,-100,(long)"/proc/self/fd",0x90000,0,0,0);if(fd<0||fd==keep)return 0;u8 b[1024];int ok=1;
 for(u32 round=0;round<1024;round++){
  long n=sc(61,fd,(long)b,sizeof(b),0,0,0);if(n<0){ok=0;break;}if(!n)break;
  for(long at=0;at<n;){if(n-at<20){ok=0;break;}u32 len=b[at+16]|(u32)b[at+17]<<8;if(len<20||len>(u32)(n-at)){ok=0;break;}
   u32 j=19,d=0;u64 number=0;if(b[at+j]=='.'){at+=len;continue;}
   while(j<len&&b[at+j]){u8 c=b[at+j++];if(c<'0'||c>'9'||number>214748364ULL){ok=0;break;}number=number*10+c-'0';d++;}
   if(!ok||!d||j==len||number>2147483647ULL){ok=0;break;}
   if((long)number!=fd&&(long)number!=keep&&sc(57,(long)number,0,0,0,0,0)){ok=0;break;}at+=len;
  }if(!ok)break;if(round==1023)ok=0;
 }if(!close1(&fd))ok=0;return ok;
}
struct iov {void *p;u64 size;};
struct msg {void *name;u32 namelen,pad;struct iov *iov;u64 iovlen;void *control;u64 controllen;u32 flags,pad2;};
_Static_assert(sizeof(struct msg)==56,"native Linux64 msg ABI");
static void packet(u8 *p,u32 type,long self,long worker){
 zero(p,256);for(u32 i=0;i<16;i++)p[i]=magic[i];p32(p+16,1);p32(p+20,type);p32(p+24,(u32)self);p32(p+28,(u32)worker);
 /* Synthetic association only, not approval or actual camera attestation. */
 for(u32 i=32;i<80;i++)p[i]=(u8)(i^0xa6);p32(p+252,crc(p,252));
}
static int send1(long fd,const u8 *p){struct iov v={(void *)p,256};struct msg m;zero(&m,sizeof(m));m.iov=&v;m.iovlen=1;return sc(211,fd,(long)&m,0x4000,0,0,0)==256;}
static int recv1(long fd,long sender,const u8 *wanted){
 u8 p[256],c[128];struct iov v={p,256};struct msg m;zero(&m,sizeof(m));zero(c,sizeof(c));m.iov=&v;m.iovlen=1;m.control=c;m.controllen=sizeof(c);
 long n=sc(212,fd,(long)&m,0x40000040,0,0,0);if(n==-11)return 2;if(n<0||m.controllen>sizeof(c))return 0;
 int ok=n==256&&!(m.flags&0x28),creds=0;
 for(u64 at=0;at<m.controllen;){if(m.controllen-at<16)return 0;u64 len=g64(c+at);u32 level=g32(c+at+8),type=g32(c+at+12);if(len<16||len>m.controllen-at)return 0;
  if(level==1&&type==2&&len==28){if(++creds!=1||g32(c+at+16)!=(u32)sender||g32(c+at+20)||g32(c+at+24))ok=0;}
  else{ok=0;if(level==1&&type==1&&len>=20&&(len-16)%4==0)for(u64 j=16;j<len;j+=4)(void)sc(57,g32(c+at+j),0,0,0,0,0);}
  u64 next=(len+7)&~7ULL;if(next>m.controllen-at)return 0;at+=next;
 }return ok&&creds==1&&eq(p,wanted,256);
}
static void worker(long fd,long parent,u64 deadline){
 long self=sc(172,0,0,0,0,0,0);if(self<=1||self!=sc(178,0,0,0,0,0,0)||sc(173,0,0,0,0,0,0)!=parent)die(61);
 if(!close_inherited(fd))die(62);u8 p[256];packet(p,1,parent,self);int granted=0;
 for(u32 i=0;i<100;i++){u64 now=0;if(!tick(&now)||now>=deadline)die(69);int r=recv1(fd,parent,p);if(r==1){granted=1;break;}if(r!=2)die(63);sleep10();}
 if(!granted)die(70);
 /* This purpose is exclusively an empty lifecycle exercise. */
 packet(p,2,parent,self);if(!send1(fd,p))die(67);if(!close1(&fd))die(68);die(0);
}
static int collector_core(void){
 long self=sc(172,0,0,0,0,0,0);u64 mask=0,blocked=~((1ULL<<8)|(1ULL<<18));
 lifecycle_state=4;
 if(self<=1||self!=sc(178,0,0,0,0,0,0)||sc(173,0,0,0,0,0,0)!=321||sc(174,0,0,0,0,0,0)||sc(175,0,0,0,0,0,0))return 4;
 /* The bootstrap must have blocked signals BEFORE creating this process.
  * This core does not provide or certify that missing outer bootstrap. */
 if(sc(135,2,0,(long)&mask,8,0,0)||mask!=blocked||!status_guard(self,321))return 4;
 int sub=-1,status=-1;if(sc(167,37,(long)&sub,0,0,0,0)||sub||sc(260,-1,(long)&status,0x40000001UL,0,0,0)!=-10)return 4;
 for(long sig=1;sig<=64;sig++){if(sig==9||sig==19)continue;u64 action[4]={0},seen[4]={1,1,1,1};if(sc(134,sig,(long)action,0,8,0,0)||sc(134,sig,0,(long)seen,8,0,0)||!eq((u8 *)action,(u8 *)seen,32))return 4;}
 if(!close_inherited(-1))return 2;
 int pair[2]={-1,-1};if(sc(199,1,0x80002,0,(long)pair,0,0))return 2;
 long left=pair[0],right=pair[1];u32 enabled=1;
 if(sc(208,left,1,16,(long)&enabled,4,0)||sc(208,right,1,16,(long)&enabled,4,0)){close1(&left);close1(&right);return 2;}
 u64 begun=0;if(!tick(&begun)||begun>~0ULL-2000000000ULL){close1(&left);close1(&right);return 2;}
 u64 deadline=begun+2000000000ULL;
 long child=sc(220,0,0,0,0,0,0);if(!child)worker(right,self,deadline);
 if(child<=1||child>2147483647L){close1(&left);close1(&right);return 2;}
 lifecycle_state=2;int held=0,done=0,reaped=0;u32 polls=0;u8 p[256];
 if(!close1(&right))held=1;packet(p,1,self,child);if(held||!send1(left,p))held=1;
 for(;;){
  u64 now=0;if(!tick(&now)||now<begun||now>=deadline||polls++>=100)held=1;
  if(!done){packet(p,2,self,child);int r=recv1(left,child,p);if(r==1)done=1;else if(r!=2)held=1;}
  if(!reaped){long r=sc(260,child,(long)&status,0xa0000001UL,0,0,0);if(r==child){reaped=1;if(status)held=1;}else if(r<0)held=1;}
  if(reaped){if(!done){packet(p,2,self,child);if(recv1(left,child,p)==1)done=1;}if(!done)held=1;break;}
  /* Timeout/error is sticky HELD. Do not abandon a potentially live child,
   * return a success, kill/restart, or spin in the caller's service thread. */
  sleep10();
 }
 if(!close1(&left))held=1;
 if(held){lifecycle_state=2;return 2;}
 lifecycle_state=10;return 10;
}

/* The inherited53 is an explicit fixture transport role, not a discovered
 * camera interface. Its real parent creation/ownership is still unverified. */
__attribute__((visibility("default"))) int fx3_isolated_collector_core(void){
 long self=sc(172,0,0,0,0,0,0);u64 mask=0,blocked=~((1ULL<<8)|(1ULL<<18));
 if(self<=1||self!=sc(178,0,0,0,0,0,0)||sc(173,0,0,0,0,0,0)!=321||sc(174,0,0,0,0,0,0)||sc(175,0,0,0,0,0,0)||sc(135,2,0,(long)&mask,8,0,0)||mask!=blocked)return 4;
 long channel=53,anchor=sc(56,-100,(long)"/proc/self",0x90000,0,0,0);if(anchor<0)return 2;
 u8 hello[256];packet(hello,3,self,0);u64 control[3]={20,0x0000000100000001ULL,0};p32((u8 *)control+16,(u32)anchor);
 struct iov v={hello,256};struct msg m;zero(&m,sizeof(m));m.iov=&v;m.iovlen=1;m.control=control;m.controllen=sizeof(control);
 int ok=sc(211,channel,(long)&m,0x4000,0,0,0)==256;
 if(!close1(&anchor))ok=0;if(!close1(&channel))ok=0;if(!ok)return 2;
 return collector_core();
}
