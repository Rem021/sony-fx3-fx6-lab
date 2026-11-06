/* Lock-free interprocess stop/progress only. No device or filesystem API. */
#include "owner_trial.h"
#include <signal.h>
#include <string.h>
_Static_assert(ATOMIC_INT_LOCK_FREE==2,"32-bit signal/IPC flags must be lock-free");
typedef struct { fx3_owner_control control; fx3_owner_result result; fx3_fixture_gate gate; } frame;
_Static_assert(ATOMIC_POINTER_LOCK_FREE==2,"signal pointer must be lock-free");
static _Atomic uint32_t * _Atomic signal_stop;
static struct sigaction previous[3];
static const int signals_[3]={SIGINT,SIGTERM,SIGHUP};
static void stop_signal(int unused) {
    (void)unused;
    _Atomic uint32_t *flag=atomic_load_explicit(&signal_stop,memory_order_relaxed);
    if (flag) atomic_store_explicit(flag,1,memory_order_relaxed);
}
#define PUB __attribute__((visibility("default")))
PUB uint32_t fx3_ipc_layout(uint32_t item) {
    uint32_t values[]={sizeof(frame),offsetof(frame,result),offsetof(frame,gate),sizeof(fx3_owner_control),sizeof(fx3_owner_result),sizeof(fx3_fixture_gate)};
    return item<6?values[item]:0;
}
PUB int fx3_ipc_init(void *memory,size_t bytes) {
    if (!memory || bytes<sizeof(frame)) return -1;
    memset(memory,0,bytes); frame *f=memory; f->control.abi=FX3_OWNER_ABI;
    atomic_init(&f->control.stop_requested,0); atomic_init(&f->result.active_call_pending,0);
    atomic_init(&f->gate.released,0); atomic_init(&f->gate.entered,0);
    return 0;
}
PUB void fx3_ipc_stop(void *memory) { frame *f=memory; atomic_store_explicit(&f->control.stop_requested,1,memory_order_release); }
PUB uint32_t fx3_ipc_stop_requested(void *memory) { frame *f=memory; return atomic_load_explicit(&f->control.stop_requested,memory_order_acquire); }
PUB uint32_t fx3_ipc_pending(void *memory) { frame *f=memory; return atomic_load_explicit(&f->result.active_call_pending,memory_order_acquire); }
PUB void fx3_ipc_fixture_release(void *memory) { frame *f=memory; atomic_store_explicit(&f->gate.released,1,memory_order_release); }
PUB uint32_t fx3_ipc_fixture_entered(void *memory) { frame *f=memory; return atomic_load_explicit(&f->gate.entered,memory_order_acquire); }
PUB int fx3_ipc_install_handlers(void *memory) {
    if (atomic_load_explicit(&signal_stop,memory_order_acquire)) return -1;
    frame *f=memory; atomic_store_explicit(&signal_stop,&f->control.stop_requested,memory_order_release);
    struct sigaction action; memset(&action,0,sizeof(action)); action.sa_handler=stop_signal; sigemptyset(&action.sa_mask);
    for (unsigned i=0;i<3;++i) {
        if (sigaction(signals_[i],&action,&previous[i])!=0) {
            while (i) { --i; sigaction(signals_[i],&previous[i],NULL); }
            atomic_store_explicit(&signal_stop,NULL,memory_order_release); return -1;
        }
    }
    return 0;
}
PUB void fx3_ipc_remove_handlers(void) {
    if (!atomic_load_explicit(&signal_stop,memory_order_acquire)) return;
    for (unsigned i=0;i<3;++i) sigaction(signals_[i],&previous[i],NULL);
    atomic_store_explicit(&signal_stop,NULL,memory_order_release);
}
