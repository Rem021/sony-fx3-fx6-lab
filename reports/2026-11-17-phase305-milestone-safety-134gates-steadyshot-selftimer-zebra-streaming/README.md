# Phase 305（305th Phase Milestone）：Wave-57 实机硬件安全门禁 `G133` & `G134` 与统一 `134/134` 预检引擎交付报告

- **日期**：`2026-11-17`
- **任务**：Task H359 — Phase 305 Wave-57 Hardware Safety Gates `G133` & `G134` + Unified `verify-134-gates` (`134/134`)
- **严格六文件交付范围**：
  1. 新增核心守卫模块：[`realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py)
  2. 更新包导出与 Milestone 295 自动发现入口：[`__init__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/outputs/fx3-safety/fx3_safety/__init__.py)
  3. 注册 CLI 子命令（含 `--json` 与 `--simulate-bench-dry-run`）：[`__main__.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/outputs/fx3-safety/fx3_safety/__main__.py)
  4. 新增文档第 67 节：[`README.md`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/outputs/fx3-safety/README.md)
  5. 新增 86 项双模式/三环境变量单元测试：[`test_realhw_steadyshot_selftimer_zebra_streaming_134gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/outputs/fx3-safety/tests/test_realhw_steadyshot_selftimer_zebra_streaming_134gate_guard.py)
  6. 本工程报告：`reports/2026-11-17-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/README.md`

---

## 核心结论（Executive Summary）

1. **已将实验室实机安全门禁总账从 `132/132` 推进并收口至 `134/134`（Phase 305）**：
   - 离线默认模式（[`evaluate_134gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py) / `verify-134-gates`）：**`131/134` 门禁通过**（`VERIFIED_131_OF_134_AWAITING_PHYSICAL_TIER0`，仅物理 Tier-0 备份回执 `G10..G12` 待人工台架接入），在 `LOCAL_DONOR_O_RDONLY` 与 `CLEAN_ROOM_SYNTHETIC`（`FX3_FX6_FORCE_CLEAN_ROOM=1`）下均实测通过。
   - 模拟演练模式（`--simulate-bench-dry-run`）：**`134/134` 门禁全绿通过**（`VERIFIED_ALL_134_GATES_DRY_RUN_SIMULATED_BACKUP`）。
   - **Milestone 295 动态自动发现实测确认**：`make verify-milestone-295` 与 `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` 自动发现最高入口 `evaluate_134gate_preflight`，输出 `gate124=131/134`、`pillars=6/6`、`auditors=45/45`、`vm_stages=61/61`、`qemu=33/33(99/99)`。
2. **所有硬核安全红线保持永久锁死**：
   - `overall_ready_for_hardware_attach = False`、`hardware_live_attachment_authorized = False`、`agent_auto_flash_blocked = True`、`persistent_emmc_writes_authorized = False`、`persistent_write_release = False`、`el3_payload_transmit_authorized = False`、`spi_nor_write_authorized = False`、`cross_model_flash_authorized = False`、`usb_packets_transmitted = 0`、`raw_firmware_bytes_leaked = 0`。
3. **测试全量实测通过**：
   - Phase 305 新增 **86 项单元测试**（`>= 84` 要求）在 **默认 (`LOCAL_DONOR_O_RDONLY`)**、**`FX3_CLEAN_ROOM_TEST=1`**、**`FX3_FX6_FORCE_CLEAN_ROOM=1`** 三种模式下全部 `86/86 OK`。
   - `outputs/fx3-safety` 全量单元测试发现共 **3,665 项测试**全部 `OK`。
   - `make clean-audit`（`scripts/run_all_lab_tests.py --clean-only`）审计 **`ALL GREEN`**。

---

## 一、实测事实 vs 推断边界（Strict Fact / Inference Separation）

| 类别 | 具体内容 | 证据来源 |
| :--- | :--- | :--- |
| **实测事实（Donor 只读 `os.O_RDONLY` + `os.pread`）** | `FX3 appFw.so`（`79,015,712 B`，50 组定界切片 `sha256: b8e2365f...`）含 `BKID_APP_setting_{movie_steadyshot,still_steadyshot,steadyshot_adjustment,steady_focal_length}`、精确 **47 档** `STEADYSHOT_FOCAL_LENGTH_{8..1000}MM`、`VAL_setting_de_squeeze_disp_DE_SQUEEZE_DISP_1_3X`、休眠 `BKID_APP_setting_movie_self_timer*` / `MOVIE_STEADYSHOT_EXTENSIONS_HYBRID`、`Zebra` Custom 1/2、`Peaking`、`Network Streaming`（仅 `60/50/30/25` 帧率）、`Airplane Mode`。 | [Wave-57 情报报告](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/reports/2026-11-17-global-sony-wave57-steadyshot-ibis-movie-selftimer-custom-zebra-streaming-intel/README.md) & [`audit_phase305_donor_contracts`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py) |
| **实测事实（FX6 ELF 与 4 语 UXC）** | `FX6 appFw.so`（`50,520,424 B`，15 组定界切片 `sha256: c459c4ed...`）含 `TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`、`VAL_HAITA_steadyshot_equip_with_body_setting_ratio_hdmi_vf_NOT_SET`、`VAL_setting_ratio_hdmi_vf_RATIO_HDMI_VF_{1_3X..2_0X}`、`VAL_setting_infra_zebra_display_ZEBRA_DISPLAY_{OFF,ZEBRA1,ZEBRA2}`、`BKID_APP_SETTING_{PICTURE_CACHE_REC,INTERVALTIME_INTERVAL_REC}` 及休眠 `BKID_APP_{RTMP,SRT}_SETTINGS1`。FX3 四语（EN/ZH-CN/ZH-TW/JA）`_f.uxc` / `.uxc` / `_g.uxc` 与 `FX3-CX95900_ALLLANG-Backup.bin` SHA-256 与标记全数校验一致。 | 11 项只读 donor 审计 |
| **推断（工程化安全护栏与台架策略）** | Movie `[Active]` ~`1.104x` 视角裁切测算；`S-Log3`（18% 灰=`41%`、90% 白=`61%`、高光裁切`~94%` IRE）及 `[Display LUT]=On` 切换至 LUT 后显示测量的工程边界；台架 `[Airplane Mode]=On` 零射频（仅放行 `USB-LAN`）与 `Slot-1` Tier-0 恢复保险库 `EROFS=30`/`EBUSY=16` 防写防火墙规则。 | [`verify_steadyshot_and_selftimer_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py) & [`verify_zebra_peaking_streaming_firewall_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h359-phase305-milestone-safety-134gates-steadyshot-selftimer-zebra-streaming/outputs/fx3-safety/fx3_safety/realhw_steadyshot_selftimer_zebra_streaming_and_134gate_guard.py) |

---

## 二、Gate `G133` & `G134` 核心门禁设计摘要

### 1. Gate `G133`（`SteadyShot` 5 轴 IBIS 四重 `Active` 互斥锁、47 档焦距表与 `Self-timer` 静动态分离）
- **4 条件 Movie `[Active]` 锁死矩阵**：当满足以下任一条件时，禁止强制开启 Movie `[SteadyShot] = Active`（`EOPNOTSUPP = 95`，自动降级至 `Standard` 并解除 `Distortion Comp. = Auto` 强绑）：
  1. Movie `[Rec Frame Rate] >= 119.88p / 100p`
  2. `S&Q` `[Frame Rate] >= 120fps / 100fps`
  3. `HDMI RAW Output = On`
  4. `[De-Squeeze Display]` 处于 `1.3x / 1.5x / 1.6x(1.65x) / 1.8x / 2.0x`
- **休眠模式与跨机型纠偏**：
  - 拒绝休眠 `[Dynamic active]`（`_f 0x741c` / `MOVIE_STEADYSHOT_EXTENSIONS_HYBRID`，`EOPNOTSUPP=95`）。
  - 校验精确 **47 档 `[Focal Length]` 表（`8mm..1000mm`）** 并对比无机身 IBIS 的 `ILME-FX6`（`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED` + 启用 Catalyst 需关闭镜头 OSS）。
  - 拒绝休眠 Movie `[Self-timer]`（`BKID_APP_setting_movie_self_timer` / `_f 0x7192 Rec Start delay` / `Single Burst` / `Self-portrait 3-sec` -> `EOPNOTSUPP=95`），放行 Still-only `[Self-timer(Single)]`（`10/5/2 sec`）、6 档 `[Self-timer(Cont)]`（`10/5/2 Sec. × 3/5 Img.`）与 `[Selftimer during Bracket]`（`Off/2/5/10 Sec`）。
  - 校验前部硬件模块 **#8**（与红色前端 REC 指示灯物理分离）与 `Initialize`-only `[Audio signals]`（在 `[Silent Mode]=On` 或 Movie HDMI 音频输出下自动静音抑制，拒绝休眠 `Audio Signal Volume`）。
  - 全量枚举矩阵 `compute_steadyshot_selftimer_matrix()`：**1,296 状态**全部不变量成立。

### 2. Gate `G134`（`Zebra` Custom 1/2、4 色峰值、RTMP/RTMPS/SRT 推流与零射频 / `Slot-1` 保险库双防火墙）
- **FX3 Zebra & Peaking vs FX6 三选一**：
  - 校验 FX3 `70..100+` 预设、`Custom1`（`Std+Range 0..109% ± 1..10%`）与 `Custom2`（`Lower Limit 0..109+`），S-Log3 锚点（`41%` / `61%` / `~94%`，拒绝 `107+` 误区），`[Display LUT] = On` 时斑马切换为 LUT 后显示测量；4 色 `[Peaking]`（`Red/Yellow/Blue/White`）；全部仅限 `[Initialize]` 重置，且严格与干净 HDMI 输出隔离。
  - 严格限制 FX6 `Monitoring > Zebra > Setting` 为 **`Off / Zebra1 / Zebra2`** 三选一单选开关（拒绝同时叠加 `Both` 幻觉！Aperture `2..20%`），FX6 Peaking 为 `B&W / Red / Yellow / Blue`。
- **`[Network Streaming]` & `[FTP Transfer Func.]`**：
  - 校验 `RTMP / RTMPS / SRT` 与 `4K / 2K / HD(1080p) / HD(720p)` `@ 59.94p / 50p / 29.97p / 25p`（拒绝 `23.98p / 24p` 及 `> 38.0 Mbps`）；在 `4K` 或 `2K 59.94p/50p` 推流期间封锁机内 `4K` 同录并锁死 `Rec Frame Rate = streaming_frame_rate`。
  - 校验 `[Reset Network Set.]` 保留 `[Airplane Mode] = On`，拒绝 FX6 休眠 QoS/RTMP/SRT 符号。
- **台架关键双防火墙**：
  - **Zero-RF Firewall**：`[Airplane Mode] = On` + `p12/p13` RF NVS 只读锁死，拦截一切 `Wi-Fi / BLE` 无线 TX（`wireless_packets_emitted == 0`、`rf_nvs_p12_p13_writes_permitted == False`），仅放行有线 `USB-LAN` / `USB Tethering`。
  - **`Slot-1` Tier-0 Vault Firewall**：拦截 `[Movie Rec During Streaming] = Enable` 指向 `Slot 1` 的机内录制与 `Slot 1` FTP 标记写入，fail-closed 返回 `EROFS (30)` / `EBUSY (16)`，确保 `slot1_data_sector_writes == 0` 且 `slot1_avf_info_mutated == False`。
  - 全量枚举矩阵 `compute_zebra_peaking_streaming_matrix()`：**576 状态**全部不变量成立。

---

## 三、端到端实测验证日志

| 验证项 | 命令 | 实测结果 |
| :--- | :--- | :--- |
| **Phase 305 单元测试（Donor 只读模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_steadyshot_selftimer_zebra_streaming_134gate_guard.py` | **86/86 OK** (`9.270s`) |
| **Phase 305 单元测试（`FX3_CLEAN_ROOM_TEST=1`）** | `PYTHONDONTWRITEBYTECODE=1 FX3_CLEAN_ROOM_TEST=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_steadyshot_selftimer_zebra_streaming_134gate_guard.py` | **86/86 OK** (`3.548s`) |
| **Phase 305 单元测试（`FX3_FX6_FORCE_CLEAN_ROOM=1`）** | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest outputs/fx3-safety/tests/test_realhw_steadyshot_selftimer_zebra_streaming_134gate_guard.py` | **86/86 OK** (`3.590s`) |
| **`verify-134-gates` 离线 & Dry-Run（Donor 模式）** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-134-gates [--simulate-bench-dry-run] --summary --json` | 离线 **`131/134`**（`VERIFIED_131_OF_134_AWAITING_PHYSICAL_TIER0`）；Dry-Run **`134/134`**（`VERIFIED_ALL_134_GATES_DRY_RUN_SIMULATED_BACKUP`） |
| **`verify-134-gates` 离线 & Dry-Run（`FX3_FX6_FORCE_CLEAN_ROOM=1`）** | `PYTHONDONTWRITEBYTECODE=1 FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety python3 -B -m fx3_safety verify-134-gates [--simulate-bench-dry-run] --summary --json` | 离线 **`131/134`**；Dry-Run **`134/134`**，`mode=CLEAN_ROOM_SYNTHETIC` |
| **`outputs/fx3-safety` 全量单元测试发现** | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=outputs/fx3-safety python3 -B -m unittest discover -s outputs/fx3-safety/tests` | **3,665/3,665 OK** (`176.274s`) |
| **Milestone 295 主控联合门禁（Donor + Clean-Room）** | `make verify-milestone-295` & `FX3_FX6_FORCE_CLEAN_ROOM=1 make verify-milestone-295` | **ALL OK**：自动发现 `evaluate_134gate_preflight`，`gate124=131/134`、`pillars=6/6`、`recovery=53/53`、`auditors=45/45`、`vm_stages=61/61`、`leaked=0` |
| **Clean-Room 卫生审计** | `make clean-audit` (`scripts/run_all_lab_tests.py --clean-only`) | **`ALL GREEN`** (`1.71s`) |
