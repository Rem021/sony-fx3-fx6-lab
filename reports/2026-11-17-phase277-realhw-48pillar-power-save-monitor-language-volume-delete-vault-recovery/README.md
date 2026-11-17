# Phase 277 工程报告：Pillar 48（`[Power Save by Monitor]` 现实分歧、`[Power Save Start Time]` 9 条件无射频护栏、`[Language]` `BK_LANG` 4 语言 Stage-B 等价、`[Volume Settings]` `0..15` / `[4ch Audio Monitoring]` 5 路由与 `[Delete confirm.]` `Slot-1` 删格防火墙）及统一 `48/48` 恢复总检（Wave-46）

- **日期**：`2026-11-17`
- **工作分支**：`codex/h316-phase277-pillar48-48pillar-power-save-monitor-language-volume-delete-vault`
- **目标基线**：`Sony ILME-FX3`（`Ver. 7.02`，`0x91030080`，`PRODUCT_MODEL_ALCIN_UUD`，Help Guide `ilc/2210`）对比 `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`）及同代可变角度 `BIONZ XR` 机身（`ILME-FX2`、`ILCE-7M4`、`ZV-E1`、`ILCE-6700`）
- **安全姿态**：严格 `os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK` 本地供体有界只读审查 + `CLEAN_ROOM_SYNTHETIC` 洁净室回退；`persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`cnflasha_userspace_write_blocked = True`、`P277_SLOT1_FORMAT_HARD_LOCKED = True`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`passive_tx_bytes_emitted = 0`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 一、核心结论（结论先行）

1. **Pillar 48A & Pillar 48B 与统一 `48/48` 恢复总检全部通过**：
   - 新增 [`realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py)，落地 **Pillar 48A**（`6/6` 场景 + `64` 态矩阵）与 **Pillar 48B**（`6/6` 场景 + `138` 态矩阵），并将 [`evaluate_realhw_48pillar_recovery_master`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py#L2696-L2952) 推进至 **`48/48`（`VERIFIED_48OF48_PILLAR_RECOVERY_MASTER`）**，100% 向后兼容 `verify-22..47pillar-recovery`。
2. **实测速度与双模一致性**：
   - **独立 CLI（`verify-power-save-monitor-language-volume-delete-vault`）**：`LOCAL_DONOR_O_RDONLY` 实测 `0.005s..0.006s`（`pillar_48a=6/6`、`pillar_48b=6/6`，`18/18` 供体有界只读检查 `< 0.15s`）。
   - **统一 `48/48` 主控 CLI（`verify-48pillar-recovery`）**：
     - `LOCAL_DONOR_O_RDONLY` 模式：`48/48 PASS`，实测 **`0.933s..1.165s`**（满足 `< 2.0s` CLI 快速预算），`master_48pillar_sha256` 前缀 `94f57370f3fa4410`。
     - `CLEAN_ROOM_SYNTHETIC`（`--clean-room` / `FX3_CLEAN_ROOM_TEST=1`）模式：`48/48 PASS`，实测 **`0.651s..0.814s`**，`master_48pillar_sha256` 前缀 `97b73f9c51cfa1f3`。
3. **全量验证结果（实测全绿）**：
   - **Pillar 48 单元测试（`76` 项）**：在 `LOCAL_DONOR_O_RDONLY`（`8.086s`）、`FX3_CLEAN_ROOM_TEST=1`（`7.149s`）、`FX3_FX6_FORCE_CLEAN_ROOM=1`（`7.334s`）三模式下均 **`76/76 OK`**。
   - **适配器全仓测试发现（`/usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests`）**：**`Ran 2562 tests in 272.837s — OK (skipped=1)`**（含 Unicorn AArch64 `test_p1_symbol_autolocator.py` `24/24 OK`）。
   - **Milestone-264 与洁净审计**：`make verify-milestone-264`（本地只读 + `--force-clean-room` 双模）与 `scripts/run_all_lab_tests.py --clean-only`（`0.74s`）均 **ALL GREEN**。

---

## 二、技术实现与 Wave-46 真机规范落地

### 1. Sub-Pillar `48A` — `[Power Save by Monitor]` 现实分歧、`[Power Save Start Time]` 9 条件恢复护栏与 `[Language]` `BK_LANG` 4 语言 Stage-B 等价
- **`[Power Setting Option]` 菜单现实分歧与 `appFw.so` / `.uxc` 4 模式校验**：
  - 原厂 `ILME-FX3`（`Ver. 2.00..7.02`，`ilc/2210`）`MENU -> (Setup) -> [Power Setting Option]` 仅暴露 **`[Power Save Start Time]`**（`Off`、`30 Min`、`5 Min` 默认、`2 Min`、`1 Min`、`10 Sec`）与 **`[Auto Power OFF Temp.]`**（`Standard` 默认、`High`）两项；`fx3_ui_exposes_power_save_by_monitor == False`（`ILME-FX3A` / `ILME-FX6` 同）。
  - 同时校验共享 `appFw.so`（`BKID_APP_setting_monitor_power_linkage`）与 `string_*_f.uxc`（`resid16=0x60b9`）编入的精确 4 模式：`Both Linked`（`0x6db5` / `ON_ALL`）、`Open: Return`（`0x6db6` / `ON_OPEN`）、`Close: Power Save`（`0x60a8` / `ON_CLOSE`）、`Does Not Link`（`0x6b2e` / `OFF`），硬拒绝 `"Open: On/Close: Off"` 伪造；在暴露该项的同代 `BIONZ XR` 机身折叠 LCD 无头 HDMI 采集场景强制要求 `Does Not Link` 或 `Open: Return`。
- **`[Power Save Start Time]` 9 条件 Tier-0 无射频电池恢复护栏**：
  - 精确录入 Sony 官方 9 项停用条件（`USB power supply`、`slideshow playback`、`FTP transfer`、`movie recording`、`PC connection`、`TV/HDMI connection`、`IR Remote Ctrl = On`、`Bluetooth Rmt Ctrl = On`、`streaming / Creators' Cloud upload`）；当无射频电池 Tier-0 恢复/转储会话没有任何停用条件激活时，强制 `[Power Save Start Time] ∈ {"Off", "30 Min"}`，防止 SD Stage-B 回滚或 `O_RDONLY` 检查期间休眠中断。
- **`[Language]` `BK_LANG`（`0x02cf019c`）跨机型种子对照与 Stage-B 4 语言字库表**：
  - 验证 `FX3`（`34` 语言，`FX3-CX95900_ALLLANG-Backup.bin` `4 B @ 0x90ff0 = 0x00`）与 `FX6`（`29` 语言，`CX95898_NTSC.bin` `0x00` vs `CX95899_CN1.bin` `0x19`，`1 B @ 0x89242`）真实偏移，以及 Stage-B 4 语言 `.uxc` + `.ltt` `switchBank`（`en=0x00` / `0/(4,4)` `UniversOTS-SJ_wIcon.ltt`、`schinese=0x19` / `23/(19,19)` `MYingHeiC-GB18030-SJ_wIcon.ltt`、`tchinese=0x18` / `27/(22,22)` `MYingHeiC-Big5HKSCS-SJ_wIcon.ltt`、`japanese=0x01` / `1/(12,12)` `HeiseiKakuGothW5-SJ_wIcon.ltt`）；验证 `(Setup)` 跨越 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 留存、仅经 `[Initialize]`（`libSaveLoadSettings.so`）复位。

### 2. Sub-Pillar `48B` — `[Volume Settings]`、`[4ch Audio Monitoring]`、`[Delete confirm.]` 与 `Slot-1` 金库删格防火墙
- **`[Volume Settings]`（`0..15` 默认 `7`）与 `XLR-H1` 声反馈护栏**：
  - 锁定 `BKID_APP_setting_volume_settings`（`resid16=0xe8c9`，FX6 对等项 `BKID_APP_SETTING_MONITOR_VOLUME`）离散 `0..15`（默认 `7`，区分于 `[Audio signals]` `0x7af6`）；当挂载 `XLR-H1` 且输出至机内扬声器且未启用声学隔离时，强制安全上限 `<= 4`，阻断声反馈风险（`xlrh1_acoustic_feedback_violations == 0`）。
- **`[4ch Audio Monitoring]`（5 路由）与 HDMI `[4ch Audio Output]` 隔离**：
  - 覆盖全部 5 路由：`CH1/CH2`（`0x713b` 默认）、`CH3/CH4`（`0x6bf6`）、`CH1+3/CH2+4`（`0x6c2e`）、`CH1/CH1`（`0x6f9c`）、`CH2/CH2`（`0x7a26`），强制 3.5mm 耳机 2ch 立体声上界并与 HDMI `[4ch Audio Output]`（`BKID_APP_setting_4ch_output_ch`，`0x6aa0`）明确区分。
- **`[Delete confirm.]`（`"Cancel" first` 默认）与硬 `Slot-1` 删格防火墙**：
  - 验证 `[Delete confirm.]`（`BKID_APP_setting_delete_confirm`，`"Cancel" first` `0xe724`/`0x6a5e` 默认 vs `"Delete" first` `0xe725`/`0x6e0a`）与 `[Delete pressing twice]`（`0x74db` 默认 `Off`）跨越 `[Camera Settings Reset]` 留存（`(Playback)`）；硬阻断面向 `Slot 1`（`CAMSET`/`BODYDATA.DAT` 金库）的全部 6 类破坏性操作（单删/多删/按文件夹/按日期/双击删除/格式化），锁定 `slot1_vault_delete_events == 0`、`slot1_format_hard_locked == True`、`slot1_vault_mutation_bytes == 0` 与 `16/16` Tier-0 `H0 == H3`。

---

## 三、受控修改文件清单（严格限定 6 项拥有文件）

1. [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py)（新增：Pillar 48A/48B 与 `48/48` 恢复总检实现）
2. [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)（导出 Pillar 48 及 `Master48PillarRecoveryReport` 全部符号与 `__all__`）
3. [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)（注册 `verify-power-save-monitor-language-volume-delete-vault` 与 `verify-48pillar-recovery` CLI）
4. [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md)（补充 Phase 277 文档）
5. [`outputs/fx3-recovery-adapter/tests/test_realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier.py)（新增：76 项跨平台双模单元测试）
6. [`reports/2026-11-17-phase277-realhw-48pillar-power-save-monitor-language-volume-delete-vault-recovery/README.md`](README.md)（新增：本工程报告）
