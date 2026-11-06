#include "bound_signal.h"
#include <errno.h>
#include <mach/mach.h>
#include <mach/task_info.h>
#include <string.h>
#include <unistd.h>
int fx3_host_same_process(const fx3_host_identity *e){
    if(!e || e->pid<=1 || e->pid==getpid() || !e->path || !e->sec || e->usec>=1000000){errno=EINVAL;return -1;}
    struct proc_bsdinfo b={0};errno=0;
    int n=proc_pidinfo(e->pid,PROC_PIDTBSDINFO,0,&b,sizeof(b));
    if(n!=(int)sizeof(b))return errno==ESRCH?0:-1;
    if(b.pbi_pid!=(uint32_t)e->pid || b.pbi_uid!=e->uid || b.pbi_start_tvsec!=e->sec || b.pbi_start_tvusec!=e->usec)return 0;
    char path[PROC_PIDPATHINFO_MAXSIZE]={0};errno=0;
    if(proc_pidpath(e->pid,path,sizeof(path))<=0)return errno==ESRCH?0:-1;
    return strcmp(path,e->path)?0:1;
}
int fx3_host_capture_token(const fx3_host_identity *e,audit_token_t *out){
    if(!out || fx3_host_same_process(e)!=1){errno=ESRCH;return -1;}
    mach_port_name_t name=MACH_PORT_NULL;
    kern_return_t kr=task_name_for_pid(mach_task_self(),e->pid,&name);
    if(kr!=KERN_SUCCESS){errno=EPERM;return -1;}
    audit_token_t data={0};mach_msg_type_number_t count=TASK_AUDIT_TOKEN_COUNT;
    kr=task_info(name,TASK_AUDIT_TOKEN,(task_info_t)&data,&count);
    mach_port_deallocate(mach_task_self(),name);
    if(kr!=KERN_SUCCESS || count!=TASK_AUDIT_TOKEN_COUNT){errno=EPERM;return -1;}
    audit_token_t token;memcpy(&token,&data,sizeof(token));
    if(token.val[5]!=(uint32_t)e->pid || token.val[1]!=e->uid || fx3_host_same_process(e)!=1){errno=ESRCH;return -1;}
    char path[PROC_PIDPATHINFO_MAXSIZE]={0};
    if(proc_pidpath_audittoken(&token,path,sizeof(path))<=0 || strcmp(path,e->path)){errno=ESRCH;return -1;}
    *out=token;return 0;
}
int fx3_host_signal_token(const audit_token_t *token,int sig){
    if(!token){errno=EINVAL;return -1;}
    audit_token_t copy=*token;
    return proc_signal_with_audittoken(&copy,sig);
}
