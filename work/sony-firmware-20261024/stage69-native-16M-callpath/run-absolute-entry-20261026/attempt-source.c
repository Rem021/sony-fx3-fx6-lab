/* OUR bounded guest-only adapter. These addresses/control fields are declared
 * Unicorn fixtures, not a camera ABI, trusted configuration epoch or hook.
 * The reject boundary is observed before its body: it is NOT Sony error handling.
 * No Linux service, actual loader, cache publication, hardware or recovery claim.
 */
typedef unsigned char u8;
typedef unsigned int u32;
typedef unsigned long long u64;
typedef struct { u64 id,kind,address; } Slot;
typedef struct {
    u64 magic,session,epoch,observed_epoch,owner;
    u64 gate,phase,fault,next_id,out_id,live,lock,data_restored;
    Slot slots[8];
} Control;
typedef struct { u64 trace,target,cpb; } Rate;
_Static_assert(sizeof(Control)==296,"control layout");
_Static_assert(sizeof(Rate)==24,"indirect rate result");
#define CONTROL ((Control*)0x113a0000ULL)
#define WRITER ((u64(*)(Control*,u64,u64,u64,u64,u64))0x13000000ULL)
static const u8 expected_hd16m[136]={
#include "expected_hd16m.inc"
};
extern Rate sony_rate(const u8 *owner);
extern u32 sony_channel(u8 *owner,void *output,u32 format,u32 mode);

__attribute__((noreturn,noinline)) void fx3_reject_boundary(u64 reason) {
    __asm__ volatile("" : : "r"(reason) : "memory");
    __builtin_trap();
}

u32 fx3_channel_adapter(u8 *owner,void *output,u32 format,u32 mode) {
    u32 i=0;
    if (!owner) return sony_channel(owner,output,format,mode);
    for (;i<136;i++) if (owner[0xe110+i]!=expected_hd16m[i]) break;
    if (i==136 && *(u32*)(owner+0xe470)==0x19450U) {
        Control *c=CONTROL;
        if ((u64)owner!=c->owner) fx3_reject_boundary(0x1001);
        u64 status=WRITER(c,0,0,0,c->epoch,c->session);
        if (status) fx3_reject_boundary(status);
        Rate rate=sony_rate(owner);
        if (rate.trace!=25999360ULL || rate.target!=16000000ULL || rate.cpb!=26000000ULL)
            fx3_reject_boundary(0x1002);
        /* Keep the original writer lease live while this original request is
         * in flight. No invented completion, packet notification or rollback.
         */
    }
    return sony_channel(owner,output,format,mode);
}
