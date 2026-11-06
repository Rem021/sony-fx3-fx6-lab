# FX6 GRM/BMP 语义核对：rowBytes、pixel order 与 ring 复算

日期：2026-11-07（本机 PT 2026-11-06）  
范围：`BMP_GetRowBytes` 字节/像素语义、`BMP_PixelFormat` 名称/像素顺序、1024×540 ring 复算  
状态：**纯静态研究；未启动/未改动 VM；未解包/修改固件；未改 QEMU/DTB/平台参数；未触碰用户三问**

## 1. 结论

1. **`BMP_GetRowBytes` 返回“字节数”，不是像素数。**
   `BitmapImpl::getRowBytes` 的实现是：
   ```text
   format = *(u32 *)(data + 0x1c)
   bpp    = BMP_PixelFormatToBytesPerPixel(format)
   width  = *(u16 *)(data + 0x18)
   *out   = (u16)(width * bpp)
   ```
   输出类型是 `short*`，所以 `rowBytes` 是 **width × bytesPerPixel** 的**字节数**。
2. **`BMP_GetSize` 与 rowBytes 自洽。**
   `BitmapImpl::getSize` 先调用 `getRowBytes`，再取 `height = *(u16 *)(data + 0x1a)`，最后：
   ```text
   size = height * rowBytes
   ```
   因此 **size = width × bpp × height**，没有额外行 padding（至少 `BitmapImpl` 这层没有）。
3. **`getPixelSortingOrder` / `getPixelStartPosition` 只是读取存储的枚举，不负责命名/排序计算。**
   - `getPixelSortingOrder` 读 `[data+0x38]`；
   - `getPixelStartPosition` 读 `[data+0x3c]`；
   - `BitmapImpl` 构造函数把这两个参数存到 `+0x38/+0x3c`；
   - `BitmapComposite` 的对应 getter 直接写 0（composite 不保存该信息）。
   二进制里**没有** `BMP_PixelFormat` / `BMP_PixelSortingOrder` / `BMP_PixelStartPosition` 的枚举名称字符串（只有 `BMP_PixelFormatNone/Max` 边界）；没有 debug section。因此**名称/通道顺序无法只靠这个二进制恢复**。
4. **appFw 的 `GRM_bitmapCreateFromPhys` 三个调用点都传 format=3、sorting/start=0。**
   - PLT：`0x1593720`；
   - 调用点：`0x2bc7680`、`0x2d3c074`、`0x2d6c1f8`；
   - `w2=3`（format 3，bpp=2）；`[sp]=0`、`[sp+8]=0`（sorting/start）。
   这些是 appFw 自己创建的 bitmap（名称/用途仍需推断），**不能直接当作 on-screen UI bitmap 的格式**。
5. **ring 复算：8×0x180000 装不下 1024×540×4；4×0x3c0000 可行。**
   - 1024×540×4 = `0x21C000`（2,211,840）> `0x180000`（1,572,864）；
   - 4×0x3c0000 总 `0xF10000`（15,794,176）< 16 MiB；
   - 8×0x180000 只在 bpp≤2 时适合；
   - 4×0x3c0000 覆盖 1024×540 的 1/2/4bpp，也覆盖 1280×720×4。
6. **现有 `libgrm-fbinit9` 可能让 `GRM_screenGetOnBitmap` 拿不到 bitmap。**
   该 shim 把 `FrameBuffer::getOnscreen` 直接返回 NULL、`getOnscreenHandle` 返回 0；`libgrm-fbinit14` 也只改了 `initialize`，`getOnscreen` 仍是 NULL。若 `GRM_screenGetOnBitmap` 依赖这个 FrameBuffer，OSD worker 会读不到屏幕 bitmap。这是环境风险，不是 ABI 问题。

## 2. 快速公开复核

本次只做快速复核：

- `BMP_PixelFormat Sony GRM`
- `BMP_PixelSortingOrder BMP_PixelStartPosition`
- `BitmapImpl getRowBytes Sony`

结果：

- 没有 Sony GRM/BMP API 文档、头文件或社区一手研究；
- 结果都是通用 BMP/Java/Android 或无关厂商页面；
- 前两份报告已确认无 Sony GRM 公开文档；本次不重复纠缠。

因此本报告的结论全部来自本机 `libgrm_bmp.so`/`appFw.so` 的静态反汇编与日志字符串。

## 3. `BMP_GetRowBytes`：字节，不是像素

### 3.1 `BitmapImpl::getRowBytes`（0x6698）

反汇编：

```text
0x6698: cbz x1, 0x6704          ; out == NULL -> return
0x66a8: mov x20, x0             ; this
0x66ac: ldr x0, [x0, #8]        ; data = this->data
0x66b0: mov x19, x1             ; out (short*)
0x66b4: add x1, x29, #0x2e      ; &bpp
0x66b8: ldr w0, [x0, #0x1c]     ; format = data+0x1c
0x66bc: bl  #0x5cf0             ; BMP_PixelFormatToBytesPerPixel(format, &bpp)
0x66c0: cbz w0, 0x66e4
...
0x66e4: ldr x0, [x20, #8]       ; data
0x66e8: ldrh w1, [x29, #0x2e]   ; bpp
0x66ec: ldrh w0, [x0, #0x18]    ; width = data+0x18
0x66f0: mul w0, w0, w1          ; width * bpp
0x66f4: strh w0, [x19]          ; *out = rowBytes
0x66f8: ret
```

结论：

```text
rowBytes = width * bytesPerPixel
```

不是 `width`（像素），也不是 `width * 4` 固定值；它按当前 format 的 bpp 计算。

### 3.2 `BitmapImpl::getSize`（0x61f4）

反汇编：

```text
0x61f8: ...
0x6218: blr x2                  ; vtable+0x40 = getRowBytes
0x621c: ldr x0, [x20, #8]       ; data
0x6220: ldrsh w1, [x29, #0x2e]  ; rowBytes
0x6224: ldrsh w0, [x0, #0x1a]   ; height = data+0x1a
0x6228: smull x0, w0, w1        ; height * rowBytes
0x622c: str x0, [x19]           ; *out = size
0x6230: ret
```

结论：

```text
size = height * rowBytes = width * bpp * height
```

`BitmapImpl` 这层没有额外 padding；`BMP_GetRowBytes` 的 `short` 输出与 `BMP_GetSize` 的 `size_t` 输出是自洽的。

### 3.3 appFw 调用点交叉

appFw 的 `GRM` 读屏函数 `0x2d6116c` 使用：

```text
GRM_bitmapGetRectangle  -> width/height
GRM_bitmapGetFormat     -> format
GRM_bitmapGetSize       -> size
GRM_bitmapReadLockBits  -> data
memcpy(dst, data, size)
```

**appFw 没有导入 `GRM_bitmapGetRowBytes`**（`nm -D` 无该符号）；它只依赖 `GetSize`。因此：

- `rowBytes` 的字节语义由 `BitmapImpl` 实现确认；
- `size` 由 `getSize` 确认等于 `rowBytes*height`；
- 在 shim 里可以额外调用 `GRM_bitmapGetRowBytes`，但这不是 appFw 原路径。

appFw 的 `GRM_bitmapCreateFromPhys` 调用点：

```text
PLT 0x1593720
0x2bc7680
0x2d3c074
0x2d6c1f8
```

三个调用点都在 `x2` 传入 **3**（format 3），`[sp]`/`[sp+8]` 传 **0**（sorting/start）。这说明 appFw 自己创建的某些 bitmap 是 **format 3、2bpp、sorting/start 0**；但它们不是 on-screen UI bitmap，不能直接外推到 `GRM_screenGetOnBitmap` 的返回值。

## 4. `getPixelSortingOrder` / `getPixelStartPosition`

### 4.1 `BitmapImpl`

`getPixelSortingOrder`（0x6544）：

```text
0x656c: ldr x0, [x21, #8]   ; data
0x6570: ldr w0, [x0, #0x38] ; sorting order
0x6574: str w0, [x20]       ; *out
```

`getPixelStartPosition`（0x658c）：

```text
0x65b4: ldr x0, [x21, #8]
0x65b8: ldr w0, [x0, #0x3c] ; start position
0x65bc: str w0, [x20]       ; *out
```

构造函数 `0x6ab8`：

```text
0x6b70: stp w23, w22, [x0, #0x1c]  ; format +0x1c, YUV mode +0x20
0x6b74: stp w21, w20, [x0, #0x38]  ; sorting +0x38, start +0x3c
```

所以：

- `+0x1c` = `BMP_PixelFormat`；
- `+0x20` = `BMP_YUVMode`；
- `+0x38` = `BMP_PixelSortingOrder`；
- `+0x3c` = `BMP_PixelStartPosition`；
- `+0x18/+0x1a` = width/height（`getRowBytes`/`getSize` 使用）。

### 4.2 `BitmapComposite`

`BitmapComposite::getPixelSortingOrder`（0x7204）和 `getPixelStartPosition`（0x7210）：

```text
0x7204: cbz x1, 0x720c
0x7208: str wzr, [x1]   ; 0
0x720c: ret
```

Composite 不保存排序/起始位置，统一返回 0。

### 4.3 enum 名称不可得

`strings libgrm_bmp.so` 只含：

```text
BMP_PixelFormatNone
BMP_PixelFormatMax
BMP_PixelSortingOrder
BMP_PixelStartPosition
```

没有 `RGBA/BGRA/ARGB/RGB565/YUV422` 等名称；`readelf -S` 没有 `.debug` 段。因此：

- **format 数值与 bpp 表**可确认（1..10 → 2/4/1/...）；
- **format 名称/通道顺序**不可仅凭此二进制恢复；
- **sorting/start 数值**可读，但枚举名/语义不可得。

### 4.4 appFw 的 format 3

三个 `GRM_bitmapCreateFromPhys` 调用点都传：

```text
w2 = 3       ; BMP_PixelFormat = 3
[sp] = 0     ; BMP_PixelSortingOrder = 0
[sp+8] = 0   ; BMP_PixelStartPosition = 0
```

format 3 在 bpp 表中是 **2bpp**。这至少证明 appFw 的某些 bitmap 是 2bpp、sorting/start 0；但 on-screen UI bitmap 由 libgrm/FrameBuffer 创建，不能据此断言 UI 是 2bpp。

## 5. 1024×540 与 ring 复算

### 5.1 1024×540 帧大小

| bpp | 字节 | 十六进制 | 8×0x180000 | 4×0x3c0000 |
|---:|---:|---:|---|---|
| 1 | 552,960 | `0x87000` | 可 | 可 |
| 2 | 1,105,920 | `0x10E000` | 可 | 可 |
| 4 | 2,211,840 | `0x21C000` | **不可** | 可 |

### 5.2 布局

```text
8×0x180000:
  slot 0x180000, 8 slots = 0xC00000, +header 0x10000 = 0xC10000
4×0x3c0000:
  slot 0x3c0000, 4 slots = 0xF00000, +header 0x10000 = 0xF10000
reserve = 0x1000000
```

### 5.3 其他分辨率

| 分辨率 | 4bpp | 8×0x180000 | 4×0x3c0000 |
|---|---:|---|---|
| 1024×540 | `0x21C000` | 不可 | 可 |
| 1280×720 | `0x384000` | 不可 | 可（余 0x3C000） |
| 1920×1080 | `0x7E9000` | 不可 | 不可 |

### 5.4 结论

- **默认 4×0x3c0000**：覆盖 1024×540 的 1/2/4bpp，也覆盖 1280×720×4；总 0xF10000 < 16 MiB。
- **8×0x180000**：只在确认 bpp≤2（format 1/3/4/5/6/7）时可用；4bpp 时单槽装不下。**不推荐作为默认**。
- **单帧/双帧 ring**：仅在实测 >3.75 MiB/帧时使用（如 1920×1080×4）；当前无证据。
- 若实际 1024×540、format 3（2bpp），8×0x180000 也能装；但 on-screen format 未确认，不能据此选 8×。

## 6. 解析器字段修正

现有 `osd_ring85.py` 的 `v[10]` 是 **stride（pixels）**，不是 rowBytes。FX6 应填：

```text
v[7]  fmt 类别：0=2bpp，1=4bpp（兼容旧解析器）
v[8]  width
v[9]  height
v[10] stride（pixels）= rowBytes / bpp
v[11] span（bytes）= size
v[12] FNV64
v[17] BMP_PixelFormat 原值
v[18] bpp
v[19] pixel sorting order / start position（打包）
```

其中：

```text
rowBytes = width * bpp
size     = height * rowBytes
stride   = rowBytes / bpp = width
```

如果 `BitmapImpl` 的 `GetRectangle` width/height 与 `GetRowPixelCount/ColPixelCount` 一致，`stride == width`；如果存在 padding，`size` 会大于 `height*width*bpp`，此时以 `size`/`rowBytes` 为准，并记录差异。

`osd_ring85.py` 的 640×480/0x12c000/8×0x180000 限制必须放宽；建议新建 `osd_ring_fx6.py`：

```text
SLOTS=4
STRIDE=0x3c0000
TOTAL=0xf10000
MAX_W=1024 (或 1280)
MAX_H=540  (或 720)
MAX_SPAN=0x3c0000
```

## 7. `libgrm-fbinit9` 的 `getOnscreen=NULL` 风险

`libgrm-fbinit9.c`：

```c
void *FrameBuffer::getOnscreen(void *self) {
    dprintf(2, "FX6_GRM_FB_GET_ONSCREEN_SKIP self=%p result=NULL\n", self);
    return (void *)0;
}
unsigned int FrameBuffer::getOnscreenHandle(void *self) { return 0; }
```

`libgrm-fbinit14.c` 只把 `FrameBuffer::initialize` 改成调用 real，`getOnscreen` 仍是 NULL。

风险：

- 若 `GRM_screenGetOnBitmap` 依赖 `FrameBuffer::getOnscreen`，它会拿到 NULL；
- OSD worker 的 `GRM_screenIsDirty`/`screenGetOnBitmap` 可能直接失败；
- 即使 GRM shim 写好，没有 screen bitmap 也不会有帧；
- 这可能是当前 FX6 没有 OSD 帧的原因之一，但本轮没有运行时验证。

## 8. 实测 vs 推断

### 反汇编实证

- `BitmapImpl::getRowBytes`：`rowBytes = width * bpp`，写 `short*`；
- `BitmapImpl::getSize`：`size = height * rowBytes`，写 `size_t`；
- `BitmapImpl::getPixelSortingOrder`：读 `[data+0x38]`；
- `BitmapImpl::getPixelStartPosition`：读 `[data+0x3c]`；
- `BitmapImpl` ctor：format/YUV 在 `+0x1c/+0x20`，sorting/start 在 `+0x38/+0x3c`；
- `BMP_PixelFormatToBytesPerPixel` 的 1..10 → bpp 表；
- appFw 三个 `CreateFromPhys` 调用点 `w2=3`、sorting/start=0；
- `libgrm-fbinit9.c` 的 `getOnscreen=NULL`/`setSize` 默认 1024×540。

### 推断

- 1024×540 是实际 UI 尺寸（来自本地 shim 注释，不是运行时）；
- 4×0x3c0000 是最优默认布局；
- appFw 的 format 3 不代表 on-screen UI 也是 format 3；
- `GRM_screenGetOnBitmap` 可能受 `getOnscreen=NULL` 影响。

### 未实测

- 没有 FX6 ring 帧/PNG；
- 没有 `FX6_GRM_FB_SET_SIZE` 的实际 w/h serial 日志；
- 没有运行 shim；
- 没有确认 on-screen bitmap 的 format/sorting/start。

## 9. 证据

- `libgrm_bmp.so`：`.../nflasha15-files/lib/libgrm_bmp.so`
  - `BitmapImpl::getRowBytes` 0x6698
  - `BitmapImpl::getSize` 0x61f4
  - `getPixelSortingOrder` 0x6544 / `getPixelStartPosition` 0x658c
  - `BitmapImpl` ctor 0x6ab8
  - `BMP_PixelFormatToBytesPerPixel` 0x8674 / 表 0xaf58
- `libgrm.so`：`.../nflasha15-files/lib/libgrm.so`，导出 `GRM_bitmapGetRowBytes`/`RowPixelCount`/`ColPixelCount`
- `appFw.so`：`.../nflasha15/lib/appFw.so`
  - `GRM_bitmapCreateFromPhys` PLT 0x1593720
  - 调用点 0x2bc7680 / 0x2d3c074 / 0x2d6c1f8
- `libgrm-fbinit9.c`：`.../cp-helper-agnostic/grm-fbinit/libgrm-fbinit9.c`
- `osd_ring85.py`：`.../runtime/osd_ring85.py`
- `guest.dtb`：`memrsv=0x01000000@0x41e000000:uc`

## 10. 边界

- 未启动/未改动任何 VM；
- 未解包/修改 `BODYDATA.DAT` 或任何固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）；
- 未写 shim、未用 `pmemsave` 实跑；需另行批准。

## 11. 仍缺什么

1. `BMP_PixelFormat` 名称/通道顺序（二进制无 enum 名称、无 debug；需运行时或外部头文件）。
2. `BMP_PixelSortingOrder`/`BMP_PixelStartPosition` 的枚举语义/名称（同上）。
3. on-screen bitmap 的实际 format/sorting/start（由 libgrm/FrameBuffer 创建，不在 appFw 的 CreateFromPhys 调用点）。
4. `GRM_screenGetOnBitmap` 是否受 `FrameBuffer::getOnscreen=NULL` 影响（需要运行时或更深的 libgrm 反汇编）。
5. 1024×540 是否为实际 UI（本地 shim 注释/默认值，不是运行时确认）。
6. 实际帧是否 4bpp（决定 4×0x3c0000 是否必要；当前选 4×3.75 MiB 是保守方案）。

## 12. 建议

- **ring 默认选 4×0x3c0000**，不要用 8×0x180000 作为 FX6 默认；
- 解析器新增 `osd_ring_fx6.py`，`v[10]=rowBytes/bpp`、`v[11]=size`、`v[17]=format`、`v[18]=bpp`、`v[19]=sorting/start`；
- 在写 shim 前，先确认 `GRM_screenGetOnBitmap` 是否受 `getOnscreen=NULL` 影响；如果是，需要先补真实的 FrameBuffer/onscreen bitmap，否则 shim 抓不到帧；
- 实跑 `pmemsave` 仍需用户批准。
