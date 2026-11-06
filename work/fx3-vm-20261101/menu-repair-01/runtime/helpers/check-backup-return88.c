
#include <assert.h>
#include <stdarg.h>
#include "fx3-backup-return-v1.c"
static int err,received,result;static unsigned forwarded,entries,returns;
int*__errno_location(void){return &err;}long syscall(long n,...){assert(n==178);return 352;}static int real(unsigned f){assert(err==77);received=f;forwarded++;err=8;return result;}
void*dlsym(void*h,const char*n){assert(h==(void*)-1&&n[0]=='B');return (void*)real;}
int dprintf(int fd,const char*f,...){assert(fd==2);if(f[24]=='E')entries++;else returns++;err=991;return 0;}
int main(void){err=77;result=-7;assert(Backup_reset_all(1)==-7&&err==8&&received==1&&forwarded==1);err=77;result=0;assert(!Backup_reset_all(4)&&err==8&&received==4&&forwarded==2);assert(calls==2&&entries+returns==4);return 0;}
