# 全球 Sony 实机情报 Wave 64（`2^6 = 64th` Wave 幂次里程碑 · `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Breathing Comp.]` 镜头白名单与裁切/HFR/RAW/S&Q 互锁、电影 `[File Settings]` `[Cam ID + Reel#]`/`37` 字符标题与 `SDHC` `4 GB` 分割、`[Copyright Info]` `46` 字符/`[Write Serial Number]` 持久化与 `CAMSET` 隔离，以及 `[Auto Power OFF Temp.]` / 9 条件 `[Power Save Start Time]` / 休眠 `[Power Save by Monitor]` / `[NTSC/PAL Selector]` 格式化风险）

- **日期**：`2026-11-17`
- **里程碑**：**Wave 64（`2^6 = 64th` Global Sony Real-Hardware Empirical Intelligence Wave）**
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Lens Compensation (still image/movie) / File Settings (movie) / Memory cards that can be used / Copyright Info / Write Serial Number (still image/movie) / Save/Load Settings / Power Save Start Time / Auto Power OFF Temp. / NTSC/PAL Selector / List of default setting values*）
  - 官方 Sony `ILME-FX3` `Ver. 3.00 / 4.00 / 6.00 / 7.00 / 7.02` 固件说明及 `support.d-imaging.sony.co.jp`（*Breathing Compensation Compatibility / Catalyst Prepare Breathing Compensation*）
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *Technical > Lens > Breathing Compensation (p.117)*、*TC/Media > Clip Name Format (p.108)*、*Project > Rec Format > Frequency (p.19, p.97)*、*Maintenance > Clock Set (p.124)*）及 `Ver. 2.00..6.01` 固件说明
  - 并严格对照 `os.O_RDONLY` 本地 donor 二进制实证（`FX3 appFw.so`、`libSaveLoadSettings.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so` 及 `FX6 string_english.uxc` / `_2.uxc`；并交叉核验 [Wave 29](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave29-file-settings-sdhc-shotmark-tc-regenerate-slot1-reclamp-coupled-tally-intel/README.md)、[Wave 30](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave30-pixel-mapping-reboot-ntsc-pal-reset-persistence-gamma-assist-displaylut-intel/README.md)、[Wave 31](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave31-steadyshot-active-raw-hfr-ciz-center-af-powersave-9cond-temp-high-intel/README.md)、[Wave 41](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave41-auto-slow-shutter-6locks-hdmi-reccontrol-tcout-4chaudio-breathing-comp-intel/README.md)、[Wave 43](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave43-release-wo-card-lens-disp-audio-meter-v2-vs-v1-copyright-info-46char-intel/README.md)、[Wave 44](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave44-file-settings-camid-reel-37char-gamma-disp-assist-log-lockout-auto-review-tcub-intel/README.md)、[Wave 46](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-17-global-sony-wave46-power-save-by-monitor-language-volume-delete-confirm-intel/README.md) 与 [Round 57](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu/README.md)）。
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、SHA-256 账本与官方 Help Guide/说明书条目）与 **`推断`**（Tier-0 `Slot 1` 保险库边界与台架防护推论）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[Breathing Comp.]` `Ver. 3.00+..7.02` 光学裁切、镜头白名单、HFR/S&Q/RAW 锁死与 Catalyst 勘误）**：
   - **实测事实（菜单、Reset 与镜头门控）**：`ILME-FX3 Ver. 7.02` 位于 `Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`（`On` / `Off`，出厂默认 **`Off`**）。与同组其余 3 项（`Shading Comp.`/`Chromatic Aberration Comp.`/`Distortion Comp.` 为 `Not available`）**不同**，**`[Breathing Comp.]` 可被 `[Camera Settings Reset]` 复位**（`Can be reset`）。`FX3 appFw.so` 实证其核心控制链为 `BKID_APP_setting_lens_comp_breathing`、`PID_SET_BREATHING_CORRECTION`、`PRM_HAITA_setting_lens_comp_breathing_exposure_mode`（`EXPOSURE_MODE_MOVIE`）、`PRM_HAITA_breathing_correction_lens_type_lens_information`（`SUPPORT` / `NOT_SUPPORT` / `NA`）及告警 `CAUTION_ID_FACTOR_CAM_LENS_BREATHING_COMP_NOT_SUPPORT_MSG`。
   - **实测事实（对 [Wave 41](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave41-auto-slow-shutter-6locks-hdmi-reccontrol-tcout-4chaudio-breathing-comp-intel/README.md) 的关键补全与 Catalyst 纠偏）**：
     - **真实禁用边界**：不仅在 Still 静态照片、`S&Q` `240fps/200fps` 与 HDMI 16-bit `RAW Output`（机内呼吸补偿**不应用于外录 RAW 输出**）中失效，Sony 官方规格与固件说明同时明确排除 **普通视频 `119.88p / 100p`（`120p`）** 与 **`S&Q` `120fps / 100fps`**；在 `< 100/120fps` 的 `S&Q` 帧率下 FX3 仍可启用（与 FX6 形成鲜明对照），同时依赖清晰影像缩放式电子裁切（开启时视角与画质略微变化），且在 `SEL100F28GM` 微距环 `0.57m–1.0m` 档、增距镜（`SEL14TC`/`SEL20TC`）、非兼容第三方镜头及 `Clear Image Zoom` / 数字变焦 / `Auto Framing` 耦合下受限或失效。
     - **Catalyst 常见误区纠偏（`support.d-imaging.sony.co.jp`）**：**`Catalyst Browse` 不支持镜头呼吸补偿**；基于元数据的后期呼吸补偿是 **付费版 `Catalyst Prepare` / `Catalyst Prepare Plugin` 的独占功能**，且拍摄前机内 **`[Distortion Comp.]` 必须设为 `[Auto]`**。
   - **实测事实（`ILME-FX3` vs `ILME-FX6 Ver. 6.01`）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18` p.117 + `FX6 appFw.so` `BKID_APP_SETTING_LENS_COMP_BREATHING`）位于 `Technical > Lens > Breathing Compensation`（`Auto` / `Off`），**强制锁定 `Off` 的条件更严格（3 项）**：① `Distortion Comp. = Off`；② `S&Q Motion > Setting = On`（**全部 `S&Q` 帧率一律禁用**，不同于 FX3 仅在 `>=100/120fps` 禁用）；③ `Rec Format > Codec` 含 `RAW`（`RAW`、`RAW & XAVC-I`、`RAW(HDMI)`、`RAW(HDMI) & XAVC-I`）。

2. **子系统 2（电影 `[File Settings]`、`[Cam ID + Reel#]` / `37` 字符标题、`SDHC` `4 GB` 分割与 Tier-0 `Slot 1` 边界）**：
   - **实测事实（FX3 全量规则与日期格式差异）**：`Shooting -> [File] -> [File Settings]`（`_f 0x7367`/`0x61bc`）**全部子项均抗 `[Camera Settings Reset]`**（`Not available`，仅 `[Initialize]` 复位）。
     - `[File Number]`：`Series`（默认，跨 `Slot 1`/`Slot 2` 换卡连续递增）/ `Reset`，外加 `[Series Counter Reset]`（`_f 0x6a52`：若目录内已有文件，则设为 `max + 1`）。
     - `[File Name Format]`：`Standard`（默认，`C0001`）、`Cam ID + Reel#`（`Ver. 3.00+`，强制要求 `SDXC` / `CFexpress Type A`）、`Title`、`Date + Title`、`Title + Date`。使用 **`SDHC`（`FAT32` `<=32 GB`）卡时，`[File Name Format]` 强制锁死为 `[Standard]`**（`base 0xe8f8`/`0xe94a`），长时 XAVC S 录制按 **`4 GB`** 自动分割文件，且无法与 `exFAT` 卡进行 `[Simult. Recording]` 双卡同录。
     - **`[Cam ID + Reel#]` 模版与溢出规律（`_f 0x6fc6` / `0x7070`）**：`Camera ID`（`A..Z`，修改会重置 `Reel Number`）+ `Reel Number`（`001..999`，执行 `File Number = Reset` **不会**重置 Reel#）+ `Camera Position`（`C`/`L`/`R`，占文件名序号首字符；当序号达到 `999` 时**仅输出文件名中的位置字符顺延递增**如 `C999 -> D001`，菜单设定值本身保持不变）+ `File Number`（`001..999`）+ `_` + **`YYMMDD`** + 2 位随机字符（如 `A001C001_230101AB`）。对比 `Date + Title` / `Title + Date`（`_f 0x6e91`/`0x7515`）采用 **`YYYYMMDD`** 8 位日期格式。
     - **`[Title Name Settings]`**：上限 **`37` 字符**（`A-Z`、`a-z`、`0-9` 及 `. - _ @ ! # $ % + = ^ ~ ( ) , ; [ ]`），默认 **`"C"`**，仅对设置之后的新录片段生效；电影目录路径（`PRIVATE/M4ROOT/CLIP`）不可自定义。
   - **实测事实 + 推断（`ILME-FX6` 对比与 `Slot 1` 保护）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18` p.108）位于 **`TC/Media > Clip Name Format`**（非 `Project > Clip Naming`），`Auto Naming` 仅提供 **`Cam ID + Reel#`** 与 **`Title`** 两档，`Title Prefix` 支持 **`4..46` 字符**（默认 **`nnn_`**，即机身序列号末 3 位），落盘 `/XDROOT/Clip/*.MXF`（CFexpress）或 `/PRIVATE/XDROOT/Clip/*.MXF`（SDXC），并具备 **卡内片段继承**（`FX6 appFw.so` `BKID_APP_CAMID_CURRENT_{CAMERA_ID,CAMERA_POSITION,CLIP_NUMBER,REEL_NUMBER}{0,1}`，及由 `DIADEM_PRO` 广播基线继承的 `HAND_OVER` 符号）。在 FX3 台架上，`BKID_APP_update_required_xavcs_file_name_reel_number`（`OFF`/`ON`/`RUNNING`/`UNSETTLED`）及序号写卡均需在 `Slot 1` 只读保险库下执行 fail-closed `EROFS (errno 30)` 拦截。

3. **子系统 3（`[Copyright Info]` `46` 字符、`[Write Serial Number]` 活跃态实证、`Round 57` Reset 勘误与 `CAMSET` 隔离）**：
   - **实测事实（对 [Round 57](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu/README.md) 的关键勘误）**：
     - [Round 57](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu/README.md)（`r57c` / `write_copyright_camreset_off_ok=1`）曾误判执行 `[Camera Settings Reset]` 会将 `[Write Copyright Info]` 开关复位为 `Off`。经直接核对 Sony 官方 `ilc/2210` *List of default setting values*：**`[Copyright Info]` 全部 4 项（`Write Copyright Info` 默认 `Off`、`Set Photographer` 默认 `―`、`Set Copyright` 默认 `―`、`Disp. Copyright Info` 默认 `―`）以及 `[Write Serial Number]`（默认 `Off`）均明确标注 `Resettable using [Camera Settings Reset]: Not available`**——即 `[Write Copyright Info]` 开关**同样抗 `[Camera Settings Reset]`**，唯有 `[Initialize]` 会将其复位并清空 PII 字符串！
   - **实测事实（`[Write Serial Number]` 在 `Ver. 7.02` 上完全活跃且扩域至 Still + Movie）**：`ilc/2210` 与 `FX3 appFw.so` 实证 `MENU -> (Shooting) -> [File] -> [Write Serial Number]` 在 `Ver. 2.00..7.02` 已由初版的 Still-only（`BKID_APP_setting_still_write_serial_number` / `_f 0x792c`）扩展并替换为活跃的 **Still + Movie 全域开关** **`BKID_APP_setting_write_serial_number_still_movie`**（`_f 0x6704`/`0x640c`/`0x7953`：*"when shooting."*），默认 `Off`、可设为 `On`。
   - **实测事实（`[Save/Load Settings]` `CAMSET*.DAT` 排除边界与 FX6 对比）**：官方 `ilc/2210` *Save/Load Settings* 明确将 **`Copyright Info` 列为不可保存到 `CAMSET*.DAT` 的参数**（与 `IPTC Information`、`Face Memory`、`Custom WB 1..3`、`External Flash Set.` 及网络凭证同组排除）；而 **`Write Serial Number`（仅 `On`/`Off` 开关，不含硬件序列号本身）未被列入排除表**。对比 `ILME-FX6 Ver. 6.01` 无消费级 EXIF `[Copyright Info]` 菜单（`FX6 appFw.so` 仅活跃追踪*镜头*序列号 `CURRENT/PRESET_LENS_SERIAL_NUMBER0..5`，机身序列号末 3 位用作 `Title Prefix` 默认 `nnn_`）。

4. **子系统 4（`[Auto Power OFF Temp.]`、9 条件 `[Power Save Start Time]`、休眠 `[Power Save by Monitor]` 与 `[NTSC/PAL Selector]` 重启/格式化风险）**：
   - **实测事实（`[Power Setting Option]` 活跃双项与休眠 1 项）**：`Setup -> [Power Setting Option]` 在 `ILME-FX3 Ver. 7.02` **仅暴露两项**，且**全部抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 复位）：
     1. **`[Power Save Start Time]`**（`BKID_APP_setting_start_power_saving`）：`Off` / `30 Min` / **`5 Min`（默认）** / `2 Min` / `1 Min` / `10 Sec`（ELF 中的 `20SEC`/`NO_LIMIT` 与 `_f.uxc` 中的 `30 sec`/`60 min`/`240 min` 属跨机型休眠档位）。严格受 Sony 官方 **9 类自动旁路条件**控制（USB 供电、幻灯片播放、FTP 传输、视频录制中、连接 PC、连接 TV/HDMI、`[IR Remote Ctrl] = On`、`[Bluetooth Rmt Ctrl] = On`、流媒体传输或上传 Creators' Cloud）。
     2. **`[Auto Power OFF Temp.]`**（`BKID_APP_setting_auto_pwr_off_temp`）：**`Standard`（默认）** / **`High`**（`_g 0x61a9` 明确提示仅建议三脚架固定使用、非手持）。
     3. **`[Power Save by Monitor]`**：在 `ILME-FX3 Ver. 7.02` 上**完全休眠未暴露**（无 EVF 眼感应器且 `ilc/2210` 不含该项；`BKID_APP_setting_monitor_power_linkage` / `_f 0x783f`/`0x6db5`/`0x6db6`/`0x60a8`/`0x6b2e` 为共享 `BIONZ XR` 混合机/FX2 代码遗留）。
   - **实测事实 + 推断（`[NTSC/PAL Selector]` 重启、代际演进与 `Slot 1` 格式化核弹防护）**：
     - `Setup -> [Area/Date] -> [NTSC/PAL Selector]`（`BKID_APP_setting_ntsc_pal_selector`）**抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 还原），切换即触发**自动重启**（`base 0xe5c1`），非出厂制式开机显示 **`Running on NTSC.`**（`base 0xe77a`）或 **`Running on PAL.`**（`base 0xe0b6`）。
     - 实证揭示了 `base.uxc` 与 `_g.uxc` 中的**双代消息共存**：现代 BIONZ XR（FX3 无 AVCHD）切换 NTSC/PAL 后通常不再对 XAVC 卡强制弹窗抹盘，而是以 `_g 0x61ca`/`0x644e`（+ `base 0xe379`/`0xe441`）**禁止回放异制式录像**；但 `base.uxc` **依然内嵌历史/特定模式格式化弹窗字串**（`base 0xe1e6`, `0xe373`, `0xe51a`, `0xe595`, `0xe9f6`：*"Recording is unavailable in this movie because format is set to NTSC/PAL. Format? Slot 1"* / *"All data will be deleted... Format?"*），且索尼机内格式化会发送 SD-Erase/TRIM，一旦误确认将永久摧毁 `Slot 1` Tier-0 保险库，因此台架必须硬执行 `Slot 1` **`EROFS (errno 30)`** 拦截。对比 `ILME-FX6 Ver. 6.01` 通过 `Project > Rec Format > Frequency`（`59.94/50/29.97/25/24/23.98`）切换并重启，**无消费级 NTSC/PAL 格式化提示**（`fx6_2 0x4000` `NTSC/PAL Area Mismatch` 与 `0x426d` `Country` 为遗留/PXW 字串）。

---

## 1. 子系统 1：`[Breathing Comp.]`（`Ver. 3.00+..7.02`）光学裁切、镜头白名单与 HFR/RAW/S&Q 互锁矩阵

### 1.1 `ILME-FX3 Ver. 7.02` 菜单规格、`Reset` 反对称性与 ELF 门控链（`实测事实`）

1. **菜单路径、版本起点与组内 Reset 分化（`实测事实`）**：
   - 路径：`MENU -> (Shooting) -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`（`_f 0x73ea` / `0x659d` / `0x616b`，`BKID_APP_setting_lens_comp_breathing`）。
   - 版本要求：**系统软件 `Ver. 3.00` 及以上**（`Ver. 3.00` 首次引入，延续至 `Ver. 7.02` 及 `ILME-FX3A`）。
   - 选项与默认值：**`Off`（出厂默认） / `On`**。
   - **关键 Reset 反对称性（`ilc/2210` *List of default setting values*）**：在同一 `[Lens Compensation]` 子菜单中，前 3 项（`Shading Comp.`、`Chromatic Aberration Comp.`、`Distortion Comp.`）均标注 **`Resettable using [Camera Settings Reset]: Not available`**，唯独 **`[Breathing Comp.]` 标注 `Can be reset`**（即会被 `[Camera Settings Reset]` 复位为 `Off`）。
2. **`FX3 appFw.so` 状态机与镜头通讯门控符号（`实测事实`）**：
   - 备份键：`BKID_APP_setting_lens_comp_breathing` 与 `BKID_APP_MR_setting_lens_comp_breathing`（支持 `MR` 记忆召回）。
   - 镜头校验消息：`INFRA_NOTIFY_BREATHING_CORRECTION_LENS_TYPE` -> `NID_BREATHING_CORRECTION_LENS_TYPE` -> `VAL_breathing_correction_lens_type_BREATHING_CORRECTION_LENS_TYPE_{SUPPORT, NOT_SUPPORT, NA}`，耦合条件 `PRM_HAITA_breathing_correction_lens_type_lens_information`（E-mount 电子镜头信息类型校验）与不兼容告警 `CAUTION_ID_FACTOR_CAM_LENS_BREATHING_COMP_NOT_SUPPORT_MSG`。
   - 曝光模式互锁：`PRM_HAITA_setting_lens_comp_breathing_exposure_mode` 绑定 `EXPOSURE_MODE_MOVIE`（仅电影模式生效，静态摄影不执行呼吸补偿），底层下发接口为 `PID_SET_BREATHING_CORRECTION` / `sequence_set_breathing_compensation`。

### 1.2 光学裁切原理、镜头兼容边界与互锁矩阵（含对 [Wave 41](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave41-auto-slow-shutter-6locks-hdmi-reccontrol-tcout-4chaudio-breathing-comp-intel/README.md) 的精准补全与 Catalyst 纠偏）

> [!IMPORTANT]
> **对 [Wave 41](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave41-auto-slow-shutter-6locks-hdmi-reccontrol-tcout-4chaudio-breathing-comp-intel/README.md) §3.2 与常见 Catalyst 误区的两项关键修正（`实测事实`）**：
> 1. **高帧率禁用阈值是 `120p/100p` 起跳（非仅 `240fps/200fps`）**：Sony 官方 `ILME-FX3` 固件发布说明与规格脚注明确指出：`[Breathing Comp.]` 在 **普通电影 `119.88p / 100p`（`120p`）** 与 **`S&Q` `120fps / 100fps`（及 `240fps / 200fps`）** 下均**不可用**；但在 `S&Q` 低于 `100/120fps` 的档位下 FX3 仍可生效（而 FX6 则禁用全部 S&Q）。
> 2. **`Catalyst Browse` 不支持呼吸补偿，且机内 `[Distortion Comp.]` 决定后期元数据可用性**：根据 `support.d-imaging.sony.co.jp` 官方兼容性矩阵，当机内关闭机内实时呼吸补偿时，随视频录制的呼吸元数据仅能由付费版 **`Catalyst Prepare` / `Catalyst Prepare Plugin`** 读取并执行后期呼吸补偿（**免费版 `Catalyst Browse` 不支持该功能**），且拍摄前必须在机内将 **`[Distortion Comp.]` 设为 `[Auto]`**。

| 约束 / 耦合维度 | `ILME-FX3 Ver. 7.02` 真实行为（`ilc/2210` + `support.d-imaging.sony.co.jp`） | `ILME-FX6 Ver. 6.01` 真实行为（`5-024-458-18` p.117 + `FX6 appFw.so`） |
| :--- | :--- | :--- |
| **菜单路径与默认值** | `Shooting -> [Image Quality/Rec] -> [Lens Compensation] -> [Breathing Comp.]`：`On` / **`Off`（默认）**；**可被 `[Camera Settings Reset]` 复位** | `Technical > Lens > Breathing Compensation`：**`Auto` / `Off`**（`BKID_APP_SETTING_LENS_COMP_BREATHING`，随 `All File` 保存） |
| **光学裁切与画质影响** | 启用 Sony 清晰影像缩放技术执行轻微电子裁切以锁定视角（开启后视角变窄、画质略微变化；视镜头而定未必 100% 消除） | 同样采用电子裁切传感器外缘以保持视角恒定 |
| **兼容 E-Mount 镜头门控** | **仅限 Sony 官方呼吸补偿兼容 E 卡口镜头**（如 `SEL11F18`、`SEL14F18GM`、`SEL15F14G`、`SEL16F18G`、`SEL20F18G`、`SEL24F14GM`、`SEL24F28G`、`SEL35F14GM`、`SEL35F18F`、`SEL40F25G`、`SEL50F12GM`、`SEL50F14GM`、`SEL50F14Z`、`SEL50F25G`、`SEL85F14GM`、`SEL85F14GM2`、`SEL85F18`、`SEL100F28GM`、`SEL135F18GM`、`SEL1224G`、`SEL1635GM`、`SELC1635G`、`SEL2470GM`、`SEL24105G` 等；非兼容镜头/第三方/机械转接环返回 `NOT_SUPPORT`/`NA`）；**特例**：`SEL100F28GM` 微距环置于 `0.57m–1.0m` 或加装增距镜（`SEL14TC`/`SEL20TC`）时不可用 | 同源 Sony E 卡口兼容镜头库（`https://www.sony.net/dics/breathing/`，Ver. 2.00 起支持） |
| **Still / 电影 / HFR 限制** | 仅电影可用（Still 无效）；**普通视频 `119.88p / 100p` 不可用**；`S&Q` `120fps / 100fps / 240fps / 200fps` 不可用（`<100/120fps` S&Q 可用） | **全部 `S&Q Motion = On` 均强制锁定 `Off`**（`5-024-458-18` p.117 明文禁用） |
| **`RAW` 输出 / 录制锁死** | **外录 HDMI 16-bit RAW（`4264×2408`）输出信号不应用机内呼吸补偿**（仅作用于机内并行 XAVC/LCD 预览） | `Project > Rec Format > Codec` 设为 **`RAW` 或任何含 `RAW` 选项**（`RAW`、`RAW & XAVC-I`、`RAW(HDMI)`、`RAW(HDMI) & XAVC-I`）时**强制锁定 `Off`** |
| **`[Distortion Comp.]` 耦合** | 机内 `[Breathing Comp.] = On` 本身无“强制 Distortion=Auto”硬置灰；但**若要使用 `Catalyst Prepare` 后期元数据呼吸补偿，机内 `[Distortion Comp.]` 必须设为 `[Auto]`** | **`Technical > Lens > Distortion Comp. = Off` 时，机内 `Breathing Compensation` 强制锁定 `Off`**（硬性耦合） |
| **`Clear Image Zoom` 耦合与台架推论** | **实测事实**：`ilc/2210` 与 `support.d-imaging.sony.co.jp` 在 `[Lens Compensation]` 节本身未单列与 `[Clear Image Zoom]` 的显式禁止项，但两项共享清晰影像缩放插值管线且 `Clear Image Zoom` 在 `119.88p/100p` 与 `S&Q >=100/120fps` 同样禁用；`Auto Framing` / `Framing Stabilizer` 亦不兼容后期呼吸元数据补偿。**推断**：在变焦倍率为 `1.0x` 且非 HFR/RAW 时二者各自遵循缩放管线，台架若启用 `[RAW Output]` 或 `120p` 应预期 `Breathing Comp.` 旁路为未裁切原始视场。 | FX6 在 `FF` 下开启 `Clear Image Zoom` 禁用 `RAW` 与 `>60fps` S&Q（独立于呼吸补偿菜单）；呼吸补偿硬锁死条件严格为上述 3 项（`Distortion Comp.=Off`、`S&Q=On`、`Codec=RAW`） |

---

## 2. 子系统 2：电影 `[File Settings]`（`[Cam ID + Reel#]` / `37` 字符标题）与 `SDHC` `4 GB` 分割 vs `exFAT` Tier-0 `Slot 1` 边界

### 2.1 `ILME-FX3 Ver. 7.02` 电影 `[File Settings]` 完整真值表与日期格式差异（`实测事实`）

1. **菜单路径与 Reset 持久性（`实测事实`）**：
   - 路径：`MENU -> (Shooting) -> [File] -> [File Settings]`（`_f 0x7367` `'\ue660File Settings'` / `_f 0x61bc` `'File Settings'`）。
   - **全部子项均抗 `[Camera Settings Reset]`**：在 `ilc/2210` *List of default setting values* 中，`[File Number]`、`[File Name Format]` 与 `[Title Name Settings]` 均标注 **`Not available`**（仅 **`[Initialize]`** 还原出厂默认值）。
   - 注意与静态照片 `[File/Folder Settings]`（3 字符 `DSC` 前缀 + `100MSDCF` 可选日期文件夹）严格分离：电影存储路径 **`PRIVATE/M4ROOT/CLIP`** 在 FX3 上固定不可改名，设置更改仅作用于**之后新录制的电影片段**。

| 子菜单项 | `ILME-FX3 Ver. 7.02` 可选值与出厂默认（`ilc/2210`） | `[Camera Settings Reset]` | 精确规则与 ELF / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[File Number]`** | **`Series`**（**默认**） / `Reset` | **Not available** | `Series`（`base 0xe8c5`）：换卡时文件序号不归零，且在 **Slot 1 与 Slot 2 之间连续递增**；`Reset`：更换存储卡后编号归零；`BKID_APP_setting_xavcs_file_number` |
| **`[Series Counter Reset]`** | 执行动作（确认弹窗 `_f 0x6250`） | — | 复位 `Series` 连续计数器；**若当前录制目录内已存在文件，则新序号设为“目录内最大编号 `+ 1`”**（`_f 0x7a28` / `_f 0x6a52`） |
| **`[File Name Format]`** | **`Standard`**（**默认**，`C0001`）\u003cbr\u003e`Cam ID + Reel#`（`Ver. 3.00+`）\u003cbr\u003e`Title` / `Date + Title` / `Title + Date` | **Not available** | `Standard` 输出 `C0001.MP4`；`Date + Title`（`_f 0x620e`/`0x6e06`/`0x6e91`）与 `Title + Date`（`_f 0x6174`/`0x61cf`/`0x7515`）使用 **8 位 `YYYYMMDD`** 日期；**`SDHC` 卡下仅支持 `Standard`**（`_f 0x7821` / `_f 0x78f5`） |
| **`[Cam ID + Reel# Settings]`** | • `Camera ID`：`A`–`Z`（`_f 0x72f1`）\u003cbr\u003e• `Reel Number`：`001`–`999`（`_f 0x726a`）\u003cbr\u003e• `Camera Position`：`C` / `L` / `R`（`_f 0x68c4`） | **Not available** | 输出模版为 **`Camera ID + Reel#(3位) + Position(1位) + File#(3位) + _ + YYMMDD + 2位随机串`**（例：`A001C001_230101AB`，**6 位 `YYMMDD` 日期**，见 `_f 0x6fc6`）。\u003cbr\u003e① 更改 `Camera ID` 会重置 `Reel Number`，但 `[File Number] = Reset` **不会**重置 `Reel Number`；\u003cbr\u003e② `Camera Position` 作为文件编号首字符（`_f 0x7070`），当序号到达 `999` 时**仅输出文件名位置字母自动顺延**（`C999 -> D001`），菜单中的 `Camera Position` 设定值自身不变；\u003cbr\u003e③ `FX3 appFw.so`：`BKID_APP_setting_xavc_s_file_name_camid_camera_{id,position}`、`BKID_APP_setting_xavcs_file_name_reel_number`、`MODEL_MOVIE_REC_REEL_NUMBER_PLUS_1_NOTIFY`、`BKID_APP_update_required_xavcs_file_name_reel_number`、`BKID_APP_recorded_after_camid_reel_setting` |
| **`[Title Name Settings]`** | 最大 **`37` 字符**，默认 **`"C"`**（`Ver. 3.00+`） | **Not available** | 仅对 `Title` / `Date + Title` / `Title + Date` 生效；允许字母 `A-Z`/`a-z`、数字 `0-9` 与符号 `. - _ @ ! # $ % + = ^ ~ ( ) , ; [ ]`；`_f 0x6c14` / `SOFTWARE_KEYBOARD_TITLE_PREFIX` / `EVENT_REMOTE_SET_XAVC_S_FILE_NAME_TITLE_PREFIX` |

### 2.2 `SDHC`（`FAT32`）`4 GB` 文件分割 vs `exFAT`（`SDXC`/`CFexpress`）及 Tier-0 `Slot 1` 边界

1. **`SDHC` vs `SDXC / CFexpress Type A` 实机门槛（`实测事实`）**：
   - **`SDHC`（`<= 32 GB`, `FAT32`）两项强制限制**：
     1. **锁死 `[File Name Format] = [Standard]`**：在 `SDHC` 卡上无法使用 `[Cam ID + Reel#]`、`[Title]`、`[Date + Title]` 或 `[Title + Date]`，强行选择会触发 UXC 错误提示 `base 0xe8f8` / `0xe94a` / `0xe1d8` / `0xe255` / `0xe257` / `0xe2f1` / `0xe2f2`（*"The current memory card does not support the file name format. Use an SDXC or CFexpress memory card."*）。
     2. **`4 GB` 自动分割与双卡混插禁令**：长时录制 `XAVC S` 视频达到 `4 GB` 上限时自动分割为多个文件；且 **`[Simult. Recording]`（双卡同步录制）严禁 `exFAT`（SDXC/CFexpress）与 `FAT32`（SDHC）混用**（两卡必须同文件系统，详见 `ilc/2210` *Memory cards that can be used*）。
2. **`Slot 1` Tier-0 只读保险库 `EROFS=30` 推论（`推断`）**：
   - 当录像触发落盘、Reel/Series 计数推进时，固件状态机通过 `BKID_APP_update_required_xavcs_file_name_reel_number`（`OFF` / `ON` / `RUNNING` / `UNSETTLED`）及 `BKID_APP_recorded_after_camid_reel_setting`（`DONE` / `NOT_YET`）更新卡内 `M4ROOT` 与卷标/索引；同时 `Save/Load Settings` 亦固定读写 `Slot 1`。当台架将恢复镜像（Tier-0 Vault）挂载于 `Slot 1` 时，任何因新录片段、`Series Counter Reset` 或 `Cam ID + Reel#` 状态刷新引发的 `Slot 1` 写入必须由只读守卫 fail-closed 返回 **`EROFS (errno 30)`**，严禁污染恢复槽位。

### 2.3 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 片段命名系统对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210` + `FX3 appFw.so`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` p.108 + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **菜单路径** | `Shooting -> [File] -> [File Settings]` | **`TC/Media > Clip Name Format`**（非 `Project > Clip Naming`！） |
| **命名模式选项** | **5 种**：`Standard` / `Cam ID + Reel#` / `Title` / `Date + Title` / `Title + Date` | **2 种（`Auto Naming`）**：`Cam ID + Reel#` / `Title`（另有 `Planning Metadata` 等为 `fx6_2.uxc` 遗留/PXW 休眠字串，未在 `5-024-458-18` 暴露） |
| **标题字符上限与默认值** | `Title Name Settings`：**`<= 37` 字符**，默认 **`"C"`** | `Title Prefix`：**`4..46` 字符**，默认 **`nnn_`**（机身序列号末 `3` 位），后缀 `Number Set` `0001..9999` |
| **卡内片名继承机制** | 依赖机内计数器（`Series` 跨双卡连续递增，`Cam ID` 修改重置 `Reel#`） | **硬件级卡内继承**：若插入的卡上已存在 `Cam ID + Reel#` 片段，自动继承末条片段的 `Cam ID / Reel# / Pos / Clip#`（`FX6 appFw.so` `BKID_APP_CAMID_CURRENT_{CAMERA_ID,CAMERA_POSITION,CLIP_NUMBER,REEL_NUMBER}{0,1}` 及 `DIADEM_PRO` 交接符号） |
| **存储目录结构** | `PRIVATE/M4ROOT/CLIP/*.MP4`（固定路径） | `/XDROOT/Clip/*.MXF`（CFexpress Type A）或 `/PRIVATE/XDROOT/Clip/*.MXF`（SDXC） |

---

## 3. 子系统 3：`[Copyright Info]`（`46` 字符）、`[Write Serial Number]` 活跃域与 `CAMSET` 隐私隔离

### 3.1 `ILME-FX3 Ver. 7.02` `[Copyright Info]` 与 `[Write Serial Number]` 真值表（`实测事实`）

> [!WARNING]
> **对 [Round 57](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu/README.md) 的显式勘误（`ilc/2210` *List of default setting values* 实证）**：
> [Round 57](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-17-round57-milestone-realhw-release-wo-card-audio-meter-copyright-qemu/README.md)（`r57c`）曾测试/假设执行 `[Camera Settings Reset]` 会将 `[Write Copyright Info]` 复位为 `Off`（`write_copyright_camreset_off_ok=1`），仅保留摄影师与版权字串。
> **直接核对官方 `ilc/2210` *List of default setting values* 证实：`[Write Copyright Info]`、`[Set Photographer]`、`[Set Copyright]`、`[Disp. Copyright Info]` 以及 `[Write Serial Number]` 五项的 `Resettable using [Camera Settings Reset]` 列全部明确标注为 `Not available`**！即 `[Write Copyright Info]` 开关**同样抗 `[Camera Settings Reset]`**，只有执行 **`[Initialize]`** 才会将该开关复位为 `Off` 并清空姓名/版权字串。

| 菜单项（`Shooting -> [File]`） | 选项 / 长度上限 / 默认值（`ilc/2210`） | `[Camera Settings Reset]` | `CAMSET*.DAT` 导出？ | 写入范围与 ELF / UXC 实证（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **`[Copyright Info] -> [Write Copyright Info]`** | **`Off`**（默认） / `On` | **Not available** | **否（明确排除）** | `_f 0x7ae4` / `0x788b` / `0x65a0`；`BKID_APP_setting_still_write_copyright_infomation`；仅写入 **Still 静态照片 EXIF** |
| **`[Copyright Info] -> [Set Photographer]`** | **`<= 46` ASCII 字母/数字/符号**（默认 `―`） | **Not available** | **否（明确排除）** | `_f 0x7172` / `0x78d2` / `_g 0x62d4`；`BKID_APP_photographer_name` |
| **`[Copyright Info] -> [Set Copyright]`** | **`<= 46` ASCII 字母/数字/符号**（默认 `―`） | **Not available** | **否（明确排除）** | `_f 0x612b` / `0x6846` / `_g 0x6370`；`BKID_APP_copyright_name` / `SOFTWARE_KEYBOARD_COPYRIGHT_NAME` |
| **`[Copyright Info] -> [Disp. Copyright Info]`** | 查看当前已设定的摄影师/版权字符串 | **Not available** | **否（明确排除）** | `_f 0x611b` / `0x79b2` |
| **`[Write Serial Number]`** | **`Off`**（默认） / **`On`**（**`Ver. 7.02` 完全活跃！**） | **Not available** | **未列入排除表** *(仅存布尔开关，不含机身序列号字符串)* | `Ver. 2.00..7.02` 已由初版 Still-only（`BKID_APP_setting_still_write_serial_number` / `_f 0x792c`）升级替换为 **`BKID_APP_setting_write_serial_number_still_movie`**（`_f 0x6704` / `0x640c` / `0x7953`：*"Writes the device's serial number when shooting."*），覆盖 **Still + Movie** |

### 3.2 `CAMSET*.DAT` 排除清单、出借隐私规范与 `FX6` 序列号模型对比（`实测事实` + `推断`）

1. **`[Save/Load Settings]`（`CAMSET*.DAT`）明确排除 `Copyright Info`（`实测事实`）**：
   - 根据 `ilc/2210` *Save/Load Settings* 官方列表（及 `libSaveLoadSettings.so` `18,760 B`, SHA-256 `07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7`、`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT` 路径格式）：
   - **不可写入 `CAMSET*.DAT` 的参数全表**：`(Shooting)` `IPTC Information`、**`Copyright Info`**；`(Exposure/Color)` `External Flash Set.`、`White Balance: Custom 1/2/3`；`(Focus)` `Face Memory`；`(Network)` `FTP Transfer Func.`、`Network Streaming`、`Cloud Connection`、`WPS Push`、`Access Point Set.`、`Wi-Fi Frequency Band`、`IP Address Setting`、`Edit Device Name`、`Import Root Certificate`、`Access Authen.`。
   - **安全设计含义（`实测事实` + `推断`）**：`Copyright Info` 被排除出 `CAMSET*.DAT`，可防止团队共享或从 C3 Portal（最多 `60` 组云端配置 / `Slot 1` 卡内最多 `10` 组）克隆机内预设时意外扩散个人摄影师姓名/版权 PII；同时正因为 `[Camera Settings Reset]` **无法**清除 `Copyright Info` 与 `[Write Serial Number]`，Sony 官方在 *Copyright Info* 页面明文警告：**将相机出借或转交他人前必须手动删除 `[Set Photographer]`/`[Set Copyright]` 或执行 `[Initialize]`**。在干净台架上，`[Write Copyright Info]` 与 `[Write Serial Number]` 应保持默认 `Off`，确保测试样本零 PII / 零真实机身序列号泄漏。
2. **`ILME-FX3` vs `ILME-FX6 Ver. 6.01` 对比（`实测事实`）**：
   - `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 appFw.so`）**没有**消费级静态照片 EXIF `[Copyright Info]` 菜单（`FX6 appFw.so` 中零星 `EVENT_REMOTE_COPYRIGHT_*` 属 Alpha 远程控制接口遗留且无 UXC 菜单呈现）。
   - FX6 围绕“序列号”暴露的是两套完全不同的工程机制：① **镜头预设序列号追踪**（`BKID_APP_CURRENT_LENS_SERIAL_NUMBER`、`BKID_APP_PRESET_LENS_SERIAL_NUMBER0..5`）；② **电影片段默认前缀 `Title Prefix = nnn_`**（自动填入机身序列号末 3 位，p.108）。`FX6 string_english_2.uxc` 中的 `0x496c` `'On(Serial Number)'` 属于多机型企业/C3 词条，在 `5-024-458-18` 常规用户菜单中未单列开关。

---

## 4. 子系统 4：`[Auto Power OFF Temp.]`、9 条件 `[Power Save Start Time]`、休眠 `[Power Save by Monitor]` 与 `[NTSC/PAL Selector]` 重启/格式化风险

### 4.1 `ILME-FX3 Ver. 7.02` `[Power Setting Option]` 活跃双项、9 条件旁路与休眠项实证（`实测事实`）

1. **菜单结构与 Reset 持久化（`实测事实`）**：
   - 路径：`MENU -> (Setup) -> [Power Setting Option]`。在 `ILME-FX3 Ver. 7.02`（`ilc/2210`）中，该页**严格仅包含以下 2 项活跃设置**，且因位于 `(Setup)` 树下，**全部抗 `[Camera Settings Reset]`**（`Not available`，仅 **`[Initialize]`** 复位）：

| 菜单项 | `FX3 Ver. 7.02` 真实选项与默认（`ilc/2210`） | `[Camera Settings Reset]` | ELF / UXC 实证与跨机型休眠符号（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Power Save Start Time]`** | `Off` / `30 Min` / **`5 Min`（出厂默认）** / `2 Min` / `1 Min` / `10 Sec` | **Not available** | `_f 0x69b0`；`BKID_APP_setting_start_power_saving`；`VAL_setting_start_power_saving_START_POWER_SAVING_{OFF, 10SEC, 1MIN, 2MIN, 5MIN, 30MIN}`。\u003cbr\u003e*注：ELF 中同时编译的 `20SEC` / `NO_LIMIT` 及 `_f.uxc` 中的 `30 sec` / `60 min` / `240 min` 在 FX3 上为休眠档位，不向用户暴露* |
| **`[Auto Power OFF Temp.]`** | **`Standard`（出厂默认）** / **`High`** | **Not available** | `_f 0x70f1`；`BKID_APP_setting_auto_pwr_off_temp`；`VAL_setting_auto_pwr_off_temp_AUTO_PWR_OFF_TEMP_{STANDARD, HIGH}`。\u003cbr\u003e`_g 0x61a9` 明确警示：`High` 仅用于**三脚架固定拍摄**（非手持长时间握持），以提高热关机阈值、延长录制时长 |
| **`[Power Save by Monitor]`**\u003cbr\u003e*(休眠项)* | **在 `ILME-FX3 Ver. 7.02` 菜单中不存在（完全休眠）** | — | `FX3` 无 EVF 眼感应器且 `ilc/2210` 不含该项；`BKID_APP_setting_monitor_power_linkage` 及 `_f 0x783f` / `0x6db5`（`Both Linked`）/ `0x6db6`（`Open: Return`）/ `0x60a8`（`Close: Power Save`）/ `0x6b2e`（`Does Not Link`）属同代 `BIONZ XR` 混合机型（如 `ILCE-7M4` / `ZV-E1` / `ILME-FX2`）共享代码遗留（与 [Wave 46](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-17-global-sony-wave46-power-save-by-monitor-language-volume-delete-confirm-intel/README.md) 结论一致） |

2. **`[Power Save Start Time]` 官方精确 9 大自动旁路（Deactivation）条件（`实测事实`，`ilc/2210` *Power Save Start Time* + [Wave 31](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h391-global-sony-wave64-milestone-breathing-camid-reel-copyright-46ch-powersave-ntscpal-intel/reports/2026-11-15-global-sony-wave31-steadyshot-active-raw-hfr-ciz-center-af-powersave-9cond-temp-high-intel/README.md)）**：
   1. 通过 **USB 线从电脑或其他设备供电**时；
   2. **幻灯片播放（Slideshow）**期间；
   3. **FTP 传输**期间；
   4. **电影录制（Recording movies）**期间；
   5. **连接至电脑（PC）**时；
   6. **连接至电视/监视器（TV / HDMI）**时；
   7. **`[IR Remote Ctrl]` = `[On]`** 时；
   8. **`[Bluetooth Rmt Ctrl]` = `[On]`** 时；
   9. **网络流媒体（Streaming）或向 Creators' Cloud 上传影像**期间。
   - **台架推论（`推断`）**：在无 USB 供电、无 HDMI 外接、纯 `NP-FZ100` 电池离线直连台架执行长耗时只读转储或自检时，因 9 项旁路条件均未触发，默认 `5 Min` 将按时进入休眠；此时必须在脚本前置将 `[Power Save Start Time]` 设回 `[Off]` 或 `[30 Min]`。

### 4.2 `[NTSC/PAL Selector]` 重启行为、双代 UXC 存储卡格式化提示剖析与 `FX6` 对比

1. **`ILME-FX3 Ver. 7.02` `[NTSC/PAL Selector]` 实测机制（`实测事实`）**：
   - **路径与 Reset 持久性**：`MENU -> (Setup) -> [Area/Date] -> [NTSC/PAL Selector]`（`_f 0x6b6f`、`BKID_APP_setting_ntsc_pal_selector`），位于 `(Setup)` 下，**抗 `[Camera Settings Reset]`**（`Not available`，仅 `[Initialize]` 恢复出厂区域制式）。
   - **自动重启与开机横幅**：每次切换 `NTSC` <-> `PAL`（以及跨 `24.00p`）均触发**自动重启**（`base 0xe5c1`：`'Change to PAL?\nReboots after change is made.'`）；当处于非出厂默认制式时，每次开机均显示 **`Running on NTSC.`**（`base 0xe77a`）或 **`Running on PAL.`**（`base 0xe0b6`）。
   - **帧率与时间码门控**：`NTSC` 开放 `23.98p`、`29.97p`、`59.94p`、`119.88p`（+ `24.00p`）及 `[Time Code Format]`（`DF` / `NDF`）；`PAL` 开放 `25p`、`50p`、`100p` 并**禁用 `23.98p` 与 `DF`/`NDF` 切换**（锁定 `NDF`）；`FX3 appFw.so` 通过 `PRM_HAITA_setting_file_format_setting_ntsc_pal_selector_frame_rate_XXXk_XXXfps_availability` 与 `PRM_HAITA_streaming_mode_setting_ntsc_pal_selector` 实时门控流媒体与录制帧率表。

2. **关键解析：`base.uxc` 遗留格式化提示 vs `_g.uxc` 现代 FX3 异制式回放拦截（`实测事实` + `推断`）**：
   - **实测事实**：在 `ILME-FX3`（`BIONZ XR` 架构，已移除 `AVCHD` 编码）官方 `ilc/2210` 文档与现代 Alpha/FX3 UXC 中，切换 `[NTSC/PAL Selector]` 主要引发的是**异制式录像回放禁令**：`base 0xe379` / `0xe441`（*"Change to PAL/NTSC? Reboots after change is made. Movies recorded in NTSC/PAL cannot be played back if changed."*) 与 `_g 0x61ca` / `_g 0x644e`（*"Movies recorded while NTSC/PAL is operating cannot be played back in the current setting. Can be played back if 'NTSC/PAL Selector' is changed."*）。
   - **同时在 `string_english.uxc`（`base`）中依然实实在在驻留着 Sony 前代格式化抹盘警示串**：`base 0xe1e6` / `0xe373`（*"To record to the media card used in PAL/NTSC, it is necessary to format. Save the image beforehand."*）、`base 0xe51a` / `0xe595` / `0xe597`（*"Recording is unavailable in this movie because format is set to PAL/NTSC.\nFormat?\nSlot 1/2"*）以及 `base 0xe9f6`（*"All data will be deleted.\nCannot use the formatted memory card when set to NTSC.\nFormat?"*）。
   - **台架风险推论（`推断`）**：Sony 机内存储卡格式化会下发低级 SD-Erase / TRIM，数据不可逆丢失；即便现代 FX3 XAVC 场景下日常切制式不主动弹出 `base 0xe595` 抹盘框，只要卡内残留旧 `AVCHD`/异常数据库触发了遗留格式化提示流，误按确认将瞬间清空 `Slot 1` Tier-0 恢复保险库。因此 **Tier-0 规则必须强制隔离 NTSC 与 PAL 测试卡，并对 `Slot 1` 一切 `Format` / `AVF_INFO` / `M4ROOT` 写请求硬返 `EROFS (errno 30)`**。

3. **`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 电源与制式系统对比（`实测事实`）**：

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ilc/2210` + `FX3 appFw.so`) | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **自动休眠定时 (`Power Save Start Time`)** | 活跃：`Off` / `30 Min` / **`5 Min`（默认）** / `2 Min` / `1 Min` / `10 Sec`（9 条件自动旁路，抗 Reset） | **无消费级待机休眠菜单**（`5-024-458-18` 无 `Power Save Start Time`；仅物理 `POWER` 拨动开关与远程 `FTP Power Save` 事件；`FX6 ns1 0x31f6/0x3238/0x3341` 属网络/发射机或共享基线字串） |
| **高温自动关机阈值 (`Auto Power OFF Temp.`)** | 活跃：**`Standard`（默认）** / **`High`**（三脚架延长录制，抗 Reset） | **无此菜单选项**（广播级主动散热风道设计，无消费级 Standard/High 两档温度阈值切换） |
| **显示屏联动休眠 (`Power Save by Monitor`)** | **休眠未暴露**（无 EVF；`appFw.so` 含共享 `BIONZ XR` 符号） | **无**（FX6 采用可拆卸寻像器式 LCD，无翻转闭合休眠开关） |
| **制式 / 频率切换机制** | `Setup -> [Area/Date] -> [NTSC/PAL Selector]`（`NTSC`/`PAL` 二选一，切换后**自动重启**，开机提示 `Running on NTSC/PAL.`，抗 Reset） | **`Project > Rec Format > Frequency`**（`59.94` / `50` / `29.97` / `25` / `24` / `23.98`；按需**自动重启**，配合 `Maintenance > Clock Set` 设时区；**无消费级插卡格式化弹窗**；`FX6 ns2 0x4000/0x460f/0x426d` 为 PXW/前代遗留字串） |

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 实证覆盖范围 |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`nflasha15/lib/appFw.so`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `[Breathing Comp.]` `HAITA`/`PID_SET`、`Cam ID + Reel#` 状态机、`Write Serial Number`（Still+Movie vs Still-only）、`start_power_saving`、`auto_pwr_off_temp`、`ntsc_pal_selector`、`monitor_power_linkage` 休眠符号 |
| `FX3 libSaveLoadSettings.so` (`usr/lib/libSaveLoadSettings.so`) | `18,760` | `07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7` | `CAMSET*.DAT` 导出/加载读写桥接接口 |
| `FX3-CX95900_ALLLANG-Backup.bin` (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失 `BK4` 参数备份基线（不泄漏原始专有字节） |
| `FX6 appFw.so` (`FX6 .../lib/appFw.so`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | FX6 `SETTING_LENS_COMP_BREATHING`、`CAMID_CURRENT_*` / `DIADEM_PRO` 继承、`SETTING_TITLE_PREFIX`、镜头序列号追踪与 `SETTING_FREQUENCY_REC_FORMAT` |
| `FX3 string_english_f.uxc` / `.uxc` / `_g.uxc` | `373,820` / `165,740` / `69,600` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` / `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | FX3 `hdr_flag=15` 主包 + `base`/`_g` 英文全量对照 |
| `FX3 string_simplifiedchinese_f.uxc` / `.uxc` / `_g.uxc` | `322,652` / `149,064` / `61,296` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `_f` / `base` / `_g` 三包四语 `resid16` 精确映射 |
| `FX3 string_traditionalchinese_f.uxc` / `.uxc` / `_g.uxc` | `324,148` / `151,908` / `61,372` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文 `_f` / `base` / `_g` 三包四语 `resid16` 精确映射 |
| `FX3 string_japanese_f.uxc` / `.uxc` / `_g.uxc` | `447,840` / `208,564` / `89,428` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本语原厂 `_f` / `base` / `_g` 三包四语 `resid16` 精确映射 |
| `FX6 string_english.uxc` / `_2.uxc` | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | FX6 `Breathing Compensation`、`Cam ID + Reel#`、`Title Prefix`、`Rec Format Frequency` 及 PXW/企业休眠字串对照 |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`，只读 `_f`/`base`/`_g` 精确提取）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x73ea` / `0x659d` / `0x616b` | `Breathing Comp.` / `Corrects the focus breathing phenomenon.` / `Does not correct the focus breathing phenomenon.` | `呼吸补偿` / `校正对焦呼吸现象。` / `不校正对焦呼吸现象。` | `呼吸補償` / `修正對焦呼吸現象。` / `不要修正對焦呼吸現象。` | `ブリージング補正` / `ブリージング現象を補正します` / `ブリージング現象を補正しません` | **活跃**（可 Reset；Movie 专属；`120p/100p` & `RAW` 受限） |
| `_f` `0x61bc` / `0x7821` / `0x7a28` / `0x6a52` | `File Settings` / `File Name Format` / `Series Counter Reset` / `Resets the sequence number counter for movies...` | `文件设置` / `文件名格式` / `序号计数器重置` / `重置动态影像的序号计数器...` | `檔案設定` / `檔案名稱格式` / `序列計數器重設` / `重設影片的序號計數器...` | `ファイル設定` / `ファイル名形式` / `連番ｶｳﾝﾀｰﾘｾｯﾄ` / `動画の連番カウンターをリセットします...` | **活跃**（全部抗 Reset；`Series Counter` 目录有片则 `max+1`） |
| `_f` `0x67ae` / `0x72f1` / `0x726a` / `0x68c4` / `0x6fc6` | `Cam ID + Reel#` / `Camera ID` / `Reel Number` / `Camera Position` / `Shoots with the file name in Cam ID+Reel no.+...YYMMDD...` | `Cam ID + Reel#` / `相机ID` / `卷盘编号` / `相机位置` / `以相机ID+卷盘编号+文件编号+日期+随机字符串...YYMMDD...` | `Cam ID + Reel#` / `相機ID` / `膠捲編號` / `相機位置` / `以相機ID+膠捲編號+檔案編號+日期+隨機字串...YYMMDD...` | `Cam ID + Reel#` / `カメラID` / `リール番号` / `カメラ位置` / `カメラID+リール番号+ファイル番号+日付+ランダム文字列...YYMMDD...` | **活跃**（需 `SDXC`/`CFexpress`；`C999->D001` 文件名顺延） |
| `_f` `0x6c14` / `0x77a6` / `0x620e` / `0x6174` / `0x6e91` | `Title Name Settings` / `Title` / `Date + Title` / `Title + Date` / `...YYYYMMDD format...` | `标题名设置` / `标题` / `日期+标题` / `标题+日期` / `...YYYYMMDD格式...` | `標題名稱設定` / `標題` / `日期+標題` / `標題+日期` / `...YYYYMMDD格式...` | `タイトル名設定` / `タイトル` / `日付+タイトル` / `タイトル+日付` / `...YYYYMMDDの形式...` | **活跃**（`<=37` 字符；默认 `"C"`；抗 Reset） |
| `base` `0xe8c5` / `0xe1d8` / `0xe8f8` | `Series` / `The current memory card does not support the file name format. Use an SDXC or CFexpress memory card.` / `...Use an SDXC memory card.` | `系列` / `目前的存储卡不支持此文件名格式。使用SDXC或CFexpress存储卡。` / `...使用SDXC存储卡。` | `連續` / `目前的記憶卡不支援此檔案名稱格式。使用SDXC或CFexpress記憶卡。` / `...使用SDXC記憶卡。` | `連番` / `現在のメモリーカードはファイル名形式に対応していません SDXCまたはCFexpressのメモリーカードをご使用ください` / `...SDXCのメモリーカードをご使用ください` | **活跃**（`SDHC` `FAT32` 锁死 `Standard` 并 `4 GB` 分割） |
| `_f` `0x6d53` / `0x7ae4` / `0x7172` / `0x612b` / `0x611b` | `Copyright Info` / `Write Copyright Info` / `Set Photographer` / `Set Copyright` / `Disp. Copyright Info` | `版权信息` / `写入版权信息` / `设置摄影师姓名` / `设置版权所有者名称` / `显示版权信息` | `版權資訊` / `寫入版權資訊` / `設定拍攝人姓名` / `設定版權所有者名稱` / `顯示版權資訊` | `著作権情報` / `著作権情報書き込み` / `撮影者名設定` / `著作権者名設定` / `著作権情報表示` | **活跃**（全 4 项**均抗 Reset**；`<=46` 字符；不入 `CAMSET`） |
| `_f` `0x7058` / `0x640c` / `0x7953` / `0x6436` / `0x792c` | `Write Serial Number` / `...when shooting.` / `Writes...when shooting.` / `...when shooting still images.` / `Writes...still images.` | `写入序列号` / `设置在拍摄时是否写入本机的序列号。` / `在拍摄时写入本机的序列号。` / `...静态影像时...` / `...静态影像时写入...` | `寫入序號` / `設定拍攝時是否寫入裝置序號。` / `拍攝時寫入裝置序號。` / `...靜態影像時...` / `...靜態影像時寫入...` | `ｼﾘｱﾙ番号書き込み` / `撮影時に本機のシリアル番号を書き込むかどうかを設定します` / `撮影時に本機のシリアル番号を書き込みます` / `静止画撮影時に...` / `静止画撮影時に...書き込みます` | **`0x7058/0x640c/0x7953` 活跃**（Still+Movie）；后 2 项 Still-only 遗留 |
| `_f` `0x69b0` / `0x6244` / `0x63c2` / `base` `0xe50f` / `0xea45` | `Power Save Start Time` / `2 Min` / `30 Min` / `...10 seconds.` / `...5 minutes.` | `自动关机开始时间` / `2分钟` / `30分钟` / `...超过10秒...` / `...超过5分钟...` | `省電開始時間` / `2分鐘` / `30分鐘` / `...超過10秒...` / `...5分鐘內...` | `ﾊﾟﾜｰｾｰﾌﾞ開始時間` / `2分` / `30分` / `...10秒間つづくと...` / `...5分間つづくと...` | **活跃**（抗 Reset；`5 Min` 默认；9 条件旁路） |
| `_f` `0x70f1` / `_g` `0x612c` / `0x61a9` | `Auto Power OFF Temp.` / `...Set "Auto Power OFF Temp." to "High"?...` / `When shooting from a tripod...` | `自动关机温度` / `...设置为"高"?...` / `通过三脚架拍摄而不是握持本机拍摄时...` | `自動關閉電源溫度` / `...設定為"高"?...` / `從三腳架拍攝而不是握住本裝置拍攝時...` | `自動電源OFF温度` / `...「高」にしますか？...` / `手持ちで撮影せずに三脚などをお使いの際は...` | **活跃**（抗 Reset；`Standard` 默认 / `High` 限三脚架） |
| `_f` `0x783f` / `0x6db5` / `0x6db6` / `0x60a8` / `0x6b2e` | `Power Save by Monitor` / `Both Linked` / `Open: Return` / `Close: Power Save` / `Does Not Link` | `通过显示屏节电` / `二者均连接` / `打开: 恢复` / `关闭: 节电` / `不连接` | `依據螢幕狀態省電` / `兩者都已連結` / `打開: 返回` / `闔上: 省電` / `不連結` | `ﾓﾆﾀｰ開閉でﾊﾟﾜｰｾｰﾌﾞ` / `両方連動` / `開:ﾊﾟﾜｰｾｰﾌﾞ復帰` / `閉:ﾊﾟﾜｰｾｰﾌﾞ` / `連動しない` | **在 FX3 Ver. 7.02 上完全休眠未暴露** |
| `_f` `0x6b6f` / `base` `0xe77a` / `0xe0b6` / `0xe5c1` / `0xe379` | `NTSC/PAL Selector` / `Running on NTSC.` / `Running on PAL.` / `Change to PAL?\nReboots...` / `...Movies recorded in NTSC cannot be played back...` | `NTSC/PAL选择器` / `运行于NTSC。` / `运行于PAL。` / `更改为PAL吗？\n更改完成后重新启动。` / `...以NTSC录制的动态影像将无法播放。` | `NTSC/PAL選擇器` / `在NTSC上執行。` / `在PAL上執行。` / `變更為PAL嗎？\n變更結束後重新啟動。` / `...以NTSC錄製的影片則無法播放。` | `NTSC/PAL切換` / `NTSCで動作中` / `PALで動作中` / `PALに変更しますか?\n変更後、再起動を行います` / `...NTSCで記録した動画は再生できません` | **活跃**（抗 Reset；强制重启；非默认开机提示） |
| `base` `0xe595` / `0xe9f6` / `_g` `0x61ca` / `0x644e` | `Recording is unavailable...Format?\nSlot 1` / `All data will be deleted...Format?` / `Movies recorded while NTSC/PAL is operating cannot be played back...` | `由于格式设为NTSC...格式化吗？\n插槽1` / `所有数据都会被删除...格式化吗？` / `在当前设置下，NTSC/PAL运行状态下录制的动态影像无法播放...` | `記錄不能用於這個動態影像...格式化？\n插槽1` / `所有資料都會被刪除...要格式化嗎？` / `在當前設定下，NTSC/PAL運行狀態下錄製的影片無法播放...` | `NTSCで動作中のため...フォーマットしますか?\nスロット 1` / `すべてのデータが削除されます...よろしいですか？` / `NTSC/PALで動作中に撮影した動画は現在の設定では再生できません...` | **`_g` 活跃回放拦截**；`base` 格式化警示受 `Slot 1` `EROFS=30` 硬隔离 |
