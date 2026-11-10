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
| `lib/libgemini-grm.so` | `51,800` | `f47c8f3ecff0710d2c246d7d0c0ccdb5381a9f39b1b8d68464d184c0be8070b9` |
| `lib/libosal_uipc.so` | `43,752` | `fe248d226863722b2ab911ca70195c616566b8cb96a2ab13b920ee25202a7b9a` |
| `lib/libbackup.so` | `14,232` | `e003e2d8a1f42fdf629dda012a01f225940c016b2ab4dbf482a761378e8d286f` |
| `lib/libInfraMediaConfig.so` | `52,312` | `9709656102d582bd0d91d7a612abb076873d533b1e0e2ed042c6b2611d56c1c3` |
| `lib/libInfraAvbbc.so` | `1,743,200` | `4ea694694cd791b1e5bc09c7a550ef2bea101c33c31c3875017829a969a5bcab` |
| `lib/libInfraInput.so` | `93,448` | `1851e2dc8515d2240b9ecaffd58591207336c5f061b1af0d3585d7b082a41f02` |
| `lib/libCertificateManager.so` | `198,880` | `a96d54c83b2aa001a51cc643adf53ae4b4a236e6a006335ca5606487d84fe45e` |
| `lib/libmpr.so` | `28,921,824` | `814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e` |
| `lib/appFw.so` | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` |
| `CHAPLIN/CX95898_NTSC.bin` | `2,253,333` | `e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e` |

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
   - When extended `0x909a015a` RPCs advance `SeqQueueCommon` to `mpr::SetMovieRecParam` -> `libXavcMxf::SetClipName` (`libmpr.so +0x54c184`), `libXavcMxfGetSlotTypeFromMediaId(uint32_t mediaId)` (`+0x53c850..0x53c8c4`) requires `mediaId == 0x1000` (Slot A -> `1`) or `mediaId == 0x1010` (Slot B -> `2`), otherwise calling `__assert_fail("0", "libXavcMxf.cpp", 274, ...)`. Detailed full-chain disassembly and BK4 byte layouts are documented in §6 below.

---

## 6. Round 4 (Step 4A): Media-Slot Initialization, `0x80cf016d` vs `0x807b002b`, BK4 Factory Bytes, & `mpr::SetMovieRecParam`

### 6.1 `im.elf` (`0x401cd0..0x401dc0`) & `libIMDB.so` Pre-`AppFw` Startup Order
- Disassembly of `bin/im.elf` at `0x401cd0..0x401dc0` shows `0x401cd0..0x401dc0` lies inside `im.elf`'s `.plt` stub table (`0x401960..0x401ef0`; `0x401d00` is `<_ZN4imcm10ImcmThreadD1Ev@plt>`), whereas `im.elf` dispatches module initializers dynamically via `lib/libIMDB.so` (`IMDB_GetData` descriptor table at `libIMDB.so` `.data.rel.ro` `0x1cde0..0x20fd0`, stride `0x78` = 120 bytes).
- Extracting `libIMDB.so` entries `[64..88]` establishes the exact pre-`Application_System_Init` (`[120]`) infrastructure initialization sequence:
  - `[65]` (`0x1fb98`): `libInfraAvbbc.so` -> `InfraAvbbc_Init` (`flags = 0x2`, `kind = 0x20000002`)
  - **`[66]` (`0x1fc10`)**: **`libInfraMediaConfig.so` -> `InfraMediaConfig_Init`** (`flags = 0x2`, `kind = 0x20000002`)
  - `[67]` (`0x1fc88`): `libInfraMediaCommon.so` -> `mcmn_init`
  - `[79]` (`0x20228`): `libInfraMediaMount.so` -> `InfraMediaMount_Init`
  - `[80]` (`0x202a0`): `libInfraMediaDetect.so` -> `InfraMediaDetect_Init`
  - `[86]` (`0x20570`): `libmprctrl.so` -> `InfraMprCtrl_Init`
  - `[87]` (`0x205e8`): `libMprSeq.so` -> `MprSequencerIf_Init`
  - `[120]` (`0x21560`): `appFw.so` -> `Application_System_Init`

### 6.2 `libInfraMediaConfig.so +0x6750` (`InfraMediaConfig_Init`) & `MediaTtlInf` Table Layout
Disassembly of `lib/libInfraMediaConfig.so` (`+0x6538..0x6790`, `+0x5de4..0x6040`, `+0x5190..0x5460`):
- `InfraMediaConfig_Init` (`+0x6750`):
  - Allocates `new(0xa0) InfraMediaConfig` (`+0x6538`) and stores the singleton at **`libInfraMediaConfig.so +0x1c470`** (`_ZN16InfraMediaConfig8m_pMyObjE`).
  - Calls `InfraMediaConfig::CreateMediaInfoTbl()` (`+0x5de4`), which scans up to 16 Backup slots (`slot = 0..15`), allocates `MediaTtlInf[slot_count]` (element stride **`0x110` = 272 bytes**) at **`[this + 0x18]`**, writes `slot_count` (`uint32_t`) at **`[this + 0x20]`**, sets **`[this + 0x98] = 1`** (`m_isReady`), and registers synchronous UIPC handler `InfraMediaConfig::CallbackPoint` on queue **`0x80cf016d`** via `MWF::EventWrapper::RegisterCallBack(0x80cf016d, ...)` (`+0x65e8..0x65fc`).
- `MediaTtlInf` element layout (`stride = 0x110`, populated by `CreateMediaInfoByBackup` `+0x5b50`):

| Offset | Type | Field | FX6 Slot A (`slot 0`) | FX6 Slot B (`slot 1`) | FX6 Slot 7 | FX6 Slot 8 |
| --- | --- | --- | --- | --- | --- | --- |
| `+0x00` | `uint32_t` | `mediaId` | `0x00001000` | `0x00001010` | `0x00002000` | `0x00003001` |
| `+0x04` | `uint16_t` | `idOffset` / index | `0` | `1` | `2` | `3` |
| `+0x06` | `uint16_t` | `devId` | `0xdf10` | `0xdf20` | `0xd600` | `0xd517` |
| `+0x08` | `uint32_t` | `mediaAttr` (`off 6..9`) | `0x00000a03` | `0x00000a03` | `0x00000000` | `0x00000000` |
| `+0x0c..0x3f` | `uint8_t[]` | slot capability flags (`off 10..63`) | `slotNo=1, bus=0x41...` | `slotNo=2, bus=0x41...` | virtual/net | SD/aux |

### 6.3 Disambiguating `0x807b002b` vs `0x80cf016d`
Static cross-referencing across `appFw.so`, `libInfraTp.so`, `libInfraAvbbc.so`, and `libInfraMediaConfig.so` resolves a critical queue identity distinction:
1. **`dest = 0x807b002b` is Touch Panel (`libInfraTp.so`), NOT Media Slots**:
   - `appFw.so +0x215b9a0..0x215bc0c` (`+0x215c38c`) sends 12B/16B commands (`cmd = 1, 2, 3, 5`) to `0x807b002b`, which is registered by `libInfraTp.so` (`infra_tp_init`, `+0x3a70`), already initialized natively inside `0x20ed13c` (`[57]`). `libInfraAvbbc.so +0xdad8` is unrelated (`avbbc` internal helper), whereas `libInfraAvbbc.so +0x142638` references subsystem `0x807b` for touch-coordinate tracking.
2. **Media-Slot Discovery Uses Synchronous `osal_snd_sync_msg(0x80cf016d, msg)` (`appFw.so +0x2125930..0x2125bb0` -> `+0x215c4a8`)**:
   - Because `appFw.so` uses **`osal_snd_sync_msg`** (`+0x215c4a8`) rather than asynchronous `osal_snd_msg`, `0x80cf016d` calls did not appear in Round 3's `osal_snd_msg` trace!
   - During `0x20ed13c` (`infra70`), `appFw.so +0x2125930` queries `0x80cf016d`:
     - **`cmd = 0x1004` (`GetMediaIDByAtrribute`, `sz = 0x60`)**: `InfraMediaConfig::GetMediaIDByAtrribute` (`+0x6044`) fills `[msg + 0x1c] = count` and `[msg + 0x20 + 4*i] = mediaId[i]`. `appFw.so +0x21259b8..0x2125a30` stores `count` into **`appFw.so +0x5c3e7e0`** and populates the 40-byte-stride (`0x28`) global media-slot array at **`appFw.so +0x5c3e560`** (`slot[0].mediaId = 0x1000`, `slot[1].mediaId = 0x1010`).
     - **`cmd = 0x1008` (`GetIdOffset`, `sz = 0x20`)** & **`cmd = 0x1000` (`GetMediaInfoCmd`, `sz = 0xe4`)**: populates per-slot `idOffset` and capability structs into `appFw.so +0x5c3e560 + i * 0x28`.

### 6.4 Genuine FX6 (`fx6_chaplin_ntsc`) BK4 Backup Contract (`libbackup.so` + `0x00cf0000..0x00cf040b`)
Disassembly of `libbackup.so` (`+0x1d5c..0x1f4c`) and `libInfraMediaConfig.so` (`+0x5190..0x5420`) exposes why Round 3's `backup_sync_msg` zero-stub (`*ret = 0`) would still zero out `InfraMediaConfig` unless exact `Backup_*` return semantics and BK4 bytes are honored:
- `Backup_get_datasize(uint32_t id)` (`libbackup.so +0x1d5c`) must return **`1`** (byte size) for `0x00cf0000..0x00cf040b`, `0x010d006c`, and `0x010d0085`.
- `Backup_read(uint32_t id, void *buf)` (`libbackup.so +0x1e14`, **2 arguments**) must write the 1-byte factory value to `*(uint8_t*)buf` and **return `1` (`datasize`)**, because `getDevIDbyBackup` (`+0x52e8: cmp w0, #0; b.gt`) and `GetBackupVal` (`+0x53d8: cmp w20, w0; b.eq`) treat `ret <= 0` as failure!
- `Backup_read_multi(const uint32_t *ids, void **ptrs)` (`libbackup.so +0x1f0c`) takes a `0`-terminated `ids[]` array (`64` IDs `0x00cf0000 + (slot<<6) + 0..63`) and `void *ptrs[64]`, and **must return `64` (`0x40`)**, because `ReadBackupConfigInfo` (`+0x521c: cmp w0, #0x40; b.eq`) zeroes all 64 bytes (`stp xzr, xzr, [x19, ...]`) if `w0 != 0x40`!
- Exact factory bytes extracted from Sony FX6 `fx6_chaplin_ntsc` BK4 image:
  - **Slot 0 (`0x00cf0000..0x00cf003f`)**: `00 10 00 00 10 df 03 0a 00 00 00 03 01 03 00 41 40 10 00 2a 01` + 43x `00` (`mediaId = 0x1000`, `devId = 0xdf10`).
  - **Slot 1 (`0x00cf0040..0x00cf007f`)**: `10 10 00 00 20 df 03 0a 00 00 00 03 02 03 00 41 40 18 00 32 02 00 00 00 00 00 00 02` + 36x `00` (`mediaId = 0x1010`, `devId = 0xdf20`).
  - **Slot 7 (`0x00cf01c0..0x00cf01ff`)**: `00 20 00 00 00 d6 00 00 00 00 00 05 00 03 00 41 00 00 00 00 00 00 00 00 00 00 00 ff` + 36x `00` (`mediaId = 0x2000`, `devId = 0xd600`).
  - **Slot 8 (`0x00cf0200..0x00cf023f`)**: `01 30 00 00 17 d5 00 00 00 00 00 01 00 03 00 08 00 00 00 01 00 00 00 00 00 00 00 ff` + 36x `00` (`mediaId = 0x3001`, `devId = 0xd517`).
  - **Flags**: `0x00cf0408 = 0x01`, `0x00cf040a = 0x01` (`0x00cf0400..0x00cf040b` otherwise `0x00`), `0x010d006c = 0x01`, `0x010d0085 = 0x01`.

### 6.5 `appFw.so +0x213d13c` -> `libmpr.so` `mpr::SetMovieRecParam` (`+0x16c5e0..0x16c74c`) -> `libXavcMxf::SetClipName` (`+0x54bf28`)
- `appFw.so +0x1cc4d48 -> +0x20de62c -> +0x213d13c` builds `mpr::movieRecParam` (`sp + 0x378`):
  - `movieRecParam + 0x234` (`sp + 0x5ac`): `uint32_t clipNameParamCount` (`2`).
  - `movieRecParam + 0x238` (`sp + 0x5b0`): `mpr::ClipNameParam clipNameParams[4]` (element stride **`0x1a4` = 420 bytes**):
    - `+0x00` (`uint8_t`): `isAllSlot` (`0` = per-slot)
    - `+0x04` (`uint32_t`): `mediaId` (`ClipNameParam[0].mediaId` at `sp + 0x5b4` = `0x1000`, `ClipNameParam[1].mediaId` at `sp + 0x758` = `0x1010`, sourced from `appFw.so +0x5c3e560` media-slot table)
    - `+0x08..0x1a3`: clip prefix/title strings
- `libmpr.so` `mpr::SetMovieRecParam(const mpr::movieRecParam&)` (`+0x16c5e0..0x16c74c`) passes `(count = [param + 0x234], array = param + 0x238)` to `libXavcMxf::SetClipName` (`+0x54bf28..0x54c184`), which loops over `i = 0..count-1` (`stride = 0x1a4`), loads `w0 = *(uint32_t*)(elem + 0x04)` when `elem[0] == 0`, and calls `libXavcMxfGetSlotTypeFromMediaId(w0)` (`+0x53c850`):
  - `w0 == 0x1000` -> returns `1` (Slot A)
  - `w0 == 0x1010` -> returns `2` (Slot B)
  - `w0 == 0` (when `InfraMediaConfig_Init` was skipped) -> `__assert_fail("0", "libXavcMxf.cpp", 274, ...)`.

### 6.6 Post-Media-Slot `SeqQueueCommon` Closure: Remote DMM (`0x9061003c`, `appFw.so +0x20fea28`)
- Immediately after `mpr::SetMovieRecParam` returns cleanly on `SeqQueueCommon`, `appFw.so +0x20fea28 -> +0x20fef80` (`infra_wrapper_dmm` remote DMM service) sends a 40-byte (`0x28`) UIPC request (`u32[0] = 0x00000001` or `0x00000002`, `src = 0x81d005ba`) to **`0x9061003c`** and blocks indefinitely in `osal_rcv_msg_tmo(0x81d005ba, &reply, -1)`.
- Replying with a 40-byte UIPC pool block `{ u32[0] = 4, u32[1] = 0 /* status OK */, ... }` to `0x81d005ba` (`src = 0x9061003c`) completes **100% of `SeqQueueCommon` cold-boot/open tasks**, returning `SeqQueueCommon` (`tid=253`) to idle (`futex_wait_queue_me`).

### 6.7 `SeqQueueNetwork` Infinite-Wait UIPC Family (`appFw.so +0x215c6d0`) & `libCertificateManager.so`
- Once `SeqQueueCommon` finishes, `AppFw` (`tid=225`) waits inside `Presenter::open` (`appFw.so +0x13b3670 -> model_future::wait +0x1acd988`) on **`SeqQueueNetwork` (`tid=264`)**.
- Disassembly of `appFw.so +0x215c6d0..0x215c8f0` reveals a shared synchronous-over-async UIPC helper (`send_and_wait_reply(dest, reply_qid, req_buf, req_len, expected_rsp_cmd)`) used across network/Wi-Fi/FTP/streaming wrappers, which sends on `osal_snd_msg` and blocks with `timeout = -1` on `reply_qid` until `r32[0] == expected_rsp_cmd` and `r32[1] == 0`:
  - `0x832609f2` (`reply_qid = 0x832609f3`): `rsp_cmd = req_cmd + 0x100`
  - `0x032789f3` (`reply_qid = 0x032789f4`): `rsp_cmd = req_cmd + 0x100`
  - `0x012282f6` (`reply_qid = 0x012282f7`): `rsp_cmd = req_cmd + 0x100`
  - `0x01af852f` (`reply_qid = 0x01af8530`): `rsp_cmd = req_cmd + 0x100`
  - `0x03008969` (`reply_qid = 0x0300896a`): `rsp_cmd = req_cmd + 0x100`
  - `0x91670464` (`reply_qid = 0x81e106cf`): `rsp_cmd = req_cmd | 0x8000` (16-bit header)
  - `0x9167046a` (`reply_qid = 0x81e206d0`): `rsp_cmd = req_cmd | 0x8000`
  - `0x807c0038` (`reply_qid = 0x81d405be`): `u32[0] = req_u32[0] + 1, u32[1] = 0`
- Immediately after `0x807c0038`, `SeqQueueNetwork` invokes `_ZN15CertificateUtil22InitCertificateManagerEv` via `appFw.so` GOT (`+0x2ef34c0`). Preloading donor `/usr/lib/libCertificateManager.so` (and sibling donor libraries in `appfw-launch`) resolves all `CertificateUtil::*` GOT slots natively, allowing `SeqQueueNetwork` to finish and **waking `AppFw` (`tid=225`) out of every `model_future::wait` barrier into steady-state `App::run`**.

### 6.8 Full Donor `CX95898_NTSC.bin` BK4 Mapping & Zero-NOP `Application_System_Init` (`nop_count = 0`)
- Rather than serving synthetic zeros for `Backup_read` / `Backup_nread_multi` (`libbackup.so +0x1f0c` / `+0x1fb4`), `build_and_run_round.py` packs the unmodified FX6 NTSC factory Backup image (`CHAPLIN/CX95898_NTSC.bin`, `2,253,333` bytes) at `/etc/fx6_chaplin_ntsc.bk4`.
- `libgrm-fbinit9.c` parses the real Sony `BK4\0` index table (`subsys` directory -> per-item `{id, size, data_offset}` records) at startup (`FX6_BK4_MMAP status=ok bytes=2253333`) and serves genuine factory bytes across `Backup_get_datasize`, `Backup_read`, `Backup_read_multi`, and **`Backup_nread_multi`** (`5,394` + `98` multi-item factory reads during `model::backup_manager` init!).
- With genuine `MWF_Init()`, `InfraMediaConfig_Init()`, `InfraInput`, and `CX95898_NTSC.bin` active, **all four historical `appFw.so` `.text` NOPs (`0x12d824c`, `0x12d8250`, `0x12d8254`, `0xc09e50`) are completely removed (`FX6_PATCH_PLAN nop_count=0`)** — `appFw.so` executes 100% unmodified `.text` instructions!

### 6.9 `rep_boot_controller::process_MODEL_POWER_ON_COMP` (`appFw.so +0x1009b90..0x100ab4c`) Screen Transition Chain
Disassembly of `rep_boot_controller::process_MODEL_POWER_ON_COMP` (`appFw.so +0x1009b90..0x100ab4c`) explains why `18rep_boot_presenter` (`slots[0]`, pure black `0xff000000` boot screen) stays open unless four hardware/handover contracts are satisfied:
1. **Diadem Handover Status (`0x02cf15c8`, `1` byte)**:
   - Read during model startup into property `3927` (`0xf57`). In raw factory BK4 (`CX95898_NTSC.bin`), `0x02cf15c8 == 0x00` (`BEFORE_BOOT`), whereas on real hardware the bootrom/updater writes **`0x03`** (`HAND_OVER_STATUS_AFTER_UUD_FROM_DIADEM_PRO_COMP`) before launching `im.elf`.
2. **Firmware Version Match (`0x02cf0069` = `0x00060001` vs `osal_snd_sync_msg(0x004b024e)` = `(6, 1)`)**:
   - `appFw.so +0x1cc3810 -> +0x215928c` queries `osal_snd_sync_msg(0x004b024e)` (`u16 major = 6, u16 minor = 1` at `msg + 0x10..0x12`) and compares the formatted string `"6.01"` against `Backup_read(0x02cf0069)` (`u32 = 0x00060001`). A mismatch forces `handover_3927` to `1` (firmware-update black screen).
3. **Physical Power Switch `PW_SW` (`InfraInput` `0x007a0001`, `phy_key_id = 1 -> status = 1`)**:
   - `appFw.so +0x1cc3998` checks physical key `PW_SW` (`phy_key_id = 1`) via `InfraInput` (`0x007a0001`). Calling `InfraInput` initialization (`1,127` registered keys in `Instance + 0x38`) and setting `PW_SW` `status = 1` (`power switch ON`, instead of `0` = power-off shutdown) prevents `rep_boot_controller` (`+0x1009ecc`) from branching to power-down standby.
4. **Initial-Setting Flag (`0x02cf0068`, `1` byte, read at `appFw.so +0x2167d40 -> +0x1a54098`, model property `0x1c54`)**:
   - **`0x02cf0068 == 0x01` (Factory Out-of-Box Default, `--initial-setting-done 0`)**:
     - `+0x1a088c0` returns `1` -> `+0x1009f4c` opens `screen_id = 7`: **`slots[2] = 37procam_menu_initial_setting_presenter`** (`vptr_off = 0x2e8eac0`, Area/Date/Time initial setup menu with anti-aliased Sony Cinema Line amber `0xffffaa00` foreground glyphs!).
   - **`0x02cf0068 == 0x00` (Initial Setup Completed, `--initial-setting-done 1`)**:
     - `+0x1a088c0` returns `0` -> branches to `+0x100aae8` -> opens `screen_id = 2`: **`slots[0]` transitions from `18rep_boot_presenter` into `25procam_shooting_presenter` (`vptr_off = 0x2e8d9e0`, `screen = 0x7f66127730`)** alongside `slots[2] = 35procam_msg_1label_1button_presenter` (`vptr_off = 0x2e8e208`, `screen = 0x7f6612da80`)!
   - From `25procam_shooting_presenter`, `31procam_big6_menu_home_presenter` (confirmed in `appFw.so` RTTI) is the `HOME`-button menu presenter invoked when `InfraInput` dispatches a `HOME` key press after dismissing any modal dialog on `slots[2]`.

### 6.10 `libgemini-grm.so` (`+0x7700..0x7e78`) `GRM_gpermFillrect` / `GRM_gpermRectblit` Struct Layouts & Offscreen Flip Discipline
Disassembly of `gemini::GRMRenderer::fillRect` (`libgemini-grm.so +0x7700..0x7950`) and `gemini::GRMRenderer::bitBlt` (`+0x79b8..0x7df8`) revealed two critical rendering bugs in early shims and established the exact binary struct layouts:
1. **Offscreen Clear Clobber Bug**:
   - During every `ux::gfxeng::GraphicsEngine::drawFramebuffer()` pass, `libuxengine.so` blits foreground widgets onto `target = s_offscreen_bmp`, calls `GRM_fbrmUpdate` (committing `s_offscreen_bmp` to physical `GPE0`), and **immediately clears the next backbuffer via `GRM_gpermFillrect(0, 0, 1024, 540, 0xff000000)`**. Calling `flush_pixels_to_osd()` inside `GRM_gpermFillrect` or `GRM_fbrmGetOffscreen` overwrote physical `GPE0` (`0x41e001000`) with solid `0xff000000` right after every frame! Restricting `flush_pixels_to_osd()` strictly to `GRM_gpermDrawFlush` / `GRM_fbrmUpdate` / `GRM_fbrmFlip` preserves the true committed frame in `GPE0`.
2. **`GRM_GPERMFillrectParamRecord` (`x0` to `GRM_gpermFillrect`)**:
   - `+0x00` (`void *`): `dst_bmp` (`BMP_ImageBuffer*`, `NULL` -> `s_offscreen_bmp`)
   - `+0x08..0x0b` (`uint8_t[4]`): `R, G, B, A` (note: when `blend_mode == 2`, `+0x77f4` forces `fp[0x0b] = 0xff` and stores the true source alpha in `fp[0x18]`)
   - `+0x0c..0x12` (`uint16_t[4]`): `x, y, w, h`
   - `+0x14` (`uint32_t`): `blend_mode` (`1` = copy/overwrite, `2` = src-over alpha blend)
   - `+0x18` (`uint8_t`): `const_alpha`
3. **`GRM_GPERMRectblitParamRecord` (`x0` to `GRM_gpermRectblit`)**:
   - `+0x00` (`void *`): `src_bmp` (`BMP_ImageBuffer*`)
   - `+0x08..0x0e` (`uint16_t[4]`): `src_x, src_y, src_w, src_h`
   - `+0x10` (`void *`): `dst_bmp` (`BMP_ImageBuffer*`)
   - `+0x18..0x1e` (`uint16_t[4]`): `dst_x, dst_y, dst_w, dst_h`
   - `+0x20..0x26` (`uint16_t[4]`): `clip_x, clip_y, clip_w, clip_h`
   - `+0x28` (`uint32_t`): `blend_mode` (`1` = copy, `2` = src-over, `3` = modulated alpha)
   - `+0x2c` (`uint8_t`): `const_alpha`
   - `+0x3c..0x3f` (`uint8_t[4]`): `tint_r, tint_g, tint_b, tint_a` when `+0x50 == 0x0e` (`GRMImage::getPixelFormat() == 8` / `BMP_PixelFormat == 4`, `1 Bpp` `A8` FreeType glyph bitmaps rendered by `libfont.so`).
