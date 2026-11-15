# 索尼 FX3 与 FX6 系统移植、QEMU 虚拟机与净室兼容性研究实验室 (`sony-fx3-fx6-lab`)

[![English](https://img.shields.io/badge/Language-English-0969da?style=flat)](./README.en.md)
[![双语总览](https://img.shields.io/badge/主文档-README.md_(中英双语)-1a7f37?style=flat)](./README.md)
[![Stage-B 架构与安全](https://img.shields.io/badge/Stage--B_架构与安全-32门禁_%7C_docs%2FSTAGE--B-8957e5?style=flat)](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md)
[![操作手册与救砖SOP](https://img.shields.io/badge/操作手册与救砖-10支柱_%7C_中英双语-d97706?style=flat)](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)
[![宿主机平台](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![目标芯片](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)_%2B_CXD90058_(ARMv7--R)-orange?style=flat)](#)
[![自动化测试](https://img.shields.io/badge/Automated_Tests-2,980_本地_%7C_2,922_洁净室_(7_Suites)-brightgreen?style=flat)](#四快速开始与验收命令)
[![无供体净室CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![FX6 原厂核实时 GPE0](https://img.shields.io/badge/FX6_GPE0-nop__count%3D0_r1a..r19e_(18%2F18_%2B_45%2F45_%2B_55%2F55)-success?style=flat)](#统一七大自动化验证套件make-test--本地供体-2980-项--洁净室-2922-项)
[![开源协议](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](#五合规声明与开源协议)

> **语言切换 / 深度参考**：[**👉 Switch to Standalone English Documentation (`README.en.md`)**](./README.en.md) · [**中英双语总览主文档 (`README.md`)**](./README.md) · [**Stage-B 全实验室架构与 32 门禁安全规范 (`docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md`)**](./docs/STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [**双语现场操作 SOP 与救砖手册 (`docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`)**](./docs/STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md)

**`sony-fx3-fx6-lab`** 是面向 **Sony Cinema Line ILME-FX3（`Ver. 7.02`，机型 ID `0x91030080`，`ALCIN_UUD`）** 与 **ILME-FX6（`Ver. 6.01`，机型 ID `0x91040086`，`CHAPLIN`）** 数字电影摄影机的净室系统工程、多架构 QEMU 协同仿真、跨机型硬件兼容性验证与真机防变砖安全研究开源仓库。两款机型均搭载 **Sony CXD90057（`AArch64` CE Linux `4.9.337-scel+`）** 主处理器与 **CXD90058（`ARMv7-R` TOPPERS-FMP 1.4.0 `cpapp-b.bin @ 0x00108000`）** 协处理器。

> [!CAUTION]
> **硬件写入硬锁状态（`persistent_emmc_writes_authorized = False` / 严禁持久化刷写真机）**  
> 实验室严格保持持久化刷机与实机连接硬锁关闭（**`NO-GO`**）：`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`hardware_live_attachment_authorized = False`、`edisx_repartition_forbidden = True`（`sector0_mutation_bytes = 0`）、`p8_cp_mutation_forbidden = True`（`cp_mutation_bytes = 0`）、`wbi_p5_write_and_hibernation_forbidden = True`（`wbi_mutation_bytes = 0`）、`calibration_mutation_bytes = 0`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0` 与 `passive_tx_bytes_emitted = 0`。所有 Stage-A / Stage-B 覆盖层仅驻留在易失性 Linux DDR（`tmpfs`）中，全部供体读取严格使用 `os.O_RDONLY`，支持无连接线 `< 1 秒` `FX3_SAFE_STOCK.FLG` SD 哨兵逃生，断电重启即可瞬间 100% 恢复原厂 Sony ILME-FX3 `Ver. 7.02`。

> [!IMPORTANT]
> **净室开源合规边界（BYOF：自备官方固件复现）**  
> 本仓库 **包含 0 字节索尼专有闭源二进制文件**（不含 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`cpapp-b.bin`、`nflasha*` 分区镜像或 `.cpio` 根文件系统镜像）且 **包含 0 字节厂商 AES/RSA 私钥**。全部 7 套测试集（`2,922` 项洁净室测试）与 `Milestone Phase 110 总闸`、`32-Gate`、`10-Pillar 恢复`、`Milestone Phase 90`、`24-Gate`、`RP2040`、`init2`、`Tier-0 GF(256)`、`OTP/RPMB 防回滚`、`Post-Trial` 门禁 CLI 均支持无供体净室 CI（`FX3_FX6_FORCE_CLEAN_ROOM=1 make test`），由 [`.github/workflows/clean-room-ci.yml`](./.github/workflows/clean-room-ci.yml) 在 `ubuntu-latest` + `macos-latest` 自动门禁校验。本地复现虚拟机交互体验请参阅 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**（由 `make verify-byof` 自动守护 `57+57` 指纹与 `46` 项源码常量一致性）。

---

## 一、全实验室工程里程碑（`Phases 1–110` · `Rounds 1–19` · `Waves 1–11`）

### 统一七大自动化验证套件（`make test` — 本地供体 `2,980` 项 / 洁净室 `2,922` 项）

1. **[`outputs/fx3-recovery-adapter/`](outputs/fx3-recovery-adapter/README.md)（本地供体 `439` / 洁净室 `381` 项测试）**
   - **10 支柱救砖恢复主套件（`make verify-10pillar-recovery`）**：汇聚第 `1..7` 支柱（`macOS 26 IOUSBHost`、**Phase 59** `RP2040-Zero -DOPEN_DRAIN` 自检 `make verify-rp2040-fixture`、**Phase 66** `< 1s` `FX3_SAFE_STOCK.FLG` `init2` 逃生 `make verify-init2-escape`、**Phase 72** `GF(256)` RAID-6 Tier-0 备份库 `make verify-tier0-backup`、**Phase 79** `OTP/RPMB` 防回滚 `make verify-antirollback-guard`、`Tier-0..4` 升级阶梯及被动只收 `1.8V` UART `S0..S6` 解码器 `passive_tx_bytes_emitted == 0`），并叠加 **支柱 8（Ph94）** CXD90057 15 分区 GPT CRC32 自愈与 RPMB HMAC-SHA256 重放防火墙 + 双人 SD 救援包（[Phase 94 报告](reports/2026-11-14-phase94-gpt-rpmb-rescue-bundle-verifier/README.md)）、**支柱 9（Ph101）** SVR4 `newc` cpio 遍历/设备节点防火墙与 JEDEC `EXT_CSD[267..269]` Pre-EOL 健康审计（[Phase 101 报告](reports/2026-11-14-phase101-ramdisk-overlay-emmc-health-verifier/README.md)）及 **支柱 10（Ph106）** FDT `0xd00dfeed` `/chosen/bootargs` `ro` 防火墙与 ARM64 `0x644d5241` 内核 `Image` 防跨机校验（[Phase 106 报告](reports/2026-11-14-phase106-fdt-bootargs-kernel-recovery-verifier/README.md)）。

2. **[`outputs/fx3-safety/`](outputs/fx3-safety/)（双模式 `505` 项测试）**
   - **32 门禁主安全预检引擎（`G01..G32`，`make verify-32-gates`）**：在 `G01..G24`（`make verify-24-gates`，含 C2PA、`exFAT`、`USB-LAN`、D-Tap/HDMI 断流、UPS、`+48V` XLR、稳定器、露点 `TEC`、PMIC `5V 900 mA`）之上扩展 **Phase 92**（`G25` Sigma 外挂风扇进排气遮挡与防雨罩背压、`G26` `1/4-20` 螺孔深度与防水壳真空，[Phase 92](reports/2026-11-14-phase92-intake-occlusion-tripod-26gate-safety/README.md)）、**Phase 97**（`G27` IMX510 激光/关机快门帘/IBIS 运输锁、`G28` `-20°C` 低温电池内阻降额与高海拔散热，[Phase 97](reports/2026-11-14-phase97-sensor-curtain-subzero-28gate-safety/README.md)）、**Phase 100**（`G29` 5GHz/6GHz 图传近场 EMI 与热插拔 ESD、`G30` `>6h` exFAT 分片与 CFexpress 零 NVRAM 磨损，[Phase 100](reports/2026-11-14-phase100-wireless-emi-endurance-30gate-safety/README.md)）及 **Phase 104** [`pl_cantilever_dummybatt_and_32gate_guard.py`](outputs/fx3-safety/fx3_safety/pl_cantilever_dummybatt_and_32gate_guard.py)（`G31` 重型 PL 转 E 悬臂力矩 `15mm` 导管支撑与 `G32` 14.8V/26V 假电池 `>8.4V` OVP 爆管熔断防火墙，[Phase 104](reports/2026-11-14-phase104-pl-cantilever-dummybatt-32gate-safety/README.md)）。

3. **[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)（双模式 `517` 项测试）**
   - **Milestone Phase 110 六柱一体化总闸（[`stage_b_milestone110_master_gate.py`](outputs/fx6-on-fx3-closure/fx6_closure/stage_b_milestone110_master_gate.py)，`make verify-milestone-110`，`< 2.5s`）**：汇聚 `32-Gate`、`10-Pillar 恢复`、`>= 20` 固件审计器、`>= 18` VM 阶段、`Round 14/17/19` 真内核全闭环与 `H0 == H2` 16 表面不可变性并生成 `milestone110_sha256`（[Phase 110 报告](reports/2026-11-14-phase110-milestone-master-gate-and-docs-sync/README.md)）。
   - 完整保留 **Phase 90 总闸（`make verify-milestone-90`）**、**Stage-A（`P1..P9+Fan`）**、**Stage-B（`P1..P12+Fan` `13/13` 补丁 / `8` 模块 `18` 锚点，100% SHA-256 回滚）**、**`U1..U5`**、**`S01..S10` 生命周期演练**、**Phase 52/76 候选集成与 Dossier v3**，及 **Phase 62/68/83 `16` 表面 `H0 == H2` 收官审计**（`make verify-post-trial-audit`）。

4. **[`outputs/fx3-vm-trial/`](outputs/fx3-vm-trial/README.md)（双模式 `273` 项测试）**
   - **端口 `8768` 实时 QEMU ARM64 `1024×540` `GPE0` 交互式 Web 控制台（[`FX6菜单.command`](outputs/fx3-vm-trial/FX6菜单.command)）**：原生 `LDEC103` 图标（`60/60` 零崩溃）、LRU 128 页四语池（**`简体中文 / 繁體中文 / EN / 日本語`**）、`P10` 按键台、4 通道 `XLR-H1` VU 表、**Phases 56/64/73/81**（示波器、Cine EI `800/12800`、快门角/`S&Q 1–240fps`、`Shockless WB`/`*M01.XML`、627 点 `Touch AF`、`x4` 放大、`S-Log3` 伪色/`CIZ`/`CAMSET` 往返）、**Phase 95**（`1.33x..2.0x` 变形镜头 IBIS 非对称/居中锁仲裁、Gyroflow `2000Hz` RTMD 遥测、`1kHz -20dBFS` 基准音与 4-Ch `-3.0 dBFS` 限幅器，[Phase 95](reports/2026-11-14-phase95-vm-trial-gyroflow-anamorphic-tone/README.md)），以及 **Phase 102**（预录制 Picture Cache `<=384 MiB` DDR 环缓、电子快门间隔摄影 `mechanical_curtain_actuations=0`、`.cube` `17³/33³/65³ -> 33³` 四面体实时上传与有线 USB-LAN FTPS 队列，[Phase 102](reports/2026-11-14-phase102-vm-trial-picturecache-cube3dlut-ftps/README.md)）。

5. **[`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/README.md)（双模式 `125` 项测试）**
   - **Rounds 1–19（`r1a..r19e`）FX3 `7.02` 原厂内核（`4.9.337-scel+`）混合态真机闭环（`nop_count = 0`、`FX6_NATIVE_FAITHFUL=1`）**：`13/13` 挂载前 SHA-256 核验、`P10` + `P11` + `P12`、`LDEC103` GPE 物理池贴图、**Round 14 四语×三界面 `18/18` 严格正差分**、**Round 17 `Status Check` 完整 `10/10` 标签（`0x2f..0x37,0x39`，$\binom{10}{2}=45/45$ 对两两差分 `> 0` + `10` 步回环 + Tab 9 `WF-12` 免疫）**（[Round 17](reports/2026-11-14-round17-fx6-on-fx3-status-fullsweep-audio/README.md)），以及 **Rounds 18–19 完整 `11/11` 全功能菜单类别（$\binom{11}{2}=55/55$ 对差分 `> 0` + `11x DOWN` 环绕 + 繁中 `Network` `WF-12` 免疫）**（[Round 18](reports/2026-11-14-round18-fx6-on-fx3-menu-8category-closure/README.md)、[Round 19](reports/2026-11-14-round19-fx6-on-fx3-menu-11cat-fullsweep/README.md)）。

6. **[`outputs/fx3-vm/`](outputs/fx3-vm/README.md)（双模式 `568` 项测试）**
   - **18 阶段全板级虚拟相机协同仿真（`fx3_vm_coemulation_suite.py` / `make verify-coemulation`）**：Stages 1–13（BT/双核 `IVSHMEM`/`Soft-GPE0`/FDT/`IMX510`/HIL/`QMP`/`EDID`/`SMPTE 12M`/双卡 `.RSV`/Touch AF/`CAMSET`/回放与露点）+ **Stage 14（Ph91）** Gyroflow `2000Hz` IMU/变形防抖（[Phase 91](reports/2026-11-14-phase91-vm-stage14-gyroflow-rtmd-anamorphic-hil/README.md)）+ **Stage 15（Ph96）** 间隔录制/Picture Cache/FTP/风扇遮挡（[Phase 96](reports/2026-11-14-phase96-vm-stage15-interval-cache-ftp-hil/README.md)）+ **Stage 16（Ph99）** 四面体 3D LUT/`-20°C`/`12G-SDI`（[Phase 99](reports/2026-11-14-phase99-vm-stage16-lut3d-subzero-sdi-hil/README.md)）+ **Stage 17（Ph103）** 5GHz/6GHz TX EMI/`>6h` exFAT 耐久（[Phase 103](reports/2026-11-14-phase103-vm-stage17-emi-exfat-endurance-hil/README.md)）+ **Stage 18（Ph107）** `C2PA 2.1`/镜头阴影/多机车队/PL 悬臂与假电池 OVP（`cnflasha_mutation_bytes=0`, `private_key_exports=0`, [Phase 107](reports/2026-11-14-phase107-vm-stage18-c2pa-shading-mcfleet-hil/README.md)）。

7. **[`outputs/fx3-firmware-lab/`](outputs/fx3-firmware-lab/README.md)（双模式 `553` 项测试）**
   - **20 大净室无密钥审计器（`audit-all` / `make verify-firmware-lab`）**：`#1..#16`（`UFU`..`global.xdb` 128p、Audio/TC/HDMI、AF/IBIS、快门/Tally、白平衡/`OCIO v2`、代理/`*M01.XML`、`CIZ`、伪色/LPCM/UB、回放/AE）+ **`#17（Ph89）`** Gyroflow/Catalyst `RTMD`（[Wave 9](reports/2026-11-14-global-sony-wave9-gyroflow-rtmd-imuvm-intel/README.md)）+ **`#18（Ph93）`** 间隔/Picture Cache/有线 FTP（[Phase 93](reports/2026-11-14-phase93-interval-cache-ftp-auditor/README.md)）+ **`#19（Ph98）`** 四面体 `.cube` LUT + `12G-SDI` 触发（[Phase 98](reports/2026-11-14-phase98-lut3d-tetrahedral-sdi-hdmi-auditor/README.md)）+ **`#20（Ph105）`** `C2PA 2.1` + E 卡口光学阴影 + Monitor & Control 有线车队审计（[Phase 105](reports/2026-11-14-phase105-c2pa-shading-mc-fleet-auditor/README.md)）。

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
| **01 —— 固件升级容器** | `BODYDATA.DAT`（`sauu` / `sdfileinput.elf`） | 机型 ID（`0x91030080` vs `0x91040086`）、区域与签名门禁仅存在于 `p1` 更新模式用户态流程中；`v7.02` `p1` 经 4 锚点 AArch64 `ADRP/BL` 自动定位；Phase 66 验证 `p1` `FAT12/16` 原子交换；Phase 79/94 拦截 OTP/RPMB 降级回滚。 |
| **02 —— Octal-SPI NOR 引导** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | FX3 `7.02` 与 FX6 `6.01` 的 `pformat_config.txt`（`1,274 B`）与 `LdrBkupList.txt`（`65` 键）100% 逐字节一致（`@ 0xFE049000`）；Tier-0 受 `GF(256)` RAID-6 守护；Tier-3 `48000` 波特率救援需通过 `make verify-rp2040-fixture` 治具且支持被动只收 UART（`tx_bytes = 0`）。 |
| **03 —— Bank 0/1 描述符表** | `p2:/setting/Backup.bin`（`0x00fa0080`） | 64 槽位（`9,216 B`）Bank 0（AP）与 Bank 1（CP/校准）完成 0 字节 DDR 重叠证明；`p2:/setting/{psd,defdet}.bin`、`p6:Jiritsu`、`p12:/cert`（`C2PA 2.1` `RQ_LIC.DAT`）与 `p18:/lens/lensfile.bin` 受 `G15` 与 `Ph105` 刚性只读保护。 |
| **04 —— 内核、FDT 与 CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb`（`16,875 B`）与 `tomco.txt` 4 段 `memcfg=`（`1,724.00 MiB`）100% 一致；Phase 106 锁定 FDT `/chosen/bootargs` `ro` 与 ARM64 `0x644d5241`；Stage-A/B 保持 FX3 原厂内核与 `p8:/cpapp-b.bin`（`cp_mutation_bytes = 0`）零改动并封锁 `p5:/wbi`（`wbi_mutation_bytes = 0`）。 |
| **05 —— 相机应用层** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | Stage-A 与 Stage-B（`stage_b_init2_guard.sh`）优先检查 `FX3_SAFE_STOCK.FLG`（`< 1s` 直退原厂），先完成 `13/13` SHA-256 校验与 32 门禁再挂载易失 `tmpfs`（`< 48 MiB` + `ro_sd_loop_bind`），严格逆序 LIFO 卸载（`H0 == H2`）。 |

---

## 三、仓库目录结构

```text
sony-fx3-fx6-lab/
├── .github/workflows/clean-room-ci.yml      # 无供体 Ubuntu + macOS 七套件、32 门禁、10 支柱与 Milestone-110 洁净室 CI
├── Makefile                                 # 统一测试、Milestone-110、32 门禁、10 支柱恢复、Milestone-90、VM 与实验室
├── README.md / README.en.md / README.zh-CN.md
├── docs/
│   ├── STAGE-B-ARCHITECTURE-AND-SAFETY.md   # 中英双语 Stage-B (P1..P12+Fan)、32 门禁 (G01..G32)、18 阶段 VM 与 10 支柱参考
│   ├── STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md # 中英双语现场操典：RP2040、+48V XLR、TEC、风扇、低温、PL/OVP 与 <1s 逃生
│   ├── STAGE-A-HARDWARE-RUNBOOK.md          # 中英双语 Phase H0->H1->H2 非持久 Stage-A 真机执行操作手册
│   └── BYOF-REPRODUCTION.md                 # 中英双语 57+57 项 SHA-256 指纹清单与自备固件复现指南
├── scripts/
│   ├── run_all_lab_tests.py                 # 统一七套件运行器 (本地 2,980 / 洁净室 2,922 项测试) + BYOF 清单 + 卫生检查
│   └── verify_byof_manifest.py              # 中英双语 BYOF SHA-256 语法、46 项源码常量与本地供体一致性审计器
├── outputs/                                 # 七大受控工程包 (本地 2,980 / 洁净室 2,922 项自动化测试)
│   ├── fx3-recovery-adapter/                # 10 支柱救砖：Tier-0..4、RP2040、init2、GF(256)、OTP/RPMB、UART、GPT、Pre-EOL、FDT (439/381)
│   ├── fx3-safety/                          # 32 门禁主预检 G01..G32 (风扇、三脚架、快门帘、-20°C、EMI、>6h、PL、假电池 OVP) (505)
│   ├── fx6-on-fx3-closure/                  # Stage-A/B、Ph52/76 集成、Ph62/68/83/90、Milestone Phase 110 六柱总闸 (517)
│   ├── fx3-vm-trial/                        # 端口 8768 Web UI：128 页、Touch AF、伪色、Gyroflow、预录制、.cube、FTPS (273)
│   ├── fx6-native-presenter-closure/        # Rounds 1..19 FX3 7.02 原厂内核 GPE0：nop=0，18/18 + 10 标签 45/45 + 11 类别 55/55 (125)
│   ├── fx3-vm/                              # 18 阶段双核 AP<->IVSHMEM<->CP 共仿真至 C2PA/光学阴影/车队/OVP (568)
│   └── fx3-firmware-lab/                    # 20 大无密钥审计器：UFU..global.xdb、Gyroflow、Cache/FTP、3D LUT/SDI、C2PA 2.1 (553)
├── reports/                                 # Phases 1..110、Rounds 1..19、Waves 1..11 全球情报与验收报告
└── conversations/                           # 五大专题研究工作区多智能体工程研究对话分类归档
```

---

## 四、快速开始与验收命令

```bash
# 1. 一键运行全部 7 套 2,980 项本地供体测试 (439 + 505 + 517 + 273 + 125 + 568 + 553) + BYOF 清单 (57+57) + 净室零残留审计
make test
make test-json

# 2. 本地模拟 GitHub Actions 无供体洁净室 CI 模式 (7 套 2,922 项测试，零索尼固件依赖)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test
FX3_FX6_FORCE_CLEAN_ROOM=1 make clean-audit

# 3. Milestone Phase 110 六柱总闸 (<2.5s) + 32 门禁、10 支柱救砖与 Phase 90 兼容总闸（双模式通用）
make verify-milestone-110
make verify-32-gates
make verify-10pillar-recovery
make verify-milestone-90
make verify-24-gates
make verify-tier0-backup
make verify-antirollback-guard
make verify-rp2040-fixture
make verify-init2-escape
make verify-post-trial-audit

# 4. Stage-B 全生命周期演练、无线防护、固件实验室（20 审计器）、18 阶段协同仿真与 Stage-A 演练目标
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
- **FX6 128 页 / Big6 / Touch AF / 伪色 / CIZ / Cine EI / Gyroflow / 预录制 / `.cube` / FTPS 控制台**：运行 `./outputs/fx3-vm-trial/FX6菜单.command` 并打开 `http://127.0.0.1:8768/`。
- **FX3 原厂菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（加 `--check` 仅校验输入指纹而不启动 QEMU）。

---

## 五、合规声明与开源协议

1. **零专有固件分发**：本仓库分发 **0 字节** 索尼闭源二进制固件、加密升级镜像或私有密钥。
2. **独立互操作性与防变砖安全研究**：全部源码、Unicorn 仿真测试套件与技术报告均在净室规范下独立编写，仅用于嵌入式系统架构研究、虚拟化探索与硬件刷前防变砖审计，与 Sony Group Corporation 无任何隶属或合作关系。
3. **开源许可**：仓库自研源码采用 MIT 协议发布；针对 QEMU 的补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议。
