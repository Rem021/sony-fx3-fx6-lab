# FX6 GRM fbinit 参数追踪、osd_ring_fx6 设计与 update 不跳过 shim 方案

日期：2026-11-07（本机 PT 2026-11-06）  
范围：`libgemini-grm` 的 width/height 实参、`osd_ring_fx6.py` 设计、`FrameBuffer::update` 真实路径 shim 设计  
状态：**纯静态研究；未启动/未改动 VM；未解包/修改固件；未改 QEMU/DTB/平台参数；未写 shim 代码；未跑 pmemsave/解析器；未触碰用户三问**

## 1. 结论

1. **未能静态确认 `libgemini-grm` 的 width/height 就是 1024×540。**
   追到的链路是：
   ```text
   GraphicsSystemCore::Initialize(name, w, h, alloc)
     -> createGraphicsContext(w, h)
       -> initializeFBResource(w, h)
         -> GRM_fbrmInitialize(w, h, format=1)
   ```
   但 `createGraphicsContext` 的调用者 `sys_createApplication` 没有直接 `bl` 调用者，疑似通过 vtable/外部函数指针调用；`initializeFBResource` 也无直接 `bl/b` 调用者，疑似虚调用。**卡在间接分发**。
2. **目前唯一的 1024×540 证据仍是 `libgrm-fbinit9.c` 的本地 shim 注释/默认值**，不是独立运行时确认。
3. **`osd_ring_fx6.py` 设计**：
   - 参数化支持 **8×0x180000**（8 帧，总 0xC10000）与 **4×0x3c0000**（4 帧，总 0xF10000）；
   - slot 头沿用 21 QWORD，新增 `raw BMP_PixelFormat`、`bpp`、`sorting/start`；
   - 静态实际 format=1/2bpp、1024×540 时 `0x10E000`，8×0x180000 足够且更优；尺寸未确认时 4×0x3c0000 更安全。
4. **不跳过 `FrameBuffer::update` 的 shim 设计**：
   - 必须走真实实现的函数：`FBResourceManager::getInstance`、`FrameBuffer::initialize`、`setSize`、`setColorFormat`、`initializeFrameBuffer`、`update`、`getOnscreen`、`getOffscreen`、`getOnscreenHandle`；
   - 顺序：manager → FrameBuffer 初始化 → setSize/setColorFormat → update（创建 `+0x20/+0x40` BMP）→ getOnscreen → OSD 读屏；
   - 主要风险：真实 `initialize/update` 依赖 MA/GRM/GPE/线程/信号量，现有 shim 正是为绕过这些而跳过；直接走真实路径可能 abort/hang。
5. 两份既有报告 `cf5f6cf6`（BMP 语义）与 `55931f93`（on-screen bitmap）均在 HEAD、工作区干净、已 push。

## 2. width/height 追踪

### 2.1 已知链路

`libgemini-grm::GraphicsContextGRM::initializeFBResource(unsigned short, unsigned short)`（0x8e68）：

```text
0x8e78: uxth w0, w1     ; width
0x8e7c: uxth w1, w2     ; height
0x8e80: mov  w2, #1     ; format = 1
0x8e84: bl   GRM_fbrmInitialize
```

`GraphicsContextGRM::createGraphicsContext(MemoryAllocator*, ushort, ushort)`（0x8ea0）：

```text
0x8eb4: uxth w23, w1    ; width
0x8ecc: uxth w24, w2    ; height
...
0x8f00: w1 = w23
0x8f04: w2 = w24
0x8f08: x0 = x21
0x8f10: bl   0x6bb0     ; helper, likely virtual initializeFBResource
```

`libux_core::GraphicsSystemCore::Initialize(char const*, ushort, ushort, MemoryAllocator*)`（0x27ef0）：

```text
0x27f04: uxth w21, w2   ; width
0x27f20: uxth w22, w3   ; height
...
0x27f88: w1 = w21
0x27f8c: w2 = w22
0x27f90: bl   createGraphicsContext
```

`libuxengine::GraphicsEngine::sys_createApplication(char const*, ushort, ushort)`（0x82854）：

```text
0x82860: uxth w20, w1   ; width
0x8286c: uxth w21, w2   ; height
...
0x82894: w2 = w21
0x82898: w1 = w20
0x8289c: x0 = x19
0x828a0: bl   GraphicsSystem::createFramebuffer
```

`GraphicsSystem::createFramebuffer` 再进入 `GraphicsSystemCore::Initialize`，最终到 `GRM_fbrmInitialize`。

### 2.2 卡点

查过：

- `libgemini-grm`：`initializeFBResource` 无直接 `bl`/`b` 调用者；`createGraphicsContext` 用 helper `0x6bb0` 间接调用。
- `libux_core`：`createGraphicsContext` 唯一直接调用点 `0x27f90`；`w1/w2` 来自 `GraphicsSystemCore::Initialize` 的 `w2/w3`。
- `libuxengine`：`sys_createApplication` 没有直接 `bl` 调用者；`createScreen3D`（0x83290）也不调用它；疑似通过 vtable/外部函数指针/动态符号。
- `appFw`：没有导入 `sys_createApplication`、`InitializeIF`、`createFramebuffer`、`GraphicsSystemCore::Initialize`。
- `readelf -r`：没有直接针对 `0x82854`/`0x8e68` 的 relocation 线索。
- 没有在 `libgemini-grm`/`libux_core`/`libuxengine` 调用链上找到 `1024`/`540` 常量。

**卡点**：`sys_createApplication`/`initializeFBResource` 的调用是间接分发；没有运行时 backtrace/断点，无法把 `w1/w2` 追到常量或配置。

### 2.3 当前能说的话

- `libgemini-grm` 确实把 `w1/w2` 原样传给 `GRM_fbrmInitialize`，format 固定 1；
- `libux_core`/`libuxengine` 链路确实把 `w/h` 从上层传到下层；
- **但 1024×540 目前只有 `libgrm-fbinit9.c` 的注释/默认值支持**：
  ```c
  /* AppFw reports 1024x540 via FrameBuffer::setSize; use the same size ... */
  if (!w) w = 1024; if (!h) h = 540;
  ```
- 这是本地 shim 证据，不是 appFw 常量或运行时串口证据。

## 3. `osd_ring_fx6.py` 设计

> 本节只写设计，不写代码、不跑解析、不碰真实 ring。

### 3.1 参数表

公共：

```text
BASE        = 0x41e000000
MAGIC       = 0x31474e495244534f  (沿用 OSDRING1 时)
HEADER      = 0x10000
PIXEL_OFF   = 0x100
MAX_W       = 1024 (或 1280)
MAX_H       = 540  (或 720)
```

布局 A：8×0x180000

```text
SLOTS       = 8
SLOT_STRIDE = 0x180000
TOTAL       = 0xC10000
MAX_SPAN    = 0x180000 - PIXEL_OFF
```

布局 B：4×0x3c0000

```text
SLOTS       = 4
SLOT_STRIDE = 0x3c0000
TOTAL       = 0xF10000
MAX_SPAN    = 0x3c0000 - PIXEL_OFF
```

### 3.2 v[] 字段（21 QWORD）

```text
v[0]  seq
v[1]  epoch
v[2]  seq（必须 == v[0]）
v[3]  update_id
v[4]  pixel_source_sequence
v[5]  token
v[6]  physical（bitmap/data 指针或 0）
v[7]  fmt 类别：0=2bpp，1=4bpp
v[8]  width
v[9]  height
v[10] stride（pixels）= rowBytes / bpp
v[11] span（bytes）= size
v[12] FNV64（data[0:size]）
v[13] bitmap 指针
v[14] data 指针
v[15] allocation
v[16] metadata
v[17] 原始 BMP_PixelFormat
v[18] bpp（1/2/4）
v[19] sorting/start 打包
v[20] version/config
```

### 3.3 校验

```text
magic == MAGIC
v[0] == v[2]
v[1] == global_epoch
v[7] in {0,1}
0 < v[8] <= MAX_W
0 < v[9] <= MAX_H
v[10] >= v[8]
v[11] <= MAX_SPAN
v[11] == v[10] * v[9] * bpp   (若 packed；否则 >=)
FNV64(data[0:v[11]]) == v[12]
像素非均匀（至少两个不同 32-bit/16-bit 值）
```

### 3.4 布局取舍

静态实际 format=1/2bpp；若 1024×540：

```text
1024 * 540 * 2 = 1,105,920 = 0x10E000
```

| 布局 | 帧数 | 总大小 | 1024×540×2 | 1280×720×2 | 1024×540×4 |
|---|---:|---:|---|---|---|
| 8×0x180000 | 8 | 0xC10000 | 可 | 不可（0x1C2000） | 不可（0x21C000） |
| 4×0x3c0000 | 4 | 0xF10000 | 可 | 可 | 可 |

结论：

- **1024×540 + 2bpp 确认时，8×0x180000 足够且多 4 个 slot**；
- **尺寸/格式未确认时，4×0x3c0000 更安全**（覆盖 1280×720×2、1024×540×4、1280×720×4）；
- 1920×1080×4（0x7E9000）两种都不够，需要单帧/双帧；
- `osd_ring85.py` 的 640×480/0x12c000/8×0x180000 限制不能直接复用，需新文件。

## 4. 不跳过 `FrameBuffer::update` 的 shim 设计

> 本节只写设计，不写代码、不编译、不运行。

### 4.1 当前 shim 为什么没有 bitmap

`libgrm-fbinit9.c`：

```c
FrameBuffer::initialize  -> skip
FrameBuffer::update      -> skip
FrameBuffer::getOnscreen -> return NULL
FBResourceManager::getInstance -> fake manager
```

结果：

```text
fb+0x68 未设置
fb+0x20 没有 BMP
GRM_screenGetOnBitmap -> NULL
```

### 4.2 必须走真实实现的函数

| 函数 | 原因 |
|---|---|
| `FBResourceManager::getInstance` | 需要真实 manager/FrameBuffer；fake 会绕过初始化 |
| `FrameBuffer` ctor | 初始化 `+0x14/+0x16/+0x18/+0x68/+0x70` |
| `FrameBuffer::initialize` | 创建 MA 空间，设置 `fb+0x68/+0x70` |
| `FrameBuffer::setSize` | 写入 width/height |
| `FrameBuffer::setColorFormat` | 写入 format（`GRM_fbrmInitialize` 的 format=1） |
| `FBResourceManager::initializeFrameBuffer` | setSize → setColorFormat → update 的顺序 |
| `FrameBuffer::update` | **关键**：为 `+0x20/+0x40` 调 `BMP_CreateFromPhys` |
| `FrameBuffer::getOnscreen` | 返回 `[fb+0x68]` → `[fb+0x20]` |
| `FrameBuffer::getOffscreen` | 可选，保持一致性 |
| `FrameBuffer::getOnscreenHandle` | 可选，读取 handle |
| `GRM_fbrmInitialize` | 真实调用 initializeFrameBuffer |
| `BMP_CreateFromPhys` | 真实创建 on/off BMP |

### 4.3 调用顺序

```text
1. FBResourceManager::getInstance()
2. FrameBuffer ctor（或真实 initialize）
3. FrameBuffer::initialize(w, memory)
4. FrameBuffer::setSize(w, h)
5. FrameBuffer::setColorFormat(format=1)
6. FrameBuffer::update()
     -> BMP_CreateFromPhys(width, height, format=1, yuv=0, phys,
                           row=width, rect=0, out=&fb+0x20,
                           sorting=0, start=0)
     -> 同样创建 fb+0x40
7. FrameBuffer::getOnscreen() -> BMP*
8. GRM_screenGetOnBitmap() -> BMP*
9. OSD worker：screenIsDirty / bitmapReadLockBits / GetSize / GetFormat
```

### 4.4 风险点

1. **真实 `initialize/update` 可能 abort/hang**：现有 shim 正是为绕过 MA/GRM/GPE/线程/信号量而跳过；直接走真实路径可能重新触发之前 abort。
2. **`FrameBuffer::initialize` 需要 MA 内存空间**；如果 MA/GPE 后端没有初始化，`MA_CreateSpace`/`MA_LogicalToPhysical` 可能失败，`BMP_CreateFromPhys` 拿不到物理地址。
3. **`FBResourceManager::getInstance` 的真实 manager 可能未初始化**；现有 fake manager 是为了避免空指针，改 real 需要保证 manager/FrameBuffer 已构造。
4. **`getOnscreen` 空指针风险**：如果 `fb+0x68` 仍是 0，真实 `getOnscreen` 会 `ldr [0]`；需要 guard 或确保 initialize 成功。
5. **width/height 未确认**：若 `sys_createApplication` 传 0 或非 1024×540，`BMP_CreateFromPhys` 可能失败或创建错误尺寸。
6. **format 固定 1/2bpp**：若上层 format 变 2/3，`GRM_fbrmInitialize` 会映射 4bpp，ring 布局要改。
7. **符号 interposition 顺序**：`libgrm` 与 `libgrm-fbinit9` 的加载顺序会影响 `FrameBuffer::update`/`getOnscreen` 谁生效；必须确认 shim 优先。
8. **`GRM_screenGetOnBitmap` 仍可能 NULL**：即使 BMP 创建，`FBResourceManager::getOnscreen`/screen manager 仍可能未初始化。
9. **`BMP_CreateFromPhys` 的 `x5=width` 语义**：当前调用把 width 当第 6 个 short 参数；若它其实是 rowBytes，2bpp 下会错位，需要运行时核对。
10. **没有 GPE/GRM 真实后端**：FX3 VM 上没有 FX6 的 GPE/GRM 硬件，真实 update 可能无法完成。

### 4.5 备选（仅记录，不推荐作为首选）

- 保持 fake manager，但手动创建 synthetic BMP：
  - `BMP_CreateSize(1024, 540, format=1, yuv=0, ..., out=&fb+0x20, sorting=0, start=0)`；
  - 设置 `fb+0x68=&fb+0x20`；
  - `getOnscreen` 返回该 BMP。
- 优点：绕开 MA/GRM/GPE；
- 缺点：不是真实 `FrameBuffer::update` 路径，可能缺少 GRM 的 dirty/update 语义；用户本次要求设计“不跳过 update”的方案，故仅作 fallback。

## 5. 报告提交状态

```text
cf5f6cf6  reports/2026-11-07-fx6-grm-bmp-semantics/README.md  (377 lines)
55931f93  reports/2026-11-07-fx6-grm-onscreen-bitmap/README.md (424 lines)
```

- 两者都在 HEAD 历史中；
- `git status` 干净；
- 已 push 到 `origin/main`。

## 6. 实测 vs 推断 vs 缺失

### 静态实测

- `initializeFBResource(w,h)` 0x8e68 → `GRM_fbrmInitialize(w,h,1)`；
- `createGraphicsContext(w,h)` 0x8ea0 接收并转发 w/h；
- `GraphicsSystemCore::Initialize(name,w,h,alloc)` 0x27ef0 → `createGraphicsContext` 0x27f90；
- `sys_createApplication(name,w,h)` 0x82854 → `GraphicsSystem::createFramebuffer` 0x828a0；
- 这些函数之间无直接 `bl` 的上层调用者，疑似 vtable/间接分发；
- 两份报告 commit/push 状态。

### 推断

- `sys_createApplication` 的 w/h 最终来自 appFw/UX 配置；
- 1024×540 是实际 UI 尺寸（本地 shim 注释/默认）；
- 8×0x180000 在 1024×540+2bpp 下足够；
- 真实 `FrameBuffer::update` 能创建 on-screen BMP，但未运行验证。

### 缺失

- `sys_createApplication`/`initializeFBResource` 的上层间接调用者；
- `w1/w2` 的实际常量/配置来源；
- 运行时 `FX6_GRM_FB_SET_SIZE`/`FX6_UX_SCREEN_AREA` 串口；
- 真实 BMP 创建/读屏结果；
- `BMP_CreateFromPhys` 第 6 个 short 参数语义；
- 无 FX6 ring 帧/PNG。

## 7. 下一步

1. 若继续静态：对 `sys_createApplication` 做 **vtable/xref/动态符号** 追踪，或从 appFw 的 `GraphicsEngine` 初始化调用点反推；当前卡在间接分发。
2. 若允许运行时（需另行批准）：在 `GRM_fbrmInitialize`/`BMP_CreateFromPhys` 下断点或打日志，直接读 w/h/format；这比继续静态追 vtable 更快。
3. 写 `osd_ring_fx6.py` 代码/跑解析、写 shim/编译、`pmemsave` 实跑均需另行批准；本次只写设计。

## 8. 边界

- 未启动/未改动任意 VM；
- 未解包/修改 `BODYDATA.DAT` 或任意固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）；
- 未写 shim 代码、未编译、未运行、未跑 pmemsave/解析器。
