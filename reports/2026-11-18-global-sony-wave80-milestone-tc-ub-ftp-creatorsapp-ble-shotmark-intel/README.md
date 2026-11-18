# 全球 Sony 实机情报 Wave 80 里程碑（`80th Wave`：`80/80 Waves` 全系列收官 · `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` `[TC/UB]` 全架构与 `VMC-BNCM1` vs 物理 `TC IN/OUT`、`[FTP Transfer Func.]` FTPS/Slot-1 `.dat`、`[Creators' App]` BLE 绑定/GPS/`[Airplane Mode]`，以及回放 `[Shot Mark 1/2]`/`[Rating]`/`[Protect]`/`[Copy]` Tier-0 `Slot 1 EROFS=30` 写卡语义深度审计）

- **日期**：`2026-11-18`
- **任务 / 波次**：`H460` · **Global Sony Real-Hardware Empirical Intelligence Wave 80 Milestone**（`80th Wave` / **`80/80 Waves` 全球实机情报全系列收官里程碑**）
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`，`Linux 4.9.337-scel+`，`PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`）
- **承接与关键勘误声明**：
  - 本 Wave 80 里程碑承接 [Wave 58（Shot Mark / Timecode Link / Wi-Fi / USB-LAN）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/reports/2026-11-17-global-sony-wave58-bright-monitoring-shot-mark-timecode-link-wifi-usblan-intel/README.md)、[Wave 61（FTP / FTPES / 9 槽位 / Slot 1 危害）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/reports/2026-11-17-global-sony-wave61-ftp-ftps-customwb-af-speed-focusmap-marker-intel/README.md)、[Wave 67（HDMI TC Output / REC Control / 4ch Audio）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/reports/2026-11-17-global-sony-wave67-pixelmap-apr-monitor-vfadjust-recall-custom-hold-hdmi-tc-recctrl-intel/README.md)、[Wave 78（Flexible Exp. / Shutter Angle / Active IBIS / SRT）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/reports/2026-11-18-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/README.md) 与 [Wave 79（Zoom Speed / My Dial 1–3 / HDMI 4K / 12G-SDI）](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/reports/2026-11-18-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/README.md)。
  - 基于官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210` Ver. 7.02）、官方 Sony `FTP Help Guide`（`helpguide.sony.net/di/ftp_2210`）、官方 `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB` Ver. 6.0）以及严格 `os.O_RDONLY` 本地 donor 二进制与共享库实证，本 Wave 80 收官审计**显式揭穿与修正了 5 项跨机型迷思与仓内守卫精度勘误**：
    1. **CRITICAL 勘误：`[Reset Network Set.]` 不清除 `[Airplane Mode] = On`（修正 [`G114`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py#L245) 描述偏差）**：[`G114`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py#L238-L246) 在 `NETWORK_RESET_CLEARED_CATEGORIES_G114` 中将 `"Airplane Mode (reset to Off)"` 列为 `[Reset Network Set.]` 清除项；然而官方 `ilc/2210`（*Setting Reset*）白纸黑字规定：**`"Even if [Reset Network Set.] is performed while [Airplane Mode] is set to [On], [Airplane Mode] will not be reset to [Off]."`**——仅 **`[Initialize]`** 才将 `[Airplane Mode]` 复位为 `Off`，且同时保留 `USB-LAN` 有线通道（零射频台架仍须物理/电气断开 `USB-LAN`）。
    2. **`[Location Info. Link Set.]` 在 Ver. 3.00–7.02 已迁出机身菜单并交由 `Creators' App` 接管（`ilc/2210` + `FX3 appFw.so` + `libInfraBluetoothLowEnergy.so`）**：尽管 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 与 `_f.uxc`（`_f 0x77b8` `\ue59eLocation Info. Link Set.`、`BKID_APP_setting_location_info_link`）仍保留 Ver. 2.00 *Imaging Edge Mobile* 时代的菜单与备份符号，但官方 `ilc/2210`（Ver. 3.00+ 至 Ver. 7.02）在机身菜单中**已无 `[Location Info. Link Set.]` 入口**，改为在手机端 **`Creators' App -> [Cameras] -> [Setup] -> [Location Information Linkage]`** 通过 Sony BLE 私有 GATT 服务 **`8000DD00-DD00-FFFF-FFFF-FFFFFFFFFFFF`**（`g_locationServiceTable`）实时向 [`libgps_rsrc.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgps_rsrc.so) 与 `sequence_set_bluetooth_location_info_link` 推送经纬度与时间/时区修正（`[Auto Time Correction]` / `[Auto Area Adjustment]`）。
    3. **FX3 `SFTP` / Implicit FTPS 证伪与 `Slot 1` `FTPSET*.DAT` 重启陷阱（`FX3 appFw.so` + `libInfraFtpClient.so`）**：虽然 [`libInfraFtpClient.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFtpClient.so) 底层 `curl_multi_perform` 通用封装包含 `sftp://%s` 字面串，且 Sony 在 `di/ftp_2210` 中将加密套件说明挂在 `di/sftp` 路径下，但 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) 中 **`sftp` 为 `0` 命中**，实机仅支持明文 `FTP` 与 Explicit `AUTH TLS`（**`FTPES`**，`_f 0x6553`）；`[Save/Load FTP Settings]` 独家向 **Slot 1** 读写 **`%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT`**（`FTPSET01.DAT`..`FTPSET10.DAT`，受用户密码加密保护且 Load 后强制重启），在 Tier-0 保险库上触发确定性 `EROFS=30`。
    4. **FX6 `Users Bit` 无 `ASCII`/`Binary` 模式，`Title1(ASCII)` 实为 Clip Title（`5-024-458-18` + `FX6 appFw.so` + `FX6_2.uxc`）**：`ILME-FX6 Ver. 6.01` 的 `TC/Media > Users Bit` 仅暴露 `Mode`（`Fix` / `Time`）与 8 位十六进制 `Setting`（ELF `EXTERN_UB_MODE_CLK_TIME` / `EXTERN_UB_MODE_PRESET_FIX`）；`FX6_2.uxc 0x4a2d` `'Title1(ASCII)'` 属于剪辑元数据标题而非 User Bit 编码。同时 FX6 的 `BKID_APP_SETTING_BLUETOOTH_FUNCTION`、`BKID_APP_SETTING_LOCATION_BY_MOBILE_APP` 与 `Shot Mark 0..9` / `Essence Mark` 均属无硬件/已退役 CBM 遗留休眠符号。
    5. **Playback `Copy` 方向非对称性与 `Shot Mark`/`Rating`/`Protect` 隐蔽写盘本质（`libmpr.so` + `libInfraAdjMedia.so` + `libInfraFsys.so`）**：`[Copy]` 在 `Slot 1 -> Slot 2` 方向对 `Slot 1` 仅作只读读取（安全放行），但在 `Slot 2 -> Slot 1` 方向会改写 `Slot 1` 簇链与数据库；看似“轻量标点”的 `[Add/Delete Shot Mark 1/2]`、`[Rating] 1..5` 与 `[Protect]` 实测在底层通过 [`libmpr.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so) / [`libInfraFsys.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFsys.so) 就地改写 `M4ROOT/CLIP/*M01.XML`、`NonRealTimeMeta`、`<xmp:Rating>`、exFAT/FAT 文件属性（`Fsys_Chmod` / `tntfs_chmod`）与 `AVF_INFO` 索引，Tier-0 `Slot 1` 必须全部截获返回 `EROFS=30`（`slot1_sector_writes == 0`）。
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *TC/UB / Matching the time code with other devices (`TP1000669445`) / HDMI Output Settings / Creators' App / Smartphone Connection / Cnct. while Power OFF / Reading location information from a smartphone / Bluetooth Settings / Airplane Mode / Reset Network Set. / Setting Reset / Save/Load Settings / Shot Mark / Image Jump Setting / Rating / Protect / Delete / Copy / List of default setting values (`TP1000888852`)*）
  - 官方 Sony `ILME-FX3` FTP Help Guide（`helpguide.sony.net/di/ftp_2210/v1/en/` —— *FTP Transfer Func. / Server Setting / Secure Protocol (FTPES) / Root Certificate Error / Import Root Certificate / Save/Load FTP Settings / Auto FTP Transfer / Directory Hierarchy / RAW+J/H Transfer Target / FTP Power Save*）
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *TC/Media > Timecode / Users Bit / TC Display / TC IN/OUT External Lock (`EXT-LK`) / Network > File Transfer / Auto Upload (Proxy) / Wireless LAN (AP & Station) / Monitor & Control vs retired Content Browser Mobile / Thumbnail > Set Clip Flag / Lock / Delete / Copy*）
  - 严格只读（`os.O_RDONLY`）本地 donor 二进制实证：[`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so)（`79,015,712` B）+ 14 个 FX3 `/usr/lib/*.so` 与 `/usr/bin/bt_stack.conf` + FX3 4 语全量 `base`/`_f`/`_g` `.uxc`（12 文件）+ [`FX3-CX95900_ALLLANG-Backup.bin`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin)（`2,229,740` B），以及 [`FX6 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so)（`50,520,424` B）+ FX6 4 语 `ns1`/`_2` `.uxc`（8 文件），合计 **38 个本地 donor 工件**。
  - 仓内安全守卫交叉对照：[`G114`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py)、[`G126`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py)、[`G128`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py)、[`G141`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py)。
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（UXC `resid16`、ELF 偏移与符号、SHA-256 账本、官方手册条款）与 **`工程推断`**（Tier-0 `Slot 1 EROFS=30` 防火墙、Zero-RF 台架规则、守卫勘误修正建议）。

---

## 核心结论速览（Executive Summary）

1. **支柱一（`[TC/UB]` 全架构、Reset 持久化、DF/NDF 帧率矩阵与 `VMC-BNCM1` vs FX6 物理 `TC IN/OUT`）**：
   - **实测事实（FX3 Ver. 7.02 6 项 + 显示设置全抗 Camera Reset）**：`Shooting -> [TC/UB]`（`_g 0x6389`）包含精确 6 项：`[Time Code Preset]`（`_f 0x6b63`，默认 `00:00:00.00`）、`[User Bit Preset]`（`_f 0x7af2`，默认 `00 00 00 00`）、`[Time Code Format]`（`_f 0x6e3d`，默认 `DF`）、`[Time Code Run]`（`_f 0x7313`，默认 `Rec Run`）、`[Time Code Make]`（`_f 0x6b79`，默认 `Preset`；ELF 含原厂拼写错误 `VAL_setting_tc_make_TC_MAKE_REGENRATE`）与 `[User Bit Time Rec]`（`_f 0x7aa8`，默认 `Off`），外加 `Setup -> [Display Option] -> [TC/UB Disp. Setting]`（`_f 0x6b0c`，`Counter`/`TC` 默认/`U-Bit`，回放仅 Movie 可切换 `base 0xe728`）。**上述全部 7 项（包括 `Preset` 数值与模式开关）在 `[Camera Settings Reset]` 下均为 `Not available`（保持不变）**，仅 `[Initialize]` 会全量归零（`Preset` 亦可在子界面按删除键清零或随系统固件升级自动清零）。
   - **实测事实（`DF`/`NDF` 矩阵与 `VMC-BNCM1` TC-IN-Only 物理拓扑）**：`[Time Code Format]` 仅在 `[NTSC/PAL Selector] = NTSC` 且帧率为 **`29.97p` / `59.94p` / `119.88p`** 时可选 `DF`/`NDF`；**`23.98p`、`24.00p` 与 PAL（`25p`/`50p`/`100p`）下均强制锁为 `NDF`/`[-]`**。FX3 **无物理 `TC OUT` BNC**，仅支持在主机身 Multi/Micro USB 接口经专用转接线 **`VMC-BNCM1`**（`A-5051-506-A`、`0.2 m`）**单向注入外部 LTC（TC-IN-Only）**：需设 `[Time Code Make] = Preset` + `[Time Code Run] = Free Run`，锁定约 10 秒后显示 `EXT-LK` 且拔线后维持自走；若更改 `Make`/`Run`/`Preset` 或切入 `S&Q` 则立即解除 `EXT-LK`（且 `VMC-BNCM1` 严禁插入 `XLR-H1` 手柄 Micro USB）。对外输出时间码仅能经 `[External Output] -> [Time Code Output]` 嵌入 HDMI（`S&Q` 禁用）。
   - **实测事实（`ILME-FX6 Ver. 6.01`）**：配备独立物理 BNC 端子与硬件 **`TC IN / OUT` 滑动切换开关**，外加机身 `TC/UB` 键、`TC RESET` 键及可分配 `DURATION/TC/U-BIT`（`ns2 0x5438`）键；`TC/Media > Timecode > Mode` 额外多出 **`Clock`** 模式（`VAL_setting_tc_make_TC_MAKE_CLOCK`）；`Users Bit` 为 `Fix`/`Time` + 8 位十六进制（**无 ASCII 模式**）。

2. **支柱二（`[FTP Transfer Func.]`、Explicit `AUTH TLS`、`Slot 1` `.dat` 与 `cacert.pem` vs FX6 `File Transfer`）**：
   - **实测事实（FX3 Ver. 7.02 协议栈与加密实证）**：`Network -> [Transfer/Remote]`（`_g 0x6399`）-> `[FTP Transfer]`（`_g 0x64bf`）-> `[FTP Transfer Func.]`（`_f 0x6317`）暴露 **`Server 1..9`**（9 槽位）、`Secure Protocol`（`Off` 明文 `FTP` vs `On` **Explicit TLS `AUTH TLS` / `FTPES`** `_f 0x6553`；**不支持 Implicit FTPS，也不支持 SSH-SFTP**；仅 Passive 模式）、`Root Certificate Error`（`Does Not Connect` / `Connect`）、`[Import Root Certificate]`（强制读取 **Slot 1** 根目录 `cacert.pem` <= 1 MB）、**`[Save/Load FTP Settings]`**（`_f 0x71ae`，读写 **Slot 1** 路径 **`%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT` -> `SONY/SETTING/<Model>/FTPSET/FTPSET01.DAT`..`FTPSET10.DAT`**，带用户密码加密且 Load 后重启）、`[Auto FTP Transfer]`（`_f 0x7b27`）、`[Transfer Target]` / `[RAW+J/H Transfer Target]`、`[Directory Hierarchy]`（`Standard` / `Same as in Camera` `A/`/`B/`）与 `[FTP Power Save]`。[`libInfraFtpClient.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFtpClient.so) 链接 OpenSSL 3.0（[`libssl.so.3`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libssl.so.3)），强制 `TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256`、`AUTH TLS` 与 CRL 吊销校验（`/cert/crl/tmp_crl.crl`），[`libCertificateManager.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libCertificateManager.so) 负责 X509/OCSP。
   - **实测事实（`ILME-FX6 Ver. 6.01`）**：`Network > File Transfer` UI 暴露 `Server Settings1..3`（ELF 留存 `1..16`）、支持 `Passive Mode On/Off`（含 Active Mode）、`Auto Upload (Proxy): Chunk`（占 Slot B 且互斥 `Simul`/`Relay`）、根证书 **`certification.pem` 置于 Slot B**，由 `Network > Network Reset` 统一清除。

3. **支柱三（`Creators' App` BLE GATT 绑定、GPS EXIF/XMP 与 `[Airplane Mode]` 抗网络复位 vs FX6）**：
   - **实测事实（5 组索尼 BLE GATT 服务与 Wake-on-LE 机制）**：`Creators' App`（Ver. 3.00+ 取代 IEM）经 `[Cnct./Remote Sht.] -> [Smartphone Connection]` 建立 BLE 配对（最多存 15 台、并发 2 路）。[`libInfraBluetoothLowEnergy.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraBluetoothLowEnergy.so) 实装 5 张 128-bit GATT 服务表：`8000CC00`（`g_dicamServiceTable`）、`8000DD00`（`g_locationServiceTable`）、`8000EE00`（`g_pairingServiceTable`）、`8000FF00`（`g_RemoteControlServiceTable`）与 `8000BB00`（`g_rxtxServiceTable`），并通过 ECDH（`EVP_PKEY_derive_set_peer`）认证；[`bt_stack.conf`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/bin/bt_stack.conf) 以 `LMP_WAKEUP_CONFIG=0x03,0x0010,0x0010,0x0800,0x0024,0x03` 驱动 `[Cnct. while Power OFF]`（`_f 0x6ab3`）。BLE NVRAM 绑定数据**抗 `[Camera Settings Reset]`**，但在 **`[Reset Network Set.]`（`CT_ID_NETWORK_RESET_DONE`）与 `[Initialize]` 下均被彻底擦除**。
   - **实测事实 + 工程推断（GPS 注入与 `[Airplane Mode]` 零射频规则）**：Ver. 3.00+ 将旧 `[Location Info. Link Set.]` 移入 `Creators' App -> [Setup] -> [Location Information Linkage]`（单一绑定手机），实时注入 `No12_LatitudeGPSinfo`/`No14_LongitudeGPSinfo` 至静态 EXIF 与视频 `M01.XML`/`MP4`。**`[Airplane Mode]`（`_f 0x6df9`）在 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 下均保持 `On` 不复位，仅 `[Initialize]` 归零为 `Off`**；Tier-0 零射频台架必须同时强制 `Airplane Mode = On` + `Bluetooth Function = Off` + `Wi-Fi = Off` + **物理/电气隔离 `[USB-LAN/Tethering]`**（确保 `rf_tx_packets == 0`）。对比 `FX6 Ver. 6.01`：仅支持 `2.4/5GHz` AP/Station Wi-Fi（`FX6V/VK` 含 5GHz，`FX6T/TK` 仅 2.4GHz）及 `Monitor & Control`（Ver. 5.00+ 淘汰 `CBM`），**无消费级 BLE 与 GPS 手机联动**。

4. **支柱四（Playback 写卡语义矩阵与 Tier-0 `Slot 1 EROFS=30` 保险库铁律 vs FX6 `Thumbnail`）**：
   - **实测事实 + 工程推断**：[`libmpr.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so)、[`libInfraFsys.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFsys.so) 与 [`libInfraAdjMedia.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAdjMedia.so) 实证：`[Add/Delete Shot Mark 1/2]` 改写 `/M4ROOT/CLIP/*M01.XML`（`EssenceMark`）与 `AVF_INFO`；`[Rating]`（`1..5`）改写 `<xmp:Rating>` / `RatingMovie` / `AVF_INFO`；`[Protect]` 调用 `Fsys_Chmod` / `tntfs_chmod` 修改只读属性与索引；`[Delete]` 删除媒体并重写 `/M4ROOT/MEDIAPRO.XML` / `AVF_INFO`；`[Copy]` 呈**方向非对称**：**`Slot 1 -> Slot 2` 对 Slot 1 严格只读安全**（且保护标记/连拍组不跨卡保留），而 **`Slot 2 -> Slot 1`** 与上述 4 类操作及 `[Save/Load FTP Settings]` 均向 `Slot 1` 发起扇区/文件写请求，在 Tier-0 保险库上**确定性命中 `EROFS (errno 30)`（`slot1_sector_writes == 0`）**。对比 `FX6 Ver. 6.01`：`Thumbnail` 使用 **`Clip Flag`（`OK` / `NG` / `KEEP`）**、`Lock/Unlock`、`Delete`、`Copy Clip`，`Shot Mark 0..9` / `Essence Mark` 在机身/已退役 CBM 路径上休眠。

---

## 1. 支柱一：`[TC/UB]` 全架构、`VMC-BNCM1` 单向锁相与物理 Sync 拓扑 vs `ILME-FX6`

### 1.1 `ILME-FX3 Ver. 7.02` `[TC/UB]` 全菜单、Reset/Initialize 持久化矩阵（`实测事实`）

菜单路径：`MENU -> (Shooting) -> [TC/UB]`（`_g 0x6389`）及 `MENU -> (Setup) -> [Display Option] -> [TC/UB Disp. Setting]`（`_f 0x6b0c`）。对照 `ilc/2210`（*TC/UB* / `TP1000888852`）与 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so)：

| 菜单项（UXC `resid16`） | 实机选项与出厂默认 | ELF 核心符号（`FX3 appFw.so`） | `[Camera Settings Reset]` | `[Initialize]` / 其他清除方式 |
| :--- | :--- | :--- | :---: | :---: |
| **`[Time Code Preset]`**<br>（`_f 0x6b63`） | 时:分:秒:帧；默认 **`00:00:00.00`**<br>（`59.94p` `00..29`；`50p` `00..24`；`23.98p` 步进 4 帧；`24.00p` 步进 1 帧） | `BKID_APP_tc_preset_time_{hour,minute,second,frame}` | **`Not available`**<br>*（抗 Camera Reset！）* | 复位为 `00:00:00.00`；另在子界面按 **Delete 键**（`_g 0x620a`）或**系统固件升级**时自动清零 |
| **`[User Bit Preset]`**<br>（`_f 0x7af2`） | 8 位十六进制（`00 00 00 00`..`FF FF FF FF`）；默认 **`00 00 00 00`** | `BKID_APP_ub_preset_digit_{12,34,56,78}` | **`Not available`** | 复位为 `00 00 00 00`；子界面按 **Delete 键**（`_g 0x6441`）可清零 |
| **`[Time Code Format]`**<br>（`_f 0x6e3d`） | **`DF`**（`_f 0x6d59`，**默认**）/ **`NDF`**（`_f 0x6c6f`） | `BKID_APP_setting_tc_format`<br>`VAL_setting_tc_format_TC_FORMAT_{DF,NDF}` | **`Not available`** | 复位为 `DF`（仅 NTSC 特定帧率可见，见 §1.2） |
| **`[Time Code Run]`**<br>（`_f 0x7313`） | **`Rec Run`**（`_f 0x75b9`，**默认**）/ **`Free Run`**（`_f 0x6978`） | `BKID_APP_setting_tc_run`<br>`VAL_setting_tc_run_TC_RUN_{REC,FREE}_RUN` | **`Not available`** | 复位为 `Rec Run`（`S&Q` 录制模式下不可用） |
| **`[Time Code Make]`**<br>（`_f 0x6b79`） | **`Preset`**（**默认**）/ **`Regenerate`**（`_f 0x698f`） | `BKID_APP_setting_tc_make`<br>`VAL_setting_tc_make_TC_MAKE_PRESET`<br>**原厂拼写错误**：`VAL_setting_tc_make_TC_MAKE_REGENRATE`（`0x3b149b5`，缺 `E`） | **`Not available`** | 复位为 `Preset`；`Regenerate` 强制以 `Rec Run` 步进并读取指定卡槽（`Simult.` 读 **Slot 1**）上一段落末尾 TC |
| **`[User Bit Time Rec]`**<br>（`_f 0x7aa8`） | **`Off`**（**默认**）/ `On` | `BKID_APP_setting_ub_time_rec`<br>`VAL_setting_ub_time_rec_UB_TIME_REC_{OFF,ON}` | **`Not available`** | 复位为 `Off`（开启后以时:分:秒写入 User Bit） |
| **`[TC/UB Disp. Setting]`**<br>（`_f 0x6b0c`，Setup 分区） | `Counter`（`_f 0x6c01`）/ **`TC`**（**默认**）/ `U-Bit`（`_f 0x71ca`） | `BKID_APP_setting_tc_ub_disp_setting`<br>`FUNC_toggle_set_tc_ub_disp_seq` | **`Not available`** | 复位为 `TC`；回放时仅动态影像可切换，静态照片或非视频回放报 `base 0xe728` |

> [!IMPORTANT]
> **实测事实（[`G128`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py) 与官方 `TP1000888852` 100% 吻合）**：`[TC/UB]` 菜单中无论是 **`Preset` 数值** 还是 **`Format` / `Run` / `Make` / `UB Time Rec` 模式开关**，连同 `[TC/UB Disp. Setting]`，**全部 7 项均抗 `[Camera Settings Reset]`**（避免片场误复位拍照参数导致多机时间码失步）。

### 1.2 帧率 `DF`/`NDF` 可用性矩阵与 `VMC-BNCM1` TC-IN-Only 外部同步拓扑（`实测事实`）

1. **`[Time Code Format]` 帧率可用性矩阵（`ilc/2210` + `G128`）**：
   - **`NTSC` 模式下 `29.97p` / `59.94p` / `119.88p`**：允许在 **`DF`**（Drop Frame，每分钟前 2 帧跳帧、每第 10 分钟不跳以修正 `29.97` 与 `30.00` 钟差）与 **`NDF`** 间切换。
   - **`NTSC` 模式下 `23.98p` 与 `24.00p`**：菜单项 `[Time Code Format]` **固定显示 `[-]` 并强制采用 `NDF` 连续计数**（不存在 23.98 DF 选项）。
   - **`PAL` 模式下 `25p` / `50p` / `100p`**：由于 PAL 为整数帧率且无 NTSC `1000/1001` 漂移，`[Time Code Format]` 菜单屏蔽隐藏并**固定按连续帧率（NDF 等价）计数**。
   - **`[S&Q Settings]` / `[FPS]` 慢动作与快动作**：`[Time Code Run]` 与 `[Time Code Output]` **全部禁用**。

2. **Multi/Micro USB `VMC-BNCM1` 单向同步（TC-IN-Only）与 HDMI TC Output 边界（`ilc/2210` `TP1000669445` + Wave 67）**：
   - **物理硬件缺口**：`ILME-FX3` **没有物理 `TC OUT` BNC 端口**，仅能通过相机机身侧面的 **Multi/Micro USB 端子**连接另售专用转接线 **`VMC-BNCM1`**（件号 **`A-5051-506-A`**，长 `0.2 m`）接收外部标准 BNC LTC 输入（**Strict TC-IN-Only**，且官方明令禁止插入 `XLR-H1` 手柄 Micro USB 口）。
   - **锁相流程与 `EXT-LK` 状态机**：外部母钟需设为连续运行（`Free Run` / `Clock`）且帧频匹配相机；FX3 切至 `Movie` 模式、设 `[Time Code Make] = Preset` + `[Time Code Run] = Free Run`。接入后屏幕出现 **`EXT-LK`**（对应 `FX3 appFw.so` `BKID_APP_ext_tc_lock_status` -> `EXT_TC_LOCK_STATUS_{LOCK,PSEUDOLOCK,UNLOCK}` 与 `BKID_APP_last_ext_tc_lock_freq`）。锁定约 **10 秒**后即使拔掉 `VMC-BNCM1` 仍保持 `EXT-LK` 自由走时（建议锁定数秒待发生器稳定后再开录）。
   - **`EXT-LK` 解除条件**：修改 `[Time Code Make]`、`[Time Code Run]`、`[Time Code Preset]` 或切入 `S&Q` 录制模式均立即解除 `EXT-LK`；另因多机接入阶段可能存在 1 帧误差与长时温漂。
   - **HDMI `[Time Code Output]` 约束（承接 Wave 67）**：位于 `Setup -> [External Output] -> [HDMI Output Settings] -> [Time Code Output]`（默认 `Off`，`Not available` 于 Camera Reset），是 `[REC Control]` 触发外部录机启停的**前置硬条件**，在 `S&Q` 下强制禁用。

### 1.3 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` `TC/UB` 硬件与架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 appFw.so`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 appFw.so/UXC`） |
| :--- | :--- | :--- |
| **物理接口与硬件开关** | 无 BNC；**机身 Multi/Micro USB + `VMC-BNCM1`（仅 TC IN）** + HDMI TC Out | **专用物理 BNC 端子 + 硬件 `TC IN / OUT` 滑动切换开关**（`ns2 0x50c7` `TC IN` / `0x456b` `TC Out`）；`BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING` 为休眠符号 |
| **物理按键与快捷切换** | 无机身 `TC` 专键（需菜单或自定义键切换显示） | 机身左侧配物理 **`TC/UB` 键**（`EVENT_INPUT_KEY_TACT_TCUB_*`）与 **`TC RESET` 键**（`EVENT_INPUT_KEY_TACT_TC_RESET_*`），外加可分配 **`DURATION/TC/U-BIT`**（`ns2 0x5438`） |
| **`Timecode Mode / Make`** | `Preset` / `Regenerate`（2 项） | **`Preset` / `Regen` / `Clock`**（3 项，`VAL_setting_tc_make_TC_MAKE_CLOCK` 使用机身时钟） |
| **`Users Bit` 模式** | `User Bit Preset`（8 位 Hex）+ `[User Bit Time Rec]`（`On`/`Off`） | `TC/Media > Users Bit`：**`Mode`（`Fix` / `Time`）**（`EXTERN_UB_MODE_{PRESET_FIX,CLK_TIME}`）+ 8 位 Hex `Setting`（**无 ASCII/Binary 模式**；`ns2 0x4a2d` `Title1(ASCII)` 系剪辑标题） |
| **`EXT-LK` 与显示状态** | 锁相后显示 `EXT-LK`；`Counter` / `TC` / `U-Bit` | `EXT-LK`（`ns2 0x50c2`）；`TC/Media > TC Display > Display Select`：`Timecode` / `Users Bit` / `Duration` |

---

## 2. 支柱二：`Network -> [Transfer/Remote] -> [FTP Transfer Func.]` & `FTPS` TLS / `.dat` 配置 vs `ILME-FX6`

### 2.1 `ILME-FX3 Ver. 7.02` `[FTP Transfer Func.]` 完整菜单树与加密/证书链路（`实测事实`）

菜单路径：`MENU -> (Network) -> [Transfer/Remote]`（`_g 0x6399`）-> `[FTP Transfer]`（`_g 0x64bf`）-> **`[FTP Transfer Func.]`**（`_f 0x6317`）。结合 `di/ftp_2210` 与本地 `.so` 只读剖析如下：

| 子菜单项 / 参数（UXC `resid16`） | `FX3 Ver. 7.02` 实机行为与默认 | ELF / `.so` 原生实现证据（`os.O_RDONLY`） |
| :--- | :--- | :--- |
| **`[FTP Function]`**（`_f 0x7287`） | `Off`（默认）/ `On`（与 `[Cloud Connection] = On` 互斥） | `BKID_APP_setting_ftp_function`；`CLOUD_CONNECTION_ON_FTP_OFF` |
| **`[Server Setting]`**（`_f 0x6442`） | **`Server 1`..`Server 9`**（`_f 0x6305`..`0x630d` **共 9 个槽位**） | `BKID_APP_ftp_server_settings_*0..8`；**仅 Passive Mode**（`passive_mode` `0` 命中） |
| **`Secure Protocol`**（`_f 0x60dd`） | `Off`（明文 `FTP`）/ `On`（**Explicit `AUTH TLS` / `FTPES`** `_f 0x6553`）；**无 Implicit FTPS、无 SSH-SFTP** | [`libInfraFtpClient.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFtpClient.so) `@0x2e6c1` **`AUTH TLS`**、`@0x2e8a5` **`TLS_AES_256_GCM_SHA384:TLS_AES_128_GCM_SHA256`**（[`libssl.so.3`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libssl.so.3) OpenSSL 3.0）、`@0x2e6e5` `/cert/crl/tmp_crl.crl`、`curl_multi_perform`；`FX3 appFw.so` `sftp` 为 **`0` 命中** |
| **`Root Certificate Error`**（`_f 0x65f2`）& **`[Import Root Certificate]`**（`_f 0x7940`） | `Does Not Connect`（推荐）/ `Connect`（强连告警）；证书必须为 PEM 格式命名 **`cacert.pem`**（`<= 1 MB`）并置于 **Slot 1 根目录**，在 `[Network Option]` 下导入 | [`libInfraCertificate.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraCertificate.so) `@0x39a6` `cacert.pem`；[`libCertificateManager.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libCertificateManager.so) `@0x8c7e` `OCSP_cert_to_id`、`@0x25981` `/usr/share/network/cert/`、`@0x2593e` `tmp_ftp_cert_from_ncm.pem`、`@0x25bbc` `/tmp_network/ftpcert.pid` |
| **`[Save/Load FTP Settings]`**（`_f 0x71ae`） | 在 **Slot 1** 保存/加载/删除最多 **10 个** FTP 配置文件（`_g 0x6433` 含用户名与密码，需设加密密码；Load 后**重启相机**，禁止跨机型加载） | [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so) `@0x3907fc8` **`%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT`**（`FTPSET%02d` -> `SONY/SETTING/<Model>/FTPSET/FTPSET01.DAT`..`10.DAT`）；`FUNC_save_load_ftp_settings_{save,load,delete}`、`BKID_APP_save_load_ftp_settings_infra_data`（160 B）；另 `@0x392680a` `%c:%s/SONY/FTPNSEND.DAT` 与 `@0x392ecf7` `%c:%s/SONY/SPSEND.DAT` |
| **`[Auto FTP Transfer]`**（`_f 0x7b27` / `0x6e4f`） | `Off`（默认）/ `On`（拍摄期间自动推送，`Target`: `Still Image` / `Movie` `All`/`Only Shot Mark`） | `BKID_APP_setting_auto_ftp_transfer`；`BKID_APP_setting_auto_ftp_transfer_target_movie` |
| **`Transfer Target`** / **`[RAW+J/H Transfer Target]`**（`_f 0x6bd5`） | Still：`JPEG & HEIF` / `RAW` / `RAW+J & RAW+H`；Movie：`Proxy Only` / `Original Only` / `Proxy & Original`；批量筛选含 `Shot Mark` / `Rating` / `Protect` / `Clip Flag`（`OK`/`NG`/`KEEP`） | `EVENT_REMOTE_FTP_GROUP_FTP_TRANSFER_FUNC_RAW_J_H_TRANS_TRGT`；`BKID_APP_is_valid_ftp_transfer_target_image_clip_flag_{ok,ng,keep,off}` |
| **`[Directory Hierarchy]`**（`_f 0x6e7e`） | **`Standard`**（直接写入 `Specify Directory` <=128 字符）/ **`Same as in Camera`**（`_f 0x76e6`，双卡分别映射根目录 **`A/`** [Slot 1] 与 **`B/`** [Slot 2]） | `BKID_APP_ftp_server_settings_directory_hierarchy{0..8}`；`SET_SERVER_DIRECTORY_HIERARCHY_{STANDARD,SAME_AS_IN_CAMERA}` |
| **`[FTP Power Save]`**（`_f 0x6a5f`） | `Off`（默认）/ `On`（空闲超时断网省电） | `BKID_APP_setting_ftp_power_save`；`INFRA_NOTIFY_FTP_POWER_SAVE_TIMER_EXPIRED` |

### 2.2 `Slot 1` `.dat` / `AVF_INFO` 保险库冲突与 `FX3` vs `FX6` FTP 横向对比

- **工程推断（Tier-0 `Slot 1` 写危害闭环）**：`[Save/Load FTP Settings]`、[`[Import Root Certificate]`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py#L181-L202) 与 FTP 传输结果写回（`save_ftp_transfer_list_to_media`、`FTPNSEND.DAT`、`AVF_INFO` `0x0a13`）全部强绑定 **`Slot 1`**。当 `Slot 1` 承载 Tier-0 只读恢复保险库时，`[Save/Load FTP Settings] -> Save/Delete` 及指向 `Slot 1` 的传输状态持久化必须由防火墙拦截并返回 **`EROFS (errno 30)`**。
- **实测事实（`ILME-FX3` vs `ILME-FX6 Ver. 6.01` `Network > File Transfer`）**：FX6 UI 暴露 `Server Settings1..3`（ELF 底层保留 `1..16`）、支持 **`Passive Mode On/Off`**（含 Active Mode）、支持 **`Auto Upload (Proxy): Chunk`**（`ns1 0x27b3`，边录边传且占 Slot B 时硬互斥 `Simul`/`Relay`）、`Transfer Clip` 剪辑列表队列与 `certification.pem`（置于 **Slot B**）；由 `Network > Network Reset`（`All Reset`）清除。

---

## 3. 支柱三：`[Cnct./Remote Sht.]` / `[Bluetooth]` / `[Airplane Mode]`：`Creators' App` BLE 绑定、GPS 注入与零射频规则 vs `ILME-FX6`

### 3.1 `Creators' App` BLE 配对协议栈、5 张 GATT 服务表与 NVRAM 绑定生命周期（`实测事实`）

1. **Ver. 3.00–7.02 配对流与硬件能力（`ilc/2210` + UXC）**：
   - `MENU -> (Network) -> [Cnct./Remote Sht.]`（`_g 0x64c5`）-> `[Smartphone Connection]`（`_f 0x755f`），配合 `Creators' App`（`_g 0x6497`，替代已退役的 *Imaging Edge Mobile*）完成蓝牙配对与 Wi-Fi 协同（配对状态 `_g 0x64a7/0x64a8/0x64d1/0x64d2`）。
   - `[Bluetooth]` 子菜单包含：`[Bluetooth Function]`（`_f 0x723c`，默认 `Off`）、`[Pairing]`、`[Manage Paired Device]`（`_f 0x72b7`）、`[Bluetooth Rmt Ctrl]`（`_f 0x6807`，默认 `Off`）、`[Disp Device Address]`（`_f 0x6d5b`），以及 `[Cnct./Remote Sht.]` 下的 **`[Cnct. while Power OFF]`**（`_f 0x6ab3` / `_g 0x6498`）。最多保存 **15 台**已配对设备，最多 **2 路**并发连接。

2. **底层 BLE GATT 服务与 Wake-on-LE 实证（[`libInfraBluetoothLowEnergy.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraBluetoothLowEnergy.so) + [`libInfraBluetoothCore.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraBluetoothCore.so) + [`bt_stack.conf`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/bin/bt_stack.conf)）**：
   - **5 张索尼私有 128-bit GATT 服务表**（`@0x8225b..0x82300` & `@0x11393..0x113ff`）：
     1. **`8000CC00-CC00-FFFF-FFFF-FFFFFFFFFFFF`**（`g_dicamServiceTable` `@0x113bc`：数码影像相机控制与 Wi-Fi 凭证下发）；
     2. **`8000DD00-DD00-FFFF-FFFF-FFFFFFFFFFFF`**（`g_locationServiceTable` `@0x113d0`：智能手机 GPS 位置与时间联动注入）；
     3. **`8000EE00-EE00-FFFF-FFFF-FFFFFFFFFFFF`**（`g_pairingServiceTable` `@0x113a6`：ECDH 配对鉴权）；
     4. **`8000FF00-FF00-FFFF-FFFF-FFFFFFFFFFFF`**（`g_RemoteControlServiceTable` `@0x113e7`：蓝牙遥控器）；
     5. **`8000BB00-BB00-FFFF-FFFF-FFFFFFFFFFFF`**（`g_rxtxServiceTable` `@0x11393`：串口/命令双向信道）。
   - **加密与运行时状态文件**：`Service/CryptManager.cpp` 调用 OpenSSL `EVP_PKEY_derive_set_peer` 完成椭圆曲线密钥协商；GATT 服务与 CCCD 订阅状态落盘于 `/tmp_bt/BleServer.txt`（`@0x82482`）与 `/tmp_bt/CCCD.txt`（`@0x82ce7`）。
   - **关机唤醒机制（Wake-on-LE）**：[`bt_stack.conf`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/bin/bt_stack.conf)（`2,926 B`）明确配置 **`LMP_WAKEUP_CONFIG=0x03,0x0010,0x0010,0x0800,0x0024,0x03`**（`wake_sources=0x03` 同时启用 BLE + BR/EDR 唤醒，`10ms` LE 扫描间隔/窗口，`white list + undirected adv`），支撑 `[Cnct. while Power OFF] = On` 期间手机端一键唤醒关机状态的 FX3 导片。

3. **BLE Bond NVRAM 生存期矩阵（`libInfraBluetooth.so` + `ilc/2210`）**：
   - [`libInfraBluetooth.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraBluetooth.so) 通过 `libbackup.so`（`Backup_read`/`Backup_write`/`Backup_sync_subsystem`）持久存储配对密钥（[`libInfraBluetoothCore.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraBluetoothCore.so) `LE_LOCAL_KEY_{IRK,IR,DHK,ER}`），并注册回调 **`CT_ID_DELETE_SAVED_BT_DEV`** 与 **`CT_ID_NETWORK_RESET_DONE`**：
   - **`[Camera Settings Reset]`**：**不擦除** BLE Bond 绑定信息与网络设置；
   - **`[Reset Network Set.]`**（`_f 0x60d3`）与 **`[Initialize]`**：**均彻底清除**全部已配对蓝牙设备 NVRAM 绑定信息、BD 配对列表及 `[Bluetooth Function]`/`[Bluetooth Rmt Ctrl]`（复归 `Off`）。

### 3.2 `[Location Info. Link Set.]` GPS EXIF/XMP 注入与 `[Airplane Mode]` 零射频总闸 vs `ILME-FX6`

1. **GPS 位置联动演进与 EXIF/XMP/MP4 写入（`实测事实`）**：
   - **菜单迁移事实**：`ilc/2210`（Ver. 2.00+ 至 Ver. 7.02）在相机机身菜单中**已无 `[Location Info. Link Set.]`**（`_f 0x77b8` 与 `BKID_APP_setting_location_info_link` 属 Ver. 2.00 IEM 时代遗留）；现由蓝牙配对后的 **`Creators' App -> [Cameras] -> [Setup] -> [Location Information Linkage]`** 开关控制，同步提供 **`[Auto Time Correction]`**（`_f 0x6990`）与 **`[Auto Area Adjustment]`**（`_f 0x68e2`），同一时刻**仅限绑定 1 台手机**。
   - **元数据注入链路**：`Creators' App` 经 GATT `8000DD00` 向 [`libgps_rsrc.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgps_rsrc.so) 与 [`FX3 appFw.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so)（`sequence_set_bluetooth_location_info_link`、`sequence_auto_time_correction`、`sequence_auto_area_correction`、`GeoGps`、`GpsInfo`、`No12_LatitudeGPSinfo`、`No14_LongitudeGPSinfo`）注入实时经纬度与时间，写入静态图像 EXIF GPS IFD 及视频侧车 `M01.XML` / `MP4` 元数据。

2. **`[Airplane Mode]`（`_f 0x6df9`）复位真值与 Tier-0 零射频台架铁律（`实测事实` + `工程推断`）**：

| 设置项 / 射频平面 | 默认值 | `[Camera Settings Reset]` | `[Reset Network Set.]` | `[Initialize]` | Tier-0 零射频台架规则（`rf_tx_packets == 0`） |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **`[Airplane Mode]`**（`_f 0x6df9`） | `Off` | **保留不变** | **若为 `On` 则仍保持 `On`！**（`ilc/2210` 明文） | **复位为 `Off`** | **强制 `On`**（彻底关断 Wi-Fi 射频与 BT 发射，触发 `_g 0x61bf/0x6254/0x62b4`、`base 0xe727/0xea50` 阻断） |
| **`[Bluetooth Function]`** & **BLE Bond** | `Off` / 空 | **保留不变** | **复位 `Off` 并擦除 BLE Bond** | **复位 `Off` 并擦除** | **强制 `Off`**（含关闭 `[Cnct. while Power OFF]` 防关机 LE 广播/扫描） |
| **Wi-Fi (`Direct` / `AP` / `STA`)** | `Off` | **保留不变** | **复位 `Off` 并清空凭证** | **复位 `Off` 并清空** | **强制 `Off`** |
| **`[USB-LAN/Tethering]`**（有线网卡） | `Off` | **保留不变** | **复位 `Off`** | **复位 `Off`** | **必须物理/电气断开**（因 `di/ftp_2210` 实证 `Airplane Mode = On` 不阻断 Type-C `USB-LAN`） |

3. **对比 `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 appFw.so`）**：
   - FX6 **无蓝牙硬件、无 `Creators' App`、无消费级 BLE GPS 位置联动、无独立 `[Airplane Mode]` 菜单**（`FX6 appFw.so` 中的 `BKID_APP_SETTING_BLUETOOTH_FUNCTION`、`BKID_APP_SETTING_LOCATION_BY_MOBILE_APP`、`BKID_APP_EXTERN_SETTING_AIRPLANE_MODE` 均属跨机休眠符号）。
   - FX6 无线链路依赖 **`Network > Wireless LAN`**：支持 `Access Point (2.4GHz)`、`Access Point (5GHz)`（**`5GHz` 仅限 `ILME-FX6V / ILME-FX6VK`，`ILME-FX6T / TK` 仅 2.4GHz**）、`Station Mode`（支持 `WPA2-PSK` 与 `WPA3-SAE`，不支持纯 WPA3 与旧 FX6 固件混连）及 `Off`（直接关断无线传输）；配对 App 为 **`Monitor & Control`（Ver. 2.0.0+，FX6 Ver. 5.00 起已正式废除 *Content Browser Mobile*）**，依赖 `[Access Authentication]` 用户名/密码加密建链。

---

## 4. 支柱四：`Playback` 写卡操作语义与 Tier-0 `Slot 1 EROFS=30` 保险库 vs `ILME-FX6` `Thumbnail`

### 4.1 表面“只读回放”操作的真实磁盘/元数据写盘审计（`实测事实` + `工程推断`）

通过只读分析 [`libmpr.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so)（`3,517,008` B）、[`libInfraMediaCommon.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaCommon.so)、[`libInfraFsys.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraFsys.so) 与 [`libInfraAdjMedia.so`](file:///Users/kafu/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAdjMedia.so)，将 Playback 看似“仅浏览/打标”的操作的底层写卡行为彻底定性：

| 操作（UXC `resid16` / ELF 符号） | 真实文件/扇区修改对象（`实测事实`） | 底层调用链证据（`libmpr.so` / `libInfra*.so`） | Tier-0 `Slot 1` 判决（`slot1_sector_writes == 0`） |
| :--- | :--- | :--- | :--- |
| **`[Add Shot Mark 1/2]`**（录中 `_f 0x628b/0x628a`）<br>**`[Add/Delete Shot Mark 1/2]`**（回放 `_f 0x6143/0x6142`） | 就地改写 **`M4ROOT/CLIP/*M01.XML`** 非实时元数据（`EssenceMark` 节点）并同步更新 `AVF_INFO` 索引数据库 | `FUNC_CUSTOM_{ADD,EDIT}_SHOT_MARK_{1,2}_ON`；`libmpr.so` `SetEssenceMarkInRec`（`@0x1f73d`）、`SetEssenceMarkInPlay`（`@0x1f79c`）、`NonRealTimeMeta`（`@0x2d4218`）、`M01.XML`（`@0x2cb3a3`） | **`BLOCKED -> EROFS (30)`**<br>（若目标卡为 `Slot 1`） |
| **`[Rating]`**（`1..5` 星，`_f 0x684f` / `_g 0x6039`） | 改写静态 JPEG/HEIF XMP `<xmp:Rating>` 段或视频侧车/媒体库分级字段 + `AVF_INFO` | `FUNC_CUSTOM_ADD_RATING_{1..5}_ON`；`libmpr.so` `SetXmpRating`（`@0x2dcc10`）、`<xmp:Rating>0</xmp:Rating>`（`@0x2dc752`）、`HEIFCoreIC::getRatingArea`、`mpr::RatingMovie` | **`BLOCKED -> EROFS (30)`** |
| **`[Protect]`**（`base 0xe2c9` / `_g 0x6362`） | 修改 FAT32/exFAT 目录项只读属性位（`chmod`）并重写 `AVF_INFO` / `MEDIAPRO.XML` | `FUNC_protect_content`；`libInfraFsys.so` `Fsys_Chmod` / `pf_chmod` / `PFVOL_IsWriteProtected`；`libInfraMediaCommon.so` `tntfs_chmod` / `tntfs_fchmod` / `perm_wr_protect` | **`BLOCKED -> EROFS (30)`** |
| **`[Delete]`**（`base 0xe504` / `_g 0x6259`） | 释放媒体文件簇链（含成对 Proxy 视频）、重写 **`/M4ROOT/MEDIAPRO.XML`** 与 `AVF_INFO` | `FUNC_delete_content`；`libmpr.so` `/M4ROOT/MEDIAPRO.XML`（`@0x2cb9f0`）；`libInfraMediaCommon.so` `AllocDirEntRange` | **`BLOCKED -> EROFS (30)`** |
| **`[Copy]` (`Slot 1 -> Slot 2`)**<br>（`_f 0x79fc` / `FUNC_copy_content`） | 仅以只读方式读取 `Slot 1` 源媒体，向 `Slot 2` 写入新文件与 `Slot 2` 数据库（注意目标卡不继承 Protect 与连拍组） | `FUNC_copy_content`、`get_battery_status_for_copy`；`libInfraAdjMedia.so` `COPY_LIBRARY`、`Usage : duplicate dst <slot1/slot2/slot3>` | **`ALLOWED`（`Slot 1` 零写入）**<br>仅限 `Slot 2` 可写且电量/卡速达标 |
| **`[Copy]` (`Slot 2 -> Slot 1`)** | 试图向 `Slot 1` 写入文件、目录项、`/M4ROOT/MEDIAPRO.XML` 与 `AVF_INFO` | `libInfraMediaMount.so` `MCMN_E_WRITEPROTECTED`；`libInfraAdjMedia.so` `Destination Media is write protected`；`FX3 appFw.so` `MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1` | **`BLOCKED -> EROFS (30)`**<br>（触发 `Slot 1` 写保护防火墙） |

> [!CAUTION]
> **工程推断（Tier-0 `Slot 1 EROFS=30` 防火墙铁律）**：在 FX3 恢复/仿真实验室中，只要 `Slot 1` 挂载只读保险库（`slot_1_contains_tier0_vault = True`），任何打开 `Slot 1` 文件描述符 `O_RDWR`/`O_WRONLY` 或调用 `chmod`/`unlink`/`rename` 的操作——无论是 Playback `[Shot Mark]`、`[Rating]`、`[Protect]`、`[Delete]`、`Copy (Slot 2 -> Slot 1)`、`[Photo Capture]`，还是 Network `[Save/Load FTP Settings]`（`.dat`）与 `AVF_INFO` 恢复——都必须**确定性 fail-closed 并向上层返回 `EROFS (errno 30)`**，维持 `slot1_sector_writes == 0`。

### 4.2 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` `Thumbnail` 与标记系统对比（`实测事实`）

- **`ILME-FX3 Ver. 7.02`**：活跃使用 **`Shot Mark 1 / Shot Mark 2`**（录制与回放均可增删，支持后拨盘暂停跳转、`Image Jump Setting` 筛选及 `FTP`/`Creators' App` 筛选推送）、**`Clip Flag`（`OK` / `NG` / `KEEP`）**（Ver. 6.00+/7.00+ 起活跃支持并可随 `Monitor & Control` / `FTP` 筛选）以及 **`Rating`（1..5 星）**；机内不提供 `Divide Clip`。
- **`ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 appFw.so/UXC`）**：`Thumbnail` 菜单直接管理 **`Set Clip Flag`（`OK` / `NG` / `KEEP`）**（配合机身 `ASSIGNABLE_SWITCH_CLIP_FLAG_{OK,NG,KEEP}`，注意 `Monitor & Control` App 矩阵中 FX6 不支持 App 内一键标 `CLIP FLAG`）、`Lock/Unlock Clip`（`BKID_APP_USER_MENU_LOCK_UNLOCK_CLIP*`）、`Delete Clip` 与 `Copy Clip`；**`Shot Mark 0..9`**（`FX6 ns1 0x26f6/0x32dd/0x326c`）与 **`Essence Mark`**（`ns1 0x28e8`, `ns2 0x4045/0x4047`）源于 XDCAM 与已退役的 *Content Browser Mobile*，在 FX6 Ver. 6.01 常规界面中处于休眠状态；同样无 `Rating` 星级，无机内 `Divide Clip`。

---

## 5. 取证账本：Donor 工件 SHA-256 与四语 UXC `resid16` 对齐验证（`实测事实`）

### 5.1 核心 ELF / `.so` / 配置文件 / NVRAM 种子 SHA-256 账本（`os.O_RDONLY` 实测）

| Donor 工件路径（相对 `/Users/kafu/AI-Workspace/AI/Projects/Mac/work/`） | 字节数 | SHA-256 校验和 | 关键实测偏移 / 签名 |
| :--- | ---: | :--- | :--- |
| `fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so` | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `FTPSET`: `0x3907fc8`; `FTPNSEND`: `0x392680a`; `REGENRATE`: `0x3b149b5` |
| `.../regular-files/usr/lib/libInfraFtpClient.so` | `232,368` | `76047761b7e2e00e1c2719bbacdec9e0e704dc86dd6b74de556616bb64e1bc4c` | `AUTH TLS`: `0x2e6c1`; `TLS_AES_256...`: `0x2e8a5`; `tmp_crl`: `0x2e6e5` |
| `.../regular-files/usr/lib/libCertificateManager.so` | `186,472` | `b4ed2680bb4b000b2078f3172ad229e001cd3f91bf767f9df01d6c83363d32d6` | `OCSP_cert_to_id`: `0x8c7e`; `tmp_ftp_cert_from_ncm.pem`: `0x2593e` |
| `.../regular-files/usr/lib/libInfraCertificate.so` | `22,872` | `62eb178eefe13725d299c03b132ff64441426655e265ab976e7843c7c8345fc8` | `cacert.pem`: `0x39a6`; `certification.pem`: `0x3925` |
| `.../regular-files/usr/lib/libssl.so.3` | `574,464` | `27bc25f1e766877b72888dba67dc60fe4589c4a7b253c9324fce8c8ad1913f21` | `OPENSSL_3.0.0` TLS 1.2/1.3 底层引擎 |
| `.../regular-files/usr/lib/libInfraBluetooth.so` | `158,968` | `e49bb8fbb723eef65d4b4e54788c39f57b1cd7ca72285bc02a726ada2ca8ef93` | `CT_ID_NETWORK_RESET_DONE`、`CT_ID_DELETE_SAVED_BT_DEV` |
| `.../regular-files/usr/lib/libInfraBluetoothCore.so` | `267,592` | `fcfb4a0086220c53a002394d268c3fb423f6cbf925beaca8ec34a409b3de566b` | `/usr/bin/bt_stack.conf`、`LE_LOCAL_KEY_{IRK,IR,DHK,ER}` |
| `.../regular-files/usr/lib/libInfraBluetoothLowEnergy.so` | `648,328` | `2d3d72bd08e1dd2bbff9d6af82af74d5d892f56faf103a6dbcf33be22609966a` | 5 张 GATT 表 `@0x11393..0x113ff` & UUID `@0x8225b..0x82300` |
| `.../full-v4/regular-files/usr/bin/bt_stack.conf` | `2,926` | `159f5529180e5d4544d8b17d08985f74acfeba452ec6a982a02a43b3be172335` | `LMP_WAKEUP_CONFIG=0x03,0x0010,0x0010,0x0800,0x0024,0x03` |
| `.../regular-files/usr/lib/libInfraAirplaneMode.so` | `14,488` | `dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea` | `Backup_read/write`、`infra_airplane_mode_init` |
| `.../regular-files/usr/lib/libgps_rsrc.so` | `23,824` | `d0f04f180576dc543a7a16bd250f7c22e3ec540731d3f247493b9ab0b0e4c116` | `GpsRsMainThread`、`PsmGpsRsApiInfraMsgCb` |
| `.../regular-files/usr/lib/libmpr.so` | `3,517,008` | `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c` | `MEDIAPRO.XML`: `0x2cb9f0`; `SetXmpRating`: `0x2dcc10`; `SetEssenceMark*` |
| `.../regular-files/usr/lib/libInfraMediaCommon.so` | `402,624` | `1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b` | `EROFS`、`tntfs_chmod`、`perm_wr_protect` |
| `.../regular-files/usr/lib/libInfraAdjMedia.so` | `318,152` | `caae47cd50a72816f75515724828a0d136985844fe3b9a13ad0fda15b08dbf11` | `COPY_LIBRARY`、`Destination Media is write protected` |
| `.../regular-files/usr/lib/libInfraFsys.so` | `683,632` | `ec0dcdfa2bd0bb9236137821ecd620ea4c726adc4b5455da9ced25287f158651` | `PFVOL_IsWriteProtected`、`Fsys_Chmod`、`pf_rename` |
| `.../regular-files/usr/lib/libInfraMediaMount.so` | `65,392` | `33b4c61c39f724e08e1bc4d07fd505a799ee37a9c1f37a43fffc7c2c9c8f75ad` | `MCMN_E_WRITEPROTECTED`、`isWriteProtected` |
| `.../original-seeds/FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | `BK4\x00` 完整 NVRAM 种子（含 `TC/UB`、`FTPSET` 等出厂基线） |
| `fx3-color-port-20261027/.../nflasha15-files/lib/appFw.so` | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `PRODUCT_MODEL_CHAPLIN`、FX6 Ver. 6.01 对比基线 |

### 5.2 FX3 & FX6 四语 UXC `resid16` 对齐精选表（`EN / SC / TC / JP`）

| 包 / `resid16` | English (`EN`) | 简体中文 (`SC`) | 繁體中文 (`TC`) | 日本語 (`JP`) |
| :--- | :--- | :--- | :--- | :--- |
| `FX3 _g 0x6389` / `_f 0x6b0c` | `TC/UB` / `TC/UB Disp. Setting` | `TC/UB` / `TC/UB显示设置` | `TC/UB` / `TC/UB顯示設定` | `TC/UB` / `TC/UB表示設定` |
| `FX3 _f 0x6b63` / `0x6b79` | `Time Code Preset` / `Time Code Make` | `Time Code Preset` / `Time Code Make` | `Time Code Preset` / `Time Code Make` | `Time Code Preset` / `Time Code Make` |
| `FX3 _f 0x6317` / `0x71ae` | `FTP Transfer Func.` / `Save/Load FTP Settings` | `FTP传输功能` / `保存/加载FTP设置` | `FTP傳輸功能` / `儲存/載入FTP設定` | `FTP転送機能` / `FTP設定の保存/読込` |
| `FX3 _f 0x60dd` / `0x6553` / `0x7940` | `Secure Protocol` / `Connects with FTPES.` / `Import Root Certificate` | `安全协议` / `连接FTPES。` / `导入根证书` | `安全通訊協定` / `連線到FTPES。` / `匯入根憑證` | `セキュアプロトコル` / `FTPESで接続します` / `ﾙｰﾄ証明書の読み込み` |
| `FX3 _g 0x64c5` / `0x6497` / `_f 0x6ab3` | `Cnct./Remote Sht.` / `Creators' App` / `Cnct. while Power OFF` | `连接/遥控拍摄` / `Creators' App` / `关机时连接` | `連線/遙控拍攝` / `Creators' App` / `關閉電源時連線` | `接続/ﾘﾓｰﾄ撮影` / `Creators' Appのご案内` / `電源OFF中の接続` |
| `FX3 _f 0x77b8` / `0x6df9` / `0x60d3` | `Location Info. Link Set.` *(Legacy)* / `Airplane Mode` / `Reset Network Set.` | `位置信息链接设置` / `飞行模式` / `复位网络设置` | `位置資訊連結設定` / `飛航模式` / `重設網路設定` | `位置情報連動設定` / `機内モード` / `ﾈｯﾄﾜｰｸ設定リセット` |
| `FX3 _f 0x628b` / `0x684f` / `base 0xe2c9` / `_f 0x79fc` | `Add Shot Mark1` / `Rating` / `Protect` / `Copy` | `添加Shot Mark1` / `分级` / `保护` / `复制` | `新增Shot Mark1` / `等級` / `保護` / `複製` | `Shot Mark1追加` / `レーティング` / `プロテクト` / `コピー` |
| `FX6 ns2 0x50c2` / `0x50c7` / `0x456b` / `0x5438` | `EXT-LK` / `TC IN` / `TC Out` / `DURATION/TC/U-BIT` | `EXT-LK` / `TC IN` / `TC输出` / `DURATION/TC/USERS BIT` | `EXT-LK` / `TC IN` / `TC輸出` / `DURATION/TC/U-BIT` | `EXT-LK` / `TC IN` / `TC出力` / `DURATION/TC/U-BIT` |
| `FX6 ns1 0x3224` / `0x32b9` / `0x329f` | `Clip Flag OK` / `Clip Flag NG` / `Clip Flag Keep` | `片段旗标OK` / `片段旗标NG` / `片段旗标Keep` | `短片旗標OK` / `短片旗標NG` / `短片旗標Keep` | `クリップフラグOK` / `クリップフラグNG` / `クリップフラグKeep` |

*(注：FX3 12 份 UXC 与 FX6 8 份 UXC 已通过只读解析验证：`FX3 base` 2,692 槽位 / `_g` 1,390 项四语 100% 对齐；`_f` 采用稀疏差分表结构，英文含 1,344 条有效偏移项、简中/繁中 1,707 条、日文 1,289 条，四语对应记录均完整可解。)*

---

## 6. `fx3-safety` 守卫交叉审计与 `80/80 Waves` 收官总结

1. **`fx3-safety` 守卫对齐与勘误项（`实测事实` + `工程推断`）**：
   - **`G114` 勘误（需后续跟进修正）**：[`realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_usb_mode_hdmi_info_protect_network_reset_and_114gate_guard.py#L245) 中 `NETWORK_RESET_CLEARED_CATEGORIES_G114` 误列 `"Airplane Mode (reset to Off)"`。基于 `ilc/2210` 实证，**`[Reset Network Set.]` 保留 `Airplane Mode = On`，仅 `[Initialize]` 将其复位为 `Off`**（本报告严格不改动 `outputs/fx3-safety/`，留作后续 guard 微调追踪）。
   - **`G126` / `G128` / `G141` 验证绿色一致**：[`G128`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_switch_vh_af_stdadj_bracket_tcub_copy_slot_and_128gate_guard.py) 对 `[TC/UB]` 6+1 项抗 Reset、`23.98p`/`24.00p`/PAL NDF 锁及 `Copy (Slot 2 -> Slot 1)` `EROFS` 拦截完全精准；[`G141`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_ftp_ftpes_customwb_af_focusmap_marker_and_142gate_guard.py) 对 FTP 9 槽位、`FTPES` 独占、`cacert.pem` 与 `Slot 1` 写危害判定完全一致；[`G126`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h460-global-sony-wave80-milestone-tc-ub-ftp-creatorsapp-ble-shotmark-intel/outputs/fx3-safety/fx3_safety/realhw_lens_comp_af_illuminator_aperture_drive_folder_rating_and_126gate_guard.py) 对 `[Rating]` 写卡阻断精准。
2. **`80/80 Waves` 全系列里程碑收官姿态**：
   - 截至 **Wave 80（`80/80 Waves`）**，`ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 的全量菜单树、物理端口拓扑、加密与无线/蓝牙 GATT 协议栈、存储卡元数据写盘语义、Reset/Initialize 持久化边界及 Tier-0 只读保险库（`slot1_sector_writes == 0`、`rf_tx_packets == 0`、`emmc_writes_authorized = False`）已实现端到端全覆盖闭环。
