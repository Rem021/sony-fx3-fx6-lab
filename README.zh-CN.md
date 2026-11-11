# 索尼 FX3 与 FX6 系统移植、QEMU 虚拟机与净室兼容性研究实验室 (`sony-fx3-fx6-lab`)

[![English](https://img.shields.io/badge/Language-English-0969da?style=flat)](./README.en.md)
[![双语总览](https://img.shields.io/badge/主文档-README.md_(中英双语)-1a7f37?style=flat)](./README.md)
[![宿主平台](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![目标芯片](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)-orange?style=flat)](#)
[![自动化测试](https://img.shields.io/badge/Automated_Tests-131%2F131_Passing_(make_test)-brightgreen?style=flat)](#四快速开始与验收命令)
[![开源协议](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](./LICENSE)

> **语言切换**：[**👉 Switch to Standalone English Documentation (`README.en.md`)**](./README.en.md) · [**中英双语总览文档 (`README.md`)**](./README.md)

**`sony-fx3-fx6-lab`** 是面向 **Sony Cinema Line ILME-FX3（Ver. 7.02，机型 ID `0x91030080`）** 与 **ILME-FX6（Ver. 6.01，机型 ID `0x91040086`）** 数字电影摄影机的净室系统工程、QEMU AArch64 虚拟化、跨机型硬件兼容性验证与真机防变砖安全研究开源仓库。两款机型均搭载 **Sony CXD90057 AArch64 SoC**，运行 Sony CE Linux `4.9.337-scel+` 内核与 TOPPERS-FMP 1.4.0 SMP RTOS 协处理器固件（`cpapp-b.bin` `@ 0x00108000`）。

> [!IMPORTANT]
> **净室开源合规边界（BYOF：自备官方固件复现）**
> 本仓库 **包含 0 字节索尼专有闭源二进制文件**（不含 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`cpapp-b.bin`、`nflasha*` 分区镜像或 `.cpio` 根文件系统镜像）。仓库内全部 Python 离线校验器、无依赖 AArch64 C/汇编工作器、Unicorn 指令级仿真套件、QEMU 设备补丁、Web 交互前端与 SHA-256 验收回执均为独立净室编写。如需在本地复现虚拟机交互体验，请参照 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**（由 `make verify-byof` 自动守护指纹一致性）自备对应 SHA-256 指纹的官方固件。

---

## 一、核心工程里程碑（截至 2026-11-10）

### 主线 1A —— FX6 128 页 Guest `GPE0` 实时互动 UI 与 `fx3-vm-trial` 管线加速
- **100% 全量 128 页原生描述符物理帧缓冲渲染**：在 QEMU ARM64 Guest 内通过 FX6 Ver. 6.01（`ILME-FX6V`）原生 `appFw.so` + `libuxengine.so` + `TextRM` 将全部 **128 张页面描述符表**（`0x02e90fb0..0x02eba7b8`，共 `2,249` 行控件）真实渲染进物理帧缓冲 `0x41e001000`（`GPE0`，`1024×540` RGBA32），全程 **`segv = 0`**（详见 [EVIDENCE-751-812-FULL-128-PAGES.md](reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-751-812-FULL-128-PAGES.md)）。
- **零内存泄漏 Guest 驱动与 22.1 倍 C 扫描线打包器**：重构 [`outputs/fx3-vm-trial/src/fx6_live_guest.c`](outputs/fx3-vm-trial/src/fx6_live_guest.c)（复用静态工作缓冲，消除每帧 `calloc` 泄漏、约 1,500 次 `dlsym` 开销及 `DISP` 越界读取），在 [`outputs/fx3-vm-trial/run_fx6_menu_trial.py`](outputs/fx3-vm-trial/run_fx6_menu_trial.py) 中引入编译态 C 扫描线转换器 `fx6_pack_scanlines` 实现 **22.1 倍** BGRA→PNG 打包加速，并提供纯标准库确定性 CPIO 构建器 [`outputs/fx3-vm-trial/build_live700.py`](outputs/fx3-vm-trial/build_live700.py)。

### 主线 1B —— FX6 原版冷启动 `nop_count = 0` `GPE0` 前景字形与拍摄 HUD 闭环
- **零指令 NOP 原版冷启动渲染突破（`256314b5`）**：交付 [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) 与 [`reports/2026-11-10-fx6-native-presenter-closure/README.md`](reports/2026-11-10-fx6-native-presenter-closure/README.md)，在完整 153 线程 `MWF_Init` + `ScreenManager` + `GraphicsEngine::drawFramebuffer()` 生命周期下，以 **`nop_count = 0`**、**`FX6_NATIVE_FAITHFUL=1`** 达成 **`37procam_menu_initial_setting_presenter`**（初始设置菜单）与 **`25procam_shooting_presenter`**（拍摄主屏 HUD）在物理 `GPE0`（`0x41e001000`，`1024×540`）上的真实前景字形与图标渲染。

### 主线 2 —— FX3 原生固件 QEMU 虚拟机与浏览器交互菜单模拟器
- **零修改启动 FX3 7.02 内核与原厂菜单（`outputs/fx3-vm/`、`outputs/fx3-vm-trial/`）**：完整建模 CXD90057 高位 DDR（`0x400000000`）、ESRAM 邮箱（`0xfe005000`）、GICD、Sony 硬件定时器、SCU、GPIO Bank5、UIPC、DMM、GPE v13/v14 与软件 LDEC LZ77 图标解压，提供一键启动的浏览器交互入口 `FX3菜单.command`（支持 4096 键 / 60 分钟交互预算，约 40.1 秒出首帧待机 OSD，已完成 32 键逐屏导航与 API16 干净恢复验收）。

### 主线 3 —— FX6-on-FX3 `P1..P9 + Fan` 兼容闭环、`U1..U5` 全未知项清零与 12 道防变砖门禁
- **受控工程包**：[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md) 与 [`outputs/fx3-safety/`](outputs/fx3-safety/)（详见 [Phase 12 完整验证报告](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md)）：
  - **10/10 兼容适配矩阵（`P1..P9 + Fan`）**：覆盖 7 个 ELF64 二进制目标（`libInfraSetupFile.so`、`libInfraMediaCommon.so`、`libInfraMediaConfig.so`、`libInfraAppRemoteBoard.so`、`appFw.so`、`libfan.so`、`upm.ko`）的确定性适配与 **100% SHA-256 逐字节无损逆向回滚**、纯 Python `8/16/44.5 MiB` `opelog.vfat` 构建器（`P2`）、`0x92840747` 端点 UIPC 应答合成（`P5`/`P6`，Unicorn 实测验证）及双内核 `pcidma_transfer_async` Sync100 跳板校验（`P7`）。
  - **5 大核心特性路由、设备树（`cxd90057.dtb`）与 `.ko` ABI 校验**：验证 43 个 ELF 的 `DT_NEEDED` 符号闭包（`0` 缺失）、FX3 `48.00 MiB` `p30` 上的 16 组 `33^3` `.cube` 3D LUT 存储余量（`+32.04 MiB`）、FX3/FX6 100% 逐字节一致的 `cxd90057.dtb`（`16,875 B`，68 节点 / 493 属性）与 7 项 `kemco.txt` `memrsv=` 保留段，以及 `P9` `upm.ko` 的 `vermagic` 与全部 61 项 `modversion_info` CRC 零漂移。
  - **零重分区 `p15` / DDR `tmpfs` 容量预算、`nflasha3-initrd` / WBI（`p5`）休眠安全红线与 Stage-A 原子编排器**：证明 `edisx_repartition_forbidden = True`（`sector0_mutation_bytes = 0`）与 **Stage-A WBI 休眠安全红线（`wbi_p5_write_and_hibernation_forbidden = True`，`wbi_mutation_bytes = 0`）**（审计 27 项 `nflasha3-initrd` → `/usr` 只读 → `insmod_drv2` `#24` `upm.ko` → `im.elf` 早启工件及 FX6 `202,677,056 B` `p5` `WBI2` 休眠头与 `+13.47 MiB` `wbimem` 地址碰撞），FX3 `500.00 MiB` `p15` 具备 `+138.76 MiB` 裸载荷 / `+74.81 MiB` ext2 镜像余量，Stage-A `tmpfs` 峰值仅 `57.46–130.76 MiB`（严守 `256.00 MiB` 上限，占 `1,917.62 MiB` 可用 DDR 的 `3.00%–6.82%`）；构建确定性 SVR4 `cpio newc`（`30,860 B`，含 `30-stage-a-orchestrator.sh` 共 6 项），并在 `/bin/sh` 隔离沙箱中验证 4 类异常回滚与 **6 大 Verify-Before-Mount 原子校验 + 逆序 LIFO 卸载场景（10 次执行）** 全程 **`0` 字节 eMMC 写入与 `0` 字节 WBI 写入**。
  - **五大蓝图未知项（`U1..U5`）100% 离线验证清零**：
    - **`U1`**：通过 30 分区零重分区映射（`p20 -> p30`、`p21 -> tmpfs` VFAT 回环、`p15` `500 MiB` 容量吻合）与 Tier-0 只读 `/sys/block/nflasha/size` 采集闭环清零。
    - **`U2`**：通过 Phase 10 `cp_rtos_compatibility_verifier.py` 清零——证明 FX3 与 FX6 `tomco.txt` 的 4 段 `memcfg=`（`1,724.00 MiB`）及 20 项 IPC 键值 **100% 相同**，定位 FX6 `cpapp-b.bin`（`17.12 MiB` `@ 0x00108000`）内 8 项 FX6 独占硬件驱动风险（`Darwin` 电子可变 ND 与 `Mew` SDI/Genlock FPGA），并强制锁定 **Stage-A 原厂 CP 红线（`p8_cp_mutation_forbidden = True`，`cp_mutation_bytes = 0`）**。
    - **`U3`**：通过 `0xfa0080` 64 槽位 Bank 0/1 零地址重叠证明与原厂 CP 红线清零（FX3 原厂 CP 直接读取本机 `psd.bin` / `defdet.bin` / `lensfile.bin` / `p6:Jiritsu` 原厂校准数据）。
    - **`U4`**：通过 Unicorn AArch64 指令级仿真证明 `SetupFile::RcvThread`（`0x19650`）与 `KikiLogGenerator_res_ope`（`0x3cb0`）在 `ENOENT`/`EINVAL`/`EROFS` 下安全降级返回，并提供 `20,588 B` RAM-Shadow `BK4\0` 合成器。
    - **`U5`**：通过 `ud_send_lsi.elf`（`0x804b0376`）+ `loader_nor.bin`（`0xFE049000`）10 组 Unicorn 边界案例验证 + Phase 11 `p1_recovery_bridge_verifier.py` 跨包 `p1` 恢复容器与两步原子退出复位清零。
  - **Tier-0 无依赖只读备份、跨包 `p1` 恢复桥接与 12 道刷前安全门禁**：零外部符号 AArch64 Linux `svc #0` 双遍只读备份工作器（`native/tier0_backup_worker.c`，覆盖 11 项关键分区）通过 Unicorn 全路径验证，联合 Phase 11 `p1_recovery_bridge_verifier.py` 对齐 `fx3_recovery`，并与 `fx3_safety` **12/12** 道门禁联动（`persistent_write_release = False`）。

### 主线 4 —— FX3 离线恢复适配工具（`v0.5`）与服务接口安全工具集
- **零外部依赖 `p1` 与引导分区工具链（`outputs/fx3-recovery-adapter/`）**：针对 `/dev/cnflasha1`（`p1` 恢复更新分区）与 `/dev/nflashaB0`/`B1`（`boot0`/`boot1`）提供 `inspect`、`build`、`verify`、`diagnose`、`rollback` 及无 libc 静态链接 AArch64 ELF 只读采集工作器，与主线 3 跨包桥接校验（`verify-p1-recovery-bridge`）并配套 **58 项** 单元与故障注入测试。

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
| **01 —— 固件升级容器** | `BODYDATA.DAT`（`sauu` / `sdfileinput.elf`） | 机型 ID（`0x91030080` vs `0x91040086`）、区域与签名门禁仅存在于 `p1` 更新模式用户态流程中。 |
| **02 —— Octal-SPI NOR 引导** | `infomisc.dat` / `DGU.bin` / `loader_nor.bin` | FX3 7.02 与 FX6 6.01 的 `pformat_config.txt`（`1,274 B`）与 `LdrBkupList.txt`（`65` 键）100% 逐字节一致（`@ 0xFE049000`）。 |
| **03 —— Bank 0/1 描述符表** | `p2:/setting/Backup.bin`（`0x00fa0080`） | 64 槽位（`9,216 B`）Bank 0（AP）与 Bank 1（CP/校准）描述符表完成 0 字节 DDR 重叠证明；Bank 0 AP 加载地址 100% 一致。 |
| **04 —— 内核、FDT 与 CP RTOS** | `vmlinux.bin` + `cxd90057.dtb` + `cpapp-b.bin` | `cxd90057.dtb`（`16,875 B`）与 `tomco.txt` 4 段 `memcfg=`（`1,724.00 MiB`）100% 一致；Stage-A 保持 FX3 原厂内核、原厂 `p8:/cpapp-b.bin`（`@ 0x00108000`）零改动并封锁 `p5:/wbi` 休眠快照。 |
| **05 —— 相机应用层** | `im.elf` + `/usr/lib/appFw.so` + `UXEngine` | `30-stage-a-orchestrator.sh` 先完成全部 11 项 SHA-256 原子校验再挂载 `tmpfs` RAM-Overlay（`0` 字节 eMMC/WBI 写入，严格逆序 LIFO 卸载，重启自动回退原厂 FX3）。 |

---

## 三、仓库目录结构

```text
sony-fx3-fx6-lab/
├── Makefile                                    # 统一测试 (`make test`)、BYOF 审计 (`make verify-byof`) 与候选包干跑 (`make dry-run`)
├── README.md                                   # 中英双语完整主文档
├── README.en.md                                # 独立纯英文说明文档 (2026-11-10)
├── README.zh-CN.md                             # 独立纯中文说明文档 (2026-11-10)
├── docs/
│   └── BYOF-REPRODUCTION.md                    # 净室自备固件中英双语 51+51 项 SHA-256 指纹清单与复现指南
├── scripts/
│   ├── run_all_lab_tests.py                    # 统一 131 项测试运行器 + BYOF 清单审计 + `git status --porcelain` 净室卫生审计
│   └── verify_byof_manifest.py                 # 中英双语 BYOF SHA-256 语法、源码常量与本地供体固件一致性审计器
├── outputs/
│   ├── fx6-on-fx3-closure/                     # Phase 12 P1..P9+Fan、U1..U5、initrd/WBI、Stage-A 原子编排、p1 桥接与 Tier-0 (56 项测试)
│   ├── fx6-native-presenter-closure/           # 原版冷启动 `nop_count=0` `FX6_NATIVE_FAITHFUL=1` GPE0 前景字形与拍摄 HUD 闭环
│   ├── fx3-safety/                             # 12 道刷前安全门禁、Sector-0/BK4 契约与变砖分类器 (17 项测试)
│   ├── fx3-recovery-adapter/                   # FX3 离线恢复适配工具 v0.5 与 AArch64 静态采集工作器 (58 项测试)
│   ├── fx3-vm-trial/                           # 交互式 FX3 与 FX6 (128 页 `live700`、22.1x C 扫描线加速) 网页模拟器入口
│   └── fx3-vm/                                 # FX3 最小研究 QEMU AArch64 虚拟机与高位 DDR / ESRAM 补丁
├── reports/
│   ├── 2026-11-10-fx6-p1p2p4-and-tier0/        # Phase 1–12 兼容适配、U1..U5 清零、initrd/WBI、p1 桥接与 12 道门禁主验证报告
│   ├── 2026-11-10-fx6-native-presenter-closure/# 原版冷启动 `nop_count=0` GPE0 前景字形与拍摄 HUD 证据报告
│   ├── 2026-11-08-fx6-native-text-gpe0/        # 100% 128 页 FX6 描述符物理 GPE0 渲染证据报告
│   └── 2026-11-03-fx6-full-system-to-fx3/      # FX6 6.01 vs FX3 7.02 30 分区与 SPI NOR 全系统静态审计
└── conversations/                              # 多智能体工程研究对话分类归档 (135 篇)
```

---

## 四、快速开始与验收命令

### 4.1 一键运行全部 131 项自动化测试、BYOF 指纹审计与净室检查（`make test` / `make verify-byof`）

```bash
# 运行全部 3 套测试集 (58 项 fx3-recovery-adapter + 17 项 fx3-safety + 56 项 fx6-on-fx3-closure = 131 项) + BYOF 与零二进制/.pyc 残留检查
make test

# 单独校验中英双语 docs/BYOF-REPRODUCTION.md 清单 (51+51 项镜像、40 项源码常量与可选本地固件)
make verify-byof

# 运行完整 FX6-on-FX3 离线候选包干跑验收 (P1..P9 + Fan + U1..U5 + CP RTOS + p1 桥接 + Stage-A/WBI + 12/12 安全门禁)
make dry-run

# 单独运行 Phase 11 跨包 p1 桥接与 Phase 12 nflasha3-initrd / WBI (p5) / Stage-A 原子编排校验器
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
```

### 4.2 启动交互式 FX3 或 FX6 网页菜单模拟器（需自备 BYOF 固件）

按 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)** 准备匹配 SHA-256 指纹的官方固件后：
- **FX6 128 页 / Big6 实时网页模拟器**：运行 `./outputs/fx3-vm-trial/FX6菜单.command`，浏览器访问 `http://127.0.0.1:8768/`。
- **FX3 原生菜单网页模拟器**：运行 `./outputs/fx3-vm-trial/FX3菜单.command`（或加 `--check` 仅校验输入指纹而不启动 QEMU）。

---

## 五、合规声明与开源协议

1. **零专有固件分发**：本仓库分发 **0 字节** 索尼闭源二进制固件、加密升级镜像或私有密钥。
2. **独立互操作性与防变砖安全研究**：全部源码、Unicorn 仿真测试套件与技术审计报告均在净室规范下独立编写，仅用于嵌入式系统架构研究、虚拟化探索与硬件刷前防变砖审计，与 Sony Group Corporation 无任何隶属或合作关系。
3. **开源许可**：仓库自研源码采用 [MIT](./LICENSE) 协议发布；针对 QEMU 的补丁遵循 [GPLv2](outputs/fx3-vm/COPYING-QEMU) 协议。
