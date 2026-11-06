/* Only a child forked by this ordinary-user test can receive a signal. */
#include "bound_signal.h"
#include <assert.h>
#include <errno.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>
int main(void){
    assert(getuid()==geteuid() && geteuid()!=0);
    int pipefd[2];assert(!pipe(pipefd));pid_t child=fork();assert(child>=0);
    if(!child){close(pipefd[1]);char c;while(read(pipefd[0],&c,1)>0){}close(pipefd[0]);_exit(0);}
    close(pipefd[0]);struct proc_bsdinfo b={0};char path[PROC_PIDPATHINFO_MAXSIZE]={0};
    assert(proc_pidinfo(child,PROC_PIDTBSDINFO,0,&b,sizeof(b))==(int)sizeof(b));
    assert(proc_pidpath(child,path,sizeof(path))>0);
    fx3_host_identity expected={child,(uint32_t)geteuid(),b.pbi_start_tvsec,b.pbi_start_tvusec,path};
    fx3_host_identity changed=expected;changed.usec^=1u;audit_token_t rejected={0};
    assert(fx3_host_capture_token(&changed,&rejected)==-1);
    changed=expected;changed.uid++;
    assert(fx3_host_capture_token(&changed,&rejected)==-1);
    changed=expected;changed.path="/not-the-child-executable";
    assert(fx3_host_capture_token(&changed,&rejected)==-1);
    audit_token_t token={0};int captured=fx3_host_capture_token(&expected,&token);
    if(captured){int error=errno;close(pipefd[1]);int status=0;assert(waitpid(child,&status,0)==child);printf("{\"capture_failed\":true,\"errno\":%d,\"child_cleanly_released\":true,\"root_or_USB\":false}\n",error);return 2;}
    audit_token_t wrong=token;wrong.val[7]^=1u;errno=0;
    int rc=fx3_host_signal_token(&wrong,SIGKILL);int error=errno,status=0;
    int observed=waitpid(child,&status,WNOHANG);
    printf("{\"wrong_token_api_return\":%d,\"errno\":%d,\"child_observation\":%d}\n",rc,error,observed);fflush(stdout);
    if(!((rc==-1 && error==ESRCH) || rc==ESRCH) || observed!=0){
        close(pipefd[1]);if(!observed)waitpid(child,&status,0);return 3;
    }
    assert(fx3_host_same_process(&expected)==1);
    assert(!fx3_host_signal_token(&token,SIGKILL));
    assert(waitpid(child,&status,0)==child && WIFSIGNALED(status) && WTERMSIG(status)==SIGKILL);
    assert(fx3_host_same_process(&expected)==0);
    close(pipefd[1]);
    printf("{\"wrong_version_denied\":true,\"own_child_only_signal\":9,\"child_exit_confirmed\":true,\"root_or_USB\":false}\n");
    return 0;
}
