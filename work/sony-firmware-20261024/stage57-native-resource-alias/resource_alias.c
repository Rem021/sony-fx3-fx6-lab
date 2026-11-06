/* Guest-only AArch64 prototype. NOT a Sony-loadable module or hooked firmware.
 * Caller-owned context/session/epoch/notifications are explicit test fixtures.
 * All actual camera ABI, shared synchronization, consumer coverage and safe
 * code reclamation remain unbound. This code restores data only, never code.
 */
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned long long u64;
#define INLINE static __attribute__((always_inline)) inline
#define ORIGINAL ((const u8 *)0xffffffc0013c5798ULL)
#define MAGIC 0x4658334735373031ULL
#define MAX64 (~0ULL)

enum { ENTER=0, REGISTER_PACKET=1, FINISH_PRODUCER=2, FINISH_PACKET=3,
       CLOSE=4, RESTORE_DATA=5 };
enum { OK=0, BAD_ABI=1, BUSY=2, CLOSED=3, EPOCH=4, SCOPE=5, PIN=6,
       CAPACITY=7, TOKEN=8, STATE=9, HELD=10, FAULT=11, SEQUENCE=12,
       OWNER=13, BAD_OP=14 };
typedef struct { u64 id, kind, address; } Slot;
typedef struct {
    u64 magic, session, epoch, observed_epoch, owner;
    u64 gate, phase, fault, next_id, out_id, live, lock, data_restored;
    Slot slots[8];
} Control;
_Static_assert(sizeof(Control)==296, "Control ABI");
_Static_assert(__builtin_offsetof(Control, slots)==104, "slots ABI");
_Static_assert(__builtin_offsetof(Control, lock)==88, "lock ABI");

static const u8 expected_ff[256]={
#include "expected_ff.inc"
};

INLINE u64 done(Control *c,u64 status) {
    __atomic_store_n(&c->lock,0,__ATOMIC_RELEASE);
    return status;
}
INLINE u64 fault(Control *c,u64 status) {
    c->gate=0;c->fault=status;return status;
}
INLINE int matches(const u8 *p,int private_copy) {
    for (u32 i=0;i<256;i++) {
        u8 b=expected_ff[i];
        if (private_copy && i>=0xb0 && i<0xb4)
            b=(u8)(249999U >> ((i-0xb0)*8));
        if (p[i]!=b) return 0;
    }
    return 1;
}
static const u8 expected_hd16m[136]={
#include "expected_hd16m.inc"
};
INLINE int target_descriptor(const u8 *d) {
    for (u32 i=0;i<136;i++) if (d[i]!=expected_hd16m[i]) return 0;
    return 1;
}
INLINE int profile(const u8 *o) {
    return target_descriptor(o+0xe110) &&
        *(const u32*)(o+0xe470)==0x19450;
}
INLINE int audit(Control *c) {
    u64 count=0;
    for (u32 i=0;i<8;i++) {
        Slot *s=&c->slots[i];
        if (!s->id) {
            if (s->kind || s->address) return 0;
            continue;
        }
        if (s->kind!=1 && s->kind!=2) return 0;
        if ((s->kind==1 && s->address) || (s->kind==2 && !s->address)) return 0;
        for (u32 j=0;j<i;j++) if (c->slots[j].id==s->id) return 0;
        count++;
    }
    return count==c->live;
}
INLINE Slot *find(Control *c,u64 id,u64 kind) {
    if (!id) return (Slot*)0;
    for (u32 i=0;i<8;i++)
        if (c->slots[i].id==id && c->slots[i].kind==kind) return &c->slots[i];
    return (Slot*)0;
}
INLINE Slot *reserve(Control *c,u64 kind,u64 address) {
    if (!c->next_id || c->next_id==MAX64) { fault(c,SEQUENCE);return (Slot*)0; }
    for (u32 i=0;i<8;i++) if (!c->slots[i].id) {
        Slot *s=&c->slots[i];s->id=c->next_id++;s->kind=kind;s->address=address;
        c->live++;c->out_id=s->id;return s;
    }
    fault(c,CAPACITY);return (Slot*)0;
}

/* op, ticket, address, epoch and session are NOT Sony ABI or trusted callbacks.
 * Register a prepared parameter dependency before ending its producer lease.
 * CLOSE prevents new entrants, but a prior producer may still register output.
 * FINISH_PACKET assumes the actual consumer has completed: real notification
 * provenance is not implemented here and cannot be inferred from a token.
 */
u64 fx3_candidate(Control *c,u64 op,u64 ticket,u64 address,u64 epoch,u64 session) {
    if (!c || c->magic!=MAGIC) return BAD_ABI;
    u64 unlocked=0;
    if (!__atomic_compare_exchange_n(&c->lock,&unlocked,1,0,
                                    __ATOMIC_ACQUIRE,__ATOMIC_RELAXED)) return BUSY;
    c->out_id=0;
    if (c->session!=session || c->epoch!=epoch) return done(c,BAD_ABI);
    if (!audit(c)) return done(c,fault(c,STATE));
    u8 *o=(u8*)c->owner;
    u8 *copy=o+0xe010;
    u64 *selected=(u64*)(o+0xe000);
    if (op==CLOSE) { c->gate=0;return done(c,OK); }
    if (op==REGISTER_PACKET) {
        if (!find(c,ticket,1) || !address || (address&7))
            return done(c,fault(c,TOKEN));
        Slot *s=reserve(c,2,address);
        return done(c,s?OK:c->fault);
    }
    if (op==FINISH_PRODUCER || op==FINISH_PACKET) {
        Slot *s=find(c,ticket,op==FINISH_PRODUCER?1:2);
        if (!s || (op==FINISH_PACKET && s->address!=address))
            return done(c,fault(c,TOKEN));
        s->id=0;s->kind=0;s->address=0;c->live--;
        return done(c,OK);
    }
    if (op!=ENTER && op!=RESTORE_DATA) return done(c,BAD_OP);
    if (c->fault) return done(c,FAULT);
    if (c->observed_epoch!=c->epoch) return done(c,fault(c,EPOCH));
    if (!o || ((u64)o&7)) return done(c,fault(c,OWNER));
    if (!profile(o)) return done(c,SCOPE);
    if (!matches(ORIGINAL,0)) return done(c,fault(c,PIN));
    u64 pointer=__atomic_load_n(selected,__ATOMIC_ACQUIRE);
    if (op==RESTORE_DATA) {
        if (c->gate) return done(c,STATE);
        if (c->live) return done(c,HELD);
        if (c->phase!=1 || pointer!=(u64)copy || !matches(copy,1))
            return done(c,fault(c,OWNER));
        __atomic_store_n(selected,(u64)ORIGINAL,__ATOMIC_RELEASE);
        c->phase=0;c->data_restored=1;
        return done(c,OK);
    }
    if (!c->gate) return done(c,CLOSED);
    if ((c->phase==0 && pointer!=(u64)ORIGINAL) ||
        (c->phase==1 && (pointer!=(u64)copy || !matches(copy,1))) || c->phase>1)
        return done(c,fault(c,OWNER));
    Slot *s=reserve(c,1,0);
    if (!s) return done(c,c->fault);
    if (!c->phase) {
        for (u32 i=0;i<256;i++) copy[i]=ORIGINAL[i];
        *(u32*)(copy+0xb0)=249999U;
        c->phase=1;c->data_restored=0;
        __atomic_store_n(selected,(u64)copy,__ATOMIC_RELEASE);
    }
    return done(c,OK);
}


/* This is OUR guest-only ABI, never a Sony hook. A separate temporary view
 * changes only the quality used for table matching. Original source/common
 * descriptor stays FH/16M. Full owner/session/epoch/locking provenance is NOT
 * implemented; these are strict experimental inputs and a private lock only.
 */
u64 fx3_match_view(Control *c,const u8 *src,u8 *dst,u64 epoch,u64 session) {
    if (!c || c->magic!=MAGIC) return BAD_ABI;
    u64 unlocked=0;
    if (!__atomic_compare_exchange_n(&c->lock,&unlocked,1,0,
                                    __ATOMIC_ACQUIRE,__ATOMIC_RELAXED)) return BUSY;
    if (c->epoch!=epoch || c->session!=session) return done(c,BAD_ABI);
    if (c->fault || !audit(c)) return done(c,FAULT);
    if (!c->gate || c->phase || c->live) return done(c,CLOSED);
    if (c->observed_epoch!=c->epoch) return done(c,EPOCH);
    if (!c->owner || (c->owner&7)) return done(c,OWNER);
    if (!src || !dst || ((u64)src&3) || ((u64)dst&3)) return done(c,SCOPE);
    if ((u64)src>MAX64-152 || (u64)dst>MAX64-152) return done(c,SCOPE);
    if ((u64)src<(u64)dst+152 && (u64)dst<(u64)src+152) return done(c,SCOPE);
    const u8 *o=(const u8*)c->owner;
    if (!target_descriptor(src) || !target_descriptor(o+0xe110)) return done(c,SCOPE);
    if (*(const u32*)(src+0x88)!=1 || *(const u32*)(src+0x8c)!=10 ||
        *(const u32*)(src+0x90)!=25) return done(c,SCOPE);
    for (u32 i=0;i<152;i++) dst[i]=src[i];
    *(u32*)(dst+0x38)=6;
    return done(c,OK);
}
