# EVIDENCE 695–698：Edit User Menu、Status/QR 页、Clip/Playback、Setting Grid

时间：2026-11-08（America/Los_Angeles）

四页共用 `/private/tmp/fx6_pages_695_698.c`
（`-DPAGE_USER / -DPAGE_EDITUSER / -DPAGE_STATUS86 / -DPAGE_CLIP83 / -DPAGE_GRID109`）。
PNG 导出后只用 Python 统计像素，未对任何 `.png` 调用图像读取。

## 1. 695 — Edit User Menu 三层页（`runs/cp-bind-561823cc`）

```
FX6_VSR69z done text=16 fill=17 icon=1 text_ok=16
```

左列 9 分类，选中条在第 2 项 `Edit User Menu`；右列 5 项：
`Add Item`(`0x02004d4b`) / `User Menu Item`(`0x02004294`) / `Edit User Menu`(`0x02004d4a`) /
`User File`(`0x02004286`) / `Assignable Button`(`0x02004264`)。

像素：`nz=435,024`、纯白 2,448、`0xcc222222` 361,873、选中条 `0xff00aaff` 38,742。

## 2. 696 — Status / Media QR 页（page 86，`0x2eb36a8`，`runs/cp-bind-fe472c77`）

```
FX6_VSR69z done text=6 fill=2 icon=1 text_ok=6
```

该表实际是 **17 行**（不是任务里写的 55 行），内容为 `No2_NOTIFY_5_*` 通知页：
`TOUCH` + `NOTIFY_5_BG`（2 条填充）+ 标题 `0x020026b7` + 4 条正文行
（`LINE1..LINE4`，`+0x18` 为 0 且有 `layout`）+ 1 个图标。

像素：`nz=4,804`、纯白 1,069、`0xff000000` 470
—— 是「浅色通知卡片」形态，与前面整屏菜单页明显不同。

## 3. 697 — Clip Properties(83) + Playback Control（`runs/cp-bind-6098607c`）

两张表叠加：`0x2eb2ad8`（8 行）+ `0x2eb1890`（54 行）。

```
FX6_VSR69z done text=14 fill=11 icon=9 text_ok=14
```

像素：`nz=435,024`、`0xdf111111` 418,501（深底）、`0xff444444` 12,270（分隔线）、纯白 1,238。
`icon=9` 是本次四页里最多的 —— 该页确实有 9 个真实图片 ResID 的图标。

## 4. 698 — Setting Grid（page 109，`0x2eb6510`）

该表只有 **7 行**（任务里写的 54 行是别的页），实际内容是 `NOTIFY_5` 对话框：

```
FX6_VSR69z done text=1 fill=0 icon=1 text_ok=2
```

像素：`nz=1,766`、纯白 490、`0x99ffffaa` 159。

`fill=0` 的原因：`No1_NOTIFY_5_BG` 是 `view_icon`（tag `0x042d5a50`，`+0x18=0x0200023a`），
不是 `view_fill`，所以走的是图标路径（`icon=1`）。
`text=1` 是标题行 `0x020026b7`；4 条 `LINE1..4` 的 `+0x18` 为 0 且没有对应 HUD 绑定，
按「无文案即不画」跳过 —— 这与固件里这些行由 controller 填文案的行为一致。

## 5. 四页像素统计（Python）

| 页面 | 帧 | nz | 纯白 | 主色 |
|---|---|---|---|---|
| 695 Edit User Menu | `cp-bind-561823cc` | 435,024 | 2,448 | `0xcc222222` 361,873 |
| 696 Status/QR | `cp-bind-fe472c77` | 4,804 | 1,069 | `0x00000000` 548,156 |
| 697 Clip/Playback | `cp-bind-6098607c` | 435,024 | 1,238 | `0xdf111111` 418,501 |
| 698 Setting Grid | `cp-bind-f0d51440` | 1,766 | 490 | `0x00000000` 551,194 |

四帧 `segv=0`，`text_ok` 均等于 `text`。

## 6. 交付物

- `menu-695-editusermenu.png`
- `menu-696-status86.png`
- `menu-697-clip83playback.png`
- `menu-698-settinggrid109.png`
- 源码 `/private/tmp/fx6_pages_695_698.c`
- 前序：`EVIDENCE-691-694-HUD-AND-MAINTENANCE.md`

## 7. 说明

任务给出的 696/698 行数（55 / 54）与固件实际表长（17 / 7）不一致，
我按固件实际表长渲染，并在本文记录差异 —— 宁可画「表里真实存在的 17 行」，
也不按错误行数越界读取其它表。
