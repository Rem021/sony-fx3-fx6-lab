/* Same-process fixed MSC session transport. No launch, open/claim, reset,
 * device close, handle importer, credential setter or firmware/file command. */
#include "host_transport.h"
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
    if(geteuid()!=0 || c->peer_uid!=501 || c->scope!=2)return -1; /* entry additionally requires a new fixed service permit/profile */
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

int fx3_receipt_peer_ack(const fx3_channel_config *peer,uint64_t deadline) {
    if(!peer)return -1;
    uint8_t data[24]={0};size_t at=0;
    while(at<sizeof(data)) {
        uint64_t now=fx3_entry_clock_ns();if(!now || now>=deadline || !fx3_channel_peer(peer))return -1;
        union {struct cmsghdr align;uint8_t bytes[CMSG_SPACE(512*sizeof(int))];} control={0};
        struct iovec io={data+at,1};
        struct msghdr msg={.msg_iov=&io,.msg_iovlen=1,.msg_control=control.bytes,.msg_controllen=sizeof(control.bytes)};
        ssize_t n=recvmsg(peer->fd,&msg,MSG_DONTWAIT);
        if(n<0 && (errno==EAGAIN || errno==EINTR)) {
            struct pollfd ready={.fd=peer->fd,.events=POLLIN};
            int rc=poll(&ready,1,10);
            if(rc<0 && errno!=EINTR)return -1;
            continue;
        }
        int reject=msg.msg_controllen!=0 || (msg.msg_flags&(MSG_TRUNC|MSG_CTRUNC));
        for(struct cmsghdr *c=CMSG_FIRSTHDR(&msg);c;c=CMSG_NXTHDR(&msg,c)) {
            size_t available=(size_t)((uint8_t *)msg.msg_control+msg.msg_controllen-(uint8_t *)c);
            if(available<sizeof(*c) || c->cmsg_len<CMSG_LEN(0))return -1;
            size_t total=c->cmsg_len<available?c->cmsg_len:available;
            if(c->cmsg_level==SOL_SOCKET && c->cmsg_type==SCM_RIGHTS && total>=CMSG_LEN(0)) {
                size_t bytes=total-CMSG_LEN(0);
                for(size_t k=0;k+sizeof(int)<=bytes;k+=sizeof(int)) {
                    int fd=-1;memcpy(&fd,(uint8_t *)CMSG_DATA(c)+k,sizeof(fd));if(fd>=0)close(fd);
                }
            }
            if(c->cmsg_len>available)return -1;
        }
        if(reject || n!=1)return -1;
        at+=(size_t)n;
    }
    return memcmp(data,"FX3ACK01",8) || memcmp(data+8,peer->nonce,16)?-1:0;
}

int fx3_receipt_send_bytes(const fx3_channel_config *peer,const uint8_t *frame,size_t bytes,uint64_t deadline) {
    if(!peer || !frame || !bytes || bytes>1028)return -1;
    size_t at=0;
    while(at<bytes) {
        uint64_t now=fx3_entry_clock_ns();
        if(!now || now>=deadline || !fx3_channel_peer(peer))return -1;
        struct pollfd ready={.fd=peer->fd,.events=POLLOUT};
        uint64_t remain=(deadline-now+999999)/1000000;
        int n=poll(&ready,1,remain>20?20:(int)remain);
        if(n<0 && errno==EINTR)continue;
        if(n<0 || ready.revents&(POLLHUP|POLLERR|POLLNVAL))return -1;
        if(!n || !(ready.revents&POLLOUT))continue;
        ssize_t sent=send(peer->fd,frame+at,bytes-at,MSG_DONTWAIT);
        if(sent<0 && (errno==EAGAIN || errno==EINTR))continue;
        if(sent<=0)return -1;
        at+=(size_t)sent;
    }
    return 0; /* Delivery is not a camera completion or a release permission. */
}
