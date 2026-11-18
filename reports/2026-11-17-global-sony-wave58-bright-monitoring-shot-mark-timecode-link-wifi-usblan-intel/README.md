# 全球 Sony 实机情报 Wave 58（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Bright Monitoring]` 与 `[Monitor Brightness]`、`[Shot Mark 1/2]` 写卡机制与回放 `[Edit]` 边界、`[Timecode Link]` / Wi-Fi WPA3 / BT / `USB-LAN` vs FX6 硬件 `TC IN/OUT` 开关，以及休眠 `[Bulb Timer]` / `BULB` 快门 / 休眠 `[Auto HDR]` Still 边界）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Bright Monitoring*、*Monitor Brightness*、*Shot Mark / Image Jump Setting*、*Playing back movies*、*Photo Capture*、*JPEG/HEIF Switch (Photo Capture)*、*Create Divider Frame*、*Select on Cam & Send*、*Wired LAN*、*USB-LAN/Tethering*、*Wi-Fi Frequency Band*、*Wi-Fi Connect*、*Access Authen. Settings/Info*、*Bluetooth Settings*、*Creators' App*、*Airplane Mode*、*Time Code / Matching time code*、*HDMI Output Settings*、*Bulb shooting*、*Shutter Type*、*D-Range Optimizer*、*DRO Bracket*、*HLG Still Image*、*Specifications*、*Setting Reset*、*Reset Network Set.*、*List of default setting values*），官方 Sony `ILME-FX3` FTP Help Guide（`helpguide.sony.net/di/ftp_2210/v1/en/`），官方 Sony `ILME-FX3` Ver. 7.00 / Ver. 7.02 固件发布说明，Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0）及 Ver. 6.00/6.02 发行说明，以及严格 `os.O_RDONLY` 本地 donor 二进制/字符串包交叉实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`full-v4` 网络内核模块 `.ko` 与共享库 `.so`、`ccodeno.txt`/`db.txt`，以及 `FX6 appFw.so`、`FX6 string_english.uxc` / `_2.uxc`）。
- **硬件安全态势**：严格只读本地 donor 分析（`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*` 符号、内核 `.ko` 清单与官方文档条款）与 **`推断`**（含 Tier-0 只读保险库与 Stage-B 护栏设计）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[Bright Monitoring]` 与 `[Monitor Brightness]` vs FX6 `VF Setting` / `Backlight` 消歧）**：
   - **实测事实（`[Bright Monitoring]` 自定义键独占、Ver. 7.00+ 放大兼容变化与模式约束）**：`[Bright Monitoring]`（`_f` `0x701f`）在 `ILME-FX3 Ver. 7.02` 中**不作为拍摄菜单开关暴露**，仅可通过 `MENU -> (Setup) -> [Operation Customize] -> [Custom Key/Dial Set.]` 绑定到自定义键触发。启用期间强制将 `[Live View Display]` 切至 `[Setting Effect OFF]`，且在关机、拍摄模式离开 `P/A/S/M` 或对焦模式脱离 `MF` 时自动取消。**Ver. 7.00/7.02 关键修订**：旧版 `ilc/2210` 注释仍写明运行 `[Focus Magnifier]` / `[Auto Magnifier in MF]` 时无法开关 Bright Monitoring，但 Sony `Ver. 7.00` 官方更新说明已明确**新增在开启 Bright Monitoring 期间使用 Focus Magnifier 与 Auto Magnifier in MF 的支持**。实测 `FX3 appFw.so` 仅含 6 个 `bright_monitoring` 符号，缺乏 `FX6` / Alpha 扩展亮度或区域字段；`ilc/2210` *Bright Monitoring* 页面归类标签包含 `still image, movie, slow&quick motion`，而操作正文特别指向静态拍摄下的按自定义键构图与保持，且该页面未列出对 HDMI 输出信号的特殊声明。
   - **实测事实（`[Monitor Brightness]` 与 Reset 边界）**：`MENU -> (Setup) -> [Monitor] -> [Monitor Brightness]`（`base` `0xe44b`, `BKID_APP_setting_lcd_brightness`）仅暴露 **`Manual`**（`-2`..`+2`，出厂默认 **`Manual`**）与 **`Sunny Weather`**（`base` `0xe1da`），无 `Auto` 选项（ELF 中 `LCD_BRIGHTNESS_{AUTO,BRIGHT,NORMAL}` 为休眠枚举）。`[Monitor Brightness]` **不支持 `[Camera Settings Reset]`**（需 `[Initialize]` 重置）。`ilc/2210` 文档未记载 FX3 在 4K/热保护下强制锁降屏幕亮度档位（主要提醒 `Sunny Weather` 功耗与室内过亮）。
   - **实测事实（FX6 对比与术语消歧）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18`）使用 **`Monitoring > VF Setting > Brightness`**（`1..15`，默认 `8`）与 `Color Mode`（`Color / B&W`），以及自定义键 `VF Adjust / VF Mode`；其 **`Shooting > Auto Exposure > Mode > Backlight`**（`VAL_setting_auto_exposure_mode_MODE_BACKLIGHT`）是**逆光自动曝光补偿**而非屏幕背光；`FX6` UXC/`appFw.so` 中的 `LCD Backlight`（`FX6_2` `0x44f0`）、`VF Backlight`（`0x44f4`）与 `NIGHTSHOT_*` 均为未开放的摄像机同源休眠资产，FX6 低照度依赖 `Cine EI` 双原生 `Base ISO 800 / 12800`。

2. **子系统 2（`[Shot Mark 1/2]` 写卡机制、回放 `[Edit]` 真值与 Slot-1 强制 Fail-Closed）**：
   - **实测事实（FX3 Ver. 7.02 无机内 `[Divide]` / `[Extract]` 剪辑，FTP 自动切片字符串实为休眠）**：`ILME-FX3 Ver. 7.02` 官方手册 `ilc/2210` 与 `FX3 appFw.so` **完全不存在**机内视频分割 `[Divide]` 或截取 `[Extract]` 功能（`divide_clip` / `clip_divide` / `extract_clip` 全部 `0` 命中）。`Playback -> [Edit]` 实际仅暴露 **`[Photo Capture]`**（`_f` `0x6856`，从暂停视频抽取静止画）、`[JPEG/HEIF Switch (Photo Capture)]`（`_f` `0x7175`, `JPEG / HEIF_420 / HEIF_422`）、`[Copy]` 与 `[Rotate]`；另可通过自定义键触发 `[Create Divider Frame]`（`_f` `0x747a`, `_g` `0x6118`）在 `DCIM/` 生成一张分隔帧图像。`_f.uxc` 中的 `Cut to 15/30/60 seconds`（`0x7005/0x6e38/0x6c2a`）及 `0x74a9`（*Cuts and transfers ... with Shot Mark as the center*）在 `FX3 appFw.so` 中无任何活跃 `CUT_TO_*` / `FTP_CUT` 状态机，属**跨机型休眠字符串**。
   - **实测事实（`[Shot Mark 1 & 2]` 录回标定与 `[Clip Flag]`）**：录制阶段经自定义键 `[Add Shot Mark1/2]`（`_f` `0x628b`/`0x628a`），回放阶段经 `[Add/Delete Shot Mark1/2]`（`_f` `0x6143`/`0x6142`）添加或删除标记；暂停回放时拨动后拨盘可直接跳转 Shot Mark，或在 `(Playback) -> [Playback Option] -> [Image Jump Setting]` 选择 `Shot Mark Only` / `Shot Mark1 Only` / `Shot Mark2 Only` / `No Shot Mark`；FTP 与手机传输支持 `[Only Shot Mark]` / `[Only Shot Mark Mov.]` 过滤，Ver. 6.00+/7.00+ 并扩展支持 **`[Clip Flag]`（`OK / NG / KEEP`）** 筛选。
   - **推断（`M4ROOT` 元数据写盘与 Slot-1 Tier-0 Fail-Closed）**：无论是录制/回放阶段增删 `Shot Mark 1/2`、`Clip Flag`，均会就地改写卡内 `M4ROOT/CLIP/*M01.XML` 非实时元数据侧车及 `AVF_INFO` 数据库索引；而 `[Photo Capture]` 与 `[Create Divider Frame]` 会在 `DCIM/` 写入新静止图像文件并更新 `AVF_INFO`。因此当 `Slot 1` 挂载只读 Tier-0 恢复保险库时，所有写卡路径（`Shot Mark` 增删、`Clip Flag`、拍照截帧、分隔帧及理论任何就地 Edit）**必须 fail-closed 拦截并返回 `EROFS (30)` / `EBUSY (16)`**。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18` p. 83 / p. 115）`Thumbnail` 菜单使用 **`Clip Flag`（`OK / NG / KEEP`）** 与 `Lock/Unlock / Delete / Transfer / Filter Clips`，同样无机内 `Divide Clip`；`FX6` UXC/`appFw.so` 中的 `Shot Mark 0..9`（`FX6_2` `0x4fe7..0x53fd`）与 `Essence Mark`（`0x4fcc`, `0x4ddd`）源自 XDCAM 与已在 FX6 Ver. 5.00+ 退役的 *Content Browser Mobile*（现已由 *Monitor & Control* 替代）。

3. **子系统 3（`[Timecode Link]`、Wi-Fi WPA3/5GHz、BT 与 `USB-LAN` vs FX6 硬件 BNC 开关）**：
   - **实测事实（FX3 Ver. 7.02 无蓝牙 `[Timecode Link]` / UltraSync BLUE）**：`FX3 appFw.so` 中 `tc_link` / `timecode_link` / `UltraSync` 全为 **`0` 命中**，Ver. 7.00/7.02 也未新增蓝牙时间码直连。FX3 仅支持通过 Multi/Micro USB 接口搭配专用转接线 **`VMC-BNCM1`**（件号 `A-5051-506-A`）注入有线外部 LTC（`[Time Code Make] = Preset` + `[Time Code Run] = Free Run`，锁定显示 `EXT-LK`，对应 `BKID_APP_ext_tc_lock_status`），以及 HDMI `[Time Code Output]`（默认 `Off`）。
   - **实测事实（Wi-Fi 双频 SKU、WPA3 与 `USB-LAN` 驱动栈）**：`ilc/2210` 明确硬件分版 —— `WW728473` 支持 `2.4/5 GHz`（`802.11 a/b/g/n/ac`），`WW558244` 仅支持 `2.4 GHz`（`802.11 b/g/n`）；`[Wi-Fi Frequency Band]`（`_f` `0x66c3`, 默认 `2.4GHz`）作用于 **Wi-Fi Direct**，`_f` `0x6953` 标明 `5GHz band: Indoor use only`；`libWlanResource.so` 绑定 `ar6000.ko` / `wlan.ko` 与监管库 `db.txt`（21 国家区、59 条 `DFS` 规则）。**Ver. 7.00+ 已彻底移除 `WEP`、`WPA-PSK` 与 `Security(IPsec)`**，强制采用 `WPA2-PSK` / `WPA3-SAE` + `[Access Authen. Settings = On]`。Bluetooth `5.0`（默认 `Bluetooth Function = Off`）支持最多 15 台已配对设备、2 路并发连接（至多 1 个 BT 遥控器）与 *Creators' App*。`[Wired LAN]`（DHCP `Auto` 默认 / `Manual` IP/掩码/网关/主次 DNS <= 15 字符）与 `[USB-LAN/Tethering]`（Ver. 7.00+ 新增 `[USB-LAN Cnct. Launch]` 默认 `Off`, `_f` `0x7d2a`, `BKID_APP_setting_usb_lan_connect_launch`）在本地 `full-v4` 根文件系统中拥有真实内核模块 **`cdc_ncm.ko`、`cdc_ether.ko`、`r8152.ko`、`asix.ko`、`ax88179_178a.ko`、`usbnet.ko`、`ipheth.ko`、`rndis_host.ko`** 与服务库 `libWiredLanResource.so` / `libNetServiceEther.so`；**但 USB-C `USB-LAN` 与 Multi/Micro USB（如 `VMC-BNCM1` 或有线快门）及 Wi-Fi 不能同时进行通信**。
   - **实测事实 + 推断（`[Airplane Mode] = On` 零射频与 FX6 对比）**：开启 `[Airplane Mode] = On` 关闭一切 Wi-Fi/BT 射频（且 `[Reset Network Set.]` 与 `[Initialize]` 均保留 `Airplane Mode = On`），但有线 `USB-LAN`（`eth0`）仍可维持受控台架隔离通信。相比之下，`ILME-FX6 Ver. 6.01`（`5-024-458-18` p. 40, 135）配备**物理 `TC IN/OUT` 拨动开关与专用 BNC 端子**（其 `FX6 appFw.so` 残留休眠 `BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING`）、**无任何蓝牙硬件**（`FX6 appFw.so` 的 `BKID_APP_SETTING_BLUETOOTH_FUNCTION` 属跨机休眠符号），并通过 USB-C 适配有线 LAN（Ver. 6.00 已将其并入 Network 状态页，且与 Wireless LAN / Modem 严格互斥）。

4. **子系统 4（休眠 `[Bulb Timer]`、`BULB` 机械快门约束与 `DRO` vs 休眠 `[Auto HDR]`）**：
   - **实测事实（`[Bulb Timer]` 在 FX3 Ver. 7.02 为休眠资产）**：尽管 `FX3 appFw.so` 含 `BKID_APP_setting_bulb_timer`、`BKID_APP_MR_setting_bulb_timer`、`N5model20setting_bulb_timer_tE` 与 `sequence_set_bulb_timer`，且 `_f.uxc` 四语含 `0x630f` `BULB Timer` 与 `0x78b6` `BULB Timer Settings`，但官方 `ilc/2210` 手册与 Ver. 7.00/7.02 更新日志对 `Bulb Timer` **零命中**（实机菜单未暴露；该功能实装于 `ILME-FX2`、`ILCE-7RM5`、`ILCE-6700`、`ILCE-7CR` 等机型）。
   - **实测事实（Still `[BULB]` 与 `DRO` / `Auto HDR` 边界）**：FX3 Still 仅支持手动 `[BULB]`（`MODE -> Manual Exposure -> 后拨盘越过 30"`），**必须使用 `[Mechanical Shutter]`**；在 `[Electronic Shutter]`、`Cont. Shooting`、`Self-timer(Cont)`、`Cont. Bracket` 与 `Interval Shooting` 下不可用（已选 BULB 会**临时回退为 `30"`**）；超过 30 秒定时曝光须依赖蓝牙遥控器（启停两次按压）、Multi/Micro USB 带锁线控或外部联机。在宽动态范围静态功能上，**`[D-Range Optimizer]`**（`Auto` 默认 / `Off` / `Lv1..Lv5`，支持 `Camera Settings Reset`）与 **`[DRO Bracket]`**（`Lo: Lv1/2/3`, `Hi: Lv1/3/5`）均**活跃可用**（当 `Picture Profile != Off` 或 `HLG Still Image = On` 时锁定禁用），而传统 Alpha **`[Auto HDR]`**（`base` `0xe49d` / `0xe453..0xe459` / `0xe5d0`, `BKID_APP_extern_menu_hdr_level`）在 FX3 上**完全休眠禁用**（由 `[HLG Still Image]` 替代宽动态静态输出）。

---

## 1. 子系统 1：`[Bright Monitoring]` 与 `[Monitor Brightness]`（`Manual -2..+2` vs `Sunny Weather`）

### 1.1 `ILME-FX3 Ver. 7.02` 真值表、快捷键约束与 Reset 边界（`实测事实`）

| 项目 / 菜单路径（`ilc/2210`） | `FX3 Ver. 7.02` 实机选项与默认值 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证与交互规则（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Bright Monitoring]`**<br>（`Setup -> Operation Customize -> Custom Key/Dial Set.`） | **仅限自定义键激活**（不在拍摄菜单直接显示 toggle） | — | `_f` `0x701f`；`EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_{ON,OFF}`、`VAL_setting_bright_monitoring_state_BRIGHT_MONITORING_STATE_{ON,OFF}`、`CAUTION_ID_FACTOR_CAM_SET_BRIGHT_MONITORING_ON_MSG`；无亮度档位枚举 |
| **`[Monitor Brightness]`**<br>（`MENU -> Setup -> Monitor -> Monitor Brightness`） | **`Manual`**（**默认**，`-2`..`+2` 默认 `0`） / **`Sunny Weather`** | **Not available**<br>*（需 `[Initialize]`）* | `base` `0xe44b`（`Monitor Brightness`）、`0xe1da` / `_f` `0x7a61`（`Sunny Weather`）；`BKID_APP_setting_lcd_brightness` + `BKID_APP_setting_lcd_brightness_brightness_setup_manual`（`-2..+2` 5 档）；`AUTO/BRIGHT/NORMAL` 为休眠枚举 |

### 1.2 `[Bright Monitoring]` 与 `[Monitor Brightness]` 运行机制深度剖析（`实测事实`）

1. **`[Bright Monitoring]` 强约束与 Ver. 7.00/7.02 版本演进（`实测事实`）**：
   - **作用机制**：在极暗环境下（如星空摄影）通过延长实时取景曝光读取时间提亮机背 LCD，便于构图。启用期间相机自动强制将 **`[Live View Display]` 切至 `[Setting Effect OFF]`**，因此曝光补偿、白平衡或创意外观的实时所见即所得预览会被暂时屏蔽，快门响应及屏幕刷新率亦会下降。
   - **自动取消条件**（`ilc/2210`）：① 电源关闭；② 拍摄模式从 `P/A/S/M` 切出；③ 对焦模式从 `MF`（手动对焦）切回任何自动对焦模式（AF）。在静态拍摄模式下按下自定义键并拍摄后，增亮预览在拍完后仍保持，再次按键方可退出。
   - **模式归属与 HDMI 行为差异**：`ilc/2210` *Bright Monitoring* 页面顶部适用标签列出 `still image, movie, slow&quick motion`，`List of icons on the screen for shooting still images` 亦收录其屏幕图标，但官方步骤文段主要围绕 *"In a still image shooting mode..."* 描述；且官方 *Bright Monitoring* 页面与 *HDMI Output Settings* 页面均**未声明** Bright Monitoring 会随洁净 HDMI 信号改动外录数据流。
   - **Ver. 7.00/7.02 对焦放大兼容性修正**：早期 `ilc/2210` 页面记载运行 `[Focus Magnifier]` 或 `[Auto Magnifier in MF]` 时不能通过自定义键开关 `[Bright Monitoring]`；而 Sony 官方 **`ILME-FX3 Ver. 7.00`（并继承至 `Ver. 7.02`）固件说明明确新增支持在开启 Bright Monitoring 期间使用 Focus Magnifier 与 Auto Magnifier in MF**，使星空手动精确合焦不再互相锁死。
   - **与 FX6 / 新 Alpha 差异**：`FX3 appFw.so` 仅存在 `BRIGHT_MONITORING_STATE_{ON,OFF}`，不存在部分机型中的 `Bright Monitoring` 多级增益或辅助对焦区域扩展项。
2. **`[Monitor Brightness]` 热管理与功耗边界（`实测事实`）**：
   - 仅含 `Manual`（`-2`..`+2` 步进 1，默认 `0`）与 `Sunny Weather`（户外强光高背光模式，无法与自动环境光传感器联动，无 `Auto`）。
   - 不同于部分无主动风扇消费机（如 `ILCE-7SM2`/`ZV-1M2` 文档明确提示 4K 或温升触发屏幕降亮），`ilc/2210` 对 `ILME-FX3`（配备内部散热风扇及更大镁合金散热底盘）**未记载** `Monitor Brightness` 在 4K 录影时的强制档位锁定；仅警告 `Sunny Weather` 会显著增加电池消耗且室内使用过亮。

### 1.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 监视亮度与低照辅助对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`, `5-024-458-18`) |
| :--- | :--- | :--- |
| **屏幕亮度控制** | `(Setup) -> [Monitor] -> [Monitor Brightness]`：`Manual (-2..+2)` / `Sunny Weather` | **`Monitoring > VF Setting > Brightness`**（`1..15`，默认 `8`），配合 `Color Mode`（`Color / B&W`）及自定义键 **`VF Adjust`** / **`VF Mode`** |
| **暗光辅助构图** | 自定义键专属 **`[Bright Monitoring]`**（强制 `Setting Effect OFF` + 仅限 `P/A/S/M + MF`） | 无 `[Bright Monitoring]`；`Cine EI` 下依靠原生双基础感光度 **`Base ISO 800 / ISO 12800`**（`FX6_1` `0x3166/0x318b`）实现无增益噪点暗光预览 |
| **`Backlight` / `Night` 术语消歧** | 无 `Backlight` 屏幕独立项或 `NightShot` 红外 | `FX6` 菜单 **`Shooting > Auto Exposure > Mode > Backlight`**（`VAL_setting_auto_exposure_mode_MODE_BACKLIGHT`）是**逆光 AE 曝光模式**；`FX6_2` `0x44f0` `LCD Backlight`、`0x44f4` `VF Backlight` 与 `BKID_APP_SETTING_NIGHTSHOT_*` 均为**休眠摄像机遗留符号** |

---

## 2. 子系统 2：`[Shot Mark 1/2]` 标定机制、回放 `[Edit]` 边界与 Slot-1 强制写保护

### 2.1 `Shot Mark 1/2`、`Clip Flag` 与回放 `[Edit]` 真值矩阵（`实测事实`）

| 功能项 / 菜单路径（`ilc/2210`） | `FX3 Ver. 7.02` 实机行为与选项 | ELF / UXC 实证与底层存储影响（`实测事实` + `推断`） |
| :--- | :--- | :--- |
| **录制期打点**<br>（`Custom Key/Dial Set.`） | **`[Add Shot Mark1]`**（`_f` `0x628b`）<br>**`[Add Shot Mark2]`**（`_f` `0x628a`） | 实测事实：录像中按自定义键在当前视频帧时间戳写入 `Shot Mark1/2` 标记；`推断`：追加写入 `M4ROOT/CLIP/*M01.XML` 非实时元数据侧车（`EssenceMark`） |
| **回放期增删**<br>（`Custom Key Setting`） | **`[Add/Delete Shot Mark1]`**（`_f` `0x6143`）<br>**`[Add/Delete Shot Mark2]`**（`_f` `0x6142`） | 实测事实：回放视频帧无标记时写入，有标记时就地删除；无法对只读介质执行 |
| **回放导航与跳转**<br>（`Playback -> Playback Option -> Image Jump Setting`） | 暂停时转动后拨盘直跳 Shot Mark；拨盘选项：`Shot Mark Only` / `Shot Mark1 Only` / `Shot Mark2 Only` / `No Shot Mark`（及 `Divider Frame Only` / `Image After Divider`） | `_f` `0x76cf` / `0x7a5b` / `0x79cb` / `0x6ffb` / `0x7818`；`0x7868` / `0x7a80`；进度条显示标点图标 |
| **筛选传输与 `Clip Flag`** | Smartphone `Select on Cam & Send` 与 `FTP` 支持 `Target Movie`: `All` / `Only Shot Mark Mov.`；Ver. 6.00+/7.00+ 支持 **`[Clip Flag]`**（`OK / NG / KEEP`） | `BKID_APP_setting_ftp_transfer_func_target_img_shot_mark`；`BKID_APP_is_valid_{ftp_transfer,send_to_smartphone}_target_image_clip_flag_{ok,ng,keep,off}` |
| **回放 `[Edit]`**<br>（`MENU -> Playback -> Edit`） | **仅含 `[Photo Capture]`**（`_f` `0x6856`）、`[JPEG/HEIF Switch (Photo Capture)]`（`_f` `0x7175`）、`[Copy]`、`[Rotate]`；另可自定义键执行 **`[Create Divider Frame]`**（`_f` `0x747a`） | `VAL_setting_photo_capture_file_type_PHOTO_CAPTURE_FILE_TYPE_{JPEG,HEIF_420,HEIF_422}`；`[Photo Capture]` 从暂停视频截取静止帧存为 JPEG/HEIF（**新写入 `DCIM/` + `AVF_INFO`**）；`[Create Divider Frame]` 同样写入新静止分隔图像 |
| **机内 `[Divide]` / `[Extract]` 与 `FTP 15/30/60s Cut`** | **FX3 Ver. 7.02 完全不存在（DORMANT / 缺失）** | **实测事实**：`ilc/2210` 全站及 `FX3 appFw.so` 对 `divide_clip` / `clip_divide` / `extract_clip` / `CUT_TO_*` / `FTP_CUT` 均 **`0` 命中**；`_f.uxc` 中 `0x7005/0x6e38/0x6c2a`（`Cut to 15/30/60 seconds`）与 `0x74a9` 属休眠字符串 |

### 2.2 卡片数据结构改写与 Slot-1 Tier-0 Fail-Closed 护栏证明（`推断`）

1. **为什么 `Shot Mark`、`Clip Flag`、`Photo Capture` 与理论 `Divide/Extract` 在 `Slot 1` 必须被阻断（`推断`）**：
   - 在 Sony XAVC 媒体树（`PRIVATE/M4ROOT/` + `DCIM/` + `AVF_INFO/`）中，**`Shot Mark 1/2`** 与 **`Clip Flag`（`OK/NG/KEEP`）** 虽不重编码主视频流（`C*.MP4`），但必须**就地覆盖或重写**对应剪辑的 NRT 元数据侧车 **`M4ROOT/CLIP/*M01.XML`** 并同步更新媒体库索引 `AVF_INFO`（`AVIN*.BNP` / `MDB`）。
   - **`[Photo Capture]`** 与 **`[Create Divider Frame]`** 则必须在 `DCIM/` 目录分配新簇、写入完整 JPEG/HEIF 静止文件并递增重写 DCF 目录项及 `AVF_INFO`。
   - 若未来或跨固件引入就地剪辑 `[Divide]` / `[Extract]`，更将直接修改主码流文件头尾、FAT32/exFAT 簇链表与多个 XML/索引。
   - 因此，只要 `Slot 1` 挂载 **Tier-0 只读恢复保险库**，任何针对 `Slot 1` 的 `[Add/Delete Shot Mark1/2]`、`[Clip Flag]` 修改、`[Photo Capture]`、`[Create Divider Frame]` 及 `[Edit]` / `[Delete]` 操作都**必须严格 fail-closed 拦截并向 UIPC 上层返回 `EROFS (errno 30)` 或 `EBUSY (errno 16)`**，确保 `slot1_data_sector_writes == 0`。

### 2.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 场记标点对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **机内活跃场记标记** | **`Shot Mark 1 / Shot Mark 2`**（录制+回放增删、后拨盘跳转、FTP/手机按 Shot Mark 过滤）+ **`Clip Flag`（`OK/NG/KEEP`）** | `Thumbnail` 菜单（`p. 83 / p. 115`）使用 **`Clip Flag`（`OK / NG / KEEP`）** 与 `Filter Clips`；`5-024-458-18` 对机内 `Shot Mark` / `Essence Mark` **零命中** |
| **机内 `Shot Mark 0..9` / `Essence Mark` 实证** | 仅存在 `Shot Mark 1 & 2` | `FX6_2.uxc` 含 `Shot Mark 0..9`（`0x4fe7..0x4ff5`, `0x5011..0x501a`, `0x53eb..0x53fd`）与 `Essence Mark`（`0x4045`, `0x4fcc`, `0x4ddd`）—— 源自 XDCAM 与 *Content Browser Mobile*（CBM Live Logging 使用 `ESSENCE_MARK`）；**FX6 Ver. 5.00+ 已废弃 CBM 改用 *Monitor & Control***，上述字符串属休眠遗留资产 |
| **机内视频分割 `Divide Clip`** | **无** | **无**（`5-024-458-18` 与 `FX6 appFw.so` `DIVIDE_CLIP` 均 `0` 命中；仅老式 XDCAM FAT 模式支持 `DIVIDE CLIP`） |

---

## 3. 子系统 3：`[Timecode Link]`、`[Wi-Fi]`（`2.4/5GHz`, `WPA2/WPA3`）、`[Bluetooth]` 与 `[Wired LAN (USB-LAN)]` vs FX6 硬件 `TC IN/OUT`

### 3.1 `[Timecode Link]`、外部 LTC 同步与有线/无线网络栈真值表（`实测事实`）

| 子系统功能（`ilc/2210`） | `FX3 Ver. 7.02` 实机支持状态与默认值 | `[Camera Settings Reset]` / `[Reset Network Set.]` | `FX3 appFw.so` / `.ko` / `.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **蓝牙 `[Timecode Link]` / `UltraSync BLUE`** | **不支持（缺失 / 0 符号）** | — | `FX3 appFw.so` 中 `tc_link` / `timecode_link` / `UltraSync` 全 **`0` 命中**；Ver. 7.00/7.02 无蓝牙时间码直连 |
| **有线外接 LTC 时间码同步**<br>（`Shooting -> TC/UB`） | **支持**：须用 Multi/Micro USB + **`VMC-BNCM1`**（`A-5051-506-A`），`Make = Preset`、`Run = Free Run`，锁定显示 `EXT-LK`；HDMI `[Time Code Output]` 默认 `Off` | `TC/UB` 属拍摄配置（部分 Reset 可重置）；HDMI `TC Output` 默认 `Off` | `BKID_APP_ext_tc_lock_status`、`BKID_APP_last_ext_tc_lock_freq`、`CAUTION_ID_FACTOR_TC_{MAKE_REGENERATE,OUTPUT_OFF}_MSG`；`_f` `0x6b63/0x6b79/0x6e3d/0x72af/0x7313/0x780c` |
| **`[Wi-Fi]` 频段与安全协议**<br>（`Network -> Wi-Fi / Network Option`） | **`WW728473`**：`2.4GHz / 5GHz`（`802.11a/b/g/n/ac`）；**`WW558244`**：仅 `2.4GHz`（`802.11b/g/n`）。`[Wi-Fi Frequency Band]` 默认 **`2.4GHz`**（作用于 Wi-Fi Direct）。**Ver. 7.00+ 仅支持 `WPA2-PSK` / `WPA3-SAE`**（已移除 `WEP` / `WPA-PSK` / `IPsec`），`[Access Authen.]` 默认 `On` | **Camera Settings Reset 不重置**；需 **`[Reset Network Set.]`** 或 **`[Initialize]`** | `base` `0xe407` `WPA3`、`0xe8ad`；`_f` `0x66c3` `Wi-Fi Frequency Band`、`0x6953` `5GHz band: Indoor use only`、`0x792a` `5GHz`；`libWlanResource.so` 加载 `ar6000.ko` / `wlan.ko` + `ccodeno.txt`（29 项）+ `db.txt`（21 国区、59 条 `DFS` 规则、0 条 `NO-OUTDOOR`） |
| **`[Bluetooth]` 与 *Creators' App***<br>（`Network -> Bluetooth`） | `Bluetooth Ver. 5.0`（2.4 GHz）；`[Bluetooth Function]` 默认 **`Off`**；`[Bluetooth Rmt Ctrl]` 默认 **`Off`**；最多 **15 台配对 / 2 台并发**（限 1 台 BT 遥控器） | 需 `[Reset Network Set.]` 或 `[Initialize]` | `_f` `0x723c` `Bluetooth Function`、`0x6807/0x76fa` `Bluetooth Rmt Ctrl`；`_g` `0x64f8`、`0x6476`；`libInfraBluetooth{,Core,LowEnergy}.so`（`/usr/bin/bt_firm.hcd`, `/usr/bin/bt_stack.conf`） |
| **`[Wired LAN]` & `[USB-LAN/Tethering]`**<br>（`Network -> Wired LAN / USB-LAN/Tethering`） | USB-C 接千兆网卡；`[IP Address Setting]` 默认 **`Auto`**（DHCP）或 `Manual`（IP/掩码/网关/DNS1/DNS2 <= 15 字符）；Ver. 7.00+ 新增 **`[USB-LAN Cnct. Launch]`** 默认 **`Off`** | 需 `[Reset Network Set.]` 或 `[Initialize]` | `full-v4/usr/kmod/` 实存 **`cdc_ncm.ko`**、**`cdc_ether.ko`**、**`r8152.ko`**、**`asix.ko`**、**`ax88179_178a.ko`**、**`usbnet.ko`**、**`ipheth.ko`**、**`rndis_host.ko`**；`libWiredLanResource.so` 绑定 `eth0` 与 `r8152/r8156/ax88179_178a/mii/usbnet`；`_f` `0x7d2a` `USB-LAN Cnct. Launch`、`BKID_APP_setting_usb_lan_connect_launch` |
| **`[Airplane Mode]`**<br>（`Network -> Network Option -> Airplane Mode`） | 默认 **`Off`**；置 `On` 时禁用一切 Wi-Fi / BT 无线连接与位置联动 | **`[Reset Network Set.]` 与 `[Initialize]` 均不会将 `On` 改回 `Off`** | `_f` `0x6b05/0x6df9`、`base` `0xe37d/0xe727/0xe99c/0xea50`；`BKID_APP_setting_airplane_mode`、`libInfraAirplaneMode.so` |

### 3.2 USB-LAN 与 Multi/Micro USB 互斥及零射频台架运行机制（`实测事实` + `推断`）

1. **USB 总线与无线互斥（`实测事实`）**：
   - 官方 `ilc/2210`（*USB-LAN/Tethering*）与 `ftp_2210` 明确规定：① 通过 USB-C 使用有线 LAN（`USB-LAN`）期间，**机内 Wi-Fi 功能不可用**；② **禁止 USB-C 端 `USB-LAN` 与 Multi/Micro USB 端其它 USB 设备（例如有线时间码 `VMC-BNCM1` 或 USB 线控）同时通信**，否则 `[USB-LAN Cnct. Launch]` 自动连接将失败；③ 断电重启或拔插网卡后，若 `[USB-LAN Cnct. Launch] = Off`，需手动重新进入 `[USB-LAN Connection]`。
2. **Stage-B 零射频（Zero-RF）台架隔离策略（`推断`）**：
   - 由于 `Airplane Mode = On` 专门屏蔽 `wlan0` / `ar6000.ko` 与 `bt_firm.hcd` 射频栈，且即便执行 `[Reset Network Set.]` 或 `[Initialize]` 仍能跨重启持久化保持 `Airplane Mode = On`，实验台可强制锁定 `Airplane Mode = On` 并仅通过 **`eth0`（`cdc_ncm.ko` / `r8152.ko` / `ax88179_178a.ko`）有线 USB-LAN** 开展零射频受控调试。

### 3.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 时间码与网络硬件对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **物理时间码接口** | 无 BNC 端子；须经 Multi/Micro USB + **`VMC-BNCM1`** 单向注入外部 LTC（与其它 Multi/Micro USB 通信及 USB-LAN 并发互斥）；无独立 TC 输出，仅支持 HDMI 数字 `Time Code Output` | **机身自带专用物理 `TC IN/OUT` BNC 端子与硬件 `TC IN/OUT` 拨动开关**（`5-024-458-18` p. 40, 135），独立于 USB-C 与 SDI/HDMI；`FX6 appFw.so` 中 `BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING` 与 `FX6_1` `USB Timecode` 为同源休眠资产 |
| **蓝牙 / NFC 硬件** | 内置 `Bluetooth 5.0` + `NFC Type 3`；支持 *Creators' App* 与蓝牙遥控 | **无蓝牙硬件**（`FX6 appFw.so` 中的 `BKID_APP_SETTING_BLUETOOTH_FUNCTION` / `FX6_1` `0x3095` 为未启用遗留符号；Ver. 6.0 已移除旧 NFC 文档流转） |
| **有线与无线网络** | USB-C `USB-LAN`（`CDC-NCM / RTL8152 / ASIX`）；Wi-Fi `2.4/5GHz` `WPA2/WPA3`（Ver. 7.00+ 移除 WEP/WPA/IPsec）；与 *Creators' App* 协同 | USB-C 支持外部有线 LAN 适配器（`5-024-458-18` p. 7；Ver. 6.00 重组 Network 状态页为 Wireless LAN / Wired LAN / Modem）；**`FX6_2` `0x41e5..0x41f2` 实证 `Wired LAN`、`Wireless LAN`、`Modem` 与 `Simul Rec` 之间存在严格硬件互斥**；使用 *Monitor & Control* |

---

## 4. 子系统 4：休眠 `[Bulb Timer]`、`BULB` 快门机械约束与 `DRO` vs 休眠 `[Auto HDR]`

### 4.1 `[Bulb Timer]` 休眠验证与 Still 静态曝光功能真值矩阵（`实测事实`）

| 功能项（`ilc/2210`） | `FX3 Ver. 7.02` 实机状态 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证与官方约束（`实测事实`） |
| :--- | :---: | :---: | :--- |
| **`[Bulb Timer]`**<br>（`BULB Timer Settings`） | **DORMANT（休眠未暴露）** | — | **`FX3 appFw.so` 实存 13 个符号**（`BKID_APP_setting_bulb_timer`、`BKID_APP_MR_setting_bulb_timer`、`BULB_TIMER_{OFF,ON}`、`N5model20setting_bulb_timer_tE`、`sequence_{set,cancel}_bulb_timer`）且 `_f.uxc` 四语含 `0x630f` `BULB Timer` 与 `0x78b6` `BULB Timer Settings`；**但 `ilc/2210` 全站与 Ver. 7.00/7.02 发布说明 `0` 命中**（该功能实装于 `ILME-FX2` / `ILCE-7RM5` / `ILCE-6700` / `ILCE-7CR`） |
| **Still `[BULB]` 长曝光**<br>（`MODE -> Manual Exposure -> >30"`） | **ACTIVE（活跃）** | 可随 `Shutter Speed` 重置 | `base` `0xe916` `BULB`、`PID_SET_BULB_MODE`、`CAUTION_ID_FACTOR_CAM_SET_BULB_ON_MSG`；**强制要求 `[Mechanical Shutter]`**；在 `[Electronic Shutter]`、`Cont. Shooting`、`Self-timer(Cont)`、`Cont. Bracket`、`Interval Shooting` 下禁用并**临时回退为 `30"`**；禁用 `[Anti-flicker Shoot.]`；`[Long Exposure NR] = On` 时曝光后追加等时长暗帧降噪 |
| **`[D-Range Optimizer]`**<br>（`Exposure/Color -> DRO`） | **ACTIVE（活跃）**（`Auto` 默认 / `Off` / `Lv1..Lv5`） | **Can be reset** | `base` `0xe89c`、`0xea04`、`0xea38..0xe0be`；`BKID_APP_setting_dro` / `BKID_APP_setting_dro_d_range_optimizer`；当 `[Picture Profile] != Off` 强制固定为 `Off`，当 `[HLG Still Image] = On` 禁用 |
| **`[DRO Bracket]`**<br>（`Drive Mode -> Bracket`） | **ACTIVE（活跃）**（`DRO Bracket: Lo` `Lv1/2/3`、`Hi` `Lv1/3/5`） | **Can be reset** | `base` `0xe18f`、`0xe952`、`0xe953`；`BKID_APP_setting_drive_mode_dro_adv_bracket`；连拍 3 张不同 DRO 等级；`[HLG Still Image] = On` 时禁用 |
| **`[Auto HDR]`**<br>（`DRO/Auto HDR` 旧组合菜单） | **DORMANT（休眠未暴露）** | — | **`ilc/2210` 全站 `0` 命中**、`FX3 appFw.so` 无 `auto_hdr` 状态机（仅存 `BKID_APP_extern_menu_hdr_level` / `VAL_HDR_LEVEL_OFF`）；`base.uxc` 中 `0xe5d0` `DRO/Auto HDR`、`0xe49d` `Auto HDR`、`0xe453..0xe459` `Exposure Diff. 4.0..6.0EV`、`0xe7c1` 均属 Alpha 遗留休眠文本；宽动态静态拍由 **`[HLG Still Image]`**（`_f` `0x76c8`, HEIF）替代 |

### 4.2 `[Bulb Timer]` 与 `[Auto HDR]` 工程判定及长曝光实务边界（`实测事实` + `推断`）

1. **为什么不能凭 `appFw.so` 与 `_f.uxc` 存在符号就认为 FX3 支持 `[Bulb Timer]`（`实测事实`）**：
   - 本次实证发现 Sony 多机型共享固件底座在 `FX3 appFw.so` 中同时沉淀了 `BKID_APP_setting_movie_self_timer`（Wave 57 证伪为休眠）与 `BKID_APP_setting_bulb_timer`（Wave 58 证伪为休眠），甚至保留了完整的四语言 UXC 条目（`0x630f` / `0x78b6`）和 C++ model sequence（`N5model20setting_bulb_timer_tE`）。但经官方 `helpguide.sony.net/ilc/2210/v1/en/` 与 Ver. 7.00/7.02 发行说明交叉核验，FX3 产品策略并未激活该菜单项（由更晚上市的 `ILME-FX2` 等机身暴露）。在 FX3 UI 模拟器或设置恢复审计中，**严禁将休眠 `BKID_APP_setting_bulb_timer` 暴露为活跃菜单或可配置状态**。
2. **FX3 超过 30 秒静态曝光的合规路径（`实测事实`）**：
   - 机内仅允许在 `Mechanical Shutter` + 单张/单次自拍下进入手动 `[BULB]`；若需定时超过 30 秒，官方 `ilc/2210` 仅支持**蓝牙遥控器**（第一次按下开始曝光、第二次按下结束）、**Multi/Micro USB 带锁线控**或外部联机控制软件（与 `ILME-FX6` 对比：FX6 纯电影机身完全不支持静态摄影与 `BULB` 快门，`FX6 appFw.so` 中 `VAL_SHUTTER_SPEED_BULB` / `VAL_EXPOSURE_MODE_AUTO_HDR` / `VAL_DRO_LEVEL_*` 全部为纯休眠残存枚举）。

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 角色与实证范围 |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`nflasha15/lib/appFw.so`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_*`、`VAL_*`、`CAUTION_ID_*`、`N5model*` 实机符号与休眠资产边界 |
| `FX6 appFw.so` (`FX6 .../lib/appFw.so`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `ILME-FX6 Ver. 6.01` `VF_SETTING`、`CLIP_FLAG`、`NIGHTSHOT`、`USB_TC_IN`、互斥与休眠对照 |
| `FX3-CX95900_ALLLANG-Backup.bin` (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失备份结构基线（`BK4\x00`） |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | FX3 `hdr_flag=15` 主菜单与提示英文包 |
| `FX3 string_english.uxc` | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | FX3 `hdr_flag=8` 基础菜单与警告英文包 |
| `FX3 string_english_g.uxc` | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | FX3 `hdr_flag=8` 扩展通信与组标签英文包 |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | 简体中文 `_f` 主菜单四语 `resid16` 精确映射 |
| `FX3 string_simplifiedchinese.uxc` / `_g.uxc` | `149,064` / `61,296` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文基础/扩展包 `resid16` 映射（`_g 0x6476` 缺译已标出） |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | 繁体中文 `_f` 主菜单四语 `resid16` 精确映射 |
| `FX3 string_traditionalchinese.uxc` / `_g.uxc` | `151,908` / `61,372` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文基础/扩展包 `resid16` 映射（`_g 0x6476` 缺译已标出） |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | 日文原厂 `_f` 主菜单 `resid16` 精确映射 |
| `FX3 string_japanese.uxc` / `_g.uxc` | `208,564` / `89,428` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日文原厂基础/扩展包 `resid16` 精确映射 |
| `FX6 string_english.uxc` | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | FX6 `VF Setting` / `Wired LAN` / `Gain` / `USB Timecode` 字符包 |
| `FX6 string_english_2.uxc` | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 `Shot Mark 0..9` / `Essence Mark` / `Clip Flag` / `Wired LAN` 互斥字符包 |
| `libWiredLanResource.so` | `36,160` | `f5ee3d70d5961753cef226bec74c15231e489491eddf63210511f57aaebf49e5` | FX3 有线网卡驱动调度（`r8152/r8156/ax88179_178a/mii/usbnet`）与 `eth0` |
| `libNetServiceEther.so` | `114,384` | `203b084190a968c732d09fd45e304c406a32eb664d98626114dcf7f178675375` | FX3 以太网 DHCP/手动 IP 状态机（`WESStartDHCPClient`） |
| `libWlanResource.so` | `56,464` | `76fe66f7c763a452c2986514b3485a62791e7750d52ffa89b31b820e4cb9eb91` | FX3 `ar6000.ko` / `wlan.ko` 与监管域 `ccodeno.txt` / `db.txt` 绑定 |
| `libWlanAdjust.so` | `73,168` | `3dcab55342e741a832bc88fd2cff96e2060d4ab3f4a6b529b9edb18434be8e9d` | FX3 Wi-Fi 射频通道与 SSID/PSK 控制库 |
| `libInfraAirplaneMode.so` | `14,488` | `dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea` | 飞行模式 RF 隔离控制库 |
| `libInfraBluetooth.so` / `LowEnergy.so` | `158,968` / `648,328` | `e49bb8fbb723eef65d4b4e54788c39f57b1cd7ca72285bc02a726ada2ca8ef93` / `2d3d72bd08e1dd2bbff9d6af82af74d5d892f56faf103a6dbcf33be22609966a` | BLE 协议栈与固件加载（`bt_firm.hcd` / `bt_stack.conf`） |
| `cdc_ncm.ko` (`full-v4/usr/kmod/`) | `32,208` | `fce183b98eebbda9bb7954854bdcb717c2da74785c97a08a767afc235628ff70` | CDC-NCM USB-LAN 内核驱动 |
| `r8152.ko` (`full-v4/usr/kmod/`) | `56,264` | `b06d855ff3944c0de7ce4b600c3d44c1b006f64a5360279e6ed8d56aae70a9bf` | Realtek RTL8152/RTL8153 USB-LAN 内核驱动 |
| `asix.ko` / `ax88179_178a.ko` (`full-v4/usr/kmod/`) | `46,592` / `23,848` | `49258835b3220042d06b9ba2e0dde7206f74594f48d210a2b1ac57e11da2fcd3` / `a4f2582b028182d9cfbb42a0d255c75589357cf4ebb19ea38cafafc20f906c76` | ASIX AX8817X / AX88179 USB-LAN 内核驱动（另含 `cdc_ether.ko` / `usbnet.ko` / `ipheth.ko` / `rndis_host.ko`） |

### 5.2 关键菜单项四语言 UXC `resid16` 校验矩阵（`实测事实`）

| 包 / `resid16` | English | 简体中文 | 繁体中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x701f` | `Bright Monitoring` | `亮屏显示` | `亮屏顯示` | `ブライトモニタリング` | 活跃（自定义键独占） |
| `base` `0xe44b` | `Monitor Brightness` | `显示屏亮度` | `螢幕亮度` | `モニター明るさ` | 活跃（`Manual -2..+2` / `Sunny Weather`） |
| `base` `0xe1da` | `Sunny Weather` | `晴朗天气` | `晴朗天氣` | `屋外晴天` | 活跃（另有 `_f` `0x7a61`） |
| `_f` `0x628b` / `0x628a` | `Add Shot Mark1` / `Add Shot Mark2` | `添加Shot Mark1` / `2` | `新增Shot Mark1` / `2` | `Shot Mark1追加` / `2` | 活跃（录制中自定义键） |
| `_f` `0x6143` / `0x6142` | `Add/Delete Shot Mark1` / `2` | `添加/删除Shot Mark1` / `2` | `新增/刪除Shot Mark1` / `2` | `Shot Mark1追加/削除` / `2` | 活跃（回放自定义键） |
| `_f` `0x76cf` / `0x79cb` / `0x6ffb` / `0x7818` | `Shot Mark Only` / `1 Only` / `2 Only` / `No Shot Mark` | `仅Shot Mark` / `仅Shot Mark1` / `2` / `无Shot Mark` | `僅Shot Mark` / `1` / `2` / `無Shot Mark` | `Shot Markのみ` / `1のみ` / `2のみ` / `なし` | 活跃（Image Jump） |
| `_f` `0x6856` | `Photo Capture` | `照片捕获` | `照片攝取` | `動画から静止画作成` | 活跃（Playback Edit） |
| `_f` `0x747a` / `_g` `0x6118` | `Create Divider Frame` / `Divider Frame` | `创建分隔帧` / `分隔帧` | `建立分格線框架` / `分格線框架` | `区切り画像作成` / `区切り画像` | 活跃（自定义键） |
| `_f` `0x7005` / `0x6e38` / `0x6c2a` / `0x74a9` | `Cut to 15/30/60 seconds` & Shot Mark center cut | `剪切为15/30/60秒` | `剪切至15/30/60秒` | `15/30/60秒にカット` | **休眠**（无活跃 ELF 状态机） |
| `_f` `0x6eb5` / `_g` `0x6398` | `Wired LAN Setting` / `Wired LAN` | `有线LAN设置` / `有线LAN` | `有線LAN設定` / `有線LAN` | `有線LAN設定` / `有線LAN` | 活跃 |
| `_f` `0x7d2a` | `USB-LAN Cnct. Launch` | `启动时USB-LAN连接` | `啟動時USB-LAN連線` | `起動時のUSB-LAN接続` | 活跃（Ver. 7.00+, 默认 `Off`） |
| `_f` `0x66c3` / `0x792a` / `0x6953` | `Wi-Fi Frequency Band` / `5GHz` / `5GHz band: Indoor use only` | `Wi-Fi频带` / `5GHz` / *英文原串* | `Wi-Fi頻帶` / `5GHz` / *英文原串* | `Wi-Fi周波数帯` / `5GHz` / `屋外で使用できません` | 活跃（`WW728473`） |
| `base` `0xe407` / `0xea7e` | `WPA3` / `WPA2` | `WPA3` / `WPA2` | `WPA3` / `WPA2` | `WPA3` / `WPA2` | 活跃（Ver. 7.00+ 移除 WEP/WPA） |
| `_f` `0x723c` / `0x6807` | `Bluetooth Function` / `Bluetooth Rmt Ctrl` | `Bluetooth功能` / `Bluetooth遥控` | `Bluetooth功能` / `Bluetooth遙控` | `Bluetooth機能` / `Bluetoothリモコン` | 活跃（默认均 `Off`） |
| `_f` `0x6b05` / `0x6df9` | `Airplane Mode` | `飞行模式` | `飛航模式` | `飛行機モード` / `機内モード` | 活跃（重置保留 `On`） |
| `_f` `0x6b79` / `0x7313` / `0x72af` | `Time Code Make` / `Run` / `Output` | `Time Code Make/Run/输出` | `Time Code Make/Run/輸出` | `Time Code Make/Run/出力` | 活跃（有线 `VMC-BNCM1` + HDMI） |
| `_f` `0x630f` / `0x78b6` | `BULB Timer` / `BULB Timer Settings` | `BULB定时器` / `设置` | `BULB計時器` / `設定` | `BULBタイマー` / `設定` | **休眠**（FX3 Ver. 7.02 未开放） |
| `base` `0xe916` | `BULB` | `BULB` | `BULB` | `BULB` | 活跃（Still `Mechanical Shutter`） |
| `base` `0xe89c` / `0xe18f` | `D-Range Optimizer` / `DRO Bracket` | `动态范围优化` / `DRO阶段曝光` | `動態範圍最佳化` / `DRO包圍式曝光` | `Dﾚﾝｼﾞｵﾌﾟﾃｨﾏｲｻﾞｰ` / `DROブラケット` | 活跃（Still/DRO） |
| `base` `0xe5d0` / `0xe49d` | `DRO/Auto HDR` / `Auto HDR` | `DRO/自动HDR` / `自动HDR` | `DRO/自動 HDR` / `自動HDR` | `DRO/オートHDR` / `オートHDR` | **休眠**（由 `_f` `0x76c8` `HLG Still Image` 替代） |
