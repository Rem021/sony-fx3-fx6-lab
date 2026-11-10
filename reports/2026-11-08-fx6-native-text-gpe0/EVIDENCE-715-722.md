# EVIDENCE 715–722：Paint 键盘输入浮层（102 行）、Media 状态页（48 行）、Clip 12 宫格缩略图（39 行）、Status Icon / Date Picker / Media Format / Direct Menu / HUD Tracking

时间：2026-11-10（America/Los_Angeles）

源码：`outputs/fx3-vm-trial/src/fx6_pages_715_718.c` 与 `outputs/fx3-vm-trial/src/fx6_live_guest.c`（16 页完整交互版）。
全部在 QEMU Guest 内由真实 `appFw.so + libuxengine.so + TextRM + ResourceManager` 渲染至物理显存 `gpe0 @ 0x41e001000`（1024×540×4），并开启：
- 每行真实扩展样式字段（`+0x1c/+0x24/+0x28/+0x30/+0x34`，`g_use_extras=1`）
- `0x042d58d0`（`view_menu_item`）按钮底框与 `+0x18` 文本标签渲染
- `0x042d58f0`（`clip_thumbnail`）4×3 缩略图宫格底框与当前选中高亮框（`0x0200c014`）
- `0x042d58b0`（`SSA / SSB / SSP`）存储卡容量进度条轨道与填充条
- `0x042d5a50` 大尺寸九宫格背景图层优先铺底（Pass 1）

所有 PNG 仅通过 Python 统计像素与非零覆盖率，未对任何 `.png` 调用图像读取工具。

---

## 1. 715 — Paint / On-Screen Keyboard 文本输入浮层（Page 4，`0x02e92c18`，102 行）

- **导出文件**：`menu-715-paintoverlay102.png`
- **Guest 渲染统计**：`synced=True seq=2 text_ok=7 fill=67 icon=3`
- **像素统计**：`nz=435,024`（完整 `912×477` 面板）、纯白像素 `1,347`、主色分布 `0xdf111111: 264,916`、`0xff222222: 114,476`、`0xff333333: 48,416`、`segv=0`。
- **结构验证**：67 个原生 `view_fill` 完整画出 `912×477` 面板底色、26 个字母键帽（`No41_KEY_A..Z`）、模式切换键（`Upper/Lower/Numeric/Symbol`）、底部操作键（`Cancel/Done/Space/Backspace/Left/Right`）、双层输入框（`No16_TEXT_BOX` / `No17_TEXT_BOX`）及 27 个输入游标刻度（`No140_TEXT_BOX_INPUT_POS_1..27`），7 条真实文本标签与 3 个图标全部贴出。

## 2. 716 — Media Status 存储卡状态页（Page 58，`0x02eaad68`，48 行）

- **导出文件**：`menu-716-mediastatus48.png`
- **Guest 渲染统计**：`synced=True seq=3 text_ok=11 fill=18 icon=7`
- **像素统计**：`nz=461,624`、纯白像素 `1,731`、主色分布 `0xdf111111: 327,705`、`0xff222222: 113,448`、`0xff444444: 9,060`、`segv=0`。
- **结构验证**：完整渲染 Slot A（`SSA`）、Slot B（`SSB`）、Proxy（`SSP`）三栏存储卡图标、写保护锁图标、容量进度条（`0x042d58b0`）、剩余时间/寿命文案及右侧 3 个 `Format` 按钮（`0x042d58d0` + `0x0200220f`）。

## 3. 717 — Clip Thumbnail Browser 12 宫格缩略图浏览页（Page 12，`0x02e9b798`，39 行）

- **导出文件**：`menu-717-clipgrid39.png`
- **Guest 渲染统计**：`synced=True seq=4 text_ok=9 fill=16 icon=9`
- **像素统计**：`nz=552,960`（**100% 全屏铺满**）、纯白像素 `766`、主色分布 `0xff222222: 321,552`、`0xff000000: 225,862`、`0xff888888: 1,576`、`0xff00aaff: 1,356`、`segv=0`。
- **结构验证**：顶部 Header（`No1_clip_header` + `No4_option_bg`）、底部 Footer（`No30_clip_footer`）、中间 4×3 共 12 个缩略图槽位（`No10..No21_clip_thumbnail`）及选中槽橙色高亮框、右侧滚动条、9 条真实片段元数据文案与 9 个媒体/签名图标完整呈现。

## 4. 718 — Status Icon / Radio Button 状态设置页（Page 92，`0x02eb44b8`，19 行）

- **导出文件**：`menu-718-statusicon19.png`
- **Guest 渲染统计**：`synced=True seq=5 text_ok=7 fill=11 icon=5`
- **像素统计**：`nz=435,024`、纯白像素 `1,915`、主色分布 `0xff222222: 277,899`、`0xdf111111: 151,483`、`0xffffffff: 1,915`、`segv=0`。
- **结构验证**：左列 4 个 RadioButton（`No7..No10_RADIOBUTTON`）、右列 4 个 TouchButton（`No11..No14_TOUCHBUTTON`）、中轴分隔线（`No23_BAR`）、4 个指向箭头（`No16..No19_ARROW`）及顶部标题与当前值全部渲染。

## 5. 719–722 — Media Format Confirm / Date Picker / Direct Menu / HUD Tracking

- **719 (`menu-719-mediafmt49.png`)**：Page 74（`0x02eafdd8`，49 行，Media Format Confirm 双栏页）— `text_ok=1 fill=32 icon=2 nz=438,675 white=386 segv=0`。
- **720 (`menu-720-touchdate16.png`)**：Page 28（`0x02ea2e48`，16 行，Date/Time 触控滚轮选择页）— `text_ok=6 fill=8 icon=2 nz=435,024 white=613 segv=0`。
- **721 (`menu-721-pg5direct40.png`)**：Page 5（`0x02e94c28`，40 行，Direct Menu List 浮层框）— `text_ok=0 fill=31 icon=0 nz=432,317 segv=0`。
- **722 (`menu-722-hudtrack20.png`)**：Page 8（`0x02e95cc0`，20 行，HUD Tracking）+ Page 7（`0x02e959a8`，7 行）— `text_ok=17 fill=0 icon=1 nz=28,970 segv=0`。

---

## 6. 715–722 汇总表

| 编号 | 页面描述 | 表偏移 / 行数 | PNG 文件 | `text_ok / fill / icon` | `nz` | 纯白像素 | `segv` |
|---|---|---|---|---|---:|---:|---:|
| 715 | Paint / Keyboard 文本输入浮层 | `0x02e92c18` (102) | `menu-715-paintoverlay102.png` | `7 / 67 / 3` | 435,024 | 1,347 | 0 |
| 716 | Media Status 存储卡状态页 | `0x02eaad68` (48) | `menu-716-mediastatus48.png` | `11 / 18 / 7` | 461,624 | 1,731 | 0 |
| 717 | Clip 12 宫格缩略图浏览页 | `0x02e9b798` (39) | `menu-717-clipgrid39.png` | `9 / 16 / 9` | 552,960 | 766 | 0 |
| 718 | Status Icon / Radio Button 页 | `0x02eb44b8` (19) | `menu-718-statusicon19.png` | `7 / 11 / 5` | 435,024 | 1,915 | 0 |
| 719 | Media Format Confirm 双栏页 | `0x02eafdd8` (49) | `menu-719-mediafmt49.png` | `1 / 32 / 2` | 438,675 | 386 | 0 |
| 720 | Date/Time 触控选择页 | `0x02ea2e48` (16) | `menu-720-touchdate16.png` | `6 / 8 / 2` | 435,024 | 613 | 0 |
| 721 | Direct Menu List 浮层框 | `0x02e94c28` (40) | `menu-721-pg5direct40.png` | `0 / 31 / 0` | 432,317 | 0 | 0 |
| 722 | HUD Tracking + Page 7 HUD | `0x02e95cc0` (27) | `menu-722-hudtrack20.png` | `17 / 0 / 1` | 28,970 | 0 | 0 |

前序报告：`EVIDENCE-711-714.md`
