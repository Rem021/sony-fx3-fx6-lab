# EVIDENCE 653：原生 FX6 菜单整页（背景/分隔线/按钮/文字）落入 gpe0

时间：2026-11-08（America/Los_Angeles）
运行：`runs/cp-bind-834742be`（candidate 653，CPIO `guest-hybrid-fx6kernel-capid-grmreal653-rectpos.cpio`）
结果：**gpe0 非零像素 789,476**，画面由 appFw 自己的菜单描述符表 + 原生
`view_fill` / `view_string` 的 `onDrawNotice` + libra `TextProcessor` 渲染而成。

## 1. 画面构成（全部来自 appFw 数据，无手写坐标/文案）

`FX6_NEXT_FILL`（原生 `Sprite::renderRect` → GDS `fillRect`）：

```
n=1 r=96,72,768,432   c=ff000000   No1_BG        color ResID 0x0200c001
n=2 r=96,194,768,188  c=ff222222   No28_BG       color ResID 0x0200c008
n=3 r=96,382,768,4    c=ff777777   No34_SEPARATOR 0x0200c00e
n=4 r=96,190,768,4    c=ff777777   No33_SEPARATOR
n=5..8 竖向分隔线 4×118 位于 x=349/607, y=72/386
```

`view_string`：50 个描述符被驱动，32 条文本通过 `setImageLoadCallback` 交付真实字形位图，
内容为 appFw 的字符串 ResID（`Set`、`Reel`、`Shot`、`FF`、`38/AP`、`JOABP`、`---min`、`FS(V1)`、`AEA0*0` …）。

## 2. 本轮打通的三个精确机制（沿 646→653 收敛）

1. **描述符 `+0x00` 是类别标签，不是控件实例**
   `tag_off = proto - appFw_base`：`0x42d57f0/0x42d59a0`=view_string，
   `0x42d5a40/0x42d57d0`=view_fill，`0x42d58d0`=按钮。
   直接当实例用会 SEGV（646 的 vptr 是 ASCII 文本）。
2. **view_fill 的正确构造与生命周期**
   `0xc27800` 是 **view_frame** 的构造函数（内部另建 5 个 view_fill）；
   view_fill 真正的构造函数是 `0xc27698`。
   顺序必须是：ctor → `vt[+0x148]`（onCreate，`Widget::initSprite` 分配 RectData 槽 0，
   使 `spr+0xda` 的 rectCount=1）→ `vt[+0x158]`（onDrawNotice，从 `color_cmn.uxc`
   解出 RGBA 写入 `rects[0]+0x22`）→ `processCommands(0)` → `Sprite::renderRect`。
   少了 onCreate，`Sprite::getRectColor` 会在 `libuxengine+0x7d488` 因 rectCount==0 断言。
3. **矩形目标坐标在 RectData 里**
   `renderRect` 从 `rects[0]+0x00/+0x04` 取目标 x/y，不是从 `pos` 参数取。
   调用前必须 `Sprite::setRectPos(spr, 0, &pos)`（或直接写 `rects[0]+0x00/+0x04`），
   否则 8 个面板/分隔线全部落在 (0,0)。
   另外 `Sprite` 的 RectData 数组指针在 `spr+0xd0`，步长 `0x2c`，颜色在**未对齐的 `+0x22`**。

## 3. 交付物

- `menu-653-full.png` — 1024×540 整帧
- `menu-653-panel.png` — 菜单内容区裁切（背景板 + 分隔线 + 4 个 `Set` 按钮 + 32 条文案）
- `menu-648-setting.png` — 仅文字/按钮阶段的对照
- `gpe0-645-native-text-crop.png` — 单条原生文字的最初证据
- `RAW-IMAGEDATA-GRM-BITS-EXACT.md` — `RawImageDataGRM`/`BMP_Handle` 位图布局

## 4. 仍可继续打磨（非阻塞）

- 左列若干窄框文案（如 `No11_SRCMEDIA` 宽 60px）原生按多行换行渲染，视觉上是竖排碎字，
  这是原生 `LayoutAttribute` 宽度决定的，不是 shim 行为。
- `view_icon` 类（tag `0x42d5800/0x42d5930`，电池/音频表）尚未绘制。
- 文案中的 `---min`、`FS(V1)`、`AEA0*0` 是 hybrid 环境下 model 层无真实状态时原生控件的输出，
  需打通 model 层才会有真实数值。
- 当前未按 presenter 生命周期建树，是逐描述符构造同类控件后扁平绘制；
  坐标与内容 100% 来自 appFw 表。
