# FX6 `UXEngine` & `GraphicsEngine` Native UI Thread Initialization Assist Report

## 1. Breakthrough Summary (Candidate `199` .. `209`)

In Candidate `199` (`cp-bind-31312fbb`, `guest-hybrid-fx6kernel-capid-grmreal199-sem.cpio`), fixing the `-16` byte stack-frame imbalance in `ux::core::GraphicsSystem::getFramebufferWidth()` (`libux_core.so + 0x30e40`), prepending `/usr/lib/libgrm-fbinit9.so` to Line 3 of `init`, and stubbing the `libosal_uipc.so` semaphore APIs allowed `grm::FrameBuffer::FrameBuffer()` (`libgrm.so + 0x23298`) and `ux::gfxeng::GraphicsEngine::GraphicsEngine()` (`libuxengine.so + 0x8350c`) to complete and return cleanly for the first time:

```text
FX6_GRM_FB_MINIMAL before manager=0x171fe10 fb=(nil) ctor=0x7f9396f298
FX6_GRM_FB_MINIMAL after manager=0x171fe10 fb=0x7f939fa280 vptr=0x7f93999e90
appfw-launch: GraphicsEngine ctor returned
appfw-launch: gfxeng=0x7f938b2e24 createScreen3D=0x7f938c1290 drawFramebuffer=0x7f938c19c8 ge=0x17207e0
```

Subsequent runs (`199` .. `209`) exposed three remaining architectural blockers:
1. **Thread 117 (`appFw.so`'s native UI thread) aborting with `FX6_ABORT_BT n=2 f0=... f1=libux_core.so + 0x2e3c0`**.
2. **`createScreen3D` in `202..207` aborting with `FX6_ABORT_BT n=2 f0=... f1=libuxengine.so + 0x832d0`**.
3. **`drawFramebuffer` in `199` faulting at `libgrm.so + 0x252c4` (`addr=0x8`, `X0=0`) and in `208` returning as a no-op without swapping frames**.

All three blockers have now been traced to their exact C++ root causes.

---

## 2. Exact C++ Root Causes

### Root Cause A: Why Thread 117 (`appFw.so`'s Real Native UI Thread) Aborted at `libux_core.so + 0x2e3c0`

- During `Application_System_Init()`, `appFw.so` spawns **Thread 117** (visible in serial logs as `I/stella(   117): Created HeapAllocator`).
- Thread 117 **already calls `uxengine_init2` (`libux_core.so + 0x2b964`) -> `UXEngine::initialize("UXEngine", 1024, 540, ...)` (`libuxengine.so + 0x74d70`) automatically**!
  - That is why the reference counter `w7` at `[libuxengine.so + 0xc4bad]` (`0x74d74`) was already `1` by the time `Application_System_Init()` returned to `appfw-launch`.
- Inside `UXEngine::initialize` (`libuxengine.so + 0x74d70`), Thread 117 executes:
  1. `0x74dc0`: `ux::core::Kernel::sys_initialize` -> `GraphicsSystem::sys_initialize` (`libux_core.so + 0x30cb8`) -> `initialize_porting_layer()` (`0x283e4`), which creates the real `ux::core::GraphicsSystemCore` singleton and stores it into **`[libux_core.so + 0x48800]`**.
  2. `0x74dc8`: `ux::resmgr::ResourceManager::sys_initialize` (`libuxengine.so + 0x750f4`) -> calls `ux::core::TextRMTextHandler::initialize()` (`libux_core.so + 0x2e340..0x2e410`).
  3. At `libux_core.so + 0x2e3a0`, `TextRMTextHandler::initialize()` calls `TextRM_initialize()` (`usr/lib/libtextrm.so + 0x066d4`), which calls `loadFontListFile()` (`libtextrm.so + 0x08a8c`).
  4. `loadFontListFile()` queries `Backup_get_datasize(0x00810000)`. Because key `0x00810000` returns `0`, it falls back to `fopen("TEXTRM_FONT_LIST", "r")` (`libtextrm.so + 0x08ae4`) in the current working directory (`/`).
  5. Because `/TEXTRM_FONT_LIST` does not exist in `/` (the actual file in the initramfs is `/usr/share/app/fontlist.dat`, and all `.ltt`/`.ttf` font files referenced by `fontlist.dat` are already present in `/usr/share/app/`), `fopen("TEXTRM_FONT_LIST", "r")` returns `NULL`.
  6. `loadFontListFile()` returns `-10000`, `TextRM_initialize()` returns `-1`, and `TextRMTextHandler::initialize()` at `libux_core.so + 0x2e3bc` (`LR = 0x2e3c0`) calls `ux::core::sys_panic()` -> `abort()`, which `libgrm-fbinit9.so` catches (`FX6_ABORT_BT n=2 f0=... f1=libux_core.so + 0x2e3c0`) and puts Thread 117 to sleep **right before Step 3 (`0x74ddc`: `GraphicsEngine::sys_initialize`), Step 4 (`0x74df8`: `AnimationEngine::sys_initialize`), and Step 5 (`0x74e00`: `WidgetSystem::sys_initialize`)**!

### Root Cause B: Why `UXEngine::initialize` Automatically Creates `GraphicsEngine`, `GraphicsContextGRM`, and Screens Once Thread 117 Passes `0x74dc8` (and Why `appfw-launch`'s `0x48800` Patch Broke `drawFramebuffer`)

- Immediately after `0x74dc8` (`ResourceManager::sys_initialize`) succeeds, `UXEngine::initialize` calls **`ux::gfxeng::GraphicsEngine::sys_initialize("UXEngine", 1024, 540, 2)` (`libuxengine.so + 0x838e4`)**:
  1. `0x838f4`: `GraphicsEngine::sys_createApplication("UXEngine", 1024, 540)` (`0x82854`) calls `ux::core::GraphicsSystem::createFramebuffer("UXEngine", 1024, 540)` (`libux_core.so + 0x30d70`).
  2. `GraphicsSystem::createFramebuffer` loads `[libux_core.so + 0x48800]` (`ux::core::GraphicsSystemCore*`) and calls its virtual slot 0: **`ux::core::GraphicsSystemCore::Initialize("UXEngine", 1024, 540, allocator)` (`libux_core.so + 0x27ef0`)**.
  3. `GraphicsSystemCore::Initialize` calls **`gemini::GraphicsContextGRM::createGraphicsContext(allocator, 1024, 540)` (`libgemini-grm.so + 0x08ea0`)**, which constructs the real `gemini::GraphicsContextGRM`, calls `GRM_fbrmInitialize(1024, 540, 1)` (triggering `libgrm-fbinit9.so`), initializes `GraphicsDrawState` and `BindImageManager`, and stores the returned `gemini::GraphicsContextGRM*` into **`[libux_core.so + 0x487f8]`** (`GraphicsSystem::getGraphicsContext()`).
  4. `0x838f8`: `GraphicsEngine::sys_createAfterTask()` (`libuxengine.so + 0x83810`) allocates and constructs the real `GraphicsEngine` (`0x83834`), stores it into **`[libuxengine.so + 0xc1f78]`** (`UXEngine::gfxeng()`), and calls **`GraphicsEngine::createScreen(ux::core::ID const&)` (`0x83870` and `0x83880`)** with the real valid screen IDs!
- **Why `appfw-launch` broke `drawFramebuffer` in `199..209`**:
  - At `0x0898c` and `0x089c8`, `appfw-launch` **overwrote `[libux_core.so + 0x48800]` (`GraphicsSystemCore*`) and `[libux_core.so + 0x48810]` with a fake zero-stub table (`0x103c258`)**!
  - Because `[libux_core.so + 0x48800]` was overwritten with `0x103c258`, `GraphicsSystem::createFramebuffer` never called `GraphicsSystemCore::Initialize`, `[libux_core.so + 0x487f8]` (`getGraphicsContext()`) remained `NULL`, and every `GraphicsSystem` method used by `drawFramebuffer()` (`isFramebufferDirty`, `prepareRendering`, `prepareSwap`, `swapFramebuffer`) jumped to `ret_zero` (`0x103c258`) instead of `GraphicsSystemCore` and `GraphicsContextGRM::swap()`!
  - Furthermore, in `202..207`, `GraphicsEngine::createScreen3D(ux::core::ID const&)` (`libuxengine.so + 0x83290`) takes a reference `ux::core::ID const*` in `x1` and checks `id != INVALID_ID` at `0x832b0` (`0x832b8: b.ne 0x832d0`); when `id == INVALID_ID`, it calls `ux::core::sys_panic()` at `0x832cc` (`LR = 0x832d0`, `f1=...832d0`) before ever reaching `Screen3D::Screen3D` (`0x83310`).

### Root Cause C: Why `199` Faulted at `libgrm.so + 0x252c4` (`addr=0x8`, `X0=0`)

- Because `libgrm-fbinit9.so` hooks `grm::FBResourceManager::initialize()` as a no-op, the member pointers `[FBResourceManager + 0x10]` (`grm::Semaphore*`), `[FBResourceManager + 0x20]` (`grm::ExternalOSDIF*`), `[FBResourceManager + 0x24]` (`grm::ResultWorker*`), and `[FBResourceManager + 0x48]` (`grm::Semaphore*`) are `NULL` (`0`).
- When `FBResourceManager::lockFrameBuffer()` (`libgrm.so + 0x22b2c`) calls `grm::Semaphore::lock()` (`0x252b8`) with `x0 = [FBResourceManager + 0x10] = NULL`, `0x252c4: ldr w0, [x0, #8]` faults with `addr=0x8`.
- Similarly, `FBResourceManager::updateRequest()` (`0x22d98`) calls `grm::FrameBuffer::swap()` (`0x22e00`, hooked by `libgrm-fbinit9.so` to copy frames to `0x41e000000`) and then calls `grm::ExternalOSDIF` and `grm::Semaphore` methods on those `NULL` member pointers.

---

## 3. Exact Patch Specification for Candidate `210` (Base: `guest-hybrid-fx6kernel-capid-grmreal199-sem.cpio`)

Start from **`guest-hybrid-fx6kernel-capid-grmreal199-sem.cpio`** (which has the clean `libuxengine.so` and `appfw-launch` calling `drawFramebuffer`) and apply the following exact modifications:

### 1. `init` (Line 3)
Prepend `ln -sf /usr/share/app/fontlist.dat /TEXTRM_FONT_LIST; ` right before `LD_PRELOAD=/usr/lib/libgrm-fbinit9.so:... /usr/bin/appfw-launch` on Line 3 of `init` so `loadFontListFile()` opens `/TEXTRM_FONT_LIST` (`-> /usr/share/app/fontlist.dat`).

### 2. `usr/lib/libux_core.so`
| Offset | Original Bytes | Replacement Bytes | Purpose |
|---|---|---|---|
| `0x2e3a8` | `a0 01 00 34` | `0d 00 00 14` | `b 0x2e3dc` in `TextRMTextHandler::initialize()` — never call `sys_panic()` (`f1=...2e3c0`) |
| `0x282bc` | `fd 7b be a9` | `c0 03 5f d6` | `ret` at `GraphicsSystemCore::AddGpeAsyncWaitCount()` |
| `0x2838c` | `fd 7b bf a9` | `c0 03 5f d6` | `ret` at `GraphicsSystemCore::WaitGpeFinish()` |
| `0x30e40` | *(already patched in 199)* | `00 80 80 52 c0 03 5f d6` | `mov w0, #1024; ret` at `getFramebufferWidth()` |
| `0x30e68` | *(already patched in 199)* | `80 43 80 52 c0 03 5f d6` | `mov w0, #540; ret` at `getFramebufferHeight()` |

### 3. `usr/lib/libgemini-grm.so`
| Offset | Original Bytes | Replacement Bytes | Purpose |
|---|---|---|---|
| `0x08e54` | `df f9 ff 97` | `1f 20 03 d5` | `nop` pre-lock of `stella::Mutex` in `GraphicsContextGRM::createSyncObject()` so `BindImageManager::checkSync` never blocks |

### 4. `usr/lib/libgrm.so`
| Offset | Replacement Bytes | Symbol / Purpose |
|---|---|---|
| `0x2526c` | `00 00 80 52 c0 03 5f d6` | `grm::Semaphore::isLocked()` -> `mov w0, #0; ret` (safe when `this == NULL`) |
| `0x252b8` | `00 00 80 52 c0 03 5f d6` | `grm::Semaphore::lock()` -> `mov w0, #0; ret` (fixes `pc=0x7f939712c4` `addr=0x8` crash) |
| `0x252f8` | `00 00 80 52 c0 03 5f d6` | `grm::Semaphore::unlock()` -> `mov w0, #0; ret` (safe when `this == NULL`) |
| `0x21e70` | `20 00 80 52 c0 03 5f d6` | `grm::ExternalOSDIF::suspend()` -> `mov w0, #1; ret` |
| `0x21ea0` | `20 00 80 52 c0 03 5f d6` | `grm::ExternalOSDIF::isUpdateFinished()` -> `mov w0, #1; ret` |
| `0x21ec0` | `20 00 80 52 c0 03 5f d6` | `grm::ExternalOSDIF::sendConfirm(bool)` -> `mov w0, #1; ret` |
| `0x21f1c` | `20 00 80 52 c0 03 5f d6` | `grm::ExternalOSDIF::lockOsdTransfer()` -> `mov w0, #1; ret` |
| `0x21f24` | `20 00 80 52 c0 03 5f d6` | `grm::ExternalOSDIF::cancelOsdTransfer()` -> `mov w0, #1; ret` |
| `0x21f60` | `20 00 80 52 c0 03 5f d6` | `grm::ExternalOSDIF::waitUpdateComplete()` -> `mov w0, #1; ret` |
| `0x2232c` | `20 00 80 52 c0 03 5f d6` | `grm::ExternalOSDIF::sendExec(...)` -> `mov w0, #1; ret` |
| `0x223cc` | `20 00 80 52 c0 03 5f d6` | `grm::ExternalOSDIF::sendUpdate(...)` -> `mov w0, #1; ret` |
| `0x22b40` | `20 00 80 52 c0 03 5f d6` | `grm::FBResourceManager::suspend()` -> `mov w0, #1; ret` |
| `0x22b84` | `20 00 80 52 c0 03 5f d6` | `grm::FBResourceManager::resume()` -> `mov w0, #1; ret` |

### 5. `usr/bin/appfw-launch` (from `199`)
| Offset | Original Bytes | Replacement Bytes | Purpose |
|---|---|---|---|
| `0x0898c` | `b4 02 00 f9` | `1f 20 03 d5` | `nop` — **do NOT overwrite `[libux_core.so + 0x48800]` (`GraphicsSystemCore*`) with `0x103c258`!** |
| `0x089c8` | `d4 0a 00 f9` | `1f 20 03 d5` | `nop` — **do NOT overwrite `[libux_core.so + 0x48810]` with `0x103c258`!** |
| `0x08d80` | `c8 02 00 b9` | `1f 20 03 d5` | `nop` — do NOT corrupt `libgemini-grm.so + 0x8cc0` (`setCheckRectCallback`) |
| `0x08df0` | `e0 02 3f d6` | `1f 20 03 d5` | `nop` — let `UXEngine::initialize` -> `GraphicsEngine::sys_initialize` -> `sys_createAfterTask` construct the real `GraphicsEngine` and Screen 0/1 |
| `0x08e18` | `f6 02 00 f9` | `1f 20 03 d5` | `nop` — do NOT overwrite `ge_instance` |
| `0x08e34` | `d7 02 00 f9` | `1f 20 03 d5` | `nop` — do NOT overwrite `[libuxengine.so + 0xc1f78]` (set by `GraphicsEngine::sys_createAfterTask`) |

---

## 4. Candidate `210` .. `213` Follow-Up (`cp-bind-bab23426`, `cp-bind-3a3628c8`, `cp-bind-abb66433`)

### 4.1 What Succeeded in `cp-bind-bab23426` (`211`)
In `cp-bind-bab23426`, with the `TextRMTextHandler::initialize()` fix applied, **Thread 117 (`appFw.so`'s real UI thread) completed `UXEngine::initialize()` for the first time**, creating the real `grm::FrameBuffer` (`0x7f96f7f280`), calling `setSize(1024, 540)`, creating **Screen 0 (`0x7f7c00d150`), Screen 1 (`0x7f7c00d2f0`), and Screen 2 (`0x7f7c010d60`)**, and entering **`app_adjchk_ui::main_loop()` (`usr/lib/AdjChkConfig.so + 0xe720`)**:
```text
FX6_GRM_FB_MINIMAL before manager=0x7f7c0081b0 fb=(nil) ctor=0x7f96ef4298
FX6_GRM_FB_MINIMAL after manager=0x7f7c0081b0 fb=0x7f96f7f280 vptr=0x7f96f1ee90
FX6_GRM_FB_SET_SIZE self=0x7f96f7f280 w=1024 h=540
FX6_GRM_FB_UPDATE_SKIP self=0x7f96f7f280 result=0
FX6_UX_SCREEN_AREA_1024 self=0x7f7c00d150 x=0 y=0 w=1024 h=540
FX6_UX_SCREEN_AREA_1024 self=0x7f7c00d2f0 x=0 y=0 w=1024 h=540
FX6_UX_SCREEN_AREA_1024 self=0x7f7c010d60 x=0 y=0 w=1024 h=540
appfw-launch: main/app_adjchk_ui.cpp:92: void app_adjchk_ui::sircs_event_start(): Assertion `0' failed.
```

### 4.2 Why `cp-bind-bab23426` Aborted at `app_adjchk_ui.cpp:92` (Right Before `presenter_jiritsu` & `drawFramebuffer`)
Disassembly of `app_adjchk_ui::main_loop()` (`usr/lib/AdjChkConfig.so + 0xe720..0xeb8c`) shows:
1. `0xe750`: `bl app_adjchk_ui::view_initialize()` (`0xc164`) — calls `WidgetSystem::createLayer()`, `TextLayout::registerFontFaceFile()`, and `ResourceManager::createFont()`, succeeding completely.
2. `0xe7bc`: `bl app_adjchk_ui::pin_manager::init()` — succeeds.
3. `0xe7fc..0xe864`: inlined `app_adjchk_ui::sircs_event_start()` calls `osal_valloc_msg_wait(0x807d0035, &msg, 12, 1)` at `0xe810` and `osal_snd_msg(0x807d0035, msg)` at `0xe850`. Because `osal_valloc_msg_wait` returns non-zero in QEMU, `0xe814: cbz w0, 0xe838` falls through to `0xe834: bl __assert_fail("0", "main/app_adjchk_ui.cpp", 92, "void app_adjchk_ui::sircs_event_start()")`, terminating the process **one instruction before `0xe868: new app_adjchk_ui::presenter_jiritsu()` and the native 60Hz `drawFramebuffer()` loop (`0xe8a8..0xea50`)**!
4. Inside the `0xe8a8..0xea50` native UI render loop:
   - `0xe8cc`: calls `osal_rcv_msg_tmo(0x80290119, &msg, 0)`. If `w0 == -0x3fe` (`-1022`, timeout), `0xe8d4: b.eq 0xeb54` sleeps `1000 us` and jumps to `0xe9c0`. If `w0 != 0 && w0 != -0x3fe`, it asserts at line 120 (`0xe8e8`); if `w0 == 0` with `msg == NULL`, it dereferences `NULL` at `0xe908`.
   - `0xe9dc`: calls `osal_snd_sync_direct(0x00910042, &buf)` to read a microsecond timestamp at `[x29, #0x88]`, divides by `16666`, and skips rendering if `x25 == x27` (`0xe9f0: b.eq 0xea4c`). When `osal_snd_sync_direct` leaves `[x29, #0x88] == 0`, `x27` stays `0 == x25`, skipping `0xe9f4..0xea48` (`presenter_jiritsu` tick, `WidgetSystem::processEvent()`, `ResourceManager::processCommands()`, `WidgetSystem::updateFrame()`, `WidgetSystem::notifyDraw()`, and `GraphicsEngine::drawFramebuffer()`).

### 4.3 Exact Binary Patches in `usr/lib/AdjChkConfig.so` to Unblock `presenter_jiritsu` and the Native `drawFramebuffer()` Loop
| Offset in `usr/lib/AdjChkConfig.so` | Original Bytes | Replacement Bytes | Instruction / Effect |
|---|---|---|---|
| `0xe7fc` | `a0 06 80 52` | `1b 00 00 14` | `b 0xe868` — skip `sircs_event_start()` IPC send and jump directly to `new app_adjchk_ui::presenter_jiritsu()` |
| `0xe8cc` | `d1 e7 ff 97` | `a2 00 00 14` | `b 0xeb54` — take the normal `usleep(1000)` timeout branch instead of blocking/asserting on `osal_rcv_msg_tmo` |
| `0xe9f0` | `e0 02 00 54` | `1f 20 03 d5` | `nop` — always execute the frame tick (`presenter_jiritsu`, `WidgetSystem::updateFrame`, `WidgetSystem::notifyDraw`, `GraphicsEngine::drawFramebuffer`) on every 1ms tick |

### 4.4 Why `cp-bind-3a3628c8` (`212`) Did Not Print `FX6_GRM_FB_MINIMAL` & Why `cp-bind-abb66433` (`213`) Failed to Load `libgrm-fbinit9.so`
1. **Race in `cp-bind-3a3628c8` (`212`)**:
   - `appfw-launch` still had the `patched 0x48800 ... -> 0x103c258` store enabled! In `212`, Thread 117 (`I/stella( 117): Created HeapAllocator`) ran `initialize_porting_layer()` **before** `appfw-launch` executed `patched 0x48800 -> 0x103c258`, so `appfw-launch` clobbered Thread 117's real `GraphicsSystemCore*` pointer with `0x103c258` right before Thread 117 called `GraphicsEngine::sys_initialize()`!
   - **Fix**: Ensure `appfw-launch` does **not** write `0x103c258` to `0x48800`/`0x48810` (NOP `0x0898c` and `0x089c8` in `usr/bin/appfw-launch`), and does **not** call `uxengine_init2` / `GraphicsEngine` ctor on the main thread — after `Application_System_Init()` returns, `appfw-launch` should simply sleep while Thread 117 runs `UXEngine::initialize()` and `app_adjchk_ui::main_loop()`.
2. **Symbol Lookup Error in `cp-bind-abb66433` (`213`)**:
   - `/usr/bin/appfw-launch: symbol lookup error: /usr/lib/libgrm-fbinit9.so: undefined symbol: __ubsan_handle_pointer_overflow` (and `__ubsan_handle_type_mismatch_v1`).
   - **Fix**: Compile `libgrm-fbinit9.so` with **`-fno-sanitize=all`** (or provide empty stub functions `void __ubsan_handle_pointer_overflow(void) {}` and `void __ubsan_handle_type_mismatch_v1(void) {}` inside `libgrm-fbinit9.c`).

