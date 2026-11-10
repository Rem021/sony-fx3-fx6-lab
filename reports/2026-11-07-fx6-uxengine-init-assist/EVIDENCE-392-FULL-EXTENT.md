# Evidence 392 — `12d8174` is a 382-call monster; the block is inside it

Date: 2026-11-07 (PST) · Runtime line: DeepSeek (handoff)
Candidate: **392** `guest-hybrid-fx6kernel-capid-grmreal392-tailtrace.cpio`
Run: **`cp-bind-47c51739`** (interrupted at 1,862.1 s)
Result: the 34-site trace completes (`POST0…POST33` all return), but the four new
`12d9fc8`-tail hooks (`POST34…37`) are never reached. Static re-check shows why:
`12d8174` does not end at `12d8554`; it continues to `12d9e14` with **382 BL sites**.

## 1. 392 result

```text
FX6_DISPATCH n=13793
FX6_POST0…POST33  CALL/RET   (all return)
(no POST34/35/36/37)
(no C09DE4B_RET / C14DFC_CALL / PRESENTER_CALL / SIGSEGV)
```

`POST33` is `12d8554 → 1180134`, the last site of the earlier 34-site list. After it,
`12d8174` continues with hundreds of further calls (the report’s earlier assumption that
`12d8554` was near the end of the block was wrong).

## 2. Static extent of `12d8174`

| Property | Value |
|---|---|
| Start | `0x12d8174` |
| First `ret` | `0x12d9e14` |
| BL sites up to that ret | **382** |
| Last sites | `12d9d70 → c0cbc0`, `12d9d94 → 1acd2f4`, `12d9da0 → c56fdc`, `12d9db4 → 10f6150`, `12d9de0 → 10f727c`, … |

So the futex wait observed in 389 is somewhere in this 382-call body, not in the
`12d9fc8` tail. The 392 tail hooks were simply ahead of the real return point.

## 3. 393 (running)

393 traces **all 382 BL sites** in `12d8174` with the same x8-safe naked stub:

- one 0x2000-byte trampoline page at `base+0x8050000`;
- 20 bytes per site (`ldr x16,#12; movz w17,#id; br x16; .quad stub`), 382×20 = 7,640 B;
- `g_post_real[512]` table.

The first `FX6_POST<id>_CALL` without `RET` is the exact blocking call. Late GPE capture
at `seconds-90` remains enabled.

## 4. Artifacts

| Item | Value |
|---|---|
| CPIO 392 | `guest-hybrid-fx6kernel-capid-grmreal392-tailtrace.cpio`, SHA-256 `2232b5ec…` |
| run 392 | `cp-bind-47c51739`, serial 2,956,615 B, SHA-256 `d199014db8e69ac01935d31cedda380de8d3c7b00bb293bd7a0a6714201a7bf5`, reason `interrupted` |
| CPIO 393 | `guest-hybrid-fx6kernel-capid-grmreal393-fulltrace.cpio`, 430,238,000 B, SHA-256 `7f178402…` |
| shim 393 | `libgrm-fbinit25-393.so`, SHA-256 `aa6cc435…` |

Durable copies under `work/fx6-385-17b9f-calltrace-20261107/`
(`serial-392.log`, `run-receipt-392.json`, `libgrm-fbinit25-393.c`, `fx6_post_stub_393.c`,
`libgrm-fbinit25-393.so`, manifest, runner).
