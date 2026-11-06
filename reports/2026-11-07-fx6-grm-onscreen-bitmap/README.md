# FX6 GRM on-screen bitmap 静态补研

日期：2026-11-07（本机 PT 2026-11-06）  
范围：`GRM_screenGetOnBitmap` 对 `FrameBuffer::getOnscreen` 的依赖、on-screen BMP 创建点、实际 format/sorting/start  
状态：**纯静态研究；未启动/未改动 VM；未解包/修改固件；未改 QEMU/DTB/平台参数；未触碰用户三问**

## 1. 结论

1. **`GRM_screenGetOnBitmap` 确实依赖 `FrameBuffer::getOnscreen`。**
   调用链：
   ```text
   GRM_screenGetOnBitmap (libgrm 0x2368c)
     -> FBResourceManager::getInstance  (PLT 0x1fe00)
     -> FBResourceManager::getOnscreen  (PLT 0x1f970, libgrm 0x22ad8)
        ldr x0,[manager+8]              ; FrameBuffer*
        b   FrameBuffer::getOnscreen    ; PLT 0x1fa50
     -> FrameBuffer::getOnscreen        (0x231e4)
        ldr x0,[fb+0x68]                ; &fb->onscreen slot
        ldr x0,[x0]                     ; BMP*
   ```
2. **on-screen BMP 的实际创建点是 `FrameBuffer::update`（0x230b8），不是 `getOnscreen` 本身。**
   `update` 对 `fb+0x20`（on-screen）和 `fb+0x40`（off-screen）两个 slot 调用：
   ```text
   BMP_CreateFromPhys(width  = [fb+0x14],
                      height = [fb+0x16],
                      format = [fb+0x18],
                      yuv    = 0,
                      phys   = [slot+0x18],
                      row    = width,
                      rect   = 0,
                      out    = slot,
                      sorting= 0,
                      start  = 0)
   ```
   `FrameBuffer::initialize`（0x22eb8）只负责 MA 内存空间，并把 `fb+0x68` 指向 `fb+0x20`、`fb+0x70` 指向 `fb+0x40`；BMP 本身由 `update` 创建。
3. **实际 format 的静态证据是 `libgemini-grm` 的 `GRM_fbrmInitialize(w,h,format=1)`。**
   - `libgemini-grm` 是唯一导入 `GRM_fbrmInitialize` 的库；调用点 `0x8e84`：
     ```text
     0x8e78: uxth w0, w1     ; width
     0x8e7c: uxth w1, w2     ; height
     0x8e80: mov  w2, #1     ; format = 1
     0x8e84: bl   GRM_fbrmInitialize
     ```
   - `GRM_fbrmInitialize`（libgrm 0x23374）对 format 做归一化：
     ```text
     format == 1        -> BMP format 1
     format == 2 or 3   -> BMP format 2
     format == 0 or >3  -> 0 (invalid)
     ```
   - BMP format 1 在上一份报告已确认是 **2bpp**。
   - 因此 **on-screen BMP 的静态实际格式是 2bpp**；`sorting=0`、`start=0` 由 `FrameBuffer::update` 的 `str wzr,[sp]` / `str wzr,[sp,#8]` 直接确认。
4. **当前 `libgrm-fbinit9` shim 会让 on-screen BMP 不存在。**
   - `FrameBuffer::initialize` 被跳过（`FX6_GRM_FB_INIT_SKIP`），`fb+0x68` 不会被设为 `fb+0x20`；
   - `FrameBuffer::update` 被跳过（`FX6_GRM_FB_UPDATE_SKIP`），`fb+0x20` 不会被 `BMP_CreateFromPhys` 填充；
   - `FrameBuffer::getOnscreen` 被覆写为直接返回 NULL；
   - `FBResourceManager::getInstance` 被覆写为使用 fake FrameBuffer。
   因此 `GRM_screenGetOnBitmap` 返回 NULL。**这是“有 ABI、无 bitmap”的直接原因。**
5. **ring 布局修正：**
   - 1024×540×2 = `0x10E000`（1,105,920），小于 `0x180000`（1,572,864）；
   - 8×0x180000 **可以装下**，而且有 8 个 slot；
   - 4×0x3c0000 也可以，但只有 4 个 slot；
   - 若实际是 1280×720×2（`0x1C2000`）或 1024×540×4（`0x21C000`），8×0x180000 不够，必须 4×0x3c0000；
   - **结论：静态 format=1/2bpp + 1024×540 时，8×0x180000 足够且更优；由于 1024×540 仍是本地 shim 证据而非运行时确认，4×0x3c0000 仍是安全回退。**

## 2. 公开复核

快速检索：

- `Sony GRM FrameBuffer getOnscreen`
- `"FrameBuffer::getOnscreen" Sony`
- `"GRM_screenGetOnBitmap"`

结果：

- 没有 Sony GRM/FrameBuffer 文档、头文件或社区一手研究；
- 结果都是无关页面；
- 前两份报告已确认无 Sony GRM 公开文档；本次只做快速复核，不再展开。

## 3. `GRM_screenGetOnBitmap` 依赖链

`GRM_screenGetOnBitmap`（libgrm `0x2368c`）：

```text
0x23698: mov x19, x0          ; out
0x2369c: bl  0x1fe00          ; FBResourceManager::getInstance
0x236a0: bl  0x1f970          ; FBResourceManager::getOnscreen
0x236a4: str x0, [x19]        ; *out = bitmap
0x236a8: mov w0, #0
```

PLT 映射：

```text
0x1fe00 = FBResourceManager::getInstance()
0x1f970 = FBResourceManager::getOnscreen()
```

`FBResourceManager::getOnscreen`（`0x22ad8`）：

```text
0x22ad8: ldr x0, [x0, #8]     ; manager->frameBuffer
0x22adc: b   0x1fa50          ; FrameBuffer::getOnscreen
```

`0x1fa50` 映射为：

```text
FrameBuffer::getOnscreen()
```

`FrameBuffer::getOnscreen`（`0x231e4`）：

```text
0x231e4: ldr x0, [x0, #0x68]  ; &fb->onscreen slot (fb+0x20)
0x231e8: ldr x0, [x0]         ; BMP*
0x231ec: ret
```

因此依赖链成立：

```text
GRM_screenGetOnBitmap
  -> FBResourceManager::getOnscreen
    -> FrameBuffer::getOnscreen
      -> [fb+0x68] -> [fb+0x20]
```

## 4. on-screen BMP 创建点

### 4.1 `FrameBuffer::initialize` 只建 MA 空间

`FrameBuffer::initialize`（`0x22eb8`）调用：

```text
MA_CreateSpace
MA_GetUnitHandle
MA_SpaceGetInitialLogicalAddress
MA_LogicalToPhysical
```

末尾设置：

```text
0x22fc0: str x1, [x20, #0x68]   ; fb+0x68 = fb+0x20
0x22fc8: str x1, [x20, #0x70]   ; fb+0x70 = fb+0x40
```

即 `fb+0x68` 指向 **on-screen slot 的地址**、`fb+0x70` 指向 **off-screen slot 的地址**；BMP 本身还没创建。

### 4.2 `FrameBuffer::update` 创建两个 BMP

`FrameBuffer::update`（`0x230b8`）循环两个 slot：

```text
x20 = fb+0x20
x23 = fb+0x60
loop:
  width  = *(short *)(fb+0x14)
  height = *(short *)(fb+0x16)
  format = *(int   *)(fb+0x18)
  phys   = *(off_t *)(x20+0x18)
  x0 = width
  x1 = height
  x2 = format
  w3 = 0                  ; YUV mode
  x4 = phys
  w5 = width
  x6 = 0                  ; rect
  x7 = x20                ; out
  [sp]   = 0              ; sorting
  [sp+8] = 0              ; start
  bl BMP_CreateFromPhys
  x20 += 0x20
  if x20 != fb+0x60: loop
```

调用点 `0x23160`：

```text
0x23138: ldrsh w0, [x19, #0x14]   ; width
0x23140: ldrh  w1, [x19, #0x16]   ; height
0x23148: ldr   w2, [x19, #0x18]   ; format
0x2314c: mov   w5, w0             ; row = width
0x23150: str   wzr, [sp]          ; sorting = 0
0x23154: mov   w3, #0             ; yuv = 0
0x23158: str   wzr, [sp, #8]      ; start = 0
0x2315c: ldr   x4, [x20, #0x18]   ; phys
0x23160: bl    BMP_CreateFromPhys
```

因此：

- on-screen slot = `fb+0x20`，off-screen slot = `fb+0x40`；
- `format` 来自 `fb+0x18`；
- `sorting=0`、`start=0`；
- `row=width`；
- BMP 创建后，`[fb+0x20]`/`[fb+0x40]` 才是有效指针。

### 4.3 `setSize`/`setColorFormat`/`initializeFrameBuffer`

`FrameBuffer::setSize`（`0x2303c`）：

```text
strh w1, [x0, #0x14]   ; width
strh w2, [x0, #0x16]   ; height
```

`FrameBuffer::setColorFormat`（`0x23048`）：

```text
str w1, [x0, #0x18]    ; format
```

`FBResourceManager::initializeFrameBuffer`（`0x22a98`）：

```text
w20 = w3 (format)
FrameBuffer::setSize(w1, w2)
FrameBuffer::setColorFormat(w20)
FrameBuffer::update()
```

`GRM_fbrmInitialize`（`0x23374`）调用 `initializeFrameBuffer`。

## 5. 实际 format：`GRM_fbrmInitialize(..., 1)`

### 5.1 唯一调用者

`GRM_fbrmInitialize` 的导入者：

```text
libgemini-grm.so: U GRM_fbrmInitialize
```

`libgemini-grm` 调用点 `0x8e84`：

```text
0x8e78: uxth w0, w1   ; width
0x8e7c: uxth w1, w2   ; height
0x8e80: mov  w2, #1   ; format = 1
0x8e84: bl   GRM_fbrmInitialize
```

### 5.2 `GRM_fbrmInitialize` 的归一化

`GRM_fbrmInitialize`（`0x23374`）：

```text
w19 = w2 (format)
w20 = w0 (width)
w21 = w1 (height)
...
cmp w19, #1
b.eq 0x233dc          ; format == 1 -> w3 = 1
cbz w19, 0x233bc      ; format == 0 -> invalid
cmp w19, #3
mov w3, #2
b.ls 0x233dc          ; format 2/3 -> w3 = 2
...
mov w3, #0            ; format 0/>3 -> 0
0x233dc:
w1 = w20
w2 = w21
x0 = manager
bl initializeFrameBuffer(w1, w2, w3)
```

因此：

```text
GRM format 1 -> BMP format 1 (2bpp)
GRM format 2/3 -> BMP format 2 (4bpp)
GRM format 0/>3 -> 0 (invalid)
```

`libgemini-grm` 传的是 **1**，所以 on-screen BMP 的静态实际格式是：

```text
BMP_PixelFormat = 1
bpp = 2
sorting = 0
start = 0
```

## 6. 当前 fbinit shim 的影响

`libgrm-fbinit9.c`：

```c
void *FrameBuffer::getOnscreen(void *self) {
    dprintf(2, "FX6_GRM_FB_GET_ONSCREEN_SKIP self=%p result=NULL\n", self);
    return (void *)0;
}
void FrameBuffer::update(void *self) {
    dprintf(2, "FX6_GRM_FB_UPDATE_SKIP self=%p result=0\n", self);
}
int FrameBuffer::initialize(unsigned int w, unsigned int h) {
    dprintf(2, "FX6_GRM_FB_INIT_SKIP self=%p w=%u h=%u result=0\n", self, w, h);
    return 0;
}
```

`libgrm-fbinit14.c` 只把 `initialize` 改成调用 real，`update`/`getOnscreen` 仍然是 stub。

后果：

- `FrameBuffer::initialize` 不执行 -> `fb+0x68` 保持 0；
- `FrameBuffer::update` 不执行 -> `fb+0x20`/`fb+0x40` 没有 BMP；
- `getOnscreen` 直接返回 NULL；
- `GRM_screenGetOnBitmap` 返回 NULL；
- OSD worker 的 `GRM_screenIsDirty`/`bitmapReadLockBits` 无 bitmap 可用。

**因此当前没有 FX6 OSD 帧，不只是 format/ring 问题，而是 on-screen bitmap 根本没创建。**

## 7. Ring 复算（format=1/2bpp）

### 7.1 1024×540

```text
1024 * 540 * 2 = 1,105,920 = 0x10E000
```

| 布局 | slot | 总大小 | 1024×540×2 |
|---|---:|---:|---|
| 8×0x180000 | 1,572,864 | 0xC10000 | 可（8 帧） |
| 4×0x3c0000 | 3,932,160 | 0xF10000 | 可（4 帧） |

**8×0x180000 足够，而且多 4 个 slot；4×0x3c0000 更浪费但更保守。**

### 7.2 风险尺寸

| 分辨率/格式 | 字节 | 8×0x180000 | 4×0x3c0000 |
|---|---:|---|---|
| 1024×540×2 | `0x10E000` | 可 | 可 |
| 1280×720×2 | `0x1C2000` | **不可** | 可 |
| 1024×540×4 | `0x21C000` | **不可** | 可 |
| 1280×720×4 | `0x384000` | **不可** | 可（余 0x3C000） |
| 1920×1080×4 | `0x7E9000` | **不可** | **不可** |

**结论**：

- 若确认 **1024×540 + format 1/2bpp**：选 **8×0x180000**（8 帧，总 0xC10000）。
- 若尺寸/格式未确认：选 **4×0x3c0000**（4 帧，总 0xF10000），覆盖 1280×720×4。
- 1920×1080×4 需要单帧/双帧 ring；当前无证据。

## 8. 解析器字段

若采用 8×0x180000 + 2bpp：

```text
v[7]  = 0          (2bpp)
v[8]  = 1024
v[9]  = 540
v[10] = rowBytes / bpp = 1024
v[11] = size = 0x10E000
v[12] = FNV64
v[17] = 1          (BMP_PixelFormat)
v[18] = 2          (bpp)
v[19] = 0          (sorting/start)
```

现有 `osd_ring85.py` 仍会拒绝：

```text
w<=640, h<=480, span<=0x12c000, fmt<=1, 8×0x180000
```

需要 `osd_ring_fx6.py`：

```text
SLOTS=8 (或 4)
STRIDE=0x180000 (或 0x3c0000)
TOTAL=0xC10000 (或 0xF10000)
MAX_W=1024
MAX_H=540
MAX_SPAN=0x180000 (或 0x3c0000)
```

## 9. 实测 vs 推断 vs 缺失

### 静态实测

- `GRM_screenGetOnBitmap` 的 PLT：`FBResourceManager::getInstance`、`getOnscreen`；
- `FBResourceManager::getOnscreen` -> `FrameBuffer::getOnscreen`（PLT 0x1fa50）；
- `FrameBuffer::getOnscreen` 读 `[fb+0x68]` -> `[fb+0x20]`；
- `FrameBuffer::initialize` 设置 `fb+0x68=fb+0x20`、`fb+0x70=fb+0x40`；
- `FrameBuffer::update` 对 `fb+0x20/+0x40` 调 `BMP_CreateFromPhys`，format=`[fb+0x18]`，sorting/start=0；
- `setSize` 写 `+0x14/+0x16`，`setColorFormat` 写 `+0x18`；
- `GRM_fbrmInitialize` 的 format 归一化；
- `libgemini-grm` 调用 `GRM_fbrmInitialize(..., 1)`；
- `libgrm-fbinit9.c` 的 initialize/update/getOnscreen stub。

### 推断

- 1024×540 是实际 UI 尺寸（来自 `libgrm-fbinit9.c` 注释/默认，不是运行时）；
- `libgemini-grm` 的 width/height 来自调用者，当前未静态定位到常量；
- on-screen BMP 是相机 LCD/OSD 用的那一块（调用链与名字支持，但没有运行时帧）。

### 未实测

- 没有 FX6 ring 帧/PNG；
- 没有 `FX6_GRM_FB_SET_SIZE`/`FX6_UX_SCREEN_AREA` 的实际 w/h serial；
- 没有运行 shim；
- 没有 `GRM_screenGetOnBitmap` 返回非 NULL 的实测；
- 没有确认 `libgemini-grm` 的 width/height 实参。

## 10. 下一步

1. **先解决 on-screen bitmap 不存在**：需要一个不跳过 `FrameBuffer::update`、且 `getOnscreen` 返回 `[fb+0x68]` 的 shim；否则 GRM 抓帧没有对象。
2. 若能确认 `GRM_fbrmInitialize` 的 width/height = 1024×540，选 8×0x180000；否则先用 4×0x3c0000。
3. 解析器新增 `osd_ring_fx6.py`；format=1/2bpp 时 `v[7]=0`、`v[18]=2`。
4. 写 shim / `pmemsave` 实跑需另行批准；本次未做。

## 11. 边界

- 未启动/未改动任意 VM；
- 未解包/修改 `BODYDATA.DAT` 或任意固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）；
- 未写 shim，未用 `pmemsave` 实跑。

## 12. 结论一句话

**`GRM_screenGetOnBitmap` 确实依赖 `FrameBuffer::getOnscreen`；on-screen BMP 由 `FrameBuffer::update` 以 `BMP_CreateFromPhys(format=1, sorting=0, start=0)` 创建，静态格式是 2bpp。当前 fbinit shim 跳过了 `update` 并让 `getOnscreen` 返回 NULL，所以 bitmap 根本不存在；ring 在 1024×540 下 8×0x180000 足够，但 4×0x3c0000 仍是未确认尺寸时的安全回退。**
