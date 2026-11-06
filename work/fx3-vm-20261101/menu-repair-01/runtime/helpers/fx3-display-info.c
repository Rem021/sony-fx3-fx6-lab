/* Explicit virtual software surface geometry. CP original18B wire shape at1b087c. */
struct fx3_display_info {unsigned int queries;};
int fx3_display_info_apply(struct fx3_display_info *s,const unsigned char *p,unsigned int n,unsigned char *r){
 const unsigned char request[8]={0x0d,0x20,0x6a,1,8,0,1,0x80};if(!s||!p||!r||n!=8)return -1024;for(unsigned int i=0;i<8;i++)if(p[i]!=request[i])return -1024;
 const unsigned char response[18]={0x0d,0x20,0x6a,0x11,18,0,1,0x80,0x80,2,0xe0,1,0x80,2,0xe0,1,1,1};for(unsigned int i=0;i<18;i++)r[i]=response[i];s->queries++;return 0;
}
