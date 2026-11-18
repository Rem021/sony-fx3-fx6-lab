# Phase 327 工程交付报告（Task H394, Wave-63）：`G145`/`G146` 与统一 `146/146` 安全预检门控

> 关联模块：[`realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h394-phase327-safety-146gates-hdmi-raw-desqueeze-reclamp-varshutter-apsc/outputs/fx3-safety/fx3_safety/realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard.py)  
> 关联测试：[`test_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_146gate_guard.py`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h394-phase327-safety-146gates-hdmi-raw-desqueeze-reclamp-varshutter-apsc/outputs/fx3-safety/tests/test_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_146gate_guard.py)（96 项双模单元测试）  
> 实证情报基线：[`Wave-63 实证情报报告`](file:///Users/kafu/AI-Workspace/AI/Orca/Worktrees/sony-fx3-fx6-lab/fx3-main-lane/h394-phase327-safety-146gates-hdmi-raw-desqueeze-reclamp-varshutter-apsc/reports/2026-11-17-global-sony-wave63-hdmi-raw-desqueeze-tally-emph-rec-varshutter-apsc-intel/README.md)

---

## 1. 实测事实 vs 推断边界

### 1.1 实测事实（本机只读 `os.O_RDONLY` / `os.pread` 验证 & `appFw.so`/`.uxc` 取证）

1. **只读 Donor 审计与零字节泄漏**：
   - 在不加载或修改任何索尼专有镜像、严守 `os.open(..., os.O_RDONLY)` 与定界 `os.pread`（单次审计耗时 `< 0.01s`，远低于 `0.20s` 上限，`RAW_FIRMWARE_BYTES_LEAKED = 0`）前提下，核验了 `11` 份 pinned donor 资产（含 `FX3 appFw.so` `79,015,712 B` 20 个切片、`FX6 appFw.so` `50,520,424 B` 12 个切片、`FX3` 四语 `_f.uxc`、`string_english.uxc`、`string_english_g.uxc`、`FX3-CX95900_ALLLANG-Backup.bin`、`FX6 string_english.uxc` / `string_english_2.uxc`）。
   - 在 `FX3 appFw.so` 与四语 `_f.uxc` 中直接命中 Wave-63 符号与 `resid16`：`BKID_APP_setting_rec_media_during_hdmi_output`（`0x6144`）、`BKID_APP_setting_hdmi_resolution`（`0x79ac`）、`BKID_APP_setting_hdmi_4k_output_setting`（`0x74d7`）、`BKID_APP_setting_raw_output`（`0x6e97`）、`BKID_APP_setting_raw_output_frame_rate`（`0x78fd`）、`BKID_APP_setting_hdmi_tc_output`（`0x72af`）、`BKID_APP_setting_rec_control`（`0x76e1`）、`BKID_APP_setting_4ch_output_ch`（`0x6aa0`）、已移除符号 `BKID_APP_setting_color_gamut_for_raw_out`（`0x6bdc`）、`BKID_APP_setting_de_squeeze_disp`（`0x7aba`）+ `VAL_DE_SQUEEZE_DISP_1_65X`、`BKID_APP_setting_rec_lamp`（`0x6e62`）+ 休眠符号 `REC_LAMP_LIGHT_UP_ONLY_ONE`、`BKID_APP_setting_emphasis_dur_rec`（`0x68cf`）、`25view_remain_shoot_display`（`0x604d`）、`BKID_APP_setting_auto_review`、`BKID_APP_setting_high_res_ss`（`0x6831`，对应日语 `高分解ｼｬｯﾀｰ`）、`BKID_APP_setting_anti_flicker_shoot`（`0x623d`）及 `BKID_APP_setting_super_35mm`（`0x6eba`）。
2. **`Gate G145`（HDMI 8 项 Initialize-only + RAW Co-Rec Vault + 5 态 De-Squeeze）**：
   - `Setup -> [External Output] -> [HDMI Output Settings]` 强制精确 8 项 Initialize-only 菜单；`[Output Resolution]` 在 `Log != Off` 或 `PPLUT1..4` 且 `Rec. Media = On` + `RAW = Off` 时强制钳位 `1080p`；`[4K Output Set.(HDMI Only)]` 仅 6 种 10-bit 模式，切入/切出 `24.00p 10bit` 未确认重启拦截（`EINVAL=22`），休眠 `24.00p 8bit`（`_f 0x748a`）与已移除 `[Color Gamut for RAW Output]`（`_f 0x6bdc`）阻断返回 `EOPNOTSUPP=95`。
   - `RAW Output = On`（`4264x2408` 16-bit）+ `Rec. Media dur HDMI Output = On` 触发内部 XAVC + Proxy 双写，若指向 `Slot-1` Tier-0 Vault 则硬阻断（`EROFS=30`, `slot1_data_sector_writes = 0`）；`Off(HDMI Only)` 则执行零写卡旁路。`HDMI Info. Display = On`（`RAW=Off` 且 `Rec. Media=On`）熄灭机身内置 LCD。
   - `[De-Squeeze Display]` 验证 Ver. `7.00/7.02` 5 态集合（`Off`, `1.3x`, `1.5x`, `1.6x` -> 实际 `1.65x`, `2.0x`），拒绝不存在的 `1.8x`（`EOPNOTSUPP=95`），强制校验 4 项锁定、6 项自动旁路、与 `Focus Magnifier` / `Bright Monitoring` 共存及零内录烘焙；`576` 状态矩阵全部收口。
3. **`Gate G146`（REC Lamp / Emph REC / Remain Shoot / Auto Review / 休眠 Var. Shutter & Wave-42 APS-C S35 勘误）**：
   - `[REC Lamp]` 仅暴露 `All On` / `Only Front Off` / `All Off`（3 盏物理灯，独立于 `[Silent Mode]`），拒绝休眠 `[Tally Light]` / `REC_LAMP_LIGHT_UP_ONLY_ONE`（`EOPNOTSUPP=95`）；`[Emphasized REC Display]` 可由 `[Camera Settings Reset]` 复位且 Clean HDMI 下抑制；`[Remain Shoot Display]` 与仅 Still 生效的 `[Auto Review]`（Interval Shoot 下禁用）均为 Initialize-only。
   - 休眠 `[Var. Shutter]`（`high_res_ss` `_f 0x6831` / `Anti-flicker Tv Scan` `_g 0x60a8`）与 `FX6` `ECS` 统一拒绝（`EOPNOTSUPP=95`），区分仅 Still 机械快门生效的 `[Anti-flicker Shoot.]`。
   - 固化 **Wave-42 Reset 勘误**：`[APS-C S35 Shooting]`（`Auto`/`On`/`Off`）为 **Initialize-only（不受 `[Camera Settings Reset]` 复位）**，开启或 `Auto` 挂接 APS-C 镜头时将视频格式钳位至 `HD 1920x1080 <= 120p`（拦截全部 `4K` / `DCI 4K` / `200-240fps` `S&Q` / `4K HDMI` / `RAW Output`）并将 Still `L: 12M` 钳位至 `M: 5.1M (2768x1848)`；`648` 状态矩阵全部收口。
4. **统一 `146/146` 主预检与向后兼容**：
   - `evaluate_146gate_preflight` 委托 `evaluate_144gate_preflight` 处理 `G01..G144`，离线模式下稳定通过 `143/146`（`VERIFIED_143_OF_146_AWAITING_PHYSICAL_TIER0`），`--simulate-bench-dry-run` 下通过 `146/146`（`VERIFIED_ALL_146_GATES_DRY_RUN_SIMULATED_BACKUP`），`verify-milestone-311` 与 `verify-milestone-295` 自动发现钩子已切换为 `146`；模拟无 donor Ubuntu CI（`_iter_work_roots=()` + `work_root is None` 防护 + `FX3_FX6_FORCE_CLEAN_ROOM=1`）全绿通过。

### 1.2 推断与边界声明

- 上述 `576` 项 `G145` 状态组合与 `648` 项 `G146` 状态组合及 `EROFS=30` / `EOPNOTSUPP=95` / `EINVAL=22` 阻断响应均基于 Phase 327 确定性离线安全护栏模型及 `--simulate-bench-dry-run` 演练推断验证；所有物理写入、跨机刷写、EL3 与真机联机标志全部硬锁 `False` / `0`，**未连接或写入任何真实 FX3 硬件**（`overall_ready_for_hardware_attach = False`）。

---

## 2. 严格文件所有权清单（仅 6 个文件）

1. `outputs/fx3-safety/fx3_safety/realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_and_146gate_guard.py`（新增）
2. `outputs/fx3-safety/fx3_safety/__init__.py`（更新导出）
3. `outputs/fx3-safety/fx3_safety/__main__.py`（新增 `verify-hdmi-raw-desqueeze-guard` / `verify-reclamp-varshutter-apsc-guard` / `verify-146-gates`）
4. `outputs/fx3-safety/README.md`（追加第 73 节）
5. `outputs/fx3-safety/tests/test_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_146gate_guard.py`（新增 96 项双模测试）
6. `reports/2026-11-17-phase327-safety-146gates-hdmi-raw-desqueeze-reclamp-varshutter-apsc/README.md`（本报告）
