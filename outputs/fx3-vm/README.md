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

## Phase 103：Stage 17 无线图传近场 EMI / D-Tap 热插拔 ESD / 3.3V LTC 钳位、12 小时连续 exFAT 无缝分片与 CFexpress SMART 磨损、及零 eMMC NVRAM 磨损耐久协同仿真

[`wireless_emi_exfat_endurance_emulator.py`](wireless_emi_exfat_endurance_emulator.py) 作为 **Stage 17** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase103_emi_exfat_endurance=True`，可通过 `--skip-phase103` 向后兼容跳过；全板 17 阶段协同仿真在本地只读供体模式下保持 `~1.34s < 1.6s`、洁净室模式下 `~0.46s < 0.55s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`physical_device_writes == 0`**、**`emmc_sector_writes == 0`**、**`emmc_wear_level_increments == 0`**、**`cxd90057_gpio_damage_events == 0`**、**`dropped_audio_samples == 0`**、**`dropped_video_frames == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成四大闭环：

1. **严格只读（`os.O_RDONLY`）媒体寿命 / NVMe SMART / 热插拔 / NVRAM 备份供体审计 + 洁净室回退**：
   - 检查 FX3 `v7.02` 与 FX6 `v6.01` 共 10 份紧凑构件（`libInfraMediaMount.so` x2、`libInfraMediaCommon.so` x2、`libbackup.so` x2、`libBackupManager.so`、`libInfraFsys.so` x2、`libHotplug.so`）的 SHA-256 与关键符号标记（`GetMediaLifeInfo`、`mcmn_drv_nvme_getlogpage_smartinformation`、`NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0`、`Backup_write`、`flash_span`、`guardAcvOn`）；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **12 小时连续纪录片录制（`43,200s` 4K `59.94p` ~`3.24 TB`）exFAT 无缝分片与 CFexpress NVMe SMART 热/磨损 HIL**：
   - 建模连续 12 小时 `600 Mbps`（`75 MB/s` -> `3,240,000,000,000 B` = `3.24 TB`）双卡槽接力录制（Slot-A -> Slot-B）及 `exFAT` 64 位 `co64` 容器与 `NonRealTimeMeta` LTC 连续性，验证跨越 **754 个 4 GiB 边界**与 **47 个 64 GiB 边界**时 **0 丢帧、0 丢音频采样、0 LTC 跳变**。
   - 对 `< 32 GB` 的 `FAT32` SDHC 卡执行长录 `BLOCKED_FAT32_4GIB_SPANNING_TRAP` 失败关闭拦截；当 CFexpress `SMART spare_blocks < 10%` 或 `T_nand > 78°C` 时动态触发 `NVMe PS0 -> PS1` 限流并无缝抢先切换至健康 Slot-B（无健康备份槽时失败关闭）。
3. **1000 mW 5GHz/6GHz 无线图传近场 EMI、D-Tap/HDMI 热插拔 ESD 与 Multi-Port 3.3V LTC 钳位 HIL**：
   - 建模在 MI-Shoe / HDMI 旁挂载 `1000 mW` `5.0..6.4 GHz` 无线图传：近场未屏蔽时触发 `BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE` 告警，验证同轴屏蔽线 + **TMDS 自适应均衡（CTLE/DFE）** + **MI-Shoe 音频屏蔽隔离**可将眼高恢复至 `>= 150 mV`（`BER <= 1e-12`）与音频底噪 `<= -98 dBFS`。
   - 强制执行 **`GND -> Power -> Signal`** 上电时序与 `100 ms` `HPD` 去抖，阻断未隔离带电 D-Tap 下的 HDMI 热插拔浪涌（`BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE`）；并在 Multi-Port 接入 `> 5.0 Vpp` 广播级 BNC LTC 时通过 `3.35 V` 钳位级拦截过压（`BLOCKED_TIMECODE_BNC_OVER_VOLTAGE`、`cxd90057_gpio_damage_events == 0`）。
4. **12 小时（`43,200 s`）零 eMMC NVRAM 磨损耐久闭环**：
   - 逐秒仿真 `43,200` 秒内的卷号递增（`800` 次）、白平衡色温切换（`144` 次）、3D LUT 切换（`72` 次）、ShotMark 标记（`240` 次）与 Tally 状态切换（`720` 次），证明 **100%（`1,976 / 1,976`）** `BKID`/NVRAM 更新均命中易失 RAM-Shadow 页，物理内部 eMMC（`/dev/mmcblk0p1..p15` 与 `/dev/mmcblk0rpmb`）保持 **0 扇区写入（`emmc_sector_writes == 0`）** 与 **0 磨损均衡递增（`emmc_wear_level_increments == 0`）**，并在周期性 NVRAM 刷写误开启时失败关闭。

### Phase 103 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 17 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/wireless_emi_exfat_endurance_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/wireless_emi_exfat_endurance_emulator.py --self-test --json

# 2. 全板 17 阶段（Stage 1..17）统一校验（本地 ~1.34s < 1.6s，洁净室 ~0.46s < 0.55s，支持 --skip-phase103）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 103 36 项单测 & 全量 532 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_wireless_emi_exfat_endurance_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_wireless_emi_exfat_endurance_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 107：Stage 18 C2PA 2.1 `cnflasha` 密钥库零触碰防火墙、E 卡口 12 针镜头暗角/色差 vs 无触点 PL 身份仲裁器、Monitor & Control 4 机位有线 USB-LAN 机队同步、及 G31/G32 假电池 OVP 撬棒 HIL

[`c2pa_shading_mcfleet_ovp_emulator.py`](c2pa_shading_mcfleet_ovp_emulator.py) 作为 **Stage 18** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase107_c2pa_shading_mcfleet_ovp=True`，可通过 `--skip-phase107` 向后兼容跳过；全板 18 阶段协同仿真在本地只读供体模式下保持 `< 1.7s`、洁净室模式下 `< 0.6s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`physical_device_writes == 0`**、**`cnflasha_mutation_bytes == 0`**、**`private_key_reads == 0`**、**`private_key_exports == 0`**、**`wf12_00342260_hits == 0`**、**`cxd90057_pmic_damage_events == 0`**、**`emount_flange_damage_events == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成四大闭环：

1. **严格只读（`os.O_RDONLY`）证书/SPAcc/E 卡口/有线以太网/USB-PD 供体审计 + 洁净室回退**：
   - 检查 FX3 `v7.02` 与 FX6 `v6.01` 共 10 份紧凑构件（`libCertificateManager.so` x2、`libInfraCertificate.so`、`libspaccdev.so`、`libInfraLensCommunicator.so` x2、`libNetServiceEther.so` x2、`cdc_ncm.ko`、`libBusPower.so`）的 SHA-256 与关键导出/符号标记（`CertificateManager`、`spaccdev`、`LensCommunicator`、`netserviceether_init`、`NseMiscSetEtherRemoteAccess`、`cdc_ncm`、`BusPower` 等）；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **C2PA 2.1 / `cnflasha` 密钥库只读隔离沙箱与防伪造门控**：
   - 仿真 Stage-B 剪辑封口时的 `cnflasha` / `RPMB` 密钥库零触碰防火墙：100% 阻断私钥读取/导出（`BLOCKED_C2PA_PRIVATE_KEY_ACCESS`，`private_key_reads == 0`、`private_key_exports == 0`）、阻断对 `cnflasha*`/`RPMB`/`SPAcc`/`RQ_LIC.DAT` 的写入与读写挂载（`BLOCKED_CNFLASHA_RPMB_KEYVAULT_MUTATION`，`cnflasha_mutation_bytes == 0`）、阻断跨机身 FX6/伪造证书欺骗（`BLOCKED_CROSS_BODY_CERT_SPOOFING`）与硬件背书伪造（`BLOCKED_C2PA_PROVENANCE_FORGERY`），并在内存 `NonRealTimeMeta` 中诚实标注 `CLEAN_ROOM_RESEARCH_UNATTESTED`（`<HardwareAttestationClaimed>false</HardwareAttestationClaimed>`）。
3. **E 卡口 12 针镜头暗角/色差/畸变多项式 vs 无触点手动 PL/变形镜头热插拔仲裁器**：
   - 建模从电子触点索尼 FE 24-70mm F2.8 GM II（`SEL2470GM2`，12 针 UART 激活 -> 应用 `cos^4` 径向暗角 `1.305891x @ r=0.85`、横向色差 `R/B`、Brown-Conrady 畸变与呼吸补偿多项式）实时热插拔至无电子触点手动 PL-to-E 变形定焦（`ATLAS_ORION_40MM_2X_PL_UNCHIPPED`，0 触点）：在 **`0.42 ms < 16.6833 ms`（`< 1 帧`）** 内瞬间复位全部暗角/色差/畸变/呼吸表至 **`1.0x` 恒等表**，实现 **`0` 帧陈旧 GM 系数泄漏**，并对 12 针 UART EEPROM 校验和损坏与陈旧系数滞留故障均执行失败关闭拦截。
4. **Sony Monitor & Control 4 机位有线千兆 USB-LAN（`CDC-NCM` / `RTL8153`）机队同步 + `P12` 射频围栏**：
   - 建模 4 机位有线以太网机队（`A-Cam` FX6 主控 + `B/C/D-Cam` FX6-on-FX3）通过 `CDC_NCM_RTL8153`（`1000 Mbps`、`PTP-IP 15740`）并发流式传输 `FALSE_COLOR` / `WAVEFORM` / `FOCUS_MAP` 遥测并执行亚毫秒级 **Gang REC 启停（`0.204 ms` 启停偏斜 / `<= 64 us` PTP 时钟偏斜）**，同时保持 `P12` `BK4\0` Wi-Fi/BT 射频 100% 静默（`0` `WF-12` `00342260` 命中），并阻断未受支持的 `RNDIS`/百兆网卡及射频越界。
5. **G31/G32 非稳压 16.8V/26.0V 假电池 OVP 撬棒与无支撑 PL 悬臂过载 HIL**：
   - 注入 `16.8V`（`G31`）与 `26.0V`（`G32`）非稳压假电池浪涌，验证启动前 OVP 撬棒隔离延迟 **`21.59 us` / `12.85 us < 50.0 us`**、PMIC 瞬态峰值钳位至 `<= 8.825V < 9.6V`（`cxd90057_pmic_damage_events == 0`）；同时对无支撑 `> 1.8 N*m`（`2.6 N*m`）PL 重型悬臂负载立即触发卡口应力互锁并闭锁 IBIS 线圈上电（`emount_flange_damage_events == 0`），而介入 15mm 导管支撑将等效法兰力矩降至 `0.728 N*m <= 1.8 N*m` 后安全放行。

### Phase 107 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 18 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/c2pa_shading_mcfleet_ovp_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/c2pa_shading_mcfleet_ovp_emulator.py --self-test --json

# 2. 全板 18 阶段（Stage 1..18）统一校验（本地 < 1.7s，洁净室 < 0.6s，支持 --skip-phase107）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 107 36 项单测 & 全量 568 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_c2pa_shading_mcfleet_ovp_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_c2pa_shading_mcfleet_ovp_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 112：Stage 19 ITU-R BT.2100 / ARIB STD-B67 HLG（HLG1/2/3 & BT.2020）管线、CTA-861.3 HDMI HDR `0x87` InfoFrame 合成器、Gamma Display Assist EVF/LCD 零泄漏隔离、与 G33/G34 烟油/盐雾/无线跟焦/云台 CoG HIL

[`hdr_hlg_assist_fiz_gimbal_emulator.py`](hdr_hlg_assist_fiz_gimbal_emulator.py) 作为 **Stage 19** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase112_hdr_hlg_fiz_gimbal=True`，可通过 `--skip-phase112` 向后兼容跳过；全板 19 阶段协同仿真在本地只读供体模式下保持 `~1.35s < 1.8s`、洁净室模式下 `~0.48s < 0.65s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`physical_device_writes == 0`**、**`display_assist_burn_in_frames == 0`**、**`xavc_clean_feed_leakage_events == 0`**、**`fiz_gear_strip_events == 0`**、**`ibis_coil_saturation_events == 0`**、**`duct_salt_haze_ingestion_damage_events == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成四大闭环：

1. **严格只读（`os.O_RDONLY`）HLG / Gamma Assist / HDMI / 风扇 / 镜头供体审计 + 洁净室回退**：
   - 检查 FX3 `v7.02` 与 FX6 `v6.01` 共 10 份紧凑构件（`string_english_f.uxc`、`string_english_g.uxc`、`string_english.uxc`、`string_english_2.uxc`、`dataflowInfraFramework.so`、`libGetLog.so`、`libInfraCCPFStatic.so`、`libfan.so` x2、`libInfraLensCommunicator.so`）的 SHA-256 与关键字节标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **ARIB STD-B67 HLG1/HLG2/HLG3 & `BT.2020 <-> BT.709` 色域矩阵管线**：
   - 实现 `HLG1`（87% 拐点 -> 10-bit 合法峰值 `826`）、`HLG2`（95% 拐点 -> `896`）、`HLG3`（100% 拐点 -> `940`）与 FX6 `HLG_LIVE` / `HLG_NATURAL` 精确分段 OETF/EOTF，验证 CIE-1931 `BT.2020 <-> BT.709` 3x3 线性色域矩阵可逆性（`D65` 白点行和为 `1.0`，逆矩阵残差 `< 1e-12`）与全覆盖 10-bit 代码值往返 **0 LSB 误差**，并对 `BT.2020`-in-`BT.709` 容器标签错配执行失败关闭拦截（`BLOCKED_MISMATCHED_BT2020_IN_BT709_CONTAINER`）。
3. **CTA-861.3 HDMI HDR `0x87` InfoFrame 合成校验 + EVF/LCD Gamma Display Assist 零泄漏隔离**：
   - 合成并反向解析验证标准 30 字节 CTA-861.3 动态范围与母版 InfoFrame（`type=0x87`、`version=0x01`、`length=26`、模 256 校验和 `(0x100 - sum) & 0xFF == 0`、`EOTF=0x03` HLG BT.2100 对比 `EOTF=0x00` SDR），并将错误校验和/长度/保留 EOTF 帧失败关闭拦截。
   - 建模 `GPE0` EVF/LCD Gamma Display Assist（`S-Log3->709(800%)` 与 `HLG(BT.2020)->709`），证明 Assist LUT 仅作用域隔离在本地监看渲染路径，**0 帧烧录泄漏**进入机内 XAVC 录制流或 Clean-HDMI 输出（`display_assist_burn_in_frames == 0`、`xavc_clean_feed_leakage_events == 0`）。
4. **G33/G34 盐雾/烟油风道 & 无线跟焦硬止点/云台变焦 CoG 振荡 HIL**：
   - 注入未防护沿海盐雾、高浓度丙二醇烟油（`> 25 mg/m^3` 且累计 `> 45 min` 未吹扫）与细碱尘进气事件，验证系统自动发布优雅的 `GPE0` 风道保护告警（`18%` / `950 RPM` 保护节流、**0 WDT 复位**、**0 硬件损伤**）。
   - 注入未校准 `> 2.5 N*m`（`3.2 N*m`）无线 FIZ 硬止点撞击与 `22 mm` 伸缩变焦云台重心漂移（`64.2 Hz` 共振，落入 `40..90 Hz` 区间），验证 `0.85 ms` 瞬时 FIZ 扭矩软限幅钳位（`1.15 N*m < 1.2 N*m`、**0 扫齿**）与 Stock-CP `0x0400` IBIS 音圈防饱和中心阻尼保护（`210.0 mA <= 450.0 mA`、**0 饱和事件**、`cp_mutation_bytes == 0`）。

### Phase 112 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 19 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/hdr_hlg_assist_fiz_gimbal_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/hdr_hlg_assist_fiz_gimbal_emulator.py --self-test --json

# 2. 全板 19 阶段（Stage 1..19）统一校验（本地 ~1.35s < 1.8s，洁净室 ~0.48s < 0.65s，支持 --skip-phase112）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 112 36 项单测 & 全量 604 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_hdr_hlg_assist_fiz_gimbal_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_hdr_hlg_assist_fiz_gimbal_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 117：Stage 20 外接 Atomos/Blackmagic ProRes RAW / BRAW 16→12-Bit Log 元数据握手、E 卡口 12 针呼吸补偿 FOV 裁剪 vs PL/RAW 旁路、MI-Shoe I2S 48kHz 主时钟 PLL 锁定、及 G35/G36 AOC HDMI +5V / CFexpress NVMe 热限与开盖急救 HIL

[`hdmi_raw_prores_breathing_mishoe_aoc_emulator.py`](hdmi_raw_prores_breathing_mishoe_aoc_emulator.py) 作为 **Stage 20** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase117_proresraw_breathing_mishoe_hil=True`，可通过 `--skip-phase117` 向后兼容跳过；全板 20 阶段协同仿真在本地只读供体模式下保持 `~1.17s < 1.8s`、洁净室模式下 `~0.29s < 0.7s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`physical_device_writes == 0`**、**`raw_lut_burn_in_frames == 0`**、**`pl_breathing_stale_crop_frames == 0`**、**`audio_pop_click_frames == 0`**、**`sy1129_hdmi_fuse_damage_events == 0`**、**`cfexpress_fat_corruption_events == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成四大闭环：

1. **严格只读（`os.O_RDONLY`）FX3/FX6 RAW / 镜头 / 热靴 / 媒体供体审计 + 洁净室回退**：
   - 检查 FX3 `v7.02` 与 FX6 `v6.01` 共 10 份紧凑构件（`string_english.uxc`、`string_english_g.uxc`、FX6 `string_english.uxc`、`string_english_2.uxc`、`libInfraLensCommunicator.so`、`libInfraHotshoe.so`、`libInfraAdjMedia.so`、`libInfraMediaConfig.so`、`libInfraMediaDetect.so`、`libInfraMediaCommon.so`）的 SHA-256 与关键符号/字符串标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Pillar A — 外接 HDMI 16-Bit 线性 → 12-Bit Log（`Atomos Ninja ProRes RAW` / `Blackmagic Video Assist BRAW`）握手与零烧录纯净流**：
   - 实现 `$C^1$` 平滑暗部趾部 16→12-bit Log 压扩器（`15.0 stops >= 14.5 stops` 动态范围、`2048 ADU` OB 钳位往返 `0` 漂移、`[0..512]` 暗部单调单射）、31 字节 CTA-861 Vendor-Specific InfoFrame（`type=0x81`，模 256 校验和为 `0`）与 56 字节 `SONYRAW1` 元数据包（`Base ISO 800 / 12800`、`Kelvin/Tint`、焦距/T-stop、`S-Gamut3.Cine` Q13 矩阵与 CRC-32）。
   - 验证本地 `GPE0` Display Assist LUT 仅作用于机内监看渲染，外发 HDMI RAW 流保持 **0 帧 LUT/OSD 烧录污染**（`raw_lut_burn_in_frames == 0`），并对非 Log 拍摄、校验和破坏及烧录泄漏故障执行失败关闭拦截。
3. **Pillar B — E 卡口 12 针 `Focus Breathing Compensation` 动态 FOV 裁剪（`1.00x..1.08x`）vs 无触点 PL / HDMI RAW `< 0.5 ms` 恒等旁路**：
   - 建模 6 支索尼 E 卡口 12 针镜头随对焦距离 `u_mm` 连续平滑插值的呼吸补偿视场缩放曲线（`1.00x..1.08x`）；当切换无触点 PL 转接环、启用 HDMI RAW 输出或 S&Q 120p 高帧率时，在 **`0.18–0.22 ms < 0.5 ms`**（`< 1` 帧）内确定性旁路复位至 **`1.000x`** 恒等映射（`pl_breathing_stale_crop_frames == 0`），并失败关闭拦截强行裁剪或陈旧系数残留。
4. **Pillar C — `MI-Shoe` 4 通道 24-Bit / `48 kHz` `I2S` 数字音频（`XLR-H1` / 无线数字接收器）主时钟 Fractional-N PLL 锁定与热拔零爆音回退**：
   - 在 `23.976p..59.94p`（含 `29.97p` `(1602,1601,1602,1601,1602)` 与 `59.94p` `(801,801,801,801,800)` 5 帧 NTSC 步进）12 小时（`43,200 s`）连续运行下实现与 `CXD90057` 视频时钟的 **Fractional-N PLL 零漂移锁定（`0.0 < 0.20` 采样/小时）**。
   - 仿真拍摄中热拔 MI-Shoe：通过 `P11` Smart Handle 队列（`0x91db059b -> 0x88000002`）触发零过零斜坡切换至内部晶振保持（`INTERNAL_CRYSTAL_HOLDOVER`），保证 **`audio_pop_click_frames == 0`** 与 `ivshmem_tx_leaks == 0`。
5. **Pillar D — `G35` & `G36` 硬件在环（AOC HDMI Pin-18 `+5V` 与 CFexpress Type-A NVMe 热限 / VPG 写底线 / 卡仓门紧急 FAT 日志 HIL）**：
   - `G35`：`AOC` 有源光缆 HDMI Pin-18 `+5V` 请求 `> 55 mA`（`125 mA`）时负载开关即时钳位至 `55.0 mA`，外部供电反灌 `> 5.35V`（`5.85V`）时在 **`16.4 us < 40 us`** 内切断隔离，保持 **`sy1129_hdmi_fuse_damage_events == 0`**。
   - `G36`：`CFexpress Type-A` 温度 `> 82°C`（`84.5°C`）触发 NVMe `PS1_THROTTLED` 热限预警；校验 `4K120p XAVC S-I 600 Mbps`（`93.75 MB/s` 写入底线）要求 `VPG200/VPG400` 认证卡并拦截 `V30`/低速卡；并在缓存刷盘期间打开卡仓门时于 `2.8 ms` 内提交紧急 exFAT 日志，确保 **`exfat_volume_dirty_bit == 0`** 与 **`cfexpress_fat_corruption_events == 0`**。

### Phase 117 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 20 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/hdmi_raw_prores_breathing_mishoe_aoc_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/hdmi_raw_prores_breathing_mishoe_aoc_emulator.py --self-test --json

# 2. 全板 20 阶段（Stage 1..20）统一校验（本地 ~1.17s < 1.8s，洁净室 ~0.29s < 0.7s，支持 --skip-phase117）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 117 40 项单测 & 全量 644 项单测（双模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_hdmi_raw_prores_breathing_mishoe_aoc_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_hdmi_raw_prores_breathing_mishoe_aoc_emulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
```

## Phase 121：Stage 21 USB-C UVC 1.5 / UAC 2.0 推流协商、P12 安全有线 SRT / RTMPS 直播、CRSDK PTP / PTP-IP 属性转换与刷写防误触防火墙、及 G37/G38 20V USB-PD 诱骗 / 15 针 Multi-Terminal / 1.8V UART HIL

[`usb_uvc_uac_srt_crsdk_usbpd_emulator.py`](usb_uvc_uac_srt_crsdk_usbpd_emulator.py) 作为 **Stage 21** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase121_uvc_srt_crsdk_usbpd_hil=True`，可通过 `--skip-phase121` 向后兼容跳过；全板 21 阶段协同仿真在本地只读供体模式下保持 `~1.16s < 1.8s`、洁净室模式下 `~0.28s < 0.7s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`physical_device_writes == 0`**、**`emmc_flash_mutation_bytes == 0`**、**`wf12_00342260_hits == 0`**、**`cxd90057_pad_damage_events == 0`**、**`uvc_osd_burn_in_frames == 0`**、**`srt_dropped_gops == 0`**、**`uart_tx_bytes == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成五大闭环：

1. **严格只读（`os.O_RDONLY`）UVC / Streaming / PTP / USB-LAN / USB-BusPower 供体审计 + 洁净室回退**：
   - 检查 FX3 `v7.02` 与 FX6 `v6.01` 共 12 份紧凑构件（`string_english_g.uxc`、FX6 `string_english.uxc`、`string_english_2.uxc`、`libInfraVericLiveStreaming.so`、`libInfraPtpControl.so` x2、`libptp.so`、`libNetServiceEther.so`、`cdc_ncm.ko`、`rndis_host.ko`、`libUsbBusPower.so`、`libBusPower.so`）的 SHA-256 与 36+ 条关键符号/字节标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Pillar A — USB-C `UVC 1.5`（`4K30p MJPEG`、`1080p60p YUY2/MJPEG`）& `UAC 2.0`（`48kHz` 16-bit 2ch PCM `1.536 Mbps`）SuperSpeed `5 Gbps` vs High-Speed `480 Mbps` 协商器**：
   - 合成并 CRC-32 校验 44 字节 `UVC 1.5` (`0x0150`) + `UAC 2.0` (`0x0200`) 描述符束；当接入 USB 2.0 线缆（`480 Mbps` 线速 / `320 Mbps` 净荷上限）时自动将 `1080p60p YUY2`（`1992.192 Mbps`）降档至 `1080p60p MJPEG`（`76.536 Mbps < 480 Mbps`），确保等时/批量净荷永不越界，并保持外发 UVC 干净画面零 OSD 烧录（`uvc_osd_burn_in_frames == 0`），同时在未允许降档或 S&Q / HDMI RAW16 互斥时失败关闭拦截。
3. **Pillar B — `P12` 射频静默有线 `USB-LAN`（`CDC-NCM / RNDIS`）`SRT`（`Caller/Listener`、`PBKEYLEN` `AES-128 / AES-256`、`20..1000 ms` ARQ 抗 `8%` 丢包零 GOP 丢失）& `RTMPS` TLS 1.3 直播推流**：
   - 强制锁定有线网卡（`CDC_NCM_RTL8153` / `CDC_NCM_AX88179` / `USB_RNDIS_WIRED`），在触发任何 WF-12 锁死前拦截全部 Wi-Fi / P2P / BT-PAN / 蜂窝传输（`wf12_00342260_hits == 0`）；验证 `SRT` 在 `8%` 模拟丢包下跨越 `10` 个 GOP 实现 **0 丢帧/0 丢 GOP**，并验证 `RTMPS TLS 1.3` + Root-CA 校验与明文 `RTMP` 拦截。
4. **Pillar C — 索尼 `CRSDK` `PTP / PTP-IP`（`0x054C`）厂商属性转换器 & 破坏性固件刷写 Opcode 防火墙**：
   - 在 `USB_PTP`（`512 B` bulk 对齐）与 `WIRED_PTPIP_15740` 上精确映射 `0xD2xx` Cinema Line 属性（`Cine EI` `0xD243`、`Base ISO 800/12800` `0xD244`、`User 3D-LUT` `0xD253`、`Shutter Angle` `0xD20D`、`Rec` `0xD215`），并在 `ILME-FX3` 上将 `P4` 电子可变 ND（`0xD25A`）安全钳位至 `Clear (0)`（`p4_nd_motor_faults == 0`）。
   - 在混合 Stage-B 模式下对所有破坏性 `0x9280..0x928F` / `0x100C` / `0x100D` / `0x9805` / `0x92F0..0x92F2` OTA/Flash 写入指令及 `\\x89UFU` / `UDTRFIRM` / `BODYDATA.DAT` 载荷执行硬拒绝（`emmc_flash_mutation_bytes == 0`）。
5. **Pillar D — `G37` & `G38` 硬件在环（`20V` D-Tap 转 USB-C 诱骗线 OVP 撬棒 & `15 针 Multi-Terminal` / `1.8V` 被动 RX UART HIL）**：
   - `G37`：对比合法 `9V/3A`（`27W`）USB-PD PDO 契约与未协商 `20V` D-Tap 诱骗线浪涌，验证 VBUS OVP 撬棒在 **`18.2 us < 35 us`** 内钳位隔离（PMIC 峰值 `8.92V < 9.6V`），并验证 `D-Tap + USB-PD` 双电源隔离器将跨源反灌电流抑制至 `0.0 mA`（`cxd90057_pad_damage_events == 0`）。
   - `G38`：对 `15-pin Multi-Terminal` 注入 `> 5.0 Vpp`（`6.2 Vpp`）LTC 时码时触发 `3.30V <= 3.35V` 保护钳位；对 `3.3V / 5.0V` UART 过驱及主动 TX 注入执行硬拦截，强制 `1.8V` 被动仅收模式 **`tx_bytes == 0`** 且 **`cxd90057_pad_damage_events == 0`**。

### Phase 121 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 21 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/usb_uvc_uac_srt_crsdk_usbpd_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/usb_uvc_uac_srt_crsdk_usbpd_emulator.py --self-test --json

# 2. 全板 21 阶段（Stage 1..21）统一校验（本地 ~1.16s < 1.8s，洁净室 ~0.28s < 0.7s，支持 --skip-phase121）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 121 40 项单测 & 全量 684 项单测（双模式）
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_usb_uvc_uac_srt_crsdk_usbpd_emulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_usb_uvc_uac_srt_crsdk_usbpd_emulator.py -v
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
```

## Phase 127：Stage 22 `XAVC MXF OP1a <-> MP4 RDD-18/UMID` 元数据与净荷桥接、`SMPTE ST 2059-2 PTPv2` vs `LTC` 亚微秒同步、`P12` 安全有线 `TSL UMD v5.0` Tally 与 `G39/G40` 暴雨热靴 / 笼架扭转 FFD HIL

[`mxf_mp4_ptpv2_tally_monsoon_emulator.py`](mxf_mp4_ptpv2_tally_monsoon_emulator.py) 作为 **Stage 22** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase127_mxf_ptpv2_tally_monsoon_hil=True`，可通过 `--skip-phase127` 向后兼容跳过；全板 22 阶段协同仿真在本地只读供体模式下保持 `~1.39s < 1.8s`、洁净室模式下 `~0.51s < 0.7s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`calibration_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`bk4_persistent_nvram_writes == 0`**、**`physical_device_writes == 0`**、**`emmc_mutation_bytes == 0`**、**`dropped_klv_tags == 0`**、**`frame_essence_reencode_loss == 0`**、**`wf12_00342260_hits == 0`**、**`fx6_green_gpio_faults == 0`**、**`mishoe_rail_corrosion_events == 0`**、**`chassis_damage_events == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成五大闭环：

1. **严格只读（`os.O_RDONLY`）16 份 FX3 `v7.02` / FX6 `v6.01` 供体审计 + 洁净室回退**：
   - 检查 `string_english.uxc`、`string_english_g.uxc`、FX6 `string_english.uxc` / `string_english_2.uxc`、FX3/FX6 `global.xdb`、`libInfraPtpControl.so`、`libNetServiceEther.so`、`cdc_ncm.ko`、`rndis_host.ko`、`libInfraHotshoe.so`、FX3/FX6 `libInfraLensCommunicator.so`、FX3/FX6 `libBusPower.so` 与 FX3 `libmpr.so`（合计 `~4.5 MB`）的 SHA-256 与 42+ 条关键符号/字节标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线（`mutation_bytes == 0`）。
2. **Pillar A — `XAVC MXF OP1a`（`SMPTE ST 377-1 / RDD-09 / RDD-18`）<-> `FX3 MP4 ISO-BMFF`（`rtmd` KLV + `.XML` `NonRealTimeMeta` + `.CUBE` 3D-LUT）无损双向桥接**：
   - 双向无损重封装（`XAVC-I <-> XAVC S-I`）全程保持 32 字节 `SMPTE 330M` Basic `UMID`、CRC-32 校验 `rtmd` KLV 包（`ExposureIndex`、双原生 ISO `800/12800`、`CaptureGammaEquation`、`CaptureColorPrimaries`、帧率、光圈、快门角、色温、`.CUBE` 路径）与 `.XML` 边车，实现 **`dropped_klv_tags == 0`** 与 **`frame_essence_reencode_loss == 0`**（`essence_sha256_preserved == True`）。
   - 失败关闭拦截跨编码无损直转、未转换原始 `MXF OP1a` 直写 FX3 `MP4` 卡槽、`rtmd` CRC 损坏及伪造 `SPVC` 认证指纹。
3. **Pillar B — `SMPTE ST 2059-2 PTPv2` 亚微秒级有线时钟伺服 & `15-Pin Multi-Terminal` `LTC` 8 小时无毛刺保持**：
   - 在 `P12` Wi-Fi 强制关闭（`wf12_00342260_hits == 0`）的有线 `CDC-NCM / RNDIS` 链路上运行 `ST 2059-2`（`Announce / Sync / Follow_Up / Delay_Req / Delay_Resp`），硬件时间戳伺服达到 **`0.184 us < 0.5 us`** RMS 偏差，软件降级伺服达到 `0.342 us < 0.5 us`。
   - 有线网口断开后无毛刺平滑切换至 `15-Pin Multi-Terminal` `LTC`（`VMC-BNCM1`）保持，8 小时（`28,800 s`）累计相位漂移仅 **`0.01726 < 0.05` 帧**且 **0 丢帧**；同时拦截 `PTP-IP` 混用、无线/蓝牙/蜂窝通道及 `uart_boot` 引脚冲突。
4. **Pillar C — 广电 `TSL UMD v5.0`（有线 `CDC-NCM` UDP/TCP）`PGM` 红 / `PVW` 绿 Tally 与 `16-char` UTF-8/ASCII 台标桥接**：
   - 解析小端 `TSL UMD v5.0` UDP 与 TCP `DLE/STX`（`0xFE 0x02`）帧及 `16-char` 台标，驱动 FX3 前/顶/后三向 Tally LED：`PGM Red` 点亮前/顶/后红灯 + `RED` OSD；`PVW Green` 保持物理红灯严格关闭 + `GREEN` OSD 且 **`fx6_green_gpio_faults == 0`**；**`OFF` 隐身覆盖（Stealth Override）** 即使处于 `PGM` 也强制熄灭全部物理 LED。全程受 `P12` 保护（`wf12_00342260_hits == 0`）。
5. **Pillar D — `G39` & `G40` 硬件在环（暴雨渗水 `24-Pin MI-Shoe` 负载开关 & `XLR-H1` 甩击 / 笼架扭转 FFD 互锁）**：
   - `G39`：暴雨渗水导致 `24-pin MI-Shoe` 阻抗跌破 `50 kOhm`（`18.5 kOhm`）时，负载开关在 **`14.8 us < 25 us`** 内硬件分断，隔离 `+3.15V/+5V` 供电轨防止电化学腐蚀（`mishoe_rail_corrosion_events == 0`），并联动检查无盖淋雨及侧门未闭毛细渗水告警。
   - `G40`：`XLR-H1` 手柄载荷超 `2.8 kg`（`3.45 kg`）触发甩击剪力告警、`1/4"-20` 底孔扭矩超 `3.5 N*m`（`4.15 N*m`）触发滑牙保护，以及非对称提笼扭转导致 E 卡口 `18.00 mm` 法兰距（`FFD`）翘曲超 `12 um`（`16.8 um`）时立即触发刚性互锁，确保 **`chassis_damage_events == 0`**。

### Phase 127 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 22 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/mxf_mp4_ptpv2_tally_monsoon_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/mxf_mp4_ptpv2_tally_monsoon_emulator.py --self-test --json

# 2. 全板 22 阶段（Stage 1..22）统一校验（本地 ~1.39s < 1.8s，洁净室 ~0.51s < 0.7s，支持 --skip-phase127）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 127 40 项单测 & 全量 724 项单测（双模式）
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_mxf_mp4_ptpv2_tally_monsoon_emulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_mxf_mp4_ptpv2_tally_monsoon_emulator.py -v
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
```

## Phase 132：Stage 23 虚拟制片 LED-Volume `Brompton/Megapixel` 抗频闪分数 `ECS` 求解器、有线 `FreeD (0xD1 29-Byte)` 镜头追踪 -> `Unreal LiveLink` 桥接、`P12` 安全 `Art-Net 4 / sACN` 同步与 `G41/G42` 锁相冲突 / 直升机 IBIS 共振 HIL

[`vp_ledwall_freed_artnet_vib_emulator.py`](vp_ledwall_freed_artnet_vib_emulator.py) 作为 **Stage 23** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase132_vp_ledwall_freed_artnet_hil=True`，可通过 `--skip-phase132` 向后兼容跳过；全板 23 阶段协同仿真在本地只读供体模式下保持 `~1.30s < 1.8s`、洁净室模式下 `~0.50s < 0.7s`），在严格保持 **`cp_mutation_bytes == 0`**、**`wbi_mutation_bytes == 0`**、**`calibration_mutation_bytes == 0`**、**`nvram_persistent_writes == 0`**、**`bk4_persistent_nvram_writes == 0`**、**`physical_device_writes == 0`**、**`emmc_mutation_bytes == 0`**、**`wf12_00342260_hits == 0`**、**`flash_split_band_frames == 0`**、**`cxd90057_pin_damage_events == 0`**、**`imx510_sensor_burn_events == 0`**、**`ibis_endstop_slam_events == 0`**、**`ibis_coil_thermal_runaway_events == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成五大闭环：

1. **严格只读（`os.O_RDONLY`）16 份 FX3 `v7.02` / FX6 `v6.01` 供体审计 + 洁净室回退**：
   - 检查 FX3/FX6 `string_english*.uxc`、`global.xdb`、`libInfraLensCommunicator.so`、`libNetServiceEther.so`、`cdc_ncm.ko`、`rndis_host.ko`、`libInfraMultiIF.so`、`libInfraPtpControl.so`、`libptp.so` 与 `cpapp-b.bin` 等 16 份紧凑构件（合计 `~1.67 MB`）的 SHA-256 与 34+ 条关键符号/字节标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线（`mutation_bytes == 0`）。
2. **Pillar A — 虚拟制片 LED-Volume `IMX510` 卷帘快门 & `Brompton Tessera / Megapixel HELIOS` 分数 `ECS` 求解器**：
   - 建模 `IMX510` 卷帘读出（`4K120p 8.7 ms` / `4K24p 13.2 ms`）与扫描复用 LED 墙（`1/8`、`1/16`、`960..7680 Hz` PWM），自动求解与扫描周期及 PWM 整数倍锁定的安全分数 `ECS` 快门：锁定时亮度条纹残差 **`< 0.5%`**（`0.195%` / `0.264%`），未锁定（如 `125 Hz` 非整倍快门或 Genlock 失锁）准确检出 **`> 18%`** 频闪条纹故障并拦截。
3. **Pillar B — 有线 `FreeD 0xD1`（`29-Byte` UDP 包，`0x40 - sum` mod 256 校验和）E 卡口 12 针镜头追踪 -> `Unreal LiveLink` 桥接**：
   - 在严格 `P12` Wi-Fi-OFF（`wf12_00342260_hits == 0`）的有线 `CDC-NCM` / `RNDIS` 链路上编码/校验 `29-byte` `FreeD 0xD1` UDP 包，以 **`60/120 Hz`**、**`< 1.2 ms`**（实测 `0.54 ms` / `0.72 ms`）端到端延迟推送 Focus/Zoom/Iris 与 6-DoF 位姿至 Unreal Engine `LiveLink`；面对无触点 PL 电影镜头时无缝切换中性编码器基线（`0x800000` / `0x0000`），同时拦截 RF 违反、超延迟与校验和错误。
4. **Pillar C — `P12` 安全有线 `Art-Net 4`（`OpDmx 0x5000` UDP `6454`）& `sACN`（`E1.31`）DMX 闪电/闪光帧边界同步器**：
   - 真实编解码 `Art-Net 4` 与 `ANSI E1.31 sACN` DMX 数据包，将闪光/雷电触发严格对齐至 `IMX510` VSYNC 帧边界（`aligned_fire_phase_ms = 0.0`），消除卷帘快门半帧撕裂条带（`flash_split_band_frames == 0`、`wf12_00342260_hits == 0`），并拒收未同步半帧撕裂与无线发射企图。
5. **Pillar D — `G41` & `G42` 硬件在环（`Tri-Level Genlock / 5V TTL Word-Clock` 误插隔离、UV 弧光辐照保护与直升机/追车台 IBIS 机械停泊 + `2000 Hz RTMD`）**：
   - `G41`：当三电平 Genlock 或 `5V TTL` 字时钟误接入 FX3 `仅限 LTC` `15 针 Multi-Terminal` 时，在 **`12.4 us < 20 us`** 内触发硬件过压/高频隔离（`cxd90057_pin_damage_events == 0`），并联动近距 UV 电弧/强闪光辐照阈值保护（`imx510_sensor_burn_events == 0`）。
   - `G42`：直升机/追车臂 `> 1.8 g`、`20..200 Hz` 共振下通过 Stock-CP `0x0400` 自动将 5 轴 IBIS 音圈切换至 **`OFF_MECHANICAL_PARK`**（`vcm_drive_ma == 0.0`、`cp_mutation_bytes == 0`）并维持 **`2000 Hz` `RTMD`** Gyroflow 采集，保证 **`ibis_endstop_slam_events == 0`** 与 **`ibis_coil_thermal_runaway_events == 0`**。

### Phase 132 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 23 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/vp_ledwall_freed_artnet_vib_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/vp_ledwall_freed_artnet_vib_emulator.py --self-test --json

# 2. 全板 23 阶段（Stage 1..23）统一校验（本地 ~1.30s < 1.8s，洁净室 ~0.50s < 0.7s，支持 --skip-phase132）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 132 40 项单测 & 全量 764 项单测（双模式）
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_vp_ledwall_freed_artnet_vib_emulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_vp_ledwall_freed_artnet_vib_emulator.py -v
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests
```

## Phase 141：Stage 24 全板端到端真机预刷写生命周期 & 四态双启动 HIL 仿真器

[`realhw_preflash_dualboot_lifecycle_emulator.py`](realhw_preflash_dualboot_lifecycle_emulator.py) 作为 **Stage 24** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase141_realhw_preflash_dualboot_hil=True`，可通过 `--skip-phase141` 向后兼容跳过；全板 24 阶段协同仿真在本地只读供体模式下保持 `~1.51s < 1.8s`、洁净室模式下 `~0.53s < 0.7s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`spi_nor_mutation_bytes == 0`**、**`cp_mutation_bytes == 0`**、**`calibration_mutation_bytes == 0`**、**`wf12_00342260_hits == 0`**、**`sector0_mutation_bytes == 0`**、**`physical_device_writes == 0`** 与 **`rsv_orphan_count == 0`** 的前提下完成五大闭环：

1. **严格只读（`os.O_RDONLY` + `mmap.ACCESS_READ`）9 份 FX3 `v7.02` / FX6 `v6.01` 供体审计 + 洁净室回退（`< 0.15s`）**：
   - 检查 FX3 `7.02` 与 FX6 `6.01` 的 `partinf.conf`、`pformat_config.txt`、`LdrBkupList.txt`、`libJiritsu.so`、`appFw.so` 与 `cpapp-b.bin` 共 9 份供体的 SHA-256 与 28+ 条关键符号/标记；在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Pillar A — `JIRITSU_SETFILE2_COLD_BACKUP_AND_SPACC_TOPOLOGY`**：
   - 建模完整 FX3 eMMC UDA（`Sector 0` `"8246"` `"2.00"` 30 项零重叠分区表 + `pnflasha1..30` + `crypt-emmc.ko` `cnflasha3/7/8/12/15/23/30` 透明 AES-XTS 边界 + `16 MiB` Octal-SPI NOR `infomisc.dat`/`loader_nor.bin`/`ddrtraining.dat @ 0x3e210fc`），并执行 Stage-288 入口自解链 `SET_FILE2` Tier-0/1/2 冷备份（`p6_peak_bytes < 4.5 MiB < 25 MiB`、`p6_residual_files == 0`、`100%` SHA-256 清单双次校验，拦截 `/tmp/jbusy`、`selector=0x02` 与 `CRC32` 篡改）。
3. **Pillar B — `CNFLASHA15_CIPHER_SAFE_INSTALL_AND_POWERCUT_ROLLBACK`**：
   - 仿真 A7C-II 风格文件级 Stage-B wrapper 经 `/dev/nflasha15`（`/dev/cnflasha15` SPACC 加密块设备）原子安装并重挂 `ro`；证明直接对 `/dev/pnflasha15` 明文写入被硬拦截（`SPACC_CIPHERTEXT_CORRUPTION_BLOCKED`）；注入写入中途断电拔电池，验证 `.orig` 日志恢复 `100%` 原厂 `im.elf` SHA-256 与 `ro` 只读状态。
4. **Pillar C — `FOUR_STATE_DUALBOOT_AND_NATIVE_REC_CLOSED_LOOP`**：
   - **路径 1（拔出 SD 卡物理逃生舱）**：直接启动 `100%` 原厂 FX3 `7.02`（`0` 个 Stage-B 挂钩，原生拍摄完整保留）。
   - **路径 2（插入合法签名 SD 清单）**：激活 Strategy-A（`/dev/nflasha20 -> /dev/nflasha30` + `tmpfs /etc/opelog`，`0` 字节 Sector-0 修改），启动 FX6 `6.01` `appFw.so` + `libMpr.so` ABI shim 驱动原厂 FX3 `cpapp-b.bin` 完成 XAVC S-I（`.MP4`）录制与封口（`rsv_orphan_count == 0`）。
   - **路径 3（插入篡改 SD 清单）**：在 `< 50 ms`（实测 `8.2 ms`）内 fail-closed 回退至原厂 FX3 `7.02`。
   - **路径 4（紧急 `p1` 单次救援启动）**：强制校验 `p1/p3` 互斥写入保护、`cfg.uart=1`（`460800 8N1`）与第 1 行 `rm -f /setting/updater/mode* && sync`，从冷备份恢复 `/usr` 并干净重启回原厂 `p3`。
5. **Pillar D — `HARDWARE_SAFETY_REDLINES_AND_ZERO_MUTATION_PROOF`**：
   - 硬锁定 `persistent_emmc_writes_authorized = False`、`spi_nor_mutation_bytes == 0`、`cp_mutation_bytes == 0`、`calibration_mutation_bytes == 0`、`wf12_00342260_hits == 0` 并阻断一切越界解锁请求。

### Phase 141 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 24 自检（< 0.15s）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_preflash_dualboot_lifecycle_emulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_preflash_dualboot_lifecycle_emulator.py --self-test --json

# 2. 全板 24 阶段（Stage 1..24）统一校验（本地 ~1.51s < 1.8s，洁净室 ~0.53s < 0.7s，支持 --skip-phase141）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 141 44 项单测 & 全量 808 项单测（双模式）
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_preflash_dualboot_lifecycle_emulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_preflash_dualboot_lifecycle_emulator.py -v
PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 145：Stage 25 真机主线 `FX6 appFw.so -> 原厂 FX3 libmpr.so / DmmCfg.bin` 插卡录制协同仿真器

[`realhw_mpr_dmm_recording_coemulator.py`](realhw_mpr_dmm_recording_coemulator.py) 作为 **Stage 25（25/25 阶段完成）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase145_realhw_mpr_dmm_rec=True`，可通过 `--skip-phase145` 跳过；全板 25 阶段协同仿真在本地只读供体模式下 `< 2.0s`、洁净室模式下 `< 0.8s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`emmc_nflasha_write_count == 0`**、**`cp_mutation_bytes == 0`**、**`dmm_allocated_after_stop == 0`**、**`m_user_count == 0`**、**`uipc_lock_depth == 0`**、**`rsv_orphan_count == 0`** 与 **`appfw_crashes == 0`** 的前提下完成五大闭环：

1. **双模式只读供体审计（`os.O_RDONLY` + `mmap.ACCESS_READ`）+ 洁净室回退（`< 0.08s`）**：
   - 检查 FX3 `7.02` 与 FX6 `6.01` 的 `libmpr.so`（`3,517,008 B` / `3,541` 导出含 `libsecvlt.so` 依赖 vs `28,921,824 B` / `4,271` 导出）、`appFw.so`（`50,520,424 B` / `89` 条 `libmpr.so` 导入 = `74` 透传 + `15` Shim）、`im.elf`（`40,920 B`）、AP `DmmCfg.bin`（`66,796 B` `603` 单元 vs `59,364 B` `556` 单元，含 `for ilc32g12m-ipsxmp` 邮戳）、CP `DmmCfg.bin`（`43,320 B` `348` 单元，含 `for ilc8g8g-ipsxcp` 邮戳）及 FX3 `libsecvlt.so`（`10,216 B` / `9` 导出），同时校验 Linux `4.9` AArch64 `ld-2.25.so` 强制要求的 `PT_LOAD p_align == 0x10000`（64 KiB）页对齐；`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 描述符。
2. **Pillar A — `LD_PRELOAD` `libmpr.so` + `libsecvlt.so` 符号与 ABI Shim 协同仿真器**：
   - 仿真 FX6 `appFw.so` 调用全部 **74** 项透传录制符号（含 `ExecEncStart`、`SetEncStartParam`、`EnqueueExecEncStart`、`EnqueueExecEncStop`、`DmmMemInfo::GetUnitInfo`、`ExecAudioEncStart/Stop`），安全拦截并放行 **15** 项 FX6 专属 SDI/RAW/Sub-Proxy 符号（`0` / `ENOENT_SAFE`），严格保留原厂 FX3 `libsecvlt.so` 绑定（`9` 导出），并在结构隔离守卫中阻断 `g_videoParamComb`（`312 B` vs `480 B`）/`s_movieRecInfo`（`3144 B` vs `5248 B`）直解引用以及非 64 KiB `PT_LOAD`（`0x1000`）加载。
3. **Pillar B — 原厂 FX3 `DmmCfg.bin` 内存池预算与零泄漏验证器**：
   - 覆盖 `4K 24p/60p/120p XAVC-I / XAVC-S / XAVC-HS 10-bit 4:2:2` + `S-Log3.Cine / Cine EI` MLUT 预览，证明峰值占用严格收敛在原厂 FX3 **20 个共享 `MAIN` DMM 单元**与 `512 MiB` 预算内，停录后 `dmm_allocated_after_stop == 0` 且 `m_user_count == 0`，并在溢出前拒收未屏蔽的 FX6 `SDI-RAW` 与 `Darwin-ND` 池请求。
4. **Pillar C — 物理 `REC` 按键 -> `ParameterControl` -> 双槽 `M4ROOT/CLIP` 生命周期**：
   - 仿真 `Standby` -> `REC_START` -> 6 项拍摄域 `ParameterControl` 翻译 -> `SIMUL` / `RELAY` Slot-A（`CFexpress Type A`）& Slot-B（`SDXC UHS-II`）虚拟 ExFAT 短片与非实时 XML（`M4ROOT/CLIP/A001C001_*.MP4` + `*.XML`，含 Cine EI 曝光指数与 `.cube` User 3D LUT 标签）-> `REC_STOP` -> `osal_uipc` `s_recordCounter == 0` 与 `s_movieRWlock` 锁深归零（`uipc_lock_depth == 0`）。
5. **Pillar D — 故障注入韧性与零持久化写入红线**：
   - 注入 `CARD_FULL_STOP`（卡满优雅 `EncWfiStop`）、`SLOT_A_HOT_PULL_RELAY_FAILOVER`（热拔 Slot-A 无缝切至 Slot-B）与 `LOW_BATTERY_ENCWFISTOP`（低电安全封口），验证 `appfw_crashes == 0`、`rsv_orphan_count == 0`、`emmc_nflasha_write_count == 0` 且 `persistent_emmc_writes_authorized == False`。

### Phase 145 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 25 自检（< 0.08s）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_mpr_dmm_recording_coemulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_mpr_dmm_recording_coemulator.py --self-test --json

# 2. 全板 25 阶段（Stage 1..25）统一校验（支持 --skip-phase145）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 145 46 项单测 & 全量 fx3-vm 单测（双模式）
/usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_mpr_dmm_recording_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_mpr_dmm_recording_coemulator.py -v
/usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 150：Stage 26（`26/26`）真机机身物理按键、5 轴 IBIS `0x0400->0x1400` 中心锁死、`XLR-H1` 热插拔、散热风扇与 `NP-FZ100`/USB-PD HIL 协同仿真器

[`realhw_body_peripheral_ibis_fan_power_coemulator.py`](realhw_body_peripheral_ibis_fan_power_coemulator.py) 作为 **Stage 26（26/26 阶段完成）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase150_realhw_body_peripheral_hil=True`，可通过 `--skip-phase150` 跳过；全板 26 阶段协同仿真在本地只读供体模式下 `< 2.2s`、洁净室模式下 `< 0.9s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`emmc_nflasha_write_count == 0`**、**`p18_mutation_bytes == 0`**、**`floating_coil_ms == 0`**、**`sdi_blocking_wait_ms == 0.0`**、**`false_19v5_dcin_alarms == 0`** 与 **`rsv_orphan_count == 0`** 的前提下完成五大闭环：

1. **双模只读供体审计（`os.O_RDONLY` + `mmap.ACCESS_READ`）+ 洁净室回退**：
   - 检查 FX3 `7.02` 与 FX6 `6.01` 的 `appFw.so`（`79,015,712 B` vs `50,520,424 B`）、`libsencore.so`（`377,328 B` vs `401,952 B`，均 `355` 导出 / `130` 导入）、`libInfraLensCommunicator.so`（`14,544 B`，均 `27` 导出 / `25` 导入）、`libInfraAvbbc.so`（`1,734,632 B` vs `1,743,200 B`）、`cpapp-b.bin`（FX3 含 **`529`** 处 `LiroSeq` 5 轴 IBIS 伺服位点 vs FX6 `148` 处）、FX6 `p18:/lens/lensfile.bin`（`262,592 B` `VX8900..`）与 `Backup.bin`（`BK4\x00`，`819` vs `840` 子系统）共 **13 份真机供体**；`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线，JSON 零原始固件字节泄漏。
2. **Pillar A — 5 轴 IBIS `LiroSeq` 伺服、`0x0400 -> 0x1400` 中心锁死与 E-Mount `p18:/lens` 只读护栏**：
   - 仿真 `Boot -> Active IBIS -> Standard IBIS -> Off -> Power-Down` 全生命周期，拦截 FX6 `PRM_is_imager_stabilization_unit_fixed` 刚性卡口误判并在 `Off`/关机时强制执行 `0x0400 -> 0x1400` 音圈物理中心锁死停放（`floating_coil_ms == 0`）；同时覆盖 E-Mount 12-pin 变焦/光圈（T-Stop/F-Stop）与呼吸效应补偿（`EVENT_FUNC_LENS_COMP_LENS_COMP_BREATHING_ON`），强制阻断任何对 `p18:/lens/lensfile.bin` 或 `nflasha` 的写入（`p18_mutation_bytes == 0`）。
3. **Pillar B — `XLR-H1` MI 热靴 4ch LPCM 实时热插拔、`VMC-BNCM1` LTC 与 `HDMI Type-A RAW` vs 屏蔽 `12G-SDI`/`BNC`**：
   - 仿真 `XLR-H1` 在待机与录制态下热拔出时将 `P11 0x91db059b` `E_TMO=-50 -> 0x8000` 并于 `0.0 ms` 回退至机内立体声/3.5mm TRS，零 UI 卡顿与断流；覆盖 Multi-USB `VMC-BNCM1` LTC 外锁（且在 `H0 uart_boot` 模式硬阻断）；激活 `HDMI Type-A 4K60 16-bit RAW` 并全程静默屏蔽 FX6 `12G-SDI`/`BNC`（`sdi_blocking_wait_ms == 0.0`）。
4. **Pillar C — FX3 机身物理按键映射与 `3x Tally` 灯可达性 HIL**：
   - 覆盖 FX3 实体 `Custom 1..6`、`T/W Zoom Rocker`、`MODE -> Big-6 Home`、`DISP -> Status Check` 与直连摇杆/拨轮，证明对 FX6 `Big-6 Home`、`128-Page Full Menu`、`Status Check`、`Direct Joystick` 与 `Servo Zoom` 的 **`100.0%` 逻辑可达性**，联动前/顶/后 **3 路 Tally LED**，同时严格保留 `MENU + SHUTTER + POWER` 物理逃生组合键不被接管覆盖。
5. **Pillar D — 主动散热风扇（`Off-in-Rec` 高温强制接管）与 `NP-FZ100` (`7.2V`) / `USB-PD` (`9V/3A`) 供电与优雅 `EncWfiStop`**：
   - 证明在 `Auto1`/`Auto2`/`Minimum`/`Off in Rec` 四档模式下，一旦温度传感器越过高温阈值即在 CMOS 热跳闸前强制接管 PWM 风扇拉升（`90% PWM`），并验证 `NP-FZ100`（`7.2V`）与 `USB-PD`（`9V/3A`）放电及欠压关断 cleanly 完成 `M4ROOT/CLIP` 封口（`EncWfiStop`），零 `19.5V DC-IN` 误报警且 `emmc_nflasha_write_count == 0`。

### Phase 150 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 26 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_body_peripheral_ibis_fan_power_coemulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_body_peripheral_ibis_fan_power_coemulator.py --self-test --json

# 2. 全板 26 阶段（Stage 1..26）统一校验（本地 < 2.2s，洁净室 < 0.9s，支持 --skip-phase150）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 150 46 项单测 & 全量 fx3-vm 单测（双模式）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_body_peripheral_ibis_fan_power_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_body_peripheral_ibis_fan_power_coemulator.py -v
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 157：Stage 27（`27/27`）真机 `IMX510` 双原生 ISO `800/12800`、`psd.bin/defdet.bin` 传感器 NVS、`.cube` 3D MLUT、`CDC-NCM` `Monitor & Control` 与 `054C:0DA1` 恢复口 HIL 协同仿真器

[`realhw_imx510_color_and_network_usb_coemulator.py`](realhw_imx510_color_and_network_usb_coemulator.py) 作为 **Stage 27（27/27 阶段完成）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase157_realhw_imx510_network_usb_hil=True`，可通过 `--skip-phase157` 跳过；全板 27 阶段协同仿真在本地只读供体模式下 `< 2.4s`、洁净室模式下 `< 1.0s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`emmc_nflasha_write_count == 0`**、**`sensor_cal_mutation_bytes == 0`**、**`rf_nvs_p12_p13_mutation_bytes == 0`**、**`slog3_master_double_baked == False`**、**`bt_hci_blocking_wait_ms == 0`**、**`bt_hci_blocking_wait_eliminated == True`** 与 **`usb_msc_0da1_recovery_intact == True`** 的前提下完成五大闭环：

1. **双模只读供体审计（`os.O_RDONLY` + `mmap.ACCESS_READ`）+ 洁净室回退**：
   - 检查 FX3 `7.02` 与 FX6 `6.01` 的 **16 份真机供体**（8 FX3 + 8 FX6）：`libInfraMscServer.so`（`64,456 B`，`125` 导出 / `69` 导入，零差异 ABI）、`libUsbControl.so`（`135,424 B`，`351` 导出 / `128` 导入，零差异 ABI）、`libWlanAdjust.so`（`73,168 B`，`188` 导出 / `119` 导入，零差异 ABI）、`libWlanResource.so`（`56,464 B`，`94` 导出 / `90` 导入，零差异 ABI）、`libsencore.so`（`377,328 B` vs `401,952 B`，`355` 导出 / `130` 导入）、`libmpr.so`（`3,517,008 B` / `3,541` 导出 vs `28,921,824 B` / `4,271` 导出，均含 `SetLutData` / `ExecEncStart` / `EncWfiStop`）、`cpapp-b.bin`（均含 `IMX510` 与 `defdet.bin`）及 `Backup.bin`（`BK4\x00`，`819` vs `840` 子系统）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线，JSON 零原始固件字节泄漏。
2. **Pillar A — `IMX510` 双原生基地 Cine EI（`ISO 800` LCG `[200..3200 EI]` <-> `ISO 12800` HCG `[3200..51200 EI]`）与 `p2:/setting/psd.bin` / `defdet.bin` 只读护栏**：
   - 验证 `ISO 12800` 处精准模拟 HCG 增益切换、未烘焙 `S-Log3` XAVC 母版 + EI XML 元数据保留 `15+` 档动态范围（`15.3` stops），并强制拦截对 `p2:/setting/psd.bin` 与 `defdet.bin` 的直接或跨机身覆盖写入（`sensor_cal_mutation_bytes == 0`）。
3. **Pillar B — `16-Slot` SD `.cube` 用户 3D MLUT（`17^3 / 33^3`）监看与 `S-Log3` 防双重烘焙护栏**：
   - 从 `/mnt/sd/PRIVATE/SONY/PRO/LUT/` 装载并校验全部 `16` 个槽位的 `17^3 / 33^3` `.cube` 表至 `/tmp/fx3_mlut_slots/` 易失 RAM，仅在 LCD 与 HDMI Type-A Clean 监看路径应用 MLUT；在 `LUT Burn-in = Off` 时保证 `slog3_master_double_baked == False`，并对 `NaN`/`Inf`/截断/越界槽位/非法的 `65^3` `.cube` 表执行 fail-closed 拒收。
4. **Pillar C — `802.11ac` Wi-Fi + `CDC-NCM` 千兆 USB-LAN（`PTP-IP TCP/15740` `Monitor & Control` + FTPES）+ `P12` 飞行模式硬切断与 `p12/p13` NVS 锁**：
   - 证明消除 `/dev/ttyAMA3` BLE 守护进程阻塞等待（`bt_hci_blocking_wait_ms == 0`）、非阻塞掩码 FX6 `WIREDLAN_WOL_*`、`P12` 飞行模式硬切断 `wlan0` 同时保持有线 `CDC-NCM`（`RTL8153`/`AX88179` `1000 Mbps`）`PTP-IP TCP/15740` 与 `FTPES` 正常通畅，并锁定 `p12/p13` RF NVS（`rf_nvs_p12_p13_mutation_bytes == 0`）。
5. **Pillar D — USB Type-C 多角色切换与不可破坏 `MSC (054C:0DA1)` / `SERVICE (054C:0336)` 恢复口保护**：
   - 验证在 `MSC (054C:0DA1)` <-> `MTP/PTP Remote` <-> `CDC-NCM` USB-LAN <-> `HDMI-UVC` 之间切换或插拔后，`054C:0DA1` 与 `054C:0336` 恢复口始终完好可达（`usb_msc_0da1_recovery_intact == True`、`persistent_emmc_writes_authorized == False`、`emmc_nflasha_write_count == 0`）。

### Phase 157 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 27 自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_imx510_color_and_network_usb_coemulator.py --self-test --summary
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_imx510_color_and_network_usb_coemulator.py --self-test --json

# 2. 全板 27 阶段（Stage 1..27）统一校验（本地 < 2.4s，洁净室 < 1.0s，支持 --skip-phase157）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 157 46 项单测 & 全量 fx3-vm 单测（双模式）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_imx510_color_and_network_usb_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_imx510_color_and_network_usb_coemulator.py -v
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 162：Stage 28（`28/28`）真机双槽 `CFexpress Type A / SDXC V90` 热切换、`.RSV` 掉电抢救、官方 `BODYDATA.DAT`（`\x89UFU`）`<100 µs` 自动旁路与五级不可变砖恢复 HIL 协同仿真器

[`realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py`](realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py) 作为 **Stage 28（28/28 阶段完成）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase162_realhw_cfexpress_ufu_5tier_hil=True`，可通过 `--skip-phase162` 跳过；全板 28 阶段协同仿真在本地只读供体模式下 `< 2.5s`、洁净室模式下 `< 1.1s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`spi_nor_write_authorized == False`**、**`el3_payload_transmit_authorized == False`**、**`emmc_nflasha_write_count == 0`**、**`cp_mutation_bytes == 0`**、**`user_media_clips_intact == True`** 与 **`rsv_orphan_count == 0`** 的前提下完成五大闭环：

1. **双模只读供体审计（`os.O_RDONLY` + `mmap.ACCESS_READ`）+ 有限字节 `BODYDATA.DAT`（`<= 4 KiB`）检查 + 洁净室回退**：
   - 检查 FX3 `7.02` 与 FX6 `6.01` 的 **12 份核心真机供体**（`libmpr.so` `3,517,008 B` / `3,541` 导出 vs `28,921,824 B` / `4,271` 导出、`libsencore.so` `377,328 B` vs `401,952 B` 同为 `355` 导出/`130` 导入、`im.elf` `40,920 B` 零差异 ABI `11` 导出/`85` 导入、`loader_nor.bin` `101,888 B` vs `92,448 B`、`cpapp-b.bin` `15,980,568 B` vs `17,952,816 B`、`Backup.bin` `BK4\x00` `819` vs `840` 子系统）以及可选本地 `BODYDATA.DAT`（`811,876,768 B` FX3 `7.02` & `847,081,840 B` FX6 `6.01`）的 **`<= 4096 B` 严格有界读取**（验证 `\x89UFU\r\n\x1a\n`、`DATV=1`、`PROV=1`、`UDID` `054c:0da1` vs `054c:0d21` 与 `FDAT` 偏移）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 时确定性切换 `CLEAN_ROOM_SYNTHETIC` 基线，JSON 零原始固件字节泄漏。
2. **Pillar A — 双槽混合 `CFexpress Type A (NVMe)` + `SDXC UHS-II (V90/V60/V30)` 码率门控、接力切换与卡门 Hall/GPIO 安全冲刷**：
   - 验证 `XAVC S-I 4K 120p 600 Mbps` 在 `CFexpress Type A` 与 `SDXC V90`（`720 Mbps`）准入而拒绝 `V30`（`SPEED_CLASS_REJECTED_SDXC_UHS_I_V30`，`appfw_crashes == 0`），仿真 `Slot A -> Slot B` 零丢帧接力切换，并在卡门写入中打开时由 Hall/GPIO 中断触发 `MPR` FIFO 归零冲刷（`mpr_fifo_residual_bytes == 0`、`exfat_volume_dirty == 0`），跨双启动切换保持 `PRIVATE/M4ROOT` 与 `XDROOT` 用户素材 `100%` 完整。
3. **Pillar B — 突发拔电池 `.RSV` 短片抢救（`Recover Image DB` / `.RSV -> .MP4/.MXF`）**：
   - 仿真录制中途断电遗留 `C0001.RSV` 与挂起索引，重启后通过 ExFAT `.RSV` 安全重组还原 `C0001.MP4` / `C0001.MXF` 与 `MEDIAPRO.XML`（`rsv_orphan_count == 0`、`emmc_nflasha_write_count == 0`），并对损坏 `.RSV` 执行 fail-closed 拦截。
4. **Pillar C — 官方索尼 `BODYDATA.DAT`（`\x89UFU\r\n\x1a\n`）共存、`<100 µs` Stage-A 自动旁路与跨机型（`FX30/A7S3/FX6`）拦截**：
   - 证明插卡存在 `/BODYDATA.DAT` 时 Stage-A 在 **`38.5 µs < 100 µs`** 自动旁路 Stage-B 进入 `100%` 原厂 FX3 `7.02` 用户态；在 `p15:/usr` `.orig` 干净卸载未完成（`H0 != H3`）前硬阻断启动 `p1` 升级器；对非 `0x91030080`（`ILME-FX30` `0x91030090` / `ILCE-7SM3` `0x91030070` / `ILME-FX6` `0x91030060`）执行 fail-closed 拦截。
5. **Pillar D — 五级不可变砖硬件恢复升级演练（`Tier-1 SD 47 µs` -> `Tier-2 p15 .orig` -> `Tier-3 同型 UFU` -> `Tier-4 Multi-USB 1.8V UART EL3 只读` -> `Tier-5 CID 匹配 ISP`）**：
   - 逐级注入故障并验证确定性恢复闭环，同时硬锁 **`el3_payload_transmit_authorized == False`**、**`spi_nor_write_authorized == False`**、**`persistent_emmc_writes_authorized == False`**、**`emmc_nflasha_write_count == 0`** 与 `passive_tx_bytes_emitted == 0`。

### Phase 162 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 28 自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py --self-test --json

# 2. 全板 28 阶段（Stage 1..28）统一校验（本地 < 2.5s，洁净室 < 1.1s，支持 --skip-phase162）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 162 46 项单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py -v
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 167：Stage 29（`29/29`）真机 `CXD90057`（`Mira`）+ `CXD90058`（`Cetus`）双 BIONZ-XR SoC 间 IPC、`sabin` SA-DSP、`XAVC-I / HEVC` 编解码与 `H0 == H3` 出厂封签 HIL 协同仿真器

[`realhw_cxd90058_sabin_codec_and_seal_coemulator.py`](realhw_cxd90058_sabin_codec_and_seal_coemulator.py) 作为 **Stage 29（29/29 阶段完成）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase167_realhw_cxd90058_sabin_seal_hil=True`，可通过 `--skip-phase167` 跳过；全板 29 阶段协同仿真在本地只读供体模式下 `< 2.6s`、洁净室模式下 `< 1.2s`），在严格保持 **`p8_cp_mutation_forbidden == True`**、**`cxd90058_mutation_bytes == 0`**、**`cp_mutation_bytes == 0`**、**`otp_write_count == 0`**、**`rpmb_write_count == 0`**、**`emmc_nflasha_write_count == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成五大闭环：

1. **双模只读供体审计（`os.O_RDONLY` + `mmap.ACCESS_READ`）+ 洁净室合成回退**：
   - 检查 FX3 `7.02` 与 FX6 `6.01` 的 **10 份核心真机供体**：`cpapp-b.bin`（`15,980,568 B` vs `17,952,816 B`，ARM32 入口字 `0x00108000` 加载基址与 `TOPPERS`/`DmmWrapper`/`memcfg`/`/usr/sabin/aed_dic1.bin`/`bed_dic1.bin`；FX6 独有 `Mew`/`MoniFpga_StartStopSDI`/`Darwin` 在 FX3 中不存在）、`libmpr.so`（`3,517,008 B` / `3,541` 导出 vs `28,921,824 B` / `4,271` 导出）、`libsencore.so`（`377,328 B` vs `401,952 B`，同为 `355` 导出/`130` 导入）、`im.elf`（`40,920 B` 零差异 ABI `11` 导出/`85` 导入）与 `Backup.bin`（`BK4\x00`，`819` vs `840` 子系统及 `\sabin\idt_cam.bin`/`tomco` 标记）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线，JSON 零原始固件字节泄漏。
2. **Pillar A — `CXD90057`（*Mira*）<-> `CXD90058`（*Cetus*）双 SoC 互联与 `1,724.00 MiB` `memcfg=` 共享池协同仿真**：
   - 校验 4 段非重叠 non-cacheable `memcfg=` 池（`1,807,745,024 B` = `1,724.00 MiB`）并在持续 `4K 120p 10-bit 4:2:2`（`240` 帧 / `480` UIPC 往返包）负载下证明 `ipc_deadlocks == 0`、`mailbox_stalls == 0`、`cxd90058_mutation_bytes == 0`、`cp_mutation_bytes == 0`，同时对门铃停滞故障与针对 `/dev/nflasha8/cpapp-b.bin` 等 Stock CP 目标的写请求执行 fail-closed 拦截。
3. **Pillar B — `sabin` 32 位 SA-DSP 微码与 `XAVC-I (MXF)` / `XAVC S-I` / `XAVC HS (HEVC)` 硬件编码桥接**：
   - 验证 `sabin` 32 位 SA-DSP 窗口（`0x809139000..0x809178FFF`，`0x40000 B`）严格位于 `memcfg=` 池内且与 `cpImg` 零重叠；模拟 FX6 `appFw.so` 录制预设驱动 FX3 原厂 `libmpr.so` 硬件编码器（`XAVC-I MXF 4K 59.94p/23.976p`、`XAVC S-I MP4 4K 119.88p`、`XAVC HS HEVC 4K 59.94p/119.88p`），并对 FX6 独占 `16-bit SDI RAW`（`mew.bin` FPGA）执行 fail-closed 拦截且 `appfw_crashes == 0`。
4. **Pillar C — 双介质 Tier-0 冷备份 RAID-6 `GF(256)`（`0x11D`）Bit-Rot 内存自愈演练**：
   - 在纯 Python `GF(2^8)` P+Q RAID-6 校验下模拟次级备份介质 2 块分片（如 `boot_b` + `cnflasha_spacc` 及边缘对 `nbl_a` + `c2pa_rq_lic`）同时损坏，证明未修复前阻断 Stage-A 暂存、修复后 RAM 内 `11/11` 分片 `100%` 比特精确重建，并对 `>= 3` 分片丢失执行 fail-closed 拒绝。
5. **Pillar D — 端到端 `H0 -> H1 -> H2 -> H3` `16/16` 出厂封签与零残留质保审计**：
   - 校验全部 `16` 个存储面（`sector0, p1, p2, p3, p5, p6, p7, p8, p12, p15, p18, p23, p30, spi_nor, otp, rpmb`）满足 `SHA256(H0) == SHA256(H3)`，零 `.orig`、零 `/tmp/jiritsu`、零 `p6` 分片残留、`OTP == 0`、`RPMB == 0` 且 `persistent_emmc_writes_authorized == False`，并对任何残留/熔丝/写请求执行 fail-closed 拦截。

### Phase 167 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 29 自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_cxd90058_sabin_codec_and_seal_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_cxd90058_sabin_codec_and_seal_coemulator.py --self-test --json

# 2. 全板 29 阶段（Stage 1..29）统一校验（本地 < 2.6s，洁净室 < 1.2s，支持 --skip-phase167）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 167 46 项单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_cxd90058_sabin_codec_and_seal_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_cxd90058_sabin_codec_and_seal_coemulator.py -v
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 172：Stage 30（`30/30` 里程碑）真机 `p12:/cert/RQ_LIC.DAT` C2PA 锁、`VMC-BNCM1`（`EXT-LK`）SMPTE 时间码、`IMX510` 6 轴陀螺仪 `NonRealTimeMeta.xml` 与 10 步 Pre-Bench Go/No-Go HIL 协同仿真器

[`realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py`](realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py) 作为 **Stage 30（`30/30` 里程碑阶段完成）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase172_realhw_c2pa_tc_gyro_prebench_hil=True`，可通过 `--skip-phase172` 跳过；全板 30 阶段协同仿真在本地只读供体模式下 `< 2.7s`、洁净室模式下 `< 1.3s`），在严格保持 **`p8_cp_mutation_forbidden == True`**、**`c2pa_cert_mutation_bytes == 0`**、**`p2_mutation_bytes == 0`**、**`p18_mutation_bytes == 0`**、**`cp_mutation_bytes == 0`**、**`otp_write_count == 0`**、**`rpmb_write_count == 0`**、**`emmc_nflasha_write_count == 0`** 与 **`persistent_emmc_writes_authorized == False`** 的前提下完成五大闭环：

1. **双模只读供体审计（`os.open(..., os.O_RDONLY)` + 缓冲 `os.read`）+ 洁净室合成回退**：
   - 检查 FX3 `7.02` 与 FX6 `6.01` 的 **10 份核心真机供体**：`cpapp-b.bin`（`15,980,568 B` vs `17,952,816 B`，ARM32 入口字 `0x00108000` 加载基址及 `IMX510`/`C_ImagerCtrl_IMX510`/`LTC`/`Gyro Data`/`OTP`；`ILME-FX3` 与 `MTG_ULOCK_START_SLAVE` 仅存在于 FX3，FX6 中为 `0` 命中）、`libmpr.so`（`3,517,008 B` / `3,541` 导出 vs `28,921,824 B` / `4,271` 导出，均含 `NonRealTimeMeta`/`LtcChangeTable`/`Gyroscope`/`SetMovieRecParam`，而 FX3 v7.02 独有的 C2PA 标记 `InfraC2PA`/`c2pa.created`/`sony.created`/`jumdSSIG`/`sigcert.p12` 在 FX6 v6.01 中不存在）、`libsencore.so`（`377,328 B` vs `401,952 B`，同为 `355` 导出/`130` 导入及 `C_GYRO_GAIN`/`MONITOR_GET_TEST_OUT_BNC_STATUS`/`GENLOCK`）、`im.elf`（`40,920 B` 零差异 ABI `11` 导出/`85` 导入及 `/dev/nflasha12`/`/cert`/`/dev/nflasha15`）与 `Backup.bin`（`BK4\x00`，`819` vs `840` 子系统及 `90057`/`psd.bin`/`defdet.bin`/`lensfile.bin`/`tomco`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺失时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线，JSON 零原始固件字节泄漏。
2. **Pillar A — `p12:/cert/RQ_LIC.DAT` 单机 C2PA 许可证 `MS_RDONLY` 不可变性与防伪防火墙**：
   - 协同仿真 Stage-B 启动、电影录制与干净卸载全流程，验证 `p12:/cert` 强制 `MS_RDONLY` 挂载、`c2pa_cert_mutation_bytes == 0`、`H0 == H1 == H2 == H3` SHA-256 不变性，并对跨机身克隆与跨型号（`ILME-FX6` / `ILME-FX30` / `ILCE-7SM3`）C2PA 签名或密钥导出请求执行 fail-closed 拦截。
3. **Pillar B — `VMC-BNCM1`（`AD_JACK_IN` Pin 10 -> `EXT-LK`）SMPTE-12M LTC-IN（`0.5V–4.5V p-p`）、User-Bits 与 Multi-USB UART 争用互锁**：
   - 协同仿真外置 LTC 跨 `23.98 / 24 / 25 / 29.97 / 59.94` fps 锁相（SMPTE-12M `0x3FFD` 同步字与 User-Bits 无损透传），对 `> 5.0V p-p` 过压或错误 ID 电阻执行 fail-closed 拒绝，对 FX6 专属 BNC `TC-OUT` 驱动进行干净屏蔽（`tc_direction == "IN"`），并对 Multi-USB `1.8V UART` 引脚争用冲突触发零损伤硬互锁（`uart_contention_damage_events == 0`、`over_voltage_damage_events == 0`）。
4. **Pillar C — `IMX510`（`8.7 ms` 读出）+ 6 轴 IMU 陀螺仪 + `p18:/lens` `NonRealTimeMeta.xml` Catalyst/Resolve 增稳管线**：
   - 模拟录制内嵌 6 轴 `2000 Hz` 陀螺仪采样与 `p18:/lens` 焦距元数据的 `XAVC S-I`（MP4）与 `XAVC-I`（MXF）片段，生成并 XML 往返解析 Sony `NonRealTimeMeta.xml`（`ver.2.20`），在不触碰 `p2` 与 `p18`（`p2_mutation_bytes == 0`、`p18_mutation_bytes == 0`）的前提下证明 100% Catalyst Browse 与 DaVinci Resolve Schema 合规，并对陀螺仪 CRC 故障、时间戳回退或读出延迟漂移执行 fail-closed 阻断。
5. **Pillar D — 完整 10 步 Pre-Bench 操作员 Go/No-Go 干跑生命周期**：
   - 协同仿真 10 步实操预演闭环：被动 USB 挂载检查 -> `054C:0DA1 -> 054C:0336` `op=0xFF` 金丝雀探针 -> 双介质 16 存储面 Tier-0 备份（`H0`）-> `p12`/`p18` `MS_RDONLY` 锁定 -> `/dev/cnflasha15` `.orig` 暂存（`H1`）-> 双启动 + `EXT-LK` 锁相 -> Big-6 实拍 + `NonRealTimeMeta.xml`（`H2`）-> `.RSV` 恢复与 C2PA 防火墙核查 -> 干净卸载 `.orig` -> `16/16 H0 == H3` 出厂零残留封签（`persistent_emmc_writes_authorized == False`、`emmc_nflasha_write_count == 0`）。

### Phase 172 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 30 自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py --self-test --json

# 2. 全板 30 阶段（Stage 1..30 里程碑）统一校验（本地 < 2.7s，洁净室 < 1.3s，支持 --skip-phase172）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 172 46 项单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_c2pa_tc_gyro_and_prebench_gonogo_coemulator.py -v
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 178：Stage 31（`31/31`）真实硬件主线 — Sony SCEL `ssboot` / `WBI2` Bootloader 旁路防火墙、100 轮断电/跌压恢复与 Slot-1 `BODYDATA.DAT`（`>=2.04`）/ C2PA 100-License 协同仿真

[`realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py`](realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py) 作为 **Stage 31（`31/31`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase178_realhw_ssboot_wbi2_powerloss_slot1_ufu_hil=True`，可通过 `--skip-phase178` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`spi_nor_write_authorized == False`**、**`el3_payload_transmit_authorized == False`**、**`physical_usb_packets_emitted == 0`**、**`otp_fuse_touches == 0`**、**`rpmb_counter_increments == 0`**、**`wbi_persistent_writes == 0`**、**`emmc_nflasha_write_count == 0`** 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **9 份真实供体**：`nflasha5.img`（`209,112,512 B`、`WBI2\x00\x00\x00\x00`、`1,399` 节）vs FX6 `wbi2-receipt.json`（`202,677,056 B`、`WBI2`、`1,197` 节）、FX3/FX6 `liro.ko`（`121,488 B` ELF64 AArch64，包含 `liro`/`4.9.337`/`suspend`/`vermagic`，哈希体机专用）、FX3 `vmlinux.bin`（`6,610,952 B`，包含 `4.9.337-scel+`/`WBI2`/`ssboot`/`hibernate`/`wbi`/`udm`）、`<= 4096 B` 有界头部读取 FX3 `7.02` `BODYDATA.DAT`（`811,876,768 B`、`\x89UFU\r\n\x1a\n`、`DATV=1`、`PROV=1`、`054c:0da1`）vs FX6 `BODYDATA.DAT`（`847,081,840 B`、`054c:0d21`），以及零差异 ABI 的 `im.elf`（`40,920 B`、`11` 导出 / `85` 导入）；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换至确定性洁净室合成基线。
2. **Pillar A — Sony SCEL `ssboot` / `WBI2` Bootloader 旁路防火墙 HIL**：
   - 协同仿真 `WBI2\x00\x00\x00\x00`（`57 42 49 32`）引导恢复路径与 Stage-A 冷启动入口（`/sbin/init` -> `fx6-stage-a-verify`），证明：未捕获的 `WBI2` 陷阱会在双启动激活前被阻断；Stage-B 对 `/dev/nflasha5` 与 `/dev/pnflasha5` 锁定 `BLKROSET=1` 并屏蔽 `PM_SUSPEND_DISK`（`disk`）与 `/proc/udm` 快照写入（`wbi_persistent_writes == 0`）；`EH1` 拔卡逃生（`38.5 us < 50 us`）与干净卸载（`H2 -> H3`）完整保留 Stock FX3 的 `0.5s` `WBI2` 热启动与 `nflasha5` SHA-256（`H0 == H3`）。
3. **Pillar B — 100 轮 `NP-FZ100` 骤拔电池 & `6.3V` 跌压（`EncWfiStop`）HIL**：
   - 连续运行 100 轮 Stock <-> Stage-B 状态切换（覆盖菜单中拔电池、录制中 `6.3V` 跌压 `EncWfiStop` exFAT `.RSV -> .MXF` 抢救、`EH2` `DISP+MENU+SHUTTER` 安全冷启动、以及 `EH3` 1 字节 `libJit.so` CRC32 fail-closed 回退），证明 `p1`、`p2:/setting`、`p5:/wbi`、`p12:/cert`、`p15:/usr`、`p18:/lens` 6 个核心分区保持 `0` 日志/元数据漂移。
4. **Pillar C — 官方 ILME-FX3 `Ver. 7.02` `BODYDATA.DAT`（`811,876,768 B`）`>=2.04` 门槛 & Slot-1 C2PA 100-License HIL**：
   - 拦截 `<= Ver. 2.02` 机身版本（避免 `7L+7S` LED 报错闪烁），强制 Slot-1 根目录唯一放置（禁止 `BODYDATA (1).DAT` 副本或 Slot-2），验证有效 `\x89UFU` `<100 us` Stage-A 旁路至 Stock FX3，校验 Slot-1 单包 `<= 100` 份 C2PA 许可与 `p12:/cert/RQ_LIC.DAT` `EROFS` 只读锁定，并强制 `WPA2/WPA3` 无线安全下限（拒绝 `WEP`/`WPA1`/`IPsec`）。
5. **Pillar D — 硬安全红线不变式**：
   - 所有禁止的物理写入与发射探针（eMMC 持久写、SPI-NOR 写、EL3 载荷发送、物理 USB 发包、OTP 熔丝触碰、RPMB 计数递增）均 fail-closed 拦截。

### Phase 178 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 31 自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py --self-test --json

# 2. 全板 31 阶段（Stage 1..31）统一校验（支持 --skip-phase178）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 178 48 项单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_ssboot_wbi2_powerloss_and_slot1_ufu_coemulator.py -v
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 182：Stage 32（`32/32`）真实硬件主线 — `MIRA_CETUS2` E-Mount `info7/info8/info3D` + `0x02cf0232` 呼吸补偿 & Type-A HDMI `4264x2408` 16-bit RAW（`BRAW` / `ProRes RAW`）HIL 协同仿真器

[`realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py`](realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py) 作为 **Stage 32（`32/32`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase182_realhw_emount_info3d_breathing_hdmi_4264_raw_hil=True`，可通过 `--skip-phase182` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`spi_nor_write_authorized == False`**、**`el3_payload_transmit_authorized == False`**、**`physical_usb_packets_emitted == 0`**、**`otp_fuse_touches == 0`**、**`rpmb_counter_increments == 0`**、**`lens_partition_writes == 0`**、**`sdi_bnc_mmio_faults == 0`** 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 `< 0.10s` + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：零差异 ABI `libInfraLensCommunicator.so`（`14,544 B`：`LensCommunicator` / `GetMountedLensInfo` / `SndSyncMsg`）、`libInfraAdjMedia.so`（`318,152 B` vs `334,536 B`：`AVBB_SCN_START_HDMI` / `AVBB_SCN_STOP_HDMI`）、`string_english*.uxc`（`uxc\x07` 容器，含 `4264x2408`、`Breathing Comp`、`Focus Map`、`ProRes`、`RAW Output Format`），并对 `cpapp-b.bin`（`Draw Widget <FocusMap>`、`fixed_lensfile`、`ExtractFromCombinedLensData`、`MoniFpga`）与 `appFw.so`（`uc_BreathingCorrectionLensType`、`HDMI_RAW_CONNECTSTATE_NOT_SET`、`info7`/`info8` 与小端 `0x02cf0232` BKID）执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Pillar A — `MIRA_CETUS2` E-Mount `info7 / info8 / info3D` 串口握手与 `0x02cf0232` 呼吸补偿 HIL**：
   - 严格校验 CPAPP 16 位白名单谓词 `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)`：放行原厂 E-Mount 镜头（如 `FE PZ 16-35mm F4 G` / `FE 24-70mm F2.8 GM II`）激活 `0x02cf0232` 呼吸补偿、Catalyst 呼吸元数据注入与 Monitor & Control `2.1.0+` Focus Map 深度流；门控拦截副厂镜头（如 `0x4210` 与 `0xCFFF` 保留位陷阱）及手动 PL/E 转接环（`0xFFFF`）；并在 Type-A HDMI RAW 激活时强制 `1.0x` 旁路，同时锁定 `p18:/lens/LENSFILE.BIN` `BLKROSET=1`（`lens_partition_writes == 0`）。
3. **Pillar B — Type-A HDMI `4264 × 2408`（`<= 60p`）16-bit Linear RAW（`Video Assist 12G HDR 3.22+` `.braw` & `Atomos Ninja` `ProRes RAW`）vs 屏蔽 `12G-SDI` HIL**：
   - 协同仿真 CTA-861 EDID 与 Sony VSIF（`0x81`，模 256 校验和）握手：`Video Assist 12G HDR 3.22+` 接纳 `4264x2408` 16->12-bit `.braw`（Capture-Locked ISO），拒绝 `Video Assist 3G`（`BLOCKED_VIDEO_ASSIST_3G_UNSUPPORTED_FOR_BRAW`）；`Atomos Ninja V/Ultra`（`AtomOS 10.64+`）封装 WB + ISO 偏移输出 `ProRes RAW`；校验机内双卡槽同步录制 `XAVC S-I / HS + Proxy`、`1.5x/1.6x` 变形反挤压仅渲染于 OSD 严禁烘焙入 RAW，以及 `12G-SDI` BNC MMIO 零故障屏蔽（`sdi_bnc_mmio_faults == 0`）。
4. **Pillar C & D — `WPA2/WPA3` 网络安全净化器与硬安全红线不变式**：
   - 强制无线连接 `WPA2/WPA3`（或有线 `WIRED_USB_CDC_NCM`），拦截 `WEP`/`WPA1`/`OPEN`/`TKIP`/`IPsec` 及路径穿越/控制字符注入；所有禁止物理写入与发射探针（eMMC 持久写、SPI-NOR 写、EL3 载荷发射、物理 USB 发包、OTP 熔丝、RPMB 递增、`p18` 写入、`12G-SDI` MMIO）均 fail-closed 拦截。

### Phase 182 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 32 自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py --self-test --json

# 2. 全板 32 阶段（Stage 1..32）统一校验（支持 --skip-phase182）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 182 48 项单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 188：Stage 33（`33/33`）真实硬件主线 — `ILME-FX3` vs `ILME-FX3A`（`2.36M` XGA / 无 NFC-IR）分支防火墙 & `XLR-H1` MI 热靴 `48kHz/24bit 4ch` 覆盖 HIL 协同仿真器

[`realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py`](realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py) 作为 **Stage 33（`33/33`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase188_realhw_fx3a_firewall_and_xlrh1_4ch_mishoe_hil=True`，可通过 `--skip-phase188` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`spi_nor_write_authorized == False`**、**`el3_payload_transmit_authorized == False`**、**`physical_usb_packets_emitted == 0`**、**`otp_fuse_touches == 0`**、**`rpmb_counter_increments == 0`**、**`fx6_ribbon_mmio_faults == 0`** 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 `< 0.10s` + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libInfraNfc.so`（`52,280 B` / `56,376 B`：`InfraNfc` / `InfraNfcSenser` / `InfraNfcSpiThread`）、`libInfraHotshoe.so`（`47,808 B`：`InfraHotshoe` / `SetAdcLevel`）、`libInfraSircs.so`（`27,072 B`：`InfraSircs` / `AsyncUipcRcvThread`）、`string_english_f.uxc`（`373,820 B`：`Shoe Audio Set.`、`48kHz`、`24bit`、`4ch`、`CH1+3/CH2+4`、`IR Remote Ctrl`、`One-touch(NFC)`）与 `string_english.uxc`（`118,208 B`），并对 `cpapp-b.bin`（`ILME-FX3`、`XLR`、`SIRCS`）、`appFw.so`（`AUDIO_MONITORING_CH_MIX_ALL`、`No41_NFC`、`CAMSET`、`VAL_hotshoe_xlr_mic_`、`SIRCS_2SEC_EVENT_STATE_OFF`）及 `BODYDATA.DAT`（`\x89UFU\r\n\x1a\n`、`DATV`、`PROV`、`UDID`）执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Pillar A — `ILME-FX3`（`Ver. 7.02`，`1.44M` LCD + NFC + IR）vs `ILME-FX3A`（`Ver. 2.02`，`2.36M` XGA LCD / 无 NFC-IR）Stage-A Fail-Closed 分支防火墙 HIL**：
   - 协同仿真 Stage-A 硬件探针（`model_id` `0x91030080` vs `0x9103008A` / `0x91030030`、LCD 点时钟 `1,440,000` vs `2,359,296`、NFC/IR 设备树存在性、`7.02` vs `2.02` 固件分支）：仅原版 `ILME-FX3` 准入 Stage-B；若插入 `ILME-FX3A` 或 `ILME-FX30`，`< 50 us` Fail-Closed 旁路回退原厂 Stock（不加载显示垫片、`0` 写入），并拦截跨型号 `BODYDATA.DAT` 与 `CAMSET` 导入。
3. **Pillar B — `XLR-H1` 多接口（MI）数字热靴 `48kHz/24bit 4ch` vs 机身 `3.5mm` 物理抢占 HIL**：
   - 协同仿真 `XLR-H1`（`HANDLE AUDIO = ON`，`IN1/IN2` XLR -> `CH1/CH2`，`IN3` 3.5mm 立体声 -> `CH3/CH4`，支持 `48kHz/24bit 4ch` / `24bit 2ch` / `16bit 2ch`，耳机 `4ch Audio Monitoring` 矩阵 `CH1/2`、`CH3/4`、`CH1+3/CH2+4`）；证明机身 `3.5mm` 插入立即抢占 MI 热靴并锁定灰显 `[MI Shoe Audio Set.]`、`S&Q` 升格零爆音静音、官方大版本 `BODYDATA.DAT` 升级重置 `[MI Shoe Audio Set.]` 为 `48kHz/16bit 2ch` 陷阱防护，以及 `CH1..CH4` Big-6 电平表映射且零 FX6 专用排线故障（`fx6_ribbon_mmio_faults == 0`）。
4. **Pillar C & D — 气隙 `FX3BNDL1` 打包卫生 & 硬安全红线不变式**：
   - 强制校验 `FX3BNDL1` 气隙 SD 卡包仅面向 `ILME-FX3` `7.02`（严禁跨机型残留、路径穿越或原生固件泄露）；所有禁止物理写入与发射探针（eMMC 持久写、SPI-NOR 写、EL3 载荷发射、物理 USB 发包、OTP 熔丝、RPMB 递增、FX6 排线 MMIO）均 fail-closed 拦截。

### Phase 188 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 33 自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py --self-test --json

# 2. 全板 33 阶段（Stage 1..33）统一校验（支持 --skip-phase188）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 188 48 项单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_fx3a_branch_firewall_and_xlrh1_4ch_mishoe_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 194：Stage 34（`34/34`）真实硬件主线 — `ILME-FX3` No-UVC USB Gadget 防火墙、`USB-PD` (`NP-FZ100`) vs `DC-C1` (`>=65W / 5A`) 功耗预算、双卡 `.cube` LUT 路径非对称、`Cine EI` 与 `RMT-P1BT` BT/IR HIL 协同仿真器

[`realhw_nouvc_dcc1_lut_path_cineei_coemulator.py`](realhw_nouvc_dcc1_lut_path_cineei_coemulator.py) 作为 **Stage 34（`34/34`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil=True`，可通过 `--skip-phase194` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`spi_nor_write_authorized == False`**、**`el3_payload_transmit_authorized == False`**、**`physical_usb_packets_emitted == 0`**、**`otp_fuse_touches == 0`**、**`rpmb_counter_increments == 0`**、**`usb_phy_hang_events == 0`**、**`power_cut_brownout_events == 0`**、**`sensor_analog_gain_contamination_events == 0`** 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 `< 0.10s` + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libUsbControl.so`（`135,424 B`）、`cdc_ncm.ko`（`32,208 B`）、`rndis_host.ko`（`14,064 B`）、`libInfraBluetoothCore.so`（`267,592 B`）、`string_english_f.uxc`（`373,820 B`：`USB Connection Mode` / `Sel. When Connect` / `Mass Storage` / `MTP` / `Remote Shoot` / `USB-LAN` / `USB Power Supply` / `Network Streaming` / `Cine EI` / `Bluetooth Rmt Ctrl` / `IR Remote Ctrl`），并对 `appFw.so`、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Pillar A — `ILME-FX3`（`0x91030080`）No-UVC USB Gadget 防火墙 & `USB-LAN`（`RNDIS/CDC-NCM`）/ 网络推流（`<= 38 Mbps`）HIL**：
   - 协同仿真 `[USB Connection Mode]`（`Sel. When Connect`、`MassStorage(MSC)`、`MTP`、`Remote Shooting`）与 `USB-LAN` 开机自动连接，拒绝不支持的 `[USB Streaming]` UVC/UAC 复合 Gadget 描述符（返回 `EOPNOTSUPP` `95`，零 USB PHY 挂死），并将 `4K 59.94p` 实时输出路由至 Network Streaming（`RTMP/RTMPS/SRT <= 38 Mbps`）或 Type-A HDMI（以及无音频 `1024x576` 旧版 `Remote Shooting` Webcam）。
3. **Pillar B — `USB Power Supply`（`NP-FZ100` 强制在位）vs `DC-C1`（`>=65W + 5A` e-Marked 线缆）电气 HIL**：
   - 协同仿真机身 Type-C PD 供电开启时拔出 `NP-FZ100` 的瞬时断电风险（与开机暂停内充 / 关机续充）、Micro-USB 供电硬拒绝，以及 `DC-C1` 假电池耦合器的电源/线缆门控（`<65W` 或 `3A`/非 e-Marker 触发红灯闪烁欠压拦截；达标则释放机身 Type-C 用于高速数据并锁定 LCD 最大亮度）。
4. **Pillar C & D — 双卡 `.cube` User LUT 路径非对称、`Cine EI`、`RMT-P1BT` BT/IR 互斥与硬安全红线**：
   - 强制校验 `SD: /Private/Sony/PRO/LUT/` vs `CFexpress-A: /Sony/PRO/LUT/` 路径非对称（交叉错配立即拦截）、`17pt/33pt` 网格（拒绝 `65pt`）、`<=63 B` ASCII 文件名、`16` 个 `p2:/setting` User LUT 槽位与 `0..+2EV` `1/3` 档 AE 偏移；验证 `Cine EI`（`800/12800` 双原生基地与 `3200..51200 EI`）零 CMOS 模拟增益污染、`RMT-P1BT`（BT 4.2）开启时禁用 IR (`SIRCS`) 与手机 GPS 联动（以及 `FX3A` 无 IR/NFC 硬件）、`Creators' Cloud` `OK/NG/KEEP` 片段筛选（`H0 == H3`）与 9 项物理写入红线 fail-closed 拦截。

### Phase 194 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 34 自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_nouvc_dcc1_lut_path_cineei_coemulator.py --self-test --json

# 2. 全板 34 阶段（Stage 1..34）统一校验（支持 --skip-phase194）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 194 48 项单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_nouvc_dcc1_lut_path_cineei_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_nouvc_dcc1_lut_path_cineei_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 200：Stage 35（`35/35` 里程碑）真实硬件主线 — `ILME-FX3` 4 态 `[Fan Control]`（`Off in Rec` 待机 `100% MAX PWM` / `Always Off` 冷备前置门控）、独立 `[Shutter Mode]`（`Speed/Angle` `5.6°..64F` vs `360°` 钳位）与 `6.01` vs `7.02` `p2:/setting` User LUT 二进制格式分叉防火墙 HIL 协同仿真器

[`realhw_fan_pwm_shutter_angle_lut_split_coemulator.py`](realhw_fan_pwm_shutter_angle_lut_split_coemulator.py) 作为 **Stage 35（`35/35` 里程碑）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase200_realhw_fan_pwm_shutter_angle_lut_split_hil=True`，可通过 `--skip-phase200` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`spi_nor_write_authorized == False`**、**`el3_payload_transmit_authorized == False`**、**`physical_usb_packets_emitted == 0`**、**`otp_fuse_touches == 0`**、**`rpmb_counter_increments == 0`**、**`p2_setting_mutation_bytes == 0`**、**`thermal_runaway_events == 0`**、**`lut_color_solver_corruption_events == 0`** 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 `< 0.10s` + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libfan.so`（FX3 `27,280 B` / FX6 `31,176 B`）、`libbackup.so`（`14,232 B`）、`libBackupManager.so`（`10,272 B`）、`im.elf`（`40,920 B`：`/dev/nflasha2` -> `/setting`）、`string_english_f.uxc`（`373,820 B`：证实 `Fan Control` / `Off in Rec` / `Always Off` / `Minimum` / `Auto Power OFF Temp.` / `Shutter Mode` / `Angle` / `Speed` / `Exposure step` `0.3EV` & `0.5EV` / `User1..User16` 存在且 **`Auto1`/`Auto2` 命中数为 `0`**），并对 `appFw.so`、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Pillar A — `ILME-FX3`（`0x91030080`）精确 4 态 `[Fan Control]`（拒绝 `Auto1/Auto2`）& 热控/冷备前置门控 HIL**：
   - 协同仿真 `MENU -> Setup -> [Setup Option] -> [Fan Control]` 精确 4 态 PWM 控制器（`Auto`、`Minimum`、`Off in Rec`、`Always Off`），对不存在的 `Auto1` / `Auto2` 请求立即返回 `EINVAL` (`22`)；在 `Off in Rec` 下待机/非录制驱动 **`100% MAX PWM`** 主动排热、正常录制降至 **`0% PWM`** 静音，并在结温触及安全上限（`[Auto Power OFF Temp.] = Standard: 68°C` / `High: 78°C`）时触发 **`100% PWM`** 紧急热保护覆盖；当处于 `Always Off`（或非 `Auto`）时硬拦截 `AdjustControl (0x40)` 75 MiB `p3` 冷备/双启入口，直至切回 `[Fan Control] = Auto`。
3. **Pillar B — 独立 `[Shutter Mode]`（`Speed` vs `Angle`）AP-CP 备份槽位与帧率钳位 HIL**：
   - 协同仿真 `Backup.bin` 独立的 `[Speed]`（`0x01240010`）与 `[Angle]`（`0x01240014`）槽位存储（跨 `BIG6` / `Movie` / `S&Q` 切换互不覆盖，且快门角对 `0.3EV / 0.5EV` `[Exposure step]` 完全免疫），在 `<= 59.94p` 允许 `5.6°..64F`（`23,040°`）多帧累加，在 `119.88p / 100p` 高帧率与 `S&Q` 下严格钳位至 `5.6°..360°`。
4. **Pillar C & D — `FX6 Ver. 6.01` vs `Stock FX3 Ver. 7.00/7.02` `p2:/setting` `User1..User16` LUT 二进制格式分叉防火墙与硬安全红线**：
   - 拦截 Stage-B `FX6 Ver. 6.01`（`<=6.01` 旧版槽位格式 `SONY_USER_LUT_SLOT_V1_LE601`）向原厂 `FX3 7.02`（`>=7.00` 优化格式 `SONY_USER_LUT_SLOT_V2_GE700`）`p2:/setting` 的直接写入（返回 `EROFS` `30`），将 `User1..User16` 全部 16 个槽位严格重定向至易失性内存目录 `/tmp/fx6_lut_overlay`，阻断未重注册的 `6.01` 槽位在 `7.02` 下直接加载，确保 `16/16 H0 == H3`（`p2_setting_mutation_bytes == 0`），并 fail-closed 锁死全部 9 项硬件安全红线。

### Phase 200 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 35（35/35 里程碑）自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_fan_pwm_shutter_angle_lut_split_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_fan_pwm_shutter_angle_lut_split_coemulator.py --self-test --json

# 2. 全板 35 阶段（Stage 1..35, 35/35 里程碑）统一校验（支持 --skip-phase200）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 200 48 项双模单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_fan_pwm_shutter_angle_lut_split_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_fan_pwm_shutter_angle_lut_split_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 202：Stage 36（`36/36` 里程碑）真实硬件主线 — `ILME-FX3` `BIG6` `[Home (Lower Left)]` 零物理 e-ND 执行器防火墙、Slot-1 `CAMSET` 双介质根路径分流与 `VMC-BNCM1` 机身专属 `TC IN` / HDMI `TC OUT` HIL 协同仿真器

[`realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py`](realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py) 作为 **Stage 36（`36/36` 里程碑）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase202_realhw_big6_noend_camset_slot1_vmcbncm1_hil=True`，可通过 `--skip-phase202` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`spi_nor_write_authorized == False`**、**`el3_payload_transmit_authorized == False`**、**`physical_usb_packets_emitted == 0`**、**`otp_fuse_touches == 0`**、**`rpmb_counter_increments == 0`**、**`e_nd_actuator_tx_count == 0`**、**`slot1_fx3_camset_mutation_bytes == 0`**、**`p2_setting_mutation_bytes == 0`**、**`xlrh1_handle_usb_tc_miswire_damage_events == 0`**、**`bnc_tcout_reverse_drive_events == 0`** 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 `< 0.10s` + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libUsbControl.so`（`135,424 B`）、`libInfraHotshoe.so`（`47,808 B`）、`libbackup.so`（`14,232 B`）、`libBackupManager.so`（`10,272 B`）、`im.elf`（`40,920 B`：`/dev/nflasha2` -> `/setting`）、`string_english_f.uxc`（`373,820 B`：证实 `Home (Lower Left)` / `Aperture` / `ND Filter` / `Fixed/Variable` / `Mode Settings` / `Save/Load Settings` / `Slot 1` / `Recall Camera Setting` / `Time Code Make` / `Time Code Run` / `Time Code Output` / `HDMI Output Settings` / `Preset` / `Free Run`），并对 `appFw.so`（含 `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT` 与 `CAMSET%02d`）、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Pillar A — `ILME-FX3`（`0x91030080`）`BIG6`（`[Mode Settings] = [Fixed/Variable]`）6 格主屏拓扑 & 零物理 e-ND 执行器防火墙 HIL**：
   - 协同仿真 `BIG6` 6 格参数磁贴（`FPS`、`ISO/Base ISO`、`Shutter Speed/Angle`、`Aperture/ND Filter`、`Picture Profile/Select LUT`、`White Balance`）及第 7 顶部状态栏区，支持 `MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)]` 在默认 E-Mount 电子光圈 `[Aperture]` 与纯虚拟参考显示 `[ND Filter]` 之间无损切换，并以 `EOPNOTSUPP`（`95`）硬拦截一切来自 `FX6` 的 `1/4..1/128` 电动无级可变 e-ND CP 总线驱动帧（`e_nd_actuator_tx_count == 0`）。
3. **Pillar B — 仅限 `Slot 1` 的 `CAMSET01.DAT .. CAMSET10.DAT` 双介质根路径分流与跨机型 `.DAT` 防火墙 HIL**：
   - 协同仿真 `MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]`，严格执行 **仅限 `Slot 1`**（`Slot 2` 立即返回 `EINVAL` `22`）、单卡最多 `10` 组（`CAMSET01.DAT .. CAMSET10.DAT`）、`MR`（`Recall Camera Setting`）模式灰显禁用（`EOPNOTSUPP` `95`）、**`SD/SDHC/SDXC`（`/PRIVATE/SONY/SETTING/FX3/CAMSET/`）vs `CFexpress Type A`（`/SONY/SETTING/FX3/CAMSET/`）根路径非对称校验**、拒绝 `ILME-FX3A` / `ILME-FX6` 跨机型 `.DAT` 混读，并将 Stage-B `FX6` 人格隔离至易失性内存沙箱 `/tmp/fx6_camset_overlay`（直接写返回 `EROFS` `30`，保持 `10/10 H0 == H3`）。
4. **Pillar C & D — `VMC-BNCM1`（`A-5051-506-A`）机身专属单向 `TC IN`（`EXT-LK` `>= 10s`）、`XLR-H1` 手柄 Micro-USB 阻断、HDMI 数字 `TC OUT` 与硬安全红线**：
   - 协同仿真 `VMC-BNCM1`（`0.2 m` BNC 母头 -> Multi/Micro-USB）仅在机身左侧 `Multi/Micro-USB` + `Movie` + `[TC Make] = [Preset]` + `[TC Run] = [Free Run]` 连续同步 `>= 10s` 后点亮 `EXT-LK`（切入 `S&Q` 或修改 `TC` 设置立即释放锁相）；对误插 `XLR-H1` 手柄侧面 Micro-USB 返回 `ENODEV`（`19`），对反向 BNC 模拟 LTC `TC OUT` 返回 `EOPNOTSUPP`（`95`），将数字 `TC OUT` 路由至标准 Type-A HDMI（`Movie` 开启、`S&Q` 自动关闭），并 fail-closed 锁死全部 9 项物理写入/发射红线。

### Phase 202 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 36（36/36 里程碑）自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py --self-test --json

# 2. 全板 36 阶段（Stage 1..36, 36/36 里程碑）统一校验（支持 --skip-phase202）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 202 48 项双模单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_big6_noend_camset_slot1_vmcbncm1_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 207：Stage 37（`37/37` 里程碑）真实硬件主线 — `ILME-FX3` `[De-Squeeze Display]`（`1.6x=1.65x` 4 项锁定 & HDMI RAW 旁路）、外置 `M&C Focus Map`（`>=150fps` 截止）与 `[Simult. + Auto Switch]` / `[Shockless WB]` HIL 协同仿真器

[`realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py`](realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py) 作为 **Stage 37（`37/37` 里程碑）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase207_realhw_desqueeze_165x_focusmap_simult_shocklesswb_hil=True`，可通过 `--skip-phase207` 跳过；全板 37 阶段协同仿真在本地只读供体模式下 `< 2.1s`、洁净室模式下 `< 1.0s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`desqueeze_baked_into_raw_or_xavc_frames == 0`、`inbody_fx3_focus_map_overlay_frames == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 `< 0.10s` + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libInfraLensCommunicator.so`（`14,544 B` 零差异 ABI）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraPtpControl.so`（`165,320 B`）、`string_english_f.uxc`（`373,820 B`：证实 `De-Squeeze Display` / `1.3x` / `2.0x` / `1.5x` / `1.6x` / `Manual Focus` / `Focus Mode` / `Focus Area` / `SteadyShot` / `Face Priority in Multi Metering` / `RAW Output` / `Off(HDMI Only)` / `HDMI Info. Display` / `Log Shooting` / `Focus Map` / `Simult. Recording` / `Auto Switch Media` / `Shockless WB` / `C.Temp./Filter`）与 `string_english.uxc`（`118,208 B`），并对 `appFw.so`（含 `1.65` CinemaScope 缩放常数）、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Pillar A — `[De-Squeeze Display]`（`Off / 1.3x / 2.0x / 1.5x / 1.6x=1.65x`）4 项锁定与 5 态 HDMI RAW / 纯净 HDMI 旁路 HIL**：
   - 协同仿真 `MENU -> Setup -> [Display Option] -> [De-Squeeze Display]`（`[1.6x]` 按索尼官方规范施加精确 **`1.65x`** 水平拉伸至 `2.39:1` CinemaScope），开启非 `Off` 档位时强制锁定 4 项相机参数（`[Focus Mode]=Manual Focus`、`[Focus Area]=Wide`、`[SteadyShot]=Off`、`[Face Priority in Multi Metering]=Off`，越权修改返回 `EOPNOTSUPP` `95`），并在 `[RAW Output]=On`、`[Off(HDMI Only)]`（联动 `[HDMI Info. Display]=Off`）、`[Log Shooting]=Off`、`[Remote Shooting]` 与静态照片模式下自动抑制反挤压显示（`desqueeze_baked_into_raw_or_xavc_frames == 0`）。
3. **Pillar B — 仅限外置 `Monitor & Control` 的 `[Focus Map]`（FX3 机内零菜单）与 `>=150fps` 截止 HIL**：
   - 以 `EOPNOTSUPP`（`95`）硬拒绝机内 FX3 `[Focus Map]` 菜单开关与 Stage-B 本地 EVF/LCD 叠加层注入；在原厂 E-Mount PDAF 镜头（`((id >> 14) == 3) && ((id & 0x0FFF) != 0x0FFF)`）与实时拍摄状态下，`< 150fps`（含 FX3 允许的 **`1..6fps` S&Q 低帧率**，区别于 FX6 `<=6fps` 封锁，以及 `24p..120fps`）向外置 `M&C` 推流 PDAF 深度图，并对 **`>= 150fps`**（`150 / 200 / 240fps`）、转接环/非 PDAF 手动镜、UVC 推流与机内回放执行硬拦截。
4. **Pillar C & D — 双卡 `[Simult. Recording]` + `[Auto Switch Media]`（`Ver. 2.0+` 单卡续录 vs `Off` 严格双备份停机）、`[Shockless WB]` 与硬安全红线**：
   - 协同仿真 `[Simult. Recording]` 下 `[Auto Switch Media]=On` 单卡录满后无缝单卡续录及换入空卡恢复双卡同录（对比 `Off` 严格双卡备份一致性停机，全程 `0` 丢帧、`0` 孤立 `.RSV`）；仿真 `[Shockless WB]`（`Off / 1 / 2 / 3`）全帧率（`1..240fps`）预设切换平滑渐变，以及手动旋转 `[C.Temp./Filter]` 色温开尔文值与 `A–B / G–M` 微调网格时的 **`0` 帧即时旁路**；并 fail-closed 锁死全部 8 项物理写入/发射/叠加红线。

### Phase 207 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 37（37/37 里程碑）自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py --self-test --json

# 2. 全板 37 阶段（Stage 1..37, 37/37 里程碑）统一校验（支持 --skip-phase207）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 207 48 项双模单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_desqueeze_165x_focusmap_simult_shocklesswb_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 213：Stage 38（`38/38` 里程碑）真实硬件主线 — `ILME-FX3` HDMI Log `1080p` 强制降档 vs `[Off(HDMI Only)]` `4K 10-bit` 黑屏联动、`Px` 代理双编码耦合保险库与 `[Focus Magnifier]` × `[Bright Monitoring]` 互斥 HIL 协同仿真器

[`realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py`](realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py) 作为 **Stage 38（`38/38` 里程碑）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase213_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_hil=True`，可通过 `--skip-phase213` 跳过；洁净室 38 阶段全板仿真 `< 0.6s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`single_sided_proxy_or_main_orphan_mutations == 0`、`on_camera_proxy_playback_frames == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libInfraLensCommunicator.so`（`14,544 B` 零差异 ABI）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`：`AVBB_SCN_START_HDMI` / `AVBB_SCN_STOP_HDMI`）、`string_english_f.uxc`（`373,820 B`：证实 `HDMI Output Settings` / `Rec. Media dur HDMI Output` / `Off(HDMI Only)` / `4K Output Set.(HDMI Only)` / `HDMI Info. Display` / `Emphasized REC Display` / `Proxy Settings` / `XAVC HS HD` / `XAVC S HD` / `16M 4:2:0 10bit` / `9M 4:2:0 10bit` / `6M 4:2:0 8bit` / `Initial Focus Mag.` / `Auto Magnifier in MF` / `Marker Display` / `Bright Monitoring` / `Setting Effect OFF`）与 `string_english.uxc`（`118,208 B`），并对 `appFw.so`（含 `LOG_SHOOTING` / `PPLUT` / `M4ROOT` / `CLIP` / `SUB` / `FOCUS_MAG` / `BrightMonitoring`）、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-model A — HDMI Log `1080p` 强制降档 vs `[Off(HDMI Only)]` `4K 10-bit` & `[HDMI Info. Display]` 机内 LCD 黑屏联动 HIL**：
   - 协同仿真 `MENU -> Setup -> [External Output] -> [HDMI Output Settings]`：当 `[Rec. Media dur HDMI Output]=On`、`[RAW Output]=Off` 且开启 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）或选用 `PPLUT1..PPLUT4` 时，即便请求 `2160p`/`Auto`，HDMI 输出强制降档为 **`1920x1080`（`1080p`）** 且机内双卡正常录制（`internal_card_recording_active == True`）；当切换 `[Off(HDMI Only)]` + `[4K Output Set.(HDMI Only)]`（`59.94p / 50p / 29.97p / 25p / 23.98p / 24.00p 10bit` 共 6 档）时输出原生 **`3840x2160` `4K 10-bit`**，同时以 `EOPNOTSUPP`（`95`）硬封锁机内存储卡录制（`internal_card_recording_active == False`）、自动强制 `[HDMI Info. Display]=Off` 并抑制 HDMI 反挤压；在 `[Rec. Media dur HDMI Output]=On` 下开启 `[HDMI Info. Display]=On` 时自动熄灭机身内置 LCD 面板（`camera_lcd_blanked == True`）并同步输出 `[Emphasized REC Display]` 红框 Tally。
3. **Sub-model B — `[Proxy Settings]` 双编码矩阵、高帧率截止、零机内代理回放与 `M4ROOT/CLIP/`+`SUB/` 原子耦合保险库 HIL**：
   - 协同仿真 `XAVC HS HD`（`1920x1080` 10-bit HEVC `4:2:0`：`16M` 与默认 `9M`，最高 `59.94p/50p`）与全局默认 `XAVC S HD`（`1280x720` 8-bit AVC `4:2:0`：`6M`，最高 `59.94p/50p`），在常规 `119.88p/100p`、S&Q 录制帧率 `119.88p/100p`、S&Q 传感器采样帧率 `>= 100fps/120fps` 及 `[Off(HDMI Only)]` 下以 `EOPNOTSUPP`（`95`）阻断代理生成；严格执行 **零机内代理独立回放**（`on_camera_proxy_playback_frames == 0`，仅在主片缩略图叠加 `(Px)` 徽标），并保证机内 Delete / Protect 对 `/PRIVATE/M4ROOT/CLIP/<Clip>.MP4` 与 `/PRIVATE/M4ROOT/SUB/<Clip>S03.MP4` **100% 原子同步执行**（单边机内修改拒绝返回 `EOPNOTSUPP`，外部读卡器孤儿文件返回 `EINVAL` 完整性告警）。
4. **Sub-model C & Redlines — `[Focus Magnifier]` 动态/静态倍率分野 × `[Bright Monitoring]` 自定义键互锁与硬安全红线 HIL**：
   - 协同仿真 `[Initial Focus Mag.]` 在视频（`Movie`/`S&Q`：`x1.0` / `x4.0`）与照片（全画幅 `x1.0` / `x2.1`、APS-C/S35 `x1.0` / `x1.5`）下的倍率边界，拦截视频模式下被禁用的 `[Auto Magnifier in MF]` 对焦环自动放大（`EOPNOTSUPP` `95`），并在放大激活期间自动隐藏 `[Marker Display]`；在 `[Focus Magnifier]` 或 `[Auto Magnifier in MF]` 放大激活期间锁定 `[Bright Monitoring]` 自定义按键（`EOPNOTSUPP` `95`），验证 `[Bright Monitoring]` 仅在 `P/A/S/M` + `MF` 下激活并强制 `[Live View Display] -> [Setting Effect OFF]`（切出 `P/A/S/M`、切入 `AF` 或关机立即自动取消），同时 fail-closed 锁死全部 8 项物理写入/发射/单边代理孤儿红线。

### Phase 213 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 38（38/38 里程碑）自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py --self-test --json

# 2. 全板 38 阶段（Stage 1..38, 38/38 里程碑）统一校验（支持 --skip-phase213）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 213 48 项双模单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_hdmi_log1080_proxy_vault_focusmag_brightmon_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 217：Stage 39（`39/39` 里程碑）真实硬件主线 — `ILME-FX3` `[File Settings]` 37 字符 / `SDHC` 强制 `[Standard]` 锁定 + `Shot Mark1/2`、`[TC Regenerate]` 独占 Slot 1 & `EXT-LK` 解锁与 `[REC Lamp]` 后置+顶部 REC 键硬件耦合 Tally HIL 协同仿真器

[`realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py`](realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py) 作为 **Stage 39（`39/39` 里程碑）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase217_realhw_filesettings_shotmark_tcregen_reclamp_hil=True`，可通过 `--skip-phase217` 跳过；本地只读供体 39 阶段全板协同仿真 `< 2.0s`、洁净室模式 `< 0.65s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`sdhc_non_standard_filename_or_custom_folder_bypasses == 0`、`slot2_simult_tc_regenerate_contamination_events == 0`、`decoupled_top_rec_button_vs_rear_tally_mismatches == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libInfraLensCommunicator.so`（`14,544 B` 零差异 ABI）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`：`AVBB_SCN_START_HDMI` / `AVBB_SCN_STOP_HDMI`）、`string_english_f.uxc`（`373,820 B`：证实 `File Settings` / `File Name Format` / `File Number` / `Series` / `Reset` / `Series Counter Reset` / `Title Name Settings` / `Cam ID + Reel#` / `Standard` / `Title` / `Date + Title` / `Title + Date` / `Shot Mark` / `Add Shot Mark1` / `Add Shot Mark2` / `Add/Delete Shot Mark1` / `Add/Delete Shot Mark2` / `Image Jump Setting` / `Only Shot Mark Mov.` / `Time Code Make` / `Regenerate` / `Time Code Output` / `REC Lamp` / `Only Front Off` / `Silent Mode`）与 `string_english.uxc`（`118,208 B`），并对 `appFw.so`（含 `SILENT_MODE` / `SHOT_MARK` / `REC_LAMP` / `CLIP` / `M4ROOT` / `REGENERATE`）、`cpapp-b.bin` 与 `libmpr.so`（含 `NonRealTimeMeta` / `LtcChangeTable` / `ShotMark`）执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-model A — `[File Settings]` 5 种命名格式、37 字符 ASCII `[Title Name]`、`SDHC` 强制 `[Standard]` 锁定与 `Shot Mark1/2` `*M01.XML` 旁路车 HIL**：
   - 协同仿真 `MENU -> Shooting -> [File] -> [File Settings]` 的全部 5 种 `[File Name Format]`（`Standard`、`Cam ID + Reel#`、`Title`、`Date + Title`、`Title + Date`）与双卡 `[File Number]`（`Series` 跨卡递增 vs `Reset` 新卡归 `0001` + `Series Counter Reset`），严格执行 **`<= 37` 个允许 ASCII 字符**（`A-Za-z0-9` + `.-_@!#$%+=^~(),;[]`，共 80 字符；空串、`>= 38` 字符或非法字符返回 `EINVAL` `22`），对 `SDHC`（`<= 32GB` FAT32）强制锁定 `[Standard]`（尝试强行解锁非标准命名或自定义 `/PRIVATE/M4ROOT/CLIP` 之外的视频目录均返回 `EOPNOTSUPP` `95`），且修改标题绝不追溯重命名既有素材；同时仿真录制中 `Add Shot Mark1/2` 与回放中 `Add/Delete Shot Mark1/2` 写入 `*M01.XML`（`NonRealTimeMeta`）旁路车、`[Image Jump Setting]` 四模式检索及 FTP `[Only Shot Mark Mov.]` / `[Only Shot Mark]` 过滤传输。
3. **Sub-model B — `[TC/UB]` `[Time Code Make: Regenerate]` 独占 Slot 1 主卡读取、强制 `Rec Run`、`VMC-BNCM1` `EXT-LK` 解锁与 `S&Q` HDMI 时间码阻断 HIL**：
   - 协同仿真 `[Regenerate]` 在单卡模式下读取当前活动卡槽最末时间码，而在 **`[Simult. Recording]` 双卡同录下严格只读取 `Slot 1`**（忽略不一致的 `Slot 2` 时间码，尝试强制从 `Slot 2` 再生返回 `EOPNOTSUPP` `95`），且无论 `[Time Code Run]` 原设为 `Free Run` 还是 `Rec Run` 一律强制按 **`[Rec Run]`** 递增；验证 `VMC-BNCM1` 外部 `EXT-LK`（要求 `Movie` + `Preset` + `Free Run` 同步 `>= 10s`）一旦切换 `[Time Code Make]`、`[Time Code Run]`、进入 `S&Q`/`Photo` 或拔除线缆即刻释放外部锁定回退内部基准，并在 `S&Q` 模式下同时封锁 `[Time Code Run]` 与 HDMI `[Time Code Output]`（强制开启返回 `EOPNOTSUPP` `95`）。
4. **Sub-model C & Redlines — `[REC Lamp]` 3 态后置+顶部 `REC` 键硬件耦合 Tally 与 `[Silent Mode]` -> `[Audio signals]` 硬锁定 HIL**：
   - 协同仿真 `MENU -> Setup -> [Setup Option] -> [REC Lamp]` 三态硬件耦合规则：`[All On]` 点亮前置灯 + 后置灯 + 顶部 `REC` 按键红灯；**`[Only Front Off]` 仅熄灭前置 Tally 灯而同时保持后置灯与顶部 `REC` 按键 LED 常亮**（拒绝 `Only Rear Off` 等电影机独占项 `EINVAL` `22`，拒绝拆解顶部 `REC` 键与后置灯硬件耦合 `EOPNOTSUPP` `95`）；`[All Off]` 熄灭全部物理 LED，但保持 `[Emphasized REC Display]` 红框 Tally 独立运行（当 `[HDMI Info. Display]=On` 时同步输出至 HDMI）；同时验证 `[Silent Mode]=On` 将 `[Audio signals]` 硬锁定灰显为 `Off`（消隐对焦合焦与自拍蜂鸣，强行开启返回 `EOPNOTSUPP` `95`），并 fail-closed 锁死全部 9 项物理写入/发射/绕过红线。

### Phase 217 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 39（39/39 里程碑）自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py --self-test --json

# 2. 全板 39 阶段（Stage 1..39, 39/39 里程碑）统一校验（支持 --skip-phase217）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 217 48 项双模单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_filesettings_shotmark_tcregen_reclamp_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 222：Stage 40（`40/40` 里程碑）真实硬件主线 — `ILME-FX3` `[Pixel Mapping]` 自动重启清零 `/tmp` & `cnflasha` 只读防火墙、`[NTSC/PAL Selector]` 跨 `[Camera Settings Reset]` 持久化与 `[Gamma Display Assist]` 4 档 vs `[Display LUT]` 锁定分离 HIL 协同仿真器

[`realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py`](realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py) 作为 **Stage 40（`40/40` 里程碑）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase222_realhw_pixelmap_ntscpal_gammaassist_displaylut_hil=True`，可通过 `--skip-phase222` 跳过；本地只读供体 40 阶段全板协同仿真 `< 2.2s`、洁净室模式 `< 0.6s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`stage_b_tmp_mount_residuals_after_pixelmap_reboot == 0`、`ntsc_pal_cross_region_db_contamination_events == 0`、`log_shooting_gamma_assist_or_hdmi_leakage_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`os.O_RDONLY` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + 洁净室合成回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libInfraLensCommunicator.so`（`14,544 B` 零差异 ABI）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`：`AVBB_SCN_START_HDMI` / `AVBB_SCN_STOP_HDMI`）、`string_english_f.uxc`（`373,820 B`：证实 `Auto Pixel Mapping` / `Pixel Mapping` / `Silent Mode` / `NTSC/PAL Selector` / `Camera Settings Reset` / `Initialize` / `TC Format` / `DF` / `NDF` / `23.98p` / `25p` / `Gamma Display Assist` / `Gamma Disp. Assist Typ.` / `S-Log3→709(800%)` / `HLG(BT.2020)` / `HLG(709)` / `HLG Still Image` / `Log Shooting` / `Cine EI` / `Cine EI Quick` / `Flexible ISO` / `Display LUT` / `Display LUT Switch`）与 `string_english.uxc`（`118,208 B`：含 FX6 `APR` / `Black Balance`），并对 `appFw.so`（含 `AUTO_PIXEL_MAPPING` / `PIXEL_MAPPING` / `SILENT_MODE` / `NTSC_PAL` / `INITIALIZE` / `AVCHD` / `M4ROOT` / `LOG_SHOOTING` / `GAMMA_DISP`）、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-model A — `[Auto Pixel Mapping]` / 手动 `[Pixel Mapping]` 强制自动重启清零 `/tmp` & `cnflasha` 只读防火墙 HIL**：
   - 协同仿真 `MENU -> Setup -> [Setup Option] -> [Auto Pixel Mapping]`（默认 `On`，电源关闭暗场采样期间即便 `[Silent Mode]=On` 仍允许机械快门暗场闭合发声；关闭为 `Off` 且距上次校准 `>= 3` 天时发出手动校准周期告警）与手动 `[Pixel Mapping]`：电池电量 `< 20%` 时以 `EOPNOTSUPP`（`95`）拒绝执行，校准期间以 `EBUSY`（`16`）全锁定操作员按键输入，校准完成后**强制触发整机自动重启（Automatic Camera Restart）**，100% 清零易失性 `/tmp` Stage-B 绑定挂载并干净引导回原厂 `ILME-FX3 Ver. 7.02 (Stock)`（`H0 == H2`，`stage_b_tmp_mount_residuals_after_pixelmap_reboot == 0`），同时以 `EROFS`（`30`）硬拦截任何用户态直写 `cnflasha` 出厂校准分区行为（`cnflasha_userspace_write_blocked == True`）。
3. **Sub-model B — `[NTSC/PAL Selector]` 独占帧率 / `DF-NDF` 矩阵、开机提示横幅与 `[Camera Settings Reset]` 持久化 HIL**：
   - 协同仿真 `MENU -> Setup -> [Area/Date] -> [NTSC/PAL Selector]`：`NTSC` 开放 `23.98p`（NTSC 独占）、`29.97p`、`59.94p`、`119.88p`（及可选 DCI `24.00p`）与 `[TC Format]` `DF`/`NDF`（`23.98p`/`24.00p` 自动锁定 `NDF`），而 `PAL` 仅开放 `25p`、`50p`、`100p` 并以 `EOPNOTSUPP`（`95`）阻断 `23.98p` 与 `DF`/`NDF`；当有效制式偏离机身区域出厂默认值时显示 `"Running on NTSC."` 或 `"Running on PAL."` 开机横幅；验证 **`[Camera Settings Reset]` 完整保留当前 `[NTSC/PAL Selector]` 制式**，唯有全量 **`[Initialize]`** 才恢复区域出厂默认制式，并对跨制式双卡槽媒体数据库未重初始化混录执行 `EOPNOTSUPP`（`95`）隔离保护。
4. **Sub-model C & Redlines — `[Gamma Display Assist]` 4 档精确表 vs `[Log Shooting]` `[Display LUT]` 硬锁定分离与仅限机内 LCD 作用域 HIL**：
   - 协同仿真 `MENU -> Setup -> [Display Option] -> [Gamma Disp. Assist Typ.]` 官方 Ver. `7.02` 精确 **4 档表**（`Auto`、`S-Log3->709(800%)`、`HLG(BT.2020)`、`HLG(709)`；尝试请求 `S-Log2` 立即以 `EINVAL = 22` 拒绝并标记 `slog2_assist_rejected == True`）；一旦激活 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`），**硬锁定灰显 `[Gamma Display Assist] = Off`**（强制覆盖尝试返回 `EOPNOTSUPP = 95`）并将机内监看预览移交 `[Display LUT]` `On`/`Off`（及 `[Display LUT Switch]` 快捷键翻转）；严格锁死 `[Gamma Display Assist]` 仅作用于机身内置 LCD 面板（`external_hdmi_gamma_assist_applied == False`，尝试注入外接 HDMI 返回 `EOPNOTSUPP = 95`），并 fail-closed 锁死全部 9 项物理写入/发射/绕过红线。

### Phase 222 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 40（40/40 里程碑）自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py --self-test --json

# 2. 全板 40 阶段（Stage 1..40, 40/40 里程碑）统一校验（支持 --skip-phase222）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 222 48 项双模单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_pixelmap_ntscpal_gammaassist_displaylut_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 226：Stage 41（`41/41` 里程碑）真实硬件主线 — Wave-31 `[SteadyShot]` `[Active]` 三重截止、`[Clear Image Zoom]` 4 项自动对焦/测光锁死与 `1.0x` 恢复、以及 `[Power Save Start Time]` 9 条件旁路 + `[Auto Power OFF Temp.]` HIL 协同仿真器

[`realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py`](realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py) 作为 **Stage 41（`41/41` 里程碑，Schema `realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase226_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_hil=True`，可通过 `--skip-phase226` 跳过；本地只读供体 41 阶段全板协同仿真 `< 2.3s`、洁净室模式 `< 0.65s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`steadyshot_active_cutoff_bypass_events == 0`、`ciz_4lock_unrestored_or_bypass_events == 0`、`tier0_p3_sleep_abort_or_thermal_burn_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libInfraLensCommunicator.so`（`14,544 B` 零差异 ABI）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`：`AVBB_SCN_START_HDMI` / `AVBB_SCN_STOP_HDMI`）、`string_english_f.uxc`（`373,820 B`：证实 `SteadyShot` / `Active` / `Standard` / `RAW Output` / `119.88p` / `100p` / `120fps` / `Clear Image Zoom` / `Digital Zoom` / `Zoom Range` / `Optical zoom only` / `Focus Area` / `Metering Mode` / `Multi` / `Face/Eye Prior. in AF` / `Face Priority in Multi Metering` / `Tracking` / `Power Save Start Time` / `30 Min` / `10 Sec` / `IR Remote Ctrl` / `Bluetooth Rmt Ctrl` / `Auto Power OFF Temp.` / `High` / `Fan Control`）与 `string_english.uxc`（`118,208 B`），并对 `appFw.so`、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-model A — 视频 `[SteadyShot]` `[Active]` `~1.1x` 裁切 vs `[Standard]`/`[Off]` 与三重硬截止 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Image Stabilization] -> [SteadyShot]`：`[Active]` 施加 `1.10x` 视角裁切并启用 5 轴光学移轴 + 电子陀螺仪裁切增稳（尝试强行抑制 `1.10x` 裁切返回 `EOPNOTSUPP = 95`），`[Standard]` 保持 `1.00x` 纯 5 轴光学移轴，`[Off]` 锁定音圈防抖机构并校验手动焦距 `[SteadyShot Focal Len.]` `8..1000mm` 范围（越界返回 `EINVAL = 22`）；严格执行 **`[Active]` 三重硬截止**：① 常规视频 `119.88p / 100p`、② `S&Q` 传感器采样帧率 `>= 100fps / 120fps`（`1..60fps` 正常开放）、③ 外接 Type-A HDMI `[RAW Output] = On`（未开启自动降级时以 `EOPNOTSUPP = 95` 阻断，开启自动回退时平滑钳位至 `Standard` `1.00x`）。
3. **Sub-model B — `[Clear Image Zoom]` / `[Digital Zoom]`（`[Zoom Range]`）RAW/HFR 禁用矩阵、4 项自动状态锁死与 `1.0x` 无损恢复 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Zoom] -> [Zoom Range]`（`Optical zoom only` `1.0x`、`Smart Zoom`、`Clear Image Zoom` 4K `1.5x` / HD & 照片 `2.0x`、`Digital Zoom` `4.0x`），在外接 HDMI `[RAW Output]=On`、常规 `119.88p/100p`、`S&Q >= 100fps` 及照片 `RAW / RAW & JPEG / RAW & HEIF` 下以 `EOPNOTSUPP = 95` 硬禁用超光学变焦；一旦进入 `> 1.0x` 超光学变焦区间，**自动联动施加全部 4 项相机状态锁**：① `[Focus Area]` 灰显禁用并退化为中心优先对焦框、② `[Metering Mode]` 强制锁定为 `[Multi]`、③ `[Face/Eye Prior. in AF]` 与 `[Face Priority in Multi Metering]` 禁用归 `Off`、④ 主体 `Real-time Tracking` 实时追踪禁用（越权覆盖尝试返回 `EOPNOTSUPP = 95`），并在变焦退回 `1.0x` 光学范围时 **100% 比特精确恢复** 用户原设定的对焦区域、测光模式、人脸/人眼对焦与追踪状态。
4. **Sub-model C & Redlines — `[Power Save Start Time]`（默认 `5 Min`）9 条件自动解除矩阵、气隙 `NP-FZ100` Tier-0 `75 MiB` `p3` 防休眠门控与 `[Auto Power OFF Temp.]` + `[Fan Control]` 耦合 HIL**：
   - 协同仿真完整菜单键名 `"Power Save Start Time"`（6 档：`Off`、`30 Min`、默认 `5 Min`、`2 Min`、`1 Min`、`10 Sec`）的 **9 项自动失效条件**（AC/USB-PD 供电、USB 数据连接、HDMI 输出连接、视频录制中、间隔拍摄中、幻灯片播放中、`[IR Remote Ctrl]=On`、`[Bluetooth Rmt Ctrl]=On`、FTP/手机无线传输中）；针对 9 项条件全为 `False` 的气隙纯电池 `NP-FZ100` 台架场景，强门控 **Tier-0 `75 MiB` `p3` 冷备导出必须设为 `Off` 或 `30 Min`** + 电量 `>= 51%` + `[Fan Control]=Auto` + 物理气隙隔离（保留默认 `5 Min` 或更短档位立即返回 `EOPNOTSUPP = 95` 防止中途待机休眠中断）；同时仿真 `[Auto Power OFF Temp.]`（`Standard` `68°C` vs `High` `78°C`），在手持（`Handheld`）状态下硬拦截 `[High]` 防止低温接触烫伤，禁止 `[High]` + `[Fan Control]=Always Off` 危险组合，高温自动触发 `100%` 风扇覆盖与优雅关机刷盘，并 fail-closed 锁死全部 9 项硬件写入/挂载/越权红线。

### Phase 226 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 41（41/41 里程碑）自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py --self-test --json

# 2. 全板 41 阶段（Stage 1..41, 41/41 里程碑）统一校验（支持 --skip-phase226）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 226 56 项双模单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_steadyshot_active_ciz_4locks_powersave_autotemp_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 232：Stage 42（`42/42` 里程碑）真实硬件主线 — Wave-32 `[Mode Settings]` (`Fixed/Variable`) S&Q 6 项硬锁矩阵、`[Zebra]`/`[Peaking]` 本地 LCD 专属与 HDMI 零像素净流隔离、以及 `[Full Format]` / `MENU+(Delete)` 2 秒组合键 Tier-0 保险库防火墙 HIL 协同仿真器

[`realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py`](realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py) 作为 **Stage 42（`42/42` 里程碑，Schema `realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase232_realhw_sq_fixedvar_zebra_peaking_fullformat_hil=True`，可通过 `--skip-phase232` 跳过；本地只读供体 42 阶段全板协同仿真 `< 2.4s`、洁净室模式 `< 0.65s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`sq_fixedvar_6lock_bypass_events == 0`、`hdmi_zebra_or_peaking_leaked_overlay_pixels == 0`、`tier0_slot1_format_or_chord_wipe_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libInfraLensCommunicator.so`（`14,544 B`）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`：`AVBB_SCN_START_HDMI` / `AVBB_SCN_STOP_HDMI` / `Format` / `Delete`）、`string_english_f.uxc`（`373,820 B`：证实 `Mode Settings` / `Fixed/Variable` / `S&Q Settings` / `FPS` / `Home` / `Audio Out Timing` / `Live` / `Lip Sync` / `Time Code Run` / `Time Code Output` / `XAVC HS 4K` / `XAVC S 4K` / `XAVC S-I 4K` / `XAVC S-I DCI 4K` / `240fps` / `200fps` / `120fps` / `100fps` / `Proxy Recording` / `Zebra Display` / `Zebra Display Select` / `Zebra Level` / `100+` / `Peaking Display` / `Peaking Display Select` / `Peaking Level` / `Peaking Color` / `HDMI Info. Display` / `Camera Settings Reset` / `Initialize` / `Format` / `Quick Format` / `Full Format` / `Switch Full Format` / `Slot 1` / `Slot 2` / `Enter` / `Delete`）与 `string_english.uxc`（`118,208 B`），并对 `appFw.so`、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-model A — Ver. 7.00+/7.02 `[Mode Settings]` = `[Fixed/Variable]` 锁定旧版 `[S&Q Settings]` 与 6 项 S&Q 硬件禁用矩阵 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Shooting Mode] -> [Mode Settings] = [Fixed/Variable]`：旧版 `[S&Q Settings]` 菜单锁定不可用（强行访问返回 `EOPNOTSUPP = 95`），帧率直接由 `Home (FPS)` / `[FPS]` 控制；在 `Variable`（S&Q）模式下确定性执行 **全部 6 项硬件录制禁令**：① `0ch` 零音频录制（尝试采集音频返回 `EOPNOTSUPP = 95`）、② `[Audio Out Timing]`（`Live` / `Lip Sync`）禁用、③ `[Time Code Run]` 与 `[Time Code Output]` 不可用、④ `240fps`（NTSC）/ `200fps`（PAL）在全部 4 种 4K 格式（`XAVC HS 4K`、`XAVC S 4K`、`XAVC S-I 4K`、`XAVC S-I DCI 4K`）下硬拦截（仅允许 `XAVC S HD` / `XAVC S-I HD`）、⑤ `120fps`（NTSC）/ `100fps`（PAL）在 `XAVC S-I DCI 4K`（`4096x2160`）下硬拦截、⑥ 当 `Rec Frame Rate` 为 `119.88p/100p` 或拍摄帧率 `>= 120fps/100fps` 时硬阻断同时录制 `[Proxy Recording]`。
3. **Sub-model B — `[Zebra Display]` / `[Zebra Level]` 跨 `[Camera Settings Reset]` 存活（仅 `[Initialize]` 清零）与 `[Zebra]` + `[Peaking]` 严格本地 LCD 专属 HDMI 零像素隔离 HIL**：
   - 协同仿真 `[Zebra Display]`（`Off`/`On`，控制拨轮左键 `[Zebra Display Select]`）与 `[Zebra Level]`（`70..100+` 预设、`Custom 1` `Standard+Range` 曝光带、`Custom 2` `Minimum/Lower-Limit` 过曝下限）：执行 **`[Camera Settings Reset]` 时斑马纹开关与等级（含 `Custom 1`/`Custom 2`）完整保留**（常规参数如 `[Peaking Display]` 则重置回 `Off`/`Mid`/`White`），仅 **`[Initialize]`** 将斑马纹清零回 `Off` / `70`；同时严格执行硬件 HDMI 净流隔离——即便 **`[HDMI Info. Display] = On`**，外接 HDMI 信号上的斑马纹像素与峰值对焦描边像素（`High/Mid/Low`、`Red/Yellow/Blue/White`）恒为 **`0`**（强行向 HDMI 注入辅助叠加层返回 `EOPNOTSUPP = 95`）。
4. **Sub-model C & Redlines — Slot 1 `[Format]`（`[Enter]` 快速格式化 vs `(Delete)` 完全格式化 + 中途取消数据已擦除隐患）与拍摄界面 `MENU + (Delete)`（`~2s`）组合键 Tier-0 保险库防火墙 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Media] -> [Format]`（`[Enter]` 仅重置文件系统管理元数据的 **Quick Format** vs 确认框按 `(Delete)` 切换初始化全卡数据块 + 元数据的 **Full Format**，以及 Full Format 中途取消导致旧数据永久擦除但卡片立即可用的物理行为）与拍摄界面同时长按 **`MENU + (Delete)` `>= 2.0s`** 直达格式化确认框（`< 2.0s` 短按忽略、非拍摄界面以 `EOPNOTSUPP = 95` 拦截）；只要 **Slot 1** 存放未完成离机 SHA-256 校验或仍在位的 Tier-0 恢复保险库（`pnflasha` / `cnflasha` / `CAMSET01.DAT`），对上述全部 3 条破坏性格式化入口一律以 `EBUSY = 16` / `EROFS = 30`（SDXC 物理 WP 锁）fail-closed 硬拦截（`tier0_slot1_format_or_chord_wipe_events == 0`），并锁死全部 9 项硬件写入/挂载/越权红线。

### Phase 232 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 42（42/42 里程碑）自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py --self-test --json

# 2. 全板 42 阶段（Stage 1..42, 42/42 里程碑）统一校验（支持 --skip-phase232）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 232 58 项双模单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_sq_fixedvar_zebra_peaking_fullformat_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 236：Stage 43（`43/43` 里程碑）真实硬件主线 — Wave-33 `[Silent Mode Settings]` `[Auto Pixel Mapping]` 目标抑制与 `[Shutter When Pwr OFF]` 硬件缺席、`[Marker Display]` 15 比例跨复位存活与本地 LCD 专属 HDMI 零像素隔离、以及 `[Flexible Exp. Mode]` 复位分流 HIL 协同仿真器

[`realhw_silent_autopixelmap_marker_flexexp_coemulator.py`](realhw_silent_autopixelmap_marker_flexexp_coemulator.py) 作为 **Stage 43（`43/43` 里程碑，Schema `realhw_silent_autopixelmap_marker_flexexp_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase236_realhw_silent_autopixelmap_marker_flexexp_hil=True`，可通过 `--skip-phase236` 跳过；本地只读供体 43 阶段全板协同仿真 `< 2.5s`、洁净室模式 `< 0.70s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`silent_mode_5func_or_pwrshutter_bypass_events == 0`、`bench_shutdown_unsuppressed_auto_pixelmap_events == 0`、`hdmi_marker_leaked_overlay_pixels == 0`、`flexexp_or_marker_reset_split_drift_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **12 份真实供体**：`libInfraLensCommunicator.so`（`14,544 B`）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`：`AVBB_SCN_START_HDMI` / `AVBB_SCN_STOP_HDMI` / `HDMI` / `Auto`）、`string_english_f.uxc`（`373,820 B`：证实 `Silent Mode Settings` / `Silent Mode` / `Target Function Settings` / `Target` / `Not Target` / `Aperture Drive in AF` / `Auto Pixel Mapping` / `Pixel Mapping` / `Sensor Cleaning` / `Shutter Type` / `Shutter Type in Interval` / `Electronic Shutter` / `Mechanical Shutter` / `Long Exposure NR` / `e-Front Curtain Shut.` / `Anti-flicker Shoot.` / `BULB` / `Flash` / `Marker Display` / `Center Marker` / `Aspect Marker` / `Safety Zone` / `Guideframe` / 全部 15 种画幅比例 `9:16`..`2.39:1` / `80%` / `90%` / `HDMI Info. Display` / `Exposure Ctrl Type` / `P/A/S/M Mode` / `Flexible Exp. Mode` / `Auto/Manual Swt. Set.` / `Av Auto/Manual Switch` / `Tv Auto/Manual Switch` / `ISO Auto/Manual Set` / `Auto Slow Shutter` / `Camera Settings Reset` / `Initialize`）与 `string_english.uxc`（`118,208 B`），并对 `appFw.so`、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-model A — `[Silent Mode Settings]` 5 项拍摄功能锁止、`[Target Function Settings]`（`[Aperture Drive in AF]` & `[Auto Pixel Mapping]`）断电暗场校准抑制与 `ILME-FX3`（`Ver. 2.00..7.02`）`[Shutter When Pwr OFF]` 硬件缺席拦截 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Shutter/Silent] -> [Silent Mode Settings]`：开启 `[Silent Mode] = [On]` 自动将 `[Shutter Type]` 与 `[Shutter Type in Interval]` 锁定为 `[Electronic Shutter]`、将 `[Audio signals]` 锁定为 `[Off]`，并禁用 **全部 5 项拍摄功能**（`Flash`、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.`，强行调用返回 `EOPNOTSUPP = 95`）。
   - `[Target Function Settings]` 独立控制 `[Aperture Drive in AF]` 与 `[Auto Pixel Mapping]`：设为 `[Not Target]` 时即便 `[Silent Mode] = [On]` 亦保留原设定；将 `[Auto Pixel Mapping]` 设为 `[Target]` 并在受控 Tier-0 备份/恢复台架关机前启用 `[Silent Mode] = [On]`，可非侵入式抑制周期性断电机械快门暗场像素映射（`poweroff_mech_shutter_darkframe_actuations == 0`、`poweroff_cnflasha_calibration_touches == 0`；未抑制的受控台架关机以 `EBUSY = 16` 硬拦截）。
   - 严格区分微单拍照机身与 `ILME-FX3`（`Ver. 2.00..7.02`）：`ILME-FX3` 在 `[Anti-dust Function]` 下仅提供 `[Sensor Cleaning]`、`[Auto Pixel Mapping]` 与 `[Pixel Mapping]`，任何请求或挂载不存在的 **`[Shutter When Pwr OFF]`** 均一律以 `EOPNOTSUPP = 95` fail-closed 硬拦截。
3. **Sub-model B — `[Marker Display]`（`Center Marker`、`Aspect Marker` `Off` + 15 种 `Ver. 3.00+/7.02` 比例、`Safety Zone` `Off/80%/90%`、`Guideframe`）跨 `[Camera Settings Reset]` 存活与本地 LCD 专属 HDMI 零像素隔离 HIL**：
   - 完整建模 `Off` 与 **全部 15 种 `Ver. 3.00+/7.02` 画幅标记比例**（`9:16`、`4:5`、`1:1`、`4:3`、`13:9`、`14:9`、`15:9`、`16:9` *(`Ver. 3.00+` 新增，`Ver. 2.00` 下返回 `EOPNOTSUPP = 95`)*、`17:9`、`1.66:1`、`1.85:1`、`1.91:1`、`2:1`、`2.35:1`、`2.39:1`）：执行 **`[Camera Settings Reset]` 时全部标记配置原样保留**，仅 **`[Initialize]`** 清零回 `Off`；同时严格执行机身本地 LCD 独占渲染——即便 **`[HDMI Info. Display] = [On]`**，外接 HDMI 视频流中的画幅/安全框/十字中心标记像素恒为 **`0`**（强行向 HDMI 输出标记叠加层返回 `EOPNOTSUPP = 95`）。
4. **Sub-model C & Redlines — `[Exposure Ctrl Type]`（`P/A/S/M Mode` vs `Flexible Exp. Mode`）与 `[Auto/Manual Swt. Set.]` / `[Auto Slow Shutter]` 复位分流 + 安全红线锁死 HIL**：
   - 协同仿真 `[Exposure Ctrl Type]` 切换（`P/A/S/M Mode` 下直接访问 `[Auto/Manual Swt. Set.]` 以 `EOPNOTSUPP = 95` 拦截）与 `Flexible Exp. Mode` 下的 `Av` / `Tv` / `ISO` 独立自动/手动切换（三项默认均为 `Manual`）及 `[Auto Slow Shutter]`（默认 `On`）：执行 **`[Camera Settings Reset]` 时 `Av`/`Tv`/`ISO` 干净复位回 `Manual`、`[Auto Slow Shutter]` 干净复位回 `On`**，与同机跨复位保留的 `[Marker Display]` / `[Aspect Marker]` 构成确定性复位分流对照，并支持从 Slot 1 `CAMSET01..10.DAT` 零持久化写入（`bk4_persistent_nvram_writes == 0`）无漂移恢复及锁死全部 10 项硬件安全红线。

### Phase 236 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 43（43/43 里程碑）自检
/usr/bin/python3 -B outputs/fx3-vm/realhw_silent_autopixelmap_marker_flexexp_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_silent_autopixelmap_marker_flexexp_coemulator.py --self-test --json

# 2. 全板 43 阶段（Stage 1..43, 43/43 里程碑）统一校验（支持 --skip-phase236）
/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 236 双模单测 & 全量 fx3-vm 单测（双模）
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_silent_autopixelmap_marker_flexexp_coemulator.py
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_silent_autopixelmap_marker_flexexp_coemulator.py
PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"
```

## Phase 239：Stage 44（`44/44` 里程碑）真实硬件主线 — Wave-34 `[Recover Image DB]` 低电量拒写与非删除 `AVF_INFO` 修复 + Slot-1 Tier-0 保险库只读防火墙、`[Monitor Flip Direction]` 跨复位存活与 `[Horizontal Flip]` 回放永不倒置、以及 `[AF Transition Speed]` / `[AF Subj. Shift Sensitivity]` 完整拼写对静照 `[Interval Shoot Func.]` HIL 协同仿真器

[`realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py`](realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py) 作为 **Stage 44（`44/44` 里程碑，Schema `realhw_recover_imagedb_monitor_flip_af_sens_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase239_realhw_recover_imagedb_monitor_flip_af_sens_hil=True` / `include_stage44=True`，支持显式 `--include-stage44` 以及通过 `--skip-phase239` / `--skip-stage44` 跳过；本地只读供体 44 阶段全板协同仿真 `< 2.6s`、洁净室模式 `< 0.70s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`tier0_slot1_unverified_imagedb_mutation_events == 0`、`playback_horizontal_flip_inversion_events == 0`、`monitor_flip_or_af_kinematics_drift_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **14 份真实供体**：`libIMDB.so`（`71,536 B`：`IMDB_find_entry` / `IMDB_get_entries` / `IMDB_find_target_bit`）、`libSaveLoadSettings.so`（`18,760 B`：`Backup_get_datasize` / `Backup_read` / `infra_saveLoadSettings_init`）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`：`AVBB_SCN_START_HDMI` / `AVBB_SCN_STOP_HDMI`）、`libInfraLensCommunicator.so`（`14,544 B`）、`string_english_f.uxc`（`373,820 B`：证实 `Recover Image DB` / `Slot 1` / `Slot 2` / `Monitor Flip Direction` / `Horizontal Flip` / `AF Transition Speed` / `AF Subj. Shift Sensitivity` / `1(Locked on)` / `5(Responsive)` / `Interval Shoot Func.` / `Shooting Start Time` / `Shooting Interval` / `Number of Shots` / `Playback` / `HDMI Info. Display` / `Camera Settings Reset` / `Initialize`）与 `string_english.uxc`（`118,208 B`：`AF Transition Speed` / `AF Subj. Shift Sens.`），并对 `appFw.so`、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 44A — `[Recover Image DB]` 低电量拒写、非删除 `AVF_INFO` 修复、动作项复位免疫与 Slot-1 Tier-0 保险库只读防火墙 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Media] -> [Recover Image DB]`：当 `NP-FZ100` 处于极度亏电状态（`battery_state == "extremely_depleted"`、`battery_soc_pct < 10` 或 `battery_mv < 6400`）时，硬件在任何 FAT/exFAT 扇区写入发生之前立即以 `EAGAIN = 11` 拒绝执行（`hardware_refused_before_fat_exfat_write == True`、`card_metadata_sector_writes == 0`），防止掉电损坏分区表。
   - 在电量充足的工作卡上重建 `AVF_INFO`（`AVIN0001.INP`、`AVIN0001.BNP`、`PRV00001.BIN`）与 `M4ROOT/MEDIAPRO.XML` 以消除 `"Image DataBase File error"` 或可拍摄张数误显示为 `"0"` 的索引不一致，**严格不删除任何已录制的视频或照片**（`deleted_clip_or_still_count == 0`，尝试借机删除媒体返回 `EOPNOTSUPP = 95`），并验证其作为即时动作项对 `[Camera Settings Reset]` 与 `[Initialize]` 的免疫性。
   - 强执行 **Slot-1 Tier-0 取证冷备保险库只读防火墙**：当 Slot 1 驻留包含 `pnflasha` / `cnflasha` / `CAMSET01.DAT` / `FX3RCPT1.BIN` 的活跃或未完成离机 SHA-256 核验的 Tier-0 备份卡时，对 Slot 1 的 `[Recover Image DB]` 请求一律以 `EROFS = 30`（SDXC 物理 `WP` 锁止）或 `EBUSY = 16` fail-closed 硬阻断（`tier0_slot1_unverified_imagedb_mutation_events == 0`）；同时允许电量充足时对 Slot 2 独立工作卡执行非删除修复，或仅在 Tier-0 保险库卡完成离机 SHA-256 核验并安全退出现场更换为未锁工作卡后放行 Slot 1 修复。
3. **Sub-Model 44B — `[Monitor Flip Direction]` 跨 `[Camera Settings Reset]` 存活与 `[Horizontal Flip]` 回放永不倒置 HIL**：
   - 完整建模 `MENU -> Setup -> [Monitor] -> [Monitor Flip Direction]` 四档（出厂默认 `Auto`、`Horizontal Flip`、`Vertical Flip`、`Off`）：执行 **`[Camera Settings Reset]` 时完整保留原设定**（`reset_only_by_initialize == True`），仅全机 **`[Initialize]`** 将其恢复回 `Auto`。
   - 严格区分实时取景与机内回放：开启 `[Horizontal Flip]` 时仅对实时拍摄取景（`live_shooting`）下的本地 LCD 画面做水平镜像（`live_shooting_lcd_horizontally_mirrored == True`），而**回放模式（`playback`）下画面方向永不水平翻转**（`playback_display_horizontally_inverted == False`、`playback_horizontal_flip_inversion_events == 0`，保证时间码与文字正常可读；强行翻转回放画面返回 `EOPNOTSUPP = 95`），且外接 HDMI 净流始终保持未翻转（`external_hdmi_clean_feed_flipped == False`）。
4. **Sub-Model 44C & Redlines — 视频/S&Q 对焦运动学（`[AF Transition Speed]` `1..7` & `[AF Subj. Shift Sensitivity]` `1..5` 完整拼写）对静照 `[Interval Shoot Func.]` 隔离 + 安全红线锁死 HIL**：
   - 精确建模 `ILME-FX3` 完整菜单拼写 **`[AF Subj. Shift Sensitivity]`**（`1(Locked on)`..`5(Responsive)`，默认 `5(Responsive)`；对 `FX6`/`Alpha` 缩写幻觉 `"AF Subj. Shift Sens."` 等一律以 `EINVAL = 22` 拒绝）与 **`[AF Transition Speed]`**（`1(Slow)`..`7(Fast)`，默认 `5`）：二者均作用于视频与 S&Q 模式（静照模式下强行启用返回 `EOPNOTSUPP = 95`），并在 **`[Camera Settings Reset]` 下干净复位回 `5` / `5(Responsive)`**，与同机跨复位保留的 `[Monitor Flip Direction]` 构成确定性非对称复位分流对照（`monitor_flip_or_af_kinematics_drift_events == 0`），同时支持从 Slot 1 `CAMSET01..10.DAT` 零持久化写入（`bk4_persistent_nvram_writes == 0`）无漂移恢复。
   - 对照建模 `MENU -> Shooting -> [Drive Mode] -> [Interval Shoot Func.]`（`Shooting Start Time` `1s..99m59s` = `1..5999s`、`Shooting Interval` `1s..60s`、`Number of Shots` `1..9999`）：严格限定为静照序列采集（`JPEG`/`HEIF`/`RAW`，后期通过 `Imaging Edge Desktop (Viewer)` 合成），任何将其混淆为 FX6 机内 MXF/MP4 视频 `Interval Rec` 的请求一律以 `EOPNOTSUPP = 95` fail-closed 拦截，并锁死全部 10 项硬件安全红线。

### Phase 239 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 44（44/44 里程碑）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py --self-test --json

# 2. 全板 44 阶段（Stage 1..44, 44/44 里程碑）统一校验（支持 --include-stage44 与 --skip-phase239）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage44 --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 239 双模单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py' -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_recover_imagedb_monitor_flip_af_sens_coemulator.py' -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 242：Stage 45（`45/45` 里程碑）真实硬件主线 — Wave-35 `[Emphasized REC Display]` 与 `[Grid Line Display]` 外接 HDMI Info 分流 vs `[Off(HDMI Only)]` / `RAW` 强制净流锁止、`[Touch Operation]` 4 项跨复位存活与台架误触防护、以及 `[Monitor Brightness]` `[Manual]`（`-2..+2`）对 `[Sunny Weather]` 室内过曝与 `NP-FZ100` 功耗护栏 HIL 协同仿真器

[`realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py`](realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py) 作为 **Stage 45（`45/45` 里程碑，Schema `realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase242_realhw_emphasized_rec_grid_hdmi_touch_sunny_hil=True` / `include_stage45=True`，支持显式 `--include-stage45` 以及通过 `--skip-phase242` / `--skip-stage45` / `--no-include-stage45` 跳过；本地只读供体 45 阶段全板协同仿真 `< 2.7s`、洁净室模式 `< 0.75s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`hdmi_only_or_raw_baked_recframe_or_grid_frames == 0`、`hdmi_local_only_marker_zebra_peaking_leaked_pixels == 0`、`unattended_bench_accidental_touch_events == 0`、`indoor_sunny_weather_unclamped_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **14 份真实供体**：`libSaveLoadSettings.so`（`18,760 B`：`Backup_get_datasize` / `Backup_read` / `infra_saveLoadSettings_init`）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`：`AVBB_SCN_START_HDMI` / `AVBB_SCN_STOP_HDMI`）、`libIMDB.so`（`71,536 B`）、`libInfraLensCommunicator.so`（`14,544 B`）、`string_english_f.uxc`（`373,820 B`：证实 `Emphasized REC Display` / `Grid Line Display` / `Grid Line Type` / `Rule of 3rds Grid` / `Square Grid` / `Diag. + Square Grid` / `HDMI Info. Display` / `Rec. Media dur HDMI Output` / `Off(HDMI Only)` / `RAW Output` / `Touch Operation` / `On: Playback Only` / `Touch Sensitivity` / `Swipe Up` / `Open the Fn Menu` / `Touch Func. in Shooting` / `Touch Tracking` / `Touch Focus` / `Brightness` / `Manual` / `Sunny Weather` / `Camera Settings Reset` / `Initialize`）与 FX6 `string_english.uxc`（`118,208 B`），并对 `appFw.so`、`cpapp-b.bin` 与 `libmpr.so` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地供体缺席时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 45A — `[Emphasized REC Display]` 与 `[Grid Line Display]` 外接 HDMI Info 分流 vs `[Off(HDMI Only)]` / `RAW` 强制净流锁止 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Shooting Display] -> [Emphasized REC Display]`（默认 `On`，视频与 `S&Q` 录制时激活四周红框；待机与静照下不激活；执行 **`[Camera Settings Reset]` 会被复位回 `On`**，可经 Slot 1 `CAMSET01..10.DAT` 零持久化写入 `bk4_persistent_nvram_writes == 0` 精确恢复）与 `[Grid Line Display]` / `[Grid Line Type]`（默认 `Off` + `Rule of 3rds Grid`，支持 `Rule of 3rds Grid`、`Square Grid`、`Diag. + Square Grid` 三种构图网格；**跨 `[Camera Settings Reset]` 完整存活**，`grid_line_reset_only_by_initialize == True`，仅全机 `[Initialize]` 清零）。
   - 严格区分本地专属监看辅助与可随 OSD 外送的叠加层：不同于永不走 HDMI 的本地专属 `Marker` / `Zebra` / `Peaking`（`hdmi_local_only_marker_zebra_peaking_leaked_pixels == 0`，强行外送返回 `EOPNOTSUPP = 95`），当 `[HDMI Info. Display]=On` 且处于常规录制路由时，`[Emphasized REC Display]` 红框与 `[Grid Line Display]` 网格**均会随 OSD 合成输出至外接 HDMI**（同时黑屏关闭机身本地 LCD）；一旦进入 `[Rec. Media dur HDMI Output]=[Off(HDMI Only)]` 或开启 HDMI `RAW Output`，硬件自动强制锁死 `[HDMI Info. Display]=Off`（`hdmi_only_or_raw_baked_recframe_or_grid_frames == 0`，尝试绕过净流锁返回 `EOPNOTSUPP = 95`），彻底杜绝外部录机将录制红框或构图网格永久烧录进主素材。
3. **Sub-Model 45B — `[Touch Operation]` 4 项跨 `[Camera Settings Reset]` 存活与无人值守台架误触防护 HIL**：
   - 完整建模 `MENU -> Setup -> [Touch Operation]` 全部 **4 个子项**：`[Touch Operation]`（`On` 默认 / `On: Playback Only` / `Off`）、`[Touch Sensitivity]`（`Standard` 默认 / `Sensitive`）、`[Swipe Up]`（`Open the Fn Menu` 默认 / `Off`）、`[Touch Func. in Shooting]`（`Touch Tracking` 默认 / `Touch Focus` / `Off`）；**全部 4 项均完整跨越 `[Camera Settings Reset]` 保留原设定**（`reset_only_by_initialize == True`），仅全机 `[Initialize]` 恢复出厂默认。
   - 强执行无人值守台架演练防误触护栏：在台架固定演练下设为 `[Touch Operation]=Off`（或针对拍摄锁止的 `On: Playback Only`）可彻底阻断线束擦碰电容屏诱发的 `Swipe Up` 弹出 Fn 菜单或 `Touch Tracking` 焦点跳变（`unattended_bench_accidental_touch_events == 0`）；无人值守台架若遗留 `[Touch Operation]=On` 则以 `EBUSY = 16` fail-closed 拦截。
4. **Sub-Model 45C & Redlines — `[Monitor Brightness]` `[Manual]`（`-2..+2`）对 `[Sunny Weather]` 室内过曝与 `NP-FZ100` 功耗护栏 + 安全红线锁死 HIL**：
   - 精确建模 `MENU -> Setup -> [Monitor] -> [Monitor Brightness]`（默认 `Manual` `0`，覆盖 `-2..+2` 共 5 档背光阶梯 `380..540 mW`，对比户外强光专用的 `[Sunny Weather]` `980 mW`）：跨 **`[Camera Settings Reset]` 完整存活**（`reset_only_by_initialize == True`），仅 `[Initialize]` 恢复回 `Manual`（`0`）；在室内暗房/台架演练下检测到 `[Sunny Weather]` 时立即标定手动曝光偏暗误判与 `NP-FZ100` 额外背光功耗风险并以 `EBUSY = 16` 拦截（`indoor_sunny_weather_unclamped_events == 0`，尝试绕过护栏返回 `EOPNOTSUPP = 95`），同时锁死全部 11 项硬件安全红线探针。

### Phase 242 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 45（45/45 里程碑）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py --self-test --json

# 2. 全板 45 阶段（Stage 1..45, 45/45 里程碑）统一校验（支持 --include-stage45 与 --skip-phase242）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage45 --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 242 双模单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py' -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_emphasized_rec_grid_hdmi_touch_sunny_coemulator.py' -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 244：Stage 46（`46/46` 里程碑）真实硬件主线 — Wave-36 `[Shoe Audio Set.]` `48kHz/24bit 4ch` 电平表扩展 vs `3.5mm` / `ANALOG` / `S&Q` 三重锁止、`[Wind Noise Reduct.]` 机身内置麦克风独占与室内低切护栏、以及 `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` 隐私校准排除防火墙与 Slot-1 Tier-0 写保护 HIL 协同仿真器

[`realhw_shoe_audio_wind_saveload_c3_coemulator.py`](realhw_shoe_audio_wind_saveload_c3_coemulator.py) 作为 **Stage 46（`46/46` 里程碑，Schema `realhw_shoe_audio_wind_saveload_c3_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase244_realhw_shoe_audio_wind_saveload_c3_hil=True` / `include_stage46=True`，支持显式 `--include-stage46` 以及通过 `--skip-phase244` / `--skip-stage46` / `--no-include-stage46` 跳过；本地只读供体 46 阶段全板协同仿真 `< 2.8s`、洁净室模式 `< 0.80s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`shoe_audio_4ch_disqualification_bypass_events == 0`、`external_mic_wind_reduct_applied_frames == 0`、`excluded_secret_or_calibration_leak_events == 0`、`tier0_slot1_unverified_camset_save_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **14 份真实供体**：`libSaveLoadSettings.so`（`18,760 B`：`Backup_get_datasize` / `Backup_read` / `infra_saveLoadSettings_init`）、`libIMDB.so`（`71,536 B`）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`）、`string_english_f.uxc`（`373,820 B`：证实 `Shoe Audio Set.` / `48kHz` / `16bit` / `24bit` / `2ch` / `4ch` / `Audio Recording` / `Audio Level Display` / `Wind Noise Reduct.` / `S&Q` / `Save/Load Settings` / `Cloud(Private)` / `Cloud(Share)` / `IPTC Information` / `Copyright Info` / `Write Copyright Info` / `Custom` / `White Balance` / `Face Memory` / `FTP Transfer Func.` / `Streaming` / `Wi-Fi` / `Slot 1` / `Slot 2` / `Camera Settings Reset` / `Initialize`）与 FX6 `string_english.uxc`（`118,208 B`：`All File` / `Shoe` / `Wind`），并对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 与 `BK4` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或本地供体缺席时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 46A — `[Shoe Audio Set.]` `48kHz/24bit 4ch` 电平表扩展 vs `3.5mm` 插孔、`ANALOG` 拨杆与 `S&Q` 三重锁止 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Audio Recording] -> [Shoe Audio Set.]`（出厂默认 `48kHz/16bit 2ch`，可选 `48kHz/24bit 2ch` 与 `48kHz/24bit 4ch`；执行 **`[Camera Settings Reset]` 会干净复位回 `48kHz/16bit 2ch`**，并可经 Slot 1 `CAMSET01..10.DAT` 零持久化写入 `bk4_persistent_nvram_writes == 0` 精确恢复）：当挂载支持数字 4ch 的 MI 热靴配件（`XLR-H1` `DIGITAL` 模式或 `ECM-M1`）并启用 `48kHz/24bit 4ch` 时，`[Audio Level Display]` 自动将拍摄 OSD 电平表由 `2ch` 扩展为 `4ch`（`CH1..CH4`）。
   - 严格强制 **3 项硬件锁止/覆盖规则**（`shoe_audio_4ch_disqualification_bypass_events == 0`，强行绕过一律以 `EOPNOTSUPP = 95` 拦截）：① `[Audio Recording]=Off` 或 `S&Q Motion` 下禁用音频录制（`0` 音轨，菜单置灰）；② 机身 `3.5mm` `MIC` 插孔接入时硬件优先接管，强制覆盖内置麦与 MI 热靴为 `2ch` `48kHz/16bit` 模拟 ADC 采集；③ `XLR-H1` `[DIGITAL/ANALOG]` 拨杆置于 `ANALOG` 时旁路数字 I2S `24bit/4ch` 链路并回退至 `2ch` `48kHz/16bit` 模拟通道。
3. **Sub-Model 46B — `[Wind Noise Reduct.]` 机身内置立体声麦克风独占与室内台架低切护栏 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Audio Recording] -> [Wind Noise Reduct.]`（默认 `Off` / `On`，可由 `[Camera Settings Reset]` 复位回 `Off`）：数字风噪高通滤波**严格仅对机身内置立体声麦克风生效**——外接机身 `3.5mm` `MIC` 或 MI 热靴 `XLR-H1` / `ECM-M1` 时恒不作用（`external_mic_wind_reduct_applied_frames == 0`，`XLR-H1` 由手柄物理 `[LOW CUT]` `Off`/`100Hz`/`300Hz` 拨杆独立控制硬件低切，强行对外置麦注入机身风噪 DSP 返回 `EOPNOTSUPP = 95`）；在室内无强风台架演练下开启 `On` 立即触发低频衰减告警并以 `EBUSY = 16` 抑制，且在 `S&Q Motion` / `[Audio Recording]=Off` 下锁止置灰。
4. **Sub-Model 46C & Redlines — `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal` 排除项隐私校准防火墙、同机型锁与 Slot-1 Tier-0 保险库写保护 HIL**：
   - 完整建模 `MENU -> Setup -> [Reset/Save Settings] -> [Save/Load Settings]` 在 `Media`（`Slot 1` / `Slot 2`，每卡最多 `10` 组 `CAMSET01.DAT..CAMSET10.DAT`，严格锁定 `ILME-FX3` 并以 `EOPNOTSUPP = 95` 拦截 `ILME-FX6` 跨机型配置）与 `Cloud(Private)` / `Cloud(Share)`（`Creators' Cloud` / `C3 Portal`，要求 `Ver. 4.00+`）下的读写契约。
   - 强执行索尼官方 **4 大类排除项防火墙**（`excluded_secret_or_calibration_leak_events == 0`）：`IPTC Information` / `Copyright Info`、`Custom White Balance 1..3` 传感器校准值、`Face Memory` 人脸特征库、以及 `FTP` / `Streaming` / `Wi-Fi` / 静态 IP / TLS 证书凭据在 `[Save]` 时彻底剥离、在 `[Load]` 时 100% 保留机内原值（强行夹带返回 `EOPNOTSUPP = 95`）；同时对驻留 Slot 1 的 Tier-0 取证备份卡阻断 `[Save]` 覆写（物理 `WP` 锁返回 `EROFS = 30`，未离线 SHA-256 核验退出的保险库卡返回 `EBUSY = 16`，`tier0_slot1_unverified_camset_save_events == 0`），而 `[Load]` 保持严格 `O_RDONLY` 零扇区写入，并锁死全部 12 项硬件安全红线探针。

### Phase 244 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Stage 46（46/46 里程碑）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_shoe_audio_wind_saveload_c3_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_shoe_audio_wind_saveload_c3_coemulator.py --self-test --json

# 2. 全板 46 阶段（Stage 1..46, 46/46 里程碑）统一校验（支持 --include-stage46 与 --skip-phase244）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage46 --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 244 双模单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_shoe_audio_wind_saveload_c3_coemulator.py' -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_shoe_audio_wind_saveload_c3_coemulator.py' -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 250（第 250 阶段里程碑！`250th` Phase Milestone）：Stage 47（`47/47` 里程碑）真实硬件主线 — Wave-37 `[Framing Settings]` 非对称 `Full`/`Crop` 双路路由与 HDMI `RAW` 互斥锁、`[USB Power Supply]` 强制 `NP-FZ100` 电池在位 + `USB Type-C` 独占与 `[USB LUN Setting]` `Multi`/`Single` 跨重置持久存活、以及 `[Anti-flicker Shoot.]` 仅限机械快门静态照片边界与原厂无 `[Var. Shutter]` HIL 协同仿真器

[`realhw_framing_usbpower_lun_antiflicker_coemulator.py`](realhw_framing_usbpower_lun_antiflicker_coemulator.py) 作为 **Phase 250（`250th` Phase Milestone）Stage 47（`47/47` 里程碑，Schema `realhw_framing_usbpower_lun_antiflicker_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase250_realhw_framing_usbpower_lun_antiflicker_hil=True` / `include_stage47=True`，支持显式 `--include-stage47` 以及通过 `--skip-phase250` / `--skip-stage47` / `--no-include-stage47` 跳过；本地只读供体 47 阶段全板协同仿真 `< 2.9s`、洁净室模式 `< 0.85s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`physical_usb_packets_emitted == 0`、`otp_fuse_touches == 0`、`rpmb_counter_increments == 0`、`framing_crop_hdmi_raw_conflict_events == 0`、`zve1_autoframing_conflation_events == 0`、`unbuffered_usb_pd_battery_pull_events == 0`、`multi_micro_usb_power_bypass_events == 0`、`antiflicker_movie_or_eshutter_bypass_events == 0`、`false_var_shutter_or_ecs_node_events == 0`、`fx3_has_var_shutter == False` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **15 份真实供体**：`libUsbBusPower.so`（`48,232 B`：`_ZN11UsbBusPower4MainEv` / `UsbBusPower` / `Backup_read`）、`libInfraMscServer.so`（`64,456 B`：`MscServer_Init` / `MassStorageServer_Create` / `ufw_ko_insmod`）、`libIMDB.so`（`71,536 B`）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`）、`string_english_f.uxc`（`373,820 B`：证实 `Framing Settings` / `Recording/Streaming` / `Crop` / `Full` / `USB Power Supply` / `USB LUN Setting` / `USB Connection Mode` / `Sel. When Connect` / `MassStorage(MSC)` / `Multi` / `Single` / `Anti-flicker Shoot.` / `Silent Mode` / `Camera Settings Reset` / `Initialize` 存在且无 `Autoframing Settings` 与 `ECS`）及 FX6 `string_english.uxc`（`118,208 B`：`ECS`），并对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 与 `BK4` 执行 `<= 4096 B` 有界窗口只读检查；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 47A — `[Framing Settings]` 非对称 `Full`/`Crop` 双路路由与 HDMI `RAW` 互斥锁 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Framing Settings]`（支持机内菜单或 Sony *Monitor & Control* 远程控制：`Framing` 默认 `Off`/`On`、`Recording/Streaming` 默认 `Full`/`Crop`、`HDMI` 默认 `Crop`/`Full`，三项均由 `[Camera Settings Reset]` 与 `[Initialize]` 恢复默认）：验证开启 `Framing=On` 时出厂非对称路由（机内存储卡/推流保留 `Full` 全画幅主素材，外部 HDMI 监看输出 `Crop` 裁切构图），拦截 `[Framing]=On` 与 HDMI `RAW` 同时开启冲突（`EBUSY = 16` / 强行绕过返回 `EOPNOTSUPP = 95`，`framing_crop_hdmi_raw_conflict_events == 0`），并拒绝将消费级 `ZV-E1`（`ilc/2330`）的 `[Autoframing Settings]` 混入 `ILME-FX3`（`ilc/2210`）。
3. **Sub-Model 47B — `[USB Power Supply]` 强制 `NP-FZ100` 电池在位 + `USB Type-C` 独占与 `[USB LUN Setting]` `Multi`/`Single` 持久存活 HIL**：
   - 协同仿真 `MENU -> Setup -> [USB]`（`[USB Connection Mode]=Sel. When Connect`、`[USB LUN Setting]=Multi`、`[USB Power Supply]=On`）：三项 `[Setup] -> [USB]` 配置在 **`[Camera Settings Reset]` 后完整保留不变**，仅由 **`[Initialize]`** 恢复出厂默认；无 `NP-FZ100` 电池（或 `DC-C1` 假电池耦合器）时拒绝开机（`EACCES = 13`），模拟 USB PD 供电中途拔出 `NP-FZ100` 触发立即无缓冲断电保护（`EBUSY = 16`，`unbuffered_usb_pd_battery_pull_events == 0`），强制 `Multi/Micro USB` 零供电/零充电边界（仅 `USB Type-C` 支持供电与关机机内充电，`EOPNOTSUPP = 95`），区分 `MassStorage(MSC)` 下 `Multi`（Slot 1 + Slot 2 双 LUN）与 `Single`（单主槽 LUN），并硬锁台架禁止直连主机 USB（`physical_usb_packets_emitted == 0`）。
4. **Sub-Model 47C & Redlines — `[Anti-flicker Shoot.]` 仅限机械快门静态照片边界与原厂 `ILME-FX3` 无 `[Var. Shutter]` HIL**：
   - 协同仿真 `MENU -> Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]`（默认 `Off` / `On`，可由 `[Camera Settings Reset]` 复位）：严格仅在 `Still` 静态拍摄 + `Mechanical` 机械快门 + `[Silent Mode]=Off` 下检测 `100 Hz` / `120 Hz` 人工照明频闪，在 `Movie` / `S&Q Motion` 或电子快门 / `[Silent Mode]=On` 下置灰禁用（强行绕过返回 `EOPNOTSUPP = 95`）；硬锁原厂 `ILME-FX3`（`ilc/2210` 至 `Ver. 7.02`）`fx3_has_var_shutter == False`（`false_var_shutter_or_ecs_node_events == 0`），拦截任何误套用 `FX30` / `ILCE-6700` `[Var. Shutter]` 或 `FX6` `ECS` 的跨机型假设，并锁死全部 14 项硬件安全红线探针。

### Phase 250 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 250（第 250 阶段里程碑！）Stage 47（47/47 里程碑）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_framing_usbpower_lun_antiflicker_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_framing_usbpower_lun_antiflicker_coemulator.py --self-test --json

# 2. 全板 47 阶段（Stage 1..47, 47/47 里程碑）统一校验（支持 --include-stage47 与 --skip-phase250）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage47 --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 250 双模单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_framing_usbpower_lun_antiflicker_coemulator.py' -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_framing_usbpower_lun_antiflicker_coemulator.py' -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 253：Stage 48（`48/48` 里程碑）真实硬件主线 — Wave-38 `[Lock Operation Parts]`（`Fn >= 3s` 锁键、`MENU + Fn >= 5s` 整机锁定组合键 vs 破坏性 `MENU + Delete >= 2s` 误格式化防火墙与 `[My Dial 1..3]` 临时拨轮覆盖）、`[Audio Out Timing]` vs `[Audio signals]` 跨重置分流与 `[Silent Mode]` 硬静音锁、以及 `[Exposure step]` `0.3EV`/`0.5EV` vs `[Shutter Angle]` 恒定快门角表免疫 HIL 协同仿真器

[`realhw_lock_op_parts_audio_timing_exp_step_coemulator.py`](realhw_lock_op_parts_audio_timing_exp_step_coemulator.py) 作为 **Phase 253 Stage 48（`48/48` 里程碑，Schema `realhw_lock_op_parts_audio_timing_exp_step_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase253_realhw_lock_op_parts_audio_timing_exp_step_hil=True` / `include_stage48=True`，支持显式 `--include-stage48` 以及通过 `--skip-phase253` / `--skip-stage48` / `--no-include-stage48` 跳过；本地只读供体 48 阶段全板协同仿真 `< 3.0s`、洁净室模式 `< 0.9s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`destructive_menu_delete_confusions == 0`、`slot1_vault_format_events == 0`、`silent_mode_audio_signal_leak_events == 0`、`shutter_angle_exposure_step_drift_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **15 份真实供体**：`string_english_f.uxc`（`373,820 B`：证实 `Lock Operation Parts` / `Dial/Wheel` / `Dial + Wheel` / `Multi-Selector` / `My Dial` / `Locked` / `Delete` / `Audio Out Timing` / `Live` / `Lip Sync` / `Audio Recording` / `Sound` / `Beep` / `Silent Mode` / `Exposure step` / `0.3EV` / `0.5EV` / `Shutter Mode` / `Shutter Speed` / `Angle` / `Speed` / `Camera Settings Reset` / `Reset Network Set.` / `Initialize`）、`libInfraAdjMedia.so`（`318,152 B`：`AUDIO` / `Backup_read`）、`libIMDB.so`、`libUsbBusPower.so`、`libInfraMscServer.so`、`libInfraMediaConfig.so` 及 FX6 `string_english.uxc`，并对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 与 `BK4` 执行 `<= 4096 B` 有界窗口只读核验；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 48A — `[Lock Operation Parts]`、整机锁定 `MENU + Fn >= 5s` vs 破坏性 `MENU + Delete >= 2s` 防火墙与 `[My Dial 1..3]` 临时拨轮覆盖 HIL**：
   - 协同仿真 `MENU -> Setup -> [Operation Customize] -> [Lock Operation Parts]`（`Off` 出厂默认 / `Multi-Slct Only` / `Dial/Wheel` / `Dial+Wheel+MSlct`）：作为 `[Setup]` 项在 **`[Camera Settings Reset]` 与 `[Reset Network Set.]` 后完整存活**，仅由 **`[Initialize]`** 恢复 `Off`；验证 `Fn` 长按 `>= 3.0s` 锁定/解锁切换（`"Locked."` / `"Unlocked."`），整机物理按键锁组合键 **`MENU + Fn >= 5.0s`**（即使 `[Lock Operation Parts]=Off` 亦锁定除快门键外的全部机身按键/拨轮/控制转盘/多向摇杆，并由 **`MENU + Fn >= 3.0s`** 解除），严防误触破坏性 **`MENU + Delete >= 2.0s`** Slot-1/Slot-2 全盘格式化组合键（Slot 1 Tier-0 救援保险箱返回 `EROFS = 30`，Slot 2 误触返回 `EACCES = 13`，`destructive_menu_delete_confusions == 0`、`slot1_vault_format_events == 0`），并验证 `[Lock Operation Parts]` 锁定标准拨轮时按住/唤起 `[My Dial 1..3]` 可临时覆盖解锁拨轮与控制转盘。
3. **Sub-Model 48B — `[Audio Out Timing]` vs `[Audio signals]` 重置分流与 `[Silent Mode]` 硬静音锁 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Audio Recording] -> [Audio Out Timing]`（`Live` 默认零延迟耳机返听防回声 / `Lip Sync` 匹配视频帧处理延迟，由 `[Camera Settings Reset]` 与 `[Initialize]` 复位至 `Live` 并在 `S&Q Motion` 或 `[Audio Recording]=Off` 下置灰禁用，强行绕过返回 `EOPNOTSUPP = 95`）与 `MENU -> Setup -> [Sound Option] -> [Audio signals]`（`On: all` 默认 / `On: shutter only` / `Off: all`，跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 持久存活，仅由 `[Initialize]` 复位；当 `[Silent Mode]=On` 时强制静音锁定为 `Off: all` 且保留底层 `[Setup]` 寄存器，`silent_mode_audio_signal_leak_events == 0`）。
4. **Sub-Model 48C & Redlines — `[Exposure step]` `0.3EV`/`0.5EV` 重构量化 vs `[Shutter Angle]` 恒定快门角表免疫 HIL**：
   - 协同仿真 `MENU -> Exposure/Color -> [Exposure] -> [Exposure step]`（`0.3EV` 默认 / `0.5EV`，可由 `[Camera Settings Reset]` 复位至 `0.3EV`）：验证切换 `0.5EV` 时同步重量化光圈（`F-stop`）、快门速度（`[Shutter Mode]=Speed`）、`ISO` 与曝光补偿（`EV`），而 `Ver. 7.02`（`Ver. 6.00+`）`[Shutter Mode]=Angle`（`5.6°..360°` 电影快门角表，含 `90°`、`172.8°`、`180°`、`360°`）对 `[Exposure step]` 100% 恒定表免疫（`shutter_angle_exposure_step_drift_events == 0`），并锁死全部 14 项硬件安全红线探针。

### Phase 253 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 253 Stage 48（48/48 里程碑）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_lock_op_parts_audio_timing_exp_step_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_lock_op_parts_audio_timing_exp_step_coemulator.py --self-test --json

# 2. 全板 48 阶段（Stage 1..48, 48/48 里程碑）统一校验（支持 --include-stage48 与 --skip-phase253）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage48 --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 253 双模 66 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_lock_op_parts_audio_timing_exp_step_coemulator.py' -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_lock_op_parts_audio_timing_exp_step_coemulator.py' -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 257：Stage 49（`49/49` 里程碑）真实硬件主线 — Wave-39 `[Display Quality]` `Standard`/`High` 省电工作台护栏与 `[Setup]` 跨重置持久化、`[Bluetooth Rmt Ctrl]` 红外 `SIRCS` 互斥锁与 3 向 `Reset Network Set.` 分流、以及 `[My Menu Setting]` / `[Display From My Menu]` 6 操作持久化与 Slot-1 `CAMSET01.DAT` `O_RDONLY` 保险箱往返 HIL 协同仿真器

[`realhw_display_quality_bt_rmt_mymenu_coemulator.py`](realhw_display_quality_bt_rmt_mymenu_coemulator.py) 作为 **Phase 257 Stage 49（`49/49` 里程碑，Schema `realhw_display_quality_bt_rmt_mymenu_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase257_realhw_display_quality_bt_rmt_mymenu_hil=True` / `include_stage49=True`，支持显式 `--include-stage49` 以及通过 `--skip-phase257` / `--skip-stage49` / `--no-include-stage49` 跳过；本地只读供体 49 阶段全板协同仿真 `< 3.0s`、洁净室模式 `< 1.0s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`tier0_battery_high_display_violations == 0`、`passive_tx_bytes_emitted == 0`、`bt_rmt_ir_lockout_violations == 0`、`slot1_mymenu_vault_mutation_bytes == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **15 份真实供体**：`string_english_f.uxc`（`373,820 B`：证实 `Display Quality` / `Standard` / `High` / `Monitor` / `Brightness` / `Manual` / `Battery` / `Bluetooth Rmt Ctrl` / `Bluetooth Function` / `Airplane Mode` / `IR Remote` / `My Menu` / `Display From My Menu` / `Add Item` / `Sort Item` / `Delete Item` / `Delete Page` / `Delete All` / `Save/Load Settings` / `Camera Settings Reset` / `Reset Network Set.` / `Initialize`）、`libInfraAdjMedia.so`、`libIMDB.so`、`libUsbBusPower.so`、`libInfraMscServer.so`、`libInfraMediaConfig.so` 及 FX6 `string_english.uxc`，并对 `appFw.so`（`DISPLAY` / `MONITOR` / `BLUETOOTH` / `CAMSET` / `SIRCS` / `MYMENU`）、`cpapp-b.bin`（`Display` / `Monitor` / `Remote` / `SIRCS`）、`libmpr.so` 与 `BK4` 执行 `<= 4096 B` 有界窗口只读核验；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 49A — `[Display Quality]` `Standard`/`High` 省电工作台护栏与 `[Setup]` 持久化 HIL**：
   - 协同仿真 `MENU -> Setup -> [Monitor] -> [Display Quality]`（`Standard` 出厂默认 / `High`）：验证其跨 **`[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整存活**，仅由 **`[Initialize]`** 复位至 `Standard`；精确建模 `[High]` 加速 `NP-FZ100`（`16.4 Wh`）实时取景功耗，并在机内电池 Tier-0 `pnflasha`/`cnflasha` 只读镜像转储工作台上自动钳位为 `[Display Quality] = Standard` + `[Monitor Brightness] = Manual(0)`（强行绕过返回 `EACCES = 13`，`tier0_battery_high_display_violations == 0`）。
3. **Sub-Model 49B — `[Bluetooth Rmt Ctrl]` 红外 `SIRCS` 互斥锁与 3 向 `Reset Network Set.` 分流 HIL**：
   - 协同仿真 `MENU -> Network -> [Bluetooth] -> [Bluetooth Rmt Ctrl]`（`Off` 默认 / `On`）：强制校验 `[Bluetooth Function] = On` + `[Airplane Mode] = Off` 射频前置条件（在零射频 `Airplane Mode = On` 工作台上自动抑制，`passive_tx_bytes_emitted == 0`）；当 `[Bluetooth Rmt Ctrl] = On` 时严格互斥封锁红外遥控器（`SIRCS`，强行注入返回 `EBUSY = 16`，`bt_rmt_ir_lockout_violations == 0`）；并验证 3 向重置分流：**跨 `[Camera Settings Reset]` 存活**，但由 **`[Reset Network Set.]` 与 `[Initialize]` 双双复位至 `Off`**（复位后恢复 `[Setup]` 下存活的红外 `SIRCS` 响应）。
4. **Sub-Model 49C & Redlines — `[My Menu Setting]` / `[Display From My Menu]` 6 操作持久化与 `CAMSET01.DAT` 往返 HIL**：
   - 协同仿真 `MENU -> My Menu -> [My Menu Setting]` 的全部 6 项子操作（`Add Item`、`Sort Item`、`Delete Item`、`Delete Page`、`Delete All`，支持最高 `6 页 x 6 项 = 36 项` 容量与第 37 项 `ENOSPC = 28` 拦截，以及 `[Display From My Menu]` `Off` 默认 / `On` 菜单首屏落地路由）；验证跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 双重持久化（仅 `[Initialize]` 清空复位），支持 `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` 完整还原 `My Menu` 与 `[Display From My Menu]`，同时拦截任何向 Slot-1 Tier-0 保险箱写入 `CAMSET01.DAT` 的行为（`EROFS = 30`，`slot1_mymenu_vault_mutation_bytes == 0`），并锁死全部 14 项硬件安全红线探针。

### Phase 257 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 257 Stage 49（49/49 里程碑）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_display_quality_bt_rmt_mymenu_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_display_quality_bt_rmt_mymenu_coemulator.py --self-test --json

# 2. 全板 49 阶段（Stage 1..49, 49/49 里程碑）统一校验（支持 --include-stage49 与 --skip-phase257）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage49 --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 257 双模 66 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_display_quality_bt_rmt_mymenu_coemulator.py' -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_display_quality_bt_rmt_mymenu_coemulator.py' -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 258：Stage 50（`50/50` 大里程碑 / Grand Milestone）真实硬件主线 — Wave-40 `[Different Set for Still/Mv]` 8 项非对称跃迁与 `Ver. 7.02` `[Shutter Angle]` 独立覆盖、`[Custom Key/Dial Set.]` 3 域键位与 `ISO/EI` 自适应及 Slot-1 `CAMSET01.DAT` `O_RDONLY` 保险箱往返、以及 `[Remain Shoot Display]` 连拍缓存边界与无 EVF `ILME-FX3` 监视拓扑护栏 HIL 协同仿真器

[`realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py`](realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py) 作为 **Phase 258 Stage 50（`50/50` 大里程碑，Schema `realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase258_realhw_diff_set_still_mv_custom_key_remain_shoot_hil=True` / `include_stage50=True`，支持显式 `--include-stage50` 以及通过 `--skip-phase258` / `--skip-stage50` / `--no-include-stage50` 跳过；本地只读供体 50 阶段全板协同仿真 `< 3.5s`、洁净室模式 `< 1.5s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`diff_set_transition_corruption_events == 0`、`shutter_angle_common_bleed_events == 0`、`slot1_custom_key_vault_mutation_bytes == 0`、`fx3_has_builtin_evf == False`、`evf_finder_monitor_spoof_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **15 份真实供体**：`string_english_f.uxc`（`373,820 B`：证实 `Different Set for Still/Mv` / 全部 8 项 `Aperture`、`Shutter Speed`、`ISO`、`Exposure Comp.`、`Metering Mode`、`White Balance`、`Picture Profile`、`Focus Mode` / `Shutter Mode` / `Angle` / `Custom Key/Dial Set.` / `ISO/EI` / `Control Wheel` / `Follow Custom` / `My Dial` / `Recall Custom hold` / `Cine EI` / `Remain Shoot Display` / `Not Displayed` / `Always Display` / `Shoot-Only Display` / `Save/Load Settings` / `Camera Settings Reset` / `Reset Network Set.` / `Initialize`）、`libInfraAdjMedia.so`、`libIMDB.so`、`libUsbBusPower.so`、`libInfraMscServer.so`、`libInfraMediaConfig.so` 及 FX6 `string_english.uxc`，并对 `appFw.so`（`SHUTTER` / `APERTURE` / `CUSTOM` / `DIAL` / `CAMSET` / `REMAIN` / `MONITOR` / `RESET`）、`cpapp-b.bin`（`Shutter` / `Custom` / `Dial` / `Display` / `Monitor` / `Initialize`）、`libmpr.so` 与 `BK4` 执行 `<= 4096 B` 有界窗口只读核验；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 50A — `[Different Set for Still/Mv]` 8 项非对称状态跃迁与 `Ver. 7.02` `[Shutter Angle]` 独立覆盖 HIL**：
   - 协同仿真 `MENU -> Setup -> [Operation Customize] -> [Different Set for Still/Mv]` 精确 8 项（`Aperture`、`Shutter Speed`、`ISO`、`Exposure Comp.`、`Metering Mode`、`White Balance`、`Picture Profile`、`Focus Mode`），跨 **`[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整存活**，仅由 **`[Initialize]`** 恢复为未勾选出厂默认；精确执行 `Common -> Separate`（复制当前值至照片与视频寄存器，**唯独 `Custom White Balance` 保持照片专属**）与 `Separate -> Common`（将标准项复位为初始出厂默认，**唯独 `Aperture`、`Shutter Speed` 与 `Custom White Balance` 保留照片端设定值**，`diff_set_transition_corruption_events == 0`）；同时验证 `Ver. 7.02`（`Ver. 6.00+`）`[Shutter Mode] = [Angle]` 覆盖规则：即便 `Shutter Speed` 未勾选（设为 Common），照片快门速度与视频快门角度依然独立运行互不串写（`shutter_angle_common_bleed_events == 0`）。
3. **Sub-Model 50B — `[Custom Key/Dial Set.]` 3 域键位、`ISO/EI` 自适应与 Slot-1 `CAMSET01.DAT` `O_RDONLY` 往返 HIL**：
   - 协同仿真 `MENU -> Setup -> [Operation Customize] -> [Custom Key/Dial Set.]`（`Still` / `Movie` / `Playback` 三域键位、电影机线三拨轮出厂默认 `Front dial=Aperture`、`Rear dial=ISO/EI` 在 `Off`/`Flexible ISO` 与 `Cine EI`/`Cine EI Quick` 间自动切换 `ISO` 与 `Exposure Index (EI)`、`Control Wheel=Shutter Speed`，以及视频 `[Follow Custom]` 继承、`[My Dial 1..3]` 临时拨轮交换与 `[Recall Custom hold 1..3]`）；验证跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 持久存活（仅 `[Initialize]` 复位），支持 `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` 无损还原，并拦截向 Slot-1 Tier-0 保险箱写入 `CAMSET01.DAT` 的行为（`EROFS = 30`，`slot1_custom_key_vault_mutation_bytes == 0`）。
4. **Sub-Model 50C & Redlines — `[Remain Shoot Display]` 连拍缓存边界与无 EVF `ILME-FX3` 监视拓扑护栏 HIL**：
   - 协同仿真 `MENU -> Setup -> [Display Option] -> [Remain Shoot Display]`（`Not Displayed` 默认 / `Always Display` / `Shoot-Only Display`），严格限定仅显示照片连拍缓存余量（`displays_movie_card_remaining_time == False`）且跨双重重置存活；同时硬锁 `ILME-FX3`（`ilc/2210`）无内置 EVF、无 `[Finder/Monitor]` 眼控切换的硬件拓扑边界（`fx3_has_builtin_evf == False`，伪造 EVF / `Finder/Monitor` 触发 `EOPNOTSUPP = 95`，`evf_finder_monitor_spoof_events == 0`），并锁死全部 14 项硬件安全红线探针。

### Phase 258 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 258 Stage 50（50/50 大里程碑）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py --self-test --json

# 2. 全板 50 阶段（Stage 1..50, 50/50 大里程碑）统一校验（支持 --include-stage50 与 --skip-phase258）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage50 --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 258 双模 68 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py' -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_diff_set_still_mv_custom_key_remain_shoot_coemulator.py' -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 262：Stage 51（`51/51`）真实硬件主线 — Wave-41 `[Auto Slow Shutter]` 6 项禁能互锁与 `Ver. 7.02` `[Shutter Angle]` 严格互斥、`[HDMI Output Settings]` `REC Control` <- `Time Code Output` 前置门控与 `4ch Audio Output` + Slot-1 保险箱护栏、以及 `[Lens Compensation]` -> `[Breathing Comp.]` 视频专属兼容镜头裁切与 `RAW` / `240p` 锁定 HIL 协同仿真器

[`realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py`](realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py) 作为 **Phase 262 Stage 51（`51/51`，Schema `realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase262_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_hil=True` / `include_stage51=True`，支持显式 `--include-stage51` 以及通过 `--skip-phase262` / `--skip-stage51` / `--no-include-stage51` 跳过；本地只读供体 51 阶段全板协同仿真 `< 3.5s`、洁净室模式 `< 1.5s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`auto_slow_shutter_lockout_bypass_events == 0`、`auto_slow_shutter_angle_overlap_events == 0`、`hdmi_rec_ctrl_without_tc_violations == 0`、`slot1_hdmi_rec_vault_mutation_bytes == 0`、`breathing_comp_raw_or_240p_bypass_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模只读供体审计（`LOCAL_DONOR_O_RDONLY` `<= 4096 B` 有界读取 `< 0.02s` 冷启动 + 进程级缓存 + `CLEAN_ROOM_SYNTHETIC` 回退）**：
   - 核验 FX3 `7.02` 与 FX6 `6.01` 的 **15 份真实供体**：`string_english_f.uxc`（`373,820 B`：证实 `Auto Slow Shutter` / `Exposure` / `Shutter Mode` / `Angle` / `Speed` / `Flexible Exp. Mode` / `Log Shooting` / `Cine EI Quick` / `Cine EI` / `ISO AUTO` / `HDMI Output Settings` / `REC Control` / `Time Code Output` / `4ch Audio Output` / `CH1/CH2` / `CH3/CH4` / `Rec. Media dur HDMI Output` / `Proxy Recording` / `RAW Output` / `Lens Compensation` / `Breathing Comp.` / `Camera Settings Reset` / `Reset Network Set.` / `Initialize`）、`libInfraAdjMedia.so`、`libIMDB.so`、`libUsbBusPower.so`、`libInfraMscServer.so`、`libInfraMediaConfig.so` 及 FX6 `string_english.uxc`，并对 `appFw.so`（`SHUTTER` / `HDMI` / `AUDIO` / `TIMECODE` / `BREATH` / `LENS` / `PROXY` / `RESET`）、`cpapp-b.bin`（`Shutter` / `HDMI` / `Audio` / `Timecode` / `Lens` / `Breathing` / `Reset` / `Initialize`）、`libmpr.so` 与 `BK4` 执行 `<= 4096 B` 有界窗口只读核验；当 `FX3_FX6_FORCE_CLEAN_ROOM=1` 或供体缺席时自动切换确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 51A — `[Auto Slow Shutter]` 6 项精确禁能互锁与 `Ver. 7.02` `[Shutter Angle]` 严格互斥 HIL**：
   - 协同仿真 `MENU -> Exposure/Color -> [Exposure] -> [Auto Slow Shutter]`（`On` 出厂默认 / `Off`，受 `[Camera Settings Reset]` 与 `[Initialize]` 复位、不受 `[Reset Network Set.]` 影响），验证索尼官方全部 6 项禁能互锁条件（① `S&Q` 慢快动作、② `Shutter Priority` 快门优先、③ `Manual Exposure` 手动曝光、④ `[ISO] != [ISO AUTO]`、⑤ `[Flexible Exp. Mode]` 手动快门、⑥ `[Log Shooting] = Cine EI Quick` / `Cine EI`；`auto_slow_shutter_lockout_bypass_events == 0`），并穷举 `768` 组曝光状态矩阵证明其与 `Ver. 7.02`（`Ver. 6.00+`）`[Shutter Mode] = [Angle]` 严格互斥、绝不同时主导曝光时间（`auto_slow_shutter_angle_overlap_events == 0`）。
3. **Sub-Model 51B — `[HDMI Output Settings]` `REC Control` <- `Time Code Output` 前置门控、`4ch Audio Output` 与 Slot-1 保险箱护栏 HIL**：
   - 协同仿真 `MENU -> Setup -> [External Output] -> [HDMI Output Settings]`，跨 **`[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整存活**（仅由 `[Initialize]` 恢复出厂默认）；强制 `[REC Control]`（`Off` 默认 / `On`）必须以 `[Time Code Output] = [On]` 为前置硬件条件（`hdmi_rec_ctrl_without_tc_violations == 0`），验证 `[4ch Audio Output]`（`CH1/CH2` 默认 vs `CH3/CH4` MI 热靴路由）与 `[Rec. Media dur HDMI Output]`（`Off` 时抑制机内 Slot-1/Slot-2 素材及 `[Proxy Recording]` 写入，且拦截向 Slot-1 Tier-0 恢复保险箱的写操作 `EROFS = 30`，`slot1_hdmi_rec_vault_mutation_bytes == 0`）。
4. **Sub-Model 51C & Redlines — `[Lens Compensation]` -> `[Breathing Comp.]` 视频专属兼容镜头裁切与 `RAW` / `240p` 锁定 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`（`Off` 默认 / `On`，`Ver. 3.00+`，受 `[Camera Settings Reset]` 复位、跨 `[Reset Network Set.]` 存活），严格限定仅对视频模式且装载呼吸补偿兼容索尼 E 卡口镜头（如 `SEL2470GM2`、`SEL50F12GM`、`SELP1635G`、`SEL70200GM2`）施加轻微视角裁切（照片模式与非兼容镜头保持 `1.0x` 无裁切），并在 `4264x2408` 16-bit 线性 HDMI `RAW Output` 及 `S&Q` `239.76p` / `200p` 下强制禁能锁定（`breathing_comp_raw_or_240p_bypass_events == 0`），同时锁死全部 15 项硬件安全红线探针。

### Phase 262 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 262 Stage 51（51/51）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py --self-test --json

# 2. 全板 51 阶段（Stage 1..51, 51/51）统一校验（支持 --include-stage51 与 --skip-phase262）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage51 --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 262 双模 66 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py' -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_auto_slow_shutter_hdmi_reccontrol_breathing_coemulator.py' -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 267：Stage 52（`52/52`）真实硬件主线 — Wave-42 `[APS-C S35 Shooting]` `12.1 MP` `4K` / `HDMI RAW` 硬锁定与 `Clear Image Zoom` 严格区分、BIONZ XR `[Face/Eye AF]` 4 项菜单与独立 AI 协处理器伪造主体拒绝及纯净外录 HDMI 框隔离 + `[Face Memory]` 跨相机重置留存、以及 `[Version]` 只读核验、`Airplane Mode = On` 零射频红点抑制与 `BODYDATA.DAT` 刷写硬阻断 HIL 协同仿真器

[`realhw_apsc_s35_face_eye_af_version_coemulator.py`](realhw_apsc_s35_face_eye_af_version_coemulator.py) 作为 **Phase 267 Stage 52（`52/52`，Schema `realhw_apsc_s35_face_eye_af_version_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase267_realhw_apsc_s35_face_eye_af_version_hil=True` / `include_stage52=True` / `stage52_realhw_apsc_s35_face_eye_af_version_hil=True`，支持显式 `--include-stage52` 以及通过 `--skip-phase267` / `--skip-stage52` / `--no-include-stage52` 跳过；本地只读供体 52 阶段全板协同仿真 `< 3.5s`、洁净室模式 `< 1.5s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、**`bodydata_update_execution_blocked == True`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`apsc_s35_4k_or_raw_bypass_events == 0`、`ai_coprocessor_subject_spoof_events == 0`、`hdmi_clean_feed_eye_frame_baked_pixels == 0`、`face_memory_camera_reset_wipe_events == 0`、`passive_tx_bytes_emitted == 0`、`bodydata_flash_execution_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模 18 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 严格通过 `os.O_RDONLY` 核验 FX3 `Ver. 7.02` 与 FX6 `Ver. 6.01` 的 **18 份真实供体**（精确锁定字节数与完整 64 位 SHA-256）：新增 `libInfraGetVersion.so`（`10,144 B`：`InfraGetVersion` / `InfraGetVersionLens`）、`libupdatermedia.so`（`10,144 B`：`UDTR_MEDIA` / `udtr_get_media_path`）与 `libupdaterufp.so`（`22,768 B`：`/BODYDATA.DAT` / `LENSDATA.DAT` / `/dev/nflasha1` / `udtr_write_firm_from_media`），联合 `string_english_f.uxc`（`373,820 B`：`APS-C/Super 35mm` / `Clear Image Zoom` / `Face/Eye AF` / `Face/Eye Priority in AF` / `Face/Eye Subject` / `Right/Left Eye Select` / `Face/Eye Frame Display` / `Regist. Faces Priority` / `Face Memory` / `HDMI Info. Display` / `Version` / `Airplane Mode`）、`appFw.so`、`cpapp-b.bin`、`libmpr.so` 与 `BK4`；同时支持 `FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双环境变量触发确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 52A — `[APS-C S35 Shooting]` `12.1 MP` `4K` / `HDMI RAW` 硬锁定与 `Clear Image Zoom` 严格区分 HIL**：
   - 协同仿真 `MENU -> Shooting -> [Image Quality/Rec] -> [APS-C S35 Shooting]`（`Auto` 出厂默认 / `On` / `Off`，受 `[Camera Settings Reset]` 与 `[Initialize]` 复位、跨 `[Reset Network Set.]` 存活）：因 `ILME-FX3` 全画幅传感器为 `12.1 MP`（`4240 × 2832`），`1.5×` APS-C / Super 35mm 子窗口（`2560 × 1440` 16:9）不具备原生 `3840 × 2160` 像素，故在全部 `4K` 格式（`XAVC HS 4K`、`XAVC S 4K`、`XAVC S-I 4K`、`DCI 4K`）及 `4264 × 2408` `HDMI RAW Output` 下**强制硬锁定 `Off` / 不可选**（`apsc_s35_4k_or_raw_bypass_events == 0`），仅在 `HD`（`XAVC S HD` / `XAVC S-I HD`）与静态照片（`~5.1 MP` `2768 × 1848`）下生效，并与 `4K` 下最高 `1.5×` 的 BIONZ XR `Clear Image Zoom` 清晰缩放严格区分。
3. **Sub-Model 52B — BIONZ XR `[Face/Eye AF]` 4 项菜单、AI 协处理器伪造拒绝、纯净 HDMI 框隔离与 `[Face Memory]` 持久化 HIL**：
   - 协同仿真 `MENU -> Focus -> [Face/Eye AF]`（`Face/Eye Priority in AF`、`Subject Recognition in AF` `Human`/`Animal`、`Right/Left Eye Select` `Auto`/`Right Eye`/`Left Eye`、`Face/Eye Frame Display` `On`/`Off`）与 `[Registered Faces Priority]`；严格拒绝 `ILME-FX2` / `ZV-E1` 独立 AI 协处理器伪造主体（`Bird`、`Insect`、`Car/Train`、`Airplane`；`EOPNOTSUPP = 95`，`ai_coprocessor_subject_spoof_events == 0`）；强制当 `HDMI Info. Display = Off`（或 `HDMI RAW Output = On`）时人脸/眼部对焦框仅在机身 LCD 渲染、**绝不烧录进纯净外录 HDMI 画面**（`hdmi_clean_feed_eye_frame_baked_pixels == 0`）；并验证 `[Face Memory]` 跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整留存，仅由 `[Delete]` 或 `[Initialize]` 清空。
4. **Sub-Model 52C & Redlines — `[Version]` 只读核验、`Airplane Mode = On` 零射频徽标抑制与 `BODYDATA.DAT` 刷写硬阻断 HIL**：
   - 协同仿真 `MENU -> Setup -> [Setup Option] -> [Version]` 只读展示机身 `ILME-FX3 Ver. 7.02` 与电子 E 卡口镜头固件版本（`flash_partitions_touched == 0`）；在 `Airplane Mode = On` 零射频台架下抑制 Creators' App 远程升级红点提醒（`passive_tx_bytes_emitted == 0`）；并无条件硬阻断任何 `[Version Update]` / `BODYDATA.DAT` / `LENSDATA.DAT` 卡槽刷写请求（`EROFS = 30`，`bodydata_update_execution_blocked == True`，`physical_device_writes == 0`，`emmc_corruptions == 0`），同时锁死全部 16 项硬件安全红线探针。

### Phase 267 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 267 Stage 52（52/52）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_apsc_s35_face_eye_af_version_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_apsc_s35_face_eye_af_version_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_apsc_s35_face_eye_af_version_coemulator.py --self-test --json

# 2. 全板 52 阶段（Stage 1..52, 52/52）统一校验（支持 --include-stage52 与 --skip-phase267）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage52 --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 267 双模 70 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_apsc_s35_face_eye_af_version_coemulator.py' -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_realhw_apsc_s35_face_eye_af_version_coemulator.py' -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 270（`270th` Milestone）：Stage 53（`53/53`）真实硬件主线 — Wave-43 `[Release w/o Card]` 静态照片专属作用域 vs 视频内录门控与 `[Release w/o Lens]`（`e_nd_actuator_tx_count == 0` 零 E 卡口镜头通信）、`Ver. 7.02`（`ilc/2210`）精确 5 项 `[Audio Recording]` vs `Ver. 1.x`（`ilc/2035`）`[Audio Level Display]` 伪造拦截与 `[DISP (Screen Disp) Set]` 音频表隔离、以及 `[Copyright Info]` `<= 46` 字符静态 EXIF 卫生与洁净室 PII 归零 HIL 协同仿真器

[`realhw_release_wo_card_audio_meter_copyright_coemulator.py`](realhw_release_wo_card_audio_meter_copyright_coemulator.py) 作为 **Phase 270（第 270 阶段里程碑）Stage 53（`53/53`，Schema `realhw_release_wo_card_audio_meter_copyright_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase270_realhw_release_wo_card_audio_meter_copyright_hil=True` / `include_stage53=True` / `stage53_realhw_release_wo_card_audio_meter_copyright_hil=True`，支持显式 `--include-stage53` 以及通过 `--skip-phase270` / `--skip-stage53` / `--no-include-stage53` 跳过；本地只读供体 53 阶段全板协同仿真 `< 4.0s`、洁净室模式 `< 1.5s`），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`fx3_has_builtin_end_filter == False`、`e_nd_actuator_tx_count == 0`、`cardless_unrecorded_production_violations == 0`、`legacy_v1_audio_level_menu_spoof_events == 0`、`hdmi_clean_feed_audio_meter_baked_pixels == 0`、`photographer_copyright_pii_leaked_bytes == 0`、`slot1_copyright_vault_mutation_bytes == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模 18 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 严格通过 `os.O_RDONLY` 核验 FX3 `Ver. 7.02` 与 FX6 `Ver. 6.01` 的 **18 份真实供体**（精确锁定字节数与完整 64 位 SHA-256 / 4096B 头部哈希）：`libInfraLensCommunicator.so`、`libInfraMediaDetect.so`、`libInfraMetaSupplier.so`、`libInfraIPTC.so`（`64,256 B`）、`libInfraHotshoe.so`、`libSaveLoadSettings.so`、`libInfraMediaConfig.so`、`libInfraAdjMedia.so`、`string_english_f.uxc`（`373,820 B`：证实 `Release w/o Card` / `Release w/o Lens` / `Audio Recording` / `Audio Rec Level` / `Audio Out Timing` / `Wind Noise Reduct.` / `Shoe Audio Set.` / `DISP` / `Copyright Info` / `Write Copyright Info` / `Set Photographer` / `Set Copyright` / `Disp. Copyright Info` / `Camera Settings Reset` / `Reset Network Set.` / `Initialize`）、FX6 `string_english.uxc`，以及对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 与 `BK4` 执行 `<= 4096 B` 有界窗口只读核验；同时支持 `FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双环境变量触发确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 53A — `[Release w/o Card]` 静态专属作用域 vs 视频内录门控 & `[Release w/o Lens]`（`e_nd_actuator_tx_count == 0`）HIL**：
   - 协同仿真 `MENU -> Shooting -> [Shutter/Silent] -> [Release w/o Card]`（`Enable` 出厂默认 / `Disable`，仅限 Still 静态照片作用域）与 `[Release w/o Lens]`（`Enable` 出厂默认 / `Disable`，覆盖 `Still` + `Movie` + `S&Q` 三域），跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 存活，仅由 `[Initialize]` 恢复 `Enable`；穷举 `768` 组工作流状态矩阵，验证 `CARDLESS_DIAGNOSTIC_BENCH`（`Enable` 允许零写卡静态快门测试，双槽为空时视频/S&Q 内录仍被阻断，外录 HDMI 受 `[Rec. Media dur HDMI Output]` 控制）vs `PRODUCTION_SHOOT`（`Disable` 防止漏插卡误拍，`cardless_unrecorded_production_violations == 0`），以及无镜头/PL 机械转接环下零 E 卡口 UART 通信与零电控 ND 通信（`fx3_has_builtin_end_filter == False`，`e_nd_actuator_tx_count == 0`）。
3. **Sub-Model 53B — `Ver. 2.00+`/`7.02`（`ilc/2210`）精确 5 项 `[Audio Recording]` vs `Ver. 1.x`（`ilc/2035`）伪造拒绝与 `DISP` 音频表 HIL**：
   - 强制锁定 `MENU -> Shooting -> [Audio Recording]` 精确 5 项（`Audio Recording` `On`/`Off`、`Audio Rec Level` `0..31`、`Audio Out Timing` `Live`/`Lip Sync`、`Wind Noise Reduct.` `On`/`Off`、`Shoe Audio Set.` `48kHz/24bit 2ch` / `48kHz/24bit 4ch` / `48kHz/16bit 2ch`），拒绝 `Ver. 1.x`（`ilc/2035`）遗留独立 `[Audio Level Display]` 菜单伪造（`EOPNOTSUPP = 95`，`legacy_v1_audio_level_menu_spoof_events == 0`）；同时建模 `Setup > Operation Customize > [DISP (Screen Disp) Set]` 2ch / 4ch MI 热靴音频电平表在 `S&Q` 或 `Audio Recording = Off` 下的自动抑制及纯洁外录 HDMI 零烧录隔离（`hdmi_clean_feed_audio_meter_baked_pixels == 0`）。
4. **Sub-Model 53C & Redlines — `[Copyright Info]` `<= 46` 字符静态 EXIF 卫生与洁净室 PII 归零 HIL**：
   - 协同仿真 `MENU -> Shooting -> [File] -> [Copyright Info]`（`Write Copyright Info` `Off` 默认 / `On`、`Set Photographer` `<= 46` 字符、`Set Copyright` `<= 46` 字符、`Disp. Copyright Info` 只读弹窗），强制 `<= 46` 字符可打印 ASCII 边界（47 字符与控制字符返回 `EINVAL = 22`）、仅写入 Still JPEG/HEIF EXIF（绝不篡改 `XAVC` / `HDMI RAW` 视频流或 Slot-1 Tier-0 恢复保险箱 `EROFS = 30`）、`[Camera Settings Reset]` 保留字串同时将写入开关复位为 `Off` vs `[Initialize]` 全清空、以及 `CLEAN_ROOM_SYNTHETIC` 下操作者 PII 归零（`photographer_copyright_pii_leaked_bytes == 0`、`camset_copyright_pii_leaked_bytes == 0`），并锁死全部 16 项硬件安全红线探针。

### Phase 270 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 270 Stage 53（53/53, 270th Milestone）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_release_wo_card_audio_meter_copyright_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_release_wo_card_audio_meter_copyright_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_release_wo_card_audio_meter_copyright_coemulator.py --self-test --json

# 2. 全板 53 阶段（Stage 1..53, 53/53）统一校验（支持 --include-stage53 与 --skip-phase270 / --skip-stage53）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage53 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 270 双模 70 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_release_wo_card_audio_meter_copyright_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_release_wo_card_audio_meter_copyright_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 274：Stage 54（`54/54`）真实硬件主线 — Wave-44 视频 `[File Settings]`（`Cam ID + Reel#` 与 `37` 字符 `Title Name`）vs 照片 `[File/Folder Settings]`（`3` 字符 `DSC` 前缀与 `Slot-1` 保险箱隔离）、`[Gamma Display Assist]`（`[Log Shooting]` 互锁与机内 LCD 专用纯净 HDMI）vs `[Display LUT]` / `[Select LUT]`（`3` 预设 + `User1..User16`）、以及 `[Auto Review]`（`Off` 电影默认）与 `[TC/UB]`（`6` 项防重置参数 + `[TC/UB Disp. Setting]`）HIL 协同仿真器

[`realhw_file_settings_gamma_assist_tcub_coemulator.py`](realhw_file_settings_gamma_assist_tcub_coemulator.py) 作为 **Phase 274 Stage 54（`54/54`，Schema `realhw_file_settings_gamma_assist_tcub_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase274_realhw_file_settings_gamma_assist_tcub_hil=True` / `include_stage54=True` / `stage54_realhw_file_settings_gamma_assist_tcub_hil=True`，支持显式 `--include-stage54` 以及通过 `--skip-phase274` / `--skip-stage54` / `--no-include-stage54` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`slot1_vault_folder_mutation_events == 0`、`title_name_37char_overflow_events == 0`、`still_prefix_leading_underscore_bypass_events == 0`、`gamma_assist_log_lockout_bypass_events == 0`、`hdmi_gamma_assist_baked_frames == 0`、`tcub_camera_settings_reset_wipe_events == 0`、`tc_24p_or_pal_df_violation_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模 18 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 严格通过 `os.O_RDONLY` 核验 FX3 `Ver. 7.02` 与 FX6 `Ver. 6.01` 的 **18 份真实供体**（精确锁定字节数与完整 64 位 SHA-256 / 4096B 头部哈希）：`libInfraMediaCommon.so`（`402,624 B`）、`libInfraMediaMount.so`（`65,392 B`）、`libInfraMediaDetect.so`（`98,224 B`）、`libInfraMetaSupplier.so`（`23,048 B`）、`libInfraIPTC.so`（`68,712 B`）、`libSaveLoadSettings.so`（`18,760 B`）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraAdjMedia.so`（`318,152 B`）、`string_english_f.uxc`（`373,820 B`：证实 `File Settings` / `File/Folder Settings` / `Cam ID + Reel#` / `Title Name Settings` / `Set File Name` / `Forced File Number Reset` / `Create New Folder` / `Gamma Display Assist` / `Gamma Disp. Assist Typ.` / `Display LUT` / `Select LUT` / `Auto Review` / `TC/UB` / `Time Code Preset` / `User Bit Preset` / `Time Code Format` / `Time Code Run` / `Time Code Make` / `User Bit Time Rec` / `TC/UB Disp. Setting` / `Camera Settings Reset` / `Initialize`）、FX6 `string_english.uxc`（`118,208 B`），以及对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 与 `BK4` 执行 `<= 4096 B` 有界窗口只读核验；同时支持 `FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双环境变量触发确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 54A — 视频 `[File Settings]`（`Cam ID + Reel#` & `37` 字符 `Title Name`）vs 照片 `[File/Folder Settings]`（`3` 字符 `DSC` 前缀 & `Slot-1` DCIM 恢复保险箱防火墙）HIL**：
   - 协同仿真视频 `MENU -> Shooting -> [File] -> [File Settings]`（`[File Number]` `Series`/`Reset` + `Series Counter Reset`，`5` 种 `[File Name Format]` 含 `Standard` `C0001.MP4`、`Cam ID + Reel#` `A..Z`/`001..999`/`C|L|R`、`Title`、`Date + Title`、`Title + Date`，`[Title Name Settings]` `1..37` 字符 `"C"` 默认，不可变 `PRIVATE/M4ROOT/CLIP` 路径 `EOPNOTSUPP = 95`）与照片 `MENU -> Shooting -> [File] -> [File/Folder Settings]`（`[File Number]` `Series`/`Reset` + `Forced File Number Reset`，`[Set File Name]` 精确 `3` 字符 `A-Z/0-9/_` `"DSC"` 默认且硬拒绝首字母 `_` `EINVAL = 22`，`[Folder Name]` `Standard Form` `100MSDCF` vs `Date Form` `100YMMDD`）。
   - 验证两套子菜单全部参数跨 `[Camera Settings Reset]` 完整存活（仅 `[Initialize]` 恢复默认），并在 `Slot 1` 持有只读 `CAMSET`/`BODYDATA.DAT` 恢复保险箱时以 `EROFS = 30` 硬阻断 `[Forced File Number Reset]` 与 `[Create New Folder]`（`slot1_vault_folder_mutation_events == 0`），同时允许 `Slot 2` 零写入仿真通过。
3. **Sub-Model 54B — `[Gamma Display Assist]`（`[Log Shooting]` 互锁 & 仅机内 LCD 纯净 HDMI）vs `[Display LUT]` / `[Select LUT]`（`3` 预设 + `User1..User16`）HIL**：
   - 协同仿真 `MENU -> Setup -> [Display Option] -> [Gamma Display Assist]`（`Off` 默认 / `On`）与 `[Gamma Disp. Assist Typ.]`（`Auto` / `S-Log3->709(800%)` / `HLG(BT.2020)` / `HLG(709)`）：一旦 `[Log Shooting]`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）!= `Off`，立即硬锁定 `[Gamma Display Assist] = Off`（越权绕过返回 `EOPNOTSUPP = 95`）；严格限定仅作用于机内 `LCD_LIVE_VIEW` 与 `INTERNAL_PLAYBACK`，绝不污染外接 `EXTERNAL_HDMI`（`hdmi_gamma_assist_baked_frames == 0`）。
   - 验证 `[Log Shooting] != Off` 期间监看转换由 `[Display LUT]`（`On` 默认 / `Off`）与 `[Select LUT]`（`3` 个内置预设 `S-Log3`、`s709`、`709(800%)` + `User1..User16` 共 `19` 项）接管，且 `[Setup]` 下三项监看配置跨 `[Camera Settings Reset]` 完整留存。
4. **Sub-Model 54C & Redlines — `[Auto Review]`（`Off` 电影默认）与 `[TC/UB]`（`6` 项防重置参数 + `[TC/UB Disp. Setting]`）HIL**：
   - 协同仿真 `MENU -> Setup -> [Display Option] -> [Auto Review]`（`ILME-FX3` 出厂默认 `Off` / `2 Sec` / `5 Sec` / `10 Sec`，仅限静止照片且视频/S&Q 保持 `0s`）与 `MENU -> Shooting -> [TC/UB]` 精确 **6** 项（`Time Code Preset` `00:00:00.00`、`User Bit Preset` `00 00 00 00`、`Time Code Format` `DF` vs `24.00p`/PAL `25p`/`50p` 强制 `NDF`、`Time Code Run` `Rec Run`/`Free Run`、`Time Code Make` `Preset`/`Regenerate`、`User Bit Time Rec` `Off`/`On`）+ `[TC/UB Disp. Setting]`（`TC` 默认 / `U-Bit`）：验证即便 `[TC/UB]` 位于 `Shooting` 菜单下，全部 `6` 项仍免疫 `[Camera Settings Reset]` 完整留存（强制抹除返回 `EOPNOTSUPP = 95`，仅 `[Initialize]` 清零重置），同时锁死全部 `16` 项硬件安全红线探针。

### Phase 274 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 274 Stage 54（54/54）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_file_settings_gamma_assist_tcub_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_file_settings_gamma_assist_tcub_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_file_settings_gamma_assist_tcub_coemulator.py --self-test --json

# 2. 全板 54 阶段（Stage 1..54, 54/54）统一校验（支持 --include-stage54 与 --skip-phase274 / --skip-stage54）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage54 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 274 双模 70 项单测 & 全量 fx3-vm 2,465 项单测（三模式 / 双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_file_settings_gamma_assist_tcub_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_file_settings_gamma_assist_tcub_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_file_settings_gamma_assist_tcub_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 278：Stage 55（`55/55`）真实硬件主线 — Wave-45 `[Focus Assistant]`（`Focus Magnifier` / `Auto Magnifier in MF` / `Initial Focus Mag.` `x1.0` / `AF in Focus Mag.`）& `[Peaking Display]` / `[AF Illuminator]`、`[Area/Date/Time Setting]` 零射频隔断、以及 `[Video Light Mode]`（`Power Link` / MI 热靴 `5V <= 900 mA`）& `[HDMI Resolution]`（`Auto` / Log `1080p` 下变换）HIL 协同仿真器

[`realhw_focus_mag_datetime_videolight_hdmires_coemulator.py`](realhw_focus_mag_datetime_videolight_hdmires_coemulator.py) 作为 **Phase 278 Stage 55（`55/55`，Schema `realhw_focus_mag_datetime_videolight_hdmires_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase278_realhw_focus_mag_datetime_videolight_hdmires_hil=True` / `include_stage55=True` / `stage55_realhw_focus_mag_datetime_videolight_hdmires_hil=True`，支持显式 `--include-stage55` 以及通过 `--skip-phase278` / `--skip-stage55` / `--no-include-stage55` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`legacy_mf_assist_spoof_events == 0`、`hdmi_clean_feed_mag_or_peaking_leaked_pixels == 0`、`af_illuminator_movie_or_sq_fire_events == 0`、`legacy_date_time_setup_spoof_events == 0`、`passive_tx_bytes_emitted == 0`、`creators_app_rtc_sync_jump_events == 0`、`mishoe_5v_900ma_overcurrent_events == 0`、`hdmi_log_1080p_downshift_bypass_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模 18 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 严格通过 `os.O_RDONLY` 核验 FX3 `Ver. 7.02` 与 FX6 `Ver. 6.01` 的 **18 份真实供体**（精确锁定字节数与完整 64 位 SHA-256 / 4096B 头部哈希）：`libInfraAdjMedia.so`（`318,152 B`）、`libInfraAirplaneMode.so`（`14,488 B`）、`libSaveLoadSettings.so`（`18,760 B`）、`libBusPower.so`（`43,968 B`）、`libInfraMediaConfig.so`（`52,312 B`）、`libInfraMediaCommon.so`（`402,624 B`）、`libInfraBluetoothCore.so`（`267,592 B`）、`libWlanControlCommon.so`（`18,528 B`）、FX3 `string_english_f.uxc`（`373,820 B`：证实 `Auto Magnifier in MF` / `Focus Magnif. Time` / `Initial Focus Mag.` / `AF in Focus Mag.` / `Peaking Display` / `Peaking Level` / `Peaking Color` / `AF Illuminator` / `Area/Date/Time Setting` / `Location Info. Link` / `Auto Time Correction` / `Auto Area Adjustment` / `Airplane Mode` / `Video Light Mode` / `Power Link` / `REC Link` / `HDMI Resolution` / `2160p` / `1080p` / `Off(HDMI Only)` / `Camera Settings Reset` / `Initialize`）、FX6 `string_english.uxc`（`118,208 B`），以及对 `appFw.so`、`cpapp-b.bin`、`libmpr.so` 与 `BK4` 执行 `<= 4096 B` 有界窗口只读核验；同时支持 `FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双环境变量触发确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 55A — `[Focus Assistant]`、`[Peaking Display]` 与 `[AF Illuminator]`（仅限静态照片）HIL**：
   - 协同仿真 `MENU -> Focus -> [Focus Assistant]`：严格强制 `ilc/2210` 官方标题 `[Auto Magnifier in MF]`（`On` 默认，以 `EOPNOTSUPP = 95` 硬拒绝旧款 `"MF Assist"` 伪造）、`[Focus Magnifier]`（`Custom Button 5` 默认 + `Touch Operation = On` 时 MF/DMF 液晶屏双击触发）、`[Focus Magnif. Time]`（`No Limit` 默认 / `2 Sec` / `5 Sec`）、独立的 Still 与 Movie `[Initial Focus Mag.]` 寄存器（`x1.0` 默认 / `x4.0`）、Still 专属 `[AF in Focus Mag.]`（`On` 默认 / `Off`）、HDMI 纯净输出退出与 `RAW Output = On` 硬锁定放大输出（`hdmi_clean_feed_mag_or_peaking_leaked_pixels == 0`）。
   - 协同仿真 `[Peaking Display]`（`Off` 默认，`Mid` 级别默认 `High`/`Mid`/`Low`，`White` 颜色默认 `Red`/`Yellow`/`Blue`/`White`，仅限机内 LCD 绝不污染外接 HDMI）与 `[AF Illuminator]`（`Auto` 默认 / `Off`，**严格仅限 Still 静态照片 AF**，在 `Movie` / `S&Q` 域绝对零点亮，`af_illuminator_movie_or_sq_fire_events == 0`）。
3. **Sub-Model 55B — `[Area/Date/Time Setting]`（`Setup > Area/Date`）与零射频 Creators' App 同步隔断 HIL**：
   - 严格强制 `ilc/2210` 官方标题 `[Area/Date/Time Setting]`（以 `EOPNOTSUPP = 95` 硬拒绝旧款 `"Date/Time Setup"` 伪造），建模 `[Area Setting]`（初始未配置 `"—"`）、`[Daylight Savings]`（`Off` 默认 / `On`）、`[Date/Time]` 与 `[Date Format]`（`Y-M-D` / `M-D-Y` / `D-M-Y`）；验证其驻留 `[Setup]` 菜单下跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整存活，仅由 `[Initialize]` 或 RTC 后备电池耗尽触发清零重设。
   - 在零射频气隙台架（`[Airplane Mode] = [On]`，`passive_tx_bytes_emitted == 0`）下硬阻断 Creators' App `[Location Information Linkage]`（`[Auto Time Correction]` / `[Auto Area Adjustment]`）蓝牙/Wi-Fi 同步，保障 `H0..H3` 取证 RTC 时标绝不意外跳变（`creators_app_rtc_sync_jump_events == 0`）。
4. **Sub-Model 55C & Redlines — `[Video Light Mode]`（`Power Link` 默认 & MI 热靴 `5V <= 900 mA`）与 `[HDMI Resolution]`（`Auto` 默认 & Log `1080p` 下变换）HIL**：
   - 协同仿真 `MENU -> Setup -> [Video Light Mode]`（`Power Link` 默认 / `REC Link` / `REC Link & STBY` / `Auto`，跨 `[Camera Settings Reset]` 存活），叠加 MI 热靴 `5V <= 900 mA` 供电轨过流门控保护（`Gate G24` 对等，`> 900 mA` 返回 `EACCES = 13` 硬件关断，`mishoe_5v_900ma_overcurrent_events == 0`）。
   - 协同仿真 `MENU -> Setup -> [External Output] -> [HDMI Resolution]`（`Auto` 默认 / `2160p` / `1080p` / `1080i`，跨 `[Camera Settings Reset]` 存活，仅 `[Initialize]` 恢复 `Auto`）：建模 `[Log Shooting] != Off` 且正在机内录制时自动将外部 HDMI 下变换至 `1080p`（除非 `Rec. Media dur HDMI Output = Off(HDMI Only)`），强行绕过返回 `EOPNOTSUPP = 95`（`hdmi_log_1080p_downshift_bypass_events == 0`），同时锁死全部 `16` 项硬件安全红线探针。

### Phase 278 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 278 Stage 55（55/55）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_focus_mag_datetime_videolight_hdmires_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_focus_mag_datetime_videolight_hdmires_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_focus_mag_datetime_videolight_hdmires_coemulator.py --self-test --json

# 2. 全板 55 阶段（Stage 1..55, 55/55）统一校验（支持 --include-stage55 与 --skip-phase278 / --skip-stage55）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage55 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 278 三模式 72 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_focus_mag_datetime_videolight_hdmires_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_focus_mag_datetime_videolight_hdmires_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_focus_mag_datetime_videolight_hdmires_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 281 Stage 56（56/56）— 真实硬件 Wave-46：`[Power Save by Monitor]` 现实分裂（`appFw.so` 4 模式 vs `ILME-FX3` `ilc/2210` 2 项 `[Power Setting Option]`）& `[Power Save Start Time]` 9 禁用条件 HIL、`[Language]` `BK_LANG`（`0x02cf019c`）34-vs-29 机种差异 & Stage-B 4 语言 `.uxc`/`.ltt` 对等、`[Volume Settings]`（`0..15` 默认 `7`）/ `[4ch Audio Monitoring]`（`5` 路 vs HDMI `4ch Audio Output`）/ `[Delete confirm.]`（`"Cancel" first` + `Slot-1` 恢复保险库防火墙）协同仿真台架

[`realhw_power_save_monitor_language_volume_delete_coemulator.py`](realhw_power_save_monitor_language_volume_delete_coemulator.py) 作为 **Phase 281 Stage 56（`56/56`，Schema `realhw_power_save_monitor_language_volume_delete_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase281_realhw_power_save_monitor_language_volume_delete_hil=True` / `include_stage56=True` / `stage56_realhw_power_save_monitor_language_volume_delete_hil=True`，支持显式 `--include-stage56` 以及通过 `--skip-phase281` / `--skip-stage56` / `--no-include-stage56` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、**`fx3_ui_exposes_power_save_by_monitor == False`**、`power_save_monitor_spoof_events == 0`、`headless_hdmi_unexpected_sleep_events == 0`、`language_count_model_mismatch_events == 0`、`bk_lang_offset_mismatch_events == 0`、`xlr_h1_speaker_feedback_guard_violations == 0`、`four_ch_headphone_routing_violations == 0`、`slot1_vault_delete_events == 0`、**`slot1_format_hard_locked == True`**、`passive_tx_bytes_emitted == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模 18 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 严格通过 `os.O_RDONLY` 核验 FX3 `Ver. 7.02` 与 FX6 `Ver. 6.01` 的 **18 份真实供体**（精确锁定字节数、完整 64 位 SHA-256 / 4096B 头部哈希及 `BK_LANG` `pread` 值）：`libSaveLoadSettings.so`（`18,760 B`）、FX3 `string_*_f.uxc` 四语言包（`en_f=373,820 B`、`sc_f=322,652 B`、`tc_f=324,148 B`、`ja_f=447,840 B`；证实 `string_english_f.uxc` 含 `Power Save by Monitor` / `Both Linked` / `Open: Return` / `Close: Power Save` / `Does Not Link` / `4ch Audio Monitoring` / `CH1+3/CH2+4` / `"Cancel" first` / `"Delete" first`，而 `string_simplifiedchinese_f.uxc` 实测使用 `"二者均连接"` 并在全包中零命中 `"Open: On/Close: Off"`）、FX3 主 `.uxc` 四语言包（`165,740 B` / `149,064 B` / `151,908 B` / `208,564 B`）、FX6 `.uxc` 四语言包（`118,208 B` / `118,644 B` / `119,168 B` / `141,692 B`），以及对 `FX3 appFw.so`（`79,015,712 B`）、`FX6 appFw.so`（`50,520,424 B`）、`FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，`0x90ff0` 4B LE `= 0`）、`CX95898_NTSC.bin`（`2,253,333 B`，`0x89242` `1B = 0x00`）与 `CX95899_CN1.bin`（`2,253,333 B`，`0x89242` `1B = 0x19`）执行 `<= 4096 B` 有界窗口只读核验；同时支持 `FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双环境变量触发确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 56A — `[Power Save by Monitor]` 现实分裂与 `[Power Save Start Time]` 9 禁用条件 HIL**：
   - 精确建模官方 `ILME-FX3 Ver. 7.02` (`ilc/2210`) `(Setup) -> [Power Setting Option]` **仅暴露 2 项**：`[Power Save Start Time]`（`Off` / `30 Min` / `5 Min` 默认 / `2 Min` / `1 Min` / `10 Sec`）与 `[Auto Power OFF Temp.]`（`Standard` 默认 / `High`）；库存 `FX3` / `FX3A` / `FX6` UI 不暴露 `[Power Save by Monitor]`（`fx3_ui_exposes_power_save_by_monitor == False`），侧翻屏内折（`Closed_Inward`）完全不触发休眠且以 `EOPNOTSUPP = 95` 硬拒绝任何伪造的 UI 变更或 `"Open: On/Close: Off"` 虚假字符串。
   - 同时对共享 `BIONZ XR` `appFw.so`（`BKID_APP_setting_monitor_power_linkage`）+ `string_*_f.uxc`（`0x60b9`）编译保留的精确 **4 模式**（`Both Linked` `0x6db5`、`Open: Return` `0x6db6`、`Close: Power Save` `0x60a8`、`Does Not Link` `0x6b2e`）建模同代侧翻屏机身（`ILME-FX2` / `ILCE-7M4` / `ZV-E1` / `ILCE-6700`）的无头 HDMI 休眠防护与 `ILCE-7M4 Ver. 6.00` 睡眠回归拦截，并完整验证全部 **9 项** `[Power Save Start Time]` 自动禁用条件（USB 供电、幻灯片播放、FTP 传输、动态影像录制、PC 连接、TV/HDMI 连接、`IR Remote Ctrl = On`、`Bluetooth Rmt Ctrl = On`、流媒体/Creators' Cloud 上传）及 `(Setup)` 跨 `[Camera Settings Reset]` 存活特性。
3. **Sub-Model 56B — `[Language]` `BK_LANG`（`0x02cf019c`）34-vs-29 机种差异与 Stage-B 4 语言 `.uxc`/`.ltt` 对等 HIL**：
   - 协同仿真 `MENU -> Setup -> [Area/Date] -> [Language]`：`ILME-FX3`（`34` 语种，`0x90ff0` 4B LE `= 0`）vs `ILME-FX6`（`29` 语种，`0x89242` 1B，`NTSC=0x00` vs `CN1=0x19`；FX6 对 FX3 独有第 30..34 语种返回 `EOPNOTSUPP = 95`），Stage-B 4 语言 `.uxc`/`.ltt` 切换矩阵（`en=0x00` `switchBank=0` `(4,4)`、`schinese=0x19` `switchBank=23` `(19,19)`、`tchinese=0x18` `switchBank=27` `(22,22)`、`japanese=0x01` `switchBank=1` `(12,12)`），开箱未设 `"—"` 提示，以及跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 完整存活、仅在 `[Initialize]` 时清零并重弹初始设定。
4. **Sub-Model 56C & Redlines — `[Volume Settings]`（`0..15`）、`[4ch Audio Monitoring]`（`5` 路）与 `[Delete confirm.]`（`"Cancel" first` + `Slot-1` 恢复保险库防火墙）HIL**：
   - 协同仿真 `[Volume Settings]`（`0..15`，出厂默认 `7`，`0xe8c9` 区别于 `[Audio signals]` `0x7af6`，`XLR-H1` 机顶话筒激活时对机内扬声器强制防啸叫钳位 `0` / `EACCES = 13` 阻断，并对齐 FX6 `BKID_APP_SETTING_MONITOR_VOLUME`）、`[4ch Audio Monitoring]` 全部 **5 路**监听路由（`CH1/CH2` `0x713b` 默认、`CH3/CH4` `0x6bf6`、`CH1+3/CH2+4` `0x6c2e`、`CH1/CH1` `0x6f9c`、`CH2/CH2` `0x7a26`；受 `3.5mm` 双声道耳机硬件边界约束并与 HDMI `[4ch Audio Output]` `0x6aa0` 解耦）。
   - 协同仿真 `[Delete confirm.]`（`"Cancel" first` 默认 `0xe724`/`0x6a5e` vs `"Delete" first` `0xe725`/`0x6e0a`）与 `[Delete pressing twice]`（`Off` 默认 `0x74db`）在 `(Playback)` 下跨 `[Camera Settings Reset]` 存活（仅 `[Initialize]` 还原），并激活硬 **Slot-1 恢复保险库防火墙**（`EROFS = 30`，`slot1_vault_delete_events == 0`，`slot1_format_hard_locked == True`）阻断 Slot 1 上全部单张/多张/文件夹/日期/连按删除及格式化，而 `Slot 2` 虚机草稿区保持零物理写（`physical_device_writes == 0`），同时锁死全部 `16` 项硬件安全红线探针。

### Phase 281 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 281 Stage 56（56/56）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_power_save_monitor_language_volume_delete_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_power_save_monitor_language_volume_delete_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_power_save_monitor_language_volume_delete_coemulator.py --self-test --json

# 2. 全板 56 阶段（Stage 1..56, 56/56）统一校验（支持 --include-stage56 与 --skip-phase281 / --skip-stage56）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage56 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 281 三模式 76 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_power_save_monitor_language_volume_delete_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_power_save_monitor_language_volume_delete_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_power_save_monitor_language_volume_delete_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 285 Stage 57（57/57）— 真实硬件 Wave-47：`[USB Connection Mode]` 4 模式 vs 休眠 `NOUVC` `[USB Streaming]` 分裂 & 数据物理隔离 USB PD、`[HDMI Info. Display]` 关屏/干净输出 & `1080` Log/`PPLUT` 钳位 vs `4K` `RAW`/`HDMI Only` 自动清屏覆写、`[Protect]` 4 范围 vs `[Format]` 抹除（`Slot-1` 双层硬件 SD `WP` + 防火墙）& `[Reset Network Set.]` 自动重启后复设 `[Airplane Mode] = [On]` 协同仿真台架

[`realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py`](realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py) 作为 **Phase 285 Stage 57（`57/57`，Schema `realhw_usb_mode_hdmi_info_protect_network_reset_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase285_realhw_usb_mode_hdmi_info_protect_network_reset_hil=True` / `include_stage57=True` / `stage57_realhw_usb_mode_hdmi_info_protect_network_reset_hil=True`，支持显式 `--include-stage57` 以及通过 `--skip-phase285` / `--skip-stage57` / `--no-include-stage57` 跳过），在严格保持 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、**`fx3_ui_exposes_native_usb_streaming == False`**、**`usb_f_uvc_insmod_at_fx3_boot == False`**、`fx3_native_uvc_spoof_events == 0`、`tier0_usb_data_enumeration_violations == 0`、`physical_usb_packets_emitted == 0`、`hdmi_osd_or_clamp_bypass_events == 0`、`hdmi_clean_feed_override_violations == 0`、`slot1_vault_format_or_delete_events == 0`、**`slot1_format_hard_locked == True`**、`post_reset_airplane_off_rf_leak_events == 0`、`passive_tx_bytes_emitted == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大核心闭环：

1. **高速双模 13 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` `< 0.2s` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 严格通过 `os.O_RDONLY` 核验 FX3 `Ver. 7.02` 与 FX6 `Ver. 6.01` 的 **13 份真实供体**（精确锁定字节数、完整 64 位 SHA-256 / 4096B 头部哈希及有界窗口）：FX3 `string_*_f.uxc` 4 语言全集（`en_f=373,820 B`、`sc_f=322,652 B`、`tc_f=324,148 B`、`ja_f=447,840 B`）、FX3 `string_english.uxc`（`165,740 B`）、FX3 `string_english_g.uxc`（`69,600 B`）、FX3 与 FX6 `usb_f_uvc.ko`（双机型同为 `78,840 B`）、FX6 `string_english.uxc`（`118,208 B`）与 `string_english_2.uxc`（`118,676 B`），以及 `FX3 appFw.so`（`79,015,712 B`：`BKID_APP_setting_usb_connection_method`、`USB_CONNECTION_METHOD_MASS_STRAGE`、`USB_CONNECTION_USB_STREAMING`、`BKID_APP_setting_hdmi_info_display`、`CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`、`FUNC_protect_*`、`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`、`FUNC_reset_network_settings`、`BKID_APP_is_shutdown_factor_network_reset`）、`FX3 BK4`（`2,229,740 B`）与 `FX6 appFw.so`（`50,520,424 B`：`BKID_APP_SETTING_USB_STREAMING_PROCAM`、`BKID_APP_SETTING_HDMI_INFO_DISPLAY`、`BKID_APP_SETTING_SDI_OUTPUT_DISPLAY`、`BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET`）；支持 `FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双环境变量触发确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 57A — `[USB Connection Mode]` 4 模式 vs 休眠 `NOUVC` `[USB Streaming]` 分裂与数据隔离 USB PD HIL**：
   - 精确建模 `ILME-FX3 Ver. 7.02` `(Setup) -> [USB] -> [USB Connection Mode]`（`_f.uxc` `0x69a2`）仅暴露 **4 模式**：`Sel. When Connect`（`0x7738` 出厂默认）、`MassStorage(MSC)`（`0x6c54`，`054C:0DA1`，内部标记 `USB_CONNECTION_METHOD_MASS_STRAGE`）、`MTP`（`0xe24b`，Slot 1）、`Remote Shoot (PC Remote)`（`0x60aa`/`0x7c6f`）；以 `EOPNOTSUPP = 95` 硬拒绝任何 FX3 原生 `[USB Streaming]` UVC/UAC 伪造切态，并与同供体 `ILME-FX6` `ProCam` UVC（`BKID_APP_SETTING_USB_STREAMING_PROCAM`，`usb_f_uvc.ko` `78,840 B`）形成清晰对比。
   - 同步建模 `[USB LUN Setting]`（`Multi` `0xe631` 默认 `2 LUN` vs `Single` `0x776d` `1 LUN`）、`[USB Power Supply]`（`On` `0x721e` 默认，仅限 Type-C 端口且须装入 `NP-FZ100` 电池）、`(Setup)` 跨 `[Camera Settings Reset]` 存活特性（仅 `[Initialize]` 恢复出厂），以及气隙 Tier-0 台架规则：**仅在 `D+/D-` 与 SuperSpeed 数据线物理切断（仅保留 `VBUS/CC` USB PD 供电）时放行**。
3. **Sub-Model 57B — `[HDMI Info. Display]` 关屏 vs 干净输出、`1080` Log/`PPLUT` 钳位与 `4K` `RAW`/`HDMI Only` 自动清屏覆写 HIL**：
   - 协同仿真 `[HDMI Info. Display]`（`On` `0xe07c` 默认输出 OSD + 黑屏关闭机背 LCD 与触控对焦 `CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`；`Off` `0xe297` 输出纯洁外录 HDMI 并保持 LCD/触控激活）；当机内录制（`Rec. Media dur HDMI Output = On`）叠合 `Log Shooting != Off` 或 `PPLUT1..4` 时强制将 HDMI 钳位至 `1080`（强绕过返回 `EOPNOTSUPP = 95`）；而当 `Off(HDMI Only)`（`0x6573`）或 `RAW Output = On`（`0x6e97`，`4264x2408`）激活时输出 `4K` 并**自动强制 `[HDMI Info. Display] = [Off]`**（`S&Q` 锁定 `Rec. Media = On` 与 `RAW Output = Off`），且验证 `(Setup)` 跨 `[Camera Settings Reset]` 存活与 `[Framing Settings (HDMI)]` 复位例外。
4. **Sub-Model 57C & Redlines — `[Protect]` 4 范围 vs `[Format]` 抹除（`Slot-1` 双层硬件 SD `WP` + 防火墙）与 `[Reset Network Set.]` 自动重启 + 复设 `[Airplane Mode] = [On]` HIL**：
   - 完整建模 `ILME-FX3` 全部 4 项 `[Protect]` 范围（`Single`/`Multiple Img.` `0xe2ca`、`All in this Folder` `0x6848`、`All with this date` `0x69f7`、`All Images in This Group` `0xe826`）在 `Slot 2` 虚机草稿区对 `[Delete]`/`[Delete pressing twice]` 返回 `EROFS = 30`，同时证明 **`[Format]`（`0xe449`/`0xe414`）会直接抹除受保护文件及 `M1..M4` 存储卡设置** —— 从而强制在 `Slot 1` 恢复保险库激活**双层防护**：硬件 SD `WP` 物理锁开关（`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`）+ 软件硬锁（`slot1_format_hard_locked == True`，`EROFS = 30`，`slot1_vault_format_or_delete_events == 0`）。
   - 协同仿真 `[Reset Network Set.]`（`FUNC_reset_network_settings`、`SETTING_RESET_NW`、`0x60d3`/`0x65d3`）清空 12 域 `(Network)` 凭据、完整保留 `(Shooting)`/`(Setup)`/`(Playback)` 与 `CAMSET`、触发强制自动重启（`BKID_APP_is_shutdown_factor_network_reset`）并将 `[Airplane Mode]` 复位至 `Off`，强迫台架规则要求**重启后立即复设 `[Airplane Mode] = [On]`（`0x6df9`）**以恢复零射频气隙姿态（否则 `EACCES = 13` 阻断，零泄漏），同时锁死全部 `16` 项硬件安全红线探针。

### Phase 285 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 285 Stage 57（57/57）自检
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py --self-test --json

# 2. 全板 57 阶段（Stage 1..57, 57/57）统一校验（支持 --include-stage57 与 --skip-phase285 / --skip-stage57）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage57 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 285 三模式 76 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_usb_mode_hdmi_info_protect_network_reset_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 289 Stage 58（58/58）— 真实硬件 Wave-48：`[Picture Profile]` `PP11`（`S-Cinetone`）开箱默认 / `[Creative Look]` & `DRO` 互斥锁 / `PP1..11` 内部参数跨复位持久化、`[White Balance]` 13 模式 & `Custom 1..3` `CAMSET` 隔离 / `Cine EI` 自动白平衡锁，与 `[Metering Mode]` 5 模式 / 测光点联动 & `CIZ` `[Multi]` 钳位协同仿真台架

[`realhw_pp_scinetone_creativelook_wb_metering_coemulator.py`](realhw_pp_scinetone_creativelook_wb_metering_coemulator.py) 作为 **Phase 289 Stage 58（`58/58`，Schema `realhw_pp_scinetone_creativelook_wb_metering_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase289_realhw_pp_scinetone_creativelook_wb_metering_hil=True` / `include_stage58=True` / `stage58_realhw_pp_scinetone_creativelook_wb_metering_hil=True`，支持显式 `--include-stage58` 以及 `--skip-phase289` / `--skip-stage58` / `--no-include-stage58` 跳过），在严格锁定 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`physical_usb_packets_emitted == 0`、`pp_creative_look_or_reset_wipe_misroute_events == 0`、`wb_cine_ei_auto_or_camset_custom_leak_events == 0`、`metering_spot_link_or_ciz_multi_bypass_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大闭环：

1. **高速双模 11 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` `< 0.2s` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 通过受界 `os.O_RDONLY`（`<= 4096 B`）核验 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 的 **11 份真实供体**：FX3 `string_*_f.uxc` 4 语种全集（`en_f=373,820 B`、`sc_f=322,652 B`、`tc_f=324,148 B`、`ja_f=447,840 B`）、FX3 `string_english.uxc`（`165,740 B`）、FX3 `string_english_g.uxc`（`69,600 B`）、FX6 `string_english.uxc`（`118,208 B`）与 `string_english_2.uxc`（`118,676 B`），以及 `FX3 appFw.so`（`79,015,712 B`）、`FX3 BK4`（`2,229,740 B`）与 `FX6 appFw.so`（`50,520,424 B`）；支持 `FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双环境变量触发确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 58A — `[Picture Profile]` `PP11`（`S-Cinetone`）开箱默认、`[Creative Look]` & `DRO` 锁定、`Log Shooting` 互斥与复位持久分裂 HIL**：
   - 精确建模 `ILME-FX3 Ver. 7.02` 出厂默认 `[Picture Profile] = PP11`（`Gamma: S-Cinetone`、`Color Mode: S-Cinetone`）同时覆盖 **Movie 与 Still**（`Different Set for Still/Mv` 默认不拆分），`PP7/8/9 = S-Log2/S-Log3`、`PP10 = HLG2 + BT.2020`、`PPLUT1..4`；对比 `ILME-FX6 Ver. 6.01` 的 `Base Look`（Custom 默认 `S-Cinetone`）+ `Scene File`。
   - 任意 `PP1..PP11` / `PPLUT1..4` 激活时，`[Creative Look]`（10 预设 `ST..SE` + `Custom Look 1..6`、8 参数，其中 `Clarity` 在 Movie/`S&Q` 与连拍下锁定）硬锁 `'-'`（`EOPNOTSUPP = 95`），`[D-Range Optimizer]` 强制 `Off`；开启 `[Log Shooting]`（`Flexible ISO` / `Cine EI Quick` / `Cine EI`）同时硬锁三者并经 `[Display LUT]`（`s709`/`709(800%)`/`User1..16`）监看。
   - 关键复位边界：`[Camera Settings Reset]` 将当前选项恢复至 `PP11`，**但 `PP1..11` 内部自定义参数跨越 `[Camera Settings Reset]` 与 `[Initialize]` 全程存活**——仅逐档 `[Picture Profile] -> [Reset]` 可恢复出厂配方。
3. **Sub-Model 58B — `[White Balance]` 13 模式、`[Priority Set in AWB]` / `[Shutter AWB Lock]`、`Cine EI` 锁定与 `Custom 1..3` 存卡隔离 HIL**：
   - 建模全部 13 类 FX3 WB 模式（15 项子模式含 4 档荧光灯、`Flash` 仅 Still 生效 / Movie 与 `S&Q` `EOPNOTSUPP = 95`、`C.Temp./Filter` `2500K..9900K` + `G7..M7`/`A7..B7`、`Custom 1..3`），对比 FX6 机身 `WHT BAL` `Memory B / A / Preset` + `ATW`。
   - `Cine EI` / `Cine EI Quick` 下硬锁 `Auto` 与 `Underwater Auto` WB（`EOPNOTSUPP = 95`）；`[Shutter AWB Lock]` 仅 Still + Auto/UW Auto 生效；`Custom 1..3` 注册值**跨 `[Camera Settings Reset]` 存活**（仅 `[Initialize]` 清空），且**严禁写入 `CAMSET01..10.DAT`**，仅由 `M1..M4` 携带（`Slot 1` 恢复保险库 `EROFS = 30`）。
4. **Sub-Model 58C & Redlines — `[Metering Mode]` 5 模式、`[Spot Metering Point]` 联动、`Clear Image Zoom` `[Multi]` 钳位与 16 项红线 HIL**：
   - 建模全部 5 类 FX3 测光模式（含 `Spot: Standard / Large`）、`[Face Priority in Multi Metering]`、`[AEL w/ Shutter]` 与 `[Exposure Std. Adjust]`（对比 FX6 波形/斑马纹与 `Standard/Backlight/Spotlight`）。`Focus Point Link` 仅在 `Flexible Spot` / `Expand Spot` 联动否则退回 `Center`；当 `CIZ / Digital Zoom > 1.0x` 时强制钳位至 `[Multi]` + `Face Priority = Off`，退回 `1.0x` 后无损恢复，同时锁定全套 16 项安全与零写红线。

### Phase 289 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 289 Stage 58（58/58）自检
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_pp_scinetone_creativelook_wb_metering_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_pp_scinetone_creativelook_wb_metering_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_pp_scinetone_creativelook_wb_metering_coemulator.py --self-test --json

# 2. 全板 58 阶段（Stage 1..58, 58/58）统一校验（支持 --include-stage58 与 --skip-phase289 / --skip-stage58）
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage58 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 289 三模式 76 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_pp_scinetone_creativelook_wb_metering_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_pp_scinetone_creativelook_wb_metering_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_pp_scinetone_creativelook_wb_metering_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 293 Stage 59（59/59）— 真实硬件 Wave-49：`[Image Quality Settings]` Still `RAW`（`Compressed` / `Uncompressed` vs 休眠 `Lossless Comp` 门控）、`JPEG/HEIF Switch`（`JPEG / HEIF(4:2:0) / HEIF(4:2:2)` `10-bit` `.HIF`）& `[HLG Still Image]` `BT.2100` 接管、`[Color Space]` `AdobeRGB` `_DSC` 前缀 & `[Set File Name]` 首字符 `_` 禁令，以及 `[Shutter Type]` 精确 2 选（无 `Auto`）/ Electronic-Silent 5 锁 / NR / `10 fps` Drive Mode `Slot-1` 保险库协同仿真台架

[`realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py`](realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py) 作为 **Phase 293 Stage 59（`59/59`，Schema `realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase293_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil=True` / `include_stage59=True` / `stage59_realhw_raw_heif_colorspace_shuttertype_nr_drive_hil=True`，支持显式 `--include-stage59` 以及 `--skip-phase293` / `--skip-stage59` / `--no-include-stage59` 跳过），在严格锁定 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_nflasha_write_count == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`physical_usb_packets_emitted == 0`、`dormant_lossless_raw_exposed_events == 0`、`hlg_still_prerequisite_bypass_events == 0`、`color_space_leading_underscore_bypass_events == 0`、`shutter_type_auto_or_5lock_bypass_events == 0`、`slot1_vault_still_or_burst_write_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大闭环：

1. **高速双模 11 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` `< 0.2s` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 通过受界 `os.O_RDONLY`（`<= 4096 B`）核验 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 的 **11 份真实供体**：FX3 `string_*_f.uxc` 4 语种全集（`en_f=373,820 B`、`sc_f=322,652 B`、`tc_f=324,148 B`、`ja_f=447,840 B`）、FX3 `string_english.uxc`（`165,740 B`）、FX3 `string_english_g.uxc`（`69,600 B`）、FX6 `string_english.uxc`（`118,208 B`）与 `string_english_2.uxc`（`118,676 B`），以及 `FX3 appFw.so`（`79,015,712 B`）、`FX3 BK4`（`2,229,740 B`）与 `FX6 appFw.so`（`50,520,424 B`）；支持 `FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双环境变量触发确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 59A — Still `[Image Quality Settings]`（`RAW` `Compressed`/`Uncompressed` vs 休眠 `Lossless Comp` 门控、`JPEG/HEIF Switch` `10-bit` `.HIF` & `[HLG Still Image]` `BT.2100` 接管 vs Still-Less `ILME-FX6`）**：
   - 精确建模 `ILME-FX3 Ver. 7.02`（`12 MP IMX510`）仅暴露 `[Compressed]`（默认）与 `[Uncompressed]` 14-bit `.ARW`——`appFw.so` 中的休眠 `Lossless Comp` / `Lossless Comp (L)/(M)/(S)`（`_f.uxc` `0x6b56`）被门控拦截并返回 `EOPNOTSUPP = 95`，对照 `ILME-FX6 Ver. 6.01` 完全不存在 `DCIM`/`.ARW`/`.JPG`/`.HIF` 静态照片流水线（`still_pipeline_present = False`）。
   - `[HLG Still Image] = On` 强制前置：`HEIF(4:2:0)` 或 `HEIF(4:2:2)` 10-bit + `File Format = HEIF` 单选 + `P/A/S/M`（在 `JPEG`、`RAW`、`RAW & HEIF` 或 `iAuto` 下 `EOPNOTSUPP = 95`），同时硬锁 `Picture Profile` / `Creative Look` / `D-Range Optimizer` / `DRO Bracket`，覆盖色彩空间为 `BT.2100`（`BT.2020`），并路由 `Gamma Display Assist`（`Auto` / `HLG(BT.2020)`）。
3. **Sub-Model 59B — `[Color Space]`（`sRGB` 默认 vs `AdobeRGB` `_DSC` 前缀）与 `[Set File Name]` 首字符 `_` 禁令 HIL**：
   - `MENU -> Shooting -> [Image Quality/Rec] -> [Color Space]`：`sRGB` 生成 `DSC00001.JPG/.ARW`，切换 `AdobeRGB` 时系统自动在前缀首部插入 `_` 生成 `_DSC0001.JPG/.ARW`（DCF 2.0 `100MSDCF`）。
   - `[Set File Name]`（默认 `DSC`，跨 `[Camera Settings Reset]` 存活，仅 `[Initialize]` 恢复）允许 3 位字符（`A-Z0-9_`），**但严格禁止将 `_` 设为第 1 个字符**（`EINVAL = 22`）；在 `HEIF` 模式下 `[Color Space]` 被忽略（`HLG Still Image = Off` 为 `sRGB`，`On` 为 `BT.2100`）。
4. **Sub-Model 59C & Redlines — `[Shutter Type]` 精确 2 选（无 `Auto`）、Electronic/Silent 5 锁矩阵、NR、`10 fps` Drive Mode 与 `Slot-1` Tier-0 保险库防火墙 HIL**：
   - `ILME-FX3 Ver. 7.02` 仅暴露 **2 项** `[Shutter Type]`（`Mechanical Shutter` 默认 vs `Electronic Shutter`，不存在 `Auto`，请求 `Auto` 返回 `EINVAL = 22`），而 `ILME-FX6` 无机械快门（`mechanical_shutter_present = False`，请求机械快门返回 `EOPNOTSUPP = 95`）。
   - `Electronic Shutter`（及未通过 `Target Function` 覆写的 `Silent Mode = On`）强制锁定 5 项功能（`EOPNOTSUPP = 95`）：① `Flash`（`1/250 s` 全画幅闪光同步仅限机械快门）、② `Long Exposure NR`（`>= 1 s` 暗帧减除）、③ `e-Front Curtain Shut.`（默认 `On`，跨 `Camera Settings Reset` 存活）、④ `BULB`、⑤ `Anti-flicker Shoot.`。
   - 建模 `[High ISO NR]` 对 RAW `.ARW` 的免处理边界、11 态 `[Drive Mode]`（`Cont. Shooting: Hi+` 最高 `10 fps`，`Uncompressed RAW` 与闪光降至 `8 fps`，连拍 `>= 1000` 帧触发 `SLOW` 降速，`> F11` 锁 AF），并对只读 `Slot 1` 强制实施 fail-closed `EROFS = 30` / `EBUSY = 16` Tier-0 保险库写拦截与全套 16 项红线探针。

### Phase 293 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 293 Stage 59（59/59）自检
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py --self-test --json

# 2. 全板 59 阶段（Stage 1..59, 59/59）统一校验（支持 --include-stage59 与 --skip-phase293 / --skip-stage59）
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage59 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 293 三模式 >=76 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_raw_heif_colorspace_shuttertype_nr_drive_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 298 Stage 60（60/60 VM 阶段里程碑！）— 真实硬件 Wave-50：`[Focus Area]` 14 区 Still-vs-Movie 追踪与 `[AF Area Registration]`、机身 `W/T` `[Zoom Lever Speed]` vs 无摇杆 `XLR-H1`、`[ISO Range Limit]` / Still-Only `[ISO AUTO Min. SS]` vs `Cine EI` 与 `[Flash Mode]` 机械快门门控 vs `[Video Light Mode]` `PMIC 5V <= 900 mA` 协同仿真台架

[`realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py`](realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py) 作为 **Phase 298 Stage 60（`60/60` 里程碑，Schema `realhw_focus_area_zoom_lever_iso_minss_flash_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase298_realhw_focus_area_zoom_lever_iso_minss_flash_hil=True` / `include_stage60=True` / `stage60_realhw_focus_area_zoom_lever_iso_minss_flash_hil=True`，支持显式 `--include-stage60` 以及 `--skip-phase298` / `--skip-stage60` / `--no-include-stage60` 跳过），在严格锁定 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_nflasha_write_count == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`physical_usb_packets_emitted == 0`、`still_only_tracking_exposed_in_movie_events == 0`、`af_area_reg_lock_op_parts_conflict_events == 0`、`xlr_h1_phantom_zoom_or_hold_events == 0`、`cine_ei_iso_range_or_minss_bypass_events == 0`、`flash_non_mech_or_movie_bypass_events == 0`、`mishoe_pmic_5v_900ma_overcurrent_events == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大闭环：

1. **高速双模 11 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` `< 0.2s` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 通过受界 `os.O_RDONLY`（`<= 4096 B`）核验 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 的 **11 份真实供体**：FX3 `string_*_f.uxc` 4 语种全集（`en_f=373,820 B`、`sc_f=322,652 B`、`tc_f=324,148 B`、`ja_f=447,840 B`）、FX3 `string_english.uxc`（`165,740 B`）、FX3 `string_english_g.uxc`（`69,600 B`）、FX6 `string_english.uxc`（`118,208 B`）与 `string_english_2.uxc`（`118,676 B`），以及 `FX3 appFw.so`（`79,015,712 B`）、`FX3 BK4`（`2,229,740 B`）与 `FX6 appFw.so`（`50,520,424 B`）；支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与 CLI `--clean-room` 切换至确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 60A — `[Focus Area]` 14 区层次（7 个通用 vs 7 个 Still-Only `Tracking:`）、`[AF Area Registration]`（强制 `Lock Operation Parts = Off` 耦合）与 `[Focus Area Limit]`（`>= 2` 下限）**：
   - 精确建模 `ILME-FX3 Ver. 7.02` 跨越 Still + Movie + `S&Q` 的 7 项通用对焦区域（`Wide`、`Zone`、`Center Fix`、`Spot: S/M/L`、`Expand Spot`）与 **仅限静态照片（Still-only）** 的 7 项 `Tracking:` 区域（`Tracking: Wide / Zone / Center Fix / Spot S/M/L / Expand Spot`）——在 Movie/`S&Q` 中请求任意 `Tracking:` 区域会被硬件门控拦截并返回 `EOPNOTSUPP = 95`（Movie/`S&Q` 主体追踪使用 `Touch Tracking`），对照 `ILME-FX6` 仅暴露电影机精简树（`Wide / Zone / Flexible Spot`）。
   - 建模 `[AF Area Registration]`（`Off / On`，跨 `Camera Settings Reset` 存活，在 Movie/`S&Q`/`iAuto` 禁用）开启时强制将 `[Lock Operation Parts]` 解除为 `Off`，并建模 `[Focus Area Limit]` 至少保留 `>= 2` 项启用区域（少于 2 项返回 `EINVAL = 22`）。
3. **Sub-Model 60B — 机身 `W/T` `[Zoom Lever Speed]`（`1st=3 / 2nd=8` STBY/REC）、`[Custom Key Z. Speed]`、`[Remote Zoom Speed]`（`Variable / Fixed 1..8`）与无摇杆 `XLR-H1` 实证辟谣**：
   - 精确建模与辟谣：`ILME-FX3` 的 `XLR-H1` 手柄仅为音频接口手柄，**无任何变焦摇杆、无录制键、无 `ZOOM HOLD` 开关**（在 FX3 上注入任意手柄变焦或手柄 Hold 指令均被拦截并计零越权、`EOPNOTSUPP = 95`），对照 `ILME-FX6` Smart Handle 暴露 `Handle Zoom`（`Off / Low / High / Variable 1..8`）+ `Handle HOLD Switch`；`0..99` 为 `Zoom Position Display` 刻度而非速度档位。
   - 建模 FX3 机身 `W/T` 两段式比例翘板 `[Zoom Lever Speed]`（`1st Zoom Spd.` `1..8` 默认 `3`、`2nd Zoom Spd.` `1..8` 默认 `8`，独立 `STBY` & `REC` 寄存器）、`[Custom Key Z. Speed]`（`1..8` 默认 `3`，STBY/REC）与 `[Remote Zoom Speed]`（`Speed Type: Variable / Fixed`、`Fixed Speed 1..8` STBY/REC），以及 `Zoom Range` 在 `RAW` 与 `119.88p`/`100p` 下的非光学变焦互斥锁定。
4. **Sub-Model 60C & Redlines — `[ISO Range Limit]` & Still-Only `[ISO AUTO Min. SS]` vs `Cine EI` Base ISO `800 / 12800` 硬锁 + `[Flash Mode]` 机械快门静态门控 vs `[Video Light Mode]` `PMIC 5V <= 900 mA` 保护**：
   - 建模 `[ISO Range Limit]`（`Min/Max` 限幅同时钳制手动 ISO 与 `ISO AUTO`）以及 **Still-only** `[ISO AUTO Min. SS]`（`Slower / Slow / Standard / Fast / Faster` 或 `1/8000..30"`，仅在 `P/A` 或 `M + ISO AUTO` 生效，Movie/`S&Q` 拒绝 `EOPNOTSUPP = 95`），二者在 Movie `Cine EI` / `Cine EI Quick` 下均被 Base ISO `800 / 12800` 硬锁并拒绝写入（`EOPNOTSUPP = 95`）。
   - 建模 `[Flash Mode]`（`Flash Off / Autoflash / Fill-flash [默认] / Slow Sync. / Rear Sync.`，`1/250 s` 全画幅闪光同步）**严格门控至 `EXPOSURE_MODE_STILL` + `Mechanical Shutter` + `Silent Mode = Off`**（Movie/`S&Q`、电子快门或静音模式均返回 `EOPNOTSUPP = 95`），而 `[Video Light Mode]`（`Power Link` 默认 / `REC Link` / `REC Link & STBY` / `Auto`）贯穿 Still + Movie + `S&Q` 并受 `MI-Shoe PMIC 5V <= 900 mA` 电流限幅保护，同步锁定全套 16 项硬件红线（含 `emmc_nflasha_write_count == 0`、`raw_firmware_bytes_leaked == 0`）。

### Phase 298 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 298 Stage 60（60/60 里程碑！）自检
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py --self-test --json

# 2. 全板 60 阶段（Stage 1..60, 60/60 里程碑！）统一校验（支持 --include-stage60 与 --skip-phase298 / --skip-stage60 / --no-include-stage60）
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage60 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 298 三模式 >=76 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_focus_area_zoom_lever_iso_minss_flash_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 301 Stage 61（61/61 VM 阶段里程碑！）— 真实硬件 Wave-51：`[XAVC S-I DCI 4K]` + `24.00p` 重启隔离与 Slot-1 Tier-0 Vault 防护、Still `[Aspect Ratio]` vs Movie/S&Q 格式锁定、`[Reg. Custom Shoot Set]` 11 项保持复选框与 `/SONY/SETTING/%s/` `M1..M4`/`CAMSET` 路径隔离，及 `[Photo Capture]` DCI 4K 锁定与 Slot-1 Vault 阻断协同仿真台架

[`realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py`](realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py) 作为 **Phase 301 Stage 61（`61/61` 里程碑，Schema `realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase301_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil=True` / `include_stage61=True` / `stage61_realhw_dci4k_aspect_custom_hold_camset_photo_capture_hil=True`，支持显式 `--include-stage61` 以及 `--skip-phase301` / `--skip-stage61` / `--no-include-stage61` 跳过），在严格锁定 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_nflasha_write_count == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`physical_usb_packets_emitted == 0`、`dci4k_120p_or_longgop_bypass_events == 0`、`reboot_24_00p_slot1_vault_reinit_events == 0`、`movie_still_aspect_override_events == 0`、`custom_hold_invalid_or_cineei_bypass_events == 0`、**`fx3_pro_camera_path_exposed == False`**、`fx6_cross_model_camset_import_events == 0`、`slot1_vault_camset_or_campr_mutation_bytes == 0`、`dci4k_photo_capture_bypass_events == 0`、`slot1_vault_photo_capture_mutation_bytes == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大闭环：

1. **高速双模 11 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` `< 0.05s` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 通过受界 `os.O_RDONLY`（`<= 4096 B`）核验 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 的 **11 份真实供体**：FX3 `string_*_f.uxc` 4 语种全集（`en_f=373,820 B`、`sc_f=322,652 B`、`tc_f=324,148 B`、`ja_f=447,840 B`）、FX3 `string_english.uxc`（`165,740 B`）、FX3 `string_english_g.uxc`（`69,600 B`）、FX6 `string_english.uxc`（`118,208 B`）与 `string_english_2.uxc`（`118,676 B`），以及 `FX3 appFw.so`（`79,015,712 B`）、`FX3 BK4`（`2,229,740 B`）与 `FX6 appFw.so`（`50,520,424 B`）；支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与 CLI `--clean-room` 切换至确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 61A — `[XAVC S-I DCI 4K]`（4096×2160 17:9）与 `24.00p` 重启隔离防火墙 + Still `[Aspect Ratio]` vs Movie/S&Q 格式锁定**：
   - 精确建模 `ILME-FX3 Ver. 3.00+/7.02` 暴露的 `[XAVC S-I DCI 4K]`（4096×2160 `17:9` All-Intra 4:2:2 10-bit：`59.94p@600Mbps`、`50p@500Mbps`、`29.97p@300Mbps`、`25p@250Mbps`、`24.00p@240Mbps`、`23.98p@240Mbps`；**无 100p/120p -> `EOPNOTSUPP=95`**；`S&Q` 仅限 `1..48fps`）；Long-GOP `[XAVC HS 4K]`/`[XAVC S 4K]` 与 `[XAVC S-I 4K]` 维持 3840×2160 `16:9` UHD 且不支持 `24.00p`（HDMI RAW 输出维持 4264×2408 `16:9`）。
   - 切换 `NTSC/PAL` 或进出真 `24.00p` 必须触发重启周期并启用 `24.00p` 回放隔离，严禁对未认证卡或 Slot-1 Tier-0 Recovery Vault 执行任何卡重初始化/格式化（fail-closed `EROFS=30`）；对比 `ILME-FX6` 原生 MXF `XAVC-I DCI 4K` 支持高达 `59.94p / 100p / 120p S&Q`。
   - 建模 Still 模式 `[Aspect Ratio]` 4 种长宽比（`3:2 / 4:3 / 16:9 / 1:1`，含 `RAW` 保留完整 `3:2` 像素并附带裁剪元数据、`APS-C S35` `L->M` 降档及 `Camera Settings Reset -> 3:2`），而 Movie/`S&Q` 画面宽高比严格由 File Format 决定（`17:9` DCI 4K 或 `16:9` UHD/HD）并拒绝 Still 长宽比修改（`EPERM=1`）。
3. **Sub-Model 61B — `[Reg. Custom Shoot Set]` 11 项保持复选框（`Recall Custom hold 1..3`）与 `/SONY/SETTING/%s/` `M1..M4` / `CAMSET` 路径隔离**：
   - 建模全部 **11 项实机复选框**（`is_checked_recall_custom_hold0..10`：`Shooting Mode`、`Aperture`、`Shutter Speed`、`Drive Mode`、`Exposure Comp.`、`ISO`、`Metering Mode`、`White Balance`、`Picture Profile`、`Focus Mode`、`Focus Area` + `AF On` 开关）对应 `BKID_APP_shoot_set_registration_*_available`、`Recall Custom hold 1..3` 按下生效 / 松开恢复基线、ISO/DRO Bracket 保持期间强制 `HLG Still Image = Off`、越界序号（非 `1..3`）及 `Self-timer` 拒绝（`EINVAL=22`）、`Cine EI / Cine EI Quick` 屏蔽 `Exposure Comp.` 保持并拦截显式绕过（`EOPNOTSUPP=95`），以及 `Camera Settings Reset` 保留 vs `Initialize` 清空生命周期。
   - 建模 FX3 `M1..M4`（`%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT`）与 `Save/Load Settings`（`%c:%s/SONY/SETTING/%s/CAMSET/CAMSET01..10.DAT`，SDXC 带 `/PRIVATE` 前缀、CFexpress 无 `/PRIVATE`），**零暴露** FX6 专用的 `PRIVATE/SONY/PRO/CAMERA/` 路径（`fx3_pro_camera_path_exposed == False`），拦截跨机型 FX6 CAMSET/All-File 导入（`EINVAL=22 / EPERM=1`），并在写入目标为 Slot-1 Tier-0 Vault 时强制 fail-closed（`EROFS=30 / EBUSY=16`）。
4. **Sub-Model 61C & Redlines — `[Photo Capture]`（`8.3M` / `2.1M`）DCI 4K 锁定与 Slot-1 Tier-0 Vault 防护 + Still-Only `[Enlarge Image]`**：
   - 建模播放模式 `[Photo Capture]` 从 UHD/HD 电影或 `S&Q` 片段抽取 `8.3M`（3840×2160 `16:9`）或 `2.1M`（1920×1080 `16:9`）静态图（支持 `[JPEG/HEIF Switch]`：`JPEG / HEIF(4:2:0) / HEIF(4:2:2)`），对 `[XAVC S-I DCI 4K]` 片段严格锁定（`_g.uxc 0x60ce -> EOPNOTSUPP=95`），写目标为 Slot-1 Tier-0 Vault 或写保护卡时 fail-closed `EROFS=30`；同步建模 Still-only `[Enlarge Image]` + `[Enlarge Initial Mag.]` + `[Enlarge Initial Position]`，并锁定全套 16 项硬件红线。

### Phase 301 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 301 Stage 61（61/61 里程碑！）自检
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py --self-test --json

# 2. 全板 61 阶段（Stage 1..61, 61/61 里程碑！）统一校验（支持 --include-stage61 与 --skip-phase301 / --skip-stage61 / --no-include-stage61）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage61 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 301 三模式 84 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_dci4k_aspect_custom_hold_camset_photo_capture_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 306 Stage 62（62/62 VM 阶段里程碑！）— 真实硬件 Wave-52：`[Sensor Cleaning]` >= 51% 电量门槛与强制断电 vs FX6 e-ND + APR、`[Exposure Comp.]` ±5.0/±2.0 EV + `[Cine EI]` 全锁定、`[Focus Mode]` Still 5 档 vs Movie/S&Q 2 档分离与优先设置，以及回放 `[View Mode]` / 9·25 `[Image Index]` / `[Display as Group]` / `[Rotate]` Slot-1 Tier-0 Vault 防火墙协同仿真台架

[`realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py`](realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py) 作为 **Phase 306 Stage 62（`62/62` 里程碑，Schema `realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase306_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil=True` / `include_stage62=True` / `stage62_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_hil=True`，支持显式 `--include-stage62` 以及 `--skip-phase306` / `--skip-stage62` / `--no-include-stage62` 跳过），在严格锁定 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_nflasha_write_count == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`physical_usb_packets_emitted == 0`、`sensor_cleaning_low_battery_bypass_events == 0`、`sensor_cleaning_mandatory_poweroff_bypass_events == 0`、`fx6_ibis_sensor_shake_spoof_events == 0`、**`fx3_has_builtin_end_filter == False`**、**`fx6_has_ibis_sensor_shake == False`**、**`cine_ei_exp_comp_enabled == False`**、`ev_comp_cine_ei_or_mode_bypass_events == 0`、`movie_sq_invalid_focus_mode_bypass_events == 0`、`dormant_12_30_image_index_exposed_events == 0`、`slot1_vault_rotate_mutation_bytes == 0` 与 **`raw_firmware_bytes_leaked == 0`** 的前提下完成四大闭环：

1. **高速双模 11 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 通过受界 `os.O_RDONLY`（`<= 4096 B`）核验 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 的 **11 份真实供体**：FX3 `string_*_f.uxc` 4 语种全集（`en_f=373,820 B`、`sc_f=322,652 B`、`tc_f=324,148 B`、`ja_f=447,840 B`）、FX3 `string_english.uxc`（`165,740 B`）、FX3 `string_english_g.uxc`（`69,600 B`）、FX6 `string_english.uxc`（`118,208 B`）与 `string_english_2.uxc`（`118,676 B`），以及 `FX3 appFw.so`（`79,015,712 B`）、`FX3 BK4`（`2,229,740 B`）与 `FX6 appFw.so`（`50,520,424 B`）；支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与 CLI `--clean-room` 切换至确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 62A — `[Sensor Cleaning]` >= 51% NP-FZ100 电量门槛与强制物理断电 vs 无 IBIS `FX6` e-ND + APR**：
   - 精确建模 `ILME-FX3 Ver. 2.00+/7.02` `[Sensor Cleaning]`（`_f.uxc 0x67d6`，旧版 `.uxc 0xe7d7` `Cleaning Mode`）：严格校验 `NP-FZ100 >= 51%` 电量（`<= 50%` 直接以 `.uxc 0xe574 Power insufficient.` 拒绝 -> `EACCES=13`；旧版 `Ver. 1.x` 拦截 `<= 2` 格并放行 `>= 3` 格），触发 5 轴 IBIS 传感器超声抖动与居中（`MODEL_CLEANING_MODE_COMP`），并强制锁定至物理电源开关 `OFF`（`_g.uxc 0x6221` `"Turn the power off after cleaning"`），在完成断电周期前阻断拆镜头或恢复拍摄（`EBUSY=16`）；对比无 5 轴 IBIS 抖动的 `ILME-FX6`（`fx6_has_ibis_sensor_shake == False` -> 超声抖动请求拒绝 `EOPNOTSUPP=95`），其前置光学 e-ND（`CLEAR`, `1/4..1/128`）与 `Technical > APR`（`MODEL_APR_EXECUTE_COMP`）正常运行，而 FX3 无内置 e-ND（`fx3_has_builtin_end_filter == False`）。
3. **Sub-Model 62B — `[Exposure Comp.]` Still ±5.0 EV / Movie & S&Q ±2.0 EV + `[Cine EI]` 全锁定**：
   - Still `P/A/S` 与 `M + ISO AUTO` 开放 `-5.0..+5.0 EV`（实时 EV 标尺显示 `-3.0..+3.0 EV`），Movie 与 `S&Q` 严格钳位 `-2.0..+2.0 EV`；`iAuto` 与固定 ISO 手动 `M` 档禁用（`M` 档**仅**在 `ISO AUTO` 时激活）；`[Log Shooting] = Cine EI / Cine EI Quick` 下 **100% 锁定**（`cine_ei_exp_comp_enabled == False` -> `EOPNOTSUPP=95`，改由 Base ISO `800`/`12800` + `[Exposure Index]` `±2.0 EV` 控制监看），而 `Flexible ISO` 保留 `±2.0 EV` 曝光补偿；`[Camera Settings Reset]` 将曝光补偿归零 `+0.0` 但保留 `Initialize-only` 的 `[Exposure step]`（`0.3EV` / `0.5EV`）；拦截休眠 Alpha `[Reset EV Comp.]`、Ver. 1 `[Dial Ev Comp]` 及 FX6 跨机型 5EV 曝光补偿（`EOPNOTSUPP=95`）。
4. **Sub-Model 62C & 62D — `[Focus Mode]` 5/2 模式分裂与优先设置 + 回放 `[View Mode]` / `9·25` `[Image Index]` / `[Display as Group]` / `[Rotate]` Slot-1 Tier-0 Vault 防火墙**：
   - Still 开放全部 5 档（`AF-S / AF-A / AF-C / DMF / MF`，默认 `AF-A` 随 `Camera Settings Reset` 复位；拦截休眠 `PF / SEMI_MANUAL`），Movie & `S&Q` 严格钳位为 **2 档**（`AF-C` `MOVIE_AUTO` 与 `MF`，拒绝 `AF-S/AF-A/DMF` -> `EOPNOTSUPP=95`）；`[Priority Set in AF-S]` / `[Priority Set in AF-C]`（`AF / Release / Balanced Emphasis`）与 Movie `AF-C` `[AF Assist]` 均属 `Initialize-only`（跨 `Camera Settings Reset` 留存），`[AF Illuminator]` 仅限 Still `AF-S/AF-A/DMF`。
   - 回放 `[View Mode]`（`Date View / Folder View(Still) / Movie View / AVCHD View / XAVC S View`，拒绝休眠 `Folder View(MP4)`）、精确 **`9 Images / 25 Images`** `[Image Index]`（严格拒绝休眠 `12 Images / 30 Images`）、`[Display as Group]` 与 `[Display Rotation]` 均跨 `Camera Settings Reset` 留存；**关键 Vault 防火墙**：Playback `[Rotate]`（`FUNC_rotate_content`）会改写卡上 EXIF 朝向 / `AVF_INFO` 数据库 -> 当 `Slot 1` 挂载 Tier-0 Recovery Vault、卡写保护或后台传输激活时强制 fail-closed（`EROFS=30` / `EBUSY=16`，`slot1_vault_rotate_mutation_bytes == 0`），仅允许在虚拟 `Slot 2` 对静态图执行零物理写入 `90°` CCW 旋转。

### Phase 306 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 306 Stage 62（62/62 里程碑！）自检
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py --self-test --json

# 2. 全板 62 阶段（Stage 1..62, 62/62 里程碑！）统一校验（支持 --include-stage62 与 --skip-phase306 / --skip-stage62 / --no-include-stage62）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage62 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 306 三模式 88 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_sensor_cleaning_ev_comp_focus_mode_rotate_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```

## Phase 309 Stage 63（63/63 VM 阶段里程碑！）— 真实硬件 Wave-53：`[Lens Compensation]` Shading Auto/Off vs 休眠 `Auto: Low` & `SteadyShot = Active` 畸变锁、内置前部 AF 辅助照明 LED（`#8`）vs 零照明 `FX6` + 电影 AF 运动学、AF 行为 `Initialize-only` 五项持久化（正交循环聚焦点），以及 `[Create New Folder]` + 回放 `[Rating]`（1..5 星）Slot-1 Tier-0 Vault 防火墙协同仿真台架

[`realhw_lens_comp_af_illuminator_folder_rating_coemulator.py`](realhw_lens_comp_af_illuminator_folder_rating_coemulator.py) 作为 **Phase 309 Stage 63（`63/63` 里程碑，Schema `realhw_lens_comp_af_illuminator_folder_rating_coemulator_v1`）** 接入 [`fx3_vm_coemulation_suite.py`](fx3_vm_coemulation_suite.py)（默认开启 `include_phase309_realhw_lens_comp_af_illuminator_folder_rating_hil=True` / `include_stage63=True` / `stage63_realhw_lens_comp_af_illuminator_folder_rating_hil=True`，支持显式 `--include-stage63` 以及 `--skip-phase309` / `--skip-stage63` / `--no-include-stage63` 跳过），在严格锁定 **`persistent_emmc_writes_authorized == False`**、**`hardware_live_attachment_authorized == False`**、**`overall_ready_for_hardware_attach == False`**、`spi_nor_write_authorized == False`、`el3_payload_transmit_authorized == False`、`isp_write_authorized == False`、**`cnflasha_userspace_write_blocked == True`**、`cnflasha_mutation_bytes == 0`、`physical_device_writes == 0`、`emmc_nflasha_write_count == 0`、`emmc_corruptions == 0`、`nop_count == 0`、`guest_code_modification_bytes == 0`、`physical_usb_packets_emitted == 0`、`dormant_shading_auto_low_exposed_events == 0`、`steadyshot_active_distortion_bypass_events == 0`、**`fx3_has_builtin_af_illuminator == True`**、**`fx6_has_builtin_af_illuminator == False`**、`af_illuminator_non_afs_or_silent_fire_events == 0`、`initialize_only_af_reset_wipe_events == 0`、`diagonal_focus_point_wrap_events == 0`、**`slot1_data_sector_writes == 0`**、`slot1_vault_folder_or_rating_mutation_bytes == 0`、**`slot1_avf_info_mutated == False`** 与 **`raw_firmware_bytes_leaked == 0`**（共 42 项红线不变量）的前提下完成五大闭环：

1. **高速双模 12 供体 `O_RDONLY` 字节与 SHA-256 精确锚定审计（`LOCAL_DONOR_O_RDONLY` + `CLEAN_ROOM_SYNTHETIC` 对等回退）**：
   - 通过受界 `os.O_RDONLY`（`<= 4096 B`）核验 `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 的 **12 份真实供体**：FX3 `string_*_f.uxc` 4 语种全集（`en_f=373,820 B`、`sc_f=322,652 B`、`tc_f=324,148 B`、`ja_f=447,840 B`）、FX3 `string_english.uxc`（`165,740 B`）、FX3 `string_english_g.uxc`（`69,600 B`）、**FX3 `libInfraLensCommunicator.so`（`14,544 B`）**、FX6 `string_english.uxc`（`118,208 B`）与 `string_english_2.uxc`（`118,676 B`），以及 `FX3 appFw.so`（`79,015,712 B`）、`FX3 BK4`（`2,229,740 B`）与 `FX6 appFw.so`（`50,520,424 B`）；支持 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与 CLI `--clean-room` 切换至确定性 `CLEAN_ROOM_SYNTHETIC` 基线。
2. **Sub-Model 63A — `[Lens Compensation]` Shading Auto/Off vs 休眠 `Auto: Low` 与 `SteadyShot = Active` 畸变锁**：
   - 精确建模 `ILME-FX3 Ver. 7.02` `[Shading Comp.]` 仅暴露 `Auto`（默认）/ `Off`，严格拒绝休眠 `LENS_COMP_SHADING_AUTO_LOW` / `_f.uxc 0x6c9c` `'Auto: Low'`（`ILCE-6700`/`ILCE-7RM5`，`EOPNOTSUPP=95`）；`[Chromatic Aberration Comp.]` 开放 `Auto`/`Off`；`[Distortion Comp.]` 开放 `Auto`/`Off`，但在特定镜头档案（`SELP1650`、`FE 28-70mm`）或 Movie/S&Q `[SteadyShot] = Active` 时强制锁定 `Auto`（尝试切 `Off` 拒绝 `EOPNOTSUPP=95`）；无触点手动镜头拒绝菜单补偿（`EOPNOTSUPP=95`）；Shading/CA/Distortion 跨 `[Camera Settings Reset]` 留存并仅在 `[Initialize]` 重置，而 Movie-only `[Breathing Comp.]` 随 `[Camera Settings Reset]` 复位；对比 `ILME-FX6 Ver. 6.01` `Technical > Lens`（`All File` 作用域，Distortion=Off / S&Q / RAW 强制禁用 Breathing）及与传感器 `White/Black Shading`（`PID_SET_{WHITE,BLACK}_SHADING`）的本质隔离。
3. **Sub-Model 63B — 内置前部 AF 辅助照明 LED（`#8`, `0.3..3.0 m`）vs 零照明 `ILME-FX6` & 电影 AF 运动学**：
   - 建模 FX3 前部自拍定时/AF 辅助照明 LED（`TP1000886886.html` Front `#8`，`0.3..3.0 m`）+ MI 热靴外闪 AF 辅助灯仅在 **Still `AF-S`**（`Auto`、非静音、非对焦放大、无转接环）触发，并在 `Movie`、`S&Q`、`AF-C`、`MF`、`Silent Mode = On`、`Focus Magnifier` 与 `Mount Adaptor` 下严格锁定拦截（`EOPNOTSUPP=95`）；严格对比 **零内置 AF 辅助照明 LED 的 `ILME-FX6`**（`fx6_has_builtin_af_illuminator == False`）；同时覆盖 Movie/`S&Q` `[AF Transition Speed]`（`1..7`，默认 `5`）、`[AF Subj. Shift Sensitivity]`（`1..5`，默认 `5`）与 `[AF Assist]`（Movie/`S&Q` `AF-C` 专用，不兼容 `SELP1650`/`SEL18200LE`）及其 `[Camera Settings Reset]` 复位逻辑。
4. **Sub-Model 63C — AF 行为 `Initialize-only` 五项持久化与正交聚焦点循环**：
   - 建模 `[Aperture Drive in AF]`（`Focus Priority` / `Standard` / `Silent Priority`，Still-only 且与 `Silent Mode Settings` 联动）、Still-only `[AF w/ Shutter]`、`[Pre-AF]`（镜头门控 `VAL_lens_pre_af_support`）、`[Circ. of Focus Point]`（**仅允许水平/垂直正交环绕，严禁对角线斜向环绕 -> `EOPNOTSUPP=95`**）以及 `[Focus Area Color]`（`White` / `Red`，拒绝旧版 `Focus Frame Color` 伪造名称 -> `EOPNOTSUPP=95`）；全部 5 项均跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 保留，**仅通过 `[Initialize]` 复位**；对比 `ILME-FX6` 缺席此 5 项而采用电影 `Iris`（`Auto Iris` / `Manual` / `Push Auto Iris` / `Override -1.0..+1.0` 步进 `0.25`）与 `Focus Area Marker`。
5. **Sub-Model 63D & Redlines — `[Create New Folder]` 与回放 `[Rating]`（1..5 星）Slot-1 Tier-0 Vault 防火墙**：
   - 建模 `[File/Folder Settings]`（`Standard Form` `100MSDCF..999MSDCF` vs `Date Form` 禁用 `[Select REC Folder]`；`Series`/`Reset`；3 字符前缀拒绝前导 `_`）、`[Create New Folder]` / `[Forced File Number Reset]`（`max + 1`、`999` 文件夹上限、双卡同录检测）与回放 `[Rating]`（1..5 星 + `[Rating Set(Custom Key)]` 复选框过滤 + 拍摄画面 `[Add Rating]` 拒绝重复评分 `_g.uxc 0x627d` 及后台 FTP 传输拦截 `EBUSY=16`）；**核心 Vault 防火墙**：当 `Slot 1` 挂载 Tier-0 Recovery Vault 时，任何 `[Create New Folder]`、`[Forced File Number Reset]`、`[Select REC Folder]` 隐式写入或 `[Rating]`/`[Add Rating]` 改写 EXIF/`AVF_INFO` 均强制 fail-closed（`EROFS=30`，`slot1_data_sector_writes == 0`、`slot1_avf_info_mutated == False`、`slot1_vault_folder_or_rating_mutation_bytes == 0`），仅允许在虚拟 `Slot 2` 执行零物理写入仿真；对比 `FX6` 使用 `XDROOT/Clip` 与 `Clip Flag`（`OK/NG/KEEP`）。

### Phase 309 CLI 运行与测试命令

```sh
# 1. 本地只读供体模式 & 洁净室模式 Phase 309 Stage 63（63/63 里程碑！）自检
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_lens_comp_af_illuminator_folder_rating_coemulator.py --self-test --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_lens_comp_af_illuminator_folder_rating_coemulator.py --self-test --summary
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx3-vm/realhw_lens_comp_af_illuminator_folder_rating_coemulator.py --self-test --json

# 2. 全板 63 阶段（Stage 1..63, 63/63 里程碑！）统一校验（支持 --include-stage63 与 --skip-phase309 / --skip-stage63 / --no-include-stage63）
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --include-stage63 --summary
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary

# 3. 单独运行 Phase 309 三模式 88 项单测 & 全量 fx3-vm 单测（双模）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_lens_comp_af_illuminator_folder_rating_coemulator.py -v
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_lens_comp_af_illuminator_folder_rating_coemulator.py -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_lens_comp_af_illuminator_folder_rating_coemulator.py -v
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'
```


