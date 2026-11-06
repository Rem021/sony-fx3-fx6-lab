#include "transition_identity.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static fx3_identity source(void){fx3_identity x={.registry_id=100,.location=0x01100000,.vid=0x54c,.pid=0x0da1,.physical_port=500,.logical_port=501,.identity_kind=FX3_ID_SERIAL};memset(x.serial_tag,'A',32);return x;}
static fx3_identity service(void){fx3_identity x=source();x.registry_id=200;x.pid=0x0336;x.location=0x01200000;x.logical_port=502;x.identity_kind=FX3_ID_CONTROLLED_PORT;memset(x.serial_tag,0,32);return x;}
static fx3_port_witness armed(void){fx3_port_witness w={0};fx3_identity a=source();uint8_t n[16];memset(n,'N',16);assert(!fx3_witness_init(&w,&a,n));assert(!fx3_witness_arm(&w,2,100,3000000000ull));return w;}
int main(void){
    fx3_identity a=source(),b=service(),c=source(),m=source();c.registry_id=300;m.registry_id=250;m.pid=0x096f;
    fx3_port_witness w=armed();assert(fx3_witness_sample(&w,2,FX3T_OK,&a,101)==FX3T_BUSY);
    assert(fx3_witness_sample(&w,2,FX3T_GONE,NULL,102)==FX3T_GONE);
    assert(!fx3_witness_sample(&w,2,FX3T_OK,&b,103));assert(fx3_witness_matches(&w,&b,2));
    assert(!fx3_witness_arm(&w,1,200,3000000000ull));assert(fx3_witness_sample(&w,1,FX3T_OK,&b,201)==FX3T_BUSY);
    assert(fx3_witness_sample(&w,1,FX3T_OK,&m,202)==FX3T_BUSY);
    assert(!fx3_witness_sample(&w,1,FX3T_OK,&c,203));assert(fx3_witness_matches(&w,&c,1));
    assert(w.state==FX3_W_RETURNED && w.service_kind==FX3_ID_CONTROLLED_PORT && !memcmp(w.origin_serial_tag,a.serial_tag,32));
    w=armed();assert(fx3_witness_sample(&w,2,FX3T_OK,&m,101)==FX3T_DENIED && w.state==FX3_W_FAILED);
    w=(fx3_port_witness){0};uint8_t nonce[16]={1};assert(!fx3_witness_init(&w,&a,nonce));
    assert(fx3_witness_sample(&w,2,FX3T_OK,&b,100)==FX3T_DENIED && !fx3_witness_matches(&w,&b,2));
    for(unsigned bad=0;bad<7;bad++){
        w=armed();fx3_identity x=b;
        if(bad==0)x.physical_port++;
        if(bad==1){x.identity_kind=FX3_ID_SERIAL;memset(x.serial_tag,'B',32);}
        if(bad==2)x.registry_id=100;
        if(bad==3)x.vid=0x1234;
        if(bad==4)memset(x.serial_tag,'A',32); /* No copied source tag on port association. */
        if(bad==5)x.logical_port=0;
        int rc=fx3_witness_sample(&w,2,FX3T_OK,&x,bad==6?99:101);assert(rc!=FX3T_OK && w.state==FX3_W_FAILED);
        assert(fx3_witness_sample(&w,2,FX3T_OK,&b,102)==FX3T_DENIED);
    }
    w=armed();assert(fx3_witness_sample(&w,2,FX3T_OK,&b,w.deadline_ns)==FX3T_TIMEOUT);
    w=armed();for(unsigned i=0;i<50;i++)assert(fx3_witness_sample(&w,2,FX3T_OK,&a,101+i)==FX3T_BUSY);
    assert(fx3_witness_sample(&w,2,FX3T_OK,&b,151)==FX3T_TIMEOUT);
    for(unsigned bad=0;bad<7;bad++){
        w=armed();assert(!fx3_witness_sample(&w,2,FX3T_OK,&b,101));assert(!fx3_witness_arm(&w,1,200,3000000000ull));
        fx3_identity x=bad<3?c:m;
        if(bad==0 || bad==3)memset(x.serial_tag,'B',32);
        if(bad==1 || bad==4)x.registry_id=100;
        if(bad==2 || bad==5)x.location++;
        if(bad==6)x.registry_id=200;
        assert(fx3_witness_sample(&w,1,FX3T_OK,&x,201)==FX3T_DENIED && w.state==FX3_W_FAILED);
    }
    w=armed();b=service();b.identity_kind=FX3_ID_SERIAL;memcpy(b.serial_tag,a.serial_tag,32);
    assert(!fx3_witness_sample(&w,2,FX3T_OK,&b,101) && w.service_kind==FX3_ID_SERIAL);
    puts("PASS bounded association:absent SERVICE serial and companion logical port;096F return-window BUSY and original return serial;unarmed/wrong port/copied or wrong serial/reused node/deadline/sample bounds");return 0;
}
