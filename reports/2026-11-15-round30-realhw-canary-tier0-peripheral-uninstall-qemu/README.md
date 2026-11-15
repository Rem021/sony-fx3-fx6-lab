# Round 30：FX3 7.02 原厂内核真机准备实跑（Part 9）— `op=0xFF` 零挂载 RAM 金丝雀、`64 KiB` 自删除 `libJit.so` 流式 Tier-0 备份、物理外设桥接（`p18:/lens RO / 5轴IBIS / XLR-H1 / HDMI-vs-SDI`）与 `H0 == H3` 无损卸载

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **目标**：在未修改的真实 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 下，通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`, `cortex-a35`, `5120 MiB`）实机预演（`r30a` / `r30b` / `r30c`），闭环实证真机上线的最后三类高危能力：
> 1. **`op=0xFF` 零挂载 RAM 金丝雀 + `64 KiB` 自删除 `libJit.so` 流式 `FX3RCPT1` Tier-0 备份与 `p6` 滑窗拉取（`r30a`）**：
>    - Stage-286 Branch-A `SET_FILE2 / GET_FILE2 op=0xFF` 纯 RAM 槽位金丝雀（`slot <= 0x11`，越界 `0x12` 返回 `-EINVAL`），回读校验 `64 B` payload `100%` 匹配（`echo_match=1`, `sha256_match=1`, `sys_mount_count=0`, `dlopen_count=0`, `emmc_write_count=0`, `378 us`）；
>    - `/tmp/jbusy` `ENOENT` 预检通过后，`SET_FILE2 op=0x00` 注入 `64 KiB`（`PT_LOAD` `p_align=0x10000`, `4` 段）自删除 `libJit.so`，经真机 `/lib/ld-2.25.so` `dlopen` 立即触发 `SYS_unlinkat` 自删（`stat` 确认 `ENOENT` `errno=2`），在 `<= 2 MiB`（`2,097,152 B <= 4 MiB`）`p6` 滑窗内将 `16` 个环回只读表面（`7,864,832 B`）流式拉取成 `4` 个 `FX3CHK1` 校验块写至 `/mnt/sd/FX3_TIER0_BACKUP.BIN` 并落盘 `528 B` `FX3RCPT1` 收据（`CRC32=0x5cf9c2db`），`p6_peak_bytes=2,097,176`，`p6_residual_bytes=0`，`emmc_write_count=0`。
> 2. **物理外设分化桥接（`p18:/lens RO` + 5 轴 IBIS 安全锁止 + MI-Shoe `XLR-H1` 4ch LPCM + 非阻塞 `12G-SDI`/BNC 屏蔽与 HDMI Type-A）+ 真机 FX6 `appFw.so` Big-6 渲染（`r30b`）**：
>    - 环回 `/dev/nflasha18`（真实 `262,592 B` / `57` 镜头条目 `VX8900` `LENSFILE.BIN`）以 `MS_RDONLY | MS_NOATIME` 挂载至 `/lens`，`fx6-stage-a-verify` 与 `libgrm-fbinit9.so` 均实测写入触发 `EROFS`（`p18_write_erofs=1`, `p18_ro_erofs=1`），E-Mount 焦距/光圈/对焦距离查询正常（`emount_query_ok=1`）；
>    - 5 轴 IBIS 音圈安全停驻（`ibis_axes=5`, `ibis_coil_parked=1`, `ibis_coil_unparked_fault=0`）、MI-Shoe `XLR-H1` 4ch 24-bit 48kHz LPCM 路由就绪（`audio_scn_ok=1`, `audio_ch_active=4`, `phantom_timeout_ms=0`）、`12G-SDI` / `mew.bin` / `BNC TC-OUT` 非阻塞屏蔽（`mew_absent=1`, `sdi_hang_ms=0`, `hdmi_type_a_active=1`, `periph_bridge_ok=1`）；
>    - 同步通过 `13/13` Stage-B SHA-256 锁定，真机 `appFw.so` 渲染 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**：`346,206` 非零像素 / `87` 唯一色 / `112` 次 `LDEC103` 硬解 / `nop_count=0` / `gpe_fb=0` / `crashes=0` / `emmc_write_count=0`。
> 3. **负向 `/tmp/jbusy` `0x10000011` 零写入中止 + 环回 `H0 == H3` 全表无损卸载（`r30c`）**：
>    - 存在 `/tmp/jbusy` 时 `SET_FILE2` 立即返回 `0x10000011`（`libjit_bytes_written=0`, `dlopen_calls=0`, `libjit_enoent=1`, `abort_ok=1`, `1,190 us`）；
>    - 完整执行 `H0（原厂 /usr + 16 表面）-> H1（Stage-B 原子安装）-> H2（双系统激活，其余 15 表面未触碰）-> H3（原子恢复原厂 + 清理所有 Stage-B 文件 + ro 重挂 EROFS）`：全部 `16/16` 表面字节级匹配 `SHA256(H3) == SHA256(H0)`（`im.elf` 同为 `2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772`，`residual_stage_b_files=0`, `h0_eq_h3=1`, `uninstall_ok=1`）。

---

## 1. 三项实机预演总览（`r30a` / `r30b` / `r30c`）

| 实跑场景 | Run ID | `r30_mode` | 核心硬件/事务门禁结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **30A：`op=0xFF` 零挂载 RAM 金丝雀 + `64 KiB` 自删除 `libJit.so` 流式 Tier-0 备份** | `r30a-canary-tier0` | `canary_tier0` | `canary_ok=1` (`sys_mount=0`, `dlopen=0`) · `elf_pt_load_64k=1` · `jit_self_unlinked=1` · `528 B FX3RCPT1` (`CRC32=0x5cf9c2db`) · `16` 表面 / `7,864,832 B` / `4` 块 `FX3CHK1` · `p6_residual_bytes=0` | 早期 Tier-0 验证退出 | 跳过（纯 RAM/SD 演练后停机） | **`0`** / **`0`** / **`0`** | `6.73s` | — |
| **30B：`p18:/lens RO` + 5 轴 IBIS + `XLR-H1` 4ch + `SDI/BNC` 屏蔽 & Big-6** | `r30b-peripheral-big6-schinese` | `peripheral_big6` | `p18_ro_mounted=1` · `p18_write_erofs=1` · `p18_ro_erofs=1` · `VX8900` (`57` 条目) · `ibis_coil_unparked_fault=0` · `audio_ch_active=4` · `sdi_hang_ms=0` · `hdmi_type_a_active=1` | `13/13` · `sid=0x0a` (`Big-6 Home`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.47s` | [`r30b-peripheral-big6-schinese-composited.png`](assets/r30b-peripheral-big6-schinese-composited.png) |
| **30C：`/tmp/jbusy` `0x10000011` 零写入中止 + `H0 == H3` 干净卸载** | `r30c-jbusy-uninstall` | `jbusy_uninstall` | `set_file2_rc=0x10000011` · `libjit_bytes_written=0` · `dlopen_calls=0` · `h2_dualboot_active=1` · `h3_surfaces_matched=16/16` · `h0_eq_h3=1` · `residual_stage_b_files=0` | 早期干净卸载退出 | 跳过（卸载校验后停机） | **`0`** / **`0`** / **`0`** | `5.04s` | — |

---

## 2. 关键真机机制实证详情

### 2.1 Stage-286 `op=0xFF` 零挂载 RAM 金丝雀与 `64 KiB` 流式 Tier-0 备份（`r30a`）
```text
FX6_R30_RAM_CANARY op=0xff selector=0xff slot=0x11 max_slot=0x11 payload_bytes=64
  echo_match=1 sha256_match=1 slot_bound_enforced=1 sys_mount_count=0 dlopen_count=0
  emmc_write_count=0 canary_ok=1 verify_us=378

FX6_R30_TIER0_BACKUP dlopen_ok=1 dlclose_rc=0 jit_self_unlinked=1 unlink_errno=2
  elf_pt_load_64k=1 pt_load_cnt=4 jbusy_enoent=1 src_ro_erofs=1
  rcpt_path=/mnt/sd/FX3RCPT1.rcpt rcpt_bytes=528 rcpt_hdr=FX3RCPT1 rcpt_len=512
  rcpt_crc32=0x5cf9c2db rcpt_crc_ok=1 surfaces_backed_up=16 total_backup_bytes=7864832
  chunk_max_bytes=2097152 chunks_pulled=4 chk1_hdr=FX3CHK1 chk1_crc_ok=1
  stream_sha_match=1 p6_peak_bytes=2097176 p6_residual_bytes=0 p6_residual_files=0
  emmc_write_count=0 tier0_ok=1 verify_us=466746
```

### 2.2 物理外设分化安全桥接（`r30b`）
```text
FX6_R30_PERIPHERAL_INIT p18_device=/dev/nflasha18 p18_loop=/dev/loop0 p18_mount=/lens
  p18_fstype=vfat p18_ro_mounted=1 p18_write_erofs=1 lensfile_bytes=262592
  lens_entries=57 lens_tag=VX8900 focal_mm=50 iris_f10=14 focus_dist_mm=1250
  emount_query_ok=1 ibis_axes=5 ibis_coil_parked=1 ibis_coil_unparked_fault=0
  audio_scn_present=1 audio_ch_active=4 audio_bit_depth=24 audio_sample_rate_hz=48000
  phantom_timeout_ms=0 sdi_masked=1 mew_bin_blocked=1 bnc_tc_masked=1
  sdi_hang_ms=0 hdmi_type_a_active=1 emmc_write_count=0 periph_bridge_ok=1

FX6_R30_PERIPHERAL_BRIDGE p18_ro_erofs=1 emount_lens_entries=57 emount_lens_tag=VX8900
  focal_mm=50 iris_f10=14 focus_dist_mm=1250 ibis_axes=5 ibis_coil_parked=1
  ibis_coil_unparked_fault=0 audio_scn_ok=1 audio_ch_active=4 audio_bit_depth=24
  audio_sample_rate_hz=48000 phantom_timeout_ms=0 sdi_masked=1 mew_bin_blocked=1
  mew_absent=1 bnc_tc_masked=1 sdi_hang_ms=0 hdmi_type_a_active=1
  emmc_write_count=0 periph_bridge_ok=1
```

### 2.3 `/tmp/jbusy` 负向保护与 `H0 -> H1 -> H2 -> H3` 干净卸载（`r30c`）
```text
FX6_R30_JBUSY_ABORT jbusy_exists=1 set_file2_rc=0x10000011 libjit_bytes_written=0
  dlopen_calls=0 libjit_enoent=1 emmc_write_count=0 abort_ok=1 verify_us=1190

FX6_R30_H0_H3_UNINSTALL
  h0_im_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
  h1_im_sha256=edb450bbafdaab11f4ceeaab925ad741bff966f0d9afc50bb0adb63eecf633a9
  h3_im_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
  h2_dualboot_active=1 h2_untouched_surfaces=15 h3_surfaces_matched=16
  h3_surfaces_total=16 h0_eq_h3=1 residual_stage_b_files=0 ro_remounted=1
  ro_write_blocked_erofs=1 emmc_write_count=0 uninstall_ok=1 verify_us=357012
```

---

## 3. `r30b` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r30b` Alpha (`26.21 KiB` / `26,842 B`) | `r30b` Composited (`26.51 KiB` / `27,147 B`) |
| :---: | :---: |
| ![r30b Big6 Alpha](assets/r30b-peripheral-big6-schinese-alpha.png) | ![r30b Big6 Composited](assets/r30b-peripheral-big6-schinese-composited.png) |

---

## 4. 复现命令与洁净室合规

```bash
# Run 30A: Stage-286 op=0xFF Zero-Mount RAM Canary + 64KiB Self-Unlinking libJit.so Streaming Tier-0 Backup
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 30 --r30-mode canary_tier0 --lang en --run-id r30a-canary-tier0 \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r30-runs/r30a

# Run 30B: Physical Peripheral Bridge (p18:/lens RO, 5-axis IBIS, XLR-H1 4ch, SDI/BNC masked) + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 30 --r30-mode peripheral_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r30b-peripheral-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r30-runs/r30b \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x0013:120:5500" --key-settle-ms 5500 \
  --export-png-stem r30b-peripheral-big6-schinese \
  --export-png-dir reports/2026-11-15-round30-realhw-canary-tier0-peripheral-uninstall-qemu/assets

# Run 30C: Negative /tmp/jbusy 0x10000011 Zero-Write Abort + H0 == H3 Clean Uninstall
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 30 --r30-mode jbusy_uninstall --lang en --run-id r30c-jbusy-uninstall \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r30-runs/r30c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部 `<SCRATCH_ROOT>/fx6-r30*` 临时构建目录已彻底删除；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
