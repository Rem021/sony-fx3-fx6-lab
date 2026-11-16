# Phase 174（第 36/36 项统一审计）：真实硬件 `p5:/wbi`（`WBI2` / `hibdrv.ko`）休眠快照隔离、零写入锁定与 Stock/Stage-B 冷启动确定性审计报告

## 1. 结论先行

本阶段在 [`outputs/fx3-firmware-lab/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab) 新增第 **36/36** 个统一固件审计模块 [`realhw_wbi2_hibdrv_hibernation_isolation_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wbi2_hibdrv_hibernation_isolation_auditor.py)，面向真实物理 `Sony ILME-FX3`（`Ver. 7.02`，`CXD90057 + CXD90058`）完成 `p5:/wbi`（`WBI2` / `hibdrv.ko`）跨世界休眠污染防护与冷启动确定性双模态（`LOCAL_DONOR_VERIFIED` 严格 `os.O_RDONLY` + `CLEAN_ROOM_SYNTHETIC`）验证：

1. **`p5:/wbi`（`/dev/nflasha5` / `/dev/cnflasha5`）休眠快照零写入硬锁（`wbi_mutation_bytes == 0`）**：实测 FX3 `7.02` 与 FX6 `6.01` `WBI2` 快照存在不可跨内核恢复的结构性差异（`resume_vector` `0x4004a67f0` vs `0x4004a87f0`、段表 `1,399` vs `1,197` 段、`phys` 上界 `0x420000000` vs `0x424000000`、`wbimem` 跨度差 `+0x00d79000` / `+13.47 MiB`）。Stage-B 强制创建 `/tmp_wbshd/stage_b_wbi_inhibit.lock` 启用 `WBI_SAVE_INHIBITED`，阻断任何 `hibdrv.ko` 快照写入与 `MS_RDWR` 重挂载，确保拔出 SD 卡后物理机 100% 回到未受损的原生 FX3 `7.02`。
2. **Stage-A 冷启动（`NORMAL`）与热唤醒（`BIS`）入口隔离**：实测 FX3/FX6 `/usr/bin/im.elf`（`40,920 B`，`11` 导出 / `85` 导入）共享 `/proc/udm/upm_bootmode`、`/sys/power/state`、`BIS`、`bootall` 检查路径；Stage-A 包装器仅在 `upm_bootmode == "NORMAL"`、单次令牌 `/tmp/mod_arm_once` 触发并清零、`/dev/nflasha5` 未挂载且具备 `noresume` / `hibdrv.resume=0` 时激活，命中 `BIS`、`UPDATER`、`SERVICE`、重入锁或预挂载 `p5` 即刻 `fail-close` 退回 `STOCK_FX3_FALLBACK`。
3. **Stage-B 退出强制 `POWEROFF_CLEAN_NO_WBI` 与防残留确定性**：实测 FX3/FX6 `libmpr.so` 与 `cpapp-b.bin` 共同包含 `mpr::PowerOff`、`Fsys_SuspendAsyncRequests`、`POWEROFF_ERROR_HANDSHAKE_END`、`POWEROFF_HANDSHAKE_TIMEOUT_ERROR`；Stage-B 退出流程先完成外卡异步刷盘与 Stock-CP 关机握手，按 LIFO 逆序卸载 bind-mount 并清空易失 `/tmp` 叠层，严禁 `/sys/power/state` 写入 `disk`/`mem`/`standby`，杜绝插拔 SD 卡切换世界时携带残留 RAM 或 CP 状态。
4. **全链路只读写入防火墙（`persistent_emmc_writes_authorized = False`, `spi_nor_write_authorized = False`）**：拦截一切对 `p5:/wbi`、`/dev/nflasha*`、`/dev/cnflasha*`、`/dev/mmcblk0*`、`hibdrv.ko`、`/sys/power/state`、`p2:/Backup.bin`、`p8:/cpapp-b.bin`、`p12:/cert`、`p18:/lens` 与 `spi_nor:` 的持久化写入，仅放行易失 `/tmp/`、`/tmp_wbshd/`、`ram://` 与外置 `/mnt/sd*`、`/mnt/cfexpress_a/` 媒体路径。

> [!IMPORTANT]
> **严格区分已实测事实与未执行物理机动作**：本文第 2 节所有文件字节数、`WBI2` 头/段表参数与符号命中计数均来自对本地 FX3 `7.02` 与 FX6 `6.01` Donor 工件执行 `os.open(..., os.O_RDONLY)` + `mmap.ACCESS_READ` / `os.pread` 的实测结果（单次扫描耗时 `0.684 s`，Clean-Room `0.002 s`）；**真实物理 `ILME-FX3` 机身插拔 SD 卡冷启/关机/电源切换与示波器或串口台架实拍尚未执行**。

---

## 2. `O_RDONLY` 本地 Donor 实测证据（`LOCAL_DONOR_VERIFIED`，`0.684 s`）

| Donor 工件 | 机身 / 固件 | `O_RDONLY` 实测字节数 | 关键结构与符号命中实测 |
| :--- | :--- | ---: | :--- |
| `nflasha5.img` / `nflasha5` | FX3 `7.02` / FX6 `6.01` | `209,112,512` / `202,677,056` | `WBI2` 魔数、`dVersion=0x20060224`；段数 `1,399` (`82` 零段) vs `1,197` (`54` 零段)；`resume_vector=0x4004a67f0` vs `0x4004a87f0`；`phys=[0x400001000, 0x420000000)` vs `[0x400001000, 0x424000000)`；`wbimem` 跨度差 `+14,127,104 B` (`+13.47 MiB`)；共有 `image_drop`/`image_mode`/`image_mem`/`image_dev`/`/dev/nflasha5`/`/dev/cnflasha5`/`upm_senser_wbi_drop`/`wbimem` |
| `im.elf` | FX3 `7.02` / FX6 `6.01` | `40,920` / `40,920` | 导出/导入完全一致（`11 / 85`）；均命中 `/proc/udm/upm_bootmode` (`1`)、`/sys/power/state` (`1`)、`BIS` (`1`)、`bootall` (`1`) |
| `libsencore.so` | FX3 `7.02` / FX6 `6.01` | `377,328` / `401,952` | 导出/导入一致（`355 / 130`）；均命中 `/dev/nflasha5` (`1`)、`WBI_DROP` (`2`)、`/boot/sen/smode` (`1`)、`/proc/snsc_boot_time` (`1`) |
| `libmpr.so` | FX3 `7.02` / FX6 `6.01` | `3,517,008` / `28,921,824` | 均命中 `_ZN3mpr8PowerOffERKNS_15powerOffInParamE` (`1`)、`_ZN3mpr12PowerOffMainEPv` (`1`)、`_ZN3mpr26gp_evtPowerOffFinishedFuncE` (`1`)、`Fsys_SuspendAsyncRequests` (`2`)、`Fsys_ResumeAsyncRequests` (`1`) |
| `appFw.so` | FX3 `7.02` / FX6 `6.01` | `79,015,712` / `50,520,424` | 均命中 `EID_POWEROFF` (`1`)、`OFF_BY_BIS` (`1`)、`UIBIZ_KEY_LANC_POWEROFF` (`2`) |
| `cpapp-b.bin` | FX3 `7.02` / FX6 `6.01` | `15,980,568` / `17,952,816` | 均命中 `POWEROFF_ERROR_HANDSHAKE_END` (`1`)、`POWEROFF_HANDSHAKE_TIMEOUT_ERROR` (`1`) |
| `Backup.bin` | FX3 `7.02` / FX6 `6.01` | `2,229,740` / `2,253,333` | 偏移 `+4` 校验字 `0xaaaaaaaa`、偏移 `+12` `BK4\x00`；子系统数 `819` vs `840` |

---

## 3. 四大审计支柱与 12 触点 4 分类兼容性矩阵

- **Pillar 1（`P5_WBI2_HIBDRV_ZERO_WRITE_LOCK`）**：[`evaluate_p5_wbi2_hibdrv_zero_write_lock`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wbi2_hibdrv_hibernation_isolation_auditor.py) 与 [`evaluate_p5_wbi2_h0_h3_conservation`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wbi2_hibdrv_hibernation_isolation_auditor.py) 验证 `/tmp_wbshd/stage_b_wbi_inhibit.lock`、`BLKROSET=1` 块只读锁、`8B` 魔数 `WBI2\x00\x00\x00\x00`（`5742493200000000`，`4.9.337-scel+` `ssboot` / LZO `prsv-img` / `liro.ko`）与卸载期 `H0 == H3` 位级守恒（`wbi_mutation_bytes == 0`），拒绝 `MS_RDWR` 挂载与任何快照片写入请求，并交叉验证 `verify_hibdrv_cross_kernel_rejection` 返回 `BLOCKED_CROSS_KERNEL_WBI2_EL1_MISMATCH`。
- **Pillar 2（`COLD_BOOT_VS_WARM_BOOT_STAGE_A_ENTRY_ISOLATION`）**：[`evaluate_stage_a_cold_vs_warm_boot_entry`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wbi2_hibdrv_hibernation_isolation_auditor.py) 强制 Stage-A 仅放行具备 `noresume`/`hibdrv.resume=0` 且 `upm_bootmode == "NORMAL"` 的首次冷启动，彻底拦截 `BIS`、`UPDATER`、`SERVICE`、重入锁与预挂载 `p5`。
- **Pillar 3（`STAGE_B_CLEAN_POWEROFF_NO_WBI_DETERMINISM`）**：[`evaluate_stage_b_poweroff_determinism`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wbi2_hibdrv_hibernation_isolation_auditor.py) 覆盖电源开关关机、电池仓退出、SD 卡拔出切换、热故障保护四类退出触发器，拒绝 `disk`/`mem`/`standby` 挂起，并验证介质刷盘与 CP 握手超时安全降级。
- **Pillar 4（`P5_WBI_WRITE_FIREWALL_AND_12TP_ISOLATION_MATRIX`）**：[`evaluate_phase174_write_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wbi2_hibdrv_hibernation_isolation_auditor.py) 与 [`build_phase174_hibernation_isolation_matrix`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wbi2_hibdrv_hibernation_isolation_auditor.py) 拦截 `/proc/udm/*`、`liro.ko`、`hibdrv.ko`、`/sys/power/state` 与 `p5:/wbi` 等持久化目标，并构建 12 触点 4 分类矩阵（`HARD_WRITE_PROTECTED=4`、`SHIM_TRANSLATED=4`、`NATIVE_PASSTHROUGH=3`、`MASKED_ABSENT_HW=1`）。

---

## 4. 交付文件清单与实测验证结果

### 4.1 交付文件（严格限定于授权路径）
- 审计核心：[`realhw_wbi2_hibdrv_hibernation_isolation_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wbi2_hibdrv_hibernation_isolation_auditor.py)
- 包导出与 `36/36` CLI 入口：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py)、[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py)、[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/README.md)
- 双模态单元测试（52 项）：[`test_realhw_wbi2_hibdrv_hibernation_isolation.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/tests/test_realhw_wbi2_hibdrv_hibernation_isolation.py)（同步放宽 [`test_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h189-phase174-wbi2-hibdrv-hibernation-isolation/outputs/fx3-firmware-lab/tests/test_realhw_c2pa_cert_vmcbncm1_tc_and_gyro_meta.py#L278) 第 278 行为 `assertGreaterEqual(..., 35)`）

### 4.2 实测通过结果（`/usr/bin/python3 -B`）
1. `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m fx3_firmware_lab audit-realhw-wbi2-hibdrv-isolation --json`：`LOCAL_DONOR_VERIFIED` `all_checks_passed=True`（`report_sha256=96b0cdbb40a16d1d4f9afeeadd1847110675a0239bc9d6465e2ab0507a71db8f`）；`--clean-room --json`：`CLEAN_ROOM_SYNTHETIC` `all_checks_passed=True`（`report_sha256=aeea12a1a61d82defd7ace2022d58e1cce117422d15d097ec4e97c4485f289f5`）。
2. `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"`：**1,262 项测试全部通过**（`48.961s`，含本阶段 52 项测试 `1.909s`）。
3. `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"`：**1,262 项测试全部通过**（`24.131s`，`skipped=4` 均为仅限本地 Donor 的断崖检查）。
4. `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`：`ALL GREEN in 0.04s`（零 `.pyc` / 二进制污染）。
5. **待后续物理台架条件**：真实物理 `ILME-FX3`（`Ver. 7.02`）带 SD 卡激活 Stage-B 开关机切换及拔卡恢复 Stock FX3、且确认 `/dev/nflasha5` `BLKROSET=1` 与 `H0 == H3` 零写入变动的实机验证。
