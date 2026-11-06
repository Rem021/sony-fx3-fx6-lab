/* Same-model source graph in fx3-vdf-config-proof.json.
 * Acceptance queue and brightness shadow only. No active VDF/hardware/pixels. */
struct fx3_vdf_config {unsigned char pending_layout[8][40];unsigned int pending_count,slope[2],slope_known[2],reset_pending,slope_updates;};
int fx3_vdf_config_apply(struct fx3_vdf_config *s,const unsigned char *p,unsigned int n,unsigned char *r){
 if(!s||!p||!r||n<8||p[0]!=0x0d||p[1]!=0x20||p[3]!=1||p[4]!=n||p[5]||p[6]!=1||p[7]!=0x80)return -1024;
 unsigned int command=p[2];
 if(command==0x4c){
  /* Only the observed boot layout for the declared 640x480 software canvas. */
  const unsigned char body[32]={7,1,1,0,0,0,0,0,0x80,2,0xe0,1,0,0,0,0,0,0,0,0,0,0,0,0,3,0,0,0,0,0,0,0};
  if(n!=40)return -1024;for(unsigned int i=0;i<32;i++)if(p[8+i]!=body[i])return -1024;
  if(s->pending_count==8)return -1021;
  for(unsigned int i=0;i<40;i++)s->pending_layout[s->pending_count][i]=p[i];s->pending_count++;
 }else if(command==0x3d){
  if(n!=10||p[9]<1||p[9]>2)return -1024;
  unsigned int selector=p[9]-1;s->slope[selector]=p[8];s->slope_known[selector]=1;s->slope_updates++;
  if(!p[8])s->reset_pending|=1U<<selector;
 }else return -1024;
 const unsigned char header[12]={0x0d,0x20,0,0x11,12,0,1,0x80,0,0,0x59,0};
 for(unsigned int i=0;i<12;i++)r[i]=header[i];r[2]=(unsigned char)command;return 0;
}
