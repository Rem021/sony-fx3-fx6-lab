/* Explicit inactive HDMI desired preset, original FX3 proof fx3-hdmi-photo-proof.json. */
struct fx3_hdmi_photo {unsigned int raw,preset6,applied;};
int fx3_hdmi_photo_apply(struct fx3_hdmi_photo *s,const unsigned char *p,unsigned int n,unsigned char *reply){
 if(!s||!p||!reply||n!=12||p[0]!=0||p[1]!=0x25||p[2]!=2||p[3]!=1||p[4]!=12||p[5]||p[6]!=1||p[7]||p[8]>2||p[9]||p[10]||p[11])return -1024;
 s->raw=p[8];s->preset6=p[8];s->applied++;
 const unsigned char response[12]={0,0x25,2,0x81,12,0,1,0,0,0,0,0};
 for(unsigned int i=0;i<12;i++)reply[i]=response[i];return 0;
}
#ifdef FX3_HDMI_PHOTO_TEST
#include <assert.h>
#include <stdio.h>
#include <string.h>
int main(void){struct fx3_hdmi_photo s={0};unsigned char p[12]={0,0x25,2,1,12,0,1,0,0,0,0,0},r[12];
 for(unsigned int i=0;i<3;i++){p[8]=i;assert(!fx3_hdmi_photo_apply(&s,p,12,r)&&s.raw==i&&s.preset6==i&&s.applied==i+1);assert(r[3]==0x81&&r[8]==0);}
 struct fx3_hdmi_photo before=s;p[8]=3;assert(fx3_hdmi_photo_apply(&s,p,12,r)==-1024&&!memcmp(&s,&before,sizeof s));p[8]=0;p[9]=1;assert(fx3_hdmi_photo_apply(&s,p,12,r)==-1024);p[9]=0;assert(fx3_hdmi_photo_apply(&s,p,11,r)==-1024);p[2]=3;assert(fx3_hdmi_photo_apply(&s,p,12,r)==-1024);puts("FX3_HDMI_PHOTO_TEST_PASS");}
#endif
