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

# 4. 运行 Phase 24 全量 22 项单测（本地供体模式 & 洁净室模式）
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py" -v
```

