# Round 38：FX3 7.02 原厂内核真机准备实跑（Part 17）— No-UVC USB Gadget 防火墙、`USB-PD` (`NP-FZ100`) / `DC-C1` (`>=65W / 5A`) 供电联锁、双介质 `.cube` User LUT 路径不对称与 `RMT-P1BT` BT/IR 互斥闭环

> **日期**：2026-11-15 | **基准内核**：`Linux version 4.9.337-scel+` (FX3 Ver. `7.02`)  
> **实测范围与物理边界**：以下所有运行时数据均在未修改的 **ILME-FX3 `7.02` 原厂 ARM64 内核（`4.9.337-scel+`）** 与真机动态链接器 `/lib/ld-2.25.so` 上通过 3 次独立 QEMU AArch64（`virt,gic-version=2,secure=off`、`cortex-a35`、`5120 MiB`）实机预演（`r38a` / `r38b` / `r38c`）测得；**物理实体 `ILME-FX3` 机身、主机 PC USB-C 枚举、`DC-C1` 假电池实测、`SDXC`/`CFexpress-A` 实卡 `.cube` 加载与配对 `RMT-P1BT` 蓝牙遥控器尚未上电执行**（未测物理边界见 §4）。

---

## 1. 三项实机预演总览（`r38a` / `r38b` / `r38c`）

| 实跑场景 | Run ID | `r38_mode` | 核心硬件/安全门禁实测结果 | Stage-B SHA-256 & Presenter | `GPE0` 非零像素 / 颜色 / `gpe_fb` | `nop_count` / `crashes` / `emmc_write` | 耗时 | 视觉凭证 |
| --- | --- | --- | --- | --- | ---: | :---: | ---: | --- |
| **38A：No-UVC USB Gadget 防火墙 + `USB-PD` (`NP-FZ100`) / `DC-C1` (`>=65W/5A`) 电气联锁 + Big-6 Home** | `r38a-nouvc-dcc1-pd-big6-schinese` | `nouvc_dcc1_pd_big6` | Native ARM64 Stage-A 与 `libgrm-fbinit9.so` 桥接拦截不支持的 `[USB Streaming]` UVC/UAC composite gadget 绑定（`uvc_gadget_reject_rc=-95` `EOPNOTSUPP`，`NO_UVC_FX3_702_HARDWARE_ABSENT`），放行 5 项合法 USB 模式（`Sel.When Connect` / `MSC` / `MTP` / `Remote Shooting` `1024x576` 无音频上限 / `USB-LAN` `RNDIS`/`CDC-NCM` `usblan_rndis_ncm_rc=0`）与 `4K 59.94p` Network Streaming（`38 Mbps` 通过、`50 Mbps` 拒收 `rc=-22`）；校验证实机身 Type-C `USB-PD` 无 `NP-FZ100` 被阻断（`body_pd_no_fz100_rc=-19` `ENODEV`）、Micro-USB 供电拒收（`rc=-95`）、`DC-C1` 假电池 `65W/5A e-Marked` 通过（`rc=0`）而 `<65W`（`45W`）与非 `5A` 线缆均拒收（`rc=-22`），并渲染 **Big-6 Home** | `13/13` · `sid=0x0a` (`31procam_big6_menu_home_presenter`, `schinese`) | **`346,686`** / **`87`** / **`0`** | **`0`** / **`0`** / **`0`** | `72.34s` | [`r38a-nouvc-dcc1-pd-big6-schinese-composited.png`](assets/r38a-nouvc-dcc1-pd-big6-schinese-composited.png) |
| **38B：双介质 `.cube` LUT 路径不对称（`SD` vs `CFexpress-A`, `17pt/33pt`, `<=63B`）与 `Cine EI` (`800 / 12800`)** | `r38b-lut-path-cineei` | `lut_path_cineei` | Native ARM64 `.cube` 校验器放行 SDXC `/Private/Sony/PRO/LUT/`（`17pt` / `33pt`, `rc=0`）及 CFexpress Type A `/Sony/PRO/LUT/`（`33pt`, `rc=0`），拦截互换卡槽目录前缀（`rc=-22`）及 `65pt` `.cube`（`rc=-22`），精确边界测试 `63B` 文件名通过（`rc=0`）而 `64B` 文件名拒收（`lut_64b_name_reject_rc=-36` `ENAMETOOLONG`）；锁定 `Cine EI` 传感器原生增益仅限 `800 / 12800`（`1600` 拒收 `rc=-22`；高基准 `12800` 有效 `3200..51200 EI` 通过而 `1600/64000 EI` 越界拒收 `rc=-34` `ERANGE`），并通过 `MS_RDONLY` 重挂载强制锁定 Stock `p2:/setting/Backup.bin`（`p2_write_blocked_rc=-30` `EROFS`, `p2_setting_bytes_touched=0`, `p2_setting_sha256_match=1`） | `13/13` 校验（早期 `.cube`/`Cine EI` 校验退出） | 跳过（LUT/`Cine EI` C 探针退出） | **`0`** / **`0`** / **`0`** | `6.54s` | — |
| **38C：`RMT-P1BT` (`BT 4.2`) vs IR / GPS 互斥、`Creators' Cloud` (`OK/NG/KEEP`) 与 `16/16 H0 == H3`** | `r38c-rmtp1bt-clipflag-seal` | `rmtp1bt_clipflag_seal` | 验证 `[Bluetooth Rmt Ctrl] = On` 时 `RMT-P1BT` (`BT 4.2`) 指令通过（`rmtp1bt_bt42_cmd_rc=0`）同时精确屏蔽机身 IR 与手机 GPS 联动（`ir_when_bt_on_rc=-16`, `gps_when_bt_on_rc=-16` `EBUSY`），关闭后恢复（`ir_when_bt_off_rc=0`, `gps_when_bt_off_rc=0`）；在 `tmpfs` 暂存 `OK`/`NG`/`KEEP` 3 条 `NonRealTimeMeta` 剪辑标记（`cloud_filter_ok_keep_count=2`, `nvs_writes_delta=0`, `p2_setting_writes=0`），通过真机 `/lib/ld-2.25.so` `dlopen("/tmp/jiritsu/libJit.so")`（`dlopen_ok=1`）并达成 **`16/16 H0 == H3`**（`drift_bits=0`） | `13/13` 校验（早期 BT/IR/ClipFlag 校验退出） | 跳过（`RMT-P1BT`/ClipFlag C 探针退出） | **`0`** / **`0`** / **`0`** | `4.85s` | — |

---

## 2. 关键实测机制详情（Live QEMU ARM64 Kernel）

### 2.1 No-UVC USB Gadget 防火墙与 `USB-PD` (`NP-FZ100`) / `DC-C1` (`>=65W / 5A`) 联锁（`r38a`）
```text
FX6_R38_NOUVC_DCC1_PD_INIT uvc_gadget_reject_rc=-95 uvc_reason=NO_UVC_FX3_702_HARDWARE_ABSENT
  usb_allowed_modes=5 msc_rc=0 mtp_rc=0 remote_shooting_rc=0 remote_webcam_cap=1024x576_no_audio
  usblan_rndis_ncm_rc=0 netstream_4k5994_38mbps_rc=0 netstream_over38_reject_rc=-22
  body_pd_with_fz100_rc=0 body_pd_no_fz100_rc=-19 micro_usb_power_rc=-95
  dcc1_65w_5a_rc=0 dcc1_under65w_reject_rc=-22 dcc1_non5a_reject_rc=-22
  appfw_present=1 wlan_present=1 shim_present=1 emmc_write_count=0 r38_init_ok=1 verify_us=604952

FX6_R38_NOUVC_DCC1_PD_BRIDGE uvc_gadget_reject_rc=-95 usblan_rc=0 netstream_4k5994_mbps=38
  body_pd_no_batt_rc=-19 dcc1_65w_5a_rc=0 dcc1_under_rc=-22
  nouvc_blocked_ok=1 usblan_netstream_ok=1 pd_dcc1_interlock_ok=1 emmc_write_count=0 r38_bridge_ok=1
```
- 真实 `FX3_MODE_TO_BIG6`（`0x7028`）驱动 `appFw.so` 进入 **Big-6 Home（`31procam_big6_menu_home_presenter`, `sid=0x0a`, `lang=schinese`）**，通过 `13/13` Stage-B SHA-256 锁定，`346,686` 非零像素 / `87` 唯一色 / `nop_count=0` / `gpe_fb=0` / `emmc_write_count=0`、`161` 实时线程零崩溃。

### 2.2 双介质 `.cube` User LUT 路径不对称与 `Cine EI` 双原生增益锁（`r38b`）
```text
FX6_R38_LUT_PATH_CINEEI sd_prefix=/Private/Sony/PRO/LUT/ cfx_prefix=/Sony/PRO/LUT/
  sd_17pt_accept_rc=0 sd_33pt_accept_rc=0 cfx_33pt_accept_rc=0
  sd_swapped_cfx_path_reject_rc=-22 cfx_swapped_sd_path_reject_rc=-22
  lut_63b_name_accept_rc=0 lut_64b_name_reject_rc=-36 lut_65pt_reject_rc=-22
  max_user_lut_slots=16 ae_offset_range=0EV_+2EV
  base_800_accept_rc=0 base_12800_3200ei_rc=0 base_12800_12800ei_rc=0 base_12800_51200ei_rc=0
  invalid_base_1600_reject_rc=-22 ei_1600_under_12800_reject_rc=-34 ei_64000_over_12800_reject_rc=-34
  sensor_gain_locked_dual_base=1 p2_setting_bytes_touched=0 p2_setting_sha256_match=1 p2_write_blocked_rc=-30
  appfw_cineei_ok=1 shim_elf_ok=1 emmc_write_count=0 r38b_ok=1 verify_us=741931
```

### 2.3 `RMT-P1BT` (`BT 4.2`) vs IR/GPS 互斥与 `Creators' Cloud` 剪辑标记清洁度（`r38c`）
```text
FX6_R38_RMTP1BT_CLIPFLAG bt_spec=4.2 rmtp1bt_bt42_cmd_rc=0
  ir_when_bt_on_rc=-16 gps_when_bt_on_rc=-16 bt_when_off_rc=-19 ir_when_bt_off_rc=0 gps_when_bt_off_rc=0
  ir_gps_masked_when_bt_on=1 ir_gps_restored_when_bt_off=1
  clip_flags_staged=3 cloud_filter_ok_keep_count=2 nvs_writes_delta=0 p2_setting_writes=0
  dlopen_ok=1 surfaces_verified=16 surfaces_h0_eq_h3=16 drift_bits=0
  emmc_write_count=0 r38c_ok=1 verify_us=3804
```

---

## 3. `r38a` 视觉凭证（`1024 x 540` Big-6 Home `sid=0x0a`, `schinese`, `< 28 KiB`）

| `r38a` Alpha（`26.50 KiB` / `27,132 B`） | `r38a` Composited（`26.82 KiB` / `27,467 B`） |
| :---: | :---: |
| ![r38a Big6 Alpha](assets/r38a-nouvc-dcc1-pd-big6-schinese-alpha.png) | ![r38a Big6 Composited](assets/r38a-nouvc-dcc1-pd-big6-schinese-composited.png) |

---

## 4. 尚未执行的真实物理相机台架测试边界

以下项目只能在物理 Sony `ILME-FX3` 相机及外接配件上执行，**本次未运行**：
1. 物理 Sony `ILME-FX3`（`Ver. 7.02`）通过 USB-C 连接主机 PC，实测无原生 UVC 视频类枚举的同时运行 `RNDIS`/`CDC-NCM` USB-LAN 与 `4K 59.94p`（`<= 38 Mbps`）`RTMP/RTMPS/SRT` 网络推流。
2. 物理 Sony `DC-C1` 直流耦合器连接 `>=65W USB-PD` 电源 + `5A e-Marked` 线缆与不足功率（`<65W / 3A`）电源时的指示灯闪烁告警对比，以及机身直连 Type-C PD 时拔出 `NP-FZ100` 电池的实机掉电测试。
3. 物理 `SDXC`（`/Private/Sony/PRO/LUT/`）与 `CFexpress Type A`（`/Sony/PRO/LUT/`）双卡槽实卡 `.cube`（`17pt/33pt`, `<=63B`）加载、`Cine EI` `800 / 12800` 切换（`3200..51200 EI`）以及实机配对 `RMT-P1BT` 蓝牙遥控屏蔽红外/GPS 联动与 `Creators' Cloud` `OK/NG/KEEP` 上传。

---

## 5. 复现命令与洁净室合规

```bash
# Run 38A: No-UVC USB Gadget Firewall + USB-PD/DC-C1 Interlock + Stage-B Big-6 Home
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 38 --r38-mode nouvc_dcc1_pd_big6 --sd-manifest-mode valid --lang schinese --initial-setting-done 1 \
  --run-id r38a-nouvc-dcc1-pd-big6-schinese --duration 68 \
  --run-dir <SCRATCH_ROOT>/fx6-r38-runs/r38a \
  --key-seq "0x01ac:120:1400,0x0030:120:800,0x01ac:120:4800,0x7028:120:5500" --key-settle-ms 5500 \
  --export-png-stem r38a-nouvc-dcc1-pd-big6-schinese \
  --export-png-dir reports/2026-11-15-round38-realhw-nouvc-dcc1-lut-path-cineei-qemu/assets

# Run 38B: Dual-Media .cube User LUT Path-Asymmetry + Cine EI (800 / 12800)
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 38 --r38-mode lut_path_cineei --lang en --run-id r38b-lut-path-cineei \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r38-runs/r38b

# Run 38C: RMT-P1BT (BT 4.2) vs IR/GPS Lock, Creators' Cloud Clip Flags & 16/16 H0 == H3
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3 -B outputs/fx6-native-presenter-closure/build_and_run_round.py \
  --round 38 --r38-mode rmtp1bt_clipflag_seal --lang en --run-id r38c-rmtp1bt-clipflag-seal \
  --duration 30 --run-dir <SCRATCH_ROOT>/fx6-r38-runs/r38c

# Dual-Mode Unit Tests & Clean Audit
/usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx6-native-presenter-closure/tests -p "test_*.py"
/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only
```

- 全部临时构建与 QEMU 暂存目录已彻底清理；两张 PNG 视觉凭证体积分别为 `27,132 B`（`26.50 KiB`）与 `27,467 B`（`26.82 KiB`，均 `< 28 KiB`）；完整结构化遥测与 `13/13` Stage-B SHA-256 核验审计见 [`summary.json`](summary.json)。
