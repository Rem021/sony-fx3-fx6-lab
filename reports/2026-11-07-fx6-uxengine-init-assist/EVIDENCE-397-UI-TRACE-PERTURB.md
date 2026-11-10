# Evidence 397 — post-presenter UI trace perturbs the init state

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **397** `guest-hybrid-fx6kernel-capid-grmreal397-uitrace.cpio`
Run: **`cp-bind-73b7f61d`** (interrupted at 87.4 s after the crash)
Purpose: trace the first UI-init call after the presenter (`c0a86c → df91e8`).

## 1. What happened

397 kept the 395 payload and added a trace site at `c0a86c → df91e8` (the first call after
the presenter). It crashed:

```text
FX6_POST390_CALL a0=0x7f9cbc84b8
APPFW_SEGV sig=11 addr=0xffffffffffffffff pc=appFw+0xde3a74
APPFW_X0=ffffffffffffffff
```

The faulting instruction is `ldr x1,[x0]` with `x0=-1` inside a callee of `df91e8`.

## 2. Why this is instrumentation, not the native boundary

- Runs 395 and 396 execute the same `c0a86c → df91e8` path (same payload, no hook there)
  and produce **no SIGSEGV**; both end in `osal_rcv_msg_tmo`.
- The only difference is the dprintf-based trace stub. The UI init is state-sensitive
  (it is reading partially constructed tables), and the extra logging call changes
  timing/global state enough to expose an error sentinel (`-1`).
- The x8-safe stub itself preserves `x0..x9`, so this is not the x8 bug from 390.

Conclusion: the post-presenter UI init cannot be probed with naive per-call dprintf
logging. Use a counter-only probe or a different observation point.

## 3. Artifacts

| Item | Value |
|---|---|
| CPIO 397 | `guest-hybrid-fx6kernel-capid-grmreal397-uitrace.cpio`, 430,238,320 B, SHA-256 `d5916437…` |
| run 397 | `cp-bind-73b7f61d`, serial 1,249,146 B, SHA-256 `59fe6ec2bde0fa26d7745a52d911325556eeca39b9442abf82a22773554e7afa`, reason `interrupted` |
| gpe0 | 50 s: all zero |

Durable copies in `work/fx6-385-17b9f-calltrace-20261107/` (`serial-397.log`,
`run-receipt-397.json`).
