/* Own process fixture only: anonymous datagram FD, SDK-shaped fake objects.
 * No root launch, IOKit library, camera or real credential negotiation. */
#include "native_session.h"
#include <errno.h>
#include <fcntl.h>
#include <pthread.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

void *fx3_iokit_fixture_create(uint32_t,uint64_t,int);
int fx3_iokit_fixture_dispose(void *);
int fx3_iokit_fixture_reply(void *,const uint8_t *,uint32_t);
int fx3_iokit_fixture_fault(void *,uint32_t,uint32_t);
uint64_t fx3_iokit_fixture_stat(void *,uint32_t);
int fx3_iokit_fixture_clock(void *,uint64_t);
void fx3_iokit_fixture_release(void *);
typedef struct {
    fx3_native_session session;
    fx3_io_context *wire;
    void *fixture;
    pid_t parent;
    int gate,audit;
    _Atomic uint32_t finish,entered;
} environment;
static int peer(void *p) {environment *e=p;return getppid()==e->parent;}
static uint64_t tick(void *p) {environment *e=p;return fx3_iokit_fixture_stat(e->fixture,16);}
static void *watch(void *p) {
    environment *e=p;int released=0,peer_lost=0;
    while(!atomic_load(&e->finish)) {
        if(!peer(e)) {
            atomic_store(e->wire->owner.stop_requested,1);
            if(!peer_lost){char x='P';(void)write(e->audit,&x,1);peer_lost=1;}
        }
        if(fx3_iokit_fixture_stat(e->fixture,17)) {
            if(!atomic_exchange(&e->entered,1)){char x='B';(void)write(e->audit,&x,1);}
            /* Explicit test-gate release only. EOF/parent death never release the call. */
            if(!released) {char go=0;if(read(e->gate,&go,1)==1 && go=='R'){fx3_iokit_fixture_release(e->fixture);released=1;}}
        }
        struct timespec t={0,1000000};nanosleep(&t,NULL);
    }return NULL;
}
static void reply(uint8_t *p,unsigned code) {memset(p,0,516);p[0]=(uint8_t)((~code)>>8);p[1]=(uint8_t)~code;if(code==6)p[4]=1;}
int main(int argc,char **argv) {
    if(argc!=7)return 64;
    int channel=atoi(argv[1]),fault_op=atoi(argv[2]),fault=atoi(argv[3]);
    environment e={.parent=getppid(),.gate=atoi(argv[4]),.audit=atoi(argv[5])};
    if(fcntl(e.gate,F_SETFL,O_NONBLOCK)<0)return 65;
    int no_sigpipe=1;if(setsockopt(channel,SOL_SOCKET,SO_NOSIGPIPE,&no_sigpipe,sizeof(no_sigpipe)))return 65;
    int family=atoi(argv[6]);if(family!=2 && family!=8)return 64;
    e.fixture=fx3_iokit_fixture_create(1,17,0);if(!e.fixture)return 65;e.wire=e.fixture;
    uint8_t nonce[16];memset(nonce,0xa5,16);
    if(fx3_session_init(&e.session,e.wire,nonce,61000000000ull,peer,tick,&e))return 65;
    if(fx3_session_init(&e.session,e.wire,nonce,61000000000ull,peer,tick,&e)!=FX3S_DENIED)return 65;
    atomic_init(&e.finish,0);atomic_init(&e.entered,0);
    pthread_t watcher;if(pthread_create(&watcher,NULL,watch,&e))return 65;
    unsigned messages=0;
    while(messages<64) {
        struct pollfd descriptor={.fd=channel,.events=POLLIN};
        int ready=poll(&descriptor,1,20);
        if(ready<0 && errno==EINTR)continue;
        if(ready<=0){if(!peer(&e))break;continue;}
        uint8_t request[FX3_REQUEST_BYTES]={0},response[FX3_RESPONSE_BYTES]={0};
        struct iovec iov={request,sizeof(request)};
        struct msghdr msg={.msg_iov=&iov,.msg_iovlen=1};
        ssize_t n=recvmsg(channel,&msg,0);
        if(n<0 && errno==EINTR)continue;
        if(n<0)break;
        /* No concatenation/truncation acceptance, ancillary data or automatic retry. */
        if((msg.msg_flags&(MSG_TRUNC|MSG_CTRUNC)) || n!=FX3_REQUEST_BYTES) {
            (void)fx3_session_dispatch(&e.session,request,0,response);
        }else {
            uint64_t next=1000000000ull+(uint64_t)messages*10000000ull;
            uint64_t current=fx3_iokit_fixture_stat(e.fixture,16);if(current>next)next=current;
            if(fx3_iokit_fixture_clock(e.fixture,next))break;
            uint8_t data[516];reply(data,e.session.next_command==1?(unsigned)family:e.session.next_command==3?4:6);
            if(fx3_iokit_fixture_reply(e.fixture,data,516))break;
            if(fx3_iokit_fixture_fault(e.fixture,(uint32_t)fault_op,(uint32_t)fault))break;
            (void)fx3_session_dispatch(&e.session,request,(uint32_t)n,response);
        }
        if(send(channel,response,sizeof(response),0)!=(ssize_t)sizeof(response))break;
        ++messages;
        if(e.session.ended || !peer(&e))break;
    }
    atomic_store(&e.finish,1);if(pthread_join(watcher,NULL))return 66;
    int host_idle=fx3_session_may_dispose_context(&e.session);
    printf("{\"schema\":1,\"mode\":\"own-process-fixture\",\"host_idle\":%s,\"native_pending\":%u,\"calls\":[%llu,%llu,%llu],\"peer_alive\":%s,\"body_completion_proven\":false,\"automatic_STOP\":false}\n",
        host_idle?"true":"false",fx3_io_pending(e.wire),
        (unsigned long long)fx3_iokit_fixture_stat(e.fixture,0),(unsigned long long)fx3_iokit_fixture_stat(e.fixture,1),
        (unsigned long long)fx3_iokit_fixture_stat(e.fixture,2),peer(&e)?"true":"false");fflush(stdout);
    if(!host_idle)return 67;
    return fx3_iokit_fixture_dispose(e.fixture)?68:0;
}
