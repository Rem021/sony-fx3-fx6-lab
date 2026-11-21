# Phase 385（Stage 89 — `89/89`）：Wave 79 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` `Shooting -> [Zoom]` 8 档变速架构、`Setup -> [Dial Customize]` 5 项矩阵与 `My Dial 1..3` / `[Function Ring(Lens)]`、`[Operation Customize]` 8 项位掩码（`G99`）与零 EVF `[DISP]` / `[Select LUT]`（`G132`），以及 `[External Output]` HDMI 4K 10-bit/RAW 与 12G-SDI 双管线 HIL 协同仿真闭环报告

- **日期**：`2026-11-21`
- **任务 / 阶段**：`H494` · **Phase 385 · VM HIL Stage 89（`89/89` Full-Board VM Co-Emulation Stages!）**
- **一手情报基线**：[Wave 79 实机深度审计报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h494-phase385-vm-stage89-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-hil/reports/2026-11-18-global-sony-wave79-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-intel/README.md)

---

## 一、结论先行（Executive Summary）

- **交付结论（`实测事实`）**：已完成 **Phase 385 Stage 89（`89/89`）** 确定性 HIL 协同仿真器实现、全板编排器接入、`112` 项四模式单测与文档闭环，全部验收门禁一次性通过（`0` 失败、`0` 字节专有固件泄漏、`0` USB/RF 发包、`0` 卡槽写入）。
- **核心交付文件（严格限定 5 份所属文件）**：
  1. [realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h494-phase385-vm-stage89-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-hil/outputs/fx3-vm/realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulator.py)（Schema `phase385_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulation_v1`）
  2. [fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h494-phase385-vm-stage89-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)（接入 `stage89_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_hil` -> `89/89`）
  3. [test_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h494-phase385-vm-stage89-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-hil/outputs/fx3-vm/tests/test_realhw_zoomspeed_mydial3_funcring_hdmi4kout_sdi12g_coemulator.py)（`112` 项前向兼容四模式单测）
  4. [outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h494-phase385-vm-stage89-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-hil/outputs/fx3-vm/README.md)（补录 Phase 385 Stage 89 CLI 与技术契约）
  5. [reports/2026-11-21-phase385-vm-stage89-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-hil/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h494-phase385-vm-stage89-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-hil/reports/2026-11-21-phase385-vm-stage89-zoomspeed-mydial3-funcring-hdmi4kout-sdi12g-hil/README.md)（本闭环报告）
- **硬件安全态势（`实测事实` + `推断`）**：
  - `ready_for_live_camera_attach = False`、`live_attach_authorized = False`、`emmc_writes_authorized = False`、`cross_model_flash_authorized = False`、`hardware_live_attachment_authorized = False`、`slot1_write_authorized = False`、`slot1_writes = 0`、`slot1_sector_writes = 0`、`slot1_data_sector_writes = 0`、`usb_tx_packets = 0`、`rf_tx_packets = 0`、`raw_firmware_bytes_leaked = 0`。
  - **推断**：本阶段严格延续 Tier-0 离线仿真台与 `Slot 1` 只读隔离红线（`HARD NO-GO` 物理相机直连或跨机型整分区刷写），所有 `[Rec. Media dur HDMI Output] = On` 针对 `Slot 1` 的写入请求均以 `EROFS (errno 30)` 确定性拒止。

---

## 二、4 路子模型与 Wave 79 六大勘误闭环对照（`实测事实`）

| 子模型 | 覆盖范围与 Wave 79 勘误修正 | FX3 Ver. 7.02 核心契约 | FX6 Ver. 6.01 差异化契约 |
| :--- | :--- | :--- | :--- |
| **89A** | `Shooting -> [Zoom]` 8 档变速架构（**`G149` `[Custom Key Z. Speed]` 无 `Variable` 闭环**）、CIZ 4 硬锁 5 退化与 `XLR-H1` 边界 | `[Zoom Range]`（`Optical zoom only` 默认 / `ClearImage Zoom` `4K 1.5x` `HD 2.0x` / `Digital Zoom` `4.0x`；`Smart Zoom` 仅 Still `M/S`）与 `[Zoom Ring Rotate]` 抗 `[Camera Settings Reset]`；`[Zoom Lever Speed]`（`1st=3`/`2nd=8`）、`[Custom Key Z. Speed]`（**仅 Fixed `1..8` 默认 `3`，硬拒 `Variable` `EOPNOTSUPP=95`**）与 `[Remote Zoom Speed]`（`Variable`/`Fix` + `1..8` 默认 `3`，ELF `BKID_APP_setting_fixed_zoom_speed_type`）均 `Can be reset`；`XLR-H1` 无物理变焦杆；4 大 CIZ/Digital 前置硬锁（Still RAW、Movie `119.88p/100p`、`S&Q >= 100fps`、HDMI RAW）+ 5 项激活退化（`Focus Area` -> Center priority AF、`Metering` -> `Multi`、Face/Eye AF/Multi-Face/Tracking 禁用） | `Technical > Zoom > Zoom Type` 仅 `Optical Zoom Only` / `On(Clear Image Zoom)`（**零 `Digital Zoom`，硬拒 `EOPNOTSUPP=95`**）；`Technical > Handle Zoom`（`Off` / `Low 1..8` def `3` / `High 1..8` def `8` / `Variable`）；明确 `0..99` 实为 HUD `Zoom Position Display`（硬拒伪 `Speed 1..99` 菜单） |
| **89B** | `Setup -> [Dial Customize]` 精确 5 项抗复位矩阵、物理 3 拨轮边界、`My Dial 1..3` 与 `[Function Ring(Lens)]` | 精确暴露 5 项（`[Custom Key/Dial Set.]`、`[My Dial Settings]`、`[Av/Tv Rotate]`、`[Function Ring(Lens)]`、`[Lock Operation Parts]`）且**全部抗 `[Camera Settings Reset]`**（仅 `Initialize` 归位）；物理 3 拨轮（`Front Dial` / `Rear Dial` / `Control Wheel`），硬拒休眠 `[Dial Setup]`（`VAL_setting_dial_setup_*` = 0 命中）、`[Dial / Wheel Lock]` 与 `Rear Dial L/R`（`EOPNOTSUPP=95`）；`My Dial 1..3`（Hold/Toggle/`1->2->3` 自动跳过空组）临时解锁 `[Lock Operation Parts]`；`[Function Ring(Lens)]`（`Power Focus` vs `APS-C/S35`，受 4K/RAW 裁剪锁约束，无环镜头回退 `FUNCTION_RING_INVALID`） | `Project > Assignable Dial`（`Grip/Remote Dial` & `Handle Dial` def `IRIS`，**包含 `ND Filter`**）vs `Project > Multi Function Dial`（def `Off`，**不含 `ND Filter`** 且菜单开启时自动禁用 `EBUSY=16`） |
| **89C** | `Setup -> [Operation Customize]` 8 项位掩码（**`G99` `Picture Profile` 抗 Reset+Init 闭环**）、零 EVF `[DISP]` 与 `[Select LUT]` vs `[Gamma Display Assist]`（**`G132` 闭环**） | `[Different Set for Still/Mv]` 精确 8 项位掩码，**`[Picture Profile]` 勾选框抗 BOTH `[Camera Settings Reset]` 和 `[Initialize]`**，`Shutter Mode = Angle` 强制 Still/Movie 快门独立；独立 `[Fn Menu Settings]` `12+12` 槽位（拒绝全空激活 `EBUSY=16`）；`[DISP (Screen Disp) Set]` 精确 4 个拍摄页 + 3 个回放页，100% 阻断零 EVF 休眠符号（`Graphic Display`、`For viewfinder`、`Monitor Off`、`[Finder/Monitor]`）；Movie/`S&Q` Log Shooting 下 `[Select LUT]`（`s709`/`709(800%)`/`S-Log3`/`User1..16`）+ `[Display LUT]` 覆盖 `[Gamma Display Assist]`，静态 Log（`_f 0x6538`）与非 Log PP 由 `[Gamma Display Assist]` 承接 | `Monitoring > Display On/Off` 暴露 **60 路 ELF `BKID_APP_SETTING_*_DISPLAY`**（`104` 路 User Menu 开关、`Rec/Play Status` 4 档、`Video Signal Monitor` 波形/矢量/直方图）；`Gamma Display Assist` 在 `Cine EI` 下硬锁 `Off`（仅 `Custom + HDR(HLG)` 允许） |
| **89D** | `Setup -> [External Output]` HDMI 4K 10-bit 4:2:2、LCD 熄屏条件、3 项 Sony ELF 拼写错误与 `12G-SDI + HDMI` 双管线 | 全部 `[External Output]` 抗 Reset；`[HDMI Resolution]` 精确 4 档（`Auto`/`2160p`/`1080p`/`1080i`，硬拒 `720p`）；Log/`PPLUT` 内录降档 `1080p`；`[4K Output Set.(HDMI Only)]` 精确 6 档 `10bit 4:2:2`（硬拒 `4:2:0` 与休眠 `_f 0x748a` `24.00p 8bit`，`24.00p` 强制重启、`APS-C/S35` 锁禁、`S&Q` 锁 `Rec. Media = On`）；`24p/60p Output` 100% 休眠（`0` ELF 命中）；`[HDMI Info. Display] = On` 仅在 `Rec. Media = On & RAW = Off` 熄灭机内 LCD；`[REC Control]` 强依赖 `TC Output = On`；锚定 3 项 Sony ELF 拼写错误（`ctrl_for_hmdi`、`outpute`、`4ch_output_ch`）与 `Slot 1 EROFS=30` | `Monitoring > Output Format` 25 项 `VAL_setting_output_format_sdi_hdmi_*` 双管线：`SDI RAW` + 4K HDMI 同步输出且机内 LCD 常亮；`HDMI RAW`（`4240x2392`，禁 `24Hz` 与 `S&Q`）强制锁定 SDI `1080P/i`；`S&Q > 60fps`（开启 SDI 或 RAW）限幅 HDMI `<= 1080p`；`SDI/HDMI Rec Control` 3 档（`Off`/`SDI/HDMI Remote I/F`/`Parallel Rec`） |

---

## 三、22 份本地只读供体与四模式洁净室实证（`实测事实`）

- **供体清单（严格 `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`，单次检测耗时 `< 0.2s <= 2.0s`）**：`20` 份紧凑供体（4 语言 × 3 变体 FX3 `.uxc` 共 `12` 份 + 4 语言 × 2 变体 FX6 `.uxc` 共 `8` 份）与 `2` 份受界 `<= 4096 B` `os.pread` 窗口供体（`FX3 appFw.so` `49` 窗口 + `5` 缺席断言、`FX6 appFw.so` `15` 窗口 + `1` 缺席断言）。
- **四模式自检摘要（`实测事实`）**：
  - `LOCAL_DONOR_O_RDONLY`：`[PASS] Phase 385 Stage 89 (89/89) | donors=22 | digest=dd8eaedbf4cb`
  - `FX3_CLEAN_ROOM_TEST=1`：`[PASS] Phase 385 Stage 89 (89/89) | mode=CLEAN_ROOM_SYNTHETIC | digest=53c782c79b24`
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`[PASS] Phase 385 Stage 89 (89/89) | mode=CLEAN_ROOM_SYNTHETIC | digest=53c782c79b24`
  - `FX3_FX6_MAC_WORK_ROOT=__fx3_fx6_clean_room_donor_disabled__`：`[PASS] Phase 385 Stage 89 (89/89) | mode=CLEAN_ROOM_SYNTHETIC | digest=8e7efb7e126e`

---

## 四、全量验收门禁实测记录（`实测事实`）

| 验收门禁 | 模式 | 实测结果 | 关键红线遥测 |
| :--- | :--- | :--- | :--- |
| **Stage 89 专项单测** | `normal` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / `work_root` 哨兵（4 模） | **4 × `112/112` OK**（每轮 `0.46s–0.66s`） | `leaked=0`, `slot1_writes=0`, `usb_tx=0`, `rf_tx=0` |
| **全量 `outputs/fx3-vm` 单测发现** | `normal` (`LOCAL_DONOR_O_RDONLY`) | **`5,741` tests OK**（`0` failures, `315.8s`） | `0` regressions across Stages 1..89 |
| **全量 `outputs/fx3-vm` 单测发现** | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`5,741` tests OK**（`0` failures, `skipped=39`, `288.6s`） | Clean-room parity verified |
| **`make verify-milestone-375`** | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK`**, **`vm_stages=89/89`**, `pillars=6/6`, `gate160=159/162`, `recovery=69/69` | `usb_tx=0`, `rf_pkts=0`, `slot1_writes=0`, `leaked=0`, `ready_attach=False` |
| **`PYTHONDONTWRITEBYTECODE=1 make clean-audit`** | 仓内洁净与 BYOF 审计 | **`ALL GREEN`**（提交前终验） | `0` `.pyc`、无专有大文件污染 |

---

## 五、后续建议（`推断`）

- 本阶段已完成 Wave 79（`79/79 Waves` 收官情报）全部 4 路子系统与 6 项跨机型勘误（`G149` `[Custom Key Z. Speed]` 仅 Fixed 与 FX6 `0..99` HUD 位置澄清、`[Dial Setup]`/`[Dial/Wheel Lock]`/`Rear Dial L/R` 休眠隔离、`G99` `[Different Set for Still/Mv]` `Picture Profile` 抗 Reset+Initialize、`[DISP]` 4 页与零 EVF 防火墙、`G132` `[Select LUT]` 覆盖 `[Gamma Display Assist]` 静动态分流，以及 HDMI 4 档分辨率 / 6 档 `10bit 4:2:2` / `24p/60p Output` 休眠 / LCD 熄屏条件 / 3 项 Sony ELF 拼写错误 vs FX6 `12G-SDI + HDMI` 25 项双管线）的 VM HIL 协同建模与全板 **`89/89`** 集成；后续更新 `fx3-safety` 安全守卫（`G99`/`G132`/`G149`）时可直接复用本阶段 `89A..89D` 契约。
