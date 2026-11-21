# Phase 383（Stage 88 — `88/88`）：Wave 78 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` `[Exposure Ctrl Type]`（`G86`）/ `[Shutter Mode]` 角度、`[Image Stabilization]` 与 `Catalyst`、`Playback -> [Photo Capture]` / `[View Mode]`（`G126`）/ `[Rating]` 与 `[USB Streaming]` 证伪 / `RTMP/RTMPS/SRT Caller` HIL 协同仿真闭环报告

- **日期**：`2026-11-21`
- **任务 / 阶段**：`H489` · **Phase 383 · VM HIL Stage 88（`88/88` Full-Board VM Co-Emulation Stages!）**
- **一手情报基线**：[Wave 78 实机深度审计报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h489-phase383-vm-stage88-flexexp-shutterangle-activeibis-catalyst-photocap-srt-hil/reports/2026-11-18-global-sony-wave78-flexexp-shutterangle-activeibis-catalyst-photocap-srt-intel/README.md)

---

## 一、结论先行（Executive Summary）

- **交付结论（`实测事实`）**：已完成 **Phase 383 Stage 88（`88/88`）** 确定性 HIL 协同仿真器实现、全板编排器接入、`112` 项四模式单测与文档闭环，全部验收门禁一次性通过（`0` 失败、`0` 字节专有固件泄漏、`0` USB/RF 发包、`0` 卡槽写入）。
- **核心交付文件（严格限定 5 份所属文件）**：
  1. [realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h489-phase383-vm-stage88-flexexp-shutterangle-activeibis-catalyst-photocap-srt-hil/outputs/fx3-vm/realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulator.py)（Schema `phase383_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulation_v1`）
  2. [fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h489-phase383-vm-stage88-flexexp-shutterangle-activeibis-catalyst-photocap-srt-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)（接入 `stage88_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_hil` -> `88/88`）
  3. [test_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h489-phase383-vm-stage88-flexexp-shutterangle-activeibis-catalyst-photocap-srt-hil/outputs/fx3-vm/tests/test_realhw_flexexp_shutterangle_activeibis_catalyst_photocap_srt_coemulator.py)（`112` 项前向兼容四模式单测）
  4. [outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h489-phase383-vm-stage88-flexexp-shutterangle-activeibis-catalyst-photocap-srt-hil/outputs/fx3-vm/README.md)（补录 Phase 383 Stage 88 CLI 与技术契约）
  5. [reports/2026-11-21-phase383-vm-stage88-flexexp-shutterangle-activeibis-catalyst-photocap-srt-hil/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h489-phase383-vm-stage88-flexexp-shutterangle-activeibis-catalyst-photocap-srt-hil/reports/2026-11-21-phase383-vm-stage88-flexexp-shutterangle-activeibis-catalyst-photocap-srt-hil/README.md)（本闭环报告）
- **硬件安全态势（`实测事实` + `推断`）**：
  - `ready_for_live_camera_attach = False`、`live_attach_authorized = False`、`cross_model_flash_authorized = False`、`emmc_writes_authorized = False`、`slot1_write_authorized = False`、`slot1_writes = 0`、`slot1_sector_writes = 0`、`slot1_data_sector_writes = 0`、`slot1_avf_info_mutated = False`、`usb_tx_packets = 0`、`rf_tx_packets = 0`、`raw_firmware_bytes_leaked = 0`。
  - **推断**：本阶段延续 Tier-0 离线台架与 `Slot 1` 只读隔离红线（`HARD NO-GO` 物理实机直连或跨机型刷写），任何试图将 `[Photo Capture]`、`[Rating]` XMP/AVF 或 `[Movie Rec During Streaming]` 写入 `Slot 1` 的路径均以 `EROFS (errno 30)` 确定性拒止。

---

## 二、4 路子模型与 Wave 78 五大勘误闭环对照（`实测事实`）

| 子模型 | 覆盖范围与 Wave 78 勘误修正 | FX3 Ver. 7.02 核心契约 | FX6 Ver. 6.01 差异化契约 |
| :--- | :--- | :--- | :--- |
| **88A** | `[Exposure Ctrl Type]`（**`G86` 抗复位补全**）、`[Auto/Manual Swt. Set.]`、`[Shutter Mode]` 角度与休眠 `Var. Shutter` | Movie/`S&Q` `[Exposure Ctrl Type]`（`_f 0x787e`：`Flexible Exp. Mode` 默认 / `P/A/S/M Mode`）**抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 归位），`[Auto/Manual Swt. Set.]`（`Av`/`Tv`/`ISO` 默认 `Manual`）与 `[Auto Slow Shutter]`（默认 `On`）均 `Can be reset`；Ver. 6.00+ `[Shutter Mode]`（`_f 0x7c7c`：`Speed` 默认 / `Angle` `_f 0x7c86`，仅 Movie/`S&Q`，`Can be reset`）含 `19` 档标准角（`5.6°..360.0°`）+ `10` 档多帧角（`2F..64F`，高帧率钳位）、严格 `BK4` 双槽隔离（`0x01120024` Speed vs `0x01120028` Angle）、不受 `[Exposure step]` 影响、启用 `Angle` 强制 Still/Movie 快门独立；`[Anti-flicker Shoot.]` 仅 Still；休眠 `Var. Shutter`（`HIGH_RES_SS`）硬拒 `EOPNOTSUPP=95` | 物理 `IRIS` / `ISO-GAIN` / `SHUTTER` / `FULL AUTO` 按键拨盘 + `Shutter Mode` 4 档（`Angle` / `Speed` / `ECS` `24..8000 Hz` / `Off`） |
| **88B** | `[Image Stabilization]` 四重硬锁、`47` 档焦距、**`G81` Ver. 2.00+ 移除 `200mm` 注记**与 `Catalyst` 陀螺 `RTMD` | Movie `[SteadyShot]`（`Active ~1.104x` 强制 `[Distortion Comp.] = Auto`、`Standard` 默认、`Off`，全部 4 项 IS `Can be reset`）；休眠 `Dynamic active` / `Intelligent Active` / `Super Active` / `HYBRID` 硬拒 `EOPNOTSUPP=95`；强制 `Active` 4 重硬锁（`119.88p/100p`、`S&Q >= 100fps`、`HDMI RAW Output = On`、`[De-Squeeze Display] != Off`）；Ver. 2.00+ 允许 `>= 200mm` 镜头开启 `Active`；`[SteadyShot Adjust.]`（`Auto`/`Manual`）+ 精确 `47` 档 `[Focal Length]`（`8..1000mm` 默认 `8mm`）；`Catalyst Prepare` 陀螺 `RTMD` 仅支持 `Off` / `Active`（**禁 `Standard`**）+ 电子触点 E 卡口镜头，`S&Q` 全帧率与 `119.88p/100p` 零可用 | 零机身传感器位移 IBIS（`"The SteadyShot mechanism is fixed."`）；兼容 OSS 镜头仍暴露 `Active / Standard / Off` 3 档（硬拒 `Dynamic Active` 与手动 IBIS 焦距）；`Catalyst` 要求镜头 OSS 开关 `OFF` + 非 `S&Q` `<= 60p` |
| **88C** | `Playback -> [Photo Capture]`、抗复位 `JPEG/HEIF`、3 项 `[View Mode]`（**`G126` 补全**）、`[Rating]` 与 `Slot 1 EROFS=30` | `[Photo Capture]`（`_f 0x6856`）：4K UHD 出 `8.3M`（`3840x2160`）、HD 出 `2.1M`（`1920x1080`），硬阻断 `XAVC S-I DCI 4K`（`4096x2160`、`_g 0x60ce`、`EOPNOTSUPP=95`）；Playback `[JPEG/HEIF Switch]`（`JPEG`/`HEIF(4:2:0)`/`HEIF(4:2:2)`，HLG->HLG HEIF）**抗 `[Camera Settings Reset]`**（区别于 Shooting 侧可复位）；`[View Mode]`（`base 0xe3b7`，抗 Reset）精确 `3` 项（`Date View`/`Folder View(Still)`/`Movie View`），硬拒休眠 `Folder View(MP4)`、`AVCHD View`、`VIEW_MODE_XAVC_S_*`（`EOPNOTSUPP=95`）；`[Rating]` `1..5` 星与抗复位 `[Rating Set(Custom Key)]` 对接 FTP/Smartphone 筛选；`Slot 1` 写请求全数硬阻断 `EROFS=30`（仅沙箱 `Slot 2` 可写） | 零机内静态抓帧（`EOPNOTSUPP=95`）；采用电影机 `Thumbnail > Set Clip Flag`（`OK` / `NG` / `KEEP` + `Delete Clip Flag` + `Filter Clips`） |
| **88D** | `[USB Streaming]` UVC/UAC 双重证伪 vs `[Network Streaming]` `RTMP/RTMPS/SRT Caller`（**`G134` 单向锚定**）与零射频防线 | `ILME-FX3` / `ILME-FX3A` / `ILCE-7SM3` 无原生 UVC/UAC，`[USB Connection Mode]` 仅暴露 `4` 项（`Sel. When Connect`/`MassStorage(MSC)`/`MTP`/`Remote Shooting`），休眠 `OUTPUT_FORMAT_*` 仅含 `4K_12_5P/15P`（无 `4K 30p/25p/24p`）且全拒 `EOPNOTSUPP=95`；`[Movie Rec During Streaming]` 100% 归属 `[Network Streaming]`；`[Network Streaming]` 强制 BLE `Creators' App` 下发、`RTMP`/`RTMPS`（H.264 + 根证书校验）与 `SRT`（H.265/H.264、`AES-128/256`、`48kHz 16-bit 2ch`、**仅出站 `SRT Caller`，硬拒 `SRT Listener`/`Rendezvous`**），帧率锁 `59.94p/50p/29.97p/25p`（禁 `23.98p/24p/120p/S&Q`）、`<= 38 Mbps`（8 档码率桶），`[Movie Rec During Streaming]`（默认 `Disable`）在 4K 或 2K 60p/50p 推流禁 4K 内录并受 `Slot 1 EROFS=30` 拦截，飞行模式硬拒射频发射（`rf_tx_packets == 0`） | 零原生 UVC、零原生 RTMP/RTMPS/SRT/QoS 直推（仅休眠共线符号，硬拒 `EOPNOTSUPP=95`）；依赖外置 `CBK-WA100` / `CBK-RPU7` / `PDT-FP1` |

---

## 三、23 份本地只读供体与四模式洁净室实证（`实测事实`）

- **供体清单（严格 `O_RDONLY | O_NOFOLLOW | O_NONBLOCK`，单次检测耗时 `0.074s <= 2.0s`）**：`20` 份紧凑供体（4 语言 × 3 变体 FX3 `.uxc` 共 `12` 份 + `6` 份 FX3 流媒体动态库 `libInfraSrtLiveStreaming.so` / `libInfraRtmpLiveStreaming.so` / `libInfraVericLiveStreaming.so` / `libInfraVericEsCodecLibrary.so` / `libInfraRtmpLiveStreamingUtilCommon.so` / `libInfraVericUtilCommon.so` + `2` 份 FX6 `.uxc`）与 `3` 份受界 `<= 4096 B` `os.pread` 窗口供体（`FX3 appFw.so` `28` 窗口 + `4` 缺席断言、`FX3 BK4` `2` 窗口、`FX6 appFw.so` `13` 窗口 + `3` 缺席断言）。
- **四模式自检摘要（`实测事实`）**：
  - `LOCAL_DONOR_O_RDONLY`：`[PASS] Phase 383 Stage 88 (88/88) | donors=23 | digest=45b916077e9c`
  - `FX3_CLEAN_ROOM_TEST=1`：`[PASS] Phase 383 Stage 88 (88/88) | mode=CLEAN_ROOM_SYNTHETIC | digest=5525742ade9d`
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`[PASS] Phase 383 Stage 88 (88/88) | mode=CLEAN_ROOM_SYNTHETIC | digest=5525742ade9d`
  - `FX3_FX6_MAC_WORK_ROOT=__fx3_fx6_clean_room_donor_disabled__`：`[PASS] Phase 383 Stage 88 (88/88) | mode=CLEAN_ROOM_SYNTHETIC | digest=f91b04acb74c`

---

## 四、全量验收门禁实测记录（`实测事实`）

| 验收门禁 | 模式 | 实测结果 | 关键红线遥测 |
| :--- | :--- | :--- | :--- |
| **Stage 88 专项单测** | `normal` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / `work_root` 哨兵（4 模） | **4 × `112/112` OK**（每轮 `0.48s–0.64s`） | `leaked=0`, `slot1_writes=0`, `usb_tx=0`, `rf_tx=0` |
| **全量 `outputs/fx3-vm` 单测发现** | `normal` (`LOCAL_DONOR_O_RDONLY`) | **`5,629` tests OK**（`0` failures, `304.5s`） | `0` regressions across Stages 1..88 |
| **全量 `outputs/fx3-vm` 单测发现** | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`5,629` tests OK**（`0` failures, `skipped=39`, `275.3s`） | Clean-room parity verified |
| **`make verify-milestone-375`** | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK`**, **`vm_stages=88/88`**, `pillars=6/6`, `gate160=157/160`, `recovery=69/69` | `usb_tx=0`, `rf_pkts=0`, `slot1_writes=0`, `leaked=0`, `ready_attach=False` |
| **`PYTHONDONTWRITEBYTECODE=1 make clean-audit`** | 仓内洁净与 BYOF 审计 | **`ALL GREEN`**（提交前终验） | `0` `.pyc`、无专有大文件污染 |

---

## 五、后续建议（`推断`）

- 本阶段已完成 Wave 78（`78/78 Waves` 收官情报）全部 4 路子系统与 5 项精密勘误（`G86` `[Exposure Ctrl Type]` 抗复位、`G81` `200mm` 注记演进与 FX6 3 档 OSS、`G126` 3 项 `[View Mode]`、UVC/UAC 双重证伪与 `G134` `SRT Caller` 单向性）的 VM HIL 协同建模与全板 **`88/88`** 集成；后续推进 `fx3-safety` 安全守卫收口时，可直接复现本阶段 `88A..88D` 契约同步更新 `G81`/`G86`/`G126`/`G134`。
