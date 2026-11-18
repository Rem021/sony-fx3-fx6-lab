# Phase 332 工程交付报告：Recovery Pillar 59（Wave-57）与 `59/59` 统一恢复总检（`verify-59pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`59/59` 恢复支柱闭环，`VERIFIED_59OF59_PILLAR_RECOVERY_MASTER`；附 Pillar 57/59 无供体 Clean-Room CI `rc=2` 根因修复）**。
- **核心成果**：
  1. 基于 [Wave 57 全球实机情报报告](../2026-11-17-global-sony-wave57-steadyshot-ibis-movie-selftimer-custom-zebra-streaming-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` `ALCIN_UUD` vs `ILME-FX6 Ver. 6.01` `5-024-458-18` `CHAPLIN`），交付 **Phase 332 Recovery Pillar 59**（Sub-Pillar **59A** `6/6` + Sub-Pillar **59B** `6/6`）及并发式 **`59/59` 统一恢复总检聚合器** `evaluate_realhw_59pillar_recovery_master`（`schema_version = "realhw_59pillar_recovery_master_v1"`，`verify-59pillar-recovery`），自动接入 Milestone 311 / 324 最高支柱自动发现接口（`recovery=59/59`）。
  2. 完成授权的无供体 Clean-Room CI 修复：定位 GitHub Actions `test_87_cli_subprocess_default_mode_exits_zero` 出现 `rc=2` 的根因——`evaluate_realhw_57pillar_recovery_master` 在 `force_clean_room=None` 且无 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时向 `56` 支柱级联传入空 `kw={}`，触发 Pillar 28 `_read_bounded_rdonly` 对缺失的 `fx3-7.02-BODYDATA.DAT` 抛出 `ValueError`；在 Pillar 57 与 Pillar 59 主控中新增 `_master57_local_donors_available()` / `_master59_local_donors_available()`（含 `work_root is None` 防护），在本地供体缺失时无缝回落至 `CLEAN_ROOM_SYNTHETIC` 并返回 `rc=0`。
- **实测结果摘要（双模全绿）**：
  - `verify-pillar59-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`59A=6/6`、`59B=6/6`，`17` 项 Wave-57 供体严格 `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 核验通过，`elapsed=0.004s`，`suite_sha256=22e97c80aa59d745...`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`59A=6/6`、`59B=6/6`，`elapsed=0.000s`，`suite_sha256=156fd9b67070b460...`。
  - `verify-59pillar-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`pillars=59/59`，`all_passed=True`，`elapsed=1.139s`（`< 1.5s` 快速 CLI 预算），`master_59pillar_sha256=9b61bb7ec710f231...`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`pillars=59/59`，`all_passed=True`，`elapsed=0.761s`（`< 1.5s`），`master_59pillar_sha256=ed3ec43e31b0d6a0...`。
  - `make verify-milestone-324`（双模）：`status=OK pillars=6/6 gate142=143/146 recovery=59/59 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 rf_pkts=0 slot1_writes=0 leaked=0`。
  - **硬件安全护栏硬锁**：`PERSISTENT_EMMC_WRITES_AUTHORIZED=False`、`SPI_NOR_WRITE_AUTHORIZED=False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED=False`、`ISP_WRITE_AUTHORIZED=False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED=False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED=False`、`OVERALL_READY_FOR_HARDWARE_ATTACH=False`、`CROSS_MODEL_FLASH_AUTHORIZED=False`、`OTP_FUSE_TOUCHES=0`、`RPMB_COUNTER_INCREMENTS=0`、`PHYSICAL_DEVICE_WRITES=0`、`RAW_FIRMWARE_BYTES_LEAKED=0`。

---

## 2. Wave-57 实测事实 vs 工程推断边界

> 以下严格区分来自 `ILME-FX3`（`ilc/2210`、`Ver. 7.02 appFw.so`/UXC/`Backup.bin`）与 `ILME-FX6`（`5-024-458-18`、`Ver. 6.01 appFw.so`/UXC）的**实测事实**，以及恢复子系统施加的**工程推断/安全护栏**。

### 2.1 Sub-Pillar 59A：`[SteadyShot]` 5 轴 IBIS / 47 档焦距 / 4 重互锁 vs `[Self-timer]` 与 FX6 边界

1. **实测事实 — `Shooting -> [Image Stabilization]`（`_g 0x6214`）4 项全可复位与 47 档焦距**：
   - Movie `[SteadyShot]`（`Active` / `Standard` 默认 / `Off`）、Still `[SteadyShot]`（`On` 默认 / `Off`）、`[SteadyShot Adjust.]`（`Auto` 默认 / `Manual`）与 `[Focal Length]`（**47 档** `8..1000mm`，默认 `8mm`）均支持 `[Camera Settings Reset]` 复位。
   - Movie `Active` 强制收窄视角并锁定 `[Distortion Comp.] = Auto`，且在 **4 种条件下锁死禁用**：① Movie `>= 100p / 119.88p`；② `S&Q >= 100fps / 120fps`；③ `HDMI RAW = On`；④ `[De-Squeeze Display] != Off`（`1.3x..2.0x`）。
   - `[Clear Image Zoom]` 同样在 `119.88p/100p` 或 `S&Q >= 100/120fps` 或 Still `RAW` 下禁用，启用时锁定 `[Metering Mode] = Multi`；`[Dynamic active]`（`_f 0x741c`）在 FX3 Ver. 7.02 上属**休眠符号**，对请求强制 `EOPNOTSUPP=95`。
2. **实测事实 — `[Self-timer]` 动/静边界、前部 `#8` 复合灯与 `[Audio signals]`**：
   - FX3 Ver. 7.02 **无 Movie `[Self-timer]`**（`BKID_APP_setting_movie_self_timer` / `Rec Start delay` `_f 0x7192` 均为跨机种休眠符号，`EOPNOTSUPP=95`）。
   - Still `[Drive Mode]`（`_g 0x616e`，可随 `Camera Settings Reset` 复位）暴露 `Self-timer(Single)`（`10/5/2s`）、`Self-timer(Cont)`（**6 档**：`10/5/2 Sec. × 3/5 Img.`）及 `[Selftimer during Bracket]`（`Off` 默认/`2/5/10 Sec`）。
   - 自拍倒计时驱动前部 **#8 复合部件**（`AF illuminator / Self-timer lamp / Visible light and IR sensor`，与前端 Tally REC 红灯物理独立）及 `Initialize`-only `[Audio signals]`（`On` 默认/`Off`，当 `Silent Mode = On` 或 Movie HDMI 音频激活时静音）。
3. **实测事实 — `ILME-FX6` 无 IBIS 边界**：
   - `FX6 appFw.so` 声明 `TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`（仅支持镜头 OSS + 机内 6 轴陀螺仪元数据供 Catalyst 后期稳像），无 Still Self-timer，改用 `Picture Cache Rec` 与 `Interval Rec`。
4. **工程推断**：
   - `Active` 模式水平视场裁切系数按 FX3 12.1MP 水平有效像素与 4K 中心采样式样测算为约 **`1.104x`**；在 Tier-0 恢复保险库护栏下，任何未授权写入 `Slot 1` 的操作均 fail-closed 返回 `EROFS=30`。

### 2.2 Sub-Pillar 59B：`[Zebra Display]` Custom1/2 IRE、4 色 `[Peaking]` Clean-HDMI 与 `[Network Streaming]` 零射频 / Slot-1 防火墙

1. **实测事实 — `Initialize`-only `[Zebra]`（Custom 1/2）与 4 色 `[Peaking]` Clean-HDMI 隔离**：
   - `[Zebra Display]`（`Off` 默认）与 `[Zebra Level]`（`70` 默认/`75/80/85/90/95/100/100+` + `Custom1` 默认 `Std+Range 0..109 ± 1..10%` + `Custom2` 默认 `Lower Limit 0..109+`）均抵抗 `Camera Settings Reset`（仅 `[Initialize]` 复位）。
   - `[Peaking Display]`（`Off` 默认）、`[Peaking Level]`（`High / Mid[def] / Low`）与 4 色 `[Peaking Color]`（`Red / Yellow / Blue / White[def]`）均为 `Initialize`-only，且 Zebra 与 Peaking 均隔离于机身屏幕，不随 Clean-HDMI 输出至外部监看器。
   - **FX6 纠偏边界**：`ILME-FX6` `Monitoring > Zebra > Setting` 为 **`Off / Zebra1 / Zebra2`** 三选一互斥切换（并非同时开启 `Both`），`Peaking > Color` 为 `B&W / Red / Yellow / Blue`。
2. **实测事实 — `Network -> [Streaming] -> [Network Streaming]` 与 Reset 边界**：
   - 支持 `RTMP`（`H.264`）、`RTMPS`（TLS + `H.264`）与 `SRT`（`H.265/H.264` + `None/AES-128/AES-256`）；分辨率/帧率支持 `4K/2K/1080p/720p @ 59.94p/50p/29.97p/25p`，**不支持 `23.98p / 24p` 推流**（`EINVAL=22` / `EOPNOTSUPP=95`）。
   - `[Movie Rec During Streaming]`（默认 `Disable`）启用时强锁机内帧率与推流帧率一致，且在 `4K` 或 `2K 59.94p/50p` 推流时禁用机内 4K 记录；推流中锁定 `Menu` / `Playback` / `FTP` / 休眠。全部 `(Network)` 项抵抗 `Camera Settings Reset`，且 `[Reset Network Set.]` 保留 `[Airplane Mode] = On`。FX6 机内残留 `RTMP/SRT/QoS Streaming` 均为休眠符号（`EOPNOTSUPP=95`）。
3. **工程推断 — S-Log3 IRE 标定与 Zero-RF / Slot-1 `EROFS=30` 双护栏**：
   - 原始 S-Log3 18% 中灰 = `41%` IRE、90% 白 = `61%` IRE、高光裁切约 **`94%` IRE**；开启 `[Display LUT] = On` 后斑马线改测算 LUT 映射后信号。
   - Tier-0 恢复台架强制 `[Airplane Mode] = On`（`rf_packets_transmitted == 0`、`rf_nvs_mutation_bytes == 0`，仅允许有线 `USB-LAN CDC-NCM` 审计），并对任何指向 `Slot 1` 的 `[Movie Rec During Streaming] = Enable` 或 FTP 写路径 fail-closed 返回 `EROFS (errno 30)`，确保 `slot1_data_sector_writes == 0`、`raw_firmware_bytes_leaked == 0`。

---

## 3. 授权交付文件清单（9 Files Strict Ownership）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier.py) | Pillar 59A/59B 状态机与评估器、17 项 `O_RDONLY` 有界核验 + `work_root is None` / 无供体 Clean-Room 自动回退、`6/6 + 6/6` 套件及 `59/59` 并发主控 `evaluate_realhw_59pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出 Phase 332 `P332_*` / `PHASE332_*` / `MASTER_59_*` / `evaluate_realhw_59pillar_recovery_master` 等 302 项符号 |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar59-steadyshot-47focal-selftimer-zebra-streaming-vault`、`verify-pillar59-recovery` 与 `verify-59pillar-recovery` CLI 子命令 |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 332 Pillar 59 & `59/59` 恢复总检文档与 CLI 示例 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier.py) | **97 项**双模与无供体模拟单元测试（覆盖正常供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`work_root=None`、无供体 CI 模拟、向后兼容与自动发现） |
| 6 | EDIT | [`outputs/fx3-recovery-adapter/tests/test_realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier.py) | 按 `msg_1a889c4c627a` 授权更新 `test_65` 为前向兼容 `assertGreaterEqual(count, 58)` 与 `callable(fn)` |
| 7 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py) | 按 `msg_baf998d50f60` 授权新增 `_master57_local_donors_available()`，修复无供体主机运行 `evaluate_realhw_57pillar_recovery_master` / `verify-57pillar-recovery` 返回 `rc=2` 的 CI 缺陷 |
| 8 | EDIT | [`outputs/fx3-recovery-adapter/tests/test_realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier.py) | 新增 `test_91_donorless_ci_mock_master57_and_cli_exit_zero`，验证 `(None,)` 与 `Path("/nonexistent-donor-root")` 下默认模式 `rc=0` |
| 9 | NEW | [`reports/2026-11-17-phase332-pillar59-59pillar-steadyshot-47focal-selftimer-zebra-streaming-vault/README.md`](README.md) | 本 Phase 332 中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 59 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest -v outputs/fx3-recovery-adapter/tests/test_realhw_59pillar_steadyshot_47focal_selftimer_zebra_streaming_vault_verifier.py` | **`97/97 OK`**（`skipped=0`，`16.746s`） |
| Pillar 59 单测（`FX3_CLEAN_ROOM_TEST=1`） | `FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest ...` | **`97/97 OK`**（`skipped=0`，`18.014s`） |
| Pillar 59 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest ...` | **`97/97 OK`**（`skipped=0`，`16.894s`） |
| Pillar 57 + Pillar 58 双模单测（含 `test_91` 无供体模拟） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=... /usr/bin/python3 -B -m unittest test_realhw_57pillar_... test_realhw_58pillar_...`（正常 & `FX3_FX6_FORCE_CLEAN_ROOM=1`） | **`181/181 OK`**（`37.406s`） & **`181/181 OK`**（`skipped=1`，`35.128s`） |
| 显式模拟无供体 CI（`(None,)` / `Path("/nonexistent-donor-root")` / `()`） | `mock.patch.object(files_mod, "iter_donor_work_roots", ...)` + `evaluate_realhw_{57,58,59}pillar_recovery_master()` & `verify-{57,59}pillar-recovery --json` | **`CLEAN_ROOM_SYNTHETIC`（`57/57` / `58/58` / `59/59`，`rc=0`，零 `TypeError`）** |
| `verify-pillar59-recovery` CLI（供体 / 洁净室） | `verify-pillar59-recovery` & `verify-pillar59-recovery --force-clean-room` | **`59A=6/6, 59B=6/6`**（`0.004s` / `0.000s`，`suite_sha256=22e97c80aa59d745...` / `156fd9b67070b460...`，`leaked=0`） |
| `verify-59pillar-recovery` CLI（供体 / 洁净室） | `verify-59pillar-recovery` & `verify-59pillar-recovery --force-clean-room` | **`59/59 PASS`**（`1.139s` / `0.761s` `< 1.5s`，`master_59pillar_sha256=9b61bb7ec710f231...` / `ed3ec43e31b0d6a0...`，`leaked=0`） |
| `make verify-byof` | `PYTHONDONTWRITEBYTECODE=1 make verify-byof` | **`LOCAL_DONOR_VERIFIED`**（`en=57 zh=57 parity_ok=True`，`0.52s`） |
| `make verify-milestone-311`（双模） | `make verify-milestone-311` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-311` | **`status=OK pillars=6/6 gate134=143/146 recovery=59/59 leaked=0`**（`aef6779e24ccfc83...` / `1d391f196059d6bf...`） |
| `make verify-milestone-324`（双模） | `make verify-milestone-324` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` | **`status=OK pillars=6/6 gate142=143/146 recovery=59/59 leaked=0`**（`e7a83d268299942f...` / `bdefb62ff170da74...`） |
| 清洁审计 | `make clean-audit` | **`ALL GREEN in 0.08s`**（零 `.pyc` / `__pycache__`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（本地供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -t outputs/fx3-recovery-adapter/tests -p "test_*.py"` | **`3,493 tests OK`**（`skipped=1`，`401.732s`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（强制洁净室） | `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab" /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -t outputs/fx3-recovery-adapter/tests -p "test_*.py"` | **`3,435 tests OK`**（`skipped=17`，`464.924s`） |

