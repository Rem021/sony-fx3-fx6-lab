/* Explicit muted software storage. No original waveform or DMA execution. */
#define FF_BASE 0x41db00000ULL
#define FF_SIZE 0x60000U
#define FF_CAP 0xc800U
struct ff_slot {unsigned int handle,generation,opens,allocated,transferred,pending;unsigned int source_handle,source_offset,dest_offset,length;unsigned long long callback,context;};
struct ff_model {unsigned char *memory;struct ff_slot slots[6];};
static struct ff_model file_model;
static unsigned int ff_get(const unsigned char *p,unsigned int n){unsigned int v=0;for(unsigned int i=0;i<n;i++)v|=(unsigned int)p[i]<<(8*i);return v;}
static void ff_put(unsigned char *p,unsigned int v,unsigned int n){for(unsigned int i=0;i<n;i++)p[i]=v>>(8*i);}
static int ff_index(unsigned int h){unsigned int i=h&1023;if(!(h&0x8000)||i<2||i>7)return -1;i-=2;return file_model.slots[i].allocated&&file_model.slots[i].handle==h?(int)i:-1;}
static unsigned long long ff_cp(unsigned int i){return FF_BASE-0x400000000ULL+(unsigned long long)i*0x10000;}
static int ff_reply(const unsigned char *q,unsigned char *r){
 unsigned int op=ff_get(q,2),h=ff_get(q+8,4),option=ff_get(q+22,2);if(!file_model.memory||!((op>=0x20&&op<=0x23)||op==0x2a))return -1024;
 if(q[2]||q[3])return -1024;
 if(op==0x2a){for(int j=2;j<40;j++)if((j<8||j>=12)&&j!=20&&j!=21&&q[j])return -1024;}
 else{for(int j=24;j<40;j++)if(q[j])return -1024;}
 int index=-1,raw=0;if(op==0x20){
  if(ff_get(q+4,4)!=0x70817||h||ff_get(q+12,4)!=0xffffffff||ff_get(q+16,4)||option>1)return -1024;
  for(int i=0;i<6;i++)if(!file_model.slots[i].allocated&&file_model.slots[i].generation<31){index=i;break;}
  if(index<0)return -1021;struct ff_slot *s=file_model.slots+index;unsigned int g=s->generation+1;memset(s,0,sizeof *s);s->generation=g;s->handle=0x8000|(g<<10)|(index+2);s->opens=option;s->allocated=1;h=s->handle;memset(file_model.memory+index*0x10000,0,FF_CAP);
 }else{index=ff_index(h);if(index<0)return -1024;struct ff_slot *s=file_model.slots+index;
  if(op==0x21){if(option>1||s->opens==255)return -1024;s->opens++;}
  if(op==0x22){if(option||!s->opens)return -1024;s->opens--;}
  if(op==0x23){if((option!=0&&option!=2)||s->pending)return -1024;raw=option==2&&s->opens?s->opens-1:s->opens;raw=raw?3:0;s->opens=0;s->allocated=0;}
 }
 memset(r,0,40);ff_put(r,op|0x8000,2);ff_put(r+6,ff_get(q+20,2),2);ff_put(r+12,h,4);ff_put(r+2,raw,2);ff_put(r+10,raw,2);
 if(op==0x20)ff_put(r+16,0x70817,4);
 if(op==0x2a||op==0x21||(op==0x20&&option==1)){unsigned long long cp=ff_cp(index);ff_put(r+8,1,2);memcpy(r+24,&cp,8);ff_put(r+32,FF_CAP,4);}return 0;
}
struct ff_local {unsigned int handle,capacity,live;unsigned long long physical;};
static struct ff_local file_locals[8];
static int ff_local_index(unsigned int h){if(h&0x8000)return -1;for(int i=0;i<8;i++)if(file_locals[i].live&&file_locals[i].handle==h)return i;return -1;}
static int ff_transfer_check(unsigned int sh,unsigned int so,unsigned int dh,unsigned int off,unsigned int length,unsigned int mode){int i=ff_index(dh),l=ff_local_index(sh);if(i<0||l<0||!length||mode!=1)return -1024;struct ff_slot *s=file_model.slots+i;if(s->transferred||s->pending||so>file_locals[l].capacity||length>file_locals[l].capacity-so||off>FF_CAP||length>FF_CAP-off)return -1024;return i;}
