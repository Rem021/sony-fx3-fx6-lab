/* Observation output only: reserved software page+0x1000, not original data. */
#define DATE98_PHYS 0x41df01000UL
#define DATE98_SPAN 0x6000UL
#define DATE98_MAGIC 0x3130383945544144UL
#define DATE98_CAP 64UL
#define DATE98_REC 320UL
static void d98_copy(void *o,const void *v,U n){unsigned char *d=o;const unsigned char*s=v;for(U i=0;i<n;i++)d[i]=s[i];}
static void d98_zero(void *o,U n){unsigned char*d=o;for(U i=0;i<n;i++)d[i]=0;}
static void d98_w(void*p,W x){d98_copy(p,&x,4);}static void d98_u(void*p,U x){d98_copy(p,&x,8);}
struct d98_model{W force_current,force_next,force_valid,date_current,date_next,date_mask;};
static int d98_init(unsigned char*p,U span){if(!p||span<64+DATE98_CAP*DATE98_REC||span>DATE98_SPAN)return 0;U m=__atomic_load_n((U*)p,__ATOMIC_ACQUIRE);if(m==DATE98_MAGIC)return 1;if(m)return 0;U expect=0;if(!__atomic_compare_exchange_n((U*)p,&expect,1,0,__ATOMIC_ACQ_REL,__ATOMIC_ACQUIRE))return 0;d98_zero(p+8,span-8);d98_u(p+8,1);d98_u(p+16,DATE98_CAP);d98_u(p+24,DATE98_REC);__atomic_store_n((U*)p,DATE98_MAGIC,__ATOMIC_RELEASE);return 1;}
static unsigned char*d98_begin(unsigned char*p,W kind,W pid,W tid,W dst,W n,U pointer,U caller,const void*raw,int ok,W method,U ns,const struct d98_model*m){if(!p||__atomic_load_n((U*)p,__ATOMIC_ACQUIRE)!=DATE98_MAGIC)return 0;U i=__atomic_fetch_add((U*)(p+32),1,__ATOMIC_ACQ_REL);if(i>=DATE98_CAP){__atomic_add_fetch((U*)(p+40),1,__ATOMIC_RELAXED);return 0;}unsigned char*r=p+64+i*DATE98_REC;__atomic_store_n((U*)r,1,__ATOMIC_RELEASE);d98_u(r+8,i+1);d98_w(r+16,pid);d98_w(r+20,tid);d98_w(r+24,dst);d98_w(r+28,n);d98_u(r+32,pointer);d98_u(r+40,caller);d98_w(r+48,1);d98_w(r+60,ok);d98_w(r+68,method);d98_w(r+76,kind);d98_u(r+80,ns);if(m)d98_copy(r+96,m,24);if(ok&&n<=64&&raw)d98_copy(r+192,raw,n);__atomic_store_n((U*)r,2,__ATOMIC_RELEASE);return r;}
static void d98_end(unsigned char*r,int rc,int error,const void*raw,W n,int ok,W method,U ns,const struct d98_model*m){if(!r)return;__atomic_store_n((U*)r,3,__ATOMIC_RELEASE);d98_w(r+48,2);d98_w(r+52,(W)rc);d98_w(r+56,(W)error);d98_w(r+64,ok);d98_w(r+72,method);d98_u(r+88,ns);if(m)d98_copy(r+120,m,24);if(ok&&n<=64&&raw)d98_copy(r+256,raw,n);__atomic_store_n((U*)r,4,__ATOMIC_RELEASE);}
