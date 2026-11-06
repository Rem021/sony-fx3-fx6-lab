#ifndef FX3_GLOBAL_GUARD_H
#define FX3_GLOBAL_GUARD_H
#include <stdint.h>
#include <sys/types.h>
#include <sys/stat.h>
enum {G_OK=0,G_BUSY,G_INVALID,G_STALE,G_IO,G_FULL};
enum {G_OWNED=1,G_CLEAN=2,G_UNKNOWN=3};
#define FX3_GUARD_RECORD 256u
#define FX3_GUARD_LIMIT 2048u
typedef struct {
    int fd;struct stat identity;
    uint8_t last[FX3_GUARD_RECORD];
    uint32_t count,started;
    uint32_t uid,pid;uint64_t sec,usec;
    uint8_t nonce[16],grant[32];
} fx3_global_guard;
int fx3_global_begin(fx3_global_guard *,const char *,uint32_t,const uint8_t *,const char *);
int fx3_global_finish(fx3_global_guard *,int);
#endif
