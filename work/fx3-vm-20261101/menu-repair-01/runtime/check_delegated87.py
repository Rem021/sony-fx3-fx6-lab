from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';source=(H/'fx3-display-observe-v4.c').read_text();body=source[source.index('static unsigned trace_packets;'):];pre=r'''
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include <stdarg.h>
typedef unsigned long U;static int e=42;static unsigned calls,seen_dst,seen_errno,length=12;static void *seen_pointer;static int rc=-1024;static U app_base=0x10000000,obj_base=0x20000000;static unsigned char message[12]={13,32,2,4,12,0,1,128,0,0,0,0};
static int native(unsigned dst,void *p){calls++;seen_dst=dst;seen_pointer=p;seen_errno=e;e=77;return rc;}static unsigned size(void *p){assert(p==message);return length;}static unsigned source(void *p){assert(p==message);return 0x81cf6100;}
static void *mock_dlsym(void *h,const char *n){(void)h;if(!strcmp(n,"osal_snd_msg"))return(void *)native;if(!strcmp(n,"osal_msg_size"))return(void *)size;if(!strcmp(n,"osal_get_msg_src"))return(void *)source;assert(0);return 0;}static char *mock_getenv(const char *n){assert(!strcmp(n,"FX3_DISPLAY_OBSERVE"));return "passive-v1";}static long mock_syscall(long n,...){assert(n==178);return 12;}static int *mock_errno(void){return &e;}static int peek(U p,void *o,U n){(void)p;(void)o;(void)n;return 0;}
#define dlsym mock_dlsym
#define getenv mock_getenv
#define syscall mock_syscall
#define __errno_location mock_errno
''';post=r'''
int main(void){unsigned char copy[12];memcpy(copy,message,12);assert(osal_snd_msg(0x92b4086f,message)==-1024&&calls==1&&seen_dst==0x92b4086f&&seen_pointer==message&&seen_errno==42&&e==77&&!memcmp(copy,message,12));e=43;rc=0;assert(!osal_snd_msg(0x8280074d,message)&&calls==2&&seen_errno==43&&e==77&&!memcmp(copy,message,12));e=44;length=1025;assert(!osal_snd_msg(0x92b4086f,message)&&calls==3&&seen_errno==44&&e==77);puts("DELEGATED_WRAPPER_PASS actual_v4/newblock_raw_readonly/no_extra_send_free_receive/oversize_not_read/native_args_errno_result_preserved");}
''';p=H/'check-delegated87.c';p.write_text(pre+body+post);args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];q=subprocess.run(args,text=True,capture_output=True);assert not q.returncode,q.stderr;q=subprocess.run([str(p.with_suffix(''))],text=True,capture_output=True);(H/'delegated87-host-check.json').write_text(json.dumps({'args':args,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr,'helper_sha256':hashlib.sha256(source.encode()).hexdigest()},indent=2)+'\n');assert not q.returncode,q.stderr;print(q.stdout)
