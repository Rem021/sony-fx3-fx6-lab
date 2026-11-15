# 索尼 FX3 与 FX6 系统移植、QEMU 虚拟机与净室兼容性研究实验室 (`sony-fx3-fx6-lab`)

[![English](https://img.shields.io/badge/Language-English-0969da?style=flat)](./README.en.md)
[![双语总览](https://img.shields.io/badge/主文档-README.md_(中英双语)-1a7f37?style=flat)](./README.md)
[![Stage-B 架构与安全](https://img.shields.io/badge/Stage--B_架构与安全-24门禁_%7C_docs%2FSTAGE--B-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![操作手册与救砖SOP](https://img.shields.io/badge/操作手册与救砖-Tier--0..4_%7C_中英双语-d97706?style=flat)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)
[![宿主机平台](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![目标芯片](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![自动化测试](https://img.shields.io/badge/Automated_Tests-2,191_本地_%7C_2,133_洁净室_(7_Suites)-brightgreen?style=flat)](#四快速开始与验收命令)
[![无供体净室CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 原厂核实时 GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r16d_(18%2F18_%2B_10%2F10)-success?style=flat)](#统一七大自动化验证套件make-test-本地供体-2191-项--洁净室-2133-项)
[![开源协议](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](#五合规声明与开源协议)

> **语言切换 / 深度参考**：[**👉 Switch to Standalone English Documentation (`README.en.md`)**](./README.en.md) · [**中英双语总览主文档 (`README.md`)**](./README.md) · [**Stage-B 全实验室架构与 24 门禁安全规范 (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)**](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [**双语现场操作 SOP 与救砖手册 (`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`)**](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)

**`sony-fx3-fx6-lab`** 是面向 **Sony Cinema Line ILME-FX3（`Ver. 7.02`，机型 ID `0x91030080`，`ALCIN_UUD`）** 与 **ILME-FX6（`Ver. 6.01`，机型 ID `0x91040086`，`CHAPLIN`）** 数字电影摄影机的净室系统工程、多架构 QEMU 协同仿真、跨机型硬件兼容性验证与真机防变砖安全研究开源仓库。两款机型均搭载 **Sony CXD90057（`AArch64` CE Linux `4.9.337-scel+`）** 主处理器与 **CXD90058（`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`）** 协处理器。

> [!CAUTION]
> **硬件写入硬锁状态（`persistent_emmc_writes_authorized = False` / 严禁持久化刷写真机）**  
> 实验室严格保持持久化刷机与实机连接硬锁关闭（**`NO-GO`**）：`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`hardware_live_attachment_authorized = False`、`edisx_repartition_forbidden = True`（`sector0_mutation_bytes = 0`）、`p8_cp_mutation_forbidden = True`（`cp_mutation_bytes = 0`）、`wbi_p5_write_and_hibernation_forbidden = True`（`wbi_mutation_bytes = 0`）、`calibration_mutation_bytes = 0`、`otp_fuse_touches = 0` 与 `rpmb_counter_increments = 0`。所有 Stage-A / Stage-B 覆盖层仅驻留在易失性 Linux DDR（`tmpfs`）中，全部供体读取严格使用 `os.O_RDONLY`，支持无连接线 `< 1 秒` `FX3_SAFE_STOCK.FLG` SD 哨兵逃生，断电重启即可瞬间 100% 恢复原厂 Sony ILME-FX3 `Ver. 7.02`。

> [!IMPORTANT]
> **净室开源合规边界（BYOF：自备官方固件复现）**  
> 本仓库 **包含 0 字节索尼专有闭源二进制文件**（不含 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`cpapp-b.bin`、`nflasha*` 分区镜像或 `.cpio` 根文件系统镜像）且 **包含 0 字节厂商 AES/RSA 私钥**。全部 7 套测试集（`2,133` 项洁净室测试）与 `Milestone Phase 90 总闸`、`24-Gate`、`20-Gate`、`RP2040`、`init2`、`Tier-0 GF(256)`、`OTP/RPMB 防回滚`、`Post-Trial` 门禁 CLI 均支持无供体净室 CI（`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`），由 [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml) 在 `ubuntu-latest` + `macos-latest` 自动门禁校验。本地复现虚拟机交互体验请参阅 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**（由 `make verify-byof` 自动守护 `57+57` 指纹与 `46` 项源码常量一致性）。

---

## 一、全实验室工程里程碑（`Phases 1–90` · `Rounds 1–16` · `Waves 1–8`）

### 统一七大自动化验证套件（`make test` — 本地供体 `2,191` 项 / 洁净室 `2,133` 项）

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md)（本地供体 `297` / 洁净室 `239` 项测试）**
   - **Phase 79 `CXD90057` OTP/RPMB 零写入防回滚与 `EXT_CSD[173/171]` 守卫**（[Phase 79 报告](reports/2026-11-14-phase79-antirollback-otp-rpmb-epoch-guard/README.md)，`make verify-antirollback-guard`）：严格确保 `otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、单调版本降级防护与永久写保护熔丝陷阱拦截。
   - **Phase 72 `GF(256)` (`0x11d`) RAID-6 Tier-0 备份库与防跨机移植守卫**（[Phase 72 报告](reports/2026-11-14-phase72-tier0-backup-gf256-parity-guard/README.md)，`make verify-tier0-backup`）：验证 `11` 个只读分区的双分片 bit-rot 自愈与机身指纹绑定（`c65670ea25a2c28e`）。
   - **Phase 66 `init2` SD 哨兵逃生（`FX3_SAFE_STOCK.FLG` `< 1 秒`）、`CXD90057` WDT `10,000ms` 破环与 `p1` `FAT12/16` 验证器**（[`init2_escape_and_watchdog_simulator.py`](outputs/fx3-recovery-adapter/fx3_recovery/init2_escape_and_watchdog_simulator.py)，[Phase 66 报告](reports/2026-11-14-phase66-init2-escape-watchdog-fat-verifier/README.md)，`make verify-init2-escape`）与 **Phase 59 `RP2040-Zero -DOPEN_DRAIN` 断机治具自检**（[`rp2040_multiport_fixture_selftest.py`](outputs/fx3-recovery-adapter/fx3_recovery/rp2040_multiport_fixture_selftest.py)，[Phase 59 报告](reports/2026-11-14-phase59-rp2040-multiport-fixture-selftest/README.md)，`make verify-rp2040-fixture`）。
   - **`Tier-0..Tier-4` 救砖升级阶梯（`S01..S12`）、`p1` VFAT 胶囊、偏移 VMA `v7.02` `p1` 4 锚点自动定位、macOS 26 `IOUSBHost` 与严格 `O_RDONLY` eMMC ISP 取证**（[Phase 47 报告](reports/2026-11-14-phase47-unbrick-escalation-ladder-verifier/README.md)、[Phase 42 报告](reports/2026-11-14-global-sony-wave3-emmc-isp-trustzone-intel/README.md)）及无 libc 静态 AArch64 采集器。

2. **[`outputs/fx3-safety/`](outputs/fx3-safety/)（双模式 `360` 项测试）**
   - **24 门禁主安全预检引擎（`G01..G24`，`make verify-24-gates`）**：组合 `preflight.py`（`G01..G12`）+ [`master_16gate_preflight.py`](outputs/fx3-safety/fx3_safety/master_16gate_preflight.py)（`G13..G16`）+ **Phase 57/61**（`G17` exFAT/客户素材隔离与 `G18` 有线 `USB-LAN CDC-NCM` + `PTP-IP 15740` + `P12` 飞行共存）+ **Phase 69**（`G19` 套件 D-Tap/铜 HDMI 地环路互锁与 E 卡口 `<= 2.0ms` `V_LENS` 撬棍断流 + `0x0400` IBIS 居中停靠；`G20` `NP-FZ100 >= 15%` UPS 冗余与 `.RSV` 只读抢救）+ **Phase 77** [`phantom48v_gimbal_and_22gate_guard.py`](outputs/fx3-safety/fx3_safety/phantom48v_gimbal_and_22gate_guard.py)（`G21` `+48V` XLR 幻象防烧毁与 `G22` `<= 0.35 N·m` 稳定器跟焦扭矩/快门防护，[Phase 77 报告](reports/2026-11-14-phase77-phantom48v-gimbal-22gate-guard/README.md)）+ **Phase 84** [`dewpoint_tec_usbc_and_24gate_guard.py`](outputs/fx3-safety/fx3_safety/dewpoint_tec_usbc_and_24gate_guard.py)（`G23` Magnus 露点 `TEC` 结露拦截与 `G24` PMIC `5V 900 mA` 配件预算门禁，[Phase 84 报告](reports/2026-11-14-phase84-dewpoint-tec-usbc-24gate-guard/README.md)）。
   - **物理治具与热电安全防火墙**：涵盖 6 阶段 `H0` 预演（`--unicorn`）、`serial_fault_detector_v2`、`RP2040-Zero -DOPEN_DRAIN` 与 `VMC-BNCM1` LTC 防火墙、`CrSDK` PTP2、MI 热靴 `XLR-H1`、`CXD90057 SPACC` AES-XTS-256 隔离、FX3 风扇 PWM（`libfan.so @ 0x1dec`）与 `NP-FZ100`/`USB-PD 9V/3A` 防护及运行时防变砖守卫。

3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)（双模式 `477` 项测试）**
   - **Phase 90 里程碑六柱一体化总闸（[`stage_b_milestone90_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone90_master_gate.py)，`make verify-milestone-90`，`< 2s`）**：汇聚 `24-Gate`、`OTP/RPMB + GF(256) + FX3_SAFE_STOCK.FLG`、`16` 固件审计器、`13-Stage` VM、`Round 16/14` 真机核闭环与 `H0 == H2` 16 表面不可变性并生成确定性 `milestone90_sha256`（[Phase 90 报告](reports/2026-11-14-phase90-milestone-master-gate-and-docs-sync/README.md)）。
   - **Stage-A（`P1..P9+Fan`）与 Stage-B（`P1..P12+Fan`，`13/13` 补丁 / `8` 模块 `18` 锚点，100% SHA-256 回滚）**：`P10` 24B 物理按键映射（`e2bc2619...`）、`P11` AP 侧 UIPC-CP 垫片（保留 `XLR-H1` 与 5 轴 IBIS 居中锁止）、`P12` `libWlanResource.so @ 0x70d4`（`47fec188...`）免疫 Sony `00342260` `WF-12` 死循环 + `BK4\0` 飞行/中文影子。
   - **全栈闭环、候选集成与试后法证**：完成 **`U1..U5` 全清零**、`60` ELF `.dynsym` + `137` `/dev/*` + `.ko` 闭合、**`S01..S10` Stage-B 生命周期演练**、**Phase 48 `070701` CPIO 打包器（`9/9` `init2`）**、**Phase 52/76 候选集成与发布档案 v3**（[Phase 76 报告](reports/2026-11-14-phase76-stage-b-release-dossier-v3/README.md)）与 **Phase 62/68/83 `16` 表面 `H0 == H2` 试后收官审计**（`make verify-post-trial-audit`，[Phase 83 报告](reports/2026-11-14-phase83-stage-b-capstone-22gate-verifier/README.md)）。

4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md)（双模式 `183` 项测试）**
   - **端口 `8768` 实时 QEMU ARM64 `1024×540` `GPE0` 交互式 Web 控制台（[`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command)）**：原生 `image_00_169.uxc` `LDEC103` 图标与 `60/60` 零崩溃、LRU 128 页四语池（**`简体中文 / 繁體中文 / EN / 日本語`**）、FX3 `P10` 按键台、`.cube` 3D LUT 上传、4 通道 `XLR-H1` VU 表、**Phase 56** IRE 波形/RGB 直方图/斑马纹/峰值/画幅参考线、**Phase 64** 双原生 ISO `800/12800` Cine EI/快门角 `5.6°..360.0°`/`S&Q 1–240fps`/Tally 隐身/`usblan_ptpip`/`hdmi_raw16` 篡改拦截、**Phase 73** `Shockless WB`/`Base Look`/双卡与 `*M01.XML` 导出（[Phase 73 报告](reports/2026-11-14-phase73-vm-trial-wb-look-dualslot-xml/README.md)），以及 **Phase 81** 画布点击 627 点 `Touch AF`（`GPE0 TAFC`）/`x4` 放大（HDMI 净流）/`S-Log3` `41%/94% IRE` 伪色 & `EL-Zone`/`CIZ` `1.5x/2.0x` 变焦互斥与 `CAMSET` 往返（[Phase 81 报告](reports/2026-11-14-phase81-vm-trial-touchaf-falsecolor-ciz/README.md)）。

5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md)（双模式 `83` 项测试）**
   - **Rounds 1–16（`r1a..r16d`）FX3 `7.02` 原厂内核（`4.9.337-scel+`）混合态真机闭环（`nop_count = 0`、`FX6_NATIVE_FAITHFUL=1`）**：`13/13` 挂载前 SHA-256 核验、`P10` + `P11` + `P12`、`LDEC103` GPE 物理池精灵贴图、**Round 14 四语×三界面 `18/18` 像素差分严格全正闭环**，以及 **Rounds 15–16 完整 `5` 标签 `Status Check`（`0x2f..0x33`，`C(5,2)=10/10` 两两差分全正 `> 0`）+ `TC/Media` 繁中（`0x18`）与 `Monitoring` 简中/日语（`0x19`/`0x01`）零崩溃真内核全闭环**（[Round 15](reports/2026-11-14-round15-fx6-on-fx3-multitab-status-monitoring/README.md)、[Round 16](reports/2026-11-14-round16-fx6-on-fx3-status-tabs45-tcmedia/README.md)）。

6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md)（双模式 `388` 项测试）**
   - **13 阶段全板级虚拟相机协同仿真（`fx3_vm_coemulation_suite.py` / `make verify-coemulation`）**：Stages 1–9（BT `/dev/ttyAMA3`、双核 `AArch64` AP ↔ `IVSHMEM` ↔ `ARM32` `cpapp-b.bin`、`Soft-GPE0`、纯 Py FDT+`MHLX`、`IMX510`/XAVC/`RTMD`、8 场景 HIL、`QMP`/`libqemu-plugin` `nop_count=0`、`256B EDID` `HDMI RAW16`、多机 `SMPTE 12M` LTC `EXT-LK` PLL + `PZ` + `libpaint` `3×3`）；**Stage 10（Ph71）** 双卡槽无缝中继/UPS `.RSV`（[Phase 71](reports/2026-11-14-phase71-vm-stage10-dualslot-proxy-ups-salvage/README.md)）；**Stage 11（Ph78）** `960×540` `evdev` Touch AF/`CIZ`/自定义键（[Phase 78](reports/2026-11-14-phase78-vm-stage11-touchaf-ciz-assignable/README.md)）；**Stage 12（Ph82）** `CAMSET01.DAT`/4ch `24-bit` LPCM/`BG1..BG8` UB（[Phase 82](reports/2026-11-14-phase82-vm-stage12-camset-lpcm-tcub/README.md)）；**Stage 13（Ph87）** 回放/`ShotMark1/2`/`<EssenceMark>`/`p1` 格式化拦截/`Push Auto Iris` 与热带露点/5V 卸载（[Phase 87](reports/2026-11-14-phase87-vm-stage13-playback-shotmark-dewpoint/README.md)）。

7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md)（双模式 `403` 项测试）**
   - **16 大净室无密钥审计器（`audit-all` / `make verify-firmware-lab`）**：`#1..#13`（`UFU`/`SDM2`、`HAITA`/`BK4`、62 包 `.uxc` + 6 套 CJK 字体、`IMX510`/XAVC、`.cube`+`RTMD`、`WBI2`/ELF64 ABI、`global.xdb` 128p、Audio/TC/HDMI、AF/IBIS、快门/Tally、白平衡/`OCIO v2`、代理/`*M01.XML`）+ **`#14（Ph75）`** `audit-assignable-ciz`（`Custom 1..6`/`CIZ 1.5x/2.0x`/`Big6`，[Phase 75](reports/2026-11-14-phase75-assignable-ciz-big6-auditor/README.md)）+ **`#15（Ph80）`** `audit-falsecolor-lpcm-ub`（`S-Log3` `41%/94% IRE` 伪色/`24-bit` LPCM/`User-Bits`，[Phase 80](reports/2026-11-14-phase80-falsecolor-lpcm-tc-ub-auditor/README.md)）+ **`#16（Ph85）`** `audit-playback-shotmark-ae`（回放/`ShotMark1/2`/自动光圈与 `p4_nd_motor_faults=0`/`internal_emmc_format_possible=False`，[Phase 85](reports/2026-11-14-phase85-playback-shotmark-ae-auditor/README.md)）。

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
| **01 —— 固件升级容器** | `BODYDATA.DAT`（`sauu` / `sdfileinput.elf`） | 机型 ID（`0x91030080` vs `0x91040086`）、区域与签名门禁仅存在于 `p1` 更新模式用户态流程中；`v7.02` `p1` 经 4 锚点 AArch64 `ADRP/BL` 自动定位；Phase 66 验证 `p1` `FAT12/16` 原子交换；Phase 79 拦截 OTP/RPMB 降级回滚。 |
| **02 —— Octal-SPI NOR 引导** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | FX3 `7.02` 与 FX6 `6.01` 的 `pformat_config.txt`（`1,274 B`）与 `LdrBkupList.txt`（`65` 键）100% 逐字节一致（`@ 0xFE049000`）；Tier-0 受 Phase 72 `GF(256)` RAID-6 守护；Tier-3 `48000` 波特率救援仅允许通过 `make verify-rp2040-fixture` 的治具。 |
| **03 —— Bank 0/1 描述符表** | `p2:/setting/Backup.bin`（`0x00fa0080`） | 64 槽位（`9,216 B`）Bank 0（AP）与 Bank 1（CP/校准）完成 0 字节 DDR 重叠证明；`p2:/setting/{psd,defdet}.bin`、`p6:Jiritsu`、`p12:/cert`（C2PA `RQ_LIC.DAT`）与 `p18:/lens/lensfile.bin` 受 `G15` 刚性只读保护。 |
| **04 —— 内核、FDT 与 CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb`（`16,875 B`）与 `tomco.txt` 4 段 `memcfg=`（`1,724.00 MiB`）100% 一致；Stage-A/B 保持 FX3 原厂内核与原厂 `p8:/cpapp-b.bin`（`cp_mutation_bytes = 0`）零改动并封锁 `p5:/wbi` 休眠快照（`wbi_mutation_bytes = 0`）。 |
| **05 —— 相机应用层** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | Stage-A（`30-stage-a-orchestrator.sh`）与 Stage-B（`stage_b_init2_guard.sh`）优先检查 `FX3_SAFE_STOCK.FLG`（`< 1s` 直退原厂），先完成 `13/13` SHA-256 校验与 24 门禁再挂载易失 `tmpfs`（`< 48 MiB` + `ro_sd_loop_bind`），严格逆序 LIFO 卸载（`H0 == H2`）。 |

---

## 三、仓库目录结构

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # 无供体 Ubuntu + macOS 七套件及 Milestone-90 洁净室 CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                 # 统一测试、Milestone-90、24门禁、Tier-0 GF(256)、OTP/RPMB、RP2040、init2、Stage-B、VM 与实验室
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # 中英双语 Stage-B (P1..P12+Fan)、24 门禁 (G01..G24)、13 阶段 VM 与 Tier-0..4 参考
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # 中英双语现场操典：RP2040、+48V XLR、稳定器、露点 TEC、5V PMIC 与 <1s 逃生
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # 中英双语 Phase H0->H1->H2 非持久 Stage-A 真机执行操作手册
│   └── BYOF-REPRODUCTION.md                 # 中英双语 57+57 项 SHA-256 指纹清单与自备固件复现指南
├── scripts/
│   ├── run_all_lab_tests.py                 # 统一七套件运行器 (本地 2,191 / 洁净室 2,133 项测试) + BYOF 清单 + 卫生检查
│   └── verify_byof_manifest.py              # 中英双语 BYOF SHA-256 语法、46 项源码常量与本地供体一致性审计器
├── outputs/                                 # 七大受控工程包 (本地 2,191 / 洁净室 2,133 项自动化测试)
│   ├── fx3-recovery-adapter/                # Tier-0..4、Ph59 RP2040、Ph66 init2 逃生/WDT、Ph72 GF(256)、Ph79 OTP/RPMB (297/239)
│   ├── fx3-safety/                          # 24 门禁主预检 G01..G24 (+48V、稳定器扭矩、TEC 露点、5V PMIC 预算) (360)
│   ├── fx6-on-fx3-closure/                  # Stage-A/B P1..P12+Fan、Ph52/76 集成、Ph62/68/83 试后审计、Ph90 总闸 (477)
│   ├── fx3-vm-trial/                        # 端口 8768 Web UI：128 页、Touch AF、x4、伪色、CIZ、Cine EI、示波器 (183)
│   ├── fx6-native-presenter-closure/        # Rounds 1..16 FX3 7.02 原厂内核 GPE0 闭环：nop_count=0，18/18 + 5 标签 10/10 (83)
│   ├── fx3-vm/                              # 13 阶段双核 AP<->IVSHMEM<->CP、Soft-GPE0、HIL、QMP、EDID、CAMSET、回放 (388)
│   └── fx3-firmware-lab/                    # 16 大无密钥审计器：UFU..global.xdb、CIZ、伪色/LPCM、回放/AE (403)
├── reports/                                 # Phases 1..90、Rounds 1..16、Waves 1..8 全球情报与验收报告
└── conversations/                           # 五大专题研究工作区多智能体工程研究对话分类归档
```

---

## 四、快速开始与验收命令

```bash
# 1. 一键运行全部 7 套 2,191 项本地供体测试 (297 + 360 + 477 + 183 + 83 + 388 + 403) + BYOF 清单 (57+57) + 净室零残留审计
make test
make test-json

# 2. 本地模拟 GitHub Actions 无供体洁净室 CI 模式 (7 套 2,133 项测试，零索尼固件依赖)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 90 六柱一体化总闸 (<2s) + 24 门禁、Tier-0 GF(256)、OTP/RPMB、RP2040 与 SD 逃生（双模式通用）
make verify-milestone-90
make verify-24-gates
make verify-tier0-backup
make verify-antirollback-guard
make verify-20-gates
make verify-rp2040-fixture
make verify-init2-escape
make verify-post-trial-audit

# 4. Stage-B 全生命周期演练、无线防护、固件实验室（16 审计器）、13 阶段协同仿真与 Stage-A 演练目标
make stage-b-lifecycle-drill
make verify-wireless-guard
make verify-firmware-lab
make verify-coemulation
make readiness-packet
make lifecycle-drill
make dry-run

# 5. 其余各阶段专项校验与卫生审计
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
- **FX6 128 页 / Big6 / Touch AF / 伪色 / CIZ / Cine EI / 示波器 / S&Q / 3D LUT / 四语实时控制台**：运行 `./outputs/fx3-vm-trial/FX6菜单.command` 并打开 `http://127.0.0.1:8768/`。
- **FX3 原厂菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（加 `--check` 仅校验输入指纹而不启动 QEMU）。

---

## 五、合规声明与开源协议

1. **零专有固件分发**：本仓库分发 **0 字节** 索尼闭源二进制固件、加密升级镜像或私有密钥。
2. **独立互操作性与防变砖安全研究**：全部源码、Unicorn 仿真测试套件与技术报告均在净室规范下独立编写，仅用于嵌入式系统架构研究、虚拟化探索与硬件刷前防变砖审计，与 Sony Group Corporation 无任何隶属或合作关系。
3. **开源许可**：仓库自研源码采用 MIT 协议发布；针对 QEMU 的补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议。
