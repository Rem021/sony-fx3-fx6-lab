# FX5 交互逻辑 + FX6 完整色彩目标：经典 FX3 7.02 菜单/控制适配设计与受限包构造实验（V2 勘误与复核版）

> [!WARNING]
> **V1 过度结论撤回与勘误声明（V1 原文已归档保留于 [`README-v1-superseded.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/README-v1-superseded.md)，旧版脚本与 JSON 原样保留）**：
> 1. **撤回“AP 到 70 描述符 DMA 完整闭环 / 跨核通信成功 / 落盘”表述**：本目录脚本仅在 Unicorn 中分段执行了 **AP 栈上包构造片断**（`0x2e3172c->0x2e26fcc`、`0x2debdb0`、`0x2dee4ac`、`0x2e3c3b8->0x2e18e3c`）与 **CP 接收写入/检查/门控片断**（`0x791f9c`、`0x2fe05c`、`0x2d38a8`、`0x79150c`、`0x3c9162`）。中间的日志与 IPC 发送调用均被替换为 `mov w0, #0`（`00008052`），且 AP 到 CP 的报文传递是由 **Python 宿主手动从 AP 模拟栈复制到 CP 模拟 RAM**，**并未执行跨核 IPC 硬件传输，未在本脚本中重放 `0x470f78` (`mlut_make_lli_table`) DMA 链表生成，更未写入非易失闪存（仅写模拟 RAM `0x10a8de0`，不能称“落盘”）**。
> 2. **补齐固定摘要绑定、地址映射证明、指令预算/终止 PC/哨兵断言与负例反证**：V1 的 [`verify_menu_backend_chains.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains.py) 只计算 SHA256 而未断言固定期望值，也未检查指令预算耗尽或错误输入反例。V2 脚本 [`verify_menu_backend_chains_v2.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains_v2.py) 已强制绑定输入二进制 SHA256/字节数、证明 ELF `PT_LOAD` 与 CP `0x108000` 基址映射、断言 `steps < budget` 与返回哨兵 PC、校验目标结构体前后 `0xdeadbeef`/`0xcafebabe` 哨兵不越界，并实测正例与非法输入反例（退出码 `0`）。同时纠正了 V1 正文中将 WB `+0xe` 余数 `0x01f4` (`500`) 误抄为 `0x05dc` (`1500`) 的笔误及将 `0x1cb8a8` 门控混入 `0x1f605c` 检查器的归类错误。
> 3. **撤回 V1 中错误的“`33³` / `149,888B` (`160+3×1984+143748+36`)” MLUT 布局描述**：V1 算式 `160 + 3×1984 + 143748 + 36 = 149,896 ≠ 149,888` 存在算术错误，且把未经核实的硬编码字符串当成 FX3 Look ID 22 的结构。经逐项绑定项目既有逆向回执（[`initializer-guest-results.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/initializer-guest-results.json)、[`extraction-results.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/extraction-results.json)、[`cp-mlut-dma-results.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/resource-20261028/cp-mlut-dma-results.json)），FX3 7.02 的 Look ID 22 (`MLUT_LOOKNAME_SL3SG3_TO_ACESREC709`) 在 [`av-cam.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin) (`0xffffffc001b05638`) 中为 **70 条 × 152 字节描述符（`10,640B`）**，其 3D LUT 为 **24 个 SRAM bank（`20×20×20 = 8,000` 节点、`24,000` 通道值、`48,000B`）**；在 [`cpapp-b.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin) (`0x02015794`) 中为 **70 条 × 140 字节描述符（`9,800B`）**。由于本脚本未重放 `0x470f78` DMA 构造，下游 DMA 与描述符初始化在本文中降级为**既有回执引用（待与新菜单控制联调验证）**。
> 4. **撤回“可将 1K 色温余量折算进 AB/GM 余数字段实现 Fine 1K”的定论，降级为未证实假设**：虽然 `appFw.so` `0x2e18e98` 确实将开尔文色温除以 `100` 写入单字节 `+0x10`（CP `0x10a8de0+0xa00`），但 V2 新增对 CP 下游复制片断 `VA 0x3c9162..0x3c91ba` (`file+0x2c1162..0x2c11ba`) 的静态与 Unicorn 验证证实：**CP 将 `+0xa00`（100K 色温字节）复制到 `[r0+0xfc]`，将 `+0x9f8..+0x9fc`（AB/GM 商与余数）复制到 `[r0+0xf4..0xf8]`，二者在下游结构体中保持物理分离**。在未逆向出最终白平衡 R/G/B 增益求解器并证明其输入域量纲之前，折算方案仅属**未证实假设**，严禁实施未经标定的映射。
> 5. **区分 AP 运行态 RAM (`0x821c538`) 与非易失持久化（Backup/CAMSET）**：ELF `PT_LOAD[1]` 头证明 `0x821c538` 位于未由文件背书的运行态 BSS RAM 段（`p_vaddr=0x3d20000`, `p_filesz=0xe4a730`, `p_memsz=0x5d1b648`），**绝不等于非易失持久化存储**。`base_look=12` 及 8 组白平衡记忆槽 `A..H` 的接入在未打通 Backup 保存链路前均标为**未验证概念方案**。
> 6. **修正过时的 VM 现状描述**：V1 声称“VM 仅启动 Linux 壳层无 GUI”已过时。根据 [`ap103-software-ldec-and-native-save.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/ap103-software-ldec-and-native-save.md) 与 [`ap105-offline-preparation.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/ap105-offline-preparation.md)，**AP103-r2 已通过软件 `/dev/ldec` 在 QEMU 中跑通完整图形界面（待机 → `MENU` → `Setup` → 语言弹窗）**，**AP105（替换 GPE 性能件候选）已完成离线准备、待执行运行与原生保存验收**；但 VM 仍只运行 AP Linux，**无真实 CP RTOS 与硬件 ISP 执行环境**。
> 7. **严格分离 Sony FX5 与 FX6 官方规格来源，移除 `fx6-prefix-curl.bin` 作为 BIG6/菜单证据**：Sony FX5 (`ILME-FX5`, Help Guide `2630 v1`) 九个 HTML 页面由本脚本直接 `HTTP 200` 拉取并提取具体段落；Sony FX6 (`ILME-FX6V` Ver. 6.01 `00259043`) 因 Akamai `HTTP 403` 拦截，仅作为受限外部搜索摘要单独列出，且绝不拿 64KB 二进制固件前缀 `fx6-prefix-curl.bin` 充当菜单或 BIG6 能力证据。

---

## 1. 先说结论（V2 逐项接受/已验 vs 待验/未完成边界）

| 评估维度 | V2 已证实的精确结论（含证据层级） | 尚未验证 / 严禁夸大的边界 |
|---|---|---|
| **1. 环境与输入原件绑定** | 卷 `UUID = F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 校验通过；[`verify_menu_backend_chains_v2.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains_v2.py) 强制校验 [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so)（`79,015,712B`, SHA256 `545c5053...290f`）、[`cpapp-b.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin)（`15,980,568B`, SHA256 `c90d00d8...bcba`）、[`av-cam.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin)（`13,348,560B`, SHA256 `0cb7e03a...bdaf`），不匹配即报错退出。 | 未改动任何原件、未触碰 VM/运行锁/USB/相机。 |
| **2. 地址映射静态证明** | **[STATIC]** `appFw.so` 的 `PT_LOAD[0]`（`vaddr=0x0, offset=0x0, filesz=0x3d0f79d`）覆盖本报告全部代码与只读表地址（`0x2c47cfc..0x3975a78`），证明 **VA 与文件偏移 1:1 恒等**；`cpapp-b.bin` 首指令 `file+0x0: e59f1004 (ldr r1, [pc, #4])` 读取 `file+0x0c` 处字面量 `0x0010800c`，证明 **`VA = file_offset + 0x108000`**。 | `0x821c538` 位于 `appFw.so` `PT_LOAD[1]` 的 BSS 段（`vaddr=0x3d20000`, `filesz=0xe4a730`, `memsz=0x5d1b648`），仅是运行态 RAM，无文件偏移，更非 Flash 持久化区。 |
| **3. 受限包构造与 CP RAM 写入实验** | **[CPU-EMU 受限分段]** 在显式记录全部 30 处 stub 的前提下，通过正例与负例反证验证了：<br>① AP `0x2e3172c->0x2e26fcc`（构造 16B `0x4151` 包，正例 `w2=1` 输出 `05005141000000000702010100000000`，反例 `w2=9>3` 命中错误分支 `0x2e270dc`）；<br>② 宿主手动送包至 CP `0x791f9c`（写模拟 RAM `0x10a8de0+0xba0..0xbb0` 与 `+0x76c`）、CP 检查器 `0x2fe05c`（证实仅比对并打日志，不拒绝 `base_look=12`）与 CP 采集字段构建函数 `0x2d38a8`（`file+0x1cb8a8`，证实 `base_look=7` 保留在 `[r4+0x794]=7`，而反例 `base_look=12` 被 `0x2d38b8: 0c29 cmp r1, #0xc` 拦截并在 `0x2d38ec` 重置为 `0`）；<br>③ AP BB/VDF `0x2debdb0`（MonitorLUT `0x0161`，反例 `9>4` 命中 `0x2debe74`）与 `0x2dee4ac`（ColorGamut `0x0167`，反例 `5` 命中 `0x2dee4ec` 零发包早退）；<br>④ AP `0x2e3c3b8->0x2e18e3c`（构造 20B `0x4006` WB 包，正例输出 `050006400100000009020100f401f40138000100`，反例 `mode=21>15` 命中 `0x2e18ff4`）及 CP `0x79150c` → 下游复制器 `0x3c9162`。 | **未执行真实 IPC 传输**（由宿主手动拷包）、**未在本脚本中执行 `0x470f78` DMA 构造**、**未验证非易失保存**、**未验证白平衡最终 R/G/B 增益求解器**。 |
| **4. FX5 交互规范 vs FX6 6.01 BIG6 映射** | **[DOC 区分来源]** FX5 (`ILME-FX5`, `2630 v1`) 的 `HOME screen`（6 柱：FPS / ISO-Gain-EI / Shutter / Iris / SceneFile-Look / WB）、`Quick Menu`（短按 `MENU`，5 页签 `Project`/`TC-Media`/`Monitoring`/`Audio`/`Info`，第 6 槽跳 Full Menu）、`Full Menu`（长按 `MENU`，10 分类，8 行视口，`-99..+99` 行内直调，`BACK` 撤销，`[Execute]` 确认弹窗）有 `HTTP 200` 原始 HTML 段落支撑。 | FX6 6.01 (`00259043`) 直接请求返回 `HTTP 403`，仅保留外部搜索摘要；FX3 物理上**无内置电子 ND、无 SDI、无专用 EVF、无独立 BNC TC Out**，禁止伪造这些硬件功能。 |

---

## 2. 本目录文件清单（保留全部 V1 文件，新增 V2 勘误与核验产物）

| 文件路径 | 版本 | 说明 | 大小 / SHA256 |
|---|---|---|---|
| [`README.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/README.md) | **V2（当前主报告）** | 醒目列出 V1 勘误与撤回声明，给出完整 stub 表、地址证明、正反例实验、70 描述符精确绑定与 FX5/FX6 分离映射 | 见磁盘 |
| [`verify_menu_backend_chains_v2.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains_v2.py) | **V2 脚本** | 固定 SHA256 断言、ELF/CP 地址映射证明、完整 stub 字节比对、指令预算/终止 PC/哨兵检查、正反例 Unicorn 套件 | 退出码 `0` |
| [`verification-receipt-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verification-receipt-v2.json) | **V2 回执** | 记录 V2 脚本退出码 (`0`)、断言通过状态及各正/反例实际执行指令步数 | `646B` (`de68d1ea...7fb1`) |
| [`static-chain-evidence-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/static-chain-evidence-v2.json) | **V2 证据** | 含 ELF `PT_LOAD` 与 CP `0x108000` 证明、30 处 stub 替换前后字节、三套正反例模拟详情及 Look 22 70 描述符对象绑定 | `27,963B` (`21e9004b...779d`) |
| [`menu-control-mapping-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/menu-control-mapping-v2.json) | **V2 映射** | 含 V1 七条勘误、FX5 vs FX6 分离页面段落引用、AP103/AP105 VM 现状与 BIG6 控制映射修正 | `6,555B` (`143c7e7a...4ff5`) |
| [`online-sources-receipt-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/online-sources-receipt-v2.json) | **V2 联网回执** | 9 份 FX5 Help Guide (`HTTP 200`) 提取出的原始 `<h2>/<h3>/<dt>/<strong>` 章节条目 + FX6 `00259043` (`HTTP 403`) 边界说明 | `16,045B` (`c949d550...96b0`) |
| [`README-v1-superseded.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/README-v1-superseded.md) | V1 归档 | 保留 V1 原始报告供对照审计（内含已撤回的过度表述） | 保留原件 |
| [`verify_menu_backend_chains.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains.py) / `*.json` | V1 归档 | 保留 V1 原始脚本与三份 V1 JSON（`online-sources-receipt.json`、`static-chain-evidence.json`、`menu-control-mapping.json`） | 保留原件 |

---

## 3. 原件摘要绑定与 VA → 文件偏移静态映射证明（Audit Point 2）

### 3.1 固定输入二进制摘要绑定
[`verify_menu_backend_chains_v2.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains_v2.py) 中的 `verify_and_bind_input_binaries()` 对以下三个只读固件镜像执行硬性 `assert`，任何字节数或 SHA256 偏差均直接抛错终止：

1. [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so)：`size = 79,015,712` bytes，SHA256 = `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`
2. [`cpapp-b.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin)：`size = 15,980,568` bytes，SHA256 = `c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba`
3. [`av-cam.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin)：`size = 13,348,560` bytes，SHA256 = `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf`

### 3.2 `appFw.so` ELF64 `PT_LOAD` 映射证明与 `0x821c538` BSS 属性证明
解析 `appFw.so` ELF64 Program Headers（`e_phoff = 0x40`, `e_phnum = 9`）得到仅有的两个 `PT_LOAD` 段：

| 段序号 | `p_offset` | `p_vaddr` | `p_filesz` | `p_memsz` | `VA - file_offset` 差值 | 覆盖范围与结论 |
|---|---|---|---|---|---|---|
| `PT_LOAD[0]` | `0x0` | `0x0` | `0x3d0f79d` | `0x3d0f79d` | **`0x0`（恒等映射）** | 覆盖 `0x0 .. 0x3d0f79d`。本报告分析的全部代码与只读查表地址（`0x2c47cfc..0x3975a78`）均落在此段内，**因此 ELF VA 与文件偏移严格相等**。 |
| `PT_LOAD[1]` | `0x3d10000` | `0x3d20000` | `0x0e4a730` | `0x5d1b648` | **`+0x10000`**（文件背书区 `0x3d20000..0x4b6a730`） | GOT/虚表（如 `0x46dd608`、`0x47369f0`、`0x47afd48`）位于文件背书区（`file_offset = VA - 0x10000`）；而 **`0x821c538` 落在 `0x4b6a730 .. 0x9a3b648` 的无文件背书 BSS 段内**，证明 `0x821c538` 纯属 AP 进程运行态 RAM，绝非持久化槽位（Audit Point 5）。 |

### 3.3 `cpapp-b.bin` 加载基址 `VA = file_offset + 0x108000` 自定位字面量证明
`cpapp-b.bin` 是无 ELF 头的 ARM32/Thumb 平坦 RTOS 镜像。读取文件首 16 字节（`file+0x0..0x0f`）：
- `file+0x00`: `04109fe5` → `ldr r1, [pc, #4]`（ARM 模式下 `PC = 当前指令 + 8 = file+0x08`，故读取 `file+0x0c` 处的 32 位字）
- `file+0x04`: `041081e2` → `add r1, r1, #4`
- `file+0x08`: `01f0a0e1` → `mov pc, r1`（跳转至紧随字面量之后的 `file+0x10` 处指令 `d300a0e3 mov r0, #0xd3`）
- `file+0x0c`: **`0c801000`**（小端 32 位值 **`0x0010800c`**）

由于 `file+0x0c` 处存储的自身运行态目标地址为 `0x0010800c`（加 4 后跳入 `0x00108010` 对应 `file+0x10`），直接证明 **`cpapp-b.bin` 的运行态基址为 `0x0010800c - 0x0c = 0x108000`**，即 **`VA = file_offset + 0x108000`**。

---

## 4. 受限 Unicorn 实验的真实边界、全量 Stub 清单与正反例复现（Audit Points 1 & 2）

### 4.1 原码执行 vs 宿主输入 vs 人工衔接边界声明
在 [`verify_menu_backend_chains_v2.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains_v2.py) 中，每一项实验均严格拆分为三部分：
1. **未修改的原厂指令（Original Code）**：
   - AP 端：`0x2e3172c..0x2e317b0` 外层封包与 `0x2e26fcc..0x2e27168` (`set_base_picture_setting_i`) 分支查表；`0x2debdb0..0x2debe74` (`vdf_disp_set_monitor_lut`)；`0x2dee4ac..0x2dee538` (`ColorGamut`)；`0x2e3c3b8..0x2e3c444` 外层封包与 `0x2e18e3c..0x2e190a8` (`PID_SET_WB_MODE` 载荷构造与 `/1000`、`/100` 有符号除法量化)。
   - CP 端：`file+0x689f9c` (`VA 0x791f9c`, `0x4151` 写入器)、`file+0x1f605c` (`VA 0x2fe05c`, `CheckSetParamBasePictureSetting` 一致性检查器)、`file+0x1cb8a8` (`VA 0x2d38a8`, 采集状态字段构建与 `cmp r1, #0xc` 门控)、`file+0x68950c` (`VA 0x79150c`, `0x4006` WB 写入器)、`file+0x2c1162..0x2c11ba` (`VA 0x3c9162..0x3c91ba`, WB 下游结构体复制器)。
2. **宿主合成输入（Host Synthetic Inputs）**：
   - 栈指针 `SP`、返回哨兵地址 `LR`、输入参数结构体内存（如 AP 8 词/6 词输入、CP 状态块初值）及结构体前后 `0xdeadbeef` / `0xcafebabe` 越界检测哨兵均由 Python 宿主在模拟 RAM 中显式构造。
3. **打桩替换与人工衔接（Stubs & Host Manual Handoff）**：
   - 下表列出的全部外部日志、断言与 IPC 发送函数调用（`bl`）在模拟 RAM 中被改写为 `mov w0, #0`（ARM64 字节 `00008052`）或 `nop; nop`（Thumb 字节 `00bf00bf`）。
   - AP 构造出的 16 字节（`0x4151`）或 20 字节（`0x4006`）报文由宿主在 `UC_HOOK_CODE` 命打桩点时从 AP 模拟栈读取，并**由宿主手动写入 CP 模拟 RAM `0x20001000` 作为 `r0` 入参**。

### 4.2 全量 Stub 替换前后字节对照表（共 30 处，完整机器可读记录见 [`static-chain-evidence-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/static-chain-evidence-v2.json)）

| 镜像 | 架构 | VA (`file_offset`) | 原始字节 | 原始反汇编 | 替换字节 | 替换后反汇编 | 打桩原因与边界说明 |
|---|---|---|---|---|---|---|---|
| `appFw.so` | ARM64 | `0x2e31780` (`0x2e31780`) | `a8f10494` | `bl #0x2f6de20` | `00008052` | `mov w0, #0` | 跳过 `0x4151` 发送前调试日志调用 |
| `appFw.so` | ARM64 | `0x2e317a0` (`0x2e317a0`) | `fcf8ff97` | `bl #0x2e2fb90` | `00008052` | `mov w0, #0` | 跳过 `0x90030001` IPC 底层发送；宿主在此 PC 读取 `x1` 指向的 16B 栈包 |
| `appFw.so` | ARM64 | `0x2e27104` (`0x2e27104`) | `4e230594` | `bl #0x2f6fe3c` | `00008052` | `mov w0, #0` | `0x2e26fcc` 非法输入错误分支日志辅助 1 |
| `appFw.so` | ARM64 | `0x2e27114` (`0x2e27114`) | `4a230594` | `bl #0x2f6fe3c` | `00008052` | `mov w0, #0` | `0x2e26fcc` 非法输入错误分支日志辅助 2 |
| `appFw.so` | ARM64 | `0x2e27124` (`0x2e27124`) | `49130594` | `bl #0x2f6be48` | `00008052` | `mov w0, #0` | `0x2e26fcc` 非法输入错误分支日志辅助 3 |
| `appFw.so` | ARM64 | `0x2e27130` (`0x2e27130`) | `46130594` | `bl #0x2f6be48` | `00008052` | `mov w0, #0` | `0x2e26fcc` 非法输入错误分支日志辅助 4 |
| `appFw.so` | ARM64 | `0x2e27144` (`0x2e27144`) | `9fad9d97` | `bl #0x15927c0` | `00008052` | `mov w0, #0` | `0x2e26fcc` 非法输入错误分支打印 1 |
| `appFw.so` | ARM64 | `0x2e27154` (`0x2e27154`) | `9bad9d97` | `bl #0x15927c0` | `00008052` | `mov w0, #0` | `0x2e26fcc` 非法输入错误分支打印 2 |
| `appFw.so` | ARM64 | `0x2e27160` (`0x2e27160`) | `58af9d97` | `bl #0x1592ec0` | `00008052` | `mov w0, #0` | `0x2e26fcc` 非法输入错误分支延时/通知 |
| `appFw.so` | ARM64 | `0x2e27164` (`0x2e27164`) | `93600294` | `bl #0x2ebf3b0` | `00008052` | `mov w0, #0` | `0x2e26fcc` 非法输入错误分支断言处理 |
| `appFw.so` | ARM64 | `0x2debe38` (`0x2debe38`) | `9cecff97` | `bl #0x2de70a8` | `00008052` | `mov w0, #0` | 跳过 MonitorLUT `0x92840747` BB 发送；宿主在此 PC 捕获 10B 栈包 |
| `appFw.so` | ARM64 | `0x2debe40` (`0x2debe40`) | `cde1ff97` | `bl #0x2de4574` | `00008052` | `mov w0, #0` | 跳过 MonitorLUT 状态码映射调用 |
| `appFw.so` | ARM64 | `0x2dee528` (`0x2dee528`) | `e0e2ff97` | `bl #0x2de70a8` | `00008052` | `mov w0, #0` | 跳过 ColorGamut `0x92840747` BB 发送；宿主在此 PC 捕获 10B 栈包 |
| `appFw.so` | ARM64 | `0x2dee530` (`0x2dee530`) | `11d8ff97` | `bl #0x2de4574` | `00008052` | `mov w0, #0` | 跳过 ColorGamut 状态码映射调用 |
| `appFw.so` | ARM64 | `0x2e3c414` (`0x2e3c414`) | `83c60494` | `bl #0x2f6de20` | `00008052` | `mov w0, #0` | 跳过 `0x4006` WB 发送前调试日志调用 |
| `appFw.so` | ARM64 | `0x2e3c434` (`0x2e3c434`) | `d7cdff97` | `bl #0x2e2fb90` | `00008052` | `mov w0, #0` | 跳过 `0x90030001` IPC 底层发送；宿主在此 PC 读取 `x1` 指向的 20B 栈包 |
| `appFw.so` | ARM64 | `0x2e1901c..0x2e1907c` (8 处) | 见 JSON | `bl #0x2f6fe3c` 等 | `00008052` | `mov w0, #0` | `0x2e18e3c` 非法白平衡模式（`w0 > 0xf`）错误分支中的 8 处外部日志/断言调用 |
| `cpapp-b.bin` | Thumb | `0x2fe086`, `0x2fe09e`, `0x2fe0b6`, `0x2fe0ce` (`file+0x1f6086..0x1f60ce`) | `e8f2fdf2` 等 | `bl #0x9e6684` | `00bf00bf` | `nop; nop` | 跳过 `CheckSetParamBasePictureSetting` 字段不一致时的 UART/日志打印 |
| `cpapp-b.bin` | Thumb | `0x2fe0f4` (`file+0x1f60f4`) | `e8f2c6b2` | `b.w #0x9e6684` | `704700bf` | `bx lr; nop` | 将 `+0xbb0` 不一致分支末尾的日志尾调用替换为返回 |
| `cpapp-b.bin` | Thumb | `0x2d38e6` (`file+0x1cb8e6`) | `12f3cdf6` | `bl #0x9e6684` | `00bf00bf` | `nop; nop` | 跳过 `0x1cb8a8` 在 `base_look >= 12` 时的错误日志打印，保留紧随其后的 `movs r0,#0; str.w r0,[r4,#0x794]` |

### 4.3 正例与负例（错误输入反例）实测汇总表
所有用例均通过 `steps_executed < budget`、`final_pc == expected_return_pc` 及前后 `0xdeadbeef`/`0xcafebabe` 哨兵断言（详见 [`verification-receipt-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verification-receipt-v2.json)）：

| 用例编号 | 被测函数与输入设定 | 执行步数 / 预算 | 终止 PC | 实测输出与断言结论 |
|---|---|---|---|---|
| **Case 1A（正例）** | AP `0x2e3172c -> 0x2e26fcc`：合法输入 `(1, 0, 0, 0x3b, w2=1[Cine EI], 1, 0, 1)` | `75 / 300` | `0x2e00000` (正常返回) | 未命中错误分支 `0x2e270dc`；生成 16B 包 `05005141000000000702010100000000`，栈哨兵完好。 |
| **Case 1B（负例反证）** | AP `0x2e3172c -> 0x2e26fcc`：非法 `w2 = 9 (> 3)` (`setting_log_shooting=9`) | `94 / 300` | `0x2e00000` (正常返回) | 在 `0x2e27074: cmp w2, #3; b.hi #0x2e270dc` **命中错误分支 `0x2e270dc`**，证明超出 `0..3` 的拍摄模式被拦截。 |
| **Case 1C（正例）** | CP `0x791f9c` (`file+0x689f9c`, `0x4151` setter)：宿主送入 Case 1A 的 16B 包 | `25 / 100` | `0x790000` (正常返回, `r0=1`) | 模拟 RAM `0x10a8de0` 写入：`+0xba0=7, +0xba4=2, +0xba8=1, +0xbac=1, +0xbb0=0, +0x76c=1`，前后哨兵完好。 |
| **Case 1D-i（正反对照）** | CP `0x2fe05c` (`file+0x1f605c`, `CheckSetParamBasePictureSetting`)：测试 `(12,2,1,1,0)` 相符 vs `+0xba0` 不符 | `33 / 100` & `38 / 100` | `0x2fe000` (正常返回) | 相符时 `0` 次触发错误日志（**证明该检查器绝不拒绝 `base_look=12`**）；不符时精确触发 `0x2fe086` 日志且不改写状态块。 |
| **Case 1D-ii（正反对照）** | CP `0x2d38a8` (`file+0x1cb8a8` 采集字段构建)：正例 `base_look=7` vs **反例 `base_look=12`** | `17 / 100` & `21 / 100` | `0x2d38f0` (正常到达检查点) | 正例 `base_look=7 (<12)` 走 `blo #0x2d38f0`，`[r4+0x794]` 保持 `7`；**反例 `base_look=12` 被 `0x2d38b8: 0c29 cmp r1, #0xc` 拦截，执行 `0x2d38ea: movs r0, #0; str.w r0, [r4, #0x794]` 将输出清零为 `0`**。 |
| **Case 2A / 2B（正反对照）** | AP `0x2debdb0` (`MonitorLUT`)：正例输入 `0` vs **反例输入 `9 (> 4)`** | `41 / 200` & `18 / 200` | `0x2de0000` / `0x2debe74` | 正例向 `0x92840747` 发送 10B `0d2061010a0001800100`；**反例 `9 > 4` 在 `0x2debdf0: cmp w1, #4; b.hi #0x2debe74` 命中错误分支且发包数为 `0`**。 |
| **Case 2C / 2D（正反对照）** | AP `0x2dee4ac` (`ColorGamut`)：正例 `0`/`1` vs **反例 `5 (!=0, !=1)`** | `33 / 200` & `19 / 200` | `0x2de0000` (正常返回) | 正例 `0` 发送 `0d2067010a0001800100`，正例 `1` 发送 `0d2067010a0001800000`；**反例 `5` 命中 `0x2dee4ec` 早退分支，发包数为 `0` 且写 `*out=0`**。 |
| **Case 3A（正例）** | AP `0x2e3c3b8 -> 0x2e18e3c` (`0x4006` WB)：合法输入 `(1, mode=9, AB=2500, GM=-1500, Temp=5600K, flag=1)` | `77 / 300` | `0x2e00000` (正常返回) | 未命中错误分支；生成 20B 包 `050006400100000009020100f401f40138000100`（其中 `+0xc` 与 `+0xe` 余数均为 `500 = 0x01f4`，`+0x10` 为 `56 = 0x38`）。 |
| **Case 3B（负例反证）** | AP `0x2e3c3b8 -> 0x2e18e3c`：非法 `mode = 21 (> 15)` | `103 / 300` | `0x2e00000` (正常返回) | 在 `0x2e18e40: cmp w0, #0xf; b.hi #0x2e18ff4` **命中错误分支 `0x2e18ff4`**。 |
| **Case 3C & 3D（正例+分离证明）** | CP `0x79150c` (`0x4006` setter) + CP 下游复制片断 `0x3c9162..0x3c91ba` (`file+0x2c1162..0x2c11ba`) | `27 / 100` & `22 / 50` | `0x790000` & `0x3c91ba` | `0x79150c` 将参数写入 `0x10a8de0+0x9f4..0xa02`；随后 `0x3c9162` 将 `+0x9f4` 复制到 `[r0+0xec]=9`、`+0x9f8..+0x9fc` 复制到 `[r0+0xf4..0xf8]=(2,1,500,500)`、`+0xa00` 复制到 `[r0+0xfc]=56`，**证实 100K 色温字节与 AB/GM 微调在下游结构体中保持独立字段**。 |

---

## 5. Look ID 22 (`MLUT_LOOKNAME_SL3SG3_TO_ACESREC709`) 70 项描述符与数据源逐阶段精确绑定（Audit Point 3）

V1 报告中关于“`33³` / `149,888B` (`160+3×1984+143748+36=149896`)”的描述已废止撤回。下面严格按照**不同二进制对象（AV `av-cam.bin` vs CP `cpapp-b.bin`）**与**70 项描述符的真实处理阶段**逐一绑定原描述符与数据源（引用自已验证回执 [`initializer-guest-results.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/initializer-guest-results.json)、[`extraction-results.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/extraction-results.json)、[`cp-mlut-dma-results.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/resource-20261028/cp-mlut-dma-results.json)）：

### 5.1 对象一：`av-cam.bin`（AArch64 平坦镜像，基址 `0xffffffc001000000`，SHA256 `0cb7e03a...bdaf`）
- **描述符表项格式**：每项 **152 字节（`0x98`）**，结构为 `<Q data_pointer, I register_offset, I reserved_zero, I word_count, char name[128], pad[4]>`。
- **Look ID 22 表位置**：描述符 VA `0xffffffc001b05638`（文件偏移 `0xb05638..0xb07fc8`），共 **70 项 × 152B = `10,640` 字节**，由原始初始化函数 `0x2baf00` / `0x2bc100` / `0x2bc330` 调用原始 `memcpy` (`0xd80`) 从静态模板区复制到运行态表区：

| 70 项内序号 | 条目数 | 阶段名称与硬件单元 | AV 目标偏移 (`dst`) | AV 源描述符偏移 (`src`) | 精确描述符名称与底层数据源规格 |
|---|---:|---|---|---|---|
| **`0 .. 5`** | 6 项 | **阶段 A (`L1D_A`)**：S-Log3 转线性 1D 查找表（R/G/B 通道选择 + SRAM） | `0xb05638 .. 0xb05930` | `0xbe6830 .. 0xbe6700` | `MLUT_L1D_A_CH_SEL_{R,G,B}` + `MLUT_L1D_A_SRAM_{R,G,B}_SL3TOLINEAR`。每通道 SRAM 为 **256 个 32 位打包字（`1,024B`）= 512 个 16 位半字槽**。 |
| **`6 .. 11`** | 6 项 | **阶段 B (`L1D_B`)**：VENICE S-Log3/S-Gamut3 ACES 1D 整形表（R/G/B 通道选择 + SRAM） | `0xb059c8 .. 0xb05cc0` | `0xbe8120 .. 0xbe7ff0` | `MLUT_L1D_B_CH_SEL_{R,G,B}` + `MLUT_L1D_B_SRAM_{R,G,B}_VENICE_L1D0_SLOG3_SGAMUT3_ACES`。每通道 **256 个 32 位打包字（`1,024B`）= 512 个 16 位槽**（前 511 槽单调递增，第 512 槽填充 `0`）。 |
| **`12 .. 59`** | 48 项 | **阶段 C (`L3D`)**：VENICE **`20×20×20` 3D LUT**（R/G/B 三通道 × 每通道 8 个 SRAM Bank 的 `SEL` + `SRAM` 配对） | `0xb05d58 .. 0xb07940` | `0xbf5648 .. 0xbf5518` | `MLUT_L3D_SEL_{R,G,B}_RAM0..7` + `MLUT_L3D_SRAM_{R,G,B}_0..7_VENICE_3DLUT_SLOG3_SGAMUT3_ACES`。共 **24 个 SRAM bank**，每个 bank 含 **500 个 32 位字 = 1,000 个 16 位值（`2,000B`）**；总计 **`20³ = 8,000` 个网格节点、`24,000` 个通道值（`48,000B`）**。解交错规则：`bank = ((r & 1) << 2) | ((g & 1) << 1) | (b & 1)`，`index_in_bank = (r // 2) * 100 + (g // 2) * 10 + b // 2`。 |
| **`60 .. 69`** | 10 项 | **阶段 D（顶层路由、YC/RGB 转换与 `3×3` 矩阵寄存器）** | `0xb079d8 .. 0xb07f30` | `0xbe6240 .. 0xbf66e8` | `[60]` `MLUT_TOP_REG_SEL_E_NORM_WS_CUBE_CDL`<br>`[61]` `MLUT_YC2RGB_REG_INV709_YC` (`YC -> RGB`)<br>`[62]` `MLUT_L1D_A_REG_SL3TOLINEAR`<br>`[63]` **`MLUT_MTX_A_REG_SG3TOAP1_0`**（源数据位于 `0xc15aa8`，与 `0xc15b78` 处的 `MLUT_MTX_A_REG_VENICE_LMX0_SLOG3_SGAMUT3_ACES` **逐字节完全一致**：9 个 signed 19-bit / Q16 系数，精确等于 Sony 官方 VENICE S-Gamut3 → ACES AP1 矩阵）<br>`[64]` `MLUT_L1D_B_REG_VENICE_L1D0_SLOG3_SGAMUT3_ACES`<br>`[65]` `MLUT_L1D_C_REG_LUT_OFF`<br>`[66]` `MLUT_MTX_B_REG_IDENTITY`<br>`[67]` `MLUT_L3D_REG_VENICE_3DLUT_SLOG3_SGAMUT3_ACES`<br>`[68]` `MLUT_MTX_C_REG_FULLTOLEGAL`<br>`[69]` `MLUT_RGB2YC_REG_709_LEGAL` |

### 5.2 对象二：`cpapp-b.bin`（32 位 ARM/Thumb RTOS 镜像，基址 `0x108000`，SHA256 `c90d00d8...bcba`）
- **不可预设与 `av-cam.bin` 结构体字节相同**：
  - 在 `cpapp-b.bin` 中，指针为 32 位，因此每个 MLUT 描述符记录长度为 **140 字节（`0x8c`）**（而非 `av-cam.bin` 的 152 字节）。
  - CP 注册表 `file+0xbf8ffc` (`VA 0xd00ffc`) 记录 `look_id = 22`、运行态描述符表首址 `0x02015794`、条目数 `70`（即 `70 × 140B = 9,800` 字节，对应既有研究中初始化生成的 `CP-look22-initialized.bin`，SHA256 `a4f057164b12be25a2e9e80bcdd6e78bffe3d7685606e8dde39d22b1e98c10e0`）。
  - **DMA 链表生成器的区别**：
    - `av-cam.bin` 的列表生成函数位于 `0x2c4794`（按 `0x98 = 152B` 步长读取 70 项，`IP=0` 寄存器低 32 位基址为 `0xf3019000`）。
    - `cpapp-b.bin` 的列表生成函数为 `mlut_make_lli_table`（`VA 0x470f78`, `file+0x368f78`），按 `0x8c = 140B` 步长读取 70 项，在 `VA 0x2025570` 生成 `70 × 16B = 1,120B` DMA LLI 描述符，对 7 种合法资源组合 `group = 0..6` 计算目标寄存器基址 `0xf4009000 + (group << 20)`（即 `0xf4009000 .. 0xf4609000`）。
    - **重要声明**：上述 `0x2c4794`（AV）与 `0x470f78`（CP）DMA 列表构建实验来自既有专项回执 [`look-consumer-guest-results.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/look-consumer-guest-results.json) 与 [`cp-mlut-dma-results.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/resource-20261028/cp-mlut-dma-results.json)；本目录的 [`verify_menu_backend_chains_v2.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains_v2.py) 并未重放 DMA 构建，故将其列为**引用既有受限实验证据**。

---

## 6. 白平衡 100K vs 1K 量化边界与下游求解器缺口（Audit Point 4）

1. **已证实的静态与模拟事实**：
   - 在 [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so) `0x2e18e98..0x2e18ec8` 中，`PID_SET_WB_MODE` (`0x4006`) 载荷构造器对输入色温 `w26`（单位 K）执行 `mov w3, #0x64; sdiv w26, w26, w3; strb w26, [x19, #0x10]`，即除以 `100` 取整后存入单字节 `+0x10`（如 `5600K -> 56 = 0x38`）。
   - 在 [`cpapp-b.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin) `0x79150c` (`file+0x68950c`) 中，CP 将 `+0x10` 字节存入 `[0x10a8de0 + 0xa00]`，而将 `+0x9..+0xf` 的 AB/GM `/1000` 商与 `%1000` 余数存入 `[0x10a8de0 + 0x9f8..0x9fc]`。
   - 在本轮新增验证的 CP 下游复制片断 `VA 0x3c9162..0x3c91ba` (`file+0x2c1162..0x2c11ba`) 中，CP 将 `[r1, #0x9f8..#0x9fc]` 原样复制到下游结构体 `[r0, #0xf4..#0xf8]`，将 `[r1, #0xa00]` 原样复制到 `[r0, #0xfc]`。
2. **为什么不能直接用 AB/GM 余数替代 1K 色温步进（标为未证实假设）**：
   - `+0xa00` (`[r0+0xfc]`) 与 `+0x9f8..+0x9fc` (`[r0+0xf4..0xf8]`) 在 CP 内部下游结构体中依然是**彼此分离的独立字段**。
   - 在尚未逆向定位出消费 `[r0+0xec..0xfe]` 的 **CP 白平衡 R/G/B 增益求解器函数**、且尚未证明 `+0xf4..+0xf8` 的物理量纲（究竟是琥珀-蓝/洋红-绿轴的 mired 微调、日志增益偏移还是传感器通道比值偏移）及黑体轨迹插值公式之前，**绝不能从“存在 16 位 AB/GM 余数字段”推导出“可将 1K 开尔文余量折算进 AB/GM”**。
   - 因此，FX5 `home_screen.html` 中的白平衡 `[Coarse]`（100K 步进）在 FX3 `0x4006` 协议上有直接的 `+0x10` 字节对应；而 `[Fine]`（1K 步进）在 FX3 上目前属于**存在协议量化阻断、折算假设未证实的待研究项**，本阶段绝不实施未经标定的折算公式。

---

## 7. FX5 官方规范与 FX6 6.01 规范严格分离及具体页面段落绑定（Audit Point 7）

所有直接抓取的 HTML 页面标题、章节标题与粗体术语清单已保存在 [`online-sources-receipt-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/online-sources-receipt-v2.json)。

### 7.1 Sony FX5 (`ILME-FX5`, Help Guide `2630 v1`) 直接验证的 UI 规范（HTTP 200）

| 页面文件与 SHA256 | 页面 `<h1>` 标题 | 页面内具体章节 / 条目原文绑定 | 对应 FX3 7.02 原生状态与能力边界 |
|---|---|---|---|
| `home_screen.html`<br>`79396f73...235c` | `HOME screen` | **Item 1 `FPS`**：子项 `[Variable]` (`On`/`Off`)、`[Value]`；对应完整菜单 `[Shooting] - [FPS]`。<br>**Item 2 `ISO / Gain / Exposure Index`**：明确规定随 `[Project] - [Base Setting] - [Shooting Mode]` 切换四套子项：`Custom` (`[ISO/Gain]`, `[Base Sensitivity]`, `[AGC]`)、`Flexible ISO` (`[ISO]`, `[Base ISO]`, `[AGC]`)、`Cine EI` (`[Exposure Index]`, `[Base ISO]`)、`Cine EI Quick` (`[Exposure Index]`)。<br>**Item 3 `Shutter`**：`[Angle]` 或 `[Speed]` (`Step` / `Cont.`) + `[Auto Shutter]`。<br>**Item 4 `Iris`**：仅含 `[F-number]` 与 `[Auto Iris]`（**注意：FX5 官方 HOME 屏第 4 项只有 Iris，无内置 ND**）。<br>**Item 5 `Scene File` / `Look`**：`Custom` 模式调 `[Paint/Look] - [Scene File]`；`Log` 模式调 `[Paint/Look] - [Base Look] - [Select]`，且子面板 `1`=主/副录 LUT 开关、`4`=`[Edit Look]`、`6`=HDMI/VF/LCD 监看 LUT 开关。<br>**Item 6 `White Balance`**：`[Mode]` (`Memory A..H`/`Preset`/`ATW`/`AWB`)、`[Color Temp]` (`[Coarse]` 100K / `[Fine]` 1K)、`[Tint]` (`-99..+99`)、`[AWB]`。 | 1. **FX5 第 4 项仅含 `Iris` 与 FX3 物理无内置 ND 完全吻合**。<br>2. FX3 原生具备 4 种拍摄模式（`setting_log_shooting` `0..3`）与双底座 ISO，但 `0x821c538` 仅是运行态 RAM，新增 `base_look=12` 或 8 组 WB 记忆槽 `A..H` 的非易失保存尚未验证。<br>3. WB `[Fine]` 1K 步进受限于 `0x4006` `+0x10` 的 100K 量化。 |
| `quick_menu.html`<br>`97521d08...6733` | `Quick Menu` | 章节 `Displaying and operating the Quick Menu`：短按 `MENU` 打开；**Items 1..5** 通过方向键左右或触控切换 `[Project]`、`[TC/Media]`、`[Monitoring]`、`[Audio]`、`[Info]` 五个页面；**Item 6** 直接跳转至当前分类的 Full Menu。<br>章节 `Information displayed on the [Info] page`：只读显示 **1. System info**（Date/time, Sensor temperature, Hours meter）、**2. Battery info**（Battery remaining, USB-PD）、**3. Lens info**（Model, Serial, Iris, Focal length, Focus distance, Depth of field）。 | FX3 原生具备 Project/TC/Media/Monitoring/Audio 对应设置序列及电池/镜头光圈焦距对焦距离模型数据；但 `[Info]` 页中的传感器摄氏温度与累计工时计数器在 AP UI 层的可读性属**待核查项**。 |
| `fullmenu_use.html`<br>`d882a235...716c` | `Using the Full Menu` | 章节 `Full menu configuration` & `Full menu operations`：长按 `MENU` 打开；包含 10 个分类（`[Shooting]`, `[Project]`, `[Paint/Look]`, `[TC/Media]`, `[Monitoring]`, `[Audio]`, `[Clip Operations]`, `[Technical]`, `[Network]`, `[Maintenance]`）；单屏最多显示 **8 行**；连续大范围子项（如 `-99..+99`）不弹选项列表而直接行内高亮调节；确认前按 `BACK` 取消修改并返回上一级；`[Execute]` 项弹出确认窗口并暂隐菜单。 | 该 8 行列表、行内直调与 `BACK` 撤销属于 UI 状态机交互契约，**9 个 FX5 页面 `HTTP 200` 只能证明 FX5 官方设计规范，不能反证 FX3 7.02 原有二进制已具备该 UI 布局**。 |
| `project.html` / `paint_look.html` / `tc_media.html` / `shooting.html` / `monitoring.html` / `block_diagram.html` | 各分类菜单说明 | 具体提取出的全部二级/三级标题见 [`online-sources-receipt-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/online-sources-receipt-v2.json) 中的 `extracted_sections_and_headings`。 | 明确区分 FX3 原生具备项（如 `Zebra`、`Peaking`、`De-Squeeze`、双槽接力/同时录制、XLR 4 声道）与 FX3 硬件缺失/容器差异项（无 SDI/VF、无 BNC TC Out、MP4 容器而非 MXF）。 |

### 7.2 Sony FX6 (`ILME-FX6V`, Ver. 6.01 `00259043`) 规格来源与限制说明
- 直接通过脚本请求 `https://www.sony.com/electronics/support/camcorders-and-video-cameras-xqd-camcorders/ilme-fx6v/software/00259043` 返回 **`HTTP 403`**（Akamai 反爬限制）。
- 公开搜索索引摘要显示 FX6 Ver. 6.00/6.01 更新了 BIG6 主屏布局、新增 59.94P 下 `1.2F (1/50)` 快门档位及 3D LUT / Monitor LUT 处理优化；同时 FX6 机身具备内置电子可变 ND（`Clear / 1/4 / 1/16 / 1/64 / Variable / Auto`）与 12G-SDI。
- **证据纪律**：由于 `00259043` 未能通过脚本直接 `HTTP 200` 归档，上述 FX6 6.01 发行说明细节在 [`online-sources-receipt-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/online-sources-receipt-v2.json) 中单独列为 `DIRECT_HTTP_403_BLOCKED_EXTERNAL_SEARCH_SUMMARY_ONLY`；本地 `fx6-prefix-curl.bin` 仅是 64KB 固件包头部二进制前缀，**绝不作为 BIG6 或菜单能力的证据**。

---

## 8. 虚拟机（VM）现状修正与完整 RAW/ISP 六段式独立审查（Audit Point 6）

### 8.1 项目内 VM 真实进展（修正 V1 过时描述）
根据项目报告 [`ap103-software-ldec-and-native-save.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/ap103-software-ldec-and-native-save.md)、[`ap103-visual-step-log.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/ap103-visual-step-log.md) 与 [`ap105-offline-preparation.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/ap105-offline-preparation.md)：
1. **AP103-r2 已具备完整图形界面（GUI）显示与按键步进能力**：通过软件 `/dev/ldec` 驱动，AP103-r2 在 4 核 MTTCG QEMU guest 中已实际跑出完整待机画面 → `MENU` → `Setup` → 语言弹窗等目视截图序列；当前未验收的是菜单修改后的原生文件持久化保存（New generation save）以及高负载下 5000ms 接收绘制超时问题。
2. **AP105 处于离线准备、待执行验收状态**：基于 AP103-r2 仅替换 GPE 性能件的 `ap105-v1-gpe-perf` 候选已离线生成，其长轮运行计时、语言/日期保存与 TRY2 网页测试目前处于待执行状态（本轮严格遵守指令，未启动任何 VM 或触碰运行锁）。
3. **VM 对色彩与 ISP 链的局限**：尽管 AP103 已能渲染 AP 侧 GUI，QEMU guest 仍然只运行 AP Linux（`appFw.so`），**不包含真实的 CP RTOS (`cpapp-b.bin`)、AV 核 (`av-cam.bin`) 或 BIONZ XR 硬件 ISP/MLUT 引擎**。因此，菜单 UI 渲染可以在后续授权的 AP VM 中验证，而 CP/AV/ISP 色彩链路仍必须依赖双核/多核指令仿真与真机硬件验证。

### 8.2 完整 RAW / 底层色彩链六段式独立审查（为何 3D LUT 绝不能替代整链）
1. **Stage 1（传感器读出、双原生 ISO 转换增益、光学黑电平 OB、坏点与暗角校正）**：归属 **硬件 ISP 前端（由 CP RTOS 配置寄存器）**。3D LUT 无法改变模拟/数字增益切换与黑电平本底。
2. **Stage 2（Bayer 去马赛克、2D/3D 空时降噪 NR、边缘 Detail 与肤色细节 Skin Tone Detail）**：归属 **硬件 ISP 空时滤波核心（由 CP RTOS 配置）**。3D LUT 无空间邻域算子，无法替代降噪与肤色细节门限。
3. **Stage 3（白平衡 R/G/B 增益求解、传感器原生色域转工作色域 `3×3` CCM、预伽马/S-Log3 传递曲线、Knee 高光拐点与滚降）**：归属 **CP RTOS 求解器 → 硬件 ISP 矩阵/曲线引擎（位于 MLUT 之前）**。若上游白平衡微调（如 1K vs 100K）、CCM 或高光拐点压缩与 FX6 不同，直接把像素送入下游 LUT 会导致高光截断斜率与肤色相角失真。
4. **Stage 4（MLUT 模块：`L1D_A` S-Log3→Linear + `MTX_A` SG3→AP1 + `L1D_B` VENICE 1D + `L3D` `20×20×20` 24-bank 3D LUT + `MTX_C` / `RGB2YC`）**：归属 **CP VFX SDK / AV MLUT 驱动 → 硬件 MLUT 窗口（CP `0xf4009000 + (group << 20)` / AV `0xf3019000`）**。这是 70 项描述符所覆盖的阶段，也是唯一可由复合 MLUT 表直接定义的部分。
5. **Stage 5（多路输出分流：主/副录编码 vs HDMI/LCD 监看辅助）**：归属 **CP 多资源组 (`group 0..6`) + BB/VDF 显示引擎 (`0x92840747` `0x0161` MonitorLUT / `0x0167` ColorGamut)**。必须保持主录与监看通道解耦。
6. **Stage 6（AP 模型 RAM `0x821c538` 与非易失 Backup/CAMSET 持久化及容器元数据）**：归属 **AP Linux (`appFw.so`) + Backup 子系统 + AV 封装器**。仅改写运行态 RAM `0x821c538` 会在重配或重启后丢失，必须接入非易失 Backup 保存机制。

---

## 9. 一键复现与核验命令

```sh
/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python \
  /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains_v2.py
```

脚本实际执行退出码为 `0`，输出回执保存在 [`verification-receipt-v2.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verification-receipt-v2.json)。
