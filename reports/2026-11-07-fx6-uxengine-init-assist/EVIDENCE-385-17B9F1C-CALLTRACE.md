# Evidence 385 — `17b9f1c` per-call trace: `c56fdc` returns; the apparent block was a mis-addressed hook

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff from `term_22969527`)
Candidate: **385** `guest-hybrid-fx6kernel-capid-grmreal385-17b9f-trace1.cpio`
Run: **`cp-bind-4767b7af`** (300 s wall window)
Conclusion: **no native frame yet**, but the previous blocker attribution is now corrected twice.

## 1. Concurrency / provenance check (done before touching anything)

- No QEMU or runner process was alive when this line started (12:23 PST).
- The newest runtime artifacts were `libgrm-fbinit25-384.c/.so` at 11:43 and
  `runs/cp-bind-83784058` at 11:45 — i.e. the previous terminal stopped at candidate 384,
  exactly the handoff boundary. No file changed after that until this line started.
- This line used new ids only: shim `385`, CPIO `...grmreal385-17b9f-trace1.cpio`,
  run `cp-bind-4767b7af`. No existing candidate, run dir, report, or source was overwritten.
- Work tree was verified on `/Volumes/KAFU2T` (UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`).

## 2. Correction: run 384 never reached `n=1003`

The cumulative report (Round 46) concluded “`17b9f1c` blocks before `17b9f98`”.
That cannot be concluded from run 384: its 120 s window ended while the dispatcher was at
`n=999`.

Reproduced from the serial logs:

| Run | Candidate | Dispatch max | `17B9F98_CALL` | Wall |
|---|---|---|---|---|
| `cp-bind-e250580c` | 382 | **1003** | not installed | 120 s |
| `cp-bind-2cb8a0d0` | 383 | 999 | 0 | 120 s |
| `cp-bind-83784058` | 384 | **999** | 0 | 120 s |

Only the 382 run actually entered handler `appFw+0x17b9f1c`; it did so at the very end of
its window, so “no further dispatch” was a timeout artifact. Runs 383/384 were still four
table entries short when killed. The absence of `17B9F98_CALL` in 384 is therefore
**not evidence** about the handler. This line raised the window to 300 s.

## 3. Candidate 385 design — in-guest call-site injection

Base: 384 (real appFw, real `Application_System_Init`, RsrcRelation initialized, all
previous real-path patches preserved). Only the shim changed:

- Kept the dispatcher hook at `1778ed8` (logs `FX6_DISPATCH n=… x2=… off=…`).
- Added entry/return stubs at **every call site inside `17b9f1c`**, forwarding
  `x0..x7` to the real callee and returning its `x0`:
  `17b9f34 → 14de79c`, `17b9f44 → c56fdc`, `17b9f4c → 14de788`,
  `17b9f54 → 14de79c`, `17b9f70 → 14de79c`, `17b9f98 → 21bdcc8`,
  `17b9fe4 → 21bdcc8`.
- This is the “single-step injection” requested for this round, implemented as a
  per-call-site trace rather than ptrace (the guest has no usable user-thread gdbstub;
  Round 36 already established the QEMU stub exposes only the four vCPUs).

Static layout of the handler (`appFw.so`, SHA-256 `a1c58b69…`, 50,520,424 B), for reference:

```text
017b9f1c  stp x29,x30,[sp,#-0x70]!
017b9f34  bl 0x14de79c      ; getter, returns global ptr
017b9f38  ldr w1,[x19]
017b9f3c  str w1,[x0,#0x10]
017b9f40  mov x0,x20
017b9f44  bl 0xc56fdc       ; object init (previously blamed)
017b9f48  ldr x19,[x29,#0x48]
017b9f4c  bl 0x14de788      ; getter
017b9f50  mov x21,x0
017b9f54  bl 0x14de79c      ; getter
017b9f58  stp x21,x0,[x29,#0x50]
...
017b9f98  bl 0x21bdcc8      ; notify (taken when [obj+8] != 0)
017b9fa4  str w19,[x0]
...
017b9fc0  add x0,x29,#0x50
017b9fc4  bl 0x11a107c      ; the real call (NOT 0x17b9fc0)
017b9fc8  mov x0,x20
017b9fcc  bl 0xc0cbc0
017b9fdc  ret
```

The handler is table entry index **1731** in the model table at `0x2b78b10`
(entry stride `0x30`, handler pointer at `+0x20`).

## 4. Result — every call up to `21bdcc8` returns

Serial excerpt (`serial-385.log`, lines 5528–5540):

```text
FX6_DISPATCH n=1003 x2=0x7f92b6ff1c mod=/usr/lib/appFw.so off=17b9f1c
FX6_17B9F44_CALL a0=0x7f912d2d00 a1=0x1 a2=0x7f912d51e0 a3=0x7f912d58d0 a4=(nil)
FX6_17B9F44_RET r0=0x7f912d2d00
FX6_17B9F4C_CALL a0=0x7f912d2d00 ...
FX6_17B9F4C_RET r0=0x7f9618e360
FX6_17B9F54_CALL a0=0x7f9618e360 ...
FX6_17B9F54_RET r0=0x7f9618e368
FX6_17B9F70_CALL a0=0x6c3 ...
FX6_17B9F70_RET r0=0x7f9618e368
FX6_17B9F98_CALL a0=(nil) a1=0x6c3 a2=0x7f9618e368 a3=0x7f912d2cfc a4=0x4
FX6_17B9F98_RET r0=(nil)
FX6_17B9FC0_CALL x0=0x1
APPFW_SEGV sig=11 addr=0x15 pc=7f9255707c
```

Facts established:

1. **`c56fdc` is called from `17b9f1c` and returns normally** (`17B9F44_CALL`/`RET`).
   This is the exact call/return record requested by the handoff.
2. The getters `14de788` / `14de79c` return normally.
3. The notification `21bdcc8` is called with `a0=NULL` (because `c56fdc` zeroed
   `[x29+0x48]`, which is then loaded into `x19`) and **returns** (`17B9F98_RET`).
4. `17b9f1c` therefore does **not** block in `14de79c`, `c56fdc`, `14de788`, or `21bdcc8`.

## 5. The SIGSEGV is instrumentation-induced, not native

The crash PC `0x7f9255707c` is `appFw+0x11a107c`, reached with `x0=1` and faulting at
`addr=0x15`. `0x11a107c` begins `ldrb w1,[x0,#0x14]`, so `x0=1` is the cause.

Root cause is the old hook address inherited from Round 45: `17b9fc0` is
`add x0,x29,#0x50`, **not a call**. Replacing that instruction with a BL to a logger meant
the real `add` never executed; the logger then called `0x11a107c` with the stale `x0`
(=1). The faulting address and the register dump (`X0=1`, `PC=11a107c`) match exactly.

So:

```text
17b9f1c calls: all return
17b9fc0 hook:  mis-addressed, skipped the add, self-inflicted SIGSEGV
real boundary: still unknown after the 21bdcc8 notify returns
```

## 6. Repair for the next candidate

386 relocates the hook from `0x17b9fc0` to the real call site **`0x17b9fc4`**, keeps
`0x17b9fcc → c0cbc0`, and forwards all eight argument registers. If `17B9FC4_RET`
appears, the handler tail proceeds to `c0cbc0 → 1acd2f4` (model-lock release path); if
`17B9FCC_CALL` appears without `RET`, the next real boundary is `1acd2f4` inside the
model mutex code, not the widget/presenter path.

## 7. Artifacts

| Item | Value |
|---|---|
| CPIO 385 | `guest-hybrid-fx6kernel-capid-grmreal385-17b9f-trace1.cpio`, 430,227,288 B, SHA-256 `fbbf8f5d…` |
| shim 385 | `libgrm-fbinit25-385.so`, SHA-256 `2d9dc368…` |
| manifest 385 | `vm-candidate-gpecap25-385.json`, SHA-256 `bbffbc63…` |
| run 385 | `runs/cp-bind-4767b7af`, serial SHA-256 `169e53efc6c03b87912b3338b7379c0fd63dce9b43dc0e99ea78cfe005eb9573` |
| gpe0 | 2,211,840 B, **all zero** (1 unique value) — no native frame |

Durable copies: `work/fx6-385-17b9f-calltrace-20261107/`
(`libgrm-fbinit25-385.c/.so`, `serial-385.log`, `run-receipt-385.json`, `gpe-captures-385.json`).

The 385 CPIO is byte-identical to 384 except for `usr/lib/libgrm-fbinit9.so`
(verified: same 1,165 members; `appFw.so` SHA unchanged `a1c58b69…`).
