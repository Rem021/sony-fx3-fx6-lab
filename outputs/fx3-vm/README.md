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






