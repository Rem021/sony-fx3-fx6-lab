#ifndef FX3_SYNTH_KEY_CORE_V1_H
#define FX3_SYNTH_KEY_CORE_V1_H
/* Explicit AP91 synthetic script, not physical CP key detection. */
typedef unsigned long sk_u64;
struct sk_script {unsigned step,phase,armed,failed;sk_u64 due;};
static const unsigned sk_keys[6]={0x1ac,0x1ab,0x30,0x30,0x1af,0x1ab};
static int sk_key_allowed(unsigned k){return k==0x1ac||k==0x1ab||k==3||k==0x15||k==0x30||k==0x1af;}
static int sk_pack(unsigned k,unsigned status,unsigned char p[20]){
 if(!sk_key_allowed(k)||status>1)return -1;
 for(unsigned i=0;i<20;i++)p[i]=0;
 for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(k>>(i*8));p[8]=status;p[16]=1;return 0;
}
static int sk_arm(struct sk_script*s,sk_u64 opened){
 if(!s||s->armed||!opened||opened>~0UL-5000000000UL)return -1;
 s->armed=1;s->step=1;s->phase=1;s->due=opened+5000000000UL;return 0;
}
static int sk_ready(struct sk_script*s,sk_u64 now,unsigned*step,unsigned*key,unsigned*status){
 if(!s||s->failed||!s->armed||s->step>6||now<s->due)return 0;
 *step=s->step;*key=sk_keys[s->step-1];*status=s->phase==1?1:0;return 1;
}
static int sk_commit(struct sk_script*s,sk_u64 sent){
 if(!s||s->failed||!s->armed||s->step>6||sent<s->due)return -1;
 sk_u64 gap=s->phase==1?100000000UL:4000000000UL;if(sent>~0UL-gap){s->failed=1;return -1;}
 if(s->phase==1)s->phase=2;else{s->step++;s->phase=1;}s->due=sent+gap;return 0;
}
#endif
