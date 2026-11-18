# 全球 Sony 实机情报 Wave 66（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：静态 `[Drive Mode]` `10 fps` 连拍与休眠 `[Focus Bracket]` 辟谣、`[Shutter Type]` 双档无 `Auto` / `1/250 s` X-Sync / `[e-Front Curtain Shut.]` / `[Long Exposure NR]`、`10` 预设 `[Creative Look]` `8` 参 vs `Picture Profile`/`Log` 覆盖与休眠 `[Soft Skin Effect]`，以及 `[Delete]` / `[Protect]` / `[Recover Image DB]` `Slot-1` Tier-0 保险库危险边界）

- **日期**：`2026-11-17`
- **任务 / 波次**：`H401` · **Wave 66（Global Sony Real-Hardware Empirical Intelligence Wave 66）**
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：
  - 官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Drive Mode / Cont. Shooting / Self-timer(Single) / Self-timer(Cont) / Cont. Bracket / Single Bracket / WB bracket / DRO Bracket / Interval Shoot Func. / Shutter Type / e-Front Curtain Shut. / Long Exposure NR / High ISO NR / Using flash / ISO AUTO Min. SS / Creative Look / Delete / Delete confirm. / Delete pressing twice / Protect / Recover Image DB / Display Media Info. / List of default setting values / Specifications*）
  - 官方 Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0 —— *Paint/Look > Base Look / Scene File / Noise Suppression / Shooting > Auto Pixel Restore (APR) / Thumbnail > Lock/Unlock Clip / Delete Clip / Media > Restore Media(A)/(B) / Monitoring > Media Status*）及 Sony Camera Remote SDK 机型能力矩阵
  - 严格只读（`os.O_RDONLY`）本地 donor 二进制实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so`、`FX6 string_english.uxc` / `_2.uxc`）
- **硬件安全态势**：严格只读本地 donor 分析（`emmc_writes_authorized = False`，`cross_model_flash_authorized = False`，`hardware_live_attachment_authorized = False`，`raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*`/`PRM_HAITA_*` 符号、SHA-256 账本与官方 Help Guide/说明书条目）与 **`推断`**（Tier-0 `Slot 1` 只读保险库、`EROFS=30` 拦截边界与模拟器台架风险推论）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`Shooting -> [Drive Mode]` 静态连拍/包围曝光与休眠 `[Focus Bracket]` 辟谣）**：
   - **实测事实（`[Drive Mode]` 真值全集）**：`ILME-FX3 Ver. 7.02` 在 `Shooting -> [Drive Mode] -> [Drive Mode]`（`_f 0x7228`）下严格暴露 **`Single Shooting`（默认）**、**`Cont. Shooting`**（`Hi+` 最高约 **`10 fps`** [实取景非实时刷新] / `Hi` 约 **`8 fps`** / `Mid` 约 **`6 fps`** / `Lo` 约 **`3 fps`**；使用 **`Uncompressed RAW`** 或闪光灯时连拍速度**下降**；光圈大于 `F11` 在 `Hi+/Hi/Mid` 下对焦锁定于首张）、`Self-timer(Single)`（`10 Sec / 5 Sec / 2 Sec`）、`Self-timer(Cont)`（`10/5/2 Sec` × `3/5 Img.` 共 6 档）、`Cont. Bracket` 与 `Single Bracket`（`0.3/0.5/0.7/1.0 EV` × `3/5/9 Img.`，`2.0/3.0 EV` × `3/5 Img.`）、`WB bracket`（`Lo ±10 MK-1` / `Hi ±20 MK-1`，3 张）及 `DRO Bracket`（`Lo Lv 1,2,3` / `Hi Lv 1,3,5`；`[HLG Still Image] = On` 时禁用）。全部 `[Drive Mode]` 项**支持 `[Camera Settings Reset]` 复位（`Can be reset`）**。
   - **实测事实（`[Focus Bracket]` 在 `FX3 Ver. 7.02` 彻底休眠辟谣 + Wave 54 交叉核对）**：尽管 `FX3 appFw.so` 编译了完整 Alpha 共享符号（`BKID_APP_setting_focus_bracket_{depth,exposure_lock,interval,number_of_shots,order,rec_folder}`、`VAL_setting_menu_drive_mode_DRIVE_MODE_FOCUS_BRACKET`、`PRM_HAITA_setting_focus_bracket_exposure_lock_setting_menu_drive_mode`），且 `_f.uxc` 含 `0x7563`（`Focus Bracket`）/`0x6915`（`Focus Bracket Order`），**但 Sony 官方 `ILME-FX3` Help Guide（`ilc/2210`）全站检索 `Focus Bracket` 为 `0` 命中，实机菜单并未向用户开放该功能**（该分支实际面向 `ILCE-7RM5` / `ILCE-7SM3` / `ZV-E1` 等同源 Alpha 机身；**交叉核对 Wave 54**：Wave 54 §3 中提到的 `BKID_APP_setting_focus_bracket_order` 与 `VAL_HAITA_*_FOCUS_BRACKET` 均属 ELF 共享门控表资产，**并非 FX3 实机激活菜单项**）。对比 **`ILME-FX6 Ver. 6.01`**：纯电影机无机械快门与静态管线，无 Still `[Drive Mode]`，亦无 `[Focus Bracket]`（`FX6 appFw.so` 仅保留 56+ 个休眠 `focus_bracket` 符号）。

2. **子系统 2（`Shooting -> [Shutter/Silent]` 与 `[Image Quality/Rec]` 降噪：`[Shutter Type]` 无 `Auto` 与 `1/250 s` 单一 X-Sync 辟谣）**：
   - **实测事实（`[Shutter Type]` 仅 2 档、无 `Auto`）**：`ILME-FX3 Ver. 7.02`（`ilc/2210` *Shutter Type* & *List of default setting values*）严格仅暴露 **2 个选项**：**`Mechanical Shutter`（默认，`_f 0x6ddb`）** 与 **`Electronic Shutter`（`_f 0x755a`）**（`Can be reset`），**不存在 `Auto` 选项**！`FX3 appFw.so` `VAL_setting_still_shutter_type_STILL_SHUTTER_TYPE_{MECHANICAL, ELECTRONIC, INVALID}` 同样**没有 `AUTO` 枚举**；ELF 中的 `STILL_SHUTTER_TYPE_ANTI_DISTORTION_SHUTTER_AUTO` 与 `_f 0x66b8`（`"Automatically switches the shutter type."`）属于 `ILCE-1` / `ILCE-7M4` / `ILCE-7RM5` 等机身的休眠共享代码（而 `[Interval Shoot Func.]` 内的 `[Shutter Type in Interval]` 则独立默认 `Electronic Shutter`）。切换至 `Electronic Shutter`（或 `[Silent Mode] = On`）强制锁死 5 项：**闪光灯拍摄、`[Long Exposure NR]`、`[e-Front Curtain Shut.]`、`BULB` 曝光与 `[Anti-flicker Shoot.]`**。
   - **实测事实（闪光同步速度 X-Sync 辟谣：`1/250 s` 单一上限，无 `1/320 s` APS-C 档）**：`ILME-FX3` 官方 *Specifications* 与 *ISO AUTO Min. SS* 实证闪光最高同步速度严格为 **`1/250 s`**；`ilc/2210` 中 **`1/320` 命中数为 `0`**（`1/250 s FF vs 1/320 s APS-C` 实为 `ILCE-7M4`/`ILCE-7RM5`/`ILCE-7M5` 等不同快门总成特性）。
   - **实测事实（`[e-Front Curtain Shut.]`、`[Long Exposure NR]` 与 `[High ISO NR]`）**：
     - `[e-Front Curtain Shut.]`（`_f 0x64c6`，ELF 内部拼写含错字 **`BKID_APP_setting_front_curtaion_shutter`**）：默认 **`On`** / `Off`，**抗 `[Camera Settings Reset]`（`Not available`，仅 `[Initialize]` 还原）**；大光圈高速快门下可能导致焦外光斑削边，且转接第三方/美能达镜头曝光不均时须设为 `Off`。
     - `[Long Exposure NR]`（`_f 0x6465`，`BKID_APP_setting_still_long_exposure_nr`）：默认 **`On`** / `Off`（`Can be reset`），仅对 **`>= 1 s` 快门**执行等时暗帧减除（`NID_LONG_EXP_NR_PROGRESS` 期间阻塞下次拍摄）；在 `Electronic Shutter`、`Silent Mode = On`、`Cont. Shooting`、`Cont. Bracket` 下禁用，`iAuto` 下不可设为 `Off`。
     - `[High ISO NR]`（`_f 0x650b`，`BKID_APP_setting_still_high_iso_nr`）：曝光 **`Normal`（默认）** / `Low` / `Off`（`Can be reset`；ELF 另含休眠 `HIGH` 枚举）；`[File Format] = RAW` 时不可用，且在 `RAW & JPEG/HEIF` 下仅作用于后者而不写入 `.ARW` 数据。
     - 对比 **`ILME-FX6 Ver. 6.01`**：无机械/前帘快门、无 X-Sync、无长曝暗帧；改用 `Shooting > Noise Suppression`（`Custom` 模式支持 On/Off + `Target Display` 分级；`Cine EI / Flexible ISO` 下支持 `Low / Mid / High`，`Cine EI` 默认 `Off`）与 `Technical > APR > Execute`（`Auto Pixel Restore`，需完全遮盖镜头执行，对应 `FX6 ns1 0x2e4e..0x339c`）。

3. **子系统 3（`Exposure/Color -> [Color/Tone] -> [Creative Look]` 10 预设 + 6 自定义 + 8 参数、`PP/Log` 覆盖规则与休眠 `[Soft Skin Effect]`）**：
   - **实测事实（10 预设 + 6 Custom Look + 8 子参数真值与范围陷阱）**：`[Creative Look]`（`_f 0x6823`/`0x6c22`，`Can be reset`）暴露精确 **10 个预设**：`ST`（默认）、`PT`、`NT`、`VV`、`VV2`、`FL`、`IN`、`SH`、`BW`、`SE`，外加 **`Custom Look 1..6`**（`_f 0x6c98`，与 10 预设共同构成 ELF `BKID_APP_creative_look_option_look{0..15}` 共 16 个槽位，且分设 `look_still{0..15}` 与 `look_movie{0..15}`）。精确 **8 项微调参数**及其真实值域：
     - `-9 .. +9`：`Contrast`、`Highlights`、`Shadows`、`Saturation`；
     - **`0 .. 9`**：`Fade`、`Sharpness`、**`Clarity`**（实证为 **`0..9`** 非对称区间，而非 `-9..+9`！）；
     - **`1 .. 5`**：`Sharpness Range`（ELF 内部名 `fineness`）。
     - **实机不可调锁定**：当设为 **`BW` 或 `SE`** 时，**`Saturation` 不可调节**；在 **Movie/S&Q 模式**下，**`Sharpness Range` 不可调节**；在 `Intelligent Auto`、`[Picture Profile] != Off`、`[Log Shooting] != Off` 时 `[Creative Look]` 强制固定显示 **`[-]`**（禁用），在 `[HLG Still Image] = On` 时同样禁用。
   - **实测事实（`[Soft Skin Effect]` 在 `FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 上均为休眠/不支持状态）**：虽然 `FX3 appFw.so` 存在 `BKID_APP_setting_soft_skin_effect{,_on}` 与 `SOFT_SKIN_EFFECT_ON_OPTION_{LOW,MID,HI}`（`_f 0x76d9`），`FX6 appFw.so` 与 `FX6 ns1 0x2cce..0x32da` 亦存在 `Soft Skin Effect Level` 等字符串，**但 `ilc/2210`（`0` 命中）与 Sony Camera Remote SDK 能力表共同实证：`ILME-FX3`、`ILME-FX30` 与 `ILME-FX6` 均不支持（`-`）`[Soft Skin Effect]`**（该功能实际仅在 `ZV-E1`、`ILCE-6700`、`ILCE-7M4` 等机型开放）。`ILME-FX6` 对应色彩管线为 `Paint/Look > Base Look`（`Custom SDR/HDR`、`Cine EI/Quick/Flex. ISO` `S-Log3/709` 与 Media(B) 3D LUT 导入）、`Scene File`、`Detail`、`Matrix`/`Multi Matrix`。

4. **子系统 4（`Playback -> [Delete]` / `[Protect]` 与 `Shooting -> [Media] -> [Recover Image DB]` / `[Display Media Info.]` `Slot-1` Tier-0 危险边界）**：
   - **实测事实（`[Delete]`、`[Delete confirm.]` 与双击速删隐患）**：`[Delete]`（`base 0xe504`）支持 `All Other Than This Img.`、`All Images in This Group`、`Multiple Img.`、`All in this Folder`、**`All with this date`**（`All in this Folder` / `All with this date` 可一次清空整目录/整天媒体，但受保护文件除外）。删除或保护附带 **Proxy** 视频的素材时，**原始视频与 Proxy 文件会被同步一并删除或保护**。`[Delete confirm.]`（`base 0xe721`）默认 **`"Cancel" first`**（`base 0xe724`），若改为 `"Delete" first`（`base 0xe725`）或开启 **`[Delete pressing twice] = On`**（`_f 0x74db`，默认 `Off`），连续两次按垃圾桶键即可**无确认提示直接不可逆删片**。Playback 全部配置**抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 还原）。
   - **实测事实与 Tier-0 推断（`[Protect]` 与 `[Recover Image DB]` 对 `Slot 1` 的直接写入风险）**：`[Protect]`（`base 0xe2c9`）会批量修改当前 `[Select Playback Media]`（默认 **`Slot 1`**）的 DCF/数据库只读属性；**`[Recover Image DB]`**（`_f 0x711b`，`base 0xe918`，`VAL_system_mode_option_SYSTEM_MODE_OPTION_RECOVER_DB`）不删除音视频文件，但会**重写所选卡槽的影像管理数据库（`AVF_INFO`）并清除 FTP 传输结果记录**（受电池电量门控，且**不受 `[Camera Settings Reset]` 与 `[Initialize]` 影响**）。**推断**：若 `Slot 1` 挂载为只读 Tier-0 恢复保险库（存放 `pnflasha`/`cnflasha`/`CAMSET01.DAT` 等位精确证据），对 `Slot 1` 触发 `[Recover Image DB]` 或 `[Protect]`/`[Delete]` 将导致数据库扇区覆写或目录破坏；台架必须强制在 VFS/块层对 `Slot 1` 一切数据库重建与元属性写入返回 **`EROFS (errno 30)`** fail-closed 拦截。`[Display Media Info.]`（`base 0xea2a`，`view_media_info`）仅只读查询剩余可拍照片数（单卡上限 `40,000` 张）与视频剩余录制时间，对 `Slot 1` 零写入风险。对比 `ILME-FX6 Ver. 6.01`：采用 `Thumbnail > Lock/Unlock Clip`、`Thumbnail > Delete Clip`、`Media > Restore Media(A)/(B)`（带 `ng_write_protected` 写保护检测）与 `Monitoring > Media Status`。

---

## 1. 子系统 1：`Shooting -> [Drive Mode]` 静态连拍/包围曝光与 `[Focus Bracket]` 休眠辟谣

### 1.1 `ILME-FX3 Ver. 7.02` `[Drive Mode]` 全量菜单真值与连拍限速表（`实测事实`）

1. **菜单路径与 `[Camera Settings Reset]` 持久化（`ilc/2210` *List of default setting values* + `FX3 appFw.so`）**：
   - `MENU -> (Shooting) -> [Drive Mode]` 仅在静态拍照（Still）管线生效；电影（Movie）与 `S&Q` 模式下整项变灰不可用。
   - **实测事实**：`[Drive Mode]` 及其附属设置项（`[Bracket Settings]`、静态 `[Interval Shoot Func.]`）**全部支持 `[Camera Settings Reset]`（`Can be reset`）**。

| 菜单项 / 子档位（`Shooting -> [Drive Mode]`） | `FX3 Ver. 7.02` 真实参数与默认（`ilc/2210`） | `[Camera Settings Reset]` | UXC `resid16` / ELF `BKID` & `VAL` 实证（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`Single Shooting`** | **出厂默认**：单次按下快门拍摄 1 张 | **Can be reset** | `_f 0x6d37` / `base 0xe842`；`DRIVE_MODE_1_IMAGE_SHOOTING` |
| **`Cont. Shooting` — `Hi+`** | 最高约 **`10 fps`**；连拍期间实时取景画面**非实时追随刷新**；F 值 `> F11` 时焦点锁定于首张 | **Can be reset** | `_f 0x68d1`；`DRIVE_MODE_CONT_SHOOTING`（`Hi+`）；选择 `Uncompressed RAW` 或启用闪光灯时连拍速率**显著下降** |
| **`Cont. Shooting` — `Hi`** | 最高约 **`8 fps`**；F 值 `> F11` 时焦点锁定于首张 | **Can be reset** | `_f 0x6c00`；选择 `Uncompressed RAW` 或闪光灯时降速；缓存写满后屏幕出现 `SLOW` 且帧率受存储卡写入带宽限制 |
| **`Cont. Shooting` — `Mid`** | 最高约 **`6 fps`**；F 值 `> F11` 时焦点锁定于首张 | **Can be reset** | `_f 0x6f48` |
| **`Cont. Shooting` — `Lo`** | 最高约 **`3 fps`**（适合边拍边确认跟焦，无 `> F11` 锁首帧限制说明） | **Can be reset** | `_f 0x6a0b` |
| **`Self-timer(Single)`** | `10 Sec` / `5 Sec` / `2 Sec`（默认 `10 Sec`） | **Can be reset** | `_f 0x6772` / `0x6e8a`，`base 0xe209`/`0xe208`/`0xe207`；`DRIVE_MODE_SELF_TIMER` |
| **`Self-timer(Cont)`** | `10 Sec. 3 Img.` / `10 Sec. 5 Img.` / `5 Sec. 3 Img.` / `5 Sec. 5 Img.` / `2 Sec. 3 Img.` / `2 Sec. 5 Img.`（共 6 档） | **Can be reset** | `_f 0x728c` / `base 0xe6e7`；`DRIVE_MODE_CONT_SELF_TIMER` *（注：ELF 另有休眠 `10SEC_10IMAGES` 等多机种枚举，FX3 7.02 未暴露）* |
| **`Cont. Bracket`** / **`Single Bracket`** | 步长与张数：`0.3EV` / `0.5EV` / `0.7EV` / `1.0EV`（均可选 **`3 / 5 / 9 Image`**）；`2.0EV` / `3.0EV`（均可选 **`3 / 5 Image`**） | **Can be reset** | `_f 0x72cb`/`base 0xe8f7`（`DRIVE_MODE_CONT_BRACKET`）；`_f 0x790b`/`base 0xe190`（`DRIVE_MODE_BRACKET_SINGLE`）；`iAuto` 下禁用；配合闪光灯作用于 `Cont. Bracket` 时执行闪光包围曝光 |
| **`WB bracket`** | **`Lo`**（`±10 MK-1` / mired 增量，3 张）/ **`Hi`**（`±20 MK-1`，3 张） | **Can be reset** | `_f 0x7acb` / `base 0xe7cf`；`DRIVE_MODE_WHITE_BALANCE_BRACKET` |
| **`DRO Bracket`** | **`Lo`**（DRO 增量小：`Lv 1, 2, 3`，3 张）/ **`Hi`**（DRO 增量大：`Lv 1, 3, 5`，3 张） | **Can be reset** | `_f 0x748d` / `base 0xe18f` / `base 0xe952..0xe953`；`DRIVE_MODE_DRO_ADV_BRACKET`；**`[HLG Still Image] = On` 时禁用** |
| **`[Bracket Settings]`**（辅助项） | `[Selftimer during Bracket]`（`Off` 默认 / `2/5/10 Sec`）与 `[Bracket order]`（`0→-→+` 默认 / `-→0→+`） | **Can be reset** | `_f 0x6466`；`BKID_APP_setting_bracket_self_timer`、`BKID_APP_setting_bracket_order`（与 Wave 54 交叉一致） |
| **`[Interval Shoot Func.]`**（同组菜单） | 静态间隔连拍（仅输出静态照片序列，非机内合成延时视频；其独立快门类型默认 `Electronic Shutter`） | **Can be reset** | `_f 0x7027`；`BKID_APP_setting_shutter_type_in_interval_anti_distortion_shutter` |

### 1.2 `[Focus Bracket]` 在 `ILME-FX3 Ver. 7.02` 上的休眠实证辟谣与 Wave 54 交叉核对（`实测事实`）

> [!CAUTION]
> **对“FX3 Ver. 7.02 已支持对焦包围（Focus Bracketing）”的实证辟谣（`实测事实`）**：
> 1. **官方实机文档零存在**：在 Sony 官方 `ILME-FX3` Help Guide（`ilc/2210`）的 *Drive Mode* 章节、*List of default setting values* 及全站检索中，**`Focus Bracket` 命中数为 `0`**；而同时代支持该功能的 Sony 机身（如 `ILCE-7RM5`、`ILCE-7SM3` v3.00+、`ZV-E1`）均在同位置明确列出 `Focus Bracket`。
> 2. **本地 ELF/UXC 确认为跨机种休眠共享资产**：`FX3 appFw.so` 中确实完整编译了 `BKID_APP_setting_focus_bracket_depth`、`_exposure_lock`、`_interval`、`_number_of_shots`、`_order`、`_rec_folder`、`VAL_setting_menu_drive_mode_DRIVE_MODE_FOCUS_BRACKET` 及互斥表项 `PRM_HAITA_setting_focus_bracket_exposure_lock_setting_menu_drive_mode`，`_f.uxc` 中亦存在 `0x7563`（`Focus Bracket`）与 `0x6915`（`Focus Bracket Order`），**但这些与同表中的 `DRIVE_MODE_MOTION_SHOT`、`DRIVE_MODE_LOW_PASS_FILTER_BRACKET`、`DRIVE_MODE_BURST_SHOOTING` 一样，属于 Alpha BIONZ XR 共享代码库中未对 `PRODUCT_MODEL_ALCIN_UUD`（FX3）解禁的休眠分支**。
> 3. **交叉核对 Wave 54**：Wave 54 报告 §3 在分析 `[Bracket Settings]` 时记录了 ELF 中的 `BKID_APP_setting_focus_bracket_order`（`0→-→+` vs `0→+`）及 `VAL_HAITA_setting_bracket_self_timer_setting_menu_drive_mode_*_DRIVE_MODE_FOCUS_BRACKET`。本波次特此明确：**该发现属于 ELF 符号层门控存在性证明，并不代表 `ILME-FX3 Ver. 7.02` 实机 UI 开放了 `[Focus Bracket]`**。
> 4. **对比 `ILME-FX6 Ver. 6.01`**：`FX6` 为纯电影机，**既无 Still `[Drive Mode]` 也无 `[Focus Bracket]`**（尽管 `FX6 appFw.so` 底层依然残留 `56` 个诸如 `sequence_start_focus_bracket`、`drive_mode_expanded_option_switch_focus_bracket` 的 Alpha 共源休眠符号）。

---

## 2. 子系统 2：`Shooting -> [Shutter/Silent]`、`[Image Quality/Rec]` 降噪与 `FX6` 对比

### 2.1 `[Shutter Type]` 无 `Auto` 辟谣、`1/250 s` 单一 X-Sync 与 `[e-Front Curtain Shut.]`（`实测事实`）

> [!IMPORTANT]
> **本子系统两项核心辟谣（`实测事实`）**：
> 1. **`[Shutter Type]` 严格只有 `2` 档，无 `Auto` 选项**：Sony 官方 `ilc/2210` *Shutter Type* 与 *List of default setting values* 明确 `ILME-FX3 Ver. 7.02` 仅暴露 **`Mechanical Shutter`（默认）** 与 **`Electronic Shutter`**。`FX3 appFw.so` 中的 `VAL_setting_still_shutter_type_STILL_SHUTTER_TYPE_*` 同样**仅含 `MECHANICAL`、`ELECTRONIC`、`INVALID`（无 `AUTO`）**；而 `BKID_APP_setting_still_shutter_type_anti_distortion_shutter`（含 `AUTO` / `MECHANICAL_SHUT` / 拼写错字 `ELECTORONIC_SHUT`）及 `_f 0x66b8`（`"Automatically switches the shutter type."`）是面向带自动畸变/电子快门切换机身的休眠分支（仅 `[Interval Shoot Func.]` 的 `[Shutter Type in Interval]` 独立使用了 `_anti_distortion_shutter` 家族并默认设为 `Electronic Shutter`）。
> 2. **闪光灯同步速度严格为 `1/250 s`，不存在 `1/320 s` APS-C 档**：`ILME-FX3` *Specifications* 与 *ISO AUTO Min. SS* 实证其全画幅电子控制纵走式焦平面快门在使用 Sony 兼容闪光灯时最高同步速度为 **`1/250 s`**；`ilc/2210` 全站 **`1/320` 与 `High-speed sync` 均无 FX3 APS-C `1/320 s` 特性**（后者属 `ILCE-7M4` / `ILCE-7RM5` 等高像素机身 APS-C 裁切同步规格；*Using flash* 另提醒使用外接高速非专用引闪在快于 `1/4000 s` 时可能出现明暗条纹，建议手动输出 `>= 1/2`）。

1. **`[Shutter/Silent]` 与 `[Image Quality/Rec]` 降噪全量真值表（`ilc/2210` + `FX3 appFw.so`）**：

| 菜单项（路径） | `FX3 Ver. 7.02` 真值选项与默认（`ilc/2210`） | `[Camera Settings Reset]` | ELF / UXC 实证与官方锁死互锁条件（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Shutter Type]`**<br>(`Shooting -> [Shutter/Silent]`) | 严格 **2 项**：<br>• **`Mechanical Shutter`（默认）**<br>• `Electronic Shutter`<br>*（无 `Auto` 档！）* | **Can be reset** | `_f 0x63db` / `0x6ddb` / `0x755a`；`BKID_APP_setting_still_shutter_type`。<br>**选 `Electronic Shutter`（或 `[Silent Mode] = On`）强制锁死 5 项**：<br>① 闪光灯拍摄（Flash）；② `[Long Exposure NR]`；③ `[e-Front Curtain Shut.]`；④ `BULB` 曝光；⑤ `[Anti-flicker Shoot.]` |
| **`[e-Front Curtain Shut.]`**<br>(`Shooting -> [Shutter/Silent]`) | **`On`（默认）** / `Off` | **Not available** | `_f 0x64c6`；`BKID_APP_setting_front_curtaion_shutter`（**Sony 内部拼写错字 `curtaion`**）、`VAL_..._FRONT_CURTAIN_SHUTTER_{ON,OFF,INVALID}`。<br>大光圈高快门下可能产生焦外点光源光斑被切边（需设 `Off`）；转接第三方/Minolta 镜头曝光不均需设 `Off`；`Electronic Shutter` / `Silent Mode = On` 时不可用 |
| **`[Long Exposure NR]`**<br>(`Shooting -> [Image Quality/Rec]`) | **`On`（默认）** / `Off` | **Can be reset** | `_f 0x6465`；`BKID_APP_setting_still_long_exposure_nr`；`NID_LONG_EXP_NR_ON` / `NID_LONG_EXP_NR_PROGRESS`。<br>仅当快门速度 **`>= 1 s`** 时触发等时长暗帧减除（处理期间阻断连续拍下一张）。<br>**不可用/强制锁死**：`Electronic Shutter`、`Silent Mode = On`、`Cont. Shooting`、`Cont. Bracket`；`iAuto` 下不可设为 `Off`。（注：`BULB` 自身亦在连拍、自拍连拍、连续包围、电子快门、间隔拍摄下禁用） |
| **`[High ISO NR]`**<br>(`Shooting -> [Image Quality/Rec]`) | **`Normal`（默认）** / `Low` / `Off`<br>*（ELF 另有休眠 `HIGH` 枚举）* | **Can be reset** | `_f 0x650b` / `0x688f` / `base 0xe9ae` / `base 0xe6ab` / `base 0xea17`；`BKID_APP_setting_still_high_iso_nr`。<br>`iAuto` 下固定 `Normal`；**`[File Format] = RAW` 时不可用**；在 `RAW & JPEG/HEIF` 下**仅作用于 JPEG/HEIF，不影响 `.ARW` 原始数据** |

### 2.2 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` 快门与降噪机制对照（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 appFw.so`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 appFw.so`） |
| :--- | :--- | :--- |
| **物理机械快门 / 前帘 / 闪光 X-Sync** | 配备机械焦平面快门，支持 `e-Front Curtain Shut.`（默认 `On`，抗 Reset）与 **`1/250 s`** 闪光同步 | **无机械快门、无电子前帘、无热靴闪光 X-Sync**（纯无机械快门电影机；`FX6 appFw.so` 中 `still_shutter_type` / `front_curtaion` 属休眠共享符号） |
| **长曝光暗帧减除** | 静态 `[Long Exposure NR]`（默认 `On`，`>= 1 s` 等时暗帧减除） | **无 `[Long Exposure NR]`**（电影快门受帧率与 180°/慢快门限约束，不执行静态黑帧减除） |
| **高感光降噪 / 坏点修复** | 静态 `[High ISO NR]`（`Normal / Low / Off`，不影响 `.ARW`）；自动像素映射周期性硬件机制 | **`Shooting > Noise Suppression`**（`FX6 ns1 0x2f30..0x2f92` / `ns2 0x4231`：`Custom` 模式可选 `On/Off` + 等级；`Cine EI / Flexible ISO` 下可选 `Off / Low / Mid / High`，`Cine EI` 默认 `Off`）+ **`Technical > APR > Execute`**（`Auto Pixel Restore`，`FX6 ns1 0x2e4e..0x339c`，需完全盖上镜头执行传感器像素修复） |

---

## 3. 子系统 3：`Exposure/Color -> [Color/Tone] -> [Creative Look]` 10 预设 8 参数、`PP/Log` 覆盖规则与休眠 `[Soft Skin Effect]`

### 3.1 `[Creative Look]` 10 预设、6 个 `Custom Look` 与 8 子参数真值（`实测事实`）

1. **菜单位置与 Reset 持久化（`ilc/2210` *Creative Look* & *List of default setting values*）**：
   - 路径：`MENU -> (Exposure/Color) -> [Color/Tone] -> [Creative Look]`（`_f 0x6823` / `0x6c22`），同时适用于 Still、Movie 与 `S&Q`；**支持 `[Camera Settings Reset]`（`Can be reset`）**。
   - **实测事实（10 预设 + 6 自定义 = ELF 16 槽位，且 Still / Movie 分别存储）**：
     - **10 个内置预设**（出厂默认 **`ST`**）：
       1. **`ST`**（Standard，`_f 0x770c`，`LOOK_STANDARD`）
       2. **`PT`**（Portrait，`_f 0x69ba`，`LOOK_PORTRAIT`）
       3. **`NT`**（Neutral，`_f 0x7652`，`LOOK_NEUTRAL`）
       4. **`VV`**（Vivid，`_f 0x6ab8`，`LOOK_VIVID`）
       5. **`VV2`**（Vivid 2 / Brilliant，`_f 0x7864`，`LOOK_BRILLIANT`）
       6. **`FL`**（Film，`_f 0x6cb6`，`LOOK_FILM`）
       7. **`IN`**（Instant / Retro，`_f 0x69c6`，`LOOK_RETRO`）
       8. **`SH`**（Soft Highkey / Airy，`_f 0x6b10`，`LOOK_AIRY`）
       9. **`BW`**（Black & White，`_f 0x7091`，`LOOK_BLACK_WHITE`）
       10. **`SE`**（Sepia，`_f 0x7702`，`LOOK_SEPIA`）
     - **`Custom Look 1..6`**（`_f 0x6c98`）：支持将基于上述预设调整后的参数注册进 **`1` 到 `6`** 号自定义外观槽位（连同 10 个预设共 **16 个槽位**，精确对应 `FX3 appFw.so` 的 **`BKID_APP_creative_look_option_look{0..15}`**、**`look_still{0..15}`** 与 **`look_movie{0..15}`** 共 `160+` 个符号）；在微调画面按垃圾桶（Delete）键可单键重置当前 Look 的已修改参数。

2. **精确 `8` 项子参数、值域与实机锁定矩阵（`ilc/2210` + `FX3 appFw.so`）**：

| 序号 | 子参数官方名（UI） | `FX3 appFw.so` 内部键名 | UXC `resid16`（`_f` / `base`） | `FX3 Ver. 7.02` 真实范围 | 实机禁用 / 不可调条件（`实测事实`） |
| :---: | :--- | :--- | :--- | :---: | :--- |
| 1 | **`Contrast`** | `contrast{0..15}` | `base 0xe9fb` | **`-9` .. `+9`** | 当 `[Creative Look]` 本身被禁用时固定 `[-]` |
| 2 | **`Highlights`** | `highlight{0..15}` | `_f 0x665b` | **`-9` .. `+9`** | 同上 |
| 3 | **`Shadows`** | `shadow{0..15}` | `_f 0x71b9` | **`-9` .. `+9`** | 同上 |
| 4 | **`Fade`** | `fade{0..15}` | `_f 0x6c64` | **`0` .. `9`** | 同上（单向正值区间） |
| 5 | **`Saturation`** | `saturation{0..15}` | `base 0xe8d0` | **`-9` .. `+9`** | **设为 `BW` 或 `SE` 时不可调节（锁死）！** |
| 6 | **`Sharpness`** | `sharpness{0..15}` | `base 0xe9fd` | **`0` .. `9`** | 当 `[Creative Look]` 本身被禁用时固定 `[-]` |
| 7 | **`Sharpness Range`** | **`fineness{0..15}`** | `_f 0x6e76` | **`1` .. `5`** | **在电影（Movie / S&Q）模式下不可调节（锁死）！** |
| 8 | **`Clarity`** | `clarity{0..15}` | `_f 0x6921` | **`0` .. `9`** | *注意真值为 **`0..9`** 而非 `-9..+9`！* |

3. **`[Picture Profile]` / `[Log Shooting]` 覆盖与变灰锁死规则（`ilc/2210`）**：
   - 当 **`[Picture Profile] != Off`**（`PP1..PP11`，`_f 0x6830`）或 **`[Log Shooting] != Off`**（`Flexible ISO / Cine EI Quick / Cine EI`，`_f 0x6020`）时，`[Creative Look]` **被覆盖并强制固定为 `[-]`（无法更改或生效）**；
   - 此外，在 **`[Intelligent Auto]`（`iAuto`）** 与静态 **`[HLG Still Image] = On`** 下，`[Creative Look]` 同样禁用并固定为 `[-]`。

### 3.2 `[Soft Skin Effect]` 休眠实证与 `FX3` vs `ILME-FX6` 色彩体系对比（`实测事实`）

> [!WARNING]
> **`[Soft Skin Effect]` 在 `FX3 Ver. 7.02` 与 `FX6 Ver. 6.01` 上均确认不支持/休眠（`实测事实`）**：
> - `FX3 appFw.so` 编译了 `BKID_APP_setting_soft_skin_effect`、`BKID_APP_setting_soft_skin_effect_on` 及 `SOFT_SKIN_EFFECT_ON_OPTION_{LOW,MID,HI}`（`_f 0x76d9`）；`FX6 appFw.so` 与 `FX6 ns1 0x2cce..0x32da` 亦存在 `Soft Skin Effect Level` 字符串。
> - **然而**：`ilc/2210`（`ILME-FX3` Help Guide）对 `Soft Skin Effect` 检索结果为 **`0` 命中**，且 Sony 官方 Camera Remote SDK 硬件支持表直接将 `CrDeviceProperty_SoftSkinEffect` 对 **`ILME-FX3`、`ILME-FX30` 与 `ILME-FX6` 全部标记为 `-`（不支持）**（该菜单仅面向 `ZV-E1` / `ILCE-6700` / `ILCE-7M4` / `ZV-1F` 等消费/Vlog 机身激活）。

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 appFw.so`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 appFw.so`） |
| :--- | :--- | :--- |
| **直出色彩风格引擎** | **`[Creative Look]`**（10 预设 `ST..SE` + 6 Custom + 8 参数；被 `PP` / `Log` 覆盖） | **无 `[Creative Look]`**，改由 **`Paint/Look > Base Look`**（`Custom SDR`: `S-Cinetone / Standard / Still / ITU709 / 709tone / User1..16`；`Custom HDR`: `HLG Live/Mild/Natural / User1..16`；`Log`: `s709 / 709(800) / S-Log3 / User1..16` + 3D LUT 导入）与 **`Scene File`**（仅 Custom）替代 |
| **电影工程调色深度** | `Picture Profile`（`PP1..PP11`）+ `Log Shooting`（`S-Log3` + 用户 LUT） | 完整广播级 **`Paint/Look`**：`Detail`、`Black`、`Knee`、`Matrix`、`Multi Matrix`、`White` 及 `Reset Paint Settings > Reset without Base Look` |
| **`[Soft Skin Effect]`** | **休眠 / 不支持**（ELF 含 `SOFT_SKIN_EFFECT_*` 共享符号，实机未激活） | **休眠 / 不支持**（`ns1` 含残留字面，SDK 标记 `-`） |

---

## 4. 子系统 4：`Playback -> [Delete]` / `[Protect]` 与 `Shooting -> [Media] -> [Recover Image DB]` / `[Display Media Info.]` `Slot-1` Tier-0 危险边界

### 4.1 `[Delete]` / `[Delete confirm.]` / `[Protect]` / `[Recover Image DB]` / `[Display Media Info.]` 实证表（`实测事实`）

1. **全量真值与持久化特征（`ilc/2210` + `FX3 appFw.so`）**：

| 菜单项（路径） | `FX3 Ver. 7.02` 真实选项、默认与关键行为（`ilc/2210`） | Reset / Initialize | ELF / UXC 实证与风险说明（`实测事实`） |
| :--- | :--- | :--- | :--- |
| **`[Delete]`**<br>(`Playback -> [Delete]`) | • `All Other Than This Img.`<br>• `All Images in This Group`<br>• `Multiple Img.`<br>• `All in this Folder`<br>• `All with this date`<br>*(受 `[Protect]` 保护文件无法由此删除，仅 `[Format]` 可清；**删除带 Proxy 的视频会同步删除原始视频与 Proxy 文件**)* | —（执行项） | `base 0xe504`/`0xe5ad`、`_f 0x6848`、`_f 0x69f7`、`base 0xe7f3`/`0xe826`/`0xe2ca`。<br>直接针对当前 `[Select Playback Media]`（默认 **`Slot 1`**）执行 `unlink` 与 `AVF_INFO` 更新 |
| **`[Delete confirm.]`**<br>(`Playback -> [Delete]`) | **`"Cancel" first`（默认）** / `"Delete" first` | **抗 Reset**（仅 Initialize 还原） | `base 0xe721` / `0xe724`（`_f 0x6a5e`） / `0xe725`（`_f 0x6e0a`）；`BKID_APP_setting_delete_confirm`。<br>若设为 `"Delete" first`，连按确认可直接删片 |
| **`[Delete pressing twice]`**<br>(`Playback -> [Delete]`) | **`Off`（默认）** / `On` | **抗 Reset**（仅 Initialize 还原） | `_f 0x74db`；`BKID_APP_setting_delete_by_delete_twice`。<br>设为 `On` 后在回放界面**连按两次删除键可跳过确认直接删片** |
| **`[Protect]`**<br>(`Playback -> [Selection/Memo]`) | `Multiple Img.` / `All in this Folder` / `Cancel All in this Folder` / `All with this date` / `Cancel All with this date` / `All Images in This Group` / `Cancel All in This Group`<br>*(保护带 Proxy 视频会**同步保护原始与 Proxy**；`[Copy]` 不会复制保护属性)* | —（卡内状态变更） | `base 0xe2c9` / `0xe553`、`_f 0x72d9` / `0x73c5` / `0x7339`。<br>对所选播放卡槽的 DCF 文件属性与媒体库执行批量写操作 |
| **`[Recover Image DB]`**<br>(`Shooting -> [Media]`) | 选择 **`Slot 1`** 或 **`Slot 2`** 后执行：<br>重建/修复影像数据库管理文件（`AVF_INFO`），**不删除音视频本体文件**，但会**重置全部 FTP 传输结果标记**；电量不足时阻断执行 | **抗 Reset 且抗 Initialize** | `_f 0x711b` / `base 0xe918` / `base 0xe63e..0xe63f` / `base 0xea12..0xea13`；`VAL_system_mode_option_SYSTEM_MODE_OPTION_RECOVER_DB`。<br>**对 `Slot 1` 触发磁盘管理文件覆写！** |
| **`[Display Media Info.]`**<br>(`Shooting -> [Media]`) | 展示两槽剩余可拍照片数（单卡最高显示 `40,000`）与剩余电影录制时间 | **只读查询** | `base 0xea2a`；`view_media_info` / `PRM_media_info_displaying_state`（含 Sony 内部拼写错字 `NOT_DISPLAYNG`）。**零写入风险** |

### 4.2 `Slot-1` Tier-0 恢复保险库 `EROFS (errno 30)` 危险分析与 `ILME-FX6` 对比（`实测事实` + `推断`）

> [!CAUTION]
> **`[Recover Image DB]` 与回放写入操作对 `Slot 1` Tier-0 恢复保险库的破坏风险（`推断`）**：
> 1. 根据实测事实，`[Recover Image DB]` 会直接对目标卡槽（`Slot 1` 或 `Slot 2`）重建 `AVF_INFO` 数据库目录与索引扇区，而 `[Select Playback Media]` 在恢复出厂/Reset 后**默认指向 `Slot 1`**。
> 2. 若实验台架将 `Slot 1` 作为只读 Tier-0 恢复保险库（存放 `pnflasha` / `cnflasha` / `CAMSET01.DAT` 等位精确恢复镜像），一旦在真机或高仿真模拟器中对 `Slot 1` 执行 `[Recover Image DB]`、`[Delete]`（含 `All with this date` / 双击速删）或 `[Protect]`，系统将尝试向 `Slot 1` 写入/重命名/修改目录项，进而**破坏保险库镜像边界或注入未预期的 `AVF_INFO` 脏扇区**。
> 3. **安全护栏约束（`推断`）**：台架文件系统与块设备守卫**必须将 `Slot 1` 严格挂载为不可变只读卷，对一切源于 `RECOVER_DB`、`DELETE`、`PROTECT` 的 `AVF_INFO` / `DCIM` / `PRIVATE` 写请求无条件返回 `EROFS (errno 30)`**；同时允许 `[Display Media Info.]` 等纯只读 `statfs` 查询正常通过。

| 对比维度 | `ILME-FX3 Ver. 7.02`（`ilc/2210` + `FX3 appFw.so`） | `ILME-FX6 Ver. 6.01`（`5-024-458-18` + `FX6 UXC/appFw.so`） |
| :--- | :--- | :--- |
| **媒体信息查看** | `Shooting -> [Media] -> [Display Media Info.]`（`base 0xea2a`） | `Monitoring > Display On/Off > Media Status`（`FX6 ns2 0x4686`） |
| **素材保护 / 锁定** | `Playback -> [Protect]`（支持文件夹/日期/组批处理） | `Thumbnail > Lock/Unlock Clip`（`Select Clip / Lock All Clips / Unlock All Clips`，`FX6 ns2 0x413c`/`0x413e`） |
| **素材删除与确认** | `Playback -> [Delete]` + `[Delete confirm.]` + `[Delete pressing twice]` | `Thumbnail > Delete Clip`（`Select Clip` / `Delete Clip?`，`FX6 ns2 0x4092`/`0x4fdd`；支持 `Delete Clip Flag` 筛选删除） |
| **数据库重建 / 恢复** | `Shooting -> [Media] -> [Recover Image DB]`（选 `Slot 1` / `Slot 2` 重建 `AVF_INFO`） | **`Media > Restore Media(A)` / `Restore Media(B)`**（`FX6 ns2 0x40db`/`0x40dd`；ELF `procam_msg_confirm_restore_media_{a,b}_controller` 含 `ng_write_protected` 只读卡拒写拦截机制！） |

---

## 5. 本地只读（`os.O_RDONLY`）Donor 取证账本与四语言 UXC `resid16` 对照矩阵

### 5.1 Donor 文件 SHA-256 账本（`实测事实`，`raw_firmware_bytes_leaked = 0`）

| Donor 文件 | 字节大小 | SHA-256 校验值 | 实证覆盖范围 |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`nflasha15/lib/appFw.so`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `menu_drive_mode` / 休眠 `focus_bracket_*`、`still_shutter_type`（无 `AUTO`）vs `anti_distortion`、`front_curtaion_shutter`、`still_long_exposure_nr`、`still_high_iso_nr`、`creative_look_option_look{0..15}`、休眠 `soft_skin_effect`、`delete_confirm`/`delete_by_delete_twice`、`SYSTEM_MODE_OPTION_RECOVER_DB`、`view_media_info` |
| `FX3-CX95900_ALLLANG-Backup.bin` (`BK4`) | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 非易失 `BK4` 参数备份基线（零专有原始字节泄漏） |
| `FX6 appFw.so` (`FX6 .../lib/appFw.so`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | 休眠 `focus_bracket`（56 符号）、`base_look`（68 符号）、`noise_suppression`、`auto_pixel_mapping`、`restore_media_{a,b}` + `ng_write_protected` |
| `FX3 string_english_f.uxc` / `.uxc` / `_g.uxc` | `373,820` / `165,740` / `69,600` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` / `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` / `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | 英文 `_f`（`hdr_flag=15`）/ `base` / `_g` 全量包 |
| `FX3 string_simplifiedchinese_f.uxc` / `.uxc` / `_g.uxc` | `322,652` / `149,064` / `61,296` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` / `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` / `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 简体中文 `_f` / `base` / `_g` 精确映射 |
| `FX3 string_traditionalchinese_f.uxc` / `.uxc` / `_g.uxc` | `324,148` / `151,908` / `61,372` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` / `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` / `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 繁体中文 `_f` / `base` / `_g` 精确映射 |
| `FX3 string_japanese_f.uxc` / `.uxc` / `_g.uxc` | `447,840` / `208,564` / `89,428` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` / `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` / `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 日本语 `_f` / `base` / `_g` 精确映射 |
| `FX6 string_english.uxc` / `_2.uxc` | `118,208` / `118,676` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` / `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `FX6` `Noise Suppression`、`APR`、`Base Look`、`Scene File`、`Restore Media(A)/(B)`、`Lock/Unlock/Delete Clip`、`Media Status`、休眠 `Soft Skin Effect` |

### 5.2 四语言 UXC `resid16` 校验矩阵（`实测事实`，只读 `_f`/`base` 精确提取）

| 包 / `resid16` | English | 简体中文 | 繁體中文 | 日本語 | 状态判定 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `_f` `0x7228` / `0x6d37` / `0x6a32` | `Drive Mode` / `Single Shooting` / `Cont. Shooting` | `拍摄模式` / `单张拍摄` / `连拍` | `過片模式` / `單張拍攝` / `連拍` | `ドライブモード` / `1枚撮影` / `連続撮影` | **活跃**（可 Reset；仅 Still 生效） |
| `_f` `0x68d1` / `0x6c00` / `0x6f48` / `0x6a0b` | `Cont. Shooting: Hi+` / `Hi` / `Mid` / `Lo` | `连拍：Hi+` / `Hi` / `Mid` / `Lo` | `連拍：Hi+` / `Hi` / `Mid` / `Lo` | `連続撮影: Hi+` / `Hi` / `Mid` / `Lo` | **活跃**（`10 / 8 / 6 / 3 fps`；Uncompressed RAW 降速） |
| `_f` `0x6772` / `0x728c` / `0x72cb` / `0x790b` / `0x7acb` / `0x748d` | `Self-timer(Single)` / `Self-timer(Cont)` / `Cont. Bracket` / `Single Bracket` / `WB bracket` / `DRO Bracket` | `自拍定时（单张）` / `自拍定时(连拍)` / `连续阶段曝光` / `单拍阶段曝光` / `白平衡阶段曝光` / `DRO阶段曝光` | `自拍定時器（單張）` / `自拍(連拍)` / `連拍包圍式曝光` / `單張包圍式曝光` / `階段白平衡` / `DRO包圍式曝光` | `ｾﾙﾌﾀｲﾏｰ（1枚）` / `ｾﾙﾌﾀｲﾏｰ（連続）` / `連続ブラケット` / `1枚ブラケット` / `ﾎﾜｲﾄﾊﾞﾗﾝｽﾌﾞﾗｹｯﾄ` / `DROブラケット` | **活跃**（可 Reset；全部受 Still 模式约束） |
| `_f` `0x7563` / `0x6915` | `Focus Bracket` / `Focus Bracket Order` | `对焦包围` / `对焦包围顺序` | `對焦階段` / `對焦階段順序` | `ﾌｫｰｶｽﾌﾞﾗｹｯﾄ` / `ﾌｫｰｶｽﾌﾞﾗｹｯﾄ順序` | **FX3 7.02 / FX6 6.01 均休眠！**（`ilc/2210` 零暴露） |
| `_f` `0x63db` / `0x6ddb` / `0x755a` / `0x66b8` | `Shutter Type` / `Mechanical Shutter` / `Electronic Shutter` / `Automatically switches the shutter type.` | `快门类型` / `机械快门` / `电子快门` / `自动切换快门类型。` | `快門類型` / `機械式快門` / `電子式快門` / `自動切換快門類型。` | `シャッター方式` / `メカシャッター` / `電子シャッター` / `シャッター方式を自動で切り換えます` | **前 3 项活跃**（无 `Auto` 档！）；**`0x66b8` 休眠** |
| `_f` `0x64c6` / `0x6465` / `0x650b` / `0x688f` / `base 0xe6ab` / `0xea17` | `e-Front Curtain Shut.` / `Long Exposure NR` / `High ISO NR` / `Normal` / `Low` / `Off` | `电子前帘快门` / `长时曝光降噪` / `高ISO降噪` / `标准` / `低` / `关` | `電子式前簾快門` / `消除長曝雜訊` / `高ISO雜訊消除` / `一般` / `小` / `關` | `電子先幕ｼｬｯﾀｰ` / `長秒時ノイズ低減` / `高感度ノイズ低減` / `標準` / `弱` / `切` | **活跃**（`e-Front Curtain` 抗 Reset；后二者可 Reset） |
| `_f` `0x6823` / `0x6c98` / `0x770c..0x7702` | `Creative Look` / `Custom Look` / `ST..SE` | `创意外观` / `自定义外观` / `ST..SE` | `風格外觀` / `自訂外觀` / `ST..SE` | `ｸﾘｴｲﾃｨﾌﾞﾙｯｸ` / `カスタムルック` / `ST..SE` | **活跃**（10 预设 + 6 自定义；`PP`/`Log` 覆盖为 `[-]`） |
| `base 0xe9fb` / `_f 0x665b` / `0x71b9` / `0x6c64` / `base 0xe8d0` / `base 0xe9fd` / `_f 0x6e76` / `0x6921` | `Contrast` / `Highlights` / `Shadows` / `Fade` / `Saturation` / `Sharpness` / `Sharpness Range` / `Clarity` | `对比度` / `高光` / `阴影` / `褪色` / `饱和度` / `锐度` / `锐度范围` / `清晰` | `對比度` / `明亮` / `陰影` / `淡化` / `飽和度` / `銳利度` / `銳利度範圍` / `清晰` | `コントラスト` / `ハイライト` / `シャドウ` / `フェード` / `彩度` / `シャープネス` / `シャープネスレンジ` / `明瞭度` | **活跃**（`Clarity 0..9`；`BW/SE` 锁 `Saturation`；Movie 锁 `Sharpness Range`） |
| `_f` `0x76d9` | `Soft Skin Effect` | `美肤效果` | `柔膚效果` | `美肌効果` | **FX3 7.02 / FX6 6.01 均休眠！**（SDK 标 `-`） |
| `base 0xe504` / `0xe721` / `_f 0x6a5e` / `0x6e0a` / `0x74db` / `base 0xe2c9` | `Delete` / `Delete confirm.` / `"Cancel" first` / `"Delete" first` / `Delete pressing twice` / `Protect` | `删除` / `删除确认画面` / `默认为"取消"` / `默认为"删除"` / `按两次删除` / `保护` | `刪除` / `刪除確認` / `"取消"優先` / `"刪除"優先` / `按兩次刪除` / `保護` | `削除` / `削除確認画面` / `「ｷｬﾝｾﾙ」が先` / `「削除」が先` / `2度押しで削除` / `プロテクト` | **活跃**（均抗 Reset；默认指向 `Slot 1` 须防误写） |
| `_f` `0x711b` / `base 0xea2a` | `Recover Image DB` / `Display Media Info.` | `修复影像数据库` / `显示媒体信息` | `還原影像資料庫` / `顯示記憶卡資訊` | `管理ファイル修復` / `メディア残量表示` | **活跃**：前者重建 `AVF_INFO` 须 **`Slot 1` `EROFS=30` 拦截**；后者只读安全 |
