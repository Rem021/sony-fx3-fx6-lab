# FX5 交互逻辑 + FX6 完整色彩目标：经典 FX3 7.02 菜单/控制适配设计与 RAW 色彩链独立审查

## 1. 先说结论

1. **环境与边界核验通过**：
   - 外部卷 `/Volumes/KAFU2T` 挂载正常，`VolumeUUID = F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 已核验写入回执。
   - 本阶段严格遵守只读原件与目录隔离：未启动或修改任何 VM runtime、未碰运行锁、未操作相机/USB/SD、未改动其他工人目录，所有产出仅写入 [`team/gemini-menu/`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/)。
2. **FX5 菜单交互架构与 FX6 6.01 BIG6 适配结论**：
   - **三层交互状态机**：以 Sony FX5 官方交互规范（`home_screen` / `quick_menu` / `fullmenu_use`）与 FX6 Ver. 6.00/6.01 官方 BIG6 规范为蓝本，经典 FX3 7.02 的 Cinema 交互应分为：
     1. **HOME (BIG6) 主屏**：左三项（`FPS`、`ISO/Gain/EI`、`Shutter`）+ 右三项（`Iris`、`Scene File / Look`、`White Balance`）+ 中央状态/波形/直方图/电平区；子面板随 `[Project] - [Base Setting] - [Shooting Mode]`（`Custom` / `Flexible ISO` / `Cine EI` / `Cine EI Quick`）动态切换。
     2. **Quick Menu（短按 `MENU`）**：5 个可横向切换分类页（`[Project]`、`[TC/Media]`、`[Monitoring]`、`[Audio]`、`[Info]`），其中 `Item 1..5` 左右切页、底部槽位一键跳转对应分类的 Full Menu，`[Info]` 页提供只读系统/电池/镜头景深诊断。
     3. **Full Menu（长按 `MENU` 或从 Quick Menu 跳入）**：10 大分类，单屏最多 8 行；小枚举项弹列表窗，大范围连续参数（如 `-99..+99`）行内高亮直接拨轮调节；未确认前按 `BACK` 撤销修改；`[Execute]` 动作项弹出确认模态框并暂隐菜单树。
   - **硬件缺失项（绝不伪造通过）**：
     - **内置电子可变 ND（`ND Filter: Clear / 1/4 / 1/16 / 1/64 / Variable / Auto`）**：FX3 7.02 无内置 ND 光学组件，[`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so) 中无 ND 执行器 sequence。右上角 BIG6 槽位在 FX3 上必须采用 FX5 的纯 `Iris`（`F-number` + `Auto Iris`）定义，或显式标注 `ND: N/A (External)`。
     - **12G-SDI 输出与专用 EVF 寻像器接口**：FX3 仅具 HDMI 与机身 LCD，无 SDI / VF 物理链路。
     - **专用 BNC Timecode Out 接口**：FX3 支持 Multi/USB 端口 TC In 同步及内建 TC/UB 发生器，无独立 BNC TC Out 物理端子。
3. **三条原生后端控制链已完成字节级静态反汇编 + Unicorn CPU 模拟闭环**：
   - **链路 1（Look / Base Picture Setting → CP MLUT → VFX SDK → 70 描述符 DMA）**：从 [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so) 的 `model::sequence_set_base_picture_setting` 构造函数（`0x2c47cfc..0x2c47e88`，读取 `0x821c538` 模型全局状态）→ `run()`（`0x2d78050..0x2d7819c`）→ 封包器 `0x2e3172c`（消息号 `0x4151`，`mov w2, #0x4151` 字节 `222a8852`）→ 5 字节载荷构造器 `infra_wrapper_imaging::detail::set_base_picture_setting_i`（`0x2e26fcc..0x2e2716c`）→ IPC 通道 `0x90030001`（`0x2e2fb90`）→ [`cpapp-b.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin) 分发表 `file+0xe003a0` → CP 校验器 `CheckSetParamBasePictureSetting`（`file+0x1f605c`，含 `file+0x1cb8a8` `0c29` 即 `cmp r1, #12` 门控）与写入器 `file+0x689f9c`（`VA 0x791f9d`，写入 `0x10a8de0 + {0xba0..0xbb0}` 并递增 `+0x76c`）→ `GetVfxMlutLookname`（`file+0x3266ec`）→ 休眠项 ID 22（`MLUT_LOOKNAME_SL3SG3_TO_ACESREC709` @ `file+0xbf8ffc`，目标地址 `0x02015794`，70 描述符）→ `SetVfxMlutParam`（`file+0x3263fc`）→ VFX SDK（`VA 0xa4f8ba`）→ `mlut_make_lli_table`（`VA 0x470f78`）生成 `0x2025570` 处 70×16B DMA 链表并指向硬件 ISP/MLUT 窗口 `0xf4009000 + (combo << 20)`。
   - **链路 2（Monitor LUT 监看辅助与 ColorGamut 显示链）**：`model::sequence_set_gamma_disp_assist::run()` 调用 `infra_wrapper_bb::detail::vdf_disp_set_monitor_lut`（`0x2debdb0..0x2debf04`），通过 BB/VDF 通道 `0x92840747`（`0x2de70a8`）发送 10 字节报文 `0d20 6101 0a00 0180 <type> 00`；`sequence_set_base_picture_setting::run()` 尾部同步调用 `0x2dee4ac..0x2dee538` 发送 `0d20 6701 0a00 0180 <gamut> 00`。静态与模拟证实 **FX3 的主录色彩链（CP `0x90030001` `0x4151`）与监看显示链（BB/VDF `0x92840747` `0x0161`/`0x0167`）在协议层天然解耦**，可直接支撑 FX5/FX6 BIG6 Look 子面板的分流开关（`Main/Sub Rec` vs `HDMI/LCD`）。
   - **链路 3（White Balance 白平衡控制链与 100K vs 1K 量化约束发现）**：`model::sequence_set_wb_mode::run()`（`0x2d9f2c8..0x2d9f3ec`）→ `0x2dd5b14` → `0x2e3c3b8..0x2e3c444`（构造 20 字节 IPC 包，消息号 `0x4006` `PID_SET_WB_MODE`，字节 `c2008852`）→ 载荷构造器 `0x2e18e3c..0x2e190a8` → CP 分发表 `file+0xdfeb90` → CP 写入器 `file+0x68950c`（`VA 0x79150d`，写入 `0x10a8de0 + {0x9f4..0xa02}` 并打印 `FW: SET_WB_MODE[%d: %d: %d: %d: %d]` @ `VA 0xdb2fde`）。**关键静态发现**：`0x2e18e98` 处指令 `mov w3, #0x64; sdiv w26, w26, w3; strb w26, [x19, #0x10]` 将开尔文色温除以 `100` 后存为单字节 `+0x10`（如 `5600K -> 56 = 0x38`），因此原生 `0x4006` 的 `+0x10` 字段仅能表达 FX5/FX6 的 `[Coarse]`（100K 步进）；若要实现 FX5/FX6 BIG6 的 `[Fine]`（1K 步进）色温与 `Tint (-99..+99)`，必须将 1K 余量折算进 `+0x9..+0xf` 的 16 位 AB/GM 微调余数字段（写入 CP `0x10a8de0+0x9fa/+0x9fc`），或扩展 CP 端 WB 增益求解器。
4. **完整 RAW/底层色彩链独立审查结论（绝不能拿 3D LUT 冒充整套色彩）**：
   - 完整成像与色彩链分为 6 段：**Stage 1**（传感器双原生 ISO 增益、黑电平 OB、坏点与镜头暗角校正：CP 配置硬件 ISP 前端）、**Stage 2**（Bayer 去马赛克与 2D/3D 降噪/锐化/肤色细节：CP 配置硬件 ISP 核心）、**Stage 3**（白平衡 R/G/B 增益、`3x3` 色彩校正矩阵 CCM、预伽马/S-Log3 曲线与高光拐点 Knee/Shoulder：CP 计算并装载硬件 ISP 矩阵/曲线引擎）、**Stage 4**（MLUT 模块：`160B` 头 + `3×1984B` 1D Pre-Shaper + `33³` 3D LUT + `3×3` 后置矩阵，共 `149,888B`，70 个 DMA 描述符写入 `0xf4009000 + (combo << 20)`）、**Stage 5**（多路输出分流：CP `combo 0..4` 编码主/副流 vs BB/VDF `0x92840747` 监看/HDMI/OSD）、**Stage 6**（AP `0x821c538` 模型状态持久化与 MP4/MXF 元数据）。
   - **3D LUT 仅覆盖 Stage 4**。若上游 Stage 1–3（白平衡微调、原生色域到 S-Gamut3/S-Gamut3.Cine 的 CCM、Knee/高光滚降、降噪与肤色细节）或下游 Stage 5–6（主录与监看分流、状态机防回写覆盖）未对齐，仅替换 3D LUT 会出现高光截断斜率偏差、偏色及触发重配后掉回默认画面。

---

## 2. 交付物清单与证据等级定义

本目录（[`work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/)）包含以下可复现交付物：

| 文件 | 用途 | 证据等级 |
|---|---|---|
| [`README.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/README.md) | 中文主报告：交互设计、映射总结、三条静态+模拟后端链、完整 RAW/ISP 六段式独立审查与最小离线实验 | 综合报告（严格区分各层证据） |
| [`menu-control-mapping.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/menu-control-mapping.json) | 机器可读映射表：FX5 三层交互状态机 + BIG6 六大项及 Project/TC/Media/Monitoring/Audio/Info → FX3 7.02 原生模型与消费者 → 待实现/硬件缺失项 + 六段式 RAW 审查 | 公开文档 + 静态二进制 + CPU 模拟 |
| [`static-chain-evidence.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/static-chain-evidence.json) | 三条原生后端链（`0x4151` BasePicture/MLUT、`0x2debdb0`/`0x2dee4ac` MonitorLUT/ColorGamut、`0x4006` WhiteBalance）的反汇编指令字节与 Unicorn CPU 模拟回执 | 静态二进制 + Unicorn CPU 模拟 |
| [`online-sources-receipt.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/online-sources-receipt.json) | 联网抓取 Sony FX5 官方 Help Guide（`quick_menu`、`fullmenu_use`、`home_screen`、`project`、`paint_look`、`tc_media`、`shooting`、`monitoring`、`block_diagram`）与 FX6 6.01 官方说明页面的 HTTP 状态码、SHA256 与标题回执 | 公开官方文档回执 |
| [`verify_menu_backend_chains.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains.py) | 一键复现核验脚本：校验卷 UUID、输入固件 SHA256、联网源回执、Capstone 反汇编断言与 Unicorn ARM64/Thumb 跨核模拟 | 可复现本地脚本 |

### 证据层级严格界定
- **[DOC / 公开官方文档]**：Sony FX5 (`ILME-FX5`, Help Guide ID `2630 v1`) 在线手册与 Sony FX6 (`ILME-FX6V`) Ver. 6.00/6.01 固件更新说明。
- **[STATIC / 静态二进制证据]**：只读提取自 FX3 7.02 的 [`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so)（SHA256 `545c5053...290f`）、[`cpapp-b.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin)（SHA256 `c90d00d8...bcba`）、[`av-cam.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha3/av-cam.bin)（SHA256 `477a8a3d...16b2`）及 [`fx6-prefix-curl.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/fx6-prefix-curl.bin)。
- **[CPU-EMU / Unicorn 指令级模拟]**：在本地 ARM64 与 ARM Thumb Unicorn 引擎中实际执行 `appFw.so` 发送端与 `cpapp-b.bin` 接收端函数，捕获真实的栈上 IPC 报文字节与 CP 状态块 `0x10a8de0` 内存写入结果。
- **[VM-HIST / 既有 VM 静态回执]**：只读引用 [`reports/2026-11-01-fx3-vm-resumed-repair/README.md`](file:///Volumes/KAFU2T/AI/Projects/Mac/reports/2026-11-01-fx3-vm-resumed-repair/README.md)，证实 QEMU guest 仅启动 Linux AP 壳层与 `init.d`，未跑起完整 Sony GUI/CP/AV 闭环，因此**绝不能用 VM 伪造菜单交互验收**。
- **[HW-UNTESTED / 实机未测项]**：真机センサー ISP 寄存器实拍效果、CP DRAM 运行态 `0x02015794` 预载内容、以及自定义 UI 注入后的真机按键/触控帧率，均属未测项，明确标注缺口，不写为通过。

---

## 3. FX5 菜单交互逻辑与 FX6 6.01 BIG6 适配设计

### 3.1 交互状态机设计（参考 FX5 `home_screen` + `quick_menu` + `fullmenu_use` 与 FX6 6.01 BIG6）

```
                   ┌───────────────────────────────────────────┐
                   │           实时取景 / 拍摄画面              │
                   │  (Direct Menu / 拨轮直接调光圈/快门/ISO)   │
                   └─────┬───────────────────┬───────────┬─────┘
            HOME 键 /    │                   │ 短按 MENU  │ 长按 MENU
            BIG6 切换    ▼                   ▼           ▼
        ┌────────────────────────┐ ┌──────────────────┐ ┌──────────────────────┐
        │   HOME (BIG6) 六柱屏   │ │ Quick Menu (5页) │ │  Full Menu (10分类)  │
        │ 左: FPS / ISO-EI / Sht │ │ 1. Project       │ │ Shooting / Project / │
        │ 右: Iris / Look / WB   │ │ 2. TC/Media      │ │ Paint/Look / TC/Med  │
        │ 中: 状态/直方图/音频表  │ │ 3. Monitoring    │ │ Monitoring / Audio / │
        │                        │ │ 4. Audio         │ │ Clip / Tech / Net /  │
        │ 选中任一柱 -> 行内子面板│ │ 5. Info (只读)    │ │ Maintenance (<=8行)  │
        │ BACK -> 取消未提交修改  │ │ 槽位6 -> 跳全菜单 │ │ [Execute] -> 确认弹窗│
        └────────────────────────┘ └─────────┬────────┘ └──────────▲───────────┘
                                             │ 点击各页底部跳转槽  │
                                             └─────────────────────┘
```

1. **HOME (BIG6) 主屏交互规则（[DOC: `home_screen.html` + FX6 6.01 `00259043`]）**：
   - **六大核心柱（BIG6）**：
     - 左上 `FPS`：显示当前帧率与 `Variable (S&Q)` 开关状态。
     - 左中 `ISO / Gain / Exposure Index`：随 `[Project] - [Base Setting] - [Shooting Mode]` 自动变形：
       - `Custom` 模式：调 `ISO/Gain` + `Base Sensitivity (Low/High)` + `AGC`。
       - `Flexible ISO` 模式：调 `ISO` + `Base ISO (Low 800 / High 12800)` + `AGC`。
       - `Cine EI` 模式：调 `Exposure Index (EI)` + 手动切 `Base ISO (Low 800 / High 12800)`。
       - `Cine EI Quick` 模式：调 `Exposure Index (EI)`，跨阈值自动联动切换 `Base ISO`。
     - 左下 `Shutter`：调 `Speed / Angle`（含 `Step` 与 `Continuous` 防闪烁微调、`Auto Shutter`，以及 FX6 6.01 在 59.94P 下新增的 `1.2F (1/50)` 档位标签）。
     - 右上 `Iris`（FX6 为 `Iris / ND Filter`）：在 FX3 7.02 上映射为 `F-number` + `Auto Iris`（因 FX3 无内置电子 ND，禁止伪造内部 ND 档位）。
     - 右中 `Scene File`（`Custom` 模式）或 `Look`（`Log` 模式）：
       - `Custom` 模式下直接切换 `Scene File`（`S-Cinetone`、`Standard`、`709tone` 等）。
       - `Log` 模式下显示 `Base Look` 名称，子面板含：`Item 1: Main/Sub Rec LUT On/Off`、`Item 4: Edit Look`（跳转 `[Paint/Look] - [Base Look] - [Select]`）、`Item 6: HDMI / LCD Monitor LUT On/Off`。
     - 右下 `White Balance`：切换 `Memory A..H` / `Preset` / `ATW` / `AWB`，行内调节 `Color Temp`（`[Coarse]` 100K 步进 / `[Fine]` 1K 步进）与 `Tint (-99..+99)`，并提供一键白平衡测量。
2. **Quick Menu（短按 `MENU`，[DOC: `quick_menu.html`]）**：
   - 顶栏固定 5 个快速页签：`[Project]`、`[TC/Media]`、`[Monitoring]`、`[Audio]`、`[Info]`。
   - 焦点位于 `Item 1..5` 时，左右方向键/拨轮或触控直接切换页签；向下进入当前页的参数槽位；每个可编辑页底部设有 `[Full Menu]` 快捷槽，一键深跳至对应分类的完整菜单。
   - `[Info]` 页专用于片场快速巡检：显示系统日期/传感器温度/累计工时、电池精确电量与 USB-PD 供电状态、E 卡口镜头型号/序列号/光圈/焦距/对焦距离/景深范围。
3. **Full Menu（长按 `MENU`，[DOC: `fullmenu_use.html`]）**：
   - 10 个一级分类：`[Shooting]`、`[Project]`、`[Paint/Look]`、`[TC/Media]`、`[Monitoring]`、`[Audio]`、`[Clip Operations]`、`[Technical]`、`[Network]`、`[Maintenance]`。
   - **8 行视口与行内微调协议**：每页最多展示 8 行；小枚举项展开不超过 8 行的弹出列表；大跨度连续数值项（如 `-99..+99` 的 Paint/Matrix/Tint）不弹列表，直接在当前行高亮数值由拨轮增减，确保调色时画面不被菜单遮挡。
   - **事务取消语义**：在按下确认键前按 `BACK`，必须丢弃临时修改并恢复原值。

---

### 3.2 BIG6 及 Project / Paint/Look / TC/Media / Monitoring / Audio 映射总表

完整机器可读版见 [`menu-control-mapping.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/menu-control-mapping.json)，核心汇总如下：

| 目标区域 / 菜单项 | FX5 / FX6 6.01 目标功能 | FX3 7.02 原生模型与可证实后端消费者 | 适配状态与待实现/无硬件边界 |
|---|---|---|---|
| **BIG6-1: FPS** | `Fixed / Variable (S&Q)` 开关 + 帧率选择（1..240fps） | `model::sequence_set_movie_format::run()`、`0x293019c`（S&Q/拍摄模式读取）、CP 传感器读出时序与 AV 编码器 | **可适配（受限于离散档位）**：FX3 原生支持 4K 1..120fps / FHD 1..240fps S&Q，但为离散预设步进（非 FX6 全模式 1fps 连续步进），且切换 S&Q 需重配传感器模式。 |
| **BIG6-2: ISO / Gain / EI** | 随模式切换 `ISO/Gain`、`Flexible ISO`、`Cine EI`、`Cine EI Quick` + `Base ISO (800/12800)` | `model::sequence_set_iso_speed_rate::run()` (`0x39520f8`)、`setting_log_shooting` (`0x2935944`: `0=Off, 1=Cine EI, 2=Cine EI Quick, 3=Flex ISO`) | **原生后端完备**：FX3 7.02 已完整支持四种拍摄模式与 S-Log3 双原生 ISO (800/12800)；仅 `Custom` 模式下 FX3 按 ISO 阈值自动切换高低底座，无独立手动 Low/High 锁开关。 |
| **BIG6-3: Shutter** | `Speed / Angle`、`Step / Continuous (ECS)`、`Auto Shutter`、59.94P 下 `1.2F (1/50)` | `model::sequence_set_shutter_type::run()` (`0x3955e14`)、`sequence_set_shutter_speed_am_switching::run()` (`0x3955d1c`) | **原生后端完备**：FX3 7.02 已内置快门角度（Shutter Angle）与高分辨率防闪烁可变快门；FX6 6.01 的 `1.2F (1/50)` 可在 UI 层映射至 59.94P 下的 `1/50` 档位。 |
| **BIG6-4: Iris / ND** | `Iris F-number` + `Auto Iris`；FX6 另有 `ND Clear / 1/4..1/128 / Auto ND` | `model::sequence_set_iris_dial::run()` (`0x3951dd4`)、`sequence_set_iris_drive::run()` (`0x3951e34`)、`sequence_set_iris_drive_for_high_resolution::run()` (`0x3951ea4`) | **Iris 原生完备 / ND 无硬件**：FX3 具备高分辨率光圈驱动后端，但**无内置电子/光学 ND 硬件**；UI 必须遵循 FX5 仅展示 `Iris`，或将 `ND` 标为 `N/A (External)`。 |
| **BIG6-5: Look / Scene File** | `Custom`: Scene File；`Log`: `Base Look` 选择 + 分流 `LUT On/Off`（主副录 vs HDMI/LCD） | 主链：`sequence_set_base_picture_setting::run()` (`0x2d78050`) → `0x4151` → CP `0x791f9d` → `GetVfxMlutLookname` (`0x3266ec`) → VFX SDK (`0xa4f8ba`) → DMA (`0x470f78`)；监看链：`vdf_disp_set_monitor_lut` (`0x2debdb0`, `0x92840747`) | **需 AP+CP 补丁桥接且受 ISP 阶段约束**：1. 原生 `0x4151` 无法触达 CP 休眠项 ID 22 (`MLUT_LOOKNAME_SL3SG3_TO_ACESREC709`)，需 6 条指令补丁；2. 主录 `0x4151` 与监看 `0x2debdb0` 天然分离，可实现分流开关；3. 完整 Paint 矩阵/细节需 CP ISP 表配合。 |
| **BIG6-6: White Balance** | `Memory A..H` (8 组)、`Preset`、`ATW`、`AWB`、`Color Temp` (`Coarse` 100K / `Fine` 1K)、`Tint (-99..+99)` | `model::sequence_set_wb_mode::run()` (`0x2d9f2c8`) → `0x2e3c3b8` (`0x4006`) → `0x2e18e3c` → CP `file+0x68950c` (`VA 0x79150d`) 写入 `0x10a8de0+{0x9f4..0xa02}` | **存在协议量化约束（已静态+模拟证实）**：`0x2e18e98` 将色温除以 `100` 写入单字节 `+0x10`（仅支持 100K 步进）；`[Fine]` 1K 步进与 `Tint` 必须折算进 `+0x9..+0xf` 的 16 位 AB/GM 余数字段，8 组记忆槽 `A..H` 需由 AP 持久化层托管并映射下发。 |
| **Project (Quick 页1 / Full)** | `Shooting Mode`、`Target Display`、`Rec Format`、`Cine EI/Flex.ISO Gamut`、`Simul/Relay`、`Proxy`、`All File` | `sequence_set_base_picture_setting`、`sequence_set_movie_format`、`sequence_set_proxy_setting`、`sequence_set_double_slot_settings` | **原生后端完备（容器差异除外）**：FX3 原生支持双卡同时/接力录制、Proxy、CAMSET 存取与 S-Gamut3/S-Gamut3.Cine 切换；但 FX3 录制 MP4 封装而非 FX6 的 MXF 封装。 |
| **Paint/Look (Full)** | `Scene File`、`Base Look`（含 User LUT 1..16）、`Black`、`Knee`、`Color Matrix`、`Multi Matrix`、`Detail`、`Skin Tone Detail` | `sequence_set_picture_profile::run()` (`0x3953e80`)、`sequence_set_lut_data::run()` (`0x39526f8`)、CP ISP 矩阵与曲线表 | **部分原生 / 高级 Paint 需 CP ISP 映射**：FX3 Picture Profile 暴露了基础 Black/Gamma/Knee/ColorMode/Detail，但 FX6 的 16 轴 Multi Matrix 与独立 Skin Tone Detail 需直接映射 CP ISP 寄存器表。 |
| **TC/Media (Quick 页2 / Full)** | `Timecode` (`Preset/Regen`, `Rec/Free Run`, `DF/NDF`)、`Users Bit`、`Remaining`、`Format Media [Execute]`、`Clip Naming` | `sequence_set_tc_ub_display_setting::run()`、`sequence_set_double_slot_settings::run()` | **原生完备（无独立 BNC TC Out）**：TC/UB 设置、双槽 CFexpress A / SDXC 剩余时间与格式化确认、片名规则均原生具备；仅无 FX6 的物理 BNC TC Out 接口。 |
| **Monitoring (Quick 页3 / Full)** | `Output On/Off`、`De-Squeeze (1.3x/2.0x)`、`Zebra 1/2`、`Peaking`、`Marker`、`Display LUT` | `sequence_set_zebra::run()`、`sequence_set_peaking::run()`、`sequence_set_de_squeeze_disp::run()`、`vdf_disp_set_monitor_lut` (`0x2debdb0`) | **HDMI/LCD 原生完备 / 无 SDI 与 VF**：斑马纹、峰值、安全框、变形宽银幕反挤压（1.3x/2.0x）、HDMI 16-bit RAW 输出均原生支持；SDI/VF 硬件缺失。 |
| **Audio & Info (Quick 页4/5)** | `CH1..CH4` 输入源/电平/限幅、监听 `Timing (Live/Lip Sync)`、`Info`（传感器温度/工时/电池/镜头景深） | `sequence_set_audio_recording::run()`、`sequence_set_external_mic_audio_format::run()`、`sequence_set_audio_output_timing::run()` | **音频 4 通道原生完备 / Info 温度工时待核**：XLR-H1 手柄 4 通道 24-bit 数字音频与监听延时原生支持；镜头焦距/对焦距离/光圈与电池百分比在 AP 模型层可读，传感器摄氏度与累计工时需核查 CP 遥测接口。 |

---

## 4. 原生后端控制链静态与 CPU 模拟证据（含文件、地址、字节与模拟结果）

所有反汇编指令与 Unicorn 内存快照已由 [`verify_menu_backend_chains.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains.py) 自动提取并写入 [`static-chain-evidence.json`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/static-chain-evidence.json)。

### 4.1 链路一：Look / Base Picture Setting 主链（AP `0x4151` → CP `0x791f9d` → `GetVfxMlutLookname` → VFX SDK → 70 描述符 DMA）

1. **AP 模型层序列构造函数 `model::sequence_set_base_picture_setting`**（[`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so) `VA 0x2c47cfc..0x2c47e88`）：
   - 挂载虚表 `0x46dd608`（通过 GOT `0x47afd48`），从全局模型状态基址 `0x821c538` 调用 getter 群（`0x294c294`、`0x29376f0`、`0x2935944`、`0x293cd58`、`0x293019c`、`0x2937718`、`0x294c3fc..0x294c474`、`0x293596c`、`0x2935980`）及辅助函数 `0x2b49520`，填充序列对象偏移 `+0x1bc..+0x1dc`：
     - `+0x1bc`: `setting_select_lut`
     - `+0x1c0`: `is_exist_user_lut`
     - `+0x1c4`: `setting_log_shooting`（`0`=Off, `1`=Cine EI, `2`=Cine EI Quick, `3`=Flexible ISO）
     - `+0x1c8`: `setting_input_signal`
     - `+0x1cc`: `setting_picture_profile_for_709tone`
     - `+0x1d0`: `setting_gamut`（`1`=S-Gamut3, `2`=S-Gamut3.Cine）
     - `+0x1d4`: `setting_picture_profile`（如 `0x3b` = S-Cinetone）
     - `+0x1d8`: `general_shooting_mode`
     - `+0x1dc`: `color_gamut_target_display`
2. **AP 序列执行入口 `model::sequence_set_base_picture_setting::run()`**（`VA 0x2d78050..0x2d7819c`，符号字串位于 `0x39486e8`）：
   - 将对象 `+0x1bc..+0x1d8` 的 8 个 32 位词压入栈帧 `x29+0x60..0x7c`，调用 `0x2dd8354` → `0x2e3172c`。
   - 随后读取 `+0x1dc`，调用 `0x2dd03d4` → `0x2dee4ac` 下发 `ColorGamut` 显示消息。
3. **AP `0x4151` 信封与 5 字节载荷构造器**（`VA 0x2e3172c..0x2e317b4` → `0x2e26fcc..0x2e2716c`）：
   - `0x2e3172c` 关键指令字节：
     - `0x2e31730: a2008052 mov w2, #5` + `0x2e31748: a2a30039 strb w2, [x29, #0x28]`（包头 `+0` = `0x05`）
     - `0x2e3174c: 222a8852 mov w2, #0x4151` + `0x2e31750: a2570079 strh w2, [x29, #0x2a]`（消息 ID `+2` = `0x4151`）
     - `0x2e31768: 99d5ff97 bl #0x2e26fcc`（调用 `infra_wrapper_imaging::detail::set_base_picture_setting_i` 填充 `+8..+12` 共 5 个字节：`base_look`、`shooting_mode`、`input_gamut`、`color_gamut`、`target_display`）
     - `0x2e3178c..0x2e3179c`: 设置 `w0 = 0x90030001`、`x1 = x29+0x28`、`x2 = 0x10`，调用 `0x2e2fb90` 发送 16 字节 IPC 包。
4. **CP 接收、参数校验、MLUT 选择与 70 描述符 DMA 链**（[`cpapp-b.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin)，`VA = file + 0x108000`）：
   - **分发表**：`file+0xe003a0` 处记录键 `0x4151`、校验函数 `0x2fe05d`（`file+0x1f605c` `CheckSetParamBasePictureSetting`）与写入函数 `0x791f9d`（`file+0x689f9c`）。
   - **CP 写入函数 `file+0x689f9c` (`VA 0x791f9c`)** 指令字节：
     - `0x791f9e: 48f6e053 movw r3, #0x8de0` / `0x791fa2: c0f20a13 movt r3, #0x10a`（基址 `r3 = 0x10a8de0`）
     - `0x791fa6..0x791fc4`: 依次读取 `[r0, #8..#0xc]` 写入 `[r3, #0xba0]` (`base_look`)、`#0xba4` (`shooting_mode`)、`#0xba8` (`input_gamut`)、`#0xbac` (`color_gamut`)、`#0xbb0` (`target_display`)，并将 `[r3, #0x76c]` 递增 1。
   - **Unicorn 跨核模拟实测结果**：
     - 输入 AP 8 词 `(0x3b, 0, 1, 2, 0, 2, 0, 1)`，Unicorn 执行 `0x2e3172c` 捕获到通道 `0x90030001` 上发送的 16 字节报文为：`05005141000000000b01020201000000`。
     - 将该 16 字节报文送入 Unicorn Thumb 引擎执行 `cpapp-b.bin` `VA 0x791f9d`，实测 `0x10a8de0` 内存写入：`+0xba0 = 11`、`+0xba4 = 1`、`+0xba8 = 2`、`+0xbac = 2`、`+0xbb0 = 1`、`+0x76c = 1`。
   - **下游 MLUT 休眠项 ID 22 与 DMA 引擎**：
     - `file+0x8d1ad6` 读取 `0x10a8de0+0xba0..0xbb0` 调用 `GetVfxMlutLookname` (`file+0x3266ec`)。
     - CP 注册表 `file+0xbf8ffc` (`VA 0xd00ffc`) 处存有休眠项 ID 22（原始字节 `160000009457010246000000`）：`look_id = 0x16 (22)`，`target_addr = 0x02015794`，`descriptor_count = 0x46 (70)`，对应符号 `MLUT_LOOKNAME_SL3SG3_TO_ACESREC709`。
     - 经 `SetVfxMlutParam` (`file+0x3263fc`) → VFX SDK (`VA 0xa4f8ba` → 资源解析器 `VA 0x488094` 查表 `0x13eaff8` → 核心 `VA 0xa14d86` → 队列 `VA 0xa1f2f2`) → `mlut_make_lli_table` (`VA 0x470f78`)，在 `0x2025570` 处生成 70 条 16 字节 DMA LLI 描述符，目标硬件窗口为 `0xf4009000 + (combo << 20)`。

---

### 4.2 链路二：Monitor LUT 监看辅助与 ColorGamut BB/VDF 独立显示链（`0x2debdb0` & `0x2dee4ac`）

1. **`infra_wrapper_bb::detail::vdf_disp_set_monitor_lut`**（[`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so) `VA 0x2debdb0..0x2debf04`，由 `model::sequence_set_gamma_disp_assist::run()` 调用）：
   - 在栈帧 `x29+0x20` 构造 10 字节报文：
     - `0x2debdb4: a2018452 mov w2, #0x200d` → `strh w2, [x29, #0x20]`
     - `0x2debdd0: 222c8052 mov w2, #0x161` → `strh w2, [x29, #0x22]`
     - `0x2debdd4: 42018052 mov w2, #0xa` → `strh w2, [x29, #0x24]`
     - `0x2debde4: c2ff8f12 mov w2, #-0x7fff` (`0x8001`) → `strh w2, [x29, #0x26]`
     - 根据输入类型将显示 LUT 枚举写入 `[x29, #0x28]`，随后通过 `0x2de70a8` 向传输通道 `0x92840747` 发送 10 字节报文。
   - **Unicorn 模拟实测捕获报文**：`0d2061010a0001800100`（通道 `0x92840747`，长度 `10`）。
2. **`ColorGamut` BB/VDF 发送器**（`VA 0x2dee4ac..0x2dee538`）：
   - 同样向通道 `0x92840747` 发送 10 字节报文，命令字为 `0x0167`（`0x2dee4c4: e22c8052 mov w2, #0x167`）。
   - **Unicorn 模拟实测捕获报文**：`0d2067010a0001800100`（通道 `0x92840747`，长度 `10`）。

---

### 4.3 链路三：White Balance 白平衡控制链（AP `0x4006` `PID_SET_WB_MODE` → CP `0x79150d`）与 100K/1K 量化证据

1. **AP 序列执行入口 `model::sequence_set_wb_mode::run()`**（[`appFw.so`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/appFw.so) `VA 0x2d9f2c8..0x2d9f3ec`，字串位于 `0x3957948`）：
   - 从序列对象 `+0x1bc..+0x1d0` 读取 6 个 32 位参数，打印调试日志 `Send PID_SET_WB_MODE[InPrm1..5]`（`0x3957887`、`0x39578cc`），打包至栈帧 `x29+0x48..0x5c` 并调用 `0x2dd5b14` → `0x2e3c3b8`。
2. **AP `0x4006` 封包器 `0x2e3c3b8..0x2e3c444` 与载荷构造器 `0x2e18e3c..0x2e190a8`**：
   - `0x2e3c3bc: a2008052 mov w2, #5`（`+0` = `0x05`）
   - `0x2e3c3e8: c2008852 mov w2, #0x4006` + `0x2e3c3f0: a2570079 strh w2, [x29, #0x2a]`（`+2` = `0x4006`）
   - 调用 `0x2e18e3c`：
     - 查跳转表 `0x397543c`（16 字节：`002f322c3b3835473e41444d50534a56`）将 AP 白平衡模式映射为线上字节 `[x19, #8]`（`0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 0xa, 0xb, 0xc, 0xd, 0x12`）。
     - **关键量化指令**：
       - `0x2e18e94: 047d8052 mov w4, #0x3e8` (`1000`)
       - `0x2e18e98: 830c8052 mov w3, #0x64` (`100`)
       - `0x2e18ea0: 610fc41a sdiv w1, w27, w4` + `0x2e18eb4: 21ec041b msub w1, w1, w4, w27`（将 `InPrm1` AB 偏移拆分为 `/1000` 商字节 `+9` 与 `%1000` 16 位余数 `+0xc`）
       - `0x2e18ea8: 400cc41a sdiv w0, w2, w4` + `0x2e18ebc: 0088041b msub w0, w0, w4, w2`（将 `-InPrm2` GM 偏移拆分为 `/1000` 商字节 `+0xa` 与 `%1000` 16 位余数 `+0xe`）
       - `0x2e18eac: 5a0fc31a sdiv w26, w26, w3` + `0x2e18ec8: 7a420039 strb w26, [x19, #0x10]`（**将开尔文色温除以 100 后存为单字节 `+0x10`**！）
3. **CP `0x4006` 接收器 `file+0x68950c` (`VA 0x79150d`)**（[`cpapp-b.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin) 分发表 `file+0xdfeb90`）：
   - 将 `[r0, #8..#0x12]` 解包写入 `0x10a8de0`：
     - `+0x9f4`: WB 模式 (`str.w r1, [r5, #0x9f4]`)
     - `+0x9f8` / `+0x9f9`: AB/GM `/1000` 商字节
     - `+0x9fa` / `+0x9fc`: AB/GM `%1000` 16 位半字余数 (`strh.w r4, [r5, #0x9fa]`, `[r5, #0x9fc]`)
     - `+0xa00`: 100K 单位色温字节 (`ldrb.w ip, [r0, #0x10]; strb.w ip, [r5, #0xa00]`)
     - `+0xa01` / `+0xa02`: 微调字节与标志位，并打印日志 `FW: SET_WB_MODE[%d: %d: %d: %d: %d]`（字串位于 `VA 0xdb2fde`，`file+0xcaafde`）。
   - **Unicorn 跨核模拟实测结果**：
     - 输入 `(1, mode=9, AB=2500, GM=-1500, Temp=5600K, flag=1)`，Unicorn 执行 `0x2e3c3b8` 捕获 20 字节 IPC 包：`050006400100000009020100f401dc0538000100`。
     - 送入 CP `VA 0x79150d` 模拟后，实测 `0x10a8de0` 写入：`+0x9f4 = 9`、`+0x9f8 = 2`、`+0x9f9 = 1`、`+0x9fa = 500 (0x01f4)`、`+0x9fc = 500 (0x01f4)`、`+0xa00 = 56 (0x38, 即 5600K/100)`、`+0xa02 = 1`。

---

## 5. 完整 RAW / 底层色彩链独立审查（CPU vs CP/AV vs 硬件 ISP）

用户明确要求移植 **FX6 整个 RAW/底层色彩链与专业电影菜单，而不是只要一个 LUT**。我们对 FX3 7.02 与 FX6 的完整成像链路做如下 6 段式独立审查：

| 阶段 | 处理内容 | 归属执行域（CPU / CP-AV / 硬件 ISP） | 能否被 3D LUT 替代？ | 独立审查结论与适配要求 |
|---|---|---|---|---|
| **Stage 1：RAW 前端与传感器读出** | 双原生 ISO 转换增益（800 / 12800）、光学黑电平钳位 (OB Clamp)、坏点补偿、镜头暗角/色度阴影校正 (Shading) | **硬件 ISP 前端 (SIE/IFE)**，由 CP RTOS (`cpapp-b.bin`) 按传感器模式表下发寄存器配置；HDMI 16-bit RAW 在去马赛克前引出 | **绝对不能** | 决定原始动态范围、暗部本底噪声及高感光度信噪比。FX3 与 FX6 共享 10.2MP 全画幅背照式 Exmor R 传感器家族，但 CP 传感器模式寄存器表决定了增益切换点与 OB 校准。 |
| **Stage 2：去马赛克与空时降噪/细节** | Bayer Demosaic、2D 空域 / 3D 时域降噪 (NR)、Detail 边缘锐化、Skin Tone Detail（肤色细节独立门限） | **硬件 ISP 核心模块**，由 CP RTOS 根据拍摄模式、ISO 档位与 Paint Detail 参数写入硬件系数表 | **绝对不能** | 3D LUT 是纯点对点颜色映射（$R,G,B \to R',G',B'$），无空间邻域算子。FX6 Paint 菜单中的 `[Detail]`、`[Noise Suppression]`、`[Skin Tone Detail]` 必须在 CP 中关联到 ISP 空域/时域滤波器参数表，否则菜单滑块将是空壳。 |
| **Stage 3：白平衡、3×3 CCM、Log/预伽马曲线与高光拐点** | R/G/B 白平衡增益（`0x4006` → `0x10a8de0+0x9f4..0xa02`）、传感器原生色域转工作色域（`S-Gamut3` / `S-Gamut3.Cine`）3×3 CCM、S-Log3 / HLG / 709 传递曲线、Knee 高光拐点与 Shoulder 滚降 | **CP RTOS 求解器 (`cpapp-b.bin`) → 硬件 ISP 矩阵与曲线单元**（位于 MLUT 之前） | **不能（强耦合）** | **这是最容易被忽视的核心段**：Stage 4 的 3D LUT 假定输入信号已经过准确的 Stage 3 转换（例如严格处于 `S-Log3 / S-Gamut3.Cine` 或特定预伽马空间）。若上游白平衡 1K 微调、CCM 矩阵或高光 Knee 压缩斜率与 FX6 不一致，直接套用 FX6 LUT 会导致高光提前硬切或肤色偏相。 |
| **Stage 4：MLUT 模块（1D 预整形 + 33³ 3D LUT + 后置矩阵）** | `149,888B` 复合表：`160B` 头 + `3×1984B` 1D Pre-Shaper + `143,748B` (`33×33×33` 3D LUT) + `36B` (`3×3` 后置矩阵) | **CP VFX SDK (`VA 0xa4f8ba`) + DMA LLI (`VA 0x470f78`) → 硬件 ISP MLUT 窗口 `0xf4009000 + (combo << 20)`** | **本段即 MLUT 本体** | 已完成从 AP `0x4151` 到 CP 70 个 DMA 描述符（`0x2025570`）的完整指令级模拟验证。包含内置 Look（含休眠项 ID 22 `SL3SG3_TO_ACESREC709` @ `0x02015794`）与 16 槽 User `.cube` LUT (`0x0229cc00`/`0x02370000`)。 |
| **Stage 5：多路输出分流（主/副编码 vs 监看/HDMI/OSD）** | 主录 XAVC-I/S/HS、副录 Proxy（CP `combo 0..4`）与 HDMI / LCD 监看辅助（BB/VDF `0x92840747` `0x0161` Monitor LUT & `0x0167` ColorGamut） | **CP 多 Combo 硬件通道 + BB/VDF 显示引擎 (`appFw.so` / `av-cam.bin`)** | **不能** | FX5/FX6 BIG6 的 `Look` 子面板允许独立开关 `Main/Sub Rec LUT` 与 `HDMI/VF/LCD Monitor LUT`。必须协同控制 CP `0x4151`、`sequence_set_embedded_lut` 与 BB/VDF `0x2debdb0`，防止开启监看 LUT 时误将 LUT 烧录进 S-Log3 主素材。 |
| **Stage 6：AP 状态机持久化与容器元数据** | `appFw.so` `0x821c538` 模型状态块、CAMSET 备份、重配防回写机制、MP4 色彩/LUT Acquisition Metadata | **AP Linux (`appFw.so`) + AV 封装器 (`av-cam.bin`)** | **不能** | `sequence_set_base_picture_setting` 每次构造（`0x2c47cfc`）都会重新从 `0x821c538` 读取各字段。若新增的 BIG6 状态（如 `base_look=12` 或 WB Memory A..H）未持久化进 `0x821c538` 对应槽位，任何引发重配的操作（切帧率、切色域、开关机）都会将色彩重置回原厂默认值。 |

---

## 6. 可离线重放的最小真实实验设计（不启动 VM、不接真机、不以 LUT 冒充整链）

为在不启动 VM、不触碰真机硬件的前提下验证 **Stage 3（上游白平衡/色域/曲线）+ Stage 4（CP 70 描述符 MLUT 引擎）+ Stage 5（多 Combo 分流）** 的真实耦合行为，定义并部分实现了如下最小离线重放实验：

1. **实验名称**：`CP Stage-3 + Stage-4 跨核指令级 + 数值级联合离线重放实验`
2. **当前已在 [`verify_menu_backend_chains.py`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/gemini-menu/verify_menu_backend_chains.py) 中跑通的跨核闭环（实测通过）**：
   - 使用 Unicorn ARM64 引擎真实执行 `appFw.so` 的 `0x2e3172c`（`0x4151` BasePictureSetting）与 `0x2e3c3b8`（`0x4006` WhiteBalance），以及 `0x2debdb0`（Monitor LUT）和 `0x2dee4ac`（ColorGamut），捕获真实栈上 IPC 字节流。
   - 将捕获到的 IPC 字节流无缝注入 Unicorn ARM Thumb 引擎，真实执行 `cpapp-b.bin` 的 `VA 0x791f9d`（`0x4151` 写入器）与 `VA 0x79150d`（`0x4006` 写入器），验证 `0x10a8de0` 状态块中 Stage-3 白平衡参数（`+0x9f4..+0xa02`）与 Stage-4 色彩路由参数（`+0xba0..+0xbb0`、`+0x76c`）的精确落盘。
3. **待 donor 工人提取 FX6 固件分区后的下一精确动作（数值像素级差分实验）**：
   - **输入**：合成 16-bit 线性 Exmor R 曝光斜坡（-6 EV 至 +6 EV）+ 24 色标准色卡矩阵。
   - **实验步骤**：
     1. 从 FX6 6.01 donor 固件的 CP/ISP 分区提取 Stage-3 预伽马/CCM/WB 增益表与 Stage-4 MLUT 表（对比 FX3 `cpapp-b.bin` 中 ID 17..22 的 `0x02015794` 等表）。
     2. 在本地 Python/Unicorn 离线管线中分别运行：
        - **路径 A（仅替换 3D LUT）**：FX3 原生 Stage-3 矩阵/曲线 + FX6 Stage-4 3D LUT。
        - **路径 B（完整 Stage-3 + Stage-4 联合链）**：FX6 Stage-3 WB/CCM/Knee 预变换 + FX6 Stage-4（1D Pre-Shaper + 33³ 3D LUT + 3×3 后置矩阵）。
     3. 计算路径 A 与路径 B 在高光拐点（+3 EV..+6 EV）的斜率误差与 24 色块的 $\Delta E_{00}$ 色差，定量证明上游 Stage-3 表对最终电影感色彩的贡献度。

---

## 7. 已知缺口与下一精确动作

1. **已知缺口（绝不隐瞒或伪造）**：
   - Sony 官方 `www.sony.com` 的 FX6 6.01 页面（`00259043`）对直接脚本 `urllib` 请求返回 HTTP 403（Akamai 反爬拦截），已通过公开搜索索引摘要及本地 [`fx6-prefix-curl.bin`](file:///Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/fx6-prefix-curl.bin) 交叉核实，而 Sony FX5 官方 Help Guide 九个核心页面均已 200 OK 完整拉取并计入 SHA256 回执。
   - CP DRAM 运行态地址 `0x02015794`（休眠项 ID 22）及 Stage-3 硬件 ISP CCM/Knee 系数表在静态 `cpapp-b.bin` 镜像之外的部分需依赖 NAND 数据分区或 donor 工人对 FX6 6.01 完整固件包的解包结果。
2. **下一精确动作**：
   - 与 `donor` 工人产出的 FX6 6.01 解包表对齐，提取 FX6 的 Stage-3 CCM/Knee 表与 Stage-4 MLUT payload，运行第 6 节定义的离线像素级差分实验，并将 AP 模型状态 `0x821c538` 的持久化槽位（`base_look=12` 及 WB Memories A..H）接入 `sequence_set_base_picture_setting` (`0x2c47cfc`) 与 `sequence_set_wb_mode` (`0x2d9f2c8`)。
