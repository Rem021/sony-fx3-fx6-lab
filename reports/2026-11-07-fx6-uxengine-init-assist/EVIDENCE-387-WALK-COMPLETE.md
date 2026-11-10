# Evidence 387 — the 13,793-entry walk completes; the next crash is another bogus NOP

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **387** = 386 payload, 2,100 s window, `vm-candidate-gpecap25-387-long.json`
Run: **`cp-bind-54bcebde`** (interrupted at 1,613.9 s after the AppFw thread had already died)
Result: **walk finished exactly at `n=13793`**, three post-walk calls returned, then
`APPFW_SEGV` at `c56ff0` caused by the shim’s bogus NOP at `0x12d8264`.

## 1. The walk completes

```text
FX6_DISPATCH n=13792 …
FX6_DISPATCH n=13793 x2=0x7f87005068 off=1895068
FX6_12D8244_CALL x0=0x7f8568def0
FX6_12D8244_RET
FX6_12D8248_CALL x0=0x10
FX6_12D8248_RET
FX6_12D8260_CALL
FX6_12D8260_RET
APPFW_SEGV sig=11 addr=0x18 pc=…+c56ff0
```

`n=13793` is exactly the static total of the five loops in `1537e00`
(5,498 + 5,269 + 1,219 + 818 + 989). The bound is constant, and there is no recursive
dispatcher call (`1778ebc` has only the five loop call sites). So the “hang” is definitively
a finite long walk; 387 reached its end at roughly 1,440 s of guest time.

The old markers `12D8244/12D8248/12D8260` now appear for the first time — they were never
reached because every earlier run was still inside loop 1.

## 2. The crash is instrumentation-induced (same class as 17b9fc0)

Disassembly of the post-walk block:

```text
12d8260  bl 0x10f5bf8     ; logged CALL/RET
12d8264  add x0,x29,#0x80 ; <-- shim NOP'ed this, thinking it was a call
12d8268  bl 0xc56fdc      ; real call, gets stale x0
```

The shim’s `fx6_patch_blocking_calls()` writes `0xd503201f` at `0x12d8264`, and
`fx6_patch_12d8260_264()` also tries to hook that same address (the NOP wins). As a result
the `add` never runs; `x0` keeps the value `0x10` left by the preceding
`FX6_12D8248_CALL x0=0x10`.

Crash registers confirm it exactly:

```text
APPFW_SEGV sig=11 addr=0x18 pc=…+c56ff0
APPFW_X0=10
APPFW_X19=10
```

`c56fdc` stores `xzr` at `[x19,#8]` → address `0x18`, unmapped. This is **not** a null
object from FX6 services; it is a stale register caused by NOPing a non-call instruction.

Consequence: the Round 19 conclusion “`c56fdc` is called with a null/0x10-like object”
was describing this same self-inflicted state. Rounds 344–349 then built guards and NOPs
around a bug created by the 12d8264 NOP. With `0x12d8264` restored, `c56fdc` receives
`x29+0x80` (a valid stack object) and the store targets the stack, not `0x18`.

## 3. Other observations

- `12D8244` and `12D8248` return normally, so the post-walk constructors are fine.
- `12D8260 → 0x10f5bf8` returns normally.
- No `C09DE4B_RET`, no `C14DFC_CALL`, no `PRESENTER_CALL`: the crash kills the thread
  before those.
- `gpe0` at 50 s: 2,211,840 B, **all zero** (the capture predates any possible paint).

## 4. Fixes prepared

| Candidate | Payload change | Status |
|---|---|---|
| 388 | restore `0xc09e48` (`GRM_fbrmRegisterTriggerFrameworkCb`) and `0xc09e50` (sync wait) to native; late GPE capture | built, not run — 387 shows it would hit the same `12d8264` crash |
| **389** | 388 **+** restore `0x12d8264` `add`, remove the bogus `12d8264` hook | **running now** (2,100 s, late capture at `seconds-90`) |

389 still keeps `0xc56fec` NOPed (it was only needed because the stale `x19` crash looked
like an internal-init problem) and keeps the `12d824c…` infra-init NOPs. If 389 passes
`12d8268` and reaches `c14dfc`, the next single-variable runs will restore `c56fec` and then
the `12d824c…` cluster, one at a time.

## 5. Success criteria for 389

1. No `APPFW_SEGV` at `c56ff0`.
2. `FX6_C09DE4B_RET` (the long `12d9fc8` call returns).
3. `FX6_C14DFC_CALL` / `RET` at `c09df0`.
4. `FX6_PRESENTER_CALL` at `c0a860`.
5. `gpe0-late.bin` captured at ≈2,010 s: non-zero pixels would be the first native-frame
   evidence; serial markers alone are not enough.

## 6. Artifacts

| Item | Value |
|---|---|
| CPIO 387 | same as 386 (`5c67f72f…`) |
| run 387 | `cp-bind-54bcebde`, serial 2,617,288 B, SHA-256 `881510541ccba1d66a21812bf3687628e0606abbc553db7f9e7c7a15b5555c49`, reason `interrupted` |
| CPIO 389 | `guest-hybrid-fx6kernel-capid-grmreal389-addfix.cpio`, 430,227,072 B, SHA-256 `5187ae51…` |
| shim 389 | `libgrm-fbinit25-389.so`, SHA-256 `ee66bbc1…` |
| manifest 389 | `vm-candidate-gpecap25-389.json`, SHA-256 `69b74a3f…` |

Durable copies under `work/fx6-385-17b9f-calltrace-20261107/`
(`serial-387.log`, `run-receipt-387.json`, `libgrm-fbinit25-389.c/.so`, manifest, runner).
