# 全球 Sony 实机情报 Wave 57（`ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01`：`[SteadyShot]` 5 轴防抖与主动模式锁死/手动焦距、`[Self-timer]` 静态与动态差异、`[Zebra]` Custom 1/2 IRE 算法与 4 色峰值 vs FX6 双寄存器斑马，以及 `[Network Streaming]` RTMP/RTMPS/SRT、流式录制与 FTP vs 零射频/Slot-1 保险库护栏）

- **日期**：`2026-11-17`
- **目标硬件基线**：Sony `ILME-FX3`（`Ver. 7.02`, `Linux 4.9.337-scel+`, `PRODUCT_MODEL_ALCIN_UUD`）vs `ILME-FX6`（`Ver. 6.01`, `PRODUCT_MODEL_CHAPLIN`）
- **权威一手信源**：官方 Sony `ILME-FX3` Help Guide（`helpguide.sony.net/ilc/2210/v1/en/` —— *SteadyShot (movie)*、*SteadyShot (still image)*、*SteadyShot Adjust.*、*Focal Length*、*Clear Image Zoom*、*Self-timer (Single/Cont.)*、*Selftimer during Bracket*、*Drive Mode*、*Audio signals*、*Parts and controls (Front side #8)*、*Zebra Display*、*Zebra Level*、*Peaking Display/Level/Color*、*Network Streaming*、*Movie Rec During Streaming*、*Airplane Mode*、*Setting Reset*），官方 Sony `ILME-FX3` FTP Help Guide（`helpguide.sony.net/di/ftp_2210/v1/en/`），Sony `ILME-FX6` Operating Instructions（`5-024-458-18 (1) GB`, Software Ver. 6.0），以及严格 `os.O_RDONLY` 本地 donor 二进制/字符串包交叉实证（`FX3 appFw.so`、`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc` 四语全量包、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 appFw.so`、`FX6 string_english.uxc` / `_2.uxc`）。
- **硬件安全态势**：严格只读本地 donor 分析（`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `raw_firmware_bytes_leaked = 0`）。下文严格区分 **`实测事实`**（含精确 UXC `resid16`、ELF `BKID_APP_*`/`VAL_*` 符号与官方文档条款）与 **`推断`**（含物理裁切测算、S-Log3 曝光工程阈值与 Tier-0 实验台护栏设计）。

---

## 核心结论速览（Executive Summary）

1. **子系统 1（`[SteadyShot]` 5 轴机身防抖 IBIS vs 无 IBIS 的 FX6）**：
   - **实测事实（FX3 Ver. 7.02 IBIS 真值与 `[Active]` 四重互斥锁）**：`MENU -> (Shooting) -> [Image Stabilization]`（`_g` `0x6214`）下暴露 Movie **`[SteadyShot]`**（`Active` / **`Standard`** 默认 / `Off`）、Still **`[SteadyShot]`**（**`On`** 默认 / `Off`）、**`[SteadyShot Adjust.]`**（**`Auto`** 默认 / `Manual`）与 **`[Focal Length]`**（默认 `8mm`，`FX3 appFw.so` 实测 **47 档** `8mm..1000mm` 枚举）。全部 4 项均**支持 `[Camera Settings Reset]`**。Movie `[Active]` 会收窄视角并锁定 `[Distortion Comp.] = Auto`，且在以下 4 种场景被系统锁死禁用：① 常规 Movie `[Rec Frame Rate] >= 119.88p / 100p`；② `S&Q` `[Frame Rate] >= 120fps / 100fps`；③ HDMI RAW 视频输出激活；④ `[De-Squeeze Display]` 启用（`VAL_HAITA_steadyshot_equip_with_body_setting_ratio_hdmi_vf_*` 在 `1.3x..2.0x` 下联动禁用）。
   - **实测事实（`[Dynamic active]` 缺席与 `[Clear Image Zoom]` 交互）**：`ilc/2210` 全站对 `Dynamic active` 零命中，`FX3 appFw.so` 的 `VAL_setting_movie_steadyshot_*` 仅含 `ACTIVE / STANDARD / OFF / INVALID`（无 `DYNAMIC_ACTIVE`，仅存休眠的 `MOVIE_STEADYSHOT_EXTENSIONS_HYBRID`）；`_f.uxc` 中 `0x741c`（`Dynamic active`）与 `0x65b5` 属于多机身共源的**休眠字符串**。`[Clear Image Zoom]` 同样在 `119.88p/100p` 或 `S&Q >= 120fps/100fps` 禁用，但文档未声明 CIZ 禁用标准/主动 SteadyShot（其视角裁切与 `[Active]` 叠加）。
   - **实测事实（FX6 对比）**：`FX6 appFw.so` 明文声明 `TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`，`FX6_1` `0x2fa5` 提示 `"The SteadyShot mechanism is fixed."`。`ILME-FX6` **无机身 IBIS**，仅支持镜头光学防抖 **OSS** 与机内记录 **6 轴陀螺仪元数据**供 *Catalyst Browse / Prepare* 后期防抖（启用 Catalyst 机内稳定前需关闭镜头 OSS）。
2. **子系统 2（`[Self-timer]` 静态与动态差异、LED #8 与 `[Audio signals]`）**：
   - **实测事实（FX3 Ver. 2.00..7.02 仍无 Movie `[Self-timer]`）**：官方 `ilc/2210` 在 `Shooting -> [Shooting Option]` 下并未开放动态视频自拍倒计时（仅含 `[Framing Settings]`）；尽管 `FX3 appFw.so` 与 `_f.uxc` 存在跨机型共源的**休眠符号**（`BKID_APP_setting_movie_self_timer`、`countdown_time` `0/3/5/10`、`repeat` `OFF/ON`；`_f` `0x7192`/`0x713d`/`0x697d`/`0x773f` `Rec Start delay: Off/3 s/5 s/10 s`、`0x792e`/`0x72ac` `Repetition`、`0x7902`），但均**未在 `ILME-FX3 Ver. 7.02` 激活**。
   - **实测事实（静态 `[Drive Mode]` 自拍定时与硬件交互）**：Still `Drive Mode`（`_g` `0x616e`，默认 `Single Shooting`，支持 `[Camera Settings Reset]`）包含 **`[Self-timer(Single)]`**（`10 sec` / `5 sec` / `2 sec`）与 **`[Self-timer(Cont)]`**（`10/5/2 Sec.` × `3/5 Img.` 共 6 档），另在 `[Bracket Settings]` 提供 **`[Selftimer during Bracket]`**（`Off` 默认 / `2/5/10 Sec`，支持 Reset）。倒计时期间前部 **#8 复合部件**（`AF illuminator / Self-timer lamp / Visible light and IR sensor`，独立于前端 REC 灯）闪烁，并配合 `(Setup) -> [Sound Option] -> [Audio signals]`（`On` / `Off`）发声（当 `[Silent Mode] = On` 或 Movie HDMI 音频输出开启时抑制提示音）。
   - **实测事实（FX6 对比）**：`ILME-FX6 Ver. 6.01` 无静态自拍定时（`FX6 appFw.so` 仅残存 `PID_SET_SELF_TIMER`），采用专业电影机流程 **`Project > Picture Cache Rec`**（预录制环形缓冲，与 Interval Rec / Simul Rec / Proxy 互斥且强制 Free Run TC）与 **`Project > Interval Rec`**（间隔帧率延时摄影，含 `Pre-Lighting`）。
3. **子系统 3（`[Zebra Display]` / Custom 1 & 2 IRE 算法与 4 色 `[Peaking]` vs FX6 双斑马）**：
   - **实测事实（FX3 Zebra 预设、Custom 1/2 算法与 Reset 行为）**：`MENU -> (Exposure/Color) -> [Zebra Display]`（`_f` `0x7852`）默认 `Off`，`[Zebra Level]`（`_f` `0x70d7`）默认 **`70`**（均**不支持 `[Camera Settings Reset]`**，需 `[Initialize]`）。预设档位含 `70 / 75 / 80 / 85 / 90 / 95 / 100 / 100+`（`_f` `0x6e39`/`0x71ba`）及 **`Custom1`**（`_f` `0x68aa`，默认模式 **`Std+Range`** `_f` `0x7500`：基准 `0..109%` ± 范围 `1..10%`）与 **`Custom2`**（`_f` `0x68ab`，默认模式 **`Lower Limit`** `_f` `0x612e`：下限 `0..109+`）。控制拨轮左键默认 `[Zebra Display Select]`。
   - **实测事实（4 色 `[Peaking]` 与清洁 HDMI 隔离）**：`MENU -> (Focus) -> [Peaking Display]` 默认 `Off`，`[Peaking Level]` 含 `High / Mid(默认) / Low`，`[Peaking Color]` 含 `Red / Yellow / Blue / White(默认)`，**均不支持 `[Camera Settings Reset]`**；控制拨轮右键默认 `[Peaking Display Select]`。官方 `ilc/2210` 明确 Zebra 与 Peaking **均不随清洁 HDMI 信号输出至外部监视器/录机**。
   - **实测事实（FX6 双寄存器斑马与颜色差异纠偏）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18` 与 `FX6 appFw.so`）的 `Monitoring > Zebra > Setting` 实为 **`Off / Zebra1 / Zebra2`** 三选一（**并非同时叠加双斑马 `Both`**）：`Zebra1`（`Level` 默认 `70%` ± `Aperture Level` 默认 `10%`，范围 `2%..20%`）与 `Zebra2`（`Level` 默认 `100%` 及以上）是两组可快速切换的独立寄存器。FX6 `Monitoring > Peaking > Color` 选项为 **`B&W / Red / Yellow / Blue`**（用 **`B&W`** 对应 FX3 的 `White`）。
   - **推断（S-Log3 / Cine EI 斑马与 LUT 陷阱）**：原始 `S-Log3` 下 18% 中灰 = `41%` IRE、90% 白 = `61%` IRE、高光裁切 ≈ `94%` IRE（故 `Custom1` 设 `Std+Range 41±1..2`，`Custom2` 设 `Lower Limit 94+` 或 `92+`；若误用 `107+` 将错过 S-Log3 截断预警）。且在 FX3 `Log Shooting` 开启 `Display LUT = On` 时，斑马测量的是**套用 LUT 后的显示信号**而非原始 S-Log3。
4. **子系统 4（`[Network Streaming]` RTMP/RTMPS/SRT、`[Movie Rec During Streaming]`、`[FTP Transfer Func.]` 与 Tier-0 实验台护栏）**：
   - **实测事实（FX3 Ver. 6.00+/7.02 原生网络推流与机内同录）**：路径为 `MENU -> (Network) -> [Streaming] -> [Network Streaming]`（`_f` `0x6cb2`），通过 Creators' App 写入协议配置，支持 **RTMP**（`H.264`）、**RTMPS**（SSL/TLS + `H.264`）与 **SRT**（`H.265/H.264` + **AES-128/AES-256**）。`[Output Img. Quality Set]`（`_f` `0x7065`）含 `High / Standard(默认) / Low / Custom`，支持 `4K(2160p) / 2K(1440p) / HD(1080p) / HD(720p)` 与 `59.94p / 50p / 29.97p / 25p`（**无 `23.98p/24p` 推流帧率**）。**`[Movie Rec During Streaming]`**（`_f` `0x79d5`，默认 `Disable`）开启后强制机内 `[Rec Frame Rate]` 与推流帧率一致，且在 `4K` 或 `2K 59.94p/50p` 推流时禁用机内 4K 记录。推流期间锁定进入 Movie 模式并禁用 Menu、Playback、FTP 与休眠。
   - **实测事实（FX3 FTP 与 Reset 边界）**：`[FTP Transfer Func.]`（`_f` `0x6317`）默认全关、`[Auto FTP Target]` = `Still Image`（Movie 可选 `All / Only Shot Mark`，默认 `Proxy Only`）、支持 Wi-Fi / Wired USB-LAN（`CDC-NCM`）/ USB Tethering 后台断点续传。全部 `(Network)` 项**不被 `[Camera Settings Reset]` 重置**，需 `[Initialize]` 或 `[Reset Network Set.]`（注：`[Reset Network Set.]` 保留 `[Airplane Mode] = On`）。
   - **实测事实（FX6 对比纠偏）**：`ILME-FX6 Ver. 6.01`（`5-024-458-18`）机内菜单**并未开放原生 QoS Streaming / RTMP / SRT 直推**（依赖 Monitor & Control、C3 Portal、FTP/SFTP/FTPES 自动/切片上传，或外接 `PDT-FP1` / `CBK-RPU7` / SDI 编码器）；但 `FX6 appFw.so` 与 `_2.uxc` 仍残留 `BKID_APP_RTMP_SETTINGS1..8_*`、`BKID_APP_SRT_SETTINGS1..8_*` 与 `QoS Streaming`（`0x51e6`/`0x5300`）等未激活的 XDCAM/FX9 同源休眠符号。
   - **推断（Tier-0 实验台双护栏）**：在 Stage-B/Tier-0 台架隔离下，强制 **`[Airplane Mode] = On`** 封死 `p12/p13` RF NVS 与 `wlan0`/BLE（`0` 无线发包），仅允许经由有线 `USB-LAN`（`CDC-NCM`）执行受控网络验证；同时当 `Slot 1` 挂载只读 Tier-0 恢复保险库时，开启 **`[Movie Rec During Streaming] = Enable`** 或任何指向 `Slot 1` 的 FTP 写入路径**必须 fail-closed 拦截并返回 `EROFS`（`errno 30`）/ `EOPNOTSUPP`**，确保 `slot1_data_sector_writes == 0`。

---

## 1. 子系统 1：`[SteadyShot]` 5 轴防抖（IBIS）、Active 模式锁死与手动焦距表

### 1.1 `ILME-FX3 Ver. 7.02` 菜单真值、Reset 边界与焦距枚举表（`实测事实`）

- **菜单路径**（`ilc/2210/v1/en/`）：`MENU` -> `(Shooting)` -> **`[Image Stabilization]`**（`_g` `0x6214`）。

| 菜单项（`ilc/2210`） | `FX3 Ver. 7.02` 实机可选项 | 出厂默认值 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC 实证与约束（`实测事实`） |
| :--- | :--- | :---: | :---: | :--- |
| **Movie `[SteadyShot]`** (`base` `0xe153`) | **`Active`** (`_f` `0x714f`) / **`Standard`** (`base` `0xe03b`) / **`Off`** (`base` `0xe297`) | **`Standard`** | **Can be reset** | `BKID_APP_setting_movie_steadyshot`；`VAL_setting_movie_steadyshot_MOVIE_STEADYSHOT_{ACTIVE,STANDARD,OFF,INVALID}`；`Active` 为光学 5 轴 + 电子裁切增强；`Standard` 为 5 轴纯机身（或配合 OSS 镜头）防抖 |
| **Still `[SteadyShot]`** (`base` `0xe153`) | **`On`** / **`Off`** (`base` `0xe297`) | **`On`** | **Can be reset** | `BKID_APP_setting_still_steadyshot`；`VAL_setting_still_steadyshot_STILL_STEADYSHOT_{ON,OFF,INVALID}`；若装用带防抖物理开关的 OSS 镜头，须通过镜头开关总控防抖启停 |
| **`[SteadyShot Adjust.]`** (`_f` `0x7880`) | **`Auto`** (`base` `0xe6da`) / **`Manual`** (`base` `0xe44c`) | **`Auto`** | **Can be reset** | `BKID_APP_setting_steadyshot_adjustment`；无电子触点老镜头/手动转接环须设为 `Manual` 并配合手动焦距输入 |
| **`[Focal Length]`** (`_f` `0x65b1`, `SteadyS. Focal Len.` `_f` `0x625a`) | **47 档固定焦距**（`8mm` .. `1000mm`） | **`8mm`** | **Can be reset** | `BKID_APP_setting_steady_focal_length`；`FX3 appFw.so` 实测精确 **47 档**枚举：`8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 28, 30, 32, 35, 40, 45, 50, 55, 60, 70, 75, 80, 85, 90, 100, 105, 120, 135, 150, 180, 200, 210, 250, 300, 350, 400, 450, 500, 600, 800, 1000` mm |

### 1.2 `[Active]` 裁切/锁死矩阵、`[Clear Image Zoom]` 与 `[Dynamic active]` 休眠字符串甄别

1. **Movie `[Active]` 模式四重锁死与互斥（`实测事实`）**：
   - `ilc/2210`（*SteadyShot (movie)*）明确规定选择 `[Active]` 时：**视角会变窄**（*angle of view becomes narrower*），且 `[Distortion Comp.]` 自动强制为 `[Auto]`。
   - 以下 **4 种条件会直接锁死禁用 `[Active]`**（前 3 项载于 `ilc/2210`，第 4 项由本仓 ELF HAITA 枚举实证）：
     1. 常规 Movie 模式下 **`[Rec Frame Rate]` 设为 `119.88p` 或 `100p`**（及更高）；
     2. `S&Q` 模式下 **`[Frame Rate]` 设为 `120fps` / `100fps`**（或更高，含 `240fps/200fps`）；
     3. 开启 **HDMI RAW 视频输出**（`[RAW Output] = On`）；
     4. 开启变形宽银幕 **`[De-Squeeze Display]`**（`FX3 appFw.so` 中 `VAL_HAITA_steadyshot_equip_with_body_setting_ratio_hdmi_vf_*` 覆盖 `1_3X / 1_5X / 1_65X / 1_8X / 2_0X`，启用反挤压显示时防抖退回禁用态）。
2. **`[Active]` 精确裁切系数区分（`实测事实` vs `推断`）**：
   - **`实测事实`**：Sony 官方 `ilc/2210` 手册与 `FX3` UXC 仅定性描述「视角变窄（angle of view becomes narrower）」，**未在官方规格表中印出具体小数倍率**。
   - **`推断`**：结合 FX3 `12.1MP`（视频有效水平像素约 `4240 px`）与 `Active` 模式电子防抖冗余边界的实拍测算，FX3 `[Active]` 视角裁切系数约为 **`1.104×`**（约 `1.1×`，等效保留 `3840 px` 中心区域作 4K `1:1` 像素采样移动，远小于早期机型的 1.2×–1.5×）。
3. **`[Clear Image Zoom]`（清晰影像缩放）交互（`实测事实`）**：
   - 路径：`MENU -> (Shooting) -> [Zoom] -> [Zoom Range] -> [Clear Image Zoom]`（默认 `Optical zoom only`）。`ilc/2210` 在 `[Clear Image Zoom]` 限制条件中规定：当常规 Movie 为 `119.88p/100p` 或 `S&Q` 为 `120fps/100fps` 以上（以及静态拍摄选 `RAW` / `RAW+JPEG/HEIF`）时，Clear Image Zoom **同样不可用**；启用 Clear Image Zoom 时会禁用 `[Focus Area]`、`[Face/Eye Prior. in AF]`、`[Tracking]` 并将 `[Metering Mode]` 锁定为 `[Multi]`。Sony 文档将 SteadyShot 列为并行独立调节项（未禁止 `CIZ` 与 `SteadyShot` 共存），但启用 `[Active]` 时其裁切会与 CIZ 数字缩放率叠加（`推断`：高倍率叠加将进一步降低边缘信噪比）。
4. **`[Dynamic active]` 在 FX3 上的真实缺席与休眠字符串甄别（`实测事实`）**：
   - 官方 `ilc/2210` 全站对 `Dynamic active` **零命中**；`FX3 appFw.so` 中 `VAL_setting_movie_steadyshot_*` 枚举集合**不存在 `DYNAMIC_ACTIVE`**（仅存在极早期架构预留的 `VAL_setting_movie_steadyshot_extensions_MOVIE_STEADYSHOT_EXTENSIONS_HYBRID`）。
   - `FX3 string_*_f.uxc` 中虽然包含 `0x741c`（`Dynamic active` / `动态增强` / `動態積極` / `ﾀﾞｲﾅﾐｯｸｱｸﾃｨﾌﾞ`）与 `0x65b5`（比 `Active` 更强但视角更窄的步行防抖说明），但这属于 `ZV-E1` / `FX2` / `Alpha` 共源 UI 字符串包带入的**休眠字符串**，在 `ILME-FX3 Ver. 7.02` 实机上**完全不可达**。

### 1.3 `ILME-FX3` vs `ILME-FX6 Ver. 6.01` 防抖架构对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` (`ALCIN_UUD`) | `ILME-FX6 Ver. 6.01` (`CHAPLIN`, `5-024-458-18`) |
| :--- | :--- | :--- |
| **机身传感器位移 IBIS** | **内置 5 轴机身防抖**（Pitch/Yaw/Roll/X/Y） | **无 IBIS 硬件**（`FX6 appFw.so`：`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`；`FX6_1` `0x2fa5` `"The SteadyShot mechanism is fixed."`） |
| **机内防抖模式** | Still `On/Off`；Movie `Active / Standard / Off` | 仅支持带光学防抖的 **E 卡口 OSS 镜头**（`Technical > Lens > SteadyShot` 或镜头物理开关；`FX6_2` `0x5232` `OSS Information`）；机内亦存休眠的 `Dynamic Active`（`FX6_1` `0x308f`/`0x30ab`）共源字符串 |
| **手动镜头焦距配置** | `[SteadyShot Adjust.] = Manual` + **47 档 `[Focal Length]` (`8..1000mm`)** | 无机内手动防抖焦距表 |
| **陀螺仪元数据与后期防抖** | 支持机内记录陀螺仪元数据（建议关闭 IBIS 或使用特定模式配合 *Catalyst Browse / Prepare*） | **全系机内记录 6 轴陀螺仪元数据**（`gyro` 随 XAVC MXF 写入），供 *Catalyst Browse / Prepare* 后期防抖（`5-024-458-18` 提示使用 Catalyst 后期稳定时需**关闭镜头 OSS**） |

---

## 2. 子系统 2：`[Self-timer]` 静态与动态差异、LED #8 与 `[Audio signals]`

### 2.1 FX3 Ver. 2.00..7.02 动态自拍缺席验证与休眠 ELF 符号（`实测事实`）

- **官方 `ilc/2210` 实证**：检查 `ILME-FX3` Ver. 7.02 官方手册 `Shooting -> [Shooting Option]` 节点，该分组下仅开放了 `[Framing Settings]`（自动构图相关）等项，**自 Ver. 1.00 直至 Ver. 7.02 均未面向 FX3 开放 Movie `[Self-timer]`（动态录制倒计时）**（对比之下，同期 `ILCE-6700`、`ZV-E1`、`ILCE-1M2` 等消费级/Vlog 机型在 `Shooting Option` 下拥有独立的 Movie `[Self-timer]`）。
- **`FX3 appFw.so` 与 `_f.uxc` 休眠符号甄别**：
  - `FX3 appFw.so` 中确实存在 `BKID_APP_setting_movie_self_timer`、`BKID_APP_setting_movie_self_timer_countdown_time`（`0 / 3 / 5 / 10`）与 `BKID_APP_setting_movie_self_timer_repeat`（`OFF / ON`）；
  - `FX3 string_*_f.uxc` 亦存在 `0x7192`（`Rec Start delay: Off`）、`0x713d`（`3 s`）、`0x697d`（`5 s`）、`0x773f`（`10 s`）、`0x792e`（`Repetition`）、`0x68f0`（`Only Once`）、`0x72ac`（`Repeat`）及 `0x7902`（`Keeps Self-timer "On" after movie recording stops.`）。
  - **结论**：上述符号与字符串均为 Sony 多机型共用固件底座的**未激活休眠资产**，严禁在 FX3 UI 模拟器或菜单审计中误判为可启用项。

### 2.2 静态 `[Drive Mode]` 自拍定时、硬件 LED #8 与 `[Audio signals]` 联动（`实测事实`）

- **菜单路径**（`ilc/2210`）：`MENU -> (Shooting) -> [Drive Mode]`（`_g` `0x616e`），仅适用于静态照片（Still）。

| 菜单项（`ilc/2210`） | 可选枚举与默认值 | `[Camera Settings Reset]` | UXC `resid16` 与 `FX3 appFw.so` / 硬件交互（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Drive Mode]` -> `[Self-timer(Single)]`** | **`10 sec`** / **`5 sec`** / **`2 sec`**<br>（`Drive Mode` 默认 `Single Shooting`） | **Can be reset** | `BKID_APP_setting_drive_mode_self_timer` / `BKID_APP_setting_self_timer_option_self_timer_single`；`_f` `0x6772`/`0x6e8a`（标题）、`0x6b41`（10s）、`0x6d25`（5s）、`0x6eec`（2s）；`base` `0xe5de` / `0xea3a` |
| **`[Drive Mode]` -> `[Self-timer(Cont)]`** | **6 档组合**：`10 Sec. 3 Img.` / `10 Sec. 5 Img.` / `5 Sec. 3 Img.` / `5 Sec. 5 Img.` / `2 Sec. 3 Img.` / `2 Sec. 5 Img.` | **Can be reset** | `BKID_APP_setting_drive_mode_cont_self_timer` / `BKID_APP_setting_self_timer_option_cont_self_timer`；`_f` `0x728c`（`base` `0xe6e7`）、`base` `0xea3b`/`0xea3c`（10s 3/5 张）、`_f` `0x6566`/`0x760f`（5s 3/5 张）、`_f` `0x65d9`/`0x669a`（2s 3/5 张） |
| **`[Bracket Settings]` -> `[Selftimer during Bracket]`** | **`Off`**（默认） / `2 Sec` / `5 Sec` / `10 Sec` | **Can be reset** | `BKID_APP_setting_bracket_self_timer`；`VAL_setting_bracket_self_timer_BRACKET_SELF_TIMER_{OFF,2SEC,5SEC,10SEC}`；`_f` `0x6ef5` |
| **休眠自拍变体（非 FX3）** | *Single Burst Self-timer* / *Self-portrait 3-sec* | — | `_f` `0x758b`（`Single Burst Self-timer`）与 `BKID_APP_setting_drive_mode_self_portrait`（`base` `0xe5b2`/`0xe8de`、`_f` `0x70b8` 翻转屏 180° 3 秒自拍）均为其它机型休眠残留 |

- **前部硬件部件 `#8` 与 `[Audio signals]` 联动（`实测事实`）**：
  1. **前部 `#8` 指示灯物理复用**：依据 `ilc/2210` *Parts and controls (Front side)*，FX3 机身正面左上角部件 **#8** 为 **`AF illuminator / Self-timer lamp / Visible light and IR sensor`** 三合一模块（与机身前端红色 `Recording lamp` 物理分离）。触发静态自拍定时后，**#8 自拍指示灯高频闪烁**并配合蜂鸣倒计时（最后 2 秒闪烁/鸣响加速）；倒计时期间再次按下快门可中途取消。
  2. **`[Audio signals]` 真实菜单边界**：路径为 `MENU -> (Setup) -> [Sound Option] -> [Audio signals]`（`_g` `0x6110`，`base` `0xe0c8`，`BKID_APP_setting_audio_signals`，不支持 `[Camera Settings Reset]`）。`ilc/2210` 实机仅暴露 `On` / `Off`（`FX3 appFw.so` 中亦存在 `AUDIO_SIGNALS_{SHUTTER,SHUTTER_OFF}` 及休眠的 `_f` `0x7637` `Audio Signal(Start/End)` / `_f` `0x7af6` `Audio Signal Volume` —— 注意实测 `_f` `0x6d1d` 与 `0x7af6` 的简/繁体中文 UXC 字符串均为空 `''`，进一步印证其未向 FX3 UI 暴露）。当 `Shooting -> [Shutter/Silent] -> [Silent Mode] = On` 时，`[Audio signals]` 自动抑制为无声；Movie 录制且启用 HDMI 音频输出时（`_f` `0x6c92`），同样停止播放操作提示音。

### 2.3 `ILME-FX6 Ver. 6.01` 预录与延时摄影替代机制（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18`) |
| :--- | :--- | :--- |
| **静态 / 动态自拍** | Still 支持 `Self-timer(Single/Cont)` 与 `Selftimer during Bracket`；**无 Movie Self-timer** | **完全无 Still Drive Mode 与自拍定时**（`FX6 appFw.so` 仅残存 `PID_SET_SELF_TIMER`）；无前部自拍灯 |
| **电影机延迟/捕捉机制** | 依赖遥控器（RMT-P1BT / Creators' App）触发 Movie REC | **`Project > Picture Cache Rec`**（`BKID_APP_SETTING_PICTURE_CACHE_REC`，`On/Off`：环形缓存预录，按下 REC 回写触发前数秒；与 Interval Rec、双卡 Simul Rec、Proxy 互斥并强制 `Free Run` 时间码）<br>**`Project > Interval Rec`**（`BKID_APP_SETTING_INTERVALTIME_INTERVAL_REC` `1s..24h` + `NUMBER_OF_FRAMES_INTERVAL_REC` `1/2/4/3/6/12/24/9` 帧；支持 **`Pre-Lighting`** `Off/2s/5s/10s`） |

---

## 3. 子系统 3：`[Zebra Display]` / `[Zebra Level]`（Custom 1/2）与 4 色 `[Peaking]` vs FX6 双斑马

### 3.1 FX3 `[Zebra Display]`、`Custom 1/2` 算法与 `[Peaking]` 真值（`实测事实`）

- **Zebra 菜单路径**：`MENU -> (Exposure/Color)`（`_g` `0x609a`）-> **`[Zebra Display]`**（`_g` `0x6352`，`_f` `0x7852`）。
- **Peaking 菜单路径**：`MENU -> (Focus)`（`_g` `0x6419`）-> **`[Peaking Display]`**（`_g` `0x6050`，`_f` `0x6fe5`；支持 MF、DMF 及电影 AF 模式）。

| 菜单项（`ilc/2210`） | 可选范围与默认值 | `[Camera Settings Reset]` | `FX3 appFw.so` / UXC `resid16` 与默认按键（`实测事实`） |
| :--- | :--- | :---: | :--- |
| **`[Zebra Display]`** | `On` / **`Off`**（默认） | **Not available** *（需 `[Initialize]`）* | `BKID_APP_setting_zebra_display`；控制拨轮 **左键 (`Left Button`) 默认绑定 `[Zebra Display Select]`**（`_f` `0x6e05`） |
| **`[Zebra Level]`** | 预设：**`70`**（默认）/ `75` / `80` / `85` / `90` / `95` / `100` / **`100+`**<br>自定义：**`Custom1`** / **`Custom2`** | **Not available** *（需 `[Initialize]`）* | `BKID_APP_setting_zebra_level`；`VAL_setting_zebra_level_ZEBRA_LEVEL_{70..100,100_PLUS,CUSTOM_1,CUSTOM_2}`；`_f` `0x70d7`、`0x6e39`/`0x71ba`（`100+`）、`0x68aa`（`Custom1`）、`0x68ab`（`Custom2`） |
| **`Custom1` / `Custom2` 参数** | **`Std+Range`**（基准 `0..109%`，范围 `±1%..±10%` 步进 `1%`）<br>**`Lower Limit`**（下限 `0..109+`） | **Not available** *（需 `[Initialize]`）* | `BKID_APP_zebra_level_custom_{1,2}_{type,standard,range,lower_limit}`；出厂默认 **`Custom1 = Std+Range`**（`_f` `0x7500`）、**`Custom2 = Lower Limit`**（`_f` `0x612e`，提示 `_f` `0x7970` `Lower Limit: ${v1}+`），但两组均可自由切换 `Std+Range` 或 `Lower Limit` |
| **`[Peaking Display]`** | `On` / **`Off`**（默认） | **Not available** *（需 `[Initialize]`）* | `BKID_APP_setting_peaking_display`；控制拨轮 **右键 (`Right Button`) 默认绑定 `[Peaking Display Select]`**（`_f` `0x62a8`） |
| **`[Peaking Level]`** | `High` / **`Mid`**（默认） / `Low` | **Not available** *（需 `[Initialize]`）* | `BKID_APP_setting_peaking_level`；`base` `0xe078`（`High`）/ `0xe06d`（`Mid`）/ `0xe06e`（`Low`）；`_f` `0x6617`/`0x776f` |
| **`[Peaking Color]`** | `Red` / `Yellow` / `Blue` / **`White`**（默认） | **Not available** *（需 `[Initialize]`）* | `BKID_APP_setting_peaking_color`；`base` `0xe8c6`（`Red`）/ `0xe14e`（`Yellow`）/ `0xe883`（`White`）与 `_f` `0x7494`（`Blue`）；`_f` `0x67a5`/`0x7548` |

- **清洁 HDMI 输出隔离（`实测事实`）**：Sony `ilc/2210` 在 *Zebra Display* 与 *Peaking Display* 条目中明确注明：**斑马线与峰值对焦辅助轮廓均不会通过 HDMI 输出到外部监视器/录机（仅显示在机身屏幕）**。

### 3.2 `S-Log3` / `Cine EI` IRE 工程参考与 `Display LUT` 测量陷阱（`推断`）

- **S-Log3 原始 IRE 参考标定（`推断`，基于 Sony S-Log3 传递函数标准）**：
  - 在关闭查看 LUT（`[Display LUT] = Off`）或 PP 模式下关闭 `[Gamma Disp. Assist]` 观察原始 `S-Log3` 信号时：**18% 中灰 = `41%` IRE**，**亚洲/白皙肤色常落于 `48%–60%` IRE**，**90% 白卡 = `61%` IRE**，而 **S-Log3 满阱高光裁切平台位于 `~94%` IRE**（对应 10-bit 码值约 `964–970`，达不到 100%+）。
  - 工程推荐配置：将 **`Custom1`** 设为 `Std+Range`（`41 ± 1%` 或 `41 ± 2%` 用于精确锁定 18% 灰卡；或 `55 ± 5%` 监控肤色），将 **`Custom2`** 设为 `Lower Limit`（**`94+`** 或安全余量 **`92+` / `93+`**）作为原始 S-Log3 过曝警报。**若在原始 S-Log3 下错误套用 `107+` / `109+`（适用于 Rec.709 超白或 S-Log2），斑马线在高光完全死白前都不会触发**。
- **`[Display LUT] = On` 测量点切换（`实测事实` + `推断`）**：在 `Log Shooting` 模式下开启 `[Display LUT] = On`（例如 `s709` 或 `709(800%)`）时，FX3 机身斑马线转而采样**经过 LUT 映射后的监看亮度信号**而非底层 S-Log3（此时 `70` 或 `95/100+` 更接近常规 Rec.709 经验，需避免用 S-Log3 的 `41%` 标尺误判 `s709` 画面）。

### 3.3 `ILME-FX6 Ver. 6.01` `Zebra1 / Zebra2` 双寄存器与 `Peaking` 对比（`实测事实`）

| 对比维度 | `ILME-FX3 Ver. 7.02` | `ILME-FX6 Ver. 6.01` (`5-024-458-18` + `FX6 appFw.so`) |
| :--- | :--- | :--- |
| **斑马显示切换方式** | `[Zebra Display]` = `On / Off` + `[Zebra Level]`（`70..100+`, `Custom1`, `Custom2`） | **`Monitoring > Zebra > Setting`**：`Off` / **`Zebra1`** / **`Zebra2`**（`VAL_setting_infra_zebra_display_ZEBRA_DISPLAY_{OFF,ZEBRA1,ZEBRA2}`）——**实证纠偏：FX6 亦为单选切换 `Zebra1` 或 `Zebra2`，并非同屏双显示（无 `Both` 枚举）** |
| **两组自定义 IRE 数学** | `Custom1` 与 `Custom2` 均可独立设为 `Std+Range`（`0..109 ± 1..10%`）或 `Lower Limit`（`0..109+`） | **`Zebra1`** 固定为区间窗：**`Zebra1 Level`**（`0%..109%`，默认 `70%`）± **`Zebra1 Aperture Level`**（`2%..20%`，默认 `10%`，`FX6_1` `0x270e`）；<br>**`Zebra2`** 固定为下限阈值：**`Zebra2 Level`**（`0%..109%`，默认 `100%` 及以上，`FX6_1` `0x270f`）；（注：`FX6 appFw.so` 另存休眠的 Alpha `ZEBRA_LEVEL_CUSTOM_1/2` 符号） |
| **峰值颜色与高级调节** | `Peaking Level`（`High/Mid/Low`）；`Peaking Color`（`Red/Yellow/Blue/White`） | `Monitoring > Peaking`：`Setting`（`On/Off`）、`Peaking Level`（`High/Mid/Low`）、**`Color`（`B&W / Red / Yellow / Blue`——用 `B&W` 对应 FX3 `White`）**；另有高级微调项 `Peaking Type`、`Normal Peaking Frequency`、`Color Peaking Level`（`FX6_2.uxc`） |

---

## 4. 子系统 4：`[Network Streaming]`、`[FTP Transfer Func.]` 与 Tier-0 实验台护栏

### 4.1 `ILME-FX3 Ver. 6.00+/7.02` `[Network Streaming]` 协议、码率矩阵与互斥锁（`实测事实`）

- **精确菜单路径**（`ilc/2210`）：`MENU -> (Network)`（`_g` `0x6131`）-> **`[Streaming]`**（`_g` `0x618d`/`0x62f8`）-> **`[Network Streaming]`**（`_f` `0x6cb2`）。目标推流 URL、Stream Key 与协议须先经 **Creators' App**（BLE 配对写入）注册至相机。
- **支持协议与音视频封装**（`ilc/2210` + `FX3 appFw.so`）：
  - **RTMP**：明文推流，视频强制 `H.264/AVC`（`STREAM_OUTPUT_ERROR_TYPE_RTMP_KEY_NG`）；
  - **RTMPS**：`rtmps://` SSL/TLS 加密，视频 `H.264/AVC`；
  - **SRT**：支持 `H.265/HEVC` 或 `H.264/AVC`，支持 **AES-128 / AES-256** 加密及 Passphrase（`STREAM_OUTPUT_ERROR_TYPE_SRT_KEY_NG`）；
  - **音频统一规格**：AAC `48 kHz, 16-bit, 2ch`。

| `[Network Streaming]` 子项 | `FX3 Ver. 7.02` 可选值与默认值 | UXC `resid16` / ELF 符号与行为规则（`实测事实`） |
| :--- | :--- | :--- |
| **`[Streaming]`** | `On` / **`Off`**（默认） | `BKID_APP_setting_movie_network_streaming_streaming`；置 `On` 即按当前配置发起连接（支持 Wi-Fi / 有线 USB-LAN / USB Tethering） |
| **`[Stream Connect Error Display]`** | 默认 `―` | `_f` `0x7064`；显示当前网络流连接错误详情 |
| **`[Output Img. Quality Set]`** | `High` / **`Standard`**（默认） / `Low` / `Custom` | `_f` `0x7065`；`BKID_APP_setting_delivery_image_quality_set_{image_quality,resolution,frame_rate}`；`DELIVERY_IMAGE_QUALITY_SET_IMAGE_QUALITY_{FINE,STANDARD,LOW,CUSTOM}` |
| **`Custom` 分辨率与帧率** | 分辨率：`4K (2160p)` / `2K (1440p)` / `HD (1080p)`（默认）/ `HD (720p)`<br>帧率：`59.94p` / `50p` / `29.97p` / `25p` | **关键帧率边界**：`VAL_setting_delivery_image_quality_set_frame_rate_*` **仅含 `25P / 30P(29.97p) / 50P / 60P(59.94p)`，不支持 `23.98p / 24p` 原生电影帧率推流**；各档推荐/默认码率（`ilc/2210`）：`4K 59.94/50p`=`38 Mbps`、`4K 29.97/25p`=`38–13 (默认34)`、`2K 59.94/50p`=`38–9 (默认18)`、`2K 29.97/25p`=`38–6 (默认13)`、`1080p 59.94/50p`=`27–4.5 (默认9)`、`1080p 29.97/25p`=`18–3 (默认6)`、`720p 59.94/50p`=`13.5–2.3 (默认6)`、`720p 29.97/25p`=`9–1.5 (默认4) Mbps` |
| **`[Output Information Display]`** | 默认 `―` | `_f` `0x7a33`；推流开始后查看实时分辨率、帧率与连接状态 |
| **`[Movie Rec During Streaming]`** | `Enable` / **`Disable`**（默认） | `_f` `0x79d5`；`BKID_APP_setting_movie_network_streaming_movie_rec_dur_distribution`；推流中不可更改；**开启后强制将机内 `[Rec Frame Rate]` 锁定为推流帧率**；当推流为 **`4K`** 或 **`2K 59.94p/50p`** 时，机内 `[File Format]` 禁止选 4K 格式（只能录 HD）；注：无法触发 `S&Q` 录制 |
| **`[Emphasized Output Display]`** | **`On`**（默认） / `Off` | `_f` `0x6661`；在监看画面外框高亮显示流媒体输出状态 |
| **`[Root Certificate Error]`** | **`Does Not Connect`**（默认） / `Connect` | `_f` `0x65f2`；`BKID_APP_setting_movie_network_streaming_root_certificate_error` |

- **推流期间全系统互斥（`实测事实`）**：推流激活时，相机自动切换至动态影像模式，并**禁用 Menu 菜单、Playback 回放、`[FTP Transfer]`、Remote Shooting、Cloud Connection、Smartphone Transfer 及 `[Power Save Start Time]` 自动关机**。

### 4.2 `[FTP Transfer Func.]` 机制、Reset 边界与 `ILME-FX6` 对比（`实测事实`）

- **FX3 `[FTP Transfer Func.]`（`ftp_2210`）**：
  - 路径：`MENU -> (Network) -> [FTP Transfer]`（`_g` `0x64bf`）-> **`[FTP Transfer Func.]`**（`_f` `0x6317`），全部设置存储于 `(Network)` 分区。
  - 默认值：`[FTP Function] = Off`、`[Server Setting] = Server 1`、`[Auto FTP Transfer] = Off`、`[Auto FTP Target] = Still Image`（动态选项：`All` / `Only Shot Mark`）、`[RAW+J/H Transfer Target] = JPEG & HEIF`、`[Transfer Target]`（动态文件）= `Proxy Only`、`[FTP Power Save] = Off`；批量传输过滤器默认 `This Date` / `All`（支持 `This Media`、`This Folder`、`Only Non-transfer`、`Only Failed Transfer`、Ver. 7.00+ 新增 `Clip Flag` 与 `Rating/Protect` 过滤）。
  - 支持 Wi-Fi、有线 USB-LAN（`CDC-NCM`）及 USB Tethering，仅被动模式（Passive Mode），后台任务在切回拍摄/回放乃至开关机后均可断点续传（拔卡、断电或切换 USB MSC 除外）。
- **Reset 生存规则（`ilc/2210` *Setting Reset*）**：`(Network)` 下的 `[Network Streaming]`、`[FTP Transfer Func.]` 与 `[Airplane Mode]` **均不被 `[Camera Settings Reset]` 重置**；须使用 **`[Initialize]`** 或 **`[Reset Network Set.]`**（且 `[Reset Network Set.]` 特别保留 **`[Airplane Mode] = On`** 状态不被清除）。
- **`ILME-FX6 Ver. 6.01` 流媒体与 FTP 对比（`实测事实`）**：
  - 官方 `ILME-FX6` 手册（`5-024-458-18` Ver. 6.0）证实 FX6 机内 `[Network]` **并不提供原生内置 QoS Streaming、RTMP/RTMPS 或 SRT 直推**（现场联网以 Wi-Fi / USB-LAN / USB Tethering 对接 *Monitor & Control*、*C3 Portal / Ci Media Cloud* 及 **FTP/SFTP/FTPES 自动/分段切片上传 Auto Upload / Chunk** 为主；若需 QoS/RTMP/SRT 直播需外接 `PDT-FP1`、`CBK-RPU7` 或独立推流编码器）。
  - 但 `FX6 appFw.so` 与 `FX6 string_english_2.uxc` 实测带有跨 XDCAM/FX9 共源的**休眠符号**：`BKID_APP_RTMP_SETTINGS1..8_*`、`BKID_APP_SRT_SETTINGS1..8_*`、`QoS Streaming`（`0x51e6`/`0x5300`）、`Intelligent QoS`（`0x52e8`）与 `Streaming Type`（`0x5044`/`0x51da`），在 `CHAPLIN` 实机上未激活。

### 4.3 Tier-0 实验台双防线护栏（零射频隔离 + `Slot-1` Vault `EROFS=30` 防写）（`推断`）

结合本实验室网络桥接审计规范（参见 [`realhw_wifi_bt_usb_uvc_network_bridge_auditor.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h357-global-sony-wave57-steadyshot-ibis-movie-selftimer-custom-zebra-streaming-intel/outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_wifi_bt_usb_uvc_network_bridge_auditor.py)）与 `Slot-1` Tier-0 恢复保险库契约，面对 `Network Streaming` 与 `FTP` 必须落地以下两道 fail-closed 护栏：

1. **强制零射频隔离（`[Airplane Mode] = On` / `P12/P13` 只读锁死）**：
   - `MENU -> (Network) -> [Network Option]`（`_g` `0x61e1`）-> **`[Airplane Mode]`**（`_f` `0x6b05`/`0x6df9`，默认 `Off`，`BKID_APP_setting_airplane_mode`）。
   - 在台架 / Stage-B 环境中强制预设 `Airplane Mode = On`，彻底屏蔽 2.4/5 GHz `wlan0` 与 BLE HCI TX（`rf_nvs_p12_p13_writes_permitted == False`、`rf_nvs_mutation_bytes == 0`），并将所有允许的推流或 FTP 校验流量严格限定在**有线 `USB-LAN`（`CDC-NCM`）** 通道上运行；同时依赖 `[Reset Network Set.]` 保留 `Airplane Mode = On` 的特性防止误复位泄漏射频。
2. **`Slot-1` Tier-0 恢复保险库 `EROFS (30)` 阻断**：
   - 正常拍摄时 `[Auto FTP Transfer]` 读取 `[Recording Media]` 槽位，而手动 `[FTP Transfer]` 默认从 `[Select Playback Media]`（出厂默认 `Slot 1`）读取；当 **`[Movie Rec During Streaming] = Enable`** 且录制目标指向 `Slot 1` 时，系统会在推流同时向卡内写入 MP4/XAVC 媒体文件及 `AVF_INFO` 数据库。
   - **护栏规则**：只要 `Slot 1` 处于 Tier-0 只读恢复保险库挂载态，任何将 **`[Movie Rec During Streaming]` 设为 `Enable` 且目标为 `Slot 1`** 的录制/建库操作，或任何试探向 `Slot 1` 回写 FTP 临时/状态标记的 I/O，**必须 fail-closed 拦截并返回 `EROFS`（`errno 30`）/ `EOPNOTSUPP`**，严格保证 `slot1_data_sector_writes == 0` 且 `slot1_avf_info_mutated == False`。

---

## 5. `O_RDONLY` 本地 Donor 审计台账与 4 语 `resid16` 一致性矩阵（`raw_firmware_bytes_leaked = 0`）

### 5.1 本波次已审计本地 Donor 文件台账（严格 `os.O_RDONLY`）

| Donor 工件 | 大小 (`B`) | SHA-256 | Wave 57 实测命中符号 / 关键证据 (`os.O_RDONLY`) |
| :--- | ---: | :--- | :--- |
| `FX3 appFw.so` (`Ver. 7.02`) | `79,015,712` | `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f` | `BKID_APP_setting_{movie_steadyshot,still_steadyshot,steadyshot_adjustment,steady_focal_length}`, 47 档 `STEADYSHOT_FOCAL_LENGTH_8MM..1000MM`, `VAL_HAITA_steadyshot_equip_with_body_setting_ratio_hdmi_vf_*`, 休眠 `BKID_APP_setting_movie_self_timer*`, `BKID_APP_setting_{drive_mode_self_timer,drive_mode_cont_self_timer,bracket_self_timer,audio_signals}`, `BKID_APP_setting_{zebra_display,zebra_level,peaking_display,peaking_level,peaking_color}`, `BKID_APP_zebra_level_custom_{1,2}_{type,standard,range,lower_limit}`, `BKID_APP_setting_{movie_network_streaming_*,delivery_image_quality_set_*,ftp_*,airplane_mode}`, `STREAM_OUTPUT_ERROR_TYPE_{RTMP_KEY_NG,SRT_KEY_NG}` |
| `FX3 string_english_f.uxc` | `373,820` | `7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b` | 首条 `0x5eb4`，`7,475` 条（`0x6000..0x7d3d`）：`Active` (`0x714f`), 休眠 `Dynamic active` (`0x741c`), `SteadyShot Adjust.` (`0x7880`), `SteadyS. Focal Len.` (`0x625a`), `Self-timer(Single/Cont)` (`0x6772`/`0x728c`), `Selftimer during Bracket` (`0x6ef5`), 休眠 `Rec Start delay` (`0x7192`等), `Zebra Display` (`0x7852`), `Zebra Level` (`0x70d7`), `Std+Range` (`0x7500`), `Lower Limit` (`0x612e`), `Custom1/2` (`0x68aa`/`0x68ab`), `Peaking Display` (`0x6fe5`), `Blue` (`0x7494`), `Network Streaming` (`0x6cb2`), `Output Img. Quality Set` (`0x7065`), `Movie Rec During Streaming` (`0x79d5`), `FTP Transfer Func.` (`0x6317`), `Airplane Mode` (`0x6b05`/`0x6df9`) |
| `FX3 string_simplifiedchinese_f.uxc` | `322,652` | `4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a` | 首条 `0x5b60`，与 `EN` `7,475` 条 `resid16` 1:1 严格对齐（实测 `0x6d1d`/`0x7af6` 为空串） |
| `FX3 string_traditionalchinese_f.uxc` | `324,148` | `32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167` | 首条 `0x5b88`，与 `EN` `7,475` 条 `resid16` 1:1 严格对齐（实测 `0x6d1d`/`0x7af6` 为空串） |
| `FX3 string_japanese_f.uxc` | `447,840` | `45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b` | 首条 `0x62a4`，与 `EN` `7,475` 条 `resid16` 1:1 严格对齐 |
| `FX3 string_english.uxc` (`ns=39`) | `165,740` | `204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e` | `2,692` 槽（`0xe000..0xea83`）：`SteadyShot` (`0xe153`), `Standard` (`0xe03b`/`0xe651`), `Off` (`0xe297`/`0xe4dd`), `Auto/Manual` (`0xe6da`/`0xe44c`), `Drive Mode` (`0xe5d2`), `Audio signals` (`0xe0c8`), `Self-timer: 10/2 Sec` (`0xe5de`/`0xea3a`), `Self-timer(Cont.) 10 Sec. 3/5 Img.` (`0xea3b`/`0xea3c`), `High/Mid/Low` (`0xe078`/`0xe06d`/`0xe06e`), `Red/Yellow/White` (`0xe8c6`/`0xe14e`/`0xe883`) |
| `FX3 string_simplifiedchinese.uxc` | `149,064` | `34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese.uxc` | `151,908` | `be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_japanese.uxc` | `208,564` | `f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d` | 与 `EN` `2,692` 槽位 1:1 严格对齐 |
| `FX3 string_english_g.uxc` (`ns=3`) | `69,600` | `a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a` | `1,390` 条（`0x6000..0x6579`）：`Image Stabilization` (`0x6214`), `Drive Mode` (`0x616e`), `Sound Option` (`0x6110`), `Exposure/Color` (`0x609a`), `Zebra Display` (`0x6352`), `Focus` (`0x6419`), `Peaking Display` (`0x6050`), `Network` (`0x6131`), `Streaming` (`0x618d`/`0x62f8`), `FTP Transfer` (`0x64bf`), `Network Option` (`0x61e1`) |
| `FX3 string_simplifiedchinese_g.uxc` | `61,296` | `a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_traditionalchinese_g.uxc` | `61,372` | `97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3 string_japanese_g.uxc` | `89,428` | `4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980` | 与 `EN` `1,390` 槽位 1:1 严格对齐 |
| `FX3-CX95900_ALLLANG-Backup.bin` | `2,229,740` | `bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2` | 双 `BK4\x00` 偏移（`0xc` / `0xd200c`）数值 BKID 存储基线 |
| `FX6 appFw.so` (`Ver. 6.01`) | `50,520,424` | `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` | `TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`, `PID_SET_SELF_TIMER`, `BKID_APP_SETTING_{PICTURE_CACHE_REC,INTERVALTIME_INTERVAL_REC,INFRA_ZEBRA_DISPLAY}`, `VAL_setting_infra_zebra_display_ZEBRA_DISPLAY_{OFF,ZEBRA1,ZEBRA2}`, 休眠 `BKID_APP_{RTMP,SRT}_SETTINGS1..8_*` |
| `FX6 string_english.uxc` (`ns=1`) | `118,208` | `5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739` | `The SteadyShot mechanism is fixed.` (`0x2fa5`), `Zebra1`/`Zebra2` (`0x23a5`/`0x23a7`), `Peaking` (`0x31ef`), 休眠 `Dynamic Active` (`0x308f`) 与 `RTMP`/`SRT` 状态字串 |
| `FX6 string_english_2.uxc` (`ns=2`) | `118,676` | `3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2` | `OSS Information` (`0x5232`), `Zebra1 Level` (`0x4528`), `Zebra2 Level` (`0x4530`), `Peaking` (`0x423d`), `Picture Cache Rec` (`0x424c`), `Interval Rec` (`0x4247`), 休眠 `QoS Streaming` (`0x51e6`/`0x5300`) & `Intelligent QoS` (`0x52e8`) |

### 5.2 4 语 `resid16` 关键菜单与选项矩阵（`FX3 string_*_f.uxc` / `.uxc` / `_g.uxc`）

| Pack / `resid16` | EN | ZH-CN | ZH-TW | JA | 归属与实机激活状态 |
| :---: | :--- | :--- | :--- | :--- | :--- |
| `_g` `0x6214` | `Image Stabilization` | `影像稳定` | `影像穩定` | `手ブレ補正` | Active：`(Shooting) -> [Image Stabilization]` |
| `base` `0xe153` | `SteadyShot` | `SteadyShot` | `SteadyShot` | `手ブレ補正` | Active：Still `On/Off`；Movie `Active/Standard/Off` |
| `_f` `0x714f` | `Active` | `增强` | `積極` | `アクティブ` | Active：Movie `SteadyShot`（120p/RAW/De-Squeeze 时禁用） |
| `_f` `0x741c` | `Dynamic active` | `动态增强` | `動態積極` | `ﾀﾞｲﾅﾐｯｸｱｸﾃｨﾌﾞ` | **Dormant**（`ilc/2210` 零命中，`ZV-E1`/`FX2` 休眠字符串） |
| `_f` `0x7880` | `SteadyShot Adjust.` | `SteadyShot调整` | `SteadyShot調整` | `手ブレ補正調整` | Active：`Auto` (`0xe6da`) / `Manual` (`0xe44c`) |
| `_f` `0x625a` | `SteadyS. Focal Len.` | `SteadyS.焦距` | `SteadyS.焦距` | `手ブレ補正焦点距離` | Active：`8mm` 默认（47 档 `8..1000mm`） |
| `_g` `0x616e` | `Drive Mode` | `拍摄模式` | `過片模式` | `ドライブモード` | Active（`base` `0xe5d2`） |
| `_f` `0x6772` / `0x728c` | `Self-timer(Single)` / `Self-timer(Cont)` | `自拍定时（单张）` / `自拍定时(连拍)` | `自拍定時器（單張）` / `自拍(連拍)` | `ｾﾙﾌﾀｲﾏｰ（1枚）` / `ｾﾙﾌﾀｲﾏｰ（連続）` | Active（Still：10/5/2s 单张；10/5/2s × 3/5 张连拍） |
| `_f` `0x6ef5` | `Selftimer during Bracket` | `阶段曝光中自拍定时` | `包圍曝光時自拍定時` | `ﾌﾞﾗｹｯﾄ時のｾﾙﾌﾀｲﾏｰ` | Active：`Off / 2 / 5 / 10 Sec`（支持 Reset） |
| `_f` `0x7192` / `0x792e` | `Rec Start delay: Off` / `Repetition` | `录制开始延迟: 关` / `重复` | `錄製開始延遲: 關` / `重複` | `カウントダウン: しない` / `繰り返し` | **Dormant**（Movie Self-timer 未在 FX3 Ver. 7.02 激活） |
| `base` `0xe0c8` | `Audio signals` | `音频信号` | `提示音` | `電子音` | Active（`_g` `0x6110` `Sound Option` 下，`On/Off`） |
| `_f` `0x7852` / `0x70d7` | `Zebra Display` / `Zebra Level` | `斑马线显示` / `斑马线水平` | `斑馬紋顯示` / `斑馬紋等級` | `ゼブラ表示` / `ゼブラレベル` | Active（`_g` `0x6352`；不支持 Camera Settings Reset） |
| `_f` `0x68aa` / `0x68ab` | `Custom1` / `Custom2` | `自定义1` / `自定义2` | `自訂1` / `自訂2` | `カスタム1` / `カスタム2` | Active：默认 `Std+Range` (`0x7500`) / `Lower Limit` (`0x612e`) |
| `_f` `0x6fe5` / `0x7494` | `Peaking Display` / `Blue` | `峰值显示` / `蓝色` | `峰值顯示` / `藍色` | `ピーキング表示` / `ブルー` | Active（`_g` `0x6050`；`High/Mid/Low` + `Red/Yellow/Blue/White`） |
| `_f` `0x6cb2` | `\ue660Network Streaming` | `\ue660网络流式传输` | `\ue660網路串流傳輸` | `\ue660ﾈｯﾄﾜｰｸｽﾄﾘｰﾐﾝｸﾞ` | Active（`_g` `0x6131` -> `0x618d`/`0x62f8`；RTMP/RTMPS/SRT） |
| `_f` `0x7065` | `Output Img. Quality Set` | `输出影像质量设置` | `輸出影像品質設定` | `出力画質設定` | Active：`High/Standard/Low/Custom`（`59.94/50/29.97/25p`） |
| `_f` `0x79d5` | `Movie Rec During Streaming` | `流式传输动态影像录制` | `串流傳輸動態影像錄製` | `ｽﾄﾘｰﾐﾝｸﾞ時の動画記録` | Active：`Enable/Disable`（Slot-1 Vault 时需 `EROFS=30` 拦截） |
| `_f` `0x6317` / `0x7b27` | `FTP Transfer Func.` / `Auto FTP Transfer` | `FTP传输功能` / `自动FTP传输` | `FTP傳輸功能` / `自動FTP傳輸` | `FTP転送機能` / `FTP自動転送` | Active（`_g` `0x64bf`；不支持 Camera Settings Reset） |
| `_f` `0x6b05` / `0x6df9` | `Airplane Mode` | `飞行模式` | `飛航模式` | `飛行機モード` | Active（`_g` `0x61e1`；台架测试强制 `On` 隔离射频） |
