
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
typedef unsigned long U;
#include "fx3-osd-core-v1.h"
static struct ho_model hm;static unsigned char *ring;
static struct ho_frame fixture;
static int failat,identities,waits,signals,refs,reads,guards,releases,unlocks,leaves,reads_attempts,guards_attempts;
static U ids[4];static unsigned char pixels[HO_MAX];
static int resolve_frame_api(void){return failat==1?-1:0;}
static int identity(struct ho_frame *f,U *data,U *a,U *b){identities++;if((failat==2&&identities==1)||(failat==5&&identities==2)||(failat==13&&identities==3))return -1;*f=fixture;*data=99;*a=88;*b=78;if(failat==6&&identities==2)*b=79;if(failat==14&&identities==3)*a=89;return 0;}
static int poll_sem(unsigned id){assert(id==88||id==78);waits++;return (failat==3&&id==88)||(failat==4&&id==78)?-1:0;}
static int bref(void *p){assert((U)p==fixture.bitmap);if(failat==7)return -1;refs++;return 0;}
static int bread(void *p,int mode,const void **bits){assert((U)p==fixture.bitmap&&mode==0);reads_attempts++;if(failat==8)return -1;reads++;*bits=pixels;return 0;}
static int raster_try(void){guards_attempts++;if(failat==9)return -1;guards++;return 0;}
static int bsize(void *p,U *n){assert((U)p==fixture.bitmap);*n=failat==10?4:fixture.span;return 0;}
static int extent(U p,U n){assert(p==fixture.physical&&n==fixture.span);return failat!=11;}
static int peek(U p,void *out,U n){assert(p==(U)pixels&&n==fixture.span);if(failat==12)return 0;memcpy(out,pixels,n);return 1;}
static int raster_leave(void){leaves++;return failat==15?-1:0;}
static int bunlock(void *p){assert((U)p==fixture.bitmap);unlocks++;return failat==16?-1:0;}
static int brelease(void *p){assert((U)p==fixture.bitmap);releases++;return failat==17?-1:0;}
static int hsignal(unsigned id){assert(id==88||id==78);ids[signals++]=id;return failat==18?-1:0;}
static int mock_usleep(unsigned n){assert(n==2000);return 0;}
#define usleep mock_usleep
static int capture(const struct ho_model *job,struct ho_frame *f,unsigned char *output){U data=0,sem88=0,sem78=0,held88=0,held78=0,bytes=0;int a=0,b=0,ref=0,reader=0,guard=0,ok=0,rc=0;const void *bits=0;struct ho_frame current={0};
 if(resolve_frame_api())return -1;if(identity(f,&data,&sem88,&sem78))return -2;
 if((rc=poll_sem((unsigned)sem88)))return -3;a=1;held88=sem88;if((rc=poll_sem((unsigned)sem78)))goto cleanup;b=1;held78=sem78;
 if(identity(&current,&data,&sem88,&sem78)||current.fb!=f->fb||current.bitmap!=f->bitmap||current.entry!=f->entry||sem88!=held88||sem78!=held78){rc=-4;goto cleanup;}*f=current;
 if((rc=bref((void *)f->bitmap)))goto cleanup;ref=1;
 for(unsigned i=0;i<201;i++){rc=bread((void *)f->bitmap,0,&bits);if(!rc&&bits){reader=1;break;}if(i<200)usleep(2000);}if(!reader){rc=-5;goto cleanup;}
 for(unsigned i=0;i<201;i++){rc=raster_try();if(!rc){guard=1;break;}if(i<200)usleep(2000);}if(!guard){rc=-6;goto cleanup;}
 if(bsize((void *)f->bitmap,&bytes)||ho_validate(job,f,bytes,extent(f->physical,f->span),0x43feb5000UL,0x140000UL)){rc=-7;goto cleanup;}
 if(!peek((U)bits,output,f->span)){rc=-8;goto cleanup;}struct ho_frame after={0};if(identity(&after,&data,&sem88,&sem78)||after.bitmap!=f->bitmap||after.physical!=f->physical||after.metadata!=f->metadata||after.entry!=f->entry||sem88!=held88||sem78!=held78||!extent(f->physical,f->span)){rc=-9;goto cleanup;}ok=1;
 cleanup:if(guard&&raster_leave())ok=0;if(reader&&bunlock((void *)f->bitmap))ok=0;if(ref&&brelease((void *)f->bitmap))ok=0;if(b&&hsignal((unsigned)held78))ok=0;if(a&&hsignal((unsigned)held88))ok=0;
 dprintf(2,"FX3_OSD_HEADLESS_LEASE fb=%#lx bitmap=%#lx sem88=%#lx sem78=%#lx read_lease=%d raster_guard=%d span=%lu result=%d original_publish_sem_untouched=1\n",f->fb,f->bitmap,sem88,sem78,reader,guard,f->span,ok?0:rc);return ok?0:-10;
}
static void ring_commit(const struct ho_model *job,const struct ho_frame *f,const unsigned char *bytes,U seq){U index=(seq-1)%HO_SLOTS;unsigned char *slot=ring+HO_HEADER+index*HO_SLOT_STRIDE;U *w=(void *)slot;U old=__atomic_load_n(w,__ATOMIC_ACQUIRE);__atomic_store_n(w,0,__ATOMIC_RELEASE);memset(slot+8,0,HO_DATA-8);memcpy(slot+HO_DATA,bytes,f->span);w[1]=hm.epoch;w[2]=seq;w[3]=job->pending;w[4]=job->pending==0x1003?seq:job->source_seq;w[5]=f->token;w[6]=f->physical;w[7]=f->format;w[8]=f->width;w[9]=f->height;w[10]=f->stride;w[11]=f->span;w[12]=ho_hash(bytes,f->span);w[13]=f->fb;w[14]=f->bitmap;w[15]=f->entry;w[16]=f->allocation;w[17]=f->metadata;w[18]=f->fbformat;w[19]=f->sem;w[20]=f->config_hash;memcpy(slot+0xc0,job->descriptor,36);__atomic_thread_fence(__ATOMIC_SEQ_CST);__atomic_store_n(w,seq,__ATOMIC_RELEASE);if(old)((U *)ring)[10]++;}

static void setup(void){identities=waits=signals=refs=reads=guards=releases=unlocks=leaves=reads_attempts=guards_attempts=0;memset(ids,0,sizeof ids);memset(&hm,0,sizeof hm);hm.pending=0x1003;hm.stage=2;hm.epoch=1;hm.descriptor[0]=3;hm.descriptor[1]=16;unsigned v=123;memcpy(hm.descriptor+8,&v,4);v=1;memcpy(hm.descriptor+12,&v,4);unsigned short d=640;memcpy(hm.descriptor+20,&d,2);d=480;memcpy(hm.descriptor+22,&d,2);fixture=(struct ho_frame){.token=123,.physical=0x43feb5100UL,.format=0,.width=640,.height=480,.stride=640,.span=614400,.fb=100,.bitmap=200,.entry=300,.allocation=1,.metadata=123,.fbformat=1,.sem=74};}
int main(void){unsigned char *out=malloc(HO_MAX);ring=calloc(1,HO_RESERVE);assert(out&&ring);for(U i=0;i<HO_MAX;i++)pixels[i]=(unsigned char)(i*7+3);for(failat=0;failat<=18;failat++){setup();struct ho_frame f={0};int rc=capture(&hm,&f,out);assert((rc==0)==(failat==0));assert(releases==refs&&unlocks==reads&&leaves==guards);assert(signals==(failat>=1&&failat<=3?0:failat==4?1:2));if(signals==2)assert(ids[0]==78&&ids[1]==88);if(signals==1)assert(ids[0]==88);unsigned char ack[8];if(rc)assert(ho_prepare_ack(&hm,ack)<0);else{assert(!memcmp(pixels,out,fixture.span));assert(!ho_commit(&hm,&f,1,1));assert(!ho_prepare_ack(&hm,ack));assert(ack[0]==3&&ack[1]==0x60);}}
 failat=0;setup();for(U seq=1;seq<=10;seq++){ring_commit(&hm,&fixture,pixels,seq);U *slot=(void *)(ring+HO_HEADER+((seq-1)%HO_SLOTS)*HO_SLOT_STRIDE);assert(slot[0]==seq&&slot[2]==seq&&slot[11]==fixture.span&&slot[12]==ho_hash(pixels,fixture.span));assert(!memcmp((unsigned char*)slot+HO_DATA,pixels,fixture.span));}assert(((U*)ring)[10]==2);free(ring);free(out);puts("HEADLESS_CAPTURE_PASS actual_capture_and_ring_code/19_native_lease_paths/all_releases_balanced/original_acquired_sem_ids/zero_ACK_on_failure/copy_byte_equal/8slot_commit_overwrite_hash");return 0;}
