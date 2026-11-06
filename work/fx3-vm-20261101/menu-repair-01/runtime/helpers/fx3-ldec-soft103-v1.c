/* AP103 software LDEC device. Original 32-byte ABI, no original hardware IRQ.
 * UDIF field offsets corroborated against original kernel and ldec.ko.
 * Decoder attribution/license: lead-claude/impl/ldec-lz77/NOTICE.txt.
 */
#include <stddef.h>
#include <stdint.h>
#include "../../../lead-claude/impl/ldec-lz77/ldec_soft.c"
typedef unsigned long U;
typedef unsigned int W;
typedef unsigned char B;
struct request103 { uint64_t source; W source_bytes,destination,destination_bytes,records,channel; B source_cache_bypass,destination_cache_bypass,reserved[2]; };
struct file103 { W devno; void **data; };
struct ioctl103 { W command; U arg; W disk_change; };
struct node103 { const char *name; unsigned short type,major,minor,count; };
struct ops103 { int (*open)(struct file103*); int (*close)(struct file103*); int (*ioctl)(struct file103*,struct ioctl103*); void *read,*write,*seek,*mmap,*poll; };
_Static_assert(sizeof(struct request103)==32,"original ioctl size");
_Static_assert(offsetof(struct request103,destination)==12,"p32 offset");
_Static_assert(offsetof(struct ioctl103,arg)==8,"UDIF arg offset");
extern int printk(const char*,...);
extern void *vmalloc(U);extern void vfree(void*);
extern U __arch_copy_from_user(void*,const void*,U);
extern U arch_p32_to_p64(W),arch_va_to_phys(U);extern void *arch_phys_to_va(U);
extern int udif_cdev_register(void*),udif_cdev_unregister(void*);
extern struct node103 udif_devnodes[];
extern B __this_module[];
static U cdev103[256] __attribute__((aligned(64)));
static U opens103,calls103,success103,reject103;
static int registered103;
static const U magic103=0x313330314345444cUL;
static int user_span103(U a,U n){return a&&n&&a<(1UL<<39)&&n<=(1UL<<39)-a;}
static int legal_span103(U a,U n){
 /* Exact GPE native pools observed in original AP102 allocation registrations.
  * Test range is a separate AP103 FDT reservation, never an AP texture. */
 const U spans[][2]={{0x410524000UL,0x410924000UL},{0x410924000UL,0x410c64000UL},{0x410c64000UL,0x410e64000UL},{0x41d300000UL,0x41d400000UL}};
 if(!n)return 0;
 for(W i=0;i<4;i++)if(a>=spans[i][0]&&a<spans[i][1]&&n<=spans[i][1]-a)return 1;
 return 0;
}
static U hash103(const B*p,U n){U h=0xcbf29ce484222325UL;for(U i=0;i<n;i++){h^=p[i];h*=0x100000001b3UL;}return h;}
static int open103(struct file103*f){if(!f||!f->data||*f->data!=(void*)&magic103)return -22;U n=__atomic_add_fetch(&opens103,1,__ATOMIC_RELAXED);printk("FX3_LDEC103_OPEN count=%lu devno=%#x result=0 synthetic_ldec=1 original_ldec_hw=0\n",n,f->devno);return 0;}
static int close103(struct file103*f){return f&&f->data&&*f->data==(void*)&magic103?0:-22;}
static int ioctl103(struct file103*f,struct ioctl103*c){
 struct request103 r={0};ldec_soft_info info={0};B *src=0,*out=0,*dst=0,*old=0;U pa=0,hs=0,ho=0;int result=-22,decode=-1;const char*reason="abi";
 U seq=__atomic_add_fetch(&calls103,1,__ATOMIC_RELAXED);
 if(!f||!f->data||*f->data!=(void*)&magic103||!c||c->command!=1)goto done;
 /* RAW command1 has no encoded _IOC_SIZE or magic: exactly32B copied, no
  * copy_to_user/output-length field exists in the original ioctl handler. */
 reason="request_copy";result=-5;
 if(!user_span103(c->arg,32)||__arch_copy_from_user(&r,(void*)c->arg,32))goto done;
 result=-22;reason="length_or_flags";
 if(!r.source_bytes||!r.destination_bytes||r.source_bytes>16U*1024*1024||r.destination_bytes>16U*1024*1024||r.channel>15||r.records!=(r.destination_bytes+4095)/4096||r.source_cache_bypass>1||r.destination_cache_bypass>1||r.reserved[0]||r.reserved[1])goto done;
 reason="user_source";result=-5;if(!user_span103(r.source,r.source_bytes))goto done;
 reason="destination_range";result=-22;
 /* Call original converter only for its valid DDR p32 domain; invalid inputs
  * can trigger original debug policy. Never invent a high address by OR. */
 if(r.destination>0xfdffffffU)goto done;
 pa=arch_p32_to_p64(r.destination);
 if(!legal_span103(pa,r.destination_bytes))goto done;
 dst=arch_phys_to_va(pa);
 if(!dst||arch_va_to_phys((U)dst)!=pa||arch_va_to_phys((U)dst+r.destination_bytes-1)!=pa+r.destination_bytes-1)goto done;
 reason="allocation";result=-5;src=vmalloc(r.source_bytes);out=vmalloc(r.destination_bytes);old=vmalloc(r.destination_bytes);if(!src||!out||!old)goto done;
 reason="source_copy";if(__arch_copy_from_user(src,(void*)(U)r.source,r.source_bytes))goto done;
 hs=hash103(src,r.source_bytes);
 reason="decode";decode=ldec_soft_decode(src,r.source_bytes,out,r.destination_bytes,&info);
 if(decode||info.output_bytes!=r.destination_bytes||info.blocks!=r.records)goto done;
 /* Commit only fully decoded private output. The original bitmap WriteLock
  * is held by the calling Lz77Decoder; do not acquire its lock recursively. */
 for(U i=0;i<r.destination_bytes;i++)old[i]=dst[i];
 for(U i=0;i<r.destination_bytes;i++)dst[i]=out[i];
 __atomic_thread_fence(__ATOMIC_SEQ_CST);
 ho=hash103(dst,r.destination_bytes);if(ho!=hash103(out,r.destination_bytes)){for(U i=0;i<r.destination_bytes;i++)dst[i]=old[i];__atomic_thread_fence(__ATOMIC_SEQ_CST);reason="write_readback_rolled_back";goto done;}
 reason="complete";result=0;__atomic_add_fetch(&success103,1,__ATOMIC_RELAXED);
done:
 if(result)__atomic_add_fetch(&reject103,1,__ATOMIC_RELAXED);
 printk("FX3_LDEC103_IOCTL seq=%lu command=%u src=%#lx src_bytes=%u p32=%#x pa=%#lx dst_bytes=%u records=%u channel=%u source_bypass=%u destination_bypass=%u decode=%d blocks=%lu src_fnv=%#lx output_fnv=%#lx result=%d reason=%s synchronous=1 synthetic_ldec=1 original_ldec_hw=0\n",seq,c?c->command:0,(U)r.source,r.source_bytes,r.destination,pa,r.destination_bytes,r.records,r.channel,r.source_cache_bypass,r.destination_cache_bypass,decode,(U)info.blocks,hs,ho,result,reason);
 if(old)vfree(old);if(out)vfree(out);if(src)vfree(src);return result;
}
static struct ops103 ops={open103,close103,ioctl103,0,0,0,0,0};
int init_module(void){
 struct node103*n=&udif_devnodes[5];
 if(n->type||n->major!=251||n->minor!=205||n->count!=1||!n->name||n->name[0]!='l'||n->name[1]!='d'||n->name[2]!='e'||n->name[3]!='c'||n->name[4])return -22;
 cdev103[0]=(U)n;cdev103[1]=(U)&ops;cdev103[2]=(U)&magic103;cdev103[0x80/8]=(U)__this_module;
 int rc=udif_cdev_register(cdev103);if(!rc)registered103=1;
 printk("FX3_LDEC103_BOUND major=251 minor=205 ioctl_bytes=32 command=1 result=%d synthetic_ldec=1 original_ldec_hw=0 input_copy=1 output_private_then_commit=1 native_p32_converter=1 no_IRQ_or_DMA=1\n",rc);return rc;
}
void cleanup_module(void){if(registered103)udif_cdev_unregister(cdev103);printk("FX3_LDEC103_STOP opens=%lu calls=%lu success=%lu reject=%lu\n",opens103,calls103,success103,reject103);}
