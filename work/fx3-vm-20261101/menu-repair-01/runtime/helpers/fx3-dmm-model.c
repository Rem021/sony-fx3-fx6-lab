#include "fx3-dmm-model.h"
/* FX3 creator provenance unknown: never use A7C2 ELF frame offsets. */
unsigned int dmm_speech_initial_creator(const unsigned long *pcs,unsigned int n){(void)pcs;(void)n;return DMM_CREATOR_UNKNOWN;}
static unsigned int get(const unsigned char *p, unsigned int n) {
    unsigned int v = 0;
    for (unsigned int i = 0; i < n; ++i) v |= (unsigned int)p[i] << (8 * i);
    return v;
}
static void put(unsigned char *p, unsigned int v, unsigned int n) {
    for (unsigned int i = 0; i < n; ++i) p[i] = v >> (8 * i);
}
int dmm_service_reply(struct dmm_service *s, const unsigned char *q, unsigned int size, unsigned char *r) {
    if (!s || !q || !r || size < 40) return -1024;
    if (!s->memory || s->physical != DMM_TEST_PHYSICAL) return -1021;
    unsigned int op = get(q, 2), option = get(q + 22, 2), handle = get(q + 8, 4);
    if (op < 0x20 || op > 0x23) { if (op != 0x2a) return -1024; }
    for (int i = 0; i < 40; ++i) r[i] = 0;
    put(r, op | 0x8000, 2);
    put(r + 6, get(q + 20, 2), 2);
    put(r + 12, op == 0x20 ? 0xffffffffU : handle, 4);
    int raw = 0;
    unsigned int index = handle & 0x3ff;
    struct dmm_slot *slot = 0;
    if (op == 0x2a) {
        /* op2a is the original handle->physical-segments query (icdt.ko pins:
         * 40B request carries only op at +0 and handle at +8; reply 802a has
         * s16 status at +2, u16 segment count at +8, 16B records from +0x18
         * with u64 address at +0 and u32 length at +8). Same handle/generation
         * binding as ops 21..23; segment address uses the CP-side physical
         * domain already evidenced by the op20/21 reply convention. */
        if (index >= 2) raw = -0x105;
        else if (s->slots[index].handle != handle) raw = -0x205;
        else if (!s->slots[index].allocated) raw = -1;
        else {
            slot = s->slots + index;
            unsigned long long seg = s->physical - 0x400000000ULL + index * 0x80000ULL;
            put(r + 8, 1, 2);
            put(r + 0x18, (unsigned int)seg, 4);
            put(r + 0x1c, (unsigned int)(seg >> 32), 4);
            put(r + 0x20, 0x80000, 4);
        }
    } else if (op == 0x20) {
        if (option > 1) raw = -4; /* Other original options are outside this test model. */
        else if (get(q + 4, 4) != 0x63a) raw = -3;
        else {
            for (index = 0; index < 2 && s->slots[index].allocated; ++index) {}
            if (index == 2) raw = -0x201;
            else {
                if (s->allocations == ~0ULL) return -1021;
                slot = s->slots + index;
                slot->allocation_epoch = ++s->allocations;
                slot->creator_kind = DMM_CREATOR_UNKNOWN;
                /* CP C1E51E sets bit15; generations run 1..31 then 1. */
                slot->generation = slot->generation < 31 ? slot->generation + 1 : 1;
                handle = 0x8000U | (slot->generation << 10) | index;
                slot->handle = handle; slot->allocated = 1; slot->open_count = option;
                for (unsigned int i = 0; i < 0x80000; ++i) s->memory[index * 0x80000 + i] = 0;
                put(r + 12, handle, 4);
                put(r + 16, 0x63a, 4);
            }
        }
    } else {
        if (index >= 2) raw = -0x105;
        else if (s->slots[index].handle != handle) raw = -0x205;
        else if (!s->slots[index].allocated) raw = -1;
        else {
            slot = s->slots + index;
            if (op == 0x21) {
                if (option > 1) raw = -4;
                else if (slot->open_count == 255) raw = -1;
                else { ++slot->open_count; s->lifecycle_changed = 1; }
            } else if (op == 0x22) {
                if (option) raw = -4;
                else if (!slot->open_count) raw = 1;
                else { --slot->open_count; s->lifecycle_changed = 1; }
            } else {
                if (option != 0 && option != 2) raw = -4;
                else {
                    s->lifecycle_changed = 1;
                    if (option == 2 && slot->open_count) --slot->open_count;
                    raw = slot->open_count ? 3 : 0;
                    slot->open_count = 0; slot->allocated = 0;
                }
            }
        }
    }
    if (!raw && slot && ((op == 0x20 && option == 1) || op == 0x21)) {
        unsigned long long cp_address = s->physical - 0x400000000ULL + index * 0x80000;
        put(r + 8, 1, 2);
        put(r + 24, (unsigned int)cp_address, 4);
        put(r + 28, (unsigned int)(cp_address >> 32), 4);
        put(r + 32, 0x80000, 4);
    }
    int converted = raw == -0x201 ? -1 : (raw == -0x105 || raw == -0x205) ? -5 : raw;
    put(r + 10, (unsigned int)raw, 2);
    put(r + 2, (unsigned int)converted, 2);
    return 0;
}
