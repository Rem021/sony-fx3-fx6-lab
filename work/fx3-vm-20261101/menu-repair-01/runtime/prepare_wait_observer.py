from pathlib import Path
import json,subprocess,os,hashlib
R=Path(__file__).resolve().parent;s=(R/'helpers/ioctl-trace-v9.c').read_text();a='static unsigned int ioctl_count;'
extra='''extern long syscall(long,...);
static unsigned char event_lock;
static struct {long tid;unsigned int target;} waits[256];
static struct {unsigned int target,op,tag1,tag2;} sends[256];
static unsigned int wait_count,send_count;
static void recv_begin(unsigned int target,void *caller){
 long tid=syscall(178);int emit=0;
 if(__atomic_test_and_set(&event_lock,__ATOMIC_ACQUIRE))return;
 unsigned int i;for(i=0;i<wait_count;i++)if(waits[i].tid==tid&&waits[i].target==target)break;
 if(i==wait_count&&wait_count<256){waits[i].tid=tid;waits[i].target=target;wait_count++;emit=1;}
 __atomic_clear(&event_lock,__ATOMIC_RELEASE);if(!emit)return;
 char path[80],name[17]={0};snprintf(path,sizeof path,"/proc/self/task/%ld/comm",tid);int fd=open(path,0);
 if(fd>=0){long n=pread(fd,name,16,0);close(fd);if(n>0&&name[n-1]=='\\n')name[n-1]=0;}
 dprintf(2,"FX3_UIPC_RECV_BEGIN tid=%ld name=%s queue=%#x caller=%p original_wait_follows=1\\n",tid,name,target,caller);
}
static void send_unique(unsigned int target,unsigned int op,const unsigned char *body,long n,int result,int error,void *caller){
 if(op<4||op>6||n!=16||target==0x8f013a||target==0x8f0139||target==0x8f0313||target==0x910040||target==0x910041||target==0x910042)return;
 unsigned int first,second;__builtin_memcpy(&first,body,4);__builtin_memcpy(&second,body+4,4);int emit=0;
 if(__atomic_test_and_set(&event_lock,__ATOMIC_ACQUIRE))return;
 unsigned int i;for(i=0;i<send_count;i++)if(sends[i].target==target&&sends[i].op==op&&sends[i].tag1==first&&sends[i].tag2==second)break;
 if(i==send_count&&send_count<256){sends[i].target=target;sends[i].op=op;sends[i].tag1=first;sends[i].tag2=second;send_count++;emit=1;}
 __atomic_clear(&event_lock,__ATOMIC_RELEASE);
 if(emit)dprintf(2,"FX3_UIPC_SEND_UNIQUE tid=%ld target=%#x op=%u tag1=%#x tag2=%#x result=%d errno=%d caller=%p delegated=1\\n",syscall(178),target,op,first,second,result,error,caller);
}
'''
assert a in s;s=s.replace(a,extra+'\n'+a)
a='    *__errno_location() = entry_errno;\n    int result = function(fd, request, argument);';assert a in s;s=s.replace(a,'    if(is_uipc&&command==7&&outer_read==16)recv_begin(argument0,caller);\n'+a)
a='    int saved_errno = *__errno_location();\n    unsigned int sequence';assert a in s;s=s.replace(a,'    int saved_errno = *__errno_location();\n    if(is_uipc)send_unique(argument0,command,message,message_read,result,saved_errno,caller);\n    unsigned int sequence')
(R/'helpers/ioctl-trace-v10.c').write_text(s);v=json.loads((R/'helpers/compile-attempt09.json').read_text());args=[a.replace('ioctl-trace-v9.c','ioctl-trace-v10.c').replace('ioctl-trace-v9.so','ioctl-trace-v10.so') for a in v['args']];env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(R/'toolchains/zig-cache');env['ZIG_LOCAL_CACHE_DIR']=str(R/'toolchains/zig-local-cache');p=subprocess.run(args,env=env,capture_output=True,text=True);assert not p.returncode,p.stderr;(R/'helpers/compile-attempt10.json').write_text(json.dumps({'args':args,'exit':p.returncode,'stderr':p.stderr,'source_sha256':hashlib.sha256((R/'helpers/ioctl-trace-v10.c').read_bytes()).hexdigest(),'scope':'passive recv-before-block and unique send signatures, bounded256 each, original IO/result/errno unchanged'},indent=2)+'\n')
s=(R/'prepare_date_ap31.py').read_text().replace("ap31-date-zone'", "ap32-app-wait'").replace('candidate31.json','candidate32.json').replace('fx3-gpe-observe-v4.so','fx3-gpe-observe-v5.so').replace('ioctl-trace-v9.so','ioctl-trace-v10.so');(R/'prepare_app_ap32.py').write_text(s);print('compiled wait observer')
