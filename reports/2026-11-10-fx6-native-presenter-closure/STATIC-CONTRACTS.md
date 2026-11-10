# FX6 Ver. 6.01 Cold-Boot & Native-Faithful Presenter Static Contracts (Q1 / Q2 / Q3)

**Date**: 2026-11-10  
**Track**: 1B — FX6 Ver. 6.01 Native `appFw.so` Cold-Boot Lifecycle & `FX6_NATIVE_FAITHFUL` Presenter Closure  
**Verification Script**: `work/fx6-native-presenter-closure-20261110/inspect_static_contracts.py`

---

## 0. Pinned Read-Only Donor Firmware Digests

All offsets and disassembly excerpts below are verified against the unmodified FX6 Ver. 6.01 (`nflasha15-files`) donor binaries:

| Binary | Size (Bytes) | SHA-256 |
| --- | ---: | --- |
| `bin/im.elf` | `40,920` | `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec` |
| `lib/libIMDB.so` | `79,728` | `a088ef303793497a443e89d6de4c8f12e07ec791c945f54e2dc1b52cd42db896` |
| `lib/libMWF.so` | `353,120` | `3c9666c49bde90076cf69af13295dc07e585d87c51a27ecaf7f1926df87d1782` |
| `lib/libgrm.so` | `265,376` | `0f9f922664ad23813fec3f2466d8f453a8741af11be9627583712b752cea9d2b` |
| `lib/libosal_uipc.so` | `43,752` | `fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a` |
| `lib/appFw.so` | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |

---

## 1. Contract Q1: `im.elf` Startup Order & `MWF_Init` ABI Signature

### 1.1 `im.elf` Phase Table & Exact Startup Ordering (`bin/im.elf` + `lib/libIMDB.so`)
- `bin/im.elf` (`e_entry = 0x402b30`, `main = 0x402490`) queries `IMDB_get_entries()` (`libIMDB.so` `imdb_raw + 0x100 = 0x1e970`, 72-byte descriptor stride) and executes phased initialization via `0x403df8(start_idx, stop_kind, flag_mask)`:
  1. **Sequential early phases** (`flag_mask = 0xff`, main thread `0x4025b0..0x402694`):
     - `0x08000000 -> 0x08000001` (`0x4025b8`)
     - `0x08000001 -> 0x08000002` (`0x4025d8`)
     - `0x08000002 -> 0x08000003` (`0x402650`)
     - **`0x08000003 -> 0x08000004` (`0x402670`)** — contains:
       - Entry `[29]` (`va = 0x1f198`): `kind = 0x20000002`, `id = 272`, `lib = "libkiki.so"`, `init = "KikiLogGenerator_init"`
       - **Entry `[32]` (`va = 0x1f270`)**: `kind = 0x20000002`, `flags = 0x1`, `target_mask = 0x7fffffff`, `module_id = 151`, `sel = 0`, `lib = "libMWF.so"`, `init = "MWF_Init"`, `arg0 = ""`, `arg1 = ""`
       - Entry `[36]` (`va = 0x1f390`): `kind = 0x20000002`, `id = 114`, `lib = "libgrm.so"`, `init = "GRM_Init"`
     - `0x08000004 -> 0x08000005` (`0x402690`)
  2. **Parallel middleware phase** (`0x08000005 -> 0x08000007`, `0x402698..0x4026cc`): spawns 3 OSAL worker threads (`0x402f94`, `flags` = `1, 2, 4`) and joins all three via `osal_wait_thread_exit`.
  3. **Business layer phase** (`0x08000007 -> 0x08000008`, `0x402700`): Entry `[149]` `BIZ_Init`.
  4. **Application phase** (`0x08000008 -> 0x08000009`, worker `0x4030a8` joined at `0x402730`):
     - **Entry `[151]` (`va = 0x213e8`)**: `kind = 0x20000004`, `flags = 0x1`, `target_mask = 0x7fffffff`, `module_id = 131`, `sel = 0`, `lib = "appFw.so"`, `init = "Application_System_Init"`, `arg0 = "AppConfig.so"`, `arg1 = "AppConfig.so"`.

### 1.2 `im.elf` Descriptor Kind Dispatch (`0x4061ec`, `0x405f5c`, `0x405e24`)
Disassembly of `bin/im.elf` (`0x4061ec..0x406288`, `0x405f5c..0x406034`, `0x405e24..0x405f50`) proves how `im.elf` invokes `MWF_Init` (`kind = 0x20000002`) vs `Application_System_Init` (`kind = 0x20000004`):

```asm
; bin/im.elf — type dispatcher (0x4061ec)
  40625c: 51000408   sub  w8, w0, #0x1            ; (kind - 0x20000001)
  406260: 7100091f   cmp  w8, #0x2                ; kinds 0x20000001..0x20000003 (incl. MWF_Init)
  406264: 540000c8   b.hi 0x40627c
  406268: aa1303e0   mov  x0, x19                 ; IMDB entry*
  40626c: 97ffff3c   bl   0x405f5c                ; 0-arg library init loader!
  ...
  40627c: 7100101f   cmp  w0, #0x4                ; kind == 0x20000004 (appFw.so)
  406280: 54000061   b.ne 0x40628c
  406284: aa1303e0   mov  x0, x19
  406288: 97fffee7   bl   0x405e24                ; 1-arg string init loader ("AppConfig.so")

; bin/im.elf — 0x405f5c (executes MWF_Init)
  405f9c: 97ffee85   bl   0x4019b0 <dlopen@plt>
  406004: 97ffef1f   bl   0x401c80 <dlsym@plt>
  406008: aa0003f4   mov  x20, x0                 ; x20 = &MWF_Init
  406024: f9401a60   ldr  x0, [x19, #0x30]
  406028: 97ffff2e   bl   0x405ce0                ; trace log helper
  40602c: d63f0280   blr  x20                     ; calls MWF_Init() with ZERO arguments; ignores w0!
  406030: 17ffffea   b    0x405fd8                ; mov w19, #0; return 0
```

### 1.3 `libMWF.so` `MWF_Init` (`+0x27e74`) & `_ZN3MWF6RsrcDP10smp_monErrE` (`+0x67e00`)
In `lib/libMWF.so`:
- `MWF_Init` (`+0x27e74`, size 4 bytes) is an unconditional tail-jump to `MWF::Initialize()` (`+0x27d68`).
- The very first instruction of `MWF::Initialize()` (`+0x27d68`) overwrites `x0` (`adrp x0, 0x65000`) to read the idempotency guard byte at `.bss + 0x65c89` (`_ZZN3MWF10InitializeEvE...`). Thus **`MWF_Init` is strictly `extern "C" void MWF_Init(void)`** (zero parameters, `void` return, idempotent).

```asm
; lib/libMWF.so — MWF_Init (+0x27e74) -> MWF::Initialize() (+0x27d68)
0000000000027e74 <MWF_Init>:
   27e74: 17ffec03   b    0x22e80 <_ZN3MWF10InitializeEv@plt>

0000000000027d68 <_ZN3MWF10InitializeEv>:
   27d68: d00001e0   adrp x0, 0x65000             ; x0 overwritten immediately (0-arg function)
   27d6c: 39722401   ldrb w1, [x0, #0xc89]        ; idempotency guard byte (+0x65c89)
   27d70: 350004c1   cbnz w1, 0x27e08             ; already initialized -> ret
   27d7c: 52800021   mov  w1, #0x1
   27d80: 39322401   strb w1, [x0, #0xc89]
   27d88: 97ffecee   bl   0x23140 <_ZN3MWF9MwfCommon4InitEv@plt>
   27d8c: 97ffeb6d   bl   0x22b40 <_ZN7Monitor4InitEv@plt>
   27d94: 97ffee67   bl   0x23730 <_Znwm@plt>     ; 0x50-byte MWF::ObjThread + StartThread()
   ...
   27dc0: 97ffefdc   bl   0x23d30 <_ZN11ObjLog_Mcmd4InitEv@plt>
   27dc4: 97ffedaf   bl   0x23480 <_ZN3MWF8RsrcMcmd4InitEv@plt>        ; -> calls MWF::RsrcDP::Initialize()
   27dc8: 97ffedbe   bl   0x234c0 <_ZN3MWF7InhMcmd4InitEv@plt>
   27dcc: 97ffee79   bl   0x237b0 <_ZN3MWF10ObjIf_Mcmd4InitEv@plt>
   27dd0: 97ffeaf8   bl   0x229b0 <_ZN3MWF5ObjIf4InitEv@plt>
   27ddc: 97ffeab9   bl   0x228c0 <_ZN3MWF14EventIdFactory10InitializeEjj@plt> ; (0x83e8, 0x800)
   27de0: 97ffebe0   bl   0x22d60 <_ZN3MWF12RsrcRelation10InitializeEv@plt>    ; -> allocates 3 ObjShLock*
   27dec: 17ffeb1d   b    0x22a60 <_ZN3MWF7InhInfo10InitializeEv@plt>          ; void tail-call
```

Inside `MWF::RsrcMcmd::Init()` (`+0x393b4`), `+0x393bc` calls `MWF::RsrcDP::Initialize()` (`+0x38cb0`), which allocates (`new(0x18)` + `MonCtrl::MonCtrl`) all five `MWF::RsrcDP` `MonCtrl*` globals in `.bss`:
- `_ZN3MWF6RsrcDP10smp_monDbgE` (`+0x67df8`)
- **`_ZN3MWF6RsrcDP10smp_monErrE` (`+0x67e00`)** — populated at `+0x38d20..0x38d30` (`str x19, [x22, #0xe00]`)
- `_ZN3MWF6RsrcDP10smp_monMsgE` (`+0x67e08`)
- `_ZN3MWF6RsrcDP10smp_monSeqE` (`+0x67e10`)
- `_ZN3MWF6RsrcDP10smp_monWrnE` (`+0x67e18`)

**Q1 ABI Conclusion**:
1. Signature is `void MWF_Init(void)` (do **not** treat `w0` return register as an integer `rc`; verify post-conditions by reading `_ZN3MWF6RsrcDP10smp_monErrE != NULL` via `dlsym`).
2. `MWF_Init()` must run in `appfw-launch` **after** `libkiki.so` / `libMWF.so` / `libgrm.so` preloads and **strictly before** `appFw.so` `Application_System_Init("AppConfig.so")` (which runs static/infra initializers that immediately dereference `RsrcDP::smp_monErr` and `RsrcRelation::mp_objShLock*`).

---

## 2. Contract Q2: `MWF::ObjShLock` Lifecycle & Exact Root Cause of `pthread_mutex_lock(0x28)`

### 2.1 `MWF::ObjShLock` Object Layout (`lib/libMWF.so +0x3b300`, `sizeof = 0xb8` = 184 B)
Static disassembly of `_ZN3MWF9ObjShLockC2Ev` (`+0x3b300`) and `_ZN3MWF9ObjShLock4LockENS0_9LOCK_MODEEi` (`+0x3b45c`) **refutes** the earlier Candidate 301 hypothesis that `0x28` came from a missing external service pointer inside an allocated `ObjShLock`:

```asm
; lib/libMWF.so — MWF::ObjShLock::ObjShLock() (+0x3b300)
000000000003b300 <_ZN3MWF9ObjShLockC2Ev>:
   3b308: 90000161   adrp x1, 0x65000
   3b30c: f9429c21   ldr  x1, [x1, #0x538]        ; &_ZTVN3MWF9ObjShLockE
   3b310: aa0003f3   mov  x19, x0                 ; this (0xb8 bytes)
   3b314: 91004021   add  x1, x1, #0x10
   3b31c: f8028401   str  x1, [x0], #0x28         ; *this = vptr; x0 = this + 0x28!
   3b320: d2800001   mov  x1, #0x0
   3b324: 97ffe03f   bl   0x23420 <pthread_mutex_init@plt> ; embedded pthread_mutex_t at this + 0x28!
   3b328: 91016260   add  x0, x19, #0x58
   3b330: 97ffdcf0   bl   0x226f0 <pthread_cond_init@plt>  ; embedded pthread_cond_t  at this + 0x58
   3b334: 91022260   add  x0, x19, #0x88
   3b33c: 97ffdced   bl   0x226f0 <pthread_cond_init@plt>  ; embedded pthread_cond_t  at this + 0x88

; lib/libMWF.so — MWF::ObjShLock::Lock(LOCK_MODE, int) (+0x3b45c)
000000000003b45c <_ZN3MWF9ObjShLock4LockENS0_9LOCK_MODEEi>:
   3b468: 9100a014   add  x20, x0, #0x28          ; x20 = &this->m_mutex (this + 0x28)
   ...
   3b470: aa1403e0   mov  x0, x20
   3b484: 97ffda1f   bl   0x21d00 <pthread_mutex_lock@plt> ; if this == NULL -> pthread_mutex_lock(0x28)!
```

### 2.2 Where All Three `ObjShLock` Singletons Are Constructed (`+0x3a57c`)
`MWF::RsrcRelation::Initialize()` (`libMWF.so +0x3a57c`), called directly by `MWF::Initialize()` at `+0x27de0`, allocates (`_Znwm(0xb8)`) and constructs all three global `ObjShLock*` pointers in `.bss`:
1. `_ZN3MWF12RsrcRelation15mp_objShLockMgrE` (`libMWF.so +0x68688`) — allocated at `+0x3a5bc..0x3a5d4`
2. `_ZN3MWF12RsrcRelation16mp_objShLockAcsrE` (`libMWF.so +0x68690`) — allocated at `+0x3a5d8..0x3a5f0`
3. `_ZN3MWF12RsrcRelation18mp_objShLockGlobalE` (`libMWF.so +0x68698`) — allocated at `+0x3a5f4..0x3a60c`

**Q2 Lifecycle Conclusion**:
- When `appfw-launch` skipped `MWF_Init()`, all three `.bss` pointers (`+0x68688`, `+0x68690`, `+0x68698`) remained `0x0`. Any `MWF::RsrcRelation` / `appFw.so` infra registration calling `mp_objShLock*->Lock(...)` passed `this = NULL`, computing `NULL + 0x28 = 0x28` and faulting inside `pthread_mutex_lock(0x28)`.
- Calling genuine `MWF_Init()` before `Application_System_Init` constructs all three `0xb8`-byte `ObjShLock` objects and initializes their embedded `pthread_mutex_t` (`+0x28`) and `pthread_cond_t` (`+0x58`, `+0x88`) fields natively, eliminating the need for any `pthread_mutex_*` null-pointer mask, `_ZNK7MonCtrl7GetFlagEv` null-mask, or `ObjShLock` bypass.

---

## 3. Contract Q3: `GRM_fbrmRegisterTriggerFrameworkCb`, Frame-Throttle Globals, & `App::start_utimer`

### 3.1 `libgrm.so` Registration & Dispatch ABI (`+0x236b8`, `+0x22c80`, `+0x22d04`)
Disassembly of `lib/libgrm.so` establishes the exact C and C++ method ABIs on `FBResourceManager`:

```asm
; lib/libgrm.so — C wrapper (+0x236b8)
00000000000236b8 <GRM_fbrmRegisterTriggerFrameworkCb>:
   236bc: aa0003e3   mov  x3, x0                  ; arg0: cb
   236c0: aa0103e4   mov  x4, x1                  ; arg1: user_data
   236c4: 97ffe1ef   bl   0x1be80 <_ZN17FBResourceManager11getInstanceEv@plt>
   236cc: aa0303e1   mov  x1, x3
   236d0: aa0403e2   mov  x2, x4
   236d4: 97ffe213   bl   0x1bf20 <_ZN17FBResourceManager26registerTriggerFrameworkCbEPFvPvES0_@plt>
   236d8: 52800000   mov  w0, #0x0                ; returns int 0

; lib/libgrm.so — storage (+0x22c80) & invocation (+0x22d04)
0000000000022c80 <_ZN17FBResourceManager26registerTriggerFrameworkCbEPFvPvES0_>:
   22c80: a9028801   stp  x1, x2, [x0, #0x28]     ; [this+0x28] = cb, [this+0x30] = user_data
   22c84: d65f03c0   ret

0000000000022d04 <_ZN17FBResourceManager16triggerFrameworkEv>:
   22d04: f9401401   ldr  x1, [x0, #0x28]         ; cb
   22d08: b4000061   cbz  x1, 0x22d14
   22d0c: f9401800   ldr  x0, [x0, #0x30]         ; x0 = user_data (1 argument!)
   22d10: d61f0020   br   x1                      ; cb(user_data) -> void
   22d14: d65f03c0   ret
```

Likewise, `GRM_fbrmRegisterDrawCompletionCb` (`libgrm.so +0x23794` -> `_ZN3grm17FBResourceManager24registerDrawCompletionCbEPFvPvES1_` at `+0x22cc8`) delegates with the **identical signature** `int GRM_fbrmRegisterDrawCompletionCb(void (*cb)(void *), void *user_data)`, invoked when `FBResourceManager::updateRequest` completes (`GRM_fbrmUpdate` `+0x235a8` / `GRM_fbrmNoUpdate` `+0x235e8`).

### 3.2 `appFw.so` `App::initialize` (`+0xc09da0`) & Frame-Gate State Machine (`+0xc091d0`, `+0xde4284`)
Inside `App::initialize` (`lib/appFw.so +0xc09da0`):
- `+0xc09de4`: `bl 0x12d9fc8` — waits on cold-boot `model_future::wait` (`+0x1acd874`).
- `+0xc09e08..0xc09e0c`: `add x0, x19, #0xa40; bl 0xde31ac` — calls `ScreenManager::initialize`, which constructs all 5 `DisplayPlugin`s and registers native Presenters (`+0xde10f4`, vtable `appFw + 0x2e8d950`, global table `appFw + 0x432ded0`), while `GraphicsEngine` (`+0x202d854`) registers `drawCompletionCb = appFw + 0xde4284`.
- `+0xc09e40..0xc09e48`: loads `[0x2ee7e38]` -> **`cb = appFw + 0xc091d0`**, `x1 = x19` (`App*`), calls **`GRM_fbrmRegisterTriggerFrameworkCb`**.
- `+0xc09e4c..0xc09e50`: `mov x0, x19; bl 0xc09c14` — calls **`App::start_utimer(App*)`**.

Why the trigger/draw callbacks are mandatory for `App::run` (`+0xc0a69c`):
- When `App::run` renders a frame (`+0xc0aca4: bl 0xc099e4` -> `WidgetSystem::notifyDraw` -> `GraphicsEngine::drawFramebuffer`), it sets two frame-gate globals:
  - `*(int*)(appFw + 0x2f197d4) = 2` (`+0xc0aa20` / `+0xc0ac6c`)
  - `*(int*)(appFw + 0x2f197d0) = 3` (`+0xc0accc`)
- At the top of each event/timer cycle (`+0xc0a960..0xc0a994`), `App::run` checks `(*0x2f197d4 != 2) || (*0x2f197d0 != 3)`. If both remain `(2, 3)`, `+0xc0a994: cbz w24, 0xc0ad0c` **skips all subsequent `notifyDraw`/`drawFramebuffer` passes**.
- Disassembly of `triggerFrameworkCb` (`+0xc091d0`) and `drawCompletionCb` (`+0xde4284`):

```asm
; lib/appFw.so — triggerFrameworkCb (+0xc091d0)
  c091d0: a9bf7bfd   stp  x29, x30, [sp, #-0x10]!
  c091d4: 52800000   mov  w0, #0x0
  c091dc: 94076c1a   bl   0xde4244                ; *(int*)(appFw + 0x2f197d4) = 0
  c091e0: 52800000   mov  w0, #0x0
  c091e4: a8c17bfd   ldp  x29, x30, [sp], #0x10
  c091e8: 14076c20   b    0xde4268                ; *(int*)(appFw + 0x2f197d0) = 0

; lib/appFw.so — drawCompletionCb (+0xde4284)
  de4284: a9bf7bfd   stp  x29, x30, [sp, #-0x10]!
  de4288: 52800000   mov  w0, #0x0
  de4290: 97ffffed   bl   0xde4244                ; *(int*)(appFw + 0x2f197d4) = 0
  de4294: 52800020   mov  w0, #0x1
  de4298: a8c17bfd   ldp  x29, x30, [sp], #0x10
  de429c: 17fffff3   b    0xde4268                ; *(int*)(appFw + 0x2f197d0) = 1
```

### 3.3 `App::start_utimer` (`+0xc09c14`) Trigger Conditions
- `App::start_utimer` (`+0xc09c14..0xc09d98`):
  1. Allocates queue/timer slot via `osal_snd_sync_direct(0x910040, ...)` (backed by `/dev/utimer` from `utimer.ko`, already loaded in guest `init` with `FX3_UTIMER_RC=0`).
  2. Registers OSAL queue callback `0xc09498` (`osal_reg_msg_queue_cb`) -> `App::utimer_cb` (`+0xc09bd4`).
  3. Starts periodic hardware/kernel timer via `0xc0924c(&handle, 20000 /* 20 ms = 50 Hz */, 2 /* periodic */)`.
  4. On each tick, `App::exec_utimer` (`+0xc09ac8`) posts a 28-byte OSAL message with ID `0x02010094` (`src = 0x830128`) to `App` queue `0x5503e0` (`osal_snd_msg` at `+0xc09bbc`), waking `App::recv_event_i` (`+0xc0a208` `osal_rcv_msg_tmo(0x5503e0)`).
- Previously, `0xc09e50` (`bl App::start_utimer`) was NOPed in `libgrm-fbinit9.so` (`patch_appfw_nops`) only because `App::initialize` had never organically reached `+0xc09e50` or lacked `triggerFrameworkCb` pumping. Restoring `0xc09e50` + firing `GRM_fbrmRegisterDrawCompletionCb` on `GRM_fbrmUpdate`/`GRM_fbrmNoUpdate` and `GRM_fbrmRegisterTriggerFrameworkCb` on a periodic 25–50 Hz vsync pump closes the entire native event-and-frame loop.

---

## 4. Cold-Boot Sequence Tail & `Application_System_Init` Threading Contract (For Round 2)

1. **`Application_System_Init` (`appFw.so +0xc0b044..0xc0b128`)**:
   - Sends startup notification to `0x8f013a`, copies config filename (`"AppConfig.so"`), and at `+0xc0b118` calls `0x222dd58` to spawn the `App` OSAL thread (`0x5503e0`, TID ~225) and **immediately returns `0`**.
   - Therefore, `appfw-launch` must **not** touch `uxengine` globals after `init("AppConfig.so")` returns; it must simply sleep (`pause()` / `sleep(3600)`) while the `App` thread executes `App::initialize` -> `App::run`.
2. **`model::sequence_cold_boot::execute` (`appFw.so +0x1cd826c..0x1cd86b0`)**:
   - Runs on `SeqQueueCommon` worker thread (TID ~250).
   - At `+0x1cd86a4: bl 0x1cd80dc`, invokes `init_hdmi(this)`:
     - `+0x1cd80fc: bl 0x20d00bc` -> `adf_set_hdmi_format` (`+0x20f158c`) -> `infra_wrapper_bb::detail::send_and_wait_cmp_i` (`+0x20ef604`), which sends command `{0x200d, 0x032d, ...}` to UIPC queue **`0x92840747`** with dynamic reply queue `src = 0x81cf....` (`osal_set_msg_src` `[msg - 0xc]`) and blocks in `osal_rcv_msg_tmo(reply_qid, &reply, -1)` expecting a 12-byte completion `{0x200d, 0x132d, 0x000c, 0x8001, u32 status=0}`.
     - `+0x1cd81b4: bl 0x20d1cfc` -> calls `+0x20f2394` (`str wzr, [x1]; ret`, already a native no-op returning status `0`).
   - **Immediately after `init_hdmi` returns (`+0x1cd86a8..0x1cd86ac`)**:
     ```asm
     1cd86a4: 97fffe8e   bl  0x1cd80dc   ; init_hdmi(this)
     1cd86a8: f9400ae0   ldr x0, [x23, #0x10]
     1cd86ac: 97f7d1ff   bl  0x1accea8   ; sets *promise = 1, unlocks 0x5a3b7a8, notify_one()!
     ```
   - `init_hdmi` is the **final gate** in `sequence_cold_boot::execute`: once `0x92840747` (`cmd 0x032d`) receives a valid 12-byte UIPC completion (`status = 0`), `+0x1cd86ac` fulfills the cold-boot promise and wakes `App::initialize` out of `model_future::wait` (`+0x1acd874` / `+0xc09de4`) directly into `ScreenManager::initialize` (`+0xc09e0c` -> `+0xde31ac`)!

---

## 5. Supplementary Static Contracts Uncovered & Verified in Rounds 1–3

### 5.1 `MonDrv::Init` (`libMWF.so +0x3f1dc`) FixedArea `Backup_read_8Byte` Contract
- During `MWF_Init() -> MWF::Initialize() -> Monitor::Init() -> MonDrv::Init()` (`libMWF.so +0x3f21c..0x3f2bc`), `MonDrv::Init` queries two 64-bit physical carveout descriptors before `mmap`ing `/dev/mem`:
  - `Backup_read_8Byte(0x00fa0028)` -> `FixedAreaTop` (mapped to safe guest RAM carveout `0x429200000UL`)
  - `Backup_read_8Byte(0x00fa005d)` -> `FixedAreaSize` (must satisfy `>= 0x5b400`; mapped to `0x00100000UL`)
- Without these two Backup IDs, `mmap(..., 0, ..., 0)` returns `MAP_FAILED` (`"ERROR : Failed to mmap!"`) and `MonQueue::GetQueueRemain` (`libMWF.so +0x409d0`) dereferences NULL.

### 5.2 `appFw.so` `R_AARCH64_TLSDESC` GOT Entries (`+0x2ef29f0`, `+0x2ef2a00`)
- Auditing `objdump -R lib/appFw.so` against all 832 entries in historic `got_table_fx6.inc` proves 830 entries are `R_AARCH64_JUMP_SLOT`, whereas 2 entries are 16-byte **`R_AARCH64_TLSDESC`** descriptors managed by `ld-linux`:
  - `appFw + 0x2ef29f0`: `_ZSt11__once_call`
  - `appFw + 0x2ef2a00`: `_ZSt15__once_callable`
- Overwriting word 0 of a `TLSDESC` pair with `dlsym()` replaces `_dl_tlsdesc_return` with a `rw-p` TLS/data address, causing `SEGV_ACCERR (code=2)` on the first `std::call_once` / `std::promise::set_value` (`appFw + 0x2159a24`). Skipping these 2 offsets (`skipped_tlsdesc=2`) eliminates the fault completely.

### 5.3 Post-`ScreenManager::initialize` Screen-Open IPC Contracts
1. **RTC Status (`appFw.so +0x2159840..0x2159c80`, `infra_wrapper_rtc::detail::get_rtc_status`)**:
   - Registers callback on queue `0x81d705bd`, sends 2-byte `{0x03, ...}` to `0x92d2091c`, and blocks on a `std::future` until `0x81d705bd` receives 2-byte `{0x03, 0x00}` with `src == 0x92d2091c` (`status = 0`).
2. **LED / SubLCD Indicator Service (`libInfraIndctr.so +0x56e4..0x5dc0`, `+0x76c8..0x7c38`)**:
   - `CIFInfraIndctr` sends 36-byte (`0x24`) `InfraIndctr::TMsg` requests to `0x807e002f`. Jump-table analysis at `libInfraIndctr.so +0xcd00` shows commands `{2, 4, 5, 6, 17}` are synchronous (`rcv_msg` on `0x807e0030` expecting 36-byte reply with `u32[0] = 7`, `u32[2] = 0`), while `{1, 3, 8, 9, 10, 12, 14, 16}` are fire-and-forget.
3. **Complete `0x20ef604` BB/CP Infinite-Timeout RPC Family (`appFw.so +0x20ee000..0x20fd000`)**:
   - Static scan of all callers to `0x20ef604` shows `0x9058003f`, `0x9059000e`, `0x905a0048`, and `0x90b201aa` use a finite 1000 ms timeout (`+0x20ef6a0`), while **exactly four** destinations use `osal_rcv_msg_tmo(reply_qid, -1)` (`src_qid = 0x81cf61xx`):
     - `0x92840747` (`w0 = 0x200d`, `rsp_cmd = req_cmd | 0x1000`, `r32[2] = 0`)
     - `0x909a015a` (`w0 = 0x2500`, `rsp_cmd = req_cmd | 0x8000`, `r32[2] = 0`)
     - `0x909c015b` (`rsp_cmd = req_cmd | 0x8000`, `r32[2] = 0`, `r8[12] = req[8]` on `0x0101`)
     - `0x912f0335` (zeroed status block)
4. **`GRM_GPERMCmdCbParamRecord` & `GraphicsEngine::drawFramebuffer` ABI (`libuxengine.so +0x839c8`, `libgemini-grm.so +0x7e68`, `libgrm.so +0x30f04`)**:
   - `ux::gfxeng::GraphicsEngine::drawFramebuffer()` (`libuxengine.so +0x839c8..0x83aac`) returns `bool` (`int` in `w0`: `1` when swapped, `0` when clean).
   - `gemini::GRMRenderer::DrawCompCb(GRM_GPERMCmdCbParamRecord*)` (`libgemini-grm.so +0x7e68`) loads `GpeFlushCbParam*` from `[x0 + 0x08]` (`ldr x19, [x0, #0x8]`), not `x0` directly; `GRM_gpermDrawFlush(cb, ud)` (`libgrm.so +0x30f04`), `GRM_gpermFillrect`, and `GRM_gpermRectblit` must pass `&GRM_GPERMCmdCbParamRecord { .cmd_id = 1, .user_data = ud }`.
5. **Downstream Media-Slot Contract (`libmpr.so +0x53c850`, `libXavcMxfGetSlotTypeFromMediaId`)**:
   - When extended `0x909a015a` RPCs advance `SeqQueueCommon` to `mpr::SetMovieRecParam` -> `libXavcMxf::SetClipName` (`libmpr.so +0x54c184`), `libXavcMxfGetSlotTypeFromMediaId(uint32_t mediaId)` (`+0x53c850..0x53c8c4`) requires `mediaId == 0x1000` (Slot A -> `1`) or `mediaId == 0x1010` (Slot B -> `2`), otherwise calling `__assert_fail("0", "libXavcMxf.cpp", 274, ...)`. Populate `libInfraMediaConfig.so` (`InfraMediaConfig_Init` `+0x6750`) / `0x807b002b` (`libInfraAvbbc.so`) media-slot IDs in the next iteration to cross `SetMovieRecParam`.

