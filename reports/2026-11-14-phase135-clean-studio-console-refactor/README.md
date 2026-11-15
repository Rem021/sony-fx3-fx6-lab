# Phase 135 — Clean Camera Studio Console UI Refactor & Pure Native Screen Mode

> **Phase 135 — Clean Camera Studio Console UI Refactor (`HTML_UI`), Default-Collapsed 6-Category Advanced Engineering Lab Drawer (`#studio-advanced-lab-drawer`), Zero `Phase XX` / `(/api/...)` Visual Clutter, & Pure Native Screen Mode (`bit 30 = 0x40000000` on `p40_flags_word`, `/api/studio_screen_mode`)**

- **日期 / Date**: 2026-11-14
- **任务分支 / Branch**: `codex/h143-phase135-clean-studio-console-refactor`
- **隔离实机验证端口 / Isolated Live Port**: `http://127.0.0.1:18785/`（`--workdir /private/tmp/fx6_p135_trial_18785 --no-browser`，验证完成后已干净停止并清理临时目录；默认端口 `8768` 全程零接触、零干扰）

---

## 1. 交付概览 / Executive Summary

Phase 135 将长期演进积累的 FX6-on-FX3 Web 控制台重构为**专业相机摄影机工作台（Clean Camera Studio Console）**，在 100% 保留全部既有后端 API、硬件安全护栏（`P4` / `P10` / `P11` / `P12` / `G31`）与测试契约的前提下，解决了首屏调试卡片堆叠、工程术语噪声外露及默认画面叠加实验室 HUD 遮挡原生 FX6 菜单的问题：

1. **首屏摄影机主工作台与 Sticky 右侧双操控区 / First-Screen Camera Studio & Sticky Dual Decks**
   - 在 [run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py#L14720-L14946) 中重构 `HTML_UI` 顶层网格为左右主辅结构：
     - **顶部 Studio 控制条 `#studio-top-bar`**：保留核心四语切换（`EN / 简体中文 / 繁體中文 / 日本語`）、**`纯净原生画面 / Pure Native Screen` 开关**（`#pure-native-screen-toggle`）、**`一键清空叠加HUD / Clear HUDs` 按钮**（`#reset-all-overlays-btn`）及实时状态徽章（`#studio-screen-mode-badge`）。
     - **首屏左侧主视口与原生操控**：`960×540` 实时画布 `#screen-wrap` → 原生 FX6 快捷页面/菜单导航 `#fx6-native-nav-card`（含默认折叠的 128 页全量页码抽屉 `#all128-pages-details` 与 11 类目录胶囊 `#cat-buttons`）→ `#cinema-big6-card`（Cinema Line Big-6 实时参数调节面板）。
     - **右侧 Sticky 物理机控台 `.studio-right-col`**：固定随屏的 FX6 D-Pad + ILME-FX3 物理机身按键台，首屏即可单屏完成开关机、菜单翻页、Big-6 参数调节与按键操作。

2. **默认折叠的 6 分类高级工程实验室抽屉 / Default-Collapsed 6-Category Advanced Lab Drawer**
   - 新增默认折叠的 `<details id="studio-advanced-lab-drawer" class="lab-drawer">`（不带 `open` 属性，见 [run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py#L14948)），将全量 12 张工程级控制卡片与调试组件（128 页搜索直跳、遥测栏、串行日志、状态详情等）收纳为 **6 个专业分类标签页 + Show All**：
     - `exposure`（曝光与色彩 / Exposure & Color）
     - `focus`（对焦与变焦 / Focus & Zoom）
     - `monitor`（监看与示波 / Monitor & Scopes）
     - `audio`（音频与时码 / Audio & TC）
     - `stream`（联机与推流 / Stream & Sync）
     - `debug`（诊断与预设 / Diagnostics & Presets）
     - `all`（全部展开 / Show All）

3. **全面清理工程代号与 API 路径噪声 / Clean Studio Typography**
   - 清理全部 18 个 `<h3>` 标题及 `P95_I18N`..`P129_I18N` 四语 `.title` 字符串中的 `Phase XX ·` 编号前缀与 `(/api/...)` 原始接口路径后缀，呈现纯粹的摄影机工程面板标题；同步修复 `run_fx6_menu_trial.py` 内 JS 正则转义（`/\\.cube$/i`、`/\\s+/`），在 Python 3.14 下达成 `0` 条 `SyntaxWarning`。

4. **Pure Native Screen Mode（`bit 30 = 0x40000000`）与一键清空叠加 HUD / Guest + Host Overlay Gate**
   - **客体固件侧（[fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c#L2063-L2065) & [fx6_render_dispatch](../../outputs/fx3-vm-trial/src/fx6_live_guest.c#L4412-L4414)）**：在 `p40_flags_word`（`mb[27]`）中启用 **Bit 30 (`0x40000000u`)** 作为全局 Pure Native Screen 门控位。置位时 `fx6_render_phase40_hud_strip` 与 `fx6_render_dispatch` 中 Phases 64..129 全部叠加层直接旁路，还原纯净 FX6 原生取景与菜单画面；同时为 Phases 64..123 补齐 `else if` bit 31 清零分支，确保任意叠加层可独立关闭。
   - **宿主机端（[get_studio_screen_mode](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py#L12466-L12504) / [set_studio_screen_mode](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py#L12505-L12615)）**：新增 `GET/POST /api/studio_screen_mode`，支持 `pure_native_screen`、`clear_all_overlays`、`toggle`、`reset`；保留后端默认 `pure_native_screen = False` 以兼容既有无头（Headless）自动化测试，同时通过前端 `localStorage('fx6_pure_native_screen')` 默认将网页新会话设为 Pure Native Screen（可一键切换）。所有 11 个 overlay setter 在用户显式启用叠加功能时自动解除 `studio_overlays_cleared` 并重新挂回 bit 31 门控。

---

## 2. 隔离端口实机 QEMU 验证与自动化测试证据 / Verification Receipts

### 2.1 隔离端口 `--port 18785` 实机 QEMU `GPE0` 像素差异实测 / Live QEMU GPE0 Pixel Delta Proof

在隔离工作目录 `/private/tmp/fx6_p135_trial_18785`（`--port 18785 --workdir /private/tmp/fx6_p135_trial_18785 --no-browser`）启动完整 FX3+FX6 QEMU 虚拟机（`25.2s` 就绪，`1024×540` `GPE0` 物理显存帧，`APPFW_SEGV=0`）：

| 验证阶段 / Scenario | 关键状态与遥测结果 / Telemetry | `GPE0` 帧指纹与像素指标 | 相对像素差异 / Pixel Delta | `APPFW_SEGV` |
|---|---|---|---|---|
| **Baseline Default (`pure_native=false`)** | `page=0`, `boot_crashed=false`, `FRAME_DIMS=1024x540` | `NZ_DEFAULT=404,631`, `SHA=afca1b803ac741fb` | 基线帧 | `0` |
| **HTML 结构门禁校验** | `h3_count=18`, 首屏严格顺序 `(12586 < 13816 < 16483 < 17319 < 25197)`, `#studio-advanced-lab-drawer` 默认无 `open` | 零 `Phase XX ·` / `(/api/...)` 噪声 | — | — |
| **Overlay Active + `pure_native=false`** | 开启辅助监看叠加层 | `NZ_OVERLAY=449,400` | — | `0` |
| **Pure Native ON (`bit 30 = 1`)** | `POST /api/studio_screen_mode {"pure_native_screen": true}` | `NZ_PURE=331,776`, `SHA=1eb757da584ea265` | vs Default: **`100,208` px**；vs Overlay: **`175,401` px** | `0` |
| **Clear All Overlays (`clear_all_overlays=true`)** | 一键清空全部 11 组叠加 HUD 状态并切入纯净原生画面 | `NZ_CLEAR=331,776` | vs Pure: **`0` px**（字节级一致） | `0` |
| **Pure Native OFF (`bit 30 = 0`)** | 恢复默认 HUD 条 | `NZ_OFF=404,631` | vs Clear: **`100,208` px**（完整恢复） | `0` |

验证完成后已停止该隔离 QEMU 会话并删除 `/private/tmp/fx6_p135_trial_18785`，默认端口 `8768` 全程未受任何影响。

### 2.2 Python 3.14 语法告警门禁、双模式单元测试与全仓洁净审计 / Verification Gates

- **Python 3.14 Zero `SyntaxWarning` 校验**：
  `python3 -B -W error::SyntaxWarning -m py_compile outputs/fx3-vm-trial/run_fx6_menu_trial.py outputs/fx3-vm-trial/tests/test_phase135_clean_studio_console.py` → **PASS (exit 0, 0 warnings)**
- **本地供体模式 / Local Donor Mode**（`/usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py"`）：
  **429 / 429 PASSED** in `13.476s`（含新增 30 项 [test_phase135_clean_studio_console.py](../../outputs/fx3-vm-trial/tests/test_phase135_clean_studio_console.py)，覆盖 real ARM64 Zig cross-compile of `fx6_live_guest.c`、`/api/studio_screen_mode` 状态机、bit 30/bit 31 门控、11 setter 重激活、`HTML_UI` 结构与顺序门禁、`SyntaxWarning` 检测）
- **洁净室模式 / Clean-Room Mode**（`FX3_FX6_FORCE_CLEAN_ROOM=1 /usr/bin/python3 -B -m unittest discover -s outputs/fx3-vm-trial/tests -p "test_*.py"`）：
  **429 / 429 PASSED** in `13.752s`（`skipped=3` 仅限供体专属静态资产校验，Phase 135 全量 30/30 通过）
- **全仓洁净门禁 / Lab Clean-Only Gate**（`/usr/bin/python3 -B scripts/run_all_lab_tests.py --clean-only`）：
  **ALL GREEN in 0.04s**（`git status --porcelain binary/pyc audit: CLEAN`）

---

## 3. 交付文件清单 / Owned Files

1. [outputs/fx3-vm-trial/run_fx6_menu_trial.py](../../outputs/fx3-vm-trial/run_fx6_menu_trial.py) — `HTML_UI` Studio Console 重构、默认折叠 `#studio-advanced-lab-drawer`（6 分类标签）、清理标题与四语标签、`/api/studio_screen_mode` 后端接口与 bit 30 门控、JS 正则转义修复
2. [outputs/fx3-vm-trial/src/fx6_live_guest.c](../../outputs/fx3-vm-trial/src/fx6_live_guest.c) — Bit 30 (`0x40000000u`) Pure Native Screen 全局旁路门控与 Phases 64..123 bit 31 清零分支
3. [outputs/fx3-vm-trial/README.md](../../outputs/fx3-vm-trial/README.md) — 同步 Phase 135 特性说明、429 项单元测试数量与测试文件清单
4. [outputs/fx3-vm-trial/tests/test_phase135_clean_studio_console.py](../../outputs/fx3-vm-trial/tests/test_phase135_clean_studio_console.py) — Phase 135 30 项双模式单元测试与 ARM64 Zig 编译验证
5. [reports/2026-11-14-phase135-clean-studio-console-refactor/README.md](README.md) — 本阶段工程交付与实测报告
