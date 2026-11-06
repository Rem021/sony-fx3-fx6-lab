/* Host journal fixture ONLY. No IOKit, camera, root or authority changes. */
#include "global_guard.h"
#include "entry_target.h"
#include <stdio.h>
#include <string.h>
#include <unistd.h>
int main(int argc,char **argv) {
    if(argc!=3 || !getuid() || geteuid()!=getuid() ||
       strncmp(argv[1],FX3_FIXTURE_JOB_ROOT,strlen(FX3_FIXTURE_JOB_ROOT)))return 77;
    uint8_t nonce[16];memset(nonce,0x5a,sizeof(nonce));
    fx3_global_guard g={.fd=-1};int rc=fx3_global_begin(&g,argv[1],(uint32_t)getuid(),nonce,"own-host-guard-fixture");
    printf("{\"begin\":%d,\"count\":%u,\"pid\":%u}\n",rc,g.count,(unsigned)getpid());fflush(stdout);
    if(rc)return 60+rc;
    char mode=argv[2][0];
    if(mode=='H') {if(read(0,&mode,1)!=1)return 89;}
    if(mode!='C' && mode!='U')return 89; /* abrupt own-process exit; OWNED stays */
    rc=fx3_global_finish(&g,mode=='C');printf("{\"finish\":%d,\"clean\":%s}\n",rc,mode=='C'?"true":"false");fflush(stdout);
    return rc?70+rc:0;
}
