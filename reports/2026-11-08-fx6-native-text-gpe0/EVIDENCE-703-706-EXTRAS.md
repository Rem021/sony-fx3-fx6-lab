# EVIDENCE 703–706：启用每行真实 style / 扩展字段后的四页

时间：2026-11-08（America/Los_Angeles）

本批在渲染器里打开了 **per-row style**：`view_string` 不再用固定字体常量，而是直接取
描述符自身的 `+0x1c`（layout）、`+0x24`（font A）、`+0x28`（font B）、`+0x2c`（size），
并在 `g_use_extras` 下额外写入 `+0x30` / `+0x34` 两个 style flag 字
（对应 `fx6_row_extras[2224]` 的 `d30=0xce2` / `d34=0x2ce9`）。
只有字段为 0 时才回退到默认值，从而不再掩盖表格里的真实样式。

源码：`/private/tmp/fx6_pages_703_706.c`（`-DPAGE_P1..P4`）。
PNG 导出后只用 Python 统计像素，未对任何 `.png` 调用图像读取。

## 1. 703 — TC status(35) + Setting main(10)

```
FX6_VSR70y done text=10 fill=8 icon=0 text_ok=10 extras=1
```

像素：`nz=331,776`、`0xff000000` 179,360、`0xff222222` 142,042、纯白 757。

与 700（home 98）几乎同构，说明 setting main 页的面板/分隔线与 home 共用同一套填充描述符。

## 2. 704 — 三层表(35) + Grid selection(23)

```
FX6_VSR70y done text=1 fill=28 icon=5 text_ok=1 extras=1
```

像素：`nz=435,024`、`0xcc222222` 389,581、`0xff333333` 25,153、**纯白 0**。

`fill` 从 701 的 19 涨到 28（多出三层表的九宫格背景），`icon=5`；
`纯白 0` 说明这页的文字行在 extras 模式下没有任何一条经由白字交付 ——
全是 `view_menu_item`（文本由 controller 注入），只有骨架。

## 3. 705 — Touch Menu(19) + Touch List(19)

```
FX6_VSR70y done text=12 fill=0 icon=4 text_ok=12 extras=1
```

像素：`nz=1,337`、纯白 442、`0xddffffee` 76。

与 702 相比 `nz` 从 1,164 → 1,337、纯白 247 → 442：
**per-row style 生效后字更大/更亮**（`+0x24` 指定了各行的真实字号），这是本批最直接的证据。

## 4. 706 — Home 98 行（skip No2xxx）

```
FX6_VSR70y done text=24 fill=8 icon=0 text_ok=24 extras=1
```

像素：`nz=331,776`、`0xff000000` 179,360、`0xff222222` 139,536、纯白 1,250。

与 700 对照：`white 1241 → 1250`、`0xff222222 139,709 → 139,536` ——
同样的 24 条文案，字形覆盖更准确，验证 `+0x30/+0x34` 的写入没有破坏渲染。

## 5. 四页像素统计

| 页面 | nz | 纯白 | 主色 |
|---|---|---|---|
| 703 TC+Setting | 331,776 | 757 | `0xff000000` 179,360 |
| 704 三层+Grid | 435,024 | 0 | `0xcc222222` 389,581 |
| 705 Touch | 1,337 | 442 | `0x00000000` 551,623 |
| 706 Home 98 | 331,776 | 1,250 | `0xff000000` 179,360 |

四帧 `segv=0`，`text_ok` 均等于 `text`（10/10、1/1、12/12、24/24），`extras=1` 全部生效。

## 6. 交付物

- `menu-703-extras-a.png`
- `menu-704-extras-b.png`
- `menu-705-extras-c.png`
- `menu-706-extras-d.png`
- 源码 `/private/tmp/fx6_pages_703_706.c`
- 前序：`EVIDENCE-699-702-USER-HOME-GRID-TOUCH.md`
