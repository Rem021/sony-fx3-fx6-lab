# Round 28：FX3 7.02 原厂内核真机准备实跑 — 可逆 SD 卡双启动逃生门、`ld-2.25.so` 硬化 `libJit.so` 自删除 Sector-0 只读探针与 Strategy-A `nflasha20/21` 零改分区桥接

> **日期**：2026-11-14 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **目标**：在未修改的真实 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 **`/lib/ld-2.25.so`** 下，通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`, `cortex-a35`, `5120 MiB`）实机预演（`r28a` / `r28b` / `r28c`），完成真机上线前最关键的 3 项机制实证：
> 1. **Stage-288 硬化 `libJit.so` 自删除只读 `Sector 0` 探针（真实 `ld-2.25.so` `dlopen`/`dlclose`）**：
>    - 编译 `64 KiB`（`PT_LOAD` `p_align=0x10000`）对齐的 ARM64 `ET_DYN` 共享库 `/tmp/jiritsu/libJit.so`（`10,032 B`）；constructor 入口立即调用 `unlinkat(AT_FDCWD, "/tmp/jiritsu/libJit.so", 0)` 实现加载即自删除（`stat` 验证返回 `ENOENT` / `errno=2`）；
>    - 以严格只读 `O_RDONLY | O_NOFOLLOW` 打开 `/dev/pnflasha0`，校验精确 `512 B` 读取（错误不截断），验真 Sony `"8246"` / `"2.00"` / `n_partition=30` 分区表（`p1: 0x80..0xbf80`, `p20=0`, `p21=0`, `p30: 0x346000..0x18000`）及 IEEE CRC32（`0x29f1a341`），并在全部校验通过后以 `O_WRONLY | O_CREAT | O_EXCL` 写出 `528 B` `FX3S0OK\0` 回执包 `/tmp/jiritsu/sector0.pkt`，`dlclose` 返回 `0`；
> 2. **Strategy-A 零 Sector-0 改分区挂载桥接（`U4` 实机验证）**：
>    - 在运行中 FX3 `7.02` 客户机内配置 `/dev/nflasha30 -> /dev/cnflasha30` 与 `/dev/nflasha20 -> /dev/nflasha30`，并在 `/etc/opelog` 挂载 `tmpfs`（预建 `OPE` / `OPE/00` / `OPE/01` 并经 `/proc/mounts` 验证），在 **`sector0_repartition=0`、`emmc_write_count=0`** 前提下直接拉起 FX6 `6.01` `appFw.so`；
> 3. **可逆 SD 卡双启动逃生门（`r28a` / `r28b` / `r28c` 三态闭环，全部 `emmc_write_count=0`、`crashes=0`）**：
>    - **`r28a`（`sd_escape_absent_stock_fx3`）**：`/mnt/sd/FX6_STAGEB_BOOT.MANIFEST` 缺失 -> `/init` 早期门控在 `47 us`（`verify_ms=0`）内返回 `FX6_R28_SD_GATE_RC=10`，立即以 `sd_dualboot_mode="STOCK_FX3_BYPASS"`、`stageb_loaded=0` 跳过 Stage-B 干净退回原厂 FX3 路径；
>    - **`r28b`（`sd_trigger_valid_jiritsu_and_stageb_big6`）**：有效 SHA-256 SD 触发包存在 -> `1.21 ms`（`verify_us=1210`）通过 `5/5` 信任根校验（`FX6_R28_SD_GATE_RC=0`），通过全部 **`13/13` Stage-B SHA-256** 锁定、完成 `libJit.so` 自删除探针与 Strategy-A 桥接，拉起 FX6 `6.01` `appFw.so` 渲染中文 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**：`346,686` 非零像素、`87` 唯一色、`22,793` icon blits、`17,251` glyph blits、`68` `GPE` 分配（`gpe_fb=0`）、`111` 次 `LDEC103` 硬件解码、`nop_count=0`、`crashes=0`、`emmc_write_count=0`；
>    - **`r28c`（`sd_trigger_tampered_fail_closed_fallback`）**：SD manifest 首字节被篡改 `1 B`（`'4' -> '1'`）-> SHA-256 校验器在 **`0.669 ms`（`verify_ms=0`, `< 50 ms` 预算）** 内快速拒绝（`FX6_R28_SD_GATE_RC=11`, `reason=sha256_mismatch`, `failed_path=/mnt/sd/FX6_STAGEB_BOOT.CFG`），以 `sd_dualboot_mode="FAIL_CLOSED_STOCK_FX3_FALLBACK"`、`tamper_rejected=1`、`stageb_loaded=0`、`emmc_write_count=0` 安全回退原厂 FX3。

---

## 1. 三态实跑总览（`r28a` / `r28b` / `r28c`）

| 实跑场景 | Run ID | SD 清单状态 | `sd_dualboot_mode` | `verify_us` (`< 50 ms`) | `stageb_loaded` | `libJit` 自删除 & `528B` CRC32 | Strategy-A `nflasha20->30` + `tmpfs` | Stage-B SHA-256 | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | ---: | :---: | :---: | :---: | :---: | ---: | :---: | ---: | --- |
| **28A: 拔卡 / 缺省回退原厂 FX3** | `r28a-sd-escape-absent-stock-fx3` | `absent` | `STOCK_FX3_BYPASS` (`rc=10`) | **`47 us`** (`0 ms`) | `0` | N/A（未加载 Stage-B） | N/A | N/A | 跳过（Stock FX3） | **`0`** / **`0`** / **`0`** | `5.15s` | — |
| **28B: 合法 SD 触发 + `libJit` + Strategy-A + Big-6** | `r28b-sd-trigger-valid-jiritsu-stageb-big6` | `valid` (`5/5`) | `STAGEB_SD_AUTHENTICATED` (`rc=0`) | **`1,210 us`** (`1 ms`) | `1` | **`1` (`ENOENT`, `0x29f1a341`)** | **`1` (`tmpfs`, `OPE/00/01`)** | **`13/13`** | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `71.61s` | [`r28b-sd-trigger-valid-jiritsu-stageb-big6-composited.png`](assets/r28b-sd-trigger-valid-jiritsu-stageb-big6-composited.png) |
| **28C: 1B 篡改 Fail-Closed 回退** | `r28c-sd-trigger-tampered-fail-closed-fallback` | `tampered` (`1B` 破坏) | `FAIL_CLOSED_STOCK_FX3_FALLBACK` (`rc=11`) | **`669 us`** (`0 ms`) | `0` | N/A（门控提前拦截） | N/A | N/A | 跳过（Fail-Closed FX3） | **`0`** / **`0`** / **`0`** | `4.47s` | — |

---

## 2. 关键真机级机制实证详情

### 2.1 Stage-288 硬化 `libJit.so` 自删除只读探针（`ld-2.25.so` `dlopen`/`dlclose`）
- **ELF64 AArch64 页面对齐**：`zig cc -target aarch64-linux-gnu.2.17 -shared -fPIC -nostdlib -Wl,-z,max-page-size=0x10000 -Wl,-z,common-page-size=0x10000 -Wl,--hash-style=sysv`，产出 `10,032 B` `ET_DYN`（`e_machine=183`），`3` 个 `PT_LOAD` 段全部严格对齐 `0x10000`（`64 KiB`）。
- **实时 `dlopen` 遥测**：
  ```text
  FX6_R28_JIRITSU_PROBE dlopen_ok=1 dlclose_rc=0 jit_self_unlinked=1 unlink_errno=2
    sector0_pkt_bytes=528 sector0_hdr=FX3S0OK sector0_len=512 sector0_crc32=0x29f1a341
    sector0_crc_ok=1 sector0_magic=8246 sector0_ver=2.00 sector0_parts=30
    p1_start=0x80 p1_size=0xbf80 p30_start=0x346000 p30_size=0x18000 emmc_write_count=0 probe_ok=1
  ```
- **安全边界**：`libJit.so` 仅通过 `O_RDONLY | O_NOFOLLOW` 访问 `/dev/pnflasha0`，`read != 512` 或魔数/版本/分区数不匹配时立即返回，不写任何半包文件；仅当校验全部通过后以 `O_WRONLY | O_CREAT | O_EXCL` 写出 `528 B` `/tmp/jiritsu/sector0.pkt`。

### 2.2 Strategy-A 零 Sector-0 改分区挂载桥接（`U4` 活体证明）
- **FX3 Sector-0 实证事实**：真实 FX3 `partinf.conf`（`30` 分区，`magic="8246"`, `ver="2.00"`）中 `p20=(0, 0)`、`p21=(0, 0)` 均为空槽，而 `p30=(0x346000, 0x18000)` 为 `48 MiB` LUT 分区。
- **Strategy-A 桥接遥测**：
  ```text
  FX6_R28_STRATEGY_A_BRIDGE nflasha20_link=/dev/nflasha30 nflasha30_link=/dev/cnflasha30
    opelog_fstype=tmpfs tmpfs_mounted=1 opelog_ope=1 opelog_00=1 opelog_01=1
    sector0_repartition=0 emmc_write_count=0 strategy_a_bridge_ok=1
  ```
- **结论**：无需改动物理 eMMC 的任何分区表字节（`sector0_repartition=0`, `emmc_write_count=0`），FX6 `6.01` `appFw.so` 即可完整启动、解码 UXC 图标与简体中文字形并渲染 Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`；注：FX6 `6.01` 实测 Big-6 Home 原生 screen id 为 `0x0a`）。

### 2.3 可逆 SD 卡双启动逃生门（`STOCK_FX3_BYPASS` vs `STAGEB_SD_AUTHENTICATED` vs `FAIL_CLOSED_STOCK_FX3_FALLBACK`）
- `/init` 在 `FX3_DEVTMPFS_RC` 挂载设备树后第一时间执行 `/usr/bin/fx6-stage-a-verify --sd-gate`：
  - **拔出 SD 卡 / 清单缺失 (`r28a`)**：`47 us` 内返回 `rc=10`，零 Stage-B 加载，干净走原厂 FX3 路径；
  - **有效 SD 卡与 `5/5` SHA-256 信任根 (`r28b`)**：`1.21 ms` 内返回 `rc=0`，继而校验 `13/13` Stage-B 二进制与资产后进入 FX6 Big-6 Home；
  - **篡改 SD 卡清单 (`r28c`)**：`0.669 ms`（`< 50 ms`）内命中首行 `/mnt/sd/FX6_STAGEB_BOOT.CFG` SHA-256 不一致并返回 `rc=11`，Fail-Closed 回退原厂 FX3。

---

## 3. `r28b` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r28b` Alpha (`26.50 KiB`) | `r28b` Composited (`26.82 KiB`) |
| :---: | :---: |
| ![r28b Big6 Alpha](assets/r28b-sd-trigger-valid-jiritsu-stageb-big6-alpha.png) | ![r28b Big6 Composited](assets/r28b-sd-trigger-valid-jiritsu-stageb-big6-composited.png) |

---

## 4. 复现命令与洁净室合规

```bash
# Run 28A: SD Trigger Absent -> Stock FX3 Bypass
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 28 --sd-manifest-mode absent --lang schinese --run-id r28a-sd-escape-absent-stock-fx3 \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r28-runs/r28a

# Run 28B: Valid SD Trigger -> Hardened libJit.so Probe + Strategy-A Bridge + Stage-B Big-6 Home (schinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 28 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r28b-sd-trigger-valid-jiritsu-stageb-big6 --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r28-runs/r28b \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x0013:120:5500" --key-settle-ms 5500 \
  --export-png-stem r28b-sd-trigger-valid-jiritsu-stageb-big6 \
  --export-png-dir reports/2026-11-14-round28-realhw-sd-dualboot-overlay-qemu-rehearsal/assets

# Run 28C: 1-Byte Tampered SD Manifest -> Fail-Closed Stock FX3 Fallback (< 50 ms)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 28 --sd-manifest-mode tampered --lang schinese --run-id r28c-sd-trigger-tampered-fail-closed-fallback \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r28-runs/r28c

# Dual-Mode Unit Tests & Clean Audit
PYTHONPATH=outputs/fx6-native-presenter-closure PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -v
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx6-native-presenter-closure PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -v
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部 `<SCRATCH_ROOT>/fx6-r28*` 临时目录已清理；两张 PNG 视觉凭证体积为 `26.50 KiB` 与 `26.82 KiB`（均 `< 85 KiB`）；完整结构化遥测、`13/13` Stage-B SHA-256 核验与 Sector-0 / `libJit` / SD Gate 审计见 [`summary.json`](summary.json)。
