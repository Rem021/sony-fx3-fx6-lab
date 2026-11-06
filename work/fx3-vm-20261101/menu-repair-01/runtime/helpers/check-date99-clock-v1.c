
#include <assert.h>
#include <string.h>
#include <stdio.h>
typedef unsigned char B;typedef unsigned W;typedef unsigned long U;
static W rd16(const B*p){return p[0]|(W)p[1]<<8;}static void cp_copy(B*d,const B*s,U n){memcpy(d,s,n);}
#include "fx3-date99-clock-core-v1.h"
#include "date99-clock-fixture-v1.h"
int main(void){for(unsigned i=0;i<sizeof fixture99/sizeof *fixture99;i++){struct date99_clock c={0};B out[16];long utc;assert(!c99_build(&c,fixture99[i].d,fixture99[i].tz,1,8000000000UL,10000000000UL,7));assert(c.valid&&c.generation==7&&c.utc_ms==fixture99[i].utc&&c.basis_ns==9000000000UL);assert(!c99_read(&c,15123000000UL,out,&utc)&&utc==fixture99[i].utc+6123&&!memcmp(out,fixture99[i].expected,16));struct date99_clock old=c;B bad[16];memcpy(bad,fixture99[i].d,16);bad[2]=13;assert(c99_build(&c,bad,fixture99[i].tz,1,8,10,8)&&!memcmp(&c,&old,sizeof c));}
 B d[16]={0xe5,7,1,1},tz[8]={0},out[16];struct date99_clock c={0};d[12]=3;assert(!c99_build(&c,d,tz,4,1,10,1)&&!c.valid&&!c99_read(&c,11,out,0)&&!memcmp(out,d,16));assert(c99_build(&c,d,tz,1,1,10,2));d[12]=0;assert(c99_build(&c,d,tz,1,11,10,2));d[0]=0x34;d[1]=8;d[2]=2;d[3]=29;assert(c99_build(&c,d,tz,1,1,10,2));puts("DATE99_CLOCK_PASS 100independent_Python_datetime_vectors/UTC_TD_DST/type0_type1/leap_century/millisecond_monotonic_progress/half_RTT_basis/unknown_BY_BOOT/no_write_on_invalid");}
