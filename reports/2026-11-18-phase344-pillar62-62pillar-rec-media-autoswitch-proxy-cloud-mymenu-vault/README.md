# Phase 344 里程碑交付报告：Recovery Pillar 62（Wave-60）与 `62/62` 统一恢复总检（`verify-62pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`62/62` 恢复支柱闭环里程碑达成，`VERIFIED_62OF62_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：
  1. 基于 [Wave 60 全球实机情报报告](../2026-11-17-global-sony-wave60-milestone-rec-media-auto-switch-proxy-cloud-mymenu-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` `ALCIN_UUD` vs `ILME-FX6 Ver. 6.01` `5-024-458-18` `CHAPLIN`），落地 **Phase 344 Recovery Pillar 62**（Sub-Pillar **62A** `6/6` + Sub-Pillar **62B** `6/6`）及并发式 **`62/62` 统一恢复总检聚合器** [`evaluate_realhw_62pillar_recovery_master`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py)（`schema = "realhw_62pillar_recovery_master_v1"`，`verify-62pillar-recovery`），并通过包根动态导出自动接入 Milestone 311 / 324 自动发现接口（`recovery=62/62`），未修改 `outputs/fx6-on-fx3-closure/` 任何文件。
  2. 全量实现无供体 CI 保护与有界只读取证：[`_resolve_phase344_donor_path`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py) 内置 `work_root is None` 防护，[`inspect_phase344_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py) 严格以 `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK` 在 `< 2.0s` 预算内检验 `17` 项 Wave-60 本地供体（大 ELF 仅读前 `4096B` 头部，小文件全量校验），并在缺少本地供体或 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 时自动切换至 `CLEAN_ROOM_SYNTHETIC` 并返回 `rc=0`。
  3. 仅触碰本次授权的 **6 个文件**，未改动任何无关目录。
- **实测结果摘要（双模 & 4 模全绿）**：
  - `verify-pillar62-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`62A=6/6`、`62B=6/6`，`17` 项 Wave-60 本地供体严格 `O_RDONLY` 核验通过，`elapsed=0.005s`，`suite_sha256=884efaab437d2017...`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`62A=6/6`、`62B=6/6`，`elapsed=0.000s`，`suite_sha256=33e76bdb7711399d...`，`raw_firmware_bytes_leaked=0`。
  - `verify-62pillar-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`pillars=62/62`，`all_passed=True`，`elapsed=1.223s`（`< 1.5s` 快速 CLI 预算），`master_62pillar_sha256=ddacf96dfa662223...`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`pillars=62/62`，`all_passed=True`，`elapsed=0.845s`（`< 1.5s`），`master_62pillar_sha256=995f0964b322b262...`，`raw_firmware_bytes_leaked=0`。
    - 模拟无供体 CI 子进程（`iter_donor_work_roots -> (None,)`）：`rc=0`，自动切换 `verification_mode="CLEAN_ROOM_SYNTHETIC"`，`pillars_passed=62/62`。
  - `make verify-milestone-324`（正常模式 & `FX3_FX6_FORCE_CLEAN_ROOM=1`）：
    - 正常模式：`status=OK pillars=6/6 gate142=143/146 recovery=62/62 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 auditors=45/45 vm_stages=74/74 h0_eq_h3=16/16 e_nd_tx=0 rf_pkts=0 slot1_writes=0 qemu=44/44(132/132) pngs=88/88(max=27467B) leaked=0`（`milestone324_sha256=53f78b6814f9614e...`）。
    - 洁净室模式：`status=OK ... recovery=62/62 ... leaked=0`（`milestone324_sha256=f0d17c8854c61414...`）。
  - **硬件安全护栏硬锁**：`CNFLASHA_USERSPACE_WRITE_BLOCKED=True`、`PERSISTENT_EMMC_WRITES_AUTHORIZED=False`、`SPI_NOR_WRITE_AUTHORIZED=False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED=False`、`ISP_WRITE_AUTHORIZED=False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED=False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED=False`、`OVERALL_READY_FOR_HARDWARE_ATTACH=False`、`CROSS_MODEL_FLASH_AUTHORIZED=False`、`OTP_FUSE_TOUCHES=0`、`RPMB_COUNTER_INCREMENTS=0`、`PHYSICAL_DEVICE_WRITES=0`、`RAW_FIRMWARE_BYTES_LEAKED=0`。

---

## 2. Wave-60 实测事实 vs 工程推断边界

> 以下严格区分来自 `ILME-FX3`（`ilc/2210`、`Ver. 7.02 appFw.so`/UXC/`Backup.bin`）与 `ILME-FX6`（`5-024-458-18`、`Ver. 6.01 appFw.so`/UXC）的**实测事实**，以及恢复子系统施加的**推断 / 工程安全护栏**。

### 2.1 Sub-Pillar 62A：`[Rec. Media Settings]` 演进、`VPG200/VPG400` 速率门禁、`[Auto Switch Media]` 溢流风险与 `[Proxy Settings]` (`sq_proxy`) 真值

1. **实测事实 — `[Prioritize Rec. Media]` 休眠与拆分后抗 Reset 的 `[Recording Media]` / `[Auto Switch Media]`**：
   - `FX3 _f.uxc` 中遗留旧 Alpha 字符串 `[Prioritize Rec. Media]`（`_f 0x719e`），但 `FX3 appFw.so` 对 `prioritize` 为 **`0` 命中**；自 `Ver. 2.00+` 至 `Ver. 7.02` 已重构为独立拆分的 **`[Recording Media]`**（Still：`BKID_APP_setting_still_recording_media` = `Slot 1 [默认]` / `Slot 2` / `Simult. Recording` / `Sort Recording`，且 `Sort Recording` 强制两卡共享同一 JPEG/HEIF Quality、Image Size 与 RAW File Type；Movie：`BKID_APP_setting_movie_recording_media` = `Slot 1 [默认]` / `Slot 2` / `Simult. Recording`，**无 Movie `Sort Recording`**，否则返回 `EOPNOTSUPP=95`）和 **`[Auto Switch Media]`**（`_f 0x6dd9`，`BKID_APP_setting_relay_rec` = `Off [默认]` / `On`）。
   - `[Recording Media]` 与 `[Auto Switch Media]` 均**抵抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 复位为 `Slot 1` + `Off`）；`Simult. Recording` 强制两卡文件系统完全一致（同 `exFAT` 或同 `FAT32`，混用返回 `EINVAL=22`）。
   - 对照 `ILME-FX6 Ver. 6.01`（`5-024-458-18` pp. 54, 99）：采用 `Project > Simul Rec`（`BKID_APP_SETTING_SIMUL_REC`）配合双 `Rec Button Set` 与 `Relay Rec`，但与 `3840x2160P` 特定网络模式、`Wired/Wireless LAN`、`Modem`、`Proxy Rec`、`Streaming` 及 `Auto Upload (Proxy): Chunk` 存在硬互斥（`FX6_2 0x41ee..0x41f7`）。
2. **推断 / 安全护栏 — Tier-0 `Slot 1` 溢流双锁与 `EROFS=30` 写防火墙**：
   - 若试台将 `[Recording Media]` 设为 `Slot 2`（或 `Sort`/`Simult.`），而抗 Reset 的 `[Auto Switch Media]` 残留为 `On`，当 `Slot 2` 写满或无卡时，FX3 固件会自动将 `DCIM/`、`M4ROOT/`、`AVF_INFO` 录制流静默滚入 `Slot 1`，威胁 Tier-0 恢复保险库。
   - 护栏强制双锁：NVRAM 校验 `RELAY_REC_OFF` + `SLOT_2`，且 `Slot 1` 借助 `PRM_HAITA_setting_relay_rec_*_media_read_only_state_slot1` 与 VFS `EROFS (errno 30)` 零写入阻断（`slot1_data_sector_writes == 0`、`slot1_dcim_m4root_avf_mutation_bytes == 0`、`Backup.bin H0 == H3` `16/16` 面）。
3. **实测事实 — `VPG200/VPG400` vs `SDXC V60/V90` 卡速门禁矩阵**：
   - `Movie XAVC HS/S 4K`（`280 Mbps`）需 `SDXC V60+` / `CFexpress Type A (VPG200+)`；`XAVC S-I 4K / DCI 4K`（`600 Mbps`）需 `SDXC V90+` / `CFexpress Type A (VPG200+)`。
   - `S&Q XAVC S-I 4K` 峰值 **`1200 Mbps`** 严禁 `SDXC`（`EINVAL=22`），强制 `CFexpress Type A`，且 `FX3 base.uxc` 实证存在 **`CFexpress VPG200`**（`0xe228`）与 **`CFexpress VPG400`**（`0xe224` / `0xe93f` / `0xe9aa`）双层告警门禁与关闭 `[Proxy Recording]` 降档提示。
4. **实测事实 & 推断 — `[Proxy Settings]` (`sq_proxy`) `XAVC S-I DCI 4K` 允许 vs `120p/100p` 禁录与 `M4ROOT/SUB/*S03.MP4`**：
   - `FX3 appFw.so` 使用 **`BKID_APP_setting_sq_proxy_{recording,file_format,record_setting}`**（`0` 条 `PRM_HAITA_*proxy*` 互斥串）：`[Proxy Recording]` 默认 `Off`（可被 `Camera Settings Reset` 复位）；`XAVC S HD`（`1280x720 6M 4:2:0 8bit` 默认）vs `XAVC HS HD`（`1920x1080 16M / 9M [默认] 4:2:0 10bit`，最高 `59.94p/50p`）；`16M 4:2:0 8bit`（`_f 0x6b8f`）与 `9M 4:2:0 8bit` 为休眠跨机型枚举。
   - **关键纠偏**：`Proxy` 仅在正常 `Movie 119.88p/100p` 与 `S&Q 120/100fps` 下强制禁用；**`XAVC S-I DCI 4K`（最高 `59.94p/50p`）允许开启 Proxy**（受卡速门禁约束）。Proxy 写入 `/PRIVATE/M4ROOT/SUB/*S03.MP4`（SD）或 `/M4ROOT/SUB/*S03.MP4`（CFexpress），机内不可回放，随母片连带删除/保护；Slot-1 上一切 Proxy 写/删/护操作均受 `EROFS=30` 防火墙拦截。

### 2.2 Sub-Pillar 62B：`[Creators' Cloud]` `*` 持久化、`[Cnct. while Power OFF]` 关机 BLE RF 危害与 `[My Menu]` `42` 槽位 vs FX6 `20` 项锁机

1. **实测事实 — `[Creators' Cloud]` `*` 跨 `[Initialize]` 持久化与 FTP 互斥**：
   - `Ver. 4.00..7.02` 覆盖 `C3 Portal` 与 `Creators' Cloud`，`Ver. 7.00+` 新增 `Clip Flag`（`OK/NG/KEEP`）直传筛选（`Ver. < 7.00` 返回 `EOPNOTSUPP=95`）；`Cloud Connection` 与 `FTP Transfer` 强制互斥（`CLOUD_CONNECTION_ON_FTP_OFF`，`EBUSY=16`）。
   - `Cloud Connection *` 与 `Cloud Information *` 带星号 `*`：**同时存活于 `[Camera Settings Reset]` 与 `[Initialize]`**，仅可在 `Cloud Information` 显式删除账号清除。
2. **实测事实 & 推断 — `[Cnct. while Power OFF]` 物理关机 BLE 供电危害与 Zero-RF 护栏**：
   - **实测事实**：`[Cnct. while Power OFF]`（`BKID_APP_extern_menu_cnct_while_power_off`，`_f 0x6ab3`，默认 `Off`）抵抗 `[Camera Settings Reset]`（需 `[Reset Network Set.]` 或 `[Initialize]` 清除）。当其为 `On` 且已完成蓝牙配对时，**即使机身物理电源开关拨至 `OFF`，`UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER` 仍维持 BLE 通电广播监听**，以便 *Creators' App* 远程唤醒并缓慢消耗 `NP-FZ100` 电池。对照 `ILME-FX6` **无蓝牙硬件**（`0` BLE 供电路径，`On` 返回 `EOPNOTSUPP=95`）。
   - **推断 / Zero-RF 台架护栏**：暗室与安全台架严禁以"物理开关 = `OFF`"推定射频静默，必须同时强制 **`[Airplane Mode] = On` 且 `[Cnct. while Power OFF] = Off`**（`rf_packets_transmitted == 0`、`rf_nvs_mutation_bytes == 0`），并配合 `Slot-1 EROFS=30` 防火墙阻断 `FORMAT_QUICK` / `FORMAT_FULL`（`slot1_data_sector_writes == 0`、`slot1_vault_mutation_bytes == 0`）。
3. **实测事实 — `[My Menu]` `6×7=42` 槽位纠偏 vs FX6 `20` 项 `User Menu with Lock`**：
   - **实测事实（关键纠偏）**：`ILME-FX3 Ver. 7.02` `[My Menu]` 实为 **`6 页 × 7 项 = 42` 个 NVRAM 槽位**（`BKID_APP_mymenu_group{1..6}_setting_list{0..6}`，**而非旧 Alpha 的 `30` 或误传 `36`**；`group0`/`group7`/`list7` 均 `0` 命中）。边界 `page=7` 或 `slot=7` 返回 `EINVAL=22`；禁止添加 `(Playback)` 项（`EOPNOTSUPP=95`）；抵抗 `[Camera Settings Reset]` 与 `[Reset Network Set.]`（仅 `[Initialize]` 或 `[Delete All]` 清空）。
   - 对照 `ILME-FX6 Ver. 6.01`（`5-024-458-18` pp. 88–89）：`User Menu` 上限 **`20` 项**，提供 **`User Menu Only`** 与租赁防篡改 **`User Menu with Lock`**（需 **`Multi-selector + MENU`** 双键组合呼出 + 4 位数字 PIN `0000–9999`，且 **绝不随 `All File` 或 `Scene File` 导出**）。

---

## 3. 授权交付文件清单（Strict 6-File Ownership）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py) | Pillar 62A/62B 状态机与评估器、17 项 `O_RDONLY` 有界核验 + `work_root is None` / 无供体 Clean-Room 自动回退、`6/6 + 6/6` 套件及 `62/62` 并发主控 `evaluate_realhw_62pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出 Phase 344 `P344_*` / `PHASE344_*` / `MASTER_62_*` / `evaluate_realhw_62pillar_recovery_master` 等 253 个公开符号与 `__all__` |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar62-rec-media-autoswitch-proxy-cloud-mymenu-vault`、`verify-pillar62-recovery` 与 `verify-62pillar-recovery` CLI 子命令（`help=` 已做 `%%` 转义） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 344 Pillar 62 & `62/62` 恢复总检文档与 CLI 示例 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py) | **146 项**（`>= 100`）四模（本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、模拟无供体 `work_root=None` 及子进程）单元测试、参数化矩阵与 `>= 62` 自动发现断言 |
| 6 | NEW | [`reports/2026-11-18-phase344-pillar62-62pillar-rec-media-autoswitch-proxy-cloud-mymenu-vault/README.md`](README.md) | 本 Phase 344 里程碑中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 62 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest -v outputs/fx3-recovery-adapter/tests/test_realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py` | **`146/146 OK`**（`18.837s`） |
| Pillar 62 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py` | **`146 tests OK (skipped=1)`**（`19.556s`，跳过项为本地供体 SHA 对比） |
| Pillar 62 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_62pillar_rec_media_autoswitch_proxy_cloud_mymenu_vault_verifier.py` | **`146 tests OK (skipped=1)`**（`20.378s`） |
| 显式模拟无供体 CI（`(None,)` / 不存在根目录 & 子进程） | `test_10` / `test_55`（独立子进程 `patch.object(_fx3_files, 'iter_donor_work_roots', return_value=(None,))` 调 `verify-62pillar-recovery --json`） | **`CLEAN_ROOM_SYNTHETIC`**（`62/62`，`rc=0`，零 `TypeError`） |
| `verify-pillar62-recovery` CLI（供体 / 洁净室） | `verify-pillar62-recovery` & `verify-pillar62-recovery --force-clean-room` | **`62A=6/6, 62B=6/6`**（`0.005s` / `0.000s`，`suite_sha256=884efaab437d2017` / `33e76bdb7711399d`，`leaked=0`） |
| `verify-62pillar-recovery` CLI（供体 / 洁净室） | `verify-62pillar-recovery` & `verify-62pillar-recovery --force-clean-room` | **`62/62 PASS`**（`1.223s` / `0.845s` `< 1.5s`，`master_62pillar_sha256=ddacf96dfa662223` / `995f0964b322b262`，`leaked=0`） |
| `make verify-milestone-324`（双模） | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324` | **`status=OK pillars=6/6 gate142=143/146 recovery=62/62 leaked=0`**（`53f78b6814f9614e...` / `f0d17c8854c61414...`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（正常模式） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -t outputs/fx3-recovery-adapter/tests` | **`3,846 tests OK (skipped=1)`**（`472.487s`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests -t outputs/fx3-recovery-adapter/tests` | **`3,788 tests OK (skipped=18)`**（`406.915s`） |
| 清洁审计 | `make clean-audit` | **`ALL GREEN`**（`0.07s`，零 `.pyc` / 零二进制残留） |
