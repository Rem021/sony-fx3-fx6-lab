# Round 36：FX3 7.02 原厂内核真机准备实跑（Part 15）— `MIRA_CETUS2` E 卡口 `info7/info8/info3D` + `0x02cf0232` 呼吸效应补偿、`Type-A HDMI 4264x2408` 16-bit RAW（`BRAW`/`ProRes RAW`）与 `WPA2/WPA3` 净化器

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r36a` / `r36b` / `r36c`）测得；**物理实体 FX3 相机机身 E 卡口镜头电触点抓包、物理 `Type-A HDMI 4264x2408` 对接 `Video Assist 12G` / `Atomos Ninja` 实机录制及物理 `WPA3-SAE` + `Monitor & Control 2.1.0+` 无线传输尚未上电执行**（未测物理边界见 §4）。

---

## 1. 三项实机预演总览（`r36a` / `r36b` / `r36c`）

| 实跑场景 | Run ID | `r36_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **36A：`MIRA_CETUS2` E 卡口 `info7/info8/info3D`、`((lens_id >> 14) == 3)`、`0x02cf0232` 呼吸补偿与 `p18:/lens/LENSFILE.BIN` `EROFS` + Big-6 Home** | `r36a-emount-info3d-big6-schinese` | `emount_info3d_big6` | 锁定 `p18:/lens/LENSFILE.BIN` 只读（`O_RDWR -> EROFS errno=30`，拦截 CineAlta 手动 `LENSFILE` 槽位写入 `rc=-30`）· 验证 `info7/info8/info3D` 握手与 Sony 原厂滤镜 `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)`：原厂 `0xC123` 启用 `0x02cf0232` 呼吸补偿（`crop=1085‰`），第三方 `0x4123` 与手动转接环 `0xFFFF` 门控关闭（`rc=-13`）· `libgrm-fbinit9.so` 运行时双重校验通过（`breathing_bk4_hits=2`, `r36_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.61s` | [`r36a-emount-info3d-big6-schinese-composited.png`](assets/r36a-emount-info3d-big6-schinese-composited.png) |
| **36B：`Type-A HDMI 4264 x 2408` (`60p`) 16-bit 线性 RAW（`Video Assist 12G 3.22+` `.braw` & `Atomos Ninja` `ProRes RAW`）、1.5x/1.6x 变形不烘焙与 `12G-SDI` 屏蔽** | `r36b-hdmi-4264-raw-prores-braw` | `hdmi_4264_raw_prores_braw` | 原生 ARM64 HDMI EDID/VSIF 垫片协商 `4264x2408@60p` 16-bit 线性 RAW：`BMD Video Assist 12G 3.22+`（`.braw`）通过（`va12g_braw_ok=1`, `iso_locked=1`），拒绝 `Video Assist 3G`（`rc=-95` `EOPNOTSUPP`），`Atomos Ninja` `ProRes RAW` 通过并携带 `WB=5600K / tint=-2 / iso_offset=+1EV` · `/usr/lib/libmpr.so`（`6/6` 符号）同步内录 `XAVC S-I + Proxy`，`1.5x/1.6x` 变形反挤压与 `.cube` MLUT 不烘焙至主码流（`raw_clean_master=1`）· `12G-SDI` 静默屏蔽（`sdi_raw_masked=1`, `sdi_mmio_probes=0`） | `13/13` 校验（早期 HDMI RAW 校验退出） | 跳过（HDMI RAW C 探针退出） | **`0`** / **`0`** / **`0`** | `5.72s` | — |
| **36C：FX3 `7.02` `WPA2/WPA3` 唯一净化器（拒绝 `WEP/WPA1/IPsec`）与 `Monitor & Control 2.1.0+` Focus Map 只读 `tmpfs` 桥** | `r36c-wpa2-wpa3-focusmap-bridge` | `wpa2_wpa3_focusmap_bridge` | Stage-B 网络净化器在到达 FX3 `7.02` `wpa_supplicant` 前直接拒绝 `WEP`、`WPA1-TKIP`、`IPsec`（均返回 `rc=-22` `EINVAL`，`supplicant_legacy_hits=0`）并放行 `WPA2-CCMP` / `WPA3-SAE`（`rc=0`），验证 `/usr/lib/libWlanResource.so` & `libWlanAdjust.so` 完整 · 锁定 `p2:/setting/Backup.bin` `EROFS (errno=30, backup_sha256_match=1)` 并经 `tmpfs` 零落盘串流 `12` 帧 `Monitor & Control 2.1.0+` Focus Map 深度遥测（`384 B`, `focus_map_tmpfs_ok=1`） | `13/13` 校验（早期 WPA3/FocusMap 校验退出） | 跳过（WPA3 & Focus Map 探针退出） | **`0`** / **`0`** / **`0`** | `5.10s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `MIRA_CETUS2` E 卡口 `info7/info8/info3D`、`0x02cf0232` 呼吸补偿与 `p18:/lens/LENSFILE.BIN` `EROFS`（`r36a`）
```text
FX6_R36_EMOUNT_INFO3D_INIT p18_lensfile=/mnt/r36_p18/lens/LENSFILE.BIN p18_lensfile_erofs=1 p18_lensfile_errno=30
  p18_r30_lens_erofs=1 lensfile_sha256_before=a3d05530305be9800f69c4621ddf1896b293c6fc4d9b0f7f7bcbef514bea0017
  lensfile_sha256_after=a3d05530305be9800f69c4621ddf1896b293c6fc4d9b0f7f7bcbef514bea0017 lensfile_sha256_match=1
  cinealta_lensfile_write_rc=-30 cinealta_slot_blocked=1 lensfile_writes=0
  info7_ok=1 info8_ok=1 info3d_ok=1 bkid_breathing=0x02cf0232
  sony_lens_id=0xC123 sony_0xc123_shift14_eq3=1 sony_0xc123_breathing_on=1 sony_crop_permille=1085
  thirdparty_lens_id=0x4123 thirdparty_0x4123_shift14_eq3=0 thirdparty_0x4123_gated_off=1
  manual_lens_id=0xFFFF manual_0xffff_gated_off=1 appfw_present=1 emmc_write_count=0 r36_init_ok=1 verify_us=656452

FX6_R36_EMOUNT_INFO3D_BRIDGE p18_lensfile_erofs_ok=1 lensfile_ro_ok=1
  sony_0xc123_breathing_on=1 thirdparty_0x4123_gated_off=1 manual_0xffff_gated_off=1
  bkid_02cf0232_val=0x01 sdi_mmio_probes=0 raw_clean_master=1 wpa2_wpa3_sanitizer=1 focusmap_ro_bridge=1
  emmc_write_count=0 r36_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `nop_count=0` / `gpe_fb=0` / `breathing_bk4_hits=2` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `Type-A HDMI 4264 x 2408` 16-bit 线性 RAW（`BRAW`/`ProRes RAW`）、1.5x/1.6x 非烘焙与 Masked `12G-SDI`（`r36b`）
```text
FX6_R36_HDMI_4264_RAW hdmi_port=TypeA raw_width=4264 raw_height=2408 raw_fps=60 raw_bit_depth=16
  va12g_braw_rc=0 va12g_braw_ok=1 braw_iso_locked=1
  va3g_rejected=1 va3g_reject_rc=-95
  atomos_ninja_rc=0 atomos_ninja_ok=1 prores_wb_kelvin=5600 prores_tint=-2 prores_iso_offset_ev=1 prores_wb_iso_meta_ok=1
  internal_xavc_si_proxy_ok=1 mpr_dlopen_ok=1 mpr_syms_resolved=6
  anamorphic_15x_nonbake=1 anamorphic_16x_nonbake=1 mlut_nonbake=1 raw_clean_master=1
  sdi_raw_masked=1 sdi_raw_mask_rc=-19 sdi_mmio_probes=0 emmc_write_count=0 r36b_ok=1 verify_us=24272
```

### 2.3 `WPA2/WPA3` 唯一净化器与 `Monitor & Control 2.1.0+` Focus Map 只读桥（`r36c`）
```text
FX6_R36_WPA3_FOCUSMAP wep_rc=-22 wpa1_tkip_rc=-22 ipsec_rc=-22 wpa2_ccmp_rc=0 wpa3_sae_rc=0
  legacy_wlan_rejected=1 wpa2_wpa3_accepted=1 rejected_before_supplicant=3 supplicant_legacy_hits=0 wlan_libs_ok=1
  mc_client_min_ver=2.1.0 focus_map_frames=12 focus_map_bytes=384 focus_map_tmpfs_ok=1
  backup_bin_erofs=1 backup_bin_errno=30
  backup_sha256_before=39b2e6f2b67cf7f04f5d8bf77dae4d9359dae27e179cda8adcfaa5d52ad719bb
  backup_sha256_after=39b2e6f2b67cf7f04f5d8bf77dae4d9359dae27e179cda8adcfaa5d52ad719bb
  backup_sha256_match=1 backup_writes=0 emmc_write_count=0 r36c_ok=1 verify_us=2816
```

---

## 3. `r36a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r36a` Alpha（`26.50 KiB` / `27,132 B`） | `r36a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r36a Big6 Alpha](assets/r36a-emount-info3d-big6-schinese-alpha.png) | ![r36a Big6 Composited](assets/r36a-emount-info3d-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony ILME-FX3 相机及外接录机上执行，**本次未运行**：
1. 物理相机实机 E 卡口接入 FE GM、第三方 E 卡口及无触点手动转接镜头时的真实 `info7/info8/info3D` 通讯帧采集与实拍呼吸效应裁切视场对比。
2. 物理相机 `Type-A HDMI` 输出 `4264x2408@60p` 16-bit Linear RAW 直连实体 Blackmagic Video Assist 12G HDR（`3.22+`）`.braw` 与 Atomos Ninja `ProRes RAW` 录机并同步 CFexpress Type A 内录 `XAVC S-I` 测试。
3. 物理相机在 FX3 Ver. `7.02` Wi-Fi `WPA2-CCMP` / `WPA3-SAE` 真实空口关联及平板端 `Monitor & Control 2.1.0+` Focus Map 实时传输测试。

---

## 5. 复现命令与洁净室合规

```bash
# Run 36A: MIRA_CETUS2 E-Mount info7/info8/info3D + 0x02cf0232 Breathing Comp + p18 EROFS + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 36 --r36-mode emount_info3d_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r36a-emount-info3d-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r36-runs/r36a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r36a-emount-info3d-big6-schinese \
  --export-png-dir reports/2026-11-15-round36-realhw-emount-info3d-hdmi-4264-raw-wpa3-qemu/assets

# Run 36B: Type-A HDMI 4264x2408@60p 16-bit Linear RAW (BRAW/ProRes RAW) + 1.5x/1.6x Non-Bake + Masked 12G-SDI
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 36 --r36-mode hdmi_4264_raw_prores_braw --lang en --run-id r36b-hdmi-4264-raw-prores-braw \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r36-runs/r36b

# Run 36C: WPA2/WPA3-Only Sanitizer (WEP/WPA1/IPsec Rejected) + Monitor & Control 2.1.0+ Focus Map Bridge
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 36 --r36-mode wpa2_wpa3_focusmap_bridge --lang en --run-id r36c-wpa2-wpa3-focusmap-bridge \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r36-runs/r36c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
