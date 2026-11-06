/* Same FX3 CP98c8ea..98c9a6, producer98f66a. Explicit idle virtual capture.
 * Active release must defer in original; unsupported here, never acknowledged. */
struct fx3_release_inhibit {unsigned int active_release,mask,updates,last_token;};
static unsigned int rel_u32(const unsigned char *p){return p[0]|((unsigned int)p[1]<<8)|((unsigned int)p[2]<<16)|((unsigned int)p[3]<<24);}
static int fx3_release_inhibit_apply(struct fx3_release_inhibit *s,const unsigned char *p,unsigned int n,unsigned char *out){
 if(!s||!p||!out||n!=16)return -1024;if(s->active_release)return -1021;
 if(p[0]!=5||p[1]||p[2]!=0x3d||p[3]!=0x40||rel_u32(p+8)!=0x8000||p[12]>1||p[13]||p[14]||p[15])return -1024;
 const unsigned char reply[12]={1,0,0x3d,0x40,0,0,0,0,0,0xf0,0,0};for(unsigned int i=0;i<12;i++)out[i]=reply[i];for(unsigned int i=0;i<4;i++)out[4+i]=p[4+i];
 if(p[12])s->mask|=0x8000;else s->mask&=~0x8000U;s->last_token=rel_u32(p+4);s->updates++;return 0;
}
