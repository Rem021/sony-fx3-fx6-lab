# Hydrogen-9｜全球索尼 BIONZ XR 固件逆向、QEMU 虚拟化与 Multi 口 BootROM 救砖最新研究同步与工程对齐报告

> **调研基准日期 (Research Cutoff)**：`2026-11-14` · **工作流任务**：`Hydrogen-9 (task_df8c276bf006)`  
> **目标对齐基线 (Lab Target Baseline)**：`ILME-FX6 v6.01 -> ILME-FX3 v7.02`（`CXD90057` / `Model ID 0x91030080`）  
> **洁净室声明 (Clean-Room Compliance)**：本文档全部外部技术事实均通过公开 GitHub 仓库文档、源码说明与官方技术通告实证检索汇总；未克隆或提交任何第三方闭源固件、密钥材料或二进制资产；对本仓 [`docs/`](../../docs/)、[`outputs/`](../../outputs/) 与 [`reports/`](../../reports/) 严格遵循只读交叉核验。

---

## 执行摘要 (Executive Summary)

2024 年底至 2026 年 11 月，全球索尼无反/电影机逆向与虚拟化研究社区在三个关键维度上实现了跨越式突破，并与本实验室 **FX6-on-FX3（`ILME-FX6 v6.01 -> ILME-FX3 v7.02`）** 工程闭环形成了高度互证：

1. **支柱一｜BIONZ XR（`CXD90057` / `CXD90058`）固件解密与 `HAITA` / `BK4` 门控体系透明化**：
   - [`OlliV/fx30_fw`](https://github.com/OlliV/fx30_fw) 与 [`leogenot/sony-a7iv-feature-research`](https://github.com/leogenot/sony-a7iv-feature-research) 完整还原了 `BODYDATA.DAT`（`\x89UFU\r\n\x1a\n` / `FDAT` / `UDTRFIRM`）的 `ECB + CBC(CXD90057_k8)` 解密链、7,337 项 `STRID_FUNC_*` 与 771 项 `PRM_HAITA_*` 互斥表，并从可执行表实证：**`PRODUCT_MODEL_ALCIN_UUD`（enum `4`、feature index `24`、`IMX510`、`CINEMA_LINE`）即 FX3 产品类别**，而 `PRODUCT_MODEL_LAX`（`IMX684`、无机械快门）对应 FX30、`PRODUCT_MODEL_LS`（`IMX710`）对应 A7 IV。
   - 2026 年下半年兴起的 `054C:0336` Senser/Jiritsu 通道（`AdjustControl PFUNC=0x40, block=0x1001`）路径穿越（`/tmp/jiritsu/../..`）与 `libJit.so` -> `im.elf` (`EUID=0`) 内存热补丁链（[`YuuLuo/a7c2-service-preload`](https://github.com/YuuLuo/a7c2-service-preload)、[`QAQLeonard/a7c2-fl23-research`](https://github.com/QAQLeonard/a7c2-fl23-research)、[`t2r05/fx30-senser-map`](https://github.com/t2r05/fx30-senser-map) 及 2026-10 A7S III BIG6/可变快门 PoC）与本实验室 Stage-A 的只读/非持久安全边界形成鲜明对照；而 Rust 重写的 [`masterflai/pmca-re-reloaded`](https://github.com/masterflai/pmca-re-reloaded)（`v1.12.1`）已解决了 **macOS 26+ `IOUSBHost` 抢占 `0xe00002be` 故障**，并正式识别 A7 V（`ILCE-7M5`）的 **"Senser v2" RSA 签名服务认证**。

2. **支柱二｜QEMU 整机虚拟化、软件 GPE/LZ77 管线与异构 Linux+RTOS `IVSHMEM` 建模**：
   - [`chocotan/a7c2-qemu`](https://github.com/chocotan/a7c2-qemu)（QEMU `11.1.2`、`virt,secure=off`、`cortex-a35`、`-device ramfb`）及其前序研究 `chocotan/a7c2-re`（目前 GitHub 已设为私有/404，核心配方记录于 [`zve10-qemu/docs/HANDOFF_2026.md`](https://github.com/cokeenet/zve10-qemu/blob/main/docs/HANDOFF_2026.md)）验证了 **软件 GPE（`gpe-raster.c` / `gpe-sprite.c`）+ Sony LZ77 CPU 解码（`sony-lz77.c`）+ `dmm-service.c` + `ramfb` `[0x41e100000, 0x41e600000)` `RGBA4444 -> XRGB8888`** 通路，在原 init 冷启动下实现拍摄 HUD 与简体中文菜单往返。
   - [`cokeenet/zve10-qemu`](https://github.com/cokeenet/zve10-qemu)、[`ivica00/sony-a6400-research`](https://github.com/ivica00/sony-a6400-research) 与 [`Liwenru88/a7r5-rea`](https://github.com/Liwenru88/a7r5-rea) 分别在 `CXD90045`（Sugilite GPU `BAR 0xF1000000` / `IRQ 76`）与 `A7R V`（4.19 模块化自建与 WBI `dfa823fc` 审计）方面取得关键进展；但**与本实验室 Round 8（FX3 Ver. 7.02 `Linux 4.9.337-scel+` 内核 + `FX6_NATIVE_FAITHFUL=1` `nop_count=0` 原生 FreeType/GPE0 跨机型闭环）相比**，本实验室已完成从真实 `appFw.so` 到物理 `GPE0` 帧缓冲的零替换（`subst_color=0, subst_image=0`）端到端跨机身移植运行，下一代架构突破口在于引入 QEMU `ivshmem-doorbell` + `ivshmem-flat` / `OpenAMP` 双 VM 联调真实的 Stock-CP（`cpapp-b.bin` ARM32 RTOS）。

3. **支柱三｜Multi 口 `48000` 波特率 BootROM 免拆机救砖、`nflasha1` 双层验签与 FX3 Wi-Fi/BT 死循环防砖**：
   - [`DavidBuchanan314/ILCE-7M4-RE`](https://github.com/DavidBuchanan314/ILCE-7M4-RE) 发现的 **CXD90057 BootROM 未公开 `48000` 波特率 Multi 口开漏 UART 启动协议**（`RP2040-Zero` 三线接入 `RX/TX/XReset`，无需拆机）及其衍生工具（[`Erlla/sony-a7m4-custom-firmware`](https://github.com/Erlla/sony-a7m4-custom-firmware) 与 [`Hearts-Ace/sony-a7r5-custom-firmware`](https://github.com/Hearts-Ace/sony-a7r5-custom-firmware) 加载官方签名 `fastboot.bin`/`mira` 至 SRAM `0x92028000`，以及 `ILCE-7M4-RE` `push_payload.py` 注入 eSRAM `0xFE020000` 触发 `18D1:4EE0` Android Fastboot v0.5），**对同样保留完整 15-pin Sony Multi 接口的 FX3 (`ILME-FX3`) 具有决定性战略价值**——可在不拆机破坏防水与排线的前提下直读/直写 AES-XTS-256 加密后的 `nflasha1..30` 与 CP NOR。
   - 结合索尼官方通告 **`00342260`**（2026-01-20 更新）及社区 FX3 v3.00–v7.02 无线模块故障导致的 `"System Error"` 5–10 秒无限重启死循环与 `6L+9S` 升级变砖案例，直接交叉验证了本实验室 Stage-A `P3`（`libInfraAppRemoteBoard.so`）与 `P8`（异步日志非阻塞）设计的必要性，并指明了 Stage-A/B 在 `InfraPericon` / `SeqQueueNetwork` / `WF-12` 无线驱动层必须实施的非阻塞降级熔断红线。

---

## 第一支柱：Sony BIONZ XR（`CXD90057` / `CXD90058`）固件逆向与特性门控

### 1.1 双核异构 SoC 硬件拓扑与内存/加密布局

基于 [`DavidBuchanan314/ILCE-7M4-RE`](https://github.com/DavidBuchanan314/ILCE-7M4-RE) 与 [`DavidBuchanan314/Sony-ILCE-7M4-Linux`](https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux) 对同代平台 `CXD90057` 实机的物理 `/proc/iomem` 与 SPI 协处理器监控提取，BIONZ XR 架构核心事实如下：

| 子系统 / 寄存器域 | 物理地址范围 / 参数 | 硬件职责与安全边界 | 对 FX3 / FX6 实验室的直接印证 |
| :--- | :--- | :--- | :--- |
| **AP ("Mira")** | `CXD90057`, 4× Cortex-A35 (ARM64) | 运行 Sony CE Linux 4.9.337 (`scel+`)、XAVC 编码调度、`appFw.so` / `im.elf` | 与本仓 FX3 v7.02 (`vmlinux.bin`) 及 Round 8 QEMU `cortex-a35` 拓扑完全一致 |
| **CP ("Cetus")** | `CXD90058`, Cortex-R5 RTOS (`0x67800000` 域) | 实时传感器/快门/IBIS/镜头控制 (`cpapp-b.bin` @ `0x00108000`)；通过 AP SPI 通道 `spicom.elf` / `ud_spicom_boot.elf` 引导或进入 3 命令 SPI 监控模式（写内存、32 位字节和校验、跳转执行） | 实证 [`outputs/fx6-on-fx3-closure`](../../outputs/fx6-on-fx3-closure/README.md) Phase 10 `U2` 结论：Stage-A 严禁刷写 `p8:/cp` (`cp_mutation_bytes = 0`) |
| **AP BootROM** | `0xffff0000..0xffffbfff` (48 KiB) | 含密钥加扰垫 `0xffffb800..0xffffbc00`；读取 `>= 0xffffc000` 触发硬件看门狗复位 | 硬件不可变 Root-of-Trust；无任何 USB 字符串，仅暴露 Multi 口 GPIO UART 与 SPI 引导模式 |
| **内部 eSRAM** | `0xfe000000..0xfeffffff` (含 `loader_nor` 映射区) | BootROM UART `uart_boot` 与 `loader_nor.bin` 执行空间（`push_payload.py` 加载至 `0xfe020000`，官方 `mira` Fastboot 加载基址 `0x92028000`） | 印证 [`outputs/fx3-safety`](../../outputs/fx3-safety/fx3_safety/boot_contracts.py) 对 `loader_nor.bin` (`0xfe04c7a8 -> 0xfe04d584`) 与 DDR 训练入口 `0xFE080000` 的定位 |
| **外设 MMIO 映射** | Serial `0xf1000000..0xf1004fff`<br>I2C `0xf1012000..0xf1013fff`<br>SPI0..4 `0xf1017000..0xf101bfff`<br>USBS `0xf10cc100..0xf10d0fff`<br>eMMC `0xf10d6000..0xf10e0fff`<br>SCU `0xf1388000` · SPACC `0xf7fc0000` | 囊括 PL011/SCEL 串口、USB 2.0/3.x 控制器、SDM2 eMMC 控制器及硬件加解密引擎 `SPACC` | 可直接用于核验 [`kernel_dtb_compatibility_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/kernel_dtb_compatibility_verifier.py) 中 `cxd90057.dtb` 的 68 节点 MMIO 范围 |
| **eMMC 分区与加密** | `SDM2` 分区表魔数 `b"8246"` `"2.00"`；加密算法 **AES-XTS-256** | 以逻辑扇区号作 XTS tweak 对加密分区（`type=5, flag&1 -> /dev/cnflasha*`）透明加解密；**eMMC 分区本身无静态启动签名校验** | 解释了为何一旦在 Fastboot (`18D1:4EE0`) 下拥有透明 XTS 通道，便可任意转储/恢复 `nflasha1..30` |

### 1.2 `BODYDATA.DAT`（`\x89UFU` / `FDAT` / `UDTRFIRM`）容器解包与固件结构

[`OlliV/fx30_fw`](https://github.com/OlliV/fx30_fw) 的 [`tools/decrypt_fdat.py`](https://github.com/OlliV/fx30_fw/blob/main/tools/decrypt_fdat.py) 及其技术笔记清晰梳理了第 5 代 BIONZ XR 固件升级包结构：
- **外层封装（`UFU`）**：`BODYDATA.DAT` 头部魔数为 8 字节 `\x89UFU\r\n\x1a\n`，内含厂商元数据与 `FDAT` 固件密文块；`FDAT` 块尾部 `0x110`（272 字节）为 **16 字节 AES-CBC IV**（位于 `off + size`）与 **256 字节 RSA-2048 签名**。
- **双段密钥解密链**：
  1. 首 512 字节头使用 `AES-ECB`，密钥为 `sha256(b"")[0:16]`（与 `ivica00/sony-a6400-research` 在 `CXD90045` 13 款机身上观测到的 AES 辅助密钥完全同源）；
  2. 载荷主体按 1024 字节分块使用 `AES-CBC(KEYS['CXD90057_k8'], IV)` 解密，每块前 4 字节包含 **2 字节小端校验和 + 2 字节块长/结束标志（`0x8000`）**；
  3. 输出 `UDTRFIRM` 容器并进一步解包出 `firmware.tar`，核心镜像包括 `/dev/nflasha3`（`vmlinux.bin` + `initrd.img`）、`nflasha7`（ext4 rootfs，FX6 为 `size=0` 而 FX3 占用 `0x19000` 扇区）与 `nflasha15`（`/usr` 只读应用分区，包含 50MB 级主应用 `/lib/appFw.so`）。

### 1.3 `HAITA` 特性门控、`PRODUCT_MODEL_*` 类别表与 `BK4` 属性体系

[`leogenot/sony-a7iv-feature-research`](https://github.com/leogenot/sony-a7iv-feature-research)（基于 A7 IV v6.02 与 FX3 v7.02 对照，[`PRODUCT_CLASS.md`](https://github.com/leogenot/sony-a7iv-feature-research/blob/main/docs/PRODUCT_CLASS.md)、[`SHUTTER_ANGLE.md`](https://github.com/leogenot/sony-a7iv-feature-research/blob/main/docs/SHUTTER_ANGLE.md)、[`LUT.md`](https://github.com/leogenot/sony-a7iv-feature-research/blob/main/docs/LUT.md)、[`OPEN_GATE.md`](https://github.com/leogenot/sony-a7iv-feature-research/blob/main/docs/OPEN_GATE.md)）与 [`OlliV/fx30_fw`](https://github.com/OlliV/fx30_fw) 对索尼多机型共用单一 `appFw.so` 的门控架构给出了可机读的二进制证明：

1. **三层门控机制**：
   - **层 1：`feature_manager::update_product_model()`（A7 IV `0x183ecc0`）**：将产品枚举写入 `.bss 0x5a59788`，所有 `PRM_FEATURE_MANAGER_*` Getter 统一通过 `ldr w0, [x0, x1, lsl #2]` 查表返回硬件能力位。
     - `PRODUCT_MODEL_LS`（enum `0`, feature idx `26`, `IMX710`, `OTHER`）= **ILCE-7M4 (A7 IV)**（`SYSIPSX-DSLR/LS` / `CH89101_CEC`）。
     - `PRODUCT_MODEL_LAX`（enum `3`, feature idx `25`, `IMX684`, `CINEMA_LINE`, 无机械快门）= **ILME-FX30**（`OlliV/fx30_fw` 中提取的 `LAX` 备份配置证实）。
     - `PRODUCT_MODEL_ALCIN_UUD`（enum `4`, feature idx `24`, `IMX510`, `CINEMA_LINE`, 双卡槽 CFexpress Type A）= **ILME-FX3**（FX3 7.02 `appFw.so` 仅保留 9 个活跃类别：`LS YT GL LAX ALCIN_UUD SA DZ YS GS`）。
   - **层 2：每机型独立菜单目录（`PRM_FEATURE_MANAGER_menu_item`, id `119`, `0x183ee0c` / `0x37b7be8`, 131 处直接调用）**：按 `TYPE_MENU_ITEM_LS` / `TYPE_MENU_ITEM_LAX` / `TYPE_MENU_ITEM_ALCIN_UUD` 整页裁剪菜单（如 `Base ISO`、`RAW Output`）。
   - **层 3：`HAITA` 生成排除规则与编码器末端门控**：`OlliV/fx30_fw` 统计出 **7,337 条 `STRID_FUNC_*`** 与 **771 条 `PRM_HAITA_*` 互斥规则**。`OPEN_GATE.md` 更指出重要反例：即使 `appFw.so` 内包含 `IMAGER_SCANMODE_FF_5K_3_2`（`VIDEO_FORMAT_5016x3344P`）与 `SELECT_CODEC_X_OCN_LT` 字符串（对应 FX5 规格），由于 AVC/HEVC 编码配置文件与 Remote SDK `0x9203` 描述符完全缺失 `5016x3344`，仅修改 `Backup.bin` 属性 `0x02cf00d7` (`BKID_APP_EXTERN_MENU_MOVIE_REC_ASPECT_XAVC`) 无法凭空激活 Open Gate。

2. **已实机验证的 `BK4` NVRAM 属性键值**：
   - **快门角度 (Shutter Angle)**：`0x02cf1702`（1B：`00`=Speed / `01`=Angle）；`0x02cf1704`（1B：`10`=180°, `0A..1C` 对应 `360°..5.6°`, `00..09` 对应 `64F..2F` 帧周期）。在 A7 IV 上写入 `0x02cf1702=01` 仅点亮 HUD 图标，因缺少 Cinema Line 拨盘分发而不可调；而 2026-10 在 A7S III 上的 PoC 通过 `libJit.so` 同步改写内存模式表与 `Backup` 实现了原生可变快门与 BIG6 界面。
   - **Log 拍摄与 3D LUT**：`0x02cf1443`（Log Shooting：`00` Off / `01` Flexible ISO / `02` Cine EI Quick / `03` Cine EI）、`0x02cf1453`（Select LUT：`00` S709 / `01` R709 / `02` S-Log3 / `03..12` User1–16）、`0x02cf14a4..0x02cf14b3`（User1–16 存在标记）。**重要工程警示**：A7 IV 上 `0x02cf1443=01` 可持久化写入并在冷启动后保留，但仍被 `TYPE_MENU_ITEM_LS` 菜单目录与运行时门控隐藏；**直接篡改 `Backup.bin` 中的 `PRODUCT_MODEL` 会联动切换全部硬件/传感器参数表，极易致砖（`leogenot` 明确警告禁止）**——这也印证了本实验室采用 **FX6 原生 `appFw.so` + 内存 Stage-A 适配层 + RAM-Shadow `BK4\0`** 路线（而非修改 FX3 原生 `Backup.bin` 机型 ID）的绝对正确性。
   - **其他已标定 `BK4` ID**：变形宽银幕反挤压 `0x02cf1bf2`（De-Squeeze）、NTSC/PAL 弹窗控制 `0x02cf0004`（[`Sony-PMCA-RE#756`](https://github.com/ma1co/Sony-PMCA-RE/issues/756)）。

### 1.4 USB 服务模式（`054C:0336`）、Jiritsu 通道与 `pmca-re-reloaded` 演进

1. **USB 服务会话与 Jiritsu `libJit.so` 代码执行链**：
   - 相机在 MSC 大容量存储模式下（FX3 `054C:0DA1`、FX30 `054C:0E0E`、A7C II `054C:0E8A`），主机下发 Vendor Control 请求 `bmRequestType=0x43, bRequest=1, wValue=0x37FF, wIndex=0xD7AA` 并完成 3–7 轮 Senser 质询后，相机在同一物理端口重枚举为服务模式 **`054C:0336`**（对应本实验室 `Gate G02` Stage 285 实机 124 帧闭环验证）。
   - [`cokeenet/zve10-qemu/docs/JIRITSU_CHANNEL.md`](https://github.com/cokeenet/zve10-qemu/blob/main/docs/JIRITSU_CHANNEL.md) 逆向还原了 `libsencore.so` 内的命令名表 `{u16 f1; u16 osal_id; u16 block; u16 code; char name[]}`，完整定位了 `AdjustControl (PFUNC=0x40, block=0x1001)` 的 Jiritsu（`adjstctl.elf` / `libJiritsu.so`）指令集：`0x4002` `MOUNT`、`0x4003` `FORMAT`（高危禁用）、`0x4005` `DEBUG`、`0x4006` `FIRMUP`、`0x4007`/`0x4010` `SET_FILE(2)`、`0x4008`/`0x4011` `GET_FILE(2)`、`0x400f` `SET_FILE_PATH`（`[req+20]` 长度 `2..513`）。
   - [`YuuLuo/a7c2-service-preload`](https://github.com/YuuLuo/a7c2-service-preload)、[`QAQLeonard/a7c2-fl23-research`](https://github.com/QAQLeonard/a7c2-fl23-research)（Issue #23 证实 ARM32 A7C 2.03 同样适用）及 2026-10 A7S III BIG6 PoC 均利用 `SET_FILE_PATH` 的 `/tmp/jiritsu/../..` 路径穿越写入 `/etc/ld.so.preload` 或 `/tmp/jiritsu/libJit.so`，再触发 `JIRITSU_DEBUG`（或日期触发命令）令 `im.elf` 调用 `dlopen()` 以 **`EUID=0`** 运行载荷。
   - [`t2r05/fx30-senser-map`](https://github.com/t2r05/fx30-senser-map) 补充了一项关键版本差异：FX30 v6.00 可通过成对写配置+冷启动启用隐藏连拍模式，但 **v6.01 固件已开始拒绝被修改的设置包**；而 [`goudvuur/sonshell`](https://github.com/goudvuur/sonshell) 则代表了基于官方 Sony Camera Remote SDK（Wi-Fi/Ethernet Keepalive + 自动化后处理）的合规非侵入式路线。

2. **[`masterflai/pmca-re-reloaded`](https://github.com/masterflai/pmca-re-reloaded)（`v1.12.1`，Rust + Tauri 2 + WASM 插件架构）工程突破**：
   - **macOS 26+ `0xe00002be` 修复**：解决 macOS 26 新版大容量存储驱动在卸载后极快抢占接口导致 `IOUSBLib` 打开失败的问题——捕获前等待磁盘驱动静默，最后回退采用原生 `IOUSBHost` 路径打开已稳定会话，且不再因 USB STALL 重发控制包。
   - **新一代安全壁垒（"Senser v2"）**：在 **ILCE-7M5 (A7 V)** 等最新 BIONZ XR 机身上检测到基于 **RSA 签名的服务认证（Senser v2）**——无厂商私钥已无法进入传统 `054C:0336` 服务壳，标志着索尼正逐步封堵软件侧服务模式入口，**进一步抬升了 Multi 口硬件 BootROM 通道（第三支柱）的长期不可替代性**。
   - **防砖工程规范**：内置基于 `camset` 容器格式的 `CAMSET*.DAT` 对比工具、强制 5 步受保护写入路径（`Drop` 退出守卫、写后全量回读校验、`rollback/-.json` 保留 5 份镜像历史），并明确警示：**部分相机内置 BusyBox `dd` 不支持 `conv=notrunc`，原地覆写会直接截断目标文件导致变砖**——本实验室所有覆盖操作一律要求先验证工具链或使用全量镜像/RAM `mount --bind`。

---

## 第二支柱：Sony 相机 QEMU 虚拟化、GPE 硬件建模与异构 `IVSHMEM` IPC

### 2.1 全球三大开源 Sony QEMU 路线横向对比

| 维度 | [`chocotan/a7c2-qemu`](https://github.com/chocotan/a7c2-qemu) (+ `a7c2-re` 谱系) | [`cokeenet/zve10-qemu`](https://github.com/cokeenet/zve10-qemu) | [`ivica00/sony-a6400-research`](https://github.com/ivica00/sony-a6400-research) | 本实验室 (`fx3-vm-trial` + `fx6-native-presenter-closure` R8) |
| :--- | :--- | :--- | :--- | :--- |
| **目标 SoC / 机型** | `CXD90057` / A7C II (`ILCE-7CM2` v2.01) | `CXD90045` / ZV-E10 (`ARMv7` Linux `3.0.27`) | `CXD90045` / A6400 (`ILCE-6400` / `6400A`) | `CXD90057` / **FX3 v7.02 内核 + FX6 v6.01 应用栈** |
| **QEMU 平台策略** | QEMU `11.1.2` `-M virt,secure=off -cpu cortex-a35 -m 24G` + DTB 修补 + `ramfb` + `sony-ui-input` | 自研 `-M cxd90045` 机器模型 + `-display none` + `bionz-streamfb` | Python/Unicorn 洁净室仿真 + `PL011` IRQ `150` + Sugilite MMIO | QEMU AArch64 (`virt,gic-version=2`, `cortex-a35`, `5120 MiB`) 运行 **FX3 7.02 原厂内核 `4.9.337-scel+`** + Stage-A `tmpfs` |
| **显示与 GPE 建模** | 软件 GPE (`gpe-raster.c`, `gpe-sprite.c`) + Sony LZ77 (`sony-lz77.c` 绕过 `/dev/ldec`) + `HOSDAP02` + `ramfb` `[0x41e100000, 0x41e600000)` | 计划将 `GRM_*` GOT Hook 重定向至 VDF `0x20312000` (`bionz-streamfb`)；已打通 `grm_gles` `/dev/dmpgles2` | 逆向 `grm_gles.ko` Sugilite `BAR 0xF1000000`, IRQ `76`, `0xF3400080`=`0x15` + `CC:` `5×9×9` 3D LUT | 原生 `libuxengine.so` FreeType + `GRM_gpermFillrect`/`Rectblit` + `libgrm-fbinit9.c` 直接落盘物理 `GPE0` (`0x41e001000`, `RGBA4444->ARGB8888`, `1024×540`) |
| **原厂补丁侵入度** | `LD_PRELOAD menu-observe.so` + Stub `dmm-service.c` / `hdmi-format-service.c` + `virtual-rom-v1` 虚拟蓝牙 | 9 项镜像修补（`liro.ko`, `backup.ko`, `libosal_uipc.so @0x26c0`, `im.elf @0x2f46`, `libc abort->b .`） | 仅启动到更新器 `BusyBox v1.13.4 /bin/ash`；主系统待解页错误恢复 | **Round 5–8 达成 `nop_count = 0`**、`subst_color = 0`、`subst_image = 0`、`forced_render = 0`；全部适配严格隔离在内存 `Stage-A` 队列与 `P1..P10+Fan` |
| **交互与实证成果** | 1GiB 虚拟 FAT16 SD 卡、GTK 触控、1120 对键码（中位延迟 `97.3ms`），原生 `init` 冷启动至中文菜单往返 | 启动至 `52.5s..70.6s`，70 个内核模块 + 43 种 UIPC 处理器；`ab_log.img` 修复 `nflasha11` `/log` | `1895` 项离线单测、`av-cam` 命令阶梯（285/286/337）、`ilce_6400a` 2.727ms 探测 | 10 个核心场景（`r5a..r7c` + `r8a/r8b` 混合内核）全量过检，`r7c` 实测 `Scene File -> "S-Cinetone"` `1,928` 像素精确差分与 `r6c == r5b` 比特级往返一致 |

### 2.2 关键共性经验与补充生态（`a7r5-rea` / `qemu-bench`）

- **`chocotan/a7c2-re` -> `a7c2-qemu` 的三大关键教训**（已归档于 `zve10-qemu` `HANDOFF_2026.md` 与 `a7c2-qemu/docs/`）：
  1. **动态链接 `busybox` 的“绝症陷阱”**：`/bin/busybox` 与 `/bin/sh` 在 BIONZ XR 相机上为**动态链接**；若 `/etc/ld.so.preload` 指向损坏/架构不匹配的 `.so`，`busybox` 无法启动 `/sbin/init`，形成“无软件可救”的绝对死锁。因此恢复只能靠 BootROM 串行注入或 `nflasha1`，绝不能依赖已坏系统的 `Jiritsu`。
  2. **`nflasha10`（12 MiB VFAT）满盘锁定错误 `0x10000009`**：`/tmp`、`/etc`、`/var` 共享同一块 12 MiB 分区，一旦写满所有写接口同时报 `0x10000009`；写入必须最小化（1–2 字节级或整分区原子刷写）。
  3. **虚拟蓝牙与跨平台 IPC 边界**：`a7c2-qemu` 2026-11-08 通过 `virtual-rom-v1` 虚拟蓝牙控制器使原厂 BSA 成功初始化，否则原生应用将直接弹出“系统出错”；而 [`PORTING-WIN-MAC.md`](https://github.com/chocotan/a7c2-qemu/blob/main/PORTING-WIN-MAC.md) 论证了该方案在 macOS Quartz GTK 可移植性尚可，但 Windows 下因 `socketpair + pass_fds` 与 `bubblewrap` 缺失而受阻——这进一步体现了本实验室 `FX3/FX6 Web UI (127.0.0.1:8768)` + 无平台耦合 PNG/JSON 回读验证的跨平台优势。
- **`cokeenet/zve10-qemu` 内核诊断与 `L0–L4` 防砖系统**：
  - 贡献了可直接移植至 Sony 4.9 内核调试的 7 项补丁（`ZZTGKILL/ZZSTACK`、`ZZEXCSTACK`、`IMOPEN/MODLOAD`、`MISSSO/MISSDEV`、`ZZFUTEX`、`ZZCOMPLETE`、`QMMAP`），并纠正了早期文档误区（`issue #4` 证实 `nflasha15` 为**未压缩 `ext2`**，可持久化写入），同时揭示 `TIMER-IP` 3 分 40 秒硬件看门狗需 `WDT_SET_STOP` 清除。
- **[`Liwenru88/a7r5-rea`](https://github.com/Liwenru88/a7r5-rea) 与 [`OpenIPC/qemu-bench`](https://github.com/OpenIPC/qemu-bench)**：
  - `a7r5-rea`（面向 Apple Silicon macOS `v4.19`）在 QEMU 内完成 86 次 Qt 真实按键与双组快门声验证，并给出了极有价值的 **WBI (`p5`) 安全审计**：即使全功能包将 WBI 首 512B 失效处理（CRC `dfa823fc`），其明确标记 WBI 休眠与 NOR 擦写为未闭环边界——与本实验室 [`STAGE-A-HARDWARE-RUNBOOK.md`](../../docs/STAGE-A-HARDWARE-RUNBOOK.md) **红线 `R2`（严禁碰 `p5:/wbi` 与 `BIS` 休眠，FX6 `wbimem` 存在 `+13.47 MiB` DDR 碰撞）** 高度一致。
  - `OpenIPC/qemu-bench`（QEMU `v10.2.0`）则证明了以 **表驱动（table-driven）** 方式为 11 大家族 IP 摄像机 SoC 编写统一机器模型的工程可行性，支持在无原厂驱动源码下以 `mmz`/`cma` 映射引导原生内核。

### 2.3 异构 Linux AP + µITRON/TOPPERS RTOS CP 双 QEMU 通信：`IVSHMEM` 与 `OpenAMP` 演进

当前索尼相机 QEMU 仿真（包括 `a7c2-qemu`、`zve10-qemu` 及本实验室 Round 8）的最大共性瓶颈在于：**仅仿真了 AP（Linux），而将 CP（`CXD90058` / `cpapp-b.bin` RTOS）的 UIPC 响应在用户态 Stub**。2024–2026 年上游 QEMU 与嵌入式异构计算社区已经成熟给出标准解法：

1. **非对称双 QEMU 共享内存通道（`ivshmem-doorbell` + `ivshmem-flat`）**：
   - 在 **AP 端（`qemu-system-aarch64` Linux `virt`）** 挂载标准 PCI 设备 **`-device ivshmem-doorbell`**，通过 `uio_ivshmem` 暴露共享内存 BAR 与向量中断门铃。
   - 在 **CP 端（`qemu-system-arm` Cortex-R5/M 无 PCI 总线 MCU）**，利用 QEMU 上游合入的 **`ivshmem-flat`**（`hw/misc/ivshmem-flat.c`，专为 Linaro **HVAC** 异构汽车计算引入），直接将标准寄存器 **`INTRMASK`、`INTRSTATUS`、`IVPOSITION`、`DOORBELL`** 映射到物理 MMIO 地址空间，并与 `ivshmem-server` 通过 Unix socket + `eventfd` 互联实现跨进程实时中断唤醒。
2. **OpenAMP 与 `virtio-msg` 传输层**：
   - [`OpenAMP/openamp-system-reference`](https://github.com/OpenAMP/openamp-system-reference) 的 `examples/zephyr/dual_qemu_ivshmem` 与 Linaro `wmamills/hvac-demo`（`demo-amp-zephyr`）已验证基于 `ivshmem-server` 运行 `libmetal` + `VirtIO` + `RPMsg` 的双 QEMU 跨系统消息环，支持非对称核间低延迟信号量与 DMA 描述符传递。
   - 2026 年 5 月发布的 **`virtio-msg`**（`edgarigl/qemu` RFC 与 Linux `remoteproc-virtio-msg`）及 MemSys '25 的 **Secure IVSHMEM**（`<200 µs` 握手延迟、约 `5%` RTT 额外开销）证明此类通道完全可承载高实时性的 UIPC 队列（如 FX3↔FX6 共享 `0x92840747` 及独占阻塞队列 `0x92d2091c` / `0x91db059b`）。

---

## 第三支柱：硬件级救砖、Multi 口 BootROM 注入与 FX3 Wi-Fi/BT 防砖

### 3.1 Multi 口 `48000` 波特率 BootROM 免拆机救砖（FX3 专属硬件安全网）

与 ZV-E10、A6700、A7C II 等仅配单 USB-C 接口（无 Multi 接口，刷砖后必须拆机飞线主板测试点）的机型不同，**Sony ILME-FX3 完整保留了物理 15-pin Sony Multi/Micro USB 接口**！这使得 [`DavidBuchanan314/ILCE-7M4-RE`](https://github.com/DavidBuchanan314/ILCE-7M4-RE) 开创的免拆机硬件救砖链可直接移植至 FX3：

```text
[Host PC] --(USB)--> [RP2040-Zero: uart_boot.ino -DOPEN_DRAIN]
                        |-- GP27 (MULTI_RST)  --> Multi Back Row Pin 9 (XReset)
                        |-- GP28 (MULTI_TX)   --> Multi Back Row Pin 7 (Cam UART RX, 1.8V/3.15V OD)
                        |-- GP29 (MULTI_RX)   <-- Multi Back Row Pin 8 (Cam UART TX)
                        `-- GND               --- Multi Pin 2 (GND)
   │
   ▼  Step 1: 48,000 baud GPIO Bit-Banged UART 握手 (错码触发 0x100D = 13 短闪)
   ├──▶ 路线 A (官方签名 Fastboot 链 — Erlla / Hearts-Ace / SimplyPatrick):
   │      MEM_WRITE 加载 Sony 官方签名 fastboot.bin ("mira") 至 SRAM 0x92028000
   │      ──▶ 切换 115,200 baud 输出 "[mira] fastboot ready"
   │      ──▶ USB-C 枚举 Android Fastboot v0.5 (18D1:4EE0, getvar:version -> OKAY0.5)
   │      ──▶ 支持 Android Sparse (0xed26ff3a), oem partition, download/flash:nflasha1
   └──▶ 路线 B (无签名开放载荷链 — ILCE-7M4-RE push_payload.py):
          MEM_WRITE 加载自研载荷至 eSRAM 0xFE020000
          ──▶ SET_UNLOCK (0x0000): 栈指针溢出覆写 0xfe02f398 -> 0xdeadbeef (或真解锁码 0x2CF25621)
          ──▶ 启动 bare-metal payloads/fastboot: 支持 oem dumpbrom / oem partition dump
          ──▶ oem cetus reset/peek/poke/exec/dumpnor (直读/恢复 CXD90058 CP NOR!)
```

> [!IMPORTANT]
> **RP2040 硬件选型红线**：`ILCE-7M4-RE` 特别警告标准树莓派 Pico 将 `GP29` 连接到了内部 `VSYS/3` 电压分压器，直接接线会拉低电平导致握手失败；必须使用全引出 `GP27..29` 的 **RP2040-Zero**（编译 `-DOPEN_DRAIN` 启用开漏驱动保护 1.8V/3.15V 相机引脚）。对照 [`xyzhangxin/sony-a6700-powerful`](https://github.com/xyzhangxin/sony-a6700-powerful) 在 A6700 上仍需依赖特定触点/拆机线序，FX3 的物理 Multi 接口意味着**只要 Octal-SPI NOR 中的 48KB BootROM 与基础供电正常，任何 eMMC Sector 0、`nflasha1` 或 `p3` 软硬砖均可在不拧一颗螺丝的情况下通过 Multi 口救回**。

### 3.2 `nflasha1` 双层信任链、SD 卡槽 1 救砖与灯语诊断

[`Erlla/sony-a7m4-custom-firmware`](https://github.com/Erlla/sony-a7m4-custom-firmware)（`no-fastboot-install/IMPLEMENTATION.md`）与 [`Hearts-Ace/sony-a7r5-custom-firmware`](https://github.com/Hearts-Ace/sony-a7r5-custom-firmware) 完整披露了第 5 代机型 `nflasha1`（`/dev/cnflasha1` = `25,100,288` 字节 / `766` 块，内含 `19,377,152` 字节 FAT12/FAT16 恢复卷）的双层验签架构及对应最小补丁：

1. **双层验证流**：
   - `/boot/initrd.img`（SquashFS，受 `/p1chksum` 校验保护）内置 `/etc/VerificationKey.pem`（451B RSA-2048 公钥）；
   - 运行时先由 `Updater::SignatureVerification::verifyKey` 比对公钥哈希，再由 `VerifySignature` 对 `BODYDATA.DAT` 尾部 256B 执行 SHA-256 + RSA-2048 PKCS#1 v1.5 验签，并通过 `isVersionOK` / `chkFirmInfo_before` 检查降级与版本跨度。
2. **与本实验室 `fx3-recovery-adapter` 的字节级高度对齐**：
   - 本仓 [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) 独立对 **FX3 v2.04/v2.05 `p1` 载荷** 标定并验证的 4 处文件偏移（`libsdfileinputupdaterapi.so` `0x9fd4` `isVersionOK`、`0xabf0` `VerifySignature`；`libupdatercorecommon.so` `0xd208`、`0xd27c`），与 `Erlla` 在 A7 IV 上公开的 4 处补丁语义 **100% 同构**（A7 IV 偏移分别为 `0x9FD4`/`0xABF0` 与 `0xD208`/`0xD27C`！甚至在两代机型上的相对编译偏移完全重合），且双双独立采用 **SquashFS `Z_SYNC_FLUSH` 等长重打包**（保持 `/boot/initrd.img` 原长以不破坏 FAT 簇链）与 **600 秒 RAM 菜单门控自动回退**（`libupdaterufp.so +0x1F50`, `appFw.so +0x265B2C8`）。
3. **SD 卡槽 1 恢复灯语矩阵**（已集成至 [`brick_classifier.py`](../../outputs/fx3-safety/fx3_safety/brick_classifier.py)）：
   - **`1 -> 3 -> 5` 闪烁**：正常升级/恢复进度推进；
   - **`5 长 + 6/7 短 (5L+6S)`**：`sdfileinput.elf` 拒绝 `BODYDATA.DAT`（版本跨度不足，如 FX3 `<=v2.02` 跳过 `v2.04/v2.05` 跳板包直刷 `v7.02`、同版本未置 `mode6`、FX3 `0x91030080` 与 FX3A 包混淆、或 Creators' App 无线传输截断）；
   - **`7 长 + 7 短 (7L+7S)`**：`/setting/updater/mode*` 已置位但槽 1 缺失合法 `BODYDATA.DAT`（通常需断电+60 秒放电+标准 32/64GB UHS-I 卡重写恢复）；
   - **`6 长 (6L)` 或 `6L+9S` / 红灯常亮**：子部件校验失败——高度关联 CP NOR 或 **WF-12 Wi-Fi/BT 硬件模块故障**。

### 3.3 FX3 Wi-Fi/BT 模块启动自检死循环（`00342260`）与 Stage-A/B 防护策略

2025–2026 年索尼 FX3（v3.00–v7.02）、FX30 与 A7S III 爆发了大规模无线模块故障相关的伪“软件变砖”现象：
- **索尼官方技术通告 [`Article ID: 00342260`](https://www.sony.com/electronics/support/articles/00342260)（2026-01-20 更新）**：索尼正式确认新版固件在开机/开启无线时对 Wi-Fi/Bluetooth 模块执行严格硬件健康检测；一旦检测到硬件异常，新版（如 v7.02）弹出 *"The Wi-Fi/Bluetooth unit has malfunctioned."* 并允许按 OK 后继续无网络拍摄；但此前的中间版本（v3.00–v5.00）常直接触发 **`"System Error"` 并在开机 5–10 秒后陷入无限重启死循环**（断电开关无效，必须拔电池；部分用户通过开机抢进菜单开飞行模式或插入 Slot 1 恢复卡待 20 分钟解冻），售后通常报价更换整块 `SY-1114` 主板（约 USD 800–1,600）。
- **版本跃迁与 LUT 升级踩坑**：FX3 历史还出现过 v6.00->v6.01 自定义 LUT 引发的升级失败（v6.02 修复），及 v6.00/v6.02 升级后红灯常亮/`6L+9S` 死机。
- **对 FX6-on-FX3 Stage-A/B 移植的直接工程映射**：
  - FX6 机身具备独立的扩展无线/有线接口与远程面板逻辑，而 FX3 `WF-12` Wi-Fi/BT 模组本身存在虚焊/老化易发故障风险。
  - **若未来 Stage-A/B 在真机上尝试挂接或保留网络/无线初始化**：一旦 `appFw.so` 或 `libInfraPericon.so` 对无线/远程板执行同步 `model_future::wait` 或阻塞轮询，一台无线模块轻度退化的 FX3 真机在冷启动 Stage-A 时就会被误判成系统级死机或卡死在开机链！
  - 本实验室当前已在 [`patcher.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/patcher.py) 通过 **`P3` (`libInfraAppRemoteBoard.so` `0x157c`/`0x1700 -> mov w0, #0; ret`)** 裁剪了远程面板线程，并在 [`ap_cp_imaging_pipeline_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/ap_cp_imaging_pipeline_verifier.py) 隔离了 `0x92d2091c`（RTC `std::future` 阻塞）与 `0x91db059b`（智能手柄队列）；**下一步 Stage-B 必须将同样严格的“非阻塞 + 降级容错（Degraded Mode）”契约显式扩展至 Wi-Fi/BT (`WF-12`) 与 `SeqQueueNetwork` / `InfraPericon` 链路**，确保任何无线子系统超时均只记录降级日志，绝不阻塞 `Application_System_Init` 或触发看门狗复位。

---

## 第四部分：FX3↔FX6 Lab Architecture Alignment & Next-Phase Upgrade Roadmap

下表将全球外部社区最新研究进展（State-of-the-Art）与本实验室五大核心交付模块进行逐一横向工程对齐，识别“我方领先项”、“外部交叉印证项”与“可立即吸收升级项”：

| 技术域 / 维度 | 外部社区最新进展 (2025–2026 SOTA) | 本实验室现有工程实现与验证基线 (`outputs/` & `docs/`) | 对齐判定 & 下阶段升级动作 (Next-Phase Action) |
| :--- | :--- | :--- | :--- |
| **1. 安全红线与防砖架构** | • `zve10-qemu` `L0..L4` 防砖 (`/log` bind + 90s 看门狗 + `mode6`)<br>• `a7c2-qemu` 警告动态链接 `busybox` 的 `ld.so.preload` 死锁<br>• `a7r5-rea` 标记 WBI (`dfa823fc`) 边界<br>• `pmca-re-reloaded` 5 步护栏 + `dd conv=notrunc` 警示 | [`outputs/fx3-safety/`](../../outputs/fx3-safety/README.md) & [`STAGE-A-HARDWARE-RUNBOOK.md`](../../docs/STAGE-A-HARDWARE-RUNBOOK.md)：<br>• 12-Gate 门禁 (`9 VERIFIED / 3 BLOCKED`，硬锁 `G12 persistent_write_release=False`)<br>• `brick_classifier.py` 5 级故障 + `5L+6S`/`7L+7S`/`6L` 诊断<br>• 4 层自撤防 `tmpfs` `/tmp/mod_arm_once` Clear-Before-Exec<br>• 绝对红线 `R1..R5`（严禁 `edisx`/Sector 0、严禁 `p5:/wbi`、严禁 `p8:/cp`、强制 `U5` 双步退出） | **我方大幅领先（全栈可机读门禁）**。<br>**升级项**：将 `WF-12` Wi-Fi/BT 硬件非阻塞自检与 `00342260` 降级状态机纳入 `Stage-B` Gate 检查与 `detect_serial_faults.py`。 |
| **2. `nflasha1` 恢复与 Tier-0 离线适配器** | • `Erlla` & `Hearts-Ace`：A7M4/A7R5 `nflasha1` 4 处补丁 + SquashFS 重打包 + `600s` RAM 门控<br>• `pmca-re-reloaded` `v1.12.1`：macOS 26 `IOUSBHost` 修复 + Senser v2 检测 | [`outputs/fx3-recovery-adapter/`](../../outputs/fx3-recovery-adapter/README.md)：<br>• FX3 `2.04/2.05` `p1` 4 处同构偏移（`0x9fd4`/`0xabf0`/`0xd208`/`0xd27c`）+ `Z_SYNC_FLUSH` 等长重压<br>• 独立静态 `AArch64` ELF 捕获器 (`fx3_p1_reader.c`, `fx3_boot_reader.c` + `elflink.py`) `58` 测试通过 | **外部 100% 交叉印证偏移同构性**。<br>**短板/升级项**：待 Phase H0 实机读取 **FX3 v7.02 本机 `p1` 指纹**（当前仅为 2.04/2.05）；并吸收 `pmca-re-reloaded` 的 **macOS 26+ `IOUSBHost` 回退捕获逻辑** 与 **Senser v2 检测** 至主机侧 USB 工具链。 |
| **3. 跨机型移植闭环 (`FX6 -> FX3`)** | • `YuuLuo` / `QAQLeonard` / `t2r05` / `leogenot`：通过 `054C:0336` + `libJit.so` 临时改内存表或写 `BK4` 单个属性（多受限于宿主 `HAITA` 与 `menu_item` 缺页）<br>• 2026-10 A7S III `libJit.so` BIG6 PoC 仍需逐项手补菜单状态 | [`outputs/fx6-on-fx3-closure/`](../../outputs/fx6-on-fx3-closure/README.md)：<br>• Phase 1–18 全量闭环：`P1..P10 + Fan` 适配矩阵、43 节点 `DT_NEEDED` 闭包、`U1..U5` 全部 `CLOSED`<br>• `30-stage-a-orchestrator.sh` Verify-Before-Mount (`30,956 B` `cpio newc`) + `verify-post-trial` H0→H1→H2 零漂移审计 (`224` 项自动化测试) | **我方路径本质领先（整套 Cinema Line FX6 UXEngine 原生迁移而非单点 Hack）**。<br>**互证项**：`leogenot` `PRODUCT_CLASS.md` 实证 `ALCIN_UUD`=`FX3`、`LAX`=`FX30`；**升级项**：在 `Stage-B` 中为 `WF-12` / `InfraPericon` / `SeqQueueNetwork` 增加非阻塞超时隔离补丁。 |
| **4. QEMU 虚拟化与原生界面仿真** | • `a7c2-qemu`：软件 GPE + `sony-lz77.c` + `ramfb` (`97.3ms`) + `virtual-rom-v1` 虚拟蓝牙，运行原厂 `init` 至中文菜单<br>• `zve10-qemu`：70 模块 + 43 UIPC 处理器<br>• `a6400-research`：Sugilite `BAR 0xF1000000` + `CC:` 3D LUT | [`outputs/fx3-vm-trial/`](../../outputs/fx3-vm-trial/README.md) & [`outputs/fx6-native-presenter-closure/`](../../outputs/fx6-native-presenter-closure/README.md)：<br>• Round 5–7：`FX6_NATIVE_FAITHFUL=1` (`nop_count=0`) + `RGBA4444` 修复 + `InfraInput` 全键盘/拨盘 + `"S-Cinetone"` 1,928px 实写回读<br>• **Round 8**：**FX3 Ver. 7.02 真内核 (`4.9.337-scel+`) + Stage-A 混合冷启动 E2E 跑通** (`148 TIDs`, `r8a/r8b`) | **我方 Round 8 在跨机型内核+应用混跑与像素级忠实度上领先**。<br>**升级项**：借鉴 `a7c2-qemu` 引入 **`sony-lz77.c` 软件解码对比基线**（避免依赖硬件 `/dev/ldec`）及 `virtual-rom-v1` 轻量蓝牙控制器模型用于验证无线防砖分支；保留 `127.0.0.1:8768` Web UI 低延迟独立通道。 |
| **5. 异构 AP↔CP 与硬件级底层救砖** | • **双 QEMU 异构**：`OpenAMP` `dual_qemu_ivshmem` + QEMU `ivshmem-flat` + `virtio-msg`<br>• **硬件救砖**：`ILCE-7M4-RE` Multi 口 `48000` 波特率 `uart_boot` (RP2040-Zero) -> `0x92028000` / `0xFE020000` `18D1:4EE0` Fastboot + `oem cetus dumpnor` | • 目前 Stage-A 采用 **Stock-CP 红线 + AP 侧队列合成** (`0x92d2091c` / `0x91db059b` 补全 `44/44` `0x92840747` 操作码)<br>• `brick_classifier.py` 已建模 Multi 口 `uart_boot` 作为 Level 4 终极救砖方案，但主机端工具链与实机引脚线束尚未落装测试 | **下一阶段最大战略增量（High-Leverage Upgrades）**：<br>1. **P0（救砖物理兜底）**：制作 **FX3 Multi 口 + RP2040-Zero (`-DOPEN_DRAIN`) 救砖线**，完成 `48000` 波特率握手测试与 Tier-0 同机冷备份（`Gate G10` 解锁前置）。<br>2. **P1（双 QEMU 异构仿真）**：利用 QEMU `ivshmem-doorbell` (AP `cortex-a35`) + `ivshmem-flat` (CP `Cortex-R5` 承载 FX3 `cpapp-b.bin`) 验证真实 AP↔CP UIPC 时序，彻底消除人工 Stub 假设。<br>3. **P2（无线硬件防砖门控）**：在 QEMU 中注入蓝牙/Wi-Fi 故障注入测试，验证 FX6 `appFw.so` 在无物理 `WF-12` 响应时 100% 进入安全降级模式而不死循环。 |

---

## 第五部分：下阶段工程落地路线图 (Next-Phase Engineering Roadmap)

1. **Milestone H3（硬件零风险前置保障 —— Multi 口 Fastboot + Tier-0 只读核验）**：
   - 按 `ILCE-7M4-RE` `uart_boot.ino`（`RP2040-Zero`, `-DOPEN_DRAIN`）制作并离线测试 FX3 Multi-Terminal 1.8V 调试桥（仅在已砖/授权测试体或先做 `uart_boot_probe` 只读握手验证）；同时使用 `pmca-re-reloaded` 的 macOS 26+ `IOUSBHost` 兼容策略完善本实验室主机侧工具链，完成 FX3 v7.02 实机 **11+2 项 Tier-0 只读备份 (`Gate G10`)**，取得真机 `p1` 指纹加入 `fx3-recovery-adapter` `profiles.py`。
2. **Milestone H4（QEMU 异构双 VM 联合仿真 —— `IVSHMEM` + 无线降级压测）**：
   - 在隔离实验分支构建 `qemu-system-aarch64`（FX3 7.02 Linux AP + `ivshmem-doorbell`）与 `qemu-system-arm`（RTOS/Cortex-R5 承载或桥接 FX3 Stock `cpapp-b.bin` + `ivshmem-flat`）双机原型，实测 `0x92840747` UIPC 跨 VM 零假定交互；同步复刻 `a7c2-qemu` 的异常硬件模型，对 `WF-12` Wi-Fi/BT 超时、断开、固件错误返回注入故障测试，确保 Stage-A/B 在任意无线异常下 100% 免疫 `00342260` 级死循环。
3. **Milestone H5（真机非持久 Stage-A 首飞 `H0 -> H1 -> H2`）**：
   - 在 `Gate G10` 物理解锁后，严格依 [`STAGE-A-HARDWARE-RUNBOOK.md`](../../docs/STAGE-A-HARDWARE-RUNBOOK.md) 执行 `make readiness-packet` -> `30-stage-a-orchestrator.sh`（10 步 `tmpfs` RAM-Overlay，`0` 字节持久化写入）-> 断电恢复 -> `verify-post-trial` 密码学零漂移审计，形成可审计的真实相机 Stage-A 闭环凭证。

---

## 参考源索引 (Primary References)

1. BootROM / Hardware Fastboot / Custom Firmware:  
   - [`DavidBuchanan314/ILCE-7M4-RE`](https://github.com/DavidBuchanan314/ILCE-7M4-RE) · [`DavidBuchanan314/Sony-ILCE-7M4-Linux`](https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux)  
   - [`Erlla/sony-a7m4-custom-firmware`](https://github.com/Erlla/sony-a7m4-custom-firmware) · [`Hearts-Ace/sony-a7r5-custom-firmware`](https://github.com/Hearts-Ace/sony-a7r5-custom-firmware)  
   - [`xyzhangxin/sony-a6700-powerful`](https://github.com/xyzhangxin/sony-a6700-powerful) · [Simply Patrick A7R V 逆向实录](https://simplypatrick.com) · [Sony Notice `00342260`](https://www.sony.com/electronics/support/articles/00342260)
2. QEMU Camera Virtualization & Heterogeneous IPC:  
   - [`chocotan/a7c2-qemu`](https://github.com/chocotan/a7c2-qemu) · [`cokeenet/zve10-qemu`](https://github.com/cokeenet/zve10-qemu) · [`Liwenru88/a7r5-rea`](https://github.com/Liwenru88/a7r5-rea)  
   - [`ivica00/sony-a6400-research`](https://github.com/ivica00/sony-a6400-research) · [`OpenIPC/qemu-bench`](https://github.com/OpenIPC/qemu-bench)  
   - [QEMU `ivshmem-flat` Docs](https://www.qemu.org/docs/master/system/devices/ivshmem-flat.html) · [`OpenAMP/openamp-system-reference`](https://github.com/OpenAMP/openamp-system-reference) · [`wmamills/hvac-demo`](https://github.com/wmamills/hvac-demo)
3. Firmware Unpacking, `HAITA` Gating & USB Service Mode:  
   - [`OlliV/fx30_fw`](https://github.com/OlliV/fx30_fw) · [`leogenot/sony-a7iv-feature-research`](https://github.com/leogenot/sony-a7iv-feature-research)  
   - [`masterflai/pmca-re-reloaded`](https://github.com/masterflai/pmca-re-reloaded) ([项目主页](https://masterflai.github.io/pmca-re-reloaded)) · [`YuuLuo/a7c2-service-preload`](https://github.com/YuuLuo/a7c2-service-preload)  
   - [`QAQLeonard/a7c2-fl23-research`](https://github.com/QAQLeonard/a7c2-fl23-research) · [`t2r05/fx30-senser-map`](https://github.com/t2r05/fx30-senser-map) · [`dino2048/zv-e10-toolkit`](https://github.com/dino2048/zv-e10-toolkit) · [`ChambersXDU/sony-a7c2-research`](https://github.com/ChambersXDU/sony-a7c2-research) · [`goudvuur/sonshell`](https://github.com/goudvuur/sonshell) · [`happyfrog2026/a7m4-color-research`](https://github.com/happyfrog2026/a7m4-color-research)
