/* Bounded software-only empty pin graph. Caller serializes transactions. */
#include "fx3-pin-config-v1.h"
struct pin_queue {unsigned active,capacity,head,count;unsigned long generation;unsigned long handles[4];};
struct pin_endpoint {unsigned key[4],state;int peer;unsigned long generation;unsigned reply_refs,resource_refs,pending_hardware;struct pin_queue queue;};
struct pin_buffer {unsigned active,domain,producer,consumer;unsigned long handle,generation,capacity;unsigned refs;};
struct pin_graph {unsigned ready,fault;unsigned long serial,queries,connections,disconnects;struct pin_endpoint pins[22];struct pin_buffer buffers[16];};
struct pin_result {unsigned command,owner,reply_id,padding;int index,peer,status;unsigned long serial;};
static unsigned pg_get(const unsigned char *p){return (unsigned)p[0]|(unsigned)p[1]<<8|(unsigned)p[2]<<16|(unsigned)p[3]<<24;}
static unsigned pg_u16(const unsigned char *p){return p[0]|(unsigned)p[1]<<8;}
static void pg_put(unsigned char *p,unsigned v){for(int i=0;i<4;i++)p[i]=(unsigned char)(v>>(i*8));}
static void pg_init(struct pin_graph *g){memset(g,0,sizeof *g);g->ready=1;for(int i=0;i<22;i++){memcpy(g->pins[i].key,pkeys[i],16);g->pins[i].state=1;g->pins[i].peer=-1;g->pins[i].generation=1;g->pins[i].pending_hardware=1;}}
static int pg_owner(unsigned id){for(int i=0;i<22;i++)if(pkeys[i][0]==id)return 1;return 0;}
static int pg_find(const unsigned key[4]){for(int i=0;i<22;i++)if(!memcmp(key,pkeys[i],16))return i;return -1;}
static int pg_edge(int a,int b){for(int i=0;i<11;i++)if(pedges[i][0]==(unsigned)a&&pedges[i][1]==(unsigned)b)return 1;return 0;}
static int pg_direction(unsigned a,unsigned b){return (a==2&&b==1)||(a==3&&b==3);}
static int pg_busy(const struct pin_endpoint *p){return p->reply_refs||p->resource_refs||p->queue.count;}
static int pg_connect(struct pin_graph *g,int a,int b){if(a<0||b<0)return -32;struct pin_endpoint *x=g->pins+a,*y=g->pins+b;
 if(x->key[1]!=y->key[1])return -23;if(!pg_direction(x->key[2],y->key[2]))return -22;
 if(x->state==2||y->state==2||pg_busy(x)||pg_busy(y))return -24;
 if((x->peer>=0&&x->peer!=b)||(y->peer>=0&&y->peer!=a))return -25;
 if(!pg_edge(a,b))return -32;if(x->state==0&&y->state==0&&x->peer==b&&y->peer==a)return 0;
 if(x->state!=1||y->state!=1||x->generation==~0UL||y->generation==~0UL)return -24;
 x->peer=b;y->peer=a;x->state=y->state=0;x->generation++;y->generation++;
 x->queue=(struct pin_queue){1,4,0,0,x->generation,{0}};y->queue=(struct pin_queue){1,4,0,0,y->generation,{0}};g->connections++;return 0;}
static int pg_disconnect(struct pin_graph *g,int a){if(a<0)return -32;struct pin_endpoint *x=g->pins+a;if(x->state==1&&x->peer<0)return -26;int b=x->peer;if(b<0||b>=22)return -32;struct pin_endpoint *y=g->pins+b;if(x->state==2||y->state==2||pg_busy(x)||pg_busy(y))return -24;if(y->peer!=a||x->generation==~0UL||y->generation==~0UL)return -24;x->peer=y->peer=-1;x->state=y->state=1;x->generation++;y->generation++;memset(&x->queue,0,sizeof x->queue);memset(&y->queue,0,sizeof y->queue);g->disconnects++;return 0;}
/* Resource registration exists only for independently validated software allocation owners.
 * Current guest control-only profile never registers or transfers image buffers. */
static int pg_buffer_register(struct pin_graph *g,unsigned domain,int producer,unsigned long handle,unsigned long capacity,unsigned long *token){if(!g->ready||producer<0||producer>=22||domain!=545||g->pins[producer].key[0]!=0x9080003bU||g->pins[producer].key[1]!=1||!handle||!capacity)return -1;for(int i=0;i<16;i++)if(g->buffers[i].active&&g->buffers[i].handle==handle)return -1;for(int i=0;i<16;i++)if(!g->buffers[i].active){struct pin_buffer *b=g->buffers+i;if(b->generation>=(~0UL>>8))return -1;unsigned long gen=b->generation+1;*b=(struct pin_buffer){1,domain,(unsigned)producer,~0U,handle,gen,capacity,0};*token=(gen<<8)|(unsigned long)(i+1);return 0;}return -1;}
static struct pin_buffer *pg_buffer(struct pin_graph *g,unsigned long token){unsigned i=(unsigned)(token&255);if(!i||i>16)return 0;struct pin_buffer *b=g->buffers+i-1;return b->active&&b->generation==(token>>8)?b:0;}
static int pg_buffer_transfer(struct pin_graph *g,unsigned long token,int producer,int consumer){struct pin_buffer *b=pg_buffer(g,token);if(!b||b->producer!=(unsigned)producer||b->refs||producer<0||producer>=22||consumer<0||consumer>=22)return -1;struct pin_endpoint *x=g->pins+producer,*y=g->pins+consumer;if(x->peer!=consumer||y->peer!=producer||x->state||y->state||y->queue.count>=y->queue.capacity||x->queue.generation!=x->generation||y->queue.generation!=y->generation)return -1;unsigned pos=(y->queue.head+y->queue.count)%4;y->queue.handles[pos]=token;y->queue.count++;x->resource_refs++;y->resource_refs++;b->consumer=(unsigned)consumer;b->refs=1;return 0;}
static int pg_buffer_return(struct pin_graph *g,unsigned long token,int consumer){struct pin_buffer *b=pg_buffer(g,token);if(!b||!b->refs||b->consumer!=(unsigned)consumer||consumer<0||consumer>=22||b->producer>=22)return -1;struct pin_endpoint *x=g->pins+b->producer,*y=g->pins+consumer;if(!y->queue.count||y->queue.handles[y->queue.head]!=token||!x->resource_refs||!y->resource_refs)return -1;y->queue.handles[y->queue.head]=0;y->queue.head=(y->queue.head+1)%4;y->queue.count--;x->resource_refs--;y->resource_refs--;b->refs=0;b->consumer=~0U;return 0;}
static int pg_buffer_retire(struct pin_graph *g,unsigned long token,int producer){struct pin_buffer *b=pg_buffer(g,token);if(!b||b->refs||b->producer!=(unsigned)producer)return -1;b->active=0;return 0;}
static int pg_request(struct pin_graph *g,unsigned owner,const unsigned char *q,unsigned n,unsigned source,unsigned char out[56],struct pin_result *r){
 if(!g||!g->ready||g->fault||!q||!out||!r||!pg_owner(owner)||!source||(source>>28)!=8||!(source&0xfffffff))return -1024;
 if((n!=48&&n!=64)||pg_get(q)!=source||pg_get(q+4)!=0xa0a0a0a0U||pg_u16(q+8)!=1||pg_u16(q+10)!=n||pg_get(q+12)!=24||pg_get(q+16)!=n||pg_u16(q+24)!=0x1000||pg_u16(q+30)!=2)return -1024;
 unsigned cmd=pg_u16(q+26);if(cmd>2||pg_u16(q+28)!=(cmd==1?40:24)||n!=(cmd==1?64:48))return -1024;
 unsigned self[4]={owner,pg_get(q+32),pg_get(q+36),pg_get(q+40)},peer[4]={0};if(cmd!=1&&pg_get(q+44))return -1024;if(cmd==1){if(pg_get(q+44)!=owner)return -1024;peer[0]=pg_get(q+60);peer[1]=pg_get(q+48);peer[2]=pg_get(q+52);peer[3]=pg_get(q+56);}
 int a=pg_find(self),b=cmd==1?pg_find(peer):-1,status=0;if(a<0)status=-32;else if(cmd==1)status=pg_connect(g,a,b);else if(cmd==2)status=pg_disconnect(g,a);else g->queries++;
 memset(out,0,56);if(cmd==0&&(owner==0x9284074a||owner==0x9080003b))pg_put(out,owner);pg_put(out+4,0xa0a0a0a0U);out[8]=1;out[10]=56;out[12]=24;out[16]=56;out[24]=0;out[25]=16;out[26]=(unsigned char)cmd;out[27]=128;out[28]=32;out[30]=2;
 pg_put(out+32,self[1]);pg_put(out+36,self[2]);pg_put(out+40,self[3]);if(cmd==0){pg_put(out+44,a>=0?g->pins[a].state:255);pg_put(out+48,a>=0?owner:0);pg_put(out+52,(unsigned)status);}else{pg_put(out+44,owner);pg_put(out+48,(unsigned)status);}
 *r=(struct pin_result){cmd,owner,source,pg_get(q+20),a,b,status,++g->serial};return 0;
}
