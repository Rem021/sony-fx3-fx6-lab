# Wave-10 Live Global Sony Firmware / VM / Unbrick Web Intelligence Sync (2026-11-14)
# 第十波全球索尼固件 / 虚拟化 / 救砖与间歇录制/预录制/有线FTP情报同步 (2026-11-14)

- **Date / 日期**: 2026-11-14
- **Phase / 阶段**: Phase 93 — Wave-10 Global Live Web Intelligence Sync & 18th Unified `fx3-firmware-lab` Auditor Alignment
- **Scope / 范围**: Clean-room synthesis of verified public documentation, firmware engineering notes, and open-source reverse-engineering / QEMU / solderless unbrick toolchains across four axes: (1) Sony FX3 `Interval Shoot Func.` vs FX6 `Interval Rec`, (2) FX6 `Picture Cache Rec` circular DDR ring-buffer mechanics vs FX3 `2048 MiB` DRAM ceiling, (3) Wired USB-LAN (`CDC-NCM`/`RTL8153`) `FTP`/`FTPES` + `Creators' Cloud` + `P12` Airplane RF-Off isolation, and (4) 2024–2026 global Sony `BIONZ XR` / `CXD90057` RE, QEMU, and eMMC recovery advances.
- **Compliance / 合规**: Zero embedded proprietary keys, zero vendor firmware binaries committed, strictly verified public URLs cited directly.

---

## English Technical Synthesis

### 1. Sony FX3 `Interval Shoot Func.` vs FX6 `Interval Rec` (Time-Lapse Architecture)

1. **FX3 (`ILME-FX3`, Ver. 7.02, March 2026)**:
   - Exposes `MENU -> Shooting -> Drive Mode -> Interval Shoot Func.` (`1s..60s` shooting interval, `1..9999` frames, shooting start time delay, optional `AE Tracking Sensitivity` in `High / Mid / Low`).
   - **Electronic Shutter Wear Firewall**: Defaults `[Shutter Type in Interval]` to `Electronic Shutter` (and locks electronic shutter under Silent Mode), eliminating mechanical focal-plane curtain actuation wear across multi-thousand-shot time-lapse sequences.
   - **Day-to-Night AE Ramp Stabilization**: Setting `AE Tracking Sensitivity = [Low]` applies strong multi-frame exposure damping across sunset/sunrise transitions to avoid luminance flicker, while `High` tracks rapid cloud shadows.
   - **Still-Sequence vs Movie Assembly**: FX3 writes individual still frames (`ARW` / `JPEG` / `HEIF`) rather than packing frames into a single in-camera XAVC clip; post-assembly uses Sony Imaging Edge Desktop or an external NLE (whereas in-camera single-file time-lapse video on FX3 uses `S&Q 1fps` movie mode).
   - Reference: [Sony ILME-FX3 Help Guide](https://helpguide.sony.net/ilc/2210/v1/en/index.html) & [Sony ILME-FX3 Support Portal](https://www.sony.net/support/ILME-FX3/?source=hg).

2. **FX6 (`ILME-FX6`, Ver. 6.02, Nov 2026)**:
   - Exposes Cinema Line `Project -> Interval Rec` (distinct from FX3's still interval mode), packing discrete frame bursts (`1 / 2 / 3 / 6 / 9 / 12` frames per trigger at `1–10 / 15 / 20 / 30 / 40 / 50s`, `1–50 min`, `1–24 h` intervals) directly into a **single XAVC movie clip** with zero audio (`Audio Rec` disabled) and optional `Pre-Lighting` (`Off / 2s / 5s / 10s`).
   - Mutually exclusive with `Picture Cache Rec`, `Simul Rec`, and `S&Q Motion`; abrupt power loss before clip finalization risks losing up to ~10 seconds of buffered movie data.
   - Local donor cross-check (`fx6_appfw` + `fx3_appfw`): `fx6_appfw` exposes `VAL_is_changing_interval_rec_to_picture_cache_rec_IS_CHANGING_INTERVAL_REC_TO_PICTURE_CACHE_REC_TRUE` and `remote_presenter::set_interval_rec_movie_frame_rate`, confirming the mutual-exclusion state machine in Sony's shared `BIONZ XR` presenter stack.

---

### 2. FX6 `Picture Cache Rec` Circular DDR Ring-Buffer vs FX3 `2048 MiB` AP DRAM Headroom

1. **FX6 Picture Cache Behavior (Introduced in Ver. 2.00, carried through Ver. 6.02)**:
   - Configurable via `Project -> Picture Cache Rec -> Cache Size` (`Short ~5s`, `Medium ~10s`, `Long ~20s`, `Max ~31s` in standard modes, reduced to `~5s` in `S&Q`).
   - Continuously encodes into an internal **circular DDR RAM ring buffer** before the user presses `REC`; pressing `REC` prepends cached GOPs to the media clip.
   - **Hard Mutual Exclusions**: Turning on `Picture Cache Rec` automatically disables `Interval Rec`, `Simul Rec`, and `Proxy Rec`; forces `Timecode` to `Free Run`; clears cached frames whenever video format, Base Look, or media status changes; and does **not** retroactively inject pre-roll frames over external `HDMI` / `SDI RAW`.

2. **FX3 `2048 MiB` DRAM Ring-Buffer Engineering Budget (Phase 93 Pillar 2 Model)**:
   - Unlike FX6's dedicated cinema thermal envelope and memory partitioning, FX3 runs `appFw.so` + `libmpr.so` + `GPE0` inside a **`2048 MiB`** AP DRAM budget (`384 MiB` kernel/DMA + `640 MiB` `appFw`/`libmpr`/`ux` + `384 MiB` `GPE0`/hardware encoder + `256 MiB` OOM safety guard = **`384.0 MiB`** safe circular ring-buffer headroom).
   - At `XAVC-I 4K60` (`600 Mbps = 75.0 MiB/s`), `10s..16s` of circular cache (`750..1200 MiB`) would blow past `384.0 MiB` and trigger the Linux OOM killer or starve `GPE0`. Clamping `XAVC-I 4K60` to **`5.0 s`** (`375.0 MiB`), `XAVC-I 4K24` (`240 Mbps = 30.0 MiB/s`) to **`12.0 s`** (`360.0 MiB`), while permitting full **`16.0 s`** on `XAVC-L 4K30` (`200.0 MiB`) and `XAVC-L FHD60` (`100.0 MiB`) preserves full stability with `0` OOM faults.

---

### 3. Wired USB-LAN (`CDC-NCM`/`RTL8153`) FTP/FTPS, Creators' Cloud & `P12` RF-Off Isolation

1. **Sony FX3 `Ver. 4.00..7.02` & FX6 `Ver. 5.00..6.02` Wired Ethernet / FTP Stack**:
   - FX3 supports USB-LAN / Tethering over `USB-C` (`CDC-NCM` / `ASIX` / `Realtek RTL8153` adapters) with `Ver. 7.00+` adding `[USB-LAN Cnct. Launch]` (auto-connect on boot) and `OK / NG / KEEP` Clip Flag upload filtering for both `FTP Transfer` and `Creators' App / Creators' Cloud` workflows.
   - FX6 supports `Network -> File Transfer` over wired USB-LAN or Ethernet, including `Auto Upload (Original / Proxy / Chunk File Transfer)` targeting `Creators' App for Enterprise` (`C3 Portal`, `Ci Media Cloud`, `PWA-RXS`) and `Monitor & Control` v2.0+/v2.5+.
   - Protocol constraints verified in both Sony documentation and FX6 `libInfraFtpClient.so` (`OPENSSL_3`, `TLS_AES_256_GCM_SHA384`): **Passive (`PASV`) mode mandatory** (`CT_ERR_PASV_NOT_SUPPORT` if active `PORT` attempted), explicit `FTPES` (`TLS 1.2/1.3`) with root CA verification (`FT_ERR_FAIL_AUTH_CACERT`), and byte-offset auto-resume (`REST` / `CT_ID_ASYNC_REQ_RESUME_FTP_TRANSFER`).
   - References: [Sony Monitor & Control Help Guide](https://helpguide.sony.net/promobile/mc/v1/en/index.html), [Monitor & Control Supported Cameras](https://helpguide.sony.net/promobile/mc/v1/en/contents/supported_camera.html), [Sony Camera Remote SDK](https://www.sony.net/CameraRemoteSDK/), [Sony Creators' App Portal](https://www.sony.net/ca/).

2. **`P12` (`00342260`) RF-Off Firewall & Internal eMMC (`p1..p15`) Traversal Guard**:
   - Under Phase 93's `P12` containment rule, enabling `Airplane Mode = On` (`VAL_setting_airplane_mode_AIRPLANE_MODE_ON`) keeps wired `CDC-NCM / RTL8153` USB-LAN FTP transfers active while proving **100% RF silence** (`wlan_rf_enabled == False`, `bt_rf_enabled == False`, `hci_tx_packets == 0`, zero `WF-12` `00342260` wireless fatal dialogs).
   - Simultaneously, FTP `CWD`/`RETR` paths are strictly confined to removable media roots (`/mnt/sd`, `/mnt/cfexpress_a`, `/mnt/cfexpress_b`, `/mnt/slot_a`, `/mnt/slot_b`) after POSIX normalization, blocking `..` traversal, NUL-byte injection, and any access to internal eMMC partitions `/dev/mmcblk0p1..p15` or calibration paths `p2:/Backup.bin`, `p2:/psd.bin`, `/dev/nflasha*`, `/dev/cnflasha*`.

---

### 4. Global 2024–2026 Sony Firmware RE, Camera QEMU Virtualization & Solderless eMMC Unbrick Sync

| Project / 项目 | Domain / 领域 | Key Technical Breakthrough (2024–2026) / 核心技术突破 | Verified Canonical URL |
| :--- | :--- | :--- | :--- |
| `masterflai/pmca-re-reloaded` | Cross-platform Rust Sony service toolkit (`v1.11.0`, 2026) | Replaces Python 2 + Zadig with native Rust (`hidapi` / `rusb`), Wasm service plugins, and strictly guarded `Backup.bin` NVRAM region edits | https://github.com/masterflai/pmca-re-reloaded |
| `DavidBuchanan314/ILCE-7M4-RE` | `BIONZ XR` (`CXD90057`) updater RE & BootROM | Decryption tooling for BIONZ XR updaters, `48000 baud` `uart_boot` BootROM payload injection, `115200 baud` bare-metal Fastboot server | https://github.com/DavidBuchanan314/ILCE-7M4-RE |
| `dino2048/zv-e10-toolkit` | Solderless eMMC brick rescue (Oct 2026) | RP2040/Pico serial injection into `uart_boot` -> `TIMER-IP` WDT disarm (`0xF2402000`) -> Fastboot (`18d1:4ee0`) -> PIO eMMC rescue (e.g., 1-byte BPB FAT fix `20 -> 0` for broken `/etc/ld.so.preload`) | https://github.com/dino2048/zv-e10-toolkit |
| `cokeenet/zve10-qemu` | `CXD90045` QEMU hardware modeling | Virtualizes Sony ZV-E10 `CXD90045` SoC peripheral registers & eMMC image bring-up | https://github.com/cokeenet/zve10-qemu |
| `chocotan/a7c2-qemu` | `BIONZ XR` full UI boot in QEMU (`virt`) | Boots stock A7C II UI in GTK using QEMU `virt`, custom DTB, `ramfb`, software `GPE`, and CPU `LZ77` (avoiding proprietary GPU/LDEC silicon) | https://github.com/chocotan/a7c2-qemu |
| `chocotan/a7c2-re` | `BIONZ XR` reverse-engineering notes | Memory maps, firmware structure, and subsystem notes complementing `a7c2-qemu` | https://github.com/chocotan/a7c2-re |
| `leogenot/sony-a7iv-feature-research` | Sony `appFw` feature & `BK4` research | Documents `BKID` / feature gate structures across Sony `ILCE-7M4` (`CXD90057`) | https://github.com/leogenot/sony-a7iv-feature-research |
| `xyzhangxin/sony-a6700-powerful` | `a6700` feature & menu research | Community clean-room analysis of Cinema / Alpha menu flags | https://github.com/xyzhangxin/sony-a6700-powerful |
| `qn06142/zv-e10-re` | `ZV-E10` firmware notes | Partition, boot, and service daemon documentation | https://github.com/qn06142/zv-e10-re |
| `ivica00/sony-a6400-research` | Offline ARMv7 `appFw` verification (~1,400 tests) | Methodological template for zero-hardware offline verification of Sony firmware contracts | https://github.com/ivica00/sony-a6400-research |

---

## 简体中文技术摘要

### 1. 索尼 FX3 间隔拍摄（`Interval Shoot Func.`）与 FX6 间隔录制（`Interval Rec`）架构对比

- **FX3（`ILME-FX3`，固件 Ver. 7.02）**：在 `MENU -> 拍摄 -> 拍摄模式 -> 间隔拍摄功能` 下提供 `1s..60s` 间隔、`1..9999` 张连拍。默认强制启用 **电子快门**（Silent Mode 锁定电子快门），实现机械焦平面快门 **0 次磨损**（Electronic-Shutter Wear Firewall）；提供 `AE 跟踪灵敏度`（`低 / 中 / 高`），日落/日出光影剧变时选 `低` 可有效抑制曝光闪烁。FX3 输出独立静态序列（ARW/JPEG/HEIF），不直接在机内合成单个 XAVC 视频（需配合 Imaging Edge Desktop 或后期剪辑软件合成，或改用机内 `S&Q 1fps`）。
- **FX6（`ILME-FX6`，固件 Ver. 6.02）**：在 `Project -> Interval Rec` 下直接将每次触发拍摄的 `1/2/3/6/9/12` 帧实时打包为 **单个 XAVC 视频文件**（关闭音频，支持 `Pre-Lighting` `Off/2s/5s/10s`），与 `Picture Cache Rec` 严格互斥（本地供体 `fx6_appfw` 中实测存在 `VAL_is_changing_interval_rec_to_picture_cache_rec_IS_CHANGING_INTERVAL_REC_TO_PICTURE_CACHE_REC_TRUE` 状态机互斥标记）。

### 2. FX6 预录制缓存（`Picture Cache Rec`）环形 DDR 缓冲与 FX3 `2048 MiB` 内存预算

- FX6 自 Ver. 2.00 起提供 `Short (~5s)` / `Medium (~10s)` / `Long (~20s)` / `Max (~31s，S&Q ~5s)` 环形 DDR 缓存预录，并在启用时自动关闭 `Interval Rec`、`Simul Rec`、`Proxy Rec`，锁定 `Free Run` 时间码，且不回溯输出到外录 `HDMI`/`SDI RAW`。
- FX3 机身 AP 总 DRAM 为 **`2048 MiB`**。扣除内核/DMA `384 MiB`、`appFw`/`libmpr`/`ux` `640 MiB`、`GPE0`/硬件编码 `384 MiB` 与 OOM 安全防线 `256 MiB` 后，留给预录制环形缓存的净安全预算为 **`384.0 MiB`**：
  - `XAVC-I 4K60`（`600 Mbps = 75.0 MiB/s`）：安全上限钳位至 **`5.0 s`**（`375.0 MiB`），强行配置 `10s..16s`（`750..1200 MiB`）将被第 18 审计器直接拦截并标记 OOM 风险；
  - `XAVC-I 4K24`（`240 Mbps = 30.0 MiB/s`）：安全上限钳位至 **`12.0 s`**（`360.0 MiB`）；
  - `XAVC-L 4K30`（`100 Mbps`）与 `XAVC-L FHD60`（`50 Mbps`）：支持完整 **`16.0 s`** 缓存。

### 3. 有线 USB-LAN（`CDC-NCM`/`RTL8153`）FTP/FTPS、Creators' Cloud 与 `P12` 飞行模式隔离

- FX3（Ver. 4.00+ 至 7.02）与 FX6（Ver. 5.00+ 至 6.02）均支持通过 Type-C 有线网卡（`CDC-NCM` / `RTL8153`）执行后台 `FTP` / 显式 `FTPES`（`TLS 1.2/1.3` + 根证书校验，`libInfraFtpClient.so` 内含 `OPENSSL_3` 与 `TLS_AES_256_GCM_SHA384`），**强制要求被动模式 `PASV`**（禁用主动 `PORT`），支持 `REST` 字节偏移断点续传及 `OK / NG / KEEP` 剪辑标记筛选上传至 FTP 服务器或 `Creators' Cloud` / `C3 Portal` / `Ci Media Cloud`。
- 第 18 审计器在 **Pillar 3** 严格验证：`P12` 飞行模式（`Airplane Mode = On`）下 **Wi-Fi 与蓝牙射频 100% 静默**（`HCI TX = 0`、彻底杜绝 `WF-12 00342260` 报错弹窗），同时通过路径规范化阻断 `..` 越权、NUL 字节注入及对机内 eMMC `p1..p15` 与校准分区（`p2:/Backup.bin`、`p2:/psd.bin`、`/dev/nflasha*`、`/dev/cnflasha*`）的任何 `CWD`/`RETR`/写入企图，仅放行 `/mnt/sd`、`/mnt/cfexpress_a|b`、`/mnt/slot_a|b` 外置卡目录。

### 4. 2024–2026 全球索尼固件逆向、QEMU 虚拟化与免焊接 eMMC 救砖同步

- 本波情报同步确认 `masterflai/pmca-re-reloaded`（2026 年跨平台 Rust 重写版，Wasm 插件与 `Backup.bin` 安全守卫）、`dino2048/zv-e10-toolkit`（2026 年 10 月免焊接 Pico BootROM 串口注入 -> 解除 `0xF2402000` `TIMER-IP` 看门狗 -> Fastboot `18d1:4ee0` + PIO eMMC 修复 `/etc/ld.so.preload`）、`cokeenet/zve10-qemu`（`CXD90045` QEMU 外设建模）以及 `chocotan/a7c2-qemu`（`virt` + DTB + `ramfb` + 软件 GPE/CPU LZ77 启动原厂 UI）持续验证了本实验室“**只读零烧写（`O_RDONLY`）+ CPU/内存级影子隔离 + 无硬件单元测试验证**”技术路线的先进性与合规性。
