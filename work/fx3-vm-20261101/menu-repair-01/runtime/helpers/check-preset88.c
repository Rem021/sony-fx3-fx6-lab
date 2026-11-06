
#include <assert.h>
#include <string.h>
#include <stdarg.h>
typedef unsigned long U;typedef unsigned int W;struct ctx{U pc,continuation,id,objreg;};static int pmem=1,err;static U epoch;static __thread U preset_task,preset_tid,preset_epoch,preset_values[4];static __thread unsigned preset_valid;static W data[4]={11,22,33,44};static U tid=352;static int readable=1;
static int*__errno_location(void){return &err;}static long syscall(long n,...){assert(n==178);return tid;}static long pread(int fd,void*p,U n,long off){assert(fd==1&&off==0x1001bc&&n==16);if(!readable)return -1;memcpy(p,data,16);return 16;}static int dprintf(int fd,const char*f,...){assert(fd==2);(void)f;return 0;}
static int peek(U p,void *out,U n){return pmem>=0&&p>=4096&&p<0x8000000000UL&&n<=0x8000000000UL-p&&pread(pmem,out,n,p)==(long)n;}
int fx3_timecode_preset_context(U *out,unsigned capacity){if(!out||capacity<7||!preset_valid||preset_tid!=(U)syscall(178))return 0;W current[4];if(!peek(preset_task+0x1bc,current,16))return 0;for(unsigned i=0;i<4;i++)if(current[i]!=preset_values[i])return 0;out[0]=preset_task;out[1]=preset_tid;out[2]=preset_epoch;for(unsigned i=0;i<4;i++)out[i+3]=preset_values[i];return 7;}
__attribute__((visibility("hidden"))) void fx3_display_event(struct ctx *c,U *r){int saved=*__errno_location();U id=c->id;
 if(id==24){preset_valid=0;preset_task=r[0];preset_tid=syscall(178);preset_epoch=__atomic_add_fetch(&epoch,1,__ATOMIC_RELAXED);W values[4];if(peek(preset_task+0x1bc,values,16)){for(unsigned j=0;j<4;j++)preset_values[j]=values[j];preset_valid=1;}dprintf(2,"FX3_PRESET_CONTEXT_CAPTURE epoch=%lu tid=%lu task=%#lx readable=%u words=%#lx,%#lx,%#lx,%#lx original_entry=2dca610\n",preset_epoch,preset_tid,preset_task,preset_valid,preset_values[0],preset_values[1],preset_values[2],preset_values[3]);}
 if(id==37){preset_valid=0;dprintf(2,"FX3_PRESET_CONTEXT_RETIRED epoch=%lu tid=%lu original_RET=2dca6e0\n",preset_epoch,preset_tid);}
 *__errno_location()=saved;
}
int main(void){U out[7],regs[31]={0x100000};struct ctx c={0,0,24,31};assert(!fx3_timecode_preset_context(out,7));fx3_display_event(&c,regs);assert(preset_valid&&preset_epoch==1&&fx3_timecode_preset_context(out,7)==7&&out[0]==0x100000&&out[1]==352&&out[2]==1&&out[3]==11&&out[6]==44);assert(!fx3_timecode_preset_context(out,6));for(unsigned i=0;i<4;i++){data[i]++;assert(!fx3_timecode_preset_context(out,7));data[i]--;}tid++;assert(!fx3_timecode_preset_context(out,7));tid--;c.id=37;fx3_display_event(&c,regs);assert(!preset_valid&&!fx3_timecode_preset_context(out,7));c.id=24;readable=0;fx3_display_event(&c,regs);assert(!preset_valid&&!fx3_timecode_preset_context(out,7));readable=1;fx3_display_event(&c,regs);assert(fx3_timecode_preset_context(out,7)==7&&out[2]==3);return 0;}
