# Evidence 390 — POST1 crash is an x8 clobber in the trace stub, not the native blocker

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **390** `guest-hybrid-fx6kernel-capid-grmreal390-posttrace.cpio`
Run: **`cp-bind-bb34818f`** (interrupted at 1,427.6 s after the AppFw thread had died)
Result: 34-site post-walk trace installed; `POST0` (`12d8268 → c56fdc`) returned;
`POST1` (`12d8274 → 113e8f4`) crashed because the C stub clobbered **x8**.

## 1. Trace result

```text
FX6_12D8260_RET
FX6_POST0_CALL n=1 a0=0x7f65e56e10 …   ; 12d8268 -> c56fdc
FX6_POST0_RET  n=1 r0=0x7f65e56e10
FX6_POST1_CALL n=2 a0=(nil) …           ; 12d8274 -> 113e8f4
APPFW_SEGV sig=11 addr=0x7f670778f4 pc=0x7f67077918
APPFW_PC_MODULE /usr/lib/appFw.so base=0x7f65f39000
```

PC offset = `0x113e918`, i.e. inside `113e8f4`:

```text
113e8f4  stp x29,x30,[sp,#-0x30]!
113e8f8  mov x29,sp
113e8fc  stp x19,x20,[sp,#0x10]
113e900  mov x19,x8        ; <-- x8 is the struct-return buffer
…
113e918  stp x21,x0,[x19]  ; fault here
```

The caller sets the buffer immediately before the call:

```text
12d826c  ldr x0,[x29,#0x88]
12d8270  mov x8,x19
12d8274  bl 113e8f4
```

The 390 stub was an ordinary C function: it logged through `dprintf` and then called the
real target, but **C does not preserve x8** across that sequence. `113e8f4` therefore
received a clobbered x8 and stored through it, faulting at `113e918`.

This is **instrumentation-induced**, not the native blocker. 389 had no such hook and
passed `12d8274` (it later blocked in a futex with no crash), which is consistent.

## 2. Fix for 391

The post stub is now a **naked assembly function** (separate translation unit
`fx6_post_stub.c`):

```text
save x0..x9 and x17 on the stack
log CALL(id, a0, a1)
restore x0..x8, load target from g_post_real[id]
blr target
save x0, log RET(id, x0), restore x0, return to slot+4
```

It preserves the full argument set including x8, and still forwards all eight integer
argument registers. Trampoline layout is unchanged (`ldr x16,#12; movz w17,#id; br x16`).

391 re-runs the same payload with this stub and a late GPE capture.

## 3. What is still unknown

389 showed the AppFw thread in `futex_wait_queue_me` after `12D8260_RET`; the blocking
call is somewhere in `12d8268 … 12d8554`. 390 only proved `12d8268` returns. 391 will
produce the full CALL/RET chain up to the first non-returning site.

## 4. Artifacts

| Item | Value |
|---|---|
| CPIO 390 | `guest-hybrid-fx6kernel-capid-grmreal390-posttrace.cpio`, 430,232,136 B, SHA-256 `a79cfb3a…` |
| run 390 | `cp-bind-bb34818f`, serial 2,617,485 B, SHA-256 `df43b6e0733a16a3ddd7a691dd7da9c7bdbaa1139d1b5f62262f2707d0639748`, reason `interrupted` |
| CPIO 391 | `guest-hybrid-fx6kernel-capid-grmreal391-x8stub.cpio`, 430,232,336 B, SHA-256 `9c34f7b5…` |
| shim 391 | `libgrm-fbinit25-391.so`, SHA-256 `664f3571…` |

Durable copies under `work/fx6-385-17b9f-calltrace-20261107/`
(`serial-390.log`, `run-receipt-390.json`, `libgrm-fbinit25-391.c`, `fx6_post_stub.c`,
`libgrm-fbinit25-391.so`, manifest, runner).
