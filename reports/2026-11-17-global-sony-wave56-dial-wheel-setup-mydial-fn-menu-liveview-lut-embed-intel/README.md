# 全球 Sony 实机情报 Wave 56（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[Dial Customize]` 术语演进与 `[Dial/Wheel Setup]` 迭代替换、`[My Dial Settings]`/`[Fn Menu Settings]` 12+12 拆分、`[Live View Display Set.]`/`[Grid Line]` HDMI 隔离，以及 `[Manage User LUTs]`/`[Embed LUT File]` 内嵌容器 vs `PPLUT1..4` 像素烘焙与 `Slot-1` 保险库防线）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *Custom Key/Dial Set.*、*My Dial Settings*、*Av/Tv Rotate*、*Function Ring(Lens)*、*Lock Operation Parts*、*Fn Menu Settings*、*Using the front dial and rear dial*、*Live View Display Set.*、*Bright Monitoring*、*Grid Line Display*、*Grid Line Type*、*HDMI Info. Display*、*Select LUT*、*Manage User LUTs*、*Log Shooting Setting*、*Picture Profile*、*Setting Reset*、*List of default setting values*），Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0），以及严格 `os.O_RDONLY` 本地 donor 二进制/字符串包交叉实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so`、`FX6 string_english.uxc` / `_2.uxc`）。
- **硬件安全态势**：严格只读本地 donor 分析（`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`、ELF 符号与官方文档条款）与 **`推断`**。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[Dial Customize]` 术语演进：`[Custom Key/Dial Set.]` 取代 `[Dial Setup]`、`[Lock Operation Parts]` 取代 `[Dial / Wheel Lock]`、`[Av/Tv Rotate]` 与 `[Function Ring(Lens)]`）**：
   - **实测事实（Ver. 2.00+ 菜单重构消歧）**：早期 `ILME-FX3 Ver. 1.xx` 在 `MENU -> (Setup) -> [Dial Customize]` 下曾提供 **`[Dial Setup]`**（`Tv Av` / `Av Tv` 对调前/后转盘）；但自 **Ver. 2.00+（含 `Ver. 7.02`, `ilc/2210`）起，`[Dial Setup]` 已被 `[Custom Key/Dial Set.]`（Still / Movie 分离配置）正式取代**。同理，`ilc/2210` 中**不存在** `[Dial / Wheel Lock]` 菜单项，实机暴露名称为 **`[Lock Operation Parts]`**（`_f` `0x6904`，`BKID_APP_setting_device_lock`：`Off` 默认 / `Multi-Selector Only` / `Dial + Wheel` / `All`；长按 `Fn` 锁定/解锁，另有 `MENU + Fn` 同按 5 秒全锁捷径）。
   - **实测事实（FX3 实机保留项与休眠 Alpha 陷阱）**：`ILME-FX3 Ver. 7.02` 的 `[Dial Customize]` 分组实际暴露 5 项：**`[Custom Key/Dial Set.]`**、**`[My Dial Settings]`**、**`[Av/Tv Rotate]`**（`Normal` 默认 / `Reverse`）、**`[Function Ring(Lens)]`**（仅 `Power Focus` 默认 与 `APS-C/Super 35 mm / Full Frame` 2 项有效枚举；`VAL_setting_function_ring_FUNCTION_RING_INVALID` 为无效占位）与 **`[Lock Operation Parts]`**。全部 `(Setup)` 菜单项均**不支持 `[Camera Settings Reset]`**（需 `[Initialize]`）。`FX3 appFw.so`/UXC 中残留的 `BKID_APP_setting_dial_setup`、`DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO`、`.uxc` `0xe352`（`Dial / Wheel Lock`）、`_f` `0x6a89`（`Dial/Wheel Setup`）及 `_f` `0x6a5c`/`0x680d`（`Rear Dial L` / `Rear Dial R`）均属于跨 Alpha 机身代码同源继承的**历史/休眠符号**。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01` 不存在 `Av/Tv Rotate` 与 `Lock Operation Parts`，而采用独立实体控制件架构：**`Multi Function Dial`**（`Project > Multi Function Dial > Default Function`：`Off` 默认 / `IRIS` / `ISO/Gain/EI` / `Auto Exposure Level` / `Audio Input Level`）、**`Grip Dial`**（`ASSIGNABLE_DIAL_00` + 方向反转）、**`Handle Dial`**（`ASSIGNABLE_DIAL_01` + 方向反转），以及专用 **`IRIS Dial`** 与无级/步进 **`ND Dial`**。
2. **子系统 2（`[My Dial Settings]` `1..3` 与 `[Fn Menu Settings]` `12 + 12` 拆分）**：
   - **实测事实（FX3 仅 3 个物理转盘/拨轮）**：`ILME-FX3` 机身上物理转盘/拨轮仅有 **3 个**——**`Front Dial`**（`base` `0xe4da` / `_f` `0x6d2a`）、**`Rear Dial`**（单个后转盘，`base` `0xe4db` / `_f` `0x6b61`，**绝非 `Rear Dial L / R` 双后转盘**）与 **`Control Wheel`**（`base` `0xe353` / `_f` `0x6178`）。`FX3 appFw.so` 虽因继承 4 转盘 Alpha 模型而包含 `BKID_APP_mydial_rear_dial_left_setting_list0..2` 与 `right_setting_list0..2`，但 FX3 实机 UI 中仅映射 `Front Dial`、`Rear Dial` 与 `Control Wheel`。
   - **实测事实（`My Dial 1..3` 共享库 vs Still/Movie 独立触发与锁覆盖）**：`[My Dial Settings]` 在底层 NVRAM 为 **3 组共享配置槽**（`list0..2`；默认值 `―`，不支持 `[Camera Settings Reset]`），但在 `[Custom Key/Dial Set.]` 中可按 **Still 与 Movie 各自独立分配**呼出键：`My Dial 1/2/3 during Hold`（按住生效）、`Toggle My Dial 1/2/3`（点按开关）或 `My Dial 1→2→3`（循环切换）。`--` / `Not set` 全空的组合将被自动跳过；且即使转盘已被 `[Lock Operation Parts]` 锁定，**呼出 `My Dial` 期间会自动临时解锁**。
   - **实测事实（`[Fn Menu Settings]` `12 + 12` 严格隔离）**：`MENU -> (Setup) -> [Operation Customize] -> [Fn Menu Settings]`（`_g` `0x614b`，不支持 `[Camera Settings Reset]`）严格拆分为 **`12` 个 Still 槽位**（`BKID_APP_fn_menu_item_ids_for_still0..11`）与 **`12` 个 Movie 槽位**（`BKID_APP_fn_menu_item_ids_for_movie0..11`）；若 12 个槽位全为 `Not set`（`base` `0xe0ac`），按 `Fn` 键将提示无效（`_f` `0x6220`）。对比之下，`ILME-FX6` 无 `My Dial` 与 `Fn Menu`，代之以一键呼出的只读 **`Status Screens`**（Main / Camera / Audio / Media / Assignable 等分页）与可旋转多控拨盘直调的 **`Direct Menu`**（`Home Screen Priority` vs `Direct Menu Priority`）。
3. **子系统 3（`[Live View Display Set.]` 三元拆分与 `[Grid Line Display]` / `[Grid Line Type]`）**：
   - **实测事实（`Live View Display Set.` 已激活子项与 ELF 符号差异）**：`ILME-FX3`（`ilc/2210`）在 **`MENU -> (Shooting) -> [Shooting Display] -> [Live View Display Set.]`**（`_f` `0x6429`，仅 Still 生效）下**确实激活了全部 3 个子项**：**`[Live View Display]`**（`Setting Effect ON` 默认 / `Setting Effect OFF`，Not available reset；开启 `[Bright Monitoring]` 时自动强制切为 `Setting Effect OFF`）、**`[Exposure Effect]`**（`Exposure Set. & flash` 默认 / `Exposure Setting Only`，Not available reset，对应 `BKID_APP_setting_flash_exposure_effect`）与 **`[Frame Rate Low Limit]`**（`On` / `Off` 默认，**Can be reset**）。此外，`[Live View Disp. Select]` 可绑定至自定义键快速切换。
   - **实测事实（`[Grid Line]` 三种类型与 HDMI 清洁输出隔离）**：`MENU -> (Shooting) -> [Shooting Display]` 下提供 **`[Grid Line Display]`**（`On` / **`Off`** 默认，Not available reset，Still/Movie/`S&Q` 通用）与 **`[Grid Line Type]`**（**`Rule of 3rds Grid`** 默认 / `Square Grid` / `Diag. + Square Grid`，Not available reset）。当 `Setup -> [External Output] -> [HDMI Info. Display]` 为 `Off`（或启用 RAW 输出 / `Off(HDMI Only)`）时，网格线等 OSD 叠加**仅留在机身 LCD，不会污染 HDMI 清洁输出**。对比之下，`ILME-FX6` 的 `Monitoring > Marker` 提供更丰富的电影机叠加体系（`Guide Frame`、`Aspect Marker` 含 `Custom Aspect Ratio`、`Safety Zone` `80/90/92.5/95%`、`Center Marker`、`100% Marker`、`Focus/Level Marker`、`User Box`）；且 `FX6 appFw.so` 中另存有面向更高端机型的休眠 PNG 自定义网格符号（`BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0..3`），FX6 `5-024-458-18` 实机仅使用标准 `Marker` 与 `Guide Frame`。
4. **子系统 4（`[Manage User LUTs]` `User1..16` `.cube` 导入、`[Embed LUT File]` 内嵌容器 vs `PPLUT1..4` 像素烘焙，与 `Slot-1` Vault 防护）**：
   - **实测事实（路径纠偏、卡目录与介质锁死）**：`[Manage User LUTs]`（`Import/Edit` / `Delete All`，Not available reset）与 `[Select LUT]`（`S-Log3` / **`s709`** 默认 Can be reset / `709(800%)` / `User1..User16`，Movie & `S&Q`）位于 `MENU -> (Exposure/Color) -> [Color/Tone]`。卡目录规范为：**SD/SDXC 卡 `/Private/Sony/PRO/LUT`**（`FX3 appFw.so` 实测字面量匹配），**CFexpress Type A 卡 `/Sony/PRO/LUT`**，支持 17-point / 33-point `.cube` 3D LUT（含 Ver. 4.00+ C3 Portal 云端导入）。而 **`[Embed LUT File]`** 位于 **`MENU -> (Shooting) -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Embed LUT File]`**（**不在 `[Color/Tone]` 下！** 默认 `On`，**Can be reset**），使用 SD/SDHC 卡时被硬件锁死为 `Off`（`_g` `0x61a0` 强制提示使用 SDXC 或 CFexpress）。
   - **实测事实（容器内嵌 vs 像素烘焙）**：`[Embed LUT File] = On` 并非在卡上生成外部独立 `.cube` 伴随文件（sidecar），而是将 `.cube` 3D LUT 与曝光指数作为元数据**直接内嵌至录制的视频媒体文件容器内部**（`FX3 appFw.so`：`is_embedded_lut_in_pb_file`、`sequence_embedded_lut_apply`；机内回放及 Sony *Catalyst Browse/Prepare* 可无损还原监看色彩而像素本身仍保留 `S-Log3`）。与之相反，将 `User1..16` 绑定到 **`Picture Profile -> PPLUT1..4`**（`[Basic Look]`）录制时，Camera DSP 会将 LUT **不可逆地直接烘焙进记录像素**；且 `PPLUT1..4` **会被 `[Camera Settings Reset]` 与 `[Initialize]` 重置**（有别于保留的 PP1–PP11）。
   - **推断（`Slot-1` Tier-0 保险库写危害护栏）**：从外部存储卡导入 `.cube` 至相机 NVRAM 的 **`[Manage User LUTs] -> [Import/Edit]` 属于纯只读卡操作**（`slot1_data_sector_writes == 0`），可在 `Slot-1` 只读挂载状态下安全放行；而执行录制的 `[Embed LUT File]` 与 `PPLUT1..4` 写盘路径，以及任何回退写入/覆盖 `Slot-1` 卡目录的行为，在 `Slot-1` 挂载 Tier-0 恢复保险库时**必须 fail-closed 拦截并返回 `EROFS` / `EOPNOTSUPP`**。

---

## 1. 子系统 1：`[Dial Customize]`、`[Av/Tv Rotate]`、`[Function Ring(Lens)]` 与 `[Lock Operation Parts]`

### 1.1 `ILME-FX3 Ver. 7.02` 菜单真值、Reset 策略与历史术语迭代（`实测事实`）

- **菜单路径**（`ilc/2210/v1/en/`）：`MENU` -> `(Setup)` -> **`[Dial Customize]`**（`_g` `0x62ed`）。

| 菜单项（`ilc/2210`） | `FX3 Ver. 7.02` 实机可选项 | 出厂默认值 | `[Camera Settings Reset]` | `FX3 appFw.so` 底层键与约束（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **`[Custom Key/Dial Set.]`** (`_f` `0x6290`/`0x73a0`) | `Still` / `Movie` 独立映射前/后转盘、控制拨轮与各物理按键 | **`―`** | **Not available** *(需 `[Initialize]`)* | `BKID_APP_setting_custom_key_movie_front_dial` 等；**自 Ver. 2.00+ 起正式取代旧版 `[Dial Setup]`** |
| **`[My Dial Settings]`** (`_f` `0x6538`) | `My Dial 1` / `My Dial 2` / `My Dial 3`（每组配置 Front Dial / Rear Dial / Control Wheel） | **`―`** | **Not available** *(需 `[Initialize]`)* | `BKID_APP_mydial_{front_dial,rear_dial_left,rear_dial_right,control_wheel}_setting_list0..2` |
| **`[Av/Tv Rotate]`** (`_f` `0x72e3`) | **`Normal`** (`_f` `0x688f`) / **`Reverse`** (`_f` `0x6175`) | **`Normal`** | **Not available** *(需 `[Initialize]`)* | `BKID_APP_setting_av_tv_rotate`; `AV_TV_ROTATE_{NORMAL,REVERSE}`；仅影响被分配了光圈或快门速度的转盘/拨轮 |
| **`[Function Ring(Lens)]`** (`_f` `0x715e`) | **`Power Focus`** (`_f` `0x71aa`/`0x767f`) / **`APS-C/Super 35 mm / Full Frame`** | **`Power Focus`** | **Not available** *(需 `[Initialize]`)* | `BKID_APP_setting_function_ring`; `VAL_setting_function_ring_FUNCTION_RING_{POWER_FOCUS,SUPER_35MM_SEL,INVALID}`；需兼容镜头切换至 `FUNCTION` 档位（向右侧旋向无穷远、向左侧旋向近摄） |
| **`[Lock Operation Parts]`** (`_f` `0x6904`) | **`Off`** / `Multi-Selector Only` (`_f` `0x686b`) / `Dial + Wheel` (`_f` `0x61bb`) / `All` | **`Off`** | **Not available** *(需 `[Initialize]`)* | `BKID_APP_setting_device_lock`; `DEVICE_LOCK_{OFF,MULTISELECTOR,DIAL_WHEEL,ALL}`；长按 `Fn` 锁/解锁（出现 `Locked.` 提示）；另支持 `MENU + Fn` 同按 5 秒锁定除快门外全部按键/转盘/拨轮 |

### 1.2 Ver. 1.xx -> Ver. 7.02 术语消歧与休眠 Alpha 符号证伪（`实测事实`）

1. **`[Dial / Wheel Setup]` / `[Dial Setup]` 的代际消歧**：
   - 在 **FX3 Ver. 1.xx** 早期固件与 `ILCE-7SM3` 等早期菜单中，`(Setup) -> [Dial Customize]` 包含 **`[Dial Setup]`**（`Tv Av` / `Av Tv`，仅在 `M` 曝光模式下对调前/后转盘职责，对应 `FX3 appFw.so` 中的 `BKID_APP_setting_dial_setup`、`DIAL_SETUP_FRONT_SHUTTER_REAR_F_NO`、`DIAL_SETUP_FRONT_F_NO_REAR_SHUTTER`）。
   - 自 **FX3 Ver. 2.00+（含 `Ver. 7.02`）** 菜单重构后，官方 Help Guide（`ilc/2210`）已将 `[Dial Setup]` 移除并整合入更灵活的 **`[Custom Key/Dial Set.]`**（支持在不同曝光模式下独立指定前/后转盘与控制拨轮功能）。
   - 同时，`FX3 appFw.so` 中的 `DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO` 与 `DIALCUSTOMIZE_DIAL_SETUP_LEFT_F_NO_RIGHT_SHUTTER`（对应 `_f` `0x625b` `"Assigns shutter speed to dial L and aperture value to dial R."`）系专为配备 `Rear Dial L / R` 的其它 Alpha 机身准备的**休眠符号**，在单后转盘的 FX3 上完全不可达。
2. **`[Dial / Wheel Lock]` -> `[Lock Operation Parts]` 命名迁移**：
   - 早期 `.uxc`（`ns=39`）保留 `0xe352` `"Dial / Wheel Lock"`，`_f.uxc` 亦保留 `0x737b` `"Dial Lock"` 与 `0x7acd` `"Wheel Lock"`；但在 `ILME-FX3 Ver. 2.00+`（`ilc/2210`）实机菜单中，该项已统一演进为可选择锁定粒度的 **`[Lock Operation Parts]`**（`_f` `0x6904`），不再存在名为 `[Dial / Wheel Lock]` 的独立菜单项。
3. **`[Function Ring(Lens)]` 选项边界**：
   - 经 `FX3 appFw.so` 枚举实证，`setting_function_ring` 仅含 `POWER_FOCUS`、`SUPER_35MM_SEL` 与 `INVALID` 三态，与 `ilc/2210` 文档 100% 吻合，未混入其它机身可能扩展的第三方环功能。

### 1.3 `ILME-FX6 Ver. 6.01` 拨盘/操作环体系对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`, `5-024-458-18`) |
| :--- | :--- | :--- |
| **主拨盘架构** | 机身内置 **Front Dial** + **Rear Dial** + **Control Wheel**（可按 Still/Movie 在 `[Custom Key/Dial Set.]` 映射） | **`Multi Function Dial`**（推按+旋转复合拨盘，菜单路径 **`Project > Multi Function Dial > Default Function`**）：`Off`（默认）/ `IRIS` / `ISO/Gain/EI` / `Auto Exposure Level` / `Audio Input Level` |
| **分体/辅助拨盘** | 无手柄可拆卸独立拨盘（XLR 顶柄仅含音频旋钮） | **`Grip Dial`**（`BKID_APP_SETTING_ASSIGNABLE_DIAL_00` + `DIRECTION` `Normal/Opposite`）、**`Handle Dial`**（`ASSIGNABLE_DIAL_01` + `DIRECTION`）、**`IRIS Dial`**、专用电子无级/步进 **`ND Dial`** |
| **旋转反转与锁定** | `[Av/Tv Rotate]`（`Normal/Reverse`）；`[Lock Operation Parts]`（长按 `Fn` 锁/解锁） | 每个可分配拨盘各自独立提供 `Direction`（`Normal/Opposite`）；无 `Fn` 长按多部件软锁，依靠机侧物理 **`HOLD` 开关**锁死机身与手柄操作件 |

---

## 2. 子系统 2：`[My Dial Settings]`（`1..3`）与 `[Fn Menu Settings]`（`12 + 12` 拆分）

### 2.1 `ILME-FX3` 物理转盘拓扑、`My Dial 1..3` 覆盖逻辑与 `Fn Menu`（`实测事实`）

1. **物理转盘硬件拓扑实证（杜绝 `Rear Dial L/R` 幻觉）**：
   - `ilc/2210`（*Using the front dial and rear dial* / *My Dial Settings*）明确确认 `ILME-FX3` 仅配备 **3 个物理旋转控制器**：**Front Dial**（前转盘，`base` `0xe4da`）、**Rear Dial**（机身右后肩单后转盘，`base` `0xe4db`）与 **Control Wheel**（背面四向复合控制拨轮，`base` `0xe353`）。
   - `FX3 appFw.so` 中虽继承了 `BKID_APP_mydial_rear_dial_left_setting_list0..2` 与 `BKID_APP_mydial_rear_dial_right_setting_list0..2`（对应 `_f` `0x6a5c` `Rear Dial L` 与 `0x680d` `Rear Dial R`），但在单后转盘的 FX3 实机上，`Rear Dial R` 符号群不对应任何第二后转盘实体，模拟器/UI 严禁渲染左右双后转盘。
2. **`[My Dial Settings]`（`MENU -> (Setup) -> [Dial Customize] -> [My Dial Settings]`）机制（`实测事实`）**：
   - **存储结构**：3 组独立组合槽位 **`My Dial 1` / `My Dial 2` / `My Dial 3`**（`list0..2`；NVRAM 参数本身跨模式共享，**不支持 `[Camera Settings Reset]`**，需 `[Initialize]`），每组可分别为 `Front Dial`、`Rear Dial`、`Control Wheel` 指定拍摄参数（或保留 `--` / `Not set`）。
   - **跨模式呼出机制**：在 **`[Custom Key/Dial Set.]`** 中可分别为 **Still** 与 **Movie** 绑定呼出方式（`FX3 appFw.so`：`VAL_my_dial_recall_state_MY_DIAL_RECALL_STATE_{NONE,1,2,3,1_HOLD,2_HOLD,3_HOLD}`）：
     - **按住生效**：`My Dial 1 during Hold` / `My Dial 2 during Hold` / `My Dial 3 during Hold`（松手即恢复常规转盘职责）；
     - **点按开关**：`Toggle My Dial 1` / `Toggle My Dial 2` / `Toggle My Dial 3`（再按或半按快门退出）；
     - **顺序循环**：`My Dial 1→2→3`（`_f` `0x7987`，按 1 -> 2 -> 3 -> 常规功能循环，**若某一编号下所有转盘均设为 `--`/`Not set`，循环时自动跳过该空组**）。
   - **安全/锁优先级覆盖**：当用户通过 `[Lock Operation Parts]` 锁定了转盘/拨轮时，**一旦触发呼出 `My Dial`，被呼出的转盘/拨轮会临时自动解锁**，退出 `My Dial` 后恢复锁定状态。
3. **`[Fn Menu Settings]`（`MENU -> (Setup) -> [Operation Customize] -> [Fn Menu Settings]`）（`实测事实`）**：
   - **严格 `12 + 12` 拆分**：`FX3 appFw.so` 实证底层划分为 **`BKID_APP_fn_menu_item_ids_for_still0..11`**（12 个 Still 槽位）与 **`BKID_APP_fn_menu_item_ids_for_movie0..11`**（12 个 Movie 槽位），不支持 `[Camera Settings Reset]`（需 `[Initialize]`）。
   - **交互与空表保护**：拍摄待机时按 `Fn` 键或使用 `[Swipe Up]`（`Open the Fn Menu`）呼出最多 `2 × 6` 网格；旋转 **Front Dial** 可直接切换高亮格子的参数值；在主屏长按 `Fn` 图标可直达 `[Fn Menu Settings]`。若 12 个槽位全部被设为 `Not set`（`base` `0xe0ac`），按 `Fn` 键将触发阻断提示（`_f` `0x6220`：*"Invalid since Fn menu settings are all 'Not set'."*）。

### 2.2 `ILME-FX3` vs `ILME-FX6` 快捷调参交互架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18`) |
| :--- | :--- | :--- |
| **临时转盘覆盖** | **`My Dial 1..3`**（Hold / Toggle / `1→2→3`；自动跳过空组；临时解锁 `[Lock Operation Parts]`） | **无 `My Dial`**；采用固定实体拨盘 + **10+ 个 Assignable Buttons** + `ND/IRIS/ISO/Shutter` 硬件快捷键 |
| **快捷网格/菜单** | **`Fn Menu`**（12 Still + 12 Movie 独立槽位；支持触摸点选与 Front Dial 直调） | **无 `Fn Menu`**；代之以 **Status Screens**（短按 `MENU` 浏览 Camera/Audio/Assignable/Media 等只读状态页）与 **`Direct Menu`**（Information Display 模式下按压 Multi Function Dial 呼出橙色光标直调 `ISO/EI, Iris, Shutter, WB, ND, Scene/Base Look`；由 `Technical > Menu Settings > Info. Disp. Mode Operation` 控制 `Home Screen Priority` vs `Direct Menu Priority`） |

---

## 3. 子系统 3：`[Live View Display Set.]`、`[Exposure Effect]` 与 `[Grid Line Display]` / `[Grid Line Type]`

### 3.1 `[Live View Display Set.]` 实机 3 项全激活实证（`实测事实`）

- **菜单路径**（`ilc/2210`）：`MENU` -> `(Shooting)` -> **`[Shooting Display]`** -> **`[Live View Display Set.]`**（`_f` `0x6429`，**仅限静态照片 Still Image**；Movie/`S&Q` 始终实时反映设定效果）。

| 子项名称（`ilc/2210`） | 可选值与 UXC `resid16` | 默认值 | `[Camera Settings Reset]` | 运行约束与 `FX3 appFw.so` 实证（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **`[Live View Display]`** (`_f` `0x7227`, `base` `0xe3ca`) | **`Setting Effect ON`** (`_f` `0x7913`, `base` `0xe3c6`) / **`Setting Effect OFF`** (`_f` `0x642f`, `base` `0xe3c7`) | **`Setting Effect ON`** | **Not available** | `BKID_APP_setting_live_view_display`；`OFF` 时不反映曝光补偿、白平衡、Creative Look 等效果（便于影棚闪光灯构图），取景画面显示 **`(VIEW)` 图标**；当开启 **`[Bright Monitoring]`** 时相机**自动强制切至 `Setting Effect OFF`**；可通过自定义键 `[Live View Disp. Select]`（`_f` `0x6001`）一键切换 |
| **`[Exposure Effect]`** (`_f` `0x6552`) | **`Exposure Set. & flash`** (`_f` `0x6bee`) / **`Exposure Setting Only`** (`_f` `0x762b`) | **`Exposure Set. & flash`** | **Not available** | `BKID_APP_setting_flash_exposure_effect`（`FLASH_EXPOSURE_EFFECT_{ON,OFF}`）+ `BKID_APP_setting_live_view_display_with_flash`；仅在 `Setting Effect ON` 且挂载/启用闪光灯时有效；设为 `Exposure Setting Only` 可避免无线/TTL 闪光评估导致取景暗部过度压暗 |
| **`[Frame Rate Low Limit]`** (`_f` `0x700e`) | `On` / **`Off`** | **`Off`** | **Can be reset** | `ilc/2210` 实机确认激活于 `[Live View Display Set.]` 下；`On` 时限制暗光/慢快门下 Live View 帧率不降至低速刷新率，在 `S`/`M` 模式连拍期间亦生效（高速连拍依快门速度可能出现短暂 blackout，`_f` `0x634f`） |

> **关键发现（`实测事实`）**：不同于其它从 Alpha 机型继承而来的休眠项，**`Exposure Effect` 与 `Frame Rate Low Limit` 在 `ILME-FX3`（`ilc/2210`）中均属于正式激活的菜单项**，并非休眠隐藏功能；且其中只有 `[Frame Rate Low Limit]` 支持 `[Camera Settings Reset]`。

### 3.2 `[Grid Line Display]`、`[Grid Line Type]` 与 HDMI 清洁输出隔离（`实测事实`）

- **菜单路径**（`ilc/2210`）：`MENU` -> `(Shooting)` -> **`[Shooting Display]`**（Still / Movie / `S&Q` 通用）：
  1. **`[Grid Line Display]`**（`_f` `0x64b8`/`0x6f9d`/`0x747d`）：`On` / **`Off`**（默认）；`Camera Settings Reset`: **Not available**（`BKID_APP_setting_grid_line_display`）。可将 **`[Grid Line Display Select]`**（`_f` `0x70c5`）绑定至自定义键或 Fn 菜单快速开关。
  2. **`[Grid Line Type]`**（`_f` `0x7920`/`0x69c9`）：**`Rule of 3rds Grid`**（默认，`_f` `0x78ae`, `base` `0xe809`）/ **`Square Grid`**（`_f` `0x715a`, `base` `0xe806`）/ **`Diag. + Square Grid`**（`_f` `0x786c`, `base` `0xe807`）；`Camera Settings Reset`: **Not available**（`BKID_APP_setting_grid_line_type`）。
- **HDMI 清洁输出隔离实证（`实测事实`）**：
  - 由 `MENU -> (Setup) -> [External Output] -> [HDMI Info. Display]`（`_f` `0x6e7c`，`BKID_APP_setting_hdmi_info_display`）控制：`Off` 时仅通过 HDMI 输出纯净录制画面，网格线与拍摄参数 OSD **仅显示在机身 LCD 上**（不会污染外录机录制的 Clean Feed）；设为 `On` 时，拍摄信息与叠加帧移至外接 HDMI 显示器而机身 LCD 熄屏（注：RAW 外录或 `Rec. Media dur HDMI Output = Off(HDMI Only)` 时系统自动强制 `[HDMI Info. Display] = Off`）。

### 3.3 `ILME-FX6 Ver. 6.01` `Marker` 与电影机辅助叠加对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18`) |
| :--- | :--- | :--- |
| **构图网格/引导框** | `[Grid Line Display]`（`On/Off`）+ `[Grid Line Type]`（3 种固定线型）；另有单独 `(Shooting Display) -> [Marker Display]`（Aspect/Center/Safety Zone） | **`Monitoring > Marker > Guide Frame`**（`On/Off`，`BKID_APP_SETTING_GUIDE_FRAME`，对应构图引导框） |
| **画幅/安全框/中心标记** | `[Marker Display]`：`Center Marker`、`Aspect Marker`（预设比例）、`Safety Zone`（`80%/90%`）、`Guide Frame` | **`Monitoring > Marker`**：`Setting`（`On/Off`）、`Color`（7 色）、`Center`（`1/2/3/4/Off`）、`Aspect Marker`（含 **`Custom Aspect Ratio`** 自定义分子/分母宽高比及遮罩 Line/Mask）、`Safety Zone`（`80%/90%/92.5%/95%`）+ `Aspect Safety Area`、`100% Marker`、`User Box`（自定义宽高与坐标）、`Focus/Level Marker` |
| **休眠自定义网格符号** | 无 PNG 自定义网格导入 | `FX6 appFw.so` 包含 `BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0..3`、`BKID_APP_DELETED_SETTING_GRID_LINE_DISPLAY_MOVIE` 与 `GOLDEN_RATIO_GRID` 等面向后续 Alpha/Pro 机型的休眠符号；FX6 `5-024-458-18` 实机仅使用 `Marker` 与 `Guide Frame` |

---

## 4. 子系统 4：`[Manage User LUTs]`、`[Select LUT]`、`[Embed LUT File]` 内嵌 vs `PPLUT1..4` 烘焙与 `Slot-1` 防护

### 4.1 路径纠偏、卡目录规范与 16 槽位生命周期（`实测事实`）

| 菜单项 | `ilc/2210` 精确路径 | 选项与默认值 | `[Camera Settings Reset]` | 卡目录 / 规格与 `FX3 appFw.so` 实证（`实测事实`） |
| :--- | :--- | :--- | :---: | :--- |
| **`[Manage User LUTs]`** (`_f` `0x71af`) | `(Exposure/Color) -> [Color/Tone] -> [Manage User LUTs]` | **`[Import/Edit]`**（`_f` `0x6a05`）<br>**`[Delete All]`**（`_f` `0x6543`）<br>槽位：`User1 .. User16` | **Not available** *(需 `[Initialize]` 删除或手动 Delete)* | `BKID_APP_is_exist_user_lut0..15`（16 槽）、`BKID_APP_user_lut_file_id0..15`、`BKID_APP_user_lut_attr_{input_gamut,ae_level_offset}0..15`；支持 **17-point / 33-point `.cube`** 3D LUT（文件名 `<= 63` 单字节字母数字含 `.cube`；SD/SDHC 下按 8.3 显示）；卡路径：**SD/SDXC = `/Private/Sony/PRO/LUT`**（`FX3 appFw.so` 字面量实测），**CFexpress Type A = `/Sony/PRO/LUT`**；Ver. 4.00+ 支持 C3 Portal `[Cloud(Private)]` / `[Cloud(Share)]` |
| **`[Select LUT]`** (`_f` `0x643e`) | `(Exposure/Color) -> [Color/Tone] -> [Select LUT]` | `S-Log3` / **`s709`** / `709(800%)` / `User1 .. User16` | **Can be reset** *(`-> s709`)* | `BKID_APP_setting_select_lut`；内建映射：`S709` (`SL3SG3Ctos709.cube`)、`R709` (`SL3SG3CtoR709-800.cube`)、`S_LOG3`；用于 Movie/`S&Q` Log 拍摄时的监看 LUT（未导入目标 User 槽位时回退显示 S-Log3，`_f` `0x77ca`） |
| **`[Embed LUT File]`** (`_f` `0x680f`) | `(Shooting) -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Embed LUT File]` *(\*\*非 `[Color/Tone]` 下\*\*)* | **`On`** / `Off` | **Can be reset** *(`-> On`)* | `BKID_APP_setting_embed_lut_file`；**插入 SD 或 SDHC 卡时硬件锁死为 `Off`**（`_g` `0x61a0` 强制提示需使用 **SDXC 或 CFexpress Type A**） |
| **`PPLUT1 .. PPLUT4`** (`_f` `0x6095`) | `(Exposure/Color) -> [Color/Tone] -> [Picture Profile]` -> `PPLUT1..4` -> `[Basic Look]` | 绑定 `User1..16` | **Reset (`PPLUT1..4` 均被 Reset 与 Initialize 清除！)** | `BKID_APP_setting_pplut1..4_link_uset_lut`；`ilc/2210` *Setting Reset* 明确指出 PP1–PP11 在 Reset/Initialize 后保留，**唯独 `PPLUT 1 - 4` 会被重置** |

### 4.2 `[Embed LUT File]` 容器内嵌 vs `PPLUT1..4` 像素烘焙对比（`实测事实`）

1. **`[Embed LUT File] = On`（Log Shooting 下的无损容器内嵌）**：
   - 当 `[Log Shooting]` 设为 `Flexible ISO`、`Cine EI` 或 `Cine EI Quick` 时，将 `[Embed LUT File]` 设为 `On` **不会在存储卡上生成单独的外部 `.cube` 伴随文件（sidecar）**，而是把当前 `[Select LUT]` 选中的 3D LUT（`.cube` 数据）与曝光指数（EI）直接写入**所录视频文件自身的容器元数据**中（`FX3 appFw.so`：`N5model25sequence_set_embedded_lutE`、`N5model27sequence_embedded_lut_applyE`、`is_embedded_lut_in_pb_file`、`embedded_lut_file_name`、`determine_frame_rate_and_movie_quality_and_yuv_color_space`）。
   - 视频帧像素本身依然保持原生 `S-Log3 / S-Gamut3(.Cine)` 无损编码；机内回放及 Sony *Catalyst Browse / Prepare*（Ver. 2022.1+）可读取内嵌 LUT 自动还原监看色彩。
2. **`PPLUT1 .. PPLUT4`（Picture Profile 下的不可逆像素烘焙）**：
   - 将 User LUT 关联至 `PPLUT1..4` 并以此配置录制视频或照片时，Camera DSP 在编码前直接完成 3D LUT 色彩映射，**结果不可逆地烘焙（bake）进视频/照片像素本身**，无需后期软件额外套用 LUT。

### 4.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` LUT 架构与多路独立开关对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18`) |
| :--- | :--- | :--- |
| **用户 3D LUT 容量与实机上限** | `User1 .. User16`（**16 个槽位**） | `Paint/Look > Base Look`（`5-024-458-18` 实机**上限为 16 个 User 3D LUT 槽位**；注：`FX6 appFw.so` 虽存在 `PRM_is_exist_user_lut0..49` 缓冲槽定义，但实机 UI 与说明书严格限制为 `16` 个） |
| **存储卡路径与导入槽位** | SD/SDXC：`/Private/Sony/PRO/LUT`<br>CFexpress：`/Sony/PRO/LUT` | SDXC：**`/PRIVATE/SONY/PRO/LUT/`**<br>CFexpress：**`/SONY/PRO/LUT/`**<br>导入入口固定为 **`Import from Media(B)`**（Slot B）及 `Import from Cloud(Private/Share)` |
| **LUT 内嵌与回放行为** | `(Shooting) -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Embed LUT File]` | **`Project > Cine EI/Flex.ISO Set > Embed LUT File`**（`BKID_APP_SETTING_FLEXIBLE_ISO_EMBED_LUT_FILE`）；若回放时文件内含嵌入 LUT 且相机仍装有对应 LUT 则优先还原，否则回退当前 `Base Look > Select`（旧固件导入带 `!` 前缀的 LUT 不可嵌入） |
| **输出通道分离烘焙能力** | 统一由 `[Display LUT]`（仅监看）或 `PPLUT1..4`（全内录烘焙）控制；无各输出口独立 LUT 开关 | **多通道独立开关**：可分别独立配置 **`Internal Rec.`**（仅机内主录套用 Base Look 烘焙或保持 Log）、**`SDI/HDMI`**、**`LCD/VF`** 与 **`Proxy/Stream`** 是否套用 LUT |

### 4.4 `Slot-1` Tier-0 只读保险库安全护栏（`实测事实` + `推断`）

- **实测事实**：`Manage User LUTs -> [Import/Edit]` 仅从卡内 `/Private/Sony/PRO/LUT` 或 `/Sony/PRO/LUT` 读取 `.cube` 至机身 NVRAM（`model_user_lut_files::mount_lut_folder()` / `read3DLUTFileForCube`），不向存储卡写入或修改 `AVF_INFO`。
- **推断（Slot-1 护栏策略）**：
  1. 当 `Slot 1` 挂载只读 Tier-0 恢复保险库时，**从 `Slot 1` 只读扫描并导入 `.cube` 属于 `safe_read_only`**，前提是绝不向 `Slot 1` 执行任何文件夹创建（`Make Cube Folder`）或配置回写；
  2. 任何指向 `Slot 1` 的视频录制（`[Embed LUT File] = On` 写入内嵌元数据容器或 `PPLUT1..4` 烘焙成片）以及任何向 `Slot 1` 写入 `.cube`/配置文件的操作，**必须 fail-closed 拦截并返回 `EROFS` / `EOPNOTSUPP`**，确保 `slot1_data_sector_writes == 0` 且 `slot1_avf_info_mutated == False`。

---

## 5. `O_RDONLY` 本地 Donor 审计台账与 4 语 `resid16` 一致性矩阵（`raw_firmware_bytes_leaked = 0`）

### 5.1 本波次已审计本地 Donor 文件台账（严格 `os.O_RDONLY`）

| Donor 工件 | 大小 (`B`) | SHA-256 | Wave 56 实测命中符号 / 关键证据 (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_{av_tv_rotate,device_lock,function_ring,custom_key_movie_front_dial}`, 历史/休眠 `BKID_APP_setting_dial_setup` (`LEFT_SHUTTER_RIGHT_F_NO`), `BKID_APP_mydial_{front_dial,rear_dial_left,rear_dial_right,control_wheel}_setting_list0..2`, `BKID_APP_fn_menu_item_ids_for_{still,movie}0..11`, `BKID_APP_setting_{live_view_display,live_view_display_with_flash,flash_exposure_effect}`, `BKID_APP_setting_{grid_line_display,grid_line_type,hdmi_info_display}`, `/Private/Sony/PRO/LUT`, `BKID_APP_is_exist_user_lut0..15`, `BKID_APP_setting_{select_lut,embed_lut_file,pplut1..4_link_uset_lut}`, `is_embedded_lut_in_pb_file` |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | `Custom Key/Dial Set.` (`0x6290`/`0x73a0`), `My Dial Settings` (`0x6538`), `My Dial 1..3` (`0x67da`/`0x64ec`/`0x6936`), `Av/Tv Rotate` (`0x72e3`), `Function Ring(Lens)` (`0x715e`), `Power Focus` (`0x71aa`/`0x767f`), `Lock Operation Parts` (`0x6904`), 历史 `Dial/Wheel Setup` (`0x6a89`), `Live View Display Set.` (`0x6429`), `Exposure Effect` (`0x6552`), `Frame Rate Low Limit` (`0x700e`), `Grid Line Display` (`0x6f9d`), `Grid Line Type` (`0x7920`), `HDMI Info. Display` (`0x6e7c`), `Manage User LUTs` (`0x71af`), `Select LUT` (`0x643e`), `Embed LUT File` (`0x680f`), `Basic Look` (`0x6f6d`), `PPLUT${v1}` (`0x6095`) |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | 首条 `0x5b60`，与 `EN` `7,475` 条 `resid16`（`0x6000..0x7d3d`）1:1 严格对齐 |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | 首条 `0x5b88`，与 `EN` `7,475` 条 `resid16`（`0x6000..0x7d3d`）1:1 严格对齐 |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | 首条 `0x62a4`，与 `EN` `7,475` 条 `resid16`（`0x6000..0x7d3d`）1:1 严格对齐 |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `Front dial` (`0xe4da`), `Rear dial` (`0xe4db`), `Control Wheel` (`0xe353`), `Not set` (`0xe0ac`), 历史 `Dial / Wheel Lock` (`0xe352`), `Setting Effect ON/OFF` (`0xe3c6`/`0xe3c7`), `Rule of 3rds Grid` (`0xe809`), `Square Grid` (`0xe806`), `Diag. + Square Grid` (`0xe807`) |
| `FX3 string_simplifiedchinese.uxc` | `149,064` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese.uxc` | `151,908` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_japanese.uxc` | `208,564` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `Dial Customize` (`0x62ed`), `Fn Menu Settings` (`0x614b`), `Shooting Display` (`0x615e`), `Color/Tone` (`0x61fa`), SDXC `Embed LUT File` 约束提示 (`0x61a0`), `Import the LUT file to User${v1}?` (`0x620b`) |
| `FX3 string_simplifiedchinese_g.uxc` | `61,296` | `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese_g.uxc` | `61,372` | `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_japanese_g.uxc` | `89,428` | `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 双 `BK4\x00` 偏移（`0xc` / `0xd200c`）数值 BKID 存储基线 |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `BKID_APP_SETTING_{MULTI_FUNCTION_DIAL,ASSIGNABLE_DIAL_00..02,GUIDE_FRAME,MARKER_DISPLAY,ASPECT_MARKER,FLEXIBLE_ISO_EMBED_LUT_FILE}`, `PRM_is_exist_user_lut0..49`（实机仅开放 16 槽）, 休眠 `BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0..3` |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `Multi Function Dial` (`0x210a`/`0x22df`), `Grip Dial` (`0x210b`), `Handle Dial` (`0x210c`), `IRIS Dial` (`0x2d11`), `Base Look` (`0x23f8`), `Import from Media(B)` (`0x25f1`), `Embed LUT File` (`0x2644`), `Home/Direct Menu Priority` (`0x2fde`/`0x2feb`) |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `ND Dial` (`0x42c5`), `Direct Menu` (`0x4302`), `Guide Frame` (`0x4520`), `Aspect Marker` (`0x4510`), `Safety Zone` (`0x450c`), `Center Marker` (`0x450a`), `User 3D LUT` (`0x4b40`) |

### 5.2 4 语 `resid16` 关键菜单与选项矩阵（`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`）

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | 归属与实机激活状态 |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_g` `0x62ed` | `Dial Customize` | `转盘自定义` | `轉盤客製化` | `ﾀﾞｲﾔﾙｶｽﾀﾏｲｽﾞ` | Active：`Setup -> [Dial Customize]` 分组 |
| `_f` `0x6290` | `\ue381Custom Key/Dial Set.` | `\ue381自定义键/转盘设置` | `\ue381自訂鍵/轉盤設定` | `\ue381ｶｽﾀﾑｷｰ/ﾀﾞｲﾔﾙ設定` | Active（Still；Movie 为 `_f` `0x73a0`，取代旧 `[Dial Setup]`） |
| `_f` `0x6a89` | `Dial/Wheel Setup` | `转盘/拨轮设置` | `轉盤/滾輪設定` | `ﾀﾞｲﾔﾙ/ﾎｲｰﾙの設定` | **Legacy / Replaced**（Ver. 2.00+ 起由 `[Custom Key/Dial Set.]` 替代） |
| `_f` `0x72e3` | `Av/Tv Rotate` | `Av/Tv旋转` | `Av/Tv旋轉` | `Av/Tvの回転方向` | Active：`Normal` (`_f` `0x688f`) / `Reverse` (`_f` `0x6175`) |
| `_f` `0x715e` | `Function Ring(Lens)` | `功能环(镜头)` | `功能環(鏡頭)` | `ﾌｧﾝｸｼｮﾝﾘﾝｸﾞ(ﾚﾝｽﾞ)` | Active：`Power Focus` (`0x71aa`) / `APS-C/S35 / Full Frame` |
| `_f` `0x6904` | `Lock Operation Parts` | `锁定操作的部件` | `操作鈕鎖定` | `操作部のロック` | Active：`Off` / `Multi-Selector Only` (`0x686b`) / `Dial + Wheel` (`0x61bb`) / `All` |
| `base` `0xe352` | `Dial / Wheel Lock` | `转盘/拨轮锁定` | `轉盤/滾輪鎖` | `ﾀﾞｲﾔﾙ/ﾎｲｰﾙﾛｯｸ` | **Legacy / Renamed**（FX3 `ilc/2210` 实机用 `[Lock Operation Parts]`） |
| `_f` `0x6d2a` | `Front Dial` | `前转盘` | `前轉盤` | `前ダイヤル` | Active（FX3 实体前转盘；`base` `0xe4da`） |
| `_f` `0x6b61` | `Rear Dial` | `后转盘` | `後轉盤` | `後ダイヤル` | Active（FX3 实体单后转盘；`base` `0xe4db`） |
| `_f` `0x6a5c` / `0x680d` | `\ue518Rear Dial L` / `\ue519Rear Dial R` | `\ue518后转盘L` / `\ue519后转盘R` | `\ue518後轉盤L` / `\ue519後轉盤R` | `\ue518後ダイヤルL` / `\ue519後ダイヤルR` | **Dormant**（4 转盘 Alpha 机型符号，FX3 仅单后转盘） |
| `_f` `0x6178` | `Control Wheel` | `控制拨轮` | `控制滾輪` | `ｺﾝﾄﾛｰﾙﾎｲｰﾙ` | Active（FX3 背面控制拨轮；`base` `0xe353`） |
| `_f` `0x6538` | `My Dial Settings` | `我的转盘设置` | `我的轉盤設定` | `マイダイヤル設定` | Active：`My Dial 1..3`（`0x67da` / `0x64ec` / `0x6936`） |
| `_f` `0x66fe` / `0x6bc0` / `0x7987` | `My Dial 1 during Hold` / `Toggle My Dial 1` / `My Dial 1→2→3` | `保持期间的我的转盘1` / `切换我的转盘1` / `我的转盘1→2→3` | `固定期間的我的轉盤1` / `切換我的轉盤1` / `我的轉盤1→2→3` | `押す間マイダイヤル1` / `再押しマイダイヤル1` / `マイダイヤル1→2→3` | Active（在 `[Custom Key/Dial Set.]` Still/Movie 下绑定） |
| `_g` `0x614b` | `Fn Menu Settings` | `Fn菜单设置` | `Fn功能表設定` | `Fnメニュー設定` | Active：12 Still + 12 Movie 槽位（不支持 Reset） |
| `_g` `0x615e` | `Shooting Display` | `拍摄显示` | `拍攝顯示` | `撮影画面表示` | Active：`(Shooting) -> [Shooting Display]` 分组 |
| `_f` `0x6429` | `Live View Display Set.` | `实时取景显示设置` | `Live View顯示設定` | `ﾗｲﾌﾞﾋﾞｭｰ表示設定` | Active（仅 Still）：含 `0x7227` / `0x6552` / `0x700e` 3 项 |
| `_f` `0x7913` / `0x642f` | `Setting Effect ON` / `Setting Effect OFF` | `设置效果开` / `设置效果关` | `設定效果開` / `設定效果關` | `設定効果反映On` / `設定効果反映Off` | Active（`base` `0xe3c6`/`0xe3c7`；默认 `ON`，不可 Reset） |
| `_f` `0x6552` | `Exposure Effect` | `曝光效果` | `曝光效果` | `露出の効果反映` | Active：`Exposure Set. & flash` (`0x6bee`) / `Exposure Setting Only` (`0x762b`) |
| `_f` `0x700e` | `Frame Rate Low Limit` | `帧速率低速限制` | `幀率低速限制` | `ﾌﾚｰﾑﾚｰﾄ低速制限` | Active（默认 `Off`，**支持 Camera Settings Reset**） |
| `_f` `0x6f9d` / `0x7920` | `Grid Line Display` / `\ue662Grid Line Type` | `网格线显示` / `\ue662网格线类型` | `格線顯示` / `\ue662格線類型` | `ｸﾞﾘｯﾄﾞﾗｲﾝ表示` / `\ue662ｸﾞﾘｯﾄﾞﾗｲﾝの種類` | Active（Still/Movie/`S&Q`；仅机身 LCD，不混入 HDMI Clean Feed） |
| `_f` `0x78ae` / `0x715a` / `0x786c` | `Rule of 3rds Grid` / `Square Grid` / `Diag. + Square Grid` | `三等分线网格` / `方形网格` / `对角 + 方形网格` | `九宮格` / `方格` / `對角線+方格` | `3分割` / `方眼` / `対角+方眼` | Active（`base` `0xe809` / `0xe806` / `0xe807`；默认三等分） |
| `_g` `0x61fa` | `Color/Tone` | `颜色/色调` | `顏色/色調` | `カラー/トーン` | Active：`(Exposure/Color) -> [Color/Tone]` 分组 |
| `_f` `0x71af` | `Manage User LUTs` | `管理用户LUT` | `管理使用者LUT` | `ユーザーLUTの管理` | Active：`Import/Edit` (`0x6a05`) / `Delete All` (`0x6543`)；`User1..16` |
| `_f` `0x643e` | `Select LUT` | `选择LUT` | `選取LUT` | `LUT選択` | Active：`S-Log3` (`0x7783`) / `s709` (`0x6a3e`) / `709(800%)` (`0x79c2`) / `User1..16` |
| `_f` `0x680f` | `Embed LUT File` | `内置LUT文件` | `嵌入LUT檔案` | `LUTﾌｧｲﾙの埋め込み` | Active（`[Log Shooting Setting]` 下）：容器元数据内嵌；SD/SDHC 锁 `Off` (`_g` `0x61a0`) |
| `_f` `0x6095` / `0x6f6d` | `PPLUT${v1}` / `Basic Look` | `PPLUT${v1}` / `基础风格` | `PPLUT${v1}` / `基本外觀` | `PPLUT${v1}` / `基本ルック` | Active（`Picture Profile` 像素烘焙；Reset/Initialize 时重置 `PPLUT1..4`） |
