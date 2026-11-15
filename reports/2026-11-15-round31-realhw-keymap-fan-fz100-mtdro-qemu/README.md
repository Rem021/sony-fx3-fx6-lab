# Round 31：FX3 7.02 原厂内核真机准备实跑（Part 10）— FX3 机身物理按键映射（`MODE->Big-6 / DISP->Status / Custom 1..6 / T-W 变焦`）、3x Tally LEDs、`Off-in-Rec` 风扇热覆盖、`NP-FZ100`/USB-PD 曲线与双层 `pnflasha/mtd0ro` 防火墙

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **目标**：在未修改的真实 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 下，通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`, `cortex-a35`, `5120 MiB`）实机预演（`r31a` / `r31b` / `r31c`），原生 ARM64 C 闭环实证 Phase 149（按键映射 / Tally / 风扇 / 供电）与 Phase 151（`pnflasha/cnflasha/mtd0ro` 防火墙）：
> 1. **FX3 机身物理按键重映射 + 3x Tally LEDs GPIO 状态同步 + 真机 FX6 `appFw.so` Big-6 渲染（`r31a`）**：
>    - 实机注入物理按键码 `0x7028`（`UIBIZ_KEY_TACT_MODE`），由 `libgrm-fbinit9.so` 动态转译为 `FX3_MODE_TO_BIG6 -> 0x718c`（`Big-6 Home`）；同时在 `fx6-stage-a-verify` 与实时 `appFw.so + 0x2245a10`（1,115 项 `<infra_key, app_key>` 映射表）中核验 `MODE->Big-6 (0x7028/0x718c)`、`DISP->Status Check (0x01fb->0x7052->0x0049)`、`EVENT_INPUT_KEY_TACT_CUSTOM1..6 (0x7046..0x704b)`、`UIBIZ_SLIKEY_ZOOM`（`0x01d1` + `0x7151/0x7152`，无 `UIBIZ_SLIKEY_ZOOM_HANDLE` `0x00df` 错配故障，`zoom_handle_fault=0`）与 `MENU+SHUTTER+POWER` 逃生热键保留（`escape_hatch_preserved=1`）；
>    - 同步验证 `Front / Top / Rear` 三颗硬件 Tally LED（`REC_LAMP_ALL_LIGHTS_UP` on `REC` / `REC_LAMP_ALL_LIGHTS_OUT` on Standby，`Green/Yellow` 保持 `OSD-only`，`gpio_mismatch_count=0`，`tally_gpio_ok=1`）；
>    - 同步通过 `13/13` Stage-B SHA-256 锁定，真机 `appFw.so` 渲染 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**：`346,686` 非零像素 / `87` 唯一色 / `110` 次 `LDEC103` 硬解 / `nop_count=0` / `gpe_fb=0` / `crashes=0` / `emmc_write_count=0`。
> 2. **主动散热风扇 `Off-in-Rec` 高温强制覆盖与 `NP-FZ100` (`7.2V`) / `USB-PD` (`9V/3A`) 优雅 `EncWfiStop` 掉电封尾（`r31b`）**：
>    - `/usr/lib/libfan.so` 与 `/usr/lib/libsencore.so` 符号就绪（`libfan_sym_ok=1`, `sencore_fan_ok=1`），`Fan Control = Off in Rec`（屏蔽危险的 `ALWAYS_OFF` `always_off_blocked=1`）在常态 `42 °C` 保持静音 `0 RPM / 0% PWM`（`fan_off_in_rec_silent=1`），注入 `T_cmos = 68 °C`（`>= 65 °C` 硬件覆盖阈值）立即强制拉满 `100% PWM / 4,800 RPM`（`fan_emergency_override_rpm=4800`, `cmos_thermal_damage_prevented=1`, `emmc_write_count=0`, `5,058 us`）；
>    - 将原厂 `NP-FZ100`（`7,200 mV`, `84%`）与 `USB-PD`（`9,000 mV / 3,000 mA = 27 W`）遥测转换至 FX6 HUD 状态，实现零误报（`false_19v5_dcin_alarm=0`）；并在压降演练 `7.2V -> 6.3V`（`<= 6,350 mV` near-end 阈值）时触发双解析 `libmpr.so` `EncWfiStop`（`encwfistop_syms_resolved=2`），完成 `C0001.RSV -> C0001.MXF`（`640 B`）封尾（`mxf_finalized=1`, `rsv_orphan_count=0`, `emmc_write_count=0`, `18,152 us`）。
> 3. **双层 `/dev/pnflasha15` 密文 vs `/dev/cnflasha15` 解密逻辑层与 `/dev/mtd0ro` SPI NOR 只读防火墙演练（`r31c`）**：
>    - 检测 `0xEF53`（`@ 0x438`）`ext2` 逻辑头（`ext2_magic_detected=1`），企图将 `/dev/cnflasha15` 逻辑镜像写入原始 SPACC 密文目标 `/dev/pnflasha15`，或使用不匹配的 `camera_cid_sha256` 恢复时，被防火墙硬拦截且 `0 B` 写入（`cross_domain_rejected=1`, `cid_mismatch_rejected=1`, `bytes_written=0`, `pnflasha_sha_intact=1`）；
>    - 打开可写 `/dev/mtd0`（`-EACCES`）及对 `MS_RDONLY` 保护的 `/dev/mtd0ro` 发起 `O_RDWR`（实测 FX3 `7.02` 内核 VFS 返回 `errno=30 EROFS`）均被硬拦截（`mtd_wr_dev_rejected=1`, `mtdro_ordwr_rejected=1`, `mtd_rw_rejected=1`）；仅允许 `O_RDONLY /dev/mtd0ro` 只读校验转储信封（`mtdro_ro_dump_ok=1`, `16,384 B`, `spi_nor_write_count=0`, `emmc_write_count=0`, `3,593 us`）。

---

## 1. 三项实机预演总览（`r31a` / `r31b` / `r31c`）

| 实跑场景 | Run ID | `r31_mode` | 核心硬件/安全门禁结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **31A：FX3 物理按键映射 + 3x Tally LEDs + Big-6** | `r31a-keymap-tally-big6-schinese` | `keymap_big6` | `FX3_MODE_TO_BIG6 (0x7028->0x718c)` · `DISP (0x01fb->0x7052)` · `Custom 1..6 (6/6)` · `zoom_handle_fault=0` · `escape_hatch_preserved=1` · `tally_front/top/rear=1` (`gpio_mismatch=0`) | `13/13` · `sid=0x0a` (`Big-6 Home`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.03s` | [`r31a-keymap-tally-big6-schinese-composited.png`](assets/r31a-keymap-tally-big6-schinese-composited.png) |
| **31B：风扇 `Off-in-Rec` 热覆盖 + `NP-FZ100`/USB-PD `EncWfiStop`** | `r31b-fan-off-in-rec-fz100-usbpd` | `fan_fz100_power` | `42°C -> 0 RPM` · `68°C -> 4800 RPM (100% PWM)` · `cmos_thermal_damage_prevented=1` · `7.2V+9V/3A` `false_19v5_dcin_alarm=0` · `6.3V EncWfiStop -> C0001.MXF` (`rsv_orphan_count=0`) | 早期风扇与供电验证退出 | 跳过（风扇/电池与 `EncWfiStop` 演练后停机） | **`0`** / **`0`** / **`0`** | `5.91s` | — |
| **31C：`pnflasha/cnflasha/mtd0ro` 双层与 SPI NOR 防火墙** | `r31c-dual-layer-pnflasha-mtdro-firewall` | `mtdro_firewall` | `ext2 0xef53` 跨层硬拒 (`cross_domain_rejected=1`, `cid_mismatch_rejected=1`, `bytes_written=0`) · `/dev/mtd0` & `O_RDWR mtd0ro` (`EROFS=30`) 硬拒 (`mtd_rw_rejected=1`) · `O_RDONLY` 转储 (`16,384 B`, `spi_nor_write_count=0`) | 早期双层与 MTDRO 防火墙验证退出 | 跳过（SPACC/MTDRO 防火墙演练后停机） | **`0`** / **`0`** / **`0`** | `6.35s` | — |

---

## 2. 关键真机机制实证详情

### 2.1 FX3 机身物理按键重映射与 3x Tally LEDs（`r31a`）
```text
FX3_PHY_KEY_MAP source=key_seq phy=0x7028 infra=0x718c name=FX3_MODE_TO_BIG6 pipeline=0x007a804c->0x005503e0

FX6_R31_KEYMAP_TALLY_INIT sencore_tally_ok=1 appfw_elf_ok=1 mode_to_big6_ok=1 disp_to_status_ok=1
  custom_keys_bound=6 zoom_rocker_ok=1 zoom_handle_fault=0 escape_hatch_preserved=1
  tally_front=1 tally_top=1 tally_rear=1 osd_only_tally=1 gpio_mismatch_count=0
  tally_gpio_state_ok=1 emmc_write_count=0 r31_keymap_tally_ok=1 verify_us=609408

FX6_R31_KEYMAP_TALLY_BRIDGE mode_to_big6_ok=1 disp_to_status_ok=1 custom_keys_bound=6
  zoom_rocker_ok=1 zoom_handle_fault=0 escape_hatch_preserved=1 keymap_codebook_ok=1
  tally_front=1 tally_top=1 tally_rear=1 rec_lamp_policy=REC_LAMP_ALL_LIGHTS_UP
  standby_lamp_policy=REC_LAMP_ALL_LIGHTS_OUT osd_only_tally=1 gpio_mismatch_count=0
  tally_gpio_ok=1 fan_mode=OFF_IN_REC fan_override_threshold_c=65 false_19v5_dcin_alarm=0
  emmc_write_count=0 r31_bridge_ok=1
```

### 2.2 主动风扇 `Off-in-Rec` 热保护覆盖与 `NP-FZ100` / `USB-PD` 曲线（`r31b`）
```text
FX6_R31_FAN_THERMAL libfan_sym_ok=1 sencore_fan_ok=1 fan_mode=OFF_IN_REC always_off_blocked=1
  normal_temp_c=42 normal_rpm=0 normal_pwm_pct=0 fan_off_in_rec_silent=1
  inject_temp_c=68 threshold_prehigh_c=58 threshold_emergency_c=65 threshold_critical_c=72
  pwm_override_pct=100 fan_emergency_override_rpm=4800 fan_override_engaged=1
  cmos_thermal_damage_prevented=1 emmc_write_count=0 fan_probe_ok=1 verify_us=5058

FX6_R31_FZ100_POWER encwfistop_syms_resolved=2 sencore_usbpd_ok=1 fz100_nominal_mv=7200
  fz100_soc_pct=84 usb_pd_mv=9000 usb_pd_ma=3000 usb_pd_mw=27000 false_19v5_dcin_alarm=0
  sag_start_mv=7200 sag_end_mv=6300 threshold_near_end_mv=6350 threshold_stop_mv=6100
  encwfistop_triggered=1 clip_path=/tmp/r31_power/C0001.MXF clip_bytes=640 mxf_finalized=1
  rsv_orphan_count=0 emmc_write_count=0 power_probe_ok=1 verify_us=18152
```

### 2.3 双层 `pnflasha15/cnflasha15` 与只读 `/dev/mtd0ro` 防火墙（`r31c`）
```text
FX6_R31_MTDRO_FIREWALL ext2_magic=0xef53 ext2_magic_detected=1
  cross_domain_rejected=1 cid_mismatch_rejected=1 bytes_written=0 pnflasha_sha_intact=1
  mtd_wr_dev_rejected=1 mtdro_ordwr_rejected=1 mtd_rw_rejected=1 mtdro_ordwr_errno=30
  mtdro_ro_dump_ok=1 mtdro_dump_bytes=16384
  mtdro_dump_sha256=0269b131e1a691c5f5783a4203112f7fc6e21cd023cdb0ae9fe60ff617b6d5d1
  spi_nor_write_count=0 emmc_write_count=0 firewall_ok=1 verify_us=3593
```

---

## 3. `r31a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r31a` Alpha (`26.50 KiB` / `27,132 B`) | `r31a` Composited (`26.82 KiB` / `27,467 B`) |
| :---: | :---: |
| ![r31a Big6 Alpha](assets/r31a-keymap-tally-big6-schinese-alpha.png) | ![r31a Big6 Composited](assets/r31a-keymap-tally-big6-schinese-composited.png) |

---

## 4. 复现命令与洁净室合规

```bash
# Run 31A: FX3 Body Keymap (0x7028 MODE->Big-6 Home) + 3x Tally LEDs + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 31 --r31-mode keymap_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r31a-keymap-tally-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r31-runs/r31a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r31a-keymap-tally-big6-schinese \
  --export-png-dir reports/2026-11-15-round31-realhw-keymap-fan-fz100-mtdro-qemu/assets

# Run 31B: Fan Off-in-Rec Thermal Emergency Override + NP-FZ100 (7.2V) & USB-PD (9V/3A) EncWfiStop
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 31 --r31-mode fan_fz100_power --lang en --run-id r31b-fan-off-in-rec-fz100-usbpd \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r31-runs/r31b

# Run 31C: Dual-Layer pnflasha15/cnflasha15 & Read-Only /dev/mtd0ro Firewall Drill
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 31 --r31-mode mtdro_firewall --lang en --run-id r31c-dual-layer-pnflasha-mtdro-firewall \
  --duration 25 --run-dir <SCRATCH_ROOT>/fx6-r31-runs/r31c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部 `<SCRATCH_ROOT>/fx6-r31*` 临时构建目录已彻底删除；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
