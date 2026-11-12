# Stage-A Non-Persistent Hardware Execution Runbook (EN / 简体中文)

- **Schema & Generator**: `stage_a_readiness_packet_v1` · [`outputs/fx6-on-fx3-closure/fx6_closure/hardware_readiness_packet.py`](../outputs/fx6-on-fx3-closure/fx6_closure/hardware_readiness_packet.py)
- **CLI Entrypoint**: `make readiness-packet` (`python3 -B -m fx6_closure build-readiness-packet`)
- **Hard-Locked Safety Posture**: `offline_engineering_complete = True` · `persistent_emmc_writes_authorized = False` · `persistent_write_release = False`

> [!CAUTION]
> **STRICT NON-PERSISTENT RAM-OVERLAY BOUNDARY (`0` BYTES WRITTEN TO eMMC / SPI NOR)**
> Stage-A never modifies `/dev/nflasha*`, `/dev/cnflasha*`, `/dev/pnflasha*`, `/dev/mtd*`, `p1:/updater`, `p2:/setting`, `p5:/wbi`, `p6:/tmp/jiritsu`, `p8:/cp`, `p12:/cert`, `p15:/usr`, or `p18:/lens`. Every binary adaptation (`P1..P9 + Fan`), loopback image (`opelog.vfat`), shadow `BK4\0` store, and one-shot arming token (`/tmp/mod_arm_once`) resides exclusively in volatile Linux DDR (`tmpfs`). Removing power immediately restores 100% stock Sony ILME-FX3 firmware.

---

# Part I — English Operator Runbook

## 1. Pre-Flight Workstation Verification (`make readiness-packet`)

Before connecting any physical Sony ILME-FX3 (`0x91030080`) body or inserting media, run the complete offline verification & readiness-packet generator on the host workstation:

```bash
# 1. Verify 57+57 bilingual BYOF manifest, all 5 automated test suites, and candidate dry-run
make verify-byof
make test
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
       --tier0-bundle-dir /path/to/fx3_tier0_capture \
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
   - Run `/etc/fx6_overlay/30-stage-a-orchestrator.sh`:
     1. Immediately unlinks `/tmp/mod_arm_once` (**Clear-Before-Exec** — guarantees next reboot is stock FX3 even on sudden kernel panic or battery pull).
     2. Asserts WBI hibernation guard (`p5:/wbi` unmounted/read-only, `BIS` hibernation disabled).
     3. Verifies all **11 SHA-256 digests** strictly **before** the first `insmod` or `mount --bind`.
     4. Activates the 10-step RAM overlay (`P9` `upm.ko` RAM replacement at slot `#24`, `/dev/loop7 -> /etc/opelog` `8 MiB` `FAT16` loopback, RAM-shadow `BK4\0` bind, `P1/P3/P4/P8/Fan` `.so` read-only bind mounts, and bounded watchdog supervision of `im.elf`).
     5. On exit or any step failure, unwinds mounted steps in strict reverse **`10..1` LIFO** order.

### Phase H2 — Emergency Recovery & Post-Power-Cycle Stock FX3 Verification

1. **Emergency Instant Recovery (At Any Moment)**:
   - Turn power switch **OFF** and remove the **NP-FZ100** battery for **10 seconds**, then re-insert and power **ON**.
   - Because `0` bytes were written to eMMC, SPI NOR, `p2:/setting`, `p5:/wbi`, or `p8:/cp`, and `/tmp/mod_arm_once` existed only in volatile DDR, the camera cold-boots directly into **100% unmodified stock FX3 Bank 0**.
   - **If `p1` Updater Shell Was Entered Manually**: Always execute the mandatory **2-step atomic `U5` Bank 0 exit** before rebooting:
     ```sh
     rm -f /setting/updater/mode* && sync
     /usr/bin/ud_send_lsi.elf 0
     ```
2. **Post-Trial Bit-Exact Audit**:
   - Confirm stock FX3 Ver. 7.02 Shooting HUD, menu version screen, E-mount lens communication, IBIS/Gyro, fan control, and dual-slot recording operate identically to pre-trial baseline.
   - Re-read `sector0`, `p2:/setting/Backup.bin`, `p8:/cp/tomco.txt`, and `p5:/wbi` header (`O_RDONLY`) and verify **100% SHA-256 parity** against Phase H0 `backup-manifest.json`.

---
---

# 第二部分 — 简体中文真机执行操作手册 (Stage-A)

## 1. 宿主机离线预检与就绪包生成（`make readiness-packet`）

在连接任何索尼 **ILME-FX3（机型 ID `0x91030080`）** 真机或插入存储卡之前，必须先在宿主机完成全量离线验证并生成确定性预检就绪包：

```bash
# 1. 运行双语 57+57 项 BYOF 清单审计、全仓 5 大测试套件与候选包干跑
make verify-byof
make test
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
       --tier0-bundle-dir /path/to/fx3_tier0_capture \
       --output /tmp/stage-a-go-packet.json
     ```
   - **唯一放行条件**：仅当返回码为 `0`，且输出满足 `"real_tier0_hardware_backup_verified": true`、`"stage_a_ram_trial_hardware_go": true`（同时 `"persistent_emmc_writes_authorized"` 依然硬锁定为 `false`）时，方可进入 Phase H1。任何合成清单、占位序列号/`cid`、缺文件、双遍哈希不等、比特翻转或魔数头（`'8246'` / `'BK4\0'` / `'FAT16'` / `tomco.txt` / `'WBI2'`）异常均会被确定性拒绝。

### Phase H1 — Stage-A 纯内存（`tmpfs`）零写闪存非持久试运行（`Gate G09` / `G11`）

1. **在易失性 `tmpfs`（`/tmp/fx6_stage_a`）中暂存载荷**：
   - 将已校验的 `30,956 B` SVR4 `cpio newc` 归档（`SHA-256: eaa7902770968b44521d991f37285574c65ad2a92cef59d7434e9861467efbd9`）与 11 项适配运行时组件解压至 `/tmp/fx6_stage_a`（峰值占用 `57.46–130.76 MiB`，远低于 `256.00 MiB` 安全上限）。
2. **创建单次内存令牌并启动原子编排器**：
   - 仅在内存 `tmpfs` 创建单次授权令牌 `/tmp/mod_arm_once`（严禁写入任何持久分区）。
   - 执行 `/etc/fx6_overlay/30-stage-a-orchestrator.sh`：
     1. **执行前即删（Clear-Before-Exec）**：启动首步立即删除 `/tmp/mod_arm_once`，确保即便发生内核崩溃或直接拔电池，下次上电必回原厂 FX3。
     2. **休眠阻断**：强制锁定 `p5:/wbi` 只读/未挂载并阻断 `BIS` 休眠触发。
     3. **挂载前全量校验（Verify-Before-Mount）**：在执行第一次 `insmod` 或 `mount --bind` 前，完整核对全部 **11 项 SHA-256**。
     4. **10 步正向激活与逆序 `10..1` LIFO 卸载**：按序完成槽位 `#24` `P9` `upm.ko` 内存替换、`/dev/loop7 -> /etc/opelog` `8 MiB` `FAT16` 回环挂载、RAM-Shadow `BK4\0` 绑定、`P1/P3/P4/P8/Fan` 只读绑定挂载及带看门狗的 `im.elf` 监管；退出或任一步失败时严格按 **`10..1` 逆序 LIFO** 完整卸载。

### Phase H2 — 紧急断电恢复与断电重启后原厂逐位一致性复核

1. **任意时刻一键紧急恢复**：
   - 将机身电源拨至 **OFF**，取出 **NP-FZ100** 电池静置 **10 秒** 后重新装回开机。
   - 由于全流程对 eMMC、SPI NOR、`p2:/setting`、`p5:/wbi`、`p8:/cp` 均为 **0 字节写入**，且内存 `tmpfs` 随断电瞬间清空，相机将 100% 冷启动回**未受任何改动的原厂 FX3 Bank 0 系统**。
   - **若曾手动进入 `p1` 维护环境**：重启前必须按序执行 **`U5` 双步原子复位**：
     ```sh
     rm -f /setting/updater/mode* && sync
     /usr/bin/ud_send_lsi.elf 0
     ```
2. **试运行后逐位一致性复核**：
   - 开机核对原厂 FX3 Ver. 7.02 拍摄主界面、系统版本菜单、E 卡口镜头通信、防抖陀螺仪、风扇温控与双卡槽录制均 100% 正常。
   - 以只读模式复读 `sector0`、`p2:/setting/Backup.bin`、`p8:/cp/tomco.txt` 与 `p5:/wbi` 头部，确认其 SHA-256 与 Phase H0 `backup-manifest.json` **100% 逐字节一致**。
