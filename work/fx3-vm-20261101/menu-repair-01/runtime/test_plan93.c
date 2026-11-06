#include <assert.h>
#include "helpers/fx3-input93-plan-v1.h"
int main(void){struct plan93 p={1,0,0,0};assert(plan93_accept(&p,1,0x1ab));assert(!plan93_accept(&p,1,0x30));assert(!plan93_accept(&p,2,3));assert(!plan93_accept(&p,3,0x1ac));for(unsigned i=4;i<=15;i++)assert(!plan93_accept(&p,i,0x1ac));assert(plan93_accept(&p,16,0x1ac));assert(!plan93_accept(&p,16,0x1ab));unsigned k[]={0x30,0x30,0x1af,0x1ac};for(unsigned i=0;i<4;i++)assert(!plan93_accept(&p,17+i,k[i]));assert(p.phase==2);assert(plan93_accept(&p,21,0x1ac));return 0;}
