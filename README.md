# Sony FX3 & FX6 Porting and QEMU Virtual Machine Lab (`sony-fx3-fx6-lab`)

> **Sony ILME-FX3 (Ver. 7.02) & ILME-FX6 (Ver. 6.01) System Emulation, Reverse Engineering, and Cross-Model Firmware Porting Research**

[![Platform](https://img.shields.io/badge/Host-macOS%20Apple%20Silicon%20(MTTCG)-blue)](#)
[![Target](https://img.shields.io/badge/Target-Sony%20CXD90057%20(AArch64)-orange)](#)
[![Status](https://img.shields.io/badge/FX3%20Menu%20VM-Interactive%20Web%20UI%20(r10)-success)](#1-fx3-模拟器与可视化网页菜单已部署可交互)
[![Status](https://img.shields.io/badge/FX6%20on%20FX3%20VM-Booted%20to%20MEDIA__START%20(Headless)-yellow)](#2-fx6-系统移植到-fx3-模拟器启动进度)

---

## 项目简介 (Overview)

本项目致力于在 Apple Silicon Mac (QEMU AArch64 TCG) 上构建 **Sony Cinema Line ILME-FX3 (`0x91030080`)** 的高保真系统级模拟器，并在此基础上推进将 **Sony ILME-FX6 (`0x91040086`, Ver. 6.01)** 完整系统（及 Venice / FX6 色彩与菜单能力）移植到 FX3 硬件与模拟器平台上的全链路工程研究。

为遵守版权合规与 GitHub 仓库体积规范，本仓库**100% 开源所有自研代码、QEMU 硬件模型补丁、内核模块与用户态兼容垫片（Shims/Helpers）、浏览器端菜单交互模拟器、自动化 GDB/QMP 观测框架、静态逆向工具与全部阶段核查报告**；不包含索尼原厂闭源二进制固件文件。自备官方固件复现指南详见 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**。

---

## 核心进展总览（截至 2026-11-06）

### 1. FX3 模拟器与可视化网页菜单（已部署可交互）

- **最小 Linux 与应用加载器基线**（[outputs/fx3-vm/README.md](outputs/fx3-vm/README.md)）：
  - 通过定制 QEMU 补丁（[fx3-esram-high-ddr.patch](outputs/fx3-vm/source-patches/fx3-esram-high-ddr.patch)）在 `0x400000000` 映射 DDR、建立 `0xfe005000` ESRAM 邮箱、Sony 硬件定时器、SCU 请求与 GPIO Bank5 模型，无需 NOP 破坏原厂内核即可在 Mac 上直接启动 FX3 7.02 原厂内核 `4.9.337-scel+`。
- **AP70–AP105 原厂菜单全链路点亮**（[reports/2026-11-01-fx3-vm-resumed-repair/README.md](reports/2026-11-01-fx3-vm-resumed-repair/README.md)）：
  - 攻克了 LCD/OSD 平面、GPE v13/v14 图形引擎、DMM 显示内存、UIPC/CP 备份同步、软件 LDEC 解码、按键输入队列及冷启动保存等 35+ 个关键关卡，实现在浏览器中实时查看并操作 **FX3 原厂相机菜单**。
- **一键试用入口（r10 正式部署版，支持 4096 键 / 60 分钟）**：
  - 入口脚本与文档位于 **[outputs/fx3-vm-trial/](outputs/fx3-vm-trial/README.md)**（双击 `FX3菜单.command` 并在打印的本机网页点击「开始本轮模拟器」即可交互操作 `MENU`、方向键、确定与 `C4`）。
  - 完整 32 键真实网页导航与退出恢复验收记录见 **[outputs/fx3-vm-trial/新版验收记录.md](outputs/fx3-vm-trial/新版验收记录.md)**。

### 2. FX6 系统移植到 FX3 模拟器启动进度

> 核心报告：
> - **[reports/2026-11-05-fx6-capid-grm-frontier/README.md](reports/2026-11-05-fx6-capid-grm-frontier/README.md)**（CP/CAPID/GRM/UXEngine/DMM 混合前沿全记录）
> - **[reports/2026-11-05-fx6-cp-helper-agnostic/README.md](reports/2026-11-05-fx6-cp-helper-agnostic/README.md)**（CP helper 地址无关绑定突破）
> - **[reports/2026-11-05-fx6-boot-gate-audit/REPORT.md](reports/2026-11-05-fx6-boot-gate-audit/REPORT.md)**（三条启动路线与门槛审计）
> - **[work/.../fx6-66ed0f78-audit/REPORT.md](work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-66ed0f78-audit/REPORT.md)**（180s 长稳运行独立只读审计）

| 里程碑阶段 | 状态 | 技术细节与验证证据 |
| :--- | :---: | :--- |
| **1. CP Helper 跨内核地址无关绑定** | **已打通** | `fx6_cp_backup_sync100_agnostic_v1` 同时支持 FX3 (`0xffffff80083220c8`) 与 FX6 (`0xffffff8008322f70`) `pcidma_transfer_async` 入口，动态计算 fallback，`FX3_BACKUP_CP_INSMOD_RC=0`。 |
| **2. FX6 `bootin` / `im.elf` / `appFw.so` 启动** | **已打通** | FX6 主应用框架 `/usr/lib/appFw.so` 在模拟器中真实加载执行；通过 `fx3-capid-v50-preinit.so` 处理 `0x032d200d` 10B 音频请求。 |
| **3. 用户态图形与 UI 库闭包 (`libgrm` / `UXEngine`)** | **已打通** | 集成 FX6 原厂 `libgrm.so`、`libma.so`、`libgrm_bmp.so`、`libInfraAppRemoteBoard.so`、`liblibra.so`、`libstella.so`、`libuxengine.so`、`grm_ma.ko` 等完整依赖闭包。 |
| **4. 180 秒无 Oops 稳定运行至 `MEDIA_START`** | **已达成** | 定位并绕过 `appFw` 异步日志 `std::future::get` 阻塞（`0x2159c50`）、`upm.ko` `upm_senser_dfs_measurement+0x4a0` 空调用与 `backup.ko` `0x75c` 断点后，系统稳定运行 180s 零 Oops，触发 `FX3_MEDIA_START_BRANCH`。 |
| **5. 宿主按键注入 (`MENU`/`DOWN`/`UP`/`LEFT`)** | **已打通** | 通过 QEMU GDB 物理内存门向 `0x41df00000` 注入按键序列，FX6 原生输入队列 100% 接收并确认（`FX3_KEY95_STEP_DONE`）。 |
| **6. 可视化屏幕输出与开机断言消解** | **攻关中** | 查明 GPE `type=0x403` surface 仅为 `request_capture` 缓冲（全零），FX6 `appFw.so` 真实显示缓冲走 **DMM (`dmm_alloc_and_open` / `dmm_mmap`)**；同时已定位 `set_model_for_boot_screen()` 对 Backup 键 `0x02cf0214`/`0x02cf0218` 的单字节 `0/1` 契约，并完成了静态 AArch64 映射快照工具 `fx3-map-snapshot` 离线验收。 |

### 3. FX6 6.01 刷入 FX3 7.02 真机硬件静态兼容矩阵与恢复工具

- **全系统静态兼容矩阵与最小可逆路径**（**[reports/2026-11-03-fx6-full-system-to-fx3/README.md](reports/2026-11-03-fx6-full-system-to-fx3/README.md)**）：
  - 完整比对了 FX3 7.02 与 FX6 6.01 的 30 个 eMMC 逻辑分区（Sector 0 `"8246"` `"2.00"` 分区表）、SPI NOR 物理扇区布局（`pformat_config.txt` 100% 相同）、`Backup.bin`（819 vs 840 子系统）、`p7` (`/rootfs`) vs `p3` RAM disk 架构差异，以及 `p20` (`/usr/data/lut`) / `p21` (`/etc/opelog`) 硬编码依赖。
  - 明确划定了机身个体校准分区红线（`p6` Jiritsu、`p18` `lensfile.bin`、`p2` `psd.bin` / `defdet.bin`）与先备份后实验的阶段 0/1 方案。
- **FX3 离线恢复适配与启动区采集工具 0.5**（**[outputs/fx3-recovery-adapter/README.md](outputs/fx3-recovery-adapter/README.md)**）：
  - 提供针对 FX3 `p1` 恢复分区与 `boot0`/`boot1` 的离线检查（`inspect`）、候选构建（`build`）、校验（`verify`）、回滚还原（`rollback`）以及静态链接无依赖 AArch64 工作器生成（`build-worker` / `build-boot-worker`）。

---

## 仓库目录结构 (Repository Structure)

```text
sony-fx3-fx6-lab/
├── README.md                                 # 项目总览与快速导航
├── docs/
│   └── BYOF-REPRODUCTION.md                  # 官方固件 SHA-256 指纹清单与自备固件复现指南
├── outputs/                                  # 正式交付物与可执行入口
│   ├── fx3-vm/                               # FX3 Mac 最小研究虚拟机（启动脚本、QEMU 补丁与构建溯源）
│   ├── fx3-vm-trial/                         # FX3 原厂菜单网页交互模拟器入口（FX3菜单.command 与验收记录）
│   ├── fx3-recovery-adapter/                 # FX3 恢复分区与 boot0/boot1 离线适配工具 0.5 (Python + AArch64 C/ASM)
│   ├── fx3-safety/                           # FX3 刷机安全边界与防变砖检查清单
│   └── progress-20261103/                    # 项目三维进度可视化静态网页快照
├── reports/                                  # 里程碑技术报告与实验回执
│   ├── 2026-11-05-fx6-capid-grm-frontier/    # FX6 混合启动前沿：CP/CAPID/GRM/UXEngine/按键注入/DMM 分析
│   ├── 2026-11-05-fx6-cp-helper-agnostic/    # FX6 地址无关 CP Helper 绑定与 appFw 执行报告
│   ├── 2026-11-05-fx6-boot-gate-audit/       # FX6 在固定 FX3 虚拟机上开机的三条路线审计
│   ├── 2026-11-03-fx6-full-system-to-fx3/    # FX6 6.01 全系统刷入 FX3 7.02 兼容矩阵与最小可逆路径
│   ├── 2026-11-01-fx3-vm-resumed-repair/     # FX3 模拟器 AP70–AP105 菜单修复全套技术笔记与网页菜单截图
│   ├── 2026-11-01-fx3-vm-deployment/         # FX3 最小研究虚拟机部署与验证报告
│   ├── 2026-11-01-fx3-gemini-integration/    # Gemini 辅助逆向集成记录
│   └── 2026-10-31-venice-phayen-color-chain/ # Venice / FX6 / FX3 色彩科学链路研究
├── research_notes/                           # 早期专题研究笔记（FX5/FX3 移植复核、救援、编码模式、诊断协议等）
└── work/                                     # 核心工程源码、垫片、运行器与自动化审计套件（已剥离大体积二进制）
    ├── fx3-color-port-20261027/              # FX6 供体评估、CP/CAPID/GRM C 源码、映射快照采集器、Backup/断言契约审计
    ├── fx3-vm-20261101/                      # FX3 QEMU 补丁、AP1–AP105 运行时 C 垫片、v25 Web 菜单模拟器服务端/前端源码
    └── sony-firmware-20261024/               # Stage 1–286 固件解包、服务模式协议、USB 传输与恢复通道研究源码
```

---

## 快速开始 (Quick Start)

### 1. 运行 FX3 恢复适配工具离线自检（无需外部固件二进制）

```bash
cd outputs/fx3-recovery-adapter
python3 -B -m unittest discover -s tests -v
```

### 2. 运行 FX6 串口故障检测器与映射采集器单元测试（无需外部固件二进制）

```bash
python3 -B -m unittest discover -s work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-serial-fault-detector/tests -v
```

### 3. 在自备固件环境下启动 FX3 网页菜单模拟器或 FX6 Headless 虚拟机

请先参阅 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** 准备好对应 SHA-256 的官方固件镜像，然后：

- **启动 FX3 网页可视化菜单模拟器**：
  双击 `outputs/fx3-vm-trial/FX3菜单.command`，打开终端输出的 `http://127.0.0.1:<port>`，点击 **「开始本轮模拟器」**。
- **运行 FX6-on-FX3 Headless 启动探测**：
  ```bash
  python3 -B work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/run_gpecap9_once.py --check
  ```

---

## 免责声明与许可说明 (Disclaimer & License)

1. 本项目仅用于相机系统架构研究、QEMU 虚拟化技术探索与固件安全审计，与 Sony Group Corporation 无任何关联。
2. 本仓库不分发任何受版权保护的 Sony 原厂固件代码或二进制映像。
3. 仓库中针对 QEMU 的修改补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 许可。在对任何真机执行写入操作前，请务必阅读 [outputs/fx3-safety/](outputs/fx3-safety/) 与 [reports/2026-11-03-fx6-full-system-to-fx3/README.md](reports/2026-11-03-fx6-full-system-to-fx3/README.md) 中的完整备份红线要求。
