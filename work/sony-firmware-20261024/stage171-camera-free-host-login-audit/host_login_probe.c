/* Own host identity only. No USB/IOKit APIs, protected volume, TCC API,
 * process signals, privilege changes, audit setters or credentials. */
#include <Security/AuthSession.h>
#include <bsm/audit.h>
#include <libproc.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <fcntl.h>
#include <unistd.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

#define GRANT "fx3-host-audit-20261028-01"
#define ROOT_BASE "/private/var/root/fx3-host-audits"
#define ROOT_DIR ROOT_BASE "/" GRANT
#define ROOT_PROBE ROOT_DIR "/probe"
#define ROOT_LEASE ROOT_DIR "/entry.once"

static int deny(const char *message,int code) {
    fprintf(stderr,"FX3_HOST_AUDIT_DENIED:%s\n",message);return code;
}

int main(int argc,char **argv) {
    if(argc==1) {puts("{\"state\":\"PLAN_ONLY\",\"camera_operations\":0}");return 0;}
    int root=argc==2 && !strcmp(argv[1],"--root");
    int user=argc==2 && !strcmp(argv[1],"--user");
    if(!root && !user)return deny("fixed_mode_only",64);
    if(root && geteuid()!=0)return deny("administrator_required",77);
    if(user && geteuid()==0)return deny("user_baseline_not_root",77);
    if(root) {
        char self[4096]={0};struct stat executable,dir,base;
        if(proc_pidpath(getpid(),self,sizeof(self))<=0 || strcmp(self,ROOT_PROBE) ||
           lstat(self,&executable) || !S_ISREG(executable.st_mode) || executable.st_uid ||
           executable.st_nlink!=1 || (executable.st_mode&0777)!=0500 ||
           lstat(ROOT_DIR,&dir) || !S_ISDIR(dir.st_mode) || dir.st_uid || (dir.st_mode&0777)!=0700 ||
           lstat(ROOT_BASE,&base) || !S_ISDIR(base.st_mode) || base.st_uid || (base.st_mode&0777)!=0700)
            return deny("root_private_identity",65);
        int fd=open(ROOT_LEASE,O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0400);
        if(fd<0)return deny("single_grant_already_consumed_or_unavailable",67);
        char line[96];int n=snprintf(line,sizeof(line),"grant=%s pid=%d\n",GRANT,getpid());
        int ok=n>0 && (size_t)n<sizeof(line) && write(fd,line,(size_t)n)==n && !fsync(fd);
        close(fd);if(!ok)return deny("lease_record_incomplete",65);
    }
    au_id_t auid=(au_id_t)-1;auditinfo_addr_t audit;memset(&audit,0,sizeof(audit));
    errno=0;int auid_rc=getauid(&auid);int auid_errno=errno;
    errno=0;int audit_rc=getaudit_addr(&audit,sizeof(audit));int audit_errno=errno;
    SecuritySessionId session=0;SessionAttributeBits attributes=0;
    OSStatus session_rc=SessionGetInfo(callerSecuritySession,&session,&attributes);
    printf("{\"schema\":1,\"grant_id\":\"%s\",\"mode\":\"%s\",\"pid\":%d,\"ppid\":%d,"
        "\"uid\":%u,\"euid\":%u,\"posix_session_id\":%d,"
        "\"getauid_return\":%d,\"getauid_errno\":%d,\"audit_uid\":%u,"
        "\"getaudit_return\":%d,\"getaudit_errno\":%d,\"audit_session_id\":%u,\"audit_flags\":%llu,"
        "\"security_session_return\":%d,\"security_session_id\":%u,\"security_session_attributes\":%u,"
        "\"has_graphic_access\":%s,\"has_tty\":%s,\"is_remote\":%s,"
        "\"camera_operations\":0,\"privacy_changes\":0}\n",
        GRANT,root?"root":"user",getpid(),getppid(),getuid(),geteuid(),getsid(0),
        auid_rc,auid_errno,(unsigned)auid,audit_rc,audit_errno,(unsigned)audit.ai_asid,
        (unsigned long long)audit.ai_flags,(int)session_rc,(unsigned)session,(unsigned)attributes,
        session_rc==0 && (attributes&sessionHasGraphicAccess)?"true":"false",
        session_rc==0 && (attributes&sessionHasTTY)?"true":"false",
        session_rc==0 && (attributes&sessionIsRemote)?"true":"false");
    return 0;
}
