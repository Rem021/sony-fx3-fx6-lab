# Round 29：FX3 7.02 原厂内核真机准备实跑（Part 8）— 原生 C 原子安装器（`/dev/nflasha15`）、写中故障 `.orig` 回滚、`p1` 单次 `mode*` 清除救援与实态 `libMpr` REC 参数桥接

> **日期**：2026-11-14 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **目标**：在未修改的真实 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 下，通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`, `cortex-a35`, `5120 MiB`）实机预演（`r29a` / `r29b` / `r29c`），闭环实证真机刷写前的四项核心上线护栏：
> 1. **原生 ARM64 C 原子 `/dev/nflasha15` 安装器（`r29a`）**：
>    - 硬件路径防火墙严格放行 `/dev/cnflasha15` 与 `/dev/nflasha15`、**拒绝明文 `/dev/pnflasha15`**（`pnflasha15_rejected=1`）；
>    - 在内存 `tmpfs` 暂存区 `/mnt/r29_usr` 预校验原厂 `/usr/bin/im.elf`（`40,920 B`, SHA-256 `2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772`），生成 `.orig` 备份并原子写入 SD 逃生启动器（`128 B`, SHA-256 `edb450bbafdaab11f4ceeaab925ad741bff966f0d9afc50bb0adb63eecf633a9`），随后 `MS_REMOUNT | MS_RDONLY` 并验证写入返回 `EROFS`（`ro_remounted=1`, `ro_write_blocked_erofs=1`, `atomic_install_ok=1`, `emmc_write_count=0`, `4.81 ms`）；
> 2. **实时 `libMpr` / `ParameterControl` AP→CP 6 参数桥接与 `MPR_Open -> MPR_Start -> MPR_Stop -> MPR_Close` 录制闭环（`r29a`）**：
>    - `libgrm-fbinit9.so` 动态解析真机 `/usr/lib/libmpr.so` 全部 `11/11` 核心 C++ mangled 符号（`_ZN3mpr4Init...`, `_ZN3mpr8RecStart...`, `_ZN3mpr7RecStop...`, `_ZN3mpr12RecClipClose...` 等）；
>    - 实态执行 6 项核心摄影参数翻译（`Base ISO 800->12800`, `23.98p` `24000/1001`, `180.0 deg -> 1/48s` (`20854 us`), `5600K`, `S-Log3/S-Gamut3.Cine`, `SDI/darwin-ND masked=1`, `p4_nd_clear=1`）并完成 `/tmp/r29_clip/C0001.RSV -> C0001.MXF`（`640 B`）闭环与 `SYS_getdents64` 孤儿扫描（`mpr_rec_finalized=1`, `rsv_orphan_count=0`）；
>    - 同步通过 `5/5` SD 信任根、`13/13` Stage-B SHA-256 锁定、Strategy-A 桥接与 `libJit.so` 自删除探针，拉起真实 FX6 `6.01` `appFw.so` 渲染 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**：`346,206` 非零像素、`87` 唯一色、`53` 次 `LDEC103` 硬解、`nop_count=0`、`crashes=0`、`gpe_fb=0`；
> 3. **写中注入故障原子 `.orig` 回滚（`r29b`）**：
>    - 事务窗口确定性注入 **1-bit 翻转 + 50% 短写（short-write）**，安装器实时捕获 SHA-256 不匹配（`735f8c54... != edb450bb...`）与短写异常，立即从 `.orig` 原子恢复 + `fsync` + `ro` 重挂（`EROFS` 验证），回读确认原厂 `im.elf` SHA-256 **`100%` 还原**（`atomic_rollback_verified=1`, `stock_sha256_restored=1`, `crashes=0`, `8.90 ms`）；
> 4. **`p1` 单次诊断 `mode*` 清除与回落原厂 `p3` 救援（`r29c`）**：
>    - 在真实 FX3 `7.02` 内核中挂载预设 `/setting/updater/mode6`、`p1:/dat2="91030080"`、`p1:/boot/kemco.txt`（`cfg.uart=1`, `console=ttyAMA0,460800n8`）与只读 `p3`（SHA-256 `f85ab7b7...`）-> 执行 `/mnt/r29_p1/sbin/init` 首条非注释指令 `rm -f /setting/updater/mode* && sync`，验证 `mode_files_remaining=0`、`dat2_intact=1`、`uart_port=1`、`p3_untouched=1`、`next_cold_boot_bank=p3`（`p1_rescue_ok=1`, `crashes=0`, `16.69 ms`）。

---

## 1. 三项实机预演总览（`r29a` / `r29b` / `r29c`）

| 实跑场景 | Run ID | `r29_mode` | 核心硬件/事务门禁结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **29A：`/dev/cnflasha15` 原子安装 + 实态 `libMpr` 6 参数 & `C0001.MXF` REC + Big-6** | `r29a-atomic-install-and-live-mpr-rec-big6` | `install_mpr_rec` | `atomic_install_ok=1` · `ro_remounted=1` · `pnflasha15_rejected=1` · `11/11` `libmpr.so` · `mpr_rec_finalized=1` · `rsv_orphan_count=0` | `13/13` · `sid=0x0a` (`Big-6 Home`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `71.75s` | [`r29a-atomic-install-and-live-mpr-rec-big6-composited.png`](assets/r29a-atomic-install-and-live-mpr-rec-big6-composited.png) |
| **29B：写中 1-bit + 50% 短写故障注入 `.orig` 原子回滚** | `r29b-fault-injected-midwrite-atomic-rollback` | `rollback` | `mismatch_detected=1` · `short_write_detected=1` · `short_write_rollback_ok=1` · `stock_sha256_restored=1` · `atomic_rollback_verified=1` | 早期安全门控退出（零污染） | 跳过（事务回滚后停机） | **`0`** / **`0`** / **`0`** | `5.98s` | — |
| **29C：`p1` 单次 `mode6` 清除 & `p3` 只读守护救援** | `r29c-p1-oneshot-mode-clear-and-p3-return` | `p1_rescue` | `first_line_cleared=1` · `mode_files_remaining=0` · `dat2_intact=1` (`91030080`) · `uart_port=1` · `p3_untouched=1` | 早期 `p1` 救援退出 | 跳过（救援验证后停机） | **`0`** / **`0`** / **`0`** | `5.18s` | — |

---

## 2. 关键真机级机制实证详情

### 2.1 原生 ARM64 C 原子 `/dev/nflasha15` 安装器与故障回滚（`r29a` & `r29b`）
- **设备节点白名单防火墙**：`r29_is_allowed_nflasha15_path()` 仅允许 `/dev/cnflasha15` 与 `/dev/nflasha15`，显式拦截 `/dev/pnflasha15`（`pnflasha15_rejected=1`）。
- **原子事务（`r29a`）**：
  ```text
  FX6_R29_ATOMIC_INSTALL mode=install device=/dev/cnflasha15 alias=/dev/nflasha15
    pnflasha15_rejected=1 nflasha15_accepted=1 cnflasha15_accepted=1
    stock_bytes=40920 stock_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
    orig_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
    staged_bytes=128 staged_sha256=edb450bbafdaab11f4ceeaab925ad741bff966f0d9afc50bb0adb63eecf633a9
    post_sha256=edb450bbafdaab11f4ceeaab925ad741bff966f0d9afc50bb0adb63eecf633a9
    pre_sha_match=1 orig_backup_ok=1 post_sha_match=1 ro_remounted=1 ro_write_blocked_erofs=1
    atomic_install_ok=1 emmc_write_count=0 crashes=0 verify_us=4813
  ```
- **故障注入回滚（`r29b`）**：
  ```text
  FX6_R29_ATOMIC_ROLLBACK fault_kind=bit_flip_1b_and_short_write device=/dev/cnflasha15
    pnflasha15_rejected=1 nflasha15_accepted=1 cnflasha15_accepted=1 stock_bytes=40920
    stock_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
    expected_staged_sha256=edb450bbafdaab11f4ceeaab925ad741bff966f0d9afc50bb0adb63eecf633a9
    corrupted_readback_sha256=735f8c548a8bccfc8d0d9125962a7298fa9eafc5efff9cc39f818d1bfc1e4b11
    restored_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
    mismatch_detected=1 short_write_detected=1 short_write_rollback_ok=1
    ro_remounted=1 ro_write_blocked_erofs=1 stock_sha256_restored=1 atomic_rollback_verified=1
    emmc_write_count=0 crashes=0 verify_us=8903
  ```

### 2.2 实态 `libMpr` AP→CP 6 参数翻译与录制生命周期闭环（`r29a`）
- 真实 `/usr/lib/libmpr.so` 符号动态解析 **`11/11`** 成功，6 参数翻译与录制封包遥测如下：
  ```text
  FX6_R29_MPR_PARAM_SHIM base_iso_from=800 base_iso_to=12800 fps=23.98p fps_num=24000 fps_den=1001
    shutter_angle=180.0 shutter_speed=1/48s shutter_us=20854 wb_kelvin=5600 color=S-Log3/S-Gamut3.Cine
    sdi_masked=1 darwin_nd_masked=1 p4_nd_clear=1 param_count=6 param_shim_ok=1

  FX6_R29_MPR_REC_CYCLE libmpr_syms_resolved=11 libmpr_syms_total=11
    state_open=1 state_start_rec=1 state_stop=1 state_close=1
    clip_path=/tmp/r29_clip/C0001.MXF clip_bytes=640 mpr_rec_finalized=1 rsv_orphan_count=0 emmc_write_count=0
  ```

### 2.3 `p1` 单次诊断 `mode*` 清除与回落原厂 `p3`（`r29c`）
- `/mnt/r29_p1/sbin/init` 第一条非注释命令执行 `rm -f /setting/updater/mode* && sync`，将已武装的 `/setting/updater/mode6` 清除至 `0` 个残留文件，并验证 `p1:/dat2="91030080"`、`p1:/boot/kemco.txt` (`cfg.uart=1`, `console=ttyAMA0,460800n8`) 与只读 `p3`（`EROFS` + SHA-256 不变）：
  ```text
  FX6_R29_P1_RESCUE mode_armed=mode6 mode_files_before=1 first_line_cleared=1 exec_rc=0
    mode_files_remaining=0 dat2_value=91030080 dat2_intact=1 uart_port=1 console_ttyama0_ok=1
    p3_untouched=1 p3_ro_erofs=1 p3_sha256=f85ab7b794369a04e67aa7ab962960a7cbcb367c8ae245510c431edee8040e0f
    next_cold_boot_bank=p3 emmc_write_count=0 crashes=0 p1_rescue_ok=1 verify_us=16694
  ```

---

## 3. `r29a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 27 KiB`）

| `r29a` Alpha (`26.21 KiB` / `26,842 B`) | `r29a` Composited (`26.51 KiB` / `27,147 B`) |
| :---: | :---: |
| ![r29a Big6 Alpha](assets/r29a-atomic-install-and-live-mpr-rec-big6-alpha.png) | ![r29a Big6 Composited](assets/r29a-atomic-install-and-live-mpr-rec-big6-composited.png) |

---

## 4. 复现命令与洁净室合规

```bash
# Run 29A: Atomic /dev/cnflasha15 Installer + 6-Param libMpr REC + Stage-B Big-6 Home (schinese)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 29 --r29-mode install_mpr_rec --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r29a-atomic-install-and-live-mpr-rec-big6 --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r29-runs/r29a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x0013:120:5500" --key-settle-ms 5500 \
  --export-png-stem r29a-atomic-install-and-live-mpr-rec-big6 \
  --export-png-dir reports/2026-11-14-round29-realhw-atomic-installer-mpr-rec-qemu-rehearsal/assets

# Run 29B: Fault-Injected Mid-Write Atomic .orig Rollback
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 29 --r29-mode rollback --lang schinese --run-id r29b-fault-injected-midwrite-atomic-rollback \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r29-runs/r29b

# Run 29C: p1 One-Shot mode* Clear Rescue & p3 Return Verification
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 29 --r29-mode p1_rescue --lang schinese --run-id r29c-p1-oneshot-mode-clear-and-p3-return \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r29-runs/r29c

# Dual-Mode Unit Tests & Clean Audit
PYTHONPATH=outputs/fx6-native-presenter-closure PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx6-native-presenter-closure PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部 `<SCRATCH_ROOT>/fx6-r29*` 临时构建目录已彻底删除；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 85 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
