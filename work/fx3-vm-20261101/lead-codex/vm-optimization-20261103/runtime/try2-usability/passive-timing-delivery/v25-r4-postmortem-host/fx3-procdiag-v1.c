/* Optional FX3 guest diagnostic. Reads /proc only; writes its own reserved
 * software slot at KEY93+0xa000. Never touches original task memory or keys.
 * Not part of the frozen r3 guest; built only for coordinator review.
 */
#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define KEY_PHYS 0x41df00000ULL
#define KEY_BYTES 0x10000
#define KEY_MAGIC 0x3545594b334d5253ULL
#define DIAG_HEADER 0x9000
#define SLOT0 0xa000
#define SLOT_BYTES 0x6000
#define TEXT_CAP (SLOT_BYTES-64)
#define MAX_OUTSTANDING 24
#define MAX_FILE_BYTES 1200
#define FILE_TIMEOUT_MS 100
#define TOTAL_CAPTURE_NS 3000000000ULL
#define MAX_SNAPSHOTS_PER_COMMAND 16
#define SNAP_MAGIC 0x31474e4953444350ULL /* PCDSING1 */

struct pending_child { pid_t pid; char path[192]; };
static struct pending_child pending[MAX_OUTSTANDING];
static unsigned pending_count;
static unsigned drop_count;
static char text[TEXT_CAP];
static size_t text_len;

static uint64_t mono_ns(void) {
    struct timespec t;
    if (clock_gettime(CLOCK_MONOTONIC, &t)) return 0;
    return (uint64_t)t.tv_sec*1000000000ULL+(uint64_t)t.tv_nsec;
}
static uint64_t fnv(const void *data,size_t n) {
    const unsigned char *p=data; uint64_t h=14695981039346656037ULL;
    for(size_t i=0;i<n;i++){h^=p[i];h*=1099511628211ULL;}
    return h;
}
static void add(const char *fmt,...) {
    if(text_len>=TEXT_CAP-1){drop_count++;return;}
    va_list ap;va_start(ap,fmt);
    int n=vsnprintf(text+text_len,TEXT_CAP-text_len,fmt,ap);
    va_end(ap);
    if(n<0){drop_count++;return;}
    if((size_t)n>=TEXT_CAP-text_len){text_len=TEXT_CAP-1;drop_count++;return;}
    text_len+=(size_t)n;
}
static void reap_children(void) {
    for(unsigned i=0;i<pending_count;) {
        int status;pid_t r=waitpid(pending[i].pid,&status,WNOHANG);
        if(r==pending[i].pid || (r<0&&errno==ECHILD)) {
            pending[i]=pending[--pending_count];
        } else i++;
    }
}
static int already_pending(const char *path) {
    for(unsigned i=0;i<pending_count;i++)if(!strcmp(pending[i].path,path))return 1;
    return 0;
}
static void track_child(pid_t child,const char *path) {
    if(pending_count>=MAX_OUTSTANDING){drop_count++;return;}
    pending[pending_count].pid=child;
    snprintf(pending[pending_count].path,sizeof pending[pending_count].path,"%s",path);
    pending_count++;
}
/* A fork isolates every potentially blocking /proc open/read. No inherited
 * business lock, no signal sent to any foreign PID, no unbounded waitpid.
 * A stuck child remains tracked and prevents another fork for that path.
 */
static int bounded_read(const char *path,char *out,size_t cap,uint64_t deadline,
                        const char *role,const char *kind) {
    uint64_t begin=mono_ns();out[0]=0;
    if(cap<2||cap>MAX_FILE_BYTES){add("FILE_END role=%s kind=%s status=invalid_cap\n",role,kind);return -1;}
    add("FILE_BEGIN role=%s kind=%s path=%s begin_ns=%llu\n",role,kind,path,
        (unsigned long long)begin);
    reap_children();
    if(already_pending(path)||pending_count==MAX_OUTSTANDING||begin>=deadline){
        add("FILE_END role=%s kind=%s status=%s bytes=0 end_ns=%llu\n",role,kind,
            begin>=deadline?"total_deadline":pending_count==MAX_OUTSTANDING?"child_cap":"prior_child_outstanding",
            (unsigned long long)mono_ns());return -1;
    }
    int fd[2];if(pipe(fd)){add("FILE_END role=%s kind=%s status=pipe_error errno=%d\n",role,kind,errno);return -1;}
    pid_t child=fork();
    if(child<0){int e=errno;close(fd[0]);close(fd[1]);add("FILE_END role=%s kind=%s status=fork_error errno=%d\n",role,kind,e);return -1;}
    if(child==0){
        close(fd[0]);int src=open(path,O_RDONLY|O_CLOEXEC);
        unsigned char packet[8+MAX_FILE_BYTES]={0};uint32_t count=0,status=0;
        if(src<0)status=101;
        else {
            while(count<cap-1){ssize_t n=read(src,packet+8+count,cap-1-count);
                if(n<0){status=102;break;}
                if(n==0)break;
                count+=(uint32_t)n;
            }
            if(count==cap-1&&status==0)status=1; /* possibly truncated, never full-ok */
            close(src);
        }
        memcpy(packet,&count,4);memcpy(packet+4,&status,4);
        /* <=1208 bytes, below PIPE_BUF: one complete diagnostic packet. */
        (void)write(fd[1],packet,8+count);close(fd[1]);_exit(0);
    }
    close(fd[1]);
    int flags=fcntl(fd[0],F_GETFL,0);
    if(flags<0||fcntl(fd[0],F_SETFL,flags|O_NONBLOCK)<0){
        int e=errno;close(fd[0]);int st;pid_t got=waitpid(child,&st,WNOHANG);
        if(got==0)track_child(child,path);
        add("FILE_END role=%s kind=%s status=nonblock_setup_error errno=%d child_pid=%ld reaped=%d\n",
            role,kind,e,(long)child,got==child);return -1;
    }
    unsigned char packet[8+MAX_FILE_BYTES];size_t have=0;uint64_t per_file_end=begin+FILE_TIMEOUT_MS*1000000ULL;
    if(per_file_end>deadline)per_file_end=deadline;
    while(have<sizeof packet){
        uint64_t now=mono_ns();if(now>=per_file_end)break;
        uint64_t rem=per_file_end-now;int ms=(int)((rem+999999)/1000000);
        if(ms<1)ms=1;if(ms>FILE_TIMEOUT_MS)ms=FILE_TIMEOUT_MS;
        struct pollfd pfd={.fd=fd[0],.events=POLLIN|POLLHUP};
        int pr=poll(&pfd,1,ms);
        if(pr<0&&errno!=EINTR)break;
        if(pr<=0)continue;
        ssize_t n=read(fd[0],packet+have,sizeof packet-have);
        if(n>0)have+=(size_t)n;
        else if(n==0)break;
        else if(errno!=EAGAIN&&errno!=EINTR)break;
        if(have>=8){uint32_t count;memcpy(&count,packet,4);
            if(count>=cap||count>MAX_FILE_BYTES)break;
            if(have>=8+count)break;
        }
    }
    close(fd[0]);
    int status=0;pid_t got=waitpid(child,&status,WNOHANG);
    uint32_t count=0,source_status=999;
    if(have>=8){memcpy(&count,packet,4);memcpy(&source_status,packet+4,4);}
    int complete=have>=8&&count<cap&&have>=8+count;
    /* A complete one-write packet proves this child finished the /proc read;
     * if its exit has not yet been reaped, track only the reap, not a path
     * blocker. Incomplete children still block another fork for this path. */
    if(got==0)track_child(child,complete?"":path);
    const char *result=!complete?"timeout_or_incomplete_packet":
        source_status==0?"ok":source_status==1?"truncated":
        source_status==101?"open_error":source_status==102?"read_error":"child_error";
    size_t used=complete?count:0;
    if(used)memcpy(out,packet+8,used);
    out[used]=0;
    for(size_t i=0;i<used;i++)if((unsigned char)out[i]<32&&out[i]!='\n'&&out[i]!='\t')out[i]=' ';
    add("FILE_END role=%s kind=%s status=%s child_pid=%ld reaped=%d bytes=%zu end_ns=%llu\n",
        role,kind,result,(long)child,got==child,used,(unsigned long long)mono_ns());
    if(used)add("FILE_DATA role=%s kind=%s begin\n%.*s\nFILE_DATA_END role=%s kind=%s\n",
                role,kind,(int)used,out,role,kind);
    return !strcmp(result,"ok")?(int)used:-1;
}
static long decimal(const char **cursor){
    const char *p=*cursor;while(*p==' '||*p=='\t')p++;
    if(*p<'0'||*p>'9')return -1;
    char *end;long value=strtol(p,&end,10);
    if(end==p||value<1||value>1000000)return -1;
    *cursor=end;return value;
}
static void path_read(const char *role,long pid,long tid,const char *kind,
                      size_t cap,uint64_t deadline,char *out) {
    char path[192];snprintf(path,sizeof path,"/proc/%ld/task/%ld/%s",pid,tid,kind);
    bounded_read(path,out,cap,deadline,role,kind);
}
static void target(const char *role,long pid,long tid,uint64_t deadline) {
    if(pid<=0||tid<=0){add("TARGET role=%s status=identity_unknown\n",role);return;}
    add("TARGET role=%s pid=%ld tid=%ld identity_source=%s\n",role,pid,tid,
        !strcmp(role,"proc97_child")?"procfs_children":"guest_tmp_marker");
    char out[1200];
    path_read(role,pid,tid,"cmdline",256,deadline,out);
    path_read(role,pid,tid,"status",700,deadline,out);
    path_read(role,pid,tid,"wchan",128,deadline,out);
    path_read(role,pid,tid,"syscall",256,deadline,out);
    path_read(role,pid,tid,"stack",1100,deadline,out);
    path_read(role,pid,tid,"stat",256,deadline,out); /* last: r3 blocked here */
}
static long parse_identity(const char *path,const char *role,uint64_t deadline,long *tid) {
    char buf[256];int n=bounded_read(path,buf,sizeof buf,deadline,role,"identity");
    if(n<=0)return -1;
    const char *p=buf;
    if(!strcmp(role,"file100")){
        const char prefix[]="F100FILE_READY_V2 ";
        if(strncmp(p,prefix,sizeof prefix-1))return -1;
        p+=sizeof prefix-1;
    }
    long pid=decimal(&p);if(pid<=0)return -1;
    if(tid){long second=decimal(&p);if(second<=0)return -1;*tid=second;}
    while(*p==' '||*p=='\t'||*p=='\n'||*p=='\r')p++;
    if(*p)return -1;
    return pid;
}
static void capture(unsigned char *map,uint64_t sequence,uint32_t step,uint32_t done){
    uint64_t begin=mono_ns(),deadline=begin+TOTAL_CAPTURE_NS;
    text_len=0;drop_count=0;
    add("PCDIAG_BEGIN version=1 guest_monotonic_ns=%llu pending=%u done=%u channel=/proc\n",
        (unsigned long long)begin,step,done);
    long key_tid=-1;
    long key_pid=parse_identity("/tmp/fx3-keyworker96.identity","key96",deadline,&key_tid);
    long file_pid=parse_identity("/tmp/fx3-file100-ready-v2","file100",deadline,0);
    long obs_pid=parse_identity("/tmp/fx3-proc97-observer.identity","proc97",deadline,0);
    target("key96",key_pid,key_tid,deadline);
    target("mainim",key_pid,key_pid,deadline);
    target("file100",file_pid,file_pid,deadline);
    target("proc97_shell",obs_pid,obs_pid,deadline);
    if(obs_pid>0){
        char children[256],path[192];
        snprintf(path,sizeof path,"/proc/%ld/task/%ld/children",obs_pid,obs_pid);
        int n=bounded_read(path,children,sizeof children,deadline,"proc97_shell","children");
        if(n>0){char *p=children;for(unsigned i=0;i<4&&*p;i++){
            char *end;long child=strtol(p,&end,10);if(end==p)break;p=end;
            target("proc97_child",child,child,deadline);
        }}else add("TARGET role=proc97_child status=children_unknown\n");
    }
    add("PCDIAG_END guest_monotonic_ns=%llu elapsed_ns=%llu outstanding_children=%u dropped_text=%u\n",
        (unsigned long long)mono_ns(),(unsigned long long)(mono_ns()-begin),pending_count,drop_count);
    unsigned char *slot=map+SLOT0;
    uint64_t odd=sequence*2-1,even=sequence*2;
    memcpy(slot,&odd,8);memcpy(slot+SLOT_BYTES-8,&odd,8);
    uint32_t len=(uint32_t)text_len;
    memcpy(slot+8,&len,4);memcpy(slot+12,&step,4);memcpy(slot+16,&done,4);
    memcpy(slot+24,&begin,8);uint64_t hash=fnv(text,text_len);
    memcpy(slot+32,&hash,8);memcpy(slot+40,text,text_len);
    __atomic_thread_fence(__ATOMIC_RELEASE);
    memcpy(slot+SLOT_BYTES-8,&even,8);
    __atomic_thread_fence(__ATOMIC_RELEASE);
    memcpy(slot,&even,8);
    memcpy(map+DIAG_HEADER,&(uint64_t){SNAP_MAGIC},8);
    memcpy(map+DIAG_HEADER+8,&sequence,8);
    memcpy(map+DIAG_HEADER+16,&pending_count,4);
    memcpy(map+DIAG_HEADER+20,&drop_count,4);
}
int main(void){
    int fd=open("/dev/mem",O_RDWR|O_SYNC);if(fd<0)return 2;
    unsigned char *map=mmap(0,KEY_BYTES,PROT_READ|PROT_WRITE,MAP_SHARED,fd,KEY_PHYS);
    close(fd);if(map==MAP_FAILED)return 3;
    uint64_t seq=0,first_seen=0;uint32_t old_step=0;unsigned attempts=0;
    for(;;){
        reap_children();uint64_t magic;memcpy(&magic,map,8);
        if(magic!=KEY_MAGIC){usleep(200000);continue;}
        uint32_t step,done;memcpy(&step,map+8,4);memcpy(&done,map+24,4);
        uint64_t now=mono_ns();
        if(step==0||step==done||step>4096){old_step=0;attempts=0;first_seen=0;usleep(200000);continue;}
        if(step!=old_step){old_step=step;attempts=0;first_seen=now;}
        uint64_t interval=attempts?2000000000ULL:1000000000ULL;
        if(now-first_seen>=interval && attempts<MAX_SNAPSHOTS_PER_COMMAND){
            capture(map,++seq,step,done);attempts++;
            first_seen=mono_ns(); /* bounded periodic passive sample while pending */
        }
        usleep(200000);
    }
}
