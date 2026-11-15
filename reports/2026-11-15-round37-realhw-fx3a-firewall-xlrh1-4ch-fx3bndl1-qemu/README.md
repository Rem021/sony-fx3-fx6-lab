# Round 37：FX3 7.02 原厂内核真机准备实跑（Part 16）— `ILME-FX3` vs `ILME-FX3A` `<50 us` Fail-Closed 防火墙、`XLR-H1` MI 热靴 `48kHz/24bit 4ch` 抢占互斥与空口 `FX3BNDL1` 序列号/AppleDouble 防护

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r37a` / `r37b` / `r37c`）测得；**物理实体 `ILME-FX3` / `ILME-FX3A` 机身、`XLR-H1` 实机 XLR 麦克风热靴以及真实 macOS Finder 写入的 ExFAT SDXC 卡跨机拔插尚未上电执行**（未测物理边界见 §4）。

---

## 1. 三项实机预演总览（`r37a` / `r37b` / `r37c`）

| 实跑场景 | Run ID | `r37_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **37A：`ILME-FX3`（`7.02`, `1.44M` LCD+NFC+IR）放行 vs `ILME-FX3A`（`2.02`, `2.36M` XGA, 无 NFC/IR）`<50 us` Fail-Closed 回退与 `CAMSET` 拦截 + Big-6 Home** | `r37a-fx3a-firewall-big6-schinese` | `fx3a_firewall_big6` | Native ARM64 Stage-A 在 **`34 us`**（`< 50 us`）拦截模拟 `ILME-FX3A`（`FAIL_CLOSED_FX3A_BRANCH_MISMATCH`, `rc=-22`, `fx3a_stageb_mounted=0`），拦截 `FX3A` `BODYDATA.DAT` & `CAMSET` 跨代导入（`rc=-79` `ELIBBAD`）；校验真机 `ILME-FX3`（`0x91030080`, `Ver. 7.02`, `1,440,000` LCD, `NFC=1`, `IR=1`）放行 `rc=0`，并拉通 `libgrm-fbinit9.so` 运行时桥接（`r37_bridge_ok=1`）渲染 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `71.64s` | [`r37a-fx3a-firewall-big6-schinese-composited.png`](assets/r37a-fx3a-firewall-big6-schinese-composited.png) |
| **37B：`XLR-H1` MI 热靴 `48kHz/24bit 4ch` LPCM（`IN1/IN2` + `IN3` -> `CH1..CH4`）vs 机身 `3.5mm` 抢占与 `S&Q` 静音** | `r37b-xlrh1-4ch-override` | `xlrh1_4ch_override` | Native ARM64 音频路由探针验证 `XLR-H1` 三档档位（`48kHz/24bit 4ch` / `24bit 2ch` / `16bit 2ch`）、`IN1->CH1, IN2->CH2, IN3L->CH3, IN3R->CH4` 及耳机监听矩阵 `CH1+3/CH2+4`（`hp_mix_left_mask=0x5`, `hp_mix_right_mask=0xa`）；验证插入机身 `3.5mm` 麦克风插孔立即锁定 MI 热靴（`mishoe_locked_by_body_35mm=1`, `mishoe_when_body35_rc=-16`, `active_source=BODY_35MM`）、拔出后恢复（`body35_removed_restored=1`）、`S&Q` 升格模式强制静音（`sq_audio_muted=1`）及升级重置保护（`48kHz_16bit_2ch`） | `13/13` 校验（早期音频路由校验退出） | 跳过（`XLR-H1` C 探针退出） | **`0`** / **`0`** / **`0`** | `5.45s` | — |
| **37C：空口 `FX3BNDL1` <-> `FX3RCPT1` 机身序列号绑定与 macOS `._*` AppleDouble / `.DS_Store` 防护 + `16/16 H0 == H3`** | `r37c-fx3bndl1-serial-appledouble` | `fx3bndl1_serial_appledouble` | 绑定本机序列号 `FX3-091030080-A001` 通过（`host_serial_bind_rc=0`）并拒绝跨机移植 SD 卡 `FX3-091030080-B999`（`transplant_reject_rc=-13`, `split_pair_reject_rc=-13` `EACCES`）；校验 macOS AppleDouble `._libJit.so`（魔数 `00 05 16 07`）非 ELF 拒载、清理 `._libJit.so` / `._FX3BNDL1.BIN` / `.DS_Store` 且不触发 `._*` `dlopen`（`dot_underscore_dlopen_attempted=0`），实测真机 `dlopen("/mnt/r37_sd_jit/libJit.so")` 成功（`dlopen_ok=1`, `dlopen_failures=0`），并完成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期序列号/AppleDouble 校验退出） | 跳过（`FX3BNDL1` C 探针退出） | **`0`** / **`0`** / **`0`** | `5.12s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `ILME-FX3` vs `ILME-FX3A` `<50 us` Fail-Closed 硬件代际防火墙与 `CAMSET` 隔离（`r37a`）
```text
FX6_R37_FX3A_FIREWALL_INIT fx3a_reject_rc=-22 fx3a_reason=FAIL_CLOSED_FX3A_BRANCH_MISMATCH
  fx3a_gate_ns=34000 fx3a_gate_us=34 fx3a_under_50us=1 fx3a_stageb_mounted=0 fx3a_fallback=FAIL_CLOSED_STOCK_FX3A
  fx3a_bodydata_reject_rc=-79 fx3a_camset_reject_rc=-79 fx3_camset_accept_rc=0
  fx3_model_id=0x91030080 fx3_fw_ver=7.02 fx3_lcd_dots=1440000 fx3_nfc=1 fx3_ir=1
  fx3_pass_rc=0 fx3_reason=PASS_ILME_FX3_702_144M appfw_present=1 emmc_write_count=0 r37_init_ok=1 verify_us=664122

FX6_R37_FX3A_FIREWALL_BRIDGE fx3a_reject_rc=-22 fx3a_camset_rc=-79 fx3_pass_rc=0
  fx3_model_id=0x91030080 fx3_lcd_dots=1440000 fx3a_rejected_ok=1 fx3a_camset_blocked_ok=1
  fx3_702_pass_ok=1 xlrh1_4ch_ok=1 body35_override_ok=1 sq_mute_ok=1 fx3bndl1_serial_ok=1
  transplant_reject_rc=-13 emmc_write_count=0 r37_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `XLR-H1` MI 热靴 `48kHz/24bit 4ch` LPCM、机身 `3.5mm` 抢占与 `S&Q` 静音（`r37b`）
```text
FX6_R37_XLRH1_4CH sample_rate_hz=48000 bit_depth=24 channels=4 ch_map=IN1_CH1,IN2_CH2,IN3L_CH3,IN3R_CH4
  monitor_matrix=CH1+3_CH2+4 hp_mix_left_mask=0x5 hp_mix_right_mask=0xa modes_supported=3
  body35_inserted_override=1 mishoe_locked_by_body_35mm=1 mishoe_when_body35_rc=-16
  active_source_on_body35=BODY_35MM body35_removed_restored=1 sq_mode_active=1 sq_audio_muted=1
  upgrade_reset_default=48kHz_16bit_2ch pre_upgrade_snapshot_saved=1 audio_scn_ok=1 shim_elf_ok=1
  emmc_write_count=0 r37b_ok=1 verify_us=731
```

### 2.3 空口 `FX3BNDL1` <-> `FX3RCPT1` 序列号绑定与 macOS `._*` AppleDouble 清洗（`r37c`）
```text
FX6_R37_FX3BNDL1_SERIAL host_serial=FX3-091030080-A001 foreign_serial=FX3-091030080-B999
  host_serial_bind_rc=0 transplant_reject_rc=-13 split_pair_reject_rc=-13 transplant_rejected=1
  bndl_magic=FX3BNDL1 rcpt_magic=FX3RCPT1 rcpt_bytes=528
  appledouble_elf_rejected=1 appledouble_stripped=2 ds_store_stripped=1
  dot_underscore_dlopen_attempted=0 dot_underscore_remaining=0 dlopen_ok=1 dlopen_failures=0
  surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0 emmc_write_count=0 r37c_ok=1 verify_us=5370
```

---

## 3. `r37a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r37a` Alpha（`26.21 KiB` / `26,842 B`） | `r37a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r37a Big6 Alpha](assets/r37a-fx3a-firewall-big6-schinese-alpha.png) | ![r37a Big6 Composited](assets/r37a-fx3a-firewall-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` / `ILME-FX3A` 相机及外接配件上执行，**本次未运行**：
1. 物理 `ILME-FX3`（`Ver. 7.02`, `1.44M` LCD + NFC + IR）与物理 `ILME-FX3A`（`Ver. 2.02`, `2.36M` XGA LCD, 无 NFC/IR）真机并排上电及实卡 `BODYDATA.DAT` / `CAMSET` 跨插验证。
2. 物理 `XLR-H1` 顶部手柄挂载至 `ILME-FX3` MI 热靴并接入两路 XLR 电容/动圈话筒（`IN1/IN2`）与 `IN3` 3.5mm 立体声话筒，实机插入机身 `3.5mm` 插头触发互斥灰显及拨盘切换 `S&Q` 模式录音静音测试。
3. 真实 macOS Finder 写入的 ExFAT SDXC 卡（产生系统级 `._*` AppleDouble 与 `.DS_Store`）在两台不同物理序列号的 `ILME-FX3` 机身上跨机插卡验证 `FX3BNDL1` <-> `FX3RCPT1` 拒载与还原。

---

## 5. 复现命令与洁净室合规

```bash
# Run 37A: ILME-FX3 vs ILME-FX3A (<50 us) Fail-Closed Firewall + CAMSET Cross-Branch Block + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 37 --r37-mode fx3a_firewall_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r37a-fx3a-firewall-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r37-runs/r37a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r37a-fx3a-firewall-big6-schinese \
  --export-png-dir reports/2026-11-15-round37-realhw-fx3a-firewall-xlrh1-4ch-fx3bndl1-qemu/assets

# Run 37B: XLR-H1 MI-Shoe 48kHz/24bit 4ch Override + Body 3.5mm Physical Lock + S&Q Mute
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 37 --r37-mode xlrh1_4ch_override --lang en --run-id r37b-xlrh1-4ch-override \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r37-runs/r37b

# Run 37C: Air-Gapped FX3BNDL1 <-> FX3RCPT1 Serial Binding & macOS AppleDouble / .DS_Store Hygiene
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 37 --r37-mode fx3bndl1_serial_appledouble --lang en --run-id r37c-fx3bndl1-serial-appledouble \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r37-runs/r37c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
