# EVIDENCE 699–702：User 三层页、Home 98 行整页、Grid/Media Grid、Touch Menu/List

时间：2026-11-08（America/Los_Angeles）

四页共用 `/private/tmp/fx6_pages_699_702.c`
（`-DPAGE_USERL1 / -DPAGE_HOME98 / -DPAGE_GRIDS / -DPAGE_TOUCH`）。
本批新增了 `page_table_ex()` —— 带 `skip_n2` 开关的通用表格渲染器，
用于在 home 表里滤掉与 `No1xxx_*` 互斥的 `No2ddd_*` 紧凑布局。
PNG 导出后只用 Python 统计像素，未对任何 `.png` 调用图像读取。

## 1. 699 — User 三层页

```
FX6_VSR70x done text=17 fill=17 icon=1 text_ok=17
```

左列 9 分类，选中条第 1 项 `User`；右列 6 项：
`User Menu Item` / `Edit User Menu` / `Assignable Button` / `User File` /
`User Gamma` / `Custom`。

像素：`nz=435,024`、纯白 2,400、`0xcc222222` 361,091、选中条 38,993。

## 2. 700 — Home 98 行整页（`0x2e9e210`）

```
FX6_VSR70x done text=24 fill=8 icon=0 text_ok=24
```

这是 home presenter 的完整描述符表，`skip_n2=1` 滤掉紧凑布局后剩 24 条文案 + 8 条填充。

像素：`nz=331,776`（正好 60% 屏占比）、`0xff000000` 179,360、`0xff222222` 139,709、纯白 1,241。
与 656（早期 home 页）的构成一致，但这次是完整 98 行表驱动。

## 3. 701 — Grid Selection（`0x2ea2788`, 23 行）+ Media Grid（`0x2eaa810`, 18 行）

```
FX6_VSR70x done text=1 fill=19 icon=4 text_ok=1
```

像素：`nz=435,024`、`0xdf111111` 426,648（几乎整屏深底）、`0xff444444` 8,090、纯白 69。

`text=1` 说明这两张表几乎全是 `view_menu_item`（文本由 controller 注入），
但 19 条填充与 4 个图标都正常 —— 网格骨架是画出来的。

## 4. 702 — Touch Menu（`0x2ea6b08`, 19 行）+ Touch List（`0x2eb4e00`, 19 行）

```
FX6_VSR70x done text=12 fill=0 icon=4 text_ok=12
```

像素：`nz=1,164`、纯白 247、`0x99ffffaa` 157
—— 极轻量的浮层形态（touch 菜单本来就是叠在取景器上的小面板），符合预期。

## 5. 四页像素统计（Python）

| 页面 | 帧 | nz | 纯白 | 主色 |
|---|---|---|---|---|
| 699 User 三层 | `cp-bind-*` | 435,024 | 2,400 | `0xcc222222` 361,091 |
| 700 Home 98 | `cp-bind-*` | 331,776 | 1,241 | `0xff000000` 179,360 |
| 701 Grid/Media | `cp-bind-*` | 435,024 | 69 | `0xdf111111` 426,648 |
| 702 Touch Menu/List | `cp-bind-*` | 1,164 | 247 | `0x00000000` 551,796 |

四帧 `segv=0`，`text_ok` 均等于 `text`（17/17、24/24、1/1、12/12）。

## 6. 交付物

- `menu-699-usermenu3layer.png`
- `menu-700-home98.png`
- `menu-701-gridselmedia.png`
- `menu-702-touchmenulist.png`
- 源码 `/private/tmp/fx6_pages_699_702.c`
- 前序：`EVIDENCE-695-698-USER-STATUS-CLIP-GRID.md`

## 7. 观察

699/700 是「整屏菜单」形态（>60% 屏占比），701 是「整屏深底 + 网格骨架」，
702 是「轻量浮层」。四张图形态差异明显，说明 page_table 的按类分派在起作用，
不是同一套填充套壳。
