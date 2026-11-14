# 索尼 FX3 与 FX6 系统移植、QEMU 虚拟机与净室兼容性研究实验室 (`sony-fx3-fx6-lab`)

[![English](https://img.shields.io/badge/Language-English-0969da?style=flat)](./README.en.md)
[![双语总览](https://img.shields.io/badge/主文档-README.md_(中英双语)-1a7f37?style=flat)](./README.md)
[![宿主平台](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![目标芯片](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)-orange?style=flat)](#)
[![自动化测试](https://img.shields.io/badge/Automated_Tests-224_Passing_(make_test)-brightgreen?style=flat)](#四快速开始与验收命令)
[![无供体净室CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![开源协议](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](./LICENSE)

> **语言切换**：[**👉 Switch to Standalone English Documentation (`README.en.md`)**](./README.en.md) · [**中英双语总览文档 (`README.md`)**](./README.md)

**`sony-fx3-fx6-lab`** 是面向 **Sony Cinema Line ILME-FX3（Ver. 7.02，机型 ID `0x91030080`）** 与 **ILME-FX6（Ver. 6.01，机型 ID `0x91040086`）** 数字电影摄影机的净室系统工程、QEMU AArch64 虚拟化、跨机型硬件兼容性验证与真机防变砖安全研究开源仓库。两款机型均搭载 **Sony CXD90057 AArch64 SoC**，运行 Sony CE Linux `4.9.337-scel+` 内核与 TOPPERS-FMP 1.4.0 SMP RTOS 协处理器固件（`cpapp-b.bin` `@ 0x00108000`）。

> [!IMPORTANT]
> **净室开源合规边界（BYOF：自备官方固件复现）**
> 本仓库 **包含 0 字节索尼专有闭源二进制文件**（不含 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`cpapp-b.bin`、`nflasha*` 分区镜像或 `.cpio` 根文件系统镜像）。仓库内全部 Python 离线校验器、无依赖 AArch64 C/汇编工作器、Unicorn 指令级仿真套件、QEMU 设备补丁、Web 交互前端与 SHA-256 验收回执均为独立净室编写，并通过 `.github/workflows/clean-room-ci.yml` 在 `ubuntu-latest` + `macos-latest` 无供体环境下自动门禁验证。如需在本地复现虚拟机交互体验，请参照 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**（由 `make verify-byof` 自动守护指纹一致性）自备对应 SHA-256 指纹的官方固件。

---

## 一、核心工程里程碑（截至 2026-11-14）

### 主线 1A —— FX6 128 页 Guest `GPE0` 实时互动 UI 与 `fx3-vm-trial` 管线加速
- **100% 全量 128 页原生描述符物理帧缓冲渲染**：在 QEMU ARM64 Guest 内通过 FX6 Ver. 6.01（`ILME-FX6V`）原生 `appFw.so` + `libuxengine.so` + `TextRM` 将全部 **128 张页面描述符表**（`0x02e90fb0..0x02eba7b8`，共 `2,249` 行控件）真实渲染进物理帧缓冲 `0x41e001000`（`GPE0`，`1024×540` RGBA32），全程 **`segv = 0`**（详见 [EVIDENCE-751-812-FULL-128-PAGES.md](reports/2026-11-08-fx6-native-text-gpe0/EVIDENCE-751-812-FULL-128-PAGES.md)）。
- **零内存泄漏 Guest 驱动、22.1 倍 C 扫描线打包器与 17 项离线单测**：重构 [`outputs/fx3-vm-trial/src/fx6_live_guest.c`](outputs/fx3-vm-trial/src/fx6_live_guest.c)（复用静态工作缓冲，消除每帧 `calloc` 泄漏、约 1,500 次 `dlsym` 开销及 `DISP` 越界读取），在 [`outputs/fx3-vm-trial/run_fx6_menu_trial.py`](outputs/fx3-vm-trial/run_fx6_menu_trial.py) 中引入编译态 C 扫描线转换器 `fx6_pack_scanlines` 实现 **22.1 倍** BGRA→PNG 打包加速，提供纯标准库确定性 CPIO 构建器 [`outputs/fx3-vm-trial/build_live700.py`](outputs/fx3-vm-trial/build_live700.py)，并为主线 1A 与主线 2（`fx3-vm`）配套 **17 项**双模式自动化单测（[`outputs/fx3-vm-trial/tests/test_vm_trial.py`](outputs/fx3-vm-trial/tests/test_vm_trial.py)）。

### 主线 1B —— FX6 原版冷启动 + Round 8 FX6-on-FX3 混合态 Stage-A QEMU 端到端闭环（`r1a..r8b`，22 张 PNG 凭证，16 项单测）
- **零指令 NOP 原版冷启动与全栈 Presenter 闭环（`r1a..r7c`）**：交付 [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) 与 [`reports/2026-11-10-fx6-native-presenter-closure/README.md`](reports/2026-11-10-fx6-native-presenter-closure/README.md)，在 **`FX6_NATIVE_FAITHFUL=1`**（`nop_count = 0`、`subst_* = 0`）与 161 活跃线程完整生命周期下，连续跑通初始设置（`sid=0x03`）、拍摄主屏 HUD（`sid=0x02`，`29` 色）、原生 `0x7023`（`CANCEL`）冷启动提示窗关闭、Big6 主屏（`sid=0x0a`，`74` 色）、Big6 参数子窗（`sid=0x0c`，`59` 色）、Cine EI Base Look（`sid=0x0b`，`66` 色）、1/2/3 层完整菜单树（`sid=0x0f` / `0x10` / `0x11`）、`Presenter::close` 逐位一致退回拍摄主屏，以及 `Backup_write(0x02cf0546={0x01})` `S-Cinetone` 实时参数修改持久化往返（`1,928` 像素字形增量）。
- **Round 8 FX6-on-FX3 Stage-A 混合态 QEMU 真实内核启动闭环（`r8a..r8b`）**：新增 `fx6-stage-a-verify.c` 与 [`reports/2026-11-14-fx6-on-fx3-qemu-hybrid/README.md`](reports/2026-11-14-fx6-on-fx3-qemu-hybrid/README.md)，直接使用 **FX3 7.02 原厂内核 `vmlinux.bin`**（`Linux version 4.9.337-scel+ #1 SMP PREEMPT Thu Dec 25 08:15:40 JST 2025`）+ FX3 7.02 `cxd90057.dtb` + Stage-A `P1..P9 + Fan` 适配补丁包（Guest 内 **10/10** SHA-256 挂载前原子校验）+ 8 MiB `opelog.vfat` + `20,588 B` `RAM-Shadow BK4\0` + `P9` `upm.ko` 启动，在 **`nop_count = 0`** 与 148 个实时线程下渲染出与原版 `r5b` 逐位一致的 **`r8a` 拍摄主屏 HUD**（`sid=0x02`，`5,451` 非零像素，`29` 色）及 **`r8b` Big6 主屏**（`sid=0x0a`，`337,227` 非零像素，`74` 色）。

### 主线 2 —— FX3 原生固件 QEMU 虚拟机与浏览器交互菜单模拟器
- **零修改启动 FX3 7.02 内核与原厂菜单（`outputs/fx3-vm/`、`outputs/fx3-vm-trial/`）**：完整建模 CXD90057 高位 DDR（`0x400000000`）、ESRAM 邮箱（`0xfe005000`）、GICD、Sony 硬件定时器、SCU、GPIO Bank5、UIPC、DMM、GPE v13/v14 与软件 LDEC LZ77 图标解压，提供一键启动的浏览器交互入口 `FX3菜单.command`（支持 4096 键 / 60 分钟交互预算，约 40.1 秒出首帧待机 OSD，已完成 32 键逐屏导航与 API16 干净恢复验收）。

### 主线 3 —— FX6-on-FX3 Phase 18 全栈兼容闭环（`P1..P9 + Fan + P10`、`U1..U5`、外设 UX / 音频、影像 / 3D LUT / 5 轴防抖与 12 道防变砖门禁）
- **受控工程包**：[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)、[`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md) 与 [`outputs/fx3-safety/`](outputs/fx3-safety/)（详见 [Phase 1–16 主报告](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md)、[Phase 17 外设 UX 报告](reports/2026-11-14-phase17-fx3-input-display-audio-audit/README.md)、[Phase 18 影像与防抖报告](reports/2026-11-14-phase18-ap-cp-imaging-ibis-audit/README.md)）：
  - **10/10 核心兼容矩阵（`P1..P9 + Fan`）+ `P10` 机身按键适配**：覆盖 7 个 ELF64 二进制目标的确定性适配与 **100% SHA-256 逐字节无损逆向回滚**、纯 Python `8/16/44.5 MiB` `opelog.vfat` 构建器（`P2`）、`0x92840747` 端点 UIPC 应答合成（`P5`/`P6`，Unicorn 实测验证）及双内核 `pcidma_transfer_async` Sync100 跳板校验（`P7`）。
  - **Phase 17 FX3 物理机身按键（`P10`）、电容触控、翻转屏/HDMI 显示路由与 `XLR-H1` 音频手柄闭环（`make verify-peripheral-ux`）**：逐项审计 `1,115` 项按键映射与 `169` 项活跃事件表，证实 15 个核心操控键原生 1:1 直通、`MENU >= 1000 ms` 原生长按进全量菜单，并提供 **24 字节 `.rodata` `P10` 键值翻译表（`P10_APPFW_KEYMAP_SPEC`，100% SHA-256 无损回滚 + Unicorn C++ `std::unordered_map` 实测）** 解锁 FX3 机身 `Fn -> Big6 HOME`、`C1 -> KURU_PON`、`C2 -> MENU_CANCEL`、`C3 -> DISP_SEL`、`PLAY -> THUMBNAIL`、`DELETE -> USER`；Unicorn 验证 `libInfraTp.so` `1024×540` 触控坐标、`AVBB_SCN_START_PANELEVF.so` `GetOutputSel` LCD/HDMI OSD 路由与 `XLR-H1`（`F48B24C4_F96B24C2`）热靴超时安全回退（`E_TMO -> 0x8000`）。
  - **Phase 18 FX6 AP ↔ FX3 Stock-CP 影像链路、3D LUT / Cine EI / 双原生 ISO、XAVC / E 卡口 AF 与 5 轴 IBIS 防抖锁止闭环（`make verify-ap-cp-imaging`）**：跨机型全量扫描证实 FX3 7.02 原厂 CP 原生实现 `0x92840747` 上 **全部 44 个 UIPC BB 操作码**（含 `0x0165`/`0x0166` 3D LUT DMA）及 9 条共享队列，精准隔离仅有的 **2 条 FX6 独占阻塞队列（`0x92d2091c` 外置 RTC `std::future` 死锁与 `0x91db059b` 智能侧手柄）** 并完成 AP 侧合成应答验证；Unicorn 验证同源 `164 B` `mpr::SetLutData` / `0x6a1b9`（`434,617 B`）`33^3` 3D LUT / Cine EI / 双原生 ISO（`800`/`12800`）；证实 `libInfraLensCommunicator.so` 可加载代码段 **0 字节差异**（E 卡口自动对焦 100% 原生兼容）及 DCI4K/QFHD/S&Q XAVC 录制矩阵；证实 FX3 原厂 CP 通过未改动的 `p2:/Backup.bin` + `p2:/psd.bin` + `p6:Jiritsu` Hall/Gyro PID 参数保持 **5 轴 IBIS 音圈防抖平台通电居中锁止**，彻底杜绝传感器失电下垂风险。
  - **零重分区 `p15` / DDR `tmpfs` 预算、`nflasha3-initrd` / WBI（`p5`）休眠红线、Stage-A `.ko`/ABI 闭包、`U1..U5` 清零、Stage-A 就绪包、`H0 -> H1 -> H2` 零写入审计与 12 道门禁**：锁定 `edisx_repartition_forbidden = True`、`p8_cp_mutation_forbidden = True`、`wbi_p5_write_and_hibernation_forbidden = True`、`persistent_emmc_writes_authorized = False` 与 `persistent_write_release = False`，并将 Phase 17/18 红线直接接入 `Gate G12` fail-closed 门禁。

### 主线 4 —— FX3 离线恢复适配工具（`v0.5`）与服务接口安全工具集
- **零外部依赖 `p1` 与引导分区工具链（`outputs/fx3-recovery-adapter/`）**：针对 `/dev/cnflasha1`（`p1` 恢复更新分区）与 `/dev/nflashaB0`/`B1`（`boot0`/`boot1`）提供 `inspect`、`build`、`verify`、`diagnose`、`rollback` 及无 libc 静态链接 AArch64 ELF 只读采集工作器，与主线 3 跨包桥接校验（`verify-p1-recovery-bridge`）并配套 **63 项** 单元、净室合成与故障注入测试。

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
├── .github/workflows/clean-room-ci.yml     # 无供体 Ubuntu + macOS 五套件净室 CI (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
├── Makefile                                # 统一测试 (`make test`)、BYOF、干跑、Phase 17/18、`make readiness-packet` 与 `make lifecycle-drill`
├── README.md                               # 中英双语完整主文档 (2026-11-14)
├── README.en.md                            # 独立纯英文说明文档 (2026-11-14)
├── README.zh-CN.md                         # 独立纯中文说明文档 (2026-11-14)
├── docs/
│   ├── BYOF-REPRODUCTION.md                # 净室自备固件中英双语 57+57 项 SHA-256 指纹清单与复现指南
│   └── STAGE-A-HARDWARE-RUNBOOK.md         # 中英双语 Phase H0->H1->H2 非持久 Stage-A 真机执行操作手册
├── scripts/
│   ├── run_all_lab_tests.py                # 统一五套件 224 项测试运行器 + BYOF 清单审计 + `git status --porcelain` 净室卫生审计
│   └── verify_byof_manifest.py             # 中英双语 BYOF SHA-256 语法、46 项源码常量与本地供体固件一致性审计器
├── outputs/
│   ├── fx6-on-fx3-closure/                 # Phase 18 P1..P10+Fan、U1..U5、Stage-A 编排、.ko/ABI、外设 UX、影像/IBIS、就绪包与审计器 (109 项测试)
│   ├── fx6-native-presenter-closure/       # 原版冷启动 + Round 8 FX6-on-FX3 混合态 Stage-A QEMU GPE0 闭环 (16 项测试)
│   ├── fx3-safety/                         # 12 道刷前安全门禁、Sector-0/BK4 契约与变砖分类器 (19 项测试)
│   ├── fx3-recovery-adapter/               # FX3 离线恢复适配工具 v0.5 与 AArch64 静态采集工作器 (63 项测试)
│   ├── fx3-vm-trial/                       # 交互式 FX3 与 FX6 (128 页 `live700`、22.1x C 扫描线加速) 网页模拟器与离线单测 (17 项测试)
│   └── fx3-vm/                             # FX3 最小研究 QEMU AArch64 虚拟机与高位 DDR / ESRAM 补丁
├── reports/
│   ├── 2026-11-14-fx6-on-fx3-qemu-hybrid/  # Round 8 FX6-on-FX3 Stage-A 混合态 QEMU E2E 启动 (`r8a..r8b`) 证据报告
│   ├── 2026-11-14-phase17-fx3-input-display-audio-audit/ # Phase 17 FX3 按键 (`P10`)/触控/显示路由/`XLR-H1` 音频兼容报告
│   ├── 2026-11-14-phase18-ap-cp-imaging-ibis-audit/      # Phase 18 AP<->Stock-CP 影像/3D LUT/XAVC/E卡口 AF/5轴 IBIS 报告
│   ├── 2026-11-10-fx6-p1p2p4-and-tier0/    # Phase 1–16 兼容适配、U1..U5 清零、initrd/WBI、.ko/ABI、就绪包与 12 道门禁主验证报告
│   ├── 2026-11-10-fx6-native-presenter-closure/# 原版冷启动 `nop_count=0` GPE0 Rounds 1–7 (`r1a..r7c`, 20 张 PNG 凭证) 证据报告
│   ├── 2026-11-08-fx6-native-text-gpe0/    # 100% 128 页 FX6 描述符物理 GPE0 渲染证据报告
│   └── 2026-11-03-fx6-full-system-to-fx3/  # FX6 6.01 vs FX3 7.02 30 分区与 SPI NOR 全系统静态审计
└── conversations/                          # 多智能体工程研究对话分类归档 (135 篇)
```

---

## 四、快速开始与验收命令

### 4.1 一键运行全部 224 项自动化测试、无供体净室 CI、BYOF 指纹审计、Phase 17/18、真机就绪包与全周期演练

```bash
# 运行全部 5 套测试集 (63 项 fx3-recovery-adapter + 19 项 fx3-safety + 109 项 fx6-on-fx3-closure + 17 项 fx3-vm-trial + 16 项 fx6-native-presenter-closure = 224 项) + BYOF 与净室检查
make test

# 本地模拟 GitHub Actions 无供体净室 CI 模式 (零索尼固件依赖)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-peripheral-ux && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-ap-cp-imaging && FX3_FX6_FORCE_CLEAN_ROOM=1 make lifecycle-drill

# 单独校验中英双语 docs/BYOF-REPRODUCTION.md 清单 (57+57 项镜像、46 项源码常量与可选本地固件)
make verify-byof

# 运行完整 FX6-on-FX3 离线候选包干跑验收、Stage-A 真机前就绪包与 H0->H1->H2 全生命周期沙盒演练
make dry-run
make readiness-packet
make lifecycle-drill

# 单独运行 Phase 11 跨包 p1 桥接、Phase 12 Stage-A 原子编排、Phase 14 Kmod/ABI、Phase 17 外设 UX 与 Phase 18 影像/IBIS 校验器
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
make verify-kmod-userland-abi
make verify-peripheral-ux
make verify-ap-cp-imaging
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
