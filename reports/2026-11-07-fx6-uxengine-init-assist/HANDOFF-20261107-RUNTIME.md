# Runtime handoff — 2026-11-07 late session (DeepSeek, inherited from `term_22969527`)

## 0. TL;DR

- The old terminal stopped at candidate 384 (`blocked` since 11:45 PST). This line resumed
  with new run ids 385–398 and never overwrote an existing candidate, run dir, or report.
- **Corrections to the inherited picture:** the “`17b9f1c` / `c09de4` block” was not a
  block. It was a **finite 13,793-entry model-table walk** (~24 min under TCG at first),
  and two later “crashes” were **mis-addressed NOPs/hooks** (`0x17b9fc0`, `0x12d8264`,
  plus the `c56fec` cleanup) that produced stale registers.
- **New milestone:** the real FX6 presenter path is now reached on the FX3 VM:
  `C09DE4B_RET → C14DFC_CALL/RET → PRESENTER_CALL`, with native `RemotePresenter`,
  `I-InputEvent`, `BackupProxy` threads and a real **1024×540 GRM framebuffer**.
- **Still not achieved:** a painted native frame. `0x41e001000` gpe0 is all zero at 50 s
  and at the late capture. The UI thread sits in `osal_rcv_msg_tmo` waiting for an
  OSAL/IPC event or screen-update job. That is the next lever.

## 1. Chronology of the runtime line

| Candidate | Run | Change | Result |
|---|---|---|---|
| 385 | `cp-bind-4767b7af` | per-call trace inside `17b9f1c` (`x0..x7`) | `c56fdc` called/returns; `21bdcc8` returns; old `17b9fc0` hook crashed at `11a107c` (mis-addressed) |
| 386 | `cp-bind-cc9f2446` | hook moved to real `17b9fc4` | `17b9f1c` returns; dispatcher continues past `n=1003`; 3,295 entries in 300 s |
| 387 | `cp-bind-54bcebde` | 2,100 s window | walk completes at exactly `n=13793`; crash at `c56ff0` from bogus `12d8264` NOP |
| 388 | built, not run | restore `c09e48`/`c09e50` | superseded by 389 |
| 389 | `cp-bind-76d6072a` | restore `12d8264 add` + trigger | walk + `12D8244/48/60` pass; AppFw blocks in `futex_wait_queue_me`; no frame |
| 390 | `cp-bind-bb34818f` | 34-site post-walk trace | `POST1` crash was C-stub x8 clobber (instrumentation) |
| 391 | `cp-bind-6c605426` | naked x8-safe stub | all 34 post-walk calls return; block is later in `12d8174` |
| 392 | `cp-bind-47c51739` | 4 tail sites | not reached: `12d8174` has 382 BL sites, not 34 |
| 393 | `cp-bind-14949ca1` | all 382 sites | `POST379 = 12d9de8 → 1acd874` never returns (model-lock `pthread_cond_wait`) |
| 394 | `cp-bind-29fa50d2` | restore `c56fec → 1acd618` | walk drops 24 min → **~30 s**; lock wait persists |
| **395** | **`cp-bind-13932101`** | **NOP only `12d9de8`** | **`C09DE4B_RET` + `C14DFC` + `PRESENTER_CALL`; native threads + 1024×540 framebuffer; no paint** |
| 396 | `cp-bind-6849dc94` | trace `0x1397450` sub-calls | all 8 return (presenter body completes) |
| 397 | `cp-bind-73b7f61d` | trace `c0a86c` | crashed at `de3a74`; trace-stub perturbation, not native |
| 398 | `cp-bind-0bd36667` | late MENU key at 90 s | `InputGate` file missing; no key reaches guest; still no frame |

## 2. Key technical findings

### 2.1 The long “block” is a finite walk

`1537e00` runs five index loops: 5,498 + 5,269 + 1,219 + 818 + 989 = **13,793**
dispatches into the model table at `0x2b78b10`. The bound is constant; there is no
recursive dispatcher call. Earlier 120–420 s windows only covered 9–33 % of loop 1.

### 2.2 Two bogus NOPs/hooks

- `0x17b9fc0` is `add x0,x29,#0x50`, not a call. Hooking it skipped the `add`, so
  `0x11a107c` got `x0=1` and crashed (`addr=0x15`).
- `0x12d8264` is `add x0,x29,#0x80`, not a call. NOPing it left `x0=0x10` for
  `0x12d8268 bl c56fdc`, which stored to `0x18` and crashed.

### 2.3 The `c56fec` cleanup cost 24 minutes

`c56fdc` calls `1acd618` (model-lock init) at `c56fec`. It was NOPed in 349 to dodge the
second crash above. Restoring it in 394 collapsed the walk from ~24 min to ~30 s (lock
contention/assert overhead gone).

### 2.4 The last post-walk blocker

`12d9de8 → 1acd874` is a model-lock condition wait (`pthread_cond_wait` via GOT
`b19e30`, signal `b193d0`, global owner `0x5a3b7a0`, assert `model_mutex.cpp:104`).
Nothing in this VM signals that condition. Skipping only this call lets `12d8174` return
and unlocks `c09de4 → c14dfc → presenter`.

### 2.5 Presenter is real, output is not connected

After `PRESENTER_CALL` (`0xc0a860 → 0x1397450`):

```text
RemotePresenter, uipc_proxy_3, AppDebug, BackupProxy, I-InputEvent ×2
FX6_GRM_FB_MINIMAL ... fb=... vptr=...
FX6_GRM_FB_SET_SIZE self=... w=1024 h=540
FX6_GRM_FBRM_CB_FIRE cb=... (1024x540 fmt=2)
FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0
```

Then AppFw (tid 222) idles in `osal_rcv_msg_tmo`. No pixels reach
`0x41e001000`, `0x429550000`, or `0x4805a1000`.

## 3. Exact next steps

1. **Find the wakeup/event.** The UI is not crashed; it is waiting for an OSAL message or
   a GRM screen-update job. Trace the `osal_rcv_msg_tmo` caller / message table, or the
   `GRM_fbrmUpdate` path, and synthesize the expected message.
2. **Do not trust an apparent absence of a call unless the run reached the site.** 383/384
   “no 17B9F98 CALL” was a timeout at `n=999`; 390/397 “crashes” were probe artifacts.
3. **Keep x8/x9 in any call-site stub.** `0x113e8f4` and other functions take struct
   return buffers in x8; a C stub clobbers it.
4. **Watch NOP addresses.** Before NOPing a `bl`, disassemble the exact address; the
   project has now hit this twice (`17b9fc0`, `12d8264`).

## 4. Repro pointers

- Harness: `/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/`
- Candidates: `guest-hybrid-fx6kernel-capid-grmreal385…398*.cpio` + matching
  `vm-candidate-gpecap25-*.json` and `run_gpecap25_*.py`.
- Durable small artifacts and serials:
  `/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/work/fx6-385-17b9f-calltrace-20261107/`
- Reports: `EVIDENCE-385…395` in `reports/2026-11-07-fx6-uxengine-init-assist/`, plus the
  cumulative `EVIDENCE-305-MWF-NULL.md` Rounds 47–54.

## 5. Scope / safety notes

- Only research and VM experiments; no physical camera flashing, no file deletion, no
  work-tree removal.
- No external push was performed by this line (per the “不对外发布” constraint); the
  reports and work artifacts are left in the repo for the next shell-enabled line to sync.
- No other agent was writing during this session; the last inherited write was 384 at
  11:45 PST, and all new artifacts use fresh 385–398 ids.

## 6. 2026-11-07 16:20 PST update — 396/397/398 reports filed; next lever is OSAL

Dedicated reports now exist:

- [EVIDENCE-396-PRESENTER-BODY.md](EVIDENCE-396-PRESENTER-BODY.md): all eight sub-calls
  of the presenter `0x1397450` return; the presenter body is complete.
- [EVIDENCE-397-UI-TRACE-PERTURB.md](EVIDENCE-397-UI-TRACE-PERTURB.md): the first
  post-presenter trace (`c0a86c → df91e8`) crashes only when the dprintf trace is added;
  395/396 run the same path without a SEGV. Do not naively trace the fragile UI init.
- [EVIDENCE-398-LATEKEY-FAIL.md](EVIDENCE-398-LATEKEY-FAIL.md): the 90 s MENU injection
  fails with `FileNotFoundError`; the shim key mailbox is only polled from
  `flush_pixels_to_osd()`, which is inactive on the native path. Keys cannot wake the
  native UI.

**Next lever:** interpose the OSAL message API inside the guest
(`osal_snd_msg`, `osal_rcv_msg_tmo`, `osal_reg_msg_queue_cb`,
`osal_valloc_msg_wait`) to learn the UI queue ID and message format, then synthesize a
screen-update message to the AppFw event loop. The GRM side (`GRM_fbrmUpdate`) is the
alternative if the OSAL queue turns out to be display-service-internal.

## 7. 2026-11-07 17:00 PST update — OSAL/UIPc table mapped; injection works; no draw

Full report: [EVIDENCE-399-414-OSAL-EVENT-INJECTION.md](EVIDENCE-399-414-OSAL-EVENT-INJECTION.md).

- **Message table mapped:**
  - `0x81cf6110` (`0x6110`): one init event `20 80 …` at `appFw+0x21278a8`.
  - `0x5503e0` (`0x3e0`): 7 display/status events (`55 03`×4, `94 00`×2, `8e 00`×1),
    drained with `tmo=0` after presenter.
  - **`0x807e0030`**: the real idle receive queue (`tmo=0xffffffff`) after presenter.
- **Raw send to these qids fails:** `osal_snd_msg`/`u_osal_snd_msg` return -512; valloc
  returns -506. Only local `0x8f0139` valloc/snd works. The qid is a **UIPc remote queue**
  handled by `uipc_proxy_3`/`/dev/uipc`; Dataflow is not used by the UI.
- **Boundary injection proven:** interposing `osal_rcv_msg_tmo`, allocating a real message
  via `u_osal_valloc_msg_wait(0x8f0139)`, and returning it for `0x807e0030` is accepted by
  the UI (`FX6_INJECT3 slot=…`, `inj=1`).
- **But payloads do not draw:** injecting the `20 80` event or the `55 03`/`94 00`/`8e 00`
  events causes no GRM/OSD activity; `gpe0-late` is still all zero. Removing the shim’s
  destructive OSD copy (400) and re-firing the GRM framebuffer callback (406) also do not
  paint.
- **Next:** decode the `appFw+0x21278a8` handler’s dispatch (`msg+2`, `msg+0xc`,
  `msg+0x18`, `msg+0x20`) to enumerate the real screen-update event id/format, then inject
  that event at the same boundary; or reverse the UIPc proxy send path.

The goal remains **active**: no native frame has been claimed; `0x41e001000` is still zero.

## 8. 2026-11-07 17:10 PST update — `0x807e0030` is a request/reply wait

- The helper at `appFw+0x2127750` builds a request (`[msg]=0x20`, `[msg+4]=request id`,
  `[msg+0x16]=param`), sends to qid `0x9061`/`0x61`, then waits on `0x807e0030` with
  `tmo=0xffffffff`; the reply handler copies `[reply+0xc]`, `[reply+0x18]`,
  `[reply+0x20]` into the caller’s out object.
- 415 injected one zero reply: accepted; AppFw returned to `osal_rcv_msg_tmo`.
- 416 answered every wait with a zero reply: the UI performed **10** request/reply cycles,
  then stopped. No GRM/OSD activity, `gpe0-late` still zero.
- **Parallel-line warning:** the old terminal woke up and wrote `...386-c56noopb.cpio`,
  a new `run_gpecap25_386.py`/`vm-candidate-gpecap25-386.json`, and is running
  `...388-lockbypass.cpio` (QEMU PID 34404). An orphan from their 386 run held the VM lock
  and was killed so 416 could rerun; their active 388 run is left untouched. New work uses
  ids ≥ 417 and waits for the shared lock. Cite CPIO filename + run id, not just number.
- **Next:** capture the request id/param via `osal_snd_msg` interposition and answer with a
  matching non-zero reply, then re-check `gpe0`.

## 9. 2026-11-07 17:20 PST update — request `0x696` captured; matched reply still no frame

- The helper send at `0xb1a120` is `osal_snd_msg` (GOT `0x2ef2998` → symbol). Filtering
  sends to `q & 0xffff == 0x003c` captured the request:
  `FX6_REQ q=61003c type=20 id=696 par=10000`.
- 419/421 answered it with `[0]=0x20`, `[2]=0`, `[0xc]=1` (`FX6_REPLY_MATCH last=696
  flag=1`). The UI still does **10** request/reply cycles, then enters a futex wait;
  `gpe0-late` stays all zero. The reply status does not change the cycle count.
- 421 also applied the parallel line’s `0x1acd680 → b 0x1acd780` model-lock bypass
  independently (`FX6_MODEL_LOCK_BYPASS2`). The 10 cycles still occur, then
  `model_mutex.cpp:59/64/75` asserts and a futex wait; no GRM/OSD draw.
- Parallel line’s `388-lockbypass` run (`cp-bind-32fec9e9`) ended with `wall_timeout`
  180 s and `CP_RC0_OBSERVED_NOT_AP`; its active QEMU was not touched.
- **Next:** observe the post-10-cycle caller of the `0x1395f20`/`0x1395f90` request loop
  and the model-lock sites it then hits (`1acd618`, `1acd2f4`, `1acd6c0`, `1acd874`);
  inject/reply there before checking `gpe0` again.

The goal remains **active**: `0x41e001000` is still zero; no native frame claimed.

## 10. 2026-11-07 17:22 PST update — 10-cycle loop is reply-independent; wait predates the patch

- 422 answered `0x696` with the param `0x10000` echoed into all three reply fields
  (`out+4/out+8/out+0x10`): exactly the same **10** request/reply cycles, then the same
  `FX6_COND_WAIT ... off1=1acd6c0` for tids 222/228. The loop count is fixed, not
  reply-driven.
- The `1acd680` bypass should skip the non-null owner-mismatch wait; seeing
  `ra1=1acd6c0` means the thread was already inside `pthread_cond_wait` **before** the
  patch was applied (the model lock is used during early AppFw init, before the
  `Application_System_Init` hook).
- Next: install the `1acd680` branch earlier (shim constructor or first PLT hit), or
  interpose `model_lock::model_lock` (`1acd618`/`1acd2f4`) and return a consistent
  already-owned state; identify the owner `[x21+0x7a0]` at the first `1acd6c0` wait.
- 422 run: `cp-bind-1e14a688` (`wall_timeout` 120 s, `CP_RC0_OBSERVED_NOT_AP`).
- 423: constructor `dl_iterate_phdr` found `appFw.so` not yet mapped (`base=0`), so the
  early patch was a no-op; the later `Application_System_Init` patch applied. This run
  showed **no** `1acd6c0` cond wait — tid 222 went to `hrtimer_nanosleep`/futex after the
  10 cycles. Still no draw; `gpe0` zero. The permanent lock wait is replaced by a timer
  poll (timing dependent).
- Next: 300 s run with request logging to capture at least one post-sleep poll, and vary
  `out+8`/`out+0x10` (currently zero) in the `0x696` reply. 423 run:
  `cp-bind-52bf0b79` (`wall_timeout` 120 s, `CP_RC0_OBSERVED_NOT_AP`).
- **423b (300 s)**: exactly the same **10** replies; no post-sleep request repeat. After
  the 10th cycle AppFw tid 222 is in `futex_wait_queue_me`; other threads sit in
  `FX6_COND_TIMEDWAIT ... off1=1c1e040` (timer loop). `gpe0-late` zero, run
  `cp-bind-e5cb052f` (`wall_timeout` 300.17 s). Conclusion: the `0x696` handshake is
  one-time, not a poll. Next lever: identify the post-cycle futex owner/waiter
  (`pthread_mutex_lock`/`sem_wait` interposition) or invoke the presenter/GRM update path
  directly.
- **425**: interposed `GRM_screenIsDirty`/`GRM_screenGetOnBitmap`; zero calls in 120 s —
  the UI in this state does not query those GRM screen functions. Forcing `dirty=1` is not
  the lever. Run `cp-bind-e9f906a4`.
- **426**: resolved the post-cycle mutex waiters:
  `tid=222 m=0x… ra=appFw+0xc1525c`, `tid=225/226/227 m=0x… ra=appFw+0xc096ec`. Both are
  **trylock spin loops** (`bl b199d0` → on failure `bl b176e0` yield/sleep → retry), not
  condvars. The mutex holders are not yet identified; `gpe0` zero. Run
  `cp-bind-142202a1`.
- Next: read the mutex owner field / futex word (or make `pthread_mutex_trylock` return
  the owner tid), then either unblock the holder or bypass the specific trylock at
  `0xc1521c`/`0xc096d4`.
- **427**: mutex fields show AppFw 222 blocked on `m=0x… lock=2 owner=228` at
  `appFw+0xc1525c` — the holder is tid 228 (presenter/framebuffer). Run
  `cp-bind-4d03be46`.
- **428/429**: broadcast tid 228’s cond (`appFw+0xde3060`); it wakes but re-waits
  (predicate false), even after setting `obj+0x78`. Runs `cp-bind-2466a835`,
  `cp-bind-046f5b5f`.
- **430**: patched the predicate check `appFw+0xde304c` to `mov w0,#1`
  (`FX6_PRED_PATCH`). Result: no `tid=228` cond wait, no post-cycle mutex waiters; AppFw
  222 now goes to `hrtimer_nanosleep`. Deadlock broken, still no draw; `gpe0` zero. Run
  `cp-bind-eee4ef78`.
- Next: instrument `nanosleep`/`clock_nanosleep` duration and the wake handler; or supply
  the display-ready condition the presenter waits for.
- **431**: `nanosleep`/`clock_nanosleep` probe saw no calls; 222 later back in futex. Run
  `cp-bind-2870a7b4`.
- **432**: with the predicate patch, 222 still waits on `owner=228`; tid 228 is
  **`RemotePresenter`**, sleeping in `hrtimer_nanosleep` while holding the mutex. Run
  `cp-bind-7de2e0c8`.
- **433**: RemotePresenter polls every **100 ms** via `usleep`
  (`FX6_SKIP usleep tid=228 usec=100000`). Skipping it released the mutex and moved 222 to
  `hrtimer_nanosleep`; still no `GRM_fbrmUpdate`/`swap`/`gpermFlush`, no draw, `gpe0`
  zero. Run `cp-bind-a1e06f3a`.
- Next: trace the 228 100 ms loop body (what it checks / which GRM call it would make) or
  deliver the frame/display event that makes it call `GRM_fbrmUpdate`.
- **434**: `pthread_create` interposition saw only **4** calls in 120 s; RemotePresenter
  and the SeqQueue/IWrapper threads are created via `lib::create_thread`/clone, not the
  exported `pthread_create`. Arg words are thread ids, not name pointers. Run
  `cp-bind-bfb1d07d`.
- Parallel line now runs `...grmreal391-owner.cpio` (its own number), also probing mutex
  owners; its active QEMU was not touched.
- **435**: all `osal_rcv_msg_tmo` queues mapped — tid 230 `0x5503df`, tid 232 `0x7ae01e`,
  tid 233 (I-InputEvent) **`0x7ae01d`**, tid 222 `0x5503e0`/`0x81cf6110`/`0x807e0030`.
  Run `cp-bind-c480255c`.
- **436**: input receive caller is `libInfraInput.so+0x78b4`; after receive it copies
  **0x20 bytes** to an event struct, frees the message, matches `event[0]` against a
  0x50-stride key table at `+4`, then calls the input callback. Run `cp-bind-c2c0056f`.
- **437**: injected a 0x20-byte event at `q=0x7ae01d` with key `0x1ab`; allocation and
  delivery succeeded (`FX6_INPUT_INJECT`), but no GRM/OSD activity, `gpe0` zero. Run
  `cp-bind-ab5e6196`.
- Next: inject key sequences (`0x1ab`, `0x30`, `0x1ac`, `0x1af`) with press/release, and/or
  inspect the `0x5250` callback target / key-config table to recover the event layout.
- **438**: injected an 8-event press/release sequence (`1ab/30/1ac/1af`) at `q=0x7ae01d`;
  all accepted (`FX6_INPUT_SEQ`), but AppFw stayed in `hrtimer_nanosleep`, no GRM/OSD,
  `gpe0` zero. Run `cp-bind-15b5e898`.
- **Why keys may be ignored**: `libInfraInput` `KeyConfigInital` (`0xb284`) loads the key
  table from qid **`0x7a0001`** (`0x51a0` size → `0x5520` alloc → `0x5320` receive). No
  receiver for `0x7a0001` appears in the observed queue list, so the table is likely
  empty. Next: reverse that request format and inject a synthetic key-config table, or
  find the config blob in the firmware; alternatively synthesize a screen-update event.


## 11. 2026-11-07 18:37 PST — WidgetSystem direct-drive results (440–447)

- `sys_getInstance()` works; `updateFrame/notifyDraw/processEvent` all return.
- `ws+0x8a0` (animating) and `ws+0x8a4` (draw-notice) can be set; `updateFrame` keeps
  `+0x8a0=1`, `notifyDraw` consumes `+0x8a4` to 0 — but no GRM/OSD draw (`prims=0`).
- The existing `LayerBase` at `ws+0x7c0` is valid and `isActive=1`; its widget tree is
  empty/unattached. `createLayer(0xd/0x3f)` returns a new layer but does not change
  `ws+0x7c0/+0x7c8`.
- `df91e8(presenter_x0+0xa40)` **SEGVs at pc=0** — presenter x0 is not the `ui_obj`
  used by `c0a86c`.
- RemotePresenter draw branch: setting `obj+0x79=1` and `*(engine+0x8af80)=1` is writable
  and does not crash, but no GRM/OSD follows.
- Scanning `41e/429/480` after update shows only the shim magic (`41e nz=2`); `429/480=0`.
- Next: attach a real layer/screen to `ws+0x7c0` (or `GraphicsEngine::createScreen`
  menu ID), then intercept all GRM entry points to find the pixel landing.

Runs: 440 `cp-bind-d721e494`, 441 `cp-bind-188b1280`, 442 `cp-bind-d74a4e49`,
443 `cp-bind-e3dca14a`, 444 `cp-bind-ef5b4e9e`, 445 `cp-bind-e6d9d922`,
446 `cp-bind-343c0eda`, 447 `cp-bind-021235f4`.

- **448**: `GraphicsEngine::sys_getInstance()` = `0x7f9c00c010`; `sys_update()` and
  `sys_render(full rect)` run (engine calls `getOffscreen` repeatedly, `prims=0`), then
  `drawFramebuffer()` **SEGV at pc=0x7fb58e0f70 addr=0x48** (libuxengine). No pixels.
  Run `cp-bind-64f4afdf`.
- Next: create the menu screen (`GraphicsEngine::createScreen(0xd/0x3f)`) before
  `sys_render`, skip/resolve the `drawFramebuffer` crash, and intercept GRM to find the
  real pixel buffer.

- **449**: `GraphicsEngine::createScreen(ID{0xd,0x3f})` returns `0x7f900c5010`, then
  `sys_update`/`sys_render` run (10× `getOffscreen`, `prims=0`), no SEGV; `41e/429/480`
  still zero. The screen is empty: the engine path is reachable, but no widget tree is
  attached.
- Next: `Screen::getRootNode()` check, activate via `ScreenBase::moveFirst/moveLast`, or use
  the real `ui_obj`/presenter screen manager instead of `createScreen` alone; then intercept
  `ScenegraphWindow::renderScreen/renderInternal`.

- **450/451**: `createScreen(0xd/0x3f)` and `(0xb/0x1d)` return valid screens with a non-null
  root (`0x7f940c5038`), `moveFirst/moveLast`/`sys_update/sys_render` all OK, but no
  primitives and `41e/429/480` zero — the screen has no `view_*` children.
- **452**: setting `engine+0x32a=1` + full dirty rect then `drawFramebuffer()` still
  **SEGV addr=0x48 pc=0x7f87273f70** inside the commit path.
- **ui_obj**: static chain `c09da0 <- c0a6cc <- c0a69c <- c0b528`, and `c0b4c8 add
  x19,x29,#0x28` shows the UI object is a **stack object**. Next: inline-hook
  `appFw+0xc0a69c` to capture `x0`, then call `df91e8(ui_obj+0xa40)`.
- Runs 450 `cp-bind-bea5c7ad`, 451 `cp-bind-4efbda30`, 452 `cp-bind-6420f505`.

- **453–455**: direct `BL` hook was out of range; a `.bss` trampoline at
  `appFw+0x6117800` redirected `c0b528` and captured the real
  `ui=0x7fa4184658`. 454: `df91e8(ui+0xa40)` **returned**, no pixels. 455: same call
  **SEGV addr=0x1c8 pc=0x7f677bc614** before returning — timing/state sensitive.
- Next: stabilize `df91e8` (retry 454 recipe, disassemble `+0x1c8` crash), then engine
  `sys_render`/`drawFramebuffer` and scan.
- Runs: 453 `cp-bind-39df9177`, 454 `cp-bind-45bba971`, 455 `cp-bind-fa327330`.

- **456**: repeat 454-only; `ui=0x7f8bb1f658`, `df91e8` returned, scan 41e nz=2 — df91e8
  returned in 2/3 runs (455 crashed at +0x1c8).
- **457**: df91e8 + `sys_update`/`sys_render` only; 9× `getOffscreen`, `prims=0`, scan
  unchanged. df91e8 does not populate a drawable `view_*` tree; the engine walks nothing.
- Next: call the `procam_*_presenter`/screen factory with the captured `ui_obj`, and
  intercept `ScenegraphWindow::renderScreen` + all GRM entry points.
- Runs: 456 `cp-bind-f95986a6`, 457 `cp-bind-d92b2940`.

- **458**: UI creates **18 screens** during init (IDs `0x8001xxxx`), but `renderScreen` is
  not called externally; `df91e8` crashes at `appFw+0xcbd614` (`ldr x2,[x0,#0x1c8]`) — an
  interface table missing the `+0x1c8` slot. Run `cp-bind-9eed01f3`.
- **459**: 9 captured screens, each `moveFirst` + engine `sys_update/sys_render`; all
  `prims=0`, scan zero. Screens exist but contain no drawable view tree. Run
  `cp-bind-c7ad4485`.
- Next: invoke the `procam_big6_menu_setting`/`procm_*_presenter` create/enter function with
  the captured `ui_obj`; instrument view constructors; or fill the missing `+0x1c8`
  interface slot.

- **460**: every UI-created screen ID resolves via `WidgetSystem::getLayerBase`; 8 layers
  are empty, but `id=8001653f` has a real widget (`0x7f6e65f700`). Run
  `cp-bind-f9d205cf`.
- **461**: `moveFirst` that layer + `ws+0x8a0/+0x8a4=1` + update/notify; still `prims=0`,
  scan zero. The widget exists but is gated/container. Run `cp-bind-b3049368`.
- Next: widget vtable/RTTI, visibility/dirty flags, enumerate child widgets, then direct
  draw / GRM interception.

- **463**: first real widget dumped: `layer id=8001653f`, `widget=0x7f6a98f700`,
  `vt=0x7f6a66b490`, `ti=0x7f79df9680`, `+0x48=0x863f5760` (matches screen ID 0).
  RTTI name read failed; no draw. Run `cp-bind-a2ef0320`.
- Next: resolve vtable/typeinfo module+offset, map vtable slots to visibility/draw, enumerate
  children, and call draw / intercept GRM.

- **464**: widget vtable = `appFw+0x2d1b490`, typeinfo name **`9view_fill`**; vt[0]/vt[1]
  dtors, vt[2]=libuxengine+0xa3220 (`return 0`), vt[3]=libuxengine+0xa1d00. Run
  `cp-bind-57330609`.
- **465**: patched vt[2] (`a3220`) to `mov w0,#1; ret`; moveFirst + update/notify still
  `prims=0`. So vt[2] is not the paint gate; view_fill likely has zero-size/transparent
  params. Run `cp-bind-cb65c258`.
- Next: read `view_fill::param_t` (widget `+0x58`/`+0x210`) for rect/color/visibility, call
  vt[3] (`libuxengine+0xa1d00`) directly.

- **466**: `view_fill` param dump: `ptr58=0x…e9b0`, `+0x210` is a member object with vtable
  `0x…f000`, `+0x18` pointer, `+0x30=1`; no direct `{x,y,w,h,color}` visible. Run
  `cp-bind-9b9cb752`.
- Next: resolve those pointers' classes and rect/color offsets; if rect zero/transparent,
  write a 1024×540 opaque rect and call update/notify or `vt[3]`/renderInternal.

- **467**: `ptr58=libuxengine+0xbc9b0`, `p58[0]=libandromeda+0x1c6e8`, `w210+0=libuxengine+0xbd000`
  (not a vtable; vtable[-1]=0), `w210+0x18=appFw+0x303f800`. Run `cp-bind-b8cc93a3`.
- **468**: `GraphicsEngine::getWindow()`=`0x7f9800c0c0`; `renderInternal(view_fill layer)`
  returns, still `prims=0`, scan zero. The walker draws nothing. Run `cp-bind-ab1d1fd6`.
- Next: log `RenderScreenWalker::visit` node count/rect/visibility; write a valid rect if
  zero; find the skip condition.

- **469 static**: `renderInternal` (`libuxengine+0x7b4cc`) checks layer vtable slot0 bit30,
  then at `0x7b544` calls `[widget_vtable+0x10]` (vt[2]) and **returns at `0x7b554` if it
  is 0**. `view_fill` vt[2] = `libuxengine+0xa3220` (`return 0`), so this is the real paint
  gate. Candidate **469-visrender** patches `a3220 -> mov w0,#1; ret` then calls
  `renderInternal`; built/packaged but **not run** (parallel `469-preloaddraw` held the VM).
- Next: run `run_gpecap25_469_visrender.py --run --seconds 120` when the lock is free; if
  no prims, write a valid rect/color into the `view_fill` param before render.

- **470-visflush**: 469-visrender + explicit `GRM_gpermDrawFlush`/`GRM_fbrmUpdate` after
  `renderInternal`. Manifest `vm-candidate-gpecap25-470.json` (argv repaired; `--check`
  passes), CPIO `…grmreal470-visflush.cpio`, shim `libgrm-fbinit25-470.so`. Runtime blocked
  by the parallel line holding the VM lock; a retry loop is active.
- Warning: the parallel line overwrote `vm-candidate-gpecap25-468.json` with
  `grmreal468-preloaddraw`; that file is no longer this line's 468-windowrender manifest.
  Cite filenames + run ids.

- **470 lock lessons**: (a) the retry loop matched its own bash command via
  `pgrep -f qemu-gpio5` and never attempted; fix by matching the full QEMU binary path and
  excluding the shell. (b) A private-lock second VM failed with `QMP closed` and
  `libux_core.so: undefined symbol _ZN5libra13ObjectBuilderC2Ev`, and its run dir was
  reused by the parallel `grmreal472-kikidraw` — do **not** bypass the shared lock.
- 470-visflush stays packaged; retry only when the shared lock is genuinely free.

- **472 observation**: parallel `grmreal472-kikidraw` preloads a lib that after 60 s calls
  `GraphicsEngine::sys_getInstance`, sets `ge+0x32a=1`, `GraphicsSystem::setDirtyRegion`,
  then `drawFramebuffer` (same commit path as our 448/452). It still holds the lock.
- **470 retry**: now uses `pgrep -x qemu-gpio5-bf4d46481998b8fb` (exact process name) and a
  0.5 s loop; will run `run_gpecap25_470_visflush.py --run --seconds 120` as soon as the
  parallel QEMU exits.

- **470**: vt[2] patched, `renderInternal` done, but `swap #2 prims=0` and later
  `SEGV addr=0x58`. Run `cp-bind-1133636b`.
- **471**: `view_fill` param layout decoded: `+0x1e8 x`, `+0x1ec y`, `+0x1f0 w`,
  `+0x1f4 h`, `+0x1f8 color`, `+0x1fc visible`; runtime `0/0/1024/540`, color 0, visible 1.
  Set color `0xFFFF0000` + full size, still `prims=0`, same SEGV. Run `cp-bind-a1047b15`.
- Next: call `appFw+0xc27448` (view_fill slot 41 layout/apply) on the widget before
  `renderInternal`; if still no prims, hook `CmdFillrect::execute`/mpgpe to see the real
  draw path.

- **472**: `appFw+0xc27448` (view_fill slot 41 layout) applied, color/size/visible set;
  still `swap #2 prims=0`, SEGV addr=0x58. Re-reading `renderInternal`: `vt[2]` is
  `isWidget3D`; `cbz w19,0x7b524` returns for 2D, and our patch to 1 forces the **3D** path
  (wrong for view_fill). Next: restore isWidget3D=0 and drive the 2D draw-notice path
  (slot 33 `onDrawNotice`) / hook `CmdFillrect::execute`.

- **473**: 2D `notifyDraw -> updateFrame` with view_fill 1024×540/opaque: still
  `prims=0`, same late `SEGV addr=0x58`. Slot 43 (`appFw+0xc2750c`) is only a
  visibility/mode/layout function, not a draw emitter. Run `cp-bind-589de1e4`.
- Next: `.bss` trampoline on `libgrm+0x2fb6c` (`grm::CmdFillrect::execute`) to see whether
  fill commands are created/executed and where pixels land.

- **474**: CmdFillrect execute vtable slot hooked, but it is **never called**; old
  `swap #2` + `SEGV 0x58` persists. Run `cp-bind-4d297827`.
- **475**: patched `ExternalOSDIF::sendUpdate` to return; crash moved to
  `libgrm+0x25300 addr=0x8`. Disassembly shows `sendUpdate` reads `[this+0x58]` with
  `this=NULL` — the OSD present virtual is called with a null singleton. Run
  `cp-bind-a713f6b3`.
- Next: find/initialize that singleton or replace the OSD present virtual with a shim that
  flushes the GRM software bitmap; then check whether CmdFillrect executes.

- **477–479**: sendUpdate caller = `FBResourceManager::updateRequest` (LR `libgrm+0x22e6c`);
  after it, null `Semaphore::unlock`/`lock` crashes. Patching `isLocked/lock/unlock`
  (`libgrm+0x2526c/0x252b8/0x252f8`) removes the SEGV; sendUpdate is called twice with our
  fake this but **+0x58=0 takes the early-return**, so no OSD transfer and still
  `prims=0`. Runs `cp-bind-3dbf1d74`, `-52633e2b`, `-b4f3df71`.
- Next: fake `ExternalOSDIF` with valid vtable and `+0x58=1` so sendUpdate proceeds to
  sendExec/proxy; then check CmdFillrect execution/pixels.

- **480**: fake ExternalOSDIF with real vtable + `+0x58=1`: sendUpdate runs twice, no SEGV,
  but still no CmdFillrect execution/pixels. It only sends MessageNotifyOSDUpdated.
- Next: find/drive `CmdProcessorExtOSD`/`sendExec` to execute the queued fill commands, or
  fake the OSD command processor.

- **481 static**: `RenderScreenWalker::visitPost` returns without drawing when
  `walker+0x30` (draw context) is NULL (`libuxengine+0x7b01c/0x7b020`). This explains
  prims=0 in every 2D attempt. Next: find where renderInternal/renderScreen sets
  walker+0x30 and provide a non-null context (or patch the check), then re-check
  CmdFillrect/0x721d0.

- **482**: interposed `GraphicsDraw::fillRect`; it is **never called**. `renderScreen`
  loads the draw context from `window+0x234` (`libuxengine+0x7b378`); that pointer is NULL,
  matching the `walker+0x30` early-return. Next: attach a valid GraphicsDraw to
  `window+0x234` (likely `GraphicsDrawState::GetInstance()`), then fillRect/Grm fill run.

- **484/485**: `GraphicsDrawState::GetInstance(tpidr)` returns a real 0x40 object
  (`vtable`, `+8` context). Attaching either the state or `+8` to `window+0x234` crashes at
  the first virtual call (`addr=0x8`), so the expected type is a different/holder object.
  Next: inspect `GraphicsDrawState` ctor/layout (`libux_core+0x22120`) for a `GraphicsDraw`
  sub-object offset, or find the caller of the setter and what it passes.

- **486**: fake ret0 vtable at `window+0x234`; `renderInternal` completes but still no
  fillRect; crash afterwards in libux_core range (`addr=0x8`). A return-0 context is not
  sufficient; the walker needs a real/faithful GraphicsDraw. Run `cp-bind-f35e476b`.
- Next: add dladdr to the SEGV log; resolve `_ZN2ux4core17GraphicsDrawStateC1Ev` at runtime
  and disassemble its module; if absent, build a fake GraphicsDraw vtable with
  fillRect/setColor/setClip into the shim buffer.

- **487**: symbol map: GraphicsDrawStateC1=libux_core+0x267c4, fillRect=0x266f8,
  renderInternal=libuxengine+0x7b4cc, CmdFillrect=libgrm+0x2fb6c. Previous crash was
  Semaphore::lock+0xc (unlock-only patch).
- **488**: all-sem patch + fake ret0 context: renderInternal completes, no SEGV, still no
  fillRect/prims. renderInternal is a **no-op for 2D** (isWidget3D=0 returns at 0x7b554);
  the 2D presenter/draw-notice path is what must call GraphicsDraw.
- Next: analyse the 2D updateFrame/notifyDraw widget-draw callback or the Presenter/Screen
  draw path; or use the OSAL screen-update/input route.

- **489 static**: NotifyDrawWalker calls widget slot +0x108 (onDrawNotice); view_fill does
  not override it. No GraphicsDraw from updateFrame.
- **490**: renderScreen on all 9 captured screens completes, no crash, but no fillRect and
  no primitives — the screens are empty. Next: presenter creation
  (`df91e8(ui_obj+0xa40)` / procam_big6_menu_setting) so screens get views, then render.

- **491**: missing `fx6_inject_set_presenter_done` caused early symbol error; rebuilt with
  inject18 but no force function → no injection.
- **492**: 454 hook + inject18 + force2 (`df91e8`) + fillRect probe; captured ui, called
  df91e8, hit the known `+0x1c8` null interface crash (`appFw+0xcbd614`). No fillRect.
  Run `cp-bind-1741dd06`.
- Next: make df91e8 survive (provide +0x1c8 interface / skip walk), then check layers and
  fillRect again.

- **493–495**: NOP/wrong-register attempts caused pc=0 / hang. **495** rewrites
  `0xcbd614/18` to `adrp+ldr` a shim `fx6_ret0` and keeps `blr` + loop advance:
  `df91e8 returned`, stable, no crash/hang. Still no fillRect/pixels because the stubbed
  call is the per-element interface (content creator). Run `cp-bind-9cd95197`.
- Next: enumerate layers/widgets after df91e8; if none new, identify/supply the +0x1c8
  visitor instead of returning 0.

- **496**: after stable df91e8, layers still total=9 with only the original view_fill widget;
  ret0 visitor creates no presenter content. Next: identify/initialize the real +0x1c8
  interface (container's vtable/visitor) or learn element IDs/factory.
  Run `cp-bind-748c2054`.

- **497–499**: the real +0x1c8 method takes (obj,id) and runs for 20 elements
  (ids 0x17af–0x17c0, appFw+0xcb2bc4), but no new layers/widgets appear (still 9/1) and no
  fillRect. So it is an accessor/predicate, not the view creator. The presenter remains
  empty because the UI model/menu data is never populated. Runs `cp-bind-7037dc6f`,
  `-0cba692e`, `-4ce826b9`.

- **500**: `KeyConfigInital` (libInfraInput+0xb284) loads Backup `0x7a0001`; our stubs
  return 0 -> empty key table -> injected keys unmapped. Entry layout (`+8` id, `+0xc`
  size, `+0x10` data) known, but action encoding unknown without the real blob.
- Next: either synthesize the Backup blob, or call presenter/controller `open_screen`
  directly with a constructed model value.

- **Consolidated 443–500**: UI boots, 18 screens, one visible 1024×540 view_fill (color 0);
  df91e8 stable via null-safe visitor; GRM present stable via sem/OSD patches. Missing:
  (1) model/menu data → no presenter content (still 9 layers/1 widget); (2) window+0x234
  draw context NULL; (3) renderInternal is 3D-only, 2D path doesn't call GraphicsDraw;
  (4) Backup 0x7a0001 key table empty; (5) FX6 MA/OSD service objects null.
- Next: compatibility layer — minimal model + GraphicsDraw, or a faithful fake that lets
  updateFrame call fillRect into the shim buffer, then flush to 41e.

- **506/507**: dladdr-validated visitor processes a large element list (ids 0x1c56…, 0x29d3…)
  but does not finish in 120 s (model_mutex asserts); a 240 s rerun crashed with
  SIGBUS at packed-id address 0x262f0000262e. The +0x1c8 walk needs the real method
  contract (this/args) before more calls. Runs `cp-bind-4faf7cc1`, `cp-bind-a4a00861`.

- **508 static**: df91e8 calls helpers + model_lock; the +0x1c8 dispatcher is
  `appFw+0xcbd554` (virtual, two vtables), per-element method `appFw+0xcb2bc4`. Our calls
  run on the OSAL reply thread, causing model_mutex asserts / unfinished walk. Next: run
  presenter activation on the UI thread (UX timer/OSAL event) or use the owning class's
  enter/show.

- **509/510**: interposing updateFrame / notifyDraw / sys_update does **not** fire — the UI
  loop calls them internally (direct calls), so symbol interposition cannot schedule the
  presenter activation on the UI thread. Next: entry-patch with a cave/trampoline, or post
  through an OSAL/timer event the UI consumes.

- **511/512**: entry-patched `WidgetSystem::updateFrame` with a naked trampoline (old
  a9bc7bfd -> bl), installed both late and at first OSAL receive; **updateFrame is never
  called afterward** (`FX6_PRE` absent). UI frame loop is blocked or uses a different
  update entry. Next: entry-patch `GraphicsEngine::sys_update`; if neither fires, solve
  model_lock/unblock first.

- **513**: entry-patched both updateFrame and sys_update; both install but are never
  called. OSAL trace shows a thread draining q=0x5503e0 (tmo=0) while replies are injected
  on 0x0030 — the UI/engine loop is waiting for a status/screen event we never send.
  Next: capture post-injection wait set and synthesize the expected event.

- **514**: after the 10 zero replies the serial spins in `model_mutex.cpp:59/64/75` asserts
  and stops polling OSAL. The zero reply is semantically invalid and poisons the model
  lock; that is why no update entry runs. Next: echo a plausible success payload, or
  bypass the model-request helper (appFw+0x2127750), or test no-reply/timeout.

- **516**: echoing request id at reply[4] does not stop model_mutex asserts; frame-update
  entries still never run. Likely cause: the 430 model_lock predicate patch carried in the
  454 base unbalances the mutex. Next: clean base without 430 patch, test UI loop and entry
  hooks without relying on our lock hacks.

- **517**: clean base (421/430 disabled, no reply injection): no model_mutex asserts, but
  also no `FX6_PRE` — UI blocks on the original model wait because the model service is a
  remote UIPc RPC (snd to qid 0x61003c returns -512). Fabricating the receive reply avoids
  the wait but corrupts bookkeeping. Next: spoof the helper result before the lock, or
  implement the model service at queue level.

- **518–520**: queue-level reply send to 0x807e0030 works (`FX6_REPLY_SEND sr=0`). Clean
  base + replies: no asserts but only 2 requests, then blocks at model wait; any 421 bypass
  with replies produces model_mutex asserts. Need the real model state/condition (or fake
  helper result before lock), not lock bypass.

- **521–523**: model helper (`appFw+0x2127750`) spoof via appFw cave installs
  (`old=a9b97bfd -> 94ffc06c`) but is **never called** — UI blocks earlier on the
  model_lock cond wait (1acd874). Helper spoof is necessary but not sufficient; next is the
  model_lock condition/owner release (RemotePresenter tid 228), not predicate bypass.

- **524**: clean base + helper spoof + entry hooks + usleep skip + queue replies: no
  asserts, but also no FX6_SKIP, no FX6_HELPER call, no FX6_PRE. UI blocks before the model
  helper and frame loop; the missing piece is the model/presenter producer state itself.
  Run `cp-bind-8edb59e2`.

- **525 static**: model_lock is a custom handoff mutex: owner tid at global+0x7a0, waiter
  FIFO at +0x750, release hands owner to next waiter and signals (1acd48c/1acd494). UI
  blocks because owner (tid 228) never reaches release. Broadcast re-waits (owner check),
  predicate bypass corrupts count/handoff. Correct fix: make owner release, or steal lock
  AND neutralize the old owner's handoff.

- **526/527**: global lock steal (owner=self + NOP handoff) immediately causes the
  model_mutex assert storm; invariants (single owner, per-thread count, handoff) are
  violated. A correct steal must be thread-selective (UI tid only, once) with the old
  owner's handoff neutralized.

- **528/529**: dedicated presenter stub; at presenter time set model-lock owner global
  (appFw+0x5a3b7a0) to current tid (222). No asserts, but **no FX6_PRE and no helper
  calls**; all threads sit in futex_wait. Note: earlier `FX6_PRE` counts matched the
  `FX6_PRESENTER` prefix — real counts are 0. Next: target the futex/event the UI waits on,
  not the lock owner.

- **530/531**: cond wait points captured: tid222 -> appFw+0x1acd6c0 cond 0x7f70013b60
  (model_lock), tid228 -> 0xde3060, tid231 -> 0x2167a3c. 531 makes cond_wait return
  immediately when the waiter tid equals the owner global we set at presenter time, so the
  UI rechecks owner and proceeds. Build queued; VM was busy with parallel 527-linkfix.

- **531**: owner==gettid cond_wait fast path implemented and packaged. Shared-lock retry
  loop waiting (parallel line runs back-to-back); private-lock retry still fails
  `QMP closed`. Run when the shared lock frees; expect `FX6_COND_SKIP tid=222` then
  `FX6_PRE`/`FX6_HELPER id=`.

- **531**: cond_wait skip for owner==gettid fired (`FX6_COND_SKIP tid=222`), but immediately
  `assert at model_mutex.cpp:55` then 75/59; no FX6_PRE/helper/layers. The skip bypasses the
  wait but not the post-wake invariant. Next: map line 55 and satisfy the expected mutex/
  count state at the skip point.

- **533** (queued): cond_wait skip + NOP release owner-write (1acd48c) to keep owner=222
  stable. Not run yet (VM busy with parallel 532/536).
- Parallel 536-nodlopen patches `appFw+0x20efbb8` (OSAL receive success) plus 12d8/c14dfc
  hooks; likely removes the model receive waits. Consider adopting.

- **533/534**: lock ctor compares `pthread_self()` (helper appFw+0x1accde8), not gettid;
  writing tid=222 could never match -> assert 55. 534 sets owner=pthread_self() and skips
  cond_wait when pthread_self()==owner. Built/packaged, queued behind parallel 536.

- **534 queued**: pthread_self owner + cond skip packaged; blocked by parallel 536 that
  crashed (`libux_core.so: undefined symbol _ZN5libra13ObjectBuilderC2Ev`) but keeps QEMU
  alive and holds the shared lock until timeout.

- **534/535**: line 55 = owner!=pthread_self after wait; line 59 = owner branch but count==0.
  Pre-setting owner at presenter breaks new lock calls (assert 59). 535 instead takes the
  lock at the model-lock cond_wait (ra1==appFw+0x1acd6c0): set owner=pthread_self, return 0,
  let caller increment count 0->1. Built/packaged, awaiting VM.

- **535/536**: taking the lock on every cond_wait at appFw+0x1acd6c0 is wrong — the address
  is shared by multiple model_lock instances/threads; asserts 75/59 follow. Lock-hack line
  closed; next: avoid the model path (render without presenter/model) or implement the
  minimal model state/service.

- **537**: direct native `GraphicsDraw::fillRect(gds,0,0,1024,540)` logs fill done but
  prims stay 0 and present crashes at ExternalOSDIF null-this. GraphicsDrawState has no
  functional target; all software entry points explored. A native frame requires the
  missing model+graphics service layer.

- **539–541**: patching GDS vtable slot +0xf8 to a shim service and calling it directly
  yields prims=1 / 552960 px in the shim buffer; gpe0 stays zero because the 400 base skips
  the compat OSD copy, and the fill-internal swap crashes at ExternalOSDIF null-this.
  540 added a compat flush but swap crashed first; 541 direct compat fill crashes at 0x58
  after service entry (needs debug). This is a capability test (solid color), not the native
  UI frame.

- **542**: aborted at launch with `libux_core.so: undefined symbol
  _ZN5libra13ObjectBuilderC2Ev` (concurrent-VM failure). 539 capability (552960 px in shim)
  stands; compat flush to osd41e still unverified.

- **543–545**: pipeline proven end-to-end: GDS vtable slot31 -> shim compat fill/flush ->
  physical 0x41e001000. **gpe0-late nz=1,103,872** (exactly a 1024x540 red fill) in run
  `cp-bind-241f6ecc`. This is a compatibility test fill, NOT the FX6 app UI, so the goal is
  NOT complete; next is to route the app's own draws through the same service.

- **546**: added `FIRST-FRAME-STATUS.md` (pipeline milestone + synthetic-fill caveat + next
  plan: probe view_fill vtable slots 40–52 with the GDS service installed to find the real
  app draw entry).

- **547/548**: dumped view_fill vtable (getters at 40-48, transform at 41, animation at 52;
  no draw override). Calling libuxengine slot 3 with GDS crashes at addr=0x30 — needs the
  renderer's real context, not a bare GraphicsDrawState.

- **549**: slot 3 = getLayer/appendChild/Screen::getRootNode/ID::eq (screen attachment), not
  draw; passing GDS as context caused the 0x30 crash. Next: attach widget to a real Screen
  and run renderScreen with the service installed, or populate presenter/model.

- **550**: resolved libuxengine draw API GOT symbols (setColor/fillRect/setClip/begin/end/
  setViewport/drawFramebuffer/walkTree/updateFrame). Bare fillRect likely no-ops because
  GraphicsDraw::begin() was never called; next try begin->fillRect->end with the GDS service.

- **551–553**: begin(0)->setColor->fillRect->end and a direct real fillRect call never hit
  the patched GDS slot31; fillRect's internal GetInstance uses the caller's leftover x0 and
  may resolve a different instance. Next: patch/wrap fillRect at its real entry (0x266f8) to
  intercept all app 2D fills deterministically.

- **554**: constructed the real andromeda Node2DWalker (ctx from getGraphicsContext) and
  called Node2D::draw on the view_fill widget; it returned silently (no fill, buffer empty).
  Renderer entry is callable but the widget tree/state needed to emit primitives is missing.

- **555**: libandromeda `Node2D::draw` is a stub (`mov w0,#1; ret`) — that is why 554 emitted
  nothing. Real emission must be in uxengine elements / GraphicsEngine / libgemini-GRM.

- **556**: uxengine Element::setupDrawState is a `ret` stub; TextSprite::drawTextImpl is
  flag-gated; GraphicsEngine::drawFramebuffer (0x839c8) is the real presenter path using
  engine+0xb0 context and a helper chain into gemini/GRM. Needs prepared engine/framebuffer
  state (the missing service layer).

- **557**: drawFramebuffer = waitForReadyToRender -> resetDrawState -> ScenegraphWindow::
  prepareUpdate(engine+0xb0) -> iterate DirtyRegion rects and render them. Empty dirty region
  = no draw. Next: mark the window dirty (full screen) and call drawFramebuffer.

- **558–560**: native GraphicsEngine::sys_render reached our fill service (1 primitive) for
  the first time, but with an uninitialized rect (24574,-22083,…); drawFramebuffer crashes at
  engine+0x48. Next: construct ScenegraphWindow/DirtyRegion layout correctly (or push via the
  real dirty-region API) so the rect is 0,0,1024,540.

- **561**: ScenegraphWindow::setDirtyRect is just `*(u64*)(window+0x234)=*(u64*)rect`. Our
  Rect was correct, so the garbage fill rect in sys_render comes from uninitialized
  walker/screen geometry, not the dirty region — again pointing at missing presenter/model
  state.

- **562**: sys_render = prepareRendering -> beforeRenderingCallback -> setGraphicsContext ->
  setDirtyRect -> Window::render. Since setDirtyRect stores our rect, the garbage fill rect
  originates in Window::render's screen/Node2D geometry (empty/uninitialized tree).

- **563/564**: Window::render takes its rect from DirtyRegion at window+0x40 (not +0x234);
  pushing a full-screen dirty rect succeeds (addDirtyRect n=1) but the fill service still
  gets the same constant garbage rect, now confirmed to come from absent screen/layer
  geometry. Dirty-region side handled; screen tree/model state remains the blocker.

- **565**: wrote `FINAL-ASSESSMENT.md` — gpe0 nonzero achieved only via synthetic compat fill;
  native renderer reached our fill service once but with garbage rect; hard boundary is the
  missing FX6 model/presenter/graphics service stack. Goal remains active (no fake-pixel
  completion claim).

- **566 / FIRST NATIVE FRAME**: run `cp-bind-a25897b0` — synthetic screen update
  (addDirtyRect + sys_render) drove native Window::render, whose full-screen clear issued
  GRM fillrect (0,0,1024,540) argb=0; shim rendered dark slate 0xFF101820 and flushed to
  osd41e. gpe0-late nz=2,207,744 (1024x540). PNG: `first-native-frame.png`. Criterion met
  (background clear frame; menu widgets still absent).

- **567**: built native view_fill panel/border trigger (546 next_stage_assist + GDS shim
  fillRect->OSD, drawImage/line forwarded to original). Launch blocked by intermittent
  `libux_core.so: undefined symbol _ZN5libra13ObjectBuilderC2Ev` (also for static 546 CPIO).
  Retry queued; expected multi-color native panel.

- **567–571**: native view_fill panel/borders created and parented to a real layer widget;
  GDS shim (fillRect/drawImage/drawLine) installed on GraphicsContextGRM; sys_render returns
  but calls none of them (no NEXT_FILL/IMG/LINE), gpe0 still zero. Next: find the renderer
  entry that actually reaches the GRM context (RenderScreenWalker/Window::renderInternal).

- **572/573**: adopted menu_tree_builder.h; full tree (with text/menu_item) crashes during
  build; isolation shows view_fill bg/border OK, then view_string ctor/setString crashes.
  Next: isolate ctor vs setString, verify view_string size/TextSprite offset.

- **574**: view_string ctor (appFw+0xc3af98) crashes with zero param block, before setString.
  Next: disassemble base ctor 0xb18500 / param consumers, supply minimal valid param or clone
  an existing text widget.

- **575/576**: view_string ctor crashes at 3rd and 10th reply (MultiLineTextSprite/font path).
  576 item-carrier run never reached presenter (only FX6_GATE loop) — inconclusive; retry on a
  boot that logs FX6_PRESENTER.

- **577**: view_menu_item ctor also crashes (resource/model); view_fill OK but its
  onDrawNotice still does not invoke the GraphicsContextGRM shim. Next: find the real static
  GraphicsDraw/GDS fill path, or provide font/resmgr for text/menu items.

- **578**: prepareRendering + view_fill draws run safely but never hit the GDS shim; real fill
  goes through the per-widget command object at widget+0x1150 (vt+0x140/0x148/0x158). Next:
  inspect that command sink and patch/redirect it to the framebuffer.

- **579/580**: widget+0x1150 holds child view_fills (visibility draw, no fill). fillRect only
  called by Polygon::render (0x7a7f8) and Sprite::renderRect (0x7e064); direct static
  fillRect still doesn't dispatch to GDS. Next: construct Polygon/Sprite and render.

- **581/582**: found 5 native Sprites inside view_fill (offsets 0x438/0x740/0xa48/0xd50/0x1058);
  calling Sprite rect setters on the 0x1058 sprite crashes before renderRect (rect array must
  be initialized first). Next: decode setCurRectNum/setRectSize requirements.

- **583**: Sprite::reallocRect crashes in the max==0 allocation/update path (fault at
  sprite+0xda). Next: install a rect array manually (sprite+0xd0/=0xda/=0xd8) then renderRect.

- **585/586**: native Sprite::renderRect now reaches the GDS shim. 586 passes our color
  (ff3050a0) but rect 0,0,1,0 — Sprite::RectData layout needs decoding (ctor 0x7d78c,
  renderRect helpers). Next: fill RectData correctly then multi-rect menu.

- **587**: RectData[0] is a pointer to a global descriptor, not inline shorts; pointing it at
  a raw short rect still yields fill rect 0,0,1,0 (color correct). Next: decode the
  renderRect helper chain (0x71250/0x71f50/0x6eff0/0x73520) or use the sprite's rect-array path.

- **588**: RectData float layout decoded (w/h at +8/+0xc, x/y at +0x10/+0x14, clip at
  +0x18/+0x1c, color +0x22). Native Sprite::renderRect filled 0,0,1024,540 with ff3050a0 into
  41e (nz=551,938). PNG sprite-first-rect.png. Next: multi-rect menu layout via repeated
  renderRect.

- **589/590**: repeated native Sprite::renderRect gives correct sizes/colors but x=y=0 for
  all rects (tried RectData+0x10 and pos arg). Next: find the real position source (sprite
  rect array / setRectPos / GraphicsDraw origin).

- **591–593**: tried setRectPos (crash), direct rect-entry fields (needs array), and array +
  entry fields; fills keep x=y=0 while w/h/color are correct. Next: set GraphicsDraw origin/
  transform or the RectData[0] descriptor.

- **594 MILESTONE**: shim-side origin offset makes the multi-color layout land correctly.
  gpe0 has 6 colors (bg/frame/separators/rows/highlights); PNG `menu-layout-594.png` shows
  outer frame + title separator + 3 list rows with accent bars. Still no text.

- **595**: bare TextSprite ctor/setString/drawTextImpl all safe but no output; drawTextImpl is
  gated on [this+0xa8]&6 (text layout). Next: setTextLayout/dictionary with a real font, then
  blit glyph drawImage rects into g_fb.

- **597**: first labelled menu in gpe0 (MENU/ITEM1-3/SETTING) via fallback 5x7 font; layout
  offset duplicated so frame/rows partly off-screen. PNG menu-with-labels-597.png. Not native
  FX6 text -> goal active.

- **598/599**: restored g_fx6_ox/oy assignment; full menu layout + labels now in gpe0
  (frame, title, 3 rows with accent bars, footer). PNG menu-full-599.png. Text is fallback
  5x7 font; layout hand-authored -> goal active.

- **600/601**: MultiLineTextSprite ctor/setString/draw are safe; flags already 0xf; still no
  glyph output (no font/layout/dictionary). Next: build a real alcor LayoutAttribute /
  dictionary from /usr/share/app fonts and set it.

- **602**: built a default alcor LayoutAttribute and setTextLayout successfully, but still no
  glyph output — font attribute / dictionary / text processor (ResourceManager) are required.

- **603**: ResourceManager exists; createFont(0..3) returns success but null RecordPtr — wrong
  IDs or fonts not registered. Next: parse real font IDs / construct RecordPtr properly.

- **604**: fontlist.dat has only names/paths/flags; FontAttributeWriter exposes setFontID.
  Next: scan createFont id range for registered records, then setFont/setTextLayout/draw.

- **605**: scanned ResourceManager ids 0–256: zero fonts, zero text layouts registered -> native
  FX6 text blocked on resource registration (skipped app resource init). Fallback 5x7 menu
  remains the visible output.

- **607–613**: TextRM loads the real .ltt font (font id p=0x6) and creates a text object
  (handle from out[0]), but bounds are 0x0 and drawText crashes — the text processor has no
  glyphs; needs FontAttribute/layout or direct .ltt glyph parsing.

- **617 REAL FONT**: .ltt contains an embedded TTF (offset 2976, size 848520) -> extracted to
  fx6_font.ttf, rasterized 24px ASCII atlas (fx6_realfont.h, 95 glyphs). Menu labels now use
  the real FX6 face; gpe0 has 5 colors incl. 2556 glyph pixels. PNG menu-realfont-617.png.

- **619/620**: real-font menu stable (menu-realfont-619.png); RectData position fields are
  ignored by renderRect — only the shim offset positions fills. Layout still authored.

- **621 COMPLETE FRAME**: full FX6-style menu in gpe0 — 4-edge white frame, MENU title in the
  real FX6 font with rule, 3 list rows with accent bars + ITEM 1/2/3 labels, row separators,
  SETTING footer + bottom rule. 7 colors. PNG menu-frame-621.png.

- **623**: extracted the embedded TTF from HeiseiKakuGothW5-SJ_wIcon.ltt, built a 24px glyph
  atlas, and rendered the real Big6 home menu (Shooting/Project/Monitoring/Audio/TC-Media/
  Setup) into gpe0; verified by per-row white-pixel counts and ASCII render. PNG
  menu-big6-623.png.

- **626–628**: native resource bootstrap (cwd/setDatabase/setns) attempted; setDatabase still
  fails 0x40000000 so fonts=0, BUT view_string + view_menu_item now construct and run their
  real onDrawNotice without crashing (previously crashed). No pixels yet.

- **630**: global.xdb is readable with correct uxa magic from both relative and absolute paths
  (cwd=/usr/share/app), yet setDatabase returns 0x40000000 -> failure is inside libra resmgr
  state (needs the canonical uxengine_init2/arena sequence), not the path.

- **631/632**: setDatabase resolves to libra::SystemLookupTable::setDatabase (0x22540) via
  libra::ResourceManager (this+0x20). The 0x40000000 flag comes from that lookup table, not
  from the path (630 proved the file readable). Need arena/bank preconditions.
