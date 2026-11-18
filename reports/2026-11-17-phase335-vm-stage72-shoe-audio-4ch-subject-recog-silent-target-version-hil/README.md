# Phase 335：VM HIL Stage 72（`72/72` 协同仿真里程碑 — Wave 62：`[Shoe Audio Set.]` 4ch 24-bit & `XLR-H1` vs `3.5mm` 接管 / `[Audio Out Timing]`、`[Face/Eye Subject]` 破谣言 `Human` + Still-Only `Animal` vs 休眠 `Bird`/`Insect`/`Car/Train`/`Airplane` & 8 槽 `[Face Memory]`、`[Silent Mode Settings]` 2 项 `[Target Function Settings]` & 休眠 `[Shutter When Pwr OFF]`、以及 `[Version]` & `BODYDATA.DAT` `Slot 1` + `Ver. 2.04/2.05` 跳板 `NO-GO` 防火墙 HIL）

- **日期**：`2026-11-17`
- **任务 / 分支**：`H407`（`task_d9b821106b6b`） · `codex/h407-phase335-vm-stage72-shoe-audio-4ch-subject-recog-silent-target-version-hil`
- **权威输入源**：[`Wave 62 实机情报报告`](../2026-11-17-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/README.md)
- **硬件安全红线**：`physical_device_writes = 0`、`persistent_emmc_writes_authorized = False`、`emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`hardware_live_attachment_authorized = False`、`overall_ready_for_hardware_attach = False`、`bodydata_flash_execution_blocked = True`、`slot1_data_sector_writes = 0`、`slot1_avf_info_mutated = False`、`emmc_nflasha_write_count = 0`、`rf_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`

---

## 核心结论速览（Conclusion First）

1. **Stage 72（`72/72` VM HIL 里程碑）已完成实现、全板接入与多模式验证**：
   - 新增 [`realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py`](../../outputs/fx3-vm/realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py)（Schema `realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator_v1`）及其 `96` 项四模式单元测试 [`test_realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py)，并接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) 作为 `stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil`（支持 `--include-stage72`、`--skip-stage72`、`--no-include-stage72`、`--skip-phase335`，自动推进至 **`vm_stages=72/72`**）；
   - 双模式 `make verify-milestone-324` 实测通过：`status=OK`、`pillars=6/6`、`gate142=143/146`、`recovery=58/58`、`auditors=45/45`、`vm_stages=72/72`、`e_nd_tx=0`、`rf_pkts=0`、`slot1_writes=0`、`leaked=0`；`outputs/fx3-vm` 全量发现双模式 `4013/4013` 通过（默认 `308.154s`，洁净室 `skipped=17`, `245.577s`）。
2. **21 份真实供体 `os.O_RDONLY` + 受界 `os.pread` 与 `work_root is None` 洁净室回退**：
   - **`实测事实`**：通过 `os.open(..., os.O_RDONLY)` 与受界 `os.pread`（`<= 4096 B`）完成 Wave-62 全部 **21 份本地真实供体**（`12` 份 FX3 四语 `.uxc` + `2` 份 FX6 英文 `.uxc` + `AVBB_SCN_START_AUDIO.so` `70,096 B` + `libInfraHotshoe.so` `47,808 B` + FX3 `2.05` `libsdfileinputupdaterapi.so` `60,584 B` + `libInfraAirplaneMode.so` `14,488 B` + `FX3 appFw.so` `79,015,712 B`、`FX3-CX95900_ALLLANG-Backup.bin` `2,229,740 B`、`FX6 appFw.so` `50,520,424 B`）的只读校验；`resolve_phase335_donor_paths(work_root)` 严格守卫 `if work_root is None: return None`，在 `FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 及无供体哨兵/Mock CI 路径下零异常切换至 `CLEAN_ROOM_SYNTHETIC`（`raw_firmware_bytes_leaked = 0`）。
3. **Wave-62 四大实机子系统闭环（严格区分 `实测事实` vs `推断`）**：
   - **72A `[Shoe Audio Set.]` 4ch 24-bit、`XLR-H1` vs `3.5mm` 硬件优先级、Proxy `AAC-LC 2ch` 与 `[Audio Out Timing]` vs `ILME-FX6`**：
     - **`实测事实`**：`ILME-FX3 Ver. 7.02` `Shooting -> [Audio Recording]` 暴露 5 项可 Reset 菜单：`[Audio Recording]`（`On[def]/Off`，`S&Q` 下禁用）、`[Audio Rec Level]`（`32` 级 `0..31`，默认 `26`，`Delete` 键一键复位，内置 Limiter 常开不可关闭/不可调阈值）、`[Shoe Audio Set.]`（`48kHz/24bit 4ch` / `48kHz/24bit 2ch` / `48kHz/16bit 2ch[def]`）、仅作用于机内立体声麦的 `[Wind Noise Reduct.]`（`Off[def]/On`），以及 **`[Audio Out Timing]`（`Live[def]` / `Lip Sync`，位于 `Shooting -> [Audio Recording]`，而非 `Setup -> [Sound Option]`！）**；`Ver. 2.00..7.02` 已移除独立 `[Audio Level Display]` 菜单项（`EOPNOTSUPP=95`）。`Setup -> [Sound Option] -> [4ch Audio Monitoring]` 提供 5 种立体声对，HDMI `[4ch Audio Output]` 选 `CH1/CH2[def]` 或 `CH3/CH4`。
     - **`实测事实`**：硬件优先级为 **`3.5mm MIC` 插孔 > MI 靴 > 机内立体声麦**（`3.5mm` 插入即强制 2ch 模拟并置灰 `[Shoe Audio Set.]`；`XLR-H1 HANDLE AUDIO = OFF` 回落内置麦；`ANALOG` 拨挡或旧式 MI 靴限制为 `48kHz/16bit 2ch`）；全主码率支持 4ch 24-bit，而同步 Proxy 永远下混为 `MPEG-4 AAC-LC 2ch 128 kbps`（`>= 100p` 禁用 Proxy）。对比 `ILME-FX6 Ver. 6.01`：原生 4ch 24-bit LPCM + 物理 `CH1..CH4` 旋钮 + 6 档 `Limiter Mode` + 休眠 `32bit float`。
     - **`推断`**：由于 FX3 在接管 `3.5mm` 或关闭 `HANDLE AUDIO` 后会自动回退并置灰 MI 靴 4ch 选项，台架音频链路验证若混插 `3.5mm` 监听/输入将静默降级为 2ch 16-bit，VM 模型通过 `EOPNOTSUPP=95` 显式阻断静默失真。
   - **72B `[Face/Eye Subject]` Wave-42 显式勘误与破谣言（`Human` + Still-Only `Animal` vs 休眠 `Bird`/`Insect`/`Car/Train`/`Airplane`）& 8 槽 `[Face Memory]`**：
     - **`实测事实`**：修正 Wave-42 笔误：`ILME-FX3 Ver. 7.02` `[Face/Eye Subject]` **仅开放 `Human[def]` 与 `Animal`**！共享 BIONZ XR ELF 中的 `Bird`、`Animal/Bird`、`Insect`、`Car/Train`、`Airplane`（`_f 0x6cb1..0x7440`，且 `BKID_APP_*` 中 `airplane` 为 `0` 命中）由 `FEATURE_MANAGER_eye_face_af_gen_type` 运行时屏蔽（`EOPNOTSUPP=95`）。`Animal` 眼部识别**仅在 Still 模式有效**，Movie/S&Q 下被 `TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT` 硬阻断。可 Reset 项含 `[Right/Left Eye Select]`、`[Face/Eye Frame Disp.]`（`Off[def]`，Clean HDMI 零泄漏）、`[Regist. Faces Priority]`（`On[def]`，选 `Animal` 时置灰）；`[Face Memory]`（最多 `8` 槽）抗 `[Camera Settings Reset]`（仅 `[Initialize]` / `Delete All` 清除）且不随 `CAMSET*.DAT` 导出。对比 `ILME-FX6 Ver. 6.01`：`Human`-only + 会话临时 `Saved Tracking Face`。
     - **`推断`**：FX3 与后续带独立 AI 单元机身共用同一 `appFw.so` 字符串/枚举表，`0x6cb1..0x7440` 符号的存在不代表菜单可达；必须结合门控符号一并拦截以防止模拟器误暴露休眠 AI 主体。
   - **72C `[Silent Mode Settings]` 二级菜单、5 项硬锁定、2 项 `[Target Function Settings]` 与休眠 `[Shutter When Pwr OFF]`**：
     - **`实测事实`**：`Shooting -> [Shutter/Silent] -> [Silent Mode Settings]` 为二级子菜单，开启 `[Silent Mode] = On` 后强制电子快门与 `Audio signals = Off` 并硬禁用 5 项（Flash、`Long Exposure NR`、`e-Front Curtain Shut.`、`BULB`、`Anti-flicker Shoot.`），但**不自动关闭 `[AF Illuminator]`**。`[Target Function Settings]` 仅暴露 **2 项**：`[Aperture Drive in AF]`（`Standard[def]/Silent Priority/Not Target`，仅 Still AF）与 `[Auto Pixel Mapping]`（`Off[def]/Not Target`）；`[Shutter When Pwr OFF]`（`_f 0x709f` / `image_sensor_barrier`）在 FX3 实机严格休眠（`EOPNOTSUPP=95`），对比 FX6 无机械快门（`APR` + e-ND）。
     - **`推断`**：在无快门台架/仿真基准中将 `[Auto Pixel Mapping]` 保持 `Off` 可阻断关机自动机械快门闭帘动作与 `cnflasha` 坏点表非易失写入（`poweroff_mech_shutter_actuations = 0`、`cnflasha_bad_pixel_writes = 0`）。
   - **72D `[Version]` 只读审计与 `BODYDATA.DAT` `Slot 1` / `Ver. 2.04-2.05` 跳板 `NO-GO` 防火墙**：
     - **`实测事实`**：`Setup -> [Setup Option] -> [Version]` 展示 `Body Ver. 7.02`、`Lens`、`Mount Adaptor`，`Ver. 6.00+` 联网更新提示在 `Airplane Mode = On` 下静默；`BODYDATA.DAT` 升级门控强制要求 `Slot 1` 根目录（FX6 为 `Slot B` 根目录 + 强制 `AC Adaptor` + 拔除全部外设）、`NP-FZ100 >= 51%`（3 格）、`<= 2.02` 机身先经 `Ver. 2.04/2.05` 跳板（跳过触发 **5 长 / 6 短** LED 故障码）并拦截跨机型文件。
     - **`推断`**：在物理未授权且无刷机隔离夹具的阶段，Tier-0 `NO-GO / BLOCKED` 防火墙必须对任何 `BODYDATA.DAT` 卡槽暂存或 `[Software Update]`/`Version Up` 执行请求 100% 返回 `EROFS=30` / `EPERM=1`（`emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`slot1_data_sector_writes = 0`、`emmc_nflasha_write_count = 0`）。

---

## 交付物与验证矩阵

| 交付文件（严格 5/5 文件所有权） | 职责与核心结果 |
| :--- | :--- |
| [`realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py`](../../outputs/fx3-vm/realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py) | Stage 72（Phase 335，`72/72` 里程碑）主协同仿真器 + 21 供体 `os.O_RDONLY` / 受界 `os.pread`（`<=4096 B`）与 `work_root is None` 洁净室回退 |
| [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 接入 `stage72_realhw_shoe_audio_4ch_subject_recog_silent_target_version_hil`（支持 `--include-stage72` / `--skip-stage72` / `--no-include-stage72` / `--skip-phase335`，自动推进 `vm_stages=72/72`） |
| [`test_realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py) | `96` 项四模式单元测试（覆盖 21 供体、`72A` 4ch/XLR-H1/3.5mm/Proxy/`Audio Out Timing`、`72B` `Human`+Still-Only `Animal`/休眠 AI/`Face Memory`、`72C` Silent 5 锁/2 项 Target/休眠 `Shutter When Pwr OFF`、`72D` `Version` & `BODYDATA.DAT` `NO-GO` 防火墙及 Suite 篡改检测） |
| [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 追加 Phase 335 Stage 72（`72/72` 里程碑）架构说明与四模式 CLI/测试命令 |
| [`reports/2026-11-17-phase335-vm-stage72-shoe-audio-4ch-subject-recog-silent-target-version-hil/README.md`](README.md) | 本工程结案报告（结论先行，严格区分 `实测事实` 与 `推断`） |

### 实测验证记录

| 验证项 | 模式 / 命令 | 实测结果 |
| :--- | :--- | :--- |
| Stage 72 独立三模式自检 | `realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py --self-test --summary`（默认 / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1`） | 全部 `[PASS]`（`donors=21`, `aud_items=5`, `subj=2`, `fmem=8`, `silent_lck=5`, `tgt_items=2`, `sh_pwroff=0`, `bd_blk=1`, `s1_wr=0`, `emmc_wr=0`, `leak=0`；digest `8593b4c73d0c` / `4098cf57e273`） |
| Stage 72 单元测试（四模式） | `unittest outputs/fx3-vm/tests/test_realhw_shoe_audio_4ch_subject_recog_silent_target_version_coemulator.py`（默认 / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / `FX3_FX6_MAC_WORK_ROOT=__fx3_fx6_clean_room_donor_disabled__`） | 正常模式 `96/96 OK`；`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与无供体哨兵回退（`96` run, `skipped=3`, `3.093s`）全数 `OK`（`0` 失败/`0` 错误） |
| 全板 72 阶段 Suite CLI | `fx3_vm_coemulation_suite.py --summary`（`LOCAL_DONOR_O_RDONLY`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与 `--skip-stage72`） | 全部退出 `0`（`m72=72/72`, `aud=5`, `subj=2`, `fmem=8`, `slck=5`, `tgt=2`, `sh_off=0`, `bd_blk=1`, `s1_wr=0`, `emmc_wr=0`；digest `9c8f71172c55` / `a5b985e9f8a5`） |
| `outputs/fx3-vm` 全量发现 | `unittest discover -s outputs/fx3-vm/tests -p 'test_*.py'`（正常与 `FX3_FX6_FORCE_CLEAN_ROOM=1`） | 默认供体模式 `4013/4013 OK`（`308.154s`）；`FX3_FX6_FORCE_CLEAN_ROOM=1` `4013` 项通过（`skipped=17`, `245.577s`, `0` 失败/`0` 错误） |
| Master Gate 里程碑校验 | `make verify-milestone-324` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324` | 4 次校验全数 `status=OK`、`pillars=6/6`、`vm_stages=72/72`、`auditors=45/45`、`e_nd_tx=0`、`rf_pkts=0`、`slot1_writes=0`、`leaked=0`（`milestone324_sha256`: `00dba590e0e8fa49...` / `7aa7181ab00f275e...` / `95dd17242354056a...` / `a340c0af0fbaf54c...`） |
| 工作区卫生审计 | `make clean-audit` | `[hygiene] git status --porcelain binary/pyc audit: CLEAN` · `ALL GREEN in 0.10s`（零 `.pyc`，零未跟踪杂文件） |
