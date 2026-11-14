# Stage-A Non-Persistent Hardware Execution Runbook (EN / 简体中文)

- **Schemas & Generators**:
  - Pre-Flight Readiness Packet: `stage_a_readiness_packet_v1` · [`outputs/fx6-on-fx3-closure/fx6_closure/hardware_readiness_packet.py`](../outputs/fx6-on-fx3-closure/fx6_closure/hardware_readiness_packet.py)
  - Post-Trial Zero-Mutation Receipt & H0→H1→H2 Sandbox Drill: `stage_a_post_trial_receipt_v1` / `stage_a_h0_h1_h2_lifecycle_drill_v1` · [`outputs/fx6-on-fx3-closure/fx6_closure/stage_a_post_trial_auditor.py`](../outputs/fx6-on-fx3-closure/fx6_closure/stage_a_post_trial_auditor.py)
- **CLI Entrypoints**: `make readiness-packet` · `make lifecycle-drill` · `python3 -B -m fx6_closure verify-post-trial`
- **Hard-Locked Safety Posture**: `offline_engineering_complete = True` · `persistent_emmc_writes_authorized = False` · `persistent_write_release = False`

> [!CAUTION]
> **STRICT NON-PERSISTENT RAM-OVERLAY BOUNDARY (`0` BYTES WRITTEN TO eMMC / SPI NOR)**
> Stage-A never modifies `/dev/nflasha*`, `/dev/cnflasha*`, `/dev/pnflasha*`, `/dev/mtd*`, `p1:/updater`, `p2:/setting`, `p5:/wbi`, `p6:/tmp/jiritsu`, `p8:/cp`, `p12:/cert`, `p15:/usr`, or `p18:/lens`. Every binary adaptation (`P1..P9 + Fan`), loopback image (`opelog.vfat`), shadow `BK4\0` store, and one-shot arming token (`/tmp/mod_arm_once`) resides exclusively in volatile Linux DDR (`tmpfs`). Removing power immediately restores 100% stock Sony ILME-FX3 firmware.

---

# Part I — English Operator Runbook

## 1. Pre-Flight Workstation Verification (`make readiness-packet` & `make lifecycle-drill`)

Before connecting any physical Sony ILME-FX3 (`0x91030080`) body or inserting media, run the complete offline verification, H0→H1→H2 lifecycle sandbox drill, and readiness-packet generator on the host workstation:

```bash
# 1. Verify 57+57 bilingual BYOF manifest, all 5 automated test suites, H0->H1->H2 lifecycle drill, and candidate dry-run
make verify-byof
make test
make lifecycle-drill > /tmp/stage-a-lifecycle-drill.json
make dry-run

# 2. Emit deterministic Stage-A Pre-Flight Readiness Packet (before hardware capture)
make readiness-packet > /tmp/stage-a-preflight-packet.json
```

Expected pre-capture fields in `/tmp/stage-a-preflight-packet.json`:
- `"schema": "stage_a_readiness_packet_v1"`
- `"offline_engineering_complete": true`
- `"persistent_emmc_writes_authorized": false`
- `"real_tier0_hardware_backup_verified": false` (flips `true` **only** after Phase H0 passes)
- `"stage_a_ram_trial_hardware_go": false` (flips `true` **only** after Phase H0 passes)

Run the **Phase 28 End-to-End Phase H0 Read-Only Rehearsal Engine** immediately before plugging in any physical body (`--unicorn` adds emulated `v7.02` `p1` 4-site execution):

```bash
PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_safety.h0_hardware_rehearsal --unicorn
```

Confirm `"all_passed": true`, `"ready_for_physical_h0_capture": true`, and `"persistent_write_release": false` before connecting hardware.

---

## 2. Absolute Hardware Redlines (Zero-Tolerance Prohibitions)

| Redline ID | Protected Subsystem | Strictly Prohibited Commands / Actions | Technical Consequence if Violated |
| :---: | :--- | :--- | :--- |
| **`R1`** (`U1`) | Sector-0 (`8246` `2.00`) & Octal-SPI NOR | `edisx.elf`, `flashcp`, `nandwrite`, `dd of=/dev/nflasha*`, `dd of=/dev/mtd*` | Overwrites partition table or shifts `p18:/lens/lensfile.bin` (`0x31C000` vs FX6 `0x312000`), orphaning per-body calibration. |
| **`R2`** (`WBI`) | `p5:/wbi` (`WBI2` Warm-Boot Hibernation) | Any write to `/dev/nflasha5`, enabling `BIS` hibernation, or mutating WBI state | FX6 `wbimem` has a **`+13.47 MiB` DDR collision** against stock FX3 `0x00BA0000@0x410524000`; mismatched resume corrupts kernel VA space. |
| **`R3`** (`U2`/`U3`) | `p8:/cp` (`cpapp-b.bin` `@ 0x00108000`) & `p2:/setting/Backup.bin` (`0xfa0080`) | Flashing FX6 `cpapp-b.bin`, editing `tomco.txt`, or writing FX6 Bank 1 `0xfa0080` descriptors | FX6 `cpapp-b.bin` embeds **8 FX6-exclusive hardware drivers** (`Darwin` variable ND + `Mew` SDI/Genlock FPGA) & GPIO `0:22` reset lines absent on FX3. |
| **`R4`** (`U5`) | Sticky Boot Arbitrator (`loader_nor.bin` `0xFE049000` + Sub-LSI ANK) | Creating `/setting/updater/mode*`, mutating `BK4\0` `boot_img` byte `+8` (`!= 0x00`), or running `ud_send_lsi.elf 1..6` | Latches camera into `p1` updater loop across cold reboots unless cleared via the mandatory 2-step Bank 0 reset. |
| **`R5`** (`ABI`) | Stock FX3 `.ko` Kernel Modules (`4.9.337-scel+`) | Copying FX6 `.ko` modules onto `/usr/kmod` or loading `emg.ko` | Breaks module symbol CRCs or probes absent FX6 hardware (`kmod_mutation_count` and `fx6_kmod_loaded_count` must stay `0`). |

---

## 3. Gate-Ordered Execution Checklist (Phase H0 → Phase H1 → Phase H2)

### Phase H0 — Same-Body Tier-0 Read-Only Capture & Two-Pass Host Verification (`Gate G10`)

1. **Hardware Preconditions**:
   - Physical Sony **ILME-FX3** (`Model ID 0x91030080`) with fresh **NP-FZ100 battery >= 80%**.
   - Dedicated formatted CFexpress Type A or UHS-II SDXC card (`>= 64 GB` free) mounted at `/mnt/fx3_tier0_backup`.
2. **Execute Read-Only Freestanding Worker (`tier0_backup_worker`)**:
   - Worker's very first path syscall unlinks `/tmp/jiritsu/libJit.so` before opening every source strictly `O_RDONLY | O_NOFOLLOW` and writing each output image strictly `O_WRONLY | O_CREAT | O_EXCL` on external media.
   - Captures **two independent SHA-256 readback passes** for all **11 mandatory Tier-0 items** (`sector0.bin`, `boot0.bin`, `boot1.bin`, `p1_updater.bin`, `p2_backup_bin.bin`, `p2_psd_bin.bin`, `p2_defdet_bin.bin`, `p6_jiritsu.bin`, `p12_cert.bin`, `p18_lensfile.bin`, `spi_nor_ddrtraining.bin`) plus read-only redline header probes **`p8_tomco.txt`** and **`p5_wbi_header.bin`**, recording real `body_serial` and 128-bit eMMC `cid` in `backup-manifest.json`.
3. **Host Workstation Validation**:
   - Copy the capture directory to two immutable read-only host locations and run:
     ```bash
     PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
       /usr/bin/python3 -B -m fx6_closure build-readiness-packet \
       --tier0-bundle-dir /path/to/fx3_tier0_capture_h0 \
       --output /tmp/stage-a-go-packet.json
     ```
   - **Mandatory GO Gate**: Proceed to Phase H1 **if and only if** the command exits `0` with:
     - `"real_tier0_hardware_backup_verified": true`
     - `"stage_a_ram_trial_hardware_go": true`
     - `"persistent_emmc_writes_authorized": false` (remains locked `false` throughout Stage-A!)
   - Note: `verify_real_tier0_capture_bundle()` automatically rejects synthetic manifests, placeholder `body_serial`/`cid`, missing files, Pass-1 != Pass-2 SHA-256 mismatches, bit flips, non-FX3 Sector-0 tables, invalid `BK4\0` checksums, corrupted `p1` `FAT16` headers, malformed `p8` `tomco.txt`, or invalidated `p5` `WBI2` headers.

### Phase H1 — Non-Persistent Stage-A RAM-Overlay Boot Trial (`Gate G09` / `G11`)

1. **Stage Verified Payload in Volatile `tmpfs` (`/tmp/fx6_stage_a`)**:
   - Unpack the verified `30,956 B` SVR4 `cpio newc` archive (`SHA-256: eaa7902770968b44521d991f37285574c65ad2a92cef59d7434e9861467efbd9`) and stage the 11 adapted runtime blobs (`P1..P9 + Fan`, `opelog.vfat`, RAM-shadow `Backup.bin`) strictly inside `/tmp/fx6_stage_a` (`57.46–130.76 MiB` peak, well inside the `256.00 MiB` `tmpfs` ceiling).
2. **Arm One-Shot Volatile Token & Launch Atomic Orchestrator**:
   - Create `/tmp/mod_arm_once` in `tmpfs` (never on `p1`, `p2:/setting`, or `p5:/wbi`).
   - Run `/etc/fx6_overlay/30-stage-a-orchestrator.sh` (archiving its volatile telemetry log to external media if desired for Phase H2 auditing):
     1. Immediately unlinks `/tmp/mod_arm_once` (**Clear-Before-Exec** — guarantees next reboot is stock FX3 even on sudden kernel panic or battery pull).
     2. Asserts WBI hibernation guard (`p5:/wbi` unmounted/read-only, `BIS` hibernation disabled).
     3. Verifies all **11 SHA-256 digests** strictly **before** the first `insmod` or `mount --bind`.
     4. Activates the 10-step RAM overlay (`P9` `upm.ko` RAM replacement at slot `#24`, `/dev/loop7 -> /etc/opelog` `8 MiB` `FAT16` loopback, RAM-shadow `BK4\0` bind, `P1/P3/P4/P8/Fan` `.so` read-only bind mounts, and bounded watchdog supervision of `im.elf`).
     5. On exit or any step failure, unwinds mounted steps in strict reverse **`10..1` LIFO** order.

### Phase H2 — Emergency Recovery & Automated Post-Trial Zero-Mutation Receipt (`stage_a_post_trial_receipt_v1`)

1. **Emergency Instant Recovery (At Any Moment)**:
   - Turn power switch **OFF** and remove the **NP-FZ100** battery for **10 seconds**, then re-insert and power **ON**.
   - Because `0` bytes were written to eMMC, SPI NOR, `p2:/setting`, `p5:/wbi`, or `p8:/cp`, and `/tmp/mod_arm_once` existed only in volatile DDR, the camera cold-boots directly into **100% unmodified stock FX3 Bank 0**.
   - **If `p1` Updater Shell Was Entered Manually**: Always execute the mandatory **2-step atomic `U5` Bank 0 exit** before rebooting:
     ```sh
     rm -f /setting/updater/mode* && sync
     /usr/bin/ud_send_lsi.elf 0
     ```
2. **Automated Post-Trial Zero-Mutation Receipt (`verify-post-trial`)**:
   - Confirm stock FX3 Ver. 7.02 Shooting HUD, menu version screen, E-mount lens communication, IBIS/Gyro, fan control, and dual-slot recording operate identically to pre-trial baseline.
   - Capture a fresh read-only Phase H2 Tier-0 bundle (`/path/to/fx3_tier0_capture_h2`, strictly distinct from Phase H0) and emit the deterministic `stage_a_post_trial_receipt_v1` cryptographic receipt on the host workstation:
     ```bash
     PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
       /usr/bin/python3 -B -m fx6_closure verify-post-trial \
       --h0-bundle-dir /path/to/fx3_tier0_capture_h0 \
       --h2-bundle-dir /path/to/fx3_tier0_capture_h2 \
       --h1-log /path/to/h1_orchestrator_telemetry.json \
       --output /tmp/stage-a-post-trial-receipt.json
     ```
   - **Mandatory Post-Trial Acceptance Criteria**: Command must exit `0` with `"all_checks_passed": true`, `"zero_mutation_verified": true`, `"same_body_identity_verified": true`, `"persistent_bytes_mutated": 0`, `"drifted_items": []` across all **13** persistent surfaces (`11` Tier-0 partitions/calibrations + `p8_tomco.txt` + `p5_wbi_header.bin`), `"u5_sticky_boot_clean": true` (`h2_bk4_byte8 == 0` and `0` `/setting/updater/mode*` residue), and `"persistent_emmc_writes_authorized": false`.

---

## 4. FX3 15-Pin Multi-Port `RP2040-Zero` (`-DOPEN_DRAIN`) Tier-3 Safety Net

Disassembly-free Tier-3 unbrick & pre-H0 BootROM inspection uses the **Sony 15-Pin Multi-Terminal** at `48,000` baud (`uart_boot` frame magic `"UB"`, CRC-32) before transitioning to `115,200` baud `[mira] fastboot ready` (`18D1:4EE0`). Validate every harness and command sequence offline with `fx3_safety.multiport_bootrom_unbrick` before connecting hardware.

| Multi-Terminal Back Row Pin | Camera Signal | Direction | Approved `RP2040-Zero` Pin | Electrical Requirement |
| :---: | :--- | :---: | :--- | :--- |
| **Pin 2** | `GND` | Reference | **`GND`** | Mandatory common ground before any signal line |
| **Pin 7** | `CAM_UART_RX` | Host $\to$ Cam | **`GP28` (`MULTI_TX`)** | `1.8V` open-drain High-Z (`-DOPEN_DRAIN`), never `3.3V` push-pull |
| **Pin 8** | `CAM_UART_TX` | Cam $\to$ Host | **`GP29` (`MULTI_RX`)** | Direct high-Z input (standard Pico `GP29` `VSYS/3` divider FORBIDDEN) |
| **Pin 9** | `XRESET` | Host $\to$ Cam | **`GP27` (`MULTI_RST`)** | `1.8V` open-drain High-Z reset pulse |

- **Strict Board Ban (`BLOCKED_ELECTRICAL_HAZARD`)**: **NEVER** connect a standard Raspberry Pi Pico (`pico`, `pico_w`, `pico_2`), whose `GP29` connects to the `VSYS/3` resistor divider, dragging down Multi Pin 8 `CAM_UART_TX`, causing `0x100D` (`13` short blinks) framing errors, or stressing `1.8V` SoC I/O. Only **Waveshare `RP2040-Zero`** compiled with `-DOPEN_DRAIN` (`1.8V` open-drain High-Z) or an explicit `1.8V` open-drain buffer is permitted.
- **BootROM WDT Trap & Read-Only Firewall**:
  - `BOOTROM` range is strictly `0xFFFF0000..0xFFFFBFFF` (`48 KiB`); any access `>= 0xFFFFC000` triggers the `CXD90057` hardware watchdog reset trap (`BLOCKED_WDT_TRAP_HAZARD`).
  - Route A loads signed `fastboot.bin` into SRAM `0x92028000..0x92427FFF`; Route B loads open bare-metal eSRAM payloads into `0xFE020000..0xFE047FFF` (stopping strictly before `loader_nor` / DDR training `0xFE080000`).
  - Fastboot (`18D1:4EE0`) is firewalled strictly to read-only diagnostics (`getvar:*`, `oem dumpbrom`, `oem partition dump`, `oem cetus dumpnor`, `oem cetus peek`, `reboot`); `flash:`, `erase:`, `oem format`, `oem cetus poke/exec`, `download:`, and `boot` are blocked (`ALLOW_DESTRUCTIVE_FASTBOOT = False`).

---

## 5. macOS 26+ `IOUSBHost` `0xe00002be` Connection Procedure

macOS 26+ triggers `0xe00002be` (`kIOReturnExclusiveAccess`) contention between kernel mass-storage drivers and libusb when switching Sony ILME-FX3 from MSC (`054C:0DA1`) to Service Mode (`054C:0336`). Follow the deterministic transport guard in `fx3_recovery.macos_usb_transport_guard`:

1. **MSC Quiescence Wait**: After USB MSC (`054C:0DA1`) enumerates, pause `>= 350 ms` for macOS 26+ mass-storage indexing/mounting to settle before claiming the interface.
2. **Bounded Exponential Backoff & `IOUSBHost` Claim Fallback**: If `0xe00002be` (`kIOReturnExclusiveAccess`) occurs, retry using bounded exponential backoff (`50 -> 100 -> 200 -> 400 -> 800 ms`, max 4 retries) with `IOUSBHost` exclusive-claim fallback rather than tight-loop polling.
3. **Vendor Control Handshake & STALL Non-Retransmit Rule**: Issue Vendor Control `(bmRequestType=0x43, bRequest=1, wValue=0x37FF, wIndex=0xD7AA)`. **If a USB `STALL` (`0xe000404f`) occurs, ABORT immediately without re-sending or retransmitting** (`STALL_ABORTED_NO_RETRANSMIT`).
4. **Senser v1 vs. Senser v2 Fail-Closed Rule**:
   - **Senser v1 (`ILME-FX3` `0x91030080`)**: Performs 7-round challenge authentication (`054C:0DA1 -> 054C:0336`).
   - **Senser v2 (`ILCE-7M5` / RSA-signed challenge)**: Must **fail closed** (`FAILED_CLOSED_SENSER_V2`)—never brute-force or forge RSA responses.
5. **Read-Only Jiritsu Channel Firewall (`PFUNC=0x40, block=0x1001`)**: Only `0x4002 MOUNT`, `0x4008 GET_FILE`, `0x4011 GET_FILE2`, and read-only `0x400F SET_FILE_PATH` (paths strictly under `/tmp/jiritsu/`, `/mnt/fx3_tier0_backup/`, or `/log/` with no `..` traversal) are allowed. `0x4003 FORMAT`, `0x4006 FIRMUP`, `0x4005 DEBUG`, `0x4007 SET_FILE`, and `0x4010 SET_FILE2` remain hard-blocked (`ALLOW_PERSISTENT_JIRITSU_WRITES = False`).

---

## 6. Sony Notice `00342260` `WF-12` Cold-Boot Airplane Shadow

Per Sony Service Notice **`00342260`**, **6 Long + 9 Short LED blinks (`6L+9S`)** or a **5–10s System Error reboot loop** indicates a `WF-12` Wi-Fi/Bluetooth IC/BGA communication fault or `CXD90058` Cetus CP NOR (`cpapp-b.bin`) subcomponent mismatch:

1. **60-Second Cold PMIC Discharge**: Remove the NP-FZ100 battery and discharge PMIC rails for **60 seconds**.
2. **Airplane Mode Isolation (`v3.00–v5.00`)**: If the UI briefly boots, immediately enable **Airplane Mode** to suppress wireless initialization.
3. **`v7.02` `BODYDATA.DAT` Degraded Mode**: Official FX3 `v7.02` converts `WF-12` failures into a dismissible `"Wi-Fi/Bluetooth unit has malfunctioned"` degraded warning instead of a fatal WDT reboot loop. Stage-A/B software stacks must likewise keep `libInfraAppRemoteBoard.so` / `InfraPericon` / `SeqQueueNetwork` wireless initialization non-blocking.
4. **Disassembly-Free Tier-3 Triage**: If locked in a `6L+9S` updater loop, enter Fastboot (`18D1:4EE0`) via `RP2040-Zero` (`-DOPEN_DRAIN`) and execute **read-only** `oem cetus dumpnor` and `oem partition` to separate CP NOR corruption from physical `WF-12` BGA solder failure on `SY-1114`. Never flash a foreign CP NOR / SPI NOR dump without keeping this board's own `ddrtraining.dat` (`0x03e210fc`) and `MIS.bin`.

---

## 7. 2026 Forbidden Operations (`ld.so.preload`, `dd` Truncation, `nflasha10` Full, `PRODUCT_MODEL` NVRAM)

Validated statically and dynamically by `fx3_safety.runtime_antibrick_guards`:

1. **`/etc/ld.so.preload` Dynamic BusyBox Deadlock (`V_LD_SO_PRELOAD`)**: `/bin/busybox` and `/bin/sh` on `CXD90057` are dynamically linked; writing `/etc/ld.so.preload` (directly or via Jiritsu `0x400F` `..` traversal) with a missing or incompatible `.so` deadlocks `/sbin/init` before shell or Jiritsu recovery can start. **Use RAM-only `LD_LIBRARY_PATH` / `tmpfs` `mount --bind` strictly behind `/tmp/mod_arm_once` Clear-Before-Exec.**
2. **Sony BusyBox `dd` Truncation (`V_BUSYBOX_DD_TRUNC`)**: Never run `dd of=<existing_file>` on Sony BusyBox without verified `conv=notrunc` support (unpatched BusyBox `dd` opens `of=` with `O_TRUNC` and destroys the destination file before reading). Stage only under the `pmca-re-reloaded` 5-step atomic contract (Drop exit guard, `tmpfs` staging, full SHA-256 readback, 5-slot rollback manifest).
3. **`nflasha10` (`12 MiB` VFAT) `0x10000009` Exhaustion (`V_NFLASHA10_FULL`)**: `/setting` (`nflasha10`) is only `12 MiB` and shared across `/tmp`, `/etc`, and `/var`. Always enforce **`>= 2 MiB` free-space headroom** (`1 MiB` hard floor); exhausting clusters triggers `0x10000009` write lockout, blocking `/setting/updater/mode*` and service recovery flags.
4. **`CAMSET` / `BK4\0` `PRODUCT_MODEL` NVRAM Lock (`V_CAMSET_PRODUCT_MODEL`)**: Never mutate `PRODUCT_MODEL` (`ALCIN_UUD` enum `4`, `0x91030080`), BK4 identity slots (`0x00000000`, `0x00010000`, `0x02CF0001`), `psd.bin`, `defdet.bin`, `lensfile.bin`, `ddrtraining`, or `cert` records. Only non-identity user settings (`0x02CF0004`, `0x02CF1443`, `0x02CF1453`, `0x02CF1702`, `0x02CF1704`, `0x02CF1BF2`) may ever be shadowed in RAM.

---

# 第二部分 — 简体中文真机执行操作手册 (Stage-A)

## 1. 宿主机离线预检、生命周期演练与就绪包生成（`make readiness-packet` & `make lifecycle-drill`）

在连接任何索尼 **ILME-FX3（机型 ID `0x91030080`）** 真机或插入存储卡之前，必须先在宿主机完成全量离线验证、H0→H1→H2 全生命周期沙盒演练并生成确定性预检就绪包：

```bash
# 1. 运行双语 57+57 项 BYOF 清单审计、全仓 5 大测试套件、H0->H1->H2 生命周期沙盒演练与候选包干跑
make verify-byof
make test
make lifecycle-drill > /tmp/stage-a-lifecycle-drill.json
make dry-run

# 2. 生成 Stage-A 真机前确定性就绪包（尚未连接真机采集前）
make readiness-packet > /tmp/stage-a-preflight-packet.json
```

采集前 `/tmp/stage-a-preflight-packet.json` 关键字段预期值：
- `"schema": "stage_a_readiness_packet_v1"`
- `"offline_engineering_complete": true`（离线工程验证 100% 闭环）
- `"persistent_emmc_writes_authorized": false`（持久闪存写入硬锁定为 `false`）
- `"real_tier0_hardware_backup_verified": false`（仅在通过 **Phase H0** 真机备份校验后变为 `true`）
- `"stage_a_ram_trial_hardware_go": false`（仅在通过 **Phase H0** 真机备份校验后变为 `true`）

在接入任何物理真机前，先运行 **Phase 28 端到端 Phase H0 只读硬件预演引擎**（`--unicorn` 启用 `v7.02` `p1` 4 位点仿真校验）：

```bash
PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter \
  /usr/bin/python3 -B -m fx3_safety.h0_hardware_rehearsal --unicorn
```

必须确认输出 `"all_passed": true`、`"ready_for_physical_h0_capture": true` 且 `"persistent_write_release": false`，方允许连接相机。

---

## 2. 真机绝对安全红线（零容忍禁令表）

| 红线编号 | 受保护子系统 | 严禁执行的命令与操作 | 违背红线的物理后果 |
| :---: | :--- | :--- | :--- |
| **`R1`** (`U1`) | Sector-0 分区表 (`8246` `2.00`) 与 Octal-SPI NOR | 严禁运行 `edisx.elf`、`flashcp`、`nandwrite` 或向 `/dev/nflasha*`、`/dev/mtd*` 写入任何字节 | 篡改分区表或使 `p18:/lens/lensfile.bin`（`0x31C000` vs FX6 `0x312000`）发生 `-20 MiB` 偏移，丢失单机卡口校准。 |
| **`R2`** (`WBI`) | `p5:/wbi`（`WBI2` 休眠快照分区） | 严禁写入 `/dev/nflasha5`、严禁激活 `BIS` 休眠快照生成或修改 WBI 分区 | FX6 `wbimem` 与 FX3 原厂 `0x00BA0000@0x410524000` 存在 **`+13.47 MiB` DDR 碰撞**；错配休眠恢复将直接破坏内核地址空间。 |
| **`R3`** (`U2`/`U3`) | `p8:/cp`（`cpapp-b.bin` `@ 0x00108000`）与 `p2:/setting/Backup.bin` (`0xfa0080`) | 严禁刷写 FX6 `cpapp-b.bin`、修改 `tomco.txt` 或写入 FX6 Bank 1 `0xfa0080` 表 | FX6 `cpapp-b.bin` 内含 **8 项 FX6 独占硬件驱动**（`Darwin` 电子可变 ND 与 `Mew` SDI/Genlock FPGA）及 GPIO `0:22` 复位线，FX3 主板不存在对应外设。 |
| **`R4`** (`U5`) | 持久启动仲裁器（`loader_nor.bin` `0xFE049000` + Sub-LSI ANK） | 严禁创建 `/setting/updater/mode*`、修改 `BK4\0` `boot_img` 第 `+8` 字节（须保持 `0x00`），或执行非零模式 `ud_send_lsi.elf 1..6` | 会导致相机跨断电粘连锁定在 `p1` 升级分区，必须执行双步原子复位方可退出。 |
| **`R5`** (`ABI`) | FX3 原厂 `.ko` 内核模块（`4.9.337-scel+`） | 严禁向 `/usr/kmod` 覆盖写入 FX6 `.ko` 或强行加载 `emg.ko` | 破坏模块符号 CRC 或探测不存在的 FX6 专有外设（必须保持 `kmod_mutation_count = 0`、`fx6_kmod_loaded_count = 0`）。 |

---

## 3. 门禁有序执行规程（Phase H0 → Phase H1 → Phase H2）

### Phase H0 — 同机 Tier-0 只读全量备份与宿主机双遍校验（`Gate G10`）

1. **硬件前置条件**：
   - 索尼 **ILME-FX3** 真机（`Model ID 0x91030080`），安装电量 **>= 80%** 的原装 **NP-FZ100** 电池。
   - 专用已格式化 CFexpress Type A 或 UHS-II SDXC 存储卡（可用空间 `>= 64 GB`），挂载于 `/mnt/fx3_tier0_backup`。
2. **运行零依赖只读备份工作器（`tier0_backup_worker`）**：
   - 首条路径系统调用即执行 `unlinkat("/tmp/jiritsu/libJit.so")`；所有源设备严格以 `O_RDONLY | O_NOFOLLOW` 打开，输出镜像严格以 `O_WRONLY | O_CREAT | O_EXCL` 写入外置存储卡。
   - 对全部 **11 项强制 Tier-0 分区与校准文件**（`sector0.bin`、`boot0.bin`、`boot1.bin`、`p1_updater.bin`、`p2_backup_bin.bin`、`p2_psd_bin.bin`、`p2_defdet_bin.bin`、`p6_jiritsu.bin`、`p12_cert.bin`、`p18_lensfile.bin`、`spi_nor_ddrtraining.bin`）及 **2 项只读红线头探针**（`p8_tomco.txt`、`p5_wbi_header.bin`）独立执行**两遍 SHA-256 读取校验**，并将真实机身序列号 `body_serial` 与 128 位 eMMC `cid` 写入 `backup-manifest.json`。
3. **宿主机硬门禁核验**：
   - 将备份目录完整拷贝至宿主机两处只读离线归档位置，并运行：
     ```bash
     PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
       /usr/bin/python3 -B -m fx6_closure build-readiness-packet \
       --tier0-bundle-dir /path/to/fx3_tier0_capture_h0 \
       --output /tmp/stage-a-go-packet.json
     ```
   - **唯一放行条件**：仅当返回码为 `0`，且输出满足 `"real_tier0_hardware_backup_verified": true`、`"stage_a_ram_trial_hardware_go": true`（同时 `"persistent_emmc_writes_authorized"` 依然硬锁定为 `false`）时，方可进入 Phase H1。任何合成清单、占位序列号/`cid`、缺文件、双遍哈希不等、比特翻转或魔数头（`'8246'` / `'BK4\0'` / `'FAT16'` / `tomco.txt` / `'WBI2'`）异常均会被确定性拒绝。

### Phase H1 — Stage-A 纯内存（`tmpfs`）零写闪存非持久试运行（`Gate G09` / `G11`）

1. **在易失性 `tmpfs`（`/tmp/fx6_stage_a`）中暂存载荷**：
   - 将已校验的 `30,956 B` SVR4 `cpio newc` 归档（`SHA-256: eaa7902770968b44521d991f37285574c65ad2a92cef59d7434e9861467efbd9`）与 11 项适配运行时组件解压至 `/tmp/fx6_stage_a`（峰值占用 `57.46–130.76 MiB`，远低于 `256.00 MiB` 安全上限）。
2. **创建单次内存令牌并启动原子编排器**：
   - 仅在内存 `tmpfs` 创建单次授权令牌 `/tmp/mod_arm_once`（严禁写入任何持久分区）。
   - 执行 `/etc/fx6_overlay/30-stage-a-orchestrator.sh`（可选将内存编排遥测日志归档至外置卡供 Phase H2 自动审计）：
     1. **执行前即删（Clear-Before-Exec）**：启动首步立即删除 `/tmp/mod_arm_once`，确保即便发生内核崩溃或直接拔电池，下次上电必回原厂 FX3。
     2. **休眠阻断**：强制锁定 `p5:/wbi` 只读/未挂载并阻断 `BIS` 休眠触发。
     3. **挂载前全量校验（Verify-Before-Mount）**：在执行第一次 `insmod` 或 `mount --bind` 前，完整核对全部 **11 项 SHA-256**。
     4. **10 步正向激活与逆序 `10..1` LIFO 卸载**：按序完成槽位 `#24` `P9` `upm.ko` 内存替换、`/dev/loop7 -> /etc/opelog` `8 MiB` `FAT16` 回环挂载、RAM-Shadow `BK4\0` 绑定、`P1/P3/P4/P8/Fan` 只读绑定挂载及带看门狗的 `im.elf` 监管；退出或任一步失败时严格按 **`10..1` 逆序 LIFO** 完整卸载。

### Phase H2 — 紧急断电恢复与断电后自动化零篡改收据核验（`stage_a_post_trial_receipt_v1`）

1. **任意时刻一键紧急恢复**：
   - 将机身电源拨至 **OFF**，取出 **NP-FZ100** 电池静置 **10 秒** 后重新装回开机。
   - 由于全流程对 eMMC、SPI NOR、`p2:/setting`、`p5:/wbi`、`p8:/cp` 均为 **0 字节写入**，且内存 `tmpfs` 随断电瞬间清空，相机将 100% 冷启动回**未受任何改动的原厂 FX3 Bank 0 系统**。
   - **若曾手动进入 `p1` 维护环境**：重启前必须按序执行 **`U5` 双步原子复位**：
     ```sh
     rm -f /setting/updater/mode* && sync
     /usr/bin/ud_send_lsi.elf 0
     ```
2. **试运行后自动化零篡改收据审计（`verify-post-trial`）**：
   - 开机核对原厂 FX3 Ver. 7.02 拍摄主界面、系统版本菜单、E 卡口镜头通信、防抖陀螺仪、风扇温控与双卡槽录制均 100% 正常。
   - 以只读模式重新采集独立的 Phase H2 Tier-0 读回包（`/path/to/fx3_tier0_capture_h2`，严禁复用 Phase H0 目录），并在宿主机运行确定性收据生成器：
     ```bash
     PYTHONPATH=outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx6-on-fx3-closure \
       /usr/bin/python3 -B -m fx6_closure verify-post-trial \
       --h0-bundle-dir /path/to/fx3_tier0_capture_h0 \
       --h2-bundle-dir /path/to/fx3_tier0_capture_h2 \
       --h1-log /path/to/h1_orchestrator_telemetry.json \
       --output /tmp/stage-a-post-trial-receipt.json
     ```
   - **强制验收放行判据**：返回码必须为 `0`，且收据输出 `"all_checks_passed": true`、`"zero_mutation_verified": true`、`"same_body_identity_verified": true`（同机 `body_serial` 与 128 位 `cid` 100% 匹配）、全部 **13 项**持久表面（11 项 Tier-0 分区/校准镜像 + `p8_tomco.txt` + `p5_wbi_header.bin`）满足 `"persistent_bytes_mutated": 0` 与 `"drifted_items": []`、`"u5_sticky_boot_clean": true`（`h2_bk4_byte8 == 0` 且零 `/setting/updater/mode*` 残留），同时 `"persistent_emmc_writes_authorized"` 保持硬锁定为 `false`。

---

## 4. FX3 15-Pin Multi-Port `RP2040-Zero`（`-DOPEN_DRAIN`）Tier-3 安全防护网

免拆机 Tier-3 救砖与上机前 BootROM 只读核查通过 **索尼 15 针 Multi 接口** 以 `48,000` 波特率（`uart_boot` 帧魔数 `"UB"` + CRC-32）完成握手，随后切换至 `115,200` 波特率 `[mira] fastboot ready`（`18D1:4EE0`）。接线前必须通过 `fx3_safety.multiport_bootrom_unbrick` 离线验签线束与命令序列。

| Multi 接口后排引脚 | 相机信号 | 方向 | 唯一允许的 `RP2040-Zero` 引脚 | 电气强制规范 |
| :---: | :--- | :---: | :--- | :--- |
| **Pin 2** | `GND` | 参考地 | **`GND`** | 接入任意信号线前必须先共地 |
| **Pin 7** | `CAM_UART_RX` | 主机 $\to$ 相机 | **`GP28` (`MULTI_TX`)** | `1.8V` 开漏高阻（`-DOPEN_DRAIN`），严禁 `3.3V` 推挽输出 |
| **Pin 8** | `CAM_UART_TX` | 相机 $\to$ 主机 | **`GP29` (`MULTI_RX`)** | 直接高阻输入（**严禁使用标准 Pico 的 `GP29` `VSYS/3` 分压线**） |
| **Pin 9** | `XRESET` | 主机 $\to$ 相机 | **`GP27` (`MULTI_RST`)** | `1.8V` 开漏高阻复位脉冲 |

- **严禁开发板清单（`BLOCKED_ELECTRICAL_HAZARD`）**：**绝对禁止**使用标准版 Raspberry Pi Pico（`pico`、`pico_w`、`pico_2`），因其 `GP29` 硬件焊接了 `VSYS/3` 电阻分压，会直接拉低 Multi Pin 8 `CAM_UART_TX` 触发 `0x100D`（`13` 短闪）帧错误或损伤 `1.8V` SoC IO。仅允许编译启用 `-DOPEN_DRAIN` 的 **Waveshare `RP2040-Zero`** 或独立 `1.8V` 开漏缓冲器。
- **BootROM 看门狗陷阱与只读防火墙**：
  - `BOOTROM` 地址严格限定在 `0xFFFF0000..0xFFFFBFFF`（`48 KiB`）；任何访问落入 `>= 0xFFFFC000` 均会触发 `CXD90057` 硬件看门狗复位陷阱（`BLOCKED_WDT_TRAP_HAZARD`）。
  - Route A 将官方签名 `fastboot.bin` 载入 SRAM `0x92028000..0x92427FFF`；Route B 将裸机 eSRAM 载荷载入 `0xFE020000..0xFE047FFF`（严格停在 `loader_nor` / DDR 训练入口 `0xFE080000` 之前）。
  - Fastboot（`18D1:4EE0`）只放行只读诊断命令（`getvar:*`、`oem dumpbrom`、`oem partition dump`、`oem cetus dumpnor`、`oem cetus peek`、`reboot`）；`flash:`、`erase:`、`oem format`、`oem cetus poke/exec`、`download:` 与 `boot` 一律拦截（`ALLOW_DESTRUCTIVE_FASTBOOT = False`）。

---

## 5. macOS 26+ `IOUSBHost` `0xe00002be` 真机接入规程

macOS 26+ 在将 ILME-FX3 从 MSC（`054C:0DA1`）切换至维修模式（`054C:0336`）时，内核大容量存储驱动与 libusb 会竞争产生 `0xe00002be`（`kIOReturnExclusiveAccess`）。必须按 `fx3_recovery.macos_usb_transport_guard` 确定性状态机执行：

1. **MSC 静默等待**：`054C:0DA1` 枚举后等待 `>= 350 ms`，待 macOS 26+ 大容量存储挂载探测稳定后再接管接口。
2. **有界指数退避与 `IOUSBHost` 回退接管**：遇到 `0xe00002be` 时执行 `50 -> 100 -> 200 -> 400 -> 800 ms` 有界指数退避（最多 4 次重试）并切换 `IOUSBHost` 独占声明，严禁死循环高频轮询。
3. **Vendor Control 握手与 STALL 禁止重传红线**：发送 `(bmRequestType=0x43, bRequest=1, wValue=0x37FF, wIndex=0xD7AA)`。**一旦发生 USB `STALL`（`0xe000404f`），必须立即终止会话，严禁在 macOS 上重发/重传切换命令**（`STALL_ABORTED_NO_RETRANSMIT`）。
4. **Senser v1 与 Senser v2 失败关闭（Fail-Closed）规则**：
   - **Senser v1（`ILME-FX3` `0x91030080`）**：执行 7 轮认证挑战切换至 `054C:0336`。
   - **Senser v2（如 `ILCE-7M5` RSA 签名认证）**：必须直接 **fail-closed 拒止**（`FAILED_CLOSED_SENSER_V2`），严禁暴力枚举或伪造签名。
5. **只读 Jiritsu 通道防火墙（`PFUNC=0x40, block=0x1001`）**：仅放行 `0x4002 MOUNT`、`0x4008 GET_FILE`、`0x4011 GET_FILE2` 及限制在 `/tmp/jiritsu/`、`/mnt/fx3_tier0_backup/`、`/log/` 且无 `..` 路径穿越的只读 `0x400F SET_FILE_PATH`；`0x4003 FORMAT`、`0x4006 FIRMUP`、`0x4005 DEBUG`、`0x4007 SET_FILE`、`0x4010 SET_FILE2` 硬锁阻断（`ALLOW_PERSISTENT_JIRITSU_WRITES = False`）。

---

## 6. Sony 公告 `00342260` `WF-12` 冷启飞行模式隔离预案

依据索尼维修公告 **`00342260`**，**6 长 + 9 短红灯闪烁（`6L+9S`）** 或 **开机 5–10 秒 System Error 重启循环** 指示 `WF-12` Wi-Fi/蓝牙 BGA/芯片通信异常或 `CXD90058` Cetus CP NOR（`cpapp-b.bin`）子组件校验失败：

1. **60 秒冷断电放电**：拆下 NP-FZ100 电池并对 PMIC 电源轨静置放电 **60 秒**。
2. **飞行模式隔离（`v3.00–v5.00`）**：若机身短暂进入菜单界面，立即开启**飞行模式**屏蔽无线模块初始化。
3. **`v7.02` `BODYDATA.DAT` 降级容错**：索尼官方 FX3 `v7.02` 已将 `WF-12` 故障转为可关闭的 `"Wi-Fi/Bluetooth unit has malfunctioned"` 降级提示而非致命重启循环；Stage-A/B 运行时堆栈同样必须保持 `libInfraAppRemoteBoard.so` / `InfraPericon` / `SeqQueueNetwork` 无线初始化非阻塞超时降级。
4. **免拆机 Tier-3 鉴真**：若机身卡死在 `6L+9S` 升级死循环，通过 `RP2040-Zero`（`-DOPEN_DRAIN`）进入 Fastboot（`18D1:4EE0`）执行**只读** `oem cetus dumpnor` 与 `oem partition`，区分 CP NOR 损坏与 `SY-1114` 主板物理 `WF-12` 虚焊/损毁。严禁在不保留本机 `ddrtraining.dat`（`0x03e210fc`）与 `MIS.bin` 的前提下刷入他机 CP/SPI NOR。

---

## 7. 2026 高危禁令操作清单（`ld.so.preload`、`dd` 截断、`nflasha10` 写满、`PRODUCT_MODEL` NVRAM）

所有脚本、写入计划与 NVRAM 变更均须通过 `fx3_safety.runtime_antibrick_guards` 审计：

1. **禁止 `/etc/ld.so.preload` 动态 BusyBox 死锁（`V_LD_SO_PRELOAD`）**：`CXD90057` 机身 `/bin/busybox` 与 `/bin/sh` 均为动态链接；直接或经由 Jiritsu `0x400F` `..` 穿越向 `/etc/ld.so.preload` 写入失效/不兼容 `.so` 会导致 `/sbin/init` 启动前即永久死锁。**只允许使用 `/tmp/mod_arm_once` Clear-Before-Exec 保护下的纯内存 `LD_LIBRARY_PATH` / `tmpfs` `mount --bind`。**
2. **禁止索尼 BusyBox 原地 `dd` 截断（`V_BUSYBOX_DD_TRUNC`）**：未验证 `conv=notrunc` 支持时严禁对既有文件执行 `dd of=<existing_file>`（索尼 BusyBox `dd` 会以 `O_TRUNC` 打开目标文件并直接清空）。所有合法阶段性写入必须遵循 `pmca-re-reloaded` 五步原子契约（Drop exit 防护、`tmpfs` 暂存、全量 SHA-256 回读核验、5 槽位回滚清单）。
3. **严防 `nflasha10`（`12 MiB` VFAT）`0x10000009` 耗尽锁死（`V_NFLASHA10_FULL`）**：`/setting`（`nflasha10`）总容量仅 `12 MiB` 且与 `/tmp`、`/etc`、`/var` 共享。必须保留 **`>= 2 MiB` 剩余安全余量**（硬底线 `1 MiB`），耗尽簇将触发 `0x10000009` 写入锁死，连升级退出标志与清理恢复命令均无法写入。
4. **严禁篡改 `CAMSET` / `BK4\0` `PRODUCT_MODEL` NVRAM（`V_CAMSET_PRODUCT_MODEL`）**：严禁修改 `PRODUCT_MODEL`（`ALCIN_UUD` 枚举值 `4`、`0x91030080`）、BK4 身份键槽（`0x00000000`、`0x00010000`、`0x02CF0001`）以及 `psd.bin`、`defdet.bin`、`lensfile.bin`、`ddrtraining`、`cert`。仅允许在 RAM 影子区调整非身份用户设置项（`0x02CF0004`、`0x02CF1443`、`0x02CF1453`、`0x02CF1702`、`0x02CF1704`、`0x02CF1BF2`）。

