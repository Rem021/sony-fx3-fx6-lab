# Phase 281（Stage 56, `56/56`）— Wave-46 真实硬件 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 协同仿真台架与门控报告

> **结论先行（ALL GREEN，Zero-Fault）**：Phase 281 将 **Wave-46 真实硬件规格**（`[Power Save by Monitor]` 现实分裂与 `[Power Save Start Time]` 9 禁用条件、`[Language]` `BK_LANG` `0x02cf019c` 34-vs-29 机种差异 & Stage-B 4 语言 `.uxc`/`.ltt` 对等、`[Volume Settings]` `0..15` / `[4ch Audio Monitoring]` 5 路 vs HDMI `4ch Audio Output` / `[Delete confirm.]` `"Cancel" first` + `Slot-1` 恢复保险库防火墙）完整建模为 **`stage56_realhw_power_save_monitor_language_volume_delete_hil`** 并接入 [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py)，实现全板 **`vm_stages=56/56`** 收敛。**76 项**新增双模单测在默认 `LOCAL_DONOR_O_RDONLY`、`FX3_CLEAN_ROOM_TEST=1` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 三种模式下全部通过（`Ran 76 tests ... OK`）；`outputs/fx3-vm/tests` 全量 **2,613 项**单测在本地只读供体（`160.258s`）与强制洁净室（`145.924s`）双模式下全部通过；`make verify-milestone-264` 与 `make verify-milestone-254` 在双模式下均输出 **`vm_stages=56/56`**，`scripts/run_all_lab_tests.py --clean-only` 干净通过（`CLEAN in 0.05s`）。全部硬件写与直播授权标志硬锁为 `False` / `0`，`raw_firmware_bytes_leaked == 0`，且工程仓库零 `.pyc` / 二进制残留。

---

## 1. 交付产物（严格限定 5 个归属文件）

| # | 交付文件 | 用途与关键结论 |
|---|---|---|
| 1 | [`realhw_power_save_monitor_language_volume_delete_coemulator.py`](../../outputs/fx3-vm/realhw_power_save_monitor_language_volume_delete_coemulator.py) | Phase 281 Stage 56（`56/56`，Schema `realhw_power_save_monitor_language_volume_delete_coemulator_v1`）协同仿真器：18 份 `O_RDONLY` 供体核验 + Sub-Model 56A/56B/56C + 16 项红线探针，洁净室确定性摘要 `44ab03fd8de9`。 |
| 2 | [`fx3_vm_coemulation_suite.py`](../../outputs/fx3-vm/fx3_vm_coemulation_suite.py) | 集成 `stage56_realhw_power_save_monitor_language_volume_delete_hil`（默认启用，支持 `--include-stage56` / `--skip-stage56` / `--skip-phase281` / `--no-include-stage56`），推进至 **`56/56`**。 |
| 3 | [`test_realhw_power_save_monitor_language_volume_delete_coemulator.py`](../../outputs/fx3-vm/tests/test_realhw_power_save_monitor_language_volume_delete_coemulator.py) | **76 项**双模单元测试（5 大测试组，使用 `sys.executable`、CI 弹性耗时阈值与前向兼容 `assertGreaterEqual(len(stage_keys), 56)`）。 |
| 4 | [`outputs/fx3-vm/README.md`](../../outputs/fx3-vm/README.md) | 补充 Phase 281 Stage 56（`56/56`）架构说明、四闭环细则与 CLI/unittest 复现命令。 |
| 5 | 本报告 `reports/2026-11-17-phase281-vm-stage56-power-save-monitor-language-volume-delete-hil/README.md` | 结论先行工程报告与实测门控台账。 |

---

## 2. 18 份真实硬件供体 `os.O_RDONLY` 实测校验（Zero-Leak）

遵循 `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模对等与 `< 0.1s` 冷启窗口约束，共锚定 **18 份** `ILME-FX3 Ver. 7.02` 与 `ILME-FX6 Ver. 6.01` 真实供体（`13` 份紧凑包校验完整 SHA-256，`5` 份大文件仅 `os.O_RDONLY` 有界 `<= 4096 B` 窗口扫描 + 头部 4 KiB SHA-256 核验）：

- **`libSaveLoadSettings.so`（FX3 7.02）**：`18,760 B`，SHA-256 前缀 `07819f42bdad381e`，确认 `SaveLoadSettingsIf::requestToRead` / `Backup_read` / `Backup_write`。
- **FX3 `_f.uxc` 4 语言包（支持扩展资源表）**：
  - `string_english_f.uxc`（`373,820 B`，`7e1f78fc8722671c`）：命中 `Power Save by Monitor`、`Both Linked`、`Open: Return`、`Close: Power Save`、`Does Not Link`、`Power Save Start Time`、`Auto Power OFF Temp.`、`4ch Audio Monitoring`、`CH1/CH2`、`CH3/CH4`、`CH1+3/CH2+4`、`CH1/CH1`、`CH2/CH2`、`4ch Audio Output`、`"Cancel" first`、`"Delete" first`、`Delete pressing twice`、`Camera Settings Reset`、`Reset Network Set.`、`Initialize`；且确认 `"Open: On/Close: Off"` 零命中（`0`）。
  - `string_simplifiedchinese_f.uxc`（`322,652 B`，`4c034acb454208b6`）：证实实际译文使用 `"通过显示屏节电"` / **`"二者均连接"`** / `"打开: 恢复"` / `"关闭: 节电"` / `"不连接"`。
  - `string_traditionalchinese_f.uxc`（`324,148 B`，`32c2f18528e1f5a2`）与 `string_japanese_f.uxc`（`447,840 B`，`45ba0b3625f3cdad`）均精确命中。
- **FX3 主 `.uxc` vs FX6 `.uxc` 4 语言包**：
  - FX3：`en=165,740 B` / `sc=149,064 B` / `tc=151,908 B` / `ja=208,564 B`；`string_english.uxc` 含 `Auto Power OFF Temp.` / `Language` / `Volume Settings` / `Delete confirm.`，零命中 `Power Save by Monitor` 与 `"Open: On/Close: Off"`。
  - FX6：`en=118,208 B` / `sc=118,644 B` / `tc=119,168 B` / `ja=141,692 B`；命中 `Language Select` / `Monitor CH` / `Delete Clip?`，零命中 `Power Save by Monitor` 与 `Auto Power OFF Temp.`。
- **大文件有界窗口 & `BK_LANG`（`0x02cf019c`）`pread` 校验**：
  - `FX3 appFw.so`（`79,015,712 B`，head4k `de3201c6615a5307`）命中 `BKID_APP_setting_monitor_power_linkage`、`BKID_APP_setting_start_power_saving`、`BKID_APP_setting_language`、`BKID_APP_setting_volume_settings`、`BKID_APP_setting_audio_monitoring_ch`、`BKID_APP_setting_4ch_output_ch`、`BKID_APP_setting_delete_confirm`、`BKID_APP_setting_delete_by_delete_twice`。
  - `FX6 appFw.so`（`50,520,424 B`，head4k `18a5d71362317f3f`）命中 `BKID_APP_SETTING_LANGUAGE`、`BKID_APP_SETTING_MONITOR_VOLUME`、`Initialize`。
  - `FX3-CX95900_ALLLANG-Backup.bin`（`2,229,740 B`，head4k `87b30e89cbf4a649`）：`@ 0x90ff0` 读出 `4 B` LE `= 0`。
  - `CX95898_NTSC.bin`（`2,253,333 B`，head4k `da125f7fabe4a514`）：`@ 0x89242` 读出 `1 B = 0x00`。
  - `CX95899_CN1.bin`（`2,253,333 B`，head4k `30e3702d49d62132`）：`@ 0x89242` 读出 `1 B = 0x19`。

---

## 3. 三大 Wave-46 协同仿真子模型与硬红线护栏

1. **Sub-Model 56A — `[Power Save by Monitor]` 现实分裂与 `[Power Save Start Time]` 9 禁用条件**：
   - 库存 `ILME-FX3`（`0x91030080`，`ilc/2210`，含 `FX3` / `FX3A` / `FX6`）`(Setup) -> [Power Setting Option]` 仅暴露 **2 项**：`[Power Save Start Time]`（`Off` / `30 Min` / `5 Min` 默认 / `2 Min` / `1 Min` / `10 Sec`）与 `[Auto Power OFF Temp.]`（`Standard` 默认 / `High`）；`fx3_ui_exposes_power_save_by_monitor == False`，侧翻屏内折（`Closed_Inward`）完全不休眠，任何伪造 UI 请求或 `"Open: On/Close: Off"` 字符串一律返回 `EOPNOTSUPP (95)`。
   - 共享 `BIONZ XR` `appFw.so` 编译保留的 **4 模式**（`Both Linked` `0x6db5`、`Open: Return` `0x6db6`、`Close: Power Save` `0x60a8`、`Does Not Link` `0x6b2e`）按同代变角度屏机型（`ILME-FX2` / `ILCE-7M4` / `ZV-E1` / `ILCE-6700`）运行无头 HDMI 休眠防护，并主动拦截 `ILCE-7M4 Ver. 6.00` 类睡眠回归；同时建模全部 **9 项**自动禁用条件（USB 供电、幻灯片、FTP、录像、PC 连接、TV/HDMI、IR 遥控、Bluetooth 遥控、流媒体/Creators' Cloud）及 `(Setup)` 跨 `[Camera Settings Reset]` 存活（仅 `[Initialize]` 还原）。
2. **Sub-Model 56B — `[Language]` `BK_LANG`（`0x02cf019c`）34-vs-29 差异与 Stage-B 4 语言对等**：
   - 完整区分 `ILME-FX3`（`34` 语言，`0x90ff0` 4B）与 `ILME-FX6`（`29` 语言，`0x89242` 1B，`NTSC=0x00` vs `CN1=0x19`，对 FX3 独有第 30..34 语言返回 `EOPNOTSUPP = 95`），Stage-B 4 语言 `.uxc`/`.ltt` 切换表（`en=0x00` / `switchBank=0` / `(4,4)`，`schinese=0x19` / `23` / `(19,19)`，`tchinese=0x18` / `27` / `(22,22)`，`japanese=0x01` / `1` / `(12,12)`），开箱 `"—"` 提示，以及跨 `[Camera Settings Reset]` 与 `[Reset Network Set.]` 存活、仅在 `[Initialize]` 清零重弹。
3. **Sub-Model 56C & Redlines — `[Volume Settings]` / `[4ch Audio Monitoring]` / `[Delete confirm.]` & `Slot-1` Vault 防火墙**：
   - `[Volume Settings]`（`0..15`，默认 `7`，`0xe8c9`，区别于 `0x7af6` `[Audio signals]`）：`XLR-H1` 激活 + 机内扬声器路径自动防啸叫钳位 `0`（强制绕过以 `EACCES = 13` 阻断）。
   - `[4ch Audio Monitoring]`（`CH1/CH2`、`CH3/CH4`、`CH1+3/CH2+4`、`CH1/CH1`、`CH2/CH2`）全部 **5 路**映射与 `3.5mm` 双声道耳机物理边界（`EOPNOTSUPP = 95`），并与 HDMI `[4ch Audio Output]`（仅 `CH1/CH2` / `CH3/CH4`）解耦。
   - `[Delete confirm.]`（`"Cancel" first` 默认 vs `"Delete" first`）+ `[Delete pressing twice]`（`Off` 默认）在 `(Playback)` 下跨 `[Camera Settings Reset]` 存活；硬 **Slot-1 恢复保险库防火墙**（`EROFS = 30`，`slot1_vault_delete_events == 0`，`slot1_format_hard_locked == True`）阻断 Slot 1 上全部单张/多张/文件夹/日期/连按删除及 `[Format]`，同时全部 `16` 项安全红线探针全部闭环。

---

## 4. 实测验证台账（ALL GREEN）

| 验证项目 | 运行模式 | 实测结果 |
|---|---|---|
| Stage 56 独立自检（`--self-test --summary`） | `LOCAL_DONOR_O_RDONLY` | `[PASS] Phase 281 Stage 56 (56/56)`（`donors=18, psm_ui=0, s1_del=0, phys_wr=0, leaked=0`） |
| Stage 56 独立自检（`--self-test --summary`） | `CLEAN_ROOM_SYNTHETIC` (`FX3_CLEAN_ROOM_TEST=1`) | `[PASS] Phase 281 Stage 56 (56/56)`（`digest=44ab03fd8de9`） |
| 全板协同仿真（`fx3_vm_coemulation_suite.py --include-stage56 --summary`） | 本地只读供体 / 洁净室 | 均返回 `0`，`realhw_power_save_monitor_language_volume_delete_hil=LOCAL_DONOR_O_RDONLY / CLEAN_ROOM_SYNTHETIC` |
| Phase 281 专项单元测试（3 模式） | Default / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` | **76 tests in 1.921s, OK**（三模式全绿） |
| 全量 `outputs/fx3-vm/tests` 发现集 | `LOCAL_DONOR_O_RDONLY` | **Ran 2613 tests in 160.258s, OK** |
| 全量 `outputs/fx3-vm/tests` 发现集 | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **Ran 2613 tests in 145.924s, OK (skipped=4)** |
| `make verify-milestone-264` | Default (`LOCAL_DONOR` + `--force-clean-room`) & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`status=OK ... vm_stages=56/56 ... leaked=0`**（`milestone264_sha256=32337ac0073693d6...` / `1b0184224563f2f7...`） |
| `make verify-milestone-254` | Default (`LOCAL_DONOR` + `--force-clean-room`) & `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`status=OK ... vm_stages=56/56 ... leaked=0`**（`milestone254_sha256=7da6b9cd2646c3c5...` / `7c68aa77c9afb000...`） |
| `scripts/run_all_lab_tests.py --clean-only` | Tracked-tree + strict-dir hygiene | **`[hygiene] git status --porcelain binary/pyc audit: CLEAN (0.05s)`** |
