/* User file is only a copied I/O envelope, never a privileged mmap backing.
 * Truncation or replacement requests stop, not process death or USB cleanup. */
#include "frame_io.h"
#include <stddef.h>
#include <unistd.h>
static int valid(fx3_frame_io *io) {
    struct stat s;
    return !atomic_load(&io->failed) && !fstat(io->fd,&s) && S_ISREG(s.st_mode) && s.st_nlink==1 &&
        (s.st_mode&07777)==0600 && s.st_uid==io->identity.st_uid && s.st_dev==io->identity.st_dev &&
        s.st_ino==io->identity.st_ino && s.st_size==4096;
}
static void fail(fx3_frame_io *io) {atomic_store(&io->failed,1);}
int fx3_frame_write(fx3_frame_io *io,const fx3_entry_frame *f) {
    uint8_t page[4096]={0};
    if(!valid(io)) {fail(io);return -1;}
    __builtin_memcpy(page,f,sizeof(*f));
    if(pwrite(io->fd,page,sizeof(page),0)!=(ssize_t)sizeof(page) || fsync(io->fd) || !valid(io)) {fail(io);return -1;}
    return 0;
}
void fx3_frame_progress(fx3_frame_io *io,const fx3_entry_frame *f) {
    if(!valid(io)) {fail(io);return;}
    const uint32_t ids[]={offsetof(fx3_owner_result,active_call_pending),offsetof(fx3_owner_result,owner_retained),
        offsetof(fx3_owner_result,session_state),offsetof(fx3_owner_result,wire_pending),offsetof(fx3_owner_result,vendor_attempted)};
    for(unsigned i=0;i<5;++i) {
        const _Atomic uint32_t *p=(const void *)((const uint8_t *)&f->result+ids[i]);uint32_t value=atomic_load(p);
        if(pwrite(io->fd,&value,4,offsetof(fx3_entry_frame,result)+ids[i])!=4) {fail(io);return;}
    }
    uint32_t started=atomic_load(&f->grant.native_started);
    if(pwrite(io->fd,&started,4,offsetof(fx3_entry_frame,grant)+offsetof(fx3_entry_grant,native_started))!=4)fail(io);
#ifdef FX3_ENTRY_FIXTURE
    uint32_t entered=atomic_load(&f->gate.entered);
    if(pwrite(io->fd,&entered,4,offsetof(fx3_entry_frame,gate)+offsetof(fx3_fixture_gate,entered))!=4)fail(io);
#endif
}
void fx3_frame_control(fx3_frame_io *io,fx3_entry_frame *f) {
#ifdef FX3_ENTRY_FIXTURE
    /* Independent explicit fake-call release remains readable after a test
     * truncates its own envelope; it does not enable any production release. */
    uint32_t release=0;
    if(pread(io->fd,&release,4,offsetof(fx3_entry_frame,gate)+offsetof(fx3_fixture_gate,released))==4 && release<=2)
        atomic_store(&f->gate.released,release);
#endif
    if(!valid(io)) {fail(io);atomic_store(&f->control.stop_requested,1);return;}
    uint32_t stop=0,ack=0;
    if(pread(io->fd,&stop,4,offsetof(fx3_entry_frame,control)+offsetof(fx3_owner_control,stop_requested))!=4 ||
       pread(io->fd,&ack,4,offsetof(fx3_entry_frame,grant)+offsetof(fx3_entry_grant,parent_ack))!=4 || stop>1 || ack>1) {
        fail(io);atomic_store(&f->control.stop_requested,1);return;
    }
    if(stop)atomic_store(&f->control.stop_requested,1);
    if(ack)atomic_store(&f->grant.parent_ack,1);
}
