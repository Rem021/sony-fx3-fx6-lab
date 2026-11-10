# EVIDENCE 707–710：Thumbnail Properties、Menu Grid、两列设置、Settings 子页

时间：2026-11-08（America/Los_Angeles）

源码 `/private/tmp/fx6_pages_707_710.c`（`-DPAGE_A..D`），四页都在
`g_use_extras=1` 下渲染（每行用描述符自己的 `+0x1c/+0x24/+0x28/+0x2c/+0x30/+0x34`）。
PNG 只用 Python 统计像素，未调用图像读取。

## 1. 707 — Thumbnail Properties（page 18，`0x2e9cef0`，46 行）

```
FX6_VSR70z done text=14 fill=1 icon=7 text_ok=14 extras=1
```

像素：`nz=552,960`（**整屏 100%**）、`0xff000000` 547,468、纯白 1,576。

这是本批唯一把整屏铺满的页面，与它「缩略图属性」的深底全屏形态一致。

## 2. 708 — Menu Grid（`0x2ea4990`, 33 行）+ Grid 3-col（`0x2ea6400`, 11 行）

```
FX6_VSR70z done text=5 fill=8 icon=3 text_ok=5 extras=1
```

像素：`nz=435,024`、`0xdf111111` 422,728、`0xff444444` 10,740、纯白 564。

## 3. 709 — Setting 两列（`0x2ea20c8`, 23 行）+ Menu List（`0x2ea5bd8`, 5 行）

```
FX6_VSR70z done text=0 fill=13 icon=5 text_ok=0 extras=1
```

像素：`nz=435,024`、`0xcc222222` 389,581、纯白 **0**。

`text=0` 说明这两张表的字符串行在静态描述符里 `+0x18` 全为 0
（文本由 controller 注入），但 13 条填充 + 5 个图标正常 —— 骨架完整。

## 4. 710 — Settings 子页（`0x2ead0d8`, 26 行）+ Toast Confirm（`0x2e9deb0`, 11 行）

```
FX6_VSR70z done text=11 fill=7 icon=3 text_ok=11 extras=1
```

像素：`nz=435,024`、`0xdf111111` 422,055、`0xff444444` 9,678、纯白 1,002。

## 5. 像素统计

| 页面 | nz | 纯白 | 主色 |
|---|---|---|---|
| 707 Thumbnail Properties | 552,960 | 1,576 | `0xff000000` 547,468 |
| 708 Menu Grid | 435,024 | 564 | `0xdf111111` 422,728 |
| 709 两列设置 | 435,024 | 0 | `0xcc222222` 389,581 |
| 710 Settings 子页 | 435,024 | 1,002 | `0xdf111111` 422,055 |

四帧 `segv=0`，`text_ok` 等于 `text`（14/14、5/5、0/0、11/11），`extras=1` 全部生效。

## 6. 交付物

- `menu-707-topprops.png` / `menu-708-menugrid.png` / `menu-709-twocol.png` / `menu-710-subpage.png`
- 源码 `/private/tmp/fx6_pages_707_710.c`
- 前序：`EVIDENCE-703-706-EXTRAS.md`
