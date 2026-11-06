#ifndef FX3_HOST_BOUND_SIGNAL_H
#define FX3_HOST_BOUND_SIGNAL_H
#include <libproc.h>
#include <stdint.h>
typedef struct {
    pid_t pid;
    uint32_t uid;
    uint64_t sec,usec;
    const char *path;
} fx3_host_identity;
/* No signal is sent during capture. A task-name port is used only to read
 * TASK_AUDIT_TOKEN, then deallocated. No task control/memory API is used. */
int fx3_host_capture_token(const fx3_host_identity *,audit_token_t *);
int fx3_host_same_process(const fx3_host_identity *); /* 1 match,0 absent/replaced,-1 unknown */
/* Kernel compares token PID/version, avoiding a PID-only signal fallback. */
int fx3_host_signal_token(const audit_token_t *,int);
#endif
