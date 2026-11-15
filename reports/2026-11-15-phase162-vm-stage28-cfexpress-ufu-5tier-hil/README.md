# Phase 162（VM Stage 28，`28/28`）：真机双槽 `CFexpress Type A / SDXC V90` 热切换、`.RSV` 掉电抢救、官方 `BODYDATA.DAT`（`\x89UFU`）`<100 µs` 自动旁路与五级不可变砖恢复 HIL 协同仿真报告

- **任务编号**：`H175 / Phase 162 (VM Stage 28, 28/28)`
- **目标主线**：物理 Sony `ILME-FX3`（`Ver. 7.02`，Model ID `0x91030080`，`CXD90057` + `CXD90058`）双槽存储与官方固件更新共存全生命周期及五级不可变砖恢复 HIL 协同仿真
- **双模式摘要**：
  - `LOCAL_DONOR_RDONLY`：Stage 28 单阶段 `audit_digest_sha256[:12] = 1fd3a75557e6`（`14` 份本地 `O_RDONLY` 供体：12 核心供体 + 2 份 `<= 4096 B` 有界 `BODYDATA.DAT` 头部）；`28/28` 全套协同仿真 `digest = b9ac8319c574`（耗时 `1.820 s < 2.5 s`）。
  - `CLEAN_ROOM_SYNTHETIC`（`FX3_FX6_FORCE_CLEAN_ROOM=1`）：Stage 28 单阶段 `audit_digest_sha256[:12] = 5ae48c73b5e0`（`12` 份合成核心供体 + 2 份有界 UFU 头部）；`28/28` 全套协同仿真 `digest = b4d24f5d6dd3`（耗时 `0.454 s < 1.1 s`）。
- **安全红线**：`p8_cp_mutation_forbidden = True`、`cp_mutation_bytes = 0`、`persistent_emmc_writes_authorized = False`、`emmc_nflasha_write_count = 0`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`user_media_clips_intact = True`、`rsv_orphan_count = 0`。

## 1. 修改与交付文件清单（严格限定于 Owned Files）

| 序号 | 文件 | 职责 |
| :--- | :--- | :--- |
| 1 | [realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py) | Phase 162 Stage 28 协同仿真模块（`O_RDONLY` 供体与 `<=4 KiB` `BODYDATA.DAT` 审计 + 四大 HIL 支柱 A–D + Clean-Room 回退） |
| 2 | [fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py#L1646-L1694) | 接入 [`run_stage28_realhw_cfexpress_ufu_5tier_hil`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py#L1646-L1694) 与 `--skip-phase162`，推进全套至 `28/28` |
| 3 | [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/README.md#L933-L967) | 增补 `outputs/fx3-vm/` Phase 162（Stage 28）CLI 命令与红线说明 |
| 4 | [test_realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/tests/test_realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py) | 46 项双模单元测试（供体 `O_RDONLY`、有界 4 KiB 头部、Pillar A–D、28/28 总控与耗时/卫生门禁） |
| 5 | [test_realhw_imx510_color_and_network_usb_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/tests/test_realhw_imx510_color_and_network_usb_coemulator.py#L575-L664) | 放宽 Stage 27 对总阶段数的 `== 27` 硬编码断言为 `assertGreaterEqual(..., 27)` 以兼容 `28/28` |
| 6 | [Phase 162 README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/reports/2026-11-15-phase162-vm-stage28-cfexpress-ufu-5tier-hil/README.md) | 本期结项报告 |

## 2. 实测事实与未执行真机边界（严格区分）

### 2.1 `O_RDONLY` 本地 Donor 实测与 Python HIL 仿真事实

通过 [`inspect_phase162_donors`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py#L969) 严格经 `os.open(..., os.O_RDONLY)` + `mmap.ACCESS_READ` 对本地 FX3 `7.02` 与 FX6 `6.01` BYOF 镜像执行零写入检查（JSON 零原始固件字节）：

- **12 份核心供体与 2 份有界 UFU 头部实测指标（`O_RDONLY`）**：
  - `libmpr.so`：FX3 `3,517,008 B`（`3,541` exp / `356` imp）vs FX6 `28,921,824 B`（`4,271` exp / `497` imp），双机含 `PrepareRelayMedia`、`ChangeRecordingMedia`、`gp_evtRecoveryStartedFunc`、`gp_evtRecoveryFinishedFunc`、`/M4ROOT/MEDIAPRO.XML` 与 `.RSV`；FX6 另含 `XDROOT`。
  - `libsencore.so`：FX3 `377,328 B` vs FX6 `401,952 B`（均 `355` exp / `130` imp），双机含 `MPR_CMD_CHECK_MEDIA_*`、`MPR_CMD_MEDIADETECT_STOP_INOUT` 与 `JIRITSU_COMPARE_MEDIA`。
  - `im.elf`：FX3 与 FX6 均为 `40,920 B`（`11` exp / `85` imp，零差异 ABI），含 `/proc/udm/upm_bootmode`、`/dev/nflasha2` 与 `IMDB_find_target_bit`。
  - `loader_nor.bin`：FX3 `101,888 B`（含 `need_to_escape:`）vs FX6 `92,448 B`（`0750_nor_loader/loader_nor.tar` 内置），共享 `updater`、`adjust`、`LDR:CP_ESCAPE`、`LDR:cpapp-b.bin` 与 `ospi_load_dgu_mis`；`cpapp-b.bin`（`15,980,568 B` vs `17,952,816 B`）与 `Backup.bin`（`BK4\x00`，`819` vs `840` 子系统）。
  - 可选本地 `BODYDATA.DAT` 严格有界读取（`_read_bounded_rdonly(..., 4096)`，不读全量 `811 MiB`）：FX3 `7.02`（`811,876,768 B`，实读 `4,096 B`）解析出 `\x89UFU\r\n\x1a\n`、`DATV=1`、`PROV=1`、`UDID` 含 `054c:0da1`（`fdat_offset=124`）；FX6 `6.01`（`847,081,840 B`，实读 `4,096 B`）`UDID` 含 `054c:0d21`（不含 `054c:0da1`，`fdat_offset=76`）。
- **四大 HIL 协同仿真支柱（Stage 28）**：
  - **Pillar A**（[`evaluate_pillar_a_cfexpress_relay_and_card_door`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py#L1460)）：`XAVC S-I 4K 120p 600 Mbps` 准入 `CFexpress Type A` / `SDXC V90` 并拒绝 `V30`；仿真 `Slot A -> Slot B` 零丢帧接力与卡门 Hall/GPIO 冲刷至 `mpr_fifo_residual_bytes == 0`，跨双启动保持 `M4ROOT`/`XDROOT` 用户素材完整。
  - **Pillar B**（[`evaluate_pillar_b_rsv_clip_salvage`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py#L1567)）：仿真断电拔电池遗留 `C0001.RSV` 后的安全 ExFAT 抢救（`.RSV -> .MP4/.MXF`），`rsv_orphan_count == 0` 且 `emmc_nflasha_write_count == 0`，损坏容器 fail-closed 拦截。
  - **Pillar C**（[`evaluate_pillar_c_bodydata_ufu_coexistence`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py#L1747)）：卡片带 `/BODYDATA.DAT` 时 Stage-A 于 `38.5 µs < 100 µs` 自动旁路 Stage-B 至原厂 FX3 `7.02`；`H0 != H3` 时硬阻断 `p1` 升级器；fail-closed 拦截 `ILME-FX30`/`ILCE-7SM3`/`ILME-FX6` 跨机型 UFU 包。
  - **Pillar D**（[`evaluate_pillar_d_5tier_unbrickable_recovery`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h175-phase162-vm-stage28-cfexpress-ufu-5tier-hil/outputs/fx3-vm/realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py#L1960)）：覆盖 `Tier-1..Tier-5` 逐级恢复演练（`5/5` 全部通过），硬锁 `el3_payload_transmit_authorized == False`、`spi_nor_write_authorized == False`、`persistent_emmc_writes_authorized == False`。

### 2.2 尚未在真实物理 ILME-FX3 相机上执行的测试（明确未测项）

以下项目属于物理主机/相机实机台架动作，**本次未在真实物理 ILME-FX3 机身通电执行（`UNEXECUTED ON PHYSICAL FX3 CAMERA`）**：
1. 真实物理机身槽 A `CFexpress Type A` + 槽 B `SDXC V90` 在 `XAVC S-I 4K 120p` 实拍过程中的接力切换、写入中开卡门物理卸载及断电拔电池后重启 `Recover Image DB` 实测。
2. 真实物理机身插卡携带官方 `BODYDATA.DAT` 时的示波器实测 Stage-A 旁路时延与实机 `p15:/usr` `.orig` 卸载后进入官方 `Ver. 7.02+` 更新流程。
3. 物理台架 `1.8V UART`、`Multi-USB 054C:0DA1/0336` 与离线 `CID` 匹配 `eMMC ISP` 恢复接线操作。

## 3. 定向与全量验证结果

| 验证命令 | 模式 | 结果 |
| :--- | :--- | :--- |
| `PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py -v` | Local Donor | **46/46 PASS** |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest outputs/fx3-vm/tests/test_realhw_cfexpress_ufu_and_5tier_recovery_coemulator.py -v` | Clean-Room | **45 PASS / 1 SKIP**（跳过本地 donor 专属字节校验） |
| `PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | Local Donor 全量 | **992/992 PASS**（`65.569s`） |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-vm /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm/tests -p "test_*.py"` | Clean-Room 全量 | **992 tests PASS (3 skipped)**（`63.381s`） |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 全仓 Clean-Room & 卫生门禁 | **ALL GREEN**（`1.71s`） |
| `/usr/bin/python3 -B outputs/fx3-vm/fx3_vm_coemulation_suite.py --summary`（双模式） | `28/28` 全板套件 | Local `1.820s < 2.5s` / Clean-Room `0.454s < 1.1s` **PASS** |
