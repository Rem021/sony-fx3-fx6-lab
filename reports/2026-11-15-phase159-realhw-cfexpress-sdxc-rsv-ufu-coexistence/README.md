# Phase 159（H172）第 33 号统一固件审计器（`33/33`）交付报告：双槽 `CFexpress Type A (NVMe)` + `SDXC UHS-II (V90)` 介质桥接、`.RSV` 断电修复与官方 Sony `BODYDATA.DAT`（`\x89UFU`）升级共存防护

## 1. 结论先行

已在 [`outputs/fx3-firmware-lab/`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h172-phase159-cfexpress-sdxc-rsv-ufu-coexistence/outputs/fx3-firmware-lab) 完成第 **33 号统一固件审计器（`33/33`）** 的双模式实现、CLI 与 `audit-all` 集成及 48 项单元测试。所有本地 FX3 `v7.02` 与 FX6 `v6.01` Donor 二进制及 `fx3-7.02-BODYDATA.DAT` 均严格通过 `os.open(..., os.O_RDONLY)` + `mmap.ACCESS_READ` / 有界 `os.pread` 检查（`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`emmc_mutation_bytes = 0`、`calibration_mutation_bytes = 0`）。

---

## 2. 交付与修改文件清单（严格限定自有文件）

| 类型 | 文件路径 | 说明 |
| :--- | :--- | :--- |
| NEW | [`realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h172-phase159-cfexpress-sdxc-rsv-ufu-coexistence/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_auditor.py) | Phase 159 核心审计器、12 项 4 分类兼容矩阵与 4 支柱确定性评估器 |
| UPDATE | [`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h172-phase159-cfexpress-sdxc-rsv-ufu-coexistence/outputs/fx3-firmware-lab/fx3_firmware_lab/__init__.py) | 导出 Phase 159 全部公开常量、数据类、评估函数与报告序列化接口至 `__all__` |
| UPDATE | [`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h172-phase159-cfexpress-sdxc-rsv-ufu-coexistence/outputs/fx3-firmware-lab/fx3_firmware_lab/__main__.py) | 新增 CLI 子命令 `audit-realhw-cfexpress-sdxc-ufu` 并接入 `audit-all`（`33/33`） |
| UPDATE | [`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h172-phase159-cfexpress-sdxc-rsv-ufu-coexistence/outputs/fx3-firmware-lab/README.md) | 增补第 33 号审计器文档与 CLI 用法 |
| NEW | [`test_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h172-phase159-cfexpress-sdxc-rsv-ufu-coexistence/outputs/fx3-firmware-lab/tests/test_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence.py) | 48 项双模式单元测试（覆盖 4 支柱、`O_RDONLY` AST 静态检查与无裸字节泄漏检查） |
| NEW | [`reports/2026-11-15-phase159-realhw-cfexpress-sdxc-rsv-ufu-coexistence/README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/codex-h172-phase159-cfexpress-sdxc-rsv-ufu-coexistence/reports/2026-11-15-phase159-realhw-cfexpress-sdxc-rsv-ufu-coexistence/README.md) | 本 Phase 159 验收报告 |

---

## 3. 已实测验证的 `O_RDONLY` Donor 事实与四大支柱审计结果

### 3.1 实测只读 Donor 元数据（本地 `LOCAL_DONOR_VERIFIED` 模式单次审计 `0.617s`）
- **FX3 `v7.02` (`0x91030080`) 与 FX6 `v6.01` 媒体核心库**：
  - `appFw.so`：`79,015,712 B`（FX3）vs `50,520,424 B`（FX6），实测均命中 `MODEL_MEDIA_EJECTED_SLOT1/2`、`INFRA_NOTIFY_MEDIA_EJECT`、`VAL_system_mode_option_SYSTEM_MODE_OPTION_RECOVER_DB`；FX3 含 `/PRIVATE/M4ROOT/GENERAL/LUT`，FX6 含 `/PRIVATE/M4ROOT`、`/PRIVATE/XDROOT/GENERAL/LUT`、`/PRIVATE/XDROOT` 与 `TARGET_SLOT_FOR_REPAIR_SLOT_A/B`。
  - `libmpr.so`：`3,517,008 B`（`3,541` 导出 / `356` 导入，FX3）vs `28,921,824 B`（`4,271` 导出 / `497` 导入，FX6），实测共享 `exfat`、`/M4ROOT/MEDIAPRO.XML`、`.RSV`、`LOG_ID_VPG_MANAGER`、`_ZN3mpr12ExecEncCloseEPv`、`_ZN3mpr6RepairERKNS_13repairInParamE`、`_ZN3mpr19ProvisionalRepairM4EjbbRjRbRm`、`_ZN5MprIf7SalvageEmmN3MPR11SalvageTypeE`、`_ZN5MprIf22NotifyMediaCoverStatusEmb`、`_ZN5MprIf5EjectEm`、`_ZN5MprIf11ForcedEjectEm`；FX6 额外携带 `/XDROOT/Clip/`、`wfsEBSyncDirectoryOptimize skip! SDXC`、`MuxMxfSlvMain_Salvage`、`muxMp4Salvage`、`muxMxfSalvage`。
  - `libsencore.so`：`377,328 B`（FX3）vs `401,952 B`（FX6），导出/导入均严格保持 `355` / `130`，共享 `EXEC_MEDIA_FORMAT`、`EXEC_SLOT_SELECT`、`MPR_CMD_CHECK_MEDIA_IF`、`MPR_CMD_CHECK_MEDIA_FREE_SPACE`、`MPR_CMD_CHECK_MEDIA_SD_WP`、`MPR_CMD_GET_MEDIA_OVERCURRENT_STATUS`、`MPR_CMD_MEDIADETECT_STOP_INOUT`。
  - `cpapp-b.bin`：`15,980,568 B`（FX3）vs `17,952,816 B`（FX6），共享 `MSG_ID_INFRABB_SYS_SET_ACTIVESLOT`、`MSG_ID_INFRABB_SYS_SET_LAST_FRAME_POS_IN_ACTIVE_MEDIA`、`MSG_ID_INFRABB_VIDEO_SET_MEDIA_ERROR`、`TCUB_CMD_SET_TIMECODE_SET_ACTIVESLOT`、`ULOGIO_RECOVERY`。
  - `nflasha7` rootfs：`insmod_drv2`（`1,298 B`）按序加载 `mcmn_drv.ko`、`nvme-core.ko`、`nvme.ko`、`ms_drv.ko`、`mmc_drv.ko`、`sata_drv.ko`；`fstab`（`1,085 B`）将 `/dev/nflasha15` 只读挂载于 `/usr`（`ext2 ro,nodiratime,noatime,sync`）。
  - `libupdaterufp.so`：`22,768 B`（FX3）vs `18,672 B`（FX6），均保持 `19` 导出 / `43` 导入，含 `/BODYDATA.DAT`、`/dev/nflasha1`、`/setting/updater/dat4`、`/usr/bin/up.sh`。
- **官方 `fx3-7.02-BODYDATA.DAT` 有界读取实测（仅 `256 B` 头部 + `64 B` 尾部 `os.pread`）**：
  - 总长度 `811,876,768 B`：`0x0000` `\x89UFU\r\n\x1a\n`；`DATV`（`0x01000000`）；`PROV`（`0x01000000`）；`UDID`（`10` 项，含 FX3 USB PID `0x054c:0x0da0`、`0x054c:0x0da1`）；`FDAT` 起始偏移 `0x007C`、载荷 `811,876,624 B`；尾部 `\x00\x00\x00\x04DEND` + 4B CRC（`12 B`），精确吻合 `0x7c + 8 + 811,876,624 + 12 = 811,876,768 B`。

### 3.2 四大支柱与 12 项 4 分类兼容矩阵（模型 / 离线合同验证）
1. **Pillar 1（双混插槽位 `Slot A/B` 与 ExFAT 共存）**：`Slot A`（`/dev/nvme0n1p1` / `/dev/mmcblk1p1` -> `/mnt/sd`）与 `Slot B`（`/dev/nvme1n1p1` / `/dev/mmcblk2p1` -> `/mnt/sd2`）允许 `PRIVATE/M4ROOT/CLIP` 与 `XDROOT/Clip` 在 Stock FX3 <-> Stage-B FX6 切换时非破坏共存，阻断双系统切换自动格式化与任何 `/dev/nflasha*` / `/dev/cnflasha*` / `/dev/mmcblk0*` 挂载覆盖。
2. **Pillar 2（速度等级码率准入闸门）**：`XAVC S-I 4K 120p (S&Q)` / `4K 60p (600 Mbps)` 强制准入 `CFexpress Type A (VPG200/VPG400)` 或 `SDXC UHS-II V90`；`XAVC S 200M` 准入 `V60+`；`XAVC HS 150M` 准入 `V30+`；硬件 `SD_WP` 写保护、槽位过流及 `< 64 MiB` 剩余空间均提前拒绝录机，防止内核 I/O 阻塞与缓存溢出。
3. **Pillar 3（卡仓门 Hall/GPIO 中断冲刷与 `.RSV` 修复）**：在 `15.0 ms` 电容保持窗口内完成 `MPR ExecEncClose` FIFO 冲刷与卸载（`6.5 ms < 15.0 ms`）；若瞬间断电则触发 `.RSV` 回退路径，允许外部卡 `/mnt/sd*/*.RSV` 修复为 `.MP4` / `.MXF` 并更新 `MEDIAPRO.XML`，严格禁止任何 `< 4 KiB` 损坏切片或 `nflasha*` 写入。
4. **Pillar 4（`BODYDATA.DAT` 自动旁路与 `p1` 升级前 `H0 == H3` 净卸载门禁）**：
   - `evaluate_stage_a_bodydata_auto_bypass()` 证明：当 Slot A 或 Slot B 存在 `BODYDATA.DAT`（无论有效 `\x89UFU` 或损坏头部），Stage-A 均以 Fail-Closed 策略在 `< 100 us` 预算内中止 Stage-B 并回落至 100% 原厂 Stock FX3（`stage_b_blocked_on_bodydata_dat == True`）。
   - `evaluate_p1_official_update_clean_uninstall()` 证明：启动 Sony 官方 `p1` 升级器（`mode1..mode6`）前，必须完成 `p15:/usr` `.orig` 还原（`H0 == H3`、残留文件 `0`、`orig_backup_verified == True` 且电池电量 `>= 51%`），确保 `Sector 0` / `p2` / `p18` 与 `SPI-NOR` 零残留、零风险。
   - 12 项 4 分类矩阵分布：`NATIVE_PASSTHROUGH=5`、`SHIM_TRANSLATED=3`、`MASKED_ABSENT_HW=1`、`HARD_WRITE_PROTECTED=3`。

---

## 4. 离线与双模式测试实测结果

| 验证命令 | 模式 | 实测结果 | 耗时 |
| :--- | :--- | :--- | :--- |
| `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence.py -v` | 本地真实 Donor | `Ran 48 tests ... OK` | `1.183s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest outputs/fx3-firmware-lab/tests/test_realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence.py -v` | 强制 Clean-Room | `Ran 48 tests ... OK` | `0.606s` |
| `PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | 本地真实 Donor 全量 | `Ran 1114 tests ... OK` | `40.721s` |
| `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-firmware-lab /usr/bin/python3 -B -m unittest discover -s outputs/fx3-firmware-lab/tests -p "test_*.py"` | 强制 Clean-Room 全量 | `Ran 1114 tests ... OK (skipped=2)` | `20.872s` |
| `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | 仓库洁净与无字节码审计 | `CLEAN / ALL GREEN` | `0.88s` |

---

## 5. 尚未执行的真实物理 FX3 机身台架验证边界

以上结论均基于只读 Donor 静态审计与 Clean-Room/模型测试；以下真实硬件台架步骤**尚未在物理 FX3 机身上执行**：
1. 在真实 FX3 (`Ver. 7.02`) 双卡槽同时插入 `CFexpress Type A`（`VPG400`）与 `SDXC UHS-II V90`（及刻意插入 `V30` 卡负向用例），实测 Stock FX3 <-> Stage-B FX6 切换后原用户 `M4ROOT` 与 `XDROOT` 素材保留与录制准入提示；
2. 录制中模拟打开卡仓门开关及异常拔电生成 `.RSV` 片段，实机执行 `Recover Image DB` 并核验 `.MP4/.MXF` 回放完整性；
3. 将测试卡根目录写入官方 `BODYDATA.DAT` 并通过物理开机实测 Stage-A 是否在 `< 100 us` 旁路 Stage-B、直接进入原厂 FX3 用户态（严禁在未执行 `H0 == H3` 净卸载还原 `p15:/usr` `.orig` 前触发官方刷写）。
