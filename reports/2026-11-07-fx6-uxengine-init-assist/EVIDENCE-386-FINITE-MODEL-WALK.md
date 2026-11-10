# Evidence 386 — the “c09de4 block” is a finite 13,793-entry model walk, not a hang

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **386** `guest-hybrid-fx6kernel-capid-grmreal386-fc4fix.cpio`
Run: **`cp-bind-cc9f2446`** (300 s wall window)
Result: **`17b9f1c` returns; dispatcher continues past `n=1003`; 3,295 entries in 300 s; no SIGSEGV.**

## 1. What changed from 385

Only the hook address in `libgrm-fbinit9.so`:

- 385: `17b9fc0` (which is `add x0,x29,#0x50`) was replaced by a BL to a logger.
  385 therefore fed `x0=1` into `0x11a107c` and self-inflicted `APPFW_SEGV addr=0x15`.
- 386: the hook moved to the real call `17b9fc4 → 0x11a107c`; the `add` executes normally,
  and `0x17b9fcc → c0cbc0` keeps its own hook. Both stubs forward `x0..x7`.

CPIO 386 differs from 385 only in `usr/lib/libgrm-fbinit9.so`
(SHA-256 `c914420b…`); the 1,165 members and `appFw.so` SHA (`a1c58b69…`) are unchanged.

## 2. Transition at the old “block”

```text
FX6_DISPATCH n=1003 x2=… off=17b9f1c
FX6_17B9F4C_CALL …  FX6_17B9F4C_RET r0=0x7f9fc50360
FX6_17B9F54_CALL …  FX6_17B9F54_RET r0=0x7f9fc50368
FX6_17B9F70_CALL …  FX6_17B9F70_RET r0=0x7f9fc50368
FX6_17B9F98_CALL a0=(nil) a1=0x6c3 a2=0x7f9fc50368 a3=0x7f9ad95cfc a4=0x4
FX6_17B9F98_RET r0=(nil)
FX6_17B9FC4_CALL a0=0x7f9ad95d10 …
FX6_17B9FC4_RET r0=(nil)
FX6_17B9FCC_CALL a0=0x7f9ad95d00 …
FX6_17B9FCC_RET r0=(nil)
FX6_DISPATCH n=1004 x2=… off=17b9fec
FX6_DISPATCH n=1005 x2=… off=17ba0f0
FX6_DISPATCH n=1006 x2=… off=18e271c
FX6_DISPATCH n=1007 x2=… off=18e2ad4
FX6_DISPATCH n=1008 x2=… off=17ba1c0
```

So the handler completes both its tail calls (`11a107c`, `c0cbc0`) and returns to the
table walk. The previous “n=1003 is the stop point” was the end of the 120 s window, not a
block.

(386’s `17b9f44 → c56fdc` hook did not install because its non-fixed mmap landed 274 MB
away; 385 already recorded that exact call/return, so no information is lost.)

## 3. Why the earlier rounds looked “stuck”: the walk is 13,793 entries long

`1537e00` is not one table; it runs five consecutive index-table loops and then returns:

| # | Table base | End offset | Stride | Entries |
|---|---|---|---|---|
| 1 | `0x24ea350` | `+0xabd4` | 8 | **5,498** |
| 2 | `0x24dd890` | `+0xa4ac` | 8 | **5,269** |
| 3 | `0x24e7d38` | `+0x261c` | 8 | **1,219** |
| 4 | `0x2b757f0` | `+0x3328` | 16 | **818** |
| 5 | `0x24f4000` | `+0x1eec` | 8 | **989** |
| | | | | **13,793** |

Each entry calls `1778ebc`, which indexes the model table at `0x2b78b10`
(stride `0x30`, handler at `+0x20`). The loop bound is a constant, not a wait:

```text
1537e20  ldur w0,[x20,#-4]
1537e24  mov  x1,x20
1537e28  add  x20,x20,#8
1537e2c  bl   1778ebc
1537e30  cmp  x20,x19
1537e34  b.ne 1537e20
```

Measured pace in 386: **3,295 dispatches / 300 s ≈ 11.0 entries/s**, so the walk alone
needs ≈ **1,250 s**. The old windows covered:

| Window | Max entries reachable | Coverage of 13,793 |
|---|---|---|
| 120 s | ~1,300 | 9 % |
| 180 s | ~2,000 | 14 % |
| 420 s (Round 39) | ~4,600 | 33 % |

That is why `12d8274/12d8288`, `12d9fc8` tail, `c09e50`, `c14dfc`, and Presenter were never
reached: the run was always still inside loop 1. The `model_mutex.cpp:59` asserts printed
throughout come from a different thread and are not the table walk stalling.

## 4. Current status

```text
17b9f1c handler:        complete (all calls returned)
model-table walk:       finite, 13,793 dispatches
386 progress:           3,295 / 13,793 (24 %) in 300 s, no fault
next dispatch family:   17ba…, 18e2…, 184e… (still in loop 1)
c14dfc (widget factory): not reached yet
Presenter registration:  not reached
gpe0:                    all zero (no native frame)
```

## 5. Next experiment (running)

**387** reuses the exact 386 payload with a 2,100 s window
(`runs/` auto-id, manifest `vm-candidate-gpecap25-387-long.json`). Expected timeline:
loop 1 ends ≈ 500 s; all five loops end ≈ 1,250 s; the remaining ≥ 800 s is margin for the
post-walk path (`1537e00` return → `12d8174` tail → `c09de4` return → `c09df0` →
`c14dfc` widget factory → Presenter).

Success criteria for 387:

1. `FX6_12D8274_CALL` (the first post-walk call previously never reached).
2. `FX6_12D9FC8` tail / `FX6_C09DE4B_RET`.
3. `FX6_C14DFC_CALL` and, only then, `FX6_PRESENTER_CALL`.
4. Non-zero `gpe0` at `0x41e001000` — the only acceptable native-frame claim.

## 6. Artifacts

| Item | Value |
|---|---|
| CPIO 386 | `guest-hybrid-fx6kernel-capid-grmreal386-fc4fix.cpio`, 430,229,160 B, SHA-256 `5c67f72f…` |
| shim 386 | `libgrm-fbinit25-386.so`, SHA-256 `c914420b…` |
| manifest 386 | `vm-candidate-gpecap25-386.json`, SHA-256 `cbdab6ed…` |
| run 386 | `cp-bind-cc9f2446`, serial SHA-256 `4099008f33b30f2fd3e8ab8fd510e1108f7b1dc4967f5016dd3ac76732be34be` |
| gpe0 386 | 2,211,840 B, all zero |

Durable copies under `work/fx6-385-17b9f-calltrace-20261107/`
(`serial-385.log`, `serial-386.log`, receipts, shim sources, manifests, runners).
