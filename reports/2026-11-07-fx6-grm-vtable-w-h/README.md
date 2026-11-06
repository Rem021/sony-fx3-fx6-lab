# FX6 GRM vtable / w-h 追踪

日期：2026-11-07（本机 PT 2026-11-06）  
范围：`sys_createApplication` 的间接分发、appFw GraphicsEngine 初始化入口、appFw rodata 中的 1024/540 配置  
状态：**纯静态研究；未启动/未改动 VM；未解包/修改固件；未改 QEMU/DTB/平台参数；未写 shim/解析器代码；未编译；未跑 pmemsave/解析器；未触碰用户三问**

## 1. 结论先行

**仍未确认 FX6 的 width/height = 1024×540。**

- `libgemini-grm::initializeFBResource(w,h)` 确实把 `w1/w2` 传给 `GRM_fbrmInitialize(w,h,1)`；
- `libux_core::GraphicsSystemCore::Initialize(name,w,h,alloc)` 确实把 `w2/w3` 传给 `createGraphicsContext`；
- 但 `sys_createApplication`（`libuxengine` 0x82854）在 `.text` 内**没有 `bl`、没有 tail `b`、没有 `adrp/add` 函数指针引用**；`readelf -r` 也没有指向 0x82854 的 relocation；
- appFw **没有导入** `sys_createApplication`、`createScreen3D`、`createFramebuffer`、`InitializeIF`、`setAreaInFramebuffer`；只导入 `GraphicsEngine::sys_getInstance`/`drawFramebuffer`/`processSystemMessage` 等；
- appFw rodata 中没有 **32-bit 1024,540** 成对常量；16-bit `1024,540` 的命中位于一个密集的 `1024×N` 表（高度约 0x217–0x220），更像字形/纹理尺寸表，不是独立屏幕配置；
- 因此 **1024×540 目前仍只有 `libgrm-fbinit9.c` 的本地 shim 注释/默认值**，不是独立静态/运行时证据。

卡点：`sys_createApplication` / `initializeFBResource` / `createGraphicsContext` 的上层调用是**间接分发**（疑似 vtable/外部指针/未使用导出），静态 xref 断在这里。

## 2. 已知调用链

```text
GraphicsSystemCore::Initialize(name, w, h, alloc)   libux_core 0x27ef0
  -> createGraphicsContext(w, h)                    libux_core 0x27f90
    -> initializeFBResource(w, h)                   libgemini-grm 0x8e68
      -> GRM_fbrmInitialize(w, h, format=1)         libgrm 0x23374
        -> FBResourceManager::initializeFrameBuffer
          -> FrameBuffer::setSize + setColorFormat
          -> FrameBuffer::update
            -> BMP_CreateFromPhys(fb+0x20, format=1, sorting=0, start=0)
```

另一条上层入口：

```text
GraphicsEngine::sys_createApplication(name, w, h)   libuxengine 0x82854
  -> GraphicsSystem::createFramebuffer(w, h)        libuxengine 0x828a0
```

### 2.1 `initializeFBResource`

`libgemini-grm`（0x8e68）：

```text
0x8e78: uxth w0, w1     ; width
0x8e7c: uxth w1, w2     ; height
0x8e80: mov  w2, #1     ; format = 1
0x8e84: bl   GRM_fbrmInitialize
```

### 2.2 `createGraphicsContext`

`libgemini-grm`（0x8ea0）：

```text
0x8eb4: uxth w23, w1    ; width
0x8ecc: uxth w24, w2    ; height
0x8f00: w1 = w23
0x8f04: w2 = w24
0x8f10: bl   0x6bb0     ; helper（疑似虚调用 initializeFBResource）
```

`0x6bb0` 不是直接 `bl 0x8e68`；它是间接 helper，无法从静态调用图直接落到 `initializeFBResource`。

### 2.3 `GraphicsSystemCore::Initialize`

`libux_core`（0x27ef0）：

```text
0x27f04: uxth w21, w2   ; width
0x27f20: uxth w22, w3   ; height
0x27f88: w1 = w21
0x27f8c: w2 = w22
0x27f90: bl   createGraphicsContext
```

### 2.4 `sys_createApplication`

`libuxengine`（0x82854）：

```text
0x82860: uxth w20, w1   ; width
0x8286c: uxth w21, w2   ; height
0x82894: w2 = w21
0x82898: w1 = w20
0x828a0: bl   GraphicsSystem::createFramebuffer
```

函数本身没有直接调用者，见下节。

## 3. 间接分发核查

### 3.1 `sys_createApplication` 的 xref

对 `libuxengine` `.text` 做：

- `bl` 到 `0x82854`：**0 个**
- tail `b` 到 `0x82854`：**0 个**
- `adrp/add` 组成函数指针：**0 个**
- `readelf -r` 指向 `0x82854` 的 relocation：**0 个**
- `nm -D appFw`：无 `sys_createApplication` 导入
- `strings appFw`：无 `sys_createApplication`
- 其他库：只有 `libuxengine` 定义该符号，没有外部 `U` 引用

结论：

- 没有静态证据表明 `sys_createApplication` 在当前的 appFw/libuxengine 组合中被调用；
- 它可能是**导出但未使用**的 API、由外部/动态方式调用、或通过未被静态扫描覆盖的间接方式调用；
- 因此不能从它反推 w/h。

### 3.2 `createGraphicsContext` / `initializeFBResource` 的 xref

- `libgemini-grm::initializeFBResource`：`.text` 内 `bl`/`b` 到 0x8e68 均为 **0**；
- `createGraphicsContext`：唯一直接 `bl` 在 `libux_core` 0x27f90；
- `GraphicsSystemCore::Initialize`：没有直接外部导入（`nm -D` 无 `U`），疑似通过 `GraphicsSystemInterface::InitializeIF`（weak）或 vtable 调用；
- `GraphicsSystemInterface::InitializeIF`（libux_core 0x2764c）是 weak 导出，没有外部 `U` 引用。

结论：调用图在 `GraphicsSystemCore::Initialize` 之上断掉；w/h 从上层进入的路径无法只靠静态 xref 闭合。

### 3.3 appFw GraphicsEngine 初始化入口

`nm -D appFw` 相关导入：

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

所以 appFw 不直接把 w/h 传给 GRM；它只通过 `GraphicsEngine::sys_getInstance` 拿单例，真正初始化在 libuxengine/libux_core/libgemini 内部。`createScreen3D`（libuxengine 0x83290）也不调用 `sys_createApplication`。

## 4. appFw rodata / 配置区搜索

### 4.1 32-bit 常量

在 appFw 全文件搜：

```text
u32 1024,540  -> 0
u32 540,1024  -> 0
u32 1280,720  -> 0
```

没有独立的 32-bit 屏幕尺寸配置。

### 4.2 16-bit 常量

```text
u16 1024,540  -> 8 处
0x2f8a0ea
0x2f8c3b6
0x2f8e6ea
0x2f909b6
0x2f92e52
0x2f9511e
0x2f9b3aa
0x2f9d676
```

这些偏移的上下文是密集的 `1024 × N` 表，例如：

```text
00 04 19 02   ; 1024, 0x219
00 04 1a 02   ; 1024, 0x21a
...
00 04 1c 02   ; 1024, 0x21c = 540
...
```

高度从约 0x217 到 0x220 连续变化，更像**字形/纹理/字形缓存尺寸表**，不是单个屏幕配置。8 处命中只是表中恰好出现 540 的行。

### 4.3 其他库

```text
libuxengine: u32/u16 1024,540 -> 0
libux_core:  u32/u16 1024,540 -> 0
libgemini:   u32/u16 1024,540 -> 0
```

`libuxengine` 有 1 处 `u16 1280,720`，上下文是随机表数据（0xe59f），不是屏幕配置。

### 4.4 结论

appFw/库中**没有找到独立的 1024×540 屏幕尺寸常量**；16-bit 命中不能作为屏幕配置证据。`libgrm-fbinit9.c` 的注释/默认值仍是唯一 1024×540 线索。

## 5. 卡点

```text
sys_createApplication (libuxengine 0x82854)
  - 无 bl / b / adrp-add xref
  - 无 relocation
  - 无 appFw 导入/字符串
  - 无其他库 U 引用

createGraphicsContext (libgemini 0x8ea0)
  - 唯一直接调用点在 libux_core 0x27f90
  - 但 GraphicsSystemCore::Initialize 本身无外部直接导入

initializeFBResource (libgemini 0x8e68)
  - 无 bl/b 调用者
  - 0x6bb0 helper 疑似虚调用

appFw rodata
  - 无 32-bit 1024,540
  - 16-bit 命中是 1024×N 表
```

因此静态图在**间接分发/未使用导出**处断开，无法确认 w/h。

## 6. 运行时方案（仅设计，不执行）

若后续批准运行时，建议按以下顺序设断点/日志；先读寄存器，再 backtrace。

### 6.1 断点

```text
libgrm:
  GRM_fbrmInitialize                 0x23374  ; w0=width, w1=height, w2=format
  FrameBuffer::setSize               0x2303c  ; w1=width, w2=height
  FrameBuffer::update                0x23160  ; 读 [fb+0x14]/[fb+0x16]/[fb+0x18]
  GRM_screenGetOnBitmap              0x2368c  ; 读 [fb+0x20]

libgemini-grm:
  initializeFBResource               0x8e68   ; w1=width, w2=height
  createGraphicsContext              0x8ea0   ; w1=width, w2=height

libux_core:
  GraphicsSystemCore::Initialize     0x27ef0  ; w2=width, w3=height
  createGraphicsContext call         0x27f90

libuxengine:
  sys_createApplication              0x82854  ; w1=width, w2=height
  createFramebuffer call             0x828a0
```

ASLR 下用模块基址 + 偏移；先 `info sharedlibrary`/`dladdr` 取基址。

### 6.2 日志

现有可用：

```text
FX6_GRM_FB_SET_SIZE
FX6_UX_SCREEN_AREA_1024
FX6_GRM_FB_UPDATE_SKIP
FX6_GRM_FB_INIT_SKIP
```

如果真实 `FrameBuffer::update` 不跳过，`FX6_GRM_FB_SET_SIZE` 应打印实际 w/h。

### 6.3 判定

- `GRM_fbrmInitialize` 命中且 `w0=1024,w1=540` -> 确认；
- 命中但 w/h 不同 -> 以运行时为准，更新 ring；
- 未命中 -> `sys_createApplication`/上层入口未调用，需 backtrace 找实际调用者；
- 命中但 `w0/w1=0` -> 初始化顺序/配置问题，检查 `FrameBuffer::setSize`。

**本轮不执行以上步骤。**

## 7. 对 ring/osd_ring_fx6 的影响

前一份报告的设计仍成立：

- 若确认 1024×540 + format 1/2bpp：`1024*540*2=0x10E000`，8×0x180000 足够（8 帧）；
- 若尺寸未确认：4×0x3c0000 更安全（覆盖 1280×720×2、1024×540×4、1280×720×4）；
- 1920×1080×4 两种都不够，需要单帧/双帧。

本报告没有新增尺寸确认，因此**不改变前一份报告的保守建议**：在运行时确认前，4×0x3c0000 仍是安全回退；确认 1024×540+2bpp 后才建议 8×0x180000。

## 8. 实测 vs 推断 vs 缺失

### 静态实测

- `initializeFBResource` / `createGraphicsContext` / `GraphicsSystemCore::Initialize` / `sys_createApplication` 的指令与参数传递；
- `sys_createApplication` 无 bl/b/adrp-add xref、无 relocation；
- appFw 无相关导入/字符串；
- appFw rodata 无 32-bit 1024,540；16-bit 命中为 1024×N 表；
- `libgrm-fbinit9.c` 的 1024×540 注释/默认值。

### 推断

- `sys_createApplication` 可能未被调用，或由未静态覆盖的间接方式调用；
- 16-bit 1024×N 表是字形/纹理尺寸表，不是屏幕配置；
- 真实 w/h 可能由 libgemini/libuxengine 内部配置决定。

### 缺失

- `sys_createApplication`/`GraphicsSystemCore::Initialize` 的实际上层调用者；
- w/h 的实际常量/配置来源；
- 运行时 `FX6_GRM_FB_SET_SIZE`/`FX6_UX_SCREEN_AREA` 日志；
- `GRM_fbrmInitialize` 是否命中；
- `FrameBuffer::update` 是否真正创建 on-screen BMP。

## 9. 边界

- 未启动/未改动任意 VM；
- 未解包/修改 `BODYDATA.DAT` 或任意固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未写 shim/解析器代码、未编译、未运行；
- 未跑 pmemsave/解析器；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）。

## 10. 下一步

1. 静态：继续查 `GraphicsSystemInterface::InitializeIF` 的 vtable/调用者，或 `libuxengine` 的 `GraphicsEngine` 构造函数调用图；当前 `sys_createApplication` 无 xref，优先怀疑它未被使用。
2. 运行时（需批准）：按第 6 节断点，先确认 `GRM_fbrmInitialize` 是否命中及 w/h；这比继续追静态 vtable 更直接。
3. 运行时确认后再决定 8×0x180000 vs 4×0x3c0000；当前保持 4× 安全回退。
