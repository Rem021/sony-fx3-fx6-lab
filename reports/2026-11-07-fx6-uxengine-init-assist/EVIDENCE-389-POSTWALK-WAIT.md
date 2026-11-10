# Evidence 389 — walk + post-walk constructors pass; AppFw blocks inside the next block

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **389** `guest-hybrid-fx6kernel-capid-grmreal389-addfix.cpio`
Run: **`cp-bind-76d6072a`** (2,100 s window, completed)
Result: no SIGSEGV; the 13,793-entry walk completes; `12D8244/8248/8260` return; the AppFw
thread then sits in `futex_wait_queue_me` with no further marker; **gpe0 late capture all zero**.

## 1. What 389 fixed

- Restored `0xc09e48` (GRM trigger-framework registration) and `0xc09e50` (sync path).
- Restored the real `0x12d8264 add x0,x29,#0x80`; removed the bogus NOP that made
  `0x12d8268 bl c56fdc` receive `x0=0x10` (387’s crash at `c56ff0`, addr `0x18`).
- Kept `0xc56fec` NOPed and the `12d824c…` infra NOPs.

## 2. Run result

```text
FX6_DISPATCH n=13793 x2=… off=1895068
FX6_12D8244_CALL x0=0x7f7bcccef0
FX6_12D8244_RET
FX6_12D8248_CALL x0=0x10
FX6_12D8248_RET
FX6_12D8260_CALL
FX6_12D8260_RET
(no APPFW_SEGV)
(no FX6_C09DE4B_RET)
(no FX6_C14DFC_CALL / PRESENTER_CALL)
```

The AppFw thread (tid 222) appears in the periodic snapshot as:

```text
AppFw
futex_wait_queue_me
… futex_wait / do_futex / SyS_futex
```

So after `12D8260_RET` the thread blocks in userspace synchronization, inside the
post-walk sequence `12d8268 … 12d8554` (the `c56fdc` object init and the following
`113e8f4` / `1188b38` x21 loop and later calls). `c56fdc` itself is now store-only
(`0xc56fec` is NOPed), so the likely wait is in a later callee.

## 3. Native-frame check

The runner’s late capture at `seconds-90` (≈2,010 s) wrote `gpe0-late.bin`:

| File | Bytes | Non-zero bytes | Unique values |
|---|---|---|---|
| `gpe0.bin` (50 s) | 2,211,840 | 0 | 1 |
| `gpe0-late.bin` (2,010 s) | 2,211,840 | 0 | 1 |

No native frame. This is consistent with the AppFw thread being blocked before
`c09de4` returns and before `c14dfc`/Presenter.

## 4. Next: 390 identifies the blocking call

390 (running) keeps the 389 payload and adds a per-call trace to all 34 BL sites from
`0x12d8268` to `0x12d8554`, using one shared near trampoline page:

```text
ldr x16,#12 ; movz w17,#site_id ; br x16 ; .quad fx6_stub_post
```

The stub reads `x17` (site id), logs `FX6_POST<id>_CALL/RET`, forwards `x0..x7`, and
returns the real `x0`. The first `POST<id>_CALL` without a matching `RET` is the exact
blocking call.

Success criteria remain: `C09DE4B_RET`, `C14DFC_CALL/RET`, `PRESENTER_CALL`, and a
non-zero late `gpe0`.

## 5. Artifacts

| Item | Value |
|---|---|
| CPIO 389 | `guest-hybrid-fx6kernel-capid-grmreal389-addfix.cpio`, 430,227,072 B, SHA-256 `5187ae51…` |
| run 389 | `cp-bind-76d6072a`, serial 3,066,811 B, SHA-256 `2fce0368c475b7baca8e209647a126ce61dde08270d098c2ff4a0963e75d9ff6` |
| CPIO 390 | `guest-hybrid-fx6kernel-capid-grmreal390-posttrace.cpio`, 430,232,136 B, SHA-256 `a79cfb3a…` |
| shim 390 | `libgrm-fbinit25-390.so`, SHA-256 `705df42a…` |

Durable copies under `work/fx6-385-17b9f-calltrace-20261107/`
(`serial-389.log`, `run-receipt-389.json`, `libgrm-fbinit25-390.c/.so`, manifest, runner).
