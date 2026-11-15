# Phase 198（Task H217）：实机 Pillar 28 风扇 PWM 热联锁、独立快门 Speed/Angle 金库与 6.01 vs 7.02 User LUT 防污染暨 28/28 统一恢复总控报告

## 1. 结论先行

基于已合入的 **Phase 195 (`verify-27pillar-recovery`)** 与 Wave-25 索尼实机情报（[Wave-25 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/reports/2026-11-15-global-sony-wave25-fan-pwm-offinrec-shutter-angle-lut-601-vs-702-binary-split-intel/README.md)），已在 `outputs/fx3-recovery-adapter/` 内完成 **Pillar 28 (`realhw_28pillar_fan_pwm_shutter_lut_split_verifier`)** 与 **28 支柱统一恢复总控 (`evaluate_28pillar_recovery_master` / `verify-28pillar-recovery`)** 闭环交付：

- **统一总控达标**：`verify-28pillar-recovery` 在本地只读 donor 模式（`LOCAL_DONOR_O_RDONLY`，约 `1.00s–1.35s`）与离线无塵室模式（`CLEAN_ROOM_SYNTHETIC`，约 `0.74s`）下均达成 `28/28`（`VERIFIED_28OF28_PILLAR_RECOVERY_MASTER`），远低于 `< 2.4s` 标称预算与 `< 6.0s` 并发上限。
- **向下兼容 100% 无损**：`verify-22pillar-recovery`（`22/22`）、`verify-24pillar-recovery`（`24/24`）、`verify-26pillar-recovery`（`26/26`）与 `verify-27pillar-recovery`（`27/27`）全部原样通过。
- **硬件安全红线硬锁**：`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。

## 2. 交付文件清单（严格限定 6 个归属文件）

1. [realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py)：实现只读 donor 审计、Pillar 28A（6 场景）、Pillar 28B（6 场景）及 `28/28` 并发聚合器 [`evaluate_28pillar_recovery_master`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py#L1706-L1881)。
2. [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)：无遮蔽导出 Pillar 28 与 `evaluate_28pillar_recovery_master` / `verify_28pillar_recovery_suite`。
3. [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)：新增 CLI 子命令 `verify-fan-pwm-lut-split-vault` 与 `verify-28pillar-recovery`（支持 `--force-clean-room` / `--clean-room`、`--json`、`--out`）。
4. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/outputs/fx3-recovery-adapter/README.md)：补齐 Phase 198 Pillar 28 与 `28/28` 恢复总控文档与 CLI 用法。
5. [test_realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/outputs/fx3-recovery-adapter/tests/test_realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py)：新增 **52 项**双模式快速单元测试（Group 0/A/B/C/D）。
6. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/reports/2026-11-15-phase198-realhw-28pillar-fan-pwm-lut-split-vault-recovery/README.md)：本阶段中文技术验收报告。

## 3. 核心架构与实测事实 vs 建模边界

### 3.1 只读实机 Donor 锚点（实测事实，`O_RDONLY | O_NOFOLLOW | O_NONBLOCK`）
[`inspect_phase198_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py#L445-L743) 对大镜像严格限制 `4096 B` `os.pread` 头部校验，对小型配置与库文件执行完整 SHA-256 锚定（JSON 报告零原始固件字节泄漏）：
- `fx3-7.02-BODYDATA.DAT`：`811,876,768 B`，`\x89UFU\r\n\x1a\n` + `DATV/PROV/UDID`，4K SHA-256 `fc1359148356be2a...`。
- `FX3 Ver. 7.02 appFw.so`（`79,015,712 B`，4K SHA-256 `de3201c6...`）对比 `FX6 Ver. 6.01 appFw.so`（`50,520,424 B`，4K SHA-256 `18a5d713...`）：实锤确认 `<=6.01` 旧版与 `>=7.00` 优化版二进制存在跨代差异。
- `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，`BK4\x00` + `0xAAAAAAAA` + `ILME-FX3`，SHA-256 `bf3a9d85...`）、`libfan.so`（`27,280 B`，导出 `fan_infra_init` / `_Z15fan_i_bkup_readP13ST_FAN_I_BKUP` / `V_TEMP_LIST`，SHA-256 `c607fc8d...`）及 `libbackup.so`（`14,232 B`，导出 `Backup_read` / `Backup_nread_setting_attr` / `Backup_protect`，SHA-256 `6a3c5f60...`）。

### 3.2 Pillar 28A：`ILME-FX3` 精确四档 `[Fan Control]` 与预备份热联锁（6 场景）
- [`evaluate_fan_pwm_prebackup_thermal_interlock`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py#L775-L877) 严格校验 `ILME-FX3` 仅有的四档枚举 `("Auto", "Minimum", "Off in Rec", "Always Off")`，对非 FX3 广播机/他厂枚举（`Auto1`、`Auto2` 等）执行 fail-closed 拦截。
- 在执行长耗时 `75 MiB` `p3` `AdjustControl (0x40)` 冷备或 Stage-B 双系统高负载试运行前，若原厂风扇仍处于 `Always Off`（或未切回 `Auto`），立即中止准入并要求先执行 `Always Off -> Auto` 预备份热覆盖（同时兼容 `[Auto Power OFF Temp.] = Standard / High`）；同时精确建模 `Off in Rec` 待机 `100% MAX PWM`、录制 `0% PWM` 及 `>= 82.0°C` 紧急热保护强开 `100% PWM`。

### 3.3 Pillar 28B：`6.01` vs `7.00/7.02` `User1..User16` LUT 跨代防污染与独立 `Speed/Angle` 金库（6 场景）
- [`evaluate_lut_split_and_shutter_angle_vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h217-phase198-pillar28-28pillar-fan-pwm-lut-split-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py#L1263-L1400) 将 Stage-B `FX6 Ver. 6.01` 旧版 LUT 槽位序列化强制重定向至易失性 tmpfs `/tmp/fx6_lut_overlay`，严禁触碰 `BLKROSET=1` 锁定的原厂 `FX3 Ver. 7.02` `p2:/setting` `User1..User16` 槽位。
- 验证 `Backup.bin` 内 `[Speed]` 与 `[Angle]` 独立键槽互不覆盖、与 `0.3EV / 0.5EV` 曝光步进解耦，以及常规帧率 `5.6°..64F (23040°)` vs `119.88p / 100p` 与 `S&Q` 收窄至 `5.6°..360°` 的边界约束，确保冷启动回到 Stock `7.02` 后 `16/16` 槽位与 `Backup.bin` 严格满足 `H0 == H3`。

## 4. 验证记录（全量 `/usr/bin/python3 -B`）

- `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-28pillar-recovery --json`：`VERIFIED_28OF28_PILLAR_RECOVERY_MASTER`（`28/28`，`master_28pillar_sha256=396b988e551c376a...`；`--force-clean-room` 下 `c7de3aed589e71ad...`）。
- `test_realhw_28pillar_fan_pwm_shutter_lut_split_verifier.py`：`LOCAL_DONOR_O_RDONLY` **52/52 OK**；`FX3_FX6_FORCE_CLEAN_ROOM=1` **52 ran (51 OK, 1 skipped)**。
- `outputs/fx3-recovery-adapter/tests` 全量发现测试（`LOCAL_DONOR_O_RDONLY` **1271 项 OK**，`FX3_FX6_FORCE_CLEAN_ROOM=1` **1213 项 OK**）与 `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`（`ALL GREEN in 0.11s`）：全部通过，零 `.pyc` 残留。
