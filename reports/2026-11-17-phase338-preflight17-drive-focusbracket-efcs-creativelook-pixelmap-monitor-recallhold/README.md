# Phase 338 第 17 级物理台架准备度预检器工程报告（`preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc` / Waves 66–67）

## 1. 核心结论（Conclusion-First）

1. **实测事实：Waves 66–67 四大 `ILME-FX3 Ver. 7.02`（`ilc/2210`，Model `0x91030080`）vs `ILME-FX6`（`Ver. 6.01`）物理台架检查组（`Check Group A..D`）全部落地闭环**：
   - 在 `outputs/fx6-on-fx3-closure/` 新增第 17 级宿主机侧只读物理台架与实拍前准备度预检器 [`realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py)（Schema `realhw_preflight17_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_hdmi_tc_v1`，版本 `phase338_v1`，CLI 子命令 `preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc`，共 `2,509` 行），将 17 级预检链路推进至 `Ph186 -> Ph204 -> Ph216 -> Ph227 -> Ph248 -> Ph261 -> Ph275 -> Ph279 -> Ph284 -> Ph291 -> Ph302 -> Ph307 -> Ph316 -> Ph321 -> Ph329 -> Ph334 -> Ph338`。
   - 全部公共符号已在 [`fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L2888) 导出，CLI 子命令与全部参数（含 `argparse` `help=` 字符串 `%%` 转义）已接入 [`fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L5499)，并在 [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L506) 新增 `# 59.` 文档条目。
2. **实测事实：Check Groups A–D 关键硬件/固件契约、官方错别字指纹、休眠辟谣与 Slot-1 `EROFS=30` 防火墙全部 fail-closed 实现**：
   - **Check Group A（Wave 66 §§1–2：Drive Mode / 休眠 Focus Bracket / 2 选 Shutter Type / EFCS / Long Exp & High ISO NR vs FX6 APR）**：[`evaluate_p338_check_group_a_drive_focusbracket_shutter_efcs_and_nr`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py#L783) 校验 Still 专属且可 Reset 的 `[Drive Mode]`（`_f 0x7228`，Movie/S&Q 下 `EOPNOTSUPP=95`）：`Single Shooting`、`Cont. Shooting`（`Hi+ 10fps / Hi 8fps / Mid 6fps / Lo 3fps`；`> F11` 在 `Hi+/Hi/Mid` 首帧锁焦；`Uncompressed RAW` 或闪光灯降速）、`Self-timer(Single)`（`10/5/2 s`）、`Self-timer(Cont)`（`6` 组）、`Cont./Single/WB/DRO Bracket`（`HLG Still=On` 锁定 `DRO Bracket`）与 `[Interval Shoot Func.]`（默认 `Electronic Shutter`）；**100% 辟谣休眠 `[Focus Bracket]`**（`BKID_APP_setting_focus_bracket_*` 与 `0x7563/0x6915` 在 `FX3 appFw.so` 中休眠，`ilc/2210` `0` 命中，与 Wave 54 交叉印证，FX3 & FX6 双端 `EOPNOTSUPP=95`）；强制 `[Shutter Type]` 仅 `2` 选项（`Mechanical Shutter` / `Electronic Shutter`，**无 `Auto`**，休眠 `0x66b8`）、单一 `1/250 s` X-Sync 上限（`1/320` `0` 命中）与电子/静音快门 `5` 项互斥；校验抗 `[Camera Settings Reset]` 的 `[e-Front Curtain Shut.]`（索尼 ELF 拼写错字 `BKID_APP_setting_front_curtaion_shutter`）、`>= 1 s` `[Long Exposure NR]` 与 `3` 选 JPEG/HEIF 专属 `[High ISO NR]`（`Normal/Low/Off`，绝不改写 `.ARW`），对比 FX6 `Noise Suppression` 与 `Technical > APR`。
   - **Check Group B（Wave 66 §§3–4：Creative Look 10+6 & 0..9 非对称参数 / 休眠 Soft Skin / Delete, Protect & Recover Image DB Slot-1 `EROFS=30`）**：[`evaluate_p338_check_group_b_creativelook_softskin_and_recoverdb`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py#L1059) 校验 `[Creative Look]` `10` 预设（`ST..SE`）+ `Custom Look 1..6`（映射 ELF `look0..look15`）及 `8` 参数精确边界（`Contrast/Highlights/Shadows/Saturation` `-9..+9`、**`Fade/Sharpness/Clarity` 非对称 `0..9`**、`Sharpness Range` `1..5`），执行 `BW/SE` 锁 `Saturation`、Movie/S&Q 锁 `Sharpness Range`、`PP != Off` / `Log != Off` / `HLG Still = On` / `iAuto` 锁为 `[-]`；拦截 FX3 & FX6 双端休眠 `[Soft Skin Effect]`（`0x76d9`，`BKID_APP_setting_soft_skin_effect` -> `EOPNOTSUPP=95`）；校验 Playback `[Delete]`（`0xe504` `5` 范围，Movie+Proxy 协同删除，跳过受保护文件）、Reset-immune `[Delete confirm.]`/`[Delete pressing twice]`、`[Protect]`（`0xe2c9`，`Copy` 不保留保护），并对改写 `AVF_INFO` 的 `[Recover Image DB]`（`0x711b`，电量门槛 `>= 20%`，抗 Reset 与 Initialize）及 `Slot-1` 写操作实施 `EROFS=30` 防火墙，对比只读 `[Display Media Info.]`（`0xea2a`，`40,000` 静态张数上限，`NOT_DISPLAYNG` 错字）。
   - **Check Group C（Wave 67 §§1–2：Auto/Manual Pixel Mapping / Silent Shutdown Click / Myth-Busting `Setup -> [Monitor]` & Dormant EVF vs FX6）**：[`evaluate_p338_check_group_c_pixelmap_apr_monitor_and_evf`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py#L1261) 校验 Reset-immune `Setup -> [Setup Option] -> [Auto Pixel Mapping]`（`0x7734`）与手动 `[Pixel Mapping]`（`0x61f7`，镜头盖+电量门控+强制重启+索尼 ELF 错字 `pixel_mappinng` / `excuted`+`0` 个 `PRM_HAITA` USB 阻断）；校验 Resettable `Silent Mode -> Target Function Settings -> [Auto Pixel Mapping]`（默认 `Off`，置 `On` 时关机触发机械快门声 `vdf_set_shutter_mute_by_pixel_mapping`），对比 FX6 `Technical > APR > Execute` 与休眠 `auto_black_balance`；**辟谣 `Setup -> [Monitor]`（而非 `[Finder/Monitor]`）** 精确 `3` 个 Reset-immune 项（`Monitor Brightness`、`Display Quality` 高温 `High -> Standard` 降档、`Monitor Flip Direction`，不含 `[Bright Monitoring]`）并拦截休眠 EVF 菜单（`EOPNOTSUPP=95`）与 FX6 四子项 `VF Adjust` 误判（FX6 为 `VF Setting` + 硬件 `MIRROR` 开关）。
   - **Check Group D（Wave 67 §§3–4 & Tier-0：Still `P/A/S/M`-Only `[Recall Custom hold 1-3]` 11 槽零 WB / `[External Output]` & `Slot-1 EROFS=30` & `16/16 H0 == H3`）**：[`evaluate_p338_check_group_d_recallhold_hdmi_tc_and_tier0`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py#L1522) 强制 `[Recall Custom hold 1-3]`（`0x60b4/0x7581/0x725b`，Reset-immune，`CAMSET/*.DAT`）**严格仅限 Still `P/A/S/M`**（Movie/S&Q/iAuto 报 `EOPNOTSUPP=95`）、精确 `11` 槽位（`is_checked_recall_custom_hold0..10`）且**零独立 `White Balance` 复选框**（`shoot_set_registration_white_balance` `0` 命中），对比 FX6 `Push AF / Push AGC / Push Auto Iris`；校验 Reset-immune `Setup -> [External Output]`（`S&Q` 锁定 `Rec. Media dur HDMI Output=On`、`Log`/`PPLUT1..4`+内录钳位 `1080`、`24.00p` 强制重启与回放隔离、`REC Control` 强制依赖 `Time Code Output=On`、`HDMI Info. Display` 在 RAW/`Off(HDMI Only)` 下强制 `Off`、`[CTRL FOR HDMI]` ELF 错字 `BKID_APP_setting_ctrl_for_hmdi`、休眠 `4K/2K` 与 `24p/60p Output` `EOPNOTSUPP=95`），并对开启内录指向 `Slot 1` 的情形实施 `EROFS=30` 防火墙，叠加 `16/16 H0 == H3`、`528 B FX3RCPT1` 双介质回执（不同 `st_dev`）与 `emmc_write_count = 0` 红线门控。
3. **实测事实：CI 规则（递归剔除 `elapsed_seconds`、`work_root=None` 安全回退、4 模式 100 项单测、Milestone 324 双模与洁净度审计）全绿**：
   - `to_deterministic_json()` 与 `_canonical_sha256_dict()` 递归剔除全部 `elapsed_seconds` / `*_elapsed*` 计时键；`resolve_phase338_donor_file_or_none(None, ...)` 与显式不存在 `work_root` 均无报错回退 `CLEAN_ROOM_SYNTHETIC`（`0 B` 读取、`0` 固件字节泄漏）。
   - 新增 [`test_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py) 共 **100** 项单测，在默认本地供体、`FX3_CLEAN_ROOM_TEST=1`、`FX3_FX6_FORCE_CLEAN_ROOM=1` 与无供体回退（`FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase338_missing` + `work_root=None`）4 种模式下全部 **100/100 OK**。
   - CLI 默认未提供物理 Tier-0 回执返回 **`rc=2`**（`BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`），`--simulate-bench-dry-run` 返回 **`rc=0`**（`DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`，`16/16 H0 == H3`）。
   - `make verify-milestone-324`（`LOCAL_DONOR_O_RDONLY` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1` 双模）均返回 `status=OK pillars=6/6`（`gate142=143/146 recovery=59/59 auditors=45/45 vm_stages=72/72 h0_eq_h3=16/16 leaked=0`），`make clean-audit` 返回 **`ALL GREEN`**。
4. **推断（非实测物理真机结论）**：
   - 以上 100 项单测、四态 CLI 指纹及 `--simulate-bench-dry-run` 仅证明宿主机只读模型、供体头检验与确定性 SHA-256 门控在离线与模拟回执条件下成立；真实 `ILME-FX3` 机台菜单交互与 Tier-0 物理双卡 `528 B FX3RCPT1` 校验仍待后续离线物理台架实测补齐（当前 `overall_ready_for_hardware_attach = False`、`emmc_write_count = 0`）。

---

## 2. 四态确定性报告指纹与实测命令回执

### 2.1 四态确定性 `report_sha256`（实测事实）

| 验证模式（`verification_mode`） | 模拟开关（`simulate_bench_dry_run`） | 总体状态（`overall_status`） | Go/No-Go 裁决（`go_no_go`） | CLI 退出码 | `O_RDONLY` 供体读取 | 确定性 `report_sha256` |
| :--- | :---: | :--- | :--- | :---: | :---: | :--- |
| `LOCAL_DONOR_O_RDONLY` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `320 B` (`0.928 ms`) | `e14db2d009e9be3dc2219dd25849e337c47d957bdc39a7c6c8f06ae429703986` |
| `LOCAL_DONOR_O_RDONLY` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `320 B` (`0.758 ms`) | `b895428bfec30bc6f4bff73e0331a5c687883322fd418b4d39d1b0ecb92358e8` |
| `CLEAN_ROOM_SYNTHETIC` | `False` | `READY_OFFLINE_AWAITING_BENCH_RECEIPTS` | `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` | `2` | `0 B` (`0.001 ms`) | `3cecf4f1294f38b462d65320be8f35802af33b5a64f7205c0df650b6cdc46a4c` |
| `CLEAN_ROOM_SYNTHETIC` | `True` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH` | `0` | `0 B` (`0.001 ms`) | `ed4a4065cdbb0f4818e4c180a47d3fc6ca98ae1abe06f361bb3614431e3b6e4c` |

### 2.2 本次交付与修改文件清单（严格 6 文件所有权）

1. [`outputs/fx6-on-fx3-closure/fx6_closure/realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py)（新增，`2,509` 行）
2. [`outputs/fx6-on-fx3-closure/fx6_closure/__init__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__init__.py#L2888)（导出全部 Phase 338 公共符号）
3. [`outputs/fx6-on-fx3-closure/fx6_closure/__main__.py`](../../outputs/fx6-on-fx3-closure/fx6_closure/__main__.py#L5499)（接入 `preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc` CLI 子命令与参数解析）
4. [`outputs/fx6-on-fx3-closure/README.md`](../../outputs/fx6-on-fx3-closure/README.md#L506)（新增 Section `# 59.`）
5. [`outputs/fx6-on-fx3-closure/tests/test_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py`](../../outputs/fx6-on-fx3-closure/tests/test_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py)（新增，100 项四模式单测，`1,927` 行）
6. [`reports/2026-11-17-phase338-preflight17-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold/README.md`](./README.md)（本报告）

### 2.3 可复现验证命令（实测全部通过）

```sh
PP="outputs/fx6-on-fx3-closure:outputs/fx3-safety:outputs/fx3-recovery-adapter:outputs/fx3-firmware-lab:outputs/fx3-vm"
TEST="outputs/fx6-on-fx3-closure/tests/test_realhw_drive_focusbracket_efcs_creativelook_pixelmap_monitor_recallhold_and_hdmi_tc_verifier.py"
CMD="preflight-drive-focusbracket-efcs-creativelook-pixelmap-monitor-recallhold-and-hdmi-tc"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -B -m unittest "$TEST"
FX3_CLEAN_ROOM_TEST=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -B -m unittest "$TEST"
FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -B -m unittest "$TEST"
FX3_FX6_MAC_WORK_ROOT=/nonexistent/phase338_missing PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -B -m unittest "$TEST"

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -B -m fx6_closure "$CMD" --summary               # expect rc=2
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PP" python3 -B -m fx6_closure "$CMD" --simulate-bench-dry-run --summary  # expect rc=0
PYTHONDONTWRITEBYTECODE=1 make verify-milestone-324
PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-324
make clean-audit
```
