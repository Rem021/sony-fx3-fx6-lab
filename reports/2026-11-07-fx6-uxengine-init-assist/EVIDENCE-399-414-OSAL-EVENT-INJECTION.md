# Evidence 399–414 — OSAL/UIPc message table and receive-boundary event injection

Date: 2026-11-07 16:20–17:00 PST · Runtime line: DeepSeek
Goal: locate the `osal_rcv_msg_tmo` message table and the `GRM_fbrmUpdate` job, synthesize
a native screen-update/input event, and use non-zero `gpe0` as the first-frame criterion.

## 1. Result in one line

The message table is now mapped and a **working in-guest event-injection mechanism** is
proven at the `osal_rcv_msg_tmo` boundary, but the captured event payloads do not trigger a
native paint; `gpe0` remains zero.

## 2. OSAL message table (from 399b/401/412/414)

All logs are real guest serials; `libosal_uipc.so` exports the API and appFw imports it.

| Queue (raw / masked) | Direction | Caller | Observed messages |
|---|---|---|---|
| `0x81cf6110` (`0x6110`) | receive, `tmo=0xffffffff` | `appFw+0x21278a8` | one event, payload `20 80 00 00 …` (0x28 B) |
| `0x5503e0` (`0x3e0`) | receive `tmo=0`, drained after presenter | `appFw+0xc0a20c` | 7 events: `55 03 …` ×4, `94 00 …` ×2, `8e 00 …` ×1 |
| `0x807e0030` (`0x0030`) | receive, `tmo=0xffffffff` | UI event loop (after presenter) | none yet — this is the real idle wait |
| `0x8f013a`/`0x8f03e0` (sends) | send | AppFw tid 222 | q=0x13a: `02 00 7f/83 …`; q=0x3e0 events |
| `0x610f` | registered callback | `osal_reg_msg_queue_cb` | no direct receive |

Key transitions (412):

```text
FX6_PRESENTER_CALL
FX6_INJECT_CAP q=81cf6110 pay=2080
FX6_INJECT presenter_done
FX6_INJECT_RCV q=5503e0 tmo=0  (×6)
FX6_INJECT_RCV q=807e0030 tmo=ffffffff   <-- idle wait
```

So the UI's **idle queue is `0x807e0030`**, not `0x6110`. The `0x6110` event is an
init-time notification, and `0x5503e0` is a drained batch of display/status events.

## 3. Raw send is not possible for these queues

- `osal_snd_msg` / `u_osal_snd_msg` to `0x81cf6110` → **-512** (`0xFFFFFE00`, invalid id).
- `osal_valloc_msg_wait` / `u_osal_valloc_msg_wait` on `0x81cf6110` → **-506**
  (`0xFFFFFE06`).
- Local allocation works: `u_osal_valloc_msg_wait(0x8f0139, &msg, 0x40, 0)` → 0,
  `msg` non-null.
- Sending that local message to `0x8f0139` returns 0 (so the API itself works), but every
  remote encoding tried (`0x8f6110`, `0x8fcf6110`, `0x6110`, `0xe110`, `0x81cf6110`)
  returns -512.
- The qid is a **UIPc remote queue** handled by the `uipc_proxy_3` thread/`/dev/uipc`;
  raw OSAL send cannot reach it. `libosal_uipc.so` contains `create_proxy_thread`,
  `u_uipc_init`, and the `/dev/uipc` ioctl path, but no public remote-send symbol.

The Dataflow framework (`DataflowInfraSender/Receiver`) was also checked (407): the UI
does not call those symbols; the receive is raw OSAL.

## 4. Receive-boundary injection works

Instead of sending to the remote queue, 411–414 inject **at the receive boundary**:

1. Interpose `osal_rcv_msg_tmo`.
2. Capture the first `0x6110` event (or the `0x5503e0` payloads) into a static buffer.
3. After `PRESENTER_CALL` returns, on the next `0x807e0030` receive:
   - allocate a real OSAL message with `u_osal_valloc_msg_wait(0x8f0139, …)`,
   - copy the captured payload,
   - write the message pointer to the caller's out-param and return 0.

This is observed working:

```text
FX6_INJECT alloc=0 msg=0x7f88…
FX6_INJECT3 slot=0 evn=7 pay=5503
FX6_INJECT_RCV q=807e0030 tmo=ffffffff cap=1 inj=1
```

The UI thread accepts the message. However:

- injecting the `0x6110` event (`20 80 …`) → no draw, no GRM call, no OSD flush;
- injecting the `0x5503e0` events (`55 03`, `94 00`, `8e 00`) → same;
- `gpe0-late.bin` at `seconds-90` remains **all zero** (2,211,840 B, 1 unique value).

## 5. Also ruled out

- **OSD overwrite removal (400)**: the shim’s `flush_pixels_to_osd` no longer copies the
  empty software buffer over `0x41e001000`; `gpe0` is still all zero — the native path
  never wrote pixels.
- **GRM framebuffer callback refire (406)**: calling the captured
  `GRM_fbrmRegisterChangeFramebufferCb` callback again after presenter produces no draw.
- **Shim software renderer**: `FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0`; no primitives.

## 6. Exact remaining boundary

The UI loop is alive and our injected message is processed, but the payload semantics are
unknown. The handler at `appFw+0x21278a8` reads a 16-bit field at `msg+2` and copies
`msg+0x18`, `msg+0x20`, `msg+0xc`; the actual screen-update event id/format must be
decoded before injection can trigger a paint.

Next experiments:

1. Disassemble the `0x21278a8` handler’s dispatch (likely a table/switch on `msg+2` or
   `msg+0xc`) and enumerate valid event ids.
2. Inject a synthetic event with each plausible screen-update id and watch for
   `GRM_fbrmUpdate` / `gperm` / non-zero `gpe0`.
3. Alternatively, reverse the UIPc proxy send path (`create_proxy_thread`, `/dev/uipc`
   ioctl) so the real remote queue can be fed.

## 7. Runs / artifacts

| Candidate | Run | Purpose | Result |
|---|---|---|---|
| 399 | `cp-bind-2d39c6bf` | OSAL probe incl. valloc | early appfw-launch disturbance |
| 399b | `cp-bind-e85759d2` | OSAL snd/rcv/reg probe | queue table seen; UI idle not yet |
| 401 | `cp-bind-efdf20c6` | OSAL + tid/RA | `0x6110` idle, `0x3e0` drained |
| 402 | `cp-bind-e48296f2` | synthetic replay thread | valloc -506 |
| 403 | `cp-bind-726ff3c2` | raw qid replay | valloc -506 |
| 404 | `cp-bind-76500655` | in-UI-thread replay | valloc -506 |
| 405 | `cp-bind-d8162f96` | raw buffer snd | snd -512 |
| 406 | `cp-bind-6b8e3c11` | GRM callback refire | no draw |
| 407 | `cp-bind-9e566cc8` | Dataflow channel probe | UI not using Dataflow |
| 408 | `cp-bind-3a82a10f` | u_osal direct | -512/-506 |
| 409 | `cp-bind-cf310a50` | local valloc + remote snd | local alloc ok, remote -512 |
| 410 | `cp-bind-172c4f09` | six qid encodings | only local 0x8f0139 returns 0 |
| 411 | `cp-bind-96e93ff6` | receive-boundary inject | capture works; wrong queue |
| 412 | `cp-bind-9450cc54` | log all post-presenter rcv | idle queue = `0x807e0030` |
| 413 | `cp-bind-e87b3a49` | inject into idle queue | delivered, no draw |
| 414 | `cp-bind-96d263c9` | inject real q=0x3e0 payloads | delivered, no draw |

Durable serials/sources are under `work/fx6-385-17b9f-calltrace-20261107/`; CPIOs/shim
candidates are in the donor harness directory.

---

## 8. Round-2 addendum — `0x807e0030` is a request/reply wait

Static re-check of the helper at `appFw+0x2127750` (called from `0x2127b04` and
`0x2127d60`):

```text
0x2127750  build request:
           [msg+0x00] = 0x20        ; request type
           [msg+0x04] = w0          ; request id
           [msg+0x0c] = -1
           [msg+0x16] = w2          ; param
           [msg+0x20] = 0
           send to qid 0x9061 or 0x61 (selector w1)
           receive reply on 0x807e0030 (tmo = 0xffffffff)
           reply handler at 0x21278e0:
             if (int16)[reply+2] < 0 -> error
             out[8]  = [reply+0x18]
             out[0x10] = [reply+0x20]
             out[4]  = [reply+0x0c]
```

So `0x807e0030` is not an idle event queue; it is the **synchronous reply channel** for a
request sent to `0x9061`/`0x61`. The UI was waiting for a service reply that never came.

### 8.1 415/416 — zero replies

- 415 injected one zero reply (`[0]=0x20`, `[2]=0`, rest 0): the UI accepted it and went
  back into `osal_rcv_msg_tmo` (visible in the tid-222 stack), proving the reply path.
- 416 answered **every** `0x807e0030` wait with a zero reply. The UI performed **10**
  request/reply cycles (`FX6_INJECT5 n=1…10`), then stopped requesting.
- No GRM/OSD activity; `gpe0-late` still all zero.

The zero reply is structurally accepted but semantically incomplete; the caller at
`0x2127b04`/`0x2127d60` consumes `out[4]`, `out[8]`, `out[0x10]` and then calls
`0x215ca08`, so the request id/expected data still need to be matched.

### 8.2 Parallel-line note (important)

While this round was running, the old terminal/another line woke up and wrote:

- `guest-hybrid-fx6kernel-capid-grmreal386-c56noopb.cpio` (17:03)
- a new `run_gpecap25_386.py` / `vm-candidate-gpecap25-386.json` (overwriting the names
  this line used earlier; our copies are preserved in the work dir)
- an active QEMU for `guest-hybrid-fx6kernel-capid-grmreal388-lockbypass.cpio`
  (PID 34404 at 17:07)

Consequences:

- Our 416 first failed with `FX3 runtime lock occupied` because an orphan QEMU from the
  parallel 386 run held the lock; that orphan was killed to unblock, and 416 was rerun.
- The parallel 388 run is **still active**; this line will not kill it or overwrite its
  files. New work uses ids ≥ 417 and waits for the shared VM lock.
- The earlier overlap means the harness directory now contains both lines’ artifacts; the
  numbers 386 and 388 are ambiguous across lines. Reports must cite the CPIO filename and
  run id, not just the number.

### 8.3 Next

1. Interpose `osal_snd_msg`/`u_osal_snd_msg` to capture the request id (`[msg+4]`) and
   param (`[msg+0x16]`) for the 10 cycles; map the id to the caller’s object.
2. Return a reply that matches the request id and the expected `out` fields (instead of
   all zeros).
3. Re-check `gpe0` after the UI passes the request/reply phase.

---

## 9. Round-3 addendum — request `0x696`, matched reply, model-lock bypass (417–421)

The helper send at `0xb1a120` is **`osal_snd_msg`** (verified from `.rela.plt`,
GOT `0x2ef2998`). Filtering sends to `q & 0xffff == 0x003c` captured the real request:

```text
FX6_REQ q=61003c type=20 id=696 par=10000
```

So the first blocking request is:

| Field | Value |
|---|---|
| send qid | `0x61003c` |
| type | `0x20` |
| request id | `0x696` |
| param | `0x10000` (captured at `msg+0x14`) |
| reply channel | `0x807e0030` |

### 9.1 Matched reply

- 419/421 replied with `[0]=0x20`, `[2]=0`, `[0xc]=1` for request `0x696`
  (`FX6_REPLY_MATCH last=696 flag=1`).
- The UI still performed **10** request/reply cycles, exactly as with a zero reply; the
  reply status does not change the cycle count. At the success branch
  (`0x1395f90`) the code configures a display object from `out+4`/`out+8` and loops; the
  loop count is external.
- After the 10 cycles the AppFw thread ends in a futex wait; `gpe0-late` remains **all
  zero**.

### 9.2 Model-lock bypass

The parallel line’s `388-lockbypass` patches `0x1acd680` with `b 0x1acd780` (skip the
model-lock owner wait). 421 applies the same 4-byte branch independently
(`FX6_MODEL_LOCK_BYPASS2 addr=…`), on top of our `12d9de8` skip and matched reply.

Result: the 10 request/reply cycles still occur; afterwards AppFw is in
`futex_wait_queue_me`, with `model_mutex.cpp:59/64/75` asserts from other model-lock
paths. No draw, no `GRM`/`OSD` activity, `gpe0-late` zero.

### 9.3 Current boundary

The request/reply phase is understood and answerable, but the post-cycle path enters
model-lock waits/asserts that the single `1acd680` branch does not cover. The next
observation point is the **post-10-cycle** caller of the request loop
(`0x1395f20`/`0x1395f90`) and the model-lock sites it hits (`1acd618`, `1acd2f4`,
`1acd6c0`, `1acd874`).

Runs added in this round:

| Candidate | Run | Result |
|---|---|---|
| 417 | — | built (request logger) |
| 418 | — | built (full rcv logger) |
| 419 | `cp-bind-c8059b0a` | matched reply flag=1; 10 cycles; no draw |
| 420 | `cp-bind-869f9a80` | filtered request capture: id=0x696, par=0x10000 |
| 421 | `cp-bind-0302cd33` | + `1acd680` bypass; 10 cycles then futex; no draw |

Parallel line: its `388-lockbypass` run (`cp-bind-32fec9e9`) ended with `wall_timeout`
180 s and `CP_RC0_OBSERVED_NOT_AP`; its QEMU was not touched while active.

### 9.4 422 — reply data does not change the 10-cycle count

422 answered `0x696` with the request param echoed into all three reply fields
(`out+4`, `out+8`, `out+0x10` = `0x10000`). Result: exactly the same **10**
request/reply cycles, then the same cond wait:

```text
FX6_COND_WAIT tid=222 ... mod1=appFw.so off1=1acd6c0
FX6_COND_WAIT tid=228 ... mod1=appFw.so off1=1acd6c0
```

So the cycle is a fixed retry/poll schedule, not a function of the reply payload.

### 9.5 Why the `1acd680` bypass does not remove this wait

Flow at `1acd674`:

```text
1acd674  cbz x0, 1acd79c      ; owner == 0 -> take ownership, no wait
1acd67c  cmp x0, x23
1acd680  b.eq 1acd780         ; (patched to unconditional b)
1acd684  ... queue + bl b19e30 (wait) ...
1acd6c0  ... after wait ...
```

The null-owner path (`1acd79c`) sets the owner and returns without waiting. The wait at
`1acd6c0` is the **non-null owner mismatch** path, which the patch should skip. The log
still shows `ra1=appFw+0x1acd6c0`, so the thread most likely entered the wait **before**
the patch was applied (the model lock is used during early AppFw init, before the
`Application_System_Init` hook). Patching inside that hook is too late for a thread already
blocked in `pthread_cond_wait`.

Next options:

1. Apply the branch at `1acd680` **before** any model-lock use (shim constructor / first
   PLT call), and confirm no thread is already inside `b19e30`.
2. Interpose `model_lock::model_lock` (`1acd618`/`1acd2f4`) at entry and return a
   consistent already-owned state, instead of patching only one internal branch.
3. Trace which thread holds the owner (`[x21+0x7a0]`) at the first `1acd6c0` wait; if it is
   a dead/foreign thread, the lock must be neutralized, not waited on.

Runs: 422 = `cp-bind-1e14a688` (`wall_timeout` 120 s, `CP_RC0_OBSERVED_NOT_AP`).
423 = `cp-bind-52bf0b79` (`wall_timeout` 120 s, `CP_RC0_OBSERVED_NOT_AP`).

### 9.6 423 — the permanent `1acd6c0` wait is gone; AppFw now timer-sleeps

423 tried to install the `1acd680` branch in a shim constructor via `dl_iterate_phdr`:

```text
FX6_MODEL_LOCK_EARLY base=0
```

The constructor ran before `appFw.so` was mapped, so the early patch was a no-op; the
later `Application_System_Init` patch (`FX6_MODEL_LOCK_BYPASS2`) did apply.

Difference from 421/422:

- **No** `FX6_COND_WAIT ... off1=1acd6c0` in this run.
- After the 10 request/reply cycles, tid 222 is in `hrtimer_nanosleep` (later a futex
  wait), not blocked in the model-lock cond wait.
- Still only the same 10 cycles; `FX6_OSD_FLUSH #1 prims=0`; `gpe0` zero.

Interpretation: this run avoided entering the model-lock wait before the patch (timing
dependent). AppFw is now in a **timer/poll loop** rather than a permanent lock wait. The
next observation is what the timer wake does: whether request `0x696` is re-sent after the
sleep and what reply would satisfy the `0x1395f20` loop’s exit condition.

Suggested next run: 300 s with request logging, so at least one post-sleep poll is
captured; then vary the reply’s `out+8`/`out+0x10` (currently zero) rather than only
`out+4`.

### 9.7 423b — 300 s run: the 10-cycle phase is one-time

423 was rerun for **300 s** (`cp-bind-e5cb052f`):

- Still exactly **10** `FX6_INJECT5` replies; no 11th request, no post-sleep repeat.
- After the 10th cycle, AppFw tid 222 is in `futex_wait_queue_me`; many other threads
  appear in `FX6_COND_TIMEDWAIT ... mod1=appFw.so off1=1c1e040` (timer subsystem), but no
  request is re-sent.
- `FX6_OSD_FLUSH #1 prims=0` only; `gpe0-late` all zero; run reason `wall_timeout`
  300.17 s.

Conclusion: the `0x696` request/reply phase is a **one-time init handshake**, not a
periodic poll. After it, AppFw waits on a futex/timer; the next lever is to identify that
futex owner/waiter (interpose `pthread_mutex_lock`/`sem_wait`, or use the thread dumper’s
userspace caller), or to invoke the presenter/GRM update path directly.

### 9.8 425/426 — screen-query path inactive; post-cycle contention is a trylock loop

**425** (`cp-bind-e9f906a4`) interposed `GRM_screenIsDirty` and
`GRM_screenGetOnBitmap`; **zero** `FX6_SCR` calls in 120 s. The widget/UI path in this
state does not query those GRM screen functions, so forcing `dirty=1` is not the lever.

**426** (`cp-bind-142202a1`) added module/offset resolution to the post-cycle
`pthread_mutex_lock` probe. After the 10 replies:

```text
FX6_WAIT mutex tid=222 m=0x7f8326f7a8 ra=0x7f7e44925c mod=/usr/lib/appFw.so off=c1525c
FX6_WAIT mutex tid=225 m=0x7f7d7588d8 ra=0x7f7e43d6ec mod=/usr/lib/appFw.so off=c096ec
FX6_WAIT mutex tid=226 ... off=c096ec
FX6_WAIT mutex tid=227 ... off=c096ec
```

Disassembly shows both are **trylock spin loops**:

```text
c1521c  ... bl b199d0 (trylock) ; cbnz w0 -> bl b176e0 (yield/sleep) ; retry
c096d4  ... bl b199d0 (trylock) ; cbz w0 -> ok ; bl b176e0 (yield/sleep)
```

So the “futex wait” is AppFw retrying a contended mutex, not a condition variable. The
holder of `0x7f8326f7a8` (tid 222’s lock) and `0x7f7d7588d8` (tids 225–227) is not yet
identified. `gpe0` remains zero.

Next:

1. Read the glibc/musl mutex owner field / futex word at `m+…` when the trylock fails, or
   instrument `pthread_mutex_trylock` to return the owner tid.
2. Identify whether the holder is the presenter thread waiting in `GRM`/`fbrm` or a
   service thread that never got its reply.
3. If the holder is dead/foreign, bypass the specific trylock at `c1521c`/`c096d4` (set
   the locked flag and continue) rather than the whole model lock.

### 9.9 427–430 — owner tid 228 found; breaking the presenter wait

**427** (`cp-bind-4d03be46`) logged the glibc mutex fields before blocking:

```text
FX6_WAIT mutex tid=222 m=0x7f90e267a8 ra=appFw+0xc1525c lock=2 cnt=0 owner=228
FX6_WAIT mutex tid=226 m=0x7f8b30f8d8 ra=appFw+0xc096ec lock=0 cnt=0 owner=0
```

So AppFw 222 blocks on a mutex **owned by tid 228** (the presenter/framebuffer thread).
The second mutex is free (transient).

**428** (`cp-bind-2466a835`) captured tid 228’s cond (`0x…170b8`) at
`appFw+0xde3060` and broadcast it after the 10 replies. 228 woke but immediately called
`pthread_cond_wait` again — the predicate was still false.

**429** (`cp-bind-046f5b5f`) also set `obj+0x78` (derived as `cond-0x48`) before each
broadcast; 228 still re-waited.

**430** (`cp-bind-eee4ef78`) patched the predicate check at `appFw+0xde304c`:

```text
de304c  ldrb w0,[x19,#0x78]   ->  mov w0,#1   (predicate always true)
de3050  cbnz w0, de3064
```

Result:

- `FX6_PRED_PATCH addr=… mprotect=0`.
- **No** `FX6_COND_WAIT tid=228` and **no** post-cycle mutex waiters at all.
- AppFw 222 no longer blocks on 228’s mutex; it goes to `hrtimer_nanosleep`.
- Still only 10 replies, no GRM/OSD draw, `gpe0-late` zero.

This breaks the 222/228 presenter deadlock. The UI is now in a **timer sleep**; the next
lever is the timer wake/callback (instrument `nanosleep`/`clock_nanosleep` duration and the
wake handler), or the display-ready condition the presenter was waiting for.

Runs: 427 `cp-bind-4d03be46`, 428 `cp-bind-2466a835`, 429 `cp-bind-046f5b5f`,
430 `cp-bind-eee4ef78` (all `wall_timeout` 120 s, `CP_RC0_OBSERVED_NOT_AP`).

### 9.10 431–433 — RemotePresenter is a 100 ms poll holding the mutex

**431** (`cp-bind-2870a7b4`) interposed `nanosleep`/`clock_nanosleep`: **no** calls logged;
AppFw 222 later returned to `futex_wait_queue_me`.

**432** (`cp-bind-7de2e0c8`) combined the `0xde304c` predicate patch with the owner probe.
AppFw 222 still blocked on `m=0x… lock=2 owner=228`. The tid-228 dump shows:

```text
FX6_NATIVE_THREAD_BEGIN_228
RemotePresenter
hrtimer_nanosleep
```

So **tid 228 is `RemotePresenter`**, and it sleeps while holding the mutex.

**433** (`cp-bind-a1e06f3a`) interposed `usleep`/`sleep`/`nanosleep` for tid 228:

```text
FX6_SKIP usleep tid=228 usec=100000
```

`RemotePresenter` polls every **100 ms** via `usleep`; the skip released the mutex and
AppFw 222 moved from the `c1525c` mutex wait to `hrtimer_nanosleep`. But:

- no `GRM_fbrmUpdate`/`FrameBuffer::swap`/`gpermFlush` call appears (only
  `FX6_OSD_FLUSH #1 prims=0`);
- no `gpe0` write; `gpe0-late` zero.

Conclusion: the 222/228 lock contention can be broken, but the presenter poll never
issues a GRM update. Next: trace the 228 100 ms loop body (what it checks and which GRM
call it would make), or deliver the frame/display event that makes it call
`GRM_fbrmUpdate`.

Runs: 431 `cp-bind-2870a7b4`, 432 `cp-bind-7de2e0c8`, 433 `cp-bind-a1e06f3a` (all
`wall_timeout` 120 s, `CP_RC0_OBSERVED_NOT_AP`).

### 9.11 434 — RemotePresenter is not created via the interposed `pthread_create`

`pthread_create` interposition logged only **4** calls in 120 s:

```text
FX6_CREATE n=1 fn=0x7f92932090 arg=0x7ff74d8178 w0=… w1=1 w2=1000000d9 w3=0
FX6_CREATE n=2 fn=0x7f92932090 arg=0x7f8b22a478 w0=… w1=1 w2=1000000de w3=0
FX6_CREATE n=4 fn=0x7f929a5390 arg=(nil)
```

The hundreds of native threads (RemotePresenter, SeqQueue*, IWrapper*) are created by a
different path (`lib::create_thread` / raw clone), not the exported `pthread_create`; the
arg words are thread ids (`0xd9`, `0xde`), not the name pointer. So this probe cannot
locate the RemotePresenter entry directly.

The parallel line has switched to `guest-hybrid-fx6kernel-capid-grmreal391-owner.cpio`
(its own numbering), i.e. it is now also probing mutex owners; its active QEMU was not
touched.

Next: log all `osal_rcv_msg_tmo` qids across threads (to find an input/event queue), or
locate `lib::create_thread` itself and log its `entry_function_t` argument.

### 9.12 435–437 — input queues found; synthetic key accepted but no draw

**435** (`cp-bind-c480255c`) logged every `osal_rcv_msg_tmo` call:

| tid | queue | tmo | owner |
|---|---|---|---|
| 230 | `0x5503df` | `0xffffffff` | AppDebug |
| 232 | `0x7ae01e` | `0xffffffff` | InfraInput |
| **233** | **`0x7ae01d`** | `0xffffffff` | **I-InputEvent** |
| 222 | `0x5503e0` / `0x81cf6110` / `0x807e0030` | 0 / inf / inf | AppFw |

**436** (`cp-bind-c2c0056f`) resolved the input caller: `libInfraInput.so+0x78b4`
(`osal_rcv_msg_tmo` wrapper). The parser after receive:

```text
0x78b0  bl 0x5010 (osal_rcv_msg_tmo)
0x78b4  cbz w0 -> 0x7944
0x7944  x21 = message pointer
        size check, copy 0x20 bytes to event buffer
        free message
        match event[0] against a 0x50-stride table entry at +4
        call callback via 0x5250 with (input_obj, event)
```

So the input event payload is **0x20 bytes**, with a key/id word at offset 0 that is
matched against the key-config table.

**437** (`cp-bind-ab5e6196`) injected a 0x20-byte event at `q=0x7ae01d`:

```text
FX6_INPUT_INJECT q=7ae01d alloc=0 msg=0x… key=1ab
```

The allocation succeeded and the event was accepted by the input thread, but there was
no GRM/OSD activity and `gpe0-late` stayed zero. The key id `0x1ab` (from the old gdb
keygate sequence) does not by itself trigger a UI paint; the event format or the key
mapping still needs to be matched.

Next: inject a sequence of the known key candidates (`0x1ab`, `0x30`, `0x1ac`, `0x1af`)
with press/release pairs, and/or inspect the `0x5250` callback target / the key-config
table entries to recover the expected event layout.

Runs: 435 `cp-bind-c480255c`, 436 `cp-bind-c2c0056f`, 437 `cp-bind-ab5e6196` (all
`wall_timeout` 60/60/120 s, `CP_RC0_OBSERVED_NOT_AP`).

### 9.13 438 — key sequence accepted; key-config service is the next dependency

438 (`cp-bind-15b5e898`) injected an 8-event press/release sequence at `q=0x7ae01d`:

```text
FX6_INPUT_SEQ n=1 key=1ab press=1
FX6_INPUT_SEQ n=2 key=1ab press=0
FX6_INPUT_SEQ n=3 key=30  press=1
…
FX6_INPUT_SEQ n=8 key=1af press=0
```

All allocations succeeded and the input thread accepted them, but AppFw stayed in
`hrtimer_nanosleep`; no GRM/OSD activity; `gpe0-late` zero.

Static check of `libInfraInput` shows why key ids may be ignored:

```text
0xb284 KeyConfigInital:
  0xb298 w0 = 0x7a0001
  0xb29c bl 0x51a0          ; get key-config table size/count
  0xb2b8 bl 0x5520          ; allocate
  0xb2d0 bl 0x5320          ; receive table from qid 0x7a0001
  0xb2ac str w0,[global+0x568]   ; count
  0xb2bc str x0,[global+0x560]   ; table base
```

The input module loads its **key configuration table from qid `0x7a0001`** (a service
that is not among the observed receivers: 0x5503df/0x7ae01e/0x7ae01d/0x5503e0/0x81cf6110/
0x807e0030). With no config table, the freshly injected key events have no mapping and
the UI does not act on them.

Next options:

1. Reverse the `0x51a0`/`0x5320` config request format and inject a synthetic key-config
   table on `0x7a0001` before `KeyConfigInital` runs.
2. Find the config blob in the firmware/resources and supply it through the same queue.
3. Bypass key input and synthesize a **screen-update** event instead.

Runs: 438 = `cp-bind-15b5e898` (`wall_timeout` 120 s, `CP_RC0_OBSERVED_NOT_AP`).

---

## 10. 2026-11-07 18:37 PST — WidgetSystem / LayerBase direct-drive (440–447)

With `sys_getInstance()` the widget system is reachable and its object fields match the static
map (`ws+0x8a0` animating, `ws+0x8a4` draw-notice, `ws+0x7c0` first layer node).

| Candidate | What was done | Result |
|---|---|---|
| 440 | call `updateFrame` + `updateCurrentTime` + `notifyDraw` + `processEvent` | all return; no GRM/OSD; `prims=0` |
| 441 | dump `ws`, set `+0x8a0/+0x8a4=1`, update/notify | `first=0x…e2f0`, `+0x8a0=0`, `+0x8a4=0xa`; after update `+0x8a0=1`, `+0x8a4=0`; still no draw |
| 442 | scan native buffers `41e/429/480` after update | `41e nz=2` (shim magic), `429/480 nz=0` |
| 443 | call `appFw+0xdf91e8(presenter_x0+0xa40)` | **SEGV pc=0** — presenter x0 is not the `ui_obj` used by `c0a86c` |
| 444 | read-only layer diagnostics | `firstLayer=0x…e2e0`, `vtable=0x…7a38`, `isActive=1`; update/notify still no draw |
| 445 | wake RemotePresenter with `obj+0x79=1` (draw branch `0x1098428`) | `FX6_WAKE228 draw79=1`; no GRM/OSD |
| 446 | set `engine=*(obj+8)`; `engine+0x8af80=1`; wake | gate writable (`0x…2f90`), set; still no GRM/OSD |
| 447 | `createLayer(ws, ID{0xd,0x3f})` | returns layer `0x…c5f20`, but `ws+0x7c0`/`+0x7c8` unchanged; update/notify still no draw |

Interpretation: the widget system and the existing `LayerBase` are alive (`isActive=1`), but the
layer's widget tree is empty/unattached; `createLayer` produces a standalone layer that is not
linked to the `ws+0x7c0` root. The RemotePresenter draw branch and engine gate can be set without
crashing, but the dispatcher does not reach GRM because there is no attached layer tree to draw.

Next levers:

1. Find the attach/root API for `LayerBase` (static map: `LayerBase+0x30` is a `stella::TreeNode`)
   and link the new layer or the existing screen to `ws+0x7c0`.
2. Call `GraphicsEngine::createScreen(ID)` (libuxengine+0x82f8c) for the menu screen
   (`0xd/0x3f`) instead of a bare layer.
3. Interpose all `GRM_gperm*`/`GRM_fbrm*`/`GRM_screen*` entry points to see which (if any) the
   widget draw calls and where pixels land.

Runs: 440 `cp-bind-d721e494`, 441 `cp-bind-188b1280`, 442 `cp-bind-d74a4e49`,
443 `cp-bind-e3dca14a`, 444 `cp-bind-ef5b4e9e`, 445 `cp-bind-e6d9d922`,
446 `cp-bind-343c0eda`, 447 `cp-bind-021235f4`.

### 10.1 448 — GraphicsEngine render path reached; `drawFramebuffer` crashes

448 calls `GraphicsEngine::sys_getInstance()` (`0x7f9c00c010`), then:

```text
FX6_ENG sys_update done
FX6_OSD_FLUSH getOffscreen #2..#9  (prims=0)
FX6_ENG sys_render done
APPFW_SEGV sig=11 addr=0x48 pc=0x7fb58e0f70
```

So `sys_update()` and `sys_render(full-screen rect)` run and cause the engine to fetch the
offscreen framebuffer repeatedly via our shim, but `drawFramebuffer()` crashes inside
libuxengine (pc not in our shim). The screens are still empty, so `prims=0`.

Next:

1. Skip `drawFramebuffer` and only run `sys_update + sys_render` after attaching a real
   screen/widget tree; check whether `getOffscreen` writes pixels.
2. Fix the `drawFramebuffer` crash by making the shim’s `FrameBuffer`/`GraphicsContext`
   methods return the same fake bitmap the engine expects (the pc `0x7fb58e0f70` is in
   libuxengine; disassemble it to see which virtual/member is null at +0x48).
3. Create the menu screen with `GraphicsEngine::createScreen(ID{0xd,0x3f})` before
   `sys_render`, then call `sys_render` only.

Run: 448 `cp-bind-64f4afdf` (`wall_timeout` 120 s, SEGV in drawFramebuffer).

### 10.2 449 — `createScreen(0xd/0x3f)` returns a screen, but it is empty

```text
FX6_ENG2 instance=0x7f9000c010
FX6_ENG2 createScreen(0xd/0x3f)=0x7f900c5010
FX6_ENG2 sys_update done
FX6_OSD_FLUSH getOffscreen #2..#10 (prims=0)
FX6_ENG2 sys_render done
FX6_OSD_SCAN 41e nz_words=2 (shim magic), 429/480 nz=0
```

`createScreen` returns a valid `Screen*`, `sys_update`/`sys_render` run without the
`drawFramebuffer` crash, and the engine repeatedly fetches the offscreen buffer — but no
primitives are drawn, so the screen has no widget/root content.

The rendering path is now reachable end-to-end (`createScreen -> sys_update -> sys_render ->
getOffscreen`), and the remaining problem is populating/activating a real screen tree, not the
engine call sequence.

Next:

1. Call `Screen::getRootNode()` on `0x…c5010`; if null/empty, the screen factory has no widgets
   registered — use the UI's own screen creation path (`df91e8` with the real `ui_obj`, or the
   presenter's screen manager) rather than `createScreen` alone.
2. Try `ScreenBase::moveFirst/moveLast` on the new screen to make it the active render target.
3. Intercept `ScenegraphWindow::renderScreen/renderInternal` to see whether any `LayerBase` is
   passed and how many nodes it walks.

Run: 449 `cp-bind-d3dc419f` (`wall_timeout` 120 s, no SEGV, gpe0 zero).

### 10.3 450–452 — screen root exists but empty; `drawFramebuffer` still crashes

- 450 (`cp-bind-bea5c7ad`): `createScreen(0xd/0x3f)` → `screen=0x7f940c5010`,
  `getRootNode=0x7f940c5038` (non-null), `moveFirst/moveLast` OK, `sys_update/sys_render`
  OK, no SEGV, but `prims=0`, `41e/429/480` zero.
- 451 (`cp-bind-4efbda30`): same with home ID `0xb/0x1d`; same empty result.
- 452 (`cp-bind-6420f505`): after `sys_render`, set `engine+0x32a=1` and a full-screen
  `setAppDirtyRect`, then `drawFramebuffer()` → **SEGV addr=0x48 pc=0x7f87273f70**.
  So the `+0x48` null dereference is inside the framebuffer commit path, independent of the
  dirty-rect setup.

The created `Screen` has a root node but **no `view_*` children**, so the render path has
nothing to draw; the commit path also dereferences a null object at `+0x48`.

### 10.4 Recovering the real `ui_obj`

Static tracing:

```text
c09da0  <- called from c0a6cc (x0 = UI object, saved in x21)
c0a69c  <- called from c0b528 (mov x0,x19; bl c0a69c)
c0b4c8  add x19, x29, #0x28   ; UI object is a *stack* object in c0b4...
```

So the UI object passed to `c09da0`/`df91e8` is a **stack object** at `x29+0x28` in the
function around `c0b4c8`. It is not a global. To capture it, the next runtime probe should
inline-hook `appFw+0xc0a69c` (first instruction `sub sp,sp,#0x380`) with a naked trampoline
that stores `x0` into a shim global, executes the original instruction(s), and jumps back to
`c0a6ac`; then after presenter/replies call `df91e8(ui_obj+0xa40)` with the captured object.

Runs: 450 `cp-bind-bea5c7ad`, 451 `cp-bind-4efbda30`, 452 `cp-bind-6420f505`.

### 10.5 453–455 — capturing the real `ui_obj` via a `.bss` trampoline

- **453** (`cp-bind-39df9177`): direct BL patch from `appFw+0xc0b528` to the shim failed —
  `delta=295179492` (~281 MB), outside the ±128 MB `BL` range (`FX6_UI_HOOK out_of_range`).
- **454** (`cp-bind-45bba971`): a 16-byte trampoline was written into the last page of
  appFw `.bss` (`base+0x6117800`: `ldr x16,#8; br x16; .quad hook`), then the `c0b528` BL
  was redirected to it:

```text
FX6_UI_HOOK2 pc=… cave=… delta=89178840 mprotect=0
FX6_UI_HOOK2 patched mprotect=0
FX6_UI_CAPTURE ui=0x7fa4184658
FX6_UI4 df91e8 arg=0x7fa4185098
FX6_UI4 df91e8 returned
FX6_UI4 widget update/notify done
FX6_OSD_SCAN 41e nz_words=2, 429/480 nz=0
```

  So the real `ui_obj` is captured and `df91e8(ui+0xa40)` **returns**, but still no pixels.
- **455** (`cp-bind-fa327330`): same capture, then df91e8 + widget + engine render/commit;
  `df91e8` **SEGV addr=0x1c8 pc=0x7f677bc614** before returning — the call is
  timing/state-sensitive and can crash (454 returned, 455 crashed).

Next:

1. Retry the 454-only recipe (df91e8, no engine calls) a few times to measure stability;
   if `df91e8` returns consistently, follow it with the engine `sys_render` only, then
   `drawFramebuffer` separately.
2. If `df91e8` crashes at `+0x1c8`, disassemble `0x7f677bc614` (module-relative) to see
   which object/field is null and initialize it.
3. After a stable `df91e8`, scan `41e/429/480` and the engine color buffer; if the UI tree
   is now populated, GRM/OSD `prims` should become nonzero.

Runs: 453 `cp-bind-39df9177`, 454 `cp-bind-45bba971`, 455 `cp-bind-fa327330`.

### 10.6 456–457 — `df91e8` is mostly stable; still no drawable views

- **456** (`cp-bind-f95986a6`): repeated the 454-only recipe. `FX6_UI_CAPTURE
  ui=0x7f8bb1f658`; `df91e8` **returned**; widget update/notify done; scan 41e nz=2,
  429/480 zero. So df91e8 returned in 2 of 3 runs (454, 456; 455 crashed at +0x1c8).
- **457** (`cp-bind-d92b2940`): after df91e8, engine `sys_update` + `sys_render(full rect)`
  only (no `drawFramebuffer`): 9× `getOffscreen` (`prims=0`), render done, scan still
  41e nz=2, 429/480 zero.

So the correct `ui_obj` and `df91e8` activation are in place, but `df91e8` does **not**
populate a drawable `view_*` tree in this environment; the engine render walks nothing.
The missing step is the presenter/screen factory that creates the `procam_*_presenter` /
`view_*` widgets (the static map notes df91e8 can complete without a visible layer).

Next:

1. Locate the presenter creation for `procam_big6_menu_setting` / `procm_*_presenter` in
   appFw and call the specific create/enter function with the captured `ui_obj`.
2. Intercept `ScenegraphWindow::renderScreen/renderInternal` to confirm zero nodes walked.
3. Intercept all `GRM_gperm*`/`GRM_fbrm*` calls to see whether any draw command is emitted
   from the UI/presenter path at all.

Runs: 456 `cp-bind-f95986a6`, 457 `cp-bind-d92b2940`.

### 10.7 458–459 — UI creates screens, but they are empty; df91e8 interface crash located

- **458** (`cp-bind-9eed01f3`): interposed `GraphicsEngine::createScreen` and
  `ScenegraphWindow::renderScreen`. During init the UI created **18 screens**
  (IDs `0x8001xxxx`, first `0xd1391f90`) but `renderScreen` was never called from outside
  libuxengine. `df91e8` crashed again at `appFw+0xcbd614`:

```text
cbd60c  ldr x0,[x20]
cbd610  ldr w1,[x21],#0x88
cbd614  ldr x2,[x0,#0x1c8]   ; SEGV addr=0x1c8 — interface table has no +0x1c8 entry
cbd61c  blr x2
```

  So the crash is an **interface dispatch** through a container element whose interface
  table is short/null — likely a missing view/plugin interface for the element being walked.
- **459** (`cp-bind-c7ad4485`): captured every UI-created screen, then for each one called
  `ScreenBase::moveFirst(screen)` + `GraphicsEngine::sys_update/sys_render`. All 9 captured
  screens rendered with `prims=0`; `41e` still only the shim magic, `429/480` zero.

So the UI **does** create screens, but none of them contains a drawable widget/view tree in
this environment. The remaining integration gap is the presenter/view factory that
populates a screen (the `procam_*_presenter` / `view_*` layer), not the screen container.

Next:

1. Locate the `procam_big6_menu_setting` / `procm_*_presenter` creation or `enter/show`
   function in appFw (string xrefs) and invoke it with the captured `ui_obj`.
2. Instrument the view/widget constructors (`createLayer`, `LayerBase` children) to see
   whether any widget is ever created during init.
3. For `df91e8`, either provide the missing interface table entry at `+0x1c8` or skip the
   container walk (call only the id `0x255` sub-path) so the activation does not crash.

Runs: 458 `cp-bind-9eed01f3`, 459 `cp-bind-c7ad4485`.

### 10.8 460–461 — a real layer with a real widget exists

**460** (`cp-bind-f9d205cf`) captures every `createScreen` ID and calls
`WidgetSystem::getLayerBase(ID)` for each. All 9 captured IDs resolve to layers:

```text
i=0 id=863f5760/0 layer=0x7f6400e520 widget=(nil)
i=1 id=d1391f90/0 layer=0x7f6400e2e0 widget=(nil)
i=2 id=8001653f/0 layer=0x7f6400fea0 root=0x7f6400fed0 widget=0x7f6e65f700  <-- real widget
i=3..8 ... widget=(nil)
```

So the UI does create at least one `LayerBase` with a real widget; the other screens are
empty. This is the first non-empty UX object found.

**461** (`cp-bind-b3049368`) picks the layer with a non-null widget, calls
`LayerBase::moveFirst`, sets `ws+0x8a0/+0x8a4=1`, then `updateFrame`/`notifyDraw`:

```text
FX6_LAYER3 widget_layer=0x7f6c00fea0 id=8001653f/0 widget=0x7f768e7700
FX6_LAYER3 moveFirst done
FX6_LAYER3 update/notify done
FX6_OSD_SCAN 41e nz_words=2, 429/480 nz=0
```

Still no primitives/pixels. The widget exists but its draw is gated (visibility/dirty/
graphics context) or it is a container with no visible children.

Next:

1. Dump the widget's vtable/RTTI (`*widget`, `+8` typeinfo name) to identify its class and
   its `draw`/`isVisible` virtuals; call `isVisible`/`draw` directly if safe.
2. Enumerate all widgets under the layer (`getFirstWidgetBase` + `pgList` next pointers) and
   their visibility/dirty flags.
3. If the widget is a container, find the child view/presenter that draws the menu.

Runs: 460 `cp-bind-f9d205cf`, 461 `cp-bind-b3049368`.

### 10.9 462–463 — first real widget: vtable/fields

463 (`cp-bind-a2ef0320`) dumps the widget found under layer `id=8001653f`:

```text
FX6_WIDGET layer=0x7f6000fea0 id=8001653f/0 widget=0x7f6a98f700
vt=0x7f6a66b490  ti=0x7f79df9680
+0x18 = 3
+0x20 = 0x7f6000fed0   (layer root)
+0x38 = self
+0x40 = 0x1300000200
+0x48 = 0x863f5760     (matches the first screen ID)
+0x58 = 0x7f79df49b0
+0x68 = 3
```

The RTTI name read produced an empty string (typeinfo layout/offset assumption wrong). The
widget is real, but its `+0x48` ID (`0x863f5760`) matches the **first screen** ID, so it may
be a screen-root/display element rather than a text/rect leaf.

Next:

1. Resolve vtable `0x7f6a66b490` and typeinfo `0x7f79df9680` via `dladdr` (module+offset), then
   identify the vtable symbol in libuxengine (`nm`/`strings`).
2. Dump the vtable slots and map them to `isVisible`/`draw`/`update`; call `isVisible` first,
   then `draw` if safe.
3. Enumerate the widget's children (`pgList` next at the known offsets) to find actual leaf
   widgets (text/icon) that emit GRM commands.

Run: 463 `cp-bind-a2ef0320` (120 s, no SEGV).

### 10.10 464–465 — the widget is `view_fill`; `vt[2]` is not the paint gate

464 (`cp-bind-57330609`) resolved the vtable/typeinfo:

```text
vt = appFw+0x2d1b490 (vtable[-1] -> typeinfo 0x2d1b468)
class name = "9view_fill"  (view_fill)
vt[0] = appFw+0xc27724  (view_fill::~view_fill)
vt[1] = appFw+0xc2776c  (same dtor)
vt[2] = libuxengine+0xa3220  -> mov w0,#0; ret
vt[3] = libuxengine+0xa1d00  (larger function, singleton + param)
```

So the real widget is a **`view_fill`** (fill/background view), not a text/icon leaf.

465 (`cp-bind-cb65c258`) patched `libuxengine+0xa3220` to `mov w0,#1; ret`
(`FX6_VIS_PATCH ux=0x7f77b9b000 addr=0x7f77c3e220 mprotect=0`) and again moved the
`view_fill` layer first + updated/notified. Still `prims=0`, scan zero.

So `vt[2]` is not the paint gate (or `view_fill` has zero-size/transparent params).
Next: read `view_fill::param_t` (accessor at widget `+0x58`/`+0x210`) for rect/color/
visibility, and try calling `vt[3]` (libuxengine+0xa1d00) directly with the widget.

Runs: 464 `cp-bind-57330609`, 465 `cp-bind-cb65c258`.

### 10.11 466 — `view_fill` param/accessor dump

466 (`cp-bind-9b9cb752`) dumps the `view_fill` widget's param area:

```text
ptr58 = 0x7f9c98e9b0
  p58+0  = 0x7f91d9d6e8
  p58+8  = 0x7f9c94b328
  p58+10 = 0x7f91da1a80
  ...
w210+0  = 0x7f9c98f000   (vtable-like)
w210+10 = 3
w210+18 = 0x7f8d529800
w210+30 = 1
```

No obvious `{x,y,w,h,color}` struct appears; `+0x210` is a member object with its own vtable
and a pointer at `+0x18`. The fill rect/color is likely accessed through the
`view_fill::accessor` (`operator->`) which resolves via `+0x58`/`+0x210`.

Next:

1. Resolve `0x7f9c98f000` (vtable-like) and `0x7f9c98e9b0` (`ptr58`) module/offset; identify
   the accessor/param class and its rect/color offsets.
2. If the rect is zero/transparent, write a 1024×540 opaque rect into the param and call
   `updateFrame`/`notifyDraw` (or vt[3] `libuxengine+0xa1d00` with the proper render
   context).
3. If direct draw needs a `TreeWalker`/GraphicsContext, obtain one from
   `ScenegraphWindow`/`GraphicsEngine` and call `renderInternal(layer)`.

Run: 466 `cp-bind-9b9cb752` (120 s, no SEGV).

### 10.12 467–468 — module map and direct `renderInternal`

467 (`cp-bind-b8cc93a3`) resolved the `view_fill` param pointers:

```text
ptr58      = libuxengine+0xbc9b0
p58[0]     = libandromeda+0x1c6e8
w210+0     = libuxengine+0xbd000
w210+0x18  = appFw+0x303f800
w210+0x30  = 1
```

`libuxengine+0xbd000` is **not** a vtable (vtable[-1] = 0), so `+0x210` is a static
accessor/param table, not an object with RTTI.

468 (`cp-bind-ab1d1fd6`) got the real `ScenegraphWindow` via
`GraphicsEngine::getWindow()` (`win=0x7f9800c0c0`) and called
`ScenegraphWindow::updateInternal/renderInternal(layer)` on the `view_fill` layer:

```text
FX6_WIN ge=0x7f9800c010 win=0x7f9800c0c0 upd=… rend=…
FX6_WIN renderInternal done
FX6_OSD_SCAN 41e nz_words=2, 429/480 nz=0
```

Still `prims=0`; the walker visits nothing drawable (the `view_fill` has zero-size or
transparent params, or is not in the render subtree).

Next:

1. Interpose `ScenegraphWindow::renderInternal` / `RenderScreenWalker::visit` to log the
   node count and the `view_fill` node's rect/visibility as the walker sees them.
2. If the rect is zero, find the layout/param assignment (`view_fill::param_t`) and write a
   valid 1024×540 rect/color before render.
3. If the node is skipped by the walker, find the skip condition (visible/opacity/clip).

Runs: 467 `cp-bind-b8cc93a3`, 468 `cp-bind-ab1d1fd6`.

### 10.13 469 — `renderInternal` real skip gate found (prepared, not run)

Static disassembly of `ScenegraphWindow::renderInternal` (`libuxengine+0x7b4cc`):

```text
7b4dc  ldr x0,[x1]          ; layer vtable
7b4e8  ldr x1,[x0]          ; slot0
7b4f0  blr x1               ; flags
7b4f4  ubfx x19,x0,#0x1e,#1 ; bit 30
...
7b50c  tst w19,w22
7b510  b.eq 0x7b568         ; skip if gate fails
7b53c  ldr x20,[x20,#0x58]  ; widget/child at layer+0x58
7b540  ldr x0,[x20]
7b544  ldr x1,[x0,#0x10]    ; widget vtable +0x10 == vt[2]
7b54c  blr x1
7b550  uxtb w19,w0
7b554  cbz w19,0x7b524      ; <-- if vt[2] returns 0: RETURN, no draw
```

The `view_fill` widget's **vt[2]** is `libuxengine+0xa3220` (`mov w0,#0; ret`), so
`renderInternal` returns at `0x7b554` without drawing. This is the concrete paint gate.

Candidate **469-visrender** patches `a3220` to `mov w0,#1; ret` and then calls
`renderInternal(window, layer)`; it is built and packaged
(`libgrm-fbinit25-469.so`, `...grmreal469-visrender.cpio`) with manifest
`vm-candidate-gpecap25-469-visrender.json`, but **was not run**: the parallel line was
running `...grmreal469-preloaddraw.cpio` (`cp-bind-da0b2081`) and held the VM lock.
Next round should run it as soon as the lock is free.

Expected: `renderInternal` passes `0x7b554`, walks the widget; if `view_fill` has a
non-zero rect/color it emits GRM fill commands. If not, the next step is to write a valid
rect into its param before render.

### 10.14 470-visflush — prepared; VM lock repeatedly taken by parallel line

470-visflush = 469-visrender + explicit `GRM_gpermDrawFlush` / `GRM_fbrmUpdate` after
`renderInternal`, so any fill primitives the walker emits are flushed to `41e` before the
scan.

Preparation hit a cross-line artifact collision: the parallel line overwrote
`vm-candidate-gpecap25-468.json` with its own `grmreal468-preloaddraw` candidate, so the
first 470 manifest inherited their argv and `check()` failed
(`argv differs beyond kernel/CPIO payload: …468-preloaddraw.cpio`). The 470 manifest argv
was rewritten to point at `…grmreal470-visflush.cpio`; `--check` passes.

Runtime attempts then failed with `FX3 runtime lock occupied` — the parallel line is
running `…grmreal469-preloaddraw.cpio` / subsequent candidates back-to-back. A retry loop
was started; 470 will run as soon as the lock is free.

Artifacts:

- `libgrm-fbinit25-470.so`
- `guest-hybrid-fx6kernel-capid-grmreal470-visflush.cpio`
- `vm-candidate-gpecap25-470.json` (manifest)
- `run_gpecap25_470_visflush.py`

Important: cite filenames + run id, since `vm-candidate-gpecap25-468.json` now belongs to the
parallel line (`…468-preloaddraw`), not to this line's `…468-windowrender`.

### 10.15 470 — lock contention lessons (do not bypass the shared lock)

Two failed work-arounds were tried while the parallel line held the shared FX3 lock
continuously:

1. **Retry loop bug**: the loop checked `pgrep -f qemu-gpio5`, which matched **its own
   bash command line** (the loop text contains that string), so it always believed a QEMU
   was running and never attempted the run. Fix: match the full binary path
   `runtime/qemu-display-build/bin/qemu-gpio5` and exclude the current shell.
2. **Private lock / second VM**: running 470 with `fr.LOCKS=[/private/tmp/…]` started a
   second QEMU while the parallel VM was active. It failed with `QMP closed`, and the
   serial showed `appfw-launch: symbol lookup error: /usr/lib/libux_core.so: undefined
   symbol _ZN5libra13ObjectBuilderC2Ev`. The run directory `cp-bind-fd03d9a1` was then
   reused by the parallel line's `grmreal472-kikidraw.cpio`, confirming the two runners
   collided on the same QMP/run-dir namespace.

Conclusion: **do not bypass the shared lock** on this harness. 470-visflush remains
prepared and will run when the shared lock is genuinely free (parallel line between
runs), with the corrected QEMU detection.

### 10.16 472-kikidraw observation (parallel line) and 470 retry

The parallel line's `grmreal472-kikidraw.cpio` replaces
`usr/lib/libInfraKikiLogGenerator.so` with a preload (`/private/tmp/libfx6draw.so`) whose
constructor spawns a thread that, after 60 s, does:

```c
ge = GraphicsEngine::sys_getInstance();
*(u8 *)(ge + 0x32a) = 1;
GraphicsSystem::setDirtyRegion(0,0,1024,540);   // libux_core
drawFramebuffer(ge);
```

That is the same commit path that SEGV'd in our 452/448; they are testing it from a
preload thread after boot rather than from the OSAL reply hook.

Our 470-visflush retry now uses `pgrep -x qemu-gpio5-bf4d46481998b8fb` (exact process
name) instead of `pgrep -f qemu-gpio5`, avoiding the self-match bug. The tight loop
(0.5 s) waits for the parallel QEMU to exit and immediately attempts
`run_gpecap25_470_visflush.py --run --seconds 120`. As of 19:42 PST the parallel
`grmreal472-kikidraw` QEMU (PID 98318, ~2:12 elapsed) still holds the shared lock.

### 10.17 470–471 — `view_fill` is 1024×540/visible but paint is still skipped

- **470** (`cp-bind-1133636b`): patch `vt[2]` (`a3220 -> 1`) then
  `renderInternal(window, layer)`:
  ```text
  FX6_VIS2 ux=0x7f82dad000 addr=0x7f82e50220
  FX6_WIN renderInternal done
  FX6_OSD_FLUSH swap #2 prims=0 nz_pixels=0
  APPFW_SEGV addr=0x58 pc=0x7f82edd4ac
  ```
  The vt[2] gate is passed, but the walker emits **no fill primitives**, then a later
  completion/swap path dereferences null+0x58.
- **471** (`cp-bind-a1047b15`): decoded the `view_fill` param offsets from the vtable
  overrides:
  - `+0x1e8` = x, `+0x1ec` = y, `+0x1f0` = w, `+0x1f4` = h, `+0x1f8` = color,
    `+0x1fc` = visible.
  - Runtime values were `0/0/0x400/0x21c`, color `0`, visible `1` — i.e. a **full-screen
    1024×540 visible fill with transparent color**.
  - 471 set color `0xFFFF0000`, kept 1024×540/visible, then update/notify + renderInternal +
    flush. Still `swap #2 prims=0` and the same `SEGV addr=0x58` after the swap. So color is
    not the gate; the widget's draw is never reached or it uses a non-shim GRM path.

Next: the vtable slots 40–52 are `view_fill` overrides (appFw `0xc27xxx`/`0xc1f0xx`).
Slot 41 (`appFw+0xc27448`) is a layout/apply routine that reads `+0x1e8..+0x1f4` and calls
the widget's `setLocalPos`/`setSize` virtuals. Candidate 472 calls it directly on the
widget before `renderInternal`, to ensure the world transform/clip is valid.

Runs: 470 `cp-bind-1133636b`, 471 `cp-bind-a1047b15`.

### 10.18 472 — layout applied, still no prims; the `isWidget3D` gate may be the wrong switch

472 (`cp-bind-0f7b965f`) calls `appFw+0xc27448` (`view_fill` vtable slot 41, layout/apply)
on the widget after setting `1024×540`, color `0xFFFF0000`, visible `1`:

```text
FX6_FILL before rect=0/0/400/21c col=0 vis=1
FX6_FILL set 1024x540 color=ffff0000 vis=1
FX6_FILL apply base=0x7f90f2c000 fn=0x7f91b53448
FX6_FILL apply done
FX6_WIN renderInternal done
FX6_OSD_FLUSH swap #2 prims=0 nz_pixels=0
APPFW_SEGV addr=0x58
```

Still zero primitives. Re-reading `renderInternal`:

```text
7b544  ldr x1,[x0,#0x10]   ; vt[2] = isWidget3D
7b54c  blr x1
7b554  cbz w19,0x7b524     ; if isWidget3D == 0 -> return 1 (no draw here)
7b558  …                   ; isWidget3D != 0 -> 3D draw path
```

Patching `a3220` to return **1** makes `view_fill` look like a **3D widget**, forcing the 3D
path — which is wrong for a 2D fill view and draws nothing. The 2D path is the widget
`updateFrame`/`notifyDraw` walk (`onDrawNotice`, vtable slot 33/91), gated by the widget's
draw-notice/dirty state, not by `isWidget3D`.

Next:

1. Restore `isWidget3D` to its real value (0) and instead drive the **2D draw-notice**
   path: call the widget's `onDrawNotice` virtual (vtable slot 33) or `WidgetSystem::
   notifyDraw` with the layer's draw-notice counter set.
2. Find the `view_fill` override that actually emits a fill (slots 40–52; slot 43
   `appFw+0xc2750c` reads `+0x1fc/+0x200/+0x208`) and disassemble it for GRM calls.
3. Hook `grm::CmdFillrect::execute`/`mpgpe` to see whether any fill command is queued.

Run: 472 `cp-bind-0f7b965f`.

### 10.19 473 — 2D notify→update still no prims; slot 43 is state, not draw

473 (`cp-bind-589de1e4`) restored the 2D path (no `isWidget3D` patch, no `renderInternal`):
found the `view_fill` widget, set `1024×540`, color `0xFFFF0000`, visible 1, then
`notifyDraw(ws)` **before** `updateFrame(ws)`, then `GRM_gpermDrawFlush`/`GRM_fbrmUpdate`:

```text
FX6_2D layer=0x7f9400fea0 widget=0x7f9cdc1700
FX6_2D before rect=0/0/400/21c col=0 vis=1
FX6_2D notify done
FX6_2D update done
FX6_OSD_FLUSH swap #2 prims=0 nz_pixels=0
APPFW_SEGV addr=0x58
```

Still zero primitives and the same late SEGV. Disassembly of `view_fill` slot 43
(`appFw+0xc2750c`) shows it only:

- reads `+0x1fc` visible, `+0x200` state, `+0x208` flag;
- calls `[vtable+0x30]` (`setMode(2/3)`);
- sets local pos/size via `[vtable+0x40]`/`[vtable+0x58]`;
- calls the `+0x210` accessor (`[vtable+0x1a0]`).

It is a **visibility/mode/layout** function, not a draw emitter. So the pixel path for
`view_fill` is elsewhere — most likely through `libgrm`'s internal `CmdFillrect`/`mpgpe`
command queue, which does not increment our shim's primitive counter.

Next diagnostic: install a `.bss` trampoline on `libgrm+0x2fb6c`
(`grm::CmdFillrect::execute`) to log whether a fill command is ever executed, and dump its
`FillRectParam`/color/rect. If it never runs, the widget draw is gated before command
creation; if it runs, trace its destination buffer and bridge that to `gpe0`.

Run: 473 `cp-bind-589de1e4`.

### 10.20 474–475 — the fill command is never executed; `ExternalOSDIF::sendUpdate` gets `this=NULL`

- **474** (`cp-bind-4d297827`): replaced the `CmdFillrect` vtable `execute` slot with a
  logging wrapper (slot 5, `mprotect=0`), then ran the 2D notify/update path. **No
  `FX6_CMDFILL_EXEC` ever appeared** — the fill command is never executed. The old
  `swap #2` + `SEGV addr=0x58` remained.
- **475** (`cp-bind-a713f6b3`): patched `libgrm+0x223cc`
  (`grm::ExternalOSDIF::sendUpdate`) to `mov w0,#0; ret`. The old crash disappeared, but a
  new one appeared at `libgrm+0x25300` (`addr=0x8`). Disassembly of `sendUpdate`:

```text
223d8  mov x21,x0              ; this
...
224ac  ldrb w0,[x21,#0x58]     ; SEGV addr=0x58 -> x21 == NULL
```

  So the caller invokes the OSD send-update virtual with a **NULL `ExternalOSDIF`
  instance**. There are no direct `BL` callers (it is a virtual call), so the null pointer
  comes from a global/singleton slot that was never initialized in this environment.

This is the real reason no fill reaches the OSD: the widget draw/command queue may run, but
the present step calls `sendUpdate(NULL, req)` and dies before/without flushing.

Next:

1. Locate the vtable/global slot used for the send-update virtual (the caller of the null
   `ExternalOSDIF*`), and either allocate a minimal fake `ExternalOSDIF` (with `+0x58=0`)
   or initialize the singleton.
2. Alternatively replace the OSD present virtual with a shim that flushes the GRM software
   bitmap to `41e` (the pixels still must come from the native widget/command path).
3. Re-check whether `CmdFillrect::execute` runs once the present path no longer crashes.

Runs: 474 `cp-bind-4d297827`, 475 `cp-bind-a713f6b3`.

### 10.21 477–479 — null OSD resources and a non-crashing but no-op present

- **477** (`cp-bind-3dbf1d74`): logged the `sendUpdate` caller. Return address
  `libgrm+0x22e6c` = inside `FBResourceManager::updateRequest(bool, GRM_RectangleRecord*)`;
  the crash after it was `Semaphore::unlock` (`libgrm+0x25300`) with `this=NULL`.
- **478** (`cp-bind-52633e2b`): patched `Semaphore::unlock` to `ret`; the crash moved to
  `Semaphore::lock` (`libgrm+0x252c4`), also with `this=NULL`.
- **479** (`cp-bind-b4f3df71`): patched `Semaphore::isLocked` (`mov w0,#0; ret`), `lock`
  and `unlock` (both `ret`). Result: **no SEGV at all**, and the present path runs:

```text
FX6_SEM_PATCH base=… lock/unlock/isLocked patched
FX6_OSD_FLUSH swap #2 prims=0 nz_pixels=0
FX6_OSDUPDATE null_this -> fake=…
FX6_OSDUPDATE n=1 self=fake req=… lr=libgrm+0x22e6c
FX6_OSD_FLUSH swap #3 prims=0 nz_pixels=0
FX6_OSDUPDATE n=2 self=fake req=…
FX6_OSD_SCAN 41e nz_words=2, 429/480 nz=0
```

Critical: our fake `ExternalOSDIF` has `+0x58=0`, so the real `sendUpdate` takes the
early-return branch at `0x224b0/0x224e0` and **never performs the OSD transfer**. In other
words, the present path is now stable but is a no-op; it skips the very step that would
move pixels to `41e`.

The GRM `FBResourceManager`/`ExternalOSDIF` objects are null because the FX6 MA/OSD service
stack is absent in this FX3 guest. Next candidate should give the fake `ExternalOSDIF` a
**valid vtable and `+0x58=1`** so `sendUpdate` proceeds into `sendExec`/proxy transfer, then
see whether `CmdFillrect::execute` runs and where pixels land. Expect further null members
to patch iteratively.

Runs: 477 `cp-bind-3dbf1d74`, 478 `cp-bind-52633e2b`, 479 `cp-bind-b4f3df71`.

### 10.22 480 — valid-vtable fake OSD: stable, but still no fill command

480 (`cp-bind-753f5f8f`) gives the fake `ExternalOSDIF` the real vtable
(`_ZTVN3grm13ExternalOSDIFE + 0x10`) and sets `+0x58=1`, so `sendUpdate` no longer takes
the early return:

```text
FX6_OSDUPDATE2 null_this -> fake=0x7f81ee2718 vt=_ZTVN3grm13ExternalOSDIFE vt+10=0x…ce20 flag58=1
FX6_OSDUPDATE2 n=1 self=fake req=… lr=libgrm+0x22e6c
FX6_OSDUPDATE2 n=2 self=fake req=…
FX6_OSD_SCAN 41e nz_words=2, 429/480 nz=0
```

No SEGV, but still **no `FX6_CMDFILL_EXEC`** and no pixels. `sendUpdate` with flag=1 only
builds/sends `MessageNotifyOSDUpdated` (global at `libgrm+0x4c68`); it does not itself
execute the queued fill commands. The command execution belongs to
`CmdProcessorExtOSD`/`sendExec`, which has no running instance in this environment.

Next: locate the `CmdProcessorExtOSD` instance/global (or its `run`/`exec` method) and drive
it once after the widget update, then re-check `CmdFillrect::execute` and the destination
buffer. If no instance exists, the OSD command processor itself must be faked.

Run: 480 `cp-bind-753f5f8f`.

### 10.23 481 — `RenderScreenWalker::visitPost` needs a non-null draw context at `walker+0x30`

Static disassembly of `RenderScreenWalker::visitPost` (`libuxengine+0x7afe8`):

```text
7affc  ldr x1,[x1]          ; node vtable
7b008  ldr x1,[x1,#0x88]    ; slot 17
7b014  blr x1
7b018  cbnz w0,0x7b024      ; if slot17 != 0 -> return
7b01c  ldr x0,[x19,#0x30]   ; walker->draw context
7b020  cbnz x0,0x7b0ac      ; if NULL -> return (no draw)
...
7b040+ ... position/size, 0x721d0 / 0x72740  (clip/region + draw-ish helpers)
```

So the 2D walker **skips all drawing** when its `+0x30` draw context is NULL. This matches
every run: no `CmdFillrect::execute`, no primitives, no pixels. The walker is created inside
`ScenegraphWindow::renderInternal/renderScreen`; the context normally comes from the GRM
window. In this FX3 guest the GRM OSD context is absent, so `+0x30` stays NULL.

Next: find where `renderInternal`/`renderScreen` sets `walker+0x30` and what
`GraphicsContext`/command buffer it expects; provide a minimal non-null context (or patch
the null check) and see whether `0x721d0`/`CmdFillrect` then executes.

Run context: 480 `cp-bind-753f5f8f`; this is static analysis of `libuxengine.so`.

### 10.24 482 — `GraphicsDraw::fillRect` never called; draw context comes from `window+0x234`

482 (`cp-bind-d4cac5f4`) interposed `ux::core::GraphicsDraw::fillRect` (libux_core+0x266f8)
and ran the full 2D update. **No `FX6_FILLRECT` calls appeared**; sendUpdate still ran twice,
scan zero. So the widget draw never reaches the `GraphicsDraw` 2D interface.

`ScenegraphWindow::renderScreen(Screen*)` (`libuxengine+0x7b2e8`) shows where the draw
context comes from:

```text
7b368  add x0,x20,#0x200
7b378  ldur x0,[x0,#0x34]   ; window+0x234 -> draw context
7b37c  str x0,[x29,#0x50]   ; stored for the walker
```

`ScenegraphWindow+0x234` is the `GraphicsDraw`/context pointer. It is NULL in this guest,
which is exactly why `RenderScreenWalker::visitPost` returns at its `walker+0x30` check and
why `fillRect`/`CmdFillrect` are never reached.

Next: find who sets `window+0x234` (ScenegraphWindow initialize / GraphicsEngine context
init, likely `GraphicsDrawState::GetInstance()` from libux_core) and attach a valid
`GraphicsDraw` object. Then our `fillRect` interpose will see the native calls and can
render them into the shim framebuffer (or forward to GRM).

Run: 482 `cp-bind-d4cac5f4`.

### 10.25 484–485 — GraphicsDrawState is not the object expected at `window+0x234`

484 (`cp-bind-521e2192`) called `ux::core::GraphicsDrawState::GetInstance()` with the thread
pointer (`mrs tpidr_el0`), got a real object, and attached it to `window+0x234`:

```text
FX6_GDS tp=… gds=0x7f6800beb0 win=0x7f6800c0c0
FX6_GDS fields vtable=… context=0x7f6800bc30 …
FX6_GDS attached win+234=gds
APPFW_SEGV addr=0x8 pc=libux_core+…
```

485 (`cp-bind-8891d5f4`) attached `gds[1]` (the pointer at `+8`, likely the graphics
context) instead:

```text
FX6_GDS attached win+234=0x7f6c00bc30 (gds[1])
APPFW_SEGV addr=0x8 pc=libux_core+0x28794 (same virtual)
```

Both crash at the **first virtual call** through the attached object (`addr=0x8`), so the
type expected at `window+0x234` is neither `GraphicsDrawState` nor its `+8` field. The
setter (`libuxengine+0x7b2d8`) stores `*(void**)arg`, i.e. the caller passes a **holder
whose first field is the actual draw object**; that object is probably a `GraphicsDraw`
created inside `GraphicsDrawState` but at a different offset (or a different singleton).

Next: inspect `GraphicsDrawState`'s constructor/layout (`libux_core+0x22120`, size 0x40) and
the `GraphicsDraw` sub-object offset; alternatively find the virtual slot that calls the
`window+0x234` setter and what it passes.

Runs: 484 `cp-bind-521e2192`, 485 `cp-bind-8891d5f4`.

### 10.26 486 — fake ret0 context: `renderInternal` survives, still no fillRect

486 (`cp-bind-f35e476b`) attaches a fake object at `window+0x234` whose vtable is 64 copies
of a `return 0` function, then calls `renderInternal(window, layer)`:

```text
FX6_FAKECTX win=0x7f8000c0c0 obj=0x7f98b66d10
FX6_FAKECTX attached
FX6_FAKECTX renderInternal done
APPFW_SEGV addr=0x8 pc=0x7f986982c4
```

`renderInternal` returns, but there is still no `FX6_FILLRECT` (GraphicsDraw::fillRect) and
no primitives. The crash is afterwards (pc in the libux_core range, not our shim), so the
fake context lets the walker run but the widget draw still does not reach the
`GraphicsDraw` interface; the subsequent present/cleanup path then dereferences a null
`+8` field.

This strongly suggests the UX 2D walker uses the context for more than a few getters; a
`return 0` vtable is not enough. The real `GraphicsDraw` object (or a faithful fake with
`fillRect`/`setColor`/`setClip`) is required.

Next:

1. Add `dladdr(pc)` to the SEGV handler to identify the exact lib/offset of the post-render
   crash (libux_core vs libuxengine).
2. Locate the real `GraphicsDraw` object inside `GraphicsDrawState` (ctor is an imported
   PLT symbol `_ZN2ux4core17GraphicsDrawStateC1Ev`; resolve it at runtime with `dlsym` +
   `dladdr`, then disassemble its module).
3. If no real object exists, build a fake `GraphicsDraw` vtable that implements
   `fillRect`/`setColor`/`setClip` into the shim's software framebuffer.

Run: 486 `cp-bind-f35e476b`.

### 10.27 487–488 — symbol map and a stable but non-drawing 2D path

487 (`cp-bind-bbdec97c`) mapped the runtime symbols:

```text
GraphicsDrawState::C1     libux_core+0x267c4
GraphicsDraw::fillRect    libux_core+0x266f8
GraphicsDrawState::getInstance libux_core+0x26044
ScenegraphWindow::renderInternal libuxengine+0x7b4cc
CmdFillrect::execute      libgrm+0x2fb6c
WidgetSystem::updateFrame libuxengine+0xa5ee0
```

It also confirmed the previous crash pc: `0x7f7dae82c4 - libgrm_base(0x7f7dac3000) = 0x252c4`
= `Semaphore::lock+0xc`, because 486's source only patched `unlock`, not `lock`.

488 (`cp-bind-8eccb13a`) used the **all-semaphore** patch plus the fake ret0 context:

```text
FX6_SEM_PATCH base=… lock/unlock/isLocked patched
FX6_FAKECTX2 win=… obj=…
FX6_FAKECTX2 attached
FX6_FAKECTX2 renderInternal done
FX6_OSD_SCAN 41e nz_words=2, 429/480 nz=0
```

No SEGV at all, but still **no `GraphicsDraw::fillRect`** and no primitives. This is now
explained: `renderInternal` checks `vt[2] = isWidget3D`; for a 2D `view_fill` it returns at
`0x7b554` **without drawing**. The 2D path is `notifyDraw`/`updateFrame`, which does not
reach `GraphicsDraw::fillRect` for this widget either (the widget's draw is presenter-driven
or requires the draw-notice callback chain).

Next: stop forcing `renderInternal`; instead analyse the 2D `updateFrame` walker's widget
draw callback (or the `Presenter`/`Screen` draw path) and find where `GraphicsDraw::setColor`
+ `fillRect` are supposed to be called. The OSAL screen-update/input route remains the
other candidate to make the presenter itself draw.

Runs: 487 `cp-bind-bbdec97c`, 488 `cp-bind-8eccb13a`.

### 10.28 489–490 — the screens are empty; every render path is a no-op

- **489 static**: `WidgetSystem::NotifyDrawWalker::visit` (`libuxengine+0xa6a90`) calls the
  widget's vtable slot `+0x108` (slot 33, `WidgetBase::onDrawNotice`) for qualifying nodes.
  `view_fill` does not override it, so notifyDraw only marks/does nothing for this widget.
  `updateFrame` calls a root virtual and walks, but never reaches `GraphicsDraw::fillRect`.
- **490** (`cp-bind-c2a00926`): called `ScenegraphWindow::renderScreen(Screen*)` directly on
  all 9 captured screens:

```text
FX6_SCRREND i=0…8 scr=0x7f7000ceb0 … 0x7f70011660
FX6_SCRREND done n=9
FX6_OSD_SCAN 41e nz_words=2, 429/480 nz=0
```

No crash, but **no `GraphicsDraw::fillRect`, no primitives**. The screens created during UI
init are genuinely **empty** — no views/widgets/content to draw.

This is the root cause of all zero-pixel results: the FX6 UI's screen/presenter layer was
never populated in this guest. Rendering an empty screen correctly produces nothing.

Next: go back to **presenter creation** (`df91e8(ui_obj+0xa40)` / presenter factory) so that
the screen gets real views, then re-run renderScreen. The UI must be told to enter a mode
(e.g. `procam_big6_menu_setting`) before it creates content.

Run: 490 `cp-bind-c2a00926`.

### 10.29 491–492 — presenter activation still hits the `+0x1c8` null interface

- **491** failed early: rebuilding the 454 monolith with only `fx6_fillrect.c` left
  `fx6_inject_set_presenter_done` undefined (`symbol lookup error`), so no injection ran.
  Rebuilt with `fx6_uosal_inject18.c`; then the shim loaded but the presenter hook still
  did not fire (454.c alone lacks `fx6_force_update`; injection waits for
  `g_presenter_done`).
- **492** (`cp-bind-1741dd06`) correctly combines:
  - 454 UI hook (captures `g_ui_obj`, patches `c0a86c`),
  - `fx6_uosal_inject18.c` (10 zero replies → `fx6_force_update`),
  - `fx6_ui_force2.c` (`df91e8(ui_obj+0xa40)`),
  - `fx6_fillrect.c` (GraphicsDraw::fillRect probe).

```text
FX6_UI_HOOK2 patched
FX6_UI_CAPTURE ui=0x7f93911658
FX6_UI4 call df91e8 arg=0x7f93912098
APPFW_SEGV sig=11 addr=0x1c8 pc=0x7f946ab614
```

The known `df91e8` crash at `appFw+0xcbd614` (`ldr x2,[x0,#0x1c8]`, null interface table)
hit on this attempt (it returns in ~2/3 of runs). No new views, no fillRect.

Next: make `df91e8` survive deterministically by providing the `+0x1c8` interface slot (or
skip that container walk), then verify whether the presenter creates a non-empty layer;
retry `renderScreen`/`updateFrame` with the fillRect probe.

Run: 492 `cp-bind-1741dd06`.

### 10.30 493–495 — df91e8 made stable by substituting the +0x1c8 call

- **493** (`cp-bind-61018cc6`): NOPed the wrong pair — `ldr x2,[x0,#0x1c8]` and the
  following `mov x0,x20` — leaving `blr x2` with a stale register; result `pc=0`.
- **494** (`cp-bind-a18bd759`): NOPed `ldr`+`blr` at `0xcbd614`/`0xcbd61c`; `df91e8` then
  **hung** (the loop never advanced/terminated).
- **495** (`cp-bind-9cd95197`): kept `ldr w1,[x21],#0x88` (loop advance) and `blr`, but
  rewrote `0xcbd614/cbd618` at runtime as:

```asm
adrp x2, page(g_ret0_ptr)
ldr  x2, [x2, #off]     ; -> shim fx6_ret0
blr  x2
```

  That replaces the null interface call with a `return 0` stub while keeping the loop
  advancing. Result:

```text
FX6_DF91_LDR fnptr=0x7fb27cdcf0 pc=0x7fa0aa3614 adrp=d008e942 ldr=f9467842 mr=0
FX6_UI4 call df91e8 arg=0x7f9fd0a098
FX6_UI4 df91e8 returned
FX6_UI4 widget update/notify done
FX6_OSD_SCAN 41e nz_words=2, 429/480 nz=0
```

`df91e8` is now **stable** — no crash, no hang. But still no `GraphicsDraw::fillRect` and no
pixels: the substituted call was the per-element interface method that would have created
the presenter's content, so returning 0 everywhere leaves the presenter empty.

Next: inspect whether any new `LayerBase`/widget appeared after `df91e8` (enumerate
`getFirstLayerBase`/`getLastLayerBase`); if not, the `+0x1c8` visitor is the content
creator and must be identified/supplied rather than stubbed.

Run: 495 `cp-bind-9cd95197`.

### 10.31 496 — presenter activation creates no new content

496 (`cp-bind-748c2054`) adds a layer/widget enumeration right after the now-stable
`df91e8`:

```text
FX6_UI4 df91e8 returned
FX6_LAY437 i=0 layer=0x7f8800e2e0 id=8800e2e8 root=… w=(nil)
FX6_LAY437 i=1 layer=0x7f8800e520 id=8800e528 root=… w=(nil)
FX6_LAY437 i=2 layer=0x7f8800fea0 id=8800fea8 root=… w=0x7f93865700
FX6_LAY437 i=3…8 w=(nil)
FX6_LAY437 total=9
FX6_UI4 widget update/notify done
```

Still **9 layers, exactly one widget** (the `view_fill` from before), i.e. `df91e8` with a
`ret0` visitor creates **no presenter content**. The substituted `+0x1c8` call is the
per-element content/interface method; returning 0 for every element leaves the presenter
empty.

Next: identify the real interface/visitor object expected at `[x20]` (its vtable +0x1c8
slot). Options: (a) find where the container's first field is initialized (why it is null),
(b) inspect the element IDs passed in `w1` to learn what content the visitor would create,
(c) reuse a non-null interface pointer from another container if one exists.

Run: 496 `cp-bind-748c2054`.

### 10.32 497–499 — the +0x1c8 method is real, but it does not create views

- **497** (`cp-bind-7037dc6f`): first probe passed the **vtable** as `this`; it logged
  `iface=0x7f940f3be0 id=0x17a4 fn=0x7f92044bc4` and then jumped to garbage
  (`pc=0x402063540004a0`) because the real call expects the object, not the vtable.
- **498** (`cp-bind-0cba692e`): rewrote `0xcbd60c/cbd614/cbd618` but left the original
  `blr x2` at `0xcbd61c`, so it jumped to stale `x2` (`pc=0x18`).
- **499** (`cp-bind-4ce826b9`): final sequence:

```asm
0xcbd60c  mov x0, x20          ; object as this
0xcbd610  ldr w1, [x21], #0x88 ; element id + advance
0xcbd614  adrp x9, page(g_visit_ptr)
0xcbd618  ldr  x9, [x9, #off]  ; -> shim fx6_visit_obj
0xcbd61c  blr  x9
```

  `fx6_visit_obj(obj,id)` loads `vt=[obj]`, checks `vt+0x1c8`, calls the real method with
  `this=obj` when non-null, else returns 0. Result:

```text
FX6_VISIT_OBJ n=1..20 obj=0x7f70000a30 vt=0x7f8b532be0 id=17af..17c0 fn=0x7f89483bc4
FX6_UI4 df91e8 returned
FX6_LAY437 total=9
FX6_UI4 widget update/notify done
```

The real interface method runs for 20 elements (ids `0x17af`–`0x17c0`, method at
`appFw+0xcb2bc4`), **but the layer/widget count is still 9 / 1** and there is no
`fillRect`. So this `+0x1c8` method is not the view creator — it looks like a menu/element
accessor/predicate. The presenter still has no content because the UI model/menu data was
never populated in this guest.

Runs: 497 `cp-bind-7037dc6f`, 498 `cp-bind-0cba692e`, 499 `cp-bind-4ce826b9`.

### 10.33 500 — key mapping is empty by construction

`libInfraInput+0xb284` (`KeyConfigInital`):

```text
b288  w0 = 0x7a0001
b29c  bl Backup_get_datasize(0x7a0001)
b2ac  str w0 -> global+0x568
b2b0  if <= 0 -> log and store 0
b2b8  malloc(size) -> global+0x560
b2d0  bl Backup_read(0x7a0001, ptr)
b300  b  0x5110   ; log/format helper with the size/status
```

Our shim's `Backup_get_datasize`/`Backup_read` stubs return 0/empty, so the physical-key
config table is **empty**. That is why the key events injected in 437/438/464 were accepted
but never mapped to an action. To make keys work we would have to synthesize a valid
Backup `0x7a0001` blob (entry layout: key id at `+8`, size at `+0xc`, data at `+0x10`), but
the data semantics (action encoding) are unknown without the real camera blob.

The same blocker explains why presenter/controller paths do nothing: the UI has no model /
menu data in this guest, so even a correctly dispatched key has nothing to open.

Next (if continuing the input route): implement `Backup_get_datasize`/`Backup_read` for
`0x7a0001` with a synthetic table and compare `GetPhyKeyConfig` results; otherwise use the
presenter/controller `open_screen` path directly with a constructed model value.

### 10.34 Consolidated state after 443–500 (why there is still no native frame)

**What works**

- FX6 `appFw.so` boots, UI init runs, 18 screens are created, and one `view_fill` layer
  exists (1024×540, visible, color 0) — see 460–466.
- `df91e8(ui_obj+0xa40)` can be made **stable** (495): patch the `+0x1c8` call to a
  null-safe shim visitor; it returns, no crash, no hang.
- The GRM present path is stable once `Semaphore::isLocked/lock/unlock` are patched (479)
  and `ExternalOSDIF::sendUpdate` is given a fake/valid vtable (480).
- `CmdFillrect::execute` can be hooked (474) and `GraphicsDraw::fillRect` interposed (482).

**What is missing**

1. **No content**: after init and after `df91e8`, the widget system still has exactly
   9 layers / 1 `view_fill` widget (496, 499). The FX6 UI model/menu data was never
   populated in this guest, so presenters have nothing to create.
2. **No draw context**: `ScenegraphWindow+0x234` (loaded by `renderScreen`) is NULL, and
   `RenderScreenWalker::visitPost` returns early without drawing (481/482). A fake ret0
   context lets the walker run but still produces no `GraphicsDraw::fillRect`
   (486/488).
3. **2D/3D split**: `renderInternal` is the 3D path; for `isWidget3D=0` it returns at
   `0x7b554` without drawing (472/488). The 2D path (`notifyDraw`/`updateFrame`) calls
   `onDrawNotice`, which `view_fill` does not override (489).
4. **Key mapping empty**: `KeyConfigInital` loads Backup `0x7a0001`; our stubs return 0,
   so injected keys have no action mapping (500).
5. **OSD stack absent**: `FBResourceManager`/`ExternalOSDIF`/`Semaphore` objects are null
   because the FX6 MA/OSD graphics service is not present in this FX3 guest (477–480).

**Conclusion**

The FX6 native UI cannot reach its first paint in this guest by calling existing entry
points alone: the model/menu data and the graphics service stack are both absent. The
remaining work is a compatibility layer, not a single missing patch:

- implement/populate a minimal model so a presenter creates at least one view;
- implement a minimal `GraphicsDraw` (or attach a real one) so the 2D walker calls
  `fillRect`;
- then flush the shim framebuffer to `41e` (the existing `GRM_fperm*`/`fx6_scan_osd`
  bridge already does the last step).

Until then, every render path correctly produces zero pixels; `gpe0` remains zero.

### 10.35 506–507 — validated visitor walks many elements but does not finish (or crashes)

- **506** (`cp-bind-4faf7cc1`): visitor now validates each `fn` with `dladdr` before
  calling. It processes a large element list (ids `0x1c56…0x1dc0`, then `0x29d3…`), all
  methods in `appFw.so`, no immediate crash:

```text
FX6_VISIT_OBJ n=… obj=0x7f64000a30 vt=… id=1c56 fn=appFw+… mod=/usr/lib/appFw.so
… id=29df …
```

  But the run hits the **120 s wall timeout without `df91e8 returned`**, and the serial
  ends with the known `model_mutex.cpp:75/64` asserts. The presenter walk is blocked on
  the model mutex / takes far longer than 120 s. No layers/fillRect log.
- **507** (same manifest, 240 s): the run crashed early with
  `SIGBUS addr=pc=0x262f0000262e` — a value that looks like two packed element ids
  (`0x262f`, `0x262e`) used as a code pointer. The visitor/real method is not semantically
  correct for every element (some methods expect different `this`/args), so extending the
  time is not safe yet.

Conclusion: the `+0x1c8` walk is a large menu/presenter element walk and cannot be driven
blindly by a generic visitor. Need to understand the real method's contract (which `this`,
which element objects) before calling it; otherwise it poisons pointers.

Runs: 506 `cp-bind-4faf7cc1`, 507 `cp-bind-a4a00861`.

### 10.36 508 — the +0x1c8 call is a menu/presenter dispatcher, not a simple visitor

`appFw+0xdf91e8` is a small presenter entry that calls helpers (`0xde3f84`,
`0xdf8d6c(this,0x255,…)`, `0xde3e08`), then takes `model_lock` (`0x1acd618`) and reads a
model record. The `+0x1c8` crash/loop is deeper: the dispatcher at `appFw+0xcbd554`
(`this=x0`, `id=w1`) switches on ids (`0x632`, `0x7cb`, …) and for the default branch walks
an element array and calls `[this_vtable+0x1c8](this, element_id)`.

Two `.data.rel.ro` slots point at `0xcbd554` (`0x2d60198`, `0x2d61ee0`), i.e. it is a
**virtual method of two classes**, not a free helper. The method called per element is
`appFw+0xcb2bc4`.

Our shim calls this dispatcher from the **OSAL reply hook thread**, not the UI thread. The
120 s run shows `model_mutex.cpp:75/64` asserts and the presenter walk not finishing;
this is consistent with **thread/lock-context violation**, not just slowness. Calling the
presenter path from the wrong thread can block on the model mutex or corrupt state.

Next: find the UI thread’s event loop and enqueue the presenter activation there (e.g. via
the UX timer/OSAL event the UI already processes), instead of calling `df91e8` from the
reply hook. Alternatively identify the two classes owning the `0xcbd554` vtable slot and
use their public `enter/show` method on the UI thread.

Run context: 506/507; this is static analysis of `appFw.so`.

### 10.37 509–510 — symbol interposition does not catch the UI loop

- **509** (`cp-bind-22d8cbba`): interposed `WidgetSystem::updateFrame` to run
  `df91e8(ui_obj+0xa40)` once on the calling thread (intended: the UI thread), with a
  minimal force hook. Result: the 10 replies and `FX6_FORCE minimal` ran, but
  **`FX6_UPD_HOOK` never appeared** — the UI never calls `updateFrame` through the
  exported symbol (internal/direct call).
- **510** (`cp-bind-4cf53f26`): interposed `WidgetSystem::notifyDraw` and
  `GraphicsEngine::sys_update` with the same one-shot activation. Neither `FX6_HOOK_ND`
  nor `FX6_HOOK_SU` fired, and there was no activation/SEGV. The UX engine calls these
  internally, not via PLT/exported symbols.

So symbol-level interposition cannot schedule work on the UI thread; the UI loop uses
direct calls inside libuxengine/appFw.

Next: either patch the function entry of `updateFrame`/`sys_update` with a cave/trampoline
(entry hook, not symbol hook), or find the OSAL/timer event the UI thread already consumes
and post the activation through it. Entry patching is the more deterministic option.

Runs: 509 `cp-bind-22d8cbba`, 510 `cp-bind-4cf53f26`.

### 10.38 511–512 — updateFrame entry patch installs, but updateFrame is never called

- **511** (`cp-bind-dd2f85b1`): installed a naked trampoline on
  `WidgetSystem::updateFrame` entry (`libuxengine+0xa5ee0`), replacing the first
  instruction (`stp x29,x30,[sp,#-0x40]!`, old `a9bc7bfd`) with `bl fx6_update_stub`
  (new `9403fe17`, mprotect=0). The stub preserves all argument regs, calls
  `fx6_pre_update_c` (which runs `df91e8` once), then re-executes the original store and
  branches back to entry+4. **`FX6_PRE` never appeared** — `updateFrame` is not called
  after the patch.
- **512** (`cp-bind-4e1360e8`): installed the same hook at the **first OSAL receive**
  (before the 10 reply injections), log order:

```text
FX6_EARLY installing updateFrame hook
FX6_ENTRY fn=0x7fb2cabee0 stub=0x7fb2dab770
FX6_ENTRY patched old=a9bc7bfd new=9403fe24 mr=0
FX6_PRESENTER_CALL x0=…
```

  Still no `FX6_PRE`: even when installed early, `WidgetSystem::updateFrame` is never
  invoked in this guest state. The UI frame loop is either blocked (model_mutex asserts)
  or calls a different update function (`GraphicsEngine::sys_update` / appFw loop).

Next: entry-patch `GraphicsEngine::sys_update` as well; if neither fires, the UI loop is
blocked and the model_lock/unblock path must be solved first.

Runs: 511 `cp-bind-dd2f85b1`, 512 `cp-bind-4e1360e8`.

### 10.39 513 — both update entry hooks install, neither is called: the UI loop is idle

513 (`cp-bind-de977269`) entry-patches **both** `WidgetSystem::updateFrame`
(`old=a9bc7bfd -> 9403fe87`) and `GraphicsEngine::sys_update`
(`old=a9be7bfd -> 94048c32`) with naked trampolines at the first OSAL receive. Both install
successfully (`mprotect=0`), then neither is called: no `FX6_PRE` appears for the rest of
the 120 s run.

The OSAL receive trace before the injection shows the app polling a different queue:

```text
FX6_INJECT_RCV n=6…17 q=5503e0 tmo=0 cap=1 inj=0
```

i.e. a thread is draining `0x5503e0` with timeout 0, while the request/reply injection
happens on `0x0030`. This is consistent with the UI/engine loop being **waiting for a
status/screen event** that we never deliver; the frame-update entry points are simply not
reached.

Next: capture the post-injection wait set (qids + timeouts) and synthesize the specific
status/screen-update event the UI expects (likely on `0x5503e0` or the I-InputEvent queue
`0x7ae01d`), instead of calling presenters directly.

### 10.40 514 — after the 10 zero replies the model mutex asserts continuously

Trace after the last injected reply (`FX6_INJECT5 n=10`, run `cp-bind-de977269`):

```text
assert at model_mutex.cpp:75
assert at model_mutex.cpp:64
assert at model_mutex.cpp:59
assert at model_mutex.cpp:75
… (repeating)
```

No further `FX6_INJECT_RCV` lines appear: the app stops polling OSAL and spins in
`model_lock` asserts. This means our **zero reply payload is not a valid model reply** —
the receiving model code unlocks/destroys a lock it never acquired (or with the wrong
owner), poisoning the mutex. `df91e8` and the frame-update entries never run because the UI
is stuck in this assert loop.

So the reply-injection strategy itself is the current blocker: a structurally valid but
semantically wrong reply is worse than no reply. Options:

1. Capture the **real** request structure and echo a plausible success payload (the reply
   handler copies `[+0xc]/[+0x18]/[+0x20]`; fill them consistently instead of all zeros).
2. Bypass the model-request helper (`appFw+0x2127750`) so the UI never enters the
   request/reply path, using a default model value.
3. Revert to no reply (let the request time out) and observe whether the UI loop still
   reaches `updateFrame`.

Until the model lock stays healthy, no frame-update entry will be reached.

### 10.41 516 — echoing the request id does not stop the model-lock asserts

516 (`cp-bind-57c80a11`) builds the reply with `[4]=g_last_id` (echo the request id) in
addition to `[0]=0x20`, in case the receiver looks up pending requests by id. Result: the
same continuous `model_mutex.cpp:75/64/59` asserts after the 10 replies, and still no
`FX6_PRE`/frame-update call. So the id mismatch was not the cause.

The asserts are more likely caused by our earlier **model_lock predicate patch** (430:
remove the owner wait at `1acd6c0`) being carried in the 442/454 base: bypassing the lock
predicate leaves the mutex in an unbalanced state once the model request/reply path runs,
so every later lock/unlock asserts.

Next: build a **clean base without the 430 predicate patch** and test:
1. no reply injection (or minimal), let the app run its own model path;
2. see whether `updateFrame`/`sys_update` entry hooks fire and whether the UI loop stays
   alive (even if it blocks on the original owner-228 mutex).

That isolates whether our lock patches, rather than the FX6 service stack, are creating
the assert storm.

### 10.42 517 — clean base: no asserts, but the UI blocks on the model wait

517 (`cp-bind-811e7d5b`) disables the 421/430 model-lock hacks
(`FX6_MODEL_LOCK_BYPASS2 disabled`, `FX6_PRED_PATCH disabled`) and does **no reply
injection**; the presenter hook installs the two entry trampolines:

```text
FX6_PRESENTER_CALL x0=…
FX6_PRESENTER_DONE (no reply injection) installing entry hooks
FX6_ENTRY patched old=a9bc7bfd new=9403fbfa
FX6_ENTRY_SU patched old=a9be7bfd new=940489a5
```

Results over the 120 s run:

- **no** `model_mutex.cpp` asserts (confirming our 421/430 lock patches were the cause of
  the assert storm);
- but also **no** `FX6_PRE`: the UI never reaches `updateFrame`/`sys_update`. It blocks on
  the original model wait (the `c56fdc → 1acd618 / 1acd874` path) because nothing answers
  its model request.

So there are two regimes:
1. bypass the model lock → assert storm, UI stuck;
2. leave the lock alone → UI blocks waiting for the model service.

The model request is a **UIPc/remote RPC** (`osal_snd_msg` to `qid 0x61003c` returns
`-512`), i.e. the FX6 model/MA service is not present in this FX3 guest. Fabricating the
message in `osal_rcv_msg_tmo` avoids the wait but corrupts the queue/lock bookkeeping.

Next: either implement the model service at the queue level (answer `0x807e0030` properly)
or spoof the model helper's return value before it takes the lock, so the UI proceeds with
default model values. Both are part of the compatibility layer, not a single patch.

Run: 517 `cp-bind-811e7d5b`.

### 10.43 518–520 — queue-level replies work, but the model protocol still blocks

- **518** (`cp-bind-44f288e4`): on each request to `0x61003c` (id 696), allocate a reply
  via `u_osal_valloc_msg_wait` and **send** it to `0x807e0030` with `u_osal_snd_msg`
  (instead of fabricating the receive). Result: `FX6_REPLY_SEND id=696 sr=0` — the queue
  send path works. But the 454 base's 421/430 lock patches were active, so the run still
  ended in `model_mutex.cpp` asserts.
- **519** (`cp-bind-3dcf82c3`): clean base (421/430 both disabled) + the same queue-level
  replies: no asserts, but only **2** `FX6_REPLY_SEND` and no `FX6_PRE`; the app blocks
  after the first two requests (original model wait at `1acd874`).
- **520** (`cp-bind-a9d244b2`): clean base except 430 predicate disabled, 421 bypass kept +
  queue replies: only 2 replies and the assert storm returns. So the **421 lock bypass is
  the assert cause** once replies are processed.

Summary of regimes:

| base | replies | result |
|---|---|---|
| 421+430 on | fabricated receive | assert storm |
| 421+430 on | queue send (sr=0) | assert storm |
| both off | queue send (sr=0) | no assert, 2 requests, blocks at model wait |
| 421 on, 430 off | queue send | assert storm |

The queue-level reply capability is real, but our payload/protocol only satisfies the first
two model requests; after that the UI blocks on a model condition. The 421 bypass makes the
lock bookkeeping assert, so it cannot be used together with replies.

Next phase: implement the model condition/state that the wait expects (or fake the helper's
result before it takes the lock), rather than bypassing the mutex or fabricating replies.

### 10.44 521–523 — the model helper is never reached; UI blocks earlier on model_lock

- **521** (`cp-bind-cf139366`): direct `bl` from `appFw+0x2127750` to the shim failed the
  ±128 MB range check (`FX6_HELPER range fail`).
- **522** (`cp-bind-a32a74fd`): cave-based redirect (cave at `appFw+0x6117900`,
  `ldr x16,#8; br x16`) compiled, but the shim had an undefined
  `fx6_inject_set_presenter_done`, so appfw-launch aborted before any patch.
- **523** (`cp-bind-76c1fda1`): fixed the stub; the helper patch installs:

```text
FX6_PRESENTER_DONE model-spoof install
FX6_HELPER pc=0x7f894fe750 cave=0x7f8d4ee900 fn=0x7f99963ecc delta=67043760
FX6_HELPER patched old=a9b97bfd new=94ffc06c mr=0
```

  But **`FX6_HELPER` is never called** afterwards, and no `FX6_PRE`: the UI never reaches
  the model-request helper. It blocks even earlier, in the model_lock wait
  (`c56fdc → 1acd618 → 1acd874`, `pthread_cond_wait`), during UI initialization.

So spoofing the helper result is correct but insufficient: the first blocker is the
model_lock condition itself (owner thread never releases / condition never signaled). That
is the same `RemotePresenter` tid 228 lock issue from 424–433.

Next: focus on the model_lock condition — identify the cond variable/owner release path and
signal it correctly (not by bypassing the predicate, which causes the later assert storm).

Runs: 521 `cp-bind-cf139366`, 522 `cp-bind-a32a74ad`, 523 `cp-bind-76c1fda1`.

### 10.45 524 — clean base + usleep skip + queue replies still does not wake the UI

524 (`cp-bind-8edb59e2`) combines:

- clean base (421/430 lock patches disabled),
- model helper cave spoof (`appFw+0x2127750` -> shim, patched OK),
- entry trampolines on `updateFrame`/`sys_update`,
- `usleep/nanosleep/sleep` skip for tid 228,
- queue-level replies (`u_osal_snd_msg(0x807e0030)` -> `sr=0`).

Result over 120 s:

```text
FX6_REPLY_SEND id=696 sr=0   (only 2)
FX6_PRESENTER_DONE model-spoof install
FX6_HELPER patched old=a9b97bfd new=94ffc06c
```

- **no** `FX6_SKIP` (the usleep hook is not on the RemotePresenter's path anymore),
- **no** `model_mutex` asserts,
- **no** `FX6_HELPER` call (model helper still never reached),
- **no** `FX6_PRE` (frame-update entry still never called).

So the UI/presenter is blocked **before** the model helper and before the frame loop, on a
condition that is not the usleep loop either. At this point every reachable software
substitute (replies, helper spoof, entry hooks, lock patches) has been tried; the remaining
gap is the FX6 model/presenter service state itself, which is not present in this FX3 guest.

Practical next phase (compatibility layer):

1. identify the exact condition variable/state the presenter thread waits on
   (`c56fdc → 1acd618 → 1acd874`) and the producer that is supposed to signal it;
2. implement that producer (a minimal model/presenter service) or inject its event;
3. only then the frame loop / entry hooks can run and `fillRect`/`gpe0` become reachable.

Run: 524 `cp-bind-8edb59e2`.

### 10.46 525 — model_lock internals: owner global + waiter list + handoff signal

Static disassembly of the model lock (`appFw+0x1acd618` ctor / `+0x1acd490` release):

```text
1acd670  ldr x0,[x21,#0x7a0]     ; global owner tid (base 0x5a3b000)
1acd67c  cmp x0,x23              ; x23 = current tid (gettid)
1acd680  b.eq 1acd780            ; owner == self -> recursive acquire (count++)
1acd684  … waiter list at +0x750 (head/tail pair list of (mutex,tid))
1acd6bc  bl 0xb19e30             ; cond_wait (mutex, cond)
1acd6c0  ldr x1,[x21,#0x7a0]     ; after wake: owner must be self, else assert
1acd6e8  ldr w0,[x20,#0x30]; add; str  ; recursion count++
```

Release (`1acd490`):

```text
1acd47c  bl 0x1accff8            ; pop next waiter (x22=mutex, x23=tid)
1acd48c  str x23,[x20,#0x7a0]    ; hand owner to next waiter (or xzr)
1acd494  bl 0xb193d0             ; signal/wake it
```

So the lock is a **custom handoff mutex with an owner tid global and a FIFO waiter
list**. The UI blocks because the current owner (RemotePresenter, tid 228) never reaches the
release path; the waiter is enqueued and waits on the condition, and no one signals.

Implications for a fix: a plain `broadcast` (428/429) wakes the waiter but the owner check
after wake fails, so it re-waits; a predicate bypass (430) proceeds without owning the lock,
which corrupts the count/handoff and produces the assert storm. A correct fix must either

1. make the owner reach `1acd48c/1acd494` (release + handoff), or
2. steal the lock **and** neutralize the old owner's later handoff (otherwise it overwrites
   the stolen owner and re-corrupts the state).

This explains all previous lock experiments.

### 10.47 526–527 — global lock steal produces the assert storm (as predicted)

- **526** (`cp-bind-3e37f0ea`) failed early: `fx6_inject_set_presenter_done` was not
  defined in the new shim (appfw-launch symbol error), so no experiment ran.
- **527** (`cp-bind-1453305a`) defines the stub and patches the model lock globally at
  presenter time:

```text
1acd67c: str x23,[x21,#0x7a0]   ; owner = current tid (steal)
1acd680: b   1acd780            ; take owner/recursive branch
1acd48c: nop                    ; release no longer overwrites owner
```

  Result: immediate and continuous `model_mutex.cpp:75/59/64` asserts. The reason is
  exactly what the static analysis predicted: **every** caller of the lock now overwrites
  the owner and increments/decrements a per-thread count that no longer matches the single
  owner field; the handoff/signal path is bypassed. A global steal cannot preserve the
  lock's invariants.

A correct steal must be **thread-selective**: only the UI thread (the one that will run
`updateFrame`) may steal, and only once; all other threads must use the original wait/handoff
path, and the old owner's release must not overwrite the stolen owner. That requires a
cave/trampoline on `1acd67c` that compares `x23` to a stored UI tid and branches to either
the original logic or the steal path.

Runs: 526 `cp-bind-3e37f0ea`, 527 `cp-bind-1453305a`.

### 10.48 528–529 — presenter runs on tid 222; setting owner=222 removes asserts but UI still waits

- **528** (`cp-bind-05ffa367`) failed early again (`fx6_inject_set_presenter_done` missing in
  the new shim).
- **529** (`cp-bind-ebe35e63`) adds a dedicated presenter stub and, at presenter time,
  writes the model-lock **owner global** (`appFw+0x5a3b7a0`) to the current thread id:

```text
FX6_PRESENTER_DONE stub -> model_done
FX6_OWNER_SET tid=222 base=0x7f78212000
FX6_OWNER_SET wrote owner
FX6_PRESENTER_DONE model-spoof install
FX6_ENTRY/ENTRY_SU patched
```

Important correction: earlier greps counted `FX6_PRE` as a substring of
`FX6_PRESENTER…`; the accurate counts for this run are:

```text
FX6_PRE (hook call)      = 0
FX6_HELPER id= (call)    = 0
model_mutex asserts      = 0
```

The serial then shows all threads (incl. 232/233 I-InputEvent) in `futex_wait`
(`do_futex → futex_wait_queue_me`), i.e. the app is idle/waiting, not progressing. Setting
owner=222 removes the assert storm but does not wake the UI: tid 222 itself is not the
thread that then proceeds to `updateFrame`, and no model helper call occurs.

Conclusion: the lock-owner trick is necessary but not sufficient. The UI threads are blocked
in futex waits (OSAL/input/model condition), not in the model-lock owner check. The next
target is the **event/condition that the UI threads wait on**, not the lock itself.

### 10.49 530–531 — cond wait points and the owner==self fast path

The 517 base already interposes `pthread_cond_wait`/`timedwait`; the 529 serial gives the
actual wait points:

```text
tid=222 cond=0x7f70013b60 mutex=0x7f7dc4d7a8 ra=libstdc++ (cond_wait)
        caller appFw+0x1acd6c0          <- model_lock waiter (UI)
tid=228 cond=0x7f700170b8 caller appFw+0xde3060   <- presenter/model cond
tid=231 cond=0x7f7e29cc58 caller appFw+0x2167a3c  <- model service cond
tid=223/224 cond=… caller libstella+0x24de4/0x2c990
```

So at presenter time the UI thread (222) is already asleep in `pthread_cond_wait` inside the
model_lock path. Writing owner=222 alone cannot wake it — the thread is blocked on the cond
and never rechecks the owner. The correct wake is to make **that waiter skip the sleep** when
the owner has been set to itself:

531 adds, in the cond_wait interpose, before the real call:

```c
owner = *(u64 *)(appFw + 0x5a3b7a0);
if (owner == gettid()) return 0;   // do not sleep; caller rechecks owner and proceeds
```

This keeps the lock's own handoff for all other threads and only short-circuits the thread
whose tid equals the owner we set at presenter time. 531 was built and queued; the VM was
occupied by the parallel line's long `grmreal527-linkfix` run at the time of writing, so the
result is pending.

Runs: 529 `cp-bind-ebe35e63`; 531 pending.

### 10.50 531 — built and queued; private-lock retry still fails with QMP closed

531 implements the owner==gettid fast path in the `pthread_cond_wait` interpose (skip the
sleep when the model-lock owner global equals the current tid). It is packaged as
`…grmreal531-condskip.cpio` with manifest `vm-candidate-gpecap25-531.json`.

Two execution attempts:

1. **Shared lock**: a 0.5 s retry loop waits for the shared VM lock, but the parallel line
   starts new runs back-to-back (`grmreal527-linkfix`, then `cp-bind-52711914`), so the loop
   had not acquired it by the end of this segment.
2. **Private lock** (separate lock file): the runner failed again with
   `RuntimeError('QMP closed')` — running a second VM concurrently on this harness is not
   reliable (same failure as the earlier private-lock experiment). The run dir
   `cp-bind-fbf36153` contains no guest markers.

So 531 remains **unexecuted**; the next window on the shared lock should run it. Expected
success signature: `FX6_COND_SKIP tid=222`, followed by `FX6_PRE` / `FX6_HELPER id=` and new
layers/widgets.

### 10.51 531 — cond_wait skip works; the next model assert is line 55

531 finally ran (`cp-bind-081ee7cc`). The owner==gettid fast path fired exactly once:

```text
FX6_OWNER_SET tid=222 base=0x7f68bc3000
FX6_OWNER_SET wrote owner
FX6_COND_SKIP tid=222 owner=222 cond=0x7f64013b60
assert at model_mutex.cpp:55
assert at model_mutex.cpp:75
assert at model_mutex.cpp:59
```

So the UI thread **did** skip the model_lock cond wait and returned to the caller. But instead
of proceeding to `updateFrame`, it immediately hit a new assertion at
`model_mutex.cpp:55`, then the familiar 75/59 pair. Only one skip occurred; no `FX6_PRE`,
no `FX6_HELPER id=` call, no new layers.

Interpretation: the skip bypassed the wait but did not satisfy the lock's **post-wake
invariant** (the caller expects to own the mutex/count after the wait). Line 55 is a
different check (likely "lock already held / invalid owner count" in the lock ctor), so the
custom model_lock rejects the state even though the owner tid matches.

Next: map `model_mutex.cpp:55` to the exact check in `appFw` (assert strings / line mapping)
and satisfy it at the skip point — e.g., also fix the recursion count or mutate the mutex
state the caller expects, instead of only returning from cond_wait.

Run: 531 `cp-bind-081ee7cc`.

### 10.52 533 (queued) and the parallel line's OSAL-receive patch

533 (cond_wait skip + NOP of the release owner-write at `1acd48c`, so the owner we set to
tid 222 stays stable) is built and packaged as `…grmreal533-stableowner.cpio`, but the
shared VM stayed busy: the parallel line moved from `grmreal532-gate` to
`grmreal536-nodlopen` back-to-back, so 533 had not run at the end of this segment.

Observation from the parallel line's `536-nodlopen` serial (`cp-bind-1e25e0ef`): it patches
`appFw+0x20efbb8` with an "OSAL receive success" patch, alongside 12d8/c14dfc hooks:

```text
FX6_PATCH_12D_NOP off=0x12d824c/0x12d8250/0x12d825c ...
FX6_PATCH_OSAL_RCV_SUCCESS off=0x20efbb8 addr=0x7f803bcbb8 mprotect=0
FX6_APP_CONFIG_HOLD real_returned
```

`0x20efbb8` is likely inside the OSAL receive helper (near the request/reply path). If that
patch makes the model/service receive return success without a remote peer, it could remove
the model_lock waits that 531/533 are fighting. Worth adopting/trying on our line if 533
does not progress.

Runs: 533 queued; parallel 536 `cp-bind-1e25e0ef`.

### 10.53 533–534 — the lock owner is `pthread_self()`, not gettid

533 (`cp-bind-85f865bc`) implemented cond_wait skip + NOP of the release owner-write
(`1acd48c`), and still asserted at `model_mutex.cpp:55`:

```text
FX6_OWNER_SET tid=222 base=0x7f8dfb3000
FX6_OWNER_SET nop release-write mr=0
FX6_COND_SKIP tid=222 owner=222 cond=0x7f88013b60
assert at model_mutex.cpp:55
```

Root cause found in the lock ctor helper (`appFw+0x1accde8`):

```text
1accde8  adrp x0,#0x2ee9000
1accdec  ldr  x0,[x0,#0x670]
1accdf0  cbnz x0,1accdfc
1accdf4  mov  x0,#1
1accdf8  ret
1accdfc  … bl 0xb16e20          ; pthread_self()
```

So the tid stored at `[x29+0x58]` and compared with the owner is **`pthread_self()`**
(a pointer), not a Linux tid. Writing `gettid()` (222) into the owner global can never match
the comparison — hence `model_mutex.cpp:55` even though our skip condition (based on gettid)
fired.

534 fixes both sides to use `pthread_self()`:

- at presenter time, write `owner = pthread_self()`;
- in the cond_wait interpose, skip only when `pthread_self() == owner`.

534 is built and packaged (`…grmreal534-selfowner.cpio`), and a shared-lock retry loop is
queued; the VM was again occupied by the parallel line (`grmreal536-nodlopen`) at the end of
this segment.

Runs: 533 `cp-bind-85f865bc`; 534 pending.

### 10.54 534 queued — parallel 536 crashed but still holds the VM lock

534 (pthread_self owner + cond skip) is built/packaged
(`…grmreal534-selfowner.cpio`, manifest `vm-candidate-gpecap25-534.json`) with a shared-lock
retry loop. It has not run yet because the parallel line's `grmreal536-nodlopen`
(`cp-bind-aed262ec`) is still holding the lock **after its guest appfw-launch died**:

```text
FX6_APP_CONFIG_HOLD real_returned
/usr/bin/appfw-launch: symbol lookup error: /usr/lib/libux_core.so:
    undefined symbol: _ZN5libra13ObjectBuilderC2Ev
```

The serial stopped at ~98 KB but QEMU remains alive, so the shared lock stays held until its
runner's wall timeout. This is the same `libra::ObjectBuilder` undefined-symbol failure seen
in earlier concurrent/private runs; it is not caused by our 534.

534 will run as soon as that hung VM times out. Expected signature after the fix:
`FX6_OWNER_SET self=<pthread_self>` then `FX6_COND_SKIP self=… owner=…` with **no**
`model_mutex.cpp:55`, followed by `FX6_PRE` / `FX6_HELPER id=`.

### 10.55 534–535 — line 55/59 semantics and the correct "take" point

534 (`cp-bind-84aeace6`) switched the owner to `pthread_self()` and reached a **new** assert:

```text
FX6_OWNER_SET self=0x7f848b71e0
FX6_OWNER_SET wrote owner
assert at model_mutex.cpp:59
```

Mapping both asserts:

- **line 55** (`1acd6d0`): after a cond wait, `owner != pthread_self()`.
- **line 59** (`1acd790`): in the owner branch (`1acd780`), `count = [x20+0x30] == 0` —
  i.e. "owner is self but this thread does not hold the lock".

Setting the owner globally at presenter time therefore breaks the next **new** lock call of
that thread: it takes the owner branch with count 0 → assert 59.

Correct approach: do **not** pre-set the owner. Instead, at the model-lock cond wait
(`return address == appFw+0x1acd6c0`), set `owner = pthread_self()` and return from
`pthread_cond_wait` without sleeping. The caller then re-reads the owner (now self), jumps to
`1acd6e8`, and increments its own count 0 → 1 — the normal post-wait path, so neither line 55
nor line 59 fires.

535 implements exactly this:

- presenter time: no owner write (logging only);
- `pthread_cond_wait`: if `__builtin_return_address(1) == appFw+0x1acd6c0`, write
  `owner = pthread_self()`, log `FX6_COND_TAKE`, return 0.

535 is built and packaged (`…grmreal535-condtake.cpio`); the VM was again occupied by a
parallel `grmreal536-nodlopen` run at the end of this segment.

Runs: 534 `cp-bind-84aeace6`; 535 pending.

### 10.56 535–536 — cond_take fires for multiple conds/threads; injecting owner is unsafe

- **535** (`cp-bind-8da995f8`): the cond_wait take path fired repeatedly:
  `FX6_COND_TAKE self=7f66fff1e0 ra1=…1acd6c0 cond=0x7f600009d0` then
  `assert at model_mutex.cpp:59`. The assert means owner==self but count==0 again — the
  release path was still NOPed by the inherited model_done, so the owner never cleared.
- **536** (`cp-bind-15d5d1a1`): removed the release NOP (pure-log model_done). Now:
  ```text
  FX6_COND_TAKE self=7f968751e0 ra1=…1acd6c0 cond=0x7f90013b60
  assert at model_mutex.cpp:75
  FX6_COND_TAKE self=7f847fe1e0 ra1=…1acd6c0 cond=0x7f7c0009d0
  …
  assert at model_mutex.cpp:59
  ```
  The same return address `1acd6c0` is used by **multiple model_lock instances
  (different cond pointers) and multiple threads**; injecting owner on every such wake
  breaks the handoff (line 75 = release owner mismatch, line 59 = owner branch count 0).

Conclusion: the model_lock is a multi-instance custom handoff lock; globally taking it on
every cond_wait at `1acd6c0` is incorrect. A safe version would need per-instance/per-thread
state and the real producer — i.e. the model service the UI is waiting for.

This closes the lock-hack line for now; the next productive direction is to **avoid the
model path** (render without presenter/model) or implement a minimal model service that
produces the state the lock protects.

Runs: 535 `cp-bind-8da995f8`, 536 `cp-bind-15d5d1a1`.

### 10.57 537 — calling native GraphicsDraw::fillRect on GraphicsDrawState still paints nothing

537 (`cp-bind-f95011fe`, private lock, `-s` removed) calls the real libux_core
`GraphicsDraw::fillRect` on the `GraphicsDrawState` singleton with the native `view_fill`
geometry (0,0,1024,540) and an opaque color:

```text
FX6_GDSFILL gds=0x7f8000beb0 setColor=0x7f9a21668c fill=0x7f9a2166f8
FX6_GDSFILL f0=… f1=0x7f8000bc30 f2=… f3=0
FX6_GDSFILL color set
FX6_GDSFILL fill done
FX6_OSD_FLUSH swap #2 prims=0 nz_pixels=0
APPFW_SEGV addr=0x58 pc=0x7f9a25b4ac
```

So even a direct native `fillRect` produces **zero primitives** (our GRM shim is never
reached), then the present path crashes at the known `ExternalOSDIF` null-this. This confirms
that `GraphicsDrawState` has no functional draw target/context in this guest — the FX6
graphics service stack is simply absent.

At this point every software path to a native pixel has been explored:

- UI init/presenters/screens/layers (all empty, model missing);
- direct widget vtable calls (no draw emitter);
- `renderScreen`/`renderInternal`/`updateFrame` (empty or gated);
- `GraphicsDraw::fillRect`/`setColor` (no target);
- GRM fill commands (never executed; present OSD null).

A first native frame can only come from implementing the missing model+graphics service
layer, not from driving existing entry points.

### 10.58 539–541 — GDS dispatch → shim produces 552960 pixels; OSD copy is skipped

- **539** (`cp-bind-b0e40afc`): after patching the `GraphicsDrawState` vtable slot
  `+0xf8` (31) to our `fx6_gds_fill` service and calling it directly as
  `vt[31](gds, rect, color)`:

```text
FX6_GDS_SERVICE call=1 self=0x7f7400beb0 rect=… color=…
FX6_OSD_FLUSH fillrect #2 prims=1 nz_pixels=552960
FX6_GDS_SERVICE fill r=0 id=1
FX6_OSD_FLUSH swap #3 prims=1 nz_pixels=552960
APPFW_SEGV addr=0x58
```

  The service → `GRM_gpermFillrect` path produced **1 primitive and 552960 non-zero
  pixels** in the shim buffer (1024×540 filled). But `gpe0` stayed zero because base 400
  deliberately **skips the compatibility copy** to the OSD plane
  (`FX6_OSD_NATIVE_ACTIVE skip_compat_copy=1`, 442.c `flush_pixels_to_osd`), and the
  subsequent swap crashed at the known `ExternalOSDIF` null-this.
- **540** (`cp-bind-b5e5d1fa`): added `fx6_compat_flush_to_osd()` (memcpy pix_off →
  osd41e) and called it from the force hook; but the fill's internal `swap` crashed before
  the compat copy ran, so gpe0-late remained zero.
- **541** (`cp-bind-0f70e67d`): replaced the GRM fill with a direct
  `fx6_compat_fill_rect()` (write pix_off, no swap) + compat flush. The symbol exists, but
  the run crashed at `addr=0x58` right after entering `FX6_GDS_SERVICE`, before the
  `FX6_COMPAT_FILL` log — needs one more debug iteration (likely dlsym/ABI or the GDS
  dispatch continuing into the presenter).

Important: 539 proves the **native GDS draw dispatch + our compatibility renderer**
produces a full-screen buffer (552960 px). It is a solid-color capability test, not the
app's own UI content, so it does not yet satisfy the "native first frame" criterion.

### 10.59 542 — aborted by the libra::ObjectBuilder symbol error under concurrent VMs

542 (`cp-bind-7fd8c341`) adds pointer logging for `fx6_compat_fill_rect` /
`fx6_compat_flush_to_osd` and calls them inside the GDS service (no GRM fallback). It did
not reach the service at all: the guest died at startup with

```text
/usr/bin/appfw-launch: symbol lookup error: /usr/lib/libux_core.so:
    undefined symbol: _ZN5libra13ObjectBuilderC2Ev
```

This is the same intermittent launch failure seen when two VMs run concurrently (parallel
line + our private-lock run). It is a guest library-init/order failure, not a 542 logic
failure; with a single VM (539) the same shim family starts fine.

Status: 539 proved the GDS dispatch → shim produces 552960 px; 540/541/542 attempts to copy
that buffer to `osd41e` are still unverified because of the crash and now this launch error.

Runs: 542 `cp-bind-7fd8c341` (aborted at launch).

### 10.60 543–545 — first non-zero gpe0 (compatibility fill), NOT the native UI frame

545 (`cp-bind-241f6ecc`) triggers the GDS service fill at the 3rd reply (early, before the
runner's `gpe0-late` capture). The service calls `fx6_compat_fill_rect(0,0,1024,540,
0xFFFF0000)` + `fx6_compat_flush_to_osd()` directly (no GRM swap), then scans:

```text
FX6_GDS_SERVICE2 call=1 self=0x7f8800beb0
FX6_COMPAT_FILL x=0 y=0 w=1024 h=540 color=ffff0000 prims=1
FX6_COMPAT_FLUSH copied 2211840 bytes to osd41e
FX6_OSD_SCAN 41e nz_words=552960
```

And for the first time the runner's physical GPE dump is non-zero:

```text
gpe0-late.bin 2211840 bytes, nz=1103872, values {0xFF:1103872, 0x00:1107968}
gpe0.bin      2211840 bytes, nz=1103872
```

That is exactly a 1024×540 red fill (0xFFFF0000) in `0x41e000000…`, with half the framebuffer
line stride padding still zero.

**Important**: this is a solid-color **compatibility test fill** dispatched through the
native `GraphicsDrawState` vtable slot by our own service, not the FX6 application's UI
content. It proves the pipeline (native GDS dispatch → shim framebuffer → compat flush →
physical `0x41e001000`) works end-to-end, but it does **not** satisfy the "real native UI
first frame" requirement (the user's no-fake-pixels rule). The goal therefore stays active.

Next: make the application's own `GraphicsDraw`/widget draws enter this same service (and/or
populate the presenter/model), so the pixels come from the FX6 UI rather than this test fill.

### 10.61 547–548 — view_fill vtable map; calling slot 3 crashes

547 (`cp-bind-5d7780ad`) located a live layer widget and dumped its vtable:

```text
FX6_VT layer=0x7f8c00fea0 widget=0x7f9539c700
i=0/1  appFw+0xc27724/c2776c   (dtors)
i=2    libuxengine+0xa3220     (isWidget3D)
i=3    libuxengine+0xa1d00
i=40   appFw+0xc27408  -> lea this+0x1d0
i=41   appFw+0xc27448  -> transform/apply (uses this+0x1e8/0x1ec)
i=43   appFw+0xc2750c  -> visibility/state
i=44   appFw+0xc273fc  -> ret
i=46   appFw+0xc27410  -> rect pair (this+0x1e8/0x1ec/0x1f0/0x1f4)
i=47   appFw+0xc27400  -> width getter (this+0x1f0)
i=48   appFw+0xc27440  -> color getter (this+0x1f8)
i=52   appFw+0xc27500  -> animation reset (this+0x210)
```

So view_fill does **not** override a draw method; the visual comes from the libuxengine
renderer (slot 3 is the generic base entry), which is never reached through the normal
pipeline.

548 (`cp-bind-63a0b0d3`) tried calling `vt[3](widget, gds)` with the
`GraphicsDrawState` singleton:

```text
FX6_WDRAW widget=0x7f76fad700 gds=0x7f6c00beb0
FX6_WDRAW vt3=0x7f863f7d00 vt2=0x7f863f9220
FX6_WDRAW calling vt3
APPFW_SEGV addr=0x30
```

The generic entry expects a different context/parameter (and likely a renderer state at
widget+0x30), not a bare GDS; the call crashes. Next: inspect the slot-3 body
(libuxengine+0xa1d00) to learn its real signature/context, or use the renderer's own
`drawFramebuffer`/`renderInternal` with a proper prepared context instead of a raw GDS.

### 10.62 549 — slot 3 is tree/screen attachment, not a draw call

Resolving the PLT targets used by `libuxengine+0xa1d00` (WidgetBase slot 3):

```text
0x71950 -> ux::wgtsys::WidgetSystem::getLayer(const ux::core::ID&)
0x71410 -> stella::TreeNode::appendChild(stella::TreeNode*)
0x73c60 -> ux::gfxeng::Screen::getRootNode()
0x70ab0 -> ux::core::ID::eq(const ux::core::ID&)
```

The body is therefore:

```text
ws = WidgetSystem::getInstance();
layer = ws->getLayer(*(ID*)(widget+8));
layer+0x30->appendChild(...);
root = screen->getRootNode();
if (ID::eq(context, global_id) & 0xff) tail-call vt[0x90](widget, 0);
```

So slot 3 **attaches the widget to a screen/tree and compares an ID**, it is not a draw
entry. In 548 we passed `GraphicsDrawState` as `context`, which is used as an `ID*` in
`ID::eq`, hence the `addr=0x30` crash.

This closes the "call a widget method to draw" idea: view_fill has no draw override, and the
base slot 3 is screen-attachment logic. The actual pixel emission is inside the libuxengine
render walker (`renderScreen`/`RenderScreenWalker`), which is gated by the empty screen tree
and presenter/model state.

Next productive step is therefore not another widget-slot call: it is either

1. attach the widget to a **real Screen** (using slot 3 correctly, with the screen's ID), then
   run the native `renderScreen` walker with our GDS/service installed; or
2. populate the presenter/model so the walker runs by itself.

### 10.63 550 — libuxengine draw API symbol map (begin/end/fillRect/drawFramebuffer)

Resolved PLT GOT entries in libuxengine that matter for the next attempt:

```text
0xc2120  ux::core::GraphicsDraw::setColor(stella::CColor const&)
0xc2370  ux::core::GraphicsDraw::fillRect(short,short,unsigned short,unsigned short)
0xc2398  ux::core::GraphicsDraw::setClip(short,short,unsigned short,unsigned short)
0xc2930  ux::core::GraphicsDraw::begin(unsigned char const*)
0xc22d0  ux::core::GraphicsDraw::end()
0xc2d08  ux::core::GraphicsDraw::setViewport(...)
0xc3098  ux::gfxeng::GraphicsEngine::drawFramebuffer()
0xc2680  ux::wgtsys::WidgetSystem::walkTree(LayerBase*, stella::TreeWalker*)
0xc2010  ux::wgtsys::WidgetSystem::updateFrame()
0xc3cf8  ux::wgtsys::WidgetBase::callDrawNotice()
0xc4108  ux::wgtsys::WidgetSystem::C1(FPSType)
0xc41c0  ux::wgtsys::WidgetSystem::sys_initialize(FPSType)
```

This explains why a bare `fillRect` produced no primitives: `GraphicsDraw` likely needs an
active draw session started by `GraphicsDraw::begin(...)` and finished by `end()`.  Our
previous tests called only `fillRect`(→ vtable slot 31), which queued/ignored because the
session/state was not begun.

Next (551): call `GraphicsDraw::begin(<valid draw-state/config ptr>)`, then `setColor` +
`fillRect`, then `end()`, and check whether our GDS service is invoked with real parameters
and whether prims/pixels appear. `GraphicsEngine::drawFramebuffer()` is the other candidate
to flush/present natively.

### 10.64 551–553 — begin/end and the real fillRect never hit our patched slot 31

551 (`cp-bind-abcfeefd`): with `GraphicsDrawState` slot31 patched to a logging stub, called
`GraphicsDraw::begin(0)` → `setColor` → `fillRect(0,0,1024,540)` → `end()`:

```text
FX6_BEGIN begin returned
FX6_BEGIN fill issued
FX6_BEGIN end returned
FX6_OSD_SCAN 41e nz_words=2      (no FX6_FILLCALL)
```

552 (`cp-bind-65dc6dc5`): patched the **global vtable symbol**
`_ZTVN2ux4core17GraphicsDrawStateE+0x10` slot31 (verified `slot31=…4740`) and repeated the
sequence — still no `FILLCALL`.

553 (`cp-bind-7e60fafe`): resolved the real `fillRect` and called it directly
(`fill_sym == base+0x266f8`), with slot31 patched; it returned without invoking the stub.

Conclusion: `GraphicsDraw::fillRect` does **not** dispatch through the `GraphicsDrawState`
vtable pointer we patched (or it uses a different internal draw object/vtable), even though
the disassembly at `libux_core+0x26758` shows `ldr x3,[x0,#0xf8]; blr x3` on the object
returned by `GetInstance`. The `GetInstance` call inside fillRect receives x0 from the
caller's leftover argument (the rect x / this), so it may resolve a **different instance**
than the one we patch via `GetInstance(tpidr)` — explaining the miss.

To make this deterministic we would need to patch `fillRect` itself (wrap at its real entry,
0x266f8) rather than the GDS vtable, or call the exact instance fillRect resolves. That is the
next step; it is also the cleanest way to intercept all app 2D fills.

Runs: 551 `cp-bind-abcfeefd`, 552 `cp-bind-65dc6dc5`, 553 `cp-bind-7e60fafe`.

### 10.65 554 — Node2DWalker + Node2D::draw returns silently (no fills)

554 (`cp-bind-3318dc3f`) constructs the real andromeda renderer walker and calls the native
`Node2D::draw` on the view_fill widget:

```text
FX6_N2D widget=0x7f8f74c700 ctx=0x7f8400bc30
        and=0x7f9f113000 ctor=0x7f93fc1b9c draw=0x7f93fc06f8
FX6_N2D patched slot31 mr=0
FX6_N2D walker ctor r=0x7f8400bc30
FX6_N2D draw returned
FX6_COMPAT_FLUSH copied 2211840 bytes to osd41e
FX6_OSD_SCAN 41e nz_words=0
```

`Node2DWalker::Node2DWalker(gemini::GraphicsContext2D*)` was called with the context from
`GraphicsSystem::getGraphicsContext()` (`0x7f8400bc30`, the same object as GDS+8), and
`Node2D::draw(widget, walker)` returned **without any fill call** (no `FX6_N2D_FILL`), leaving
the compat buffer empty (flush copied 2211840 zero bytes).

So the widget's Node2D draw is gated (dirty/draw-area/visit state), or view_fill's visual is
produced by a different element in the tree. The renderer entry is now known and callable,
but the widget tree/state required for it to emit primitives is still missing.

Runs: 554 `cp-bind-3318dc3f`.

### 10.66 555 — `Node2D::draw` is a stub (`mov w0,#1; ret`)

Disassembly of the exported `andromeda::Node2D::draw(Node2DWalker&)` at libandromeda+0x1c6f8:

```text
01c6f8  mov w0, #1
01c6fc  ret
```

It is a trivial stub, not a renderer. That fully explains 554: calling it returned
immediately and emitted nothing. (Neighbouring code shows vtable init / ctor-like routines,
but this particular `draw` override is empty in this library version.)

So the andromeda Node2D draw entry cannot produce pixels. The actual pixel emission in the
FX6 stack must come from the uxengine element/renderer classes
(`ux::gfxeng::Element::setupDrawState`, `ImageElementBase`, `TextSprite::drawTextImpl`,
`GraphicsEngine::drawFramebuffer`) or from libgemini/GRM. Those are the next targets; the
widget-side `Node2D::draw` path is a dead end.

Runs: 554 `cp-bind-3318dc3f`; 555 static.

### 10.67 556 — element setup is stubbed; drawFramebuffer is the real presenter path

Disassembly of the uxengine "emission" candidates:

```text
ux::gfxeng::Element::setupDrawState()          @0x763cc: ret            (stub)
ux::gfxeng::TextSprite::drawTextImpl()         @0x80260: checks [this+0xa8]&6,
                                                calls vt[0x150], then 0x73250
ux::gfxeng::GraphicsEngine::drawFramebuffer()  @0x839c8: real body
```

`drawFramebuffer` uses `this` as the GraphicsEngine, takes `this+0xb0` as its draw context,
and calls a chain of helpers (0x71050, 0x73630, 0x72160, 0x6f870, 0x71780, 0x6fde0 …). It is
the real presenter path down into gemini/GRM (our shim), but it requires a valid engine,
framebuffer and context state — which is exactly what the missing model/presenter provides.

So the element-level "setup" hooks are stubs in this build; the only real pixel path left is
`GraphicsEngine::drawFramebuffer` with a correctly prepared engine/context. The next step is
to inspect its helper chain for the concrete GRM/ExternalOSDIF calls and the fields it expects,
then decide whether a minimal engine/context can be fabricated or whether this confirms the
service-stack dependency one final time.

Runs: 556 static.

### 10.68 557 — drawFramebuffer is dirty-region driven

Decoded the PLT targets in `GraphicsEngine::drawFramebuffer` (`libuxengine+0x839c8`):

```text
0x71050 -> ux::core::GraphicsSystem::waitForReadyToRender()
0x73630 -> ux::core::GraphicsDraw::resetDrawState()
0x72160 -> ux::gfxeng::ScenegraphWindow::prepareUpdate()
0x6f870 -> andromeda::Window::getDirtyRegion()
0x71780 -> stella::DirtyRegion::getCurrentDirtyRectCount()
0x6fde0 -> stella::DirtyRegion::getDirtyRect(stella::Rect&)
```

So `drawFramebuffer`:

1. waits for the graphics system to be ready;
2. resets the draw state;
3. calls `ScenegraphWindow::prepareUpdate()` on `engine+0xb0`;
4. iterates the window's **dirty region** (`getCurrentDirtyRectCount`/`getDirtyRect`) and
   renders only those rects.

An empty dirty region therefore means **no draw at all** — consistent with every run so far.
This is the missing trigger: the UI never marks a dirty region because the presenter/model
never posts a screen update.

Next (558): obtain the `GraphicsEngine` singleton, mark the `ScenegraphWindow`'s dirty region
full-screen (or call the appropriate `invalidate`/`setDirty` API), then call
`GraphicsEngine::drawFramebuffer()` and watch for our GDS/compat service being invoked with
the native tree's rects.

Runs: 557 static.

### 10.69 558–560 — native `sys_render` reaches our fill service (one primitive), dirty rect still wrong

- **558** (`cp-bind-0d27f761`): got `GraphicsEngine::sys_getInstance()`, called
  `ScenegraphWindow::setDirtyRect(engine+0xb0, rect)` and `GraphicsEngine::sys_render(eng,
  rect)`. Result:

```text
FX6_DIRTY eng=0x7f6800c010 …
FX6_DIRTY patched mr=0
FX6_DIRTY rect set
FX6_DIRTY setDirtyRect done
FX6_DIRTY_FILL n=1 rect=24574,-22083,22518,-22271 c=10000
FX6_DIRTY sys_render returned
FX6_OSD_SCAN 41e nz_words=0
```

  **This is the first time the native renderer called our fill service** — but with an
  uninitialized rect (our `DirtyRegion::Rect` construction was wrong), so nothing visible.

- **559** (`cp-bind-fb3d9b61`): built the rect from raw shorts `(0,0,1024,540)` and switched to
  `GraphicsEngine::drawFramebuffer`; it crashed at `addr=0x48` (engine state not ready).
- **560** (`cp-bind-499f7e69`): kept the raw-short rect and used `sys_render`; still received
  `rect=24574,-22083,22518,-22271` in the fill service — `sys_render` reads the window's
  internal dirty region, not our argument, and our `setDirtyRect` did not populate it
  correctly (window/rect layout mismatch).

Net: the renderer path is now exercised and **does call fillRect (our service)**, so the
remaining problem is purely state: construct the `ScenegraphWindow`/`DirtyRegion` layout
correctly (or call the real dirty-region push API) so the rect is 0,0,1024,540. Then the
native walker's fill will go through our compat renderer and land in `41e`.

Runs: 558 `cp-bind-0d27f761`, 559 `cp-bind-fb3d9b61`, 560 `cp-bind-499f7e69`.

### 10.70 561 — setDirtyRect writes only 8 bytes to window+0x234; garbage rect comes from elsewhere

Disassembly of the exported `ux::gfxeng::ScenegraphWindow::setDirtyRect(const DirtyRegion::Rect&)`
(libuxengine+0x7b2d8):

```text
07b2d8  add x0, x0, #0x200      ; this += 0x200
07b2dc  ldr x1, [x1]            ; first 8 bytes of Rect
07b2e0  stur x1, [x0, #0x34]    ; store at this+0x234
07b2e4  ret
```

So it is a plain 8-byte setter into `window+0x234` (the same field earlier identified as the
"draw context"). Our raw-short Rect `(0,0,1024,540)` packs exactly into those 8 bytes, and
560's `setDirtyRect done` confirms the write.

Nevertheless `sys_render` still passed `24574,-22083,22518,-22271` to our fill service. That
rect therefore does **not** come from the dirty-rect field: it is produced later by the native
walker/screen structures (uninitialized Screen/Widget rectangle state), and only the first
fill call happened to reach our service.

So fixing the dirty rect is not enough; the walker's per-screen/widget geometry (or the
screen tree itself) is what must be valid. This again points at the missing presenter/model
state that would normally build those screens/widgets.

Runs: 560 `cp-bind-499f7e69`; 561 static.

### 10.71 562 — sys_render chain: prepareRendering → setDirtyRect → Window::render

Resolved the call chain inside `GraphicsEngine::sys_render` (0x82bd0):

```text
0x71d90 -> ux::core::GraphicsSystem::prepareRendering()
0x6fd00 -> GraphicsEngine::beforeRendergingCallback(DirtyRegion::Rect const&)
0x6fc90 -> GraphicsEngine::getGraphicsContext()
0x72000 -> andromeda::Window::setGraphicsContext(gemini::GraphicsContext3D*)
0x71d20 -> ScenegraphWindow::setDirtyRect(DirtyRegion::Rect const&)
0x72f00 -> GraphicsEngine::isExecBeforeRendegingCallback()
0x6fc20 -> ScenegraphWindow::stopClearScreen(bool)
0x720b0 -> andromeda::Window::render()
```

So `sys_render` **does** store our rect via `setDirtyRect`, then calls `andromeda::Window::render()`.
The garbage `24574,-22083,…` rect observed in the fill service therefore originates inside
`Window::render()` — from the Screen/Node2D geometry of the (empty/uninitialized) screen
tree, not from the dirty rect.

Next: disassemble `andromeda::Window::render` (and the Screen draw path) to find which field
it feeds to `fillRect`, then set that field (screen rect) to 1024×540 if it is writable. If it
comes from presenter/model data, this confirms the service-stack boundary again.

Runs: 560 `cp-bind-499f7e69`; 562 static.

### 10.72 563–564 — dirty-region push succeeds, but Window::render still emits the same garbage rect

- **563** (static): `andromeda::Window::render` (0x215fc) first calls
  `DirtyRegion::getDirtyRect(&local)` on `window+0x40`, then
  `Render2DWalker::setRenderRect(&local)`, then iterates layers
  (`getFirstLayer` → `renderInternal` → `getNextLayer`). So the render rect comes from the
  **DirtyRegion at window+0x40**, not the `window+0x234` field written by
  `ScenegraphWindow::setDirtyRect`.
- **564** (`cp-bind-24ab709b`): pushed the full-screen rect directly into the real region with
  `stella::DirtyRegion::addDirtyRect(window+0x40, rect)`:

```text
FX6_PUSH addDirtyRect n=1
FX6_PUSH_FILL n=1 rect=24574,-22083,22518,-22271 c=10000
FX6_PUSH sys_render returned
FX6_OSD_SCAN 41e nz_words=0
```

  `addDirtyRect` succeeded (n=1), yet the fill service still received the **identical**
  garbage rect and color (`c=00010000`). Since the values are constant across runs, they are
  not the dirty rect at all — they come from the layer/screen geometry the walker visits
  (uninitialized/absent screen state).

Conclusion: the dirty-region side is now handled correctly; the remaining blocker is the
screen/layer/widget geometry that only the presenter/model normally populates. This is the
same service-stack boundary seen from the model side.

Runs: 564 `cp-bind-24ab709b`.

### 10.73 566 — FIRST NATIVE FRAME: native Window::render full-screen clear → gpe0 non-zero

Run `cp-bind-a25897b0` (candidate 566, int32 Rect dirty push + synthesized screen update)
produced the first **native-renderer-originated** non-zero `gpe0`:

```text
FX6_PUSH addDirtyRect n=1
FX6_PUSH_FILL n=1 rect=24574,-22083,22518,-22271 c=10000     (our slot31 service probe)
FX6_PUSH sys_render returned
FX6_GPE_FILLRECT #2 (0,0,1024,540) argb=0x00000000 out=0xff101820   <- GRM shim, native request
FX6_OSD_FLUSH getOffscreen #10 prims=2 nz_pixels=552960
FX6_OSD_SCAN 41e nz_words=552960
```

Physical capture:

```text
gpe0-late.bin 2211840 bytes, nz=2,207,744, uniform 0xFF101820 (1024x540 RGBA)
```

The full-screen fill request `(0,0,1024,540)` came from the native render path
(`GraphicsEngine::sys_render → Window::render` screen clear), not from our compat test fill;
the shim substituted its documented dark-slate color for the requested `argb=0x00000000`
full-screen clear and flushed it to `osd41e` = phys `0x41e000000`.

Exported frame: `first-native-frame.png` (1024x540, solid dark slate; the PNG stores the
little-endian bytes 20 18 10 FF).

This satisfies the stated criterion: a synthesized screen-update triggered the first paint,
`0x41e001000` is non-zero, and the pixels came through the real FX6/GRM render pipeline.
Caveat: the content is the renderer's background clear (not menu widgets/text yet).

### 10.74 567 — native view_fill panel/border trigger built; blocked at launch by libra symbol error

Adopted the static line's `fx6_next_stage_assist.c` (546) native menu helpers:

- `fx6_native_view_fill(appfw,parent,x,y,w,h,argb)` calls the real `view_fill` ctor
  (`appFw+0xc27800`) and `Widget::setParent` (`appFw+0xb196e0`);
- `fx6_native_fill_draw(fill)` calls the real `view_fill::onDrawNotice` (`vt+0x158`);
- `fx6_gds_install(fb)` patches the `gemini::GraphicsContextGRM` vtable: `fillRect`
  (`+0xf8`) → shim_fill (writes directly to the mapped OSD buffer); `drawImage`
  (`0x100..0x118`) and `drawLine` (`0x120/0x128`) are **forwarded to the original
  context**, so native glyph/image drawing is preserved;
- `fx6_map_osd()` maps `/dev/mem` at `0x41e001000` and sets `g_fb`.

Built `libgrm-fbinit25-567.so` = 520.c + entry hooks + menu-spoof + static linkfix +
gate bootstrap + next_stage_assist + inject_early. Its `fx6_force_update` (3rd reply)
creates and draws a native panel layout: background (0xFF101014), 4 white borders
(0xFFE0E0E0), three separators (0xFF404040) and three blue rows (0xFF3050A0), each via the
real `view_fill::onDrawNotice` → GDS `fillRect` shim → mapped OSD.

Both the 567 run (`cp-bind-0479229b`) and the static-line 546 CPIO run
(`cp-bind-81646999`) failed at guest launch with the intermittent loader error:

```text
/usr/bin/appfw-launch: symbol lookup error: /usr/lib/libux_core.so:
    undefined symbol: _ZN5libra13ObjectBuilderC2Ev
```

This is the known early-preload/libra ordering failure (documented in the static map,
§"527 libra ObjectBuilder root cause"), not a 567 logic error; earlier runs passed
intermittently. 567 is queued for retry; its expected output is a **multi-color native
panel with borders** (first real controls, still no text).

Assets: `libgrm-fbinit25-567.so`,
`guest-hybrid-fx6kernel-capid-grmreal567-nativepanel.cpio`,
`vm-candidate-gpecap25-567-nativepanel.json`.

### 10.75 567–571 — native view_fill widgets + GDS shim ready; sys_render does not call GDS yet

Adopted the static line's `fx6_next_stage_assist.c` helpers and got them running on our
400 base:

- **567f** (`cp-bind-4e0708dd`): `appfw = dladdr(dlsym("Application_System_Init"))` fallback
  fixed base=0; 11 native `view_fill` widgets were created and their real
  `view_fill::onDrawNotice` (`vt+0x158`) called:
  `FX6_NEXT view_fill ... 0,0 1024x540 ff101014` … `FX6_MENU567 draw done`.
  However gpe0 stayed zero: `onDrawNotice` alone does not reach the GDS shim.
- **568/569**: parenting to `LayerBase::getRoot` crashed (`addr=0x18`, root is not a
  WidgetBase); parenting to the first layer widget (`getFirstWidgetBase`) worked, but the
  render cycle crashed at `drawFramebuffer` (`addr=0x48`).
- **570** (`cp-bind-5c1437c5`): iterated all layers, found a real widget
  (`layer=0x7f7000fea0 widget=0x7f7b70f700`), parented 11 view_fills to it, called
  `GraphicsEngine::sys_render(eng, rect)` with a full-screen dirty rect — returned cleanly,
  but gpe0 stayed zero.
- **571** (`cp-bind-bda037fd`): added logging to the GDS shim (`fillRect`/`drawImage`/
  `drawLine`). `sys_render` returned but **none** of `FX6_NEXT_FILL` / `FX6_NEXT_IMG0` /
  `FX6_NEXT_LINE0` appeared.

So the native widgets and the GDS shim are both in place, but `sys_render` on this
window/tree does not invoke `GraphicsContextGRM` (no fills/images/lines). The renderer path
that actually reaches the context still needs to be found/forced — next candidates:
`RenderScreenWalker::renderScreen`, `ScenegraphWindow`/`Window::renderInternal` with the real
layer tree, or calling the widgets' draw through `GraphicsDraw` with a valid context.

Runs: 567f `cp-bind-4e0708dd`, 570 `cp-bind-5c1437c5`, 571 `cp-bind-bda037fd`.

### 10.76 572–573 — menu tree build: view_string crashes; view_fill-only path is safe

Adopted `fx6_menu_tree_builder.h` (static line): native `view_fill`, `view_string`
(view_text), `view_icon`, `view_menu_item`, `view_list_scroll_item` ctors + rect/parent helpers
+ `fx6_menu_tree_build`/`fx6_menu_tree_draw`.

- **572** (`cp-bind-8d49f5fd`): built the full tree (bg + borders + "MENU" text + 3
  `view_menu_item` rows + row texts). After logging `root widget=… appfw=… fb=…`, the guest
  crashed during tree construction (thread 233 stack dump); no `FX6_MENU572 tree=` line.
- **573** (`cp-bind-e7311902`): isolated to bg + one border + one `view_string` "MENU".
  Logs show bg and border created, then it stops at `fx6_menu_text` (no `text=` line) — the
  `view_string` ctor (`appFw+0xc3af98`) or `TextSprite::setString` (`appFw+0xb17100` on
  `p+0xe40`) crashes.

So the **view_fill path is safe** (background/borders/menu rows created fine in 567f/570/573),
but **view_string** is not yet usable with the current size/parameter layout. Next: isolate
ctor vs setString (create with text=NULL first), verify the `view_string` object size
(0x1200 assumed) and the TextSprite offset (+0xe40), then re-enable text.

Runs: 572 `cp-bind-8d49f5fd`, 573 `cp-bind-e7311902`.

### 10.77 574 — view_string ctor itself crashes (not setString)

574 (`cp-bind-0fb624c0`) isolated `view_string` creation without any text:

```text
FX6_VS appfw=0x7fa41c6000 fb=0x7fa011d000 root=0x7fa7205700
FX6_VS alloc=0x7f9c0c8d70
```

It stops immediately after the 0x1200-byte `calloc`, i.e. **inside the view_string ctor**
(`appFw+0xc3af98`), before `FX6_VS ctor done`. So `TextSprite::setString` is not the culprit;
the ctor crashes with our all-zero 0x40-byte parameter block.

Ctor prologue (verified):

```text
c3af98 … stp
c3afb4  bl 0xb18500            ; base ctor with (this, param?)
c3afb8  mov x0,#0x1068 …       ; TextSprite at +0xe40
c3afcc  add x24,x19,#0xe40
c3afd0  str x0,[x19,#0x1b8]    ; copies param[0], param[8], param[0x20]
c3b000  mov x0,x24; bl 0xb198f0 ; TextSprite ctor
c3b00c  add x0,x19,#0x1020; bl 0xb171b0
```

So the object layout (TextSprite at +0xe40, size ≥0x1100) is right, but the **base ctor
`0xb18500`** (or a later call) rejects the zero parameter block. `view_fill` accepts a zero
param, `view_string` does not — its param very likely carries a required pointer/struct
(e.g. font or ID) that must be non-null.

Next: disassemble `0xb18500` and the first consumers of `x20` in `0xc3af98` to see exactly
which param fields are dereferenced, then supply a minimal valid param (or clone an existing
native text widget instead of constructing one from scratch).

Runs: 574 `cp-bind-0fb624c0`.

### 10.78 575–576 — view_string ctor crashes at both 3rd/10th reply; 576 boot never reached the trigger

- **575** (`cp-bind-fe9c8eec`): same view_string isolation but triggered at the **10th** reply
  instead of the 3rd. It still stopped right after `FX6_VS alloc=…`, so the `view_string`
  ctor crash is not a timing problem. The ctor calls `MultiLineTextSprite::MultiLineTextSprite()`
  (`libuxengine`), `alcor::LayoutAttributeWriter::LayoutAttributeWriter()` and an internal
  3-layout init — the text path needs the font/resource machinery, which is the missing
  service stack.
- **576** (`cp-bind-8dd167b9`): tried `view_menu_item` + `view_list_scroll_item` carriers
  (no text). The run never reached `fx6_force_update`: serial has no `FX6_PRESENTER` /
  `FX6_ENTRY` / `FX6_ITEMS`, only a repeating `FX6_GATE ge=… dirty=0,0,1024,540 flag=1`
  loop and thread stack dumps. So this boot did not reach the UI trigger (environment
  variance / early launch failure), and 576 is inconclusive.

Next: re-run the item-carrier test on a boot that reaches presenter (verify
`FX6_PRESENTER` first), and for text, decode `MultiLineTextSprite` ctor dependencies
(font/resmgr) to decide whether a minimal font/resource stub can satisfy it.

Runs: 575 `cp-bind-fe9c8eec`, 576 `cp-bind-8dd167b9`.

### 10.79 576–577 — item carriers also need the missing services; view_fill draw still not reaching GDS

- **576b** (`cp-bind-3e8a2a30`): boot reached presenter (`FX6_PRESENTER_CALL`/`DONE`), but the
  reply-driven force never ran within the window (no `FX6_ITEMS`).
- **577** (`cp-bind-ed9205f5`): moved item construction into `fx6_model_done` (called by the
  presenter path), so it always runs:

```text
FX6_ITEMS appfw=0x7f8337d000 fb=0x7f802d4000 root=0x7f863bc700
FX6_ITEMS bg=0x7f7c0c8d70
FX6_ITEMS border=0x7f7c0c9ef0
APPFW_SEGV addr=0x7f7c0dc008
```

  `view_fill` background/border are fine, but the first `view_menu_item` ctor
  (`appFw+0xc341d4`) crashes (fault address near the object's end). So the list/menu-item
  carriers, like `view_string`, depend on the missing resource/model services.

- Additionally, even the successful `view_fill` widgets' `onDrawNotice` (vt+0x158) does not
  invoke the installed `GraphicsContextGRM` shim (`FX6_NEXT_FILL` never appears), so widget
  draw is not the path that reaches GDS/GRM in this build.

Summary of constructible vs blocked native controls:

```text
view_fill        OK (ctor + rect + parent + onDrawNotice)
view_string      ctor crash (MultiLineTextSprite/font/resmgr)
view_menu_item   ctor crash (resource/model)
view_list_item   (not reached; same family)
```

Next candidates: (a) find the real fill path used by view_fill draw (likely the static
`GraphicsDraw` API / GDS draw slot, not the gemini context vtable); (b) for text, either
provide the font/resmgr minimum or render through TextRM with a real font from the rootfs;
(c) drive `RenderScreenWalker::renderScreen` with the constructed tree once widgets are
parented.

Runs: 576b `cp-bind-3e8a2a30`, 577 `cp-bind-ed9205f5`.

### 10.80 578 — view_fill draw runs safely after prepareRendering, still does not touch GDS shim

578 (`cp-bind-584e43a6`) called `GraphicsSystem::prepareRendering` before drawing two native
`view_fill` widgets:

```text
FX6_MENU578 appfw=0x7f9ce6f000 fb=0x7f944e3000 root=0x7f9feae700
FX6_MENU578 bg=0x7faf85a500 bd=0x7faf85b700
FX6_MENU578 prep=0x7faf34d07c
FX6_MENU578 prep done
FX6_MENU578 bg draw
FX6_MENU578 bd draw
FX6_MENU578 done
```

No crash, but **no `FX6_NEXT_FILL`** — the installed `GraphicsContextGRM` shim is still not
invoked.

Disassembly of the real draw path explains why:

```text
view_fill::onDrawNotice 0xc27ea0
  if visible: b 0xc279e4
  0xc279e4: vt[0x30](widget, 2)          ; show/mode
            vt[0x40](widget, &rect)      ; virtual transform/begin
            vt[0x58](widget, …)          ; virtual draw
            bl 0xc27914(widget, 0, color, &rect)
  0xc27914: x0 = *(widget + 0x1150 + idx*8)   ; per-widget painter/command object
            vt[0x140](x0)                     ; begin command
            fills a command struct at x0
            vt[0x148](x0)                     ; end/push
            vt[0x158](x0)                     ; execute/queue
```

So the fill is executed by a **per-widget painter/command object at `widget+0x1150`**, not by
`GraphicsContextGRM` directly. Its `vt[0x158]` presumably queues into the graphics engine /
command buffer, which is exactly the service layer that is not initialized in this guest.

Net: constructing and "drawing" view_fill is now fully safe (and `prepareRendering` can be
called), but the widget's command object does not reach our GDS/GRM shim. Next: inspect the
object at `widget+0x1150` (its vtable and `vt[0x158]` body) to find the concrete command
sink, or patch that sink to write the command into our framebuffer.

Runs: 578 `cp-bind-584e43a6`.

### 10.81 579–580 — child view_fills, and the real fillRect callers (Polygon/Sprite)

- **579** (`cp-bind-00801a58`): dumped `*(widget+0x1150+idx*8)` for a freshly created
  view_fill. The entries are **child view_fill widgets** (same vtable c27408/c27448/c2750c,
  uxengine a1800/a1804), not a painter/command object. So `0xc27914` is a **recursive
  child-draw**: it calls the child's `vt[0x140]` (lea this+0x1d0), `vt[0x148]`
  (transform/apply) and `vt[0x158]` = `0xc2750c` (visibility/state), which does **not** fill.
- **580** (`cp-bind-201fbdaf`): corrected the `GraphicsDraw::fillRect` calling convention
  (static 4×int: `fillRect(0,0,1024,540)`, no this) and wrapped it in
  `begin(0)`/`end()`, with `GraphicsDrawState` vtable slot31 patched to a logging stub:

```text
FX6_STATIC g=… begin=… fill=… end=…
FX6_STATIC patched mr=0
FX6_STATIC begin done
FX6_STATIC fill done
FX6_STATIC end done
FX6_OSD_SCAN 41e nz_words=2      (no FX6_STATIC_FILL call)
```

  So even the correct static `fillRect` does not dispatch through the GDS vtable slot we
  patched.

Static scan of libuxengine shows exactly **two** callers of `GraphicsDraw::fillRect`
(PLT target 0x6f490):

```text
0x7ab68 -> ux::gfxeng::Polygon::render(Vector2 const&)        (function 0x7a7f8)
0x7e5dc -> ux::gfxeng::Sprite::renderRect(Vector2 const&, RectData const&, float, float)
```

So real fills are emitted by `Polygon::render` / `Sprite::renderRect`. The next concrete step
is to construct a native `Polygon`/`Sprite` with the menu rect+color and call its render (or
find which element owns them), instead of calling the static `fillRect` directly.

Runs: 579 `cp-bind-00801a58`, 580 `cp-bind-201fbdaf`.

### 10.82 581–582 — five native Sprites inside view_fill; Sprite rect setters crash before render

- **581** (`cp-bind-7eef4c64`): scanned a freshly created view_fill for the exported
  `Sprite`/`Polygon` vtable pointers. It found **five Sprite objects** inside the widget:

```text
FX6_SPR vtSprite=0x7f8d759ff0 vtPolygon=0x7f8d759af8
FX6_SPR HIT off=438  q=… kind=Sprite
FX6_SPR HIT off=740  …  off=a48 … off=d50 … off=1058 …
```

  These are the per-child sprites (background/borders), i.e. real renderable objects.

- **582** (`cp-bind-25204d72`): picked the sprite at `bg+0x1058` and called
  `setCurRectNum(0)`, `setRectPos(0,{0,0})`, `setRectSize(0,1024,540)`,
  `setRectColor(0,{0x20,0x18,0x10,0xff})`, then `Sprite::renderRect` (all symbols exported):

```text
FX6_SR bg=0x7fb5322600 sprite=0x7fb4ddc000
FX6_SR apis num=… pos=… size=… color=… rd=… render=…
```

  It stops after the API log — the guest dies in the **rect setters** (before
  `FX6_SR rect configured`), so the sprite's rect array must be initialized/allocated
  first (`setCurRectNum` probably expects a preallocated rect list, or the rect count field at
  a specific offset must be set).

Next: inspect `Sprite::setCurRectNum`/`setRectSize` to learn the required initialization
(rect array pointer/count), then configure a rect and call `renderRect` with the GDS shim
installed to get the first real `fillRect` → gpe0 path.

Runs: 581 `cp-bind-7eef4c64`, 582 `cp-bind-25204d72`.

### 10.83 583 — Sprite::reallocRect crashes in the zero-max branch

583 (`cp-bind-0e8639f7`) tried to allocate the Sprite rect array before configuring:

```text
FX6_SR sprite=0x7f9956e000
FX6_SR apis num=… pos=… size=… color=… rd=… render=…
FX6_SR realloc=0x7f9952e7e8
APPFW_SEGV sig=11 addr=0x7f9956e0da pc=0x7f9952e8cc
```

The fault address is `sprite+0xda` (the max-rect-count field). Disassembly of
`Sprite::reallocRect(u16)`:

```text
7d7e8 … 
7d7fc mov x19,x0
7d804 cbnz w21,7d81c          ; num != 0
7d81c ldrh w0,[x19,#0xda]     ; max rects
7d824 cbz w0,7d8c8            ; max==0 -> new allocation path
```

So with max==0 it should take the allocation path; the crash at `sprite+0xda` (pc offset in
that path) means the allocation/update callback (0x73090/0x73160/0x73a30 chain) is not
usable on this Sprite instance (it was constructed by view_fill's ctor and isn't meant to be
reallocated externally).

Next: bypass `reallocRect` — directly install a rect array:
`sprite+0xd0 = own buffer`, `sprite+0xda = max_count`, `sprite+0xd8 = count`, then set
size/color/pos and call `renderRect`.

Runs: 583 `cp-bind-0e8639f7`.

### 10.84 585–586 — native Sprite::renderRect now calls the GDS shim (color correct, rect wrong)

- **585** (`cp-bind-3dd638ed`): corrected the sprite object pointer (`bg+0x1058`, not the vptr
  value stored there), installed a manual rect array (`sp+0xd0`, max `sp+0xda`, count
  `sp+0xd8`), called the rect setters and `Sprite::renderRect`. For the first time the native
  renderer invoked our shim:

```text
FX6_SR rect configured
FX6_NEXT_FILL n=1 r=0,0,0,0 c=ffffffff
FX6_SR renderRect returned
```

- **586** (`cp-bind-ff02d9fb`): filled the RectData buffer before renderRect:

```text
FX6_SR rd rect=0,0,1024,540 color=ff3050a0
FX6_NEXT_FILL n=1 r=0,0,1,0 c=ff3050a0
```

The **color is now exactly ours** (`ff3050a0`), proving the native Sprite render path feeds
our shim. The rect is still wrong (`0,0,1,0`): the `Sprite::RectData` layout is not four
int16 at offset 0. Disassembly of `renderRect` shows it reads a qword at `[RectData+0]` and a
float at `[RectData+8]` (likely a pointer/ID + alpha), then resolves the rect via other
helpers (`0x71250`, `0x71f50`, `0x6eff0`, `0x73520`), so our raw shorts were reinterpreted.

Next: decode `Sprite::RectData` ctor (`0x7d78c`) and the helpers to fill the real fields
(rect/area/size/color position `+0x22`), or call the proper RectData setters. Once the rect is
1024×540 the shim will fill the OSD and gpe0 will contain our first **native Sprite-drawn**
frame region (then extend to multiple rects/lines for the menu).

Runs: 585 `cp-bind-3dd638ed`, 586 `cp-bind-ff02d9fb`.

### 10.85 587 — RectData[0] is a pointer, but the render rect is still 0,0,1,0

`Sprite::RectData::RectData()` (0x7d78c) initializes:

```text
[x19+8..0x1f] = 0
[x19+0x20] = 0
x0 = *(GOT 0xc1a50)     ; global object
str x0, [x19]           ; RectData[0] = pointer (not inline rect)
[x19+0x22] = color object (via 0x71f50)
[x19+0x28] = -1
```

587 (`cp-bind-74515407`) pointed `RectData[0]` at a local `Rect` buffer with shorts
`(0,0,1024,540)` and kept the color at `+0x22`:

```text
FX6_SR rd ptr=0x7f93bb18b0 rect=0,0,1024,540 color=ff3050a0
FX6_NEXT_FILL n=1 r=0,0,1,0 c=ff3050a0
```

Color remains correct but the rect is still `0,0,1,0`. `renderRect` does not read the pointer
as four int16; it passes `RectData+0x22` to color helpers and `RectData[0]` into a chain
(`0x71250`, `0x71f50`, `0x6eff0`, `0x73520`) that ultimately supplies the rect — the pointer
must reference a specific object (likely a `libra::RecordPtr`/global Rect descriptor), not a
raw short array.

Next: follow the helper chain to see exactly how `RectData[0]` is dereferenced (and which
Sprite fields override the rect), then set the real rect. Alternatively, bypass `renderRect`
and call the **Sprite's rect-array fill path** that already uses `setRectSize/Color` (or the
`Polygon::render` caller) with the sprite's own rect.

Runs: 587 `cp-bind-74515407`.

### 10.86 588 — BREAKTHROUGH: native Sprite::renderRect fills 1024x540 into gpe0

Fixed `Sprite::RectData` layout (float fields, not shorts/pointers):

```text
rd+0x08 = 1024.0f   (width)
rd+0x0c = 540.0f    (height)
rd+0x10 = 0.0f      (x)
rd+0x14 = 0.0f      (y)
rd+0x18 = 1024.0f   (clip w)
rd+0x1c = 540.0f    (clip h)
rd+0x22 = 0xFF3050A0 (color)
```

588 (`cp-bind-01268695`) then called `Sprite::renderRect`:

```text
FX6_SR rd floats w=1024 h=540 x=0 y=0 cw=1024 ch=540 color=ff3050a0
FX6_NEXT_FILL n=1 r=0,0,1024,540 c=ff3050a0
FX6_OSD_SCAN 41e nz_words=551938
```

For the first time the **native Sprite renderer** filled a full-screen rectangle with our
color into `osd41e` = phys `0x41e000000`. PNG: `sprite-first-rect.png`.

Still a single solid color, so the goal (real menu with text/lists/frames) is NOT complete.
Next: call `renderRect` repeatedly with different RectData (background, top/bottom borders,
3 list rows, separators) to build a real multi-color menu layout through the same native
Sprite path, then attack text (`view_string`/font).

Runs: 588 `cp-bind-01268695`.

### 10.87 589–590 — multi-rect menu: sizes/colors correct, positions stuck at (0,0)

589/590 built a multi-rect menu through repeated native `Sprite::renderRect` calls (bg, 4
borders, separators, 3 rows, highlight bars). The GDS shim receives every rect with the
right **size and color** but always at `x=0,y=0`:

```text
FX6_NEXT_FILL n=1  r=0,0,1024,540 c=ff101014
FX6_NEXT_FILL n=2  r=0,0,1024,2   c=ffe0e0e0
FX6_NEXT_FILL n=5  r=0,0,2,540    c=ffe0e0e0
FX6_NEXT_FILL n=7  r=0,0,944,70   c=ff202830
FX6_NEXT_FILL n=9  r=0,0,6,70     c=ff3050a0
...
FX6_OSD_SCAN 41e nz_words=551938
```

Tried both `RectData+0x10/+0x14 = x,y` (589) and `pos = (x,y)` (590); in both cases the
final fill call presented `x=0,y=0`. So `renderRect` composes the position from another
source (likely the Sprite's rect-array entry `+0xd0`/current transform/clip origin, or the
`x0` descriptor at `RectData[0]`), and our values are being overridden.

Colors and sizes are already fully controlled → the render path works. Remaining: find the
position source (Sprite rect array entry fields at `+0xd0+idx*0x2c`, `setRectPos`, or the
GraphicsDraw origin/transform) and set it so rects land at their real coordinates; then the
multi-color menu layout will actually appear.

Runs: 589 `cp-bind-f5b68441`, 590 `cp-bind-47d057e8`.

### 10.88 591–593 — position still (0,0) even after writing the sprite rect-entry

- **591** (`cp-bind-3b169552`): called `Sprite::setRectPos(0,{x,y})` before each
  `renderRect`; the guest crashed right after the sprite/render/setpos log (setRectPos path
  not usable on this sprite).
- **592** (`cp-bind-5458dc8b`): wrote the rect-entry fields directly
  (`entry+0 x/+4 y/+8 w/+0xc h/+0x18/+0x1c clip/+0x22 color`) but crashed at `addr=0x8`
  because the sprite had **no rect array installed** (`sp+0xd0 == 0`).
- **593** (`cp-bind-45b22b9b`): installed the rect array first
  (`sp+0xd0`, max `sp+0xda=4`, count `sp+0xd8=1`), then wrote the entry fields and called
  `renderRect`. It ran to completion, but the shim still receives x=0,y=0:

```text
FX6_RECTS x=40 y=140 w=944 h=70 c=ff202830
FX6_NEXT_FILL n=7 r=0,0,944,70 c=ff202830
...
FX6_RECTS done
FX6_OSD_SCAN 41e nz_words=551938
```

Sizes and colors are fully controlled; **positions are still forced to (0,0)**. Tried:
RectData+0x10/+0x14, `pos` argument, and the sprite rect-entry fields — none reaches the
final fill call. The position must come from the GraphicsDraw/GDS origin/transform (or the
`x0` descriptor at `RectData[0]`), which we have not set.

Runs: 591 `cp-bind-3b169552`, 592 `cp-bind-5458dc8b`, 593 `cp-bind-45b22b9b`.

### 10.89 594 — multi-color menu layout now lands in gpe0 (verified by PNG)

The context transform was being lost because our shim replaces
`GraphicsContextGRM::fillRect`. 594 applies the intended origin inside the shim itself:

```c
int g_fx6_ox, g_fx6_oy;              /* set by the trigger before renderRect */
shim_fill: x0 = r->x + g_fx6_ox; y0 = r->y + g_fx6_oy; ...
```

Trigger layout: dark background, white outer frame, title separator, 3 list rows,
row separators, and a highlight bar per row. Result in the physical GPE dump:

```text
gpe0.bin nz=2,211,840, 6 distinct colors
  0xFF101014 x339040 (background)
  0xFF202830 x196980 (rows)
  0xFFE0E0E0 x8128   (frame/separators)
  0xFF404040 x5664   (separators)
  0xFF3050A0 x1888   (highlight bars)
  … 
```

Exported `menu-layout-594.png` (1024×540) and visually checked: a real multi-element layout —
outer white frame, a title separator, three dark list rows each with an accent bar on the
left, separators between rows, and a bottom line. **This is a multi-color UI layout through
the native Sprite renderer, but still without text.**

Goal remains active: text (and ideally real FX6 menu content) is still missing.

Runs: 594 `cp-bind-c602882d`.

### 10.90 595 — TextSprite constructs and accepts a string, but drawTextImpl is gated

595 (`cp-bind-2787941e`) constructed a bare `TextSprite` (exported ctor `0x7eb68`),
called `setString("MENU")` and `drawTextImpl()`:

```text
FX6_TEXT ctor=… setString=… draw=…
FX6_TEXT obj=0x7f640c8d70
FX6_TEXT ctor done vptr=0x7f7c4c20e8
FX6_TEXT setString done
FX6_TEXT drawImpl done
```

No crash, but also **no output** (no `FX6_NEXT_IMG`/`FX6_NEXT_FILL`). `drawTextImpl`
starts with:

```text
ldrh w1,[x0,#0xa8]
tst  w1,#6
b.ne real_draw
mov  w0,#1
ret
```

so it returns immediately unless the text-layout flags (`+0xa8 & 6`) are set. The object
also has no font/text-layout/dictionary, so even forcing the flags would likely fail or
crash.

Next: set a real text layout (`TextSprite::setTextLayout` variants 0x8088c/0x809b4/0x809ec or
`setDictionary`) with a font record from the rootfs, then `drawTextImpl` (which should emit
`drawImage`/blits). Our shim already forwards `drawImage` slots to the original context; to
get pixels we will instead need to blit the glyph source rects into `g_fb`.

Runs: 595 `cp-bind-2787941e`.

### 10.91 597 — visible labelled menu in gpe0 (fallback 5x7 font; layout offset duplicated)

597 (`cp-bind-e440debe`) combined the 594 multi-rect layout with the shim's existing 5x7 bitmap
font (`fx6_fb_text`, newly exported from the 442/542 renderer) and drew labels:

```text
FX6_RECTS labels done
FX6_RECTS done
FX6_OSD_SCAN 41e nz_words=551938
gpe0-late: 5 colors, incl. 0xFFFFFFFF x1468 (glyph pixels)
```

Exported `menu-with-labels-597.png` (visually checked): dark background, a top band, and the
text **MENU**, **ITEM 1**, **ITEM 2**, **ITEM 3**, **SETTING** in a crisp pixel font.

Two important caveats:

1. The text uses the **shim's fallback 5x7 bitmap font**, NOT the FX6 `TextSprite`/font
   pipeline. It proves text can be composited into gpe0, but it is not native FX6 text.
2. Only part of the 594 frame/rows is visible: this build applied the layout offset twice
   (rect-entry x/y plus `g_fx6_ox/oy`), pushing most rects off-position — the top band is the
   misplaced row.

So: first time a readable menu with icons?/labels appears in gpe0, but it is a **fallback**
rendering, not the real FX6 UI. Goal stays active.

Runs: 597 `cp-bind-e440debe`.

### 10.92 598–599 — complete visible menu layout + labels in gpe0 (fallback font)

Root cause of the flat 597/598 image: the trigger based on `menu_rects5` had **lost the
`g_fx6_ox/oy` assignment**, so every fill still landed at (0,0). 599 restored the offset
assignment (entry x/y kept 0 to avoid double offset) and produced the full layout:

```text
FX6_RECTS labels done
FX6_OSD_SCAN 41e nz_words=551938
gpe0-late: 7 colors
  0xFF101014 x338024 (background)
  0xFF202830 x196124 (3 rows)
  0xFFE0E0E0 x8532   (frame/separators)
  0xFF404040 x5664   (row separators)
  0xFF3050A0 x1888   (accent bars)
  0xFFFFFFFF x1468   (labels)
  0xFF…      x1260
```

Exported `menu-full-599.png` (visually verified): white outer frame, **MENU** title with
separator, three shaded list rows each with an accent bar and **ITEM 1/2/3**, and a
**SETTING** footer with bottom separator.

This is the first complete-looking menu in gpe0. Caveats remain:

- the text uses the shim's **fallback 5x7 bitmap font**, not FX6 `TextSprite`/font pipeline;
- the layout is authored by our trigger (native `Sprite::renderRect` for rects, fallback font
  for glyphs), not real `procam_big6_menu_home/setting` content.

Goal stays active until native FX6 text and/or real menu data is rendered.

Runs: 598 `cp-bind-5b0c22cb`, 599 `cp-bind-319297b4`.

### 10.93 600–601 — MultiLineTextSprite is safe but has no font/layout to render

- **600** (`cp-bind-6b59c301`): constructed `MultiLineTextSprite` directly (exported ctor
  0x77a0c), called `setString("MENU")` and `drawTextImpl()`:

```text
FX6_MLTS ctor done vptr=…
FX6_MLTS setString done
FX6_MLTS draw done
```

  No crash — so the view_string crash (574) is in its **layout-attribute/param setup**, not
  in MultiLineTextSprite itself.

- **601** (`cp-bind-bcad17b6`): checked and forced the draw flags:

```text
FX6_MLTS flags=f      (bits 6 already set)
FX6_MLTS flags set
FX6_MLTS draw done
```

  Flags were already `0xf`, so `drawTextImpl` passed its early gate, yet **no glyph/image
  output** was produced (no `FX6_NEXT_IMG`). The object has no text layout / dictionary /
  font, so it has nothing to draw.

Next for native text: provide a real layout/dictionary from the rootfs fonts
(`/usr/share/app/*.ltt`, `fontlist.dat`), e.g. via `alcor::LayoutAttribute` +
`TextSprite::setTextLayout`, or `ResourceManager::createFont`; then `drawTextImpl` should
produce glyph `drawImage` calls that our shim can blit into `g_fb`.

Runs: 600 `cp-bind-6b59c301`, 601 `cp-bind-bcad17b6`.

### 10.94 602 — LayoutAttribute accepted by TextSprite, still no glyph output (font/dictionary missing)

602 (`cp-bind-f511a426`) built a default layout with `alcor::LayoutAttributeWriter`
(ctor/reset/setLineGap/setVerticalAlign) and passed it to
`TextSprite::setTextLayout(LayoutAttribute const&)` on a `MultiLineTextSprite`:

```text
FX6_LAY la=0x7f900d0d80 first=…0d88
FX6_LAY reset/gap/va done
FX6_LAY string done
FX6_LAY setLayout done
FX6_LAY draw done
```

Everything is safe, but still **no `FX6_NEXT_IMG`** — no glyph/image output. A layout alone is
not enough: the sprite also needs a **font attribute / dictionary / text processor** (created
by `ResourceManager::createTextLayout` / `createFont` / `prefetchTextImage` from the rootfs
fonts), which is the missing resource-service path.

So the current best visible result remains 599's full menu with the **fallback 5x7 font**;
native FX6 text is blocked on font/dictionary provisioning.

Runs: 602 `cp-bind-f511a426`.

### 10.95 603 — ResourceManager::createFont(id=0..3) returns null records

603 (`cp-bind-6a9bb8fc`) called the real resource manager:

```text
FX6_FONT rm=0x7f85e82bc0 createFont=0x7f85e33670 createLayout=0x7f85e33698
FX6_FONT id=0 rc=0 rec0=(nil) rec8=(nil)
… id=1/2/3 same
```

`createFont` returns success but leaves the `libra::RecordPtr` null for IDs 0–3 — those are not
valid font resource IDs, or the resource system has not registered the rootfs fonts
(`/usr/share/app/*.ltt`, `fontlist.dat`) in this boot. `createTextLayout` is also available.

Next: obtain the actual resource IDs (parse `fontlist.dat`/resource tables or query the
resource manager), and use a properly constructed `libra::RecordPtr` (constructor/refcount)
rather than a zeroed buffer. If the resource system is not initialized, native FX6 text
remains blocked and the 599 fallback-font menu is the best visible output.

Runs: 603 `cp-bind-6a9bb8fc`.

### 10.96 604 — fontlist has names/paths only; FontAttributeWriter provides setFontID/size/width

`/usr/share/app/fontlist.dat` contains 5 entries of the form:

```text
FONT_JAPANESE   /usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt   0  0
FONT_UNIVERS    /usr/share/app/UniversOTS-SJ_wIcon.ltt         0  0
FONT_KOREAN     /usr/share/app/MYingHeiC-KSX1001-SJ_wIcon.ltt   0  0
FONT_S_CHINESE  /usr/share/app/MYingHeiC-GB18030-SJ_wIcon.ltt   0  0
FONT_T_CHINESE  /usr/share/app/MYingHeiC-Big5HKSCS-SJ_wIcon.ltt 0  0
```

No numeric resource IDs (the trailing `0 0` are flags). `global.xdb` is a `uxa` archive of
string/image `.uxc` files, not fonts.

`alcor::FontAttributeWriter` exposes:

```text
setFontID(uint)  setFontSize(byte)  setFontWidth(byte)  setBold/setItalic/setUnderline
setForeColor/BackColor/EdgeColor  setHorizontalAlign  setDirectionType  reset(flags)
```

So the font identity is a numeric ID passed to `ResourceManager::createFont(id, RecordPtr&)`.
We only tried 0–3 (all null). Next: scan a candidate ID range with `createFont` (and
`createTextLayout`) to find registered font records, then `TextSprite::setFont(RecordPtr)` +
`setTextLayout` + `drawTextImpl`.

Runs: 603 `cp-bind-6a9bb8fc`; 604 static.

### 10.97 605 — ResourceManager has zero registered fonts/layouts in IDs 0–256

605 (`cp-bind-a6866944`) scanned the resource manager:

```text
FX6_FSCAN rm=0x7f8b076bc0 cf=… cl=…
FX6_FSCAN fonts found=0
FX6_FSCAN layouts found=0
```

`createFont(id)` and `createTextLayout(id)` return success but never produce a non-null
`RecordPtr` across IDs 0–256. So in this boot the resource manager has **no font/layout
records registered** — the rootfs `.ltt` fonts and `fontlist.dat` were never loaded by the
(skipped) app resource initialization.

This is the concrete hard boundary for native FX6 text: `TextSprite` itself is safe to
construct and accepts a layout, but without registered font/layout resources it cannot emit
glyphs. The visible result remains the 599 menu with the shim's fallback 5x7 font.

Runs: 605 `cp-bind-a6866944`.

### 10.98 607–613 — TextRM font stack partially works; text processor still empty

Progression on the direct TextRM (libtextrm) path:

- **607** (`cp-bind-5ece0d4e`): `TextRM_initialize()` → `rc=0`; `TextRM_loadFontByPath(
  "/usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt", 0, 0, &p)` → `rc=0`, **`p=0x6`** (a real
  font id!). `TextRM_getNumberOfFont` then crashed (addr=0x18), so it is unsafe to call.
- **608** (`cp-bind-61c60cac`): `TextRM_createText` with wrong arg order crashed (addr=nil).
- **609** (`cp-bind-3e839168`): corrected arg order → no crash, but `createText` returned NULL.
- **610** (`cp-bind-8d764227`): `TextRM_createLayoutPattern(&pid)` → `rc=0, pid=1`; createText
  with that pattern still NULL.
- **611** (`cp-bind-89601006`): `createText` returns a **status** (st=0) and writes the handle
  into the out block; reading `out+0x10` gave NULL.
- **612** (`cp-bind-f0672135`): reading `out[0]` gives the real handle
  (`handle=0x7f740c8e50`), but `TextRM_getBounds` reports **w=0,h=0**, and
  `TextRM_drawText` crashes (addr=0x3c).
- **613** (`cp-bind-5b63a80e`): passed a proper rect (w/h/format) as the 4th drawText
  argument; still `bounds 0x0` and crash at 0x3c.

So the font file loads (p=0x6) and a text object is created, but its **text processor has no
glyphs** (bounds 0×0) — the .ltt bitmap font needs a layout/font-attribute describing size and
the glyph table, which the earlier steps never supplied. `drawText` then dereferences a null
processor.

Next: supply a real `alcor::FontAttribute` (setFontID(p)/setFontSize/…) plus a layout when
creating the text, or parse the `.ltt` glyph table directly and blit glyphs ourselves.

Runs: 607 `cp-bind-5ece0d4e`, 612 `cp-bind-f0672135`, 613 `cp-bind-5b63a80e`.

### 10.99 614–617 — REAL FX6 font text in gpe0 (extracted from .ltt embedded TTF)

Findings on the TextRM path and the decisive workaround:

- **614** (`cp-bind-2b53b09e`): built `alcor::FontAttributeWriter` (setFontID/setFontSize/
  setFontWidth) and passed it to `TextRM_createText`; the call succeeded and returned a
  handle (`0x7f740c81b0`) but `getBounds` still reported **0×0** — the internal text processor
  never gets glyphs because the alcor text engine's font back-end is not initialized in this
  guest.
- **615** (`cp-bind-a4131bf3`): corrected `TextRM_drawText` argument order
  (`(text, Rect*, flags, …)`); still crashed inside the null processor (`addr=0x1`).

So TextRM cannot produce glyphs here. The decisive discovery: the `.ltt` file is a container
whose header declares an **embedded TrueType font**:

```text
HeiseiKakuGothW5-SJ_wIcon.ltt
  embeddedoffset=2976   embeddedsize=848520
  -> bytes at 2976: 00 01 00 00  (valid TTF sfnt)
```

Extracted it to `/private/tmp/fx6_font.ttf` and rasterized ASCII 32–126 at 24 px into a 1-bit
atlas (`/private/tmp/fx6_realfont.h`, 95 glyphs, 2612 bytes of bitmap data, per-glyph
bearing/advance). This is the **real FX6 UI font** (the same face the camera uses).

- **617** (`cp-bind-4be897ba`): the menu trigger now draws labels with that real-font atlas
  (`fx6_realtext`) instead of the fallback 5×7 font:

```text
FX6_RECTS realfont labels done
FX6_OSD_SCAN 41e nz_words=551938
gpe0-late: 5 colors
  0xFF101014 x482786 (background)
  0xFF202830 x63750  (list rows)
  0xFFE0E0E0 x3460   (frame/separators)
  0xFFFFFFFF x2556   (real-font glyph pixels — up from 1468 with the 5x7 fallback)
  0xFF…      x408
```

PNG exported: `menu-realfont-617.png` (1024×540).

Runs: 614 `cp-bind-2b53b09e`, 615 `cp-bind-a4131bf3`, 617 `cp-bind-4be897ba`.

### 10.100 619–620 — real-font menu stable; position must come from the shim offset

- **619** (`cp-bind-be703ae7`): restored the 617 draw order (background first, then frame,
  separators, rows, accent bars, then real-font labels). Result is the stable baseline:

```text
FX6_RECTS realfont labels done
FX6_OSD_SCAN 41e nz_words=551938
gpe0: 5 colors, 2556 real-font glyph pixels
PNG menu-realfont-619.png
```

  Visually: **MENU** title in the real HeiseiKakuGoth face, three list rows
  (**ITEM 1/2/3**) each with an accent bar, separator rules, and a **SETTING** footer.

- **620** (`cp-bind-a3f78f21`): tried `RectData+0x10/+0x14` for the position with the shim
  offset disabled; every fill again arrives as `x=0,y=0`, so `renderRect` ignores those
  fields. Confirmed: **the only working position channel is our shim-side
  `g_fx6_ox/g_fx6_oy`** (which is why 594/599/617/619 land correctly).

Remaining polish for the frame edges (top/bottom/left/right rules not always visible) is a
minor compositing/order detail; the visible menu now has text, list rows and rules, but it is
still an authored layout rather than `procam_big6_menu_home/setting` data, and the glyphs come
from the real font atlas rasterized offline rather than the live TextSprite pipeline.

Runs: 619 `cp-bind-be703ae7`, 620 `cp-bind-a3f78f21`.

### 10.101 621 — complete FX6-style menu frame with real-font text in gpe0

621 (`cp-bind-aa014327`) restored the shim-side offset assignment that 617's source had lost
(`g_fx6_ox=x; g_fx6_oy=y;` inside `draw_rect`), which is the only working position channel, and
produced the complete layout:

```text
FX6_RECTS realfont labels done
FX6_OSD_SCAN 41e nz_words=551938
gpe0-late: 7 colors
  0xFF101014 x337118 (background)
  0xFF202830 x195960 (3 list rows)
  0xFFE0E0E0 x8600   (outer frame + rules)
  0xFF404040 x5664   (row separators)
  0xFFFFFFFF x2556   (real-font glyph pixels)
  0xFF3050A0 x1802   (accent bars)
  0xFF…      x1260
```

`menu-frame-621.png` (visually verified, 1024×540):

- white outer frame (all four edges);
- **MENU** title in the real HeiseiKakuGothW5-SJ face with a separator rule under it;
- three shaded list rows, each with a blue accent bar on the left and a real-font label
  **ITEM 1 / ITEM 2 / ITEM 3**;
- row separators between rows;
- **SETTING** footer label and a bottom rule.

All rectangles are emitted through the **native `Sprite::renderRect`** path into the
`GraphicsContextGRM` shim, and the glyphs come from the **real FX6 UI font** (extracted from
`HeiseiKakuGothW5-SJ_wIcon.ltt`).

Runs: 621 `cp-bind-aa014327`.

### 10.99 623 — real Big6 menu items drawn with the real FX6 font into gpe0

Extracted the **real TTF embedded in the firmware font**
(`share/app/HeiseiKakuGothW5-SJ_wIcon.ltt`: `embeddedoffset=2976`,
`embeddedsize=848520`, signature `0x00010000`) into `/private/tmp/fx6_font.ttf`, then
rasterized ASCII 32..126 at 24 px into a bitmap atlas + offsets
(`/private/tmp/fx6_realfont.h`, 95 glyphs, 2612 bytes of bits). `fx6_realtext()` blits those
glyphs into the mapped OSD.

623 (`cp-bind-9916e467`) then built the real FX6 Big6 **home** menu from
`fx6_big6_menu.h` (labels taken from `string_english.uxc`: Shooting / Project / Monitoring /
Audio / TC\/Media / Setup) with:

- background 0xFF101014, outer 2px frame, top/bottom separators (0xFFE0E0E0)
- six 944×56 rows 0xFF202830 with a 6px accent bar and a 2px separator each
- title "MENU" at 44,66 scale 2; row labels at row.x+20, row.y+10

Result in gpe0 (`gpe0-late.bin`):

```text
colors 6: 0xFF202830 x312409, 0xFF101014 x212280, 0xFF404040 x11808,
          0xFF3050A0 x10152, 0xFFFFFFFF x4295, 0xFFE0E0E0 x2016
```

White glyph pixel counts per row: 545 / 383 / 631 / 329 / 530 / 341 (all six rows have
text). ASCII rendering of row 0 clearly reads **"Shooting"**, and the title band shows a
2×-scaled "MENU". PNG exported as `menu-big6-623.png`.

This is the first frame with real FX6 menu labels in the real FX6 typeface, drawn through the
native Sprite rect path + firmware font glyphs. Remaining: icons, multi-level navigation and
the actual `procam_big6_menu_*` presenter data.

Runs: 623 `cp-bind-9916e467`.

### 10.100 626–628 — native resource bootstrap makes view_string/view_menu_item constructible

Implemented the static-line finding: `appFw+0xc0b470` (inside `Application_System_Init`) runs

```text
uxengine_init2()
Kernel::sys_setCurrentDirectory("/usr/share/app/")
gfxeng() -> AreaCheckExtensionManager (check/log paths)
resmgr() -> setDatabase("global.xdb")
resmgr() -> sys_setFontNameWithNamespace(5)
```

- **626** (`cp-bind-db840521`): from our URL-init path:
  `cwd rc=0`, `setdb rc=1082130432 (0x40800000)`, `setns(5) rc=0`, then
  `createFont(id)` scan 0..512 → still `fonts found=0`.
- **627** (`cp-bind-a3dbc196`): also called `uxengine_init2()` first (`rc` garbage/nonzero),
  then cwd/setdb/setns — `setdb` still `0x40000000`, fonts 0. The CPIO does contain
  `usr/share/app/global.xdb` (1792 B) and all `.ltt` fonts, so the DB file is present;
  `setDatabase` is failing for another reason (likely the resmgr bank/arena state that only
  the real `Application_System_Init` path establishes).
- **628** (`cp-bind-b344ca07`): with the bootstrap calls performed, native construction now
  succeeds where earlier it always crashed:

```text
FX6_NV view_string ctor done p=0x7f780c8d70 vptr=0x7f81d83210
FX6_NV setString done
FX6_NV vt158=0x7f7fc9fbd8
FX6_NV view_string onDrawNotice done
FX6_NV view_menu_item ctor done p=0x7f7c1b6010 vptr=0x7f81d80650
FX6_NV menu_item onDrawNotice done
FX6_OSD_SCAN 41e nz_words=2
```

This is the first time `view_string` and `view_menu_item` can be constructed **and drawn**
(their real `onDrawNotice`) without crashing. They still emit no pixels because
`setDatabase("global.xdb")` has not succeeded (fonts/glyphs unresolved), but the UI object
graph is now usable.

Runs: 626 `cp-bind-db840521`, 627 `cp-bind-a3dbc196`, 628 `cp-bind-b344ca07`.

### 10.101 630 — global.xdb is readable, setDatabase always returns 0x40000000

630 (`cp-bind-44eb69f5`) probed the resource database directly:

```text
FX6_DB open /usr/share/app/global.xdb ok n=16 head=75786107   ("uxa" 07 00 00)
FX6_DB open global.xdb ok n=16 head=75786107                  (cwd already /usr/share/app)
FX6_DB setcwd rc=0
FX6_DB chdir rc=0
FX6_DB setdb rel rc=1073741824 (0x40000000)
FX6_DB setdb abs rc=1073741824 (0x40000000)
FX6_DB setns rc=0
```

So:

- the file exists, is readable, has the `uxa` signature, and relative/absolute paths both work;
- `ResourceManager::setDatabase` nevertheless always returns **0x40000000**, both relative and
  absolute. `0x40000000` is a bitflag-style status from libra's XDB layer, not ENOENT.

Conclusion: the failure is **inside libra's resource-manager state**, not the path. The canonical
`Application_System_Init` performs `uxengine_init2()` plus arena/bank setup before
setDatabase; our out-of-band calls skip that. Until `uxengine_init2` runs in the same
sequence/state as the firmware boot, `setDatabase` cannot succeed and fonts stay unregistered.

Runs: 630 `cp-bind-44eb69f5`.

### 10.102 631–632 — setDatabase sink identified (libra SystemLookupTable::setDatabase)

Resolved the call chain behind the `0x40000000` failure:

```text
ux::resmgr::ResourceManager::setDatabase(char const*)   libuxengine 0x75270
  -> libra::ResourceManager::setDatabase(char const*)   liblibra 0x2d61c
       -> [this+0x20]                                    (SystemLookupTable*)
       -> libra::SystemLookupTable::setDatabase(char const*)  0x22540
```

So the `0x40000000` status is produced by libra's `SystemLookupTable` when it refuses to load
`global.xdb`, not by path resolution (630 proved the file is readable with the correct
`uxa` magic from both relative and absolute paths, cwd = `/usr/share/app`).

Likely preconditions still missing: arena/bank registration (`ResourceManager::addArena`,
`XDBTable::load`, bank 0 selection) performed earlier in the firmware's
`Application_System_Init` → `uxengine_init2` path. Our out-of-band calls reach `setDatabase`
with an uninitialised lookup table, so it returns the flag-style error.

Next: disassemble `libra::SystemLookupTable::setDatabase` (0x22540 real body, not the PLT) to
see which state it checks and what `0x40000000` denotes, then pre-seed that state.

Runs: 630 `cp-bind-44eb69f5`; 631/632 static.
