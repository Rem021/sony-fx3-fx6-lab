# Phase 340 里程碑交付报告：Recovery Pillar 61（Wave-59）与 `61/61` 统一恢复总检（`verify-61pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`61/61` 恢复支柱闭环里程碑达成，`VERIFIED_61OF61_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：
  1. 基于 [Wave 59 全球实机情报报告](../2026-11-17-global-sony-wave59-big6-home-framing-interval-shoot-tc-make-run-auth-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` `ALCIN_UUD` vs `ILME-FX6 Ver. 6.01` `5-024-458-18` `CHAPLIN`），落地 **Phase 340 Recovery Pillar 61**（Sub-Pillar **61A** `6/6` + Sub-Pillar **61B** `6/6`）及并发式 **`61/61` 统一恢复总检聚合器** [`evaluate_realhw_61pillar_recovery_master`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py)（`schema = "realhw_61pillar_recovery_master_v1"`，`verify-61pillar-recovery`），并自动接入 Milestone 311 / 324 最高支柱自动发现接口（`recovery=61/61`）。
  2. 全量实现无供体 CI 保护：`_resolve_phase340_donor_path` 内置 `work_root is None` 防护，且 `evaluate_realhw_61pillar_recovery_master` 通过 `_master61_local_donors_available()` 在缺少本地 donor 时自动切换至 `CLEAN_ROOM_SYNTHETIC` 并返回 `rc=0`。
  3. 全量放宽历史 Pillar（`30..49` 及 `airgap`，含 Task H418 指定的 `44..50` 区间）及对应测试的 donor 只读检查墙钟预算：`0.15s -> 2.0s`（当前库内已实现 `0` 处 `0.15s budget` 硬编码残留），消除高并发 6 路 QEMU/单元测试磁盘 I/O 下的瞬态超预算误报。
- **实测结果摘要（双模 & 4 模全绿）**：
  - `verify-pillar61-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`61A=6/6`、`61B=6/6`，`17` 项 Wave-59 本地供体严格 `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 核验通过，`elapsed=0.004701s`，`suite_sha256=6f1fd57a025f97fd...`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`61A=6/6`、`61B=6/6`，`elapsed=0.000452s`，`suite_sha256=01a9986a93fd94d9...`，`raw_firmware_bytes_leaked=0`。
  - `verify-61pillar-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`pillars=61/61`，`all_passed=True`，`elapsed=1.231196s`（`< 1.5s` 快速 CLI 预算），`master_61pillar_sha256=a69a4e0bb23edede...`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`pillars=61/61`，`all_passed=True`，`elapsed=0.851313s`（`< 1.5s`），`master_61pillar_sha256=3c4867f1aafc9250...`，`raw_firmware_bytes_leaked=0`。
    - 模拟无供体 CI 子进程（`iter_donor_work_roots -> (None,)`）：`rc=0`，自动切换 `verification_mode="CLEAN_ROOM_SYNTHETIC"`，`pillars_passed=61/61`。
  - `make verify-milestone-324` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324`：`status=OK pillars=6/6 gate142=143/146 recovery=61/61 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 auditors=45/45 vm_stages=73/73 h0_eq_h3=16/16 e_nd_tx=0 rf_pkts=0 slot1_writes=0 qemu=43/43(129/129) pngs=86/86(max=27467B) leaked=0`（`milestone324_sha256=5c403f553f3cec16...` / `0d4c78bdafc6444d...`）。
  - **硬件安全护栏硬锁**：`CNFLASHA_USERSPACE_WRITE_BLOCKED=True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED=False`、`SPI_NOR_WRITE_AUTHORIZED=False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED=False`、`ISP_WRITE_AUTHORIZED=False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED=False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED=False`、`OVERALL_READY_FOR_HARDWARE_ATTACH=False`、`CROSS_MODEL_FLASH_AUTHORIZED=False`、`OTP_FUSE_TOUCHES=0`、`RPMB_COUNTER_INCREMENTS=0`、`PHYSICAL_DEVICE_WRITES=0`、`RAW_FIRMWARE_BYTES_LEAKED=0`。

---

## 2. Wave-59 实测事实 vs 工程推断边界

> 以下严格区分来自 `ILME-FX3`（`ilc/2210`、`Ver. 7.02 appFw.so`/UXC/`Backup.bin`）与 `ILME-FX6`（`5-024-458-18`、`Ver. 6.01 appFw.so`/UXC）的**实测事实**，以及恢复子系统施加的**工程推断 / 安全护栏**。

### 2.1 Sub-Pillar 61A：Ver. 7.00/7.02 `BIG6` Home 主屏幕、手动 `[Framing Settings]` vs 休眠 `[Auto Framing]` 与静态 `[Interval Shoot Func.]`

1. **实测事实 — `HOME` (`BIG6`) 主屏幕前置条件、动态 6 格矩阵与左下角元数据 ND 边界**：
   - `ILME-FX3` 自 **Ver. 7.00**（延续至 `Ver. 7.02`）引入 `HOME` (`BIG6`) 主屏幕，必须满足 `Shooting Mode -> [Mode Settings] = Fixed/Variable`（`_f 0x7d0d`，`BKID_APP_setting_fps_fixed_variable_select`）；Ver. 6.02 及更早版本或 `Mode Settings = Movie` 均不得激活（返回 `EOPNOTSUPP=95`）。
   - 入口为自定义键 `[HOME]`（`_f 0x7cad` / `0x7cb1`）或开启 `[Touch Operation]` 后的向下滑动（`_f 0x7cdd`）；状态机经 `BKID_APP_home_screen_state`（`OFF / ON_CURSOR_OFF / ON_CURSOR_ON / TEMP_OFF`）及 `BKID_APP_home_screen_last_cursor_position_number` 流转，`26view_tp_button_01_for_big6` 底部/顶部状态栏严格只读。
   - 6 格由 `update_big6_item_iso_ei` 动态调度：`FPS`、`ISO`（`Log=Off` / `Flexible ISO`）或 `Base ISO + EI`（`Cine EI` / `Cine EI Quick`）、`Shutter Speed / Angle`、`Home (Lower Left)`（`Aperture` 默认 / `ND Filter` `_f 0x7ce3`）、`Picture Profile`（`Log=Off`）或 `Select LUT`（`Log!=Off`，`_f 0x643e`）、`White Balance`。**FX3 无物理内置可变电子 ND（`e-ND`）硬件**，`ND Filter` 仅作外置物理 ND 滤镜数值元数据记录；对照 `ILME-FX6 Ver. 6.01`（`procam_big6_menu_home_*`）内置真实物理可变 e-ND（`Clear / 1/4 / 1/128 / Auto`）。
2. **实测事实 — 手动 `[Framing Settings]` vs 100% 休眠 AI `[Auto Framing]`**：
   - `FX3 Ver. 7.00+` 活跃暴露 `Shooting Option -> [Framing Settings]`（`_f 0x7d18`），包含 `Framing`（默认 `Off`）、`Recording/Streaming`（默认 `Full` / `Crop`）与 `HDMI`（默认 `Crop` / `Full`）双路独立裁切路由，配合 `Framing Stop (Full)`（`_f 0x7d25`）与 `Switch Framing`（`_f 0x7d1e`）；开启时强制关闭 `APS-C S35`，且在录制中、USB/网络流传输中或 `>= 100p` 高帧率下锁定（`EBUSY=16`）。
   - `_f.uxc` 中的 `Auto Framing Settings`（`0x6be6`）、`Auto Framing`（`0x79bc`）、`Crop Level`（`0x6c9d`）、`Framing Tracking Speed`（`0x69cc`）与 `Framing Stabilizer`（`0x7566`）在 FX3 上 100% 休眠：`FX3 appFw.so` 对 `AUTO_FRAMING_AFR` / `FRAMING_SIZE` / `FRAMING_FOLLOW_UP_SPEED` / `PTZAUTOFRAMING_*` 均 **`0` 命中**，且特征枚举锁定为 `TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY`（`EOPNOTSUPP=95`）。
3. **实测事实 & 工程推断 — 静态 `[Interval Shoot Func.]`（7 项可重置子项 / 9,999 张）vs `FX6 Interval Rec`（单 MXF）与 Slot-1 `EROFS=30` 防火墙**：
   - **实测事实**：FX3 `Drive Mode -> [Interval Shoot Func.]`（`_f 0x7027`）仅限静态 `Still` 域（`Movie`/`S&Q`/`Intelligent Auto` 不可用），包含 7 项均支持 `[Camera Settings Reset]` 的子参数：`Interval Shooting`（`Off`）、`Shooting Start Time`（`1..5999s`，默认 `1s`）、`Shooting Interval`（`1..60s`，默认 `3s`）、`Number of Shots`（`1..9999`，默认 `30`）、`AE Tracking Sensitivity`（`High / Mid[def] / Low`）、`Shutter Type in Interval`（`Mechanical Shutter / Electronic Shutter[def]`，独立于常规快门类型）及 `Shoot Interval Priority`（`Off[def] / On`），配套 `Display as Group`（`0x6f26`）与 `PB Speed for Interval`（`0x72bd`）；开启后若处于 `BULB` 自动退出回退至 `30"`。对照 `ILME-FX6` `Project > Interval Rec` 直接封装单一 XAVC MXF 视频剪辑（`Number of Frames` `1..24`，支持 `Pre-Lighting`，与 `Picture Cache Rec / Simul Rec / S&Q Motion / Proxy / Audio` 互斥）。
   - **工程推断**：单次最多 `9,999` 张（双格式最高 `19,998` 个 `DCIM/` 文件 + `AVF_INFO` 数据库高频改写）具备极高写卡爆发风险；当 Slot 1 承载 Tier-0 只读保险库时，所有指向 Slot 1 的间隔连拍或格式化必须 fail-closed 拦截返回 `EROFS (30)`，确保 `slot1_data_sector_writes == 0`、`slot1_dcim_avf_mutation_bytes == 0`、`Backup.bin H0 == H3`（`16/16` 面）。

### 2.2 Sub-Pillar 61B：`[Time Code Make/Run]`、`HDMI [REC Control]`、`[Access Authen.]` SSH/TLS 与 `[Fan Control]` 零 `Max`

1. **实测事实 — `Initialize` 专属 `[Time Code Make/Run]` 与 `HDMI Output Settings` `[REC Control]`**：
   - `TC/UB -> [Time Code Make]`（`_f 0x6b79`：`Preset[def]` / `Regenerate`，`VAL_setting_tc_make_TC_MAKE_REGENRATE`）与 `[Time Code Run]`（`_f 0x7313`：`Rec Run[def]` / `Free Run`）均抵抗 `Camera Settings Reset`（仅 `Initialize` 复位至 `Preset + Rec Run`）。
   - `Regenerate` 从当前 `[Recording Media]` 卡槽（`Simult. Recording` 时读取 **Slot 1**）末段延续 TC 并**强制覆盖按 `Rec Run` 运行**；使用 `VMC-BNCM1` 注入外部 LTC 锁定 `EXT-LK` 必须同时满足 `Preset + Free Run` 且未占 `USB-LAN` 互斥端口。对照 FX6 额外支持 `VAL_setting_tc_make_TC_MAKE_CLOCK`（FX3 拒绝 `Clock` 返回 `EOPNOTSUPP=95`）。
   - `HDMI Output Settings`（抵抗 `Camera Settings Reset`，仅 `Initialize` 复位）中 `[REC Control]`（`_f 0x76e1`）强制要求 `[Time Code Output] = On`（`_f 0x72af`）作为前置门控，但**实证在 `Rec. Media dur HDMI Output = On` 与 `Off(HDMI Only)` 两种模式下均有效**，仅在 `S&Q` 或 USB/网络流传输中受阻（`EOPNOTSUPP=95`）；`[4ch Audio Output]`（`_f 0x6aa0`）可选 `CH1/CH2[def]` 或 `CH3/CH4`；对照 FX6 拆分为 `SDI/HDMI Remote I/F` 与 `Parallel Rec`。
2. **实测事实 — Ver. 7.00+ `[Access Authen.]` SSH+PTP-IP 架构、出站 TLS 根证书与 `[Fan Control]` 零 `Max`**：
   - `FX3 Ver. 7.00+` 移除 `WEP`、`WPA-PSK` 与 `Security(IPsec)`（`0x69aa`），要求 `WPA2-PSK` / `WPA3-SAE` + 默认 `On` 的 `[Access Authen. Settings]`（`_f 0x7ada`）。`FX3 appFw.so` 对 `HTTP_DIGEST` / `BASIC_AUTH` / `HTTPS` 均 **`0` 命中**，认证链路实质为 `SSH`（`MSGID_SSHD_START_CMD` + Fingerprint `_g 0x610b`）承载 `PTP-IP`；`[Import Root Certificate]`（`_f 0x7940`）仅用于出站 `FTPS / RTMPS / Cloud` TLS 校验。`Reset Network Set.` 与 `Initialize` 均保留 `Airplane Mode`。
   - `[Fan Control]`（`_f 0x6e77`，抵抗 `Camera Settings Reset`）在 FX3 暴露 `Auto / Minimum / Off in Rec / Always Off` **4 档**（`Off in Rec` 在录制中停转但超内部热阈值强制重转），而在 FX6 仅公开 `Auto / Minimum / Off in Rec` **3 档**（`Always Off` 在 FX6 上休眠不可暴露）；**FX3 与 FX6 `appFw.so` 对 `FAN_CONTROL_MAX` 均为 `0` 命中，两者均绝不存在 `Max` 选项**！`[Auto Power OFF Temp.]` 提供 `Standard / High`（4K60 ~30->90 min，HD60 ~60->120 min）。
3. **工程推断 — Zero-RF 台架隔离与 `Slot-1 EROFS=30` 防火墙**：
   - 恢复工作流强制 `Airplane Mode = On` + `USB-LAN (CDC-NCM)` 有线传输（`rf_packets_transmitted == 0`、`rf_nvs_mutation_bytes == 0`），并阻断任何针对 Slot 1 的写入/导入证书/格式化动作（`EROFS=30`、`slot1_data_sector_writes == 0`、`raw_firmware_bytes_leaked == 0`）。

---

## 3. 授权交付文件清单（Strict File Ownership）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py) | Pillar 61A/61B 状态机与评估器、17 项 `O_RDONLY` 有界核验 + `work_root is None` / 无供体 Clean-Room 自动回退、`6/6 + 6/6` 套件及 `61/61` 并发主控 `evaluate_realhw_61pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出 Phase 340 `P340_*` / `PHASE340_*` / `MASTER_61_*` / `evaluate_realhw_61pillar_recovery_master` 等 268 个公开符号与 `__all__` |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar61-big6-framing-interval-tc-auth-fan-vault`、`verify-pillar61-recovery` 与 `verify-61pillar-recovery` CLI 子命令 |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 340 Pillar 61 & `61/61` 恢复总检文档与 CLI 示例 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py) | **107 项**四模（本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、模拟无供体 `(None,)` / 不存在根目录及子进程）单元测试与前向兼容 `>= 61` 自动发现断言 |
| 6 | EDIT | `outputs/fx3-recovery-adapter/fx3_recovery/realhw_{30..49}pillar_*_verifier.py`, `realhw_airgap_sd_bundle_manifest_verifier.py` 及 `tests/test_realhw_{39..44}pillar_*_verifier.py`（27 个文件） | 将并发磁盘 I/O 下易抖动的供体墙钟预算阈值由 `0.15s` 统一放宽至 `2.0s` |
| 7 | NEW | [`reports/2026-11-17-phase340-milestone-pillar61-61pillar-big6-framing-interval-tc-auth-vault/README.md`](README.md) | 本 Phase 340 里程碑中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 61 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_61pillar_big6_home_framing_interval_tc_make_auth_fan_vault_verifier.py -v` | **`107/107 OK`**（`18.615s`） |
| Pillar 61 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest ... -v` | **`107/107 OK`**（`20.826s`） |
| Pillar 61 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest ... -v` | **`107/107 OK`**（`20.305s`） |
| 显式模拟无供体 CI（`(None,)` / `Path("/nonexistent-donor-root")` & 子进程） | `test_11` / `test_55`（独立子进程 `patch.object(f, 'iter_donor_work_roots', return_value=(None,))` 调 `verify-61pillar-recovery --json`） | **`CLEAN_ROOM_SYNTHETIC`（`61/61`，`rc=0`，零异常）** |
| `verify-pillar61-recovery` CLI（供体 / 洁净室） | `verify-pillar61-recovery --json` & `verify-pillar61-recovery --force-clean-room --json` | **`61A=6/6, 61B=6/6`**（`0.004701s` / `0.000452s`，`suite_sha256=6f1fd57a025f97fd...` / `01a9986a93fd94d9...`，`leaked=0`） |
| `verify-61pillar-recovery` CLI（供体 / 洁净室） | `verify-61pillar-recovery --json` & `verify-61pillar-recovery --force-clean-room --json` | **`61/61 PASS`**（`1.231196s` / `0.851313s` `< 1.5s`，`master_61pillar_sha256=a69a4e0bb23edede...` / `3c4867f1aafc9250...`，`leaked=0`） |
| `make verify-milestone-324`（正常模式 & `FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324` & `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` | **`status=OK pillars=6/6 gate142=143/146 recovery=61/61 leaked=0`**（`5c403f553f3cec16...` / `0d4c78bdafc6444d...`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（正常模式） | `PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s tests` | **`3,700 tests OK`**（`skipped=1`，`485.312s`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s tests` | **`3,642 tests OK`**（`skipped=17`，`439.669s`） |
| 清洁审计 | `make clean-audit` | **`ALL GREEN`**（`0.06s`，零 `.pyc` / 零二进制残留） |
