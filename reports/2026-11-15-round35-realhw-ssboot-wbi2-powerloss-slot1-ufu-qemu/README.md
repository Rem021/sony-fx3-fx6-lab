# Round 35：FX3 7.02 原厂内核真机准备实跑（Part 14）— Sony SCEL `ssboot`/`WBI2`（`nflasha5`）冷启动锁定、100 周期掉电 `.RSV -> .MXF` 抢救与 Slot-1 `BODYDATA.DAT`（`>=2.04`）/ C2PA `<=100` 上限

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r35a` / `r35b` / `r35c`）测得；**物理实体 FX3 相机机身、SCEL `ssboot` 引导休眠硬件断点、实体 `NP-FZ100` `6.3V` 掉电台架与实体机身 Slot-1 UFU 刷机测试尚未上电执行**（未测物理边界见 §4）。

---

## 1. 三项实机预演总览（`r35a` / `r35b` / `r35c`）

| 实跑场景 | Run ID | `r35_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **35A：SCEL `ssboot` / `WBI2`（`nflasha5`）冷启动锁、`BLKROSET=1`（`EROFS`）、`disk` 休眠拦截与 Big-6 Home** | `r35a-ssboot-wbi2-big6-schinese` | `ssboot_wbi2_big6` | 校验 `nflasha5` `WBI2\x00\x00\x00\x00`（`57 42 49 32 00 00 00 00`, `1,399` sections）+ Tier-0 `FX3RCPT1`（`528 B`）基线摘要 · 绑定 `/dev/loop_nflasha5` & `/dev/loop_pnflasha5` `BLKROSET=1` + `MS_RDONLY` 强制 `/dev/nflasha5` & `/dev/pnflasha5` `O_RDWR` 返回 `EROFS (errno=30)`（`wbi_persistent_writes=0`）· 拦截 `PM_SUSPEND_DISK`（`/sys/power/state "disk" -> rc=-1`）与 `/proc/udm`（`rc=-30`）· `libgrm-fbinit9.so` 运行时双重校验通过（`r35_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.32s` | [`r35a-ssboot-wbi2-big6-schinese-composited.png`](assets/r35a-ssboot-wbi2-big6-schinese-composited.png) |
| **35B：100 周期原生 ARM64 Stock <-> Stage-B 模式切换、拔电池/6.3V 掉电 `.RSV -> .MXF` 抢救与 `16/16 H0 == H3`** | `r35b-powerloss-100cycle-rsv` | `powerloss_100cycle_rsv` | 验证 `/usr/lib/libmpr.so` `EncWfiStop` 真实符号 · 在 guest 内高速连续执行 **100 个生命周期闭环**：Stage-B 启动 -> 拔电池清空 `tmpfs` `/tmp` & `/etc/opelog`（`100/100`）-> `6.3V (<=6.35V)` 欠压遗留 `C0003.RSV`（`8,192 B`）-> 下次启动抢救封装为 `C0003.MXF`（`8,256 B`）并更新 `MEDIAPRO.XML`（`100/100`）-> `EH1` 退卡 `<50 us` 回归 Stock（`eh1_max_us=15`, `eh1_avg_ns=7669`, `100/100`）-> 卸载密封后 `16/16` 关键分区（含 `p5:/wbi` `WBI2` 扇区头）`H0 == H3`（`drift_bits=0`, `orig_residual_count=0`, `p15_ro_erofs=1`） | `13/13` 校验（早期 100 周期压力测试退出） | 跳过（100 周期电源故障压测后停机） | **`0`** / **`0`** / **`0`** | `37.53s` | — |
| **35C：官方 FX3 `7.02` `BODYDATA.DAT`（`>=2.04` 门槛 / Slot-1 唯一性 / `<100 us` 旁路）与 Slot-1 C2PA `<=100` 许可证上限** | `r35c-slot1-ufu-c2pa-ceiling` | `slot1_ufu_c2pa_ceiling` | 拒绝 `<= Ver. 2.02` 直升（`rc=-22`, 防止 `7L+7S` 硬件报错灯故障）并放行 `>=2.04`（`ver_204_floor_ok=1`）· 拒绝 Slot-2 更新文件（`rc=-18`）与重名 `BODYDATA (1).DAT`（`rc=-17`）· 合法 Slot-1 `/mnt/sd/BODYDATA.DAT`（`\x89UFU\r\n\x1a\n`, `0x91030080`）在 **`34 us`**（`< 100 us`）内自动旁路回原厂 Stock · Slot-1 C2PA 验证接收 `100` 张许可证（`rc=0`）并拒绝 `101` 张（`rc=-7` `E2BIG`），保持 `p12:/cert/RQ_LIC.DAT` `EROFS (errno=30)` · 封锁 `WEP/WPA1/IPsec`（`rc=-93`）仅放行 `WPA2/WPA3`（`wpa2_wpa3_enforced=1`） | `13/13` 校验（早期 UFU/C2PA 旁路回 Stock 退出） | 跳过（UFU `<100 us` 旁路回原厂 Stock 后停机） | **`0`** / **`0`** / **`0`** | `5.04s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 Sony SCEL `ssboot` / `WBI2`（`nflasha5`）冷启动锁与 `disk` 休眠拦截（`r35a`）
```text
FX6_R35_SSBOOT_WBI2_INIT wbi2_magic=WBI2 wbi2_magic_hex=5742493200000000 wbi2_magic_ok=1 wbi2_sections=1399
  fx3_rcpt1_magic=FX3RCPT1 fx3_rcpt1_bytes=528 fx3_rcpt1_ok=1
  wbi2_hdr_sha256=b2b1e7eb51627956deec33424c52fb396c9be4f10051d1e6501a817b60742890
  wbi2_part_sha256=8f947c0fc89c98f21f6374959a8618f9d29de070e7af3431ad10d05c48872a1f
  wbi2_sha256_match=1 wbi_resume_bypassed=1 cold_boot_init_verified=1
  nflasha5_blkroset=1 pnflasha5_blkroset=1 nflasha5_open_errno=30 pnflasha5_open_errno=30
  wbi_erofs_enforced=1 wbi_persistent_writes=0 pm_suspend_disk_rc=-1 proc_udm_write_rc=-30
  ssboot_disk_intercepted=1 emmc_write_count=0 r35_init_ok=1 verify_us=156644

FX6_R35_SSBOOT_WBI2_BRIDGE wbi2_magic_ok=1 nflasha5_erofs_ok=1 pnflasha5_erofs_ok=1 fx3_rcpt1_ok=1
  wbi_resume_bypassed=1 ssboot_disk_intercepted=1 wbi_persistent_writes=0 emmc_write_count=0 r35_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 100 周期 Stock <-> Stage-B、掉电 `.RSV -> .MXF` 抢救与 `16/16 H0 == H3`（`r35b`）
```text
FX6_R35_POWERLOSS_100CYCLE encwfistop_sym_ok=1 cycles_completed=100 cycles_passed=100
  rsv_salvaged_cycles=100 tmpfs_evaporated_cycles=100 eh1_under_50us_cycles=100
  eh1_avg_ns=7669 eh1_max_ns=14992 eh1_max_us=15
  brownout_mv=6300 brownout_threshold_mv=6350 rsv_clip=C0003.RSV mxf_clip=C0003.MXF mediapro_xml_ok=1
  h0_wbi_sha256=b2b1e7eb51627956deec33424c52fb396c9be4f10051d1e6501a817b60742890
  h3_wbi_sha256=b2b1e7eb51627956deec33424c52fb396c9be4f10051d1e6501a817b60742890
  wbi2_h0_eq_h3=1
  h0_im_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
  h3_im_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
  h3_surfaces_matched=16 h3_surfaces_total=16 h0_eq_h3=1 drift_bits=0
  orig_residual_count=0 p15_ro_erofs=1 emmc_write_count=0 r35b_ok=1 verify_us=32075716
```

### 2.3 Slot-1 `BODYDATA.DAT`（`>=2.04` 门槛/`<100 us` 旁路）与 C2PA `<=100` 许可证上限（`r35c`）
```text
FX6_R35_SLOT1_UFU_C2PA bodydata_path=/mnt/sd/BODYDATA.DAT bodydata_expected_bytes=811876768
  ufu_magic_ok=1 stage_b_aborted=1 stock_fx3_booted=1
  bypass_ns=34000 bypass_us=34 bypass_budget_us=100 bypass_under_100us=1
  fx3_expected_model_id=0x91030080 fx3_0x91030080_valid=1
  ver_202_rejected=1 ver_202_reject_rc=-22 led_7l_7s_prevented=1 ver_204_floor_ok=1
  slot2_rejected=1 slot2_reject_rc=-18 dup_bodydata_rejected=1 dup_bodydata_reject_rc=-17
  c2pa_100_accepted=1 c2pa_100_count=100 c2pa_100_rc=0
  c2pa_101_rejected=1 c2pa_101_count=101 c2pa_101_rc=-7
  p12_cert_erofs=1 p12_cert_errno=30
  c2pa_sha256_before=a3b46f100b34d4014ec24b3a96fb0b79380783ee37c7e30960ed42ce93246429
  c2pa_sha256_after=a3b46f100b34d4014ec24b3a96fb0b79380783ee37c7e30960ed42ce93246429
  c2pa_sha256_match=1 c2pa_cert_writes=0
  wep_rc=-93 wpa1_rc=-93 ipsec_rc=-93 wpa2_rc=0 wpa3_rc=0
  deprecated_wlan_blocked=1 wpa2_wpa3_enforced=1
  emmc_write_count=0 r35c_ok=1 verify_us=5452
```

---

## 3. `r35a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r35a` Alpha（`26.50 KiB` / `27,132 B`） | `r35a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r35a Big6 Alpha](assets/r35a-ssboot-wbi2-big6-schinese-alpha.png) | ![r35a Big6 Composited](assets/r35a-ssboot-wbi2-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony ILME-FX3 相机上执行，**本次未运行**：
1. 物理相机实体 SCEL `ssboot` 引导程序冷启动与 `nflasha5`（`WBI2`）真机 PMIC 断电挂起分支硬件验证。
2. 物理相机使用实体 `NP-FZ100` 在 `6.3V` 电压跌落下的真实 `EncWfiStop` `.RSV` 写入实体 CFexpress Type A / SDXC ExFAT 介质及多周期实体拔电池压测。
3. 物理相机通过 Slot-1 根目录放置官方 `BODYDATA.DAT` 对真实 Ver. `7.02`（`>= Ver. 2.04`）机身执行完整官方 UFU 流程及实体 C2PA / WPA3 无线认证。

---

## 5. 复现命令与洁净室合规

```bash
# Run 35A: SCEL ssboot/WBI2 Cold-Boot Lock + BLKROSET=1 (EROFS) + disk Intercept + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 35 --r35-mode ssboot_wbi2_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r35a-ssboot-wbi2-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r35-runs/r35a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r35a-ssboot-wbi2-big6-schinese \
  --export-png-dir reports/2026-11-15-round35-realhw-ssboot-wbi2-powerloss-slot1-ufu-qemu/assets

# Run 35B: 100-Cycle Stock <-> Stage-B + Mid-Recording Battery-Pull / 6.3V Brownout .RSV -> .MXF Salvage
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 35 --r35-mode powerloss_100cycle_rsv --lang en --run-id r35b-powerloss-100cycle-rsv \
  --duration 40 --run-dir <SCRATCH_ROOT>/fx6-r35-runs/r35b

# Run 35C: Official BODYDATA.DAT (>=2.04 Floor / Slot-1 Root / <100 us Bypass) & Slot-1 C2PA <=100 License Ceiling
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 35 --r35-mode slot1_ufu_c2pa_ceiling --lang en --run-id r35c-slot1-ufu-c2pa-ceiling \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r35-runs/r35c

# Dual-Mode Unit Tests & Clean Audit
PYTHONPATH=outputs/fx6-native-presenter-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx6-native-presenter-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
