# 全球 Sony 实机情报 Wave 53（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Lens Compensation]` 镜头补偿、`[AF Transition Speed]`/`[AF Assist]` 与 `[AF Illuminator]` 硬件实证、`[Aperture Drive in AF]`/`[Pre-AF]`/`[AF w/ Shutter]`/`[Circ. of Focus Point]`，及 `[File/Folder Settings]`/`[Rating]` Slot-1 Tier-0 保险库写危害审计）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Lens Compensation (still image/movie)* `TP1000882810.html`、*Front side* `TP1000886886.html`、*AF Illuminator* `TP1000867618.html`、*AF Assist* `TP1000887675.html`、*AF Transition Speed* `TP1000876482.html`、*AF Subj. Shift Sensitivity* `TP1000876470.html`、*Aperture Drive in AF* `TP1000883907.html`、*AF w/ Shutter* `TP1000844102.html`、*Pre-AF* `TP1000867619.html`、*Circ. of Focus Point* `TP1000883913.html`、*Focus Area Color* `TP1000884362.html`、*File/Folder Settings* `TP1000884356.html`、*Select REC Folder* `TP1000843995.html`、*Create New Folder* `TP1000843996.html`、*Rating* `TP1000882823.html`、*Rating Set(Custom Key)* `TP1000882822.html`、*List of default setting values*），Sony `ILME-FX6` Operating Instructions（`5-024-458-18`, Software Ver. 6.0），以及严格 `os.O_RDONLY` 本地 donor 二进制/字符串包交叉实证（`FX3 appFw.so`、`libInfraLensCommunicator.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so`、`FX6 string_english.uxc` / `_2.uxc`）。
- **硬件安全态势**：严格只读本地 donor 分析（`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`/偏移、ELF 符号与官方文档编号）与 **`推断`**。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[Lens Compensation]`：`Shading` / `Chromatic Aberration` / `Distortion` / `Breathing`）**：
   - **实测事实**：`ILME-FX3 Ver. 7.02` 菜单路径为 `MENU -> (Shooting) -> [Image Quality/Rec] -> [Lens Compensation]`，三个静态/通用补偿项均**仅向用户暴露 `[Auto]` 与 `[Off]` 两档**（`Shading Comp.` 默认 `Auto`，`Chromatic Aberration Comp.` 默认 `Auto`，`Distortion Comp.` 默认 `Off`，三者均不支持 `[Camera Settings Reset]` 重置，仅 `[Breathing Comp.]` `On/Off` 默认 `Off` 支持重置）。尽管 `FX3 appFw.so`、`FX6 appFw.so` 均包含 `VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW` 且 `FX3 string_*_f.uxc` `0x6c9c` 存在 `'Auto: Low'` 字符串，该档位属于与 `ILCE-6700`（`Auto / Auto: Low / Off`）及 `ILCE-7RM5`（`Auto / Low / Off`）共用 BIONZ XR 代码族产生的**休眠枚举**，在 FX3 Ver. 7.02 与 FX6 Ver. 6.01 上并未激活。
   - **实测事实**：`ILME-FX6 Ver. 6.01` 将光学补偿置于 **`Technical > Lens`**（并非旧款机型的 `[Project/Paint/Lens] -> [Lens] -> [Compensate]`），四项均为 `Auto` / `Off` 且随 `All File` 保存；当 `Distortion Comp. = Off`、`S&Q = On` 或 `Codec` 含 **`RAW`** 时，`FX6` 的 `Breathing Compensation` 强制锁定 `Off`。
2. **子系统 2（`[AF Transition Speed]` / `[AF Subj. Shift Sensitivity]` / `[AF Assist]` 与 `[AF Illuminator]` 硬件纠偏）**：
   - **实测事实（关键硬件纠偏）**：与“FX3 机身无对焦辅助灯”的常见误判相反，`ILME-FX3` 官方硬件图 `TP1000886886.html`（*Front side* #8）明确记载机身正面内置 **`AF illuminator/Self-timer lamp/Visible light and IR sensor`**，`TP1000867618.html` 与 `BKID_APP_setting_still_image_af_illuminator` 证实 FX3 在静态照片（Still）模式下既可点亮机身内置辅助灯，也可联动 MI 热靴外接闪光灯的 AF 辅助灯（在 `Movie`/`S&Q`、`AF-C`/运动中 `AF-A`、`Focus Magnifier`、转接环时全部锁定）；与之对比，**`ILME-FX6` 才彻底缺失内置机身 AF 辅助灯**（`FX6 appFw.so` 中的 `setting_still_image_af_illuminator` 为无实机菜单的休眠 Alpha 符号）。
   - **实测事实**：`[AF Transition Speed]`（`1 (Slow)..7 (Fast)`，默认 `5`）与 `[AF Subj. Shift Sensitivity]`（`1(Locked on)..5(Responsive)`，默认 `5(Responsive)`；FX3 `_f.uxc` 全称在 `0x79d6`，带图标紧凑版 `AF Subj. Shift Sens.` 在 `0x64de`）以及 `[AF Assist]`（`On/Off`，默认 `Off`，通过 `VAL_HAITA` 门控在视频 `AF-C` / `MOVIE_AUTO` 下生效）均支持 `[Camera Settings Reset]`。
3. **子系统 3（`[Aperture Drive in AF]` / `[AF w/ Shutter]` / `[Pre-AF]` / `[Circ. of Focus Point]` / `[Focus Area Color]`）**：
   - **实测事实**：`[Aperture Drive in AF]`（Still 专用）提供 **`Focus Priority`** / **`Standard`**（默认）/ **`Silent Priority`** 三档，且 5 项之中这 5 个设置（`Aperture Drive in AF`、`AF w/ Shutter` 默认 `On`、`Pre-AF` 默认 `Off`、`Circ. of Focus Point` 默认 `Does Not Circulate`、`Focus Area Color` 默认 `White`）全部对 `[Camera Settings Reset]` **不可重置（`Not available`）**，仅 `[Initialize]` 可恢复出厂。`ILME-FX3` 正式菜单名称为 **`[Circ. of Focus Point]`** 与 **`[Focus Area Color]`**（`BKID_APP_setting_focus_frame_color` 与 `_f.uxc` `0x7087` 为旧 Alpha 命名遗留）。`ILME-FX6` 无上述 5 项设置，改用电影机专用 `Iris` 体系（`Auto Iris` / `Manual` / `Push Auto Iris` / `Iris Override`）。
4. **子系统 4（`[File/Folder Settings]` / `[Select REC Folder]` / `[Create New Folder]` / `[Rating]` 与 Slot-1 Tier-0 保险库防护）**：
   - **实测事实**：`[Folder Name]` 默认 `Standard Form`（`100MSDCF`..`999MSDCF`，支持末尾 5 字符定制），切换为 `Date Form`（`100_MMDD` 形态如 `10020405`）时禁用 `[Select REC Folder]`；单目录上限 `4,000` 张，双卡同时录制时 `[Select REC Folder]` 要求两卡存在同名目录，`[Create New Folder]` 以两卡最大目录号 `+1` 同步建夹。`[Rating]`（`★1..★5`）与 `[Rating Set(Custom Key)]` 直接改写卡上影像 EXIF/XMP 标签并更新 `AVF_INFO` ImageDB，同时可联动 FTP 自动传输。
   - **推断（安全防线）**：当 `Slot 1` 插入承载 `pnflasha`/`cnflasha`/`CAMSET01.DAT` 的只读 Tier-0 恢复保险库介质时，任何针对 `Slot 1` 的 `[Create New Folder]`、`[Forced File Number Reset]`、Playback `[Rating]` 或 `[Add Rating]` 写操作均必须在分发前 fail-closed 拦截并返回 **`EROFS` / `EOPNOTSUPP`**，确保 `slot1_metadata_sector_writes == 0` 且 `slot1_avf_info_mutated == False`。

---

## 1. 子系统 1：`[Lens Compensation]`（`Shading` / `Chromatic Aberration` / `Distortion` / `Breathing`）实证对比

### 1.1 `ILME-FX3 Ver. 7.02` 菜单路径、选项清单与 `Shading Comp.` 休眠枚举实证

- **菜单路径（实测事实，`TP1000882810.html`）**：`MENU` -> `(Shooting)` -> `[Image Quality/Rec]` -> **`[Lens Compensation]`**（`_f.uxc` `0x75c8` `'\ue662Lens Compensation'`；`.uxc` & `_g.uxc` `0x631f` `'\ue61eLens Compensation'`；`_g.uxc` `0x605a` `'Lens Comp.'`）。

| 子菜单项 (`ilc/2210` + `FX3 appFw.so`) | FX3 实机暴露选项 | 出厂默认值 | `[Camera Settings Reset]` | `appFw.so` BKID / 枚举与硬件约束 (`实测事实`) |
| :--- | :--- | :---: | :---: | :--- |
| **`[Shading Comp.]`** (`_f.uxc` `0x64e1`) | **`[Auto]`**, **`[Off]`** *(无 `Low` / `Auto: Low`)* | **`Auto`** | **Not available** *(需 `[Initialize]`)* | `BKID_APP_setting_lens_comp_shading`, `PID_SET_SHADING_CORRECTION`; `FX3 appFw.so` 含休眠枚举 `LENS_COMP_SHADING_AUTO_LOW` 与 `_f.uxc` `0x6c9c` `'Auto: Low'`，但 `ilc/2210` 与 FX3 UI 仅暴露 `Auto / Off` |
| **`[Chromatic Aberration Comp.]`** (`_f.uxc` `0x68cd`) | **`[Auto]`**, **`[Off]`** | **`Auto`** | **Not available** *(需 `[Initialize]`)* | `BKID_APP_setting_lens_comp_chro_aber`, `PID_SET_CHROMA_ABERR_CORRECTION`, `LENS_COMP_CHRO_ABER_{AUTO,OFF}` |
| **`[Distortion Comp.]`** (`_f.uxc` `0x6200`) | **`[Auto]`**, **`[Off]`** | **`Off`** | **Not available** *(需 `[Initialize]`)* | `BKID_APP_setting_lens_comp_distortion`, `PID_SET_DISTORTION_CORRECTION`, `VAL_select_distortion_support_LENS_SELECT_DISTORTION_{SUPPORTED,NOT_SUPPORTED}` |
| **`[Breathing Comp.]`** (`_f.uxc` `0x73ea`, `Ver. 3.00+`) | **`[On]`**, **`[Off]`** *(仅 Movie)* | **`Off`** | **Can be reset** | `BKID_APP_setting_lens_comp_breathing`, `PID_SET_BREATHING_CORRECTION`, `VAL_HAITA_setting_lens_comp_breathing_exposure_mode_*_EXPOSURE_MODE_MOVIE`, `VAL_breathing_correction_lens_type_BREATHING_CORRECTION_LENS_TYPE_SUPPORT` |

- **对 `Shading Comp.` 选项数量的严格实证结论（`实测事实`）**：
  - 官方 `ILME-FX3` Help Guide `TP1000882810.html` 及跨机型比对显示：`ILCE-6700` 暴露 `[Auto] / [Auto: Low] / [Off]`，`ILCE-7RM5` / `ILCE-9M3` / `ILX-LR1` 暴露 `[Auto] / [Low] / [Off]`，而 **`ILME-FX3`（`ilc/2210`）、`ILME-FX30` 与 `ILCE-1` 仅暴露 `[Auto]` 与 `[Off]` 两档**。
  - `FX3 Ver. 7.02 appFw.so` 中确实存在 `VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW`，且 `_f.uxc` `0x6c9c` 携带 `'Auto: Low'`（简中 `'自动: 低'` / 繁中 `'自動: 小'` / 日文 `'オート: 弱'`）；**推断**：这是 Sony 统一 BIONZ XR 平台（`appFw.so` + `_f.uxc` 共享资源包）保留给 `ILCE-6700` 等机型的休眠多机型枚举，在 FX3 机型配置表中被屏蔽。

### 1.2 E 卡口镜头元数据强制锁定、无触点手动镜头与 RAW 压缩/边车交互

- **E 卡口镜头通信与强制锁定机制（`实测事实`）**：
  - `FX3` 通过 `libInfraLensCommunicator.so`（`14,544 B`, `osal_snd_sync_msg` / `osal_snd_msg`）读取镜头 ROM/MCU 参数，并向图像管线发送 `PID_SET_LENS_CORRECTION_DATA` 与 `PID_SET_MANUAL_LENS_CORRECTION`。
  - **强制锁定为 `[Auto]` 的场景**（`TP1000882810.html`）：
    1. 特定光学设计强依赖数码几何校正的 E 卡口镜头（如 `SELP1650`、`FE 28-70mm` 等，对应 `VAL_select_distortion_support_LENS_SELECT_DISTORTION_NOT_SUPPORTED`）会将 `[Distortion Comp.]` **强制锁死在 `[Auto]`**，禁止切至 `[Off]`；
    2. 视频模式下开启 **`[SteadyShot] = [Active]`** 时，同样会强制将 `[Distortion Comp.]` 锁定为 `[Auto]`（因电子裁切增稳与畸变矫正共享几何网格变换）。
  - **无触点纯手动镜头（Unchipped Manual Lens）**：`TP1000882810.html` 明确指出镜头补偿仅在兼容自动补偿的镜头上可用（`VAL_launch_lens_comp_LENS_COMP_VALUE_NOT_EXIST`）；挂载无电子触点的第三方手动镜头时，四项补偿菜单不可调节（除非机内底层兜底 `PID_SET_MANUAL_LENS_CORRECTION`）。
- **RAW 压缩（Compressed / Lossless Compressed / Uncompressed）与边车/像素交互（`实测事实` + `推断`）**：
  - **实测事实（官方口径）**：Sony 官方文档说明 `[Lens Compensation]` 应用于机内 JPEG/HEIF 与机内视频录制；在 `Picture Profile` 章节亦注明依据 Gamma 设置不同，关闭镜头补偿可减轻暗部噪点；在静态 `.ARW`（无论 Compressed / Lossless / Uncompressed）中，Sony `Imaging Edge Desktop` 读取内嵌镜头校正参数进行后期渲染。
  - **实测事实（社区与开源 RAW 解码器验证）**：在实机 ARW 行为上，**`[Distortion Comp.]` 永不烘焙进 ARW 像素数据**（仅作参数标签/元数据记录，JPEG/HEIF 才会被裁切变形）；而 **`[Shading Comp.] = [Auto]` 会对多款 Sony Alpha 机型的 ARW 传感器原始暗角数据施加像素级增益修改**（因此使用 Darktable / Lightroom 等第三方镜头配置文件时，若机内未设为 `Off` 易导致边缘双重提亮或 IBIS 偏移时暗角不均）。

### 1.3 `ILME-FX6 Ver. 6.01` 菜单路径与约束对比

| 维度 | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`, `5-024-458-18`) |
| :--- | :--- | :--- |
| **菜单路径** | `(Shooting) -> [Image Quality/Rec] -> [Lens Compensation]` | **`Technical > Lens`**（非旧款 `[Project/Paint/Lens] -> [Lens] -> [Compensate]`） |
| **子项名称与选项** | `Shading Comp.` (`Auto/Off`)、`Chromatic Aberration Comp.` (`Auto/Off`)、`Distortion Comp.` (`Auto/Off`)、`Breathing Comp.` (`On/Off`, Movie) | **`Shading Compensation`** (`Auto/Off`, `0x560a`)、**`Chroma Aberration Comp.`** (`Auto/Off`, `0x4f71`)、**`Distortion Comp.`** (`Auto/Off`, `0x4f62`)、**`Breathing Compensation`** (`Auto/Off`) |
| **休眠符号对比** | `appFw.so` 含 `LENS_COMP_SHADING_AUTO_LOW`（未暴露） | `FX6 appFw.so` 同样继承 `LENS_COMP_SHADING_AUTO_LOW`（未暴露）；另外 `string_english_2.uxc` 含 `White/Black Shading`（`0x4274..0x4275`，属于传感器白/黑电平均匀度校准 `PID_SET_{WHITE,BLACK}_SHADING`，与镜头暗角补偿无关） |
| **RAW / S&Q 互斥** | `[Breathing Comp.]` 仅限 Movie（外录 HDMI RAW 不支持内置视频级呼吸补偿） | **`Breathing Compensation` 在以下任一条件强制锁 `Off`**：`Distortion Comp. = Off`、`Shooting > S&Q Motion = On`，或 `Project > Rec Format > Codec` 含 **`RAW`** |
| **配置文件归属** | 存于机内 NVRAM / `CAMSET*.DAT`（除 `Breathing` 外不随 `Camera Settings Reset` 清除） | 存于 **`All File`**（`s/SONY/PRO/CAMERA/`），**不随 `Scene File` 保存** |

---

## 2. 子系统 2：Movie `[AF Transition Speed]` / `[AF Subj. Shift Sensitivity]` / `[AF Assist]` 与 `[AF Illuminator]` 硬件实证

### 2.1 `[AF Transition Speed]`（`1..7`）、`[AF Subj. Shift Sensitivity]`（`1..5`）与 `[AF Assist]`（`On/Off`）

- **菜单路径（实测事实，`ilc/2210`）**：`MENU` -> `(Focus)` -> `[AF/MF]`。

| 设置项 | 实机选项与刻度 | 默认值 | `Camera Settings Reset` | 适用模式 | `FX3 appFw.so` 符号与互斥门控 (`实测事实`) |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **`[AF Transition Speed]`** (`_f.uxc` `0x6e9d`) | `7 (Fast)`, `6`, `5`, `4`, `3`, `2`, `1 (Slow)` | **`5`** | **Can be reset** | **仅 `Movie` & `S&Q Motion`** | `BKID_APP_setting_movie_af_transition_speed`, `PID_SET_MOVIE_AF_TRANSITION_SPEED`, `VAL_setting_movie_af_transition_speed_MOVIE_AF_TRANSITION_SPEED_{1_SLOW..7_FAST}` |
| **`[AF Subj. Shift Sensitivity]`** (`_f.uxc` `0x79d6`; Fn 紧凑名 `0x64de`) | `5(Responsive)`, `4`, `3`, `2`, `1(Locked on)` | **`5(Responsive)`** | **Can be reset** | **仅 `Movie` & `S&Q Motion`** | `BKID_APP_setting_movie_af_subj_shift_sens`, `PID_SET_MOVIE_AF_SUBJECT_SWITCH_SENSITIVITY`（见注释：枚举 `5_RESPONSICE` 为 Sony 固件原生拼写） |
| **`[AF Assist]`** (`_f.uxc` `0x64a9`) | `On`, `Off` | **`Off`** | **Can be reset** | **仅 `Movie` & `S&Q Motion` 下的 `AF-C`** | `BKID_APP_setting_af_assist`; `VAL_HAITA_setting_af_assist_system_mode_*_SYSTEM_MODE_REC_MOVIE` & `VAL_HAITA_setting_af_assist_setting_focus_mode_menu_dial_*_FOCUS_MODE_MENU_DIAL_MOVIE_AUTO` |

- **`[AF Assist]` 运行机制与镜头限制（`实测事实`，`TP1000887675.html`）**：
  - 当视频模式 `[Focus Mode] = [Continuous AF]`（`appFw.so` 内部编码为 `MOVIE_AUTO`）且 `[AF Assist] = [On]` 时，转动镜头对焦环可即时覆盖自动对焦、手动切换对焦焦点；**停止转动对焦环后，AF-C 即锁定新落点处的被摄体并恢复连续跟踪**。
  - 官方文档明确列出不兼容镜头：`SELP1650`、`SEL18200LE`（不适用于部分 PZ/LE 早期 E 卡口镜头）。
- **`ILME-FX6 Ver. 6.01` 对比（`实测事实`）**：
  - `FX6` 在 `Shooting > Focus` 菜单提供 **`AF Transition Speed`**（`1..7`，`string_english.uxc` `0x272e`/`0x3242`/`0x332f`）、**`AF Subj. Shift Sens.`**（`1..5`，`0x272f`/`0x32a5`/`0x3302`）以及 **`AF Assist`**（`On/Off`，`string_english_2.uxc` `0x43e2..0x43e5`，`PID_SET_AF_ASSIST_ENABLE`），其视频 AF 切换曲线与 FX3 同源（`FX6 appFw.so` 使用完全相同的 `MOVIE_AF_TRANSITION_SPEED_{1_SLOW..7_FAST}` 与 `MOVIE_AF_SUBJ_SHIFT_SENS_{1_LOCKED_ON..5_RESPONSICE}` 枚举）。

### 2.2 关键硬件实证纠偏：`ILME-FX3` 内置机身 AF 辅助灯 vs `ILME-FX6` 彻底缺失

- **实测事实（反驳“FX3 无机身内置 AF 辅助灯”假设）**：
  1. **`ILME-FX3` 机身正面确实内置 LED 对焦辅助灯**：官方 `TP1000886886.html`（*Front side* 零件图 #8）明确标注为 **`AF illuminator/Self-timer lamp/Visible light and IR sensor`**（位于握把与卡口之间、红外遥控接收窗上方），官方规格有效距离约为 `0.3 m – 3.0 m`（搭配 `FE 28-70mm F3.5-5.6 OSS`）。
  2. **内置灯 + MI 热靴外接闪光灯双路触发（`TP1000867618.html`）**：菜单 `MENU -> (Focus) -> [AF/MF] -> [AF Illuminator]`（`.uxc` `0xe07f`, `_f.uxc` `0x69c0`, `BKID_APP_setting_still_image_af_illuminator`：`Auto` 默认 / `Off`，`Camera Settings Reset` **Can be reset**）在静态照片半按快门至合焦前触发机身辅助灯；若 MI 热靴（Multi Interface Shoe）安装了具备 AF 辅助灯功能的 Sony 外接闪光灯且已开机，**外接闪光灯的 AF 辅助灯也会同步点亮**（另 `_f.uxc` `0x6a2b`/`0x6999` 还携带 Alpha 共享的外闪辅助灯亮度/待机闪烁提示词条）。
  3. **四项严格锁定条件（`TP1000867618.html`）**：在以下场景 `[AF Illuminator]` 均不可用：
     - 拍摄模式为 **`[Movie]`** 或 **`[S&Q Motion]`**（**即在视频工作流中完全禁止**）；
     - `[Focus Mode]` 为 `[Continuous AF]`（`AF-C`）或 `[Automatic AF]`（`AF-A`）且被摄体处于移动状态；
     - `[Focus Magnifier]` 对焦放大激活期间；
     - 安装卡口适配器（Mount Adaptor，如 `LA-EA*`）时。
- **`ILME-FX6 Ver. 6.01` 硬件缺失实证（`实测事实`）**：
  - `ILME-FX6` 定位纯电影摄影机（无静态机械快门与消费级自拍/辅助照明 LED）：`FX6` 实机前面板无 AF Illuminator LED，`5-024-458-18` 说明书与 `FX6 string_english*.uxc` 均无 `[AF Illuminator]` 菜单；`FX6 appFw.so` 中仅存 6 条休眠 Alpha 符号（`N5model36setting_still_image_af_illuminator_tE` 等），无实机触发通道。

---

## 3. 子系统 3：`[Aperture Drive in AF]`、`[AF w/ Shutter]`、`[Pre-AF]`、`[Circ. of Focus Point]` 与 `[Focus Area Color]`

### 3.1 完整参数规格、重置策略与 4 语实证（`实测事实`）

| 菜单项 (`ilc/2210` 正式命名 & 路径) | 选项清单 | 默认值 | `Camera Settings Reset` | 模式范围 | `FX3 appFw.so` Key & 实测行为约束 |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **`[Aperture Drive in AF]`** (`Focus -> [AF/MF]`, `_f` `0x7879`/`0x67ba`) | `Focus Priority`, **`Standard`**, `Silent Priority` | **`Standard`** | **Not available** | **仅 Still** | `BKID_APP_setting_stl_aperture_drive_in_af`; 另在 `Silent Mode Settings` 中有独立的 `BKID_APP_setting_silent_detail_setting_aperture_drive_in_af` (`Standard / Silent Priority`) |
| **`[AF w/ Shutter]`** (`Focus -> [AF/MF]`, `_f` `0x771d`/`0x7942`) | **`On`**, `Off` | **`On`** | **Not available** | **仅 Still** | `BKID_APP_setting_still_image_af_w_shutter`; 设为 `Off` 可实现纯粹后键对焦（`AF-ON` 剥离半按快门触发） |
| **`[Pre-AF]`** (`Focus -> [AF/MF]`, `_f` `0x76d8`/`0x6b26`) | `On`, **`Off`** | **`Off`** | **Not available** | **仅 Still** | `BKID_APP_setting_pre_af`, `PID_SET_PRE_AF`; 受镜头能力位 `VAL_lens_pre_af_support_LENS_PRE_AF_{SUPPORT,NA}` 门控，开启后半按快门前即持续预对焦 |
| **`[Circ. of Focus Point]`** (`Focus -> [Focus Area]`, `_f` `0x74f6`/`0x744d`) | `Circulate`, **`Does Not Circulate`** | **`Does Not Circulate`** | **Not available** | **Still, Movie, `S&Q`** | `BKID_APP_setting_circulate_of_focus_point`; 仅对 `Zone` / `Spot: S/M/L` / `Expand Spot` 及其 `Tracking` 生效，触边水平/垂直折返，**不支持对角线循环** |
| **`[Focus Area Color]`** (`Focus -> [Focus Area]`, `_f` `0x74ad`/`0x6af1`) | **`White`**, `Red` | **`White`** | **Not available** | **Still, Movie, `S&Q`** | `BKID_APP_setting_focus_frame_color`（内部沿用 `Focus Frame Color` `_f` `0x7087` 旧命名，`EXTERN_VAL_MENU_FOCUS_FRAME_COLOR_{WHITE,RED}`） |

### 3.2 `[Aperture Drive in AF]` 光学声音、实时取景景深与连拍速度耦合（`实测事实`）

Cross-checking `TP1000883907.html` 与 `_f.uxc` / `.uxc` / `_g.uxc` 提示语揭示了三档对焦光圈驱动的明确机械/帧率权衡：
1. **`[Focus Priority]`**（`_f.uxc` `0x75c0`/`0x6d66` -> `0x659e` & `0x66ee`；`_g.uxc` `0x631a` & `0x63e2`）：
   - 改变对焦时的光圈叶片开合策略以最大化相位检测合焦精度与速度；
   - **实机副作用（UXC 明文警告）**：光圈驱动机械声可能明显可闻（`_g.uxc` `0x631a`/`0x63e2`），实时屏幕可能不反映光圈收缩后的亮度/景深效果（`0x66ee`），且**连续拍摄（Burst）速度可能下降**（`0x659e` / `_g.uxc` `0x63e2`：*"continuous shooting speed may decrease"*）。
2. **`[Standard]`**（`_f.uxc` `0x7425`）：标准光圈驱动平衡，出厂默认。
3. **`[Silent Priority]`**（`_f.uxc` `0x64d3`/`0x6d3a` -> `0x6b9b`）：相比 `Standard` 进一步压低光圈驱动音，但对焦速度可能有所降低且弱光/高反差下合焦难度增加；当静音拍摄（`Silent Mode = On`）开启时，独立子项 `setting_silent_detail_setting_aperture_drive_in_af` 亦在 `Standard` 与 `Silent Priority` 间联动（`VAL_HAITA_setting_silent_detail_setting_aperture_drive_in_af_setting_silent_mode_still_*`）。

### 3.3 `ILME-FX6 Ver. 6.01` 虹膜/对焦控制架构差异（`实测事实`）

- `FX6` 全菜单与 `5-024-458-18` 操作指南中**不存在** `[Aperture Drive in AF]`、`[AF w/ Shutter]`、`[Pre-AF]`、`[Circ. of Focus Point]` 及 `White/Red` `[Focus Area Color]`：
  - **休眠符号实证**：`FX6 appFw.so` 虽保留了 `setting_stl_aperture_drive_in_af`、`setting_still_image_af_w_shutter`、`setting_pre_af`、`setting_circulate_of_focus_point`、`setting_focus_frame_color` 等 Alpha 残留类，均未接入 FX6 UI 树；
  - 甚至 `FX6 string_english_2.uxc` 中的 `0x4fc3`（`'Close Iris to F2.4 for AF'`）与 `0x4332`（`'Iris Warning for AF'`）在 `FX6 appFw.so` 中检索结果为 **`0` 命中**，证实其为 PXW-FX9/广播摄像机字符串包的未接线遗留词条；
  - **`FX6` 实机采用电影机 `Iris` 控制**：`Auto Iris` / `Manual Iris Level` / `Push Auto Iris` / `Auto Iris Override`（`-1.0 .. +1.0` in `0.25` 步进）/ `IRIS Dial` 及 `Focus Area Marker`。

---

## 4. 子系统 4：`[File/Folder Settings]`、`[Select REC Folder]`、`[Create New Folder]`、`[Rating]` 与 `Slot-1` Tier-0 保险库写危害审计

### 4.1 `[File/Folder Settings]` 目录命名、上限与双卡同步规则（`实测事实`）

- **菜单路径**：`MENU` -> `(Shooting)` -> `[File]` -> **`[File/Folder Settings]`**（`_f.uxc` `0x6400` / `0x61ed`）、**`[Select REC Folder]`**（`.uxc` `0xe859`, `_f.uxc` `0x798a`）、**`[Create New Folder]`**（`_f.uxc` `0x60c7`, `.uxc` `0xe44a`, `_g.uxc` `0x63a8`）。

| 菜单项 | 可选值与命名格式 | 默认值 | `Camera Settings Reset` | 路径/容量/双卡规则 (`TP1000884356` / `843995` / `843996` + `appFw.so`) |
| :--- | :--- | :---: | :---: | :--- |
| **`[Folder Name]`** (`.uxc` `0xe9ab`) | **`[Standard Form]`** (`.uxc` `0xe4ff`) / **`[Date Form]`** (`.uxc` `0xe448`, `_f` `0x6e94`) | **`Standard Form`** | **Not available** | `Standard Form`: `DCIM/100MSDCF`..`999MSDCF`（`100`~`999` + 5 位字母数字下划线，可借 `[Create New Folder]` 或 `[Forced File Number Reset]` 修改后 5 位 `_g.uxc` `0x60b2`）；`Date Form`: `DCIM/100` + 年末位 + `MMDD`（如 `10020405`） |
| **`[File Number]`** (`.uxc` `0xe4f5`) | **`Series`**, `Reset` | **`Series`** | **Not available** | `BKID_APP_setting_still_file_number`; `Series` 在换卡或换文件夹时延续编号（`Slot 1`/`Slot 2` 联动） |
| **`[Forced File Number Reset]`** (`_f` `0x790f`/`0x618b`) | 立即执行动作 | — | — | 重置静态照片文件编号至 `0001` 并**新建一个目录**（`_g.uxc` `0x624e`/`0x62d0`/`0x6428`: *`"${v1} folder created."`*） |
| **`[Set File Name]`** (`_f` `0x6271`/`0x6993`) | 3 位前缀（大写字母/数字/下划线，首字符不可为 `_`） | **`DSC`** | **Not available** | 指定静态图像文件名前 3 字符；`Standard Form` 固定首字符行为见 `_f.uxc` `0x6709` |
| **`[Select REC Folder]`** | 从现有静态目录选择 | 当前录制夹 | — | **在 `[Folder Name] = [Date Form]` 时不可用**；**双卡同时录制时，仅可选两张卡均存在的同名目录** |
| **`[Create New Folder]`** | 在 `DCIM/` 创建编号 `+1` 新夹 | — | — | 单目录上限 **`4,000`** 张（满号触发 `STATUS_OF_MEDIA_SLOT1_FOLDER_MAX`）；双卡同时录制时，以**两张卡上最大文件夹号 `+1`** 在双卡同步创建 |

*(注：`[Focus Bracket]` 亦可通过 `BKID_APP_setting_focus_bracket_rec_folder` 自动创建新文件夹存放包围张序列并在完成后退回原目录，见 `_f.uxc` `0x6198`。)*

### 4.2 `[Rating]`（`★1..★5`）与 `[Rating Set(Custom Key)]` 写盘语义（`实测事实`）

- **菜单路径**：`MENU` -> `(Playback)` -> `[Selection/Memo]` -> **`[Rating]`**（`_f.uxc` `0x684f` / `0x7769`）与 **`[Rating Set(Custom Key)]`**（`_f.uxc` `0x766e` / `0x66c1` / `0x662c`，默认未分配 `―`）。
- **自定义按键双重模式（`TP1000882823.html` + `FX3 appFw.so`）**：
  1. **静态拍摄模式自定义键 `[Add Rating]`**（`_f.uxc` `0x7a79`, `0x72cf`, `0x644d..0x6452`, `FUNC_rating_on_shooting_screen`）：在拍摄后对**最后一张静态照片**直接追加 preset 星级（`★1..★5`，UXC 私有星标 `\ue5c2`..`\ue5c6`）；不支持在视频录制过程中使用；若已标星则拒绝覆盖（`_g.uxc` `0x627d`：*"Can't add since a Rating is already applied."*）。
  2. **回放模式自定义键 `[Rating]` / 菜单 `[Rating]`**（`FUNC_rating_content` / `FUNC_rating_content_by_toggle`）：在回放界面循环切换 `★1..★5` 或清除分级，同时由 `BKID_APP_valid_rating_1..5_selecting` 限制可轮转的星级子集（`_f.uxc` `0x68d4..0x68d8`, `0x71cc`）。
- **卡片落盘与关联写操作（`实测事实`）**：
  - `Rating` 并非纯内存标签：执行标星会**直接修改存储卡上的图像文件元数据（EXIF / XMP `VAL_xmp_rating_XMP_RATING_VALID`）与 `AVF_INFO` 影像管理数据库**，用于支持 `[Image Jump Setting]`、`[Filter Condition]` 及 **FTP / Smartphone 按星级自动传输**（`_f.uxc` `0x6a00` / `0x634a` / `0x62da..0x6452`）；背景传输期间若尝试修改评级会被 `EDIT_FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_RATING` 拦截。

### 4.3 `Slot-1` Tier-0 恢复保险库写危害与 Fail-Closed 防护（`实测事实` + `推断`）

- **实测事实（默认槽位与只读状态字）**：
  - `FX3` 诸多单槽默认指向 **`Slot 1`**（见 Wave 51/52 对 `[Select Playback Media]`、`[Memory/Recall Media]`、`[Save/Load Settings]` 的实测结论）；`FX3 appFw.so` 内部维护细粒度槽位状态字：`VAL_status_of_media_slot1_STATUS_OF_MEDIA_SLOT1_READ_ONLY`、`STATUS_OF_MEDIA_SLOT1_DB_LOCKED`、`STATUS_OF_MEDIA_SLOT1_UNWRITABLE`、`STATUS_OF_MEDIA_SLOT1_FOLDER_MAX` 以及 `VAL_media_movie_write_protect_state_slot1_MEDIA_MOVIE_WRITE_PROTECT_STATE_SLOT1_PROTECT`。
- **推断（`Slot-1` Tier-0 恢复保险库防线映射，衔接项目 `G77` / `G84` / `G87` / `G98` 护栏语义）**：
  - 当 `Slot 1` 插入承载本实验室 **Tier-0 恢复保险库产物**（`pnflasha` / `cnflasha` / `CAMSET01.DAT`）的只读或物理写保护卡时，以下 4 类 Wave 53 操作若指向 `Slot 1`（或双卡同时录制模式波及 `Slot 1`）均属于**致命级卡面结构/扇区突变危害**：
    1. `[Create New Folder]`（`EVENT_FUNC_CREATE_NEW_FOLDER_ON` / `FUNC_create_folder`）：在 `Slot 1` `DCIM/` 创建新文件夹并更新 FAT/exFAT 目录表；
    2. `[Forced File Number Reset]`（`FUNC_still_file_number_reset`）：强制重置序号并在 `Slot 1` 创建新文件夹；
    3. `[Rating]` / `[Rating Set(Custom Key)]`（`FUNC_rating_content` / `FUNC_rating_on_shooting_screen`）：直接改写 `Slot 1` 上文件 EXIF/XMP 与 `AVF_INFO` ImageDB；
    4. `[Select REC Folder]` 配合双卡同时拍照或隐式建夹写盘动作。
  - **强制工程要求（推断）**：在模拟器与实机安全预检护栏中，只要检测到 `Slot 1` 持有 Tier-0 恢复保险库标识（`pnflasha`/`cnflasha`/`CAMSET01.DAT`）或处于只读/写保护挂载态，上述 4 类针对 `Slot 1` 的突变请求**必须 fail-closed 拦截并向上层返回 `EROFS` / `EOPNOTSUPP`**，严格保障 `slot1_metadata_sector_writes == 0`、`slot1_avf_info_mutated == False`。
- **`ILME-FX6 Ver. 6.01` 对比（`实测事实`）**：
  - `FX6` 不存在 `100MSDCF` 静态照片目录、`[Forced File Number Reset]` 或消费级 `★1..★5` `[Rating]`：目录管理围绕专业 XAVC **`XAVC Root Folder Name` / `Edit Folder Name` / `Select Folder` / `Rename Folder`**（`FX6 string_english_2.uxc` `0x4cbf`, `0x4f94`, `0x55bd`）与 `Cam ID + Reel#` 展开；剪辑标记采用 **`Clip Flag`（`OK` / `NG` / `KEEP`）**（`VAL_content_clip_flag_CONTENT_CLIP_FLAG_{OK,NG,KEEP,NONE}`、`FUNC_set_clip_flag_*`）。

---

## 5. `O_RDONLY` 本地 Donor 审计台账与 4 语 `resid16` 一致性矩阵（`raw_firmware_bytes_leaked = 0`）

### 5.1 本波次已审计本地 Donor 文件台账（严格 `os.O_RDONLY`）

| Donor 工件 | 大小 (`B`) | SHA-256 | Wave 53 实测命中符号 / 关键证据 (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_lens_comp_{shading,chro_aber,distortion,breathing}`, `LENS_COMP_SHADING_AUTO_LOW`（休眠枚举）, `VAL_select_distortion_support_*`, `BKID_APP_setting_movie_af_{transition_speed,subj_shift_sens}`, `BKID_APP_setting_af_assist`, `BKID_APP_setting_still_image_af_illuminator`, `BKID_APP_setting_stl_aperture_drive_in_af`, `BKID_APP_setting_still_image_af_w_shutter`, `BKID_APP_setting_pre_af`, `BKID_APP_setting_circulate_of_focus_point`, `BKID_APP_setting_focus_frame_color`, `BKID_APP_setting_still_still_folder_name`, `FUNC_create_folder`, `FUNC_rating_content`, `VAL_xmp_rating_XMP_RATING_VALID`, `STATUS_OF_MEDIA_SLOT1_{READ_ONLY,DB_LOCKED,FOLDER_MAX}` |
| `libInfraLensCommunicator.so` | `14,544` | `e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab` | `osal_snd_sync_msg` / `osal_snd_msg` / `osal_reg_sync_msg_queue_cb` 镜头总线 IPC 桥接库 |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `7,475` 条 `0x1e1c` 记录（`0x6000..0x7d3d`，偏移首条 `0x5eb4`）：`Shading Comp.` (`0x64e1`), `Auto: Low` (`0x6c9c` 休眠), `Chromatic Aberration Comp.` (`0x68cd`), `Distortion Comp.` (`0x6200`), `Breathing Comp.` (`0x73ea`), `AF Transition Speed` (`0x6e9d`), `AF Subj. Shift Sensitivity` (`0x79d6`), `AF Assist` (`0x64a9`), `Aperture Drive in AF` (`0x7879`), `Circ. of Focus Point` (`0x74f6`), `Focus Area Color` (`0x74ad`), `Rating` (`0x684f`) |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | 与 `EN` `7,475` 条 `resid16` 1:1 严格对齐 |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | 与 `EN` `7,475` 条 `resid16` 1:1 严格对齐 |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | 与 `EN` `7,475` 条 `resid16` 1:1 严格对齐 |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `2,692` 槽位：`AF Illuminator` (`0xe07f`), `Folder Name` (`0xe9ab`), `Standard Form` (`0xe4ff`), `Date Form` (`0xe448`), `File Number` (`0xe4f5`), `Select REC Folder` (`0xe859`), `New Folder` (`0xe44a`), `White` (`0xe883`), `Red` (`0xe8c6`), `Unable to perform rating on this image.` (`0xe876`) |
| `FX3 string_simplifiedchinese.uxc` | `149,064` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese.uxc` | `151,908` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_japanese.uxc` | `208,564` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `1,390` 槽位：`Lens Comp.` (`0x605a`), `Create a new folder.` (`0x63a8`/`0x60b1`), `Last 5 char. of folder name can be changed.` (`0x60b2`), `Focus Priority` 连拍降速/声响警告 (`0x631a`/`0x63e2`), `Can't add since a Rating is already applied.` (`0x627d`), `Image Database File error...` (`0x63b7`) |
| `FX3 string_simplifiedchinese_g.uxc` | `61,296` | `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese_g.uxc` | `61,372` | `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_japanese_g.uxc` | `89,428` | `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 双 `BK4\x00` 偏移（`0xc`, `0xd200c`）数值 BKID 存储基线 |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_EXTERN_LENS_{SHADING,CHROMATIC_ABERRATION,DISTORTION}_COMPENSATION`, `BKID_APP_SETTING_{AF_ASSIST,MOVIE_AF_TRANSITION_SPEED,MOVIE_AF_SUBJ_SHIFT_SENS}`, `VAL_content_clip_flag_CONTENT_CLIP_FLAG_{OK,NG,KEEP}`; 零 `iris_warn` / `close_iris` 符号 |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `AF Transition Speed` (`0x272e`), `AF Subj. Shift Sens.` (`0x272f`), `Clip Flag {OK,Keep,NG}` (`0x3224`/`0x329f`/`0x32b9`), `XAVC Root Folder Name` (`0x28ef`) |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `Shading Compensation` (`0x560a`), `Chroma Aberration Comp.` (`0x4f71`), `Distortion Comp.` (`0x4f62`), `AF Assist` (`0x43e2..0x43e5`), `Edit Folder Name` (`0x4cbf`), `Select Folder` (`0x4f94`), `Rename Folder` (`0x55bd`), `Set Clip Flag` (`0x42ad`), `Close Iris to F2.4 for AF` (`0x4fc3`, 未接线) |

### 5.2 4 语 `resid16` 关键菜单与选项矩阵（`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`）

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | 归属与语义说明 |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x75c8` | `\ue662Lens Compensation` | `\ue662镜头补偿` | `\ue662鏡頭補償` | `\ue662ﾚﾝｽﾞ補正` | 菜单组标题（`Image Quality/Rec`） |
| `_f` `0x64e1` | `Shading Comp.` | `阴影补偿` | `陰影補償` | `周辺光量補正` | 暗角/周边光量补偿（FX3 仅 `Auto`/`Off`） |
| `_f` `0x6c9c` | `Auto: Low` | `自动: 低` | `自動: 小` | `オート: 弱` | **休眠多机型词条**（`ILCE-6700` 等用，FX3 不暴露） |
| `_f` `0x68cd` | `Chromatic Aberration Comp.` | `色差补偿` | `色像差補償` | `倍率色収差補正` | 倍率色差补偿（`Auto` 默认 / `Off`） |
| `_f` `0x6200` | `Distortion Comp.` | `失真补偿` | `失真補償` | `歪曲収差補正` | 畸变补偿（`Auto` / `Off` 默认；部分镜头/`Active` 增稳锁 `Auto`） |
| `_f` `0x73ea` | `Breathing Comp.` | `呼吸补偿` | `呼吸補償` | `ブリージング補正` | 呼吸效应补偿（`Ver. 3.00+` Movie，`On` / `Off` 默认） |
| `_f` `0x6e9d` | `AF Transition Speed` | `AF过渡速度` | `對焦變換速度` | `AFﾄﾗﾝｼﾞｼｮﾝ速度` | Movie/`S&Q` 对焦切换速度 `1 (Slow)..7 (Fast)`（默认 `5`） |
| `_f` `0x79d6` | `AF Subj. Shift Sensitivity` | `AF摄体转移敏度` | `對焦變換靈敏度` | `AF乗り移り感度` | Movie/`S&Q` 主体切换灵敏度 `1(Locked on)..5(Responsive)`（`0x64de` 为 `\ue660AF Subj. Shift Sens.`） |
| `_f` `0x64a9` | `AF Assist` | `AF帮助` | `AF幫助` | `AFアシスト` | Movie/`S&Q` `AF-C` 对焦环手动覆盖（`On` / `Off` 默认） |
| `.uxc` `0xe07f` | `AF Illuminator` | `AF辅助照明` | `對焦輔助照明` | `AF補助光` | `Auto` 默认 / `Off`（Still 专用；触发机身正面 LED + 兼容 MI 热靴闪光灯） |
| `_f` `0x7879` | `Aperture Drive in AF` | `AF光圈驱动` | `對焦中的光圈驅動` | `AF時の絞り駆動` | Still 专用：`Focus Priority` (`0x75c0`) / `Standard` (`0x7a3f` 默认) / `Silent Priority` (`0x64d3`) |
| `_f` `0x771d` | `AF w/ Shutter` | `半按快门AF` | `半按快門對焦` | `ｼｬｯﾀｰ半押しAF` | Still 专用：`On` 默认 / `Off`（`Not available` for Camera Settings Reset） |
| `_f` `0x76d8` | `Pre-AF` | `预先AF` | `預先對焦` | `プリAF` | Still 专用：`On` / `Off` 默认（`Not available` for Camera Settings Reset） |
| `_f` `0x74f6` | `Circ. of Focus Point` | `对焦点的循环` | `對焦點循環` | `ﾌｫｰｶｽ位置の循環` | `Circulate` (`0x78e1`) / `Does Not Circulate` (`0x7968` 默认；非对角循环） |
| `_f` `0x74ad` | `\ue662Focus Area Color` | `\ue662对焦边框颜色` | `\ue662對焦框色` | `\ue662ﾌｫｰｶｽｴﾘｱ枠色` | `White` (`.uxc` `0xe883` 默认) / `Red` (`.uxc` `0xe8c6`)；`0x7087` 为旧名 `Focus Frame Color` |
| `_f` `0x6400` | `File/Folder Settings` | `文件/文件夹设置` | `檔案/資料夾設定` | `ﾌｧｲﾙ/ﾌｫﾙﾀﾞｰ設定` | 静态照片文件与文件夹子菜单 |
| `.uxc` `0xe9ab` | `Folder Name` | `文件夹名` | `資料夾名稱` | `フォルダー形式` | `Standard Form` (`.uxc` `0xe4ff` `100MSDCF` 默认) / `Date Form` (`.uxc` `0xe448` `10020405`) |
| `.uxc` `0xe859` | `Select REC Folder` | `选择REC文件夹` | `選擇REC資料夾` | `記録フォルダー選択` | `Date Form` 下禁用；双卡同时录制需两卡公共目录 |
| `_f` `0x60c7` | `Create New Folder` | `新文件夹` | `新資料夾` | `ﾌｫﾙﾀﾞｰ新規作成` | 创建编号 `+1` 新夹（上限 `4,000` 张/夹；`Slot-1` Tier-0 保险库需 `EROFS`/`EOPNOTSUPP` 拦截） |
| `_f` `0x684f` | `Rating` | `分级` | `等級` | `レーティング` | `★1..★5`（`\ue5c2..\ue5c6`）；直接改写卡上 EXIF/XMP 与 `AVF_INFO` ImageDB |
| `_f` `0x766e` | `Rating Set(Custom Key)` | `分级设置(自定义键)` | `等級設定（自訂鍵）` | `ﾚｰﾃｨﾝｸﾞ ｶｽﾀﾑｷｰ設定` | 缩窄自定义键 `[Add Rating]` / `[Rating]` 可选星级子集 |
