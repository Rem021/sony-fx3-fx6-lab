#include <assert.h>
#include <pthread.h>
#include <stdatomic.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sched.h>
#define N 256
static uint64_t old_serial, old_record[N][12];
static uint64_t new_serial, new_record[N][12], dropped;
static atomic_uint new_lock;
static atomic_uint ready_a, resume_a;
static void paused_writer(void){atomic_store(&ready_a,1);while(!atomic_load(&resume_a))sched_yield();}
static void old_write(int paused){
 uint64_t s=__atomic_add_fetch(&old_serial,1,__ATOMIC_RELAXED),*r=old_record[(s-1)%N];
 __atomic_store_n(&r[0],0,__ATOMIC_RELAXED);
 if(paused){paused_writer();}
 r[1]=s*100;r[2]=s;r[3]=5;
 __atomic_store_n(&r[0],s,__ATOMIC_RELEASE);
}
static void new_write(int paused){
 unsigned zero=0;
 if(!atomic_compare_exchange_strong_explicit(&new_lock,&zero,1,memory_order_acquire,memory_order_relaxed)){
  __atomic_add_fetch(&dropped,1,__ATOMIC_RELAXED);return;
 }
 uint64_t s=__atomic_add_fetch(&new_serial,1,__ATOMIC_RELAXED),*r=new_record[(s-1)%N];
 __atomic_store_n(&r[0],0,__ATOMIC_RELAXED);
 if(paused){paused_writer();}
 r[1]=s*100;r[2]=s;r[3]=5;
 __atomic_store_n(&r[0],s,__ATOMIC_RELEASE);
 atomic_store_explicit(&new_lock,0,memory_order_release);
}
static void *old_a(void *unused){(void)unused;old_write(1);return 0;}
static void *new_a(void *unused){(void)unused;new_write(1);return 0;}
int main(void){pthread_t a;
 pthread_create(&a,0,old_a,0);while(!atomic_load(&ready_a))sched_yield();
 for(int i=0;i<N;i++)old_write(0);
 atomic_store(&resume_a,1);pthread_join(a,0);
 assert(old_serial==257 && old_record[0][0]==1 && old_record[0][1]==100 && old_record[0][2]==1);
 /* The 257th accepted row was replaced by stale writer A: torn chronology. */
 printf("r2 reproduced: serial=%llu slot0_serial=%llu expected257=lost\n",(unsigned long long)old_serial,(unsigned long long)old_record[0][0]);
 atomic_store(&ready_a,0);atomic_store(&resume_a,0);pthread_create(&a,0,new_a,0);while(!atomic_load(&ready_a))sched_yield();
 for(int i=0;i<N;i++)new_write(0);
 atomic_store(&resume_a,1);pthread_join(a,0);
 assert(new_serial==1 && dropped==N && new_record[0][0]==1 && new_record[0][2]==1);
 printf("r3 guarded: accepted=%llu dropped=%llu intact_serial=%llu\n",(unsigned long long)new_serial,(unsigned long long)dropped,(unsigned long long)new_record[0][0]);
 return 0;
}
