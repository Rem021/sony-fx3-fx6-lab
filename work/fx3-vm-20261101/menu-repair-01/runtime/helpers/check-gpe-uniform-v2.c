#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "fx3-gpe-uniform-v2.c"
int main(void){
 unsigned int p[14]={0x3feb5100,4,0,0,640,480,640,0,0,0x1ff00,0,0,0,0};struct uniform_plan z={0};assert(!uniform_plan(p,&z)&&z.span==614400&&z.pitch==1280);
 unsigned char *mem=malloc(z.span+32);memset(mem,0xa5,z.span+32);uniform_write(mem+16,&z);for(unsigned long i=0;i<z.span;i++)assert(!mem[16+i]);for(int i=0;i<16;i++)assert(mem[i]==0xa5&&mem[z.span+16+i]==0xa5);
 p[8]=0xffffffff;assert(!uniform_plan(p,&z));uniform_write(mem+16,&z);assert(mem[16]==255&&mem[16+z.span-1]==255);
 p[8]=0xff010203;assert(uniform_plan(p,&z)==5);p[8]=0;p[10]=1;assert(uniform_plan(p,&z)==5);p[10]=0;p[9]=0;assert(uniform_plan(p,&z)==5);p[9]=0x1ff00;p[0]=0x3fffffff;assert(uniform_plan(p,&z)==5);p[0]=0x3feb5100;p[4]=641;assert(uniform_plan(p,&z)==5);p[4]=640;p[3]=2000;assert(uniform_plan(p,&z)==5);free(mem);puts("FX3_UNIFORM_PASS captured640x480/614400B guards, white packing, unsupported colours/callback/blend/range/stride rejected");
}
