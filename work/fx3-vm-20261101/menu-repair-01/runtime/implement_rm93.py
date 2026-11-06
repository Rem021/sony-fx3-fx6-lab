from pathlib import Path
import json
R=Path(__file__).resolve().parent;H=R/'helpers';proof=json.loads((R.parents[1]/'lead-claude/audits/rm-media-service/rm-media-proof.json').read_text());cfg=bytes.fromhex(proof['configuration_projection']['payload_hex']);assert len(cfg)==112
(H/'fx3-rm-empty-core-v1.h').write_text(r'''
#ifndef FX3_RM_EMPTY_CORE_V1
#define FX3_RM_EMPTY_CORE_V1
#define RM93_ID 0x80d9016eU
#define RM93_UNKNOWN 0x80000003U
#define RM93_ERROR 0x80000000U
struct rm93_state {unsigned notify,generation,replayed,commands;};
struct rm93_ops {int (*alloc)(unsigned,void **,unsigned);int (*send)(unsigned,void *);int (*release)(unsigned,void *);void (*source)(void *,unsigned);int (*alive)(unsigned);void (*log)(const char *,unsigned,unsigned,unsigned);};
static const unsigned char rm93_config[112]={'''+','.join(hex(b) for b in cfg)+r'''};
static const unsigned char rm93_empty[7]={2,0,0,7,0,0,0};
static unsigned rm93_u16(const unsigned char*p){return p[0]|(unsigned)p[1]<<8;}static unsigned rm93_u32(const unsigned char*p){return rm93_u16(p)|rm93_u16(p+2)<<16;}
static void rm93_put(unsigned char*p,unsigned v,unsigned n){for(unsigned i=0;i<n;i++)p[i]=(unsigned char)(v>>(8*i));}
static void rm93_copy(void*out,const void*in,unsigned n){unsigned char*d=out;const unsigned char*s=in;for(unsigned i=0;i<n;i++)d[i]=s[i];}
static int rm93_replay(struct rm93_state*s,const struct rm93_ops*o,unsigned destination){void*p=0;if(o->alive(destination)!=1)return -1;int rc=o->alloc(destination,&p,7);if(rc||!p){if(p)o->release(destination,p);return -2;}rm93_copy(p,rm93_empty,7);o->source(p,destination);if(o->alive(destination)!=1){o->release(destination,p);return -3;}rc=o->send(destination,p);if(rc){o->release(destination,p);return -4;}s->replayed++;o->log("FRONT_TRANSFER",destination,s->generation,7);return 0;}
/* Takes ownership of exactly one request. Copies own bytes, frees request,
 * allocates separate responses. No request/reply pointer retained by state. */
static int rm93_process(struct rm93_state*s,const struct rm93_ops*o,void*request,unsigned bytes){
 unsigned char header[24],body[4],response[136];unsigned command=0,reply=0,status=0,payload=0;int malformed=0;
 if(!request)return -1;
 if(bytes<24||bytes>4096){o->release(RM93_ID,request);o->log("LENGTH_REJECT",bytes,0,0);return -2;}
 rm93_copy(header,request,24);command=rm93_u32(header);reply=rm93_u32(header+8);unsigned declared=rm93_u16(header+6);
 if(declared!=bytes-24||rm93_u16(header+4)!=1||!reply||rm93_u32(header+12)!=0)malformed=1;
 if(command==9&&(bytes!=136||declared!=112))malformed=1;
 if(command==3&&(bytes!=28||declared!=4))malformed=1;
 if(command==3&&!malformed)rm93_copy(body,(unsigned char*)request+24,4);
 int fr=o->release(RM93_ID,request);o->log("REQUEST_FREE",command,bytes,(unsigned)fr);if(fr)return -3;s->commands++;
 if(malformed){status=RM93_UNKNOWN;o->log("LENGTH_REJECT",command,bytes,declared);}
 else if(command==9)payload=112;
 else if(command==3){unsigned wanted=rm93_u32(body),old=s->notify;s->generation++;if(!wanted){s->notify=0;o->log("CANCEL",old,s->generation,0);}else{if(rm93_replay(s,o,wanted)){s->notify=0;status=RM93_ERROR;o->log("REPLAY_REJECT",wanted,s->generation,0);}else{s->notify=wanted;o->log(old==wanted?"DUPLICATE_REG":"REGISTER",wanted,s->generation,1);}}payload=4;}
 else{status=RM93_UNKNOWN;o->log("UNKNOWN",command,bytes,status);}
 rm93_copy(response,header,24);rm93_put(response+6,payload,2);rm93_put(response+12,status,4);if(payload==112)rm93_copy(response+24,rm93_config,112);else if(payload==4)rm93_copy(response+24,body,4);
 if(o->alive(reply)!=1){o->log("REPLY_QUEUE_REJECT",reply,command,0);return -4;}void*p=0;int rc=o->alloc(reply,&p,24+payload);if(rc||!p){if(p)o->release(reply,p);o->log("REPLY_ALLOC_REJECT",command,(unsigned)rc,0);return -5;}rm93_copy(p,response,24+payload);o->source(p,RM93_ID);rc=o->send(reply,p);if(rc){o->release(reply,p);o->log("REPLY_SEND_REJECT",command,(unsigned)rc,0);return -6;}o->log("REPLY_TRANSFER",command,24+payload,status);return 0;
}
#endif
''')
print('core config112 generated from proof')
