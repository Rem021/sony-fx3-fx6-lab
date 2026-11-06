#ifndef FX3_OWN_BRIDGE_JOB_H
#define FX3_OWN_BRIDGE_JOB_H
struct bridge_job {
 unsigned char plan[256],plan_sha[32],image_sha[32];
 unsigned long parent_pid,parent_tid,issued,expires,old_mask;
};
_Static_assert(sizeof(struct bridge_job)==360,"own runtime context ABI");
static inline void bj_copy(void *out,const void *in,unsigned n){unsigned char *a=out;const unsigned char *b=in;for(unsigned i=0;i<n;i++)a[i]=b[i];}
static inline unsigned bj_g32(const unsigned char *p){unsigned v=0;for(unsigned i=0;i<4;i++)v|=(unsigned)p[i]<<(8*i);return v;}
static inline unsigned long bj_g64(const unsigned char *p){unsigned long v=0;for(unsigned i=0;i<8;i++)v|=(unsigned long)p[i]<<(8*i);return v;}
static inline void bj_p32(unsigned char *p,unsigned v){for(unsigned i=0;i<4;i++)p[i]=(unsigned char)(v>>(8*i));}
static inline void bj_p64(unsigned char *p,unsigned long v){for(unsigned i=0;i<8;i++)p[i]=(unsigned char)(v>>(8*i));}
static inline unsigned bj_crc(const unsigned char *p,unsigned n){unsigned c=~0u;for(unsigned i=0;i<n;i++){c^=p[i];for(unsigned j=0;j<8;j++)c=(c>>1)^((0u-(c&1))&0xedb88320u);}return ~c;}
static inline void bj_packet(unsigned char *p,const struct bridge_job *j,unsigned collector,unsigned worker,unsigned type){
 const unsigned char magic[16]="FX3BRIDGEIPC4";for(unsigned i=0;i<256;i++)p[i]=0;bj_copy(p,magic,16);
 bj_p32(p+16,4);bj_p32(p+20,type);bj_p32(p+24,(unsigned)j->parent_pid);bj_p32(p+28,collector);bj_p32(p+32,worker);bj_p32(p+36,1);
 bj_copy(p+40,j->plan+32,16);bj_copy(p+56,j->plan_sha,32);bj_copy(p+88,j->image_sha,32);bj_p64(p+120,j->issued);bj_p64(p+128,j->expires);
 bj_copy(p+136,j->plan+80,32);bj_copy(p+168,j->plan+48,32);bj_p64(p+200,j->parent_tid);bj_copy(p+208,j->plan+164,32);bj_p64(p+240,bj_g64(j->plan+196));bj_p32(p+252,bj_crc(p,252));
}
__attribute__((visibility("hidden"))) int fx3_parent_receiver(long,unsigned,const struct bridge_job *,int *);
__attribute__((visibility("hidden"))) int fx3_isolated_collector_core(long,const struct bridge_job *);
#endif
