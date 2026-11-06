/* Own ordinary-user fake backend. Original Sony instructions are never executed. */
#include "stream.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
typedef struct {unsigned version,variant,reads,bodies,total,writes,stops;uint64_t now;} fake;
static uint64_t now(void *p){return ++((fake*)p)->now;}
static fx3_call ok(unsigned count,int known){return(fx3_call){.status=FX3T_OK,.returned=1,.count_known=(uint32_t)known,.count=count};}
static fx3_call control(void *p,const uint8_t q[8],uint32_t ms){
 static const uint8_t stop[8]={0x43,1,0,0xc8,0x55,0x28,0,0};assert(ms && !memcmp(q,stop,8));((fake*)p)->stops++;return ok(0,0);
}
static fx3_call write_packet(void *p,const uint8_t *q,uint32_t n,uint32_t ms){
 /* Independent public 12-byte header + ProductInfo category/command/arg0. */
 static const uint8_t expected[17]={5,0,0,0,0x10,0,1,0,0,0,0,0,0,0,0x1f,0,0};
 assert(ms && n==17 && !memcmp(q,expected,17));((fake*)p)->writes++;return ok(0,0);
}
static fx3_call read_packet(void *p,uint8_t *out,uint32_t n,uint32_t ms){
 fake *f=p;assert(ms);f->reads++;
 if(f->reads==1){
  uint8_t header[12]={88,0,0,0,0x10,0,1,0,0,0,0,1};header[8]=(uint8_t)f->version;
  assert(n==12);
  switch(f->variant){case 1:header[0]=89;break;case 2:header[4]=0x11;break;case 3:header[6]=2;break;case 4:header[9]=1;break;case 5:header[10]=1;break;case 6:header[11]=0;break;default:break;}
  memcpy(out,header,12);return ok(f->variant==7?11:12,1);
 }
 assert(n==88-f->total);uint32_t part=n>23?23:n;
 for(uint32_t i=0;i<part;i++)out[i]=(uint8_t)((f->total+i)*3u+1u);
 f->bodies++;f->total+=part;return ok(part,1);
}
static fx3_call dispose(void *p){(void)p;abort();}
int main(int argc,char **argv){
 assert(getuid()==501 && geteuid()==501 && argc==3);fake f={.version=(unsigned)strtoul(argv[1],NULL,10),.variant=(unsigned)strtoul(argv[2],NULL,10),.now=1000};
 assert((f.version==0 || f.version==3) && f.variant<=7);
 fx3_route r={.initialized=1,.active=1,.generation=1};
 fx3_stream s={.route=&r,.ops={now,control,write_packet,read_packet,dispose},.backend=&f,.generation=1,.deadline_ns=1000000000,
  .mode=FX3_MODE_SERVICE,.started=1,.exchange_finished=1};atomic_init(&s.busy,0);
 uint8_t key[32];memset(key,0x5a,32);fx3_read_receipt receipt={0};int rc=fx3_stream_read0(&s,key,&receipt);
 int stopped=-1;if(rc==FX3T_OK)stopped=fx3_stream_stop(&s);
 printf("{\"version\":%u,\"variant\":%u,\"rc\":%d,\"bytes\":%u,\"reply_valid\":%u,\"writes\":%u,\"body_calls\":%u,\"body_total\":%u,\"STOP_calls\":%u,\"STOP_rc\":%d,\"opaque_hmac\":\"",f.version,f.variant,rc,receipt.bytes,receipt.reply_valid,f.writes,f.bodies,f.total,f.stops,stopped);
 for(unsigned i=0;i<32;i++)printf("%02x",receipt.opaque_hmac[i]);puts("\"}");return 0;
}
