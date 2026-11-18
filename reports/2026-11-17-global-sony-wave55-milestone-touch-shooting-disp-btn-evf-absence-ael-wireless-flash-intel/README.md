# 全球 Sony 实机情报 Wave 55（55th Wave Milestone：`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Touch Func. in Shooting]` 与 EVF/Touch-Pad 硬件缺失、`[DISP (Screen Disp) Set]` 监视器模式与休眠取景器键、`[AEL w/ Shutter]` / `[Exp.comp.set]` / `[Wireless Flash]` / `[External Flash Set.]`，以及 `[Cont. Play for Interval]` / `[Photo Capture]` / 休眠 `[Beauty Effect]` 与 Slot-1 Tier-0 保险库防线）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Touch Operation*、*Touch Sensitivity*、*Touch Func. in Shooting*、*Swipe Up*、*Touch operations on the monitor*、*Focusing using touch operations (Touch Focus)*、*DISP (Screen Disp) Set*、*Using the DISP (Display Setting) button*、*Display Option*、*AEL w/ Shutter*、*Exp.comp.set*、*Wireless Flash*、*External Flash Set.*、*Cont. Play for Interval*、*Play Speed for Interval*、*Rotate*、*Photo Capture*、*JPEG/HEIF Switch (Photo Capture)*、*List of default setting values*），Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0），以及严格 `os.O_RDONLY` 本地 donor 二进制/字符串包交叉实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so`、`FX6 string_english.uxc` / `_2.uxc`）。
- **硬件安全态势**：严格只读本地 donor 分析（`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`、ELF 符号与官方文档条款）与 **`推断`**。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[Touch Func. in Shooting]` / `[Touch Sensitivity]` / `[Swipe Up]` vs 休眠 `[Touch Panel/Pad]` / `[Touch Shutter]` / `[Touch AE]` / `[Footer Icon Touch]`）**：
   - **实测事实（关键纠偏）**：`ILME-FX3 Ver. 7.02`（`ilc/2210`）在 `MENU -> (Setup) -> [Touch Operation]` 下仅暴露 4 个有效子项：**`[Touch Operation]`**（`On` 默认 / `On: Playback Only` / `Off`）、**`[Touch Sensitivity]`**（`Standard` 默认 / **`Sensitive`** —— 注：非 `Responsive`）、**`[Touch Func. in Shooting]`**（`Touch Focus` / **`Touch Tracking`** 默认 / `Off`）与 **`[Swipe Up]`**（**`Open the Fn Menu`** 默认 / `Off`）；**全部 4 项均不支持 `[Camera Settings Reset]`**（需 `[Initialize]`）。
   - **实测事实（`Touch Shutter` / `Touch AE` / `Touch Pad` / `Footer Icon Touch` 全线缺失）**：在 `Still`、`Movie` 与 `S&Q Motion` 三种模式下，`ILME-FX3` 的 `[Touch Func. in Shooting]` 均仅提供 **`Touch Focus` / `Touch Tracking` / `Off`**——**`[Touch Shutter]` 与 `[Touch AE]` 在 FX3 上完全不存在**（`ilc/2210` 零命中），且因 FX3 **无电子取景器（EVF）**，来自 `ILCE-7SM3` 的 **`[Touch Panel/Pad]` / `[Touch Pad Settings]`** 同样被彻底屏蔽；`[Footer Icon Touch]`（`_f` `0x70da`）亦为面向 `ILCE-7RM5`/`6700`/`ZV-E1` 的**休眠共享字符**（FX3 实机仅保留 `[Swipe Up]` 与 Ver. 2.00+ 屏幕触摸功能图标/`STBY/REC` 触控）。对比之下，`ILME-FX6 Ver. 6.01` 通过 `Technical > Touch Operation`（`On/Off`）与 `Shooting > Focus > Touch Function in MF`（`Spot Focus / Tracking AF`）在可拆卸触摸取景器上实现触控对焦与实时追踪，无灵敏度调节及 `Swipe Up`。
2. **子系统 2（`[DISP (Screen Disp) Set]` 监视器复选框与 `ILME-FX3` 零 EVF / 零 `Select Finder/Monitor` 实证）**：
   - **实测事实（路径与模式纠偏）**：`[DISP (Screen Disp) Set]` 位于 **`MENU -> (Setup) -> [Operation Customize] -> [DISP (Screen Disp) Set]`**（非 `Display Option` 子菜单！默认 `―`，不支持 `[Camera Settings Reset]`）。在拍摄模式下仅暴露 **`4` 个勾选页面**：**`Display All Info.`**、**`No Disp. Info.`**、**`Histogram`** 与 **`Level`**；回放（及 Auto Review）`DISP` 键仅循环 **`3` 个页面**：`Display Info.` -> `Histogram` -> `No Disp. Info.`。
   - **实测事实（零 EVF 与休眠键位证伪）**：**`ILME-FX3` 无电子取景器、无眼部传感器、无 `FINDER/MONITOR` 按键**，`ilc/2210` 中 **`Select Finder/Monitor`**、**`For viewfinder`** 与 **`Graphic Display`** 全部为 **0 命中**。`FX3 appFw.so` 与 `.uxc` 中的 `BKID_APP_setting_finder_monitor`、`BKID_APP_disp_mode_shoot_finder`、`BKID_APP_valid_disp_mode_shoot_monitor_for_viewfinder`、`DISP Button:Finder`（`_f` `0x6b57`）、`Select Finder/Monitor`（`_f` `0x74f9`）及 `Graphic Display`（`base` `0xe07a`）全部属于继承自 `ILCE-7SM3`/Alpha 家族的**门控休眠符号**。对比之下，`ILME-FX6` 虽同样无内置 EVF（`TYPE_BUILTIN_EVF_NOT_EXIST`），但标配**可拆卸 3.5" 触摸 LCD + 卡扣式 `Viewfinder Hood`**（说明书 `5-024-458-18` 称为 `Viewfinder` / `Viewfinder Hood`，无 `"Loupe"` 一词），并采用 `Monitoring > Display On/Off` 单项开关与 `Home Screen Priority` / `Direct Menu Priority` 双视图架构。
3. **子系统 3（Still `[AEL w/ Shutter]` 与闪光灯子菜单 `[Exp.comp.set]` / `[Wireless Flash]` / `[External Flash Set.]`）**：
   - **实测事实**：4 项全部**仅限静态照片（Still-only）**，在 `Movie` / `S&Q` 下不可用：
     - **`[AEL w/ Shutter]`**（`Exposure/Color -> [Metering]`）：`Auto`（默认，Not available reset）/ `On` / `Off`；`[AEL toggle]` 自定义键优先于半按快门。
     - **`[Exp.comp.set]`**（`Exposure/Color -> [Flash]`，注意在 `[Flash]` 子菜单下而非 `[Exposure Comp.]`）：**`Ambient&flash`**（默认，Not available reset，曝光补偿同时影响环境光与闪光输出）vs **`Ambient only`**（仅偏移背景环境光、锁定 TTL 闪光输出）。
     - **`[Wireless Flash]`**（`Exposure/Color -> [Flash]`）：`Off`（默认）/ `On`（光学或无线电离机引闪，支持 `[Wireless Test Flash]` 自定义键）；**唯一支持 `[Camera Settings Reset]`（`Can be reset`）**。
     - **`[External Flash Set.]`**（`Exposure/Color -> [Flash]`）：`[Ext. Flash Firing Set.]` 与 `[Ext. Flash Cust. Set.]`（Not available reset），仅支持**直接安装于 MI 热靴**的 Sony 闪光灯或无线引闪器（不支持连线离机或通过相机菜单复位闪光灯）。
   - **实测事实**：纯电影机 `ILME-FX6` **无机械快门、无静态闪光曝光系统**，以上 4 项在 `FX6` 全菜单与 `5-024-458-18` 中彻底缺失（`FX6 appFw.so` 仅存零 `BKID_APP_*` 的休眠 Alpha C++ 类；FX6 唯一的闪光相关菜单为抑制卷帘快门半帧闪光条纹的 **`Flash Band Reduce`**）。
4. **子系统 4（回放 `[Cont. Play for Interval]` / `[Play Speed for Interval]` 9 档刻度、有效 `[Edit]` 项 vs 休眠 `[Beauty Effect]`/`[Trimming]` 陷阱，及 `Slot-1` Tier-0 保险库护栏）**：
   - **实测事实（命名与刻度消歧）**：`ILME-FX3` 官方 `ilc/2210` 在 **`MENU -> (Playback) -> [Viewing]`**（非 `Playback Option`）下暴露 **`[Cont. Play for Interval]`**（`_f` `0x78fa`）与 **`[Play Speed for Interval]`**（`_f` `0x639e`），同时 `_f.uxc` 保留旧式缩写 **`Cont. PB for Interval`**（`0x72e6`）与 **`PB Speed for Interval`**（`0x72bd`）；`FX3 appFw.so` 实证其速率枚举为 **`1..9` 级**（`CONTINUOUS_PLAYBACK_SPEED_1..9`，**默认 `5`**，并非 `1..5`），且可于播放中用前后拨轮/控制拨轮实时调速。
   - **实测事实（`[Edit]` 实机清单 vs 休眠陷阱）**：`MENU -> (Playback) -> [Edit]` 在 FX3 上仅激活 **`[Rotate]`**、**`[Photo Capture]`**、**`[JPEG/HEIF Switch]`**（`JPEG` 默认 / `HEIF(4:2:0)` / `HEIF(4:2:2)`）与 **`[Copy]`**；而 `_f` `0x7849` **`[Beauty Effect]`**（美颜另存）与 `appFw.so` 中的 `sequence_edit_trimming_*`（裁剪另存）均为**未接入 FX3 实机菜单的休眠 Alpha 编辑陷阱**（`ilc/2210` 零命中）。
   - **推断（`Slot-1` Tier-0 保险库写危害护栏）**：`[Cont. Play for Interval]` 与 `[Play Speed for Interval]` 属只读视图操作；但 **`[Rotate]`、`[Photo Capture]`**（从视频截帧并向当前 `[Select Playback Media]` 槽位写入新静态文件）及休眠 **`[Beauty Effect]`/`[Trimming]`** 均会直接写盘并改写 `AVF_INFO`。在 `Slot 1`（默认回放目标）挂载只读 Tier-0 恢复保险库时，任何指向 `Slot 1` 的回放编辑写分发**必须 fail-closed 拦截并返回 `EROFS` / `EOPNOTSUPP`**（`slot1_data_sector_writes == 0` 且 `slot1_avf_info_mutated == False`）。

---

## 1. 子系统 1：`[Touch Func. in Shooting]`、`[Touch Sensitivity]` 与休眠 `[Touch Panel/Pad]` / `[Footer Icon Touch]`

### 1.1 `ILME-FX3 Ver. 7.02` `[Touch Operation]` 完整菜单树与功能消歧（`实测事实`）

- **菜单路径**（`ilc/2210/v1/en/`）：`MENU` -> `(Setup)` -> **`[Touch Operation]`**（`_g.uxc` `0x6345`, `base.uxc` `0xe8e3`）。

| 菜单项 | `FX3` 实机可选值 | 出厂默认值 | `[Camera Settings Reset]` | 适用模式 | `FX3 appFw.so` BKID / 约束（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **`[Touch Operation]`** | **`On`** / `On: Playback Only` (`_f` `0x6cde`) / `Off` | **`On`** | **Not available** *(需 `[Initialize]`)* | Still / Movie / `S&Q` / Playback | `BKID_APP_setting_touch_operation`, `TOUCH_OPERATION_{ON,ON_PLAYBACK_ONLY,OFF}` |
| **`[Touch Sensitivity]`** (`_f` `0x739f`) | **`Standard`** / **`Sensitive`** (`_f` `0x7205`) | **`Standard`** | **Not available** | 全局触控屏 | `BKID_APP_setting_touch_sensitivity`, `TOUCH_SENSITIVITY_{STANDARD,SENSITIVE}` *(非 `Responsive`)* |
| **`[Touch Func. in Shooting]`** (`_f` `0x7575`) | **`Touch Focus`** (`_f` `0x6e79`/`0x7427`) / **`Touch Tracking`** (`_f` `0x68f4`/`0x69ee`) / **`Off`** | **`Touch Tracking`** | **Not available** | **Still / Movie / `S&Q` 三模完全一致** | `BKID_APP_setting_shooting_touch_function`; **不含 `Touch Shutter` / `Touch AE`** |
| **`[Swipe Up]`** (`_f` `0x7518`) | **`Open the Fn Menu`** (`_f` `0x7281`) / `Off` | **`Open the Fn Menu`** | **Not available** | Still / Movie / `S&Q` 待机 | `BKID_APP_setting_swipe_up`, `SWIPE_UP_{FN_MENU,OFF}`; 仅 `[Touch Operation] = On` 有效 |

- **三项核心纠偏与休眠 Alpha 符号证伪（`实测事实`）**：
  1. **`Touch Shutter` 与 `Touch AE` 在 `ILME-FX3` 全模式均不存在**：尽管 `FX3 appFw.so` 与 `.uxc` 包含共享 BIONZ XR 代码产出的 `VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_SHUTTER`、`FUNC_touch_shutter_yuv_seq`、`PID_SET_TOUCH_SPOT_METER`、`_f` `0x6a80`/`0x62d5`（`Touch Shutter`）、`_f` `0x702a`（`Touch AE`）、`_f` `0x797e`（`Touch Focus+AE`）及 `_g` `0x6150`（`Touch AE Cancel`），但 **`ilc/2210` 官方文档中 `[Touch Func. in Shooting]` 在 Still、Movie 与 `S&Q` 三种模式下均严格仅暴露 `Touch Focus` / `Touch Tracking` / `Off`**，并不存在 `Touch Shutter` 或 `Touch AE`。
  2. **`[Touch Panel/Pad]` 彻底缺席（EVF 缺失耦合）**：`FX3 appFw.so` 继承自带 EVF 机型的 `BKID_APP_setting_touch_panel_pad`（`TOUCH_PANEL_PAD_{TOUCH_PANEL_ONLY,TOUCH_PAD_ONLY,TOUCH_PANEL_PAD}`）及 `BKID_APP_setting_touch_pad_{operation_area,operation_type,vertical}`（对应 `_f` `0x76ec` `Touch Panel/Pad`、`0x6d1a` `Touch Pad Only`、`0x7312` `Touch Pad (vertical)`、`0x7307`），但因 `ILME-FX3` **无电子取景器（EVF）**，整组触摸板菜单在实机 UI 被门控隐藏（仅 `ilc/2210` *Touch Sensitivity* 的手套注意事项保留一句泛用术语 `"touch panel/pad"`）。
  3. **`[Footer Icon Touch]` 为休眠字符 vs FX3 触摸图标交互**：`_f` `0x70da`（`Footer Icon Touch` / `0x77a9` / `0x78ff`）及 `[Swipe Left]` / `[Swipe Right]`（`_f` `0x6b06` / `0x6c19`）在 `ilc/2210` 中为 **0 命中**（系 `ILCE-7RM5` / `ILCE-6700` / `ZV-E1` 等 `[Touch Panel Settings] -> [Shooting Screen]` 菜单条目）。在 `ILME-FX3`（`Ver. 2.00+` 至 `Ver. 7.02`）中，屏幕支持直接点击触控功能图标切换 `Touch Focus / Touch Tracking / Off`、`STBY/REC` 录制触控（`BKID_APP_setting_stby_rec_touch_button` / `_f` `0x6dd7`）、长按 Fn 图标进入 `[Fn Menu Settings]`，以及通过 `[Swipe Up]` 快速上滑呼出 Fn 菜单（回放支持左右滑动翻页、双指捏合/双击放大、点击暂停/播放视频）。

### 1.2 `ILME-FX6 Ver. 6.01` 触摸交互架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`, `5-024-458-18`) |
| :--- | :--- | :--- |
| **触控开关与路径** | `(Setup) -> [Touch Operation]`（`On` / `On: Playback Only` / `Off`） | **`Technical > Touch Operation`**（`On` / `Off`，`BKID_APP_SETTING_TOUCH_OPERATION`，`FX6 base` `0x23ab`） |
| **拍摄触控模式** | `[Touch Func. in Shooting]`：`Touch Focus` / `Touch Tracking` / `Off`（Still/Movie/`S&Q`） | AF/Push AF 下点击可启动 **`Realtime Tracking AF`**（`BKID_APP_TOUCH_TRACKING_STATE`）；MF/Push MF 下由 **`Shooting > Focus > Touch Function in MF`**（`Spot Focus` / `Tracking AF`，`FX6 base` `0x254e`）决定；分配 `Focus Setting` 键后可点击/拖拽移动橙色对焦框 |
| **灵敏度与手势** | `[Touch Sensitivity]`（`Standard / Sensitive`）、`[Swipe Up]`（`Open the Fn Menu / Off`） | **无** `Touch Sensitivity`、**无** `Swipe Up`、**无** `Touch Shutter` / `Touch AE` |

---

## 2. 子系统 2：`[DISP (Screen Disp) Set]` 与 `ILME-FX3` 零 EVF / 零 `Select Finder/Monitor` 硬件实证

### 2.1 `[DISP (Screen Disp) Set]` 精确路径、拍摄/回放页面集合与休眠词条（`实测事实`）

- **菜单路径**（`ilc/2210`）：`MENU` -> `(Setup)` -> **`[Operation Customize]`** -> **`[DISP (Screen Disp) Set]`**（`_g.uxc` `0x61c4` -> `_g.uxc` `0x61da`；默认 **`―`**，不支持 `[Camera Settings Reset]`）。

| 场景 | `ILME-FX3 Ver. 7.02` 实机可选页面 | `FX3` 底层键 / UXC `resid16`（`实测事实`） | 是否存在于 `ilc/2210` |
| :--- | :--- | :--- | :---: |
| **拍摄模式（Still / Movie / `S&Q`）** | 1. **`Display All Info.`**<br>2. **`No Disp. Info.`**<br>3. **`Histogram`**<br>4. **`Level`** *(前后+左右双轴水平仪，水平时变绿)* | `BKID_APP_disp_mode_shoot_monitor`<br>`BKID_APP_valid_disp_mode_shoot_monitor_{all_info,no_info,histogram,level}`<br>`base` `0xea0e` / `0xe9f9` / `0xe07b` / `0xe8bc` | **YES** *(仅此 4 项)* |
| **回放 / Auto Review** | 1. **`Display Info.`**<br>2. **`Histogram`** *(含高光/暗部闪烁警告)*<br>3. **`No Disp. Info.`** | `BKID_APP_disp_mode_play`<br>`VAL_disp_mode_play_DISP_MODE_PLAY_{INFO_ON,HISTOGRAM,INFO_OFF}`<br>`FUNC_set_next_disp_mode_play` | **YES** *(仅此 3 项)* |
| **Alpha 休眠屏幕项（FX3 未启用）** | `Graphic Display`、`For viewfinder`、`Monitor Off` | `base` `0xe07a` (`Graphic Display`)、`_f` `0x62d3` & `base` `0xe2e5` (`For viewfinder`)、`BKID_APP_valid_disp_mode_shoot_monitor_{for_viewfinder,monitor_off}` | **NO** *(0 命中)* |

### 2.2 硬件实证：`ILME-FX3` 零电子取景器（EVF）vs `ILME-FX6` 可拆卸触摸屏/取景遮光罩

- **`ILME-FX3` 零 EVF 与 `FINDER/MONITOR` 门控实证（`实测事实`）**：
  1. `ILME-FX3` 机身顶部配备可拆卸 XLR 手柄接口热靴与 3.0 英寸侧翻触摸 LCD（`7.5 cm TFT`），**机身无任何内置电子取景器（EVF）、无眼部接近传感器、无物理 `FINDER/MONITOR` 按键**。
  2. 在 `ilc/2210` 官方手册中，**`Select Finder/Monitor`**、**`Finder/Monitor Sel.`** 与 **`For viewfinder`** 均为 **0 命中**。
  3. 然而因 `FX3 appFw.so` 与 `ILCE-7SM3` 同源，`appFw.so` 与 UXC 仍残留完整 EVF 符号群：`BKID_APP_setting_finder_monitor`、`VAL_setting_finder_monitor_FINDER_MONITOR_{AUTO,FINDER,LCD,MANUAL,MONITOR,VIEW_FINDER}`、`FUNC_toggle_set_finder_monitor_sel_seq`、`BKID_APP_disp_mode_shoot_finder`、`BKID_APP_valid_disp_mode_shoot_finder_{all_info,no_info,histogram,level}`、`FUNC_disp_button_finder_seq`、`BKID_APP_extern_disp_layoutmode_rec_evf`、`_f` `0x674a` (`DISP Button:Monitor`)、`_f` `0x6b57` (`DISP Button:Finder`)、`_f` `0x74f9` (`Select Finder/Monitor`)、`_f` `0x6daf`/`0x754a` (`Finder/Monitor Sel.`)、`base` `0xe664` (`FINDER/MONITOR`)、`_g` `0x63fc` (`Finder/Monitor`)。模拟器与安全护栏若错误激活这些休眠符号，将在无 EVF 的 FX3 上造成“切屏黑屏假死”陷阱。
- **`ILME-FX6 Ver. 6.01` 可拆卸 LCD 取景器架构对比（`实测事实`）**：
  - `ILME-FX6` 同样**无机身内置 EVF**（`FX6 appFw.so`: `VAL_FEATURE_MANAGER_builtin_evf_TYPE_BUILTIN_EVF_NOT_EXIST`），但随机附带一块 **3.5 英寸可拆卸触摸 `Viewfinder`（LCD Monitor）与卡扣式金属锁扣 `Viewfinder Hood`**（`5-024-458-18` 官方称呼为 `Viewfinder` 与 `Viewfinder Hood`，不用 `"Loupe"` 一词），可装于顶部手柄或机身多处 45° 夹具并支持 `MIRROR` 镜像翻转。
  - FX6 不使用 FX3 的 4 页 `DISP` 轮询表，而是通过 **`Monitoring > Display On/Off`** 逐项开关叠加信息，并通过 **`Technical > Menu Settings > Info. Disp. Mode Operation`** 在 `Home Screen Priority` 与 `Direct Menu Priority` 间切换；同时保留 `LCD Monitor Mode`、`VF Adjust`、`VF Focus Mag ×3/×6`、`LCD Monitor/VF Select`（外接/系统切换）等电影机专用显示菜单（`FX6 appFw.so` 亦残留休眠 Alpha `DISP_MODE_SHOOT_MONITOR_FOR_VIEWFINDER` 等枚举）。

---

## 3. 子系统 3：Still `[AEL w/ Shutter]` 与闪光灯子菜单 `[Exp.comp.set]` / `[Wireless Flash]` / `[External Flash Set.]`

### 3.1 `ILME-FX3 Ver. 7.02` 完整规格、路径与 Reset 策略分化（`实测事实`）

| 菜单项 | `ilc/2210` 精确路径 | 可选值 | 默认值 | `[Camera Settings Reset]` | 适用模式 | `FX3 appFw.so` Key & 运行语义（`实测事实`） |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- |
| **`[AEL w/ Shutter]`** (`_f` `0x669d`, `0x6bcc`) | `(Exposure/Color) -> [Metering] -> [AEL w/ Shutter]` | **`Auto`** / `On` / `Off` | **`Auto`** | **Not available** *(需 `[Initialize]`)* | **仅 Still** | `BKID_APP_setting_still_image_ael_w_shutter`; `Auto` 在 `AF-S` 下半按锁定曝光、在 `AF-A` 移动/连拍时解除；`Off` 在连拍期间持续重新测光；自定义键 `[AEL toggle]` 优先 |
| **`[Exp.comp.set]`** (`_f` `0x73c2`, `base` `0xe11a`) | `(Exposure/Color) -> **[Flash]** -> [Exp.comp.set]` *(注：位于 `[Flash]` 下)* | **`Ambient&flash`** (`_f` `0x6efe`) / **`Ambient only`** (`_f` `0x7617`) | **`Ambient&flash`** | **Not available** *(需 `[Initialize]`)* | **仅 Still** | `BKID_APP_setting_exp_comp_set` (`MR_` 同步支持); `Ambient&flash` 使 `[Exposure Comp.]` 同时偏移环境光与闪光输出；`Ambient only` 仅调节背景环境光亮度、保持闪光灯输出不变 (`base` `0xe1e9`/`0xe3e5`) |
| **`[Wireless Flash]`** (`_f` `0x6201`, `0x605b`) | `(Exposure/Color) -> [Flash] -> [Wireless Flash]` | `On` / **`Off`** | **`Off`** | **Can be reset** *(唯一可 Reset!)* | **仅 Still** | `BKID_APP_setting_wireless_flash`, `VAL_HAITA_setting_wireless_flash_exposure_mode_*_STILL`; 支持光通信（Controller）与无线电（Commander）引闪，可分配 `[Wireless Test Flash]` (`_f` `0x7567`) 至自定义键 |
| **`[External Flash Set.]`** (`_f` `0x6771`) | `(Exposure/Color) -> [Flash] -> [External Flash Set.]` | `[Ext. Flash Firing Set.]` (`_f` `0x671d`) / `[Ext. Flash Cust. Set.]` (`_f` `0x705f`) | **`―`** | **Not available** *(需 `[Initialize]`)* | **仅 Still** | `BKID_APP_external_flash_menu_*` + `45+` 条 `PID_SET_EXT_FLASH_*` 指令；**必须直接插在 MI 热靴上**（不支持同步线离机 `base` `0xe8c7`/`0xe53e`）；不支持从相机菜单对闪光灯执行配对/重置/初始化 |

### 3.2 `ILME-FX6 Ver. 6.01` 无闪光与无半按快门测光体系对比（`实测事实`）

- `ILME-FX6` 为纯电子快门电影机，**机身既无机械焦平面快门，亦无 MI 热靴 TTL 闪光同步电路及静态拍照模式**：
  - `FX6` 全菜单与 `5-024-458-18` 中**完全不存在** `[AEL w/ Shutter]`、`[Exp.comp.set]`、`[Wireless Flash]` 与 `[External Flash Set.]`；
  - `FX6 appFw.so` 仅保留少量无 `BKID_APP_*` 键的休眠 Alpha C++ 类型（`N5model22setting_exp_comp_set_tE`、`N5model24setting_wireless_flash_tE`、`N5model27launch_ext_flash_settings_tE`、`EXTERN_VAL_EV_SHIFT_AFFECT_AMBIENT*`）；
  - `FX6` 字符串包中唯一含 `"Flash"` 的实机功能为 **`Flash Band Reduce`**（`FX6 _2` `0x4215` / `0x5566` / `0x5614..0x5615`），用于消除现场他机闪光灯在 CMOS 卷帘快门下造成的上下半帧曝光割裂，与拍照闪光灯控制毫无关联。

---

## 4. 子系统 4：回放 `[Cont. Play for Interval]` / `[Play Speed for Interval]`、有效 `[Edit]` 项 vs 休眠陷阱与 Slot-1 Tier-0 防线

### 4.1 间隔连续回放命名消歧与 `1..9` 级速率实证（`实测事实`）

- **菜单路径**（`ilc/2210`）：`MENU` -> `(Playback)` -> **`[Viewing]`**（`_g` `0x6033`，注意**并非** `[Playback Option]` `_g` `0x6188`）。
- **命名演进与 UXC 双别名实证（`实测事实`）**：
  - 官方 `ilc/2210` 文档采用 **`[Cont. Play for Interval]`** 与 **`[Play Speed for Interval]`**（对应 `_f.uxc` `0x78fa` 与 `0x639e`）；
  - 同一 `_f.uxc` 文件内同时保留了早期 Alpha 缩写 **`Cont. PB for \ue5d1Interval`**（`0x72e6`）与 **`PB Speed for \ue5d1Interval`**（`0x72bd`），两套词条在简中/繁中/日文下翻译完全一致。
- **9 档精确速率刻度与默认中位值（`实测事实`）**：
  - `ilc/2210` *List of default setting values* 载明 `[Play Speed for Interval]` 默认值为 **`5`**，且 Playback 菜单项全部**不支持 `[Camera Settings Reset]`**（需 `[Initialize]`）；
  - `FX3 appFw.so` 实证其底层参数 `BKID_APP_setting_continuous_playback` 定义了精确的 **9 档枚举**：**`VAL_setting_continuous_playback_CONTINUOUS_PLAYBACK_SPEED_1 .. 9`**（配合 `increment_continuous_playback_speed` / `decrement_continuous_playback_speed`），`5` 恰好为 `1..9` 刻度中值（而非 `1..5`）；
  - 实机操作约束：支持间隔拍摄与连拍群组连续回放；单张查看时按方向下键可直接启动/暂停/恢复连续播放，播放中旋转前/后拨轮或控制拨轮可实时调速；**机内不可将间隔照片合成为视频**（须在 PC 端使用 *Imaging Edge Desktop (Viewer)*）。

### 4.2 回放 `[Edit]` 实机清单 vs 休眠 Alpha 编辑陷阱，及 `Slot-1` Tier-0 写危害防线

| 功能项 | `ILME-FX3` 状态 (`ilc/2210` + UXC + `appFw.so`) | `ILME-FX6` 状态 (`5-024-458-18`) | 对 `Slot 1` 的 I/O 影响 & Tier-0 护栏要求（`实测事实` + `推断`） |
| :--- | :--- | :--- | :--- |
| **`[Cont. Play for Interval]` / `[Play Speed for Interval]`** | **Active** (`Playback -> [Viewing]`, `Speed 1..9`, 默认 `5`) | **无此功能** | **纯只读回放浏览**（`safe_read_only`） |
| **`[Rotate]`** (`base` `0xe5ae`, `_f` `0x795a`) | **Active** (`Playback -> [Edit]`, `FUNC_rotate_content`, 逆时针旋转 90° 并持久化) | **无此功能** | **写入操作**（改写图像方向元数据/数据库）-> 目标为只读 `Slot 1` 时 **MUST fail-closed (`EROFS`)** |
| **`[Photo Capture]`** (`_f` `0x6856`) + **`[JPEG/HEIF Switch]`** (`_f` `0x6938`, `JPEG` / `HEIF(4:2:0)` / `HEIF(4:2:2)`) | **Active** (`Playback -> [Edit]`, `BKID_APP_setting_photo_capture_file_type`, 从视频提取暂停帧并保存为新静态照片) | **无此功能** *(仅存 `BKID=0` 休眠 `launch_photo_capture_t`)* | **高危写入操作**（在当前 `[Select Playback Media]` 槽位新建照片文件并更新 `AVF_INFO`）-> 当 `[Select Playback Media] = Slot 1`（默认值！）且 `Slot 1` 挂载 Tier-0 保险库时 **MUST fail-closed (`EROFS` / `EOPNOTSUPP`)** |
| **`[Copy]`** (`_f` `0x79fc`, `FUNC_copy_content`) | **Active** (`Playback -> [Edit]`, 从当前 `[Select Playback Media]` 复制到对侧槽位) | **无机内菜单** *(休眠 `Copy Clip`)* | `Slot 2 -> Slot 1` 方向写入 `Slot 1` -> **MUST fail-closed (`EROFS` / `EBUSY`)**（见 Wave 54） |
| **`[Beauty Effect]`** (`_f` `0x7849`) & **`[Trimming]`** | **Dormant Trap**（仅存于 `_f.uxc` `0x7849`/`0x6360` 与 `appFw.so` `API_START_BEAUTYEFFECT_DETECTION`、`sequence_edit_trimming_*`；`ilc/2210` 零命中） | **无此功能** | 若触发均会尝试**另存新文件** -> 在门控禁止启用的同时，对只读 `Slot 1` 叠加 fail-closed `EROFS` 兜底，保证 `slot1_data_sector_writes == 0` 且 `slot1_avf_info_mutated == False` |

---

## 5. `O_RDONLY` 本地 Donor 审计台账与 4 语 `resid16` 一致性矩阵（`raw_firmware_bytes_leaked = 0`）

### 5.1 本波次已审计本地 Donor 文件台账（严格 `os.O_RDONLY`）

| Donor 工件 | 大小 (`B`) | SHA-256 | Wave 55 实测命中符号 / 关键证据 (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_{touch_operation,touch_sensitivity,shooting_touch_function,swipe_up,stby_rec_touch_button,icon_touch_function}`, 休眠 `BKID_APP_setting_touch_panel_pad` / `touch_pad_*` / `TOUCH_SHUTTER`, `BKID_APP_disp_mode_shoot_monitor`, 休眠 `BKID_APP_setting_finder_monitor` / `disp_mode_shoot_finder`, `BKID_APP_setting_still_image_ael_w_shutter`, `BKID_APP_setting_exp_comp_set`, `BKID_APP_setting_wireless_flash`, `BKID_APP_external_flash_menu_*` + `45+` `PID_SET_EXT_FLASH_*`, `BKID_APP_setting_continuous_playback` (`SPEED_1..9`), `BKID_APP_setting_photo_capture_file_type` (`JPEG/HEIF_420/HEIF_422`), `FUNC_rotate_content`, 休眠 `API_START_BEAUTYEFFECT_DETECTION` & `sequence_edit_trimming_*` |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `Touch Func. in Shooting` (`0x7575`), `Touch Focus` (`0x6e79`/`0x7427`), `Touch Tracking` (`0x68f4`/`0x69ee`), `Touch Sensitivity` (`0x739f`), `Sensitive` (`0x7205`), `Swipe Up` (`0x7518`), `Open the Fn Menu` (`0x7281`), `On: Playback Only` (`0x6cde`), 休眠 `Touch Shutter`/`Touch AE`/`Touch Panel/Pad`/`Footer Icon Touch`/`For viewfinder`/`Finder/Monitor Sel.` (`0x6a80/0x702a/0x76ec/0x70da/0x62d3/0x74f9`), `AEL w/ Shutter` (`0x669d`), `Exp.comp.set` (`0x73c2`), `Ambient&flash` (`0x6efe`), `Ambient only` (`0x7617`), `Wireless Flash` (`0x6201`), `External Flash Set.` (`0x6771`), `Ext. Flash Firing/Cust. Set.` (`0x671d`/`0x705f`), `Cont. Play/PB for Interval` (`0x78fa`/`0x72e6`), `Play/PB Speed for Interval` (`0x639e`/`0x72bd`), `Photo Capture` (`0x6856`), `JPEG/HEIF Switch` (`0x6938`), `HEIF(4:2:0/4:2:2)` (`0x7959`/`0x6057`), `Beauty Effect` (`0x7849`, 休眠) |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | 首条 `0x5b60`，与 `EN` `7,475` 条 `resid16`（`0x6000..0x7d3d`）1:1 严格对齐 |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | 首条 `0x5b88`，与 `EN` `7,475` 条 `resid16`（`0x6000..0x7d3d`）1:1 严格对齐 |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | 首条 `0x62a4`，与 `EN` `7,475` 条 `resid16`（`0x6000..0x7d3d`）1:1 严格对齐 |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `Display All Info.` (`0xea0e`), `No Disp. Info.` (`0xe9f9`), `Histogram` (`0xe07b`), `Level` (`0xe8bc`), 休眠 `Graphic Display` (`0xe07a`), 休眠 `For viewfinder` (`0xe2e5`), 休眠 `FINDER/MONITOR` (`0xe664`), `Exp.comp.set` / `Ambient only` / `Ambient&flash` (`0xe11a..0xe11c`), `Rotate` (`0xe5ae`), 外闪错误提示 (`0xe53e`/`0xe8c7`) |
| `FX3 string_simplifiedchinese.uxc` | `149,064` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese.uxc` | `151,908` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_japanese.uxc` | `208,564` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `Touch Operation` (`0x6345`), `Operation Customize` (`0x61c4`), `DISP (Screen Disp) Set` (`0x61da`), `DISP Button` (`0x625d`), `Viewing` (`0x6033`), `Edit` (`0x6418`), `Playback Option` (`0x6188`), 休眠 `Touch AE Cancel` (`0x6150`) & `Finder/Monitor` (`0x63fc`) |
| `FX3 string_simplifiedchinese_g.uxc` | `61,296` | `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese_g.uxc` | `61,372` | `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_japanese_g.uxc` | `89,428` | `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 双 `BK4\x00` 偏移（`0xc` / `0xd200c`）数值 BKID 存储基线 |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_SETTING_TOUCH_OPERATION`, `BKID_APP_SETTING_TOUCH_FUNCTION_IN_MF`, `BKID_APP_TOUCH_TRACKING_STATE`, `VAL_FEATURE_MANAGER_builtin_evf_TYPE_BUILTIN_EVF_NOT_EXIST`, `BKID_APP_SETTING_INFO_DISP_MODE_OPERATION`; 零 `BKID_APP_*` 静态闪光与回放编辑键 |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `Touch Operation` (`0x23ab`), `Touch Function in MF` (`0x254e`), `LCD Monitor/VF Select` (`0x30e8`), `Home Screen Priority` (`0x2fde`), `Direct Menu Priority` (`0x2feb`) |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `Viewfinder` (`0x4d83`), `Display On/Off` (`0x4241`), `VF Display Setting` (`0x42bf`), `Flash Band Reduce` (`0x4215`/`0x5566`) |

### 5.2 4 语 `resid16` 关键菜单与选项矩阵（`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`）

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | 归属与实机激活状态 |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_g` `0x6345` | `Touch Operation` | `触摸操作` | `觸控操作` | `タッチ操作` | Active：`On` / `On: Playback Only` (`_f` `0x6cde`) / `Off` |
| `_f` `0x739f` | `Touch Sensitivity` | `触摸灵敏度` | `觸控靈敏度` | `タッチ感度` | Active：`Standard` / `Sensitive` (`_f` `0x7205`) |
| `_f` `0x7575` | `Touch Func. in Shooting` | `拍摄期间的触摸功能` | `拍攝期間的觸控功能` | `撮影時のタッチ機能` | Active：`Touch Focus` (`0x7427`) / `Touch Tracking` (`0x69ee`) / `Off` |
| `_f` `0x7518` | `Swipe Up` | `上划` | `向上滑動` | `上方向にスワイプ` | Active：`Open the Fn Menu` (`_f` `0x7281`) / `Off` |
| `_f` `0x6a80` | `Touch Shutter` | `触屏快门` | `觸控快門` | `タッチシャッター` | **Dormant**（`ilc/2210` 零命中，FX3 未启用） |
| `_f` `0x702a` | `Touch AE` | `触屏AE` | `觸控AE` | `タッチAE` | **Dormant**（`ilc/2210` 零命中，FX3 未启用） |
| `_f` `0x76ec` | `Touch Panel/Pad` | `触摸屏/触摸板` | `觸控面板/觸控板` | `ﾀｯﾁﾊﾟﾈﾙ/ﾀｯﾁﾊﾟｯﾄﾞ` | **Dormant**（EVF 缺失，`ilc/2210` 无此菜单） |
| `_f` `0x70da` | `Footer Icon Touch` | `页脚图标触摸` | `註腳圖示觸控` | `ﾌｯﾀｰｱｲｺﾝﾀｯﾁ` | **Dormant**（其他 Alpha 机型菜单，FX3 未启用） |
| `_g` `0x61c4` | `Operation Customize` | `操作自定义` | `操作客製化` | `操作カスタマイズ` | Active：`[DISP (Screen Disp) Set]` 父级分组 |
| `_g` `0x61da` | `DISP (Screen Disp) Set` | `DISP(画面显示)设置` | `DISP(畫面顯示)設定` | `DISP(画面表示)設定` | Active：`Display All Info.` / `No Disp. Info.` / `Histogram` / `Level` |
| `.uxc` `0xea0e` | `Display All Info.` | `显示全部信息` | `顯示所有資訊` | `全情報表示` | Active（拍摄 DISP 勾选页之一） |
| `.uxc` `0xe9f9` | `No Disp. Info.` | `无显示信息` | `不顯示資訊` | `情報表示 なし` | Active（拍摄/回放 DISP 页面之一） |
| `.uxc` `0xe07b` | `Histogram` | `柱状图` | `柱狀圖` | `ヒストグラム` | Active（拍摄/回放 DISP 页面之一） |
| `.uxc` `0xe8bc` | `Level` | `数字水平量规` | `水平` | `水準器` | Active（拍摄 DISP 勾选页之一，区别于 `_f` `0x7181` 等级） |
| `.uxc` `0xe07a` | `Graphic Display` | `图形显示` | `圖形顯示` | `グラフィック表示` | **Dormant**（`ilc/2210` 零命中，FX3 未启用） |
| `_f` `0x62d3` | `\ue381For viewfinder` | `\ue381取景器` | `\ue381適合觀景窗` | `\ue381ﾌｧｲﾝﾀﾞｰ撮影用` | **Dormant**（FX3 无 EVF） |
| `_f` `0x74f9` | `Select Finder/Monitor` | `选择取景器/显示屏` | `選擇觀景窗/螢幕` | `ﾌｧｲﾝﾀﾞｰ/ﾓﾆﾀｰ選択` | **Dormant**（FX3 无 EVF 与 `FINDER/MONITOR` 键） |
| `_f` `0x669d` | `AEL w/ Shutter` | `快门AEL` | `半按快門AEL` | `ｼｬｯﾀｰ半押しAEL` | Active（仅 Still：`Auto` / `On` / `Off`，不可 Reset） |
| `_f` `0x73c2` | `Exp.comp.set` | `曝光补偿设置` | `曝光補償設定` | `露出補正の影響` | Active（仅 Still：`Ambient&flash` / `Ambient only`，不可 Reset） |
| `_f` `0x6efe` | `Ambient&flash` | `环境光+闪光` | `現場光與閃光` | `定常光+ﾌﾗｯｼｭ` | Active 默认值（曝光补偿作用于背景+闪光） |
| `_f` `0x7617` | `Ambient only` | `仅环境光` | `只有現場光` | `定常光のみ` | Active（曝光补偿仅作用于背景环境光） |
| `_f` `0x6201` | `Wireless Flash` | `无线闪光灯` | `無線閃光燈` | `ワイヤレスフラッシュ` | Active（仅 Still：`Off` / `On`，**支持 Camera Settings Reset**） |
| `_f` `0x6771` | `External Flash Set.` | `外置闪光灯设置` | `外接閃光燈設定` | `外部フラッシュ設定` | Active（仅 Still MI 热靴直连，下含 `0x671d` Firing / `0x705f` Cust. Set.） |
| `_f` `0x78fa` | `Cont. Play for \ue5d1Interval` | `\ue5d1间隔连续播放` | `\ue5d1間隔的連續播放` | `\ue5d1ｲﾝﾀｰﾊﾞﾙ連続再生` | Active（`Playback -> [Viewing]`；`_f` `0x72e6` 为 `Cont. PB` 同义旧词条） |
| `_f` `0x639e` | `Play Speed for \ue5d1Interval` | `\ue5d1间隔播放速度` | `\ue5d1間隔的播放速度` | `\ue5d1ｲﾝﾀｰﾊﾞﾙ再生速度` | Active（`1..9` 档，默认 `5`；`_f` `0x72bd` 为 `PB Speed` 同义旧词条） |
| `_f` `0x6856` | `Photo Capture` | `照片捕获` | `照片攝取` | `動画から静止画作成` | Active（`Playback -> [Edit]`，写入新静态图至当前回放槽位） |
| `_f` `0x6938` | `\ue61cJPEG/HEIF Switch` | `\ue61cJPEG/HEIF切换` | `\ue61cJPEG/HEIF切換` | `\ue61cJPEG/HEIF切換` | Active（`Photo Capture` 输出：`JPEG` / `HEIF(4:2:0)` `0x7959` / `HEIF(4:2:2)` `0x6057`） |
| `.uxc` `0xe5ae` | `Rotate` | `旋转` | `轉動` | `回転` | Active（`Playback -> [Edit]`，逆时针 90° 旋转并持久化） |
| `_f` `0x7849` | `Beauty Effect` | `美化效果` | `美容效果` | `ﾋﾞｭｰﾃｨｰｴﾌｪｸﾄ` | **Dormant**（`ilc/2210` 零命中，FX3 未启用） |
