# EVIDENCE 711–714：Gamma Assist Overlay、Setting Grid (69 rows)、Network (176 rows)、Settings Subpage (28 rows)

时间：2026-11-10（America/Los_Angeles）

本批在 `g_use_extras=1`（启用每行真实 `+0x1c/+0x24/+0x28/+0x2c/+0x30/+0x34` 样式扩展字段）下，由 QEMU Guest 原生渲染至 `gpe0 @ 0x41e001000` 并导出 PNG（仅使用 Python 统计像素，未对任何 `.png` 调用图像读取）。

## 1. 711 — Gamma Assist Overlay（`0x02e917d8`，71 行，`cp-bind-a08d6a6d`）

```
FX6_VSR71x done text=11 fill=0 icon=41 text_ok=11 extras=1
```

- 导出帧：`menu-711-gamma71.png`
- 像素统计：`nz=2,842`（1024×540 取景器浮层形态，含 41 个状态图标与 11 条文案）、主色 `0xff000000` 550,118、`0xffeeeeee` 1,192、`0xff444444` 322，`segv=0`。

## 2. 712 — Setting Grid 69 行（`0x02ea0d18`，69 行，`cp-bind-93deaaff`）

```
FX6_VSR71x done text=0 fill=23 icon=2 text_ok=0 extras=1
```

- 导出帧：`menu-712-setgrid69.png`
- 像素统计：`nz=432,174`、主色 `0xff222222` 389,896、`0xff000000` 120,786、`0xff333333` 17,700，`segv=0`。

## 3. 713 — Network Full Page 176 行（`0x02ea7648`，176 行，`cp-bind-3d65765f`）

```
FX6_VSR71x done text=9 fill=110 icon=25 text_ok=9 extras=1
```

- 导出帧：`menu-713-network176.png`
- 像素统计：`nz=435,024`、纯白 `751`、主色 `0xff111111` 392,901、`0xff000000` 117,936、`0xffeeeeee` 25,024，`segv=0`。

## 4. 714 — Settings Subpage（`0x02eb0d08` / `0x02eb53a0`，28 行，`cp-bind-daac5649`）

```
FX6_VSR71x done text=5 fill=7 icon=1 text_ok=5 extras=1
```

- 导出帧：`menu-714-subpage26.png`
- 像素统计：`nz=435,024`、纯白 `587`、主色 `0xff111111` 423,747、`0xff000000` 117,936、`0xff444444` 9,902，`segv=0`。

## 5. 四页像素与执行汇总表

| 页面 | Run 目录 | 串口统计 (`FX6_VSR71x`) | PNG 文件 | nz | 纯白 | segv |
|---|---|---|---|---|---|---|
| 711 Gamma Assist Overlay | `cp-bind-a08d6a6d` | `text=11 fill=0 icon=41 text_ok=11` | `menu-711-gamma71.png` | 2,842 | 0 | 0 |
| 712 Setting Grid 69 | `cp-bind-93deaaff` | `text=0 fill=23 icon=2 text_ok=0` | `menu-712-setgrid69.png` | 432,174 | 0 | 0 |
| 713 Network 176 | `cp-bind-3d65765f` | `text=9 fill=110 icon=25 text_ok=9` | `menu-713-network176.png` | 435,024 | 751 | 0 |
| 714 Settings Subpage | `cp-bind-daac5649` | `text=5 fill=7 icon=1 text_ok=5` | `menu-714-subpage26.png` | 435,024 | 587 | 0 |

前序报告：`EVIDENCE-707-710.md`
