#include "../ldec_soft.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* A B, distance2/64-byte match, distance0 terminator => AB repeated33. */
    const uint8_t good[] = {0xf0,0x0c,'A','B',0xf0,2,0,0};
    uint8_t out[66];
    ldec_soft_info info;
    assert(ldec_soft_decode(good,sizeof(good),out,sizeof(out),&info)==0);
    for (size_t i=0;i<sizeof(out);++i) assert(out[i] == (i%2 ? 'B':'A'));
    assert(info.blocks == 1 && info.matches == 1 && info.max_distance == 2);
    for (size_t n=0;n<sizeof(good);++n) {
        memset(out,0xa5,sizeof(out));
        assert(ldec_soft_decode(good,n,out,sizeof(out),NULL)!=0);
        for (size_t i=0;i<sizeof(out);++i) assert(out[i] == 0xa5);
    }
    uint8_t buffer[128] = {0};
    memcpy(buffer,good,sizeof(good));
    assert(ldec_soft_decode(buffer,sizeof(good),buffer+1,66,NULL)==LDEC_E_OVERLAP);
    assert(ldec_soft_decode(good,sizeof(good),NULL,66,NULL)==0);
    assert(ldec_soft_decode(good,sizeof(good),NULL,67,NULL)!=0);
    puts("C ASan/UBSan + unchanged-on-failure + overlap checks passed");
    return 0;
}
