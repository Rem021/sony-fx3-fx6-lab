# 全球 Sony 实机情报 Wave 54（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Switch V/H AF Area]`/`[Focus Area Limit]`/`[Focus Area Color]`、`[Exposure Std. Adjust]` 1/6 EV 校准与 `[Bracket Settings]`、`[TC/UB Disp. Setting]`/`[User Bit Time Rec]`/`[Time Code Format]`，及回放 `[Copy]` 双向写入与 Slot-1 Tier-0 保险库护栏/`[Slide Show]`）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Switch V/H AF Area*、*Focus Area Limit*、*Focus Area*、*Focus Area Color*、*Touch Focus*、*Exposure Std. Adjust*、*Bracket Settings*、*Self-timer(Single)*、*TC/UB*、*TC/UB Disp. Setting*、*Select Playback Media*、*Copy*、*Slide Show*、*Power Save Start Time*、*List of default setting values*），Sony `ILME-FX6` Operating Instructions（`5-024-458-18`, Software Ver. 6.0），以及严格 `os.O_RDONLY` 本地 donor 二进制/字符串包交叉实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so`、`FX6 string_english.uxc` / `_2.uxc`）。
- **硬件安全态势**：严格只读本地 donor 分析（`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`/图标前缀、ELF 符号与官方文档条款）与 **`推断`**。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[Switch V/H AF Area]` / `[Focus Area Limit]` / `[Focus Area Color]`）**：
   - **实测事实**：`[Switch V/H AF Area]`（`MENU -> (Focus) -> [Focus Area]`，默认 `Off`，选项 `Off` / `AF Point Only` / `AF Point + AF Area`）**仅适用于静态照片（Still）且仅在 `[Focus Mode] = [AF-C]` 时生效**，依赖机内 3 态重力方向传感器（`VH_AF_AREA_ORIENTATION_INFORMATION_{0_DEGREES,90_DEGREES,270_DEGREES,INVALID}`，镜头垂直朝上/朝下时返回 `INVALID`），在 `Movie`、`iAuto`、数码变焦、AF 激活中、连拍、自拍倒计时及 `[Focus Magnifier]` 下禁止切换，且变更此项会清空各方向记忆的对焦位置；支持 `[Camera Settings Reset]`。
   - **实测事实**：`[Focus Area Limit]`（Still / Movie 适用，默认 `―`，支持 `[Camera Settings Reset]`）在 `FX3` 上**精确暴露 14 项 `BKID_APP_focus_area_limit_*` 复选框**（`Wide` / `Zone` / `Center Fix` / `Spot: S/M/L` / `Expand Spot` 及其 `7` 项 `Tracking:` 对应项；ELF 中 `model::focus_area_limit_{xl,xs,custom_1..3}` 为无 BKID/无 UXC 的休眠 Alpha 符号），且 Movie/`S&Q` 中 `[Tracking]` 不可选（改用 Touch Tracking）；当只剩 1 项被勾选时，`.uxc` `0xea28` 禁止切换并要求至少勾选 2 项。`[Focus Area Color]`（Still / Movie / `S&Q` 适用，选项 `White` 默认 / `Red`）**不支持 `[Camera Settings Reset]`**（需 `[Initialize]`）。`ILME-FX6` 无自动竖拍方向切换、无 `Focus Area Limit` 勾选裁剪、无 `White/Red` 边框切换（移动对焦框时变橙色，另有 `Focus Area Marker` 与 `Focus Area Ind.(AF-S)`）。
2. **子系统 2（`[Exposure Std. Adjust]` 与 Still `[Bracket Settings]`）**：
   - **实测事实（消歧定论）**：`ILME-FX3` 的 `[Exposure Std. Adjust]`（`MENU -> (Exposure/Color) -> [Exposure Comp.] -> [Exposure Std. Adjust]`）支持 **全部 5 种测光模式**（**`Multi`** / **`Center`** / **`Spot`** / **`Entire Screen Avg.`** / **`Highlight`**），绝非仅 4 种：`ilc/2210`、`FX3 appFw.so`（`BKID_APP_setting_exposure_standard_metering_mode_{multi,center,spot,average,highlight}`，每项 13 档 `-1 .. +1 EV` @ `1/6 EV` 步进）与 `_f.uxc` 5 组带测光图标的前缀条目（`\ue59f / \ue2b3 / \ue2b4 / \ue597 / \ue596`）100% 吻合；进入前弹出警示确认框（`.uxc` `0xe567`），调整后独立写入 EXIF（不叠加进 `Exposure Comp.`），同步偏移 `M.M.`（Metered Manual）基准与 Spot AEL 锁定值，在包围曝光期间修改会重置张数，且 **`[Camera Settings Reset]` 不可重置（仅 `[Initialize]` 可恢复 `±0`）**。
   - **实测事实**：Still `[Bracket Settings]`（`MENU -> (Shooting) -> [Drive Mode] -> [Bracket Settings]`）包含 `[Selftimer during Bracket]`（`Off` 默认 / `2 Sec` / `5 Sec` / `10 Sec`）与 `[Bracket order]`（`0→-→+` 默认 / `-→0→+`），两者均支持 `[Camera Settings Reset]`。`ILME-FX6` 无 `[Exposure Std. Adjust]` 且无静态照片包围曝光功能（`FX6 appFw.so` 中 `bracket_*` 为休眠符号，FX6 仅提供 `Auto Exposure Level`、`Iris`、`e-ND`、`AGC` 与 `Exposure Index`）。
3. **子系统 3（`[TC/UB Disp. Setting]`、`[User Bit Preset]` / `[User Bit Time Rec]` 与 `[Time Code Format]`）**：
   - **实测事实**：`MENU -> (Shooting) -> [TC/UB]` 包含 6 项核心设置（`Time Code Preset` 默认 `00:00:00.00`、`User Bit Preset` 默认 `00 00 00 00`、`Time Code Format` / `_f.uxc` `TC Format` 默认 `DF`、`Time Code Run` 默认 `Rec Run`、`Time Code Make` 默认 `Preset`、`User Bit Time Rec` 默认 `Off`），**全部 6 项均不支持 `[Camera Settings Reset]`**（需 `[Initialize]`）；`[TC/UB Disp. Setting]` 位于 `MENU -> (Setup) -> [Display Option]`（选项 `Counter` [Help Guide 亦称 `Duration`] / `TC` [默认] / `U-Bit`，回放期间仅在动态影像回放时可切换，见 `.uxc` `0xe728`）。`[Time Code Format]` 仅在 `[NTSC/PAL Selector] = NTSC` 时可调 `DF / NDF`，在 `23.98p` / `24.00p` 下强制锁定为 `NDF`（显示 `[-]`），在 `PAL` 制式下隐藏。`ILME-FX6` 配备物理 BNC `TC IN/TC OUT` 端口与实体 `IN/OUT` 拨动开关（锁相显示 `EXT-LK`）、`TC/Media > Timecode / Users Bit (Mode: Fix/Time) / TC Display (Duration/Timecode/Users Bit) / HDMI TC Out`，并在 `FX6 appFw.so` 带有 `BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING`；FX3 则无物理 BNC 时码口（仅靠机身/配件适配方案）。
4. **子系统 4（回放 `[Select Playback Media]`、插槽间 `[Copy]` 方向性保险库危害与 `[Slide Show]`）**：
   - **实测事实**：`[Select Playback Media]`（`MENU -> (Playback) -> [Playback Target]`）默认 **`Slot 1`**；`MENU -> (Playback) -> [Edit] -> [Copy]`（`FUNC_copy_content`）**始终以当前 `[Select Playback Media]` 为源槽位、将当前日期或当前文件夹的全部影像/视频复制到对侧槽位**，受 `get_battery_status_for_copy` 电量门控及目标卡速率门槛（`.uxc` `0xe80e` / `0xe8ca`：需 `SDXC Class10/U1/V10` 以上或 `CFexpress`）约束，复制后目标卡取消群组显示并清除 `Protect` 保护标志。`[Slide Show]`（`Repeat: On/Off` 默认 `Off`，`Interval: 1/3/5/10/30 Sec` 默认 `3 Sec`，不支持 `[Camera Settings Reset]`）仅可在 `Date View` 或 `Folder View(Still)` 启动，且播放期间**自动旁路 `[Power Save Start Time]`**。
   - **推断（关键双向安全性不对称防线）**：`[Copy]` 的写入目标完全由 `[Select Playback Media]` 反向决定——当 `[Select Playback Media] = Slot 1` 时，`[Copy]` 从 `Slot 1` 只读复制到 `Slot 2`；**一旦用户切换到 `[Select Playback Media] = Slot 2`，执行 `[Copy]` 将向 `Slot 1` 写入大量文件与 `AVF_INFO` 数据库**！因此当 `Slot 1` 挂载只读 Tier-0 恢复保险库（`pnflasha`/`cnflasha`/`CAMSET01.DAT`）时，面向 `Slot 2 -> Slot 1` 方向的 `[Copy]` **必须 fail-closed 拦截并返回 `EROFS` / `EBUSY`**，确保 `slot1_data_sector_writes == 0`。对比之下，`ILME-FX6 Ver. 6.01`（`5-024-458-18`）机内菜单**不暴露 `Copy Clip` / `Copy All`**（`FX6 appFw.so` 中的 `USER_MENU_COPY_CLIP*` 与 `string_english_2.uxc` `Copy Clip` 属于休眠遗留条目），实机依赖 `Transfer Clip`（FTP）与 Catalyst Browse/Prepare 完成素材转储。

---

## 1. 子系统 1：`[Switch V/H AF Area]`、`[Focus Area Limit]` 与 `[Focus Area Color]` 实证

### 1.1 `ILME-FX3 Ver. 7.02` 菜单规格、方向传感器门控与 14 项 `Focus Area Limit` 实证

- **菜单路径（`实测事实`，`ilc/2210/v1/en/`）**：`MENU` -> `(Focus)` -> `[Focus Area]` 下包含 **`[Switch V/H AF Area]`**、**`[Focus Area Limit]`** 与 **`[Focus Area Color]`**。

| 菜单项 | 可选值与刻度 | 默认值 | `[Camera Settings Reset]` | 适用模式 | `FX3 appFw.so` BKID / 状态与锁定边界（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **`[Switch V/H AF Area]`** (`_f.uxc` `0x73ae`) | `Off` (`0x63aa`) / **`AF Point Only`** (`0x615a`) / **`AF Point + AF Area`** (`0x69e8`) | **`Off`** | **Can be reset** | **仅 Still** | `BKID_APP_setting_vertical_horizontal_focus_area_switch`; `VAL_setting_vertical_horizontal_focus_area_switch_VERTICAL_HORIZONTAL_FOCUS_AREA_SWITCH_{OFF,FOCUS_POSITION_ONLY,FOCUS_POSITION_FOCUS_AREA}` |
| **`[Focus Area Limit]`** (`_f.uxc` `0x6de2`) | 14 个独立复选框（多选 + `[OK]`） | **`―`** *(全勾选/未裁剪)* | **Can be reset** | **Still, Movie** | `BKID_APP_focus_area_limit_{wide,zone,center,flexible_spot_{s,m,l},expanded_flexible_spot}` + 7 个 `tracking_af_*`；只留 1 项时 `.uxc` `0xea28` 禁止再取消 |
| **`[Focus Area Color]`** (`_f.uxc` `0x74ad`) | **`White`** (`.uxc` `0xe883`) / **`Red`** (`.uxc` `0xe8c6`) | **`White`** | **Not available** *(需 `[Initialize]`)* | **Still, Movie, `S&Q`** | `BKID_APP_setting_focus_frame_color`（`_f` `0x7087` 保留旧名 `Focus Frame Color`）；`extern_menu_focus_frame_color` |

- **`[Switch V/H AF Area]` 方向传感器状态机与 8 项锁定边界（`实测事实`）**：
  1. `FX3 appFw.so` 维护 `vh_af_area_orientation_information`（枚举：`VH_AF_AREA_ORIENTATION_INFORMATION_0_DEGREES`、`90_DEGREES`、`270_DEGREES` 与 `INVALID`），并为水平（`0_degrees`）、快门朝上竖拍（`90_degrees`）和快门朝下竖拍（`270_degrees`）分别保存独立的 `autofocus_area_*_{0,90,270}_degrees` 坐标与区域配置。
  2. 当镜头垂直朝上或朝下时，重力姿态判为 `INVALID`，不触发方向切换；`ilc/2210` 明确规定仅在 **`[Focus Mode] = [AF-C]`** 下生效，且在 **`[Intelligent Auto]`、Movie 拍摄期间、数码变焦、AF 动作中、连拍、自拍倒计时、`[Focus Magnifier]` 激活期间**均不切换。修改 `[Switch V/H AF Area]` 选项会清空三个方向已记忆的对焦设置。
- **`[Focus Area Limit]` 实机复选框精确清单（`14` 项 `BKID_APP_focus_area_limit_*` vs 休眠平台符号，`实测事实`）**：
  - **实机暴露 14 项**：`Wide`、`Zone`、`Center Fix` (`_f` `0x7824`)、`Spot: S` / `Spot: M` / `Spot: L`、`Expand Spot`，以及 `Tracking: Wide`、`Tracking: Zone`、`Tracking: Center Fix` (`_f` `0x602b`)、`Tracking: Spot S/M/L`、`Tracking: Expand Spot`。
  - **休眠符号证伪**：`FX3 appFw.so` 的 `model::` 命名空间虽包含 `focus_area_limit_flexible_spot_{xl,xs}` 与 `focus_area_limit_custom_{1..3}`（面向 `ILCE-7RM5` / `ILCE-6700` 等机型的共享 BIONZ XR 代码），但 **无对应 `BKID_APP_*` 存储键，且 `FX3 string_english_f.uxc` 中不存在 `Spot: XL`、`Spot: XS` 或 `Custom 1` 词条**。
  - **Movie 差异与最小 2 项下限**：`ilc/2210` 明确标注在 `Movie` 或 `S&Q Motion` 模式下 `[Tracking]` 不可在 `[Focus Area]` 中选取（视频追踪需通过 `Touch Tracking`）；同时当用户将可选区域限制至仅剩 1 项并尝试切换时，系统弹出 `.uxc` `0xea28`（*"Selectable AF areas are limited to 1 so changes cannot be made. Set the focus area limit to 2 AF areas or more."*）；若取消勾选已注册进 `[Switch V/H AF Area]` 或 `[AF Area Registration]` 的区域，已注册设置会同步变更。

### 1.2 `ILME-FX6 Ver. 6.01` 对焦区域体系对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`, `5-024-458-18`) |
| :--- | :--- | :--- |
| **`[Switch V/H AF Area]`** | 支持 `Off / AF Point Only / AF Point + AF Area`（3 方向 `0°/90°/270°` 记忆，Still `AF-C`） | **无此菜单**（`FX6 appFw.so` 无 `vertical_horizontal_focus_area_switch`；虽继承静态 `BKID_APP_AUTOFOCUS_AREA_*_{0,90,270}_DEGREES` 坐标占位符，但全机无竖拍自动切换功能） |
| **`[Focus Area Limit]`** | 14 项勾选裁剪（含 `Tracking:*`），支持 `[Switch Focus Area]` 自定义键轮询 | **无此菜单**（`FX6` 仅提供 `Shooting > Focus > Focus Area` 与 `Focus Area(AF-S)`，`string_english.uxc` `0x222c`/`0x223c`，可通过可编程键 `<1>..<9>` / `Focus Hold` 调出） |
| **`[Focus Area Color]`** | `White` / `Red`（`Focus Area Color`） | **无 `White/Red` 选项**；FX6 移动对焦框时框体变为**橙色**，并通过 `Monitoring > Display On/Off > Focus Area Ind.(AF-S)`（`0x2236`）及 `Focus Area Marker`（`string_english_2.uxc` `0x4d6b`）控制显示 |

---

## 2. 子系统 2：`[Exposure Std. Adjust]`（1/6 EV 分测光校准）与 Still `[Bracket Settings]`

### 2.1 `[Exposure Std. Adjust]` 5 测光模式消歧实证与 reset 隔离（`实测事实`）

- **菜单路径**：`MENU` -> `(Exposure/Color)` -> `[Exposure Comp.]` -> **`[Exposure Std. Adjust]`**（`_f.uxc` `0x6114` / `0x6f71` / `0x7578`）。
- **核心消歧定论（`5` 种模式，非 `4` 种）**：交叉核对 `ilc/2210` 官方文档（*Exposure Std. Adjust* 与 *List of default setting values*）及 `FX3 appFw.so`、`FX3 _f.uxc`，`ILME-FX3 Ver. 7.02` 明确支持 **5 种测光模式独立校准**，范围均为 **`-1 EV` 至 `+1 EV`（`1/6 EV` 步进，共 13 档：`MINUS_1, MINUS_5_6..MINUS_1_6, 0, PLUS_1_6..PLUS_5_6, PLUS_1`）**：

| 测光模式 (`ilc/2210`) | `_f.uxc` 图标词条 & 说明 `resid16` | `FX3 appFw.so` 持久化 Key (`BKID_APP_*`) | 默认值 | `[Camera Settings Reset]` |
| :--- | :--- | :--- | :---: | :---: |
| **`Multi`** | `_f` `0x6d79` (`\ue59fMulti`), `0x7606`, `0x6dc0` | `BKID_APP_setting_exposure_standard_metering_mode_multi` | **`±0`** | **Not available** |
| **`Center`** | `_f` `0x6da8` (`\ue2b3Center`), `0x77d3`, `0x6f8c` | `BKID_APP_setting_exposure_standard_metering_mode_center` | **`±0`** | **Not available** |
| **`Spot`** | `_f` `0x7a8a` (`\ue2b4Spot`), `0x63a4`, `0x7009` | `BKID_APP_setting_exposure_standard_metering_mode_spot` | **`±0`** | **Not available** |
| **`Entire Screen Avg.`** | `_f` `0x6f15` (`\ue597Entire Screen Average`), `0x7a05`, `0x605e`, `0x66d3` | `BKID_APP_setting_exposure_standard_metering_mode_average` | **`±0`** | **Not available** |
| **`Highlight`** | `_f` `0x7600` (`\ue596Highlight`), `0x6974`, `0x7a23` | `BKID_APP_setting_exposure_standard_metering_mode_highlight` | **`±0`** | **Not available** |

- **运行语义与安全特性（`实测事实`）**：
  1. **警示弹窗与重置隔离**：进入调节前触发 `.uxc` `0xe567`（*"This function adjusts the standard of optimum exposure. Generally, adjustment is not necessary. Adjust?"*）。5 项偏移全部不受 `[Camera Settings Reset]` 影响，**仅 `[Initialize]` 可恢复 `±0`**。
  2. **独立 EXIF 与 `M.M.` 耦合**：调节值通过 `PID_SET_STANDARD_EXPOSURE_SETTING` 注入测光基线，**独立写入 EXIF，不计入也不改变 `[Exposure Comp.]` 数值**；同步偏移 `M.M.`（Metered Manual）手动测光零点；Spot AEL 锁定时采用 `Spot` 模式校准值；在包围曝光拍摄序列中途调整 `[Exposure Std. Adjust]` 会**重置包围曝光已拍张数**。

### 2.2 Still `[Bracket Settings]`（自拍定时与顺序）与 `ILME-FX6` 对比

- **菜单路径（`实测事实`，`ilc/2210`）**：`MENU` -> `(Shooting)` -> `[Drive Mode]` -> **`[Bracket Settings]`**（`_f.uxc` `0x6466` / `0x6f6f`）。

| 子菜单项 | 实机可选值 | 默认值 | `[Camera Settings Reset]` | `FX3 appFw.so` Key / 枚举与行为约束（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **`[Selftimer during Bracket]`** (`_f` `0x6ef5`) | **`Off`** / **`2 Sec`** / **`5 Sec`** / **`10 Sec`** (`.uxc` `0xe207..0xe209`) | **`Off`** | **Can be reset** | `BKID_APP_setting_bracket_self_timer`, `BRACKET_SELF_TIMER_{OFF,2SEC,5SEC,10SEC}`; 通过 `VAL_HAITA_setting_bracket_self_timer_setting_menu_drive_mode_*` 门控仅对 `BRACKET_SINGLE / CONT_BRACKET / DRO_ADV_BRACKET / FOCUS_BRACKET / WHITE_BALANCE_BRACKET` 生效 |
| **`[Bracket order]`** (`_f` `0x76b1`, `.uxc` `0xe346`) | **`0→-→+`** (`.uxc` `0xe1d3`) / **`-→0→+`** (`.uxc` `0xe1d4`) | **`0→-→+`** | **Can be reset** | `BKID_APP_setting_bracket_order`, `BRACKET_ORDER_{ZERO_MINUS_PLUS,MINUS_ZERO_PLUS}`; 作用于曝光包围与白平衡包围（注：Focus Bracket 使用独立 `BKID_APP_setting_focus_bracket_order`：`0→-→+` vs `0→+`） |

- **`ILME-FX6 Ver. 6.01` 对比（`实测事实`）**：
  - `FX6` 全菜单**无 `[Exposure Std. Adjust]`**（`FX6 appFw.so` 中 `exposure_standard` 检索结果为 `0` 命中），且无静态照片包围曝光功能（`FX6 appFw.so` 中的 `setting_bracket_order` / `setting_bracket_self_timer` 属于纯电影机未接线的休眠 Alpha 符号）；`FX6` 在 `Custom` / `Flexible ISO` 下的测光偏移通过 `Shooting > Auto Exposure > Auto Exposure Level`（以及 `Iris`、`e-ND`、`AGC`）完成，`Cine EI` 下则固定增益并由 `Exposure Index` 调整监看参考亮度。

---

## 3. 子系统 3：`[TC/UB Disp. Setting]`、`[User Bit Preset]`/`[User Bit Time Rec]` 与 `[Time Code Format]`

### 3.1 `ILME-FX3 Ver. 7.02` `[TC/UB]` 与 `[TC/UB Disp. Setting]` 完整矩阵（`实测事实`）

- **菜单路径**：
  - 时码与用户比特配置：`MENU` -> `(Shooting)` -> **`[TC/UB]`**（`_g.uxc` `0x6389`）。
  - 屏幕/HDMI 计数显示切换：`MENU` -> `(Setup)` -> `[Display Option]` -> **`[TC/UB Disp. Setting]`**（`_f.uxc` `0x6b0c`）。

| 菜单项 (`ilc/2210` + UXC) | 可选值 / 范围 | 默认值 | `[Camera Settings Reset]` | `FX3 appFw.so` Key / 枚举与制式门控（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **`[Time Code Preset]`** (`_f` `0x6b63`) | `00:00:00.00` .. `23:59:59.29` (`59.94p`) / `.24` (`50p`) / 4 帧步进 (`23.98p`) | **`00:00:00.00`** | **Not available** | `BKID_APP_tc_preset_time_{hour,minute,second,frame}`; 按 `(Delete)` 归零 |
| **`[User Bit Preset]`** (`_f` `0x7af2`) | 8 位十六进制 (`00 00 00 00` .. `FF FF FF FF`) | **`00 00 00 00`** | **Not available** | `BKID_APP_ub_preset_digit_{12,34,56,78}`, `FUNC_ub_preset_seq`; `User Bit Reset` (`_f` `0x758f`, `_g` `0x6441`) |
| **`[Time Code Format]`** (`_f` `0x6e3d`; 缩写 `TC Format` `0x761d`) | **`DF`** (`0x6d59`) / **`NDF`** (`0x6c6f`) | **`DF`** | **Not available** | `BKID_APP_setting_tc_format`, `TC_FORMAT_{DF,NDF,INVALID}`; **仅 `NTSC` 可用**；`23.98p` / `24.00p` 强制 `NDF`（UI 显示 `[-]`）；`PAL` 制式下菜单项隐藏 |
| **`[Time Code Run]`** (`_f` `0x7313`) | **`Rec Run`** / `Free Run` | **`Rec Run`** | **Not available** | `BKID_APP_setting_tc_run`; 配合 `Free Run` 可与外部时钟同步 |
| **`[Time Code Make]`** (`_f` `0x6b79`) | **`Preset`** / `Regenerate` | **`Preset`** | **Not available** | `BKID_APP_setting_tc_make`, `PID_SET_TC_MODE`, `PID_SET_TC_TYPE` |
| **`[User Bit Time Rec]`** (`_f` `0x7aa8`) | `On` (`0x7668`) / **`Off`** (`0x6cdd`) | **`Off`** | **Not available** | `BKID_APP_setting_ub_time_rec`, `VAL_setting_ub_time_rec_UB_TIME_REC_{ON,OFF}`; `On` 时将实时时/分/秒写入 User Bit |
| **`[TC/UB Disp. Setting]`** (`_f` `0x6b0c`) | **`Counter`** (`0x6c01`, Help Guide 亦称 `Duration`) / **`TC`** / **`U-Bit`** (`0x71ca`) | **`TC`** | **Not available** | `BKID_APP_setting_tc_ub_disp_setting`, `TC_UB_DISP_SETTING_{COUNTER,TC,U_BIT}`, `FUNC_toggle_set_tc_ub_disp_seq`; 回放时仅动态影像回放支持切换（`.uxc` `0xe728`） |

*(注：FX3 UXC 字符串包中 `Time Code Format`、`User Bit Preset`、`User Bit Time Rec`、`TC Format`、`DF`、`NDF`、`U-Bit` 在简中/繁中/日文包内均保留英文原词；仅 `TC/UB Disp. Setting` 与 `Counter` 进行了本地化翻译。)*

### 3.2 `ILME-FX6 Ver. 6.01` 专用 BNC `TC IN/OUT` 硬件时码架构对比（`实测事实`）

| 维度 | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`, `5-024-458-18`) |
| :--- | :--- | :--- |
| **硬件物理接口** | **无 BNC 时码接口**（外部时码输入依赖 Multi 接口专有线缆或音频轨 LTC） | **机身左侧物理 BNC `TC IN/TC OUT` 端口 + 实体 `IN / OUT` 拨动开关**（上拨 `IN`、下拨 `OUT`；外部锁定显示 **`EXT-LK`**，`BKID_APP_EXT_TC_LOCK_STATUS`）；另有 `BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING` |
| **菜单路径与命名** | `(Shooting) -> [TC/UB]` 与 `(Setup) -> [Display Option] -> [TC/UB Disp. Setting]` | **`TC/Media > Timecode`**（`Mode`: `Preset/Regen/Clock`; `Run`: `Rec Run/Free Run`; **`TC Format`**: `DF/NDF` `0x456d`; `Setting`; `Reset`）、**`TC/Media > Users Bit`**（`Mode`: **`Fix`** / **`Time`** `0x48b5..0x48b8`; `Setting`）、**`TC/Media > TC Display > Display Select`**（`Duration` / `Timecode` / `Users Bit`）、**`TC/Media > HDMI TC Out`** |
| **Reset 策略** | `[Camera Settings Reset]` 不重置 TC/UB（需 `[Initialize]`） | 独立存在于 `All File` 体系，支持 `Timecode Reset` 归零与物理/全菜单快速设置 |

---

## 4. 子系统 4：回放 `[Select Playback Media]`、双向 `[Copy]` 与 Slot-1 Tier-0 保险库护栏、`[Slide Show]`

### 4.1 `[Select Playback Media]` 与 `[Copy]` 机械流及双向不对称写入危害（`实测事实` + `推断`）

- **菜单路径（`实测事实`，`ilc/2210`）**：
  - 源卡选择：`MENU` -> `(Playback)` -> `[Playback Target]` -> **`[Select Playback Media]`**（`_f.uxc` `0x6bcd`，`BKID_APP_select_playback_media`，默认 **`Slot 1`**）。
  - 卡间复制：`MENU` -> `(Playback)` -> `[Edit]` -> **`[Copy]`**（`_f.uxc` `0x79fc`，`FUNC_copy_content`）。
- **实机运行机制与 4 项约束（`实测事实`）**：
  1. **方向由 `[Select Playback Media]` 唯一确定**：`[Copy]` 将**当前 `[Select Playback Media]` 选中槽位**中“当前回放日期”或“当前文件夹”内的静态影像/视频（含 `_f.uxc` `0x7b37..0x7b92` 展示的筛选条件：日期/文件夹/全卡、静态/视频/全部、星级/Shot Mark/保护过滤）复制到**对侧槽位**的存储卡（`_f` `0x68de` / `0x6f7e` / `0x7443`: *"Copy all ... to the memory card in slot ${v1}?"*）。
  2. **电量门控（Battery Gate）**：`FX3 appFw.so` 底层通过 `infra_wrapper_upm::detail::get_battery_status_for_copy` 校验供电状态，文档明确提示大批量复制耗时较长且需确保电池电量充足。
  3. **目标卡格式与速率门槛**：复制视频时目标卡必须满足对应编码速率要求，否则触发 `.uxc` `0xe80e` / `0xe8ca`（需高于 `SDXC Class10/U1/V10` 或 `CFexpress` 卡）并终止（`0xe366` *"Cannot copy."* / `0xe6db` *"Copy failed."*）。
  4. **目标卡元数据重构**：属于同一连拍/间隔群组的照片复制到目标卡后**不再作为群组显示**；原卡上的 **`Protect` 保护标志在目标卡上会被取消**。
- **关键安全防线：`Slot 1 <-> Slot 2` 双向不对称与 Fail-Closed 拦截（`推断`）**：
  - 在本实验室的双槽恢复架构下，**`Slot 1` 常驻承载 `pnflasha`/`cnflasha`/`CAMSET01.DAT` 的 Tier-0 只读恢复保险库**：
    - **方向 A（`[Select Playback Media] = Slot 1`）**：`[Copy]` 执行 `Slot 1 -> Slot 2`（仅读取 `Slot 1`、写入 `Slot 2`），不修改 `Slot 1` 扇区（前提是禁止同步刷新 `Slot 1` 的 `AVF_INFO`）。
    - **方向 B（`[Select Playback Media] = Slot 2`，高危写入方向！）**：执行 `[Copy]` 时目标槽位 `${v1}` 自动翻转为 **`Slot 1`**（`Slot 2 -> Slot 1`），`FUNC_copy_content` 将在 `Slot 1` 创建 `DCIM/`/`PRIVATE/M4ROOT/` 目录、写入媒体文件并重建 `Slot 1` 的 `AVF_INFO` ImageDB！
  - **强制护栏要求（`推断`）**：一旦安全预检检测到 `Slot 1` 挂载 Tier-0 恢复保险库或处于只读状态（`STATUS_OF_MEDIA_SLOT1_READ_ONLY` / `UNWRITABLE` / `LOCKED`），所有源于 `Slot 2`（`[Select Playback Media] = Slot 2`）的 `[Copy]` 分发**必须在进入写盘流水线前 fail-closed 拦截并返回 `EROFS` / `EBUSY`**，保证 `slot1_data_sector_writes == 0` 且 `slot1_avf_info_mutated == False`。

### 4.2 `[Slide Show]` 与 `[Power Save Start Time]` 旁路规则 + `ILME-FX6` 对比

- **菜单路径与参数（`实测事实`，`ilc/2210`）**：`MENU` -> `(Playback)` -> `[Viewing]` -> **`[Slide Show]`** -> `[Repeat]` / `[Interval]` -> `[Enter]`（`.uxc` `0xe2cc`，`FUNC_start_playback_slide_show`）。
  - **`[Repeat]`**（`_f` `0x685f`, `.uxc` `0xe2d1`）：`On` / **`Off`**（默认，播完一遍退出）；对应 `BKID_APP_setting_viewing_repeat`。
  - **`[Interval]`**（`.uxc` `0xe2cd`）：`1 Sec` / **`3 Sec`**（默认）/ `5 Sec` / `10 Sec` / `30 Sec`（`.uxc` `0xe2ce..0xe2d0`, `0xe4be..0xe4c3`）；对应 `BKID_APP_setting_viewing_interval`（`INTERVAL_{1,3,5,10,30}SEC`）。
  - **前置条件与 Reset**：仅可在 `[View Mode] = [Date View]` 或 `[Folder View(Still)]` 下启动；回放菜单项**不支持 `[Camera Settings Reset]`**（需 `[Initialize]`）。
  - **`[Power Save Start Time]` 旁路规则（`实测事实`）**：`ilc/2210` *Power Save Start Time*（`5 Min` 默认）明确规定，**在 `[Slide Show]` 播放期间自动停用省电休眠计时器（`DURING_PLAYBACK_SLIDESHOW`）**，防止自动待机中断循环展示。
- **`ILME-FX6 Ver. 6.01` 对比（`实测事实`）**：
  - `FX6` 无 `[Slide Show]`、无 `[View Mode]`（`Date View`/`Folder View(Still)`）、无面向单卡的静态/视频批量 `[Copy]` 菜单：`5-024-458-18`（p. 83 / p. 115）Thumbnail 菜单仅暴露 `Display Clip Properties`、`Set Clip Flag`、`Lock/Unlock Clip`、`Delete Clip`、`Transfer Clip`（FTP，上限 200 clips）、`Transfer Clip (Proxy)`、`Filter Clips` 与 `Thumbnail Caption`。虽然 `FX6 appFw.so` 与 `string_english_2.uxc` 保留了 `BKID_APP_USER_MENU_COPY_CLIP0/1` 与 `'Copy Clip'` (`0x4136` / `0x4fde`)、`'Copy All Clips'` (`0x4138` / `0x4fc5` / `0x55c5`) 等继承自 PXW-FX9 的休眠字符串，但在 `ILME-FX6` 实机上并未激活，素材跨卡/转储需通过 **Sony Catalyst Browse / Catalyst Prepare** 或 FTP 完成。

---

## 5. `O_RDONLY` 本地 Donor 审计台账与 4 语 `resid16` 一致性矩阵（`raw_firmware_bytes_leaked = 0`）

### 5.1 本波次已审计本地 Donor 文件台账（严格 `os.O_RDONLY`）

| Donor 工件 | 大小 (`B`) | SHA-256 | Wave 54 实测命中符号 / 关键证据 (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_vertical_horizontal_focus_area_switch` (`0/90/270/INVALID`), 14× `BKID_APP_focus_area_limit_*`, `BKID_APP_setting_focus_frame_color`, 5× `BKID_APP_setting_exposure_standard_metering_mode_{multi,center,spot,average,highlight}` (`MINUS_1..PLUS_1`), `PID_SET_STANDARD_EXPOSURE_SETTING`, `BKID_APP_setting_bracket_{self_timer,order}`, `BKID_APP_setting_{tc_format,tc_make,tc_run,tc_ub_disp_setting,ub_time_rec}`, `BKID_APP_{tc_preset_time_*,ub_preset_digit_*}`, `BKID_APP_select_playback_media`, `FUNC_copy_content`, `get_battery_status_for_copy`, `BKID_APP_setting_viewing_{interval,repeat}`, `FUNC_start_playback_slide_show`, `STATUS_OF_MEDIA_SLOT1_{READ_ONLY,LOCKED,UNWRITABLE}` |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `7,475` 条 `0x1e1c` 记录（首条 `0x5eb4`）：`Switch V/H AF Area` (`0x73ae`), `AF Point Only` (`0x615a`), `AF Point + AF Area` (`0x69e8`), `Focus Area Limit` (`0x6de2`), `Focus Area Color` (`0x74ad`), `Exposure Std. Adjust` (`0x6114`), 5 测光图标前缀 (`0x605e/0x63a4/0x6974/0x7606/0x77d3`), `Bracket Settings` (`0x6466`), `Selftimer during Bracket` (`0x6ef5`), `Bracket order` (`0x76b1`), `TC/UB Disp. Setting` (`0x6b0c`), `User Bit Preset` (`0x7af2`), `User Bit Time Rec` (`0x7aa8`), `Time Code Format` (`0x6e3d`), `Select Playback Media` (`0x6bcd`), `Copy` (`0x79fc`), `Repeat` (`0x685f`) |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | 首条 `0x5b60`，与 `EN` `7,475` 条 `resid16` (`0x6000..0x7d3d`) 1:1 严格对齐 |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | 首条 `0x5b88`，与 `EN` `7,475` 条 `resid16` (`0x6000..0x7d3d`) 1:1 严格对齐 |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | 首条 `0x62a4`，与 `EN` `7,475` 条 `resid16` (`0x6000..0x7d3d`) 1:1 严格对齐 |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `2,692` 槽位：`Selectable AF areas are limited to 1...` (`0xea28`), `White` (`0xe883`), `Red` (`0xe8c6`), `This function adjusts the standard...` (`0xe567`), `0→-→+` (`0xe1d3`), `-→0→+` (`0xe1d4`), `TC/UB display switching is invalid...` (`0xe728`), `Cannot copy.` (`0xe366`), `Copy failed.` (`0xe6db`), 卡速限制 (`0xe80e`/`0xe8ca`), `Slide Show` (`0xe2cc`), `Interval` (`0xe2cd`), `1/3/5/10/30 Sec` (`0xe2ce..0xe2d0`, `0xe4be..0xe4c3`) |
| `FX3 string_simplifiedchinese.uxc` | `149,064` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese.uxc` | `151,908` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_japanese.uxc` | `208,564` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `1,390` 槽位：`Slot 1` (`0x608f`), `Slot 2` (`0x6090`), `TC/UB` (`0x6389`), `Reset the user bit?` (`0x6441`) |
| `FX3 string_simplifiedchinese_g.uxc` | `61,296` | `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese_g.uxc` | `61,372` | `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_japanese_g.uxc` | `89,428` | `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 双 `BK4\x00` 数值 BKID 存储基线 |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_SETTING_{TC_FORMAT,TC_UB_DISP_SETTING,UB_TIME_REC,HDMI_TC_OUTPUT,USB_TC_IN_ALT_MODE_SETTING}`, `BKID_APP_EXT_TC_LOCK_STATUS`, `BKID_APP_USER_MENU_COPY_CLIP*`（休眠）；零 `exposure_standard` / `vertical_horizontal_focus_area_switch` / `focus_area_limit` |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `Timecode` (`0x2e81`), `Users Bit Mode` (`0x2f3a`), `TC Display Display Select` (`0x2f37`), `DURATION/TC/\nU-BIT` (`0x3284`), `Focus Area Ind.(AF-S)` (`0x2236`) |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `TC Format` (`0x456d`), `DF/NDF` (`0x48b1..0x48b4`), `Fix/Time` (`0x48b5..0x48b8`), `HDMI TC Out` (`0x4245`), `Focus Area Marker` (`0x4d6b`), `Copy Clip` (`0x4136` 休眠) |

### 5.2 4 语 `resid16` 关键菜单与选项矩阵（`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`）

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | 归属与语义说明 |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x73ae` | `Switch V/H AF Area` | `换垂直和水平AF区` | `換垂直/水平AF區` | `縦横ﾌｫｰｶｽｴﾘｱ切換` | Still `AF-C` 3 方向自动切换（默认 `Off` `_f` `0x63aa`） |
| `_f` `0x615a` | `AF Point Only` | `仅AF点` | `僅對焦點` | `ﾌｫｰｶｽ位置のみ` | 仅按方向切换对焦点坐标 |
| `_f` `0x69e8` | `AF Point + AF Area` | `AF点 + AF区域` | `對焦點 + 對焦區域` | `ﾌｫｰｶｽ位置+ﾌｫｰｶｽｴﾘｱ` | 同时按方向切换对焦区域与对焦点坐标 |
| `_f` `0x6de2` | `Focus Area Limit` | `对焦区域限制` | `對焦區域限制` | `ﾌｫｰｶｽｴﾘｱ限定` | 14 项复选框裁剪可选对焦区域（`0xea28` 至少 2 项下限） |
| `_f` `0x74ad` | `\ue662Focus Area Color` | `\ue662对焦边框颜色` | `\ue662對焦框色` | `\ue662ﾌｫｰｶｽｴﾘｱ枠色` | `White` (`.uxc` `0xe883` 默认) / `Red` (`.uxc` `0xe8c6`) |
| `_f` `0x6114` | `Exposure Std. Adjust` | `曝光标准调整` | `曝光標準調整` | `露出基準調整` | 5 测光模式 `±1 EV @ 1/6 EV` 校准（`Initialize`-only 重置） |
| `_f` `0x6d79` | `\ue59fMulti` | `\ue59f多重` | `\ue59f多重` | `\ue59fﾏﾙﾁ` | 5 测光模式之一（`0x7606` `Exposure Std. Adj.\ue59f`） |
| `_f` `0x6da8` | `\ue2b3Center` | `\ue2b3中心` | `\ue2b3中心` | `\ue2b3中央重点` | 5 测光模式之一（`0x77d3` `Exposure Std. Adj.\ue2b3`） |
| `_f` `0x7a8a` | `\ue2b4Spot` | `\ue2b4点测光` | `\ue2b4定點測光` | `\ue2b4スポット` | 5 测光模式之一（`0x63a4` `Exposure Std. Adj.\ue2b4`） |
| `_f` `0x6f15` | `\ue597Entire Screen Average` | `\ue597整个屏幕平均` | `\ue597全螢幕平均` | `\ue597画面全体平均` | 5 测光模式之一（`0x605e` `Exposure Std. Adj.\ue597`） |
| `_f` `0x7600` | `\ue596Highlight` | `\ue596强光` | `\ue596醒目` | `\ue596ハイライト重点` | 5 测光模式之一（`0x6974` `Exposure Std. Adj.\ue596`） |
| `.uxc` `0xe567` | `This function adjusts the standard of\noptimum exposure.\nGenerally, adjustment is not necessary.\nAdjust?` | `此功能调节最佳曝光标准。\n通常，不需要调节。\n是否调节？` | `此功能調整最佳曝光標準。\n通常，不需要調整。\n調整？` | `適正露出の基準を調整する機能です\n通常は調整をおこなう必要はありません\n調整しますか？` | `[Exposure Std. Adjust]` 入口警示确认对话框 |
| `_f` `0x6466` | `Bracket Settings` | `阶段曝光设置` | `包圍式曝光設定` | `ブラケット設定` | Still 包围曝光设置入口（`Drive Mode` 子菜单） |
| `_f` `0x6ef5` | `Selftimer during Bracket` | `阶段曝光中自拍定时` | `包圍曝光時自拍定時` | `ﾌﾞﾗｹｯﾄ時のｾﾙﾌﾀｲﾏｰ` | `Off` / `2 Sec` (`0xe207`) / `5 Sec` (`0xe208`) / `10 Sec` (`0xe209`) |
| `_f` `0x76b1` | `Bracket order` | `阶段曝光顺序` | `階段順序` | `ブラケット順序` | `0→-→+` (`.uxc` `0xe1d3` 默认) / `-→0→+` (`.uxc` `0xe1d4`) |
| `_f` `0x6b0c` | `TC/UB Disp. Setting` | `TC/UB显示设置` | `TC/UB顯示設定` | `TC/UB表示設定` | `Counter` (`0x6c01`) / `TC` (默认) / `U-Bit` (`0x71ca`) |
| `_f` `0x7af2` | `User Bit Preset` | `User Bit Preset` | `User Bit Preset` | `User Bit Preset` | 8 位十六进制 User Bit 预设（默认 `00 00 00 00`） |
| `_f` `0x7aa8` | `User Bit Time Rec` | `User Bit Time Rec` | `User Bit Time Rec` | `User Bit Time Rec` | `On` / `Off`（默认）；开启后以当前时间写入 User Bit |
| `_f` `0x6e3d` | `Time Code Format` | `Time Code Format` | `Time Code Format` | `Time Code Format` | `DF` (`0x6d59` 默认) / `NDF` (`0x6c6f`)；仅 NTSC，24p/23.98p 锁 NDF |
| `_f` `0x6bcd` | `Select Playback Media` | `选择播放媒体` | `選擇播放插槽` | `再生メディア選択` | `Slot 1` (`_g` `0x608f` 默认) / `Slot 2` (`_g` `0x6090`) |
| `_f` `0x79fc` | `Copy` | `复制` | `複製` | `コピー` | 从当前 `[Select Playback Media]` 复制到对侧卡（`Slot 2 -> Slot 1` 需 Tier-0 `EROFS`/`EBUSY` 拦截） |
| `.uxc` `0xe2cc` | `Slide Show` | `幻灯片播放` | `循環播放` | `スライドショー` | `Repeat` (`_f` `0x685f`: `On/Off`) + `Interval` (`.uxc` `0xe2cd`: `1/3/5/10/30 Sec`) |
