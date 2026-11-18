# Phase 334 第 16 级物理台架准备度预检器与 CI 确定性修复工程报告（`preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun` / Waves 64–65）

## 1. 核心结论（Conclusion-First）

1. **实测事实：Waves 64–65 四大 `ILME-FX3 Ver. 7.02`（`ilc/2210`，Model `0x91030080`）物理台架检查组（`Check Group A..D`）全部闭环**：在 `outputs/fx6-on-fx3-closure/` 新增第 16 级宿主机侧只读物理台架与实拍前准备度预检器 [`realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py)（Schema `realhw_preflight16_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_usblun_v1`，版本 `phase334_v1`，CLI 子命令 `preflight-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-and-usblun`，共 `2,508` 行），将 16 级操作员台架预检链路推进至 `Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334`。全部公共符号已在 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L2806) 完整导出并去重（`__all__` 共 **`2,752` 项零冲突**），CLI 子命令已在 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L5241) 接入，[`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L502) 已新增 `# 58.`。
2. **实测事实：Waves 64–65 关键勘误（Round-57 版权/序列号抗 Reset）、休眠能力辟谣（`Power Save by Monitor`、`Lossless Comp`、`UVC/UAC`）与 `USB LUN = Single` Slot-1 高危隔离全部 fail-closed 落地**：
   - **Check Group A（Wave 64 §§1–2：呼吸效应补偿 & 电影文件设置 / SDHC vs exFAT）**：[`evaluate_p334_check_group_a_breathing_camid_and_sdhc`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py#L741) 校验可被 `[Camera Settings Reset]` 复位的 `[Breathing Comp.]`（`_f 0x73ea`，默认 `Off`；在常规 `119.88p/100p`、`S&Q >= 100/120fps`、Still、HDMI 16-bit RAW、CIZ/Digital Zoom、Auto Framing 与微距/增倍镜下禁用，FX3 允许 `<100fps S&Q` 而 FX6 在任意 `S&Q=On` / `Distortion Comp.=Off` / `RAW` 下锁死 `Off`；后期呼吸补偿需付费 `Catalyst Prepare / Plugin` + 机身 `Distortion Comp.=Auto`，拒绝免费 `Catalyst Browse`）；校验仅限 Initialize 复位的 Movie `[File Settings]`（`Cam ID + Reel#` `A..Z` + `001..999` + `C/L/R` 滚转 `C999->D001` + `YYMMDD`，`Title` `<= 37` 字符默认 `"C"`，`Date+Title` `YYYYMMDD`，`SDHC FAT32 <= 32 GB` 强制 `Standard` + `4 GB` 分片并禁止与 `exFAT` 混用 `Simult. Recording`，对 `Slot 1` Tier-0 Vault 实施 `EROFS=30` 防火墙；对比 FX6 `TC/Media > Clip Name Format` `4..46` 字符 `nnn_`）。
   - **Check Group B（Wave 64 §§3–4：Round-57 版权 46 字符勘误、省电 9 条件 & NTSC/PAL Slot-1 格式化防火墙）**：[`evaluate_p334_check_group_b_copyright_powersave_and_ntscpal`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py#L1000) 严格执行 **Round-57 勘误**：`[Copyright Info]` 全部 4 项（`<=46` 字符）与 Still+Movie `[Write Serial Number]`（`BKID_APP_setting_write_serial_number_still_movie`）**均抗 `[Camera Settings Reset]`**（仅 `Initialize` 复位），且 `Copyright Info` 排除出 `CAMSET*.DAT` 而 `Write Serial Number` 布尔项保留；`[Power Setting Option]` 精确暴露 2 个 Initialize-only 项（`[Power Save Start Time]` 9 大官方旁路条件 + `[Auto Power OFF Temp.]=High` 仅限三脚架非手持），以 `EOPNOTSUPP=95` 拒绝休眠 `[Power Save by Monitor]`（`0x783f/0x6db5/0x6db6/0x60a8/0x6b2e`）及未暴露定时器；`[NTSC/PAL Selector]`（`0x6b6f`）要求完整重启并阻断跨制式直接回放，对 `base.uxc`（`0xe1e6..0xe9f6`）在 `Slot-1`（须保持物理 WP 锁定且含 Tier-0 备份）触发 `EROFS=30`。
   - **Check Group C（Wave 65 §§1–2：CIZ/Digital Zoom、8 档分速、Auto Slow Shutter 6 锁 & 双原生 Base ISO）**：[`evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py#L1186) 校验 `Optical Only`（`1.0x`）/ `Clear Image Zoom`（4K `<=1.5x` / HD `<=2.0x`）/ `Digital Zoom`（`<=4.0x`；激活期间强制 `CENTER_FIX` AF + `MULTI` 测光并关闭人脸/跟踪；`120p`、`S&Q >= 100fps`、Still RAW 禁用；FX6 零 Digital Zoom）；区分 Initialize-only `[Zoom Range]`/`[Zoom Ring Rotate]` 与 Resettable 8 档速度（`1st=3`/`2nd=8`/`Custom Key=3`/`Remote Fixed=3`）；校验可 Reset 的 `[Auto Slow Shutter]` 6+ 项互锁、Initialize-only `[ISO Range Limit]`（仅限手动 ISO）、Still 专属 `P/A + ISO AUTO` `[ISO AUTO Min. SS]`（闪光灯下由 `1/250s` 覆盖）及双原生 Base ISO 真值表（`Cine EI 800/12800`、`PP11_SCINETONE/HLG/Cine4 100/2000`、`PP_OFF 80/1600`，非 Cine EI 无 Base ISO 菜单，隔离 FX6 AGC）。
   - **Check Group D（Wave 65 §§3–4：休眠无损 RAW、HLG Still、`USB LUN=Single` Slot-1 危境、`NP-FZ100`/`DC-C1` PD 门控与双休眠 UVC）**：[`evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py#L1404) 辟谣并拦截 FX3 休眠 `[Lossless Comp]`（`0x6b56` -> `EOPNOTSUPP=95`，FX3 仅暴露 `Compressed`/`Uncompressed`）；校验 `[HLG Still Image]`（`HEIF 4:2:0/4:2:2` + `HEIF` + `P/A/S/M`）；对 `Sort Recording`/`Simultaneous Recording`/`Auto Switch Media=On`/`Slot-1` 目标写入执行 `EROFS=30`；针对 **CRITICAL `[USB LUN Setting]=Single` 仅暴露 `Slot 1`（隐藏 `Slot 2`）** 联合宿主机 MSC/Spotlight/`fseventsd`/`fsck` 隔离执行硬拦截；校验 USB-C PD 必须装配有电 `NP-FZ100` 或 `DC-C1`（`>=65W PD + 5A e-Marked` 线缆，对比 FX6 `19.5V DC IN`）；以 `EOPNOTSUPP=95` 阻断 FX3 & FX6 双端休眠 `[USB Streaming]` UVC/UAC（`0x6216/0x6194`），阻断 `[Movie Rec During Streaming]`（`0x79d5`）与 `[Rec. Media dur HDMI Output]`（`0x6144`）命中 Slot 1；叠加 `16/16 H0 == H3`（带序列号/CID 熵检）与双介质 `528 B FX3RCPT1`（不同 `st_dev`）Tier-0 门控及零发射安全红线。
3. **实测事实：4 项授权 Clean-Room CI 确定性/耗时修复（`msg_c2f9565b91c4`）已全部落地并验证通过**：
   - 修复 Phase 321 ([`realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier.py))、Phase 329 ([`realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier.py)) 与 Phase 334 `to_deterministic_json()` / `_canonical_sha256_dict()`，递归清零或剥离嵌套 `elapsed_seconds` / `*_elapsed*` / `*_ms` 计时字段，彻底消除 `1e-06` vs `0.0` 浮点抖动。
   - 修复 Milestone 147 / 175 / 193 主门控 ([`realhw_milestone147_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone147_master_gate.py)、[`realhw_milestone175_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone175_master_gate.py)、[`realhw_milestone193_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone193_master_gate.py)) `to_deterministic_json()` 与 `compute_milestone*_sha256()`：剥离嵌套非确定性计时字段与受子阶段计时影响的非确定性 `audit_digest_sha256`，同时在 [`test_milestone175_realhw_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_milestone175_realhw_master_gate.py) 将随 71 阶段扩展而增大的 wall-clock 预算从 `6.0s` 放宽至 `30.0s`。
4. **实测事实：四模式 100 项新单测、442 项 Clean-Room 目标回归、Milestone 324 Clean-Room 门控与洁净度审计全绿**：
   - 新增 [`test_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py) 共 **100** 项单测，在本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与无供体路径回退 4 种模式下均 **100/100 OK**。
   - 目标 6 套 CI 修复与 Phase 334 测试集（Phase 321、Phase 329、Milestone 147/175/193、Phase 334）在 `FX3_FX6_FORCE_CLEAN_ROOM=1` 下 **`442/442` 全数通过（`0` 失败，`181.591s`）**。
   - 对整个 `outputs/fx6-on-fx3-closure/tests` 执行 `FX3_FX6_FORCE_CLEAN_ROOM=1` 单进程 `unittest discover`（共 **`2,565` 项**，含 `skipped=51`）：**Phase 334 与 4 项 CI 修复测试全部通过**；仅既有 `test_phase68_stage_b_rehearsal_orchestrator.py::test_03_single_rehearsal_under_4_seconds` 在 509s 高负载发现尾部出现 `4.44s > 4.0s` 抖动（该测试在 `GITHUB_ACTIONS=true` 下阈值为 `15.0s`，且独立运行 `FX3_FX6_FORCE_CLEAN_ROOM=1` 时 **`34/34 OK`（`3.408s`）**）。
   - `FX3_FX6_FORCE_CLEAN_ROOM=1 python3 -B -m fx6_closure verify-milestone-324 --force-clean-room` 返回 **`status=OK pillars=6/6`**；本地无供体工作树下 `make verify-milestone-324` 因缺少 `Mac/work` 供体资产停留在 `recovery=57/58`（`pillars=5/6`，未改动既有 Recovery 适配器）。`make clean-audit` 返回 **`ALL GREEN`**。

---

## 2. 四态确定性报告指纹与实测命令回执

### 2.1 四态确定性 `report_sha256`（实测）

| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 退出码 | `O_RDONLY` 供体读取 | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `320 B` (`0.923 ms`) | `b98fb1c5f3c0091c0c4295da1b5483d6df432c16b9592890b533b8b6c0e84d4b` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `320 B` (`0.547 ms`) | `27e432f5eebf818b03215902e498e8ce38f225e38d21e7283865acaaab3ec113` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0 B` (`0.000 ms`) | `018329d2b60307e103faab95eca48bfee3324cae9b290a58a62314c6a2405024` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0 B` (`0.000 ms`) | `505d0d7ba305e47150b63c82fdcfe0ec48474a7266d291b6cc85ecacd4770330` |

### 2.2 本次交付与修改文件清单

1. Phase 334 核心交付：
   - [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py)
   - [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py)
   - [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py)
   - [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md)
   - [`outputs/fx6-on-fx3-closure/tests/test_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py)
   - [`reports/2026-11-17-phase334-preflight16-breathing-camid-copyright-powersave-zoom-ciz-rawcomp-usblun/README.md`](./README.md)
2. 授权 Clean-Room CI 确定性/计时修复（`msg_c2f9565b91c4`）：
   - [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_verifier.py)
   - [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_shoe_audio_4ch_subject_recog_hdmi_raw_desqueeze_and_varshutter_verifier.py)
   - [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone147_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone147_master_gate.py)
   - [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone175_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone175_master_gate.py)
   - [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone193_master_gate.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_milestone193_master_gate.py)
   - [`outputs/fx6-on-fx3-closure/tests/test_milestone175_realhw_master_gate.py`](../../outputs/fx6-on-fx3-closure/tests/test_milestone175_realhw_master_gate.py)

### 2.3 可复现验证命令

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_verifier.py"
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase334_missing PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure verify-milestone-324 --force-clean-room
make clean-audit
```
