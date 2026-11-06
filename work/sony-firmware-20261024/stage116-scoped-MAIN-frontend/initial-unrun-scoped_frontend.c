/* OUR GUEST-ONLY COPY PREPARER: no firmware hook, camera ABI or deployable code.
 * Gate address/ranges/epochs/callsites are explicit Unicorn fixture inputs.
 * No actual Sony lock, idle state, config epoch or allocation is established.
 * Opaque external-data pointers stay borrowed until the real setter copies them.
 */
typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef struct {
    u64 magic, armed, session, epoch, observed_epoch, idle;
    u64 source, destination, source_bytes, destination_bytes;
} Gate;
_Static_assert(sizeof(Gate)==80,"guest-only gate ABI");
extern u32 sony_type(u32 codec,u32 resolution,u32 color,u32 depth,u32 gop);
extern void sony_ctor(void *object);
extern void *sony_copy(void *destination,const void *source,u64 count);
enum { OK=0, BAD_GATE=1, CLOSED=2, EPOCH=3, SITE=4, RANGE=5, PROFILE=6, TYPE=7 };
static int span(u64 a,u64 n) {
    return a>=0x11000000ULL && a<=0x11010000ULL && n<=0x11010000ULL-a;
}
u32 fx3_prepare_main(const Gate *g,const u8 *src,u8 *dst,u64 site,u64 epoch) {
    if ((u64)g!=0x1100d000ULL || g->magic!=0x46583346524f4e54ULL) return BAD_GATE;
    if (g->armed!=1 || !g->session || g->idle!=1) return CLOSED;
    if (epoch!=g->epoch || g->observed_epoch!=g->epoch) return EPOCH;
    if (site!=0x2e6f7bcULL && site!=0x2e6f9b0ULL) return SITE;
    if (!src || !dst || ((u64)src&7) || ((u64)dst&7) ||
        g->source!=(u64)src || g->destination!=(u64)dst ||
        g->source_bytes!=0x1c0 || g->destination_bytes!=0x1c0 ||
        !span((u64)src,0x1c0) || !span((u64)dst,0x1c0) ||
        ((u64)src<(u64)dst+0x1c0 && (u64)dst<(u64)src+0x1c0)) return RANGE;
    if (*(const u32*)(src+0x170)!=5 || *(const u32*)(src+0x174)!=6 ||
        *(const u32*)(src+0x178)!=3) return PROFILE;
    u32 type=sony_type(1,2,0,1,0);
    if (type!=6) return TYPE;
    sony_ctor(dst); /* Original constructor clears all448 bytes. */
    sony_copy(dst,src,0x1bd); /* Preserve original setter's445-byte value span. */
    *(u32*)(dst+0x170)=type; /* Logical quality6/frame3 remain unchanged. */
    return OK;
}
