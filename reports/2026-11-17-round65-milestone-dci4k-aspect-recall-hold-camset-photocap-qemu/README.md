# Round 65（`65th` 轮里程碑 · Wave-51 / `R28..R65` `38/38` 实机预演轮次 · 第 `112..114` 次实跑 -> `114/114` 总实跑 · `76/76` 张 Big-6 PNG `<= 27,467 B`）：FX3 7.02 原厂内核真机准备预演 — `XAVC S-I DCI 4K`（`4096×2160` `24.00p` 重启与 `59.94p` 上限）vs Long-GOP `UHD 3840×2160` & `4264×2408` HDMI RAW、静态 `[Aspect Ratio]`（`3:2/4:3/16:9/1:1`）vs `FX6`、11 复选框 `[Reg. Custom Shoot Set]`（`Recall Custom hold 1..3`）+ 机身 `1..3` / 卡 `M1..M4` `SONY/SETTING/FX3/CAMPR` & `CAMSET` vs `FX6` `SONY/PRO/CAMERA`，以及 `[Photo Capture]` `DCI 4K` 锁定与 `Slot-1` Tier-0 保险库防火墙

> **日期**：2026-11-17 | **轮次**：**Round 65 (Wave-51 · `65th` Round Milestone · `38/38` Real-HW Rounds · `112th..114th` Live Runs -> `114/114` Total Live Runs, `76/76` PNGs `<= 27,467 B`)** | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r65a` / `r65b` / `r65c`，正式达成 **第 `65` 轮里程碑**、**`R28..R65` `38/38` 轮实机内核预演**、**第 `112..114` 次 -> `114/114` 次独立实跑**、**`76/76` 张 `< 50 KiB`（本轮 `<= 27,467 B`：`26,842 B` 与 `27,147 B`）PNG 视觉凭证**）测得；**物理实体 `ILME-FX3` 机内 `CFexpress VPG200+`/`SDXC V90+` 码流与 `24.00p` 重启、`4264×2408` 外部 HDMI RAW 实拍、静态 `[Aspect Ratio]`/`RAW` 裁剪元数据与 11 项 `[Reg. Custom Shoot Set]` 实体手感、以及回放 `[Photo Capture]` 抽帧与 `[Enlarge Image]` 实测尚未在物理真机台架上电执行**（未测物理边界见 §4）。

---

## 1. 第 65 轮 `65th` 轮里程碑 / `38/38` 实机预演（Wave-51 · `38/38` 实机轮次 / `112th..114th` -> `114/114` 次实跑 / `76/76` PNG）三项实机预演总览（`r65a` / `r65b` / `r65c`）

| 实跑场景 | Run ID | `r65_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **65A（第 112 次实跑）：Wave-51 四大支柱 — `XAVC S-I DCI 4K`（`24.00p` 重启与 `59.94p` 上限）vs Long-GOP `UHD` & `4264×2408` HDMI RAW + 快门 `Angle`、静态 `[Aspect Ratio]` vs `FX6`、11 复选框 `[Reg. Custom Shoot Set]` + `CAMPR`/`CAMSET` vs `SONY/PRO/CAMERA`、`[Photo Capture]` `DCI 4K` 锁定 + `Slot-1` `-EROFS` + Big-6 Home** | `r65a` | `dci4k_aspect_camset_photocap_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 四路支柱桥接实证：(1) 核验 **`XAVC S-I DCI 4K`**（`_f.uxc 0x7336`，`4096×2160` `17:9`，Ver. 3.00+，支持 `23.98p`/`24.00p` `240M` 与 `25p`/`29.97p`/`50p`/`59.94p` `600M`，`24.00p` 强制重启并触发 `_g.uxc 0x639b` 回放隔离；S&Q 仅限 `1..48fps`，拒绝 `100/120fps` 与 `119.88p/100p` `-22 EINVAL`），对比 **`XAVC HS 4K` / `XAVC S 4K` / `XAVC S-I 4K`** 严格限定 `3840×2160` UHD（拒绝 `DCI 4K`/`24.00p` 及沉睡 `xavc_hs_8k_24p` `-95 EOPNOTSUPP`）及外部 HDMI RAW **`4264×2408`**（强制 `Log != Off` 并锁定 `S-Log3`）+ 快门 `Angle`（`5.6..360.0 deg` / `2F..64F`）；(2) 核验静态 **`[Aspect Ratio]`**（`_f.uxc 0x757c`：`3:2` 默认 `12M` / `4:3` `11M` / `16:9` `10M` / `1:1` `8.0M`，`RAW` 保留完整 `3:2` 全像素并写入裁剪元数据，`[APS-C S35 Shooting]=On` 限制最大尺寸 `L->M`），对比无静态模式的 `FX6`（`-2 ENOENT`）；(3) 核验 11 复选框 **`[Reg. Custom Shoot Set]`**（`_f.uxc 0x7631`：`Recall Custom hold 1..3`，11 项 `BKID_APP_shoot_set_registration_*`，仅限静态 `P/A/S/M`，拒绝 Movie/`S&Q`/`iAuto`/`MR` `-16 EBUSY`，排除自拍并强制在 ISO/DRO 保持期间关闭 `[HLG Still Image]`），核验机身 `1..3` 与卡 `M1..M4` `/PRIVATE/SONY/SETTING/FX3/CAMPR%02d%c.DAT` / `CAMSET01..10.DAT`（对比 `FX6` 专属 `SONY/PRO/CAMERA` `-2 ENOENT`）；(4) 核验回放 **`[Photo Capture]`**（`_f.uxc 0x6856`：`8.3M` 4K / `2.1M` HD，`JPEG`/`HEIF 4:2:0`/`4:2:2`）在 `XAVC S-I DCI 4K` 片段上的硬拦截（`_g.uxc 0x60ce` `-95`）+ 静态专用 `[Enlarge Image]` + `Slot-1` Tier-0 `-EROFS`，驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`r65_init_ok=1`, `r65_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.80s` | [`r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-composited.png`](assets/r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-composited.png) |
| **65B（第 113 次实跑）：Fail-Closed Wave-51 防火墙 — Long-GOP DCI 4K/24.00p、DCI 4K 120p、沉睡 8K、Movie `Recall Custom hold`、`SONY/PRO/CAMERA` 伪造、`DCI 4K` `[Photo Capture]` 与 `Slot-1` 只读拦截** | `r65b` | `wave51_dci4k_aspect_camset_photocap_guard` | Native ARM64 Fail-Closed 注入阻断实测：(1) 拦截 Long-GOP `DCI 4K`/`24.00p`（`-95 EOPNOTSUPP`）、`XAVC S-I DCI 4K 119.88p` 与 `S&Q 120fps`（`-22 EINVAL`）、沉睡 `xavc_hs_8k_24p`（`-95 EOPNOTSUPP`）、无 Log 启用 HDMI RAW（`-16 EBUSY`）及越界快门角 `400.0 deg`（`-22 EINVAL`）；(2) 拦截 `FX6` 静态 `Aspect Ratio`（`-2 ENOENT`）；(3) 拦截 Movie/`S&Q`/`iAuto`/`MR` 下启用 `Recall Custom hold`（`-16 EBUSY`）、保持期间启用自拍或第 12 项伪造（`-22 EINVAL`）、`FX6` `SONY/PRO/CAMERA` 跨机型伪造（`-2 ENOENT`）及 `Slot-2 CAMSET` 越权（`-13 EACCES`）；(4) 拦截 `XAVC S-I DCI 4K` 片段执行 `[Photo Capture]`（`_g.uxc 0x60ce` `-95 EOPNOTSUPP`）、Movie 态 `[Enlarge Image]`（`-16 EBUSY`），以及向只读 `Slot-1` 保险库/`P2`/`cnflasha` 写入照片捕获或 `CAMPR`/`CAMSET`（`-30 EROFS`, `slot1_vault_sha256_match=1`, `emmc_write_count=0`, `r65b_ok=1`） | `13/13` 校验（早期 Fail-Closed 注入 C 探针退出） | 跳过（Fail-Closed 注入 C 探针退出） | **`0`** / **`0`** / **`0`** | `7.91s` | — |
| **65C（第 114 次实跑 · 闭环）：洁净卸载 `/tmp` Stage-B 覆盖层 + Wave-51 复位层级不对称验证 + `16/16 H0 == H3` + Big-6 Home 渲染** | `r65c` | `clean_unmount_wave51_reset_h0_h3_big6` | Native ARM64 Wave-51 联合预演（**第 `65` 轮里程碑 / `38/38` 实机轮次 · 第 `114/114` 次独立实跑闭环**）：洁净卸载易失性 `/tmp` Stage-B 覆盖层验证 100% 恢复原厂 `ILME-FX3 Ver. 7.02`（`stock_unmount_restored_ok=1`）；实证 `[Camera Settings Reset]` 将静态 `[Aspect Ratio]` 复位为 `3:2`、`[JPEG/HEIF Image Size]` 复位为 `L` 并将 `[Memory/Recall Media]` 复位至 `Slot 1`，而 **`[Reg. Custom Shoot Set]`（`Recall Custom hold 1..3`）、机身 `1..3` 存储库、`[Photo Capture]` `[JPEG/HEIF Switch]`、`[Enlarge Initial Mag.]` 与 `[Enlarge Initial Position]` 均跨 `[Camera Settings Reset]` 存活**（`camreset_preserves_wave51_survivors_ok=1`），卡片 `[Format]` 仅擦除 `M1..M4` 与 `CAMSET` 而不影响机身 `1..3` 与 `Recall hold`（`card_format_preserves_body_ok=1`），`[Initialize]` 恢复全部出厂默认（`initialize_restores_wave51_defaults_ok=1`）；经真机 `/lib/ld-2.25.so` `dlopen`（`dlopen_ok=1`）达成 **`16/16 H0 == H3`**（`drift_bits=0`, `cnflasha_write_bytes=0`, `emmc_write_bytes=0`, `raw_firmware_bytes_leaked=0`），并驱动 `appFw.so` 渲染简体中文 **Big-6 Home**（`346,686` 非零像素，`87` 唯一色，`emmc_write_count=0`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `76.59s` | 同 `65A` 架构（Big-6 Home） |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 Wave-51 四大支柱初始化与 Stage-B 四路桥接（`r65a` — 第 112 次实跑）
```text
FX6_R65_WAVE51_INIT fx3_wave51_nodes_ok=1 uxc_tokens_ok=1
  dci4k_uhd_hdmi_raw_ok=1 still_aspect_ratio_ok=1
  recall_hold_camset_ok=1 photocap_enlarge_slot1_ok=1
  dci4k_119p_rc=-22 long_gop_dci4k_rc=-95 dormant_8k_rc=-95
  hdmi_raw_no_log_rc=-16 fx6_still_aspect_rc=-2 movie_recall_hold_rc=-16
  fx6_pro_cam_spoof_rc=-2 pcap_dci4k_rc=-95 pcap_slot1_rc=-30
  p2_write_blocked_rc=-30 p2_sha256_match=1
  cnflasha_sha256_match=1 slot1_vault_sha256_match=1
  long_gop_dci4k_bypass_events=0 fx6_still_aspect_spoof_events=0
  movie_recall_hold_bypass_events=0 fx6_pro_camera_spoof_events=0
  dci4k_photocap_bypass_events=0 slot1_wave51_write_events=0
  passive_tx_bytes_emitted=0 cnflasha_writes=0 e_nd_actuator_tx_count=0
  appfw_present=1 shim_present=1 emmc_write_count=0
  r65_init_ok=1 verify_us=812861

FX6_R65_XAVC_DCI4K_UHD_HDMI_RAW_BRIDGE xavc_si_dci4k_24p_reboot_59p_ok=1
  long_gop_uhd_only_4264_hdmi_raw_slog3_ok=1
  shutter_angle_5_6_to_360_2f_64f_ok=1 xavc_dci4k_uhd_hdmi_raw_ok=1
  long_gop_dci4k_bypass_events=0 emmc_write_count=0 r65_bridge_ok=1

FX6_R65_STILL_ASPECT_RATIO_FX6_BRIDGE still_aspect_4ratio_raw_crop_ok=1
  apsc_s35_l_to_m_clamp_ok=1 fx6_still_aspect_enoent_ok=1
  still_aspect_ratio_fx6_ok=1 fx6_still_aspect_spoof_events=0
  emmc_write_count=0 p2_setting_writes=0

FX6_R65_RECALL_HOLD_11CHK_CAMSET_BRIDGE reg_custom_shoot_11chk_still_pasm_ok=1
  body_1_3_card_m1_m4_campr_camset_ok=1 fx6_pro_camera_enoent_ok=1
  recall_hold_11chk_camset_ok=1 movie_recall_hold_bypass_events=0
  fx6_pro_camera_spoof_events=0 cnflasha_writes=0 emmc_write_count=0

FX6_R65_PHOTOCAP_ENLARGE_SLOT1_VAULT_BRIDGE photocap_83m_21m_dci4k_lockout_ok=1
  enlarge_image_mag_pos_split_ok=1 slot1_tier0_vault_erofs_ok=1
  photocap_enlarge_slot1_ok=1 dci4k_photocap_bypass_events=0
  slot1_wave51_write_events=0 cnflasha_writes=0 emmc_write_count=0
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `101` 次 `OSD_FLUSH` / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 Fail-Closed Long-GOP `DCI 4K`、`119.88p`、Movie `Recall Custom hold`、`SONY/PRO/CAMERA` 伪造、`DCI 4K` `[Photo Capture]` 与 `Slot-1` 隔离拦截（`r65b` — 第 113 次实跑）
```text
FX6_R65_WAVE51_GUARD long_gop_dci4k_rc=-95 long_gop_24_00p_rc=-95
  dci4k_120p_rc=-22 dci4k_sq_120fps_rc=-22 dormant_8k_rc=-95
  hdmi_raw_no_log_rc=-16 angle_out_of_range_rc=-22 fx6_still_aspect_rc=-2
  recall_movie_rc=-16 recall_sq_rc=-16 recall_iauto_rc=-16 recall_mr_rc=-16
  recall_selftimer_rc=-22 recall_12chk_rc=-22 fx6_pro_camera_rc=-2
  camset_slot2_rc=-13 pcap_dci4k_rc=-95 pcap_slot1_rc=-30
  enlarge_movie_rc=-16 slot1_wave51_erofs_rc=-30
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  long_gop_dci4k_bypass_events=0 fx6_still_aspect_spoof_events=0
  movie_recall_hold_bypass_events=0 fx6_pro_camera_spoof_events=0
  dci4k_photocap_bypass_events=0 slot1_wave51_write_events=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  appfw_ok=1 shim_elf_ok=1 cnflasha_writes=0 emmc_write_count=0
  r65b_ok=1 verify_us=854677
```

### 2.3 洁净卸载还原原厂、Wave-51 复位层级与 `16/16 H0 == H3`（`r65c` — 第 114 次实跑）
```text
FX6_R65_CLEAN_UNMOUNT_WAVE51_H0_H3 stock_unmount_restored_ok=1
  camreset_preserves_wave51_survivors_ok=1 card_format_preserves_body_ok=1
  initialize_restores_wave51_defaults_ok=1
  long_gop_dci4k_bypass_events=0 fx6_still_aspect_spoof_events=0
  movie_recall_hold_bypass_events=0 fx6_pro_camera_spoof_events=0
  dci4k_photocap_bypass_events=0 slot1_wave51_write_events=0
  slot1_vault_ro_blocked_rc=-30 slot1_vault_sha256_match=1
  p2_write_blocked_rc=-30 cnflasha_ro_blocked_rc=-30
  cnflasha_write_bytes=0 emmc_write_bytes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  passive_tx_bytes_emitted=0 e_nd_actuator_tx_count=0
  raw_firmware_bytes_leaked=0 emmc_write_count=0
  r65c_ok=1 verify_us=407682
```

---

## 3. `r65a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `<= 27,467 B`）

| `r65a` Alpha（`26.21 KiB` / `26,842 B`） | `r65a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r65a Big6 Alpha](assets/r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-alpha.png) | ![r65a Big6 Composited](assets/r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机上电执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）`CFexpress VPG200+` / `SDXC V90+` 机内录制与 Type-A HDMI 外部录制台架（实测内部 `XAVC S-I DCI 4K` `4096×2160` `17:9` `24.00p` 强制重启与回放隔离、`59.94p` `600M` 上限、S&Q `1..48fps`、Long-GOP `3840×2160` UHD 边界、`4264×2408` 外部 HDMI RAW 强制 `S-Log3` 锁定，以及快门 `Angle` `5.6..360.0 deg` / `2F..64F` 实拍时序）。
2. 物理 Sony `ILME-FX3`（`Ver. 7.02`）光学成像与存储卡路径台架（实测静态 `[Aspect Ratio]` `3:2` `12M` / `4:3` `11M` / `16:9` `10M` / `1:1` `8.0M`、`RAW` 全像素裁剪元数据与 `APS-C S35` `L->M` 降档、11 复选框 `[Reg. Custom Shoot Set]` `Recall Custom hold 1..3` 自定义按键按住保持及 `[HLG Still Image]=Off` 联动，以及机身 `1..3` / 卡 `M1..M4` `/PRIVATE/SONY/SETTING/FX3/CAMPR%02d%c.DAT` & `CAMSET01..10.DAT` 实写实读）。
3. 物理 Sony `ILME-FX3`（`Ver. 7.02`）回放抽帧与放大交互台架（实测 `[Photo Capture]` `8.3M` 4K / `2.1M` HD `JPEG`/`HEIF 4:2:0`/`4:2:2` 在 `XAVC S-I DCI 4K` 片段上的 `_g.uxc 0x60ce` 拒绝提示、静态 `[Enlarge Image]` `[Enlarge Initial Mag.]`/`[Enlarge Initial Position]` 跨 `[Camera Settings Reset]` 持久化，以及 `Slot-1` 写保护与 `MDB` 数据库行为）。

---

## 5. 复现命令与洁净室合规

```bash
# Run 65A (112th Live Run): Wave-51 4-Pillar XAVC S-I DCI 4K vs UHD/HDMI RAW + Aspect Ratio + Reg. Custom Shoot Set/CAMPR/CAMSET + Photo Capture/Slot-1 + Big-6 Home (SChinese)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 65 --r65-mode dci4k_aspect_camset_photocap_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r65a --duration 71 \
  --run-dir <SCRATCH_ROOT>/round65-qemu/r65a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500 \
  --export-png-stem r65a-dci4k-aspect-camset-photocap-4ch-big6-schinese \
  --export-png-dir reports/2026-11-17-round65-milestone-dci4k-aspect-recall-hold-camset-photocap-qemu/assets

# Run 65B (113th Live Run): Fail-Closed Wave-51 Guard (Long-GOP DCI 4K, DCI 4K 120p, Movie Recall Hold, FX6 SONY/PRO/CAMERA Spoof, DCI 4K Photo Capture, Slot-1 EROFS)
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 65 --r65-mode wave51_dci4k_aspect_camset_photocap_guard --sd-manifest-mode valid --lang en \
  --run-id r65b --duration 35 \
  --run-dir <SCRATCH_ROOT>/round65-qemu/r65b

# Run 65C (114th Live Run — 65th Milestone & 38/38 Real-HW Closure): Clean Unmount Stock FX3 Restoration, Wave-51 Reset Tiers + 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 65 --r65-mode clean_unmount_wave51_reset_h0_h3_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r65c --duration 71 \
  --run-dir <SCRATCH_ROOT>/round65-qemu/r65c \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 1500
```
- **洁净室合规声明**：所有报告、遥测 JSON（`summary.json`）与视觉资产均严格脱敏：`raw_firmware_bytes_leaked == 0`、`emmc_write_count == 0`、`cnflasha_writes == 0`、`long_gop_dci4k_bypass_events == 0`、`fx6_still_aspect_spoof_events == 0`、`movie_recall_hold_bypass_events == 0`、`fx6_pro_camera_spoof_events == 0`、`dci4k_photocap_bypass_events == 0`、`slot1_wave51_write_events == 0`，未包含任何专有固件原始字节、宿主机绝对路径或受保护的实时 QEMU 监控端口信息。
