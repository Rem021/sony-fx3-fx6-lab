# EVIDENCE 646–648：原生描述符表驱动的 FX6 菜单整页落入 gpe0

时间：2026-11-08（America/Los_Angeles）
结论：**gpe0 现在显示的是 appFw 自己菜单表驱动、由原生 `view_string` / `view_fill`
的 `onDrawNotice` 与 libra/uxengine 字库渲染出的真实 FX6 页面**，
文字内容（`Set`、`FF`、`Reel`、`Shot`、`38/AP`、`JOABP`、`---min`、`FS(V1)`、`AEA0*0` 等）、
按钮、分隔线、坐标全部来自 `appFw.so` 的 `.data.rel.ro` 描述符表，没有手写任何菜单。

## 1. 关键模型修正（646 → 647）

646 曾假设描述符 `+0x00` 是"已构造的 prototype 控件"，直接调它的 vtable：
结果第一个描述符的 vptr 是 `0x30627573003630`（ASCII 文本"06...u..."），立刻 SEGV。
正确含义（静态线 `appFw+0xc1935c..0xc19784` 确认，并由运行期数值验证）：

```
proto 是 16 字节类别标签，不是实例
tag_off = (uintptr_t)proto - appFw_load_base
  0x042d57f0 / 0x042d59a0  -> view_string   (ctor 0xc3af98)
  0x042d5a40 / 0x042d57d0  -> view_fill     (ctor 0xc27800)
  0x042d58d0              -> 按钮（带 text_resid，如 0x020023da "Set"）
```

运行期核对：646 打印 `proto=0x7fa25f8860`、`appfw=0x7f9e323000`，
差值正是 `0x42d5860`（另一个 tag），模型成立。

## 2. 三个必须的细节（648 修正）

1. `view_string +0x21c = 1`，否则 `onDrawNotice` 的属性提交被跳过。
2. `setImageLoadCallback` 的 userdata 要传**该控件自身**，回调里用
   `+0x1e8/+0x1ec` 取自己的坐标；同时每个控件画完立刻 `processCommands(0)`，
   否则所有文字都会叠到循环最后一次的全局坐标上。
3. 字号资源要成段加载：`0x02006000..0x0200603f`、`0x0200a000..0x0200a02f`、
   `0x02008000..0x0200800f`（描述符用到了 `0x02006007/6008/600d/600e/600f/6015/602b/602e/6030`
   与 layout `0x0200a029/a02a/a02b`）。648 实测 `loadFonts ok=101/101`。

## 3. 648 运行证据（`cp-bind-13c47a1b`）

```
FX6_VSR648 loadFonts ok=101/101
FX6_VSR648 home presenter[01] F No1_BG        (96,72,768,432) color=0200c001
FX6_VSR648 home presenter[02] F No28_BG       (96,194,768,188) color=0200c008
FX6_VSR648 home presenter[06] S No1430_IMAGER_SCAN_MODE_RAW_VIDEO_FORMAT (336,257,208,32) text=02002f1d
FX6_VSR648 home presenter[07] S No1440_CODEC_NAME (336,297,180,32) text=02005261
FX6_VSR648 home presenter[13] F No34_SEPARATOR (96,382,768,4) color=0200c00e
FX6_VSR648 text blit n=216 at 654,425      <- 右下 "Set" 按钮
FX6_VSR648 text blit n=216 at 398,425
FX6_VSR648 text blit n=140 at 154,296
FX6_VSR648 done text=50 fill=8 text_ok=32
```

gpe0（`gpe0-final.bin` / `gpe0-late.bin`）：
- 非零像素 5186，包围盒 x∈[119,709]、y∈[83,448]
- 32 次原生文字图像交付，8 个原生 `view_fill` 面板/分隔线
- 主色为不透明白 `0xffffffff` 及若干 RGBA4444 展开的抗锯齿中间色

## 4. 交付物

- `menu-648-full.png` — 1024×540 整帧
- `menu-648-setting.png` — 菜单内容区裁切，可直接读出原生菜单文案与按钮
- `gpe0-645-native-text-crop.png` — 单条原生文字的最初证据
- `EVIDENCE-639-645-NATIVE-TEXT.md` — 645 阶段（单控件文字链路）证据
- `RAW-IMAGEDATA-GRM-BITS-EXACT.md` — `RawImageDataGRM`/`BMP_Handle` 精确布局

## 5. 剩余工作

- 文案里仍有占位符（`FF`、`---min`、`FS(V1)`、`AEA0*0`），因为 hybrid 中模型/媒体状态为默认值，
  这些是**原生**控件渲染的真实结果，不是伪造文本；如需真实数值需先打通 model 层。
- 尚未按原生 presenter 的生命周期建树（当前是逐描述符构造同类控件），
  菜单页内容与坐标已 100% 来自 appFw 表，但容器层级仍是扁平绘制。
- 图标类（`view_icon`，tag `0x42d5800/0x42d5930`）尚未绘制。
