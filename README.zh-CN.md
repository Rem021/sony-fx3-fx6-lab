# 索尼 FX3 与 FX6 系统移植、QEMU 虚拟机与净室兼容性研究实验室 (`sony-fx3-fx6-lab`)

[![English](https://img.shields.io/badge/Language-English-0969da?style=flat)](./README.en.md)
[![双语总览](https://img.shields.io/badge/主文档-README.md_(中英双语)-1a7f37?style=flat)](./README.md)
[![宿主平台](https://img.shields.io/badge/Host-macOS_Apple_Silicon_(MTTCG)-blue?style=flat)](#)
[![目标芯片](https://img.shields.io/badge/SoC-Sony_CXD90057_(AArch64)-orange?style=flat)](#)
[![自动化测试](https://img.shields.io/badge/Automated_Tests-271_Passing_(make_test)-brightgreen?style=flat)](#四快速开始与验收命令)
[![无供体净室CI](https://img.shields.io/badge/Clean--Room_CI-Ubuntu_%2B_macOS_(0_Donors)-0969da?style=flat)](./.github/workflows/clean-room-ci.yml)
[![开源协议](https://img.shields.io/badge/License-MIT_%2F_GPLv2_(QEMU)-656d76?style=flat)](./LICENSE)

> **语言切换**：[**👉 Switch to Standalone English Documentation (`README.en.md`)**](./README.en.md) · [**中英双语总览文档 (`README.md`)**](./README.md)

**`sony-fx3-fx6-lab`** 是面向 **Sony Cinema Line ILME-FX3（Ver. 7.02，机型 ID `0x91030080`）** 与 **ILME-FX6（Ver. 6.01，机型 ID `0x91040086`）** 数字电影摄影机的净室系统工程、QEMU AArch64 虚拟化、跨机型硬件兼容性验证与真机防变砖安全研究开源仓库。两款机型均搭载 **Sony CXD90057 AArch64 SoC**，运行 Sony CE Linux `4.9.337-scel+` 内核与 TOPPERS-FMP 1.4.0 SMP RTOS 协处理器固件（`cpapp-b.bin` `@ 0x00108000`）。

> [!IMPORTANT]
> **净室开源合规边界（BYOF：自备官方固件复现）**
> 本仓库 **包含 0 字节索尼专有闭源二进制文件**（不含 `BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`cpapp-b.bin`、`nflasha*` 分区镜像或 `.cpio` 根文件系统镜像）。仓库内全部 Python 离线校验器、无依赖 AArch64 C/汇编工作器、Unicorn 指令级仿真套件、QEMU 设备补丁、Web 交互前端与 SHA-256 验收回执均为独立净室编写，并通过 `.github/workflows/clean-room-ci.yml` 在 `ubuntu-latest` + `macos-latest` 无供体环境下自动门禁验证。如需在本地复现虚拟机交互体验，请参照 **[docs/BYOF-REPRODUCTION.md](docs/BYOF-REPRODUCTION.md)**（由 `make verify-byof` 自动守护指纹一致性）自备对应 SHA-256 指纹的官方固件。

---

## 一、核心工程里程碑（截至 2026-11-14）

### 主线 1A —— FX6 128 页 Guest `GPE0` 实时互动 UI、Phase 19 原生图标渲染与 `60/60` 连击零死机修复
- **Phase 19 索尼 FX6 原生精灵图标（`image_00_169.uxc`）解码渲染与 `60/60` 多连击零崩溃根治**：只读注入 `image_00_169.uxc` 并建立 LDEC 合法 `/dev/mem` GPE 物理内存池（`0x410524000..0x410e64000`）与 `RGBA4444`/`RGBA8888`/`A8`/`ARGB4444` 混合器；拦截 `liblibra.so` 异步工作线程 `_ZN5libra20GenerateImageCommand6notifyEb`（`0x2a238`）、将静态单槽控件缓冲升级为 32 槽对齐环形池并串行化 GDB `finally` `$c#63` 恢复，顺利通过 **60/60 跨页快速连击压测（`0 APPFW_SEGV`，单页最高 `icon_n=119`，平均 `179.3 ms`/次，详见 [Phase 19 报告](reports/2026-11-14-phase19-live-icon-rendering/README.md)）**。
- **100% 全量 128 页原生描述符物理帧缓冲渲染、22.1 倍 C 扫描线打包器与 20 项离线单测**：将全部 **128 张页面描述符表**（`2,249` 行控件）真实渲染进物理帧缓冲 `0x41e001000`（`GPE0`，`1024×540` RGBA32，`segv = 0`），配套 `fx6_pack_scanlines`（**22.1 倍**加速）、[`build_live700.py`](outputs/fx3-vm-trial/build_live700.py) 与 **20 项**双模式单测（[`test_vm_trial.py`](outputs/fx3-vm-trial/tests/test_vm_trial.py)）。

### 主线 1B —— FX6 原版冷启动 + Round 8 / Round 9 FX6-on-FX3 混合态 QEMU 端到端闭环（`r1a..r9d`，26 张 PNG 凭证，20 项单测）
- **零指令 NOP 原版冷启动与全栈 Presenter 闭环（`r1a..r7c`）**：交付 [`outputs/fx6-native-presenter-closure/`](outputs/fx6-native-presenter-closure/) 与 [`reports/2026-11-10-fx6-native-presenter-closure/README.md`](reports/2026-11-10-fx6-native-presenter-closure/README.md)，在 **`FX6_NATIVE_FAITHFUL=1`**（`nop_count = 0`、`subst_* = 0`）下跑通全生命周期冷启动与交互导航。
- **Round 8（Stage-A）与 Round 9（Stage-B `P10`）FX6-on-FX3 真实内核闭环（`r8a..r9d`）**：直接使用 **FX3 7.02 原厂内核 `vmlinux.bin`**（`4.9.337-scel+`）+ FX3 `cxd90057.dtb` 启动（[Round 8 报告](reports/2026-11-14-fx6-on-fx3-qemu-hybrid/README.md)、[Round 9 报告](reports/2026-11-14-round9-fx6-on-fx3-p10-presenter/README.md)），Guest 内完成 **11/11** Stage-B SHA-256 原子校验（`P10` 内存读回 `ok=1`），经 `SRM3KYE5 -> InfraInput` 注入 FX3 机身 `Fn`/`C1`/`C2`/`MENU`/`ENTER` 按键流，跑通 **`r9a` 拍摄主屏 HUD**（`sid=0x02`）、**`r9b` Big6 主屏**（`sid=0x0a`）、**`r9c` Big6 参数子窗**（`sid=0x0c`，含 `2,035` 个琥珀色 `0xffffaa00` 高亮像素）与 **`r9d` 全量菜单第 2 层**（`sid=0x10`，`434,010` 像素，`87` 色）。

### 主线 2 —— FX3 原生固件 QEMU 虚拟机与浏览器交互菜单模拟器
- **零修改启动 FX3 7.02 内核与原厂菜单（`outputs/fx3-vm/`、`outputs/fx3-vm-trial/`）**：完整建模 CXD90057 高位 DDR（`0x400000000`）、ESRAM 邮箱（`0xfe005000`）、GICD、Sony 硬件定时器、SCU、GPIO Bank5、UIPC、DMM、GPE v13/v14 与软件 LDEC LZ77 图标解压，提供一键启动的浏览器交互入口 `FX3菜单.command`（支持 4096 键 / 60 分钟交互预算，约 40.1 秒出首帧待机 OSD，已完成 32 键逐屏导航与 API16 干净恢复验收）。

### 主线 3 —— FX6-on-FX3 Phase 21 全栈兼容闭环（`P1..P11 + Fan`、`U1..U5`、Stage-B `P10`、`P11` UIPC-CP 垫片、5 轴防抖与 12 道门禁）
- **受控工程包**：[`outputs/fx6-on-fx3-closure/`](outputs/fx6-on-fx3-closure/README.md)、[`docs/STAGE-A-HARDWARE-RUNBOOK.md`](docs/STAGE-A-HARDWARE-RUNBOOK.md) 与 [`outputs/fx3-safety/`](outputs/fx3-safety/)（详见 [Phase 1–16 主报告](reports/2026-11-10-fx6-p1p2p4-and-tier0/README.md)、[Phase 17 报告](reports/2026-11-14-phase17-fx3-input-display-audio-audit/README.md)、[Phase 18 报告](reports/2026-11-14-phase18-ap-cp-imaging-ibis-audit/README.md)、[Phase 20 Stage-B 报告](reports/2026-11-14-phase20-p10-stage-b-integration/README.md)、[Phase 21 `P11` 垫片报告](reports/2026-11-14-phase21-uipc-cp-shim-closure/README.md)）：
  - **Phase 17 & Phase 20 Stage-B 联合 `appFw.so` 与机身按键/触控/音视频闭环（`make verify-peripheral-ux` & `make verify-stage-b-p10`）**：将 24 字节 `.rodata` `P10` 键值翻译表与 `P1+P4+P8` 零重叠合并为 Stage-B `appFw.so`（10 处共 41 B，SHA-256 `e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4`，100% 无损回滚 + 21 键 Unicorn 实测），解锁 FX3 机身 `Fn -> Big6 HOME`、`C1..C3`、`PLAY`、`DELETE`，并验证 `1024×540` 触控、LCD/HDMI OSD 路由与 `XLR-H1` 热靴音频兼容。
  - **Phase 18 & Phase 21 `P11` AP↔Stock-CP UIPC 垫片、3D LUT / Cine EI / 双原生 ISO 与 5 轴 IBIS 防抖锁止闭环（`make verify-ap-cp-imaging` & `make verify-uipc-cp-shim`）**：证实 FX3 7.02 原厂 CP 原生实现 `0x92840747` 上 **全部 44 个 UIPC BB 操作码**，并在 Unicorn 下验证可执行 `P11` AP 垫片（`0x92d2091c` `/dev/rtc0->udate` 解除 `std::promise` 死锁与 `0x91db059b` 侧手柄离线应答且保留 `XLR-H1`、`developing_mode_FHD -> 0x92840747`、`0x0165`/`0x0166` `33^3` 3D LUT DMA、双原生 ISO `800`/`12800`、E 卡口 AF `0 B` 差异，以及 **FX3 5 轴 IBIS 音圈防抖平台通电居中锁止**）。
  - **零重分区预算、WBI/CP 红线、`U1..U5` 清零、Stage-A 就绪包、`H0 -> H1 -> H2` 零写入审计与 12 道门禁**：锁定 `edisx_repartition_forbidden = True`、`p8_cp_mutation_forbidden = True`、`wbi_p5_write_and_hibernation_forbidden = True`、`persistent_emmc_writes_authorized = False` 与 `persistent_write_release = False`。

### 主线 4 —— FX3 离线恢复适配工具（`v0.5`）、全球救砖情报同步与服务接口安全工具集
- **零外部依赖 `p1` 工具链与全球情报卷宗（`outputs/fx3-recovery-adapter/`、[全球情报报告](reports/2026-11-14-global-sony-firmware-vm-unbrick-intel/README.md)）**：针对 `/dev/cnflasha1`（`p1` 恢复更新分区）与 `/dev/nflashaB0`/`B1`（`boot0`/`boot1`）提供 `inspect`、`build`、`verify`、`diagnose`、`rollback` 及无 libc 静态 AArch64 ELF 只读采集工作器，同步对齐 2025–2026 全球索尼 BIONZ XR 固件逆向（`ALCIN_UUD`、Multi-port `48000` 波特率 BootROM `uart_boot -> 0x92028000` 硬件救砖与 WF-12 无线故障非阻塞隔离），配套 **63 项**测试。

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
├── Makefile                                # 统一测试 (`make test`)、BYOF、干跑、Phase 17..21、`make readiness-packet` 与 `make lifecycle-drill`
├── README.md                               # 中英双语完整主文档 (2026-11-14)
├── README.en.md                            # 独立纯英文说明文档 (2026-11-14)
├── README.zh-CN.md                         # 独立纯中文说明文档 (2026-11-14)
├── docs/
│   ├── BYOF-REPRODUCTION.md                # 净室自备固件中英双语 57+57 项 SHA-256 指纹清单与复现指南
│   └── STAGE-A-HARDWARE-RUNBOOK.md         # 中英双语 Phase H0->H1->H2 非持久 Stage-A 真机执行操作手册
├── scripts/
│   ├── run_all_lab_tests.py                # 统一五套件 271 项测试运行器 + BYOF 清单审计 + `git status --porcelain` 净室卫生审计
│   └── verify_byof_manifest.py             # 中英双语 BYOF SHA-256 语法、46 项源码常量与本地供体固件一致性审计器
├── outputs/
│   ├── fx6-on-fx3-closure/                 # Phase 21 P1..P11+Fan、U1..U5、Stage-A/B、.ko/ABI、外设 UX、影像/UIPC-CP/IBIS、就绪包与审计器 (149 项测试)
│   ├── fx6-native-presenter-closure/       # 原版冷启动 + Round 8 (Stage-A) & Round 9 (Stage-B `P10`) 混合态 QEMU GPE0 闭环 (20 项测试)
│   ├── fx3-safety/                         # 12 道刷前安全门禁、Sector-0/BK4 契约与变砖分类器 (19 项测试)
│   ├── fx3-recovery-adapter/               # FX3 离线恢复适配工具 v0.5 与 AArch64 静态采集工作器 (63 项测试)
│   ├── fx3-vm-trial/                       # 交互式 FX3 与 FX6 (Phase 19 原生图标 `image_00_169.uxc`、`60/60` 连击零死机) 网页模拟器 (20 项测试)
│   └── fx3-vm/                             # FX3 最小研究 QEMU AArch64 虚拟机与高位 DDR / ESRAM 补丁
├── reports/
│   ├── 2026-11-14-phase19-live-icon-rendering/         # Phase 19 实时 FX6 原生图标渲染 + 60/60 连击零崩溃修复报告
│   ├── 2026-11-14-phase20-p10-stage-b-integration/     # Phase 20 Stage-B 联合 `appFw.so` (`P1+P4+P8+P10`) 与 21 键 Unicorn 报告
│   ├── 2026-11-14-phase21-uipc-cp-shim-closure/        # Phase 21 `P11` UIPC-CP 垫片 (`0x92d2091c`/`0x91db059b`)、LUT DMA 与 IBIS 报告
│   ├── 2026-11-14-round9-fx6-on-fx3-p10-presenter/     # Round 9 FX6-on-FX3 Stage-B `P10` 多场景 QEMU Presenter (`r9a..r9d`) 报告
│   ├── 2026-11-14-global-sony-firmware-vm-unbrick-intel/ # 2025-2026 全球索尼固件逆向、QEMU/IVSHMEM 与 Multi-port BootROM 救砖情报卷宗
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

### 4.1 一键运行全部 271 项自动化测试、无供体净室 CI、BYOF 指纹审计、Phase 17..21、真机就绪包与全周期演练

```bash
# 运行全部 5 套测试集 (63 项 fx3-recovery-adapter + 19 项 fx3-safety + 149 项 fx6-on-fx3-closure + 20 项 fx3-vm-trial + 20 项 fx6-native-presenter-closure = 271 项) + BYOF 与净室检查
make test

# 本地模拟 GitHub Actions 无供体净室 CI 模式 (零索尼固件依赖)
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-byof && FX3_FX6_FORCE_CLEAN_ROOM=1 make test && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-peripheral-ux && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-ap-cp-imaging && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-stage-b-p10 && FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-uipc-cp-shim && FX3_FX6_FORCE_CLEAN_ROOM=1 make lifecycle-drill

# 单独校验中英双语 docs/BYOF-REPRODUCTION.md 清单 (57+57 项镜像、46 项源码常量与可选本地固件)
make verify-byof

# 运行完整 FX6-on-FX3 离线候选包干跑验收、Stage-A 真机前就绪包与 H0->H1->H2 全生命周期沙盒演练
make dry-run
make readiness-packet
make lifecycle-drill

# 单独运行 Phase 11 跨包 p1 桥接、Phase 12 Stage-A 原子编排、Phase 14 Kmod/ABI 及 Phase 17..21 专项校验器
make verify-p1-recovery-bridge
make verify-stage-a-orchestrator
make verify-kmod-userland-abi
make verify-peripheral-ux
make verify-ap-cp-imaging
make verify-stage-b-p10
make verify-uipc-cp-shim
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
