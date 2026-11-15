# Phase 152（第 31 号审计器）：真机 Wi-Fi (`802.11ac`)、`BLE Creators' App` vs FX6 M&C、USB Type-C (`MSC 054C:0DA1` / `MTP` / `UVC`) 与有线 `USB-LAN` FTP 桥接审计报告

- **任务编号**：`H164 / Phase 152`
- **关联情报**：[Wave-19 SPI-NOR `/dev/mtd0ro` / eMMC `EXT_CSD` ISP / Sony 无线与 USB 架构情报报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/reports/2026-11-15-global-sony-wave19-spi-nor-mtdro-emmc-isp-wireless-intel/README.md)
- **目标架构**：Hybrid Userland Stage-B（`FX6 v6.01 appFw.so` + `LD_PRELOAD libgrm-fbinit9.so` 运行于 Stock FX3 `v7.02` `4.9.337-scel+` 内核与原厂 `cpapp-b.bin` RTOS 之上）
- **核心红线**：100% `os.O_RDONLY` + `mmap.ACCESS_READ` 只读静态审计 + 确定性 Clean-Room 回退；严格锁定 `p12/p13` RF TX 功率与 MAC/BD_ADDR NVS（`rf_nvs_p12_p13_writes_permitted == False`、`rf_nvs_mutation_bytes == 0`），确保 USB `MSC (054C:0DA1)` 与 `SERVICE (054C:0336)` 恢复口永不被破坏（`usb_msc_0da1_recovery_intact == True`），消除 FX6/FX3 BT/BLE 守护进程阻塞（`bt_hci_blocking_wait_ms == 0`、`bt_hci_blocking_wait_eliminated == True`），状态叠加严格限制在 `/tmp/` / `ram://`（`persistent_emmc_writes_authorized == False`、`emmc_mutation_bytes == 0`）。

## 1. 本次修改文件清单（严格限定 7 个 Owned Files）

| 序号 | 文件 | 职责 |
| :--- | :--- | :--- |
| 1 | [Wave-19 Global Intelligence README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/reports/2026-11-15-global-sony-wave19-spi-nor-mtdro-emmc-isp-wireless-intel/README.md) | Wave-19 `/dev/mtd0ro` SPI-NOR、eMMC `EXT_CSD[179]` ISP 与 Sony `Monitor & Control` / USB-LAN / Wi-Fi / UVC 公开情报 |
| 2 | [realhw_wifi_bt_usb_uvc_network_bridge_auditor.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wifi_bt_usb_uvc_network_bridge_auditor.py) | 第 31 号统一审计器（4 大支柱 + 12 触点 4 分类兼容矩阵 + `p12/p13`/eMMC 写保护卫士） |
| 3 | [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) | 导出 Phase 152 常量、数据类、评估函数与 `__all__` 符号 |
| 4 | [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) | 新增 CLI 子命令 `audit-realhw-network-usb-bridge` 并接入 `audit-all`（汇总 `31/31`） |
| 5 | [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/README.md) | 更新第 31 号审计器说明与 CLI 用法示例 |
| 6 | [test_realhw_wifi_bt_usb_uvc_network_bridge.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/tests/test_realhw_wifi_bt_usb_uvc_network_bridge.py) | 46 项双模式（Local Donor / Clean-Room）单元测试 |
| 7 | [Phase 152 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/reports/2026-11-15-phase152-realhw-wifi-bt-usb-uvc-network-bridge/README.md) | 本期 Phase 152 结项报告 |

## 2. 实测事实与未执行边界（严格区分）

### 2.1 `O_RDONLY` 本地 Donor 实测事实（FX3 v7.02 vs FX6 v6.01）

通过 [`analyze_realhw_wifi_bt_usb_uvc_network_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wifi_bt_usb_uvc_network_bridge_auditor.py#L996) 对本地 30 份 BYOF 镜像执行 `os.O_RDONLY` + `mmap.ACCESS_READ` 实测（单次全量耗时 **`0.629 s` < `1.5 s`**，SHA-256 `112a62d14282bfa4b822514be561eb56c55908fa8bcea68a18153cb2bcc3df04`）：

- **被测 Donor 字节与符号规模（`O_RDONLY`）**：
  - `appFw.so`：FX3 `79,015,712 B` vs FX6 `50,520,424 B`
  - `libsencore.so`：FX3 `377,328 B` vs FX6 `401,952 B`（双方导出/导入符号一致：**`355` exports / `130` imports**；共享 `START_WIFI_CHECK` / `LOAD_BT_FIRMWARE` / `PREPARE_BT_DEV_ADDR` / `USB_ETHER_FORCE_MODE_SET`，FX6 额外新增 `WIREDLAN_NETIF_DOWN`、`WIREDLAN_WOL_ENABLE`、`WIREDLAN_WOL_CTRL_*`、`USB_SEL_ALT_MODE`）
  - `cpapp-b.bin`：FX3 `15,980,568 B` vs FX6 `17,952,816 B`（共享 `DFS_FACTOR_WIFI_CONNECT`、`DFS_FACTOR_USB_CONNECT`、`GpHCI`、`HCIpJ`，FX3 含 `DFS_FACTOR_ETHER_CONNECT`）
  - `Backup.bin`（`BK4\x00` 双记录）：FX3 `2,229,740 B`（`819` 子系统）vs FX6 `2,253,333 B`（`840` 子系统），32-bit 校验和全部有效
  - `im.elf`：FX3 与 FX6 均为 **`40,920 B`**（`11` exports / `85` imports 完全一致）
  - **完全一致的共享动态库 ABI**：
    - `libInfraMscServer.so`：FX3 = FX6 = `64,456 B`（**`125` exports / `69` imports**，`0` 差异）
    - `libUsbControl.so`：FX3 = FX6 = `135,424 B`（**`351` exports / `128` imports**，`0` 差异）
    - `libWlanAdjust.so`：FX3 = FX6 = `73,168 B`（**`188` exports / `119` imports**，`0` 差异，绑定 `/dev/nflasha23/INFO/WIFI_INF.TXT`、`WPS_PIN.TXT`）
    - `libWlanResource.so`：FX3 = FX6 = `56,464 B`（**`94` exports / `90` imports**，内嵌 `/usr/kmod/wlan.ko`、`bdwlan30_1vy_rc_sHH.bin`、`qwlan30.bin`、`MurataTypeTP.bin`、`otp.bin`）
  - **跨机身差异共享动态库**：
    - `libInfraBluetoothCore.so`：FX3 `267,592 B`（`509` exp / `108` imp）vs FX6 `267,576 B`（`503` exp / `111` imp，共享 `/dev/ttyAMA3`、`/tmp_bt/bsa_s_pid`）
    - `libInfraBluetoothLowEnergy.so`：FX3 `648,328 B`（`1,340` exp / `173` imp）vs FX6 `530,488 B`（`1,053` exp / `137` imp）
    - `libInfraUsbCmn.so`：FX3 `159,504 B`（`479` exp / `79` imp）vs FX6 `164,144 B`（`503` exp / `80` imp）
    - `libInfraPtpControl.so`：FX3 `165,320 B`（`456` exp / `117` imp）vs FX6 `152,520 B`（`435` exp / `113` imp）
    - `libNetServiceEther.so`：FX3 `114,384 B`（`286` exp / `94` imp）vs FX6 `175,376 B`（`480` exp / `96` imp，FX6 新增 `WESStartCableLinkCheck` / `WESReconnect` / `NseMiscGetStatusEther`）
    - `libInfraFtpClient.so`：FX3 `232,368 B`（`599` exp / `215` imp）vs FX6 `231,816 B`（`605` exp / `144` imp）
- **4 大支柱与 12 触点兼容矩阵（`NATIVE_PASSTHROUGH=4` / `SHIM_TRANSLATED=4` / `MASKED_ABSENT_HW=3` / `HARD_WRITE_PROTECTED=1`）**：
  - [`evaluate_wifi_rf_nvs_isolation`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wifi_bt_usb_uvc_network_bridge_auditor.py#L622)：`802.11ac` 2.4/5 GHz 与 `P12` 飞行隔离受控放行，`p12:/cert` / `p13` RF TX 功率与 `WIFI_INF.TXT` 写请求 100% 硬阻断（`rf_nvs_p12_p13_writes_permitted == False`、`rf_nvs_mutation_bytes == 0`）。
  - [`evaluate_bt_ble_daemon_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wifi_bt_usb_uvc_network_bridge_auditor.py#L670)：屏蔽 FX6 `appFw.so` 对缺失 BLE/BT 守护进程的阻塞等待（`bt_hci_blocking_wait_ms == 0`、`bt_hci_blocking_wait_eliminated == True`），将远程监看路由至 Wi-Fi/LAN 版 `Monitor & Control`。
  - [`evaluate_usb_multi_role_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wifi_bt_usb_uvc_network_bridge_auditor.py#L720)：原生保留 `MSC (054C:0DA1)` + `SERVICE (054C:0336)` 救砖与 `MTP/PTP Remote`，并将 FX6 `USB_STREAMING` ProCam UVC 端点掩蔽为 `HDMI-to-UVC` 外接路径，阻断任何劫持 `054C:0DA1` 恢复口的行为（`usb_msc_0da1_recovery_intact == True`）。
  - [`evaluate_wired_ether_ftp_mc_bridge`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h164-phase152-wave19-intel-wifi-bt-usb-uvc-bridge/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wifi_bt_usb_uvc_network_bridge_auditor.py#L783)：支持 `CDC-NCM` (`RTL8153`/`AX88179` 1000 Mbps) FTP/FTPES 与 `Monitor & Control` (`PTP-IP TCP/15740`)，非阻塞掩蔽 FX6 独有 `WIREDLAN_WOL_*` PCIe NIC，同时在 `P12` 飞行隔离下拒绝无线 `wlan0`。

### 2.2 尚未在真实物理 ILME-FX3 机身上执行的实机测试（明确未测项）

以下项目属于真机上电运行时验证，**本次仅完成静态 `O_RDONLY` ELF/Token/BK4 分析与 Clean-Room 合同验证，尚未在物理 ILME-FX3 相机上执行**：
1. 真实物理 ILME-FX3 运行 Stage-B 时插拔 `USB-C CDC-NCM`（`RTL8153`/`AX88179`）千兆网卡与 `Monitor & Control` App 实机联调及 FTPES 大文件传输吞吐。
2. 真实物理机身切换到 `Mass Storage` 后，主机端校验 `054C:0DA1` 与 *Senser* `054C:0336` 枚举及断电重插恢复验证。
3. 物理机 `5 GHz 802.11ac` 射频连接及 `P12` 飞行模式开关切换时，内核 `wlan.ko` 与 `/dev/ttyAMA3` 实机 `dmesg` 零阻塞验证。

## 3. 定向验证结果

| 验证命令 | 模式 | 结果 |
| :--- | :--- | :--- |
| `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_wifi_bt_usb_uvc_network_bridge.py` | Local Donor | **46/46 PASS**（`3.782s`） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_wifi_bt_usb_uvc_network_bridge.py` | Clean-Room | **45 PASS / 1 SKIP**（`0.731s`，仅跳过本地 donor 专属断言） |
| `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | Local Donor 全量 | **1018/1018 PASS**（`38.564s`） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | Clean-Room 全量 | **1016 PASS / 2 SKIP**（`20.194s`） |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | Hygiene / Clean-Room | **ALL GREEN**（`0.06s`） |
