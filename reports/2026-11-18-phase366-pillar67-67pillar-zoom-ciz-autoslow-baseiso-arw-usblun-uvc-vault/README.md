# Phase 366 结项报告：Recovery Pillar 67 与 `67/67` 统一恢复总检里程碑（Wave-65 `[Zoom Range]`/`8` 档变焦速度、`[Auto Slow Shutter]` 6+ 锁死/静态 `[ISO AUTO Min. SS]`/双原生 Base ISO、休眠 `Lossless Comp` `.ARW`/`[HLG Still Image]`/`Sort Recording`、`[USB LUN Setting]=Single` `Slot 1` 险境/`NP-FZ100` PD/双机休眠 `UVC` 防火墙）

- **日期**：`2026-11-18`
- **任务 / 阶段**：`H461` · **Phase 366（Recovery Pillar 67 & `67/67` Master Recovery Milestone）**
- **依据实机基线**：Sony `ILME-FX3`（`Ver. 7.02`，`0x91030080`，`PRODUCT_MODEL_ALCIN_UUD`，`ilc/2210`）vs `ILME-FX6`（`Ver. 6.01`，`PRODUCT_MODEL_CHAPLIN`，`5-024-458-18`），全部立足 [Wave 65 全局情报报告](../2026-11-17-global-sony-wave65-zoom-ciz-autoslow-iso-arw-rawcomp-usblun-uvc-intel/README.md) 与 **25 项**（`FX3` 18 项 + `FX6` 7 项）只读 donor 实证。
- **事实与推断边界声明**：文中所有 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、内核模块（`usbg_storage.ko`、`usbg_stillimage.ko`、`usb_f_uvc.ko`、`g_webcam.ko`）符号与 SHA-256、官方 Help Guide 规则均标注为 **`[实测事实]`**；所有台架隔离策略（`Slot 1 EROFS=30` 阻断、`Stage-B /tmp` 隔离、macOS MSC 挂载阻断推理与模拟单元测试结果）均标注为 **`[模拟/安全护栏推断]`**。报告正文 **0 字节**泄露索尼专有原始固件字节（`raw_firmware_bytes_leaked = 0`）。

---

## 核心结论先行（Executive Conclusion）

1. **已将恢复验证总检推升至 `67/67`（`VERIFIED_67OF67_PILLAR_RECOVERY_MASTER`）** `[模拟/安全护栏推断]`：
   - 新增 [`realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py)，导出至 [`__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) 并接入 [`__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py)（`verify-67pillar-recovery` / `verify-pillar67-recovery` / `verify-pillar67-zoom-ciz-autoslow-baseiso-arw-usblun-uvc-vault`），与 `fx6_closure verify-milestone-349`（`recovery=67/67`）无缝自动对接。
   - **硬安全红线全程锁死**：`overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`cross_model_flash_authorized = False`、`persistent_emmc_writes_authorized = False`、`cnflasha_userspace_write_blocked = True`、`otp_fuse_touches = 0`、`rpmb_counter_increments = 0`、`physical_usb_packets_emitted = 0`、`physical_device_writes = 0`、`slot1_data_sector_writes = 0`、`raw_firmware_bytes_leaked = 0`。
2. **Pillar 67A 四大关键物理与 Reset 边界落地** `[实测事实]`：
   - **`[Zoom Range]` 与 8 档变焦速度 Reset 劈裂**：`[Zoom Range]`（`Optical zoom only` 默认 / `ClearImage Zoom` `1.5x` 4K & `2.0x` HD / `Digital Zoom` `4.0x` 电影 & 最高 `8.0x` 静态 S）与 `[Zoom Ring Rotate]`（`Left(W)/Right(T)` 默认 / `Right(W)/Left(T)`）**抗 `[Camera Settings Reset]`（`Not available`）**；而 `[Zoom Lever Speed]`（`1st=3`、`2nd=8 Fast`，`Standby`/`Movie Rec`）、`[Custom Key Z. Speed]`（`1..8` 默认 `3`）及 `[Remote Zoom Speed]`（`Variable` 默认 / `Fixed 1..8` 默认 `3`）**可被 Reset（`Can be reset`）**。CIZ/Digital 在静态 `RAW`、电影 `119.88p/100p`、`S&Q >= 100fps`、HDMI `RAW Output = On` 与 `Breathing Comp. = On` 下硬锁死（`EOPNOTSUPP=95`），激活时强制中央优先 AF + `[Multi]` 测光并禁用人脸/眼控/跟踪；对照 `FX6` 仅 2 档 `Zoom Type`（零 `Digital Zoom`）+ `Handle Zoom`。
   - **`[Auto Slow Shutter]` 6+ 锁死、静态专属 `[ISO AUTO Min. SS]` 与双原生 Base ISO 矩阵**：`[Auto Slow Shutter]`（电影专属、默认 `On`、`Can be reset`）在 `S&Q`、`S`、`M`、固定手动 ISO、`Flexible Exp.` 手动快门、`Cine EI`/`Cine EI Quick` 及 `Shutter Mode = Angle` 下强制禁用；`[ISO Range Limit]` 抗 Reset（仅限手动 ISO）；`[ISO AUTO Min. SS]` 仅限静态 `P/A + ISO AUTO`（默认 `STD`，电影/`S&Q` 返回 `EOPNOTSUPP=95`，闪光灯优先 `1/250s`）；`19` 组双原生 Base ISO 曲线矩阵（`800/12800` Cine EI、`640/12800` Flexible ISO/PP S-Log3/S-Log2/ITU709 800%、`100/2000` PP11 S-Cinetone/HLG/HLG3/Cine4、`80/1600` PP Off/HLG2/Cine3、`64/1280` Cine1、`50/1000` HLG1/Cine2，且 `[Base ISO]` 菜单开关仅在 `Cine EI`/`Cine EI Quick` 暴露）全部纳入确定性校验。
3. **Pillar 67B 休眠 `Lossless` `.ARW`、`[USB LUN Setting]=Single` `Slot 1` 威胁与双机 `UVC` 辟谣落地** `[实测事实]` + `[模拟/安全护栏推断]`：
   - **休眠 `Lossless Comp` `.ARW` 拒绝**：尽管 `FX3 appFw.so` 与 `_f.uxc` 编译了 `RAW_FILE_TYPE_LOSSLESS`（`L/M/S`），`ILME-FX3 Ver. 7.02` 实机仅暴露 `Compressed`（默认）与 `Uncompressed` 14-bit `.ARW`，验证器对 `Lossless Comp` 一律以 `EOPNOTSUPP=95` 拒绝；同时约束 `[HLG Still Image]`（纯 `HEIF` + `P/A/S/M` -> `BT.2100` + ISO 下限 `100/125`），并将 `[Sort Recording]` + `[Auto Switch Media]` 满卡外溢与流媒体 `[Movie Rec During Streaming]` / HDMI `[Rec. Media dur HDMI Output]` 写卡封死在 Tier-0 `Slot 1 EROFS=30` 防火墙后。
   - **`[USB LUN Setting] = Single` 暴露“仅 `Slot 1`”而非隐藏 `Slot 1`**：`Setup -> [USB]` 全树 3 项（`[USB Connection Mode]` 4 档、`[USB LUN Setting]`、`[USB Power Supply]`）均抗 `Camera Settings Reset`；`MSC + Single` 仍向宿主机暴露 `Slot 1`（`054C:0DA1`，`usbg_storage.ko`），接入 macOS 将被 `mds`/`fseventsd`/`Finder`/`fsck_exfat` 脏写毁损，台架在所有 `MSC`/`MTP` macOS 直连下故障闭锁。
   - **`NP-FZ100` USB-PD 门控与双机休眠 `UVC` 防火墙**：`FX3` 即便接入 `9V/3A` USB-C PD 仍强制依赖带电量 `NP-FZ100`（无电池供电需 `DC-C1` + `>=65W PD` + `5A e-Marked` 线缆），对照 `FX6` `19.5V DC IN`；同时在 `FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 上双双拒绝休眠原生 `UVC USB Streaming`（`usb_f_uvc.ko` / `g_webcam.ko`，`EOPNOTSUPP=95`）。

---

## 变更文件清单（严格限定 6 项自有文件）

| 序号 | 文件路径 | 变更性质 | 职责摘要 |
| :--- | :--- | :---: | :--- |
| 1 | [`realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py) | NEW | Pillar 67A/67B 确定性状态模型、25 项 `O_RDONLY` 只读 donor 探测与 Clean-Room 合成回退、`67/67` 并发总检聚合器 |
| 2 | [`__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | EDIT | 无遮蔽导出 Pillar 67 与 `67/67` 公开符号（保留 `22..66` 全部兼容导出） |
| 3 | [`__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | EDIT | 接入 `verify-67pillar-recovery`、`verify-pillar67-recovery` 与完整别名 CLI 子命令（转义 `800%%`） |
| 4 | [`test_realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_67pillar_zoom_ciz_autoslow_baseiso_arw_usblun_uvc_vault_verifier.py) | NEW | `176` 项单元测试（超 `>=130` 要求），覆盖正常 donor、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与模拟无 donor `work_root=None` |
| 5 | [`README.md`](../../outputs/fx3-recovery-adapter/README.md) | EDIT | 追加 Phase 366 Pillar 67 与 `67/67` 统一恢复总检文档与验证命令 |
| 6 | [`reports/2026-11-18-phase366-pillar67-67pillar-zoom-ciz-autoslow-baseiso-arw-usblun-uvc-vault/README.md`](README.md) | NEW | 本 Phase 366 中文工程结项报告 |

---

## 实测验证结果台账（Verification Ledger）

| 验证项 | 执行模式 / 命令 | 实测结果（`[实测事实]`） |
| :--- | :--- | :--- |
| Pillar 67 专项单元测试（正常 donor 模式） | `PYTHONDONTWRITEBYTECODE=1 ... unittest -v test_realhw_67pillar_...py` | **`176 / 176` PASS**（`24.795s`） |
| Pillar 67 专项单元测试（`FX3_CLEAN_ROOM_TEST=1`） | `FX3_CLEAN_ROOM_TEST=1 ... unittest -q test_realhw_67pillar_...py` | **`176 / 176` PASS**（`23.694s`） |
| Pillar 67 专项单元测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `FX3_FX6_FORCE_CLEAN_ROOM=1 ... unittest -q test_realhw_67pillar_...py` | **`176 / 176` PASS**（`26.145s`） |
| 模拟无 donor 回退（`iter_donor_work_roots -> (None,)`） | 内置 `test_006` / `test_030` / `test_033` | **PASS**（自动切换 `CLEAN_ROOM_SYNTHETIC`） |
| `verify-67pillar-recovery --json`（正常模式） | `LOCAL_DONOR_O_RDONLY`（25 donors） | `status=VERIFIED_67OF67_PILLAR_RECOVERY_MASTER`, `pillars=67/67`, `elapsed=1.260409s`, `sha256=0d6131598ddf81042b69cb5bd890ad96f2bd53fd85062d24082ea9d3beb2750a`, `leaked=0` |
| `verify-67pillar-recovery --force-clean-room --json` | `CLEAN_ROOM_SYNTHETIC`（25 synthetic donors） | `status=VERIFIED_67OF67_PILLAR_RECOVERY_MASTER`, `pillars=67/67`, `elapsed=0.838258s`, `sha256=1e6abc608632936ce3341bbb61c4027c9e9adbf8ee07b665b65cf1341b540d8c`, `leaked=0` |
| Milestone 349 双模总门控（正常模式） | `python3 -B -m fx6_closure verify-milestone-349` | **`status=OK`**, `mode=LOCAL_DONOR_O_RDONLY`, `recovery=67/67`, `gate148=153/156`, `h0_eq_h3=16/16`, `slot1_writes=0`, `leaked=0`, `ready_attach=False` |
| Milestone 349 双模总门控（Clean-Room 模式） | `python3 -B -m fx6_closure verify-milestone-349 --force-clean-room` | **`status=OK`**, `mode=CLEAN_ROOM_SYNTHETIC`, `recovery=67/67`, `gate148=153/156`, `h0_eq_h3=16/16`, `slot1_writes=0`, `leaked=0`, `ready_attach=False` |
| `fx3-recovery-adapter` 全量测试发现（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `unittest discover -s outputs/fx3-recovery-adapter/tests -p "test_*.py"` | **`4569` 项 PASS**（`544.990s`，`skipped=18`） |
| `fx3-recovery-adapter` 全量 `75` 文件（正常 donor 模式三段分片） | `files[0:45]` + `files[45:57]` + `files[57:75]` + `54pillar` 独立复核 | **Shard A `2277` PASS（`skipped=1`）、Shard C `1069` PASS、Shard B `1279/1281` PASS**（仅既有 `test_realhw_54pillar` 2 项硬编码 `1.5s` 阈值在高负载下抖动至 `1.838s`/`2.689s`，独立复核 **`84/84` PASS** `12.542s`） |
| Clean-Room 卫生与二进制审计 | `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | **`ALL GREEN in 0.08s`**（`0` `.pyc`、`0` 未授权二进制） |

