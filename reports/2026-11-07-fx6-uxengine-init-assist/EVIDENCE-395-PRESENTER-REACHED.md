# Evidence 395/396 — native presenter reached; framebuffer created; still no painted frame

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidates: **395** (`...grmreal395-skiplock.cpio`), **396** (`...grmreal396-presentertrace.cpio`)
Runs: **`cp-bind-13932101`** (395, 900 s), **`cp-bind-6849dc94`** (396, in progress)

## 1. The breakthrough

After the 13,793-entry model walk, `12d8174` has 382 call sites. 393 found the last
non-returning one:

```text
POST379 = 0x12d9de8 -> 0x1acd874   (model-lock condition wait, pthread_cond_wait)
```

395 skips exactly that one call (`NOP` at `0x12d9de8`) and leaves everything else real.
Result (`cp-bind-13932101`):

```text
FX6_POST378_RET
FX6_POST380_CALL / RET
FX6_POST381_CALL / RET
FX6_C09DE4B_RET                 <-- 12d9fc8 returns at last
FX6_C14DFC_CALL x0=…            <-- c09df0 widget-factory call
FX6_C14DFC_RET  x0=…
FX6_PRESENTER_CALL x0=0x7f975b94b8   <-- c0a860 -> 0x1397450
```

New native threads appear after the presenter call:

| tid | comm | wchan |
|---|---|---|
| 241 | `RemotePresenter` | futex |
| 242 | `uipc_proxy_3` | osal_unlock |
| 243 | `AppDebug` | osal_rcv_msg_tmo |
| 244 | `BackupProxy` | futex |
| 245/246 | `I-InputEvent` | futex |

And the shim's GRM path constructs a real framebuffer:

```text
FX6_GRM_FB_MINIMAL before manager=… fb=(nil) ctor=…
FX6_GRM_FB_MINIMAL after  manager=… fb=0x7fb1656230 vptr=0x7fb15eae90
FX6_GRM_FB_SET_SIZE self=0x7fb1656230 w=1024 h=540
FX6_GRM_FBRM_CB_FIRE cb=… user=… (1024x540 fmt=2)
FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0
```

`c09de4` now returns; `c14dfc` runs; the presenter call is entered; the GRM framebuffer
manager exists; the FBRM trigger callback fires. This is the first time in the project that
the real presenter path is reached.

## 2. 396 — presenter sub-calls all return

Run `cp-bind-6849dc94` (interrupted at 113.5 s after the presenter path had settled).
396 traces the eight call sites of `0x1397450` (`POST382…POST389`):

```text
POST382 (21bdd4c)  RET
POST383 (1acd618)  RET
POST384 (222cd6c)  RET
POST385 (1395c3c)  RET   <-- the actual presenter construction
POST386 (222cf40)  RET
POST387 (21bde38)  RET
POST388 (1ac81b4)  RET
POST389 (1acd2f4)  RET
```

So `0x1397450` completes its whole body; the presenter stub does not log a RET (by design),
but all inner calls returned. No SIGSEGV, no further draw.

## 3. What is still missing: a draw job / output flush

- AppFw (tid 222) then sits in `osal_rcv_msg_tmo` — the OSAL receive loop, waiting for an
  IPC/job message. It is not crashed and not in a futex.
- `gpe0` at 50 s and `gpe0-late` at ≈810 s are both **all zero** (2,211,840 B, 1 unique
  value).
- The shim's own `FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0` shows no primitives were
  queued through the compatibility renderer.
- The minimal GRM framebuffer is 1024×540, but nothing has yet copied it to
  `0x41e001000`/`0x429550000` (the OSD physical planes captured by QMP).

So the remaining gap is exactly the original Round-4 question, now one level higher:
**which job/notify wakes the AppFw event loop and causes the first native paint?**
Candidate knobs for the next runs:

1. Late input injection (key after presenter is up, not at 35 s).
2. A GRM `fbrmUpdate`/`gperm` trigger through the existing shim wrappers.
3. The `0xc09e48` trigger-framework registration path (it is restored in 388+ and the FBRM
   callback fired, so registration is probably not the missing piece).

## 4. Evidence status

| Claim | Status |
|---|---|
| 13,793-entry walk completes | proven (387/393) |
| `c56fdc` call/return at `17b9f1c` | proven (385) |
| `17b9f1c` returns | proven (386) |
| `c56fec`/`1acd618` restore speeds walk 24 min → ~30 s | observed (394) |
| model-lock wait at `1acd874` is the last post-walk blocker | proven (393/395) |
| `c09de4` returns | proven (395) |
| `c14dfc` runs | proven (395) |
| presenter enter + native threads + 1024×540 GRM framebuffer | proven (395) |
| native painted frame | **not yet** (`gpe0` all zero) |

## 6. 397/398 — after the presenter

- **397** (`cp-bind-73b7f61d`, interrupted at 87.4 s) added a trace at `c0a86c → df91e8`,
  the first call after the presenter. It crashed at `appFw+0xde3a74` with `x0=-1`;
  395/396 executed the same path without a SEGV, so this is a **trace-stub perturbation**
  (the C/asm logger changes state in a fragile UI init), not a native fault. No further
  use of that hook.
- **398** (`cp-bind-0bd36667`, 600 s) kept the stable 395 payload and moved the menu-key
  injection to 90 s. The injection failed before touching the guest:
  `keyinject-error.txt` = `FileNotFoundError(2, 'No such file or directory')`; no
  `FX3_KEY96_*` marker appears in the serial. The shim’s key mailbox is only polled from
  `flush_pixels_to_osd()`, which is inactive on the native path, so this gate cannot wake
  the native input threads. `gpe0-late.bin` at 510 s is still all zero.

## 7. Remaining gap

The AppFw thread ends in `osal_rcv_msg_tmo` (IPC receive loop), not a crash: the real
presenter is constructed and the UI is idle waiting for an event/job. The 1024×540 GRM
framebuffer exists, but no pixels have been copied to the OSD planes. The next lever is
therefore an **event** (native input / GRM screen-update job), not another code-path patch.

## 8. Artifacts

| Item | Value |
|---|---|
| CPIO 395 | `guest-hybrid-fx6kernel-capid-grmreal395-skiplock.cpio`, SHA-256 `d1968f5c…` |
| run 395 | `cp-bind-13932101`, serial 2,868,421 B, SHA-256 `2796c29940350a08d44a331f16f69c23dcab026e5530a256f1e995fd5b5d2c7b` |
| CPIO 396 | `guest-hybrid-fx6kernel-capid-grmreal396-presentertrace.cpio`, SHA-256 `0526707f…` |
| run 396 | `cp-bind-6849dc94`, serial 1,416,775 B, SHA-256 `3e33d2aaf9978ae5ba4f247c68410a8fcda43fcaadf2a8258d6cb7f94aafa7ab` |
| run 397 | `cp-bind-73b7f61d`, serial SHA-256 `59fe6ec2bde0fa26d7745a52d911325556eeca39b9442abf82a22773554e7afa` |
| gpe0 395 | 50 s and 810 s: all zero |

Durable copies under `work/fx6-385-17b9f-calltrace-20261107/`.
