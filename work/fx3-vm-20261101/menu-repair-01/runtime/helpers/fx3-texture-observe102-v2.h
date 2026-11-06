/* Passive SHA256 + raw-channel histogram over already validated mapped rows. */
struct tex102_sha {unsigned h[8];unsigned char block[64];U length;unsigned used;};
static unsigned tex102_rotr(unsigned a,unsigned n){return(a>>n)|(a<<(32-n));}
static void tex102_block(struct tex102_sha*s,const unsigned char*p){
 static const unsigned k[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
 unsigned w[64];for(unsigned i=0;i<16;i++)w[i]=(unsigned)p[4*i]<<24|(unsigned)p[4*i+1]<<16|(unsigned)p[4*i+2]<<8|p[4*i+3];for(unsigned i=16;i<64;i++){unsigned a=w[i-15],b=w[i-2];w[i]=w[i-16]+(tex102_rotr(a,7)^tex102_rotr(a,18)^(a>>3))+w[i-7]+(tex102_rotr(b,17)^tex102_rotr(b,19)^(b>>10));}
 unsigned a=s->h[0],b=s->h[1],c=s->h[2],d=s->h[3],e=s->h[4],f=s->h[5],g=s->h[6],h=s->h[7];for(unsigned i=0;i<64;i++){unsigned t=h+(tex102_rotr(e,6)^tex102_rotr(e,11)^tex102_rotr(e,25))+((e&f)^(~e&g))+k[i]+w[i];unsigned z=(tex102_rotr(a,2)^tex102_rotr(a,13)^tex102_rotr(a,22))+((a&b)^(a&c)^(b&c));h=g;g=f;f=e;e=d+t;d=c;c=b;b=a;a=t+z;}unsigned v[8]={a,b,c,d,e,f,g,h};for(unsigned i=0;i<8;i++)s->h[i]+=v[i];
}
static void tex102_init(struct tex102_sha*s){unsigned initial[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};__builtin_memcpy(s->h,initial,32);s->length=0;s->used=0;}
static void tex102_update(struct tex102_sha*s,const unsigned char*p,U n){s->length+=n;while(n){unsigned m=64-s->used;if(m>n)m=(unsigned)n;__builtin_memcpy(s->block+s->used,p,m);s->used+=m;p+=m;n-=m;if(s->used==64){tex102_block(s,s->block);s->used=0;}}}
static void tex102_final(struct tex102_sha*s,char out[65]){U bits=s->length*8;unsigned char pad[128]={0x80};unsigned n=s->used<56?56-s->used:120-s->used;tex102_update(s,pad,n);for(unsigned i=0;i<8;i++)pad[i]=(unsigned char)(bits>>(56-8*i));tex102_update(s,pad,8);const char*d="0123456789abcdef";for(unsigned i=0;i<32;i++){unsigned b=(s->h[i/4]>>(24-8*(i%4)))&255;out[2*i]=d[b>>4];out[2*i+1]=d[b&15];}out[64]=0;}
static void tex102_rows(const unsigned char*p,U step,U line,unsigned rows,char out[65]){struct tex102_sha s;tex102_init(&s);for(unsigned y=0;y<rows;y++)tex102_update(&s,p+(U)y*step,line);tex102_final(&s,out);}
struct tex102_sample {unsigned enabled,seq,fmt,bpp,source_rows,destination_rows;U source_line,source_step,destination_line,source_phys,destination_phys,raw_source,source_object,destination_object;U source_bytes,destination_bytes;unsigned char *source_copy,*before_copy,*after_copy;int result;};
static __thread unsigned char *tex102_workspace;static __thread U tex102_workspace_capacity;
#ifndef TEX102_MAP_FLAGS
#define TEX102_MAP_FLAGS 0x22
#endif
extern int snprintf(char*,size_t,const char*,...);
static void tex102_copy_rows(unsigned char*out,const unsigned char*in,U step,U line,unsigned rows){for(unsigned y=0;y<rows;y++)__builtin_memcpy(out+(U)y*line,in+(U)y*step,line);}
static void tex102_before(struct tex102_sample*s,const unsigned char*raw,const struct gpe_plan*p,const unsigned char*src,const unsigned char*dst,unsigned seq,U so,U dob){
 int saved=*__errno_location();if(raw[112]!=1||raw[114]!=255||raw[115]!=1)goto done;
 if(p->empty_clip_noop){dprintf(2,"FX3_TEX102_SKIPPED seq=%u reason=empty_clip_native_no_pixel_access_preserved raw_source=%#lx\n",seq,load64(raw+56));goto done;}
 if(!p->src_rows||!p->rows||!p->src_line||!p->line||p->src_line>0x200000UL/p->src_rows||p->line>0x200000UL/p->rows||(p->src_bpp!=2&&p->src_bpp!=4)||p->src_line%p->src_bpp){dprintf(2,"FX3_TEX102_SKIPPED seq=%u reason=observer_size_or_format_bound\n",seq);goto done;}
 U source_n=(U)p->src_rows*p->src_line,destination_n=(U)p->rows*p->line,need=(source_n+2*destination_n+4095)&~4095UL;
 if(need>tex102_workspace_capacity){void*q=mmap(0,need,3,TEX102_MAP_FLAGS,-1,0);if(q==(void*)-1){dprintf(2,"FX3_TEX102_SKIPPED seq=%u reason=private_observer_workspace_unavailable\n",seq);goto done;}if(tex102_workspace)(void)munmap(tex102_workspace,tex102_workspace_capacity);tex102_workspace=q;tex102_workspace_capacity=need;}
 s->enabled=1;s->seq=seq;s->fmt=load32(raw+92);s->bpp=p->src_bpp;s->source_rows=p->src_rows;s->destination_rows=p->rows;s->source_line=p->src_line;s->source_step=p->src_step;s->destination_line=p->line;s->source_phys=p->src;s->destination_phys=p->dst;s->raw_source=load64(raw+56);s->source_object=so;s->destination_object=dob;s->source_bytes=source_n;s->destination_bytes=destination_n;s->source_copy=tex102_workspace;s->before_copy=tex102_workspace+source_n;s->after_copy=s->before_copy+destination_n;
 tex102_copy_rows(s->source_copy,src,p->src_step,p->src_line,p->src_rows);tex102_copy_rows(s->before_copy,dst,p->dst_step,p->line,p->rows);
 done:*__errno_location()=saved;
}
static void tex102_after(struct tex102_sample*s,const struct gpe_plan*p,const unsigned char*dst,int result){int saved=*__errno_location();if(s->enabled){tex102_copy_rows(s->after_copy,dst,p->dst_step,p->line,p->rows);s->result=result;}*__errno_location()=saved;}
/* Caller releases original resource/raster locks before entering this function.
 * All reads below target our private immutable per-command copies only. */
static void tex102_emit(struct tex102_sample*s){
 if(!s->enabled)return;int saved=*__errno_location();char source[65],before[65],after[65];unsigned hist[4][256]={{0}},bins=s->bpp==2?16:256;
 tex102_rows(s->source_copy,s->source_bytes,s->source_bytes,1,source);tex102_rows(s->before_copy,s->destination_bytes,s->destination_bytes,1,before);tex102_rows(s->after_copy,s->destination_bytes,s->destination_bytes,1,after);
 for(U x=0;x<s->source_bytes;x+=s->bpp){const unsigned char*b=s->source_copy+x;if(s->bpp==2){unsigned v=b[0]|(unsigned)b[1]<<8;for(unsigned c=0;c<4;c++)hist[c][(v>>(12-4*c))&15]++;}else for(unsigned c=0;c<4;c++)hist[c][b[3-c]]++;}
 dprintf(2,"FX3_TEX102_BEFORE seq=%u raw_source=%#lx source_crop=%#lx destination_crop=%#lx source_object=%#lx destination_object=%#lx source_format=%u source_bpp=%u source_rows=%u source_line_bytes=%lu source_step_bytes=%lu destination_rows=%u destination_line_bytes=%lu source_SHA256=%s destination_before_SHA256=%s pixel_order=%s original_raw144_logged=1 read_only=1 hash_outside_raster_lock=1 captured_before_original_submit=1\n",s->seq,s->raw_source,s->source_phys,s->destination_phys,s->source_object,s->destination_object,s->fmt,s->bpp,s->source_rows,s->source_line,s->source_step,s->destination_rows,s->destination_line,source,before,s->bpp==2?"LE_RGBA4444_nibbles_R12_G8_B4_A0":"raw_byte3_byte2_byte1_byte0_alpha_semantics_by_native_format");
 for(unsigned c=0;c<4;c++){char text[4096];unsigned used=0;for(unsigned i=0;i<bins;i++){int n=snprintf(text+used,sizeof(text)-used,"%s%u:%u",i?",":"",i,hist[c][i]);if(n<0||(unsigned)n>=sizeof(text)-used)break;used+=(unsigned)n;}text[used]=0;dprintf(2,"FX3_TEX102_HIST seq=%u channel=%u bins=%u counts=%s all_raw_crop_pixels=1 padding_excluded=1 hash_outside_raster_lock=1\n",s->seq,c,bins,text);}
 dprintf(2,"FX3_TEX102_AFTER seq=%u result=%d destination_after_SHA256=%s destination_changed=%u original_submit_result_unchanged=1 read_only=1 hash_outside_raster_lock=1\n",s->seq,s->result,after,__builtin_memcmp(before,after,64)!=0);*__errno_location()=saved;
}
