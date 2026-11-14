# 索尼 FX3 与 FX6 系统移植、QEMU 虚拟机与净室兼容性研究实验室 (`sony-fx3-fx6-lab`)

[![English](https://img.shields.io/badge/Language-English-0969da?style=flat)](./README.en.md)
[![双语总览](https://img.shields.io/badge/主文档-README.md_(中英双语)-1a7f37?style=flat)](./README.md)
[![Stage-B 架构与安全](https://img.shields.io/badge/Stage--B_架构与安全-docs%2FSTAGE--B-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![宿主机平台](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![目标芯片](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![自动化测试](https://img.shields.io/badge/Automated_Tests-1,045_Passing_(7_Suites)-brightgreen?style=flat)](#四快速开始与验收命令)
[![无供体净室CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![开源协议](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](#五合规声明与开源协议)

> **语言切换 / 深度参考**：[**👉 Switch to Standalone English Documentation (`README.en.md`)**](./README.en.md) · [**中英双语总览主文档 (`README.md`)**](./README.md) · [**Stage-B 全实验室架构与 16 门禁安全规范 (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)**](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)

**`sony-fx3-fx6-lab`** 是面向 **Sony Cinema Line ILME-FX3（`Ver. 7.02`，机型 ID `0x91030080`，`ALCIN_UUD`）** 与 **ILME-FX6（`Ver. 6.01`，机型 ID `0x91040086`，`CHAPLIN`）** 数字电影摄影机的净室系统工程、多架构 QEMU 协同仿真、跨机型硬件兼容性验证与真机防变砖安全研究开源仓库。两款机型均搭载 **Sony CXD90057（`AArch64` CE Linux `4.9.337-scel+`）** 主处理器与 **CXD90058（`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`）** 协处理器。

> [!CAUTION]
> **硬件写入硬锁状态（`persistent_emmc_writes_authorized = False` / 严禁持久化刷写真机）**  
> 实验室严格保持持久化刷机硬锁关闭（**`NO-GO`**）：`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`edisx_repartition_forbidden = True`（`sector0_mutation_bytes = 0`）、`p8_cp_mutation_forbidden = True`（`cp_mutation_bytes = 0`）、`wbi_p5_write_and_hibernation_forbidden = True`（`wbi_mutation_bytes = 0`）、`calibration_mutation_bytes = 0`。所有 Stage-A / Stage-B 覆盖层仅驻留在易失性 Linux DDR（`tmpfs`）中，全部供体读取严格使用 `os.O_RDONLY`，断电重启即可瞬间 100% 恢复原厂 Sony ILME-FX3 `Ver. 7.02`。

> [!IMPORTANT]
> **净室开源合规边界（BYOF：自备官方固件复现）**  
> 本仓库 **包含 0 字节索尼专有闭源二进制文件**（不含 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`cpapp-b.bin`、`nflasha*` 分区镜像或 `.cpio` 根文件系统镜像）且 **包含 0 字节厂商 AES/RSA 私钥**。全部 7 套测试集均支持无供体净室 CI（`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`），由 [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml) 在 `ubuntu-latest` + `macos-latest` 自动门禁校验。本地复现虚拟机交互体验请参阅 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**（由 `make verify-byof` 自动守护 `57+57` 指纹与 `46` 项源码常量一致性）。

---

## 一、全实验室七套件工程里程碑（`Wave 1..8` · `Phases 1..50` · `Rounds 1..11`）

### 统一七大自动化验证套件（`make test` 共 `1,045` 项测试全绿）

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md)（`167` 项测试）**
   - **`Tier-0..Tier-4` 救砖升级阶梯（12 场景 `S01..S12`）与 `p1` `FAT12`/`FAT16` VFAT 原子回滚胶囊**：校验 `FAT1 == FAT2`、VFAT LFN 长文件名校验和、断环交叉链接拦截与 6 步 `fsync` 原子落盘（[`unbrick_ladder_and_capsule_verifier.py`](outputs/fx3-recovery-adapter/fx3_recovery/unbrick_ladder_and_capsule_verifier.py)，[Phase 47 报告](reports/2026-11-14-phase47-unbrick-escalation-ladder-verifier/README.md)）。
   - **偏移 VMA `v7.02` `p1` 4 锚点自动定位器、macOS 26 `IOUSBHost` 防护与只读 eMMC 取证审计**：自动解析 `v7.02` `p1` 地址（拒绝写死 `v2.00` 偏移）、守护 macOS `0xe00002be` 静默回退与 Senser v1/v2 防护、严格 `O_RDONLY` 审计 `EXT_CSD[179]`/`CMD42` 禁用/`Sector 0`/`BK4\0`/`WBI2`（[Phase 42 报告](reports/2026-11-14-global-sony-wave3-emmc-isp-trustzone-intel/README.md)），并包含无 libc 静态 AArch64 采集器（`fx3_p1_reader.c`、`fx3_boot_reader.c`、`elflink.py`）。

2. **[`outputs/fx3-safety/`](outputs/fx3-safety/)（`200` 项测试）**
   - **16 门禁主安全预检引擎（`G01..G16`）**：组合 `G01..G12`（`preflight.py`）与 `G13..G16`（[`master_16gate_preflight.py`](outputs/fx3-safety/fx3_safety/master_16gate_preflight.py)，[Phase 50 报告](reports/2026-11-14-phase50-wave4-c2pa-exfat-hetero-vm-intel/README.md)），刚性保护 Sony **C2PA**（`RQ_LIC.DAT`、`sigcert.p12`、`p12:/cert`、TrustZone/RPMB）、出厂校准分区（`psd.bin`、`defdet.bin`、`Backup.bin`、`p6:Jiritsu`、`p18:/lens/lensfile.bin`）、`exFAT` 掉电脏位（`VolumeDirty`/`.RSV`）及 `P12`/`WBI2`/`CP` 不可变性。
   - **物理治具与热电安全防火墙**：涵盖 6 阶段 `H0` 只读预演（`--unicorn`）、`serial_fault_detector_v2`（`TIMER-IP` `220s`/`90s` 看门狗）、**`RP2040-Zero -DOPEN_DRAIN` Multi-Port `48000` 波特率 `uart_boot` 与 `VMC-BNCM1` LTC 防火墙**、**`CrSDK` PTP2 `0x9201..0x9209`**、**24 针 MI 热靴 `XLR-H1`**、**`CXD90057 SPACC` `cnflasha` AES-XTS-256 隔离**（[Phase 38 报告](reports/2026-11-14-phase38-crsdk-mishoe-ltc-spacc-guard/README.md)）、**FX3 风扇 PWM（`libfan.so @ 0x1dec`）与 `NP-FZ100`/`USB-PD 9V/3A` 防护**（[Phase 44 报告](reports/2026-11-14-phase44-thermal-pwm-npfz100-usbpd-guard/README.md)）及运行时防变砖守卫（`ld.so.preload`、`dd`、`nflasha10` `0x10000009`）。

3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)（`279` 项测试）**
   - **Stage-A（`P1..P9+Fan`）与 Stage-B（`P1..P12+Fan`，`13/13` 补丁 / `8` 模块 `18` 锚点，100% SHA-256 回滚）**：
     - **`P10`**：24B `.rodata` FX3 机身物理按键重映射（`Fn→HOME`、`C1→KURU_PON`、`C2→MENU_CANCEL`、`C3→DISP_SEL`、`PLAY→THUMBNAIL`、`DELETE→USER`），零重叠合并入 Stage-B `appFw.so`（`e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4`，[Phase 20 报告](reports/2026-11-14-phase20-p10-stage-b-integration/README.md)）。
     - **`P11`**：AP 侧 UIPC-CP 垫片（`0x92d2091c` `/dev/rtc0->udate` + `0x91db059b` 脱离手柄 ACK 保留 `XLR-H1` + `developing_mode_FHD` + `0x0165`/`0x0166` `33³` 3D LUT DMA + Cine EI `800/12800` + **5 轴 IBIS 居中锁止**，[Phase 21 报告](reports/2026-11-14-phase21-uipc-cp-shim-closure/README.md)）。
     - **`P12`**：`libWlanResource.so::_Z16handleFatalErrorv @ 0x70d4 -> mov w0, #0; ret`（`7 B` 差异，`47fec188cc174faae7180744695257a9641b15dfdb3f237194be24fd551a1995`）彻底阻断 Sony 通告 `00342260` `WF-12` 无限重启，叠加 `BK4\0` 飞行模式与可选中/英/日语言 RAM 影子（[Phase 22 报告](reports/2026-11-14-phase22-wf12-wireless-fault-isolation/README.md)）。
   - **全栈蓝图与生命周期闭环**：实现 **`U1..U5` 全清零**、`60` ELF `.dynsym`/`DT_NEEDED`/`VERNEED` + `137` `/dev/*` + `.ko` 闭合、**`S01..S10` Stage-B `H0 -> H1 -> H2` 生命周期演练**（[Phase 35 报告](reports/2026-11-14-phase35-stage-b-lifecycle-closure/README.md)）、**`stage_b_ram_overlay_packager`**（确定性 `070701` CPIO + `9/9` POSIX `/bin/sh` `init2` 沙盒，[Phase 48 报告](reports/2026-11-14-phase48-stage-b-ram-overlay-packager/README.md)）及 **`stage_b_master_readiness_packet`**（`stage_b_readiness_packet_v2`，[Phase 39 报告](reports/2026-11-14-phase39-stage-b-master-readiness-dossier/README.md)）。

4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md)（`81` 项测试）**
   - **端口 `8768` 实时 QEMU ARM64 `1024×540` `GPE0` 交互式 Web 控制台（[`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command)）**：集成原生 `image_00_169.uxc` `LDEC103` 图标与 `60/60` 零崩溃修复（[Phase 19 报告](reports/2026-11-14-phase19-live-icon-rendering/README.md)）、LRU 128 页零冻结池（`170/170`）、实时 **`简体中文 / EN / 日本語`** 切换、FX3 `P10` 机身按键台（[Phase 23 报告](reports/2026-11-14-phase23-128page-multilang-fx3deck/README.md)）、实时 **Cine EI / 快门角 / `P4` ND-Clear 锁**（[Phase 30 报告](reports/2026-11-14-phase30-cineei-lut-nd-interactive-trial/README.md)）、**防崩溃 `.cube` `17³/33³` 3D LUT 上传器**、**4 通道 `XLR-H1` VU 表**、**`RTMD 0xE304`**、**`CAMSET` 场景预设**（[Phase 40 报告](reports/2026-11-14-phase40-vm-trial-cube-lut-xlr-presets/README.md)）、**11 分类 / 128 页双语即时搜索直跳栏**、**机内三语 `GPE0` 像素差自检**与 **`HardenedThreadingHTTPServer`** 零堆栈断连加固（[Phase 49 报告](reports/2026-11-14-phase49-vm-trial-menu-search-hardening/README.md)）。

5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md)（`34` 项测试）**
   - **原版冷启动 `nop_count = 0`（`r1a..r7c`）与 Rounds 8–11 FX3 `7.02` 原厂内核（`4.9.337-scel+`）混合态真机闭环（`r8a..r11d`）**：`13/13` 挂载前 SHA-256 核验、`P10` 物理键位 + `P11` 遥测 + `P12` `libWlanResource.so` + `BK4 0x02cf019c=0x19`、`LDEC103` GPE 物理池精灵贴图，以及原生 **`MYingHeiC-GB18030-SJ_wIcon.ltt`** 简体中文（`bank 19/23`）最高渲染 **`476` 色**与 `24,891` 字形块（[Round 10 报告](reports/2026-11-14-round10-fx6-on-fx3-full-icon-presenter/README.md)、[Round 11 报告](reports/2026-11-14-round11-fx6-on-fx3-schinese-p12-presenter/README.md)）。

6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md)（`127` 项测试）**
   - **5 阶段全板级虚拟相机协同仿真（`fx3_vm_coemulation_suite.py`）**：Stage 1 冷启动 + `virtual-rom-v1` `/dev/ttyAMA3` 蓝牙 H4 UART（[Phase 29](reports/2026-11-14-phase29-soft-gpe-bt-rom-emulator/README.md)）；Stage 2 **双架构 `AArch64` AP ↔ `IVSHMEM` ↔ 未修改 `ARM32 Thumb-2` 原厂 CP `cpapp-b.bin @ 0x00108000`**（`cp_mutation_bytes = 0`，[Phase 24](reports/2026-11-14-phase24-dual-ap-cp-ivshmem-bridge/README.md)）；Stage 3 `Soft-GPE0` + `ramfb`（`HOSDAP02`）；Stage 4 纯 Python `CXD90057` FDT `0xd00dfeed`（`4,614 B`）+ `MmioWindowBus` + 8 通道 `mhlx` 环（[Phase 41](reports/2026-11-14-phase41-qemu-pcie-bar-mailbox-dtb/README.md)）；Stage 5 **`IMX510` VSYNC / `libmpr` XAVC / `SMPTE RDD 18` `RTMD 0xE304` / 双 CFexpress Type A 与 SDXC 流水线**（[Phase 45](reports/2026-11-14-phase45-vm-imx510-xavc-cfexpress-pipeline/README.md)）。

7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md)（`157` 项测试）**
   - **8 大净室无密钥审计器（`audit-all` / `make verify-firmware-lab`）**：`UFU`/`FDAT`/`UDTRFIRM`/`SDM2` 容器审计（`5L+6S` 门控）、`ALCIN_UUD` vs `CHAPLIN` `HAITA`/`BK4` 差异与 `5016×3344` 负向证明、**62 包 29 语言 `.uxc` + 6 套 CJK `.ltt`/`.ttf` `cmap` 校验 + 1,610 精灵 CPU `LDEC`**（[Phase 27](reports/2026-11-14-phase27-uxc-multilang-cjk-font-audit/README.md)）、**`IMX510`/双原生 ISO `800/12800`/XAVC 矩阵**（[Phase 31](reports/2026-11-14-phase31-imx510-xavc-codec-matrix/README.md)）、**`.cube` `17³→33³` 3D LUT + `RTMD 0xE304`**（[Phase 37](reports/2026-11-14-phase37-cube-3dlut-rtmd-verifier/README.md)）、**`WBI2`/`hibdrv` EL1 失配拦截 + 纯 Python ELF64 `.dynsym` ABI 差异**（[Phase 43](reports/2026-11-14-phase43-wbi2-hibdrv-and-elf64-abi-diff/README.md)）与 **`global.xdb` `uxa\x07` + 11 分类 128 页菜单树及 FX3 硬件谓词审计**（[Phase 46](reports/2026-11-14-phase46-global-xdb-and-128page-menu-audit/README.md)）。

---

## 二、五阶段硬件引导与信任边界概览

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="./assets/boot-pipeline-zh-dark.svg">
    <source media="(prefers-color-scheme: light)" srcset="./assets/boot-pipeline-zh-light.svg">
    <img alt="五阶段安全引导流水线" src="./assets/boot-pipeline-zh-light.svg" width="100%">
  </picture>
</p>

| 引导层级 | 核心组件 | 已核验架构契约 |
| :--- | :--- | :--- |
| **01 —— 固件升级容器** | `BODYDATA.DAT`（`sauu` / `sdfileinput.elf`） | 机型 ID（`0x91030080` vs `0x91040086`）、区域与签名门禁仅存在于 `p1` 更新模式用户态流程中；`v7.02` `p1` 经 4 锚点 AArch64 `ADRP/BL` 自动定位。 |
| **02 —— Octal-SPI NOR 引导** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | FX3 `7.02` 与 FX6 `6.01` 的 `pformat_config.txt`（`1,274 B`）与 `LdrBkupList.txt`（`65` 键）100% 逐字节一致（`@ 0xFE049000`）；Tier-3 `48000` 波特率 BootROM 救援仅允许 `RP2040-Zero -DOPEN_DRAIN`。 |
| **03 —— Bank 0/1 描述符表** | `p2:/setting/Backup.bin`（`0x00fa0080`） | 64 槽位（`9,216 B`）Bank 0（AP）与 Bank 1（CP/校准）完成 0 字节 DDR 重叠证明；`p2:/setting/{psd,defdet}.bin`、`p6:Jiritsu`、`p12:/cert`（C2PA）与 `p18:/lens/lensfile.bin` 受 `G15` 刚性只读保护。 |
| **04 —— 内核、FDT 与 CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb`（`16,875 B`）与 `tomco.txt` 4 段 `memcfg=`（`1,724.00 MiB`）100% 一致；Stage-A/B 保持 FX3 原厂内核与原厂 `p8:/cpapp-b.bin`（`cp_mutation_bytes = 0`）零改动并封锁 `p5:/wbi` 休眠快照（`wbi_mutation_bytes = 0`）。 |
| **05 —— 相机应用层** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | Stage-A（`30-stage-a-orchestrator.sh`）与 Stage-B（`stage_b_init2_guard.sh`）先完成全部 `13/13` SHA-256 原子校验再挂载易失 `tmpfs` RAM-Overlay（`< 48 MiB` + `ro_sd_loop_bind`，`0` 字节 eMMC/WBI/CP 写入），严格逆序 LIFO 卸载，断电自动回退原厂 FX3。 |

---

## 三、仓库目录结构

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # 无供体 Ubuntu + macOS 七套件净室 CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                 # 统一测试、Stage-B、固件实验室、协同仿真、BYOF 与卫生检查入口
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # 中英双语 Stage-B (P1..P12+Fan)、16 门禁 (G01..G16) 与 Tier-0..4 参考
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # 中英双语 Phase H0->H1->H2 非持久 Stage-A 真机执行操作手册
│   └── BYOF-REPRODUCTION.md                 # 中英双语 57+57 项 SHA-256 指纹清单与自备固件复现指南
├── scripts/
│   ├── run_all_lab_tests.py                 # 统一七套件 1,045 项测试运行器 + BYOF 清单审计 + `git status` 卫生检查
│   └── verify_byof_manifest.py              # 中英双语 BYOF SHA-256 语法、46 项源码常量与本地供体一致性审计器
├── outputs/                                 # 七大受控工程包 (共 1,045 项自动化测试)
│   ├── fx3-recovery-adapter/                # Tier-0..4 阶梯、p1 VFAT 胶囊、v7.02 自动定位、macOS USB 与 eMMC 取证 (167)
│   ├── fx3-safety/                          # 16 门禁主预检 G01..G16、H0 预演、WDT v2、RP2040、C2PA 与热电守卫 (200)
│   ├── fx6-on-fx3-closure/                  # Stage-A/B P1..P12+Fan、U1..U5、S01..S10、SVR4 打包器 v2 与就绪包 v2 (279)
│   ├── fx3-vm-trial/                        # 端口 8768 三语 128 页实时 Web UI、.cube LUT、XLR VU 与搜索直跳 (81)
│   ├── fx6-native-presenter-closure/        # 原版冷启动 nop_count=0 + Rounds 8..11 FX3 7.02 原厂内核 GPE0 闭环 (34)
│   ├── fx3-vm/                              # 5 阶段双核 AP<->IVSHMEM<->CP、Soft-GPE0、FDT 与 IMX510/XAVC/RTMD VM (127)
│   └── fx3-firmware-lab/                    # 无密钥 UFU/SDM2、HAITA/BK4、62 .uxc/CJK、IMX510、.cube、WBI2 与 global.xdb (157)
├── reports/                                 # Phases 1..50、Rounds 1..11、Waves 1..4 全球情报与 Phase 54 同步报告
└── conversations/                           # 五大专题研究工作区多智能体工程研究对话分类归档
```

---

## 四、快速开始与验收命令

```bash
# 1. 一键运行全部 7 套 1,045 项测试 (167 + 200 + 279 + 81 + 34 + 127 + 157) + BYOF 清单 (57+57) + 净室零残留审计
make test
make test-json

# 2. 本地模拟 GitHub Actions 无供体净室 CI 模式 (零索尼固件依赖)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Stage-B 全生命周期演练、无线防护、固件实验室、协同仿真与 Stage-A 演练目标
make stage-b-lifecycle-drill
make verify-wireless-guard
make verify-firmware-lab
make verify-coemulation
make readiness-packet
make lifecycle-drill
make dry-run

# 4. 其余各阶段专项校验与卫生审计
make verify-byof
make verify-storage-ram-budget
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
make verify-kmod-userland-abi
make verify-peripheral-ux
make verify-ap-cp-imaging
make verify-stage-b-p10
make verify-uipc-cp-shim
make clean-audit
```

**在自备 BYOF 固件环境下启动交互式模拟器（详见 [`docs/BYOF-REPRODUCTION.md`](docs/BYOF-REPRODUCTION.md)）**：
- **FX6 128 页 / Big6 / Cine EI / 3D LUT / 三语实时控制台**：运行 `./outputs/fx3-vm-trial/FX6菜单.command` 并打开 `http://127.0.0.1:8768/`。
- **FX3 原厂菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（加 `--check` 仅校验输入指纹而不启动 QEMU）。

---

## 五、合规声明与开源协议

1. **零专有固件分发**：本仓库分发 **0 字节** 索尼闭源二进制固件、加密升级镜像或私有密钥。
2. **独立互操作性与防变砖安全研究**：全部源码、Unicorn 仿真测试套件与技术报告均在净室规范下独立编写，仅用于嵌入式系统架构研究、虚拟化探索与硬件刷前防变砖审计，与 Sony Group Corporation 无任何隶属或合作关系。
3. **开源许可**：仓库自研源码采用 MIT 协议发布；针对 QEMU 的补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议。
