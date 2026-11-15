# FX3 Mac 最小研究虚拟机

当前可在这台 Apple Silicon Mac 上用原生 QEMU/TCG 运行 **经典 FX3 7.02 的原 Linux 内核与最小原用户态**。已分别验证原 BusyBox/`uname`，以及原动态加载器对 `bootin.elf`、`im.elf` 的 verify/list。相机菜单、CP/IPC、CMOS/ISP、照片与录像尚未接入。

## 运行

双击本目录 [启动FX3最小研究虚拟机.command](启动FX3最小研究虚拟机.command)。终端运行约 12 秒后正常退出，显示状态和日志路径。该 `.command` 是可审阅的终端入口，不是图形相机界面。

也可使用本机已安装的 Python 3（优先探测 `$FX3_PYTHON`、`~/.local/bin/python3`、系统 `python3`）：

```sh
python3 outputs/fx3-vm/run_probe.py --self-check
python3 outputs/fx3-vm/run_probe.py --profile minimal-linux --seconds 12
python3 outputs/fx3-vm/run_probe.py --profile app-loader --seconds 12
```

`--seconds` 是宿主机壁钟观察窗，可设 1–30 秒。未满足标记或出现 guest exception 时退出码为 2，不把 QEMU 自身正常退出当作 FX3 启动通过。运行中按 Ctrl-C 会收尾所属 QEMU 子进程。日志位于 `work/fx3-vm-20261101/host/runs/a-<8位ID>/`。

| profile | 实际验证的终点 | 保留的边界 |
|---|---|---|
| `minimal-linux` | 原内核启动 → 原 BusyBox 执行自写最小 `/init` → 原 `uname` → 完成标记 | 七个未建模硬件初始化入口被明确禁用；未执行 Sony 原 `/init` |
| `app-loader` | 同一原内核 → 原动态加载器对原 bootin/im 各执行 `--verify`、`--list`，四项返回 0 | 20 份原 ELF、88 条依赖闭包；不进入应用 main/constructor，不代表菜单运行 |

## 模型与固定输入

软件模型只新增 4 KiB ESRAM mailbox `[0xfe005000,0xfe006000)`，把 2 GiB 主 RAM 的物理基址放到 Sony 原有 `0x400000000`，并通过实验 DTB 把原固定 GICD 虚拟地址映到 QEMU 的真实 GICD。物理地址基址 16 GiB 不等于分配 16 GiB 内存。没有外设 catch-all、伪造 IRQ 成功或内核 NOP。

`manifest.json` 明列七个禁用 initcall：hwtimer、wdt、FUSB、PCIe、DDRC、PCI DMA、Sony USB。它们在这个最小配置中没有设备模型，不能据内核/用户态结果提升整机硬件兼容性。

QEMU、glib、pcre2、intl 的运行闭包在 `bin/` 和 `lib/`，采用相对 dylib 链接，去除了构建目录 RPATH。初始及最终签名没有 entitlements；按本机 ad-hoc 重新签名，并用最终二进制实际执行 TCG 验证。构建树不是运行依赖。

实验 DTB 和最小 CPIO 在 `share/`；CPIO 中原 ELF 均从本机已经解包的自有固件逐字节引用，无完整 BODYDATA.DAT 或完整分区。原内核只读引用：

```text
~/AI-Workspace/AI/Projects/Mac/work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin
SHA256 da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c
```

入口按需核对内核与运行文件 SHA（若显式回退外盘路径则核对卷 UUID）；有缺失/变化会停止。未连接相机或手机；运行参数不提供网卡、USB/宿主磁盘/宿主目录透传。当前验收是短时运行，长期稳定性未验证。

## 证据与来源

- [固定运行清单](manifest.json)
- [最终运行验证](metadata/final-runtime-validation.json)
- [Mach-O 依赖与相对链接前后摘要](metadata/runtime-relocation.json)
- [删除构建目录 RPATH 的记录](metadata/rpath-removal.json)
- [QEMU 构建与固定源](metadata/build-provenance.json)
- [两项明示内存模型源码补丁](source-patches/fx3-esram-high-ddr.patch)
- [QEMU GPL 文本](COPYING-QEMU)

研究材料和旧失败原件保留在本项目 `work/fx3-vm-20261101/`。原菜单部署仍需 FX3 专属 AP/CP、IPC、设置/Backup、输入和显示模型；本入口没有生成可刷入修改固件。

## 独立 AP 入口 alpha 附录

默认两profile验收之外，另用同一最终QEMU尝试原 `im.elf target=qemu`，guest进程限2秒、宿主观察12秒。实际报告 `open /dev/uipc error: No such file or directory` 后退出，原wait RC为133；未出现kernel panic，所属QEMU已回收。syscall trace不可用，未证明到达应用main或显示菜单，未将该返回值解释成ABI不兼容。

这给出下一处具体环境缺口：Sony UIPC设备与服务模型。默认运行包/profile保持不变，当前停止追加仿真修复轮。`~/AI-Workspace/AI/Projects/Mac/work/fx3-vm-20261101/host/ap-entry-alpha-summary.json`。

## 离线补丁与溯源自动化校验

本目录的 `source-patches/fx3-esram-high-ddr.patch`（`0xfe005000` ESRAM 与 `0x400000000` 高位 DDR 统一 diff 行数与映射校验）、`COPYING-QEMU`、`manifest.json`、`metadata/*.json` 全量 6 份 `@loader_path` / `LC_RPATH` 清除溯源记录，以及 `run_probe.py` 语法与隔离参数契约已纳入离线单测套件 [`outputs/fx3-vm-trial/tests/test_vm_trial.py`](../fx3-vm-trial/tests/test_vm_trial.py)（不拉起 QEMU，不依赖专有二进制，可通过仓库根目录 `make test` 一键执行）。

## Phase 24：双指令集（`CXD90057` AArch64 AP ↔ `CXD90058` ARM32 Thumb-2 Stock-CP）`IVSHMEM` 协同仿真桥

[`dual_ap_cp_ivshmem_bridge.py`](dual_ap_cp_ivshmem_bridge.py) 在不触碰 `run_probe.py`、`manifest.json` 与 `8768` 端口的前提下，构建了洁净室兼容的 **Dual-ISA Unicorn 协同仿真引擎** 与 **外部双 QEMU `ivshmem-doorbell` / `ivshmem-flat` 拓扑生成器**：

- **Peer 0（AP `Mira` / `CXD90057` / `UC_ARCH_ARM64`）**：`ivshmem-doorbell` BAR0 MMIO（`0x1000_0000`：`INTRMASK=0x00`、`INTRSTATUS=0x04`、`IVPOSITION=0x08`、`DOORBELL=0x0C`）+ BAR2 共享内存（`0x1010_0000`，1 MiB 零拷贝 `ctypes` `mem_map_ptr`）。真实执行 AArch64 机器码完成 `P11` AP 侧隔离过滤（`0x92d2091c` `/dev/rtc0` 与 `0x91db059b` Smart Handle 永不进入 TX Ring）及 `0x92840747` TX 入队 + Doorbell `(1 << 16) | 0`。
- **Peer 1（Stock-CP `Cetus` / `CXD90058` / `UC_ARCH_ARM | UC_MODE_THUMB`）**：`ivshmem-flat` MMIO（`0x6780_0000`）+ 共享内存（`0x6790_0000`），将未修改的 FX3 v7.02 `cpapp-b.bin` 以只读/可执行（`UC_PROT_READ | UC_PROT_EXEC`，`cp_mutation_bytes == 0`）映射至 `0x0010_8000`。真实执行 ARM32 Thumb-2 中断服务例程，直接读取映射的 `cpapp-b.bin` 内存校验 `0x0010800c` 基址字面量、`0x92840747` `MOVW/MOVT` 队列常量与完成表常量，处理 `33^3` 3D LUT DMA（`0x0165` > `0xbb80` / `0x0166`）、Cine EI 双原生 ISO（`800`/`12800`）与 5 轴 IBIS 语音线圈中心锁定（`Off`/`Standard`/`Active`），回写 `opcode | 0x8000` 完成包至 RX Ring 并回敲 Doorbell `(0 << 16) | 0`。
- **双模式洁净室运行**：本地只读（`O_RDONLY` + `bytes.find`）读取 FX3 `cpapp-b.bin`、FX6 `appFw.so`、`libosal_uipc.so`；当设置 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或缺失供体时自动切换至确定性合成 `[TOMCO]` + `AArch64` + `Thumb-2` 固件。

### Phase 24 运行与测试命令

```sh
# 1. 本地只读供体模式运行 Dual-ISA 协同仿真自检（< 0.5s）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/dual_ap_cp_ivshmem_bridge.py

# 2. 洁净室合成模式（无本地供体依赖）
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/dual_ap_cp_ivshmem_bridge.py --json

# 3. 导出外部双 QEMU（ivshmem-server + ivshmem-doorbell + cortex-r5 ivshmem-flat）CLI 拓扑
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/dual_ap_cp_ivshmem_bridge.py --topology

# 4. 运行 Phase 24 + Phase 29 全量 47 项单测（本地供体模式 & 洁净室模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v
```

## Phase 29：无硬件依赖软件 GPE 光栅/精灵合成引擎与 `virtual-rom-v1` 蓝牙 HCI UART 仿真器

[`soft_gpe_and_bt_rom_emulator.py`](soft_gpe_and_bt_rom_emulator.py) 在严格遵循只读（`os.O_RDONLY`）与零持久化写入（`WBI_MUTATION_BYTES=0`、`CP_MUTATION_BYTES=0`、`NVRAM_PERSISTENT_WRITES=0`）前提下，落地了两项核心虚拟化参考模型：

1. **Part A — 软件 GPE（`GRM_gpermFillrect` / `GRM_gpermRectblit` / `HOSDAP02` / `ramfb`）光栅合成参考引擎**：
   - 建模 `1024×540` `GPE0`（`0x41E001000`）与 `ramfb`（`[0x41E100000, 0x41E600000)`）扫描输出管线，完整实现 `Fillrect`、`Rectblit`（含缩放与裁剪）、9-patch 边角拉伸（直接解析 `image_00_169.uxc` 实机 `left/top/right/bottom` 嵌入边距）与 Porter-Duff `SRC_OVER` / `SRC_COPY` 混合。
   - 覆盖 `RGBA4444`、`ARGB4444`、`RGBA8888` 与 `A8` 字形遮罩（`0x0E` 着色）四大像素格式，并严格对齐 [`libgrm-fbinit25-542.c`](../fx3-vm-trial/src/libgrm-fbinit25-542.c) 与 [`fx6_next_stage_assist_log.c`](../fx3-vm-trial/src/fx6_next_stage_assist_log.c) 的 `fx6_px`（`0xAARRGGBB` / 小端 `[B,G,R,A]`）R/B 通道打包约定（琥珀色采样 `0xFFF08018` 比特精确一致）。
   - 使用纯 CPU Sony LDEC/LZ77（`0x0F` raw + `0xF0` 回溯匹配）只读解码 FX6 `image_00_169.uxc`（`1,610` 精灵含 `22` 项 9-patch），在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或缺失供体时自动切换确定性合成 `uxd\x07` 夹具。
2. **Part B — `virtual-rom-v1` 蓝牙 HCI H4 UART（`/dev/ttyAMA3`）状态机仿真器**：
   - 只读（`os.O_RDONLY`）核验 FX6 `libbt-vendor.so`（`47,968 B`）与 `libInfraBluetoothCore.so`（`267,576 B`）中的 `/dev/ttyAMA3` 与 `BSA` 初始化标记（洁净室模式下自动使用合成 ELF64 夹具）。
   - 实现完整 H4 UART 分帧与命令应答器（`HCI_Reset 0x0C03`、`HCI_Read_Local_Version_Info 0x1001`、`HCI_Read_BD_ADDR 0x1009`、Broadcom/Cypress `0xFC2E`/`0xFC4C`/`0xFC4E` PatchRAM 与 `0xFC18` 波特率切换 `115200 -> 3000000`），并覆盖 4 种确定性运行模式：
     - `HEALTHY_VIRTUAL_ROM_V1`：完整 `BSA` 建链成功（`0` 错误，确定性 `BD_ADDR = 58:36:57:00:29:01`）。
     - `UART_DISCONNECTED_TIMEOUT`：死串口返回 `0` 事件，验证 `P12` `BT_DEGRADED_DISABLED`（`0x0BB9` / `3001`）非致命降级。
     - `PATCHRAM_CORRUPT_NACK`：模拟固件下发中段 `WF-12` NACK（`0x0C` + `HCI_EVT_HARDWARE_ERROR 0x10`），验证索尼 `00342260` 飞行模式锁存防死循环隔离（`0` WDT 复位）。
     - `AIRPLANE_SHADOW_GATED`：Stage-A/B RAM-Shadow `BK4\0`（`0x019e0012=00`、`0x01a20002=00`）激活时门控 `0` 条 HCI 发送、`0` 字节 UART 写入。

### Phase 29 运行与测试命令

```sh
# 1. 本地只读供体模式自检（< 0.5s）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/soft_gpe_and_bt_rom_emulator.py --json

# 2. 洁净室合成模式自检（< 0.3s）
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/soft_gpe_and_bt_rom_emulator.py --json

# 3. 运行 Phase 24 + Phase 29 + Phase 33 全量 71 项单测（本地供体 & 洁净室双模式，< 3s）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v
```

## Phase 33：全板级虚拟相机协同仿真统一编排器与 CLI（`fx3_vm_coemulation_suite.py`）

[`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py) 将 `outputs/fx3-vm/` 内的冷启动基线、Bluetooth UART、Dual-ISA `IVSHMEM` 协处理器与软件 `GPE0`/`ramfb` 合成管线整合为单入口、确定性、洁净室兼容的全板级虚拟相机冷启动与拍摄周期编排器：

1. **Stage 1 — AP 冷启动基线与 `virtual-rom-v1` `/dev/ttyAMA3` 蓝牙建链（含 P12/00342260 退化隔离）**：
   - 只读（`os.O_RDONLY`）核验 [`manifest.json`](manifest.json) 与 [`run_probe.py`](run_probe.py) 基线（`2048 MiB`、`FX3_VM_ESRAM_RAM=1`、`FX3_VM_HIGH_DDR=1`、`7` 项禁用 initcall），并检查 FX6 `libbt-vendor.so` / `libInfraBluetoothCore.so` 标记（洁净室模式下切换合成 ELF64 夹具）。
   - 执行目标模式（`HEALTHY_VIRTUAL_ROM_V1`、`UART_DISCONNECTED_TIMEOUT` → `P12` `0x0BB9`、`PATCHRAM_CORRUPT_NACK` → `00342260` 飞行模式锁存、`AIRPLANE_SHADOW_GATED` → `BK4\0` 门控）及 4 模式防砖矩阵验证。
2. **Stage 2 — Dual-ISA `AArch64` AP ↔ `IVSHMEM` ↔ `ARM32 Thumb-2` Stock-CP 拍摄闭环**：
   - 运行 `P11` AP 侧隔离过滤（`0x92d2091c` `/dev/rtc0` 与 `0x91db059b` Smart Handle 零泄漏至 CP），以及跨 `0x92840747` Doorbell/Flat 的 ProCam（`0x0416`）、Cine EI 双原生 ISO（`800 / 12800`：`0x0169` / `0x016A`）、`33^3` 3D LUT DMA（`0x0165 > 0xbb80` + `0x0166`）与 5 轴 IBIS 中心锁定（`0x0400`：`Off` / `Standard` / `Active`），全程强制 `cp_mutation_bytes == 0`。
   - 证明 Stage 1 任意蓝牙退化/隔离模式均不阻断 Stage 2 拍摄与成像流水线（`shooting_unaffected = True`）。
3. **Stage 3 — 软件 GPE0（`0x41E001000`）+ `ramfb`（`0x41E100000`）`1024×540` HUD + Big-6 合成**：
   - 以 `os.O_RDONLY` 只读解码 FX6 `image_00_169.uxc`（`1,610` 精灵含 `22` 项 9-patch；洁净室模式自动切换合成 `uxd\x07` `5` 精灵），结合 Stage 1 BT 状态徽章与 Stage 2 Cine EI / LUT / IBIS 遥测合成完整 `1024×540` HUD + Big-6 帧，校验 `fx6_px`（`0xFFF08018`）R/B 通道对齐、`gpe0->gpe1` 刷新一致性与 `HOSDAP02` `ramfb` `XRGB8888` 扫描输出。

### Phase 33 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式输出确定性 JSON 审计摘要
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py

# 2. 洁净室合成模式输出确定性 JSON 审计摘要（支持 --bt-mode / --cine-ei-iso / --lut-mode / --ibis-mode / --summary）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --clean-room
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --clean-room --summary

# 3. 运行 outputs/fx3-vm 全量 155 项单测（Phase 24 22 项 + Phase 29 25 项 + Phase 33 24 项 + Phase 41 28 项 + Phase 45 28 项 + Phase 53 28 项，< 4.5s）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v
```

## Phase 41：QEMU CXD90057 纯 Python FDT/DTB 合成器、`mhlx`/`ipcu` 硬件邮箱环与 `0xf0000000..0xf8ffffff` MMIO 窗口仿真器

[`cxd90057_dtb_and_mhlx_emulator.py`](cxd90057_dtb_and_mhlx_emulator.py) 为 `outputs/fx3-vm/` 补齐了纯 Python 设备树编解码、SoC 外设 MMIO 窗口总线与 `mhlx`/`ipcu` 邮箱/冷热启动握手能力，并作为可选/默认 **Stage 4** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（`--skip-phase41` 可跳过）：

1. **只读（`os.O_RDONLY`）FX3 v7.02 / FX6 v6.01 内核与模块 MMIO 契约审计 + 洁净室回退**：
   - 本地供体存在时以严格 `os.O_RDONLY` 检视 `vmlinux.bin`、`cxd90057.dtb`（`17,131 B`）、`osal_uipc.ko`、`utimer.ko`、`elpspacc.ko`、`elpspaccusr.ko`、`grm_ma.ko`、`pcie-if.ko`、`pci_ep_cp.ko`、`libspaccdev.so`、`libosal_uipc.so`、`libbt-vendor.so`、`libInfraBluetoothCore.so` 及 `cpapp-b.bin` 中涵盖 `mhlx`、`ipcu`、`shm`、`gpe`、`spacc`、`timer`、`ttyAMA0..ttyAMA3` 7 大子系统的符号与 MMIO 契约；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时切换至固定 SHA-256 洁净室基线。
2. **零外部 `dtc` 依赖纯 Python FDT v17（`0xd00dfeed`）编译器与解析器**：
   - `compile_cxd90057_hybrid_fdt()` 与 `parse_fdt_blob()` 全程内存完成 `.dts` 生成、大端 FDT v17 打包与严格解析校验（`4,614 B`、`29` 节点、`127` 属性、`3` 项非重叠 `/memreserve/`，绝不向仓库写入 `.dtb`/`.bin`）。
   - 覆盖 `cpus`（4x `arm,cortex-a53`）、`memory@40000000`（`2048 MiB`）、`/reserved-memory`（`shm_ipc@41df00000`、`wbi_hib_guard@41df80000`、`gpe0_fb@41e001000` 零重叠）、`soc/timer-ip@f0100000`（hwtimer + WDT）、`soc/serial@f0200000..f0203000`（`ttyAMA0..ttyAMA3`，含 `virtual-rom-v1` 蓝牙 UART）、`soc/mhlx@f0800000`、`soc/spacc@f7fc0000`（AES-XTS `cnflasha` 内核态隔离）及 `soc/ivshmem@10000000`（BAR0/BAR2）。
3. **`0xf0000000..0xf8ffffff` MMIO 窗口、`mhlx` 邮箱环与 `shm_Loader` 冷/热启动握手**：
   - [`MmioWindowBus`](cxd90057_dtb_and_mhlx_emulator.py) 建模 `144 MiB` MMIO 窗口分发、SPAcc 用户态越界拦截、`timer-ip` WDT 喂狗计数、`mhlx` 8 通道 16 槽位环形描述符、`W1C` 中断清除寄存器，以及 `shm_Loader` 冷启动（`0x4101 -> 0xc101`）与热唤醒（`0x4102 -> 0xc102`）握手，全程强制 `cp_mutation_bytes == 0`、`wbi_mutation_bytes == 0`。

### Phase 41 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/cxd90057_dtb_and_mhlx_emulator.py --self-test --json
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/cxd90057_dtb_and_mhlx_emulator.py --self-test --summary

# 2. 导出合成 CXD90057 混合设备树 .dts 与 FDT v17 元数据
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/cxd90057_dtb_and_mhlx_emulator.py --dts
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/cxd90057_dtb_and_mhlx_emulator.py --fdt-info

# 3. 单独运行 Phase 41 28 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_cxd90057_dtb_and_mhlx.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_cxd90057_dtb_and_mhlx.py -v
```

## Phase 45：`IMX510` VSYNC 帧管线、`libmpr` XAVC-I / XAVC S-I 录制管线、`RTMD 0xE304` 逐帧打包与双 CFexpress Type A / SDXC 槽位仿真器

[`imx510_xavc_cfexpress_pipeline_emulator.py`](imx510_xavc_cfexpress_pipeline_emulator.py) 作为 **Stage 5** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase45` 跳过），打通 `IMX510 -> BIONZ XR -> SMPTE RDD 18 RTMD -> Dual Slot A/B` 虚拟录制闭环：

1. **只读（`os.O_RDONLY`）`libmpr.so` / `appFw.so` / `cpapp-b.bin` 录制管线审计 + 洁净室回退**：
   - 使用 C 级 `bytes.find` 检视 FX3 `v7.02` 与 FX6 `v6.01` 的 `IMX510` 读出模式（`4096x2160` DCI 4K、`3840x2160` QFHD、`1920x1080` FHD、`23.98p..120p` / `240p` S&Q 与 `5016x3344` Open-Gate 编码器缺失反证）、`libmpr.so` `XAVC-I`（`MXF` `libXavcMxf`）与 `XAVC S-I` / `XAVC S` / `XAVC HS`（`MP4` `libXavcMp4`）码率配置表、`KlvConverter` `RDD18`、`P4` `set_nd_filter_*` 及 `CFexpress Type A` / `SDXC` 速率警告契约；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下切换确定性洁净室基线。
2. **逐帧 `IMX510` VSYNC、`SMPTE RDD 18` `RTMD`（`0xE304` + `0xE305`）与双卡槽仿真**：
   - 建模精确有理数时基（`24000/1001..240000/1001`）、`90 kHz` PTS、SMPTE 时间码、Dual Base ISO（`800` / `12800`）+ EI 增益（dB）、`33^3` 3D LUT 激活标记、`P4` `ND=Clear` 光学锁（`mode=4`, `val=(1,1)`）及 5 轴 IBIS 遥测逐帧 KLV 校验。
   - 覆盖 `SIMULTANEOUS`（双槽 SHA-256 一致性）、`RELAY_AUTO_SWITCH`（低水位无丢帧切换）、`SORT_PROXY_MAIN`（Main + `16 Mbps` HEVC Proxy）与故障隔离 `SPEED_CLASS_REJECT`（例如 `4K 120p XAVC-I 600Mbps` 写入 `V30` SD 卡时安全拒绝，`appFw.so` 零崩溃、`wdt_resets == 0`），全程强制 `cp_mutation_bytes == 0`、`wbi_mutation_bytes == 0`、`physical_device_writes == 0`。

### Phase 45 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/imx510_xavc_cfexpress_pipeline_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/imx510_xavc_cfexpress_pipeline_emulator.py --self-test --json

# 2. 全板 Stage 1..6 统一校验（< 2.5s）
make verify-coemulation
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-coemulation

# 3. 单独运行 Phase 45 28 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_imx510_xavc_cfexpress_pipeline.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_imx510_xavc_cfexpress_pipeline.py -v
```

## Phase 53：Stage 6 HIL 动态故障注入与热管理 / `NP-FZ100` / `XLR-H1` / `C2PA` 协同仿真台

[`fx3_vm_hil_fault_harness.py`](fx3_vm_hil_fault_harness.py) 作为 **Stage 6** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase53` 跳过），打通 `CXD90057 AP` + `CXD90058 Stock-CP`（`cp_mutation_bytes == 0`）+ `Soft-GPE0` + `IMX510/XAVC` 全板 8 场景确定性硬件在环（HIL）动态故障注入闭环：

1. **`HIL-01` 4K 60p Cine EI + `XLR-H1` + `EXT-LK` 标称拍摄**：`SoC 54°C`、`NP-FZ100 88% (7980mV)` + `USB-PD 9.0V`、`XLR-H1`（`24-bit 48kHz`）、`VMC-BNCM1 EXT-LK` 锁定，`0` 丢帧。
2. **`HIL-02` `OFF_IN_REC` 阶梯温升（`48°C -> 64°C -> 83°C -> 91°C`）**：`>=62°C` SoC / `>=68°C` CFexpress 自动风扇 PWM 覆写、`>=82°C` 琥珀色 HUD 告警、`>=90°C` 优雅封口 XAVC 尾标并干净卸载 exFAT（`VolumeDirty == 0`、零 `.RSV` 残片）与 `tmpfs` RAM overlay。
3. **`HIL-03` 实时 `XLR-H1` MI 热靴热拔出**：验证 `P11`（`0x91db059b -> 0x88000002`）秒级回落至 `INTERNAL_STEREO` 且 `IVSHMEM` TX 环零泄漏、Stock-CP 零唤醒/零崩溃。
4. **`HIL-04` `NP-FZ100`（`7200 mV`）InfoLITHIUM vs `BP-U`（`11500 mV`）抗误切 + VBUS 压降保护**：证明 `7200 mV` 正常运行不被 `11500 mV` 阈值误关机，而 `VBUS` 压降 `>450 mV` 失效关闭阻塞 `H0`/`H1` 进入。
5. **`HIL-05` `C2PA RQ_LIC.DAT` 与 `SPACC 0xf7fc0000 cnflasha` 读写陷阱**：立即拦截针对 `cnflasha*`、C2PA 证书与出厂校准区及用户态 `SPACC` MMIO 的写入/挂载探测（`calibration_mutation_bytes == 0`）。
6. **`HIL-06` `P4` 光学可变 ND 指令注入（`Auto ND` / `1/4..1/128`）**：在无光学 ND 硬件的 FX3 机身上强制钳位至 `ND=Clear`（`mode=4, val=(1,1)`），`0` 电机超时并校验 `RTMD 0xE107`。
7. **`HIL-07` `P12` `libWlanResource.so` `0x70d4` + `virtual-rom-v1` `/dev/ttyAMA3` 超时**：中和索尼 `00342260`（`WF-12`）死循环挂起（`ALLOWED_DEGRADED`、`wdt_resets == 0`、HUD UI 保持响应）。
8. **`HIL-08` 双 CFexpress Slot A 写满切换 Slot B `RELAY_AUTO_SWITCH` + 低速 `V30` 拒绝**：零丢帧无缝接力与 `V30` 安全 `SPEED_CLASS_REJECT`。

### Phase 53 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 8 场景 HIL 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_hil_fault_harness.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_hil_fault_harness.py --self-test --json

# 2. 全板 Stage 1..6 统一校验（< 2.5s）
make verify-coemulation
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-coemulation

# 3. 单独运行 Phase 53 28 项单测（双模式）& 全量 155 项单测（< 4.5s）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_fx3_vm_hil_fault_harness.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_fx3_vm_hil_fault_harness.py -v
```

## Phase 58：Stage 7 非侵入式 QMP 客体自省追踪器与 USB-LAN（`CDC-NCM` / `PTP-IP 15740`）安全通道

[`qmp_guest_introspection_tracer.py`](qmp_guest_introspection_tracer.py) 作为 **Stage 7** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase58` 跳过），在严格保持 **`nop_count == 0`**、**`guest_code_modification_bytes == 0`** 与 **`cp_mutation_bytes == 0`** 的前提下落地三大能力：

1. **严格只读（`os.O_RDONLY`）USB-LAN / PTP-IP 供体模块与动态库审计（含洁净室回退）**：
   - 检查 FX6 `cdc_ncm.ko`（`32,208 B`）、`rndis_host.ko`（`14,064 B`）、`libNetServiceEther.so`（`175,376 B`）、`libInfraPtpControl.so`（`152,520 B`）、`libptp.so`（`77,408 B`）与 `libSshInfraNetworkCommon.so`（`14,568 B`）的 SHA-256 与关键导出标记，并在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **零代码改写 QMP JSON-RPC / HMP `xp` / `pmemsave` / TCG 插件与 GDB RSP 自省**：
   - 完整建模 `qmp_capabilities`（`oob` 协商与未协商拒绝）、`query-status`、`query-cpus-fast`（4x `aarch64` vCPU）、`human-monitor-command`（`info registers`、`gva2gpa`、`xp`；拦截一切变更型 HMP/QMP 命令）及 `pmemsave` 纯内存 `mem://` 捕获。
   - 无侵入解码 `KEY_MB_PHYS`（`0x41DF00000` `SRM3KYE5`）、`CTRL_MB_PHYS`（`0x41E000E00` `0x4658364C` `'FX6L'` + `P4 ND=Clear` + `bk4_locked`）、`GPE0_PHYS`（`0x41E001000` `fx6_px` `0xFFF08018`）与 `MHLX`（`0xF0800000` / `0x41DF01000`）环形队列槽位（`0x0416`, `0x0400`），并附带 `libqemu-plugin`（`qemu-plugin.h`）与 GDB RSP `Qqemu.PhyMemMode:1` / `Z2` 硬件观察点规范（`guest_text_sw_breakpoints == 0`）。
3. **有线 USB-C 以太网（`CDC-NCM` / `RTL8153` / `AX88179`）`P12` 飞行模式免疫与 `PTP-IP 15740` 安全门控**：
   - 验证在 `P12` 飞行模式（`BK4\0` 影子 `0x019e0012=00`, `0x01a20002=00`，Wi-Fi 与 BT 零唤醒、彻底免疫索尼 `00342260` / `WF-12` 死循环）下，有线 `CDC-NCM` `1 Gbps` 网卡可独立承载 **Monitor & Control** / **Content Browser Mobile** / **Camera Remote SDK**（假色、波形、对焦图、触控对焦与 Access Authentication SSH/TLS）；同时拦截不受支持的 `RNDIS`/`CDC-ECM`、`AX88179A`/`2.5G` 网卡、FX3 手动 IP 缺失同网段默认网关，以及 `TCP 15740` 上的一切固件刷写/NVRAM/校准篡改操作码（`0x9280..0x9282`, `0x92F0..0x92F2`）。

### Phase 58 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/qmp_guest_introspection_tracer.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/qmp_guest_introspection_tracer.py --self-test --json

# 2. 全板 Stage 1..7 统一校验（< 2.5s）
make verify-coemulation
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-coemulation

# 3. 单独运行 Phase 58 28 项单测 & 全量 183 项单测（双模式，< 4.5s）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_qmp_guest_introspection_tracer.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_qmp_guest_introspection_tracer.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 63：Stage 8 HDMI Type-A `4264x2408 16-bit Linear RAW` EDID 协商、`MLUT` 净流与 USB-C 模式仲裁器

[`uvc_hdmi_raw_output_emulator.py`](uvc_hdmi_raw_output_emulator.py) 作为 **Stage 8** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase63` 跳过），补齐 `outputs/fx3-vm/` 8 阶段全板协同仿真闭环：

1. **严格只读（`os.O_RDONLY`）USB/UVC/HDMI 供体审计 + 洁净室回退**：
   - 检查 FX6 `usb_f_uvc.ko`、`usb_f_uac2.ko`、`g_webcam.ko`、`usb_f_mass_storage.ko`、`g_mass_storage.ko`、`usbg_stillimage.ko`、`cdc_ncm.ko`、`libUsbControl.so`、`libInfraUsbCmn.so`、`AVBB_SCN_START_PANELEVF.so` 共 10 份核心构件的 SHA-256 与关键导出标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **纯 Python VESA/CEA-861 `256B`（`128B+128B`）`EDID` 合成、校验与外录握手**：
   - 生成并校验 `00ffffffffffffff00` 头与 Block 0/Block 1 模 256 校验和 `== 0` 的真实 E-EDID：
     - `ATOMOS_NINJA_RAW16`：协商 `4264x2408 16-bit Linear RAW`（最高 `59.94p`）+ `ProRes RAW` VSDB + `SMPTE 12M` HDMI 时间码录机触发；线性 RAW 旁路 HDMI 端 `MLUT` 烧录而保持内屏 `LCD MLUT` 独立。
     - `SMALLHD_CINE_10BIT_422`：`3840x2160` / `1920x1080` `10-bit YCbCr 4:2:2` + `MLUT` On/Off + OSD Clean-Feed 切换，拒绝 `16-bit RAW` 并安全回退至 `10-bit YCbCr 4:2:2`（零黑屏）。
     - `HDMI_DISCONNECTED`（`HPD == 0` 录机热拔出）：零丢帧无感回落至内屏 `GPE0` `1024x540`（`0x41e001000`、`dropped_internal_xavc_frames == 0`）。
   - 证明 FX6 专属 `12G-SDI` 子输出设置（`PRM_FEATURE_MANAGER_sdi_output`、`AVBB_SCN_START_HDMI_SDI_SUB`、`EXEC_SDI_SUB_OUTPUT`）在 FX3 硬件上安全无操作隔离（`sdi_transceiver_faults == 0`）。
3. **USB-C Gadget 模式仲裁器（`UVC/UAC` vs `USB-LAN CDC-NCM` vs `CrSDK PTP` vs `MSC`）**：
   - 强制单功能互斥（并发小工具数 `<= 1`），支持 `UVC/UAC`（`4K30` / `1080p60`）、`USB-LAN CDC-NCM`（`1 Gbps`）与 `CrSDK PTP`（`usbg_stillimage.ko`）原子切换，同时强制 `P12` `BK4\0` 飞行模式无线静默（`0` BT TX、WLAN 关闭、`00342260` 免疫）、`cp_mutation_bytes == 0`、`wbi_mutation_bytes == 0` 与 `persistent_emmc_writes_authorized == False`（拍摄/录像期间拦截 `MSC` 与 `DFU` 原生闪存写入）。

### Phase 63 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/uvc_hdmi_raw_output_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/uvc_hdmi_raw_output_emulator.py --self-test --json

# 2. 全板 Stage 1..8 统一校验（< 2.5s）
make verify-coemulation
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-coemulation

# 3. 单独运行 Phase 63 30 项单测 & 全量 213 项单测（双模式，< 5s）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_uvc_hdmi_raw_output_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_uvc_hdmi_raw_output_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 67：Stage 9 多机位 SMPTE 12M TC `EXT-LK`、E 卡口 PZ 伺服/呼吸补偿与 `libpaint` 3x3 色彩管线

[`tc_genlock_lens_paint_emulator.py`](tc_genlock_lens_paint_emulator.py) 作为 **Stage 9** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase67` 跳过，9 阶段全套协同仿真保持 `< 1.4s`），在严格保持 **`cp_mutation_bytes == 0`**、**`calibration_mutation_bytes == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下落地三大核心闭环：

1. **严格只读（`os.O_RDONLY`）时间码/E 卡口/色彩矩阵供体审计 + 洁净室回退**：
   - 检查 FX3 `libInfraLensCommunicator.so`、`CAMERA_SCN_MOVIE_REC_START.so` 与 FX6 `libInfraLensCommunicator.so`、`libInfraLanc.so`、`libInfraMultiIF.so`、`libosal_udate.so`、`libInfraHotshoe.so`、`AVBB_SCN_START_VIDEO.so`、`AVBB_SCN_START_PANELEVF.so`、`libInfraAvbbc.so` 共 10 份精简构件（合计 `2,706,848 B`）的 SHA-256 与关键符号标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **多机位 SMPTE 12M LTC `EXT-LK` PLL 锁相与精确 Drop-Frame 数学模型**：
   - 覆盖 `23.98p`（`23.976`）、`24.00p`、`25.00p`、`29.97p_ndf`、`29.97p_df`、`50.00p`、`59.94p_ndf`、`59.94p_df` 八大时基与 80-bit SMPTE 12M LTC 正反向同步字（`0x3FFD` / `0xBFFC`）及偶数极性校验位编解码；精确实现 `29.97 DF` 每分钟跳过 `;00/;01` 且逢 `10` 的倍数分钟（`00, 10, 20, 30, 40, 50`）不跳帧（`00:00:59;29 -> 00:01:00;02`、`00:09:59;29 -> 00:10:00;00`）。
   - 建模 `VMC-BNCM1` Multi Port（`680 kΩ` ID）`EXT-LK` 锁相零漂移（`0.0f`）对比 `±0.5 ppm` TCXO 12 小时 `Free-Run`（`21.6 ms` / `0.5179f`）与拔线 6 小时 `Holdover`（`0.2589f` `PSEUDOLOCK`），并强制执行 **Phase 38 `uart_boot` `1.8V` 电气隔离门控**（BootROM `uart_boot` 锁存期间严禁耦合 `0.5..4.5 Vpp` LTC 输入）。
3. **E 卡口 `libInfraLensCommunicator` PZ 伺服、呼吸效应补偿与 Stock-CP 5 轴 IBIS+OSS 融合**：
   - 建模 `SELP1635G` / `SELP28135G` 8 档电动变焦（`PZ 1..8`）加减速受限梯形速度曲线（无焦距过冲、`MHLX 0x0210 -> 0x8210`）、基于对焦距离（`0.28m .. inf`）与焦距（`16..35mm`）动态插值的呼吸补偿 FOV 缩放系数（`1.000x .. 1.075x`）写入 `RTMD 0xE304` 帧内元数据，以及 Stock-CP `cpapp-b.bin`（`cp_mutation_bytes == 0`）5 轴 IBIS（`Active` / `Standard` / `Off 0x0400 Center-Lock`）与镜头 2 轴 OSS 的 `pitch/yaw/roll/shift_x/shift_y` 轴向仲裁。
4. **`libpaint` Cinema Line 色彩管线（精确 Sony `S-Log3` / `S-Cinetone` / `Knee` / 白点保持 3x3 矩阵）**：
   - 验证 `IMX510` 16-bit 线性信号到精确 Sony `S-Log3` OETF/EOTF（`18% -> 10-bit 420`）与 `S-Cinetone` + 高光 `Knee` 的无损闭环、所有 3x3 Paint Matrix 行和严格等于 `1.0`（白点中性灰误差 `<= 1e-12`），以及 `HDMI RAW16` 逐比特直通绕过 `MLUT`/Paint Matrix（同时保持 `HDMI 4:2:2 10-bit` `MLUT=On` 烘焙与 FX6 `12G-SDI` 零异常隔离）。

### Phase 67 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 9 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/tc_genlock_lens_paint_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/tc_genlock_lens_paint_emulator.py --self-test --json

# 2. 全板 Stage 1..9 统一校验（< 1.4s，支持 --skip-phase67 向后兼容）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 67 33 项单测 & 全量 246 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_tc_genlock_lens_paint_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_tc_genlock_lens_paint_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 71：Stage 10 双卡槽 `Relay`/`Simul`/`Sort` Proxy、`NonRealTimeMeta.xml` 伴随文件与 `USB-PD -> NP-FZ100` UPS / `.RSV` 断电救援

[`dualslot_proxy_ups_salvage_emulator.py`](dualslot_proxy_ups_salvage_emulator.py) 作为最终 **Stage 10** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase71` 跳过，10 阶段全套协同仿真在本地只读供体模式下保持 `< 1.5s`、洁净室模式下 `< 0.5s`），在严格保持 **`cp_mutation_bytes == 0`**、**`p1_emmc_mutations == 0`**、**`internal_emmc_writes == 0`**、**`c2pa_license_untouched == True`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成全板 **10 阶段协同仿真闭环**：

1. **严格只读（`os.O_RDONLY`）双卡槽/代理/XML/电源/救援供体审计 + 洁净室回退**：
   - 检查 FX3 `libmpr.so` 与 FX6 `libInfraFsys.so`、`libInfraMediaCommon.so`、`libInfraMediaDetect.so`、`libInfraMediaMount.so`、`libInfraMediaConfig.so`、`libInfraMetaSupplier.so`、`libul_xml.so`、`libBusPower.so`、`libUsbBusPower.so` 共 10 份构件的 SHA-256 与关键导出符号标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **双卡槽（`Slot A` + `Slot B`）`Relay` / `Simultaneous` / `Sort` 弹性环形缓冲与零丢帧切换**：
   - 建模 `256 MiB` DRAM Elastic FIFO 承载 `600 Mbps` `4K 59.94p XAVC S-I`（`1.25 MB/frame` GOP=1）+ `16 Mbps` `1080p XAVC HS 10-bit Proxy`（`S03.MP4`）：
     - **`Relay` 自动接力**：`Slot A` 写满至 `0` 空闲簇时干净闭合 `A001C001_261114_FX3V.MP4`（`moov` 落盘、`VolumeDirty=0`），`256 MiB` FIFO 吸收 `<= 85 ms` 的 `Slot B` 打开/FAT 簇分配延迟，实现 **`0` 丢帧**无缝续写 `A001C002_261114_FX3V.MP4`。
     - **`Simultaneous` 双卡同录**：验证 `Slot A == Slot B` 逐帧 CRC32 / SHA-256 一致性，并在录制途中热拔出 `Slot B` 时隔离故障，确保 `Slot A` **`0` 丢帧**存活（`app_crashes == 0`、`wdt_resets == 0`）。
     - **`Sort` 分流（`CFexpress Type A VPG400` 主码流 + `SDXC UHS-II V60` `S03.MP4` 代理）**：验证启用 `S&Q` 升格（`120fps` / `240fps`）时 Proxy 自动干净挂起（`SQ_OFF_SPEED_AUTO_SUSPEND`）且绝不阻塞主码流录制。
3. **纯内存 `NonRealTimeMeta`（`*M01.XML`）+ `RTMD 0xE304` 逐剪辑元数据一致性校验器**：
   - 在虚拟剪辑封口时于内存生成并解析 `NonRealTimeMeta` XML，并与 Stage 9/10 实时管线及 `RTMD 0xE304` 交叉核验（`Cine EI 800/12800`、`S-Gamut3.Cine / S-Log3`、`.cube` User LUT 槽位、`SMPTE 12M` `StartTimecode`、`SELP1635G` 焦距/呼吸补偿 FOV 缩放系数与 `IBIS Active` 模式），实现 100% 一致性且 `c2pa_license_untouched == True`、`internal_emmc_writes == 0`。
4. **录中掉电（`USB-PD 9V/3A` 热拔 -> `NP-FZ100` UPS 与无电池 `.RSV` 应急救援）协同仿真**：
   - 场景 1：`NP-FZ100` `65%` SoC 下拔掉 `USB-PD` -> `0.4 ms` 理想二极管切换，**`0` 丢帧**连续录制。
   - 场景 2：`NP-FZ100` 跌至 `2%`（`6.2V` / `6200 mV` 欠压阈值）-> Stock-CP `PMIC` 触发 `libmpr` 可控紧急刷盘，关断前完成 `moov` + `M01.XML` + exFAT `VolumeDirty=0`（**`0` 损坏剪辑**）。
   - 场景 3：无电池瞬时掉电演练 -> 合成内存建立 Sony `.RSV` 原始流救援容器并恢复全部已提交环帧（`salvageable_frames == committed_ring_frames`、`VolumeDirty=0`、`p1_emmc_mutations == 0`、`persistent_emmc_writes_authorized == False`）。

### Phase 71 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 10 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/dualslot_proxy_ups_salvage_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/dualslot_proxy_ups_salvage_emulator.py --self-test --json

# 2. 全板 10 阶段（Stage 1..10）统一校验（本地 < 1.5s，洁净室 < 0.5s，支持 --skip-phase71）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 71 34 项单测 & 全量 280 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_dualslot_proxy_ups_salvage_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_dualslot_proxy_ups_salvage_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 78：Stage 11 `evdev` 627 点 `PDAF` 触控对焦、`Clear Image Zoom (CIZ)` 仲裁与可分配按键分发器

[`touch_af_ciz_assignable_emulator.py`](touch_af_ciz_assignable_emulator.py) 作为 **Stage 11** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase78` 向后兼容跳过；全板 11 阶段协同仿真在本地只读供体模式下保持 `< 1.4s`、洁净室模式下 `< 0.5s`），在严格保持 **`cp_mutation_bytes == 0`**、**`bk4_persistent_nvram_writes == 0`**、**`null_gpio_derefs == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成三大互动与变焦控制闭环：

1. **严格只读（`os.O_RDONLY`）触控/变焦/可分配按键供体审计 + 洁净室回退**：
   - 检查 FX3 `libInfraLensCommunicator.so`、`global.xdb`、`string_english.g.uxc` 与 FX6 `libInfraLensCommunicator.so`、`libInfraTp.so`、`libInfraInput.so`、`libInfraDial.so`、`libul_GpioCtrl.so`、`libInfraSetupFile.so`、`string_english.uxc` 共 10 份精简构件（合计 `613,744 B`）的 SHA-256 与关键导出标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Linux `evdev`（`ABS_MT_POSITION_X/Y`）-> Stock-CP `IMX510` 627 点（`33x19`）`PDAF` 与变形宽银幕逆映射**：
   - 建模 `960x540` `GPE0` 电容触摸（`touch_down` / `drag` / `double_tap_cancel`）通过 `MHLX` 环形邮箱（`0x0310..0x0314 -> 0x8310..0x8314`，`0` 阻塞）映射至 `IMX510` `95%` 覆盖范围 `33 x 19 = 627` 相位检测对焦网格。
   - **变形宽银幕反挤压逆映射（`1.3x` / `2.0x`）**：精确计算光学传感器 `(u, v)` 坐标，并拦截落在上下黑边遮幅（letterbox matte）内的误触（`OUTSIDE_ACTIVE_IMAGE_LETTERBOX_IGNORED`，零边缘误对焦）。
   - **对焦放大（`Focus Magnifier` `1.0x -> 4.0x -> 1.0x`）**：验证 `GPE0` 预览围绕选中 `PDAF` 网格实时放大与平移时，内录 `XAVC` 与 `HDMI RAW16` 净流保持 `1.0x` 未裁剪（`clean-feed invariant`），并支持按 Cinema Line 规则退出或锁定。
3. **机身 `T/W` 8 档变焦拨杆 + `Clear Image Zoom`（`CIZ` `4K 1.5x` / `FHD 2.0x`）运行时仲裁器**：
   - 完整闭环 `SELP1635G` 光学伺服变焦（`16..35mm`、`1.00x`）-> 光端平滑接力 `CIZ`（`4K` `1.00x..1.50x`、`FHD` `1.00x..2.00x`，完整保留 627 点 `PDAF` 与实时眼部追踪）-> `Digital Zoom`（`>1.5x/2.0x` 自动切换 `CENTER_SPOT_CONTRAST_ONLY`）。
   - 验证开启 `HDMI RAW16` 或 `S&Q >= 120fps` 时平滑重置 `ciz_scale = 1.00x`（`CIZ_CLAMPED_BY_MODE_EXCLUSION`），`0` 邮箱阻塞。
4. **可分配按键（`Custom 1..6` + `Lens Hold` + `XLR-H1` + `Big6` 易失影子）安全分发器**：
   - 验证 FX3 全部实体键（`Base ISO 800<->12800`、`Zebra`、`Peaking`、`S&Q`、`Focus Magnifier`、`Status Check`、`Big6 Home`）及 `Big6` 易失内存状态覆盖（`ram://tmp/camset_big6_shadow.json`），同时确保触发 FX3 缺失硬件的 FX6 动作（`ND Preset`、`Auto ND`、`VF Adjust`）安全返回 `CONTAINED_NO_OP_TOAST`（`0` 空 GPIO 解引用、`bk4_persistent_nvram_writes == 0`）。

### Phase 78 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 11 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/touch_af_ciz_assignable_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/touch_af_ciz_assignable_emulator.py --self-test --json

# 2. 全板 11 阶段（Stage 1..11）统一校验（本地 < 1.4s，洁净室 < 0.5s，支持 --skip-phase78）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 78 36 项单测 & 全量 316 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_touch_af_ciz_assignable_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_touch_af_ciz_assignable_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 82：Stage 12 跨机身 `CAMSET` 清洗、4 通道 `24-bit/48 kHz` LPCM（`-20 dB` 安全轨 + 限幅器）与 SMPTE 12M `User-Bits` 多机位再生器

[`camset_lpcm_tcub_emulator.py`](camset_lpcm_tcub_emulator.py) 作为 **Stage 12** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase82` 向后兼容跳过；全板 12 阶段协同仿真在本地只读供体模式下保持 `< 1.4s`、洁净室模式下 `< 0.5s`），在严格保持 **`cp_mutation_bytes == 0`**、**`bk4_persistent_nvram_writes == 0`**、**`uart_boot_contention_events == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成三大机队闭环：

1. **严格只读（`os.O_RDONLY`）`CAMSET`/音频/时间码供体审计 + 洁净室回退**：
   - 检查 FX3 `libBackupManager.so`、`libInfraExtBackupCommunicator.so`、`libbackup.so`、`libWlanResource.so`、`string_english_g.uxc` 与 FX6 `libInfraSetupFile.so`、`libbackup.so`、`libInfraMultiIF.so`、`libInfraHotshoe.so`、`string_english.uxc` 共 10 份精简构件（合计 `750,680 B`）的 SHA-256 与关键符号标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **跨机身 `CAMSET` A-Cam FX6 -> B-Cam FX3 机队配置清洗器与易失内存影子加载器**：
   - 导入 A-Cam `ILME-FX6` 配置文件（`Cine EI 800`、`S-Gamut3.Cine/S-Log3`、`User1.cube`、`23.98p 180.0°`、`5600K`，含 FX6 专属 `ND 1/16`、`12G-SDI`、`VF Zebra`、`Wi-Fi AP=On`）至运行 Stage-B 的 B-Cam `ILME-FX3` 易失内存影子（`ram://tmp/camset_bcam_fx3_shadow.json`）。
   - 100% 保留共享 Cinema Line 成像参数，同时确定性钳位/屏蔽缺失硬件与射频禁区字段（`nd_preset -> "Clear"`、`sdi_out -> "CONTAINED_DISABLED"`、`vf_zebra -> LCD 重定向`、`wlan_ap -> False` 强制 `P12` 飞行模式影子 `0x019e0012=00` / `0x01a20002=00`、`bk4_persistent_nvram_writes == 0`），并拦截任何针对 `/dev/nflasha*` / `bk4://persistent` 的非易失写入企图。
3. **4 通道 `24-bit / 48 kHz` LPCM（`XLR-H1` CH1/CH2 + `-20 dB` 安全轨 CH3/CH4）与砖墙峰值限幅器**：
   - 建模逐样本 `int24`（`[-8388608, +8388607]`）`S24_3LE`（`5,760 B`）及 QEMU `virtio-sound` `S32_LE`（`7,680 B`）`480` 帧 / `10 ms` 周期：`CH1/CH2` 走 `XLR-H1` 主轨（叠加 Phase 77 `+48V` 幻象供电传感器防烧毁防火墙），`CH3/CH4` 录制 `-20.0 dB` 备份安全轨；验证 `+12 dBFS` 瞬态过载下 `-0.5 dBFS` 砖墙限幅器启动且 **`0` 次 `int24` 溢出回卷**（`CH3/CH4` 零削波）。
   - 验证 `XLR-H1` 热拔出时通过 `P11` 隔离（`0` IVSHMEM 泄漏）秒级回落至 `INTERNAL_STEREO_FALLBACK`（`+48V` 泄放至 `0.25 V`），以及 `S&Q` 升格（`120fps`/`240fps`）时自动全通道静音（`nonzero_samples == 0`）。
4. **SMPTE 12M `User-Bits`（`BG1..BG8`）机队标签与 `TC IN`（`Multi-Port`）-> `TC OUT`（`HDMI`）再生器**：
   - 将 `CamID=B`、`Reel=002`、`MasterCam=A` 与锁定标记打包进 80-bit `0x3FFD` LTC 帧的 32-bit `BG1..BG8` 二进制组（`42 00 24 13`），通过 `VMC-BNCM1` `EXT-LK` 与 A-Cam 零帧偏移（`0f`）锁相，强制执行 Phase 38 `uart_boot` `1.8V` 电气隔离防火墙（`0` 争用事件），并干净再生下游 `HDMI TC OUT`（含时间码 + `User-Bits`）。

### Phase 82 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 12 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/camset_lpcm_tcub_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/camset_lpcm_tcub_emulator.py --self-test --json

# 2. 全板 12 阶段（Stage 1..12）统一校验（本地 1.21s < 1.4s，洁净室 0.36s < 0.5s，支持 --skip-phase82）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 82 36 项单测 & 全量 352 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_camset_lpcm_tcub_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_camset_lpcm_tcub_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 87：Stage 13 回放/缩略图梭车、`ShotMark1/2` `<EssenceMark>` 同步、`Cine EI` `Push Auto Iris` 与露点/PMIC 5V HIL

[`playback_shotmark_dewpoint_emulator.py`](playback_shotmark_dewpoint_emulator.py) 作为 **Stage 13** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase87` 向后兼容跳过；全板 13 阶段协同仿真在本地只读供体模式下保持 `1.18s < 1.5s`、洁净室模式下 `0.36s < 0.5s`），在严格保持 **`cp_mutation_bytes == 0`**、**`p1_emmc_mutations == 0`**、**`persistent_emmc_writes_authorized == False`**、**`internal_emmc_format_blocked == True`** 与 **`p4_nd_motor_faults == 0`** 的前提下完成三大闭环：

1. **严格只读（`os.O_RDONLY`）回放/媒体/光圈/风扇/总线供电供体审计 + 洁净室回退**：
   - 检查 FX3 `libInfraCCPFStatic.so`、`libInfraMediaConfig.so`、`libInfraMediaMount.so`、`libInfraLensCommunicator.so`、`libfan.so`、`libBusPower.so`、`libUsbBusPower.so` 与 FX6 `libInfraLanc.so`、`libfan.so`、`libUsbBusPower.so` 共 10 份精简构件（合计 `505,144 B`）的 SHA-256 与关键导出标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **缩略图 / 回放梭车（`1x, 2x, 5x, 15x` 正反向）、`ShotMark1/2` `<EssenceMark>` XML 同步与内部 eMMC `p1` 媒体隔离**：
   - 在 `Slot A / Slot B` 剪辑（`A001C001..A001C008`）间建模 `SHOOTING_LIVE_VIEW` ↔ `THUMBNAIL_INDEX` ↔ `PLAYBACK_SHUTTLE` 状态切换与 `1x/2x/5x/15x` 正反向梭车，在录制与回放梭车期间实时打点 `ShotMark1`（`OK`）和 `ShotMark2`（`KEEP`），并将帧精确 `<EssenceMark>` 节点 100% 往返同步至内存 `NonRealTimeMeta`（`*M01.XML`）伴随文件。
   - 验证针对受保护剪辑（`ClipProtected=True`）的 `Delete Clip` 与针对内部 `/dev/mmcblk0p1`（`p1` eMMC）的 `Format Media` 请求均 **100% 失败关闭拦截**（`internal_emmc_format_blocked == True`、`persistent_emmc_writes_authorized == False`、`p1_emmc_mutations == 0`）。
3. **`Cine EI` `Push Auto Iris`（`1/8` 档光圈伺服收敛至 `41.0% IRE` `S-Log3` 中灰 / `< 94.0% IRE` 高光保护）且零 `P4` ND 故障**：
   - 在 `Cine EI`（`Base 800`、`180.0°` 快门角锁定）面对 `+3.5 EV` 场景照度跃升时，通过 `MHLX` 镜头伺服包（`0x0220 -> 0x8220`）以 `1/8` 档（`0.125 EV`）步进平滑收缩 E 卡口光圈（`T1.4 -> T4.8`，`28` 步），使 `18%` 灰卡精准收敛至 **`41.02% IRE` `S-Log3`**（高光测光模式下高光峰值 `< 94.0% IRE`，`92.31% IRE`），全程 **`0` 次 `P4` 可变 ND 电机调用与故障**（`p4_nd_motor_faults == 0`）。
4. **环境露点（外置 `TEC` 结露陷阱）与 PMIC `5V` 附件电流预算 HIL 协同仿真**：
   - 建模热带片场湿热环境（`31°C / 80% RH`，Magnus-Tetens `T_dp = 27.14°C`）与附件热插拔组合（`XLR-H1 +48V` `360 mA` + 有源光纤 HDMI `160 mA` + 总线供电 USB-C LAN `420 mA` = `940 mA > 900 mA`），证明低于露点的外置 `TEC` 制冷（`11.0°C < T_dp`）和超额 `5V` 负载均触发即时 HIL 告警与零电源轨故障卸载（`pmic_rail_faults == 0`），而机内 `libfan.so` 风冷（`39.5°C`）与外接供电 USB-PD Hub（`520 mA`）100% 绿灯畅行。

### Phase 87 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 13 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/playback_shotmark_dewpoint_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/playback_shotmark_dewpoint_emulator.py --self-test --json

# 2. 全板 13 阶段（Stage 1..13）统一校验（本地 1.18s < 1.5s，洁净室 0.36s < 0.5s，支持 --skip-phase87）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 87 36 项单测 & 全量 388 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_playback_shotmark_dewpoint_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_playback_shotmark_dewpoint_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 91：Stage 14 Gyroflow / Sony Catalyst `2000 Hz` 6 轴 IMU `RTMD`（SMPTE RDD 18 `0xE4xx`）FIFO、变形宽银幕（`1.33x/1.5x/1.8x/2.0x`）非对称 IBIS 增益/中心锁仲裁器与 `IMX510` 卷帘快门读出偏斜 HIL

[`gyroflow_rtmd_anamorphic_emulator.py`](gyroflow_rtmd_anamorphic_emulator.py) 作为 **Stage 14** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase91` 向后兼容跳过；全板 14 阶段协同仿真在本地只读供体模式下保持 `1.12s < 1.5s`、洁净室模式下 `0.35s < 0.5s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`physical_device_writes == 0`**、**`stock_cp_fault_count == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成四大核心闭环：

1. **严格只读（`os.O_RDONLY`）IMU / `RTMD` / `SteadyShot` / 变形反挤压供体审计 + 洁净室回退**：
   - 检查 FX3 `v7.02` 与 FX6 `v6.01` 共 10 份紧凑构件（`dataflowInfraFramework.so` x2、`libmpr.so`、`libInfraCCPFStatic.so`、`CAMERA_SCN_MOVIE_REC_START.so`、`AVBB_SCN_START_VIDEO.so`、`AVBB_SCN_START_PANELEVF.so`、`libGetLog.so` x2、`string_english_f.uxc`）的 SHA-256 与关键导出标记（`UDAMSetGyroscopeValue`、`GetData_GyroInfo`、`PID_SET_ANAMO_DESQUEEZE_SCALE`、`PID_SET_FRAME_LOCK_STEADYSHOT`、`MSG_ID_VDF_INPUT_SET_DE_SQUEEZE`、`De-Squeeze Display` 等）；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **`2000 Hz` 6 轴 IMU 环形 FIFO -> 逐帧 SMPTE RDD 18 `RTMD`（`0xE400..0xE438`）打包与四元数积分验证**：
   - 仿真 `CXD90057`/`CXD90058` SPI `2000 Hz` 6 轴陀螺仪/加速度计环形缓冲在 `23.98p`（`~83.4` 样本/帧）、`24.00p`（`83, 83, 84` 交替）、`25.00p`（精确 `80`）、`29.97p`（`~66.7`）、`59.94p`（`~33.4`）与 `119.88p`（`~16.7`）下的精确取样，配备微秒晶振漂移补偿（`250 ppm` 漂移收敛至 `< 2.0 us` 残差）、高水位溢出防护门控（`> 512` 样本阻塞自动抑制无效陀螺轨道）与 `S&Q / VFR` `RTMD` 自动禁用安全标志。
   - 验证 Sony E 卡口 Cinema Line `+X/+Y/+Z` 正交 `SO(3)` 安装矩阵（`det == +1.0`）以及经过 `0xE4xx` KLV 往返封包/解包后的 Gyroflow 中点四元数积分精度（漂移 `0.000013° < 0.02°`）。
3. **变形宽银幕（`Off=1.0x`, `1.3x`/`1.33x`, `1.5x`, `1.8x`, `2.0x`）非对称 IBIS 偏航缩放 & FX6-on-FX3 中心锁仲裁器**：
   - 支持两种安全运行模式：`ANAMORPHIC_ASYMMETRIC_YAW_SCALING`（`Standard` IBIS 下将水平偏航增益按 `1 / squeeze_factor` 缩放，消除反挤压水平果冻摆动）与 `POST_GYROFLOW_IBIS_CENTER_LOCK`（锁定 `CXD90058` `0x0400 = Off` 中心锁通电，仅记录 `2000 Hz` 原始陀螺 `RTMD`）。
   - 对变形倍率下未补偿的球面 `Active` 电子裁切畸变以及在 Gyroflow 后期增稳启用时向 `RTMD` 嵌入非零 `0xE438` IBIS 位移偏移（双重增稳隐患）执行 **100% 失败关闭拦截**。
4. **`IMX510` 传感器卷帘快门读出时间与偏斜 HIL**：
   - 精确建模 Full-Frame 4K（`8.7 ms` / `8700 us`）、4K 120p `1.1x` 裁切（`4.3 ms` / `4300 us`）与 HDMI 16-bit Linear RAW（`8.9 ms` / `8900 us` @ `4264x2408`）的逐行读出周期，编码进 `RTMD` `0xE400` 并验证行级去偏斜残差 `< 0.01 px` 且 `0` 次 Stock-CP 故障注入。

### Phase 91 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 14 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/gyroflow_rtmd_anamorphic_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/gyroflow_rtmd_anamorphic_emulator.py --self-test --json

# 2. 全板 14 阶段（Stage 1..14）统一校验（本地 1.12s < 1.5s，洁净室 0.35s < 0.5s，支持 --skip-phase91）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 91 36 项单测 & 全量 424 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_gyroflow_rtmd_anamorphic_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_gyroflow_rtmd_anamorphic_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 96：Stage 15 间隔录制（延时摄影电子快门 XAVC 封包与 6 档日落 AE 平滑）、Picture Cache（DDR 预录环形缓冲仲裁）、有线 USB-LAN FTPS（P12 射频零唤醒）与 Sigma 风扇堵转 / 水下壳体真空 HIL

[`interval_cache_ftp_fan_emulator.py`](interval_cache_ftp_fan_emulator.py) 作为 **Stage 15** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase96` 向后兼容跳过；全板 15 阶段协同仿真在本地只读供体模式下保持 `1.28s < 1.5s`、洁净室模式下 `0.41s < 0.5s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`physical_device_writes == 0`**、**`wf12_00342260_hits == 0`**、**`emmc_partition_mutations == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成五大闭环：

1. **严格只读（`os.O_RDONLY`）间隔/预录/FTPS/USB-LAN/风扇供体审计 + 洁净室回退**：
   - 检查 FX3 `v7.02` 与 FX6 `v6.01` 共 10 份紧凑构件（`libmpr.so`、`cachecontrol.ko`、`libInfraFtpClient.so` x2、`libNetServiceEther.so` x2、`cdc_ncm.ko`、`libWlanResource.so`、`libfan.so` x2）的 SHA-256 与关键符号标记（`intervalRec`、`PreRecStart`、`InfraFtpClient_Init`、`TLS_AES_256_GCM_SHA384`、`jobReqResumeFtpTransfer`、`FT_ERR_PASV_NOT_SUPPORT`、`netserviceether_init`、`fan_infra_init`、`g_bkup_dev_temp_bkid_list` 等）；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Interval Recording（延时摄影）电子快门 XAVC 封包器与 6 档日落 AE 平滑器**：
   - 建模 Cinema Line 间隔录制（间隔 `1..60s`、张数 `1..9999`），强制锁定电子快门（`mechanical_curtain_actuations == 0`，消除 10,000 次机械帘幕磨损），覆盖 `High` / `Mid` / `Low` / `Lock` 四档阻尼指数 AE 平滑曲线，完成单 MXF/MP4 封包及内存 `NonRealTimeMeta`（`*M01.XML`）`<IntervalRecording>` 标签往返校验。
3. **FX6 Picture Cache（Pre-Rec）循环 DDR 环形缓冲仲裁器（FX3 2048 MiB DRAM）**：
   - 建模 `2s..16s` GOP 对齐预触发环形缓冲，覆盖 `XAVC-I 4K60`（`600 Mbps` 自动钳位至 `5.0s` / `357.628 MiB <= 384 MiB`）、`XAVC-I 4K24`（`240 Mbps` `10s` 全量 / `16s` 钳位至 `13.0s`）、`XAVC-L 4K30`、`XAVC-I FHD60` 与 `XAVC-L FHD60`，确保 `appFw`/`GPE0`/内核预留 `>= 1664 MiB`（`oom_events == 0`）、REC 触发零丢 GOP 刷写至 CFexpress Slot A/B，并在 `S&Q` / `HDMI RAW16` / `Interval Rec` 激活时自动安全挂起。
4. **有线 USB-LAN（`CDC-NCM` / `RTL8153`）被动 FTPS（TLS 1.3 + `REST` 断点续传）与 `P12` / eMMC 防火墙**：
   - 验证 `PROXY_ONLY` 与 `ORIGINAL_AND_PROXY` 队列在链路闪断注入后通过 `REST <byte_offset>` 续传并达成端到端 SHA-256 一致；同时强制 `P12` Wi-Fi/BT 射频静默（`00342260` `WF-12` 命中 `== 0`）并 100% 拦截指向内部 eMMC `p1..p15`（`/dev/mmcblk0*`、`/dev/nflasha*`、`bk4://`、`..` 路径穿越）的读写请求。
5. **Sigma 离心风扇霍尔测速堵转 / 侧面排气遮挡（`< 5 mm`）与水下摄影壳体真空泄漏 HIL**：
   - 注入风扇转子堵转（`PWM >= 25%` 且 `RPM == 0`）、侧面排风间隙 `< 5 mm`、`> 1.5 mbar/10min` 真空压降及进水告警，验证立即触发零损失活跃剪辑刷新（`.RSV` 无损封口、`VolumeDirty == 0`）与安全关机，且内部 eMMC 零损坏（`emmc_corruptions == 0`）。

### Phase 96 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 15 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/interval_cache_ftp_fan_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/interval_cache_ftp_fan_emulator.py --self-test --json

# 2. 全板 15 阶段（Stage 1..15）统一校验（本地 1.28s < 1.5s，洁净室 0.41s < 0.5s，支持 --skip-phase96）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 96 36 项单测 & 全量 460 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_interval_cache_ftp_fan_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_interval_cache_ftp_fan_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 99：Stage 16 `65^3->33^3` `.cube` 四面体 3D-LUT DMA 引擎、HDMI AVI InfoFrame + HDMI->12G-SDI `ST 2082` REC-Trigger 桥接、与零下（`-20°C`）Li-Ion ESR / 高海拔（`5,200m`）降额 HIL

[`lut3d_tetrahedral_subzero_sdi_emulator.py`](lut3d_tetrahedral_subzero_sdi_emulator.py) 作为 **Stage 16** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启，可通过 `--skip-phase99` 向后兼容跳过；全板 16 阶段协同仿真在本地只读供体模式下保持 `~1.38s < 1.5s`、洁净室模式下 `~0.47s < 0.5s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`physical_device_writes == 0`**、**`sdi_transceiver_faults == 0`**、**`lithium_plating_events == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成四大闭环：

1. **严格只读（`os.O_RDONLY`）3D-LUT / HDMI-SDI / USB-PD / 风扇供体审计 + 洁净室回退**：
   - 检查 FX3 `v7.02` 与 FX6 `v6.01` 共 10 份紧凑构件（`libmpr.so`、`libInfraAvbbc.so` x2、`AVBB_SCN_START_PANELEVF.so`、`AVBB_SCN_START_VIDEO.so`、`libBusPower.so`、`libUsbBusPower.so` x2、`libfan.so` x2）的 SHA-256 与关键导出标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **用户 `.cube` 3D LUT 清洗器与 `65^3 / 17^3 -> 33^3` 6-子四面体（Kuhn `T1..T6`）DMA 重采样引擎**：
   - 解析 `17^3`、`33^3` 与 `65^3` DaVinci Resolve `.cube` 文件，对 `NaN`/`Inf`、`LUT_1D_SIZE`、倒置 `DOMAIN_MIN >= DOMAIN_MAX`、体素计数不匹配、超大载荷及路径穿越/控制字符执行 100% 失败关闭拦截（`CubeLutSanitizationError`）。
   - 通过精确 6-子四面体重心插值重采样至 `CXD90058` 硬件 `33^3`（`35,937` 体素），打包为 `U8`（`107,812 B`）或 `U16`（`215,622 B`）DMA 查表并经 `IVSHMEM` `0x0165`（`> 0xbb80` DRAM 路径）/ `0x0166` 槽位切换载入易失共享内存（`nvram_persistent_writes == 0`），强制锁定 **Main-SLog3 内录无烧录 + Proxy MLUT 独立开关 + HDMI Clean-Feed / RAW16 旁路** 路由隔离。
3. **CEA-861-G HDMI AVI InfoFrame + Sony VSIF REC-Trigger -> 12G-SDI（SMPTE ST 2082）无损桥接**：
   - 合成并反向校验标准 17 字节 CEA-861-G HDMI AVI InfoFrame（模 256 校验和 `(0x100 - sum) & 0xFF == 0`、`YCbCr 4:2:2 10-bit`、`S-Gamut3.Cine/S-Log3` 与 `LIMITED_LEGAL` TRS 防碰撞门控，阻断全范围 `YQ=1` 与 SDI 保留字 `0x000..0x003` / `0x3FC..0x3FF` 冲突）+ Sony VSIF 帧精确 `RISING_START` / `FALLING_STOP` 触发边沿，验证外置 HDMI->12G-SDI 桥接器 **0 丢触发（`dropped_rec_triggers == 0`）**、**SMPTE RP 188 LTC/VITC 零帧偏移锁相（`ltc_vitc_frame_offset == 0`）** 且 FX3 机身无假性 SDI-BNC 报错（`sdi_transceiver_faults == 0`）。
4. **零下（`-20°C`）`NP-FZ100` Arrhenius ESR 压降热切换与高海拔（`5,200m`）对流降额 HIL**：
   - 建模 `-20°C` 深冷下 2S Li-Ion 内阻急升（`R_int ≈ 1.0784 Ω`）在 `8.5W`（`4K120 + Active IBIS`）瞬态负载下的端电压跌落预测，在跨越 `6.0V` PMIC UVLO 前无感切换至 **`USB-PD 9V/3A`（`8.88V` 总线）** 并严格闭锁 `<= 0°C` 锂电充电以消除析锂（`lithium_plating_events == 0`），无 USB-PD 时提前触发零丢帧 `.RSV` 抢救封口。
   - 建模 ISA `5,200m` 高原气压（`~52.6 kPa`、空气密度与风机质量流量比 `~0.587x`）对流降额，主动拉升 Sigma 离心风扇 PWM（`55% -> 95%` / `~3,530 RPM`）并卸除后台非关键 `FTPS`（`1.4W`）功耗，确保 `CXD90057` 峰值结温稳定控制在 `T_warn = 82.0°C` 以下。

### Phase 99 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 16 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/lut3d_tetrahedral_subzero_sdi_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/lut3d_tetrahedral_subzero_sdi_emulator.py --self-test --json

# 2. 全板 16 阶段（Stage 1..16）统一校验（本地 ~1.38s < 1.5s，洁净室 ~0.47s < 0.5s，支持 --skip-phase99）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 99 36 项单测 & 全量 496 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_lut3d_tetrahedral_subzero_sdi_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_lut3d_tetrahedral_subzero_sdi_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```




