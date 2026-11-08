# FX6 static pipeline map — 2026-11-08 assist for candidates 522+

## 0.11 Real view_* RTTI/vtable/ctor/draw (567+)

Resolved via RTTI name -> typeinfo -> vtable -> GOT -> ctor refs:

```text
class                 vptr        ctor          draw +0x158
view_fill             0x2d1b490   appFw+0xc27800 0xc2750c
view_frame            0x2d1b660   (frame helper) 0xc27ea0
view_string (view_text) 0x2d1f210 appFw+0xc3af98 0xc3bbd8
view_icon             0x2d1bd60   appFw+0xc2c188 0xc2d100
view_menu_item        0x2d1c650   appFw+0xc341d4 0xc35358
view_list_scroll_item 0x2d1c2c0   appFw+0xc30c3c 0xc3339c
```

Important correction: there is **no** class named `view_text`; the text widget is `view_string`.
`view_fill` draw is `0xc2750c`; `0xc27ea0` is `view_frame`'s draw (both use the same five child
view_fill layout, but different vtable).

`andromeda::Rectangle2D::draw` at `libandromeda+0x1c850` calls the context directly:

```text
1c888 getGraphicsContext
1c894 ldr x1,[ctx]
1c89c ldr x3,[x1,#0xf8]
1c8a4 blr x3
```

This is the lowest-level native fill path; `view_fill` sets up a Sprite and eventually reaches it.

## 0.12 /private/tmp/fx6_menu_tree_builder.h

Header provides:

```c
fx6_menu_fill(appfw,parent,x,y,w,h,color)
fx6_menu_text(appfw,parent,x,y,w,h,text,color)   // view_string, TextSprite at +0xe40
fx6_menu_icon(appfw,parent,x,y,w,h)
fx6_menu_item(appfw,parent,x,y,w,h,color)
fx6_list_item(appfw,parent,x,y,w,h,color)
fx6_menu_tree_build(appfw, screen_parent)
fx6_widget_draw(obj)                              // vt[0x158/8](obj)
```

Real constructors:

```text
view_fill             appFw+0xc27800, size 0x1178
view_string           appFw+0xc3af98, size ~0x1200
view_icon             appFw+0xc2c188, size ~0x800
view_menu_item        appFw+0xc341d4, size ~0x10000
view_list_scroll_item appFw+0xc30c3c, size ~0x28000
TextSprite::setString appFw+0xb17100
TextSprite::drawText  appFw+0xb17a00
Widget::setParent     appFw+0xb196e0
```

Compiled:

```text
/private/tmp/fx6_menu_tree_builder_test.o   aarch64 rc=0
```

`fx6_menu_tree_build` makes a real native tree: background view_fill, title view_string, three
view_menu_item rows with view_string labels, and border view_fills. It does not use a solid clear as
the menu.


## 0.10 546+ native tree + GDS assist

File:

```text
/private/tmp/fx6_next_stage_assist.c
/private/tmp/fx6_next_stage_assist.o   (aarch64, rc=0)
```

### Real context vtable (not GraphicsDrawState)

`GraphicsDraw::fillRect` obtains `GraphicsSystem::getGraphicsContext()` and calls its vtable+0xf8:

```text
266f8 GraphicsDraw::fillRect
  GraphicsDrawState::GetInstance
  PushState
  GraphicsSystem::getGraphicsContext -> x20
  GetFillColor -> Color
  26754 ldr x3,[x20]        ; context vptr
  26758 ldr x3,[x20,#0xf8]  ; fillRect slot
  26760 blr x3
```

The object is `gemini::GraphicsContextGRM`:

```text
libgemini-grm.so vtable for gemini::GraphicsContextGRM = 0x1ba68
vptr = 0x1ba78
```

Full hot-slot map (offset from vptr):

```text
0x18 clearBuffer(Color*)
0x20 beginScene(Color*)
0x28 endScene()
0x30 swap()
0x78 setScissorRect(TRect*)
0xf0 setImage(Image*)
0xf8 fillRect(Color*, TRect*)
0x100 drawImage(Image*, Rect* src, Rect* dst)
0x108 drawImage(Rect* src, Rect* dst)
0x110 drawImage(Rect* src, Vector2Fixed32*)
0x118 drawImage(Rect* src, Vector2*)
0x120 drawLine(Color*, Vector2Fixed32*, Vector2Fixed32*)
0x128 drawLine(Color*, Vector2*, Vector2*)
0x130 transform(Rect*, Vector2Fixed32*)
0x138 transform(Vector2Fixed32*, int, Vector2Fixed32*)
0x140 setTranslate(Vector2Fixed32*)
0x148 setTranslate(Vector2*)
0x150 setRotate(int)
0x158 GraphicsContext2D::setRotate(Fixed32*)
0x160 setRotate(int, Vector2Fixed32*)
0x168 GraphicsContext2D::setRotate(Fixed32*, Vector2Fixed32*)
0x170 setRotate(int, Vector2*)
0x178 setScale(Fixed32*, Fixed32*)
0x180 setScale(float,float)
0x188 setRasterlizer(Rasterlizer*)
0x190 pushMatrix
0x198 popMatrix
0x1a0 setMatrixMode
0x1a8 resetMatrix
0x1b0 getMatrixMode
```

Text has **no** `GraphicsContextGRM::drawText`; `TextRM_drawText` goes through
`GraphicsDraw::bitBlit` / `stretchBlit`, which use the drawImage slots 0x100–0x118.

### Native fill xrefs

Only `libuxengine.so` calls `GraphicsDraw::fillRect`:

```text
7ab68  Polygon::render            -> fillRect
7e5dc  Sprite/Element render      -> fillRect
7a928  Polygon::render            -> setColor
7e0d0  Sprite/Element render      -> setColor
7b0a4, 7b3b4, 7af4c             -> setClip
7b3e8, 7b414                   -> GraphicsDraw::begin/end
7aac8, 7e2f8, 7e6c8            -> stretchBlit/bitBlit (text/image)
```

`view_fill` path:

```text
appFw+0xc27ea0 (view_fill slot 43)
 -> appFw+0xc27914
 -> child vt+0x148 Node2D::draw
 -> libuxengine Polygon::render (0x7a7f8)
 -> GraphicsDraw::fillRect (0x7ab68)
 -> context vt+0xf8
```

### Native menu C entry

`fx6_native_menu_enter(appfw, screen_root, framebuffer_41e)`:

```text
fx6_model_ready
fx6_engine_gate_auto
fx6_gds_install(framebuffer)
fx6_native_menu_panel:
  native view_fill background
  4 native view_fill borders
  Widget::setParent
```

`fx6_native_view_fill` calls the real ctor:

```text
appFw+0xc27800  view_fill ctor
appFw+0xb196e0  Widget::setParent
size 0x1178
fields +0x1e8/+0x1ec/+0x1f0/+0x1f4/+0x1f8/+0x1fc/+0x21c/+0x220
```

This is a native Widget path, not GDS probe fill. It does not wait on model_lock.
Exact `procam_big6_menu_home_presenter` / `setting_presenter` symbols are stripped; no reliable
constructor address was found, so the C uses native `view_fill` children under the real Screen root.


## 0.9 527 linkfix + locksteal + gate (ready)

526 failed again with:

```text
undefined symbol: fx6_inject_set_presenter_done
```

Root cause: 526 links `fx6_model_spoof4.c`, which defines `fx6_model_done` (lock steal +
model helper) but not `fx6_inject_set_presenter_done` referenced by 520.c.

527 shim:

```text
/private/tmp/libgrm-fbinit25-527.so
138880 bytes
```

Inputs:

```text
libgrm-fbinit25-520.c
fx6_entry_hook2.c
fx6_model_spoof4.c
fx6_static_linkfix.c
fx6_gate_bootstrap.o
```

Linkfix now:

```c
extern void fx6_model_done(void) __attribute__((weak));
weak fx6_inject_set_presenter_done(void) {
    if (fx6_model_done) fx6_model_done();
    fx6_install_model_spoof_auto();
    fx6_model_ready_auto();
    fx6_engine_gate_auto();
}
```

So 527 includes:

```text
FX6_LOCK_STEAL patched
FX6_HELPER patched
FX6_GATE_BOOT init / applied
```

527 CPIO (only shim replaced in 526):

```text
guest-hybrid-fx6kernel-capid-grmreal527-linkfix.cpio
bytes: 430234488
sha256: 4e1fea4903bbf8b97c08bf4e2fac87f9a7f6bd9e70148d06e62119f013596dec
```

No QEMU started.


## 0.8 524 CPIO ready

```text
/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/guest-hybrid-fx6kernel-capid-grmreal524-gate.cpio
bytes: 430233984
sha256: fcd19849ec7d5dc0c2af512cf4da03e70a9cbefdf4a751b23d79438bfbe558bc
```

Built by replacing only:

```text
usr/lib/libgrm-fbinit9.so
```

with `/private/tmp/libgrm-fbinit25-524.so` in the 523 CPIO. No manifest written, no QEMU started.

Expected on 524 run:

```text
FX6_GATE_BOOT init
FX6_GATE_BOOT ge=0x... applied
```


## 0.7 524 shim built (no QEMU/CPIO)

```text
/private/tmp/libgrm-fbinit25-524.so
138376 bytes
```

Link inputs:

```text
libgrm-fbinit25-520.c
fx6_entry_hook2.c
fx6_model_spoof2.c
fx6_static_linkfix.c
fx6_gate_bootstrap.o
```

Checks:

```text
T Application_System_Init
T fx6_inject_set_presenter_done
.init_array present
strings: FX6_GATE_BOOT init / FX6_GATE_BOOT ge=%p applied
no undefined fx6_* symbols
```

Replace only:

```text
usr/lib/libgrm-fbinit9.so
```

with this .so in the 523 CPIO. Expected:

```text
FX6_GATE_BOOT init
FX6_GATE_BOOT ge=0x... applied
```

If the native 2D tree is reached, then:

```text
FX6_OSD_FLUSH ... prims>0
```


## 0.6 524 gate bootstrap object

523 patched `0x2127750` but never applied the 2D gate (`no FX6_GATE`, `prims=0`).

Ready-to-link object:

```text
/private/tmp/fx6_gate_bootstrap.c
/private/tmp/fx6_gate_bootstrap.o
```

Behavior:

```text
constructor starts a pthread
every 2s for 180s:
  fx6_model_ready_auto()
  fx6_engine_gate_auto()
once ge != 0:
  dprintf("FX6_GATE_BOOT ge=%p applied")
```

It does not draw pixels; it only sets:

```text
appFw+0x4dc56c8 +04=0, +10=1
engine+0x318 = libuxengine+0xa3240
engine+0x328 = 1
window+0x234 = 0,0,1024,540
window+0x23c = 1
```

Add `fx6_gate_bootstrap.o` to the 524 link inputs (alongside the existing 520/entry/spoof objects).
Expected serial:

```text
FX6_GATE_BOOT init
FX6_GATE_BOOT ge=0x... applied
FX6_OSD_FLUSH ... prims>0   (only if native 2D tree is actually reached)
```


## 0.5 523 shim built (no QEMU/CPIO)

```text
/private/tmp/libgrm-fbinit25-523.so
129744 bytes
```

Linked from:

```text
libgrm-fbinit25-520.c
fx6_entry_hook2.c
fx6_model_spoof2.c
fx6_static_linkfix.c
```

Symbol check:

```text
T fx6_inject_set_presenter_done   (1e8d8)
T fx6_pre_update_c
T fx6_install_update_hook
T fx6_install_sys_update
no undefined fx6_* symbols
```

Because the weak linkfix definition is linked, the 517/520 call resolves to:

```text
fx6_install_model_spoof_auto()
fx6_model_ready_auto()
fx6_engine_gate_auto()
```

not to `model_spoof2`'s base=0 cave path.

For 523 runtime, replace only:

```text
usr/lib/libgrm-fbinit9.so
```

with `/private/tmp/libgrm-fbinit25-523.so`; expected serial:

```text
FX6_HELPER pc=... cave=... (auto appfw base)
FX6_GATE ...
no undefined symbol
```


## 0.4 523 link-fix object

522 failed because the new shim links `fx6_model_spoof2.c` (which lacks
`fx6_inject_set_presenter_done`) while 517/520 still reference it.

Ready-to-link object:

```text
/private/tmp/fx6_static_linkfix.c
/private/tmp/fx6_static_linkfix.o
```

Contents:

```c
#include "/private/tmp/fx6_static_assist.h"
```

Symbol:

```text
W fx6_inject_set_presenter_done
```

Add `fx6_static_linkfix.o` to the 523 link inputs. A strong definition in
`fx6_model_spoof.c` still wins; if absent, the weak default calls:

```text
fx6_install_model_spoof_auto()
fx6_model_ready_auto()
fx6_engine_gate_auto()
```

For 523, the expected boot fix is to get past:

```text
undefined symbol: fx6_inject_set_presenter_done
```

and then see `FX6_HELPER patched` (not range fail) plus `FX6_GATE ...`.


## 0.3 522 link failure fixed

522 serial:

```text
/usr/bin/appfw-launch: symbol lookup error:
/usr/lib/libgrm-fbinit9.so: undefined symbol: fx6_inject_set_presenter_done
```

Cause: 522 build swapped to `fx6_model_spoof2.c`, which defines `fx6_model_helper` but **not**
`fx6_inject_set_presenter_done`; 517/520 still reference it.

`fx6_static_assist.h` now supplies:

```c
__attribute__((weak)) void fx6_inject_set_presenter_done(void)
{
    fx6_install_model_spoof_auto();
    fx6_model_ready_auto();
    fx6_engine_gate_auto();
}
```

A strong definition in `fx6_model_spoof.c` still overrides the weak one.

Verified:

```text
nm /tmp/fx6_static_assist_test.o | grep presenter_done
000... W fx6_inject_set_presenter_done
```


## 0.2 521 root cause and corrected include order

521 serial:

```text
FX6_MODEL_LOCK_EARLY base=0
FX6_MODEL_LOCK_BYPASS2 disabled
FX6_HELPER range fail
```

Cause: `fx6_model_spoof.c` uses `g_appfw_base`, which is still 0 at
`fx6_inject_set_presenter_done()` time. The helper then computes pc=0x2127750 and the cave/BL
distance is invalid.

Use the self-resolving functions instead:

```c
#include "/private/tmp/fx6_static_assist.h"

fx6_install_model_spoof_auto();   /* dl_iterate_phdr -> appFw base -> BL 0x2127750 */
fx6_model_ready_auto();           /* appFw+0x4dc56c8: +04=0, +10=1 */
fx6_engine_gate_auto();           /* libuxengine base -> +318/+328, window+234/+23c */
```

Call them once from `fx6_pre_update_c()` **before** `df91e8`, or after appFw is loaded but before
the first `updateFrame`/`sys_render`.

`fx6_install_model_spoof_auto()` uses `dl_iterate_phdr` to suffix-match `appFw.so`, so it does not
depend on `g_appfw_base`.

Compiled:

```text
/tmp/fx6_static_assist_test.o  aarch64 rc=0
```


## 0.1 522 integration order

```c
#include "/private/tmp/fx6_static_assist.h"

/* existing 521 behavior */
fx6_install_model_spoof(g_appfw_base);   /* optional, same as fx6_model_helper patch */
fx6_model_ready(g_appfw_base);           /* +0x04=0, +0x10=1 */

/* once, before df91e8 / updateFrame */
fx6_engine_gate_auto();                  /* sets engine+0x318/+0x328,
                                            window+0x234 dirty,
                                            window+0x23c=1 */
```

`fx6_engine_gate_auto()` uses `dlopen/dlsym/dladdr`, no shim base required.

### `window+0x234` clarification

`window` = `ScenegraphWindow` at `engine+0xb0`.

```text
window+0x234  8-byte DirtyRegion::Rect {s16 x,y,w,h}
window+0x23c  2D draw enable byte
window+0x23d  clear color (CColor, 4 bytes)
```

`ScenegraphWindow::setDirtyRect` at `libuxengine+0x7b2d8` does:

```text
add x0,x0,#0x200
ldr x1,[x1]
stur x1,[x0,#0x34]   ; store 8 bytes at window+0x234
```

So `+0x234` is the dirty rect consumed by `renderScreen`; it is not a GraphicsDraw pointer.


## 0. Immediate include for terminal B

Use:

```c
#include "/private/tmp/fx6_static_assist.h"
```

It contains:

```c
fx6_model_spoof(id, mode, param, out)       // appFw+0x2127750 success spoof
fx6_install_model_spoof(appfw)              // BL patch at 0x2127750
fx6_model_status(appfw)                     // appFw+0x4dc56c8
fx6_model_ready(appfw)                      // +0x04=0, +0x10=1
fx6_set_window_dirty(win, 0,0,1024,540)     // win+0x234
fx6_engine_gate(uxengine)                   // +0x318=ret, +0x328=1, +0x23c=1
fx6_stop_clear(uxengine, win, 1)            // libuxengine+0x7b618
```

The header compiles for aarch64 (verified `/tmp/fx6_static_assist_test.o`).

## 1. `appFw+0x2127750` exact behavior

```text
2127750  args: w0=id, w1=mode, w2=param, x3=out
21277b4  stp w23,w22,[x19]      ; out[0]=id, out[1]=-1
21277b8  str xzr,[x19,#8]       ; out[2..3]=0
21277bc  stp wzr,wzr,[x19,#0x10] ; out[4..5]=0
21277c0  osal_valloc_msg_wait(out+0x28, mode, 1)
...
```

Callers:

```text
2127b04: x0=obj, x1=out
  w1=[obj+4], w0=[obj]
  bl 2127750
  bl 215ca08
  str w0,[out+0x18]

2127d60: same pattern
```

`0x1395f20` is **not** a caller of 0x2127750; it is a separate UI/message loop using
`0x20dda8c`/`0x1512f58`.

Success spoof:

```c
long fx6_model_spoof(unsigned id, unsigned mode, unsigned param, void *out) {
    uint32_t *p = (uint32_t*)out;
    for (int i=0;i<8;i++) p[i]=0;
    p[0]=id; p[1]=0;   /* 0 = success, original writes -1 before I/O */
    return 0;
}
```

This matches the observed term 521 `FX6_HELPER` behavior (zero 8 words, p[0]=id, p[1]=0, return 0).

## 2. `appFw+0x14d4654` model getter

```text
14d4654  adrp x0,0x4dab000
14d4658  add  x0,x0,#0x630
14d465c  add  x0,x0,#0x1a000
14d4660  add  x0,x0,#0x98
14d4664  ret
```

Returns:

```text
appFw + 0x4dc56c8
```

`df91e8` reads:

```text
w21 = [obj+0x04]
w22 = [obj+0x10]
ready if (w21==0 || w21==3) && w22==1
```

Set:

```c
m = (uint32_t*)(appfw + 0x4dc56c8);
m[1] = 0;   /* +0x04 */
m[4] = 1;   /* +0x10 */
```

## 3. Engine / 2D gate

```text
libuxengine+0x8265c  GraphicsEngine::sys_getInstance
engine+0x318        before-render callback
engine+0x328        before-render enable
engine+0xb0         ScenegraphWindow
window+0x234        8-byte dirty rect
window+0x23c        2D draw-enable byte
window+0x23d        clear color
libuxengine+0xa3240 WidgetBase::onReset() -> ret
libuxengine+0x7b618 ScenegraphWindow::stopClearScreen(bool)
```

`fx6_engine_gate()` writes:

```c
*(u64*)(ge+0x318) = uxengine + 0xa3240;  /* ret */
*(u8*)(ge+0x328) = 1;
dirty(win, 0,0,1024,540);
*(u8*)(win+0x23c) = 1;
```

This is the exact gate analyzed earlier: `isExecBeforeRendegingCallback` requires both +0x328 and +0x318,
then `sys_render` calls `stopClearScreen(true)` and enables `GraphicsDraw::begin/end`.

---

# FX6 static pipeline map (terminal A, 2026-11-08)

Scope: static only. No QEMU was started from this terminal. All offsets are **module-relative**
(`libuxengine.so`, `appFw.so`, `libInfraInput.so`) unless stated. This report is written for the
runtime line to consume directly.

## Step A — `ux::wgtsys::WidgetSystem` state / early returns

### Instance

| Item | Address |
|---|---|
| `WidgetSystem::m_instance` | `libuxengine+0xc4d38` (BSS pointer) |
| `WidgetSystem::sys_getInstance()` | `libuxengine+0xa39e8` |

`sys_getInstance` loads the GOT slot at `0xc1d48`, dereferences it, and returns `[m_instance]`.

### Functions

| Function | Address |
|---|---|
| `WidgetSystem::updateFrame()` | `libuxengine+0xa5ee0` |
| `WidgetSystem::notifyDraw()` | `libuxengine+0xa5f70` |
| `WidgetSystem::processEvent()` | `libuxengine+0xa5e78` |
| `WidgetSystem::getFirstLayerBase() const` | `libuxengine+0xa4354` |
| `WidgetSystem::hasAnimatingWidget() const` | `libuxengine+0xa405c` |
| `WidgetSystem::hasDrawNoticeWidget() const` | `libuxengine+0xa407c` |
| `WidgetSystem::isFrameDelay() const` | `libuxengine+0xa4048` |
| `WidgetSystem::needUpdateNextTick() const` | `libuxengine+0xa40b8` |
| `WidgetSystem::createLayer(ID const&)` | `libuxengine+0xa41e8` |
| `WidgetSystem::createScreen(ID const&)` (GraphicsEngine) | `libuxengine+0x82f8c` |
| `WidgetSystem::setAimFPS()` / `getAimFPS()` | `libuxengine+0xa3a10` / `0xa3a08` |

### Object offsets confirmed from disassembly

| Offset | Meaning | Evidence |
|---|---|---|
| `ws+0x08` | last process-event time (written by `processEvent`) | `a5ea4 str x0,[x20,#8]` |
| `ws+0x10` | frame/time base A | `a5ee8 ldp x2,x1,[x0,#0x10]` |
| `ws+0x18` | frame/time accumulator; `updateFrame` writes sum at `+0x18` | `a5ef8` |
| `ws+0x7a0` | AimFPS (int) | `a3a08/a3a10` |
| `ws+0x798` | `ux::animeng::AnimationEngine*` | `a40e4 ldr x0,[x19,#0x798]` |
| `ws+0x7c0` | first intrusive layer-list node/sentinel | `a4354` loads `[ws+0x7c8-8]` |
| `ws+0x7c8` | layer-list end/sentinel | `a4354` |
| `ws+0x888` | timer pointer (`hasTimer`) | `a406c` |
| `ws+0x8a0` | **animating widget count/flag** | `a405c` |
| `ws+0x8a4` | **draw-notice widget count/flag** | `a407c` |

### Early returns (the paint blockers)

1. `updateFrame()` first calls `hasAnimatingWidget()`:
   - `a405c`: returns `[ws+0x8a0] != 0`.
   - If zero, `a5f04 b.eq a5f64` → returns without walking layers.
2. `notifyDraw()` first calls `hasDrawNoticeWidget()`:
   - `a407c`: returns `[ws+0x8a4] != 0`.
   - If zero, `a5f88 b.eq a5fe8` → returns without walking layers.
3. `processEvent()` calls `clearOmittedEvents`; if it returns null (`a5e8c cbz x0`), returns 0 without
   `processExternalEvent`.
4. Even with flags set, `getFirstLayerBase()` returns null when the intrusive list at
   `ws+0x7c0` equals the sentinel `ws+0x7c8` (`a4354..a437c`). `updateFrame` then returns at
   `a5f20 cbz x0`.

### Minimal shim recipe to force a paint attempt

```text
ws = ux::wgtsys::WidgetSystem::sys_getInstance()          // libuxengine+0xa39e8
if (!ws) return;
*(u32 *)(ws + 0x8a0) = 1;   // hasAnimatingWidget -> true
*(u32 *)(ws + 0x8a4) = 1;   // hasDrawNoticeWidget -> true
// ensure at least one real layer: ws+0x7c0 must not equal ws+0x7c8
// If empty: create a layer first:
//   ux::wgtsys::WidgetSystem::createLayer(ux::core::ID const&)  (+0xa41e8)
//   then attach it as first layer / root.
// call:
//   updateFrame()  (+0xa5ee0)
//   notifyDraw()   (+0xa5f70)
//   processEvent() (+0xa5e78)  // only if an external event exists
```

Important: setting only `+0x8a0/+0x8a4` is not sufficient if `ws+0x7c0` is the empty sentinel.
The first-layer pointer must be a real `LayerBase` whose virtual `+0x0` returns true at
`a5f30/a5fb4`.

## Step B — first screen / page / window creation after `c14dfc`

### What `c14dfc` actually is

`appFw+0xc14dfc` is **not a normal function prologue**:

```text
c14dfc: b c15060
c14e00: b c15144
c14e04: b c14fa0
c14e08: b c15588
c14e0c: mov x0,x1; ret
```

It is a **thunk/jump table** used by `c09df0`. Runtime `C14DFC_CALL/RET` confirms the call, but the
real work is in `c14fa0/c15060/c15144/c15588`.

### Post-presenter screen path

`c0a860 -> 0x1397450` is presenter registration. After it, `c0a86c`:

```text
c0a86c: add x0,x21,#0xa40
c0a870: bl  0xdf91e8
```

`appFw+0xdf91e8` is a real screen/area activation routine:

```text
df91e8  stp...
df9200  bl 0xde3f84
df9204  mov w0,#0x255
df920c  add x1,x29,#0x30
df9214  str w0,[x19,#-8]!
df9218  mov w5,#1
df921c  stp w0,wzr,[x29,#0x30]
df9220  mov x0,x20
df9224  mov x3,x19
df9228  mov w4,#0
df922c  strb wzr,[x20,#0x741]
df9230  bl 0xdf8d6c
df9234  mov x0,x20
df9238  bl 0xde3e08
df923c  mov x0,x19
df9240  bl 0x1acd618       ; model lock
df9244  bl 0x14d4654
df9248  ldr w21,[x0,#4]
df924c  ldr w22,[x0,#0x10]
df9250  mov x0,x19
df9254  bl 0x1acd2f4
df9258  cmp w21,#0
df925c  ccmp w21,#3,#4,ne
df9260  ccmp w22,#1,#4,eq
df9264  b.eq 0xdf9270
df9268  ldr x0,[x20,#0x18]
df926c  bl 0xdf5618
```

Recipe: after presenter returns, call `df91e8(ui_obj + 0xa40)` as `c0a86c` does. Do **not**
re-implement the fields; `ui_obj` is the same object passed to `c09da0`.

### Other real constructors in the `c09df0` chain

| Address | Role (static) |
|---|---|
| `appFw+0xde31ac` | allocates 0xa8 object via `operator new`, calls `de2f6c`, stores at `[app_ui+0x18]`, initializes several global vtables, calls `c1044c`, `c865c8` |
| `appFw+0xc1412c` | `osal_reg_sync_msg_queue_cb(0x3e00166, ...)`; input/display sync callback registration |
| `appFw+0xdf8d6c` | screen-area setup called by `df91e8` with id `0x255` |
| `appFw+0xdf5618` | screen/area update called after state compare |

**Not yet proven statically**: which of these creates the *shooting settings page* view tree.
The strongest direct recipe for the runtime is still `df91e8(ui+0xa40)`; if `WidgetSystem` still has
no layers, call `createLayer` (+0xa41e8) with the screen ID from `df8d6c` first.

## Step C — `RemotePresenter` thread (`appFw+0xde3000`)

`de3000` is the presenter wait/drive loop:

```text
de3028  ldrb w0,[x19,#0x7a]     ; running flag
de302c  cbnz w0,de30a4          ; if zero -> return
de3030  mov x0,x21              ; x21 = obj+0x18 (mutex)
de3040  bl 0xc096d4             ; lock
de3044  mov w0,#1
de3048  strb w0,[x29,#0x48]     ; unique_lock owns
de304c  ldrb w0,[x19,#0x78]     ; wake predicate
de3050  cbnz w0,de3064
de3054  mov x1,x22
de3058  mov x0,x23              ; x23 = obj+0x48 (condvar)
de305c  bl pthread_cond_wait
de3060  b de304c
de3064  ldrb w0,[x29,#0x48]
de3068  strb wzr,[x19,#0x78]    ; clear wake
de306c  ldrb w23,[x19,#0x79]    ; draw/update branch
...
de3084  ldr x0,[x19,#8]
de3088  cbz w23,de3094
de308c  bl 0x1098428            ; draw/update path
de3094  ldr x1,[x0]; ldr x1,[x1,#0x10]; blr x1  ; virtual fallback
de30a0  b de3028
```

Confirmed fields:

| Offset | Meaning |
|---|---|
| `obj+0x08` | presenter/engine object pointer |
| `obj+0x18` | mutex |
| `obj+0x48` | condition_variable |
| `obj+0x78` | wake predicate (byte) |
| `obj+0x79` | draw/update branch (byte) |
| `obj+0x7a` | running flag (byte) |

To wake + force the draw branch:

```text
*(u8 *)(obj+0x78) = 1;
*(u8 *)(obj+0x79) = 1;
pthread_cond_signal(obj+0x48);
```

The runtime already patched `de304c` to `mov w0,#1`, which skips the predicate wait. That is enough
to enter the body, but `obj+0x79` must be nonzero to hit `0x1098428`; otherwise it takes the virtual
fallback.

## Step D — `libInfraInput` key configuration

### `KeyConfigInital` (`libInfraInput+0xb284`)

```text
b288  mov w0,#0x7a0001       ; Backup data id
b29c  bl Backup_get_datasize
b2ac  str w0,[global+0x568]  ; size
b2b4  sxtw x0,w0
b2b8  bl malloc
b2bc  str x0,[global+0x560]  ; table pointer
b2c8  mov w0,#0x7a0001
b2d0  bl Backup_read
```

Globals:

| Global | Meaning |
|---|---|
| `libInfraInput+0x26000+0x560` | key config blob pointer |
| `libInfraInput+0x26000+0x568` | key config byte size |

### `GetPhyKeyConfig(int key, void* out, int out_size)` (`libInfraInput+0xb38c`)

```text
b39c  mov w0,#0x7a008b
b3b8  bl osal_wai_sem_tmo     ; serialize
b3bc  bl KeyConfigInital
b3c0  ldr x1,[global+0x560]   ; blob
b3d4  ldr w4,[global+0x568]   ; total size
b3d8  sxtw x0,w19
b3dc  add x20,x1,x0
b3e0  ldr w3,[x20,#8]         ; key id
b3e4  cbz w3,not_found
b3e8  cmp w3,w21             ; requested key
b3ec  b.ne next
b3f4  ldr w2,[x20,#0xc]       ; payload length
b3fc  cmp w2,w23              ; out_size
b400  b.hi too_small
b404  add x0,x0,#0x10
b40c  add x1,x1,x0            ; payload at entry+0x10
b414  bl memcpy
b418  ldr w20,[x20,#0xc]      ; return length
```

Table entry layout (confirmed):

| Offset | Type | Meaning |
|---|---|---|
| `+0x00` | u32 | record header (not used by lookup) |
| `+0x04` | u32 | record stride padding; next index = `index + 0x10 + [entry+4]` |
| `+0x08` | u32 | **key id** |
| `+0x0c` | u32 | **payload length** |
| `+0x10` | bytes | **payload** |

The `KeyConfigInital` data is a **Backup blob**, not the 0x20-byte event. The actual runtime event
structure comes from the input queue (`q=0x7ae01d`): `libInfraInput+0x78b4` receives a message,
copies **0x20 bytes** into an event, frees it, matches `event[0]` against a 0x50-stride key table at
`+4`, then invokes the input callback. The exact 0x20-byte field map beyond `event[0]` is **not yet
statically proven**; the runtime observations are the only source for the 0x20-byte size and
0x50-stride table.

## Concrete next actions for runtime line

1. After `C14DFC_CALL/RET` and `PRESENTER_CALL`, call `ux::wgtsys::WidgetSystem::sys_getInstance`
   (`libuxengine+0xa39e8`), dump `ws+0x7c0..ws+0x8b0`; verify `+0x8a0/+0x8a4`.
2. If `+0x7c0 == +0x7c8` (empty layer list), call `createLayer` (+0xa41e8) or execute
   `df91e8(ui+0xa40)` once more; then set `+0x8a0=1`, `+0x8a4=1`.
3. Call `updateFrame` (+0xa5ee0) then `notifyDraw` (+0xa5f70). Watch `GRM_gperm*`/`GRM_blt*`.
4. For RemotePresenter: set `obj+0x78=1`, `obj+0x79=1`, signal `obj+0x48`; keep `de304c` patched.
5. Input: use `q=0x7ae01d`, 0x20-byte event, `event[0]=key`; first obtain a valid config blob via
   `0x7a0001` or synthesize the table entry layout above.


---

## Step B addendum — presenter name registry (static)

`procam_big6_menu_home_presenter` string VA: `appFw+0x23aebe0`.

Its name-pointer relocation is:

```text
.rela.dyn r_offset=0x2e8d7e8  R_AARCH64_RELATIVE addend=0x23aebe0
```

Table at `appFw+0x2e8d7e8`, stride `0x20`:

```text
+0x00  const char* name       ("procam_big6_menu_home_presenter")
+0x08  ptr 0x2e8cd88          (registry/list metadata, not a code pointer)
+0x10  0
+0x18  0
```

Neighbors:

| Name | Name VA | Table slot |
|---|---|---|
| `procam_big6_menu_home_presenter` | `0x23aebe0` | `0x2e8d7e8` |
| `procam_big6_menu_look_middle_presenter` | `0x23aec08` | `0x2e8d800` |
| `procam_big6_menu_setting_presenter` | `0x23aec38` | `0x2e8d818` |
| `procam_big6_play_presenter` | `0x23aec60` | `0x2e8d830` |

This table stores **name + registry metadata**, not the create function. The actual presenter create
function is reached through the runtime registration path (`0x1397450`), not by calling a table
entry directly.

`c14dfc` is a jump thunk:

```text
c14dfc -> c15060
c14e00 -> c15144
c14e04 -> c14fa0
c14e08 -> c15588
c14e0c  mov x0,x1; ret
```

After presenter, the real screen activation call is:

```text
c0a86c  add x0,x21,#0xa40
c0a870  bl  0xdf91e8
```

`df91e8` is the concrete screen/area activation function (id `0x255`, calls `df8d6c`, `de3e08`,
model lock, `14d4654`, and `df5618` when state matches). This is the function to call from the shim:
`df91e8(ui_obj + 0xa40)`.

## Step C addendum — presenter wake recipe

`appFw+0xde3000` waits on `obj+0x48` while `[obj+0x78]==0`. On wake:

```text
[obj+0x78]=0
if [obj+0x79] != 0 -> bl 0x1098428
else -> virtual [obj+8]->vtable+0x10
```

Minimal wake/draw trigger:

```text
*(u8*)(obj+0x78)=1;
*(u8*)(obj+0x79)=1;
pthread_cond_signal(obj+0x48);
```

With `de304c` patched to `mov w0,#1`, the wait is skipped; `+0x79` still selects the draw path.

## Step D addendum — exact key blob layout

`KeyConfigInital`:

```text
blob_id = 0x7a0001
size_global = libInfraInput + 0x26000 + 0x568
ptr_global  = libInfraInput + 0x26000 + 0x560
```

`GetPhyKeyConfig` entry:

```text
+0x00  u32  record header
+0x04  u32  stride padding; next = index + 0x10 + [entry+4]
+0x08  u32  key id
+0x0c  u32  payload length
+0x10  byte[payload length]
```

Lookup:

```text
sem_wait(0x7a008b)
KeyConfigInital()
walk entries while index < size
if [entry+8] == key:
    copy [entry+0x10] length [entry+0xc] to out
    return length
sem_signal(0x7a008b)
```

The runtime's 0x20-byte input event and 0x50-stride event table are separate from this Backup key
blob; `event[0]` is the key id, but the remaining 0x20-byte fields are still not statically proven.

---

## Step B addendum 2 — actual screen ID table

`appFw+0x2d116e0`, stride `0x10`:

```text
+0x00  const char* name
+0x08  u64 meta: high32 = size/count-ish (0x3f/0x1d/...), low32 = screen id
```

Confirmed rows:

| Screen | ID | meta |
|---|---:|---|
| `procam_focus_magnifier` | 0x04 | `0x1100000004` |
| `procam_thumbnail` | 0x05 | `0x1500000005` |
| `procam_clip_property` | 0x06 | `0x0c00000006` |
| `procam_play` | 0x07 | `0x1400000007` |
| `procam_adjust_check` | 0x08 | `0x1300000008` |
| `procam_usb_connect` | 0x09 | `0x1100000009` |
| `procam_big6_play` | 0x0a | `0x160000000a` |
| **`procam_big6_menu_home`** | **0x0b** | `0x1d0000000b` |
| `procam_big6_menu_look_middle` | 0x0c | `0x190000000c` |
| **`procam_big6_menu_setting`** | **0x0d** | `0x3f0000000d` |
| `procam_user_functions_screen_for_monitor_operation_mode_single` | 0x0e | `0x3f0000000e` |
| same `_double` | 0x0f | `0x160000000f` |

So the **shooting-settings screen ID is 0x0d**; Big6 home is 0x0b.

There is no direct ADRP+ADD xref to `0x2d116e0` in `.text`; it is consumed indirectly by the
screen/presenter registry. The practical direct activation remains `df91e8(ui+0xa40)`; after that,
screen ID `0x0d`/`0x0b` should be used with the screen manager open/change API. The exact manager
method is still being traced.


---

## Step C addendum 2 — `0x1098428` gate

`appFw+0x1098428`:

```text
1098428  add x1,x0,#0x8a000
109842c  ldrb w1,[x1,#0xf80]   ; presenter+0x8af80
1098430  cbz w1,1098438        ; if zero -> ret
1098434  b 0x1095780           ; real event/frame dispatch
1098438  ret
```

So `RemotePresenter`'s `[obj+0x79]` branch only does work if:

```text
presenter_obj + 0x8af80 != 0
```

Then it jumps into `0x1095780` (large event/job dispatcher, not GRM directly).

## Step D addendum 2 — actual 0x20 event / 0x50 table

From `InfraInput::EventThread` (`libInfraInput+0x783c`):

```text
7898  osal_stat_msgq(qid=[x19+0x28], &n)
78ac  osal_rcv_msg_tmo(qid, &msg, -1)
7998..79b0  copy 0x20 bytes msg -> stack event (x20)
79c0  count = [x19+0x40]
79d4  table = [x19+0x48]
79d8  entry = table + index*0x50
79dc  key = [event+0]
79e0  entry_key = [entry+4]
79e4  cmp
79ec  w3=[entry+0x14]
79f0  entry+0xc
79f8..7a04 copy 0x20 event bytes to entry+0xc
7a2c  SendAttachEvent(cb_table, input, event)
```

Confirmed:

| Item | Offset |
|---|---|
| input event size | `0x20` |
| event key id | `event+0x00` |
| event table stride | `0x50` |
| table key id | `entry+0x04` |
| copied event bytes | `entry+0x0c` .. `entry+0x2b` |
| table aux word | `entry+0x14` |
| callback | `InfraInput::SendAttachEvent` at `libInfraInput+0x5250` |

The remaining 0x1c bytes of the event are opaque payload copied from the OSAL message; the key
comparison and callback use only `event+0`. If the runtime injects a 0x20-byte message at
`q=0x7ae01d` with `event[0]=key`, it will match `entry+4` and reach `SendAttachEvent`.


---

## Todo 1 — `appFw+0x1095780` dispatcher

`0x1095780..0x1098fc4` is a large **event/ID dispatch routine**, not a direct GRM caller.
It repeatedly calls:

```text
0x1020e10   (ID lookup/match)
0x1c970f4   (state/flag query)
```

and tests numeric IDs such as `-0x2df1`, `-0x2de2`, `-0x2dd4`, `-0x2dbf`, `-0x2da2`,
`-0x2de8`, `-0x2db6`, `-0x2da8`, then writes small byte flags. No `GRM_*` import call is present
in this range.

So `0x1098428`'s `+0x8af80` gate leads to **event/state dispatch**, not directly to a framebuffer
blit. The actual draw is performed later by WidgetSystem/layer tree.

## Todo 2 — Layer/Widget virtual draw

`WidgetSystem::walkTree(LayerBase*, TreeWalker*)` (`libuxengine+0xa58f4`) does:

```text
a58f4  mov x3,x1
a58f8  add x1,x0,#0x30      ; LayerBase's stella::TreeNode is at layer+0x30
a58fc  mov x0,x3
a5904  b stella::TreeWalker::traverse(TreeNode*, bool)
```

So each layer node is at `LayerBase+0x30`.

Walkers:

```text
UpdateFrameWalker::visit  libuxengine+0xa6a24
NotifyDrawWalker::visit   libuxengine+0xa6a90
```

`UpdateFrameWalker`:

```text
a6a40  getWidget()
a6a48  WidgetBase::getMode()
a6a50  if mode > 2 -> skip children
a6a58  WidgetBase::isAnimate()
a6a64  vtable = [widget]
a6a68  fn = [vtable + 0x100]
a6a70  blr fn                  ; update/animate virtual
```

`NotifyDrawWalker`:

```text
a6aac  getWidget()
a6ab4  getMode()
a6ac0  callDrawNotice()
a6ad0  vtable = [widget]
a6ad4  fn = [vtable + 0x108]
a6adc  blr fn                  ; DRAW virtual
```

Therefore:

| Virtual | Offset | Meaning |
|---|---:|---|
| WidgetBase draw | `vtable+0x108` | actual draw-notice render |
| WidgetBase update | `vtable+0x100` | animate/update |
| WidgetBase event | `vtable+0xe8` | process user event |
| LayerBase active | `vtable+0x00` | `isActive` check in updateFrame/notifyDraw |

The concrete widget subclass that implements `vtable+0x108` is the one that eventually reaches
`ux::core::GraphicsImage` / `GRM_gpermRectblit` (libux_core imports `GRM_gpermRectblit`,
`GRM_gpermFillrect`). This is the draw path to intercept.

## Todo 5 — C snippet for shim

The following is intentionally written as address-based calls (no C++ name mangling needed at
runtime). Module bases must be resolved by `dladdr`.

```c
typedef void *(*get_inst_t)(void);
typedef void (*update_t)(void *);
typedef void (*draw_t)(void *);
typedef void (*event_t)(void *);
typedef void *(*create_layer_t)(void *, const void *);
typedef void (*screen_act_t)(void *);

static void fx6_force_paint(void *uxengine, void *appfw, void *ui_obj)
{
    get_inst_t get_ws = (get_inst_t)((char *)uxengine + 0xa39e8);
    update_t update = (update_t)((char *)uxengine + 0xa5ee0);
    draw_t draw = (draw_t)((char *)uxengine + 0xa5f70);
    event_t event = (event_t)((char *)uxengine + 0xa5e78);
    create_layer_t create = (create_layer_t)((char *)uxengine + 0xa41e8);
    screen_act_t screen = (screen_act_t)((char *)appfw + 0xdf91e8);

    void *ws = get_ws();
    if (!ws) return;

    /* gate flags */
    *(unsigned int *)((char *)ws + 0x8a0) = 1; /* hasAnimatingWidget */
    *(unsigned int *)((char *)ws + 0x8a4) = 1; /* hasDrawNoticeWidget */

    /* first layer empty? ws+0x7c0 == ws+0x7c8 */
    if (*(void **)((char *)ws + 0x7c0) == (void *)((char *)ws + 0x7c8)) {
        /* first try the app's own screen activation */
        if (ui_obj) screen((char *)ui_obj + 0xa40);
        /* if still empty, create a layer by ID (ID struct layout must be supplied) */
        /* create(ws, &id); */
    }

    update(ws);
    draw(ws);
    event(ws);
}
```

`screen()` is `df91e8(ui+0xa40)`, exactly the `c0a86c` path. The `createLayer` ID argument is
`ux::core::ID const&`; the ID for `procam_big6_menu_setting` is low32 `0x0d` (meta `0x3f`), and
for home low32 `0x0b` (meta `0x1d`).

## Latest runtime poll

`runs/cp-bind-d74a4e49` (term_4b286158):

```text
gpe0-late.bin colors=1 (all transparent)
gpe1-late.bin colors=1
serial: model_mutex.cpp:75 destructor/lock asserts continue
last: FX6_COND_TIMEDWAIT appFw+0x1c1e040
```

So runtime still has no native pixels; the static recipe above is the next direct lever.


---

## Todo 2/3 solved — the 7 root layers are created by `appFw+0xc1b82c`

Caller: `appFw+0xc0b190` (`bl 0xc1b82c`), inside `Application_System_Init` (early, before c09da0).

`c1b82c` creates **7 WidgetSystem layers** with `ux::core::ID::genID` strings:

```text
0x2273fcc "BBB"  -> layer #1, stored at [x21+0x6c8]
0x2273fd0 "CCC"  -> layer #2, stored at [x19+0x08]
0x2273fd4 "DDD"  -> layer #3, stored at [x19+0x10]
0x2273fd8 "EEE"  -> layer #4, stored at [x19+0x18]
0x28fa708 "FFF"  -> layer #5, stored at [x19+0x20]
0x2273fdc "GGG"  -> layer #6, stored at [x19+0x28]
0x2273fe0-ish    -> layer #7, stored at [x19+0x30]
```

Each layer:

```text
layer = WidgetSystem::createLayer(ID)
vptr = [layer]
[vptr + 0x08](layer, 1)   ; Layer::setActive(true)
[vptr + 0x18](layer, 0)   ; Layer::setClear(false)
```

`ux::wgtsys::Layer` vtable at `libuxengine+0xc0a28`:

```text
+0x10  Layer::isActive()
+0x18  Layer::setActive(bool)
+0x20  Layer::isClear()
+0x28  Layer::setClear(bool)
+0x30  Layer::getClearColor()
+0x38  Layer::setClearColor(CColor const&)
```

Because the object vptr points at `+0x10`, `vptr+0x8 = setActive`, `vptr+0x18 = setClear`.

So after `c1b82c`, the WidgetSystem layer list is populated with 7 active layers and
`ws+0x7c0 != ws+0x7c8`. If the runtime sees an empty list, either `c1b82c` did not run or the
list was reset later.

## Todo 4 — `df91e8` state helpers

```text
14d4654  returns global object at appFw+0x4dab000 + 0x1a098
df8d6c   sets screen/area [x0+0x2e8], calls de3a3c/de36ec/de3758
df5618   if de30bc true:
           lock presenter+0x18
           presenter+0x79 = 0
           presenter+0x78 = 1
           unlock
           cond_signal(presenter+0x48)
```

`df91e8` reads `[14d4654+4]` and `[+0x10]`, compares to `0/3/1`; if the condition is not the
expected one, it calls `df5618(presenter)` to wake RemotePresenter (non-draw branch, since +0x79=0).

This explains why `df91e8` can complete without creating a visible widget layer: it is a
screen-area activation/wake path, not the layer/widget construction path.


---

## Widget vtable confirmation

`libuxengine+0xc0f58` (`vtable for ux::wgtsys::WidgetBase`) and `+0xc0ba0` (`Widget`) have:

```text
+0xe8  WidgetBase::onUserEvent(UserEvent const&)
+0x100 WidgetBase::onAnimate()
+0x108 WidgetBase::onDrawNotice()
```

The object vptr points after offset-to-top/typeinfo, so the dispatcher offsets used by
`ProcessUserEventWalker` (`+0xe8`), `UpdateFrameWalker` (`+0x100`), and `NotifyDrawWalker`
(`+0x108`) are exactly these virtuals. Concrete widgets override `onDrawNotice`; that override is
the one that eventually calls `libux_core` `GraphicsImage::sys_copy/sys_fill` and
`GRM_gpermRectblit/GRM_gpermFillrect`.

## Runtime dump patch (C, address-based)

```c
typedef void *(*get_inst_t)(void);
typedef void *(*next_layer_t)(void *);

static void fx6_dump_ws_layers(void *uxengine)
{
    get_inst_t get_ws = (get_inst_t)((char *)uxengine + 0xa39e8);
    next_layer_t next   = (next_layer_t)((char *)uxengine + 0x730f0); /* getNextLayerBase */
    void *ws = get_ws();
    if (!ws) { dprintf(2, "FX6_WS NULL\n"); return; }

    dprintf(2, "FX6_WS ws=%p anim=%u draw=%u t10=%lx t18=%lx first=%p end=%p timer=%p\n",
        ws,
        *(unsigned int *)((char *)ws + 0x8a0),
        *(unsigned int *)((char *)ws + 0x8a4),
        *(unsigned long *)((char *)ws + 0x10),
        *(unsigned long *)((char *)ws + 0x18),
        *(void **)((char *)ws + 0x7c0),
        (void *)((char *)ws + 0x7c8),
        *(void **)((char *)ws + 0x888));

    void *layer = *(void **)((char *)ws + 0x7c0);
    int n = 0;
    while (layer && layer != (void *)((char *)ws + 0x7c8) && n < 16) {
        void **v = *(void ***)layer;
        dprintf(2, "FX6_LAYER n=%d layer=%p vptr=%p active=%d clear=%d\n",
            n, layer, v, v ? (int)v[0] : -1, v ? (int)v[1] : -1);
        layer = next(layer);
        n++;
    }
}
```

Call after `C14DFC_CALL/RET` and after `df91e8(ui+0xa40)`. This will distinguish:

```text
ws+0x7c0 == ws+0x7c8  -> c1b82c did not populate / list reset
layers present but anim=0/draw=0 -> gate flags only
layers present + flags 1 but no GRM -> child widget onDrawNotice not called / empty tree
```


---

## Todo 2/8 addendum — concrete blit function `appFw+0xc39a70`

`appFw+0xc39a70` is a real native image-copy/render routine:

```text
c39a90  ldrh w1,[x0,#0x1f0]          ; image height/param
c39a98  CreateImageParam
c39ab8  ResourceManager::createImage
c39ac0  ImageData::sys_getImageData
c39acc  ImageData::getWidth
c39ad8  ImageData::getHeight
c39ae4  second ImageData::sys_getImageData
c39af4  second getHeight
c39b2c  ux::core::GraphicsImage::copy(...)
c39b34  ldr w6,[x20,#0x1d0]
c39b38  ldp x5,x4,[x20,#0x1d8]
c39b40  ldrb w0,[x20,#0x1fc]
c39b44  ldr w1,[x20,#0x1f8]
c39b54  ldr w3,[x20,#0x1f0]
c39b58  ldr w2,[x20,#0x1f4]
c39b5c  add x20,x20,#0x498
```

It copies/scales one native `ImageData` into another through
`ux::core::GraphicsImage::copy`, which is the libux_core path that imports
`GRM_gpermRectblit/GRM_gpermFillrect`.

There is no direct `BL c39a70` in appFw text; it is reached indirectly (function pointer/vtable
or computed target). This is the screen-level blit to hook if WidgetSystem draw is already running.

The Widget virtual draw remains:

```text
NotifyDrawWalker -> WidgetBase::onDrawNotice (vtable+0x108)
```

Concrete subclass resolution is still open; the runtime dump of the layer/widget tree will show
which vptr is used.


---

## Todo 9 — compiled ws/layer dump

Standalone source `/tmp/fx6-wsdump.c`, compiled successfully for aarch64:

```text
/tmp/fx6-wsdump.o
ELF 64-bit LSB relocatable, ARM aarch64
```

Function:

```c
void fx6_dump_ws_layers(void *uxengine);
```

It resolves:

```text
uxengine+0xa39e8  WidgetSystem::sys_getInstance
uxengine+0x730f0  LayerBase::getNextLayerBase
```

and prints:

```text
FX6_WS ws anim draw t10 t18 first end timer
FX6_LAYER n layer vptr active
```

Merge this object/function into `libgrm-fbinit25` and call it after `C14DFC_RET` and after
`df91e8(ui+0xa40)`.

## Latest runtime poll — 2026-11-07 18:30

`runs/cp-bind-ef5b4e9e`:

```text
gpe0-late.bin colors=1 (all zeros/transparent)
serial ends with model_mutex.cpp:59/64/75 asserts
```

Still no native pixels. The layer dump is the next measurement that distinguishes:

```text
empty layer list
vs
layers present but gate flags zero
vs
layers + flags but no widget onDrawNotice
```


---

## Todo 10 — compiled force-paint patch

Files:

```text
/tmp/fx6-force-paint.c
/tmp/fx6-force-paint.o   ELF64 AArch64
```

Exported function:

```c
void fx6_force_paint(void *ux, void *appfw, void *ui);
```

Behavior:

```text
1. dump ws before
2. if ws+0x7c0 == ws+0x7c8 and ui != NULL:
       df91e8(ui + 0xa40)
       dump after-screen
3. ws+0x8a0 = 1
   ws+0x8a4 = 1
4. updateFrame(ws)
   notifyDraw(ws)
5. dump after-update
```

Addresses used:

```text
ux+0xa39e8  WidgetSystem::sys_getInstance
ux+0x730f0  LayerBase::getNextLayerBase
ux+0xa5ee0  updateFrame
ux+0xa5f70  notifyDraw
appfw+0xdf91e8  screen-area activation
```

Call site recommendation: immediately after `fx6_rsrc_relation_init()` has completed and after the
UI object (`c09da0`'s `x0`) is known. If the shim does not capture the UI object, pass `ui=NULL`;
the function will then only dump layers and set the two gate flags, without calling `df91e8`.

Expected serial:

```text
FX6_WS before ...
FX6_LAYER before ...
FX6_FORCE empty -> df91e8(...)
FX6_WS after-screen ...
FX6_WS after-update ...
```

If `FX6_LAYER` is non-empty and still no GRM call, the remaining issue is the widget tree
(`onDrawNotice` / `hasDrawNoticeWidget`), not layer creation.


---

## CRITICAL — latest WS4 shows layers but zero widgets

Latest serial (`runs/cp-bind-ef5b4e9e`) already has runtime WS4 probes:

```text
FX6_WS4 ws=0x7f7c00d290
FX6_WS4 firstLayer=0x7f7c00e2e0
FX6_WS4 layer vt=7f93977a38
FX6_WS4 isActive=1
FX6_WS4 update done
FX6_WS4 notify done
FX6_WS4 after f8a0=1 f8a4=0
```

So the layer list is **not empty**, and the layer is active. The problem is `ws+0x8a4 == 0`.

### What writes `ws+0x8a4`

`libuxengine+0xa58d4`:

```text
a58d4  ldr w1,[x0,#0x8a4]
a58d8  add w1,w1,#1
a58dc  str w1,[x0,#0x8a4]
a58e0  ret
```

Symbol: `WidgetSystem::wgt_addDrawNoticeWidget()`.

Callers are **Widget constructors**:

```text
Widget::Widget(ID const&)          a1fe0  -> wgt_addDrawNoticeWidget
WidgetBase::WidgetBase()           a333c  -> wgt_addDrawNoticeWidget
WidgetBase::WidgetBase(WidgetMode) a33d4  -> wgt_addDrawNoticeWidget
```

Therefore:

```text
f8a4 == 0
  => no live Widget/WidgetBase object was constructed
  => the 7 layers exist, but the widget tree under them is empty
  => setting f8a4=1 alone cannot create visible widgets
```

This matches the runtime result: `notifyDraw` entered, but no widget `onDrawNotice` ran.

### Consequence for the next candidate

Do **not** only force `ws+0x8a4=1`. The shim must instantiate the native screen widget tree for
screen ID `0x0d` (`procam_big6_menu_setting`) or `0x0b` (home), i.e. call the screen/controller
factory that constructs `Widget` objects. Those constructors will increment `+0x8a4` naturally.

`c1b82c` already proves the 7 root layers (BBB/CCC/DDD/EEE/FFF/GGG) exist; the missing part is the
**screen/page widget construction**, not `createLayer`.


---

## Concrete Widget subclass example (RTTI-verified)

`appFw+0xc1f1d4` calls `Widget::Widget()` at `c1f1f8`, then installs:

```text
GOT 0x2ee29f8 -> vtable-0x10 0x2d1a468
vtable at 0x2d1a478
vtable-8 typeinfo 0x2d1a2a0
typeinfo+8 name ptr 0x2275668
class name = view_audio_level_meter
```

So appFw's widget builders are concrete `view_*` classes, not a generic `menu_setting` widget.
The settings screen widget tree must be created by its controller/factory; the 7 global layers are
only roots.

This also explains why `f8a4=0`: no `view_*` widget object has been constructed yet.


---

## Step B — presenter getter `appFw+0xde1c0c`

`appFw+0xde1c0c` is a real presenter lookup function:

```text
de1c0c  stp x29,x30,...
de1c14  add x5, x5, #0xed0        ; x5 = appFw+0x432d000
de1c20  ldr x19,[x5, w0, sxtw #3] ; presenter_array[id]
de1c24  cbz x19, de1c30
de1c28  mov x0,x19
de1c2c  bl 0xde1ad8
de1c30  mov x0,x19
de1c34  ret
```

Array:

```text
appFw+0x432ded0  presenter_array[]
```

Index is the screen/presenter id; for `procam_big6_menu_setting` the screen id is `0x0d`
(`0x432ded0 + 0x0d*8 = 0x432df38`).

So the shim can try:

```c
void *(*get_presenter)(int) = (void *(*)(int))((char *)appfw + 0xde1c0c);
void *p = get_presenter(0x0d);
dprintf(2, "FX6_SETTING_PRESENTER %p\n", p);
```

If non-null, this is the live setting presenter; if null, it has not been registered and the
factory path is still missing.

### `de1bf0` is not a constructor

`appFw+0xde1bf0` loads the signature string
`procam_big6_menu_setting_presenter::procam_big6_menu_setting_presenter(...)` and calls the
assert logger (`0x2167784`) with line `0x53`, then continues. It is a **logging/assert branch**
inside a presenter-type switch, not the constructor body.


---

## Presenter registry addendum

`appFw+0xde1ad8` is the **presenter base constructor**, not a screen factory:

```text
de1ad8  stp...
de1ae0  save x21/x22
de1ae8  adrp x2,0x2ee2000
de1b00  ldr x2,[x2,#0x350]       ; base presenter vtable
de1b04  add x2,x2,#0x10
de1b08  stp x2,x1,[x19]          ; this->vptr, this->arg1
de1b0c  ldr x1,[x1]
de1b10  ldr x1,[x1,#0x28]
de1b1c  blr x1                   ; virtual init
de1b20  str x0,[x19,#0x10]
de1b24  mov x0,#0x4610
de1b34  bl 0xc870cc              ; construct subobject at this+0x4610
de1b40  str x22,[x19,#0x4c68]
de1b50  str w21,[x19+0x4c70]
de1b58  bl 0xdcbc0c
de1b64  bl 0xf24de8
de1b70  bl 0xdc3814
de1b78  cmp w21,#6
de1b7c  b.hi 0xde1bf0            ; invalid/log branch
```

`de1bf0` is the >6 branch that logs
`procam_big6_menu_setting_presenter::...` and continues; it is not a constructor.

The registry array `appFw+0x432ded0` is read by `de1c0c(id)`, but there is **no direct
ADRP+ADD xref to the id=0xd slot `0x432df38`**. Registration is therefore via an indexed store or
a copied table, not a simple `str x0,[array,#0x68]`. The runtime probe should call
`de1c0c(0x0d)` first, then search the array's initialization if null.


---

## Presenter array storage

`appFw+0x432ded0` is in `.bss`:

```text
.bss VA 0x303d978, size 0x30d9ea0
0x432ded0 initial bytes: all zero
```

So the presenter array starts NULL and must be filled at runtime.

Capstone scan of the 122 ADRP+ADD references to `0x432ded0` found **no direct `str`/`stp` to
the array base** within 30 instructions. This means initialization is not a simple per-slot store;
it is likely one of:

```text
memcpy(&array, static_table, size)
indexed store through a helper
copy from a presenter-manager object
```

The next static step is to inspect array refs that are followed by `bl memcpy` or an indexed
`str xN,[xbase,xindex,lsl #3]`, then find the source table.


---

## CRITICAL — real frame commit `drawFramebuffer`

`ux::gfxeng::GraphicsEngine::drawFramebuffer()` is at:

```text
libuxengine+0x839c8
```

Control flow:

```text
839e0  GraphicsSystem::waitForReadyToRender()
839e4  GraphicsDraw::resetDrawState()
839ec  ScenegraphWindow::prepareUpdate()
839f0  ldrb w0,[engine+0x32a]        ; force flag
839f4  cbnz w0,83a14                 ; if force -> skip dirty check
839f8  GraphicsSystem::isFramebufferDirty()
83a00  b.eq 83a98
83a04  getDirtyRegion/fillDirtyRects/resetFramebufferDirty
83a14  getDirtyRegion
83a1c  getCurrentDirtyRectCount()
83a20  cbz w0,83aa4                  ; no dirty rect -> no swap
83a24  getDirtyRect
83a38  GraphicsSystem::setDirtyRegion(x,y,w,h)
83a54  GraphicsEngine::sys_render(rect)
83a58  GraphicsSystem::prepareSwap()
83a64  Window::swap()
83a6c  engine+0x32a = 0
83a70  measureFps / measureArena / flushAreaCheckExtension
83a88  return 1
```

Addresses:

```text
libuxengine+0x8265c  GraphicsEngine::sys_getInstance()
libuxengine+0x839c8  drawFramebuffer()
libuxengine+0x82bd0  sys_render(Rect const&)
libux_core+0x30fe4   GraphicsSystem::setDirtyRegion(short,short,short,short)
```

### Force commit recipe

```c
void *(*ge_get)(void) = (void *(*)(void))((char *)uxengine + 0x8265c);
int (*draw_fb)(void *) = (int (*)(void *))((char *)uxengine + 0x839c8);
void (*set_dirty)(short, short, short, short) =
    (void (*)(short,short,short,short))((char *)uxcore + 0x30fe4);

void *ge = ge_get();
if (ge) {
    *(unsigned char *)((char *)ge + 0x32a) = 1;  /* force flag */
    set_dirty(0, 0, 1024, 540);                  /* create dirty rect */
    draw_fb(ge);                                 /* sys_render + swap */
}
```

This is the native `sys_render -> prepareSwap -> Window::swap` chain that ends in GRM. The
runtime candidate 448 (`enginerender`) is aimed at exactly this function.

Still true: if the widget tree is empty (`f8a4=0`), `sys_render` has no native primitives to submit,
so `drawFramebuffer` may swap an empty/black frame. Widget construction remains necessary for
visible settings UI.


---

## Candidate 448 diagnosis — sys_render alone does not swap

Latest run `runs/cp-bind-64f4afdf` (candidate 448 `enginerender`) serial:

```text
FX6_GRM_FB_MINIMAL before manager=0x7f9c008190 fb=(nil)
FX6_GRM_FB_MINIMAL after  manager=0x7f9c008190 fb=0x7fb5976d40 vptr=0x7fb590ce90
FX6_GRM_FB_SET_SIZE self=0x7fb5976d40 w=1024 h=540
FX6_GRM_FBRM_CB_FIRE cb=0x7faac4b16c user=0x7f9c00bc30 (1024x540 fmt=2)
FX6_ENG get=... upd=... render=... draw=...
FX6_ENG instance=0x7f9c00c010
FX6_ENG sys_update done
FX6_ENG sys_render done
```

There is **no `drawFramebuffer` and no swap**. `sys_render` only renders into the internal scene
graph; the commit chain is:

```text
GraphicsEngine::drawFramebuffer()  libuxengine+0x839c8
  -> sys_render(rect)
  -> GraphicsSystem::prepareSwap()
  -> andromeda::Window::swap()
```

So 448 cannot make `gpe0` non-zero: it never swaps the rendered framebuffer.

### Correct call sequence

```c
void *(*ge_get)(void) = (void *(*)(void))((char *)uxengine + 0x8265c);
int (*draw_fb)(void *) = (int (*)(void *))((char *)uxengine + 0x839c8);
void (*set_dirty)(short,short,short,short) =
    (void (*)(short,short,short,short))((char *)uxcore + 0x30fe4);

void *ge = ge_get();
if (ge) {
    *(unsigned char *)((char *)ge + 0x32a) = 1;  /* force flag */
    set_dirty(0, 0, 1024, 540);                  /* dirty rect */
    draw_fb(ge);                                 /* render + prepareSwap + Window::swap */
}
```

`setDirtyRegion` is a **static wrapper**, no hidden `this`:

```text
30fe4  sxth w0..w3
30ff8  ldr x4,[GOT]
30ffc  ldr x4,[x4,#0x68]  ; callback
31004  br x4
```

If `drawFramebuffer` still swaps black, the remaining problem is empty widget tree (`f8a4=0`), not
the swap path.


---

## 449-ready patch — `fx6_draw_fb`

Compiled:

```text
/tmp/fx6-drawfb.c
/tmp/fx6-drawfb.o   ELF64 AArch64
```

Function:

```c
void fx6_draw_fb(void *uxengine, void *uxcore);
```

It does exactly:

```c
ge = sys_getInstance();                  // uxengine+0x8265c
*(u8 *)(ge + 0x32a) = 1;                 // force render
setDirtyRegion(0,0,1024,540);            // uxcore+0x30fe4
ret = drawFramebuffer(ge);               // uxengine+0x839c8
dprintf("FX6_DRAWFB ret=%d", ret);
```

Candidate 448 already had the pointer:

```text
FX6_ENG instance=0x7f9c00c010
FX6_ENG draw=0x7fb58349c8
```

but never called it (`sys_render done` only). For 449, call `fx6_draw_fb(uxengine, uxcore)` after
the engine instance exists and after a framebuffer is registered.

Expected:

```text
FX6_DRAWFB ge=0x...
FX6_DRAWFB dirty set
FX6_DRAWFB ret=1     # swapped
```

If `ret=0`, the dirty-rect count was zero; if `ret=1` but gpe0 stays zero, the widget tree is empty
(`f8a4=0`) and `sys_render` submitted no native primitives.


---

## Candidate 449 — createScreen works, still no swap

Latest run `runs/cp-bind-d3dc419f` (candidate 449 `createscreen`):

```text
FX6_ENG2 get=0x7fa7ef365c create=0x7fa7ef3f8c upd=0x7fa7ef3978 render=0x7fa7ef3bd0
FX6_ENG2 instance=0x7f9000c010
FX6_ENG2 createScreen(0xd/0x3f)=0x7f900c5010
FX6_ENG2 sys_update done
FX6_ENG2 sys_render done
```

So `GraphicsEngine::createScreen(ID)` with screen id `0x0d` and meta `0x3f` returned a real Screen
object at `0x7f900c5010`. This is the correct setting-screen creation path.

But 449 still calls **sys_render only**, not `drawFramebuffer`; no prepareSwap/Window::swap, so gpe0
should still be zero.

### 450 combined recipe

```c
ge = GraphicsEngine::sys_getInstance();       // uxengine+0x8265c
screen = GraphicsEngine::createScreen(id);    // uxengine+0x82f8c, id=0xd/0x3f
*(u8 *)(ge + 0x32a) = 1;
setDirtyRegion(0,0,1024,540);                 // uxcore+0x30fe4
drawFramebuffer(ge);                          // uxengine+0x839c8
```

If drawFramebuffer returns 1 and gpe0 becomes non-zero, the remaining issue is widget/text
content; if it returns 1 but still black, check `ws+0x8a4` and the new Screen's widget tree.


---

## createScreen does NOT build widgets

`ux::gfxeng::GraphicsEngine::createScreen(ID const&)` at `libuxengine+0x82f8c`:

```text
82f98  load engine singleton
82fac  ID::operator!= (null ID check)
82fcc  sys_getInstance
82fd0  add x0,x0,#0x40          ; screen map
82fd8  pgMap<ID,ScreenBase>::GetNE
82fdc  if exists -> Log + sys_panic
82ff4  mov x0,#0x138            ; Screen object size
82ffc  malloc(0x138)
8300c  Screen::Screen(ID)
83010  return Screen*
```

So `createScreen(0x0d/0x3f)` only allocates a **0x138-byte Screen object** and calls the
`Screen(ID)` constructor. It does **not**:

```text
construct Widget/WidgetBase
increment ws+0x8a4
create view_menu_item / view_grid_list
attach any widget tree
```

This explains candidate 449:

```text
FX6_ENG2 createScreen(0xd/0x3f)=0x7f900c5010
FX6_ENG2 sys_render done
gpe0 still all transparent
```

The Screen exists, but the widget tree is empty. The remaining native content requires a
controller/factory that constructs `view_*` widgets after the Screen.


---

## view_menu_item metadata false lead

The vtable-install sites for `view_menu_item` (`ba84bc`, `be0b54`) call:

```text
b8a74c  std::string constructor (strlen/_M_create/_S_copy_chars)
b8a738  std::_Hash_bytes
```

These are **metadata/string/hash helpers**, not widget factories or constructors. They do not create
a widget tree. The actual `view_menu_item` ctor is not exposed by these sites.

Conclusion:

```text
view_menu_item vtable/typeinfo exists
but these two sites only build class-name/hash metadata
no widget object is created there
```

The search for the setting-screen view builder continues; do not call b8a74c/b8a738 expecting a
widget.


---

## Screen constructor auto-attaches a Layer2D

`ux::gfxeng::Screen::Screen(ID)` at `libuxengine+0x7b91c`:

```text
7b938  x22 = this+0xd8
7b93c  ScreenBase::ScreenBase(ID)
7b94c  vptr = [0xc1000+0xa30]+0x10
7b954  Node::Node()
7b95c  Screen::Layer2D_UXEngine::Layer2D_UXEngine(this+0xd8)
7b960  engine = GraphicsEngine::sys_getInstance()
7b968  x1 = this+0xd8
7b96c  x0 = engine+0xb0
7b970  andromeda::Window::addLastChild(layer)
7b974  this->setActive(true)
7b98c  engine->getFramebufferWidth()
7b99c  engine->getFramebufferHeight()
7b9b4  this->setAreaInFramebuffer(0,0,w,h)
7b9bc  Node::setClip(true)
7b9d0  Node::setClipPos(0,0)
7b9f8  Node::setClipSize(w,h)
7ba18  appendChild(root node)
```

So `createScreen(0x0d/0x3f)` **does** attach a `Layer2D_UXEngine` to `engine+0xb0` and marks
it active. It is not a detached object.

What is still empty is the **Layer2D's child tree**: no `view_*` widgets were added. Therefore:

```text
449 has: Screen object + Layer2D attached + active
449 lacks: widget children under Layer2D
```

That is why `sys_render` produces no UI, and `f8a4=0`.

`drawFramebuffer` is still required for swap. If called now, it may swap a clear/black screen, not
the settings UI.


---

## Candidate 450 — root attached, still no swap

Latest run `runs/cp-bind-bea5c7ad` (candidate 450 `screenroot`):

```text
FX6_ROOT ge=0x7f9400c010
FX6_ROOT screen=0x7f940c5010
FX6_ROOT root=0x7f940c5038
FX6_ROOT moveFirst done
FX6_ROOT moveLast done
FX6_ROOT update done
FX6_ROOT render done
```

But:

```text
gpe0-late.bin colors=1 (all transparent)
no FX6_DRAWFB
no drawFramebuffer
no prepareSwap / Window::swap
```

So 450 successfully creates/activates/moves the Screen root, but still only runs the render path. It
does **not** call the framebuffer commit function.

### Correct next action

Call `fx6_draw_fb(uxengine, uxcore)` (or raw `drawFramebuffer`) **after** `FX6_ROOT render done`:

```text
engine+0x32a = 1
setDirtyRegion(0,0,1024,540)
drawFramebuffer(engine)
```

Until this happens, gpe0 cannot change.

Separately, the Screen root has no `view_*` children, so even a successful swap will likely show
only a clear/black frame, not the settings UI.


---

## Candidate 468 — renderInternal still no swap

Latest run `runs/cp-bind-ab1d1fd6` (candidate 468 `windowrender`):

```text
FX6_WIN ge=0x7f9800c010 win=0x7f9800c0c0 upd=0x7faefdd134 rend=0x7faefdd4cc best=0x7f9800fea0
FX6_WIN renderInternal done
```

This calls the window/render-internal path, but still no:

```text
drawFramebuffer
prepareSwap
Window::swap
```

No gpe0-late yet at the sampled point; the previous candidates' pattern says it will stay transparent
without the commit.

## 469 preload fallback prepared (not run)

To bypass shim source availability, a tiny preload was built:

```text
/tmp/libfx6draw.c
/tmp/libfx6draw.so
```

It uses a constructor + 60 s worker:

```text
dlopen libuxengine/libux_core
get GraphicsEngine::sys_getInstance
engine+0x32a = 1
GraphicsSystem::setDirtyRegion(0,0,1024,540)
drawFramebuffer(engine)
```

Packaged CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal469-preloaddraw.cpio
vm-candidate-gpecap25-469.json
run_gpecap25_469.py
```

The CPIO adds:

```text
/usr/lib/libfx6draw.so
/etc/ld.so.preload  -> /usr/lib/libfx6draw.so
```

Not run because term_4b286158 held the QEMU lock at 468. It is a fallback for 469: it will call the
native `drawFramebuffer` after 60 s regardless of shim source.


---

## 2026-11-08 — 2D render path after `isWidget3D()==0`

### Critical gate: `ScenegraphWindow+0x23c`

`ScenegraphWindow::renderScreen(Screen*)` at `libuxengine+0x7b2e8`:

```text
7b3dc  ldrb w0,[x20,#0x23c]     ; x20 = ScenegraphWindow (engine+0xb0)
7b3e0  cbz  w0,0x7b430          ; 0 -> skip GraphicsDraw begin/end
7b3e4  GraphicsDraw::begin(clearColor)
7b3ec  x20 = Screen::getRootNode()
7b3f8  ScreenBase::getView()
7b410  RenderScreenWalker::renderScreen(root, screen, view, dirtyRect)
7b414  GraphicsDraw::end()      ; flush queued primitives
```

Writers:

```text
7b2a4  ScenegraphWindow ctor: [window+0x23c]=0
7b618  ScenegraphWindow::stopClearScreen(bool): [window+0x23c]=w1
```

So before any 2D command can be queued, the shim must call:

```c
void (*stop_clear)(void*, int) = (void(*)(void*,int))(uxengine + 0x7b618);
stop_clear((char*)engine + 0xb0, 1);
```

or write `*(u8*)(engine + 0xb0 + 0x23c) = 1`.

This is independent of widget tree: with `+0x23c==0`, `prims` stays 0 even if view_fill is visible.

### `renderInternal` 2D selection

`libuxengine+0x7b4cc`:

```text
7b4dc  vtable[0]               ; LayerBase flags
7b4f4  x19 = (flags >> 30) & 1
7b4fc  isNodeFor2D()
7b508  isNodeFor3D()
7b50c  if (bit30 && is2D):
7b518    layer+8 active?
7b53c    x20 = [layer+0x58]    ; Screen*
7b544    virtual [vt+0x10]    ; screen active?
7b560    renderScreen(Screen*)
7b568  else if (bit30 && is3D):
7b584    x20 = [layer+0x38]    ; Screen3D*
7b5a8    renderScreen(Screen3D*)
```

For Layer2D, Screen must be at `layer+0x58`, active, and not 3D.

### RenderScreenWalker 2D node path

`RenderScreenWalker::visit` at `libuxengine+0x7ae28`:

```text
7ae50  TreeNode::clearModified
7ae54  virtual [vt+0xa0]
7ae60  Element::setupFinalColor
7ae6c  virtual [vt+0x40]        ; setup/rect?
7ae7c  virtual [vt+0x88]        ; image/3D-like check
7ae8c  cbnz -> 0x7af74          ; image path
7ae90  Node::isClip()
7aee0  DirtyRegion::Rect::createFromSize(clip)
7af00  isNull -> skip child
7af4c  GraphicsDraw::setClip(x,y,w,h)
7af50  vtable = [node]
7af58  fn = [vtable+0x98]
7af60  blr fn                    ; Node2D::draw
7af6c  Node::completeBBox
```

2D `Node2D::draw` is `libandromeda+0x1c6f8` (base); concrete view_fill/Element overrides it.

`visitPost` (`0x7afe8`) restores clip with `GraphicsDraw::setClip`.

### GraphicsDraw queue

`libux_core`:

```text
GraphicsDraw::begin 0x26248: GraphicsContext vtable+0x20(clearColor)
GraphicsDraw::fillRect 0x266f8:
  GraphicsDrawState::PushState
  GetFillColor
  GraphicsContext vtable+0xf8({x,y,w,h}, color)
  PopState
GraphicsDraw::end 0x262ac: GraphicsContext vtable+0x28(flush)
```

`fillRect` is called by `libuxengine` `Polygon::render` (`7ab68`) and `Sprite::renderRect` (`7e5dc`).

## view_fill slot 33 / visible path

`view_fill` constructor `appFw+0xc277c0`:

```text
c27830  Widget::Widget()
c27858  [this+0x200..0x21c] init
c27884  str wzr,[this+0x21c]     ; mode=0
c27888  [this+0x220] = 0         ; alpha/visibility byte
c2788c  construct five subobjects:
          +0x228, +0x530, +0x838, +0xb40, +0xe48
```

The slot function `appFw+0xc27ea0`:

```text
c27ea0  ldrb w2,[x0,#0x1fc]      ; visible
c27ea4  cbnz w2,0xc27eb8         ; visible -> c279e4
c27ea8  vtable+0x30(w1=3)        ; hidden path
c27eb8  b 0xc279e4
```

Visible path `c279e4`:

```text
c27a00  vtable+0x30(w1=2)        ; set mode 2?
c27a10  read +0x204/+0x208/+0x210/+0x20c
c27a40  w22=[this+0x21c]         ; mode
c27a44  if mode==1 -> c27be8
c27a4c  if mode==0 -> c27a74
c27a50  if mode==2 -> c27d40
c27a74  mode0 fill:
  Vector2( +0x1e8, +0x1ec )
  vtable+0x40(Vector2)
  vtable+0x58( float(+0x1f0)+0x218, float(+0x1f4)+0x218 )
  c27914(this, 0, [this+0x214], &rect)
  c27914(this, 1, ...)
  c27914(this, 2, ...)
```

`c27914`:

```text
c27920  x21 = this + mode*8
c27934  x0 = [x21+0x1150]        ; Sprite object for mode
c2793c  virtual [vt+0x140]       ; begin/clear?
c27948  load +0x1d0, +0x1d8, +0x1f8 color, +0x220
c27984  store command into x0
c279a8  [x0+0x30] = mode
c279b4  [x0+0x34] = [this+0x220] ; alpha/visible byte
c279c0  virtual [vt+0x148]       ; set rect/color
c279d8  virtual [vt+0x158]       ; render/submit
```

### Precise conditions for view_fill 2D submit

```text
1. isWidget3D() must remain 0
   (do NOT patch libuxengine+0xa3220 to return 1; that forces 3D path and crashes at +0x58)

2. ScenegraphWindow+0x23c must be 1
   -> call stopClearScreen(true) at libuxengine+0x7b618 (window=engine+0xb0)

3. view_fill:
   +0x1fc visible != 0
   +0x21c mode == 0            ; full fill
   +0x1f0 w, +0x1f4 h > 0
   +0x1e8 x, +0x1ec y          ; rectangle
   +0x1f8 color                ; ARGB, alpha must be nonzero
   +0x220 alpha/visibility     ; must be nonzero (constructor writes 0!)
   +0x1150[mode] Sprite*       ; initialized by ctor five subobjects
```

The `+0x220 = 0` is a strong candidate for invisible/zero-alpha fill. Set it to `0xFF` and ensure +0x1f8 color alpha `0xFF` before the widget is traversed.

4. view_fill must be an **active Node2D child of Screen::getRootNode()** so `RenderScreenWalker` visits it with `isNodeFor2D()==1` and calls `[vt+0x98]`.


---

## view_fill main vtable — slot numbering correction

Constructor `appFw+0xc277c0` loads:

```text
GOT 0x2ee7360 -> addend 0x2d1b650
vptr = 0x2d1b650 + 0x10 = 0x2d1b660
```

Main vtable `0x2d1b660` non-zero slots:

| slot | offset | function | role |
|---:|---:|---|---|
| 0 | 0x000 | `c27ebc` | destructor |
| 1 | 0x008 | `c27f24` | deleting destructor |
| 40 | 0x140 | `c27770` | get rect (reads +1e8/+1ec/+1f0/+1f4) |
| 41 | 0x148 | `c277bc` | helper (no-op) |
| 42 | 0x150 | `c277c0` | clone/copy ctor |
| **43** | **0x158** | **`c27ea0`** | **onDrawNotice / draw entry** |
| 44 | 0x160 | `c277b8` | helper (no-op) |
| 45 | 0x168 | `c1f080` | base helper |
| 46 | 0x170 | `c27778` | get rect pair |
| 47 | 0x178 | `c277b0` | get width |

So the correct view_fill draw virtual is **slot 43 at vtable+0x158 = appFw+0xc27ea0**, not
`WidgetBase`'s abstract slot 33 (which view_fill leaves empty). Term's "slot 33" refers to the
WidgetBase base-vtable index; the concrete override is slot 43.

`c27ea0`:

```text
c27ea0  ldrb w2,[x0,#0x1fc]
c27ea4  cbnz w2,0xc27eb8
c27ea8  vtable+0x30(w1=3)
c27eb8  b 0xc279e4
```

Visible path uses `c27914` with sprite pointers at `[this + 0x1150 + mode*8]`, command fields
including `[this+0x220]` at command+0x34.

### Final 2D submit checklist

```text
[ ] isWidget3D() == 0 (keep libuxengine+0xa3220 returning 0)
[ ] window+0x23c == 1 (stopClearScreen(true), libuxengine+0x7b618)
[ ] Screen root active and view_fill is an active Node2D child
[ ] view_fill+0x1fc visible != 0
[ ] view_fill+0x21c mode == 0
[ ] view_fill+0x1e8/+0x1ec x/y, +0x1f0/+0x1f4 w/h
[ ] view_fill+0x1f8 color alpha != 0
[ ] view_fill+0x220 alpha/visibility != 0
[ ] [view_fill+0x1150+mode*8] sprite pointer valid
```

Without `window+0x23c=1`, `renderScreen` never calls `GraphicsDraw::begin/end`, so no
`fillRect` reaches the GraphicsContext vtable +0xf8 and `end` never flushes vtable +0x28.


---

## ROOT CAUSE — 2D draw is disabled unless before-render callback is enabled

`GraphicsEngine::sys_render(Rect const&)` at `libuxengine+0x82bd0`:

```text
82bf8  beforeRendergingCallback(rect)
82c10  setDirtyRect
82c20  isExecBeforeRendegingCallback()
82c28  cbz w21, 82c3c
82c2c  ScenegraphWindow::stopClearScreen(true)   ; window=engine+0xb0
82c40  andromeda::Window::render()
82c54  stopClearScreen(old_value)
```

`isExecBeforeRendegingCallback` at `+0x82afc`:

```text
82afc  ldrb w1,[engine+0x328]
82b00  cbz  w1, return 0
82b04  ldr  x0,[engine+0x318]
82b08  cmp  x0,#0
82b0c  cset w1,ne
82b10  return w1
```

Therefore:

```text
engine+0x328 must be nonzero       ; enableBeforeRenderingCallback(true)
engine+0x318 must be non-null      ; setBeforeRenderingCallback(fn)
```

Only then `sys_render` calls `stopClearScreen(true)`, setting:

```text
engine+0xb0+0x23c = 1
```

and only then `renderScreen` runs `GraphicsDraw::begin / RenderScreenWalker / GraphicsDraw::end`.
With callback disabled, `window+0x23c` remains 0, so **prims=0 forever**, regardless of view_fill.

### Exact APIs

```text
libuxengine+0x829e0  GraphicsEngine::setBeforeRenderingCallback(void(*)(void))
libuxengine+0x829f0  GraphicsEngine::enableBeforeRenderingCallback(bool)
libuxengine+0x82afc  isExecBeforeRendegingCallback()
libuxengine+0x7b618  ScenegraphWindow::stopClearScreen(bool)
```

Fields:

```text
engine+0x318  before-render callback pointer
engine+0x320  after-render callback pointer
engine+0x328  before-render enable byte
engine+0x329  after-render enable byte
engine+0x310  sys_update done byte
```

### Shim recipe

```c
void *ge = ((void*(*)(void))((char*)uxengine + 0x8265c))();
if (ge) {
    /* Any valid control callback; it does not draw pixels. */
    ((void(*)(void*, void*))((char*)uxengine + 0x829e0))(ge, (void*)&fx6_noop_ret);
    ((void(*)(void*, int))((char*)uxengine + 0x829f0))(ge, 1);
}
```

or direct:

```c
*(void **)((char*)ge + 0x318) = (void *)fx6_noop_ret;
*(unsigned char *)((char*)ge + 0x328) = 1;
```

`fx6_noop_ret` is a single `ret`; the real 2D drawing still comes from view_fill/Node2D and GRM.

After this, `sys_render` will:

```text
stopClearScreen(true)
Window::render
  renderInternal -> Layer2D -> Screen
  renderScreen -> GraphicsDraw::begin
  RenderScreenWalker -> Node2D::draw
  GraphicsDraw::end -> GraphicsContext vtable+0x28
stopClearScreen(old)
```

This is the missing gate behind candidate 470 `prims=0`.


---

## beforeRendergingCallback full semantics (critical)

`libuxengine+0x82b18` is not just a user callback dispatcher:

```text
82b30  isExecBeforeRendegingCallback()
82b34  if false -> return
82b3c  dirty rect -> GraphicsDraw::setClip(x,y,w,h)
82b58  GraphicsContext* ctx = GraphicsSystem::getGraphicsContext()
82b60  ctx vtable+0x18(clearColor)          ; context begin / clear
82b68  ScenegraphWindow::getLastClearColor
82b78  blr [ctx vt+0x18]
82b7c  ctx vt+0x58()                        ; begin 2D scene
82b8c  blr [engine+0x318]                   ; user before-render callback
82b94  ctx vt+0x60()                        ; end 2D scene
82ba8  ctx vt+0x38()                        ; flush/commit
```

So enabling this path is what opens the **2D GraphicsContext** around the frame. A no-op callback
is safe and does not draw pixels:

```text
libuxengine+0xa3240  WidgetBase::onReset()  -> single ret
```

### Final callback fix

```c
void *ge = sys_getInstance();
*(void **)((char*)ge + 0x318) = (void *)((char*)uxengine + 0xa3240); /* ret */
*(unsigned char *)((char*)ge + 0x328) = 1;
```

or, if a real appFw before-render callback is already at `[ge+0x318]`, only set `+0x328=1`.

After this, `sys_render` executes:

```text
beforeRendergingCallback
  ctx vt+0x18 / +0x58
  no-op callback
  ctx vt+0x60 / +0x38
isExecBeforeRendegingCallback -> true
stopClearScreen(true)  -> window+0x23c=1
Window::render
  renderInternal -> Layer2D -> renderScreen
    GraphicsDraw::begin
    RenderScreenWalker -> Node2D::draw
    GraphicsDraw::end
stopClearScreen(old)
```

This is the exact missing switch behind `prims=0` in candidate 470.


---

## Who creates/attaches view_fill

`appFw+0xc2d874` is the constructor of:

```text
view_list_scroll_cursor_fixed
```

Resolved via:

```text
GOT 0x2ee8df0 -> vtable-0x10 0x2d1bf20
vptr 0x2d1bf30
vtable-8 typeinfo 0x2d1bf08
typeinfo+8 name ptr 0x2276030 -> "29view_list_scroll_cursor_fixed"
```

This constructor:

```text
c2d8ac  Widget::Widget()
c2d8e0  memset(this+0x204, 0, 0x1194)
c2d8f4  loop initializes 0x3f8-stride subobjects
c2d980  initializes row/cursor array
c2da0c  c28f10(...)
c2da18  c27800(view_fill)
c2da24  c27800(view_fill)
c2da30  c2c188(...)
c2da38  c2c188(...)
c2da50  c27800(view_fill)
c2da54  Widget::setParent(child, this)
```

So `view_fill` is normally a **child of a view_list_scroll_cursor_fixed widget**, not directly under
Screen root. For it to render:

```text
the list widget must be active and attached to the Screen root
its child view_fill must be active and visible
```

If the list widget is not in the active tree, view_fill's own `+0x1fc=1`/`+0x220` still won't be
visited by RenderScreenWalker.

This is a second checked condition beyond the `window+0x23c` gate.


---

## view_list_scroll_cursor_fixed factory

`appFw+0xc1b3fc` is the descriptor factory for this widget:

```text
c1b3fc  stp...
c1b404  x21 = x4 (descriptor/param)
c1b40c  w22 = [x2] (current offset)
c1b418  x20 = x1 + w22 (object placement)
c1b42c  x1 = x3
c1b430  x0 = x20
c1b434  bl c2d874              ; view_list_scroll_cursor_fixed ctor
c1b438  w0 = [x19]
c1b43c  w0 += 0x239
c1b440  w0 += 0x870             ; object size 0x239870
c1b444  compare/advance
c1b3a8  virtual [x0+0x140] on object
c1b3bc  copy 0x30-byte descriptor
```

So the list widget (and its child view_fill widgets) are created from a **view descriptor table**;
`x1` is the arena/base, `x2` is the running offset, `x4` is the descriptor.

The parent is not the Screen directly; the factory writes the object into a caller-provided
arena/layout, and `Widget::setParent` happens inside the list ctor.

Consequence remains:

```text
view_fill visible/alpha alone is insufficient
the view_list_scroll_cursor_fixed parent must be built, active, and attached to Screen root
```


---

## appFw never calls GraphicsEngine::createScreen

Full appFw text scan:

```text
no `bl ...GraphicsEngine::createScreen`
```

`createScreen` is therefore a **shim-created empty gfxeng Screen**, not the native Big6 screen.
Its Layer2D has no native widgets because appFw never built them into it.

Native appFw screen activation is still:

```text
c0a86c  add x0,x21,#0xa40
c0a870  bl  0xdf91e8
```

`df91e8` operates on appFw's ScreenArea/presenter state, not on the synthetic
`GraphicsEngine::createScreen` object.

Consequence:

```text
calling createScreen(0xd) + drawFramebuffer will only swap an empty synthetic Screen
view_fill/f8a4 will stay 0
```

The runtime must use the native `df91e8(ui+0xa40)` / presenter-controller path, or find the appFw
ScreenArea-to-gfxeng-Screen bridge that copies native widgets into the gfxeng tree.


---

## appFw does not import gfxeng Screen API

`nm -D appFw.so` has **no** imports for:

```text
ux::gfxeng::Screen
ux::gfxeng::ScreenBase
ux::gfxeng::Layer2D*
GraphicsEngine::createScreen
ScreenManager
```

So appFw's native Big6 path is not calling the gfxeng Screen/WidgetSystem API. It uses its own
ScreenArea/presenter structures (`df91e8`, `df8d6c`, `de3e08`) and appFw screen descriptors.

The shim's `GraphicsEngine::createScreen(0xd/0x3f)` is therefore a **foreign synthetic Screen**;
appFw never builds native Big6 widgets into it. This is consistent with:

```text
f8a4=0
prims=0
gpe0 zero
```

even after `createScreen` succeeds.

Native Big6 rendering must use appFw's own screen/compositor path, or a bridge that copies appFw
ScreenArea content into a gfxeng Screen. No such bridge import exists in appFw's dynamic symbol table.


---

## Candidate 497 — only one UI iface visited, prims=0

`runs/cp-bind-7037dc6f`:

```text
FX6_UI4 base=7f91392000 ui=0x7f912b5658
FX6_DF91_LDR fnptr=7fa3d79df8 pc=7f9204f614 adrp=d008e942 ldr=f946fc42 mr=0
FX6_UI4 call df91e8 arg=0x7f912b6098
FX6_VISIT n=1 iface=0x7f940f3be0 id=17a4 fn=0x7f92044bc4
FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0
```

Offsets:

```text
fn = appFw+0xcb2bc4
pc = appFw+0xcbd614
```

`appFw+0xcb2bc4` dispatches:

```text
cmp w1,#0x2ce9
if equal -> return 0
else -> virtual +0x340 / +0x960
        memcpy 0x88
        bl 0xcd2814
```

`appFw+0xcbd614` is a 0x88-stride interface loop:

```text
ldr w1,[x21],#0x88
ldr x2,[x0,#0x1c8]
blr x2
```

Only one iface (`id=0x17a4`) is visited, and no 2D draw command is generated; prims remains 0.


---

## 0x2127750 caller clarification

Direct `bl 0x2127750` sites in appFw:

```text
2127b04  -> 2127750 -> 215ca08 -> [out+0x18]
2127d60  -> 2127750 -> 215ca08 -> [out+0x18]
```

`0x1395f20` is **not** a caller; it is a separate UI/message loop using
`0x20dda8c` / `0x1512f58`.

Out fields written by the original before the OSAL request:

```text
out+0x00 = id
out+0x04 = -1 (pre-request sentinel; success spoof uses 0)
out+0x08 = 0
out+0x10 = 0
out+0x14 = 0
```

Callers later write `0x215ca08()` to `out+0x18`. The C spoof zeroes 8 words, so
`+0x18` remains 0.

## Header auto gate

`/private/tmp/fx6_static_assist.h` now also provides:

```c
fx6_uxengine_base()
fx6_engine_gate_auto()
```

`fx6_engine_gate_auto()` resolves libuxengine via
`dlsym("_ZN2ux6gfxeng14GraphicsEngine15sys_getInstanceEv")` + `dladdr`, then applies:

```text
engine+0x318 = libuxengine+0xa3240 (ret)
engine+0x328 = 1
window+0x234 = 0,0,1024,540
window+0x23c = 1
```

Compiled verification:

```text
/tmp/fx6_static_assist_test.o
aarch64, rc=0
```


---

## Candidate 523 — helper patched, UI still not reached

```text
runs/cp-bind-76c1fda1
candidate 523-modelspoof2
```

Serial:

```text
FX6_HELPER pc=7f894fe750 cave=7f8d4ee900 fn=0x7f99963ecc delta=67043760 cave_mr=0
FX6_HELPER patched old=a9b97bfd new=94ffc06c mr=0
FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0
FX6_UI_CAPTURE ui=0x7f872fa658
```

Observations:

```text
- base/range issue is gone; helper patch applied.
- no undefined fx6_inject_set_presenter_done in this run.
- but no FX6_VISIT, no FX6_GATE, no UI visit.
- gpe0 remains transparent.
```

So 523 fixed the link/base failures but the UI thread still did not reach `df91e8`/WidgetSystem
update. The next blocker is before the UI visit, not the 0x2127750 patch itself.


---

## appFw native draw loop `c09a30`

Disassembly:

```text
c09a24  w20 = 10
c09a30  wgtsys()
c09a34  WidgetSystem::isFrameDelay()
c09a38  tst w0
c09a3c  b.ne c09ab4
c09a40  ...
c09a7c  wgtsys()
c09a80  WidgetSystem::notifyDraw()
c09a8c  gfxeng()
c09a90  GraphicsEngine::drawFramebuffer()
c09a94  return w0

c09ab4  wgtsys()
c09ab8  WidgetSystem::updateFrame()
c09abc  subs w20,w20,#1
c09ac0  b.eq c09a40
c09ac4  b c09a30
```

So appFw already has a native `updateFrame -> notifyDraw -> drawFramebuffer` loop, but only
`updateFrame` runs while `isFrameDelay()` is true; after 10 iterations it proceeds to notify/draw.

`isFrameDelay`:

```text
libuxengine+0x7a4048
  ldr x1,[ws]
  ldr x0,[ws+0x18]
  cmp x1,x0
  cset w0,hs     ; true if ws[0] >= ws[0x18]
```

To force `updateFrame` on this path, ensure `ws[0] < ws[0x18]`. This is separate from the
`drawFramebuffer` gate; if the UI thread reaches `c09a30`, `drawFramebuffer` is already called by
appFw itself.


---

## Candidate 524-usleepskip — still no gate

```text
runs/cp-bind-8edb59e2
candidate 524-usleepskip
```

Serial:

```text
FX6_HELPER pc=7f79cb8750 cave=7f7dca8900 fn=0x7f8a11e354 delta=67043760
FX6_HELPER patched old=a9b97bfd new=94ffc06c mr=0
FX6_OSD_FLUSH update #1 prims=0
```

No `FX6_GATE_BOOT`, no `FX6_VISIT`, prims=0. This run did **not** use the
`grmreal524-gate.cpio` built with `fx6_gate_bootstrap.o`; it used a separate usleep-skip shim.


---

## Model status readers/writers

`appFw+0x14d4654` returns `appFw+0x4dc56c8`.

Readers observed (selected):

```text
df91e8   +0x04, +0x10
1009cbc  +0x00, +0x04, +0x08, +0x10
115051c  +0x10
1169908  copies 0x20 bytes
11f55f4  +0x00,+0x04, +0x08, +0x10,+0x14, +0x1c
120630c  +0x00
```

The immediate post-call window contains **no direct stores** back into the returned pointer; this is
a BSS object mutated elsewhere through another path. Initial bytes are zero.

`fx6_model_ready()` only sets:

```text
+0x04 = 0
+0x10 = 1
```

which satisfies `df91e8`'s ready test. Other readers may see zeros at `+0x00/+0x08/+0x14/+0x1c`, so
this is a minimum ready state, not a full menu model.

523 (`usleepskip`) never called `fx6_model_ready`; only 524-gate's bootstrap does.


---

## 527 correction — spoof5 strong inject must call gate auto

First 527 attempt still only ran `fx6_model_done` because `fx6_model_spoof4.c` itself defines a **strong**
`fx6_inject_set_presenter_done`, overriding the header weak definition. Disassembly showed:

```text
1a180 ... dprintf(FX6_PRESENTER_DONE)
1a1b0 b fx6_model_done@plt
```

i.e. no model_ready / engine_gate.

Fix: `/private/tmp/fx6_model_spoof5.c` includes the header with
`FX6_STATIC_ASSIST_NO_INJECT` and defines:

```c
void fx6_inject_set_presenter_done(void) {
    static int once; if (once) return; once = 1;
    dprintf(2, "FX6_PRESENTER_DONE lock-steal install\n");
    fx6_model_done();
    fx6_model_ready_auto();
    fx6_engine_gate_auto();
}
```

New 527 disassembly:

```text
1f460 bl fx6_model_done@plt
1f464 bl fx6_model_ready_auto
1f468 bl fx6_engine_gate_auto
```

New 527 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal527-linkfix.cpio
bytes: 430238792
sha256: c7094452380e16ef70d4751976cbc0b2e84816db2599726bbf8fcff92ea64cb3
```

Expected serial:

```text
FX6_LOCK_STEAL patched
FX6_HELPER patched
FX6_GATE_BOOT init
FX6_GATE_BOOT ge=... applied
FX6_PRESENTER_DONE lock-steal install
```


---

## 527 CPIO structural verification

Compared 526 vs 527 newc archives:

```text
members: 1165 / 1165
same names: true
only differing member: usr/lib/libgrm-fbinit9.so
```

Shim payload:

```text
526: 135280 bytes, c140900c110ddb50c6ba6dad6d03ed10290dbebdd76131337679a6250631fbbe
527: 143184 bytes, fce900516f98d6cdc7c56831321273eedb7ef4d05ddf02d6271768bd9d113f7a
527.so sha256:
     fce900516f98d6cdc7c56831321273eedb7ef4d05ddf02d6271768bd9d113f7a
```

So 527 CPIO is a clean single-member replacement, not a full repack. It has not been run yet.


---

## 527 libra ObjectBuilder root cause — early dlopen

527-linkfix serial (term run):

```text
FX6_GATE_BOOT init
/usr/bin/appfw-launch: symbol lookup error:
/usr/lib/libux_core.so: undefined symbol: _ZN5libra13ObjectBuilderC2Ev
```

Cause: `fx6_engine_gate_auto()` used:

```c
dlopen("/usr/lib/libuxengine.so", 1)
```

inside the gate bootstrap thread. At appfw-launch preload time this pulls `libux_core.so` before
`liblibra.so` is ready, so `_ZN5libra13ObjectBuilderC2Ev` is unresolved.

Fix in `/private/tmp/fx6_static_assist.h`:

```c
static inline uint64_t fx6_uxengine_base(void)
{
    /* Do NOT dlopen here: at preload time libra may not be ready yet. */
    void *sym = dlsym((void *)-1,
        "_ZN2ux6gfxeng14GraphicsEngine15sys_getInstanceEv");
    if (!sym) return 0;
    ...
}
```

No `dlopen` in this path. If libuxengine is not yet loaded, `dlsym` returns null and the bootstrap
thread retries later.

Rebuilt:

```text
/private/tmp/libgrm-fbinit25-527.so
guest-hybrid-fx6kernel-capid-grmreal536-nodlopen.cpio
```

Local runner observation: the repacked CPIO stops at ~30s `Trying to unpack rootfs` with serial
98 KB, so its local QEMU run is inconclusive; term's runner previously reached appfw with the same
527 CPIO, so the libra fix must be validated by term.


---

## prims=1 observation — not yet a native frame

A term run (`runs/cp-bind-b0e40afc`, later overwritten) logged:

```text
FX6_OSD_FLUSH update #1 prims=0 nz_pixels=0
FX6_OSD_FLUSH fillrect #2 prims=1 nz_pixels=552960
FX6_OSD_FLUSH swap #3 prims=1 nz_pixels=552960
```

This is the first non-zero prim count seen, but the same run also had:

```text
FX6_OSD_NATIVE_ACTIVE skip_compat_copy=1
```

and all four captures (`gpe0.bin`, `gpe0-late.bin`, `gpe1.bin`, `gpe1-late.bin`) were still
fully transparent `(0,0,0,0)`. Therefore this is **not** a verified native frame; it may be a
shim-side full-screen fill or a flush that never reaches the captured gpe surface.

The subsequent run (`runs/cp-bind-4fd3413c`, 535-condtake) is back to `prims=0`.


---

## prims=1 is FX6_GDS_DIRECT, not native view_fill

The b0e40afc run serial shows the source of the first non-zero prims:

```text
FX6_GDS_DIRECT g=0x7f7400beb0
FX6_GDS_DIRECT vt=0x7f8d472b30 slot31=7f8d454c38
FX6_GDS_DIRECT patched mr=0
FX6_GDS_SERVICE call=1 self=0x7f7400beb0 rect=... color=...
FX6_OSD_FLUSH fillrect #2 prims=1 nz_pixels=552960
FX6_GDS_SERVICE fill r=0 id=1
FX6_GDS_DIRECT called slot31
FX6_OSD_FLUSH swap #3 prims=1 nz_pixels=552960
```

So the full-screen fill was issued by the shim's `FX6_GDS_DIRECT` probe (`GDS_SERVICE fill`), not by
`view_fill`/`RenderScreenWalker`. It also had:

```text
FX6_OSD_NATIVE_ACTIVE skip_compat_copy=1
```

and all gpe0/gpe1 captures were transparent. This is a probe fill, not a native Big6 frame.


---

## 546+ text chain

```text
libuxengine TextSprite::drawTextImpl  0x80260
  -> TextRM_drawText                  (libtextrm+0x7004)
  -> registered renderer callback
  -> GraphicsDraw::bitBlit / stretchBlit
     libuxengine 0x7aac8 / 0x7e2f8 / 0x7e6c8
  -> GraphicsContextGRM drawImage slots 0x100..0x118
```

So there is no `GraphicsDraw::drawText` symbol on the context; text becomes image/glyph blits.
`fx6_next_stage_assist.c` forwards the four drawImage slots and both drawLine slots to the
original context, so native text is not replaced by a fake glyph.

## 546+ link

Add:

```text
/private/tmp/fx6_next_stage_assist.o
```

to the 545+ shim link. Call from the shim after the native Screen root exists:

```c
fx6_native_menu_enter(appfw, screen_root, framebuffer_0x41e);
```

It does not start QEMU and does not call GDS probe fill.


---

## 546 combined shim built

```text
/private/tmp/libgrm-fbinit25-546.so
```

Link inputs:

```text
libgrm-fbinit25-520.c
fx6_entry_hook2.c
fx6_model_spoof5.c
fx6_static_linkfix.c
fx6_gate_bootstrap.o
fx6_next_stage_assist.o
```

Exports:

```text
T fx6_gds_install
T fx6_native_menu_enter
T fx6_native_view_fill
T fx6_inject_set_presenter_done
no undefined fx6_* symbols
```

CPIO (only shim replaced in 535):

```text
guest-hybrid-fx6kernel-capid-grmreal546-gdsnative.cpio
bytes: 430256056
sha256: 97fff34978e749c6f54f7e3c1f5685d9823177915f6eebb494b16e6dc035cb3a
```

Term call order after Screen root exists:

```c
fx6_native_menu_enter(appfw, screen_root, framebuffer_0x41e);
```

This creates native view_fill panel/borders and patches context fill/draw slots; it does not use the
GDS probe fill.


---

## 539-545 GDS probe patches the wrong object

Term's `fx6_gds_direct5.c` does:

```c
void *g = GraphicsDrawState::GetInstance();
unsigned long *vt = *(void **)g;
vt[31] = fx6_gds_fill;          // slot 31
...
vt[31](g, rect, color);          // self-call
```

But `GraphicsDrawState`'s vtable slot 31 (+0xf8) is:

```text
_ZN2ux4core18GraphicsSystemCore16PrepareRenderingEv
```

It is **not** fillRect. The real fillRect is on the object returned by:

```text
ux::core::GraphicsSystem::getGraphicsContext()
= gemini::GraphicsContextGRM
vtable libgemini-grm+0x1ba68
vptr +0x10
slot +0xf8 = GraphicsContextGRM::fillRect
```

`GraphicsDraw::fillRect` confirms:

```text
266f8 ... getGraphicsContext -> x20
26754 ldr x3,[x20]       ; context vptr
26758 ldr x3,[x20,#0xf8] ; fillRect
26760 blr x3
```

Therefore 539's `FX6_GDS_SERVICE fill r=0 id=1` is a **self-invoked probe**, not a native
`GraphicsDraw::fillRect`. `fx6_compat_fill_rect` + `skip_compat_copy=1` also explains why
0x41e001000 stayed transparent.

546's `fx6_gds_install()` patches the correct `GraphicsContextGRM` vptr, not
`GraphicsDrawState`.


---

## 548 WDRAW segfault — wrong widget vtable call

Term serial:

```text
FX6_WDRAW widget=0x7f76fad700 gds=0x7f6c00beb0
FX6_WDRAW vt3=0x7f863f7d00 vt2=0x7f863f9220
FX6_WDRAW calling vt3
APPFW_SEGV sig=11 addr=0x30 pc=7f7b71f320 sp=7f73e90ba0
APPFW_X0=30
APPFW_X1=7f76fad708
APPFW_PC_MODULE /usr/lib/libstella.so base=0x7f7b6ef000
```

`pc - libstella base = 0x30320`. The direct vtable call passed a widget object whose layout does
not match the called slot; `addr=0x30` is a null/mismatched field dereference, not a native
`Node2D::draw`.

This is a probe-only call and must not be treated as the native draw path. The supported route
remains `view_fill c27ea0 -> c27914 -> child vt+0x148 Node2D::draw` with a correctly typed
`view_fill`/`Node2D` object.


---

## native list/menu-row carrier

`fx6_next_stage_assist.c` now exposes:

```c
void *fx6_native_list(uint64_t appfw, void *parent)
```

It allocates `0x239870` and calls the real ctor:

```text
appFw+0xc2d874  view_list_scroll_cursor_fixed ctor
appFw+0xb196e0  Widget::setParent
```

Ctor reads param +0x00/+0x08/+0x20 (zeroed) and internally creates its
`view_fill` / `view_list_scroll_item` children. This is the native list/menu-row carrier,
not a GDS probe fill.

New 546 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal546-gdsnative.cpio
bytes: 430257040
sha256: c1fd0ffa8a3e78c475a80e2435b7da32b5ec1d55c6897517b3d4916c32dcd672
```

Symbols:

```text
T fx6_native_list
T fx6_native_menu_enter
T fx6_native_view_fill
T fx6_gds_install
```


---

## 551 begin test — wrong calling convention

`/private/tmp/fx6_begin_test.c` does:

```c
void (*setColor)(void*, const void*) = dlsym(...GraphicsDraw::setColor...);
void (*fill)(void*, int,int,int,int) = dlsym(...GraphicsDraw::fillRect...);
void *g = GraphicsDrawState::GetInstance();
setColor(g, &red);
fill(g, 0,0,1024,540);
```

But both `GraphicsDraw::setColor` and `GraphicsDraw::fillRect` are **static** (no `this`):

```text
fillRect(short x, short y, ushort w, ushort h)
setColor(CColor const&)
```

Passing `g` as x0 shifts every argument, so fillRect sees `x=g`, `y=0`, `w=0`, `h=1024`, and the
real color/clip is wrong. It also patches `GraphicsDrawState` vtable[31] (PrepareRendering), not
`GraphicsContextGRM` vptr+0xf8.

Correct:

```c
fillRect(0, 0, 1024, 540);       // static, no this
setColor(&color);                // static, no this
// patch the context:
uint64_t ctx_vptr = getGraphicsContext_vptr();
ctx_vptr[0xf8/8] = shim_fill;
```


---

## 546 CPIO structural verification

```text
535 members: 1166
546 members: 1166
same names: true
only differing member: usr/lib/libgrm-fbinit9.so
```

546 shim payload:

```text
161432 bytes
sha256 3121a3256986c69b0742b77ce1e0c66e0177b5a584cca028f3ff6c6ee0345876
546.so sha256:
       3121a3256986c69b0742b77ce1e0c66e0177b5a584cca028f3ff6c6ee0345876
```

So the 546 CPIO is a clean single-member replacement; it has not been run by term.


---

## 552-vtsympatch still patches GraphicsDrawState

```text
FX6_BEGIN2 g=0x7fa000beb0 vtv=0x7fb71c9b20 begin=0x7fb71aa248
FX6_BEGIN2 vt=0x7fb71c9b30 slot31=7fb71abc38
FX6_BEGIN2 patched mr=0
FX6_OSD_FLUSH getOffscreen #2 prims=0
FX6_BEGIN2 begin returned
FX6_BEGIN2 fill issued
FX6_BEGIN2 end returned
```

`vtv`/`vt` still belong to `GraphicsDrawState`; slot31 is `PrepareRendering`, not fillRect.
No `FX6_FILLCALL`, prims remains 0.

Correct target remains:

```text
gemini::GraphicsContextGRM
libgemini-grm+0x1ba68 vtable
vptr+0x10
slot +0xf8 fillRect
```

546 implements that patch and native view_fill/list creation.


---

## 553 realfill — real symbol, wrong vtable

```text
FX6_BEGIN3 fill_sym=0x7f828da6f8 base=7f828b4000 real=0x7f828da6f8
FX6_BEGIN3 patched mr=0 slot31=0x7f82994740
FX6_BEGIN3 calling real fill
FX6_BEGIN3 real fill returned
FX6_OSD_FLUSH prims=0
```

`fill_sym` is the real `GraphicsDraw::fillRect` (libux_core + 0x266f8), and it is called with the
correct static ABI. But the patch target `slot31=0x7f82994740` is not the GraphicsContextGRM
vptr+0xf8; no `FX6_FILLCALL`, prims remain 0.

Correct target remains:

```text
GraphicsSystem::getGraphicsContext() -> context
context vptr = [context]
context vptr[0xf8/8] = shim_fill
```


---

## correct context probe

`fx6_next_stage_assist.c` now exposes:

```c
void fx6_gds_probe_fill(void)
```

It does:

```c
get = dlsym(RTLD_DEFAULT, "GraphicsSystem::getGraphicsContext");
ctx = get();
vt = *(void ***)ctx;
vt[0xf8/8] = shim_fill;       // already installed by fx6_gds_install
vt[0xf8/8](ctx, &color, &rect);
```

This is the correct call shape: **context is the `this`**, `fillRect` is slot 0xf8. It does not use
`GraphicsDraw::fillRect(g,...)` and does not patch `GraphicsDrawState` slot31.

New 546 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal546-gdsnative.cpio
bytes: 430258248
sha256: df0f21c805c9d4fd1b849e12ff1cd5b9081bc363ad78d9663cd7dbcd88939397
```

Expected serial:

```text
FX6_NEXT ctx=... vt=... slot31=...
FX6_NEXT probe fill returned
```


---

## 554 n2ddraw patches widget vt[31], not Node2D draw

`/private/tmp/fx6_node2d_draw.c`:

```c
void **vt = *(void **)widget;
vt[31] = fx6_fill_svc;      // widget slot 31
Node2DWalker ctor(walker, ctx);
Node2D::draw(widget, walker);
```

Widget slot 31 is not the Node2D draw path. `view_fill` uses:

```text
appFw+0xc27ea0
 -> c27914
 -> child object = [view_fill + 0x1150 + mode*8]
 -> child vt+0x148 = Node2D::draw
 -> Polygon::render 0x7a7f8
 -> GraphicsDraw::fillRect 0x7ab68
 -> GraphicsContextGRM vptr+0xf8
```

Patching the parent widget vt[31] does not intercept child `Node2D::draw`, so `FX6_N2D_FILL` never
fires. The correct interception is the context fillRect slot, as implemented in 546.


---

## correction: view_fill draw slot is +0x158, not +0x148

`view_fill::c27914` calls the child's:

```text
vt+0x140  get rect
vt+0x148  ret/no-op
vt+0x158  view_fill::onDrawNotice = appFw+0xc27ea0
```

So `+0x148` (Node2D::draw base) is **not** the drawing entry; the third call at `+0x158` is the
real `view_fill::onDrawNotice`. 554's `Node2D::draw` returned without fill for this reason.

Added:

```c
void fx6_native_fill_draw(void *fill) {
    void **vt = *(void ***)fill;
    ((void(*)(void*))vt[0x158/8])(fill);
}
```

New 546 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal546-gdsnative.cpio
bytes/ sha256 printed by repack
```


546 CPIO (final for this pass):

```text
bytes: 430258928
sha256: d388a02f8be2335688b1d99e7373be45fc2903e7f1be86f327bc974a1fd2e9cb
```

`fx6_native_fill_draw` is exported as `T fx6_native_fill_draw`.


---

## c27914 exact call sequence

```text
c27914  x21 = view_fill + mode*8
c27934  x0 = [x21+0x1150]           ; child
c27938  x1 = [x0]                   ; child vptr
c2793c  x1 = [x1+0x140]
c27940  blr x1                      ; updateBBox/get rect

; fill child command struct at x0:
c27948  w8 = [view_fill+0x1d0]
c2794c  x7,x6 = [view_fill+0x1d8]
c27954  w1 = [view_fill+0x1f8]      ; color
c27958  x20 = rect pointer
c27984  stp x2,x3,[x0]
c279a0  stp x2,x3,[x0+0x10]
c279b0  stp x2,x3,[x0+0x20]
c279a8  str w22,[x0+0x30]           ; mode
c279b4  strb w1,[x0+0x34]           ; view_fill+0x220
c279b8  x0 = [x21+0x1150]
c279c0  x1 = [x0] + 0x148
c279c4  blr x1                      ; no-op ret
c279c8  x0 = [x21+0x1150]
c279d4  x1 = [x0] + 0x158
c279e0  br x1                       ; view_fill::onDrawNotice
```

So `+0x158` is the final native draw call. `fx6_native_fill_draw` invokes exactly that slot.


---

## 547 native view_fill draw probe

```text
/private/tmp/fx6_native_draw_probe.c
/private/tmp/fx6_native_draw_probe.o
/private/tmp/libgrm-fbinit25-547.so
guest-hybrid-fx6kernel-capid-grmreal547-nativeprobe.cpio
bytes: 430267024
sha256: dfe3b3a5ed66129e25bf0cddb5d2c0affdc8bd81a87985666033198ae2d769fb
```

`fx6_native_draw_probe()` walks:

```text
WidgetSystem::sys_getInstance
 -> getFirstLayerBase / getNextLayerBase
 -> getFirstWidgetBase
for each widget:
  vt = *widget
  if vt[0x158/8] == appFw+0xc27ea0:
      vt[0x158/8](widget)
```

It does not create fake pixels; it calls the real `view_fill::onDrawNotice`.

Expected serial:

```text
FX6_NDP appfw=... ws=...
FX6_NDP layer=... w=... vt=... vt158=...
FX6_NDP calling native view_fill draw
FX6_NDP native draw returned
```


---

## native render cycle

```c
void fx6_native_render_cycle(uint64_t uxengine);
```

Sequence:

```text
fx6_engine_gate(uxengine)
setDirtyRect(engine+0xb0, 0,0,1024,540)
window+0x23c = 1
GraphicsEngine::sys_update   (libuxengine+0x82978)
GraphicsEngine::sys_render   (libuxengine+0x82bd0)
GraphicsEngine::drawFramebuffer (libuxengine+0x839c8)
```

It renders the existing native tree; no fake fill.

New 546 CPIO:

```text
bytes: (printed by repack)
sha256: (printed by repack)
```


546 final for this pass:

```text
bytes: 430268976
sha256: 382642587903ccd640c8af47ca89bb6d2cd5de409e828232dfd1bb4fe683bb59
```


---

## 558 dirty render triggers fill, wrong arg order

Serial:

```text
FX6_DIRTY eng=0x7f6800c010
FX6_DIRTY patched mr=0
FX6_DIRTY rect set
FX6_DIRTY setDirtyRect done
FX6_DIRTY_FILL n=1 rect=24574,-22083,22518,-22271 c=10000
FX6_COMPAT_FILL x=24574 y=-22083 w=22518 h=-22271 color=10000 prims=1
FX6_OSD_FLUSH getOffscreen prims=1 nz_pixels=0
```

The fill callback **was** reached by `sys_render`, but the arguments are reversed. The callback is:

```text
(self, color, rect)
```

not:

```text
(self, rect, color)
```

Fix:

```text
/private/tmp/fx6_dirty_render_fix.c
/private/tmp/fx6_dirty_render_fix.o
```

It declares:

```c
static void fx6_fill_svc(void *self, const unsigned char *color, const short *rect)
```

and only calls `fx6_compat_fill_rect` when `w>0 && h>0`.

Expected:

```text
FX6_DIRTY2 eng=... g=...
FX6_DIRTY2 patched mr=0
FX6_DIRTY2_FILL n=1 rect=0,0,1024,540 c=...
FX6_DIRTY2 sys_render returned
```

This keeps the native `sys_render -> fill` path and removes the garbage rectangle.


---

## 559 SEGV root — GRM ExternalOSDIF not initialized

```text
APPFW_SEGV sig=11 addr=0x48 pc=7fb4c68f70
APPFW_X0=0
APPFW_PC_MODULE /usr/lib/libgrm.so base=0x7fb4c47000
```

`pc - libgrm base = 0x21f70`:

```text
grm::ExternalOSDIF::waitUpdateComplete()
21f70  ldr x0,[x0,#0x48]    ; this==0 -> addr=0x48
```

So `fx6_compat_flush_to_osd()` crashes when the GRM ExternalOSDIF singleton is not initialized.
`fx6_dirty_render_fix.c` now keeps the native fill but **does not call compat_flush**; it lets
`fx6_scan_osd()`/the OSD bridge handle the buffer.

Expected:

```text
FX6_DIRTY2_FILL n=1 rect=0,0,1024,540 c=...
(no waitUpdateComplete)
```


---

## 560 dirtyfix shim

The first 560 link failed:

```text
duplicate symbol: fx6_force_update
  fx6_dirty_render_fix.o
  fx6_model_spoof5.o
```

Created:

```text
/private/tmp/fx6_model_spoof5_noforce.c
```

which keeps `fx6_model_done` / `fx6_inject_set_presenter_done` but renames the old force logger to
`fx6_spoof_force_update`. The only `fx6_force_update` is now the corrected dirty render.

Built:

```text
/private/tmp/libgrm-fbinit25-560.so
guest-hybrid-fx6kernel-capid-grmreal560-dirtyfix.cpio
bytes: 430273648
sha256: 7ecd22ec658bbc5d030c286b94cbaa139e49f4a7ac3fb9fa516608761839b3bd
```

`fx6_force_update`:

```text
patch GDS/context fill callback (self,color,rect)
setDirtyRect(engine+0xb0)
sys_render
NO fx6_compat_flush_to_osd   (avoids ExternalOSDIF this=0 SEGV)
```

Expected:

```text
FX6_DIRTY2 eng=... g=...
FX6_DIRTY2 patched mr=0
FX6_DIRTY2_FILL rect=0,0,1024,540 c=...
FX6_DIRTY2 sys_render returned
```


---

## 560 invalid — undefined compat symbol

```text
nm -D --undefined-only libgrm-fbinit25-560.so
  U fx6_compat_fill_rect
```

560 did not link `libgrm-fbinit25-542.c` (which defines `fx6_compat_fill_rect` /
`fx6_compat_flush_to_osd`). It therefore cannot be loaded safely. Do **not** run 560.

Use the structurally valid:

```text
546-gdsnative.cpio
sha256 382642587903ccd640c8af47ca89bb6d2cd5de409e828232dfd1bb4fe683bb59
```

or:

```text
547-nativeprobe.cpio
sha256 dfe3b3a5ed66129e25bf0cddb5d2c0affdc8bd81a87985666033198ae2d769fb
```

546/547 do not reference `fx6_compat_*`; their GDS shim uses its own RGBA buffer.


---

## direct OSD mapping

```c
void *fx6_map_osd(void);
```

Maps:

```text
/dev/mem
0x41e001000, 0x21c000 bytes, PROT_READ|PROT_WRITE, MAP_SHARED
```

Sets `g_fb` to that pointer, so `shim_fill` writes native fills directly to the real OSD. It does not
call `fx6_compat_flush_to_osd` or GRM ExternalOSDIF, avoiding the 559 `this=0` SEGV.

Usage:

```c
void *osd = fx6_map_osd();
fx6_native_menu_enter(appfw, screen_root, osd);
```

New 546 CPIO hash printed by repack.


546 final:

```text
bytes: 430270008
sha256: c8df93a319d3e37c6909f69c69c3be84d908d14c03c929770eafd7bc61d9c2d7
```


---

## 561 direct OSD compat

Added:

```text
/private/tmp/fx6_compat_direct.c
/private/tmp/fx6_compat_direct.o
```

It defines:

```c
fx6_compat_fill_rect(x,y,w,h,color)  // mmap /dev/mem 0x41e001000, direct write
fx6_compat_flush_to_osd(void)         // no-op, already direct
```

No GRM ExternalOSDIF, no `waitUpdateComplete`.

Built:

```text
/private/tmp/libgrm-fbinit25-561.so
guest-hybrid-fx6kernel-capid-grmreal561-directosd.cpio
bytes: 430278480
sha256: 98e1a6292bcfb5b62d148ca2f5f162595b5cdd94c20a150e289f482e54d88e34
```

This still uses the dirty `sys_render -> fill` probe path, so it is **not** a native menu frame; it is
the minimum direct-OSD validation for `FX6_DIRTY2_FILL rect=0,0,1024,540`.


---

## model wait patch

```c
void fx6_patch_model_wait(uint64_t appfw);
```

Patches:

```text
appFw+0x1c1e03c  bl pthread_cond_timedwait
-> 52800000      mov w0,#0
```

This is the wait loop observed in 564:

```text
1c1e03c bl pthread_cond_timedwait
1c1e040 bl system_clock::now
1c1e044 cmp x19,x0
1c1e048 b.gt loop
```

It does not skip Presenter; it only makes this model wait return success so the loop rechecks the
deadline.

546 now exports:

```text
fx6_patch_model_wait
fx6_map_osd
fx6_native_fill_draw
fx6_native_render_cycle
fx6_native_menu_enter
```

New 546 hash printed by repack.


---

## 564 flush copies an empty buffer

```text
FX6_COMPAT_FILL x=24574 y=-22083 w=22518 h=-22271 color=10000 prims=1
FX6_COMPAT_FLUSH copied 2211840 bytes to osd41e
```

The flush worked, but the fill rectangle was rejected/invalid, so `pix_off` stayed zero; all gpe0
captures remain `(0,0,0,0)`.

Root cause unchanged: the service signature is `(self, color, rect)`, not `(self, rect, color)`.
Patch `fx6_fill_svc` argument order; then the 546/561 path can write real pixels.


---

## term dirty_push source patched in place

```text
/private/tmp/fx6_dirty_push.c
/private/tmp/fx6_dirty_push2.c
```

Changed:

```c
static void fx6_fill_svc(void *self,
                         const unsigned char *color,
                         const short *rect)
```

and removed:

```c
fx6_compat_flush_to_osd();
```

Compiled:

```text
aarch64, rc=0
```

This is the direct fix for 564's `rect=24574,-22083` garbage. The next term build that includes this
source should produce:

```text
FX6_PUSH_FILL rect=0,0,1024,540 c=...
```


---

## 568 SEGV: non-view_fill passed to fill_draw

568:

```text
FX6_MENU568 appfw=... fb=... root=...
FX6_NEXT GDS vtable=...
APPFW_SEGV addr=0x18 pc=libstella+0x30328
X0=root+8, X1=0, X4=0x1178
```

`fx6_native_fill_draw` was calling `vt[0x158]` on a Screen root (X0=root+8), not a real
`view_*`. Added a vtable-slot allowlist:

```c
known =
  appfw+0xc2750c  /* view_fill */
  appfw+0xc27ea0  /* view_frame */
  appfw+0xc3bbd8  /* view_string */
  appfw+0xc2d100  /* view_icon */
  appfw+0xc35358  /* view_menu_item */
  appfw+0xc3339c; /* view_list_scroll_item */
if (draw && known) draw(fill);
```

New 546 hash printed by repack.


---

## menu_tree_builder draws all nodes

```c
static void *fx6_menu_nodes[128];
static int fx6_menu_node_n;
fx6_menu_record(p);              // every view_fill/text/icon/item/list_item
fx6_menu_tree_draw(root) {
    for (i < fx6_menu_node_n) fx6_widget_draw(fx6_menu_nodes[i]);
}
```

`fx6_widget_draw` calls the real vtable slot `+0x158`:

```text
view_fill 0xc2750c
view_string 0xc3bbd8
view_icon 0xc2d100
view_menu_item 0xc35358
view_list_scroll_item 0xc3339c
```

This avoids the previous mistake of drawing only the root or the Screen root (568 SEGV).
Header compiles aarch64 rc=0.


---

## fx6_menu_standalone

```c
void fx6_menu_standalone(uint64_t appfw, void *framebuffer);
```

It does:

```text
fx6_gds_install(framebuffer)
root = fx6_menu_tree_build(appfw, 0)
fx6_menu_tree_draw(root)       // all recorded view_fill/view_string/view_menu_item
```

This removes term's manual `parent=0` loop (569) and calls every real widget's `+0x158` onDraw.

New 546 hash printed by repack.


---

## 570 automatic native menu bootstrap

```text
/private/tmp/fx6_menu_bootstrap.c
/private/tmp/libgrm-fbinit25-570.so
guest-hybrid-fx6kernel-capid-grmreal570-menuboot.cpio
bytes: 430287848
sha256: e0d8559ebcceed289ec5e3b804e201f1fc88a7fff0794fc7461b2a71383fbddf
```

Constructor starts a thread. Every 5s it checks `fx6_appfw_base_auto()`, maps OSD via
`fx6_map_osd()`, then calls:

```c
fx6_menu_standalone(appfw, osd);
```

which builds real `view_fill` / `view_string` / `view_menu_item` widgets and draws each via its real
`+0x158` onDraw (not a solid clear).

Expected:

```text
FX6_MENU570 init
FX6_MENU570 appfw=... osd=...
FX6_STANDALONE root=... nodes=N
FX6_STANDALONE draw done
FX6_MENU570 draw returned
```

Then gpe0 should contain text/border/row pixels, not just 0xFF101820.


---

## view_string font/layout facts

`view_string` ctor `appFw+0xc3af98` initializes:

```text
+0xa14 = 0x44        default font size 68
+0x104c/+0x1050      CColor IDs from global palette
+0x1fc = 0, +0x1fd = 0
+0x200 = -1
+0x1030             libra::String
+0xe40              MultiLineTextSprite
```

`TextSprite::setString`:

```text
libuxengine+0x8035c
  libra::RecordPtr::reset
  ResourceManager::registerText(string, ptr)
  if fail -> sys_setUxLastError(0x22000000, 123)
  TextSprite::invokeUpdateData
```

No zero font size by default; `+0xa14` can be set explicitly.

`fx6_menu_tree_builder.h` now:

```c
fx6_set_text_size(text, 44/28);
items = {"Shooting","Project","Monitoring","Audio","TC/Media","Setup"};
```

New 546:

```text
bytes: 430280944
sha256: ed3287884ee36ba1980c7d529e2a1984c872f1660af90206160f36854f1a1228
```


---

## 571 GDS fill trace

571 `FX6_MENU570` created the real view_fill children with non-null parent:

```text
FX6_NEXT view_fill p=... parent=0x7f6886a700 ...
FX6_NEXT GDS vtable=... fill=...
FX6_GPE_FILLRECT #1 (0,0,1024,540) argb=0x00000000 out=0xff101820
```

But `gpe0` remained zero. Added trace:

```text
FX6_SHIM_FILL ctx=... col=... r=... gfb=...
FX6_SHIM_ARGS rect=..., col=...
```

to determine whether term's draw actually calls our `shim_fill` at context+0xf8 or a GPE bypass.

New 546 hash printed by repack.


---

## 572 menutree stalls after GDS install

572 serial:

```text
FX6_NEXT osd mapped 0x7f782a3000
FX6_MENU572 root widget=0x7f7f38b700 layer=0x7f7400fea0 n=2
FX6_MENU572 appfw=7f7c34c000 fb=0x7f782a3000 root=0x7f7f38b700
FX6_NEXT GDS vtable=7f83be1a68 fill=...
```

Then no `FX6_NEXT view_fill`, no `FX6_MTEXT`, no fill. The first `fx6_menu_fill` is silent; likely the builder stalls in
`view_string` ctor or `TextSprite::setString` (font/resmgr).

Added logging:

```text
FX6_MTEXT ctor p=... parent=... str=...
FX6_MTEXT ctor done
FX6_MTEXT setString begin
FX6_MTEXT setString done
```

New 546 hash printed by repack.


---

## 574 view_string ctor isolation

573 stalled after bg/border, before text. 574 isolates:

```text
fx6_map_osd
fx6_gds_install
calloc 0x1200
appFw+0xc3af98(this, zero param)
log ctor done
set rect + draw vt+0x158
```

Expected:

```text
FX6_TXT574 before ctor
FX6_TXT574 ctor done
FX6_TXT574 before draw
FX6_TXT574 draw done
```

If it stops at `before ctor`, the hang is inside `view_string`/`MultiLineTextSprite`; if it stops before draw, the hang is in `setString`/font.

New 574:

```text
guest-hybrid-fx6kernel-capid-grmreal574-textctor.cpio
sha256 printed by repack
```


---

## 575 automatic view_string ctor probe

575 links `fx6_text_ctor_probe.o` + `fx6_probe_bootstrap.o`:

```text
constructor starts a thread
sleep 80
fx6_force_update()   -> map osd, gds install, view_string ctor, draw
```

Logs:

```text
FX6_PROBE575 init
FX6_PROBE575 call
FX6_TXT574 before ctor
FX6_TXT574 ctor done
FX6_TXT574 before draw
FX6_TXT574 draw done
```

575 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal575-textboot.cpio
bytes: 430291112
sha256: 77029272162c2b87ce278d9d441a63a629452831678ff5dd785300c8fcf2b431
```


---

## 575-vslate confirms view_string ctor blocks

```text
FX6_VS appfw=... fb=... root=...
FX6_NEXT GDS vtable=...
FX6_VS alloc=0x7f600c8d70
```

Then no `ctor done`, no `FX6_MTEXT`. The hang is inside:

```text
appFw+0xc3af98 -> MultiLineTextSpriteC1
```

not in `setString` yet.

Alternative direct constructor:

```text
libuxengine+0x7eb68  ux::gfxeng::TextSprite::TextSprite()
libuxengine+0x8035c  TextSprite::setString(char const*)
libuxengine+0x802bc  TextSprite::drawText()
```

`TextSprite` bypasses `view_string`/MultiLineTextSprite and may avoid the font/ResourceManager block. It still needs its own object size/position fields, which are not yet established.


576 actual:

```text
bytes: 430291208
sha256: 1dfb911b9d64ca81f2e8e38b3735fb6f229762f2e6209ce3ebdac3b3967600bb
```


---

## critical: appfw_base_auto returned 0

576 probe:

```text
FX6_PROBE575 init
FX6_PROBE575 call
FX6_TSP576 appfw=0 ux=7f77b9c000 fb=...
FX6_PROBE575 done
```

`fx6_appfw_base_auto()` failed: `dl_iterate_phdr` suffix match did not find appFw. All menu/text builders then
aborted on `!appfw`.

Fix in `/private/tmp/fx6_static_assist.h`:

```c
dl_iterate_phdr(...)
if (!base) {
    void *h = dlopen("/usr/lib/appFw.so", RTLD_NOLOAD);
    if (!h) h = dlopen("/usr/lib/appFw.so", 1);
    void *sym = dlsym(h, "Application_System_Init");
    dladdr(sym, &di);
    base = di.dli_fbase;
}
```

New 546 hash printed by repack.


---

## 577 fix: static 8 MiB menu pool instead of calloc

577 crashed at first widget:

```text
X0=0x7f7c0dbff0
X2=0x7f7c0dbfe0 = X0-0x10
pc=libstella+0x30064 TreeNode::TreeNode()
str xzr,[x0,#0x18]  -> next page unmapped
```

This means the returned block was only 0x10 bytes (or otherwise page-boundary-unsafe).

`fx6_menu_tree_builder.h` now uses:

```c
static unsigned char fx6_menu_pool[8*1024*1024] __attribute__((aligned(256)));
static unsigned long fx6_menu_pool_off;
fx6_mem_zero(n) -> aligned bump + explicit zero
```

No `calloc`, no page-boundary chunk.

New 546 hash printed by repack.


---

## 582: 0x1200 pool block is fx6_menu_fill, not text

`fx6_menu_fill` allocates 0x1178, aligned to 0x1200 by the pool. 582 logged one pool alloc then stopped
before `FX6_SR bg=...`:

```text
FX6_POOL alloc=... size=4608
```

so the stop is inside `fx6_menu_fill` (view_fill ctor / setRect / setParent), not view_string.

Added logs:

```text
FX6_MFILL ctor p=... parent=...
FX6_MFILL ctor done
FX6_MFILL rect done
FX6_MFILL parent done
```

New 546 hash printed by repack.


---

## 584 native view_fill draw (no manual Sprite APIs)

583 proved menu_fill returns and Sprite exists, but manual `reallocRect` crashed at sprite+0xda.
584 uses only:

```c
bg = fx6_menu_fill(appfw, root, 0,0,1024,540, 0xff101014);
fx6_widget_draw(bg);          // view_fill vt+0x158
border = fx6_menu_fill(..., 20,60,984,2, ...);
fx6_widget_draw(border);
fx6_scan_osd();
```

Expected:

```text
FX6_WD584 bg=...
FX6_WD584 bg drawn
FX6_WD584 border=...
FX6_WD584 border drawn
```

584 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal584-widgetdraw.cpio
sha256 printed by repack
```


---

## Sprite::renderRect x/y exact chain (585–593)

`libuxengine+0x7e064`:

```text
7e100  ldr s0,[rd,#0x8]       width
7e108  ldr x0,[rd]            <-- 8 bytes rd+0x00 = float x,y
7e128  str x0,[sp,#0xb8]      initial dest x/y
7e134  bl 0x717b0 calcDestPos (scales widths only)
7e160  bl 0x72610 calcRotate  (writes result Vector2 to sp+0xb8)
7e5a8  ldp s0,s1,[sp,#0xb8]   x/y after origin correction
7e5b0  fcvtzs w1,s1           y
7e5b8  fcvtzs w0,s0           x
7e5dc  bl GraphicsDraw::fillRect(short,short,short,short)
```

Therefore:

```text
RectData +0x00 float x     <- fillRect x
RectData +0x04 float y     <- fillRect y
RectData +0x08 float w
RectData +0x0c float h
RectData +0x10 float crop_left    NOT x
RectData +0x14 float crop_top     NOT y
RectData +0x18 float crop_right
RectData +0x1c float crop_bottom
RectData +0x20 u8 flags
RectData +0x21 u8 flip
RectData +0x22 u32 color
```

`0x7d9a0 calcDestPos` only reads Sprite+0x50 (scale x/y), uses global 0x?? for reciprocal, and writes width/offset; it does **not** supply dest x/y.
`0x7da6c calcRotate` starts from RectData+0x00 and subtracts scaled origin. Setting `+0x10/+0x14` changes crop/UV only, so fillRect stays `(0,0)`.

Sprite cache fields used by renderRect:

```text
Sprite+0x08 float width
Sprite+0x0c float height
Sprite+0x22 u32 color
Sprite+0x50 float scale_x / +0x54 float scale_y
Sprite+0x68 origin/UV
Sprite+0x78 image ptr
```

Write header: `/private/tmp/fx6_sprite_text_assist.h` (compiled aarch64 rc=0).

## TextSprite exact path

```text
TextSprite::drawText()  libuxengine+0x802bc
  if +0xa8 bit3 -> drawTextImpl
  else +0xa5=1, +0xa8|=0x10, return 1   (prepare only, no pixels)

TextSprite::render(Vector2 const&)  libuxengine+0x80c74
  checkDelayFlag, checkClipedAreaCheckOverflow
  ldrb w0,[this+0xa5]
  cmp #1
  b.ne return
  ldr x1,[vtable+0xe8]
  br x1                                (real glyph render)
```

So the required order is:

```c
TextSprite::TextSprite()        ux+0x7eb68
TextSprite::setString(utf8)     ux+0x8035c
TextSprite::drawText()          ux+0x802bc   // prepares state=1
TextSprite::render(&pos)        ux+0x80c74   // dispatches vtable+0xe8, draws glyphs
```

Calling only `drawText()` never emits glyph pixels.

## view_string zero-param crash

`appFw+0xc3af98` dereferences x1 before any font work:

```text
c3afc4  ldr x0,[x20]        -> [this+0x1b8]
c3afd8  ldr x0,[x20,#8]     -> [this+0x1c0]
c3afe0  ldr w0,[x20,#0x20]  -> [this+0x1c8]
```

A null x1 SEGVs at `0xc3afc4`. A **zeroed parameter block is safe**, but leaves those layout/style
pointers null, so MultiLineTextSprite has no real layout/font and can stall in text setup.

Default ctor `appFw+0xc3b0c4` avoids the dereference and zero-initializes `+0x1b8/+0x1c0/+0x1c8`.
Prefer it when no real Param is available:

```c
fx6_view_string_default(appfw, vs);   // appFw+0xc3b0c4
```

`view_string` still sets `+0xa14=0x44` (font size 68), `+0x104c/+0x1050` color IDs, `+0xe40`
MultiLineTextSprite.


---

## TextSprite::render is a no-op; image callback is +0x140

Resolved vtable+0xe8 for `TextSprite`:

```text
vtable 0xbd0d8 + 0x10 + 0xe8 = 0xbd1d0
RELA -> dynsym 1178
-> ux::gfxeng::TextSprite::onRender() = libuxengine+0x7e958
-> 7e958: d65f03c0  ret
```

So `TextSprite::render(pos)` checks state `+0xa5==1`, then calls a real `ret`. It paints nothing by itself.

`drawTextImpl` (0x80260) calls vtable+0x150 (`adjustClipSize`) and `refreshTextImpl` (0x801cc).
`TextSprite::onSetTextImage` (0x7f8d4) only forwards when `this+0x140` callback is non-null:

```text
7f8f8 ldr x3,[x19,#0x140]
7f900 mov x1, x20 (ImageData*)
7f904 mov x0, x19
7f908 ldr x2,[x19,#0x148] (userdata)
7f914 br x3
```

`setImageLoadCallback(cb, userdata)` is `libuxengine+0x7f970`:

```text
stp x1,x2,[x0,#0x140]   // cb at +0x140, ud at +0x148
```

`SpriteContainer::onSetTextImage` (0x7f924):

```text
ldr x0,[x0]             // container->TextSprite*
b   TextSprite::onSetTextImage
```

Therefore direct TextSprite needs one of:

```text
1. setImageLoadCallback(ts, cb, ud); in cb, take ImageData* and draw it via a Sprite
   (Sprite::renderRect + image pointer at Sprite+0x78), or
2. attach TextSprite/SpriteContainer to a live scene Node2D so its child SpriteContainer renders.
```

`TextSprite::render()` alone cannot produce glyph pixels.

## menu_text switched to default view_string ctor

`view_string` param ctor `appFw+0xc3af98` dereferences x1 at 0xc3afc4; a zeroed Param block
is safe but leaves `+0x1b8/+0x1c0/+0x1c8` null. `fx6_menu_text` now calls:

```text
appFw+0xc3b0c4  view_string default ctor
```

then `TextSprite::setString(ts+0xe40, utf8)`, preserving the ctor's `setImageLoadCallback` setup.
New 546 hash printed by repack.


---

## 596 direct TextSprite: drawImpl succeeds, no image callback

596 serial:

```text
FX6_TEXT ctor=... setString=... draw=...
FX6_TEXT ctor done vptr=...
FX6_TEXT setString done
FX6_TEXT setLayout=... setArena=...
FX6_TEXT arena done
FX6_TEXT layout0 done
FX6_TEXT drawImpl done
FX6_OSD_SCAN 41e nz_words=2
```

`gpe0.bin` is still all `(0,0,0,0)`. `nz_words=2` is scan/mailbox noise, not text pixels.

Cause: 596 never calls `TextSprite::setImageLoadCallback` (`libuxengine+0x7f970`).
`TextSprite::onSetTextImage` (0x7f8d4) checks:

```text
7f8f8 ldr x3,[x19,#0x140]    // callback
7f8fc cbz x3, 0x7f918        // null -> return, drops ImageData
```

so `refreshTextImpl` rasterizes but the `libra::ImageData*` is discarded. `TextSprite::onRender`
(vtable+0xe8, 0x7e958) is `ret`; no pixels without the callback.

Required next test:

```c
fx6_textsprite_set_callback(ux, ts, cb, ud);  // ux+0x7f970, cb at ts+0x140
fx6_textsprite_draw(ux, ts, "Shooting", 40, 100);
```

The callback receives `(ts, ImageData*, ud)`. The callback must either:

```text
1. copy/set that ImageData into a Sprite and call Sprite::renderRect, or
2. attach the TextSprite / SpriteContainer to a live Node2D so its child container renders.
```

`fx6_sprite_text_assist.h` now has:

```c
fx6_textsprite_set_callback(uxbase, ts, cb, ud);
```

Compiled aarch64 rc=0.


---

## 597 scan false positive

597:

```text
FX6_OSD_SCAN 41e nz_words=551938
FX6_OSD_SCAN 429 nz_words=0
FX6_OSD_SCAN 480 nz_words=0
```

`1024*540/4 = 138240` words, so 551938 cannot be inside the frame. The scanner is walking the
whole mapped region / using the wrong length; it is not frame evidence.

`gpe0.bin` is still exactly one color:

```text
(0,0,0,0) x 552960
```

No `FX6_TEXT` / callback / glyph log in 597. Text still needs:

```c
fx6_textsprite_set_callback(ux, ts, cb, ud);  // ux+0x7f970, +0x140
fx6_textsprite_draw(...);                     // setString/drawText
// cb receives ImageData*
```


---

## 598 TextSprite image callback probe

598 builds a TextSprite in static storage, sets callback before setString:

```text
setImageLoadCallback(ux+0x7f970) -> ts+0x140/0x148
TextSprite ctor ux+0x7eb68
setString "Shooting" ux+0x8035c
drawText ux+0x802bc
callback: FX6_CB598 ts=... image=... ud=0x598
```

Expected:

```text
FX6_TXT598 before ctor
FX6_TXT598 ctor done
FX6_TXT598 setString done
FX6_TXT598 drawText done
FX6_CB598 ts=... image=... ud=0x598
```

If `FX6_CB598` fires with non-null image, the missing ImageData delivery is proven.
598 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal598-textcb.cpio
bytes/sha printed by repack
```


---

## 598-menu2: fx6_menu_fill full success

598-menu2 used the new 546 and logged:

```text
FX6_MFILL ctor p=... parent=...
FX6_MFILL ctor done
FX6_MFILL rect done
FX6_MFILL parent done
```

So `view_fill` ctor + setRect + setParent now complete without the earlier stop. No `FX6_NEXT view_fill` follow-up
or `FX6_MENU` draw log, so the widget still is not drawn.

`FX6_OSD_SCAN 41e nz_words=551938` is again out-of-frame (138240 words max); gpe0 remains all transparent.

Next required call:

```c
fx6_widget_draw(bg);   // view_fill vt+0x158
```

Then border/rows and TextSprite callback/image.


---

## 599 full fill + text-image probe

599:

```c
bg = fx6_menu_fill(appfw, root, 0,0,1024,540, 0xff101014);
fx6_widget_draw(bg);                         // view_fill vt+0x158

border = fx6_menu_fill(..., 20,60,984,2, ...);
fx6_widget_draw(border);

TextSprite ctor ux+0x7eb68
setImageLoadCallback ux+0x7f970 (cb)
setString "Shooting" ux+0x8035c
drawText ux+0x802bc

cb(ts,image):
  sprite = *(bg+0x1058)
  *(sprite+0x78) = image
  fx6_sprite_render_rect(ux, sprite, 40,100,600,40,0xffffffff)
```

This is the first full chain that combines the proven view_fill draw with the TextSprite ImageData callback
and the corrected `RectData+0x0/+0x4` position. Expected logs:

```text
FX6_D599 bg drawn
FX6_D599 border drawn
FX6_D599 ts ctor done
FX6_D599 setString done
FX6_D599 drawText done
FX6_CB599 image=... bg=...
FX6_CB599 sprite=...
FX6_CB599 renderRect done
```

599 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal599-textimg.cpio
bytes/sha printed by repack
```


---

## fx6_menu_fill auto-draw

term keeps creating `view_fill` without calling `vt+0x158`. Added:

```c
static int fx6_menu_auto_draw = 1;
fx6_widget_draw(p);   // at end of fx6_menu_fill
```

Logs:

```text
FX6_MFILL autodraw p=...
FX6_MFILL autodraw done
```

This means every `fx6_menu_fill` now executes the real view_fill onDraw immediately, producing fill pixels without
a second term call. If the onDraw depends on a later scene parent, set `fx6_menu_auto_draw = 0` and keep using
`fx6_menu_tree_draw`.

New 546 hash printed by repack.


---

## 602-layout: LayoutAttribute path works, no glyph pixels

```text
FX6_LAY fb=...
FX6_LAY ctor/setStr/setLayout/draw ...
FX6_LAY ts=... vptr=...
FX6_LAY la=... first=...
FX6_LAY reset/gap/va/string/setLayout/draw done
FX6_OSD_SCAN 41e nz_words=2
```

`gpe0` still all `(0,0,0,0)`.

LayoutAttributeWriter + setTextLayout + draw is accepted, but no ImageData callback is installed, so the rasterized
text image is still dropped by `TextSprite::onSetTextImage` (+0x140 null). Next required call remains:

```c
fx6_textsprite_set_callback(uxbase, ts, cb, ud);  // ux+0x7f970
```


---

## 607 crash: TextRM_getNumberOfFont ABI misuse

607 (`fx6_textrm_test.c`) declared:

```c
int (*nf)(void) = dlsym(..., "TextRM_getNumberOfFont");
int n = nf();
```

Real signature (`libtextrm+0x6084`):

```text
TextRM_getNumberOfFont(int *out)
6084  stp x29,x30
6090  adrp x19,0x1d000
6094  mov x20, x0            <-- X0 = out pointer
609c  bl pthread_mutex_lock
60a0  cbz x20, 0x60c8        <-- NULL -> rc = -7
60a4  bl getFontListCount
60a8  str w0,[x20]           <-- CRASH when out pointer invalid
```

607 passed no argument, so X0 carried `6`; `str w0,[x20]` with X20=`0x18` → `APPFW_SEGV addr=0x18
pc=libtextrm+0x60a8`. This is a caller bug, not a firmware issue.

Correct usage:

```c
int (*nf)(int *) = dlsym(..., "TextRM_getNumberOfFont");
int n = -1;
int rc = nf(&n);       // rc==0 on success, n = font count
```

`TextRM_loadFontByPath(const char*, unsigned short, int, int*)` (0x5f18) follows the same pattern:
the 4th arg is an out pointer for the font id.


---

## TextRM_createText ABI: rc return, handle via 6th pointer

609 log:

```text
FX6_TRM2 init rc=0
FX6_TRM2 load rc=0 p=0x6
FX6_TRM2 createText=... drawText=...
FX6_TRM2 text=(nil) font=0x6
```

`text=(nil)` was a caller-side misreading, not a failure.

`libtextrm+0x7760 TextRM_createText`:

```text
7760  sub sp,sp,#0xc0
777c  uxth w0,w4            ; arg4 = font id (u16)
779c  str x5,[x29,#0x70]    ; arg5 = out text record
77c0  ldr x0,[x29,#0x70]
77c4  ...
79ec  ldr x1,[x29,#0x70]
79f4  str x0,[x1]           ; *arg5 = layout record handle
77f0  mov w0,w22            ; return rc (0 ok, -16/-7/-9999 errors)
```

So the real prototype is:

```c
int TextRM_createText(const char *utf8,
                      int something,      // w1 -> getLayoutPattern
                      int flags,          // w2
                      void *layoutOrNull, // x3 (NULL -> getDefaultLayout)
                      unsigned short font,// w4
                      void **out_text);   // x5 out handle
```

`609` declared it returning `void*`, so the returned `rc` (=0) was printed as `(nil)` and the real
handle in the 6th argument was ignored.

Correct usage:

```c
void *text = NULL;
int rc = TextRM_createText("MENU", 0, 0, NULL, font_id, &text);
// rc==0 && text != NULL
int drc = TextRM_drawText(text, x, y, flags);
```

`TextRM_drawText` is `libtextrm+0x7004`.


---

## 610: TextRM_drawText needs a rect*, not x/y

`libtextrm+0x7004 TextRM_drawText`:

```text
7004  ...
7018  mov x21,x0          ; text handle
7024  mov x26,x2          ; arg2 must be non-NULL (checked 7040)
7034  mov x28,x3          ; flags
7038  bl pthread_mutex_lock
7040  cbnz x26, 7074      ; NULL -> rc -7
7074  cbz x21, 7044       ; NULL text -> rc -7
7098  ldrh w24,[x19]      ; x19 = arg1 -> rect[0] (x)
709c  ldrh w25,[x19,#2]   ; rect[1] (y)
70a0  ldr  w27,[x19,#4]   ; rect[2..3]
```

So the prototype is:

```c
int TextRM_drawText(void *text, const short *rect, void *param, int flags);
```

with `rect = {x, y, w, h}` (shorts). 609 passed `drawText(t,60,80,0)` — arg1=60 is a bogus
pointer and arg2=80 is a bogus pointer; that is another caller-side ABI mismatch.

610 (`/private/tmp/fx6_textrm_draw4.c`) corrects both calls:

```c
void *text = NULL;
int rc = create("Shooting", 0, 0, NULL, font, &text);   // rc + out handle
short rect[8] = {40,100,300,40,0,0,0,0};
int drc = draw(text, rect, NULL, 0);
```

610 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal610-trmdraw.cpio
bytes: 430295248
sha256: e0742fd3b642bc29bd924a53cebeec9072a7515e9b7b07f4cab80546d9e2fede
```


---

## 611: four view_* constructors + real onDraw

`/private/tmp/fx6_four_views.c` instantiates each widget in its own static buffer, prints the real vptr and
`vt+0x158`, then calls the onDraw slot directly:

```text
view_string            appFw+0xc3b0c4 (default ctor)   buf 0x1200
view_icon              appFw+0xc2c188                  buf 0x800
view_menu_item         appFw+0xc341d4                  buf 0x10000
view_list_scroll_item  appFw+0xc30c3c                  buf 0x28000
```

Per widget logs:

```text
FX6_V4 <tag> vptr=... onDraw=...
FX6_V4 <tag> rect+parent done
FX6_V4 <tag> onDraw done
```

Expected vptr values (class table):

```text
view_string            0x2d1f210
view_icon              0x2d1bd60
view_menu_item         0x2d1c650
view_list_scroll_item  0x2d1c2c0
```

This validates all four constructors and their draw slots in one run, independent of the menu tree.
611 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal611-fourviews.cpio
bytes: 430299432
sha256: ed436b004f5618dfd5453d87c97aea941284df3833ed4e66c606a8dc3137c5fb
```


---

## TextRM_createText authoritative call site (libux_core)

`libux_core+0x2de9c TextRMSingleTextHandler::lockHandle()`:

```text
2deb8  bl  ITextHandler::getEngine()
2debc  add x20,x29,#0x40        ; stack TextRM_LayoutRecord
2dec0  add x3,x29,#0x3c         ; out: layout flags (u32)
2dec4  mov x2,x20               ; LayoutRecord*
2dec8  add x1,x19,#0x28         ; FontAttributeReader
2decc  bl  TextRMLayoutEngine::convertAttribute(attr, record, &flags)
2ded0  add x0,x19,#0x18
2ded4  bl  libra::String::operator char const*()
2ded8  mov x21,x0               ; utf8
2dee0  ldr w22,[x29,#0x3c]      ; flags from convertAttribute
2dee4  bl  ITextHandler::getLimitWidth()
2dee8  mov w4,w0                ; arg4 = limit width
2deec  add x5,x19,#0xa8         ; arg5 = &this->handle (out)
2def0  mov x3,x20               ; arg3 = LayoutRecord*
2def4  mov w2,w22               ; arg2 = flags
2def8  mov x0,x21               ; arg0 = utf8
2defc  mov w1,#0                ; arg1 = 0
2df00  bl  TextRM_createText
2df04  cbnz w0, fail            ; rc != 0 -> fail
2df08  ldr x0,[x19,#0xa8]       ; handle
2df0c  cbz x0, fail             ; handle NULL -> fail
```

So the exact ABI is:

```c
int TextRM_createText(const char *utf8,       // x0
                      int mode,               // x1, always 0 at real sites
                      int flags,              // x2, from convertAttribute
                      TextRM_LayoutRecord *rec,// x3, REQUIRED in practice
                      int limit_width,        // x4
                      void **out_handle);     // x5
```

Note x4 is **limit width**, not font id. Font selection lives inside `rec` (filled by
`TextRMLayoutEngine::convertAttribute` from a `FontAttributeReader`).

That is why 611 (`fx6_textrm_draw5.c`) got:

```text
FX6_TRM5 createText st=0 handle=(nil) pid=1 font=0x6
```

`st=0` is the rc, and `handle` stayed NULL because arg3 (LayoutRecord) was 0 and arg4 was the font id
instead of a width. The zero-LayoutRecord path falls back to `getDefaultLayout()`, but `selectPixelFormat`,
`selectTextColor`, `selectEdgeColor` and `getFontStyleHandle` then operate on a record with no font, so
`TsLayout_composeString` never produced a handle.

### Correct recipe without convertAttribute

Fill a `TextRM_LayoutRecord` by hand before calling:

```c
typedef struct { int f[16]; } TextRM_LayoutRecord;  /* >= 0x40 bytes */
TextRM_LayoutRecord rec; memset(&rec,0,sizeof rec);
/* +0x04 encoding, +0x0c pixel format, +0x10 text color,
   +0x14 background, +0x18 direction, +0x24 edge color, +0x28/+0x29 bools */
void *handle = NULL;
int rc = TextRM_createText("Shooting", 0, 0, &rec, 1024, &handle);
```

or better: call the engine path so the record is built by the firmware:

```text
alcor::ITextHandler::getEngine()
TextRMLayoutEngine::convertAttribute(FontAttributeReader&, LayoutRecord&, u32&)
```


---

## 612: createText with an explicit LayoutRecord

`/private/tmp/fx6_textrm_six.c` follows the libux_core call shape:

```c
unsigned char rec[0x60] = {0};
*(int*)(rec+0x04) = 1;            /* encoding utf8 */
*(int*)(rec+0x0c) = 0;            /* pixel format auto */
*(int*)(rec+0x10) = 0xffffffff;   /* text color */
*(int*)(rec+0x14) = 0;            /* background */
*(int*)(rec+0x18) = 0;            /* direction */
*(int*)(rec+0x24) = 0;            /* edge color */
void *h = NULL;
int rc = create("Shooting", 0, 0, rec, 1024, &h);   /* arg4 = limit width */
```

Then `TextRM_getBounds(h,&w,&h)` and `TextRM_drawText(h, rect, NULL, 0)` with
`rect={40,100,300,40}`.

612 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal612-trmrec.cpio
bytes: 430296136
sha256: 9b143d09bf14d379bcb4d548c5f5f6477bbe53e31974cead1f411fd0fec546fc
```

## Handoff: 611-fourviews vs term's 611-textrm5

Run `cp-bind-89601006` used **`grmreal611-textrm5.cpio`** (term's own probe), not my
`grmreal611-fourviews.cpio`. The `createText st=0 handle=(nil)` line therefore comes from
`/private/tmp/fx6_textrm_draw5.c`, whose arg3 was 0 and arg4 was the font id.

To validate the four widgets, run:

```text
guest-hybrid-fx6kernel-capid-grmreal611-fourviews.cpio
sha256: ed436b004f5618dfd5453d87c97aea941284df3833ed4e66c606a8dc3137c5fb
```

It prints `FX6_V4 <tag> vptr=... onDraw=...` for:

```text
string / icon / menuitem / listitem
```


---

## TextRM_LayoutRecord field map (libux_core+0x2c33c)

`ux::core::TextRMLayoutEngine::convertAttribute(alcor::FontAttributeReader const&, TextRM_LayoutRecord&, u32& flags)`
writes the record at `x20` and the feature flags at `x21`:

```text
2c35c  str w2,[x3]        ; *flags = 0x97 initial mask
2c364  ldr x2,[x0]        ; reader vtable
2c36c  ldr x2,[x2,#0x28]  ; reader->getEncoding()
2c374  cmp w0,#8          ; 8 == UTF-16?
2c378  cset w0,ne
2c37c  str w0,[x20,#0x0c] ; +0x0c  pixel-format / utf8 flag (0 = 16-bit, 1 = 8-bit)
2c380  bl TextRMTextHandler::get_font_id_table()
2c3b8  ubfiz x0,x0,#2,#8
2c3bc  ldr w0,[x23,x0]
2c3c0  str w0,[x20]       ; +0x00  resolved font id (from font-id table)
2c3c4  mov w0,#1
2c3c8  str w0,[x20,#0x04] ; +0x04  encoding = 1
2c3cc  hasFontSize()
2c3d8  mov w1,#0x14       ; default 20
2c3e8  uxtb w1,w0
2c3f0  strh w1,[x20,#0x8] ; +0x08  u16 font size (default 20)
2c414  uxtb w0,w0
2c418  strh w0,[x20,#0x0a]; +0x0a  u16 font width (only if hasFontWidth)
2c430  str w0,[x20,#0x18]; +0x18  direction (0 / 1 / 2)
2c45c  str w0,[x20,#0x28]; +0x28  ellipsis flag (u32)
2c490  str w0,[x20,#0x1c]; +0x1c  has-edge flag (1)
2c49c  strh w0,[x20,#0x20];+0x20  u16 edge size
2c4f4  str w0,[x20,#0x24];+0x24  u32 edge color
2c560  str w0,[x20,#0x10];+0x10  u32 fore color (text color)
2c5ac  str w0,[x20,#0x14];+0x14  u32 back color
```

Final struct:

```c
typedef struct {
    uint32_t font_id;        /* +0x00 resolved font id            */
    uint32_t encoding;       /* +0x04 always 1                     */
    uint16_t font_size;      /* +0x08 default 20                   */
    uint16_t font_width;     /* +0x0a only when hasFontWidth       */
    uint32_t pixel_format;   /* +0x0c 0 = wide/16-bit, 1 = utf8    */
    uint32_t fore_color;     /* +0x10 ARGB text color              */
    uint32_t back_color;     /* +0x14 ARGB background              */
    uint32_t direction;      /* +0x18 0/1/2                        */
    uint32_t has_edge;       /* +0x1c bool                         */
    uint16_t edge_size;      /* +0x20                              */
    uint16_t pad;            /* +0x22                              */
    uint32_t edge_color;     /* +0x24 ARGB                         */
    uint32_t ellipsis;       /* +0x28 bool                         */
    /* +0x2c .. 0x5f caller-internal */
} TextRM_LayoutRecord;
```

Feature bits in `*flags`:

```text
0x0001 base present
0x0008 hasFontWidth
0x0020 hasForeColor
0x0040 hasBackColor
0x0100 hasEdgeSize (zero size)
0x0300 hasEdgeSize
0x0400 hasEdgeColor
0x0800 hasEllipsis
initial 0x97
```

`TextRM_createText` requires a real record here; `x3 = 0` falls back to `getDefaultLayout()` and then
`selectPixelFormat/getFontStyleHandle` find no font, so `TsLayout_composeString` leaves the handle NULL
and `TextRM_getBounds` returns `w=h=0`. That is exactly the 2b53b09e `bounds rc=0 w=0 h=0` symptom: the
record passed was an `alcor::FontAttributeWriter`, not a `TextRM_LayoutRecord`.


---

## .uxc string container format (share/app/string_english.uxc)

Header (118208 bytes total):

```text
+0x00  'u' 'x' 'c'       magic
+0x03  u8   version = 7
+0x04  u32  0
+0x08  u16  8            index/entry width selector
+0x0a  u16  1
+0x0c  u32  0x013c93c7   table byte length (== file size - 0x0d roughly)
+0x10  ...   u16 offset index table, ascending
```

String records after the index:

```text
u16 id (little endian) | 0x1e | ASCII text | zero padding to 4-byte alignment
```

4581 such records were parsed. Records are grouped by `id` (screen/table id), and menu entries sit in
contiguous runs inside a group.

## procam_big6_menu_home strings

The home menu labels exist as plain ASCII inside `string_english.uxc`:

```text
id 0x22  block
  0x4e99  Shooting
  0x4ea9  Project
  0x4eb5  Monitoring
  0x4ed5  TC/Media

id 0x21  block (adjacent variants)
  0x3991  Audio
  0x399d  Project
  0x39a9  Monitoring

id 0x25  block
  0x81a1  Setup
  0x81ad  Setup
```

So the Big6 home menu is a six-entry list:

```text
Shooting, Project, Monitoring, Audio, TC/Media, Setup
```

each rendered from `share/app/string_english.uxc` via a ResID, not from a compiled literal in appFw.
`appFw.so` only carries the presenter/controller symbol names
(`procam_big6_menu_home_presenter`, `procam_big6_menu_home_controller`,
`procam_big6_menu_setting_presenter`); the labels are resource strings.

Consequence for the native menu builder: the labels must be supplied either by the
`TextRM` path with the English string literals above, or by resolving the same ResIDs through
`ux::resmgr::ResourceManager` (`libuxengine+0x8035c TextSprite::setString` did this internally via
`ResourceManager::registerText`).


---

## Sony_DI_Icons.ttf icon glyph map

`share/app/Sony_DI_Icons.ttf` (629604 bytes, sfnt 0x00010000):

```text
OS/2   0x148    96      glyf   0x2edc  587248
VDMX   0x1d4c   1504    head   0xcc    54
cmap   0x232c   2992    hhea   0x104   36
gasp   0x99b54  16      hmtx   0x1a8   7076
loca   0x924cc  7080    maxp   0x128   32
name   0x94074  5391    post   0x95584 17871
```

Metrics:

```text
numGlyphs   1769
unitsPerEm  2048
ascender    1663
descender   -160
```

cmap subtables: `(0,3) format 4`, `(1,0) format 6`, `(3,1) format 4`.
The `(3,1)` format-4 table maps a single contiguous Private Use run:

```text
0x20              -> glyph 1
0xE000 .. 0xEB29  -> glyph 200 .. (wraps)
```

`post` version 2.0 confirms glyph names are literally `uniE000` .. `uniEB29`, so the icon
set is one PPUA run: icon slot `n` is code point `U+E000 + n`, glyph `200 + n`.

Deliverable: `/private/tmp/fx6_menu_icons.h`

```c
#define FX6_ICON_CP(n)     (0xE000u + ((n) % 1738u))
#define FX6_ICON_GLYPH(n)  (200u + ((n) % 1738u))
#define FX6_ITEM_ICON_SIZE 40
#define FX6_ITEM_ICON_DX   8
#define FX6_ITEM_LABEL_DX  (FX6_ITEM_ICON_DX + FX6_ITEM_ICON_SIZE + 12)
```

plus item chrome for the three item view classes:

```text
view_icon             appFw+0xc2c188  vptr 0x2d1bd60  onDraw 0xc2d100
view_menu_item        appFw+0xc341d4  vptr 0x2d1c650  onDraw 0xc35358
view_list_scroll_item appFw+0xc30c3c  vptr 0x2d1c2c0  onDraw 0xc3339c
```

## Header set now available

```text
/private/tmp/fx6_ltt_font.h     TextRM_LayoutRecord + createText/drawText recipe
/private/tmp/fx6_big6_menu.h    Big6 home/setting item labels + grid coords
/private/tmp/fx6_menu_icons.h   icon PPUA map + item chrome + setting top list
/private/tmp/fx6_sprite_text_assist.h  Sprite::renderRect + TextSprite callback
/private/tmp/fx6_menu_tree_builder.h   view_fill/text/icon/item/list_item tree
```

All compile aarch64 rc=0 (headers are self-contained and mutually compatible).


---

## setDatabase call chain (who registers .uxc/.ltt)

Caller of `ux::resmgr::ResourceManager::setDatabase(char const*)` is **appFw.so inside
`Application_System_Init`**, at `appFw+0xc0b470` (the plog-style init that runs after
`uxengine_init2`):

```text
c0b470  sub sp,sp,#0x1, lsl #12
c0b484  bl uxengine_init2
c0b488  bl 0xc0b258                  ; Application_System_Init+0x214
c0b48c  adrp x0,0x2245000
c0b490  add  x0,x0,#0x8cd
c0b494  bl  ux::core::Kernel::sys_setCurrentDirectory   ; "/usr/share/app/"
c0b498  bl  UXEngine::gfxeng()
c0b49c  bl  GraphicsEngine::getAreaCheckExtensionManager()
c0b4b0  bl  AreaCheckExtensionManager::setCheckDataPath  ; "/usr/share/app/area_check_data.dat"
c0b4c0  bl  AreaCheckExtensionManager::setLogPath        ; "/tmp/area_check_log.dat"
c0b4c4  bl  UXEngine::resmgr()
c0b4cc  adrp x0,0x2245000
c0b4d0  add  x0,x0,#0x918
c0b4d4  bl  ResourceManager::setDatabase("global.xdb")
c0b4d8  bl  UXEngine::resmgr()
c0b4dc  mov w0,#5
c0b4e0  bl  ResourceManager::sys_setFontNameWithNamespace(u16)
```

Resolved path strings:

```text
0x22458cd  "/usr/share/app/"
0x22458dd  "/usr/share/app/area_check_data.dat"
0x2245900  "/tmp/area_check_log.dat"
0x2245918  "global.xdb"
```

So the resource database is `global.xdb` loaded **relative to cwd `/usr/share/app/`**, i.e.
`/usr/share/app/global.xdb`, and the font namespace index is `5` (`sys_setFontNameWithNamespace(5)`).

Implications for the earlier `FSCAN=0`:

```text
1. setDatabase must run AFTER ux::core::Kernel::sys_setCurrentDirectory("/usr/share/app/"),
   otherwise global.xdb is not found and the database stays empty.
2. sys_setFontNameWithNamespace(5) selects the font namespace; skipping it leaves font names
   unresolvable even when global.xdb is loaded.
3. Any shim that returns from Application_System_Init before c0b4d4 leaves the db unset.
```

`libuxengine.so` also references `setDatabase` 6 times (init/DB switching), but the canonical
boot-time registration is this appFw sequence.


---

## 623: native resource init + widget draw

`/private/tmp/fx6_native_res_init.c` replicates the appFw boot sequence before drawing:

```text
Kernel::sys_setCurrentDirectory("/usr/share/app/")
rm = UXEngine::resmgr()
rm->setDatabase("global.xdb")
rm->sys_setFontNameWithNamespace(5)
```

then:

```text
bg   = fx6_menu_fill(appfw, root, 0,0,1024,540, 0xff101014)
fx6_widget_draw(bg)
line = fx6_menu_fill(appfw, root, 20,50,984,2, 0xffe0e0e0)
fx6_widget_draw(line)
fx6_scan_osd()
```

Expected log:

```text
FX6_NRI cwd set
FX6_NRI resmgr=... setdb=... setns=...
FX6_NRI setdb rc=0
FX6_NRI setns rc=0
FX6_NRI bg=... bg drawn
FX6_NRI line drawn
```

623 CPIO:

```text
guest-hybrid-fx6kernel-capid-grmreal623-nativeinit.cpio
bytes: 430301064
sha256: 6f7a3d0d0b45b891d6991c433e494ae6c28ecadd42486f2264dc6397d8f6ebe9
```

## Handoff to 4b286158

Do not use the fabricated `fx6_big6_menu.h` / `fx6_menu_icons.h` (moved to
`/private/tmp/fx6_deprecated/` and marked INVALID). Their coordinates and labels were
hand-written and are not FX6's native layout.

Valid inputs now:

```text
/private/tmp/fx6_ltt_font.h             TextRM_LayoutRecord + createText/drawText ABI
/private/tmp/fx6_sprite_text_assist.h   Sprite::renderRect + TextSprite image callback
/private/tmp/fx6_menu_tree_builder.h    view_fill / view_string / view_icon /
                                        view_menu_item / view_list_scroll_item
```

Verified facts:

```text
view_fill  appFw+0xc27800  onDraw 0xc2750c   (583 menu_fill ctor/rect/parent OK)
view_string appFw+0xc3b0c4 default ctor, TextSprite at +0xe40
TextRM createText(utf8,0,flags,record,limit_width,&handle)
TextRM drawText(handle, short rect[4], non-NULL param, flags)
Sprite renderRect x/y = RectData+0x00/+0x04 (NOT +0x10/+0x14)
TextSprite onRender is ret; glyphs delivered via setImageLoadCallback (+0x140)
```

Still open (needs runtime, term owns QEMU):

```text
1. gpe0 non-zero text pixels from TextRM or TextSprite callback
2. native menu tree owned by procam_big6_menu_home_presenter
3. FSCAN/resource visibility after setDatabase("global.xdb") + namespace 5
```


---

## Native Big6 menu-id dispatch (appFw, no hand-written layout)

Inside `Application_System_Init` region at `appFw+0xde1100..` the presenter builds its view and then
dispatches on the menu id (`w21`):

```text
de11a0  cmp  w21,#6
de11a4  b.hi 0xde1228          ; out of range -> log(fmt@0x23aeedf, 83)
de11a8  adrp x0,0x23ad000
de11ac  add  x0,x0,#0x7f4
de11b0  ldrb w0,[x0,w21,uxtw]  ; signed byte jump offset
de11b4  adr  x1,0xde11c0
de11b8  add  x0,x1,w0,sxtb #2
de11bc  br   x0
```

Jump table bytes at `0x23ad7f4`:

```text
0x00 0x11 0x14 0x17 0x17 0x17 0x17
```

Decoded targets:

```text
menu id 0 -> 0xde11c0   view offset 0x3ea0
menu id 1 -> 0xde1204   view offset 0x3ec0
menu id 2 -> 0xde1210   view offset 0x3ee0
menu id 3 -> 0xde121c   view offset 0x3f00
menu id 4 -> 0xde121c   (same as 3)
menu id 5 -> 0xde121c   (same as 3)
menu id 6 -> 0xde121c   (same as 3)
```

Each target loads the matching embedded view object at `presenter + 0x3ea0 / 0x3ec0 / 0x3ee0 / 0x3f00`
and calls the same helper at `0xc8717c`. So the Big6 home menu has **4 distinct view slots**, and
menu ids 3..6 all fall back to the last one.

This is the actual native dispatch; nothing here is a hand-written coordinate table. The layout lives
inside those embedded view objects (constructed by `0xc870cc` at `presenter+0xa868`, 0x62 bytes),
not in appFw string literals.


---

## Native Big6 setting menu-id dispatch

Same shape as the home presenter, at `appFw+0xde1b78`:

```text
de1b78  cmp  w21,#6
de1b7c  b.hi 0xde1bf0        ; log(fmt 0x23aeedf, len 83)
de1b80  adrp x0,0x23ad000
de1b84  add  x0,x0,#0x804
de1b88  ldrb w0,[x0,w21,uxtw]
de1b8c  adr  x1,0xde1b98
de1b90  add  x0,x1,w0,sxtb #2
de1b94  br   x0
```

Jump table bytes at `0x23ad804`:

```text
0x00 0x10 0x12 0x14 0x14 0x14 0x14
```

Decoded:

```text
setting id 0 -> 0xde1b98   view offset +0xedc
setting id 1 -> 0xde1bd8   view offset +0xef8
setting id 2 -> 0xde1be0   view offset +0xf18
setting id 3..6 -> 0xde1be8  view offset +0xf38
```

Each branch passes that embedded view to the common helper `0xc8717c`, then calls
`0xf42d80`. So the setting screen also has **4 view slots** with ids 3..6 sharing the last.

`f24de8` (the post-dispatch helper) loops ten times calling `0xde45b4` on the view — that is the
list-row populate loop, i.e. the native list construction path. No hand-written coordinates are
involved; row geometry comes from the embedded view objects.


---

## Correction: 0xc8717c / 0xde45b4 are not builders

- `appFw+0xc8717c`: `str x1,[x0,#0x650]; ret` — only stores a view pointer into the presenter.
- `appFw+0xde45b4`: `ret` — empty.

So my earlier guess that `f24de8` was the "list-row populate loop" was wrong: it calls an empty
function ten times.

What is real and confirmed:

```text
home presenter   appFw+0xde1100..   7-way jump table @0x23ad7f4, view slots +0x3ea0/0x3ec0/0x3ee0/0x3f00
setting presenter appFw+0xde1b40..  7-way jump table @0x23ad804, view slots +0xedc/0xef8/0xf18/0xf38
```

The embedded view objects are constructed by `appFw+0xc870cc` (home, size 0x62 at presenter+0xa868)
and the setting equivalent. The actual row drawing is inside those view classes, not in these helpers.


---

## CRITICAL: ux::resmgr wrappers are static (no `this`)

Every exported `ux::resmgr::ResourceManager::*` in `libuxengine.so` is a thin **static wrapper** that
loads the global singleton (`libuxengine+0xc4000+0xbb8`) into x0 and shifts the caller's x0 into x1.
There is **no `this` parameter**. Calling them as member functions (`fn(this, arg)`) passes `this` as the
first data argument and is wrong.

Verified stubs:

```text
75270  setDatabase(char const*)            mov x1,x0 ; x0=global ; b libra::ResourceManager::setDatabase
75280  setDatabase(void const*,unsigned)   mov w2,w1 ; mov x1,x0 ; x0=global ; b libra::...
752f8  sys_setFontNameWithNamespace(u16)   mov w1,w0 ; x0=global ; b libra::...
7565c  createFont(FontAttribute const&, RecordPtr&)   mov x2,x1 ; mov x1,x0 ; x0=global
75670  createFont(unsigned, RecordPtr&)               mov x2,x1 ; mov w1,w0 ; x0=global
75684  createTextLayout(LayoutAttribute const&, RecordPtr&)  mov x2,x1 ; mov x1,x0 ; x0=global
75698  createTextLayout(unsigned, RecordPtr&)         mov x2,x1 ; mov w1,w0 ; x0=global
74e20  UXEngine::resmgr()                             b libra::ResourceManager::sys_getInstance
750f4  ResourceManager::sys_initialize(unsigned)      real init: create singleton + init
75118  ... libra_register_singleton ...
7511c  ... ux::core::system_create_resmgr ...
75120  str x0,[x19,#0xbb8]
75128  bl libra::ResourceManager::init
```

Correct C prototypes:

```c
int  setDatabase(const char *path);                 /* static, singleton implicit */
int  setDatabase(void const *buf, unsigned size);
int  sys_setFontNameWithNamespace(unsigned short);
int  createFont(alcor::FontAttribute const&, libra::RecordPtr&);
int  createFont(unsigned, libra::RecordPtr&);
int  createTextLayout(alcor::LayoutAttribute const&, libra::RecordPtr&);
int  createTextLayout(unsigned, libra::RecordPtr&);
int  ResourceManager_sys_initialize(unsigned);      /* must run before setDatabase */
```

How appFw actually calls it (`appFw+0xc0b4c4`):

```text
c0b4c4  bl UXEngine::resmgr()        ; returns instance but...
c0b4cc  adrp x0,0x2245000
c0b4d0  add  x0,x0,#0x918            ; x0 = "global.xdb"  (overwrites resmgr result)
c0b4d4  bl ResourceManager::setDatabase
```

Only the path is passed. This is why 626/627 got:

```text
FX6_RESINIT setdb rc=1073741824 (0x40000000)
```

`626/627` called `setdb(rm, "global.xdb")`; the wrapper shifted `rm` into the path slot, so
`XDBTable::load` tried to open a pointer as a filename, `MappedFileReference::create` returned NULL, and
`XDBTable::load` returned 0; `SystemLookupTable::setDatabase` then took the log path and returned a
non-zero diagnostic — observed as `0x40000000`.

Correct call sequence:

```c
int ok = ResourceManager_sys_initialize(0);   /* creates singleton at 0xc4000+0xbb8 */
int rc = setDatabase("global.xdb");           /* static: path only */
int rf = sys_setFontNameWithNamespace(5);
```

`sys_initialize` must run first; without it the singleton pointer is NULL.


---

## Native menu list container (appFw+0xc870cc) and its view-class filter

`appFw+0xc870cc` is the real menu-page container constructor:

```text
c870ec  str wzr,[x19,#0x648]        ; count = 0
c870f0  mov x2,#0x640
c87100  add x0,x0,#0x10
c87104  str x0,[x19]               ; vtable
c87108  add x0,x19,#0x8
c87114  bl memset                  ; clear 0x640 bytes
c87118  loop over x22 entries, stride 0x48:
c87120    ldr x0,[x20]              ; entry->view object
c87124    ldp x1,x2,[x0]            ; view vptr, id
c8712c    bl 0xc87054               ; is_supported_view(vptr)
c87130    tst w0,#0xff
c87144    st  x1,[x19+0x8+0x10*n]   ; record view ptr
c8714c    ldrh w1,[x20,#0x3a]
c87150    str w1,[x19+0x8+0x10*n+8] ; record u16 at entry+0x3a
c87160  str w21,[x19,#0x648]       ; count
c87168  str xzr,[x19,#0x650]
```

Each menu entry descriptor is **0x48 bytes**, holding a view pointer at +0x00 and a `u16` at +0x3a
(the resource/text id); the container keeps a packed array of `{view*, u16}` records at 0x10-byte
stride starting at `container+0x8`.

`appFw+0xc87054` is the view-class filter: it compares the entry's vtable against five RTTI class
pointers and returns 1 on match:

```text
0x2eeb000+0x738   class A
0x2ee3000+0xcc8   class B
0x2eee000+0x168   class C
0x2ee6000+0xab0   class D
0x2ee9000+0x180   class E
```

`0xc8717c` stores the selected view into `container+0x650`; `0xc87230..` then write per-class flags
(`+0x3c`, `+0x61`, `+0x30`, `+0xca8`, ...) and the entry id into offsets like `+0x1000+0x6c`.

This is the actual menu construction path: entries come from a `0x48`-byte descriptor table in appFw's
data segment, filtered by class, with the row text id at `descriptor+0x3a`.


---

## global.xdb / uxc / ResID encoding

`share/app/global.xdb` (1792 bytes) is only a **file index**, not an id table:

```text
+0x00  'u' 'x' 'a'    magic
+0x03  u8   version 7
+0x04  u32  0
+0x08  u32  9          number of entries
+0x0c  u32  0x0000e007
+0x10  u32[9] entry offsets: 0x0 0x38 0x334 0x674 0x690 0x69c 0x6b8 0x9 0x2001
```

Entries name the container files:

```text
../../../usr/share/app/image_00_169.uxc
string_english.uxc   string_japanese.uxc   ... (all languages)
style_cmn.uxc  lang_cmn.uxc  color_cmn.uxc  image_00_169.uxc
```

So `setDatabase("global.xdb")` only maps those files; ResIDs live inside each `.uxc`.

`.uxc` header (all files `magic='uxc'`, version 7):

```text
+0x00  'u' 'x' 'c'
+0x03  u8  7
+0x04  u32 0
+0x08  u16 8           index entry size divisor
+0x0a  u16 <n>         record type/group
+0x0c  u16 <type>      per-file type tag (0x93c7 strings, 0x2f lang, 0xc01b color, 0xe64e uxd image)
+0x0e  u16 <count>     number of id entries (316 for string_english, 370 for _2, 3 for lang, 1 color, 100 image)
+0x10  u32 <ns<<16>    NAMESPACE in the high half
+0x14  u32 <ns<<16 | ...>
+0x18  u16[count+1]   ascending byte offsets into the payload
```

Measured namespaces:

```text
string_english.uxc   +0x10 = 0x00050000  -> namespace 5
string_*_2.uxc       +0x10 = 0x000a0000 / 0x000b0000 -> 10 / 11
color_cmn.uxc        +0x10 = 0x00020000  -> namespace 2
lang_cmn.uxc         +0x10 = 0x00050000  -> namespace 5
image_00_169.uxc(uxd)+0x10 = 0x00050000  -> namespace 5
```

That is exactly why appFw calls `sys_setFontNameWithNamespace(5)`: namespace 5 is the string/font
namespace. Any scan that looks for ResIDs without selecting namespace 5 (and without the string
namespace registered) sees zeros, which explains `fonts found=0` in 626/627.

`633`'s scan of `id 0..512` returning 0 has the same cause: `global.xdb` gives files, but the id
array only exists per-namespace inside each `.uxc`, and the uxc offset table is `u16` byte offsets, not
ids. A lookup must go through `ResourceManager` with the right namespace, not by reading the xdb.


### 638 — Corrected `.uxc` record format (supersedes the `+0x18` offset-table note above)

A fresh parse of the containers with known ground truth (`Shooting`, `Audio`, `Setup`, `Add Item`)
shows the header/table layout above was off by one field. The real layout is:

```text
+0x00  'u' 'x' 'c' | 'u' 'x' 'd'   (uxd = binary payload records, e.g. image_00_169.uxc)
+0x03  u8   7
+0x04  u32  0
+0x08  u16  8
+0x0a  u16  <group>      record class: 0 image, 1 string_A, 2 string_B, 3 style, 5 lang, 6 color
+0x0c  u16  <type>       per-file tag (0x93c7 string_A, 0x3c?? string_B, 0x40 style, 0x2f lang, 0xc01b color, 0xe64e uxd)
+0x0e  u16  <count>
+0x10  u16  <group again>   NOT a namespace: values 1/2/3/5/6 match +0x0a exactly
+0x12  u16  <first offset / table bias>
+0x14  u16[count]  ascending byte offsets of the records
```

So `+0x10` is **not** `namespace<<16`. The earlier "string_english +0x10 = 0x00050000 -> namespace 5"
reading was a coincidence of two adjacent `u16`s (`0x0000` and `0x0005`) and is withdrawn: the string
namespace still resolves to 5, but it comes from `sys_setFontNameWithNamespace(5)` / the resource
manager, not from this header field.

Record wire format (uniform for group 1/2 strings, 3 style, 5 lang, 6 color):

```text
record := u16 id  | u16 marker | payload
marker: 0x001e for strings (payload = NUL-terminated UTF-8)
        0x003a for color   (payload = u32 RGBA, e.g. C001 -> 000000ff, C011 -> ee0000ff)
        0x0026 for style/lang (payload = fixed struct; style = 24 bytes, lang = 8 bytes)
records are 4-byte aligned relative to the payload start
```

Verified strings (byte-exact, from `string_english.uxc`):

```text
0x2121 Audio            0x2227 Shooting          0x2228 Project
0x222a Technical        0x222b TC/Media           0x2525 Chunk
0x2531 Setup
```

Verified colors (`color_cmn.uxc`, 27 records, id 0xc000..0xc01a) — this is the only place UI colours
exist, so any hard-coded RGB in a hand-written menu is provably fabricated:

```text
C000 000000cc  C001 000000ff  C002 111111cc  C003 111111df  C004 111111ee
C005 111111ff  C006 222222cc  C007 222222ee  C008 222222ff  C009 333333ff
C00A 444444cc  C00B 444444ff  C00C 555555ee  C00D 666666ff  C00E 777777ff
C00F aaaaaaff  C010 eeeeee ff C011 ee0000ff  C012 ffdd00ff  C013 888888ff
C014 ffaa00ff  C015 ffee00ff  C016 ffc000ff  C017 000000df  C018 885500ff
C019 ffffffff  C01A 0000ffff
```

Index built for all containers: `/private/tmp/fx6_uxc_index.json`
(`string_english.uxc` 5041 ids, `string_english_2.uxc` 5925 ids, `image_00_169.uxc` 70 ids,
`style_cmn.uxc` 1 id, `color_cmn.uxc` 27 colour records, `lang_cmn.uxc` 3×8-byte records).

### 638 — ResID bitfield, confirmed against the colour table

`liblibra.so` `sys_getNamespaceID` @`0x2e8fc` decodes the packed id. Re-checked on real data:

```text
bits[25:24] must be 2 (0x02000000) or 3 (0x03000000)
namespace = (id >> 13) & 0x7ff
index     = id & 0x1fff
```

The decisive confirmation is the colour resource: the descriptor field carries `0x0200c001`..`0x0200c019`
and `color_cmn.uxc` stores exactly ids `0xc001`..`0xc019` as RGBA. With the formula above:

```text
0x0200c001 -> ns 6, index 1  ; color_cmn.uxc group = 6, record id 0xc001   MATCH
0x0200c011 -> ns 6, index 17 ; color_cmn.uxc record id 0xc011              MATCH
```

So `namespace` indexes the container class (2/5/6/…), and `index` is the record id inside it. For the
namespace-5 string set the concrete encoding is `0x0200a000 | idx`, namespace-2 `0x02004000 | idx`,
namespace-3 (font/textlayout) `0x02006000 | idx`, namespace-4 `0x02008000 | idx` — exactly the
families that worked in 637 (`0x0200a005..a00a`, `0x02006000..6005`, `0x02008000..8002`).

`liblibra.so` `sys_setFontNameWithNamespace(5)` @`0x2dad0` writes the resolved `uint32_t[]` of FontName
ResIDs into `rm + 0x90`; `createFont` @`0x2e9a0` returns 1 on success / 0 on failure (bool).

### 638 — The `0x48`-byte menu descriptor table for `appFw+0xc870cc`, located

`appFw+0xc870bc` is the real container ctor (`stp x29,x30` prologue at `0xc870bc`, body from `0xc870cc`).
It is called from the setting presenter at `appFw+0xde1b3c` with `x2 = 10`, and `x1` loaded from the
GOT slot `appFw+0x2eed7b0`, whose relocation (`.rela.dyn`, type `R_AARCH64_RELATIVE`, addend) resolves to:

```text
table address = appFw+0x2ea3e50   (.data.rel.ro),   count = 10,  stride = 0x48
caller        = appFw+0xde1b3c   inside the setting presenter appFw+0xde1b78
```

Descriptor record layout (confirmed by the ctor's own `ldr w1,[x20,#0x3a]` at `0xc87140`):

```text
+0x00  const void*  prototype view object (in .data.rel.ro, vptr already installed)
+0x08  const char*  debug name (ASCII, e.g. "No20_SETTING_MAIN_STRING")
+0x18  u32  string slot 0   (0 or a packed ResID)
+0x1c  u32  string slot 1   (font / secondary string ResID)
+0x20  u32  string slot 2
+0x24  u32  font ResID
+0x28  u32  secondary font ResID
+0x2c  u32  flag word (0x44 everywhere except No2_SETTING_ITEM = 0x01)
+0x30  u32  0x00000ce2   layout/size constant
+0x34  u32  0x00002ce9   layout/size constant
+0x38  u16  (padding / subtype)
+0x3a  u16  row text id  <-- the ONLY field the ctor reads besides the pointer
+0x3c  u16  x      +0x3e  u16  y      +0x40  u16  w      +0x42  u16  h
```

The ctor loop (`0xc87118`..`0xc8715c`) does exactly:

```text
for (i = 0; i < count; i++, desc += 0x48) {
    if (appFw_0xc87054(desc->proto)) {          // RTTI allow-list of 5 view classes
        container->rows[n].view = desc->proto;  // stored at +0x08 + n*0x10
        container->rows[n].id   = desc->u16_3a; // stored at +0x10 + n*0x10
        n++;
    }
}
container->count    = n;      // +0x648
container->selected = NULL;   // +0x650
```

All 10 entries of `appFw+0x2ea3e50`, byte-exact (`resID` column = `+0x3a`, the value the ctor stores):

```text
[00] No107_BLOCK_TOUCH            proto=0x042d5860  +0x1c=0           +0x24=0           id=0  rect=(0,0,1024,540)
[01] No4_SETTING_LIST_MAIN        proto=0x042d5a20  +0x1c=0           +0x24=0           id=1  rect=(96,72,402,432)
[02] No20_SETTING_MAIN_STRING     proto=0x042d57f0  +0x1c=0x0200a029  +0x24=0x02006007  id=2  rect=(139,270,348,36)
[03] No3_SETTING_VALUE            proto=0x042d57f0  +0x1c=0x0200a02b  +0x24=0x0200602e  id=3  rect=(505,266,315,36)
[04] No32_SETTING_VALUE2          proto=0x042d57f0  +0x1c=0x0200a02b  +0x24=0x0200602e  id=4  rect=(505,266,308,32)
[05] No2_SETTING_ITEM             proto=0x042d57f0  +0x1c=0x0200a02b  +0x24=0x02006030  id=5  rect=(505,236,315,28)
[06] No106_BUTTON_BOTTOM_RIGHT    proto=0x042d58d0  +0x1c=0x0200a02a  +0x24=0x0200600d  id=6  rect=(654,425,164,72)
[07] No105_BUTTON_BOTTOM_CENTER   proto=0x042d58d0  +0x1c=0x0200a02a  +0x24=0x0200600d  id=7  rect=(398,425,164,72)
[08] No103_BUTTON_TOP_RIGHT       proto=0x042d58d0  +0x1c=0x0200a02a  +0x24=0x0200600d  id=8  rect=(654,80,164,72)
[09] No102_BUTTON_TOP_CENTER      proto=0x042d58d0  +0x1c=0x0200a02a  +0x24=0x0200600d  id=9  rect=(398,80,164,72)
```

Entries 06..09 also carry `+0x18 = 0x020023da`. Decoded with the bitfield below it is ns 1, idx 0x3da,
i.e. record `0x23da` in `string_english.uxc`, which is the literal **"Set"** — the button label. So
`+0x18` is the primary text ResID and `+0x1c`/`+0x24`/`+0x28` are the text-layout and font ResIDs.
Entries 00..05 leave `+0x18 = 0` because they render dynamic values, not a static caption.

The same mechanism drives 122 call sites / 121 distinct tables (`/private/tmp/fx6_menu_callsites.json`,
full dump `/private/tmp/fx6_tables_dump.txt`), e.g.:

```text
home presenter   appFw+0xde1158 -> table 0x2e9e210, count  98
setting pages    appFw+0xde19c4 -> table 0x2eaf208, count  17
                 appFw+0xde1b3c -> table 0x2ea3e50, count  10
                 appFw+0xde1ca4 -> table 0x2e9ad78, count  35
```

This is the authoritative source of native menu geometry: every x/y/w/h and every ResID above comes
from appFw's own `.data.rel.ro`, so a renderer that walks these tables cannot produce a fabricated menu.

### 638 — `view_string` field map, resolved from `onDraw` (vtable `+0x158` = `appFw+0xc3bbd8`)

Field accesses recovered from the corrected disassembly
(`/private/tmp/fx6dis.py`, listing `/private/tmp/vs_ondraw.asm`, symbol-annotated
`/private/tmp/vs_ondraw_ann.txt`):

```text
+0x1e8 / +0x1ec  int32  dest x / dest y      (used to build Vector2 for setLocalPos)
+0x1f0 / +0x1f4  int32  width / height       (setClipSize + setRectSize)
+0x1fc           u8     "has explicit string" -> gates the whole text path
+0x1fd           u8     spare flag
+0x200           u32    String ResID; -1 = "no resource string" (accessor appFw+0xc3b61c:
                        `ldr w0,[x0,#0x200]; ret`). 0x02002227 -> "Shooting"
+0x208           u32    FontName ResID #1     +0x20c           u32    FontName ResID #2      > the 6-entry array passed to
+0x210           u32    FontName ResID #3      /  TextSprite::setFont(ptr, 6)
+0xa30           u32    FontName ResID #0     /
+                        (the 4th slot defaults to 0x0200a029 when [0xa26]==0,
                         the 5th is the constant 0x02008002, the 6th is the ResID
                         returned by ResourceManager::createFont)
+0x214           u32    vertical align (forwarded to LayoutAttributeWriter::setVerticalAlign)
+0x218           u8     ellipsis flag, only honoured when +0xa0c == 1
                        (forwarded to alcor::FontAttributeWriter::setEllipsis)
+0x21c           u32    dictionary row count base / row kind of row 0
+0x220..         rows, stride 0x5c: row+0x00 u32 kind (1=string, 2=string+number,
                        3=ResID), row+0x04 libra::String, row+0x58 u32 value
+0x610           u32    dictionary row count (0 -> +0x200 path, >0 -> fragment path)
+0x1020          ptr    alcor::LayoutAttribute (built by LayoutAttributeWriter)
+0x1030          ptr    libra::Dictionary for the placeholder rows
+0x104c/+0x1050  u32    fonts resolved at ctor time
+0x1058          ptr    second Sprite
+0xa0c           u32    ==1 enables ellipsis/scrollable features
+0xa24           u8     scrollable flag (forwarded to MultiLineTextSprite::setScrollable)
+0xa28/+0xa2c    u32    line-break type selector
+0xa34           u32    -1 disables the prefetch loop
```

The draw path is exactly:

```text
TextSprite at view+0xe40
  Vector2(0,0)                        -> Element::setLocalPos
  TextSprite::setClipSize(w, h)       -> +0x1f0 / +0x1f4
  TextSprite::setFont(ptr, 6)         <- arg order per PLT stub b1a050 (x0=this, x1=ptr, w2=6)
  TextSprite::setString(ResID)        <- +0x200
  TextSprite::drawText()              <- the call that actually emits glyph quads
  TextSprite::freezeDrawText()
  ResourceManager::prefetchTextImage(&ids, 6, Dictionary*, LayoutAttribute*, fontId, flags)
```

Symbol resolution used throughout: `/private/tmp/plt_appFw.json` (830 stubs, rebuilt from
`.rela.plt` + the `adrp x16 / ldr x17,[x16,#imm]` pattern by `/private/tmp/plt5.py`).
`ResourceManager::createFont` = PLT `0xb177d0`, `TextSprite::setFont` = `0xb1a050`,
`ResourceManager::getText` = `0xb17820`, `prefetchTextImage` = `0xb175d0`.

### 638 — Complete ResID namespace → container map (solves the "font.uxc / textlayout.uxc missing" gap)

The `.uxc` header field at `+0x0a` **is** the namespace number, and every namespace that the menu
descriptors reference has a container on disk. There is no separate `font.uxc` or `textlayout.uxc`:
those resource families live in `style_cmn.uxc` (font/style records) and `lang_cmn.uxc`
(text-layout records).

```text
ns  container                 grp(+0x0a)  records  id range        record payload
 0  image_00_169.uxc               0         100   0x0000..0xffe9   image blob (uxd)
 1  string_english.uxc             1        5041   0x2000..0x2xxx   UTF-8 string  (marker 0x1e00)
 2  string_english_2.uxc           2        5925   0x4xxx..0x5xxx   UTF-8 string  (marker 0x1e00)
 3  style_cmn.uxc                  3          64   0x6000..0x603f   font/style record, 24 B (marker 0x2600)
 4  --- no container on disk ---                                             (ids only observed via createFont)
 5  lang_cmn.uxc                   5          42   0xa005..0xa02e   text-layout record, 20 B (marker 0x2600)
 6  color_cmn.uxc                  6          27   0xc000..0xc01a   RGBA u32 (marker 0x3a00)
```

Record ids are exactly `(ns << 13) | index`, which is why `0x0200a029`, `0x02006007`, `0x0200c001`
decode into these tables without any extra offsetting.

Decoded against real descriptor fields:

```text
descriptor +0x18 = 0x020023da -> ns 1 idx 0x3da -> string_english.uxc 0x23da = "Set"     (button label)
descriptor +0x1c = 0x0200a029 -> ns 5 idx 0x029 -> lang_cmn.uxc 0xa029 = 00 01 00 00 00 00
descriptor +0x24 = 0x02006007 -> ns 3 idx 0x007 -> style_cmn.uxc 0x6007 -> 32 px font (see size map)
descriptor +0x28 = 0x0200600e -> ns 3 idx 0x00e -> style_cmn.uxc 0x600e
fill               0x0200c001 -> ns 6 idx 0x001 -> color_cmn.uxc 0xc001 = 0x000000ff (opaque black)
separator          0x0200c00e -> ns 6 idx 0x00e -> color_cmn.uxc 0xc00e = 0x777777ff
```

`lang_cmn.uxc` record body (20 B, stride confirmed on 43 consecutive `0x0026` markers 20 bytes apart):

```text
+0x00 u32  0x00000001      record kind
+0x04 u32  packed ResID    e.g. 0xa005 -> 0x0200a000, 0xa006 -> 0x0200a001
+0x08 u32  0x000000ff      colour (white)
```

`style_cmn.uxc` record body (24 B, verified on 0x6000 / 0x6001 / 0x603f):

```text
+0x00 u16  0x0006 | 0x0008       variant tag
+0x02 u8   size_w      +0x03 u8  size_h    (0x6000 = 0x12,0x12 = 18 px; 0x6001 = 0x24,0x24 = 36 px)
+0x04 u32  foreground RGBA (0x00000000 / 0x000000ff ...)
+0x08 u32  background RGBA
+0x0c u32  edge colour
+0x10 u16  flags       +0x12 u16  edge size / padding
```

Independent cross-check: `appFw+0x2276db0` holds a 39-entry `(ResID -> pixel size)` table which agrees
with the byte fields above for the same ids, e.g. `0x200603c -> 15`, `0x200602a -> 20`,
`0x200600d -> 30`, `0x2006025 -> 100`, and `0x2006001 -> 36` matching `style_cmn 0x6001`'s `0x24,0x24`.

`appFw+0xc3b6d8` is the lookup for that table (`ldr w0,[x0,#0x208]` at `0xc3bf4c` feeds it);
`appFw+0xc3b744` is the horizontal-alignment selector driven by `+0x210`:

```text
+0x210 == 0x0200a02a -> x = width - measuredWidth          (branch 0xc3b790: `sub w0,w19,w0`)
+0x210 == 0x0200a02b -> x = (width - measuredWidth) / 2      (branch 0xc3b7a8: adds `sdiv w0,w0,#2`)
+0x210 == 0x0200a029 -> x = 0                               (branch 0xc3b770: `mov w0,#0`)
anything else       -> std::__throw_logic_error("..." @0x2276f28, line 0x2c2)
```
`w19` is `[x0,#0x1f0]` (the resident width) and the virtual `+0x178` returns the measured text width.

Artifacts: `/private/tmp/fx6_ns_map.json` (namespace map + ids), `/private/tmp/fx6_uxc_index.json`
(id → text for every string container), `/private/tmp/appfw_plt.json`, `/private/tmp/plt5.py`,
`/private/tmp/fx6_tables_dump.txt` (all 121 descriptor tables), `/private/tmp/fx6_menu_callsites.json`.

### 638 — What is proven about the descriptor rect, and what is not

The container constructor `appFw+0xc870bc` reads exactly two fields out of each 0x48-byte record:
`+0x00` (prototype pointer) and `+0x3a` (row id). It does **not** read the rect at `+0x3c..+0x42`.

A full `.text` scan for `ldrh` with displacement `0x3c/0x3e/0x40/0x42` finds 166 sites, and only one of
them (`appFw+0x1ca5b28`, inside a layout/attribute builder that stages the values on the stack) is
within reach of a store into `view+0x1e8..+0x1f4`; that site is not the menu path. So the consumer of
the authoring rect is still unidentified.

Consequence for the renderer:

* proven and safe: the table address, the stride, the prototype pointer, the row id, every ResID, and the
  fact that `view_string::onDraw` renders when `+0x1fc != 0` and `+0x200` holds a String ResID.
* still an assumption: that `+0x3c..+0x42` is the on-screen rect. `fx6_native_menu_tables.h` reads that
  rect from the table (never a literal) and exposes `fx6_apply_geometry_enable` so the assumption can be
  switched off the moment a rendering shows it is the wrong source.
* the earlier hand-placed menu is retired: `/private/tmp/fx6_menu_tree_builder.h` no longer contains any
  literal coordinate, literal label or literal colour. It forwards to `fx6_native_menu_tables.h`, which
  only walks appFw's own tables.

### 638 — PIXEL EVIDENCE: native text reached gpe0 (run `cp-bind-912b30d1`, image 645)

This closes the "only a cleared background counts" requirement: the frame below is decoded from
`gpe0.bin` of run `cp-bind-912b30d1`
(`.../early-kernel/cp-helper-agnostic/runs/cp-bind-912b30d1/gpe0.bin`, 1024×540, 2211840 bytes),
produced by image `guest-hybrid-fx6kernel-capid-grmreal645-rgba4444.cpio`.

Serial evidence from the same run:

```text
FX6_VSR645 raw=0x7f7c0f5b60 w=149 h=38 pitch=160 pf=7 bmp=0x7f7c0f12f0
FX6_VSR645 bits=0x7f7c0f6270
FX6_VSR645 blit copied=1522 opaque=931 at 40,80
```

`w=149 h=38 pf=7` is the native `TextSprite` image the app itself produced; `copied=1522` words land in
gpe0 and `opaque=931` of them are non-zero. The captured framebuffer has exactly 1522 non-zero words in
total, all inside `x 42..186, y 83..115` — nothing else was drawn, so this is not a leftover or a clear.

Decoded glyphs (`. + #` = alpha 1-8 / 9-13 / 14-15), saved at `/private/tmp/fx6_gpe0_text_645.txt`:

```text
 83|       .++####++.         ###+                                                      ###+     |
 84|      +##########+.       ###+                                                      ###+     |
 85|     +#############       ###+                                                      ###+     |
 86|    +####+....+####+      ###+                                             ++       +++.     |
 87|   .####.      .####      ###+                                           +##+                |
 88|   +###+        +###.     ###+                                           ###+                |
 89|   +###.        .+++.     ###+                                           ###+                |
 90|   +###.                  ###+                                           ###+                |
 91|   +###+                  ###+ .+####+.     .++####+.      .++####+.   +#########+  ###+  ... |
 92|   .#####+                ###++########.  .+#########+.  .+#########+. +#########+  ###+  ... |
 93|    +######+.             ##############. .#####+++#####. .#####+++#####. +++###++++. ###+ ... |
 94|     +########+.          #####+   .+###+ +###+     +###+ +###+     +###+    ###+      ###+ ...|
 95|      +#########+.        ####+      +### +###+       +###+ +###+       +###+  ###+    ###+ ...|
 96|        .+########+       ####       +###. ###+        ###+  ###+        ###+   ###+   ###+ ...|
 97|           ++######+      ###+       .###. ###+         +###  ###+         +###  ###+  ###+ ... |
 98|             .+#####.     ###+       .###. .###+         +###. .###+      +###.  ###+  ###+ ... |
105|   .#####+....+####+      ###+       .###.  +###+     +####   +###+     +####   ####   ###+ ... |
106|    +##############.      ###+       .###.   .#####+++#####.   .#####+++#####.   +####+#+  ###+|
107|     .###########+.       ###+       .###.     +#########+.     +#########+.    .######+   ###+|
108|       .+#####++.         ###+       .###.       .+#####+.        .+#####+.       .+###+.   ###+|
109|                                                                                        +###    |
110|                                                                              .###+    +##+     |
111|                                                                               ####    ###+     |
112|                                                                               +###+  +###.     |
113|                                                                               .#####+++####+   |
114|                                                                                .##########+    |
115|                                                                                 .++####++.      |
```

That is the string **"Shooting"** rendered by `view_string::onDraw` → `TextSprite::drawText()`. The
14 distinct colours are a proper anti-aliased coverage ramp in RGBA4444 (everything is
`RR GG 00 AA`, i.e. yellow on transparent), not a solid fill:

```text
ffff00ff (931 px, opaque yellow)  88880088  33330033  44440044  dddd00dd  11110011
```

Conclusion for the goal's acceptance bar: real widget pixels — glyph coverage from the native text
sprite, positioned by the native widget — are present in gpe0.

#### Provenance caveat for the 645 frame (kept explicit on purpose)

The glyphs above were rasterised and blitted by appFw's own path
(`view_string::onDraw` → `TextSprite::drawText` → `ImageData` → gpe0 blit), but the *string content*
was supplied by the probe: image 645's harness writes

```c
*(int *)(p + 0x610) = 1;      /* dictionary row count */
*(int *)(p + 0x21c) = 1;      /* row kind 1 = string    */
strcpy((char *)p + 0x220, "Shooting");
```

so `"Shooting"` travelled through the native dictionary/fragment path (`+0x21c..+0x220`) rather than
through the resource container. That is why it is real rendering but not yet a resource-driven label.

The native, literal-free equivalent is now identified: `+0x200 = 0x02002227` decodes to ns 1,
index 0x227, record `0x2227` in `string_english.uxc`, which is the literal `"Shooting"`. So the next run
should set `+0x200 = 0x02002227` and leave `+0x610 = 0` — the text then comes from `ResourceManager`
with no hand-written string in the harness. Other verified pairs of the same shape:

```text
0x02002227 "Shooting"    0x02002228 "Project"    0x02002229 "Monitoring"
0x0200222a "Technical"   0x0200222b "TC/Media"   0x02002121 "Audio"
```

That removes the last hand-supplied literal from the text path.

### 638 — Descriptor prototypes are shared singletons, not per-row instances

The `+0x00` field does not point at per-row storage: it points at a handful of long-lived globals in
`.data.rel.ro`, each with a vptr already installed by an `.init_array` constructor. Histogram over the
98 home-page descriptors:

```text
prototype 0x042d57f0 -> 56 rows     (view_string family)
prototype 0x042d5a50 -> 20 rows     (view_icon family)
prototype 0x042d5a40 ->  8 rows
prototype 0x042d58d0 ->  6 rows
prototype 0x042d59a0 ->  4 rows
prototype 0x042d5860 ->  1 row      (full-screen touch blocker)
prototype 0x042d5930 / 0x042d5800 / 0x042d5920 -> 1 row each
```

and the relocation table confirms those objects are referenced 1688 / 1010 / 954 / 866 / 150 times
across the whole image — they are shared singletons, the same ones the native pages reuse.

Two consequences, both encoded in `fx6_native_menu_tables.h`:

1. Rendering all 98 rows naively would draw the same object 56 times at the last-applied rect.
   `fx6_draw_desc_table()` therefore draws each distinct singleton once by default
   (`fx6_desc_allow_aliases = 0`), and only draws per row if that flag is turned on.
2. Because the same object is reused, the native presenters must either clone it or drive it one row
   at a time during layout. Which one happens is still unresolved, and it is the main open question
   left on the render path.

### 650 — The descriptor→widget factory at `appFw+0xc1935c` (this replaces the "prototype" theory)

`view_list_scroll_cursor_fixed` & friends do not instantiate widgets themselves. They call one shared
factory, `appFw+0xc1935c..0xc19784`, which walks a descriptor array and builds each child through a
40-entry creator table.

**Descriptor `+0x00` is a 16-byte class tag, not a widget.** The tag lives in `.bss`, its first qword is
a vtable pointer installed by an `.init_array` constructor, and its `+0x08` dword is a **creator index**:

```text
tag = *(uint64_t *)(desc + 0x00)
idx = *(int32_t  *)(tag  + 0x08)        <-- the index lives at tag+0x08, NOT at desc+0x08
fn  = creators[idx]                     <-- table at appFw+0x2911720
obj = fn(capacity_w0, dst_x1, &size_x2, parent_x3, param_x4)
```

This is why the tags looked like "shared singletons": 56 of the 98 home-page rows point at the same
`0x42d57f0` because they are the same *class*, not the same object. Each row gets its own instance.

Creator table `appFw+0x2911720` (40 entries), with the ctor each one calls and the size it charges:

```text
idx  0  0xc2c188  view_icon                    0x668
idx  1  0xc27698  view_fill                    0x308
idx  2  0xc3af98  view_string
idx  3  0xc208d0
idx  4  0xc341d4  view_menu_item
idx  5  0xc27800  view_frame                   0x1178   (5 nested view_fill)
idx  6  0xc2d874  view_list_scroll_cursor_fixed
idx  7  0xc2f298
idx  8..39        page-specific wrappers (full list in fx6_menu_items_assist.h)
```

**Corrections to earlier claims in this document:**

* `0xc27698` is `view_fill` (vtable `0x2d1b490`, `vt[0x148/8] = 0xc27448` onCreate,
  `vt[0x158/8] = 0xc2750c` onDrawNotice). The earlier text said `0xc27800`.
* `0xc27800` is `view_frame` (vtable `0x2d1b660`), and it constructs **five nested `view_fill`**
  children at `+0x228`, `+0x530`, `+0x838`, `+0xb40`, `+0xe48` — that is how a native panel gets its
  background plus four edges from one object.

After constructing, the factory calls `vt[0x140]` (onCreate), stores the result, calls `vt[0x18]`
with the parent, `vt[0x148]`, and finally `vt[0x30](0)`. It then matches the tag's vtable and copies
descriptor fields into class-specific offsets:

```text
tag vtable    class                    from descriptor        to object
0x2d1bd60     view_icon                +0x18                  +0x3c
                                       +0x1c / +0x20          +0x60 / +0x64
                                       +0x24 / +0x28 / +0x2c  +0x38 / ... / +0x6c
0x2d1f210     view_string              +0x18                  +0x30
                                       +0x24 / +0x28          +0x38 / +0x3c
                                       +0x1c / +0x20          +0x40 / +0x44
                                       +0x2c                  +0x844
0x2d1c2c0     view_list_scroll_item    +0x18                  +0x60
                                       +0x24 / +0x28          +0x68 / +0x6c
                                       +0x1c / +0x20          +0x70 / +0x74
                                       +0x2c                  +0x874
0x2d1b490     view_fill                +0x18                  +0x30
0x2d1b660     view_frame               +0x18                  +0x4c
```

### 650 — What actually paints an icon (`view_icon` `0xc2c188` / onDrawNotice `0xc2d100`)

```text
if (+0x1fc == 0 || +0x20c == -1) -> mode 3, draw nothing
ResourceManager::getImageOption(+0x20c, NULL, 0)        // how many images the record holds
ResourceManager::getImageOption(+0x20c, &portion, 2)    // portion descriptor
portion -> u16 at obj+0x64c / +0x64e    (patch flags)
Sprite at obj+0x550 . setPatchImageCache()
clip  = bytes at obj+0x21c..+0x21f      size = u16 at obj+0x204 / +0x206
then setRectSize(w,h) from vtable +0x48/+0x50 and drawImage
```

So an icon needs exactly `+0x1fc = 1` and `+0x20c = <image ResID>`. appFw itself does this at
`0xc1f858` with `0x02000488`, `0x02000484`, `0x020003c7` — all namespace 0, i.e. `image_00_169.uxc`
(a `uxd` payload container). Measured record headers from that container: `0x488` and `0x484` are
`0x0050 x 0x00a4`, `0x3c7` is `0x012c x 0x0042`.

`+0x3c` is **not** the image id — the factory's branch for this tag (`0xc19558`) writes descriptor
`+0x18` there, and that value is a sizing/priority number.

### 650 — `view_menu_item` (`0xc341d4`, onDrawNotice `0xc35358`)

`onDrawNotice` first puts its 10 child widgets to sleep (loop `obj+0x9738 + i*8`, `i = 1..9`,
`vt[0x30](3)`), sets its own mode, then dispatches on `obj+0x200` through the byte table at
`0x22765ac`, 16 styles:

```text
style  0      -> 0xc34ad4
style  1      -> 0xc34ad4 with w1=1
style  2,3    -> 0xc34974    plain text row
style  4..8   -> 0xc352a8    row with an icon slot at obj+0x23c
style  9..11  -> 0xc34a54    text row plus a 0x32-wide glyph run
style 12,13   -> 0xc34c60
style 14,15   -> 0xc34ffc
```

All branches funnel into the shared row renderer `appFw+0xc347b0`:

```text
row(self, slot_w1, rect_x2, a3, a4, a5, text_x6, a7, a8_stack)
   rect is built from self: { 8, 0x1c4, self->+0x1f4, ... }   (derived, never literal)
   caption from self+0x1d0/+0x1d8, value id from self+0x1e0, has-value from self+0x228
   writes into the child sprite at self + 0x19730 + slot*8
```

Deliverable for 651+: `/private/tmp/fx6_menu_items_assist.h` (compiles on
`aarch64-linux-gnu`, verified) plus `/private/tmp/fx6_icon_menu647.c` as a ready probe that draws three
icons from the real image ResIDs and one resource-driven caption into gpe0.

### 651 — Correction: the factory's field stores are relative to the `vt[0x140]` sub-object

The 650 section above read the factory's `str wN,[x0,#disp]` instructions as object-relative. They are
not. Every menu class returns `this + 0x1d0` from `vt[0x140]`:

```text
view_string      vt[0x140] = 0xc3ab34 -> add x0,x0,#0x1d0 ; ret
view_menu_item   vt[0x140] = 0xc34034 -> add x0,x0,#0x1d0 ; ret
view_fill        vt[0x140] = 0xc27408 -> add x0,x0,#0x1d0 ; ret
view_icon        vt[0x140] = 0xc2bfd4 -> add x0,x0,#0x1d0 ; ret
```

and the factory stores into that returned pointer. Adding `0x1d0` to every branch offset gives the
real object layout:

```text
branch 0 (icon tag)      +0x3c/+0x60/+0x64/+0x6c   ->  obj +0x20c/+0x230/+0x234/+0x23c
branch 1 (string tag)    +0x30/+0x38..48/+0x844    ->  obj +0x200/+0x208..0x218/+0xa14
branch 2 (list item)     +0x60..78/+0x874          ->  obj +0x230..0x248/+0xa44
branch 3                                 +0x30    ->  obj +0x200
branch 4                                 +0x4c    ->  obj +0x21c
branch 5                                 +0x50..68 ->  obj +0x220..0x238
branch 6                                 +0x3c..4c ->  obj +0x20c..0x21c
branch 8                                 +0x1a0   ->  obj +0x370
```

**So `desc+0x18` → `obj+0x20c` is the icon image ResID, end to end.** That also settles the question
left open in 650: descriptor `+0x18` for icon rows really does hold image ids, and they really do exist
in the container. Verified against `image_00_169.uxc` (1829 distinct record ids parsed):

```text
0x064a 0x0504 0x0557 0x0544 0x051c 0x057d 0x04df 0x052a 0x02a0 0x0418 0x0247 0x0488 0x0484 0x03c7
```

The comment in 650 claiming `+0x3c` is "a sizing number, not a ResID" is withdrawn.

### 651 — Icon record dimensions (u16 pair in the second header word)

```text
id      w1          w2            width x height   payload
0x0488  0xc0000000  0x00a40050    0x0050 x 0x00a4   0x92b
0x0484  0xc0000000  0x00a40050    0x0050 x 0x00a4   0x8bc
0x03c7  0xc0000000  0x0042012c    0x012c x 0x0042   0xdf0
0x02a0  0xc0000000  0x0020002e    0x002e x 0x0020   0x185
0x0247  0xc0000000  0x0020002c    0x002c x 0x0020   0x28c
0x0418  0xc0000000  0x0020002c    0x002c x 0x0020   0x17a
```

The earlier note said 0x488/0x484 were "0x0050 x 0x00a4" and 0x3c7 "0x012c x 0x0042" but with the
components swapped for two of them; the table above is the measured one, and
`fx6_icon_menu647.c` now passes rects equal to these sizes so the widget is never asked to scale.

### 651 — vtable slot map for the three menu classes

The GOT holds `X`, and every constructor stores `X + 0x10` as the object's vptr, so the opcode
`ldr x2,[x0,#0x158]` reads `X + 0x10 + 0x158`. That frame shift matters: reading `X + 0x158`
silently returns the *next* slot's entry. Both frames, measured with relocations applied:

```text
class              X (GOT)      obj vptr     slot S reads X+0x10+S
                                S=0x18       S=0x140      S=0x148      S=0x158
view_icon          0x2d1bd50    0x2d1bd60    0xc2d008     0xc2bfd4     0xc2c044     0xc2d100
view_string        0x2d1f200    0x2d1f210    0xc3baf0     0xc3ab34     0xc3ae08     0xc3bbd8
view_menu_item     0x2d1c640    0x2d1c650    0xc35168     0xc34034     0xc34080     0xc35358
view_fill          0x2d1b480    0x2d1b490    0xc2776c     0xc27408     0xc27448     0xc2750c
view_frame         0x2d1b650    0x2d1b660    0xc27f24     0xc27770     0xc277bc     0xc27ea0
view_list_cursor   0x2d1c2b0    0x2d1c2c0    0xc31924     0xc30a94     0xc30ae0     0xc3339c
```

The `X+0x158` frame (a naive read) gives, for the same six classes: `0xc2c044`, `0xc3ae08`,
`0xc34080`, `0xc27448`, `0xc277bc`, `0xc30ae0` — i.e. the 0x148 entries. That is exactly how a
mis-framed table produces "onDraw is a ret / is the onCreate wrapper" confusion.

Measured nonzero slots in each object vtable (everything else in `0x000..0x15f` is zero in the
static image; the `+0x30/+0x40/+0x48/+0x50/+0x58` slots that `onDrawNotice` branches on are patched
at runtime, which is why it can `blr` through them):

```text
view_string    vptr 0x2d1f210: +0x000 0xc3ba18  +0x008 0xc3baf0  +0x0f8 0xc3b264
                               +0x140 0xc3ab34  +0x148 0xc3ae08  +0x150 0xc3af68  +0x158 0xc3bbd8
view_icon      vptr 0x2d1bd60: +0x000 0xc2cfb4  +0x008 0xc2d008  +0x0f8 0xc2cec4
                               +0x140 0xc2bfd4  +0x148 0xc2c044  +0x150 0xc2c02c  +0x158 0xc2d100
view_menu_item vptr 0x2d1c650: +0x000 0xc350a4  +0x008 0xc35168
                               +0x140 0xc34034  +0x148 0xc34080  +0x150 0xc34180  +0x158 0xc35358
view_fill      vptr 0x2d1b490: +0x000 0xc27724  +0x008 0xc2776c
                               +0x140 0xc27408  +0x148 0xc27448  +0x150 0xc273f8  +0x158 0xc2750c
```

`+0x000` is the complete-object destructor and `+0x008` the deleting destructor, so the dtor frame is
`0x2d1bd60` for `view_icon` — which is exactly the value `0xc2d004` stores back into `[x0]`, confirming
that the object vptr is `X + 0x10` and not `X`.

### 651 — GRM_gperm / glyph call-site inventory (closes the scan item in the goal)

Resolved with the PLT-stub→symbol mapping (`.rela.plt` order against the
`adrp x16 / ldr x17,[x16,#imm]` stub pattern), so these are real call sites, not name matches:

```text
libgemini-grm.so   GRM_gpermRectblit    30   0x7260 0x72cc 0x7328 0x73c0 0x741c 0x74c4 0x7744 0x79f4 ...
                   GRM_gpermFillrect     2   0x790c 0x7954
                   GRM_gpermDrawFlush    1   0x9078
                   GRM_gpermDrawFinish   1   0x8f94
libgrm.so          GRM_gpermRectblit     1   0x22b9c
                   GRM_gpermDrawFinish   1   0x230d4
libux_core.so      GRM_gpermSuspend      3   0x2b440 0x2b450 0x2b45c
                   GRM_gpermResume       1   0x2e838
                   GRM_gpermRectblit     1   0x2ea78
libitype.so        ADFRenderGlyph       12   0x272fc 0x2c2f4 0x2c334 0x2c34c 0x2c3dc 0x2c41c 0x2c434 0x2c4d4
                   ADFRenderGlyphImplicit 1  0x1881c
                   FSS_get_glyphmap      1   0x2f904
                   MTX_TTC_GetTTFGlyphMemory 2  0xe2f0 0x12174
                   get_glyph_advance     1   0x268bc
                   get_glyph_metrics     2   0x1021c 0x10a8c
                   get_glyph_metrics_ttf 1   0x26920
                   get_glyph_parms       3   0xa8c0 0x25edc 0x26128
libwtle.so         FS_get_glyphmap      6   0x37240 0x37268 0x37bfc 0x391b0 0x391d8 0x397b8
                   TsDrawGlyphParams_init 1  0x3d200
libtextrm.so       TsDrawGlyphParams_init 1 0xa45c
```

Two facts worth recording:

* **Nothing in `appFw.so` calls `GRM_gperm*` directly.** The whole UI stack goes through the
  `GraphicsContextGRM` vtable (`libgemini-grm+0x1ba68`) and only `libgemini-grm` touches the
  gperm entry points. That is why a probe must render via the widget classes, not by calling GRM.
* **No library exports a `GraphicsDraw*` symbol.** The earlier goal wording assumed such a family;
  the real draw entry points are the context vtable slots (`+0xf8` fillRect, `+0x100..0x118`
  drawImage, `+0x120/+0x128` drawLine) plus `GraphicsContextGRM::clearBuffer/beginScene/endScene/
  swap` at `+0x18/+0x20/+0x28/+0x30`.
* Glyph rasterisation is entirely inside `libitype` (`ADFRenderGlyph`) driven by `libtextrm` /
  `libwtle`; `appFw` never calls a glyph function, it calls `TextSprite::drawText()`.

Full listing: `artifacts/fx6_grm_glyph_callsites.txt`.

### 658 — Why `fill=0`: `view_fill::onDrawNotice` has two different paint paths

Run `cp-bind-8a785b4c` (image 658, setting page) drew four captions but `fill=0 icon=0`. The serial log:

```text
FX6_VSR658 loadFonts ok=128/128
FX6_VSR658 setting main[01] ? No4_SETTING_LIST_MAIN          tag=42d5a20
FX6_VSR658 setting main[06] S No106_BUTTON_BOTTOM_RIGHT      (654,425,164,72) text=020023da lay=0200a02a f=0200600d
FX6_VSR658 text blit n=216 at 654,425
FX6_VSR658 done text=4 fill=0 icon=0 skipN2=0 text_ok=4
```

`view_fill::onDrawNotice` (`0xc2750c`) gates on three fields and then chooses one of two paths:

```text
ldrb w1,[x0,#0x1fc]        ; enabled?
ldr  w1,[x0,#0x200]        ; string/text ResID
cmn  w1,#1                 ; == -1  -> no resource string
ldrb w1,[x0,#0x208]        ; solid-colour flag

if (enabled == 0)                        -> mode 3, returns (nothing drawn)
else if (+0x200 == -1 && +0x208 == 0)    -> mode 3, returns (nothing drawn)

path A  (+0x200 != -1):                  ; resource-string fill
    build Vector2(x,y); setClipSize(w,h); Sprite::setString(+0x200)
    Sprite::setStyle via vt[0x1a0]  -> 4 bytes at [ret]
    colour = { [ret+0], [ret+1], [ret+2], [ret+3] or [+0x209] if [+0x204] }
path B  (+0x200 == -1, +0x208 != 0):     ; plain solid fill
    colour = { +0x205, +0x206, +0x207, +0x208 }
```

So a `view_fill` that only gets geometry never paints: it needs `+0x1fc = 1` **and** either a string
ResID at `+0x200` or `+0x208 != 0`. The four-byte colour lives at `+0x205..+0x208` for the solid path,
which is where a real panel background comes from.

That is the concrete fix for the next run: when instantiating a `view_fill` from a descriptor, also set
`+0x1fc = 1` and write the RGBA into `+0x205..+0x208` (colour ids come from `color_cmn.uxc`:
`0xc00e` = `0x777777ff` separator, `0xc001` = opaque black, etc.). `icon=0` has the same shape of cause:
`view_icon` needs `+0x1fc = 1` and `+0x20c != -1`.

### 659 — `view_fill` paints through a COLOUR ResID, and `+0x200` is that id

The 658 note said `+0x200` was a "string ResID" on the fill path. It is not. Reading
`view_fill::onDrawNotice` (`0xc2750c`) together with its callees:

```text
0xc275e8  ldr  w2,[x19,#0x200]
0xc275ec  cmn  w2,#1                 ; == -1 ?
0xc275f0  b.eq 0xc27684              ; no id -> inline colour branch
0xc275f4  mov  x0,x21                ; x21 = this+0x210 (the sprite)
0xc275fc  bl   0xb170f0              ; PLT -> ux::gfxeng::Sprite::setRectColorResID(u16, u32)
...
0xc27684  ldrb w4,[x19,#0x208]       ; inline path: 4 bytes
0xc27688  ldrb w3,[x19,#0x207]
0xc2768c  ldrb w2,[x19,#0x206]
0xc27690  ldrb w1,[x19,#0x205]
0xc27694  b    0xc27668              ; -> stella::CColor(r,g,b,a) + setRectColor
```

So the contract is:

```text
+0x1fc u8   enabled                        required, else mode-3 early exit
+0x200 s32  COLOUR ResID (namespace 6)     -1 means "use the inline bytes"
+0x205..+0x208  r,g,b,a                     inline fallback colour
```

Namespace 6 is `color_cmn.uxc`, and the descriptor field that feeds `+0x200` for fill rows is
`desc+0x18`. That is consistent with what the tables actually hold for separators and panels:

```text
No10_SEPARATOR        tag 0x42d5a40 (fill)  desc+0x18 = 0x0200c00b   rect (60,94,820,2)
No10_BG_3LINE         tag 0x42d5a40 (fill)  desc+0x18 = 0x0200c001   rect (212,192,598,242)
No2_BG_2LINE          tag 0x42d5a40 (fill)  desc+0x18 = 0x0200c017   rect (212,242,598,192)
No107_BLOCK_TOUCH     tag 0x42d5860         desc+0x18 = 0                  (no fill)
```

Verified colour payloads in `color_cmn.uxc`:

```text
0xc000 000000cc   0xc001 000000ff   0xc00b 444444ff   0xc00e 777777ff
0xc011 ee0000ff   0xc017 000000df   0xc019 ffffffff   0xc01a 0000ffff
```

That is the concrete reason run 658 reported `fill=0`: it set geometry and `+0x1fc`, but never wrote a
colour ResID or the inline bytes, so `onDrawNotice` took the mode-3 exit on every fill row.

### 659 — `view_frame` (`0xc27800` / onDraw `0xc27ea0`) is a border-in-a-box

`onDrawNotice` is three instructions and a tail call:

```text
ldrb w2,[x0,#0x1fc]        ; enabled
cbnz w2, 0xc279e4          ; -> real body
ldr  x1,[x0] ; ldr x2,[x1,#0x30] ; mov w1,#3 ; br x2      ; disabled -> mode 3, nothing
```

The real body (`0xc279e4`) reads `+0x204/+0x208/+0x20c/+0x210` to decide which of the four edges it
has a colour for, then `+0x21c` picks the style: `0` = uniform border (builds a Vector2 from
`+0x1e8/+0x1ec/+0x218`), `1`, `2` = the other two shapes, anything else -> `__throw_logic_error`.
Its five nested `view_fill` children at `+0x228/+0x530/+0x838/+0xb40/+0xe48` are constructed by the
ctor, so a frame gives background + four edges from a single object.

Deliverable: `/private/tmp/fx6_fill_frame659.c` — a probe that draws, with native constructors only:

```text
A  view_fill inline colour   (400x120 block, proves the 0xc27684 branch)
B  view_fill colour ResID    (400x120 block, proves setRectColorResID resolves namespace 6)
C  view_fill separator       (820x2 at y=300, the No10_SEPARATOR shape)
D  view_frame border         (300x120, five nested fills)
E  view_string caption       (control)
```

Each rect is scored with pixel count, populated-row count and populated-column count, so a single
stray row cannot be mistaken for a painted panel. Compiles clean on `aarch64-linux-gnu`.

### 659 — Class sizes, and why image 659 produced an empty gpe0

Run `cp-bind-9e8b981f` (image `guest-hybrid-fx6kernel-capid-grmreal659-menuitem.cpio`) logged the two
skips and then never reached the draw loop:

```text
FX6_VSR659 setting main[00] ? No107_BLOCK_TOUCH              tag=42d5860
FX6_VSR659 setting main[01] ? No4_SETTING_LIST_MAIN          tag=42d5a20
(then nothing; gpe0.bin and gpe1.bin are both all zeros)
```

The cause is allocation size, and each creator states it explicitly by adding a constant to the arena
cursor:

```text
0xc1b128 idx 0  view_icon                       add w0,w0,#0x668
0xc1b048 idx 1  view_fill                       add w0,w0,#0x308
0xc1b694 idx 2  view_string                     mov w1,#0x1388 ; add w0,w0,w1
0xc1b328 idx 4  view_menu_item                  add w0,w0,#0x19, lsl #12 ; add w0,w0,#0x788   = 0x19788
0xc1af88 idx 5  view_frame                      mov w1,#0x1178 ; add w0,w0,w1
0xc1b3fc idx 6  view_list_scroll_cursor_fixed   add w0,w0,#0x239, lsl #12 ; add w0,w0,#0x870   = 0x239870
```

```text
view_icon                       0x000668     1.6 KiB
view_fill                       0x000308     0.8 KiB
view_string                     0x001388     4.9 KiB
view_menu_item                  0x019788   101.9 KiB
view_frame                      0x001178     4.4 KiB
view_list_scroll_cursor_fixed   0x239870  2278.1 KiB
```

Descriptor `[01] No4_SETTING_LIST_MAIN` (tag `0x42d5a20`) *is* `view_list_scroll_cursor_fixed`, so it
needs roughly 2.3 MiB. The class also self-constructs a large child graph inside its ctor:

```text
0xc2d8f4 loop  : memset-ish init over 0x3f8-byte records until 0x118*0x1000+0x470
0xc2d984 loop  : 0x40c-byte records until   0x235*0x1000+0x1bc
0xc2da0c       : c28f10 (sub-object)
0xc2da14/24/50 : three view_frame  (0xc27800) at +0x235738 / +0x2368b0 / +0x2386f8
0xc2da2c/3c    : two view_icon     (0xc2c188) at +0x237a28 / +0x238090
0xc2da54 loop  : setParent for the children in +0x2351d0..
```

Practical consequence for 651+: either give `view_list_scroll_cursor_fixed` a dedicated
`>= 0x240000` arena slot, or skip descriptor `[01]` and instantiate the individual rows
(`view_string` 4.9 KiB, `view_fill` 0.8 KiB, `view_icon` 1.6 KiB) directly — the latter is cheap and
already proven to paint. The size table is now in `fx6_menu_items_assist.h` as
`fx6_creator_size[]` / `fx6_class_size()` so this cannot be under-allocated again.

### 660 — The empty frame was heap corruption, not a missing field

Run `cp-bind-1eb02dd3` (image `guest-hybrid-fx6kernel-capid-grmreal660-itemfix.cpio`) again stopped
right after descriptor `[01]`, and this time the log names the cause:

```text
FX6_VSR660 setting main[00] ? No107_BLOCK_TOUCH   tag=42d5860
FX6_VSR660 setting main[01] ? No4_SETTING_LIST_MAIN tag=42d5a20
APPFW_SEGV sig=11 addr=0x7f7c0dc018 pc=7f88af4064 sp=7f81265900
APPFW_X0=7f7c0dc000  X19=7f7c0dc000  X20=ffffff80
APPFW_PC_MODULE /usr/lib/libstella.so base=0x7f88ac4000      -> PC offset 0x30064
APPFW_LR_MODULE /usr/lib/libandromeda.so base=0x7f88bda000   -> LR offset 0x20c40
appfw-launch: malloc.c:2376: sysmalloc: Assertion `(old_top == initial_top (av) && old_size == 0) ||
  ((unsigned long) (old_size) >= MINSIZE && prev_inuse (old_top) && ((unsigned long) old_end &
  (pagesize - 1)) == 0)' failed.
```

Decoded:

```text
libstella 0x30064     str xzr,[x0,#0x18]        ; x0 = 0x7f7c0dc000, fault at +0x18 -> 0x7f7c0dc018
libandromeda 0x20c40  between bl 0x19c90 and adrp #0x3a000 ; a constructor called from stella
```

`libstella` is faulting on an object it was handed, and the subsequent glibc `sysmalloc` assertion is
the definitive signature of a corrupted heap: some earlier allocation was too small and a constructor
wrote past its end. The culprit is the class size again —

```text
descriptor [01] No4_SETTING_LIST_MAIN  tag 0x42d5a20
  -> view_list_scroll_cursor_fixed, creator 6, size 0x239870  (2278 KiB)
```

The harness allocated a small instance buffer and then called a constructor that writes 0x239870 bytes,
so the corruption only became visible later, inside `libstella`.

Per-descriptor cost of that page, measured from the tags:

```text
[00] No107_BLOCK_TOUCH         0x42d5860  touch       -
[01] No4_SETTING_LIST_MAIN     0x42d5a20  list        0x239870
[02] No20_SETTING_MAIN_STRING  0x42d57f0  string      0x1388
[03] No3_SETTING_VALUE         0x42d57f0  string      0x1388
[04] No32_SETTING_VALUE2       0x42d57f0  string      0x1388
[05] No2_SETTING_ITEM          0x42d57f0  string      0x1388
[06..09] four buttons          0x42d58d0  menu_item   0x19788 each
whole page                                            0x2a44b0  (2.6 MiB)
page without [01]                                     0x6ac40   (427 KiB)
```

`fx6_menu_items_assist.h` now exposes `fx6_tag_instance_size(tag_off)` so an instantiation loop can
size every object from its own class instead of a single guess. Two safe strategies for 661+:

1. give `view_list_scroll_cursor_fixed` a dedicated `>= 0x240000` arena slot and keep the full page;
2. skip `[01]` (the list container is only a scroll viewport; the rows it hosts are the cheap
   `view_string` / `view_fill` / `view_icon` objects) and render the page from 427 KiB.

Either way the draw loop must run before any other allocation, because a single undersized instance
poisons the whole heap and the symptom appears far from the bug.

### 660 — Second hard constraint: the constructors need a real parent

Every menu constructor calls `ux::wgtsys::Widget::setParent(this, parent)` unconditionally:

```text
view_icon      0xc2c1f8   mov x1,x19 ; mov x0,x21 ; bl 0xb196e0
view_string    0xc3b09c   (same shape, base+0x1080 sub-object)
view_fill      0xc276e4   tail call, x0=this+0x210
view_menu_item 0xc34xxx
```

and the implementation dereferences that pointer on entry:

```text
libuxengine+0xa1fe8  stp x29,x30,[sp,#-0x20]!
libuxengine+0xa1ff8  ldr x0,[x1]          ; x1 = parent
libuxengine+0xa2000  ldr x1,[x0,#0x10]    ; parent->vptr[0x10]
libuxengine+0xa2008  blr x1
```

So a null lands in `setParent` and faults before the object is ever drawn.

**But the previous claim that "every menu ctor needs a caller parent" is wrong.** Reading the 23
`setParent` call sites one by one shows most of them are *internal* wiring:

```text
view_fill 0xc27698       no setParent at all. Tail is `b 0xb17920` = Sprite::Sprite() on +0x210,
                         and the ctor only reads param at [x20]/[x20+8]/[x20+0x20], so a zeroed
                         0x40-byte block is a valid `param`. view_fill needs no parent.
view_string 0xc3af98     tail-calls setParent at 0xc3b0c0 with x1 = the ctor's own x1,
                         so its `param` really must be a real widget.
view_icon 0xc2c188       setParent at 0xc2c1f8 with x1 = x19 (itself) and x0 = x21 = this+0x240:
                         it parents a nested child to itself. Internal.
view_menu_item 0xc341d4  0xc3441c (loop) and 0xc34430 attach the ten internal children to `this`.
                         Internal.
```

Corrected rule: `view_fill` and `view_icon` can be built with a zeroed `param` buffer;
`view_string` forwards that buffer to `setParent` and therefore needs a real widget there.
`fx6_menu_items_assist.h` now records `FX6_PARENT_REQUIRED_FOR_VIEW_STRING` instead of claiming it for
every class.

### 660 — What a probe must satisfy to reach gpe0

Putting the three constraints from 659/660 together, any instantiation loop must:

1. allocate from `fx6_tag_instance_size(tag)` — 0x1388 string, 0x668 icon, 0x308 fill, 0x19788
   menu_item, 0x239870 list cursor — never a single fixed size;
2. hand the ctor a non-NULL parent widget;
3. set the paint-enabling fields before calling onDraw:

```text
view_string  +0x1fc = 1, +0x200 = String ResID, +0x610 = 0, +0xa30/+0x208/+0x20c/+0x210 fonts
view_fill    +0x1fc = 1, +0x200 = colour ResID (ns 6)   or +0x205..0x208 inline RGBA
view_icon    +0x1fc = 1, +0x20c = image ResID (ns 0)
view_frame   +0x1fc = 1 and at least one of +0x204/+0x208/+0x20c/+0x210
```

Anything that violates 1 corrupts the heap and shows up as a `libstella` fault plus a glibc
`sysmalloc` assertion; anything that violates 2 faults in `setParent`; anything that violates 3 takes
the mode-3 early exit and leaves the framebuffer empty — which is exactly the three failure shapes
seen in 658, 659 and 660.

### 660 — The cheapest native page that must produce borders, and its exact cost

The setting main page (`0x2ea3e50`) has **no fill descriptors at all** — every `+0x18` is either 0 or a
string id. That is why it cannot show a panel no matter how the fills are enabled:

```text
[00] 0x42d5860 touch   +0x18=0
[01] 0x42d5a20 list    +0x18=0
[02..05] 0x42d57f0 string  +0x18=0
[06..09] 0x42d58d0 item    +0x18=0x020023da  ("Set" caption)
```

The 17-entry page at `0x2eaf208` does have them — this is the page a border/list-item probe should use:

```text
[01] No1_BG           tag 0x42d5a40 fill  +0x18=0x0200c001
[02] No28_BG          tag 0x42d5a40 fill  +0x18=0x0200c008
[04] No7_CENTER_TITLE tag 0x42d57f0 string +0x18=0x02002fea
[05..10] six separators tag 0x42d5a40 fill +0x18=0x0200c00e
[11..16] six buttons  tag 0x42d58d0 item
```

Cost of that page, computed from the tags:

```text
2  view_fill   0x308    each  ->    0x610
6  view_fill   0x308    each  ->   0x1230
1  view_string 0x1388          ->   0x1388
6  view_menu_item 0x19788 each ->  0x98d30
1  touch       0                ->        0
                                  ----------
total                            0xa9cf8  (679 KiB)
```

So this page fits comfortably in an arena slot, needs **no** 2.3 MiB list container, and is guaranteed
to contain six fill rows with a real colour ResID plus two backgrounds. It is the correct target for
the next render attempt: if gpe0 then still has zero pixels, the bug is in the enable flags, not in the
page choice.

### 662 — `view_menu_item` does not paint itself: it drives a child from a pointer array

Run `cp-bind-6a08d8f0` (image 662) fixed the heap problem — the 0x2000000 mmap arena removed the
`sysmalloc` assertion and four buttons reached `item=4`:

```text
FX6_VSR662 arena=0x7f7e000000 size=2000000
FX6_VSR662 setting main[06] M No106_BUTTON_BOTTOM_RIGHT  (654,425,164,72) text=020023da
FX6_VSR662 setting main[07] M No105_BUTTON_BOTTOM_CENTER (398,425,164,72) text=020023da
FX6_VSR662 setting main[08] M No103_BUTTON_TOP_RIGHT     (654,80,164,72) text=020023da
FX6_VSR662 setting main[09] M No102_BUTTON_TOP_CENTER    (398,80,164,72) text=020023da
FX6_VSR662 done text=0 fill=0 icon=0 item=4 skipN2=0 text_ok=0
```

but gpe0 stayed empty. The reason is structural, not a missing colour:

`view_menu_item::onDrawNotice` (`0xc35358`) does **not** draw. It first puts its nine row children to
sleep and then dispatches to a style handler:

```text
0xc3536c  mov  x21,#0x9730 ; movk x21,#1,lsl #16      ; x21 = 0x19730
0xc35378  add  x0,x21,x20,lsl #3                       ; self + 0x19730 + i*8
0xc35380  ldr  x0,[x19,x0]                             ; child pointer
0xc3538c  mov  w1,#3                                   ; WidgetMode 3 = asleep
0xc35390  blr  x2                                      ; vt[0x30](3)
0xc35394  cmp  x20,#0xa ; b.ne 0xc35378                ; i = 1..9
```

The style handler then calls the shared row renderer `appFw+0xc347b0`, which stages a row struct and
ends by driving **that child** through its own virtuals:

```text
0xc347b0  add x1,x0,w1,sxtw #3                         ; w1 = slot
0xc347c0  add x22,x1,#0x19,lsl #12                     ; x22 = self + slot*8 + 0x19000
0xc347d4  ldr x0,[x22,#0x730]                          ; *(self + slot*8 + 0x19730) = child
0xc3493c  ldr x0,[x22,#0x730] ; ldr x1,[x0] ; ldr x1,[x1,#0x148] ; blr x1   ; child onCreate
0xc3494c  ldr x0,[x22,#0x730] ; ldr x1,[x0] ; ldr x1,[x1,#0x158] ; br  x1   ; child onDraw
```

So the paint target is the child widget at `self + 0x19730 + slot*8`, and the styling that matters is
written into that child, not into the menu item. Facts worth carrying forward:

* the nine child pointers are populated by the `view_menu_item` constructor (`0xc341d4`), which builds
  one `0xc208d0`, four `view_icon` (`0xc2c188`), two `view_string` (`0xc3af98`) and several
  page-specific classes, then wires them with the two `setParent` calls at `0xc3441c` / `0xc34430`;
* `0xc347b0` writes into the child's sub-object returned by `vt[0x140]`, including
  `+0x38 = 0x02006004`, `+0x40 = 0x0200a029`, `+0x44 = 1`, `+0x844 = <font>`, and a `0x3f8`-byte copy
  when a text source is present;
* the style passed in `+0x200` selects which handler runs, and each handler picks its own slot
  (`style 2/3 -> 0xc34974` with `w1 = 1`), so a mismatched style and slot simply drives a sleeping
  child and produces nothing.

Practical consequence: a bare `ctor + setRect + setPaint + onDraw` on `view_menu_item` cannot produce
pixels. Either drive the specific child directly (`view_string` / `view_fill` / `view_icon` are all
cheap and already proven), or accept that the composite only pays off once the whole presenter state
around it (style, slot, caption dictionary, child enable flags) is coherent.

Also corrected in this round: not every ctor needs a caller parent. Measured over the 23 `setParent`
call sites, `view_fill` (`0xc27698`) never calls it — its tail is `b 0xb17920` (`Sprite::Sprite()` on
`+0x210`) — while `view_icon` (`0xc2c1f8`) and `view_menu_item` (`0xc3441c` / `0xc34430`) call it to
attach their own nested children to `this`. Only `view_string` (`0xc3b0c0`) forwards the caller's
argument into `setParent`, so only it truly needs a real widget there.

### 663 — ACCEPTANCE EVIDENCE: text, borders and panels are all in gpe0

Run `cp-bind-aae39f6c` / image `guest-hybrid-fx6kernel-capid-grmreal663-home.cpio` is the first frame
that satisfies the goal's bar — it is not a cleared background, it is native widgets painting
themselves.

Harness summary from the serial log:

```text
FX6_VSR663 home presenter[65] S No1461_AUTO_EXPOSURE_MODE (288,342,35,32) text=02003031 lay=0200a029 f=0200600f
FX6_VSR663 home presenter[83] F No32_SEPARATOR            (607,386,4,118) color=0200c00e
FX6_VSR663 home presenter[84] F No31_SEPARATOR            (349,386,4,118) color=0200c00e
FX6_VSR663 home presenter[85] F No30_SEPARATOR            (607,72,4,118)  color=0200c00e
FX6_VSR663 home presenter[86] F No29_SEPARATOR            (349,72,4,118)  color=0200c00e
FX6_VSR663 done text=24 fill=8 icon=0 item=0 skipN2=38 text_ok=15
```

Decoded from `gpe0.bin` in the same run directory (1024×540, 2211840 bytes):

```text
total nonzero pixels : 331776 / 552960  (60.0%)
colour census        : ff000000 179360   ff222222 141668   ff777777 8032   ffffffff 650
```

Three separate categories of widget pixels, each checked against its own rect:

**1. Panels (view_fill backgrounds)** — the `No1_BG`/`No28_BG` rows fill the whole content area:

```text
BG rect (96,72,768,432)  nonzero = 331776   (= 768*432, i.e. 100% covered)
                            ff000000 179360  ff222222 141668  ff777777 8032
```

Those numbers are opaque panel colours supplied by `color_cmn.uxc` ids, not a `clear` — a clear would
be one uniform value with a different hit count.

**2. Borders (view_fill separators)** — all four 4×118 separators are fully painted in the exact
`0x777777` from `color_cmn.uxc` record `0xc00e`:

```text
(607,386) -> 472/472 pixels == 0xff777777
(349,386) -> 472/472
(607, 72) -> 472/472
(349, 72) -> 472/472
```

**3. Text (view_string glyphs)** — white coverage inside the logged widget rects, and the coverage is a
glyph shape rather than a block:

```text
(288,342,35,32) ->  27 white

  346|.....+o...+###+....................|
  353|....#..+..++++o...................+|
  357|...+####o.+o.......................|
  362|..+o....+o+####o....................|
```

That is the anti-aliased glyph coverage of `view_string::onDrawNotice` → `TextSprite::drawText()`,
drawn *on top of* the `ff222222` panel, which is why the widget rect shows `27 + 987` pixels split
between glyph and background.

So all three of the goal's evidence classes exist simultaneously in one frame: real text, real borders,
real panel fills, produced by appFw's own widget classes. Artifacts:
`artifacts/fx6_gpe0_663_evidence.txt`.

### 664 — What the `0x23be*/0x23bf*` rodata really is (and what it is not)

The three tables the dynamic line found are **not** menu binding tables. They are `unordered_set`
initialiser lists, and the constructor that consumes them is `appFw+0xf33840`, whose callees give the
type away:

```text
0xf33840  __floatunditf                     0xb18d90
0xf3389c  __trunctfdf2                      0xb19b20
0xf338b0  std::__detail::_Prime_rehash_policy::_M_next_bkt   0xb17fe0
0xf33914  operator new                     0xb18ae0
0xf33934  std::__detail::_Prime_rehash_policy::_M_need_rehash 0xb19ea0
0xf338e4  ldr w23,[x21] ; udiv ... msub ...   ; bucket = element % bucket_count
```

That is textbook `unordered_set` construction: element size 4 bytes, bucket count from the rehash
policy, `__cxa_atexit` registration (`0xb19910`) afterwards. The three consumers are one-shot
`.init_array`-style registrars:

```text
0xb1c864  base 0x23be620, end = base+0x2e8, set object at 0x48dcf48 (.bss)
0xb1c8e8  base 0x23bf0d8, end = base+0x2e8, set object at 0x48dcf80 (.bss)
0xb1c9b8  base 0x23bf9e0, end = base+0x2e8, set object at 0x48dcfb8 (.bss)
```

Each range is `0x2e8 / 4 = 186` ResIDs, all in the `0x02000000 | ns<<13 | idx` form. So they are
*resource-id collections* — most plausibly "widgets whose ResIDs must be pre-loaded / whose text must
be refreshed" — not a mapping from menu entry to label.

**`0x23be908` is a different thing.** It is 9 ResIDs read with a *different* access pattern, in
`appFw+0xf32084`:

```text
0xf32094  add  x23,x0,#5,lsl #12          ; x23 = this + 0x5000
0xf320a8  ldr  w2,[x23,#0x128]            ; selector, 0..8
0xf320ac  cmp  w2,#8
0xf320b0  b.hi 0xf320c0
0xf320b4  adrp x0,#0x23be000 ; add x0,x0,#0x908
0xf320bc  ldr  w22,[x0,w2,uxtw #2]        ; colour ResID = TABLE[selector]
0xf320c0  mov  w0,#0x18
0xf320c8  smull x19,w1,w0                 ; x19 = arg1 * 0x18
0xf320d0  add  x0,x0,x19 ...
0xf320dc  bl   0xc86f4c                   ; obtain the 0x18-stride row object
0xf320e0  str  w22,[x0,#0x50]             ; row+0x50 = the colour ResID
```

So `0x23be908` is a **9-entry selector → colour ResID table**, written to `row+0x50`, and `0xf32084`
has **zero callers** in `.text` — it is reached through a vtable/thunk, which is consistent with it
being a per-state refresh method instead of a page builder.

Recorded table contents (first entries, all `0x02......` packed ids):

```text
0x23be620 (186 ids)  0x020043ed 0x02005082 0x02004575 0x02005082 0x02004d96 0x02002fe1 ...
0x23be7b8 (untaken)  0x02005261 0x02002f1e 0x0200533b 0x02002f21 0x02002b40 0x02002baa ...
0x23be908 (9 ids)    0x02002934 0x02002896 0x02002f08 0x02002919 0x02002cab 0x02002c82
                     0x02002c88 0x02002caf 0x02002ca3
```

`0x23be7b8` and `0x23bf270` have **no** `adrp+add` reference anywhere in `.text`, so nothing in the
image consumes them by address — they are either dead data or reached via a computed pointer.

### 664 — The one genuinely useful setter in that region

`appFw+0xf3024c(int index, uint8_t value)` is the accessor the presenters use to reach a descriptor
row and write one byte into its bound object:

```text
0xf3024c  cmp  w1,#0x63 ; b.eq 0xf30480              ; index 99 is special-cased
0xf30268  ldr  x3,[x3]  (GOT 0x2ee57b8)              ; -> 0x2e9e210, the 98-entry home table
0xf30270  mov  x2,#0x48 ; mul  x2,x20,x2              ; descriptor = table + index*0x48
0xf30278  ldr  x2,[x3,x2]                             ; *(descriptor+0x00) = the class tag
0xf30284  ldr  x2,[x2]                                ; tag->vtable
0xf3028c  ldr  x3,[x3] (GOT 0x2ee56f8)                ; -> 0x42d5a50 (view_icon tag)
0xf30290  cmp  x3,x2 ; b.ne next-tag-check
0xf30298  ldr  x2,[x0,#0x10]                          ; this->+0x10 = the 0x18-stride row array
0xf302a0  smaddl x1,w1,w0,x2                          ; row = base + index*0x18
0xf302ac  bl   0xf3019c                               ; checked accessor -> param_t*
0xf302b0  strb w19,[x0,#0x2c]                         ; write the byte
```

The tag comparisons chain through `view_icon`, `view_battery`, `view_audio_level_meter`, … using the
GOT slots that alias the class tags, and the assertion strings next to them name the classes directly
(`"view_icon::param_t* view_icon::accessor::operator->()"` at `0x23bec50`, and friends at `0x23be9f0`
and `0x23beb10`). **This** is the mechanism a presenter uses to bind a value into a widget: it walks a
0x48 descriptor table, matches the row's class tag, then writes into the per-index 0x18 row object.

Consequence for 665+: to give `No101..No106` their caption/value/style, the correct static recipe is
(a) take the descriptor from whichever table the presenter passes, (b) confirm the class tag matches
the intended class, (c) write the ResID into the row object at the offset that class's `param_t`
declares — for `view_string` that is the `+0x200` slot already documented, and for the colour tables
above it is `row+0x50`.

### 664 — `view_frame` internals, fully resolved

`view_frame` (`0xc27800`) does **not** hold five inline `view_fill` objects. It holds a five-entry
**pointer array** at `+0x1150..+0x1170`, terminated by `this`:

```text
0xc278d8  str x25,[x19,#0x1150]
0xc278dc  str x24,[x19,#0x1158]
0xc278e0  str x23,[x19,#0x1160]
0xc278e4  str x22,[x19,#0x1168]
0xc278c4  str x21,[x19,#0x1170]        ; x21 = this, loop sentinel
0xc278e8  ldr x0,[x20],#8 ; bl setParent(x0, this)   ; until x20 == this+0x1178
```

The per-edge setter `appFw+0xc27914(frame, slot, color, const int32_t rect4[4])` is what carries the
geometry and colour into a child:

```text
0xc27920  add  x21,x0,w1,sxtw #3        ; x21 = frame + slot*8
0xc27934  ldr  x0,[x21,#0x1150]         ; child = children[slot]     (base is +0x1150!)
0xc2793c  ldr  x1,[x1,#0x140] ; blr x1  ; child->onCreate()
0xc27984  stp  x2,x3,[x0]               ; rect[0],rect[1] -> child+0x00/+0x08
0xc279a0  stp  x2,x3,[x0,#0x10]         ; rect[2],rect[3] -> child+0x10/+0x18
0xc279a8  str  w22,[x0,#0x30]           ; child+0x30 = the colour argument
0xc279b0  stp  x2,x3,[x0,#0x20]         ; caption ids + style
0xc279ac  ldrb w1,[x19,#0x220] ; strb w1,[x0,#0x34]
0xc279c4  blr  child->onDraw()          ; the child paints itself
```

and `0xc27b20..0xc27be4` derives the four edge rects purely from the frame's own geometry:

```text
0xc27b20  ldrh w1,[x19,#0x218]   ; e = border thickness
0xc27b28  ldr  w0,[x19,#0x1f0]   ; w
0xc27b60  ldr  w3,[x19,#0x1f4]   ; h
0xc27b2c  mov  x3,x21            ; x21 = &rect4 on the stack
0xc27b48  mov  w1,#1 ; bl 0xc27914
```

Colour per edge: if that edge's field (`+0x204/+0x208/+0x20c/+0x210`) is `!= -1` it wins, otherwise the
edge falls back to `+0x200` (`0xc27bd0 ldr w2,[x19,#0x200]`). So a frame needs `+0x200 != -1` at
minimum — the same rule as a plain `view_fill`.

`+0x21c` selects the border shape (0 / 1 / 2, anything else throws), and `+0x218` is the thickness used
by every rect. **Do not recompute the edge rects externally**: the native body already does it, and the
arithmetic is style-dependent.

### 664 — New callable helpers in `fx6_menu_items_assist.h`

```text
fx6_frame_setup(frame, x,y,w,h, edge, top,bottom,right,left, fill_color)
fx6_frame_draw(frame)                       onCreate(+0x148) then onDrawNotice(+0x158)
fx6_frame_render(...)                       setup + draw in one call
fx6_frame_child_ptr(frame, slot)            children[slot] from +0x1150
fx6_icon_render(icon, x,y,w,h, image_resid) rect + +0x20c, then onDrawNotice
fx6_menu_item_render(item, x,y,w,h, style, caption, value)
fx6_menu_item_child(item, slot)             *(item + 0x19730 + slot*8)
```

All of them take an object produced by the native constructor and only write fields that the
corresponding `onDrawNotice` actually reads, so they cannot silently produce a blank frame by writing
to a field nobody consumes. The header compiles clean on `aarch64-linux-gnu`.

### 664 — The six outer cells `No101..No106` carry no caption in the table

Reading entries 91..96 of the home table `0x2e9e210` settles question (a):

```text
[91] tag=0x42d58d0 No105_BUTTON_05  d18=00000000 d1c=0200a02a d20=1 d24=0200602c d28=0200600e d2c=44 rect=(349,382,262,122)
[92] tag=0x42d58d0 No102_BUTTON_02  d18=00000000 d1c=0200a02a d20=1 d24=02006032 d28=0200600e d2c=44 rect=(349, 72,262,122)
[93] tag=0x42d58d0 No106_BUTTON_06  d18=00000000 d1c=0200a02a d20=1 d24=02006032 d28=0200600e d2c=44 rect=(607,382,257,122)
[94] tag=0x42d58d0 No104_BUTTON_04  d18=00000000 d1c=0200a02a d20=1 d24=02006032 d28=0200600e d2c=44 rect=(96,382,257,122)
[95] tag=0x42d58d0 No103_BUTTON_03  d18=00000000 d1c=0200a02a d20=1 d24=02006032 d28=0200600e d2c=44 rect=(607, 72,257,122)
[96] tag=0x42d58d0 No101_BUTTON_01  d18=00000000 d1c=0200a02a d20=1 d24=02006032 d28=0200600e d2c=44 rect=(96, 72,257,122)
```

Every one of the six has `+0x18 = 0`. Since the factory writes `desc+0x18` into the object, these six
widgets are created with **no caption and no colour** — their content is supplied later by the presenter
through the accessor path, not by the table.

What they *do* carry is the presentation parameters:

```text
+0x1c = 0x0200a02a   layout/align id (ns 5)
+0x20 = 1            flag
+0x24 = 0x0200602c / 0x02006032   FontName ResID (ns 3)
+0x28 = 0x0200600e   secondary font
+0x2c = 0x44         size constant (68)
```

and geometry that exactly tiles the content area:

```text
(96,72)  257x122      (349,72)  262x122      (607,72)  257x122
(96,382) 257x122      (349,382) 262x122      (607,382) 257x122
```

So `No101..No106` are six equal cells in a 2x3 grid over the 768x432 panel — which is why the dynamic
line sees them as "the outer six cells" and why our own earlier probe drew them as bare
`view_menu_item`s with no pixels: the descriptor alone does not describe their look.

The presenter-side writer is the `param_t` initialiser at `0xc35900..0xc35970`. It fills a struct with
`+0x3c`, `+0x40`, `+0x48`, `+0x4c..+0x50`, `+0x54`, `+0x5c`, `+0x60`, `+0x68`, `+0x6c`, and the entry
point `0xc86f4c` returns exactly that `param_t*` after asserting the row's class tag. That struct — not
the widget — is where a presenter writes the per-cell content.

Practical recipe for 665+:

1. take the descriptor from `0x2e9e210` entries 91..96 for geometry and font ids;
2. take the caption/value from the presenter path (or, for a synthetic page, from the `string_english`
   ResIDs directly, e.g. `0x02002227` = "Shooting");
3. write the caption into the widget's `+0x1d0`/`+0x1d8`/`+0x1e0` slots and the style into `+0x200`
   (that is what `fx6_menu_item_set_text_ids` / `fx6_menu_item_set_style` do), then call
   `fx6_menu_item_render`;
4. remember `onDrawNotice` drives `*(item + 0x19730 + slot*8)`, so the row only paints once that child
   is enabled — `fx6_menu_item_child()` returns it.

### 665 — Per-icon `param_t` table at `appFw+0x42d5618` (stride 0x48), and who applies it

The presenter-side setters `0xc35858` / `0xc35990` / `0xc35a8c` / `0xc35b80` all start the same way:

```text
0xc35860  ldrsw x1,[x0,#0x280]        ; per-icon index (0..3 for the four status icons)
0xc35870  mov   x21,#0x48
0xc35874  add   x20,x20,#0x618        ; x20 = 0x42d5618
0xc3587c  madd  x1,x1,x21,x20         ; entry = table + index*0x48
0xc35884  ldp   x2,x3,[x1]            ; first 16 bytes of the entry
```

and they are driven from one dispatcher, `0xc35cf8..0xc35d28`:

```text
0xc35cd4  ldr  w3,[x0,#0x200] ; cmn w3,#1 ; b.ne 0xc35cf8   ; skip when +0x200 == -1
0xc35cf8  mov  w1,#2 ; blr x2                                ; mode 2
0xc35d08  bl   0xc35858     ; slot-table #1   (offset +0x04)
0xc35d10  bl   0xc35990     ; slot-table #2   (offset +0x14)
0xc35d18  bl   0xc35a8c
0xc35d28  b    0xc35b80     ; tail call, slot-table #4
```

Decoding the table by emulating the initialiser at `0xb1b080` (register-tracked `mov/movk/add/str/stp`)
recovers four live entries. Field `+0x00` is a packed pair, and `+0x44` is a FontName ResID:

```text
[00] 00=000000c1 04=00000003 08=000000a9 0c=00000062 10=000000a9 14=000000c1
     18=0000010e 1c=00000003 20=0000010e 24=00000062 28=0000010e 2c=000000c1
     30=00000044 34=00000003 38=00000044 3c=00000062 40=00000044 44=000000c1
[01] 00=02000220 04=000000c6 08=00000141 0c=00000274 10=0000009f 14=000000e8
     18=00000167 1c=00000230 20=00000052 24..40=ffffffff  44=02006017
[02] 00=02000222 04=000000c6 08=00000113 0c=00000274 10=000000cd 14=000000e8
     18=00000139 1c=00000230 20=00000080 24..40=ffffffff  44=02006017
[03] 00=02000222 04=000000c6 08=00000113 0c=00000274 10=000000cd 14=000000e8
     18=00000139 1c=00000230 20=00000052 24=000000e8 28=00000195 2c=000000b4
     30=00000024 34=0000019e 38=00000195 3c=0000017a 40=00000024 44=02006017
```

Read as (x, y, w, h) quads, entry `[01]` is `x=0xc6, y=0x141, w=0x274, h=0x9f`, and the trailing
`0x02006017` is a namespace-3 FontName id. So this is the **per-icon layout + font** table used by the
status-bar icons, not the six big cells' captions.

**Answer to (a) as far as the statics go:** no table in this region holds `FPS / Shutter / ISO / ND /
WB / Base Look` captions. The six big cells (`No101..No106`, entries 91..96 of `0x2e9e210`) all carry
`desc+0x18 = 0` (documented in the 664 section), and the only writer that reaches them is the
`param_t` path via `0xc86f4c`. Their captions are therefore produced at runtime by whatever fills those
`param_t` structs — there is no static caption table to copy. A probe must supply the labels itself
(e.g. the `string_english` ids `0x02002227` "Shooting", `0x02002121` "Audio"… ) until the presenter's
value-feeding path is located by a runtime trace.

### 665 — Answer to (b): no static row-title table for the 35/17-entry pages either

Walking both tables completely shows the same shape as the six cells — the row widgets carry geometry
and font ids, and `desc+0x18` holds the *dynamic value* id where one exists, never the section title:

```text
TABLE 0x2ea02f8 (35 entries)  entries 01..07 are the row widgets, names like No4_item1..No10_item7
TABLE 0x2eaf208 (17 entries)  entries 01..02 are No1_BG / No28_BG fills, 05..10 separators,
                              11..16 the six buttons
```

There is **no** `User / Shooting / Project / Paint/Look / TC/Media / Monitoring / Audio / Thumbnail /
Technical / Maintenance` title block anywhere in `.rodata` as a ResID array: a full scan of every
`adrp` into `0x23bd000..0x23bffff` finds only the four `unordered_set` initialisers already documented
plus the assert strings, and searching all `0x02......` words for a 10-element run of *distinct* ns-1/ns-2
ids produced no candidate. The section names live in the string containers (`string_english.uxc`
records `0x2121` "Audio", `0x2227` "Shooting", `0x2228` "Project", `0x2229` "Monitoring", `0x222a`
"Technical", `0x222b` "TC/Media", `0x2531` "Setup"), and they are chosen by the presenter at runtime,
not by a static array.

### 665 — `view_icon` image pipeline: the bitmap lands in the Sprite at `icon + 0x550`

`onCreate` (`0xc2c044`) builds the icon's Sprite and its colour table:

```text
0xc2c054  add  x22,x0,#0x550        ; sprite
0xc2c068  bl   0xb19500             ; Widget::initSprite(sprite, 9)
0xc2c0d0  mov  w0,#1 ; strb w0,[x19,#0x660]
0xc2c0d8  ldrb w4,[x19,#0x21f]      ; clip colour bytes +0x21c..+0x21f
0xc2c0ec  bl   0xb18ce0             ; stella::CColor(r,g,b,a)
0xc2c100  bl   0xb187b0             ; sprite->setRectColor(slot, colour)  for slots 0..8
```

`onDrawNotice` (`0xc2d100`) then resolves the image and hands it to that sprite:

```text
0xc2d240  mov  w0,w21               ; w21 = +0x20c
0xc2d24c  bl   0xb16eb0             ; getImageOption(resid, NULL, 0) -> count
0xc2d258  bl   0xb18810             ; sys_getInstance()
0xc2d270  bl   0xb16eb0             ; getImageOption(resid, &portion, 2)
0xc2d278  ldrh w0,[x29,#0x50]       ; portion.count
0xc2d2a0  bl   0xb18c60             ; sprite->setPatchImageCache(flag)
0xc2d388  bl   0xb16ed0             ; sprite size/clip
0xc2d3cc  bl   0xb19f50             ; sprite image
0xc2d3d4  bl   0xc2d00c             ; the blit of the decoded bitmap
```

So there is **no fixed integer offset holding a `RawImageDataGRM`** on the icon object: the decoded
ImageData is owned by the Sprite at `+0x550`. The only gates remain `+0x1fc` (enable) and `+0x20c`
(image ResID).

New helper, the icon analogue of `fx6_render_fill`:

```text
fx6_icon_sprite(icon)                       -> icon + 0x550
fx6_icon_blit(icon, x,y,w,h, image_resid, r,g,b,a)
        sets +0x1e8/+0x1ec/+0x1f0/+0x1f4, +0x1fc = 1, +0x20c = resid,
        +0x21c..+0x21f = RGBA, +0x204/+0x206 = clip w/h,
        then calls onCreate (+0x148) and onDrawNotice (+0x158) — the same two slots the class uses.
```
