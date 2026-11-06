/* Own memory-only unit of the exact native trace function. No IOKit. */
#include "owner_trial.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
typedef struct { fx3_owner_result *report; } native_owner;
#include "claim-trace-function.inc"

int main(void) {
    struct {uint64_t a;fx3_owner_result result;uint64_t z;} guarded;
    memset(&guarded,0,sizeof(guarded));guarded.a=0x1234567890abcdefULL;guarded.z=0xfedcba0987654321ULL;
    native_owner p={.report=&guarded.result};
    int32_t shortage=(int32_t)0xe00002beu;
    assert(trace_claim_result(&p,103,shortage)==shortage);
    assert(guarded.result.event_count==1 && guarded.result.events[0].phase==103 && guarded.result.events[0].raw_return==shortage);
    assert(trace_claim_result(&p,104,0)==0 && guarded.result.events[1].phase==104);
    assert(guarded.result.event_count==2);
    for(uint32_t i=2;i<FX3_OWNER_EVENTS;++i)assert(trace_claim_result(&p,105,0)==0);
    fx3_owner_event last=guarded.result.events[FX3_OWNER_EVENTS-1];
    assert(trace_claim_result(&p,999,shortage)==shortage);
    assert(guarded.result.event_count==FX3_OWNER_EVENTS);
    assert(!memcmp(&last,&guarded.result.events[FX3_OWNER_EVENTS-1],sizeof(last)));
    assert(guarded.a==0x1234567890abcdefULL && guarded.z==0xfedcba0987654321ULL);
    memset(&guarded.result,0,sizeof(guarded.result));
    for(uint32_t i=0;i<61;++i)trace_claim_result(&p,101,0);
    assert(guarded.result.event_count==61 && 61<FX3_OWNER_EVENTS);
    printf("{\"status\":\"PASS_EXACT_TRACE_RETURN_BITS_ORDER_CAPACITY_AND_BUDGET\",\"checks\":3,\"device_operations\":0}\n");
    return 0;
}
