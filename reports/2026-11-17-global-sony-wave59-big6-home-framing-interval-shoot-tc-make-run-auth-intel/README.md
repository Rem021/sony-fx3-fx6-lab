# 全球 Sony 实机情报 Wave 59（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：Ver. 7.00/7.02 `[BIG6]` Home 主屏幕与 `[Framing Settings]` / 休眠 `[Auto Framing]`、`[Interval Shoot Func.]` 静态延时连拍 vs FX6 `[Interval Rec]`、`[Time Code Make/Run]` 与 `[HDMI Output Settings]` `[REC Control]`，以及 `[Access Authen.]` SSH/TLS 架构与 `[Fan Control]` / `[Auto Power OFF Temp.]`）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Home screen (BIG6)*、*Mode Settings (Fixed/Variable)*、*Home (Lower Left)*、*Swipe Down*、*Framing Settings*、*Auto Framing (unsupported notice)*、*Interval Shoot Func.*、*Display as Group / PB Speed for Interval*、*Time Code Make / Time Code Run*、*Matching time code (VMC-BNCM1)*、*HDMI Output Settings (Rec. Media dur HDMI Output / Time Code Output / REC Control / 4ch Audio Output)*、*Access Authen. Settings / Access Authen. Info*、*Import Root Certificate*、*Fan Control*、*Auto Power OFF Temp.*、*Recording time*、*Camera Settings Reset / Initialize / Reset Network Set.*），Sony `ILME-FX3` Ver. 6.00 / Ver. 7.00 / Ver. 7.02 固件更新说明，Sony *Monitor & Control* Help Guide，Sony *Camera Remote SDK* 协议文档，Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *Home Screen p. 15*、*Interval Rec pp. 55–56*、*Timecode Mode/Run & SDI/HDMI Rec Control pp. 100, 108*、*Technical > Fan Control*）及 Ver. 6.00–6.02 发行说明；并对照严格 `os.O_RDONLY` 本地 donor 实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so` 与 `FX6 string_english.uxc` / `_2.uxc`）。
- **硬件安全态势**：严格只读本地 donor 分析（`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*` 符号、SHA-256 账本与官方文档条目）与 **`推断`**（含 Tier-0 只读保险库与 Stage-B 护栏设计）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（Ver. 7.00/7.02 `[BIG6]` Home 屏幕与 `[Framing Settings]` vs 休眠 `[Auto Framing]`）**：
   - **实测事实（FX3 Ver. 7.00+ `[BIG6]` Home 屏幕前置条件、6 格矩阵与控制边界）**：FX3 自 **Ver. 7.00**（延续至 `Ver. 7.02`）新增电影机风格 **`HOME` (`BIG6`) 主屏幕**，但其启用有硬前置条件：必须在 `MENU -> (Shooting) -> [Shooting Mode] -> [Mode Settings]` 设为 **`[Fixed/Variable]`**（`_f` `0x7d0d` / `0x7d19`, `BKID_APP_setting_fps_fixed_variable_select`）。入口支持两种方式：① 绑定自定义键 **`[HOME]`**（`_f` `0x7cad` / `0x7cb1 Open Home Screen` / `0x7cf1`）；② 在开启 `[Touch Operation]` 后**屏幕向下滑动**（`_f` `0x7cdd`, `_g` `0x6526`, `VAL_setting_swipe_down_SWIPE_DOWN_HOME_SCREEN`），按 `MENU` 或 `Fn` 退出并恢复实时取景。6 格参数在实机 `FX3 appFw.so`（`26view_tp_button_01_for_big6`、`update_big6_item_iso_ei`、`BKID_APP_home_screen_state`）中呈精确动态映射：**FPS**（`Fixed/Variable`）、**ISO / Base ISO / EI**（`Log Shooting = Off` 或 `Flexible ISO` 下显示 `ISO`；`Cine EI` / `Cine EI Quick` 下显示 `Base ISO` 与 `EI`）、**Shutter Speed / Shutter Angle**（受 `Shutter Mode` 切换）、**Aperture（默认）或 ND Filter**（通过 `[Home (Lower Left)]` `_f` `0x7ce3` 切换至 `ND_FILTER` —— **纯手动滤镜值元数据记录，FX3 无物理电子 ND 硬件**）、**Picture Profile（`Log=Off`）或 Select LUT（`Log!=Off`, `_f` `0x643e`）**、**White Balance**；底部/顶部"其他相机设置"状态条仅只读展示。支持触控直点或按下控制拨轮中心激活光标（`HOME_SCREEN_STATE_ON_CURSOR_ON`）方向键选择调节。
   - **实测事实（`[Framing Settings]` 活跃，而 AI `[Auto Framing]` 在 FX3 Ver. 7.02 为休眠资产）**：`Shooting -> [Shooting Option] -> [Framing Settings]`（`_f` `0x7d18`）在 FX3 Ver. 7.00+ 为**活跃功能**，包含 **`Framing`**（默认 `Off`）、**`Recording/Streaming`**（`Full` 默认 / `Crop`）与 **`HDMI`**（`Crop` 默认 / `Full`），配合 *Monitor & Control* 或自定义键 `[Framing Stop (Full)]`（`_f` `0x7d25`）/ `[Switch Framing]`（`_f` `0x7d1e`）手动裁切推拉，强制关闭 APS-C S35 且录制/流传输/`>=100p` 时锁定。相反，`_f.uxc` 中的 **`[Auto Framing Settings]`**（`0x6be6`）、`Auto Framing`（`0x79bc`）、`Crop Level`（`0x6c9d`）、`Framing Tracking Speed`（`0x69cc` Lv1..5）、`Framing Stabilizer`（`0x7566`）及 `_g` `0x60e6/0x62ad/0x63d1` 在 **FX3 Ver. 7.02 上完全休眠未开放**：官方 `ilc/2210` 与 *Monitor & Control* 手册明确标注 **FX3/FX3A/FX30 不支持 Auto Framing**，且 `FX3 appFw.so` 的 Feature Manager 枚举固定指向 `TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`（`AUTO_FRAMING_AFR`、`FRAMING_SIZE`、`FRAMING_FOLLOW_UP_SPEED`、`PTZAUTOFRAMING_*` 全部 **`0` 命中**）。
   - **实测事实（与 FX6 Ver. 6.00/6.01 对比）**：`ILME-FX6` 自 Ver. 6.00 起亦引入 VENICE/BURANO 风格的 **`Home Screen`（`BIG6`）**（`5-024-458-18` p. 15；`FX6 appFw.so` `procam_big6_menu_home_{presenter,controller}`、`procam_big6_menu_look_middle_*`、`FX6_2` `0x5231`），6 格固定为 `FPS / ISO-Gain-EI / Shutter / ND Filter-Iris / Base Look-Scene / White Balance`，且支持触控与多功能拨盘/Direct Menu 操作，不随 SDI/HDMI 输出至外部监视器；同样，`FX6 appFw.so` 与 `FX6_1.uxc` 内的 `Auto Framing` / `PTZAUTOFRAMING_*`（`0x2a8d..0x2de1`）也是**休眠未开放符号**。

2. **子系统 2（`[Interval Shoot Func.]` 静态延时连拍 vs FX6 `[Interval Rec]`）**：
   - **实测事实（FX3 参数全表与机制差异）**：FX3 的 `MENU -> (Shooting) -> [Drive Mode] -> [Interval Shoot Func.]`（`_f` `0x7027` / `0x77a7`）**仅生成静态照片序列**（不在机内自动合成视频，需经 *Imaging Edge Desktop* Viewer 合成）。共 7 项子参数且**全部支持 `[Camera Settings Reset]` 重置**：`Interval Shooting`（默认 `Off`）、`Shooting Start Time`（`1s..99m59s`, 默认 `1 Sec`）、`Shooting Interval`（`1s..60s`, 默认 `3 Sec`）、`Number of Shots`（`1..9999`, 默认 `30`）、`AE Tracking Sensitivity`（`High / Mid[默认] / Low`）、`Shutter Type in Interval`（`Mechanical Shutter / Electronic Shutter[默认，独立于常规 Shutter Type]`）、`Shoot Interval Priority`（`Off[默认] / On`）。回放配套 `[Display as Group]`（`_f` `0x6f26`）与 `[PB Speed for Interval]`（`_f` `0x72bd`）。在 `Intelligent Auto` 模式下不可用，启用时自动退出 `BULB` 并回退 `30"`。
   - **推断（单次至多 9,999 张写卡爆发与 Slot-1 Tier-0 Fail-Closed）**：单个 `[Interval Shoot Func.]` 任务可向 `DCIM/` 触发至多 **9,999 次静态文件写入（RAW/JPEG/HEIF 翻倍至 19,998 文件）并连续改写 `AVF_INFO` 媒体数据库**；若 Slot 1 承载 Tier-0 只读恢复保险库，任何针对 Slot 1 的间隔拍摄写入或触发路径**必须 fail-closed 阻断并返回 `EROFS (30)` / `EBUSY (16)`**，保障 `slot1_data_sector_writes == 0`。
   - **实测事实（与 FX6 `[Interval Rec]` 对比）**：`ILME-FX6` 的 `Project > Interval Rec`（`5-024-458-18` pp. 55–56、`FX6_2.uxc` `0x4247/0x43c6/0x4578/0x4db6`）直接在机内将多帧时间间隔图像封装为**单个 XAVC MXF 视频剪辑**：`Interval Time` 跨越 `1s..24h`（含 `1..10s, 15..50s, 1..10m, 15..50m, 1..4h, 6h, 12h, 24h`），`Number of Frames` 依系统帧率选 `1/2/3/4/6/9/12/24` 帧，另支持 `Pre-Lighting`（配合 HVL-LBPC），但与 `Picture Cache Rec`、`Simul Rec`、`S&Q Motion` 及代理录制严格互斥（`MODEL_VALUE_CHANGED_BY_EXCLUSION_INTERVAL_REC`），且变更视频格式会自动关闭。

3. **子系统 3（`[Time Code Make]` / `[Time Code Run]` 与 `[HDMI Output Settings]` 联动）**：
   - **实测事实（`Regenerate` 强制 `Rec Run` 与 `VMC-BNCM1` 边界）**：`MENU -> (Shooting) -> [TC/UB]` 中的 `[Time Code Make]`（`_f` `0x6b79`：`Preset[默认]` / `Regenerate`）与 `[Time Code Run]`（`_f` `0x7313`：`Rec Run[默认]` / `Free Run`）**均不支持 `[Camera Settings Reset]` 重置**。当 `Time Code Make = Regenerate` 时，相机会从 `[Recording Media]` 指定的卡槽（若为 **`Simult. Recording` 同时录制则读取 Slot 1**）末段片段继承连续时间码，并**强制按 `Rec Run` 运行，无视 `[Time Code Run]` 当前选项**；使用 `VMC-BNCM1` 注入外部 LTC 必须同时设为 `Preset + Free Run` 方可锁定 `EXT-LK`。
   - **实测事实（HDMI `REC Control`、`Time Code Output` 与 `4ch Audio Output` 状态机）**：`MENU -> (Setup) -> [External Output] -> [HDMI Output Settings]` 同样**不支持 `[Camera Settings Reset]` 重置**。**`[REC Control]`（默认 `Off`）开启前必须先将 `[Time Code Output]` 设为 `On`（默认 `Off`）**；但依据 `FX3 appFw.so` `PRM_HAITA_setting_rec_control_*` 互斥符号表，**`[REC Control]` 在 `[Rec. Media dur HDMI Output]` 为 `On` 或 `Off(HDMI Only)` 两种模式下均可生效**（包含内录+外录同步触发，或插卡/不插卡下 HDMI-only / RAW 外录触发，屏幕显示 `(STBY)` / `(REC)`），但在 S&Q 帧率或流传输模式下受限。**`[4ch Audio Output]`**（`_f` `0x6aa0`：`CH1/CH2[默认]` / `CH3/CH4`）因 HDMI 仅开放立体声两通道输出，无法 4 声道同传，录制与回放期间均生效。
   - **实测事实（与 FX6 对比）**：`ILME-FX6` 的 `TC/Media > Timecode > Mode` 在 `Preset` / `Regen` 之外多出实时 **`Clock`** 模式（`VAL_setting_tc_make_TC_MAKE_CLOCK`，FX3 无此项），且具备物理 BNC `TC IN/OUT`；`Project > SDI/HDMI Rec Control > Setting`（`5-024-458-18` p. 108）明确拆分为 **`SDI/HDMI Remote I/F`**（机内无卡单控外录，非帧精确）与 **`Parallel Rec`**（机内有卡并行帧精确同步，Simul Rec 时跟随 Slot A）。

4. **子系统 4（Ver. 7.00+ `[Access Authen.]` 安全重构与 `[Fan Control]` / `[Auto Power OFF Temp.]` 热边界）**：
   - **实测事实（`Access Authen.` 为 SSH + PTP-IP 认证，非 HTTPS/HTTP Digest）**：FX3 **Ver. 7.00 彻底移除了 `Security(IPsec)`、`WEP` 与 `WPA-PSK`**，强制要求 `WPA2-PSK` / `WPA3-SAE` 配合默认 **`On`** 的 `[Access Authen. Settings]`（Ver. 3.00+ 引入，不随 `Camera Settings Reset` 清除，须用 `[Reset Network Set.]` 或 `[Initialize]` 重置）。`ilc/2210`、Sony Camera Remote SDK 与 `FX3 appFw.so` 共同实证：**`Access Authen.` 基于 SSH 协议（`MSGID_SSHD_START_CMD`, `sshd_start`, `_g 0x634e GOTO_SSHINFODISPLAY`）通过用户名、密码及设备 SSH Host Key Fingerprint（`_g 0x610b`, `_f 0x69b4`）完成链路加密与鉴权**；`FX3 appFw.so` 中 **`HTTP_DIGEST`、`BASIC_AUTH`、`HTTPS` 全部 `0` 命中**。`[Import Root Certificate]`（`_f` `0x7940`, `ROOT_CERTIFICATE_TYPE_{CLOUD,FTP,RTMP}`, `HTTP_CLIENT_TLS_ERR`）仅作用于相机作为客户端发起的 **FTPS / RTMPS / Cloud 出站 TLS 校验**。
   - **实测事实（`[Fan Control]` 与 `[Auto Power OFF Temp.]` 纠偏：FX3 与 FX6 均不存在 `Max` 选项！）**：
     - FX3 `Setup -> [Setup Option] -> [Fan Control]`（默认 `Auto`，**不支持 `Camera Settings Reset`**）实际暴露 **`Auto`**、**`Minimum`**、**`Off in Rec`** 与 **`Always Off`**（`_f` `0x6811/0x68fd`）**4 档**；`FAN_CONTROL_MAX` 在 `FX3 appFw.so` 中为 **`0` 命中**。`[Auto Power OFF Temp.]`（默认 `Standard`，**不支持 `Camera Settings Reset`**）提供 `Standard` / `High`（`VAL_setting_auto_pwr_off_temp_AUTO_PWR_OFF_TEMP_{STANDARD,HIGH}`），设为 `High` 可将 4K 59.94p 连续录制时长从约 30 分钟延长至约 90 分钟（25°C/40°C），HD 59.94p 延至约 120 分钟（25°C），但触发低温烫伤警告并要求尽量使用三脚架。
     - **关键跨机纠偏（`ILME-FX6` 同样不存在 `Max`）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18` `Technical > Fan Control`）与 `FX6 appFw.so` 中实际仅提供 **`Auto` / `Minimum`（`Always On (Minimum)` `FX6_1 0x2fda`） / `Off in Rec`** 3 档，**`FAN_CONTROL_MAX` 在 `FX6 appFw.so` 中同样 `0` 命中**；与 FX3 相反的是，`FAN_CONTROL_ALWAYS_OFF`（`Always Off`, `FX6_1 0x2880`）在 FX6 上是**休眠未暴露符号**，而 FX3 则将其公开为用户菜单选项。

---

## 1. 子系统 1：Ver. 7.00/7.02 `[BIG6]` (Home) 屏幕与 `[Framing Settings]` / 休眠 `[Auto Framing]`

### 1.1 `ILME-FX3 Ver. 7.02` 真值矩阵与 Reset 边界（`实测事实`）

| 项目 / 菜单路径（`ilc/2210`） | `FX3 Ver. 7.02` 实机选项与默认值 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证与交互规则（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Mode Settings]`**<br>（`Shooting -> Shooting Mode -> Mode Settings`） | `Movie` / **`Fixed/Variable`**（Ver. 7.00+ 新增） | **Can be reset** | `_f` `0x7d0d` `Fixed/Variable`、`_f` `0x7d19`、`_g` `0x6521`；`BKID_APP_setting_fps_fixed_variable_select`；**`HOME` (`BIG6`) 激活硬前提** |
| **`HOME` (`BIG6`) 主屏幕**<br>（自定义键 `[HOME]` 或向下滑动） | 6 枚大图标控制块 + 只读状态条（默认 `Off`） | `Home (Lower Left)` 可随拍摄自定义重置 / 快捷状态按切换保持 | `26view_tp_button_01_for_big6`、`GUIDE_BIG6_FPS_SELECT`、`GUIDE_BIG6_FRAME_RATE`、`update_big6_item_iso_ei`、`BKID_APP_home_screen_state`、`VAL_home_screen_state_HOME_SCREEN_STATE_{OFF,ON_CURSOR_OFF,ON_CURSOR_ON,TEMP_OFF}`、`BKID_APP_home_screen_last_cursor_position_number` |
| **`[Home (Lower Left)]`**<br>（`Setup -> Operation Customize -> Home (Lower Left)`） | **`Aperture`**（**默认**） / `ND Filter` | **Can be reset** | `_f` `0x7ce3` `Home (Lower Left)`、`_f` `0x7ce6`/`0x7ca2`/`0x7cf0`、`0x7a1b`；`BKID_APP_setting_movie_home_lower_left`、`MOVIE_HOME_LOWER_LEFT_{APERTURE,ND_FILTER}`；**无 e-ND 硬件，纯手动滤镜记录** |
| **`[Swipe Down]`**<br>（`Setup -> Touch Operation -> Swipe Down`） | `Off` / `Open Home Screen` 等 | 随触控操作设置 | `_f` `0x7cdd` *"Opens the Home screen through a downwards swipe on the screen."*、`_g` `0x6526`、`VAL_setting_swipe_down_SWIPE_DOWN_HOME_SCREEN` |
| **`[Framing Settings]` -> `Framing`**<br>（`Shooting -> Shooting Option -> Framing Settings`） | `Off`（**默认**） / `On` | **Can be reset** | `_f` `0x7d18` / `0x7d14`；`BKID_APP_setting_fixed_camera_framing_settings_fixed_camera_framing`、`FIXED_CAMERA_FRAMING_{OFF,ON}`；强制关 APS-C S35；`100p/120p` 及录制/流传输中锁定 |
| **`Recording/Streaming`**（`Framing Settings` 子项） | `Full`（**默认**） / `Crop` | **Can be reset** | `_f` `0x7d13` / `0x7d24` `Full` / `0x7d0e` `Crop`；`BKID_APP_setting_fixed_camera_framing_settings_recording_image_crop`、`RECORDING_IMAGE_CROP_{OFF,ON}` |
| **`HDMI`**（`Framing Settings` 子项） | `Crop`（**默认**） / `Full` | **Can be reset** | `_f` `0x7d0f`；`BKID_APP_setting_fixed_camera_framing_settings_hdmi_crop`、`HDMI_CROP_{OFF,ON}` |
| **`[Framing Stop (Full)]` / `[Switch Framing]`** | 仅自定义键 | **Can be reset** | `_f` `0x7d25` / `0x7d1e`；`FUNC_toggle_set_fixed_camera_framing_seq` |
| **`[Auto Framing]` / `[Auto Framing Settings]`** | **DORMANT（FX3 Ver. 7.02 不支持/未激活）** | — | `_f` `0x6be6/0x79bc/0x6c9d/0x69cc/0x7566` 属跨机型 UXC 资产；`FX3 appFw.so` `TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`，且 **`AUTO_FRAMING_AFR` / `FRAMING_SIZE` / `PTZAUTOFRAMING_*` 均 `0` 命中** |

### 1.2 `[BIG6]` 屏幕 6 格动态映射、交互状态机与 `[Framing Settings]` 裁切路由（`实测事实`）

1. **`[BIG6]` 6 格在不同曝光/Log 模式下的真实参数布局（`实测事实`）**：
   - 在 `Mode Settings = Fixed/Variable` 启用后，FX3 `BIG6` 主屏幕按 **"上 3 格 + 下 3 格 + 顶部/底部只读状态条"** 组织（与 `ilc/2210` *Home screen* 章节及 `FX3 appFw.so` 符号完全吻合）：
     - **上左（Tile 1 — `FPS`）**：显示与切换 `Fixed` / `Variable` 及帧率（`GUIDE_BIG6_FPS_SELECT`、`GUIDE_BIG6_FRAME_RATE`）。
     - **上中（Tile 2 — `ISO / Base ISO / EI`）**：由 `FX3 appFw.so` 中 **`update_big6_item_iso_ei`** 函数动态调度 —— 在 `Log Shooting = Off` 或 **`Flexible ISO`**（以及自定义曝光 `P/A/S/M`）下显示实时 **`ISO`**；在 **`Cine EI`** 或 **`Cine EI Quick`** 下切换为 **`Base ISO`**（`800` / `12800`）与 **`EI`** 曝光指数（`_f` `0x78ce`）。
     - **上右（Tile 3 — `Shutter`）**：随 `[Shutter Mode]` 在 **`Shutter Speed`**（`1/50` 等）与 **`Shutter Angle`**（`180.0°` 等）间自动切换显示。
     - **左下（Tile 4 — `Aperture` / `ND Filter`）**：由 `[Home (Lower Left)]`（`BKID_APP_setting_movie_home_lower_left`）控制，默认 `Aperture`（光圈值）；若设为 `ND Filter`（`_f` `0x7ce3` / `0x7ca2`），仅提供手动录入外置物理 ND 档位元数据（`_f` `0x7cbf/0x7cde/0x7cee`、`_g` `0x6527`），**FX3 机内不存在任何可变电子 ND 滤镜硬件**。
     - **下中（Tile 5 — `Picture Profile` / `Select LUT`）**：`Log Shooting = Off` 时显示 `Picture Profile`（`Gamma` / `Color Mode` / `PP` 编号）；`Log Shooting != Off` 时切换为 **`Select LUT`**（`_f` `0x643e`，支持快速切换已导入/预置用户 LUT）。
     - **下右（Tile 6 — `White Balance`）**：显示并调节色温/白平衡模式。
     - **其他相机设置状态条**：位于主屏幕边缘，展示电池电量、双卡余量、音频电平、TC 等信息，**仅限只读监看，不可直接点击修改**。
   - **触控与按键双重交互（`实测事实`）**：既可在触摸启用时**直接点击 6 个区块之一**弹出子调节面板，也可在启用主屏幕后**按下控制拨轮（Control Wheel）中央按键**将状态机从 `HOME_SCREEN_STATE_ON_CURSOR_OFF` 切入 `HOME_SCREEN_STATE_ON_CURSOR_ON`（`_f` `0x7cf1` / `BKID_APP_home_screen_last_cursor_position_number`），通过上下左右方向键在 6 格间移动并再次按中心确认。在任一状态下按下 `MENU` 或 `Fn` 键可临时切至菜单/取景画面并返回（`HOME_SCREEN_STATE_TEMP_OFF`）。

2. **`[Framing Settings]`（手动取景裁切）vs `[Auto Framing]`（AI 自动构图）边界（`实测事实`）**：
   - **FX3 Ver. 7.00/7.02 仅开放手动 `[Framing Settings]`**：在 `Shooting -> [Shooting Option] -> [Framing Settings]` 中，开启 `Framing = On` 后，允许配合手机/平板端 ***Monitor & Control*** App（`_f` `0x7d10/0x7d16/0x7d20`）实时画框裁切与平滑推拉构图，或通过机内自定义键 `[Switch Framing]` / `[Framing Stop (Full)]` 在全画幅与裁切框间瞬时切换。**独立双路路由规则**：`Recording/Streaming` 默认 `Full`（机内插卡录制与流传输保持完整广角，或设为 `Crop` 仅记录裁切画面）；`HDMI` 默认 `Crop`（HDMI 默认输出裁切后特写画面，可单独改为 `Full`）。
   - **排斥约束（`FX3 appFw.so` `PRM_HAITA_*` 实证）**：开启 `Framing` 后自动关闭 APS-C S35 裁切视角（`model_diff_apsc_restriction_imager_frame_rate_in_file_format_4k`），且在 **4K `100p/120p` 等高帧率、正在录制或 USB/网络流传输进行中**不可变更设置；部分机身不支持自动人体识别追踪。
   - **`[Auto Framing]` 为什么在 FX3 Ver. 7.02 为 DORMANT（`实测事实`）**：尽管 `string_english_f.uxc` 与 `_g.uxc` 存在完整的四语翻译（`0x6be6 Auto Framing Settings`、`0x79bc Auto Framing`、`0x6c9d Crop Level` `Small/Medium/Large`、`0x69cc Framing Tracking Speed` `1..5`、`0x7566 Framing Stabilizer`、`0x639c/0x64df 15s/30s switch`），但这是 Sony 共享 UI 资源池的跨机型文本（面向 `ZV-E1`、`ILCE-1M2`、`PXW-Z200` / `ILME-FX2` 等搭载专用 AI 处理单元的机body）。实测 `FX3 appFw.so` 不仅缺乏 `AUTO_FRAMING_AFR`、`FRAMING_SIZE`、`FRAMING_FOLLOW_UP_SPEED` 等状态机，其功能管理器也锁定在 **`TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`**，与官方 `ilc/2210` 及 *Monitor & Control* 文档"FX3/FX3A/FX30 不支持 Auto Framing"声明 100% 吻合。

### 1.3 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Home 主屏与自动构图对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`, `5-024-458-18`) |
| :--- | :--- | :--- |
| **Home (`BIG6`) 激活与布局** | 需先设 `Mode Settings = Fixed/Variable`；自定义键 `[HOME]` 或下划手势进入；6 格：`FPS` / `ISO or Base ISO·EI` / `Shutter(Speed/Angle)` / `Aperture or Manual ND` / `Picture Profile or Select LUT` / `White Balance` | **Ver. 6.00 新增原生 `Home Screen`（`BIG6`，`5-024-458-18` p. 15）**；由 `Assign Button = Home` 调出；6 格固定为 **`FPS` / `Shutter` / `ISO·Gain·EI` / `ND Filter·Iris` / `Base Look·Scene` / `White Balance`**（`FX6 appFw.so` `procam_big6_menu_home_*`、`procam_big6_menu_look_middle_*`） |
| **左下格 ND 实质差异** | 仅手动输入外置物理 ND 片数值（无电子可变 ND） | **真实内置电子无级可变 ND 滤镜（`1/4..1/128` + `Clear` + `Auto`）**，可直接触控或通过拨盘调节 |
| **外部输出与导航** | 仅机背 LCD/触控及控制拨轮方向键操作，不输出外部监视器 | 仅机身液晶屏操作（不随 SDI/HDMI 输出，p. 15），支持触控 + 多功能拨盘 / Direct Menu |
| **`Framing Settings` / `Auto Framing`** | **`[Framing Settings]`（手动裁切 + *Monitor & Control*）活跃**；`[Auto Framing]` **休眠不支持** | **两者均未在 `5-024-458-18` 公开**：`FX6 appFw.so` 虽存在 `AUTO_FRAMING_AFR` / `FRAMING_SIZE` / `PTZAUTOFRAMING_*` 及 `FX6_1.uxc` `0x2a8d..0x2de1`，属 Sony 专业线共享代码库休眠符号，FX6 Ver. 6.01 实机不提供机内手动/AI 取景裁切 |

---

## 2. 子系统 2：`[Interval Shoot Func.]`（静态延时连拍）vs FX6 `[Interval Rec]`

### 2.1 `ILME-FX3 Ver. 7.02` 菜单真值矩阵、回放配套与 Reset 边界（`实测事实`）

| 菜单路径 / 参数项（`ilc/2210`） | `FX3 Ver. 7.02` 取值范围与出厂默认 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证与互斥约束（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **入口路径**<br>`MENU -> (Shooting) -> [Drive Mode] -> [Interval Shoot Func.]` | **仅限静态照片连拍序列**（不生成机内电影剪辑） | **Can be reset** | `_f` `0x7027` / `0x77a7` / `0x6876`；`BKID_APP_setting_interval_shooting`、`N5model28launch_interval_shoot_func_tE`、`sequence_start_interval_shooting`；`Intelligent Auto` 下不可用 |
| **`[Interval Shooting]`** | **`Off`**（默认） / `On` | **Can be reset** | `_f` `0x7874`；`VAL_setting_interval_shooting_INTERVAL_SHOOTING_{OFF,ON}`；开启后覆盖 `BULB`（临时回退至 `30"`） |
| **`[Shooting Start Time]`** | `1 Sec` .. `99 Min 59 Sec`（**默认 `1 Sec`**） | **Can be reset** | `_f` `0x6b0a`；`EVENT_REMOTE_INTERVAL_SHOOT_FUNC_SHOOTING_START_TIME`；`REC_STATE_IN_PROCESS_COUNTDOWN_TO_START_SHOOTING_INTERVAL_SHOOTING_STARTED` |
| **`[Shooting Interval]`** | `1 Sec` .. `60 Sec`（**默认 `3 Sec`**） | **Can be reset** | `_f` `0x624c`、`_g` `0x61d4`；`EVENT_REMOTE_INTERVAL_SHOOT_FUNC_SHOOTING_INTERVAL` |
| **`[Number of Shots]`** | `1` .. `9999`（**默认 `30`**） | **Can be reset** | `_f` `0x71dd` / `0x79be`、`_g` `0x625f`；`EVENT_REMOTE_INTERVAL_SHOOT_FUNC_NUMBER_OF_SHOTS` |
| **`[AE Tracking Sensitivity]`** | `High` / **`Mid`**（默认） / `Low` | **Can be reset** | `_f` `0x615b` / `0x740a`；`VAL_HAITA_setting_ae_tracking_setting_interval_shooting_AE_TRACKING_{HIGH,MID,LOW}`；`Low` 下亮度变化过渡平滑 |
| **`[Shutter Type in Interval]`** | `Mechanical Shutter` / **`Electronic Shutter`**（**强制默认**） | **Can be reset** | `_f` `0x74c0` / `0x6ddb` / `0x755a` / `0x60b5` / `0x7982`；`VAL_HAITA_setting_shutter_type_setting_interval_shooting_SHUTTER_TYPE_{ELECTRONIC,MECHANICAL}_INTERVAL_SHOOTING_ON`；**默认电子快门以消除机械快门寿命磨损** |
| **`[Shoot Interval Priority]`** | **`Off`**（默认） / `On` | **Can be reset** | `_f` `0x6f69` / `0x6571` / `0x6f9a`；`VAL_setting_shoot_interval_priority_SHOOT_INTERVAL_PRIORITY_{OFF,ON}`；在 P/A 模式下自动缩短快门时间以保拍摄节奏 |
| **`[Display as Group]`** & **`[PB Speed for Interval]`**<br>（`Playback -> Playback Option`） | `Display as Group`: `Off`/`On`；`PB Speed`: 连续回放组内间隔序列速度调节 | — | `_f` `0x6f26` / `0x6447` / `0x70c1`、`0x72bd` / `0x639e` / `0x6060` / `0x6600` / `0x72a0`、`base` `0xe6e4`；`CONTINUOUS_PLAYBACK_FOR_INTERVAL_SHOOTING_MODE_{OFF,ON}` |

### 2.2 静态照片写卡爆发与 Slot-1 Tier-0 恢复保险库 `EROFS=30` 强制护栏（`实测事实` + `推断`）

1. **为什么 `[Interval Shoot Func.]` 对存储子系统具有极高写入爆发风险（`实测事实` + `推断`）**：
   - **实测事实**：单次间隔拍摄配置上限为 **`Number of Shots = 9,999`**。若采用 `RAW + JPEG` 或 `RAW + HEIF` 双格式记录（且或叠加 `Simult. Recording` 双卡同时记录），单次序列会在无需人工持续按压快门的情况下，在数十分钟至数小时内自动触发高达 **`9,999` 张逻辑拍摄 / `19,998` 个 `DCIM/` 静态媒体文件写入**。
   - **推断**：每一张静态图像落盘不仅在 `DCIM/100MSDCF/`（满 `9,999` 文件后自动跨文件夹至 `101MSDCF/`）分配大批量新簇，还会高频触发 DCF 目录项递增与 **`AVF_INFO/` 媒体数据库（MDB）及缩略图缓存页覆写**。因此，当 **Slot 1 挂载为 Tier-0 只读恢复保险库**时，无论 `[Interval Shoot Func.]` 是通过物理快门键、*Creators' App* / USB 遥控还是定时器自动倒计时启动，**只要当前静态录制媒体指向 Slot 1（`Slot 1` 单写、`Simult. Recording` 或自动分选），内核/存储拦截层与模拟器 VFS 必须严守 fail-closed 原则，在首笔写扇区前直接拒绝并返回 `EROFS (errno 30)` / `EBUSY (errno 16)`，保障 `slot1_data_sector_writes == 0`**。

### 2.3 `ILME-FX3` 静态延时序列 vs `ILME-FX6 Ver. 6.01` `[Interval Rec]`（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` `[Interval Shoot Func.]` | `ILME-FX6 Ver. 6.01` `Project > Interval Rec` (`5-024-458-18` pp. 55–56) |
| :--- | :--- | :--- |
| **产物形态与工作流** | **静态照片序列**（`ARW` / `JPEG` / `HEIF` 存 `DCIM/`）；机内仅支持 `PB Speed for Interval` 分组快速预览，需导至电脑用 *Imaging Edge Desktop* 合成视频 | **机内直接封装为单一 XAVC MXF 视频剪辑**（写入 `XDROOT/Clip/`），按设定帧率实时拼合为可立即回放的电影文件 |
| **间隔与帧数参数** | 起始等待 `1s..99m59s`；间隔 **`1s..60s`**；总张数 **`1..9999`** | **`Interval Time`**（`FX6_2` `0x4578`）：`1s..10s, 15s..50s, 1m..10m, 15m..50m, 1h..4h, 6h, 12h, 24h`（最长 24 小时）；**`Number of Frames`**（`0x43c6`）：依系统频率可选 `1/2/4`、`3/6/12`、`6/12/24`、`9` 帧 |
| **灯光联动与快门** | 无预闪/预亮灯控制；专设 `Electronic Shutter` 默认以保护机械快门 | 内置 **`Pre-Lighting`**（`FX6_2` `0x4db6`：`Off / 2s / 5s / 10s`，控制 HVL-LBPC 在曝光前点亮）；全电子传感器读出 |
| **互斥与自动解除** | 与 `BULB`（退至 30"）、`Intelligent Auto`、部分连拍互斥 | 与 **`Picture Cache Rec`、`Simul Rec`、`S&Q Motion`、Proxy 录制及音频录制严格互斥**（`MODEL_VALUE_CHANGED_BY_EXCLUSION_INTERVAL_REC`、`PRM_is_changing_interval_rec_to_picture_cache_rec`）；更改系统视频格式时自动取消 `Interval Rec` |

---

## 3. 子系统 3：`[Time Code Make]` / `[Time Code Run]` 与 `[HDMI Output Settings]`（`REC Control` / `Time Code Output` / `4ch Audio Output`）

### 3.1 `ILME-FX3 Ver. 7.02` 时间码与 HDMI 输出控制真值矩阵（`实测事实`）

| 设置项 / 菜单路径（`ilc/2210`） | `FX3 Ver. 7.02` 可选项与出厂默认 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证与联动约束（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Time Code Make]`**<br>（`Shooting -> TC/UB -> Time Code Make`） | **`Preset`**（**默认**） / `Regenerate` | **Not available**<br>*（需 `[Initialize]`）* | `_f` `0x6b79` / `0x67fa` / `0x698f`；`BKID_APP_setting_tc_make`、`VAL_setting_tc_make_TC_MAKE_{PRESET,REGENRATE}` [Sony 原厂拼写]；**`Regenerate` 强制锁定 `Rec Run`** |
| **`[Time Code Run]`**<br>（`Shooting -> TC/UB -> Time Code Run`） | **`Rec Run`**（**默认**） / `Free Run` | **Not available**<br>*（需 `[Initialize]`）* | `_f` `0x7313` / `0x75b9` / `0x6978`；`BKID_APP_setting_tc_run`、`VAL_setting_tc_run_TC_RUN_{REC_RUN,FREE_RUN}`；外部 `VMC-BNCM1` LTC 需 `Preset + Free Run` |
| **`[Rec. Media dur HDMI Output]`**<br>（`Setup -> External Output -> HDMI Output Settings`） | **`On`**（**默认**） / `Off(HDMI Only)` | **Not available**<br>*（需 `[Initialize]`）* | `_f` `0x6144` / `0x6573`；`BKID_APP_setting_rec_media_during_hdmi_output`、`REC_MEDIA_DURING_HDMI_OUTPUT_{ON,OFF}`；S&Q 下固定 `On` |
| **`[Time Code Output]`**<br>（`HDMI Output Settings` 子项） | **`Off`**（**默认**） / `On` | **Not available**<br>*（需 `[Initialize]`）* | `_f` `0x72af`；`BKID_APP_setting_hdmi_tc_output`、`VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_{OFF,ON}`；S&Q 下不可设 |
| **`[REC Control]`**<br>（`HDMI Output Settings` 子项） | **`Off`**（**默认**） / `On` | **Not available**<br>*（需 `[Initialize]`）* | `_f` `0x76e1` / `0x6657`；`BKID_APP_setting_rec_control`、`VAL_setting_rec_control_REC_CONTROL_{OFF,ON}`；**必须先设 `Time Code Output = On` 方可开启** |
| **`[4ch Audio Output]`**<br>（`HDMI Output Settings` 子项） | **`CH1/CH2`**（**默认**） / `CH3/CH4` | **Not available**<br>*（需 `[Initialize]`）* | `_f` `0x6aa0` / `0x713b` / `0x6bf6` / `0x758c`；`BKID_APP_setting_4ch_output_ch`、`E_4CH_OUTPUT_CH_{1CH_2CH,3CH_4CH}`；录回均有效 |

### 3.2 `Regenerate`、多卡录制 TC 读取与 `REC Control` 状态机深度验证（`实测事实`）

1. **`Regenerate` 对 `Time Code Run` 的强覆盖与多卡槽规则（`实测事实`）**：
   - 当 `[Time Code Make]` 设为 **`Regenerate`** 时，相机在开机或开始录制前会自动扫描存储卡上最后一个视频片段的末尾时间码并接续递增，从而保证同一张卡连续拍摄多条素材的时间码严格单调不重叠。
   - **强制联动规则**：`ilc/2210` 与 `FX3 appFw.so`（`CAUTION_ID_FACTOR_TC_MAKE_REGENERATE_MSG`）共同确认，**一旦设为 `Regenerate`，时间码无论 `[Time Code Run]` 当前选为 `Rec Run` 还是 `Free Run`，实际一律按 `Rec Run` 运行**（仅在录制期间推进，停机待命不走字）。
   - **多卡（Relay / Simultaneous）槽位读取行为**：`Regenerate` 总是从 **`[Recording Media]` 中当前选定记录的卡槽**读取末条时间码；当 `[Recording Media]` 设为 **`Simult. Recording`（同时录制）** 时，系统确定性地读取 **Slot 1** 上最后一段片段的时间码作为接续基准。在 `Relay Rec` 跨卡接力期间，新卡槽沿用相机内部实时 TC 寄存器连续推进，不会归零中断。
   - **外部 LTC 锁定冲突边界**：使用 `VMC-BNCM1`（Multi/Micro USB 转 BNC）锁定外部时间码时，`Make` 必须保持 `Preset` 且 `Run` 必须保持 `Free Run`（即 `EXT-LK`）；若在锁定后将 `Make` 或 `Run` 切换为 `Regenerate` / `Rec Run` 或手动修改预设值，外部时间码锁定立即解除（退回内部自由计时）。

2. **`[HDMI Output Settings]` 中 `[REC Control]` 的精确开启条件与误区澄清（`实测事实`）**：
   - **硬性前置条件 1**：在 `ilc/2210` *HDMI Output Settings* 中明确规定，**当 `[Time Code Output]` 为 `Off` 时，`[REC Control]` 无法设置为 `On`**（`REC Control` 通过在 HDMI 消隐期嵌入标准 Sony Timecode/Trigger 数据包向外部录机如 Atomos Ninja 发送起停脉冲）。
   - **关于 `[Rec. Media dur HDMI Output]` 的重要事实澄清（`FX3 appFw.so` HAITA 矩阵实证）**：
     - 查阅 `FX3 appFw.so` 中的 `PRM_HAITA_setting_rec_control_hdmi_connect_state_hdmi_output_format_resolution_for_exclusion_setting_rec_media_during_hdmi_output_setting_raw_output_media_mount_state_slot1_2_exposure_mode` 等多条 HAITA 状态枚举，发现 **`REC_CONTROL_ON` 与 `REC_MEDIA_DURING_HDMI_OUTPUT_ON`（内录+外录同步）以及 `REC_MEDIA_DURING_HDMI_OUTPUT_OFF`（HDMI-Only 外录，包含 `RAW_OUTPUT_ON` 与 `RAW_OUTPUT_OFF`）均存在有效合法路径**！
     - 且 `ilc/2210` 与 HAITA 规则同时说明：当 **`Rec. Media dur HDMI Output = On`（机内插卡同时录制）** 时，必须保证 `[Recording Media]` 至少一槽已挂载可录卡，按机身 REC 键同时向卡与 HDMI 外录机发送 `(REC)`；当 **`Rec. Media dur HDMI Output = Off(HDMI Only)`（包括 ProRes RAW HDMI 外录或无卡纯外录测试）** 时，`REC Control = On` 同样允许工作，此时按下机身 `MOVIE` 按钮可直接遥控外部 HDMI 录机开始/停止录制并显示 `(STBY)` / `(REC)` 状态，机内不写入任何卡扇区。但在 **`Network Streaming` 开启、`USB Streaming` 开启、或 `S&Q` 高帧率/时间码关闭模式**下，`REC Control` 被 HAITA 状态机禁用。
   - **`[4ch Audio Output]` 硬件降混边界**：虽然 FX3 配合 XLR-H1 手柄支持机内 4 通道 24-bit LPCM 音频录制（XAVC S / HS / S-I），但 HDMI 接口输出遵循 2ch LPCM 规范，无法在单根 HDMI 线中同时承载 4 条独立声道；用户必须在 `CH1/CH2` 与 `CH3/CH4` 之间二选一，且该切换不仅作用于实时监看/外录，也作用于回放输出。

### 3.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 时间码模式与外录控制对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18` pp. 100, 108) |
| :--- | :--- | :--- |
| **`TC Make / Mode` 选项** | `Preset` / `Regenerate`（无 `Clock` 模式） | **`Preset` / `Regen` / `Clock`**（`VAL_setting_tc_make_TC_MAKE_CLOCK`，直接锁同步系统实时时钟） |
| **物理接口与 `Regen` 触发** | 需经 Multi/Micro USB + `VMC-BNCM1`（仅单向 `TC IN`）；`Regen` 在 Simult. Rec 下固定读 **Slot 1** | **专用物理 BNC `TC IN/OUT` 双向端子 + 拨动开关**；`Int Regen` 下在 Simult. Rec 时跟随 **Slot A**；支持 `TC Reset` / `Hold` |
| **外录控制模式** | `HDMI Output Settings -> [REC Control]`（单一 `Off / On`，强制要求 `Time Code Output = On`；支持 `Rec. Media = On` 与 `Off(HDMI Only)`） | `Project > SDI/HDMI Rec Control > Setting`（`5-024-458-18` p. 108）精确区分为 **`Off`** / **`SDI/HDMI Remote I/F`**（机内无卡单控外录，**非帧精确**） / **`Parallel Rec`**（机内插卡双路并行帧精确同步）；`FX6 appFw.so` 另有 `VAL_HAITA_setting_hdmi_tc_output_sdi_output_*` 校验 HDMI 与 SDI 并发约束 |
| **4ch 音频外输出** | `[4ch Audio Output]`：`CH1/CH2` / `CH3/CH4` 二选一 | HDMI 同为 2ch 二选一（`E_4CH_OUTPUT_CH_{1CH_2CH,3CH_4CH}`）；SDI 支持多通道嵌入输出 |

---

## 4. 子系统 4：Ver. 7.00+ `[Access Authen. Settings]` / `[Info]` 与 `[Fan Control]` / `[Auto Power OFF Temp.]`

### 4.1 `ILME-FX3 Ver. 7.02` 网络认证与热管理真值矩阵（`实测事实`）

| 设置项 / 菜单路径（`ilc/2210`） | `FX3 Ver. 7.02` 实机选项与出厂默认 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证与官方协议边界（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Access Authen. Settings]` -> `Access Authen.`**<br>（`Network -> Network Option -> Access Authen. Settings`） | **`On`**（**Ver. 3.00+ 默认**） / `Off` | **Not available**<br>*（需 `[Reset Network Set.]` 或 `[Initialize]`）* | `_f` `0x7ada` / `0x6644` / `0x6eb3` / `0x62ec` / `0x743f`；`BKID_APP_setting_access_authentication{,_username,_password}`、`VAL_setting_access_authentication_ACCESS_AUTHENTICATION_{ON,OFF}`、`encrypt_access_authentication_info`、`CAUTION_ID_FACTOR_ACCESS_AUTHENTICATION_OFF` |
| **`[Access Authen. Info]`**<br>（`Network -> Network Option -> Access Authen. Info`） | 显示 `User`、`Password`、`MAC Address`、**SSH `Fingerprint`** | 同上（Reset Network 生成新凭证/重置） | `_f` `0x6b2b` / `0x6d76` / `0x69b4`、`base` `0xe5b5` / `0xe72a`、`_g` `0x6008/0x610b/0x634e`；`MSGID_SSHD_START_CMD`/`CMP`、`sshd_start`、`sshd_stop`、`access_authentication_fingerprint` |
| **`[Import Root Certificate]`**<br>（`Network -> Network Option -> Import Root Certificate`） | 从卡导入根证书供 **FTPS / RTMPS / Cloud** 验证服务器 | **Not available**<br>*（`Reset Network Set.` 会清除已导入根证书）* | `_f` `0x7940` / `0x7d28`、`_g` `0x607a/0x6086/0x6186/0x6193/0x63cd/0x651e`；`ROOT_CERTIFICATE_TYPE_{CLOUD,FTP,RTMP}`、`HTTP_CLIENT_TLS_ERR`、`sonycert` |
| **`Security(IPsec)` / `WEP` / `WPA-PSK`** | **Ver. 7.00+ 已彻底移除（REMOVED）** | — | `_f` `0x69aa` / `0x6e70` 及 `FX3 appFw.so` `BKID_APP_setting_ipsec` 等 79 个 `ipsec` 符号均属 **Ver. 7.00 移除后的休眠历史符号** |
| **`[Fan Control]`**<br>（`Setup -> Setup Option -> Fan Control`） | **`Auto`**（**默认**） / `Minimum` / `Off in Rec` / `Always Off`<br>*(**无 `Max` 选项**)* | **Not available**<br>*（需 `[Initialize]`）* | `_f` `0x6e77` / `0x6f78` / `0x63f0` / `0x694b` / `0x6d0d` / `0x76fb` / `0x6b53` / `0x6074` / `0x6811` / `0x68fd`；`BKID_APP_setting_fan_control`、`FAN_CONTROL_{AUTO,MINIMUM,OFF_IN_REC,ALWAYS_OFF}`；**`FAN_CONTROL_MAX` 为 `0` 命中** |
| **`[Auto Power OFF Temp.]`**<br>（`Setup -> Power Setting Option -> Auto Power OFF Temp.`） | **`Standard`**（**默认**） / `High` | **Not available**<br>*（需 `[Initialize]`）* | `_f` `0x70f1`、`base` `0xe03b/0xe078/0xe0d7`、`_g` `0x612c/0x61a9`；`BKID_APP_setting_auto_pwr_off_temp`、`VAL_setting_auto_pwr_off_temp_AUTO_PWR_OFF_TEMP_{STANDARD,HIGH}` |

### 4.2 `[Access Authen.]` 底层协议真相与 `[Fan Control]` / `[Auto Power OFF Temp.]` 热力学边界（`实测事实`）

1. **Ver. 7.00+ 网络安全架构重构：`Access Authen.` 是 SSH，TLS 仅管出站客户端（`实测事实`）**：
   - **为什么不是 HTTPS 或 HTTP Digest/Basic Auth**：实测 `FX3 appFw.so` 中 **`HTTP_DIGEST`、`BASIC_AUTH`、`HTTPS` 全部为 `0` 命中**。相反，二进制内直接挂载 **`MSGID_SSHD_START_CMD` / `MSGID_SSHD_START_CMP`、`sshd_start`、`sshd_stop`、`access_authentication_fingerprint` 与 `GOTO_SSHINFODISPLAY`**（`_g` `0x634e`），且 `_g` `0x610b` 四语原文明确指出：*"Access authen. by enter user name and PW, verifying fingerprint with connected device."*。与 Sony *Camera Remote SDK* 及 `ilc/2210` 互证：FX3 的 `[Access Authen.]` 是在 Wi-Fi / USB-LAN 上为 **PTP-IP / Creators' App / Imaging Edge Remote / Monitor & Control** 通信建立 **SSH 加密隧道（含服务端主机密钥指纹核验与口令鉴权）**。
   - **Ver. 7.00 移除的旧协议与默认防线**：Sony Ver. 7.00 官方发行说明明确声明彻底停止支持 **`WEP`、`WPA-PSK` 与 `Security(IPsec)`**，将无线加密锁定在 `WPA2-PSK` / `WPA3-SAE` 之上，并将 `[Access Authen. Settings]` 出厂设为 **`On`**。一旦用户人为设为 `Off`（`CAUTION_ID_FACTOR_ACCESS_AUTHENTICATION_OFF`），远程控制/传输通道将以明文无加密认证模式运行。
   - **TLS 与根证书 (`[Import Root Certificate]`) 的真实职责**：`FX3 appFw.so` 中的 TLS 符号限定在 **`HTTP_CLIENT_TLS_ERR`、`HTTP_CLIENT_GET_ACCURATE_DATE_TIME_TLS_ERR` 及 `ROOT_CERTIFICATE_TYPE_{CLOUD,FTP,RTMP}`**，配合内存卡导入的服务器根证书文件校验相机主动外连的 **FTPS（FTP over TLS）、RTMPS（流媒体）与 Sony Cloud** 远端服务器证书；执行 `[Reset Network Set.]` 时会同时清除用户/密码凭据与导入的根证书，但保留 `[Airplane Mode]` 状态。

2. **`[Fan Control]` 无 `Max` 选项与 `[Auto Power OFF Temp.]` 官方续航热指标（`实测事实`）**：
   - **`[Fan Control]` 四档运行规律（`ilc/2210` + UXC）**：
     - **`Auto`**（默认，`FAN_CONTROL_AUTO`）：由机身热传感器闭环自动启停并无级调速。
     - **`Minimum`**（`FAN_CONTROL_MINIMUM`，`_f` `0x76fb`）：持续以**最低声噪转速**运转，兼顾收音安静度与基础导热。
     - **`Off in Rec`**（`FAN_CONTROL_OFF_IN_REC`，`_f` `0x6074`）：待机时强力散热（可高速运转），**一旦按下录制立即停转以保证机顶/内置麦克风绝对静音**；**但若机身内部温度越过安全保护阈值，固件仍会强制临时重新启动风扇**。
     - **`Always Off`**（`FAN_CONTROL_ALWAYS_OFF`，`_f` `0x68fd`）：风扇全时段强制关闭（仅靠被动镁合金底盘散热），显著缩短连续 4K 录制时长并更早触发过热保护。
     - **零 `Max` 证实**：无论是官方 `ilc/2210` 还是 `FX3 appFw.so`，均**不存在 `Max` 或 `Always (Max)` 选项**（`FAN_CONTROL_MAX = 0` 命中）。
   - **`[Auto Power OFF Temp.]` 与官方温控实测时长（`ilc/2210` *Recording time* + `base 0xe0d7` / `_g 0x61a9`）**：
     - 设为 **`High`**（默认 `Standard`）后，以 25°C / 40°C 环境温度连续录制为例：`XAVC S 4K 59.94p`（150M 4:2:0 8bit）的连续可用录制时长从 `Standard` 下的 **约 30 分钟** 延长至 **`High` 下的约 90 分钟**；`XAVC S HD 59.94p`（50M 4:2:0 8bit）从 `Standard` **约 60 分钟**（25°C）延长至 **约 120 分钟**（25°C）/ **约 90 分钟**（40°C）。
     - `base 0xe0d7` 与 `_g 0x61a9` 四语提示同时强制弹出**低温烫伤（low-temperature burn）警告**，要求设为 `High` 时避免长时间手持，改用三脚架固定。

### 4.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 安全认证与散热控制对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **`Access Authen.` 与 SSH/TLS** | `Network -> Access Authen. Settings`（默认 `On`，SSH 用户名/密码/Fingerprint）；无 IPsec/WEP/WPA；出站 FTPS/RTMPS/Cloud 根证书校验 | `Network > Access Authentication`（`FX6_1` `0x254b/0x279e`、`FX6_2` `0x42d2`）；同为 `sshd_start/stop` + Fingerprint；`FX6 appFw.so` 另支持 **`SRT` TTLS / `RTMPS_certification.pem`** 与 `EVP_DigestSign*/Verify*`，且存在 `ACCESS_AUTHENTICATION_ALWAYS_ON_{TRUE,FALSE}` 与从 `Diadem Pro` 迁移标志 |
| **`Fan Control` 活跃选项** | **`Auto` / `Minimum` / `Off in Rec` / `Always Off`**（4 档；**无 `Max`**） | **`Technical > Fan Control` 仅 3 档：`Auto` / `Minimum`（`Always On (Minimum)`, `FX6_1 0x2fda`） / `Off in Rec`**；**实测 `FX6 appFw.so` 与 `5-024-458-18` 同样绝对不存在 `Max`（`FAN_CONTROL_MAX = 0` 命中）** |
| **`Always Off` 符号差异** | **活跃公开**（`_f` `0x6811/0x68fd` + `FAN_CONTROL_ALWAYS_OFF`） | **休眠未暴露**（`FX6 appFw.so` 有 `FAN_CONTROL_ALWAYS_OFF` 且 `FX6_1 0x2880` 有 `'Always Off'`，但 `5-024-458-18` 未对用户开放） |
| **`Auto Power OFF Temp.`** | **公开**（`Standard` / `High`，延长至 ~90–120 min 并伴随三脚架/低温烫伤警告） | `5-024-458-18` 无对应消费级菜单项（FX6 依赖更大风道与金属散热设计全天候运行）；`FX6 appFw.so` 仅保留共享 `EVENT_REMOTE_AUTO_POWER_OFF_TEMPERATURE` 符号 |

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 角色与实证范围 |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`nflasha15/lib/appFw.so`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BIG6`、`Framing`、`Interval Shoot`、`TC Make/Run`、`REC Control`、`4ch`、`Access Authen`、`Fan/Temp` 及休眠边界 |
| `FX6 appFw.so` (`FX6 .../lib/appFw.so`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `ILME-FX6 Ver. 6.01` `procam_big6`、`Interval Rec`、`TC Clock`、`FAN_CONTROL_*`（证伪 `Max`、确认 `Always Off` 休眠） |
| `FX3-CX95900_ALLLANG-Backup.bin` (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失备份结构基线（`BK4\x00`） |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | FX3 `hdr_flag=15` 主菜单与提示英文包（`0x6000..0x7d3d`, `7,475` 条） |
| `FX3 string_english.uxc` | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | FX3 `hdr_flag=8` 基础菜单与警告英文包（`0xe000..0xea83`, `2,692` 条） |
| `FX3 string_english_g.uxc` | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | FX3 `hdr_flag=8` 扩展提示与验证英文包（`0x6000..0x6579`, `1,390` 条） |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | 简体中文 `_f` 主菜单四语 `resid16` 精确映射 |
| `FX3 string_simplifiedchinese.uxc` / `_g.uxc` | `149,064` / `61,296` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文基础/扩展包 `resid16` 映射 |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | 繁体中文 `_f` 主菜单四语 `resid16` 精确映射 |
| `FX3 string_traditionalchinese.uxc` / `_g.uxc` | `151,908` / `61,372` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文基础/扩展包 `resid16` 映射 |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | 日文原厂 `_f` 主菜单四语 `resid16` 精确映射 |
| `FX3 string_japanese.uxc` / `_g.uxc` | `208,564` / `89,428` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日文原厂基础/扩展包 `resid16` 精确映射 |
| `FX6 string_english.uxc` | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | FX6 `Auto Framing`（休眠）/ `Always Off`（休眠）/ `Always On (Minimum)` / `Off in Rec` / `Timecode` 字符包 |
| `FX6 string_english_2.uxc` | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 `Home` (`BIG6`) / `Interval Rec` / `SDI/HDMI Rec Control` / `Fan Control` 字符包 |

### 5.2 关键菜单项四语言 UXC `resid16` 校验矩阵（`实测事实`）

| 包 / `resid16` | English | 简体中文 | 繁体中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x7d0d` | `Fixed/Variable` | `固定/可变` | `固定/變數` | `Fixed/Variable` | 活跃（`BIG6` Home 前置条件） |
| `_f` `0x7cad` / `0x7cb1` | `HOME` / `Open Home Screen` | `HOME` / `打开主屏幕` | `HOME` / `開啟主螢幕` | `HOME` / `ホーム画面を開く` | 活跃（Ver. 7.00+） |
| `_f` `0x7ce3` / `0x7ca2` | `Home (Lower Left)` / Assign ND | `主屏幕(左下)` / 指定ND滤镜 | `主螢幕(左下)` / 指定ND | `ホーム設定(左下)` / ND割当 | 活跃（手动 ND 元数据） |
| `_f` `0x643e` / `0x78ce` | `Select LUT` / `Base ISO` | `选择LUT` / `Base ISO` | `選取LUT` / `Base ISO` | `LUT選択` / `Base ISO` | 活跃（`BIG6` Log/Cine EI 格） |
| `_f` `0x7d18` / `0x7d14` | `Framing Settings` / `Framing` | `取景设置` / `取景` | `取景設定` / `取景` | `フレーミング設定` / `フレーミング` | 活跃（手动取景 + M&C） |
| `_f` `0x7d13` / `0x7d0f` | `Recording/Streaming` / `HDMI` | `录制/流式传输` / `HDMI` | `錄製/串流傳輸` / `HDMI` | `記録/ストリーミング` / `HDMI` | 活跃（`Full`/`Crop` 独立路由） |
| `_f` `0x7d1e` / `0x7d25` | `Switch Framing` / `Framing Stop (Full)` | `切换取景` / `取景停止(全画幅)` | `切換取景` / `取景停止(全片幅)` | `ﾌﾚｰﾐﾝｸﾞ切換` / `停止 (全画)` | 活跃（自定义键） |
| `_f` `0x6be6` / `0x79bc` | `Auto Framing Settings` / `Auto Framing` | `自动取景设置` / `自动取景` | `自動取景設定` / `自動取景` | `ｵｰﾄﾌﾚｰﾐﾝｸﾞ設定` / `ｵｰﾄﾌﾚｰﾐﾝｸﾞ` | **休眠**（FX3 Ver. 7.02 不支持） |
| `_f` `0x7027` / `0x7874` | `Interval Shoot Func.` / `Interval Shooting` | `间隔拍摄功能` / `间隔拍摄` | `時間間隔拍攝功能` / `時間間隔拍攝` | `ｲﾝﾀｰﾊﾞﾙ撮影機能` / `ｲﾝﾀｰﾊﾞﾙ撮影` | 活跃（静态序列） |
| `_f` `0x6b0a` / `0x624c` / `0x71dd` | `Shooting Start Time` / `Shooting Interval` / `Number of Shots` | `拍摄开始时间` / `拍摄间隔` / `拍摄张数` | `拍攝開始時間` / `拍攝間隔` / `拍攝數` | `撮影開始時間` / `撮影間隔` / `撮影枚数` | 活跃（`1s..99m59s` / `1..60s` / `1..9999`） |
| `_f` `0x615b` / `0x74c0` / `0x6f69` | `AE Tracking Sensitivity` / `Shutter Type in Interval` / `Shoot Interval Priority` | `AE跟踪灵敏度` / `间隔内的快门类型` / `拍摄间隔优先` | `AE追蹤靈敏度` / `間隔內的快門類型` / `拍攝間隔優先順序` | `AE追従感度` / `ｲﾝﾀｰﾊﾞﾙ時ｼｬｯﾀｰ方式` / `撮影間隔優先` | 活跃（默认电子快门） |
| `_f` `0x6f26` / `0x72bd` | `Display as Group` / `PB Speed for Interval` | `以组显示` / `间隔播放速度` | `以群組形式顯示` / `間隔的播放速度` | `グループ表示` / `ｲﾝﾀｰﾊﾞﾙ再生速度` | 活跃（分组回放） |
| `_f` `0x6b79` / `0x67fa` / `0x698f` | `Time Code Make` / `Preset` / `Regenerate` | `Time Code Make` / `Preset` / `Regenerate` | 同英文 | 同英文 | 活跃（`Regenerate` 强锁 `Rec Run`） |
| `_f` `0x7313` / `0x75b9` / `0x6978` | `Time Code Run` / `Rec Run` / `Free Run` | `Time Code Run` / `Rec Run` / `Free Run` | 同英文 | 同英文 | 活跃（不可 `Camera Settings Reset`） |
| `_f` `0x6144` / `0x6573` | `Rec. Media dur HDMI Output` / `Off(HDMI Only)` | `HDMI输出时的摄像媒体` / `关(仅HDMI)` | `HDMI輸出時錄製到記憶卡` / `關(僅限HDMI)` | `HDMI出力時のﾒﾃﾞｨｱ記録` / `切(HDMIのみ)` | 活跃 |
| `_f` `0x72af` / `0x76e1` / `0x6aa0` | `Time Code Output` / `REC Control` / `4ch Audio Output` | `Time Code输出` / `REC控制` / `4ch音频输出` | `Time Code輸出` / `REC控制` / `4ch音訊輸出` | `Time Code出力` / `RECｺﾝﾄﾛｰﾙ` / `4ch音声の出力` | 活跃（`REC Control` 需 `TC Out=On`） |
| `_f` `0x7ada` / `0x6b2b` / `_g 0x610b` | `Access Authen. Settings` / `Info` / Fingerprint | `访问身份验证设置` / `信息` / 指纹验证 | `存取身份驗證設定` / `資訊` / 指紋驗證 | `ｱｸｾｽ認証設定` / `情報` / ﾌｨﾝｶﾞｰﾌﾟﾘﾝﾄ | 活跃（SSH，默认 `On`） |
| `_f` `0x7940` / `_f 0x69aa` | `Import Root Certificate` / `Security(IPsec)` | `导入根证书` / `安全性(IPsec)` | `匯入根憑證` / `安全性(IPsec)` | `ﾙｰﾄ証明書の読み込み` / `ｾｷｭﾘﾃｨ(IPsec)` | Root Cert 活跃（FTPS/RTMPS/Cloud）；**IPsec 已于 Ver. 7.00 移除** |
| `_f` `0x6e77` / `0x6d0d` / `0x6b53` / `0x6811` | `Fan Control` / `Minimum` / `Off in Rec` / `Always Off` | `风扇控制` / `最低` / `录制时关` / `总是关` | `風扇控制` / `最小` / `錄製時關` / `始終關` | `ﾌｧﾝ制御` / `最小` / `記録時Off` / `常にOff` | 活跃（**无 `Max`**） |
| `_f` `0x70f1` / `base 0xe078` / `0xe0d7` / `_g 0x61a9` | `Auto Power OFF Temp.` / `High` / Tripod warning | `自动关机温度` / `高` / 三脚架与升温提示 | `自動關閉電源溫度` / `高` / 腳架與升溫提示 | `自動電源OFF温度` / `高` / 三脚推奨・温度警告 | 活跃（默认 `Standard`） |
