/* Bounded byte storage for original face-registration records, no image/recognition engine. */
#define FR_BASE 0x41dd00000ULL
#define FR_SIZE 0x90000U
#define FR_MAX 0x64000U
static const unsigned fr_units[3]={0x1d9,0x1da,0x1db},fr_cap[3]={0x64000,0xc800,0xd100},fr_offset[3]={0,0x70000,0x80000},fr_extent[3]={0x223,0x224,0x225};
struct fr_slot {unsigned handle,generation,allocated,opens,pending,transfers,source_handle,source_offset,dest_offset,length;unsigned long callback,context,epoch;};
struct fr_model {unsigned char *memory;unsigned long allocations;struct fr_slot slots[3];};
static struct fr_model face_model;
struct fr_local {unsigned handle,unit,capacity,live;unsigned long long physical;};static struct fr_local face_locals[8];
static int fr_unit_index(unsigned unit){for(int i=0;i<3;i++)if(fr_units[i]==unit)return i;return -1;}
static int fr_index(unsigned h){unsigned i=h&1023;if(!(h&0x8000)||i<8||i>10)return -1;i-=8;return face_model.slots[i].allocated&&face_model.slots[i].handle==h?(int)i:-1;}
static unsigned long long fr_cp(unsigned i){return FR_BASE-0x400000000ULL+fr_offset[i];}
static int fr_reply(const unsigned char *q,unsigned char *r){unsigned op=ff_get(q,2),h=ff_get(q+8,4),option=ff_get(q+22,2);if(!face_model.memory||q[2]||q[3]||!((op>=0x20&&op<=0x23)||op==0x2a))return -1024;for(int j=24;j<40;j++)if(q[j])return -1024;int i;
 if(op==0x20){i=fr_unit_index(ff_get(q+4,4));if(i<0||h||ff_get(q+12,4)!=0xffffffff||ff_get(q+16,4)||option>1)return -1024;struct fr_slot *s=face_model.slots+i;if(s->allocated||s->pending||face_model.allocations==~0UL)return -1021;unsigned generation=s->generation<31?s->generation+1:1;memset(s,0,sizeof *s);s->handle=0x8000|(generation<<10)|(i+8);s->generation=generation;s->allocated=1;s->opens=option;s->epoch=++face_model.allocations;h=s->handle;memset(face_model.memory+fr_offset[i],0,fr_cap[i]);}
 else{i=fr_index(h);if(i<0)return -1024;if(op==0x21){if(ff_get(q+4,4)!=fr_units[i])return -1024;}else if(ff_get(q+4,4))return -1024;for(int j=12;j<20;j++)if(q[j])return -1024;struct fr_slot *s=face_model.slots+i;if(op==0x21){if(option>1||s->opens==255)return -1024;s->opens++;}else if(op==0x22){if(option||!s->opens)return -1024;s->opens--;}else if(op==0x23){if(option||s->opens||s->pending)return -1024;s->allocated=0;}else if(option)return -1024;}
 memset(r,0,40);ff_put(r,op|0x8000,2);ff_put(r+6,ff_get(q+20,2),2);ff_put(r+12,h,4);if(op==0x20)ff_put(r+16,fr_units[i],4);if(op==0x2a||op==0x21||(op==0x20&&option==1)){unsigned long long cp=fr_cp(i);ff_put(r+8,1,2);memcpy(r+24,&cp,8);ff_put(r+32,fr_cap[i],4);}return 0;}
static int fr_local_index(unsigned h){if(h&0x8000)return -1;for(int i=0;i<8;i++)if(face_locals[i].live&&face_locals[i].handle==h)return i;return -1;}
static int fr_transfer_check(unsigned sh,unsigned so,unsigned dh,unsigned off,unsigned length,unsigned mode){int i=fr_index(dh),l=fr_local_index(sh);if(i<0||l<0||!length||mode!=1)return -1024;struct fr_slot *s=face_model.slots+i;struct fr_local *local=face_locals+l;if(s->pending||local->unit!=fr_units[i]||local->capacity!=fr_cap[i]||!local->physical||so>local->capacity||length>local->capacity-so||off>fr_cap[i]||length>fr_cap[i]-off||local->physical<0x400000000ULL||local->physical+local->capacity>0x540000000ULL)return -1024;return i;}
