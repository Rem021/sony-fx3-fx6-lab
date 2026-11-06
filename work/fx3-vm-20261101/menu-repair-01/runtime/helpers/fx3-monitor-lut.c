/* FX3 AP0161 -> BB19c95c -> legacy2001/011d -> f029/111d -> AP1161.
 * Software inactive display: mode0 identity only, retain request and pendingconfig.
 * No physical LUT programming or activecolour conversion is claimed. */
struct fx3_monitor_lut {unsigned int known,mode[2],updates,pending_f029;};
static int fx3_monitor_lut_apply(struct fx3_monitor_lut *s,const unsigned char *p,unsigned int n,unsigned char *out){
 if(!s||!p||!out||n!=10)return -1024;const unsigned char req[10]={0x0d,0x20,0x61,1,10,0,1,0x80,0,0};for(unsigned int i=0;i<10;i++)if(p[i]!=req[i])return -1024;
 const unsigned char reply[12]={0x0d,0x20,0x61,0x11,12,0,1,0x80,0,0,0,0};for(unsigned int i=0;i<12;i++)out[i]=reply[i];s->known=1;s->mode[0]=s->mode[1]=0;s->updates++;s->pending_f029++;return 0;
}
