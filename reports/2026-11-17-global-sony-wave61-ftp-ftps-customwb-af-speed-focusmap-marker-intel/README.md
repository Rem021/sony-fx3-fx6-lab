# 全球 Sony 实机情报 Wave 61（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[FTP Transfer Func.]` `FTP`/`FTPS` Explicit TLS vs 休眠 `SFTP` 核实、9 服务器槽位与 `Slot 1` `EROFS=30` 陷阱、`[CustomWB]`/`[Priority Set in AWB]`/`[Shutter AWB Lock]`/`[Shockless WB]` vs `Cine EI` 与 `FX6` `ATW`/`Memory A–H`、Movie `[AF Transition Speed]`/`[AF Subj. Shift Sens.]`/`[AF Assist]`/`[Focus Map]` 实证纠偏，以及 `[Marker Display]` 15 比例与 4 色 `[Peaking Display]` vs `FX6` `User Box`）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *White Balance / Custom Setup / Priority Set in AWB / Shutter AWB Lock / Shockless WB / Log Shooting Setting / AF Transition Speed / AF Subj. Shift Sensitivity / AF Assist / Marker Display / Peaking Display / Save/Load Settings / List of default setting values*）
  - 官方 Sony `ILME-FX3` FTP Help Guide（`helpguide.sony.net/di/ftp_2210/v1/en/` —— *Server Setting / FTP Transfer / Auto FTP Transfer / RAW+J/H Transfer Target / Directory Hierarchy / FTP Power Save / Import Root Certificate / USB-LAN Connection / Airplane Mode*）
  - 官方 Sony *Monitor & Control* Help Guide（*Supported Cameras / Shooting Assist Functions [Focus map] / Focus / Connecting using a USB Cable / HDMI/UVC*）及 Sony `ILME-FX3` `Ver. 2.00 / 3.00 / 6.00 / 7.00 / 7.02` 固件发布说明
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0）与 `ILME-FX6` Security Precautions Help Guide（`5-075-080-11(1)` / FTPES 算法规范）
  - 并严格对照 `os.O_RDONLY` 本地 donor 二进制实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so` 与 `FX6 string_english.uxc` / `_2.uxc`；参见 [Wave 60 里程碑报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h376-global-sony-wave61-ftp-ftps-customwb-af-speed-focusmap-marker-intel/reports/2026-11-17-global-sony-wave60-milestone-rec-media-auto-switch-proxy-cloud-mymenu-intel/README.md)）。
- **硬件安全态势**：严格只读本地 donor 分析（`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、SHA-256 账本与官方文档条目）与 **`推断`**（含 `Slot 1` Tier-0 保险库 `EROFS=30` 防火墙与 Zero-RF 台架护栏）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[FTP Transfer Func.]`：`FTP`/`FTPS` Explicit TLS vs 零 `SFTP`、9 槽位、休眠 `Transfer JPEG Size`、`Slot 1` `AVF_INFO` 写危害与 `USB-LAN` 绕过飞行模式）**：
   - **实测事实（协议边界与 9 服务器槽位）**：`ILME-FX3 Ver. 7.02` 提供 **`Server 1`..`Server 9` 共 9 个 FTP 服务器槽位**（`BKID_APP_ftp_server_settings_*0..8`），支持明文 **`FTP`** 与 **`FTPS` Explicit TLS（`FTPES`）**（`SET_SERVER_SECURE_PROTOCOL_{OFF,ON}`，`_f 0x6553` `'Connects with FTPES.'`），**仅支持被动模式（Passive Mode）**（`FX3 appFw.so` 中 `passive_mode` 与 `sftp` 均为 **`0` 命中**；`_f 0x68d9`/`0x6ed3` 为跨机型休眠字符串）。`di/ftp_2210` 网页中出现的 `"SFTP"` 字样**仅存在**于 Sony 通用加密套件文档链接 `helpguide.sony.net/di/sftp/v1/` 中，FX3 与 FX6 实机菜单均不向用户暴露 SSH-SFTP（尽管 `FX6 appFw.so` 内部残留未暴露的 `SET_SERVER_SECURE_PROTOCOL_ON_SFTP` 枚举）。
   - **实测事实（休眠字符串 `[Transfer JPEG Size]`/`[Transfer HEIF Size]`）**：`_f 0x6aed` (`'Transfer JPEG Size'`) 与 `_f 0x63dd` (`'Transfer HEIF Size'`) 在 FX3 UXC 中存在，但在 `FX3 appFw.so` 中为 **`0` 命中**且不存在于 `di/ftp_2210` FX3 菜单中，属跨机型休眠字符串（仅在支持同拍异尺寸分选的机型暴露）。
   - **实测事实 + 推断（`Slot 1` Tier-0 保险库危害与 Zero-RF `USB-LAN` 漏洞）**：`FX3 base.uxc 0x0a13`（`'Image Database File error.\nFTP transfer results will be reset if recovered. Recover?'`）结合 `FX3 appFw.so` 的 `CONTENT_INFO_FTP_TRANS_STAT_{COMPLETE,FAILED,NOT_TARGET,RESERVED}`、`save_ftp_transfer_list_to_media` 及 `PRM_HAITA_ftp_display_result_media_*_slot1`，证明 FTP 传输状态记录与存储卡 `AVF_INFO` 影像数据库强耦合；且 `[Import Root Certificate]` 强制从 **Slot 1 根目录读取 `cacert.pem`**（最大 1 MB）。任何指向 `Slot 1` 的 FTP 读取/写状态/DB 修复请求在 Tier-0 只读保险库下必须 fail-closed 返回 **`EROFS (errno 30)`**。同时 **`[Airplane Mode] = On` 仅阻断 Wi-Fi FTP，仍放行 `USB-LAN` 有线网卡 FTP**，Zero-RF 台架必须同步断离 `[USB-LAN/Tethering]`。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18`）使用 `Network > File Transfer`，用户界面暴露 `Server Settings1..3`（外加 `Ci`/`NCM`/`Relay`；ELF 保留 `1..16`），支持 **`Passive Mode On/Off`（含 Active Mode）**，根证书名为 **`certification.pem`** 且从 **Slot B** 载入各服务器配置，并独有 **`Auto Upload (Proxy): Chunk`** 边录边传（占用 Slot B 时硬互斥 `Simul Rec` 与 `Relay Rec`）。

2. **子系统 2（白平衡深度解析：`Custom 1..3`、`[Priority Set in AWB]`、`[Shutter AWB Lock]`、`[Shockless WB]` 与 `Cine EI` 锁定）**：
   - **实测事实**：`FX3` 在 `MENU -> (Exposure/Color) -> [White Balance]` 提供 `Auto`（默认）、`Auto: Ambience`、`Auto: White`、预设光源、`C.Temp./Filter`（**`2500K`–`9900K`**，ELF `COLOR_TEMP_COLOR_FILTER_2500K`..`9900K` 实证）及 `Custom 1..3`。`[Priority Set in AWB]`（`Standard` 默认/`Ambience`/`White`）跨 Still/Movie 生效且支持 `[Camera Settings Reset]`；**`[Shutter AWB Lock]`（仅 Still，`Shut. Halfway` / `Cont. Shooting` / `Off` 默认）抗 `[Camera Settings Reset]`**（须 `[Initialize]`）；**`[Shockless WB]`（Movie/S&Q，`Off` / `1 (Fast)` 默认 / `2` / `3 (Slow)`）支持 `[Camera Settings Reset]`**，但直接调节 `C.Temp./Filter` 与 `A-B`/`G-M` 微调会绕过平滑立即生效。
   - **实测事实**：当 `[Log Shooting] != Off`（`Flexible ISO`/`Cine EI`/`Cine EI Quick`）或 Picture Profile 设成 `S-Log3` / `PPLUT1..4` 时，执行 `[Custom Setup]` 采白可能报 `_f 0x63ac` / `base 0x0220`（`Custom WB Error`）；进入 `Cine EI` / `Cine EI Quick` 后，`[Auto]` 与 `[Underwater Auto]` 被强制禁用（仅留预设、`C.Temp./Filter`、`Custom 1..3`）。
   - **实测事实（FX6 对比）**：`ILME-FX6` 配备物理三档 **`WHT BAL` 开关（`PRST` / `A` / `B`）** + **`Memory A..H`**（8 组，`VAL_setting_white_select_WHITE_SELECT_MEMORY_{A..H}`）+ 预设 `3200K/4300K/5600K/6300K` + **`ATW`（`Auto Tracing White Balance`，`ATW Speed 1..5` + `ATW Hold`）**；与 FX3 相同，`Cine EI` / `Cine EI Quick` 下 `ATW` 同样被锁定禁用。

3. **子系统 3（Movie AF 动态参数与 `[Focus Map]` 重大实证纠偏）**：
   - **实测事实（CRITICAL 纠偏：`FX6` 的 `AF Subj. Shift Sens.` 也是 `1..5`，而非 `1..7`！）**：`ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 在两条动态 AF 刻度上**完全一致**——`[AF Transition Speed]` 为 **`1 (Slow)`..`7 (Fast)`**（FX3 默认 `5`），而 **`[AF Subj. Shift Sensitivity]` 两者均严格为 `1 (Locked on)`..`5 (Responsive)`**（FX3 默认 `5 (Responsive)`；`FX6 appFw.so` 实测仅存在 `MOVIE_AF_SUBJ_SHIFT_SENS_1_LOCKED_ON` 至 `5_RESPONSICE`，`6`/`7` 均为 **`0` 命中**，`FX6 string_english.uxc` `0x22f5`/`0x22f7` 亦印证）。FX3 两者均可由 `[Camera Settings Reset]` 复位。
   - **实测事实**：`[AF Assist]`（`BKID_APP_setting_af_assist`，默认 `Off`，可由 `[Camera Settings Reset]` 复位）允许在 Movie/S&Q `AF-C` 期间转动镜头对焦环手动接管并在停转后交回 AF 锁定新目标，但不兼容 `SELP1650` / `SEL18200LE`。
   - **实测事实（CRITICAL 纠偏：FX3 没有机身内 `[Focus Map]`，且非 `Ver. 2.00` 引入！）**：`ILME-FX3` 从未在机身屏幕上提供 `[Focus Map]` 菜单（`FX3 appFw.so` 中 `BKID_APP_USER_MENU_FOCUS_MAP` 与 `ASSIGNABLE_SWITCH_FOCUS_MAP` 均为 `0` 命中，`ilc/2210` 机身菜单无此项；`_f 0x61f9` 为多机型共用字符串）。FX3 是在 **`Ver. 6.00`**（2024 年 9 月，延续至 `Ver. 7.02`）才通过 `to_remote_event_focus_map` / `sequence_notify_focus_map` 遥测管线**仅面向外部 *Monitor & Control* App（Ver. 2.1.0+）开放 `[Focus Map]`**；受限条件包括 **`>= 150 fps`（即 200/240fps S&Q，注意 100p/119.88p 小于 150 fps 不在此列）**、回放控制、开启 `Auto Framing`、非 PDAF 镜头/转接环/无镜头、USB 有线远程连接或 UVC（FX3 本身不支持 UVC）。对比 `ILME-FX6 Ver. 6.01` 则具备**机身原生 `Focus Map`**（同时受 `<= 6 fps` 下限与 `>= 150 fps` 上限及 `HDMI RAW`/`Focus Magnifier`/`Digital Extender` 互斥）。

4. **子系统 4（电影辅助 `[Marker Display]` 15 种比例与 4 色 `[Peaking Display]` vs `FX6` `User Box`）**：
   - **实测事实**：`ILME-FX3 Ver. 7.02` 的 `[Marker Display]`（`Shooting -> [Marker Display]`，仅 Movie & S&Q 生效）5 个子项（`Marker Display` / `Center Marker` / `Aspect Marker` / `Safety Zone` [`Off`/`80%`/`90%`] / `Guideframe` [`Off`/`On`]）以及 `[Peaking Display]`（`Focus -> [Peaking Display]`，Still/Movie/S&Q 均生效）3 个子项（`Peaking Display` / `Peaking Level` [`High`/`Mid`/`Low`] / `Peaking Color` [`Red`/`Yellow`/`Blue`/`White`]）**全部 8 项均抗 `[Camera Settings Reset]`（`Not available`，须 `[Initialize]`）**。
   - **实测事实**：FX3 的 `[Aspect Marker]` 在 `FX3 appFw.so`（`VAL_setting_marker_display_aspect_ASPECT_*`）与 `ilc/2210` 中全部激活 **`Off` + 15 种画幅比例（共 16 态）**：`9:16`、`4:5`、`1:1`、`4:3`、`13:9`、`14:9`、`15:9`、`16:9` *(Ver. 3.00+ 新增)*、`17:9`、`1.66:1`、`1.85:1`、`1.91:1`、`2:1`、`2.35:1`、`2.39:1`（无任何休眠比例）。`Guideframe` 在机身仅单一网格开关，而 `VAL_um_guide_frame_*`（`RULE_OF_3RD_GRID`/`SQUARE_GRID`/`DIAG_SQUARE_GRID`）留作外部/UM 扩展；两者（`Marker Display` 与 `Peaking Display`）均**严格仅限机身监看屏显示，绝不随 HDMI Clean/Info 输出到外录机或外部监视器**，且 `Marker Display` 在开启 `[Focus Magnifier]` 时自动隐藏。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01` 在 `Monitoring > Marker` 提供 `Aspect Mask`（遮罩透明度 `0..15` 默认 `12`）、自定义比例 `Custom`（`BKID_APP_MARKER_ASPECT_CUSTOM_RATIO_{WIDTH,HEIGHT}`）、`Aspect Safety Area`（`80%/90%/92.5%/95%`）以及可精确设定像素坐标与宽高的 **`User Box`**（`Width 3..479`, `Height 3..269`, `H Pos -476..+476`, `V Pos -266..+266`，由 `PRM_HAITA_setting_user_box_*` 交叉限位）；峰值颜色为 **`B&W` / `Red` / `Yellow` / `Blue`**（用 `B&W` 取代 FX3 的 `White`）。

---

## 1. 子系统 1：`[FTP Transfer Func.]`（`FTP`/`FTPS` vs 休眠 `SFTP`、9 槽位、`Slot 1` 危害与 Zero-RF `USB-LAN`）

### 1.1 `ILME-FX3 Ver. 7.02` FTP 全量配置矩阵与 Reset 边界（`实测事实`）

| 菜单路径 / 项（`di/ftp_2210` + `ilc/2210`） | `FX3 Ver. 7.02` 真值与默认设置 | Reset 边界 | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[FTP Function]`**<br>(`Network -> FTP Transfer -> FTP Transfer Func.`) | **`Off`**（**默认**） / `On`；与 `[Cloud Connection] = On` 互斥 | **`Reset Network Set.`** / `[Initialize]`<br>*(`Camera Settings Reset` 无效)* | `_f 0x7287` / `0x6317`；`BKID_APP_setting_ftp_function`；`CLOUD_CONNECTION_ON_FTP_OFF` |
| **`[Server Setting]` (`Server 1..9`)** | **共 `9` 个服务器槽位**（默认 `Server 1`）；每槽含 `Display Name` / `Destination Settings`（`Host Name` / `Secure Protocol` / `Root Certificate Error` / `Port`）/ `Directory Settings` / `User Info` | **`Reset Network Set.`** / `[Initialize]` | `_f 0x6442` / `0x6305..0x630b`, `0x72f4` (`Server 8`), `0x630d` (`Server 9`)；`BKID_APP_ftp_server_settings_*0..8`（共 10 个子键 × 9 槽，无 `Passive Mode` 键） |
| **`Secure Protocol` & 协议族核实** | **`Off`（明文 FTP）** / **`On`（`FTPS` Explicit TLS / `FTPES`）**；**无 `SFTP`**；**仅支持 Passive Mode**（不支持 Active Mode） | **`Reset Network Set.`** / `[Initialize]` | `_f 0x60dd` / `_f 0x6553` `'Connects with FTPES.'`；`VAL_setting_set_server_secure_protocol_SET_SERVER_SECURE_PROTOCOL_{OFF,ON}`；`sftp`、`ftpes`、`passive_mode` 在 `FX3 appFw.so` 均 **`0` 命中** |
| **`Root Certificate Error`** & **`[Import Root Certificate]`** | `Does Not Connect`（推荐） / `Connect`（强制连并警告）；根证书须以 PEM 格式存为 **`cacert.pem`**（≤ 1 MB）置于 **Slot 1 根目录**后从 `[Network Option] -> [Import Root Certificate] -> [FTP Function]` 导入 | **`Reset Network Set.`** / `[Initialize]`（同步清空已导入根证书） | `_f 0x65f2` / `0x65a3` / `0x7940`；`BKID_APP_ftp_server_settings_root_certification_error{0..8}`；`REMOTE_SETTING_FTP_ROOT_CERTIFICATE_ERROR_BEHAVIOR_FORCE_{CONNECT,NOT_CONNECT}` |
| **`[Directory Hierarchy]`** | **`Standard`**（直接落入 `Specify Directory` [最长 128 字符]）/ **`Same as in Camera`**（复刻卡目录：Slot 1 -> `A/...`、Slot 2 -> `B/...`）；同名冲突策略：`Does Not Overwrite` / `Overwrite` | **`Reset Network Set.`** / `[Initialize]` | `_f 0x6e7e` / `0x76e6` / `0x6012` / `0x684a` / `0x75ca` / `0x64d9`；`BKID_APP_ftp_server_settings_directory_hierarchy{0..8}`；`SET_SERVER_DIRECTORY_HIERARCHY_{STANDARD,SAME_AS_IN_CAMERA}` |
| **`[Auto FTP Transfer]`** & **`[Auto FTP Target]`** | `Off`（默认） / `On`（断线恢复后自动续传，目标锁定当前 `[Recording Media]` 槽位）；Target：`Still Image`（全部） / `Movie`（`All` / `Only Shot Mark`） | **`Reset Network Set.`** / `[Initialize]` | `_f 0x7b27` / `0x6d48`；`BKID_APP_setting_auto_ftp_transfer`；`BKID_APP_setting_auto_ftp_transfer_target_movie`；`AUTO_FTP_TRANSFER_TARGET_MOVIE_{ALL,MOVIE_SHOT_MARK}` |
| **`[FTP Transfer]`（批量传输筛选）** | 基于 `[Select Playback Media]` 选定槽位：`Target Group`（`This Date` / `This Folder` / `This Media`）、`Still Images/Movies`、`Target Img (Rating)`（`1..5`/`Off`）、`Target Movie (Shot Mark)`（`All`/`Only Shot Mark Mov.`）、`Target Img (Protect)`（`All`/`Only Protected Img.`）、**`Trgt. Img (Clip Flag)`**（Ver. 7.00+：`OK`/`NG`/`KEEP`/`Off`）、`Transfer Status`（`All`/`Only Non-transfer`/`Only Failed Transfer`） | **`Reset Network Set.`** / `[Initialize]` | `_f 0x62fc` / `0x69a4` / `0x694a` / `0x794b` / `0x7d31` / `0x6a2e` / `0x6026` / `0x6030`；`BKID_APP_setting_ftp_transfer_target_group` / `target_image` / `still_movie_target_image` / `func_target_img_shot_mark` / `transfer_status`；`BKID_APP_is_valid_ftp_transfer_target_image_clip_flag_{ok,ng,keep,off}` |
| **`[RAW+J/H Transfer Target]`** & **Movie 传输目标** | Still：`JPEG & HEIF`（默认） / `RAW` / `RAW+J & RAW+H`；Movie：`Proxy Only`（默认） / `Original Only` / `Proxy & Original` | **`Reset Network Set.`** / `[Initialize]` | `_f 0x6bd5` / `0x7263` / `0x645d` / `0x6f63` / `0x6381`；`EVENT_REMOTE_FTP_GROUP_FTP_TRANSFER_FUNC_RAW_J_H_TRANS_TRGT`；`VAL_setting_send_to_smartphone_function_raw_j_h_trans_trgt_*` |
| **`[Transfer JPEG Size]`** / **`[Transfer HEIF Size]`** | **FX3 实机未暴露（不适用）** | — | `_f 0x6aed` (`'Transfer JPEG Size'`) 与 `_f 0x63dd` (`'Transfer HEIF Size'`) 在 `FX3 appFw.so` **`0` 命中**，属跨机型休眠字符串 |
| **`[FTP Power Save]`** | **`Off`**（默认，长连接） / **`On`**（闲置超时断开网络/停止 Wi-Fi 发射；切服务器、切有线/无线 LAN、改 LAN 配置、触发 `[FTP Transfer]`/`[Auto FTP Transfer]` 或关 `[FTP Function]` 时重连） | **`Reset Network Set.`** / `[Initialize]` | `_f 0x6a5f`；`BKID_APP_setting_ftp_power_save`；`VAL_setting_ftp_power_save_FTP_POWER_SAVE_{OFF,ON}`；`INFRA_NOTIFY_FTP_POWER_SAVE_TIMER_EXPIRED` |

### 1.2 休眠 `SFTP` 与休眠 `[Transfer JPEG Size]` 证据链核查（`实测事实`）

1. **为什么网络上常误传 FX3 支持 `SFTP`**：Sony 官方 `di/ftp_2210` 与 `5-075-080-11`（FX6 安全说明）在解释推荐与弃用的 TLS 加密套件时，正文内嵌了统一域名帮助链接 `https://helpguide.sony.net/di/sftp/v1/h_zz/index.html`（Sony 用 `di/sftp` 命名 **"Secure FTP"** 通用白皮书目录，实际指 **FTPES / FTPS Explicit TLS**）。
2. **二进制实证**：在 `FX3 appFw.so`（79,015,712 字节）全文本搜索 `sftp` 为 **`0` 命中**；FTP 服务器安全开关仅存在两态 `SET_SERVER_SECURE_PROTOCOL_{OFF,ON}`，对应的 UI 说明 `_f 0x6553` 明确写作 `'Connects with FTPES.'`（简中 `'连接FTPES。'`）。因此 **FX3 Ver. 7.02 仅支持 FTP 与 FTPES（FTPS Explicit TLS），不支持 SSH-SFTP，也不支持 Implicit FTPS（990 端口隐式模式）**。
3. **对比 `FX6 appFw.so`**：`FX6 appFw.so` 内部确实包含 `SET_SERVER_SECURE_PROTOCOL_ON_FTPES` 与 `SET_SERVER_SECURE_PROTOCOL_ON_SFTP` 两组枚举符号，但 `FX6 string_english.uxc` / `_2.uxc`、FX6 `5-024-458-18` 操作手册及 `5-075-080-11` 均**只暴露并记录了 `FTPES`（`Using Secure Protocol On/Off`）**，未向用户开放 `SFTP`。

### 1.3 `Slot 1` `AVF_INFO` 数据库写危害（`EROFS=30`）与 Zero-RF `USB-LAN` 陷阱（`实测事实` + `推断`）

1. **FTP 传输状态与 `AVF_INFO` 数据库耦合实证（`实测事实`）**：
   - `FX3 base.uxc 0x0a13` 存在明确告警：`'Image Database File error.\nFTP transfer results will be reset if recovered. Recover?'`（简中：`'影像数据库文件错误。\n修复后FTP传输结果将重置。要修复吗？'`），且 `base 0x09b7` 明确给出 Slot 1 并发互斥提示 `'FTP Transferring...\nCannot be executed.\nSlot 1'`。
   - `FX3 appFw.so` 存在完整传输状态写回符号：`VAL_ftp_transfer_for_exclusion_CONTENT_INFO_FTP_TRANS_STAT_{COMPLETE,FAILED,NOT_TARGET,RESERVED}`、`save_ftp_transfer_list_to_media`、`write_ftp_setting`，以及卡状态互斥表 `PRM_HAITA_ftp_display_result_media_media_{locked,read_only,error,...}_state_slot1`。
   - 此外，`di/ftp_2210` 明确规定写保护（Lock 开关锁定）的存储卡不可执行 FTP 传输记录更新，且 `[Import Root Certificate]` 仅从 **Slot 1** 根目录读取 `cacert.pem`。
2. **Tier-0 保险库安全推论（`推断`）**：
   - 若将承载 Tier-0 只读保险库镜像的 **`Slot 1`** 用作 FTP 源盘或回放盘，当固件尝试向 `Slot 1` 更新 `CONTENT_INFO_FTP_TRANS_STAT`、调用 `save_ftp_transfer_list_to_media` 或响应 `AVF_INFO` 修复（`0x0a13`/`0x035e`）时，底层扇区将面临元信息改写风险。Stage-B 存储防火墙必须对 `Slot 1` 任何非只读/DB 写入路径严格 fail-closed 返回 **`EROFS (errno 30)`**（并确保 `cacert.pem` 导入或证书校验只在隔离测试或只读映射下进行）。
3. **Zero-RF 漏洞：`[Airplane Mode] = On` 不阻断 `USB-LAN`（`实测事实` + `推断`）**：
   - `di/ftp_2210`（*USB-LAN Connection*）明确记载：**即使 `[Airplane Mode]` 设为 `[On]`，仍可通过 Type-C `USB-LAN` 有线转换适配器执行 FTP 传输**（此时相机仅禁用 Wi-Fi 与蓝牙；`FX3 appFw.so` 对应存在 `VAL_HAITA_setting_ftp_function_setting_ftp_connect_method_*_USB_ETHER` 与 `VAL_ftp_airplane_mode_state_*`）。
   - **台架规程（`推断`）**：Zero-RF 测试环境除了设置 `Airplane Mode = On` 与 `FTP Function = Off` 外，必须物理/电气断开或软件禁用 `[USB-LAN/Tethering]`，防止有线网卡桥接意外泄露测试素材或访问外部 FTP 服务器。

### 1.4 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` FTP / File Transfer 对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`di/ftp_2210`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` pp. 76–78 + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **菜单位置与服务器槽位** | `Network -> [FTP Transfer] -> [FTP Transfer Func.]`；**`Server 1..9`**（9 槽位） | `Network > File Transfer`；UI 暴露 **`Server Settings1..3`**（+ `Ci` / `NCM` / `Relay`；ELF 底层支持 `1..16`） |
| **传输模式（Passive/Active）** | **仅 Passive Mode**（不支持 Active Mode） | 支持 **`Passive Mode On / Off`**（可选 **Active Mode**） |
| **加密协议与根证书名** | `FTP` & **`FTPES` (`FTPS` Explicit TLS)**，无 `SFTP`；根证书 **`cacert.pem`** 从 **Slot 1** 导入 `[Import Root Certificate]` | `FTP` & **`FTPES` (`FTPS` Explicit TLS)**（`Using Secure Protocol On/Off`），UI 无 `SFTP`；根证书 **`certification.pem`** 从 **Slot B** 按服务器 `Load/Clear` |
| **边录边传与 Proxy 分段** | `[Auto FTP Transfer]`（随 `[Recording Media]`；片段完结后传输，无 Chunk 分段） | `Auto Upload` / **`Auto Upload (Proxy)`**（支持 **`Chunk`** 边录边传，占用 Slot B 时硬互斥 `Simul Rec` 与 `Relay Rec`） |

---

## 2. 子系统 2：白平衡深度解析（`Custom 1..3`、`[Priority Set in AWB]`、`[Shutter AWB Lock]`、`[Shockless WB]` 与 `Cine EI`）

### 2.1 `ILME-FX3 Ver. 7.02` 白平衡全量真值表与 Reset 边界（`实测事实`）

| 菜单项（`Shooting -> Exposure/Color -> [White Balance]`） | `FX3 Ver. 7.02` 选项、范围与出厂默认 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[White Balance]`（活动模式）** | **`Auto`**（**默认**）、`Auto: Ambience`、`Auto: White`、`Daylight`、`Shade`、`Cloudy`、`Incandescent`、`Fluorescent`（4 档）、`Flash`（仅 Still）、`Underwater Auto`、**`C.Temp./Filter`**（**`2500K`–`9900K`**，步进 100K，后拨盘直调）、**`Custom 1..3`**（+ `Custom Setup`） | **Can be reset**<br>*（活动模式复位回 `Auto`）* | `_f 0x73ee` / `0x6035` / `base 0x079d..0x079c`；`BKID_APP_setting_white_balance_{still,movie}`；`VAL_white_balance_color_temperature_color_temp_color_filter_COLOR_TEMP_COLOR_FILTER_{2500K..9900K}`；`VAL_setting_white_balance_WHITE_BALANCE_CUSTOM_{1,2,3}` |
| **`Custom 1..3`（微调坐标与 `Log`/`S-Log3` 采集告警）** | 右方向键进入二维微调网格；支持在 `A-B`（Amber–Blue）与 `G-M`（Green–Magenta）轴微调（`base.uxc` 含小数步进模板 `${v1}.${v2}`，现代 Sony Alpha/FX 网格为 `A7–B7` [0.5 步/29 级] × `G7–M7` [0.25 步/57 级]） | `Custom 1..3` **不可写入 `[Save/Load Settings]`（`CAMSET*.DAT`）**；`[Initialize]` 清空全部 | `_f 0x63ac` `'Capturing of the custom WB failed.'`；`base 0x002c` `'Custom Setup'` / `0x0220` `'Custom WB Error'`；`base 0x034d`/`0x05a5`/`0x09be` (`A-B: ${v1}.${v2} G-M: ${v3}.${v4}`)；`BKID_APP_preserved_white_balance_adjustment_gm_custom_{1..3}` |
| **`[Priority Set in AWB]`**（Still / Movie 共用） | **`Standard`**（**默认**） / `Ambience` / `White` | **Can be reset** | `_f 0x67a7` / `0x749f` / `0x6541`；`BKID_APP_setting_priority_set_in_awb`；`VAL_setting_priority_set_in_awb_PRIORITY_SET_IN_AWB_{STANDARD,AMBIENCE,WHITE}` |
| **`[Shutter AWB Lock]`**（**仅 Still**） | `Shut. Halfway`（Help Guide 称 `Shutter Half Press`） / `Cont. Shooting` / **`Off`**（**默认**）<br>*注：Movie 锁定 AWB 须绑定自定义键 `[AWB Lock Hold]` / `[AWB Lock Toggle]`* | **Not available**<br>*（抗 Reset，须 `[Initialize]`）* | `_f 0x66db` / `0x6373` / `0x6a32`；`BKID_APP_setting_stl_awb_lock_with_shutter`；`VAL_setting_stl_awb_lock_with_shutter_STL_AWB_LOCK_WITH_SHUTTER_{AWB_LOCK_W_S1,AWB_LOCK_DURING_CONT_SHOOTING,DO_NOT_LOCK_W_SHUTTER}`；`PRM_HAITA_hold_awb_lock_state_still` |
| **`[Shockless WB]`**（**仅 Movie / S&Q**） | `Off` / **`1 (Fast)`**（**默认**） / `2` / `3 (Slow)`<br>*（直接调整 `C.Temp./Filter` 与 `A-B`/`G-M` 微调不经平滑，0 延迟生效）* | **Can be reset** | `_f 0x62fe` / `0x6649` / `0x6ef1`；`BKID_APP_setting_movie_shockless_wb`；`MOVIE_SHOCKLESS_WB_{OFF,1,2,3}` |

### 2.2 `[Custom Setup]` 采白失败机制、`Cine EI` 禁用边界与 Reset 细则（`实测事实` + `推断`）

1. **Log Shooting / S-Log3 / PPLUT 下的 `[Custom Setup]` 报错规律（`实测事实`）**：
   - `ilc/2210`（*Log Shooting Setting* 与 *Picture Profile*）明确提示：当 **`[Log Shooting]` 不为 `[Off]`**（包括 `Flexible ISO`、`Cine EI`、`Cine EI Quick`），或 Picture Profile 启用了 **`[S-Log3]`** 或 **`PPLUT1`–`PPLUT4`** 时，使用 `[Custom Setup]` 对白卡采白**可能触发采白失败报错**（屏幕显示橙色告警 `_f 0x63ac` / `base 0x0220` `'Custom WB Error'`）。Sony 官方推荐流程为：临时切回 `Log Shooting = Off`（或非 S-Log3/PPLUT 伽马）完成采白后，再切换回目标 Log/PP 配置。
2. **`Cine EI` 与 `Cine EI Quick` 的白平衡锁定（`实测事实`）**：
   - 依据 `ilc/2210`（*White Balance*）：进入 `[Log Shooting] = Cine EI` 或 `Cine EI Quick` 时，**`[Auto]` 与 `[Underwater Auto]` 被强制禁用**（不可选）；操作员只能使用固定色温预设（如日光/白炽灯）、`C.Temp./Filter`（`2500K–9900K`）或预先测得的 `Custom 1..3`。
3. **`[Camera Settings Reset]` 对 `Custom 1..3` 内部槽位与活动模式的区别（`实测事实` + `推断`）**：
   - **实测事实**：`[Camera Settings Reset]` 会将活动 `[White Balance]` 复位为 `Auto`，并将 `[Priority Set in AWB]` 与 `[Shockless WB]` 复位回默认值（`Standard` / `1 (Fast)`），但**不会复位 `[Shutter AWB Lock]`**（`Not available`）；同时 `[Save/Load Settings]`（`CAMSET*.DAT`）明确排除 `Custom 1..3`。
   - **推断**：由于 `ilc/2210` 未将 `Custom 1..3` 内部校准色温列入 `[Camera Settings Reset]` 复位清单且 `FX3 appFw.so` 单独维护 `BKID_APP_preserved_white_balance_adjustment_gm_custom_{1..3}`，仅靠 `[Camera Settings Reset]` 只能保证退出 `Custom 1..3` 回到 `Auto`，不能保证清空历史上存留于 `Custom 1..3` 的校准值；实验台架交接前须执行 **`[Initialize]`** 才能确保彻底清零。

### 2.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 白平衡控制架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **物理切换与存储槽位** | 菜单 + `C2` 默认按键切换；**3 个自定义槽位（`Custom 1..3`）** | 机身侧物理 **3 档 `WHT BAL` 拨钮开关（`B` / `A` / `PRST`）**；支持 **`Memory A..H`** 8 组色温记忆（`VAL_setting_white_select_WHITE_SELECT_MEMORY_{A..H}`） |
| **Preset WB 与偏移** | `Daylight` / `Shade` / `Cloudy` / `Incandescent` / `Fluorescent` / `C.Temp./Filter (2500K–9900K)` | `Preset White`（`3200K` / `4300K` / `5600K` / `6300K` / `Custom`）+ 独立 `Offset Color Temp` / `Offset Tint` |
| **自动白平衡追踪与速度** | `Auto` + `[Priority Set in AWB]` + `[Shockless WB]`（`Off / 1..3`）+ 按键 `AWB Lock Hold/Toggle` | **`ATW`（`Auto Tracing White Balance`）**（可配于 `B` 档开关或自定义键）+ **`ATW Speed`（`1..5`，`VAL_setting_atw_speed_ATW_SPEED_{1..5}`）** + **`ATW Hold`**（`ASSIGNABLE_SWITCH_ATW_HOLD`） |
| **`Cine EI` 模式限制** | 禁用 `Auto` 与 `Underwater Auto` | 同样**锁定禁用 `ATW`**，仅允许固定色温预设或 `Memory` 档位 |

---

## 3. 子系统 3：Movie AF 动态（`[AF Transition Speed]`、`[AF Subj. Shift Sens.]`、`[AF Assist]` 与 `[Focus Map]`）

### 3.1 `ILME-FX3 Ver. 7.02` Movie AF 动态参数与重大跨机纠偏（`实测事实`）

| 菜单项 / 功能 | `FX3 Ver. 7.02` 真值与默认 | `[Camera Settings Reset]` | `FX6 Ver. 6.01` 真值对比（`实测事实`） | 二进制与 UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- | :--- |
| **`[AF Transition Speed]`**<br>(`Focus -> AF/MF`) | **`1 (Slow)` .. `7 (Fast)`**（7 级，默认 **`5`**） | **Can be reset** | **`1 (Slow)` .. `7 (Fast)`**（同为 7 级） | FX3 `_f 0x6e9d`, `0x73bb..0x73c1`；FX3 & FX6 ELF 共用 `VAL_setting_movie_af_transition_speed_MOVIE_AF_TRANSITION_SPEED_{1_SLOW..7_FAST}` |
| **`[AF Subj. Shift Sensitivity]`**<br>(`Focus -> AF/MF`) | **`1 (Locked on)` .. `5 (Responsive)`**（**5 级**，默认 **`5 (Responsive)`**） | **Can be reset** | **`1 (Locked On)` .. `5 (Responsive)`（同为 `1..5`，而非误传的 `1..7`！）** | FX3 `_f 0x79d6`, `0x6c1e..0x6c1a` (`level 1..5`)；FX6 UXC `0x22f5`/`0x22f7`；**FX3 与 FX6 ELF 均止步于 `MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE`（`6`/`7` 均为 `0` 命中！）** |
| **`[AF Assist]`**<br>(`Focus -> AF/MF`) | **`Off`**（**默认**） / `On`（Movie/S&Q `AF-C` 下转动对焦环可手动接管对焦，停转后由 AF 锁定新目标） | **Can be reset** | 支持 **`AF Assist`**（`BKID_APP_SETTING_AF_ASSIST`，且受 `LENS_AF_ASSIST_INHIBIT` 约束） | FX3 `_f 0x64a9`；`BKID_APP_setting_af_assist`；`VAL_setting_af_assist_AF_ASSIST_{OFF,ON}`；官方确认不兼容 **`SELP1650`** 与 **`SEL18200LE`** |

> **关键跨机纠偏（`实测事实`）**：部分社区传闻误称 `ILME-FX6` 的 `AF Subj. Shift Sens.` 扩展到了 `1..7` 级。本次通过直接解析 `FX6 appFw.so`（50,520,424 字节）与 `FX6 string_english.uxc` 实证：**FX6 与 FX3 一样，`AF Transition Speed` 为 `1..7`，而 `AF Subj. Shift Sens.` 严格为 `1..5`**（ELF 符号表完整枚举仅为 `1_LOCKED_ON`, `2`, `3`, `4`, `5_RESPONSICE`，甚至连拼写笔误 `RESPONSICE` 都完全同源）。FX6 在操作上额外提供 `AF Speed/Sens.` 快速自定义按键切换。

### 3.2 `[Focus Map]` 实证纠偏：Ver. 6.00+ 仅限外部 *Monitor & Control* vs FX6 机身原生（`实测事实`）

1. **纠偏 1：FX3 从未在 `Ver. 2.00` 拥有机身内 Focus Map，实为 `Ver. 6.00` 通过 *Monitor & Control* App 开放**：
   - `ILME-FX3` 机身本体的 `MENU` 中**不存在 `[Focus Map]` 菜单项**，也不存在对应的可分配自定义按键（`FX3 appFw.so` 中 `BKID_APP_USER_MENU_FOCUS_MAP`、`ASSIGNABLE_SWITCH_FOCUS_MAP` 均为 **`0` 命中**，`ilc/2210` 机身菜单亦无该页）。`_f 0x61f9` (`'Focus Map'`) 与 `_f 0x6247` 仅为 Sony 多机型共用 UI 资源包残留的共享字符串。
   - Sony 在 **`ILME-FX3 Ver. 6.00`**（2024 年 9 月，延续至 `Ver. 7.02`）中通过 `to_remote_event_focus_map` 与 `model::sequence_notify_focus_map` 遥测事件，正式向 **iPad/Android *Monitor & Control* App（Ver. 2.1.0+）** 开放 `[Focus Map]` 景深热力图（`Monitoring -> [TOOL] -> [Focus map]`，支持 0%–100% 透明度；冷色点 = 焦点后景深，暖色点 = 焦点前景深，无色点 = 合焦区；不烧录进机内录制与 HDMI 输出）。
2. **FX3（*Monitor & Control*）vs FX6（机身原生）`Focus Map` 互斥与限制矩阵（`实测事实`）**：

| 对比维度 | `ILME-FX3 Ver. 6.00–7.02` (*Monitor & Control* App) | `ILME-FX6 Ver. 4.00–6.01`（机身原生 + *M&C*） |
| :--- | :--- | :--- |
| **呈现载体与底层符号** | **仅外部 *Monitor & Control*（Wi-Fi 无线连接）**；`FX3 appFw.so`：`to_remote_event_focus_map`、`sequence_notify_focus_map` | **机身 LCD 取景器原生内置** + *M&C*；`FX6 appFw.so`：`BKID_APP_USER_MENU_FOCUS_MAP`、`ASSIGNABLE_SWITCH_FOCUS_MAP`、`FX6_1 0x106e..0x11fe` |
| **帧率硬互斥** | **`>= 150 fps` 不可用**（即 S&Q `200fps/240fps` 被禁；`100p/119.88p` 小于 150 fps 仍属允许区间） | **`<= 6 fps` 下限 与 `>= 150 fps` 上限**双重不可用（S&Q `1..6 fps` 及 `150+ fps` 均禁） |
| **功能与镜头互斥** | 禁用条件（*M&C* 官方文档）：① **回放控制中**；② **未装镜头 / 非 PDAF 相位对焦镜头 / 安装镜头转接环**；③ **开启 `Auto Framing`（自动构图）**；④ **USB 有线远程拍摄**或 **UVC**（FX3 不支持 UVC） | 禁用条件（FX6 手册 + 固件）：非 PDAF 镜头/无镜头、MF 模式（部分状态）、`HDMI RAW` / `Focus Magnifier` / `Digital Extender`、`Base Look` / 特定监看输出互斥 |
| **Clean HDMI 同步注记** | 不污染机内录制与 HDMI 信号；但经 Wi-Fi 使用 *M&C* 同步监看时，若无线信号抖动，Focus Map 与人脸/追踪框可能相对 HDMI 画面轻微滞后 | 机身支持叠加在机内 LCD 或受监看选项控制的输出口，录制文件本身绝不烧录 |

---

## 4. 子系统 4：`[Marker Display]`（15 比例全激活）与 4 色 `[Peaking Display]` vs `FX6` `User Box`

### 4.1 `ILME-FX3 Ver. 7.02` `[Marker Display]` 与 `[Peaking Display]` 全量真值矩阵（`实测事实`）

| 菜单项 / 路径 | `FX3 Ver. 7.02` 实机选项与出厂默认 | `[Camera Settings Reset]` | HDMI 输出隔离 | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **`[Marker Display]`**<br>(`Shooting -> Marker Display`，**仅 Movie / S&Q**) | **`Off`**（**默认**） / `On`（总开关，支持多标记同时叠加） | **Not available**<br>*（须 `[Initialize]`）* | **绝对仅机身屏幕**（*Not output to HDMI*） | `_f 0x6803`；`BKID_APP_setting_marker_display`；`VAL_setting_marker_display_MARKER_DISPLAY_{OFF,ON}`；`PRM_HAITA_setting_marker_display_exposure_mode` |
| **`[Center Marker]`** | **`Off`**（**默认**） / `On` | **Not available** | **绝对仅机身屏幕** | `_f 0x6707`；`BKID_APP_setting_center` |
| **`[Aspect Marker]`** | **`Off`**（**默认**）+ **全部 15 种激活比例（共 16 态）**：`9:16`、`4:5`、`1:1`、`4:3`、`13:9`、`14:9`、`15:9`、`16:9` *(Ver. 3.00+)*、`17:9`、`1.66:1`、`1.85:1`、`1.91:1`、`2:1`、`2.35:1`、`2.39:1`（**0 休眠比例**） | **Not available** | **绝对仅机身屏幕** | `_f 0x66ac`；`BKID_APP_setting_marker_display_aspect`；`VAL_setting_marker_display_aspect_ASPECT_{OFF,9_16,4_5,1_1,4_3,13_9,14_9,15_9,16_9,17_9,1_66_1,1_85_1,1_91_1,2_1,2_35_1,2_39_1}` 全量 16 枚值在 ELF 与 UXC 一一命中 |
| **`[Safety Zone]`** | **`Off`**（**默认**） / `80%` / `90%` | **Not available** | **绝对仅机身屏幕** | `_f 0x6f50`, `0x67e3` (`80%`), `0x693c` (`90%`)；`BKID_APP_setting_safety_zone`；`SAFETY_ZONE_{OFF,0_8,0_9}` |
| **`[Guideframe]`** | **`Off`**（**默认**） / `On`（机身单一九宫格/网格开关；与 `[Focus Magnifier]` 互斥隐藏） | **Not available** | **绝对仅机身屏幕** | `_f 0x62f9`/`0x6d65`；`BKID_APP_setting_guide_frame`；注：`VAL_um_guide_frame_UM_GUIDE_FRAME_{RULE_OF_3RD_GRID,SQUARE_GRID,DIAG_SQUARE_GRID}` 仅属 UM/外部连接枚举 |
| **`[Peaking Display]`**<br>(`Focus -> Peaking Display`，Still / Movie / S&Q) | **`Off`**（**默认**） / `On`（支持 MF / DMF 及 Movie AF；`Peaking Display Select` 默认绑定控制拨轮右键） | **Not available**<br>*（须 `[Initialize]`）* | **绝对不通过 HDMI 输出峰值轮廓** | `_f 0x6fe5` / `g 0x0050`；`BKID_APP_setting_peaking_display`；`PEAKING_DISPLAY_VALUE_{OFF,ON}` |
| **`[Peaking Level]`** | `High` / **`Mid`**（**默认**） / `Low` | **Not available** | 同上 | `base 0x014c` / `0x0078` / `0x006d` / `0x006e`；`BKID_APP_setting_peaking_level`；`PEAKING_LEVEL_VALUE_{HIGH,MID,LOW}` |
| **`[Peaking Color]`** | `Red` / `Yellow` / `Blue` / **`White`**（**默认**） | **Not available** | 同上 | `base 0x014d` / `0x08c6` / `0x014e` / `_f 0x7494` / `base 0x0883`；`BKID_APP_setting_peaking_color`；`PEAKING_COLOR_VALUE_{RED,YELLOW,BLUE,WHITE}` |

> **清洁 HDMI 监看与复位安全注记（`实测事实` + `推断`）**：`ilc/2210` 明确确认无论是 `[Marker Display]` 还是 `[Peaking Display]`，均**不会透传至 HDMI 外部设备**（与 `[HDMI Info. Display]` 状态无关）；同时 **`[Focus Magnifier]` 放大对焦期间 `[Marker Display]` 自动隐藏**。由于全组 8 项设置**均不受 `[Camera Settings Reset]` 影响**，若测试台架或租赁机交接仅执行了拍摄设置复位，残留的遮幅标线与峰值着色仍会保留在屏幕中，必须执行 **`[Initialize]`** 或逐项归 `Off`。

### 4.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 电影标线与峰值体系对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **Aspect 比例与自定义** | **15 种固定比例**（含 `9:16` / `4:5` / `1:1` / `1.91:1` / `2:1` 竖屏与流媒体比例；**无自定义比例**） | 11 种传统比例 + **`Custom`** 自由比例（`BKID_APP_MARKER_ASPECT_CUSTOM_RATIO_{WIDTH,HEIGHT}`；无 `9:16` 等竖屏比例） |
| **Aspect Mask（暗角遮罩）** | **无**（仅描线显示） | 支持 **`Aspect Marker: Line / Mask`** 及 **`Aspect Mask` 透光级（`0..15`，默认 `12`）**（`BKID_APP_SETTING_ASPECT_MASK`） |
| **安全框精度** | `Safety Zone`：`Off / 80% / 90%` | 独立 `Safety Zone` (`On/Off`) + **`Aspect Safety Zone` & `Aspect Safety Area` (`80% / 90% / 92.5% / 95%`)** + `100% Marker` |
| **`User Box` 自由矩形框** | **无** | **`Monitoring > Marker > User Box`**（`BKID_APP_SETTING_USER_BOX`：`Width 3..479` def `240`、`Height 3..269` def `135`、`H Pos -476..+476` def `0`、`V Pos -266..+266` def `0`，由 `PRM_HAITA_setting_user_box_{h_pos_width,v_pos_height}` 联锁边界） |
| **峰值颜色与选项** | `Red / Yellow / Blue / White` | **`B&W / Red / Yellow / Blue`**（`PEAKING_COLOR_VALUE_B_W`，**用 `B&W` 替代 `White`**）+ 独立 `Peaking Type` / `Peaking Frequency` |

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 实证覆盖范围 |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`nflasha15/lib/appFw.so`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `ftp_server_settings*0..8`、`0` 命中 `sftp`/`passive_mode`/`transfer_jpeg_size`、`priority_set_in_awb`、`stl_awb_lock_with_shutter`、`movie_shockless_wb`、`af_transition_speed`/`af_subj_shift_sens`/`af_assist`、`to_remote_event_focus_map`、`marker_display_aspect` 16 态、`peaking_*` |
| `FX6 appFw.so` (`FX6 .../lib/appFw.so`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `AUTO_UPLOAD_PROXY_CHUNK`、`SET_SERVER_SECURE_PROTOCOL_ON_{FTPES,SFTP}`、`WHITE_SELECT_MEMORY_{A..H}`、`ATW_SPEED_{1..5}`、`MOVIE_AF_SUBJ_SHIFT_SENS_{1..5}`（证伪 `1..7`）、`USER_MENU_FOCUS_MAP`、`USER_BOX_*`、`PEAKING_COLOR_VALUE_B_W` |
| `FX3-CX95900_ALLLANG-Backup.bin` (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失备份结构基线（`BK4\x00`，不含明文 `BKID_APP_*` 键名字符串） |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | FX3 `hdr_flag=15` 主菜单与提示英文包（`7,475` 条实测记录 `0x6000..0x7d32`） |
| `FX3 string_english.uxc` / `_g.uxc` | `165,740` / `69,600` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | FX3 `hdr_flag=8` 基础菜单、`Custom WB`、`AVF_INFO + FTP` 告警与扩展提示英文包 |
| `FX3 string_simplifiedchinese_f.uxc` / `.uxc` / `_g.uxc` | `322,652` / `149,064` / `61,296` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `_f` / 基础 / 扩展三包四语 `resid16` 精确映射 |
| `FX3 string_traditionalchinese_f.uxc` / `.uxc` / `_g.uxc` | `324,148` / `151,908` / `61,372` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁體中文 `_f` / 基础 / 扩展三包四语 `resid16` 精确映射 |
| `FX3 string_japanese_f.uxc` / `.uxc` / `_g.uxc` | `447,840` / `208,564` / `89,428` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本語原厂 `_f` / 基础 / 扩展三包四语 `resid16` 精确映射 |
| `FX6 string_english.uxc` / `_2.uxc` | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 `ATW` / `Focus Map` / `User Box` / `Aspect Mask` / `B&W` 峰值字符串包（`SFTP` `0` 命中） |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x6317` / `0x62fc` | `FTP Transfer Func.` / `FTP Transfer` | `FTP传输功能` / `FTP传输` | `FTP傳輸功能` / `FTP傳輸` | `FTP転送機能` / `FTP転送` | 活跃（抗 `Camera Settings Reset`） |
| `_f` `0x6305` / `0x72f4` / `0x630d` | `Server 1` / `Server 8` / `Server 9` | `服务器1` / `服务器8` / `服务器9` | `伺服器1` / `伺服器8` / `伺服器9` | `サーバー1` / `サーバー8` / `サーバー9` | 活跃（9 槽位，`0x72f4` 独立编码） |
| `_f` `0x60dd` / `0x6553` | `Secure Protocol` / `Connects with FTPES.` | `安全协议` / `连接FTPES。` | `安全通訊協定` / `連線到FTPES。` | `セキュアプロトコル` / `FTPESで接続します` | 活跃（Explicit FTPS；零 `SFTP`） |
| `_f` `0x6e7e` / `0x76e6` / `0x6a5f` | `Directory Hierarchy` / `Same as in Camera` / `FTP Power Save` | `目录层级` / `与拍摄装置中相同` / `FTP节电` | `目錄階層` / `與拍攝裝置相同` / `FTP省電` | `フォルダー階層` / `カメラと同じ` / `FTPパワーセーブ` | 活跃（`Slot 1->A` / `Slot 2->B`） |
| `_f` `0x7d31` / `0x6bd5` / `0x7940` | `Trgt. Img (Clip Flag)` / `RAW+J/H Transfer Target` / `Import Root Certificate` | `目标影像(片段旗标)` / `RAW+J/H传输目标` / `导入根证书` | `目標影像(短片旗標)` / `RAW+J/H傳輸目標` / `匯入根憑證` | `対象動画(ｸﾘｯﾌﾟﾌﾗｸﾞ)` / `RAW+J/H転送対象` / `ﾙｰﾄ証明書の読み込み` | 活跃（Ver. 7.00+ Clip Flag） |
| `_f` `0x6aed` / `0x63dd` | `Transfer JPEG Size` / `Transfer HEIF Size` | `传输JPEG尺寸` / `传输HEIF尺寸` | `傳輸JPEG尺寸` / `傳輸HEIF尺寸` | `転送するJPEGサイズ` / `転送するHEIFサイズ` | **休眠**（FX3 ELF `0` 命中） |
| `base` `0x0a13` | `Image Database File error.\nFTP transfer results will be reset if recovered. Recover?` | `影像数据库文件错误。\n修复后FTP传输结果将重置。要修复吗？` | `影像資料庫檔案錯誤。\n如果還原，將重設FTP傳輸結果。要還原?` | `管理ファイルに不整合が見つかりました\n修復するとFTP転送結果がﾘｾｯﾄされます\n修復しますか？` | **关键证据**（FTP 结果与 DB 耦合） |
| `base` `0x09b7` / `0x09b8` | `FTP Transferring...\nCannot be executed.\nSlot 1` / `Slot 2` | `FTP传输...\n无法执行。\n插槽1` / `插槽2` | `FTP傳輸中...\n無法執行。\n插槽1` / `插槽2` | `FTP転送中\n実行できません\nスロット 1` / `スロット 2` | 活跃（FTP 槽位传输中互斥告警） |
| `_f` `0x73ee` / `0x67a7` / `0x66db` / `0x62fe` | `White Balance` / `Priority Set in AWB` / `Shutter AWB Lock` / `Shockless WB` | `白平衡模式` / `AWB优先级设置` / `快门AWB锁定` / `减震WB` | `白平衡` / `AWB優先順序設定` / `快門AWB鎖` / `減震WB` | `ホワイトバランス` / `AWB時の優先設定` / `ｼｬｯﾀｰAWBﾛｯｸ` / `ショックレスWB` | 活跃（`Shutter AWB Lock` 抗 Reset） |
| `_f` `0x63ac` / `base` `0x0220` | `Capturing of the custom WB failed.` / `Custom WB Error` | `捕获自定义WB失败。` / `自定义白平衡错误` | `捕捉自設WB失敗。` / `自設白平衡錯誤` | `カスタムWBの取り込みに失敗しました` / `カスタムWB設定エラー` | 活跃（Log / S-Log3 采白告警） |
| `_f` `0x6e9d` / `0x79d6` / `0x64a9` | `AF Transition Speed` / `AF Subj. Shift Sensitivity` / `AF Assist` | `AF过渡速度` / `AF摄体转移敏度` / `AF帮助` | `對焦變換速度` / `對焦變換靈敏度` / `AF幫助` | `AFﾄﾗﾝｼﾞｼｮﾝ速度` / `AF乗り移り感度` / `AFアシスト` | 活跃（`1..7` / `1..5` / `On/Off`） |
| `_f` `0x61f9` | `Focus Map` | `焦点图` | `對焦圖` | `フォーカスマップ` | 共享字符串（FX3 仅限外部 *M&C*） |
| `_f` `0x6803` / `0x6707` / `0x66ac` / `0x6f50` / `0x62f9` | `Marker Display` / `Center Marker` / `Aspect Marker` / `Safety Zone` / `Guideframe` | `标记显示` / `中央标记` / `纵横标记` / `安全框` / `引导框` | `錄影輔助標誌顯示` / `中央錄影輔助標誌` / `長寬比輔助標誌` / `安全區` / `水平導引框` | `マーカー表示` / `センターマーカー` / `アスペクトマーカー` / `セーフティゾーン` / `ガイドフレーム` | 活跃（全部 **抗 Reset**；仅机内屏） |
| `_f` `0x78d7`..`0x6da5`, `base` `0x00d9` | `Aspect Marker` 全 15 比例（`9:16`..`2.39:1` & `1:1`） | 同左（15 项全匹配） | 同左（15 项全匹配） | 同左（15 项全匹配） | **全部 15 项激活** |
| `_f` `0x6fe5` / `base` `0x014c` / `base` `0x014d` | `Peaking Display` / `Peaking Level` / `Peaking Color` | `峰值显示` / `峰值水平` / `峰值色彩` | `峰值顯示` / `峰值等級` / `峰值顏色` | `ピーキング表示` / `ピーキングレベル` / `ピーキング色` | 活跃（`Red/Yellow/Blue/White`，抗 Reset） |
