# Phase 370 结项报告：Recovery Pillar 68 与 `68/68` 统一恢复总检里程碑（Wave-66 静态 `[Drive Mode]` 10fps 与休眠 `[Focus Bracket]` 辟谣、2 档 `[Shutter Type]` 无 `Auto` / `1/250 s` X-Sync / 抗 Reset `[e-Front Curtain Shut.]` / `[Long Exposure NR]` / `[High ISO NR]`、10 预设 8 非对称参数 `[Creative Look]` vs 休眠 `[Soft Skin Effect]` 及 `[Delete]`/`[Protect]`/`[Recover Image DB]` `Slot 1 EROFS=30` 防火墙）

- **日期**：`2026-11-18`
- **任务 / 阶段**：`H468` · **Phase 370（Recovery Pillar 68 & `68/68` Master Recovery Milestone）**
- **依据实机基线**：Sony `ILME-FX3`（`Ver. 7.02`，`0x91030080`，`PRODUCT_MODEL_ALCIN_UUD`，`ilc/2210`）vs `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`，`5-024-458-18`），全部立足 [Wave 66 全局情报报告](../2026-11-17-global-sony-wave66-drive-focusbracket-shutter-efcs-creativelook-recoverdb-intel/README.md) 与 **17 项**（`FX3` 14 项 + `FX6` 3 项）只读 donor 实证。
- **事实与推断边界声明**：文中所有 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、donor 文件大小与 SHA-256、官方 Help Guide/说明书规则均标注为 **`[实测事实]`**；所有台架隔离策略（`Slot 1 EROFS=30` 阻断、`Stage-B /tmp` 隔离与模拟单元测试/总门控结果）均标注为 **`[模拟/安全护栏推断]`**。报告正文 **0 字节**泄露索尼专有原始固件字节（`raw_firmware_bytes_leaked = 0`）。

---

## 核心结论先行（Executive Conclusion）

1. **已将恢复验证总检推升至 `68/68`（`VERIFIED_68OF68_PILLAR_RECOVERY_MASTER`）** `[模拟/安全护栏推断]`：
   - 新增 [`realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py)，无遮蔽导出至 [`__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py)（含 `verify_68pillar_recovery_master` / `verify_68pillar_recovery_suite` / `verify_68pillar_recovery` / `evaluate_realhw_68pillar_recovery_master` 等全套对称入口）并接入 [`__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)（`verify-68pillar-recovery` / `verify-pillar68-recovery` / `verify-pillar68-drive-focusbracket-shutter-efcs-creativelook-recoverdb-vault`），与 `fx6_closure verify-milestone-364`（`recovery=68/68`）无缝自动对接。
   - **硬安全红线全程锁死**：`overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`cross_model_flash_authorized = False`、`persistent_emmc_writes_authorized = False`、`emmc_writes_authorized = False`、`cnflasha_userspace_write_blocked = True`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`slot1_sector_writes = 0`、`slot1_data_sector_writes = 0`、`cnflasha_writes = 0`、`raw_firmware_bytes_leaked = 0`。
2. **Pillar 68A 静态 `[Drive Mode]` 10fps / 休眠 `[Focus Bracket]` 辟谣 + 2 档 `[Shutter Type]` 无 `Auto` / `1/250 s` X-Sync / `[e-Front Curtain Shut.]` / 降噪边界落地** `[实测事实]`：
   - **`[Drive Mode]` 全量 9 项（全部 `Can be reset`）与休眠 `[Focus Bracket]` 拒绝**：严格建模 `Single Shooting`（默认）、`Cont. Shooting`（`Hi+` `10 fps` 非实时取景刷新 / `Hi` `8 fps` / `Mid` `6 fps` / `Lo` `3 fps`；`> F11` 在 `Hi+/Hi/Mid` 下锁焦首张；`Uncompressed RAW` 或闪光灯降速）、`Self-timer(Single)`（`10/5/2 Sec`）、`Self-timer(Cont)`（严格 6 组合，拒绝休眠 `10SEC_10IMAGES`）、`Cont. Bracket` 与 `Single Bracket`（`0.3..1.0 EV` × `3/5/9`、`2.0/3.0 EV` × `3/5`，`iAuto` 下禁用）、`WB bracket`（`Lo ±10 MK-1` / `Hi ±20 MK-1`）、`DRO Bracket`（`HLG Still Image = On` 时禁用）及 `[Interval Shoot Func.]`（仅输出静态照片序列，独立 `[Shutter Type in Interval]` 默认 `Electronic Shutter`）。对 FX3 休眠 `[Focus Bracket]`（`0` 命中 `ilc/2210`，尽管 ELF 含 `BKID_APP_setting_focus_bracket_*` 与 `_f 0x7563`/`0x6915`）及纯电影机 `ILME-FX6` Still `Drive Mode` / `Focus Bracket` 一律返回 `EOPNOTSUPP=95` 拒绝。
   - **2 档 `[Shutter Type]` 无 `Auto`、`1/250 s` X-Sync 与抗 Reset `[e-Front Curtain Shut.]`**：`[Shutter Type]`（`Can be reset`）严格暴露 `Mechanical Shutter`（默认）与 `Electronic Shutter`，显式拒绝休眠 `Auto` / `ANTI_DISTORTION_SHUTTER_AUTO` / `_f 0x66b8`（`EOPNOTSUPP=95`）；`Electronic Shutter` 或 `Silent Mode = On` 硬锁 5 项（`Flash`、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.`）；机械闪光同步上限严格 `1/250 s`（拒绝 `1/320` 伪造）；`[e-Front Curtain Shut.]`（Sony 拼写错字 `BKID_APP_setting_front_curtaion_shutter`，默认 `On`）**抗 `[Camera Settings Reset]`（`Not available`，仅 `Initialize` 还原）**；`[Long Exposure NR]`（`>= 1 s` 暗帧减除，电子/静音/连拍/连拍包围禁用，`iAuto` 锁 `On`）与 `[High ISO NR]`（严格 3 档 `Normal`/`Low`/`Off`，拒绝休眠 `HIGH`，永不修改 `.ARW` 原始数据）对照 `FX6` `Shooting > Noise Suppression` 与 `Technical > APR > Execute`。
3. **Pillar 68B `[Creative Look]` 10 预设 6 自定义 8 非对称参数 / 休眠 `[Soft Skin Effect]` 辟谣与 `[Delete]`/`[Protect]`/`[Recover Image DB]` `Slot 1 EROFS=30` 防火墙落地** `[实测事实]` + `[模拟/安全护栏推断]`：
   - **`[Creative Look]`（`Can be reset`）与休眠 `[Soft Skin Effect]` 拒绝**：覆盖 `ST..SE` 10 预设 + `Custom Look 1..6`（对应 ELF `look_still0..15` / `look_movie0..15` 16 槽位）与 8 项非对称参数值域（`-9..+9`：`Contrast`/`Highlights`/`Shadows`/`Saturation`；**`0..9`**：`Fade`/`Sharpness`/`Clarity`；**`1..5`**：`Sharpness Range`/`fineness`）；强制 `BW`/`SE` 锁死 `Saturation`、Movie/`S&Q` 锁死 `Sharpness Range`，且在 `Picture Profile != Off`、`Log Shooting != Off`、`HLG Still Image = On` 或 `iAuto` 下强制固定为 `[-]` 禁用；同时在 `FX3` 与 `FX6` 双机上拒绝休眠 `[Soft Skin Effect]`（`0` 命中 `ilc/2210`，SDK 标 `-`），对照 `FX6` `Base Look` / `Scene File` / `Multi Matrix`。
   - **Playback `[Delete]`/`[Protect]` 与 `[Recover Image DB]` Tier-0 `Slot 1 EROFS=30` 故障闭锁**：建模 `[Delete]` 5 档范围 + Proxy 联动删除 + 受保护项跳过、抗 Reset 的 `[Delete confirm.]`（`"Cancel" first` vs `"Delete" first`）与 `[Delete pressing twice]` 双击速删风险、`[Protect]`（`Fsys_Chmod` + Proxy 联动保护，`[Copy]` 不保留保护属性）、抗 Reset 且抗 Initialize 的 `[Recover Image DB]`（重建 `AVF_INFO` 并清除 FTP 传输结果、受电池电量 `EBUSY=16` 门控）以及只读安全的 `[Display Media Info.]`（单卡 `40,000` 张上限）；对任何面向 Tier-0 只读 `Slot 1`（及 `FX6 Restore Media(A)`）的写/删/改属性/重建库操作无条件触发 **`EROFS (errno 30)`** fail-closed 阻断（`slot1_sector_writes == 0`、`cnflasha_writes == 0`、`Backup.bin H0 == H3` `16/16`）。

---

## 变更文件清单（严格限定 6 项自有文件）

| 序号 | 文件路径 | 变更性质 | 职责摘要 |
| :--- | :--- | :---: | :--- |
| 1 | [`realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py) | NEW | Pillar 68A/68B 确定性状态模型、17 项 `O_RDONLY` 只读 donor 探测与 Clean-Room 合成回退、`68/68` 并发总检聚合器 |
| 2 | [`__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | EDIT | 无遮蔽导出 Pillar 68 与 `68/68` 公开符号（含 `verify_68pillar_recovery_master` 等，保留 `22..67` 全部兼容导出） |
| 3 | [`__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | EDIT | 接入 `verify-68pillar-recovery`、`verify-pillar68-recovery` 与完整别名 CLI 子命令 |
| 4 | [`test_realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_68pillar_drive_focusbracket_shutter_efcs_creativelook_recoverdb_vault_verifier.py) | NEW | `192` 项单元测试（超 `>=140` 要求），覆盖正常 donor、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与模拟无 donor `work_root=None` |
| 5 | [`README.md`](../../outputs/fx3-recovery-adapter/README.md) | EDIT | 追加 Phase 370 Pillar 68 与 `68/68` 统一恢复总检文档与验证命令 |
| 6 | [`reports/2026-11-18-phase370-pillar68-68pillar-drive-focusbracket-shutter-efcs-creativelook-recoverdb-vault/README.md`](README.md) | NEW | 本 Phase 370 中文工程结项报告 |

---

## 实测验证结果台账（Verification Ledger）

| 验证项 | 执行模式 / 命令 | 实测结果（`[实测事实]`） |
| :--- | :--- | :--- |
| Pillar 68 专项单元测试（正常 donor 模式） | `PYTHONDONTWRITEBYTECODE=1 ... unittest -q test_realhw_68pillar_...py` | **`192 / 192` PASS**（`20.179s`） |
| Pillar 68 专项单元测试（`FX3_CLEAN_ROOM_TEST=1`） | `FX3_CLEAN_ROOM_TEST=1 ... unittest -q test_realhw_68pillar_...py` | **`192 / 192` PASS**（`19.918s`） |
| Pillar 68 专项单元测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest -q test_realhw_68pillar_...py` | **`192 / 192` PASS**（`19.511s`） |
| 模拟无 donor 回退（`iter_donor_work_roots -> (None,)`） | `unittest -v test_realhw_68pillar_...py -k test_005_donor_inspect_env_clean_room_and_donorless_work_root_none` | **PASS**（`0.842s`，自动切换 `CLEAN_ROOM_SYNTHETIC`） |
| `verify-68pillar-recovery --json`（正常模式） | `LOCAL_DONOR_O_RDONLY`（17 donors） | `status=VERIFIED_68OF68_PILLAR_RECOVERY_MASTER`, `pillars=68/68`, `elapsed=1.238351s`, `sha256=301d9565e191dc02fc79cdea33e9c36fb0de87296d6e900f37670e6e2e570858`, `leaked=0` |
| `verify-68pillar-recovery --force-clean-room --json` | `CLEAN_ROOM_SYNTHETIC`（17 synthetic donors） | `status=VERIFIED_68OF68_PILLAR_RECOVERY_MASTER`, `pillars=68/68`, `elapsed=0.832884s`, `sha256=43e14980da0d937278316264851bfcc1aee18a867a83672b8430f242a0772a41`, `leaked=0` |
| Milestone 364 双模总门控（正常模式） | `python3 -B -m fx6_closure verify-milestone-364` | **`status=OK`**, `mode=LOCAL_DONOR_O_RDONLY`, `pillars=6/6`, `recovery=68/68`, `gate156=153/156`, `h0_eq_h3=16/16`, `slot1_writes=0`, `leaked=0`, `ready_attach=False` |
| Milestone 364 双模总门控（Clean-Room 模式） | `python3 -B -m fx6_closure verify-milestone-364 --force-clean-room` | **`status=OK`**, `mode=CLEAN_ROOM_SYNTHETIC`, `pillars=6/6`, `recovery=68/68`, `gate156=153/156`, `h0_eq_h3=16/16`, `slot1_writes=0`, `leaked=0`, `ready_attach=False` |
| `fx3-recovery-adapter` 全量测试发现（正常 donor 模式） | `unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py" -q` | **`4819` 项 PASS**（`624.058s`，`skipped=1`） |
| `fx3-recovery-adapter` 全量测试发现（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py" -q` | **`4761` 项 PASS**（`587.885s`，`skipped=18`） |
| Clean-Room 卫生与二进制审计 | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` | **`ALL GREEN in 0.11s`**（`0` `.pyc`、`0` 未授权二进制） |
