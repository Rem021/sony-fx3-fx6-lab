#include "bridge_core.h"
#include "callback_offsets.h"

static uint16_t rd16(const uint8_t* p) { return (uint16_t)(p[0] | ((uint16_t)p[1]<<8)); }
static uint32_t rd32(const uint8_t* p) {
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint64_t rd64(const uint8_t* p) { return (uint64_t)rd32(p)|((uint64_t)rd32(p+4)<<32); }
static void wr16(uint8_t* p,uint16_t v) { p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8); }
static void wr32(uint8_t* p,uint32_t v) {
    for(unsigned i=0;i<4;i++)p[i]=(uint8_t)(v>>(8*i));
}
static void wr64(uint8_t* p,uint64_t v) { wr32(p,(uint32_t)v);wr32(p+4,(uint32_t)(v>>32)); }
static void clear_plan(fx6diag_plan* p) {
    uint8_t* b=(uint8_t*)p;
    for(size_t i=0;i<sizeof(*p);i++)b[i]=0;
}
int fx6diag_map(const uint8_t* source,size_t length,
                 const uintptr_t thunks[57],fx6diag_plan* result) {
    if(!result)return FX6DIAG_MAP_LENGTH;
    clear_plan(result);
    if(!source||!thunks||length!=FX6DIAG_SOURCE_BYTES)return FX6DIAG_MAP_LENGTH;
    uint32_t count=rd32(source+0x268);
    if(count<1||count>4)return FX6DIAG_MAP_COUNT;
    for(unsigned i=0;i<4;i++)result->slots[i]=rd32(source+0x26c+4*i);
    for(unsigned i=0;i<count;i++) {
        if(result->slots[i]==0xffff)return FX6DIAG_MAP_SENTINEL;
        for(unsigned j=0;j<i;j++)if(result->slots[i]==result->slots[j])return FX6DIAG_MAP_DUPLICATE;
    }
    result->source_u16=rd16(source+0x28a);
    if(result->source_u16!=1440)return FX6DIAG_MAP_U16;
    result->count=count;
    for(unsigned i=0;i<8;i++)result->mapped[i]=source[i];
    for(unsigned i=0;i<57;i++) {
        uint64_t original=rd64(source+fx6diag_src_offsets[i]);
        result->original_callbacks[i]=original;
        if(original) {
            if(!thunks[i]||(uint64_t)thunks[i]==original)return FX6DIAG_MAP_THUNK;
            result->target_thunks[i]=(uint64_t)thunks[i];
            wr64(result->mapped+fx6diag_dst_offsets[i],(uint64_t)thunks[i]);
        }
    }
    for(unsigned i=0;i<18;i++) {
        uint64_t original=rd64(source+fx6diag_extra_offsets[i]);
        result->original_extra[i]=original;
        if(original)result->extra_nonnull++;
    }
    wr32(result->mapped+0x1d0,count);
    for(unsigned i=0;i<16;i++)result->mapped[0x1d4+i]=source[0x26c+i];
    for(unsigned i=0;i<14;i++)result->mapped[0x1e4+i]=source[0x27c+i];
    wr16(result->mapped+0x1f2,780); /* provisional FX3 Xavcs; EnterRec always stops */
    for(unsigned i=0;i<4;i++)result->mapped[0x1f4+i]=source[0x28c+i];
    return FX6DIAG_MAP_OK;
}
