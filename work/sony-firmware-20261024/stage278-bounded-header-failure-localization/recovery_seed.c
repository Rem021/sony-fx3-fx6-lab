/* Own v1 journal seed and observer. Never root; exits cooperatively on stdin. */
#include "global_guard.h"
#include "entry_shared.h"
#include "entry_target.h"
#include <CommonCrypto/CommonDigest.h>
#include <assert.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>
static void p32(uint8_t *p,uint32_t n){for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(n>>(8*i));}
static void p64(uint8_t *p,uint64_t n){p32(p,(uint32_t)n);p32(p+4,(uint32_t)(n>>32));}
static void identity(uint8_t *p,pid_t pid){
    uint32_t uid=0;uint64_t sec=0,usec=0;assert(!fx3_entry_pid_info((uint32_t)pid,&uid,&sec,&usec));
    p32(p,(uint32_t)pid);p32(p+4,uid);p64(p+8,sec);p64(p+16,usec);
}
int main(int argc,char **argv){
    assert(argc==4 && getuid()==geteuid() && getuid()!=0);
    assert(!strncmp(argv[1],FX3_FIXTURE_JOB_ROOT,strlen(FX3_FIXTURE_JOB_ROOT)) &&
           !strncmp(argv[2],FX3_FIXTURE_JOB_ROOT,strlen(FX3_FIXTURE_JOB_ROOT)));
    fx3_global_guard g={.fd=-1};uint8_t nonce[16];memset(nonce,'P',16);
    assert(fx3_global_begin(&g,argv[1],(uint32_t)getuid(),nonce,"fixture-prior-SERVICE")==G_OK);
    int release[2];assert(!pipe(release));pid_t observer=fork();assert(observer>=0);
    if(!observer){close(release[1]);close(g.fd);char c;assert(read(release[0],&c,1)==1);close(release[0]);_exit(0);}
    close(release[0]);uint8_t b[256]={0};memcpy(b,"FX3RCV01",8);p32(b+8,1);p32(b+12,256);
    identity(b+16,getpid());identity(b+40,observer);memcpy(b+64,nonce,16);
    CC_SHA256("fixture-prior-SERVICE",(CC_LONG)strlen("fixture-prior-SERVICE"),b+80);
    memset(b+112,'A',32);memset(b+144,'E',32);p64(b+176,50);p64(b+184,100);p64(b+192,500);
    p32(b+200,0x01100000);p32(b+204,(uint32_t)strtoul(argv[3],NULL,10));CC_SHA256(b,224,b+224);
    int fd=open(argv[2],O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0400);assert(fd>=0);
    assert(write(fd,b,256)==256 && !fsync(fd));close(fd);
    puts("ready");fflush(stdout);char cmd;assert(read(STDIN_FILENO,&cmd,1)==1);
    assert(write(release[1],"x",1)==1);close(release[1]);int status=0;
    assert(waitpid(observer,&status,0)==observer && WIFEXITED(status) && !WEXITSTATUS(status));
    _exit(0); /* Old v1 OWNED persists. No signals or camera operation. */
}
