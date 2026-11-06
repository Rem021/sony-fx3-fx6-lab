from pathlib import Path
import subprocess,json,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';source=(H/'fx3-osd-headless-v1.c').read_text();capture=source[source.index('static int capture('):source.index('static void ring_commit(')];commit=source[source.index('static void ring_commit('):source.index('static void *worker(')]
pre=r'''
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
'''
post=r'''
static void setup(void){identities=waits=signals=refs=reads=guards=releases=unlocks=leaves=reads_attempts=guards_attempts=0;memset(ids,0,sizeof ids);memset(&hm,0,sizeof hm);hm.pending=0x1003;hm.stage=2;hm.epoch=1;hm.descriptor[0]=3;hm.descriptor[1]=16;unsigned v=123;memcpy(hm.descriptor+8,&v,4);v=1;memcpy(hm.descriptor+12,&v,4);unsigned short d=640;memcpy(hm.descriptor+20,&d,2);d=480;memcpy(hm.descriptor+22,&d,2);fixture=(struct ho_frame){.token=123,.physical=0x43feb5100UL,.format=0,.width=640,.height=480,.stride=640,.span=614400,.fb=100,.bitmap=200,.entry=300,.allocation=1,.metadata=123,.fbformat=1,.sem=74};}
int main(void){unsigned char *out=malloc(HO_MAX);ring=calloc(1,HO_RESERVE);assert(out&&ring);for(U i=0;i<HO_MAX;i++)pixels[i]=(unsigned char)(i*7+3);for(failat=0;failat<=18;failat++){setup();struct ho_frame f={0};int rc=capture(&hm,&f,out);assert((rc==0)==(failat==0));assert(releases==refs&&unlocks==reads&&leaves==guards);assert(signals==(failat>=1&&failat<=3?0:failat==4?1:2));if(signals==2)assert(ids[0]==78&&ids[1]==88);if(signals==1)assert(ids[0]==88);unsigned char ack[8];if(rc)assert(ho_prepare_ack(&hm,ack)<0);else{assert(!memcmp(pixels,out,fixture.span));assert(!ho_commit(&hm,&f,1,1));assert(!ho_prepare_ack(&hm,ack));assert(ack[0]==3&&ack[1]==0x60);}}
 failat=0;setup();for(U seq=1;seq<=10;seq++){ring_commit(&hm,&fixture,pixels,seq);U *slot=(void *)(ring+HO_HEADER+((seq-1)%HO_SLOTS)*HO_SLOT_STRIDE);assert(slot[0]==seq&&slot[2]==seq&&slot[11]==fixture.span&&slot[12]==ho_hash(pixels,fixture.span));assert(!memcmp((unsigned char*)slot+HO_DATA,pixels,fixture.span));}assert(((U*)ring)[10]==2);free(ring);free(out);puts("HEADLESS_CAPTURE_PASS actual_capture_and_ring_code/19_native_lease_paths/all_releases_balanced/original_acquired_sem_ids/zero_ACK_on_failure/copy_byte_equal/8slot_commit_overwrite_hash");return 0;}
'''
p=H/'check-headless-native-capture-v1.c';p.write_text(pre+capture+commit+post);a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(H/'check-headless-native-capture-v1')];subprocess.run(a,check=True,capture_output=True);r=subprocess.run([str(H/'check-headless-native-capture-v1')],text=True,capture_output=True);receipt={'args':a,'exit':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'tested_source_sha256':hashlib.sha256(source.encode()).hexdigest(),'scope':'Exact native capture/ring_commit functions extracted unchanged; native API/identity/extent mocked; VM native dispatch pending'};(H/'headless-native-host-check.json').write_text(json.dumps(receipt,indent=2)+'\n');print(r.stdout,r.stderr);assert r.returncode==0
