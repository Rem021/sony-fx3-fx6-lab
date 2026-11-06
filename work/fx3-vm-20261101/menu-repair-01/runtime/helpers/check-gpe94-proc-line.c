#include <stdio.h>
#include <assert.h>
#include <string.h>
int main(void){const char*l="0002  0000    00000001  0000000f  00000000  00000000  ffffffff  00000002  429b00000 (400000000+29b00000)  06900000 ";unsigned a,b,c,d,e,f,g,h;unsigned long start,base,offset,bytes;int used=0;int n=sscanf(l,"%x %x %x %x %x %x %x %x %lx (%lx+%lx) %lx %n",&a,&b,&c,&d,&e,&f,&g,&h,&start,&base,&offset,&bytes,&used);assert(n==12&&!l[used]&&a<=65535&&offset<=~0UL-base&&start==base+offset&&bytes&&bytes<=~0UL-start);printf("PASS n=%d used=%d len=%lu id=%x all_schema_arithmetic_tail_tests_pass; only_duplicate_id_term_left_in_original_code3_predicate\n",n,used,strlen(l),a);return 0;}
