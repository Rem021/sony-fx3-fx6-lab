from pathlib import Path
import json,subprocess,os
R=Path(__file__).resolve().parent;H=R/'helpers'
s=r'''#include <stdint.h>
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
'''
(H/'fx3-icrypt-observe-v1.c').write_text(s)
x=json.loads((H/'fx3-capid-v25-build.json').read_text());a=x['args'];a=a[:a.index('-Wl,-soname,fx3-fx3-capid-v25.so')]+['-Wl,-soname,fx3-icrypt-observe-v1.so',str(H/'fx3-icrypt-observe-v1.c')]+[str(R/'guest-sdk/lib'/n) for n in ['libc-2.25.so','libdl-2.25.so','ld-2.25.so']]+['-o',str(H/'fx3-icrypt-observe-v1.so')]
e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));subprocess.run(a,env=e,check=True)
s=(R/'build_lcd_osd_candidate70.py').read_text().replace("D=R/'ap70-lcd-osd'","D=R/'ap71-icrypt-load'").replace("base=R/'ap69-audio-query-observe/candidate69.json'","base=R/'ap70-lcd-osd/candidate70.json'").replace("candidate70.json","candidate71.json")
s=s.replace("if name=='init':", "if name=='simulation/fx3-hdmi-registration-v1.so':\n  entries.append(('simulation/fx3-icrypt-observe-v1.so',f,(R/'helpers/fx3-icrypt-observe-v1.so').read_bytes()))\n if name=='init':")
s=s.replace('init=data.decode().replace("FX3_CAPID_STORAGE=reserved-v1 ","FX3_CAPID_STORAGE=reserved-v1 FX3_LCD_OSD=captured-v1 ")','init=data.decode().replace("/simulation/ioctl-trace.so /usr/bin/bootin.elf", "/simulation/ioctl-trace.so:/simulation/fx3-icrypt-observe-v1.so:/usr/lib/libInfraCrypt.so /usr/bin/bootin.elf").replace("while true; do /bin/busybox sleep 1; done\\n", "while true; do /bin/busybox sleep 1; done\\n")')
s=s.replace(";v['scope']=", ";v['scope']=")
s=s.replace("(D/'candidate71.json').write_text", "v['required_markers']+=['FX3_ICRYPT_HAS'];(D/'candidate71.json').write_text")
(R/'build_icrypt_candidate71.py').write_text(s)
subprocess.run(['python3',str(R/'build_icrypt_candidate71.py')],check=True)
