/* msg_398ba0ce872e: bounded adapter serialization; original FIFO/pixel math unchanged. */
#ifdef FX3_GPE102_HOST_TEST
#include <time.h>
typedef struct timespec gpe102_timespec;
#define GPE102_CLOCK_MONOTONIC CLOCK_MONOTONIC
#else
typedef struct{long tv_sec,tv_nsec;}gpe102_timespec;
extern int clock_gettime(int,gpe102_timespec*);extern int nanosleep(const gpe102_timespec*,gpe102_timespec*);
#define GPE102_CLOCK_MONOTONIC 1
#endif
static U gpe102_now(void){gpe102_timespec t;if(clock_gettime(GPE102_CLOCK_MONOTONIC,&t))return 0;return(U)t.tv_sec*1000000000UL+(U)t.tv_nsec;}
static int gpe102_take(unsigned char*lock,unsigned seq,unsigned op){
 if(!__atomic_test_and_set(lock,__ATOMIC_ACQUIRE))return 0;
 int saved=*__errno_location();U start=gpe102_now(),now=start;unsigned waits=0;int failed=0;
 if(!start)failed=1;
 while(!failed){
  now=gpe102_now();if(!now||now<start||now-start>=500000000UL){failed=1;break;}
  gpe102_timespec delay={0,250000};nanosleep(&delay,0);waits++;
  if(!__atomic_test_and_set(lock,__ATOMIC_ACQUIRE))break;
 }
 U ended=gpe102_now();dprintf(2,"FX3_GPE102_LOCK_WAIT seq=%u op=%u waits=%u wait_ns=%lu acquired=%u max_ns=500000000 original_FIFO_serialization=1\n",seq,op,waits,ended>=start?ended-start:0,!failed);
 *__errno_location()=saved;return failed?-1:0;
}
