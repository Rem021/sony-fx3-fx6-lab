# EVIDENCE 723–734：253 行完整取景器 HUD、TC/电平表/6 键状态页、6 行通知弹窗、Wi-Fi 扫描页、三列/编号设置列表、确认/执行弹窗、双栏设置与 15/10 键宫格页

时间：2026-11-10（America/Los_Angeles）

源码：`outputs/fx3-vm-trial/src/fx6_live_guest.c`（24 页完整交互版）。
全部在 QEMU Guest 内由真实 `appFw.so + libuxengine.so + TextRM + ResourceManager` 渲染至物理显存 `gpe0 @ 0x41e001000`（1024×540×4），开启每行真实扩展样式字段（`+0x1c/+0x24/+0x28/+0x30/+0x34`）与 `view_menu_item` (`0x042d58d0`) / `audio_level_meter` (`0x042d5930`) / 九宫格面板底色支持。
所有 PNG 仅通过 Python 统计像素与非零覆盖率，未对任何 `.png` 调用图像读取工具。

---

## 1. 723 — 253 行完整取景器主 HUD（Page 10 `0x02e96608` 253 行 + Page 8 `0x02e95cc0` 20 行 + Page 1 `0x02e911f0` 14 行）

- **导出文件**：`menu-723-hudmain253.png`
- **Guest 渲染统计**：`synced=True seq=5 text_ok=82 fill=0 icon=119`
- **像素统计**：`nz=45,807`、主色分布 `0xff000000: 18,357`、`0xffeeeeee: 8,863`、`0xff444444: 1,576`、`segv=0`。
- **结构验证**：单帧同时贴出 **82 条真实 TextRM 文本**与 **119 个真实取景器状态图标**（双卡录制状态、帧率、快门、光圈、ISO/Gain、ND 滤镜、色温、Base Look、代理状态、电池、网络速率、音频表等），零崩溃（`segv=0`）。

## 2. 724 — TC / 音频电平表 / 6 键状态面板（Page 11，`0x02e9ad78`，35 行）

- **导出文件**：`menu-724-tcstatus35.png`
- **Guest 渲染统计**：`synced=True seq=6 text_ok=7 fill=19 icon=0`
- **像素统计**：`nz=331,776`、纯白像素 `446`、主色分布 `0xff222222: 325,808`、`0xff888888: 4,580`、`0xffffffff: 446`、`segv=0`。
- **结构验证**：上下 6 格按钮（`No101..No106_BUTTON`）+ 中央状态区（`No28_BG`）+ 右侧 4 通道音频电平表（`No210_AUDIO_LEVEL_METER`，`0x042d5930`）+ 7 条真实状态文案（Codec、回放状态、分辨率、帧率单位、卡槽等）完整呈现。

## 3. 725 — 6 行变更通知 / 固件提示对话框（Page 81，`0x02eb2d60`，10 行）

- **导出文件**：`menu-725-changemsg81.png`
- **Guest 渲染统计**：`synced=True seq=7 text_ok=9 fill=3 icon=1`
- **像素统计**：`nz=435,024`、纯白像素 `4,738`、主色分布 `0xdf111111: 401,713`、`0xff222222: 18,112`、`0xffffffff: 4,738`、`segv=0`。
- **结构验证**：标题（`No9_TITLE`）、6 行正文说明（`No10..No15_CHANGE_MESSAGE_LINE_1..6`）以及底部 `OK`（`No6_NEXT_OK`）与 `Cancel`（`No4_CANCEL`）共 9 条文本全部由 `ResourceManager` 解析并贴出（纯白字形像素高达 `4,738`）。

## 4. 726 — Wireless LAN / Wi-Fi SSID 扫描列表页（Page 43，`0x02ea5560`，11 行）

- **导出文件**：`menu-726-wlanscan43.png`
- **Guest 渲染统计**：`synced=True seq=8 text_ok=5 fill=4 icon=1`
- **像素统计**：`nz=435,024`、纯白像素 `708`、主色分布 `0xdf111111: 424,970`、`0xff222222: 6,437`、`0xff444444: 1,640`、`segv=0`。
- **结构验证**：顶部标题（`No3_TITLE`）、三列表头（`No12_STATUS`、`No11_SSID`、`No17_SEC`）、右上角 `Set` 按钮（`No20_SETTING_LIST_SET`）及分隔线完整渲染。

## 5. 727–728 — 三列设置列表页（Page 66 `0x02eacdc0` / Page 73 `0x02eafac0`）

- **727 (`menu-727-setlist66.png`)**：Page 66（`0x02eacdc0`，10 行）— `text_ok=5 fill=4 icon=1 nz=435,024 white=942 segv=0`。
- **728 (`menu-728-setlist73.png`)**：Page 73（`0x02eafac0`，10 行）— `text_ok=4 fill=4 icon=1 nz=435,024 white=782 segv=0`。

## 6. 729–730 — 2/3 行确认弹窗（Page 72 `0x02eaf7a8`）与执行/取消弹窗（Page 93 `0x02eb4a58`）

- **729 (`menu-729-confirm72.png`)**：Page 72（`0x02eaf7a8`，10 行，`OK / Cancel` 确认对话框）— `text_ok=4 fill=4 icon=0 nz=144,716 white=1,175 segv=0`。
- **730 (`menu-730-execdlg93.png`)**：Page 93（`0x02eb4a58`，12 行，`Execute / Cancel` 模态对话框）— `text_ok=2 fill=5 icon=3 nz=171,444 white=507 segv=0`。

## 7. 731–732 — 双栏设置详情页（Page 77 `0x02eb1530`）与二层设置横幅页（Page 112 `0x02eb8760`）

- **731 (`menu-731-splitset77.png`)**：Page 77（`0x02eb1530`，11 行，左右双栏设置值 + 底部辅助说明）— `text_ok=4 fill=3 icon=0 nz=440,748 white=652 segv=0`。
- **732 (`menu-732-banner112.png`)**：Page 112（`0x02eb8760`，11 行，二层顶部横幅设置页）— `text_ok=4 fill=1 icon=2 nz=10,315 white=121 segv=0`。

## 8. 733–734 — 15 键 3×5 菜单宫格页（Page 64 `0x02eac280`）与 10 键 2×5 媒体宫格页（Page 57 `0x02eaa810`）

- **733 (`menu-733-menugrid64.png`)**：Page 64（`0x02eac280`，34 行，3×5 共 15 键宫格 + Index/Page 导航栏）— `text_ok=2 fill=26 icon=1 nz=461,624 white=211 segv=0`。
- **734 (`menu-734-mediagrid57.png`)**：Page 57（`0x02eaa810`，18 行，2×5 共 10 键媒体宫格）— `text_ok=1 fill=16 icon=0 nz=435,024 white=125 segv=0`。

---

## 9. 723–734 汇总表

| 编号 | 页面描述 | 表偏移 / 行数 | PNG 文件 | `text_ok / fill / icon` | `nz` | 纯白像素 | `segv` |
|---|---|---|---|---|---:|---:|---:|
| 723 | 253 行完整取景器主 HUD | `0x02e96608` (287) | `menu-723-hudmain253.png` | `82 / 0 / 119` | 45,807 | 0 | 0 |
| 724 | TC / 电平表 / 6 键状态面板 | `0x02e9ad78` (35) | `menu-724-tcstatus35.png` | `7 / 19 / 0` | 331,776 | 446 | 0 |
| 725 | 6 行变更通知对话框 | `0x02eb2d60` (10) | `menu-725-changemsg81.png` | `9 / 3 / 1` | 435,024 | 4,738 | 0 |
| 726 | Wi-Fi SSID 扫描列表页 | `0x02ea5560` (11) | `menu-726-wlanscan43.png` | `5 / 4 / 1` | 435,024 | 708 | 0 |
| 727 | 三列设置列表页 (Page 66) | `0x02eacdc0` (10) | `menu-727-setlist66.png` | `5 / 4 / 1` | 435,024 | 942 | 0 |
| 728 | 编号设置列表页 (Page 73) | `0x02eafac0` (10) | `menu-728-setlist73.png` | `4 / 4 / 1` | 435,024 | 782 | 0 |
| 729 | 2/3 行确认弹窗 (Page 72) | `0x02eaf7a8` (10) | `menu-729-confirm72.png` | `4 / 4 / 0` | 144,716 | 1,175 | 0 |
| 730 | 执行/取消弹窗 (Page 93) | `0x02eb4a58` (12) | `menu-730-execdlg93.png` | `2 / 5 / 3` | 171,444 | 507 | 0 |
| 731 | 左右双栏设置详情页 (Page 77) | `0x02eb1530` (11) | `menu-731-splitset77.png` | `4 / 3 / 0` | 440,748 | 652 | 0 |
| 732 | 二层设置横幅页 (Page 112) | `0x02eb8760` (11) | `menu-732-banner112.png` | `4 / 1 / 2` | 10,315 | 121 | 0 |
| 733 | 15 键 3×5 菜单宫格页 (Page 64) | `0x02eac280` (34) | `menu-733-menugrid64.png` | `2 / 26 / 1` | 461,624 | 211 | 0 |
| 734 | 10 键 2×5 媒体宫格页 (Page 57) | `0x02eaa810` (18) | `menu-734-mediagrid57.png` | `1 / 16 / 0` | 435,024 | 125 | 0 |

前序报告：`EVIDENCE-715-722.md`
