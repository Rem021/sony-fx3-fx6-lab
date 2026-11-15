# Round 34：FX3 7.02 原厂内核真机准备实跑（Part 13）— `p12:/cert/RQ_LIC.DAT` C2PA `EROFS` 锁、`VMC-BNCM1`（`EXT-LK`）SMPTE TC + `IMX510` 6 轴陀螺仪 XML、`CXD90057+CXD90058`/`sabin` 1,724 MiB 编码池与 `16-bit SDI RAW` 屏蔽及 RAID-6 `GF(256)` 2 块自愈 + `16/16 H0 == H3` 原厂密封

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r34a` / `r34b` / `r34c`）测得；**物理实体 FX3 相机机身、物理 `VMC-BNCM1` BNC 适配器及真实 `CXD90058` / `CFexpress` 实体硬件台架测试尚未上电执行**（未测物理边界见 §4）。

---

## 1. 三项实机预演总览（`r34a` / `r34b` / `r34c`）

| 实跑场景 | Run ID | `r34_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **34A：`p12:/cert/RQ_LIC.DAT` C2PA `EROFS` 锁、`VMC-BNCM1` `EXT-LK` 24.00 fps TC + `IMX510` 6 轴陀螺仪 XML + Big-6 Home** | `r34a-c2pa-tc-gyro-big6-schinese` | `c2pa_tc_gyro_big6` | 挂载合成 `p12:/cert/RQ_LIC.DAT`（`MS_RDONLY`），写拦截返回 `EROFS (errno=30)`（`c2pa_sha256_match=1`, `c2pa_cert_writes=0`）· 拦截跨机型 C2PA 签名（`cross_model_c2pa_blocked=1`, `rc=-22`）· 验证 `VMC-BNCM1`（`AD_JACK_IN -> EXT-LK 24.00 fps` LTC-IN 并屏蔽 BNC `TC-OUT`）+ UART 互斥（`rc=-16`）· 生成 `C0001M01.XML`（`809 B`, `NonRealTimeMeta`, `IMX510 8700 us`, `imuAxes=6`）· `libmpr.so` 双重校验证实（`mpr_nrtm_ok=1`, `mpr_ltc_ok=1`, `c2pa_erofs_ok=1`, `r34_bridge_ok=1`） | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,206`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.94s` | [`r34a-c2pa-tc-gyro-big6-schinese-composited.png`](assets/r34a-c2pa-tc-gyro-big6-schinese-composited.png) |
| **34B：`CXD90057`（*Mira*）+ `CXD90058`（*Cetus*）`1,724 MiB`、`sabin` 只读与 `16-bit SDI RAW`（`mew.bin`）失败关闭屏蔽** | `r34b-cxd90058-sabin-sdi-mask` | `cxd90058_sabin_sdi_mask` | 校验真实 `/setting/cxd90057.dtb`（`16,875 B`）与 5 个 `/usr/sabin/*.bin` 微码 · `p8:/cpapp-b.bin` 与 `sabin` `MS_RDONLY` 锁定（`p8_cpapp_erofs=1`, `errno=30`, `cxd90058_writes=0`, `sabin_writes=0`）· `memcfg= 1,724 MiB` 池通过 `XAVC-I (1480 MiB)` 与 `XAVC HS (1220 MiB)` 并拦截 `1856 MiB` 溢出（`rc=-12`）· `/usr/lib/libmpr.so` 实机解析 `6/6` 编码器符号 · `mew.bin` 缺失时 `16BIT_SDI_RAW` 返回 `-ENODEV (-19)` 零崩溃（`sdi_raw_masked=1`） | `13/13` 校验（早期 DSP/SDI 屏蔽验证退出） | 跳过（`CXD90058` / `sabin` / `SDI RAW` 屏蔽验证后停机） | **`0`** / **`0`** / **`0`** | `5.88s` | — |
| **34C：双介质 Tier-0 RAID-6 `GF(256)` 2 块自愈 & 卸载后 `16/16 H0 == H3` 原厂密封** | `r34c-raid6-gf256-seal-16` | `raid6_gf256_seal_16` | 向 11 x `4,096 B` 次级备份归档注入 2 块损坏（`chunk 2`, `chunk 7`）并在 ARM64 guest RAM 中经 `GF(256)`（`0x11d`, `g=0x02`）P+Q 校验 100% 比特无损重建（`orig_archive_sha256 == healed_archive_sha256`）· 执行卸载恢复（`im.elf.orig -> im.elf`）后 `16/16` 全分区 `SHA256(H0) == SHA256(H3)`，`orig_residual_count=0`，`tmp_jiritsu_residual_count=0`，`mode_residual_count=0`，`p15_ro_erofs=1` | `13/13` 校验（早期 RAID-6 + 密封验证退出） | 跳过（`RAID-6` 自愈 + `16/16 H0==H3` 密封后停机） | **`0`** / **`0`** / **`0`** | `6.27s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 `p12:/cert/RQ_LIC.DAT` C2PA `EROFS` 锁、`VMC-BNCM1`（`EXT-LK`）与 `IMX510` 6 轴陀螺仪 XML（`r34a`）
```text
FX6_R34_C2PA_TC_GYRO_INIT p12_cert_erofs=1 p12_cert_errno=30
  c2pa_sha256_before=4c2af5162b8045bf3e2cd2c8d78e9340145aa621bcf4ed07c163b535bf067198
  c2pa_sha256_after=4c2af5162b8045bf3e2cd2c8d78e9340145aa621bcf4ed07c163b535bf067198
  c2pa_sha256_match=1 c2pa_cert_writes=0 fx3_c2pa_allowed=1 cross_model_c2pa_blocked=1 cross_model_c2pa_rc=-22
  vmc_bncm1_ext_lk=1 ad_jack_in=1 tc_sync_mode=EXT-LK tc_fps=24.00 ltc_mv=1800 bnc_tc_out_masked=1 vmc_uart_mutex_rc=-16
  nrtm_xml_path=/tmp/r34_clip/C0001M01.XML nrtm_xml_bytes=809 nrtm_xml_ok=1
  imx510_readout_us=8700 imu_axes=6 imu_packets=240 mpr_nrtm_ok=1 mpr_ltc_ok=1
  emmc_write_count=0 r34_init_ok=1 verify_us=492898

FX6_R34_C2PA_TC_GYRO_BRIDGE c2pa_erofs_ok=1 c2pa_sha256_match=1 cross_model_c2pa_blocked=1
  vmc_bncm1_ext_lk=1 tc_fps=24.00 bnc_tc_out_masked=1 imx510_readout_us=8700 imu_axes=6
  nrtm_xml_ok=1 mpr_bridge_ok=1 emmc_write_count=0 r34_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,206` 非零像素 / `87` 唯一色 / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 `CXD90057` + `CXD90058` 双 BIONZ-XR `memcfg= 1,724 MiB`、`sabin` 只读与 `16-bit SDI RAW` 屏蔽（`r34b`）
```text
FX6_R34_CXD90058_SABIN ap_soc=CXD90057_Mira cp_soc=CXD90058_Cetus
  cxd90057_dtb_ok=1 cxd90057_dtb_bytes=16875 p8_cpapp_erofs=1 p8_cpapp_errno=30 p8_sha256_match=1
  sabin_erofs=1 sabin_blobs_verified=5 cxd90058_writes=0 sabin_writes=0
  memcfg_total_mib=1724 memcfg_xavc_i_mib=1480 memcfg_xavc_hs_mib=1220
  memcfg_overflow_blocked=1 memcfg_overflow_rc=-12
  mpr_dlopen_ok=1 mpr_syms_resolved=6 mpr_syms_total=6 xavc_i_bridge_ok=1 xavc_hs_bridge_ok=1
  mew_absent=1 sdi_raw_masked=1 sdi_raw_mask_rc=-19 hdmi_type_a_fallback=1
  emmc_write_count=0 r34b_ok=1 verify_us=71558
```

### 2.3 Tier-0 RAID-6 `GF(256)` 2 块比特腐败自愈与卸载后 `16/16 H0 == H3` 原厂密封（`r34c`）
```text
FX6_R34_RAID6_SEAL_16 gf256_poly=0x11d gf256_gen=0x02 data_chunks=11 parity_chunks=2 chunk_bytes=4096
  corrupted_chunks_injected=2 reconstructed_chunks=2
  orig_archive_sha256=ea07737133f19bdd239f3058c7f599582b4f87c39fb39c7d37224639ec2a382a
  healed_archive_sha256=ea07737133f19bdd239f3058c7f599582b4f87c39fb39c7d37224639ec2a382a
  raid6_sha256_match=1 raid6_healed_ok=1
  h0_im_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
  h3_im_sha256=2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772
  h3_surfaces_matched=16 h3_surfaces_total=16 h0_eq_h3=1
  orig_residual_count=0 tmp_jiritsu_residual_count=0 mode_residual_count=0
  p15_ro_erofs=1 emmc_write_count=0 r34c_ok=1 verify_us=496237
```

---

## 3. `r34a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r34a` Alpha（`26.21 KiB` / `26,842 B`） | `r34a` Composited（`26.51 KiB` / `27,147 B`） |
| :---: | :---: |
| ![r34a Big6 Alpha](assets/r34a-c2pa-tc-gyro-big6-schinese-alpha.png) | ![r34a Big6 Composited](assets/r34a-c2pa-tc-gyro-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony ILME-FX3 相机上执行，**本次未运行**：
1. 物理相机真实 eMMC `p12:/cert/RQ_LIC.DAT` 分区在实拍下的原厂 C2PA 内容凭证签名完整性核验。
2. 物理相机 Multi 端口连接实体 `VMC-BNCM1` 转接线并接入外部 SMPTE-12M LTC 24.00 fps 时码发生器与实拍 `IMX510` 陀螺仪封装联动测试。
3. 物理机身双 BIONZ-XR（`CXD90057` + `CXD90058`）在实体 CFexpress Type A 介质上的长时间高码率 `XAVC-I` / `XAVC HS` 编码压测。

---

## 5. 复现命令与洁净室合规

```bash
# Run 34A: p12 C2PA EROFS Lock + VMC-BNCM1 EXT-LK 24fps + IMX510 8700us Gyro XML + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 34 --r34-mode c2pa_tc_gyro_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r34a-c2pa-tc-gyro-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r34-runs/r34a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r34a-c2pa-tc-gyro-big6-schinese \
  --export-png-dir reports/2026-11-15-round34-realhw-cxd90058-c2pa-tc-gyro-seal-qemu/assets

# Run 34B: CXD90057+CXD90058 1724 MiB Pool + sabin EROFS + libmpr.so + 16-bit SDI RAW (mew.bin) Mask
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 34 --r34-mode cxd90058_sabin_sdi_mask --lang en --run-id r34b-cxd90058-sabin-sdi-mask \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r34-runs/r34b

# Run 34C: Dual-Media Tier-0 RAID-6 GF(256) 2-Chunk Self-Heal & Post-Uninstall 16/16 H0 == H3 Seal
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 34 --r34-mode raid6_gf256_seal_16 --lang en --run-id r34c-raid6-gf256-seal-16 \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r34-runs/r34c

# Dual-Mode Unit Tests & Clean Audit
PYTHONPATH=outputs/fx6-native-presenter-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx6-native-presenter-closure /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `26,842 B`（`26.21 KiB`）与 `27,147 B`（`26.51 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
