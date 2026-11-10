# Evidence 391 — every post-walk call returns; the block is after `12d8174` returns

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **391** `guest-hybrid-fx6kernel-capid-grmreal391-x8stub.cpio`
Run: **`cp-bind-6c605426`** (interrupted at 1,396.7 s after the trace showed the full block)
Result: all 34 traced post-walk calls (`POST0…POST33`) return; no SIGSEGV; no
`C09DE4B_RET` / `C14DFC_CALL` / `PRESENTER_CALL`; no native frame.

## 1. The x8-safe stub works

```text
FX6_POST0_CALL  a0=0x7f90b72e10 …   FX6_POST0_RET  r0=0x7f90b72e10
FX6_POST1_CALL  a0=(nil) …          FX6_POST1_RET  r0=0x7f90b72fa0
FX6_POST2_CALL  a0=0x7f90b72fa0 …   FX6_POST2_RET  r0=(nil)
…
FX6_POST15/16/17  (x21 loop body)
…
FX6_POST30_CALL … FX6_POST30_RET
FX6_POST31_CALL … FX6_POST31_RET
FX6_POST32_CALL … FX6_POST32_RET
FX6_POST33_CALL a0=0x7f90b72fa0 …   FX6_POST33_RET r0=(nil)
```

`POST1` is the call that crashed 390 (`12d8274 → 113e8f4`); with the naked assembly stub
preserving `x0..x9`/`x17`, it returns normally. This confirms 390’s SIGSEGV was purely a
stub bug.

## 2. Where the block is now

The traced block is `12d8260 … 12d8554`. All of its call sites returned, so `12d8174`
reaches its epilogue and returns to `12d9fc8` at `12da024`. The next code is:

```text
12da024  bl 0x222cf40
12da034  bl 0x21bde38
12da03c  bl 0x1ac81b4
12da044  bl 0x1acd2f4   ; model-lock release path (mutex + refcount)
12da054  ret
```

None of these is instrumented yet. Since 389’s AppFw thread sat in `futex_wait_queue_me`,
the most likely blocker is `1acd2f4` (or the `1ac81b4` virtual call), not the block that
391 just cleared.

## 3. 392 (running)

392 keeps the 391 payload and appends four trace sites to the same shared trampoline page:

| id | slot | target |
|---|---|---|
| 34 | `12da024` | `222cf40` |
| 35 | `12da034` | `21bde38` |
| 36 | `12da03c` | `1ac81b4` |
| 37 | `12da044` | `1acd2f4` |

The first `POST<id>_CALL` without `RET` is the real blocker. Late GPE capture remains at
`seconds-90`.

## 4. Artifacts

| Item | Value |
|---|---|
| CPIO 391 | `guest-hybrid-fx6kernel-capid-grmreal391-x8stub.cpio`, 430,232,336 B, SHA-256 `9c34f7b5…` |
| run 391 | `cp-bind-6c605426`, serial 2,668,595 B, SHA-256 `37f976b23c3aff4e1cde88883d46ef571b7a94c5bd035e24a97d5c4dbed271c8`, reason `interrupted` |
| CPIO 392 | `guest-hybrid-fx6kernel-capid-grmreal392-tailtrace.cpio`, 430,232,336 B, SHA-256 `2232b5ec…` |
| shim 392 | `libgrm-fbinit25-392.so`, SHA-256 `371d2f90…` |

Durable copies under `work/fx6-385-17b9f-calltrace-20261107/`
(`serial-391.log`, `run-receipt-391.json`, `libgrm-fbinit25-392.c/.so`, manifest, runner).
