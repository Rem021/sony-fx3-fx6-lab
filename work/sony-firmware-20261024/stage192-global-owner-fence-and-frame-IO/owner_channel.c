/* Same-process fixed MSC session transport. No launch, open/claim, reset,
 * device close, handle importer, credential setter or firmware/file command. */
#include "owner_channel.h"
#include "entry_shared.h"
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <poll.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

enum { C_IDLE=0,C_RUNNING=1,C_CLEAN=2,C_HELD=3,C_FAILED=4 };
int fx3_channel_peer(const fx3_channel_config *c) {
    uid_t uid=(uid_t)-1;gid_t group=(gid_t)-1;pid_t pid=0;socklen_t size=sizeof(pid);
    uint32_t actual_uid=0;uint64_t sec=0,usec=0;
    if(!c || c->fd<0)return 0;
    struct pollfd readiness={.fd=c->fd,.events=POLLIN};
    if(poll(&readiness,1,0)<0 || readiness.revents&(POLLHUP|POLLERR|POLLNVAL))return 0;
    if(readiness.revents&POLLIN) {
        int available=0;socklen_t bytes=sizeof(available);
        if(getsockopt(c->fd,SOL_SOCKET,SO_NREAD,&available,&bytes) || bytes!=sizeof(available) || available<=0)return 0;
    }
    return !getpeereid(c->fd,&uid,&group) && uid==c->peer_uid &&
        !getsockopt(c->fd,SOL_LOCAL,LOCAL_PEERPID,&pid,&size) && size==sizeof(pid) &&
        pid>0 && (uint32_t)pid==c->peer_pid &&
        !fx3_entry_pid_info(c->peer_pid,&actual_uid,&sec,&usec) && actual_uid==c->peer_uid &&
        sec==c->peer_sec && usec==c->peer_usec;
}
static int wait_fd(int fd,short events,uint64_t deadline,_Atomic uint32_t *stop) {
    for(;;) {
        uint64_t now=fx3_entry_clock_ns();if(!now || now>=deadline || (stop && atomic_load(stop)))return -1;
        uint64_t ms=(deadline-now+999999)/1000000;int timeout=ms>20?20:(int)ms;
        struct pollfd p={.fd=fd,.events=events};int n=poll(&p,1,timeout);
        if(n<0 && errno==EINTR)continue;
        if(n<0 || p.revents&POLLNVAL)return -1;
        if(n && p.revents&events)return 0;
        if(n && p.revents&(POLLHUP|POLLERR))return -1;
    }
}
int fx3_channel_connect(fx3_channel_config *c) {
    if(!c || c->fd!=-1 || !c->path || !c->peer_pid || !c->peer_sec || c->peer_usec>=1000000 ||
       !c->generation || !c->deadline_ns || c->scope<1 || c->scope>2)return -1;
#ifndef FX3_OWNER_CHANNEL_FIXTURE
    if(geteuid()!=0 || c->peer_uid!=501 || c->scope!=1)return -1; /* no live authentication release */
#endif
    struct sockaddr_un address={.sun_family=AF_UNIX};size_t length=strlen(c->path);
    struct stat before,after;
    if(!length || length>=sizeof(address.sun_path) || lstat(c->path,&before) || !S_ISSOCK(before.st_mode) ||
       before.st_uid!=c->peer_uid || (before.st_mode&0777)!=0600 || before.st_nlink!=1)return -1;
    memcpy(address.sun_path,c->path,length+1);address.sun_len=(uint8_t)(offsetof(struct sockaddr_un,sun_path)+length+1);
    int fd=socket(AF_UNIX,SOCK_STREAM,0);if(fd<0)return -1;
    int flags=fcntl(fd,F_GETFL),yes=1;
    if(flags<0 || fcntl(fd,F_SETFL,flags|O_NONBLOCK) || fcntl(fd,F_SETFD,FD_CLOEXEC) ||
       setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&yes,sizeof(yes))) {close(fd);return -1;}
    int rc=connect(fd,(struct sockaddr *)&address,address.sun_len);
    if(rc && errno==EINPROGRESS) {
        int error=0;socklen_t n=sizeof(error);
        if(wait_fd(fd,POLLOUT,c->deadline_ns,NULL) || getsockopt(fd,SOL_SOCKET,SO_ERROR,&error,&n) || error) {close(fd);return -1;}
    }else if(rc) {close(fd);return -1;}
    c->fd=fd;
    if(lstat(c->path,&after) || before.st_dev!=after.st_dev || before.st_ino!=after.st_ino || !fx3_channel_peer(c)) {
        c->fd=-1;close(fd);return -1;
    }
    return 0;
}
static int peer_callback(void *p) {return fx3_channel_peer(&((fx3_channel_runtime *)p)->config);}
static uint64_t clock_callback(void *unused) {(void)unused;return fx3_entry_clock_ns();}
static int ancillary_reject(struct msghdr *msg) {
    int reject=msg->msg_controllen!=0 || (msg->msg_flags&(MSG_TRUNC|MSG_CTRUNC));
    /* Received SCM_RIGHTS duplicates are closed, never imported or used. */
    for(struct cmsghdr *c=CMSG_FIRSTHDR(msg);c;c=CMSG_NXTHDR(msg,c)) {
        uint8_t *end=(uint8_t *)msg->msg_control+msg->msg_controllen;
        size_t available=(size_t)(end-(uint8_t *)c);
        if(available<sizeof(*c) || c->cmsg_len<CMSG_LEN(0))return -1;
        if(c->cmsg_level==SOL_SOCKET && c->cmsg_type==SCM_RIGHTS) {
            size_t total=c->cmsg_len<available?c->cmsg_len:available;
            if(total<CMSG_LEN(0))return -1;
            size_t bytes=total-CMSG_LEN(0);
            for(size_t at=0;at+sizeof(int)<=bytes;at+=sizeof(int)) {int fd=-1;memcpy(&fd,(uint8_t *)CMSG_DATA(c)+at,sizeof(fd));if(fd>=0)close(fd);}
            if(bytes%sizeof(int))return -1;
        }
        if(c->cmsg_len>available)return -1;
    }
    return reject?-1:0;
}
static int receive_exact(fx3_channel_runtime *r,uint8_t *data,size_t size) {
    if(!peer_callback(r))return -1;
    size_t at=0;
    while(at<size) {
        if(atomic_load(r->wire.owner.stop_requested) || fx3_entry_clock_ns()>=r->config.deadline_ns)return -1;
        /* Darwin externalizes rights before user buffer truncation. Receive
         * one stream byte/control record with storage for the XNU512-FD cap,
         * so discarded ancillary bytes cannot hide installed descriptors. */
        union {struct cmsghdr align;uint8_t bytes[CMSG_SPACE(sizeof(int)*512)];} control={0};
        _Static_assert(sizeof(control)>=2048,"XNU control mbuf bound");
        struct iovec iov={data+at,1};struct msghdr msg={.msg_iov=&iov,.msg_iovlen=1,.msg_control=control.bytes,.msg_controllen=sizeof(control.bytes)};
        ssize_t n=recvmsg(r->config.fd,&msg,MSG_DONTWAIT);
        if(n<0 && (errno==EAGAIN || errno==EINTR)) {
            if(wait_fd(r->config.fd,POLLIN,r->config.deadline_ns,r->wire.owner.stop_requested))return -1;
            continue;
        }
        if(ancillary_reject(&msg) || n<=0)return -1;
        at+=(size_t)n;
    }return 0;
}
static int send_exact(fx3_channel_runtime *r,const uint8_t *data,size_t size) {
    size_t at=0;
    while(at<size) {
        if(!peer_callback(r) || wait_fd(r->config.fd,POLLOUT,r->config.deadline_ns,NULL))return -1;
        ssize_t n=send(r->config.fd,data+at,size-at,MSG_DONTWAIT);
        if(n<0 && (errno==EAGAIN || errno==EINTR))continue;
        if(n<=0)return -1;at+=(size_t)n;
    }return 0;
}
static uint32_t get32(const uint8_t *p) {return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static void put32(uint8_t *p,uint32_t n) {for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(n>>(8*i));}
int fx3_channel_cleanup_allowed(fx3_channel_runtime *r) {
    if(!r || !r->initialized)return 1;
    if(r->initialized==1)return fx3_io_invalidate(&r->wire,r->config.generation)==IO_OK;
    if(fx3_io_pending(&r->wire) || atomic_load(&r->session.busy) || r->wire.start_sent || r->session.started)return 0;
    if(r->session.wire && fx3_session_finish_host(&r->session)!=FX3S_OK)return 0;
    return 1;
}
int fx3_channel_run(fx3_channel_runtime *r,const fx3_channel_config *cfg,const fx3_io_owner *owner,fx3_owner_result *report) {
    if(!r || r->initialized || !cfg || !owner || !report || !fx3_channel_peer(cfg))return -1;
    r->config=*cfg;r->report=report;
    if(fx3_io_bind(&r->wire,owner))return -1;
    r->initialized=1;
    if(fx3_session_init(&r->session,&r->wire,cfg->nonce,cfg->deadline_ns,peer_callback,clock_callback,r))return -1;
    r->initialized=2;
    atomic_store(&report->session_state,C_RUNNING);
    int outcome=0;
    for(unsigned count=0;count<64;++count) {
        uint8_t prefix[4],request[FX3_REQUEST_BYTES],response[FX3_RESPONSE_BYTES+4];
        if(receive_exact(r,prefix,4) || get32(prefix)!=FX3_REQUEST_BYTES || receive_exact(r,request,sizeof(request))) {outcome=-1;break;}
        uint32_t op=get32(request+32);
        if(cfg->scope==1 && op!=FX3S_OBSERVE && op!=FX3S_STATUS && op!=FX3S_END) {outcome=-1;break;}
#ifdef FX3_OWNER_CHANNEL_FIXTURE
        if(cfg->before_request)cfg->before_request(cfg->fixture);
#endif
        put32(response,FX3_RESPONSE_BYTES);
        int status=fx3_session_dispatch(&r->session,request,sizeof(request),response+4);
        if(send_exact(r,response,sizeof(response))) {outcome=-1;break;}
        if(status!=FX3S_OK && status!=FX3S_NATIVE_ERROR && status!=FX3S_INCOMPLETE) {outcome=-1;break;}
        if(r->session.ended)break;
    }
    if(r->wire.owner.published_vendor)atomic_store(r->wire.owner.published_vendor,r->wire.start_sent!=0);
    int safe=fx3_channel_cleanup_allowed(r);
    atomic_store(&report->session_state,safe?(outcome?C_FAILED:C_CLEAN):C_HELD);
    return outcome;
}
