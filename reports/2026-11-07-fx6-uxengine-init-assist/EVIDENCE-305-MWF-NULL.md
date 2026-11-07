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
