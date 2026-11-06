/* Original FX3: 24*32B validation and double-buffer cache before130b completion.
 * This finite software backend retains config and queuesf024, no active output. */
struct fx3_plane_config {unsigned char banks[2][768];unsigned int valid[2],next_bank,committed,pending_f024;};
static unsigned int plane_u16(const unsigned char *p){return p[0]|((unsigned int)p[1]<<8);}
int fx3_plane_config_apply(struct fx3_plane_config *s,const unsigned char *p,unsigned int n,unsigned char *r){
 if(!s||!p||!r||n!=776||p[0]!=0x0d||p[1]!=0x20||p[2]!=0x47||p[3]!=1||p[4]!=8||p[5]!=3||p[6]!=1||p[7]!=0x80)return -1024;
 for(unsigned int k=0;k<24;k++){
  const unsigned char *q=p+8+32*k;
  if(q[0]&~7U||q[1]>1||q[2]||q[3]>7||q[20]>7||q[21]>1||q[22]||q[23]||q[24]>3||q[25]||q[26]||q[27]||q[28]||q[29]||q[30]||q[31])return -1024;
  /* Original validates rectangles for inactive entries. Software geometry640x480. */
  if(q[0]&&!q[1]&&(plane_u16(q+4)+plane_u16(q+8)>640||plane_u16(q+6)+plane_u16(q+10)>480||plane_u16(q+12)+plane_u16(q+16)>640||plane_u16(q+14)+plane_u16(q+18)>480))return -1024;
 }
 unsigned int bank=s->next_bank;for(unsigned int i=0;i<768;i++)s->banks[bank][i]=p[i+8];s->valid[bank]=1;s->next_bank^=1;s->committed++;s->pending_f024++;
 const unsigned char header[12]={0x0d,0x20,0x47,0x11,12,0,1,0x80,0,0,0x59,0};for(unsigned int i=0;i<12;i++)r[i]=header[i];return 0;
}
