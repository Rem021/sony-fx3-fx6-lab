# Round 33：FX3 7.02 原厂内核真机准备实跑（Part 12）— 双槽 `CFexpress Type A / SDXC V90` 断电门盖冲洗、`.RSV -> .MXF` 抢救、`BODYDATA.DAT`（`\x89UFU`）`<100 µs` 原厂旁路与五级不可变砖恢复演练

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r33a` / `r33b` / `r33c`）测得；**物理实体 FX3 相机机身尚未上电接入执行实机卡槽热插拔与板级联调**（未测物理边界见 §4）。

---

## 1. 三项实机预演总览（`r33a` / `r33b` / `r33c`）

| 实跑场景 | Run ID | `r33_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **33A：`CFexpress Type A / SDXC V90` 双槽接力、门盖 GPIO 冲洗、`.RSV -> .MXF` 抢救 + Big-6 Home** | `r33a-cfexpress-rsv-big6-schinese` | `cfexpress_rsv_big6` | Slot A `/mnt/sd` & Slot B `/mnt/sd2` 挂载保留 `PRIVATE/M4ROOT/CLIP` & `XDROOT/Clip` 用户素材（`user_clips_preserved=1`）· `600 Mbps` 准入通过 `CFexpress Type A (3200)` / `V90 (720)` 并拦截模拟 `V30 (240)`（`v30_600m_rejected=1`, `rc=-22`）· 卡槽门盖 GPIO 电容保持窗（`15 ms`）内完成 `64 KiB` FIFO 冲洗（`door_gpio_irq_ms=1`, `door_flush_ms=4`, `unflushed_bytes=0`）· `C0002.RSV (8,192 B) -> C0002.MXF (8,256 B)` 抢救与 `MEDIAPRO.XML` 更新（`rsv_salvaged=1`, `tiny_rsv_rejected=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.07s` | [`r33a-cfexpress-rsv-big6-schinese-composited.png`](assets/r33a-cfexpress-rsv-big6-schinese-composited.png) |
| **33B：Sony 官方 `BODYDATA.DAT`（`\x89UFU\r\n\x1a\n`）`<100 µs` 原厂旁路与跨机型拦截** | `r33b-bodydata-ufu-bypass` | `bodydata_ufu_bypass` | 在 guest `/mnt/sd/BODYDATA.DAT` 放置 `\x89UFU\r\n\x1a\n` 头后，原生 ARM64 `fx6-stage-a-verify` 在 **`48 µs`**（`48,000 ns < 100 µs`）内中止 Stage-B 回退原厂 FX3（`BODYDATA_UFU_STOCK_BYPASS`）· 校验通过 `ILME-FX3` (`0x91030080`) 并拦截模拟 `ILME-FX30` (`0x91030084`, `fx30_rejected=1`, `rc=-22`) · 脏态阻断 `p1` 升级（`rc=-16`, `mode_files_while_dirty=0`）直至恢复 `p15:/usr` `.orig`（`H0 == H3`, `p15_residual_files=0`, `p15_ro_erofs=1`） | `13/13` 校验（早期 UFU 旁路验证退出） | 跳过（`BODYDATA.DAT` 原厂旁路后停机） | **`0`** / **`0`** / **`0`** | `5.51s` | — |
| **33C：五级不可变砖恢复梯队预演（`EH1 47 µs` → `p15 .orig` → `p1 mode*` → `UART` → `EL3/ISP` 只读锁）** | `r33c-recovery-5tier` | `recovery_5tier` | Live ARM64 内核 5/5 恢复梯队全通过：`Tier 1` (`EH1` `26 µs < 47 µs`) → `Tier 2` (`p15 .orig` `H0 == H3`, `p15_ro_erofs=1`) → `Tier 3` (`p1 mode* clear`, `p3_ro_erofs=1`) → `Tier 4` (`1.8V ttyAMA0 460800` 被动只读, `uart_tx_bytes=0`, 过压 `rc=-34`, `VMC` 争用 `rc=-16`) → `Tier 5` (`mtd0ro` `EROFS errno=30`, `el3_gate_rc=-1`, `otp_gate_rc=-1`, `mtd0_gate_rc=-13`) | `13/13` 校验（早期五级恢复验证退出） | 跳过（五级不可变砖门禁验证后停机） | **`0`** / **`0`** / **`0`** | `4.86s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 双槽 `CFexpress Type A / SDXC V90` 接力、门盖冲洗与 `.RSV -> .MXF` 抢救（`r33a`）
```text
FX6_R33_CFEXPRESS_RSV_INIT slot_a_mounted=1 slot_b_mounted=1 user_clips_preserved=1
  clip_m4root_sha256_match=1 clip_xdroot_sha256_match=1 dual_slot_relay_ok=1
  admit_cfexpress_600m=1 admit_v90_600m=1 v30_600m_rejected=1 v30_reject_rc=-22
  door_flush_ok=1 door_gpio_irq_ms=1 door_flush_ms=4 cap_hold_ms=15 unflushed_bytes=0
  rsv_salvaged=1 rsv_size_bytes=8192 mxf_size_bytes=8256 mediapro_xml_updated=1
  tiny_rsv_rejected=1 mpr_elf_ok=1 sencore_elf_ok=1 emmc_write_count=0 r33_init_ok=1

FX6_R33_CFEXPRESS_RSV_BRIDGE slot_a_cfexpress=1 slot_b_sdxc_v90=1 user_clips_preserved=1
  dual_slot_relay_ok=1 admit_600mbps_ok=1 v30_600m_rejected=1 door_flush_ok=1
  unflushed_bytes=0 rsv_salvaged=1 mediapro_xml_updated=1 sencore_ok=1
  emmc_write_count=0 r33_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`。

### 2.2 Sony 官方 `BODYDATA.DAT`（`\x89UFU\r\n\x1a\n`）Stage-A `<100 µs` 原厂旁路与跨机型拦截（`r33b`）
```text
FX6_R33_BODYDATA_UFU_BYPASS bypass_mode=BODYDATA_UFU_STOCK_BYPASS
  bodydata_path=/mnt/sd/BODYDATA.DAT ufu_magic_ok=1 stage_b_aborted=1 stock_fx3_booted=1
  bypass_ns=48000 bypass_us=48 bypass_budget_us=100 bypass_under_100us=1
  fx3_expected_model_id=0x91030080 fx3_0x91030080_valid=1
  fx30_observed_model_id=0x91030084 fx30_rejected=1 fx30_reject_rc=-22 fx30_stage_b_aborted=1
  5l6s_brick_guard=1 p1_arm_blocked_dirty=1 p1_arm_blocked_rc=-16 mode_files_while_dirty=0
  p15_orig_h0_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
  p15_orig_h3_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
  h0_eq_h3=1 p15_residual_files=0 p15_ro_erofs=1 p1_arm_allowed_clean=1
  emmc_write_count=0 r33b_ok=1 verify_us=7554
```

### 2.3 五级不可变砖恢复梯队（`r33c`）
```text
FX6_R33_TIER_STEP tier=1 name=TIER_1_EH1_47US_SD_BYPASS eh1_budget_us=47 measured_us=26 stock_fallback=1 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 tier_ok=1
FX6_R33_TIER_STEP tier=2 name=TIER_2_P15_ORIG_RESTORE_H0_EQ_H3 h0_eq_h3=1 p15_ro_erofs=1 residual_files=0 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 tier_ok=1
FX6_R33_TIER_STEP tier=3 name=TIER_3_P1_MODE_CLEAR_LINE1 mode_before=2 mode_after=0 exec_rc=0 p3_ro_erofs=1 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 tier_ok=1
FX6_R33_TIER_STEP tier=4 name=TIER_4_UART_460800_1V8_PASSIVE_TRIAGE kernel_ok=1 uart_logic_mv=1800 uart_tx_bytes=0 ov_abort_rc=-34 vmc_abort_rc=-16 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 tier_ok=1
FX6_R33_TIER_STEP tier=5 name=TIER_5_EL3_ISP_READ_ONLY_LOCK mtd_dump_ok=1 mtd_dump_bytes=16384 mtd_rw_errno=30 el3_gate_rc=-1 otp_gate_rc=-1 mtd0_gate_rc=-13 pnflasha_gate_rc=-13 el3_payload_tx=0 spi_nor_writes=0 otp_writes=0 emmc_write_count=0 tier_ok=1
FX6_R33_5TIER_RECOVERY tiers_passed=5 tiers_total=5 t1_eh1_47us_ok=1 t2_p15_orig_h0_eq_h3_ok=1 t3_p1_mode_clear_ok=1 t4_uart_passive_triage_ok=1 t5_el3_isp_ro_lock_ok=1 uart_tx_bytes=0 otp_writes=0 el3_payload_tx=0 spi_nor_writes=0 emmc_write_count=0 r33c_ok=1 verify_us=18488
```

---

## 3. `r33a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r33a` Alpha（`26.50 KiB` / `27,132 B`） | `r33a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r33a Big6 Alpha](assets/r33a-cfexpress-rsv-big6-schinese-alpha.png) | ![r33a Big6 Composited](assets/r33a-cfexpress-rsv-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目仅能在物理 Sony ILME-FX3 相机上执行，**本次未运行**：
1. 物理相机真实插拔 `CFexpress Type A` 与 `SDXC UHS-II V90` 双卡执行 `600 Mbps` XAVC S-I 实拍跨卡接力。
2. 物理相机电池/卡槽门盖霍尔开关 GPIO 中断在掉电保持电容窗口内对真实高速缓存 FIFO 执行物理落盘并断电重启抢救 `.RSV`。
3. 物理相机通过 SD 卡或 USB 执行 Sony 官方 `Ver. 7.02 / 7.xx` `BODYDATA.DAT`（`\x89UFU\r\n\x1a\n`）固件更新包全程上电验证。

---

## 5. 复现命令与洁净室合规

```bash
# Run 33A: Dual-Slot CFexpress Type A / SDXC V90 Relay + Card-Door Flush + .RSV Salvage + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 33 --r33-mode cfexpress_rsv_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r33a-cfexpress-rsv-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r33-runs/r33a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r33a-cfexpress-rsv-big6-schinese \
  --export-png-dir reports/2026-11-15-round33-realhw-cfexpress-rsv-ufu-5tier-qemu/assets

# Run 33B: BODYDATA.DAT (\x89UFU) <100 us Stock Bypass + ILME-FX30 Rejection + p1 Update Guard
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 33 --r33-mode bodydata_ufu_bypass --lang en --run-id r33b-bodydata-ufu-bypass \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r33-runs/r33b

# Run 33C: 5-Tier Unbrickable Recovery Escalation Rehearsal
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 33 --r33-mode recovery_5tier --lang en --run-id r33c-recovery-5tier \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r33-runs/r33c

# Dual-Mode Unit Tests & Clean Audit
PYTHONPATH=outputs/fx6-native-presenter-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx6-native-presenter-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
