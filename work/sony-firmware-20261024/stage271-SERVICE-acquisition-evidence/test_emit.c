/* Real ordinary-user serializer/filesystem only. No camera or IOKit backend. */
#include "service_flow.h"
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
static int output=-1;
int fx3_channel_peer(const fx3_channel_config *peer){return peer!=NULL;}
int fx3_receipt_send_bytes(const fx3_channel_config *peer,const uint8_t *p,size_t n,uint64_t deadline){
    (void)peer;(void)deadline;return write(output,p,n)==(ssize_t)n?0:-1;
}
int main(int argc,char **argv){
    if(argc!=4 || getuid()==0 || getuid()!=geteuid())return 64;
    unsigned step=(unsigned)strtoul(argv[3],NULL,10);
    if(step!=0 && step!=203 && step!=210)return 64;
    output=open(argv[2],O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);if(output<0)return 65;
    fx3_channel_config peer={0};uint8_t nonce[16]={1};
    fx3_receipt_meta meta={.uid=getuid(),.pid=(uint32_t)getpid(),.sec=1,.usec=2,.nonce=nonce,.grant="offline-serializer-only"};
    fx3_flow_journal journal={0};
    if(fx3_flow_journal_open(&journal,&peer,&meta,argv[1]))return 66;
    fx3_owner_result owner={0};fx3_owner_control control={0};
    fx3_service_flow flow={.journal=&journal,.owner=&owner,.control=&control};
    flow.service.acquire_step=step;flow.service.acquire_raw_return=step?-536870203:0;
    fx3_call call={.status=step?FX3T_UNKNOWN:FX3T_DENIED,.returned=1,.raw_return=flow.service.acquire_raw_return};
    int rc=fx3_flow_emit(&flow,11,1,&call);
    if(fx3_flow_journal_close(&journal))rc=-1;
    if(close(output))rc=-1;
    return rc?67:0;
}
