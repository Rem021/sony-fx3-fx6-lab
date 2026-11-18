# 全球 Sony 实机情报 Wave 62（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Shoe Audio Set.]` 4 声道 24-bit / `XLR-H1` vs 机内麦与 `[Audio Out Timing]` `Live/Lip Sync`、`[Face/Eye AF]` 被摄体识别破谣言（`Human`/`Animal` vs 休眠 `Bird`/`Insect`/`Car/Train`/`Airplane`）、`[Silent Mode Settings]` `[Target Function Settings]` 耦合矩阵，以及 `[Version]` 机身/镜头 `BODYDATA.DAT` 刷机卡槽风险与 `NO-GO` 红线）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Audio Recording / Audio Rec Level / Shoe Audio Set. / Wind Noise Reduct. / Audio Out Timing / 4ch Audio Monitoring / 4ch Audio Output / Face/Eye Prior. in AF / Face/Eye Subject / Right/Left Eye Select / Face/Eye Frame Disp. / Face Memory / Regist. Faces Priority / Silent Mode Settings / Version / List of default setting values*）
  - Sony `ILME-FX3` `Ver. 2.00 / 2.04 / 2.05 / 3.00 / 5.00 / 6.00 / 6.01 / 7.00 / 7.02` 官方固件发布说明与升级指引
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0）与 `ILME-FX6` `Ver. 6.00 / 6.01 / 6.02` 升级文档
  - 并严格对照 `os.O_RDONLY` 本地 donor 二进制实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`FX3 p1 2.05 nflasha1` / `libsdfileinputupdaterapi.so`、`FX6 appFw.so`、`FX6 AVBB_SCN_START_AUDIO.so` / `libInfraHotshoe.so` 及 `FX6 string_english.uxc` / `_2.uxc`；参见 [Wave 42 报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h382-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md) 与 [Wave 61 报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h382-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/reports/2026-11-17-global-sony-wave61-ftp-ftps-customwb-af-speed-focusmap-marker-intel/README.md)）。
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、SHA-256 账本与官方文档条目）与 **`推断`**（含物理卡槽写危害、Zero-RF 隔离与 `NO-GO` 刷机防护推理）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（数字 MI 靴 `[Shoe Audio Set.]`、`XLR-H1` `HANDLE AUDIO` 切换、`[Wind Noise Reduct.]` 与 `[Audio Out Timing]` `Live/Lip Sync`）**：
   - **实测事实（菜单路径与Ver. 2.00+ OSD 纠偏）**：在 `ILME-FX3 Ver. 7.02`（`ilc/2210`）中，**`[Audio Out Timing]`（`Live` 默认 / `Lip Sync`）位于 `Shooting -> [Audio Recording]` 之下**（`BKID_APP_setting_audio_output_timing`），**并非位于 `Setup -> [Sound Option]`**；而 `Setup -> [Sound Option]` 实际承载 `[Volume Settings]`、`[4ch Audio Monitoring]`（`CH1/CH2`、`CH3/CH4`、`CH1+3/CH2+4`、`CH1/CH1`、`CH2/CH2`）与 `[Audio signals]`。此外，**`[Audio Level Display]` 仅在早期 Ver. 1.x 菜单/共享 ELF 中存在**（`BKID_APP_setting_audio_recording_level_display`、`_f 0x7a36`），在 `Ver. 2.00..7.02`（`ilc/2210`）中已取消独立开关菜单，改为在取景画面通过 `DISP` 自动常驻（并在激活 4ch 时自动扩展为 4 通道电平表）。
   - **实测事实（4ch 24-bit 编码矩阵与物理接管优先级）**：`[Audio Rec Level]` 为 **32 级步进 `0..31`**（出厂默认 **`26`**，`VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_0..31`），支持在菜单内按 `Delete` 键一键复位；内置限幅器（Limiter）始终自动介入且不可在 FX3 菜单关闭。`[Shoe Audio Set.]` 提供 `48kHz/24bit 4ch`、`48kHz/24bit 2ch` 与 **`48kHz/16bit 2ch`（默认）**，且在 **全部主录格式（`XAVC HS 4K`、`XAVC S 4K/HD`、`XAVC S-I 4K/HD/DCI 4K`）** 下均支持 `48kHz/24bit 4ch`，而**同步 Proxy 视频（`XAVC HS HD` / `XAVC S HD`）永远强制压缩为 `MPEG-4 AAC-LC 2ch 128 kbps`**（且 `100p/119.88p/120p+` 禁用 Proxy）。接管优先级上：**`3.5mm` `MIC` 插孔插入优先于 MI 靴**（强制退回 2ch 模拟并置灰 `[Shoe Audio Set.]`）；`XLR-H1` 的 `HANDLE AUDIO = OFF` 时退回机身内置麦；`DIGITAL/ANALOG = ANALOG` 时限制为 `2ch 16-bit`；`S&Q` 模式下音轨全面禁用。`[Wind Noise Reduct.]` **仅作用于机身内置立体声麦克风**，对 `XLR-H1` 及 `3.5mm` 外接麦完全无效。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18`）原生 LPCM `24-bit 48 kHz 4ch`，配备物理 `CH1..CH4` 电平旋钮、`AUTO/MAN` 与 `Through` 拨挡、`Smart Handle INPUT1/2` XLR 与手柄内置麦、6 档可配置 `Limiter Mode`（`Off / -6 / -9 / -12 / -15 / -17 dB`）及独立 `CH1&2 / CH3&4 AGC Mode`；`FX6 appFw.so` 内部同样保留 `AUDIO_OUTPUT_TIMING_{LIVE,LIP_SYNC}`，而 `4ch/48kHz/32bit float`（`FX6 ns1 0x3215`）目前仅停留在休眠字符串层。

2. **子系统 2（`[Face/Eye AF]` 被摄体识别破谣言：`Human` / `Animal` vs 休眠 `Bird` / `Insect` / `Car/Train` / `Airplane`）**：
   - **实测事实（CRITICAL 破谣言 + 对 [Wave 42](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h382-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md) 的显式勘误）**：`ILME-FX3 Ver. 7.02`（`ilc/2210`）无独立 AI 处理芯片，其 `MENU -> Focus -> [Face/Eye AF]` 下的 **`[Face/Eye Subject]` 仅开放 `Human`（默认）与 `Animal` 两项**！**`FX3 Ver. 7.02` 既不支持 `Bird`（修正 Wave 42 中将 `Ver. 3.00+/7.02` 误述为支持 `[Bird]` 的笔误——`Bird` 仅在 `ILME-FX30` / `ILME-FX2` / `ILCE-7RM5` / `ZV-E1` 等后续 AI 识别架构机型中提供），也不支持 `Insect`、`Car/Train`、`Airplane`**。
   - **实测事实（Still vs Movie 分裂与 `[Face Memory]` 活跃实证）**：即便选择 `Animal`，**`ILME-FX3 Ver. 7.02` 也仅能在静态照片模式（Still）中检测动物眼部，在 Movie 视频模式下完全不支持动物眼部或动物脸部识别**（`FX3 appFw.so` 存在硬互斥符号 `VAL_HAITA_..._TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT`）。`[Right/Left Eye Select]`（`Auto` 默认/`Right Eye`/`Left Eye` + 自定义键 `[Switch Right/Left Eye]`）与 `[Face/Eye Frame Disp.]`（**默认 `Off`**，`Clean HDMI / HDMI RAW` 零污染）均活跃；**`[Face Memory]`（最多登记 8 张人脸）与 `[Regist. Faces Priority]`（默认 `On`，选 `Animal` 时置灰）在 FX3 上完全活跃**，且已登记人脸数据**抗 `[Camera Settings Reset]`** 亦**不随 `CAMSET*.DAT` 导出**，须通过 `Delete All` 或 `[Initialize]` 清除。
   - **实测事实（跨机型共享 ELF 休眠证明）**：`FX3 appFw.so` 属于多机型共享的 BIONZ XR 代码库（枚举含 `ALCIN_UUD/DZ/GL/GS/LAX/LS/SA/YS/YT`），因此同时包含休眠枚举 `SUBJECT_DETECTION_{BIRD,ANIMAL_BIRD,INSECT,CAR_TRAIN,PLANE}`、灵敏度键 `BKID_APP_setting_{detection,tracking}_sensitivity_{bird,car_train,insect}`（注意 `airplane` 在 `BKID_APP_*` 中为 **`0` 命中**）以及 `_f.uxc` 共享词条（`_f 0x6cb1` `'Bird'`、`0x6957` `'Animal/Bird'`、`0x6996` `'Insect'`、`0x674e` `'Car/Train'`、`0x7440` `'Airplane'`）；但在 `ALCIN_UUD` 上被 `FEATURE_MANAGER_eye_face_af_gen_type` 运行时门控完全屏蔽。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18`）的 `Face/Eye Detection AF`（`Face/Eye Priority AF` / `Face/Eye Only AF` / `Off`）**仅支持 `Human`**，不支持动物/鸟类/交通工具；且 FX6 Ver. 6.0 已用 Real-time Tracking AF 的**临时会话式 `Saved Tracking Face`** 替代了旧版固定脸部登记菜单（`FX6 _2.uxc 0x4312` 仍残留 `'Delete Registered Face'` 历史词条）。

3. **子系统 3（`[Silent Mode Settings]`、`[Target Function Settings]` 与 `[Shutter When Pwr OFF]` 破谣言）**：
   - **实测事实**：`ILME-FX3 Ver. 7.02` 在 `MENU -> Shooting -> [Shutter/Silent]` 下采用 **`[Silent Mode Settings]` 二级菜单**（`_f 0x655f`），包含 `[Silent Mode]`（`Off` 默认/`On`）与 `[Target Function Settings]`（`_f 0x79c0`），**而非早期的单一开关**。开启 `[Silent Mode]` 后，系统强制锁定电子快门并关闭 `[Audio signals]`，同时硬禁用 **5 项功能**：**闪光灯拍摄、`[Long Exposure NR]`、`[e-Front Curtain Shut.]`、`BULB` 拍摄、`[Anti-flicker Shoot.]`**（注意：`[AF Illuminator]` 并未被静音模式自动禁用）。
   - **实测事实（`[Target Function Settings]` 仅 2 项 + `[Shutter When Pwr OFF]` 确认休眠）**：在 `ilc/2210` 中，FX3 的 `[Target Function Settings]` **仅有 2 个可选目标项**：① **`[Aperture Drive in AF]`**（`Standard` 默认/`Silent Priority`/`Not Target`，仅 Still AF 生效）；② **`[Auto Pixel Mapping]`**（`Off` 默认/`Not Target`；设为 `Off` 可阻断关机自动像素映射触发的机械快门动作与 `cnflasha` 坏点表写入）。尽管 `FX3 appFw.so` 与 `_f.uxc`（`0x709f` `'Shutter When Pwr OFF'`、`0x7495` `'Anti-dust Function'`）存在共享代码的 `image_sensor_barrier` 符号，但 **`ilc/2210` 实机菜单完全不包含 `[Shutter When Pwr OFF]`**——FX3 无断电机械帘幕防尘关闭功能；而 `ILME-FX6` 则彻底无机械焦平面快门（采用电子卷帘快门 + 内置电子可变 ND 与 `Auto Pixel Restore`）。

4. **子系统 4（`[Version]` 机身/镜头固件升级、`BODYDATA.DAT` `Slot 1` 强制门控与 `NO-GO` 物理刷机红线）**：
   - **实测事实**：`ILME-FX3 Ver. 7.02` 的 `MENU -> Setup -> [Setup Option] -> [Version]` 展示 `Body`（`Ver. 7.02`）、`Lens`（`Ver. xx`，当支持升级的 E 卡口镜头挂载时，`_g 0x6517`）与 `Mount Adaptor` 版本；`Ver. 6.00+` 在联网时会在该菜单显示红点更新提示（`_g 0x6516`），在 Zero-RF `Airplane Mode = On` 台架下自动静默。
   - **实测事实（`BODYDATA.DAT` `Slot 1` 路径、Ver. 2.04/2.05 跳板与 LED 故障码）**：通过记忆卡升级（`[Software Update]`，`_f 0x6fd6`）必须将未改名的 **`BODYDATA.DAT`** 置于相机格式化卡的 **`Slot 1` 根目录**（`Slot 2` 不被识别），且 `NP-FZ100` 电量必须 **`>= 51%`（3 格）**；**凡当前处于 `Ver. 2.02` 及更早版本的机身，严禁直接刷 `Ver. 7.02` `BODYDATA.DAT`**，必须先经 PC 端 `01_Update_ILMEFX3V20x` 升至 **`Ver. 2.04` 或 `Ver. 2.05`** 跳板版，否则触发报错。升级过程约 6 分钟，状态灯按 **`1 -> 3 -> 5` 次**闪烁推进，失败则循环闪烁 **`5 长（0.5s）/ 6 短（0.25s）`**（缺跳板或文件校验失败）或 **`7 长 / 7 短`**，跨机型文件则报 *"The target model for the update file is incorrect"*；升级完成后会自动重置 TC/UB。对比 **`ILME-FX6 Ver. 6.01`** 则使用 `Maintenance > Version > Version Up`（`FX6 _2.uxc 0x462c`），强制将 `BODYDATA.DAT` 放入 **Slot B 根目录**（忽略 Slot A），**强制要求连接交流电源适配器（`AC Adaptor`）**并拔除所有 USB/SDI/HDMI/冷靴外设。
   - **推断（严格硬件安全红线）**：`emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`hardware_live_attachment_authorized = False`。严禁任何自动化流程向物理卡槽写入或放置 `BODYDATA.DAT`、严禁对真机触发 `[Software Update]`/`Version Up`、严禁跨机型（FX6 <-> FX3）刷写固件（**`NO-GO / BLOCKED`**）。

---

## 1. 子系统 1：数字 MI 靴 `[Shoe Audio Set.]`、`XLR-H1` vs 机内麦、`[Wind Noise Reduct.]` 与 `[Audio Out Timing]`

### 1.1 `ILME-FX3 Ver. 7.02` 音频子系统全量真值表与菜单纠偏（`实测事实`）

> [!IMPORTANT]
> **菜单归属纠偏（`ilc/2210` 实证）**：任务提示中曾以 `Setup -> Sound Option -> [Audio Out Timing]` 与 `[Audio Level Display]` 提问；经 `ilc/2210` 官方文档及 `FX3 appFw.so` 交叉核验：**`[Audio Out Timing]` 实际位于 `Shooting -> [Audio Recording]` 之下**（与 `[Audio Recording]`、`[Audio Rec Level]`、`[Shoe Audio Set.]`、`[Wind Noise Reduct.]` 并列），而 `Setup -> [Sound Option]` 下只有 `[Volume Settings]`、`[4ch Audio Monitoring]` 与 `[Audio signals]`；同时 **`[Audio Level Display]` 在 `Ver. 2.00..7.02` 中已不作为独立菜单项提供**，仅保留在旧版代码/UXC 词库（`_f 0x7a36`）中。

| 菜单路径 / 项（`ilc/2210` Ver. 7.02） | `FX3 Ver. 7.02` 真值、步进与出厂默认 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Audio Recording]`**<br>(`Shooting -> Audio Recording`) | **`On`**（**默认**） / `Off`；`S&Q` 模式下禁用且不录声音 | **Can be reset** | `_f 0x72d3` / `base 0xe72e` / `_g 0x61b8`；`BKID_APP_setting_audio_recording` |
| **`[Audio Rec Level]`**<br>(`Shooting -> Audio Recording`) | **32 级步进 `0..31`**，出厂默认 **`26`**；作用于内置麦与 `3.5mm` `MIC` 口；按 `Delete` 键一键复位；**内置 Limiter 不可关闭** | **Can be reset** | `_f 0x63b9` / `0x6f0a`；`BKID_APP_setting_audio_recording_level`；`VAL_setting_audio_recording_level_AUDIO_RECORDING_LEVEL_0..31` |
| **`[Shoe Audio Set.]`**<br>(`Shooting -> Audio Recording`) | `48kHz/24bit 4ch`、`48kHz/24bit 2ch`、**`48kHz/16bit 2ch`**（**默认**）；仅挂载数字音频 MI 靴附件（如 `XLR-H1`、`ECM-B1M`/`B10`）时有效 | **Can be reset** | `_f 0x77f6`（`\ue62fShoe Audio Set.`）；`_f 0x6195` / `0x70bc` / `0x6dde`；`BKID_APP_setting_external_mic_audio_format`；`VAL_..._48KHZ_{24BIT_4CH,24BIT_2CH,16BIT_2CH}` |
| **`[Wind Noise Reduct.]`**<br>(`Shooting -> Audio Recording`) | **`Off`**（**默认**） / `On`；**仅对机身内置立体声麦生效**（数字低切抑制风噪；非风天会同步衰减正常人声/低频） | **Can be reset** | `_f 0x7b2a` / `base 0xe4b1`；`base 0xe4ae` `'Reduces wind noise when using the internal microphone.'`；`BKID_APP_setting_wind_noise_reduction` |
| **`[Audio Out Timing]`**<br>(`Shooting -> Audio Recording`，*非 Setup*) | **`Live`**（**默认**，低延迟直出监听） / **`Lip Sync`**（同步画音流水线延迟以对齐画面监听）；`S&Q` 下不可用 | **Can be reset** | `_f 0x62d8` / `0x6bc2`；`_f 0x753d`/`0x7af3` (`Live`) / `0x6066`/`0x6bbc` (`Lip Sync`)；`BKID_APP_setting_audio_output_timing`；`AUDIO_OUTPUT_TIMING_{LIVE,LIP_SYNC}` |
| **`[Audio Level Display]`**<br>*(旧版遗留词条)* | **Ver. 2.00..7.02 `ilc/2210` 已移除独立菜单**；通过 `DISP` 切出 `All Info` 自动显示（2ch 或 4ch 电平表） | — | `_f 0x7a36` `'Audio Level Display'`；`BKID_APP_setting_audio_recording_level_display`（Ver. 2+ 菜单未暴露） |
| **`[4ch Audio Monitoring]`**<br>(`Setup -> Sound Option`) | **`CH1/CH2`**（**默认**）、`CH3/CH4`、`CH1+3/CH2+4`、`CH1/CH1`、`CH2/CH2`；耳机仅限立体声混听，不可同时输出 4 路离散声道 | **Can be reset** | `_f 0x70dd` / `0x776e`；`BKID_APP_setting_4ch_audio_monitoring`；`AUDIO_MONITORING_4CH_{CH1_CH2,CH3_CH4,CH1_3_CH2_4,CH1_CH1,CH2_CH2}` |
| **`[4ch Audio Output]`**<br>(`Setup -> External Output -> HDMI Output Settings`) | **`CH1/CH2`**（**默认**） / `CH3/CH4`（HDMI 仅支持双声道输出，须择组输出） | **Can be reset** | `BKID_APP_setting_hdmi_4ch_audio_output` |

### 1.2 `48kHz/24bit 4ch` 编码兼容性、`XLR-H1` 路由与硬件接管优先级（`实测事实`）

1. **视频封装格式与 Proxy 编码行为（`实测事实`）**：
   - `ILME-FX3 Ver. 7.02` 的全部主记录格式——**`XAVC HS 4K`**（LPCM 24-bit 4ch）、**`XAVC S 4K` / `XAVC S HD`**（LPCM 24-bit 4ch）、**`XAVC S-I 4K` / `XAVC S-I HD` / `XAVC S-I DCI 4K`**（LPCM 24-bit 4ch）——只要接入兼容 4ch 24-bit 的 MI 靴附件（如原装 `XLR-H1` 手柄）并将 `[Shoe Audio Set.]` 设为 `48kHz/24bit 4ch`，**均可写入 4 声道 24-bit 48 kHz LPCM 音轨**。
   - **Proxy 轨降级约束**：开启 `[Proxy Recording]` 时，Proxy 文件（`XAVC HS HD` / `XAVC S HD`）**永远仅记录 `MPEG-4 AAC-LC 2ch`（128 kbps）**，不会携带 4ch 24-bit LPCM；且当主视频帧率设为 `100p/119.88p/120p+` 时 Proxy 录制本身被禁用。
2. **输入优先级与 `XLR-H1` `HANDLE AUDIO` / `3.5mm` 接管规则（`实测事实`）**：
   - **`3.5mm` `MIC`（红色插孔）最高硬件接管**：只要向机身左侧 `3.5mm` `MIC` 插孔插入插头，无论是否安装了 `XLR-H1` 或数字 MI 靴麦，机身立即切回 `3.5mm` 模拟 2ch 输入，**`[Shoe Audio Set.]` 菜单自动置灰**，由 `[Audio Rec Level]`（`0..31`）接管增益。
   - **`XLR-H1` `HANDLE AUDIO` 开关与拨挡**：`XLR-H1` 上拨到 **`HANDLE AUDIO = OFF`** 时，手柄数字音频被切断，相机自动回落至**机身内置立体声麦**（此时 `[Audio Rec Level]` 与 `[Wind Noise Reduct.]` 重新生效）；当 `HANDLE AUDIO = ON` 时，若手柄侧面 `DIGITAL/ANALOG` 拨向 **`ANALOG`**（或挂载仅支持模拟/2ch 的旧款 MI 靴麦），`[Shoe Audio Set.]` 被限制为 **`48kHz/16bit 2ch`**，24-bit 4ch 选项不可用。
   - **4 声道映射（`XLR-H1` `INPUT SELECT = IN1·IN2`）**：`INPUT1`（XLR/TRS）-> `CH1`，`INPUT2`（XLR/TRS）-> `CH2`，`INPUT3`（3.5mm 立体声微麦口 L/R）-> **`CH3` / `CH4`**；若 `INPUT SELECT = IN1`（单路分配），`INPUT1` 镜像至 `CH1/CH2`。机身侧 `AUDIO` 菜单无法控制 `XLR-H1` 上的物理旋钮增益与 `AUTO/MAN/LINK` 状态。

### 1.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 四声道音频架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210` + `FX3 appFw.so`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **4 声道来源与硬件依赖** | 依赖数字 MI 靴（`XLR-H1` 等）才支持 `24-bit 4ch`；裸机仅机内立体声 2ch | **机身/智能手柄原生 4 声道 `24-bit 48 kHz LPCM`**（无需外接转换器） |
| **物理通道增益控制** | 裸机靠菜单 `[Audio Rec Level]`（`0..31` def `26`）；4ch 增益全靠 `XLR-H1` 侧面旋钮 | 机身侧面板独立 **`CH1..CH4` 物理旋钮 + `AUTO/MAN` 开关**（`CH3/CH4` 含 `Through` 档位）；手柄配 `INPUT1/2` XLR |
| **风噪抑制与限幅器** | `[Wind Noise Reduct.]` **仅限机内麦**；内置限幅器常开且**不可配阈值** | `Audio > Audio Input > INPUT1/2 Wind Filter`（独立低切）+ **6 档可配置 `Limiter Mode`**（`Off / -6 / -9 / -12 / -15 / -17 dB`）+ `CH1&2 / CH3&4 AGC Mode`（`Mono/Stereo`） |
| **监听与输出延迟** | `[Audio Out Timing]`（`Live`/`Lip Sync`）位于 `Shooting -> Audio Recording`；耳机 `[4ch Audio Monitoring]`（5 种双声道组合） | `Monitoring > Monitor CH` 支持 `CH1/CH2`、`CH3/CH4`、`MIX ALL` 及单通道监听；`FX6 appFw.so` 存在同源 `BKID_APP_SETTING_AUDIO_OUTPUT_TIMING`；`FX6 ns1 0x3215` 含休眠 `4ch/48kHz/32bit float` 字符串 |

---

## 2. 子系统 2：`[Face/Eye AF]` 被摄体识别破谣言（`Human`/`Animal` vs 休眠 `Bird`/`Insect`/`Car/Train`/`Airplane`）

### 2.1 `ILME-FX3 Ver. 7.02` 真实菜单矩阵与对 Wave 42 的明确勘误（`实测事实`）

> [!WARNING]
> **破谣言与 Wave 42 勘误（`ilc/2210` + `FX3 appFw.so` 实证）**：
> 1. 社区与 [Wave 42](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h382-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md) 第 2 节曾误将 `ILME-FX3 Ver. 3.00+/7.02` 记为支持 `[Bird]`。经 `ilc/2210` 官方手册（*Face/Eye Subject*、*Face/Eye Prior. in AF*）及 FX3 全版本固件发布说明（`Ver. 2.00..7.02`）逐一核对：**`ILME-FX3 Ver. 7.02` 从未开放 `Bird`、`Insect`、`Car/Train` 或 `Airplane` 识别——`[Face/Eye Subject]` 仅有 `Human` 与 `Animal` 两项！**（`Bird` 直到配备独立 AI 处理单元的 `ILME-FX2` / `ZV-E1` / `ILCE-7RM5` 或后续型号 `ILME-FX30` 才开放。）
> 2. 此外，[Wave 42](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h382-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/reports/2026-11-15-global-sony-wave42-apsc-s35-4k-lockout-face-eye-af-right-left-eye-version-read-only-intel/README.md) 顺序列出了 `[Face/Eye Frame Disp.]` 的 `[On] / [Off]`，本文进一步确证其**出厂默认值为 `[Off]`**（`ilc/2210` *List of default setting values*）。

| 菜单路径（`Focus -> [Face/Eye AF]`） | `FX3 Ver. 7.02` 真实选项、默认与模式限制 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Face/Eye Prior. in AF]`** | **`On`**（**默认**；`Intelligent Auto` 模式下锁定 `On`） / `Off` | **Can be reset** | `_f 0x68e6` / `0x6bdd`；`BKID_APP_setting_face_eye_prior_in_af` |
| **`[Face/Eye Subject]`** | 仅 **`Human`**（**默认**） / **`Animal`**<br>**关键限制**：`Animal` **仅在 Still（静态照片）下可识别动物眼部**，**Movie/S&Q 下完全不检测动物眼部与动物面部**；**无 `Bird`/`Insect`/`Car/Train`/`Airplane`** | **Can be reset** | `_f 0x70fa` / `0x7643`；`_f 0x763f` (`Human`) / `0x6511` (`Animal`)；`VAL_HAITA_..._TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT` |
| **`[Right/Left Eye Select]`** | **`Auto`**（**默认**） / `Right Eye` / `Left Eye`（以被摄体自身左右眼为准；可绑定自定义键 `[Switch Right/Left Eye]`）；适用于 `Human` 及 Still 模式 `Animal` | **Can be reset** | `_f 0x63a5` / `0x69fc`；`BKID_APP_setting_right_left_eye_select` |
| **`[Face/Eye Frame Disp.]`** | **`Off`**（**默认**） / `On`（当 `[AF Area Auto Clear] = On` 时合焦后自动消失；**绝不随 Clean HDMI / HDMI RAW 输出**） | **Can be reset** | `_f 0x7183` / `0x74e3`；`BKID_APP_setting_face_eye_frame_disp` |
| **`[Face Memory]`** | **活跃（最多登记 8 张人脸）**：`New Registration`、`Order Exchanging`、`Delete`、`Delete All`；**不含于 `CAMSET*.DAT`** | **Not available**<br>*(抗 Reset；须 `Delete All` 或 `[Initialize]`)* | `_f 0x6533` / `0x6d87`；`BKID_APP_face_memory_*` |
| **`[Regist. Faces Priority]`** | **`On`**（**默认**） / `Off`（当 `[Face/Eye Subject] = Animal` 时置灰禁用） | **Can be reset** | `_f 0x629c` / `0x7063`；`BKID_APP_setting_regist_faces_priority` |

### 2.2 `FX3 appFw.so` 多机型共享 ELF 与休眠 AI-Unit 识别码证据链（`实测事实`）

为什么在解包 `FX3 appFw.so` 与 `string_*_f.uxc` 时能搜索到 `Bird`、`Insect`、`Car/Train`、`Airplane`？实测二进制符号分布如下：
1. **多机型共享架构实证（`实测事实`）**：`FX3 appFw.so` 内部 `PRODUCT_MODEL_*` 枚举同时包含 `ALCIN_UUD`（FX3）、`DZ`、`GL`、`GS`、`LAX`、`LS`、`SA`、`YS`、`YT` 等同代/衍生 BIONZ XR 家族代号。
2. **休眠 UXC 词条与 `VAL_setting_subject_detection_*`（`实测事实`）**：
   - UXC `_f` 包保留了全家族通用词条：`_f 0x6cb1` (`'Bird'`)、`_f 0x6957` (`'Animal/Bird'`)、`_f 0x6996` (`'Insect'`)、`_f 0x674e` (`'Car/Train'`)、`_f 0x7440` (`'Airplane'`)。
   - ELF 中存在通用值表 `VAL_setting_subject_detection_SUBJECT_DETECTION_{HUMAN,ANIMAL,BIRD,ANIMAL_BIRD,INSECT,CAR_TRAIN,PLANE}`，以及共享灵敏度键 `BKID_APP_setting_{detection,tracking}_sensitivity_{bird,car_train,insect}`；但注意精确细节：**`airplane` 在 `BKID_APP_*` 中为 `0` 命中**，且被摄体切换开关 `valid_subject_detection_switch_*` 仅覆盖 `human`/`animal`/`bird` 三类，不包含 `insect`/`car_train`/`airplane`。
3. **运行时门控实证（`实测事实`）**：`FX3 appFw.so` 通过 `FEATURE_MANAGER_eye_face_af_gen_type`（`TYPE_EYE_FACE_AF_GEN_TYPE_2` / `_TYPE_4`）以及显式能力标志 **`TYPE_ANIMAL_EYE_AF_IN_MOVIE_NOT_SUPPORT`**、**`TYPE_ANIMAL_EYE_AF_PHASE_2_0_NOT_SUPPORT`** 对 `ALCIN_UUD` 施加硬件能力门控——在 FX3 上彻底封死 `Bird`/`Insect`/`Car/Train`/`Airplane` 菜单入口，并将 `Animal` 限制在 Still-Only 眼部检测路径。

### 2.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 被摄体识别与人脸记忆对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18`) |
| :--- | :--- | :--- |
| **菜单名称与工作模式** | `Focus -> [Face/Eye AF]` -> `[Face/Eye Prior. in AF]`（`On` / `Off`） | `Shooting > Focus > Face/Eye Detection AF`：**`Face/Eye Priority AF`** / **`Face/Eye Only AF`**（仅在检测到人脸/眼部时驱动 AF）/ `Off` |
| **支持被摄体范围** | **`Human`（Still/Movie）+ `Animal`（仅 Still 眼部）** | **仅 `Human`**（无 Animal / Bird / Insect / Car / Airplane） |
| **左右眼切换** | 支持 `[Right/Left Eye Select]`（`Auto`/`Right Eye`/`Left Eye`）+ 自定义键 | 支持 Face/Eye 选择框切换与左/右眼自动跟踪，但无 FX3 式消费级菜单细分项 |
| **人脸记忆机制** | **活跃 `[Face Memory]`**（永久存储最多 **8 张人脸**，独立于 `CAMSET*.DAT` 与 Reset） | **无 `[Face Memory]` 长期库**（`FX6 _2.uxc 0x4312` 仅残存历史 `'Delete Registered Face'`）；Ver. 6.0 改用 Real-time Tracking AF 下的**临时会话 `Saved Tracking Face`**（触摸或多功能拨杆锁定后在本次追踪期间记忆，停止追踪或按 `PUSH AF` 即清除） |

---

## 3. 子系统 3：`[Silent Mode Settings]`、`[Target Function Settings]` 耦合与 `[Shutter When Pwr OFF]` 破谣言

### 3.1 `ILME-FX3 Ver. 7.02` 静音模式架构与 `[Target Function Settings]` 实证（`实测事实`）

1. **二级菜单结构与硬互斥耦合（`实测事实`）**：
   - `ILME-FX3 Ver. 7.02` 在 `MENU -> Shooting -> [Shutter/Silent]` 下提供 **`[Silent Mode Settings]`**（`_f 0x655f` / `0x72df`），内含 **`[Silent Mode]`**（`Off` 默认/`On`，可 Reset）与 **`[Target Function Settings]`**（`_f 0x79c0`），而非单一布尔开关。
   - 开启 **`[Silent Mode] = On`** 后，固件强制执行两项锁定与 **5 项功能禁用**：
     - **强制锁定**：① `[Shutter Type]` 与 `[Shutter Type in Interval]` 锁定为电子快门（`Electronic Shutter`）；② `[Audio signals]`（`base 0xe0c8` 提示音/电子音）强制静默为 `Off`；
     - **强制禁用的 5 项功能**（`ilc/2210` *Silent Mode Settings* 明文）：**闪光灯拍摄（Flash）**、**`[Long Exposure NR]`**、**`[e-Front Curtain Shut.]`**、**`BULB` 拍摄**、**`[Anti-flicker Shoot.]`**。
     - **未被自动静音的物理噪声**：对焦驱动音、光圈叶片驱动音及 `[AF Illuminator]`（需手动关闭或通过 `[Target Function Settings]` 控制）不会因主开关自动消除。
2. **`[Target Function Settings]` 仅有的 2 个活跃子项（`实测事实`）**：
   - **`[Aperture Drive in AF]`**（`_f 0x61b5`，**仅 Still AF 有效**）：可选 **`Standard`**（**默认**，可 Reset）、**`Silent Priority`**（`_f 0x64d3`，降低光圈马达噪音，但对焦速度可能变慢）、**`Not Target`**（`_f 0x64e7`，不随 Silent Mode 改变）。
   - **`[Auto Pixel Mapping]`**（`_f 0x7734`）：可选 **`Off`**（**默认**，可 Reset；开启静音模式时跳过自动像素映射）或 **`Not Target`**（仍按出厂周期执行）。`UXC _g 0x623d` / `0x63fa` 明确警告：将其设为 `Off` 后需定期手动执行 `[Pixel Mapping]`；在无快门/安全台架下保持 `Off` 可**避免关机时意外触发机械帘幕动作与 `cnflasha` 非易失坏点表写入**。

### 3.2 `[Shutter When Pwr OFF]`（`image_sensor_barrier`）休眠证伪 vs `ILME-FX6` 无快门架构（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210` + `FX3 appFw.so`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **机械快门硬件** | 具备电子前帘 + 机械焦平面快门（仅 Still / 像素映射使用） | **无机械快门（Shutterless 架构）**：纯电子卷帘快门 + 内置电子可变 ND 滤镜 |
| **`[Silent Mode Settings]` 与 `[Target Function Settings]`** | 活跃二级菜单；`[Target Function Settings]` **仅含 2 项**：`[Aperture Drive in AF]` 与 `[Auto Pixel Mapping]` | **无 `[Silent Mode Settings]` 菜单**（仅独立设置 `Audio > Beep` 开关提示音） |
| **`[Shutter When Pwr OFF]` (`image_sensor_barrier`)** | **实机完全休眠 / 不存在**！`FX3 appFw.so` 存在共享代码符号 `BKID_APP_setting_silent_detail_setting_image_sensor_barrier` / `EVENT_REMOTE_ANTI_DUST_FUNCTION_IMAGE_SENSOR_BARRIER` 及 `_f 0x709f` `'Shutter When Pwr OFF'` / `_f 0x7495` `'Anti-dust Function'`，但 **`ilc/2210` 实机无此功能，断电不闭合帘幕** | **物理上不可能**：无机械快门帘幕，`FX6 appFw.so` 同源 `image_sensor_barrier` 符号亦为休眠残余 |
| **坏点映射机制** | `[Pixel Mapping]`（Still 机械闭合帘幕采集黑帧），可被 `[Target Function Settings]` 设为 `Off` | `Maintenance > Auto Pixel Restore`（`FX6 ns1 0x2e4e / 0x324a` `'Auto Pixel Restore'`，无需机械快门） |

---

## 4. 子系统 4：`[Version]` 机身/镜头固件升级（`BODYDATA.DAT` `Slot 1` 门控）与 `NO-GO` 物理刷机红线

### 4.1 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 固件升级与故障码矩阵（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210` + 官方升级指引 + `FX3 appFw.so`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + Ver. 6.02 官方指引) |
| :--- | :--- | :--- |
| **菜单路径与版本显示** | `Setup -> [Setup Option] -> [Version]`（`base 0xe396`）：显示 **`Body`**（`Ver. 7.02`）、**`Lens`**（`_g 0x6517` `Lens: Ver.${v1}`，仅挂载支持升级的 E 卡口镜头时显示）与 `Mount Adaptor`；`Ver. 6.00+` 在联网时显示更新徽标（`_g 0x6516` `'There is the latest software version.'`），在 `Airplane Mode = On` 台架下静默 | `Maintenance > Version`（`FX6 ns2 0x5655`）：显示 **`Version Number`**、**`Lens Version Number`**（`0x55c8`）、`Net-Func`（`0x4dd3`）、`Ext. Unit`（`0x4f5e`）；触发项为 **`Version Up`**（`0x462c`） |
| **记忆卡升级触发与唯一卡槽** | `[Version] -> [Software Update]`（`_f 0x6fd6` / `0x7283`；Ver. 2.04/3.00+ 引入）：**必须置于 `Slot 1` 根目录**（`Slot 2` 绝不识别！） | `Version > Version Up > Execute`：**必须置于 `Slot B` 根目录**（`Slot A` 被忽略！） |
| **升级镜像文件名与体积参考** | **`BODYDATA.DAT`**（严禁 `(1)`/`-3` 重命名后缀） | **`BODYDATA.DAT`**（Ver. 6.02 官方体积为 `848,254,320` 字节） |
| **供电强制门控** | `NP-FZ100` 电池剩余电量 **`>= 51%`（屏幕至少 3 格）** | **强制连接交流电源适配器（`AC Adaptor`）**（纯电池会弹出 `'Please use the AC Adaptor'` 阻断）；拔除 USB/SDI/HDMI/MI 靴附件 |
| **跳板版与设置影响** | **处于 `Ver. 2.02` 或更早版本的机身必须先经 PC 端升级至 `Ver. 2.04` 或 `Ver. 2.05` 跳板版**（不可直接刷 `Ver. 7.02` `BODYDATA.DAT`）；升级后 **TC/UB 会被重置** | 从 `Ver. 5.02` 及更早版本升至 `Ver. 6.0x` 会**初始化部分机身设置**（官方要求事先导出 `All File` 至 `Slot B` 备份） |
| **耗时、指示灯进度与故障码** | 全程约 **6 分钟**：正常按存取灯 **`1 -> 3 -> 5` 次**闪烁推进；失败则循环闪烁 **`5 长（0.5s）/ 6 短（0.25s）`**（缺 Ver. 2.04/2.05 跳板或文件损坏）或 **`7 长 / 7 短`**，若跨机型/版本异常则提示 `_g 0x630a`（`'The update file version is incorrect.'`）或 *"The target model for the update file is incorrect"* | 全程屏显/指示灯提示进度，出现错误则报 `FX6 ns1 0x26bc` `'Version Upgrade Error on Camera!'` 或重启恢复 |
| **底层 ELF 符号实证** | `BKID_APP_{body_version,update_body_version,body_update_start_flag}`、`PRM_lens_version`、`get_lens_version_after_uud`、`version_update_type_selected`；`libsdfileinputupdaterapi.so`（`FX3 p1 2.05`） | `BKID_APP_...` 版本门控与 `Version Upgrade` 状态机 |

### 4.2 物理刷机与 `BODYDATA.DAT` 严格 **`NO-GO / BLOCKED`** 安全红线（`实测事实` + `推断`）

> [!CAUTION]
> **硬件与合规绝对红线（`NO-GO / BLOCKED`）**：
> - `emmc_writes_authorized = False` | `cross_model_flash_authorized = False` | `hardware_live_attachment_authorized = False` | `raw_firmware_bytes_leaked = 0`。
> 1. **严禁对真实物理相机执行任何刷机准备或触发操作**：严禁向任何物理插入真实 `ILME-FX3`（`Slot 1`）或 `ILME-FX6`（`Slot B`）的 SD/CFexpress Type A 卡拷贝、生成或保留 `BODYDATA.DAT`，严禁诱导或自动点击 `[Software Update]` / `Version Up`。
> 2. **严禁跨机型或跳过跳板刷写**：尽管 `FX3`（`Slot 1`）与 `FX6`（`Slot B`）均采用名为 `BODYDATA.DAT` 的更新文件名，两者的加密签名、分区表（`nflasha*`）与硬件平台存在根本差异；且 FX3 `Ver. 2.02` 及以下机器跳过 `Ver. 2.04/2.05` 直接强刷会立即触发 `5 长 / 6 短` 校验锁定。所有 `BODYDATA.DAT` 及 `nflasha*` 分析在实验室中**永远仅限本地只读（`os.O_RDONLY`）离线验证**。

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 实证覆盖范围 |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`nflasha15/lib/appFw.so`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `audio_recording_level_0..31`、`external_mic_audio_format`、`audio_output_timing`、`4ch_audio_monitoring`、`SUBJECT_DETECTION_*` 与 `NOT_SUPPORT` 门控、`face_memory`、`silent_detail_setting`、`image_sensor_barrier` 休眠、`body_version`/`lens_version` |
| `FX6 appFw.so` (`FX6 .../lib/appFw.so`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `AUDIO_OUTPUT_TIMING_{LIVE,LIP_SYNC}`、`image_sensor_barrier` 休眠、FX6 音频/对焦/版本门控状态机 |
| `FX6 AVBB_SCN_START_AUDIO.so` | `70,096` | `96252cad4c9c13575a6c071be9f9fe72853382af7a4133bac7257e056f71420a` | FX6 音频服务启动组件基线校验 |
| `FX6 libInfraHotshoe.so` | `47,808` | `0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6` | FX6 MI 热靴底层通信库基线校验 |
| `FX3 p1 2.05 nflasha1` | `19,377,152` | `ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591` | FX3 `Ver. 2.05` 跳板版系统镜像基线（不泄漏原始字节） |
| `FX3 p1 2.05 libsdfileinputupdaterapi.so` | `60,584` | `257164d1cdf88757b8c0e2ba08ac47b06c46007410af308b7a8571b442b00cd2` | FX3 `Slot 1` SD 卡 `BODYDATA.DAT` 升级接口库 |
| `FX3-CX95900_ALLLANG-Backup.bin` (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失备份结构基线（`BK4\x00`） |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | FX3 `hdr_flag=15` 主菜单与提示英文包（`7,475` 条 `0x6000..0x7d3d`） |
| `FX3 string_english.uxc` / `_g.uxc` | `165,740` / `69,600` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | FX3 `hdr_flag=8` 基础菜单、Wind Noise、版本及升级报错英文包 |
| `FX3 string_simplifiedchinese_f.uxc` / `.uxc` / `_g.uxc` | `322,652` / `149,064` / `61,296` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `_f` / 基础 / 扩展三包四语 `resid16` 精确映射 |
| `FX3 string_traditionalchinese_f.uxc` / `.uxc` / `_g.uxc` | `324,148` / `151,908` / `61,372` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文 `_f` / 基础 / 扩展三包四语 `resid16` 精确映射 |
| `FX3 string_japanese_f.uxc` / `.uxc` / `_g.uxc` | `447,840` / `208,564` / `89,428` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本语原厂 `_f` / 基础 / 扩展三包四语 `resid16` 精确映射 |
| `FX6 string_english.uxc` / `_2.uxc` | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 `32bit float`（休眠）、`Delete Registered Face`（残余）、`Auto Pixel Restore`、`Version Up` 字符串包 |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`，由 [uxc_multilang_and_font_verifier.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h382-global-sony-wave62-shoe-audio-4ch-subject-recog-silent-target-lens-fw-intel/outputs/fx3-firmware-lab/fx3_firmware_lab/uxc_multilang_and_font_verifier.py) 与 `_f` `0x1c\x1e` 解析器直接核验）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x72d3` / `0x63b9` / `0x77f6` | `Audio Recording` / `Audio Rec Level` / `Shoe Audio Set.` | `录音` / `录音音量` / `MI靴音频设置` | `音訊錄製` / `錄音音量` / `MI靴音訊設定` | `音声記録` / `録音レベル` / `ｼｭｰの音声設定` | **活跃**（`0..31` def `26`；4ch 24bit） |
| `_f` `0x6195` / `0x70bc` / `0x6dde` | `Sets ... 48kHz, ... 24bit, ... 4ch.` / `24bit ... 2ch.` / `16bit ... 2ch.` | `...48kHz...24bit...4ch。` / `24bit...2ch。` / `16bit...2ch。` | `...48kHz...24bit...4ch。` / `24bit...2ch。` / `16bit...2ch。` | `...48kHz...24bit...4ch` / `24bit...2ch` / `16bit...2ch` | **活跃**（`[Shoe Audio Set.]` 三态说明） |
| `base` `0xe4b1` / `0xe4ae` | `Wind Noise Reduct.` / `Reduces wind noise when using the internal microphone.` | `减少风噪声` / `使用内部麦克风时减少风噪声。` | `減少風噪音` / `使用內部麥克風時降低風聲。` | `風音低減` / `内蔵マイク使用時に風雑音を低減します` | **活跃**（**仅限机内麦**铁证） |
| `_f` `0x7a36` | `Audio Level Display` | `音频等级显示` | `音訊等級顯示` | `音声レベル表示` | **Ver. 2+ 菜单取消**（改 `DISP` 自动显表） |
| `_f` `0x6bc2` / `0x753d` / `0x6066` | `Audio Out Timing` / `Live` / `Lip Sync` | `音频输出时刻` / `实况转播` / `唇音同步` | `音訊輸出時刻` / `即時播送` / `唇音同步` | `音声出力タイミング` / `ライブ` / `リップシンク` | **活跃**（位于 `Shooting -> Audio Recording`） |
| `_f` `0x70dd` | `4ch Audio Monitoring` | `4ch音频监测` | `4ch音訊監聽` | `4ch音声のﾓﾆﾀﾘﾝｸﾞ` | **活跃**（位于 `Setup -> Sound Option`） |
| `_f` `0x68e6` / `0x70fa` | `Face/Eye Prior. in AF` / `Face/Eye Subject` | `AF人脸/眼睛优先` / `脸/眼摄体检测` | `對焦面孔眼部優先` / `面/眼攝體偵測` | `AF時の顔/瞳優先` / `顔/瞳検出対象` | **活跃**（FX3 仅限 `Human`/`Animal`） |
| `_f` `0x763f` / `0x6511` | `Human` / `Animal` | `人` / `动物` | `人類` / `動物` | `人物` / `動物` | **活跃**（`Animal` 仅限 Still 眼部） |
| `_f` `0x6cb1` / `0x6957` / `0x6996` / `0x674e` / `0x7440` | `Bird` / `Animal/Bird` / `Insect` / `Car/Train` / `Airplane` | `鸟类` / `动物/鸟类` / `昆虫` / `汽车/火车` / `飞机` | `鳥` / `動物/鳥` / `昆蟲` / `汽車/火車` / `飛機` | `鳥` / `動物/鳥` / `昆虫` / `車/列車` / `飛行機` | **休眠破谣言**（共享词库，FX3 运行时屏蔽） |
| `_f` `0x63a5` / `0x7183` / `0x6533` / `0x629c` | `Right/Left Eye Select` / `Face/Eye Frame Disp.` / `Face Memory` / `Regist. Faces Priority` | `右眼/左眼选择` / `人脸/眼睛检测框` / `人脸登记` / `登记的人脸优先` | `右眼/左眼選擇` / `面孔/眼部偵測框` / `面孔登錄` / `登錄面孔優先` | `右目/左目選択` / `顔/瞳枠表示` / `個人顔登録` / `登録顔優先` | **活跃**（`Face Memory` 8 张且抗 Reset） |
| `_f` `0x655f` / `0x7046` / `0x79c0` | `Silent Mode Settings` / `Silent Mode` / `Target Function Settings` | `静音模式设置` / `静音模式` / `目标功能设置` | `靜音模式設定` / `靜音模式` / `目標功能設定` | `ｻｲﾚﾝﾄﾓｰﾄﾞ設定` / `サイレントモード` / `対象機能の設定` | **活跃**（二级菜单架构） |
| `_f` `0x61b5` / `0x64d3` / `0x64e7` / `0x7734` | `Aperture Drive in AF` / `Silent Priority` / `Not Target` / `Auto Pixel Mapping` | `AF光圈驱动` / `静音优先级` / `非目标` / `自动像素映射` | `對焦中的光圈驅動` / `靜音優先順序` / `不是目標` / `自動像素映射` | `AF時の絞り駆動` / `サイレント優先` / `対象にしない` / `ｵｰﾄﾋﾟｸｾﾙﾏｯﾋﾟﾝｸﾞ` | **活跃**（`Target Function Settings` 仅此 2 项） |
| `_f` `0x709f` / `0x7495` | `Shutter When Pwr OFF` / `Anti-dust Function` | `关机时快门` / `防尘功能` | `關閉電源時快門` / `防塵功能` | `電源OFF時のｼｬｯﾀｰ` / `アンチダスト機能` | **休眠破谣言**（FX3 无断电闭帘功能） |
| `base` `0xe0c8` / `0xe396` / `0xea58` / `_g` `0x6517` | `Audio signals` / `Version` / `Body` / `Lens: Ver.${v1}` | `音频信号` / `版本` / `机身` / `镜头: Ver.${v1}` | `提示音` / `版本` / `機身` / `鏡頭: Ver.${v1}` | `電子音` / `バージョン表示` / `ボディー` / `レンズ: Ver.${v1}` | **活跃**（静音锁定电子音为关） |
| `_f` `0x6fd6` / `_g` `0x6516` / `0x630a` / `0x616b` | `Software Update` / `There is the latest software version.` / `The update file version is incorrect.` / `Software update complete.` | `软件更新` / `有最新软件版本。` / `更新文件版本不正确。` / `软件身更新完成。` | `軟體更新` / `有最新軟體版本。` / `更新檔案版本不正確。` / `軟體更新完成。` | `ｿﾌﾄｳｪｱｱｯﾌﾟﾃﾞｰﾄ` / `本機ｿﾌﾄｳｪｱに最新ﾊﾞｰｼﾞｮﾝがあります` / `アップデートファイルのバージョンが\n正しくありません` / `ソフトウェアアップデートが完了しました` | **活跃**（`Slot 1` `BODYDATA.DAT`；**物理刷机 `NO-GO`**） |
