# Phase 212（Task H233）：实机 Pillar 30 `Px` 原子主+代理联动金库、`[Off(HDMI Only)]` 零内录卡互锁与 `30/30` 里程碑恢复总控报告

## 1. 结论先行

基于已合入的 **Phase 208 (`verify-29pillar-recovery`)** 与索尼官方实机情报 Wave-28（[Wave-28 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/reports/2026-11-15-global-sony-wave28-hdmi-log-1080p-hdmionly-4k-proxy-coupled-vault-focusmag-brightmon-intel/README.md)），已在 `outputs/fx3-recovery-adapter/` 内闭环实现 **Pillar 30 (`realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier`)** 并正式达成 **`30/30` 里程碑恢复总控 (`evaluate_realhw_30pillar_recovery_master` / `verify-30pillar-recovery`)**：

- **里程碑 `30/30` 达标**：`verify-30pillar-recovery` 在本地只读供体模式（`LOCAL_DONOR_O_RDONLY`，实测约 `1.180s`，`master_30pillar_sha256=d9cbb5dce40b89ea...`）与离线洁净室模式（`CLEAN_ROOM_SYNTHETIC`，实测约 `0.855s`，`master_30pillar_sha256=ead7bbcc7469a95d...`）下均达成 `30/30`（`VERIFIED_30OF30_PILLAR_RECOVERY_MASTER`），远低于 `< 2.6s` 标称预算与 `< 6.0s` 测试并发上限。
- **向下兼容 100% 无损**：`verify-22pillar-recovery`（`22/22`）、`verify-24pillar-recovery`（`24/24`）、`verify-26pillar-recovery`（`26/26`）、`verify-27pillar-recovery`（`27/27`）、`verify-28pillar-recovery`（`28/28`）与 `verify-29pillar-recovery`（`29/29`）全部原样通过。
- **硬件安全红线硬锁**：`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`isp_write_authorized = False`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`raw_firmware_bytes_leaked = 0`。

## 2. 交付文件清单（严格限定 6 个归属文件）

1. [realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py)：实现有界只读 donor 审计、Pillar 30A（6 场景）、Pillar 30B（6 场景）及 `30/30` 并发聚合器 [`evaluate_realhw_30pillar_recovery_master`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py#L1636-L1785)。
2. [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)：无遮蔽导出 Pillar 30 与 `evaluate_realhw_30pillar_recovery_master` / `verify_30pillar_recovery_suite`。
3. [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)：新增 CLI 子命令 `verify-proxy-coupled-hdmi-vault` 与 `verify-30pillar-recovery`（支持 `--force-clean-room` / `--clean-room`、`--json`、`--out`）。
4. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/outputs/fx3-recovery-adapter/README.md)：补齐 Phase 212 Pillar 30 与 `30/30` 里程碑恢复总控文档及 CLI 用法。
5. [test_realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/outputs/fx3-recovery-adapter/tests/test_realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py)：新增 **54 项**双模式快速单元测试（Group 0/A/B/C/D）。
6. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/reports/2026-11-15-phase212-realhw-30pillar-proxy-coupled-hdmi-only-vault-recovery/README.md)：本阶段中文技术验收报告。

## 3. 核心架构与实测事实 vs 建模边界

### 3.1 只读实机 Donor 锚点（实测事实，`O_RDONLY | O_NOFOLLOW | O_NONBLOCK`，`< 0.15s`）
[`inspect_phase212_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py#L692-L816) 对大镜像严格限制 `4096 B` `os.pread` 头部校验，对媒体/备份管理库执行完整 SHA-256 锚定（JSON 报告零原始固件字节泄漏）：
- `fx3-7.02-BODYDATA.DAT`：`811,876,768 B`，`\x89UFU\r\n\x1a\n` + `DATV/PROV/UDID`，4K SHA-256 `fc135914e0767d69...`。
- `FX3 Ver. 7.02 appFw.so`：`79,015,712 B`（ELF64 `EM_AARCH64`），4K SHA-256 `de3201c6615a5307...`。
- `FX3-CX95900_ALLLANG-Backup.bin`：`2,229,740 B`，`0xAAAAAAAA` 同步字 + `BK4\x00` + `ILME-FX3`，SHA-256 `bf3a9d851f9853fd...`。
- `libInfraMediaConfig.so`（`52,312 B`，导出 `InfraMediaConfig` / `GetMediaNum` / `Backup_sync_subsystem`，SHA-256 `483548d53dfbe941...`）、`libBackupManager.so`（`10,272 B`，导出 `BackupManager` / `SKData_Init` / `Backup_get_datasize`，SHA-256 `ef95ca41dadcad9a...`）及 `libbackup.so`（`14,232 B`，导出 `Backup` / `setting`，SHA-256 `6a3c5f6067620c00...`）。

### 3.2 Pillar 30A：`Px` 原子主+代理联动金库（状态机建模，6 场景）
- [`evaluate_proxy_coupled_vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py#L824-L1022) 跨 **Slot 1 与 Slot 2** 审计 `/M4ROOT/CLIP/`（`XAVC HS` / `XAVC S` / `XAVC S-I` `.MP4` + `*M01.XML`）与 `/M4ROOT/SUB/`（`*S03.MP4`：`XAVC HS HD` `1920x1080` 10-bit `16M`/`9M` HEVC 或 `XAVC S HD` `1280x720` 8-bit `6M` AVC）原子联动一致性。
- 严格校验 `Sony FX3 Ver. 7.02` Delete / Protect 双侧原子语义，fail-closed 拦截孤立 `SUB/`、带 `(Px)` 位但缺 `SUB/`、无 `(Px)` 位却残留 `SUB/`、主/代理只读保护属性不一致与单侧操作请求。
- 强制截断 `119.88p`/`100p` Normal、`>= 100fps`/`120fps` S&Q 及 `[Off(HDMI Only)]` 代理生成，并严禁机内直接回放 `SUB/` 代理片段假设。

### 3.3 Pillar 30B：`[Off(HDMI Only)]` 零内录卡互锁、HDMI Log `1080p` 降档与 `FocusMag × BrightMon`（状态机建模，6 场景）
- [`evaluate_hdmi_only_zero_card_and_interlocks`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h233-phase212-pillar30-30pillar-proxy-coupled-hdmi-only-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py#L1030-L1195) 拦截将 `[Rec. Media dur HDMI Output] = [Off(HDMI Only)]`（`[4K Output Set.(HDMI Only)]` `59.94p..24.00p 10bit`）误认为内录激活或用于 `PRE_BACKUP_TIER0` 的零卡隐患（`internal_card_recording_active == False`）。
- 校验 `[On]` 且 `RAW Output = Off` 时 `Log Shooting`（`Cine EI` / `Cine EI Quick` / `Flexible ISO`）与 `PPLUT1..4` 强制 HDMI `1080p` 降档；校验 `[HDMI Info. Display = On]` 熄灭机身 LCD 以及 `RAW Output = On` / `Off(HDMI Only)` 自动抑制 `[HDMI Info. Display]` 与 `[De-Squeeze]`。
- 校验 `Focus Magnifier`（电影仅 `x1.0`/`x4.0`、`Auto Magnifier in MF` 禁用、放大期间抑制 `Marker Display` 且锁定 `Bright Monitoring` 按键）与 `Bright Monitoring`（仅 `P/A/S/M + MF` 且强制 `[Setting Effect OFF]`）互斥护栏，同时确认 Stage-B 易失 `tmpfs` 覆盖层与 `Backup.bin` / `16/16` Tier-0 表面干净复位（`H0 == H3`）。

## 4. 验证记录（全量 `/usr/bin/python3 -B`）

- `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-proxy-coupled-hdmi-vault --json`：`VERIFIED_PILLAR30_PROXY_HDMI_ONLY_VAULT`（`LOCAL_DONOR_O_RDONLY` `suite_sha256=ea694279b3ae4a49...`；`--force-clean-room` `CLEAN_ROOM_SYNTHETIC` `4a882b1055f77a1c...`）。
- `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-30pillar-recovery --json`：`VERIFIED_30OF30_PILLAR_RECOVERY_MASTER`（`30/30`，`LOCAL_DONOR_O_RDONLY` `1.180s` `master_30pillar_sha256=d9cbb5dce40b89ea...`；`--force-clean-room` `0.855s` `ead7bbcc7469a95d...`）。
- `test_realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier.py`：`LOCAL_DONOR_O_RDONLY` **54/54 OK**（`8.675s`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` **54/54 OK**（`7.953s`）。
- `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`：`Clean-Room Audit: ALL GREEN in 0.04s`，零 `.pyc` 残留。
- `outputs/fx3-recovery-adapter/tests` 全量发现测试：`LOCAL_DONOR_O_RDONLY` **1377 项 OK (skipped=1)**（`112.791s`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` **1319 项 OK (skipped=16)**（`72.493s`），均全部通过。
