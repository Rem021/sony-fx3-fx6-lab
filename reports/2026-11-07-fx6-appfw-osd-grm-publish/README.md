# FX6 appFw OSD/GRM 发布点静态定位

日期：2026-11-07（巡查时间；本机 PT 2026-11-06）  
范围：FX6 appFw 的屏幕/OSD 帧发布路径，只读静态分析  
状态：**未启动/未改动任何 VM；未解包/修改固件；未改 QEMU/DTB/平台参数；未触碰用户三问**

## 1. 结论

1. **FX6 appFw 本身不包含 `OSDRING1` / `0x41e000000` 字符串**。`0x41e000000` ring 是 FX3 项目侧 `fx3-osd-headless` 的测试约定，不是 FX6 原生协议。
2. 但当前 FX6 使用的 `guest.dtb` **已经保留** `0x01000000@0x41e000000:uc`（16 MiB），近期 FX6 serial 也都出现该 `memrsv`。所以 ring 的物理内存已经存在，缺的是**发布者**。
3. 静态定位到 FX6 的原生帧源：
   - `GRM_screenGetOnBitmap` + `GRM_bitmapReadLockBits`；
   - 读取函数 `0x2d6116c`；
   - worker 链 `0x2d61f44 → 0x2d61da4 → 0x2d6116c`；
   - `GRM_fbrmRegisterDrawCompletionCb` 的封装在 `0x2d610b4`，注册调用在 `0x2d61f5c`。
4. 该路径把屏幕 bitmap 复制到 `this+0x12c000+0x1b9`，**不是** `0x41e000000`。要复用现有 ring，需要新增一个 **GRM interposer**，在 `GRM_bitmapReadLockBits` 返回后把 bitmap 复制到 ring。
5. 现有 `osd_ring85.py` 的解析上限是 **640×480、fmt 0/1、span ≤ 0x12c000、8×0x180000 slot**。如果 FX6 UI 大于 640×480 或每像素 4 字节，**当前 ring 布局装不下**，必须调整 slot 数/stride 或改成单帧 ring。
6. 本次没有 FX6 可见帧；没有 `FX3_OSD_HEADLESS_*`/ring magic/PNG。文末明确区分“静态实测”和“推断”。

## 2. 公开资料检索

检索了：

- `FX6 appFw OSD GPE framebuffer`
- `Sony camera GraphicsEngine Screen3D OSD reverse engineering`
- `libuxengine GraphicsEngine Sony camera`
- `Sony GPE DMM framebuffer camera firmware`
- `vdf_set_osd_layout` / `osd_transfer_sender` / `MPGRM OSD` / `vga_cache_osd`
- `GRM_screenGetOnBitmap` / `GRM_bitmapReadLockBits` / `GRM_fbrmRegisterDrawCompletionCb`

结果：

- **没有找到 Sony GRM/OSD API 的公开文档或社区一手研究**；
- 唯一接近的社区资料是 [`ma1co/fwtool.py`](https://github.com/ma1co/fwtool.py) 等 Sony 固件容器工具，它们只处理 FDAT/DAT，不覆盖 UI/OSD；
- `WidgetSystem`、`Screen3D` 等搜索结果与 Sony 无关；
- `0x41e000000` ring 是**本项目 FX3 侧自建测试结构**，不是公开 Sony 协议。

因此，本报告的 FX6 发布路径全部来自**本机 appFw 静态反汇编**，不是公开文档。

## 3. FX6 appFw 静态结构

### 3.1 文件

```text
path: .../sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so
size: 79,015,712
sha256: 545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f
```

ELF：

```text
.plt  = 0x15918c0 (size 0x2dc0)
.text = 0x1594680 (size 0x19f4548)
```

### 3.2 相关导入

```text
U GRM_screenGetOnBitmap
U GRM_bitmapReadLockBits
U GRM_bitmapReadUnlockBits
U GRM_bitmapGetRectangle
U GRM_bitmapGetFormat
U GRM_bitmapGetSize
U GRM_fbrmRegisterDrawCompletionCb
U _ZN2ux6gfxeng14GraphicsEngine15drawFramebufferEv
U _ZN2ux6wgtsys12WidgetSystem11updateFrameEv
U _ZN2ux6wgtsys12WidgetSystem10notifyDrawEv
U _ZN2ux6wgtsys12WidgetSystem15sys_getInstanceEv
U _ZN8UXEngine6gfxengEv
```

### 3.3 OSD/VDF 字符串

```text
_INFRA_PIN_ATOM(MPGRM, OSD, INOUT, 0)
_INFRA_PIN_ATOM(VDF, OSD, INOUT, 0)
sequence_playback_vga_cache_osd
vdf_set_osd_layout
VDF SET_OSD_ON_OFF
set_yuv_osd_disp_pattern
osd_transfer_sender
```

`osd_transfer_sender` 在文件偏移 `0x2f91ba8`，带长度前缀 `19`，**很像线程名**。这一点是推断，未在运行时验证。

### 3.4 没有 ring 原生字符串

`strings appFw.so` 检索：

```text
OSDRING / 0x41e000000 / 41e000000 / OSD_HEADLESS / FX3_OSD
```

**无结果**。因此 FX6 appFw 不直接写 FX3 的 ring。

## 4. 原生帧源与 worker 链

### 4.1 UI 帧循环

`GraphicsEngine::drawFramebuffer`：

```text
0x16f1a0c: bl  WidgetSystem::notifyDraw
0x16f1a14: bl  ...
0x16f1a18: bl  UXEngine::gfxeng
0x16f1a1c: bl  GraphicsEngine::drawFramebuffer
0x16f1a38: bl  WidgetSystem::updateFrame
```

这是 **UI 渲染/提交**路径。它是 FX6 的 `GraphicsEngine`/`WidgetSystem`，不是 FX3 的 `libObj` OSD shim。

### 4.2 GRM 读屏函数 `0x2d6116c`

关键指令：

```text
0x2d61188: bl  GRM_screenIsDirty
0x2d611d4: bl  GRM_screenGetOnBitmap
0x2d611e4: bl  GRM_bitmapReadLockBits
0x2d611f8: bl  GRM_bitmapGetRectangle
0x2d61248: bl  GRM_bitmapGetFormat
0x2d61274: bl  GRM_bitmapGetSize
0x2d61294: bl  memcpy
0x2d6129c: bl  GRM_bitmapReadUnlockBits
```

数据流：

```text
screenGetOnBitmap(&bitmap)
bitmapReadLockBits(bitmap, -1, &data)
bitmapGetRectangle(bitmap, &rect)
  width  = *(int16*)(rect + 4)  -> this+0x258238
  height = *(int16*)(rect + 6)  -> this+0x25823c
bitmapGetFormat(bitmap, &format) -> this+0x258240
bitmapGetSize(bitmap, &size)     -> this+0x258248
memcpy(this+0x12c000+0x1b9, data, size)
bitmapReadUnlockBits(bitmap)
```

**这是 FX6 的屏幕 bitmap 读出点**。`rect+4/+6` 的语义（width/height 还是 x/y）是**推断**，需运行时确认；`format`/`size` 的输出指针是从调用点反推的，头文件未公开。

### 4.3 worker 链

```text
0x2d61f44  worker（无直接 bl 调用者，像线程入口）
  0x2d61f5c: bl 0x2d610b4   ; 注册 draw completion callback
  0x2d61f6c: bl 0x2d61da4   ; 处理循环
      0x2d61e78: bl 0x2d6116c ; 读屏
```

`0x2d61da4` 内还有 `0x2d61e78` 前后的 OSD/YUV 处理；`0x2d61f44` 末尾的队列等待（`0x2aa1ea8`/`0x29501b4`）符合 **worker 线程**。

`0x2d610b4`：

```text
0x2d610b8: mov x1, x0          ; callback/context
0x2d610cc: ldr x0, [x0, #0xd48] ; GRM handle
0x2d610d0: bl GRM_fbrmRegisterDrawCompletionCb
0x2d610f8: set byte [this+0x2581bb] = 1
```

注册成功后在 `this+0x2581bb` 置 1。`x1` 到底是函数指针还是 `this`/functor，**未完全证明**；从调用点看它传的是 `x0=this`，可能 API 期望 `(handle, context)` 或 `(handle, callback)`，需要 GRM 头文件/运行时确认。

## 5. 是否使用 `0x41e000000` ring

**不使用。** 依据：

- appFw 中没有 `OSDRING`/`0x41e000000` 字符串；
- `0x2d6116c` 的目标是 `this+0x12c000+0x1b9`，不是 `0x41e000000`；
- `0x41e000000` 只在 FX3 的 `fx3-osd-headless`/`osd_ring85.py` 里定义。

但：

```text
guest.dtb: memrsv=0x01000000@0x41e000000:uc
recent FX6 serial: memrsv=0x01000000@0x41e000000:uc
```

16 MiB 已经保留，且是 uncached。**ring 可以复用，但必须由新 shim 写入**；FX6 appFw 不会自己写。

## 6. 建议的 FX6 抓帧 shim

### 6.1 方案 A（推荐）：hook `GRM_bitmapReadLockBits`

`LD_PRELOAD` 一个 `libfx6-grm-ring.so`：

```c
int GRM_bitmapReadLockBits(GRM_Bitmap *bmp, int mode, void **data) {
    int rc = real_GRM_bitmapReadLockBits(bmp, mode, data);
    if (rc == 0 && data && *data) {
        GRM_Rect rect; uint32_t fmt = 0; size_t size = 0;
        real_GRM_bitmapGetRectangle(bmp, &rect);
        real_GRM_bitmapGetFormat(bmp, &fmt);
        real_GRM_bitmapGetSize(bmp, &size);
        ring_publish(*data, size, rect, fmt);
    }
    return rc;
}
```

优点：

- 只 hook 一个导出 API；
- 不需要理解 `GraphicsEngine`/`WidgetSystem` 内部对象；
- 在 appFw 的 `memcpy` 之前拿到原始 bitmap；
- appFw 自己的 `bitmapReadUnlockBits` 仍然正常执行。

注意：

- `GRM_bitmapGetRectangle/Format/Size` 的签名是从 appFw 调用点反推的，需要先做 ABI 静态核对；
- `GRM_bitmapReadLockBits` 可能被其他模块调用；可以用 `__builtin_return_address(0)` 限定 `0x2d611e4` 的调用者，或只处理 `mode=-1`；
- 复制必须在 unlock 之前完成；不要在 hook 里调用 appFw 的 unlock。

### 6.2 方案 B：hook `GRM_screenGetOnBitmap`

- 更靠上，能拿到“屏幕 bitmap”；
- 但此时还没 lock，像素可能正在更新；
- 需要自己调用 `GRM_bitmapReadLockBits` 并解锁，可能与 appFw 的锁竞争；
- 不如 A 稳。

### 6.3 方案 C：hook `GRM_fbrmRegisterDrawCompletionCb`

- 可以包住 appFw 注册的回调，在每帧完成时读屏；
- 但 callback ABI 未证明（`x1` 是函数指针还是 context），风险最高；
- 只作为 B 的备选。

## 7. 帧字段与解析

### 7.1 现有 ring

```text
BASE   = 0x41e000000
TOTAL  = 0xc10000
HEADER = 0x10000
STRIDE = 0x180000
MAGIC  = 0x31474e495244534f
SLOTS  = 8
```

`osd_ring85.py` 的 slot 头是 21 个 QWORD：

```text
v[0]  seq
v[1]  epoch
v[2]  seq（必须等于 v[0]）
v[3]  update_id
v[4]  pixel_source_sequence
v[5]  token
v[6]  physical
v[7]  fmt（0=16-bit，1=32-bit）
v[8]  width
v[9]  height
v[10] stride（pixels）
v[11] span（bytes）
v[12] fnv64
v[13..20] native identity
```

像素从 `slot+0x100` 开始；`osd_ring85.py` 会检查：

```text
v[0]==v[2]
v[1]==global_epoch
v[11] <= 0x12c000
v[7] <= 1
0 < w <= 640
0 < h <= 480
stride >= w
```

### 7.2 FX6 需要新增/修改的字段

| 字段 | 来源 | 状态 |
|---|---|---|
| width | `GRM_bitmapGetRectangle` +4 | 静态推断 |
| height | `GRM_bitmapGetRectangle` +6 | 静态推断 |
| format | `GRM_bitmapGetFormat` | 静态实测调用 |
| size/span | `GRM_bitmapGetSize` | 静态实测调用 |
| data | `GRM_bitmapReadLockBits` | 静态实测调用 |
| stride | `size / height`（若 packed） | **推断**，需运行时核对 |
| FNV64 | 对 data[0:size] 计算 | 设计 |
| seq/epoch | shim 维护 | 设计 |
| physical/token | bitmap/data 指针或 0 | 设计，非原生 |

### 7.3 现有 ring 的容量风险

- 640×480×4 = 1,228,800 (0x12c000)，刚好是 `osd_ring85.py` 的 `v[11]` 上限；
- 1280×720×4 = 3,686,400 (0x384000)，**大于 slot stride 0x180000**；
- 8×0x180000 = 0xc00000，加 header 0x10000 = 0xc10000，正好是当前 TOTAL；
- 若 FX6 帧 >1.5 MiB，当前 8-slot ring **装不下**，必须：
  - 改成 4 slots × 0x3c0000（约 3.75 MiB/槽，4×3.75=15 MiB + header，仍 <16 MiB）；或
  - 改成单帧/双帧 ring；或
  - 降低分辨率/格式。

**这是复用 ring 前必须确认的第一件事。**

## 8. 验证步骤（本次不执行）

### A. 静态 ABI 核对（不需要 VM）

1. 从 `libgrm.so` 的导出表确认 `GRM_bitmapReadLockBits`/`GRM_bitmapGetRectangle`/`GRM_bitmapGetFormat`/`GRM_bitmapGetSize` 的签名；
2. 用 appFw 调用点的寄存器用法交叉验证；
3. 确认 `GRM_bitmapGetRectangle` 的 `+4/+6` 是宽高还是坐标；
4. 确认 `GRM_bitmapGetFormat` 的枚举值与 ring `fmt` 的映射；
5. 确认 `GRM_bitmapGetSize` 是否等于 `stride*height`。

### B. 运行时抓帧（需另行批准，本次不做）

1. 用 FX6 候选 + `libfx6-grm-ring.so` 启动；
2. QMP `pmemsave 0x41e000000 0x100` + `0x1000000`；
3. 用新解析器检查 magic/seq/width/height/stride/span/fnv；
4. 输出 PNG，检查非均匀像素和 UI 文字；
5. 如果 `v[11] > 0x12c000` 或 `w>640`/`h>480`，改用新 ring 布局/新解析器。

### C. 失败判定

- 没有 `FX6_GRM_RING_*` 标记 → hook 没被调用；
- `GRM_bitmapReadLockBits` 返回非 0 → 读锁失败；
- `size/height` 不是整数 → stride 假设错误；
- `fmt` 不在 0/1 → 需要新增格式；
- 环里 magic 不对 → shim 没写 header；
- 有帧但全黑 → 读的是错误 bitmap 或 `screenIsDirty` 未触发。

## 9. 仍缺信息

1. FX6 UI 的实际分辨率/像素格式；是否会超过 640×480/1.5 MiB。
2. `GRM_bitmapGetRectangle` 的 `+4/+6` 字段语义（w/h 还是 x/y）。
3. `GRM_bitmapGetFormat` 枚举到 ring `fmt` 的映射（16-bit 565 / 32-bit BGRA / RGBA）。
4. `GRM_bitmapGetSize` 是否包含 padding；`stride` 能否由 `size/height` 得到。
5. `GRM_fbrmRegisterDrawCompletionCb` 的 `x1` 是 callback 还是 context；`0x2d610b4` 的 ABI 未证明。
6. `0x2d61f44` 是否就是 `osd_transfer_sender` 线程体；字符串/无调用者只是强推断。
7. 该路径是**相机 LCD** 还是**HDMI/VGA OSD**；`vga_cache_osd` 名字暗示外部输出，但 `GRM_screenGetOnBitmap` 是 on-screen bitmap，需运行时区分。
8. `/dev/mem` 在 FX6 appFw 进程里是否可映射 `0x41e000000`；FX3 shim 可以，FX6 未验证。
9. FX6 appFw 目前还没跑到 UI（`GraphicsEngine` 构造仍 blocked）；即使 shim 就绪，也要先让 UI 起来。

## 10. 实测 vs 推断

### 静态实测

- appFw 文件大小/SHA256；
- `.plt`/`.text` 地址；
- `nm -D` 导入表；
- `strings` 中 `OSDRING` 无结果、`osd_transfer_sender` 存在；
- 0x16f1a1c / 0x16f1a38 / 0x2d61f5c / 0x2d61f6c / 0x2d61e78 等 `bl` 调用点；
- 0x2d611d4 / 0x2d611e4 / 0x2d611f8 / 0x2d61248 / 0x2d61274 / 0x2d61294 / 0x2d6129c 的 GRM 调用；
- DTB 与近期 serial 的 `memrsv=0x01000000@0x41e000000:uc`。

### 推断

- `0x2d61f44` 是 `osd_transfer_sender` 线程体；
- `0x2d6116c` 读的是相机 LCD 的 on-screen bitmap；
- `rect+4/+6` 是 width/height；
- `stride = size/height`；
- `0x41e000000` ring 可被新 shim 复用；
- `GRM_fbrmRegisterDrawCompletionCb` 的 `x1` 语义。

### 未实测

- 没有任何 FX6 OSD ring 帧/PNG；
- 没有运行 `libfx6-grm-ring.so`；
- 没有确认 FX6 UI 分辨率/格式；
- 没有确认 `GRM` 读锁在 FX6 进程里的实际返回。

## 11. 证据

- appFw：`.../nflasha15/lib/appFw.so`，79,015,712，SHA256 `545c5053...`
- `osd_ring85.py`：`.../fx3-vm-20261101/menu-repair-01/runtime/osd_ring85.py`
- FX3 PNG：`.../runtime/ap103v4ldec600-71ce5752-final-committed.png`，640×480，SHA256 `e2228181...`
- FX3 ring 预留：`guest.dtb` / serial `memrsv=0x01000000@0x41e000000:uc`
- QEMU 显示后端报告：`reports/2026-11-06-qemu-display-backends/README.md`
- 公开工具：[`ma1co/fwtool.py`](https://github.com/ma1co/fwtool.py)（只覆盖固件容器，不覆盖 OSD）

## 12. 边界

- 未启动/未改动任何 VM；
- 未解包/修改 `BODYDATA.DAT` 或任何固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）；
- 实际跑 VM 抓 ring 需要另行批准，本次未做。

## 13. 建议下一步

1. **先做静态 ABI 核对**：`GRM_bitmapReadLockBits`/`GetRectangle`/`GetFormat`/`GetSize` 的签名与枚举；
2. 再决定 ring 布局：如果 FX6 帧 ≤640×480×4，复用现有 8×0x180000；否则改成 4×0x3c0000 或单帧 ring；
3. 写 `libfx6-grm-ring.so`（只读、无 guest ACK），用 `pmemsave` 验证；
4. 在 UI 起来之前，shim 不会产生帧；当前 `GraphicsEngine` blocked 仍是前置条件。
