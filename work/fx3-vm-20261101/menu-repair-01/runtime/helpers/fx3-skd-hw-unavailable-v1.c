typedef unsigned long size_t;
extern void *dlsym(void *,const char *);extern int *__errno_location(void);extern char *getenv(const char *);extern int strcmp(const char *,const char *);extern int snprintf(char *,size_t,const char *,...);extern long readlink(const char *,char *,size_t);extern int dprintf(int,const char *,...);extern void _exit(int) __attribute__((noreturn));
struct skd_dl_info {const char *file;void *base;const char *symbol;void *address;};extern int dladdr(const void *,struct skd_dl_info *);
static void *(*skd_next_mmap)(void *,size_t,int,int,int,long);
static int skd_missing_match(void *address,size_t length,int protection,int flags,int fd,long offset,void *caller){
 const char *enabled=getenv("FX3_SKD_HW");if(!enabled||strcmp(enabled,"unavailable-rom-v1")||address||length!=0x1000||protection!=1||flags!=1||fd<0||offset!=0xffffb000UL)return 0;
 struct skd_dl_info info={0};if(!dladdr(caller,&info)||!info.file||strcmp(info.file,"/usr/lib/libInfraSKD.so")||!info.base||(unsigned long)caller-(unsigned long)info.base!=0x645ec)return 0;
 char path[64],target[64];int n=snprintf(path,sizeof path,"/proc/self/fd/%d",fd);if(n<0||(size_t)n>=sizeof path)return 0;long count=readlink(path,target,sizeof target);return count==8&&__builtin_memcmp(target,"/dev/mem",8)==0;
}
static void *skd_mmap_dispatch(void *address,size_t length,int protection,int flags,int fd,long offset,void *caller){
 int saved=*__errno_location();if(skd_missing_match(address,length,protection,flags,fd,offset,caller)){dprintf(2,"FX3_SKD_HW_UNAVAILABLE caller=%p relative=0x645ec map_call=0x645e8 offset=0xffffb000 length=0x1000 protection=1 flags=1 fd=%d errno=19 skd_hardware_available=0 key_material_fabricated=0 other_regions_unchanged=1\n",caller,fd);*__errno_location()=19;return (void *)-1;}
 void *(*fn)(void *,size_t,int,int,int,long)=__atomic_load_n(&skd_next_mmap,__ATOMIC_ACQUIRE);if(!fn){fn=dlsym((void *)-1,"mmap");if(!fn)_exit(126);__atomic_store_n(&skd_next_mmap,fn,__ATOMIC_RELEASE);}*__errno_location()=saved;return fn(address,length,protection,flags,fd,offset);
}
void *mmap(void *address,size_t length,int protection,int flags,int fd,long offset){return skd_mmap_dispatch(address,length,protection,flags,fd,offset,__builtin_return_address(0));}
