#ifndef FX3_INPUT95_HOSTSTEP_V1_H
#define FX3_INPUT95_HOSTSTEP_V1_H
/* Host-owned command12 at+8. No predefined sequence; no autonomous next key.
 * delete_key=0 until independent key audit is approved by Lead. */
#define HP95_MAGIC 0x3545594b334d5253UL
#define HP95_MAX_STEPS 30U
struct hp95_command {unsigned step,key,hold_ms;};
static int hp95_allowed(unsigned key,unsigned delete_key){return key==3||key==0x30||key==0x15||key==0x1af||key==0x1ac||key==0x1ab||(delete_key&&key==delete_key);}
static int hp95_validate(unsigned done,const struct hp95_command*c,unsigned delete_key){if(!c||done>=30||c->step!=done+1||c->step>30)return -1;if(!hp95_allowed(c->key,delete_key))return -2;if(c->hold_ms<50||c->hold_ms>200)return -3;return 0;}
static int hp95_pack(unsigned key,unsigned down,unsigned delete_key,unsigned char*p){if(!p||down>1||!hp95_allowed(key,delete_key))return -1;for(unsigned i=0;i<20;i++)p[i]=0;for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(key>>(8*i));p[8]=(unsigned char)down;p[16]=1;return 0;}
#endif
