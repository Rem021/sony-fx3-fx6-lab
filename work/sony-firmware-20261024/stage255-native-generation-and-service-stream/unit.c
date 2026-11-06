/* Own native C with synthetic pipe callbacks only, no IOKit linkage. */
#include "stream.h"
#include <CommonCrypto/CommonHMAC.h>
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "digest_vectors.h"
typedef struct {
    uint64_t now;
    uint32_t writes,reads,controls,disposals,last_command,body_at,kind;
    uint32_t sizes[128],bad_header,zero_body,header_short,fail_write,unreturned,fail_dispose,split;
    int stop_stall;
    uint32_t fixed_digest,service_mode,digest_round,challenge_family;
    uint8_t last[516];
} fake;
static uint64_t now(void *p){return ((fake *)p)->now;}
static fx3_call ok(uint32_t n){return(fx3_call){F_OK,0,1,1,n};}
static fx3_call control(void *p,const uint8_t setup[8],uint32_t ms){
    fake *f=p;assert(ms && ms<=1000);f->controls++;
    assert(setup[0]==0x43 && setup[1]==1);
    if(setup[2]==0 && f->stop_stall)return(fx3_call){F_STALL,-1,1,0,0};
    return ok(0);
}
static fx3_call write_pipe(void *p,const uint8_t *b,uint32_t n,uint32_t ms){
    fake *f=p;assert(ms && ms<=1000);f->writes++;
    if(f->unreturned)return(fx3_call){F_UNKNOWN,0,0,0,0};
    if(f->fail_write)return(fx3_call){F_STALL,-1,1,0,0};
    assert(n==17 || n==516);memcpy(f->last,b,n);
    if(n==17){assert(b[14]==0x1f && b[16]==0);f->kind=1;f->body_at=0;}
    else{
        f->kind=0;f->last_command=(uint16_t)~((uint16_t)b[0]<<8|b[1]);
        if(f->fixed_digest && f->last_command==3){
            assert(f->digest_round<3);const uint8_t *expected=f->service_mode?expect_SERVICE8[f->digest_round]:f->challenge_family==2?expect_MSC2[f->digest_round]:expect_MSC8[f->digest_round];
            assert(!memcmp(b+5,expected,32));f->digest_round++;
        }
    }
    return(fx3_call){F_OK,0,1,0,0};
}
static void packet(uint8_t *b,unsigned code){memset(b,0,516);uint16_t n=(uint16_t)~code;b[0]=(uint8_t)(n>>8);b[1]=(uint8_t)n;}
static fx3_call read_pipe(void *p,uint8_t *b,uint32_t n,uint32_t ms){
    fake *f=p;assert(ms && ms<=1000);assert(f->reads<128);f->sizes[f->reads++]=n;
    if(!f->kind){
        assert(n==516);packet(b,f->last_command==1?(f->challenge_family?f->challenge_family:8):f->last_command==3?4:6);
        if(f->last_command==1)for(unsigned i=4;i<516;i++)b[i]=(uint8_t)i;
        if(f->last_command==5)b[4]=1;
        return ok(516);
    }
    if(f->kind==1){
        assert(n==12);static const uint8_t h[12]={88,0,0,0,16,0,1,0,0,0,0,1};memcpy(b,h,12);
        if(f->bad_header)b[0]=89;
        f->kind=2;return ok(f->header_short?11:12);
    }
    assert(n==88-f->body_at);
    if(f->zero_body)return ok(0);
    uint32_t count=f->split && n>32?32:n;
    for(unsigned i=0;i<count;i++)b[i]=(uint8_t)(f->body_at+i);
    f->body_at+=count;return ok(count);
}
static fx3_call dispose(void *p){fake *f=p;f->disposals++;return(fx3_call){f->fail_dispose?F_IO:F_GONE,-2,1,0,0};}
static const fx3_stream_ops ops={now,control,write_pipe,read_pipe,dispose};
static fx3_identity id(uint64_t registry,uint16_t pid){fx3_identity a={.registry_id=registry,.location=0x1100000,.vid=0x54c,.pid=pid};memset(a.body_tag,0x35,32);return a;}
static void request(uint8_t b[516],unsigned cmd){packet(b,cmd);if(cmd==3){b[4]=1;memset(b+5,0x12,32);}}
static void auth(fx3_stream *s){
    uint8_t a[516],b[516];assert(fx3_stream_start(s)==F_OK);
    for(unsigned round=0;round<3;round++){request(a,1);assert(fx3_stream_auth(s,a,b)==F_OK);request(a,3);assert(fx3_stream_auth(s,a,b)==F_OK);}
    request(a,5);assert(fx3_stream_auth(s,a,b)==F_OK);assert(s->exchange_finished);
}
static void service(fx3_route *r,fx3_stream *s,fake *f){
    fx3_identity m=id(101,0xda1),v=id(202,0x336);fx3_stream first={0};fake mf={.now=1000};
    assert(fx3_route_init(r,&m)==F_OK);assert(fx3_stream_bind(r,&first,&m,1,9000000000,&ops,&mf)==F_OK);
    auth(&first);assert(fx3_stream_retire(&first)==F_OK);
    uint8_t a[516],b[516];request(a,1);assert(fx3_stream_auth(&first,a,b)==F_DENIED);assert(mf.disposals==1);
    assert(fx3_stream_bind(r,s,&v,2,9000000000,&ops,f)==F_OK);auth(s);
}
static void nominal(void){
    fx3_route r={0};fx3_stream s={0};fake f={.now=1000,.split=1,.stop_stall=1};service(&r,&s,&f);
    fx3_read_receipt out={0};uint8_t key[32],body[88],expected[32];memset(key,0x42,32);for(unsigned i=0;i<88;i++)body[i]=(uint8_t)i;
    unsigned start=f.reads;assert(fx3_stream_read0(&s,key,&out)==F_OK);
    assert(f.sizes[start]==12 && f.sizes[start+1]==88 && f.sizes[start+2]==56 && f.sizes[start+3]==24);
    assert(out.bytes==88 && out.reply_valid && out.table_AB_capability && !out.authentication_proven && !out.camera_threads_proven);
    CCHmac(kCCHmacAlgSHA256,key,32,body,88,expected);assert(!memcmp(out.opaque_hmac,expected,32));
    assert(fx3_stream_stop(&s)==F_STALL);assert(fx3_stream_retire(&s)==F_OK);assert(f.disposals==1);
    fx3_identity returned=id(303,0xda1);assert(fx3_route_observe_return(&r,&returned)==F_OK);assert(r.phase==3);
}
static void identity_gates(void){
    fx3_identity a=id(101,0xda1);fx3_route r={0};assert(!fx3_route_init(&r,&a));
    fx3_identity wrong=a;wrong.body_tag[0]^=1;assert(fx3_route_candidate(&r,&wrong,1)==F_DENIED);
    wrong=a;wrong.location++;assert(fx3_route_candidate(&r,&wrong,1)==F_DENIED);
    fx3_stream s={0};fake f={.now=1};assert(!fx3_stream_bind(&r,&s,&a,1,99999999,&ops,&f));auth(&s);assert(!fx3_stream_retire(&s));
    wrong=id(101,0x336);assert(fx3_route_candidate(&r,&wrong,2)==F_DENIED);wrong=id(202,0xda1);assert(fx3_route_candidate(&r,&wrong,2)==F_DENIED);
    wrong=id(202,0x336);assert(!fx3_route_candidate(&r,&wrong,2));
}
static void invalid_header(unsigned short_header){
    fx3_route r={0};fx3_stream s={0};fake f={.now=1000,.bad_header=!short_header,.header_short=short_header};service(&r,&s,&f);
    fx3_read_receipt out={0};uint8_t key[32]={1};unsigned at=f.reads;
    assert(fx3_stream_read0(&s,key,&out)==F_SHAPE);assert(f.reads==at+1 && !f.body_at && !out.reply_valid);
    assert(!memcmp(out.opaque_hmac,(uint8_t[32]){0},32));assert(fx3_stream_retire(&s)==F_UNKNOWN);
}
static void body_zero_and_repeat(void){
    fx3_route r={0};fx3_stream s={0};fake f={.now=1000,.zero_body=1};service(&r,&s,&f);
    fx3_read_receipt out={0};uint8_t key[32]={1};unsigned at=f.reads;
    assert(fx3_stream_read0(&s,key,&out)==F_SHAPE && f.reads==at+2);
    unsigned n=f.reads;assert(fx3_stream_read0(&s,key,&out)==F_DENIED && f.reads==n);
    assert(fx3_stream_retire(&s)==F_UNKNOWN);
}
static void no_progress_or_dispose_while_pending(void){
    fx3_route r={0};fx3_stream s={0};fake f={.now=1000};service(&r,&s,&f);uint8_t key[32]={1};fx3_read_receipt out={0};
    atomic_store(&s.busy,1);assert(fx3_stream_read0(&s,key,&out)==F_BUSY);assert(fx3_stream_retire(&s)==F_BUSY && !f.disposals);atomic_store(&s.busy,0);
    f.unreturned=1;assert(fx3_stream_read0(&s,key,&out)==F_UNKNOWN);assert(fx3_stream_retire(&s)==F_UNKNOWN && !f.disposals);
}
static void deadline_and_disposal_failure(void){
    fx3_route r={0};fx3_stream s={0};fake f={.now=1000};service(&r,&s,&f);f.now=9000000000;
    uint8_t key[32]={1};fx3_read_receipt out={0};unsigned writes=f.writes;assert(fx3_stream_read0(&s,key,&out)==F_TIMEOUT && f.writes==writes);
    f.fail_dispose=1;assert(fx3_stream_retire(&s)==F_UNKNOWN && f.disposals==1);assert(fx3_stream_retire(&s)==F_DENIED && f.disposals==1);
}
static void authentication_stall_is_not_replayable(void){
    fx3_identity a=id(101,0xda1);fx3_route r={0};fx3_stream s={0};fake f={.now=1000};assert(!fx3_route_init(&r,&a));assert(!fx3_stream_bind(&r,&s,&a,1,9000000000,&ops,&f));assert(!fx3_stream_start(&s));
    uint8_t req[516],reply[516];request(req,1);f.fail_write=1;assert(fx3_stream_auth(&s,req,reply)==F_STALL);
    assert(fx3_stream_auth(&s,req,reply)==F_DENIED && f.writes==1);
}
static void fixed_native_digest_integration(void){
    for(unsigned family=2;family<=8;family+=6){
        fx3_identity m=id(101,0xda1),v=id(202,0x336);fx3_route r={0};fx3_stream first={0},second={0};
        fake mf={.now=1000,.fixed_digest=1,.challenge_family=family};assert(!fx3_route_init(&r,&m));assert(!fx3_stream_bind(&r,&first,&m,1,9000000000,&ops,&mf));
        assert(!fx3_stream_start(&first));assert(!fx3_stream_exchange_fixed(&first));assert(mf.digest_round==3 && mf.writes==7 && mf.reads==7);assert(!fx3_stream_retire(&first));
        fake sf={.now=1000,.fixed_digest=1,.service_mode=1};assert(!fx3_stream_bind(&r,&second,&v,2,9000000000,&ops,&sf));
        assert(!fx3_stream_start(&second));assert(!fx3_stream_exchange_fixed(&second));assert(sf.digest_round==3 && sf.writes==7 && sf.reads==7);
    }
}
int main(void){
    nominal();identity_gates();invalid_header(0);invalid_header(1);body_zero_and_repeat();
    no_progress_or_dispose_while_pending();deadline_and_disposal_failure();authentication_stall_is_not_replayable();
    fixed_native_digest_integration();
    puts("PASS 9 native component checks; fixed native digest matches pinned Python reference; synthetic callbacks only; no IOKit");return 0;
}
