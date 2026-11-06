/* Original FX3 CEC20e686/20f370/652152. Explicit software disconnectedCEC.
 * Retains power request only; no HPD, address discovery or wire activity. */
struct fx3_cec_power {unsigned int known,power,generation;};
static int fx3_cec_power_apply(struct fx3_cec_power *s,const unsigned char *p,unsigned int n,unsigned char *out){
 if(!s||!p||!out||n!=12)return -1024;
 const unsigned char header[8]={0,0,1,1,12,0,1,0};for(unsigned int i=0;i<8;i++)if(p[i]!=header[i])return -1024;
 if(p[8]>1||p[9]||p[10]||p[11])return -1024;
 const unsigned char reply[16]={0,0,1,0x81,16,0,1,0,0,0,0,0,0,0,0,0};for(unsigned int i=0;i<16;i++)out[i]=reply[i];out[12]=p[8];s->known=1;s->power=p[8];s->generation++;return 0;
}
