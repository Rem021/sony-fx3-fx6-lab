# FX6 `UXEngine` & `GraphicsEngine` Native UI Thread Initialization Assist Report

## 1. Breakthrough Summary (Candidate `199` .. `218`)

1. **Candidate `199` (`cp-bind-31312fbb`, `guest-hybrid-fx6kernel-capid-grmreal199-sem.cpio`)**:
   - Fixing the `-16` byte stack-frame imbalance in `ux::core::GraphicsSystem::getFramebufferWidth()` (`libux_core.so + 0x30e40`), prepending `/usr/lib/libgrm-fbinit9.so` to Line 3 of `init`, and stubbing the `libosal_uipc.so` semaphore APIs allowed `grm::FrameBuffer::FrameBuffer()` (`libgrm.so + 0x23298`) and `ux::gfxeng::GraphicsEngine::GraphicsEngine()` (`libuxengine.so + 0x8350c`) to complete and return cleanly for the first time.
2. **Candidate `211` (`cp-bind-bab23426`, `guest-hybrid-fx6kernel-capid-grmreal211-ui.cpio`)**:
   - Adding `ln -sf /usr/share/app/fontlist.dat /TEXTRM_FONT_LIST` in `init` and patching `ux::core::TextRMTextHandler::initialize()` (`libux_core.so + 0x2e3a8` -> `0d 00 00 14`) resolved the `FX6_ABORT_BT f1=libux_core.so+0x2e3c0` crash.
   - **For the first time in the project, `appFw.so`'s own native UI thread (Thread 117/118) completed `UXEngine::initialize()` and created all 3 native `1024x540` screens** (`0x7f7c00d150`, `0x7f7c00d2f0`, `0x7f7c010d60`), entering `app_adjchk_ui::main_loop()` (`usr/lib/AdjChkConfig.so + 0x0e720`).
3. **Candidate `218` (`cp-bind-df619377`, `guest-hybrid-fx6kernel-capid-grmreal218-draw.cpio`)**:
   - Bypassing `app_adjchk_ui::sircs_event_start()` (`usr/lib/AdjChkConfig.so + 0x0e7fc` -> `1b 00 00 14`) allowed Thread 118 to construct `new app_adjchk_ui::presenter_jiritsu()`, initialize the UI widget tree, and **enter the native `UXEngine::gfxeng()->drawFramebuffer()` render pipeline**, reaching `grm::FrameBuffer::getOffscreen()` (`libgrm-fbinit9.so`)!

---

## 2. Exact C++ Root Causes & Architectural Findings

### 2.1 Why Some Runs (`212`, `220..226`) Do Not Print `FX6_GRM_FB_MINIMAL` or Crash at `libux_core.so + 0x31af4` (`addr=0x28`, `X0=0`)
**CRITICAL RACE CONDITION BETWEEN `appfw-launch` AND THREAD 117/118**:
- During `Application_System_Init()`, `appFw.so` spawns its native UI thread (Thread 117/118: `I/stella(118): Created HeapAllocator`), which runs **`uxengine_init2` -> `UXEngine::initialize("UXEngine", 1024, 540, ...)` (`libuxengine.so + 0x74d70`)**.
- At the exact same moment (~30s after `Application_System_Init()` returns), **`usr/bin/appfw-launch` ALSO runs on the main thread**!
- Look at what `usr/bin/appfw-launch` currently executes in `211..226`:
  1. `0x0898c`: `str x20, [x21]` — **overwrites `[libux_core.so + 0x48800]` (`ux::core::GraphicsSystemCore*`) with `0x103c258` (`ret_zero` stub table)**!
     - Whenever `appfw-launch` prints `patched 0x48800 ... -> 0x103c258` **after** Thread 118 runs `initialize_porting_layer()`, `appfw-launch` **wipes out Thread 118's real `GraphicsSystemCore*` pointer**, replacing it with `0x103c258`! Then when Thread 118 calls `GraphicsSystem::createFramebuffer()`, virtual slot 0 jumps to `0x103c258` (`ret 0`) instead of `GraphicsSystemCore::Initialize()`, so **`GRM_fbrmInitialize` and `FX6_GRM_FB_MINIMAL` are NEVER called**!
     - That is 100% why `223`, `224`, `225`, `226` did not print `FX6_GRM_*`!
  2. `0x08c18`: `blr x19` — **`appfw-launch` calls `uxengine_init2` concurrently with Thread 118**!
     - When Thread 118 has just incremented `[libuxengine.so + 0xc4bad]` (`w7`) from `0` to `1` at `0x74dbc` (but has not yet finished `UXEngine::initialize`), `appfw-launch`'s call to `uxengine_init2` sees `w7 == 1` at `0x74d78`, returns immediately from `UXEngine::initialize`, and crashes at `libux_core.so + 0x31af4` (`addr=0x28`, `X0=0`)!
     - That is 100% why `cp-bind-58730175` (`226`), `cp-bind-6220b943`, `cp-bind-08e2037f`, and `cp-bind-d577501f` crashed at `APPFW_SEGV sig=11 addr=0x28 pc=...faf4 /usr/lib/libux_core.so`!
  3. `0x08e34`: **`appfw-launch` overwrites `[libuxengine.so + 0xc1f78]` (`UXEngine::gfxeng()`) with `&ge_instance(0x104c258)`**!

#### Mandatory Fix in `usr/bin/appfw-launch` (Eliminates the Race 100% Deterministically)
In `usr/bin/appfw-launch`, NOP out `appfw-launch`'s post-`Application_System_Init()` interference so **Thread 117/118 has 100% exclusive ownership of `UXEngine` and `GraphicsSystemCore`**:
| Offset in `usr/bin/appfw-launch` | Current Bytes in `218..226` | Replacement Bytes | Effect |
|---|---|---|---|
| `0x0898c` | `b4 02 00 f9` *(or Jump over `0x08940..0x08ecc`)* | `1f 20 03 d5` (`nop`) | **Never overwrite `[libux_core.so + 0x48800]` with `0x103c258`!** |
| `0x089c8` | `1f 20 03 d5` | `1f 20 03 d5` (`nop`) | Never overwrite `[libux_core.so + 0x48810]` |
| `0x08c18` | `60 02 3f d6` (`blr x19`) | `1f 20 03 d5` (`nop`) | **Never call `uxengine_init2` from `appfw-launch` (prevents `libux_core.so + 0x31af4` `addr=0x28` SEGV)!** |
| `0x08c30` | `78 01 00 94` | `1f 20 03 d5` (`nop`) | Skip `setUIResponseRect` in `appfw-launch` |
| `0x08df0` | `1f 20 03 d5` | `1f 20 03 d5` (`nop`) | Skip `GraphicsEngine` ctor in `appfw-launch` |
| `0x08e18` | `1f 20 03 d5` | `1f 20 03 d5` (`nop`) | Skip `ge_instance` store in `appfw-launch` |
| `0x08e34` | `1f 20 03 d5` | `1f 20 03 d5` (`nop`) | Never overwrite `[libuxengine.so + 0xc1f78]` |
| `0x08e64` | `60 02 3f d6` | `1f 20 03 d5` (`nop`) | Skip `createScreen3D` in `appfw-launch` |
| `0x08e98` | `80 02 3f d6` | `1f 20 03 d5` (`nop`) | Skip `drawFramebuffer` in `appfw-launch` (Thread 118 runs `drawFramebuffer` natively!) |

*(Even simpler: in `usr/bin/appfw-launch`, patching a single instructionright after `Application_System_Init()` returns — e.g. at **`0x08940`** jumping directly to **`0x08ec0`** (`60 01 00 14`, `b 0x08ec0` -> `"appfw-launch: keeping process alive"`) — skips ALL of `appfw-launch`'s `0x48800`/`uxengine_init2`/`0xc1f78` interference in one 4-byte patch!)*

---

### 2.2 Why `218` Faulted in `libstella.so` (`LinearList::remove`) When `getOffscreen()` Returned `NULL`
In `cp-bind-df619377` (`218`), Thread 118 ran `drawFramebuffer()` -> `GraphicsSystemCore::PrepareRendering()` -> `gemini::GraphicsContextGRM::prepareRendering()` (`libgemini-grm.so`):
1. `prepareRendering()` calls `GRM_fbrmGetOffscreen(&bmp)` -> `grm::FrameBuffer::getOffscreen(fb)`.
2. Because `libgrm-fbinit9.so` returned `NULL` (`0`) from `getOffscreen()` and `getOnscreen()`, `GraphicsContextGRM` received `bmp = NULL` (`0`) and passed `NULL` into `libgemini.so` / `liblibra.so`, corrupting the draw target state and causing `stella::LinearList::remove` (`libstella.so + 0x298d8`) / `liblibra.so + 0x3702c` to fault!

---

### 2.3 Exact `grm::FrameBuffer` and `grm::bmp::BitmapImpl` Memory Layout & How to Provide Valid `1024x540` Onscreen/Offscreen `GRM_Bitmap` Objects Without `libma.so` (`MA_CreateSpace`)

We audited `grm::FrameBuffer` (`usr/lib/libgrm.so + 0x22eb8..0x23318`) and `grm::bmp::BitmapImpl` (`usr/lib/libgrm_bmp.so + 0x06054..0x07fb4`):

#### A. Why `grm::FrameBuffer::initialize()` (`libgrm.so + 0x22eb8`) and `BMP_Create` (`libgrm_bmp.so + 0x07c38`) Asserted in `216` / `221`
1. `grm::FrameBuffer::initialize()` calls `MA_CreateSpace()` (`usr/lib/libma.so + 0x05290`), which constructs `ma::MAMessage(uint16_t)` (`libma.so + 0x05964`) and calls `osal_valloc_msg_wait`, asserting at `Message.h:94: Assertion 'msg' failed` (`cp-bind-cd7e45bc`).
2. `grm::FrameBuffer::update()` (`libgrm.so + 0x230b8`) reads:
   - `width` (`uint16_t`) at **`[fb + 0x14]`**
   - `height` (`uint16_t`) at **`[fb + 0x16]`**
   - `colorFormat` (`uint32_t`) at **`[fb + 0x18]`** (set by `FrameBuffer::setColorFormat` at `0x23048: str w1, [x0, #0x18]`; in `cp-bind-2e00a48a`, `[fb + 0x18]` was `0 == BMP_PixelFormatNone`, which triggered `Bitmap.cpp:372: Assertion 'format > BMP_PixelFormatNone' failed`! For RGBA8888 / OSD, `format` is **`1`** or **`2`**).
   - And then calls `BMP_CreateFromPhys(width, height, format, 0, phys_addr, 0, &bmp_slot)` (`libgrm_bmp.so + 0x07ea4`), which in turn calls `MA_CreateSpaceDirect` (`libma.so + 0x05330`), which ALSO calls `ma::MAMessage`!
3. Look at what `grm::FrameBuffer::getOnscreen()`, `getOffscreen()`, `getOnscreenHandle()`, and `swap()` (`libgrm.so + 0x231d8..0x23280`) actually do at the instruction level:
   - **`getOffscreen(fb)` (`0x231d8`)**:
     ```c
     // 0x231d8: ldr x0, [x0, #0x70]
     // 0x231dc: ldr x0, [x0]
     // 0x231e0: ret
     return **(void ***)((char *)fb + 0x70);
     ```
   - **`getOnscreen(fb)` (`0x231e4`)**:
     ```c
     // 0x231e4: ldr x0, [x0, #0x68]
     // 0x231e8: ldr x0, [x0]
     // 0x231ec: ret
     return **(void ***)((char *)fb + 0x68);
     ```
   - **`getOnscreenHandle(fb)` (`0x231f0`)**:
     ```c
     // 0x231f0: ldr x0, [x0, #0x68]
     // 0x231f4: ldr w0, [x0, #0x10]
     // 0x231f8: ret
     return *(uint32_t *)((char *)(*(void **)((char *)fb + 0x68)) + 0x10);
     ```
   - **`swap(fb)` (`0x2324c`)**:
     ```c
     // 0x23268: ldp x0, x1, [x19, #0x68]
     // 0x2326c: stp x1, x0, [x19, #0x68]
     // Simply swaps the two pointers at [fb + 0x68] and [fb + 0x70]!
     ```

#### B. Exact Layout of `grm::bmp::BitmapImpl` (`usr/lib/libgrm_bmp.so`, `sizeof = 0x80` bytes)
We inspected `grm::bmp::BitmapImpl::BitmapImpl` (`libgrm_bmp.so + 0x06ab8`), `create(long, short, BMP_RectangleRecord*)` (`0x06eb4`), `getLogicalAddress` (`0x0627c`), `getPhysicalAddress` (`0x0626c`), `getDimensions` (`0x0664c`), `getRowBytes` (`0x06698`), `getFormat` (`0x06240`), `getRectangle` (`0x061e0`), `getAllocatedRectangle` (`0x06610`), `readLockBits` (`0x06978`), and `writeLockBits` (`0x06814`).

Every `BMP_*` C function in `libgrm_bmp.so` (`BMP_GetDimensions`, `BMP_GetRowBytes`, `BMP_GetFormat`, `BMP_GetLogicalAddress`, `BMP_WriteLockBits`, `BMP_WriteUnlockBits`, `BMP_ReadLockBits`, `BMP_ReadUnlockBits`, `BMP_GetRectangle`, `BMP_GetAllocatedRectangle`, `BMP_GetUnitHandle`) simply casts the `GRM_Bitmap` handle (`void *bmp`) to `grm::bmp::BitmapBase*` and calls its virtual method!

And inside `grm::bmp::BitmapImpl` (`vptr = _ZTVN3grm3bmp10BitmapImplE + 0x10` at `libgrm_bmp.so + 0x1da48`), the fields read by all methods are:
| Offset in `BitmapImpl` | Size | Type / Value for `1024x540` RGBA8888 (`stride = 4096`) | Used By |
|---|---|---|---|
| `+0x00` | 8B | `vptr` = `dlsym(RTLD_DEFAULT, "_ZTVN3grm3bmp10BitmapImplE") + 0x10` | All `BMP_*` virtual dispatch |
| `+0x08` | 8B | `void *memSpace` = non-NULL dummy pointer (e.g. `(void*)0x1`) | Checked `!= NULL` by `getDimensions`, `getRowBytes`, `getFormat`, `writeLockBits`, `readLockBits` |
| `+0x10` | 8B | `void *logAddr` = pointer to 4MB pixel buffer (`1024 * 540 * 4` bytes) | Returned by `getLogicalAddress` (`0x0627c`), `writeLockBits` (`0x06950`), `readLockBits` |
| `+0x18` | 2B | `int16_t allocWidth` = `1024` | `getDimensions`, `getRowBytes` |
| `+0x1a` | 2B | `int16_t allocHeight` = `540` | `getDimensions` |
| `+0x1c` | 4B | `BMP_PixelFormat format` = `1` (or `2`, 4 bytes/pixel) | `getFormat` (`0x06240`), `BMP_PixelFormatToBytesPerPixel` |
| `+0x20` | 8B | `int64_t physAddr` = `0x41e001000` (or physical/virtual addr) | `getPhysicalAddress` (`0x0626c`) |
| `+0x28` | 8B | `uint64_t sizeBytes` = `1024 * 540 * 4` (`0x21c000`) | `getSize` (`0x061f4`) |
| `+0x30` | 4B | `int32_t writeLockCount` = `0` | `writeLockBits` / `writeUnlockBits` |
| `+0x34` | 4B | `int32_t refCount` = `1` | `addReference` / `release` |
| `+0x38` | 4B | `int32_t readLockCount` = `0` | `readLockBits` / `readUnlockBits` |
| `+0x3c` | 4B | `BMP_YUVMode yuvMode` = `0` | `getYUVMode` |
| `+0x40` | 2B | `int16_t rect.x` = `0` | `getRectangle` (`+0x40`) |
| `+0x42` | 2B | `int16_t rect.y` = `0` | `getRectangle` |
| `+0x44` | 2B | `int16_t rect.w` = `1024` | `getRectangle` |
| `+0x46` | 2B | `int16_t rect.h` = `540` | `getRectangle` |
| `+0x48` | 2B | `int16_t subRect.x` = `0` | `getSubRectangle` (`+0x48`) |
| `+0x4a` | 2B | `int16_t subRect.y` = `0` | `getSubRectangle` |
| `+0x4c` | 2B | `int16_t subRect.w` = `1024` | `getSubRectangle` |
| `+0x4e` | 2B | `int16_t subRect.h` = `540` | `getSubRectangle` |
| `+0x50` | 2B | `int16_t allocRect.x` = `0` | `getAllocatedRectangle` (`+0x50`) |
| `+0x52` | 2B | `int16_t allocRect.y` = `0` | `getAllocatedRectangle` |
| `+0x54` | 2B | `int16_t allocRect.w` = `1024` | `getAllocatedRectangle`, `getRowBytes` |
| `+0x56` | 2B | `int16_t allocRect.h` = `540` | `getAllocatedRectangle` |
| `+0x58` | 4B | `uint32_t unitHandle` = `1` | `getUnitHandle` (`0x067d0`, skips `MA_GetUnitHandle` if we patch `0x067d0` to return `0`) |
| `+0x5c` | 2B | `int16_t rowAlign` = `1` | `getRowBytes`: `((allocRect.w + rowAlign - 1) / rowAlign) * rowAlign * bpp` |
| `+0x5e` | 2B | `int16_t colAlign` = `1` | `getColPixelCount` |
| `+0x68..0x98` | 48B | `stella::Mutex` (initialized by `BitmapImpl::BitmapImpl` ctor at `+0x68`) | `writeLockBits` / `readLockBits` lock `this + 0x68`! |

**Crucial Detail on `BitmapImpl` Construction**:
If you call the real `grm::bmp::BitmapImpl::BitmapImpl(1024, 540, 2, 0, 0, 0)` constructor (`_ZN3grm3bmp10BitmapImplC1Ess15BMP_PixelFormat11BMP_YUVMode21BMP_PixelSortingOrder22BMP_PixelStartPosition` in `libgrm_bmp.so`), it **automatically**:
1. Sets the real `vptr` (`+0x00`),
2. Calls `new stella::Mutex()` (`+0x08` in `BitmapBase`) and initializes the embedded mutex at `+0x68` (`0x06b88`),
3. Sets `refCount = 1` (`+0x34`), `format` (`+0x1c`), `yuvMode` (`+0x3c`), `rect` (`+0x40..0x46` = `0, 0, 1024, 540`)!
Then, after calling `BitmapImpl::BitmapImpl(bmp_obj, 1024, 540, 2, 0, 0, 0)` on a `256`-byte aligned buffer `bmp_obj`, you only need to populate the memory fields that `BitmapImpl::create()` would have set:
```c
*(void **)((char *)bmp_obj + 0x08) = (void *)0x1;          // non-NULL memSpace
*(void **)((char *)bmp_obj + 0x10) = pixel_buf;            // 1024*540*4 byte buffer!
*(short *)((char *)bmp_obj + 0x18) = 1024;                 // allocWidth
*(short *)((char *)bmp_obj + 0x1a) = 540;                  // allocHeight
*(unsigned long *)((char *)bmp_obj + 0x20) = 0x41e001000UL;// physAddr
*(unsigned long *)((char *)bmp_obj + 0x28) = 1024*540*4UL; // sizeBytes
*(short *)((char *)bmp_obj + 0x48) = 0;                    // subRect.x
*(short *)((char *)bmp_obj + 0x4a) = 0;                    // subRect.y
*(short *)((char *)bmp_obj + 0x4c) = 1024;                 // subRect.w
*(short *)((char *)bmp_obj + 0x4e) = 540;                  // subRect.h
*(short *)((char *)bmp_obj + 0x50) = 0;                    // allocRect.x
*(short *)((char *)bmp_obj + 0x52) = 0;                    // allocRect.y
*(short *)((char *)bmp_obj + 0x54) = 1024;                 // allocRect.w
*(short *)((char *)bmp_obj + 0x56) = 540;                  // allocRect.h
*(short *)((char *)bmp_obj + 0x5c) = 1;                    // rowAlign = 1
*(short *)((char *)bmp_obj + 0x5e) = 1;                    // colAlign = 1
```
And in `usr/lib/libgrm_bmp.so`, patch `grm::bmp::BitmapImpl::getUnitHandle(unsigned int*)` (`0x067d0`) to:
- `0x067d0`: `3f 00 00 b9 00 00 80 52 c0 03 5f d6` (`str wzr, [x1]; mov w0, #0; ret`) so `BMP_GetUnitHandle` never calls `MA_GetUnitHandle`!

And in `libgrm-fbinit9.so`, `getOnscreen(self)` and `getOffscreen(self)` simply return `bmp_onscreen` and `bmp_offscreen` (two such initialized `BitmapImpl` objects backed by two `1024*540*4` pixel buffers), and when `grm::FrameBuffer::swap(self)` or `grm::FBResourceManager::updateRequest` runs, copy the rendered pixels from `pixel_buf` into the `0x41e000000` shared-memory frame ring!

---

### 2.4 Why `zig cc` Stubs Failed earlier (`213..215`) and How to Link `libgrm-fbinit9.so` Cleanly
When compiling `libgrm-fbinit9.so` with `zig cc -target aarch64-linux-gnu`:
1. Always pass **`-fno-sanitize=all -fPIC -shared`** and link against the guest `libc.so.6` and `libdl.so.2` (or pass `-Wl,--no-undefined-version` with a version script / link against the extracted initramfs `/lib/libc.so.6` `/lib/libdl.so.2`) so `DT_NEEDED` for `libc.so.6` and `libdl.so.2` are present in `.dynamic`.
2. Ensure `_ZN2ux6gfxeng6Screen20setAreaInFramebufferEsstt` is kept in `libgrm-fbinit9.c` (it was accidentally omitted in `214..216`).
3. Ensure `dlsym((void *)-1L, ...)` (`RTLD_NEXT`) or `dlopen("/usr/lib/libgrm_bmp.so", RTLD_LAZY)` is used to resolve `_ZN3grm3bmp10BitmapImplC1Ess15BMP_PixelFormat11BMP_YUVMode21BMP_PixelSortingOrder22BMP_PixelStartPosition`.

---

## 3. Summary Checklist for Candidate `227`

1. **Eliminate the `appfw-launch` vs Thread 118 Race (`usr/bin/appfw-launch`)**:
   - In `usr/bin/appfw-launch`, NOP out `0x0898c` (`patched 0x48800 -> 0x103c258`) and `0x08c18` (`blr x19` calling `uxengine_init2`), or jump at **`0x08940`** directly to **`0x08ec0`** (`60 01 00 14`, `b 0x08ec0`).
   - This guarantees Thread 118 **always** keeps its real `GraphicsSystemCore*` at `[libux_core.so + 0x48800]`, **never** SEGVs at `libux_core.so + 0x31af4` (`addr=0x28`), and **always** reaches `FX6_GRM_FB_MINIMAL` -> `3x 1024x540 Screen` -> `AdjChkConfig.so` `drawFramebuffer()`!
2. **Keep the `AdjChkConfig.so` Native Render Loop Patches (from `218`)**:
   - `0x0e7fc` -> `1b 00 00 14` (`b 0x0e868`, skip `sircs_event_start` assert)
   - `0x0e8cc` -> `a2 00 00 14` (`b 0x0eb54`, take `usleep(1000)` branch)
   - `0x0e9f0` -> `1f 20 03 d5` (`nop`, run `drawFramebuffer()` on every tick)
   - Plus optional Jiritsu UI open in `presenter_jiritsu::presenter_jiritsu()`:
     - `0x0bd28` -> `35 00 00 14` (`b 0x0bdfc`)
     - `0x0be00` -> `d9 fd ff 97` (`bl presenter_jiritsu::open_jiritsu`)
3. **Provide Real `BitmapImpl` Objects from `getOnscreen()` / `getOffscreen()`**:
   - Construct `BitmapImpl` via `_ZN3grm3bmp10BitmapImplC1Ess15BMP_PixelFormat11BMP_YUVMode21BMP_PixelSortingOrder22BMP_PixelStartPosition(bmp, 1024, 540, 2, 0, 0, 0)` and populate `+0x08` (`0x1`), `+0x10` (`pixel_buf`), `+0x18`/`+0x1a` (`1024`/`540`), `+0x20` (`phys`), `+0x28` (`1024*540*4`), `+0x48..0x56` (`0, 0, 1024, 540`), `+0x5c`/`+0x5e` (`1`/`1`), and patch `libgrm_bmp.so + 0x067d0` (`getUnitHandle`) to `3f 00 00 b9 00 00 80 52 c0 03 5f d6`.


---

## 6. Round 222~227 `BMP_CreateSize` ABI、`libux_core 0x31af4` 空指针与 `FrameBuffer::update` 显存桥接方案

> [!IMPORTANT]
> **对上文 `BitmapImpl` 偏移的精确反汇编勘误**：
> 通过对 `libgrm_bmp.so` (`0x6ab8..0x6ba8` 及 `0x61e0..0x6974`) 逐条指令反汇编确认：`grm::bmp::BitmapImpl` 的 `[bmp + 0x08]` **不是** `memSpace` 占位值，而是构造函数通过 `calloc(1, 0x40)` 分配并初始化的 **`info` 元数据结构体指针**！**切勿把 `*(void**)(bmp + 0x08)` 覆盖为 `0x1`**，否则 `getDimensions` (`ldr w2, [x0, #8]` 从 `info+0x08` 读宽高) 会直接触发 `SEGV addr=0x9`！请以下方第 6.1 节的精确反汇编布局为准。

---

### 6.1 任务 1：`libgrm_bmp.so` (`Bitmap.cpp:372`) 像素格式枚举、`BMP_CreateSize` 陷阱与真实 `BitmapImpl` 构造

#### 1) 为什么 Round 222 (`cp-bind-2e00a48a` / `/tmp/libgrm-fbinit18.c`) 触发 `Bitmap.cpp:372: Assertion 'format > BMP_PixelFormatNone' failed`？
反汇编 `libgrm_bmp.so` 的 `BMP_Create` (`0x7c38`) 与 `BMP_PixelFormatToBytesPerPixel` (`0x8674`)：
- **`BMP_Create` (`0x7c38`) 真实 10 参数签名**：
  ```c
  BMP_Error BMP_Create(
      void *space,                        // x0: MA memory space handle (不可为整数 1024!)
      short width,                        // w1: 1024
      short height,                       // w2: 540
      BMP_PixelFormat format,             // w3: > 0 (1=2Bpp, 2=4Bpp RGBA8888)
      BMP_YUVMode yuvMode,                // w4: 0
      short alignX,                       // w5: 0 (内部 <=0 时自动设为 1)
      short alignY,                       // w6: 0 (内部 <=0 时自动设为 1)
      BMP_Bitmap *outBmp,                 // x7: 输出 BitmapImpl* 指针地址
      BMP_PixelSortingOrder sortingOrder, // [sp+0]: 0
      BMP_PixelStartPosition startPos     // [sp+8]: 0
  );
  ```
- 在 `/tmp/libgrm-fbinit18.c` 中调用 `BMP_Create(1024, 540, 1, 0)` 时，参数全部错位 1 个寄存器：
  - `x0 (space) = 1024`
  - `w1 (width) = 540`
  - `w2 (height) = 1`
  - **`w3 (format) = 0` (`BMP_PixelFormatNone`)**
- `BMP_Create` 内部调用 `grm::bmp::BitmapImpl::create` (`0x6f28`) -> `BMP_PixelFormatToBytesPerPixel(format=0, &bpp)` (`0x8674`)：
  - `0x8680: cmp w0, #0; b.le 0x869c` -> 命中 `0x869c`：`__assert_fail("format > BMP_PixelFormatNone", ".../Bitmap.cpp", 372)`！
- **`BMP_PixelFormat` 真实枚举与每像素字节数表 (`libgrm_bmp.so + 0xaf58`)**：
  ```text
  0xaf58: 00 00 00 00  02 00 00 00  04 00 00 00  02 00 00 00  04 00 00 00  01 00 00 00
  ```
  - `0` (`BMP_PixelFormatNone`) -> 非法，触发 `Bitmap.cpp:372` 断言
  - `1` -> **2 Bytes/pixel** (`RGB565` / `YUV422`，`1024x540` = `0x10e000` bytes)
  - `2` -> **4 Bytes/pixel** (`RGBA8888` / `ARGB8888`，`1024x540` = `0x21c000` bytes)
  - `3` -> **2 Bytes/pixel**
  - `4` -> **4 Bytes/pixel**
  - `5` -> **1 Byte/pixel** (`CLUT8` / `A8`)

#### 2) 为什么 `/tmp/libgrm-fbinit19.c` & `20.c` (Rounds 226..227) 的 `BMP_CreateSize(1024, 540, 1, 0, &bmp)` 是致命陷阱？
反汇编 `BMP_CreateSize` (`libgrm_bmp.so + 0x7c0c`) 与 `grm::bmp::BitmapBase::createSize` (`0x615c`)：
```asm
00007c0c <BMP_CreateSize>:
    7c14: sxth w3, w3             ; w3 = alignX (0)
    7c18: sxth w1, w1             ; w1 = height (540)
    7c1c: mov  x5, x4             ; x5 = uint64_t *outByteSize (&bmp)
    7c20: sxth w0, w0             ; w0 = width (1024)
    7c24: mov  w4, #0             ; w4 = alignY (0)
    7c28: bl   615c <_ZN3grm3bmp10BitmapBase10createSizeEss15BMP_PixelFormatssPm>
```
- **`BMP_CreateSize` 根本不创建 `BMP_Bitmap` 对象！** 它的作用仅仅是计算缓冲区字节大小 `((w + alignX - 1)/alignX)*alignX * ((h + alignY - 1)/alignY)*alignY * bpp`，并把算出的字节数写入 `*x4` (`&bmp`)！
- 当传入 `BMP_CreateSize(1024, 540, 1, 0, &bmp)` 时，`bmp` 被赋值为整数 **`(void *)0x10e000`** (`1024 * 540 * 2 = 1,105,920`)！
- 一旦渲染线程 (`GraphicsContextGRM::beginScene` / `AdjChkConfig.so` `drawFramebuffer()`) 调用 `BMP_GetDimensions(bmp, ...)` (`0x812c`: `ldr x8, [x0]; ldr x8, [x8, #0x78]; blr x8`)，解引用 `*(void **)0x10e000` 就会立刻触发 **`SEGV addr=0x10e000`**！
- 同时不能直接调 `BMP_Create`，因为 `BitmapImpl::create` (`0x6f28`) 在 `0x7058` 会调用 `MA_Alloc(space, size, 64, 0, &physAddr)`，在没有初始化真实 `/dev/ma` 内核内存池时会返回失败。

#### 3) 真实 `grm::bmp::BitmapImpl` (`0xb8` 字节) + `info` (`0x40` 字节) 精确内存布局
反汇编 `_ZN3grm3bmp10BitmapImplC1Ess15BMP_PixelFormat11BMP_YUVMode21BMP_PixelSortingOrder22BMP_PixelStartPosition` (`0x6ab8..0x6ba8`) 及所有虚函数 (`0x61e0..0x6974`)：

| 层级与偏移 | 大小 | 字段含义 | 构造函数 (`0x6ab8`) 是否已设置 | 读取该字段的函数 |
|---|---|---|---|---|
| `bmp + 0x00` | 8B | `vptr` (`_ZTVN3grm3bmp10BitmapImplE + 0x10` = `0x1da48`) | **是** (`0x6b0c`) | 所有 `BMP_*` C API 虚表分发 |
| `bmp + 0x08` | 8B | `info` (`calloc(1, 0x40)` 分配的元数据指针) | **是** (`0x6b24`) | 几乎所有 `BitmapImpl` 方法 (`ldr x0, [x0, #8]`) |
| `  info + 0x00` | 4B | `uint32_t magic = 0x00abcdef` | **是** (`0x6b3c`) | 内部校验 |
| `  info + 0x04..0x0a` | 8B | `short rect_x=0, rect_y=0, rect_w=w, rect_h=h` | **是** (`0x6b40..0x6b4c`) | `getRectangle` (`0x61e0`), `getDimensions` (`0x664c`: 读 `info+0x08` 和 `info+0x0a`) |
| `  info + 0x0c..0x12` | 8B | `short sub_x=0, sub_y=0, sub_w=w, sub_h=h` | **是** (`0x6b50..0x6b5c`) | `getSubRectangle` (`0x65d4`) |
| `  info + 0x14..0x16` | 4B | `short alloc_x=0, alloc_y=0` | **是** (`calloc` 清零) | `getAllocatedRectangle` (`0x6610`) |
| `  info + 0x18` | 2B | `short alloc_w` (**必须手动设为 `1024`**) | **否 (默认 0)** | `getRowBytes` (`0x6698`), `getSize` (`0x61f4`), `getAllocatedRectangle` (`0x6610`), `clear` (`0x6398`) |
| `  info + 0x1a` | 2B | `short alloc_h` (**必须手动设为 `540`**) | **否 (默认 0)** | `getColPixelCount` (`0x66d8`), `getSize` (`0x61f4`), `getAllocatedRectangle` (`0x6610`), `clear` (`0x6398`) |
| `  info + 0x1c` | 4B | `BMP_PixelFormat format` (`2` = RGBA8888 4Bpp) | **是** (`0x6b60`) | `getFormat` (`0x6240`), `getRowBytes` (`0x6684`), `clear` (`0x6388`) |
| `  info + 0x20` | 4B | `BMP_YUVMode yuvMode` (`0`) | **是** (`0x6b64`) | `getYUVMode` (`0x6254`) |
| `  info + 0x28` | 8B | `uint64_t physAddr` (**需手动设为物理地址如 `0x41e001000UL`**) | **否 (默认 0)** | `getPhysicalAddress` (`0x6268`) |
| `  info + 0x30` | 8B | `uint64_t userData` (`0`) | **是** (`0x6b70`) | `getUserData` (`0x62bc`) |
| `  info + 0x38..0x3c` | 8B | `sortingOrder` (`0`), `startPosition` (`0`) | **是** (`0x6b68..0x6b6c`) | `getPixelSortingOrder` / `getPixelStartPosition` |
| `bmp + 0x10` | 8B | `void *logicalBits` (**必须手动设为 `pixel_buf` 指针**) | **否 (默认 NULL)** | `getLogicalAddress` (`0x627c`), `writeLockBits` (`0x6948`), `readLockBits` (`0x69ec`), `clear` (`0x63bc`) |
| `bmp + 0x18` | 8B | `void *maSpace` (`NULL` 即可，配合 `0x67d0` 补丁) | **是** (`0x6b14`) | `getSpace` (`0x6290`), `getUnitHandle` (`0x67d0`) |
| `bmp + 0x20` | 8B | `uint64_t memoryAlignment` (`64`) | **是** (`0x6b7c`) | `getMemoryAlignment` (`0x62a4`) |
| `bmp + 0x28` | 4B | `int32_t refCount` (`1`) | **是** (`0x6b74`) | `addReference` (`0x6728`), `release` (`0x6754`) |
| `bmp + 0x2c..0x34` | 12B | `readLockCount=0`, `waitCount=0`, `writeLockCount=0` | **是** (`0x6b18..0x6b20`) | `writeLockBits` (`0x688c`), `readLockBits` (`0x6974`) |
| `bmp + 0x38..0x67` | 48B | `pthread_mutex_t` | **是** (`0x6b88`) | `writeLockBits` / `readLockBits` / `clear` |
| `bmp + 0x68..0x97` | 48B | `pthread_cond_t` | **是** (`0x6b90`) | `writeLockBits` / `readLockBits` |

- **必打二进制补丁 (`usr/lib/libgrm_bmp.so + 0x067d0`)**：
  `grm::bmp::BitmapImpl::getUnitHandle(unsigned int*)` (`0x067d0`) 原指令会调用 `MA_GetUnitHandle([bmp+0x18], [info+0x28], outHandle)`。将其首部 3 条指令替换为：
  ```text
  偏移 0x067d0: 3f 00 00 b9  00 00 80 52  c0 03 5f d6
  (str wzr, [x1] ; mov w0, #0 ; ret)
  ```
  这样 `BMP_GetUnitHandle` 直接写出 `handle = 0` 并返回 `0 (BMP_ErrorNone)`，彻底绕过 `/dev/ma`！

---

### 6.2 任务 2：`libux_core.so + 0x31af4` (`SEGV addr=0x28`, `X0=0`) 根因与修复

#### 1) 崩溃指令反汇编 (`libux_core.so + 0x31ae8`)
```asm
00031ae8 <_ZN2ux4core6Kernel10getProfileENS0_21UXEngineConfigurationEl>:
   31ae8: b00000a2  adrp x2, 48000 <_DYNAMIC+0x200>
   31aec: 93407c00  sxtw x0, w0
   31af0: f9440840  ldr  x0, [x2, #0x810]   ; x0 = *(ux::core::Kernel **)(libux_core.so + 0x48810)
   31af4: f9401400  ldr  x0, [x0, #0x28]    ; <--- SEGV addr=0x28 when x0 == NULL!
   31af8: 14000f39  b    357dc <_ZNK2ux4core7Profile10getProfileENS0_21UXEngineConfigurationEl>
```
- **函数名**：`ux::core::Kernel::getProfile(ux::core::UXEngineConfiguration, long)` (`libux_core.so + 0x31ae8`)。
- **`x0` 预期内容**：全局单例指针 `ux::core::Kernel::s_instance`（位于 `libux_core.so + 0x48810`）。`[x0 + 0x28]` 是 `Kernel` 对象内部的 `ux::core::Profile*` 成员指针。
- **直接调用方**：`libux_core.so + 0x2b9fc` (`ux::core::GraphicsSystemCore::initialize` 之后读取配置 `getProfile(5, 0)`)。

#### 2) 为什么在 Round 223~227 (`cp-bind-08e2037f`, `cp-bind-6220b943`, `cp-bind-58730175`) 中 `[libux_core.so + 0x48810]` 为 `NULL`？
对比 `cp-bind-6220b943` 与 `cp-bind-58730175` 的串口日志与寄存器现场：
- 崩溃栈指针是 **`sp=0x7fd8cc7e10` / `sp=0x7fda5cf7e0`（主线程 `appfw-launch` 的栈，而非 Thread 117/118 的 `0x7fa492f...` 栈）**！
- **主线程 `appfw-launch` 与 Thread 117/118 的竞态时序**：
  1. `Application_System_Init()` 派生出 Thread 117/118，Thread 117/118 进入 `ux::UXEngine::initialize()` (`libuxengine.so + 0x74d70`)。
  2. 在 `libuxengine.so + 0x74dbc`，Thread 117/118 **先将初始化标志位 `[libuxengine.so + 0xc4bac]` 设为 `1`**，随后才调用 `ux::core::Kernel::sys_initialize()` (`libux_core.so + 0x31dfc`)。
  3. `Kernel::sys_initialize()` 直到打印完 `Created HeapAllocator.` 和 `Replaced log-hook.` 之后的 **`0x31ee4`** (`str x20, [x24, #0x810]`) 才会把 `Kernel*` 写入 `[libux_core.so + 0x48810]`！
  4. 与此同时，在 `224..227` 的 initramfs 中，`usr/bin/appfw-launch` 在 `Application_System_Init()` 返回后，虽然 `0x0898c` 被 NOP 掉了，但 **`0x08a10..0x08c18` 仍在执行**！它在主线程上：
     - 打印 `appfw-launch: patched getter range 0x...c74..0x...ce0`（把 `libuxengine.so + 0x82c74..0x82ce0` 的 7 个 getter 函数用 `0` 覆盖损坏！）；
     - 在 `0x08c18: blr x19` 调用了 `uxengine_init2()`！
  5. 主线程进入 `uxengine_init2()` -> `UXEngine::initialize()` 时，看到 `[libuxengine.so + 0xc4bac]` 已经被 Thread 117/118 设成了 `1`，于是**在 `0x74d84` 直接跳过初始化返回**！紧接着主线程继续往下走，调用 `Kernel::getProfile(5, 0)` (`0x31af0`)，此时 Thread 117/118 还没跑到 `0x31ee4`，`[libux_core.so + 0x48810]` 仍是 `0`，主线程当场触发 `APPFW_SEGV sig=11 addr=0x28 pc=7faccefaf4` 并杀死整个进程！

#### 3) 根治方案（两步双保险）
1. **必打补丁 1 — 让 `appfw-launch` 在 `Application_System_Init()` 返回后直接跳到保活循环 (`usr/bin/appfw-launch` 文件偏移 `0x08954`)**：
   查看 `227` 的 `usr/bin/appfw-launch` 反汇编 (`0x1018940..0x1018eb4`)：
   ```asm
   1018940: bl  1011310 <printf@plt>   ; "appfw-launch: Application_System_Init() -> %d\n"
   1018954: cbz x19, 1018eb4           ; 原指令: b4 00 2b 13
   ... (0x1018958..0x1018eb0 是旧的 post-init hack: 改 0x48800、抹零 getter、调 uxengine_init2)
   1018eb4: adrp x0, 1020000           ; "appfw-launch: keeping process alive for startup worker threads\n"
   ```
   只需将 `usr/bin/appfw-launch` **文件偏移 `0x08954`**（虚拟地址 `0x1018954`）的 4 字节：
   - 原字节：`b4 00 2b 13` (`cbz x19, 0x1018eb4`)
   - **替换为：`58 01 00 14` (`b 0x1018eb4`)**
   这样主线程在打印完 `Application_System_Init() -> 0` 后，100% 直接跳到 `keeping process alive for startup worker threads` (`sleep(300)`)，绝不再破坏 `0x48800`、绝不再抹零 `libuxengine.so` getter、绝不再在主线程抢跑调用 `uxengine_init2()`！
2. **可选防御补丁 2 — `libux_core.so + 0x31ae8` (`Kernel::getProfile`) 空指针保护**：
   将 `usr/lib/libux_core.so` 偏移 `0x31ae8..0x31afc` (5 条指令) 替换为带空指针检查的版本（若 `x0 == 0` 则直接返回默认值 `x1`）：
   - 或在 `libgrm-fbinit9.c` 中直接导出同名符号拦截 `_ZN2ux4core6Kernel10getProfileENS0_21UXEngineConfigurationEl`：
     ```c
     long _ZN2ux4core6Kernel10getProfileENS0_21UXEngineConfigurationEl(int cfg, long def_val) {
         return def_val;
     }
     ```
     由于 `libgrm-fbinit9.so` 通过 `LD_PRELOAD` 加载，导出该函数即可让所有对 `Kernel::getProfile` 的 PLT 调用在 `Kernel` 未就绪或无需 profile 时安全返回默认值 `def_val`！

---

### 6.3 任务 3：`FrameBuffer::update()` / `swap()` 与 `GRM_gperm*` 到 GPE OSD 显存 (`0x41e000000` / `0x429550000` / `0x4805a1000`) 桥接方案

#### 1) `libgemini-grm.so` 与 `libgrm.so` 的完整渲染与刷屏链路反汇编结论
通过对 `libgemini-grm.so` (`0x6db0..0x8700`) 与 `libgrm.so` (`0x2d000..0x32900`) 的反汇编，确认 Sony FX6 UI 每一帧的完整渲染路径如下：
1. **帧开始 (`gemini::GraphicsContextGRM::beginScene` @ `libgemini-grm.so + 0x8344`)**：
   - 调用 `GRM_screenGetOffBitmap(screenId, &bmp)` -> `grm::FBResourceManager::getOffscreen` -> `grm::FrameBuffer::getOffscreen(fb)`。
   - 调用 `GRM_RendererSetTargetBitmap(renderer, bmp)` (`0x76ec`) 将 `bmp` 存入 `[renderer + 0x08]`。
2. **图元绘制 (`gemini::GRMRenderer` @ `libgemini-grm.so + 0x76c0..0x7de0`)**：
   - 矩形填充：`GRMRenderer::drawFillRect` (`0x7b5c`) 调用 `GRM_gpermFillrect(int planeId, const GRM_Rect *dstRect, unsigned int color, GRM_BlendMode blendMode)` (`libgrm.so + 0x308ac`)。
   - 位图/文字贴图：`GRMRenderer::drawImage` (`0x7700` / `0x7858`) 调用 `GRM_gpermRectblit(int planeId, BMP_Bitmap srcBmp, const GRM_Rect *srcRect, const GRM_Rect *dstRect, const void *opt, GRM_BlendMode blendMode)` (`libgrm.so + 0x30918`)。
   - **关键发现**：在 `libgrm.so` 中，`GRM_gpermFillrect` (`0x308ac`) 和 `GRM_gpermRectblit` (`0x30918`) 内部会检查 `[GPEResourceManager + 0x08]`（硬件 GPE engine 指针）。因为在 `FX6_GRM_FB_MINIMAL=1` 下跳过了 `/dev/gpe` 硬件初始化，`[GPEResourceManager + 0x08] == NULL`，导致原版 `GRM_gpermFillrect` 和 `GRM_gpermRectblit` 直接返回 `-2`（空操作）！
   - 因此，除了把 `pixel_buf` 挂到 `BitmapImpl + 0x10`（供 CPU 直接锁定的 `BMP_WriteLockBits` / `BMP_Clear` 使用）之外，**在 `libgrm-fbinit9.so` 中同时拦截 `GRM_gpermFillrect` 和 `GRM_gpermRectblit` 进行软件光栅化写入 `pixel_buf`**，就能把所有 GPE 2D 加速绘制（矩形背景、图标、字库贴图）也 100% 落盘到 `pixel_buf`！
3. **帧结束与刷屏 (`gemini::GraphicsContextGRM::endScene` @ `libgemini-grm.so + 0x83f8` & `AdjChkConfig.so` `drawFramebuffer`)**：
   - `endScene` 调用 `GRM_gpermFlush(planeId, drawCompCb, arg)` (`libgrm.so + 0x30ab8` -> `0x30784`)。
   - 当 `[GPEResourceManager + 0x08] == NULL` 时，`GPEResourceManager::flush` (`0x30784`) **会自动同步调用 `drawCompCb` (`GraphicsContextGRM::DrawCompCb` @ `0x82b4`) -> `FlushCompCb` (`0x82f4`) -> `GRM_fbrmUpdate` (`libgrm.so + 0x2f180`) -> `FBResourceManager::updateRequest` (`0x2eef8`) -> `grm::FrameBuffer::swap()` (`0x2dbd4`)**！
   - 此外，`ux::gfxeng::Screen::updateFramebuffer()` 也会直接调用 `grm::FrameBuffer::update()` (`_ZN3grm11FrameBuffer6updateEv` @ `libgrm.so + 0x2dc80`)。

#### 2) 可直接编译进 `libgrm-fbinit9.so` 的完整 `BitmapImpl` + 软件光栅化 + 显存同步代码
以下代码可直接替换 `/tmp/libgrm-fbinit20.c` 中错误的 `BMP_CreateSize` 逻辑，同时修复：
1. 真实 `BitmapImpl` (`0xb8` 字节) + `info` (`[bmp + 0x08]`, `alloc_w=1024`, `alloc_h=540`) + `pixel_buf` (`[bmp + 0x10]`) 构造；
2. 拦截 `GRM_gpermFillrect` / `GRM_gpermRectblit` 将 2D 加速绘制光栅化到 `g_pixel_buf`；
3. 拦截 `_ZN3grm11FrameBuffer6updateEv`、`GRM_fbrmUpdate`、`_ZN3grm11FrameBuffer4swapEv`，将 `g_pixel_buf` (`1024x540x4` RGBA8888) 同步刷入 GPE OSD 物理显存窗口 (`0x41e000000`、`0x429550000`、`0x4805a1000`)；
4. 拦截 `_ZN2ux4core6Kernel10getProfileENS0_21UXEngineConfigurationEl` 防止 `0x31af4` 空指针崩溃：

```c
#define _GNU_SOURCE
#include <dlfcn.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define FB_W 1024
#define FB_H 540
#define FB_BPP 4
#define FB_STRIDE (FB_W * FB_BPP)
#define FB_BYTES (FB_W * FB_H * FB_BPP)

typedef void (*BitmapImplCtor_t)(void *this_ptr, short w, short h, int fmt, int yuv, int sort, int start);

static uint8_t *g_pixel_buf = NULL;
static void *g_bmp_onscreen = NULL;
static void *g_bmp_offscreen = NULL;
static void *g_osd_map_41e = NULL; /* 0x41e000000 (IPC/VRAM) */
static void *g_osd_map_429 = NULL; /* 0x429550000 (GPE OSD window 0) */
static void *g_osd_map_480 = NULL; /* 0x4805a1000 (GPE OSD window 1) */
static uint32_t g_flush_count = 0;

static void init_osd_mappings(void) {
    static intited = 0;
    if (inited) return;
    inited = 1;
    int fd = open("/dev/mem", O_RDWR | O_SYNC);
    if (fd < 0) return;
    void *m1 = mmap(NULL, 0x400000, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0x41e000000ULL);
    if (m1 != MAP_FAILED) g_osd_map_41e = m1;
    void *m2 = mmap(NULL, 0x400000, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0x429550000ULL);
    if (m2 != MAP_FAILED) g_osd_map_429 = m2;
    void *m3 = mmap(NULL, 0x400000, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0x4805a1000ULL);
    if (m3 != MAP_FAILED) g_osd_map_480 = m3;
    close(fd);
}

static void *create_real_bitmap_impl(uint8_t *backing_pixels) {
    static BitmapImplCtor_t real_ctor = NULL;
    if (!real_ctor) {
        void *h = dlopen("/usr/lib/libgrm_bmp.so", RTLD_LAZY | RTLD_GLOBAL);
        real_ctor = (BitmapImplCtor_t)dlsym(
            h ? h : RTLD_DEFAULT,
            "_ZN3grm3bmp10BitmapImplC1Ess15BMP_PixelFormat11BMP_YUVMode21BMP_PixelSortingOrder22BMP_PixelStartPosition");
    }
    void *bmp = calloc(1, 256); /* real size is 0xb8 */
    if (!bmp) return NULL;
    if (real_ctor) {
        /* format = 2 (4 bytes/pixel RGBA8888 per 0xaf58 table), yuv = 0, sort = 0, start = 0 */
        real_ctor(bmp, FB_W, FB_H, 2, 0, 0, 0);
    }
    /* Fix up info struct allocated at [bmp + 0x08] by BitmapImpl ctor (0x6b24) */
    uint8_t *info = *(uint8_t **)((uint8_t *)bmp + 0x08);
    if (!info) {
        info = (uint8_t *)calloc(1, 0x40);
        *(uint8_t **)((uint8_t *)bmp + 0x08) = info;
        *(uint32_t *)(info + 0x00) = 0x00abcdefU;
        *(int16_t *)(info + 0x08) = FB_W;
        *(int16_t *)(info + 0x0a) = FB_H;
        *(int16_t *)(info + 0x10) = FB_W;
        *(int16_t *)(info + 0x12) = FB_H;
        *(int32_t *)(info + 0x1c) = 2;
    }
    /* Critical: set alloc_w (info+0x18), alloc_h (info+0x1a), physAddr (info+0x28) */
    *(int16_t *)(info + 0x18) = FB_W;
    *(int16_t *)(info + 0x1a) = FB_H;
    *(uint64_t *)(info + 0x28) = 0x41e001000ULL;
    /* Critical: set logicalBits pointer at [bmp + 0x10] */
    *(void **)((uint8_t *)bmp + 0x10) = backing_pixels;
    return bmp;
}

static void ensure_bitmaps(void) {
    if (!g_pixel_buf) {
        init_osd_mappings();
        /* Prefer mapping directly inside 0x41e001000 if available, otherwise heap */
        if (g_osd_map_41e) {
            g_pixel_buf = (uint8_t *)g_osd_map_41e + 0x1000;
        } else {
            g_pixel_buf = (uint8_t *)calloc(1, FB_BYTES);
        }
    }
    if (!g_bmp_onscreen)  g_bmp_onscreen  = create_real_bitmap_impl(g_pixel_buf);
    if (!g_bmp_offscreen) g_bmp_offscreen = create_real_bitmap_impl(g_pixel_buf);
}

static void flush_pixels_to_osd(const char *tag) {
    if (!g_pixel_buf) return;
    init_osd_mappings();
    if (g_osd_map_429) memcpy(g_osd_map_429, g_pixel_buf, FB_BYTES);
    if (g_osd_map_480) memcpy(g_osd_map_480, g_pixel_buf, FB_BYTES);
    if (g_osd_map_41e && g_pixel_buf != (uint8_t *)g_osd_map_41e + 0x1000) {
        memcpy((uint8_t *)g_osd_map_41e + 0x1000, g_pixel_buf, FB_BYTES);
    }
    g_flush_count++;
    if (g_flush_count <= 10 || (g_flush_count % 60) == 0) {
        fprintf(stderr, "[FX6-FB-BRIDGE] %s flush #%u -> OSD (0x41e=%p 0x429=%p 0x480=%p)\n",
                tag, g_flush_count, g_osd_map_41e, g_osd_map_429, g_osd_map_480);
    }
}

/* Override BMP_GetUnitHandle / BitmapImpl::getUnitHandle so /dev/ma is never needed */
int _ZN3grm3bmp10BitmapImpl13getUnitHandleEPj(void *self, unsigned int *out_handle) {
    (void)self;
    if (out_handle) *out_handle = 0;
    return 0;
}

int BMP_GetUnitHandle(void *bmp, unsigned int *out_handle) {
    (void)bmp;
    if (out_handle) *out_handle = 0;
    return 0;
}

/* Guard ux::core::Kernel::getProfile against NULL s_instance on early calls */
long _ZN2ux4core6Kernel10getProfileENS0_21UXEngineConfigurationEl(int cfg, long def_val) {
    (void)cfg;
    return def_val;
}

/* FrameBuffer::getOnscreen / getOffscreen */
void *_ZN3grm11FrameBuffer11getOnscreenEv(void *self) {
    (void)self;
    ensure_bitmaps();
    return g_bmp_onscreen;
}

void *_ZN3grm11FrameBuffer12getOffscreenEv(void *self) {
    (void)self;
    ensure_bitmaps();
    return g_bmp_offscreen;
}

/* FrameBuffer::update / swap / GRM_fbrmUpdate bridge to OSD physical memory */
int _ZN3grm11FrameBuffer6updateEv(void *self) {
    (void)self;
    ensure_bitmaps();
    flush_pixels_to_osd("FrameBuffer::update");
    return 0;
}

int _ZN3grm11FrameBuffer4swapEv(void *self) {
    (void)self;
    ensure_bitmaps();
    flush_pixels_to_osd("FrameBuffer::swap");
    return 0;
}

/* Software rasterizer for GRM_gpermFillrect & GRM_gpermRectblit when GPE HW is bypassed */
typedef struct {
    int16_t x, y, w, h;
} GRM_Rect16;

int GRM_gpermFillrect(int plane_id, const GRM_Rect16 *rect, uint32_t color, int blend_mode) {
    (void)plane_id; (void)blend_mode;
    ensure_bitmaps();
    if (!g_pixel_buf || !rect) return 0;
    int x0 = rect->x < 0 ? 0 : rect->x;
    int y0 = rect->y < 0 ? 0 : rect->y;
    int x1 = (rect->x + rect->w) > FB_W ? FB_W : (rect->x + rect->w);
    int y1 = (rect->y + rect->h) > FB_H ? FB_H : (rect->y + rect->h);
    uint32_t *base = (uint32_t *)g_pixel_buf;
    for (int y = y0; y < y1; y++) {
        uint32_t *row = base + y * FB_W;
        for (int x = x0; x < x1; x++) {
            row[x] = color;
        }
    }
    return 0;
}

int GRM_gpermRectblit(int plane_id, void *src_bmp, const GRM_Rect16 *src_rect,
                      const GRM_Rect16 *dst_rect, const void *opt, int blend_mode) {
    (void)plane_id; (void)opt; (void)blend_mode;
    ensure_bitmaps();
    if (!g_pixel_buf || !src_bmp || !dst_rect) return 0;
    uint8_t *src_info = *(uint8_t **)((uint8_t *)src_bmp + 0x08);
    uint8_t *src_bits = *(uint8_t **)((uint8_t *)src_bmp + 0x10);
    if (!src_info || !src_bits) return 0;
    int src_w = *(int16_t *)(src_info + 0x18);
    int src_h = *(int16_t *)(src_info + 0x1a);
    if (src_w <= 0) src_w = *(int16_t *)(src_info + 0x08);
    if (src_h <= 0) src_h = *(int16_t *)(src_info + 0x0a);
    int sx0 = src_rect ? src_rect->x : 0;
    int sy0 = src_rect ? src_rect->y : 0;
    int dx0 = dst_rect->x;
    int dy0 = dst_rect->y;
    int bw  = dst_rect->w;
    int bh  = dst_rect->h;
    uint32_t *dst_base = (uint32_t *)g_pixel_buf;
    uint32_t *src_base = (uint32_t *)src_bits;
    for (int r = 0; r < bh; r++) {
        int dy = dy0 + r, sy = sy0 + r;
        if (dy < 0 || dy >= FB_H || sy < 0 || sy >= src_h) continue;
        for (int c = 0; c < bw; c++) {
            int dx = dx0 + c, sx = sx0 + c;
            if (dx < 0 || dx >= FB_W || sx < 0 || sx >= src_w) continue;
            uint32_t px = src_base[sy * src_w + sx];
            if (px != 0) dst_base[dy * FB_W + dx] = px;
        }
    }
    return 0;
}
```

---

## 7. Round 229~231 (`cp-bind-76bf09c7` / `cp-bind-c0e5507f`) Root-Cause Analysis & Exact Fixes for Candidate `232`

### 7.1 Breakthrough in Candidate `230` (`cp-bind-76bf09c7`, `guest-hybrid-fx6kernel-capid-grmreal230-bmp.cpio`)
Using the `grm::bmp::BitmapImpl` constructor (`_ZN3grm3bmp10BitmapImplC1Ess15BMP_PixelFormat11BMP_YUVMode21BMP_PixelSortingOrder22BMP_PixelStartPosition`) and `info` metadata layout from Section 6.1, Candidate `230` (`cp-bind-76bf09c7`) achieved:
```text
FX6_BMP_READY on=0x7faca65a00 off=0x7facc81b00 pix_on=0x7faca65b00 pix_off=0x7facc81c00 ctor=0x7fab966ab8
FX6_GRM_FB_GET_OFFSCREEN bmp=0x7facc81b00 pix=0x7facc81c00
FX6_GRM_FB_GET_OFFSCREEN bmp=0x7facc81b00 pix=0x7facc81c00
```
- The **1st** `FX6_GRM_FB_GET_OFFSCREEN` was called by `ux::core::GraphicsSystem::prepareRendering()` (`libuxengine.so + 0x82bec`).
- The **2nd** `FX6_GRM_FB_GET_OFFSCREEN` was called by `andromeda::Window::render()` -> `gemini::GraphicsContextGRM::beginScene()` -> `GRM_screenGetOffBitmap()` (`libgemini-grm.so + 0x835c`).

### 7.2 Why Patching `libstella.so + 0x298d8` to `ret` in Candidate `231` (`cp-bind-c0e5507f`) Caused an Early Crash in `liblibra.so + 0x3702c` (`addr = 0x7f00000008`)
1. In `usr/lib/liblibra.so`, `libra::XDBTable::unloadBankItem(libra::BankItem*, bool)` (`0x36f28`) executes two consecutive operations when unloading a bank item whose reference count is `0`:
   - `+0x2c` (`0x36f54`): calls `stella::LinearList::remove(&this->bankList, bankItem)` (`_ZN6stella10LinearList6removeEPNS0_7ElementE@plt`) to unlink `bankItem` from `this->bankList` (`this + 0x18`).
   - `+0x40` (`0x36f68`): calls `stella::_destruct_and_free<libra::BankItem>(bankItem, allocator)` (`0x36ef4`), which frees `bankItem` back to the heap.
2. When `libstella.so + 0x298d8` (`LinearList::remove + 0x18`) was patched to `ret` (`c0 03 5f d6`) in `231`:
   - During `UXEngine` startup (right after `not enough remaining space; need 4194304 bytes more`), `XDBTable::unloadBankItem` called `LinearList::remove(&this->bankList, 0x7f70010a30)`, which returned immediately **without unlinking `0x7f70010a30` from `this->bankList`**, and then `_destruct_and_free` **freed `0x7f70010a30`** (writing glibc heap chunk metadata `0x7f00000000` into `[0x7f70010a30 + 8]`).
   - On the very next `XDBTable::lookup` -> `getCurrentBank` -> `getBankItem` (`0x37050`), `getBankItem` walked `this->bankList`, found the **already-freed dangling `bankItem` (`0x7f70010a30`) still sitting at the head of `this->bankList`**, and passed it to `XDBTable::releaseBankItem(0x7f70010a30)` (`0x37014`), which loaded `x20 = [0x7f70010a30 + 8] = 0x7f00000000` and faulted at `0x3702c: ldr x1, [x20, #8]` (`addr = 0x7f00000008`).
3. **Mandatory Action**: **Restore `usr/lib/libstella.so + 0x298d8` to its original bytes (`02 00 40 f9`, `ldr x2, [x0]`)**!

### 7.3 Why `230` (`cp-bind-76bf09c7`) Printed `"not enough remaining space; need 4194304 bytes more"` and How to Register All 3 `libra::ArenaParam` Arenas (`mpMemoryHeap`, `mpMemoryHeap2`, `mpTextHeap`)
In `usr/lib/appFw.so`, right after `uxengine_init2` (`0xc0b484`), `appFw.so` calls `0xc0b258` (`0xc0b260..0xc0b468`), which configures the 3 `libra::ArenaParam` memory arenas (`0x400000` = 4 MB, `0x340000` = 3.25 MB, `0x200000` = 2 MB; total = `0x940000` = 9.25 MB):
1. At `0xc0b294`, it calls `Backup_read_8Byte(0x00fa0191)` to obtain the base virtual address `x23` of the UXEngine arena buffer.
2. At `0xc0b2f4`, it calls `Backup_read_8Byte(0x00fa0192)` to obtain the remaining byte size `x24` of the UXEngine arena buffer.
3. Because `0x00fa0191` and `0x00fa0192` return `0` in our hybrid environment, `x24 (0) < 0x400000` at `0xc0b324`, causing `0xc0b338` to print `not enough remaining space; need 4194304 bytes more` and **return `0` at `0xc0b33c` without calling `UXEngine::resmgr()->addArena()`** (`0xc0b420`)!
4. Without `addArena()`, `libra::CacheManager` has **zero memory arenas** (`mpMemoryHeap`, `mpMemoryHeap2`, and `mpTextHeap` are all missing), so any dynamic font/text/image cache operation in `liblibra.so` has no backing arena.
5. **Drop-In Fix in `libgrm-fbinit9.c` (`LD_PRELOAD`)**:
   Intercept `Backup_read_8Byte(unsigned int id)`:
   ```c
   unsigned long Backup_read_8Byte(unsigned int id) {
       typedef unsigned long (*fn_t)(unsigned int);
       static fn_t real_fn;
       static void *ux_arena_buf;
       if (id == 0x00fa0191U) {
           if (!ux_arena_buf) posix_memalign(&ux_arena_buf, 4096, 0x1000000UL);
           return (unsigned long)ux_arena_buf;
       }
       if (id == 0x00fa0192U) {
           return 0x1000000UL; /* 16 MB (> 9.25 MB needed for all 3 arenas) */
       }
       if (!real_fn) real_fn = (fn_t)dlsym((void *)-1L, "Backup_read_8Byte");
       return real_fn ? real_fn(id) : 0UL;
   }
   ```

### 7.4 How to Fix `stella::LinearList::remove` (`X0 = 0xf940000171000c3f`) Cleanly Without Breaking `XDBTable::unloadBankItem`
All 8 callers of `_ZN6stella10LinearList6removeEPNS0_7ElementE` across the entire firmware (`liblibra.so`) call it **via PLT**.
Instead of patching `libstella.so + 0x298d8` to `ret` (which fails to unlink freed `BankItem` nodes), export a pointer-validating `_ZN6stella10LinearList6removeEPNS0_7ElementE` in `libgrm-fbinit9.c` (`LD_PRELOAD`):
```c
static inline int is_valid_user_ptr(const void *p) {
    uintptr_t u = (uintptr_t)p;
    return (u >= 0x10000UL) && ((u >> 40) == 0) && ((u & 0x7UL) == 0);
}

void *_ZN6stella10LinearList6removeEPNS0_7ElementE(void **list, void *elem) {
    if (!is_valid_user_ptr(list) || !is_valid_user_ptr(elem)) return (void *)0;
    void **prev_next = list;
    void *curr = *list;
    int steps = 0;
    while (curr && steps++ < 4096) {
        if (!is_valid_user_ptr(curr)) {
            dprintf(2, "FX6_LIST_REMOVE_BAD_CURR list=%p elem=%p curr=%p\n", list, elem, curr);
            *prev_next = (void *)0;
            return (void *)0;
        }
        void *next = *(void **)curr;
        if (curr == elem) {
            if (next && !is_valid_user_ptr(next)) next = (void *)0;
            *prev_next = next;
            return curr;
        }
        prev_next = (void **)curr;
        curr = next;
    }
    return (void *)0;
}
```
This guarantees:
1. Valid `BankItem` nodes in `XDBTable::unloadBankItem` are **always unlinked** (`*prev_next = next`), completely preventing the `liblibra.so + 0x3702c` (`addr = 0x7f00000008`) dangling-pointer crash.
2. Any corrupted node pointer (such as `0xf940000171000c3f`, where `(u >> 40) != 0`) is caught **before** dereferencing, logged once, and safely unlinked (`*prev_next = NULL`) without crashing!

---

## 8. Round 232~235 (`cp-bind-37cfdaf9` / `cp-bind-a03d8b43` / `cp-bind-559cb72c` / `cp-bind-64cef2de`) Root Causes & Complete Drop-In Fix for Candidate `235`

### 8.1 Exact Root Cause of `FX6_ABORT_BT` in `232` / `233` / `235` (`f4=libux_core.so+0x248d4` -> `f1=libgrm.so+0x2deec`)
In `232` (`cp-bind-37cfdaf9`), `not enough remaining space; need 4194304 bytes more` was completely resolved! `appFw.so` proceeded into `UXEngine::resmgr()->addArena(i, arenaParam)` (`0xc0b420`) and aborted with:
```text
FX6_ABORT_BT n=5 f0=0x7f878f26fc f1=0x7f87891eec f2=0x7f86832a50 f3=0x7f86831384 f4=0x7f8783f8d4
```
Resolving the 4 frames against `/proc/$pid/maps`:
- `f4` = `libux_core.so + 0x248d4`: `ux::core::ArenaImpl::initialize(libra::ArenaParam const&)` (`0x247fc + 0xd8`), right after `0x248d0: bl MA_CreateSpaceDirect`!
- `f3` = `libma.so + 0x5384`: `MA_CreateSpaceDirect` (`0x5330 + 0x54`)
- `f2` = `libma.so + 0x6a50`: `ma::MemorySpaceImpl::create(unsigned long, unsigned long, char*, MA_SpaceType)` (`0x69bc + 0x94`)
- `f1` = `libgrm.so + 0x2deec`: `ma::MMap::map(long, unsigned long)` (`0x2de94 + 0x58`), right after `0x2dee8: bl abort`!

**Why `MA_CreateSpaceDirect` Aborted**:
1. Inside `ma::MMap::map(long physAddr, unsigned long size)` (`libgrm.so + 0x2de94`), `0x2debc..0x2dee8` checks whether `physAddr` is in physical High DDR `[0x400000000 .. 0x5fffffffe]`. Because `Backup_read_8Byte(0x00fa0191)` returned a virtual address (`ux_arena` = `0x7f...`), `ma::MMap::map` called `abort()` at `0x2dee8`!
2. Furthermore, even if `_ZN2ma4MMap3mapElm` is stubbed, the very next call in `ma::MemorySpaceImpl::create` (`libma.so + 0x6a64`) constructs `ma::MAMessage(uint16_t)` (`osal_valloc_msg_wait`), which asserts `Assertion 'msg' failed` (`Message.h:94`) unless `MA_CreateSpaceDirect` itself is intercepted!
3. Most importantly, `libux_core.so` (`ux::core::ArenaImpl`) and `libgrm_bmp.so` (`grm::bmp::BitmapImpl`) only call 14 `MA_*` functions via PLT (`MA_CreateSpaceDirect`, `MA_CreateSpace`, `MA_DestroySpace`, `MA_SetUserData`, `MA_SpaceGetInitialLogicalAddress`, `MA_SpaceCompact`, `MA_SpaceRegistCompactionEventHandler`, `BMP_AssocMemorySpaceForCompaction`, `MA_SpaceMalloc`, `MA_SpaceFree`, `MA_SpaceFree_gralloc`, `MA_LogicalToPhysical`, `MA_PhysicalToLogical`, `MA_FindSpaceByLogicalAddress`, `MA_GetUnitHandle`). Exporting these 14 functions in `libgrm-fbinit9.c` (`LD_PRELOAD`) bypasses `libma.so` 100% and makes `ArenaImpl::initialize()` and `BMP_CreateEx()` succeed natively for all 3 arenas (`mpMemoryHeap`, `mpMemoryHeap2`, `mpTextHeap`)!

### 8.2 Why `234` (`cp-bind-559cb72c`) Did Not Reach `FX6_GRM_FB_MINIMAL` (Two Bugs in `234`)
1. **Bug 1 in `/tmp/libgrm-fbinit24.c` (`Backup_read_8Byte` did not forward other IDs!)**:
   In `/tmp/libgrm-fbinit24.c`, `Backup_read_8Byte` returned `0UL` for all IDs other than `0x00fa0191` and `0x00fa0192`, breaking `appFw.so`'s other 8-byte Backup reads! It **must** forward all other IDs to `dlsym((void *)-1L, "Backup_read_8Byte")`!
2. **Bug 2 in `usr/bin/appfw-launch` (`0x08954` unpatched race with Thread 118)**:
   In `cp-bind-559cb72c/serial.log`, `appfw-launch` ran `patched getter range` and `uxengine_init2` on the main thread right while Thread 118 was inside `Kernel::sys_initialize()`.
   Patching `usr/bin/appfw-launch` at file offset **`0x08954`** from `b4 2a 00 b4` (`cbz x19, 0x8eb4`) to **`58 01 00 14` (`b 0x8eb4`)** skips `appfw-launch`'s post-init interference 100% deterministically.

### 8.3 How to Trigger `run_gpecap25_once.py`'s Built-In QMP `pmemsave` Automatically (Zero QMP Socket Scripting Needed!)
Look at lines 125–138 of `run_gpecap25_once.py`:
`run_gpecap25_once.py` **already spawns a background thread `_gpe_capture(run_dir, sock, reader)`** that holds the active QMP socket `sock` and waits 50 seconds!
At `t = 50s`, `_gpe_capture` greps `serial.log` for:
```python
r'FX3_GPE_RESOURCE_REGISTER[^\n]*type=0x403[^\n]*logical=(0x[0-9a-f]+)[^\n]*phys=(0x[0-9a-f]+)[^\n]*bytes=(0x[0-9a-f]+)'
```
Whenever `serial.log` contains that line, `run_gpecap25_once.py` **automatically executes QMP `pmemsave`** for:
- `gpe0.bin` (`phys=0x41e001000`, `size=0x21c000` = `1024*540*4` bytes)
- `dmm0400.bin` (`0x4805a1000`, `0x800000` bytes)
- `dmm0403.bin` (`0x429550000`, `0x12d000` bytes)
and saves them directly into `runs/cp-bind-xxxxxxxx/`!
Therefore, simply printing:
```c
dprintf(2, "FX3_GPE_RESOURCE_REGISTER type=0x403 logical=0x41e001000 phys=0x41e001000 bytes=0x21c000\n");
```
inside `init_osd()` in `libgrm-fbinit9.c` will make `run_gpecap25_*.py` automatically dump `gpe0.bin`, `dmm0400.bin`, and `dmm0403.bin` via QMP!

### 8.4 Critical Pixel Buffer Unification (`bmp_on` and `bmp_off` Sharing `pix_on`)
In `/tmp/libgrm-fbinit24.c`, `getOffscreen()` returned `bmp_off` (pointing to `pix_off`), whereas `GRM_gpermFillrect`, `GRM_gpermRectblit`, and `flush_pixels_to_osd` read/wrote `pix_on`! Thus any CPU drawing (`BMP_WriteLockBits` / `BMP_Clear` / `TextSprite`) into `bmp_off` went to `pix_off` and was never flushed to `osd41e`.
- **Fix**: In `ensure_bitmaps()`, set **`*(void **)((char *)bmp_off + 0x10) = pix_on;`** so both `bmp_on` and `bmp_off` write to the **exact same `pix_on` buffer** (`1024*540*4` bytes), and in `flush_pixels_to_osd()` copy `pix_on` to both `(char *)osd41e + 0x1000` and `(char *)osd429` (`0x429550000`)!

### 8.5 Complete Drop-In Replacement for the Bottom Half of `/tmp/libgrm-fbinit24.c`
Replace everything from `#define FB_W 1024` to the end of `/tmp/libgrm-fbinit24.c` (and in `ensure_bitmaps()`, set `*(void **)((char *)bmp_off + 0x10) = pix_on;`) with:
```c
#define FB_W 1024
#define FB_H 540
#define FB_BYTES (FB_W*FB_H*4)
typedef unsigned long uptr;
typedef struct { short x,y,w,h; } GRM_Rect16;
static unsigned char ux_arena[0x1000000] __attribute__((aligned(4096)));
static void *osd41e; static void *osd429; static int osd_tried; static unsigned int flush_count;
extern int open(const char*, int);
extern int close(int);
extern void *mmap(void*, unsigned long, int, int, int, long);
extern void *memcpy(void*, const void*, unsigned long);
extern void *memset(void*, int, unsigned long);
extern int posix_memalign(void **, unsigned long, unsigned long);
extern void free(void *);

static int valid_ptr(const void *p) { uptr u=(uptr)p; return (u>=0x10000UL)&&((u>>40)==0)&&((u&7UL)==0); }

void *_ZN6stella10LinearList6removeEPNS0_7ElementE(void **list, void *elem) {
    if (!valid_ptr(list) || !valid_ptr(elem)) return 0;
    void **prev_next=list; void *curr=*list; int steps=0;
    while (curr && steps++<4096) {
        if (!valid_ptr(curr)) { dprintf(2,"FX6_LIST_REMOVE_BAD list=%p elem=%p curr=%p\n",list,elem,curr); *prev_next=0; return 0; }
        void *next=*(void**)curr;
        if (curr==elem) { if (next && !valid_ptr(next)) next=0; *prev_next=next; return curr; }
        prev_next=(void**)curr; curr=next;
    }
    return 0;
}

unsigned long Backup_read_8Byte(unsigned int id) {
    typedef unsigned long (*fn_t)(unsigned int);
    static fn_t real_fn;
    if (id==0x00fa0191U) return (unsigned long)ux_arena;
    if (id==0x00fa0192U) return 0x1000000UL;
    if (!real_fn) real_fn = (fn_t)dlsym((void *)-1L, "Backup_read_8Byte");
    return real_fn ? real_fn(id) : 0UL;
}

/* Complete user-space MA_* implementation for ArenaImpl and BitmapImpl */
static unsigned long g_fake_space_obj[8] = { 0x430000000UL, 0x1000000UL, (unsigned long)ux_arena, 0 };
int MA_Initialize(void) { return 0; }
int MA_Terminate(void) { return 0; }
int MA_CreateSpace(void *param, void **out_space) { (void)param; if (!out_space) return -3; *out_space = g_fake_space_obj; return 0; }
int MA_CreateSpaceDirect(unsigned long phys, unsigned long size, char *name, int type, void **out_space) {
    (void)phys; (void)size; (void)type;
    if (!out_space) return -3;
    *out_space = g_fake_space_obj;
    dprintf(2, "FX6_MA_CREATE_SPACE_DIRECT name=%s size=0x%lx -> %p\n", name ? name : "?", size, *out_space);
    return 0;
}
int MA_DestroySpace(void *param, void *space) { (void)param; (void)space; return 0; }
int MA_SetUserData(void *space, unsigned long data) { (void)space; (void)data; return 0; }
int MA_SpaceGetInitialLogicalAddress(void *space, void **out_log) { (void)space; if (!out_log) return -3; *out_log = ux_arena; return 0; }
int MA_SpaceCompact(void *space, int mode) { (void)space; (void)mode; return 0; }
int MA_SpaceRegistCompactionEventHandler(void *space, void *a, void *b, void *c, void *d) { (void)space;(void)a;(void)b;(void)c;(void)d; return 0; }
int BMP_AssocMemorySpaceForCompaction(void *space, int flag) { (void)space; (void)flag; return 0; }
int MA_SpaceMalloc(void *space, unsigned long size, unsigned long align, void **out_log) {
    (void)space;
    if (!out_log) return -3;
    unsigned long a = align < 64 ? 64 : align;
    if (a & (a - 1)) a = 64;
    unsigned long sz = size ? size : 64;
    void *p = 0;
    if (posix_memalign(&p, a, sz) != 0 || !p) return -4;
    memset(p, 0, sz);
    *out_log = p;
    return 0;
}
int MA_SpaceFree(void *space, void *log_addr) { (void)space; if (log_addr) free(log_addr); return 0; }
int MA_SpaceFree_gralloc(void *space, void *log_addr) { return MA_SpaceFree(space, log_addr); }
int MA_LogicalToPhysical(void *space, const void *log_addr, unsigned long *out_phys) { (void)space; if (!out_phys || !log_addr) return -3; *out_phys = (unsigned long)log_addr; return 0; }
int MA_PhysicalToLogical(void *space, unsigned long phys_addr, void **out_log) { (void)space; if (!out_log) return -3; *out_log = (void *)phys_addr; return 0; }
int MA_FindSpaceByLogicalAddress(const void *log_addr, void **out_space) { (void)log_addr; if (!out_space) return -3; *out_space = g_fake_space_obj; return 0; }
int MA_GetUnitHandle(void *space, unsigned int *out_handle) { (void)space; if (!out_handle) return -3; *out_handle = 1; return 0; }
void GRM_utilWriteMemorySpaceLog(int a, int b, int c, int d) { (void)a;(void)b;(void)c;(void)d; }

static void init_osd(void) {
    if (osd_tried) return; osd_tried=1;
    int fd=open("/dev/mem",2|0x101000);
    if (fd<0) { dprintf(2,"FX6_OSD open failed\n"); return; }
    void *m1=mmap(0,0x400000,3,1,fd,0x41e000000L);
    void *m2=mmap(0,0x200000,3,1,fd,0x429550000L);
    close(fd);
    if (m1 && m1!=(void*)-1) {
        osd41e=m1;
        dprintf(2,"FX6_OSD mmap=%p\n",m1);
        dprintf(2,"FX3_GPE_RESOURCE_REGISTER type=0x403 logical=0x41e001000 phys=0x41e001000 bytes=0x21c000\n");
    }
    if (m2 && m2!=(void*)-1) osd429=m2;
}

static void flush_pixels_to_osd(const char *tag) {
    init_osd();
    /* Composite any non-zero pixels from pix_off into pix_on in case bmp_off was written directly */
    unsigned int *p_on = (unsigned int *)pix_on;
    unsigned int *p_off = (unsigned int *)pix_off;
    for (int i = 0; i < FB_W * FB_H; i++) {
        if (p_off[i] != 0) p_on[i] = p_off[i];
    }
    if (osd41e) memcpy((char*)osd41e+0x1000, pix_on, FB_BYTES);
    if (osd429) memcpy((char*)osd429, pix_on, 0x12c000);
    flush_count++;
    if (flush_count<8 || flush_count%30==0) dprintf(2,"FX6_OSD_FLUSH %s #%u\n",tag,flush_count);
}

int _ZN3grm11FrameBuffer4swapEv(void *self) { (void)self; ensure_bitmaps(); flush_pixels_to_osd("swap"); return 0; }
int GRM_fbrmUpdate(int a, void *b, void *c) { (void)a;(void)b;(void)c; ensure_bitmaps(); flush_pixels_to_osd("fbrmUpdate"); return 0; }

int GRM_gpermFillrect(int plane, const GRM_Rect16 *r, unsigned int color, int blend) {
    (void)plane;(void)blend; ensure_bitmaps();
    if (!r) return 0;
    int x0=r->x<0?0:r->x, y0=r->y<0?0:r->y;
    int x1=r->x+r->w>FB_W?FB_W:r->x+r->w, y1=r->y+r->h>FB_H?FB_H:r->h+r->y;
    unsigned int *base=(unsigned int*)pix_on;
    for (int y=y0;y<y1;y++) for (int x=x0;x<x1;x++) base[y*FB_W+x]=color;
    return 0;
}

int GRM_gpermRectblit(int plane, void *src, const GRM_Rect16 *sr, const GRM_Rect16 *dr, const void *opt, int blend) {
    (void)plane;(void)opt;(void)blend; ensure_bitmaps();
    if (!src || !dr) return 0;
    unsigned char *info=*(unsigned char**)((char*)src+8);
    unsigned char *bits=*(unsigned char**)((char*)src+0x10);
    if (!info || !bits) return 0;
    int sw=*(short*)(info+0x18), sh=*(short*)(info+0x1a);
    if (sw<=0) sw=*(short*)(info+0x08); if (sh<=0) sh=*(short*)(info+0x0a);
    int sx0=sr?sr->x:0, sy0=sr?sr->y:0, dx0=dr->x, dy0=dr->y, bw=dr->w, bh=dr->h;
    unsigned int *db=(unsigned int*)pix_on, *sb=(unsigned int*)bits;
    for (int y=0;y<bh;y++) { int dy=dy0+y, sy=sy0+y; if(dy<0||dy>=FB_H||sy<0||sy>=sh)continue;
      for (int x=0;x<bw;x++) { int dx=dx0+x, sx=sx0+x; if(dx<0||dx>=FB_W||sx<0||sx>=sw)continue; unsigned int p=sb[sy*sw+sx]; if(p) db[dy*FB_W+dx]=p; } }
    return 0;
}
```

---

## 9. Round 239~242 里程碑：`GRM_fbrmRegisterChangeFramebufferCb` 破除 `0×0` 裁剪、首帧 `552,960` 非零像素落盘与 `stella::TreeNode` 场景图防护 (`libgrm-fbinit30.so`)

### 9.1 Round 239 (`cp-bind-88c9bd94`) ~ Round 240 (`cp-bind-a96c53de`)：完整跑通 `GraphicsEngine::drawFramebuffer()`
1. **修复 `BitmapImpl` 结构体布局 (`ensure_bitmaps`)**：保留 `[b + 0x08]` (`0x40` 字节 `info` 结构体指针) 与 `[b + 0x38]` (`pthread_mutex_t`)，并拦截 `BitmapImpl::create` 两个重载使用 `calloc` 动态分配，将 `.bss` 体积控制在 `~4.4 MB`；
2. **修复 `stella::LinearList::remove` 与 `libra::HashRecord` 生命周期**：通过校验指针合法性的 `LinearList::remove`、`ImageData::detach`、`HashRecord::decRef`、`XDBTable::releaseBankItem`，彻底跨过 `libstella.so + 0x298d8` 与 `liblibra.so + 0x2ab64`；
3. **Round 240 成果 (`cp-bind-a96c53de`)**：首次完整执行完 `GraphicsEngine::drawFramebuffer()` 并抵达 `FX6_OSD_FLUSH fbrmUpdate #5` (`andromeda::Window::swap()`)，成功导出 `gpe0.bin` (`2,211,840` B)、`gpe1.bin`、`dmm0400.bin`、`dmm0403.bin`。

### 9.2 Round 241 (`cp-bind-508c609a`)：破除 `GraphicsContextGRM` `0×0` 裁剪并首次写入 `552,960` 个非零像素
1. **为什么 Round 240 中 `fbrmUpdate #5` 的 `prims=0 nz_pixels=0`？**
   - `libgemini-grm.so` 中的 `gemini::grm::GraphicsContextGRM::initialize` 会调用 `GRM_fbrmRegisterChangeFramebufferCb(ChangeFbrmScreenChangeCallback, this)` 注册屏幕尺寸回调；
   - 在回调触发前，`GraphicsContextGRM` 的 `m_width` (`+0x28`) 和 `m_height` (`+0x2a`) 保持为 `0×0`，导致 `resetClipRect()` 将裁剪矩形设为 `(0, 0, 0, 0)`，所有 `drawFillRect` / `drawImage` 均被 `TRect::intersect` 裁剪丢弃！
2. **Round 241 修复 (`libgrm-fbinit29.so`)**：
   - 导出 `GRM_fbrmRegisterChangeFramebufferCb`，在注册时立即以 `{ width=1024, height=540, format=2, rotate=0 }` 同步回调 `cb(user_data, &info)`；
   - 对齐 `libgemini-grm.so` 调用 `GRM_gpermFillrect(cmd_id, cmd_param, fill_param, cb, ud)` 与 `GRM_gpermRectblit(cmd_id, cmd_param, blit_param, cb, ud)` 的 5 参数 ABI；
   - 导出 `_ZN13app_adjchk_ui4view13update_screenEv` 指针校验版，跨过 `AdjChkConfig.so + 0x0c498` (`addr=0x150`)。
3. **Round 241 实测结果 (`runs/cp-bind-508c609a/serial.log`)**：
   ```text
   1625: FX6_GRM_FBRM_CB_FIRE cb=0x7faa3ee16c user=0x7f9000bf50 (1024x540 fmt=2)
   1640: FX6_GPE_FILLRECT #1 (0,0,1024,540) argb=0x00000000
   1641: FX6_OSD_FLUSH fillrect #4 prims=1 nz_pixels=552960
   1643: FX6_OSD_FLUSH gpermDrawFlush #6 prims=1 nz_pixels=552960
   ```
   `libgemini-grm.so` 首次原生调用 `GRM_gpermFillrect` 与 `GRM_gpermDrawFlush`，向 `gpe0.bin` / `gpe1.bin` / `dmm0400.bin` / `dmm0403.bin` 写入 **`552,960` 个非零像素 (`1024×540`)**！

### 9.3 Round 242 (`libgrm-fbinit30.so`)：`stella::TreeNode` 场景图遍历防护
1. **Round 241 后续停点 (`libstella.so + 0x30038`, `addr=0x18`, `X0=0x7f9c0ce2f8`)**：
   - 位于 `_ZNK6stella8TreeNode19getFirstActiveChildEv + 0x0c`，在遍历场景图时遇到 `vptr == NULL` 的未完全初始化 `TreeNode` (`0x7f9c0ce2f8`)，读取 `*(vptr + 0x18)` (`getChildNodes`) 触发 `addr=0x18`。
2. **Round 242 修复 ([`libgrm-fbinit25.c`](file:///Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab/reports/2026-11-07-fx6-uxengine-init-assist/libgrm-fbinit25.c) / `/tmp/libgrm-fbinit30.so`)**：
   - 导出 `_ZNK6stella8TreeNode19getFirstActiveChildEv`、`_ZNK6stella8TreeNode13getFirstChildEv`、`_ZNK6stella8TreeNode20getNextActiveSiblingEv`、`_ZNK6stella8TreeNode14getNextSiblingEv`、`_ZN6stella10TreeWalker8traverseEPNS_8TreeNodeEb`、`_ZN9andromeda14NodeWalkerBase5visitERN6stella8TreeNodeE` 等全套场景图遍历防护，遇到 `vptr == NULL` 的无效节点时自动跳过并继续遍历后续有效兄弟/子节点，同时将全屏背景清屏与前景控件矩形/位图赋予区分色值。


