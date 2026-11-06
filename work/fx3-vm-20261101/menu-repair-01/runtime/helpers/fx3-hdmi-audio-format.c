/* FX3 CP source pins: fx3-audio-format-proof.json. Inactive configuration only. */
struct fx3_audio_format {unsigned int format,applied,notification_reason;};
int fx3_audio_format_apply(struct fx3_audio_format *s,const unsigned char *p,unsigned int n,unsigned char *reply){
 if(!s||!p||!reply||n!=10||p[0]!=0x0d||p[1]!=0x20||p[2]!=0x2d||p[3]!=3||p[4]!=10||p[5]||p[6]!=1||p[7]!=0x80||p[8]>1||p[9])return -1024;
 s->format=p[8];s->applied++;s->notification_reason=3;
 const unsigned char response[12]={0x0d,0x20,0x2d,0x13,12,0,1,0x80,0,0,0x58,0};
 for(unsigned int i=0;i<12;i++)reply[i]=response[i];return 0;
}
#ifdef FX3_AUDIO_FORMAT_TEST
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void){struct fx3_audio_format s={0};unsigned char p[10]={0x0d,0x20,0x2d,3,10,0,1,0x80,0,0},r[12];
 assert(!fx3_audio_format_apply(&s,p,10,r)&&s.format==0&&s.applied==1&&s.notification_reason==3);assert(r[2]==0x2d&&r[3]==0x13&&r[10]==0x58);
 p[8]=1;assert(!fx3_audio_format_apply(&s,p,10,r)&&s.format==1&&s.applied==2);struct fx3_audio_format before=s;
 p[8]=2;assert(fx3_audio_format_apply(&s,p,10,r)==-1024&&!memcmp(&s,&before,sizeof s));p[8]=1;p[9]=1;assert(fx3_audio_format_apply(&s,p,10,r)==-1024);p[9]=0;assert(fx3_audio_format_apply(&s,p,9,r)==-1024);p[2]=0x2f;assert(fx3_audio_format_apply(&s,p,10,r)==-1024);puts("FX3_HDMI_AUDIO_FORMAT_TEST_PASS");}
#endif
