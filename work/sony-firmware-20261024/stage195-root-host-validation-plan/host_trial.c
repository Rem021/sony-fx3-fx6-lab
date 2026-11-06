/* HOST ONLY: self/process metadata, private local files, AF_UNIX and 64B RAM.
 * No IOKit/USB API, device driver, disk partition, network IP or firmware code.
 * Root artifact is built but not executed without its specific new approval. */
#include "host_target.h"
#include "entry_shared.h"
#include "frame_io.h"
#include "global_guard.h"
#include "helper_hello.h"
#include "host_login.h"
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mount.h>
#include <sys/stat.h>
#include <time.h>
#include <unistd.h>
static void put32(uint8_t *p,uint32_t x){for(unsigned i=0;i<4;++i)p[i]=(uint8_t)(x>>(8*i));}
static void put64(uint8_t *p,uint64_t x){for(unsigned i=0;i<8;++i)p[i]=(uint8_t)(x>>(8*i));}
static uint32_t get32(const uint8_t *p){return (uint32_t)p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static int hex(const char *s,uint8_t *out){
    if(strlen(s)!=32)return -1;
    for(unsigned i=0;i<16;++i){
        char a=s[2*i],b=s[2*i+1];
        if(!((a>='0'&&a<='9')||(a>='a'&&a<='f')) || !((b>='0'&&b<='9')||(b>='a'&&b<='f')))return -1;
        char pair[3]={a,b,0};out[i]=(uint8_t)strtoul(pair,NULL,16);
    }return 0;
}
static int deny(const char *s,int code){fprintf(stderr,"HOST_ONLY_DENIED:%s\n",s);return code;}
static void pause_short(void){struct timespec p={0,5000000};nanosleep(&p,NULL);}
static int directory(const char *p,uint32_t uid,int check_fs){
    int fd=open(p,O_RDONLY|O_DIRECTORY|O_NOFOLLOW|O_CLOEXEC);struct stat st;struct statfs fs;
    if(fd<0)return -1;
    if(fstat(fd,&st) || !S_ISDIR(st.st_mode) || st.st_uid!=uid || (st.st_mode&07777)!=0700 ||
        fstatfs(fd,&fs) || (check_fs && (fs.f_flags&MNT_IGNORE_OWNERSHIP))){close(fd);return -1;}
    return fd;
}
static int observer(const fx3_entry_grant *g,uint32_t owner){
    uint32_t uid;uint64_t sec,usec;
    return !fx3_entry_pid_info(g->observer_pid,&uid,&sec,&usec) && uid==owner && sec==g->observer_birth_sec && usec==g->observer_birth_usec;
}
static int claim(int dir,const char *name,const uint8_t nonce[16]){
    int fd=openat(dir,name,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0400);if(fd<0)return -1;
    int ok=write(fd,nonce,16)==16 && !fsync(fd);if(close(fd))ok=0;if(fsync(dir))ok=0;return ok?0:-1;
}
static void header(uint8_t *p,const char magic[8],uint32_t bytes,uint32_t kind,const fx3_receipt_meta *m){
    memcpy(p,magic,8);put32(p+8,1);put32(p+12,bytes);put32(p+16,kind);put32(p+20,HOST_SCOPE);
    put32(p+24,m->uid);put32(p+28,m->pid);put64(p+32,m->sec);put64(p+40,m->usec);memcpy(p+48,m->nonce,16);
    CC_SHA256(m->grant,(CC_LONG)strlen(m->grant),p+64);
}
static int archive_write(int dir,const uint8_t data[256],uint32_t uid){
    int fd=openat(dir,"host-result.bin",O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW|O_CLOEXEC,0600);if(fd<0)return -1;
    struct stat st;
    int ok=!fstat(fd,&st) && S_ISREG(st.st_mode) && st.st_uid==uid && st.st_nlink==1 && (st.st_mode&07777)==0600 &&
        write(fd,data,256)==256 && !fsync(fd);
    if(close(fd))ok=0;if(fsync(dir))ok=0;return ok?0:-1;
}
static int archive_read(int dir,uint8_t data[256],uint32_t uid){
    int fd=openat(dir,"host-result.bin",O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);if(fd<0)return -1;
    struct stat a,b;uint8_t hash[32],grant[32];
    int ok=!fstat(fd,&a) && S_ISREG(a.st_mode) && a.st_uid==uid && a.st_nlink==1 && (a.st_mode&07777)==0600 &&
        a.st_size==256 && pread(fd,data,256,0)==256 && !fstat(fd,&b) && a.st_dev==b.st_dev && a.st_ino==b.st_ino &&
        a.st_size==b.st_size && a.st_mtimespec.tv_sec==b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec==b.st_mtimespec.tv_nsec;
    if(close(fd))ok=0;if(!ok)return -1;
    CC_SHA256(data,224,hash);CC_SHA256(HOST_TRIAL_ID,strlen(HOST_TRIAL_ID),grant);
    if(memcmp(data,"FX3HST01",8) || get32(data+8)!=1 || get32(data+12)!=256 || get32(data+16)!=1 ||
        get32(data+20)!=HOST_SCOPE || get32(data+24)!=uid || memcmp(data+64,grant,32) || memcmp(data+224,hash,32))return -1;
    return 0;
}
int main(int argc,char **argv){
    int query=argc>1 && !strcmp(argv[1],"readback");
    if(argc<2 || (!query && strcmp(argv[1],"trial")))return deny("fixed_mode",64);
    uint32_t self_uid=(uint32_t)geteuid(),owner;
    const char *protected_dir,*frame_path,*socket_path;int check_fs;
#ifdef HOST_FIXTURE
    if(argc!=6 || getuid()!=geteuid() || !getuid())return deny("unprivileged_fixture_only",64);
    protected_dir=argv[5];frame_path=argv[2];socket_path=argv[4];owner=(uint32_t)getuid();check_fs=0;
    char resolved[4096];
    if(!realpath(frame_path,resolved) || strncmp(resolved,HOST_FIXTURE_ROOT,strlen(HOST_FIXTURE_ROOT)) ||
        !realpath(protected_dir,resolved) || strncmp(resolved,HOST_FIXTURE_ROOT,strlen(HOST_FIXTURE_ROOT)) ||
        strncmp(socket_path,HOST_FIXTURE_SOCKETS,strlen(HOST_FIXTURE_SOCKETS)))return deny("fixture_paths",65);
#else
    if(argc!=5 || getuid()!=0 || geteuid()!=0)return deny("administrator_host_only",77);
    protected_dir=HOST_PROTECTED;owner=501;check_fs=1;
    frame_path=query?HOST_JOB "/query.bin":HOST_JOB "/trial.bin";
    socket_path=query?HOST_JOB "/query.sock":HOST_JOB "/trial.sock";
    if(strcmp(argv[2],frame_path) || strcmp(argv[4],socket_path))return deny("fixed_paths",65);
    char own_path[4096];struct stat exe,console;
    if(fx3_entry_pid_path(getpid(),own_path,sizeof(own_path)) || strcmp(own_path,HOST_HELPER) || lstat(HOST_HELPER,&exe) ||
        !S_ISREG(exe.st_mode) || exe.st_uid || exe.st_nlink!=1 || (exe.st_mode&07777)!=0500 ||
        stat("/dev/console",&console) || console.st_uid!=owner)return deny("root_self_and_console",65);
    int base=directory(HOST_BASE,0,1),job=directory(HOST_JOB,owner,1);
    if(base<0 || job<0)return deny("fixed_directories",65);close(base);close(job);
#endif
    uint8_t nonce[16];if(hex(argv[3],nonce))return deny("nonce",64);
    fx3_host_login login;fx3_host_login_read(&login);
#ifndef HOST_FIXTURE
    if(!fx3_host_login_valid(&login,owner))return deny("GUI_TTY_audit_identity",65);
#endif
    int dir=directory(protected_dir,self_uid,check_fs);if(dir<0)return deny("protected_directory",65);
    int fd=open(frame_path,O_RDWR|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);struct stat st;
    if(fd<0 || fstat(fd,&st) || !S_ISREG(st.st_mode) || st.st_uid!=owner || st.st_nlink!=1 ||
        (st.st_mode&07777)!=0600 || st.st_size!=4096)return deny("frame_identity",65);
    fx3_entry_frame *f=calloc(1,4096);if(!f || pread(fd,f,4096,0)!=4096)return deny("private_frame",65);
    fx3_frame_io io={.fd=fd,.identity=st};atomic_init(&io.failed,0);fx3_entry_grant *g=&f->grant;
    if(g->schema!=3 || g->mode!=1 || g->owner_uid!=owner || g->fixture_fail || g->fixture_option || g->fixture_block ||
        f->control.abi!=4 || memcmp(g->nonce,nonce,16) || !observer(g,owner))return deny("host_grant",65);
    if(claim(dir,query?"readback.once":"trial.once",nonce))return deny("single_attempt_consumed",67);
    if(fx3_entry_claim(f,nonce))return deny("frame_claim",65);
    uint32_t uid;uint64_t sec,usec;
    if(fx3_entry_pid_info(getpid(),&uid,&sec,&usec) || uid!=self_uid)return deny("self_identity",65);
    g->native_pid=getpid();g->birth_sec=sec;g->birth_usec=usec;atomic_store(&g->helper_ready,1);
    if(fx3_frame_write(&io,f))return deny("ready",65);
    uint64_t deadline=fx3_entry_clock_ns()+5000000000ull,ack_deadline=fx3_entry_clock_ns()+2000000000ull;
    while(!atomic_load(&g->parent_ack) && !atomic_load(&f->control.stop_requested) && observer(g,owner) && fx3_entry_clock_ns()<ack_deadline){fx3_frame_control(&io,f);pause_short();}
    if(!atomic_load(&g->parent_ack) || atomic_load(&f->control.stop_requested) || !observer(g,owner) || fx3_entry_clock_ns()>=ack_deadline)return deny("parent_ack",68);
    fx3_channel_config peer={.path=socket_path,.peer_uid=owner,.peer_pid=g->observer_pid,.peer_sec=g->observer_birth_sec,
        .peer_usec=g->observer_birth_usec,.deadline_ns=deadline,.generation=1,.scope=1,.fd=-1};memcpy(peer.nonce,nonce,16);
    fx3_receipt_meta meta={.uid=uid,.pid=getpid(),.sec=sec,.usec=usec,.nonce=nonce,.grant=HOST_TRIAL_ID};
    if(fx3_channel_connect(&peer) || fx3_helper_hello(&peer,&meta,deadline) || fx3_receipt_peer_ack(&peer,deadline))return deny("peer_image_ACK",68);
    fx3_frame_control(&io,f);
    if(atomic_load(&io.failed) || atomic_load(&f->control.stop_requested) || !observer(g,owner) || fx3_entry_clock_ns()>=deadline)return deny("stopped_before_host_work",68);
    uint8_t archive[256]={0},wire[388]={0};uint32_t bytes;
    if(!query){
        fx3_global_guard guard={.fd=-1};char journal[4096];
        if(snprintf(journal,sizeof(journal),"%s/host-only.journal",protected_dir)>=(int)sizeof(journal))return deny("host_journal_path",65);
        if(fx3_global_begin(&guard,journal,self_uid,nonce,HOST_TRIAL_ID))return deny("host_journal",69);
        uint8_t payload[64]={0};memcpy(payload,nonce,16);memset(payload+16,0xa5,32);put32(payload+48,uid);put32(payload+52,getpid());put64(payload+56,sec);
        header(archive,"FX3HST01",256,1,&meta);CC_SHA256(payload,sizeof(payload),archive+96);
        put32(archive+128,1);put32(archive+132,(uint32_t)login.auid_return);put32(archive+136,login.audit_uid);
        put32(archive+140,login.audit_record_uid);put32(archive+144,login.audit_session);put32(archive+148,login.security_session);
        put32(archive+152,login.attributes);put32(archive+156,((login.attributes&sessionHasGraphicAccess)?1:0)|((login.attributes&sessionHasTTY)?2:0)|((login.attributes&sessionIsRemote)?4:0));
        put32(archive+160,1);put32(archive+176,64);
        if(fx3_global_finish(&guard,1))return deny("host_journal_finish",69);
        CC_SHA256(archive,224,archive+224);
        if(archive_write(dir,archive,self_uid))return deny("private_archive",70);
        bytes=256;put32(wire,bytes);memcpy(wire+4,archive,bytes);
    }else{
        if(archive_read(dir,archive,self_uid))return deny("protected_readback",70);
        bytes=384;put32(wire,bytes);header(wire+4,"FX3HRD01",bytes,2,&meta);memcpy(wire+100,archive,256);CC_SHA256(wire+4,352,wire+356);
    }
    int delivered=!fx3_receipt_send_bytes(&peer,wire,bytes+4,deadline);
    atomic_store(&g->native_completed,1);g->native_return=delivered?0:2;fx3_frame_write(&io,f);
    close(peer.fd);close(fd);close(dir);
    printf("{\"host_only\":true,\"mode\":\"%s\",\"pid\":%u,\"record_delivered\":%s,\"device_operations\":0",query?"readback":"trial",(unsigned)getpid(),delivered?"true":"false");
    fx3_host_login_print_json(&login);printf("}\n");return delivered?0:71;
}
