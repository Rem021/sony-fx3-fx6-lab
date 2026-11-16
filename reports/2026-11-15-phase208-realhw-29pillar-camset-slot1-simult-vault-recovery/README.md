# Phase 208（Task H229）：实机 Pillar 29 Slot-1 `CAMSET` 双介质金库、`BIG6` 零 e-ND 总线护栏、双卡 `[Auto Switch Media = Off]` 严格冗余与 29/29 统一恢复总控报告

## 1. 结论先行

基于已合入的 **Phase 198 (`verify-28pillar-recovery`)** 与索尼官方实机情报 Wave-26（[Wave-26 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/reports/2026-11-15-global-sony-wave26-big6-home-aperture-nd-camset-slot1-path-vmcbncm1-tcin-only-intel/README.md)）及 Wave-27（[Wave-27 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/reports/2026-11-15-global-sony-wave27-desqueeze-165x-4locks-external-focusmap-150fps-simult-autoswitch-shocklesswb-intel/README.md)），已在 `outputs/fx3-recovery-adapter/` 内闭环实现 **Pillar 29 (`realhw_29pillar_camset_slot1_simult_vault_verifier`)** 与 **29 支柱统一恢复总控 (`evaluate_29pillar_recovery_master` / `verify-29pillar-recovery`)**：

- **统一总控达标**：`verify-29pillar-recovery` 在本地只读供体模式（`LOCAL_DONOR_O_RDONLY`，实测约 `1.00s`）与离线洁净室模式（`CLEAN_ROOM_SYNTHETIC`，实测约 `0.74s`）下均达成 `29/29`（`VERIFIED_29OF29_PILLAR_RECOVERY_MASTER`），远低于 `< 2.5s` 标称预算与 `< 6.0s` 测试并发上限。
- **向下兼容 100% 无损**：`verify-22pillar-recovery`（`22/22`）、`verify-24pillar-recovery`（`24/24`）、`verify-26pillar-recovery`（`26/26`）、`verify-27pillar-recovery`（`27/27`）与 `verify-28pillar-recovery`（`28/28`）全部原样通过。
- **硬件安全红线硬锁**：`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`。

## 2. 交付文件清单（严格限定 6 个归属文件）

1. [realhw_29pillar_camset_slot1_simult_vault_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_29pillar_camset_slot1_simult_vault_verifier.py)：实现只读 donor 审计、Pillar 29A（6 场景）、Pillar 29B（6 场景）及 `29/29` 并发聚合器 [`evaluate_29pillar_recovery_master`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_29pillar_camset_slot1_simult_vault_verifier.py#L1597-L1772)。
2. [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)：无遮蔽导出 Pillar 29 与 `evaluate_29pillar_recovery_master` / `verify_29pillar_recovery_suite`。
3. [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)：新增 CLI 子命令 `verify-camset-simult-vault` 与 `verify-29pillar-recovery`（支持 `--force-clean-room` / `--clean-room`、`--json`、`--out`）。
4. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/outputs/fx3-recovery-adapter/README.md)：补齐 Phase 208 Pillar 29 与 `29/29` 恢复总控文档及 CLI 用法。
5. [test_realhw_29pillar_camset_slot1_simult_vault_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/outputs/fx3-recovery-adapter/tests/test_realhw_29pillar_camset_slot1_simult_vault_verifier.py)：新增 **52 项**双模式快速单元测试（Group 0/A/B/C/D）。
6. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/reports/2026-11-15-phase208-realhw-29pillar-camset-slot1-simult-vault-recovery/README.md)：本阶段中文技术验收报告。

## 3. 核心架构与实测事实 vs 建模边界

### 3.1 只读实机 Donor 锚点（实测事实，`O_RDONLY | O_NOFOLLOW | O_NONBLOCK`）
[`inspect_phase208_donors_readonly`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_29pillar_camset_slot1_simult_vault_verifier.py#L640-L931) 对大镜像严格限制 `4096 B` `os.pread` 头部校验，对核心存储介质配置与备份管理库执行完整 SHA-256 锚定（JSON 报告零原始固件字节泄漏）：
- `fx3-7.02-BODYDATA.DAT`：`811,876,768 B`，`\x89UFU\r\n\x1a\n` + `DATV/PROV/UDID`，4K SHA-256 `fc135914e0767d69...`。
- `nflasha8/cpapp-b.bin`：`15,980,568 B`，ARM 异常向量 `04 10 9f e5`，4K SHA-256 `452c9e4e05fc1942...`（锚定 `ILME-FX3` `CP` 总线无物理内置电子 ND 执行器）。
- `FX3 Ver. 7.02 appFw.so`：`79,015,712 B`（ELF64 `EM_AARCH64`），4K SHA-256 `de3201c6615a5307...`。
- `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，`BK4\x00` + `0xAAAAAAAA` + `ILME-FX3`，SHA-256 `bf3a9d85...`）、`libInfraMediaConfig.so`（`52,312 B`，导出 `InfraMediaConfig` / `GetMediaNum` / `Backup_sync_subsystem`，SHA-256 `483548d5...`）及 `libBackupManager.so`（`10,272 B`，导出 `BackupManager` / `SKData_Init` / `Backup_get_datasize`，SHA-256 `ef95ca41...`）。

### 3.2 Pillar 29A：仅限 Slot-1 `CAMSET01..10.DAT` 双介质金库与 `BIG6` 零 e-ND 总线保护（状态机建模，6 场景）
- [`evaluate_slot1_camset_and_big6_end_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_29pillar_camset_slot1_simult_vault_verifier.py#L939-L1053) 强制仅允许 **Slot 1** 读写 `<= 10` 个 `CAMSET01.DAT..CAMSET10.DAT`（拦截 `Slot 2`、`>10` 档案与 `MR` 模式，并排除 `WB Custom 1/2/3`、`FTP`、流媒体、IP/证书、日期时间等机器绑定项）；严格执行 **SDXC**（`/PRIVATE/SONY/SETTING/FX3/CAMSET`）与 **CFexpress Type A**（`/SONY/SETTING/FX3/CAMSET`）根目录分裂；拦截 `FX3A`/`FX6` 跨机型 `.DAT` 混入并将 Stage-B `FX6` 配置隔离于 tmpfs `/tmp/fx6_camset_overlay`；同时强制 `BIG6` 左下角 `[Aperture / ND Filter]` 在 FX3 `CP` 总线上保持 `e_nd_actuator_tx_count == 0`。

### 3.3 Pillar 29B：双卡 `[Simult. + Auto Switch = Off]` 严格冗余、`VMC-BNCM1` 机身 `TC IN` 与 `1.65x` 净冷回退（状态机建模，6 场景）
- [`evaluate_simult_autoswitch_tcin_and_desqueeze_vault`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h229-phase208-pillar29-29pillar-camset-slot1-simult-vault-recovery/outputs/fx3-recovery-adapter/fx3_recovery/realhw_29pillar_camset_slot1_simult_vault_verifier.py#L1217-L1347) 强制双卡严格金库冗余下 `[Auto Switch Media] = Off`（防止 `Ver. 2.0+` 单卡写满后静默退化为单卡续录）；拦截 `VMC-BNCM1` 误插 `XLR-H1` 手柄 Micro-USB 口及反向驱动 BNC `TC OUT`（`EOPNOTSUPP`，仅走 Type-A HDMI 数字 `TC OUT`）；校验 `[De-Squeeze Display]` `1.6x == 1.65` 倍精确水平拉伸与四项硬件强锁（`MF / Wide / SteadyShot Off / Face Priority Off`）、无内置菜单的外置 `M&C Focus Map`（`< 150fps`）及 `[Shockless WB]` `C.Temp./Filter` 即时旁路，确保冷启动回到 Stock `7.02` 后 `p2:/setting` `16/16 H0 == H3`。

## 4. 验证记录（全量 `/usr/bin/python3 -B`）

- `PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m fx3_recovery verify-29pillar-recovery --json`：`VERIFIED_29OF29_PILLAR_RECOVERY_MASTER`（`29/29`，`LOCAL_DONOR_O_RDONLY` `master_29pillar_sha256=32c8e80109db4107...`；`--force-clean-room` 下 `99574f9d65304247...`）。
- `test_realhw_29pillar_camset_slot1_simult_vault_verifier.py`：`LOCAL_DONOR_O_RDONLY` **52/52 OK**（`8.18s`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` **52 ran (51 OK, 1 skipped)**（`8.48s`）。
- `outputs/fx3-recovery-adapter/tests` 全量发现测试（`LOCAL_DONOR_O_RDONLY` **1323 项 OK (skipped=1)**，`FX3_FX6_FORCE_CLEAN_ROOM=1` **1265 项 OK (skipped=16)**）与 `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`（`ALL GREEN in 2.18s`）：全部通过，零 `.pyc` 残留。
