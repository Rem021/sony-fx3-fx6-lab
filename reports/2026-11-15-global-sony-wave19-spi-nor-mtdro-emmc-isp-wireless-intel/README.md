# Wave-19 Global Public Intelligence Report: `CXD90057` SPI-NOR / `/dev/mtd0ro` vs `/dev/mtd0`, eMMC `EXT_CSD` Off-Chip ISP Backup, and Sony BIONZ XR `Monitor & Control` / USB-LAN / Wi-Fi / UVC Architecture

- **日期**：2026-11-15
- **任务**：Task H164 — Phase 152（Wave-19 全球公开情报 + 第 31 号真机 Wi-Fi/BT/USB/UVC/USB-LAN 桥接审计器）
- **信息分层原则**：严格区分 **公开互联网实证（Web Search）**、**本地只读供体实测（`os.O_RDONLY`）** 与 **未执行项（物理真机硬件上电与离线 ISP 焊盘读写未在本工作站执行）**。

---

## 1. 结论先行（4 条核心情报）

1. **Linux `/dev/mtd0ro` vs `/dev/mtd0` SPI-NOR 只读转储机制**：Linux `mtdchar`（`drivers/mtd/mtdchar.c`，字符设备主设备号 `90`）为每个 MTD 分区成对分配次设备号——`/dev/mtdN` 为偶数（`2*N`），`/dev/mtdNro` 为奇数（`2*N+1`）。`mtdchar_open()` 检测 `(file->f_mode & FMODE_WRITE) && (minor & 1)` 直接返回 `-EACCES`，`mtdchar_ioctl()` 对非可写描述符调用 `MEMERASE`/`MEMWRITE`/`MEMLOCK` 返回 `-EPERM`，而 `MEMGETINFO`/`MEMISLOCKED` 仍可用。对纯 NOR 闪存转储，应优先读取 `/dev/mtd0ro`（`dd if=/dev/mtd0ro of=spi_nor.bin bs=64k` 或 `mtd_debug read /dev/mtd0ro`），且因 SPI-NOR 无 NAND OOB/坏块表，禁止误用 `nanddump`。
2. **eMMC `EXT_CSD` 与 `BOOT_PARTITION_ENABLE`（`EXT_CSD[179]`）离线 ISP 备份守则**：依据 JEDEC `JESD84-B51`，`EXT_CSD[179]`（`PARTITION_CONFIG`）同时承载非易失性启动位 `BOOT_ACK`（bit `[6]`）、`BOOT_PARTITION_ENABLE`（bits `[5:3]`：`0x0` 禁止、`0x1` `boot0/ROM2`、`0x2` `boot1/ROM3`、`0x7` `UDA`）与易失性访问窗口 `PARTITION_ACCESS`（bits `[2:0]`：`0x0` UDA、`0x1` boot0、`0x2` boot1、`0x3` RPMB）。ISP 备份必须在保持 SoC 复位/断电隔离、匹配 `VCCQ`（`1.8V`/`3.3V`）与短飞线（`< 10 cm`）的前提下，连续两次读取并比对 `512 B` `EXT_CSD` + `CID` + `CSD`；任何读切区必须采用 `(orig_179 & 0xF8) | target_access` 的 Read-Modify-Write，绝不可覆写 bits `[6:3]` 或触发一次性 OTP 字段 `EXT_CSD[162]`（`RST_n_FUNCTION`），且 `RPMB` 物理不可纯克隆。
3. **`CXD90057`（AP）+ `CXD90058`（CP）双芯片 SPI-NOR 与 eMMC 拓扑**：公开社区（`DavidBuchanan314/ILCE-7M4-RE`、`Hearts-Ace/sony-a7r5-custom-firmware`）已确认 BIONZ XR 架构包含运行 Linux 的 `CXD90057`（`ARM64 Cortex-A35`，挂载 eMMC `SDM2`）与运行 TOPPERS/FMP RTOS 的 `CXD90058`（`ARM Cortex-R5`）。本地 `O_RDONLY` 供体进一步实证 FX3/FX6 采用 64 MiB 物理 SPI-NOR（`0x000000-0x1FFFFF` 为 `loader_nor.bin`，`0x200000+` 为 `--swap16` 的 `CPAPP-B.BIN`，经 `nor_loader_writer.sh` / `nor_update` 写入而非 fastboot `nflasha8`），而 AP 启动后通过 `/dev/nflasha*`/`/dev/cnflasha*`（AES-XTS-256 `SPAcc`）访问 eMMC，其中 `p12/p13` 承载不可修改的无线校准/MAC/证书。
4. **Sony BIONZ XR `Monitor & Control` / USB-LAN / Wi-Fi / UVC 实机特性差异**：公开索尼官方手册与 `Monitor & Control` 发行说明确认——**FX3（v7.00/v7.02）** 原生支持低功耗蓝牙（BLE）配对 `Creators' App`、Wi-Fi AP/Router、开机自动识别 USB-LAN 适配器、Direct USB Remote Shooting、RTMP/RTMPS 推流与 `Monitor & Control v2.4.0+`；**FX6** 无蓝牙配对硬件，支持 Wi-Fi AP/Router、USB-LAN、`USB Tethering`（明确不支持 iPadOS/macOS）与 `Monitor & Control v2.5.0+`。**关键公开实证：FX3 与 FX6 均不具备 FX30/FX2/ZV-E1 那样的免驱 USB-C `USB Streaming (UVC)` 机身菜单**（FX3 可配合 `Imaging Edge Webcam`，二者在 4K 无压缩/低延迟直播场景均依赖 `HDMI -> UVC` 外置采集卡）。因此 Stage-B 运行 FX6 `appFw.so` 时，必须屏蔽不匹配的 BT/BLE 守护阻塞与 `FX6 ProCam USB Streaming` 悬空端点，同时保持 USB `MSC (054C:0DA1)` 与 `SERVICE (054C:0336)` 救砖恢复通路 100% 畅通。

---

## 2. 主题 A：Linux `/dev/mtd0ro` vs `/dev/mtd0` SPI-NOR 只读转储机制

| 维度 | `/dev/mtdN`（可读可写设备） | `/dev/mtdNro`（只读镜像节点） | 对 FX3/FX6 工程的约束 |
| :--- | :--- | :--- | :--- |
| 内核字符设备编号 | Major `90`，Minor `2 * N` | Major `90`，Minor `2 * N + 1` | 内核态仅靠次设备号最低位（`minor & 1`）硬性区分权限，不依赖用户态 `chmod` |
| `open(..., O_WRONLY\|O_RDWR)` | 经 `mtdchar_open()` 允许打开 | 返回 **`-EACCES`**（`Permission denied`） | 取证与镜像备份脚本统一打开 `/dev/mtd0ro`，从内核层物理杜绝误写 SPI-NOR |
| `ioctl()` 行为（`drivers/mtd/mtdchar.c`） | 允许 `MEMERASE`、`MEMWRITE`、`MEMLOCK`、`MEMUNLOCK` | 擦/写/锁类 `ioctl` 返回 **`-EPERM`**；只读查询 `MEMGETINFO`、`MEMISLOCKED`、`MEMGETREGIONCOUNT` 正常返回 | 可安全查询 `mtdinfo /dev/mtd0ro`（块大小/擦除扇区/总容量）而不触发任何写时序 |
| 转储工具选择 | 仅限明确的刷写流程（且不可跨机型混刷） | `dd if=/dev/mtd0ro of=nor.bin bs=64k conv=sync` 或 `mtd_debug read /dev/mtd0ro 0 <len> nor.bin` | SPI-NOR 为线性地址空间、无 OOB/ECC 坏块跳转，严禁使用 `nanddump` |

---

## 3. 主题 B：eMMC `EXT_CSD` 与 `BOOT_PARTITION_ENABLE`（`EXT_CSD[179]`）ISP 离线备份

### 3.1 `EXT_CSD[179]`（`PARTITION_CONFIG`，JEDEC JESD84-B51）位域规范

| 位域 | 名称 | 属性 | 关键枚举与含义 | 风险提示 |
| :--- | :--- | :--- | :--- | :--- |
| `[7]` | Reserved | 保留 | 恒为 `0` | 保持原值不变 |
| `[6]` | `BOOT_ACK` | **非易失性（NV）** | `1` = SoC 上电发送 `CMD0` 启动应答 `010`；`0` = 无应答 | 若修改后与 `CXD90057` BootROM 期望不一致，直接导致黑砖不上电 |
| `[5:3]` | `BOOT_PARTITION_ENABLE` | **非易失性（NV）** | `0x0` 禁止 boot、`0x1` Boot Partition 1（`boot0`/`ROM2`）、`0x2` Boot Partition 2（`boot1`/`ROM3`）、`0x7` User Data Area | 离线 ISP **绝对禁止改变此 3 bit**；切换读取目标区时必须以 `(orig & 0xF8) \| access` 掩码写入 |
| `[2:0]` | `PARTITION_ACCESS` | **易失性（上电复位归 `0`）** | `0x0` UDA、`0x1` `boot0`、`0x2` `boot1`、`0x3` `RPMB`、`0x4..0x7` `GP1..GP4` | 仅用于引导读取各物理逻辑区，重上电自动恢复 |

### 3.2 离线 ISP 取证关键校验字段与实操红线

- **必读完整 512 B 寄存器镜像**：同时备份 `CID`（16 B）、`CSD`（16 B）与 `EXT_CSD`（512 B），至少核对：
  - `EXT_CSD[177]` `BOOT_BUS_CONDITIONS`（总线位宽 1/4/8-bit 与 SDR/DDR 启动模式，NV）；
  - `EXT_CSD[178]` `BOOT_CONFIG_PROT`（检查 boot 配置是否受写保护）；
  - `EXT_CSD[226]` `BOOT_SIZE_MULTI`（`boot0`/`boot1` 单区大小 `= reg * 128 KiB`）；
  - `EXT_CSD[215:212]` `SEC_COUNT`（`UDA` 总扇区数 `* 512 B`）；
  - `EXT_CSD[267]` `PRE_EOL_INFO` & `[268:269]` `DEVICE_LIFE_TIME_EST_TYP_A/B`（评估闪存健康度）。
- **物理电气与 OTP 红线**：
  1. 隔离主控 `CXD90057`（保持 SoC `RESET_N` 拉低或晶振接地、主电池与 USB 断电），严防主控与 ISP 编程器争抢 `CMD/CLK/DAT0`。
  2. 严格匹配 `VCCQ`（`1.8 V` 或 `3.3 V`），`CLK/CMD/DAT0/GND` 飞线 `< 10 cm` 并降低初始 `CLK`（`1~4 MHz`）连续读取两遍做 SHA-256 一致性校验。
  3. **严禁触碰一次性 OTP 寄存器 `EXT_CSD[162]`（`RST_n_FUNCTION`）**；确认 `RPMB`（`ROM4`）因 HMAC-SHA256 认证密钥绑定无法通过常规转储克隆。

---

## 4. 主题 C：Sony BIONZ XR `Monitor & Control` / USB-LAN / Wi-Fi / UVC 跨机身架构

| 子系统 | ILME-FX3（公开实证 `v7.00/v7.02`） | ILME-FX6（公开实证 `v6.01`） | Stage-B 混合运行工程决策（结合本地 `O_RDONLY`） |
| :--- | :--- | :--- | :--- |
| **Wi-Fi (`802.11ac` 2.4/5 GHz)** | 支持 AP 直连 / Station 路由器、RTMP/RTMPS、FTP/FTPES；`p12/p13` 存本机 MAC 与 TX 功率校准 | 支持 AP / Station、FTP/FTPES、`Monitor & Control` | `libWlanAdjust.so` ABI 100% 一致（`188/119`）；**`p12/p13` 强制 `O_RDONLY` 写锁**，`P12` 飞行隔离模式下不触发 `WF-12` |
| **蓝牙 BLE vs M&C** | 具备物理 BLE 芯片，`Creators' App` 蓝牙配对唤醒 Wi-Fi（`libInfraBluetoothCore.so` `509` 导出、`libInfraBluetoothLowEnergy.so` `1,340` 导出） | **无 BLE 配对硬件**，使用 Wi-Fi/USB-LAN 版 `Content Browser Mobile` / `Monitor & Control` | 通过 Stage-B `LD_PRELOAD` 屏蔽 FX6 `appFw.so` 对不匹配 BT/BLE 守护进程的等待，确保 `bt_hci_blocking_wait_ms == 0` |
| **USB Type-C Multi-Role** | 原生 `MSC (054C:0DA1)` / `SERVICE (054C:0336)` 恢复、`MTP/PTP Remote`；**无机身免驱 USB-C UVC `USB Streaming`**（需 HDMI 采集卡或 Imaging Edge Webcam） | 支持 `MSC`/`MTP`/远程控制，ProCam 菜单含 `USB Streaming` 条目；4K UVC 同样建议 HDMI 采集 | `libInfraMscServer.so`（`125/69`）与 `libUsbControl.so`（`351/128`）在双机身 **ABI 完全一致**；屏蔽 FX6 `USB_STREAMING` 悬空调用以免劫持 `054C:0DA1` 恢复口 |
| **有线 USB-LAN & FTP / M&C** | `v7.00+` 支持开机自动识别 USB-C 千兆网卡（`CDC-NCM` / `RTL8153`）、支持 Direct USB Remote、FTP/FTPES 与 `Monitor & Control v2.4.0+` | 支持有线 USB-LAN、FTP/FTPES、`Monitor & Control v2.5.0+`（`USB Tethering` 不支持 iPadOS/macOS）；独有 PCIe Wake-on-LAN `WIREDLAN_WOL_*` | 保留原生 `CDC-NCM` USB-LAN 千兆 FTP & `Monitor & Control`（`PTP-IP TCP/15740`），对 FX6 独有 `WIREDLAN_WOL_*` 实施 `0 ms` 非阻塞空返回掩蔽 |

---

## 5. 未执行项与验证边界

1. **物理设备实机测试未执行**：本工作站未连接物理 `ILME-FX3` 真机，亦未对物理 SPI-NOR（`/dev/mtd0ro`）或 `CXD90057` eMMC 焊盘执行离线 ISP 读写测试；上述实操规则与位域数值仅源自公开规格（Linux `mtdchar`、JEDEC `JESD84-B51`、Sony 公开固件/手册）及本地 `O_RDONLY` 只读供体分析。
2. **Wave-19 参考来源（Web Grounding）**：
   - Linux Kernel MTD Character Device (`drivers/mtd/mtdchar.c`, `mtd-utils`: `mtdinfo`, `mtd_debug`, `/dev/mtd0ro` minor `2N+1` `-EACCES`/`-EPERM`)
   - JEDEC `JESD84-B51` eMMC 5.1 Standard (`EXT_CSD[179] PARTITION_CONFIG`, `BOOT_PARTITION_ENABLE`, `BOOT_ACK`, `EXT_CSD[162] RST_n_FUNCTION`, `mmc-utils`) & 嵌入式 eMMC ISP 硬件取证规范
   - 公开 BIONZ XR 逆向研究：`DavidBuchanan314/ILCE-7M4-RE`、`Hearts-Ace/sony-a7r5-custom-firmware`
   - Sony 官方帮助指南与 `Monitor & Control`（`ILME-FX3` v7.00/v7.02 Help Guide、`ILME-FX6` Help Guide、`Monitor & Control` v2.4.0/v2.5.0 兼容性文档、Sony UVC/HDMI Capture 官方支持矩阵）
