
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
static int stub_open(const char*,int,...),stub_close(int),stub_print(const char*,...);static long stub_read(int,void*,unsigned long),stub_seek(int,long,int);static void*stub_map(void*,unsigned long,int,int,int,long);static int stub_unmap(void*,unsigned long);
#define REPLAY_HOST_TEST 1
#define open stub_open
#define close stub_close
#define read stub_read
#define lseek stub_seek
#define printf stub_print
#define mmap stub_map
#define munmap stub_unmap
#include "fx3-backup-replay-v1.c"
#undef printf
static B*input,*ram,*initial,*shadow;static unsigned mapped,unmapped,offset;static int shortfile,badreadback,verified,rollback_verified;
static int stub_open(const char*p,int f,...){if(!strcmp(p,"/simulation/ap89-backup-ram.bin")){assert(f==0);return 10;}assert(!strcmp(p,"/dev/mem")&&f==2);return 11;}
static int stub_close(int fd){assert(fd==10||fd==11);return 0;}static long stub_seek(int fd,long off,int whence){assert(fd==10&&!off);if(whence==2)return REPLAY_BYTES-shortfile;assert(whence==0);offset=0;return 0;}
static long stub_read(int fd,void*p,U n){assert(fd==10&&n==REPLAY_BYTES-offset);U z=n>7777?7777:n;memcpy(p,input+offset,z);offset+=z;return z;}
static void*stub_map(void*p,U n,int prot,int flags,int fd,long off){assert(!p&&n==REPLAY_BYTES&&(prot==1||prot==3)&&flags==1&&fd==11&&off==REPLAY_PHYS);mapped++;if(badreadback&&mapped==2){assert(prot==1);memcpy(shadow,ram,REPLAY_BYTES);shadow[1000]^=1;return shadow;}return ram;}
static int stub_unmap(void*p,U n){assert((p==ram||p==shadow)&&n==REPLAY_BYTES);unmapped++;return 0;}
static int stub_print(const char*f,...){if(strstr(f,"REPLAY_VERIFIED"))verified++;if(strstr(f,"ROLLBACK")){va_list ap;va_start(ap,f);rollback_verified=va_arg(ap,int);va_end(ap);}return 0;}
static void reset(void){memcpy(ram,initial,REPLAY_BYTES);mapped=unmapped=verified=rollback_verified=0;offset=0;shortfile=badreadback=0;}
int main(int argc,char**argv){assert(argc==3);FILE*f=fopen(argv[1],"rb");assert(f);input=malloc(REPLAY_BYTES);ram=malloc(REPLAY_BYTES);initial=calloc(1,REPLAY_BYTES);shadow=malloc(REPLAY_BYTES);assert(fread(input,1,REPLAY_BYTES,f)==REPLAY_BYTES);fclose(f);f=fopen(argv[2],"rb");assert(f);assert(fread(initial,1,2229740,f)==2229740);fclose(f);char text[65];digest((B*)"",0,text);assert(!strcmp(text,"e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"));digest((B*)"abc",3,text);assert(!strcmp(text,"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"));
 /* Pythonhashlib-proven padding boundaries injected below. */
 B vector[1000];for(unsigned i=0;i<1000;i++)vector[i]=(B)(i*7);digest(vector,55,text);assert(!strcmp(text,"576a1bf8d4478657e6dc4af9398544765c2a92cde28478b019235cfed315fc09"));digest(vector,56,text);assert(!strcmp(text,"9b20501dfd1d99161c257950f3444f3e49230c351c5c8e0943ef369f85f5205d"));digest(vector,63,text);assert(!strcmp(text,"30b345906b493f06f69444b6521113511c242f30e29840462950035043682f1e"));digest(vector,64,text);assert(!strcmp(text,"d8bc63b4fc1156e5e7d95a418b9bf54cd3174bedbc2db40f74895349b229b3c0"));digest(vector,65,text);assert(!strcmp(text,"1ee23b0fbcaecc1aff4a9e8f1645f35ab2c8e13609cd73b68df8b5e3f63ce073"));digest(vector,127,text);assert(!strcmp(text,"67d79933e3c9aa8e89f481e071cfca1e9a16c09d7263b5efa3bb01f1a9f8d065"));digest(vector,128,text);assert(!strcmp(text,"54c9eb041badfd7064645067b107661fed6113197ce2dd066ba69618abd3732f"));digest(vector,129,text);assert(!strcmp(text,"5b55715b51c54661ed0cbd75ba5b00cf1ffee3b7c113a636eca613d9425116a6"));digest(vector,1000,text);assert(!strcmp(text,"89f4ff56a25dd1db06a4ce6033603775d705fb96f30f8693733fef602a1ca532"));
 reset();assert(!replay()&&verified==1&&mapped==2&&unmapped==2&&!memcmp(ram,input,REPLAY_BYTES));
 reset();badreadback=1;assert(replay()==1&&!verified&&rollback_verified&&mapped==3&&unmapped==3&&!memcmp(ram,initial,REPLAY_BYTES));
 reset();input[400]^=1;assert(replay()==1&&!mapped&&!memcmp(ram,initial,REPLAY_BYTES));input[400]^=1;
 reset();shortfile=1;assert(replay()==1&&!mapped&&!memcmp(ram,initial,REPLAY_BYTES));
 reset();ram[4]^=1;B old=ram[4];assert(replay()==1&&mapped==1&&unmapped==1&&ram[4]==old&&!verified);free(input);free(ram);free(initial);free(shadow);puts("REPLAY89_PASS sha256_empty_abc_padding_and_fullsnapshot/sourceSHA_guard/fixedrange2bank_header/fullcopy_remapSHA/actualrollback/sourceimmutable/partialreads/shortfile_noRAMwrite");return 0;}
