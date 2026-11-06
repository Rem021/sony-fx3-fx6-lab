/* New service-scope root-private permit parser; no general native release. */
#include "status_permit.h"
#include "target_binding.h"
#include "entry_target.h"
#include <CommonCrypto/CommonDigest.h>
#include <fcntl.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/mount.h>
#include <unistd.h>
static uint32_t get32(const uint8_t *p){return p[0]|(uint32_t)p[1]<<8|(uint32_t)p[2]<<16|(uint32_t)p[3]<<24;}
static uint64_t get64(const uint8_t *p){return get32(p)|(uint64_t)get32(p+4)<<32;}
int fx3_status_permit_bytes(const uint8_t *p,size_t n,const uint8_t nonce[16]){
    static const uint8_t magic[16]="FX3SERVICEPERM1";
    uint8_t hash[32];
    if(!p || !nonce || n!=96 || memcmp(p,magic,16) || get32(p+16)!=1 || get32(p+20)!=0x53564334 ||
       memcmp(p+24,nonce,16) || memcmp(nonce,FX3_FIXED_NONCE,16) || get32(p+40)!=FX3_FIXED_LOCATION ||
       get32(p+44)!=1 || get64(p+48)!=FX3_CACHED_REGISTRY_ID || get64(p+56))return 0;
    CC_SHA256(p,64,hash);return !memcmp(hash,p+64,32);
}
static int file_check(const char *path,uint32_t uid,const uint8_t nonce[16],int check_fs){
    int fd=open(path,O_RDONLY|O_NOFOLLOW|O_NONBLOCK|O_CLOEXEC);if(fd<0)return 0;
    struct stat a,b;struct statfs fs;uint8_t data[97]={0};
    int ok=!fstat(fd,&a) && S_ISREG(a.st_mode) && a.st_uid==uid && a.st_nlink==1 &&
      (a.st_mode&07777)==0400 && a.st_size==96 && !fstatfs(fd,&fs) &&
      (!check_fs || !(fs.f_flags&MNT_IGNORE_OWNERSHIP)) && pread(fd,data,sizeof(data),0)==96 && !fstat(fd,&b) &&
      a.st_dev==b.st_dev && a.st_ino==b.st_ino && a.st_size==b.st_size && a.st_uid==b.st_uid &&
      a.st_mode==b.st_mode && a.st_nlink==b.st_nlink &&
      a.st_mtimespec.tv_sec==b.st_mtimespec.tv_sec && a.st_mtimespec.tv_nsec==b.st_mtimespec.tv_nsec &&
      a.st_ctimespec.tv_sec==b.st_ctimespec.tv_sec && a.st_ctimespec.tv_nsec==b.st_ctimespec.tv_nsec;
    if(close(fd))ok=0;
    return ok && fx3_status_permit_bytes(data,96,nonce);
}
int fx3_status_permit(const uint8_t nonce[16]){
    return getuid()==0 && geteuid()==0 && file_check(FX3_ROOT_GRANT_DIR "/permit.bin",0,nonce,1);
}
#ifdef FX3_PERMIT_TEST
int fx3_status_permit_test_file(const char *p,uint32_t uid,const uint8_t nonce[16]){return file_check(p,uid,nonce,0);}
#endif
