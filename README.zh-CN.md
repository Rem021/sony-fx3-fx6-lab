# Sony FX3 / FX6 Lab · 中文研究文档

**用 QEMU、浏览器菜单工具和离线校验研究索尼 FX3 / FX6 固件。**

面向相机固件研究者。模拟器与离线结果不代表真机验收，真实 FX3 跨机型持久化刷写仍为硬锁禁止状态（**`BLOCKED / NO-GO`**）。

[项目首页](README.md) · [English](README.en.md) · **[固件准备](docs/BYOF-REPRODUCTION.md)** · **[真机台架部署档案](docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md)** · [运行与校验](#四快速开始与验收命令)

[![无供体净室CI](https://github.com/Rem021/sony-fx3-fx6-lab/actions/workflows/clean-room-ci.yml/badge.svg)](./.github/workflows/clean-room-ci.yml)
[![自动化测试](https://img.shields.io/badge/Automated_Tests-12,101_本地_%7C_12,043_洁净室_(7_Suites)-brightgreen?style=flat)](#四快速开始与验收命令)
[![Milestone 264](https://img.shields.io/badge/Master_Gate-Milestone_264_%7C_Phases_1..268_%7C_Rounds_1..53-1a7f37?style=flat)](#一全实验室工程里程碑phases-1268--rounds-153--waves-145)
[![开源协议](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](./LICENSE)

**`sony-fx3-fx6-lab`** 是面向 **Sony Cinema Line ILME-FX3（`Ver. 7.02`，机型 ID `0x91030080`，`ALCIN_UUD`）** 与 **ILME-FX6（`Ver. 6.01`，机型 ID `0x91040086`，`CHAPLIN`）** 数字电影摄影机的净室系统工程、多架构 QEMU 协同仿真、跨机型硬件兼容性验证与真机防变砖安全研究开源仓库。两款机型均搭载 **Sony CXD90057（`AArch64` CE Linux `4.9.337-scel+`）** 主处理器与 **CXD90058（`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`）** 协处理器。

> [!CAUTION]
> **硬件写入硬锁状态（`persistent_emmc_writes_authorized = False` / 严禁持久化刷写真机）**  
> 实验室严格保持持久化刷机与实机连接硬锁关闭（**`NO-GO`**）：`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`hardware_live_attachment_authorized = False`、`edisx_repartition_forbidden = True`（`sector0_mutation_bytes = 0`）、`p8_cp_mutation_forbidden = True`（`cp_mutation_bytes = 0`）、`wbi_p5_write_and_hibernation_forbidden = True`（`wbi_mutation_bytes = 0`）、`calibration_mutation_bytes = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`emmc_flash_mutation_bytes = 0` 与 `passive_tx_bytes_emitted = 0`。所有 Stage-A / Stage-B 覆盖层仅驻留在易失性 Linux DDR（`tmpfs`）中，全部供体读取严格使用 `os.O_RDONLY`，支持无连接线 `< 1 秒` `FX3_SAFE_STOCK.FLG` SD 哨兵逃生，断电重启即可瞬间 100% 恢复原厂 Sony ILME-FX3 `Ver. 7.02`。

> [!IMPORTANT]
> **净室开源合规边界（BYOF：自备官方固件复现）**  
> 本仓库 **包含 0 字节索尼专有闭源二进制文件**（不含 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`cpapp-b.bin`、`nflasha*` 分区镜像或 `.cpio` 根文件系统镜像）且 **包含 0 字节厂商 AES/RSA 私钥**。全部 7 套测试集（**`12,043` 项无供体洁净室测试** / **`12,101` 项本地供体测试**）与 `Grand Milestone Phase 264 六柱总闸`（`make verify-milestone-264`）、`108 门禁`（`verify-108-gates`）、`45 支柱离线救砖`（`verify-45pillar-recovery`）、`52 阶段虚拟相机 HIL 协同仿真` 及 `45 项无密钥固件审计器` 均支持无供体净室 CI（`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`），由 [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml) 在 `ubuntu-latest` + `macos-latest` 自动门禁校验。本地复现虚拟机交互体验请参阅 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**（由 `make verify-byof` 自动守护 `57+57` 指纹与 `46` 项源码常量一致性）。

---

## 一、全实验室工程里程碑（`Phases 1–268` · `Rounds 1–53` · `Waves 1–45`）

> **最新主线验收基线（`Grand Milestone Phase 264` + `Phases 265–268` + `Waves 1–45`）**：
> - **六柱总闸**：`make verify-milestone-264`（`LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC` 双模式 6/6 全绿通过，见 [Phase 264 报告](reports/2026-11-15-phase264-milestone264-master-closure-gate/README.md)、[真机台架部署档案](docs/REAL-HARDWARE-FX3-702-DEPLOYMENT-DOSSIER.md)）。
> - **安全与恢复**：**`108/108` 安全门禁**（`G01..G108`，`verify-108-gates`）· **`45/45` 离线救砖支柱**（`verify-45pillar-recovery`）· **`6` 大真机台架被动预检器**（`Ph186/204/216/227/248/261`）。
> - **仿真与固件实验室**：**`52/52` 虚拟相机 HIL 协同仿真阶段**（`make verify-coemulation`）· **`45/45` 无密钥固件审计器**（`make verify-firmware-lab`）· **`26/26` 轮原厂未改 `ILME-FX3 Ver. 7.02` ARM64 QEMU 实跑**（`r28..r53`，`78/78` 次运行，`52/52` 张脱敏 PNG `< 28 KiB`）。

### 统一七大自动化验证套件（`make test` — 本地供体 `12,101` 项 / 洁净室 `12,043` 项：`2,341`/`2,283` + `2,613` + `1,485` + `429` + `1,170` + `2,325` + `1,738`）

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md)（本地供体 `557` / 洁净室 `499` 项测试）**
   - **13 支柱救砖恢复主套件（`make verify-13pillar-recovery`）**：汇聚第 `1..10` 支柱（`macOS 26 IOUSBHost`、**Ph59** `RP2040-Zero -DOPEN_DRAIN` 自检 `make verify-rp2040-fixture`、**Ph66** `< 1s` `FX3_SAFE_STOCK.FLG` `init2` 逃生 `make verify-init2-escape`、**Ph72** `GF(256)` RAID-6 Tier-0 自愈 `make verify-tier0-backup`、**Ph79** `OTP/RPMB` 防回滚 `make verify-antirollback-guard`、`Tier-0..4` 阶梯、被动只收 `1.8V` UART `S0..S6` `passive_tx_bytes_emitted == 0`、Ph94 GPT CRC32/RPMB 重放、Ph101 SVR4 `cpio`/`EXT_CSD[267..269]` Pre-EOL、Ph106 FDT `/chosen/bootargs` `ro` 与 ARM64 `Image`）**叠加** **支柱 11（Ph113）** 双槽 A/B 与断电 `BODYDATA.DAT` OTA 修复（[Phase 113 报告](reports/2026-11-14-phase113-ab-bank-interrupted-ota-recovery/README.md)）、**支柱 12（Ph119）** SquashFS `4.0` `hsqs` 与 Warp-Boot `hibdrv` `WBI2` 审计（[Phase 119 报告](reports/2026-11-14-phase119-squashfs-wbi-hibdrv-recovery/README.md)）及 **支柱 13（Ph124）** Mask-BootROM USB 与 JEDEC eMMC `BOOT0/BOOT1` `EXT_CSD[179/177/173/226]` 恢复（[Phase 124 报告](reports/2026-11-14-phase124-bootrom-usb-emmc-bootpart-recovery/README.md)）。

2. **[`outputs/fx3-safety/`](outputs/fx3-safety/)（双模式 `665` 项测试）**
   - **40 门禁主安全预检引擎（`G01..G40`，`make verify-40-gates`）**：在 `G01..G32`（`make verify-32-gates`）基础上扩展 **Phase 108**（`G33` 海岸盐雾/细尘/剧场烟雾过滤与 `G34` 无线跟焦硬限位滑扣/伸缩变焦稳定器 CoG 振荡，[Phase 108](reports/2026-11-14-phase108-saltspray-followfocus-34gate-safety/README.md)）、**Phase 115**（`G35` 光纤 HDMI Pin-18 `+5V` 过流/倒灌与剪切力矩、`G36` CFexpress VPG 持续写入/NVMe 降速与仓门未关刷写防护，[Phase 115](reports/2026-11-14-phase115-safety-hdmi5v-cfexpress-36gates/README.md)）、**Phase 120**（`G37` `20V` USB-C PD 诱骗线/双电源串电/UVC 4K30p 热饱和、`G38` 15 针多接口 `LTC`/`3.3V` UART/`CRSDK` PTP 刷机指令防火墙，[Phase 120](reports/2026-11-14-phase120-safety-usbpd-multiterminal-38gates/README.md)），以及 **Phase 125** [`monsoon_mishoe_cagetwist_and_40gate_guard.py`](outputs/fx3-safety/fx3_safety/monsoon_mishoe_cagetwist_and_40gate_guard.py)（`G39` 热带季风湿润 24 针 MI 热靴短路与敞口侧盖毛细渗水、`G40` `XLR-H1` 甩力滑丝/`1/4"-20 > 3.5 N·m` 滑扣与不对称兔笼扭矩引发 E 卡口 `18.00 mm` 法兰距形变 —— 离线 `37/40` 如实拦截 vs 模拟预演 `40/40`，[Phase 125](reports/2026-11-14-phase125-safety-monsoon-mishoe-cagetwist-40gates/README.md)）。

3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)（双模式 `559` 项测试）**
   - **Milestone Phase 130 六柱一体化总闸（[`stage_b_milestone130_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone130_master_gate.py)，`make verify-milestone-130`，`< 2.5s`）**：汇聚 `40-Gate`、`13-Pillar 恢复`、`>= 24` 固件审计器、`>= 21` VM 阶段、`Round 14/17/19/20..24` 真内核全闭环与 `H0 == H2` 16 表面不可变性并生成 `milestone130_sha256`（[Phase 130 报告](reports/2026-11-14-phase130-milestone-master-gate-and-docs-sync/README.md)）。
   - 完整保留 **Phase 110 总闸（`make verify-milestone-110`）**、**Phase 90 总闸（`make verify-milestone-90`）**、**Stage-A（`P1..P9+Fan`）**、**Stage-B（`P1..P12+Fan` `13/13` 补丁 / 100% SHA-256 回滚）**、**`U1..U5`**、**`S01..S10` 生命周期演练**、**Phase 52/76 Dossier v3** 及 **Phase 62/68/83 `H0 == H2` 收官审计**（`make verify-post-trial-audit`）。

4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md)（双模式 `367` 项测试）**
   - **端口 `8768` 实时 QEMU ARM64 `1024×540` `GPE0` 交互式 Web 控制台（[`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command)）**：原生 `LDEC103` 图标（`60/60` 零崩溃）、LRU 128 页四语池（**`简体中文 / 繁體中文 / EN / 日本語`**）、`P10` 按键台、4 通道 `XLR-H1` VU 表、**Phases 56..102**（示波器、Cine EI、Touch AF/`x4`/伪色/`CIZ`、Gyroflow/变形防抖/基准音、Picture Cache/间隔拍摄/`.cube`/FTPS）、**Phase 109**（`'MCFL'` Monitor & Control 4 机位有线 Gang-REC + HDMI->12G-SDI `AVI`/`RP 188` + E/PL 阴影仲裁 + `C2PA 2.1` 零接触溯源 HUD，[Phase 109](reports/2026-11-14-phase109-vm-trial-mcfleet-sdi-c2pa/README.md)）、**Phase 116**（`'HLGA'` `HLG1/2/3 BT.2100` + `Display Assist` 洁净输出 + `CTA-861.3 (0x87)` + `ProRes RAW`/`BRAW` + 呼吸效应补偿 HUD，[Phase 116](reports/2026-11-14-phase116-vm-trial-hlg-bt2100-proresraw-breathing/README.md)），以及 **Phase 123**（`'UVCS'` USB-C `UVC 1.5/UAC 2.0` + 有线 `P12` `SRT/RTMPS TLS 1.3` + `CRSDK PTP` 销毁指令防火墙 HUD，[Phase 123](reports/2026-11-14-phase123-vm-trial-uvc-srt-crsdk-ptp/README.md)）。

5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md)（双模式 `198` 项测试）**
   - **Rounds 1–24（`r1a..r24e`）FX3 `7.02` 原厂内核（`4.9.337-scel+`）混合态真机闭环（`nop_count = 0`、`FX6_NATIVE_FAITHFUL=1`）**：`13/13` 挂载前 SHA-256 核验、`P10` + `P11` + `P12`、**R14 `18/18`**、**R17 `10/10` Status Check（`45/45` `> 0`）**、**R19 `11/11` Full-Menu（`55/55` `> 0`）**，**外加 Rounds 20–24 五大四语（`EN/JA/ZH-CN/ZH-TW`）`12/12` 双界面真内核闭环**（`Network` + `WF-12`、`Audio`、`Paint/Look` & `Camera`、`Monitoring`、`Project` -> 合计 **`60/60` 多语言配对严格正差分**，27 次实跑零崩溃，[Round 20](reports/2026-11-14-round20-fx6-on-fx3-network-4lang-wf12-closure/README.md)、[Round 21](reports/2026-11-14-round21-fx6-on-fx3-audio-4lang-dualsurface-closure/README.md)、[Round 22](reports/2026-11-14-round22-fx6-on-fx3-paintlook-camera-4lang-closure/README.md)、[Round 23](reports/2026-11-14-round23-fx6-on-fx3-monitoring-4lang-dualsurface-closure/README.md)、[Round 24](reports/2026-11-14-round24-fx6-on-fx3-project-4lang-dualsurface-closure/README.md)）。

6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md)（双模式 `684` 项测试）**
   - **21 阶段全板级虚拟相机协同仿真（`fx3_vm_coemulation_suite.py` / `make verify-coemulation`）**：Stages 1–18 + **Stage 19（Ph112）** `HLG/BT.2100`/Display Assist/跟焦稳定器 HIL（[Phase 112](reports/2026-11-14-phase112-vm-stage19-hdr-hlg-gimbal-fiz-hil/README.md)）+ **Stage 20（Ph117）** `ProRes RAW`/`BRAW`/呼吸补偿/MI 热靴 I2S & AOC `+5V` HIL（[Phase 117](reports/2026-11-14-phase117-vm-stage20-proresraw-breathing-mishoe-hil/README.md)）+ **Stage 21（Ph121）** `UVC/UAC`/有线 `SRT/RTMPS`/`CRSDK PTP` 防火墙/`20V` USB-PD 诱骗 HIL（`wf12_00342260_hits=0`、`emmc_flash_mutation_bytes=0`，[Phase 121](reports/2026-11-14-phase121-vm-stage21-uvc-srt-crsdk-usbpd-hil/README.md)）。

7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md)（双模式 `713` 项测试）**
   - **24 大净室无密钥审计器（`audit-all` / `make verify-firmware-lab`）**：`#1..#20` + **`#21（Ph111）`** `HLG/BT.2100/Display Assist`（[Phase 111](reports/2026-11-14-phase111-hdr-hlg-bt2100-display-assist-auditor/README.md)）+ **`#22（Ph114）`** `HDMI RAW ProRes/BRAW`/呼吸补偿/MI 时钟（[Phase 114](reports/2026-11-14-phase114-proresraw-breathing-mishoe-auditor/README.md)）+ **`#23（Ph118）`** `UVC/UAC/SRT/RTMPS/CRSDK PTP`（[Phase 118](reports/2026-11-14-phase118-uvc-srt-crsdk-ptp-auditor/README.md)）+ **`#24（Ph122）`** `MXF OP1a/MP4 RDD-18/PTPv2/TSL UMD v5.0`（[Phase 122](reports/2026-11-14-phase122-mxf-mp4-ptpv2-tally-auditor/README.md)）。

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
| **01 —— 固件升级容器** | `BODYDATA.DAT`（`sauu` / `sdfileinput.elf`） | 机型 ID（`0x91030080` vs `0x91040086`）、区域与签名门禁仅存在于 `p1` 更新模式用户态流程中；`v7.02` `p1` 经 4 锚点 AArch64 `ADRP/BL` 自动定位；Phase 66 验证 `p1` `FAT12/16` 原子交换；Phase 79/94/113 拦截 OTP/RPMB 降级与 A/B 断电 OTA 变砖。 |
| **02 —— Octal-SPI NOR 引导** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | FX3 `7.02` 与 FX6 `6.01` 的 `pformat_config.txt`（`1,274 B`）与 `LdrBkupList.txt`（`65` 键）100% 逐字节一致（`@ 0xFE049000`）；Tier-0 受 `GF(256)` RAID-6 守护；Tier-3 `48000` 波特率救援需先通过 `make verify-rp2040-fixture` 治具并叠加 Phase 124 BootROM USB/`BOOT0..1` 校验，支持被动只收 UART（`tx_bytes = 0`）。 |
| **03 —— Bank 0/1 描述符表** | `p2:/setting/Backup.bin`（`0x00fa0080`） | 64 槽位（`9,216 B`）Bank 0（AP）与 Bank 1（CP/校准）完成 0 字节 DDR 重叠证明；`p2:/setting/{psd,defdet}.bin`、`p6:Jiritsu`、`p12:/cert`（`C2PA 2.1` `RQ_LIC.DAT`）与 `p18:/lens/lensfile.bin` 受 `G15` 与 `Ph105` 刚性只读保护。 |
| **04 —— 内核、FDT 与 CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb`（`16,875 B`）与 `tomco.txt` 4 段 `memcfg=`（`1,724.00 MiB`）100% 一致；Phase 106/119 锁定 FDT `/chosen/bootargs` `ro`、ARM64 `0x644d5241`、SquashFS `hsqs` 与 `WBI2`；Stage-A/B 保持 FX3 原厂内核与 `p8:/cpapp-b.bin`（`cp_mutation_bytes = 0`）零改动并封锁 `p5:/wbi`（`wbi_mutation_bytes = 0`）。 |
| **05 —— 相机应用层** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | Stage-A 与 Stage-B（`stage_b_init2_guard.sh`）优先检查 `FX3_SAFE_STOCK.FLG`（`< 1s` 直退原厂），先完成 `13/13` SHA-256 校验与 40 门禁再挂载易失 `tmpfs`（`< 48 MiB` + `ro_sd_loop_bind`），严格逆序 LIFO 卸载（`H0 == H2`）。 |

---

## 三、仓库目录结构

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # 无供体 Ubuntu + macOS 七套件、40 门禁、13 支柱与 Milestone-130 洁净室 CI
├── Makefile                                 # 统一测试、Milestone-130、40 门禁、13 支柱恢复、M110/M90、VM 与实验室
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # 中英双语 Stage-B (P1..P12+Fan)、40 门禁 (G01..G40)、21 阶段 VM 与 13 支柱参考
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # 中英双语现场操典：RP2040、+48V、TEC、盐雾/AOC、USB-PD 诱骗、季风热靴与逃生
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # 中英双语 Phase H0->H1->H2 非持久 Stage-A 真机执行操作手册
│   └── BYOF-REPRODUCTION.md                 # 中英双语 57+57 项 SHA-256 指纹清单与自备固件复现指南
├── scripts/
│   ├── run_all_lab_tests.py                 # 统一七套件运行器 (本地 3,743 / 洁净室 3,685 项测试) + BYOF 清单 + 卫生检查
│   └── verify_byof_manifest.py              # 中英双语 BYOF SHA-256 语法、46 项源码常量与本地供体一致性审计器
├── outputs/                                 # 七大受控工程包 (本地 3,743 / 洁净室 3,685 项自动化测试)
│   ├── fx3-recovery-adapter/                # 13 支柱救砖：Tier-0..4、RP2040、init2、GF(256)、OTP/RPMB、UART、A/B、WBI2、BootROM (557/499)
│   ├── fx3-safety/                          # 40 门禁主预检 G01..G40 (盐雾、跟焦 CoG、AOC 5V、NVMe、USB-PD、季风热靴、FFD) (665)
│   ├── fx6-on-fx3-closure/                  # Stage-A/B、Ph52/76 集成、M90/M110、Milestone Phase 130 六柱总闸 (559)
│   ├── fx3-vm-trial/                        # 端口 8768 Web UI：128 页、示波器、M&C 车队、HLG BT.2100/RAW、UVC/SRT/CRSDK (367)
│   ├── fx6-native-presenter-closure/        # Rounds 1..24 FX3 7.02 原厂内核 GPE0：nop=0，R14/R17/R19 + R20..24 5/5 60/60 (198)
│   ├── fx3-vm/                              # 21 阶段双核 AP<->IVSHMEM<->CP 共仿真至 HLG/RAW/UVC/SRT/CRSDK (684)
│   └── fx3-firmware-lab/                    # 24 大无密钥审计器：UFU..C2PA 2.1、HLG、ProRes/BRAW、UVC/SRT/CRSDK、MXF/PTPv2 (713)
├── reports/                                 # Phases 1..130、Rounds 1..24、Waves 1..14 全球情报与验收报告
└── conversations/                           # 五大专题研究工作区多智能体工程研究对话分类归档
```

---

## 四、快速开始与验收命令

```bash
# 1. 一键运行全部 7 套 12,101 项本地供体测试 (2,341 + 2,613 + 1,485 + 429 + 1,170 + 2,325 + 1,738) + BYOF 清单 (57+57) + 净室零残留审计
make test
make test-json

# 2. 本地模拟 GitHub Actions 无供体洁净室 CI 模式 (7 套 12,043 项测试，零索尼固件依赖)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Grand Milestone Phase 264 六柱总闸 + 108 门禁、45 支柱救砖与历史兼容总闸（双模式通用）
make verify-milestone-264
PYTHONPATH="outputs/fx3-safety" python3 -B -m fx3_safety verify-108-gates --simulate-bench-dry-run
PYTHONPATH="outputs/fx3-recovery-adapter" python3 -B -m fx3_recovery verify-45pillar-recovery
make verify-milestone-254
make verify-milestone-233
make verify-milestone-221
make verify-milestone-130
make verify-40-gates
make verify-13pillar-recovery
make verify-milestone-110
make verify-32-gates
make verify-10pillar-recovery
make verify-milestone-90
make verify-24-gates
make verify-fast
make verify-tier0-backup
make verify-antirollback-guard
make verify-rp2040-fixture
make verify-init2-escape
make verify-post-trial-audit

# 4. Stage-B 全生命周期演练、无线防护、固件实验室（45 审计器）、52 阶段协同仿真与 Stage-A 演练目标
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
- **FX6 128 页 / Big6 / Touch AF / 伪色 / CIZ / Cine EI / Gyroflow / M&C / HLG / UVC-SRT-CRSDK 控制台**：运行 `./outputs/fx3-vm-trial/FX6菜单.command` 并打开 `http://127.0.0.1:8768/`。
- **FX3 原厂菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（加 `--check` 仅校验输入指纹而不启动 QEMU）。

---

## 五、合规声明与开源协议

1. **零专有固件分发**：本仓库分发 **0 字节** 索尼闭源二进制固件、加密升级镜像或私有密钥。
2. **独立互操作性与防变砖安全研究**：全部源码、Unicorn 仿真测试套件与技术报告均在净室规范下独立编写，仅用于嵌入式系统架构研究、虚拟化探索与硬件刷前防变砖审计，与 Sony Group Corporation 无任何隶属或合作关系。
3. **开源许可**：仓库自研源码采用 [MIT](./LICENSE) 协议发布；针对 QEMU 的补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议。
