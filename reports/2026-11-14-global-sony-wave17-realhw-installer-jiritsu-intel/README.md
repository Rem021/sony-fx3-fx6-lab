# Wave-17 Live Global Sony BIONZ XR Real-Hardware Installer, `libJiritsu.so` / `AdjustControl`, & `CXD90057` Recovery Web Intelligence Sync (2026-11-14)
# 第十七波全球索尼 BIONZ XR 真机安装器、`libJiritsu.so` / `AdjustControl` 与 `CXD90057` 硬件恢复情报同步 (2026-11-14)

- **Date / 日期**: 2026-11-14
- **Phase / 阶段**: Phase 137 — Real-Hardware Main Track Part 3: Wave-17 Real-Hardware Sony BIONZ XR Installer & Recovery Intel Sync + 27th `fx3-firmware-lab` Auditor Alignment
- **Scope / 范围**: Bilingual clean-room synthesis of live-verified public technical intelligence covering:
  1. **Real-Hardware `/dev/nflasha15` (`ext2` `/usr`) Atomic File-Level Patching & Factory Restoration (`QAQLeonard/a7c2-fl23-research` → `QAQLeonard/a7c2-tools`)**
  2. **Senser USB Service Mode (`AdjustControl 0x40`), `libJiritsu.so` (`block 0x1001`) & RAM-Transient Execution (`chocotan/a7c2-re`, `YuuLuo/a7c2-service-preload`, `cokeenet/zve10-qemu`, `t2r05/fx30-senser-map`)**
  3. **Backup Property Toggles vs Dial/Menu Consumer Boundaries (`leogenot/sony-a7iv-feature-research`) & `BODYDATA.DAT` Unpacking (`DavidBuchanan314/fwtool.py` `a7iv` branch)**
  4. **`CXD90057` Multi-Port UART Boot (`48,000 → 115,200` baud RP2040), SRAM Fastboot (`18d1:4ee0`), `boot0` AES-XTS `SDM2` Partition Recovery & `CXD90058` 64 MiB SPI NOR Isolation (`DavidBuchanan314/ILCE-7M4-RE`, `Erlla/sony-a7m4-custom-firmware`, `Hearts-Ace/sony-a7r5-custom-firmware`)**
- **Compliance / 合规**: Zero embedded proprietary keys, zero Sony binary payloads committed, strictly verified public URLs and read-only (`os.O_RDONLY`) donor observations cited directly.

---

## English Technical Synthesis

### 1. In-Place `/dev/nflasha15` (`ext2` `/usr`) Atomic Patching (`QAQLeonard/a7c2-fl23-research` → `QAQLeonard/a7c2-tools`)

1. **Repository Evolution & Real-Hardware Architecture**:
   - Originally published as `QAQLeonard/a7c2-fl23-research` (renamed to **`QAQLeonard/a7c2-tools`** on November 7, 2026) and mirrored across macOS adapter work (`a7c2-fl23-macos`) and `lzh2016zzz/a7cr-fl23-research` for the Sony A7C II (`ILCE-7CM2`, v2.01) and A7CR.
   - Instead of re-signing an entire `BODYDATA.DAT` firmware package (which fails Sony's ECDSA/RSA signature gate in `sauu` / `sdfileinput.elf` on `CXD90057`), the installer performs **targeted file-level patching inside `/dev/nflasha15` (`ext2` mounted at `/usr`)**:
     1. Verifies `/dev/nflasha15 /usr ext2` mount identity and checks original AP/CP target file hashes + exact patch byte windows before touching flash.
     2. Temporarily remounts `/usr` read-write (`mount -o remount,rw /usr`), applies bounded byte patches (or stages backup copies), performs **full readback SHA-256 verification** with automatic rollback on any mismatch, and immediately restores read-only (`mount -o remount,ro /usr`).
     3. Invalidates or bypasses the `WBI2` hibernation snapshot (`nflasha5`) before battery-pull cold reboot so the updated `/usr/lib/appFw.so` takes effect cleanly on next cold boot.
2. **Direct Relevance to FX3 `v7.02` Route-1 (Hybrid Userland Stage-B)**:
   - Confirms that on `CXD90057` (`ILME-FX3` shares the exact same `nflasha15` `/usr ext2` encrypted `/dev/cnflasha15` + `WBI2` `nflasha5` cold-boot architecture), modifying `/usr` **does not require** re-flashing `loader_nor.bin`, `pformat_config.txt`, `mew.bin` FPGA, or `darwin` ND firmware.
   - **Critical FX3 vs A7C II Boundary**: A7C II binary offsets and partition tables do **not** apply to FX3 `v7.02`, and FX3 `7.02` has a **75 MiB `p3` (`/system`)** + **16 MiB `p7` (`/rootfs`)** + **500 MiB `p15` (`/usr`)** split that must be backed up at Tier-0/Tier-1 before any persistent `/usr` write is ever authorized (`persistent_emmc_writes_authorized = False` until real-camera readback completes).

---

### 2. USB Senser Service Mode (`AdjustControl 0x40`), `libJiritsu.so` (`0x1001`) & RAM Execution

| Component / Protocol | Technical Mechanism (Verified Public Sources) | FX3 `7.02` Lab Implication |
| :--- | :--- | :--- |
| **Senser USB Handshake (`ma1co/Sony-PMCA-RE`, `YuuLuo/a7c2-service-preload`)** | Mass Storage (`054C:0E8A`) challenge-response transitions camera into Service Mode (`054C:0336`) handled by `sen.elf` + `libsencore.so`, followed by SHA-1/SHA-256 key-table auth. | Matches our local Stage 285/286 `Communication05` service-access evidence (`read0` 88 B + `/tmp/jiritsu`). |
| **`AdjustControl` `PFUNC=0x40` (`cokeenet/zve10-qemu` `JIRITSU_CHANNEL.md`)** | Framing `{int16 block, int16 code}`: `0x0603` (`Backup_read` code `1`, `Backup_write` code `2`, `setBackupProtection` code `15`); `0x0404` (`RAM_READ` `0x00fe`); `0x1001` (`libJiritsu.so` command dispatch). | Per-property `readBackup`/`writeBackup` (`0x0603`) avoids large-blob USB chunk crashes (`SenserChunkSize` mismatch); **cross-model `Backup.bin` blob replacement is unsafe**. |
| **`libJiritsu.so` (`block = 0x1001`, codes `0x4001..0x4012`)** | Maps `JIRITSU_MODE` (`0x4001`), `MOUNT` (`0x4002`), `FORMAT` (`0x4003` — destructive!), `START` (`0x4004`), `DEBUG` (`0x4005`), `FIRMUP` (`0x4006`), `SET_FILE2` (`0x4010`), `GET_FILE2` (`0x4011`), `FILE_DELETE2` (`0x4012`), plus `SET_FILE_PATH` (`0x400f`). | `SET_FILE_PATH` / `GET_FILE2` path traversal (`/tmp/jiritsu/../..`) is the primary **zero-persistent-write** candidate for Tier-0 readback (`Backup.bin`, `psd.bin`, `defdet.bin`, `lensfile.bin`) once verified on FX3 `libJiritsu.so`! |
| **RAM-Only Execution (`chocotan/a7c2-re`, `YuuLuo/a7c2-service-preload`)** | (1) Writing `/tmp/jiritsu/libJit.so` triggers updater `dlopen` (`_init` runs as `Uid 0` inside `im.elf`); (2) `/etc/ld.so.preload` + `JIRITSU_DEBUG` spawns privileged child, or `sshd` on port 2222 (`dmode`). | **Brick Warning**: `busybox` is dynamically linked on `CXD90057`; writing a bad path into persistent `/etc/ld.so.preload` or exhausting `nflasha10` (`12 MiB` `/tmp` vfat) causes an unrecoverable software boot failure! Keep all Stage-0 probes strictly in volatile RAM. |
| **QEMU Emulation (`chocotan/a7c2-re`, `chocotan/a7c2-qemu`, `cokeenet/zve10-qemu`)** | Stock firmware GTK rendering via soft-GPE (`gpe-raster.c`, `gpe-sprite.c`), CPU `sony-lz77.c`, DMM/HDMI, `ramfb`, and `libJiritsu.so` `jiritsu_init` heap-corruption bypass. | Validates our `outputs/fx3-vm-trial/` and `outputs/fx3-vm/` dual-ISA QEMU architecture. |

---

### 3. `leogenot/sony-a7iv-feature-research` & `DavidBuchanan314/fwtool.py` (`a7iv`)

1. **`leogenot/sony-a7iv-feature-research` (MIT, ILCE-7M4 `v6.02`)**:
   - Demonstrates `serviceshell` setup, `fwtool.py` static extraction (`appfw_elf.py`, `bk4.py`), read-only `Backup` inspection, and `BK4` property toggling (e.g., `0x02cf1702` Shutter Angle Mode, `0x02cf1443` Log Shooting).
   - **Key Architecture Proof**: Simply flipping a `BK4` property bit in NVRAM exposes an on-screen indicator (e.g. Shutter Angle) without wiring dial handlers, menu trees, or `libmpr.so` / `cpapp-b.bin` consumers—confirming our **Unknown `U2` / `U3` thesis** that true FX6 feature parity requires **Stage-B AP userland (`appFw.so` + `global.xdb` + `.uxc`) coupled to Stock FX3 CP**, not NVRAM bit-flipping alone.
2. **`DavidBuchanan314/fwtool.py` (`a7iv` branch / `ma1co/fwtool.py` PR #52)**:
   - Public `CXD90057` `BODYDATA.DAT` → `FDAT` (`UDTRFIRM`) → `firmware.tar` extractor (`0700_part_image/dev/nflasha*`, `0110_backup/SYSIPSX-DSLR/*`, `0750_nor_loader/loader_nor.tar`, `0300_partconf/partinf.conf`).
   - Used strictly as a public reference for `UDTRFIRM` container geometry; `fx3-firmware-lab` stores **zero** proprietary decryption keys.

---

### 4. `CXD90057` Hardware Recovery: Multi-Port UART Boot, Fastboot, `boot0` AES-XTS & Separate SPI NOR

1. **Multi-Port UART Boot (`DavidBuchanan314/ILCE-7M4-RE`, `Sony-ILCE-7M4-Linux`)**:
   - The `CXD90057` AP (`4× Cortex-A35`) 48 KB BootROM monitors the Sony Multi/Micro USB accessory port RX pin after reset (`48,000` baud → `115,200` baud via RP2040 `tools/uart_boot`), staging an EL3 payload at `0xFE020000` to bring up **SRAM USB Fastboot (`18d1:4ee0`)** (`oem dumpbrom`, `oem partition`, `fastboot dump/flash`).
   - Unlike Type-C-only bodies (`α6700`, `A7C II`, `ZV-E10` which need motherboard UART test points or CC/Pico methods like `xyzhangxin/sony-a6700-powerful`), **ILME-FX3 retains the physical Multi/Micro USB connector**, preserving the `uart_boot` hardware unbrick lifeline (provided `VMC-BNCM1` LTC cable is disconnected during recovery).
2. **`SDM2` eMMC AES-XTS & Separate `64 MiB` Octal-SPI NOR (`Erlla/sony-a7m4-custom-firmware`, `Hearts-Ace/sony-a7r5-custom-firmware`)**:
   - `CXD90057` eMMC partitions marked `type=5, flag=1` (`nflasha3,4,7,8,12,15,23,30`) use **AES-XTS-256** (`crypt-emmc.ko`) with keys derived from eMMC `boot0` (`parse_emmc_boot0.py`), and do **not** enforce per-partition cryptographic signatures at cold boot.
   - **Crucial SPI NOR Warning**: The `CXD90058` ISP coprocessor (`cpapp-b.bin`, TOPPERS/FMP RTOS `@ 0x00108000`) boots from a **separate Octal-SPI NOR flash** (`infomisc.dat`, `DGU.bin`, `LdrBkup.bin`, `loader_nor.bin`, `MIS.bin + ddrtraining.dat`, `pcie_phy_fw.bin`, `cpapp-b.bin` copy at Sector `4096`). Flashing eMMC alone does **not** touch SPI NOR; conversely, running Route-2's `nor_loader_writer.sh` overwrites SPI NOR and risks permanent unrecoverable bricking if `ddrtraining.dat` or `cpapp-b.bin` mismatches!

---

## Reference Index (Public URLs)

| Project / Source | Focus Area | Canonical URL |
| :--- | :--- | :--- |
| `QAQLeonard/a7c2-tools` (ex `a7c2-fl23-research`) | Atomic `/dev/nflasha15` `/usr` ext2 patcher + rollback + restore | https://github.com/QAQLeonard/a7c2-tools |
| `chocotan/a7c2-re` & `chocotan/a7c2-qemu` | `dmode`, `libJit`, `sshd`, dynamic `busybox` brick notes, GTK QEMU `ramfb` | https://github.com/chocotan/a7c2-re |
| `leogenot/sony-a7iv-feature-research` | `serviceshell`, `BK4` property toggles vs consumer wiring gap | https://github.com/leogenot/sony-a7iv-feature-research |
| `DavidBuchanan314/fwtool.py` (`a7iv` branch) | `CXD90057` `BODYDATA.DAT` / `FDAT` / `UDTRFIRM` unpacker | https://github.com/DavidBuchanan314/fwtool.py |
| `DavidBuchanan314/ILCE-7M4-RE` | `CXD90057` 48 KB BootROM `uart_boot`, SRAM Fastboot `18d1:4ee0`, `boot0` XTS | https://github.com/DavidBuchanan314/ILCE-7M4-RE |
| `DavidBuchanan314/Sony-ILCE-7M4-Linux` | `CXD90057` Linux `4.9.337` GPL kernel, `SDM2`, `SPAcc` | https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux |
| `YuuLuo/a7c2-service-preload` | Senser `054C:0336`, `libJit.so`, `/etc/ld.so.preload` warnings | https://github.com/YuuLuo/a7c2-service-preload |
| `cokeenet/zve10-qemu` (`docs/JIRITSU_CHANNEL.md`) | `AdjustControl 0x40` block `0x1001` (`0x4001..0x4012`) & `0x0603` table | https://github.com/cokeenet/zve10-qemu |
| `t2r05/fx30-senser-map` | `ILME-FX30` Senser/Jiritsu channel & `appFw.so` product flags | https://github.com/t2r05/fx30-senser-map |
| `Erlla/sony-a7m4-custom-firmware` & `Hearts-Ace/sony-a7r5-custom-firmware` | Offline Unicorn/QEMU verification + `64 MiB` SPI NOR vs eMMC isolation | https://github.com/Erlla/sony-a7m4-custom-firmware |
| `xyzhangxin/sony-a6700-powerful` | External Pico boot & `nflasha*` eMMC unbrick | https://github.com/xyzhangxin/sony-a6700-powerful |
| `ma1co/Sony-PMCA-RE` | Base Senser USB service-mode & `AdjustControl` client | https://github.com/ma1co/Sony-PMCA-RE |

---

## 简体中文技术摘要

1. **真机 `/dev/nflasha15`（`ext2` `/usr`）原子级文件补丁路线（`QAQLeonard/a7c2-fl23-research` → `a7c2-tools`）**：
   - 跳过官方 `BODYDATA.DAT` ECDSA/RSA 签名重打包限制，在运行态通过校验 `/dev/nflasha15 /usr ext2` 与原文件哈希窗口、`mount -o remount,rw /usr`、写入补丁、**全量 SHA-256 回读校验（失败即回滚）**、立即恢复只读，并失效 `nflasha5`（`WBI2` 休眠快照）使冷启动生效。
   - 对 **FX3 `7.02` Route-1（混合用户态 Stage-B）** 的关键启示：无需刷写 SPI NOR（`loader_nor.bin`）、FPGA（`mew.bin`）或电子 ND（`darwin`）；但严禁直接套用 A7C II 偏移，且在获得真机 `p1/p2/p6/p18` 全量只读备份前，`persistent_emmc_writes_authorized` 必须保持 `False`。
2. **Senser `AdjustControl (0x40)` 与 `libJiritsu.so`（`0x1001`）服务通道边界**：
   - `0x0603` 负责单键 `Backup_read`/`Backup_write`（避免整块大对象读取触发 USB 分片崩溃），`0x1001` 分发 `0x4001..0x4012`（含 `SET_FILE2` / `GET_FILE2` / `SET_FILE_PATH` 路径穿越只读回读与 `JIRITSU_FORMAT 0x4003` 破坏性命令）。
   - `chocotan/a7c2-re` 与 `YuuLuo/a7c2-service-preload` 实证 `busybox` 为动态链接，任何持久修改 `/etc/ld.so.preload` 或写满 12 MiB `nflasha10` (`/tmp`) 均会导致不可恢复软砖，因此所有 Stage-0 探针必须严格留在易失 RAM 内。
3. **属性位翻转局限与 `CXD90057` 硬件级救砖隔离**：
   - `leogenot/sony-a7iv-feature-research` 证明仅改 `BK4` 键值只能点亮部分 HUD 文本，无法补全拨轮、菜单与 `appFw.so` 消费链；完整功能必须依赖 Stage-B 用户态框架。
   - `ILCE-7M4-RE` 与 `sony-a7m4-custom-firmware` 确认 `CXD90057` 的 Multi 口保留了 `48,000 → 115,200` baud RP2040 `uart_boot` + SRAM Fastboot（`18d1:4ee0`）硬件救砖通道，同时 `CXD90058` CP RTOS 拥有独立的 **Octal-SPI NOR 闪存**，严禁跨机型执行 Route-2 `nor_loader_writer.sh` 覆写 NOR。
