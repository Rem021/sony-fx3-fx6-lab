#include <stdint.h>
extern void *dlsym(void *,const char *);
extern int dprintf(int,const char *,...);
extern int *__errno_location(void);
extern void _exit(int);
static unsigned char observe(const char *name,unsigned int id,void *caller){
 int saved=*__errno_location();unsigned char (*fn)(unsigned int)=dlsym((void *)-1,name);if(!fn)_exit(126);
 *__errno_location()=saved;unsigned char rc=fn(id);saved=*__errno_location();
 dprintf(2,"FX3_ICRYPT_HAS api=%s id=%#x result=%u caller=%p original=1 init_called_by_observer=0\n",name,id,rc,caller);
 *__errno_location()=saved;return rc;
}
unsigned char iCrypt_HasPublicKey(unsigned int id){return observe("iCrypt_HasPublicKey",id,__builtin_return_address(0));}
unsigned char iCrypt_HasPrivateKey(unsigned int id){return observe("iCrypt_HasPrivateKey",id,__builtin_return_address(0));}
void *dlopen(const char *name,int flags){
 int saved=*__errno_location();void *(*fn)(const char *,int)=dlsym((void *)-1,"dlopen");if(!fn)_exit(126);
 *__errno_location()=saved;void *h=fn(name,flags);saved=*__errno_location();
 if(name){const char *p=name;while(*p&&*p!='I')p++;if(*p=='I')dprintf(2,"FX3_IMDB_LOAD name=%s flags=%#x handle=%p\n",name,flags,h);}
 *__errno_location()=saved;return h;
}
