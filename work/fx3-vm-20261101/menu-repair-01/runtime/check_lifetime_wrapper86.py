from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';source=(H/'fx3-osd-lifetime-v1.c').read_text();pre=r'''
#define syscall test_syscall
#define getenv test_getenv
#define dlsym test_dlsym
#define dladdr test_dladdr
#define clock_gettime test_clock
#define __errno_location test_errno
#define pthread_create test_thread_create
#define pthread_detach test_thread_detach
''';post=r'''
extern void abort(void);extern int puts(const char *);
#define CHECK(x) do{if(!(x)){dprintf(2,"FAIL at%d: %s\n",__LINE__,#x);abort();}}while(0)
static int error_value,on=1,native_rc,seen_errno,alloc_calls,send_calls,free_calls,thread_calls;static unsigned last_dst,last_n,last_wait;static void **last_out;static void *last_p;static unsigned char message[36];static U clock_value=100;
int *test_errno(void){return &error_value;}long test_syscall(long n,...){return n==172?123:n==178?77:0;}char *test_getenv(const char *n){return on&&!strcmp(n,"FX3_OSD_LIFETIME")?"observe-v1":0;}int test_clock(int n,struct lp_ts *t){CHECK(n==1);t->sec=clock_value/1000000000UL;t->ns=clock_value%1000000000UL;return 0;}int test_thread_create(void *p,const void *a,void *(*f)(void *),void *arg){(void)a;(void)f;(void)arg;*(U*)p=5;thread_calls++;return 0;}int test_thread_detach(U p){CHECK(p==5);return 0;}
int test_dladdr(const void *p,struct lp_di *d){d->file="/usr/lib/libObj.so";d->base=(void *)((U)p-0xf1db8);return 1;}
static int native_alloc(unsigned dst,void **out,unsigned n,unsigned wait){alloc_calls++;last_dst=dst;last_out=out;last_n=n;last_wait=wait;seen_errno=error_value;if(!native_rc)*out=message;error_value=723;return native_rc;}
static int native_send(unsigned dst,void *p){send_calls++;last_dst=dst;last_p=p;seen_errno=error_value;error_value=724;return native_rc;}
static int native_free(unsigned dst,void *p){free_calls++;last_dst=dst;last_p=p;seen_errno=error_value;error_value=725;return native_rc;}
static unsigned native_size(void *p){CHECK(p==message);return 12;}static unsigned native_source(void *p){CHECK(p==message);return 0x8288076cU;}static int native_stat(unsigned d,unsigned *o){(void)d;memset(o,0,16);return 0;}static int native_gate(unsigned p,U seq){(void)p;(void)seq;return 0;}
void *test_dlsym(void *h,const char *n){(void)h;if(!strcmp(n,"osal_valloc_msg_wait"))return(void *)native_alloc;if(!strcmp(n,"osal_snd_msg"))return(void *)native_send;if(!strcmp(n,"osal_free_msg"))return(void *)native_free;if(!strcmp(n,"osal_msg_size"))return(void *)native_size;if(!strcmp(n,"osal_get_msg_src"))return(void *)native_source;if(!strcmp(n,"osal_stat_msgq"))return(void *)native_stat;if(!strcmp(n,"fx3_osd_timeout_pair"))return(void *)native_gate;abort();}
int main(void){void *out=0;error_value=411;CHECK(!osal_valloc_msg_wait(0x8280074d,&out,12,1));CHECK(alloc_calls==1&&last_dst==0x8280074d&&last_out==&out&&last_n==12&&last_wait==1&&seen_errno==411&&error_value==723&&out==message&&ledger.live==1);unsigned char wire[12]={2,16,0,0,0,0,0,0,5,16,0,0};memcpy(message,wire,12);error_value=412;CHECK(!osal_snd_msg(0x8280074d,message));CHECK(send_calls==1&&last_dst==0x8280074d&&last_p==message&&seen_errno==412&&error_value==724&&ledger.pending==0x1005&&ledger.sends==1&&thread_calls==1&&!memcmp(message,wire,12));error_value=413;CHECK(!osal_free_msg(0x8280074d,message));CHECK(free_calls==1&&seen_errno==413&&error_value==725&&!ledger.live&&ledger.frees==1);native_rc=-1022;error_value=414;CHECK(osal_valloc_msg_wait(0x8280074d,&out,12,7)==-1022&&seen_errno==414&&error_value==723&&last_wait==7&&!ledger.live);on=0;error_value=415;CHECK(osal_snd_msg(0x8280074d,message)==-1022&&seen_errno==415&&error_value==724);CHECK(alloc_calls==2&&send_calls==2&&free_calls==1);puts("LIFETIME_WRAPPER_PASS actual_full_helper/all_native_args_and_errno_results_preserved/original_body_unchanged/no_extra_free_or_receive/failure_passthrough/enabled_disabled");return 0;}
''';p=H/'check-osd-lifetime-wrapper-v1.c';p.write_text(pre+source+post);a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];q=subprocess.run(a,text=True,capture_output=True);assert not q.returncode,q.stderr;q=subprocess.run([str(p.with_suffix(''))],text=True,capture_output=True);(H/'osd-lifetime-wrapper-host-check.json').write_text(json.dumps({'args':a,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr,'actual_helper_sha256':hashlib.sha256(source.encode()).hexdigest(),'scope':'Full actual helper compiled with native API/system mocks; no guest acceptance'},indent=2)+'\n');assert not q.returncode,q.stderr;print(q.stdout)
