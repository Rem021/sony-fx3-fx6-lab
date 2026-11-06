/* Actual baseline/candidate translation unit, all native/system facilities mocked.
 * Native firmware and guest timing are NOT executed by this fixture. */
#define R35_HOST_MANUAL_INIT 1
#define open m_open
#define read m_read
#define pread m_pread
#define close m_close
#define mmap m_mmap
#define munmap m_munmap
#define syscall m_syscall
#define dprintf m_dprintf
#define dlsym m_dlsym
#define dlopen m_dlopen
#define dlinfo m_dlinfo
#define getenv m_getenv
#define pthread_create m_pthread_create
#define pthread_detach m_pthread_detach
#define pthread_atfork m_pthread_atfork
#define clock_gettime m_clock_gettime
#define __errno_location m_errno
#include SOURCE_FILE
extern int printf(const char *,...);extern void exit(int);
#define CHECK(x) do{if(!(x)){printf("FAIL line=%d expr=%s\n",__LINE__,#x);exit(1);}}while(0)
static int er,mode,send_rc,send_count,open_count,read_count,map_count,close_count,log_count,thread_count,nested;
static unsigned char memory[HO_RESERVE],message[12];static unsigned query_count;
#ifdef BENCH
extern U host_cost_ns(void);extern long host_cost_getpid(void);
#endif
static unsigned bytes=12,source=HO_AP;
int *m_errno(void){return &er;}
int m_open(const char *p,int f,...){open_count++;if(strstr(p,".claim"))return mode==1?-1:7;if(!strcmp(p,"/proc/cmdline"))return mode==2?-1:8;if(!strcmp(p,"/proc/self/mem"))return mode==3?-1:9;if(!strcmp(p,"/dev/mem"))return mode==4?-1:10;return -1;}
long m_read(int fd,void *b,size_t n){read_count++;const char *s="memrsv=0x01000000@0x41e000000:uc";if(mode==7)s="wrong-header";size_t k=0;while(s[k])k++;if(k>n)k=n;memcpy(b,s,k);return k;}
long m_pread(int fd,void*b,size_t n,long at){return -1;}
int m_close(int x){close_count++;return 0;}
void *m_mmap(void*a,size_t n,int p,int f,int fd,long at){map_count++;return mode==5?(void*)-1:memory;}
int m_munmap(void*p,size_t n){return 0;}
long m_syscall(long n,...){if(n==172){query_count++;
#ifdef BENCH
return host_cost_getpid();
#else
return 241;
#endif
}return 242;}
int m_dprintf(int fd,const char*f,...){log_count++;return 0;}
void *m_dlsym(void*h,const char*n){return 0;}void *m_dlopen(const char*n,int f){return 0;}int m_dlinfo(void*h,int r,void*p){return -1;}
char *m_getenv(const char*n){if(!strcmp(n,"FX3_OSD_HEADLESS"))return "software-ring-v1";if(!strcmp(n,"FX3_OSD_QUEUE_OWNER"))return "native-receiver-v1";return 0;}
int m_pthread_create(void*t,const void*a,void*(*f)(void*),void*p){thread_count++;return 1;}int m_pthread_detach(U t){return 0;}
int m_pthread_atfork(void(*a)(void),void(*b)(void),void(*c)(void)){return 0;}
int m_clock_gettime(int n,struct timing_ts*t){t->s=4;t->n=123;return 0;}
static unsigned sz(void*p){return bytes;}static unsigned src(void*p){return source;}
static int stub_alloc(unsigned a,void**p,unsigned n,unsigned f){return -1;}static int stub_wait(unsigned a,unsigned b){return -1;}static int stub_signal(unsigned a){return 0;}static int stub_receive(unsigned a,void**p,long t){return -1;}
static int delegate(unsigned dst,void*p){send_count++;CHECK(er==37);if(nested==1){nested=2;unsigned char q[12]={2,16,0,0,0,0,0,0,3,16,0,0};int e=osal_snd_msg(dst,q);CHECK(e==send_rc);}memset(p,0xcc,12);er=123;return send_rc;}
static void reset(int m,int rc){mode=m;send_rc=rc;send_count=open_count=read_count=map_count=close_count=log_count=thread_count=nested=0;er=37;api_ready=1;hsend=delegate;hsize=sz;hsource=src;halloc=stub_alloc;hwait=stub_wait;hsignal=stub_signal;hreceive=stub_receive;observer_ready=worker_started=ho_lock=0;pmem=-1;ring=0;memset(&hm,0,sizeof hm);memset(&ownership,0,sizeof ownership);bytes=12;source=HO_AP;unsigned char q[12]={2,16,0,0,0,0,0,0,3,16,0,0};memcpy(message,q,12);
#ifdef CANDIDATE
 r35_lock=r35_owner=r35_loss=0;memset(&r35_record,0,sizeof r35_record);r35_init();CHECK(er==37);
#endif
}
int main(void){
#ifdef BENCH
 U total=0;unsigned iterations=20000,queries=0;
 for(unsigned i=0;i<iterations;i++){reset(1,0);unsigned before=query_count;U begin=host_cost_ns();int rc=osal_snd_msg(HO_CONTROL,message);U end=host_cost_ns();total+=end-begin;CHECK(!rc&&er==123&&send_count==1);unsigned delta=query_count-before;if(!i)queries=delta;CHECK(queries==delta);}
 printf("BENCH actual_wrapper_claim_failure_ns=%.2f iterations=%u actual_host_getpid_calls_per_wrapper=%u interval_includes_clock_measurement_overhead=1 mocked_native_and_IO=1\n",(double)total/iterations,iterations,queries);
 reset(1,0);CHECK(osal_snd_msg(HO_CONTROL,message)==0);total=0;queries=0;
 for(unsigned i=0;i<iterations;i++){unsigned char q[12]={2,16,0,0,0,0,0,0,3,16,0,0};memcpy(message,q,12);er=37;unsigned before=query_count;U begin=host_cost_ns();int rc=osal_snd_msg(HO_CONTROL,message);U end=host_cost_ns();total+=end-begin;CHECK(!rc&&er==123);unsigned delta=query_count-before;if(!i)queries=delta;CHECK(delta==queries);}
 printf("BENCH steady_completed_claim_failure_wrapper_ns=%.2f iterations=%u actual_host_getpid_calls_per_wrapper=%u no_collector_reset=1 native_and_IO_mock=1\n",(double)total/iterations,iterations,queries);return 0;
#endif
 for(int i=0;i<8;i++){
  reset(i,i==6?-17:0);int rc=osal_snd_msg(HO_CONTROL,message);CHECK(send_count==1&&rc==send_rc&&er==123);
#ifdef CANDIDATE
  struct r35_packet p={{0}};CHECK(fx3_r35_snapshot_v1(R35_ABI,&p)==1);CHECK(p.w[6]==2&&(int)p.w[8]==send_rc&&p.w[7]==0x1003);
  if(i==6)CHECK(!p.w[9]&&!ring);else{CHECK(p.w[9]==2);int expected=i==1?-1:i==2||i==7?-2:i==3?-3:i==4||i==5?-4:0;CHECK((int)p.w[10]==expected);CHECK(p.w[11]==(i==4?1:i==5?2:i==0?3:0));if(i==0)CHECK(((U)p.w[12]|((U)p.w[13]<<32))==HO_MAGIC);}
#endif
  printf("CASE mode=%d rc=%d errno=%d sends=%d opens=%d reads=%d maps=%d closes=%d logs=%d threads=%d\n",i,rc,er,send_count,open_count,read_count,map_count,close_count,log_count,thread_count);
 }
 reset(1,0);message[2]=1;CHECK(osal_snd_msg(HO_CONTROL,message)==0);
#ifdef CANDIDATE
 CHECK(!r35_record.w[6]);
#endif
 reset(1,-17);nested=1;CHECK(osal_snd_msg(HO_CONTROL,message)==-17&&send_count==2&&er==123);
#ifdef CANDIDATE
 CHECK(r35_record.w[6]==2&&(int)r35_record.w[8]==-17);
 reset(1,0);r35_owner=0;CHECK(osal_snd_msg(HO_CONTROL,message)==0);CHECK(!r35_record.w[6]&&!r35_loss);r35_init();struct r35_packet p;CHECK(fx3_r35_snapshot_v1(R35_ABI,&p)==1&&!p.w[6]);

#endif
 printf("WRAPPER_PASS\n");return 0;
}
