#include <stddef.h>
#include <stdint.h>
void *memcpy(void*d,const void*s,size_t n){unsigned char*a=d;const unsigned char*b=s;for(size_t i=0;i<n;i++)a[i]=b[i];return d;}
void *memset(void*d,int v,size_t n){unsigned char*a=d;for(size_t i=0;i<n;i++)a[i]=(unsigned char)v;return d;}
#if PERF_VERSION==8
#include "fx3-gpe-backend-v8.c"
#else
#include "fx3-gpe-backend-v9.c"
#endif
int probe(unsigned op,const unsigned char *raw,unsigned char *dst,unsigned char *src){
 struct gpe_context c;gpe_init(&c,(struct gpe_hooks){0});struct gpe_ref d={1,5},s={2,9};
 int r=gpe_register(&c,d,u64(raw),dst,640*480*4);if(r)return r;
 if(op){r=gpe_register(&c,s,u64(raw+56),src,16*1024*1024);if(r)return r;}
 r=gpe_begin_batch(&c,1);if(r)return r;return gpe_submit(&c,op,1,0,raw,op?144:56,d,s);
}
