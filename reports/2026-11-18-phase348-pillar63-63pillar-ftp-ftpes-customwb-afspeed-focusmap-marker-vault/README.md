# Phase 348 里程碑交付报告：Recovery Pillar 63（Wave-61）与 `63/63` 统一恢复总检（`verify-63pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`63/63` 恢复支柱闭环里程碑达成，`VERIFIED_63OF63_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：
  1. 基于 [Wave 61 全球实机情报报告](../2026-11-17-global-sony-wave61-ftp-ftps-customwb-af-speed-focusmap-marker-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` / `di/ftp_2210` `PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01` `5-024-458-18` `PRODUCT_MODEL_CHAPLIN`），落地 **Phase 348 Recovery Pillar 63**（Sub-Pillar **63A** `6/6` + Sub-Pillar **63B** `6/6`）及并发式 **`63/63` 统一恢复总检聚合器** [`evaluate_realhw_63pillar_recovery_master`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py)（`schema = "realhw_63pillar_recovery_master_v1"`，`verify-63pillar-recovery` / `verify-pillar63-recovery`），并通过包根动态导出自动接入 `realhw_milestone324_master_gate.py`（`recovery=63/63`），未修改 `outputs/fx6-on-fx3-closure/` 任何文件。
  2. 全量实现无供体 CI 保护与有界只读取证：[`_resolve_phase348_donor_path`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py) 内置 `work_root is None` 防护，[`inspect_phase348_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py) 严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 在 `< 2.0s` 预算内检验 `17` 项 Wave-61 本地供体（大 ELF 仅读前 `4096B` 头部，小文件全量校验），并在缺少本地供体或 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换至 `CLEAN_ROOM_SYNTHETIC` 并返回 `rc=0`。
  3. 严格仅触碰本次授权的 **6 个文件**，未改动任何无关目录。
- **实测结果摘要（双模 & 4 模全绿）**：
  - `verify-pillar63-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`63A=6/6`、`63B=6/6`，`17` 项 Wave-61 本地供体严格 `O_RDONLY` 核验通过，`elapsed=0.006s`，`suite_sha256=c988983cc01a49536e2c9e48dc6f31ac41cc429c75215cb6687038747f3a4661`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`63A=6/6`、`63B=6/6`，`elapsed=0.000s`，`suite_sha256=bf0b8beef29340b934520f04fbbfba9700eca39ac31f66777ccc173978b1fb5a`，`raw_firmware_bytes_leaked=0`。
  - `verify-63pillar-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`pillars=63/63`，`all_passed=True`，`elapsed=1.257s`（`< 1.5s` 快速 CLI 预算），`master_63pillar_sha256=e2eb307782d099f5a0742acac05ed3efdc198ac2798f356bd97d3db7053f5600`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`pillars=63/63`，`all_passed=True`，`elapsed=0.869s`（`< 1.5s`），`master_63pillar_sha256=de715c59223d5cd9b09222783170c0c279140d6f1358cae4011458868b80fca9`，`raw_firmware_bytes_leaked=0`。
    - 模拟无供体 CI 子进程（`iter_donor_work_roots -> (None,)`）：`rc=0`，自动切换 `verification_mode="CLEAN_ROOM_SYNTHETIC"`，`pillars_passed=63`。
  - `make verify-milestone-324`（正常模式 & `FX3_FX6_FORCE_CLEAN_ROOM=1`）：
    - 正常模式：`status=OK pillars=6/6 gate142=145/148 recovery=63/63 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 auditors=45/45 vm_stages=75/75 h0_eq_h3=16/16 e_nd_tx=0 rf_pkts=0 slot1_writes=0 qemu=45/45(135/135) pngs=90/90(max=27467B) leaked=0`（`milestone324_sha256=1b8aedb00c22ba88...`）。
    - 洁净室模式：`status=OK ... recovery=63/63 ... leaked=0`（`milestone324_sha256=9a5f826e878ce429...`）。
  - **硬件安全护栏硬锁**：`CNFLASHA_USERSPACE_WRITE_BLOCKED=True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED=False`、`SPI_NOR_WRITE_AUTHORIZED=False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED=False`、`ISP_WRITE_AUTHORIZED=False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED=False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED=False`、`OVERALL_READY_FOR_HARDWARE_ATTACH=False`、`CROSS_MODEL_FLASH_AUTHORIZED=False`、`OTP_FUSE_TOUCHES=0`、`RPMB_COUNTER_INCREMENTS=0`、`PHYSICAL_DEVICE_WRITES=0`、`RAW_FIRMWARE_BYTES_LEAKED=0`。

---

## 2. Wave-61 实测事实 vs 工程推断边界

> 以下严格区分来自 `ILME-FX3`（`ilc/2210`、`di/ftp_2210`、`Ver. 7.02 appFw.so`/UXC/`Backup.bin`）与 `ILME-FX6`（`5-024-458-18`、`Ver. 6.01 appFw.so`/UXC）的**实测事实**，以及恢复子系统施加的**推断 / 工程安全护栏**。

### 2.1 Sub-Pillar 63A：`[FTP Transfer Func.]`（`FTP`/`FTPES` vs 零 `SFTP`、`9` 槽位、`USB-LAN` 旁路、`Slot 1` `AVF_INFO` `EROFS=30`）与白平衡深真值

1. **实测事实 — `[FTP Transfer Func.]` `9` 服务器槽位、被动 `FTP`/`FTPES` 与零 `SFTP`/`Transfer JPEG Size`**：
   - `ILME-FX3 Ver. 7.02` 暴露 `Server 1..9`（`BKID_APP_ftp_server_settings_*0..8`，抵御 `[Camera Settings Reset]`，仅由 `[Reset Network Set.]` 或 `[Initialize]` 清空），仅支持明文 `FTP` 与 `FTPES`（`FTPS` Explicit TLS，`SET_SERVER_SECURE_PROTOCOL_{OFF,ON}`，`_f 0x6553` `'Connects with FTPES.'`）且仅支持 **Passive Mode**。
   - `FX3 appFw.so` 对 `sftp`、`ftpes`、`passive_mode` 及休眠字符串 `[Transfer JPEG Size]`（`_f 0x6aed`）/`[Transfer HEIF Size]`（`_f 0x63dd`）均为 **`0` 命中**，因此恢复门禁对 `SFTP`、`Active Mode` 与 `Transfer JPEG/HEIF Size` 全部返回 `EOPNOTSUPP=95`；根证书强制使用 **`cacert.pem`**（`<= 1 MiB`）置于 **`Slot 1` 根目录**。
   - 对照 `ILME-FX6 Ver. 6.01`（`5-024-458-18` pp. 76–78）：UI 暴露 `Server Settings1..3`（+ `Ci`/`NCM`/`Relay`）、支持 **`Passive Mode On/Off`（含 Active Mode）**、根证书 **`certification.pem`** 位于 **`Slot B`**，并独有 `Auto Upload (Proxy): Chunk`（与 `Simul Rec`/`Relay Rec` 互斥）。
2. **实测事实 + 推断/护栏 — `Slot 1` `AVF_INFO` `EROFS=30` 防火墙与 Zero-RF `USB-LAN` 双锁**：
   - **实测事实**：`FX3 base.uxc 0x0a13`（`'Image Database File error.\nFTP transfer results will be reset if recovered. Recover?'`）结合 `save_ftp_transfer_list_to_media`、`CONTENT_INFO_FTP_TRANS_STAT_{COMPLETE,FAILED,NOT_TARGET,RESERVED}` 与 `PRM_HAITA_ftp_display_result_media_*_slot1`，证实 FTP 状态写回与 `AVF_INFO` 数据库耦合；同时 `[Airplane Mode] = On` 仅阻断 Wi-Fi/BLE，**仍放行有线 `USB-LAN` FTP（`USB_ETHER`）**。
   - **推断 / 工程护栏**：Tier-0 `Slot 1` 保险库保护防火墙必须以 `EROFS=30` 阻断所有非只读 `Slot 1` 操作（`SAVE_FTP_TRANSFER_LIST_SLOT1`、`WRITE_FTP_TRANS_STAT_SLOT1`、`RECOVER_AVF_INFO_SLOT1`、`FORMAT_QUICK`、`FORMAT_FULL` -> `slot1_data_sector_writes == 0`、`Backup.bin H0 == H3`）；Zero-RF 暗室/气隙台架必须双锁 `[Airplane Mode] = On` **且** `[USB-LAN] = Off`（`rf_packets_transmitted == 0`、`usblan_packets_transmitted == 0`）。
3. **实测事实 — 白平衡深真值（`Custom 1..3`、`[Priority Set in AWB]`、`[Shutter AWB Lock]`、`[Shockless WB]` 与 `Cine EI`）**：
   - `Auto`（默认）、`C.Temp./Filter` `2500K..9900K`（步进 `100K`）、`Custom 1..3`（`CAMSET*.DAT` 明确排除；在 `Log != Off` / `S-Log3` / `PPLUT1..4` 下执行 `[Custom Setup]` 触发 `base 0x0220` / `_f 0x63ac` `Custom WB Error` 告警）。
   - `Cine EI` / `Cine EI Quick` 强制锁定禁用 `Auto` 与 `Underwater Auto`；`[Priority Set in AWB]`（`Standard`/`Ambience`/`White`）与 Movie/S&Q `[Shockless WB]`（`Off`/`1 [默认]`/`2`/`3`，直接调节 `C.Temp.`/`A-B`/`G-M` 微调时立即旁路）均**可被 `[Camera Settings Reset]` 复位**；而 **Still 专属 `[Shutter AWB Lock]`**（`Off [默认]`/`Shut. Halfway`/`Cont. Shooting`）**抗 `[Camera Settings Reset]`**（`Not available`，Movie 态返回 `EOPNOTSUPP=95`）。
   - 对照 `ILME-FX6`：物理三档 `WHT BAL`（`PRST`/`A`/`B`）、`Memory A..H`（8 组）与 `ATW Speed 1..5`（在 `Cine EI` 下锁定 `ATW`）。

### 2.2 Sub-Pillar 63B：Movie AF `1..7` / `1..5` 同源纠偏、App 专属 `[Focus Map]` 辟谣与 8 项抗 Reset 辅助 + Clean-HDMI 隔离

1. **实测事实（CRITICAL 跨机纠偏）— FX3 与 FX6 共享 `AF Transition Speed 1..7` & `AF Subj. Shift Sens. 1..5`**：
   - `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 的 `[AF Transition Speed]` 均为 **`1..7`**（FX3 默认 `5`），且两者 **`[AF Subj. Shift Sensitivity]` 均严格为 `1..5`**（FX3 默认 `5 (Responsive)`；直接解析 `FX6 appFw.so` 验证 `6`/`7` 均为 **`0` 命中**，且 FX6 同源枚举亦止步于 `MOVIE_AF_SUBJ_SHIFT_SENS_5_RESPONSICE`）；`[AF Assist]`（默认 `Off`）明确不兼容 `SELP1650` / `SEL18200LE`。
2. **实测事实（CRITICAL 辟谣）— `ILME-FX3` 机内零 `[Focus Map]` UI，Ver. 6.00+ 仅面向 *Monitor & Control***：
   - `ILME-FX3 Ver. 7.02` 在机内菜单与自定义按键中存在 **0 个 `[Focus Map]` 入口**（`FX3 appFw.so` 对 `BKID_APP_USER_MENU_FOCUS_MAP` 与 `ASSIGNABLE_SWITCH_FOCUS_MAP` 均为 **`0` 命中** -> 机内请求返回 `EOPNOTSUPP=95`）；系在 `Ver. 6.00+` 起经 `to_remote_event_focus_map` / `sequence_notify_focus_map` **专供外部 *Monitor & Control* App `Ver. 2.1.0+`** 使用，且于 **`>= 150 fps`（如 `200/240fps`）**、回放控制、`Auto Framing`、非 PDAF/无镜头/转接环、USB 远程/UVC 下禁用。
   - 对照 `ILME-FX6 Ver. 6.01` 具备原生机内 `Focus Map`（受 `<= 6 fps` 与 `>= 150 fps` 双帧率阈值及 `HDMI RAW`/放大/数字扩展互斥约束）。
3. **实测事实 — 8 项抗 Reset 监看辅助（`[Marker Display]` 15 比例 + 4 色 `[Peaking Display]`）与 Clean-HDMI `0 px` 隔离**：
   - Movie/S&Q `[Marker Display]` 5 项（`Marker Display`、`Center Marker`、`Aspect Marker` [`Off` + **`15` 种激活比例** `9:16..2.39:1` = `16` 态]、`Safety Zone` [`Off`/`80%`/`90%`]、`Guideframe` [`Off`/`On`]）与 `[Peaking Display]` 3 项（`Off`/`On`、`High`/`Mid [默认]`/`Low`、`Red`/`Yellow`/`Blue`/`White [默认]`）**全部 8 项均抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 清零）。
   - 无论 `[HDMI Info. Display]` 取 `On` 或 `Off`，此 8 项均**仅在机内屏幕渲染，HDMI 输出 `0 px`**；`[Marker Display]` 在 `[Focus Magnifier]` 激活期间自动隐藏。
   - 对照 `ILME-FX6`：`Aspect Mask 0..15`、自定义 `Custom` 比例、`Safety Area 80/90/92.5/95%`、像素级 `User Box`（`Width 3..479`, `Height 3..269`, `H Pos -476..+476`, `V Pos -266..+266`）以及 `B&W` 峰值色彩（替代 FX3 `White`）。

---

## 3. 授权交付文件清单（Strict 6-File Ownership）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py) | Pillar 63A/63B 状态机与评估器、17 项 `O_RDONLY` 有界核验 + `work_root is None` / 无供体 Clean-Room 自动回退、`6/6 + 6/6` 套件及 `63/63` 并发主控 `evaluate_realhw_63pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出 Phase 348 `P348_*` / `PHASE348_*` / `MASTER_63_*` / `evaluate_realhw_63pillar_recovery_master` 等全部公开符号与 `__all__` |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar63-ftp-ftpes-customwb-afspeed-focusmap-marker-vault`、`verify-pillar63-recovery` 与 `verify-63pillar-recovery` CLI 子命令（`help=` 已做 `%%` 转义） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 348 Pillar 63 & `63/63` 恢复总检文档与 CLI 示例 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py) | **131 项**（`>= 100`）四模（本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、模拟无供体 `work_root=None` 及子进程）单元测试、参数化矩阵与 `>= 63` 自动发现断言 |
| 6 | NEW | [`reports/2026-11-18-phase348-pillar63-63pillar-ftp-ftpes-customwb-afspeed-focusmap-marker-vault/README.md`](README.md) | 本 Phase 348 里程碑中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 63 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py -v` | **`131/131 OK`**（`20.433s`） |
| Pillar 63 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py -v` | **`131/131 OK`**（`20.041s`） |
| Pillar 63 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_63pillar_ftp_ftpes_customwb_afspeed_focusmap_marker_vault_verifier.py -v` | **`131/131 OK`**（`20.468s`） |
| 显式模拟无供体 CI（`(None,)` / 不存在根目录 & 子进程） | `test_07` / `test_43`（独立子进程 `patch.object(fr.files, 'iter_donor_work_roots', return_value=(None,))` 调 `verify-63pillar-recovery --json`） | **`CLEAN_ROOM_SYNTHETIC`**（`63/63`，`rc=0`，零 `TypeError`） |
| `verify-pillar63-recovery` CLI（供体 / 洁净室） | `verify-pillar63-recovery` & `verify-pillar63-recovery --force-clean-room` | **`63A=6/6, 63B=6/6`**（`0.006s` / `0.000s`，`suite_sha256=c988983cc01a4953` / `bf0b8beef29340b9`，`leaked=0`） |
| `verify-63pillar-recovery` CLI（供体 / 洁净室） | `verify-63pillar-recovery` & `verify-63pillar-recovery --force-clean-room` | **`63/63 PASS`**（`1.257s` / `0.869s` `< 1.5s`，`master_63pillar_sha256=e2eb307782d099f5` / `de715c59223d5cd9`，`leaked=0`） |
| `make verify-milestone-324`（双模） | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324` & `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` | **`status=OK pillars=6/6 gate142=145/148 recovery=63/63 auditors=45/45 vm_stages=75/75 qemu=45/45(135/135) pngs=90/90(max=27467B) leaked=0`**（`1b8aedb00c22ba88...` / `9a5f826e878ce429...`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（正常模式） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`3,977 tests OK (skipped=1)`**（`545.367s`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`3,919 tests OK (skipped=18)`**（`484.550s`） |
| 清洁审计 | `make clean-audit` | **`ALL GREEN`**（`1.15s`，零 `.pyc` / 零二进制残留） |
