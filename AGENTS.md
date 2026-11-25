# FX3｜Sony FX3 / FX5 / FX6 实验室
- 核心模块：`outputs/fx3-vm/`（Web UI 模拟器）· `outputs/fx3-vm-trial/`（v6.01 `gpe0` 菜单运行器）· `outputs/fx3-firmware-lab/`（解包与 `ldec` 解码）· `outputs/fx3-recovery-adapter/` & `outputs/fx3-safety/`（恢复与硬件安全护栏）。
- BYOF 合规红线：严禁提交索尼专有固件镜像（`nflasha*`、`.cpio`、`appFw.so`、`cpapp-b.bin`）、`.qcow2`/`.img` 磁盘或 `>50 MiB` 大文件；保留 `Mac/work/...` 下被引用的本地 donor 二进制。
- 硬件禁令：严禁对真实物理 FX3 相机执行跨机型整分区刷写或 USB/SD 烧录（NO-GO）。
- 编排防卡队：总控不挂 `schedule` 定时轮询；合入后清理已合并子工作树。
