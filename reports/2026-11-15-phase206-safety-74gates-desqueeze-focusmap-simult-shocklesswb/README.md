# Phase 206（Task H227）实机安全护栏报告：`G73`（`[De-Squeeze Display]` `1.6x=1.65x` 四项硬锁定 + 外置 `M&C Focus Map` `<150fps` 截止）+ `G74`（`[Simult. + Auto Switch]` 双槽冗余一致性 + `[Shockless WB]` 零帧直通）+ `verify-74-gates` 总控预检

## 1. 结论先行

已在 `outputs/fx3-safety/` 完成 **Phase 206（Safety Gates `G73` & `G74` + `verify-74-gates` Master Guard）** 端到端实现与双模式（本地 `os.O_RDONLY` Donor 审计 + `FX3_FX6_FORCE_CLEAN_ROOM=1` 无固件洁净室）验证，同时保持 `verify-58-gates` 至 `verify-72-gates` **100% 向后兼容通过**：

- **Gate `G73`（[`evaluate_g73_desqueeze_focusmap_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h227-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/outputs/fx3-safety/fx3_safety/realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard.py#L1832-L1907)）**：精确校验 `ILME-FX3`（`Ver. 7.02`）`[De-Squeeze Display]`（`Off / 1.3x / 2.0x / 1.5x / 1.6x`，其中菜单 `[1.6x]` 实测水平拉伸倍率为 **`1.65x`** 还原 `2.39:1` CinemaScope）、开启时的 **4 项机身硬锁定**（`[Focus Mode]=Manual Focus`、`[Focus Area]=Wide`、`[SteadyShot]=Off`、`[Face Priority in Multi Metering]=Off`）、5 类自动抑制退回 `1.0x` 场景（`[RAW Output]=On`、`[Off(HDMI Only)]` 且强制 `[HDMI Info. Display]=Off`、`[Log Shooting]=Off`、`[Remote Shooting]`、`Still`），并严禁 Stage-B 伪造 `FX3` 机内本地 `[Focus Map]` 菜单/OSD 叠加层及阻断 `>=150fps` / 转接环 / 非 PDAF 镜头 / 回放态下的外置 `M&C` `Focus Map`。
- **Gate `G74`（[`evaluate_g74_simult_autoswitch_shocklesswb_guard`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h227-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/outputs/fx3-safety/fx3_safety/realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard.py#L1910-L1985)）**：在要求双卡冷备/严格冗余一致性（`strict_dual_vault_parity_required=True`）时强制锁定 `[Simult. Recording]` + **`[Auto Switch Media]=Off`**（阻断 `Ver. 2.00+` `[Auto Switch Media]=On` 单卡写满后静默退化为单卡录制的冗余丢失风险），并校验全帧率（`1..240fps`）`[Shockless WB]`（`Off / 1 / 2 / 3`）及 `[C.Temp./Filter]` 色温 K 值直改、`A-B / G-M` 微调网格偏移的 **`0` 帧立即生效旁路（Immediate Bypass）**。
- **74-Gate 总控预检（[`evaluate_74gate_preflight`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h227-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/outputs/fx3-safety/fx3_safety/realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard.py#L1993-L2413) / `verify-74-gates`）**：默认离线 `71/74`（`G10..G12` 物理 Tier-0 冷备待实机挂载），`--dry-run-simulated` 演练 `74/74`，全部物理烧录与总线发射红线硬锁定为只读零副作用（`overall_ready_for_hardware_attach = False`、`persistent_emmc_writes_authorized = False`、`spi_nor_write_authorized = False`、`el3_payload_transmit_authorized = False`、`agent_auto_flash_blocked = True`、`physical_usb_packets_emitted = 0`、`raw_firmware_bytes_leaked = 0`）。

---

## 2. 交付文件清单（严格限定 6 个归属文件）

1. [realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h227-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/outputs/fx3-safety/fx3_safety/realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard.py) — Phase 206 核心模块（只读 `os.O_RDONLY` Donor 契约审计、`Gate G73`、`Gate G74` 及 `evaluate_74gate_preflight`）。
2. [__init__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h227-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/outputs/fx3-safety/fx3_safety/__init__.py) — 导出 `G73`、`G74`、`Master74GateReport`、`evaluate_74gate_preflight` 等符号。
3. [__main__.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h227-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/outputs/fx3-safety/fx3_safety/__main__.py) — 接入 `verify-g73-desqueeze-focusmap`、`verify-g74-simult-autoswitch-shocklesswb`、`verify-74-gates`（支持 `--force-clean-room`、`--dry-run-simulated`、`--json`）。
4. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h227-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/outputs/fx3-safety/README.md) — 新增第 37 节文档说明 Phase 206 `G73`/`G74` 与 `verify-74-gates`。
5. [test_phase206_desqueeze_focusmap_simult_shocklesswb_74gate_guard.py](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h227-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/outputs/fx3-safety/tests/test_phase206_desqueeze_focusmap_simult_shocklesswb_74gate_guard.py) — 56 项双模式快速单元测试（含 `< 6.0s` 墙钟上限断言与 `58..72` 门向后兼容回归）。
6. [README.md](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h227-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/reports/2026-11-15-phase206-safety-74gates-desqueeze-focusmap-simult-shocklesswb/README.md) — 本报告。

---

## 3. 实测事实 vs 工程契约边界

| 维度 | 实测事实（Sony 官方规范 & 本地只读 Donor 验证） | Phase 206 护栏裁决策略 |
| :--- | :--- | :--- |
| `[De-Squeeze Display]` 倍率 | `FX3 Ver. 7.00+` 新增 `1.5x` 与 `1.6x`，菜单 `[1.6x]` 实际执行 **`1.65x`** 水平拉伸；`cpapp-b.bin` 实测含 `DeSqueeze`/`Squeeze`/`Focus`/`HDMI`/`RAW`/`WB`/`Media`/`Auto` 字符串标记 | 宣称 `1.6x -> 1.60x` 或固件 `< 7.00` 开启 `1.5x/1.6x` 立即 `BLOCKED_G73_DESQUEEZE_MENU_OR_FACTOR_MISMATCH` |
| 四项变形宽银幕硬锁定 | `[De-Squeeze Display] != Off` 且未自动抑制时，实机强制 `Manual Focus`、`Wide`、`SteadyShot=Off`、`Face Priority in Multi Metering=Off` | 任一未满足即 `BLOCKED_G73_DESQUEEZE_4_LOCK_VIOLATION` |
| `ILME-FX3` `Focus Map` 形态 | `FX3`（`Ver. 6.00..7.02`）无任何机内 `[Focus Map]` 菜单与本地 LCD/HDMI 景深渲染层，仅向外部 `M&C` 输出 PDAF 景深流且在 `>=150fps` 硬切断（`<=6fps` 下限仅属 `FX6`） | 伪造机内菜单/Stage-B 本地叠加报 `BLOCKED_G73_IN_BODY_FX3_FOCUS_MAP_FORBIDDEN`；`>=150fps` / 转接环 / 非 PDAF / 回放报 `BLOCKED_G73_EXTERNAL_FOCUS_MAP_CUTOFF_VIOLATION` |
| `Simult.` + `Auto Switch Media` | `Ver. 2.00+` 双卡同录叠加 `Auto Switch Media=On` 在单槽写满后静默降级为单卡录制 | 严格双卡冗余模式强制 `Auto Switch Media=Off`，违者报 `BLOCKED_G74_STRICT_DUAL_VAULT_REQUIRES_SIMULT_AUTOSWITCH_OFF` |
| `[Shockless WB]` 直通物理 | `Off/1/2/3` 在预设切换时平滑过渡，但直接修改 `[C.Temp./Filter]` K 值或 `A-B / G-M` 微调网格均绕过平滑、`0` 帧立即跳变 | 宣称 K 值直改或 `A-B/G-M` 偏移存在非零平滑帧立即报 `BLOCKED_G74_SHOCKLESS_WB_KELVIN_GRID_BYPASS_VIOLATION` |

---

## 4. 验证结果汇总

已在工作树使用 `/usr/bin/python3 -B` 全量通过以下 6 组定向与全仓回归验证（零 `.pyc` / `__pycache__` 污染，零专有固件字节泄漏）：

- `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m fx3_safety verify-74-gates --json | head -n 35` -> `VERIFIED_71_OF_74_AWAITING_PHYSICAL_TIER0`（`--dry-run-simulated` 为 `74/74`）。
- `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase206_desqueeze_focusmap_simult_shocklesswb_74gate_guard.py` -> **56 tests OK**（实测 `3.718s`，低于 `6.0s` 墙钟上限）。
- `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest outputs/fx3-safety/tests/test_phase206_desqueeze_focusmap_simult_shocklesswb_74gate_guard.py` -> **56 tests OK**（`CLEAN_ROOM_SYNTHETIC`，实测 `2.423s`）。
- `PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` -> 全量 `fx3-safety` **1507 tests OK**。
- `FX3_FX6_FORCE_CLEAN_ROOM=1 PYTHONPATH=outputs/fx3-safety /usr/bin/python3 -B -m unittest discover -s outputs/fx3-safety/tests -p "test_*.py"` -> 全量洁净室模式 **1507 tests OK**（`skipped=1`）。
- `/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only` -> 全实验室洁净测试 **ALL GREEN**。
