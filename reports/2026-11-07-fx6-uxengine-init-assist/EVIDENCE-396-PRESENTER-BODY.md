# Evidence 396 — presenter body completes; no paint

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **396** `guest-hybrid-fx6kernel-capid-grmreal396-presentertrace.cpio`
Run: **`cp-bind-6849dc94`** (interrupted at 113.5 s after the presenter body had settled)
Purpose: determine whether `0x1397450` (the `c0a860` presenter call) blocks internally.

## 1. Trace

395 had already reached `FX6_PRESENTER_CALL`. 396 added the x8-safe naked-stub trace to
the eight call sites of `0x1397450`:

| id | slot | target | result |
|---|---|---|---|
| 382 | `1397478` | `21bdd4c` | CALL / RET |
| 383 | `1397480` | `1acd618` | CALL / RET |
| 384 | `1397488` | `222cd6c` | CALL / RET |
| 385 | `1397494` | `1395c3c` | CALL / RET (presenter construction) |
| 386 | `13974a0` | `222cf40` | CALL / RET |
| 387 | `13974a8` | `21bde38` | CALL / RET |
| 388 | `13974b0` | `1ac81b4` | CALL / RET |
| 389 | `13974b8` | `1acd2f4` | CALL / RET |

```text
FX6_PRESENTER_CALL x0=…
FX6_POST382_CALL … POST389_RET
(no SIGSEGV)
```

The presenter stub only logs `PRESENTER_CALL` (it does not log a return), so the eight
inner CALL/RET pairs are the strongest available evidence that `0x1397450` finished its
body. The run was stopped after the trace settled.

## 2. What this rules out

- The presenter call is not stuck in the presenter construction (`1395c3c` returns).
- The presenter call is not stuck in the model-lock init/release (`1acd618`, `1acd2f4`
  return).
- The remaining idle state is after `0x1397450`, in the caller’s later UI-init calls or
  the event loop (`osal_rcv_msg_tmo`).

## 3. Artifacts

| Item | Value |
|---|---|
| CPIO 396 | `guest-hybrid-fx6kernel-capid-grmreal396-presentertrace.cpio`, 430,238,320 B, SHA-256 `0526707f…` |
| run 396 | `cp-bind-6849dc94`, serial 1,416,775 B, SHA-256 `3e33d2aaf9978ae5ba4f247c68410a8fcda43fcaadf2a8258d6cb7f94aafa7ab`, reason `interrupted` |
| gpe0 | 50 s: all zero |

Durable copies in `work/fx6-385-17b9f-calltrace-20261107/` (`serial-396.log`,
`run-receipt-396.json`).
