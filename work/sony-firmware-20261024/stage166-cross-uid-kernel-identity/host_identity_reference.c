/* Read-only host API reference; no device APIs, privilege or process signals. */
#include <libproc.h>
#include <errno.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc,char **argv) {
    if(argc!=2)return 64;
    char *end=NULL;long pid=strtol(argv[1],&end,10);
    if(!end || *end || pid<=0 || pid>INT_MAX)return 64;
    struct proc_bsdshortinfo small={0};struct proc_bsdinfo full={0};
    errno=0;int sr=proc_pidinfo((int)pid,PROC_PIDT_SHORTBSDINFO,0,&small,sizeof(small));int se=errno;
    errno=0;int fr=proc_pidinfo((int)pid,PROC_PIDTBSDINFO,0,&full,sizeof(full));int fe=errno;
    printf("{\"pid\":%ld,\"short_return\":%d,\"short_size\":%zu,\"short_errno\":%d,\"short_uid\":%u,"
        "\"full_return\":%d,\"full_size\":%zu,\"full_errno\":%d,\"full_uid\":%u,"
        "\"full_birth_sec\":%llu,\"full_birth_usec\":%llu}\n",
        pid,sr,sizeof(small),se,small.pbsi_uid,fr,sizeof(full),fe,full.pbi_uid,
        (unsigned long long)full.pbi_start_tvsec,(unsigned long long)full.pbi_start_tvusec);
    return 0;
}
