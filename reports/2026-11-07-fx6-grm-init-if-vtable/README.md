# FX6 GRM InitializeIF / GraphicsEngine 调用图追踪

日期：2026-11-07（本机 PT 2026-11-06）  
范围：`GraphicsSystemInterface::InitializeIF` 的 vtable/调用者、`GraphicsEngine` 构造函数调用图、`sys_createApplication` 是否被使用  
状态：**纯静态研究；未启动/未改动 VM；未解包/修改固件；未改 QEMU/DTB/平台参数；未写代码；未编译；未跑 pmemsave/解析器；未触碰用户三问**

## 1. 结论先行

**静态证据支持“`sys_createApplication` 在当前 appFw/libuxengine 组合中未被使用”。**

- `libuxengine::GraphicsEngine::sys_createApplication`（0x82854）：
  - `.text` 内无 `bl`、无 tail `b`、无 `adrp/add` 函数指针引用；
  - 无 relocation 指向它；
  - 没有其他库/appFw 的 `U` 引用；
  - `nm -D appFw` 无该符号，`strings appFw` 也没有。
- `libux_core::GraphicsSystemInterface::InitializeIF`（0x2764c）：
  - 是一个 **vtable[0] 跳板**（`own_` → object → vtable → `br x6`）；
  - `.text` 内无 `bl/b/adrp-add` xref；
  - 没有外部 `U` 引用；
  - 很可能是一个**未被使用的弱接口**。
- `GraphicsEngine::sys_initialize`（0x838e4）：
  - `.text` 内无 xref；
  - 反汇编只做 timing/fps 初始化（`w3` 被用作 fps 除数），**不调用 `sys_createApplication`**，也不创建 framebuffer。
- `GraphicsEngine::sys_getInstance`（0x8265c）：
  - 只是返回 `m_instance`（全局单例），不构造、不调用 `sys_createApplication`。
- `GraphicsEngine` 构造函数（0x8350c）：
  - `.text` 内无 `bl/b/adrp-add` xref（可能在 `.init_array`/静态初始化里，未排除）；
  - 反汇编不调用 `sys_createApplication`/`createFramebuffer`。

**推论**：静态调用图上，framebuffer 创建链

```text
sys_createApplication
  -> GraphicsSystem::createFramebuffer
    -> GraphicsSystemCore::Initialize
      -> createGraphicsContext
        -> initializeFBResource
          -> GRM_fbrmInitialize
```

**不可达**。这与当前“没有 on-screen bitmap、没有 OSD 帧”一致；问题不只是 `libgrm-fbinit9` 跳过了 `FrameBuffer::update`，而是**上层初始化入口可能根本没被调用**。

**但这不是运行时证明**：`.init_array`、动态符号、外部进程/插件、未扫描的间接调用仍可能执行它；需要运行时断点确认。

## 2. `InitializeIF` 的 vtable 跳板

`libux_core` 0x2764c：

```text
0x2764c: adrp x4, #0x46000
0x27650: ldr  x4, [x4, #0xe50]   ; own_
0x27654: ldr  x5, [x4]           ; object
0x27658: ldr  x4, [x5]           ; vtable
0x2765c: ldr  x6, [x4]           ; vtable[0]
0x27660: mov  x4, x3             ; allocator
0x27664: mov  w3, w2             ; h
0x27668: mov  w2, w1             ; w
0x2766c: mov  x1, x0             ; name
0x27670: mov  x0, x5             ; this
0x27674: br   x6                 ; call vtable[0]
```

所以：

- `InitializeIF` 本身不是 `GraphicsSystemCore::Initialize` 的直接调用；
- 它通过 `own_` 对象的 vtable[0] 进行虚调用；
- `own_` 在 `libux_core` 0x486f0（BSS）；
- `InitializeIF` 是 weak 导出，没有外部 `U`；
- `.text` 内 `bl/b/adrp-add` 到 0x2764c 均为 0。

**判断**：这是 `GraphicsSystemInterface` 的接口转发函数；当前构建里没有静态调用者，疑似未使用。若它被调用，vtable[0] 可能落到 `GraphicsSystemCore::Initialize`，但静态无法证明 vtable 目标。

## 3. `sys_createApplication` 的 xref

`libuxengine` 0x82854：

```text
0x82860: uxth w20, w1   ; width
0x8286c: uxth w21, w2   ; height
...
0x8289c: x0 = x19
0x828a0: bl   GraphicsSystem::createFramebuffer
```

核查：

- `bl` 到 0x82854：0
- tail `b` 到 0x82854：0
- `adrp/add` 指针：0
- relocation 指向 0x82854：0
- `nm -D appFw`：无
- 其他库 `U`：无
- `strings appFw`：无

**唯一调用 `GraphicsSystem::createFramebuffer` 的静态点就是 0x828a0，位于 `sys_createApplication` 内部。** 如果 `sys_createApplication` 不执行，`createFramebuffer` 也不会执行。

## 4. `GraphicsEngine::sys_initialize` 不创建 framebuffer

`libuxengine` 0x838e4：

```text
0x838f0: uxth w20, w3       ; w3（不是 w/sp）
0x838f4: bl   0x6f520
0x838f8: bl   0x70f80
0x838fc: bl   0x72e80
...
0x83904: mov  w3, #0x4240
0x83908: movk w3, #0xf, lsl #16   ; 0xF4240 = 1,000,000
0x8390c: sdiv w3, w3, w20          ; 1e6 / w3
...
```

它做的是 **fps/timing 初始化**，没有调用 `sys_createApplication`，也没有 `createFramebuffer`/`BMP_Create`。

`sys_getInstance`（0x8265c）：

```text
0x8265c: adrp x0, #0xc1000
0x82660: ldr  x0, [x0, #0xf78]
0x82664: ldr  x0, [x0]
0x82668: ret
```

只是取全局单例；没有构造、没有初始化。

## 5. `GraphicsEngine` 构造函数

`libuxengine` 0x8350c：

- 反汇编里调用 `0x6eef0`/`0x70160`/`0x737b0`/`0x728e0`/`0x70820`/`0x73090` 等；
- 没有 `bl 0x82854`（`sys_createApplication`）；
- 没有 `bl 0x828a0`（`createFramebuffer`）；
- `.text` 内没有 `bl/b/adrp-add` 到 0x8350c 的 xref；
- 可能在 `.init_array`/静态初始化里被调用；静态 xref 未覆盖 `.init_array`，所以不能断言构造函数未运行，但可以断言它不创建 framebuffer。

## 6. 与 appFw 的关系

appFw 只导入：

```text
GraphicsEngine::drawFramebuffer
GraphicsEngine::sys_getInstance
GraphicsEngine::processSystemMessage
GraphicsEngine::getAreaCheckExtensionManager
GraphicsEngine::setOverflowResizeFontAttribute
GraphicsEngine::setOverflowResizeLayoutAttribute
```

没有：

```text
sys_createApplication
createScreen3D
createFramebuffer
InitializeIF
Screen::setAreaInFramebuffer
```

所以 appFw 只通过 `sys_getInstance` 拿到单例，然后画；它不负责创建 framebuffer。若单例没有 framebuffer，`drawFramebuffer` 可能空转或失败。

## 7. appFw rodata 的 1024/540 复核

上一份报告已确认：

- `u32 1024,540`：0 处；
- `u16 1024,540`：8 处，位于密集 `1024×N` 表（高度约 0x217–0x220），像字形/纹理尺寸表；
- `libuxengine`/`libux_core`/`libgemini`：无独立 1024,540 对；
- 唯一 1024×540 线索仍是 `libgrm-fbinit9.c` 注释/默认值。

本报告不重复展开。

## 8. 解释：为什么当前没有 on-screen bitmap

结合前两份报告：

1. `GRM_screenGetOnBitmap` 依赖 `FrameBuffer::getOnscreen`；
2. `FrameBuffer::getOnscreen` 依赖 `fb+0x68`→`fb+0x20`；
3. `fb+0x20` 的 BMP 由 `FrameBuffer::update` 调用 `BMP_CreateFromPhys` 创建；
4. `FrameBuffer::update` 由 `createFramebuffer` → `GraphicsSystemCore::Initialize` → `createGraphicsContext` → `initializeFBResource` → `GRM_fbrmInitialize` 触发；
5. **静态图上 `sys_createApplication` 没有被调用，`InitializeIF` 也没有调用者**。

因此最可能的解释是：

```text
framebuffer 创建入口未执行
  -> fb+0x20 没有 BMP
  -> GRM_screenGetOnBitmap 返回 NULL
  -> OSD worker 无 bitmap
  -> 没有可见帧
```

`libgrm-fbinit9` 跳过 `FrameBuffer::update` 只是第二层原因；**第一层是入口未调用**。

## 9. 运行时验证方案（仅设计，不执行）

### 9.1 断点

```text
libux_core:
  GraphicsSystemInterface::InitializeIF  0x2764c
  GraphicsSystemCore::Initialize         0x27ef0

libuxengine:
  GraphicsEngine::sys_createApplication  0x82854
  GraphicsSystem::createFramebuffer      0x828a0
  GraphicsEngine::sys_initialize         0x838e4
  GraphicsEngine::sys_getInstance        0x8265c
  GraphicsEngine ctor                    0x8350c

libgemini-grm:
  initializeFBResource                   0x8e68
  createGraphicsContext                  0x8ea0

libgrm:
  GRM_fbrmInitialize                     0x23374
  FrameBuffer::setSize                   0x2303c
  FrameBuffer::update                    0x23160
  GRM_screenGetOnBitmap                  0x2368c
```

### 9.2 判定

- 如果 `sys_createApplication`/`InitializeIF`/`GRM_fbrmInitialize` **都没命中** → 确认入口未调用；
- 如果 `sys_createApplication` 命中 → 读 `w1/w2`，确认 w/h；
- 如果 `GRM_fbrmInitialize` 命中 → 读 `w0/w1/w2`，确认 w/h/format；
- 如果 `createFramebuffer` 命中但 `GRM_fbrmInitialize` 不命中 → 中间 `GraphicsSystemCore::Initialize`/`createGraphicsContext` 断开；
- 如果 `FrameBuffer::update` 命中但 `fb+0x20` 仍空 → `BMP_CreateFromPhys` 失败，查 MA 物理地址/format。

### 9.3 日志

```text
FX6_GRM_FB_SET_SIZE
FX6_UX_SCREEN_AREA_1024
FX6_GRM_FB_UPDATE_SKIP
FX6_GRM_FB_INIT_SKIP
```

**本轮不执行以上步骤。**

## 10. 实测 vs 推断 vs 缺失

### 静态实测

- `InitializeIF` 是 vtable[0] 跳板，无 `.text` xref、无外部 U；
- `sys_createApplication` 无 `bl/b/adrp-add`、无 reloc、无外部 U；
- `sys_initialize` 只做 timing，不调用 `sys_createApplication`；
- `sys_getInstance` 只返回单例；
- `GraphicsEngine` ctor 不调用 `sys_createApplication`/`createFramebuffer`；
- appFw 无相关导入；
- `createFramebuffer` 唯一静态调用点在 `sys_createApplication` 内。

### 推断

- `sys_createApplication`/`InitializeIF` 在当前构建中未被使用；
- framebuffer 创建入口未执行，导致没有 on-screen BMP；
- 这比 `libgrm-fbinit9` 跳过 update 更上游。

### 缺失

- `.init_array`/动态符号/外部插件是否调用这些入口；
- 运行时断点是否命中；
- 实际 w/h/format；
- 真正触发 `GRM_fbrmInitialize` 的调用者（如果有）。

## 11. 边界

- 未启动/未改动任意 VM；
- 未解包/修改 `BODYDATA.DAT` 或任意固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未写代码、未编译、未运行；
- 未跑 pmemsave/解析器；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）。

## 12. 下一步

1. 静态：查 `.init_array`/`.fini_array` 是否引用 `GraphicsEngine` ctor 或 `sys_createApplication`；查 `own_`（0x486f0）的初始化写入点，确认 `InitializeIF` 的 vtable 目标。
2. 运行时（需批准）：按第 9 节断点，先确认 `sys_createApplication`/`InitializeIF` 是否命中；若不命中，回到 appFw 的 `GraphicsEngine::drawFramebuffer` 调用点 backtrace，找真正的初始化入口。
3. 只有确认入口和 w/h 后，才决定 8×0x180000 vs 4×0x3c0000；当前保持 4× 安全回退。
