#ifndef FX6_SNAPSHOT_CORE_H
#define FX6_SNAPSHOT_CORE_H
#include <stdint.h>
#include <stdio.h>

enum { FX6_PEEKDATA=2, FX6_DETACH=17, FX6_GETREGSET=0x4204,
       FX6_SEIZE=0x4206, FX6_INTERRUPT=0x4207, FX6_NT_PRSTATUS=1 };
struct fx6_regs { uint64_t x[31], sp, pc, pstate; };
_Static_assert(sizeof(struct fx6_regs)==272,"arm64 NT_PRSTATUS size");
struct fx6_stack { uint64_t low,high; };
struct fx6_ops {
 long (*trace)(int,int,uintptr_t,uintptr_t,int *);
 int (*wait)(int,int *,int *);
 uint64_t (*now)(void);
 void (*pause)(void);
 int (*cancel)(void);
 int (*belongs)(int);
 int (*stack)(int,uint64_t,struct fx6_stack *);
 FILE *out;
 uint64_t page_size;
};
struct fx6_active { int tid,seized,stopped,signal; };
int fx6_frame_valid(uint64_t,uint64_t,const struct fx6_stack *,uint64_t);
int fx6_capture_thread(struct fx6_ops *,struct fx6_active *,int);
int fx6_cleanup_thread(struct fx6_ops *,struct fx6_active *);
#endif
