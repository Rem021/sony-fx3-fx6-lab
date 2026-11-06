/* Ordinary-user host-only journal test in a fresh test directory. */
#include "global_guard.h"
#include <assert.h>
#include <stdio.h>
#include <sys/wait.h>
#include <unistd.h>
int main(int argc,char **argv){
    assert(argc==2 && geteuid()!=0);
    pid_t child=fork();assert(child>=0);
    if(!child){
        fx3_global_guard g={.fd=-1};uint8_t nonce[16]={1};
        assert(fx3_global_begin(&g,argv[1],(uint32_t)geteuid(),nonce,"offline-unknown-263")==G_OK);
        assert(fx3_global_finish(&g,0)==G_OK);_exit(0);
    }
    int status=0;assert(waitpid(child,&status,0)==child && WIFEXITED(status) && !WEXITSTATUS(status));
    fx3_global_guard again={.fd=-1};uint8_t nonce[16]={2};
    assert(fx3_global_begin(&again,argv[1],(uint32_t)geteuid(),nonce,"offline-next-263")==G_STALE);
    assert(again.fd==-1);
    puts("PASS: child exited; durable UNKNOWN still denies a fresh owner without camera or root");
    return 0;
}
