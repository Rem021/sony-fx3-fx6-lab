# Phase 379（Stage 87 — `87/87`）：Wave 77 `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` `[Movie Settings]` / `VPG200-VPG400` / `[Priority Set in AWB]` / `[Shutter AWB Lock]` / `[Touch Operation]` / `G109` & `G104` / `[Screen Reader]` SKU 门禁 HIL 协同仿真闭环报告

- **日期**：`2026-11-21`
- **任务 / 阶段**：`H482` · **Phase 379 · VM HIL Stage 87（`87/87` Full-Board VM Co-Emulation Stages!）**
- **一手情报基线**：[Wave 77 实机深度审计报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h482-phase379-vm-stage87-movieset-vpg-awbprio-touchpad-screenreader-version-hil/reports/2026-11-18-global-sony-wave77-movieset-vpg-awbprio-atw-touchpad-screenreader-version-intel/README.md)

---

## 一、结论先行（Executive Summary）

- **交付结论（`实测事实`）**：已完成 **Phase 379 Stage 87（`87/87`）** 确定性 HIL 协同仿真器实现、全板编排器接入、108 项四模式单测与文档闭环，全部 5 项验收门禁一次性通过（`0` 失败、`0` 字节专有固件泄漏、`0` USB/RF 发包、`0` 卡槽写入）。
- **核心交付文件（严格限定 5 份所属文件）**：
  1. [realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h482-phase379-vm-stage87-movieset-vpg-awbprio-touchpad-screenreader-version-hil/outputs/fx3-vm/realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulator.py)（Schema `phase379_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulation_v1`）
  2. [fx3_vm_coemulation_suite.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h482-phase379-vm-stage87-movieset-vpg-awbprio-touchpad-screenreader-version-hil/outputs/fx3-vm/fx3_vm_coemulation_suite.py)（接入 `stage87_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_hil` -> `87/87`）
  3. [test_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulator.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h482-phase379-vm-stage87-movieset-vpg-awbprio-touchpad-screenreader-version-hil/outputs/fx3-vm/tests/test_realhw_movieset_vpg_awbprio_touchpad_screenreader_version_coemulator.py)（`108` 项前向兼容四模式单测）
  4. [outputs/fx3-vm/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h482-phase379-vm-stage87-movieset-vpg-awbprio-touchpad-screenreader-version-hil/outputs/fx3-vm/README.md)（补录 Phase 379 Stage 87 CLI 与技术契约）
  5. [reports/2026-11-21-phase379-vm-stage87-movieset-vpg-awbprio-touchpad-screenreader-version-hil/README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h482-phase379-vm-stage87-movieset-vpg-awbprio-touchpad-screenreader-version-hil/reports/2026-11-21-phase379-vm-stage87-movieset-vpg-awbprio-touchpad-screenreader-version-hil/README.md)（本闭环报告）
- **硬件安全态势（`实测事实` + `推断`）**：
  - `ready_for_live_camera_attach = False`、`live_attach_authorized = False`、`cross_model_flash_authorized = False`、`emmc_writes_authorized = False`、`slot1_bodydata_write_authorized = False`、`slot1_writes = 0`、`usb_tx_packets = 0`、`rf_tx_packets = 0`、`raw_firmware_bytes_leaked = 0`。
  - **推断**：本阶段继续维持 Tier-0 只读与离线台架隔离边界（`HARD NO-GO` 物理实机直连/跨机型刷写），任何试图向 `Slot 1` 写入 `BODYDATA.DAT` 或执行 `[Software Update]`/`Version Up` 的路径均以 `EROFS (errno 30)` 确定性拒止。

---

## 二、4 路子模型与 Wave 77 五大勘误落地对照（`实测事实`）

| 子模型 | 覆盖范围与 Wave 77 勘误修正 | FX3 Ver. 7.02 核心契约 | FX6 Ver. 6.01 差异化契约 |
| :--- | :--- | :--- | :--- |
| **87A** | `[File Format]` / `[Movie Settings]` 6 编码、`24.00p` 隔离、5 阶卡速与 **`G139` 勘误** | 精确 `6` 编码（默认 `XAVC S HD`，Ver. 3.00+ `XAVC S-I DCI 4K`）；休眠 `8K`（`xavc_hs_8k`）拒 `EOPNOTSUPP=95`；跨 `24.00p` 触发 `MODEL_EVENT_REBOOT_BY_CROSS_2400P` + 回放隔离 + `4K Output Set.(HDMI Only)` 互斥 + `S&Q 48fps` 独占 `24.00p + DCI 4K`；5 阶 ELF 门禁（`100/200/400/600/1350 MBPS`）：`S&Q XAVC S HD 100/120fps` 仅需 `SDXC V60+`（仅 `200/240fps` 需 `V90+`）、`S&Q DCI 4K` 禁 `100/120fps`（最高 `60fps/600M`）、`S&Q XAVC S-I 4K 1200M + Proxy` 触发 `1350MBPS VPG400`；双项均 `Can be reset` | `Project > Rec Format`（`RAW & XAVC-I` / `RAW(HDMI) & XAVC-I` / `XAVC-I` `Class300` max `600M VBR` / `XAVC-L` QFHD `150M/100M` & HD `50M/35M`）；硬拒休眠 `Class480`、`XAVC-L25` 与 `XAVC-L DCI 4K`（`EOPNOTSUPP=95`） |
| **87B** | `[Priority Set in AWB]`、Still 独占 `[Shutter AWB Lock]`、`2500K..9900K` `[C.Temp./Filter]` | `[Priority Set in AWB]`（`Standard/Ambience/White`，`Can be reset`）在 Still/Movie + `Flexible ISO` 下 `Auto` 生效，在 `Cine EI`/`Cine EI Quick` 下因禁 `Auto`/`Underwater Auto` 而失效；`[Shutter AWB Lock]`（`Off/Shutter Half Press/Cont. Shooting`）**严格 Still 独占**（Movie/`S&Q` 拒 `EOPNOTSUPP=95`）且**抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 复位）；`[C.Temp./Filter]` 为 `2500K..9900K`（`75` 档）、`A7..B7`（`29` 步 @ `0.5`）、`G7..M7`（`57` 步 @ `0.25`） | 物理三段 `WHT BAL`（`B/A/PRESET`）、`Preset`（Custom `3200/4300/5600/6300K`；Cine EI `3200/4300/5500K`）、`ATW`（`2000K..15000K`、`Speed 1..5`、`ATW Hold`，Cine EI 禁用）、`Tint -99..+99`、`R/B Gain -99.0..+99.0`、`Shockless White Off/1/2/3` |
| **87C** | `[Touch Operation]` 4 项 vs 休眠 EVF `[Touch Panel/Pad]` 与 **`G109` 勘误** | `Setup -> [Touch Operation]` 精确 `4` 项（全抗 Reset）；无 EVF 机身硬拒休眠 `[Touch Panel/Pad]`、`Touch Pad Settings/Area Set./vertical` 与 `Touch Shutter`（`EOPNOTSUPP=95`）；**`G109` 勘误**：`[Focus Assistant]` 4 项 + `[Peaking Display]` 3 项共 **7 项全抗 `[Camera Settings Reset]`**（仅 `[Initialize]` 复位），`[Peaking]` 零 HDMI 泄漏，`[AF in Focus Mag.]` 严格 Still 独占并实施 5 项硬禁用 | `Monitoring > Peaking` 严格 `3` 项 ELF 绑定（`Setting`、`Level`、`Color B&W/Red/Yellow/Blue`）；硬拒休眠 UXC `Peaking Type`/`Normal/Color`/`Peaking Frequency`（`EOPNOTSUPP=95`，`0` ELF 参数） |
| **87D** | `[Accessibility]`/`[Screen Reader]` SKU 门禁、双槽 `[Version]`（**`G104` 勘误**）与 `EROFS=30` | `screen_reader/screen_reader.cpp`（`SLOW_2..FAST_4`、`0..15` 音量）受 SKU 门禁限制，`ILME-FX3`/`ILME-FX6` UI 暴露均为 **`0` 项**（`EOPNOTSUPP=95`），零 HDMI 音频联动；**`G104` 勘误**：`libInfraGetVersion.so` 仅导出 `InfraGetVersion` / `InfraGetVersionLens`，`[Version]` **仅含 `Body` & `Lens` 2 槽**（卡口适配器共用 `Lens` 槽，拒独立第 3 槽与 MI-Shoe 版本）；`Airplane Mode = On` 静默 Ver. 6.00+ 更新红点（`rf_tx_packets = 0`）；`[Software Update]` / `Slot 1 BODYDATA.DAT` 硬阻断 `EROFS=30` | `Maintenance > Version`（`Body`、`Lens`、`Ext. Unit`），升级硬要求 `Slot B` + 外接 `AC` 适配器；自动化台架同样以 `EROFS=30` 硬阻断刷写；`procam/screen_reader` 门禁休眠（`0` UI 暴露） |

---

## 三、20 份本地只读供体与四模式洁净室实证（`实测事实`）

- **供体清单**：`17` 份紧凑供体（4 语言 × 3 变体 FX3 `.uxc` 共 `12` 份 + `libInfraGetVersion.so` `10,144 B` + `libupdatermedia.so` `10,144 B` + `libInfraMediaDetect.so` `98,224 B` + 2 份 FX6 `.uxc`）与 `3` 份受界 `<= 4096 B` `os.pread` 窗口供体（`FX3 appFw.so` 27 窗口 + 2 缺席断言、`FX3 BK4` 2 窗口、`FX6 appFw.so` 11 窗口 + 3 缺席断言）。
- **四模式自检摘要（`实测事实`）**：
  - `LOCAL_DONOR_O_RDONLY`：`[PASS] Phase 379 Stage 87 (87/87) | donors=20 | digest=c7089122a0dd`
  - `FX3_CLEAN_ROOM_TEST=1`：`[PASS] Phase 379 Stage 87 (87/87) | mode=CLEAN_ROOM_SYNTHETIC | digest=4da960b8243f`
  - `FX3_FX6_FORCE_CLEAN_ROOM=1`：`[PASS] Phase 379 Stage 87 (87/87) | mode=CLEAN_ROOM_SYNTHETIC | digest=4da960b8243f`
  - `FX3_FX6_MAC_WORK_ROOT=__fx3_fx6_clean_room_donor_disabled__`：`[PASS] Phase 379 Stage 87 (87/87) | mode=CLEAN_ROOM_SYNTHETIC | digest=85e7a1a9c916`

---

## 四、全量验收门禁实测记录（`实测事实`）

| 验收门禁 | 模式 | 实测结果 | 关键红线遥测 |
| :--- | :--- | :--- | :--- |
| **Stage 87 专项单测** | `normal` / `FX3_CLEAN_ROOM_TEST=1` / `FX3_FX6_FORCE_CLEAN_ROOM=1` / `work_root` 哨兵（4 模） | **4 × `108/108` OK**（每轮 `~0.30s`） | `leaked=0`, `slot1_writes=0`, `usb_tx=0`, `rf_tx=0` |
| **全量 `outputs/fx3-vm` 单测发现** | `normal` (`LOCAL_DONOR_O_RDONLY`) | **`5,517` tests OK**（`0` failures, `274.2s`） | `0` regressions across Stages 1..87 |
| **全量 `outputs/fx3-vm` 单测发现** | `FX3_FX6_FORCE_CLEAN_ROOM=1` | **`5,517` tests OK**（`0` failures, `skipped=39`, `238.0s`） | Clean-room parity verified |
| **`make verify-milestone-364`** | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK`**, **`vm_stages=87/87`**, `pillars=6/6`, `gate156=157/160`, `recovery=68/68` | `usb_tx=0`, `rf_pkts=0`, `slot1_writes=0`, `leaked=0`, `ready_attach=False` |
| **`make verify-milestone-324`** | `LOCAL_DONOR_O_RDONLY` & `CLEAN_ROOM_SYNTHETIC` | **`status=OK`**, **`vm_stages=87/87`**, `pillars=6/6`, `gate142=157/160`, `recovery=68/68` | `usb_tx=0`, `rf_pkts=0`, `slot1_writes=0`, `leaked=0`, `ready_attach=False` |
| **`PYTHONDONTWRITEBYTECODE=1 make clean-audit`** | 仓内洁净与 BYOF 审计 | **`ALL GREEN`**（见提交前终验） | `0` `__pycache__`、无专有大文件污染 |

---

## 五、后续建议（`推断`）

- 本阶段已完成 Wave 77 全部 4 路子系统与 5 项勘误（`G139`、`G109`、`G104`、FX6 `Peaking` 3 项真相与 `Screen Reader` SKU 门禁）的 VM HIL 协同建模与全板 `87/87` 集成；后续若推进 `fx3-safety` 守卫波次，可直接复现本阶段 `87A..87D` 契约同步更新 `G104`/`G109`/`G139` 及新增 `Screen Reader` 独立门禁守卫。
