#define _POSIX_C_SOURCE 200809L
#include "api.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#define DBYTES (640*480*2)
#define GUARD 32
struct vector { unsigned op,n;uint8_t raw[144]; };
static struct vector *vectors;static unsigned nvec;
static uint8_t *texture;static size_t texture_len;
static uint32_t rng=0x92a31e47;static uint32_t random9(void){rng^=rng<<13;rng^=rng>>17;return rng^=rng<<5;}
static uint64_t checks,zero_rejects,accepted,compared_bytes,math_checks;
static void check(int v){checks++;if(!v){fprintf(stderr,"FAIL check=%llu\n",(unsigned long long)checks);abort();}}
static uint32_t get32(const uint8_t*p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t get64(const uint8_t*p){return get32(p)|(uint64_t)get32(p+4)<<32;}
static void set32(uint8_t*p,uint32_t v){memcpy(p,&v,4);}
static void set64(uint8_t*p,uint64_t v){memcpy(p,&v,8);}
static uint8_t *file_bytes(const char *name,size_t *len){FILE*f=fopen(name,"rb");assert(f);assert(!fseek(f,0,SEEK_END));long n=ftell(f);assert(n>0);rewind(f);uint8_t *b=malloc((size_t)n);assert(b);assert(fread(b,1,(size_t)n,f)==(size_t)n);fclose(f);*len=(size_t)n;return b;}
static void load_vectors(void){size_t n;uint8_t*b=file_bytes("build/vectors.bin",&n);assert(n>=12&&!memcmp(b,"GPEVEC09",8));nvec=get32(b+8);vectors=calloc(nvec,sizeof(*vectors));assert(vectors);size_t at=12;for(unsigned i=0;i<nvec;i++){assert(at+8<=n);vectors[i].op=get32(b+at);vectors[i].n=get32(b+at+4);at+=8;assert(vectors[i].n<=144&&at+vectors[i].n<=n);memcpy(vectors[i].raw,b+at,vectors[i].n);at+=vectors[i].n;}assert(at==n);free(b);texture=file_bytes("build/textures.bin",&texture_len);}
struct trace { unsigned callbacks,statuses;uint64_t value; };
static int cb(void*u,uint64_t fn,const uint8_t p[16]){struct trace*t=u;t->callbacks++;t->value^=fn^get64(p)^get64(p+8);return 0;}
static int status(void*u,uint32_t src,const uint8_t p[4]){struct trace*t=u;t->statuses++;t->value^=(uint64_t)src<<32|get32(p);return 0;}
static int plan9(const struct vector *v,struct gpe_plan*p,int old){return v->op==0?(old?v8_gpe_plan_fill(v->raw,v->n,p):gpe_plan_fill(v->raw,v->n,p)):(old?v8_gpe_plan_blit(v->raw,v->n,p):gpe_plan_blit(v->raw,v->n,p));}
struct fixture { uint8_t *dst[2],*src[2],*before;size_t srcbytes,dstbytes;uint64_t db,sb;unsigned shared;struct gpe_context ctx[2];struct trace trace[2];struct gpe_plan plan;int planned; };
static void make_fixture(const struct vector*v,struct fixture*f,unsigned short_source,unsigned short_destination){
 memset(f,0,sizeof(*f));f->db=get64(v->raw);f->sb=v->op?get64(v->raw+56):0;f->dstbytes=DBYTES;
 f->planned=plan9(v,&f->plan,0);
 f->srcbytes=4096;
 if(!f->planned&&v->op){uint64_t e=f->plan.src-f->sb+(f->plan.src_rows-1)*f->plan.src_step+f->plan.src_line;assert(e<=16*1024*1024);f->srcbytes=(size_t)e;}
 if(short_source&&f->srcbytes)f->srcbytes--;
 if(short_destination&&!f->planned){uint64_t e=f->plan.dst-f->db+(f->plan.rows-1)*f->plan.dst_step+f->plan.line;if(e>0&&e<=DBYTES)f->dstbytes=(size_t)e-1;}
 f->shared=v->op&&f->sb>=f->db&&f->sb-f->db<DBYTES&&f->srcbytes<=DBYTES-(f->sb-f->db);
 for(unsigned j=0;j<2;j++){
  f->dst[j]=malloc(DBYTES+2*GUARD+1);f->src[j]=malloc(f->srcbytes+2*GUARD+1);assert(f->dst[j]&&f->src[j]);
  memset(f->dst[j],0x6d,DBYTES+2*GUARD+1);memset(f->src[j],0xb2,f->srcbytes+2*GUARD+1);
  /* Different initial destinations and full-buffer comparisons catch no-op,
   * padding, crop and alpha changes; all valid source bytes come from LDEC. */
  uint8_t*d=f->dst[j]+GUARD+1,*s=f->src[j]+GUARD+1;
  for(size_t i=0;i<DBYTES;i++)d[i]=(uint8_t)(i*37+(i>>9)*13+97);
  for(size_t i=0;i<f->srcbytes;i++)s[i]=texture[i%texture_len];
  if(f->shared)memcpy(d+(f->sb-f->db),s,f->srcbytes);
 }
 f->before=malloc(DBYTES+2*GUARD+1);assert(f->before);memcpy(f->before,f->dst[0],DBYTES+2*GUARD+1);
}
static int execute(const struct vector*v,struct fixture*f,unsigned j,unsigned stale,unsigned retiring){
 struct gpe_context*c=&f->ctx[j];struct gpe_ref d={1,5},s=f->shared?d:(struct gpe_ref){2,9};
 if(j==0)v8_gpe_init(c,(struct gpe_hooks){&f->trace[j],cb,status});else gpe_init(c,(struct gpe_hooks){&f->trace[j],cb,status});
 int r=j?gpe_register(c,d,f->db,f->dst[j]+GUARD+1,f->dstbytes):v8_gpe_register(c,d,f->db,f->dst[j]+GUARD+1,f->dstbytes);
 if(!r&&v->op&&!f->shared)r=j?gpe_register(c,s,f->sb,f->src[j]+GUARD+1,f->srcbytes):v8_gpe_register(c,s,f->sb,f->src[j]+GUARD+1,f->srcbytes);
 if(r)return r;
 if(retiring){struct gpe_lease l={0};check(!(j?gpe_acquire(c,d,&l):v8_gpe_acquire(c,d,&l)));check((j?gpe_unregister(c,d):v8_gpe_unregister(c,d))==GPE_BUSY);}
 check(!(j?gpe_begin_batch(c,1):v8_gpe_begin_batch(c,1)));
 if(stale)d.generation--;
 r=j?gpe_submit(c,v->op,83,0x808261c0,v->raw,v->n,d,s):v8_gpe_submit(c,v->op,83,0x808261c0,v->raw,v->n,d,s);
 while(c->count)check(!(j?gpe_deliver_one(c):v8_gpe_deliver_one(c)));
 for(unsigned i=0;i<GPE_EXTENTS;i++)c->extents[i].cpu=NULL;c->hooks.user=NULL;
 return r;
}
static void free_fixture(struct fixture*f){for(unsigned j=0;j<2;j++){free(f->dst[j]);free(f->src[j]);}free(f->before);}
static void differential(const struct vector*v,unsigned mode,unsigned index){
 struct gpe_plan a,b;memset(&a,0x23,sizeof a);memset(&b,0x23,sizeof b);int pa=plan9(v,&a,1),pb=plan9(v,&b,0);check(pa==pb);check(!memcmp(&a,&b,sizeof a));
 struct fixture f;make_fixture(v,&f,mode==1,mode==2);
 if(mode==5&&!f.shared)for(unsigned j=0;j<2;j++)for(size_t i=0;i<f.srcbytes;i+=2)f.src[j][GUARD+1+i]|=15;
 int r8=execute(v,&f,0,mode==3,mode==4),r9=execute(v,&f,1,mode==3,mode==4);
 if(r8!=r9||memcmp(f.dst[0],f.dst[1],DBYTES+2*GUARD+1)){fprintf(stderr,"VECTOR index=%u mode=%u r8=%d r9=%d\n",index,mode,r8,r9);abort();}
 check(!memcmp(&f.ctx[0],&f.ctx[1],sizeof f.ctx[0]));check(!memcmp(&f.trace[0],&f.trace[1],sizeof f.trace[0]));
 check(!memcmp(f.src[0],f.src[1],f.srcbytes+2*GUARD+1));
 for(unsigned j=0;j<2;j++){check(!memcmp(f.dst[j],f.before,GUARD+1));check(!memcmp(f.dst[j]+GUARD+1+DBYTES,f.before+GUARD+1+DBYTES,GUARD));}
 if(r8){check(!memcmp(f.dst[0],f.before,DBYTES+2*GUARD+1));zero_rejects++;}else accepted++;
 compared_bytes+=DBYTES+2*GUARD+1;
 if(mode==0&&index<nvec)printf("VECTOR,%u,%d,%u,%u,%u,%u\n",index,r9,pb?0:b.approx_fmt2,pb?0:b.approx_stretch,pb?0:b.approx_tile,pb?0:b.approx_blend);
 free_fixture(&f);
}
static void math_test(void){
 for(unsigned i=0;i<=65025;i++){check(opt_r255(i)==(i+127)/255);math_checks++;}
 for(unsigned k=0;k<256;k++)for(unsigned a=0;a<16;a++)for(unsigned sc=0;sc<16;sc++)for(unsigned dc=0;dc<16;dc++){
  uint32_t s=a|(sc<<4)|((15-sc)<<8)|(dc<<12),d=dc|(dc<<4)|(sc<<8)|((15-dc)<<12);
  check(ref_blend(s,d,2,k)==opt_blend(s,d,2,k));math_checks++;
 }
 for(unsigned i=0;i<200000;i++){
  uint32_t s=random9(),d=random9();unsigned k=random9()&255;check(ref_blend(s,d,4,k)==opt_blend(s,d,4,k));
  uint8_t t[4]={(uint8_t)s,(uint8_t)(s>>8),(uint8_t)(s>>16),(uint8_t)(s>>24)};unsigned m=random9()&255;
  check(ref_a8(m,t,d&65535,k)==opt_a8(m,t,d&65535,k));math_checks+=2;
 }
}
static struct vector random_vector(unsigned i){
 struct vector v={.op=i%7?1:0,.n=i%7?144:56};uint8_t*p=v.raw;set64(p,0x600000000);
 unsigned w=1+random9()%80,h=1+random9()%60,fmt=i%11==0?1:0;
 if(!v.op){set32(p+8,random9()%120);set32(p+12,random9()%120);set32(p+16,w);set32(p+20,h);set32(p+24,640);set32(p+28,fmt);set32(p+32,random9());p[36]=i%3;p[37]=(uint8_t)random9();p[38]=(uint8_t)(i%2);}
 else{
  set64(p+56,0x500000000);for(unsigned o=0;o<2;o++){set32(p+16+4*o,o?h:w);set32(p+32+4*o,o?h:w);set32(p+72+4*o,o?h:w);}set32(p+48,640);set32(p+52,fmt);set32(p+88,128);set32(p+92,fmt);p[112]=i%2;p[114]=(uint8_t)random9();p[121]=i%2;
  if(i%3==0&&!fmt){p[112]=1;p[115]=1;set32(p+8,3);set32(p+12,7);set32(p+24,9);set32(p+28,9);set32(p+32,50);set32(p+36,50);if(i%2){set32(p+72,1+random9()%90);set32(p+76,1+random9()%90);}else{set32(p+92,2);p[117]=14;p[111]=255;set32(p+108,random9()|0xff000000U);}}
  else if(i%5==0&&!fmt){set32(p+72,1+random9()%100);set32(p+76,1+random9()%90);p[112]=0;p[114]=255;}
  else {p[119]=(i>>1)&1;p[120]=(i>>2)&1;}
 }
 if(i%13==0)set32(p+(v.op?48:24),1); /* rejects retain atomic zero-write */
 if(i%17==0)p[v.op?113:36]=255;
 return v;
}
static double now9(void){struct timespec t;check(!clock_gettime(CLOCK_MONOTONIC,&t));return (double)t.tv_sec+t.tv_nsec*1e-9;}
/* Timings include submit/plan/spans/events, exclude setup, texture fill and reset.
 * Both versions run interleaved; all repeats write/compute actual observable data. */
static double timed(const struct vector*v,struct fixture*f,unsigned j,unsigned loops){
 struct gpe_context*c=&f->ctx[j];struct gpe_ref d={1,5},s=f->shared?d:(struct gpe_ref){2,9};
 if(j==0)v8_gpe_init(c,(struct gpe_hooks){0});else gpe_init(c,(struct gpe_hooks){0});
 check(!(j?gpe_register(c,d,f->db,f->dst[j]+GUARD+1,f->dstbytes):v8_gpe_register(c,d,f->db,f->dst[j]+GUARD+1,f->dstbytes)));
 if(v->op&&!f->shared)check(!(j?gpe_register(c,s,f->sb,f->src[j]+GUARD+1,f->srcbytes):v8_gpe_register(c,s,f->sb,f->src[j]+GUARD+1,f->srcbytes)));
 check(!(j?gpe_begin_batch(c,1):v8_gpe_begin_batch(c,1)));
 uint8_t raw[144];memcpy(raw,v->raw,v->n);raw[v->op?121:38]=1;memset(raw+(v->op?128:40),0,16);
 double start=now9();for(unsigned l=0;l<loops;l++){int r=j?gpe_submit(c,v->op,l,0,raw,v->n,d,s):v8_gpe_submit(c,v->op,l,0,raw,v->n,d,s);check(!r);}return (now9()-start)*1e6/loops;
}
static int cmp_double(const void*a,const void*b){double x=*(const double*)a,y=*(const double*)b;return (x>y)-(x<y);}
static void bench_one(unsigned i,const char*prefix,unsigned category){
 struct fixture f;make_fixture(&vectors[i],&f,0,0);double a[7],b[7];unsigned loops=12;
 (void)timed(&vectors[i],&f,0,1);(void)timed(&vectors[i],&f,1,1);
 for(unsigned j=0;j<7;j++){if(j&1){b[j]=timed(&vectors[i],&f,1,loops);a[j]=timed(&vectors[i],&f,0,loops);}else{a[j]=timed(&vectors[i],&f,0,loops);b[j]=timed(&vectors[i],&f,1,loops);}}
 qsort(a,7,sizeof(double),cmp_double);qsort(b,7,sizeof(double),cmp_double);
 printf("%s,%u,%u,%.6f,%.6f,%.4f,%u\n",prefix,i,loops,a[3],b[3],a[3]/b[3],category);free_fixture(&f);
}
static void benchmark(void){
 puts("PERF,index,loops,v8_us,v9_us,speedup,class_index");
 for(unsigned i=nvec-10;i<nvec;i++)bench_one(i,"PERF",i-(nvec-10));
 unsigned chosen[10];uint64_t area[10]={0};for(unsigned k=0;k<10;k++)chosen[k]=UINT32_MAX;
 for(unsigned i=0;i<nvec-10;i++){
  const struct vector*v=&vectors[i];struct gpe_plan p;if(plan9(v,&p,0)||p.bpp!=2||p.empty_clip_noop)continue;
  uint64_t base=get64(v->raw),end=p.dst-base+(uint64_t)(p.rows-1)*p.dst_step+p.line;
  if(p.dst<base||end>DBYTES)continue;
  if(v->op){uint64_t se=p.src+(uint64_t)(p.src_rows-1)*p.src_step+p.src_line,de=p.dst+(uint64_t)(p.rows-1)*p.dst_step+p.line;if(p.src<de&&p.dst<se)continue;}
  unsigned cat=!v->op?(p.approx_blend?1:0):p.approx_fmt2?(p.constant_alpha==255?8:9):p.approx_tile?7:p.approx_stretch==2?5:p.approx_stretch?6:!p.approx_blend?2:p.constant_alpha==255?3:4;
  uint64_t pixels=(uint64_t)p.rows*p.line/p.bpp;if(pixels>area[cat]){area[cat]=pixels;chosen[cat]=i;}
 }
 for(unsigned cat=0;cat<10;cat++)if(chosen[cat]!=UINT32_MAX)bench_one(chosen[cat],"HISTPERF",cat);
}

int main(int argc,char**argv){load_vectors();if(argc>1&&!strcmp(argv[1],"bench")){benchmark();free(vectors);free(texture);return 0;}
 math_test();differential(&vectors[nvec-7],5,nvec-7);for(unsigned i=0;i<nvec;i++){differential(&vectors[i],0,i);if(i%11==0)for(unsigned mode=1;mode<=4;mode++)differential(&vectors[i],mode,i);}
 for(unsigned i=0;i<1200;i++){struct vector v=random_vector(i);differential(&v,0,nvec+i);}
 printf("PASS checks=%llu math=%llu historical_and_canonical=%u accepted=%llu zero_write_rejects=%llu compared_bytes=%llu\n",(unsigned long long)checks,(unsigned long long)math_checks,nvec,(unsigned long long)accepted,(unsigned long long)zero_rejects,(unsigned long long)compared_bytes);
 free(vectors);free(texture);return 0;}
