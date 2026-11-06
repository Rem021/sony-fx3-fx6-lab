#define DATE_CLOCK_TEST 1
#include "seed-date-clock-v3.c"
#include <assert.h>
int osal_snd_sync_direct(unsigned int target,void *p){return -1;}
static struct clock_message make(int y,int mo,int d,int h,int minute){struct clock_message m={{0}};unsigned char *p=bytes(&m)+20;set16(p,y);p[2]=mo;p[3]=d;p[4]=h;p[5]=minute;return m;}
int main(void){
 struct clock_message a=make(2021,1,1,0,0);long n=seconds(&a);assert(!normalize_initial_utc(&a,540));unsigned char *p=bytes(&a)+20;assert(get16(p)==2020&&p[2]==12&&p[3]==31&&p[4]==15&&p[5]==0);assert(seconds(&a)+540*60==n);
 a=make(2024,3,1,4,30);assert(!normalize_initial_utc(&a,540));p=bytes(&a)+20;assert(get16(p)==2024&&p[2]==2&&p[3]==29&&p[4]==19&&p[5]==30);
 a=make(2021,1,1,0,0);n=seconds(&a);assert(!normalize_initial_utc(&a,0)&&seconds(&a)==n);
 a=make(2000,1,1,0,0);assert(normalize_initial_utc(&a,540));return 0;
}
