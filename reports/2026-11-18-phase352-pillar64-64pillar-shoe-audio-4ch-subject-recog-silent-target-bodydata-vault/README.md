# Phase 352 里程碑交付报告：Recovery Pillar 64（Wave-62）与 `64/64` 统一恢复总检（`verify-64pillar-recovery`）

## 1. 结论先行（Conclusion First）

- **交付状态**：**PASS（`64/64` 恢复支柱闭环里程碑达成，`VERIFIED_64OF64_PILLAR_RECOVERY_MASTER`）**。
- **核心成果**：
  1. 基于 [Wave 62 全球实机情报报告](../2026-11-17-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/README.md)（`ILME-FX3 Ver. 7.02` `ilc/2210` `0x91030080` `PRODUCT_MODEL_ALCIN_UUD` vs `ILME-FX6 Ver. 6.01` `5-024-458-18` `PRODUCT_MODEL_CHAPLIN`），落地 **Phase 352 Recovery Pillar 64**（Sub-Pillar **64A** `6/6` + Sub-Pillar **64B** `6/6`）及并发式 **`64/64` 统一恢复总检聚合器** [`evaluate_realhw_64pillar_recovery_master`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py)（`schema_version = "realhw_64pillar_recovery_master_v1"`，`verify-64pillar-recovery` / `verify-pillar64-recovery`），并通过包根动态导出自动接入 `realhw_milestone324_master_gate.py`（`recovery=64/64`），未修改 `Makefile`、`outputs/fx3-safety/`、`outputs/fx3-vm/` 或 `outputs/fx6-on-fx3-closure/` 任何文件。
  2. 全量实现无供体 CI 保护与有界只读取证：[`_resolve_phase352_donor_path`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py) 内置 `work_root is None` 防护，[`inspect_phase352_donors_readonly`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py) 严格以 `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)` 在 `<= 2.0s` 预算内检验 **21 项** Wave-62 本地供体（16 项 `FX3 7.02/2.05` + 5 项 `FX6 6.01`；大文件仅读前 `4096B` 头部，小文件全量校验），并在缺少本地供体或 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 时安全回退至 `CLEAN_ROOM_SYNTHETIC` 并返回 `rc=0`。
  3. 严格仅触碰本次授权的 **6 个所属文件**，未改动任何无关目录。
- **实测结果摘要（双模 & 4 模全绿）**：
  - `verify-pillar64-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`64A=6/6`、`64B=6/6`，`21` 项 Wave-62 本地供体严格 `O_RDONLY` 核验通过，`elapsed=0.005s`，`suite_sha256=6669b2e305d92251b4fd299f530f7931f20de5172a63b45023e02ebce720bcbb`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`64A=6/6`、`64B=6/6`，`elapsed=0.000s`，`suite_sha256=27d7b49a54e544cda6b3314d5db9a48f4573834ae6abb03cfd6dffa5d51b6404`，`raw_firmware_bytes_leaked=0`。
  - `verify-64pillar-recovery`：
    - `LOCAL_DONOR_O_RDONLY`：`pillars=64/64`，`all_passed=True`，`elapsed=1.012s`（文本 CLI）/ `1.258s`（JSON CLI），均满足 `< 1.5s` 快速 CLI 预算，`master_64pillar_sha256=01abc1f296b17697838683e3e7225f959e0c1c1a13e469082a8c14a4862a89af`，`raw_firmware_bytes_leaked=0`。
    - `CLEAN_ROOM_SYNTHETIC`（`--force-clean-room`）：`pillars=64/64`，`all_passed=True`，`elapsed=0.673s`（文本 CLI）/ `0.923s`（JSON CLI），均满足 `< 1.5s` 快速 CLI 预算，`master_64pillar_sha256=bc88338ed190b0b1f408f7c608b8a0466418b68567342c565c683ed060d7b667`，`raw_firmware_bytes_leaked=0`。
    - 模拟无供体 CI（`patch.object(fr.files, 'iter_donor_work_roots', return_value=(None,))`）：`rc=0`，自动切换 `verification_mode="CLEAN_ROOM_SYNTHETIC"`，`pillars_passed=64/64`，`raw_firmware_bytes_leaked=0`。
  - `make verify-milestone-324`（正常模式 & `FX3_FX6_FORCE_CLEAN_ROOM=1`）：
    - 正常模式：`status=OK pillars=6/6 gate142=147/150 recovery=64/64 cnflasha_ro=True otp=0 rpmb=0 passive_tx=0 auditors=45/45 vm_stages=76/76 h0_eq_h3=16/16 e_nd_tx=0 rf_pkts=0 slot1_writes=0 qemu=46/46(138/138) pngs=92/92(max=27467B) leaked=0`（`milestone324_sha256=1e0cbbdfdd04fd98...`）。
    - 洁净室模式：`status=OK ... recovery=64/64 ... leaked=0`（`milestone324_sha256=5e959ef10fcc47d9...`）。
  - **硬件安全护栏硬锁**：`BODYDATA_PLACEMENT_OR_FLASH_AUTHORIZED=False`、`CROSS_MODEL_FLASH_AUTHORIZED=False`、`PERSISTENT_EMMC_WRITES_AUTHORIZED=False`、`CNFLASHA_USERSPACE_WRITE_BLOCKED=True`、`SPI_NOR_WRITE_AUTHORIZED=False`、`EL3_PAYLOAD_TRANSMIT_AUTHORIZED=False`、`ISP_WRITE_AUTHORIZED=False`、`LIVE_USB_IOKIT_TRANSMIT_ENABLED=False`、`HARDWARE_LIVE_ATTACHMENT_AUTHORIZED=False`、`OVERALL_READY_FOR_HARDWARE_ATTACH=False`、`OTP_FUSE_TOUCHES=0`、`RPMB_COUNTER_INCREMENTS=0`、`PHYSICAL_DEVICE_WRITES=0`、`RAW_FIRMWARE_BYTES_LEAKED=0`。

---

## 2. Wave-62 实测事实 vs 工程推断边界

> 以下严格区分来自 `ILME-FX3`（`ilc/2210`、`Ver. 7.02 appFw.so`/UXC/`Backup.bin`/`Ver. 2.05 libsdfileinputupdaterapi.so`/`Ver. 7.02 BODYDATA.DAT` 头部）与 `ILME-FX6`（`5-024-458-18`、`Ver. 6.01 appFw.so`/`AVBB_SCN_START_AUDIO.so`/`libInfraHotshoe.so`/UXC）的**实测事实**，以及恢复子系统施加的**推断 / 工程安全护栏**。

### 2.1 Sub-Pillar 64A：`[Shoe Audio Set.]` `4ch 24-bit`、`XLR-H1`/`3.5mm` 接管、`[Audio Out Timing]` 与 `[Face/Eye Subject]` 破谣言

1. **实测事实 — `Shooting -> [Audio Recording]` 全量矩阵与菜单纠偏**：
   - `[Audio Recording]`（`_f 0x72d3` / `base 0xe72e`，`BKID_APP_setting_audio_recording`）：默认 `On`，`S&Q` 模式下禁用（返回 `EOPNOTSUPP=95`）。
   - `[Audio Rec Level]`（`_f 0x63b9`/`0x6f0a`，`BKID_APP_setting_audio_recording_level`）：`0..31` 共 32 级步进，出厂默认 **`26`**，`Delete` 键一键复位；机身内置 Limiter 常开且在 FX3 菜单中不可配置/关闭（请求配置返回 `EOPNOTSUPP=95`）。
   - `[Shoe Audio Set.]`（`_f 0x77f6`，`BKID_APP_setting_external_mic_audio_format`）：支持 `48kHz/24bit 4ch`、`48kHz/24bit 2ch` 与 **`48kHz/16bit 2ch`（默认）**；FX3 全部主录格式（`XAVC HS 4K`、`XAVC S 4K/HD`、`XAVC S-I 4K/HD/DCI 4K`）均支持写入 `24-bit 4ch LPCM`，而同步 Proxy（`XAVC HS HD` / `XAVC S HD`）永远强制压缩为 **`MPEG-4 AAC-LC 2ch 128 kbps`** 且在 `>= 100p/120p+` 禁用。
   - `[Wind Noise Reduct.]`（`_f 0x7b2a`/`base 0xe4b1`/`0xe4ae`）：仅作用于**机身内置立体声麦克风**，对 `XLR-H1` 与 `3.5mm` 外接麦无效。
   - `[Audio Out Timing]`（`_f 0x62d8`/`0x6bc2`）：**`Live`（默认）** / `Lip Sync`，实位于 **`Shooting -> [Audio Recording]`**（而非 `Setup -> [Sound Option]`）；Ver. 2.00..7.02 已彻底移除独立 `[Audio Level Display]` 开关菜单（`_f 0x7a36` / `BKID_APP_setting_audio_recording_level_display` 为旧版休眠项 -> `EOPNOTSUPP=95`），改由 `DISP` 自动常驻并在 4ch 激活时扩展为 4 通道电平表。
   - `Setup -> [Sound Option]` 下 `[4ch Audio Monitoring]` 提供 5 种耳机混听（`CH1/CH2`、`CH3/CH4`、`CH1+3/CH2+4`、`CH1/CH1`、`CH2/CH2`），HDMI 经 `[4ch Audio Output]` 选 `CH1/CH2` 或 `CH3/CH4`。
2. **实测事实 — 硬件输入接管优先级与 FX6 对照**：
   - `3.5mm MIC` 插孔拥有最高硬件优先级：插入后强制切回 2ch 模拟并置灰 `[Shoe Audio Set.]`（非 `16bit 2ch` 请求返回 `EOPNOTSUPP=95`）。
   - `XLR-H1` 拨挡 `HANDLE AUDIO = OFF` 时切断手柄音频并回落机身内置麦；`DIGITAL/ANALOG = ANALOG`（或旧款模拟靴麦）上限锁定 `48kHz/16bit 2ch`；`DIGITAL` 4ch 映射为 `INPUT1->CH1`、`INPUT2->CH2`、`INPUT3->CH3/CH4`。
   - 对照 `ILME-FX6 Ver. 6.01`：机身/智能手柄原生 `4ch 24-bit 48kHz`，配备物理 `CH1..CH4` 旋钮与 6 档 `Limiter Mode`（`Off / -6 / -9 / -12 / -15 / -17 dB`），而 `FX6 ns1 0x3215` 的 `4ch/48kHz/32bit float` 仍处于休眠字符串层（未激活 -> `EOPNOTSUPP=95`）。
3. **实测事实 — `[Face/Eye AF] -> [Face/Eye Subject]` `Human`/`Animal`-Only 破谣言与 `[Face Memory]`**：
   - `ILME-FX3 Ver. 7.02` 无独立 AI 处理单元，`[Face/Eye Subject]`（`_f 0x70fa`/`0x7643`，可被 Reset）**严格仅开放 `Human`（默认）与 `Animal`**；且受 `FX3 appFw.so` 显式互斥符号 `VAL_HAITA_setting_face_eye_af_subject_TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT` 约束，**`Animal` 眼部检测仅限 Still 静态照片模式生效**（Movie/S&Q 下返回 `EOPNOTSUPP=95`）。
   - 证伪社区误传与早期猜测：`FX3 appFw.so` 因多机型 BIONZ XR 共享而携带休眠词条 `_f 0x6cb1` (`Bird`) / `0x6957` (`Animal/Bird`) / `0x6996` (`Insect`) / `0x674e` (`Car/Train`) / `0x7440` (`Airplane`)，但 `ALCIN_UUD` 上被 `FEATURE_MANAGER_eye_face_af_gen_type` 屏蔽，且 `BKID_APP_*airplane* == 0`（对以上 5 类休眠被摄体均返回 `EOPNOTSUPP=95`）。
   - `[Face Memory]` 在 FX3 活跃：上限 **8 张人脸**，抗 `[Camera Settings Reset]`，**不随 `CAMSET*.DAT` 导出**，仅通过 `Delete All` / `[Initialize]` 清零；`[Face/Eye Frame Disp.]` 出厂默认 **`Off`** 且 Clean-HDMI 永远输出 **`0 px`**。
   - 对照 `ILME-FX6 Ver. 6.01`：`Face/Eye Detection AF`（`Face/Eye Priority AF` / `Face/Eye Only AF` / `Off`）**仅支持 `Human`**，并以会话式 `Saved Tracking Face` 替代固定脸库（`FX6 _2.uxc 0x4312` 仅残存历史 `'Delete Registered Face'`）。
4. **推断 / 安全护栏**：
   - 台架保持 Tier-0 `Slot 1` 只读审计隔离（任何写/格式化触发 `EROFS=30`，`slot1_data_sector_writes == 0`），Stage-B 覆写限 `/tmp/fx3_stage_b_overlay/pillar64`，`Backup.bin H0 == H3`（`16/16`）。

### 2.2 Sub-Pillar 64B：`[Silent Mode Settings]` `2`-Item 目标矩阵、休眠 `[Shutter When Pwr OFF]` 与 `[Version]` `BODYDATA.DAT` `Slot 1` 防火墙

1. **实测事实 — `[Silent Mode Settings]` 与严格 `2` 项 `[Target Function Settings]` + 休眠 `[Shutter When Pwr OFF]`**：
   - `Shooting -> [Shutter/Silent] -> [Silent Mode Settings]`（`_f 0x655f`/`0x72df`）包含 `[Silent Mode]`（`_f 0x7046`，`Off` 默认/`On`，可 Reset）与 `[Target Function Settings]`（`_f 0x79c0`）。开启 `[Silent Mode] = On` 时强制切换电子快门、关闭 `[Audio signals]`（`base 0xe0c8`）并硬禁用 **5 项功能**（`Flash`、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.` -> 强行请求返回 `EOPNOTSUPP=95`），而 **`[AF Illuminator]` 不会被自动禁用**。
   - `[Target Function Settings]` 在 `ilc/2210` 上**严格仅包含 2 项**：① `[Aperture Drive in AF]`（`_f 0x61b5`，Still-only，`Standard` 默认 / `Silent Priority` / `Not Target`）；② `[Auto Pixel Mapping]`（`_f 0x7734`，`Off` 默认 / `Not Target`）。任何伪造第 3 项的请求返回 `EOPNOTSUPP=95`。
   - **证伪休眠 `[Shutter When Pwr OFF]`**：尽管共享 ELF/UXC 包含 `_f 0x709f` (`'Shutter When Pwr OFF'`) / `0x7495` (`'Anti-dust Function'`) 与 `image_sensor_barrier` 符号，`ILME-FX3 Ver. 7.02` 实机 UI **0 暴露**（`dormant_shutter_when_pwr_off_exposed_events == 0`，强行触发返回 `EOPNOTSUPP=95`）；而 `ILME-FX6` 本身无机械焦平面快门（采用 `Auto Pixel Restore` `FX6 ns1 0x2e4e/0x324a`）。
2. **实测事实 — `[Version]`、`BODYDATA.DAT` `Slot 1` 与 Ver. 2.04/2.05 跳板门控**：
   - `Setup -> [Setup Option] -> [Version]`（`base 0xe396`）展示 `Body`（`Ver. 7.02`）、`Lens`（`_g 0x6517`，兼容镜头挂载时显示）与 `Mount Adaptor`；`Ver. 6.00+` 在联网状态下显示更新红点徽标（`_g 0x6516`），Zero-RF `Airplane Mode = On` 台架将其静默抑制。
   - `[Software Update]`（`_f 0x6fd6`/`0x7283`）严格仅读取 **`Slot 1` 根目录** 的未改名 `BODYDATA.DAT`（忽略 `Slot 2`；对照 `ILME-FX6` `Maintenance > Version > Version Up` 严格 **`Slot B` 根目录** + **强制外接 `AC Adaptor`**）；要求 `NP-FZ100 >= 51%`（`3` 格）；**`<= Ver. 2.02` 机身严禁直接跨刷 `Ver. 7.02`，必须先经 PC 升至 `Ver. 2.04` 或 `Ver. 2.05` 跳板**（否则触发 `5 long / 6 short` 或 `7 long / 7 short` LED 报警；升级完成后重置 TC/UB）。
3. **推断 / 安全护栏（`NO-GO` 刷机防火墙 & `EROFS=30`）**：
   - 台架保持 `[Auto Pixel Mapping] = Off` 以防止关机触发机械快门动作及 `cnflasha` 坏点表写入（`cnflasha_pixel_map_mutation_bytes == 0`）。
   - 硬锁定 `bodydata_placement_or_flash_authorized == False`、`cross_model_flash_authorized == False`、`emmc_writes_authorized == False`、`hardware_live_attachment_authorized == False`；任何试图向 `Slot 1` 放置/写入 `BODYDATA.DAT`、触发实机刷写或执行跨机型（`FX6 <-> FX3`）刷写的操作均被拦截并返回 **`EROFS=30`**（`slot1_bodydata_mutation_bytes == 0`、`slot1_data_sector_writes == 0`）。

---

## 3. 授权交付文件清单（Strict 6-File Ownership）

| 序号 | 变更类型 | 文件路径 | 职责摘要 |
| :---: | :---: | :--- | :--- |
| 1 | NEW | [`outputs/fx3-recovery-adapter/fx3_recovery/realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py) | Pillar 64A/64B 状态机与评估器、21 项 `O_RDONLY` 有界核验 + `work_root is None` / 无供体 Clean-Room 自动回退、`6/6 + 6/6` 套件及 `64/64` 并发主控 `evaluate_realhw_64pillar_recovery_master` |
| 2 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__init__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) | 导出 Phase 352 `P352_*` / `PHASE352_*` / `MASTER_64_*` / `evaluate_realhw_64pillar_recovery_master` / `verify_64pillar_recovery` 等全部公开符号与 `__all__` |
| 3 | EDIT | [`outputs/fx3-recovery-adapter/fx3_recovery/__main__.py`](../../outputs/fx3-recovery-adapter/fx3_recovery/__main__.py) | 注册 `verify-pillar64-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault`、`verify-pillar64-recovery` 与 `verify-64pillar-recovery` CLI 子命令（`help=` 已做 `%%` 转义） |
| 4 | EDIT | [`outputs/fx3-recovery-adapter/README.md`](../../outputs/fx3-recovery-adapter/README.md) | 补充 Phase 352 Pillar 64 & `64/64` 恢复总检文档与 CLI 示例 |
| 5 | NEW | [`outputs/fx3-recovery-adapter/tests/test_realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py`](../../outputs/fx3-recovery-adapter/tests/test_realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py) | **180 项**（`>= 128`）四模（本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1`、`work_root=None` / 不存在路径）单元测试、参数化矩阵与 `>= 64` 向前兼容自动发现断言 |
| 6 | NEW | [`reports/2026-11-18-phase352-pillar64-64pillar-shoe-audio-4ch-subject-recog-silent-target-bodydata-vault/README.md`](README.md) | 本 Phase 352 里程碑中文工程交付报告 |

---

## 4. 实测验证矩阵（Verification Evidence）

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| Pillar 64 单测（本地 `O_RDONLY` 供体） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py` | **`180/180 OK`**（`19.957s`） |
| Pillar 64 单测（`FX3_CLEAN_ROOM_TEST=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py` | **`180/180 OK`**（`19.190s`） |
| Pillar 64 单测（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest outputs/fx3-recovery-adapter/tests/test_realhw_64pillar_shoe_audio_4ch_subject_recog_silent_target_bodydata_vault_verifier.py` | **`180/180 OK`**（`20.373s`） |
| 显式模拟无供体 CI（`work_root=None` / `(None,)`） | `test_06` & 独立 `-c` 验证（`patch.object(fr.files, 'iter_donor_work_roots', return_value=(None,))`） | **`CLEAN_ROOM_SYNTHETIC`**（`64/64`，`rc=0`，`leaked=0`） |
| `verify-pillar64-recovery` CLI（供体 / 洁净室） | `verify-pillar64-recovery` & `verify-pillar64-recovery --force-clean-room` | **`64A=6/6, 64B=6/6`**（`0.005s` / `0.000s`，`suite_sha256=6669b2e305d92251...` / `27d7b49a54e544cd...`，`leaked=0`） |
| `verify-64pillar-recovery` CLI（供体 / 洁净室） | `verify-64pillar-recovery` & `verify-64pillar-recovery --force-clean-room` | **`64/64 PASS`**（`1.012s` / `0.673s` `< 1.5s`，JSON `1.258s` / `0.923s`，`master_64pillar_sha256=01abc1f296b17697...` / `bc88338ed190b0b1...`，`leaked=0`） |
| `make verify-milestone-324`（双模） | `PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324` & `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` | **`status=OK pillars=6/6 gate142=147/150 recovery=64/64 auditors=45/45 vm_stages=76/76 qemu=46/46(138/138) pngs=92/92(max=27467B) leaked=0`**（`1e0cbbdfdd04fd98...` / `5e959ef10fcc47d9...`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（正常模式） | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`4,157 tests OK (skipped=1)`**（`552.840s`） |
| `fx3-recovery-adapter` 全套 `unittest discover`（`FX3_FX6_FORCE_CLEAN_ROOM=1`） | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-recovery-adapter /usr/bin/python3 -B -m unittest discover -s outputs/fx3-recovery-adapter/tests` | **`4,099 tests OK (skipped=18)`**（`490.370s`） |
| 清洁审计 | `PYTHONDONTWRITEBYTECODE=1 make clean-audit` | **`ALL GREEN`**（零 `.pyc` / 零二进制残留） |
