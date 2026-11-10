# Evidence 393 — the walk, 379 post-walk calls, then `1acd874` condition wait

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **393** `guest-hybrid-fx6kernel-capid-grmreal393-fulltrace.cpio`
Run: **`cp-bind-14949ca1`** (interrupted at 1,866.8 s after the trace had stopped at the blocker)
Result: `n=13793` walk completes; **379 of 382** `12d8174` call sites return; `POST379`
= `0x12d9de8 → 0x1acd874` never returns.

## 1. Trace endpoint

```text
FX6_DISPATCH n=13793
…
FX6_POST377_CALL a0=0x7fa05dce20 a1=0x1     POST377_RET
FX6_POST378_CALL a0=(nil) a1=(nil)          POST378_RET
FX6_POST379_CALL a0=0x7fa05dcfa0 a1=(nil)
(no POST379_RET)
(no POST380/POST381)
(no C09DE4B_RET / C14DFC_CALL / PRESENTER_CALL / SIGSEGV)
```

Site map:

| id | slot | target | result |
|---|---|---|---|
| 377 | `12d9ddc` | `10fa3cc` | RET |
| 378 | `12d9de0` | `10f727c` | RET |
| **379** | **`12d9de8`** | **`1acd874`** | **blocked** |
| 380 | `12d9dec` | `10f618c` | not reached |
| 381 | `12d9df4` | `1acce48` | not reached |

## 2. What `1acd874` is

Disassembly (abridged):

```text
1acd874  stp x29,x30,[sp,#-0x80]!
1acd880  mov x20,x0
1acd884  adrp x0,0x5a3b000 ; global guard at +0x7a8
1acd8a8  bl c1521c          ; guard constructor
1acd8b4  ldr x0,[x20]
1acd8b8  ldrb w0,[x0]
1acd8bc  cbnz w0,1acd8ec    ; fast path if already set
1acd8c0  bl 1accde8
1acd8cc  bl 1acd208         ; lookup lock record
1acd8d8  ldr w0,[x0,#0x30]  ; refcount
1acd8dc  cbnz w0,1acd914
1acd8e0  ldr x0,[x20,#0x10]
1acd8e4  mov x1,x23
1acd8e8  bl b19e30          ; PLT -> pthread_cond_wait (GOT 0x2ef2820)
…
1acd914  ldr x1,[x29,#0x58] ; owner
1acd91c  ldr x0,[x19,#0x7a0] ; global lock owner
1acd920  cmp x1,x0
1acd924  b.eq 1acd940
1acd93c  bl 2167784          ; assert (model_mutex.cpp:104)
1acd940  … pop waiter, bl b193d0 (cond signal), bl b19e30 again
```

`b19e30` is a GOT branch to `pthread_cond_wait`; `b193d0` to the corresponding
signal/broadcast. The function waits until the global model-lock owner state matches.
The AppFw thread never wakes, so the condition is never signalled in this environment.

## 3. Why this is likely a skipped-initializer artifact

`c56fdc` is:

```text
c56fdc  stp x29,x30,[sp,#-0x20]!
c56fe8  mov x19,x0
c56fec  bl 1acd618        ; <-- shim has been NOPing this since candidate 349
c56ff0  str xzr,[x19,#8]
c56ffc  ret
```

`1acd618` initializes the same model-lock machinery (guard c1521c, record lookup
1accde8, owner/refcount fields). It was NOPed in 349 to dodge a crash that we now know
was caused by the bogus `0x12d8264` NOP (stale `x0=0x10`). With `0x12d8264` restored in
389, every `c56fdc` call receives a valid object, so restoring `0xc56fec` should be safe
and may initialize the lock state that `1acd874` is waiting on.

## 4. 394 (running)

394 = 393 payload with the `0xc56fec` NOP removed (real `1acd618` call restored). It keeps
the 382-site trace so the same `POST379` line will show whether `1acd874` now returns.
Late GPE capture at `seconds-90` remains enabled.

Success criteria:

1. `POST379_RET` and `POST380/381_RET`;
2. `C09DE4B_RET`;
3. `C14DFC_CALL/RET`;
4. `PRESENTER_CALL`;
5. non-zero `gpe0-late.bin`.

## 5. Artifacts

| Item | Value |
|---|---|
| CPIO 393 | `guest-hybrid-fx6kernel-capid-grmreal393-fulltrace.cpio`, 430,238,000 B, SHA-256 `7f178402…` |
| run 393 | `cp-bind-14949ca1`, serial 3,109,949 B, SHA-256 `afce0bc5b7ca041dc946d39dd86301d279d1161ee262447b460c25f48fadba00`, reason `interrupted` |
| CPIO 394 | `guest-hybrid-fx6kernel-capid-grmreal394-c56init.cpio`, 430,237,384 B, SHA-256 `b5ed5cc7…` |
| shim 394 | `libgrm-fbinit25-394.so`, SHA-256 `c61ef57c…` |

Durable copies under `work/fx6-385-17b9f-calltrace-20261107/`
(`serial-393.log`, `run-receipt-393.json`, `libgrm-fbinit25-394.c/.so`, manifest, runner).
