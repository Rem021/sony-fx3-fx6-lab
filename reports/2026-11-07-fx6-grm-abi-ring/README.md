# FX6 GRM ABI 核对与 ring 布局结论

日期：2026-11-07（本机 PT 2026-11-06）  
范围：FX6 appFw 的 GRM bitmap API、FX6 UI 分辨率/像素格式、`0x41e000000` ring 容量  
状态：**纯静态研究；未启动/未改动 VM；未解包/修改固件；未改 QEMU/DTB/平台参数；未触碰用户三问**

## 1. 结论

1. **GRM bitmap API 的 ABI 已由 `libgrm_bmp.so` 的日志字符串 + 反汇编 + appFw 调用点三方交叉确认**：
   - `GRM_screenGetOnBitmap(Bitmap **out)`：返回 0，写 bitmap 指针；
   - `GRM_bitmapReadLockBits(Bitmap *, int mode, void **data)`：返回 0/错误，`mode=-1`；
   - `GRM_bitmapReadUnlockBits(Bitmap *)`；
   - `GRM_bitmapGetRectangle(Bitmap *, BMP_RectangleRecord **rect)`：返回 0，写 record 指针；
   - `GRM_bitmapGetFormat(Bitmap *, BMP_PixelFormat *fmt)`：返回 0，写 4 字节 enum；
   - `GRM_bitmapGetSize(Bitmap *, size_t *size)`：返回 0，写 8 字节 size；
   - `GRM_bitmapGetRowBytes(Bitmap *, short *rowBytes)`：返回 0，写 2 字节 row bytes；
   - `GRM_bitmapGetRowPixelCount(Bitmap *, short *w)` / `ColPixelCount(Bitmap *, short *h)`：返回 0，写 2 字节宽/高。
2. **`BMP_PixelFormat` 的 1..10 与 bpp 表已读出**：
   ```text
   1→2, 2→4, 3→2, 4→1, 5→2, 6→2, 7→2, 8→4, 9→4, 10→4
   ```
   `0` 和 `>10` 是非法值。enum 名称未公开，只有数值/bpp 可确认。
3. **FX6 UI 分辨率有本地强证据：1024×540**。`libgrm-fbinit9.c` 明确写：
   ```c
   /* AppFw reports 1024x540 via FrameBuffer::setSize; use the same size ... */
   if (!w) w = 1024; if (!h) h = 540;
   ```
   这是本地 shim 源码注释/默认值，不是 appFw 的独立符号；实际 UI 仍未运行确认。
4. **ring 容量结论：8×0x180000 不够用，推荐 4×0x3c0000。**
   - 1024×540×4 = `0x21C000`（2,211,840），大于单 slot `0x180000`（1,572,864）；
   - 1024×540×2 = `0x10E000`（1,105,920），8×0x180000 可以；
   - 1024×540×1 = `0x87000`，可以；
   - 因为格式在运行前未知，且 4bpp 是合法格式（2/8/9/10），**8×0x180000 不是稳健布局**；
   - 4×0x3c0000：总 `0xF10000`（15,794,176）< 16 MiB（16,777,216），每槽 3.75 MiB，能容纳 1024×540×4，也能容纳 1280×720×4；
   - 如果实际是 1920×1080×4（`0x7E9000`），4×0x3c0000 不够，需要单帧/双帧 ring；但当前没有 1080p UI 的证据。

## 2. 公开资料检索

检索：

- `GRM_bitmapReadLockBits`
- `GRM_bitmapGetFormat`
- `GRM_screenGetOnBitmap`
- `FX6_UX_SCREEN_AREA_1024`
- `Sony GRM BMP PixelFormat`
- `Sony FX6 appFw OSD`

结果：

- **没有找到 Sony GRM/BMP API 的公开文档、头文件或社区一手研究**；
- `BMP_PixelFormat` 的 enum 名称未公开；
- 最接近的社区工具是 [`ma1co/fwtool.py`](https://github.com/ma1co/fwtool.py)，只处理 FDAT/DAT 固件容器，不涉及 GRM/UI；
- 因此本报告的 ABI/格式结论来自本机二进制（`libgrm_bmp.so` 的日志字符串、反汇编、`libgrm-fbinit9.c` 源码），不是公开文档。

## 3. GRM/BMP ABI 证据

### 3.1 `libgrm_bmp.so` 的日志字符串（静态实测）

`libgrm_bmp.so` 内含以下 `BMP_Error` 字符串：

```text
BMP_Error grm::bmp::BMP_GetFormat(Bitmap, BMP_PixelFormat*)
BMP_Error grm::bmp::BMP_GetRowBytes(Bitmap, short int*)
BMP_Error grm::bmp::BMP_GetSize(Bitmap, size_t*)
BMP_Error grm::bmp::BMP_GetRectangle(Bitmap, BMP_RectangleRecord**)
BMP_Error grm::bmp::BMP_GetRowPixelCount(Bitmap, short int*)
BMP_Error grm::bmp::BMP_GetColPixelCount(Bitmap, short int*)
BMP_Error grm::bmp::BMP_GetPixelSortingOrder(Bitmap, BMP_PixelSortingOrder*)
BMP_Error grm::bmp::BMP_GetPixelStartPosition(Bitmap, BMP_PixelStartPosition*)
BMP_Error grm::bmp::BMP_PixelFormatToBytesPerPixel(BMP_PixelFormat, short int*)
```

这比单纯看汇编更强：它是编译进二进制的函数签名/日志字符串。

### 3.2 反汇编交叉确认

`BMP_GetRowPixelCount`（`0x896c`）：

```text
0x899c: mov x19, x1
0x89a0: ldr x1, [x0]
0x89a4: ldr x2, [x1, #0x30]
0x89a8: add x1, x29, #0x28
0x89ac: blr x2
0x89b0: cbz x19, ...
0x89b4: ldr x0, [x29, #0x28]
0x89b8: ldrsh w0, [x0, #4]
0x89bc: strh w0, [x19]
```

`BMP_GetColPixelCount`（`0x89d0`）同样，但读 `[x0, #6]`。

因此：

```text
BMP_RectangleRecord +4 = width  (row pixels)
BMP_RectangleRecord +6 = height (col pixels)
```

这直接确认了 appFw `0x2d61228` 的 `+4/+6` 就是宽/高。

其他函数：

```text
BMP_GetRectangle (0x8104): 调 vtable+0x20，写 rect 指针
BMP_GetFormat    (0x8270): 调 vtable+0x50，写 BMP_PixelFormat
BMP_GetRowBytes  (0x81d0): 调 vtable+0x40，写 short row bytes
BMP_GetSize      (0x8214): 调 vtable+0x48，写 size_t
BMP_GetFormat/Size/Rect 均返回 0 或错误码
```

### 3.3 `GRM` 包装与 appFw 调用点

appFw 的调用点（静态实测）：

```text
0x2d611d4: GRM_screenGetOnBitmap(&bitmap)
0x2d611e4: GRM_bitmapReadLockBits(bitmap, -1, &data)
0x2d611f8: GRM_bitmapGetRectangle(bitmap, &rect)
0x2d61248: GRM_bitmapGetFormat(bitmap, &format)
0x2d61274: GRM_bitmapGetSize(bitmap, &size)
0x2d61294: memcpy(dst, data, size)
0x2d6129c: GRM_bitmapReadUnlockBits(bitmap)
```

因此 `GRM` 层签名与 `BMP` 层一致：

| API | 签名（推断/交叉确认） | 返回/输出 | 证据 |
|---|---|---|---|
| `GRM_screenGetOnBitmap` | `int (Bitmap **out)` | 0；写指针 | appFw `0x2d611d4`；`libgrm` `0x2368c` 写 `[x0]` |
| `GRM_bitmapReadLockBits` | `int (Bitmap *, int mode, void **data)` | 0/错误；写 data | appFw `0x2d611e4`；mode=-1 |
| `GRM_bitmapReadUnlockBits` | `int (Bitmap *)` | 0/错误 | appFw `0x2d6129c` |
| `GRM_bitmapGetRectangle` | `int (Bitmap *, BMP_RectangleRecord **rect)` | 0；写 record 指针 | appFw `0x2d611f8`；rect+4/+6 |
| `GRM_bitmapGetFormat` | `int (Bitmap *, BMP_PixelFormat *fmt)` | 0；写 enum | appFw `0x2d61248`；BMP 签名 |
| `GRM_bitmapGetSize` | `int (Bitmap *, size_t *size)` | 0；写 size | appFw `0x2d61274`；BMP 签名 |
| `GRM_bitmapGetRowBytes` | `int (Bitmap *, short *rowBytes)` | 0；写 2 字节 | 导出符号；BMP 签名 |
| `GRM_bitmapGetRowPixelCount` | `int (Bitmap *, short *w)` | 0；写宽 | 导出符号；BMP 反汇编 |
| `GRM_bitmapGetColPixelCount` | `int (Bitmap *, short *h)` | 0；写高 | 导出符号；BMP 反汇编 |

**注意**：`GRM_bitmapGetRowBytes` / `RowPixelCount` / `ColPixelCount` 没有被 FX6 appFw 导入（appFw 只用 Rectangle/Format/Size），但 `libgrm.so` 导出它们，shim 可以 `dlsym` 调用。

## 4. `BMP_PixelFormat` 与 bpp

`BMP_PixelFormatToBytesPerPixel`（`0x8674`）先检查：

```text
w0 > 0
w0 <= 0xa
```

然后查表：

```text
0xaf58: uint16_t bpp[11]
```

从 `.rodata` 读出：

| `BMP_PixelFormat` | bpp |
|---:|---:|
| 0 | 0（非法） |
| 1 | 2 |
| 2 | 4 |
| 3 | 2 |
| 4 | 1 |
| 5 | 2 |
| 6 | 2 |
| 7 | 2 |
| 8 | 4 |
| 9 | 4 |
| 10 | 4 |
| 11+ | 0（非法） |

结论：

- **4bpp**：format `2/8/9/10`；
- **2bpp**：format `1/3/5/6/7`；
- **1bpp**：format `4`；
- enum 名称/像素排序未公开；`BMP_GetPixelSortingOrder`/`StartPosition` 可以取到运行时的顺序信息，但 enum 语义仍需推断。

## 5. FX6 UI 分辨率：1024×540

`libgrm-fbinit9.c`（本地 shim，路径 `.../cp-helper-agnostic/grm-fbinit/libgrm-fbinit9.c`）：

```c
/* AppFw reports 1024x540 via FrameBuffer::setSize; use the same size for the
 * UX screen area when the screen object still carries 0x0. */
void _ZN3grm11FrameBuffer7setSizeEtt(void *self, unsigned short w, unsigned short h) {
    if (!w) w = 1024; if (!h) h = 540;
    ...
}
```

同时有日志：

```text
FX6_UX_SCREEN_AREA_1024 self=%p x=%d y=%d w=%u h=%u
FX6_GRM_FB_SET_SIZE self=%p w=%u h=%u
```

`libgrm-fbinit9.so` 导出：

```text
FrameBuffer::setSize(unsigned short, unsigned short)
FrameBuffer::initialize(unsigned int, unsigned long)
Screen::setAreaInFramebuffer(short, short, unsigned short, unsigned short)
```

**性质说明**：

- 这是**本地 shim 源码**，不是 Sony appFw 的符号；
- 注释说 “AppFw reports 1024x540”，属于本地开发者对 appFw 行为的记录；
- shim 只在 `w==0 || h==0` 时用 1024×540 兜底；如果 appFw 传入非零值，会保留原值；
- 所以“FX6 UI = 1024×540”是**强本地静态证据**，不是独立运行时确认；没有 FX6 帧可以证明。

## 6. Ring 容量计算

### 6.1 现有 8×0x180000

```text
slot      = 0x180000 = 1,572,864
8 slots   = 0xC00000
header    = 0x10000
total     = 0xC10000 = 12,648,448
reserve   = 0x1000000 = 16,777,216
```

每帧上限约 1.5 MiB。

### 6.2 4×0x3c0000

```text
slot      = 0x3c0000 = 3,932,160
4 slots   = 0xF00000
header    = 0x10000
total     = 0xF10000 = 15,794,176
reserve   = 0x1000000 = 16,777,216
余量      = 0x0F0000 = 983,040
```

每帧上限 3.75 MiB。

### 6.3 1024×540 帧大小

| bpp | 字节数 | 十六进制 | 8×0x180000 | 4×0x3c0000 |
|---:|---:|---:|---|---|
| 1 | 552,960 | `0x87000` | 可 | 可 |
| 2 | 1,105,920 | `0x10E000` | 可 | 可 |
| 4 | 2,211,840 | `0x21C000` | **不可**（>0x180000） | 可 |

### 6.4 其他分辨率

| 分辨率 | 4bpp 字节 | 十六进制 | 8×0x180000 | 4×0x3c0000 |
|---|---:|---:|---|---|
| 1024×540 | 2,211,840 | `0x21C000` | 不可 | 可 |
| 1280×720 | 3,686,400 | `0x384000` | 不可 | 可（余 0x?） |
| 1920×1080 | 8,294,400 | `0x7E9000` | 不可 | 不可 |

1280×720×4 距 `0x3c0000` 还有 `0x3c0000 - 0x384000 = 0x3C000`（245,760）余量；若 row padding 很大，需实测 `size`。

### 6.5 结论

- **8×0x180000**：只适合 1024×540 的 1/2bpp；遇到 4bpp 就装不下。由于 format 在运行前未知，**不推荐作为 FX6 默认**。
- **4×0x3c0000**：覆盖 1024×540 的 1/2/4bpp，也覆盖 1280×720×4；总 0xF10000 < 16 MiB；**推荐作为 FX6 默认布局**。
- **单帧/双帧 ring**：仅当实测帧 >3.75 MiB（例如 1920×1080×4）时才需要；当前没有 1080p UI 证据。单帧 8.29 MiB + header 8.36 MiB 可放进 16 MiB；双帧 16.65 MiB 也能勉强放进 16 MiB（余 ~123 KiB），但无缓冲余量。

## 7. 解析器改造

现有 `osd_ring85.py` 的硬限制：

```text
TOTAL  = 0xc10000
HEADER = 0x10000
STRIDE = 0x180000
SLOTS  = 8
v[7]   <= 1
v[11]  <= 0x12c000
0 < w  <= 640
0 < h  <= 480
```

这些是 FX3 640×480 专用，FX6 1024×540 会被直接拒绝。

建议新增 `osd_ring_fx6.py`（或参数化 `osd_ring85.py`）：

```text
BASE   = 0x41e000000
HEADER = 0x10000
SLOTS  = 4
STRIDE = 0x3c0000
TOTAL  = 0xf10000
MAX_W  = 1024   (或 1280)
MAX_H  = 540    (或 720)
MAX_SPAN = 0x3c0000
```

slot 头沿用 21 QWORD，但字段语义扩展：

```text
v[0]  seq
v[1]  epoch
v[2]  seq（== v[0]）
v[3]  update_id
v[4]  pixel_source_sequence
v[5]  token
v[6]  physical（bitmap/data 指针，非物理地址时填 0）
v[7]  fmt 类别：0=2bpp，1=4bpp（兼容旧解析器）
v[8]  width
v[9]  height
v[10] stride（pixels；= rowBytes / bpp）
v[11] span（bytes；= size）
v[12] FNV64
v[13] bitmap 指针
v[14] data 指针
v[15] allocation
v[16] metadata
v[17] native format（BMP_PixelFormat 原值）
v[18] bpp（1/2/4）
v[19] pixel sorting order / start position（打包）
v[20] config/version
```

- `fmt` 类别用于旧解析器快速判断 2/4bpp；
- `v[17]` 保留原始 `BMP_PixelFormat`，便于后续精确转换；
- `v[18]` 是 bpp，直接用 `BMP_PixelFormatToBytesPerPixel` 或 `rowBytes/width` 得到；
- `v[19]` 可打包 `BMP_GetPixelSortingOrder`/`GetPixelStartPosition`；如果 shim 暂不取，填 0 并标记 unknown；
- `v[12]` 对 `data[0:size]` 计算 FNV64；
- 像素数据从 `slot+0x100` 开始。

## 8. 建议 shim 的精确调用序列

```c
GRM_Bitmap *bmp = NULL;
if (GRM_screenGetOnBitmap(&bmp) || !bmp) return;

void *data = NULL;
if (GRM_bitmapReadLockBits(bmp, -1, &data) || !data) return;

BMP_RectangleRecord *rect = NULL;
BMP_PixelFormat fmt = 0;
short bpp = 0, rowBytes = 0, w = 0, h = 0;
size_t size = 0;

GRM_bitmapGetRectangle(bmp, &rect);
GRM_bitmapGetFormat(bmp, &fmt);
GRM_bitmapGetSize(bmp, &size);
GRM_bitmapGetRowBytes(bmp, &rowBytes);
GRM_bitmapGetRowPixelCount(bmp, &w);
GRM_bitmapGetColPixelCount(bmp, &h);
BMP_PixelFormatToBytesPerPixel(fmt, &bpp);

ring_publish(data, size, w, h, rowBytes, fmt, bpp);
GRM_bitmapReadUnlockBits(bmp);
```

注意：

- 如果 shim 只 hook `GRM_bitmapReadLockBits`，上述 `Get*` 调用应使用 `RTLD_NEXT`，避免递归；
- `GRM_bitmapGetRowBytes` 写 `short`，1024/1280 宽 ×4 仍在 short 范围；
- `rowBytes` 是字节数还是像素数需运行时核对；若 `rowBytes == w`，说明它是像素数，stride 需乘 bpp；
- `size` 应等于 `rowBytes * h`（若 `rowBytes` 为字节）或 `rowBytes * bpp * h`（若为像素）；不一致时以 `size` 为准并记录。

## 9. 验证步骤（本次不执行）

### A. 静态 ABI 核对（已完成部分）

- [x] `BMP` 日志字符串签名；
- [x] `BMP_GetRowPixelCount/ColPixelCount` 读 rect+4/+6；
- [x] format→bpp 表；
- [x] `libgrm-fbinit9.c` 的 1024×540 证据；
- [ ] `rowBytes` 是字节还是像素（需要运行时或 `BMP_GetRowBytes` 实现细节）；
- [ ] `BMP_PixelFormat` enum 名称/像素顺序（需要运行时 `GetPixelSortingOrder`/`StartPosition`）。

### B. 运行时（需另行批准，本次不做）

1. 用 FX6 候选 + GRM shim 启动；
2. QMP `pmemsave 0x41e000000 0x100` + `0xf10000`；
3. 用 `osd_ring_fx6.py` 解析；
4. 检查 `MAGIC`、seq、w/h、span、FNV、非均匀像素；
5. 输出 PNG，检查 UI 文字。

## 10. 仍缺信息

1. FX6 实际 `BMP_PixelFormat`（1..10 中哪个）；决定 2/4bpp。
2. `BMP_PixelFormat` enum 名称、像素排序/起始位置；决定 PNG 的 R/B 通道顺序。
3. `GRM_bitmapGetRowBytes` 返回的是字节还是像素；决定 `stride`。
4. `GRM_bitmapGetRectangle` record 是否还有 padding/对齐字段；`+4/+6` 已确认是宽/高，但 record 总大小未确认。
5. 1024×540 是否为实际 UI；`libgrm-fbinit9.c` 说明是本地 shim 的观察/默认，不是运行时确认。
6. 是否有 1280×720/1920×1080 的 UI 模式；当前无证据。
7. `GRM_bitmapReadLockBits` 的 `mode=-1` 是否表示“全部/只读”；appFw 用法可用，但 enum 名未公开。
8. 无 FX6 实际帧；当前 `GraphicsEngine` 构造 blocked，UI 还没起来。

## 11. 实测 vs 推断

### 静态实测

- `libgrm_bmp.so` 的 `BMP_Error ... (Bitmap, ...)` 日志字符串；
- `BMP_GetRowPixelCount` 读 `[record+4]`、`BMP_GetColPixelCount` 读 `[record+6]`；
- `BMP_PixelFormatToBytesPerPixel` 的 1..10 查表（`.rodata 0xaf58`）；
- `GRM`/`BMP` 函数地址与 appFw 调用点；
- `libgrm-fbinit9.c` 的 1024×540 源码/默认值；
- `guest.dtb` 的 `memrsv=0x01000000@0x41e000000:uc`。

### 推断

- `GRM_*` 包装与 `BMP_*` 同签名；
- 1024×540 是 FX6 UI 的实际尺寸；
- `rowBytes` 是字节数；
- `BMP_PixelFormat` 1..10 的语义来自 bpp 表，不是公开头文件；
- 4×0x3c0000 是默认最优布局。

### 未实测

- 任何 FX6 ring 帧/PNG；
- FX6 实际 format/bpp/rowBytes；
- FX6 UI 是否真的 1024×540；
- shim 运行结果。

## 12. 证据

- `libgrm_bmp.so`：`.../nflasha15-files/lib/libgrm_bmp.so`
  - 日志字符串、`0x8674`、`0xaf58`、`0x896c`、`0x89d0`
- `libgrm.so`：`.../nflasha15-files/lib/libgrm.so`
  - `GRM_bitmapGetRowBytes`/`RowPixelCount`/`ColPixelCount` 导出
- `libgrm-fbinit9.c`：`.../cp-helper-agnostic/grm-fbinit/libgrm-fbinit9.c`
- `libgrm-fbinit9.so`：`.../grm-fbinit/libgrm-fbinit9.so`
- `appFw.so`：`.../nflasha15/lib/appFw.so`，SHA256 `545c5053...`
- `osd_ring85.py`：`.../runtime/osd_ring85.py`
- `guest.dtb`：`memrsv=0x01000000@0x41e000000:uc`

## 13. 边界

- 未启动/未改动任何 VM；
- 未解包/修改 `BODYDATA.DAT` 或任何固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）；
- 未写 `libfx6-grm-ring.so`，未用 `pmemsave` 实跑；这些需另行批准。

## 14. 最终建议

1. **默认 ring 布局选 4×0x3c0000**（总 0xF10000），因为它覆盖 1024×540 的 1/2/4bpp，也覆盖 1280×720×4；
2. **8×0x180000 仅在运行时确认 bpp≤2 且尺寸≤1024×540 时使用**；不要作为默认；
3. **单帧/双帧 ring** 仅在实测帧 >3.75 MiB 时使用（例如 1920×1080×4），当前无证据；
4. **解析器新增 `osd_ring_fx6.py`**，放宽 640×480/0x12c000 限制，并记录 `BMP_PixelFormat`/bpp/pixel order；
5. 在写 shim 前，先补 `rowBytes` 字节/像素语义和 `BMP_PixelFormat` 名称/像素顺序两块静态/运行时证据。
