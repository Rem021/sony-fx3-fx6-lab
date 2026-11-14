# FX3｜Sony FX3 / FX5 / FX6 固件与模拟器实验室

> 继承全局 `~/.codex/AGENTS.md`（并行改代码请在 Orca `FX3` Git 项目下开独立工作树，常规改动用 `agent-ship` 自动交付）。

- **核心模块**：`outputs/fx3-vm/`（FX3 Web UI 模拟器）· `outputs/fx3-vm-trial/`（FX3/FX6 v6.01 `gpe0` 128 页菜单运行器）· `outputs/fx3-firmware-lab/`（解包与 `ldec` 解码）· `outputs/fx3-recovery-adapter/` & `outputs/fx3-safety/`（恢复与硬件安全护栏，含 66 项离线与 Unicorn 测试）。
- **开源与合规红线（BYOF）**：严禁提交索尼专有固件镜像（`nflasha*`、`.cpio`、`appFw.so`、`cpapp-b.bin`）、`.qcow2`/`.img` 磁盘或 `>50 MiB` 大文件；保留 `Mac/work/...` 下被引用的本地 donor 二进制。
- **硬件禁令**：严禁对真实物理 FX3 相机执行跨机型整分区刷写或 USB/SD 烧录（BLOCKED / NO-GO）。
