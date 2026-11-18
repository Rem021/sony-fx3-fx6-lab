# Phase 282 工程报告：Pillar 49（`[USB Connection Mode]` 4 模式与休眠 `NOUVC`、`USB PD` 物理隔离、 `[HDMI Info. Display]` LCD 熄屏/`1080` 钳位、`[Protect]` vs `[Format]` `Slot-1` 双层防线、`[Reset Network Set.]` 自动重启与零射频顺序）及统一 `49/49` 恢复总检（Wave-47）

- **日期**：`2026-11-17`
- **工作分支**：`codex/h323-phase282-pillar49-49pillar-usb-mode-hdmi-info-protect-network-reset-vault`
- **权威基准**：[Wave-47 真实硬件情报报告](../2026-11-17-global-sony-wave47-usb-connection-mode-hdmi-info-protect-reset-network-intel/README.md) · Sony `ILME-FX3`（`Ver. 7.02`，`0x91030080`，`PRODUCT_MODEL_ALCIN_UUD`，Help Guide `ilc/2210`）对比 `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`）
- **硬件安全姿态**：严格 `os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK` 18 份本地供体有界只读审查 + `CLEAN_ROOM_SYNTHETIC` 洁净室回退；`persistent_emmc_writes_authorized = False`、`hardware_live_attachment_authorized = False`、`cnflasha_userspace_write_blocked = True`、`P282_SLOT1_FORMAT_HARD_LOCKED = True`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`passive_tx_bytes_emitted = 0`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`raw_firmware_bytes_leaked = 0`。

---

## 一、核心结论（结论先行）

1. **Pillar 49A & Pillar 49B 与统一 `49/49` 恢复总检全部通过**：
   - 新增 [realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py)，完整落地 **Pillar 49A**（`6/6` 场景 + `44` 态矩阵）与 **Pillar 49B**（`6/6` 场景 + `44` 态矩阵），并将 [`evaluate_realhw_49pillar_recovery_master`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py#L2823-L3154) 并发聚合推进至 **`49/49`（`VERIFIED_49OF49_PILLAR_RECOVERY_MASTER`）**，100% 向后兼容 Pillars `1..48`。
2. **实测速度与双模一致性**：
   - **独立 CLI（`verify-usb-mode-hdmi-info-protect-network-reset-vault`）**：`LOCAL_DONOR_O_RDONLY` 实测 `0.003454s`（`pillar_49a = 6/6`、`pillar_49b = 6/6`，`18/18` 供体有界只读检查耗时 `0.003124s` < `0.15s`）。
   - **统一 `49/49` 主控 CLI（`verify-49pillar-recovery`）**：
     - `LOCAL_DONOR_O_RDONLY` 模式：`49/49 PASS`，实测 **`1.070942s`**（满足 `< 2.0s` CLI 快速预算），`master_49pillar_sha256` 前缀 `7fb60aa1ab1302e2`。
     - `CLEAN_ROOM_SYNTHETIC`（`--clean-room` / `FX3_CLEAN_ROOM_TEST=1`）模式：`49/49 PASS`，实测 **`0.695232s`**（`< 2.0s`），`master_49pillar_sha256` 前缀 `6c4879e6c04e551a`。
3. **全量实测验证结果（ALL GREEN）**：
   - **Pillar 49 单元测试（`76` 项）**：
     - `LOCAL_DONOR_O_RDONLY`（`python3 -B`）：`76/76 OK`（`8.462s`）
     - `FX3_CLEAN_ROOM_TEST=1`（`python3 -B`）：`76/76 OK`（`8.195s`）
     - `FX3_FX6_FORCE_CLEAN_ROOM=1`（`python3 -B`）：`76/76 OK`（`8.006s`）
     - Python 3.9（`/usr/bin/python3 -B`）：`76/76 OK`（`9.724s`）
   - **适配器全仓测试发现（`/usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests`）**：**`Ran 2638 tests in 263.941s — OK (skipped=1)`**（含 Unicorn AArch64 `test_p1_symbol_autolocator.py` `24/24 OK` 与本次新增 76 项测试）。
   - **Milestone-264 与洁净审计**：`make verify-milestone-264`（本地只读 + `--force-clean-room` 双模 `6/6`、`recovery=44/44`、`gate102=99/102`、`vm_stages=55/55`、`qemu=28/28(84/84)`）与 `PYTHONDONTWRITEBYTECODE=1 python3 -B scripts/run_all_lab_tests.py --clean-only`（`ALL GREEN in 1.99s`）均通过。

---

## 二、技术实现与 Wave-47 真机规范落地

### 1. Sub-Pillar `49A` — `[USB Connection Mode]` 4 模式与 `NOUVC` 分歧、数据隔离 `USB PD` 供电护栏及 `[HDMI Info. Display]` 清洁输出护栏
实现入口：[`evaluate_usb_mode_pd_guard_and_hdmi_info_vault`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py#L1773-L2127)
- **4 模式暴露与休眠 `NOUVC` 边界**：
  - 锁定原厂 `ILME-FX3 Ver. 7.02` `(Setup) -> [USB] -> [USB Connection Mode]`（`BKID_APP_setting_usb_connection_method`，`_f.uxc` `0x69a2`）仅暴露 **4** 种模式：`Sel. When Connect`（`0x7738` 默认）、`MassStorage(MSC)`（`0x6c54`，`054C:0DA1`，`appFw.so` 内部标记 `USB_CONNECTION_METHOD_MASS_STRAGE`）、`MTP`（`.uxc` `0xe24b`）、`Remote Shoot (PC Remote)`（`_f.uxc` `0x60aa`）。
  - 验证共享固件内休眠 `usb_f_uvc.ko`（`78,840 B`）与 `_f.uxc` `0x7399` / `_g.uxc` `0x63f7` `[USB Streaming]` 词条在 `ILME-FX3` UI 保持未暴露（`P282_FX3_UI_EXPOSES_USB_STREAMING == False`，对比 `ILME-FX6` 启用 `ProCam UVC` 与 `USB Tethering` `0x29c9`），严禁伪造 `USB Streaming` 菜单。
- **空气隔离 Tier-0 数据阻断与 `USB PD` 仅供电规则**：
  - 阻断 Tier-0 备份/回滚期间的 `MassStorage(MSC)`、`MTP`、`Remote Shoot` 与 `USB-LAN` 主机枚举事件（`usb_host_data_enumeration_events == 0`）。
  - 仅在 `D+/D-` 与 SuperSpeed 数据线**物理隔离**、使用 `USB Type-C` 端口且插入 `NP-FZ100` 电池时，方允许 `[USB Power Supply] = [On]`（`_f.uxc` `0x721e`），并校验 `[USB LUN Setting]`（`Multi` `0xe631` 默认 vs `Single` `0x776d`）。
- **`[HDMI Info. Display]` LCD 熄屏护栏与 `1080p` 钳位 / `4K` 强制清洁覆盖**：
  - `[HDMI Info. Display]` 默认 `On`（`0xe07c`）会输出 OSD 叠加并熄灭机内 LCD（`CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`）；在接入外部 HDMI 采集器进行人工 LCD 菜单引导恢复时，强制要求 `[HDMI Info. Display] = Off`（`0xe297`），保证 LCD 触摸/菜单实时可见。
  - 校验机内录制且开启 `Log Shooting != Off`（`Flexible ISO` / `Cine EI` / `Cine EI Quick`）或 `PPLUT1..4` 时 HDMI 分辨率钳位至 `1080p`；校验 `Rec. Media dur HDMI Output = Off(HDMI Only)`（`0x6573`）或 `RAW Output = On`（`0x6e97`）输出 `4K` 并自动强制 `HDMI Info. Display = Off`。
  - 校验 `(Setup)` 下 USB 与 HDMI 设置跨越 `[Camera Settings Reset]` 留存（例外：`Framing Settings (HDMI)` 重置为 `Crop`），并保持 `Slot-1` `WP` 与 `H0 == H3`（`16/16`）零写入。

### 2. Sub-Pillar `49B` — `[Protect]` 四作用域 vs `[Format]` 擦除与 `Slot-1` 双层防线、`[Reset Network Set.]` 自动重启及零射频顺序
实现入口：[`evaluate_protect_format_network_reset_zero_rf_vault`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py#L2129-L2435)
- **`[Protect]` 仅阻断 `[Delete]` 而不防 `[Format]`（`Slot-1` 双层硬件 `WP` + 防火墙强制）**：
  - 校验 `ILME-FX3` `(Playback) -> [Selection/Memo] -> [Protect]`（`.uxc` `0xe2c9`）全部 4 个作用域：`Single/Multiple Img.`（`.uxc` `0xe2ca`）、`All in this Folder`（`_f.uxc` `0x6848`）、`All with this date`（`_f.uxc` `0x69f7`）、`All Images in This Group`（`.uxc` `0xe826`）均可阻断 `[Delete]` 与 `[Delete pressing twice]`。
  - 由于 `[Format]`（`.uxc` `0xe449`/`0xe414`，含 Quick/Full Format）会直接清除受保护文件与卡内 `M1..M4` 设置（`ILME-FX6` 的 `Lock/Unlock Clip` `0x42af` 同样被 `Format Media` `0x4254` 清除），对承载 `CAMSET`/`BODYDATA.DAT` 恢复金库的 `Slot 1` **硬拒仅依赖软件 `[Protect]` 的弱姿态**，强制要求**同时**满足物理 SD `WP` 锁定（`VAL_mr_memory_error_status_MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`）与 `slot1_format_hard_locked == True`。
- **`[Reset Network Set.]` 自动重启与复归 `[Airplane Mode] = [On]` 零射频闭环**：
  - 校验 `FUNC_reset_network_settings` / `SETTING_RESET_NW`（`_f.uxc` `0x60d3`/`0x65d3`）严格清空 `(Network)` 凭据/配对/证书并**保留 `(Shooting)`/`(Setup)`/`(Playback)`/`CAMSET`**。
  - 验证强制自动重启因子 `BKID_APP_is_shutdown_factor_network_reset` 触发且完成后，`[Airplane Mode]` 会被重置为 `Off`——因此在零射频认证前**强制要求重启已完整落地且人工/策略重新置位 `[Airplane Mode] = [On]`（`0x6df9`）**。

---

## 三、受控修改文件清单（严格限定 6 项拥有文件）

1. [realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py)（新增：Pillar 49A/49B、`18` 供体有界 `O_RDONLY` 检查与 `49/49` 总检聚合器）
2. [__init__.py](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)（导出 Pillar 49 及 `Master49PillarRecoveryReport` 全部符号与 `__all__`）
3. [__main__.py](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)（注册 `verify-usb-mode-hdmi-info-protect-network-reset-vault` 与 `verify-49pillar-recovery` CLI）
4. [outputs/fx3-recovery-adapter/README.md](../../outputs/fx3-recovery-adapter/README.md)（补充 Phase 282 文档与 `python3 -B` 命令用法）
5. [test_realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py](../../outputs/fx3-recovery-adapter/tests/test_realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier.py)（新增：76 项跨平台双模单元测试，采用前向兼容 `>= 49` 支柱数校验）
6. [reports/2026-11-17-phase282-realhw-49pillar-usb-mode-hdmi-info-protect-network-reset-vault-recovery/README.md](README.md)（新增：本工程报告）
