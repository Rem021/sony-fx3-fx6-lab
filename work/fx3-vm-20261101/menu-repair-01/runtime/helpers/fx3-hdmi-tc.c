/* FX3 HDMI0109 set_tc_output: original65c78c/selectorA->profile+7c.
 * Explicit inactive software output supports TC disabled only. */
struct fx3_hdmi_tc {unsigned int known,tc_output,updates;};
static int fx3_hdmi_tc_apply(struct fx3_hdmi_tc *s,const unsigned char *p,unsigned int n,unsigned char *out){
 const unsigned char header[8]={0,0x25,9,1,12,0,1,0};if(!s||!p||!out||n!=12)return -1024;
 for(unsigned int i=0;i<8;i++)if(p[i]!=header[i])return -1024;for(unsigned int i=8;i<12;i++)if(p[i])return -1024;
 const unsigned char reply[12]={0,0x25,9,0x81,12,0,1,0,0,0,0,0};for(unsigned int i=0;i<12;i++)out[i]=reply[i];s->known=1;s->tc_output=0;s->updates++;return 0;
}
