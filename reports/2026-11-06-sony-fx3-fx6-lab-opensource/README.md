# 2026-11-06 Sony FX3 & FX6 虚拟机与系统移植全量开源同步回执

- **日期**：2026-11-06
- **GitHub 开源仓库**：[https://github.com/Rem021/sony-fx3-fx6-lab](https://github.com/Rem021/sony-fx3-fx6-lab)（Public，默认分支 `main`，首轮提交 SHA `f051fc43f8ca11fbae9474842e1b285d75e6af72`）
- **本机仓库路径**：[/Volumes/KAFU2T/AI/Projects/Mac/outputs/sony-fx3-fx6-lab](../../outputs/sony-fx3-fx6-lab)
- **原始项目文件保护**：本机 `work/`、`outputs/`、`reports/`、`research_notes/` 下所有既有文件与路径保持原位、未做任何移动或修改，不影响既有模拟器脚本与哈希校验锁。

---

## 1. 同步范围与文件统计

本次同步涵盖了项目中关于 **Sony ILME-FX3 (7.02)** 与 **Sony ILME-FX6 (6.01)** 的全部自研代码、补丁、脚本、进度报告与校验清单（共计 **19,572 个文件，约 182.2 MiB 文本与源码**）：

1. **正式交付与工具入口 (`outputs/`)**：
   - `outputs/fx3-vm/`：FX3 Mac 最小研究虚拟机启动器、QEMU 高位 DDR/ESRAM 补丁 (`fx3-esram-high-ddr.patch`)、Mach-O 相对化与溯源清单。
   - `outputs/fx3-vm-trial/`：FX3 原厂菜单网页交互模拟器入口 (`FX3菜单.command`)、使用说明与 32 键真实网页导航验收记录。
   - `outputs/fx3-recovery-adapter/`：FX3 恢复分区 (`p1`) 与 `boot0`/`boot1` 离线适配及静态 AArch64 工作器构建工具 0.5。
   - `outputs/fx3-safety/`：真机刷写安全红线与防变砖检查清单。
   - `outputs/progress-20261103/`：项目三维进度静态可视化看板。
2. **全阶段核查报告 (`reports/` & `research_notes/`)**：
   - `reports/2026-11-05-fx6-capid-grm-frontier/`：FX6 混合启动前沿（CP/CAPID/GRM/UXEngine/按键注入/DMM 显示内存定位）。
   - `reports/2026-11-05-fx6-cp-helper-agnostic/`：FX6 地址无关 CP Helper 绑定与 `appFw.so` 执行报告。
   - `reports/2026-11-05-fx6-boot-gate-audit/`：FX6 在固定 FX3 虚拟机上开机的三条路线审计。
   - `reports/2026-11-03-fx6-full-system-to-fx3/`：FX6 6.01 全系统刷入 FX3 7.02 的 30 分区兼容矩阵、NOR 同构证明与最小可逆路径。
   - `reports/2026-11-01-fx3-vm-resumed-repair/`：FX3 模拟器 AP70–AP105 菜单修复全套技术报告与网页菜单截图。
   - `reports/2026-10-31-venice-phayen-color-chain/` 及 `research_notes/` 下全部 10 个索尼 FX3/FX5/FX6 专题研究目录。
3. **核心工程源码与测试套件 (`work/`)**：
   - `work/fx3-color-port-20261027/`：FX6 供体评估、地址无关 CP helper C 源码、CAPID 预初始化、GRM/FrameBuffer C 垫片、AArch64 映射采集器 (`fx3_map_snapshot`)、串口故障检测器、Backup 键值与开机画面断言契约分析脚本。
   - `work/fx3-vm-20261101/`：FX3 QEMU 设备模型补丁、AP1–AP105 运行时 C 辅助库源码、`v25` 网页菜单模拟器服务端/前端 (`.py`/`.js`) 及自动化浏览器/QMP/GDB 测试套件。
   - `work/sony-firmware-20261024/`：Stage 1–286 固件解包、服务模式协议 (`285/286 AdjustControl`)、USB 传输与恢复通道研究源码。
4. **自备固件复现指南 (`docs/BYOF-REPRODUCTION.md`)**：
   - 汇总了 FX3 7.02 与 FX6 6.01 各关键官方分区镜像、内核、DTB 与动态库的精确字节长度和 SHA-256 指纹，供外部研究者自备官方固件包复现。

---

## 2. 安全与合规核查

- **密钥扫描**：全量 19,572 个文件经正则扫描确认 `0` 处私钥或 API Token（`Secret hits: 0`）。
- **版权与大文件排除**：通过导出过滤与 `.gitignore` 排除了 `work/` 下约 146 GB 的索尼原厂闭源二进制文件（`BODYDATA.DAT`、`vmlinux.bin`、`appFw.so`、`nflasha*`）、453 MB `.cpio` 镜像及第三方上游源码树（`linux-kernel`、`qemu-src`、`zig` 工具链）。
