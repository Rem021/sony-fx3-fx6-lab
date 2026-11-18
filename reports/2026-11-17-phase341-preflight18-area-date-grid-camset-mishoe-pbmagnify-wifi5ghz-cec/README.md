# Phase 341 第 18 级物理台架准备度预检器工程报告（`preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec` / Waves 68–69）

## 1. 核心结论（Conclusion-First）

1. **实测事实：Waves 68–69 四大 `ILME-FX3 Ver. 7.02`（`ilc/2210`，Model `0x91030080`）vs `ILME-FX6`（`Ver. 6.01`）物理台架检查组（`Check Group A..D`）全部落地闭环**：
   - 在 `outputs/fx6-on-fx3-closure/` 新增第 18 级宿主机侧只读物理台架与实拍前准备度预检器 [`realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py)（Schema `realhw_preflight18_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_cec_v1`，版本 `phase341_v1`，CLI 子命令 `preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec`，共 `2,200` 行），将 18 级预检链路推进至 `Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334 -> Ph338 -> Ph341`。
   - 全部 156 个公共符号已在 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3033) 导出，CLI 子命令与全部参数（含 `argparse` `help=` 字符串 `%%` 转义）已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L5752)（默认 `rc=2` 等待物理 Tier-0 双卡回执，`--simulate-bench-dry-run` `rc=0`），并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L511) 新增 Section `# 60.` 文档条目。
2. **实测事实：Check Groups A–D 关键硬件/固件契约、官方错别字指纹、休眠辟谣、Slot-1 `EROFS=30` 与 CEC 台架劫持防火墙全部 fail-closed 实现**：
   - **Check Group A（Wave 68 §§1–2：Reset 免疫 `Setup -> [Area/Date]` / 内部焊死 RTC 电池 vs FX6 `Clock Set` + Clean-HDMI `[Grid Line Display]` vs 0px HDMI `[Marker Display]`）**：[`evaluate_p341_check_group_a_area_date_grid_and_marker`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py#L769) 校验抗 `[Camera Settings Reset]`（仅 `[Initialize]` 归零）的 `Setup -> [Area/Date] -> [Area/Date/Time Setting]`（`_f 0x6a9c`，取代旧名 `0xe87f Date/Time Setup`）：精确 `30` 个 `AREA_GMT_*` 时区（含 `6` 个半小时偏移 `M_03_5`/`P_03_5`/`P_04_5`/`P_05_5`/`P_06_5`/`P_09_5`）、`[Daylight Savings]`（`0xe917` 与索尼原厂 ELF 错字 `convert_setting_daylight_saving_to_saylight_saving`）、`[Date Format]`（`0x670d`: `Y-M-D`/`M-D-Y`/`D-M-Y`）以及焊接式内部可充电 RTC 备电（无用户可换 CR2032 槽，亏电须装满电 `NP-FZ100` 关机静置 `>= 24h` 充电），对比 `FX6 Maintenance > Clock Set`（30 分钟步进且无独立 DST 开关）；同时校验均抗 Reset 的 **`[Grid Line Display]`**（`0x6f9d`，`Rule of 3rds`/`Square`/`Diag.+Square`，当 `[HDMI Info. Display]=On` 且非 RAW/非 `Off(HDMI Only)` 时**会透传至 HDMI**）与 Movie/S&Q 专属 **`[Marker Display]`**（`0x6803`/`Guideframe` `0x62f9`/15 比例 `Aspect Marker`/`Safety Zone`，在 `Focus Magnifier` 期间隐藏，且**永远向 HDMI 输出 `0` 像素**）。
   - **Check Group B（Wave 68 §§3–4：锁定 `Slot 1` 的 `[Save/Load Settings]` + `EROFS=30` + 零 PC Flash Sync + `XLR-H1` 冷靴互斥 vs FX6 零 `GENLOCK` BNC）**：[`evaluate_p341_check_group_b_camset_mishoe_and_flash_sync`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py#L942) 强制 `[Save/Load Settings]`（`0x6254`，`libSaveLoadSettings.so`）严格锁定 **`Slot 1`**（`CAMSET01..10.DAT`，`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`，`FX3` 对 `PRO/CAMERA` 命中 **`0`** 次，拒绝 `<= Ver. 1.01` 配置文件在 `>= 2.00` 加载，拒绝 `MR` 模式下加载，维护 18 项官方排除类别与独立的 `FTPSET/%s.DAT` 路径，区分机身 `Camera Set. Memory` `1..3` 与卡端 `M1..M4` `CAMPR%02d%c.DAT`），并对指向 `Slot 1` Tier-0 保险库的 `SAVE`/`DELETE` 强制返回 **`EROFS=30`**（允许只读 `LOAD`/`RECALL`），对比 `FX6 Project > All File`（`Media(B)` `.ALL`）及 `0` 命中的休眠 `[Reference File]`；**辟谣 FX3 机身无物理 PC Flash Sync 端子**（`FX3 appFw.so` `0` 个 `SYNCHRO_TERMINAL*` 符号 -> `EOPNOTSUPP=95`），`XLR-H1` 占用唯一电气 MI 热靴且仅提供无触点被动冷靴，物理排除 `HVL-LBPC`（`Video Light Mode` `0x6211` 4 模式 + `PMIC 5V <= 900 mA`）或 MI 闪光灯（仅限 Still 机械快门 `1/250 s` X-Sync、禁止 `>=250V`），对比 `FX6` 可切换 `TC IN/OUT` BNC 与**零物理 `GENLOCK` BNC**（尽管 `FX6 appFw.so` 休眠编译 `107` 个 `GENLOCK` 符号）。
   - **Check Group C（Wave 69 §§1–2：Still 专属 `Playback -> [Magnification]` + `[Anti-flicker Shoot.]` vs 100% 休眠 `[Var. Shutter]`/`[Anti-flicker Tv Scan]` vs FX6 `ECS`）**：[`evaluate_p341_check_group_c_pb_magnify_and_antiflicker`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py#L1133) 校验抗 Reset 的 `Playback -> [Magnification]`（`[Enlarge Image]` `0xe8cb`、`[Enlarge Initial Mag.]` `0x6b6e` `Standard. Mag.`/`Previous Mag.`、`[Enlarge Initial Position]` `0x781f` `Focused Position`/`Center`、索尼 ELF 错字 `playback_zoom_maginify_by_pinch`），强制**严格仅限静态照片**（对视频执行放大触发 `"You cannot enlarge movies."` / `playback_zoom::is_inhibition()` -> **`EOPNOTSUPP=95`**），对比 `FX6 Thumbnail / Rec Review` 与实时 `Focus Magnifier`；校验 Still 机械快门专属且可 Reset 的 `[Anti-flicker Shoot.]`（`0x623d`，仅 `100/120 Hz`，在 Movie/S&Q/Electronic Shutter/Silent Mode/BULB 锁定，对高频 PWM LED 无效），并拦截 100% 休眠的 `[Var. Shutter]`（`0x6831`）、`[Var. Shutter Set.]`（`0x6f9e`）、`[Anti-flicker Set.]`（`0x68e7`）与 `[Anti-flicker Tv Scan]`（`0x63c0` -> **`EOPNOTSUPP=95`**），对比 `FX6 ECS`（`23.99..8000 Hz`）。
   - **Check Group D（Wave 69 §§3–4 & Tier-0：双 SKU `Wi-Fi` / `p12/p13` RF NVS `MS_RDONLY` / 前面板 `#5` IR / 默认 `On` `[CTRL FOR HDMI]` CEC 劫持防护 & `16/16 H0 == H3`）**：[`evaluate_p341_check_group_d_wifi_ir_cec_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py#L1281) 校验 `backup_get_wi_fi_frequency_band_dst` 门控（`WW728473` 支持 2.4+5 GHz vs `WW558244` 锁定 2.4 GHz 单频 -> 请求 5 GHz 返回 `EOPNOTSUPP=95`）、Ver. 7.00+ 仅允许 `WPA2-PSK`/`WPA3-SAE`（拒绝已移除的 `WEP`/`WPA-PSK`/`IPsec`）、`[Reset Network Set.]` 保留 `[Airplane Mode]=On`、`[Camera Settings Reset]` 不复位网络菜单、`p12/p13` RF NVS `MS_RDONLY`（`rf_nvs_mutation_bytes=0`）与 `wireless_rf_packets_emitted=0`（对比 `FX6V` vs `FX6T` AP/Station Mode）；校验抗 Reset 的 `[IR Remote Ctrl]`（`0x61a6`）对应前面板 **`#5`** `Infrared remote sensor`（非 `#8` AF 辅助灯/自拍灯）、`ILME-FX3A` 硬件移除 IR 传感器、`IR` 与 `[Bluetooth Rmt Ctrl]` 互斥、`[IR Remote Ctrl]=On` 旁路 `[Power Save Start Time]`、FX3 零 `2.5mm LANC` 接口；强制校验抗 Reset 但**出厂默认 `On`** 的 `[CTRL FOR HDMI]`（`0xe41f`，`BKID_APP_setting_ctrl_for_hmdi`，暴露 `41` 个含 `STANDBY`/`MENU`/`EXIT` 但无 `CEC_REC` 的 `EVENT_INPUT_KEY_CEC_*` 劫持风险）在挂载 HDMI 台架时必须显式置 **`Off`**；并叠加双介质 `528 B FX3RCPT1`（不同 `st_dev`）`16/16 H0 == H3` 与 `emmc_write_count = 0` 红线门控。
3. **实测事实：CI 规则（递归剔除 `elapsed_seconds`、`work_root=None` 安全回退、4 模式 100 项单测、Milestone 324 双模与洁净度审计）全绿**：
   - `to_deterministic_json()` 与 `_canonical_sha256_dict()` 递归剔除全部 `elapsed_seconds` / `*_elapsed*` 计时键；`resolve_phase341_donor_file_or_none(None, ...)` 与显式不存在 `work_root` 均无报错回退 `CLEAN_ROOM_SYNTHETIC`（`0 B` 读取、`0` 固件字节泄漏）。
   - 新增 [`test_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py) 共 **100** 项单测（`>= 96`），在默认本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与无供体回退（`FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase341_missing` + `work_root=None`）4 种模式下全部 **100/100 OK**。
   - CLI `--help` 退出码 **`0`**（确认全部 `%%` 正确转义，含 `80%`、`90%` 与 `%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`）；默认未提供物理 Tier-0 回执返回 **`rc=2`**（`BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`）；`--simulate-bench-dry-run` 返回 **`rc=0`**（`DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`16/16 H0 == H3`）。
   - `make verify-milestone-324`（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模）均返回 `status=OK pillars=6/6`（`gate142=143/146 recovery=60/60 auditors=45/45 vm_stages=73/73 qemu=43/43(129/129) pngs=86/86(max=27467B) h0_eq_h3=16/16 leaked=0`），`make clean-audit` 返回 **`ALL GREEN`**（`0.05s`）。
4. **推断（非实测物理真机结论）**：
   - 以上 100 项单测、四态 CLI 指纹及 `--simulate-bench-dry-run` 仅证明宿主机只读模型、供体头检查与确定性 SHA-256 门控在离线与模拟回执条件下成立；真实 `ILME-FX3` 机台菜单交互与 Tier-0 物理双卡 `528 B FX3RCPT1` 校验仍待后续离线物理台架实测补齐（当前 `overall_ready_for_hardware_attach = False`、`emmc_write_count = 0`）。

---

## 2. 四态确定性报告指纹与实测命令回执

### 2.1 四态确定性 `report_sha256`（实测事实）

| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 退出码 | `O_RDONLY` 供体读取 | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `320 B` (`0.544 ms`) | `af54cc68030c1d6153236a7081587a2ae432768a35a7b0bdaf3f56fc8b10a6f0` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `320 B` (`0.406 ms`) | `09f8f6774feb07c27674a1d2a1bf4000612bc4118747e1579b3cfa45f657bb2a` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0 B` (`0.000 ms`) | `9f4b92f174496004b4ceb4f583ee713e02599709c46e3c31cca60e501e5b92d1` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0 B` (`0.000 ms`) | `0dd4e43cc45e199c761eaa4e797c4431c266054c46c952de588718f2be9f240a` |

### 2.2 本次交付与修改文件清单（严格 6 文件所有权）

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py)（新增，`2,200` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L3033)（导出全部 156 个 Phase 341 公共符号）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L5752)（接入 `preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec` CLI 子命令与参数解析）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L511)（新增 Section `# 60.`）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py)（新增，100 项四模式单测，`1,885` 行）
6. [`reports/2026-11-17-phase341-preflight18-area-date-grid-camset-mishoe-pbmagnify-wifi5ghz-cec/README.md`](./README.md)（本报告）

### 2.3 可复现验证命令（实测全部通过）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_area_date_dst_grid_cleanhdmi_camset_mishoe_pb_magnify_wifi_5ghz_and_cec_verifier.py"
CMD="preflight-area-date-dst-grid-cleanhdmi-camset-mishoe-pb-magnify-wifi-5ghz-and-cec"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase341_missing PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m unittest "$TEST"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --summary               # expect rc=2
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" /usr/bin/python3 -B -m fx6_closure "$CMD" --simulate-bench-dry-run --summary  # expect rc=0
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324
make clean-audit
```
