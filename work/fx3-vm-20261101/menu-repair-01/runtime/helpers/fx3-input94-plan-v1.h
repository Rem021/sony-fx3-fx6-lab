#ifndef FX3_INPUT94_PLAN_V1
#define FX3_INPUT94_PLAN_V1
struct plan93 {unsigned next,phase,default_steps,nav;};
static int plan93_accept(struct plan93*s,unsigned step,unsigned key){static const unsigned first[2]={3,0x1ac},nav[4]={0x30,0x30,0x1af,0x1ac};if(!s||step!=s->next||step<1||step>19)return -1;if(step<=2){if(key!=first[step-1])return -2;}else if(!s->phase){if(key==0x1ac){if(s->default_steps>=12)return -3;s->default_steps++;}else if(key==0x1ab)s->phase=1;else return -4;}else if(s->phase==1){if(s->nav>=4||key!=nav[s->nav])return -5;if(++s->nav==4)s->phase=2;}else return -6;s->next++;return 0;}
#endif
