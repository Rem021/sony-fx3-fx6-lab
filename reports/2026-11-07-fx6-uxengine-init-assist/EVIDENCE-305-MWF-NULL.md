# Candidate 289–305 — Native FX6 appFw reaches MWF, but null objects block Presenter

## Verdict

**Objective not complete.** Native FX6 UI (Big6) still has not rendered a real frame.

The experiment has moved from a self-built UI to the real FX6 50.5MB `appFw.so` and real
`Application_System_Init("AppConfig.so")`. It creates nine real 1024x540 UX ScreenAreas, but then
stops in MWF with null service objects before the Presenter/Widget factory path completes.

## What is now genuinely working

| Item | Evidence |
|---|---|
| Real FX6 `appFw.so` | 50,520,424 bytes, SHA-256 `a1c58b69…` |
| Real `global.xdb` / `image_00_169.uxc` / fonts | FX6 donor resources |
| `/usr/bin/appfw-launch` | correct FX6 `.rela.plt` GOT base `0x2ef1000…0x2ef2a00` |
| GOT rebinding | `entries=832 fixed=799 missing=33` |
| Backup service | memory-only `Backup_*`; no `/dev/backup` wait from appFw |
| `Application_System_Init` | real function called; returns |
| UI thread | starts; stella HeapAllocator created |
| Native UX layers | nine `FX6_UX_SCREEN_AREA_1024` objects |
| MWF null objects | bypassed with symbol-level null wrappers (not global NOPs) |

Key serial tail:

```text
FX6_APP_CONFIG_ENTRY arg=AppConfig.so
FX6_APP_CONFIG_HOLD real_returned
I/stella: Created HeapAllocator
I/stella: Replaced log-hook
FX6_UX_SCREEN_AREA_1024 × 9
FX6_MWF_NULL ObjShLock::Lock
FX6_MWF_NULL push_tail self=0
FX6_MWF_NULL ObjShLock::Unlock
```

## What still fails

The null MWF wrapper prevents SIGSEGV but drops the message pushes:

```text
ObjMsgList::push_tail(self=0) -> return 0
ObjShLock::Lock(self=0) -> return 0
```

No `FX6` widget/Presenter registration is reached. The gpe0 remains fully transparent.

## Candidates

| Candidate | Change | Result |
|---|---|---|
| 289 | truncate FX3 probes, load stream/dmm/grm_ma, real appFw | reaches UPM assert |
| 290 | add upm/udate/kikilog and seeds | reaches kikilog assert |
| 291 | add kikilog notify stub | reaches FTP/remote asserts |
| 293 | NOP five external-service calls | no crash, but no Presenter |
| 294 | stub-first preload + correct FX6 GOT | fixes GOT; Backup_read crash |
| 295 | Backup_read no-memset | 9 ScreenAreas; no Presenter |
| 299 | fake success for osal_rcv | same |
| 300 | null pthread mutex compatibility | passes mutex, new MWF null |
| 301 | ObjShLock::Lock return | passes, new ObjMsgList null |
| 302 | ObjMsgList::push_tail global return | passes, but drops messages |
| 303 | ObjShLock::Unlock return | no crash; threads wait |
| 305 | symbol-level null wrappers only | valid calls go to real MWF; still no Presenter |

## Root cause boundary

The block is **not** the UI layout, colors, fonts, or text renderer. It is:

```text
external FX6 services absent in FX3 VM
-> MWF service objects have null ObjShLock/ObjMsgList
-> UI thread never reaches Presenter registration
```

The current wrappers are VM compatibility shims, not a native UI implementation. They must be
replaced by correct object construction / service initialization before any native frame is claimed.

## Next

1. Identify the object that owns the null `ObjMsgList` (caller of `push_tail(self=0)`).
2. Trace its constructor / `RsrcAcsr` initialization; do not globally drop messages.
3. Preserve `0xc14dfc`, `0x1397450`, `0xdf91e8`.
4. Capture a real 1024x540 `0x41e001000` frame only after Presenter registration.

## Repro

Base: `guest-hybrid-fx6kernel-capid-grmreal305-mwfwrap.cpio`

Latest run: `runs/cp-bind-de72af8e`

Serial SHA-256: `04e34566e70beb3d9938830b1c667921e43b5736de80420491c756af4b38a7e9`

gpe0: transparent, 1 color; no native frame.

---

## Round 2 update — 308/309: real RsrcRelation initialization

The upstream null object was identified and fixed properly.

Disassembly of `MWF::RsrcRelation::AddRsrcAcsr` showed that it pushes through the GOT slot for:

```text
MWF::RsrcRelation::mp_acsrInsList
```

`MWF::RsrcRelation::Initialize()` allocates that `ObjMsgList` plus three `ObjShLock` objects and
stores them via GOT slots. It had never been called in the hybrid environment.

Candidate 308 calls the real `RsrcRelation::Initialize()` from the preload shim before
`Application_System_Init("AppConfig.so")`:

```text
FX6_RSRC_RELATION_INIT mwf=... fn=...
```

Result:

```text
FX6_MWF_NULL ... = 0     (no more null MWF logs)
9 × FX6_UX_SCREEN_AREA_1024
no SIGSEGV
no assertion
```

Candidate 309 restores `0xc09e50` (the 0x910040/20s path) instead of NOPing it. It still creates
nine ScreenAreas and then produces no Presenter/Widget logs and no frame within 150s.

### Current exact boundary

```text
RsrcRelation globals: initialized (real)
ObjMsgList / ObjShLock: non-null
9 UX ScreenAreas: created
Widget factory / Presenter: still not reached
gpe0: fully transparent
```

This is no longer a null-object crash. The next step is to inspect the UI thread wait state after
the nine ScreenAreas and trace `0xc09e50` / `0x12d8254` completion, preserving all real registration.

Candidates:

```text
308  guest-hybrid-fx6kernel-capid-grmreal308-rsrcinit.cpio
309  guest-hybrid-fx6kernel-capid-grmreal309-trigger.cpio
```

---

## Round 3 update — 306–310: RsrcRelation fixed; AppFw waits after 9 ScreenAreas

`MWF::RsrcRelation::AddRsrcAcsr` was pushing through the GOT slot for
`MWF::RsrcRelation::mp_acsrInsList`. The missing initializer was identified as
`MWF::RsrcRelation::Initialize()`, which allocates `ObjMsgList` and three `ObjShLock` objects.

Candidate 308 calls the real initializer before `Application_System_Init`:

```text
FX6_RSRC_RELATION_INIT mwf=... fn=...
```

Result of 308/309:

```text
- no FX6_MWF_NULL logs
- no SIGSEGV
- no assertion
- 9 × FX6_UX_SCREEN_AREA_1024
- no Widget/Presenter registration
- gpe0 fully transparent
```

Candidate 309 restored the `0xc09e50` trigger path; it did not produce a Presenter within 150s.

Candidate 310 adds `comm`/kernel stack to the monitor. The UI/AppFw threads after the nine
ScreenAreas are:

| TID | comm | wchan | role |
|---|---|---|---|
| 217 | appfw-launch | hrtimer_nanosleep | launcher main |
| 222 | AppFw | futex_wait_queue_me | application/UI thread |
| 223 | uxengine_res1 | futex_wait_queue_me | UX resource |
| 224 | uxengine_res2 | futex_wait_queue_me | UX resource |
| 225 | InfraNotify | futex_wait_queue_me | infrastructure notify |
| 226–240+ | IWrapperBB/HDMI/Imaging/UPM/... | osal_rcv_msg_tmo / osal_unlock | IPC service threads |

This confirms the native appFw is past null-object construction but its `AppFw` thread is blocked
on a userspace futex after the UX layers.

### Next

1. Attach GDB to the running `AppFw` thread (222) and obtain its userspace backtrace, or
   interpose `pthread_cond_wait`/`pthread_join` to capture the futex caller.
2. Map the wakeup owner among the 45 IPC service threads.
3. Preserve the real RsrcRelation initialization and the real service registration.
4. Only claim a native frame after Presenter registration and a non-empty `0x41e001000` gpe0.

Latest run:

```text
310  cp-bind-179a4af2
CPIO guest-hybrid-fx6kernel-capid-grmreal310-comm.cpio
```

---

## Round 4 update — 311–313: AppFw thread is in an event-loop cond wait

After `RsrcRelation::Initialize`, no null MWF objects remain. Interposing
`pthread_cond_wait` and logging module/offset of both caller levels gives:

```text
FX6_COND_WAIT tid=222 cond=0x7f8801e460 mutex=0x7f946ec7a8
  ra=libstdc++.so.6+0xb3610
  ra1=appFw.so+0x1acd988
```

Other waiters:

```text
tid=223 stella.so+0x24de4 (ra1 stella+0x2c990)
tid=224 stella.so+0x24de4
tid=225 libstdc++ wait, ra1=appFw+0x1a76e68
tid=244+ appFw+0x20c4560 / service waits
```

Disassembly at `appFw+0x1acd988`:

```text
1acd97c  ldr  x0, [x20,#0x10]
1acd980  mov  x1, x23
1acd984  bl   std::condition_variable::wait(unique_lock<mutex>&)
1acd988  ldr  x0, [x19,#0x7a0]   ; event/job state
1acd98c  cbz  x0, 0x1acda08
1acd990  ...
```

This is a normal **event/job-loop condition wait**, not a null-object crash. The AppFw thread is
idle waiting for a notify at `0x1acd978` / `0x1acd9d0`.

### Current boundary

```text
RsrcRelation: real initialized
MWF null objects: gone
9 ScreenAreas: created
AppFw tid222: condition_variable wait in event loop
no Widget/Presenter registration
no native frame
```

### Next

1. Identify the job/notify producer for the loop at `appFw+0x1acd988`.
2. Determine whether the nine ScreenAreas need a menu/input job or the `0x910040` trigger.
3. Preserve real object/service initialization; enqueue the missing job rather than faking the UI.
4. Only claim a native frame after Presenter registration and non-empty gpe0.

Runs:

```text
311 cp-bind-5ae93920
312 cp-bind-c4eb5b00
313 cp-bind-aff26593
```

---

## Round 5 update — 314: presenter hook out of BL range

To verify whether `0xc0a860 -> 0x1397450` is reached, 314 tried to patch that
`bl` to a shim logger:

```text
FX6_PRESENTER_HOOK slot=7f9357f860 target=7fa4f01748 delta=295182056
FX6_PRESENTER_HOOK_RANGE
```

The shim is 295 MB away; AArch64 `bl` only reaches ±128 MB, so the hook was not installed.
This is a tooling limitation, not evidence about presenter execution.

Current native state remains:

```text
RsrcRelation initialized
no null MWF objects
9 × FX6_UX_SCREEN_AREA_1024
AppFw event-loop cond wait
no Widget/Presenter/frame
```

Next: install a near trampoline in an executable appFw-adjacent mapping (or use a QEMU GDB
breakpoint) to determine whether 0xc0a860/0x1397450 runs; then enqueue/render the correct UI job.

---

## Round 6 update — 315–317: near trampoline attempt hit appFw TLS

315 tried a hinted mmap trampoline; 316 used MAP_FIXED at appFw+0x4000000. 317 switched
to RW→RX and logged errno.

317 result:

```text
FX6_PRESENTER_TRAMP ... tr=0  (315/316)
```

317 crashed inside the shim itself:

```text
APPFW_SEGV addr=0x7fa9428010
PC=libgrm-fbinit9.so+0x18cc0
```

Disassembly at the fault:

```text
18cc0  str w8, [x9]     ; x9 = 0x7fa9428010
```

`0x7fa9428010` is exactly the fixed `appFw+0x4000000` mapping used for the trampoline.
The appFw TLS/errno pointer lives in that region, so MAP_FIXED overwrote it; the shim then
crashed while writing `errno`.

This is a **mapping bug**, not evidence about Presenter execution. No native frame.

### Next

- Do not MAP_FIXED over appFw TLS.
- Allocate a near page only after validating it is outside appFw segments and TLS
  (e.g. +0x8000000, still inside BL range), or use a QEMU GDB breakpoint.
- Then determine whether 0xc0a860/0x1397450 runs and enqueue the real UI job.

Candidates: 315 tramp, 316 trampfixed, 317 tramprx.

---

## Round 7 update — 318–320: presenter hook installed, never hit

Fixes:

- 318: near mmap was tested with the wrong BL range (`1<<25` instead of `1<<27`).
- 319: installed the trampoline but wrote code after mprotect RX, causing a write fault.
- 320: writes trampoline while RW, then mprotect RX, then patches appFw.

320 result:

```text
FX6_PRESENTER_MMAP hint=... p=...
FX6_PRESENTER_TRAMP slot=... target=...
FX6_PRESENTER_TRAMP_RX mprotect=0
FX6_PRESENTER_TRAMP_PATCH insn=95cfd5e8 mprotect=0 delta=121591712
9 × FX6_UX_SCREEN_AREA_1024
```

No `FX6_PRESENTER_CALL` in the entire run.

This is now positive evidence: the hook was correctly installed at `0xc0a860`, but
`0xc0a860 -> 0x1397450` **never executes**. Presenter registration is not being attempted;
the UI loop stops before that call.

Current boundary:

```text
RsrcRelation: real initialized
MWF null: gone
9 ScreenAreas: created
0xc0a860 presenter call: not reached
AppFw event-loop cond wait: still the stop point
native frame: none
```

Next: hook earlier call sites (`0xc0a6cc` / `0xc0a854` / `0xc09da0`) to determine which
branch of the UI loop is skipped, then feed the correct job/notify.

Candidates: 318 trampsafe, 319 tramp127, 320 trampwx.

---

## Round 8 update — 321–325: c09da0 entered but never returns

Working near trampolines (after the 320 W^X fix) allowed hooking the UI loop:

```text
0xc0a6cc  bl 0xc09da0     -> FX6_C09DA0_CALL x0=...
0xc0a860  bl 0x1397450    -> installed, never called
```

Candidate 322 (call/ret logger):

```text
FX6_C09DA0_CALL
(no FX6_C09DA0_RET)
```

So `c09da0` does not return; Presenter registration at `0xc0a860` is never reached.

Candidates 324/325 tried to skip the known tail waits:

```text
324: NOP 0xc09e50  -> still no RET
325: NOP 0xc09e48 + 0xc09e50 -> still no RET
```

Disassembly at `c09da0` shows the tail calls are:

```text
c09e44  ldr x0, [GRM callback]
c09e48  bl  GRM_fbrmRegisterTriggerFrameworkCb
c09e50  bl  0xc09c14     ; 0x910040 / 20s wait
c09e54  return
```

Skipping both still leaves `c09da0` blocked earlier, before the GRM tail. The next candidates are
the earlier calls in `c09da0`, especially:

```text
c09df0  bl 0xc14dfc   ; widget factory
c09df8  bl 0x10f5eb8
c09e0c  bl 0xde31ac
c09e10  bl 0xc1412c
```

No native frame; `0x41e001000` remains transparent.

Next: hook `0xc09df0 -> 0xc14dfc` and subsequent calls to locate the exact non-returning child.

---

## Round 9 update — 326: c14dfc widget factory is not reached

A near trampoline was installed at:

```text
0xc09df0  bl 0xc14dfc   (widget factory)
```

Run 326:

```text
FX6_C14DFC_MMAP p=...
FX6_C14DFC_HOOK ... mr=0
9 × FX6_UX_SCREEN_AREA_1024
FX6_C09DA0_CALL x0=...
(no FX6_C14DFC_CALL)
```

So `c09da0` blocks **before** `c09df0 -> c14dfc`.

Earlier `c09da0` body:

```text
c09db4  x22 = x0 + 0xa40
c09db8  x21 = x0 + 0x1000
c09dbc  x0 = [x0 + 0x20]
c09dc4  ldr x1,[x0]; ldr x2,[x1]; blr x2   ; virtual call
c09dd8  bl 0x114a068
c09de4  bl 0x12d9fc8
c09df0  bl 0xc14dfc   ; NOT reached
```

Next hooks: the virtual `blr x2` path, then `0xc09dd8 -> 0x114a068` and
`0xc09de4 -> 0x12d9fc8`.

No native frame; gpe0 transparent.

---

## Round 10 update — 326–329: invalid virtual object at c09dc4

326: `c09df0 -> c14dfc` hook installed; never called.

327: `c09dd8 -> 114a068` and `c09de4 -> 12d9fc8` hooks installed; neither called.

328: hooked `c09dc4  blr x2`:

```text
FX6_VIRTUAL_CALL x0=... x1=(nil) x2=0x7f666871e0 mod=? off=0
APPFW_SEGV addr=0x7f666871e0 pc=0x7f666871e0
```

x2 is a heap/data address, not code; the virtual object reached through `[x0+0x20]` has an
invalid vtable slot.

329: skipped the invalid virtual call:

```text
FX6_VIRTUAL_SKIP_INVALID
FX6_VIRTUAL_RET
APPFW_SEGV addr=(nil) pc=c09dc8
```

Skipping is not sufficient: `c09dc8` immediately dereferences state expected from the virtual call.

### Current root

`c09da0` calls a virtual method at `c09dc4` on the object at `[x0+0x20]`; that object's vtable
slot is not code. This is the first hard block before `c14dfc`/`0x1397450`. It must be constructed
or replaced with the correct FX6 UI object, not skipped.

No native frame; gpe0 transparent.

---

## Round 11 update — 330–331: virtual call target corrected

330 read the c09da0 object:

```text
FX6_C09DA0_Q20 a=...
A0=... A8=...
V0=... V8=...
```

It showed the earlier hook at `c09dc4` was on the wrong instruction (`ldr x1`), not the `blr x2`.
331 moved the hook to the real indirect call at:

```text
0xc09dd0  blr x2
```

Result:

```text
FX6_VIRTUAL_CALL x0=... x1=... x2=... mod=/usr/lib/appFw.so off=c0afd0
FX6_VIRTUAL_RET x0=... x1=...
```

So the virtual slot is valid (`appFw+c0afd0`) and returns normally. The previous invalid-x2
crash was our hook mistake.

However, after the virtual return:

```text
FX6_C09DD8_HOOK installed
FX6_C09DE4_HOOK installed
FX6_C14DFC_HOOK installed
(no CALL for any)
(no FX6_C09DA0_RET)
```

`c09dd8`/`c09de4`/`c14dfc` are still not reached after the virtual call. The next step is to
verify the return path from the trampoline (LR/stack) and inspect c09da0 between c09dd4 and
c09dd8; do not treat the virtual call as the blocker anymore.

No native frame; gpe0 transparent.

---

## Round 12 update — 332: original blr also does not reach c09dd8

332 removed the c09dd0 trampoline and let the original `blr x2` run. The virtual object read is valid:

```text
FX6_C09DA0_Q20 ...
FX6_C09DA0_A0 ...
FX6_C09DA0_V0=appFw+...
```

Still:

```text
no FX6_C09DD8_CALL
no FX6_C14DFC_CALL
no FX6_C09DA0_RET
```

So the original virtual call (`appFw+c0afd0`) itself does not lead to c09dd8/c14dfc in this
environment. 331's wrapper returned from the call, but the caller still did not proceed; 332's
un-instrumented call blocks/returns elsewhere.

This is now the exact boundary: the first virtual call inside c09da0, on `[x0+0x20]`, must be
made to complete with correct semantics. The object/vtable is present, but its method likely
depends on absent FX6 UXEngine state.

No native frame; gpe0 transparent.

---

## Round 13 update — 333: appFw+c0afd0 is only `ret`

Disassembly:

```text
c0afd0: d65f03c0  ret
c0afd4: ret
c0afd8: ret
...
```

So the first virtual call inside c09da0 is a trivial return; it has no business logic and cannot
be the semantic blocker. `blr x2` returns to `c09dd4` immediately.

Yet 331/332 still show:

```text
no FX6_C09DD8_CALL
no FX6_C14DFC_CALL
no FX6_C09DA0_RET
```

This shifts the fault to the instrumented return path / LR handling around c09dd0, or to the
c09da0 trampoline itself, not to an absent UXEngine operation.

Next: verify the exact LR/PC after the c09dd0 trampoline returns (c09dd4 expected), and test
without the c09da0/c09dd0 trampolines but with only a c14dfc entry hook. Do not chase c0afd0.

---

## Round 14 update — 334: minimal hooks still do not reach c14dfc

334 removed the c09da0 entry trampoline and all c09dd0 virtual instrumentation, keeping only:

```text
c14dfc call-site hook
presenter call-site hook
RsrcRelation initialization
```

Result:

```text
FX6_C14DFC_HOOK ... mr=0
9 × FX6_UX_SCREEN_AREA_1024
(no FX6_C14DFC_CALL)
(no FX6_PRESENTER_CALL)
```

So the missing c14dfc is **not caused by the c09da0/c09dd0 trampolines**. The original c09da0
path itself stops before c09df0.

Given `appFw+c0afd0` is just `ret`, the next candidate is the original call at:

```text
c09dd8  bl 0x114a068
```

(and c09de4 -> 0x12d9fc8). No native frame; gpe0 transparent.

---

## Round 15 update — 335: c09de4 blocks, c09dd8 returns

335 kept the minimal hooks and added only c09dd8/c09de4 call-site hooks. Result:

```text
FX6_C09DD8B_HOOK ... mr=0
FX6_C09DE4B_HOOK ... mr=0
FX6_C14DFC_HOOK ... mr=0
9 × FX6_UX_SCREEN_AREA_1024
FX6_C09DD8B_CALL x0=...
FX6_C09DD8B_RET
FX6_C09DE4B_CALL x0=...
(no C09DE4B_RET)
(no C14DFC_CALL)
```

So the new exact blocker is:

```text
c09de4  bl 0x12d9fc8
```

It is entered and does not return. c14dfc is after it, so Presenter is still unreachable.

Next: hook/skip 0x12d9fc8 or inspect it; if it is a blocking wait, replace with a timeout, not a
global bypass. No native frame; gpe0 transparent.

---

## Round 16 update — 336–337: 12d8174 blocks before 12d824c

336 skipped only `0x12d8254`; 337 also skipped `0x12d824c`, `0x12d8250`, `0x12d825c`.
Both still show:

```text
FX6_C09DD8B_CALL / RET
FX6_C09DE4B_CALL
(no C09DE4B_RET)
(no C14DFC_CALL)
```

So the block inside `12d9fc8 -> 12d8174` is **earlier** than 12d824c:

```text
12d8244  bl 0xc0cbc0
12d8248  bl 0x10f6208
12d824c  MonCtrl
12d8250  hardware IPC
12d8254  external process loader
12d8258/12d825c ...
```

Next: hook/skip 0x10f6208 or 0xc0cbc0, preserving RsrcRelation and the rest. No native frame.

---

## Round 17 update — 338–339: early 12d8174 calls return

338 hooked:

```text
12d8244 -> 0xc0cbc0   CALL/RET
12d8248 -> 0x10f6208  CALL/RET
```

Both return normally. 339 additionally NOPed 12d8258 (and already 12d824c/50/54/5c), but:

```text
FX6_C09DE4B_CALL
(no C09DE4B_RET)
(no C14DFC_CALL)
```

So the block is **not** 12d8244, 12d8248, or the 12d824c/50/54/58/5c cluster; it is later in
12d8174 (or in a constructor before those calls).

Next: hook the next 12d8174 calls after 12d8260 (and locate the next non-returning child).
No native frame.

---

## Round 18 update — 340: all early 12d8174 children return

340 added CALL/RET hooks for:

```text
12d81ac -> 0x15373c0   CALL/RET
12d81b0 -> 0xc0b9a8    CALL/RET
12d8244 -> 0xc0cbc0    CALL/RET
12d8248 -> 0x10f6208   CALL/RET
```

Result:

```text
FX6_C09DE4B_CALL
FX6_12D81AC_CALL / RET
FX6_12D81B0_CALL / RET
FX6_12D8244_CALL / RET
FX6_12D8248_CALL / RET
(no C09DE4B_RET)
(no C14DFC_CALL)
```

So the block is **after 12d8248** inside 12d8174, not in the early constructors. With 12d824c/50/54/58/5c
already NOPed, the next candidates are the following block from 12d8260 onward.

No native frame; gpe0 transparent.

---

## Round 19 update — 341–342: crash inside c56fdc

341 hooked the next calls:

```text
12d8260 -> 0x10f5bf8  CALL/RET
12d8264 -> 0xc56fdc   CALL then SIGSEGV
```

Crash:

```text
APPFW_SEGV pc=appFw+c56ff0  x0=0  addr=0x18
```

So `c56fdc` is called with a null/0x10-like object and faults at +0x14.

342 NOPed `12d8264`; however the same crash still occurred at `appFw+c56ff0` immediately after
`FX6_C09DE4B_CALL`. This means another path also calls `c56fdc` (or the NOP was not on the executed
call site).

Exact blocker is now:

```text
c56fdc with invalid/null object
```

No native frame.

---

## Round 19b — 343: c56fdc is a high-frequency utility

Static scan of appFw `.text` found ~22,176 direct BL sites targeting `0xc56fdc`
(first verified at `0xc66a28`). It is a general utility, not a single UI call.

Consequences:

- NOP at `12d8264` alone cannot prevent all calls; 342 still crashed at
  `appFw+c56ff0` with `x0=0`.
- Fixing it requires a null-safe entry guard or identifying the exact caller
  (stack/LR) of the failing call, not a single call-site NOP.

Current blocker remains `c56fdc` + invalid object; no native frame.

---

## Round 20 update — 344: c56fdc entry guard does not stop the crash

344 installed a near trampoline at `c56fdc` entry:

```text
FX6_C56FDC_GUARD_MMAP p=...
FX6_C56FDC_GUARD_PATCH entry=... tr=... mr=0
```

It copies the first four instructions, adds a null guard, and branches back to `c56fec`.
Nevertheless:

```text
FX6_C09DE4B_CALL
APPFW_SEGV pc=appFw+c56ff0  addr=0x8  X19=0
```

The crash is still `str xzr,[x19,#8]` with `x19=0`. The guard did not catch the call, so entry
x0 was not <0x1000, or the guarded path did not branch as intended. Need to disassemble the
runtime trampoline / verify x0 at entry and the c56fec call's effect on x19.

No native frame.

---

## Round 22 update — 345: c56fdc is called with a valid x0

345 replaced c56fdc entry with a no-op trampoline. Result:

```text
FX6_C56FDC_NOOP x0=0x7f734a1d30 lr=appFw...
APPFW_SEGV addr=0x400001efe
```

The call is reached with a **valid** x0, so the previous x19=0 crash was from c56fdc's internal
behavior, not a null argument. Skipping c56fdc removes required side effects and crashes later
at a different address.

Conclusion: c56fdc must be executed, but its body/ABI handling needs correction; a no-op is not
valid. No native frame.

---

## Round 23 update — 346: corrected guard still sees X19=0

346 fixed the guard to test `x0 < 0x1000` via `subs xzr,x0,#0x1000; b.lo`, not just `cbz`.
It still crashes:

```text
FX6_C09DE4B_CALL
APPFW_SEGV pc=appFw+c56ff0
X19=0
addr=0x8
```

So either:

- `c56fdc` is entered with a valid x0 (guard passes), but the call at `c56fec` destroys x19, or
- the guard trampoline branch/layout is not executing as intended.

Next: verify the runtime trampoline bytes and the effect of `0x1acd618` on x19. No native frame.

---

## Round 24 update — 347: guard entry changed from BL to B

Root cause found in 346 guard: the entry patch used `BL` to the trampoline, which overwrites
LR with `c56fe0` before `mov x17,x30`. The guard then saved the wrong return address.

347 changes the entry patch to:

```text
B trampoline   ; preserves caller LR in x30
```

so the trampoline can save the real caller LR, run the copied prologue, and return correctly.

Built:

```text
guest-hybrid-fx6kernel-capid-grmreal347-guardb.cpio
sha256 465760b8...
```

Not yet run/verified. No native frame.

---

## Round 25 update — 347/348: guard B stops crash, c09dd8 loops

347 changed the c56fdc entry patch from BL to B (preserves caller LR). 348 ran it for 120s.

Result:

```text
FX6_C56FDC_GUARD2_PATCH ... mr=0
9 × FX6_UX_SCREEN_AREA_1024
FX6_C09DD8B_CALL / RET repeated for 25 MB of serial
no APPW_SEGV
no C09DE4B_CALL
no C14DFC_CALL
no PRESENTER_CALL
gpe0 transparent
```

So the guard no longer takes the old crash, but the UI now spins through c09dd8 instead of
reaching c09de4/c14dfc. This is a new loop state, not a native frame.

Next: stop the c09dd8 loop (identify caller/task) or let c09da0 continue to c09de4; preserve the
correct c56fdc side effects.

---

## Round 26 update — 349: skipping c56fec removes crash, still no return

349 did not touch c56fdc entry; it NOPed only the internal call:

```text
c56fec  bl 0x1acd618  -> NOP
```

Result:

```text
FX6_PATCH_C56FEC_NOP mprotect=0
9 × FX6_UX_SCREEN_AREA_1024
FX6_C09DE4B_CALL
no APPW_SEGV
(no C09DE4B_RET)
(no C14DFC_CALL)
(no PRESENTER_CALL)
```

So removing the internal c56fdc call avoids the crash but leaves c09de4 not returning. The next
step is to locate its remaining wait/loop after c56fec, not to skip more blindly. No native frame.

---

## Round 27 update — 350: 180s not enough / c09de4 still stuck

Re-ran 349 for the runner maximum 180s.

```text
FX6_C09DE4B_CALL 1
FX6_C09DE4B_RET 0
FX6_C14DFC_CALL 0
FX6_PRESENTER_CALL 0
APPFW_SEGV 0
FX6_UX_SCREEN_AREA 9
```

So the non-return is not just slow initialization; c09de4 is stuck (or loops) after c56fdc.
No native frame.

---

## Round 28 update — 351: 12d8174 first loop is finite

Disassembly around 12d826c shows a finite loop:

```text
12d8358  add x21, x21, #0x70
12d8368  cmp x21, #0x150
12d836c  b.ne 12d826c
```

Then nested loops (3 × 2 × 4) and many later calls. So c09de4's non-return is not the first
x21 loop being infinite; it must block in one of the later initialization calls (around
12d85b8 onward).

No native frame.

---

## Round 29 update — 352: next calls are trivial setters

Disassembly of:

```text
12d85bc -> 0x121e9e4
12d85c4 -> 0x120eadc
```

shows ordinary setter/update functions; neither waits. The 12d8174 loops are finite
(`cmp x21,#0x150`; nested 3x2x4). Thus c09de4's non-return is in a later synchronous call,
not these setters or the first loop.

No native frame.

---

## Round 30 update — 353: 12d9fc8 tail not reached

Hooked:

```text
12da038 -> 0x1ac81b4
12da044 -> 0x1acd2f4
```

Result:

```text
FX6_C09DE4B_CALL
(no FX6_12DA038_CALL)
(no FX6_12DA044_CALL)
(no C14DFC_CALL)
```

So c09de4 is still inside **12d8174**, before the 12d9fc8 tail. The search remains within
12d8174 after c56fdc. No native frame.

---

## Round 31 update — 354: loop calls not reached

Hooked:

```text
12d8274 -> 0x113e8f4
12d8288 -> 0x1188b38
```

Result:

```text
FX6_C09DE4B_CALL
(no 12D8274_CALL)
(no 12D8288_CALL)
(no C14DFC_CALL)
```

So c09de4 is stuck **before** the 12d8274 loop, even earlier than the finite x21 loop.
This invalidates the assumption that it reached the loop. Next must instrument the path
between c09da0 tail and 12d8244 again, with the current 349 patch set, because earlier hook
results were from different candidate sets.

No native frame.

---

## Round 32 update — 356: exact blocker 12d81bc -> 0x15373ec

356 added CALL/RET hooks for:

```text
12d81b4 -> 0x1b3f730    CALL/RET
12d81bc -> 0x15373ec    CALL / no RET
```

Result:

```text
FX6_12D81B4_CALL 1
FX6_12D81B4_RET 1
FX6_12D81BC_CALL 1
FX6_12D81BC_RET 0
FX6_C09DE4B_RET 0
FX6_C14DFC_CALL 0
```

So c09de4 blocks exactly at:

```text
12d81bc  bl 0x15373ec
```

inside 12d8174, before 12d8244 and before the x21 loop. Next: disassemble 0x15373ec and
find its wait/loop. No native frame.

---

## Round 33 update — 357: 15373ec is a large condvar constructor

Disassembly of `0x15373ec` shows repeated:

```text
operator new(0x30)
std::condition_variable::condition_variable()
store at global+...
```

It is a large object/condition-variable constructor, not a direct wait or infinite loop at entry.
The no-return may be due to an enormous initialization sequence or a later blocking call inside it.

No native frame.

---

## Round 34 update — 358: skipping 15373ec breaks c56fdc precondition

358 NOPed `12d81bc -> 0x15373ec` while keeping the c56fec NOP.

Result:

```text
FX6_C09DE4B_CALL
FX6_12D8244_CALL / RET
APPFW_SEGV pc=appFw+c56ff0  X19=0
```

So skipping the condvar constructor let 12d8244 run, but the later c56fdc call again received an
invalid object and crashed at +0x14. The constructor at 0x15373ec initializes state that c56fdc
depends on; it cannot simply be skipped.

The real block is that this large condvar constructor does not finish in 180s under this setup.
No native frame.

---

## Round 35 update — 359: 15373ec is small enough to finish quickly

Static count from 0x15373ec:

```text
operator new calls: 48
std::condition_variable constructions: 19
first ret: 0x1537898
```

So it is not a massive constructor. Under TCG it should finish quickly. The 180s non-return is
therefore a **blocking subcall / lock**, not raw volume.

Next: instrument the first 48 `new`/condvar steps or find which constructor waits.
No native frame.

---

## Round 36 — gdbstub probe (2026-11-08)

QEMU does expose a gdbstub on TCP 1234 (`-s` in argv). A minimal RSP client was used.

Results:

```text
qSupported: PacketSize=20020; ... multiprocess+
qfThreadInfo: m01 / m02
Hg1..Hg4: OK
CPU0..CPU3 PC=0xffffff8008097988 (__switch_to)
SP/FP in kernel stacks
```

So the gdbstub exposes **only the four vCPUs**, not Linux user threads. While appFw is blocked,
all four vCPUs are idle in `__switch_to`; there is no way to select the appFw thread (222) or read
its userspace stack via this interface. The `0x15373ec` user virtual address is not in the current
CPU context.

Conclusion: gdbstub cannot provide the needed 15373ec internal call stack in this harness.
Pivot to in-process instrumentation (operator new/condvar call tracing inside 15373ec).
No native frame.

---

## Round 37 — 360/362/363: 46th allocation is the last trace point

`_Znwm` was interposed to log callers inside 0x15373ec:

```text
FX6_NEW_15373 off=0x1537414 ... 0x15377c4 (46 calls, size=48)
```

362 hooked `15377d0 -> 0x1778edc`: never called.
363 disassembled 15373dc: it only zeroes 0x30 bytes and returns, cannot block.

So after the 46th `_Znwm` call at 0x15377c4, neither 15373dc's store nor 15377d0 is observed.
Because `_Znwm` logs **before** calling the real allocator, the block may be inside the real
operator new / malloc for that 46th allocation.

No native frame.

---

## Round 38 — 364: all 46 allocations return

`_Znwm` now logs both entry and return:

```text
FX6_NEW_15373 46
FX6_NEW_RET 46
last RET off=0x15377c4 r=0x7f8c014720
```

So the allocator is not blocked. After the last `new` at 0x15377c4, the block occurs before
the call at 0x15377d0. The intervening code is only:

```text
15377c8  bl 15373dc   ; zero 0x30 bytes
15377cc  str x20,[x19,#0x468]
15377d0  bl 0x1778edc
```

15373dc is trivial. This leaves a store/page fault, a preemption never scheduled, or an
instrumentation/cache artifact; no SIGSEGV is reported.

No native frame.

---

## Round 39 — 420s run: model_mutex assert

A 420s run of 349 (max raised in a copy) still produced:

```text
9 × FX6_UX_SCREEN_AREA_1024
no C09DE4B_RET
no C14DFC_CALL
no PRESENTER_CALL
no SIGSEGV
```

New repeating serial evidence:

```text
assert at model_mutex.cpp:59
function: model::model_lock::model_lock()
assert at model_mutex.cpp:59
function: model::model_lock::model_lock()
...
```

So the long non-return is not only a large table initialization; the model lock path is asserting
repeatedly. This is a concrete new blocker: `model::model_lock` construction/recursion.

Next: locate model_mutex.cpp:59 assert and fix the lock state; do not skip the whole 15373ec.
No native frame.

---

## Round 40 — 371: model_mutex string xref

The only xref to the `model_mutex.cpp` string in appFw is at 0x1acd6dc, inside the UI
condition-variable wait loop:

```text
1acd6bc  bl std::condition_variable::wait
1acd6c0  ldr x1,[x21,#0x7a0]
1acd6c4  ldr x0,[x29,#0x58]
1acd6c8  cmp x1,x0
1acd6cc  b.eq ...
1acd6d0  adrp x2, model_mutex.cpp
1acd6d4  mov w1,#55
1acd6dc  assert(...)
```

That site is line 55, not the logged line 59; line 59 likely another shared assert site.
This is a **lock-owner/condition-wait assert**, not a constructor assert.

Consequence: c09de4's non-return may be the UI loop repeatedly hitting a model lock ownership
assert after a condition wait, not the 15373ec constructor itself.

Next: locate the line-59 site or all callers of this assert, and fix lock ownership/init.
No native frame.

---

## Round 41 — 377: exact line-59 site

Line-59 `model_mutex.cpp` assert is at 1acd78c:

```text
1acd780  ldr w0,[x20,#0x30]
1acd784  cmp w0,#0
1acd788  b.gt 1acd6e8
1acd78c  adrp x2, model_mutex.cpp
1acd790  mov w1,#59
1acd794  add x2, x2, #0x6d8
1acd798  b 1acd6dc  ; assert
```

So it checks a **counter at x20+0x30** (<=0) in the UI queue/condition-wait path, not a
model_lock constructor. The repeated assert means the queue/refcount state is wrong after
the condition wait.

No native frame.

---

## Round 42 — 378: assert moves to line 75

378 NOPed the model_mutex assert logger calls at 1acd6dc and 1acd7b8.

Result:

```text
FX6_ASSERT_NOP 2
FX6_C09DE4B_RET 0
FX6_C14DFC_CALL 0
FX6_PRESENTER_CALL 0
9 ScreenAreas
assert at model_mutex.cpp:75
```

So suppressing the earlier assert sites does not fix the lock state; the next assertion (line 75)
appears. This confirms the lock/queue ownership is genuinely inconsistent, not just noisy logging.
No native frame.

---

## Round 43 — 379: all model_mutex asserts silenced, still no c14dfc

379 NOPed line75 assert (1acd378) in addition to line55/59/64.

Result:

```text
FX6_ASSERT75_NOP 1
FX6_ASSERT_NOP 2
assert at model_mutex 0
FX6_C09DE4B_RET 0
FX6_C14DFC_CALL 0
FX6_PRESENTER_CALL 0
9 ScreenAreas
```

So the assert logging was secondary; the UI still does not progress to c14dfc. The block is now
in the post-15373ec table/loop path (`1537e00` repeated 0x1778ebc calls) or its synchronization.
No native frame.

---

## Round 44 — 380: 1778ebc is a table dispatcher

Disassembly:

```text
1778ebc  sxtw x0,w0
1778ec0  mov  x3,#0x30
1778ec4  adrp x2,0x2b78000
1778ec8  add  x2,x2,#0xb10
1778ecc  madd x0,x0,x3,x2
1778ed0  ldr  x2,[x0,#0x20]
1778ed4  mov  x0,x1
1778ed8  br   x2
```

So 1537e00 dispatches ~14k table entries through a function pointer; c09de4 is likely stuck inside
one handler, not in the dispatcher. Without logging the dispatcher's x2/handler sequence, we cannot
identify which entry blocks.

No native frame.

---

## Round 44 — 382: dispatcher reaches n=1003, last handler 17b9f1c

With a correct dispatcher hook (1778ed8), 382 logged 1003 dispatches:

```text
FX6_DISPATCH n=999  x2=appFw+17b9bdc
FX6_DISPATCH n=1000 x2=appFw+17b9cac
FX6_DISPATCH n=1001 x2=appFw+17b9d7c
FX6_DISPATCH n=1002 x2=appFw+17b9e4c
FX6_DISPATCH n=1003 x2=appFw+17b9f1c
(no further dispatch)
```

So the blocking handler is:

```text
appFw+0x17b9f1c
```

Disassembly shows calls:

```text
14de79c
c56fdc
14de788
14de79c
21bdcc8
11a107c
c0cbc0
```

The handler never returns to the dispatcher. No native frame.

---

## Round 45 — 383: handler blocks before 17b9fc0

Hooks installed at:

```text
17b9fc0 -> 0x11a107c   HOOK ok, no CALL
17b9fcc -> 0xc0cbc0    HOOK ok, no CALL
```

So handler 17b9f1c blocks before either call, i.e. in its earlier subcalls:

```text
14de79c
c56fdc
14de788
14de79c
21bdcc8
```

No native frame.

---

## Round 46 — 384: 17b9f1c blocks before 17b9f98

Hook at:

```text
17b9f98 -> 0x21bdcc8  HOOK ok
no CALL
```

So the handler blocks even earlier, before 21bdcc8, in:

```text
14de79c
c56fdc
14de788
14de79c
```

No native frame.

---

## Round 47 — 385/386 (2026-11-07 12:27–12:40 PST): `17b9f1c` is not a block; the walk is 13,793 entries

Detailed reports:
[EVIDENCE-385-17B9F1C-CALLTRACE.md](EVIDENCE-385-17B9F1C-CALLTRACE.md),
[EVIDENCE-386-FINITE-MODEL-WALK.md](EVIDENCE-386-FINITE-MODEL-WALK.md).

### 47.1 Run 384 never reached the handler

`cp-bind-83784058` (384, 120 s) stopped at dispatch `n=999` — four entries before
`17b9f1c`. The Round 46 conclusion “blocks before 17b9f98” is therefore unsupported; only
`cp-bind-e250580c` (382) ever entered `n=1003`, at the very end of its window.

### 47.2 385: per-call trace inside `17b9f1c`

New CPIO `...grmreal385-17b9f-trace1.cpio`, run `cp-bind-4767b7af` (300 s), hooked every
call site in the handler and forwarded `x0..x7`:

```text
FX6_DISPATCH n=1003 off=17b9f1c
FX6_17B9F44_CALL a0=0x7f912d2d00 …      ; c56fdc
FX6_17B9F44_RET  r0=0x7f912d2d00
FX6_17B9F4C_CALL / RET                  ; 14de788
FX6_17B9F54_CALL / RET                  ; 14de79c
FX6_17B9F70_CALL / RET                  ; 14de79c
FX6_17B9F98_CALL a0=(nil) …             ; 21bdcc8
FX6_17B9F98_RET  r0=(nil)
FX6_17B9FC0_CALL x0=0x1
APPFW_SEGV sig=11 addr=0x15 pc=…+11a107c
```

So **`c56fdc` is called from `17b9f1c` and returns normally** (the handoff’s exact
request), as do `14de788`, `14de79c`, and `21bdcc8`.

The SIGSEGV was self-inflicted: `17b9fc0` is `add x0,x29,#0x50`, not a call. Hooking it
skipped the `add`, so `0x11a107c` received `x0=1` and faulted at `addr=0x15`. This also
invalidates the Round 45 “17b9fc0 hook, no CALL” observation: that hook was one instruction
early and would have crashed if reached.

### 47.3 386: corrected `0x17b9fc4` hook, handler returns

CPIO `...grmreal386-fc4fix.cpio`, run `cp-bind-cc9f2446` (300 s):

```text
FX6_17B9FC4_CALL / RET   ; 11a107c
FX6_17B9FCC_CALL / RET   ; c0cbc0
FX6_DISPATCH n=1004 … n=1005 … n=1006 … n=1007 … n=1008 …
```

The walk continues; no SEGV. 386 reached **3,295 dispatches in 300 s** (≈ 11/s).

### 47.4 The real cause of the “block”: a finite 13,793-entry table walk

`1537e00` runs five consecutive index loops and returns:

| Table | Entries |
|---|---|
| `0x24ea350` (+0xabd4, stride 8) | 5,498 |
| `0x24dd890` (+0xa4ac, stride 8) | 5,269 |
| `0x24e7d38` (+0x261c, stride 8) | 1,219 |
| `0x2b757f0` (+0x3328, stride 16) | 818 |
| `0x24f4000` (+0x1eec, stride 8) | 989 |
| **total** | **13,793** |

At ≈ 11 entries/s the walk needs ≈ 1,250 s. The 120–420 s windows of Rounds 27–46 covered
only 9–33 % of loop 1, so `12d8274`, `12d9fc8`, `c14dfc`, and Presenter were never reached.
The `model_mutex.cpp:59` asserts are a parallel thread, not a stalled walk.

### 47.5 Next

387 re-runs the identical 386 payload with a **2,100 s** window
(`vm-candidate-gpecap25-387-long.json`). Success criteria: `12D8274_CALL`,
`C09DE4B_RET`, `C14DFC_CALL`, `PRESENTER_CALL`, then a non-zero `0x41e001000` gpe0.
No native frame has been claimed yet.

---

## Round 48 — 387/389: walk completes at 13,793; `c56fdc` crash is a second bogus NOP

Detailed report: [EVIDENCE-387-WALK-COMPLETE.md](EVIDENCE-387-WALK-COMPLETE.md).

### 48.1 387 (run `cp-bind-54bcebde`)

The 2,100 s window reached **exactly `n=13793`** (the static sum of the five loops), then:

```text
FX6_12D8244_CALL / RET
FX6_12D8248_CALL x0=0x10 / RET
FX6_12D8260_CALL / RET
APPFW_SEGV sig=11 addr=0x18 pc=…+c56ff0
APPFW_X0=10   APPFW_X19=10
```

So the model walk is finite and completes; the post-walk constructors run. The next fault
is at `c56fdc` with `x19=0x10`.

### 48.2 Root cause: `0x12d8264` is an `add`, not a call

```text
12d8260  bl 0x10f5bf8
12d8264  add x0,x29,#0x80   ; <-- shim NOP'ed this
12d8268  bl 0xc56fdc        ; receives stale x0=0x10 -> str xzr,[x19,#8] -> addr 0x18
```

The shim both hooked and NOPed `0x12d8264`; the NOP won. This is the same class of mistake
as the `17b9fc0` hook in Round 47. The Round 19 “`c56fdc` called with a null/0x10-like
object” was this self-inflicted stale register, not an absent FX6 service.

### 48.3 Fixes

- **388** (built, not run): restore `0xc09e48` GRM trigger-callback registration and
  `0xc09e50`; add a late GPE capture at `seconds-90`.
- **389** (running): 388 **+** restore the `0x12d8264` `add` and remove the bogus hook.
  Keeps `0xc56fec` and the `12d824c…` infra NOPs for now.

389 success criteria: no `c56ff0` SIGSEGV; `C09DE4B_RET`; `C14DFC_CALL/RET`;
`PRESENTER_CALL`; non-zero `gpe0-late.bin`. Only then can a native frame be claimed.

---

## Round 49 — 389/390: walk and post-walk constructors pass, then a futex wait

Detailed report: [EVIDENCE-389-POSTWALK-WAIT.md](EVIDENCE-389-POSTWALK-WAIT.md).

### 49.1 389 (`cp-bind-76d6072a`, 2,100 s, completed)

```text
FX6_DISPATCH n=13793
FX6_12D8244_CALL / RET
FX6_12D8248_CALL x0=0x10 / RET
FX6_12D8260_CALL / RET
no SIGSEGV
no C09DE4B_RET
no C14DFC_CALL / PRESENTER_CALL
```

The AppFw thread (tid 222) is then in `futex_wait_queue_me`, i.e. blocked in userspace
synchronization inside the next block (`12d8268 … 12d8554`). `c56fdc` is store-only now
because `0xc56fec` is NOPed, so the wait is in one of the following calls.

Late capture (`gpe0-late.bin`, ≈2,010 s): 2,211,840 B, **0 non-zero bytes** — still no
native frame, consistent with the thread never returning from `12d9fc8`.

### 49.2 390 (running): 34-site post-walk trace

All BL sites `0x12d8268…0x12d8554` get a per-site id (`x17`) through one shared near
trampoline page; the first `FX6_POST<id>_CALL` without a matching `RET` is the blocker.
389’s payload is otherwise unchanged (trigger restore + `0x12d8264 add` fix).

Success criteria unchanged: `C09DE4B_RET`, `C14DFC_CALL/RET`, `PRESENTER_CALL`, and a
non-zero late `gpe0`.

---

## Round 50 — 390/391: post-walk trace hits an x8-clobber in the stub

Detailed report: [EVIDENCE-390-X8-STUB.md](EVIDENCE-390-X8-STUB.md).

### 50.1 390 (`cp-bind-bb34818f`, interrupted at 1,427.6 s)

```text
FX6_12D8260_RET
FX6_POST0_CALL … 12d8268 -> c56fdc
FX6_POST0_RET
FX6_POST1_CALL … 12d8274 -> 113e8f4
APPFW_SEGV pc=appFw+0x113e918 addr=0x7f670778f4
```

`113e8f4` begins `mov x19,x8`; the caller sets `x8=x19` at `12d8270` as a struct-return
buffer. The 390 trace stub was an ordinary C function and clobbered x8 across `dprintf`,
so the real `113e8f4` stored through a bad pointer. This is instrumentation-induced;
389 (no such hook) passed `12d8274` and blocked later in a futex. It is **not** the
native blocker.

### 50.2 391 (running): naked assembly stub

`fx6_post_stub.c` now saves `x0..x9` and `x17`, logs, restores `x0..x8`, calls the real
target, logs the return, and returns to `slot+4`. Trampolines are unchanged
(`ldr x16,#12; movz w17,#id; br x16`). 391 re-runs the same payload with the late GPE
capture.

Expected: the first `FX6_POST<id>_CALL` without `RET` is the real post-walk blocking call.
Success criteria remain `C09DE4B_RET`, `C14DFC_CALL/RET`, `PRESENTER_CALL`, non-zero late
`gpe0`.

---

## Round 51 — 391/392: all 34 post-walk calls return; block moves into the `12d9fc8` tail

Detailed report: [EVIDENCE-391-POSTWALK-COMPLETE.md](EVIDENCE-391-POSTWALK-COMPLETE.md).

### 51.1 391 (`cp-bind-6c605426`, interrupted at 1,396.7 s)

```text
FX6_POST0_CALL … POST0_RET
FX6_POST1_CALL … POST1_RET     ; the call that crashed 390's C stub
…
FX6_POST33_CALL … POST33_RET
(no C09DE4B_RET / C14DFC_CALL / PRESENTER_CALL / SIGSEGV)
```

The naked stub (saves `x0..x9`, `x17`) fixed the x8 clobber; all 34 sites in
`12d8260…12d8554` return. So `12d8174` completes and returns to `12d9fc8` at `12da024`.

### 51.2 New boundary

```text
12da024  bl 0x222cf40
12da034  bl 0x21bde38
12da03c  bl 0x1ac81b4
12da044  bl 0x1acd2f4   ; model-lock release path (mutex/refcount)
12da054  ret
```

These four are untraced; 389’s AppFw thread sat in `futex_wait_queue_me`, so `1acd2f4`
(or the `1ac81b4` virtual call) is the prime suspect.

### 51.3 392 (running)

392 appends these four sites as `POST34…POST37` to the same x8-safe trampoline page. The
first `POST<id>_CALL` without `RET` is the real blocker. Late `gpe0` capture remains at
`seconds-90`.

---

## Round 52 — 392/393: `12d8174` has 382 calls; full-function trace

Detailed report: [EVIDENCE-392-FULL-EXTENT.md](EVIDENCE-392-FULL-EXTENT.md).

### 52.1 392 (`cp-bind-47c51739`, interrupted at 1,862 s)

```text
FX6_DISPATCH n=13793
FX6_POST0 … POST33   all CALL/RET
(no POST34…37)
(no C09DE4B_RET / C14DFC / PRESENTER / SIGSEGV)
```

`12d8554` is not near the end of `12d8174`. Static count: the function runs from
`0x12d8174` to its first `ret` at `0x12d9e14` and contains **382 BL sites**. The 389 futex
wait is inside this body, not in the `12d9fc8` tail.

### 52.2 393 (running)

All 382 sites are traced with the x8-safe naked stub: one 0x2000 trampoline page,
20 bytes/site, `g_post_real[512]`. The first `POST<id>_CALL` without `RET` is the real
blocking call. Late `gpe0` capture at `seconds-90`.

---

## Round 53 — 393/394: `12d9de8 → 1acd874` is the model-lock condition wait

Detailed report: [EVIDENCE-393-MODEL-LOCK-WAIT.md](EVIDENCE-393-MODEL-LOCK-WAIT.md).

### 53.1 393 (`cp-bind-14949ca1`, interrupted at 1,866.8 s)

```text
FX6_DISPATCH n=13793
FX6_POST0 … POST378   all CALL/RET
FX6_POST379_CALL a0=0x7fa05dcfa0 a1=(nil)
(no POST379_RET)
(no POST380/381, no C09DE4B_RET / C14DFC / PRESENTER)
```

Site 379 = `0x12d9de8 → 0x1acd874`. That function initializes a model-lock guard,
looks up the lock record, checks `[record+0x30]` (refcount), and calls the GOT-resolved
`pthread_cond_wait` (`b19e30`); the matching signal is `b193d0`. The global owner is
`0x5a3b7a0`; mismatch hits the `model_mutex.cpp:104` assert. The AppFw thread waits
forever because nothing signals that condition in this environment.

### 53.2 Likely cause: the `c56fec` NOP removed the lock initializer

`c56fdc` calls `1acd618` at `c56fec`; `1acd618` initializes the same guard/record/owner
machinery. The shim has NOPed `c56fec` since 349 to dodge a crash that was actually caused
by the bogus `0x12d8264` NOP (stale `x0=0x10`). With `0x12d8264` restored in 389, the
original reason for NOPing `c56fec` is gone.

### 53.3 394 (running)

394 restores the real `c56fec → 1acd618` call and keeps the 382-site trace. If
`POST379_RET` appears, the lock state was the artifact; the run should then reach
`C09DE4B_RET` / `C14DFC` / `PRESENTER`. Late `gpe0` capture at `seconds-90` will decide
whether a native frame exists.

---

## Round 54 — 395/396/397/398: **native presenter reached**; no painted frame yet

Detailed report: [EVIDENCE-395-PRESENTER-REACHED.md](EVIDENCE-395-PRESENTER-REACHED.md).

### 54.1 394: c56fec restore speeds the walk 24 min → ~30 s

`cp-bind-29fa50d2`: the 13,793-entry walk now finishes in **about 30 seconds** instead of
~24 minutes. The model-lock wait at `1acd874` remains, so 394 still stalls at `POST379`.

### 54.2 395: skipping exactly `12d9de8` unlocks the whole path

`cp-bind-13932101` NOPs only the one `12d9de8 → 1acd874` call. Result:

```text
FX6_POST378_RET
FX6_POST380_CALL / RET
FX6_POST381_CALL / RET
FX6_C09DE4B_RET            <-- 12d9fc8 returns
FX6_C14DFC_CALL / RET
FX6_PRESENTER_CALL        <-- c0a860 -> 0x1397450
```

New native threads: `RemotePresenter` (241), `uipc_proxy_3` (242), `AppDebug` (243),
`BackupProxy` (244), `I-InputEvent` (245/246). The shim’s GRM path builds a real
1024×540 framebuffer (`FX6_GRM_FB_MINIMAL` / `FX6_GRM_FB_SET_SIZE`) and the FBRM trigger
callback fires (`FX6_GRM_FBRM_CB_FIRE … 1024x540 fmt=2`).

### 54.3 396: presenter body completes

`cp-bind-6849dc94`: all eight call sites of `0x1397450` (`POST382…POST389`, including the
presenter construction at `1395c3c`) return. The presenter stub does not log a RET by
design, so this is the strongest available proof that the presenter body finished.

### 54.4 397/398: the remaining gap is an event, not a code path

- 397 hooked `c0a86c → df91e8` and crashed at `+0xde3a74` (`x0=-1`); 395/396 ran the same
  code without a SEGV, so this is a trace-stub perturbation. Not used again.
- 398 moved menu-key injection to 90 s; it failed with
  `FileNotFoundError` (the `InputGate` file is absent) and no `FX3_KEY96_*` marker
  appears. The shim mailbox is only polled from `flush_pixels_to_osd()`, which is inactive
  on the native path.
- AppFw (tid 222) sits in `osal_rcv_msg_tmo` — a healthy IPC receive loop — not a crash.
- `gpe0` at 50 s and at `seconds-90` remains **all zero**.

```text
real presenter constructed:  yes
native UI threads:           yes
1024x540 GRM framebuffer:    yes
FBRM trigger callback:       fired
pixels in 0x41e001000:       none
```

### 54.5 Next lever

The UI is idle waiting for an OSAL/IPC event or a GRM screen-update job. The next work is
to identify that message/wakeup (e.g., a native input event through `I-InputEvent`, or a
`GRM_fbrmUpdate`/screen-update job) rather than patching more init calls. All source,
manifests, and serials for 385–398 are in
`work/fx6-385-17b9f-calltrace-20261107/`, with the CPIO/shim candidates in the donor
harness directory.


---

## Round 47 — 386: c56fdc no-op preserves LR but breaks later state

386 patched c56fdc entry with `B -> trampoline -> C no-op` (preserves caller LR).

Result:

```text
FX6_C56_NOOP_B x0=0x...
APPFW_SEGV addr=0x400001efe
PC/LR appFw
```

So the no-op is reached, but c56fdc's body is required by later code; skipping it causes a new
crash. The handler still does not reach c14dfc.

No native frame.

---

## Round 48 — 387: c56fdc calls model_lock constructor

Disassembly of 0x1acd618 (called from c56fdc+0x10) shows it loads:

```text
1acd61c adrp x0,0x5a3b000
1acd620 add  x0,x0,#0x7a8
...
1acd670 ldr  x0,[x21,#0x7a0]   ; model lock owner
1acd674 cbz  x0,...
1acd678 ldr  x23,[x29,#0x58]
1acd67c cmp  x0,x23
...
```

So c56fdc is a **model_lock acquire/construct helper**, and 1acd618 is the model-lock
constructor/lock path. The model_mutex asserts and the c56fdc block are the same lock-ownership
problem, not unrelated.

No native frame.

---

## Round 49 — 388: model-lock bypass does not unlock progress

388 patched 1acd680 to branch directly to the same-thread success path, bypassing the owner wait.

Result:

```text
FX6_MODEL_LOCK_BYPASS 1
9 ScreenAreas
FX6_C09DE4B_RET 0
FX6_C14DFC_CALL 0
FX6_PRESENTER_CALL 0
assert at model_mutex 3
```

So simply bypassing the lock owner wait does not let c09de4 finish; the model lock/queue
protocol is still inconsistent. No native frame/settings screen.
