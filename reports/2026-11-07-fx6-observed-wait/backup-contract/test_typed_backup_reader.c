#include "typed_backup_reader.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned checks;
#define CHECK(x) do { assert(x); ++checks; } while (0)
#ifdef FX6_READER_TEST_ALLOC
static size_t fail_after=SIZE_MAX;
void *fx6_test_calloc(size_t count, size_t bytes) {
    if (fail_after==0) return NULL;
    if (fail_after!=SIZE_MAX) --fail_after;
    return calloc(count,bytes);
}
#endif
int main(void) {
    /* Synthetic fixtures only. Real pinned BK4 values are checked separately. */
    struct fx6_backup_record r = { .record_index=0, .item_count=4,
        .items={{0xfa0191,8,{0x78,0x56,0x34,0x12}},
                {0xfa0192,8,{0x00,0x10}},
                {0xfa01a3,8,{255,255,255,255,255,255,255,255}},
                {0xfa01a4,8,{255,255,255,255,255,255,255,255}}} };
    unsigned char guarded[32], unchanged[32];
    memset(guarded, 0xa5, sizeof guarded); memcpy(unchanged,guarded,sizeof guarded);
    CHECK(fx6_template_read_u64(&r,0xfa0191,guarded+7,8)==FX6_READ_OK);
    uint64_t value; memcpy(&value,guarded+7,8); CHECK(value==0x12345678);
    CHECK(!memcmp(guarded,unchanged,7)); CHECK(!memcmp(guarded+15,unchanged+15,17));
    for (size_t n=0;n<32;n++) if(n!=8) {
        memcpy(guarded,unchanged,sizeof guarded);
        CHECK(fx6_template_read_u64(&r,0xfa0191,guarded+7,n)==FX6_READ_BAD_SIZE);
        CHECK(!memcmp(guarded,unchanged,sizeof guarded));
    }
    CHECK(fx6_template_read_u64(&r,0x12345678,guarded+7,8)==FX6_READ_NOT_HANDLED);
    CHECK(!memcmp(guarded,unchanged,sizeof guarded));
    CHECK(fx6_template_read_u64(&r,0xfa0191,NULL,8)==FX6_READ_BAD_ARGUMENT);
    CHECK(fx6_template_read_u64(&r,0xfa01a3,&value,8)==FX6_READ_OK);
    CHECK(value==UINT64_MAX);
    r.items[2].length=7;
    CHECK(fx6_template_read_u64(&r,0xfa0191,guarded+7,8)==FX6_READ_BAD_RECORD);
    CHECK(!memcmp(guarded,unchanged,sizeof guarded)); r.items[2].length=8;
    r.items[2].id=r.items[1].id;
    CHECK(fx6_template_read_u64(&r,0xfa0191,guarded+7,8)==FX6_READ_BAD_RECORD);
    CHECK(!memcmp(guarded,unchanged,sizeof guarded)); r.items[2].id=0xfa01a3;
    r.record_index=2;
    CHECK(fx6_template_read_u64(&r,0xfa0191,guarded+7,8)==FX6_READ_BAD_RECORD);
    CHECK(!memcmp(guarded,unchanged,sizeof guarded));
    CHECK(!fx6_arena_create(0,1)); CHECK(!fx6_arena_create(16,0));
    CHECK(!fx6_arena_create(16,17)); CHECK(!fx6_arena_create(SIZE_MAX,1));
#ifdef FX6_READER_TEST_ALLOC
    fail_after=0; CHECK(!fx6_arena_create(4096,2048));
    fail_after=1; CHECK(!fx6_arena_create(4096,2048));
    fail_after=SIZE_MAX;
#endif
    CHECK(fx6_arena_read_u64(NULL,0xfa0192,guarded+7,8)==FX6_READ_NO_CAPABILITY);
    CHECK(!memcmp(guarded,unchanged,sizeof guarded));
    struct fx6_owned_arena *a=fx6_arena_create(4096,2048); CHECK(a);
    uint64_t base,capacity;
    CHECK(fx6_arena_read_u64(a,0xfa0191,&base,8)==FX6_READ_OK);
    CHECK(fx6_arena_read_u64(a,0xfa0192,&capacity,8)==FX6_READ_OK);
    CHECK(base!=0); CHECK(capacity==4096);
    /* Exercise actual backing boundary under ASan, not just scalar constants. */
    unsigned char *p=(unsigned char *)(uintptr_t)base;
    CHECK(p[0]==0 && p[capacity-1]==0); p[0]=0x12; p[capacity-1]=0x34;
    CHECK(p[0]==0x12 && p[capacity-1]==0x34);
    CHECK(fx6_arena_read_u64(a,0xfa01a3,guarded+7,8)==FX6_READ_NO_CAPABILITY);
    CHECK(fx6_arena_read_u64(a,0xfa01a4,guarded+7,8)==FX6_READ_NO_CAPABILITY);
    CHECK(fx6_arena_read_u64(a,0x12345678,guarded+7,8)==FX6_READ_NOT_HANDLED);
    CHECK(fx6_arena_read_u64(a,0xfa0192,guarded+7,4)==FX6_READ_BAD_SIZE);
    CHECK(!memcmp(guarded,unchanged,sizeof guarded));
    fx6_arena_destroy(a); fx6_arena_destroy(NULL);
    printf("{\"status\":\"PASS\",\"checks\":%u,\"scope\":\"host typed helper only\"}\n",checks);
}
