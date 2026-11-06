# FX3 Mac 最小研究虚拟机

当前可在这台 Apple Silicon Mac 上用原生 QEMU/TCG 运行 **经典 FX3 7.02 的原 Linux 内核与最小原用户态**。已分别验证原 BusyBox/`uname`，以及原动态加载器对 `bootin.elf`、`im.elf` 的 verify/list。相机菜单、CP/IPC、CMOS/ISP、照片与录像尚未接入。

## 运行

双击本目录 [启动FX3最小研究虚拟机.command](启动FX3最小研究虚拟机.command)。终端运行约 12 秒后正常退出，显示状态和日志路径。该 `.command` 是可审阅的终端入口，不是图形相机界面。

也可使用本机已安装的 Python 3.14：

```sh
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 /Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/run_probe.py --self-check
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 /Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/run_probe.py --profile minimal-linux --seconds 12
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3 /Volumes/KAFU2T/AI/Projects/Mac/outputs/fx3-vm/run_probe.py --profile app-loader --seconds 12
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
/Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage47-runtime-provider-binding/official-files/nflasha3/vmlinux.bin
SHA256 da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c
```

入口核对外盘 UUID、原内核与运行文件 SHA；有缺失/变化会停止。未连接相机或手机；运行参数不提供网卡、USB/宿主磁盘/宿主目录透传。当前验收是短时运行，长期稳定性未验证。

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

这给出下一处具体环境缺口：Sony UIPC设备与服务模型。默认运行包/profile保持不变，当前停止追加仿真修复轮。[alpha原始记录](/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/host/ap-entry-alpha-summary.json)。
