# Phase 336 里程碑交付报告：Recovery Pillar 60（Wave-58）与 `60/60` 统一恢复总检（`verify-60pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`60/60` 恢复支柱闭环里程碑达成，`VERIFIED_60OF60_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：
  1. 基于 [Wave 58 全球实机情报报告](../2026-11-17-global-sony-wave58-bright-monitoring-shot-mark-timecode-link-wifi-usblan-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` `ALCIN_UUD` vs `ILME-FX6 Ver. 6.01` `5-024-458-18` `CHAPLIN`），落地 **Phase 336 Recovery Pillar 60**（Sub-Pillar **60A** `6/6` + Sub-Pillar **60B** `6/6`）及并发式 **`60/60` 统一恢复总检聚合器** `evaluate_realhw_60pillar_recovery_master`（`schema_version = "realhw_60pillar_recovery_master_v1"`，`verify-60pillar-recovery`），并自动接入 Milestone 311 / 324 最高支柱自动发现接口（`recovery=60/60`）。
  2. 全量实现无供体 CI 保护：`_resolve_phase336_donor_path` 内置 `work_root is None` 防护，且 `evaluate_realhw_60pillar_recovery_master` 通过 `_master60_local_donors_available()` 在缺少本地 donor 时自动切换至 `CLEAN_ROOM_SYNTHETIC` 并返回 `rc=0`。
- **实测结果摘要（双模 & 4 模全绿）**：
  - `verify-pillar60-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`60A=6/6`、`60B=6/6`，`17` 项 Wave-58 本地供体严格 `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 核验通过，`elapsed=0.004977s`，`suite_sha256=21505ba5d5bad129...`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`60A=6/6`、`60B=6/6`，`elapsed=0.000508s`，`suite_sha256=f1b16d0d4161a8f5...`，`raw_firmware_bytes_leaked=0`。
  - `verify-60pillar-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`pillars=60/60`，`all_passed=True`，`elapsed=1.384132s`（`< 1.5s` 快速 CLI 预算），`master_60pillar_sha256=59e88b2e5abc9078...`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`pillars=60/60`，`all_passed=True`，`elapsed=0.989045s`（`< 1.5s`），`master_60pillar_sha256=45d05acdf844c5cb...`，`raw_firmware_bytes_leaked=0`。
    - 模拟无供体 CI 子进程（`iter_donor_work_roots -> (None,)`）：`rc=0`，自动切换 `verification_mode="CLEAN_ROOM_SYNTHETIC"`，`pillars_passed=60/60`。
  - `make verify-milestone-324` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324`：`status=OK pillars=6/6 gate142=143/146 recovery=60/60 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 auditors=45/45 vm_stages=71/71 h0_eq_h3=16/16 rf_pkts=0 slot1_writes=0 qemu=42/42(126/126) pngs=84/84 leaked=0`。
  - **硬件安全护栏硬锁**：`CNFLASHA_USERSPACE_WRITE_BLOCKED=True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED=False`、`SPI_NOR_WRITE_AUTHORIZED=False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED=False`、`ISP_WRITE_AUTHORIZED=False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED=False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED=False`、`OVERALL_READY_FOR_HARDWARE_ATTACH=False`、`CROSS_MODEL_FLASH_AUTHORIZED=False`、`OTP_FUSE_TOUCHES=0`、`RPMB_COUNTER_INCREMENTS=0`、`PHYSICAL_DEVICE_WRITES=0`、`RAW_FIRMWARE_BYTES_LEAKED=0`。

---

## 2. Wave-58 实测事实 vs 工程推断边界

> 以下严格区分来自 `ILME-FX3`（`ilc/2210`、`Ver. 7.02 appFw.so`/UXC/`Backup.bin`、`full-v4` 内核 `.ko`/`.so`）与 `ILME-FX6`（`5-024-458-18`、`Ver. 6.01 appFw.so`/UXC）的**实测事实**，以及恢复子系统施加的**工程推断 / 安全护栏**。

### 2.1 Sub-Pillar 60A：`[Bright Monitoring]` Ver.7.00+ 放大对焦共存、`[Monitor Brightness]` 与机械快门 `[BULB]` / `[DRO]` vs 休眠 `[Bulb Timer]` / `[Auto HDR]`

1. **实测事实 — `[Bright Monitoring]` 快捷键独占、自动取消与 Ver.7.00+ 放大共存**：
   - `ILME-FX3 Ver. 7.02` 仅允许通过自定义键绑定 `[Bright Monitoring]`（`_f 0x701f`，`FX3 appFw.so` 共 `6` 个符号，无多档增益或区域扩展），不在拍摄菜单暴露。
   - 激活期间强制将 `[Live View Display]` 切至 `[Setting Effect OFF]`，并在关机、拍摄模式离开 `P/A/S/M` 或对焦模式离开 `MF` 时自动取消；**Ver. 7.00 / 7.02 官方更新解锁了与 `[Focus Magnifier]` 及 `[Auto Magnifier in MF]` 的并发共存**（`Ver. 6.02` 及更早版本互斥返回 `EOPNOTSUPP=95`）。
2. **实测事实 — `Initialize` 专属 `[Monitor Brightness]` vs FX6 `VF Setting` / `AE Backlight` 消歧**：
   - `Setup -> [Monitor] -> [Monitor Brightness]`（`base 0xe44b`，`BKID_APP_setting_lcd_brightness`）仅暴露 `Manual`（`-2..+2`，默认 `0`）与 `Sunny Weather`（`base 0xe1da` / `_f 0x7a61`），抵抗 `Camera Settings Reset`（仅 `[Initialize]` 复位）；休眠枚举 `LCD_BRIGHTNESS_{AUTO,BRIGHT,NORMAL}` 返回 `EOPNOTSUPP=95`。
   - 对照 `ILME-FX6 Ver. 6.01`：使用 `Monitoring > VF Setting > Brightness`（`1..15`，默认 `8`）与 `Color Mode`（`Color / B&W`），`Shooting > Auto Exposure > Mode > Backlight`（`VAL_setting_auto_exposure_mode_MODE_BACKLIGHT`）实为逆光曝光模式，休眠 `LCD Backlight` / `VF Backlight` / `NIGHTSHOT_*` 严禁混淆。
3. **实测事实 — 机械快门专属 `[BULB]`、`DRO` 锁定与休眠 `[Bulb Timer]` / `[Auto HDR]`**：
   - 静态 `[BULB]`（`base 0xe916`、`PID_SET_BULB_MODE`、`CAUTION_ID_FACTOR_CAM_SET_BULB_ON_MSG`）强制要求 `[Mechanical Shutter]` 并在 `Single Shooting` / `Self-timer(Single)` / `DRO Bracket` 下生效，激活后禁用 `Anti-flicker Shoot.`；若切至 `Electronic Shutter`、`Cont. Shooting`、`Self-timer(Cont)`、`Cont. Bracket`、`Interval Shooting`、Movie 或非 `M` 档，自动回退至 `30"`（未回退则 fail-closed）。
   - `[D-Range Optimizer]`（`Auto[def]/Off/Lv1..5`）及 `[DRO Bracket]` 支持 `[Camera Settings Reset]`，当 `Picture Profile != Off` 或 `HLG Still Image = On` 时锁定禁用；`FX3 appFw.so` 内的 `13` 个休眠 `Bulb Timer` 符号（`_f 0x630f` / `0x78b6`）及休眠 `[Auto HDR]`（`base 0xe49d` / `0xe5d0`）在实机 `ilc/2210` 均未暴露，评估器一律拒绝并返回 `EOPNOTSUPP=95`。
4. **工程推断**：
   - Tier-0 恢复金库下对 `Slot 1` 发起任何写入/格式化或 Stage-B overlay 逃逸 `/tmp` 或 `Backup.bin H0 != H3`（`< 16` 面）均 fail-closed 拦截。

### 2.2 Sub-Pillar 60B：`[Shot Mark 1/2]` / `[Clip Flag]` vs 休眠 `[Divide]`/`[Extract]`、`VMC-BNCM1 EXT-LK`、WPA3/`USB-LAN` 零射频与 `Slot-1 EROFS=30` 防火墙

1. **实测事实 — 活跃 `[Shot Mark 1/2]` / `[Clip Flag]` / `[Edit]` vs 休眠 `[Divide]`/`[Extract]`/`Cut 15-30-60s`**：
   - FX3 Ver. 7.02 活跃暴露录制/回放 `[Shot Mark 1/2]`（`_f 0x628b`/`0x628a`/`0x6143`/`0x6142`）、Ver. 6.00+/7.00+ `[Clip Flag]`（`Off/OK/NG/KEEP`）、`[Image Jump Setting]`（6 档）与回放 `[Edit]`（`Photo Capture`、`JPEG/HEIF Switch` `JPEG/HEIF_420/HEIF_422`、`Copy`、`Rotate` + 自定义键 `Create Divider Frame` `_f 0x747a`）。
   - `FX3 appFw.so` 对 `divide_clip` / `clip_divide` / `extract_clip` / `CUT_TO_*` 全为 `0` 命中，`_f.uxc` 中 `Cut to 15/30/60 seconds`（`0x7005/0x6e38/0x6c2a`）及 FX6 `Shot Mark 0..9` / `Essence Mark` 均为跨机型休眠符号，全部返回 `EOPNOTSUPP=95`。
2. **实测事实 — 零蓝牙 `[Timecode Link]` vs `VMC-BNCM1 EXT-LK`、Wi-Fi SKU/WPA3 硬化与 `USB-LAN` 互斥**：
   - `FX3 appFw.so` 对 `tc_link` / `timecode_link` / `UltraSync` 全为 `0` 命中（`EOPNOTSUPP=95`）；外接 LTC 仅支持 Multi/Micro USB + `VMC-BNCM1`（`A-5051-506-A`）在 `Preset + Free Run` 且未启用 `USB-LAN` 时锁定 `EXT-LK`，对照 FX6 机身物理 `TC IN/OUT` BNC 拨动开关（且 FX6 无蓝牙硬件）。
   - Wi-Fi 分区硬件真值：`WW728473` 支持 `2.4/5GHz`，`WW558244` 仅支持 `2.4GHz`（`db.txt` 21 国家区 / 59 DFS 规则、`ccodeno.txt` 29 项）；**Ver. 7.00+ 移除 `WEP`、`WPA-PSK` 与 `Security(IPsec)`**，强制 `WPA2-PSK` / `WPA3-SAE` + `Access Authen. = On`。
   - `full-v4` 实存 `8` 个 USB-LAN 内核模块（含 `cdc_ncm.ko`、`r8152.ko`）与 `libWiredLanResource.so` / `libNetServiceEther.so`；`USB-LAN` 与机内 `Wi-Fi` 及 `Multi/Micro USB`（如 `VMC-BNCM1`）严格互斥，且 `[Reset Network Set.]` 与 `[Initialize]` 均将 `[USB-LAN Cnct. Launch]` 复位为 `Off` 并保留 `[Airplane Mode] = On`。
3. **工程推断 — Zero-RF 台架隔离与 `Slot-1 EROFS=30` 防火墙**：
   - `Airplane Mode = On` + `USB-LAN (CDC-NCM)` 保证 `rf_packets_transmitted == 0` 与 `rf_nvs_mutation_bytes == 0`。
   - 对挂载 Tier-0 保险库的 `Slot 1` 发起任何修改 `M4ROOT/CLIP/*M01.XML` + `AVF_INFO`（`Shot Mark` / `Clip Flag`）、写 `DCIM/` 静止帧（`Photo Capture` / `Create Divider Frame`）或格式化的动作一律 fail-closed 拦截返回 `EROFS (errno 30)`，保证 `slot1_data_sector_writes == 0`、`raw_firmware_bytes_leaked == 0`。

---

## 3. 授权交付文件清单（Strict 6-File Ownership）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier.py) | Pillar 60A/60B 状态机与评估器、17 项 `O_RDONLY` 有界核验 + `work_root is None` / 无供体 Clean-Room 自动回退、`6/6 + 6/6` 套件及 `60/60` 并发主控 `evaluate_realhw_60pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出 Phase 336 `P336_*` / `PHASE336_*` / `MASTER_60_*` / `evaluate_realhw_60pillar_recovery_master` 等公开符号与 `__all__` |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar60-bright-mon-shotmark-usblan-bulb-vault`、`verify-pillar60-recovery` 与 `verify-60pillar-recovery` CLI 子命令（`%%` 转义） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 336 Pillar 60 & `60/60` 恢复总检文档与 CLI 示例 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier.py) | **100 项**四模（本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、模拟无供体 `(None,)` / 不存在根目录及子进程）单元测试与前向兼容自动发现断言 |
| 6 | NEW | [`reports/2026-11-17-phase336-milestone-pillar60-60pillar-bright-mon-shotmark-usblan-bulb-vault/README.md`](README.md) | 本 Phase 336 里程碑中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 60 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_60pillar_bright_mon_shotmark_usblan_bulb_dormant_vault_verifier.py -v` | **`100/100 OK`**（`20.822s`） |
| Pillar 60 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest ... -v` | **`100/100 OK`**（`19.781s`） |
| Pillar 60 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest ... -v` | **`100/100 OK`**（`21.773s`） |
| 显式模拟无供体 CI（`(None,)` / `Path("/nonexistent-donor-root")` & 子进程） | `test_15` / `test_18` / `test_100` + 独立子进程 `patch.object(f, 'iter_donor_work_roots', return_value=(None,))` 调 `verify-60pillar-recovery --json` | **`CLEAN_ROOM_SYNTHETIC`（`60/60`，`rc=0`，零 `TypeError`）** |
| `verify-pillar60-recovery` CLI（供体 / 洁净室） | `verify-pillar60-recovery --json` & `verify-pillar60-recovery --force-clean-room --json` | **`60A=6/6, 60B=6/6`**（`0.004977s` / `0.000508s`，`suite_sha256=21505ba5d5bad129...` / `f1b16d0d4161a8f5...`，`leaked=0`） |
| `verify-60pillar-recovery` CLI（供体 / 洁净室） | `verify-60pillar-recovery --json` & `verify-60pillar-recovery --force-clean-room --json` | **`60/60 PASS`**（`1.384132s` / `0.989045s` `< 1.5s`，`master_60pillar_sha256=59e88b2e5abc9078...` / `45d05acdf844c5cb...`，`leaked=0`） |
| `make verify-milestone-324`（正常模式 & `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `make verify-milestone-324` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` | **`status=OK pillars=6/6 gate142=143/146 recovery=60/60 leaked=0`**（`055204985d1587ed...` / `75d102c94f8b8641...`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（正常模式） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -v` | **`3,593 tests OK`**（`skipped=1`，`490.259s`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`3,535 tests OK`**（`skipped=17`，`434.733s`） |
| 清洁审计 | `make clean-audit` | **`ALL GREEN`**（零 `.pyc` / 零未跟踪残留） |
