typedef unsigned long U;typedef unsigned long size_t;
extern void *dlsym(void *,const char *);extern int dlinfo(void *,int,void *);extern int dprintf(int,const char *,...);extern int *__errno_location(void);extern int open(const char *,int,...);extern long pread(int,void *,size_t,long);extern int close(int);extern long syscall(long,...);extern void *mmap(void *,size_t,int,int,int,long);extern int mprotect(void *,size_t,int);extern int memcmp(const void *,const void *,size_t);extern void *memcpy(void *,const void *,size_t);extern char *strstr(const char *,const char *);
struct lm{U base;char *name;void *dynamic;struct lm *next,*prev;};
static U app_base,obj_base,seq;static unsigned int bound;static __thread U timer_widget,ui_update;static __thread unsigned int timer_depth;
static U (*timer_orig)(U,U,U);static U (*table_orig)(U,U,U,U,U,U,U);static U (*fill_orig)(U);static U (*config_orig)(U);
static unsigned long timer_calls,id_calls,info_calls,table_calls,config_calls,config_target_calls,fill_calls;
static void timer_stats(void){int saved=*__errno_location();char path[96];extern int snprintf(char *,size_t,const char *,...);snprintf(path,sizeof path,"/tmp/fx3-timer-stats-%ld",syscall(172));int fd=open(path,0x20241,0600);if(fd>=0){dprintf(fd,"FX3_TIMER_OBSERVER_END pid=%ld bound=%u timer_entry=%lu id_compare=%lu info=%lu table=%lu config=%lu config_target=%lu fill=%lu event_seq=%lu snapshot=1\n",syscall(172),bound,timer_calls,id_calls,info_calls,table_calls,config_calls,config_target_calls,fill_calls,seq);close(fd);}*__errno_location()=saved;}
static U number(void){return __atomic_add_fetch(&seq,1,__ATOMIC_RELAXED);}
static int peek(U address,void *out,U n){int saved=*__errno_location();int fd=open("/proc/self/mem",0);long rc=fd<0?-1:pread(fd,out,n,address);if(fd>=0)close(fd);*__errno_location()=saved;return rc==(long)n;}
static U timer_hook(U widget,U id,U time){
 int saved=*__errno_location();U old=timer_widget;unsigned int depth=timer_depth;timer_widget=widget;timer_depth=depth+1;__atomic_add_fetch(&timer_calls,1,0);U n=number();timer_stats();
 if(n<=1024)dprintf(2,"FX3_TIMER_ENTRY seq=%lu tid=%ld widget=%#lx id_object=%#lx input_time=%lu ui_update=%lu original=1\n",n,syscall(178),widget,id,time,ui_update);
 *__errno_location()=saved;U rc=timer_orig(widget,id,time);saved=*__errno_location();timer_widget=old;timer_depth=depth;
 if(n<=1024)dprintf(2,"FX3_TIMER_RETURN seq=%lu tid=%ld result=%#lx\n",n,syscall(178),rc);*__errno_location()=saved;return rc;
}
U observe_id(U a,U b) __asm__("_ZNK2ux4core2IDeqES1_");
U observe_id(U a,U b){
 int saved=*__errno_location();U (*fn)(U,U)=dlsym((void *)-1,"_ZNK2ux4core2IDeqES1_");if(!fn)__builtin_trap();
 *__errno_location()=saved;U rc=fn(a,b);saved=*__errno_location();U caller=(U)__builtin_return_address(0);
 if(timer_depth&&caller==app_base+0x176fb7c){__atomic_add_fetch(&id_calls,1,0);timer_stats();U n=number();unsigned int id=0;int read=peek(a,&id,4);if(n<=1024)dprintf(2,"FX3_TIMER_ID seq=%lu tid=%ld widget=%#lx read=%d input_id=%#x expected=%#x result=%#lx branch_at=0x176fb80 taken_exit=%u\n",n,syscall(178),timer_widget,read,id,(unsigned int)b,rc,!(rc&255));}
 *__errno_location()=saved;return rc;
}
U observe_info(U a,U b,U c,U d,U e,U f) __asm__("_ZN2ux6wgtsys10WidgetBase12getTimerInfoERKNS_4core2IDERNS0_9TimerTypeERjRS3_Rm");
U observe_info(U a,U b,U c,U d,U e,U f){
 int saved=*__errno_location();U (*fn)(U,U,U,U,U,U)=dlsym((void *)-1,"_ZN2ux6wgtsys10WidgetBase12getTimerInfoERKNS_4core2IDERNS0_9TimerTypeERjRS3_Rm");if(!fn)__builtin_trap();
 *__errno_location()=saved;U rc=fn(a,b,c,d,e,f);saved=*__errno_location();
 if(timer_depth&&a==timer_widget){__atomic_add_fetch(&info_calls,1,0);timer_stats();U time=0,n=number();int read=peek(f,&time,8);if(n<=1024)dprintf(2,"FX3_TIMER_INFO seq=%lu tid=%ld widget=%#lx result=%#lx stored_time=%lu time_read=%d branch_at=0x176fbc0 taken_exit=%u\n",n,syscall(178),a,rc,time,read,!(rc&255));}
 *__errno_location()=saved;return rc;
}
static U table_hook(U a,U b,U c,U d,U e,U f,U g){
 int saved=*__errno_location();U head=0;int observe=timer_depth&&b==timer_widget;int read=observe?peek(a+0x890,&head,8):0;
 *__errno_location()=saved;U rc=table_orig(a,b,c,d,e,f,g);saved=*__errno_location();
 if(observe){__atomic_add_fetch(&table_calls,1,0);timer_stats();U time=0,n=number();int tr=peek(g,&time,8);if(n<=1024)dprintf(2,"FX3_TIMER_TABLE seq=%lu tid=%ld widget=%#lx manager=%#lx head=%#lx head_read=%d result=%#lx hit=%u stored_time=%lu time_read=%d next_offset=0x30\n",n,syscall(178),b,a,head,read,rc,(unsigned int)(rc&255),time,tr);}
 *__errno_location()=saved;return rc;
}
static U config_hook(U a){
 int saved=*__errno_location();U caller=(U)__builtin_return_address(0),n=number();__atomic_add_fetch(&config_calls,1,0);if(caller==app_base+0x2191df8)__atomic_add_fetch(&config_target_calls,1,0);timer_stats();if(n<=1024)dprintf(2,"FX3_UI_CONFIG_ENTER seq=%lu tid=%ld caller_relative=%#lx object=%#lx\n",n,syscall(178),caller-app_base,a);
 *__errno_location()=saved;U rc=config_orig(a);saved=*__errno_location();if(n<=1024)dprintf(2,"FX3_UI_CONFIG_RETURN seq=%lu tid=%ld caller_relative=%#lx result=%#lx\n",n,syscall(178),caller-app_base,rc);if(caller==app_base+0x2191df8){ui_update=n;if(n<=1024)dprintf(2,"FX3_UI_CONFIG_DONE seq=%lu tid=%ld caller=0x2191df4 result=%#lx ui_update=%lu\n",n,syscall(178),rc,n);}
 *__errno_location()=saved;return rc;
}
static U fill_hook(U command){
 int saved=*__errno_location();U bitmap=0,n=number();__atomic_add_fetch(&fill_calls,1,0);timer_stats();int read=peek(command+0x78,&bitmap,8);
 if(n<=1024)dprintf(2,"FX3_UI_FILL_EXEC seq=%lu tid=%ld command=%#lx bitmap=%#lx bitmap_read=%d ui_update=%lu timer_depth=%u\n",n,syscall(178),command,bitmap,read,ui_update,timer_depth);
 *__errno_location()=saved;U rc=fill_orig(command);saved=*__errno_location();if(n<=1024)dprintf(2,"FX3_UI_FILL_RETURN seq=%lu tid=%ld result=%#lx\n",n,syscall(178),rc);*__errno_location()=saved;return rc;
}
static void sync_code(unsigned char *p,U n){U ctr;__asm__ volatile("mrs %0,ctr_el0":"=r"(ctr));U dc=4UL<<((ctr>>16)&15),ic=4UL<<(ctr&15);for(U a=(U)p&~(dc-1);a<(U)p+n;a+=dc)__asm__ volatile("dc cvau,%0"::"r"(a):"memory");__asm__ volatile("dsb ish":::"memory");for(U a=(U)p&~(ic-1);a<(U)p+n;a+=ic)__asm__ volatile("ic ivau,%0"::"r"(a):"memory");__asm__ volatile("dsb ish;isb":::"memory");}
static int patch(U address,const unsigned char prefix[16],void *hook,void **original){
 unsigned char *p=(void *)address;if(memcmp(p,prefix,16))return -1;unsigned char *tr=mmap(0,4096,3,0x22,-1,0);if(tr==(void *)-1)return -2;
 memcpy(tr,p,16);unsigned int jump[2]={0x58000050,0xd61f0200};U next=address+16;memcpy(tr+16,jump,8);memcpy(tr+24,&next,8);sync_code(tr,32);if(mprotect(tr,4096,5))return -3;
 *original=tr;if(mprotect((void *)(address&~4095UL),4096,7))return -4;memcpy(p,jump,8);memcpy(p+8,&hook,8);sync_code(p,16);if(mprotect((void *)(address&~4095UL),4096,5))return -5;return 0;
}
static void bind(void *h,void *(*fn)(const char *,int)){
 if(bound)return;struct lm *a=0,*o=0;if(dlinfo(h,2,&a)||!a)return;void *oh=fn("libObj.so",5);if(!oh||dlinfo(oh,2,&o)||!o)return;
 const unsigned char prefixes[4][16]={{0xfd,0x7b,0xba,0xa9,0xfd,3,0,0x91,0xf5,0x13,0,0xf9,0xf5,3,0,0xaa},{0xfd,0x7b,0xbb,0xa9,0xfd,3,0,0x91,0xf3,0x53,1,0xa9,0xf3,3,0,0xaa},{0xfd,0x7b,0xbd,0xa9,0xfd,3,0,0x91,0xf3,0x0b,0,0xf9,0xf3,3,0,0xaa},{0xfd,0x7b,0xb8,0xa9,0xfd,3,0,0x91,0xf3,0x53,1,0xa9,0xf3,3,0,0xaa}};
 U addresses[4]={a->base+0x176fb4c,o->base+0x176ab0,o->base+0x100c48,a->base+0x16ee6f8};void *hooks[4]={(void *)timer_hook,(void *)table_hook,(void *)fill_hook,(void *)config_hook};void **out[4]={(void **)&timer_orig,(void **)&table_orig,(void **)&fill_orig,(void **)&config_orig};
 for(int i=0;i<4;i++)if(memcmp((void *)addresses[i],prefixes[i],16)){dprintf(2,"FX3_TIMER_BIND_FAILED k=%d reason=prefix original_unchanged=1\n",i);return;}
 app_base=a->base;obj_base=o->base;for(int i=0;i<4;i++){int rc=patch(addresses[i],prefixes[i],hooks[i],out[i]);if(rc){dprintf(2,"FX3_TIMER_BIND_FAILED k=%d result=%d\n",i,rc);return;}}
 bound=1;timer_stats();dprintf(2,"FX3_TIMER_BOUND count=4 prefixes_verified=16 pc_relative_in_stolen=0 original_calls_preserved=1 app_base=%#lx obj_base=%#lx\n",app_base,obj_base);
}
void *dlopen(const char *name,int flags){int saved=*__errno_location();void *(*fn)(const char *,int)=dlsym((void *)-1,"dlopen");if(!fn)__builtin_trap();*__errno_location()=saved;void *h=fn(name,flags);saved=*__errno_location();if(h&&name&&strstr(name,"appFw.so"))bind(h,fn);*__errno_location()=saved;return h;}
