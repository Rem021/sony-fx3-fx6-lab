/* OUR Unicorn-only wrapper, not a Sony-loadable module or physical address map.
 * Only a modeled callsite is redirected. Original logging/locks/hardware and
 * all actual loader/CPU/mapping/cache synchronization remain unverified.
 */
typedef unsigned char u8;
typedef unsigned int u32;
static const u8 expected_hd16m[136]={
#include "expected_hd16m.inc"
};
extern int sony_matcher(const u8 *owner,const u8 *descriptor98);

int fx3_match_adapter(const u8 *owner,const u8 *source) {
    if (!owner || !source) return sony_matcher(owner,source);
    u8 view[152] __attribute__((aligned(16)));
    /* Validate the copied input, not an earlier view of source. The owner's
     * descriptor is only a bounded equality guard, NOT a trusted epoch/lock.
     */
    for (u32 i=0;i<152;i++) view[i]=source[i];
    u32 i=0;
    for (;i<136;i++) if (view[i]!=expected_hd16m[i]) break;
    if (i==136) {
        for (i=0;i<136;i++) if (owner[0xe110+i]!=expected_hd16m[i]) break;
        if (i==136 && *(u32*)(view+0x88)==1 && *(u32*)(view+0x8c)==10 &&
            *(u32*)(view+0x90)==25) {
            *(u32*)(view+0x38)=6;
            return sony_matcher(owner,view);
        }
    }
    return sony_matcher(owner,source);
}
