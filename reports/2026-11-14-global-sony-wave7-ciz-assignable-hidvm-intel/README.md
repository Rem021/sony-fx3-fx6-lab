# Phase 75 — Wave-7 Global Sony Ergonomics/CIZ, ARM64 Input Virtualization & Camera NVRAM Shadow Intelligence Sync

# 第 75 阶段 — Wave-7 全球索尼操控与超分、ARM64 输入虚拟化及相机 NVRAM 易失性影子覆写公开情报同步

> **Date / 日期**: `2026-11-14`  
> **Task / 任务**: `Phase 75 (task_174e74884a15)` · **Worktree**: `h70-phase75-wave7-intel-assignable-ciz-big6-auditor`  
> **Target Baseline / 对齐基线**: `ILME-FX6 v6.00/v6.01/v6.02 -> ILME-FX3 v7.00/v7.02` (`CXD90057` + `IMX510` + `GPE0 960x540`)  
> **Clean-Room Compliance / 洁净室声明**: All external findings are synthesized from live web searches (`2026-11-14`) of official Sony firmware/manual documentation, Linux kernel `input`/`uinput` multi-touch specs, QEMU `virtio-input` docs, and public `PMCA-RE`/`BK4`/`CAMSET` reverse-engineering references. Zero proprietary keys or third-party binaries were copied or committed.

---

## 1. Bilingual Executive Synthesis / 中英双语工程摘要

### English Executive Summary

Wave-7 synthesizes public technical intelligence (`2025–2026-11`) across the three pillars backing our **14th Unified Firmware-Lab Auditor** ([`assignable_zoom_ciz_and_fn_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/assignable_zoom_ciz_and_fn_auditor.py)) and our **FX6-on-FX3** clean-room VM/hardware bridge:

1. **Sony FX3 (`v7.00–v7.02`) & FX6 (`v6.00–v6.02`) Ergonomics, `Big6` & `Clear Image Zoom` (`CIZ`)**:
   - **`Big6` Home Screen Customization**: FX3 `v7.00` (Aug 26, 2025) and FX6 `v6.00` (Mar 2026) converged on the **BIG6** Cinema Line perimeter dashboard (**FPS**, **ISO/EI**, **Shutter**, **Aperture / ND Filter**, **Picture Profile / LUT**, **White Balance**) around a read-only central status/audio/media core. On FX3 `v7.00+`, `Big6` requires `S&Q Mode Settings = [Fixed/Variable]`, defaults `[HOME]` to **Custom Button 4**, supports `Home (Lower Left)` toggling (`Aperture` on FX3 vs `ND Filter` on FX6), and temporarily claims the Control Wheel / Multi-Selector for BIG6 navigation while displayed.
   - **Assignable Button Topology (`FX6 1..11` vs `FX3 Custom 1..6 + Focus Hold`)**: FX6 exposes `AssignableButton1..11` in Camera Remote SDK / `appFw.so` (`ASSIGNABLE_SWITCH_1..11`), mapped physically across body `ASSIGN 1–3`, Smart Grip `ASSIGN 4–6` (or `GP-VR100`), Top Handle `ASSIGN 7–8`, LCD/VF `ASSIGN 9`, plus the E-mount lens `Focus Hold` button (`10` physical controls; `10–11` are SDK-reserved). FX3 has body `Custom 1–6`, `Lens Focus Hold`, `Multi-Selector/Joystick`, `AF-ON`, `AEL`, and `Touch Fn`, while Sony's **`XLR-H1`** handle is FX3/FX30/FX2-specific and lacks FX6's `ASSIGN 7–8` switches and top-handle zoom rocker. Consequently, FX6-only targets (`ND Preset`, `Auto ND`, `VF Adjust`, `SDI/HDMI Rec Control`, `Smart Grip 7..9`) must cleanly gray-out or redirect (`SDI/HDMI -> HDMI`, `Push Auto ND -> Push Auto Iris`) with zero null-GPIO faults.
   - **`Clear Image Zoom` (`CIZ`) & Mutual-Exclusion Rules**: `CIZ` delivers By-Pixel Super Resolution up to **`1.5x`** in `4K/QFHD` and **`2.0x`** in `FHD` via the FX3 `T/W` shutter-ring zoom lever (8 variable speed steps) or FX6 Smart Grip / Top Handle rocker (`CIZ` cannot be triggered directly from a static Assignable Button; `Crop Select` in FX6 `v6.00` switches scan mode instead). Crucially, `CIZ` is mutually excluded whenever **`HDMI RAW16`** is active or **`S&Q` / `Rec Frame Rate` reaches `100/120/200/240fps`**, and outside optical zoom AF restricts `Focus Area` / disables `Touch Tracking` & `Face/Eye` priority unless gated cleanly back to `1.00x Optical Zoom Only`.

2. **ARM64 Input & Touch Virtualization (`QEMU virtio-input` + Linux `uinput` / `evdev`)**:
   - On `qemu-system-aarch64`, **`virtio-input-host-pci`** passes host `/dev/input/eventX` (or `uinput` virtual nodes) into the guest with `CONFIG_VIRTIO_INPUT`, while **`virtio-multitouch-pci`** (QEMU 8.1+) and **`vhost-user-input-pci`** provide native/daemon-decoupled multi-touch injection.
   - Capacitive `960x540` `GPE0` LCD touch emulation requires **`INPUT_PROP_DIRECT`**, **`BTN_TOUCH`**, and Linux **Multi-Touch Protocol Type B** (`ABS_MT_SLOT`, `ABS_MT_TRACKING_ID` with `-1` release, `ABS_MT_POSITION_X/Y` scaled to `960x540` and paced at ~`8 ms` intervals so gesture recognizers never drop swipes). Rotary dials and zoom-lever rockers map cleanly to **`EV_REL`** (`REL_DIAL`, `REL_WHEEL`, `REL_WHEEL_HI_RES` at 120 units/notch, `REL_X`) plus **`EV_KEY`** detents.

3. **Camera NVRAM Shadow & Safe Customization (`CAMSET` + Volatile `BK4`)**:
   - FX3 saves `CAMSET*.DAT` (up to 10 slots on Slot 1) at `/PRIVATE/SONY/SETTING/FX3/CAMSET/` (SD) or `/SONY/SETTING/<MODEL>/CAMSET/` (CFexpress Type A), whereas FX6 saves `*.ALL` files on Slot B under `/PRO/CAMERA/`.
   - Internal `BK4` ("ILCE Settings v4") stores dual redundant banks checksummed by `backup.sum` on SPI NOR / eMMC (`nflasha*`), separate from factory calibration (`nfa2`/`nfa6`/`cnflasha`). Session-only RAM tests (`no save`) modify runtime state without executing persistent `bk s` NOR/eMMC sync — guaranteeing **zero flash wear (`bk4_persistent_nvram_writes == 0`)** and preserving factory calibration (`persistent_emmc_writes_authorized = False`).

### 中文工程摘要

Wave-7 同步了 `2025–2026-11` 期间三大领域的最新公开技术情报，直接支撑 **第 14 号统一固件实验室审计器**（[`assignable_zoom_ciz_and_fn_auditor.py`](../../outputs/fx3-firmware-lab/fx3_firmware_lab/assignable_zoom_ciz_and_fn_auditor.py)）及 **FX6-on-FX3** 洁净室架构：

1. **索尼 FX3 (`v7.00–v7.02`) 与 FX6 (`v6.00–v6.02`) 操控自定义、`Big6` 与清晰影像缩放（`CIZ`）**：
   - **`Big6` 主屏与自定义规则**：FX3 `v7.00` 与 FX6 `v6.00` 统一了电影机 **BIG6** 六宫格主界面（帧率、`ISO/EI`、快门、光圈/ND、风格/LUT、白平衡），中心区域为只读状态与音频/存储卡监视。FX3 上启用 `Big6` 须满足 `S&Q 模式设置 = [固定/可变]`，默认绑定至 `C4` 按键，支持左下角切换（FX3 光圈 vs FX6 ND），且展示期间方向转盘临时接管 BIG6 导航。
   - **自定义按键跨机身拓扑（`FX6 1..11` -> `FX3 Custom 1..6 + 镜头保持`）**：FX6 在 SDK/固件中定义 `ASSIGNABLE_SWITCH_1..11`，物理上分布于机身 `1–3`、手柄 `4–6`、顶提 `7–8`、监视器 `9` 与镜头 `Focus Hold`（`10–11` 为 SDK 预留）；FX3 配备 `Custom 1–6`、镜头对焦保持、摇杆、`AF-ON`、`AEL` 与触控图标，且 **`XLR-H1`** 提手不具备 FX6 顶提按键与变焦跷跷板。因此 FX6 独占硬件按键（`ND 预设`、`自动 ND`、`VF 调节`、`SDI/HDMI 录制控制`）必须安全置灰或重定向（如 `Push Auto ND -> Push Auto Iris`、`SDI/HDMI -> HDMI`），保证 `0` 空 GPIO 异常。
   - **清晰影像缩放（`CIZ`）与互斥矩阵**：`CIZ` 在 `4K/QFHD` 下支持 `1.5x`、在 `FHD` 下支持 `2.0x` 全像素超解像，通过 FX3 快门环 `T/W` 变焦杆（8 级变速）或 FX6 变焦跷跷板驱动；当启用 **`HDMI 16-bit RAW`** 或 **`S&Q 100/120/200/240fps`** 高帧率时，`CIZ` 必须自动互斥钳位回 `1.00x`（仅光学变焦），且不崩溃 `icx1295`/`libcamera`。
2. **ARM64 输入与触控虚拟化（`QEMU virtio-input` + Linux `uinput`/`evdev`）**：
   - 使用 `virtio-input-host-pci`、`virtio-multitouch-pci`（QEMU 8.1+）或 `vhost-user-input-pci` 配合 `uinput`，通过 **`INPUT_PROP_DIRECT`**、**`BTN_TOUCH`** 与 **MT Type B 协议**（`ABS_MT_SLOT`、`ABS_MT_TRACKING_ID`、精确匹配 `960x540` `GPE0` 范围的 `ABS_MT_POSITION_X/Y`）仿真电容屏触控追踪；波轮与 `T/W` 变焦杆通过 `EV_REL`（`REL_DIAL`/`REL_WHEEL`/`REL_WHEEL_HI_RES`/`REL_X`）与 `EV_KEY` 注入。
3. **相机 NVRAM 影子覆写与零磨损定制（`CAMSET` + 易失性 `BK4`）**：
   - 区分 SD/CFexpress `CAMSET*.DAT` / `*.ALL` 导出与内部双 Bank `BK4`（`backup.sum` 校验、独立于出厂校准 `nfa2`/`nfa6`/`cnflasha`）；实验性自定义状态仅在 RAM/`/tmp` 易失性影子层生效，严禁触发 `bk s` 持久化刷写，确保 `bk4_persistent_nvram_writes == 0`。

---

## 2. Domain 1: Sony FX3 `v7.00–v7.02` & FX6 `v6.00–v6.02` Ergonomics, `Big6`, `CIZ` & Assignable Buttons

| Capability / 功能维度 | `ILME-FX3` (`v7.00 -> v7.02`) | `ILME-FX6` (`v6.00 -> v6.02`) | Phase 75 Cross-Body Contract / 第 75 阶段跨机身契约 |
| :--- | :--- | :--- | :--- |
| **`Big6` Home Screen** | Added in `v7.00` (Aug 2025); requires `[S&Q Mode Settings] = [Fixed/Variable]`; default `C4`; `Home (Lower Left)` configurable (`Aperture` default) | Added in `v6.00` (Mar 2026); `Home` assignable to `1–9` / `Focus Hold`; `ND Filter` lower-left slot; updated shooting border | `6`-slot `Big6` + `12`-slot `Fn` layout validated in volatile `/tmp` / `CAMSET` JSON shadow (`bk4_persistent_nvram_writes == 0`) |
| **Assignable Button Slots** | Body `Custom 1–6` + `Lens Focus Hold` + `Multi-Selector/Joystick` + `AF-ON` + `AEL` + `Touch Fn`; `XLR-H1` handle has no `ASSIGN 7–8` | `ASSIGN 1–3` (Body) + `4–6` (Smart Grip / `GP-VR100`) + `7–8` (Top Handle) + `9` (LCD/VF) + `Lens Focus Hold` (`10–11` SDK-only) | `ASSIGN 1–6` -> `Custom 1–6`; `Focus Hold` -> `Focus Hold`; `7–11` redirected to Joystick/Touch; FX6-only `ND Preset`/`Auto ND`/`VF Adjust` grayed out (`0` null-GPIO faults) |
| **`Clear Image Zoom` (`CIZ`)** | `1.5x` (`4K/QFHD`) / `2.0x` (`FHD`), `T/W` shutter-ring zoom lever (`8-Step` variable speed `UIBIZ_KEY_ZOOM_TELE/WIDE_SPEED_1..8`) | `1.5x` (`4K/QFHD`) / `2.0x` (`FHD`), Smart Grip / Top Handle zoom rocker (`ZOOM_SPEED_REC_1..8`); `Crop Select` in `v6.00` | `Optical Zoom Only` (`1.00x`) / `CIZ` (`1.5x` 4K, `2.0x` FHD) / `Digital` (`4.0x`); `HDMI RAW16` & `S&Q 120/240fps` cleanly clamp `CIZ` -> `1.00x` (`0` `icx1295`/`libcamera` crashes) |
| **Touch AF & Anamorphic Desqueeze** | `960x540` touch LCD; `Touch Focus` / `Touch Tracking` (`Touch Shutter` disabled in movie/cine); `1.3x / 1.5x / 1.6x / 2.0x` de-squeeze (`v7.00+`); `Focus Magnifier x4.0` | `Touch Focus` / `Touch Tracking`; `1.3x / 2.0x` de-squeeze (`v6.00+`); `Focus Magnifier x3/x6` | Exact `960x540` `GPE0` -> `[0..1]` `IMX510` 627-pt (`33x19`) PDAF transform with `4.0x` crop & `1.3x/1.5x/1.6x/2.0x` inverse-X desqueeze math |

**Public Citations (Domain 1)**:
- Sony ILME-FX3 Firmware Ver. 7.00 / 7.02 & Help Guide (BIG6, S&Q Fixed/Variable, Clear Image Zoom, HDMI RAW, Anamorphic De-squeeze):
  - <https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/downloads>
  - <https://www.newsshooter.com/2025/08/26/sony-fx3-v7-00-and-fx30-v6-00-firmware-updates/>
  - <https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000285051.html>
- Sony ILME-FX6 Firmware Ver. 6.00 / 6.01 / 6.02, Assignable Buttons (`1..9` + `Focus Hold`, SDK `10..11`), Clear Image Zoom & Top Handle vs `XLR-H1`:
  - <https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx6v/downloads>
  - <https://www.newsshooter.com/2026/03/18/sony-fx6-firmware-v6-00-released/>
  - <https://helpguide.sony.net/pro/fx6/v1/en/contents/TP1000180000.html>

---

## 3. Domain 2: ARM64 Input & Touch Virtualization (`QEMU virtio-input` + `uinput` / `evdev`)

| Component / 组件 | Mechanism / 实现机制 | Key Parameters / 关键参数 | FX3/FX6 VM Integration / 虚拟机映射意义 |
| :--- | :--- | :--- | :--- |
| **QEMU Device Backends** | `virtio-input-host-pci` / `virtio-multitouch-pci` (QEMU 8.1+) / `vhost-user-input-pci` | `evdev=/dev/input/eventX`, `CONFIG_VIRTIO_INPUT=y`, Unix chardev socket | Passes host touch & rotary events cleanly into AArch64 `virt` guest Linux |
| **Capacitive Touch (`GPE0`)** | Linux `uinput` / `evdev` Multi-Touch Protocol Type B | `INPUT_PROP_DIRECT`, `BTN_TOUCH`, `ABS_MT_SLOT`, `ABS_MT_TRACKING_ID` (`-1` lift), `ABS_MT_POSITION_X` `[0..960]`, `ABS_MT_POSITION_Y` `[0..540]` | Simulates `960x540` `GPE0` capacitive Touch Focus / Touch Tracking & BIG6 cell taps at ~`8 ms` pacing |
| **Rotary Dial & `T/W` Rocker** | `EV_REL` + `EV_KEY` via `uinput` / `rotary-encoder` | `REL_DIAL`, `REL_WHEEL`, `REL_WHEEL_HI_RES` (`120`/notch), `REL_X`, `KEY_ENTER` | Emulates FX3 front/rear dials, Control Wheel, and 8-step `T/W` zoom lever rocker |

**Public Citations (Domain 2)**:
- Linux Kernel Multi-Touch (`evdev` Type B) & `uinput` Documentation: <https://docs.kernel.org/input/multi-touch-protocol.html>, <https://docs.kernel.org/input/uinput.html>
- QEMU `virtio-input` / `virtio-multitouch-pci` / `vhost-user-input` Architecture & Upstream Docs: <https://www.qemu.org/docs/master/system/devices/virtio-input.html>, <https://www.kraxel.org/blog/2016/04/qemu-and-evdev-passthrough/>

---

## 4. Domain 3: Camera NVRAM Shadow & Safe Customization (`CAMSET` + Volatile `BK4`)

- **FX3 `CAMSET*.DAT` Paths**: Slot 1 only (up to 10 presets):
  - SD Card: `/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT`
  - CFexpress Type A: `/SONY/SETTING/ILME-FX3/CAMSET/CAMSET01.DAT`
  - Excluded from `CAMSET`: IPTC/Copyright, Custom WB 1–3, Face Memory, Network/FTP keys, Area/Date/Time.
- **FX6 `*.ALL` Paths**: Slot B under `/PRO/CAMERA/*.ALL` (`Project -> All File -> Save/Load`).
- **`BK4` Dual-Bank Flash vs Volatile RAM Shadow**:
  - Persistent `BK4` ("ILCE Settings v4") maintains dual SPI NOR / eMMC banks protected by `backup.sum`, physically separated from factory calibration (`nfa2` / `nfa6` / `cnflasha`).
  - Research & Stage-B overlays (`no save` volatile runtime writes vs `bk s` persistent NOR sync) allow `Big6` (6 slots), `Fn` (12 slots), and Assignable button remapping to persist purely in volatile `/tmp` / `CAMSET` JSON shadows during emulation/Stage-B sessions with **`bk4_persistent_nvram_writes == 0`** and **`persistent_emmc_writes_authorized == False`**.

**Public Citations (Domain 3)**:
- Sony FX3 Save/Load Settings (`CAMSET`) & FX6 `All File` Help Guides: <https://helpguide.sony.net/ilc/2035/v1/en/contents/TP1000267806.html>, <https://helpguide.sony.net/pro/fx6/v1/en/contents/TP1000180054.html>
- `PMCA-RE` (`CAMSET` / `BK4` research) & Sony Alpha/Cinema `BK4` NVRAM Bank Tools: <https://github.com/ma1co/Sony-PMCA-RE>, <https://github.com/leogenot/sony-a7iv-feature-research>
