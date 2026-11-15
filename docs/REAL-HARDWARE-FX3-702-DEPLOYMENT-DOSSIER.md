# Sony ILME-FX3 (`Ver. 7.02`) 实机 Stage-B 双系统部署、逃生舱与无痕卸载权威手册（Milestone Phase 147 Dossier）

> **文档定位 / Document Scope**: 本手册为 **Milestone Phase 147 实机上台架就绪总闸门（`realhw_milestone147_master_gate_v1`）** 的权威工程总册，覆盖 **Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, `ALCIN_UUD`)** 上部署 **ILME-FX6 (`Ver. 6.01`)** Hybrid Userland Stage-B 双系统的完整链路：  
> `054C:0DA1 -> 054C:0336` (`SET_FILE2` + `AdjustControl 0x40`) Tier-0 16 面冷备 → 实机二进制兼容适配（`U2` / `U3` / `libmpr.so` / `U6`）→ Strategy-A `nflasha20 -> nflasha30` 零 Sector-0 桥接与 BYOF SD 卡载荷包（`U4`）→ `/dev/cnflasha15` 原子 `/usr/bin/im.elf` 逃生舱包装器 → `p1` 首行清除救援（`U5`）与 `H0 == H3` 16 面零漂移无痕卸载 SOP。  
> **配套文档 / Companion Docs**: [`STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md`](./STAGE-B-OPERATOR-SOP-AND-UNBRICK-RUNBOOK.md) · [`STAGE-B-ARCHITECTURE-AND-SAFETY.md`](./STAGE-B-ARCHITECTURE-AND-SAFETY.md) · [`BYOF-REPRODUCTION.md`](./BYOF-REPRODUCTION.md) · [`outputs/fx6-on-fx3-closure/README.md`](../outputs/fx6-on-fx3-closure/README.md)

> [!CAUTION]
> **刚性安全红线与工程状态严格边界（Hard-Locked Safety Posture & Facts vs Bench Boundary）**
> 1. **实验仓与离线门禁硬锁（当前仓库/CI 默认锁定态）**：
>    - `persistent_emmc_writes_authorized = False` · `persistent_write_release = False`
>    - `spi_nor_write_authorized = False` · `hardware_live_attachment_authorized = False`
>    - `physical_usb_packets_emitted = 0` · `otp_fuse_touches = 0` · `rpmb_counter_increments = 0` · `passive_tx_bytes_emitted = 0`
>    - `sector0_mutation_bytes = 0` · `cp_mutation_bytes = 0` (`p8:/cpapp-b.bin` 零改动) · `wbi_mutation_bytes = 0` (`p5:/wbi` 禁止写入/休眠) · `calibration_mutation_bytes = 0` (`C2PA RQ_LIC.DAT` / `p2:/Backup.bin` 仅作内存影子覆盖或零修改)
> 2. **已闭环实证 vs 未执行实机台架的严格区分**：
>    - **已闭环（Verified Offline / Unicorn / POSIX `/bin/sh` / QEMU Real FX3 `7.02` `4.9.337-scel+`）**：Phases 134–143 与 Milestone 147 全部 6 支柱代码、双模测试（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1`）以及 Rounds 28 (`r28a..r28c`) & 29 (`r29a..r29c`) 实机 ARM64 内核 QEMU 演练已全部通过并留痕。
>    - **尚未执行（Not Yet Executed）**：**真实物理 Sony ILME-FX3 实机上电 USB 连接与现场台架采集会话（Physical Camera Bench Session）尚未执行**；在真实物理机房台架通过操作员独立 `Gate G10..G12` 实机回读签收前，禁止任何持久化写入或 USB 实包发射。

---

## English Executive Summary

This dossier consolidates **Milestone Phase 147 (`verify-milestone-147`)** — the real-hardware bench-readiness closure spanning **Phases 134–143** and **Rounds 28–29** live **Sony ILME-FX3 `Ver. 7.02` (`4.9.337-scel+`)** ARM64 QEMU kernel rehearsals:

- **Tier-0 16-Surface Streaming Cold Backup (`G43`, Pillars 14–17)**: Transitions USB PID `054C:0DA1 -> 054C:0336` via `SET_FILE2` to execute the Stage-288 hardened `libJiritsu.so` (`J0` + CRC32 + self-`unlinkat`, `O_RDONLY|O_NOFOLLOW`, `ld-2.25.so` `p_align=0x10000`), streaming all 16 critical storage surfaces via `AdjustControl (0x40)` (`FX3RCPT1`) to SD media and pulling over `p6 <= 4 MiB` (`FX3CHK1`) sliding windows with `GF(256)` P+Q RAID-6 redundancy and body-serial anti-transplant lock.
- **Binary Compatibility Closure (`U2/U3/U6/libmpr.so`, Phases 137 & 140)**: Leaves FX3 Stock CP RTOS (`p8:/cpapp-b.bin`) untouched (`cp_mutation_bytes = 0`), bridges `Backup.bin` (`819 -> 840`) & `0xfa0080` Bank 0/1 load maps, and closes `libmpr.so` (`74` direct pass-through + `15` shimmed calls + `20` MAIN `DmmCfg.bin` pools) plus all `19` `libJiritsu.so` `0x1001` opcodes (`U6`).
- **Strategy-A Zero-Sector-0 Bridge (`U4`, Phase 136) & BYOF SD Stage-B Bundle (Phase 143)**: Symlinks `/dev/nflasha20 -> /dev/nflasha30` (`48.00 MiB`) and mounts `tmpfs /etc/opelog` (`OPE/00/01`) with `sector0_mutation_bytes = 0`, loading verified FX6 Stage-B components (`< 64 MiB` `tmpfs` budget; `9.234 MiB` local / `8.135 MiB` clean-room) from `/mnt/sd/FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST` (`13/13` SHA-256 lock + body serial binding).
- **Atomic `/dev/cnflasha15` Escape-Hatch Wrapper (`G44`, Round 29) & `H0 == H3` Clean Uninstaller (`Phase 143`)**: Wraps `/usr/bin/im.elf` atomically **strictly via `/dev/cnflasha15`** (`/dev/pnflasha15` hard-blocked; mid-write bit-flip/truncation rolls back bit-identically to `.orig`), enforcing 3 instant escape hatches (`EH1` SD absent `47 us <= 50 us` stock FX3 bypass, `EH2` `STOP_STAGEB.FLAG` / `MENU+PLAY`, `EH3` fail-closed manifest fallback + `LAST_BOOT_DIAG.TXT`), `p1` line-1 `rm -f /setting/updater/mode* && sync` (`U5` unconditional return to `p3`), and `16/16` `SHA256(H0) == SHA256(H3)` factory restoration.
- **Safety Posture Separation**: All offline verification, QEMU `4.9.337-scel+` kernel rehearsals (Rounds 28–29), and dual-mode unit suites are **CLOSED**, whereas **live physical FX3 bench attachment remains LOCKED (`persistent_emmc_writes_authorized = False`, `hardware_live_attachment_authorized = False`, `physical_usb_packets_emitted = 0`)** until physical Tier-0 capture verification (`G10..G12`).

---

## 第一章 实机部署全景架构与 6 支柱总闸门映射

| 支柱 ID | 对应模块与 Phase | 核心技术契约与通过门槛 | 实测基线数据（Local Donor / Clean-Room） |
| :--- | :--- | :--- | :--- |
| **`P1`** | [`fx3_safety`](../outputs/fx3-safety/fx3_safety/realhw_jiritsu_cnflasha_and_44gate_guard.py) (Ph142) | **`>= 44` 安全门禁 (`G01..G44`)**：干跑演练 `>= 44/44`；默认离线态严格锁定 `G10..G12`（`41/44`），严禁未采集 Tier-0 直接放行实机挂接 | `44/44` dry-run, `41/44` offline lock (`G43` USB-PID/Jiritsu, `G44` `cnflasha15`/Mode1) |
| **`P2`** | [`fx3_recovery`](../outputs/fx3-recovery-adapter/fx3_recovery/__init__.py) (Ph134/138/139) | **`>= 17` 恢复支柱**：`SecureBoot` 全链校验、`/dev/cnflasha15` 原子写入器（`pnflasha15` 拒绝）、`AdjustControl (0x40)` `FX3RCPT1` 16 面 SD 流式冷备与 `p6 <= 4 MiB` `FX3CHK1` 滑窗回传 | `17/17` (`otp_fuse_touches=0`, `rpmb_counter_increments=0`, `passive_tx_bytes_emitted=0`, `physical_device_writes=0`) |
| **`P3`** | [`fx3_firmware_lab`](../outputs/fx3-firmware-lab/fx3_firmware_lab/realhw_mpr_dmm_rec_pipeline_bridge_auditor.py) (Ph137/140) | **`>= 28` 实机二进制审计器**：`U2` Stock-CP RTOS 零侵入、`U3` `Backup.bin` `819->840` & `0xfa0080` Bank 0/1、`libmpr.so` `74` 直通 + `15` 垫片 + `20` MAIN `DmmCfg.bin` 内存池 | `28/28` (`fx6_only=1169` local / `15` clean-room, `shim=15`, `passthrough=74/12`, `calibration_mutation_bytes=0`) |
| **`P4`** | [`fx3-vm`](../outputs/fx3-vm/) (Ph141) | **`>= 24` 阶段 HIL 协同仿真**：4 态双启动（SD 缺席/合法 Stage-B/篡改回落/`p1` 救援）与 22/23/24 阶段异构硬件外设协同 | `24/24` (`emmc_corruptions=0`, `cp_mutation_bytes=0`, `wf12_00342260_hits=0`) |
| **`P5`** | [`fx6_closure`](../outputs/fx6-on-fx3-closure/fx6_closure/realhw_sd_stageb_bundle_and_uninstaller.py) (Ph136/143) | **`U4/U5/U6` 闭环 + BYOF SD 载荷包 + `H0 == H3`**：Strategy-A `nflasha20 -> nflasha30` 零 Sector-0 桥接、3 道逃生舱 (`EH1 <= 50 us`)、16 面工厂还原 | `U4/U5/U6 CLOSED`, `EH1=47 us`, `H0==H3 16/16`, `5/5` 掉电演练通过 (`tmpfs 9.234 MiB`) |
| **`P6`** | Round 28 & Round 29 QEMU 实证 | **实机 FX3 `7.02` (`4.9.337-scel+`) 内核 QEMU 演练收据**：`summary.json` 只读审计（Clean-Room 下确定性合成回退），零 NOP、零崩溃、零 eMMC 篡改 | `R28 (3/3)` + `R29 (3/3)` (`nop_count=0`, `crashes=0`, `emmc_write_count=0`) |

---

## 第二章 Step 1 — `054C:0DA1 -> 054C:0336` (`SET_FILE2`) Tier-0 16 面流式冷备规程

### 2.1 USB 阶段迁移与 Stage-288 `libJiritsu.so` P0 加固
在任何文件系统或包装器改动**之前**，必须通过只读冷备完成本机全量 16 面取证留档（`Gate G43` + `Pillar 17`）：

1. **USB PID 受控切换 (`054C:0DA1 -> 054C:0336`)**：
   - FX3 `7.02` 原厂维护模式以 `054C:0DA1` 枚举；通过受控 `SET_FILE2` + **`AdjustControl (0x40)`** 请求触发 `libJiritsu.so`（`225,200 B`，SHA-256 `bdef58b2...`）内联 `dlopen` 通道，切换至调试传输端点 `054C:0336`。
   - **U6 闭环证明**（Phase 136）：Category `0x1001` 全部 19 条内置操作码均不直接导出 `/setting` 或 `/dev/nflasha*`，仅允许经由 `SET_FILE2` 注入经 Stage-288 §4 P0 加固的瞬态读写工兵（`10,032 B` `ET_DYN` `e_machine=183`）。
2. **Stage-288 §4 六项 P0 安全加固约束**：
   - **入口自毁 (`unlinkat`)**：`.init` 入口立即执行 `unlinkat("/tmp/jiritsu/libJit.so")`，Round 28 实证 `errno=2` (`ENOENT`)，内存驻留后磁盘零残留；
   - **严格只读与反追踪打开**：所有设备读取强锁 `O_RDONLY | O_NOFOLLOW`（`devno.ko`/`emmc.ko`/`setup_nflash` 映射 `/dev/pnflasha0` 与 `/dev/nflasha*`），禁止截断（零 `O_TRUNC`）；
   - **64 KiB 页对齐 ELF 与固定哈希**：严格对齐 `ld-2.25.so` 的 `PT_LOAD p_align=0x10000` 及 `DT_HASH (1,1,0,0)`；
   - **8 字节帧头 + CRC32 封包**：`J0` 魔数 + `u16 length` + `u32 CRC32`，如 Round 28 实证 `512 B Sector-0`（`"8246"` / `"2.00"` / `30` 分区，CRC32 `0x29f1a341`）打包为 `528 B` `FX3S0OK` 帧；
   - **双通路无损回传**：
     - **SD 流式冷备通路 (`FX3RCPT1`)**：直接流式转储全量 16 面镜像与 `FX3RCPT1` 机身绑定回执至实验 SD 卡；
     - **`p6 <= 4 MiB` 滑窗回传通路 (`FX3CHK1`)**：当通过 `p6` 小窗口分块拉取时，严格限定单窗 `<= 4 MiB` 并附带 `FX3CHK1` 逐窗校验码与 `GF(256)`（`0x11d`）P+Q RAID-6 冗余校验，严禁跨机身移植。

### 2.2 16 面 Tier-0 必检指纹清单（`H0` 黄金基线）
必须覆盖：`sector0`（512 B `'8246'`）、`p1`（VFAT + `dat2=91030080` + `dat3`）、`p2`（`Backup.bin` / `psd.bin` / `defdet.bin` / `cxd90057.dtb`）、`p3`、`p5`（`WBI2`）、`p6`、`p7`、`p8`（`cpapp-b.bin`）、`p12`（`C2PA RQ_LIC.DAT`）、`p15`（`/usr`）、`p18`（`/lens/lensfile.bin`）、`p23`、`p30`、`spi_nor`（`ddrtraining.dat` + `loader_nor.bin`）、`otp`、`rpmb`（后三者仅元状态/只读审计，`0` 修改）。

---

## 第三章 Step 2 — 实机二进制兼容闭环（`U2` / `U3` / `libmpr.so` / `U6`）

- **`U2` Stock-CP RTOS 零侵入红线 (`p8:/cpapp-b.bin`)**：FX3 `7.02` 与 FX6 `6.01` `tomco.txt` 共享完全一致的 4 个 `memcfg=` 内存池（`1,724.00 MiB`）与 20 个 IPC 键；Stage-B 严禁修改 `p8`（`cp_mutation_bytes = 0`），通过 AP 侧 `P11` 垫片合成 FX6 独有阻塞队列 `0x92d2091c`（RTC `/dev/rtc0->udate`）与 `0x91db059b`（Smart Handle），保活 Stock-CP 全部 `44/44` `0x92840747` 操作码与 5 轴 IBIS 居中锁止。
- **`U3` 校准数据结构与 Bank 0/1 映射 (`Backup.bin` `819 -> 840`)**：Phase 137 验证 FX3 `Backup.bin` `819` 条目向 FX6 `840` 槽位及 `0xfa0080` Bank 0/1 映射的无冲突适配，运行期通过易失性 `/tmp/bk4_shadow`（`BK4\0`）内存影子承接语言/飞行模式（`0x019e0012=00` / `0x0051000f=00` / `0x01a20002=00`）与 CJK 字符集配置，确保物理 `p2:/setting/Backup.bin` 零字节写入。
- **`libmpr.so` & `DmmCfg.bin` 录影管线桥接**：Phase 140 实证 `libmpr.so` **74 项直接透传符号 + 15 项精确垫片符号**（屏蔽 FX6 专属 SDI 与物理 ND 滤镜调用）及 **20 个 MAIN `DmmCfg.bin` 内存池**；Round 29 `r29a` 已在真实 FX3 `7.02` ARM64 QEMU 内核中实测通过 `libmpr.so` `11/11` 核心符号、6 参数切换（`Base ISO 800->12800`、`23.98p`、`180.0 deg / 1/48s`、`5600K`、`S-Log3/S-Gamut3.Cine`）以及 `/tmp/r29_clip/C0001.MXF`（`640 B`, `mpr_rec_finalized=1`, `rsv_orphan_count=0`）完整封口。

---

## 第四章 Step 3 — Strategy-A `nflasha20 -> nflasha30` 零 Sector-0 桥接与 BYOF SD 载荷包

- **Strategy-A 零重分区桥接 (`U4` 闭环)**：拒绝高风险的 `edisx.elf` eMMC 重分区（`sector0_mutation_bytes = 0`）。启动阶段建立 `/dev/nflasha20 -> /dev/nflasha30`（`48.00 MiB`，兼容 `/dev/cnflasha30` 加密块层映射）符号链接，并将操作日志挂载为易失性 `tmpfs /etc/opelog`（含 `OPE/00` 与 `OPE/01` 目录）。FX3 原厂 `Sector 0`（30 分区）、`p12:/cert` 与 `p18:/lens` 全程 100% 原样保留。
- **BYOF SD 卡 Stage-B 目录树与清单验签（Phase 143）**：
  - `/FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST`：强制绑定机身序列号与 Tier-0 `FX3RCPT1` 回执哈希（拒绝跨机身串卡启动），锁定 **13/13 Stage-B 载荷 SHA-256**；
  - `/FX6_STAGEB/shim/`：`libgrm-fbinit9.so`、`libmpr_fx6_to_fx3_bridge.so`；
  - `/FX6_STAGEB/usr_overlay/`：FX6 Stage-B 兼容库与语言资源包（`tmpfs` 总占用 `< 64 MiB`，实测 `9.234 MiB` 本地 / `8.135 MiB` 洁净室；`appFw.so` `e2bc2619...` 通过只读回环绑定，`libWlanResource.so` `47fec188...` 隔离 `WF-12 00342260` 无限重启）；
  - `/FX6_STAGEB/runtime/bk4_ram_shadow.seed` & `/FX6_STAGEB/rescue/uninstall_restore_stock.manifest`。

---

## 第五章 Step 4 — `/dev/cnflasha15` 原子 `/usr/bin/im.elf` 逃生舱包装器与 3 道毫秒级 bypass

> [!IMPORTANT]
> **`/dev/cnflasha15` 强制通道禁令 (`Gate G44` & Round 29)**  
> 凡修改 `/usr/bin/im.elf` 包装器，**必须且只能经由加密块设备节点 `/dev/cnflasha15`（或对应映射 `/dev/nflasha15`）原子操作**；**绝对禁止直接写入 `/dev/pnflasha15`（底层物理设备）**，否则将破坏加密映射一致性并立即被安全守卫拦截（`pnflasha15_rejected=1`）。

1. **原子安装与回滚实证（Round 29 `r29a / r29b`）**：
   - 将原厂 `/usr/bin/im.elf`（`40,920 B`，SHA-256 `2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772`）原子备份为 `.orig`，写入 `128 B` 逃生舱启动包装器（`edb450bb...`）并立即执行 `MS_REMOUNT | MS_RDONLY`（验证 `EROFS` 只读锁死，耗时 `4.81 ms`）；严禁写入 `/etc/ld.so.preload`。
   - **写中故障自愈（`r29b`）**：当注入 1-bit 翻转 + 50% 短写损坏（`735f8c54...`）时，安装器在 `8.90 ms` 内自动从 `.orig` 原子回滚并恢复与原厂完全一致的 `2838e5da...`。
2. **三道独立“零变砖”物理逃生舱（Round 28 `r28a..r28c` & Phase 143）**：
   - **`EH1` 无卡极速旁路**：未检测到 `/mnt/sd/FX6_STAGEB/FX6_STAGEB_BOOT.MANIFEST` 时，包装器跳过所有挂载与验签，实测耗时 **`47 us`（硬指标 `<= 50 us`）** 返回 `STOCK_FX3_BYPASS`（`rc=10`），零延迟直启原厂 FX3 `7.02`；
   - **`EH2` 物理防误触标志与按键组合**：检测到 SD 卡根目录 `STOP_STAGEB.FLAG` 或冷启动按住 **`MENU + PLAY`**（兼容 `FX3_SAFE_STOCK.FLG`），立即旁路进入原厂系统并可选触发干净自动卸载；
   - **`EH3` 清单/序列号/13 锁篡改失效关闭**：当检测到哪怕 **1 字节** 清单或载荷篡改（`r28c` 实测 `669 us <= 50 ms`），立即 `FAIL_CLOSED_STOCK_FX3_FALLBACK`（`rc=11`）拒绝挂载 `tmpfs` 并输出 `/mnt/sd/FX6_STAGEB/LAST_BOOT_DIAG.TXT` 排障日志，直接启动原厂系统。

---

## 第六章 Step 5 — `p1` 首行救援（`U5`）与 `H0 == H3` 无痕卸载 SOP

### 6.1 `p1` 首行清除单次启动锁与强制返回 `p3`（Round 29 `r29c` & `U5`）
为彻底防止更新器循环卡死（`p1` bootloop），所有从恢复/更新模式退出的操作**必须遵守 `U5` 两步退出契约**：
1. 在 `/sbin/init` 第一行或恢复入口强制执行：
   ```sh
   rm -f /setting/updater/mode* && sync
   ud_send_lsi.elf 0
   ```
2. Round 29 `r29c` 在真实 FX3 `7.02` 内核中实证：清除 `mode6` 后 `mode_files_remaining == 0`、`dat2 == 91030080`、`p3` 零改动、`next_cold_boot_bank == p3`，全流程耗时 `16.69 ms`。

### 6.2 `H0 -> H1 -> H2 -> H3` 16 面原厂字节级无痕卸载规程（Phase 143）
| 阶段 | 状态定义 | 关键执行动作 | 验证红线 |
| :--- | :--- | :--- | :--- |
| **`H0`** | 原厂 FX3 `7.02` 黄金基线 | Step 1 完成全量 16 面只读快照并生成 `FX3RCPT1` + `GF(256)` 校验卷 | `16/16` SHA-256 锁定记录 |
| **`H1`** | Stage-B 原子接入态 | 通过 `/dev/cnflasha15` 原子包装 `/usr/bin/im.elf`（保留 `.orig`）并验证 `EH1..EH3` | `/dev/pnflasha15` 写入次数 `0`；`EROFS` 重新挂载成功 |
| **`H2`** | Stage-B 双系统拍摄态 | 插入已绑定本机序列号的 SD 卡运行 Stage-B 易失性 `tmpfs` 覆盖层与 `BK4\0` 影子 | `sector0 / p2 / p5 / p8 / p12 / p18` 持久化修改 `0 B` |
| **`H3`** | 原厂字节级干净卸载态 | 拔卡或触发 `uninstall_restore_stock.manifest`：经 `/dev/cnflasha15` 原子还原 `.orig -> /usr/bin/im.elf`，删除包装器残余，执行 `sync` + `MS_RDONLY` + `p1` 首行清理 | **`16/16` 存储面 `SHA256(H0) == SHA256(H3)`**，零 `.orig` 残留；通过 `5/5` 卸载中掉电恢复演练 |

---

## 第七章 上机前必跑门禁指令清单（Milestone 147 Verification Matrix）

执行以下全部命令时，默认保持**洁净字节码**（`/usr/bin/python3 -B`），并可在双模（本地只读供体与无供体洁净室 `FX3_FX6_FORCE_CLEAN_ROOM=1`）下交叉互验：

```sh
# 1. Milestone 147 44-Gate 安全总闸门（G01..G44，验证 G43/G44 与离线 G10..G12 真值锁定）
make verify-44-gates

# 2. 17+ 支柱恢复与流式冷备闭合门禁（SecureBoot + cnflasha15 + AdjustControl 0x40 + p6<=4MiB）
make verify-17pillar-recovery

# 3. BYOF SD Stage-B 载荷包、3 道逃生舱与 H0==H3 16 面无痕卸载演练门禁
make verify-sd-stageb-bundle

# 4. Milestone Phase 147 六支柱实机上台架就绪总闸门（< 3.0s，本地供体 + 洁净室双模）
make verify-milestone-147
FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-147

# 5. 全实验室快速核心门禁与全量洁净单元测试审计
make verify-fast
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```
