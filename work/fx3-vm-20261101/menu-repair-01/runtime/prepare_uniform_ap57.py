from pathlib import Path
import json,subprocess,os,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-gpe-observe-v7.c').read_text();pos=s.index('static int fill(');end=s.index('static const char *names[]',pos)
s=s[:pos]+'''extern long read(int,void *,size_t);
extern char *strstr(const char *,const char *);
extern int sscanf(const char *,const char *,...);
extern int munmap(void *,size_t);
#include "fx3-gpe-uniform.c"
static int raster_failed;
static unsigned int fills_done;
static int (*draw_complete)(unsigned int,const void *,size_t);
static int extent_live(void){
 char data[65536];int fd=open("/proc/udm/dmm_extents",0);if(fd<0)return 0;long n=read(fd,data,sizeof(data)-1);close(fd);if(n<=0||n>=sizeof(data)-1)return 0;data[n]=0;
 char *line=data;while(line&&*line){unsigned int a,b,c,d,e,f,g,h;unsigned long start,parent,offset,bytes;
 if(sscanf(line,"%x %x %x %x %x %x %x %x %lx (%lx+%lx) %lx",&a,&b,&c,&d,&e,&f,&g,&h,&start,&parent,&offset,&bytes)==12&&d==0x545&&c==1&&g==3&&start==0x43feb5000UL&&bytes==0x140000UL)return 1;
 while(*line&&*line!='\\n')line++;if(*line)line++;else break;}return 0;
}
static int fill(int g,int c,unsigned int seq,unsigned int src,const void *p){
 unsigned int raw[14];struct uniform_plan plan;
 if(g||c||src||!p||pread(process_mem,raw,56,(long)p)!=56||uniform_plan(raw,&plan)||!extent_live()){raster_failed=1;return capture("fill",g,c,seq,src,p,56);}
 unsigned long base=plan.address&~4095UL,delta=plan.address-base,length=(delta+plan.span+4095)&~4095UL;
 void *area=mmap(0,length,3,1,physical,base);if(area==(void *)-1){raster_failed=1;return 5;}
 uniform_write((unsigned char *)area+delta,&plan);__atomic_thread_fence(__ATOMIC_SEQ_CST);
 int unmap=munmap(area,length);if(unmap||!extent_live()){raster_failed=1;return 5;}fills_done++;
 dprintf(2,"FX3_GPE_UNIFORM_DONE sequence=%u address=%#lx bytes=%lu rows=%u value=%u fills=%u result=0 pixels_written=1 physical_engine=0 lifetime=original_FIFO_pending_completion\\n",seq,plan.address,plan.line*plan.rows,plan.rows,plan.value,fills_done);return 0;
}
static int blit(int g,int c,unsigned int seq,unsigned int src,const void *p){raster_failed=1;return capture("blit",g,c,seq,src,p,144);}
static int flush(int g,int c,unsigned int seq,unsigned int src,const void *p){
 unsigned char raw[24];if(g||c||raster_failed||!fills_done||!p||pread(process_mem,raw,24,(long)p)!=24||!draw_complete)return capture("flush",g,c,seq,src,p,24);
 for(unsigned int i=0;i<24;i++)if(raw[i])return capture("flush",g,c,seq,src,p,24);
 int status=0,ok=!src||draw_complete(src,&status,4);if(!ok){raster_failed=1;return 5;}
 dprintf(2,"FX3_GPE_UNIFORM_FLUSH sequence=%u source=%#x fills=%u status=0 native_SendDrawComp=%d physical_engine=0\\n",seq,src,fills_done,src!=0);return 0;
}
''' +s[end:]
s=s.replace('get_instance=dlsym(h,','draw_complete=dlsym(h,"_ZN5mpgpe7message12SendDrawCompEjPKvm");\n get_instance=dlsym(h,');(H/'fx3-gpe-observe-v9.c').write_text(s)
x=json.loads((H/'fx3-gpe-observe-v7-build.json').read_text());args=[a.replace('fx3-gpe-observe-v7','fx3-gpe-observe-v9') for a in x['args']];env=os.environ.copy();env.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));v=subprocess.run(args,capture_output=True,text=True,env=env);assert not v.returncode,v.stderr;(H/'fx3-gpe-observe-v9-build.json').write_text(json.dumps({'args':args,'exit':v.returncode,'stderr':v.stderr,'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'output_sha256':hashlib.sha256((H/'fx3-gpe-observe-v9.so').read_bytes()).hexdigest(),'core_sha256':hashlib.sha256((H/'fx3-gpe-uniform.c').read_bytes()).hexdigest(),'scope':'FX3 exact liveDMM545/43feb5000/140000 originalFIFO uniformoverwrite subset; no callbacks/blit/blend, native SendDrawComp only after CPU writes; no independent allocator pin claimed'},indent=2)+'\n')
s=(R/'prepare_futex_ap55.py').read_text().replace('ap55-futex-lock','ap57-uniform-fill').replace("base=R/'ap53-plane-cache/candidate53.json'","base=R/'ap55-futex-lock/candidate55.json'").replace('candidate55.json','candidate57.json').replace("base=R/'ap55-futex-lock/candidate57.json'","base=R/'ap55-futex-lock/candidate55.json'");s=s.replace("if name=='simulation/fx3-capid-v1.so':","if name=='simulation/fx3-gpe-observe-v7.so':data=(R/'helpers/fx3-gpe-observe-v9.so').read_bytes()\n if name=='simulation/fx3-capid-v1.so':");s=s.replace('Boundedproviderobserver and GPE requestcapture only; no pixelwrites.','Explicit GPE liveDMM545 uniformoverwrite softwaremodel; originalFIFO/nativeSendDrawComp, all other draws unsupported.');(R/'build_uniform_candidate57.py').write_text(s)
